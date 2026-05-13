# Archivo: analizar_video.py
import cv2
import mediapipe as mp
import glob
import os

# Importamos nuestras clases modulares desde sus respectivos archivos
from modulos.modulo_sentadilla import ModuloSentadilla
from modulos.modulo_peso_muerto import ModuloPesoMuerto
from modulos.modulo_press_militar import ModuloPressMilitar

def dibujar_landmarks_filtrados(frame, pose_landmarks, indices_relevantes, conexiones_relevantes):
    """Dibuja en el frame solo los landmarks y conexiones relevantes para el ejercicio."""
    h, w, _ = frame.shape
    
    # Dibujar conexiones (líneas)
    for a, b in conexiones_relevantes:
        pt_a = pose_landmarks.landmark[a]
        pt_b = pose_landmarks.landmark[b]
        x_a, y_a = int(pt_a.x * w), int(pt_a.y * h)
        x_b, y_b = int(pt_b.x * w), int(pt_b.y * h)
        cv2.line(frame, (x_a, y_a), (x_b, y_b), (245, 66, 230), 2)
    
    # Dibujar puntos (landmarks)
    for idx in indices_relevantes:
        pt = pose_landmarks.landmark[idx]
        cx, cy = int(pt.x * w), int(pt.y * h)
        cv2.circle(frame, (cx, cy), 5, (245, 117, 66), -1)
        cv2.circle(frame, (cx, cy), 6, (245, 66, 230), 1)

def analizar_video_guardado(ruta_video, ejercicio):
    print(f"\n[SISTEMA] Iniciando análisis biomecánico del vídeo: {ruta_video}")
    print(f"[SISTEMA] Motor de reglas cargado: {ejercicio.__class__.__name__}")
    
    # Obtener landmarks y conexiones específicas del ejercicio
    indices_relevantes = ejercicio.obtener_landmarks_relevantes()
    conexiones_relevantes = ejercicio.obtener_conexiones_relevantes()
    
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=2, 
                        min_detection_confidence=0.5, min_tracking_confidence=0.5)
    
    cap = cv2.VideoCapture(ruta_video)

    while cap.isOpened():
        exito, frame = cap.read()
        if not exito:
            break 

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        resultados = pose.process(frame_rgb)
        frame_rgb.flags.writeable = True
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        if resultados.pose_landmarks and resultados.pose_world_landmarks:
            # Dibujar SOLO los landmarks relevantes para este ejercicio
            dibujar_landmarks_filtrados(frame_bgr, resultados.pose_landmarks, 
                                         indices_relevantes, conexiones_relevantes)
            
            # El motor modular (sea cual sea) evalúa el frame
            ejercicio.evaluar_postura(
                resultados.pose_world_landmarks.landmark, 
                resultados.pose_landmarks.landmark, 
                frame_bgr
            )

        cv2.imshow('TFG Aaron - Plataforma Modular', frame_bgr)
        if cv2.waitKey(30) & 0xFF == ord('q'): 
            break

    ejercicio.generar_informe_clinico()

    cap.release()
    cv2.destroyAllWindows()
    pose.close()

def menu_principal():
    print("\n" + "="*50)
    print("🏥 PLATAFORMA DE TELEREHABILITACIÓN (TFG Aarón)")
    print("="*50)
    
    # DICCIONARIO DE MÓDULOS INYECTADOS
    modulos_disponibles = {
        1: ("Sentadilla", "sentadilla", ModuloSentadilla),
        2: ("Peso Muerto", "peso_muerto", ModuloPesoMuerto),
        3: ("Press Militar", "press_militar", ModuloPressMilitar)
    }

    # PASO 1: SELECCIÓN DE EJERCICIO
    print("\n[PASO 1] Selecciona el protocolo clínico a aplicar:")
    for clave, (nombre, _, _) in modulos_disponibles.items():
        print(f"  [{clave}] -> {nombre}")
        
    while True:
        try:
            seleccion_ej = int(input("\nElige el número del ejercicio: "))
            if seleccion_ej in modulos_disponibles:
                nombre_ejercicio, carpeta_ejercicio, ClaseEjercicio = modulos_disponibles[seleccion_ej]
                
                print(f"\n[SISTEMA] Has seleccionado: {nombre_ejercicio}")
                print("Selecciona el nivel de dificultad:")
                print("  [1] -> Principiante (Mayor holgura en rangos y técnica)")
                print("  [2] -> Avanzado (Evaluación técnica estricta)")
                while True:
                    nivel_str = input("\nElige el nivel (1 o 2): ")
                    if nivel_str == "1":
                        nivel_elegido = "principiante"
                        break
                    elif nivel_str == "2":
                        nivel_elegido = "avanzado"
                        break
                    else:
                        print("⚠️ Opción no válida. Introduce 1 o 2.")
                        
                motor_ejercicio = ClaseEjercicio(nivel=nivel_elegido) # Instanciación dinámica
                break
            else:
                print("⚠️ Opción no válida.")
        except ValueError:
            print("⚠️ Introduce un número entero.")

    # PASO 2: SELECCIÓN DE VÍDEO (busca en videos/<ejercicio>/ y en videos/)
    carpeta_base_videos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
    carpeta_ejercicio_videos = os.path.join(carpeta_base_videos, carpeta_ejercicio)
    
    videos_disponibles = []
    # Buscar en la subcarpeta del ejercicio
    if os.path.exists(carpeta_ejercicio_videos):
        videos_disponibles += glob.glob(os.path.join(carpeta_ejercicio_videos, "*.mp4"))
    # También buscar en la carpeta raíz videos/ (compatibilidad con vídeos anteriores)
    if os.path.exists(carpeta_base_videos):
        videos_disponibles += glob.glob(os.path.join(carpeta_base_videos, "*.mp4"))
    
    if not videos_disponibles:
        print(f"\n❌ No hay vídeos .mp4 disponibles. Graba uno primero con grabar_ejercicio.py.")
        return

    print(f"\n[PASO 2] Selecciona el vídeo para analizar con el módulo de {nombre_ejercicio}:")
    for indice, video in enumerate(videos_disponibles):
        print(f"  [{indice}] -> {os.path.basename(video)}")
    
    while True:
        try:
            seleccion_vid = int(input("\nElige el número del vídeo: "))
            if 0 <= seleccion_vid < len(videos_disponibles):
                video_elegido = videos_disponibles[seleccion_vid]
                # Ejecución
                analizar_video_guardado(video_elegido, motor_ejercicio)
                break
            else:
                print("⚠️ Número de vídeo fuera de rango.")
        except ValueError:
            print("⚠️ Introduce un número entero.")

if __name__ == "__main__":
    menu_principal()