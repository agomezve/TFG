import os
from graphviz import Digraph

def generar_esquema_capas():
    dot = Digraph(format='png')
    dot.attr(rankdir='TB', size='10,12', bgcolor='#FDFEFE', nodesep='0.8', ranksep='0.8', compound='true')
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded', 
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='2.0', margin='0.3,0.2', fontsize='14')
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # Capa de Presentación (Frontend / Cliente)
    with dot.subgraph(name='cluster_frontend') as c:
        c.attr(label='Capa de Presentación', style='dashed,rounded', color='#3498DB', fontname='Helvetica-Bold', fontsize='16', bgcolor='#EBF5FB', margin='20')
        c.node('GUI', 'Interfaz Gráfica\nMenús, Botones y Dashboard', fillcolor='#AED6F1')
        c.node('View', 'Renderizado Visual\nSuperposición de esqueleto y métricas', fillcolor='#AED6F1')

    # Capa de Lógica de Negocio (Backend / Servidor)
    with dot.subgraph(name='cluster_backend') as c:
        c.attr(label='Capa de Lógica de Negocio', style='dashed,rounded', color='#27AE60', fontname='Helvetica-Bold', fontsize='16', bgcolor='#EAFAF1', margin='20')
        c.node('Motor', 'Orquestador Principal', fillcolor='#A9DFBF')
        c.node('AI', 'Motor Biomecánico\nExtracción espacial y trigonometría', fillcolor='#A9DFBF')
        c.node('Modulos', 'Módulos de Ejercicio', fillcolor='#A9DFBF')

    # Capa de Datos
    with dot.subgraph(name='cluster_datos') as c:
        c.attr(label='Capa de Datos', style='dashed,rounded', color='#E67E22', fontname='Helvetica-Bold', fontsize='16', bgcolor='#FEF5E7', margin='20')
        c.node('DB', 'Gestor de Base de Datos\nPersistencia de historiales', shape='cylinder', fillcolor='#F5CBA7')
        c.node('Export', 'Sistema de Exportación\nGeneración de informes', shape='note', fillcolor='#F5CBA7')

    # Relaciones y flujos
    # Frontend -> Backend
    dot.edge('GUI', 'Motor', label=' Peticiones del usuario')
    dot.edge('Motor', 'AI', label=' Envía Frame')
    dot.edge('AI', 'Modulos', label=' Envía Ángulos')
    
    # Backend -> Frontend
    dot.edge('Modulos', 'Motor', label=' Devuelve Diagnóstico')
    dot.edge('Motor', 'View', label=' Ordena Actualizar Interfaz')
    
    # Backend -> Datos
    dot.edge('Modulos', 'DB', label=' Al finalizar: Guarda Estadísticas')
    dot.edge('DB', 'Export', label=' Extrae y escribe ficheros')
    
    # Datos -> Frontend
    dot.edge('DB', 'GUI', label=' Retorna historial para mostrar en Dashboard')

    ruta_salida = dot.render('esquema_arquitectura_capas', cleanup=True, view=False)
    print(f"Esquema de capas generado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema_capas()
