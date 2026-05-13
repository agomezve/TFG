# Explicación del Código: `captura_webcam.py`

Este archivo contiene el código para el sistema en tiempo real y constituye un prototipo sencillo de lo que podríamos llamar un **"espejo inteligente"**. 

## ¿Para qué sirve?
Tiene el objetivo fundamental de actuar como la **Capa de Captura y Presentación temporal** del TFG para certificar que el reconocimiento base de posturas con la webcam funciona bien y sin trabas. No incluye la lógica interna ni los cálculos angulares específicos de cada ejercicio, sirve solo de monitor en tiempo real del esqueleto completo.

## Explicación paso a paso de su flujo:
1. **Inicialización de la IA (MediaPipe):**
   Carga las utilidades de MediaPipe Pose, para procesar la captura de video buscando puntos corporales (Landmarks). Utiliza una complejidad de modelo de 1 (`model_complexity=1`), lo cual es un excelente equilibrio para que a la CPU estándar le dé tiempo a no tener latencia, mientras mantiene una buena precisión.

2. **Acceso a la Cámara:**
   Llama a OpenCV (`cv2.VideoCapture(0)`) para encender la webcam por defecto del ordenador (dispositivo número 0). 

3. **Bucle Infinito Analítico:**
   Empieza a capturar cuadros o imágenes por segundo continuamente. 
   - A cada imagen, le cambia la codificación de color (OpenCV lee imágenes en formato BGR por defecto, pero MediaPipe necesita que sea RGB). 
   - Optimiza los recursos bloqueando la escritura en la imagen temporalmente mientras procesa (`frame_rgb.flags.writeable = False`).
   - El modelo matemático de MediaPipe procesa y se produce un resultado: Una malla de coordenadas esqueléticas.

4. **El Renderizado (Feedback):**
   Usa `mp_drawing.draw_landmarks()` para superponer en colorines la interpretación visual que el ordenador está haciendo del cuerpo del usuario encima del video original. Todo el esqueleto será dibujado en pantalla.

5. El bucle termina y libera correctamente los periféricos del ordenador al pulsar la tecla `'q'`.

---
**En resumen para explicar al profesor:**
*Este script levanta la cámara, ejecuta el modelo de MediaPipe general y proyecta el esqueleto completo en la cara del usuario a tiempo real. Lo utilizamos como 'checker' diagnóstico de bajo coste para asegurar que el tracking por IA está funcionando a buena resolución y refresco.*
