"""Unit tests for the M4 safety monitor pure logic (no ROS2 runtime)."""
from __future__ import annotations

import json
import math

from swarm_execution.safety import (
    SafetyLimits,
    detect_proximity_violations,
    exceeds_speed_limit,
)
from swarm_execution.safety_monitor_node import SafetyMonitorNode, holds_payload


def _robot(robot_id: str, x: float, y: float, v: float = 0.0) -> dict:
    return {"robot_id": robot_id, "x": x, "y": y, "linear_velocity": v}


def test_no_violation_when_robots_far_apart():
    limits = SafetyLimits(min_distance_m=0.3, max_linear_velocity_mps=0.2)
    robots = [_robot("robot_1", 0.0, 0.0), _robot("robot_2", 1.0, 0.0)]

    assert detect_proximity_violations(robots, limits.min_distance_m) == set()


def test_both_robots_flagged_when_closer_than_min_distance():
    limits = SafetyLimits(min_distance_m=0.3, max_linear_velocity_mps=0.2)
    robots = [_robot("robot_1", 0.0, 0.0), _robot("robot_2", 0.2, 0.0)]

    assert detect_proximity_violations(robots, limits.min_distance_m) == {
        "robot_1",
        "robot_2",
    }


def test_distance_exactly_at_threshold_is_not_a_violation():
    robots = [_robot("robot_1", 0.0, 0.0), _robot("robot_2", 0.3, 0.0)]

    assert detect_proximity_violations(robots, 0.3) == set()


def test_only_the_violating_pair_is_flagged_among_three_robots():
    robots = [
        _robot("robot_1", 0.0, 0.0),
        _robot("robot_2", 0.1, 0.0),
        _robot("robot_3", 5.0, 0.0),
    ]

    assert detect_proximity_violations(robots, 0.3) == {"robot_1", "robot_2"}


def test_single_robot_never_violates():
    assert detect_proximity_violations([_robot("robot_1", 0.0, 0.0)], 0.3) == set()


def test_speed_within_limit_is_allowed():
    assert exceeds_speed_limit(0.18, 0.2) is False


def test_speed_above_limit_is_flagged():
    assert exceeds_speed_limit(0.25, 0.2) is True


def test_diagonal_distance_uses_euclidean_norm():
    # 3-4-5 triangle: distance 0.5 from a 0.3/0.4 offset.
    robots = [_robot("robot_1", 0.0, 0.0), _robot("robot_2", 0.3, 0.4)]
    assert math.isclose(0.5, math.hypot(0.3, 0.4))
    assert detect_proximity_violations(robots, 0.4) == set()
    assert detect_proximity_violations(robots, 0.6) == {"robot_1", "robot_2"}


def test_holds_payload_sorts_robot_ids():
    assert holds_payload({"robot_2", "robot_1"}) == json.dumps(
        {"held": ["robot_1", "robot_2"]}
    )


def test_holds_payload_empty_set_is_empty_list():
    assert holds_payload(set()) == json.dumps({"held": []})


# ---------------------------------------------------------------------------
# Node callback (ROS2 bypassed via __new__)
# ---------------------------------------------------------------------------


class _StringMsg:
    def __init__(self, data: str) -> None:
        self.data = data


def _make_node(min_distance_m: float = 0.3) -> tuple[SafetyMonitorNode, list[str]]:
    node = SafetyMonitorNode.__new__(SafetyMonitorNode)
    node._limits = SafetyLimits(
        min_distance_m=min_distance_m, max_linear_velocity_mps=0.2
    )
    node._latched_stops = set()
    node._coordinating = set()
    stops: list[str] = []
    node._emergency_stop = lambda robot_id: stops.append(robot_id)
    # No-op by default; tests exercising /safety/holds publish override this.
    node._publish_holds = lambda: None

    class _Logger:
        def warning(self, _msg):
            pass

    node.get_logger = lambda: _Logger()
    return node, stops


def test_callback_stops_both_robots_on_proximity_violation():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(scene)))

    assert sorted(stops) == ["robot_1", "robot_2"]


def test_callback_issues_no_stop_when_robots_clear():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 1.0, "y": 0.0},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(scene)))

    assert stops == []


