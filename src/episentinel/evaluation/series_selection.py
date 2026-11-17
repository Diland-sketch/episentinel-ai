"""Causal selection from an explicitly supplied candidate universe and prefix only."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np
import pandas as pd

from .temporal_protocol import TemporalProtocol, positive_integer, validate_protocol


@dataclass(frozen=True, slots=True)
class EligibilityCriteria:
    """Caller-specified thresholds, not statistical or epidemiological eligibility.

    Missing/invalid initial prefixes are always excluded; no imputation occurs.
    min_positive=None disables that filter. No historical threshold is implied.
    """

    min_observed: int
    max_series: int
    min_positive: int | None = None

    def __post_init__(self):
        for name in ("min_observed", "max_series"):
            object.__setattr__(self, name, positive_integer(getattr(self, name), name))
        if self.min_positive is not None:
            object.__setattr__(self, "min_positive", positive_integer(self.min_positive, "min_positive"))


@dataclass(frozen=True, slots=True)
class SelectionRecord:
    code: str
    score: float | None
    n_observed: int
    n_positive: int
    eligible: bool
    selected: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FrozenCohort:
    train_size: int
    criteria: EligibilityCriteria
    candidate_codes: tuple[str, ...]
    selected_codes: tuple[str, ...]
    records: tuple[SelectionRecord, ...]
    score_rule: str = "initial_training_sum_desc_code_asc"


def select_cohort(
    series: Mapping[str, pd.Series], *, candidate_codes: tuple[str, ...],
    protocol: TemporalProtocol, criteria: EligibilityCriteria,
) -> FrozenCohort:
    """Read only iloc[:train_size]; neither index labels nor future values are used.

    Candidate codes must be supplied from an approved catalogue or initial data.
    Extra mapping entries are ignored, so future-only territories cannot enter.
    Each series must already have the same positional grid; its provenance and
    calendar are external prerequisites, not inferred from a pandas index.
    """
    validate_protocol(protocol)
    if not isinstance(criteria, EligibilityCriteria):
        raise TypeError("criteria must be EligibilityCriteria")
    if criteria.min_observed > protocol.train_size or (
        criteria.min_positive is not None and criteria.min_positive > protocol.train_size
    ):
        raise ValueError("eligibility threshold exceeds initial training size")
    if not isinstance(series, Mapping):
        raise TypeError("series must be a mapping")
    if type(candidate_codes) is not tuple or not candidate_codes:
        raise ValueError("provide an explicit nonempty candidate_codes tuple")
    if any(type(c) is not str or not c or c != c.strip() for c in candidate_codes):
        raise ValueError("candidate codes must be nonempty canonical strings")
    if len(set(candidate_codes)) != len(candidate_codes):
        raise ValueError("duplicate candidate codes")

    candidates = tuple(sorted(candidate_codes))
    assessed = []
    for code in candidates:
        if code not in series:
            assessed.append((code, None, 0, 0, ("series_absent",)))
            continue
        source = series[code]
        if not isinstance(source, pd.Series):
            raise TypeError(f"{code}: expected pd.Series")
        prefix = source.iloc[:protocol.train_size]
        reasons = []
        if len(prefix) != protocol.train_size:
            reasons.append("insufficient_initial_history")
        values = []
        for value in prefix:
            if value is None or value is pd.NA or value is pd.NaT:
                reasons.append("missing_initial_value")
                continue
            if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
                reasons.append("invalid_initial_value")
                continue
            try:
                number = float(value)
            except (ValueError, OverflowError):
                reasons.append("invalid_initial_value")
                continue
            if math.isnan(number):
                reasons.append("missing_initial_value")
                continue
            if not math.isfinite(number) or number < 0:
                reasons.append("invalid_initial_value")
                continue
            exact = int(number) == int(value) if isinstance(value, Integral) else number == value
            if not exact:
                reasons.append("inexact_initial_value")
                continue
            values.append(number)
        n_observed = len(values)
        n_positive = sum(value > 0 for value in values)
        if n_observed < criteria.min_observed:
            reasons.append("min_observed_not_met")
        if criteria.min_positive is not None and n_positive < criteria.min_positive:
            reasons.append("min_positive_not_met")
        score = None
        if not any(r in reasons for r in (
            "insufficient_initial_history", "missing_initial_value",
            "invalid_initial_value", "inexact_initial_value",
        )):
            try:
                score = math.fsum(values)
            except OverflowError:
                reasons.append("nonfinite_score")
        assessed.append((code, score, n_observed, n_positive, tuple(dict.fromkeys(reasons))))

    ranking = sorted((row for row in assessed if not row[4]), key=lambda row: (-row[1], row[0]))
    selected = tuple(row[0] for row in ranking[:criteria.max_series])
    records = tuple(SelectionRecord(
        code, score, observed, positive, not reasons, code in selected,
        reasons if reasons else (() if code in selected else ("outside_top_k",)),
    ) for code, score, observed, positive, reasons in assessed)
    return FrozenCohort(protocol.train_size, criteria, candidates, selected, records)
