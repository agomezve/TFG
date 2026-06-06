import os
from graphviz import Digraph

def generar_esquema_capas():
    dot = Digraph(format='png')
    dot.attr(rankdir='TB', size='10,14', bgcolor='#FDFEFE', nodesep='0.8', ranksep='1.0', compound='true')
    dot.attr('node', fontname='Helvetica,Arial,sans-serif', shape='box', style='filled,rounded',
             fontcolor='#2C3E50', color='#7F8C8D', penwidth='2.0', margin='0.3,0.2', fontsize='14')
    dot.attr('edge', fontname='Helvetica,Arial,sans-serif', fontsize='12', color='#7F8C8D', penwidth='1.5')

    # ── Capa de Presentación (Frontend / Cliente) ──────────────────────────────
    with dot.subgraph(name='cluster_frontend') as c:
        c.attr(label='Capa de Presentación', style='dashed,rounded', color='#3498DB',
               fontname='Helvetica-Bold', fontsize='16', bgcolor='#EBF5FB', margin='20')
        c.node('GUI',  'Interfaz Gráfica\nMenús, Botones y Dashboard\n(CustomTkinter)', fillcolor='#AED6F1')
        c.node('View', 'Renderizado Visual\nSuperposición de esqueleto,\nmétrica y barra de progreso', fillcolor='#AED6F1')
        c.node('Nivel','Selector de Nivel\n(Principiante / Intermedio / Avanzado)', fillcolor='#D6EAF8')

    # ── Capa de Lógica de Negocio (Backend / Motor) ────────────────────────────
    with dot.subgraph(name='cluster_backend') as c:
        c.attr(label='Capa de Lógica de Negocio', style='dashed,rounded', color='#27AE60',
               fontname='Helvetica-Bold', fontsize='16', bgcolor='#EAFAF1', margin='20')
        c.node('Motor',    'Orquestador Principal\n(pantalla_principal.py)', fillcolor='#A9DFBF')
        c.node('AI',       'Motor Biomecánico\nExtracción espacial y trigonometría 3D\n(MediaPipe + NumPy)', fillcolor='#A9DFBF')
        c.node('Modulos',  '10 Módulos de Ejercicio\n(sentadilla, peso muerto, press militar,\npress banca, plancha, propiocepción,\nhombros, hip thrust, zancadas, búlgaras)', fillcolor='#A9DFBF')
        c.node('FSM',      'Máquina de Estados por Ejercicio\n(DE PIE → BAJANDO → SUBIENDO → ARRIBA)\nFases: inicio · repetición · finalización', fillcolor='#D5F5E7')
        c.node('Seguridad','Cortafuegos de Seguridad\n• 3 errores totales → fin de serie\n• 2 errores consecutivos → fin de serie\n• Umbral rep. incompleta: ≥ 65 %', fillcolor='#FADBD8')
        c.node('Objetivo', 'Control de Objetivo\n• Ejercicios dinámicos: 10 repeticiones\n• Isométricos: 20 s / 40 s / 60 s\n  según nivel (princ. / inter. / avanz.)', fillcolor='#FEF9E7')

    # ── Capa de Datos ──────────────────────────────────────────────────────────
    with dot.subgraph(name='cluster_datos') as c:
        c.attr(label='Capa de Datos', style='dashed,rounded', color='#E67E22',
               fontname='Helvetica-Bold', fontsize='16', bgcolor='#FEF5E7', margin='20')
        c.node('DB',     'Gestor de Base de Datos\nPersistencia de historiales clínicos\n(SQLite / database.py)',
               shape='cylinder', fillcolor='#F5CBA7')
        c.node('Export', 'Sistema de Exportación\nInformes .txt con métricas:\n• Profundidad media · Errores\n• Velocidad de ejecución (s/rep)',
               shape='note', fillcolor='#F5CBA7')

    # ── Relaciones ─────────────────────────────────────────────────────────────
    # Frontend → Backend
    dot.edge('GUI',    'Nivel',  label=' Selección de nivel')
    dot.edge('Nivel',  'Motor',  label=' Parámetro de nivel')
    dot.edge('GUI',    'Motor',  label=' Peticiones del usuario')
    dot.edge('Motor',  'AI',     label=' Envía Frame RGB')

    # Motor biomecánico → Módulos → FSM
    dot.edge('AI',      'Modulos',   label=' Envía Ángulos 3D')
    dot.edge('Modulos', 'FSM',       label=' Ejecuta evaluación')
    dot.edge('FSM',     'Seguridad', label=' Actualiza contadores')
    dot.edge('FSM',     'Objetivo',  label=' Verifica objetivo')

    # Backend → Frontend
    dot.edge('Modulos',   'Motor', label=' Devuelve Diagnóstico + feedback')
    dot.edge('Motor',     'View',  label=' Ordena actualizar interfaz')
    dot.edge('Seguridad', 'Motor', label=' Dispara fin de serie\n(si cortafuegos activo)')
    dot.edge('Objetivo',  'Motor', label=' Dispara fin de serie\n(si objetivo alcanzado)')

    # Backend → Datos
    dot.edge('Modulos', 'DB',     label=' Al finalizar: guarda estadísticas')
    dot.edge('DB',      'Export', label=' Extrae y escribe ficheros .txt')

    # Datos → Frontend
    dot.edge('DB', 'GUI', label=' Retorna historial para Dashboard')

    ruta_salida = dot.render('esquema_arquitectura_capas', cleanup=True, view=False)
    print(f"Esquema de capas generado en: {os.path.abspath(ruta_salida)}")

if __name__ == "__main__":
    generar_esquema_capas()