def test_callback_tolerates_malformed_scene_json():
    node, stops = _make_node()

    node._on_scene_state(_StringMsg("not json{"))

    assert stops == []


def test_callback_skips_malformed_robot_entry_without_crashing():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "y": 0.0},  # missing x
            {"robot_id": "robot_2", "x": 0.05, "y": 0.0},
            {"robot_id": "robot_3", "x": 0.05, "y": 0.0},
        ]
    }

    # robot_1 is dropped; robot_2/robot_3 overlap and are flagged.
    node._on_scene_state(_StringMsg(json.dumps(scene)))

    assert sorted(stops) == ["robot_2", "robot_3"]


def test_callback_stops_robot_exceeding_speed_limit():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "linear_velocity": 0.5},
            {"robot_id": "robot_2", "x": 5.0, "y": 0.0, "linear_velocity": 0.1},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(scene)))

    # robot_1 over the 0.2 m/s limit; robot_2 within it and far away.
    assert stops == ["robot_1"]


def test_violation_latches_for_hold_republish():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }
    node._on_scene_state(_StringMsg(json.dumps(scene)))
    stops.clear()

    # The hold timer re-issues stops for latched robots between scene updates.
    node._hold_stops()

    assert sorted(stops) == ["robot_1", "robot_2"]


def test_latch_clears_when_violation_resolves():
    node, stops = _make_node(min_distance_m=0.3)
    close = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }
    clear = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 2.0, "y": 0.0},
        ]
    }
    node._on_scene_state(_StringMsg(json.dumps(close)))
    node._on_scene_state(_StringMsg(json.dumps(clear)))
    stops.clear()

    node._hold_stops()

    assert stops == []


def test_coordinating_robot_suppressed_from_safety_stop():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }
    # robot_1 is executing a coordination command (backing away).
    node._coordinating = {"robot_1"}
    node._on_scene_state(_StringMsg(json.dumps(scene)))

    # Only robot_2 should be stopped; robot_1 is suppressed.
    assert stops == ["robot_2"]


def test_coordination_suppression_cleared_on_completion():
    node, stops = _make_node(min_distance_m=0.3)
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }
    node._coordinating = {"robot_1"}

    class _StatusMsg:
        def __init__(self, robot_id: str, status: str) -> None:
            self.robot_id = robot_id
            self.status = status

    node._on_coord_status(_StatusMsg("robot_1", "COMPLETED"))
    node._on_scene_state(_StringMsg(json.dumps(scene)))

    # After completion, robot_1 is no longer suppressed.
    assert "robot_1" in stops


def test_holds_published_on_latch_change():
    node, _stops = _make_node(min_distance_m=0.3)
    published: list[list[str]] = []
    node._publish_holds = lambda: published.append(sorted(node._latched_stops))
    close = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }
    clear = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 2.0, "y": 0.0},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(close)))
    # Latch set changed from {} to {robot_1, robot_2}: publish once.
    assert published == [["robot_1", "robot_2"]]

    published.clear()
    node._on_scene_state(_StringMsg(json.dumps(close)))
    # Same latch set as before: the scene callback does not re-publish (the 1s
    # timer owns periodic refresh, not the per-scene-update path).
    assert published == []

    node._on_scene_state(_StringMsg(json.dumps(clear)))
    # Latch emptied: publish once with an empty list.
    assert published == [[]]


def test_holds_refresh_republishes_while_latched():
    node, _stops = _make_node(min_distance_m=0.3)
    published: list[list[str]] = []
    node._publish_holds = lambda: published.append(sorted(node._latched_stops))
    node._latched_stops = {"robot_1"}

    node._refresh_holds()
    # Late-joiner tolerance: periodic refresh republishes while any robot held.
    assert published == [["robot_1"]]


def test_holds_refresh_publishes_empty_set_for_restart_recovery():
    # A freshly restarted monitor starts with an empty latch set and would
    # otherwise publish nothing until the next latch change — stranding a
    # coordination_client still holding robots from before the restart. The
    # heartbeat is therefore unconditional: empty sets publish every tick too.
    node, _stops = _make_node(min_distance_m=0.3)
    published: list[list[str]] = []
    node._publish_holds = lambda: published.append(sorted(node._latched_stops))
    node._latched_stops = set()

    node._refresh_holds()

    assert published == [[]]
