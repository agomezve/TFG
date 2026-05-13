import sqlite3
import os
import datetime

# Ruta absoluta a la base de datos dentro del proyecto
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacientes.db")

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla de Pacientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            edad INTEGER,
            notas TEXT
        )
    ''')

    # Tabla de Sesiones/Informes
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

    conn.commit()
    conn.close()

def crear_paciente(nombre, edad=None, notas=""):
    """Crea un nuevo paciente y retorna su ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO pacientes (nombre, edad, notas) VALUES (?, ?, ?)', (nombre, edad, notas))
    conn.commit()
    paciente_id = cursor.lastrowid
    conn.close()
    exportar_bbdd_texto()
    return paciente_id

def obtener_pacientes():
    """Devuelve una lista de todos los pacientes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nombre, edad FROM pacientes ORDER BY nombre ASC')
    pacientes = cursor.fetchall()
    conn.close()
    return pacientes

def obtener_nombre_paciente(paciente_id):
    """Devuelve el nombre del paciente dado su ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nombre FROM pacientes WHERE id = ?', (paciente_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado[0] if resultado else "Invitado"

def guardar_sesion(paciente_id, ejercicio, nivel, repeticiones, errores, profundidad_media=None, observaciones=""):
    """Guarda una sesión de ejercicio en la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO sesiones (paciente_id, fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (paciente_id, fecha_actual, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones))
    conn.commit()
    conn.close()
    exportar_bbdd_texto()

def obtener_historial_paciente(paciente_id):
    """Devuelve las sesiones de un paciente específico."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones 
        FROM sesiones WHERE paciente_id = ? ORDER BY id DESC
    ''', (paciente_id,))
    historial = cursor.fetchall()
    conn.close()
    return historial

# Inicializar la base de datos cuando se importa el módulo
init_db()

def exportar_bbdd_texto():
    """Genera/Actualiza un archivo de texto con todo el contenido de la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, nombre, edad, notas FROM pacientes ORDER BY id ASC')
    pacientes = cursor.fetchall()
    
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
        
        cursor.execute('''
            SELECT fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones 
            FROM sesiones WHERE paciente_id = ? ORDER BY id ASC
        ''', (p_id,))
        sesiones = cursor.fetchall()
        
        if sesiones:
            lineas.append("    📖 Historial de Sesiones:")
            for idx, ses in enumerate(sesiones, 1):
                fecha, ejer, niv, reps, errs, prof, obs = ses
                prof_str = f"{prof:.1f}º" if prof else "N/A"
                lineas.append(f"       {idx}. [{fecha}] {ejer} ({niv.capitalize()}) -> {reps} reps ({errs} errores) | Ext/Flex media: {prof_str} | Obs: {obs}")
        else:
            lineas.append("    📖 Historial de Sesiones: Ninguna sesión registrada aún.")
        
        lineas.append("\n" + ("-"*60) + "\n")
        
    conn.close()
    
    txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_de_datos.txt")
    try:
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
    except IOError as e:
        print(f"Error escribiendo BBDD en texto: {e}")
