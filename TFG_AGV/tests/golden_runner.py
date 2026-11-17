"""Ejecuta TODOS los módulos de ejercicio sobre los landmarks reales guardados en
tests/fixtures y devuelve una "huella" del comportamiento (estado final, traza
frame a frame, texto del informe y fila guardada en la BBDD).

Sirve como test de regresión ("golden master"): si alguien cambia la lógica de
un ejercicio sin querer, la huella cambia y el test falla.

El código se ejecuta sobre una COPIA temporal del proyecto para que los informes
y la base de datos de prueba nunca toquen los datos reales.
"""
import contextlib
import gzip
import glob
import importlib
import inspect
import io
import json
import os
import re
import shutil
import sys
import tempfile
from unittest import mock

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(RAIZ, "tests", "fixtures")
NIVELES = ["principiante", "intermedio", "avanzado"]


class _Punto:
    __slots__ = ("x", "y", "z", "visibility")

    def __init__(self, fila):
        self.x, self.y, self.z, self.visibility = (float(v) for v in fila)


class _Reloj:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def _serializable(valor):
    if isinstance(valor, (bool, str)) or valor is None:
        return valor
    if isinstance(valor, (int, np.integer)):
        return int(valor)
    if isinstance(valor, (float, np.floating)):
        return round(float(valor), 4)
    if isinstance(valor, (list, tuple)):
        return [_serializable(v) for v in valor]
    if isinstance(valor, dict):
        return {str(k): _serializable(v) for k, v in valor.items()}
    return f"<{type(valor).__name__}>"


def _limpiar_texto(texto, raiz_temporal):
    # La carpeta de datos puede ser la del proyecto o una configurada: da igual.
    texto = texto.replace(os.path.join(raiz_temporal, "proyecto"), "<DATOS>")
    texto = texto.replace(os.path.join(raiz_temporal, "datos"), "<DATOS>")
    texto = re.sub(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", "<FECHA>", texto)
    texto = re.sub(r"\d{4}-\d{2}-\d{2}[_ ]\d{2}[-:]\d{2}[-:]\d{2}", "<FECHA>", texto)
    texto = re.sub(r"\d{4}-\d{2}-\d{2}", "<DIA>", texto)
    return texto


def _clases_ejercicio(raiz):
    from modulos.modulo_base import ModuloEjercicio  # noqa: importado desde la copia
    clases = {}
    for ruta in sorted(glob.glob(os.path.join(raiz, "modulos", "modulo_*.py"))):
        nombre_mod = "modulos." + os.path.splitext(os.path.basename(ruta))[0]
        mod = importlib.import_module(nombre_mod)
        for nombre, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, ModuloEjercicio) and obj is not ModuloEjercicio and obj.__module__ == nombre_mod:
                clases[nombre] = obj
    return clases


def ejecutar(raiz_codigo=RAIZ):
    """Devuelve el diccionario de huellas ejecutando el código de `raiz_codigo`."""
    tmp = tempfile.mkdtemp(prefix="telerehab_golden_")
    copia = os.path.join(tmp, "proyecto")
    os.makedirs(copia)
    shutil.copytree(os.path.join(raiz_codigo, "modulos"), os.path.join(copia, "modulos"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    for extra in ("database.py", "config.py", "ejercicios.py", "seguridad.py"):
        if os.path.exists(os.path.join(raiz_codigo, extra)):
            shutil.copy(os.path.join(raiz_codigo, extra), copia)

    entorno = {"TELEREHAB_DATA_DIR": os.path.join(tmp, "datos")}
    # Si otro test ya importó estos módulos, se descartan para cargar los de la copia
    for nombre in [m for m in sys.modules
                   if m in ("database", "config", "ejercicios", "seguridad") or m == "modulos" or m.startswith("modulos.")]:
        del sys.modules[nombre]
    modulos_previos = set(sys.modules)
    sys.path.insert(0, copia)
    try:
        with mock.patch.dict(os.environ, entorno), contextlib.redirect_stdout(io.StringIO()):
            import database
            paciente_id = database.crear_paciente("Paciente Prueba", 40, "")
            clases = _clases_ejercicio(copia)

        huellas = {}
        for fixture in sorted(glob.glob(os.path.join(FIXTURES, "*.npz"))):
            datos = np.load(fixture)
            mundo = [[_Punto(f) for f in frame] for frame in datos["mundo"]]
            imagen = [[_Punto(f) for f in frame] for frame in datos["imagen"]]
            clip = os.path.splitext(os.path.basename(fixture))[0]

            for nombre_clase, clase in sorted(clases.items()):
                for nivel in NIVELES:
                    reloj = _Reloj()
                    salida = io.StringIO()
                    with mock.patch("time.time", reloj), mock.patch.dict(os.environ, entorno), \
                            contextlib.redirect_stdout(salida):
                        ej = clase(nivel=nivel)
                        ej.set_paciente(paciente_id)
                        traza = []
                        for w, i in zip(mundo, imagen):
                            reloj.t += 1 / 30.0
                            lienzo = np.zeros((720, 1280, 3), dtype=np.uint8)
                            ej.evaluar_postura(w, i, lienzo)
                            traza.append((ej.get_errores_acumulados(), ej.get_errores_consecutivos(),
                                          bool(ej.get_objetivo_completado()),
                                          getattr(ej, "estado_esqueleto", None)))
                        estado = {k: _serializable(v) for k, v in sorted(vars(ej).items())}
                        ej.generar_informe_clinico()
                        fila = database.obtener_historial_paciente(paciente_id)[:1]

                    huellas[f"{clip}|{nombre_clase}|{nivel}"] = {
                        "estado_final": estado,
                        "traza": _serializable(traza),
                        "informe": _limpiar_texto(salida.getvalue(), tmp),
                        "bbdd": _serializable([list(f[1:]) for f in fila]),
                    }
        return huellas
    finally:
        sys.path.remove(copia)
        for nombre in set(sys.modules) - modulos_previos:
            if nombre == "database" or nombre.startswith("modulos") or nombre in ("config", "ejercicios", "seguridad"):
                sys.modules.pop(nombre, None)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    destino = os.path.join(RAIZ, "tests", "golden", "huellas.json.gz")
    origen = sys.argv[1] if len(sys.argv) > 1 else RAIZ
    resultado = ejecutar(origen)
    with gzip.open(destino, "wt", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"{len(resultado)} huellas guardadas en {destino}")
