"""Capa de datos (SQLite) de la plataforma de telerehabilitación.

Mantiene exactamente la misma API pública que antes (crear_paciente, obtener_pacientes,
guardar_sesion, obtener_historial_paciente...) y añade:
  - contraseñas por usuario guardadas con hash seguro (PBKDF2, nunca en texto plano),
  - migración automática de bases de datos antiguas (no se pierde ningún dato),
  - ruta de la BBDD configurable (ver config.py).
"""
import contextlib
import datetime
import os
import sqlite3

from config import directorio_datos, ruta_bbdd
from seguridad import generar_hash, verificar_hash

# Contraseña que tenían todos los usuarios en la versión del TFG. Se sigue aceptando
# para los pacientes que todavía no tienen una contraseña propia, así nada deja de funcionar.
CONTRASENA_INICIAL = "12345"
USUARIO_FISIO = "fisio"


def __getattr__(nombre):
    # Compatibilidad: antes existía la constante DB_PATH.
    if nombre == "DB_PATH":
        return ruta_bbdd()
    raise AttributeError(nombre)


@contextlib.contextmanager
def _conexion():
    os.makedirs(directorio_datos(), exist_ok=True)
    conn = sqlite3.connect(ruta_bbdd())
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Inicializa la base de datos, crea las tablas si no existen y migra las antiguas."""
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                edad INTEGER,
                notas TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paciente_id INTEGER,
                fecha TEXT NOT NULL,
                ejercicio TEXT NOT NULL,
                nivel TEXT NOT NULL,
                repeticiones INTEGER,
                errores INTEGER,
                profundidad_media REAL,
                observaciones TEXT,
                FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ajustes (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        ''')

        # Migración: columna de contraseña (las BBDD del TFG no la tenían)
        columnas = [fila[1] for fila in cursor.execute("PRAGMA table_info(pacientes)")]
        if "password_hash" not in columnas:
            cursor.execute("ALTER TABLE pacientes ADD COLUMN password_hash TEXT")

        # Contraseña del fisioterapeuta: se crea con la de siempre y se puede cambiar desde la app
        existe = cursor.execute("SELECT 1 FROM ajustes WHERE clave = 'fisio_password_hash'").fetchone()
        if not existe:
            cursor.execute("INSERT INTO ajustes (clave, valor) VALUES (?, ?)",
                           ("fisio_password_hash", generar_hash(CONTRASENA_INICIAL)))


def crear_paciente(nombre, edad=None, notas="", password=None):
    """Crea un nuevo paciente y retorna su ID. Si se indica contraseña, se guarda con hash."""
    password_hash = generar_hash(password) if password else None
    with _conexion() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO pacientes (nombre, edad, notas, password_hash) VALUES (?, ?, ?, ?)',
                       (nombre, edad, notas, password_hash))
        paciente_id = cursor.lastrowid
    exportar_bbdd_texto()
    return paciente_id


def obtener_pacientes():
    """Devuelve una lista de todos los pacientes: (id, nombre, edad)."""
    with _conexion() as conn:
        return conn.execute('SELECT id, nombre, edad FROM pacientes ORDER BY nombre ASC').fetchall()


def obtener_nombre_paciente(paciente_id):
    """Devuelve el nombre del paciente dado su ID."""
    with _conexion() as conn:
        resultado = conn.execute('SELECT nombre FROM pacientes WHERE id = ?', (paciente_id,)).fetchone()
    return resultado[0] if resultado else "Invitado"


def existe_paciente(nombre):
    """True si ya hay un paciente con ese nombre (sin distinguir mayúsculas)."""
    with _conexion() as conn:
        fila = conn.execute('SELECT 1 FROM pacientes WHERE lower(nombre) = lower(?)', (nombre.strip(),)).fetchone()
    return fila is not None


def guardar_sesion(paciente_id, ejercicio, nivel, repeticiones, errores, profundidad_media=None, observaciones=""):
    """Guarda una sesión de ejercicio en la base de datos."""
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conexion() as conn:
        conn.execute('''
            INSERT INTO sesiones (paciente_id, fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (paciente_id, fecha_actual, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones))
    exportar_bbdd_texto()


def obtener_historial_paciente(paciente_id):
    """Devuelve las sesiones de un paciente específico (la más reciente primero)."""
    with _conexion() as conn:
        return conn.execute('''
            SELECT fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones
            FROM sesiones WHERE paciente_id = ? ORDER BY id DESC
        ''', (paciente_id,)).fetchall()


# ──────────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def autenticar(usuario, password):
    """Comprueba las credenciales introducidas en el login.

    Devuelve una tupla (rol, datos):
      ("fisio", None)                  -> acceso al panel del fisioterapeuta
      ("paciente", (id, nombre))       -> acceso del paciente
      (None, "mensaje de error")       -> credenciales no válidas
    """
    usuario = (usuario or "").strip()
    password = (password or "").strip()
    if not usuario or not password:
        return None, "Por favor, rellene todos los campos"

    with _conexion() as conn:
        if usuario.lower() == USUARIO_FISIO:
            fila = conn.execute("SELECT valor FROM ajustes WHERE clave = 'fisio_password_hash'").fetchone()
            if fila and verificar_hash(password, fila[0]):
                return "fisio", None
            return None, "Contraseña incorrecta"

        paciente = conn.execute(
            "SELECT id, nombre, password_hash FROM pacientes WHERE lower(nombre) = lower(?) ORDER BY id LIMIT 1",
            (usuario,)).fetchone()

    if paciente is None:
        return None, "Usuario no registrado"
    paciente_id, nombre, password_hash = paciente
    valida = verificar_hash(password, password_hash) if password_hash else password == CONTRASENA_INICIAL
    if not valida:
        return None, "Contraseña incorrecta"
    return "paciente", (paciente_id, nombre)


def cambiar_password_paciente(paciente_id, nueva_password):
    with _conexion() as conn:
        conn.execute("UPDATE pacientes SET password_hash = ? WHERE id = ?", (generar_hash(nueva_password), paciente_id))


def cambiar_password_fisio(nueva_password):
    with _conexion() as conn:
        conn.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES ('fisio_password_hash', ?)",
                     (generar_hash(nueva_password),))


# ──────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN
# ──────────────────────────────────────────────────────────────────────────────

def exportar_bbdd_texto():
    """Genera/Actualiza un archivo de texto con todo el contenido de la base de datos."""
    with _conexion() as conn:
        cursor = conn.cursor()
        pacientes = cursor.execute('SELECT id, nombre, edad, notas FROM pacientes ORDER BY id ASC').fetchall()

        lineas = []
        lineas.append("==================================================")
        lineas.append("        REGISTRO GLOBAL DE PACIENTES Y SESIONES")
        lineas.append(f"        Última actualización: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas.append("==================================================\n")

        for pac in pacientes:
            p_id, p_nombre, p_edad, p_notas = pac
            lineas.append(f"👤 PACIENTE #{p_id}: {p_nombre.upper()}")
            lineas.append(f"    - Edad: {p_edad if p_edad else 'N/A'}")
            lineas.append(f"    - Riesgos/Notas: {p_notas if p_notas else 'Vacío'}")

            sesiones = cursor.execute('''
                SELECT fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones
                FROM sesiones WHERE paciente_id = ? ORDER BY id ASC
            ''', (p_id,)).fetchall()

            if sesiones:
                lineas.append("    📖 Historial de Sesiones:")
                for idx, ses in enumerate(sesiones, 1):
                    fecha, ejer, niv, reps, errs, prof, obs = ses
                    prof_str = f"{prof:.1f}º" if prof else "N/A"
                    lineas.append(f"       {idx}. [{fecha}] {ejer} ({niv.capitalize()}) -> {reps} reps ({errs} errores) | Ext/Flex media: {prof_str} | Obs: {obs}")
            else:
                lineas.append("    📖 Historial de Sesiones: Ninguna sesión registrada aún.")

            lineas.append("\n" + ("-" * 60) + "\n")

    txt_path = os.path.join(directorio_datos(), "base_de_datos.txt")
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
    except IOError as e:
        print(f"Error escribiendo BBDD en texto: {e}")


# Inicializar la base de datos cuando se importa el módulo
init_db()
