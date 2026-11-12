"""Aceptacion B06-I1: casos 1-35 del contrato, agrupados y parametrizados."""
from dataclasses import fields

import numpy as np
import pandas as pd
import pytest

from episentinel.services import ForecastResult, generar_pronostico
from episentinel.services import forecast_service as servicio

METODOS = ["ultimo_valor", "ingenua_estacional"]
FUNCIONES = {
    "ultimo_valor": "pronosticar_ultimo_valor",
    "ingenua_estacional": "pronosticar_ingenua_estacional",
}


def serie(n=120):
    return pd.Series(np.arange(n, dtype=float),
                     index=pd.date_range("2020-01-01", periods=n, freq="7D"), name="casos")


def iguales(a, b):
    for campo in fields(ForecastResult):
        x, y = getattr(a, campo.name), getattr(b, campo.name)
        if isinstance(x, pd.DataFrame):
            pd.testing.assert_frame_equal(x, y)
        else:
            assert x == y


def rechazado(resultado, codigo):
    assert resultado.estado_ejecucion == "rechazado"
    assert resultado.estado_ajuste == "no_ejecutado"
    assert resultado.error.codigo == codigo
    assert resultado.error.campo and resultado.error.mensaje
    assert isinstance(resultado.error.detalles, dict)
    assert resultado.predicciones.empty
    assert list(resultado.predicciones) == ["yhat"]
    assert resultado.predicciones.index.name == "fecha"
    assert resultado.predicciones.yhat.dtype == float
    assert resultado.intervalos is None


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("horizonte", [1, 8, 110])
def test_prediccion_fechas_y_contrato(metodo, horizonte):
    # Casos 1-3, 5-6 y 11: corte inclusivo, no el final de la serie completa.
    s = serie()
    r = generar_pronostico(s, 79, horizonte, metodo)
    esperado = np.full(horizonte, 79.) if metodo == "ultimo_valor" else np.resize(np.arange(28., 80.), horizonte)
    np.testing.assert_array_equal(r.predicciones.yhat, esperado)
    pd.testing.assert_index_equal(r.predicciones.index, pd.date_range(s.index[79] + pd.Timedelta(days=7), periods=horizonte, freq="7D", name="fecha"))
    assert r.estado_ejecucion == "ok" and r.estado_ajuste == "no_requiere_ajuste"
    assert r.metodo == metodo and r.corte == 79 and r.fecha_corte == s.index[79]
    assert r.horizonte == horizonte and r.n_observaciones == 80
    assert r.error is None and r.intervalos is None
    assert r.predicciones.yhat.dtype == float
    assert r.parametros == ({"periodo_estacional": 52} if metodo == "ingenua_estacional" else {})
    codigos = [a.codigo for a in r.advertencias]
    assert codigos == (["CALENDARIO_PROVISIONAL_B03", "PERIODO_ESTACIONAL_HEREDADO_52"] if metodo == "ingenua_estacional" else ["CALENDARIO_PROVISIONAL_B03"])
    assert all(a.mensaje for a in r.advertencias)


@pytest.mark.parametrize("metodo", METODOS)
def test_delega_solo_prefijo(monkeypatch, metodo):
    # Caso 4: espia que conserva la implementacion real.
    s = serie()
    original = getattr(servicio, FUNCIONES[metodo])
    llamadas = []

    def espia(train, pasos, **kwargs):
        llamadas.append((train.copy(), pasos, kwargs))
        return original(train, pasos, **kwargs)

    monkeypatch.setattr(servicio, FUNCIONES[metodo], espia)
    assert generar_pronostico(s, 79, 8, metodo).estado_ejecucion == "ok"
    assert len(llamadas) == 1
    pd.testing.assert_series_equal(llamadas[0][0], s.iloc[:80])
    assert llamadas[0][1:] == (8, {"m": 52} if metodo == "ingenua_estacional" else {})


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("cola", ["extremos", "sin_cola", "corta", "larga", "nan", "inf", "negativo", "texto", "duplicados", "desorden", "hueco", "nat"])
def test_no_anticipacion(metodo, cola):
    # Casos 7-12, incluyendo cambios del dtype global por texto futuro.
    s = serie()
    esperado = generar_pronostico(s, 79, 60, metodo)
    if cola in ("sin_cola", "corta", "larga"):
        s = serie({"sin_cola": 80, "corta": 82, "larga": 200}[cola])
    elif cola in ("duplicados", "desorden", "hueco", "nat"):
        idx = list(s.index)
        idx[81] = {"duplicados": idx[80], "desorden": idx[0], "hueco": idx[81] + pd.Timedelta(days=1), "nat": pd.NaT}[cola]
        s.index = pd.DatetimeIndex(idx)
    else:
        s = s.astype(object)
        s.iloc[80:] = {"extremos": 1e100, "nan": np.nan, "inf": np.inf, "negativo": -1, "texto": "invalido"}[cola]
    iguales(esperado, generar_pronostico(s, 79, 60, metodo))


