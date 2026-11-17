"""Gráficas de progreso del paciente (se usan en el panel del fisioterapeuta)."""
from matplotlib.figure import Figure

COLOR_FONDO = "#2B2B2B"
COLOR_OK = "#2ECC71"
COLOR_ERROR = "#E74C3C"
EJERCICIOS_POR_TIEMPO = ("plancha", "propiocepcion")


def figura_progreso(historial, ejercicio, tamano=(9, 4)):
    """Barras apiladas por día de entrenamiento (suma de todas las series del día):
    parte correcta en verde y con error en rojo, más la línea de % de ejecución correcta.

    `historial` son filas de obtener_historial_paciente() en orden cronológico:
    (fecha, ejercicio, nivel, repeticiones, errores, profundidad_media, observaciones)
    """
    por_dia = {}
    for s in historial:
        if s[1] != ejercicio:
            continue
        dia = por_dia.setdefault(s[0][:10], [0, 0])
        dia[0] += int(s[3] or 0)
        dia[1] += int(s[4] or 0)
    dias = sorted(por_dia)
    reps = [por_dia[d][0] for d in dias]
    errores = [min(por_dia[d][1], por_dia[d][0]) for d in dias]
    correctas = [r - e for r, e in zip(reps, errores)]
    porcentaje = [100.0 * c / r if r else 0.0 for c, r in zip(correctas, reps)]
    etiquetas = [f"{d[8:10]}/{d[5:7]}" for d in dias]
    unidad = "segundos" if ejercicio.lower() in EJERCICIOS_POR_TIEMPO else "repeticiones"

    fig = Figure(figsize=tamano, dpi=100, facecolor=COLOR_FONDO)
    ax = fig.add_subplot(111)
    ax.set_facecolor(COLOR_FONDO)
    x = list(range(len(dias)))
    ax.bar(x, correctas, color=COLOR_OK, label="Correctas")
    ax.bar(x, errores, bottom=correctas, color=COLOR_ERROR, label="Con error")
    max_etiquetas = 15 if tamano[0] >= 9 else 8  # menos fechas en el eje si la gráfica es estrecha (móvil)
    paso = max(1, len(dias) // max_etiquetas)
    ax.set_xticks(x[::paso])
    ax.set_xticklabels(etiquetas[::paso], rotation=45, ha="right")
    ax.set_xlabel("Día de entrenamiento", color="white")
    ax.set_ylabel(f"{unidad} (total del día)", color="white")
    ax.set_title(f"{ejercicio}: evolución diaria", color="white")
    ax.tick_params(colors="white")
    for borde in ax.spines.values():
        borde.set_color("#666666")

    ax2 = ax.twinx()
    ax2.plot(x, porcentaje, color="#F1C40F", marker="o", linewidth=2, label="% correcto")
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("% ejecución correcta", color="#F1C40F")
    ax2.tick_params(colors="#F1C40F")
    for borde in ax2.spines.values():
        borde.set_color("#666666")

    lineas = ax.get_legend_handles_labels()
    lineas2 = ax2.get_legend_handles_labels()
    ax.legend(lineas[0] + lineas2[0], lineas[1] + lineas2[1], loc="lower left",
              facecolor="#333333", labelcolor="white", edgecolor="#666666")
    fig.tight_layout()
    return fig
