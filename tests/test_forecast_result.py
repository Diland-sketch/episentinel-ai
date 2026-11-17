"""Contrato I2-A: construccion completa, estados y aislamiento de datos."""
from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from episentinel.services import Advertencia, ErrorPronostico, ForecastResult


def datos_exito(**cambios):
    fecha = pd.Timestamp("2020-01-01")
    indice = pd.date_range(fecha + pd.Timedelta(days=7), periods=2, freq="7D", name="fecha")
    datos = dict(estado_ejecucion="ok", estado_ajuste="no_requiere_ajuste",
                 metodo="ultimo_valor", corte=0, fecha_corte=fecha,
                 horizonte=2, n_observaciones=1,
                 predicciones=pd.DataFrame({"yhat": [2., 2.]}, index=indice))
    datos.update(cambios)
    return datos


def bandas(indice):
    return pd.DataFrame({"lo": [1., 1.], "hi": [3., 3.]}, index=indice.copy())


def error():
    return ErrorPronostico("SERIE_INVALIDA", "serie", "Serie invalida")


def test_construccion_atomica_y_vistas_con_indice_canonico():
    datos = datos_exito()
    r = ForecastResult(**datos, intervalos=bandas(datos["predicciones"].index))
    pd.testing.assert_frame_equal(r.predicciones, datos["predicciones"])
    pd.testing.assert_index_equal(r.predicciones.index, r.intervalos.index, exact=True)
    assert r.predicciones is not r.predicciones
    assert r.intervalos is not r.intervalos
    assert r.predicciones.index.name == "fecha"
    assert r.predicciones.yhat.dtype == float


def test_copia_de_tablas_de_entrada_incluye_valores_e_indices():
    datos = datos_exito()
    pred = datos["predicciones"]
    ic = bandas(pred.index)
    esperado, bandas_esperadas = pred.copy(deep=True), ic.copy(deep=True)
    r = ForecastResult(**datos, intervalos=ic)
    pred.iloc[0, 0] = 999
    ic.iloc[0, 0] = 999
    pred.index = pred.index + pd.Timedelta(days=7)
    ic.index = ic.index + pd.Timedelta(days=14)
    pd.testing.assert_frame_equal(r.predicciones, esperado)
    pd.testing.assert_frame_equal(r.intervalos, bandas_esperadas)


@pytest.mark.parametrize("tabla", ["predicciones", "intervalos"])
def test_mutacion_de_vistas_no_afecta_resultado(tabla):
    datos = datos_exito()
    r = ForecastResult(**datos, intervalos=bandas(datos["predicciones"].index))
    antes_pred, antes_ic = r.predicciones, r.intervalos
    vista = getattr(r, tabla)
    vista.iloc[0, 0] = -123
    vista.index = vista.index + pd.Timedelta(days=7)
    vista.columns = [f"columna_{i}" for i in range(len(vista.columns))]
    pd.testing.assert_frame_equal(r.predicciones, antes_pred)
    pd.testing.assert_frame_equal(r.intervalos, antes_ic)


def test_arrays_originales_no_quedan_referenciados():
    fechas = np.array(["2020-01-08", "2020-01-15"], dtype="datetime64[ns]")
    valores = np.array([2., 2.])
    pred = pd.DataFrame({"yhat": valores}, index=pd.DatetimeIndex(fechas, copy=False), copy=False)
    r = ForecastResult(**datos_exito(predicciones=pred))
    esperado = r.predicciones
    valores[0] = 999
    fechas[0] = np.datetime64("2030-01-01")
    pd.testing.assert_frame_equal(r.predicciones, esperado)


@pytest.mark.parametrize("nombre,valor", [
    ("estado_ejecucion", "error"), ("estado_ajuste", "no_ejecutado"),
    ("metodo", "ingenua_estacional"), ("corte", 9), ("fecha_corte", pd.Timestamp("2030-01-01")),
    ("horizonte", 99), ("n_observaciones", 10), ("parametros", {}),
    ("advertencias", ()), ("error", error()), ("predicciones", None), ("intervalos", None),
])
def test_no_reasignacion_publica(nombre, valor):
    r = ForecastResult(**datos_exito())
    # slots + frozen puede rechazar propiedades con TypeError segun Python.
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        setattr(r, nombre, valor)


