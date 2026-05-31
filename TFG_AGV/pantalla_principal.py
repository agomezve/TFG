import customtkinter as ctk
import tkinter.filedialog as filedialog
import cv2
import PIL.Image, PIL.ImageTk
import os
import time
import mediapipe as mp
import datetime
from database import obtener_pacientes, crear_paciente, obtener_historial_paciente
from modulos.modulo_sentadilla import ModuloSentadilla
from modulos.modulo_peso_muerto import ModuloPesoMuerto
from modulos.modulo_press_militar import ModuloPressMilitar
from modulos.modulo_plancha import ModuloPlancha
from modulos.modulo_propiocepcion import ModuloPropiocepcion
from modulos.modulo_hombro_lateral import ModuloHombroLateral
from modulos.modulo_deslizamiento import ModuloDeslizamiento
from modulos.modulo_hip_thrust import ModuloHipThrust
from modulos.modulo_zancadas import ModuloZancadas
from modulos.modulo_bulgaras import ModuloBulgaras

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def dibujar_landmarks_filtrados(frame, pose_landmarks, indices_relevantes, conexiones_relevantes, color=(245, 66, 230)):
    """Dibuja en el frame solo los landmarks y conexiones relevantes para el ejercicio."""
    h, w, _ = frame.shape
    for a, b in conexiones_relevantes:
        pt_a = pose_landmarks.landmark[a]
        pt_b = pose_landmarks.landmark[b]
        x_a, y_a = int(pt_a.x * w), int(pt_a.y * h)
        x_b, y_b = int(pt_b.x * w), int(pt_b.y * h)
        cv2.line(frame, (x_a, y_a), (x_b, y_b), color, 4)
    for idx in indices_relevantes:
        pt = pose_landmarks.landmark[idx]
        cx, cy = int(pt.x * w), int(pt.y * h)
        cv2.circle(frame, (cx, cy), 6, color, -1)
        cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1)

