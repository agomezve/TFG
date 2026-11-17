"""Catálogo único de ejercicios de la plataforma.

Antes la lista de ejercicios estaba repetida en varios sitios (lista del dashboard,
cadena de if/elif, mapa de vídeos...). Ahora añadir un ejercicio nuevo es añadir
UNA entrada aquí.
"""
from dataclasses import dataclass

from modulos.modulo_bulgaras import ModuloBulgaras
from modulos.modulo_hip_thrust import ModuloHipThrust
from modulos.modulo_hombro_lateral import ModuloHombroLateral
from modulos.modulo_peso_muerto import ModuloPesoMuerto
from modulos.modulo_plancha import ModuloPlancha
from modulos.modulo_press_banca import ModuloPressBanca
from modulos.modulo_press_militar import ModuloPressMilitar
from modulos.modulo_propiocepcion import ModuloPropiocepcion
from modulos.modulo_sentadilla import ModuloSentadilla
from modulos.modulo_zancadas import ModuloZancadas


@dataclass(frozen=True)
class Ejercicio:
    nombre: str              # Nombre visible y el que se guarda en la BBDD
    clase: type              # Módulo de análisis biomecánico
    carpeta_informes: str    # Subcarpeta donde el módulo guarda sus informes
    video_explicativo: str   # Archivo dentro de videos_explicativos/


CATALOGO = [
    Ejercicio("Sentadilla",        ModuloSentadilla,    "sentadilla",     "v_e_sentadilla.mp4"),
    Ejercicio("Peso Muerto",       ModuloPesoMuerto,    "peso_muerto",    "v_e_peso_muerto.mp4"),
    Ejercicio("Press Militar",     ModuloPressMilitar,  "press_militar",  "v_e_press_militar.mp4"),
    Ejercicio("Press Banca",       ModuloPressBanca,    "press_banca",    "v_e_press_banca.mp4"),
    Ejercicio("Plancha",           ModuloPlancha,       "plancha",        "v_e_plancha.mp4"),
    Ejercicio("Propiocepcion",     ModuloPropiocepcion, "propiocepcion",  "v_e_propiocepcion.mp4"),
    Ejercicio("Hombros Laterales", ModuloHombroLateral, "hombro_lateral", "v_e_elevaciones_laterales.mp4"),
    Ejercicio("Hip Thrust",        ModuloHipThrust,     "hip_thrust",     "v_e_hip_trust.mp4"),
    Ejercicio("Zancadas",          ModuloZancadas,      "zancadas",       "v_e_zancadas.mp4"),
    Ejercicio("Bulgaras",          ModuloBulgaras,      "bulgaras",       "v_e_bulgaras.mp4"),
]

POR_NOMBRE = {e.nombre: e for e in CATALOGO}


def nombres() -> list:
    return [e.nombre for e in CATALOGO]


def crear_modulo(nombre: str, nivel: str):
    """Instancia el módulo de análisis del ejercicio indicado."""
    return POR_NOMBRE[nombre].clase(nivel=nivel)


def carpeta_informes(nombre: str) -> str:
    """Subcarpeta de informes de un ejercicio. Para nombres desconocidos usa la regla antigua."""
    ejercicio = POR_NOMBRE.get(nombre)
    return ejercicio.carpeta_informes if ejercicio else nombre.lower().replace(" ", "_")
