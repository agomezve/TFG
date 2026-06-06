import os
from graphviz import Digraph

def generar_esquema_librerias():
    # Inicialización del grafo
    dot = Digraph(format='png')

    # Atributos generales
    dot.attr(rankdir='TB', size='12,12', bgcolor='#FDFEFE', nodesep='1.0', ranksep='1.2', compound='true')

    # Estilo base para nodos
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded',
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='2.0', margin='0.3,0.2', fontsize='14')

    # Estilo base para aristas
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # ── Librerías externas ────────────────────────────────────────────────────
    dot.node('OpenCV',      'OpenCV\nCaptura fotogramas de la webcam\ny renderiza el esqueleto en pantalla', fillcolor='#AED6F1')
    dot.node('MediaPipe',   'MediaPipe AI\nInferencia topológica:\nextrae 33 nodos corporales 3D\n(BlazePose)', fillcolor='#D5F5E3')
    dot.node('NumPy',       'NumPy\nCálculo de ángulos 3D\nvía álgebra vectorial', fillcolor='#FAD7A1')
    dot.node('CustomTk',    'CustomTkinter\nInterfaz gráfica moderna:\ndashboard, login, popup de nivel', fillcolor='#E8DAEF')
    dot.node('PIL',         'Pillow (PIL)\nConversión de frames OpenCV\na imágenes CTkImage para la GUI', fillcolor='#D7DBDD')

    # ── Subgrafo de la aplicación ─────────────────────────────────────────────
    with dot.subgraph(name='cluster_app') as c:
        c.attr(label='Aplicación TFG', style='dashed,rounded', color='#BDC3C7',
               fontname='Helvetica-Bold', fontsize='16', bgcolor='#F8F9F9', margin='25')

        c.node('Orquestador', 'Orquestador\n(pantalla_principal.py)\nGestión de webcam, nivel y\ncortafuegos de seguridad', fillcolor='#AED6F1')

        c.node('Logica', '10 Módulos de Ejercicio\n(modulo_base.py + subclases)\nFSM · umbrales · feedback\ndetección de errores consecutivos', fillcolor='#E8DAEF')

        c.node('Seguridad', 'Cortafuegos de Seguridad\n≥ 3 errores totales → fin\n≥ 2 errores consecutivos → fin\n≥ 65% recorrido → error parcial', fillcolor='#FADBD8')

        c.node('Objetivo', 'Control de Objetivo\nDinámicos: 10 reps\nIsométricos: 20 / 40 / 60 s\nsegún nivel elegido', fillcolor='#FEF9E7')

        c.node('SQLite', 'Base de Datos\n(SQLite / database.py)\nHistorial clínico por paciente\n+ exportación de informes .txt', shape='cylinder', fillcolor='#D7DBDD')

        # Relaciones internas
        c.edge('Orquestador', 'Logica',     label=' Evalúa postura por frame')
        c.edge('Logica',      'Seguridad',  label=' Actualiza errores')
        c.edge('Logica',      'Objetivo',   label=' Verifica objetivo')
        c.edge('Seguridad',   'Orquestador',label=' Dispara fin de serie')
        c.edge('Objetivo',    'Orquestador',label=' Dispara fin de serie')
        c.edge('Logica',      'SQLite',     label=' Al finalizar: exporta métricas')

    # ── Relaciones externas ───────────────────────────────────────────────────
    dot.edge('OpenCV',     'MediaPipe',    label=' 1. Envía frame convertido a RGB')
    dot.edge('MediaPipe',  'NumPy',        label=' 2. Devuelve 33 landmarks 3D')
    dot.edge('NumPy',      'Logica',       label=' 3. Transforma a ángulos biométricos')
    dot.edge('Logica',     'OpenCV',       label=' 4. Dibuja alertas, barra y esqueleto')
    dot.edge('OpenCV',     'PIL',          label=' 5. Convierte frame a imagen')
    dot.edge('PIL',        'Orquestador',  label=' 6. Actualiza canvas de la GUI')
    dot.edge('CustomTk',   'Orquestador',  label=' UI: eventos del usuario\n(login, nivel, inicio/fin)')

    # Renderizar
    ruta_salida = dot.render('esquema_relacion_librerias', cleanup=True, view=False)
    print(f"Esquema generado correctamente y guardado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema_librerias()
