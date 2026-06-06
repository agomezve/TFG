# Archivo: modulo_propiocepcion.py
import cv2
import time
import math
from modulos.modulo_base import ModuloEjercicio

class ModuloPropiocepcion(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"desviacion_maxima": 0.03}
            self.objetivo_segundos = 60
        elif self.nivel == "intermedio":
            self.umbrales = {"desviacion_maxima": 0.04}
            self.objetivo_segundos = 40
        else:
            self.umbrales = {"desviacion_maxima": 0.05}
            self.objetivo_segundos = 20
            
        self.tiempo_ultimo_frame = None
        self.centro_x_referencia = None
        
        self.segundos_totales = 0.0
        self.puntos_inestabilidad = 0
        
        self.feedback_actual = "Ponte de pie sobre una pierna."
        self.color_feedback = (255, 255, 255)

    def get_errores_acumulados(self) -> int:
        return 0  # Es isométrico, no expulsamos por errores consecutivos

    def get_objetivo_completado(self) -> bool:
        return self.segundos_totales >= self.objetivo_segundos

    def obtener_landmarks_relevantes(self) -> list:
        # Cadera(23,24), Rodilla(25,26), Tobillo(27,28)
        return [23, 24, 25, 26, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        cadera_d = landmarks_2d[24].x
        cadera_i = landmarks_2d[23].x
        centro_x_actual = (cadera_d + cadera_i) / 2.0
        
        tobillo_y_i = landmarks_2d[27].y
        tobillo_y_d = landmarks_2d[28].y
        diferencia_altura_tobillos = abs(tobillo_y_i - tobillo_y_d)

        t_actual = time.time()
        
        if diferencia_altura_tobillos > 0.05:
            if self.tiempo_ultimo_frame is not None:
                dt = t_actual - self.tiempo_ultimo_frame
                self.segundos_totales += dt
                
                if self.centro_x_referencia is not None:
                    desplazamiento = abs(centro_x_actual - self.centro_x_referencia)
                    if desplazamiento > self.umbrales["desviacion_maxima"]:
                        self.puntos_inestabilidad += 1
                        self.centro_x_referencia = centro_x_actual
                        self.feedback_actual = "¡Inestabilidad detectada! Rectifica."
                        self.color_feedback = (0, 0, 255)
                    else:
                        self.feedback_actual = "Equilibrio correcto."
                        self.color_feedback = (0, 255, 0)
                else:
                    self.centro_x_referencia = centro_x_actual
            
            self.tiempo_ultimo_frame = t_actual
        else:
            self.tiempo_ultimo_frame = None
            self.centro_x_referencia = None
            self.feedback_actual = "Levanta un pie para empezar."
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
        self.dibujar_estadisticas_ui(frame, "Apoyo Monopodal", f"{int(self.segundos_totales)}s", self.puntos_inestabilidad)
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)
        cv2.putText(frame, f"Objetivo: {segundos_restantes}s restantes ({self.objetivo_segundos}s total)", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Propiocepcion",
                nivel=self.nivel,
                repeticiones=int(self.segundos_totales),
                errores=self.puntos_inestabilidad,
                profundidad_media=0
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_propiocepcion_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "usuarios", nombre_pac_limpio, fecha_dia, "propiocepcion", "informes")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: PROPIOCEPCIÓN MONOPODAL (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"🔹 Objetivo: {self.objetivo_segundos} segundos")
        lineas_informe.append(f"🔹 Tiempo total de equilibrio: {int(self.segundos_totales)} s")
        lineas_informe.append(f"🔹 Puntos de inestabilidad detectados: {self.puntos_inestabilidad}")
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
