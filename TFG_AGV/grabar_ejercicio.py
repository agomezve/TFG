import cv2
import time
import mediapipe as mp
import os
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

def grabar_con_landmarks_interactivo():
    """
    Permite seleccionar el tipo de ejercicio, da 5 segundos de preparación, 
    luego graba 20 segundos de vídeo detectando solo los landmarks del ejercicio seleccionado.
    Los vídeos se guardan en videos/<ejercicio>/.
    """
    print("\n" + "="*50)
    print("🎥 MÓDULO DE GRABACIÓN VISUAL (CON ESQUELETO)")
    print("="*50)
    
    # 1. SELECCIÓN DE EJERCICIO
    ejercicios_disponibles = {
        1: ("Sentadilla", "sentadilla", ModuloSentadilla),
        2: ("Peso Muerto", "peso_muerto", ModuloPesoMuerto),
        3: ("Press Militar", "press_militar", ModuloPressMilitar)
    }
    
    print("\n[PASO 1] Selecciona el tipo de ejercicio a grabar:")
    for clave, (nombre, _, _) in ejercicios_disponibles.items():
        print(f"  [{clave}] -> {nombre}")
    
    while True:
        try:
            seleccion = int(input("\nElige el número del ejercicio: "))
            if seleccion in ejercicios_disponibles:
                nombre_ejercicio, carpeta_ejercicio, ClaseEjercicio = ejercicios_disponibles[seleccion]
                
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
                        
                motor = ClaseEjercicio(nivel=nivel_elegido)
                break
            else:
                print("⚠️ Opción no válida.")
        except ValueError:
            print("⚠️ Introduce un número entero.")
    
    # Obtener landmarks filtrados del ejercicio
    indices_relevantes = motor.obtener_landmarks_relevantes()
    conexiones_relevantes = motor.obtener_conexiones_relevantes()
    
    # 2. Nombre del archivo
    nombre_base = input(f"\n[PASO 2] Introduce el nombre para el vídeo de {nombre_ejercicio}: ")
    nombre_archivo = f"{nombre_base}.mp4" if not nombre_base.endswith(".mp4") else nombre_base
    
    # Crear carpeta videos/<ejercicio>/ si no existe
    carpeta_videos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos", carpeta_ejercicio)
    if not os.path.exists(carpeta_videos):
        os.makedirs(carpeta_videos)
        
    ruta_completa = os.path.join(carpeta_videos, nombre_archivo)
        
    duracion_segundos = 20
    cuenta_atras = 5
    print(f"\n[SISTEMA] Ejercicio: {nombre_ejercicio}")
    print(f"[SISTEMA] Landmarks activos: {indices_relevantes}")
    print(f"[SISTEMA] Preparando exportación visual a: {ruta_completa}")

    # 3. Inicialización de MediaPipe (Capa de Procesamiento)
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1, 
                        min_detection_confidence=0.5, min_tracking_confidence=0.5)

    # 4. Inicialización de OpenCV (Capa de Captura)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: No se puede acceder a la webcam.")
        return

    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_asumidos = 30.0 
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    salida = cv2.VideoWriter(ruta_completa, fourcc, fps_asumidos, (ancho, alto))

    # --- CUENTA ATRÁS DE 5 SEGUNDOS (solo en pantalla, NO se graba) ---
    print(f"\n⏳ ¡Colócate en posición! Tienes {cuenta_atras} segundos...")
    tiempo_cuenta = time.time()
    while True:
        restante = cuenta_atras - (time.time() - tiempo_cuenta)
        if restante <= 0:
            break
        exito, frame = cap.read()
        if not exito:
            break
        # Mostrar cuenta atrás en pantalla (NO se escribe al archivo)
        texto_cuenta = f"Preparate... {int(restante) + 1}"
        cv2.rectangle(frame, (0, alto // 2 - 60), (ancho, alto // 2 + 20), (0, 0, 0), -1)
        cv2.putText(frame, texto_cuenta, (ancho // 2 - 200, alto // 2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        cv2.imshow('TFG Aaron - Grabacion Visual', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cap.release()
            salida.release()
            cv2.destroyAllWindows()
            pose.close()
            print("\n[SISTEMA] Grabación cancelada durante la cuenta atrás.")
            return

    print(f"\n🔴 ¡GRABANDO {nombre_ejercicio.upper()}! (20 segundos)")
    
    # 5. Bucle principal con control temporal
    tiempo_inicio = time.time()
    
    while (time.time() - tiempo_inicio) < duracion_segundos:
        exito, frame = cap.read()
        if not exito:
            break
            
        # --- PROCESAMIENTO MEDIAPIPE ---
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False
        resultados = pose.process(frame_rgb)
        frame_rgb.flags.writeable = True
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        # Si detecta el cuerpo, dibujamos SOLO los landmarks del ejercicio
        if resultados.pose_landmarks:
            dibujar_landmarks_filtrados(frame_bgr, resultados.pose_landmarks, 
                                         indices_relevantes, conexiones_relevantes)
            
        # --- GUARDADO (sin HUD, solo esqueleto filtrado) ---
        salida.write(frame_bgr)
        
        # --- CAPA DE PRESENTACIÓN (HUD) solo en pantalla ---
        frame_preview = frame_bgr.copy()
        tiempo_restante = duracion_segundos - (time.time() - tiempo_inicio)
        texto_hud = f"GRABANDO {nombre_ejercicio.upper()}: {int(tiempo_restante)}s restantes"
        cv2.rectangle(frame_preview, (0, 0), (ancho, 40), (0, 0, 255), -1)
        cv2.putText(frame_preview, texto_hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow('TFG Aaron - Grabacion Visual', frame_preview)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[SISTEMA] Grabación cancelada manualmente.")
            break

    cap.release()
    salida.release()
    cv2.destroyAllWindows()
    pose.close()
    print(f"\n✅ Grabación finalizada. Vídeo de {nombre_ejercicio} guardado: {nombre_archivo}")

if __name__ == "__main__":
    grabar_con_landmarks_interactivo()