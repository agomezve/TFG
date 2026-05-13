# Explicación del Código: `grabar_ejercicio.py`

Este es un **script especializado en la grabación interactiva** dirigida. En lugar de procesar un video que ya existe, su función es guiar al paciente a grabarse de manera limpia e inteligentemente para generar material procesable por nuestro módulo de análisis a posteriori.

## 1. Menú de Intenciones
Primero, interroga al usuario mostrandole el número de protocolo e identificador que quiere ejecutar (Sentadilla, Peso Muerto o Press Militar) y pide cómo quiere nombrar el nuevo archivo que está por grabarse. Instancia la clase de análisis que corresponda (para aprovechar su listado de articulaciones).

## 2. Configuración y Carpetas
Chequea si el subdirectorio del ejercicio (ej. `videos/sentadilla/`) existe y si no, lo crea de forma limpia y transparente gracias a la librería fundamental del SO (`os.makedirs`). Configura el conversor MP4 de grabación (`cv2.VideoWriter_fourcc`).

## 3. Fase de Calibración / Cuenta Atrás 
Una vez arrancada la webcam, aísla un bucle inicial y provee **5 segundos de cuenta atrás** donde el paciente podrá moverse y centrarse adecuadamente alejándose de la cámara.
- Importante: En esta fase, el script dibuja el texto de la cuenta regresiva en el centro de la pantalla, pero ese texto *no se está guardando* en el videoclip de exportación, es solo visual interactivo (`HUD`).

## 4. Fase de Acción 
Después de los 5 segundos de gracia, inicia el verdadero loop de guardado. Se ejecutará forzosamente y al cronómetro exacto un proceso de 20 segundos de duración, operando así:
- Lee de la cámara el fotograma de imagen.
- Lo envía a MediaPipe Pose.
- Obtiene las líneas y posiciones del paciente (solo las predefinidas para el ejercicio).
- Las dibuja filtradas llamando a la función auxiliar `dibujar_landmarks_filtrados`.
- Manda este "Fotograma con los puntos dibujados" de vuelta a escribirse y apilarse dentro del archivo MP4 con `salida.write`.
- Modifica el fotograma local en pantalla agregando textos extra de grabación restante como Feedback para que el usuario conozca cuándo va finalizando, separando la capa de presentación de exportación.

---
**En resumen para explicar al profesor:**
*Este script estandariza el ecosistema clínico de entrada. Permite a los pacientes producir clips listos de 20 segundos para un ejercicio específico con una cuenta atrás en vivo, y procesar activamente en la IA todos los fotogramas para insertar estéticamente solo los trazados anatómicos que son del protocolo del ejercicio escogido.*
