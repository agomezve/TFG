import os
from graphviz import Digraph

def generar_esquema_librerias():
    # Inicialización del grafo
    dot = Digraph(format='png')
    
    # Atributos generales
    dot.attr(rankdir='TB', size='10,10', bgcolor='#FDFEFE', nodesep='0.8', ranksep='1.0', compound='true')
    
    # Estilo base para nodos
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded', 
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='2.0', margin='0.3,0.2', fontsize='14')
    
    # Estilo base para aristas
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # Nodos externos (Librerías)
    dot.node('OpenCV', 'OpenCV\nCaptura fotogramas y\nrenderiza la interfaz', fillcolor='#AED6F1')
    dot.node('MediaPipe', 'MediaPipe AI\nInferencia topológica:\nextrae 33 nodos 3D', fillcolor='#D5F5E3')
    dot.node('NumPy', 'NumPy\nEstructuración matricial y\ncálculo vectorial', fillcolor='#FAD7A1')
    
    # Subgrafo para la App
    with dot.subgraph(name='cluster_app') as c:
        c.attr(label='Aplicación ', style='dashed,rounded', color='#BDC3C7', fontname='Helvetica-Bold', fontsize='16', bgcolor='#F8F9F9', margin='20')
        c.node('Logica', 'Módulo de Ejercicios\nEvaluación de tolerancias,\nfeedback y seguridad', fillcolor='#E8DAEF')
        c.node('SQLite', 'Base de Datos\nAlmacenamiento del\nhistorial clínico', shape='cylinder', fillcolor='#D7DBDD')
        
        c.edge('Logica', 'SQLite', label=' Exporta métricas')

    # Relaciones y flujo circular
    dot.edge('OpenCV', 'MediaPipe', label=' 1. Envía el Frame convertido a RGB')
    dot.edge('MediaPipe', 'NumPy', label=' 2. Devuelve posiciones biológicas (Landmarks)')
    dot.edge('NumPy', 'Logica', label=' 3. Transforma a Ángulos Biométricos')
    dot.edge('Logica', 'OpenCV', label=' 4. Ordena superponer alertas visuales y gráficas')

    # Renderizar y abrir en pantalla automáticamente
    ruta_salida = dot.render('esquema_relacion_librerias', cleanup=True, view=False)
    print(f"Esquema generado correctamente y guardado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema_librerias()
