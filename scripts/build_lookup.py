"""Genera data/processed/municipios.csv (codigo -> nombre) para el dashboard
y reports/ingest_report.json (cifras de la limpieza). Usa los 3 CSV de data/raw/.
"""
import json

import pandas as pd

from episentinel.data.ingest import cargar_eventos, limpiar

RUTAS = {210: "data/raw/Dengue_210.csv", 220: "data/raw/Dengue_220.csv", 580: "data/raw/Dengue_580.csv"}


def reparar(texto):
    """Corrige texto UTF-8 leido como cp1252 (p. ej. 'OCAÃ‘A' -> 'OCAÑA')."""
    if isinstance(texto, str) and ("Ã" in texto or "Â" in texto):
        try:
            return texto.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return texto
    return texto


raw = cargar_eventos(RUTAS)
val, reporte = limpiar(raw)

nombres = (val.sort_values("ano")
              .groupby("cod_mun")[["municipio_ocurrencia", "departamento_ocurrencia"]].last()
              .rename(columns={"municipio_ocurrencia": "municipio", "departamento_ocurrencia": "departamento"}))
nombres["municipio"] = nombres["municipio"].map(reparar).str.title()
nombres["departamento"] = nombres["departamento"].map(reparar).str.title()
nombres["cod_dpto"] = nombres.index.str[:2]
nombres.reset_index().to_csv("data/processed/municipios.csv", index=False, encoding="utf-8")

with open("reports/ingest_report.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, indent=2, ensure_ascii=False)

print(f"municipios.csv: {len(nombres)} municipios | {nombres['departamento'].nunique()} departamentos")
print(nombres.loc[["76001", "05001", "54001"]])