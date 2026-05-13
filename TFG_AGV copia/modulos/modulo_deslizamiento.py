# Archivo: modulo_deslizamiento.py
import cv2
from modulos.modulo_base import ModuloEjercicio

class ModuloDeslizamiento(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        self.max_flexion = 0.0
        
        self.feedback_actual = "Desliza la mano hacia arriba."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return 0

    def obtener_landmarks_relevantes(self) -> list:
        # Cadera(24), Hombro(12), Codo(14)
        # Evaluaremos ambos lados y nos quedaremos con el que más se mueva o el promedio
        return [11, 12, 13, 14, 23, 24]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        cadera_d = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        hombro_d = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        codo_d   = [world_landmarks[14].x, world_landmarks[14].y, world_landmarks[14].z]

        cadera_i = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        hombro_i = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        codo_i   = [world_landmarks[13].x, world_landmarks[13].y, world_landmarks[13].z]
        
        # Angulo en el plano sagital/frontal entre cadera, hombro y codo
        angulo_d = self.calcular_angulo_3d(cadera_d, hombro_d, codo_d)
        angulo_i = self.calcular_angulo_3d(cadera_i, hombro_i, codo_i)
        
        # Nos quedamos con el ángulo máximo que esté alcanzando el brazo
        angulo_max_instante = max(angulo_d, angulo_i)

        if angulo_max_instante > self.max_flexion:
            self.max_flexion = angulo_max_instante
            self.feedback_actual = f"Nuevo máximo: {int(self.max_flexion)}º"
            self.color_feedback = (0, 255, 0)
        elif angulo_max_instante < self.max_flexion - 20:
            self.feedback_actual = "Relajando..."
            self.color_feedback = (255, 255, 255)

        porcentaje = (self.max_flexion / 180.0) * 100.0
        self.dibujar_barra_progreso(frame, porcentaje)
        
        self.en_error = False
        self.dibujar_estadisticas_ui(frame, "Deslizamiento", int(self.max_flexion), 0)
        
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Deslizamiento Pared",
                nivel=self.nivel,
                repeticiones=int(self.max_flexion), # Reutilizamos repeticiones para guardar los grados
                errores=0,
                profundidad_media=0
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_deslizamiento_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "deslizamiento")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: DESLIZAMIENTO EN PARED (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Ángulo máximo de flexión alcanzado: {int(self.max_flexion)}º")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")
