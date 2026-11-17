"""Configuración central de rutas de la plataforma.

Por defecto todo se guarda junto al código (igual que siempre). Se puede cambiar
la carpeta de datos con la variable de entorno TELEREHAB_DATA_DIR, lo que permite:
  - empaquetar la app como ejecutable (la carpeta del programa suele ser de solo lectura),
  - separar los datos clínicos del código (y no subirlos nunca a GitHub),
  - ejecutar los tests sin tocar los datos reales.
"""
import os
import sys

DIRECTORIO_CODIGO = os.path.dirname(os.path.abspath(__file__))


def directorio_datos() -> str:
    """Carpeta donde se guardan la BBDD, los informes y los vídeos de los pacientes."""
    return os.environ.get("TELEREHAB_DATA_DIR") or DIRECTORIO_CODIGO


def ruta_bbdd() -> str:
    return os.path.join(directorio_datos(), "pacientes.db")


def nombre_carpeta_paciente(nombre: str) -> str:
    """Convierte un nombre de paciente en un nombre de carpeta seguro (misma regla de siempre)."""
    return "".join([c for c in nombre if c.isalpha() or c.isdigit() or c == ' ']).rstrip().replace(" ", "_").lower()


def abrir_con_aplicacion_del_sistema(ruta: str) -> None:
    """Abre un archivo (vídeo, informe...) con la aplicación predeterminada en macOS, Windows o Linux."""
    import subprocess
    if sys.platform == "darwin":
        subprocess.Popen(["open", ruta])
    elif sys.platform.startswith("win"):
        os.startfile(ruta)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", ruta])
