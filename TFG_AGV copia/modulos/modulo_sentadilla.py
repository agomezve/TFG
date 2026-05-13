# Archivo: modulo_sentadilla.py
import cv2
from modulos.modulo_base import ModuloEjercicio

class ModuloSentadilla(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"profundidad_maxima": 90.0, "inicio_repeticion": 170.0, "valgo_tolerancia": 0.03}
        else: # principiante
            self.umbrales = {"profundidad_maxima": 120.0, "inicio_repeticion": 140.0, "valgo_tolerancia": 0.10}
        self.fase_actual = "DE PIE"
        self.angulo_minimo_actual = 180.0
        self.hubo_valgo_actual = False
        self.stats_repeticiones_totales = 0
        self.stats_registro_profundidades = []
        self.stats_repeticiones_con_valgo = 0
        self.feedback_actual = "Preparado. Comienza a bajar."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return self.stats_repeticiones_con_valgo

    def obtener_landmarks_relevantes(self) -> list:
        # Cadera(23,24), Rodilla(25,26), Tobillo(27,28) — ambos lados
        return [23, 24, 25, 26, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        cadera = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        rodilla = [world_landmarks[26].x, world_landmarks[26].y, world_landmarks[26].z]
        tobillo = [world_landmarks[28].x, world_landmarks[28].y, world_landmarks[28].z]
        
        angulo_rodilla = self.calcular_angulo_3d(cadera, rodilla, tobillo)
        desviacion_x = cadera[0] - rodilla[0] 

        # Calcular porcentaje de barra
        rango = self.umbrales["inicio_repeticion"] - self.umbrales["profundidad_maxima"]
        progreso_grados = self.umbrales["inicio_repeticion"] - angulo_rodilla
        porcentaje = (progreso_grados / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje)) # Clamp

        # Inicialización de tracker de %
        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "DE PIE" and angulo_rodilla >= self.umbrales["inicio_repeticion"]:
            self.estado_esqueleto = "neutro"

        # Máquina de estados
        if angulo_rodilla < self.umbrales["inicio_repeticion"] and self.fase_actual == "DE PIE":
            self.fase_actual = "BAJANDO"
            self.angulo_minimo_actual = angulo_rodilla 
            self.hubo_valgo_actual = False
            self.max_porcentaje_actual = porcentaje
            self.feedback_actual = "Bajando... Mantén la espalda recta."
            self.color_feedback = (255, 255, 0)
            
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_rodilla < self.angulo_minimo_actual:
                self.angulo_minimo_actual = angulo_rodilla
                
            if desviacion_x > self.umbrales["valgo_tolerancia"] and not self.hubo_valgo_actual:
                self.hubo_valgo_actual = True
                self.estado_esqueleto = "error"
                self.feedback_actual = "¡CUIDADO! Rodilla hacia adentro."
                self.color_feedback = (0, 0, 255)
                
            if porcentaje == 100 and not self.hubo_valgo_actual:
                self.estado_esqueleto = "correcto"
                
            if angulo_rodilla > self.angulo_minimo_actual + 5: 
                self.fase_actual = "SUBIENDO"
                self.feedback_actual = "Subiendo..."
                self.color_feedback = (0, 255, 0)
                    
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje) # en subida el % baja
            
            if angulo_rodilla > self.umbrales["inicio_repeticion"]:
                self.fase_actual = "DE PIE"
                
                if self.max_porcentaje_actual >= 100:
                    self.feedback_actual = "Buena repetición."
                    self.stats_repeticiones_totales += 1
                    self.stats_registro_profundidades.append(self.angulo_minimo_actual)
                    if self.hubo_valgo_actual:
                        self.stats_repeticiones_con_valgo += 1
                elif self.max_porcentaje_actual > 40:
                    self.feedback_actual = "Incompleta. Cuenta como error."
                    self.stats_repeticiones_totales += 1
                    self.stats_repeticiones_con_valgo += 1 # Castigado por no llegar
                    self.estado_esqueleto = "error"
                else:
                    self.feedback_actual = "Preparado. Comienza a bajar."
                
                self.max_porcentaje_actual = 0.0

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_valgo
        self.dibujar_estadisticas_ui(frame, "Sentadilla", reps_correctas, self.stats_repeticiones_con_valgo)

    def generar_informe_clinico(self):
        import os
        import datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        # Guardado en base de datos si hay paciente
        media_prof = sum(self.stats_registro_profundidades) / self.stats_repeticiones_totales if self.stats_repeticiones_totales > 0 else 0
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Sentadilla",
                nivel=self.nivel,
                repeticiones=self.stats_repeticiones_totales,
                errores=self.stats_repeticiones_con_valgo,
                profundidad_media=media_prof
            )
        
        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_sentadilla_{fecha_actual}.txt"
        
        # Crear carpeta estructurada si no existe
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "sentadilla")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: SENTADILLA (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Repeticiones completadas: {self.stats_repeticiones_totales}")
        if self.stats_repeticiones_totales > 0:
            lineas_informe.append(f"🔹 Profundidad media: {media_prof:.1f}º")
            lineas_informe.append(f"🔹 Errores de valgo: {self.stats_repeticiones_con_valgo}")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")