"""Baseline ingenua estacional (tarea B2): pronostica cada semana futura
igual al valor observado hace exactamente m semanas (misma semana, anio
anterior). Es el piso minimo que SARIMA debe superar para justificarse.
"""
from __future__ import annotations
import pandas as pd


def pronosticar_ingenua_estacional(train: pd.Series, pasos: int, m: int = 52) -> pd.Series:
    if len(train) < m:
        raise ValueError(f"La serie de entrenamiento necesita al menos {m} semanas")
    valores = train.values
    pron = [valores[-m + (i % m)] for i in range(pasos)]
    fechas = pd.date_range(train.index[-1] + pd.Timedelta(days=7), periods=pasos, freq="7D")
    return pd.Series(pron, index=fechas, name="yhat")

def pronosticar_ultimo_valor(train: pd.Series, pasos: int) -> pd.Series:
    """Baseline de ultimo valor (random walk): todas las semanas futuras
    repiten el ultimo valor observado. Es un piso exigente en series con
    ciclos epidemicos largos y estacionalidad anual debil."""
    fechas = pd.date_range(train.index[-1] + pd.Timedelta(days=7), periods=pasos, freq="7D")
    return pd.Series([train.values[-1]] * pasos, index=fechas, name="yhat")