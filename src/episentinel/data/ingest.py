"""Ingesta y limpieza de los 3 CSV reales de SIVIGILA (tarea A3).

Cada archivo corresponde a un evento (210 dengue, 220 dengue grave,
580 mortalidad por dengue), exportado con comillas y separador de miles
en los campos numéricos (ej. el año llega como "2,013").
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EVENTOS_VALIDOS = {210, 220, 580}
COLS_NUM = ["cod_eve", "semana", "ano", "cod_dpto_o", "cod_mun_o", "conteo"]


def leer_csv_sivigila(ruta: str) -> pd.DataFrame:
    d = pd.read_csv(ruta, dtype=str, sep=",", quotechar='"', encoding="utf-8-sig")
    if d.shape[1] == 1:
        d = pd.read_csv(ruta, dtype=str, sep=None, engine="python", encoding="utf-8-sig")
    d.columns = d.columns.str.strip().str.lower()
    return d


def cargar_eventos(rutas: dict[int, str]) -> pd.DataFrame:
    """rutas: {210: 'Dengue_210.csv', 220: 'Dengue_220.csv', 580: 'Dengue_580.csv'}"""
    partes = [leer_csv_sivigila(r) for r in rutas.values()]
    raw = pd.concat(partes, ignore_index=True)
    for c in COLS_NUM:
        raw[c] = raw[c].str.replace(",", "", regex=False).str.strip()
    return raw


def limpiar(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Devuelve (filas_validas, reporte). El reporte es serializable a JSON."""
    n_crudo = len(raw)

    ajenas = ~raw["cod_eve"].astype(float).isin(EVENTOS_VALIDOS)
    n_ajenas = int(ajenas.sum())
    eventos_ajenos = raw.loc[ajenas, "cod_eve"].value_counts().to_dict() if n_ajenas else {}
    df = raw[~ajenas].copy()

    for c in COLS_NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    mun, dpto = df["cod_mun_o"], df["cod_dpto_o"]
    codigo = pd.Series(np.where(mun < 1000, dpto * 1000 + mun, mun), index=df.index)
    df["cod_mun"] = codigo.round().astype("Int64").astype("string").str.zfill(5)
    df["cod_dpto"] = df["cod_mun"].str[:2]

    mun_ok = df["cod_mun"].notna() & ~df["cod_mun"].fillna("00000").str.endswith("000")
    valido = (
        df["semana"].between(1, 53)
        & df["ano"].notna()
        & mun_ok
        & df["conteo"].notna()
        & (df["conteo"] >= 0)
    )
    val = df[valido].copy()

    reporte = {
        "filas_crudas": n_crudo,
        "filas_ajenas_excluidas": n_ajenas,
        "eventos_ajenos": eventos_ajenos,
        "filas_tras_excluir_ajenas": int(len(df)),
        "filas_invalidas_adicionales": int((~valido).sum()),
        "filas_validas_para_panel": int(len(val)),
        "filas_validas_por_evento": val["cod_eve"].value_counts().astype(int).to_dict(),
        "municipios_unicos_dataset_completo": int(df["cod_mun"].nunique()),
        "municipios_unicos_filas_validas": int(val["cod_mun"].nunique()),
        "periodo": [int(val["ano"].min()), int(val["ano"].max())],
        "suma_conteo_casos_210_220": float(val.loc[val["cod_eve"].isin([210, 220]), "conteo"].sum()),
        "suma_conteo_mortalidad_580": float(val.loc[val["cod_eve"] == 580, "conteo"].sum()),
        "filas_clave_duplicada": int(val.duplicated(["cod_eve", "ano", "semana", "cod_mun"], keep=False).sum()),
        "filas_semana_53": int((val["semana"] == 53).sum()),
    }
    return val, reporte


def construir_panel(val: pd.DataFrame, eventos: list[int], plegar_semana_53: bool = True) -> pd.DataFrame:
    """Panel municipio x semana para los eventos dados (p. ej. [210, 220] o [580]).

    Contrato: filas = cod_mun (texto 5 dígitos), columnas = DatetimeIndex
    semanal, valores enteros. Semana 53 se pliega a la 52 (decisión heredada
    de la Fase 1; ver P-05 en DECISIONES_TECNICAS.md si se revisa).
    """
    d = val[val["cod_eve"].isin(eventos)].copy()
    sem = d["semana"].clip(upper=52) if plegar_semana_53 else d["semana"]
    y0 = int(d["ano"].min())
    d["t"] = ((d["ano"] - y0) * 52 + sem - 1).astype(int)

    T = int(d["t"].max()) + 1
    fechas = pd.date_range(f"{y0}-01-01", periods=T, freq="7D")

    panel = d.groupby(["cod_mun", "t"])["conteo"].sum().unstack(fill_value=0)
    panel = panel.reindex(columns=range(T), fill_value=0)
    panel.columns = fechas
    return panel.astype("int64")