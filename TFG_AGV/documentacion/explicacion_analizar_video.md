# Explicación del Código: `analizar_video.py`

Este es el **script principal del sistema** para el análisis a posteriori de videos pregrabados, interactuando de forma dinámica con los diferentes módulos de ejercicios.

## 1. Menú Principal y Selección de Módulo
Al inicio de la ejecución (`menu_principal()`), el programa muestra una interfaz en terminal. En ella, el usuario puede seleccionar un "protocolo clínico" u ejercicio.
Gracias a la arquitectura modular del código, el programa cuenta con un diccionario (`modulos_disponibles`) donde están referenciadas las clases de cada ejercicio: Sentadilla, Peso Muerto y Press Militar. Cuando se elige uno, el programa crea una instancia de ese módulo en específico (lo llamamos "inyectar el motor de reglas").

## 2. Detección y Selección de Video
El código busca automáticamente los videos localizados en la carpeta `videos/` y sus subcarpetas. Te da a elegir qué video de la lista quieres procesar.

## 3. Análisis Biomecánico (`analizar_video_guardado`)
En esta fase, suceden varios pasos críticos por cada fotograma (frame) del video:
- **Lectura del Video:** Utiliza la librería **OpenCV** para leer el archivo MP4 cuadro por cuadro.
- **Detección de Postura:** Empuja el cuadro actual, que se ve de color (BGR a RGB), al modelo neuronal predictivo de **MediaPipe Pose** para extraer las coordenadas del esqueleto.
- **Filtrado Visual:** Llama a la función `dibujar_landmarks_filtrados`. Aquí está la gracia: en vez de dibujar todo el cuerpo humano, le pide al módulo del ejercicio (por ejemplo, Sentadilla) *qué puntos exactos* (landmarks) necesita, y solo dibuja las líneas y puntos correspondientes.
- **Evaluación Médica/Deportiva:** Manda las coordenadas 3D detectadas al módulo del ejercicio llamando a `ejercicio.evaluar_postura()`. El módulo procesa las matemáticas y pone el texto de *Feedback* o Corrección en pantalla.
- Al usuario se le enseña la ventana con los puntos y el texto.

## 4. Finalización
Una vez acabado el video (o si el usuario pulsa la tecla 'q'), se rompe el bucle, se cierran las ventanas liberando memoria, y se invoca a `ejercicio.generar_informe_clinico()`, lo cual delegará en el módulo específico la responsabilidad de guardar las estadísticas en un PDF o TXT.

---
**En resumen para explicar al profesor:**
*Es el maestro de ceremonias. Enlaza los videos del paciente en disco con los modelos matemáticos y de IA de MediaPipe. Al ser independiente del tipo de ejercicio, permite que en el futuro se puedan añadir nuevos ejercicios simplemente programando el módulo, sin tocar este archivo central.*
