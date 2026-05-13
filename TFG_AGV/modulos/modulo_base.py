# Archivo: modulo_base.py
import numpy as np
import mediapipe as mp
import cv2
from abc import ABC, abstractmethod
import sys
import os

# Añadir el path raíz para asegurar que se encuentra database
# al usar desde main_gui.py o analizar_video.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ModuloEjercicio(ABC):
    """Interfaz base que define el contrato para todos los ejercicios de telerehabilitación."""
    
    def __init__(self):
        self.paciente_id = None
        self.en_error = False
        self.estado_esqueleto = "neutro" # "neutro", "correcto", "error"
        self._porcentaje_visual = 0.0  # Valor suavizado para la animación de la barra
        
    def get_errores_acumulados(self) -> int:
        """Devuelve el número de repeticiones mal hechas. 
        Este valor lo proveerán los submódulos usando sus variables internas."""
        return 0
        
    def dibujar_estadisticas_ui(self, frame, nombre_ejercicio, rep_correctas, rep_errores):
        """Dibuja el título estandarizado del ejercicio indicando aciertos y fallos."""
        estado = getattr(self, 'estado_esqueleto', 'neutro')
        en_error = getattr(self, 'en_error', False)

        if estado == "error" or en_error:
            color = (255, 0, 0) # Rojo en RGB
        elif estado == "correcto":
            color = (0, 255, 0) # Verde en RGB
        else:
            color = (255, 255, 255) # Blanco por defecto
            
        texto = f"{nombre_ejercicio} | Correctas: {rep_correctas} | Errores: {rep_errores}"
        cv2.putText(frame, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
    def set_paciente(self, paciente_id):
        self.paciente_id = paciente_id

    def dibujar_barra_progreso(self, frame, porcentaje, texto_fase="", color=(0, 255, 0)):
        """
        Dibuja una barra de progreso horizontal animada en la parte inferior del frame.
        porcentaje: float de 0 a 100 (valor objetivo real).
        La barra se mueve suavemente hacia el valor objetivo usando interpolación lineal (lerp).
        Zonas de color (BGR):
          0  – 50%  → Rojo
          50 – 70%  → Naranja
          70 – 90%  → Amarillo
          90 – 100% → Verde
        """
        h, w, _ = frame.shape
        x_start = int(w * 0.1)
        y_start = h - 60
        ancho_max = int(w * 0.8)
        alto = 30

        # --- Suavizado (lerp) ---
        # Factor 0.25 → sube rápido pero sin saltos bruscos.
        # Cuando baja (nueva rep) usamos factor mayor para resetear visualmente rápido.
        porcentaje_objetivo = max(0.0, min(100.0, float(porcentaje)))
        if not hasattr(self, '_porcentaje_visual'):
            self._porcentaje_visual = 0.0

        factor_lerp = 0.30 if porcentaje_objetivo >= self._porcentaje_visual else 0.45
        self._porcentaje_visual += (porcentaje_objetivo - self._porcentaje_visual) * factor_lerp

        # Clamp final por seguridad
        pv = max(0.0, min(100.0, self._porcentaje_visual))
        ancho_relleno = int((pv / 100.0) * ancho_max)

        # --- Color por zonas (RGB — el frame ya viene en RGB desde pantalla_principal.py) ---
        if pv < 50:
            # Rojo puro
            color_dinamico = (220, 0, 0)
        elif pv < 70:
            # Interpolación Rojo → Naranja  (50-70%)
            t = (pv - 50) / 20.0          # 0 → 1
            r = 220
            g = int(100 * t)              # verde sube un poco
            b = 0
            color_dinamico = (r, g, b)
        elif pv < 90:
            # Interpolación Naranja → Amarillo  (70-90%)
            t = (pv - 70) / 20.0          # 0 → 1
            r = int(220 - 20 * t)         # rojo baja un poco
            g = int(100 + 155 * t)        # verde sube hasta 255
            b = 0
            color_dinamico = (r, g, b)
        else:
            # Interpolación Amarillo → Verde  (90-100%)
            t = (pv - 90) / 10.0          # 0 → 1
            r = int(200 * (1.0 - t))      # rojo desaparece
            g = 255
            b = 0
            color_dinamico = (r, g, b)

        # --- Dibujo ---
        # Fondo (barra vacía)
        cv2.rectangle(frame, (x_start, y_start), (x_start + ancho_max, y_start + alto), (40, 40, 40), -1)
        # Borde
        cv2.rectangle(frame, (x_start, y_start), (x_start + ancho_max, y_start + alto), (200, 200, 200), 2)
        # Relleno animado
        if ancho_relleno > 0:
            cv2.rectangle(frame, (x_start, y_start), (x_start + ancho_relleno, y_start + alto), color_dinamico, -1)

        # Texto porcentaje a la derecha de la barra
        cv2.putText(frame, f"{int(pv)}%", (x_start + ancho_max + 10, y_start + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    
    def calcular_angulo_3d(self, a, b, c) -> float:
        """
        Calcula el ángulo 3D entre tres puntos (vectores en R3) usando álgebra lineal.
        """
        vec_ba = np.array(a) - np.array(b)
        vec_bc = np.array(c) - np.array(b)
        
        cos_theta = np.dot(vec_ba, vec_bc) / (np.linalg.norm(vec_ba) * np.linalg.norm(vec_bc))
        angulo_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
        
        return np.degrees(angulo_rad)

    @abstractmethod
    def obtener_landmarks_relevantes(self) -> list:
        """Retorna la lista de índices de landmarks de MediaPipe relevantes para este ejercicio."""
        pass

    def obtener_conexiones_relevantes(self) -> list:
        """Filtra POSE_CONNECTIONS para devolver solo las conexiones entre landmarks relevantes."""
        indices = set(self.obtener_landmarks_relevantes())
        return [(a, b) for a, b in mp.solutions.pose.POSE_CONNECTIONS 
                if a in indices and b in indices]

    @abstractmethod
    def evaluar_postura(self, world_landmarks, landmarks_2d, frame) -> None:
        pass

    @abstractmethod
    def generar_informe_clinico(self) -> None:
        pass