from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from episentinel.data.epidemiological_series import (
    CalendarMetadata, MunicipalIdentity, PeriodGrid, SeriesValidationError, build_series,
)


def grid(periods=((2020, 52), (2020, 53), (2021, 1)), **metadata):
    return PeriodGrid(periods, CalendarMetadata("test-grid", "v1", "synthetic fixture", **metadata))


def row(year=2020, week=52, event=210, count=3, code="05001", **extra):
    return dict(cod_mun=code, ano=year, semana=week, cod_eve=event, conteo=count, **extra)


def build(rows, periods=None, events=(210,), code="05001"):
    return build_series(rows, territory=MunicipalIdentity(code), event_codes=events,
                        period_grid=periods if periods is not None else grid())


def test_year_boundary_preserves_s53_without_dates():
    result = build([row(2021, 1, count=7), row(week=53, count=5), row(count=2)])
    points = result.series[0].points
    assert [p.period for p in points] == [(2020, 52), (2020, 53), (2021, 1)]
    assert [p.observed_count for p in points] == [2, 5, 7]
    assert result.series[0].observed_total == 14
    assert not hasattr(points[0], "date")
    assert result.grid.metadata.verification == "unverified"
    assert "calendar_unverified" in result.series[0].eligibility.reasons


def test_no_s53_generated_and_missing_is_not_zero():
    result = build([row(count=0)], grid(((2020, 52), (2021, 1))))
    series = result.series[0]
    assert len(series.points) == 2
    assert [(p.observed_count, p.observation_status) for p in series.points] == [(0, "observed"), (None, "missing")]
    assert series.points[1].source_refs == ()
    assert series.coverage.missing_periods == ((2021, 1),)
    assert series.coverage.observed_periods == 1
    assert series.coverage.status == "incomplete_in_declared_grid"


def test_events_are_separate_including_partial_event_coverage():
    result = build([row(event=210, count=10), row(event=220, count=2), row(event=580, count=1)],
                   grid(((2020, 52), (2020, 53))), events=(210, 220, 580))
    assert result.event_codes == (210, 220, 580)
    assert [s.event_code for s in result.series] == [210, 220, 580]
    assert [s.observed_total for s in result.series] == [10, 2, 1]
    assert all(s.points[1].observed_count is None for s in result.series)


@pytest.mark.parametrize("count", [3, 99])
def test_duplicates_cross_sources_block(count):
    with pytest.raises(SeriesValidationError) as caught:
        build([row(source="a.csv", record=2), row(count=count, source="b.csv", record=8)])
    assert caught.value.code == "duplicate"
    assert caught.value.input_position == 2


@pytest.mark.parametrize("code", ["00000", "01000", "01862", "05000"])
def test_special_territory_not_a_municipality(code):
    with pytest.raises(SeriesValidationError, match="Special territory"):
        MunicipalIdentity(code)


@pytest.mark.parametrize("code", ["99999", "05001"])
def test_syntactic_candidate_not_rejected_without_catalog(code):
    result = build([row(code=code)], code=code)
    assert result.territory.catalog_validation == "pending"
    assert result.structural_integrity == "valid"
    assert result.series[0].eligibility.status == "not_evaluated"
    assert "territorial_catalog_pending" in result.series[0].eligibility.reasons


@pytest.mark.parametrize("code", ["5001", 5001, "05001.0", " 05001", "abcde"])
def test_malformed_identity(code):
    with pytest.raises(SeriesValidationError):
        MunicipalIdentity(code)


@pytest.mark.parametrize("periods", [(), None, ((2020, 52), (2020, 52)), ((2021, 1), (2020, 52)),
    ((2020, 0),), ((2020, 54),), ((2020.5, 1),), ((2020, True),), ((20, 1),), ((2020,),)])
def test_bad_grids(periods):
    with pytest.raises(SeriesValidationError):
        grid(periods)


def test_selected_s53_outside_grid_is_not_folded_or_dropped():
    with pytest.raises(SeriesValidationError) as caught:
        build([row(week=53)], grid(((2020, 52), (2021, 1))))
    assert caught.value.code == "outside_grid"


