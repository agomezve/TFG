# Archivo: modulo_press_banca.py
# Visión lateral: el paciente está tumbado/semiinclinado con la cámara a su lado.
# MediaPipe detecta el perfil del cuerpo.
# Se analiza el brazo más visible (el que queda hacia la cámara).
# Landmarks relevantes: Hombro, Codo, Muñeca del lado cercano a la cámara.
# En visión lateral, el hombro derecho (12) es el más visible si el usuario está de perfil derecho.
# Usamos la media de ambos brazos igual que en Press Militar pero con umbrales adaptados
# a la posición horizontal (los ángulos son distintos en posición supina).
import cv2
import time
import datetime
from modulos.modulo_base import ModuloEjercicio

OBJETIVO_REPS = 10

class ModuloPressBanca(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel

        # Rango real (banca): codo doblado ~80-100° (barra al pecho) → extensión ~135-148°
        if self.nivel == "avanzado":
            self.umbrales = {
                "extension_minima": 140.0,
                "flexion_maxima": 80.0,
                "desalineacion_maxima": 0.10
            }
        elif self.nivel == "intermedio":
            self.umbrales = {
                "extension_minima": 135.0,
                "flexion_maxima": 90.0,
                "desalineacion_maxima": 0.13
            }
        else:  # principiante
            self.umbrales = {
                "extension_minima": 110.0,
                "flexion_maxima": 105.0,
                "desalineacion_maxima": 0.18
            }

        # Máquina de estados: ABAJO → EMPUJANDO → ARRIBA → BAJANDO → ABAJO
        self.fase_actual = "ABAJO"
        self.angulo_maximo_actual = 0.0
        self.hubo_desalineacion = False

        # Estadísticas
        self.stats_repeticiones_totales = 0
        self.stats_registro_extension = []
        self.stats_repeticiones_con_error = 0
        self.errores_consecutivos = 0

        self.feedback_actual = "Tumbado. Baja la barra al pecho y empuja."
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
        # Hombro(11,12), Codo(13,14), Muñeca(15,16) — igual que press militar
        return [11, 12, 13, 14, 15, 16]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        # Brazo derecho
        hombro_der = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        codo_der   = [world_landmarks[14].x, world_landmarks[14].y, world_landmarks[14].z]
        muneca_der = [world_landmarks[16].x, world_landmarks[16].y, world_landmarks[16].z]

        # Brazo izquierdo
        hombro_izq = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        codo_izq   = [world_landmarks[13].x, world_landmarks[13].y, world_landmarks[13].z]
        muneca_izq = [world_landmarks[15].x, world_landmarks[15].y, world_landmarks[15].z]

        angulo_der = self.calcular_angulo_3d(hombro_der, codo_der, muneca_der)
        angulo_izq = self.calcular_angulo_3d(hombro_izq, codo_izq, muneca_izq)

        # Desalineación: diferencia de Y entre codo y muñeca (en visión lateral, Y indica altura)
        desalineacion_der = abs(codo_der[1] - muneca_der[1])
        desalineacion_izq = abs(codo_izq[1] - muneca_izq[1])

        angulo_mas_bajo = min(angulo_der, angulo_izq)
        angulo_mas_alto = max(angulo_der, angulo_izq)
        desalineacion_max = max(desalineacion_der, desalineacion_izq)

        # Progreso basado en la media de ambos brazos para mayor equidad
        angulo_medio_prog = (angulo_der + angulo_izq) / 2.0
        rango = self.umbrales["extension_minima"] - self.umbrales["flexion_maxima"]
        progreso = angulo_medio_prog - self.umbrales["flexion_maxima"]
        porcentaje = (progreso / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "ABAJO" and angulo_medio_prog <= self.umbrales["flexion_maxima"] + 15:
            self.estado_esqueleto = "neutro"

        # --- FSM ---
        if angulo_medio_prog < self.umbrales["flexion_maxima"] and self.fase_actual == "ABAJO":
            self.fase_actual = "EMPUJANDO"
            self.angulo_maximo_actual = angulo_medio_prog
            self.hubo_desalineacion = False
            self.max_porcentaje_actual = porcentaje
            self.feedback_actual = ""
            self.color_feedback = (255, 255, 255)
            self.tiempo_inicio_rep = time.time()

        elif self.fase_actual == "EMPUJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_medio_prog > self.angulo_maximo_actual:
                self.angulo_maximo_actual = angulo_medio_prog

            if desalineacion_max > self.umbrales["desalineacion_maxima"] and not self.hubo_desalineacion:
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
                    self.feedback_actual = "Repetición registrada."
                elif self.max_porcentaje_actual > 65:  # Movimiento parcial significativo → error
                    self.stats_repeticiones_totales += 1
                    self.stats_repeticiones_con_error += 1
                    self.errores_consecutivos += 1
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Incompleta. Cuenta error."

                self.max_porcentaje_actual = 0.0
                self.tiempo_inicio_rep = None

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_error
        self.dibujar_estadisticas_ui(frame, "Press Banca", reps_correctas, self.stats_repeticiones_con_error)
        cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os
        from database import guardar_sesion, obtener_nombre_paciente

        media_ext = sum(self.stats_registro_extension) / self.stats_repeticiones_totales if self.stats_repeticiones_totales > 0 else 0
        media_vel = sum(self.tiempos_repeticion) / len(self.tiempos_repeticion) if self.tiempos_repeticion else 0

        if self.paciente_id is not None:
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Press Banca",
                nivel=self.nivel,
                repeticiones=self.stats_repeticiones_totales,
                errores=self.stats_repeticiones_con_error,
                profundidad_media=media_ext
            )

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c == ' ']).rstrip().replace(" ", "_").lower()

        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_press_banca_{fecha_actual}.txt"

        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "press_banca", "informes")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)

        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO DE TELEREHABILITACIÓN")
        lineas_informe.append(f"Ejercicio: Press Banca (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50 + "\n")

        if self.stats_repeticiones_totales == 0:
            lineas_informe.append("❌ RESULTADO: No se ha detectado ninguna repetición completa.\n")
            lineas_informe.append("Posibles causas: El paciente no alcanzó el rango mínimo de flexión o extensión.")
        else:
            porcentaje_error = (self.stats_repeticiones_con_error / self.stats_repeticiones_totales) * 100
            lineas_informe.append("📊 DATOS CUANTITATIVOS:")
            lineas_informe.append(f" - Repeticiones completadas: {self.stats_repeticiones_totales} / {OBJETIVO_REPS}")
            lineas_informe.append(f" - Extensión media del codo: {media_ext:.1f}° (Objetivo: > {self.umbrales['extension_minima']}°)")
            lineas_informe.append(f" - Repeticiones con desalineación: {self.stats_repeticiones_con_error} ({porcentaje_error:.0f}%)")
            if media_vel > 0:
                lineas_informe.append(f" - Velocidad de ejecución media: {media_vel:.2f} s/repetición\n")

            lineas_informe.append("💡 CONSEJOS Y CORRECCIONES AUTOMÁTICAS:")
            if media_ext >= self.umbrales["extension_minima"]:
                lineas_informe.append(" [RANGO] ✅ Extensión óptima alcanzada en el press de banca.")
            else:
                lineas_informe.append(" [RANGO] ⚠️ Intenta estirar más el brazo al final del empuje.")

            if porcentaje_error > 0:
                lineas_informe.append(" [TÉCNICA] 🚨 Desalineación del codo detectada.")
                lineas_informe.append("             -> Mantén el codo a 45-75° del torso durante el descenso.")
            else:
                lineas_informe.append(" [TÉCNICA] ✅ Alineación correcta del codo en todo el recorrido.")

        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)

        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")
