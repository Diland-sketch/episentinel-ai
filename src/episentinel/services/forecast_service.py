"""B06-I1: pronosticos desde un corte posicional inclusivo.

La malla de siete dias y el periodo heredado de 52 observaciones son
provisionales, pendientes de B03. No representan una decision sobre semana
53, calendario epidemiologico, territorio o ceros frente a faltantes.
Solo se inspeccionan fechas y valores del prefijo hasta el corte; nunca se
imputa, ordena o limpia la entrada. Este servicio no genera alertas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Integral, Real
from typing import Literal

import numpy as np
import pandas as pd

from episentinel.baselines.ingenua_estacional import (
    pronosticar_ingenua_estacional,
    pronosticar_ultimo_valor,
)

Metodo = Literal["ultimo_valor", "ingenua_estacional"]


@dataclass(frozen=True)
class Advertencia:
    codigo: str
    mensaje: str


@dataclass(frozen=True)
class ErrorPronostico:
    codigo: str
    campo: str
    mensaje: str
    detalles: dict[str, object] = field(default_factory=dict)


def _predicciones_vacias() -> pd.DataFrame:
    return pd.DataFrame({"yhat": pd.Series(dtype=float)},
                        index=pd.DatetimeIndex([], name="fecha"))


@dataclass
class ForecastResult:
    estado_ejecucion: Literal["ok", "rechazado", "error"] = "rechazado"
    estado_ajuste: Literal["no_ejecutado", "no_requiere_ajuste"] = "no_ejecutado"
    metodo: Metodo | None = None
    corte: int | None = None
    fecha_corte: pd.Timestamp | None = None
    horizonte: int | None = None
    n_observaciones: int = 0
    predicciones: pd.DataFrame = field(default_factory=_predicciones_vacias)
    intervalos: pd.DataFrame | None = None
    parametros: dict[str, int] = field(default_factory=dict)
    advertencias: tuple[Advertencia, ...] = ()
    error: ErrorPronostico | None = None

    def __post_init__(self):
        # Invariante del contrato, tambien para futuros adaptadores con bandas.
        if self.intervalos is not None and not self.intervalos.index.identical(self.predicciones.index):
            raise ValueError("Intervalos y predicciones deben compartir el mismo indice temporal")


def _es_entero(valor: object) -> bool:
    return isinstance(valor, Integral) and not isinstance(valor, (bool, np.bool_))


def generar_pronostico(
    serie: pd.Series, corte: int, horizonte: int, metodo: Metodo,
) -> ForecastResult:
    """Devuelve exactamente horizonte pasos, sin consultar observaciones futuras.

    Errores de entrada se devuelven estructurados, en orden: serie, horizonte,
    metodo, serie vacia, corte, indice, valores, suficiencia y fechas futuras.
    Excepciones operativas previstas del baseline se convierten en errores;
    defectos inesperados de programacion se propagan. Los baselines no ajustan
    parametros ni ofrecen intervalos. No hay sustitucion automatica de metodo.
    """
    salida = ForecastResult()

    def rechazar(codigo, campo, mensaje, **detalles):
        salida.error = ErrorPronostico(codigo, campo, mensaje, detalles)
        return salida

    if not isinstance(serie, pd.Series):
        return rechazar("SERIE_INVALIDA", "serie", "Se requiere una pd.Series")
    if not _es_entero(horizonte) or horizonte <= 0:
        return rechazar("HORIZONTE_INVALIDO", "horizonte", "Debe ser un entero positivo")
    salida.horizonte = horizonte = int(horizonte)
    if not isinstance(metodo, str) or metodo not in ("ultimo_valor", "ingenua_estacional"):
        return rechazar("METODO_INVALIDO", "metodo", "Metodo no admitido")
    salida.metodo = metodo
    salida.parametros = {"periodo_estacional": 52} if metodo == "ingenua_estacional" else {}
    if serie.empty:
        return rechazar("SERIE_VACIA", "serie", "No hay observaciones")
    if not _es_entero(corte) or not 0 <= corte < len(serie):
        return rechazar("CORTE_INVALIDO", "corte", "Debe ser una posicion valida e inclusiva")
    salida.corte = corte = int(corte)
    train = serie.iloc[:corte + 1].copy(deep=True)
    salida.n_observaciones = len(train)
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
    salida.fecha_corte = indice[-1]
    salida.advertencias = (Advertencia(
        "CALENDARIO_PROVISIONAL_B03", "Malla tecnica de siete dias pendiente de definicion definitiva en B03",
    ),)
    if metodo == "ingenua_estacional":
        salida.advertencias += (Advertencia(
            "PERIODO_ESTACIONAL_HEREDADO_52", "Se reutiliza el periodo existente de 52 observaciones; B03 pendiente",
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
        valores.append(numero)
    if metodo == "ingenua_estacional" and len(train) < 52:
        return rechazar("HISTORICO_INSUFICIENTE", "serie", "La ingenua estacional requiere 52 observaciones",
                        requeridas=52, disponibles=len(train))
    try:
        fechas = pd.date_range(indice[-1] + pd.Timedelta(days=7), periods=horizonte, freq="7D", name="fecha")
    except (ValueError, OverflowError):
        return rechazar("FECHAS_FUTURAS_INVALIDAS", "horizonte", "Fechas futuras fuera del rango representable")

    # Conversion explicita del prefijo validado: el dtype global puede haber
    # cambiado a object por datos posteriores al corte.
    train = pd.Series(valores, index=indice.copy(), name=train.name, dtype=float)
    salida.estado_ajuste = "no_requiere_ajuste"
    try:
        if metodo == "ultimo_valor":
            pred = pronosticar_ultimo_valor(train, horizonte)
        else:
            pred = pronosticar_ingenua_estacional(train, horizonte, m=52)
    except (ValueError, RuntimeError, FloatingPointError, OverflowError) as exc:
        salida.estado_ejecucion = "error"
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
        salida.estado_ejecucion = "error"
        return rechazar("SALIDA_INVALIDA", "predicciones", "Salida incompatible con horizonte, fechas o valores")
    salida.predicciones = pd.DataFrame({"yhat": valores_pred}, index=fechas)
    salida.estado_ejecucion = "ok"
    return salida
