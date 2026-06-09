import customtkinter as ctk
import tkinter.filedialog as filedialog
import cv2
import PIL.Image, PIL.ImageTk
import os
import time
import mediapipe as mp
import datetime
import subprocess
from database import obtener_pacientes, crear_paciente, obtener_historial_paciente
from modulos.modulo_sentadilla import ModuloSentadilla
from modulos.modulo_peso_muerto import ModuloPesoMuerto
from modulos.modulo_press_militar import ModuloPressMilitar
from modulos.modulo_plancha import ModuloPlancha
from modulos.modulo_propiocepcion import ModuloPropiocepcion
from modulos.modulo_hombro_lateral import ModuloHombroLateral
from modulos.modulo_press_banca import ModuloPressBanca
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
            
        if usuario.lower() == "fisio" and password == "12345":
            self.mostrar_dashboard_fisio()
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
            "Press Banca",
            "Plancha",
            "Propiocepcion",
            "Hombros Laterales",
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
            nivel = s[2] if s[2] else "Desconocido"
            reps = int(s[3]) if s[3] else 0
            errs = int(s[4]) if s[4] else 0
            
            if fecha_str not in stats_por_fecha:
                stats_por_fecha[fecha_str] = []
            stats_por_fecha[fecha_str].insert(0, {"reps": reps, "errores": errs, "nivel": nivel})
            
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
                nombre_lower = nombre_ejercicio.lower()
                niv_str = serie.get('nivel', 'Desconocido').capitalize()
                
                if nombre_lower == "plancha":
                    texto_serie = f"Serie {i+1} ({niv_str}): {serie['reps']}s totales | {max(0, serie['reps']-serie['errores'])}s correctos | {serie['errores']}s error"
                elif nombre_lower == "propiocepcion":
                    texto_serie = f"Serie {i+1} ({niv_str}): {serie['reps']}s aguantados | {serie['errores']} inestabilidades"
                else:
                    correctas = serie['reps'] - serie['errores']
                    texto_serie = f"Serie {i+1} ({niv_str}): {serie['reps']} reps | {correctas} correctas | {serie['errores']} fallidas"
                
                color_texto = "white" if serie['errores'] == 0 else "#FF8A8A"
                lbl_s = ctk.CTkLabel(frame_stats, text=texto_serie, font=ctk.CTkFont(size=15), text_color=color_texto)
                lbl_s.pack(anchor="w", pady=2)



    # Mapeo ejercicio -> archivo de vídeo explicativo (MP4 con audio)
    VIDEOS_EXPLICATIVOS = {
        "Press Militar":     "v_e_press_militar.mp4",
        "Peso Muerto":       "v_e_peso_muerto.mp4",
        "Zancadas":          "v_e_zancadas.mp4",
        "Hombros Laterales": "v_e_elevaciones_laterales.mp4",
    }

    def mostrar_video_explicativo(self, nombre_ejercicio, mensaje_error=None):
        for widget in self.main_panel.winfo_children():
            widget.destroy()

        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Volver ", command=self.mostrar_dashboard, fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)

        if mensaje_error:
            lbl_error = ctk.CTkLabel(self.main_panel, text=mensaje_error, font=ctk.CTkFont(size=22, weight="bold"), text_color="red")
            lbl_error.pack(pady=(30, 10))

        lbl_titulo = ctk.CTkLabel(self.main_panel, text=f"Vídeo Explicativo: {nombre_ejercicio}", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=30 if not mensaje_error else 10)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        nombre_archivo = self.VIDEOS_EXPLICATIVOS.get(nombre_ejercicio)
        ruta_video = os.path.join(base_dir, "videos_explicativos", nombre_archivo) if nombre_archivo else None

        if ruta_video and os.path.exists(ruta_video):
            # --- Miniatura del vídeo (centrada y sin deformar) ---
            try:
                cap_thumb = cv2.VideoCapture(ruta_video)
                exito, frame = cap_thumb.read()
                cap_thumb.release()
                if exito:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_thumb = PIL.Image.fromarray(frame_rgb)
                    
                    # El espacio reservado en la UI es 600x337
                    target_w, target_h = 600, 337
                    
                    # Redimensionar manteniendo la proporción original
                    img_thumb.thumbnail((target_w, target_h), PIL.Image.Resampling.LANCZOS)
                    
                    # Crear fondo oscuro que llene el espacio
                    background = PIL.Image.new("RGB", (target_w, target_h), (43, 43, 43))
                    
                    # Pegar el frame en el centro
                    offset_x = (target_w - img_thumb.width) // 2
                    offset_y = (target_h - img_thumb.height) // 2
                    background.paste(img_thumb, (offset_x, offset_y))
                    
                    ctk_thumb = ctk.CTkImage(light_image=background, dark_image=background, size=(target_w, target_h))
                    lbl_thumb = ctk.CTkLabel(self.main_panel, image=ctk_thumb, text="")
                    lbl_thumb.pack(pady=(0, 10))
                else:
                    ruta_img = os.path.join(base_dir, "video_placeholder.png")
                    if os.path.exists(ruta_img):
                        img = PIL.Image.open(ruta_img)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 337))
                        lbl_img = ctk.CTkLabel(self.main_panel, image=ctk_img, text="")
                        lbl_img.pack(pady=(0, 10))
            except Exception as e:
                print(f"Error generando miniatura: {e}")

            # --- Info de duración ---
            try:
                cap_info = cv2.VideoCapture(ruta_video)
                fps_v = cap_info.get(cv2.CAP_PROP_FPS) or 30
                frames_v = cap_info.get(cv2.CAP_PROP_FRAME_COUNT)
                cap_info.release()
                dur_seg = int(frames_v / fps_v)
                lbl_dur = ctk.CTkLabel(self.main_panel, text=f"🎬 Vídeo explicativo",
                                       font=ctk.CTkFont(size=14), text_color="#AAAAAA")
                lbl_dur.pack(pady=(0, 10))
            except Exception:
                pass

            # --- Botón de reproducción ---
            def abrir_video(ruta=ruta_video):
                subprocess.Popen(["open", ruta])

            btn_play = ctk.CTkButton(
                self.main_panel,
                text="▶  Reproducir Vídeo Explicativo",
                font=ctk.CTkFont(size=18, weight="bold"),
                fg_color="#F2A900", hover_color="#C78A00",
                text_color="black", height=50, width=320,
                command=abrir_video
            )
            btn_play.pack(pady=10)


        else:
            # Sin vídeo disponible → placeholder
            try:
                ruta_img = os.path.join(base_dir, "video_placeholder.png")
                if os.path.exists(ruta_img):
                    img = PIL.Image.open(ruta_img)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 337))
                    lbl_img = ctk.CTkLabel(self.main_panel, image=ctk_img, text="")
                    lbl_img.pack(pady=20)
                else:
                    lbl_placeholder = ctk.CTkLabel(self.main_panel, text="[VÍDEO EXPLICATIVO PRÓXIMAMENTE]",
                                                   font=ctk.CTkFont(size=18), width=600, height=337,
                                                   fg_color="#2B2B2B", corner_radius=10)
                    lbl_placeholder.pack(pady=20)
            except Exception as e:
                print(f"Error cargando placeholder: {e}")

    def mostrar_popup_iniciar(self, nombre_ejercicio):
        popup = ctk.CTkToplevel(self)
        popup.title(f"Iniciar: {nombre_ejercicio}")
        popup.geometry("350x330")
        popup.attributes("-topmost", True)
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (350 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (330 // 2)
        popup.geometry(f"+{x}+{y}")

        lbl_tit = ctk.CTkLabel(popup, text=nombre_ejercicio.upper(), font=ctk.CTkFont(size=20, weight="bold"))
        lbl_tit.pack(pady=(20, 10))

        lbl_niv = ctk.CTkLabel(popup, text="Selecciona tu nivel de dificultad:")
        lbl_niv.pack(pady=10)
        
        var_nivel = ctk.StringVar(value="Principiante")
        
        frame_radio = ctk.CTkFrame(popup, fg_color="transparent")
        frame_radio.pack(pady=10)
        
        r1 = ctk.CTkRadioButton(frame_radio, text="Principiante", variable=var_nivel, value="Principiante")
        r1.pack(side="left", padx=8)
        r2 = ctk.CTkRadioButton(frame_radio, text="Intermedio", variable=var_nivel, value="Intermedio")
        r2.pack(side="left", padx=8)
        r3 = ctk.CTkRadioButton(frame_radio, text="Avanzado", variable=var_nivel, value="Avanzado")
        r3.pack(side="left", padx=8)

        camara_var = ctk.StringVar(value="📸 Cámara Principal (0)")
        opciones_camara = ["📸 Cámara Principal (0)", "📱 iPhone / Secundaria (1)"]
        combo_camara = ctk.CTkOptionMenu(popup, values=opciones_camara, variable=camara_var, width=220)
        combo_camara.pack(pady=10)

        def proceed():
            idx = 1 if "1" in camara_var.get() else 0
            self._trigger_inicio(popup, nombre_ejercicio, var_nivel.get(), idx)

        btn_web = ctk.CTkButton(popup, text="▶ INICIAR ENTRENAMIENTO", fg_color="green", hover_color="darkgreen", text_color="white", command=proceed)
        btn_web.pack(pady=15)

    # ── Consejos por ejercicio ─────────────────────────────────────────────────
    CONSEJOS_EJERCICIO = {
        "Sentadilla": [
            "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
            "📏 Sépate al menos 2 m para que se vea el cuerpo entero.",
            "🦵 Asegúrate de que ambas piernas son visibles en todo momento.",
            "🔦 Buena iluminación frontal, sin sombras en las piernas.",
            "👕 Ropa que contraste con el fondo.",
        ],
        "Peso Muerto": [
            "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
            "📏 Sépate al menos 2 m para que se vean pies, rodillas, caderas y hombros.",
            "🎯 Oriéntate perpendicular a la cámara (perfil puro, no en diagonal).",
            "🔦 Iluminación lateral para que el contorno del cuerpo sea nítido.",
            "🦴 Evita ropa muy holgada que oculte la posición de la cadera.",
        ],
        "Press Militar": [
            "📐 Cámara DE FRENTE (frontal), a la altura de tu pecho.",
            "📏 Sépate al menos 1.5 m para ver los brazos completamente extendidos.",
            "💪 Asegúrate de que codos y muñecas son visibles en todo el recorrido.",
            "🔦 Iluminación uniforme sin sombras sobre los brazos.",
            "🧍 Manténte centrado en el encuadre durante todo el ejercicio.",
        ],
        "Press Banca": [
            "📐 Cámara de LADO (lateral), a la altura del banco o del suelo.",
            "📏 Sépate al menos 2 m para ver todo tu cuerpo horizontal.",
            "🛏️ Asegúrate de que la cámara captura desde la cabeza hasta los pies.",
            "💪 Los codos y muñecas deben ser visibles en todo el recorrido.",
            "🔦 Buena iluminación para distinguir brazos y torso del fondo.",
        ],
        "Plancha": [
            "📐 Cámara de LADO (lateral), cerca del suelo o a poca altura.",
            "📏 Sépate al menos 2 m para ver hombros, cadera y tobillos.",
            "🎯 Oriéntate perpendicular a la cámara (perfil puro).",
            "🔦 Iluminación lateral para ver bien la línea del cuerpo.",
            "🧘 Quédate quieto en el mismo sitio durante todo el ejercicio.",
        ],
        "Propiocepcion": [
            "📐 Cámara DE FRENTE (frontal), a la altura de tu pecho.",
            "📏 Sépate al menos 2 m para ver el cuerpo entero de cabeza a pies.",
            "🦵 Fondo despejado y sin movimiento para mejorar la detección.",
            "👟 Empieza con los dos pies en el suelo y levanta uno al iniciar.",
            "🔦 Iluminación uniforme sin sombras en el suelo.",
        ],
        "Hombros Laterales": [
            "📐 Cámara DE FRENTE (frontal), a la altura de tu cintura.",
            "📏 Sépate al menos 1.5 m para ver ambos brazos elevados.",
            "💪 Asegúrate de que codos y muñecas son visibles al elevar.",
            "🔦 Iluminación frontal sin sombras sobre los brazos.",
            "🧍 Manténte centrado en el encuadre durante todo el ejercicio.",
        ],
        "Hip Thrust": [
            "📐 Cámara de LADO (lateral), a la altura del banco o suelo.",
            "📏 Sépate al menos 2 m para ver hombros, cadera y rodillas.",
            "🎯 Oriéntate perpendicular a la cámara (perfil puro, no en diagonal).",
            "🔦 Iluminación lateral para detectar bien la extensión de cadera.",
        ],
        "Zancadas": [
            "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
            "📏 Sépate al menos 2.5 m para ver ambas piernas en la zancada.",
            "🦵 Realiza las zancadas en línea recta, no en diagonal.",
            "🔦 Iluminación lateral para ver bien ambas rodillas.",
            "👕 Evita ropa similar al fondo, especialmente en las piernas.",
        ],
        "Bulgaras": [
            "📐 Cámara de LADO (lateral), a la altura de tu cadera.",
            "📏 Sépate al menos 2.5 m para ver ambas piernas.",
            "🦵 El pie trasero elevado debe ser visible — no debe taparse.",
            "🎯 Oriéntate perpendicular a la cámara (perfil puro).",
            "🔦 Buena iluminación lateral para distinguir ambas piernas.",
        ],
    }

    def _trigger_inicio(self, popup, ejercicio, nivel, cam_index=0):
        popup.destroy()
        consejos = self.CONSEJOS_EJERCICIO.get(ejercicio, [])
        if not consejos:
            self.iniciar_webcam(ejercicio, nivel.lower(), cam_index)
            return
        self._mostrar_popup_consejos(ejercicio, nivel, consejos, cam_index)

    def _mostrar_popup_consejos(self, ejercicio, nivel, consejos, cam_index=0):
        w, h = 460, 400
        tips = ctk.CTkToplevel(self)
        tips.title(f"Consejos: {ejercicio}")
        tips.geometry(f"{w}x{h}")
        tips.attributes("-topmost", True)
        tips.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        tips.geometry(f"+{x}+{y}")

        ctk.CTkLabel(tips, text=f"⚠️  Antes de empezar", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#F39C12").pack(pady=(18, 4))
        ctk.CTkLabel(tips, text=f"{ejercicio.upper()} — Nivel {nivel}",
                     font=ctk.CTkFont(size=13)).pack(pady=(0, 10))

        frame_scroll = ctk.CTkScrollableFrame(tips, height=220)
        frame_scroll.pack(fill="both", expand=True, padx=18, pady=4)
        for consejo in consejos:
            ctk.CTkLabel(frame_scroll, text=consejo, wraplength=390,
                         justify="left", anchor="w",
                         font=ctk.CTkFont(size=13)).pack(anchor="w", pady=4)

        ctk.CTkButton(tips, text="✅  Entendido, ¡comenzar!", fg_color="#27AE60",
                      hover_color="#1E8449", text_color="white",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: [tips.destroy(), self.iniciar_webcam(ejercicio, nivel.lower(), cam_index)]
                      ).pack(pady=(15, 14))

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
        elif ejercicio == "Press Banca":
            self.ejercicio_activo = ModuloPressBanca(nivel=nivel)
        elif ejercicio == "Plancha":
            self.ejercicio_activo = ModuloPlancha(nivel=nivel)
        elif ejercicio == "Propiocepcion":
            self.ejercicio_activo = ModuloPropiocepcion(nivel=nivel)
        elif ejercicio == "Hombros Laterales":
            self.ejercicio_activo = ModuloHombroLateral(nivel=nivel)
        elif ejercicio == "Hip Thrust":
            self.ejercicio_activo = ModuloHipThrust(nivel=nivel)
        elif ejercicio == "Zancadas":
            self.ejercicio_activo = ModuloZancadas(nivel=nivel)
        elif ejercicio == "Bulgaras":
            self.ejercicio_activo = ModuloBulgaras(nivel=nivel)
            
        self.ejercicio_activo.set_paciente(self.paciente_activo_id)

    def iniciar_webcam(self, ejercicio, nivel, cam_index=0):
        if self.procesando_video:
            self.detener_video()
        self.iniciar_motor_ejercicio(ejercicio, nivel)
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            self.preparar_vista_video("❌ Error: No se puede acceder a la webcam.")
            return
        self.procesando_video = True
        self.hora_inicio_analisis = time.time()
        self.tiempo_preparacion_fin = time.time() + 5.0
        self._nombre_ejercicio_activo = ejercicio
        self.video_writer = None # Se inicializará con el primer frame
        
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
        self._nombre_ejercicio_activo = ejercicio
        
        self.preparar_vista_video("")
        self.btn_stop.configure(state="normal")
        self.btn_stop.place(relx=0.98, rely=0.05, anchor="ne")
        self.actualizar_frame()

    def detener_video(self):
        self.procesando_video = False
        if self.cap:
            self.cap.release()
            self.cap = None
            
        if hasattr(self, 'video_writer') and self.video_writer is not None:
            self.video_writer.release()
            
            # Renombrar con FPS real
            if hasattr(self, 'inicio_grabacion_vid') and hasattr(self, 'frames_grabados_vid') and hasattr(self, 'ruta_video_actual'):
                duracion = time.time() - self.inicio_grabacion_vid
                if duracion > 0 and self.frames_grabados_vid > 0:
                    fps_real = self.frames_grabados_vid / duracion
                    nuevo_nombre = self.ruta_video_actual.replace(".avi", f"_fps{fps_real:.2f}.avi")
                    try:
                        os.rename(self.ruta_video_actual, nuevo_nombre)
                    except: pass
                    
            self.video_writer = None
        if self.ejercicio_activo is not None:
            # Generar el informe y guardar en BBDD ANTES de obtener_historial_paciente
            self.ejercicio_activo.generar_informe_clinico()
            self.ejercicio_activo = None
                
        # Volver al Dashboard al detener el vídeo
        self.mostrar_dashboard()

    def _disparar_fin_serie(self, nombre_ejercicio):
        """Finaliza la sesión automáticamente al completar el objetivo y muestra mensaje de éxito."""
        self.procesando_video = False
        if self.cap:
            self.cap.release()
            self.cap = None

        if hasattr(self, 'video_writer') and self.video_writer is not None:
            self.video_writer.release()
            
            # Renombrar con FPS real
            if hasattr(self, 'inicio_grabacion_vid') and hasattr(self, 'frames_grabados_vid') and hasattr(self, 'ruta_video_actual'):
                duracion = time.time() - self.inicio_grabacion_vid
                if duracion > 0 and self.frames_grabados_vid > 0:
                    fps_real = self.frames_grabados_vid / duracion
                    nuevo_nombre = self.ruta_video_actual.replace(".avi", f"_fps{fps_real:.2f}.avi")
                    try:
                        os.rename(self.ruta_video_actual, nuevo_nombre)
                    except: pass
                    
            self.video_writer = None

        if self.ejercicio_activo is not None:
            self.ejercicio_activo.generar_informe_clinico()
            self.ejercicio_activo = None

        # Mostrar pantalla de éxito brevemente antes de volver al dashboard
        for widget in self.main_panel.winfo_children():
            widget.destroy()
        lbl_ok = ctk.CTkLabel(self.main_panel,
                               text=f"✅ ¡Serie completada!\n{nombre_ejercicio}",
                               font=ctk.CTkFont(size=32, weight="bold"),
                               text_color="#00FFAA")
        lbl_ok.pack(expand=True)
        self.after(2500, self.mostrar_dashboard)

    def actualizar_frame(self):
        # Prevenir errores al cerrar pestaña o si el canvas_video fue destruido
        if not self.winfo_exists() or not self.main_panel.winfo_exists() or not hasattr(self, 'canvas_video'):
            return
        if not self.procesando_video or self.cap is None:
            return

        exito, frame = self.cap.read()
        if not exito:
            self.detener_video()  # Fin del video
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
                color_esqueleto = (255, 0, 0)   # RGB para Rojo
            elif estado == "correcto":
                color_esqueleto = (0, 255, 0)   # RGB para Verde
            else:
                color_esqueleto = (0, 0, 255)   # RGB para Azul
            
            dibujar_landmarks_filtrados(frame_rgb, resultados.pose_landmarks, indices, conexiones, color=color_esqueleto)
            
            tiempo_actual = time.time()
            if tiempo_actual < getattr(self, 'tiempo_preparacion_fin', 0):
                segundos_restantes = int(getattr(self, 'tiempo_preparacion_fin', 0) - tiempo_actual) + 1
                h, w, _ = frame_rgb.shape
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
                
                # --- CORTAFUEGOS DE SEGURIDAD ---
                # Condición 1: 3 errores totales acumulados
                errores_totales = getattr(self.ejercicio_activo, 'get_errores_acumulados', lambda: 0)()
                # Condición 2: 2 errores consecutivos
                errores_consec = getattr(self.ejercicio_activo, 'get_errores_consecutivos', lambda: 0)()

                if errores_totales >= 3 or errores_consec >= 2:
                    nombre = getattr(self, '_nombre_ejercicio_activo', '')
                    self.detener_video()
                    self.mostrar_video_explicativo(
                        nombre,
                        mensaje_error="Vuelve a ver el vídeo explicativo para mejorar la técnica en el ejercicio."
                    )
                    return

                # --- OBJETIVO COMPLETADO (10 reps o 30s) ---
                if self.ejercicio_activo.get_objetivo_completado():
                    nombre = getattr(self, '_nombre_ejercicio_activo', '')
                    self._disparar_fin_serie(nombre)
                    return

        # Redimensionar y convertir a CTkImage para evitar errores de pyimage en CustomTkinter
        w_main = self.main_panel.winfo_width()
        h_main = self.main_panel.winfo_height()
        
        # Prevenir tamaños no válidos causados por inicialización de la ventana
        if w_main < 50 or h_main < 50:
            w_main, h_main = 640, 480
            
        # Grabación de vídeo
        if getattr(self, 'procesando_video', False):
            if not hasattr(self, 'video_writer') or self.video_writer is None:
                h_vid, w_vid, _ = frame_rgb.shape
                nombre_pac_limpio = "".join([c for c in getattr(self, 'paciente_activo_nombre', 'paciente') if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
                import datetime
                fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                fecha_dia = datetime.datetime.now().strftime("%Y-%m-%d")
                import os
                carpeta_base = os.path.dirname(os.path.abspath(__file__))
                ej_limpio = getattr(self, '_nombre_ejercicio_activo', 'ejercicio').lower().replace(" ", "_")
                carpeta_videos = os.path.join(carpeta_base, "usuarios", nombre_pac_limpio, fecha_dia, ej_limpio, "videos")
                if not os.path.exists(carpeta_videos):
                    os.makedirs(carpeta_videos)
                ruta_video = os.path.join(carpeta_videos, f"video_{ej_limpio}_{fecha_actual}.avi")
                # MJPG es casi nativo en todas las plataformas
                fourcc = cv2.VideoWriter_fourcc(*'MJPG') 
                # 12.0 FPS es un buen promedio de la velocidad real de Mediapipe
                self.video_writer = cv2.VideoWriter(ruta_video, fourcc, 12.0, (int(w_vid), int(h_vid)))
                self.ruta_video_actual = ruta_video
                self.frames_grabados_vid = 0
                self.inicio_grabacion_vid = time.time()
                print(f"[SISTEMA] Iniciando grabación de vídeo en: {ruta_video} ({w_vid}x{h_vid})")
                if not self.video_writer.isOpened():
                    print("[SISTEMA] ❌ ERROR CRÍTICO: VideoWriter no pudo abrir el archivo. Revisa permisos o códecs.")
                
            if self.video_writer is not None and self.video_writer.isOpened():
                if frame_rgb.shape[2] == 4:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGBA2BGR)
                else:
                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                self.video_writer.write(frame_bgr)
                self.frames_grabados_vid += 1

        # Convertir a imagen de Tkinter manteniendo el tamaño del canvas
        img = PIL.Image.fromarray(frame_rgb)
        ctk_img = ctk.CTkImage(light_image=img, size=(w_main, h_main))
        
        self.canvas_video.configure(image=ctk_img, text="", fg_color="transparent")
        
        self.after(10, self.actualizar_frame)

    def mostrar_dashboard_fisio(self):
        for widget in self.winfo_children():
            widget.destroy()
            
        self.protocol("WM_DELETE_WINDOW", self.procesar_cierre)
        
        self.header_frame = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(10, 0))

        btn_logout = ctk.CTkButton(self.header_frame, text="Cerrar Sesión", fg_color="red", hover_color="darkred",
                                   text_color="white", command=self.mostrar_login, width=120)
        btn_logout.pack(side="right", padx=(20, 0))

        lbl_paciente = ctk.CTkLabel(self.header_frame, text="Panel de Fisioterapeuta", 
                                    font=ctk.CTkFont(size=20, weight="bold"), text_color="#00FFAA")
        lbl_paciente.pack(side="left", padx=0)
        
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        lbl_titulo = ctk.CTkLabel(self.main_panel, text="Seleccione un Paciente", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(0, 20))
        
        frame_grid = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        frame_grid.pack(fill="both", expand=True)
        
        for i, p in enumerate(self.pacientes):
            paciente_id, nombre, edad = p
            card = ctk.CTkFrame(frame_grid, width=200, height=150, corner_radius=15, fg_color="#2B2B2B")
            card.grid(row=i//4, column=i%4, padx=15, pady=15)
            card.pack_propagate(False)
            
            lbl_img = ctk.CTkLabel(card, text="👤", font=ctk.CTkFont(size=50))
            lbl_img.pack(pady=(10, 5))
            
            lbl_nom = ctk.CTkLabel(card, text=nombre, font=ctk.CTkFont(size=16, weight="bold"))
            lbl_nom.pack()
            
            btn_ver = ctk.CTkButton(card, text="Ver Entrenos", command=lambda pid=paciente_id, n=nombre: self.mostrar_calendario_paciente_fisio(pid, n))
            btn_ver.pack(pady=10)

    def mostrar_calendario_paciente_fisio(self, paciente_id, nombre):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Volver", command=self.mostrar_dashboard_fisio, fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)
        
        lbl_titulo = ctk.CTkLabel(self.main_panel, text=f"Entrenamientos de {nombre}", font=ctk.CTkFont(size=24, weight="bold"))
        lbl_titulo.pack(pady=(0, 20))
        
        historial = obtener_historial_paciente(paciente_id)
        
        if not historial:
            ctk.CTkLabel(self.main_panel, text="El paciente no tiene entrenamientos registrados.", font=ctk.CTkFont(size=16)).pack(pady=40)
            return
            
        dias_entreno = {}
        for s in historial:
            fecha_str = s[0][:10]
            if fecha_str not in dias_entreno:
                dias_entreno[fecha_str] = []
            dias_entreno[fecha_str].append(s)
            
        frame_scroll = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        frame_scroll.pack(fill="both", expand=True)
        
        for fecha in sorted(dias_entreno.keys(), reverse=True):
            card = ctk.CTkFrame(frame_scroll, corner_radius=10, fg_color="#2B2B2B")
            card.pack(fill="x", pady=5, padx=20)
            
            lbl_f = ctk.CTkLabel(card, text=f"📅 {fecha}", font=ctk.CTkFont(size=18, weight="bold"))
            lbl_f.pack(side="left", padx=20, pady=15)
            
            btn_ver = ctk.CTkButton(card, text="Ver Detalle del Día", command=lambda p=paciente_id, n=nombre, f=fecha, h=dias_entreno[fecha]: self.mostrar_ejercicios_dia_fisio(p, n, f, h))
            btn_ver.pack(side="right", padx=20, pady=15)

    def mostrar_ejercicios_dia_fisio(self, paciente_id, nombre, fecha, historial_dia):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Volver", command=lambda: self.mostrar_calendario_paciente_fisio(paciente_id, nombre), fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)
        
        lbl_titulo = ctk.CTkLabel(self.main_panel, text=f"Resumen del {fecha} - {nombre}", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_titulo.pack(pady=(0, 20))
        
        # Agrupar por ejercicio
        ejercicios = {}
        for s in historial_dia:
            ej = s[1]
            if ej not in ejercicios:
                ejercicios[ej] = []
            ejercicios[ej].insert(0, s) # Reverse insert to keep chronological if query is DESC
            
        frame_scroll = ctk.CTkScrollableFrame(self.main_panel, fg_color="transparent")
        frame_scroll.pack(fill="both", expand=True)
        
        for ej, series in ejercicios.items():
            card = ctk.CTkFrame(frame_scroll, corner_radius=10, fg_color="#333333")
            card.pack(fill="x", pady=10, padx=20)
            
            lbl_e = ctk.CTkLabel(card, text=f"{ej.upper()}", font=ctk.CTkFont(size=18, weight="bold"))
            lbl_e.pack(anchor="w", padx=20, pady=(10, 5))
            
            for i, serie in enumerate(series):
                frame_s = ctk.CTkFrame(card, fg_color="transparent")
                frame_s.pack(fill="x", padx=40, pady=2)
                
                niv_str = serie[2].capitalize() if serie[2] else "Desconocido"
                
                texto_s = f"Serie {i+1} ({niv_str}): {serie[3]} reps | {serie[4]} fallos"
                lbl_s = ctk.CTkLabel(frame_s, text=texto_s, font=ctk.CTkFont(size=15))
                lbl_s.pack(side="left")
                
                btn_ver = ctk.CTkButton(frame_s, text="Ver Informe y Vídeo", width=140, height=28, command=lambda e=ej, idx=i, p_id=paciente_id, p_nom=nombre, f=fecha, ts=serie[0]: self.mostrar_detalle_serie_fisio(p_id, p_nom, f, e, idx, ts))
                btn_ver.pack(side="right")

    def mostrar_detalle_serie_fisio(self, paciente_id, nombre, fecha, ejercicio, serie_idx, db_timestamp_str=None):
        for widget in self.main_panel.winfo_children():
            widget.destroy()
            
        # Buscar el informe y video en la carpeta
        nombre_pac_limpio = "".join([c for c in nombre if c.isalpha() or c.isdigit() or c==' ']).rstrip().replace(" ", "_").lower()
        carpeta_base = os.path.dirname(os.path.abspath(__file__))
        carpeta_ejercicio = os.path.join(carpeta_base, "usuarios", nombre_pac_limpio, fecha, ejercicio.lower().replace(" ", "_"))
        carpeta_txt = os.path.join(carpeta_ejercicio, "informes")
        carpeta_vid = os.path.join(carpeta_ejercicio, "videos")
        
        archivos_txt = []
        archivos_mp4 = []
        if os.path.exists(carpeta_txt):
            archivos_txt = sorted([f for f in os.listdir(carpeta_txt) if f.endswith(".txt")])
        if os.path.exists(carpeta_vid):
            archivos_mp4 = sorted([f for f in os.listdir(carpeta_vid) if f.endswith(".mp4") or f.endswith(".avi")])
            
        ruta_txt = None
        ruta_mp4 = None
        t_txt = None
        
        import datetime
        def extraer_dt(filename):
            try:
                name = filename.rsplit('.', 1)[0]
                if "_fps" in name:
                    name = name.split("_fps")[0]
                parts = name.split('_')
                d_str = parts[-2]
                t_str = parts[-1]
                return datetime.datetime.strptime(f"{d_str}_{t_str}", "%Y-%m-%d_%H-%M-%S")
            except:
                return datetime.datetime.min
                
        # 1. Intentar buscar el TXT por el timestamp de la BBDD (super preciso, a prueba de borrados)
        if db_timestamp_str:
            try:
                db_t = datetime.datetime.strptime(db_timestamp_str, "%Y-%m-%d %H:%M:%S")
                min_diff = 999999
                for txt in archivos_txt:
                    t = extraer_dt(txt)
                    diff = abs((db_t - t).total_seconds())
                    if diff < min_diff and diff <= 15: # Margen de 15 segundos entre BBDD y guardado de archivo
                        min_diff = diff
                        ruta_txt = os.path.join(carpeta_txt, txt)
                        t_txt = t
            except:
                pass
                
        # 2. Fallback: buscar por índice si no se encontró por fecha (legacy)
        if not ruta_txt and serie_idx < len(archivos_txt):
            ruta_txt = os.path.join(carpeta_txt, archivos_txt[serie_idx])
            t_txt = extraer_dt(archivos_txt[serie_idx])
            
        # 3. Si hay TXT, buscar su vídeo correspondiente
        if ruta_txt and t_txt:
            video_match = None
            for vid in archivos_mp4:
                t_vid = extraer_dt(vid)
                diff = (t_txt - t_vid).total_seconds()
                if 0 <= diff <= 1200: 
                    video_match = vid
                    
            if video_match:
                ruta_mp4 = os.path.join(carpeta_vid, video_match)
            
        btn_volver = ctk.CTkButton(self.main_panel, text="⬅ Cerrar Detalle", command=lambda: self.mostrar_calendario_paciente_fisio(paciente_id, nombre), fg_color="gray", hover_color="darkgray")
        btn_volver.pack(anchor="nw", pady=10)
        
        lbl_titulo = ctk.CTkLabel(self.main_panel, text=f"Detalle: {ejercicio.upper()} - Serie {serie_idx+1}", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_titulo.pack(pady=10)
        
        if ruta_mp4:
            btn_video = ctk.CTkButton(self.main_panel, text="▶ Reproducir Vídeo de la Serie", fg_color="#00FFAA", text_color="black", font=ctk.CTkFont(weight="bold"), command=lambda: self.reproducir_video_fisio(ruta_mp4))
            btn_video.pack(pady=10)
        else:
            ctk.CTkLabel(self.main_panel, text="No hay vídeo disponible para esta serie.", text_color="orange").pack(pady=10)
            
        texto_informe = "No se encontró el informe en texto para esta serie."
        if ruta_txt and os.path.exists(ruta_txt):
            with open(ruta_txt, "r", encoding="utf-8") as f:
                texto_informe = f.read()
                
        textbox = ctk.CTkTextbox(self.main_panel, width=700, height=400, font=ctk.CTkFont(family="Consolas", size=14))
        textbox.pack(pady=10)
        textbox.insert("1.0", texto_informe)
        textbox.configure(state="disabled")

    def reproducir_video_fisio(self, ruta_mp4):
        """Abre el vídeo de la serie en el reproductor del sistema (no bloqueante).
        Usar cv2.imshow en un bucle bloqueaba el hilo de tkinter impidiendo
        que los botones 'Volver' y 'Cerrar Sesión' respondieran."""
        subprocess.Popen(["open", ruta_mp4])

if __name__ == "__main__":
    app = AppRehabilitacion()
    app.mainloop()