class AppRehabilitacion(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Plataforma de Telerehabilitación TFG")
        self.geometry("1100x700")

        self.paciente_activo_id = None
        self.paciente_activo_nombre = None
        
        self.cap = None
        self.ejercicio_activo = None
        self.procesando_video = False
        
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(static_image_mode=False, model_complexity=1, 
                                      min_detection_confidence=0.5, min_tracking_confidence=0.5)

        self.mostrar_login()

    def procesar_cierre(self):
        self.detener_video()
        self.pose.close()
        self.quit()

    def mostrar_login(self):
        # Limpiar
        for widget in self.winfo_children():
            widget.destroy()
            
        self.protocol("WM_DELETE_WINDOW", self.quit)

        frame_login = ctk.CTkFrame(self, width=400, height=400)
        frame_login.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

        lbl_titulo = ctk.CTkLabel(frame_login, text="Plataforma de Telerehabilitación", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(40, 20))

        lbl_usuario = ctk.CTkLabel(frame_login, text="Usuario:", font=ctk.CTkFont(size=14))
        lbl_usuario.pack(pady=(10, 5))

        self.entry_usuario = ctk.CTkEntry(frame_login, placeholder_text="Nombre de usuario", width=250)
        self.entry_usuario.pack(pady=5)

        lbl_password = ctk.CTkLabel(frame_login, text="Contraseña:", font=ctk.CTkFont(size=14))
        lbl_password.pack(pady=(10, 5))

        self.entry_password = ctk.CTkEntry(frame_login, placeholder_text="Contraseña", width=250, show="*")
        self.entry_password.pack(pady=5)
        
        self.lbl_error = ctk.CTkLabel(frame_login, text="", text_color="red")
        self.lbl_error.pack(pady=5)

        btn_login = ctk.CTkButton(frame_login, text="Iniciar Sesión", command=self.login_paciente, width=250)
        btn_login.pack(pady=(20, 40))
        
        self.pacientes = obtener_pacientes() # Lista de (id, nombre, edad)

    def login_paciente(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()
        
        if not usuario or not password:
            self.lbl_error.configure(text="Por favor, rellene todos los campos")
            return
            
        if password != "12345":
            self.lbl_error.configure(text="Contraseña incorrecta")
            return
            
        usuario_encontrado = False
        for p in self.pacientes:
            # Comparamos ignorando mayúsculas/minúsculas para mayor flexibilidad
            if p[1].lower() == usuario.lower():
                self.paciente_activo_id = p[0]
                self.paciente_activo_nombre = p[1]
                usuario_encontrado = True
                break
                
        if usuario_encontrado:
            self.mostrar_principal()
        else:
            self.lbl_error.configure(text="Usuario no registrado")

    def mostrar_principal(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        self.protocol("WM_DELETE_WINDOW", self.procesar_cierre)

        # Barra Superior (Header) persistente
        self.header_frame = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(10, 0))

        btn_logout = ctk.CTkButton(self.header_frame, text="Cerrar Sesión", fg_color="red", hover_color="darkred",
                                   text_color="white", command=self.mostrar_login, width=120)
        btn_logout.pack(side="right", padx=(20, 0))

        lbl_paciente = ctk.CTkLabel(self.header_frame, text=f"👤 {self.paciente_activo_nombre}", 
                                    font=ctk.CTkFont(size=18, weight="bold"), text_color="#00FFAA")
        lbl_paciente.pack(side="right", padx=0)

        # Panel Principal (Dashboard / Vídeo)
        self.main_panel = ctk.CTkFrame(self)
        self.main_panel.pack(side="top", fill="both", expand=True, padx=20, pady=(10, 20))
        
        self.mostrar_dashboard()

    def mostrar_dashboard(self):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        lbl_titulo = ctk.CTkLabel(self.main_panel, text="Lista de ejercicios de rehabilitación", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=30)
        
        frame_cards = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        frame_cards.pack(fill="both", expand=True, padx=20)
        
        ejercicios = [
            "Sentadilla",
            "Peso Muerto",
            "Press Militar",
            "Plancha",
            "Propiocepcion",
            "Hombros Laterales",
            "Deslizamiento Pared",
            "Hip Thrust",
            "Zancadas",
            "Bulgaras"
        ]
        
        for i, nombre in enumerate(ejercicios):
            card = ctk.CTkFrame(frame_cards, corner_radius=10)
            card.pack(pady=10, fill="x", padx=20)
            
            lbl_ej = ctk.CTkLabel(card, text=nombre, font=ctk.CTkFont(size=20, weight="bold"))
            lbl_ej.grid(row=0, column=0, padx=20, pady=25, sticky="w")
            
            btn_video = ctk.CTkButton(card, text="🎬 Vídeo Explicativo", fg_color="#F2A900", hover_color="#C78A00", text_color="black", command=lambda n=nombre: self.mostrar_video_explicativo(n))
            btn_video.grid(row=0, column=1, rowspan=2, padx=10, pady=15)
            
            btn_iniciar = ctk.CTkButton(card, text="▶️ Iniciar", fg_color="green", hover_color="darkgreen", command=lambda n=nombre: self.mostrar_popup_iniciar(n))
            btn_iniciar.grid(row=0, column=2, rowspan=2, padx=10, pady=15)
            
            btn_stats = ctk.CTkButton(card, text="📊 Estadísticas", command=lambda n=nombre: self.mostrar_estadisticas_ejercicio(n))
            btn_stats.grid(row=0, column=3, rowspan=2, padx=10, pady=15)
            
            card.grid_columnconfigure(0, weight=1)

    def mostrar_estadisticas_ejercicio(self, nombre_ejercicio):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Volver", command=self.mostrar_dashboard, fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)
        
        historial = obtener_historial_paciente(self.paciente_activo_id)
        historial_filtrado = [s for s in historial if s[1].lower() == nombre_ejercicio.lower()]
        
        frame_scroll = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent", corner_radius=10)
        frame_scroll.pack(fill="both", expand=True, pady=10)
        
        if not historial_filtrado:
            lbl_vacio = ctk.CTkLabel(frame_scroll, text="Aún no hay datos registrados para mostrar.", font=ctk.CTkFont(size=18))
            lbl_vacio.pack(pady=40)
            return

        lbl_titulo = ctk.CTkLabel(frame_scroll, text=f"📊 RESUMEN CLÍNICO: {nombre_ejercicio.upper()}", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_titulo.pack(pady=(0, 20))

        # Agrupar por fecha
        stats_por_fecha = {}
        for s in historial_filtrado:
            fecha_completa = s[0]
            fecha_str = fecha_completa[:10]
            reps = int(s[3]) if s[3] else 0
            errs = int(s[4]) if s[4] else 0
            
            if fecha_str not in stats_por_fecha:
                stats_por_fecha[fecha_str] = []
            stats_por_fecha[fecha_str].insert(0, {"reps": reps, "errores": errs})
            
        meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
                 
        for fecha, series_list in sorted(stats_por_fecha.items(), reverse=True):
            try:
                dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
                dia = str(dt.day)
                mes_año = f"{meses[dt.month]} {dt.year}"
            except:
                dia = "XX"
                mes_año = fecha
                
            # Contenedor principal de la tarjeta del día
            card = ctk.CTkFrame(frame_scroll, corner_radius=15, fg_color="#2B2B2B")
            card.pack(fill="x", pady=10, padx=20)
            
            # Contenedor izquierdo: Calendario
            frame_cal = ctk.CTkFrame(card, fg_color="transparent", width=80)
            frame_cal.pack(side="left", padx=20, pady=15, fill="y")
            
            lbl_icono = ctk.CTkLabel(frame_cal, text="🗓️", font=ctk.CTkFont(size=35))
            lbl_icono.pack()
            
            lbl_dia = ctk.CTkLabel(frame_cal, text=dia, font=ctk.CTkFont(size=24, weight="bold"))
            lbl_dia.pack()
            
            lbl_mes = ctk.CTkLabel(frame_cal, text=mes_año, font=ctk.CTkFont(size=14))
            lbl_mes.pack()
            
            # Separador vertical
            separador = ctk.CTkFrame(card, width=2, fg_color="#444444")
            separador.pack(side="left", fill="y", pady=15, padx=10)
            
            # Contenedor derecho: Estadísticas
            frame_stats = ctk.CTkFrame(card, fg_color="transparent")
            frame_stats.pack(side="left", fill="both", expand=True, padx=20, pady=15)
            
            lbl_series = ctk.CTkLabel(frame_stats, text=f"Total: {len(series_list)} Series completadas", font=ctk.CTkFont(size=16, weight="bold"))
            lbl_series.pack(anchor="w", pady=(0, 10))
            
            for i, serie in enumerate(series_list):
                if nombre_ejercicio.lower() == "plancha":
                    texto_serie = f"Serie {i+1}: {serie['reps']}s totales | {max(0, serie['reps']-serie['errores'])}s correctos | {serie['errores']}s error"
                elif nombre_ejercicio.lower() == "propiocepcion":
                    texto_serie = f"Serie {i+1}: {serie['reps']}s aguantados | {serie['errores']} inestabilidades"
                elif nombre_ejercicio.lower() == "deslizamiento pared":
                    texto_serie = f"Serie {i+1}: Ángulo máximo {serie['reps']}º"
                else:
                    correctas = serie['reps'] - serie['errores']
                    texto_serie = f"Serie {i+1}: {serie['reps']} reps | {correctas} correctas | {serie['errores']} fallidas"
                
                color_texto = "white" if serie['errores'] == 0 else "#FF8A8A"
                lbl_s = ctk.CTkLabel(frame_stats, text=texto_serie, font=ctk.CTkFont(size=15), text_color=color_texto)
                lbl_s.pack(anchor="w", pady=2)



    def mostrar_video_explicativo(self, nombre_ejercicio, mensaje_error=None):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Volver ", command=self.mostrar_dashboard, fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)
        
        if mensaje_error:
            lbl_error = ctk.CTkLabel(self.main_panel, text=mensaje_error, font=ctk.CTkFont(size=22, weight="bold"), text_color="red")
            lbl_error.pack(pady=(30, 10))
        
        lbl_titulo = ctk.CTkLabel(self.main_panel, text=f"Vídeo Explicativo: {nombre_ejercicio}", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=40 if not mensaje_error else 10)

    def mostrar_popup_iniciar(self, nombre_ejercicio):
        popup = ctk.CTkToplevel(self)
        popup.title(f"Iniciar: {nombre_ejercicio}")
        popup.geometry("350x220")
        popup.attributes("-topmost", True)
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (350 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (220 // 2)
        popup.geometry(f"+{x}+{y}")

        lbl_tit = ctk.CTkLabel(popup, text=nombre_ejercicio.upper(), font=ctk.CTkFont(size=20, weight="bold"))
        lbl_tit.pack(pady=(20, 10))

        lbl_niv = ctk.CTkLabel(popup, text="Selecciona tu nivel de dificultad:")
        lbl_niv.pack(pady=10)
        
        var_nivel = ctk.StringVar(value="Principiante")
        
        frame_radio = ctk.CTkFrame(popup, fg_color="transparent")
        frame_radio.pack(pady=10)
        
        r1 = ctk.CTkRadioButton(frame_radio, text="Principiante", variable=var_nivel, value="Principiante")
        r1.pack(side="left", padx=10)
        r2 = ctk.CTkRadioButton(frame_radio, text="Avanzado", variable=var_nivel, value="Avanzado")
        r2.pack(side="left", padx=10)

        btn_web = ctk.CTkButton(popup, text="▶ INICIAR ENTRENAMIENTO", fg_color="green", hover_color="darkgreen", text_color="white", command=lambda: self._trigger_inicio(popup, nombre_ejercicio, var_nivel.get()))
        btn_web.pack(pady=15)

    def _trigger_inicio(self, popup, ejercicio, nivel):
        popup.destroy()
        self.iniciar_webcam(ejercicio, nivel.lower())

    def preparar_vista_video(self, texto_pantalla=""):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
        self.canvas_video = ctk.CTkLabel(self.main_panel, text=texto_pantalla, 
                                         font=ctk.CTkFont(size=22), text_color="black", fg_color="white", justify="center")
        self.canvas_video.pack(side="top", fill="both", expand=True)
        
        self.btn_stop = ctk.CTkButton(self.main_panel, text="⏹ Finalizar", fg_color="red", hover_color="darkred", 
                                      command=self.detener_video, state="disabled")

    def iniciar_motor_ejercicio(self, ejercicio, nivel):

        if ejercicio == "Sentadilla":
            self.ejercicio_activo = ModuloSentadilla(nivel=nivel)
        elif ejercicio == "Peso Muerto":
            self.ejercicio_activo = ModuloPesoMuerto(nivel=nivel)
        elif ejercicio == "Press Militar":
            self.ejercicio_activo = ModuloPressMilitar(nivel=nivel)
        elif ejercicio == "Plancha":
            self.ejercicio_activo = ModuloPlancha(nivel=nivel)
        elif ejercicio == "Propiocepcion":
            self.ejercicio_activo = ModuloPropiocepcion(nivel=nivel)
        elif ejercicio == "Hombros Laterales":
            self.ejercicio_activo = ModuloHombroLateral(nivel=nivel)
        elif ejercicio == "Deslizamiento Pared":
            self.ejercicio_activo = ModuloDeslizamiento(nivel=nivel)
        elif ejercicio == "Hip Thrust":
            self.ejercicio_activo = ModuloHipThrust(nivel=nivel)
        elif ejercicio == "Zancadas":
            self.ejercicio_activo = ModuloZancadas(nivel=nivel)
        elif ejercicio == "Bulgaras":
            self.ejercicio_activo = ModuloBulgaras(nivel=nivel)
            
        self.ejercicio_activo.set_paciente(self.paciente_activo_id)

    def iniciar_webcam(self, ejercicio, nivel):
        if self.procesando_video:
            self.detener_video()
        self.iniciar_motor_ejercicio(ejercicio, nivel)
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.preparar_vista_video("❌ Error: No se puede acceder a la webcam.")
            return
        self.procesando_video = True
        self.hora_inicio_analisis = time.time()
        self.tiempo_preparacion_fin = time.time() + 5.0
        
        self.preparar_vista_video("")
        self.btn_stop.configure(state="normal")
        self.btn_stop.place(relx=0.98, rely=0.05, anchor="ne")
        self.actualizar_frame()

    def iniciar_video(self, ejercicio, nivel):
        if self.procesando_video:
            self.detener_video()
        
        ruta = filedialog.askopenfilename(title="Seleccionar vídeo", filetypes=[("Archivos MP4", "*.mp4"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
            
        self.iniciar_motor_ejercicio(ejercicio, nivel)
        self.cap = cv2.VideoCapture(ruta)
        self.procesando_video = True
        self.hora_inicio_analisis = time.time()
        self.tiempo_preparacion_fin = time.time() + 5.0
        
        self.preparar_vista_video("")
        self.btn_stop.configure(state="normal")
        self.btn_stop.place(relx=0.98, rely=0.05, anchor="ne")
        self.actualizar_frame()

    def detener_video(self):
        self.procesando_video = False
        if self.cap:
            self.cap.release()
            self.cap = None
            
        if self.ejercicio_activo is not None:
            # Generar el informe y guardar en BBDD ANTES de obtener_historial_paciente
            self.ejercicio_activo.generar_informe_clinico()
            self.ejercicio_activo = None
                
        # Volver al Dashboard al detener el vídeo
        self.mostrar_dashboard()

    def actualizar_frame(self):
        # Prevenir errores al cerrar pestaña o si el canvas_video fue destruido
        if not self.winfo_exists() or not self.main_panel.winfo_exists() or not hasattr(self, 'canvas_video'):
            return
        if not self.procesando_video or self.cap is None:
            return

        exito, frame = self.cap.read()
        if not exito:
            self.detener_video() # Fin del video
            return

        # Procesamiento Mediapipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        resultados = self.pose.process(frame_rgb)
        frame_rgb.flags.writeable = True
        
        if resultados.pose_landmarks and resultados.pose_world_landmarks and self.ejercicio_activo:
            # Dibujar landmarks filtrados
            indices = self.ejercicio_activo.obtener_landmarks_relevantes()
            conexiones = self.ejercicio_activo.obtener_conexiones_relevantes()
            # Color condicional Tricolor: Azul(neutro), Verde(correcto), Rojo(error)
            estado = getattr(self.ejercicio_activo, 'estado_esqueleto', 'neutro')
            if estado == "error":
                color_esqueleto = (255, 0, 0) # RGB para Rojo
            elif estado == "correcto":
                color_esqueleto = (0, 255, 0) # RGB para Verde
            else:
                color_esqueleto = (0, 0, 255) # RGB para Azul
            
            dibujar_landmarks_filtrados(frame_rgb, resultados.pose_landmarks, indices, conexiones, color=color_esqueleto)
            
            tiempo_actual = time.time()
            if tiempo_actual < getattr(self, 'tiempo_preparacion_fin', 0):
                segundos_restantes = int(getattr(self, 'tiempo_preparacion_fin', 0) - tiempo_actual) + 1
                h, w, _ = frame_rgb.shape
                # Texto grande centrado
                texto_prep = f"PREPARACION: {segundos_restantes}"
                (tw, th), _ = cv2.getTextSize(texto_prep, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
                cv2.putText(frame_rgb, texto_prep, (int((w-tw)/2), int(h/2)), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 165, 0), 3, cv2.LINE_AA)
            else:
                # Evaluar y dibujar progreso sobre rgb
                self.ejercicio_activo.evaluar_postura(
                    resultados.pose_world_landmarks.landmark, 
                    resultados.pose_landmarks.landmark, 
                    frame_rgb
                )
                
                # Cortafuegos de seguridad: Auto-finalizar a los 3 errores
                errores = getattr(self.ejercicio_activo, 'get_errores_acumulados', lambda: 0)()
                if errores >= 3:
                    nombre = self.ejercicio_activo.__class__.__name__.replace("Modulo", "")
                    self.detener_video()
                    self.mostrar_video_explicativo(
                        nombre, 
                        mensaje_error="Vuelve a ver el vídeo explicativo para mejorar la técnica en el ejercicio."
                    )
                    return


        # Redimensionar y convertir a CTkImage para evitar errores de pyimage en CustomTkinter
        w_main = self.main_panel.winfo_width()
        h_main = self.main_panel.winfo_height()
        
        # Prevenir tamaños no válidos causados por inicialización de la ventana
        if w_main < 50 or h_main < 50:
            w_main, h_main = 640, 480
            
        img = PIL.Image.fromarray(frame_rgb)
        ctk_img = ctk.CTkImage(light_image=img, size=(w_main, h_main))
        
        self.canvas_video.configure(image=ctk_img, text="", fg_color="transparent")

        # Llamar a actualizar_frame después de 15ms
        self.after(15, self.actualizar_frame)

if __name__ == "__main__":
    app = AppRehabilitacion()
    app.mainloop()
