"""Scientific journey tests use local temporary evidence, without fitting models."""
from pathlib import Path
import hashlib
import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import lab_evidence as evidence
from app.analysis_presenter import new_state, set_source, set_selection, make_config, read_profiles, execute
from tests.test_platform_app import artifacts, prohibit_models

ROOT = Path(__file__).resolve().parents[1]


def journey():
    page = AppTest.from_file(str(ROOT / "app/platform_app.py"), default_timeout=20).run()
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    assert not page.exception
    return page


def click(page, label):
    next(button for button in page.button if button.label == label).click().run()
    assert not page.exception


def test_catalog_has_twelve_substantive_phases_and_four_chapters():
    assert [p.number for p in evidence.PHASES] == list(range(1, 13))
    assert [sum(p.chapter == chapter for p in evidence.PHASES) for chapter in evidence.CHAPTERS] == [4, 3, 3, 2]
    for phase in evidence.PHASES:
        assert all((phase.objective, phase.methodology, phase.result, phase.limitations, phase.pending, phase.sources, phase.reproduce))
    assert "fuga" in evidence.PHASES[5].limitations
    assert "superioridad general" in evidence.PHASES[6].limitations


def test_missing_evidence_does_not_create_results_or_complete_phases(tmp_path):
    context = evidence.load_context(tmp_path)
    assert context["comparison"] is None and context["ingest"] is None
    assert evidence.split_rows(context) == [] and evidence.summary_rows(context) is None
    assert {evidence.phase_status(phase, context) for phase in evidence.PHASES} == {"Parcial", "Pendiente"}
    assert evidence.phase_status(evidence.PHASES[8], context) == "Pendiente"


def test_collection_requires_matching_sources_and_provenance(tmp_path, monkeypatch):
    expected = {}
    for relative in evidence.EXPECTED_SOURCES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (path.name + " synthetic").encode()
        path.write_bytes(payload)
        expected[relative] = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(evidence, "EXPECTED_SOURCES", expected)
    phase = evidence.PHASES[1]
    assert evidence.phase_status(phase, evidence.load_context(tmp_path)) == "Parcial"
    for relative in ("data/README.md", "docs/PROCEDENCIA_B02.md", "scripts/audit_csv_sources.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic provenance fixture", encoding="utf-8")
    assert evidence.phase_status(phase, evidence.load_context(tmp_path)) == "Completo con evidencia"
    next(iter((tmp_path / "data/raw").iterdir())).write_bytes(b"modified synthetic source")
    assert evidence.phase_status(phase, evidence.load_context(tmp_path)) == "Parcial"


