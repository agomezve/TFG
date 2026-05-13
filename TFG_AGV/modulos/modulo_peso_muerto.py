# Archivo: modulo_peso_muerto.py
import cv2
from modulos.modulo_base import ModuloEjercicio

class ModuloPesoMuerto(ModuloEjercicio):
    def __init__(self, nivel="principiante"):
        self.nivel = nivel
        if self.nivel == "avanzado":
            self.umbrales = {"profundidad_maxima": 80.0, "inicio_repeticion": 165.0, "rodilla_error": 115.0} # Más exigente con la rodilla y más profundo
        else: # principiante
            self.umbrales = {"profundidad_maxima": 100.0, "inicio_repeticion": 150.0, "rodilla_error": 100.0}
            
        self.fase_actual = "DE PIE"
        self.angulo_minimo_actual = 180.0
        self.hubo_error_rodilla = False
        self.stats_repeticiones_totales = 0
        self.stats_registro_profundidades = []
        self.stats_repeticiones_con_error = 0

    def get_errores_acumulados(self) -> int:
        return self.stats_repeticiones_con_error

    def obtener_landmarks_relevantes(self) -> list:
        # Hombro(11,12), Cadera(23,24), Rodilla(25,26), Tobillo(27,28)
        return [11, 12, 23, 24, 25, 26, 27, 28]

    def evaluar_postura(self, world_landmarks, landmarks_2d, frame):
        hombro_d = [world_landmarks[12].x, world_landmarks[12].y, world_landmarks[12].z]
        cadera_d = [world_landmarks[24].x, world_landmarks[24].y, world_landmarks[24].z]
        rodilla_d = [world_landmarks[26].x, world_landmarks[26].y, world_landmarks[26].z]
        tobillo_d = [world_landmarks[28].x, world_landmarks[28].y, world_landmarks[28].z]

        hombro_i = [world_landmarks[11].x, world_landmarks[11].y, world_landmarks[11].z]
        cadera_i = [world_landmarks[23].x, world_landmarks[23].y, world_landmarks[23].z]
        rodilla_i = [world_landmarks[25].x, world_landmarks[25].y, world_landmarks[25].z]
        tobillo_i = [world_landmarks[27].x, world_landmarks[27].y, world_landmarks[27].z]

        angulo_cadera_d = self.calcular_angulo_3d(hombro_d, cadera_d, rodilla_d)
        angulo_cadera_i = self.calcular_angulo_3d(hombro_i, cadera_i, rodilla_i)
        
        angulo_rodilla_d = self.calcular_angulo_3d(cadera_d, rodilla_d, tobillo_d)
        angulo_rodilla_i = self.calcular_angulo_3d(cadera_i, rodilla_i, tobillo_i)

        angulo_cadera = min(angulo_cadera_d, angulo_cadera_i) # Evaluamos el más profundo
        angulo_rodilla = min(angulo_rodilla_d, angulo_rodilla_i) # Evaluamos el que más se dobla

        # Calcular porcentaje
        rango = self.umbrales["inicio_repeticion"] - self.umbrales["profundidad_maxima"]
        progreso_grados = self.umbrales["inicio_repeticion"] - angulo_cadera
        porcentaje = (progreso_grados / rango) * 100.0 if rango > 0 else 0
        porcentaje = max(0, min(100, porcentaje))

        if not hasattr(self, 'max_porcentaje_actual'):
            self.max_porcentaje_actual = 0.0

        if self.fase_actual == "DE PIE" and angulo_cadera >= self.umbrales["inicio_repeticion"]:
            self.estado_esqueleto = "neutro"

        # Máquina de estados
        if angulo_cadera < self.umbrales["inicio_repeticion"] and self.fase_actual == "DE PIE":
            self.fase_actual = "BAJANDO"
            self.angulo_minimo_actual = angulo_cadera 
            self.hubo_error_rodilla = False
            self.max_porcentaje_actual = porcentaje
            
        elif self.fase_actual == "BAJANDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            if angulo_cadera < self.angulo_minimo_actual:
                self.angulo_minimo_actual = angulo_cadera
                
            if angulo_rodilla < self.umbrales["rodilla_error"]:
                self.hubo_error_rodilla = True
                self.estado_esqueleto = "error"
                
            if porcentaje == 100 and not self.hubo_error_rodilla:
                self.estado_esqueleto = "correcto"
                
            if angulo_cadera > self.angulo_minimo_actual + 5: 
                self.fase_actual = "SUBIENDO"
                    
        elif self.fase_actual == "SUBIENDO":
            self.max_porcentaje_actual = max(self.max_porcentaje_actual, porcentaje)
            
            if angulo_cadera > self.umbrales["inicio_repeticion"]:
                self.fase_actual = "DE PIE"
                
                if self.max_porcentaje_actual >= 100:
                    self.stats_repeticiones_totales += 1
                    if self.hubo_error_rodilla:
                        self.stats_repeticiones_con_error += 1
                    self.stats_registro_profundidades.append(self.angulo_minimo_actual)
                elif self.max_porcentaje_actual > 40:
                    self.stats_repeticiones_totales += 1
                    self.stats_repeticiones_con_error += 1
                    self.estado_esqueleto = "error"
                    
                self.max_porcentaje_actual = 0.0

        self.dibujar_barra_progreso(frame, porcentaje)
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_error
        self.dibujar_estadisticas_ui(frame, "Peso Muerto", reps_correctas, self.stats_repeticiones_con_error)

    def generar_informe_clinico(self):
        import os
        import datetime
        from database import guardar_sesion, obtener_nombre_paciente
        
        # Guardado en base de datos si hay paciente
        if self.paciente_id is not None:
            profundidad_media = sum(self.stats_registro_profundidades) / len(self.stats_registro_profundidades) if self.stats_registro_profundidades else 0.0
            guardar_sesion(
                paciente_id=self.paciente_id,
                ejercicio="Peso Muerto",
                nivel=self.nivel,
                repeticiones=self.stats_repeticiones_totales,
                errores=self.stats_repeticiones_con_error,
                profundidad_media=profundidad_media,
                observaciones="Sin anomalías severas." if self.stats_repeticiones_con_error == 0 else "Alerta de flexión excesiva de rodilla o rango insuficiente detectado."
            )
            
        nombre_pac_limpio = "invitado"
        if self.paciente_id is not None:
            nombre_pac = obtener_nombre_paciente(self.paciente_id)
            nombre_pac_limpio = "".join([c for c in nombre_pac if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
            
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"informe_peso_muerto_{fecha_actual}.txt"
        
        # Crear carpeta estructurada si no existe
        carpeta_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_informes = os.path.join(carpeta_base, "informes", nombre_pac_limpio, fecha_dia, "peso_muerto")
        if not os.path.exists(carpeta_informes):
            os.makedirs(carpeta_informes)
        ruta_informe = os.path.join(carpeta_informes, nombre_archivo)
        
        reps_correctas = self.stats_repeticiones_totales - self.stats_repeticiones_con_error
        
        lineas_informe = []
        lineas_informe.append("=" * 50)
        lineas_informe.append(f"📋 INFORME CLÍNICO: PESO MUERTO (Nivel: {self.nivel.capitalize()})")
        lineas_informe.append(f"Fecha del análisis: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lineas_informe.append("=" * 50)
        
        lineas_informe.append("\n📊 DATOS CUANTITATIVOS:")
        lineas_informe.append(f" - Repeticiones totales: {self.stats_repeticiones_totales}")
        lineas_informe.append(f" - Repeticiones válidas completadas: {reps_correctas}")
        lineas_informe.append(f" - Repeticiones con error (flexión de rodillas/rango): {self.stats_repeticiones_con_error}")
        
        if self.stats_registro_profundidades:
            prof_media = sum(self.stats_registro_profundidades) / len(self.stats_registro_profundidades)
            lineas_informe.append(f" - Ángulo de cadera máximo medio: {prof_media:.1f} grados (Objetivo: < {self.umbrales['profundidad_maxima']} grados)")
        
        texto_final = "\n".join(lineas_informe)
        
        try:
            with open(ruta_informe, "w", encoding="utf-8") as archivo:
                archivo.write(texto_final)
            print(f"\n[SISTEMA] ✅ El informe se ha exportado correctamente a: {ruta_informe}")
        except IOError as e:
            print(f"\n[SISTEMA] ❌ Error al guardar el informe: {e}")