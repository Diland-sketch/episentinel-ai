# Estado del proyecto

## 2026-10-26 — Pista A

- Qué se hizo: validado el pipeline de ingesta con los 3 CSV reales; construido configs/split.json y el script build_panel.py (A6).
- Qué se decidió (y por qué): train=2007-2020 (14 años), val=2021, test=2022 — deja un año completo de prueba y uno de validación, sin tocar el patrón multianual de brotes. Alcance de series: nacional + 34 departamentos + top 30 municipios elegibles (692 municipios cubren 99,1% de los casos pero no son viables de ajustar en 3 días; 65 series sí lo son).
- Archivos cambiados: configs/split.json, scripts/build_panel.py, src/episentinel/data/ingest.py.
- Resultados (origen: real): panel de casos 1.124 municipios x 832 semanas (2007-2022); 219.083 filas válidas de 223.651 crudas; 1.124 municipios válidos (de 1.158 con códigos inválidos incluidos).
- Problemas abiertos: cifra de "1.194.662 casos" de la presentación de Fase 1 no coincide con la suma real recalculada (1.186.504); confirmar cuál se cita en el documento técnico.
- Siguiente paso: B y C migran del panel sintético al real en cuanto este commit esté en main.