@pytest.mark.parametrize("values", [(727, 779, 831), (0, 1, 2)])
def test_split_chart_counts_follow_actual_config(values, tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/split.json").write_text(json.dumps(dict(zip(("train_end", "val_end", "test_end"), values))))
    rows = evidence.split_rows(evidence.load_context(tmp_path))
    assert sum(row["Semanas configuradas"] for row in rows) == values[-1] + 1
    assert rows[1]["Inicio (posición)"] == values[0] + 1
    assert rows[2]["Fin inclusivo"] == values[-1]


def test_invalid_split_and_corrupt_reports_are_not_silently_replaced(artifacts):
    (artifacts / "configs/split.json").write_text('{"train_end": 779,"val_end": 727,"test_end":831}')
    (artifacts / "reports/comparacion_fase2.csv").write_text("serie,modelo,mae,rmse,mase\nNACIONAL,x,1,2,inf\n")
    (artifacts / "reports/ingest_report.json").write_text("invalid JSON")
    context = evidence.load_context(artifacts)
    assert evidence.split_rows(context) == []
    assert context["comparison"] is None and context["ingest"] is None
    assert len(context["errors"]) == 2


def test_saved_metrics_are_read_without_recomputing_models(artifacts):
    context = evidence.load_context(artifacts)
    assert len(context["comparison"]) == 8
    assert evidence.summary_rows(context).loc["ingenua_ultimo_valor", "mase"] == .2
    signature = evidence.evidence_signature(artifacts)
    path = artifacts / "reports/comparacion_fase2.csv"
    frame = pd.read_csv(path)
    frame["mase"] = .425
    frame.to_csv(path, index=False)
    assert evidence.evidence_signature(artifacts) != signature
    assert evidence.summary_rows(evidence.load_context(artifacts)).iloc[0]["mase"] == .425


def test_all_twelve_phases_and_chapters_never_fit_models(artifacts, monkeypatch):
    prohibit_models(monkeypatch)
    page = journey()
    seen = []
    for number in range(1, 13):
        phase = evidence.PHASES[number - 1]
        assert page.radio(key="epi_science_chapter_widget").value == phase.chapter
        assert page.radio(key=f"epi_science_phase_widget_{phase.chapter}").value == number
        assert any(phase.title in item.value and f"FASE {number:02d}" in item.value for item in page.markdown)
        assert any(item.label == "Evidencia y reproducción de esta fase" for item in page.expander)
        if number == 6:
            assert len(page.get("plotly_chart")) == 1
        if number == 9:
            assert page.warning and not page.get("plotly_chart")
        if number == 10:
            assert len(page.get("plotly_chart")) == 1
        seen.append(number)
        if number < 12:
            click(page, "Fase siguiente →")
    assert len(seen) == 12
    assert next(b for b in page.button if b.label == "Fase siguiente →").disabled
    click(page, "← Fase anterior")
    assert page.radio(key="epi_science_phase_widget_4").value == 11


def test_contextual_graph_link_and_return_preserve_scientific_selection(artifacts, monkeypatch):
    prohibit_models(monkeypatch)
    page = journey()
    page.radio(key="epi_science_chapter_widget").set_value(3).run()
    click(page, "Explorar vista histórica · Pronósticos")
    assert page.radio(key="epi_lab_mode_widget").value == "Vistas históricas"
    assert page.radio(key="epi_lab_view").value == "Pronósticos"
    assert not page.get("plotly_chart")
    page.radio(key="epi_lab_mode_widget").set_value("Recorrido científico").run()
    assert page.radio(key="epi_science_chapter_widget").value == 3
    assert page.radio(key="epi_science_phase_widget_3").value == 8
    assert not page.exception


def test_chapter_selection_and_observatory_result_survive_navigation(artifacts, monkeypatch):
    prohibit_models(monkeypatch)
    page = journey()
    state = new_state()
    set_source(state, b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,220,2\n", "synthetic.csv")
    profile = read_profiles(ROOT / "configs/ui_period_grids.json")[0]
    for field, value in (("municipality", "76001"), ("event", 220), ("profile", profile["id"])):
        set_selection(state, field, value)
    execute(state, make_config("76001", 220, profile))
    identity = state["execution_key"]
    page.session_state.epi_work = state
    page.radio(key="epi_science_chapter_widget").set_value(3).run()
    page.radio(key="epi_science_phase_widget_3").set_value(9).run()
    page.radio(key="epi_science_chapter_widget").set_value(1).run()
    page.radio(key="epi_science_chapter_widget").set_value(3).run()
    assert page.radio(key="epi_science_phase_widget_3").value == 9
    page.radio(key="epi_platform_nav").set_value("Observatorio Epidemiológico").run()
    page.radio(key="epi_nav").set_value("Analizar datos").run()
    assert not page.exception and len(page.get("plotly_chart")) == 1
    assert page.session_state.epi_work["execution_key"] == identity
    page.radio(key="epi_platform_nav").set_value("Laboratorio de Machine Learning").run()
    assert page.radio(key="epi_science_phase_widget_3").value == 9
    assert page.session_state.epi_work["execution_key"] == identity


def test_missing_or_corrupt_artifacts_keep_phase_accessible(artifacts):
    (artifacts / "data/processed/panel_casos.parquet").unlink()
    (artifacts / "reports/comparacion_fase2.csv").write_text("wrong,columns\n1,2\n")
    page = journey()
    page.radio(key="epi_science_chapter_widget").set_value(3).run()
    page.radio(key="epi_science_phase_widget_3").set_value(10).run()
    assert not page.exception and not page.get("plotly_chart")
    assert any("No hay una comparación guardada válida" in info.value for info in page.info)
    assert any(e.label == "Incidencias de lectura de evidencia" for e in page.expander)
    page.radio(key="epi_science_chapter_widget").set_value(4).run()
    assert not page.exception
