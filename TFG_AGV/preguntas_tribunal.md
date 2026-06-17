# 🎓 Simulacro de Tribunal — TFG: Detección y Corrección de Movimiento para Telerehabilitación

> **Rol:** Profesor del tribunal evaluador  
> **Proyecto:** Plataforma de telerehabilitación con visión artificial (MediaPipe + OpenCV + Python)  
> **Alumno:** Aaron Gómez Vera

---

## ❓ PREGUNTA 1 — Motivación y contexto clínico

> *"¿Por qué existe la necesidad de una solución como la tuya? ¿Qué problema clínico real resuelve tu sistema?"*

### ✅ Respuesta modelo

El problema de partida es la **brecha entre la clínica y el domicilio del paciente**. Cuando un fisioterapeuta prescribe ejercicios para casa, no tiene ninguna forma objetiva de saber si el paciente los está ejecutando correctamente. El paciente puede olvidar la técnica, compensar con grupos musculares incorrectos, o simplemente abandonar. Esto provoca:

- **Lesiones secundarias** por mala técnica repetida.
- **Recaídas** y alargamiento del proceso de recuperación.
- **Abandono terapéutico**, uno de los mayores problemas en fisioterapia.

Mi solución cierra ese vacío convirtiendo una cámara estándar en un fisioterapeuta virtual que evalúa la postura en tiempo real, da feedback inmediato y genera un informe que el profesional puede revisar. Esto también supera barreras geográficas y de movilidad, que son especialmente relevantes para pacientes mayores o con movilidad reducida.

---

## ❓ PREGUNTA 2 — Diferenciación respecto al estado del arte

> *"Existen soluciones comerciales como TrakPhysio o Kaia Health. ¿En qué se diferencia tu proyecto de ellas?"*

### ✅ Respuesta modelo

Las soluciones comerciales que analicé presentan limitaciones importantes para el contexto académico y clínico local:

1. **Coste prohibitivo**: son plataformas SaaS (Software as a Service) con licencias por profesional o por paciente.
2. **Caja negra**: no permiten al fisioterapeuta personalizar los umbrales biomecánicos ni añadir ejercicios propios.
3. **Dependencia de internet y servidores externos**: los datos del paciente viajan a terceros, con implicaciones de privacidad (RGPD).

Mi sistema es completamente **local, offline y de código abierto**. El fisioterapeuta tiene control total: puede ajustar los rangos articulares, añadir nuevos ejercicios en minutos gracias a la arquitectura modular, y los datos del paciente nunca salen del ordenador. Además, funciona con una webcam estándar, sin hardware adicional.

---

## ❓ PREGUNTA 3 — MediaPipe y su fiabilidad clínica

> *"MediaPipe es una librería de propósito general desarrollada por Google, no un instrumento médico certificado. ¿Cómo justificas su uso en un contexto clínico?"*

### ✅ Respuesta modelo

Es una pregunta muy pertinente. MediaPipe Pose Landmarker no es un dispositivo médico homologado, y así lo reconozco explícitamente en la memoria. Sin embargo, hay tres argumentos que justifican su uso:

**Primero**, la literatura científica avala su fiabilidad. El estudio de Latreche et al. (2023) publicado en *Measurement* validó la precisión de MediaPipe para mediciones cinemáticas de rehabilitación, obteniendo correlaciones superiores al 95% con sistemas de captura de movimiento de referencia en varios rangos articulares.

**Segundo**, mi sistema no actúa como diagnóstico médico. Es una herramienta de **apoyo y seguimiento**, igual que una báscula no diagnostica obesidad pero sí informa sobre el peso. La decisión clínica siempre recae en el fisioterapeuta.

**Tercero**, utilizo las **coordenadas 3D world landmarks** en lugar de las 2D de pantalla, lo que mitiga significativamente los errores de perspectiva que son la principal fuente de imprecisión de la herramienta.

---

## ❓ PREGUNTA 4 — Arquitectura técnica y decisiones de diseño

> *"¿Por qué elegiste una arquitectura modular basada en herencia y polimorfismo en lugar de un enfoque más simple como un único script?"*

### ✅ Respuesta modelo

La respuesta la viví en carne propia durante el desarrollo. Al principio empecé con un único archivo central con toda la lógica. Cuando quise añadir el cuarto ejercicio, el código era tan acoplado que modificar el umbral de rodilla en la sentadilla rompía la lógica del press militar. Era inmantenible.

