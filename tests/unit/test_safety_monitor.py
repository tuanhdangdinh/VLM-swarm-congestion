"""Unit tests for the M4 safety monitor pure logic (no ROS2 runtime)."""
from __future__ import annotations

import json
import math

from swarm_execution.safety import (
    REASON_MIN_DISTANCE,
    REASON_STALE_POSE,
    SafetyLimits,
    detect_proximity_violations,
    evaluate_latches,
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
    node._last_fresh_distances = {}
    node._cancel_nav2_goal = lambda _robot_id: None
    stops: list[str] = []
    node._emergency_stop = lambda robot_id: stops.append(robot_id)
    # No-op by default; tests exercising /safety/holds publish override this.
    node._publish_holds = lambda: None

    class _Logger:
        def warning(self, _msg):
            pass

    node.get_logger = lambda: _Logger()
    return node, stops


class _FakeAdapter:
    """Records `cancel()` calls, standing in for `Nav2Adapter` in isolation.

    `_cancel_nav2_goal` now just delegates to `self._adapter.cancel(robot_id)`
    (see `nav2_adapter.py::cancel`), so these tests only need to observe that
    delegation, not a real action-client/service round trip — that is already
    covered by `test_nav2_adapter.py`.
    """

    def __init__(self) -> None:
        self.cancelled: list[str] = []

    def cancel(self, robot_id: str) -> None:
        self.cancelled.append(robot_id)


class _RecordingLogger:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def warning(self, msg) -> None:
        self.warnings.append(str(msg))

    def info(self, msg) -> None:
        self.infos.append(str(msg))


def test_latch_requests_cancel_all_through_adapter():
    # _make_node stubs _cancel_nav2_goal as a no-op so the pure-latching tests
    # above don't need an adapter; this test restores the real method to
    # exercise its delegation to Nav2Adapter.cancel.
    node, _stops = _make_node(min_distance_m=0.3)
    fake_adapter = _FakeAdapter()
    node._adapter = fake_adapter
    del node._cancel_nav2_goal
    node.get_logger = lambda: _RecordingLogger()
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
            {"robot_id": "robot_2", "x": 0.2, "y": 0.0},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(scene)))

    assert sorted(fake_adapter.cancelled) == ["robot_1", "robot_2"]

    # The hold timer re-issues the zero-Twist but must not re-request a
    # cancel-all on every 40 Hz tick for a robot already latched.
    node._hold_stops()
    assert sorted(fake_adapter.cancelled) == ["robot_1", "robot_2"]


def test_cancel_log_no_longer_claims_result():
    # The old log line ("nav2 goal cancelled robot=...") asserted a result the
    # node never observed, because cancel_goals_async() silently no-op'd. The
    # new line only claims the request was made; the adapter logs the actual
    # server response separately (see test_nav2_adapter.py).
    node, _stops = _make_node(min_distance_m=0.3)
    node._adapter = _FakeAdapter()
    del node._cancel_nav2_goal
    logger = _RecordingLogger()
    node.get_logger = lambda: logger

    node._cancel_nav2_goal("robot_1")

    assert any(
        "cancel-all requested" in msg and "robot=robot_1" in msg
        for msg in logger.infos
    )
    assert not any("cancelled" in msg for msg in logger.infos)


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

    # The whole pair is exempt while robot_1 coordinates: latching robot_2
    # would freeze the choreographed close pass (yielder parks 0.35m off
    # centerline < the 0.45m threshold), wedging both robots permanently.
    assert stops == []


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


def test_pair_with_coordinating_member_not_flagged():
    # A yielder parked 0.35m off-centerline during its hold is closer than
    # the 0.45m latch threshold to the passing robot; the pair is exempt
    # while the yielder is under an ACTIVE coordination command, otherwise
    # the pass itself would latch the passer and freeze both robots.
    robots = [
        {"robot_id": "robot_1", "x": -1.5, "y": 0.35},
        {"robot_id": "robot_2", "x": -1.5, "y": 0.0},
    ]
    assert detect_proximity_violations(robots, 0.45) == {"robot_1", "robot_2"}
    assert detect_proximity_violations(robots, 0.45, {"robot_1"}) == set()


