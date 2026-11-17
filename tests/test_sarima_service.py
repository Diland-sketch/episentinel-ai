"""B06-I2-B: politica del adaptador y ajustes reales sin alterar algoritmos."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
from types import SimpleNamespace
import warnings

import numpy as np
import pandas as pd
import pytest
from statsmodels.tools.sm_exceptions import ConvergenceWarning, HessianInversionWarning, ValueWarning

from episentinel.services import generar_pronostico
from episentinel.services import sarima_adapter as adaptador

METODOS = ("sarima_sin_estacional", "sarima_estacional")
MINIMOS = {"sarima_sin_estacional": 30, "sarima_estacional": 156}


def serie(n=180):
    return pd.Series(10. + np.arange(n) % 7,
                     index=pd.date_range("2015-01-01", periods=n, freq="7D"), name="casos")


@pytest.fixture
def motor(monkeypatch):
    resultado = SimpleNamespace(mle_retvals={"converged": True, "iterations": np.int64(4), "warnflag": 0},
                                params=np.array([0.1, 0.2, 1.]), llf=-12.5)
    llamadas = []

    def ajustar(train, *, order, seasonal_order):
        llamadas.append(("ajuste", train.copy(deep=True), order, seasonal_order))
        resultado.ultimo = train.iloc[-1]
        return resultado

    def pronosticar(res, pasos, fechas, alpha):
        llamadas.append(("pronostico", pasos, fechas.copy(), alpha))
        valores = res.ultimo + np.arange(pasos, dtype=float)
        return pd.DataFrame({"yhat": valores, "lo": valores - 1, "hi": valores + 1}, index=fechas)

    monkeypatch.setattr(adaptador, "ajustar_sarima", ajustar)
    monkeypatch.setattr(adaptador, "pronosticar", pronosticar)
    return SimpleNamespace(resultado=resultado, llamadas=llamadas, ajustar=ajustar, pronosticar=pronosticar)


def verificar_error(r, codigo, ajuste, ejecucion="error"):
    assert r.estado_ejecucion == ejecucion and r.estado_ajuste == ajuste
    assert r.error.codigo == codigo
    assert r.predicciones.empty and r.intervalos is None and r.nivel_intervalo is None
    if ejecucion == "rechazado":
        assert r.diagnostico_ajuste is None


@pytest.mark.parametrize("metodo", METODOS)
def test_delegacion_configuracion_y_resultado(motor, metodo):
    s = serie(200)
    r = generar_pronostico(s, 170, 40, metodo, alpha=0.1)
    assert r.estado_ejecucion == "ok" and r.estado_ajuste == "convergente"
    assert r.nivel_intervalo == 0.9
    pd.testing.assert_series_equal(motor.llamadas[0][1], s.iloc[:171])
    assert motor.llamadas[0][2] == (1, 1, 1)
    esperado = (1, 0, 1, 52) if metodo == "sarima_estacional" else (0, 0, 0, 0)
    assert motor.llamadas[0][3] == esperado
    assert motor.llamadas[1][1] == 40 and motor.llamadas[1][3] == 0.1
    assert r.parametros["seasonal_order"] == esperado
    assert r.parametros["politica_historico"] == "sarima_min_history_v1"
    assert r.diagnostico_ajuste["converged"] is True
    assert r.diagnostico_ajuste["iterations"] == 4
    assert r.diagnostico_ajuste["llf"] == -12.5
    assert len(r.predicciones) == 40
    pd.testing.assert_index_equal(r.predicciones.index, r.intervalos.index)
    assert (r.intervalos.lo <= r.predicciones.yhat).all()
    assert (r.predicciones.yhat <= r.intervalos.hi).all()


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("desfase", [-1, 0, 1])
def test_minimos_operativos_al_corte(motor, metodo, desfase):
    n = MINIMOS[metodo] + desfase
    r = generar_pronostico(serie(220), n - 1, 8, metodo)
    if desfase < 0:
        verificar_error(r, "HISTORICO_INSUFICIENTE", "no_ejecutado", "rechazado")
        assert r.error.detalles["disponibles"] == n
        assert r.error.detalles["requeridas"] == MINIMOS[metodo]
        assert not motor.llamadas
    else:
        assert r.estado_ejecucion == "ok"


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("valor", [0., 7.])
def test_constantes_rechazadas_sin_sustitucion(motor, metodo, valor):
    s = serie()
    s[:] = valor
    verificar_error(generar_pronostico(s, 179, 8, metodo), "SERIE_CONSTANTE_NO_ADMITIDA", "no_ejecutado", "rechazado")
    assert not motor.llamadas


def test_casi_constante_se_ejecuta_y_corta_prioriza_longitud(motor):
    s = serie()
    s[:] = 7.
    r = generar_pronostico(s, 20, 8, "sarima_sin_estacional")
    verificar_error(r, "HISTORICO_INSUFICIENTE", "no_ejecutado", "rechazado")
    s.iloc[0] += 1e-10
    assert generar_pronostico(s, 179, 8, "sarima_sin_estacional").estado_ejecucion == "ok"


@pytest.mark.parametrize("valor", [2**53 + 1, np.uint64(2**53 + 1), Fraction(1, 3)])
def test_conversion_inexacta_rechazada_antes_del_ajuste(motor, valor):
    s = serie().astype(object)
    s.iloc[10] = valor
    r = generar_pronostico(s, 179, 8, "sarima_sin_estacional")
    verificar_error(r, "PRECISION_NUMERICA_NO_ADMITIDA", "no_ejecutado", "rechazado")
    assert r.error.detalles["posicion"] == 10 and not motor.llamadas


@pytest.mark.parametrize("alpha", [0, 1, -0.1, True, np.bool_(False), np.nan, np.inf, "0.05", None, 1e-300, 10**400])
def test_alpha_invalido(motor, alpha):
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional", alpha=alpha)
    verificar_error(r, "ALPHA_INVALIDO", "no_ejecutado", "rechazado")
    assert not motor.llamadas


def test_alpha_real_convertible(motor):
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional", alpha=Fraction(1, 20))
    assert r.estado_ejecucion == "ok" and r.nivel_intervalo == 0.95


@pytest.mark.parametrize("valor", [None, 1, "true", {}, False, np.bool_(True)])
def test_indicador_de_convergencia(motor, valor):
    motor.resultado.mle_retvals["converged"] = valor
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")
    if isinstance(valor, np.bool_) and valor:
        assert r.estado_ejecucion == "ok"
    elif valor is False:
        verificar_error(r, "NO_CONVERGENCIA", "no_convergente")
    else:
        verificar_error(r, "CONVERGENCIA_NO_VERIFICABLE", "no_verificado")
    if r.estado_ejecucion != "ok":
        assert len(motor.llamadas) == 1


@pytest.mark.parametrize("retvals", [None, {}, {"converged": True, "warnflag": 2}])
def test_diagnostico_ausente_o_contradictorio(motor, retvals):
    motor.resultado.mle_retvals = retvals
    verificar_error(generar_pronostico(serie(), 179, 8, "sarima_sin_estacional"),
                    "CONVERGENCIA_NO_VERIFICABLE", "no_verificado")


@pytest.mark.parametrize("converged,ajuste,codigo", [
    (True, "no_verificado", "CONVERGENCIA_NO_VERIFICABLE"),
    (False, "no_convergente", "NO_CONVERGENCIA"),
    (None, "no_convergente", "NO_CONVERGENCIA"),
])
def test_advertencia_de_convergencia_bloquea(motor, monkeypatch, converged, ajuste, codigo):
    motor.resultado.mle_retvals["converged"] = converged
    def ajustar(*args, **kwargs):
        warnings.warn("No converge", ConvergenceWarning)
        return motor.ajustar(*args, **kwargs)
    monkeypatch.setattr(adaptador, "ajustar_sarima", ajustar)
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")
    verificar_error(r, codigo, ajuste)
    assert r.advertencias[-1].fase == "ajuste"
    assert r.advertencias[-1].codigo == "NO_CONVERGENCIA"
    assert len(motor.llamadas) == 1


@pytest.mark.parametrize("campo,valor", [("llf", np.nan), ("llf", np.inf), ("llf", None),
                                         ("params", [np.inf]), ("params", []), ("params", None),
                                         ("params", [1 + 2j]), ("params", [True]), ("params", ["1"])])
def test_diagnostico_numerico_invalido(motor, campo, valor):
    setattr(motor.resultado, campo, valor)
    verificar_error(generar_pronostico(serie(), 179, 8, "sarima_sin_estacional"),
                    "AJUSTE_NUMERICO_INVALIDO", "fallido")
    assert len(motor.llamadas) == 1


@pytest.mark.parametrize("fase", ["ajuste", "pronostico"])
@pytest.mark.parametrize("excepcion", [ValueError, RuntimeError, np.linalg.LinAlgError, FloatingPointError, OverflowError])
def test_excepciones_previstas(motor, monkeypatch, fase, excepcion):
    def fallar(*args, **kwargs):
        warnings.warn("Aviso antes del fallo", UserWarning)
        raise excepcion("fallo simulado")
    monkeypatch.setattr(adaptador, "ajustar_sarima" if fase == "ajuste" else "pronosticar", fallar)
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")
    numerica = excepcion in (np.linalg.LinAlgError, FloatingPointError, OverflowError)
    codigo = ("ERROR_NUMERICO_" if numerica else "FALLO_") + fase.upper()
    verificar_error(r, codigo, "fallido" if fase == "ajuste" else "convergente")
    assert r.error.detalles["fase"] == fase
    assert r.error.detalles["tipo_excepcion"] == excepcion.__name__
    assert r.advertencias[-1].fase == fase


@pytest.mark.parametrize("fase", ["ajuste", "pronostico"])
@pytest.mark.parametrize("excepcion", [TypeError, AttributeError, AssertionError])
def test_excepciones_inesperadas_no_se_ocultan(motor, monkeypatch, fase, excepcion):
    def fallar(*args, **kwargs):
        raise excepcion("defecto de programacion")
    monkeypatch.setattr(adaptador, "ajustar_sarima" if fase == "ajuste" else "pronosticar", fallar)
    with pytest.raises(excepcion, match="programacion"):
        generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")


@pytest.mark.parametrize("fase", ["ajuste", "pronostico"])
@pytest.mark.parametrize("categoria", [UserWarning, RuntimeWarning, HessianInversionWarning])
def test_advertencias_bloqueantes(motor, monkeypatch, fase, categoria):
    original = motor.ajustar if fase == "ajuste" else motor.pronosticar
    def avisar(*args, **kwargs):
        warnings.warn("Diagnostico no permitido", categoria)
        return original(*args, **kwargs)
    monkeypatch.setattr(adaptador, "ajustar_sarima" if fase == "ajuste" else "pronosticar", avisar)
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")
    if categoria is RuntimeWarning:
        verificar_error(r, "ERROR_NUMERICO_" + fase.upper(), "fallido" if fase == "ajuste" else "convergente")
    else:
        verificar_error(r, "ADVERTENCIA_" + fase.upper() + "_BLOQUEANTE", "convergente")
    assert r.advertencias[-1].fase == fase


@pytest.mark.parametrize("categoria,mensaje,codigo", [
    (ValueWarning, "No frequency information was provided, so inferred frequency 7D will be used.", "FRECUENCIA_INFERIDA"),
    (UserWarning, "Non-stationary starting autoregressive parameters found. Using zeros as starting parameters.", "INICIALIZACION_SARIMA"),
    (UserWarning, "Non-invertible starting MA parameters found. Using zeros as starting parameters.", "INICIALIZACION_SARIMA"),
])
def test_advertencias_permitidas_se_conservan(motor, monkeypatch, categoria, mensaje, codigo):
    def ajustar(*args, **kwargs):
        warnings.warn(mensaje, categoria)
        return motor.ajustar(*args, **kwargs)
    monkeypatch.setattr(adaptador, "ajustar_sarima", ajustar)
    filtros, errores_numpy = list(warnings.filters), np.geterr().copy()
    r = generar_pronostico(serie(), 179, 8, "sarima_sin_estacional")
    assert r.estado_ejecucion == "ok" and r.advertencias[-1].codigo == codigo
    assert r.advertencias[-1].fase == "ajuste" and mensaje in r.advertencias[-1].mensaje
    assert warnings.filters == filtros and np.geterr() == errores_numpy


def test_frecuencia_inferida_no_semanal_bloquea(motor, monkeypatch):
    def ajustar(*args, **kwargs):
        warnings.warn("No frequency information was provided, so inferred frequency D will be used.", ValueWarning)
        return motor.ajustar(*args, **kwargs)
    monkeypatch.setattr(adaptador, "ajustar_sarima", ajustar)
    verificar_error(generar_pronostico(serie(), 179, 8, "sarima_sin_estacional"),
                    "ADVERTENCIA_AJUSTE_BLOQUEANTE", "convergente")


@pytest.mark.parametrize("defecto,codigo", [
    ("tipo", "SALIDA_INVALIDA"), ("fechas", "SALIDA_INVALIDA"), ("longitud", "SALIDA_INVALIDA"),
    ("columna_extra", "SALIDA_INVALIDA"), ("yhat_nan", "RESULTADO_NUMERICO_INVALIDO"),
    ("yhat_negativo", "RESULTADO_NUMERICO_INVALIDO"), ("sin_bandas", "INTERVALO_INVALIDO"),
    ("lo_nan", "INTERVALO_INVALIDO"), ("hi_inf", "INTERVALO_INVALIDO"),
    ("lo_negativo", "INTERVALO_INVALIDO"), ("invertidas", "INTERVALO_INVALIDO"),
    ("punto_fuera", "INTERVALO_INVALIDO"),
])
def test_salidas_invalidas_no_publican_exito_parcial(motor, monkeypatch, defecto, codigo):
    def pronosticar(*args, **kwargs):
        p = motor.pronosticar(*args, **kwargs)
        if defecto == "tipo":
            return p.yhat
        if defecto == "fechas":
            p.index += pd.Timedelta(days=1)
        elif defecto == "longitud":
            return p.iloc[:-1]
        elif defecto == "columna_extra":
            p["extra"] = 1
        elif defecto == "sin_bandas":
            return p[["yhat"]]
        elif defecto == "invertidas":
            p.loc[p.index[0], ["lo", "hi"]] = [1000, 0]
        elif defecto == "punto_fuera":
            p.loc[p.index[0], "lo"] = p.yhat.iloc[0] + 1
        else:
            columna, valor = {"yhat_nan": ("yhat", np.nan), "yhat_negativo": ("yhat", -1),
                              "lo_nan": ("lo", np.nan), "hi_inf": ("hi", np.inf),
                              "lo_negativo": ("lo", -1)}[defecto]
            p.loc[p.index[0], columna] = valor
        return p
    monkeypatch.setattr(adaptador, "pronosticar", pronosticar)
    verificar_error(generar_pronostico(serie(), 179, 8, "sarima_sin_estacional"), codigo, "convergente")


def test_desbordamiento_real_en_retransformacion_es_error(motor, monkeypatch):
    def desbordar(*args, **kwargs):
        np.expm1(np.array([1000.]))
    monkeypatch.setattr(adaptador, "pronosticar", desbordar)
    verificar_error(generar_pronostico(serie(), 179, 8, "sarima_sin_estacional"),
                    "ERROR_NUMERICO_PRONOSTICO", "convergente")


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("cola", ["sin_cola", "larga", "extremo", "texto", "faltante", "fecha_invalida"])
def test_no_anticipacion_incluye_intervalos_y_diagnosticos(motor, metodo, cola):
    s = serie(200)
    esperado = generar_pronostico(s, 170, 40, metodo)
    if cola == "sin_cola":
        s = s.iloc[:171]
    elif cola == "larga":
        s = serie(300)
    elif cola == "fecha_invalida":
        idx = list(s.index)
        idx[180] = pd.NaT
        s.index = pd.DatetimeIndex(idx)
    else:
        s = s.astype(object)
        s.iloc[171:] = {"extremo": 2**100, "texto": "invalido", "faltante": None}[cola]
    r = generar_pronostico(s, 170, 40, metodo)
    assert r == esperado
    assert len(r.predicciones) == 40


def test_resultado_sarima_y_entrada_protegidos(motor):
    s = serie()
    original = s.copy(deep=True)
    r = generar_pronostico(s, 179, 8, "sarima_sin_estacional")
    pd.testing.assert_series_equal(s, original)
    pred, ic = r.predicciones, r.intervalos
    vista_pred, vista_ic = r.predicciones, r.intervalos
    vista_pred.iloc[0, 0] = 999
    vista_ic.iloc[0, 0] = 999
    motor.resultado.mle_retvals["iterations"] = 999
    pd.testing.assert_frame_equal(r.predicciones, pred)
    pd.testing.assert_frame_equal(r.intervalos, ic)
    assert r.diagnostico_ajuste["iterations"] == 4
    with pytest.raises(TypeError):
        r.diagnostico_ajuste["converged"] = False
    with pytest.raises(FrozenInstanceError):
        r.nivel_intervalo = 0.8


@pytest.mark.parametrize("metodo", METODOS)
def test_sarima_real_converge_y_coincide_con_algoritmo_existente(monkeypatch, metodo):
    # No usa el fixture motor: se ajustan ambos modelos reales con sus ordenes de produccion.
    n = 312
    rng = np.random.default_rng(42)
    t = np.arange(n)
    s = pd.Series(rng.poisson(40 + 10 * np.sin(2 * np.pi * t / 52)).astype(float),
                  index=pd.date_range("2010-01-01", periods=n, freq="7D"))
    original = adaptador.ajustar_sarima
    ajustes = []
    def observar(*args, **kwargs):
        pd.testing.assert_series_equal(args[0], s, check_freq=False)
        res = original(*args, **kwargs)
        ajustes.append(res)
        return res
    monkeypatch.setattr(adaptador, "ajustar_sarima", observar)
    futuro = pd.Series(np.full(12, 1e12), index=pd.date_range(s.index[-1] + pd.Timedelta(days=7), periods=12, freq="7D"))
    r = generar_pronostico(pd.concat([s, futuro]), n - 1, 8, metodo)
    assert r.estado_ejecucion == "ok", (r.error, r.advertencias, r.diagnostico_ajuste)
    assert len(ajustes) == 1 and ajustes[0].mle_retvals["converged"]
    assert r.estado_ajuste == "convergente" and r.diagnostico_ajuste["parametros_finitos"]
    esperado = adaptador.pronosticar(ajustes[0], 8, r.predicciones.index, alpha=0.05)
    np.testing.assert_allclose(r.predicciones.yhat, esperado.yhat)
    np.testing.assert_allclose(r.intervalos, esperado[["lo", "hi"]])
    assert np.isfinite(r.predicciones.to_numpy()).all() and np.isfinite(r.intervalos.to_numpy()).all()
    assert (r.intervalos.lo <= r.predicciones.yhat).all() and (r.predicciones.yhat <= r.intervalos.hi).all()
    # Un NaT exclusivamente futuro elimina freq del indice global. La salida
    # completa (incluidos avisos/diagnosticos) debe permanecer igual en el motor real.
    con_fecha_futura_invalida = pd.concat([s, futuro])
    fechas = list(con_fecha_futura_invalida.index)
    fechas[-1] = pd.NaT
    con_fecha_futura_invalida.index = pd.DatetimeIndex(fechas)
    assert con_fecha_futura_invalida.index.freq is None
    repetido = generar_pronostico(con_fecha_futura_invalida, n - 1, 8, metodo)
    assert repetido == r
    assert len(ajustes) == 2
    print(f'REAL {metodo}: converged={r.diagnostico_ajuste["converged"]}, '
          f'iterations={r.diagnostico_ajuste.get("iterations")}, llf={r.diagnostico_ajuste["llf"]}, '
          f'filas={len(r.predicciones)}, nivel={r.nivel_intervalo}')
