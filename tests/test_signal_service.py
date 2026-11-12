"""Synthetic B07 tests: evaluable EARS and explicit integration limitations."""
import builtins
from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, build_series,
)
from episentinel.detection.alertas import ears_c2
from episentinel.services.isolated_pipeline import PipelineConfig, run_pipeline
from episentinel.services.signal_service import EarsC2Config, evaluate_signals
import episentinel.services.signal_service as signal_service


def bundle(counts, *, periods=None, verification="verified"):
    by_event = counts if isinstance(counts, dict) else {210: counts}
    n = len(next(iter(by_event.values())))
    periods = tuple(periods) if periods is not None else tuple((2020, w) for w in range(1, n + 1))
    metadata = CalendarMetadata("synthetic-grid", "v1", "synthetic test only", verification,
                                "synthetic provider declaration; not institutional validation"
                                if verification == "verified" else None)
    rows = []
    for event, values in by_event.items():
        for (year, week), count in zip(periods, values):
            if count is not None:
                rows.append(dict(cod_mun="05001", ano=year, semana=week, cod_eve=event,
                                 conteo=count, source="synthetic.csv", record=len(rows) + 2))
    return build_series(rows, territory=MunicipalIdentity("05001"),
                        event_codes=tuple(by_event), period_grid=PeriodGrid(periods, metadata))


def ears_report(series, config=None):
    return evaluate_signals(series, ears_config=config, rules=("ears_c2",))


@pytest.mark.parametrize("count,status", [(13, "no_signal"), (14, "signal")])
def test_exact_threshold_and_immediately_above(count, status):
    result = ears_report(bundle([10] * 9 + [count])).results[-1]
    assert result.status == status
    assert result.threshold == 13 and result.reference_mean == 10
    assert result.reference_sd == 0 and result.effective_sd == 1
    assert result.score == count - 10
    assert result.not_evaluable_reason is None
    assert result.observed_count == count and result.reason


def test_synthetic_peak_is_detected_and_reference_is_explained():
    result = ears_report(bundle([10] * 12 + [100])).results[-1]
    assert result.status == "signal"
    assert [p.period for p in result.reference] == [(2020, w) for w in range(4, 11)]
    assert all(p.observed_count == 10 and p.period < result.period for p in result.reference)
    assert result.territory_code == "05001" and result.event_code == 210
    assert result.parameters == dict(base=7, guard=2, k=3.0, min_sd=1.0, min_casos=3)


@pytest.mark.parametrize("n", [1, 4, 9])
def test_short_history_is_not_a_negative_signal(n):
    results = ears_report(bundle([10] * n)).results
    assert len(results) == n
    assert all(r.status == "not_evaluable" for r in results)
    assert all(r.not_evaluable_reason == "insufficient_reference" for r in results)
    assert all(r.threshold is None and r.score is None for r in results)


@pytest.mark.parametrize("value", [0, 10])
def test_constant_series_has_finite_reference_and_no_signal(value):
    result = ears_report(bundle([value] * 12)).results[-1]
    assert result.status == "no_signal" and result.observed_count == value
    assert result.score == 0 and result.effective_sd == 1


def test_observed_zero_differs_from_missing_observation():
    zero = ears_report(bundle([10] * 9 + [0])).results[-1]
    missing = ears_report(bundle([10] * 9 + [None])).results[-1]
    assert zero.status == "no_signal" and zero.observed_count == 0
    assert missing.status == "not_evaluable" and missing.observed_count is None
    assert missing.not_evaluable_reason == "missing_observation"
    assert missing.threshold is None and missing.score is None


def test_completely_absent_series_stays_absent_for_all_rules():
    series = bundle([None] * 12)
    report = evaluate_signals(series)
    assert len(report.results) == 36
    assert all(r.status == "not_evaluable" and r.observed_count is None for r in report.results)
    assert all(r.not_evaluable_reason == "missing_observation" for r in report.results)
    assert series.series[0].observed_total is None


def test_missing_reference_is_not_evaluable_without_imputation():
    values = [10] * 9 + [40]
    values[2] = None
    series = bundle(values)
    result = ears_report(series).results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "missing_reference"
    assert any(p.observed_count is None for p in result.reference)
    assert series.series[0].points[2].observed_count is None


def test_missing_guard_observations_keep_positions_without_joining_reference():
    result = ears_report(bundle([10] * 7 + [None, None, 40])).results[-1]
    assert result.status == "signal"
    assert [p.period for p in result.reference] == [(2020, w) for w in range(1, 8)]


