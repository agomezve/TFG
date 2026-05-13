# Archivo: modulo_hip_thrust.py
import cv2
from modulos.modulo_base import ModuloEjercicio

class ModuloHipThrust(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"extension_completa": 175.0, "descenso": 120.0, "tolerancia_extension": 5.0}
        else: # principiante
            self.umbrales = {"extension_completa": 165.0, "descenso": 130.0, "tolerancia_extension": 15.0}
            
        self.fase_actual = "ABAJO"
        self.repeticiones = 0
        self.errores = 0
        
        # Guardaremos los grados máximos alcanzados en cada repe para hacer estadística
        self.maximos_alcanzados = []
        self.max_actual = 0.0
        self.hubo_error_actual = False
        
        self.feedback_actual = "Preparado. Hombros apoyados, sube la cadera."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return self.errores

    def obtener_landmarks_relevantes(self) -> list:
        # Hombro(11,12), Cadera(23,24), Rodilla(25,26)
        return [11, 12, 23, 24, 25, 26]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        hombro_d = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        cadera_d = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        rodilla_d = [world_landmarks[26].x, world_landmarks[26].y, world_landmarks[26].z]

        hombro_i = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        cadera_i = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        rodilla_i = [world_landmarks[25].x, world_landmarks[25].y, world_landmarks[25].z]
        
        angulo_d = self.calcular_angulo_3d(hombro_d, cadera_d, rodilla_d)
        angulo_i = self.calcular_angulo_3d(hombro_i, cadera_i, rodilla_i)
        
        # Nos quedamos con el promedio para la extensión de cadera general
        angulo_cadera = (angulo_d + angulo_i) / 2.0

        porcentaje = ((angulo_cadera - self.umbrales["descenso"]) / (self.umbrales["extension_completa"] - self.umbrales["descenso"])) * 100.0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "ABAJO" and angulo_cadera <= self.umbrales["descenso"] + 15:
            self.estado_esqueleto = "neutro"
        
        if self.fase_actual == "ABAJO":
            if angulo_cadera > self.umbrales["descenso"] + 10:
                self.fase_actual = "SUBIENDO"
                self.max_actual = angulo_cadera
                self.hubo_error_actual = False
                self.max_porcentaje_actual = porcentaje
                self.feedback_actual = "Empujando arriba..."
                self.color_feedback = (255, 255, 0)
                
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_cadera > self.max_actual:
                self.max_actual = angulo_cadera
                
            if porcentaje == 100 and not self.hubo_error_actual:
                self.estado_esqueleto = "correcto"

            if angulo_cadera < self.max_actual - 10:
                # Si empieza a bajar pero no llegó arriba, lo marcamos como error de rango
                self.hubo_error_actual = True
                self.estado_esqueleto = "error"
                self.fase_actual = "BAJANDO"
                self.feedback_actual = "¡Te ha faltado subir más la cadera!"
                self.color_feedback = (0, 0, 255)
            elif angulo_cadera >= self.umbrales["extension_completa"]:
                self.fase_actual = "ARRIBA"
                self.feedback_actual = "Extensión completa. Baja controlando."
                self.color_feedback = (0, 255, 0)
                
        elif self.fase_actual == "ARRIBA":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_cadera < self.umbrales["extension_completa"] - 10:
                self.fase_actual = "BAJANDO"
                self.feedback_actual = "Bajando cadera..."
                self.color_feedback = (255, 255, 0)
                
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_cadera < self.umbrales["descenso"]:
                self.fase_actual = "ABAJO"
                
                if self.max_porcentaje_actual >= 100:
                    self.repeticiones += 1
                    self.maximos_alcanzados.append(self.max_actual)
                    if self.hubo_error_actual:
                        self.errores += 1
                    self.feedback_actual = "Repetición registrada."
                elif self.max_porcentaje_actual > 40:
                    self.repeticiones += 1
                    self.errores += 1
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Incompleto. Cuenta error."
                
                self.max_porcentaje_actual = 0.0

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.repeticiones - self.errores
        self.dibujar_estadisticas_ui(frame, "Hip Thrust", reps_correctas, self.errores)
        
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        media_ext = sum(self.maximos_alcanzados) / self.repeticiones if self.repeticiones > 0 else 0
        
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Hip Thrust",
                nivel=self.nivel,
                repeticiones=self.repeticiones,
                errores=self.errores,
                profundidad_media=media_ext
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_hip_thrust_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "hip_thrust")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: HIP THRUST (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Repeticiones completadas: {self.repeticiones}")
        if self.repeticiones > 0:
            lineas_informe.append(f"🔹 Extensión de cadera media alcanzada: {media_ext:.1f}º")
            lineas_informe.append(f"🔹 Repeticiones sin completar el rango superior: {self.errores}")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
        except IOError:
            pass
