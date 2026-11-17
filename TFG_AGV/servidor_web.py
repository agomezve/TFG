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
import datetime
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
from adherencia import plan_de_hoy, resumen_adherencia
from metricas import metricas_clinica, metricas_paciente
from config import directorio_datos, nombre_carpeta_paciente
from informes import buscar_informe_y_video
from motor import SesionEjercicio

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_WEB = os.path.join(RAIZ, "web")
CARPETA_CERTS = os.path.join(RAIZ, "certs")
NIVELES = ("principiante", "intermedio", "avanzado")
# Versión del texto de consentimiento (web/privacidad.html). Si cambia el texto, se sube la versión
# y a cada paciente se le vuelve a pedir que lo acepte.
VERSION_CONSENTIMIENTO = "2026-11"

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


def _fisio(request):
    return _usuario(request, "fisio")


def _paciente_de_mi_clinica(fisio, paciente_id):
    """Un fisio solo ve y toca a los pacientes de su clínica (para el resto, 'no existe')."""
    if database.clinica_de_paciente(paciente_id) != fisio["clinica_id"]:
        raise HTTPException(404, "Paciente no encontrado")


@app.post("/api/login")
async def login(request: Request):
    datos = await request.json()
    rol, info = database.autenticar(datos.get("usuario"), datos.get("password"))
    if rol is None:
        raise HTTPException(401, info)
    token = secrets.token_urlsafe(24)
    if rol == "fisio":
        # info es None para el fisio de siempre (clínica principal) o los datos del fisio de otra clínica
        clinica_id = info["clinica_id"] if info else database.CLINICA_PRINCIPAL
        _SESIONES[token] = {"rol": "fisio", "id": None, "fisio_id": info["fisio_id"] if info else None,
                            "nombre": (info["nombre"] if info else None) or "Fisioterapeuta",
                            "clinica_id": clinica_id, "clinica": database.nombre_clinica(clinica_id)}
        return {"token": token, **_SESIONES[token]}
    _SESIONES[token] = {"rol": "paciente", "id": info[0], "nombre": info[1]}
    return {"token": token, **_SESIONES[token], "consentimiento": _consentimiento_vigente(info[0])}


