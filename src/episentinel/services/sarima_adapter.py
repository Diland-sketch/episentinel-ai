"""B06-I2-B: adaptador interno sobre ajustar_sarima/pronosticar existentes.

Recibe un prefijo y fechas futuras ya validados por forecast_service. No cambia
ordenes, optimizador, transformacion ni truncado a cero del algoritmo historico.
No reintenta ni sustituye modelos. Captura advertencias por fase; solo permite
avisos conocidos de frecuencia inferida e inicializacion AR/MA, condicionados a
un ajuste final valido. Avisos desconocidos, numericos o de covarianza bloquean.

El punto es expm1 de la media logaritmica (sin correccion de retrans formacion),
no una media de conteos garantizada. Bandas nominales transformadas y truncadas;
no acreditan calibracion ni incluyen toda la incertidumbre de parametros/modelo.
Los diagnosticos son un resumen de escalares, no el objeto mutable de statsmodels.
"""
from __future__ import annotations

from collections.abc import Mapping
from numbers import Integral, Real
import re
import warnings

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning, ValueWarning

from episentinel.models.sarima import ajustar_sarima, pronosticar
from .forecast_result import Advertencia, ErrorPronostico, ForecastResult

_NUMERICAS = (np.linalg.LinAlgError, FloatingPointError, OverflowError)
_OPERATIVAS = (ValueError, RuntimeError, *_NUMERICAS)


def _clasificar_aviso(aviso):
    mensaje = str(aviso.message)
    if issubclass(aviso.category, ConvergenceWarning):
        return "NO_CONVERGENCIA"
    if issubclass(aviso.category, RuntimeWarning):
        return "ADVERTENCIA_NUMERICA"
    if issubclass(aviso.category, ValueWarning) and re.fullmatch(
        r"No frequency information was provided, so inferred frequency "
        r"(7D|W-(MON|TUE|WED|THU|FRI|SAT|SUN)) will be used\.", mensaje
    ):
        return "FRECUENCIA_INFERIDA"
    inicios = (
        "Non-stationary starting autoregressive parameters found.",
        "Non-invertible starting MA parameters found.",
        "Non-stationary starting seasonal autoregressive",
        "Non-invertible starting seasonal moving average",
    )
    if aviso.category is UserWarning and mensaje.startswith(inicios) and "zeros" in mensaje.lower():
        return "INICIALIZACION_SARIMA"
    return "ADVERTENCIA_BLOQUEANTE"


def _avisos(registro, fase):
    return tuple(Advertencia(_clasificar_aviso(w), f"{w.category.__name__}: {w.message}", fase)
                 for w in registro)


def _diagnostico(resultado):
    retvals = getattr(resultado, "mle_retvals", None)
    retvals = retvals if isinstance(retvals, Mapping) else {}
    indicador = retvals.get("converged")
    converged = bool(indicador) if isinstance(indicador, (bool, np.bool_)) else None
    llf_original = getattr(resultado, "llf", None)
    params_originales = getattr(resultado, "params", None)
    try:
        llf = float(llf_original) if isinstance(llf_original, Real) and not isinstance(llf_original, (bool, np.bool_)) else None
        params = np.asarray(params_originales)
        parametros_reales = (params.ndim == 1 and params.size > 0
                             and all(isinstance(v, Real) and not isinstance(v, (bool, np.bool_)) for v in params))
        parametros_finitos = parametros_reales and bool(np.isfinite(params.astype(float)).all())
    except (TypeError, ValueError, OverflowError):
        llf, parametros_finitos = None, False
    llf = llf if llf is not None and np.isfinite(llf) else None
    diagnostico = {"converged": converged, "llf": llf, "parametros_finitos": parametros_finitos}
    # Claves opcionales del optimizador: no se fabrica un numero de iteraciones.
    for clave in ("iterations", "warnflag", "fcalls"):
        valor = retvals.get(clave)
        if isinstance(valor, Integral) and not isinstance(valor, (bool, np.bool_)):
            diagnostico[clave] = int(valor)
    return diagnostico


def _valores_validos(columna):
    for valor in columna:
        if not isinstance(valor, Real) or isinstance(valor, (bool, np.bool_)):
            return False
        try:
            numero = float(valor)
        except (ValueError, OverflowError):
            return False
        if not np.isfinite(numero) or numero < 0:
            return False
    return True


