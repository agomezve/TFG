import cv2
import mediapipe as mp

def iniciar_espejo_inteligente():
    """
    Inicia la captura de vídeo y el procesamiento de pose en tiempo real.
    Implementa la Capa de Captura (OpenCV) y la Capa de Procesamiento (Mediapipe).
    """
    print("Iniciando Módulo de Captura... Presiona 'q' en la ventana de vídeo para salir.")

    # 1. Inicializamos los módulos de Mediapipe
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    # 2. Configuramos el modelo Pose Landmarker
    # model_complexity=1 es el equilibrio ideal para CPU
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 3. Capa de Captura (OpenCV): Acceso a la webcam (índice 0)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: No se puede acceder a la cámara. Revisa los permisos de macOS.")
        return

    while cap.isOpened():
        exito, frame = cap.read()
        if not exito:
            print("Ignorando frame vacío.")
            continue

        # OpenCV lee en BGR, Mediapipe procesa en RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Optimización: marcamos el frame como no escribible antes de procesar
        frame_rgb.flags.writeable = False
        
        # 4. Capa de Procesamiento: Extraemos los landmarks corporales
        resultados = pose.process(frame_rgb)
        
        # Volvemos a permitir escritura para dibujar
        frame_rgb.flags.writeable = True
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

        # 5. Capa de Presentación (Prototipo temporal): Dibujar el esqueleto
        if resultados.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame_bgr,
                resultados.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # Mostramos el resultado actuando como el "espejo inteligente"
        cv2.imshow('TFG Aaron - Biofeedback', frame_bgr)

        # Salir con la tecla 'q'
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

    # Liberación estricta de recursos
    cap.release()
    cv2.destroyAllWindows()
    pose.close()

if __name__ == "__main__":
    iniciar_espejo_inteligente()