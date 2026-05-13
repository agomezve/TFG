# Explicación del Código: `modulos/modulo_sentadilla.py`

Esta es la implementación **clínica** concreta para detectar errores técnicos al realizar una sentadilla básica. Al heredar de `ModuloEjercicio`, aplica la plantilla y centra su procesamiento en un conjunto concreto del cuerpo humano.

## Los Requisitos de Rastreo Biométrico
La función `obtener_landmarks_relevantes` inscribe únicamente los lados del tren inferior, solicitando a la cámara dibujar y trackear solamente:
- Las caderas (#23, #24)
- Las rodillas (#25, #26)
- Los tobillos (#27, #28)

## 1. El Motor Lógico (Máquina de Estados)
Cuando el modulo recibe la foto (`evaluar_postura`), el código invoca velozmente el algoritmo matemático base (`calcular_angulo_3d`) para derivar la apertura principal de la extremidad inferior y comienza a evaluar iterativamente la sentadilla separando el comportamiento interno por estados o **Fases**: `DE PIE`, `BAJANDO` y `SUBIENDO`.

## 2. Los Umbrales Clínicos y las Detecciones de Fallos
Posee una variable base llamada `self.umbrales` que guarda las configuraciones máximas y admisibles antes de dar el aviso preventivo:
- **Rango de Repeticiones**: Se establece que para que cuente como inicio de sentadilla la rodilla debe cerrarse algo menos que 160º. Por cada iteración busca hasta dónde llegó la flexión más profunda y cuenta una repetición si vuelve a extender por arriba del umbral.
- **El famoso «Valgo de rodilla»:** Resta el espacio tridimensional de apertura entre el punto de la cadera (`cadera[0]`, referenciando al eje X frente al objetivo visual) y la rodilla. Si esa variable diferencial es superior al margen clínico establecido (alrededor de 0.05), el software salta alarmado modificando todo en pantalla para generar color rojo de prevención alertando: **"¡CUIDADO! Rodilla hacia adentro (Valgo)."**

## 3. Resultados 
La etapa `generar_informe_clinico()` empaqueta todos los descubrimientos almacenados telemétricamente en una traza de historial en carpetas y genera dinámicamente el sumario de txt con la media profunda obtenida y el porcentaje de fracasos para ese ejercicio, aportando un documento analítico apto para los rehabilitadores.

---
**En resumen para explicar al profesor:**
*Este script de lógica local implementa una Máquina de Estados Finita dedicada exclusivamente a interpretar los ángulos inferioes de flexión en las Sentadillas. Incorpora umbrales programados de protección para el Valgo que advierten al paciente presencial, y paralelamente consolida los ángulos máximos obtenidos en formato TXT estructurado tras la práctica.*
