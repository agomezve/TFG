"""Motor de una serie de ejercicio, independiente de la interfaz.

Contiene el mismo bucle por fotograma que usaba la app de escritorio (pantalla_principal.py):
  5 s de preparación -> evaluar_postura del módulo -> cortafuegos de seguridad
  (3 errores totales o 2 consecutivos) -> objetivo completado (10 reps o 30 s),
además de la grabación de la serie y su conversión a MP4.

Lo usan la app de escritorio (funciones de dibujo y grabación) y la app móvil/web
(SesionEjercicio completa), así ambas se comportan exactamente igual.
"""
import datetime
import os
import shutil
import subprocess
import time

import cv2
import mediapipe as mp

import ejercicios
from config import directorio_datos, nombre_carpeta_paciente

SEGUNDOS_PREPARACION = 5.0


def dibujar_landmarks_filtrados(frame, pose_landmarks, indices_relevantes, conexiones_relevantes, color=(245, 66, 230)):
    """Dibuja en el frame solo los landmarks y conexiones relevantes para el ejercicio."""
    h, w, _ = frame.shape
    for a, b in conexiones_relevantes:
        pt_a = pose_landmarks.landmark[a]
        pt_b = pose_landmarks.landmark[b]
        x_a, y_a = int(pt_a.x * w), int(pt_a.y * h)
        x_b, y_b = int(pt_b.x * w), int(pt_b.y * h)
        cv2.line(frame, (x_a, y_a), (x_b, y_b), color, 4)
    for idx in indices_relevantes:
        pt = pose_landmarks.landmark[idx]
        cx, cy = int(pt.x * w), int(pt.y * h)
        cv2.circle(frame, (cx, cy), 6, color, -1)
        cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1)


def color_esqueleto(ejercicio_activo):
    """Color tricolor del esqueleto: azul (neutro), verde (correcto), rojo (error). En RGB."""
    estado = getattr(ejercicio_activo, 'estado_esqueleto', 'neutro')
    if estado == "error":
        return (255, 0, 0)
    if estado == "correcto":
        return (0, 255, 0)
    return (0, 0, 255)


