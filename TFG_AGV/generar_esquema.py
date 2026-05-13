import os
from graphviz import Digraph

def generar_esquema():
    # Creamos el grafo especificando el formato
    dot = Digraph(format='png')
    
    # Atributos generales del grafo (separación, márgenes, color de fondo)
    dot.attr(rankdir='TB', size='10,12', bgcolor='white', nodesep='0.6', ranksep='0.8')
    
    # Atributos globales para nodos (fuente limpia, bordes redondeados, grosor)
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded', 
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='1.5', margin='0.3,0.1')
    
    # Atributos globales para aristas (fuente, color, grosor de flechas)
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # Definición de una paleta de colores moderna y suave (tonos pastel)
    c_inicio_fin = '#D5F5E3'  # Verde pastel muy claro
    c_decision = '#FCF3CF'    # Amarillo pastel
    c_correcto = '#A9DFBF'    # Verde esmeralda pastel
    c_error = '#F5B7B1'       # Rojo coral pastel
    c_video = '#AED6F1'       # Azul cielo pastel

    # Definición de Nodos
    dot.node('Inicio', 'Captura de Movimiento', 
             shape='ellipse', fillcolor=c_inicio_fin, fontname='Helvetica-Bold')
             
    dot.node('Comparacion', '¿Movimiento Captado ==\nMovimiento Esperado?', 
             shape='diamond', fillcolor=c_decision, style='filled')
             
    dot.node('RepCorrecta', 'Repetición Correcta\n(Correctas += 1)', 
             fillcolor=c_correcto)
             
    dot.node('RepErronea', 'Repetición Errónea\n(Erróneas += 1)', 
             fillcolor=c_error)
             
    dot.node('VerificarErrores', '¿Erróneas == 3?', 
             shape='diamond', fillcolor=c_decision, style='filled')
             
    dot.node('Video', 'Reproducir Vídeo\nExplicativo del Ejercicio', 
             fillcolor=c_video)
             
    dot.node('VerificarFin', '¿Repeticiones Totales ==\nRepeticiones Esperadas?', 
             shape='diamond', fillcolor=c_decision, style='filled')
             
    dot.node('Fin', 'Fin de la Serie', 
             shape='ellipse', fillcolor=c_inicio_fin, fontname='Helvetica-Bold')

    # Conexiones (Aristas)
    dot.edge('Inicio', 'Comparacion')
    
    # Etiquetas con color en verde/rojo para mayor claridad visual
    dot.edge('Comparacion', 'RepCorrecta', label='  Sí  ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    dot.edge('Comparacion', 'RepErronea', label='  No  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    
    dot.edge('RepCorrecta', 'VerificarFin')
    
    dot.edge('RepErronea', 'VerificarErrores')
    dot.edge('VerificarErrores', 'Video', label='  Sí  ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    dot.edge('VerificarErrores', 'VerificarFin', label='  No  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    
    dot.edge('Video', 'VerificarFin')
    
    dot.edge('VerificarFin', 'Inicio', label='  No  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    dot.edge('VerificarFin', 'Fin', label='  Sí  ', fontcolor='#27AE60', fontname='Helvetica-Bold')

    # Renderizar y abrir en pantalla automáticamente
    ruta_salida = dot.render('mapa_conceptual_telerehabilitacion', cleanup=True, view=True)
    print(f"Esquema generado correctamente y abierto en pantalla.\nGuardado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema()