@pytest.mark.parametrize("metodo,n", [("ultimo_valor", 1), ("ingenua_estacional", 52)])
def test_historico_minimo(metodo, n):
    # Casos 13 y 15.
    assert generar_pronostico(serie(n), n - 1, 8, metodo).estado_ejecucion == "ok"


def test_insuficiente_aunque_exista_futuro():
    # Caso 14.
    r = generar_pronostico(serie(), 50, 8, "ingenua_estacional")
    rechazado(r, "HISTORICO_INSUFICIENTE")
    assert r.error.detalles == {"requeridas": 52, "disponibles": 51}


@pytest.mark.parametrize("corte", [0, -1, None, True, "0"])
def test_vacia_antes_del_corte(corte):
    # Caso 16 y prioridad aclarada por el usuario.
    rechazado(generar_pronostico(serie(0), corte, 8, "ultimo_valor"), "SERIE_VACIA")


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("constante", [0., 7.5])
def test_constantes(metodo, constante):
    # Casos 17-18.
    s = serie()
    s[:] = constante
    r = generar_pronostico(s, 79, 60, metodo)
    assert r.estado_ejecucion == "ok"
    np.testing.assert_array_equal(r.predicciones.yhat, np.full(60, constante))


@pytest.mark.parametrize("entrada", [[], np.array([1]), pd.DataFrame({"x": [1]}), None])
def test_tipo_serie(entrada):
    # Caso 19.
    rechazado(generar_pronostico(entrada, 0, 8, "ultimo_valor"), "SERIE_INVALIDA")


@pytest.mark.parametrize("horizonte", [0, -1, True, np.bool_(False), 8., "8", None])
def test_horizonte_invalido(horizonte):
    # Caso 20.
    rechazado(generar_pronostico(serie(), 79, horizonte, "ultimo_valor"), "HORIZONTE_INVALIDO")


def test_enteros_numpy():
    # Casos 21 y 23.
    r = generar_pronostico(serie(), np.int64(79), np.int64(8), "ultimo_valor")
    assert r.estado_ejecucion == "ok"
    assert type(r.corte) is int and type(r.horizonte) is int


@pytest.mark.parametrize("corte", [-1, 120, True, np.bool_(True), 79., "79", None])
def test_corte_invalido(corte):
    # Caso 22.
    rechazado(generar_pronostico(serie(), corte, 8, "ultimo_valor"), "CORTE_INVALIDO")


@pytest.mark.parametrize("metodo", ["desconocido", "Último valor", None])
def test_metodo_invalido(monkeypatch, metodo):
    # Caso 24: ningun baseline puede ejecutarse.
    def prohibido(*args, **kwargs):
        pytest.fail("Se ejecuto un baseline con metodo invalido")
    for funcion in FUNCIONES.values():
        monkeypatch.setattr(servicio, funcion, prohibido)
    rechazado(generar_pronostico(serie(), 79, 8, metodo), "METODO_INVALIDO")


@pytest.mark.parametrize("tipo,codigo", [("numerico", "INDICE_INVALIDO"), ("tz", "INDICE_INVALIDO"), ("nat", "INDICE_INVALIDO"), ("duplicado", "INDICE_INVALIDO"), ("desorden", "INDICE_INVALIDO"), ("hueco", "FRECUENCIA_INVALIDA"), ("diario", "FRECUENCIA_INVALIDA")])
def test_indices_invalidos(tipo, codigo):
    # Casos 25-26.
    s = serie()
    if tipo == "numerico":
        s.index = range(len(s))
    elif tipo == "tz":
        s.index = s.index.tz_localize("UTC")
    elif tipo == "hueco":
        s = s.drop(s.index[10])
    elif tipo == "diario":
        s.index = pd.date_range("2020-01-01", periods=len(s), freq="D")
    else:
        idx = list(s.index)
        idx[10] = {"nat": pd.NaT, "duplicado": idx[9], "desorden": idx[0]}[tipo]
        s.index = pd.DatetimeIndex(idx)
    rechazado(generar_pronostico(s, 79, 8, "ultimo_valor"), codigo)


@pytest.mark.parametrize("valor", [np.nan, pd.NA, np.inf, -np.inf, -1, True, np.bool_(False), 1 + 0j, "texto", "12"])
def test_valores_invalidos(valor):
    # Caso 27.
    s = serie().astype(object)
    s.iloc[10] = valor
    r = generar_pronostico(s, 79, 8, "ultimo_valor")
    rechazado(r, "VALORES_INVALIDOS")
    assert r.error.detalles["posicion"] == 10


