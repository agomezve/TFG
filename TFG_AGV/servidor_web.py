"""Servidor de la app móvil (PWA) de telerehabilitación.

El móvil usa su cámara y envía los fotogramas por WebSocket; aquí se analizan con los
MISMOS módulos de ejercicio que la app de escritorio (motor.SesionEjercicio), se guarda
la sesión en la misma BBDD y se devuelve el fotograma con el esqueleto y las correcciones.

Uso:
    python servidor_web.py                 # http://localhost:8000
    python servidor_web.py --https         # además https://<IP-del-ordenador>:8443 para el móvil
    TELEREHAB_DATA_DIR=datos_demo python servidor_web.py   # con los datos de demo
"""
import argparse
import asyncio
import io
import json
import os
import secrets
import socket
import subprocess

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import database
import ejercicios
from config import directorio_datos
from informes import buscar_informe_y_video
from motor import SesionEjercicio

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_WEB = os.path.join(RAIZ, "web")
CARPETA_CERTS = os.path.join(RAIZ, "certs")
NIVELES = ("principiante", "intermedio", "avanzado")

app = FastAPI(title="TeleRehab IA", docs_url=None, redoc_url=None)

# Sesiones de usuario en memoria: token -> {"rol": "fisio"|"paciente", "id": int, "nombre": str}
_SESIONES = {}


# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def _usuario(request_o_token, rol=None):
    token = request_o_token
    if isinstance(request_o_token, Request):
        cabecera = request_o_token.headers.get("authorization", "")
        token = cabecera[7:] if cabecera.startswith("Bearer ") else request_o_token.query_params.get("token")
    usuario = _SESIONES.get(token or "")
    if usuario is None:
        raise HTTPException(401, "Sesión caducada, vuelve a iniciar sesión")
    if rol and usuario["rol"] != rol:
        raise HTTPException(403, "No tienes permiso para esto")
    return usuario


@app.post("/api/login")
async def login(request: Request):
    datos = await request.json()
    rol, info = database.autenticar(datos.get("usuario"), datos.get("password"))
    if rol is None:
        raise HTTPException(401, info)
    token = secrets.token_urlsafe(24)
    if rol == "fisio":
        _SESIONES[token] = {"rol": "fisio", "id": None, "nombre": "Fisioterapeuta"}
    else:
        _SESIONES[token] = {"rol": "paciente", "id": info[0], "nombre": info[1]}
    return {"token": token, **_SESIONES[token]}


@app.post("/api/logout")
async def logout(request: Request):
    cabecera = request.headers.get("authorization", "")
    _SESIONES.pop(cabecera[7:], None)
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# PACIENTE
# ──────────────────────────────────────────────────────────────────────────────

def _historial_json(paciente_id):
    return [
        {"fecha": f, "ejercicio": e, "nivel": n, "repeticiones": int(r or 0), "errores": int(er or 0),
         "profundidad_media": p, "observaciones": o}
        for (f, e, n, r, er, p, o) in database.obtener_historial_paciente(paciente_id)
    ]


@app.get("/api/ejercicios")
async def lista_ejercicios(request: Request):
    _usuario(request)
    return [
        {"nombre": e.nombre, "video": f"/videos_explicativos/{e.video_explicativo}",
         "consejos": ejercicios.CONSEJOS.get(e.nombre, []),
         "por_tiempo": e.nombre in ("Plancha", "Propiocepcion")}
        for e in ejercicios.CATALOGO
    ]


@app.get("/api/mi-historial")
async def mi_historial(request: Request):
    usuario = _usuario(request, "paciente")
    return _historial_json(usuario["id"])


