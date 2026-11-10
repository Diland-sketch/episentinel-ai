import numpy as np
import pandas as pd

from episentinel.data.synthetic import make_panel
from episentinel.detection.alertas import (
    alertas_sarima_un_paso, ears_c2, tabla_alertas, semaforo,
)

SIN_ESTACIONAL = dict(order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))


def _serie(n_anios=6, seed=3, pico=None):
    panel = make_panel(n_municipios=3, start_year=2015, end_year=2015 + n_anios - 1, seed=seed, n_outbreaks=0)
    s = panel.iloc[0].astype(float).copy()
    if pico is not None:
        s.iloc[pico] = s.iloc[pico] * 6 + 80
    return s


def test_sarima_un_paso_forma_y_columnas():
    s = _serie()
    t = alertas_sarima_un_paso(s, train_end=int(len(s) * 0.7), **SIN_ESTACIONAL)
    assert list(t.columns) == ["obs", "yhat", "lo", "hi", "alerta_sarima"]
    assert len(t) == len(s) - int(len(s) * 0.7) - 1
    assert (t["lo"] <= t["hi"]).all() and (t[["yhat", "lo", "hi"]] >= 0).all().all()
    assert t.index.equals(s.index[int(len(s) * 0.7) + 1 :])


def test_sarima_un_paso_detecta_un_pico_inyectado():
    base = _serie()
    pos = int(len(base) * 0.85)
    t = alertas_sarima_un_paso(_serie(pico=pos), train_end=int(len(base) * 0.7), **SIN_ESTACIONAL)
    assert bool(t.loc[base.index[pos], "alerta_sarima"])


def test_sarima_un_paso_no_alerta_en_exceso_sin_pico():
    s = _serie()
    t = alertas_sarima_un_paso(s, train_end=int(len(s) * 0.7), **SIN_ESTACIONAL)
    assert t["alerta_sarima"].mean() < 0.15


def test_ears_detecta_salto_brusco():
    x = pd.Series(np.r_[np.full(20, 10.0), 60.0, np.full(5, 10.0)], index=pd.date_range("2020-01-01", periods=26, freq="7D"))
    e = ears_c2(x)
    assert bool(e["alerta_ears"].iloc[20])
    assert e["alerta_ears"].sum() == 1


def test_semaforo_niveles():
    df = pd.DataFrame({
        "alerta_sarima": [False, True, True],
        "alerta_ears": [False, False, True],
        "alerta_canal": [False, False, False],
    })
    assert list(semaforo(df)) == ["verde", "amarillo", "rojo"]


def test_tabla_alertas_une_las_tres_reglas():
    s = _serie(n_anios=7)
    t = tabla_alertas(s, train_end=52 * 5 - 1, order=(1, 0, 0), seasonal_order=(0, 0, 0, 0))
    for c in ["alerta_sarima", "alerta_ears", "alerta_canal", "zona", "nivel"]:
        assert c in t.columns
    assert set(t["nivel"].unique()) <= {"verde", "amarillo", "rojo"}