def test_pair_without_coordinating_member_still_flagged():
    # The exemption is per-pair: an unrelated close pair with no coordinating
    # member latches normally even while some other robot is coordinating.
    robots = [
        {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
        {"robot_id": "robot_2", "x": 0.1, "y": 0.0},
        {"robot_id": "robot_3", "x": 5.0, "y": 5.0},
    ]
    assert detect_proximity_violations(robots, 0.45, {"robot_3"}) == {
        "robot_1",
        "robot_2",
    }


# ---------------------------------------------------------------------------
# STALE fail-safe (run D 2026-09-16: overlapping markers blinded the monitor)
# ---------------------------------------------------------------------------

_LIMITS = SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2)
_PAIR = ("robot_1", "robot_2")


def _stale(robot_id: str, x: float, y: float) -> dict:
    return {"robot_id": robot_id, "x": x, "y": y, "status": "STALE"}


def _fresh(robot_id: str, x: float, y: float) -> dict:
    return {"robot_id": robot_id, "x": x, "y": y, "status": "MOVING"}


def test_derived_stale_band_is_min_distance_plus_margin():
    assert _LIMITS.stale_unsafe_distance_m == 0.6
    explicit = SafetyLimits(0.3, 0.2, stale_unsafe_distance_m=0.9)
    assert explicit.stale_unsafe_distance_m == 0.9


def test_stale_robot_keeps_existing_latch():
    # No memory at all and both carried poses far apart: the only thing holding
    # these robots is the previous latch, which a STALE reading must not clear.
    robots = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 3.0, 0.0)]

    result = evaluate_latches(robots, _LIMITS, previous_latched={"robot_1", "robot_2"})

    assert result.latched == {"robot_1", "robot_2"}
    assert result.reasons["robot_1"] == REASON_STALE_POSE


def test_stale_robot_last_seen_close_is_latched():
    # Run D shape: the carried poses are stale and wrong (M1 froze them 3 m
    # apart) while the last real non-STALE reading had the pair at 0.078 m.
    # The latch must come from the memory, not from the carried pose.
    robots = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 3.0, 0.0)]

    result = evaluate_latches(
        robots, _LIMITS, last_fresh_distances={_PAIR: 0.078}
    )

    assert result.latched == {"robot_1", "robot_2"}
    assert result.reasons["robot_2"] == REASON_STALE_POSE


def test_stale_robot_last_seen_far_is_not_latched():
    # Far in both the memory and the carried pose: a robot that merely lost its
    # marker while alone in the aisle is not a safety event.
    robots = [_stale("robot_1", 0.0, 0.0), _fresh("robot_2", 3.0, 0.0)]

    result = evaluate_latches(robots, _LIMITS, last_fresh_distances={_PAIR: 3.0})

    assert result.latched == frozenset()


def test_stale_latch_released_on_fresh_reading_when_separated():
    stale_scene = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 0.05, 0.0)]
    latched = evaluate_latches(
        stale_scene, _LIMITS, last_fresh_distances={_PAIR: 0.078}
    )
    assert latched.latched == {"robot_1", "robot_2"}

    # 0.5 m apart and both detected again: at/above min_distance_m, so the
    # latch lifts even though 0.5 m is still inside the 0.6 m STALE band —
    # the wider band gates unknown poses only, never fresh ones.
    fresh_scene = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.5, 0.0)]
    released = evaluate_latches(
        fresh_scene,
        _LIMITS,
        previous_latched=latched.latched,
        last_fresh_distances=latched.last_fresh_distances,
    )

    assert released.latched == frozenset()
    assert released.last_fresh_distances[_PAIR] == 0.5


