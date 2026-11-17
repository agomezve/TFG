"""Tests unitarios rápidos: geometría, seguridad, base de datos y catálogo de ejercicios.

Ejecutar todos los tests:  python -m unittest discover -s tests -v
"""
import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class TestAngulos(unittest.TestCase):
    def setUp(self):
        from modulos.modulo_sentadilla import ModuloSentadilla
        self.ej = ModuloSentadilla()

    def test_angulo_recto(self):
        self.assertAlmostEqual(self.ej.calcular_angulo_3d([1, 0, 0], [0, 0, 0], [0, 1, 0]), 90.0, places=5)

    def test_angulo_llano(self):
        self.assertAlmostEqual(self.ej.calcular_angulo_3d([-1, 0, 0], [0, 0, 0], [1, 0, 0]), 180.0, places=5)

    def test_angulo_en_3d(self):
        self.assertAlmostEqual(self.ej.calcular_angulo_3d([1, 0, 0], [0, 0, 0], [1, 1, 0]), 45.0, places=5)
        self.assertAlmostEqual(self.ej.calcular_angulo_3d([0, 0, 2], [0, 0, 0], [0, 3, 0]), 90.0, places=5)


class TestSeguridad(unittest.TestCase):
    def test_hash_y_verificacion(self):
        from seguridad import generar_hash, verificar_hash
        h = generar_hash("secreto123")
        self.assertNotIn("secreto123", h)
        self.assertTrue(verificar_hash("secreto123", h))
        self.assertFalse(verificar_hash("otra", h))

    def test_sal_distinta(self):
        from seguridad import generar_hash
        self.assertNotEqual(generar_hash("abc"), generar_hash("abc"))

    def test_hash_corrupto(self):
        from seguridad import verificar_hash
        self.assertFalse(verificar_hash("abc", "basura"))
        self.assertFalse(verificar_hash("abc", None))


class TestBaseDeDatos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entorno = mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": self.tmp.name})
        self.entorno.start()
        import database
        self.db = importlib.reload(database)

    def tearDown(self):
        self.entorno.stop()
        self.tmp.cleanup()

    def test_datos_en_carpeta_configurada(self):
        self.assertEqual(self.db.DB_PATH, os.path.join(self.tmp.name, "pacientes.db"))
        self.assertTrue(os.path.exists(self.db.DB_PATH))

    def test_crear_y_guardar_sesion(self):
        pid = self.db.crear_paciente("Lucía", 70, "Prótesis de rodilla", password="clave123")
        self.db.guardar_sesion(pid, "Sentadilla", "principiante", 10, 2, 105.5)
        historial = self.db.obtener_historial_paciente(pid)
        self.assertEqual(historial[0][1:6], ("Sentadilla", "principiante", 10, 2, 105.5))
        self.assertEqual(self.db.obtener_nombre_paciente(pid), "Lucía")
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "base_de_datos.txt")))

    def test_login_fisio(self):
        self.assertEqual(self.db.autenticar("fisio", "12345"), ("fisio", None))
        self.assertEqual(self.db.autenticar("FISIO", "mala")[0], None)
        self.db.cambiar_password_fisio("nuevaclave")
        self.assertIsNone(self.db.autenticar("fisio", "12345")[0])
        self.assertEqual(self.db.autenticar("fisio", "nuevaclave")[0], "fisio")

    def test_login_paciente_con_password_propia(self):
        pid = self.db.crear_paciente("Pedro", password="pedro2026")
        self.assertEqual(self.db.autenticar("pedro", "pedro2026"), ("paciente", (pid, "Pedro")))
        self.assertEqual(self.db.autenticar("Pedro", "12345"), (None, "Contraseña incorrecta"))

    def test_login_paciente_antiguo_sigue_funcionando(self):
        pid = self.db.crear_paciente("Marta")  # sin contraseña, como en la versión del TFG
        self.assertEqual(self.db.autenticar("marta", "12345"), ("paciente", (pid, "Marta")))
        self.assertEqual(self.db.autenticar("marta", "otra")[0], None)

    def test_errores_de_login(self):
        self.assertEqual(self.db.autenticar("", ""), (None, "Por favor, rellene todos los campos"))
        self.assertEqual(self.db.autenticar("nadie", "12345"), (None, "Usuario no registrado"))

    def test_migracion_bbdd_antigua(self):
        # Simula la BBDD de la versión del TFG (sin columna password_hash ni tabla ajustes)
        ruta = os.path.join(self.tmp.name, "antigua")
        os.makedirs(ruta)
        conn = sqlite3.connect(os.path.join(ruta, "pacientes.db"))
        conn.execute("CREATE TABLE pacientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, edad INTEGER, notas TEXT)")
        conn.execute("INSERT INTO pacientes (nombre) VALUES ('Aaron')")
        conn.commit()
        conn.close()
        with mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": ruta}):
            db = importlib.reload(self.db)
            self.assertEqual(db.autenticar("aaron", "12345")[0], "paciente")
            self.assertEqual(db.autenticar("fisio", "12345")[0], "fisio")


class TestCatalogo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importar la interfaz inicializa la BBDD: que sea siempre una temporal.
        cls.tmp = tempfile.TemporaryDirectory()
        cls.entorno = mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": cls.tmp.name})
        cls.entorno.start()

    @classmethod
    def tearDownClass(cls):
        cls.entorno.stop()
        cls.tmp.cleanup()

    def test_todos_los_ejercicios_tienen_modulo_video_y_consejos(self):
        import ejercicios
        from pantalla_principal import AppRehabilitacion
        self.assertEqual(len(ejercicios.CATALOGO), 10)
        for e in ejercicios.CATALOGO:
            with self.subTest(ejercicio=e.nombre):
                modulo = ejercicios.crear_modulo(e.nombre, "principiante")
                self.assertTrue(modulo.obtener_landmarks_relevantes())
                self.assertIn(e.nombre, AppRehabilitacion.CONSEJOS_EJERCICIO)
                self.assertTrue(os.path.exists(os.path.join(RAIZ, "videos_explicativos", e.video_explicativo)))

    def test_carpeta_informes_coincide_con_la_del_modulo(self):
        # El panel del fisio busca los informes en esta carpeta: debe ser la que usa cada módulo.
        import inspect
        import ejercicios
        for e in ejercicios.CATALOGO:
            codigo = inspect.getsource(e.clase.generar_informe_clinico)
            with self.subTest(ejercicio=e.nombre):
                self.assertIn(f'"{e.carpeta_informes}"', codigo)

    def test_nombre_carpeta_paciente(self):
        from config import nombre_carpeta_paciente
        self.assertEqual(nombre_carpeta_paciente("Ana María  "), "ana_maría")
        self.assertEqual(nombre_carpeta_paciente("../x"), "x")


if __name__ == "__main__":
    unittest.main()