def ejecutar_sarima(train: pd.Series, fechas: pd.DatetimeIndex, contexto: dict) -> ForecastResult:
    """Ejecuta una sola vez cada fase; contexto contiene parametros validados."""
    parametros = contexto["parametros"]
    contexto = dict(contexto)
    advertencias = tuple(contexto.pop("advertencias", ()))
    diagnostico = {"converged": None, "llf": None, "parametros_finitos": None}

    def fallo(codigo, ajuste, fase, mensaje, exc=None):
        detalles = {"fase": fase}
        if exc is not None:
            detalles.update(tipo_excepcion=type(exc).__name__, motivo=str(exc))
        return ForecastResult(
            estado_ejecucion="error", estado_ajuste=ajuste,
            diagnostico_ajuste=diagnostico, advertencias=advertencias,
            error=ErrorPronostico(codigo, "metodo", mensaje, detalles), **contexto,
        )

    excepcion = None
    with warnings.catch_warnings(record=True) as registro:
        warnings.simplefilter("always")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                resultado = ajustar_sarima(train, order=parametros["order"], seasonal_order=parametros["seasonal_order"])
        except _OPERATIVAS as exc:
            excepcion = exc
    avisos_ajuste = _avisos(registro, "ajuste")
    advertencias += avisos_ajuste
    if excepcion is not None:
        codigo = "ERROR_NUMERICO_AJUSTE" if isinstance(excepcion, _NUMERICAS) else "FALLO_AJUSTE"
        return fallo(codigo, "fallido", "ajuste", "No se pudo completar el ajuste SARIMA", excepcion)
    diagnostico = _diagnostico(resultado)
    if diagnostico["llf"] is None or not diagnostico["parametros_finitos"]:
        return fallo("AJUSTE_NUMERICO_INVALIDO", "fallido", "ajuste", "Parametros o log-verosimilitud no finitos")
    converged = diagnostico["converged"]
    aviso_convergencia = any(a.codigo == "NO_CONVERGENCIA" for a in avisos_ajuste)
    if converged is True and (aviso_convergencia or diagnostico.get("warnflag", 0) != 0):
        return fallo("CONVERGENCIA_NO_VERIFICABLE", "no_verificado", "ajuste", "Diagnosticos de convergencia contradictorios")
    if converged is False or aviso_convergencia:
        return fallo("NO_CONVERGENCIA", "no_convergente", "ajuste", "El ajuste no convergio")
    if converged is not True:
        return fallo("CONVERGENCIA_NO_VERIFICABLE", "no_verificado", "ajuste", "No hay indicador booleano de convergencia")
    if any(a.codigo == "ADVERTENCIA_NUMERICA" for a in avisos_ajuste):
        return fallo("ERROR_NUMERICO_AJUSTE", "fallido", "ajuste", "Advertencia numerica durante el ajuste")
    if any(a.codigo == "ADVERTENCIA_BLOQUEANTE" for a in avisos_ajuste):
        return fallo("ADVERTENCIA_AJUSTE_BLOQUEANTE", "convergente", "ajuste", "Advertencia de ajuste no permitida")

    excepcion = None
    with warnings.catch_warnings(record=True) as registro:
        warnings.simplefilter("always")
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
                pred = pronosticar(resultado, pasos=contexto["horizonte"], fechas=fechas, alpha=parametros["alpha"])
        except _OPERATIVAS as exc:
            excepcion = exc
    avisos_pronostico = _avisos(registro, "pronostico")
    advertencias += avisos_pronostico
    if excepcion is not None:
        codigo = "ERROR_NUMERICO_PRONOSTICO" if isinstance(excepcion, _NUMERICAS) else "FALLO_PRONOSTICO"
        return fallo(codigo, "convergente", "pronostico", "No se pudo completar el pronostico SARIMA", excepcion)
    if any(a.codigo == "ADVERTENCIA_NUMERICA" for a in avisos_pronostico):
        return fallo("ERROR_NUMERICO_PRONOSTICO", "convergente", "pronostico", "Advertencia numerica en el pronostico")
    if any(a.codigo not in ("FRECUENCIA_INFERIDA",) for a in avisos_pronostico):
        return fallo("ADVERTENCIA_PRONOSTICO_BLOQUEANTE", "convergente", "pronostico", "Advertencia de pronostico no permitida")

    if (not isinstance(pred, pd.DataFrame) or not pred.columns.is_unique or "yhat" not in pred
            or len(pred) != contexto["horizonte"] or not pred.index.equals(fechas)):
        return fallo("SALIDA_INVALIDA", "convergente", "pronostico", "Estructura, longitud o fechas incompatibles")
    if not _valores_validos(pred["yhat"]):
        return fallo("RESULTADO_NUMERICO_INVALIDO", "convergente", "pronostico", "Predicciones no finitas o invalidas")
    if "lo" not in pred or "hi" not in pred:
        return fallo("INTERVALO_INVALIDO", "convergente", "pronostico", "Faltan bandas de prediccion")
    if not _valores_validos(pred["lo"]) or not _valores_validos(pred["hi"]):
        return fallo("INTERVALO_INVALIDO", "convergente", "pronostico", "Bandas no finitas o invalidas")
    if not ((pred["lo"] <= pred["yhat"]) & (pred["yhat"] <= pred["hi"])).all():
        return fallo("INTERVALO_INVALIDO", "convergente", "pronostico", "Bandas no cumplen lo <= yhat <= hi")
    if set(pred.columns) != {"yhat", "lo", "hi"}:
        return fallo("SALIDA_INVALIDA", "convergente", "pronostico", "Columnas de salida inesperadas")
    return ForecastResult(
        estado_ejecucion="ok", estado_ajuste="convergente", diagnostico_ajuste=diagnostico,
        nivel_intervalo=1 - parametros["alpha"], predicciones=pred[["yhat"]],
        intervalos=pred[["lo", "hi"]], advertencias=advertencias, **contexto,
    )
