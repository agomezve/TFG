"""Informe PDF de evolución de un paciente, para el fisio o para adjuntar a la historia clínica.

Se genera con matplotlib (PdfPages), que ya es dependencia del proyecto: sin librerías nuevas.
Páginas: resumen (indicadores, plan y avisos) · evolución por ejercicio · listado de series.
"""
import datetime
import io
import textwrap

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

A4 = (8.27, 11.69)
AZUL = "#1E6FD9"
VERDE = "#1F9D55"
ROJO = "#D64545"
AMARILLO = "#C99A06"
GRIS = "#5B6472"
CLARO = "#EEF2F7"


def _pagina():
    fig = Figure(figsize=A4)
    fig.patch.set_facecolor("white")
    return fig


def _cabecera(fig, titulo, subtitulo, pie):
    fig.text(0.07, 0.955, "TeleRehab IA", fontsize=10, color=AZUL, weight="bold")
    fig.text(0.93, 0.955, pie, fontsize=8, color=GRIS, ha="right")
    fig.text(0.07, 0.915, titulo, fontsize=18, weight="bold")
    fig.text(0.07, 0.89, subtitulo, fontsize=9.5, color=GRIS)
    fig.add_artist(_linea(fig, 0.875))


def _linea(fig, y):
    from matplotlib.lines import Line2D
    return Line2D([0.07, 0.93], [y, y], color="#D5DBE3", linewidth=0.8, transform=fig.transFigure)


def _pie(fig, n, total):
    fig.text(0.5, 0.025, f"Página {n} de {total} · Informe generado automáticamente a partir del análisis por "
             "visión artificial. No sustituye la valoración clínica del fisioterapeuta.",
             fontsize=7, color=GRIS, ha="center")


def _kpi(fig, x, y, valor, etiqueta, color=AZUL):
    from matplotlib.patches import FancyBboxPatch
    fig.add_artist(FancyBboxPatch((x, y), 0.2, 0.075, boxstyle="round,pad=0,rounding_size=0.01",
                                  transform=fig.transFigure, facecolor=CLARO, edgecolor="none"))
    fig.text(x + 0.1, y + 0.04, valor, fontsize=17, weight="bold", color=color, ha="center")
    fig.text(x + 0.1, y + 0.014, etiqueta, fontsize=7.5, color=GRIS, ha="center")


NOMBRES = {"Propiocepcion": "Propiocepción", "Bulgaras": "Búlgaras"}


def _nombre(ejercicio):
    return NOMBRES.get(ejercicio, ejercicio)


def _texto(v, sufijo=""):
    return "—" if v is None else f"{v}{sufijo}".replace(".", ",")


