import numpy as np
import pandas as pd
import pytest

from episentinel.models.sarima import ajustar_sarima, pronosticar, medir_tiempo_ajuste


def _serie_corta(n_semanas=120, seed=0):
    fechas = pd.date_range("2019-01-01", periods=n_semanas, freq="7D")
    rng = np.random.default_rng(seed)
    base = 8 + 3 * np.sin(2 * np.pi * (np.arange(n_semanas) % 52) / 52)
    casos = rng.poisson(np.clip(base, 1, None))
    return pd.Series(casos.astype(float), index=fechas)


def test_ajustar_sarima_no_estacional_converge():
    serie = _serie_corta()
    resultado = ajustar_sarima(serie, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))
    assert np.isfinite(resultado.llf)


def test_pronosticar_shape_y_orden_de_bandas():
    serie = _serie_corta()
    resultado = ajustar_sarima(serie, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))
    fechas_futuras = pd.date_range(serie.index[-1] + pd.Timedelta(days=7), periods=8, freq="7D")
    pron = pronosticar(resultado, pasos=8, fechas=fechas_futuras)
    assert pron.shape == (8, 3)
    assert (pron["lo"] <= pron["yhat"]).all()
    assert (pron["yhat"] <= pron["hi"]).all()
    assert (pron >= 0).values.all()


def test_medir_tiempo_ajuste_devuelve_positivo():
    serie = _serie_corta(n_semanas=80)
    segundos = medir_tiempo_ajuste(serie, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))
    assert segundos > 0