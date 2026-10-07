"""prereg-v3 addendum A8 (ii): un-exempted hard-contact floor in M4's safety monitor.

`SafetyLimits.hard_contact_floor_m` (default 0.0, off) applies the
min-distance stop to a pair closer than the floor EVEN when a clearing
maneuver's exemption covers it. With the floor off, `evaluate_latches` must
be byte-identical to the pre-change monitor: the goldens in
`data/safety_floor/default_latches.json` were written by `_golden_latches`
below on the untouched integration tip (19a1859) before any edit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from swarm_execution.safety import (
    REASON_HARD_CONTACT_FLOOR,
    REASON_MIN_DISTANCE,
    ClearingExemption,
    CoordinationTracker,
    SafetyLimits,
    evaluate_latches,
)
from swarm_execution.safety_monitor_node import SafetyMonitorNode, hard_contact_floor_detail

_GOLDEN = Path(__file__).parent / "data" / "safety_floor" / "default_latches.json"

# The IB10 release geometry at the v3 contact (GT centre distance 0.084 m),
# a pull-off pass (0.21 m) and a clean separation, each with and without the
# release exemption, plus a STALE robot inside the band.
_EXEMPT_PAIR = ClearingExemption(
    clearing_robots=frozenset({"robot_3"}), pairs=frozenset({("robot_3", "robot_4")})
)
_SCENES: dict[str, tuple[list[dict], ClearingExemption | frozenset[str]]] = {
    "contact_exempt": (
        [
            {"robot_id": "robot_3", "x": 0.0, "y": -1.0, "status": "STOPPED"},
            {"robot_id": "robot_4", "x": 0.084, "y": -1.0, "status": "MOVING"},
            {"robot_id": "robot_1", "x": -1.02, "y": 0.38, "status": "STOPPED"},
        ],
        _EXEMPT_PAIR,
    ),
    "contact_not_exempt": (
        [
            {"robot_id": "robot_3", "x": 0.0, "y": -1.0, "status": "STOPPED"},
            {"robot_id": "robot_4", "x": 0.084, "y": -1.0, "status": "MOVING"},
        ],
        frozenset(),
    ),
    "pull_off_pass_exempt": (
        [
            {"robot_id": "robot_3", "x": -0.33, "y": -1.0, "status": "STOPPED"},
            {"robot_id": "robot_4", "x": -0.12, "y": -1.0, "status": "MOVING"},
        ],
        _EXEMPT_PAIR,
    ),
    "clear_exempt": (
        [
            {"robot_id": "robot_3", "x": 0.0, "y": -1.0, "status": "STOPPED"},
            {"robot_id": "robot_4", "x": 0.0, "y": 0.0, "status": "MOVING"},
        ],
        _EXEMPT_PAIR,
    ),
    "stale_in_band_exempt": (
        [
            {"robot_id": "robot_3", "x": 0.0, "y": -1.0, "status": "STALE"},
            {"robot_id": "robot_4", "x": 0.1, "y": -1.0, "status": "STALE"},
        ],
        _EXEMPT_PAIR,
    ),
    "robot_scope_exempt": (
        [
            {"robot_id": "robot_3", "x": 0.0, "y": -1.0},
            {"robot_id": "robot_4", "x": 0.05, "y": -1.0},
        ],
        frozenset({"robot_3"}),
    ),
}
_MEMORY = {("robot_3", "robot_4"): 0.12}


def _serialize(evaluation: Any) -> dict[str, Any]:
    return {
        "latched": sorted(evaluation.latched),
        "reasons": dict(sorted(evaluation.reasons.items())),
        "memory": {f"{a}+{b}": d for (a, b), d in sorted(evaluation.last_fresh_distances.items())},
    }


def _golden_latches(limits: SafetyLimits) -> dict[str, Any]:
    out = {}
    for name, (robots, exempt) in _SCENES.items():
        for previous in ((), ("robot_3", "robot_4")):
            for memory in (None, _MEMORY):
                key = f"{name}|prev={'+'.join(previous) or '-'}|mem={memory is not None}"
                out[key] = _serialize(
                    evaluate_latches(robots, limits, set(previous), memory, exempt)
                )
    return out


def _limits(**extra: Any) -> SafetyLimits:
    return SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2, **extra)


def _robots(name: str) -> list[dict]:
    return _SCENES[name][0]


# ---- default off: byte-identical to the pre-change monitor ----


def test_default_limits_latches_match_pre_change_golden():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert json.dumps(_golden_latches(_limits()), sort_keys=True) == json.dumps(
        golden, sort_keys=True
    )


def test_explicit_zero_floor_latches_match_pre_change_golden():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    latches = _golden_latches(_limits(hard_contact_floor_m=0.0))
    assert json.dumps(latches, sort_keys=True) == json.dumps(golden, sort_keys=True)


def test_zero_floor_records_no_breaches():
    evaluation = evaluate_latches(_robots("contact_exempt"), _limits(), exempt=_EXEMPT_PAIR)
    assert evaluation.floor_breaches == {}


def test_shipped_safety_yaml_keeps_the_floor_off():
    import yaml

    safety_yaml = (
        Path(__file__).resolve().parents[2] / "ros2_ws/src/swarm_execution/config/safety.yaml"
    )
    assert yaml.safe_load(safety_yaml.read_text())["safety"]["hard_contact_floor_m"] == 0.0


# ---- floor on ----


def test_floor_latches_an_exempt_pair_inside_it():
    evaluation = evaluate_latches(
        _robots("contact_exempt"), _limits(hard_contact_floor_m=0.2), exempt=_EXEMPT_PAIR
    )
    assert evaluation.latched == frozenset({"robot_3", "robot_4"})
    assert evaluation.reasons == {
        "robot_3": REASON_HARD_CONTACT_FLOOR,
        "robot_4": REASON_HARD_CONTACT_FLOOR,
    }
    assert evaluation.floor_breaches == {("robot_3", "robot_4"): pytest.approx(0.084)}


def test_floor_spares_an_exempt_pull_off_pass_above_it():
    # 0.21 m: the pull-off pass's worst case still sits above a 0.20 floor.
    evaluation = evaluate_latches(
        _robots("pull_off_pass_exempt"), _limits(hard_contact_floor_m=0.2), exempt=_EXEMPT_PAIR
    )
    assert evaluation.latched == frozenset()


def test_floor_is_strict_at_its_boundary():
    robots = [
        {"robot_id": "robot_3", "x": 0.0, "y": -1.0},
        {"robot_id": "robot_4", "x": 0.25, "y": -1.0},
    ]
    evaluation = evaluate_latches(robots, _limits(hard_contact_floor_m=0.25), exempt=_EXEMPT_PAIR)
    assert evaluation.latched == frozenset()


def test_floor_spares_a_bystander_outside_the_exempt_pair():
    # robot_1 is ~1.1 m away: neither the floor nor min_distance applies to it.
    evaluation = evaluate_latches(
        _robots("contact_exempt"), _limits(hard_contact_floor_m=0.2), exempt=_EXEMPT_PAIR
    )
    assert "robot_1" not in evaluation.latched


def test_floor_keeps_min_distance_reason_for_an_unexempt_pair():
    evaluation = evaluate_latches(
        _robots("contact_not_exempt"), _limits(hard_contact_floor_m=0.2), exempt=frozenset()
    )
    assert evaluation.reasons == {
        "robot_3": REASON_MIN_DISTANCE,
        "robot_4": REASON_MIN_DISTANCE,
    }
    assert evaluation.floor_breaches == {}


def test_floor_applies_to_robot_scope_exemption():
    evaluation = evaluate_latches(
        _robots("robot_scope_exempt"),
        _limits(hard_contact_floor_m=0.2),
        exempt=frozenset({"robot_3"}),
    )
    assert evaluation.latched == frozenset({"robot_3", "robot_4"})


def test_floor_uses_a_stale_robot_carried_pose():
    evaluation = evaluate_latches(
        _robots("stale_in_band_exempt"), _limits(hard_contact_floor_m=0.2), exempt=_EXEMPT_PAIR
    )
    assert evaluation.latched == frozenset({"robot_3", "robot_4"})
    assert evaluation.reasons["robot_3"] == REASON_HARD_CONTACT_FLOOR


def test_floor_latch_lifts_once_the_pair_separates():
    limits = _limits(hard_contact_floor_m=0.2)
    first = evaluate_latches(_robots("contact_exempt"), limits, exempt=_EXEMPT_PAIR)
    second = evaluate_latches(
        _robots("pull_off_pass_exempt"),
        limits,
        first.latched,
        first.last_fresh_distances,
        _EXEMPT_PAIR,
    )
    assert second.latched == frozenset()


# ---- validation and the log line ----


def test_floor_must_sit_below_min_distance():
    with pytest.raises(ValueError, match="below min_distance_m"):
        _limits(hard_contact_floor_m=0.45)


def test_floor_must_not_be_negative():
    with pytest.raises(ValueError, match=">= 0"):
        _limits(hard_contact_floor_m=-0.1)


def test_floor_detail_names_the_floor_and_pair_on_a_floor_latch():
    limits = _limits(hard_contact_floor_m=0.2)
    evaluation = evaluate_latches(_robots("contact_exempt"), limits, exempt=_EXEMPT_PAIR)
    detail = hard_contact_floor_detail(
        "robot_3", evaluation.reasons, evaluation.floor_breaches, limits
    )
    assert detail == " hard_contact_floor_m=0.2 pairs=robot_3+robot_4@0.084"


def test_floor_detail_empty_for_any_other_reason():
    limits = _limits(hard_contact_floor_m=0.2)
    evaluation = evaluate_latches(_robots("contact_not_exempt"), limits, exempt=frozenset())
    assert hard_contact_floor_detail(
        "robot_3", evaluation.reasons, evaluation.floor_breaches, limits
    ) == ""


# ---- node wiring (ROS2 bypassed via __new__, as in test_safety_monitor) ----


class _Logger:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def warning(self, msg: str) -> None:
        self.warnings.append(str(msg))

    def info(self, msg: str) -> None:
        pass


class _Msg:
    def __init__(self, **fields: Any) -> None:
        self.__dict__.update(fields)


def _release_node(floor_m: float) -> tuple[SafetyMonitorNode, list[str], _Logger]:
    node = SafetyMonitorNode.__new__(SafetyMonitorNode)
    node._limits = _limits(hard_contact_floor_m=floor_m)
    node._latched_stops = set()
    node._coordination = CoordinationTracker()
    node._exempt_pairs = frozenset()
    node._last_fresh_distances = {}
    node._cancel_nav2_goal = lambda _robot_id: None
    stops: list[str] = []
    node._emergency_stop = stops.append
    node._publish_holds = lambda: None
    logger = _Logger()
    node.get_logger = lambda: logger
    # The IB10 release: robot_3 holds for the lead robot_4 (pair exempt).
    parameters = {"backup_distance_m": 0.0, "hold_sec": 120.0, "passer_robot_id": "robot_4"}
    node._on_coord_command(
        _Msg(
            command_id="r1-junction-release",
            robot_id="robot_3",
            action="yield",
            parameters_json=json.dumps(parameters),
        )
    )
    node._on_coord_status(
        _Msg(
            command_id="r1-junction-release",
            robot_id="robot_3",
            status="ACTIVE",
            detail="holding for passing robot",
        )
    )
    return node, stops, logger


def _contact_scene() -> _Msg:
    return _Msg(data=json.dumps({"robots": _robots("contact_not_exempt")}))


def test_node_without_floor_lets_the_exempt_release_pair_touch():
    node, stops, logger = _release_node(0.0)
    node._on_scene_state(_contact_scene())
    assert stops == []
    assert logger.warnings == []


def test_node_with_floor_stops_the_exempt_release_pair_and_names_the_floor():
    node, stops, logger = _release_node(0.2)
    node._on_scene_state(_contact_scene())
    assert sorted(stops) == ["robot_3", "robot_4"]
    assert sorted(logger.warnings) == [
        "safety stop robot=robot_3 reason=hard_contact_floor "
        "hard_contact_floor_m=0.2 pairs=robot_3+robot_4@0.084",
        "safety stop robot=robot_4 reason=hard_contact_floor "
        "hard_contact_floor_m=0.2 pairs=robot_3+robot_4@0.084",
    ]
