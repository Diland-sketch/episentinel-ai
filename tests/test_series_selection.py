"""Synthetic causal-selection tests; no forecasts or historical artifacts."""
from dataclasses import FrozenInstanceError
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest

from episentinel.evaluation.series_selection import EligibilityCriteria, select_cohort
from episentinel.evaluation.temporal_protocol import TemporalProtocol


PROTOCOL = TemporalProtocol(8, 20, 32)
CRITERIA = EligibilityCriteria(min_observed=8, max_series=2, min_positive=2)


def inputs():
    return {
        "00003": pd.Series([2.] * 8 + [100.] * 24),
        "00001": pd.Series([2.] * 8 + [0.] * 24),
        "00002": pd.Series([0.] * 7 + [1.] + [10000.] * 24),
    }


def select(data, **kwargs):
    return select_cohort(data, candidate_codes=("00003", "00002", "00001"),
                         protocol=PROTOCOL, criteria=kwargs.get("criteria", CRITERIA))


@pytest.mark.parametrize("future", [None, np.nan, np.inf, -1, "invalid", 10**30])
def test_future_values_do_not_change_selection_or_filters(future):
    data = inputs()
    expected = select(data)
    for code in data:
        data[code] = data[code].astype(object)
        data[code].iloc[8:] = future
    assert select(data) == expected
    assert expected.selected_codes == ("00001", "00003")
    assert expected.records[1].reasons == ("min_positive_not_met",)


def test_future_length_index_and_new_territory_are_not_selection_inputs():
    expected = select(inputs())
    data = {code: s.iloc[:8].copy() for code, s in inputs().items()}
    data["future_only"] = pd.Series([1e10] * 100)
    assert select(data) == expected
    for code in ("00001", "00002", "00003"):
        data[code] = pd.concat([data[code], pd.Series([None] * 100, index=["bad"] * 100)])
    assert select(data) == expected


def test_ties_are_resolved_by_code_independent_of_mapping_and_candidate_order():
    data = inputs()
    one = EligibilityCriteria(8, 1)
    a = select(data, criteria=one)
    b = select_cohort(dict(reversed(list(data.items()))), candidate_codes=("00001", "00002", "00003"),
                      protocol=PROTOCOL, criteria=one)
    assert a == b
    assert a.selected_codes == ("00001",)
    assert a.records[2].eligible and a.records[2].reasons == ("outside_top_k",)


def test_input_and_frozen_cohort_do_not_change_with_forecast_outcomes():
    data = inputs()
    before = {code: s.copy(deep=True) for code, s in data.items()}
    result = select(data)
    for code in data:
        pd.testing.assert_series_equal(data[code], before[code])
    data["00001"].iloc[:] = 999
    data.clear()
    outcomes = {"00001": "error", "00003": "ok"}
    assert outcomes["00001"] == "error"
    assert result.selected_codes == ("00001", "00003")
    assert result.records[0].score == 16
    with pytest.raises(FrozenInstanceError):
        result.selected_codes = ("00003",)
    with pytest.raises(FrozenInstanceError):
        result.criteria.max_series = 99


@pytest.mark.parametrize("value,reason", [
    (None, "missing_initial_value"), (pd.NA, "missing_initial_value"),
    (np.nan, "missing_initial_value"), (pd.NaT, "missing_initial_value"),
    (-1, "invalid_initial_value"), (np.inf, "invalid_initial_value"),
    (True, "invalid_initial_value"), ("2", "invalid_initial_value"),
    (1j, "invalid_initial_value"), (10**400, "invalid_initial_value"),
    (2**53 + 1, "inexact_initial_value"), (Fraction(1, 3), "inexact_initial_value"),
])
def test_invalid_prefix_is_excluded_without_imputation(value, reason):
    data = {"A": pd.Series([1.] * 8, dtype=object)}
    data["A"].iloc[0] = value
    result = select_cohort(data, candidate_codes=("A",), protocol=PROTOCOL,
                           criteria=EligibilityCriteria(1, 1))
    assert result.selected_codes == ()
    assert reason in result.records[0].reasons
    assert result.records[0].score is None
    assert result.records[0].n_observed == 7


def test_absent_short_and_overflow_series_have_explicit_reasons():
    result = select_cohort({"short": pd.Series([1.]), "huge": pd.Series([1e308] * 8)},
                           candidate_codes=("absent", "short", "huge"), protocol=PROTOCOL,
                           criteria=EligibilityCriteria(8, 3))
    records = {r.code: r for r in result.records}
    assert records["absent"].reasons == ("series_absent",)
    assert "insufficient_initial_history" in records["short"].reasons
    assert records["huge"].reasons == ("nonfinite_score",)
    assert result.selected_codes == ()


def test_no_implicit_positive_week_filter():
    result = select_cohort({"zero": pd.Series([0.] * 8)}, candidate_codes=("zero",),
                           protocol=PROTOCOL, criteria=EligibilityCriteria(8, 1))
    assert result.selected_codes == ("zero",)
    assert result.records[0].score == 0


@pytest.mark.parametrize("codes", [(), ["A"], ("A", "A"), (1,), (" A",), ("",)])
def test_candidate_universe_must_be_explicit_and_unambiguous(codes):
    with pytest.raises(ValueError):
        select_cohort({}, candidate_codes=codes, protocol=PROTOCOL, criteria=CRITERIA)


@pytest.mark.parametrize("args", [(0, 1), (True, 1), (1, 0), (1, 2.5), (1, 1, 0), (1, 1, True)])
def test_invalid_criteria(args):
    with pytest.raises(ValueError):
        EligibilityCriteria(*args)


@pytest.mark.parametrize("criteria", [EligibilityCriteria(9, 1), EligibilityCriteria(1, 1, 9)])
def test_impossible_threshold_rejected(criteria):
    with pytest.raises(ValueError, match="exceeds"):
        select(inputs(), criteria=criteria)


def test_invalid_types_rejected():
    with pytest.raises(TypeError):
        select_cohort({"A": [1] * 8}, candidate_codes=("A",), protocol=PROTOCOL, criteria=CRITERIA)
    with pytest.raises(TypeError):
        select_cohort([], candidate_codes=("A",), protocol=PROTOCOL, criteria=CRITERIA)
