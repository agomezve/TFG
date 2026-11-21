"""Paso 2 de la demo estática: captura la API con datos ficticios y monta la web para GitHub Pages.

Arranca el servidor real (servidor_web.py) sobre la BBDD de demo que crea grabar_series_demo.py,
entra como fisio y como cada paciente, y guarda sus respuestas en demo/datos.json. demo.js las
sirve en el navegador en lugar del servidor, así que la app es exactamente la misma.

Uso (desde TFG_AGV/):
    TFG/bin/python despliegue/pages/construir_demo.py <carpeta_trabajo> <carpeta_web> [dominio]
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

TRABAJO = os.path.abspath(sys.argv[1])
WEB = os.path.abspath(sys.argv[2])
DOMINIO = sys.argv[3] if len(sys.argv) > 3 else "telerehabia.iaencrudo.es"
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
SERIES = os.path.join(TRABAJO, "series")
series = json.load(open(os.path.join(SERIES, "series.json"), encoding="utf-8"))

# Copia de los datos: la captura crea invitaciones y no debe tocar el original
DATOS = os.path.join(TRABAJO, "datos_captura")
shutil.rmtree(DATOS, ignore_errors=True)
shutil.copytree(os.path.join(TRABAJO, "datos"), DATOS)

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    PUERTO = s.getsockname()[1]
BASE = f"http://127.0.0.1:{PUERTO}"
servidor = subprocess.Popen([sys.executable, "servidor_web.py", "--puerto", str(PUERTO)], cwd=RAIZ,
                            env={**os.environ, "TELEREHAB_DATA_DIR": DATOS},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pedir(ruta, token=None, metodo="GET", cuerpo=None, crudo=False):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req) as r:
        contenido = r.read()
    return contenido if crudo else json.loads(contenido)


try:
    for _ in range(60):
        try:
            pedir("/salud")
            break
        except OSError:
            time.sleep(0.5)
    else:
        sys.exit("El servidor no arranca")

    shutil.rmtree(WEB, ignore_errors=True)
    os.makedirs(os.path.join(WEB, "demo", "series"))

    def guardar(ruta, contenido):
        destino = os.path.join(WEB, ruta)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(contenido)

    fisio = pedir("/api/login", metodo="POST", cuerpo={"usuario": "fisio", "password": "12345"})
    tf = fisio.pop("token")
    ejercicios = pedir("/api/ejercicios", tf)
    for e in ejercicios:  # en la web no van los originales (pesan mucho): todo con la versión ligera
        e["video_analisis"] = e["video"]

    lista = pedir("/api/fisio/pacientes", tf)
    historiales, series_fisio = {}, {}
    for p in lista:
        h = pedir(f"/api/fisio/pacientes/{p['id']}/historial", tf)
        historiales[p["id"]] = h
        guardar(f"api/fisio/pacientes/{p['id']}/informe.pdf",
                pedir(f"/api/fisio/pacientes/{p['id']}/informe.pdf", tf, crudo=True))
        # Informe y vídeo de cada serie (solo las grabadas hoy con el motor tienen vídeo e informe)
        por_dia = {}
        for s in reversed(h["sesiones"]):
            por_dia.setdefault(s["fecha"][:10], {}).setdefault(s["ejercicio"], []).append(s)
        for dia, por_ej in por_dia.items():
            for ej, ss in por_ej.items():
                for i, s in enumerate(ss):
                    q = urllib.parse.urlencode({"paciente_id": p["id"], "fecha": dia, "ejercicio": ej, "idx": i, "ts": s["fecha"]})
                    r = pedir(f"/api/fisio/serie?{q}", tf)
                    if r["informe"] or r["video"]:
                        video = None
                        if r["video"] and ej in series:
                            video = "/demo/series/" + series[ej]["video"]
                            if series[ej]["paciente"] == p["nombre"]:  # la serie grabada hoy con el motor
                                series[ej].update(informe=r["informe"], repeticiones=s["repeticiones"])
                        series_fisio[f"{p['id']}|{s['fecha']}"] = {"informe": r["informe"], "video": video}

    metricas = pedir("/api/fisio/metricas", tf)
    guardar("api/fisio/metricas.csv", pedir("/api/fisio/metricas.csv", tf, crudo=True))
    guardar("api/fisio/qr.svg", pedir("/api/fisio/qr.svg?" + urllib.parse.urlencode(
        {"texto": f"https://{DOMINIO}/#invitacion=demo"}), tf, crudo=True))

    # Formas «vacías» (paciente recién creado, sin plan ni series) para cuando el fisio da de alta uno
    nuevo = pedir("/api/fisio/pacientes", tf, "POST", {"nombre": "Paciente nuevo", "edad": "50"})
    vacio_lista = next(p for p in pedir("/api/fisio/pacientes", tf) if p["id"] == nuevo["id"])
    vacio_historial = pedir(f"/api/fisio/pacientes/{nuevo['id']}/historial", tf)

    pacientes = {}
    for p in lista:
        login = pedir("/api/login", metodo="POST", cuerpo={"usuario": p["nombre"], "password": "demo1234"})
        tp = login.pop("token")
        pacientes[p["nombre"].lower()] = {
            "login": login, "historial": pedir("/api/mi-historial", tp), "plan": pedir("/api/mi-plan", tp),
            "consentimiento": pedir("/api/consentimiento", tp)}
finally:
    servidor.terminate()

# Series en directo: vídeo ya analizado + línea temporal del marcador
for nombre, s in series.items():
    shutil.copy(os.path.join(SERIES, s["video"]), os.path.join(WEB, "demo", "series", s["video"]))
directo = {n: {"video": "/demo/series/" + s["video"], "linea": s["linea"], "resultado": s["resultado"],
               "informe": s.get("informe"), "repeticiones": s.get("repeticiones", 0)}
           for n, s in series.items()}

datos = {"generado": time.strftime("%Y-%m-%d"), "ejercicios": ejercicios,
         "fisio": {"login": fisio, "pacientes": lista, "historiales": historiales, "metricas": metricas},
         "pacientes": pacientes, "series": series_fisio, "directo": directo,
         "vacio": {"lista": vacio_lista, "historial": vacio_historial}}
with open(os.path.join(WEB, "demo", "datos.json"), "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))

# La app tal cual + demo.js (se carga antes que app.js)
CW = os.path.join(RAIZ, "web")
os.makedirs(os.path.join(WEB, "static"))
for f in os.listdir(CW):
    if f not in ("index.html", "sw.js", "manifest.webmanifest", "privacidad.html"):
        shutil.copy(os.path.join(CW, f), os.path.join(WEB, "static", f))
shutil.copy(os.path.join(AQUI, "demo.js"), os.path.join(WEB, "static", "demo.js"))
html = open(os.path.join(CW, "index.html"), encoding="utf-8").read()
html = html.replace('<script src="/static/app.js"></script>',
                    '<script src="/static/demo.js"></script>\n  <script src="/static/app.js"></script>')
html = html.replace("<title>", '<meta name="robots" content="noindex">\n  <title>', 1)
open(os.path.join(WEB, "index.html"), "w", encoding="utf-8").write(html)
os.makedirs(os.path.join(WEB, "privacidad"))
shutil.copy(os.path.join(CW, "privacidad.html"), os.path.join(WEB, "privacidad", "index.html"))
for f in ("sw.js", "manifest.webmanifest"):
    shutil.copy(os.path.join(CW, f), os.path.join(WEB, f))
for carpeta in ("web", "portadas"):
    shutil.copytree(os.path.join(RAIZ, "videos_explicativos", carpeta), os.path.join(WEB, "videos_explicativos", carpeta))
open(os.path.join(WEB, "CNAME"), "w").write(DOMINIO + "\n")
open(os.path.join(WEB, ".nojekyll"), "w").close()
open(os.path.join(WEB, "404.html"), "w", encoding="utf-8").write(html)
open(os.path.join(WEB, "README.md"), "w", encoding="utf-8").write(
    f"# TeleRehab IA · demo\n\nDemo pública en https://{DOMINIO} con pacientes **ficticios**. "
    "El análisis con cámara en directo necesita el servidor; aquí se reproducen series ya analizadas "
    "por el mismo motor (MediaPipe).\n\nGenerada con `despliegue/pages/` del repositorio del TFG.\n")
print("Web lista en", WEB)
