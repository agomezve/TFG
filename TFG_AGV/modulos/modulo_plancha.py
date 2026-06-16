# Archivo: modulo_plancha.py
import cv2
import time
from modulos.modulo_base import ModuloEjercicio

class ModuloPlancha(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        # En plancha la clave es que hombro, cadera y tobillo formen una línea recta (~180º)
        if self.nivel == "avanzado":
            self.umbrales = {"tolerancia_inferior": 170.0, "tolerancia_superior": 190.0}
            self.objetivo_segundos = 60
        elif self.nivel == "intermedio":
            self.umbrales = {"tolerancia_inferior": 165.0, "tolerancia_superior": 195.0}
            self.objetivo_segundos = 40
        else:  # principiante
            self.umbrales = {"tolerancia_inferior": 160.0, "tolerancia_superior": 200.0}
            self.objetivo_segundos = 20
            
        self.tiempo_inicio = None
        self.tiempo_ultimo_frame = None
        
        self.segundos_totales = 0.0
        self.segundos_error = 0.0
        
        self.feedback_actual = "Colócate en posición horizontal."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return 0  # Ejercicio isométrico, no autoterminamos por errores consecutivos

    def get_objetivo_completado(self) -> bool:
        return self.segundos_totales >= self.objetivo_segundos

    def obtener_landmarks_relevantes(self) -> list:
        # Hombro(11,12), Cadera(23,24), Tobillo(27,28)
        return [11, 12, 23, 24, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        hombro = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        cadera = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        tobillo = [world_landmarks[28].x, world_landmarks[28].y, world_landmarks[28].z]
        
        angulo_cuerpo = self.calcular_angulo_3d(hombro, cadera, tobillo)

        t_actual = time.time()
        
        if angulo_cuerpo > 140:
            if self.tiempo_ultimo_frame is not None:
                dt = t_actual - self.tiempo_ultimo_frame
                self.segundos_totales += dt
                
                if angulo_cuerpo < self.umbrales["tolerancia_inferior"] or angulo_cuerpo > self.umbrales["tolerancia_superior"]:
                    self.segundos_error += dt
                    self.feedback_actual = "¡CUIDADO! Alinea la cadera con tu espalda."
                    self.color_feedback = (0, 0, 255)
                else:
                    self.feedback_actual = "Posición correcta. ¡Aguanta!"
                    self.color_feedback = (0, 255, 0)
            
            self.tiempo_ultimo_frame = t_actual
        else:
            self.tiempo_ultimo_frame = None
            self.feedback_actual = "Colócate en posición."
            self.color_feedback = (255, 255, 255)

        # Barra indica % de tiempo transcurrido hacia el objetivo
        porcentaje_tiempo = (self.segundos_totales / self.objetivo_segundos) * 100.0
        porcentaje_tiempo = max(0, min(100, porcentaje_tiempo))
            
        self.dibujar_barra_progreso(frame, porcentaje_tiempo)
        
        if self.color_feedback == (0, 0, 255):
            self.estado_esqueleto = "error"
        elif self.color_feedback == (0, 255, 0):
            self.estado_esqueleto = "correcto"
        else:
            self.estado_esqueleto = "neutro"

        segundos_restantes = max(0, int(self.objetivo_segundos - self.segundos_totales))
        self.dibujar_estadisticas_ui(frame, "Plancha", f"{int(self.segundos_totales - self.segundos_error)}s", f"{int(self.segundos_error)}s")
        cv2.putText(frame, f"Objetivo: {segundos_restantes}s restantes ({self.objetivo_segundos}s total)", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Plancha",
                nivel=self.nivel,
                repeticiones=int(self.segundos_totales),
                errores=int(self.segundos_error),
                profundidad_media=0
            )
            
        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_plancha_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "usuarios", nombre_pac_limpio, fecha_dia, "plancha", "informes")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: PLANCHA ISOMÉTRICA (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Objetivo: {self.objetivo_segundos} segundos")
        lineas_informe.append(f"🔹 Tiempo total aguantado: {int(self.segundos_totales)} s")
        lineas_informe.append(f"🔹 Tiempo en postura correcta: {max(0, int(self.segundos_totales - self.segundos_error))} s")
        lineas_informe.append(f"🔹 Tiempo en postura hundida/arqueada: {int(self.segundos_error)} s")
        objetivo_alcanzado = "✅ SÍ" if self.segundos_totales >= self.objetivo_segundos else "❌ NO"
        lineas_informe.append(f"🔹 Objetivo alcanzado: {objetivo_alcanzado}")
        lineas_informe.append("=" * 50)
        
        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")
