from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from app.analysis_presenter import (
    ensure_current, execute, fingerprint, issue_rows, make_config, narrative,
    new_state, observed_figure, read_profiles, set_selection, set_source,
)

ROOT = Path(__file__).resolve().parents[1]
CSV = b"cod_mun,ano,semana,cod_eve,conteo\n76001,2020,52,210,0\n76001,2020,53,220,2\n"


def prepared(event=210):
    state = new_state()
    set_source(state, CSV, "test.csv")
    profile = read_profiles(ROOT / "configs/ui_period_grids.json")[0]
    return state, make_config("76001", event, profile)


def test_real_pipeline_zero_missing_graph_and_narrative():
    state, config = prepared()
    result = execute(state, config)
    assert result.status == "completed"
    series = result.series.series[0]
    assert [p.observed_count for p in series.points] == [0, None, None]
    assert "1 de 3" in narrative(series)
    figure = observed_figure(series)
    assert figure.data[0].connectgaps is False
    assert list(figure.data[0].y) == [0, None, None]
    assert figure.data[1].yaxis == "y2"  # missing markers never use count=0
    assert list(figure.layout.xaxis.categoryarray) == ["2020 · S52", "2020 · S53", "2021 · S01"]


@pytest.mark.parametrize("change", ["bytes", "filename", "municipality", "event", "profile_metadata"])
def test_every_change_invalidates_results(change):
    state, config = prepared()
    execute(state, config)
    if change in {"bytes", "filename"}:
        set_source(state, CSV + (b"76001,2021,1,210,1\n" if change == "bytes" else b""),
                   "other.csv" if change == "filename" else "test.csv")
        assert state["result"] is None
    elif change in {"municipality", "event"}:
        set_selection(state, change, "05001" if change == "municipality" else 220)
        assert state["result"] is None
    else:
        metadata = replace(config.period_grid.metadata, version="changed")
        modified = replace(config, period_grid=replace(config.period_grid, metadata=metadata))
        assert not ensure_current(state, modified)
        assert state["result"] is None


def test_same_inputs_keep_result_and_no_mutation():
    state, config = prepared()
    before = deepcopy(config)
    execute(state, config)
    assert set_source(state, CSV, "test.csv") is False
    assert ensure_current(state, config)
    assert state["load"].data[0]["conteo"] == 0 and config == before


def test_rejected_source_cannot_execute_and_clears_previous_result():
    state, config = prepared()
    execute(state, config)
    set_source(state, b"bad,data\n1,2\n", "bad.csv")
    assert state["result"] is None and state["load"].blocked
    with pytest.raises(ValueError):
        execute(state, config)
    assert issue_rows(state["load"].report)[0]["Qué revisar"]


def test_all_missing_has_no_zero_total():
    state, config = prepared()
    config = replace(config, territory=type(config.territory)("05001"))
    series = execute(state, config).series.series[0]
    assert series.observed_total is None
    assert "no significa cero" in narrative(series)


def test_missing_config_invalidates_current():
    state, config = prepared()
    execute(state, config)
    assert not ensure_current(state, None) and state["result"] is None


def test_profile_retains_provenance_and_no_official_calendar():
    profile = read_profiles(ROOT / "configs/ui_period_grids.json")[0]
    cfg = make_config("76001", 210, profile)
    assert cfg.period_grid.metadata.verification == "unverified"
    assert cfg.period_grid.metadata.source and cfg.period_grid.metadata.version
    assert cfg.period_grid.periods == ((2020, 52), (2020, 53), (2021, 1))


def test_demo_generator_refuses_unignored_output(tmp_path):
    from scripts.prepare_b08_demo import prepare
    with pytest.raises(ValueError, match="ignored"):
        prepare(tmp_path / "absent", tmp_path / "public-output")
    assert not (tmp_path / "public-output").exists()


def test_demo_transform_is_repeatable_and_traceable(tmp_path, monkeypatch):
    import hashlib, json
    from types import SimpleNamespace
    import scripts.prepare_b08_demo as demo
    def audited(path, event):
        rows = []
        for record, (year, week) in enumerate([(2020, 52), (2020, 53), (2021, 1)], 2):
            if event == 220 and week == 1:
                continue
            rows.append(dict(cod_mun="76001", ano=year, semana=week, cod_eve=event,
                             conteo=record, source=path.name, record=record))
        return SimpleNamespace(sha256=demo.EXPECTED[event][0], issues=[], candidates=rows)
    monkeypatch.setattr(demo, "audit_sivigila", audited)
    monkeypatch.setattr(demo.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0))
    output = tmp_path / "demo"
    one = demo.prepare(tmp_path, output)
    payload = (output / "b08_demo.csv").read_bytes()
    two = demo.prepare(tmp_path, output)
    assert one == two and one["rows"] == 5
    assert one["csv_sha256"] == hashlib.sha256(payload).hexdigest()
    assert len(one["source_refs"]) == 5
    assert json.loads((output / "b08_demo_manifest.json").read_text(encoding="utf-8"))["license"] == "CC BY-SA 4.0"
    (output / "b08_demo.csv").write_bytes(b"existing different data")
    with pytest.raises(FileExistsError):
        demo.prepare(tmp_path, output)


def test_executive_summary_uses_current_coverage_without_epidemiological_inference():
    from app.analysis_presenter import executive_summary, interpretation_sections, warning_notes
    state, config = prepared()
    result = execute(state, config)
    before = deepcopy(result)
    summary = executive_summary(result)
    assert (summary["observed"], summary["expected"], summary["missing"]) == (1, 3, 2)
    assert summary["coverage_label"] == "33 %"
    assert summary["warning_count"] == len(result.warnings)
    assert summary["eligibility"] == "No evaluada"
    assert [title for title, _ in interpretation_sections(result.series.series[0])] == [
        "Qué muestran estos datos", "Qué sí puede concluirse", "Qué sigue siendo incierto"]
    assert any("pronósticos" in note for note in warning_notes(result))
    assert result == before


def test_premium_chart_preserves_values_and_has_no_forecast_trace():
    state, config = prepared()
    series = execute(state, config).series.series[0]
    figure = observed_figure(series)
    assert figure.layout.height >= 500
    assert list(figure.data[0].y) == [0, None, None]
    assert not figure.data[0].connectgaps
    assert {trace.name for trace in figure.data} == {"Conteo observado", "Sin observación"}