def test_unverified_calendar_cannot_produce_signal_or_no_signal():
    report = ears_report(bundle([10] * 10, verification="unverified"))
    assert all(r.status == "not_evaluable" for r in report.results)
    assert all(r.not_evaluable_reason == "calendar_unverified" for r in report.results)


def test_sparse_declared_grid_is_not_treated_as_consecutive_weeks():
    periods = [(2020, w) for w in (1, 2, 3, 4, 5, 7, 8, 9, 10, 11)]
    result = ears_report(bundle([10] * 10, periods=periods)).results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "nonconsecutive_grid"


def test_s53_preserved_and_cross_year_interpretation_remains_pending():
    periods = tuple((2020, w) for w in range(44, 54)) + ((2021, 1),)
    report = ears_report(bundle([10] * 9 + [40, 40], periods=periods))
    assert tuple(r.period for r in report.results) == periods
    assert report.results[-2].period == (2020, 53)
    assert report.results[-2].status == "signal"
    assert report.results[-1].status == "not_evaluable"
    assert report.results[-1].not_evaluable_reason == "calendar_boundary_pending"


def test_events_are_never_combined():
    series = bundle({210: [10] * 9 + [100], 220: [10] * 10, 580: [0] * 10})
    report = ears_report(series)
    last = {r.event_code: r for r in report.results if r.period == (2020, 10)}
    assert {event: r.status for event, r in last.items()} == {
        210: "signal", 220: "no_signal", 580: "no_signal",
    }
    assert last[210].observed_count == 100 and last[220].observed_count == 10
    assert last[580].observed_count == 0 and len(report.results) == 30


def test_future_changes_do_not_change_previous_results_including_missingness():
    values = [10] * 12 + [40] + [10] * 7
    changed = values[:14] + [None, 1000000, 0, 99, None, 4000]
    before = evaluate_signals(bundle(values))
    after = evaluate_signals(bundle(changed))
    assert [r for r in before.results if r.period <= (2020, 14)] == [
        r for r in after.results if r.period <= (2020, 14)
    ]


def test_adding_future_points_does_not_change_prefix_results():
    values = [10] * 12 + [40]
    prefix = evaluate_signals(bundle(values))
    extended = evaluate_signals(bundle(values + [1000000, None, 0, 1]))
    assert prefix.results == tuple(r for r in extended.results if r.period <= (2020, 13))


def test_current_observation_and_guard_are_excluded_from_reference():
    baseline = ears_report(bundle([10] * 10)).results[-1]
    changed = ears_report(bundle([10] * 7 + [999999, 999999, 100])).results[-1]
    assert baseline.reference == changed.reference
    assert baseline.threshold == changed.threshold == 13
    assert baseline.status == "no_signal" and changed.status == "signal"


def test_numeric_rule_reuses_historical_ears_with_identical_parameters():
    values = [2, 5, 3, 6, 4, 7, 3, 8, 9, 14, 12, 30]
    config = EarsC2Config(base=4, guard=1, k=2, min_sd=0.5, min_casos=2)
    expected = ears_c2(pd.Series(values, dtype=float), **asdict(config))
    report = ears_report(bundle(values), config)
    for position, result in enumerate(report.results):
        if position >= config.base + config.guard:
            assert (result.status == "signal") == bool(expected.iloc[position]["alerta_ears"])
            assert result.score == pytest.approx(expected.iloc[position]["z_ears"])
            assert len(result.reference) == config.base


def test_minimum_case_gate_is_preserved():
    result = ears_report(bundle([0] * 9 + [1]), EarsC2Config(k=0)).results[-1]
    assert result.score > 0 and result.observed_count < result.parameters["min_casos"]
    assert result.status == "no_signal"


def test_pending_methods_do_not_fabricate_thresholds_or_forecasts():
    report = evaluate_signals(bundle([10] * 12))
    reasons = {"canal_endemico": "explicit_period_channel_pending",
               "sarima_one_step": "forecast_service_pending"}
    for rule, reason in reasons.items():
        results = [r for r in report.results if r.rule == rule]
        assert len(results) == 12
        assert all(r.status == "not_evaluable" and r.not_evaluable_reason == reason for r in results)
        assert all(r.reference == () and r.threshold is None and r.score is None for r in results)
    assert not hasattr(report, "semaforo")


