import numpy as np
import pandas as pd
import pytest

from episentinel.baselines.canal_endemico import construir_canal, clasificar


def _serie_sintetica(anios=(2018, 2019, 2020, 2021), pico_en_2021=True):
    fechas = pd.date_range(f"{anios[0]}-01-01", periods=len(anios) * 52, freq="7D")
    rng = np.random.default_rng(0)
    base = 10 + 3 * np.sin(2 * np.pi * (np.arange(len(fechas)) % 52) / 52)
    casos = rng.poisson(np.clip(base, 1, None))
    if pico_en_2021:
        casos[-52:][20:28] = casos[-52:][20:28] * 8 + 50  # brote en semanas 21-28 del ultimo anio
    return pd.Series(casos, index=fechas)


def test_construir_canal_shape_y_monotonia():
    serie = _serie_sintetica()
    canal = construir_canal(serie, anio_actual=2021, anios_referencia=5)
    assert list(canal.index) == list(range(1, 53))
    valid = canal.dropna()
    assert (valid["p10"] <= valid["p25"]).all()
    assert (valid["p25"] <= valid["mediana"]).all()
    assert (valid["mediana"] <= valid["p75"]).all()
    assert (valid["p75"] <= valid["p90"]).all()


def test_n_anios_correcto():
    serie = _serie_sintetica()
    canal = construir_canal(serie, anio_actual=2021, anios_referencia=5)
    assert (canal.dropna()["n_anios"] == 3).all()


def test_semanas_sin_historico_quedan_nan():
    serie = _serie_sintetica(anios=(2020, 2021), pico_en_2021=False)
    canal = construir_canal(serie, anio_actual=2021, anios_referencia=5, min_anios=2)
    assert canal["p10"].isna().all()


def test_clasificar_detecta_el_brote_inyectado():
    serie = _serie_sintetica(pico_en_2021=True)
    canal = construir_canal(serie, anio_actual=2021, anios_referencia=5)
    clasif = clasificar(serie, canal, anio_actual=2021)
    assert len(clasif) == 52
    semanas_brote = clasif[(clasif["semana"] >= 21) & (clasif["semana"] <= 28)]
    assert (semanas_brote["zona"] == "epidemia").mean() > 0.5


def test_clasificar_sin_brote_mayoria_no_epidemia():
    serie = _serie_sintetica(pico_en_2021=False)
    canal = construir_canal(serie, anio_actual=2021, anios_referencia=5)
    clasif = clasificar(serie, canal, anio_actual=2021)
    assert (clasif["zona"] == "epidemia").mean() < 0.3


def test_zonas_validas():
    serie = _serie_sintetica()
    canal = construir_canal(serie, anio_actual=2021)
    clasif = clasificar(serie, canal, anio_actual=2021)
    assert set(clasif["zona"].unique()) <= {"exito", "seguridad", "alerta", "epidemia", "sin_datos"}