def _grafica_ejercicio(ax, sesiones, ejercicio):
    por_dia = {}
    for s in sesiones:
        d = por_dia.setdefault(s["fecha"][:10], [0, 0])
        d[0] += s["repeticiones"]
        d[1] += min(s["errores"], s["repeticiones"])
    dias = sorted(por_dia)
    x = list(range(len(dias)))
    correctas = [por_dia[d][0] - por_dia[d][1] for d in dias]
    errores = [por_dia[d][1] for d in dias]
    pct = [100 * c / (c + e) if c + e else 0 for c, e in zip(correctas, errores)]
    ax.bar(x, correctas, color=VERDE, label="Correctas")
    ax.bar(x, errores, bottom=correctas, color=ROJO, label="Con error")
    paso = max(1, len(dias) // 10)
    ax.set_xticks(x[::paso])
    ax.set_xticklabels([f"{d[8:10]}/{d[5:7]}" for d in dias][::paso], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    unidad = "segundos" if ejercicio in ("Plancha", "Propiocepcion") else "repeticiones"
    ax.set_ylabel(unidad, fontsize=8, color=GRIS)
    ax.set_title(_nombre(ejercicio), fontsize=10.5, loc="left", weight="bold")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax2 = ax.twinx()
    ax2.plot(x, pct, color=AMARILLO, marker="o", markersize=3, linewidth=1.5, label="% correcto")
    ax2.set_ylim(0, 105)
    ax2.tick_params(axis="y", labelsize=7, colors=AMARILLO)
    ax2.spines["top"].set_visible(False)
    if dias:
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=6.5, loc="upper left", frameon=False, ncol=3)


def generar_informe(paciente, clinica, historial, plan_hoy, adherencia, metricas):
    """Devuelve los bytes del PDF.

    paciente: {nombre, edad}; historial: lista de sesiones (más reciente primero);
    plan_hoy: salida de plan_de_hoy(); adherencia: salida de resumen_adherencia();
    metricas: salida de metricas_paciente().
    """
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    pie = f"{clinica} · {hoy}"
    cronologico = list(reversed(historial))
    ejercicios = sorted({s["ejercicio"] for s in historial}, key=lambda e: -sum(1 for s in historial if s["ejercicio"] == e))
    paginas = []

    # ── Página 1: resumen ──
    fig = _pagina()
    edad = f" · {paciente['edad']} años" if paciente.get("edad") else ""
    periodo = (f"Desde el {datetime.date.fromisoformat(metricas['primera']).strftime('%d/%m/%Y')} "
               f"hasta el {datetime.date.fromisoformat(metricas['ultima']).strftime('%d/%m/%Y')}"
               if metricas["primera"] else "Todavía no ha hecho ninguna serie")
    _cabecera(fig, f"Informe de evolución: {paciente['nombre']}", f"Paciente{edad} · {periodo}", pie)
    adh = adherencia.get("adherencia")
    color_adh = VERDE if adh is not None and adh >= 80 else AMARILLO if adh is not None and adh >= 50 else ROJO
    _kpi(fig, 0.07, 0.775, _texto(adh, " %"), "Adherencia (últimos 7 días)", color_adh)
    _kpi(fig, 0.29, 0.775, str(metricas["series"]), "Series realizadas")
    _kpi(fig, 0.51, 0.775, _texto(metricas["dias_por_semana"]), "Días de entreno por semana")
    mejora = metricas["mejora"]
    _kpi(fig, 0.73, 0.775, "—" if mejora is None else f"{mejora:+d} pts",
         "Técnica: 1.ª semana → última", VERDE if (mejora or 0) > 0 else ROJO if (mejora or 0) < 0 else AZUL)
    if metricas["correcto_inicio"] is not None:
        fig.text(0.07, 0.75, f"Ejecución correcta: {metricas['correcto_inicio']} % en la primera semana de uso y "
                 f"{metricas['correcto_final']} % en la última.", fontsize=8.5, color=GRIS)

    y = 0.70
    fig.text(0.07, y, "Plan prescrito", fontsize=12, weight="bold")
    y -= 0.03
    if plan_hoy:
        for txt, x in (("Ejercicio", 0.07), ("Nivel", 0.36), ("Pauta", 0.53), ("Esta semana", 0.75)):
            fig.text(x, y, txt, fontsize=8, color=GRIS, weight="bold")
        for item in plan_hoy:
            y -= 0.026
            fig.text(0.07, y, _nombre(item["ejercicio"]), fontsize=9.5)
            fig.text(0.36, y, item["nivel"].capitalize(), fontsize=9.5)
            fig.text(0.53, y, f"{item['series']} series × {item['dias_semana']} días/sem", fontsize=9.5)
            fig.text(0.75, y, f"{item['hechas_semana']} de {item['objetivo_semana']} series", fontsize=9.5,
                     color=VERDE if item["hechas_semana"] >= item["objetivo_semana"] else GRIS)
    else:
        y -= 0.01
        fig.text(0.07, y, "No tiene plan asignado.", fontsize=9.5, color=GRIS)

    y -= 0.06
    fig.text(0.07, y, "Avisos", fontsize=12, weight="bold")
    alertas = adherencia.get("alertas") or []
    if not alertas:
        y -= 0.03
        fig.text(0.07, y, "Sin avisos: el paciente sigue el plan con normalidad.", fontsize=9.5, color=VERDE)
    colores = {"alta": ROJO, "media": AMARILLO, "info": GRIS}
    for a in alertas:
        for i, linea in enumerate(textwrap.wrap(a["texto"], 95)):
            y -= 0.024
            fig.text(0.07, y, ("●  " if i == 0 else "    ") + linea, fontsize=9.5, color=colores.get(a["gravedad"], GRIS))

    y -= 0.06
    fig.text(0.07, y, "Resumen por ejercicio", fontsize=12, weight="bold")
    y -= 0.03
    for txt, x in (("Ejercicio", 0.07), ("Series", 0.36), ("Total", 0.48), ("% correcto", 0.63), ("Última", 0.78)):
        fig.text(x, y, txt, fontsize=8, color=GRIS, weight="bold")
    for ej in ejercicios[:12]:
        ses = [s for s in historial if s["ejercicio"] == ej]
        reps = sum(s["repeticiones"] for s in ses)
        err = sum(min(s["errores"], s["repeticiones"]) for s in ses)
        y -= 0.024
        fig.text(0.07, y, _nombre(ej), fontsize=9.5)
        fig.text(0.36, y, str(len(ses)), fontsize=9.5)
        fig.text(0.48, y, f"{reps} {'s' if ej in ('Plancha', 'Propiocepcion') else 'reps'}", fontsize=9.5)
        fig.text(0.63, y, f"{round(100 * (reps - err) / reps) if reps else 0} %", fontsize=9.5)
        fig.text(0.78, y, datetime.date.fromisoformat(ses[0]["fecha"][:10]).strftime("%d/%m/%Y"), fontsize=9.5)
    paginas.append(fig)

    # ── Evolución por ejercicio: 3 gráficas por página ──
    for i in range(0, len(ejercicios), 3):
        fig = _pagina()
        _cabecera(fig, "Evolución por ejercicio", "Total diario de cada ejercicio: parte correcta (verde), "
                  "con error (rojo) y % de ejecución correcta (línea).", pie)
        for j, ej in enumerate(ejercicios[i:i + 3]):
            ax = fig.add_axes([0.1, 0.62 - j * 0.27, 0.78, 0.2])
            _grafica_ejercicio(ax, [s for s in cronologico if s["ejercicio"] == ej], ej)
        paginas.append(fig)

    # ── Listado de series (las 40 últimas por página) ──
    for i in range(0, max(len(historial), 1), 40):
        fig = _pagina()
        _cabecera(fig, "Detalle de series", f"{len(historial)} series en total, de la más reciente a la más antigua.", pie)
        y = 0.845
        for txt, x in (("Fecha", 0.07), ("Ejercicio", 0.27), ("Nivel", 0.47), ("Total", 0.62), ("Errores", 0.72), ("Observaciones", 0.82)):
            fig.text(x, y, txt, fontsize=8, color=GRIS, weight="bold")
        for s in historial[i:i + 40]:
            y -= 0.019
            fig.text(0.07, y, s["fecha"][:16], fontsize=8)
            fig.text(0.27, y, _nombre(s["ejercicio"]), fontsize=8)
            fig.text(0.47, y, (s["nivel"] or "").capitalize(), fontsize=8)
            fig.text(0.62, y, str(s["repeticiones"]), fontsize=8)
            fig.text(0.72, y, str(s["errores"]), fontsize=8, color=ROJO if s["errores"] else "black")
            fig.text(0.82, y, (s.get("observaciones") or "")[:22], fontsize=7, color=GRIS)
        if not historial:
            fig.text(0.07, y - 0.03, "Sin series registradas.", fontsize=9.5, color=GRIS)
        paginas.append(fig)

    buffer = io.BytesIO()
    with PdfPages(buffer, metadata={"Title": f"Informe de evolución - {paciente['nombre']}", "Creator": "TeleRehab IA"}) as pdf:
        for n, fig in enumerate(paginas, 1):
            _pie(fig, n, len(paginas))
            pdf.savefig(fig)
    return buffer.getvalue()