def test_serialization_reproducibility_and_no_input_mutation():
    series = bundle({210: [10] * 9 + [40, None], 220: [0] * 11})
    original = deepcopy(series)
    first = evaluate_signals(series)
    assert series == original and first == evaluate_signals(series)
    serialized = json.loads(json.dumps(asdict(first), allow_nan=False))
    assert serialized["contract_version"] == "1"
    assert serialized["calendar"]["calendar_id"] == "synthetic-grid"
    assert serialized["results"][-1]["observed_count"] == 0
    first.results[0].parameters["k"] = 100
    assert evaluate_signals(series).results[0].parameters["k"] == 3


def test_numeric_overflow_is_not_a_negative_or_nonserializable_signal():
    report = ears_report(bundle([10 ** 400] * 10))
    result = report.results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "numeric_precision_unsupported"
    json.dumps(asdict(report), allow_nan=False)


@pytest.mark.parametrize("n", [
    10 ** 16 - 1, 10 ** 16, 10 ** 16 + 1, 10 ** 20,
    2 ** 53 - 2, 2 ** 53 - 1, 2 ** 53, 2 ** 53 + 1, 10 ** 400,
])
@pytest.mark.parametrize("delta", [3, 4])
def test_large_integer_regression_through_real_csv_pipeline(n, delta):
    series = bundle([n] * 9 + [n + delta])
    config = PipelineConfig("precision-repro-v1", series.territory, (210,), series.grid)
    payload = ("cod_mun,ano,semana,cod_eve,conteo\n" + "".join(
        f"05001,2020,{w},210,{n + delta if w == 10 else n}\n" for w in range(1, 11)
    )).encode()
    pipeline = run_pipeline(payload, config=config, source_name="precision.csv")
    assert pipeline.status == "completed" and not pipeline.load_diagnostic.blocked
    assert pipeline.series.series[0].points[-1].observed_count == n + delta
    report = ears_report(pipeline.series)
    result = report.results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "numeric_precision_unsupported"
    assert result.observed_count == n + delta
    assert all(getattr(result, name) is None for name in (
        "reference_mean", "reference_sd", "effective_sd", "threshold", "score",
    ))
    json.dumps(asdict(report), allow_nan=False)


@pytest.mark.parametrize("n", [2 ** 52 - 5, 2 ** 52 - 4, 2 ** 52 - 3, 2 ** 52])
@pytest.mark.parametrize("delta", [3, 4])
def test_subunit_resolution_boundary_is_correct_or_explicitly_rejected(n, delta):
    report = ears_report(bundle([n] * 9 + [n + delta]))
    result = report.results[-1]
    if result.status == "not_evaluable":
        assert result.not_evaluable_reason == "numeric_precision_unsupported"
        assert result.threshold is None and result.score is None
    else:
        assert result.status == ("signal" if delta > 3 else "no_signal")
        assert result.threshold == n + 3 and result.score == delta
    json.dumps(asdict(report), allow_nan=False)


@pytest.mark.parametrize("n", [0, 10])
@pytest.mark.parametrize("delta", [0, 3, 4])
def test_ordinary_csv_pipeline_preserves_negative_threshold_and_peak(n, delta):
    series = bundle([n] * 9 + [n + delta])
    config = PipelineConfig("ordinary-v1", series.territory, (210,), series.grid)
    payload = ("cod_mun,ano,semana,cod_eve,conteo\n" + "".join(
        f"05001,2020,{w},210,{n + delta if w == 10 else n}\n" for w in range(1, 11)
    )).encode()
    pipeline = run_pipeline(payload, config=config)
    assert pipeline.status == "completed"
    report = ears_report(pipeline.series)
    result = report.results[-1]
    assert result.status == ("signal" if delta > 3 else "no_signal")
    assert result.reference_mean == n and result.threshold == n + 3
    assert result.score == delta and result.not_evaluable_reason is None
    json.dumps(asdict(report), allow_nan=False)


def test_unsupported_counts_are_rejected_before_float64_conversion(monkeypatch):
    series = bundle([10 ** 20] * 9 + [10 ** 20 + 4])

    def forbidden(*args, **kwargs):
        raise AssertionError("Unsupported integer reached float64 conversion")

    monkeypatch.setattr(signal_service.pd, "Series", forbidden)
    result = ears_report(series).results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "numeric_precision_unsupported"


