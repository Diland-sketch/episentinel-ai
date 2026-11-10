"""Deteccion de alertas sobre series semanales de casos (Fase 2, demo).

Tres reglas independientes, todas usando SOLO informacion anterior a la
semana evaluada (podrian correr en tiempo real):

  1. SARIMA un paso adelante: se ajusta con el entrenamiento y sus
     parametros se mantienen fijos mientras se actualiza el estado con cada
     nueva observacion; alerta si el observado supera el limite superior del
     intervalo de prediccion de la semana siguiente.
  2. EARS C2 (CDC): linea base movil de 7 semanas con margen de 2 semanas.
  3. Canal endemico: alerta si el observado supera el percentil 90 de la
     misma semana en los ultimos 5 anios.

IMPORTANTE: no existen etiquetas oficiales de "brote" para validar estas
alertas (ver DECISIONES_TECNICAS, P-02). Son candidatos a anomalia, no
brotes confirmados.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from episentinel.baselines.canal_endemico import clasificar, construir_canal


def alertas_sarima_un_paso(
    serie: pd.Series,
    train_end: int,
    order: tuple[int, int, int] = (1, 1, 1),
    seasonal_order: tuple[int, int, int, int] = (1, 0, 1, 52),
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Prediccion un paso adelante desde train_end+1 hasta el final de la serie.

    Devuelve DataFrame indexado por fecha con: obs, yhat, lo, hi, alerta_sarima.
    Los parametros se estiman SOLO con serie[:train_end+1].
    """
    y = np.log1p(serie.astype(float))
    modelo = SARIMAX(
        y.iloc[: train_end + 1], order=order, seasonal_order=seasonal_order,
        enforce_stationarity=False, enforce_invertibility=False,
    )
    res = modelo.fit(disp=False)
    res_full = res.apply(y, refit=False)
    pred = res_full.get_prediction(start=train_end + 1, end=len(y) - 1, dynamic=False)
    ic = pred.conf_int(alpha=alpha)
    idx = serie.index[train_end + 1 :]
    out = pd.DataFrame({
        "obs": serie.iloc[train_end + 1 :].astype(float).values,
        "yhat": np.expm1(pred.predicted_mean.values).clip(min=0),
        "lo": np.expm1(ic.iloc[:, 0].values).clip(min=0),
        "hi": np.expm1(ic.iloc[:, 1].values).clip(min=0),
    }, index=idx)
    out["alerta_sarima"] = out["obs"] > out["hi"]
    return out


def ears_c2(
    serie: pd.Series, base: int = 7, guard: int = 2, k: float = 3.0,
    min_sd: float = 1.0, min_casos: int = 3,
) -> pd.DataFrame:
    """EARS C2 adaptado a datos semanales. Devuelve z y alerta_ears."""
    ref = serie.astype(float).shift(guard + 1)
    mu = ref.rolling(base).mean()
    sd = ref.rolling(base).std().clip(lower=min_sd)
    z = (serie - mu) / sd
    return pd.DataFrame({"z_ears": z, "alerta_ears": (z > k) & (serie >= min_casos)})


def alertas_canal_endemico(serie: pd.Series, anios: list[int]) -> pd.DataFrame:
    """Zona del canal endemico por semana, para cada anio de `anios`."""
    partes = []
    for a in anios:
        canal = construir_canal(serie, anio_actual=a, anios_referencia=5)
        partes.append(clasificar(serie, canal, anio_actual=a))
    zonas = pd.concat(partes)
    zonas["alerta_canal"] = zonas["zona"] == "epidemia"
    return zonas[["zona", "alerta_canal"]]


def semaforo(df: pd.DataFrame) -> pd.Series:
    """verde (0 reglas), amarillo (1), rojo (2 o mas)."""
    n = df[["alerta_sarima", "alerta_ears", "alerta_canal"]].fillna(False).astype(int).sum(axis=1)
    return pd.cut(n, bins=[-1, 0, 1, 3], labels=["verde", "amarillo", "rojo"]).astype(str)


def tabla_alertas(serie: pd.Series, train_end: int, order=(1, 1, 1), seasonal_order=(1, 0, 1, 52)) -> pd.DataFrame:
    """Une las tres reglas para el periodo posterior a train_end."""
    s = alertas_sarima_un_paso(serie, train_end, order, seasonal_order)
    e = ears_c2(serie).loc[s.index]
    # el canal usa anio por posicion (52 semanas/anio), igual que construir_panel()
    y0 = serie.index[0].year
    pos = np.arange(len(serie))
    anio_pos = pd.Series(y0 + pos // 52, index=serie.index)
    anios_eval = sorted(anio_pos.loc[s.index].unique())
    c = alertas_canal_endemico(serie, anios_eval).loc[s.index]
    out = s.join(e).join(c)
    out["nivel"] = semaforo(out)
    return out