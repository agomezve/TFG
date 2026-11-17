"""Localiza el informe clínico (.txt) y el vídeo de una serie concreta de un paciente.

Es la misma búsqueda que hacía el panel del fisio de escritorio; ahora la comparten
la app de escritorio y la app móvil/web.
"""
import datetime
import os

import ejercicios
from config import directorio_datos, nombre_carpeta_paciente


def _extraer_dt(filename):
    try:
        name = filename.rsplit('.', 1)[0]
        if "_fps" in name:
            name = name.split("_fps")[0]
        parts = name.split('_')
        return datetime.datetime.strptime(f"{parts[-2]}_{parts[-1]}", "%Y-%m-%d_%H-%M-%S")
    except Exception:
        return datetime.datetime.min


def buscar_informe_y_video(nombre, fecha, ejercicio, serie_idx, db_timestamp_str=None):
    """Devuelve (ruta_txt, ruta_video); cualquiera de los dos puede ser None."""
    carpeta_dia = os.path.join(directorio_datos(), "usuarios", nombre_carpeta_paciente(nombre), fecha)
    # Los informes los guarda cada módulo en su carpeta (p. ej. "hombro_lateral") y los vídeos
    # se guardan con el nombre del ejercicio (p. ej. "hombros_laterales"): se buscan ambas.
    carpeta_ej_informes = os.path.join(carpeta_dia, ejercicios.carpeta_informes(ejercicio))
    carpeta_ej_videos = os.path.join(carpeta_dia, ejercicio.lower().replace(" ", "_"))
    carpeta_txt = os.path.join(carpeta_ej_informes, "informes")
    carpeta_vid = os.path.join(carpeta_ej_videos, "videos")
    if not os.path.exists(carpeta_txt) and os.path.exists(carpeta_ej_informes):
        carpeta_txt = carpeta_ej_informes  # Estructura antigua: informes sin subcarpeta

    archivos_txt = sorted(f for f in os.listdir(carpeta_txt) if f.endswith(".txt")) if os.path.exists(carpeta_txt) else []
    archivos_vid = sorted(f for f in os.listdir(carpeta_vid) if f.endswith((".mp4", ".avi"))) if os.path.exists(carpeta_vid) else []

    ruta_txt = None
    ruta_vid = None
    t_txt = None

    # 1. Buscar el TXT por el timestamp de la BBDD (margen de 15 s entre BBDD y archivo)
    if db_timestamp_str:
        try:
            db_t = datetime.datetime.strptime(db_timestamp_str, "%Y-%m-%d %H:%M:%S")
            min_diff = 999999
            for txt in archivos_txt:
                t = _extraer_dt(txt)
                diff = abs((db_t - t).total_seconds())
                if diff < min_diff and diff <= 15:
                    min_diff = diff
                    ruta_txt = os.path.join(carpeta_txt, txt)
                    t_txt = t
        except Exception:
            pass

    # 2. Fallback: buscar por índice (series antiguas)
    if not ruta_txt and serie_idx < len(archivos_txt):
        ruta_txt = os.path.join(carpeta_txt, archivos_txt[serie_idx])
        t_txt = _extraer_dt(archivos_txt[serie_idx])

    # 3. Vídeo de esa serie: el último que empezó como mucho 20 min antes del informe
    if ruta_txt and t_txt:
        video_match = None
        for vid in archivos_vid:
            diff = (t_txt - _extraer_dt(vid)).total_seconds()
            if 0 <= diff <= 1200:
                video_match = vid
        if video_match:
            ruta_vid = os.path.join(carpeta_vid, video_match)

    return ruta_txt, ruta_vid
