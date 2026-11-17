"""Crea un ENTORNO DE PRUEBAS completo en `datos_prueba/` (ignorada por git).

Junta en una sola carpeta:
  - los pacientes ficticios de `datos_demo/` (Carmen, Julian, Lucia), con su historial;
  - el perfil real de Aaron: todas sus sesiones de `pacientes.db` y todos sus
    informes y vídeos de `usuarios/aaron/`.

Los datos reales originales no se tocan: solo se copian.
Las contraseñas de Aaron y del fisio se generan al azar (el entorno está pensado para
abrirse desde internet) y se guardan en `datos_prueba/CREDENCIALES.txt`.

Uso:
    python scripts/crear_datos_demo.py          (si no existe datos_demo/)
    python scripts/crear_entorno_pruebas.py
    TELEREHAB_DATA_DIR=datos_prueba python servidor_web.py
"""
import os
import secrets
import shutil
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN_REAL = RAIZ
ORIGEN_DEMO = os.path.join(RAIZ, "datos_demo")
DESTINO = os.path.join(RAIZ, "datos_prueba")
PERFIL = "Aaron"

if os.path.exists(DESTINO):
    sys.exit(f"Ya existe {DESTINO}. Bórrala si quieres regenerarla.")
if not os.path.exists(os.path.join(ORIGEN_DEMO, "pacientes.db")):
    sys.exit("Falta datos_demo/. Ejecuta antes scripts/crear_datos_demo.py")

# 1) Partimos de una copia de la demo.
shutil.copytree(ORIGEN_DEMO, DESTINO)

sys.path.insert(0, RAIZ)
os.environ["TELEREHAB_DATA_DIR"] = DESTINO
import config  # noqa: E402
import database  # noqa: E402

database.init_db()

# 2) Copiamos el paciente real y todas sus sesiones.
real = sqlite3.connect(os.path.join(ORIGEN_REAL, "pacientes.db"))
fila = real.execute("SELECT id, edad, notas FROM pacientes WHERE lower(nombre) = lower(?) ORDER BY id LIMIT 1",
                    (PERFIL,)).fetchone()
if not fila:
    sys.exit(f"No hay ningún paciente {PERFIL} en pacientes.db")
id_real, edad, notas = fila
sesiones = real.execute(
    "SELECT fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones"
    " FROM sesiones WHERE paciente_id = ? ORDER BY fecha", (id_real,)).fetchall()
real.close()

pass_paciente = secrets.token_urlsafe(6)
pass_fisio = secrets.token_urlsafe(6)

nuevo_id = database.crear_paciente(PERFIL, edad, notas or "Perfil de pruebas con sus sesiones y vídeos reales",
                                   password=pass_paciente)
conn = sqlite3.connect(config.ruta_bbdd())
conn.executemany(
    "INSERT INTO sesiones (paciente_id, fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(nuevo_id, *s) for s in sesiones])
conn.commit()
conn.close()
database.cambiar_password_fisio(pass_fisio)

# 3) Copiamos sus informes y vídeos.
carpeta = config.nombre_carpeta_paciente(PERFIL)
shutil.copytree(os.path.join(ORIGEN_REAL, "usuarios", carpeta), os.path.join(DESTINO, "usuarios", carpeta),
                ignore=shutil.ignore_patterns(".DS_Store"))

database.exportar_bbdd_texto()

# 4) Planes recetados de ejemplo y consentimiento de los pacientes ficticios
#    (Aaron no lo tiene aceptado: así, al entrar, se ve la pantalla de consentimiento).
PLANES = {
    "Carmen": [("Sentadilla", "principiante", 3, 5), ("Propiocepcion", "principiante", 2, 5)],
    "Julian": [("Press Militar", "principiante", 3, 3), ("Hombros Laterales", "principiante", 3, 3)],
    "Lucia": [("Bulgaras", "intermedio", 3, 3), ("Zancadas", "intermedio", 3, 3), ("Plancha", "intermedio", 2, 3)],
    PERFIL: [("Press Militar", "intermedio", 3, 3), ("Sentadilla", "intermedio", 3, 3), ("Peso Muerto", "intermedio", 3, 2)],
}
for pid, nombre, _ in database.obtener_pacientes():
    if nombre in PLANES:
        database.guardar_plan(pid, [{"ejercicio": e, "nivel": n, "series": s, "dias_semana": d}
                                    for e, n, s, d in PLANES[nombre]])
    if nombre != PERFIL:
        database.registrar_consentimiento(pid, "2026-11")

with open(os.path.join(DESTINO, "CREDENCIALES.txt"), "w", encoding="utf-8") as f:
    f.write(f"Paciente {PERFIL}: usuario {PERFIL} / contraseña {pass_paciente}\n")
    f.write(f"Fisioterapeuta: usuario fisio / contraseña {pass_fisio}\n")
    f.write("Pacientes demo: Carmen, Julian, Lucia / contraseña demo1234\n")

print(f"Entorno de pruebas creado en {DESTINO}: {len(sesiones)} sesiones de {PERFIL}.")
print(f"Credenciales en {os.path.join(DESTINO, 'CREDENCIALES.txt')}")
