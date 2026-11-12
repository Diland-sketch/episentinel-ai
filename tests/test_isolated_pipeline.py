"""B05-I1 integration tests: synthetic CSVs, no historical outputs."""
import builtins
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
from io import BytesIO, StringIO
import io
import json
from pathlib import Path

import pytest

from episentinel.data.csv_loader import load_csv
from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, SeriesValidationError,
)
from episentinel.services import isolated_pipeline as pipeline
from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline

HEADER = "cod_mun,ano,semana,cod_eve,conteo\n"
VALID = (HEADER + "05001,2020,52,210,0\n05001,2020,53,210,5\n"
         "05001,2021,1,210,7\n05001,2020,52,220,2\n05001,2020,52,580,1\n"
         "99999,2010,1,210,99\n").encode()


def config(**changes):
    base = PipelineConfig("synthetic-v1", MunicipalIdentity("05001"), (210, 220, 580),
                          PeriodGrid(((2020, 52), (2020, 53), (2021, 1)),
                                     CalendarMetadata("test-grid", "v1", "synthetic fixture")))
    return replace(base, **changes)


def test_valid_csv_series_selection_coverage_and_trace():
    cfg = config()
    before = deepcopy(cfg)
    result = run_pipeline(VALID, config=cfg, source_name="example.csv")
    assert result.status == "completed" and not result.errors
    assert result.config == before and cfg == before
    assert result.config is not cfg
    assert not hasattr(result, "data") and not hasattr(result.load_diagnostic, "data")
    assert result.load_diagnostic.source == "example.csv"
    assert result.load_diagnostic.sha256 == hashlib.sha256(VALID).hexdigest()
    bundle = result.series
    assert bundle.event_codes == (210, 220, 580)
    assert [s.observed_total for s in bundle.series] == [12, 2, 1]
    assert [p.observed_count for p in bundle.series[0].points] == [0, 5, 7]
    assert [p.period for p in bundle.series[0].points] == [(2020, 52), (2020, 53), (2021, 1)]
    assert [p.observed_count for p in bundle.series[1].points] == [2, None, None]
    assert bundle.series[1].points[1].observation_status == "missing"
    assert bundle.series[0].points[0].source_refs[0].source == "example.csv"
    assert bundle.series[0].points[0].source_refs[0].record == 2
    assert bundle.selection.selected_records == 5 and bundle.selection.unselected_records == 1
    assert all(s.eligibility.status == "not_evaluated" for s in bundle.series)
    assert any(w.code == "pending_calendar" for w in result.warnings)
    assert any(w.code == "coverage_incomplete" and w.event_code == 220 for w in result.warnings)
    json.dumps(asdict(result))


@pytest.mark.parametrize("kind", ["path", "bytes", "stream"])
def test_supported_sources(tmp_path, kind):
    path = tmp_path / "input.csv"
    path.write_bytes(VALID)
    source = {"path": path, "bytes": VALID, "stream": BytesIO(VALID)}[kind]
    result = run_pipeline(source, config=config(), source_name="same.csv")
    assert result.status == "completed"
    assert result.load_diagnostic.sha256 == hashlib.sha256(VALID).hexdigest()
    if kind == "stream":
        assert not source.closed and source.tell() == len(VALID)


def test_stream_current_position_and_ownership():
    source = BytesIO(b"prefix" + VALID)
    source.seek(6)
    assert run_pipeline(source, config=config()).status == "completed"
    assert not source.closed


@pytest.mark.parametrize("payload", [b"", HEADER.encode(),
    (HEADER + "05001,2020,52,210,-1\n").encode(),
    (HEADER + '05001,2020,52,210,1\n"broken').encode(),
    (HEADER + "05001,2020,52,210,1\n05001,2020,52,210,1\n").encode(),
    (HEADER + "05001,2020,52,210,1\n05001,2020,52,210,8\n").encode(),
])
def test_rejected_csv_never_builds_partial_series(monkeypatch, payload):
    def forbidden(*args, **kwargs):
        pytest.fail("build_series must not run after a blocked load")
    monkeypatch.setattr(pipeline, "build_series", forbidden)
    result = run_pipeline(payload, config=config())
    assert result.status == "blocked" and result.errors
    assert result.series is None and result.load_diagnostic.blocked
    assert result.load_diagnostic.report["summary"]["rows_delivered"] == 0


@pytest.mark.parametrize("changes", [dict(event_codes=()), dict(event_codes=(210, 210)),
    dict(event_codes=(999,)), dict(territory="05001"), dict(period_grid=None)])
def test_configuration_rules_delegated_to_b03(changes):
    result = run_pipeline(VALID, config=config(**changes))
    assert result.status == "blocked" and result.series is None
    assert result.load_diagnostic is not None and not result.load_diagnostic.blocked
    assert result.errors[0].stage == "configuration"


@pytest.mark.parametrize("cfg", [None, {}, config(version=""), config(event_codes=None)])
def test_invalid_config_does_not_consume_input(cfg):
    source = BytesIO(VALID)
    result = run_pipeline(source, config=cfg)
    assert result.status == "blocked" and result.series is None
    assert result.load_diagnostic is None and result.errors[0].stage == "configuration"
    assert source.tell() == 0


