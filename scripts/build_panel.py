"""Tarea A6: construir el panel real y los archivos de configuracion
que consumen B y C (contrato en PAQUETE_EQUIPO_EPISENTINEL.md, seccion 2.2).
"""
import json
import pandas as pd

from episentinel.data.ingest import cargar_eventos, limpiar, construir_panel

RUTAS = {210: "data/raw/Dengue_210.csv", 220: "data/raw/Dengue_220.csv", 580: "data/raw/Dengue_580.csv"}
N_MUNICIPIOS = 30  # top-N por casos acumulados, entre los elegibles (>=52 semanas con casos en train)
TRAIN_END = 727    # ver configs/split.json

raw = cargar_eventos(RUTAS)
val, reporte = limpiar(raw)

panel_casos = construir_panel(val, eventos=[210, 220])
panel_muertes = construir_panel(val, eventos=[580])
panel_casos.to_parquet("data/processed/panel_casos.parquet")
panel_muertes.to_parquet("data/processed/panel_muertes.parquet")

# --- series_seleccionadas.csv ---
train_panel = panel_casos.iloc[:, : TRAIN_END + 1]
sem_con_casos = (train_panel > 0).sum(axis=1)
elegibles = sem_con_casos[sem_con_casos >= 52].index

top_mun = panel_casos.loc[elegibles].sum(axis=1).sort_values(ascending=False).head(N_MUNICIPIOS).index
cod_dpto = pd.Series(top_mun, index=top_mun).str[:2]

deptos_val = val.copy()
deptos_val["cod_dpto"] = deptos_val["cod_mun"].str[:2]
deptos_unicos = sorted(deptos_val["cod_dpto"].dropna().unique())

filas = [{"unit": "nacional", "tipo": "nacional", "cod": ""}]
filas += [{"unit": f"dpto_{c}", "tipo": "departamento", "cod": c} for c in deptos_unicos]
filas += [{"unit": f"mun_{c}", "tipo": "municipio", "cod": c} for c in top_mun]

pd.DataFrame(filas).to_csv("configs/series_seleccionadas.csv", index=False)

print(f"Panel casos: {panel_casos.shape} | Panel muertes: {panel_muertes.shape}")
print(f"Series seleccionadas: 1 nacional + {len(deptos_unicos)} departamentos + {len(top_mun)} municipios = {1+len(deptos_unicos)+len(top_mun)}")

with open("reports/ingest_report.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, indent=2, ensure_ascii=False)