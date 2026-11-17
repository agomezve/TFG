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


# Consejos de colocación de la cámara que se muestran antes de empezar cada ejercicio
CONSEJOS = {
    "Sentadilla": [
        "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
        "📏 Sepárate al menos 2 m para que se vea el cuerpo entero.",
        "🦵 Asegúrate de que ambas piernas son visibles en todo momento.",
        "🔦 Buena iluminación frontal, sin sombras en las piernas.",
        "👕 Ropa que contraste con el fondo.",
    ],
    "Peso Muerto": [
        "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
        "📏 Sepárate al menos 2 m para que se vean pies, rodillas, caderas y hombros.",
        "🎯 Oriéntate perpendicular a la cámara (perfil puro, no en diagonal).",
        "🔦 Iluminación lateral para que el contorno del cuerpo sea nítido.",
        "🦴 Evita ropa muy holgada que oculte la posición de la cadera.",
    ],
    "Press Militar": [
        "📐 Cámara DE FRENTE (frontal), a la altura de tu pecho.",
        "📏 Sepárate al menos 1.5 m para ver los brazos completamente extendidos.",
        "💪 Asegúrate de que codos y muñecas son visibles en todo el recorrido.",
        "🔦 Iluminación uniforme sin sombras sobre los brazos.",
        "🧍 Mantente centrado en el encuadre durante todo el ejercicio.",
    ],
    "Press Banca": [
        "📐 Cámara de LADO (lateral), a la altura del banco o del suelo.",
        "📏 Sepárate al menos 2 m para ver todo tu cuerpo horizontal.",
        "🛏️ Asegúrate de que la cámara captura desde la cabeza hasta los pies.",
        "💪 Los codos y muñecas deben ser visibles en todo el recorrido.",
        "🔦 Buena iluminación para distinguir brazos y torso del fondo.",
    ],
    "Plancha": [
        "📐 Cámara de LADO (lateral), cerca del suelo o a poca altura.",
        "📏 Sepárate al menos 2 m para ver hombros, cadera y tobillos.",
        "🎯 Oriéntate perpendicular a la cámara (perfil puro).",
        "🔦 Iluminación lateral para ver bien la línea del cuerpo.",
        "🧘 Quédate quieto en el mismo sitio durante todo el ejercicio.",
    ],
    "Propiocepcion": [
        "📐 Cámara DE FRENTE (frontal), a la altura de tu pecho.",
        "📏 Sepárate al menos 2 m para ver el cuerpo entero de cabeza a pies.",
        "🦵 Fondo despejado y sin movimiento para mejorar la detección.",
        "👟 Empieza con los dos pies en el suelo y levanta uno al iniciar.",
        "🔦 Iluminación uniforme sin sombras en el suelo.",
    ],
    "Hombros Laterales": [
        "📐 Cámara DE FRENTE (frontal), a la altura de tu cintura.",
        "📏 Sepárate al menos 1.5 m para ver ambos brazos elevados.",
        "💪 Asegúrate de que codos y muñecas son visibles al elevar.",
        "🔦 Iluminación frontal sin sombras sobre los brazos.",
        "🧍 Mantente centrado en el encuadre durante todo el ejercicio.",
    ],
    "Hip Thrust": [
        "📐 Cámara de LADO (lateral), a la altura del banco o suelo.",
        "📏 Sepárate al menos 2 m para ver hombros, cadera y rodillas.",
        "🎯 Oriéntate perpendicular a la cámara (perfil puro, no en diagonal).",
        "🔦 Iluminación lateral para detectar bien la extensión de cadera.",
    ],
    "Zancadas": [
        "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
        "📏 Sepárate al menos 2.5 m para ver ambas piernas en la zancada.",
        "🦵 Realiza las zancadas en línea recta, no en diagonal.",
        "🔦 Iluminación lateral para ver bien ambas rodillas.",
        "👕 Evita ropa similar al fondo, especialmente en las piernas.",
    ],
    "Bulgaras": [
        "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
        "📏 Sepárate al menos 2.5 m para ver ambas piernas.",
        "🦵 El pie trasero elevado debe ser visible — no debe taparse.",
        "🎯 Oriéntate perpendicular a la cámara (perfil puro).",
        "🔦 Buena iluminación lateral para distinguir ambas piernas.",
    ],
}
