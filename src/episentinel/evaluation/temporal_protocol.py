"""B10-I1/I2: explicit positional protocol; no calendar inference or model calls."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral


B06_METHODS = (
    "ultimo_valor", "ingenua_estacional", "sarima_sin_estacional", "sarima_estacional",
)


def positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


@dataclass(frozen=True, slots=True)
class TemporalProtocol:
    """Boundaries are exclusive counts, origins are inclusive zero-based positions.

    Partition: [0, train_size), [train_size, validation_end),
    [validation_end, total_size). Positions alone do not certify weekly spacing.
    """

    train_size: int
    validation_end: int
    total_size: int
    horizon: int = 8
    step: int = 4
    window: str = "expanding"
    cohort_policy: str = "fixed_initial_training"
    methods: tuple[str, ...] = B06_METHODS

    def __post_init__(self):
        for name in ("train_size", "validation_end", "total_size", "horizon", "step"):
            object.__setattr__(self, name, positive_integer(getattr(self, name), name))
        if self.horizon != 8 or self.step != 4:
            raise ValueError("B10-I2 requires horizon=8 and step=4")
        if self.window != "expanding" or self.cohort_policy != "fixed_initial_training":
            raise ValueError("B10-I2 requires expanding windows and a fixed initial cohort")
        if type(self.methods) is not tuple or self.methods != B06_METHODS:
            raise ValueError("methods must be the canonical tuple of all four B06 methods")
        if not 0 < self.train_size < self.validation_end < self.total_size:
            raise ValueError("partition boundaries must be strictly increasing")
        if min(self.validation_end - self.train_size,
               self.total_size - self.validation_end) < self.horizon:
            raise ValueError("each evaluation partition must contain a complete horizon")


def validate_protocol(protocol: TemporalProtocol) -> TemporalProtocol:
    """Return the validated immutable protocol; reject implicit dict coercions."""
    if not isinstance(protocol, TemporalProtocol):
        raise TypeError("protocol must be TemporalProtocol")
    return protocol
