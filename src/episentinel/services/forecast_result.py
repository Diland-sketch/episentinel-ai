"""B06-I2: resultado atomico con instantaneas inmutables.

Compatibilidad con I1: se conservan los nombres publicos y las vistas pandas
predicciones/intervalos. Incompatibilidades intencionadas: ForecastResult exige
estados explicitos y argumentos por nombre; no admite construccion vacia seguida
de asignaciones. Un constructor incoherente lanza TypeError/ValueError (el servicio
sigue devolviendo errores estructurados para entradas invalidas).

Cada acceso a una tabla crea una copia independiente. Los mappings se congelan
recursivamente y listas/tuplas se convierten a tuplas; solo se admiten metadatos
con claves de texto y valores escalares simples o colecciones de esos valores.
No se garantiza identidad de DataFrames, campos de dataclasses, asdict, pickle
ni serializacion JSON directa de los mappings. No se exponen buffers compartidos.

La malla de siete dias sigue siendo provisional, pendiente de B03. Los intervalos
SARIMA tienen nivel nominal, no acreditan calibracion ni deteccion de brotes.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from numbers import Integral, Real
from types import MappingProxyType
from typing import Literal

import numpy as np
import pandas as pd

Metodo = Literal["ultimo_valor", "ingenua_estacional", "sarima_estacional", "sarima_sin_estacional"]
METODOS_SARIMA = ("sarima_estacional", "sarima_sin_estacional")
# Politica operativa provisional: no garantiza suficiencia estadistica ni
# convergencia. 156 son tres bloques de 52 observaciones, no tres anios oficiales.
MIN_OBSERVACIONES = MappingProxyType({
    "ultimo_valor": 1, "ingenua_estacional": 52,
    "sarima_sin_estacional": 30, "sarima_estacional": 156,
})


def _texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{campo} debe ser texto no vacio")


def _congelar(valor, activos=None):
    """Copia recursiva; rechaza objetos arbitrarios y colecciones ciclicas."""
    if activos is None:
        activos = set()
    if valor is None or type(valor) in (str, bool, int, float):
        return valor
    if isinstance(valor, np.generic):
        convertido = valor.item()
        if type(convertido) in (str, bool, int, float):
            return convertido
        raise TypeError("Escalar de metadatos no admitido")
    if not isinstance(valor, (Mapping, tuple, list)):
        raise TypeError("Metadatos requieren escalares simples, mappings, listas o tuplas")
    identidad = id(valor)
    if identidad in activos:
        raise ValueError("Metadatos ciclicos no admitidos")
    activos.add(identidad)
    try:
        if isinstance(valor, Mapping):
            if any(type(clave) is not str for clave in valor):
                raise TypeError("Las claves de metadatos deben ser texto")
            return MappingProxyType({k: _congelar(v, activos) for k, v in valor.items()})
        return tuple(_congelar(v, activos) for v in valor)
    finally:
        activos.remove(identidad)


def _mapping(valor):
    if not isinstance(valor, Mapping):
        raise TypeError("Se requiere un mapping de metadatos")
    return _congelar(valor)


@dataclass(frozen=True, slots=True)
class Advertencia:
    codigo: str
    mensaje: str
    fase: Literal["validacion", "ajuste", "pronostico"] = "validacion"

    def __post_init__(self):
        _texto(self.codigo, "codigo")
        _texto(self.mensaje, "mensaje")
        if self.fase not in ("validacion", "ajuste", "pronostico"):
            raise ValueError("Fase de advertencia invalida")


@dataclass(frozen=True, slots=True)
class ErrorPronostico:
    codigo: str
    campo: str
    mensaje: str
    detalles: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        for nombre in ("codigo", "campo", "mensaje"):
            _texto(getattr(self, nombre), nombre)
        object.__setattr__(self, "detalles", _mapping(self.detalles))


def _entero(valor, campo, minimo):
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Integral) or valor < minimo:
        raise ValueError(f"{campo} debe ser un entero >= {minimo}")
    return int(valor)


def _columna(tabla, nombre):
    valores = []
    for valor in tabla[nombre]:
        if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
            raise ValueError(f"{nombre} debe contener numeros reales")
        try:
            numero = float(valor)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"{nombre} no representable") from exc
        if not np.isfinite(numero) or numero < 0:
            raise ValueError(f"{nombre} debe ser finito y no negativo")
        valores.append(numero)
    return tuple(valores)


@dataclass(frozen=True, slots=True, init=False)
class ForecastResult:
    """Resultado validado; tablas de salida independientes en cada lectura.

    Un error de pronostico puede conservar un ajuste convergente. Los baselines
    mantienen los estados de I1, sin diagnostico de optimizacion ni nivel nominal.
    Sus intervalos opcionales en construccion directa no implican que el servicio
    los calcule. Un exito SARIMA exige diagnostico convergente e intervalos.
    """

    estado_ejecucion: Literal["ok", "rechazado", "error"]
    estado_ajuste: Literal["no_ejecutado", "no_requiere_ajuste", "convergente",
                          "no_convergente", "no_verificado", "fallido"]
    metodo: Metodo | None
    corte: int | None
    fecha_corte: pd.Timestamp | None
    horizonte: int | None
    n_observaciones: int
    parametros: Mapping[str, object]
    advertencias: tuple[Advertencia, ...]
    error: ErrorPronostico | None
    diagnostico_ajuste: Mapping[str, object] | None
    nivel_intervalo: float | None
    _fechas: tuple[pd.Timestamp, ...]
    _yhat: tuple[float, ...]
    _bandas: tuple[tuple[float, ...], tuple[float, ...]] | None

    def __init__(
        self, *, estado_ejecucion, estado_ajuste, metodo=None, corte=None,
        fecha_corte=None, horizonte=None, n_observaciones=0, predicciones=None,
        intervalos=None, parametros=None, advertencias=(), error=None,
        diagnostico_ajuste=None, nivel_intervalo=None,
    ):
        if estado_ejecucion not in ("ok", "rechazado", "error"):
            raise ValueError("Estado de ejecucion invalido")
        estados_sarima = ("convergente", "no_convergente", "no_verificado", "fallido")
        if estado_ajuste not in ("no_ejecutado", "no_requiere_ajuste", *estados_sarima):
            raise ValueError("Estado de ajuste invalido")
        if metodo is not None and metodo not in MIN_OBSERVACIONES:
            raise ValueError("Metodo invalido")
        es_sarima = metodo in METODOS_SARIMA
        if diagnostico_ajuste is not None:
            diagnostico_ajuste = _mapping(diagnostico_ajuste)
        if nivel_intervalo is not None:
            if isinstance(nivel_intervalo, (bool, np.bool_)) or not isinstance(nivel_intervalo, Real):
                raise ValueError("Nivel nominal de intervalo invalido")
            try:
                nivel_intervalo = float(nivel_intervalo)
            except (ValueError, OverflowError) as exc:
                raise ValueError("Nivel nominal de intervalo no representable") from exc
            if not np.isfinite(nivel_intervalo) or not 0 < nivel_intervalo < 1:
                raise ValueError("Nivel nominal de intervalo invalido")
        if not es_sarima:
            if estado_ajuste in estados_sarima or diagnostico_ajuste is not None or nivel_intervalo is not None:
                raise ValueError("Un baseline no admite diagnosticos ni estados SARIMA")
        elif estado_ajuste == "no_ejecutado":
            if diagnostico_ajuste is not None:
                raise ValueError("Un ajuste no ejecutado no tiene diagnostico")
        else:
            if estado_ajuste not in estados_sarima or diagnostico_ajuste is None:
                raise ValueError("SARIMA ejecutado requiere estado y diagnostico de ajuste")
            if "converged" not in diagnostico_ajuste:
                raise ValueError("Diagnostico requiere converged (bool o None)")
            converged = diagnostico_ajuste["converged"]
            if converged is not None and type(converged) is not bool:
                raise ValueError("Indicador de convergencia invalido")
            if estado_ajuste == "convergente" and converged is not True:
                raise ValueError("Ajuste convergente requiere indicador positivo")
            if estado_ajuste == "no_convergente" and converged is True:
                raise ValueError("Ajuste no convergente contradice el diagnostico")
        n_observaciones = _entero(n_observaciones, "n_observaciones", 0)
        if corte is not None:
            corte = _entero(corte, "corte", 0)
        if horizonte is not None:
            horizonte = _entero(horizonte, "horizonte", 1)
        if (corte is None and n_observaciones != 0) or (corte is not None and n_observaciones != corte + 1):
            raise ValueError("Corte y numero de observaciones incoherentes")
        if fecha_corte is not None:
            if not isinstance(fecha_corte, pd.Timestamp) or pd.isna(fecha_corte) or fecha_corte.tz is not None:
                raise ValueError("fecha_corte requiere Timestamp valido sin zona horaria")
            if corte is None:
                raise ValueError("Una fecha de corte requiere posicion de corte")
        if error is not None and not isinstance(error, ErrorPronostico):
            raise TypeError("error debe ser ErrorPronostico o None")
        if not isinstance(advertencias, (tuple, list)) or any(not isinstance(a, Advertencia) for a in advertencias):
            raise TypeError("advertencias requiere una lista o tupla de Advertencia")
        parametros = _mapping({} if parametros is None else parametros)
        if metodo is None and parametros:
            raise ValueError("Parametros requieren un metodo validado")

        if predicciones is None:
            predicciones = pd.DataFrame({"yhat": pd.Series(dtype=float)}, index=pd.DatetimeIndex([], name="fecha"))
        if not isinstance(predicciones, pd.DataFrame):
            raise TypeError("predicciones debe ser DataFrame")
        if list(predicciones.columns) != ["yhat"]:
            raise ValueError("predicciones requiere exclusivamente yhat")
        indice = predicciones.index
        if not isinstance(indice, pd.DatetimeIndex) or indice.tz is not None or indice.hasnans:
            raise ValueError("Predicciones requieren DatetimeIndex valido sin zona horaria")
        yhat = _columna(predicciones, "yhat")
        bandas = None
        if intervalos is not None:
            if not isinstance(intervalos, pd.DataFrame):
                raise TypeError("intervalos debe ser DataFrame o None")
            if not intervalos.index.identical(indice):
                raise ValueError("Intervalos y predicciones deben compartir el mismo indice temporal")
            if list(intervalos.columns) != ["lo", "hi"]:
                raise ValueError("intervalos requiere exclusivamente lo y hi")
            lo, hi = _columna(intervalos, "lo"), _columna(intervalos, "hi")
            if any(not inferior <= punto <= superior for inferior, punto, superior in zip(lo, yhat, hi)):
                raise ValueError("Bandas deben cumplir lo <= yhat <= hi")
            bandas = (lo, hi)

        if estado_ejecucion == "ok":
            ajuste_exitoso = "convergente" if es_sarima else "no_requiere_ajuste"
            if error is not None or estado_ajuste != ajuste_exitoso:
                raise ValueError("Exito requiere ausencia de error y estado de ajuste coherente")
            if metodo is None or corte is None or fecha_corte is None or horizonte is None:
                raise ValueError("Exito requiere metadatos completos")
            minimo = MIN_OBSERVACIONES[metodo]
            if n_observaciones < minimo or len(yhat) != horizonte:
                raise ValueError("Historico u horizonte incoherente")
            try:
                esperado = pd.date_range(fecha_corte + pd.Timedelta(days=7), periods=horizonte, freq="7D")
            except (ValueError, OverflowError) as exc:
                raise ValueError("Fechas futuras no representables") from exc
            if not indice.equals(esperado):
                raise ValueError("Fechas de prediccion incompatibles con corte y horizonte")
            if es_sarima:
                if bandas is None or nivel_intervalo is None:
                    raise ValueError("Exito SARIMA requiere intervalos y su nivel nominal")
                llf = diagnostico_ajuste.get("llf")
                if (isinstance(llf, bool) or not isinstance(llf, Real) or not np.isfinite(llf)
                        or diagnostico_ajuste.get("parametros_finitos") is not True):
                    raise ValueError("Exito SARIMA requiere diagnostico numerico valido")
        else:
            if error is None or yhat or intervalos is not None or nivel_intervalo is not None:
                raise ValueError("Un resultado no exitoso requiere error y ausencia de predicciones/intervalos")
            if estado_ejecucion == "rechazado" and estado_ajuste != "no_ejecutado":
                raise ValueError("Rechazo requiere ajuste no ejecutado")
            if estado_ejecucion == "error":
                ajustes_error = estados_sarima if es_sarima else ("no_requiere_ajuste",)
                if estado_ajuste not in ajustes_error or any(v is None for v in (metodo, corte, fecha_corte, horizonte)):
                    raise ValueError("Error de ejecucion requiere metadatos y estado de ajuste coherentes")

        valores = dict(estado_ejecucion=estado_ejecucion, estado_ajuste=estado_ajuste,
                       metodo=metodo, corte=corte, fecha_corte=fecha_corte,
                       horizonte=horizonte, n_observaciones=n_observaciones,
                       parametros=parametros, advertencias=tuple(advertencias), error=error,
                       diagnostico_ajuste=diagnostico_ajuste, nivel_intervalo=nivel_intervalo,
                       _fechas=tuple(indice), _yhat=yhat, _bandas=bandas)
        for nombre, valor in valores.items():
            object.__setattr__(self, nombre, valor)

    def _indice(self):
        return pd.DatetimeIndex(self._fechas, name="fecha", freq="7D" if self._fechas else None)

    @property
    def predicciones(self) -> pd.DataFrame:
        return pd.DataFrame({"yhat": self._yhat}, index=self._indice(), dtype=float)

    @property
    def intervalos(self) -> pd.DataFrame | None:
        if self._bandas is None:
            return None
        return pd.DataFrame({"lo": self._bandas[0], "hi": self._bandas[1]}, index=self._indice(), dtype=float)