La solución fue aplicar el **patrón Estrategia** con una clase base abstracta `ModuloEjercicio`. Esta clase define un contrato que todos los ejercicios deben cumplir:

- `obtener_landmarks_relevantes()` → ¿qué puntos del cuerpo me interesan?
- `evaluar_postura()` → ¿cómo evalúo si la técnica es correcta?
- `generar_informe_clinico()` → ¿qué hago al finalizar?

El orquestador principal se vuelve **ciego al ejercicio concreto**: simplemente llama a esos métodos genéricos. Esto tiene una consecuencia directa: durante la última fase del proyecto, añadí 4 nuevos ejercicios complejos en muy poco tiempo, sin tocar ni una sola línea del motor visual principal. Eso es escalabilidad real.

---

## ❓ PREGUNTA 5 — El problema de la perspectiva y los ángulos 3D

> *"¿Qué es el error de paralaje en este contexto y cómo lo has resuelto?"*

### ✅ Respuesta modelo

El error de paralaje ocurre cuando el paciente no está perfectamente alineado de perfil con la cámara. Si calculo el ángulo de rodilla con trigonometría 2D (los píxeles de la pantalla), una rotación de solo 15 grados del paciente puede producir un error de 20-30 grados en el ángulo calculado. Esto generaría falsos positivos: el sistema penalizaría repeticiones perfectamente ejecutadas.

La solución fue abandonar completamente la geometría 2D y trabajar con las **world landmarks** de MediaPipe, que son coordenadas tridimensionales métricas (x, y, z) donde el origen es la cadera del paciente. Con estas coordenadas aplico álgebra lineal: construyo dos vectores a partir del punto articular de interés y calculo el ángulo entre ellos usando el **producto escalar y el arcocoseno**:

`θ = arccos( (BA⃗ · BC⃗) / (|BA⃗| × |BC⃗|) )`

Esto da el ángulo real en el espacio 3D independientemente de la orientación del paciente respecto a la cámara. Es la misma matemática que usa la biomecánica clásica en laboratorios de captura de movimiento.

---

## ❓ PREGUNTA 6 — Validación y pruebas con usuarios reales

> *"¿Cómo has validado que tu sistema mide bien? ¿Con qué usuarios lo has probado?"*

### ✅ Respuesta modelo

La validación tiene dos niveles:

**Nivel técnico**: Realicé pruebas con vídeos pregrabados de los mismos ejercicios bajo diferentes condiciones de iluminación, ropa, distancia y ángulo de cámara. Verifiqué que el sistema detectaba correctamente repeticiones completas y penalizaba las incompletas, ajustando los umbrales iterativamente.

**Nivel clínico**: Conté con la validación de un profesional de la salud —un fisioterapeuta— que evaluó si los umbrales biomecánicos definidos se correspondían con los criterios clínicos reales para cada ejercicio. Por ejemplo, si el sistema exige en la sentadilla un ángulo de rodilla inferior a 90° para validar la repetición, el profesional confirmó que ese criterio se alinea con la práctica clínica estándar.

Reconozco que la muestra es limitada para un estudio de eficacia clínica, y lo señalo explícitamente como una línea de trabajo futuro: un ensayo con N ≥ 30 pacientes con mediciones comparadas con un sistema de captura de movimiento de referencia.

---

## ❓ PREGUNTA 7 — Sistema de alertas y seguridad del paciente

> *"¿Cómo evitas que un paciente se lesione más usando tu aplicación incorrectamente?"*

### ✅ Respuesta modelo

Implementé un **sistema de cortafuegos de seguridad** en dos capas:

**Primera capa — Detención preventiva automática**: Si el paciente acumula 3 errores totales en la sesión, o 2 errores consecutivos, el sistema detiene la grabación inmediatamente y redirige al paciente al vídeo explicativo del ejercicio. La premisa es: si alguien falla dos veces seguidas, probablemente está fatigado o no recuerda bien la técnica, y seguir empeorará la situación.

**Segunda capa — Feedback visual tricolor en tiempo real**: El esqueleto digital cambia de color:
- 🔵 Azul: posición neutra, sin evaluar
- 🟢 Verde: postura correcta, repetición válida
- 🔴 Rojo: error técnico detectado

Esto da información instantánea al paciente para corregirse antes de que el error se consolide. La barra de progreso animada también refuerza visualmente cuándo una repetición está cerca de completarse o cuándo está fallando.