def test_selected_period_outside_grid_blocks_without_series():
    result = run_pipeline(VALID, config=config(period_grid=PeriodGrid(((2020, 52), (2021, 1)),
                         CalendarMetadata("short", "1", "fixture"))))
    assert result.status == "blocked" and result.series is None
    assert result.errors[0].code == "outside_grid" and result.errors[0].stage == "series"
    assert result.errors[0].input_position == 2


def test_explicit_events_and_no_observations_are_not_zero():
    result = run_pipeline(VALID, config=config(territory=MunicipalIdentity("05002"), event_codes=(580,)))
    assert result.status == "completed"
    assert len(result.series.series) == 1 and result.series.series[0].event_code == 580
    assert result.series.series[0].observed_total is None
    assert all(p.observed_count is None for p in result.series.series[0].points)
    assert any(w.code == "no_selected_observations" for w in result.warnings)


def test_reuses_b04_and_b03_once_and_does_not_mutate(monkeypatch):
    real_load, real_build = pipeline.load_csv, pipeline.build_series
    calls = []
    retained = {}
    def observed_load(*args, **kwargs):
        calls.append("load")
        loaded = real_load(*args, **kwargs)
        retained["loaded"] = loaded
        retained["before"] = deepcopy(loaded)
        return loaded
    def observed_build(data, **kwargs):
        calls.append("build")
        assert data == retained["loaded"].data
        assert data is not retained["loaded"].data
        return real_build(data, **kwargs)
    monkeypatch.setattr(pipeline, "load_csv", observed_load)
    monkeypatch.setattr(pipeline, "build_series", observed_build)
    result = run_pipeline(VALID, config=config())
    assert calls == ["load", "build"] and result.status == "completed"
    assert retained["loaded"] == retained["before"]
    result.load_diagnostic.report["summary"]["rows_read"] = -1
    assert retained["loaded"] == retained["before"]


def test_builder_failure_cannot_mutate_loader_data(monkeypatch):
    loaded = load_csv(VALID)
    before = deepcopy(loaded)
    monkeypatch.setattr(pipeline, "load_csv", lambda *a, **kw: loaded)
    def broken_builder(data, **kwargs):
        data[0]["conteo"] = 999
        raise SeriesValidationError("test_failure", "synthetic", input_position=1)
    monkeypatch.setattr(pipeline, "build_series", broken_builder)
    result = run_pipeline(VALID, config=config())
    assert result.status == "blocked" and result.series is None
    assert loaded == before


@pytest.mark.parametrize("kind", ["missing", "text_stream", "unsupported", "source_name"])
def test_input_failures_are_structured(tmp_path, kind):
    source = {"missing": tmp_path / "absent.csv", "text_stream": StringIO(VALID.decode()),
              "unsupported": object(), "source_name": VALID}[kind]
    result = run_pipeline(source, config=config(), source_name=123 if kind == "source_name" else None)
    assert result.status == "failed" and result.series is None
    assert result.load_diagnostic is None and result.errors[0].stage == "load"


def test_does_not_open_files_for_writing_or_change_historical_sentinels(tmp_path, monkeypatch):
    source = tmp_path / "input.csv"
    source.write_bytes(VALID)
    panel = tmp_path / "panel_casos.parquet"
    report = tmp_path / "ingest_report.json"
    panel.write_bytes(b"historical panel sentinel")
    report.write_bytes(b'{"historical": true}')
    originals = {p: p.read_bytes() for p in (source, panel, report)}
    real_builtin, real_io = builtins.open, io.open
    def guard(real):
        def read_only(file, mode="r", *args, **kwargs):
            assert not any(c in mode for c in "wax+"), f"Unexpected write: {file}"
            return real(file, mode, *args, **kwargs)
        return read_only
    monkeypatch.setattr(builtins, "open", guard(real_builtin))
    monkeypatch.setattr(io, "open", guard(real_io))
    result = run_pipeline(source, config=config())
    assert result.status == "completed"
    assert {p: p.read_bytes() for p in originals} == originals


def test_missing_data_from_an_accepted_loader_fails_closed(monkeypatch):
    loaded = load_csv(VALID)
    loaded.data = None
    monkeypatch.setattr(pipeline, "load_csv", lambda *a, **kw: loaded)
    result = run_pipeline(VALID, config=config())
    assert result.status == "failed" and result.series is None
    assert result.errors[0].code == "invalid_load_result"


def test_no_implicit_s53_or_configuration_mutation():
    events = [210]
    cfg = config(event_codes=events, period_grid=PeriodGrid(((2020, 52), (2021, 1)),
                 CalendarMetadata("without-53", "v1", "synthetic fixture")))
    events.append(220)
    payload = (HEADER + "05001,2020,52,210,0\n05001,2021,1,210,4\n").encode()
    result = run_pipeline(payload, config=cfg)
    assert result.status == "completed"
    assert result.series.event_codes == (210,)
    assert [p.period for p in result.series.series[0].points] == [(2020, 52), (2021, 1)]


def test_programming_errors_are_not_disguised_as_csv_errors(monkeypatch):
    def unexpected(*args, **kwargs):
        raise RuntimeError("synthetic programming failure")
    monkeypatch.setattr(pipeline, "build_series", unexpected)
    with pytest.raises(RuntimeError, match="programming failure"):
        run_pipeline(VALID, config=config())
