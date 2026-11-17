"""B06-I2: pronosticos desde un corte posicional inclusivo.

La malla de siete dias y el periodo heredado de 52 observaciones son
provisionales, pendientes de B03. No representan una decision sobre semana
53, calendario epidemiologico, territorio o ceros frente a faltantes.
Solo se inspeccionan fechas y valores del prefijo hasta el corte; nunca se
imputa, ordena o limpia la entrada. Este servicio no genera alertas.

SARIMA usa minimos operativos provisionales de 30 (sin estacionalidad) y 156
(estacional) observaciones. No garantizan suficiencia estadistica ni convergencia.
Las constantes y conversiones numericas inexactas se rechazan solo para SARIMA;
los baselines conservan la politica I1. No hay adaptacion de periodos B03/B05.
"""
from __future__ import annotations

from numbers import Integral, Real

import numpy as np
import pandas as pd

from episentinel.baselines.ingenua_estacional import (
    pronosticar_ingenua_estacional,
    pronosticar_ultimo_valor,
)

# Reexportacion compatible con las importaciones directas de I1.
from .forecast_result import (
    Advertencia, ErrorPronostico, ForecastResult, Metodo, METODOS_SARIMA, MIN_OBSERVACIONES,
)


def _es_entero(valor: object) -> bool:
    return isinstance(valor, Integral) and not isinstance(valor, (bool, np.bool_))