---

## ❓ PREGUNTA 8 — Gestión de datos y privacidad

> *"¿Cómo almacenas y proteges los datos clínicos de los pacientes?"*

### ✅ Respuesta modelo

El sistema almacena todos los datos **exclusivamente en local**, en el propio ordenador del fisioterapeuta. No hay ninguna conexión a servicios de terceros ni transmisión de datos por red.

La base de datos utilizada es SQLite, un fichero ligero que se guarda en la carpeta del proyecto. Contiene únicamente:
- Nombre del paciente, ID y notas clínicas básicas
- Estadísticas de sesiones: fecha, ejercicio, nivel, repeticiones y errores

Los vídeos grabados de las sesiones se guardan en subcarpetas organizadas por paciente y fecha. Adicionalmente, se genera automáticamente un informe en texto plano al finalizar cada sesión.

Reconozco que el sistema actual es un prototipo de investigación, y para una comercialización real habría que añadir: cifrado de la base de datos, autenticación robusta con contraseñas hasheadas, y posiblemente cumplimiento formal con el RGPD europeo en cuanto a consentimiento informado y derecho al olvido.

---

## ❓ PREGUNTA 9 — Limitaciones del sistema

> *"¿Cuáles son las principales limitaciones de tu sistema y qué no puede hacer?"*

### ✅ Respuesta modelo

Ser honesto sobre las limitaciones es importante en cualquier trabajo científico. Las principales son:

**Técnicas**:
- El sistema requiere buenas condiciones de iluminación y un fondo despejado. En entornos domésticos desordenados, MediaPipe puede perder la detección.
- Depende de que el paciente esté correctamente encuadrado en la cámara, lo que requiere cierta disciplina de posicionamiento.
- La webcam debe capturar el cuerpo completo, lo que limita espacios muy pequeños.

**Clínicas**:
- No sustituye la evaluación manual del fisioterapeuta: no puede palpar, medir fuerza muscular ni detectar dolor.
- No es apto para fases agudas postquirúrgicas o lesiones que requieren supervisión directa.
- La validación clínica es limitada: las pruebas se hicieron con un número reducido de usuarios.

**De usabilidad**:
- Puede existir una brecha digital en pacientes mayores no familiarizados con tecnología.
- El sistema actual es exclusivamente de escritorio (Mac/Windows/Linux), no existe versión móvil.

---

## ❓ PREGUNTA 10 — Trabajo futuro y visión de producto

> *"¿Qué haría de este proyecto un producto real y cuáles son las siguientes líneas de investigación?"*

### ✅ Respuesta modelo

Identifico varias líneas de evolución ordenadas por impacto:

**A corto plazo (meses)**:
- Migración a una **aplicación móvil** (iOS/Android), que es el dispositivo que el paciente tiene en casa. Tecnologías como TensorFlow Lite o el MediaPipe Tasks de JavaScript permitirían ejecutar el modelo directamente en el móvil.
- Añadir más ejercicios clínicamente relevantes siguiendo el mismo patrón modular.

**A medio plazo (6-18 meses)**:
- **Sincronización en la nube**: permitir que el fisioterapeuta acceda a los informes del paciente desde su clínica sin que el paciente tenga que llevar físicamente el ordenador.
- **Gamificación**: sistemas de puntos, rachas de entrenamiento y logros para mejorar la adherencia, especialmente en perfiles jóvenes.

**A largo plazo (investigación)**:
- **Entrenamiento de modelos propios**: en lugar de usar los umbrales biomecánicos definidos manualmente, usar los datos acumulados para entrenar un modelo de ML que aprenda qué constituye una repetición "correcta" de forma adaptativa por paciente.
- **Realidad Aumentada**: superponer el esqueleto digital directamente sobre el cuerpo real usando gafas AR o el modo AR de un móvil, para una experiencia más inmersiva.
- **Control por voz**: permitir al paciente interactuar con el sistema sin tocar el teclado mientras hace ejercicio.

---

## 🧠 Consejo final para la defensa

> Cuando el tribunal te haga una pregunta difícil, **no improvises sin base**. La estructura que mejor funciona es:
> 1. Reconocer la pregunta ("Es una cuestión muy relevante...")
> 2. Contextualizar el problema
> 3. Explicar tu solución o decisión
> 4. Reconocer la limitación si existe ("Para trabajo futuro...")

**¡Mucha suerte mañana! 🎓**
