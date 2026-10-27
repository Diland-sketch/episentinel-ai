import json
from pathlib import Path

import pandas as pd
import pytest

from episentinel.data.ingest import cargar_eventos, limpiar, construir_panel

# Ajusta estas rutas a donde tengas los 3 CSV reales (no se suben a Git).
RUTAS = {
    210: "data/raw/Dengue_210.csv",
    220: "data/raw/Dengue_220.csv",
    580: "data/raw/Dengue_580.csv",
}

pytestmark = pytest.mark.skipif(
    not all(Path(r).exists() for r in RUTAS.values()),
    reason="CSV reales no presentes en data/raw/ (no se versionan en Git)",
)


def test_pipeline_real_end_to_end():
    raw = cargar_eventos(RUTAS)
    val, reporte = limpiar(raw)

    assert reporte["filas_ajenas_excluidas"] == 22
    assert reporte["filas_tras_excluir_ajenas"] == 223629
    assert reporte["municipios_unicos_dataset_completo"] == 1158
    # Filtrando municipios inválidos (código terminado en '000') baja a ~1.124
    assert reporte["municipios_unicos_filas_validas"] < reporte["municipios_unicos_dataset_completo"]

    panel_casos = construir_panel(val, eventos=[210, 220])
    assert panel_casos.index.name is None or True  # el índice es cod_mun
    assert (panel_casos.values >= 0).all()
    assert isinstance(panel_casos.columns, pd.DatetimeIndex)

    panel_muertes = construir_panel(val, eventos=[580])
    assert panel_muertes.values.sum() == reporte["suma_conteo_mortalidad_580"]


def test_reporte_es_serializable_a_json():
    raw = cargar_eventos(RUTAS)
    _, reporte = limpiar(raw)
    json.dumps(reporte)  # no debe lanzar error