def test_stale_latch_persists_on_fresh_reading_when_still_close():
    stale_scene = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 0.05, 0.0)]
    latched = evaluate_latches(
        stale_scene, _LIMITS, last_fresh_distances={_PAIR: 0.078}
    )

    fresh_scene = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.2, 0.0)]
    still = evaluate_latches(
        fresh_scene,
        _LIMITS,
        previous_latched=latched.latched,
        last_fresh_distances=latched.last_fresh_distances,
    )

    assert still.latched == {"robot_1", "robot_2"}
    assert still.reasons["robot_1"] == REASON_MIN_DISTANCE


def test_stale_failsafe_disabled_by_parameter():
    # The parameter gates both halves of the rule: the distance memory and the
    # keep-the-existing-latch behaviour.
    limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, stale_pose_is_unsafe=False
    )
    robots = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 3.0, 0.0)]

    result = evaluate_latches(
        robots,
        limits,
        previous_latched={"robot_1", "robot_2"},
        last_fresh_distances={_PAIR: 0.078},
    )

    assert result.latched == frozenset()


def test_stale_failsafe_does_not_block_commanded_backup():
    # Mirrors test_coordinating_robot_suppressed_from_safety_stop: robot_1 is
    # reversing under an ACTIVE coordination command (the designed way out of a
    # close standoff) with its marker occluded, so M1 reports it STALE. The
    # whole pair keeps the existing lift — latching either one would stall the
    # backup or freeze the partner mid-choreography.
    robots = [_stale("robot_1", 0.0, 0.0), _fresh("robot_2", 0.05, 0.0)]

    result = evaluate_latches(
        robots,
        _LIMITS,
        previous_latched={"robot_1", "robot_2"},
        last_fresh_distances={_PAIR: 0.078},
        coordinating={"robot_1"},
    )

    assert result.latched == frozenset()


def test_memory_ignores_pairs_measured_against_a_stale_pose():
    # A distance measured against a carried (frozen) pose must not enter the
    # memory the fail-safe trusts — that would launder the stale datum.
    robots = [_stale("robot_1", 0.0, 0.0), _fresh("robot_2", 3.0, 0.0)]

    result = evaluate_latches(robots, _LIMITS, last_fresh_distances={_PAIR: 0.078})

    assert result.last_fresh_distances[_PAIR] == 0.078
    assert result.latched == {"robot_1", "robot_2"}


def test_callback_latches_stale_pair_from_remembered_distance():
    # Node wiring: `status` must reach the pure function, and the memory must
    # survive between scene messages.
    node, stops = _make_node(min_distance_m=0.45)
    closing = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "MOVING"},
            {"robot_id": "robot_2", "x": 0.5, "y": 0.0, "status": "MOVING"},
        ]
    }
    # Markers overlap, both go STALE, and M1 freezes the last known poses.
    blind = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "STALE"},
            {"robot_id": "robot_2", "x": 0.5, "y": 0.0, "status": "STALE"},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(closing)))
    assert stops == []

    node._on_scene_state(_StringMsg(json.dumps(blind)))

    assert sorted(stops) == ["robot_1", "robot_2"]


def test_stale_latch_reason_logged_once_per_latch():
    node, _stops = _make_node(min_distance_m=0.45)
    logged: list[str] = []

    class _Capture:
        def warning(self, msg):
            logged.append(msg)

    node.get_logger = lambda: _Capture()
    closing = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "MOVING"},
            {"robot_id": "robot_2", "x": 0.5, "y": 0.0, "status": "MOVING"},
        ]
    }
    blind = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "STALE"},
            {"robot_id": "robot_2", "x": 0.5, "y": 0.0, "status": "STALE"},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(closing)))
    node._on_scene_state(_StringMsg(json.dumps(blind)))
    node._on_scene_state(_StringMsg(json.dumps(blind)))

    # One line per newly-latched robot and nothing on the repeat message: the
    # reason is a latch-transition diagnostic, not a per-message one.
    stale_lines = [m for m in logged if "reason=stale_pose_unsafe" in m]
    assert sorted(stale_lines) == [
        "safety stop robot=robot_1 reason=stale_pose_unsafe",
        "safety stop robot=robot_2 reason=stale_pose_unsafe",
    ]
