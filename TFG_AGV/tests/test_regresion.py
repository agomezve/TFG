"""Test de regresión: el comportamiento de los 11 módulos de ejercicio, sobre
11 vídeos reales y 3 niveles, debe ser idéntico al guardado en tests/golden.

Si cambias A PROPÓSITO la lógica de un ejercicio, regenera la referencia con:
    python tests/golden_runner.py
"""
import gzip
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden_runner  # noqa: E402

RUTA_GOLDEN = os.path.join(golden_runner.RAIZ, "tests", "golden", "huellas.json.gz")


class TestRegresionEjercicios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with gzip.open(RUTA_GOLDEN, "rt", encoding="utf-8") as f:
            cls.esperado = json.load(f)
        cls.obtenido = golden_runner.ejecutar()

    def test_mismas_combinaciones(self):
        self.assertEqual(sorted(self.esperado), sorted(self.obtenido))

    def test_comportamiento_identico(self):
        for clave, esperado in self.esperado.items():
            obtenido = self.obtenido.get(clave)
            for parte in ("estado_final", "traza", "informe", "bbdd"):
                with self.subTest(caso=clave, parte=parte):
                    self.assertEqual(esperado[parte], obtenido[parte])


if __name__ == "__main__":
    unittest.main()
