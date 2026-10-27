"""SARIMA (tarea C1): ajuste y pronostico sobre conteos semanales.

Se modela log1p(casos), no el conteo crudo: el EDA real encontro
sobredispersion fuerte (varianza >> media) en casi todos los municipios
(ver docs/DECISIONES_TECNICAS.md). Esta transformacion es provisional; si
se decide cambiar a una binomial negativa, documentarlo ahi como propuesta
antes de reemplazarla.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


def ajustar_sarima(
    train: pd.Series,
    order: tuple[int, int, int] = (1, 1, 1),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 52),
):
    """Ajusta SARIMA sobre log1p(train). Devuelve el resultado ajustado
    (statsmodels SARIMAXResultsWrapper)."""
    y = np.log1p(train.astype(float))
    modelo = SARIMAX(
        y, order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    return modelo.fit(disp=False)


def pronosticar(resultado, pasos: int, fechas: pd.DatetimeIndex, alpha: float = 0.05) -> pd.DataFrame:
    """Pronostico de `pasos` semanas, invertido a la escala original."""
    pred = resultado.get_forecast(steps=pasos)
    media = pred.predicted_mean
    ic = pred.conf_int(alpha=alpha)
    return pd.DataFrame({
        "yhat": np.expm1(media.values).clip(min=0),
        "lo": np.expm1(ic.iloc[:, 0].values).clip(min=0),
        "hi": np.expm1(ic.iloc[:, 1].values).clip(min=0),
    }, index=fechas[:pasos])


def medir_tiempo_ajuste(
    serie: pd.Series,
    order: tuple[int, int, int] = (1, 1, 1),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 52),
) -> float:
    """Segundos que tarda ajustar_sarima sobre esta serie (insumo de C3,
    para decidir cuantos municipios se pueden modelar en el tiempo disponible)."""
    t0 = time.perf_counter()
    ajustar_sarima(serie, order=order, seasonal_order=seasonal_order)
    return time.perf_counter() - t0