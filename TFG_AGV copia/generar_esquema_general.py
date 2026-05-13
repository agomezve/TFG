import os
from graphviz import Digraph

def generar_esquema_general():
    # Inicialización del grafo
    dot = Digraph(format='png')
    
    # Atributos generales
    dot.attr(rankdir='TB', size='12,20', bgcolor='#F8F9F9', nodesep='0.8', ranksep='1.0', compound='true')
    
    # Estilo base para nodos
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded', 
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='2.0', margin='0.3,0.2', fontsize='14')
    
    # Estilo base para aristas
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # Paleta de colores Pastel más vivos
    c_inicio_fin = '#D5F5E3'  # Verde pastel
    c_decision = '#FCF3CF'    # Amarillo pastel
    c_accion = '#E8DAEF'      # Morado pastel
    c_core = '#A9DFBF'        # Verde esmeralda pastel
    c_video = '#AED6F1'       # Azul cielo pastel
    c_error = '#F5B7B1'       # Rojo coral pastel
    c_data = '#FAD7A1'        # Naranja pastel
    c_doc = '#D7DBDD'         # Gris claro para documentos

    # Estilos comunes para los bloques contenedores (clusters)
    cluster_style = {
        'style': 'dashed,rounded', 
        'color': '#BDC3C7', 
        'fontname': 'Helvetica-Bold', 
        'fontsize': '16', 
        'fontcolor': '#34495E', 
        'bgcolor': '#FDFEFE',
        'margin': '20'
    }

    # 1. BLOQUE DE AUTENTICACIÓN
    with dot.subgraph(name='cluster_auth') as c:
        c.attr(label='Módulo de Gestión de Usuarios', **cluster_style)
        c.node('Inicio', 'Abrir Aplicación', shape='ellipse', fillcolor=c_inicio_fin, fontname='Helvetica-Bold')
        c.node('Registrado', '¿Paciente\nRegistrado?', shape='diamond', fillcolor=c_decision, style='filled')
        c.node('Login', 'Iniciar Sesión', fillcolor=c_accion)
        c.node('Registro', 'Registrarse', fillcolor=c_accion)
    
    # 2. BLOQUE MENÚ PRINCIPAL E INTERFAZ
    with dot.subgraph(name='cluster_dashboard') as c:
        c.attr(label='Módulo de Interfaz y Navegación', **cluster_style)
        c.node('Dashboard', 'Menú Principal', fillcolor=c_core, fontname='Helvetica-Bold', fontsize='16')
        c.node('Accion', '¿Qué opción\nse ha elegido?', shape='diamond', fillcolor=c_decision, style='filled')
        c.node('Estadisticas', 'Ver Historial Clínico\ny Progreso', shape='folder', fillcolor=c_data)
        c.node('VideoRep', 'Ver Vídeo\nExplicativo', fillcolor=c_video)
    
    # 3. BLOQUE DE IA Y BIOMECÁNICA (Bucle principal)
    with dot.subgraph(name='cluster_motor') as c:
        c.attr(label='Motor Biomecánico y Evaluación Técnica (IA)', **cluster_style)
        c.node('Dificultad', 'Seleccionar Dificultad', fillcolor=c_accion)
        c.node('Preparacion', 'Fase de Calibración', fillcolor=c_core)
        c.node('Captura', 'Captura de Movimiento', fillcolor=c_core)
        c.node('Analisis', 'Análisis Biomecánico', fillcolor=c_core)
        c.node('Seguridad', '¿Acumula\n3 errores técnicos?', shape='diamond', fillcolor=c_decision, style='filled')
        c.node('Abortar', 'Abortar Serie\npor Seguridad', fillcolor=c_error)
        c.node('FinSerie', '¿El paciente pulsa\n"Finalizar Serie"?', shape='diamond', fillcolor=c_decision, style='filled')

    # 4. BLOQUE DE PERSISTENCIA DE DATOS
    with dot.subgraph(name='cluster_datos') as c:
        c.attr(label='Capa de Datos', **cluster_style)
        c.node('Informe', 'Generar Informe Clínico\ny Guardar', shape='note', fillcolor=c_doc)

    # ================= CONEXIONES =================
    
    # Autenticación
    dot.edge('Inicio', 'Registrado')
    dot.edge('Registrado', 'Login', label='  Sí  ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    dot.edge('Registrado', 'Registro', label='  No  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    
    dot.edge('Login', 'Dashboard')
    dot.edge('Registro', 'Dashboard')
    
    # Dashboard a Opciones
    dot.edge('Dashboard', 'Accion', label=' Selecciona un ejercicio ')
    dot.edge('Accion', 'Estadisticas', label=' Estadísticas ')
    dot.edge('Accion', 'VideoRep', label=' Vídeo ')
    dot.edge('Accion', 'Dificultad', label=' Iniciar ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    
    # Retornos al Dashboard
    dot.edge('Estadisticas', 'Dashboard', label=' Volver ')
    dot.edge('VideoRep', 'Dashboard', label=' Volver ')
    
    # Flujo de Ejercicio
    dot.edge('Dificultad', 'Preparacion')
    dot.edge('Preparacion', 'Captura')
    dot.edge('Captura', 'Analisis')
    
    # Flujo de Análisis y Seguridad
    dot.edge('Analisis', 'Seguridad')
    dot.edge('Seguridad', 'Abortar', label='  Sí  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    dot.edge('Abortar', 'VideoRep', label=' Redirigir a Vídeo ')
    
    dot.edge('Seguridad', 'FinSerie', label='  No  ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    
    # Bucle de captura o Fin
    dot.edge('FinSerie', 'Captura', label='  No  ', fontcolor='#C0392B', fontname='Helvetica-Bold')
    dot.edge('FinSerie', 'Informe', label='  Sí  ', fontcolor='#27AE60', fontname='Helvetica-Bold')
    
    # Del informe de vuelta al inicio
    dot.edge('Informe', 'Dashboard', label=' Serie Completada ')

    # Renderizar y abrir en pantalla automáticamente
    ruta_salida = dot.render('mapa_flujo_completo_app', cleanup=True, view=True)
    print(f"Esquema general generado correctamente y abierto en pantalla.\nGuardado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema_general()
