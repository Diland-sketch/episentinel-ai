import json
from episentinel.data.ingest import cargar_eventos, limpiar

RUTAS = {210: "data/raw/Dengue_210.csv", 220: "data/raw/Dengue_220.csv", 580: "data/raw/Dengue_580.csv"}

raw = cargar_eventos(RUTAS)
val, reporte = limpiar(raw)
val.to_parquet("data/interim/eventos_validos.parquet", index=False)

with open("reports/ingest_report.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, indent=2, ensure_ascii=False)

print(json.dumps(reporte, indent=2, ensure_ascii=False))