def test_selection_conservation_trace_and_no_input_mutation():
    rows = [row(source="a.csv", record=17), row(week=53, count=0, source="b.csv", record=4),
            row(event=220, count=9), row(year=2010, code="01862", count=1)]
    original = deepcopy(rows)
    result = build(iter(rows))
    assert rows == original
    assert (result.selection.input_records, result.selection.selected_records,
            result.selection.unselected_records) == (4, 2, 2)
    series = result.series[0]
    assert series.observed_total == 3
    refs = [p.source_refs[0] for p in series.points if p.source_refs]
    assert [(r.input_position, r.source, r.record) for r in refs] == [(1, "a.csv", 17), (2, "b.csv", 4)]
    rows[0]["conteo"] = 999
    assert series.points[0].observed_count == 3
    with pytest.raises(FrozenInstanceError):
        series.points[0].observed_count = 9


def test_grid_detaches_mutable_input():
    periods = [[2020, 52], [2021, 1]]
    declared = grid(periods)
    periods[0][1] = 1
    assert declared.periods == ((2020, 52), (2021, 1))


def test_all_missing_is_structurally_valid_not_eligible_claim():
    result = build([])
    series = result.series[0]
    assert result.structural_integrity == "valid"
    assert series.coverage.observed_periods == 0
    assert series.coverage.expected_periods == 3
    assert series.observed_total is None  # no observations must not look like zero cases
    assert all(p.observed_count is None for p in series.points)
    assert series.eligibility.status == "not_evaluated"
    assert "missing_observations" in series.eligibility.reasons


def test_complete_grid_does_not_assert_method_eligibility():
    result = build([row()], grid(((2020, 52),)))
    series = result.series[0]
    assert series.coverage.status == "complete_in_declared_grid"
    assert series.coverage.calendar_verification == "unverified"
    assert series.eligibility.status == "not_evaluated"
    assert "dates_unassigned" in series.eligibility.reasons


def test_verified_metadata_requires_evidence_but_does_not_generate_dates():
    with pytest.raises(SeriesValidationError):
        grid(verification="verified")
    declared = grid(verification="verified", evidence="synthetic calendar evidence; not official")
    result = build([], declared)
    assert result.grid.metadata.evidence.startswith("synthetic")
    assert result.series[0].eligibility.status == "not_evaluated"
    assert "dates_unassigned" in result.series[0].eligibility.reasons


@pytest.mark.parametrize("metadata", [dict(source=""), dict(version=""), dict(verification="official")])
def test_required_metadata(metadata):
    config = dict(calendar_id="test", version="1", source="synthetic")
    config.update(metadata)
    with pytest.raises(SeriesValidationError):
        CalendarMetadata(**config)


@pytest.mark.parametrize("events", [(), (210, 210), (999,), (True,), None])
def test_invalid_event_selection(events):
    with pytest.raises(SeriesValidationError):
        build([], events=events)


@pytest.mark.parametrize("change", [dict(conteo=-1), dict(conteo=1.5), dict(conteo=True),
    dict(ano="2020"), dict(semana=54), dict(cod_eve=999), dict(cod_mun="5001"),
    dict(record=0), dict(source="")])
def test_revalidate_observations(change):
    observation = row()
    observation.update(change)
    with pytest.raises(SeriesValidationError) as caught:
        build([observation])
    assert caught.value.input_position == 1


def test_missing_field_and_non_mapping_fail_closed():
    for observation in [{"cod_mun": "05001"}, None]:
        with pytest.raises(SeriesValidationError):
            build([observation])


def test_duplicates_block_even_outside_selection():
    with pytest.raises(SeriesValidationError) as caught:
        build([row(event=220), row(event=220)])
    assert caught.value.code == "duplicate"


def test_declared_grid_does_not_infer_undeclared_intermediate_weeks():
    declared = grid(((2020, 1), (2020, 3)))
    result = build([row(week=1), row(week=3)], declared)
    assert [p.period for p in result.series[0].points] == [(2020, 1), (2020, 3)]
    assert result.series[0].coverage.status == "complete_in_declared_grid"
    assert result.series[0].coverage.calendar_verification == "unverified"