def _consentimiento_vigente(paciente_id):
    fila = database.obtener_consentimiento(paciente_id)
    return bool(fila and fila[0] == VERSION_CONSENTIMIENTO)


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

    def recurso(carpeta, archivo):
        # Versión ligera para el móvil (720p, sin audio) y portada, si existen; si no, el original
        return f"/videos_explicativos/{carpeta}/{archivo}" if os.path.exists(
            os.path.join(RAIZ, "videos_explicativos", carpeta, archivo)) else None

    return [
        {"nombre": e.nombre,
         "video": recurso("web", e.video_explicativo) or f"/videos_explicativos/{e.video_explicativo}",
         "video_analisis": f"/videos_explicativos/{e.video_explicativo}",  # el original, para «Probar con el vídeo de ejemplo»
         "portada": recurso("portadas", e.video_explicativo.rsplit(".", 1)[0] + ".jpg"),
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


@app.get("/api/mi-plan")
async def mi_plan(request: Request):
    """Plan que ha recetado el fisio, con lo que lleva hecho hoy y esta semana."""
    usuario = _usuario(request, "paciente")
    historial = _historial_json(usuario["id"])
    plan = database.obtener_plan(usuario["id"])
    return {"plan": plan_de_hoy(plan, historial), **resumen_adherencia(plan, historial)}


@app.post("/api/mi-password")
async def mi_password(request: Request):
    usuario = _usuario(request, "paciente")
    d = await request.json()
    nueva = d.get("nueva") or ""
    if database.autenticar(usuario["nombre"], d.get("actual"))[0] != "paciente":
        raise HTTPException(400, "La contraseña actual no es correcta")
    if len(nueva) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres")
    if nueva != d.get("nueva2"):
        raise HTTPException(400, "Las contraseñas no coinciden")
    database.cambiar_password_paciente(usuario["id"], nueva)
    return {"ok": True}


# ─── Protección de datos (RGPD) ───────────────────────────────────────────────

@app.get("/api/consentimiento")
async def ver_consentimiento(request: Request):
    usuario = _usuario(request, "paciente")
    fila = database.obtener_consentimiento(usuario["id"])
    return {"version_actual": VERSION_CONSENTIMIENTO, "aceptado": _consentimiento_vigente(usuario["id"]),
            "fecha": fila[1] if fila else None}


@app.post("/api/consentimiento")
async def aceptar_consentimiento(request: Request):
    usuario = _usuario(request, "paciente")
    d = await request.json()
    if d.get("version") != VERSION_CONSENTIMIENTO or d.get("acepto") is not True:
        raise HTTPException(400, "Debes aceptar la versión vigente del consentimiento")
    database.registrar_consentimiento(usuario["id"], VERSION_CONSENTIMIENTO)
    return {"ok": True}


@app.delete("/api/consentimiento")
async def retirar_consentimiento(request: Request):
    """El paciente retira el consentimiento: no se graban más series hasta que lo vuelva a aceptar."""
    usuario = _usuario(request, "paciente")
    database.retirar_consentimiento(usuario["id"])
    return {"ok": True}


@app.get("/api/mis-datos")
async def mis_datos(request: Request):
    """Derecho de acceso y portabilidad: todos los datos del paciente en JSON."""
    usuario = _usuario(request, "paciente")
    fila = database.obtener_consentimiento(usuario["id"])
    datos = {
        "paciente": usuario["nombre"],
        "exportado": datetime.datetime.now().isoformat(timespec="seconds"),
        "consentimiento": {"version": fila[0], "fecha": fila[1]} if fila else None,
        "plan": database.obtener_plan(usuario["id"]),
        "sesiones": _historial_json(usuario["id"]),
    }
    nombre_fichero = f"mis_datos_telerehab_{usuario['id']}.json"
    return Response(json.dumps(datos, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'})


# ──────────────────────────────────────────────────────────────────────────────
# FISIOTERAPEUTA
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/fisio/pacientes")
async def fisio_pacientes(request: Request):
    fisio = _fisio(request)
    resultado = []
    for pid, nombre, edad in database.obtener_pacientes(fisio["clinica_id"]):
        historial = _historial_json(pid)
        plan = database.obtener_plan(pid)
        resultado.append({"id": pid, "nombre": nombre, "edad": edad, "series": len(historial),
                          "ultima": historial[0]["fecha"] if historial else None,
                          "en_plan": len(plan), **resumen_adherencia(plan, historial)})
    return resultado


@app.post("/api/fisio/pacientes")
async def fisio_nuevo_paciente(request: Request):
    fisio = _fisio(request)
    d = await request.json()
    nombre = (d.get("nombre") or "").strip()
    password = d.get("password") or ""
    edad_txt = str(d.get("edad") or "").strip()
    # Mismas validaciones que el formulario de la app de escritorio. La contraseña es opcional:
    # si se deja vacía, el paciente la crea él mismo con el enlace o el QR de invitación.
    if not nombre:
        raise HTTPException(400, "El nombre es obligatorio")
    if nombre.lower() == database.USUARIO_FISIO or database.existe_usuario_fisio(nombre):
        raise HTTPException(400, "Ese nombre está reservado")
    if database.existe_paciente(nombre):
        raise HTTPException(400, "Ya existe un paciente con ese nombre")
    if password or d.get("password2"):
        if len(password) < 6:
            raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
        if password != d.get("password2"):
            raise HTTPException(400, "Las contraseñas no coinciden")
    if edad_txt and not edad_txt.isdigit():
        raise HTTPException(400, "La edad debe ser un número")
    # Sin contraseña se pone una aleatoria que nadie conoce (nunca la inicial "12345")
    pid = database.crear_paciente(nombre, int(edad_txt) if edad_txt else None, (d.get("notas") or "").strip(),
                                  password=password or secrets.token_urlsafe(16), clinica_id=fisio["clinica_id"])
    return {"id": pid, "nombre": nombre, "invitacion": None if password else _nueva_invitacion(request, pid)}


@app.get("/api/fisio/pacientes/{paciente_id}/historial")
async def fisio_historial(request: Request, paciente_id: int):
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
    historial = _historial_json(paciente_id)
    plan = database.obtener_plan(paciente_id)
    consentimiento = database.obtener_consentimiento(paciente_id)
    return {"nombre": database.obtener_nombre_paciente(paciente_id), "sesiones": historial,
            "plan": plan_de_hoy(plan, historial), **resumen_adherencia(plan, historial),
            "consentimiento": {"version": consentimiento[0], "fecha": consentimiento[1],
                               "vigente": consentimiento[0] == VERSION_CONSENTIMIENTO} if consentimiento else None}


@app.put("/api/fisio/pacientes/{paciente_id}/plan")
async def fisio_guardar_plan(request: Request, paciente_id: int):
    """El fisio receta el plan: lista de {ejercicio, nivel, series (1-10), dias_semana (1-7)}."""
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
    items = (await request.json()).get("plan")
    if not isinstance(items, list):
        raise HTTPException(400, "Formato de plan no válido")
    limpios, vistos = [], set()
    for i in items:
        ej, nivel = i.get("ejercicio"), i.get("nivel")
        try:
            series, dias = int(i.get("series")), int(i.get("dias_semana"))
        except (TypeError, ValueError):
            raise HTTPException(400, "Series y días deben ser números")
        if ej not in ejercicios.POR_NOMBRE or nivel not in NIVELES or ej in vistos:
            raise HTTPException(400, f"Ejercicio o nivel no válido: {ej}")
        if not (1 <= series <= 10 and 1 <= dias <= 7):
            raise HTTPException(400, "Series entre 1 y 10, días por semana entre 1 y 7")
        vistos.add(ej)
        limpios.append({"ejercicio": ej, "nivel": nivel, "series": series, "dias_semana": dias})
    database.guardar_plan(paciente_id, limpios)
    return {"ok": True, "plan": limpios}


@app.delete("/api/fisio/pacientes/{paciente_id}")
async def fisio_borrar_paciente(request: Request, paciente_id: int):
    """Derecho de supresión: borra al paciente con todas sus sesiones, informes y vídeos."""
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
    d = await request.json()
    nombre = database.obtener_nombre_paciente(paciente_id)
    if (d.get("confirmacion") or "").strip().lower() != nombre.lower():
        raise HTTPException(400, "Escribe el nombre del paciente para confirmar")
    await run_in_threadpool(database.borrar_paciente, paciente_id)
    # Cierra las sesiones abiertas de ese paciente
    for token in [t for t, u in _SESIONES.items() if u["rol"] == "paciente" and u["id"] == paciente_id]:
        _SESIONES.pop(token, None)
    return {"ok": True}


@app.get("/api/fisio/pacientes/{paciente_id}/progreso.png")
async def fisio_progreso(request: Request, paciente_id: int, ejercicio: str):
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
    return await run_in_threadpool(_png_progreso, paciente_id, ejercicio)


@app.get("/api/fisio/serie")
async def fisio_serie(request: Request, paciente_id: int, fecha: str, ejercicio: str, idx: int, ts: str = None):
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
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
    fisio = _fisio(request)
    base = os.path.realpath(os.path.join(directorio_datos(), "usuarios"))
    completa = os.path.realpath(os.path.join(directorio_datos(), ruta))
    if not completa.startswith(base + os.sep) or not completa.endswith(".mp4") or not os.path.exists(completa):
        raise HTTPException(404, "Vídeo no encontrado")
    carpeta = os.path.relpath(completa, base).split(os.sep)[0]
    if carpeta not in {nombre_carpeta_paciente(n) for _, n, _ in database.obtener_pacientes(fisio["clinica_id"])}:
        raise HTTPException(404, "Vídeo no encontrado")
    return FileResponse(completa, media_type="video/mp4")


@app.post("/api/fisio/password")
async def fisio_password(request: Request):
    fisio = _fisio(request)
    d = await request.json()
    nueva = d.get("nueva") or ""
    usuario = database.usuario_de_fisio(fisio["fisio_id"]) if fisio["fisio_id"] else database.USUARIO_FISIO
    if database.autenticar(usuario, d.get("actual"))[0] != "fisio":
        raise HTTPException(400, "La contraseña actual no es correcta")
    if len(nueva) < 6:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 6 caracteres")
    if nueva != d.get("nueva2"):
        raise HTTPException(400, "Las contraseñas no coinciden")
    database.cambiar_password_fisio(nueva, fisio["fisio_id"])
    return {"ok": True}


# ─── Métricas del piloto e informe PDF ────────────────────────────────────────

def _metricas(clinica_id):
    filas = []
    for pid, nombre, edad in database.obtener_pacientes(clinica_id):
        m = metricas_paciente(database.obtener_plan(pid), _historial_json(pid))
        filas.append({"id": pid, "nombre": nombre, "edad": edad, **m})
    return {"clinica": database.nombre_clinica(clinica_id), "generado": datetime.date.today().isoformat(),
            "resumen": metricas_clinica(filas), "pacientes": filas}


@app.get("/api/fisio/metricas")
async def fisio_metricas(request: Request):
    """Resultados del piloto en la clínica: uso, adherencia y evolución de la técnica."""
    return await run_in_threadpool(_metricas, _fisio(request)["clinica_id"])


@app.get("/api/fisio/metricas.csv")
async def fisio_metricas_csv(request: Request):
    """Lo mismo en CSV (Excel en español: separador ';'), una fila por paciente."""
    import csv
    datos = await run_in_threadpool(_metricas, _fisio(request)["clinica_id"])
    columnas = [("id", "ID"), ("nombre", "Paciente"), ("edad", "Edad"), ("primera", "Primera sesión"),
                ("ultima", "Última sesión"), ("semanas", "Semanas de uso"), ("series", "Series"),
                ("dias_activos", "Días activos"), ("dias_por_semana", "Días por semana"),
                ("series_7d", "Series últimos 7 días"), ("adherencia", "Adherencia 7 días (%)"),
                ("correcto_inicio", "% correcto 1.ª semana"), ("correcto_final", "% correcto última semana"),
                ("mejora", "Mejora (puntos)")]
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow([titulo for _, titulo in columnas])
    for fila in datos["pacientes"]:
        escritor.writerow(["" if fila[c] is None else str(fila[c]).replace(".", ",") if isinstance(fila[c], float) else fila[c]
                           for c, _ in columnas])
    nombre = f"metricas_piloto_{datos['generado']}.csv"
    return Response("\ufeff" + salida.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _pdf_paciente(clinica_id, paciente_id):
    from informe_pdf import generar_informe
    historial = _historial_json(paciente_id)
    plan = database.obtener_plan(paciente_id)
    edad = next((e for pid, _, e in database.obtener_pacientes(clinica_id) if pid == paciente_id), None)
    return generar_informe({"nombre": database.obtener_nombre_paciente(paciente_id), "edad": edad},
                           database.nombre_clinica(clinica_id), historial, plan_de_hoy(plan, historial),
                           resumen_adherencia(plan, historial), metricas_paciente(plan, historial))


@app.get("/api/fisio/pacientes/{paciente_id}/informe.pdf")
async def fisio_informe_pdf(request: Request, paciente_id: int):
    fisio = _fisio(request)
    _paciente_de_mi_clinica(fisio, paciente_id)
    pdf = await run_in_threadpool(_pdf_paciente, fisio["clinica_id"], paciente_id)
    nombre = f"informe_{nombre_carpeta_paciente(database.obtener_nombre_paciente(paciente_id))}_{datetime.date.today()}.pdf"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}"'})


# ─── Invitaciones: el paciente crea su contraseña con un enlace o un QR ──────────

def _nueva_invitacion(request, paciente_id):
    codigo, caduca = database.crear_invitacion(paciente_id)
    return {"codigo": codigo, "caduca": caduca}


@app.post("/api/fisio/pacientes/{paciente_id}/invitacion")
async def fisio_invitacion(request: Request, paciente_id: int):
    """Genera (o regenera) la invitación de un paciente. Anula las anteriores y su contraseña sigue igual
    hasta que la use."""
    _paciente_de_mi_clinica(_fisio(request), paciente_id)
    return _nueva_invitacion(request, paciente_id)


@app.get("/api/fisio/qr.svg")
async def fisio_qr(request: Request, texto: str):
    import segno
    _fisio(request)
    salida = io.BytesIO()
    segno.make(texto, error="m").save(salida, kind="svg", scale=8, border=2, dark="#111", light="#fff")
    return Response(salida.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


@app.get("/api/invitacion/{codigo}")
async def ver_invitacion(codigo: str):
    datos = database.consultar_invitacion(codigo)
    if not datos:
        raise HTTPException(404, "La invitación no es válida o ha caducado. Pide a tu fisioterapeuta una nueva.")
    return {"nombre": datos[1], "clinica": database.nombre_clinica(database.clinica_de_paciente(datos[0]))}


@app.post("/api/invitacion/{codigo}")
async def usar_invitacion(request: Request, codigo: str):
    """El paciente elige su contraseña y entra directamente en la app."""
    d = await request.json()
    password = d.get("password") or ""
    if len(password) < 6:
        raise HTTPException(400, "La contraseña debe tener al menos 6 caracteres")
    if password != d.get("password2"):
        raise HTTPException(400, "Las contraseñas no coinciden")
    datos = database.usar_invitacion(codigo, password)
    if not datos:
        raise HTTPException(404, "La invitación no es válida o ha caducado. Pide a tu fisioterapeuta una nueva.")
    token = secrets.token_urlsafe(24)
    _SESIONES[token] = {"rol": "paciente", "id": datos[0], "nombre": datos[1]}
    return {"token": token, **_SESIONES[token], "consentimiento": _consentimiento_vigente(datos[0])}


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
    if not _consentimiento_vigente(usuario["id"]):
        # Sin consentimiento no se analiza ni se graba nada
        await ws.send_text(json.dumps({"estado": "error", "mensaje": "Antes de grabar tienes que aceptar el consentimiento"}))
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


@app.get("/privacidad")
async def privacidad():
    return FileResponse(os.path.join(CARPETA_WEB, "privacidad.html"), headers={"Cache-Control": "no-cache"})


@app.get("/salud")
async def salud():
    """Comprobación para el servidor en la nube (health check)."""
    return {"ok": True}


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
