"""Pure positional planning, including illustrative historical-sized boundaries."""
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from episentinel.evaluation.rolling_origin import plan_rolling_origin, validate_origin
from episentinel.evaluation.temporal_protocol import B06_METHODS, TemporalProtocol, validate_protocol


def test_illustrative_positions_have_24_complete_origins_without_crossing():
    protocol = TemporalProtocol(728, 780, 832)
    plan = plan_rolling_origin(protocol)
    validation = tuple(o for o in plan.origins if o.partition == "validation")
    test = tuple(o for o in plan.origins if o.partition == "test")
    assert tuple(o.cut for o in validation) == tuple(range(727, 772, 4))
    assert tuple(o.cut for o in test) == tuple(range(779, 824, 4))
    assert len(plan.origins) == 24
    for origin in plan.origins:
        start, end = (728, 780) if origin.partition == "validation" else (780, 832)
        assert origin.train_start == 0
        assert origin.target_start == origin.cut + 1
        assert origin.target_positions == tuple(range(origin.cut + 1, origin.cut + 9))
        assert start <= origin.target_start < origin.target_end <= end
        assert len(origin.target_positions) == 8
        assert origin.methods == B06_METHODS
    assert tuple((o.partition, o.cut) for o in plan.excluded) == (("validation", 775), ("test", 827))
    schedules = {m: tuple(o.cut for o in plan.origins if m in o.methods) for m in B06_METHODS}
    assert len(set(schedules.values())) == 1


@pytest.mark.parametrize("length", [8, 9, 10, 11, 12, 13, 51, 52, 53])
def test_partial_tail_is_recorded_never_truncated(length):
    protocol = TemporalProtocol(10, 10 + length, 10 + 2 * length)
    plan = plan_rolling_origin(protocol)
    assert len(plan.origins) == 2 * ((length - 8) // 4 + 1)
    assert all(o.target_end - o.target_start == 8 for o in plan.origins)
    assert all(o.reason == "incomplete_partition_horizon" for o in plan.excluded)
    with pytest.raises(FrozenInstanceError):
        plan.origins = ()


@pytest.mark.parametrize("changes", [
    {"train_size": 0}, {"train_size": True}, {"train_size": 8.0},
    {"validation_end": 8}, {"validation_end": 15}, {"total_size": 20},
    {"total_size": 27}, {"horizon": 4}, {"step": 8}, {"step": False},
    {"window": "sliding"}, {"cohort_policy": "per_origin"},
    {"methods": [*B06_METHODS]}, {"methods": B06_METHODS[:2]},
    {"methods": tuple(reversed(B06_METHODS))},
])
def test_invalid_or_ambiguous_protocol_rejected(changes):
    args = dict(train_size=8, validation_end=20, total_size=32)
    args.update(changes)
    with pytest.raises(ValueError):
        TemporalProtocol(**args)


@pytest.mark.parametrize("partition,cut", [
    ("validation", 6), ("validation", 8), ("validation", 15),
    ("validation", 19), ("test", 15), ("test", 27),
    ("test", True), ("test", 19.0), ("unknown", 19),
])
def test_explicit_invalid_origin_rejected(partition, cut):
    with pytest.raises(ValueError):
        validate_origin(TemporalProtocol(8, 20, 32), partition=partition, cut=cut)


def test_exclusive_boundaries_and_inclusive_cut_are_not_confused():
    protocol = TemporalProtocol(8, 20, 32)
    origin = validate_origin(protocol, partition="test", cut=19)
    assert origin.target_positions == tuple(range(20, 28))
    assert origin.cut + 1 == 20  # training includes positions 0..19
    assert validate_protocol(protocol) is protocol
    with pytest.raises(TypeError):
        plan_rolling_origin({"train_size": 8})


def test_config_is_an_explicit_non_operational_example():
    path = Path(__file__).resolve().parents[1] / "configs" / "evaluacion_b10.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["real_execution_authorized"] is False
    assert config["selection_criteria"] is None
    assert config["candidate_universe"] is None
    args = dict(config["positional_example"])
    args["methods"] = tuple(args["methods"])
    assert len(plan_rolling_origin(TemporalProtocol(**args)).origins) == 24
