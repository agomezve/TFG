"""Tests de varias clínicas, invitaciones, métricas del piloto e informe PDF."""
import datetime
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

from metricas import metricas_clinica, metricas_paciente  # noqa: E402

HOY = datetime.date(2026, 11, 17)


def serie(dias_atras, reps=10, errores=0, ejercicio="Sentadilla"):
    return {"fecha": f"{HOY - datetime.timedelta(days=dias_atras)} 18:00:00", "ejercicio": ejercicio, "nivel": "principiante",
            "repeticiones": reps, "errores": errores, "profundidad_media": None, "observaciones": ""}


class TestMetricas(unittest.TestCase):
    PLAN = [{"ejercicio": "Sentadilla", "nivel": "principiante", "series": 1, "dias_semana": 3}]

    def test_mejora_entre_primera_y_ultima_semana(self):
        hist = [serie(0, errores=1), serie(2, errores=1), serie(20, errores=5), serie(18, errores=5)]
        m = metricas_paciente(self.PLAN, hist, HOY)
        self.assertEqual((m["correcto_inicio"], m["correcto_final"], m["mejora"]), (50, 90, 40))
        self.assertEqual((m["series"], m["dias_activos"], m["series_7d"]), (4, 4, 2))

    def test_sin_comparacion_con_menos_de_dos_semanas(self):
        m = metricas_paciente(self.PLAN, [serie(0), serie(5)], HOY)
        self.assertIsNone(m["mejora"])

    def test_paciente_sin_sesiones(self):
        m = metricas_paciente([], [], HOY)
        self.assertEqual(m["series"], 0)
        self.assertIsNone(m["dias_por_semana"])

    def test_resumen_de_clinica(self):
        a = metricas_paciente(self.PLAN, [serie(0, errores=1), serie(20, errores=5)], HOY)
        b = metricas_paciente([], [], HOY)
        r = metricas_clinica([a, b])
        self.assertEqual((r["pacientes"], r["pacientes_activos"], r["series_totales"]), (2, 1, 2))
        self.assertEqual((r["pacientes_mejoran"], r["pacientes_comparables"]), (1, 1))


class TestClinicasEInvitaciones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entorno = mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": self.tmp.name})
        self.entorno.start()
        import database
        self.db = importlib.reload(database)

    def tearDown(self):
        self.entorno.stop()
        self.tmp.cleanup()

    def test_bbdd_antigua_queda_en_la_clinica_principal(self):
        self.db.crear_paciente("Ana", None, "", password="secreta1")
        con = sqlite3.connect(self.db.DB_PATH)
        self.assertEqual(con.execute("SELECT clinica_id FROM pacientes").fetchone()[0], 1)
        con.close()
        self.db.init_db()  # la migración se puede repetir sin errores
        self.assertEqual(self.db.autenticar("fisio", "12345"), ("fisio", None))

    def test_cada_clinica_ve_solo_sus_pacientes(self):
        c2 = self.db.crear_clinica("Fisio Salamanca")
        self.db.crear_fisio("laura", "secreta1", c2, "Laura")
        self.db.crear_paciente("Ana", None, "", password="secreta1")
        self.db.crear_paciente("Luis", None, "", password="secreta1", clinica_id=c2)
        self.assertEqual([n for _, n, _ in self.db.obtener_pacientes(1)], ["Ana"])
        self.assertEqual([n for _, n, _ in self.db.obtener_pacientes(c2)], ["Luis"])
        rol, info = self.db.autenticar("Laura", "secreta1")  # sin distinguir mayúsculas
        self.assertEqual((rol, info["clinica_id"], info["nombre"]), ("fisio", c2, "Laura"))
        self.assertEqual(self.db.autenticar("laura", "mala")[0], None)

    def test_usuario_de_fisio_no_puede_repetirse(self):
        self.db.crear_paciente("Ana", None, "", password="secreta1")
        for usuario in ("fisio", "Ana"):
            with self.assertRaises(ValueError):
                self.db.crear_fisio(usuario, "secreta1", 1)
        self.db.crear_fisio("laura", "secreta1", 1)
        with self.assertRaises(ValueError):
            self.db.crear_fisio("LAURA", "secreta1", 1)

    def test_cambiar_password_de_fisio_de_clinica(self):
        fid = self.db.crear_fisio("laura", "secreta1", 1)
        self.db.cambiar_password_fisio("nueva123", fid)
        self.assertEqual(self.db.autenticar("laura", "nueva123")[0], "fisio")
        self.assertEqual(self.db.autenticar("fisio", "12345"), ("fisio", None))  # el fisio de siempre no cambia

    def test_invitacion_de_un_solo_uso(self):
        pid = self.db.crear_paciente("Ana", None, "", password="aleatoria-que-nadie-sabe")
        viejo, _ = self.db.crear_invitacion(pid)
        codigo, _ = self.db.crear_invitacion(pid)
        self.assertIsNone(self.db.consultar_invitacion(viejo))  # la nueva anula la anterior
        self.assertEqual(self.db.consultar_invitacion(codigo), (pid, "Ana"))
        self.assertEqual(self.db.usar_invitacion(codigo, "mia1234"), (pid, "Ana"))
        self.assertEqual(self.db.autenticar("Ana", "mia1234")[0], "paciente")
        self.assertIsNone(self.db.usar_invitacion(codigo, "otra123"))  # ya no vale

    def test_invitacion_caducada(self):
        pid = self.db.crear_paciente("Ana", None, "", password="x" * 10)
        codigo, _ = self.db.crear_invitacion(pid, dias_validez=-1)
        self.assertIsNone(self.db.consultar_invitacion(codigo))

    def test_solo_se_guarda_el_hash_del_codigo(self):
        pid = self.db.crear_paciente("Ana", None, "", password="x" * 10)
        codigo, _ = self.db.crear_invitacion(pid)
        con = sqlite3.connect(self.db.DB_PATH)
        guardado = con.execute("SELECT codigo_hash FROM invitaciones").fetchone()[0]
        con.close()
        self.assertNotEqual(guardado, codigo)

    def test_informe_pdf(self):
        from informe_pdf import generar_informe
        from adherencia import plan_de_hoy, resumen_adherencia
        plan = [{"ejercicio": "Sentadilla", "nivel": "principiante", "series": 2, "dias_semana": 3, "actualizado": None}]
        hist = [serie(d, errores=d % 3, ejercicio=e) for d in range(0, 30, 2) for e in ("Sentadilla", "Plancha")]
        pdf = generar_informe({"nombre": "Ana", "edad": 54}, "Clínica principal", hist, plan_de_hoy(plan, hist),
                              resumen_adherencia(plan, hist), metricas_paciente(plan, hist))
        self.assertTrue(pdf.startswith(b"%PDF"))
        vacio = generar_informe({"nombre": "Luis", "edad": None}, "Clínica", [], [], resumen_adherencia([], []),
                                metricas_paciente([], []))
        self.assertTrue(vacio.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