def test_metadatos_sin_aliases_y_congelados_recursivamente():
    origen = {"config": {"orden": [1, 0, 1]}, "lista": [{"valor": 2}], "escalar": np.int64(52)}
    avisos = [Advertencia("CALENDARIO_PROVISIONAL_B03", "Pendiente de B03")]
    r = ForecastResult(**datos_exito(), parametros=origen, advertencias=avisos)
    origen["config"]["orden"][0] = 999
    origen["lista"][0]["valor"] = 999
    avisos.clear()
    assert r.parametros["config"]["orden"] == (1, 0, 1)
    assert r.parametros["lista"][0]["valor"] == 2
    assert r.parametros["escalar"] == 52
    assert len(r.advertencias) == 1
    assert isinstance(r.parametros, Mapping)
    with pytest.raises(TypeError):
        r.parametros["nuevo"] = 1
    with pytest.raises(TypeError):
        r.parametros["config"]["nuevo"] = 1
    with pytest.raises(TypeError):
        r.parametros["lista"][0]["valor"] = 3
    with pytest.raises(TypeError):
        r.parametros["config"]["orden"][0] = 3
    with pytest.raises(FrozenInstanceError):
        r.advertencias[0].codigo = "otro"


def test_detalles_error_tambien_se_congelan():
    origen = {"posiciones": [1, 2], "contexto": {"valor": 3}}
    e = ErrorPronostico("VALORES_INVALIDOS", "serie", "No valido", origen)
    r = ForecastResult(estado_ejecucion="rechazado", estado_ajuste="no_ejecutado", error=e)
    origen["posiciones"].append(4)
    origen["contexto"]["valor"] = 9
    assert r.error.detalles == {"posiciones": (1, 2), "contexto": {"valor": 3}}
    with pytest.raises(TypeError):
        r.error.detalles["contexto"]["valor"] = 1
    with pytest.raises(FrozenInstanceError):
        r.error.codigo = "otro"


@pytest.mark.parametrize("valor", [pd.DataFrame({"x": [1]}), np.array([1]), {1, 2}, object()])
def test_metadatos_mutables_no_soportados_se_rechazan(valor):
    with pytest.raises(TypeError):
        ForecastResult(**datos_exito(), parametros={"objeto": valor})
    with pytest.raises(TypeError):
        ErrorPronostico("E", "serie", "error", {"objeto": valor})


def test_metadatos_ciclicos_y_claves_no_texto():
    ciclo = []
    ciclo.append(ciclo)
    with pytest.raises(ValueError, match="ciclicos"):
        ForecastResult(**datos_exito(), parametros={"ciclo": ciclo})
    with pytest.raises(TypeError, match="claves"):
        ForecastResult(**datos_exito(), parametros={1: "valor"})


@pytest.mark.parametrize("cambios", [
    {"estado_ejecucion": "desconocido"}, {"estado_ajuste": "convergente"},
    {"estado_ajuste": "no_ejecutado"}, {"metodo": "sarima_estacional"},
    {"metodo": None}, {"corte": None}, {"fecha_corte": None}, {"horizonte": None},
    {"error": error()}, {"horizonte": 0}, {"horizonte": True}, {"horizonte": 2.},
    {"corte": -1}, {"corte": True}, {"n_observaciones": 2}, {"n_observaciones": True},
    {"fecha_corte": pd.NaT}, {"fecha_corte": "2020-01-01"},
    {"fecha_corte": pd.Timestamp("2020-01-01", tz="UTC")},
    {"metodo": "ingenua_estacional"},
])
def test_exito_incoherente_se_rechaza(cambios):
    with pytest.raises(ValueError):
        ForecastResult(**datos_exito(**cambios))


def test_construccion_vacia_o_posicional_no_admitida():
    with pytest.raises(TypeError):
        ForecastResult()
    with pytest.raises(TypeError):
        ForecastResult("ok", "no_requiere_ajuste")


