"""B05-I1: read-only orchestration of B04 CSV loading and B03 series."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from os import PathLike
from typing import BinaryIO

from episentinel.data.csv_loader import load_csv
from episentinel.data.epidemiological_series import (
    MunicipalIdentity, PeriodGrid, SeriesBundle, SeriesValidationError, build_series,
)


@dataclass(frozen=True)
class PipelineConfig:
    version: str
    territory: MunicipalIdentity
    event_codes: tuple[int, ...]
    period_grid: PeriodGrid

    def __post_init__(self):
        # Snapshot common mutable event selections without duplicating B03 rules.
        if isinstance(self.event_codes, list):
            object.__setattr__(self, "event_codes", tuple(self.event_codes))


@dataclass(frozen=True)
class PipelineIssue:
    stage: str
    code: str
    reason: str
    source: str | None = None
    record: int | None = None
    column: str | None = None
    input_position: int | None = None
    event_code: int | None = None


@dataclass(frozen=True)
class LoadDiagnostic:
    source: str
    sha256: str
    contract_version: str
    blocked: bool
    report: dict
    pending_decisions: tuple[dict, ...]


@dataclass(frozen=True)
class PipelineResult:
    status: str
    config: PipelineConfig | None
    load_diagnostic: LoadDiagnostic | None
    series: SeriesBundle | None
    warnings: tuple[PipelineIssue, ...]
    errors: tuple[PipelineIssue, ...]


def _load_issue(item):
    return PipelineIssue("load", item["code"], item["reason"],
                         source=item.get("source"), record=item.get("record"),
                         column=item.get("column"))


def run_pipeline(
    source: str | PathLike | bytes | BinaryIO,
    *,
    config: PipelineConfig,
    source_name: str | None = None,
) -> PipelineResult:
    """Load once and build once, exposing series only after complete success.

    B04 owns CSV validation; B03 owns temporal, event and territorial invariants.
    Binary streams follow B04 semantics: current cursor to EOF, not closed/reset.
    Expected input/validation failures become structured results. Programming errors
    are not silently swallowed. No writes, models or signal services are invoked.
    """
    if not isinstance(config, PipelineConfig):
        error = PipelineIssue("configuration", "invalid_configuration", "PipelineConfig is required")
        return PipelineResult("blocked", None, None, None, (), (error,))
    if not isinstance(config.event_codes, tuple):
        error = PipelineIssue("configuration", "invalid_event_selection", "Event selection must be a tuple or list")
        return PipelineResult("blocked", None, None, None, (), (error,))
    snapshot = deepcopy(config)
    if not isinstance(snapshot.version, str) or not snapshot.version.strip():
        error = PipelineIssue("configuration", "invalid_version", "Configuration version must be nonempty text")
        return PipelineResult("blocked", snapshot, None, None, (), (error,))
    try:
        loaded = load_csv(source, source_name=source_name)
    except (OSError, TypeError) as exc:
        code = "source_io_error" if isinstance(exc, OSError) else "source_type_error"
        error = PipelineIssue("load", code, str(exc))
        return PipelineResult("failed", snapshot, None, None, (), (error,))
    diagnostic = LoadDiagnostic(loaded.source, loaded.sha256, loaded.contract_version,
                                loaded.blocked, deepcopy(loaded.report),
                                tuple(deepcopy(loaded.pending_decisions)))
    warnings = tuple(_load_issue(item) for item in diagnostic.report["warnings"])
    errors = tuple(_load_issue(item) for item in diagnostic.report["errors"])
    if loaded.blocked or errors:
        if not errors:
            errors = (PipelineIssue("load", "load_blocked", "CSV loader rejected the source"),)
        return PipelineResult("blocked", snapshot, diagnostic, None, warnings, errors)
    if loaded.data is None:
        error = PipelineIssue("load", "invalid_load_result", "Accepted load did not provide data")
        return PipelineResult("failed", snapshot, diagnostic, None, warnings, (error,))
    try:
        bundle = build_series(deepcopy(loaded.data), territory=snapshot.territory,
                              event_codes=snapshot.event_codes, period_grid=snapshot.period_grid)
    except SeriesValidationError as exc:
        stage = "configuration" if exc.input_position is None else "series"
        error = PipelineIssue(stage, exc.code, str(exc), input_position=exc.input_position)
        return PipelineResult("blocked", snapshot, diagnostic, None, warnings, (error,))
    series_warnings = []
    for series in bundle.series:
        series_warnings.append(PipelineIssue("series", "eligibility_not_evaluated",
                                             ", ".join(series.eligibility.reasons), event_code=series.event_code))
        if series.coverage.missing_periods:
            series_warnings.append(PipelineIssue("series", "coverage_incomplete",
                                                 "Missing observations in the explicitly declared grid",
                                                 event_code=series.event_code))
        if series.coverage.observed_periods == 0:
            series_warnings.append(PipelineIssue("series", "no_selected_observations",
                                                 "No observations for the selected territory/event",
                                                 event_code=series.event_code))
    return PipelineResult("completed", snapshot, diagnostic, bundle,
                          warnings + tuple(series_warnings), ())
