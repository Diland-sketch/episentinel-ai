import numpy as np
import pandas as pd
import pytest

from episentinel.baselines.ingenua_estacional import pronosticar_ingenua_estacional, pronosticar_ultimo_valor


def _serie(n=120):
    return pd.Series(np.arange(n, dtype=float), index=pd.date_range("2019-01-01", periods=n, freq="7D"))


def test_ingenua_estacional_repite_el_valor_de_hace_52_semanas():
    s = _serie()
    p = pronosticar_ingenua_estacional(s, pasos=10)
    np.testing.assert_array_equal(p.values, s.values[-52:-52 + 10])
    assert p.index[0] == s.index[-1] + pd.Timedelta(days=7)


def test_ingenua_estacional_exige_al_menos_un_anio():
    with pytest.raises(ValueError):
        pronosticar_ingenua_estacional(_serie(30), pasos=4)


def test_ultimo_valor_es_plano_y_con_fechas_correctas():
    s = _serie()
    p = pronosticar_ultimo_valor(s, pasos=8)
    assert (p.values == s.values[-1]).all() and len(p) == 8
    assert p.index[0] == s.index[-1] + pd.Timedelta(days=7)