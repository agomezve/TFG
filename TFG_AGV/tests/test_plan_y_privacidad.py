"""Tests del plan recetado, la adherencia/alertas y la protección de datos (RGPD)."""
import datetime
import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from adherencia import plan_de_hoy, resumen_adherencia  # noqa: E402

HOY = datetime.date(2026, 11, 17)


def serie(dias_atras, ejercicio="Sentadilla", errores=0, hora="18:00:00"):
    return {"fecha": f"{HOY - datetime.timedelta(days=dias_atras)} {hora}", "ejercicio": ejercicio, "errores": errores}


class TestAdherencia(unittest.TestCase):
    PLAN = [{"ejercicio": "Sentadilla", "nivel": "principiante", "series": 3, "dias_semana": 2}]

    def test_plan_de_hoy_cuenta_series(self):
        hist = [serie(0), serie(0, hora="18:05:00"), serie(2), serie(9)]
        d = plan_de_hoy(self.PLAN, hist, HOY)[0]
        self.assertEqual((d["hechas_hoy"], d["hechas_semana"], d["objetivo_semana"]), (2, 3, 6))
        self.assertFalse(d["completado_hoy"])

    def test_adherencia_maxima_100(self):
        hist = [serie(d, hora=f"18:0{i}:00") for d in range(3) for i in range(4)]  # 12 series > 6 recetadas
        self.assertEqual(resumen_adherencia(self.PLAN, hist, HOY)["adherencia"], 100)

    def test_alerta_inactividad_y_adherencia_baja(self):
        r = resumen_adherencia(self.PLAN, [serie(8)], HOY)
        tipos = {a["tipo"] for a in r["alertas"]}
        self.assertEqual(r["dias_sin_entrenar"], 8)
        self.assertIn("inactivo", tipos)
        self.assertIn("adherencia_baja", tipos)
        self.assertEqual(r["alertas"][0]["gravedad"], "alta")

    def test_alerta_tecnica(self):
        hist = [serie(0, errores=2), serie(1, errores=3), serie(2, errores=0)]
        tipos = {a["tipo"] for a in resumen_adherencia(self.PLAN, hist, HOY)["alertas"]}
        self.assertIn("tecnica", tipos)

    def test_sin_plan(self):
        r = resumen_adherencia([], [], HOY)
        self.assertIsNone(r["adherencia"])
        self.assertEqual({a["tipo"] for a in r["alertas"]}, {"sin_plan", "sin_sesiones"})

    def test_paciente_al_dia_sin_alertas(self):
        hist = [serie(d, hora=f"18:0{i}:00") for d in (0, 3) for i in range(3)]
        r = resumen_adherencia(self.PLAN, hist, HOY)
        self.assertEqual(r["adherencia"], 100)
        self.assertEqual(r["alertas"], [])


class TestPlanYPrivacidadBBDD(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.entorno = mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": self.tmp.name})
        self.entorno.start()
        import database
        self.db = importlib.reload(database)

    def tearDown(self):
        self.entorno.stop()
        self.tmp.cleanup()

    def test_guardar_y_sustituir_plan(self):
        pid = self.db.crear_paciente("Ana", 30, "", password="secreta1")
        self.db.guardar_plan(pid, [{"ejercicio": "Sentadilla", "nivel": "intermedio", "series": 3, "dias_semana": 4},
                                   {"ejercicio": "Plancha", "nivel": "principiante", "series": 2, "dias_semana": 3}])
        self.assertEqual([p["ejercicio"] for p in self.db.obtener_plan(pid)], ["Sentadilla", "Plancha"])
        self.db.guardar_plan(pid, [{"ejercicio": "Zancadas", "nivel": "avanzado", "series": 1, "dias_semana": 1}])
        plan = self.db.obtener_plan(pid)
        self.assertEqual(len(plan), 1)
        self.assertEqual((plan[0]["ejercicio"], plan[0]["nivel"]), ("Zancadas", "avanzado"))

    def test_consentimiento(self):
        pid = self.db.crear_paciente("Ana", None, "", password="secreta1")
        self.assertIsNone(self.db.obtener_consentimiento(pid))
        self.db.registrar_consentimiento(pid, "2026-11")
        self.assertEqual(self.db.obtener_consentimiento(pid)[0], "2026-11")
        self.db.retirar_consentimiento(pid)
        self.assertIsNone(self.db.obtener_consentimiento(pid))

    def test_borrar_paciente_elimina_todo(self):
        pid = self.db.crear_paciente("Ana Paz", None, "", password="secreta1")
        otro = self.db.crear_paciente("Luis", None, "", password="secreta1")
        self.db.guardar_sesion(pid, "Sentadilla", "principiante", 10, 0)
        self.db.guardar_sesion(otro, "Sentadilla", "principiante", 10, 0)
        self.db.guardar_plan(pid, [{"ejercicio": "Sentadilla", "nivel": "principiante", "series": 3, "dias_semana": 3}])
        self.db.registrar_consentimiento(pid, "2026-11")
        carpeta = os.path.join(self.tmp.name, "usuarios", "ana_paz", "2026-11-17")
        os.makedirs(carpeta)
        open(os.path.join(carpeta, "video.mp4"), "w").close()

        self.assertEqual(self.db.borrar_paciente(pid), "Ana Paz")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "usuarios", "ana_paz")))
        self.assertEqual(self.db.obtener_historial_paciente(pid), [])
        self.assertEqual(self.db.obtener_plan(pid), [])
        self.assertIsNone(self.db.obtener_consentimiento(pid))
        self.assertEqual([n for _, n, _ in self.db.obtener_pacientes()], ["Luis"])
        self.assertEqual(len(self.db.obtener_historial_paciente(otro)), 1)  # el otro paciente no se toca
        self.assertIsNone(self.db.borrar_paciente(9999))


if __name__ == "__main__":
    unittest.main()