def test_fechas_fuera_de_rango():
    # Caso 28.
    s = pd.Series([1.], index=pd.DatetimeIndex([pd.Timestamp.max]))
    rechazado(generar_pronostico(s, 0, 8, "ultimo_valor"), "FECHAS_FUTURAS_INVALIDAS")


def test_separacion_temporal_no_representable():
    s = pd.Series([1., 2.], index=pd.DatetimeIndex([pd.Timestamp.min, pd.Timestamp.max]))
    rechazado(generar_pronostico(s, 1, 8, "ultimo_valor"), "FRECUENCIA_INVALIDA")


@pytest.mark.parametrize("s,corte,horizonte,metodo,codigo", [
    (None, None, 0, None, "SERIE_INVALIDA"),
    (serie(0), None, 0, None, "HORIZONTE_INVALIDO"),
    (serie(0), None, 8, None, "METODO_INVALIDO"),
    (serie(0), None, 8, "ultimo_valor", "SERIE_VACIA"),
    (pd.Series([np.nan]), -1, 8, "ultimo_valor", "CORTE_INVALIDO"),
    (pd.Series([np.nan]), 0, 8, "ultimo_valor", "INDICE_INVALIDO"),
    (pd.Series([np.nan], index=serie(1).index), 0, 8, "ingenua_estacional", "VALORES_INVALIDOS"),
])
def test_precedencia_y_rechazo(s, corte, horizonte, metodo, codigo):
    # Casos 29 y 33.
    rechazado(generar_pronostico(s, corte, horizonte, metodo), codigo)


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("excepcion", [ValueError, RuntimeError, FloatingPointError, OverflowError])
def test_fallo_operativo_sin_sustitucion(monkeypatch, metodo, excepcion):
    # Casos 30 y 34.
    def fallar(*args, **kwargs):
        raise excepcion("fallo simulado")
    def prohibido(*args, **kwargs):
        pytest.fail("Sustitucion silenciosa de metodo")
    for otro, funcion in FUNCIONES.items():
        monkeypatch.setattr(servicio, funcion, fallar if otro == metodo else prohibido)
    r = generar_pronostico(serie(), 79, 8, metodo)
    assert r.estado_ejecucion == "error" and r.estado_ajuste == "no_requiere_ajuste"
    assert r.error.codigo == "FALLO_PRONOSTICO" and r.predicciones.empty
    assert r.error.detalles["tipo_excepcion"] == excepcion.__name__


@pytest.mark.parametrize("defecto", ["longitud", "fechas", "negativo", "nan", "inf", "tipo", "texto", "booleano"])
def test_salida_invalida(monkeypatch, defecto):
    # Caso 31.
    def salida(train, pasos):
        p = pd.Series(np.ones(pasos), index=pd.date_range(train.index[-1] + pd.Timedelta(days=7), periods=pasos, freq="7D"))
        if defecto == "longitud":
            return p.iloc[:-1]
        if defecto == "fechas":
            p.index += pd.Timedelta(days=1)
        elif defecto == "tipo":
            return p.to_frame()
        else:
            p = p.astype(object)
            p.iloc[0] = {"negativo": -1, "nan": np.nan, "inf": np.inf, "texto": "1", "booleano": True}[defecto]
        return p
    monkeypatch.setattr(servicio, "pronosticar_ultimo_valor", salida)
    r = generar_pronostico(serie(), 79, 8, "ultimo_valor")
    assert r.estado_ejecucion == "error" and r.estado_ajuste == "no_requiere_ajuste"
    assert r.error.codigo == "SALIDA_INVALIDA" and r.predicciones.empty


def test_error_inesperado_visible(monkeypatch):
    # Caso 32.
    def fallo(*args, **kwargs):
        raise TypeError("defecto de programacion")
    monkeypatch.setattr(servicio, "pronosticar_ultimo_valor", fallo)
    with pytest.raises(TypeError, match="defecto de programacion"):
        generar_pronostico(serie(), 79, 8, "ultimo_valor")


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("invalida", [False, True])
def test_no_muta_entrada(metodo, invalida):
    # Caso 35.
    s = serie()
    if invalida:
        s.iloc[10] = np.nan
    antes = s.copy(deep=True)
    generar_pronostico(s, 79, 8, metodo)
    pd.testing.assert_series_equal(s, antes)


def test_intervalos_comparten_indice():
    r = generar_pronostico(serie(), 79, 8, "ultimo_valor")
    bandas = pd.DataFrame({"lo": np.zeros(8), "hi": np.ones(8)}, index=r.predicciones.index.copy())
    ForecastResult(predicciones=r.predicciones, intervalos=bandas)
    bandas.index = bandas.index + pd.Timedelta(days=1)
    with pytest.raises(ValueError, match="mismo indice temporal"):
        ForecastResult(predicciones=r.predicciones, intervalos=bandas)
