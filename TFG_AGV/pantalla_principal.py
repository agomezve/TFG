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

        frame_login = ctk.CTkFrame(self, width=400, height=500)
        frame_login.place(relx=0.5, rely=0.5, anchor=ctk.CENTER)

        lbl_titulo = ctk.CTkLabel(frame_login, text="Bienvenido a la Plataforma", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(40, 20))

        lbl_selec = ctk.CTkLabel(frame_login, text="Seleccionar paciente existente:", font=ctk.CTkFont(size=14))
        lbl_selec.pack(pady=(10, 5))

        self.pacientes = obtener_pacientes() # Lista de (id, nombre, edad)
        nombres = [p[1] for p in self.pacientes] if self.pacientes else ["(No hay pacientes)"]
        
        self.combo_pacientes = ctk.CTkComboBox(frame_login, values=nombres, width=250)
        self.combo_pacientes.pack(pady=10)

        btn_login = ctk.CTkButton(frame_login, text="Iniciar Sesión", command=self.login_paciente, width=250)
        btn_login.pack(pady=10)

        lbl_o = ctk.CTkLabel(frame_login, text="— O —", text_color="gray")
        lbl_o.pack(pady=10)

        self.entry_nuevo = ctk.CTkEntry(frame_login, placeholder_text="Nombre del nuevo paciente", width=250)
        self.entry_nuevo.pack(pady=10)

        btn_registro = ctk.CTkButton(frame_login, text="Registrar y Acceder", fg_color="green", hover_color="darkgreen", command=self.registrar_paciente, width=250)
        btn_registro.pack(pady=(10, 40))

    def login_paciente(self):
        seleccion = self.combo_pacientes.get()
        if seleccion and seleccion != "(No hay pacientes)":
            for p in self.pacientes:
                if p[1] == seleccion:
                    self.paciente_activo_id = p[0]
                    self.paciente_activo_nombre = p[1]
                    break
            self.mostrar_principal()

    def registrar_paciente(self):
        nombre = self.entry_nuevo.get().strip()
        if nombre:
            pid = crear_paciente(nombre=nombre)
            self.paciente_activo_id = pid
            self.paciente_activo_nombre = nombre
            self.mostrar_principal()

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
        
        texto_pantalla = self.generar_resumen_estadisticas(historial_filtrado)
        
        frame_scroll = ctk.CTkScrollableFrame(self.main_panel, fg_color="white", corner_radius=10)
        frame_scroll.pack(fill="both", expand=True, pady=10)
        
        lbl_stats = ctk.CTkLabel(frame_scroll, text=texto_pantalla, font=ctk.CTkFont(size=18), text_color="black", justify="center")
        lbl_stats.pack(fill="both", expand=True, pady=20)

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
        # Crear la ventana tLoplevel
        popup = ctk.CTkToplevel(self)
        popup.title(f"Iniciar: {nombre_ejercicio}")
        popup.geometry("350x220")
        popup.attributes("-topmost", True)
        
        # Orientar la ventana siempre al centro
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

    def generar_resumen_estadisticas(self, historial):
        if not historial:
            return "Aún no hay datos registrados para mostrar."
            
        stats = {}
        for s in historial:
            fecha_completa = s[0]
            fecha_str = fecha_completa[:10]
            ejercicio = s[1]
            reps = int(s[3]) if s[3] else 0
            errs = int(s[4]) if s[4] else 0
            
            if ejercicio not in stats:
                stats[ejercicio] = {}
            if fecha_str not in stats[ejercicio]:
                stats[ejercicio][fecha_str] = []
                
            stats[ejercicio][fecha_str].insert(0, {"reps": reps, "errores": errs})
            
        texto_pantalla = "📊 RESUMEN CLÍNICO POR EJERCICIO\n" + ("─" * 45) + "\n\n"
        meses = {1:"enero", 2:"febrero", 3:"marzo", 4:"abril", 5:"mayo", 6:"junio", 
                 7:"julio", 8:"agosto", 9:"septiembre", 10:"octubre", 11:"noviembre", 12:"diciembre"}
        dias_sem = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes", 5:"Sábado", 6:"Domingo"}
        
        for ej, dias in sorted(stats.items()):
            texto_pantalla += f"🏋️ EJERCICIO: {ej.upper()}\n"
            for fecha, series_list in sorted(dias.items(), reverse=True):
                try:
                    dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
                    fecha_bonita = f"{dias_sem[dt.weekday()]} {dt.day} de {meses[dt.month]} {dt.year}"
                except:
                    fecha_bonita = fecha
                
                texto_pantalla += f"    📅 {fecha_bonita}\n"
                texto_pantalla += f"    {len(series_list)} Series\n"
                
                for i, serie in enumerate(series_list):
                    if ej.lower() == "plancha":
                        texto_pantalla += f"        {i+1}ºserie: {serie['reps']} segundos totales | {max(0, serie['reps']-serie['errores'])}s correctos | {serie['errores']}s con error.\n"
                    elif ej.lower() == "propiocepcion":
                        texto_pantalla += f"        {i+1}ºserie: {serie['reps']} segundos aguantados | {serie['errores']} puntos de inestabilidad detectados.\n"
                    elif ej.lower() == "deslizamiento pared":
                        texto_pantalla += f"        {i+1}ºserie: Ángulo máximo alcanzado: {serie['reps']}º\n"
                    else:
                        correctas = serie['reps'] - serie['errores']
                        texto_pantalla += f"        {i+1}ºserie: {serie['reps']} repeticiones totales | {correctas} correctas | {serie['errores']} con error.\n"
                texto_pantalla += "\n"
                               
        return texto_pantalla



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
