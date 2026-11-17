"""Adherencia al plan y alertas para el fisioterapeuta.

Funciones puras (sin BBDD ni red) para poder probarlas fácilmente:
  - plan_de_hoy(plan, historial, hoy)    -> qué le toca hoy al paciente y cuánto lleva
  - resumen_adherencia(plan, historial, hoy) -> % de cumplimiento de los últimos 7 días + alertas

`historial` es una lista de dicts con al menos "fecha" ("AAAA-MM-DD HH:MM:SS"), "ejercicio" y "errores".
`plan` es una lista de dicts {ejercicio, nivel, series, dias_semana}.
"""
import datetime

DIAS_SIN_ENTRENAR_ALERTA = 3      # días sin ninguna serie a partir de los que se avisa
ADHERENCIA_BAJA = 50              # % de cumplimiento semanal por debajo del que se avisa
ERRORES_SERIE_DIFICIL = 2         # una serie con >= estos errores cuenta como "con dificultad"


def _dia(fecha_txt):
    return datetime.date.fromisoformat(fecha_txt[:10])


def plan_de_hoy(plan, historial, hoy=None):
    """Para cada ejercicio del plan: series hechas hoy y esta semana frente a lo recetado."""
    hoy = hoy or datetime.date.today()
    hace7 = hoy - datetime.timedelta(days=6)
    resultado = []
    for item in plan:
        del_ej = [s for s in historial if s["ejercicio"] == item["ejercicio"]]
        hoy_n = sum(1 for s in del_ej if _dia(s["fecha"]) == hoy)
        semana_n = sum(1 for s in del_ej if hace7 <= _dia(s["fecha"]) <= hoy)
        objetivo_semana = item["series"] * item["dias_semana"]
        resultado.append({**item, "hechas_hoy": hoy_n, "hechas_semana": semana_n,
                          "objetivo_semana": objetivo_semana,
                          "completado_hoy": hoy_n >= item["series"]})
    return resultado


def resumen_adherencia(plan, historial, hoy=None):
    """Devuelve {adherencia, dias_sin_entrenar, ultima, alertas:[{tipo, texto, gravedad}]}.

    adherencia: % de las series recetadas en los últimos 7 días que se han hecho (máx. 100), o None sin plan.
    """
    hoy = hoy or datetime.date.today()
    fechas = sorted((_dia(s["fecha"]) for s in historial), reverse=True)
    ultima = fechas[0] if fechas else None
    dias_sin = (hoy - ultima).days if ultima else None

    adherencia = None
    if plan:
        detalle = plan_de_hoy(plan, historial, hoy)
        objetivo = sum(d["objetivo_semana"] for d in detalle)
        hechas = sum(min(d["hechas_semana"], d["objetivo_semana"]) for d in detalle)
        adherencia = round(100 * hechas / objetivo) if objetivo else None

    alertas = []
    if not plan:
        alertas.append({"tipo": "sin_plan", "gravedad": "info", "texto": "Sin plan de ejercicios asignado"})
    if ultima is None:
        alertas.append({"tipo": "sin_sesiones", "gravedad": "media", "texto": "Todavía no ha hecho ninguna serie"})
    elif dias_sin >= DIAS_SIN_ENTRENAR_ALERTA:
        alertas.append({"tipo": "inactivo", "gravedad": "alta" if dias_sin >= 7 else "media",
                        "texto": f"Lleva {dias_sin} días sin entrenar"})
    if adherencia is not None and adherencia < ADHERENCIA_BAJA and ultima is not None:
        alertas.append({"tipo": "adherencia_baja", "gravedad": "media",
                        "texto": f"Solo ha cumplido el {adherencia}% del plan esta semana"})

    # Dificultad técnica: 2 de sus 3 últimas series de un ejercicio con muchos errores
    por_ejercicio = {}
    for s in sorted(historial, key=lambda s: s["fecha"], reverse=True):
        por_ejercicio.setdefault(s["ejercicio"], []).append(s)
    for ejercicio, series in por_ejercicio.items():
        ultimas = series[:3]
        dificiles = sum(1 for s in ultimas if (s.get("errores") or 0) >= ERRORES_SERIE_DIFICIL)
        if len(ultimas) >= 2 and dificiles >= 2 and ultima and (hoy - _dia(ultimas[0]["fecha"])).days <= 14:
            alertas.append({"tipo": "tecnica", "gravedad": "alta",
                            "texto": f"Dificultad en {ejercicio}: {dificiles} de sus últimas {len(ultimas)} series con errores",
                            "ejercicio": ejercicio})

    orden = {"alta": 0, "media": 1, "info": 2}
    alertas.sort(key=lambda a: orden[a["gravedad"]])
    return {"adherencia": adherencia, "dias_sin_entrenar": dias_sin,
            "ultima": ultima.isoformat() if ultima else None, "alertas": alertas}
