# Explicación del Código: `modulos/modulo_base.py`

Este documento expone la estructura más arquitectural e ingenieril del proyecto y su función es aplicar las mejores prácticas sobre un diseño de "Programación Orientada a Objetos" o **Patrón de Arquitectura Modular**.

## La Clase `ModuloEjercicio`
Se importa el paquete `abc` (Abstract Base Classes) de Python para crear una clase que **actúa como una plantilla o contrato inquebrantable**. 
Ninguna instancia concreta de código se va a referir directamente al "Módulo Ejercicio", pero cualquier archivo que quiera convertirse en un ejercicio de este proyecto deberá "heredar" de esta superclase y firmar su contrato de estructura.

### Obligaciones Estructurales (Métodos Abstractos):
Aquellos métodos con el decorador `@abstractmethod` son los que obligatoriamente deben crearse en cada submódulo de ejercicio, de lo contrario el programa fallaría:
- `obtener_landmarks_relevantes()`: Para que cada deporte determine qué puntos son los que MediaPipe debe rescatar.
- `evaluar_postura()`: Donde se define todo el motor condicional lógico (máquina de estados).
- `generar_informe_clinico()`: Lógica para finalizar la evaluación y exponerla según el deporte al paciente.

### Utilidades Globales:
Esta superclase cuenta con utilidades útiles que se "donan" gratis a cualquier especialidad que herede de la clase:
- **`obtener_conexiones_relevantes`**: Ya sabe automáticamente buscar cuáles son las líneas de unión basándose en los puntos relevantes marcados.
- **`calcular_angulo_3d`**: El motor cardíaco puramente matemático. Recibe tres listas de coordenadas x,y,z (tres puntos). Transforma los tres puntos en dos "vectores matemáticos". Mediante álgebra del paquete Numpy, obtiene el "Coseno" cruzado entre estos puntos asilados en 3D y recupera el ángulo real absoluto utilizando el arco coseno. Transforma la medida final generada (que por defecto es en radianes) a grados llanos con `np.degrees()`.

---
**En resumen para explicar al profesor:**
*Se ha implementado el paradigma de programación orientada a objetos usando interfaces abstractas para la correcta extensibilidad y escalabilidad del proyecto biométrico. Esto agrupa un conjunto unificado de estándares donde reside la carga de trigonometría espacial con el cómputo de ángulos 3D para aislar la complejidad técnica fuera de los perfiles individuales de cada ejercicio fisioterapéutico.*
