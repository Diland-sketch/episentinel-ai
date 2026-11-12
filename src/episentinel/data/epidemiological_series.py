"""B03-I1: explicit periods, municipal candidates and separate event series.

No date inference, aggregation, imputation, I/O or forecasting is performed.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from numbers import Integral
import re

from .csv_contract import EVENTS, classify_territory

Period = tuple[int, int]


class SeriesValidationError(ValueError):
    """Blocking structural error; no partial SeriesBundle is returned."""

    def __init__(self, code: str, message: str, input_position: int | None = None):
        self.code = code
        self.input_position = input_position
        super().__init__(message)


def _integer(value, name, minimum, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, Integral)
            or value < minimum or (maximum is not None and value > maximum)):
        raise SeriesValidationError("invalid_value", f"{name}: invalid integer {value!r}")
    return int(value)


def _period(value) -> Period:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise SeriesValidationError("invalid_period", "Period must be an explicit (year, week) pair")
    return (_integer(value[0], "ano", 1000, 9999), _integer(value[1], "semana", 1, 53))


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise SeriesValidationError("invalid_metadata", f"{name}: nonempty text required")


def _code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{5}", value):
        raise SeriesValidationError("invalid_territory", "Territorial code must have exactly five digits")
    return value


@dataclass(frozen=True)
class CalendarMetadata:
    calendar_id: str
    version: str
    source: str
    verification: str = "unverified"
    evidence: str | None = None

    def __post_init__(self):
        for name in ("calendar_id", "version", "source"):
            _text(getattr(self, name), name)
        if self.verification not in {"unverified", "verified"}:
            raise SeriesValidationError("invalid_metadata", "Unknown calendar verification state")
        if self.verification == "verified" or self.evidence is not None:
            _text(self.evidence, "evidence")


@dataclass(frozen=True)
class PeriodGrid:
    periods: tuple[Period, ...]
    metadata: CalendarMetadata

    def __post_init__(self):
        if not isinstance(self.metadata, CalendarMetadata):
            raise SeriesValidationError("invalid_metadata", "CalendarMetadata is required")
        if not isinstance(self.periods, (tuple, list)):
            raise SeriesValidationError("invalid_grid", "Provide explicit periods as a tuple or list")
        periods = tuple(_period(p) for p in self.periods)
        if not periods or any(a >= b for a, b in zip(periods, periods[1:])):
            raise SeriesValidationError("invalid_grid", "Grid must be nonempty, unique and strictly ordered")
        object.__setattr__(self, "periods", periods)


@dataclass(frozen=True)
class MunicipalIdentity:
    code: str

    def __post_init__(self):
        _code(self.code)
        if classify_territory(self.code) != "municipal_candidate":
            raise SeriesValidationError("special_territory", "Special territory cannot identify a municipal series")

    @property
    def catalog_validation(self) -> str:
        return "pending"


@dataclass(frozen=True)
class SourceReference:
    input_position: int
    source: str | None
    record: int | None


@dataclass(frozen=True)
class SeriesPoint:
    period: Period
    observed_count: int | None
    observation_status: str
    source_refs: tuple[SourceReference, ...]


@dataclass(frozen=True)
class Coverage:
    expected_periods: int
    observed_periods: int
    missing_periods: tuple[Period, ...]
    calendar_verification: str

    @property
    def status(self) -> str:
        return "complete_in_declared_grid" if not self.missing_periods else "incomplete_in_declared_grid"


@dataclass(frozen=True)
class Eligibility:
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EventSeries:
    event_code: int
    points: tuple[SeriesPoint, ...]
    coverage: Coverage
    eligibility: Eligibility

    @property
    def observed_total(self) -> int | None:
        """Diagnostic sum of observed counts, or None if nothing was observed."""
        counts = [p.observed_count for p in self.points if p.observed_count is not None]
        return sum(counts) if counts else None


@dataclass(frozen=True)
class SelectionSummary:
    input_records: int
    selected_records: int
    unselected_records: int


@dataclass(frozen=True)
class SeriesBundle:
    territory: MunicipalIdentity
    grid: PeriodGrid
    event_codes: tuple[int, ...]
    series: tuple[EventSeries, ...]
    selection: SelectionSummary
    structural_integrity: str = "valid"


def build_series(
    observations: Iterable[Mapping[str, object]],
    *,
    territory: MunicipalIdentity,
    event_codes: Iterable[int],
    period_grid: PeriodGrid,
) -> SeriesBundle:
    """Build independent series on a supplied grid; reject rather than repair.

    Input must already have passed the B04 validation gate. Invariants are checked
    again across the entire supplied collection, including cross-source duplicates.
    Grid membership is checked only for the explicitly selected territory/events.
    """
    if not isinstance(territory, MunicipalIdentity) or not isinstance(period_grid, PeriodGrid):
        raise SeriesValidationError("invalid_configuration", "MunicipalIdentity and PeriodGrid are required")
    if not isinstance(event_codes, Iterable) or not isinstance(observations, Iterable):
        raise SeriesValidationError("invalid_configuration", "Observations and event selection must be iterable")
    events = tuple(_integer(e, "cod_eve", 0) for e in event_codes)
    if not events or len(set(events)) != len(events) or not set(events) <= EVENTS:
        raise SeriesValidationError("invalid_events", "Select unique supported events explicitly")
    domain = set(period_grid.periods)
    seen, selected = set(), {}
    n_input = 0
    for position, raw in enumerate(observations, 1):
        n_input = position
        try:
            if not isinstance(raw, Mapping):
                raise SeriesValidationError("invalid_record", "Observation must be a mapping")
            code = _code(raw["cod_mun"])
            period = _period((raw["ano"], raw["semana"]))
            event = _integer(raw["cod_eve"], "cod_eve", 0)
            if event not in EVENTS:
                raise SeriesValidationError("invalid_events", "Observation event outside contract")
            count = _integer(raw["conteo"], "conteo", 0)
            source, record = raw.get("source"), raw.get("record")
            if source is not None:
                _text(source, "source")
            if record is not None:
                record = _integer(record, "record", 1)
            key = code, event, period
            if key in seen:
                raise SeriesValidationError("duplicate", f"Repeated observation key: {key}")
            seen.add(key)
            if code == territory.code and event in events:
                if period not in domain:
                    raise SeriesValidationError("outside_grid", f"Selected observation outside grid: {period}")
                selected[event, period] = (count, SourceReference(position, source, record))
        except KeyError as exc:
            raise SeriesValidationError("missing_field", f"Required field missing: {exc}", position) from exc
        except SeriesValidationError as exc:
            if exc.input_position is None:
                exc.input_position = position
            raise
    outputs = []
    for event in events:
        points, missing = [], []
        for period in period_grid.periods:
            match = selected.get((event, period))
            if match is None:
                missing.append(period)
            points.append(SeriesPoint(period, None if match is None else match[0],
                                      "missing" if match is None else "observed",
                                      () if match is None else (match[1],)))
        reasons = ["method_not_evaluated", "dates_unassigned", "territorial_catalog_pending"]
        if period_grid.metadata.verification == "unverified":
            reasons.append("calendar_unverified")
        if missing:
            reasons.append("missing_observations")
        coverage = Coverage(len(points), len(points) - len(missing), tuple(missing),
                            period_grid.metadata.verification)
        outputs.append(EventSeries(event, tuple(points), coverage, Eligibility("not_evaluated", tuple(reasons))))
    return SeriesBundle(territory, period_grid, events, tuple(outputs),
                        SelectionSummary(n_input, len(selected), n_input - len(selected)))
