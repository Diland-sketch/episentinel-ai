"""Pure rolling-origin planning, with one shared schedule and no model execution."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral

from .temporal_protocol import B06_METHODS, TemporalProtocol, validate_protocol


@dataclass(frozen=True, slots=True)
class Origin:
    partition: str
    cut: int
    train_start: int
    target_start: int
    target_end: int  # exclusive
    methods: tuple[str, ...] = B06_METHODS

    @property
    def target_positions(self) -> tuple[int, ...]:
        return tuple(range(self.target_start, self.target_end))


@dataclass(frozen=True, slots=True)
class ExcludedOrigin:
    partition: str
    cut: int
    reason: str = "incomplete_partition_horizon"


@dataclass(frozen=True, slots=True)
class RollingPlan:
    protocol: TemporalProtocol
    origins: tuple[Origin, ...]
    excluded: tuple[ExcludedOrigin, ...]


def _bounds(protocol: TemporalProtocol, partition: str) -> tuple[int, int]:
    if partition == "validation":
        return protocol.train_size, protocol.validation_end
    if partition == "test":
        return protocol.validation_end, protocol.total_size
    raise ValueError("partition must be validation or test")


def validate_origin(protocol: TemporalProtocol, *, partition: str, cut: int) -> Origin:
    """Reject explicit incomplete, misaligned or out-of-partition requests."""
    validate_protocol(protocol)
    start, end = _bounds(protocol, partition)
    if isinstance(cut, bool) or not isinstance(cut, Integral):
        raise ValueError("cut must be an integer")
    cut = int(cut)
    if cut < start - 1 or (cut - (start - 1)) % protocol.step:
        raise ValueError("cut is outside the partition origin grid")
    if cut + protocol.horizon >= end:
        raise ValueError("incomplete horizon or partition boundary crossed")
    return Origin(partition, cut, 0, cut + 1, cut + 1 + protocol.horizon, protocol.methods)


def plan_rolling_origin(protocol: TemporalProtocol) -> RollingPlan:
    """Restart the step grid at each partition; record incomplete tail candidates."""
    validate_protocol(protocol)
    origins, excluded = [], []
    for partition in ("validation", "test"):
        start, end = _bounds(protocol, partition)
        for cut in range(start - 1, end - 1, protocol.step):
            if cut + protocol.horizon >= end:
                excluded.append(ExcludedOrigin(partition, cut))
            else:
                origins.append(validate_origin(protocol, partition=partition, cut=cut))
    return RollingPlan(protocol, tuple(origins), tuple(excluded))
