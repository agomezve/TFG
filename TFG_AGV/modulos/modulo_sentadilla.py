# Archivo: modulo_sentadilla.py
import cv2
import time
from modulos.modulo_base import ModuloEjercicio

OBJETIVO_REPS = 10

class ModuloSentadilla(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        # Rango real: de pie ~170-175° → profundidad
        # Principiante: 135° (cuarto de sentadilla, muy poca movilidad), Intermedio: 105° (cerca del avanzado), Avanzado: 100° (realista)
        if self.nivel == "avanzado":
            self.umbrales = {"profundidad_maxima": 100.0, "inicio_repeticion": 170.0, "valgo_tolerancia": 0.03}
        elif self.nivel == "intermedio":
            self.umbrales = {"profundidad_maxima": 105.0, "inicio_repeticion": 165.0, "valgo_tolerancia": 0.06}
        else:  # principiante
            self.umbrales = {"profundidad_maxima": 135.0, "inicio_repeticion": 160.0, "valgo_tolerancia": 0.12}

        self.fase_actual = "DE PIE"
        self.angulo_minimo_actual = 180.0
        self.hubo_valgo_actual = False
        self.stats_repeticiones_totales = 0
        self.stats_registro_profundidades = []
        self.stats_repeticiones_con_valgo = 0
        self.errores_consecutivos = 0
        self.feedback_actual = "Listo. Flexiona las rodillas para comenzar."
        self.color_feedback = (255, 255, 255)
        self.tiempo_inicio_rep = None
        self.tiempos_repeticion = []

    def get_errores_acumulados(self) -> int:
        return self.stats_repeticiones_con_valgo

    def get_errores_consecutivos(self) -> int:
        return self.errores_consecutivos

    def get_objetivo_completado(self) -> bool:
        return self.stats_repeticiones_totales >= OBJETIVO_REPS

    def obtener_landmarks_relevantes(self) -> list:
        # Cadera(23,24), Rodilla(25,26), Tobillo(27,28) — ambos lados
        return [23, 24, 25, 26, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        # ── Pierna derecha ──────────────────────────────────────────────────────
        cadera_d  = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        rodilla_d = [world_landmarks[26].x, world_landmarks[26].y, world_landmarks[26].z]
        tobillo_d = [world_landmarks[28].x, world_landmarks[28].y, world_landmarks[28].z]
        # ── Pierna izquierda ────────────────────────────────────────────────────
        cadera_i  = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        rodilla_i = [world_landmarks[25].x, world_landmarks[25].y, world_landmarks[25].z]
        tobillo_i = [world_landmarks[27].x, world_landmarks[27].y, world_landmarks[27].z]

        angulo_d = self.calcular_angulo_3d(cadera_d, rodilla_d, tobillo_d)
        angulo_i = self.calcular_angulo_3d(cadera_i, rodilla_i, tobillo_i)

        # La rodilla promedio marca el avance real de la sentadilla (bilateral)
        angulo_rodilla = (angulo_d + angulo_i) / 2.0

        # Valgo: rodilla cae hacia dentro (X de rodilla < X de cadera en el mismo lado)
        valgo_d = cadera_d[0] - rodilla_d[0]          # positivo → rodilla cae hacia dentro
        valgo_i = rodilla_i[0] - cadera_i[0]           # positivo → rodilla cae hacia dentro
        hay_valgo = (valgo_d > self.umbrales["valgo_tolerancia"]) or \
                    (valgo_i > self.umbrales["valgo_tolerancia"])

        # Porcentaje de barra
        rango = self.umbrales["inicio_repeticion"] - self.umbrales["profundidad_maxima"]
        progreso_grados = self.umbrales["inicio_repeticion"] - angulo_rodilla
        porcentaje = (progreso_grados / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "DE PIE" and angulo_rodilla >= self.umbrales["inicio_repeticion"]:
            self.estado_esqueleto = "neutro"

        # ── Máquina de estados ──────────────────────────────────────────────────
        if angulo_rodilla < self.umbrales["inicio_repeticion"] and self.fase_actual == "DE PIE":
            self.fase_actual = "BAJANDO"
            self.angulo_minimo_actual = angulo_rodilla
            self.hubo_valgo_actual = False
            self.max_porcentaje_actual = porcentaje
            self.tiempo_inicio_rep = time.time()

        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_rodilla < self.angulo_minimo_actual:
                self.angulo_minimo_actual = angulo_rodilla

            if hay_valgo and not self.hubo_valgo_actual:
                self.hubo_valgo_actual = True
                self.estado_esqueleto = "error"
                self.feedback_actual = "¡CUIDADO! Rodilla hacia adentro."
                self.color_feedback = (0, 0, 255)

            if porcentaje >= 100 and not self.hubo_valgo_actual:
                self.estado_esqueleto = "correcto"
                self.feedback_actual = ""

            if angulo_rodilla > self.angulo_minimo_actual + 5:
                self.fase_actual = "SUBIENDO"

        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)

            if angulo_rodilla > self.umbrales["inicio_repeticion"]:
                self.fase_actual = "DE PIE"

                if self.max_porcentaje_actual >= 100:
                    self.stats_repeticiones_totales += 1
                    self.stats_registro_profundidades.append(self.angulo_minimo_actual)
                    if self.tiempo_inicio_rep is not None:
                        self.tiempos_repeticion.append(time.time() - self.tiempo_inicio_rep)
                    if self.hubo_valgo_actual:
                        self.stats_repeticiones_con_valgo += 1
                        self.errores_consecutivos += 1
                    else:
                        self.errores_consecutivos = 0
                    self.feedback_actual = "Buena repetición." if not self.hubo_valgo_actual else "Repetición con valgo."
                    self.color_feedback = (0, 255, 0) if not self.hubo_valgo_actual else (0, 165, 255)
                elif self.max_porcentaje_actual > 65:
                    self.stats_repeticiones_totales += 1
                    self.stats_repeticiones_con_valgo += 1
                    self.errores_consecutivos += 1
                    self.estado_esqueleto = "error"
                    self.feedback_actual = "Incompleta. Cuenta como error."
                    self.color_feedback = (0, 0, 255)
                else:
                    self.feedback_actual = "Listo. Flexiona las rodillas para comenzar."
                    self.color_feedback = (255, 255, 255)

                self.max_porcentaje_actual = 0.0
                self.tiempo_inicio_rep = None

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_valgo
        self.dibujar_estadisticas_ui(frame, "Sentadilla", reps_correctas, self.stats_repeticiones_con_valgo)
        if self.feedback_actual:
            cv2.putText(frame, self.feedback_actual, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.color_feedback, 2)

    def generar_informe_clinico(self):
        import os, datetime
        from database import guardar_sesion, obtener_nombre_paciente

        media_prof = sum(self.stats_registro_profundidades) / self.stats_repeticiones_totales if self.stats_repeticiones_totales > 0 else 0
        media_vel = sum(self.tiempos_repeticion) / len(self.tiempos_repeticion) if self.tiempos_repeticion else 0
        if self.paciente_id is not None:
            guardar_sesion(paciente_id=self.paciente_id, ejercicio="Sentadilla", nivel=self.nivel,
                           repeticiones=self.stats_repeticiones_totales, errores=self.stats_repeticiones_con_valgo,
                           profundidad_media=media_prof)

        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c == ' ']).rstrip().replace(" ", "_").lower()

        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "sentadilla", "informes")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, f"informe_sentadilla_{fecha_actual}.txt")

        lineas_informe = ["=" * 50,
                          f"📋 INFORME CLÍNICO: SENTADILLA (Nivel: {self.nivel.capitalize()})",
                          f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                          "=" * 50,
                          f"🔹 Repeticiones completadas: {self.stats_repeticiones_totales} / {OBJETIVO_REPS}"]
        if self.stats_repeticiones_totales > 0:
            lineas_informe.append(f"🔹 Profundidad media: {media_prof:.1f}º")
            lineas_informe.append(f"🔹 Errores de valgo: {self.stats_repeticiones_con_valgo}")
        if media_vel > 0:
            lineas_informe.append(f"🔹 Velocidad de ejecución media: {media_vel:.2f} s/repetición")
        lineas_informe.append("=" * 50)

        texto_final = "\n".join(lineas_informe)
        print("\n" + texto_final)
        try:
            with open(ruta_informe, "w", encoding="utf-8") as f:
                f.write(texto_final)
            print(f"\n[SISTEMA] ✅ Informe exportado: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar: {e}")