def convertir_grabacion_a_mp4(ruta_avi, frames, inicio):
    """Convierte el .avi de la serie a MP4 con los FPS reales.

    Si ffmpeg no está instalado o la conversión falla, se conserva el .avi original
    (renombrado con los FPS reales para poder convertirlo a mano).
    """
    if not ruta_avi or inicio is None or not os.path.exists(ruta_avi):
        return None
    duracion = time.time() - inicio
    if duracion <= 0 or frames <= 0:
        return None

    fps_real = frames / duracion
    ruta_mp4 = ruta_avi.replace(".avi", ".mp4")
    convertido = False
    if shutil.which("ffmpeg"):
        try:
            resultado = subprocess.run([
                "ffmpeg", "-y", "-r", str(fps_real),
                "-i", ruta_avi,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", ruta_mp4
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            convertido = (resultado.returncode == 0 and os.path.exists(ruta_mp4)
                          and os.path.getsize(ruta_mp4) > 0)
        except OSError:
            convertido = False

    if convertido:
        os.remove(ruta_avi)
        return ruta_mp4
    try:
        os.rename(ruta_avi, ruta_avi.replace(".avi", f"_fps{fps_real:.2f}.avi"))
    except OSError:
        pass
    return None


def ruta_nueva_grabacion(nombre_paciente, nombre_ejercicio):
    """Ruta del .avi de una serie nueva: usuarios/<paciente>/<día>/<ejercicio>/videos/."""
    nombre_pac_limpio = nombre_carpeta_paciente(nombre_paciente or 'paciente')
    ahora = datetime.datetime.now()
    ej_limpio = (nombre_ejercicio or 'ejercicio').lower().replace(" ", "_")
    carpeta_videos = os.path.join(directorio_datos(), "usuarios", nombre_pac_limpio,
                                  ahora.strftime("%Y-%m-%d"), ej_limpio, "videos")
    os.makedirs(carpeta_videos, exist_ok=True)
    return os.path.join(carpeta_videos, f"video_{ej_limpio}_{ahora.strftime('%Y-%m-%d_%H-%M-%S')}.avi")


class SesionEjercicio:
    """Una serie de ejercicio que se alimenta fotograma a fotograma (app móvil/web).

    procesar(frame_rgb) dibuja sobre el fotograma y devuelve el estado:
      "en_curso", "completado" (objetivo alcanzado) o "cortafuegos" (demasiados errores).
    Al terminar (por cualquier motivo) hay que llamar a finalizar(): genera el informe
    clínico, guarda la sesión en la BBDD y cierra la grabación, igual que en escritorio.
    """

    def __init__(self, nombre_ejercicio, nivel, paciente_id, nombre_paciente, grabar=True, fps_grabacion=15.0):
        self.nombre_ejercicio = nombre_ejercicio
        self.nombre_paciente = nombre_paciente
        self.ejercicio_activo = ejercicios.crear_modulo(nombre_ejercicio, nivel)
        self.ejercicio_activo.set_paciente(paciente_id)
        self.pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1,
                                           min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.tiempo_preparacion_fin = time.time() + SEGUNDOS_PREPARACION
        self.grabar = grabar
        self.fps_grabacion = fps_grabacion
        self.video_writer = None
        self.tam_video = None
        self.ruta_video_actual = None
        self.frames_grabados_vid = 0
        self.inicio_grabacion_vid = None
        self.finalizada = False
        self.persona_detectada = False

    # ── Datos para la interfaz ────────────────────────────────────────────────
    def segundos_preparacion(self):
        return max(0, int(self.tiempo_preparacion_fin - time.time()) + 1) if time.time() < self.tiempo_preparacion_fin else 0

    def marcador(self):
        ej = self.ejercicio_activo
        return {
            "errores": int(getattr(ej, 'get_errores_acumulados', lambda: 0)()),
            "estado_esqueleto": getattr(ej, 'estado_esqueleto', 'neutro'),
            "preparacion": self.segundos_preparacion(),
            "persona_detectada": self.persona_detectada,
        }

    # ── Bucle por fotograma (idéntico al de escritorio) ──────────────────────
    def procesar(self, frame_rgb):
        if self.finalizada:
            return "finalizada"
        frame_rgb.flags.writeable = False
        resultados = self.pose.process(frame_rgb)
        frame_rgb.flags.writeable = True
        estado = "en_curso"
        self.persona_detectada = bool(resultados.pose_landmarks)

        if resultados.pose_landmarks and resultados.pose_world_landmarks:
            indices = self.ejercicio_activo.obtener_landmarks_relevantes()
            conexiones = self.ejercicio_activo.obtener_conexiones_relevantes()
            dibujar_landmarks_filtrados(frame_rgb, resultados.pose_landmarks, indices, conexiones,
                                        color=color_esqueleto(self.ejercicio_activo))

            tiempo_actual = time.time()
            if tiempo_actual < self.tiempo_preparacion_fin:
                segundos_restantes = int(self.tiempo_preparacion_fin - tiempo_actual) + 1
                h, w, _ = frame_rgb.shape
                texto_prep = f"PREPARACION: {segundos_restantes}"
                (tw, th), _ = cv2.getTextSize(texto_prep, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
                cv2.putText(frame_rgb, texto_prep, (int((w - tw) / 2), int(h / 2)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 165, 0), 3, cv2.LINE_AA)
            else:
                self.ejercicio_activo.evaluar_postura(
                    resultados.pose_world_landmarks.landmark,
                    resultados.pose_landmarks.landmark,
                    frame_rgb
                )
                # Cortafuegos de seguridad: 3 errores totales o 2 consecutivos
                errores_totales = getattr(self.ejercicio_activo, 'get_errores_acumulados', lambda: 0)()
                errores_consec = getattr(self.ejercicio_activo, 'get_errores_consecutivos', lambda: 0)()
                if errores_totales >= 3 or errores_consec >= 2:
                    estado = "cortafuegos"
                # Objetivo completado (10 reps o 30 s)
                elif self.ejercicio_activo.get_objetivo_completado():
                    estado = "completado"

        self._grabar(frame_rgb)
        return estado

    def _grabar(self, frame_rgb):
        if not self.grabar:
            return
        h, w = frame_rgb.shape[:2]
        if self.video_writer is None:
            self.ruta_video_actual = ruta_nueva_grabacion(self.nombre_paciente, self.nombre_ejercicio)
            self.tam_video = (int(w), int(h))
            self.video_writer = cv2.VideoWriter(self.ruta_video_actual, cv2.VideoWriter_fourcc(*'MJPG'),
                                                self.fps_grabacion, self.tam_video)
            self.frames_grabados_vid = 0
            self.inicio_grabacion_vid = time.time()
        if self.video_writer.isOpened():
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            if (w, h) != self.tam_video:
                frame_bgr = cv2.resize(frame_bgr, self.tam_video)
            self.video_writer.write(frame_bgr)
            self.frames_grabados_vid += 1

    def finalizar(self):
        """Cierra la grabación, genera el informe clínico y guarda la sesión (una sola vez)."""
        if self.finalizada:
            return
        self.finalizada = True
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            convertir_grabacion_a_mp4(self.ruta_video_actual, self.frames_grabados_vid, self.inicio_grabacion_vid)
        self.ejercicio_activo.generar_informe_clinico()
        self.pose.close()
