"""Paso 1 de la demo estática: crea los datos ficticios y graba series ya analizadas.

Ejecuta el motor de análisis real (motor.SesionEjercicio, el mismo que usa /ws/serie)
sobre los vídeos explicativos, como si el paciente pulsara «Probar con el vídeo de ejemplo».
Por cada ejercicio guarda:
  - la serie en la BBDD de demo (informe + vídeo), para que el fisio la vea en el historial
  - el vídeo con el esqueleto dibujado y la línea temporal del marcador, para reproducirla
    en la web estática (GitHub Pages no puede ejecutar MediaPipe)

Solo pacientes FICTICIOS (Carmen, Julian, Lucia). Nada de esto sale de datos reales.

Uso (desde TFG_AGV/):  TFG/bin/python despliegue/pages/grabar_series_demo.py <carpeta_trabajo>
"""
import json
import os
import shutil
import subprocess
import sys
import time

TRABAJO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.cache/telerehab-demo"))
DATOS = os.path.join(TRABAJO, "datos")
SERIES = os.path.join(TRABAJO, "series")
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

shutil.rmtree(TRABAJO, ignore_errors=True)
os.makedirs(SERIES)
os.environ["TELEREHAB_DATA_DIR"] = DATOS
subprocess.run([sys.executable, os.path.join(RAIZ, "scripts", "crear_datos_demo.py")], check=True)

# Reloj simulado: el análisis va fotograma a fotograma, más lento o más rápido que el tiempo real.
# Así la cuenta atrás de preparación y los ejercicios por tiempo (plancha) duran lo que el vídeo.
_reloj = [time.time()]
time.time = lambda: _reloj[0]

sys.path.insert(0, RAIZ)
import cv2  # noqa: E402
import database  # noqa: E402
import ejercicios  # noqa: E402
import motor  # noqa: E402

database.init_db()
database.renombrar_clinica(1, "Clínica demo TeleRehab")
PLANES = {
    "Carmen": [("Sentadilla", "principiante", 2, 5), ("Propiocepcion", "principiante", 2, 5)],
    "Julian": [("Press Militar", "principiante", 3, 3), ("Hombros Laterales", "principiante", 3, 3)],
    "Lucia": [("Bulgaras", "intermedio", 3, 3), ("Zancadas", "intermedio", 3, 3), ("Plancha", "intermedio", 2, 3)],
}
pacientes = {nombre: pid for pid, nombre, _ in database.obtener_pacientes(1)}
for nombre, plan in PLANES.items():
    database.guardar_plan(pacientes[nombre], [{"ejercicio": e, "nivel": n, "series": s, "dias_semana": d}
                                             for e, n, s, d in plan])
# Cada ejercicio se graba para el paciente que lo tiene pautado (los demás, para Lucia)
DUENO = {e: (nombre, n) for nombre, plan in PLANES.items() for e, n, _, _ in plan}

FPS = 15.0  # ritmo al que el móvil manda fotogramas al servidor
resumen = {}
for ej in ejercicios.CATALOGO:
    nombre_pac, nivel = DUENO.get(ej.nombre, ("Lucia", "intermedio"))
    pid = pacientes[nombre_pac]
    cap = cv2.VideoCapture(os.path.join(RAIZ, "videos_explicativos", ej.video_explicativo))
    paso = max(1, round((cap.get(cv2.CAP_PROP_FPS) or 30) / FPS))
    sesion = motor.SesionEjercicio(ej.nombre, nivel, pid, nombre_pac, grabar=True, fps_grabacion=FPS)
    linea, estado, n = [], "en_curso", 0
    while estado == "en_curso":
        ok, frame = cap.read()
        if not ok:
            estado = "detenido"
            break
        n += 1
        if (n - 1) % paso:
            continue
        escala = min(1.0, 720 / frame.shape[1])
        if escala < 1:
            frame = cv2.resize(frame, (round(frame.shape[1] * escala), round(frame.shape[0] * escala)))
        estado = sesion.procesar(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        m = sesion.marcador()
        linea.append([round(len(linea) / FPS, 3), m["errores"], int(m["persona_detectada"]), estado])
        _reloj[0] += 1 / FPS
    cap.release()
    sesion.finalizar()

    # Vídeo ligero para la web (H.264, faststart) a partir de la grabación de la serie
    destino = os.path.join(SERIES, ej.video_explicativo)
    origen = sesion.ruta_video_actual.replace(".avi", ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", origen, "-an", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "28", "-pix_fmt", "yuv420p", "-movflags", "+faststart", destino], check=True)
    # Compactar la línea temporal: solo los instantes en que cambia algo
    compacta = [p for i, p in enumerate(linea) if i == 0 or p[1:] != linea[i - 1][1:]]
    resumen[ej.nombre] = {"paciente": nombre_pac, "nivel": nivel, "resultado": estado,
                          "video": os.path.basename(destino), "duracion": round(len(linea) / FPS, 2),
                          "ruta_grabacion": os.path.relpath(origen, DATOS), "linea": compacta}
    print(f"{ej.nombre:18} {nombre_pac:7} {estado:12} {len(linea) / FPS:5.1f} s  errores={linea[-1][1] if linea else 0}")

with open(os.path.join(SERIES, "series.json"), "w", encoding="utf-8") as f:
    json.dump(resumen, f, ensure_ascii=False, indent=1)
print("Series listas en", SERIES)
