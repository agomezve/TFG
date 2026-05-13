import cv2
import numpy as np
import mediapipe as mp
import sys

def test_stack_definitivo():
    print("=== INICIANDO DIAGNÓSTICO DEL STACK TFG ===")
    
    try:
        # 1. Test de NumPy (Capa Matemática)
        print("[1/3] Probando NumPy (Geometría Vectorial)...")
        # Creamos una imagen sintética negra de 500x500 píxeles con 3 canales (RGB)
        imagen_sintetica = np.zeros((500, 500, 3), dtype=np.uint8)
        print("      ✅ NumPy operativo.")

        # 2. Test de OpenCV (Capa de Captura/Conversión)
        print("[2/3] Probando OpenCV (Manipulación de Matrices)...")
        # Dibujamos un rectángulo verde para darle información a la imagen
        cv2.rectangle(imagen_sintetica, (100, 100), (400, 400), (0, 255, 0), -1)
        # Simulamos la conversión de espacio de color
        imagen_rgb = cv2.cvtColor(imagen_sintetica, cv2.COLOR_BGR2RGB)
        print("      ✅ OpenCV operativo y compilado correctamente.")

        # 3. Test de MediaPipe (Capa de Procesamiento)
        print("[3/3] Probando MediaPipe Pose (Red Neuronal C++)...")
        mp_pose = mp.solutions.pose
        # Inicializamos el modelo de forma estricta
        pose = mp_pose.Pose(static_image_mode=True, model_complexity=1)
        
        # Procesamos la imagen sintética (obviamente no encontrará un humano, 
        # pero si no crashea, significa que los pesos del modelo se cargaron en RAM)
        resultados = pose.process(imagen_rgb)
        
        if resultados.pose_landmarks is None:
            print("      ✅ MediaPipe operativo (Analizó la imagen sin errores aunque no encontró un cuerpo).")
        
        pose.close()
        
        print("\n🚀 DIAGNÓSTICO COMPLETADO: Tu entorno está 100% listo para desarrollar la plataforma modular.")

    except Exception as e:
        print(f"\n❌ ERROR FATAL detectado en el entorno: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_stack_definitivo()