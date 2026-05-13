# Archivo: modulo_hombro_lateral.py
import cv2
from modulos.modulo_base import ModuloEjercicio

class ModuloHombroLateral(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"angulo_max": 85.0, "angulo_min": 25.0, "asimetria_tol": 10.0}
        else: # principiante
            self.umbrales = {"angulo_max": 75.0, "angulo_min": 35.0, "asimetria_tol": 20.0}
            
        self.fase_actual = "ABAJO"
        self.repeticiones = 0
        self.errores = 0
        self.hubo_error_repeticion = False
        self.feedback_actual = "Brazos relajados. Listo para subir."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return self.errores

    def obtener_landmarks_relevantes(self) -> list:
        # Cadera(23,24), Hombro(11,12), Codo(13,14)
        return [11, 12, 13, 14, 23, 24]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        cadera_d = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        hombro_d = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        codo_d   = [world_landmarks[14].x, world_landmarks[14].y, world_landmarks[14].z]

        cadera_i = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        hombro_i = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        codo_i   = [world_landmarks[13].x, world_landmarks[13].y, world_landmarks[13].z]
        
        angulo_d = self.calcular_angulo_3d(cadera_d, hombro_d, codo_d)
        angulo_i = self.calcular_angulo_3d(cadera_i, hombro_i, codo_i)
        
        angulo_medio = (angulo_d + angulo_i) / 2.0
        diferencia = abs(angulo_d - angulo_i)

        porcentaje = (angulo_medio / self.umbrales["angulo_max"]) * 100.0 if self.umbrales["angulo_max"] > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "ABAJO" and angulo_medio <= self.umbrales["angulo_min"] + 15:
            self.estado_esqueleto = "neutro"

        if self.fase_actual == "ABAJO":
            if angulo_medio > self.umbrales["angulo_min"] + 10:
                self.fase_actual = "SUBIENDO"
                self.hubo_error_repeticion = False
                self.max_porcentaje_actual = porcentaje
                self.feedback_actual = "Subiendo brazos..."
                self.color_feedback = (255, 255, 0)
        
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if diferencia > self.umbrales["asimetria_tol"]:
                self.hubo_error_repeticion = True
                self.estado_esqueleto = "error"
                self.feedback_actual = "Sube ambos brazos igual."
                self.color_feedback = (0, 0, 255)
                
            if porcentaje == 100 and not self.hubo_error_repeticion:
                self.estado_esqueleto = "correcto"
                
            if angulo_medio < (self.max_porcentaje_actual / 100.0) * self.umbrales["angulo_max"] - 10:
                self.fase_actual = "BAJANDO"
                self.feedback_actual = "Bajando antes de tiempo..."
                self.color_feedback = (0, 165, 255)
            elif angulo_d > self.umbrales["angulo_max"] and angulo_i > self.umbrales["angulo_max"]:
                self.fase_actual = "ARRIBA"
                self.feedback_actual = "Punto máximo, ahora baja lento."
                self.color_feedback = (0, 255, 0)
                
        elif self.fase_actual == "ARRIBA":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio < self.umbrales["angulo_max"] - 10:
                self.fase_actual = "BAJANDO"
                self.feedback_actual = "Bajando controlado..."
                self.color_feedback = (255, 255, 0)
                
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio < self.umbrales["angulo_min"]:
                self.fase_actual = "ABAJO"
                
                if self.max_porcentaje_actual >= 100:
                    self.repeticiones += 1
                    if self.hubo_error_repeticion:
                        self.errores += 1
                    self.feedback_actual = "Buena repetición."
                elif self.max_porcentaje_actual > 40:
                    self.repeticiones += 1
                    self.errores += 1
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Incompleto. Cuenta error."
                
                self.max_porcentaje_actual = 0.0

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.repeticiones - self.errores
        self.dibujar_estadisticas_ui(frame, "Elev. Lateral", reps_correctas, self.errores)
        
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Hombros Laterales",
                nivel=self.nivel,
                repeticiones=self.repeticiones,
                errores=self.errores,
                profundidad_media=0
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_hombro_lateral_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "hombro_lateral")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: HOMBROS LATERALES (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Repeticiones completadas: {self.repeticiones}")
        if self.repeticiones > 0:
            lineas_informe.append(f"🔹 Errores de asimetría: {self.errores}")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")
