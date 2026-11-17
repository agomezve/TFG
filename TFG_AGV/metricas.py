"""Métricas del piloto: cómo evoluciona cada paciente y la clínica en conjunto (funciones puras).

Sirven para enseñar resultados a una clínica o a un jurado: cuántos pacientes entrenan,
cuánto cumplen el plan y si mejora su técnica desde la primera semana hasta la última.

`historial` son dicts {fecha, ejercicio, repeticiones, errores, ...} como los de la API.
"""
import datetime

from adherencia import resumen_adherencia


def _dia(fecha):
    return datetime.date.fromisoformat(fecha[:10])


def _pct_correcto(sesiones):
    reps = sum(s["repeticiones"] for s in sesiones)
    errores = sum(min(s["errores"], s["repeticiones"]) for s in sesiones)
    return round(100 * (reps - errores) / reps) if reps else None


def metricas_paciente(plan, historial, hoy=None):
    """Resumen de un paciente desde su primera sesión.

    La técnica se compara entre los 7 primeros días de uso y los 7 últimos; si ha entrenado
    menos de 2 semanas no hay comparación (devuelve None en la mejora).
    """
    hoy = hoy or datetime.date.today()
    resumen = resumen_adherencia(plan, historial, hoy=hoy)
    if not historial:
        return {"series": 0, "dias_activos": 0, "primera": None, "ultima": None, "semanas": 0,
                "dias_por_semana": None, "correcto_inicio": None, "correcto_final": None, "mejora": None,
                "series_7d": 0, "adherencia": resumen["adherencia"]}
    dias = sorted({_dia(s["fecha"]) for s in historial})
    primera, ultima = dias[0], dias[-1]
    semanas = max(1, ((ultima - primera).days + 1 + 6) // 7)
    inicio = [s for s in historial if _dia(s["fecha"]) < primera + datetime.timedelta(days=7)]
    final = [s for s in historial if _dia(s["fecha"]) > ultima - datetime.timedelta(days=7)]
    correcto_inicio, correcto_final = _pct_correcto(inicio), _pct_correcto(final)
    hay_comparacion = (ultima - primera).days >= 13 and correcto_inicio is not None and correcto_final is not None
    return {
        "series": len(historial),
        "dias_activos": len(dias),
        "primera": primera.isoformat(),
        "ultima": ultima.isoformat(),
        "semanas": semanas,
        "dias_por_semana": round(len(dias) / semanas, 1),
        "correcto_inicio": correcto_inicio if hay_comparacion else None,
        "correcto_final": correcto_final if hay_comparacion else None,
        "mejora": (correcto_final - correcto_inicio) if hay_comparacion else None,
        "series_7d": sum(1 for s in historial if (hoy - _dia(s["fecha"])).days < 7),
        "adherencia": resumen["adherencia"],
    }


def _media(valores):
    valores = [v for v in valores if v is not None]
    # Redondeo «de toda la vida» (0,5 hacia arriba), igual que la app: round() de Python redondea al par
    return int(sum(valores) / len(valores) + 0.5) if valores else None


def metricas_clinica(por_paciente):
    """Agrega la lista de metricas_paciente() de todos los pacientes de una clínica."""
    con_sesiones = [m for m in por_paciente if m["series"]]
    con_mejora = [m for m in por_paciente if m["mejora"] is not None]
    return {
        "pacientes": len(por_paciente),
        "pacientes_activos": sum(1 for m in por_paciente if m["series_7d"]),
        "series_totales": sum(m["series"] for m in por_paciente),
        "series_7d": sum(m["series_7d"] for m in por_paciente),
        "adherencia_media": _media(m["adherencia"] for m in por_paciente),
        "dias_por_semana": (round(sum(m["dias_por_semana"] for m in con_sesiones) / len(con_sesiones), 1)
                            if con_sesiones else None),
        "correcto_inicio": _media(m["correcto_inicio"] for m in con_mejora),
        "correcto_final": _media(m["correcto_final"] for m in con_mejora),
        "pacientes_mejoran": sum(1 for m in con_mejora if m["mejora"] > 0),
        "pacientes_comparables": len(con_mejora),
    }
