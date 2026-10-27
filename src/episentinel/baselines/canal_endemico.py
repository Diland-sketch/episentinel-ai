"""Canal endemico (tarea B1).

Construye, para cada semana epidemiologica (1-52), el corredor historico de
casos esperados a partir de anios de referencia, y clasifica cada semana del
anio evaluado en una de 4 zonas: exito, seguridad, alerta, epidemia.

Metodo clasico de franjas sobre percentiles de log(1+x) (el mismo principio
que usa el canal endemico del Boletin Epidemiologico del INS).

Nota sobre anio/semana: NO se usa el calendario ISO. Se deriva de la
posicion dentro de la serie, igual que construir_panel() (52 semanas por
anio, empezando el 1 de enero del primer anio). Usar isocalendar() aqui
daria semanas desalineadas con el resto del pipeline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ZONAS = ["exito", "seguridad", "alerta", "epidemia"]


def _anio_semana(serie: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    y0 = serie.index[0].year
    t = np.arange(len(serie))
    anio = y0 + t // 52
    semana = (t % 52) + 1
    return anio, semana


def construir_canal(
    serie: pd.Series,
    anio_actual: int | None = None,
    anios_referencia: int | None = 5,
    min_anios: int = 2,
) -> pd.DataFrame:
    """Canal endemico por semana epidemiologica (1..52).

    serie: pd.Series con DatetimeIndex semanal (una fila de un panel).
    anio_actual: anio a evaluar (se excluye del historico). Por defecto,
        el ultimo anio presente en la serie.
    anios_referencia: cuantos anios anteriores a anio_actual se usan como
        historico. None = usa todos los disponibles.
    min_anios: semanas con menos anios de historico que esto quedan con
        NaN (no hay base suficiente para una franja confiable).

    Devuelve un DataFrame indexado 1..52 con p10, p25, mediana, p75, p90
    (en la escala original de casos) y n_anios.
    """
    anio, semana = _anio_semana(serie)
    df = pd.DataFrame({"casos": serie.values, "anio": anio, "semana": semana})

    anio_actual = anio_actual or int(df["anio"].max())
    hist = df[df["anio"] < anio_actual]
    if anios_referencia is not None:
        hist = hist[hist["anio"] >= anio_actual - anios_referencia]

    log_casos = np.log1p(hist["casos"])
    g = log_casos.groupby(hist["semana"])
    tabla = pd.DataFrame({
        "p10": g.quantile(.10), "p25": g.quantile(.25),
        "mediana": g.median(), "p75": g.quantile(.75), "p90": g.quantile(.90),
        "n_anios": hist.groupby("semana")["anio"].nunique(),
    })
    for c in ["p10", "p25", "mediana", "p75", "p90"]:
        tabla[c] = np.expm1(tabla[c]).clip(lower=0)
    tabla = tabla.reindex(range(1, 53))
    tabla.loc[tabla["n_anios"] < min_anios, ["p10", "p25", "mediana", "p75", "p90"]] = np.nan
    tabla.index.name = "semana"
    return tabla


def clasificar(serie: pd.Series, canal: pd.DataFrame, anio_actual: int) -> pd.DataFrame:
    """Clasifica cada semana de anio_actual contra un canal ya construido."""
    anio, semana = _anio_semana(serie)
    df = pd.DataFrame({"casos": serie.values, "anio": anio, "semana": semana}, index=serie.index)
    d = df[df["anio"] == anio_actual].join(canal, on="semana")

    cond = [
        d["casos"] <= d["p25"],
        (d["casos"] > d["p25"]) & (d["casos"] <= d["mediana"]),
        (d["casos"] > d["mediana"]) & (d["casos"] <= d["p90"]),
        d["casos"] > d["p90"],
    ]
    d["zona"] = np.select(cond, ZONAS, default="sin_datos")
    d.loc[d[["p10", "p25", "mediana", "p75", "p90"]].isna().any(axis=1), "zona"] = "sin_datos"
    return d[["anio", "semana", "casos", "zona"]]