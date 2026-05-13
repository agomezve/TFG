# Archivo: modulo_zancadas.py
import cv2
import numpy as np
from modulos.modulo_base import ModuloEjercicio

class ModuloZancadas(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"profundidad_maxima": 90.0, "inicio_repeticion": 160.0, "max_desbalance_torso": 0.05}
        else: # principiante
            self.umbrales = {"profundidad_maxima": 110.0, "inicio_repeticion": 150.0, "max_desbalance_torso": 0.10}
            
        self.fase_actual = "DE PIE"
        self.repeticiones = 0
        self.errores_profundidad = 0
        self.errores_equilibrio = 0
        
        self.angulo_min_alcanzado = 180.0
        self.desbalance_max_alcanzado = 0.0
        
        self.profundidades = []
        self.hubo_error_profundidad_actual = False
        self.hubo_error_equilibrio_actual = False
        
        self.centro_x_referencia = None
        
        self.feedback_actual = "De pie. Puedes hacer la zancada cuando quieras."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return self.errores_profundidad + self.errores_equilibrio

    def obtener_landmarks_relevantes(self) -> list:
        # Hombro(11,12), Cadera(23,24), Rodilla(25,26), Tobillo(27,28)
        return [11, 12, 23, 24, 25, 26, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        cadera_d = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        rodilla_d = [world_landmarks[26].x, world_landmarks[26].y, world_landmarks[26].z]
        tobillo_d = [world_landmarks[28].x, world_landmarks[28].y, world_landmarks[28].z]

        cadera_i = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        rodilla_i = [world_landmarks[25].x, world_landmarks[25].y, world_landmarks[25].z]
        tobillo_i = [world_landmarks[27].x, world_landmarks[27].y, world_landmarks[27].z]
        
        hombro_x_medio = (landmarks_2d[11].x + landmarks_2d[12].x) / 2.0
        cadera_x_medio = (landmarks_2d[23].x + landmarks_2d[24].x) / 2.0
        
        # Desviación del torso respecto a la vertical
        desbalance_actual = abs(hombro_x_medio - cadera_x_medio)
        
        angulo_rodilla_d = self.calcular_angulo_3d(cadera_d, rodilla_d, tobillo_d)
        angulo_rodilla_i = self.calcular_angulo_3d(cadera_i, rodilla_i, tobillo_i)
        
        # El ángulo activo es el de la pierna que más se está flexionando
        angulo_activo = min(angulo_rodilla_d, angulo_rodilla_i)

        rango = self.umbrales["inicio_repeticion"] - self.umbrales["profundidad_maxima"]
        progreso = self.umbrales["inicio_repeticion"] - angulo_activo
        porcentaje = (progreso / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "DE PIE" and angulo_activo >= self.umbrales["inicio_repeticion"]:
            self.estado_esqueleto = "neutro"
        
        if self.fase_actual == "DE PIE":
            if angulo_activo < self.umbrales["inicio_repeticion"]:
                self.fase_actual = "BAJANDO"
                self.angulo_min_alcanzado = angulo_activo
                self.desbalance_max_alcanzado = desbalance_actual
                
                self.hubo_error_profundidad_actual = False
                self.hubo_error_equilibrio_actual = False
                
                self.max_porcentaje_actual = porcentaje
                self.feedback_actual = "Bajando..."
                self.color_feedback = (255, 255, 0)
                
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_activo < self.angulo_min_alcanzado:
                self.angulo_min_alcanzado = angulo_activo
                
            if desbalance_actual > self.desbalance_max_alcanzado:
                self.desbalance_max_alcanzado = desbalance_actual
                
            if desbalance_actual > self.umbrales["max_desbalance_torso"]:
                self.hubo_error_equilibrio_actual = True
                self.estado_esqueleto = "error"
                self.color_feedback = (0, 0, 255)
                self.feedback_actual = "¡CUIDADO! Tronco desequilibrado."
                
            if porcentaje == 100 and not self.hubo_error_equilibrio_actual and not self.hubo_error_profundidad_actual:
                self.estado_esqueleto = "correcto"
                
            # Si empieza a extender de nuevo asume que terminó de bajar
            if angulo_activo > self.angulo_min_alcanzado + 15:
                self.fase_actual = "SUBIENDO"
                
                if self.angulo_min_alcanzado > self.umbrales["profundidad_maxima"] + 15:
                    self.hubo_error_profundidad_actual = True
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Falta bajar más."
                    self.color_feedback = (0, 165, 255)
                elif not self.hubo_error_equilibrio_actual:
                    self.feedback_actual = "Buena profundidad. Arriba."
                    self.color_feedback = (0, 255, 0)
                    
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_activo > self.umbrales["inicio_repeticion"]:
                self.fase_actual = "DE PIE"
                
                if self.max_porcentaje_actual >= 100:
                    self.repeticiones += 1
                    self.profundidades.append(self.angulo_min_alcanzado)
                    
                    if self.hubo_error_profundidad_actual:
                        self.errores_profundidad += 1
                    if self.hubo_error_equilibrio_actual:
                        self.errores_equilibrio += 1
                        
                    self.feedback_actual = "Zancada registrada."
                elif self.max_porcentaje_actual > 40:
                    self.repeticiones += 1
                    self.errores_profundidad += 1 # Incompleto a propósito
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Zancada incompleta. Cuenta error."
                
                self.max_porcentaje_actual = 0.0

        self.en_error = self.hubo_error_profundidad_actual or self.hubo_error_equilibrio_actual
        self.dibujar_barra_progreso(frame, porcentaje)
        
        errores_totales = self.errores_profundidad + self.errores_equilibrio
        reps_correctas = self.repeticiones - errores_totales
        self.dibujar_estadisticas_ui(frame, "Zancadas", reps_correctas, errores_totales)
        
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        media_prof = sum(self.profundidades) / self.repeticiones if self.repeticiones > 0 else 0
        errores_totales = self.errores_profundidad + self.errores_equilibrio
        
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Zancadas",
                nivel=self.nivel,
                repeticiones=self.repeticiones,
                errores=errores_totales,
                profundidad_media=media_prof
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_zancadas_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "zancadas")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: ZANCADAS (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Repeticiones completadas: {self.repeticiones}")
        if self.repeticiones > 0:
            lineas_informe.append(f"🔹 Flexión media alcanzada de rodilla activa: {media_prof:.1f}º")
            lineas_informe.append(f"🔹 Zancadas con flexión insuficiente: {self.errores_profundidad}")
            lineas_informe.append(f"🔹 Zancadas perdiendo equilibrio de torso: {self.errores_equilibrio}")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
        except IOError:
            pass