def test_rechazo_completo_sin_metadatos_aun_no_validados():
    r = ForecastResult(estado_ejecucion="rechazado", estado_ajuste="no_ejecutado", error=error())
    assert r.metodo is None and r.fecha_corte is None and r.corte is None
    assert r.n_observaciones == 0 and r.horizonte is None
    assert r.predicciones.empty and r.intervalos is None
    assert list(r.predicciones) == ["yhat"]
    assert r.predicciones.index.name == "fecha" and r.predicciones.yhat.dtype == float


@pytest.mark.parametrize("estado", ["rechazado", "error"])
@pytest.mark.parametrize("defecto", ["sin_error", "con_predicciones", "con_intervalos", "ajuste_incorrecto"])
def test_no_exito_exige_error_y_no_publica_datos(estado, defecto):
    datos = datos_exito(estado_ejecucion=estado,
                        estado_ajuste="no_ejecutado" if estado == "rechazado" else "no_requiere_ajuste",
                        error=error())
    pred = datos.pop("predicciones")
    if defecto == "sin_error":
        datos["error"] = None
    elif defecto == "con_predicciones":
        datos["predicciones"] = pred
    elif defecto == "con_intervalos":
        datos["intervalos"] = bandas(pred.index).iloc[:0]
    else:
        datos["estado_ajuste"] = "no_requiere_ajuste" if estado == "rechazado" else "no_ejecutado"
    with pytest.raises(ValueError):
        ForecastResult(**datos)


def test_error_operativo_con_metadatos_completos():
    datos = datos_exito(estado_ejecucion="error", error=ErrorPronostico("FALLO_PRONOSTICO", "metodo", "Fallo"))
    datos.pop("predicciones")
    r = ForecastResult(**datos)
    assert r.predicciones.empty and r.estado_ajuste == "no_requiere_ajuste"
    datos["fecha_corte"] = None
    with pytest.raises(ValueError):
        ForecastResult(**datos)


@pytest.mark.parametrize("defecto", ["columna", "duplicada", "longitud", "fecha", "nat", "tz", "indice", "nan", "inf", "negativo", "texto", "booleano"])
def test_predicciones_invalidas(defecto):
    datos = datos_exito()
    p = datos["predicciones"]
    if defecto == "columna":
        p.columns = ["otro"]
    elif defecto == "duplicada":
        datos["predicciones"] = pd.concat([p, p], axis=1)
    elif defecto == "longitud":
        datos["predicciones"] = p.iloc[:1]
    elif defecto == "fecha":
        p.index += pd.Timedelta(days=1)
    elif defecto == "nat":
        p.index = pd.DatetimeIndex([pd.NaT, p.index[1]])
    elif defecto == "tz":
        p.index = p.index.tz_localize("UTC")
    elif defecto == "indice":
        p.index = range(2)
    else:
        p = p.astype(object)
        p.iloc[0, 0] = {"nan": np.nan, "inf": np.inf, "negativo": -1, "texto": "1", "booleano": True}[defecto]
        datos["predicciones"] = p
    with pytest.raises(ValueError):
        ForecastResult(**datos)


@pytest.mark.parametrize("defecto", ["indice", "columnas", "nan", "inf", "negativo", "invertidas", "punto_fuera", "longitud"])
def test_intervalos_invalidos(defecto):
    datos = datos_exito()
    ic = bandas(datos["predicciones"].index)
    if defecto == "indice":
        ic.index += pd.Timedelta(days=1)
    elif defecto == "columnas":
        ic.columns = ["inferior", "superior"]
    elif defecto == "longitud":
        ic = ic.iloc[:1]
    elif defecto == "invertidas":
        ic.iloc[0] = [4, 1]
    elif defecto == "punto_fuera":
        ic.iloc[0] = [3, 4]
    else:
        ic.iloc[0, 0] = {"nan": np.nan, "inf": np.inf, "negativo": -1}[defecto]
    with pytest.raises(ValueError):
        ForecastResult(**datos, intervalos=ic)


