"""B07-I1: causal, per-rule signals on the explicit B03 period grid."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from math import inf, isfinite, nextafter, ulp
from numbers import Integral, Real
from sys import float_info

import pandas as pd

from episentinel.data.epidemiological_series import (
    CalendarMetadata, SeriesBundle, SeriesPoint,
)
from episentinel.detection.alertas import ears_c2

RULES = ("ears_c2", "canal_endemico", "sarima_one_step")
# At this binade float64 spacing reaches one count. Require subunit resolution.
_SUBUNIT_LIMIT = 1 << (float_info.mant_dig - 1)
_UNAVAILABLE_REASONS = {
    "missing_observation": "No observed count exists for this period; absence is not zero.",
    "forecast_service_pending": "A causal one-step forecast contract from B06 is not available.",
    "explicit_period_channel_pending": "The historical 52-position channel is incompatible with the B03 grid.",
    "calendar_unverified": "Calendar metadata is unverified; a weekly reference cannot be assumed.",
    "insufficient_reference": "Fewer than base + guard previous periods are available.",
    "calendar_boundary_pending": "The reference window crosses a year boundary requiring calendar decisions.",
    "nonconsecutive_grid": "The local grid omits intermediate week numbers; it cannot be compressed.",
    "missing_reference": "At least one required historical reference count is missing.",
    "numeric_precision_unsupported": "Float64 cannot certify the reference, threshold and score comparison.",
}


@dataclass(frozen=True)
class EarsC2Config:
    base: int = 7
    guard: int = 2
    k: float = 3.0
    min_sd: float = 1.0
    min_casos: int = 3

    def __post_init__(self):
        for name, minimum in (("base", 2), ("guard", 0), ("min_casos", 0)):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
            object.__setattr__(self, name, int(value))
        for name in ("k", "min_sd"):
            value = getattr(self, name)
            if (isinstance(value, bool) or not isinstance(value, Real)
                    or not isfinite(value) or value < 0 or (name == "min_sd" and value == 0)):
                raise ValueError(f"{name} must be finite and {'positive' if name == 'min_sd' else 'nonnegative'}")
            object.__setattr__(self, name, float(value))


@dataclass(frozen=True)
class SignalEvaluation:
    period: tuple[int, int]
    event_code: int
    territory_code: str
    rule: str
    status: str
    observed_count: int | None
    reference: tuple[SeriesPoint, ...]
    reference_mean: float | None
    reference_sd: float | None
    effective_sd: float | None
    threshold: float | None
    score: float | None
    reason: str
    not_evaluable_reason: str | None
    parameters: dict


@dataclass(frozen=True)
class SignalReport:
    contract_version: str
    calendar: CalendarMetadata
    results: tuple[SignalEvaluation, ...]


def _validate_bundle(bundle):
    if not isinstance(bundle, SeriesBundle):
        raise TypeError("bundle must be a B03 SeriesBundle")
    if bundle.structural_integrity != "valid":
        raise ValueError("SeriesBundle must have valid structural integrity")
    if tuple(s.event_code for s in bundle.series) != bundle.event_codes:
        raise ValueError("SeriesBundle event selection does not match its series")
    for series in bundle.series:
        if tuple(p.period for p in series.points) != bundle.grid.periods:
            raise ValueError("Series points must match the explicit period grid")
        for point in series.points:
            count = point.observed_count
            if count is None:
                if point.observation_status != "missing":
                    raise ValueError("Missing counts require missing observation status")
            elif (isinstance(count, bool) or not isinstance(count, Integral) or count < 0
                  or point.observation_status != "observed"):
                raise ValueError("Observed counts must be nonnegative integers with observed status")


def _compare_scaled(delta: Fraction, variance: Fraction, bound: Fraction) -> int:
    """Exact sign of delta / sqrt(variance) - bound, without rounding a root."""
    if delta < 0 <= bound:
        return -1
    if bound < 0 <= delta:
        return 1
    left, right = delta * delta, bound * bound * variance
    relation = (left > right) - (left < right)
    return -relation if delta < 0 else relation


def _precision_supported(counts, observed, config, statistics, signal):
    """Certify float outputs against exact rational statistics; never classify.

    Statistics may be rounded by at most one adjacent float. The strict
    comparison, including equality, must agree exactly in both published
    threshold and score. This gate only rejects a historical-kernel result.
    """
    mean, sd, effective_sd, threshold, score = statistics
    if any(ulp(value) >= 1 for value in statistics):
        return False
    n, total = len(counts), sum(counts)
    exact_mean = Fraction(total, n)
    variance = Fraction(n * sum(c * c for c in counts) - total * total, n * (n - 1))
    effective_variance = max(variance, Fraction(config.min_sd) ** 2)
    k, delta = Fraction(config.k), Fraction(observed) - exact_mean

    def bounds(value):
        return Fraction(nextafter(value, -inf)), Fraction(nextafter(value, inf))

    lower, upper = bounds(mean)
    if not lower <= exact_mean <= upper:
        return False
    for value, squared in ((sd, variance), (effective_sd, effective_variance)):
        lower, upper = bounds(value)
        if not max(lower, Fraction(0)) ** 2 <= squared <= upper ** 2:
            return False
    lower, upper = bounds(threshold)
    if (_compare_scaled(lower - exact_mean, effective_variance, k) > 0
            or _compare_scaled(upper - exact_mean, effective_variance, k) < 0):
        return False
    lower, upper = bounds(score)
    if (_compare_scaled(delta, effective_variance, lower) < 0
            or _compare_scaled(delta, effective_variance, upper) > 0):
        return False
    relation = _compare_scaled(delta, effective_variance, k)
    threshold_relation = (observed > threshold) - (observed < threshold)
    score_relation = (score > config.k) - (score < config.k)
    return (threshold_relation == score_relation == relation
            and signal == (relation > 0 and observed >= config.min_casos))


def evaluate_signals(
    bundle: SeriesBundle, *, ears_config: EarsC2Config | None = None,
    rules: tuple[str, ...] = RULES,
) -> SignalReport:
    """Evaluate independent rules; no aggregation, dates, writes or model fitting.

    B05-I1 consumers pass PipelineResult.series only after status='completed'.
    EARS requires verified calendar metadata and a consecutive within-year
    window. Cross-year interpretation, endemic channel and B06 remain pending.
    """
    _validate_bundle(bundle)
    config = EarsC2Config() if ears_config is None else ears_config
    if not isinstance(config, EarsC2Config):
        raise TypeError("ears_config must be EarsC2Config or None")
    if (not isinstance(rules, (tuple, list)) or not rules
            or any(not isinstance(rule, str) or rule not in RULES for rule in rules)
            or len(set(rules)) != len(rules)):
        raise ValueError("rules must select unique supported rules")
    outputs = []
    for series in bundle.series:
        for position, point in enumerate(series.points):
            for rule in rules:
                parameters = asdict(config) if rule == "ears_c2" else {"integration": "pending"}
                reference = ()
                if rule == "ears_c2":
                    start = max(0, position - config.guard - config.base)
                    stop = max(0, position - config.guard)
                    reference = series.points[start:stop]

                def result(status, reason, *, unavailable=None, mean=None, sd=None,
                           effective_sd=None, threshold=None, score=None):
                    return SignalEvaluation(
                        point.period, series.event_code, bundle.territory.code, rule,
                        status, point.observed_count, reference, mean, sd, effective_sd,
                        threshold, score, reason, unavailable, dict(parameters),
                    )

                unavailable = None
                if point.observed_count is None:
                    unavailable = "missing_observation"
                elif rule == "sarima_one_step":
                    unavailable = "forecast_service_pending"
                elif rule == "canal_endemico":
                    unavailable = "explicit_period_channel_pending"
                elif bundle.grid.metadata.verification != "verified":
                    unavailable = "calendar_unverified"
                elif position < config.base + config.guard:
                    unavailable = "insufficient_reference"
                else:
                    # Only the local window ending at T is inspected, never a suffix.
                    window = series.points[position - config.base - config.guard:position + 1]
                    if any(p.period[0] != point.period[0] for p in window):
                        unavailable = "calendar_boundary_pending"
                    elif any(b.period[1] != a.period[1] + 1 for a, b in zip(window, window[1:])):
                        unavailable = "nonconsecutive_grid"
                    elif any(p.observed_count is None for p in reference):
                        unavailable = "missing_reference"
                if unavailable:
                    outputs.append(result("not_evaluable", _UNAVAILABLE_REASONS[unavailable],
                                          unavailable=unavailable))
                    continue

                # Reuse the historical numerical EARS kernel with a local RangeIndex.
                # Guard values are unused; reserve their positions without converting them.
                counts = [int(p.observed_count) for p in reference]
                observed = int(point.observed_count)
                if any(count >= _SUBUNIT_LIMIT for count in (*counts, observed)):
                    code = "numeric_precision_unsupported"
                    outputs.append(result("not_evaluable", _UNAVAILABLE_REASONS[code], unavailable=code))
                    continue
                try:
                    values = pd.Series(counts + [None] * config.guard + [observed], dtype="float64")
                    historical = values.shift(config.guard + 1).rolling(config.base)
                    mean = float(historical.mean().iloc[-1])
                    sd = float(historical.std().iloc[-1])  # same reductions and ddof as ears_c2
                    effective_sd = max(sd, config.min_sd)
                    threshold = mean + config.k * effective_sd
                    computed = ears_c2(values, **parameters).iloc[-1]
                    score = float(computed["z_ears"])
                except (OverflowError, ValueError):
                    outputs.append(result("not_evaluable", "Counts exceed numeric evaluation range",
                                          unavailable="numeric_range"))
                    continue
                if not all(isfinite(v) for v in (mean, sd, effective_sd, threshold, score)):
                    outputs.append(result("not_evaluable", "Nonfinite numeric reference or score",
                                          unavailable="numeric_range"))
                    continue
                signal = bool(computed["alerta_ears"])
                statistics = (mean, sd, effective_sd, threshold, score)
                if not _precision_supported(counts, observed, config, statistics, signal):
                    code = "numeric_precision_unsupported"
                    outputs.append(result("not_evaluable", _UNAVAILABLE_REASONS[code], unavailable=code))
                    continue
                if signal:
                    explanation = "Observed exceeds mean + k * effective SD and meets min_casos"
                elif point.observed_count < config.min_casos:
                    explanation = "EARS evaluated; observed count is below min_casos"
                else:
                    explanation = "EARS evaluated; z does not strictly exceed k"
                outputs.append(result("signal" if signal else "no_signal", explanation,
                                      mean=mean, sd=sd, effective_sd=effective_sd,
                                      threshold=threshold, score=score))
    return SignalReport("1", bundle.grid.metadata, tuple(outputs))
