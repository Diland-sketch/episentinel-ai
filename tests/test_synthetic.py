import numpy as np
import pandas as pd
import pytest

from episentinel.data.synthetic import make_panel, panel_nacional


def test_shape_and_index():
    panel = make_panel(n_municipios=10, start_year=2020, end_year=2021, seed=1)
    assert panel.shape == (10, 2 * 52)
    assert panel.index.name == "cod_mun"


def test_cod_mun_es_texto_de_5_digitos():
    panel = make_panel(n_municipios=15, start_year=2020, end_year=2020, seed=1)
    for cod in panel.index:
        assert isinstance(cod, str)
        assert len(cod) == 5
        assert cod.isdigit()


def test_columnas_son_datetimeindex_semanal():
    panel = make_panel(n_municipios=5, start_year=2020, end_year=2021, seed=1)
    assert isinstance(panel.columns, pd.DatetimeIndex)
    deltas = panel.columns.to_series().diff().dropna().unique()
    assert len(deltas) == 1
    assert deltas[0] == pd.Timedelta(days=7)


def test_valores_enteros_no_negativos():
    panel = make_panel(n_municipios=20, start_year=2015, end_year=2022, seed=7)
    assert (panel.values >= 0).all()
    assert np.issubdtype(panel.values.dtype, np.integer)


def test_reproducible_con_misma_semilla():
    a = make_panel(n_municipios=8, start_year=2020, end_year=2020, seed=99)
    b = make_panel(n_municipios=8, start_year=2020, end_year=2020, seed=99)
    pd.testing.assert_frame_equal(a, b)


def test_semillas_distintas_dan_paneles_distintos():
    a = make_panel(n_municipios=8, start_year=2020, end_year=2020, seed=1)
    b = make_panel(n_municipios=8, start_year=2020, end_year=2020, seed=2)
    assert not a.equals(b)


def test_52_semanas_por_anio():
    panel = make_panel(n_municipios=3, start_year=2018, end_year=2020, seed=1)
    assert panel.shape[1] == 3 * 52


def test_sobredispersion_presente():
    # El panel sintético debe imitar varianza > media (visto en el EDA real),
    # no un proceso Poisson puro.
    panel = make_panel(n_municipios=40, start_year=2015, end_year=2022, seed=3)
    media = panel.mean(axis=1)
    varianza = panel.var(axis=1)
    con_actividad = media > 0.5
    assert (varianza[con_actividad] > media[con_actividad]).mean() > 0.5


def test_panel_nacional_es_suma_de_municipios():
    panel = make_panel(n_municipios=6, start_year=2020, end_year=2020, seed=1)
    nacional = panel_nacional(panel)
    assert isinstance(nacional, pd.Series)
    assert nacional.name == "nacional"
    np.testing.assert_array_equal(nacional.values, panel.sum(axis=0).values)


def test_rechaza_parametros_invalidos():
    with pytest.raises(ValueError):
        make_panel(n_municipios=0)
    with pytest.raises(ValueError):
        make_panel(start_year=2022, end_year=2020)
