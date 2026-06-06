# Archivo: modulo_press_militar.py
import cv2
import time
import datetime
from modulos.modulo_base import ModuloEjercicio

OBJETIVO_REPS = 10

class ModuloPressMilitar(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        
        # 1. Umbrales Clínicos Computacionales
        # flexion_maxima: ángulo del codo en posición baja (brazos a altura del hombro, codos doblados ~90°)
        # extension_minima: ángulo del codo cuando el brazo está extendido hacia arriba
        # Rango real: ~90° (abajo) → ~148-155° (arriba)
        if self.nivel == "avanzado":
            self.umbrales = {
                "extension_minima": 142.0,   # Realista
                "flexion_maxima": 100.0,      # Codos doblados (bajando hasta la barbilla)
                "desalineacion_maxima": 0.12
            }
        elif self.nivel == "intermedio":
            self.umbrales = {
                "extension_minima": 138.0,   # Cerca del avanzado
                "flexion_maxima": 105.0,      # Bajada un poco menos estricta
                "desalineacion_maxima": 0.13
            }
        else:  # principiante
            self.umbrales = {
                "extension_minima": 115.0,   # Muy básico, poca movilidad
                "flexion_maxima": 115.0,      # Posición baja permisiva
                "desalineacion_maxima": 0.18
            }
        
        # 2. Máquina de Estados
        self.fase_actual = "ABAJO"
        self.angulo_maximo_actual = 0.0
        self.hubo_desalineacion = False
        
        # 3. Memoria Telemétrica
        self.stats_repeticiones_totales = 0
        self.stats_registro_extension = []
        self.stats_repeticiones_con_error = 0
        self.errores_consecutivos = 0
        
        self.feedback_actual = "Codos a altura de hombro. Empuja hacia arriba."
        self.color_feedback = (255, 255, 255)
        # Velocidad de ejecución
        self.tiempo_inicio_rep = None
        self.tiempos_repeticion = []

    def get_errores_acumulados(self) -> int:
        return self.stats_repeticiones_con_error

    def get_errores_consecutivos(self) -> int:
        return self.errores_consecutivos

    def get_objetivo_completado(self) -> bool:
        return self.stats_repeticiones_totales >= OBJETIVO_REPS

    def obtener_landmarks_relevantes(self) -> list:
        # Hombro(11,12), Codo(13,14), Muñeca(15,16) — ambos lados
        return [11, 12, 13, 14, 15, 16]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        # Brazo derecho
        hombro_der = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        codo_der = [world_landmarks[14].x, world_landmarks[14].y, world_landmarks[14].z]
        muneca_der = [world_landmarks[16].x, world_landmarks[16].y, world_landmarks[16].z]
        
        # Brazo izquierdo
        hombro_izq = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        codo_izq = [world_landmarks[13].x, world_landmarks[13].y, world_landmarks[13].z]
        muneca_izq = [world_landmarks[15].x, world_landmarks[15].y, world_landmarks[15].z]
        
        angulo_codo_der = self.calcular_angulo_3d(hombro_der, codo_der, muneca_der)
        desviacion_x_der = abs(codo_der[0] - muneca_der[0])
        
        angulo_codo_izq = self.calcular_angulo_3d(hombro_izq, codo_izq, muneca_izq)
        desviacion_x_izq = abs(codo_izq[0] - muneca_izq[0])

        angulo_mas_bajo = min(angulo_codo_der, angulo_codo_izq)
        angulo_mas_alto = max(angulo_codo_der, angulo_codo_izq)
        desviacion_max = max(desviacion_x_der, desviacion_x_izq)

        # Progreso basado en la media de ambos brazos (no el peor) para mayor equidad
        angulo_medio_prog = (angulo_codo_der + angulo_codo_izq) / 2.0
        rango = self.umbrales["extension_minima"] - self.umbrales["flexion_maxima"]
        progreso_grados = angulo_medio_prog - self.umbrales["flexion_maxima"]
        porcentaje = (progreso_grados / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "ABAJO" and angulo_medio_prog <= self.umbrales["flexion_maxima"] + 15:
            self.estado_esqueleto = "neutro"

        # --- MOTOR DE REGLAS CLÍNICAS (BILATERAL) ---
        if angulo_medio_prog < self.umbrales["flexion_maxima"] and self.fase_actual == "ABAJO":
            self.fase_actual = "SUBIENDO"
            self.angulo_maximo_actual = angulo_medio_prog
            self.hubo_desalineacion = False
            self.max_porcentaje_actual = porcentaje
            self.feedback_actual = ""
            self.color_feedback = (255, 255, 255)
            self.tiempo_inicio_rep = time.time()
            
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio_prog > self.angulo_maximo_actual:
                self.angulo_maximo_actual = angulo_medio_prog
            
            if desviacion_max > self.umbrales["desalineacion_maxima"] and not self.hubo_desalineacion:
                self.hubo_desalineacion = True
                self.estado_esqueleto = "error"
                self.feedback_actual = "¡Codo desalineado!"
                self.color_feedback = (0, 0, 255)
                
            if porcentaje == 100 and not self.hubo_desalineacion:
                self.estado_esqueleto = "correcto"
                
            if angulo_medio_prog < self.angulo_maximo_actual - 10:
                self.fase_actual = "BAJANDO"
                self.feedback_actual = ""
                self.color_feedback = (255, 255, 255)
            elif angulo_medio_prog > self.umbrales["extension_minima"]:
                self.fase_actual = "ARRIBA"
                self.feedback_actual = ""
                
        elif self.fase_actual == "ARRIBA":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio_prog < self.umbrales["extension_minima"] - 10:
                self.fase_actual = "BAJANDO"
                self.feedback_actual = ""
            
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio_prog < self.umbrales["flexion_maxima"]:
                self.fase_actual = "ABAJO"
                
                if self.max_porcentaje_actual >= 100:
                    self.stats_repeticiones_totales += 1
                    self.stats_registro_extension.append(self.angulo_maximo_actual)
                    if self.tiempo_inicio_rep is not None:
                        self.tiempos_repeticion.append(time.time() - self.tiempo_inicio_rep)
                    if self.hubo_desalineacion:
                        self.stats_repeticiones_con_error += 1
                        self.errores_consecutivos += 1
                    else:
                        self.errores_consecutivos = 0
                elif self.max_porcentaje_actual > 65:  # Movimiento parcial con recorrido suficiente → error
                    self.stats_repeticiones_totales += 1
                    self.stats_repeticiones_con_error += 1
                    self.errores_consecutivos += 1
                    self.estado_esqueleto = "error"
                
                self.max_porcentaje_actual = 0.0
                self.tiempo_inicio_rep = None

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_error
        self.dibujar_estadisticas_ui(frame, "Press Militar", reps_correctas, self.stats_repeticiones_con_error)
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        """Genera el reporte por consola y lo exporta a un archivo de texto plano (.txt)."""
        import os
        from database import guardar_sesion, obtener_nombre_paciente
        
        media_ext = sum(self.stats_registro_extension) / self.stats_repeticiones_totales if self.stats_repeticiones_totales > 0 else 0
        media_vel = sum(self.tiempos_repeticion) / len(self.tiempos_repeticion) if self.tiempos_repeticion else 0
        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Press Militar",
                nivel=self.nivel,
                repeticiones=self.stats_repeticiones_totales,
                errores=self.stats_repeticiones_con_error,
                profundidad_media=media_ext
            )
        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_press_militar_{fecha_actual}.txt"
        
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "usuarios", nombre_pac_limpio, fecha_dia, "press_militar", "informes")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        lineas_informe = []
        lineas_informe.append("="*50)
        lineas_informe.append(f"📋 INFORME CLÍNICO DE TELEREHABILITACIÓN")
        lineas_informe.append(f"Ejercicio: Press Militar (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("="*50 + "\n")
        
        if self.stats_repeticiones_totales == 0:
            lineas_informe.append("❌ RESULTADO: No se ha detectado ninguna repetición completa.\n")
            lineas_informe.append("Posibles causas: El paciente no alcanzó el rango mínimo de flexión o extensión estipulado por los umbrales clínicos.")
        else:
            porcentaje_error = (self.stats_repeticiones_con_error / self.stats_repeticiones_totales) * 100
            
            lineas_informe.append("📊 DATOS CUANTITATIVOS:")
            lineas_informe.append(f" - Repeticiones válidas completadas: {self.stats_repeticiones_totales} / {OBJETIVO_REPS}")
            lineas_informe.append(f" - Extensión media del codo: {media_ext:.1f} grados (Objetivo: > {self.umbrales['extension_minima']} grados)")
            lineas_informe.append(f" - Repeticiones con desalineación de antebrazo: {self.stats_repeticiones_con_error} ({porcentaje_error:.0f}%)")
            if media_vel > 0:
                lineas_informe.append(f" - Velocidad de ejecución media: {media_vel:.2f} s/repetición\n")
            
            lineas_informe.append("💡 CONSEJOS Y CORRECCIONES AUTOMÁTICAS:")
            if media_ext >= self.umbrales["extension_minima"]:
                lineas_informe.append(" [RANGO] ✅ Excelente. Alcanzaste la extensión óptima en el press.")
            else:
                lineas_informe.append(" [RANGO] ⚠️ Limitación en la extensión. Intenta estirar el brazo un poco más arriba al finalizar el empuje.")
                
            if porcentaje_error > 0:
                lineas_informe.append(" [TÉCNICA] 🚨 ALERTA: Has perdido la verticalidad del antebrazo durante el recorrido.")
                lineas_informe.append("             -> Corrección: Mantén la muñeca alineada justo por encima del codo para evitar tensión en el manguito rotador.")
            else:
                lineas_informe.append(" [TÉCNICA] ✅ Alineación perfecta del antebrazo. Sin desviaciones riesgosas.")

        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error crítico al intentar guardar el informe: {e}")