def generar_pronostico(
    serie: pd.Series, corte: int, horizonte: int, metodo: Metodo, *, alpha: float = 0.05,
) -> ForecastResult:
    """Devuelve exactamente horizonte pasos, sin consultar observaciones futuras.

    Errores de entrada se devuelven estructurados, en orden: serie, horizonte,
    metodo, serie vacia, corte, indice, valores, suficiencia y fechas futuras.
    alpha se aplica y valida exclusivamente para SARIMA; los baselines conservan
    intervalos y nivel nominal None. Se exige 0 < alpha < 1 y un nivel 1-alpha
    representable estrictamente entre 0 y 1. La conversion exacta se comprueba
    antes de log1p, no implica que log1p preserve distancias entre conteos grandes.
    Excepciones operativas previstas del metodo se convierten en errores;
    defectos inesperados de programacion se propagan. Los baselines no ajustan
    parametros ni ofrecen intervalos. No hay sustitucion automatica de metodo.
    """
    # Solo el contexto local de validacion es mutable. Cada salida se construye
    # completa y validada; nunca se modifica un ForecastResult ya publicado.
    contexto = {}
    estado_ejecucion = "rechazado"
    estado_ajuste = "no_ejecutado"

    def rechazar(codigo, campo, mensaje, **detalles):
        return ForecastResult(
            estado_ejecucion=estado_ejecucion, estado_ajuste=estado_ajuste,
            error=ErrorPronostico(codigo, campo, mensaje, detalles), **contexto,
        )

    if not isinstance(serie, pd.Series):
        return rechazar("SERIE_INVALIDA", "serie", "Se requiere una pd.Series")
    if not _es_entero(horizonte) or horizonte <= 0:
        return rechazar("HORIZONTE_INVALIDO", "horizonte", "Debe ser un entero positivo")
    contexto["horizonte"] = horizonte = int(horizonte)
    if not isinstance(metodo, str) or metodo not in MIN_OBSERVACIONES:
        return rechazar("METODO_INVALIDO", "metodo", "Metodo no admitido")
    contexto["metodo"] = metodo
    es_sarima = metodo in METODOS_SARIMA
    contexto["parametros"] = {"periodo_estacional": 52} if metodo == "ingenua_estacional" else {}
    if serie.empty:
        return rechazar("SERIE_VACIA", "serie", "No hay observaciones")
    if not _es_entero(corte) or not 0 <= corte < len(serie):
        return rechazar("CORTE_INVALIDO", "corte", "Debe ser una posicion valida e inclusiva")
    contexto["corte"] = corte = int(corte)
    train = serie.iloc[:corte + 1].copy(deep=True)
    contexto["n_observaciones"] = len(train)
    indice = train.index
    if not isinstance(indice, pd.DatetimeIndex) or indice.tz is not None:
        return rechazar("INDICE_INVALIDO", "serie.index", "Se requiere DatetimeIndex sin zona horaria")
    for posicion, fecha in enumerate(indice):
        if pd.isna(fecha):
            return rechazar("INDICE_INVALIDO", "serie.index", "Fecha ausente", posicion=posicion)
        if posicion and fecha <= indice[posicion - 1]:
            return rechazar("INDICE_INVALIDO", "serie.index", "Fechas duplicadas o desordenadas", posicion=posicion)
    for posicion in range(1, len(indice)):
        try:
            semanal = indice[posicion] - indice[posicion - 1] == pd.Timedelta(days=7)
        except (ValueError, OverflowError):
            semanal = False
        if not semanal:
            return rechazar("FRECUENCIA_INVALIDA", "serie.index", "B03 pendiente: se requieren pasos de siete dias", posicion=posicion)
    contexto["fecha_corte"] = indice[-1]
    contexto["advertencias"] = (Advertencia(
        "CALENDARIO_PROVISIONAL_B03", "Malla tecnica de siete dias pendiente de definicion definitiva en B03",
    ),)
    if metodo in ("ingenua_estacional", "sarima_estacional"):
        contexto["advertencias"] += (Advertencia(
            "PERIODO_ESTACIONAL_HEREDADO_52", "Se reutiliza el periodo existente de 52 observaciones; B03 pendiente",
        ),)
    if es_sarima:
        if isinstance(alpha, (bool, np.bool_)) or not isinstance(alpha, Real):
            return rechazar("ALPHA_INVALIDO", "alpha", "alpha y 1-alpha deben estar estrictamente entre 0 y 1")
        try:
            alpha = float(alpha)
        except (ValueError, OverflowError):
            return rechazar("ALPHA_INVALIDO", "alpha", "alpha no representable")
        if not np.isfinite(alpha) or not 0 < alpha < 1 or not 0 < 1 - alpha < 1:
            return rechazar("ALPHA_INVALIDO", "alpha", "alpha y 1-alpha deben estar estrictamente entre 0 y 1")
        contexto["parametros"] = {
            "order": (1, 1, 1),
            "seasonal_order": (1, 0, 1, 52) if metodo == "sarima_estacional" else (0, 0, 0, 0),
            "alpha": alpha, "transformacion": "log1p",
            "politica_historico": "sarima_min_history_v1",
            "min_observaciones": MIN_OBSERVACIONES[metodo],
        }
        contexto["advertencias"] += (Advertencia(
            "MINIMO_OPERATIVO_PROVISIONAL", "El minimo historico no garantiza suficiencia estadistica ni convergencia",
        ),)
    valores = []
    for posicion, valor in enumerate(train):
        if not isinstance(valor, Real) or isinstance(valor, (bool, np.bool_)):
            return rechazar("VALORES_INVALIDOS", "serie", "Se requieren valores numericos reales", posicion=posicion)
        try:
            numero = float(valor)
        except (ValueError, OverflowError):
            return rechazar("VALORES_INVALIDOS", "serie", "Valor no representable", posicion=posicion)
        if not np.isfinite(numero) or numero < 0:
            return rechazar("VALORES_INVALIDOS", "serie", "Valores finitos y no negativos requeridos", posicion=posicion)
        if es_sarima:
            exacto = int(numero) == int(valor) if isinstance(valor, Integral) else numero == valor
            if not exacto:
                return rechazar("PRECISION_NUMERICA_NO_ADMITIDA", "serie",
                                "Conversion a float pierde precision antes del ajuste", posicion=posicion)
        valores.append(numero)
    if metodo == "ingenua_estacional" and len(train) < 52:
        return rechazar("HISTORICO_INSUFICIENTE", "serie", "La ingenua estacional requiere 52 observaciones",
                        requeridas=52, disponibles=len(train))
    if es_sarima:
        if len(train) < MIN_OBSERVACIONES[metodo]:
            return rechazar("HISTORICO_INSUFICIENTE", "serie", "Historico inferior al minimo operativo SARIMA",
                            requeridas=MIN_OBSERVACIONES[metodo], disponibles=len(train),
                            metodo=metodo, politica="sarima_min_history_v1")
        if all(v == valores[0] for v in valores):
            return rechazar("SERIE_CONSTANTE_NO_ADMITIDA", "serie", "SARIMA no admite historicos exactamente constantes")
    try:
        fechas = pd.date_range(indice[-1] + pd.Timedelta(days=7), periods=horizonte, freq="7D", name="fecha")
    except (ValueError, OverflowError):
        return rechazar("FECHAS_FUTURAS_INVALIDAS", "horizonte", "Fechas futuras fuera del rango representable")

    # Conversion explicita del prefijo validado: el dtype global puede haber
    # cambiado a object por datos posteriores al corte.
    train = pd.Series(valores, index=indice.copy(), name=train.name, dtype=float)
    if es_sarima:
        # La frecuencia global puede perderse por fechas posteriores al corte.
        # Fijar solo metadatos del prefijo ya validado evita avisos dependientes
        # del futuro. No se generan ni modifican sus fechas o valores.
        train.index = pd.DatetimeIndex(tuple(train.index), freq="7D", name=train.index.name)
        # Importacion local: B05/B07 y los baselines no cargan este adaptador.
        from .sarima_adapter import ejecutar_sarima
        return ejecutar_sarima(train, fechas, contexto)
    estado_ajuste = "no_requiere_ajuste"
    try:
        if metodo == "ultimo_valor":
            pred = pronosticar_ultimo_valor(train, horizonte)
        else:
            pred = pronosticar_ingenua_estacional(train, horizonte, m=52)
    except (ValueError, RuntimeError, FloatingPointError, OverflowError) as exc:
        estado_ejecucion = "error"
        return rechazar("FALLO_PRONOSTICO", "metodo", "El baseline no pudo generar el pronostico",
                        tipo_excepcion=type(exc).__name__, motivo=str(exc))

    valida = isinstance(pred, pd.Series) and len(pred) == horizonte and pred.index.equals(fechas)
    if valida:
        valida = all(isinstance(v, Real) and not isinstance(v, (bool, np.bool_)) for v in pred)
    if valida:
        try:
            valores_pred = pred.to_numpy(dtype=float)
            valida = bool(np.isfinite(valores_pred).all() and (valores_pred >= 0).all())
        except (ValueError, OverflowError):
            valida = False
    if not valida:
        estado_ejecucion = "error"
        return rechazar("SALIDA_INVALIDA", "predicciones", "Salida incompatible con horizonte, fechas o valores")
    return ForecastResult(
        estado_ejecucion="ok", estado_ajuste=estado_ajuste,
        predicciones=pd.DataFrame({"yhat": valores_pred}, index=fechas), **contexto,
    )