def _png_progreso(paciente_id, ejercicio):
    from graficas import figura_progreso
    historial = list(reversed(database.obtener_historial_paciente(paciente_id)))
    figura = figura_progreso(historial, ejercicio, tamano=(5.2, 4.4))  # proporción de pantalla de móvil
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png", dpi=160, facecolor=figura.get_facecolor())
    return Response(buffer.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/mi-progreso.png")
async def mi_progreso(request: Request, ejercicio: str):
    usuario = _usuario(request, "paciente")
    return await run_in_threadpool(_png_progreso, usuario["id"], ejercicio)


# ──────────────────────────────────────────────────────────────────────────────
# FISIOTERAPEUTA
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/fisio/pacientes")
async def fisio_pacientes(request: Request):
    _usuario(request, "fisio")
    resultado = []
    for pid, nombre, edad in database.obtener_pacientes():
        historial = database.obtener_historial_paciente(pid)
        resultado.append({"id": pid, "nombre": nombre, "edad": edad, "series": len(historial),
                          "ultima": historial[0][0] if historial else None})
    return resultado


@app.post("/api/fisio/pacientes")
async def fisio_nuevo_paciente(request: Request):
    _usuario(request, "fisio")
    d = await request.json()
    nombre = (d.get("nombre") or "").strip()
    password = d.get("password") or ""
    edad_txt = str(d.get("edad") or "").strip()
    # Mismas validaciones que el formulario de la app de escritorio
    if not nombre or not password:
        raise HTTPException(400, "El nombre y la contraseña son obligatorios")
    if nombre.lower() == database.USUARIO_FISIO:
        raise HTTPException(400, "Ese nombre está reservado")
    if database.existe_paciente(nombre):
        raise HTTPException(400, "Ya existe un paciente con ese nombre")
    if len(password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    if password != d.get("password2"):
        raise HTTPException(400, "Las contraseñas no coinciden")
    if edad_txt and not edad_txt.isdigit():
        raise HTTPException(400, "La edad debe ser un número")
    pid = database.crear_paciente(nombre, int(edad_txt) if edad_txt else None, (d.get("notas") or "").strip(), password=password)
    return {"id": pid, "nombre": nombre}


@app.get("/api/fisio/pacientes/{paciente_id}/historial")
async def fisio_historial(request: Request, paciente_id: int):
    _usuario(request, "fisio")
    return {"nombre": database.obtener_nombre_paciente(paciente_id), "sesiones": _historial_json(paciente_id)}


@app.get("/api/fisio/pacientes/{paciente_id}/progreso.png")
async def fisio_progreso(request: Request, paciente_id: int, ejercicio: str):
    _usuario(request, "fisio")
    return await run_in_threadpool(_png_progreso, paciente_id, ejercicio)


@app.get("/api/fisio/serie")
async def fisio_serie(request: Request, paciente_id: int, fecha: str, ejercicio: str, idx: int, ts: str = None):
    _usuario(request, "fisio")
    nombre = database.obtener_nombre_paciente(paciente_id)
    ruta_txt, ruta_vid = buscar_informe_y_video(nombre, fecha, ejercicio, idx, ts)
    informe = None
    if ruta_txt and os.path.exists(ruta_txt):
        with open(ruta_txt, encoding="utf-8") as f:
            informe = f.read()
    video = None
    if ruta_vid and ruta_vid.endswith(".mp4"):  # los .avi no se pueden reproducir en el navegador
        video = os.path.relpath(ruta_vid, directorio_datos())
    return {"informe": informe, "video": video}


@app.get("/api/fisio/video")
async def fisio_video(request: Request, ruta: str):
    _usuario(request, "fisio")
    base = os.path.realpath(os.path.join(directorio_datos(), "usuarios"))
    completa = os.path.realpath(os.path.join(directorio_datos(), ruta))
    if not completa.startswith(base + os.sep) or not completa.endswith(".mp4") or not os.path.exists(completa):
        raise HTTPException(404, "Vídeo no encontrado")
    return FileResponse(completa, media_type="video/mp4")


@app.post("/api/fisio/password")
async def fisio_password(request: Request):
    _usuario(request, "fisio")
    d = await request.json()
    nueva = d.get("nueva") or ""
    if database.autenticar(database.USUARIO_FISIO, d.get("actual"))[0] != "fisio":
        raise HTTPException(400, "La contraseña actual no es correcta")
    if len(nueva) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres")
    if nueva != d.get("nueva2"):
        raise HTTPException(400, "Las contraseñas no coinciden")
    database.cambiar_password_fisio(nueva)
    return {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# SERIE EN DIRECTO (WebSocket)
# ──────────────────────────────────────────────────────────────────────────────
#  Cliente -> servidor: fotograma JPEG (binario) | "stop" (texto)
#  Servidor -> cliente: fotograma JPEG procesado (binario) seguido de un JSON con el estado.

def _procesar_jpeg(sesion, datos):
    imagen = cv2.imdecode(np.frombuffer(datos, np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        return None, "en_curso"
    frame_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    estado = sesion.procesar(frame_rgb)
    ok, salida = cv2.imencode(".jpg", cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 70])
    return (salida.tobytes() if ok else None), estado


@app.websocket("/ws/serie")
async def ws_serie(ws: WebSocket, token: str = Query(...), ejercicio: str = Query(...), nivel: str = Query(...)):
    usuario = _SESIONES.get(token)
    await ws.accept()
    if usuario is None or usuario["rol"] != "paciente" or ejercicio not in ejercicios.POR_NOMBRE or nivel not in NIVELES:
        await ws.send_text(json.dumps({"estado": "error", "mensaje": "Sesión no válida"}))
        await ws.close()
        return

    sesion = await run_in_threadpool(SesionEjercicio, ejercicio, nivel, usuario["id"], usuario["nombre"])
    estado = "en_curso"
    try:
        while estado == "en_curso":
            mensaje = await ws.receive()
            if mensaje["type"] == "websocket.disconnect":
                break
            if mensaje.get("text") == "stop":
                estado = "detenido"
                break
            if mensaje.get("bytes"):
                jpeg, estado = await run_in_threadpool(_procesar_jpeg, sesion, mensaje["bytes"])
                if jpeg:
                    await ws.send_bytes(jpeg)
                await ws.send_text(json.dumps({"estado": estado, **sesion.marcador()}))
    except WebSocketDisconnect:
        pass
    finally:
        # Igual que al pulsar "Detener" o al terminar en escritorio: informe + BBDD + vídeo
        await run_in_threadpool(sesion.finalizar)
    try:
        await ws.send_text(json.dumps({"estado": "guardado", "resultado": estado}))
        await ws.close()
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# FICHEROS ESTÁTICOS (la app en sí)
# ──────────────────────────────────────────────────────────────────────────────

app.mount("/videos_explicativos", StaticFiles(directory=os.path.join(RAIZ, "videos_explicativos")), name="videos")
app.mount("/static", StaticFiles(directory=CARPETA_WEB), name="static")


@app.get("/")
async def inicio():
    return FileResponse(os.path.join(CARPETA_WEB, "index.html"), headers={"Cache-Control": "no-cache"})


@app.get("/sw.js")
async def service_worker():
    return FileResponse(os.path.join(CARPETA_WEB, "sw.js"), media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
async def manifest():
    return FileResponse(os.path.join(CARPETA_WEB, "manifest.webmanifest"), media_type="application/manifest+json")


@app.exception_handler(HTTPException)
async def error_http(request, exc):
    return JSONResponse({"detalle": exc.detail}, status_code=exc.status_code)


# ──────────────────────────────────────────────────────────────────────────────
# ARRANQUE
# ──────────────────────────────────────────────────────────────────────────────

def ip_local():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def asegurar_certificado(ip):
    """Certificado autofirmado para HTTPS en la red local (el móvil exige HTTPS para usar la cámara)."""
    os.makedirs(CARPETA_CERTS, exist_ok=True)
    cert, clave = os.path.join(CARPETA_CERTS, "cert.pem"), os.path.join(CARPETA_CERTS, "key.pem")
    if not (os.path.exists(cert) and os.path.exists(clave)):
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "825",
                        "-keyout", clave, "-out", cert, "-subj", "/CN=TeleRehab local",
                        "-addext", f"subjectAltName=IP:{ip},IP:127.0.0.1,DNS:localhost"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cert, clave


async def _servir(https, puerto, puerto_https):
    import uvicorn
    servidores = [uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=puerto, log_level="warning"))]
    ip = ip_local()
    print(f"\n  App en este ordenador:  http://localhost:{puerto}")
    if https:
        cert, clave = asegurar_certificado(ip)
        servidores.append(uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=puerto_https, log_level="warning",
                                                        ssl_certfile=cert, ssl_keyfile=clave)))
        print(f"  App en el móvil (misma WiFi):  https://{ip}:{puerto_https}")
        print("  (el móvil avisará de que el certificado no es de confianza: acepta para continuar)")
    print(f"  Datos: {directorio_datos()}\n")
    await asyncio.gather(*(s.serve() for s in servidores))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor de la app móvil de telerehabilitación")
    parser.add_argument("--https", action="store_true", help="servir también por HTTPS para usarla desde el móvil")
    parser.add_argument("--puerto", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--puerto-https", type=int, default=8443)
    args = parser.parse_args()
    asyncio.run(_servir(args.https, args.puerto, args.puerto_https))
