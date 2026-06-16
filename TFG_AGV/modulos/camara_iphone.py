"""
camara_iphone.py
================
Módulo para detectar y conectar automáticamente la cámara del iPhone.

Lógica de prioridad:
  1. Continuity Camera (inalámbrico vía WiFi) – macOS Ventura + iOS 16+
  2. Continuity Camera (cable USB)
  3. Fallback a webcam integrada del Mac (índice 0)

Requiere: ffmpeg instalado (para listar dispositivos AVFoundation).
"""

import cv2
import subprocess
import re
import os

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────

# Palabras clave que identifican un iPhone en la lista de dispositivos
_IPHONE_KEYWORDS = ("iphone", "continuity camera", "apple iphone")

# ──────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE DISPOSITIVOS
# ──────────────────────────────────────────────────────────────────────────────

def _listar_dispositivos_avfoundation() -> list[tuple[int, str]]:
    """
    Llama a ffmpeg para obtener la lista de dispositivos de vídeo disponibles
    en macOS (AVFoundation).

    Retorna: lista de tuplas (índice_openCV, nombre_dispositivo)
             o lista vacía si ffmpeg no está disponible.
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            capture_output=True, text=True, timeout=6
        )
        # ffmpeg envía la lista por stderr aunque no haya error en el parsing
        output = result.stderr

        dispositivos = []
        en_video = False
        for linea in output.splitlines():
            if "AVFoundation video devices" in linea:
                en_video = True
                continue
            if "AVFoundation audio devices" in linea:
                break   # Fin de la sección de vídeo
            if en_video:
                # Ejemplo: "[AVFoundation...] [1] iPhone Camera"
                m = re.search(r'\[(\d+)\]\s+(.+)', linea)
                if m:
                    idx = int(m.group(1))
                    nombre = m.group(2).strip()
                    dispositivos.append((idx, nombre))

        return dispositivos

    except FileNotFoundError:
        # ffmpeg no instalado
        return []
    except Exception:
        return []


def _encontrar_indice_iphone(dispositivos: list[tuple[int, str]]) -> tuple[int, str] | None:
    """
    Busca entre los dispositivos detectados el que corresponde al iPhone.

    Retorna: (índice, nombre) del iPhone, o None si no se encuentra.
    """
    for idx, nombre in dispositivos:
        nombre_lower = nombre.lower()
        if any(kw in nombre_lower for kw in _IPHONE_KEYWORDS):
            return idx, nombre
    return None


# ──────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ──────────────────────────────────────────────────────────────────────────────

def diagnosticar_camaras() -> dict:
    """
    Devuelve un diccionario con el estado de las cámaras detectadas.
    Útil para depuración y para mostrar información al usuario.

    Retorna:
        {
          "dispositivos_avf": [(idx, nombre), ...],
          "iphone_idx": int | None,
          "iphone_nombre": str | None,
          "ffmpeg_disponible": bool,
        }
    """
    dispositivos = _listar_dispositivos_avfoundation()
    ffmpeg_ok = len(dispositivos) > 0 or _ffmpeg_presente()
    resultado_iphone = _encontrar_indice_iphone(dispositivos)

    return {
        "dispositivos_avf": dispositivos,
        "iphone_idx": resultado_iphone[0] if resultado_iphone else None,
        "iphone_nombre": resultado_iphone[1] if resultado_iphone else None,
        "ffmpeg_disponible": ffmpeg_ok,
    }


def _ffmpeg_presente() -> bool:
    """Comprueba si ffmpeg está disponible en el sistema."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=3)
        return True
    except Exception:
        return False


def conectar_camara_iphone(verbose: bool = True) -> tuple[cv2.VideoCapture | None, str]:
    """
    Intenta conectar a la cámara del iPhone usando Continuity Camera.

    Prioridad:
      1. iPhone detectado via AVFoundation (WiFi o cable – macOS lo gestiona solo)
      2. Escaneo de índices 1..4 (fallback por si ffmpeg no está instalado)
      3. None si no se encuentra el iPhone

    Args:
        verbose: Si True, imprime mensajes informativos por consola.

    Retorna:
        (cap, descripcion)
          - cap: objeto cv2.VideoCapture listo para usar, o None si falla.
          - descripcion: cadena describiendo la conexión realizada.
    """
    def log(msg):
        if verbose:
            print(msg)

    log("\n🔍 Buscando cámara del iPhone...")

    # ── Paso 1: detección via AVFoundation (ffmpeg) ──────────────────────────
    dispositivos = _listar_dispositivos_avfoundation()

    if dispositivos:
        log(f"   Dispositivos detectados: {[n for _, n in dispositivos]}")
        resultado = _encontrar_indice_iphone(dispositivos)

        if resultado:
            idx, nombre = resultado
            log(f"   📱 iPhone encontrado: '{nombre}' → índice AVFoundation [{idx}]")

            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    log(f"✅ Conectado al iPhone via Continuity Camera (índice {idx})")
                    return cap, f"iPhone – {nombre}"
            cap.release()
            log(f"   ⚠️  Índice {idx} detectado pero no responde. Probando alternativas...")

    # ── Paso 2: escaneo de índices sin ffmpeg ─────────────────────────────────
    # (útil si ffmpeg no está instalado pero el iPhone sigue montado como cámara)
    log("   🔌 Escaneando índices de cámara (1 al 4)...")
    for i in range(1, 5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                log(f"✅ Cámara externa encontrada en índice {i} (posiblemente iPhone)")
                return cap, f"Cámara externa (índice {i})"
        cap.release()

    # ── Sin iPhone ────────────────────────────────────────────────────────────
    log("❌ No se encontró ninguna cámara del iPhone.")
    log("   → Asegúrate de que el iPhone está en la misma WiFi O conectado por cable USB.")
    log("   → En el iPhone: Ajustes > General > AirPlay y Handoff > Cámara de Continuidad (activo).")
    return None, "iPhone no encontrado"


def conectar_camara_mac() -> tuple[cv2.VideoCapture | None, str]:
    """
    Conecta a la webcam integrada del Mac (índice 0).

    Retorna: (cap, descripcion)
    """
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, _ = cap.read()
        if ret:
            return cap, "Webcam Mac (índice 0)"
    cap.release()
    return None, "Webcam Mac no disponible"


def seleccionar_camara(usar_iphone: bool = True, verbose: bool = True) -> tuple[cv2.VideoCapture | None, str]:
    """
    Punto de entrada principal. Selecciona la cámara según la preferencia.

    Args:
        usar_iphone: Si True, intenta primero el iPhone y hace fallback al Mac.
                     Si False, usa directamente la webcam del Mac.
        verbose: Si True, imprime mensajes informativos.

    Retorna: (cap, descripcion)
    """
    if not usar_iphone:
        return conectar_camara_mac()

    cap, desc = conectar_camara_iphone(verbose=verbose)
    if cap is not None:
        return cap, desc

    # Fallback: webcam del Mac
    if verbose:
        print("⚠️  Usando webcam integrada del Mac como alternativa.")
    return conectar_camara_mac()