@pytest.mark.parametrize("cambios", [
    {"predicciones": [1, 2]}, {"intervalos": [1, 2]}, {"parametros": []},
    {"advertencias": ["texto"]}, {"error": "texto"},
])
def test_tipos_incorrectos(cambios):
    with pytest.raises(TypeError):
        ForecastResult(**datos_exito(**cambios))


def datos_sarima(**cambios):
    datos = datos_exito(metodo="sarima_sin_estacional", corte=29, n_observaciones=30,
                        estado_ajuste="convergente", nivel_intervalo=0.95,
                        diagnostico_ajuste={"converged": True, "llf": -12.5,
                                            "parametros_finitos": True, "iterations": 4})
    datos["intervalos"] = bandas(datos["predicciones"].index)
    datos.update(cambios)
    return datos


@pytest.mark.parametrize("estado,converged", [
    ("fallido", None), ("convergente", True), ("no_convergente", False), ("no_verificado", None),
])
def test_error_sarima_antes_o_despues_del_ajuste(estado, converged):
    datos = datos_sarima(estado_ejecucion="error", estado_ajuste=estado,
                        predicciones=None, intervalos=None, nivel_intervalo=None,
                        diagnostico_ajuste={"converged": converged},
                        error=ErrorPronostico("FALLO", "metodo", "Fallo simulado"))
    r = ForecastResult(**datos)
    assert r.estado_ajuste == estado and r.estado_ejecucion == "error"
    assert r.predicciones.empty and r.intervalos is None and r.nivel_intervalo is None


def test_sarima_exitoso_y_diagnostico_inmutable():
    datos = datos_sarima()
    datos["diagnostico_ajuste"]["optimizer"] = {"gopt": [0.1, 0.2]}
    r = ForecastResult(**datos)
    datos["diagnostico_ajuste"]["optimizer"]["gopt"][0] = 99
    assert r.diagnostico_ajuste["optimizer"]["gopt"] == (0.1, 0.2)
    with pytest.raises(TypeError):
        r.diagnostico_ajuste["iterations"] = 99
    with pytest.raises(FrozenInstanceError):
        r.nivel_intervalo = 0.9
    pd.testing.assert_index_equal(r.predicciones.index, r.intervalos.index)
    assert r.estado_ajuste == "convergente" and r.nivel_intervalo == 0.95


@pytest.mark.parametrize("cambios", [
    {"intervalos": None}, {"nivel_intervalo": None}, {"nivel_intervalo": 1},
    {"nivel_intervalo": np.nan}, {"nivel_intervalo": True}, {"diagnostico_ajuste": None},
    {"diagnostico_ajuste": {}}, {"diagnostico_ajuste": {"converged": 1}},
    {"diagnostico_ajuste": {"converged": False}},
    {"diagnostico_ajuste": {"converged": True, "llf": np.nan, "parametros_finitos": True}},
    {"diagnostico_ajuste": {"converged": True, "llf": -1., "parametros_finitos": False}},
    {"estado_ajuste": "no_convergente"}, {"estado_ajuste": "no_requiere_ajuste"},
])
def test_sarima_exito_incoherente_rechazado(cambios):
    with pytest.raises(ValueError):
        ForecastResult(**datos_sarima(**cambios))


def test_rechazo_sarima_no_tiene_diagnostico_ni_intervalos():
    r = ForecastResult(estado_ejecucion="rechazado", estado_ajuste="no_ejecutado",
                       metodo="sarima_estacional", error=error())
    assert r.diagnostico_ajuste is None and r.nivel_intervalo is None
    with pytest.raises(ValueError):
        ForecastResult(estado_ejecucion="rechazado", estado_ajuste="no_ejecutado",
                       metodo="sarima_estacional", error=error(), diagnostico_ajuste={})


@pytest.mark.parametrize("cambio", [{"diagnostico_ajuste": {}}, {"nivel_intervalo": 0.95}])
def test_baseline_no_declara_diagnostico_sarima(cambio):
    with pytest.raises(ValueError):
        ForecastResult(**datos_exito(**cambio))
