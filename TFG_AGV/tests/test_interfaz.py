"""Prueba de humo de la interfaz: abre la app real (con una BBDD temporal) y recorre
las pantallas principales del paciente y del fisioterapeuta sin usar la cámara.
Se salta automáticamente si no hay entorno gráfico.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class TestInterfaz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.entorno = mock.patch.dict(os.environ, {"TELEREHAB_DATA_DIR": cls.tmp.name})
        cls.entorno.start()
        try:
            import database
            database.init_db()  # por si el módulo ya se importó con otra carpeta de datos
            import pantalla_principal
            cls.app = pantalla_principal.AppRehabilitacion()
        except Exception as e:  # sin pantalla (por ejemplo en un servidor de CI)
            cls.entorno.stop()
            raise unittest.SkipTest(f"Sin entorno gráfico: {e}")
        cls.app.withdraw()
        # Cualquier excepción dentro de un callback de Tk hace fallar el test
        cls.errores_tk = []
        cls.app.report_callback_exception = lambda tipo, valor, tb: cls.errores_tk.append(
            "".join(__import__("traceback").format_exception(tipo, valor, tb)))

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()
        cls.entorno.stop()
        cls.tmp.cleanup()

    def tearDown(self):
        self.assertEqual(self.errores_tk, [], "\n".join(self.errores_tk))

    def _login(self, usuario, password):
        self.app.mostrar_login()
        self.app.entry_usuario.insert(0, usuario)
        self.app.entry_password.insert(0, password)
        self.app.login_paciente()
        self.app.update()

    def test_flujo_completo(self):
        import database
        app = self.app

        # Login incorrecto
        self._login("fisio", "mala")
        self.assertEqual(app.lbl_error.cget("text"), "Contraseña incorrecta")

        # Panel del fisio sin pacientes y alta de un paciente
        self._login("fisio", "12345")
        pid = database.crear_paciente("Demo", 65, "Rodilla", password="demo123")
        for reps, err in ((10, 3), (10, 1), (10, 0)):
            database.guardar_sesion(pid, "Sentadilla", "principiante", reps, err, 110.0)
        database.guardar_sesion(pid, "Plancha", "intermedio", 40, 5)
        app.mostrar_dashboard_fisio()
        app.update()
        self.assertEqual([p[1] for p in app.pacientes], ["Demo"])

        fecha = database.obtener_historial_paciente(pid)[0][0][:10]
        app.mostrar_calendario_paciente_fisio(pid, "Demo")
        app.update()
        app.mostrar_progreso_paciente_fisio(pid, "Demo")
        app.update()
        app.mostrar_ejercicios_dia_fisio(pid, "Demo", fecha, database.obtener_historial_paciente(pid))
        app.update()
        app.mostrar_detalle_serie_fisio(pid, "Demo", fecha, "Hombros Laterales", 0)
        app.update()
        app._popup_nuevo_paciente()
        app._popup_cambiar_password_fisio()
        app.update()

        # Paciente
        self._login("demo", "demo123")
        self.assertEqual(app.paciente_activo_id, pid)
        for nombre in ("Sentadilla", "Plancha", "Hombros Laterales"):
            app.mostrar_estadisticas_ejercicio(nombre)
            app.update()
            app.mostrar_video_explicativo(nombre)
            app.update()
        app.iniciar_motor_ejercicio("Bulgaras", "avanzado")
        self.assertEqual(type(app.ejercicio_activo).__name__, "ModuloBulgaras")
        self.assertEqual(app.ejercicio_activo.paciente_id, pid)


if __name__ == "__main__":
    unittest.main()