def test_unused_guard_precision_does_not_change_reference_or_decision():
    baseline = ears_report(bundle([10] * 9 + [14])).results[-1]
    guarded = ears_report(bundle([10] * 7 + [10 ** 400, 10 ** 20, 14])).results[-1]
    assert guarded.reference == baseline.reference
    assert guarded.status == baseline.status == "signal"
    assert guarded.threshold == baseline.threshold == 13
    assert guarded.score == baseline.score == 4


def test_extreme_future_counts_do_not_change_past_numeric_eligibility():
    past = [10] * 9 + [14]
    prefix = ears_report(bundle(past))
    extended = ears_report(bundle(past + [10 ** 20, 10 ** 400, 0]))
    assert prefix.results == extended.results[:len(past)]
    assert extended.results[10].not_evaluable_reason == "numeric_precision_unsupported"


@pytest.mark.parametrize("fault", ["score", "classification"])
def test_exact_certificate_rejects_unreliable_kernel_outputs(monkeypatch, fault):
    original = signal_service.ears_c2

    def corrupted(*args, **kwargs):
        result = original(*args, **kwargs)
        if fault == "score":
            result.loc[result.index[-1], "z_ears"] += 0.25
        else:
            result.loc[result.index[-1], "alerta_ears"] = False
        return result

    monkeypatch.setattr(signal_service, "ears_c2", corrupted)
    result = ears_report(bundle([10] * 9 + [14])).results[-1]
    assert result.status == "not_evaluable"
    assert result.not_evaluable_reason == "numeric_precision_unsupported"
    assert result.threshold is None and result.score is None


def test_b04_b05_b03_output_is_consumed_without_changing_their_interfaces():
    series = bundle([10] * 9 + [40])
    config = PipelineConfig("test-v1", series.territory, (210,), series.grid)
    payload = ("cod_mun,ano,semana,cod_eve,conteo\n" + "".join(
        f"05001,2020,{w},210,{40 if w == 10 else 10}\n" for w in range(1, 11)
    )).encode()
    pipeline = run_pipeline(payload, config=config)
    assert pipeline.status == "completed"
    assert ears_report(pipeline.series).results[-1].status == "signal"
    assert pipeline.series.series[0].eligibility.status == "not_evaluated"
    blocked = run_pipeline(b"bad csv", config=config)
    assert blocked.status == "blocked" and blocked.series is None
    with pytest.raises(TypeError):
        evaluate_signals(blocked.series)


def test_evaluation_has_no_file_io_and_is_independent_of_working_directory(tmp_path, monkeypatch):
    series = bundle([10] * 9 + [40])
    expected = evaluate_signals(series)
    monkeypatch.chdir(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Signal evaluation attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert evaluate_signals(series) == expected


def test_module_can_be_imported_when_streamlit_is_unavailable(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    completed = subprocess.run(
        [sys.executable, "-B", "-c", "import sys; sys.modules['streamlit'] = None; "
         "from episentinel.services.signal_service import evaluate_signals; print('ok')"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ok"


@pytest.mark.parametrize("kwargs", [
    dict(base=1), dict(base=True), dict(guard=-1), dict(guard=0.5), dict(k=-1),
    dict(k=float("nan")), dict(k=float("inf")), dict(min_sd=0), dict(min_sd=-1),
    dict(min_casos=-1), dict(min_casos=True),
])
def test_invalid_numeric_configuration_fails_explicitly(kwargs):
    with pytest.raises(ValueError):
        EarsC2Config(**kwargs)


@pytest.mark.parametrize("rules", [(), ("unknown",), ("ears_c2", "ears_c2"), "ears_c2", None])
def test_invalid_rule_selection_fails_explicitly(rules):
    with pytest.raises(ValueError):
        evaluate_signals(bundle([10] * 10), rules=rules)


def test_inconsistent_bundle_is_not_silently_evaluated():
    series = bundle([10] * 10)
    with pytest.raises(ValueError):
        evaluate_signals(replace(series, structural_integrity="invalid"))
    points = series.series[0].points
    invalid = replace(series.series[0], points=points[:-1])
    with pytest.raises(ValueError):
        evaluate_signals(replace(series, series=(invalid,)))
    invalid_point = replace(points[-1], observation_status="missing")
    invalid = replace(series.series[0], points=points[:-1] + (invalid_point,))
    with pytest.raises(ValueError):
        evaluate_signals(replace(series, series=(invalid,)))
