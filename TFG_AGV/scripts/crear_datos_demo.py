"""Crea una base de datos de DEMOSTRACIÓN con pacientes ficticios y 6 semanas de sesiones.

Útil para enseñar la plataforma (por ejemplo, en la presentación a Wolaria) sin usar
datos reales. Los datos se guardan en la carpeta `datos_demo/` (ignorada por git).

Uso:
    python scripts/crear_datos_demo.py
    TELEREHAB_DATA_DIR=datos_demo python pantalla_principal.py      (macOS / Linux)
    set TELEREHAB_DATA_DIR=datos_demo && python pantalla_principal.py (Windows)

Usuarios: fisio / 12345   ·   carmen, julian, lucia / demo1234
"""
import datetime
import os
import random
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("TELEREHAB_DATA_DIR", os.path.join(RAIZ, "datos_demo"))

if os.path.exists(os.path.join(os.environ["TELEREHAB_DATA_DIR"], "pacientes.db")):
    sys.exit(f"Ya existe una BBDD en {os.environ['TELEREHAB_DATA_DIR']}. Bórrala si quieres regenerarla.")

import database  # noqa: E402  (se inicializa en la carpeta de demo)

PACIENTES = [
    # nombre, edad, notas, [(ejercicio, nivel, reps objetivo)], errores iniciales -> finales
    ("Carmen", 71, "Prótesis total de rodilla derecha (postoperatorio, semana 4)",
     [("Sentadilla", "principiante", 10), ("Propiocepcion", "principiante", 20)], 4, 0),
    ("Julian", 45, "Tendinopatía del manguito rotador",
     [("Press Militar", "principiante", 10), ("Hombros Laterales", "principiante", 10)], 5, 1),
    ("Lucia", 28, "Readaptación tras rotura de LCA (fase de fuerza)",
     [("Bulgaras", "intermedio", 10), ("Zancadas", "intermedio", 10), ("Plancha", "intermedio", 40)], 3, 0),
]

random.seed(7)
hoy = datetime.date.today()
for nombre, edad, notas, plan, err_ini, err_fin in PACIENTES:
    pid = database.crear_paciente(nombre, edad, notas, password="demo1234")
    conn = sqlite3.connect(database.DB_PATH)
    for dia in range(42, 0, -1):
        if random.random() > 0.55:  # ~3 sesiones por semana
            continue
        fecha = hoy - datetime.timedelta(days=dia)
        progreso = 1 - dia / 42
        for ejercicio, nivel, objetivo in plan:
            for serie in range(3):
                errores = max(0, round(err_ini + (err_fin - err_ini) * progreso + random.uniform(-1, 1)))
                errores = min(errores, 2)  # el cortafuegos corta la serie al 3er error
                hora = datetime.time(18, 5 + serie * 4, random.randint(0, 59))
                conn.execute(
                    "INSERT INTO sesiones (paciente_id, fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, '')",
                    (pid, f"{fecha} {hora}", ejercicio, nivel, objetivo, errores,
                     round(random.uniform(95, 130), 1)))
    conn.commit()
    conn.close()

database.exportar_bbdd_texto()
print(f"Datos de demostración creados en {os.environ['TELEREHAB_DATA_DIR']}")
