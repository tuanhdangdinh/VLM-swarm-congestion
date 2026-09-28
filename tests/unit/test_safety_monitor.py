"""Unit tests for the M4 safety monitor pure logic (no ROS2 runtime)."""
from __future__ import annotations

import json
import math

import pytest
from swarm_execution.safety import (
    REASON_MIN_DISTANCE,
    REASON_STALE_POSE,
    CoordinationTracker,
    SafetyLimits,
    clearing_exempt_robots,
    crossing_order_from_parameters,
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
    node._coordination = CoordinationTracker()
    node._exempt_pairs = frozenset()
    node._last_fresh_distances = {}
    node._cancel_nav2_goal = lambda _robot_id: None
    stops: list[str] = []
    node._emergency_stop = lambda robot_id: stops.append(robot_id)
    # No-op by default; tests exercising /safety/holds publish override this.
    node._publish_holds = lambda: None

    class _Logger:
        def warning(self, _msg):
            pass

        def info(self, _msg):
            pass

    node.get_logger = lambda: _Logger()
    return node, stops


class _CommandMsg:
    def __init__(
        self, command_id: str, robot_id: str, action: str, parameters_json: str = ""
    ) -> None:
        self.command_id = command_id
        self.robot_id = robot_id
        self.action = action
        self.parameters_json = parameters_json


class _StatusMsg:
    def __init__(self, command_id: str, robot_id: str, status: str) -> None:
        self.command_id = command_id
        self.robot_id = robot_id
        self.status = status


def _dispatch(
    node: SafetyMonitorNode,
    command_id: str,
    robot_id: str,
    action: str,
    parameters: dict | None = None,
) -> None:
    """Feed one command and its ACTIVE status, as the command bus would."""
    parameters_json = "" if parameters is None else json.dumps(parameters)
    node._on_coord_command(_CommandMsg(command_id, robot_id, action, parameters_json))
    node._on_coord_status(_StatusMsg(command_id, robot_id, "ACTIVE"))


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
    # robot_1 is executing a clearing maneuver (backing away) and robot_2 is
    # its partner, parked by the linked wait under the same command id (the
    # production yield shape; a lone yield is pinned separately below).
    _dispatch(node, "req-yield", "robot_1", "yield")
    _dispatch(node, "req-yield", "robot_2", "temporary_wait")
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
    _dispatch(node, "req-yield", "robot_1", "yield")

    node._on_coord_status(_StatusMsg("req-yield", "robot_1", "COMPLETED"))
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
        exempt={"robot_1"},
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


# ---------------------------------------------------------------------------
# Clearing-maneuver exemption (runs G4/K1 2026-09-25/26: a reroute leg plus its
# partner's temporary_wait disarmed the monitor; one robot drove into the other)
# ---------------------------------------------------------------------------


def _tracker_with(*commands: tuple[str, str, str]) -> CoordinationTracker:
    tracker = CoordinationTracker()
    for command_id, robot_id, action in commands:
        tracker.record_command(command_id, robot_id, action)
        tracker.record_status(command_id, robot_id, "ACTIVE")
    return tracker


def _close_pair() -> list[dict]:
    return [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.30, 0.0)]


def test_exempt_robots_include_robot_when_active_yield():
    tracker = _tracker_with(("req-yield", "robot_1", "yield"))

    assert tracker.exempt_robots() == {"robot_1"}


def test_exempt_robots_include_robot_when_active_reverse():
    tracker = _tracker_with(("req-reverse", "robot_1", "reverse"))

    assert tracker.exempt_robots() == {"robot_1"}


def test_exempt_robots_exclude_robot_when_active_reroute():
    tracker = _tracker_with(("req-reroute", "robot_1", "reroute"))

    assert tracker.exempt_robots() == frozenset()


def test_exempt_robots_exclude_robot_when_active_temporary_wait():
    tracker = _tracker_with(("req-reroute", "robot_2", "temporary_wait"))

    assert tracker.exempt_robots() == frozenset()


@pytest.mark.parametrize(
    "action", ["navigate", "goal", "priority_override", "convoy", "wait", "stop"]
)
def test_exempt_robots_exclude_robot_when_active_non_clearing_action(action: str):
    tracker = _tracker_with((f"req-{action}", "robot_1", action))

    assert tracker.exempt_robots() == frozenset()


def test_exempt_robots_exclude_waits_when_reverse_refused():
    # A refused reverse is grounded as temporary_waits under the same
    # `<request>-reverse` id. The id names the strategy, not the action, so an
    # id-suffix rule would wrongly exempt two robots that are only waiting.
    tracker = _tracker_with(
        ("req-reverse", "robot_1", "temporary_wait"),
        ("req-reverse", "robot_2", "temporary_wait"),
    )

    assert tracker.exempt_robots() == frozenset()


def test_exempt_robots_exclude_active_robot_when_command_unseen():
    tracker = CoordinationTracker()
    tracker.record_status("req-yield", "robot_1", "ACTIVE")

    assert tracker.exempt_robots() == frozenset()


def test_exempt_robots_resolve_when_status_arrives_before_command():
    tracker = CoordinationTracker()
    tracker.record_status("req-yield", "robot_1", "ACTIVE")

    tracker.record_command("req-yield", "robot_1", "yield")

    assert tracker.exempt_robots() == {"robot_1"}


def test_exempt_robots_clear_when_command_completes():
    tracker = _tracker_with(("req-yield", "robot_1", "yield"))

    tracker.record_status("req-yield", "robot_1", "COMPLETED")

    assert tracker.exempt_robots() == frozenset()


def test_exempt_robots_keep_robot_when_other_command_terminates():
    # A busy-rejected command's FAILED, or a base_mission status from
    # coordination_client, is not the yield's own terminal status.
    tracker = _tracker_with(("req-yield", "robot_1", "yield"))

    tracker.record_status("req2-reroute", "robot_1", "FAILED")
    tracker.record_status("base_mission", "robot_1", "COMPLETED")

    assert tracker.exempt_robots() == {"robot_1"}


def test_tracker_bounds_commands_without_terminal_status():
    tracker = CoordinationTracker()
    for i in range(CoordinationTracker.MAX_TRACKED_COMMANDS + 10):
        tracker.record_command(f"req{i}-yield", "robot_1", "yield")

    tracker.record_status(
        f"req{CoordinationTracker.MAX_TRACKED_COMMANDS + 9}-yield", "robot_1", "ACTIVE"
    )

    assert len(tracker._action_by_key) == CoordinationTracker.MAX_TRACKED_COMMANDS
    assert tracker.exempt_robots() == {"robot_1"}


def test_clearing_exempt_robots_is_pure_join_of_status_and_action():
    exempt = clearing_exempt_robots(
        {"robot_1": "req-yield", "robot_2": "req-yield"},
        {("req-yield", "robot_1"): "yield", ("req-yield", "robot_2"): "temporary_wait"},
    )

    assert exempt == {"robot_1"}


def test_pair_exempt_when_one_member_yields_and_other_waits():
    # The yield flow: the passer's linked temporary_wait does not exempt it,
    # but the pair stays exempt through the yielder's own ACTIVE yield.
    tracker = _tracker_with(
        ("req-yield", "robot_1", "yield"),
        ("req-yield", "robot_2", "temporary_wait"),
    )

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exempt_robots())

    assert flagged == set()


def test_pair_exempt_when_one_member_yields_and_other_reroutes():
    # Mixed pair rule: exempt while a clearing maneuver is among the pair's
    # ACTIVE commands, whatever the other member runs.
    tracker = _tracker_with(
        ("req-yield", "robot_1", "yield"),
        ("req2-reroute", "robot_2", "reroute"),
    )

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exempt_robots())

    assert flagged == set()


def test_pair_flagged_when_members_reroute_and_wait():
    # The G4/K1 shape: robot_1 on a reroute Nav2 leg, robot_2 parked by the
    # linked temporary_wait. Neither is clearing, so the 0.45 m rule applies.
    tracker = _tracker_with(
        ("req-reroute", "robot_1", "reroute"),
        ("req-reroute", "robot_2", "temporary_wait"),
    )

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exempt_robots())

    assert flagged == {"robot_1", "robot_2"}


def test_stale_failsafe_armed_when_active_commands_are_non_clearing():
    # K1 contact: both markers overlap, both robots STALE, last fresh distance
    # 0.119 m. The fail-safe must latch despite the reroute/wait being ACTIVE.
    tracker = _tracker_with(
        ("req-reroute", "robot_1", "reroute"),
        ("req-reroute", "robot_2", "temporary_wait"),
    )
    robots = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 0.119, 0.0)]

    result = evaluate_latches(
        robots,
        _LIMITS,
        last_fresh_distances={_PAIR: 0.119},
        exempt=tracker.exempt_robots(),
    )

    assert result.latched == {"robot_1", "robot_2"}


def test_stale_latch_kept_when_active_commands_are_non_clearing():
    tracker = _tracker_with(
        ("req-reroute", "robot_1", "reroute"),
        ("req-reroute", "robot_2", "temporary_wait"),
    )
    robots = [_stale("robot_1", 0.0, 0.0), _stale("robot_2", 3.0, 0.0)]

    result = evaluate_latches(
        robots,
        _LIMITS,
        previous_latched={"robot_1", "robot_2"},
        exempt=tracker.exempt_robots(),
    )

    assert result.latched == {"robot_1", "robot_2"}


def _scene(distance_m: float, status: str = "MOVING") -> _StringMsg:
    return _StringMsg(
        json.dumps(
            {
                "robots": [
                    {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": status},
                    {"robot_id": "robot_2", "x": distance_m, "y": 0.0, "status": status},
                ]
            }
        )
    )


def test_latch_persists_when_reroute_goes_active_after_latch():
    # K1: the pair latched at the 0.45 m crossing, then 0.8 s later the reroute
    # and its partner's temporary_wait went ACTIVE. The old exemption lifted
    # the latch; now it must hold and /safety/holds must not announce a release.
    node, _stops = _make_node(min_distance_m=0.45)
    published: list[list[str]] = []
    node._publish_holds = lambda: published.append(sorted(node._latched_stops))
    node._on_scene_state(_scene(0.41))
    assert node._latched_stops == {"robot_1", "robot_2"}

    _dispatch(node, "req-reroute", "robot_1", "reroute")
    _dispatch(node, "req-reroute", "robot_2", "temporary_wait")
    node._on_scene_state(_scene(0.30))

    assert node._latched_stops == {"robot_1", "robot_2"}
    assert published == [["robot_1", "robot_2"]]


def test_latch_fires_when_pair_closes_during_reroute():
    # G4: the reroute went ACTIVE before the first sub-0.45 m frame arrived.
    node, stops = _make_node(min_distance_m=0.45)
    _dispatch(node, "req-reroute", "robot_1", "reroute")
    _dispatch(node, "req-reroute", "robot_2", "temporary_wait")

    node._on_scene_state(_scene(0.41))

    assert sorted(stops) == ["robot_1", "robot_2"]


def test_latch_held_when_pair_goes_stale_during_reroute():
    node, stops = _make_node(min_distance_m=0.45)
    _dispatch(node, "req-reroute", "robot_1", "reroute")
    _dispatch(node, "req-reroute", "robot_2", "temporary_wait")
    node._on_scene_state(_scene(0.41))

    stops.clear()
    node._on_scene_state(_scene(0.41, status="STALE"))

    assert sorted(stops) == ["robot_1", "robot_2"]


def test_latch_released_when_reverse_goes_active():
    # Non-regression: a clearing maneuver still lifts an existing latch so the
    # commanded backup can run.
    node, _stops = _make_node(min_distance_m=0.45)
    node._on_scene_state(_scene(0.27))
    assert node._latched_stops == {"robot_1", "robot_2"}

    _dispatch(node, "req-reverse", "robot_1", "reverse")
    _dispatch(node, "req-reverse", "robot_2", "reverse")
    node._on_scene_state(_scene(0.27))

    assert node._latched_stops == set()


def test_latch_released_when_yield_goes_active_with_waiting_partner():
    node, _stops = _make_node(min_distance_m=0.45)
    node._on_scene_state(_scene(0.27))

    _dispatch(node, "req-yield", "robot_1", "yield")
    _dispatch(node, "req-yield", "robot_2", "temporary_wait")
    node._on_scene_state(_scene(0.27))

    assert node._latched_stops == set()


def test_coordination_status_change_logged_with_action_and_exemption():
    node, _stops = _make_node(min_distance_m=0.45)
    logger = _RecordingLogger()
    node.get_logger = lambda: logger

    _dispatch(node, "req-reroute", "robot_1", "reroute")
    node._on_coord_status(_StatusMsg("req-reroute", "robot_1", "ACTIVE"))

    assert logger.infos == [
        "coordination status robot=robot_1 command=req-reroute "
        "status=ACTIVE action=reroute exempt=False"
    ]


# ---------------------------------------------------------------------------
# Pair-scoped clearing exemption (T2b safety prerequisite, 2026-09-28): a
# clearing robot is exempt only against the robots of its own clearing command,
# never against a bystander it could back into.
# ---------------------------------------------------------------------------


def _yield_command(
    tracker: CoordinationTracker,
    yielder: str,
    passers: list[str],
    command_id: str = "req-yield",
    parameters: dict | None = None,
) -> None:
    if parameters is None:
        parameters = {"passer_robot_id": passers[0]} if passers else {}
    tracker.record_command(command_id, yielder, "yield", parameters)
    tracker.record_status(command_id, yielder, "ACTIVE")
    for position, passer in enumerate(passers):
        tracker.record_command(
            command_id, passer, "temporary_wait", {"linked_position": position}
        )
        tracker.record_status(command_id, passer, "ACTIVE")


def _two_passer_order() -> dict:
    return {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_3"]}


def test_exemption_covers_yielder_and_passer_pair():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])

    exemption = tracker.exemption()

    assert exemption.clearing_robots == {"robot_1"}
    assert exemption.pairs == {("robot_1", "robot_2")}


def test_pair_scope_leaves_yielder_passer_pair_unflagged():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exemption())

    assert flagged == set()


def test_pair_scope_flags_yielder_and_bystander():
    # The report's wrong-order hazard: the yielder backs toward a third robot
    # that is not part of its clearing command.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])
    robots = [
        _fresh("robot_1", 0.0, 0.0),
        _fresh("robot_2", 0.30, 0.0),
        _fresh("robot_3", -0.30, 0.0),
    ]

    flagged = detect_proximity_violations(robots, 0.45, tracker.exemption())

    assert flagged == {"robot_1", "robot_3"}


def test_pair_scope_flags_passer_and_bystander():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])
    robots = [
        _fresh("robot_1", -3.0, 0.0),
        _fresh("robot_2", 0.0, 0.0),
        _fresh("robot_3", 0.30, 0.0),
    ]

    flagged = detect_proximity_violations(robots, 0.45, tracker.exemption())

    assert flagged == {"robot_2", "robot_3"}


def test_lone_yield_does_not_exempt_uncommanded_neighbor():
    # Intentional change from the robot-scoped rule: a yield command that
    # names no partner has no pair to clear, so the neighbour is a bystander.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", [])

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exemption())

    assert flagged == {"robot_1", "robot_2"}


def test_pair_scope_flags_yielder_and_robot_on_other_command():
    # The pair-scoped counterpart of test_pair_exempt_when_one_member_yields_
    # and_other_reroutes: robot_2 was never part of the yield command.
    tracker = _tracker_with(
        ("req-yield", "robot_1", "yield"),
        ("req2-reroute", "robot_2", "reroute"),
    )

    flagged = detect_proximity_violations(_close_pair(), 0.45, tracker.exemption())

    assert flagged == {"robot_1", "robot_2"}


def test_passer_stays_partner_after_its_wait_is_released():
    # No-escort yield: the command bus completes the passer's wait at hold
    # start ("released: yield holding") while the yielder is still ACTIVE.
    # The pass itself must stay exempt.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])

    tracker.record_status("req-yield", "robot_2", "COMPLETED")

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_passer_stays_partner_after_it_takes_a_new_command():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])
    tracker.record_status("req-yield", "robot_2", "COMPLETED")

    tracker.record_command("req2-reroute", "robot_2", "reroute")
    tracker.record_status("req2-reroute", "robot_2", "ACTIVE")

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_reverse_fan_out_exempts_every_pair_of_its_robots():
    tracker = _tracker_with(
        ("req-reverse", "robot_1", "reverse"),
        ("req-reverse", "robot_2", "reverse"),
        ("req-reverse", "robot_3", "reverse"),
    )

    assert tracker.exemption().pairs == {
        ("robot_1", "robot_2"),
        ("robot_1", "robot_3"),
        ("robot_2", "robot_3"),
    }


def test_reverse_does_not_exempt_robot_outside_its_command():
    tracker = _tracker_with(
        ("req-reverse", "robot_1", "reverse"),
        ("req-reverse", "robot_2", "reverse"),
    )

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_waiting_passers_are_not_paired_with_each_other():
    # Only the clearing robot's pairs are exempt: two waits of the same yield
    # command keep the 0.45 m rule between them.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2", "robot_3"], parameters=_two_passer_order())
    tracker.record_status("req-yield", "robot_2", "COMPLETED")

    assert ("robot_2", "robot_3") not in tracker.exemption().pairs


def test_later_passer_not_partner_before_earlier_passer_released():
    # During the backup and pull-off only crossing_order[0] is the yielder's
    # partner; robot_3, queued further back, keeps full protection.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2", "robot_3"], parameters=_two_passer_order())

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_later_passer_admitted_once_earlier_passer_released():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2", "robot_3"], parameters=_two_passer_order())

    tracker.record_status("req-yield", "robot_2", "COMPLETED")

    assert tracker.exemption().pairs == {("robot_1", "robot_2"), ("robot_1", "robot_3")}


def test_busy_rejected_earlier_passer_does_not_admit_later_passer():
    # A busy-reject FAILED is not a release: robot_2 never waited, and the
    # yielder may still be backing toward robot_3.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2", "robot_3"], parameters=_two_passer_order())

    tracker.record_status("req-yield", "robot_2", "FAILED")

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_exemption_ends_when_yield_completes():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2", "robot_3"], parameters=_two_passer_order())
    tracker.record_status("req-yield", "robot_2", "COMPLETED")

    tracker.record_status("req-yield", "robot_1", "COMPLETED")

    assert tracker.exemption().pairs == frozenset()


def test_yield_without_order_parameters_pairs_every_command_member():
    # A yield whose parameters were never seen (or carry no passer) falls back
    # to the command's robot set, which is the two-robot yield shape.
    tracker = _tracker_with(
        ("req-yield", "robot_1", "yield"),
        ("req-yield", "robot_2", "temporary_wait"),
    )

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_yield_passer_named_by_parameters_is_partner_before_its_wait_arrives():
    tracker = CoordinationTracker()
    tracker.record_command("req-yield", "robot_1", "yield", {"passer_robot_id": "robot_2"})
    tracker.record_status("req-yield", "robot_1", "ACTIVE")

    assert tracker.exemption().pairs == {("robot_1", "robot_2")}


def test_tracker_bounds_command_memberships():
    tracker = CoordinationTracker()
    for i in range(CoordinationTracker.MAX_TRACKED_COMMANDS + 10):
        tracker.record_command(f"req{i}-yield", "robot_1", "yield")

    assert len(tracker._members_by_command) == CoordinationTracker.MAX_TRACKED_COMMANDS


@pytest.mark.parametrize(
    ("action", "parameters", "expected"),
    [
        ("yield", {"crossing_order": ["robot_2", "robot_3"]}, ("robot_2", "robot_3")),
        ("yield", {"passer_robot_id": "robot_2"}, ("robot_2",)),
        (
            "yield",
            {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_3"]},
            ("robot_2", "robot_3"),
        ),
        ("yield", {}, None),
        ("yield", None, None),
        ("yield", {"crossing_order": "robot_2"}, None),
        ("yield", {"crossing_order": []}, None),
        ("reverse", {"crossing_order": ["robot_2"]}, None),
        ("temporary_wait", {"passer_robot_id": "robot_2"}, None),
    ],
)
def test_crossing_order_from_parameters(action, parameters, expected):
    assert crossing_order_from_parameters(action, parameters) == expected


def test_stale_yielder_relatched_against_bystander_from_memory():
    # The keep-latch half of the STALE rule stays robot-level for a clearing
    # robot, but the remembered-distance half is pair-scoped: the bystander
    # pair re-latches from its last fresh distance.
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])
    robots = [
        _stale("robot_1", 0.0, 0.0),
        _fresh("robot_2", 2.0, 0.0),
        # Carried pose is not close; only the remembered distance is.
        _fresh("robot_3", -0.8, 0.0),
    ]

    result = evaluate_latches(
        robots,
        _LIMITS,
        previous_latched={"robot_1", "robot_3"},
        last_fresh_distances={("robot_1", "robot_3"): 0.44},
        exempt=tracker.exemption(),
    )

    assert result.latched == {"robot_1", "robot_3"}


def test_stale_yielder_with_only_partner_nearby_keeps_the_lift():
    tracker = CoordinationTracker()
    _yield_command(tracker, "robot_1", ["robot_2"])
    robots = [
        _stale("robot_1", 0.0, 0.0),
        _fresh("robot_2", 0.05, 0.0),
        _fresh("robot_3", 4.0, 0.0),
    ]

    result = evaluate_latches(
        robots,
        _LIMITS,
        previous_latched={"robot_1", "robot_2"},
        last_fresh_distances={_PAIR: 0.078, ("robot_1", "robot_3"): 4.0},
        exempt=tracker.exemption(),
    )

    assert result.latched == frozenset()


_THREE_ROBOT_SCENE = {
    "robots": [
        {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": "MOVING"},
        {"robot_id": "robot_2", "x": 0.30, "y": 0.0, "status": "MOVING"},
        {"robot_id": "robot_3", "x": -0.30, "y": 0.0, "status": "MOVING"},
    ]
}


def test_node_latches_clearing_yielder_against_bystander():
    node, stops = _make_node(min_distance_m=0.45)
    _dispatch(node, "req-yield", "robot_1", "yield", {"passer_robot_id": "robot_2"})
    _dispatch(node, "req-yield", "robot_2", "temporary_wait")

    node._on_scene_state(_StringMsg(json.dumps(_THREE_ROBOT_SCENE)))

    assert node._latched_stops == {"robot_1", "robot_3"}
    assert sorted(stops) == ["robot_1", "robot_3"]


def test_node_latches_later_passer_against_backing_yielder():
    node, _stops = _make_node(min_distance_m=0.45)
    order = {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_3"]}
    _dispatch(node, "req-yield", "robot_1", "yield", order)
    _dispatch(node, "req-yield", "robot_2", "temporary_wait", {"linked_position": 0})
    _dispatch(node, "req-yield", "robot_3", "temporary_wait", {"linked_position": 1})

    node._on_scene_state(_StringMsg(json.dumps(_THREE_ROBOT_SCENE)))

    assert node._latched_stops == {"robot_1", "robot_3"}


def test_node_admits_later_passer_after_earlier_passer_released():
    node, _stops = _make_node(min_distance_m=0.45)
    order = {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_3"]}
    _dispatch(node, "req-yield", "robot_1", "yield", order)
    _dispatch(node, "req-yield", "robot_2", "temporary_wait", {"linked_position": 0})
    _dispatch(node, "req-yield", "robot_3", "temporary_wait", {"linked_position": 1})
    node._on_coord_status(_StatusMsg("req-yield", "robot_2", "COMPLETED"))

    node._on_scene_state(_StringMsg(json.dumps(_THREE_ROBOT_SCENE)))

    assert node._latched_stops == set()


def test_node_tolerates_malformed_command_parameters():
    node, _stops = _make_node(min_distance_m=0.45)
    node._on_coord_command(_CommandMsg("req-yield", "robot_1", "yield", "not json{"))
    node._on_coord_status(_StatusMsg("req-yield", "robot_1", "ACTIVE"))
    _dispatch(node, "req-yield", "robot_2", "temporary_wait")

    node._on_scene_state(_scene(0.30))

    assert node._latched_stops == set()


def test_node_speed_rule_still_exempts_clearing_robot():
    # The speed rule is per robot, not per pair: a raw-cmd_vel backup is
    # exempt from it exactly as before.
    node, stops = _make_node(min_distance_m=0.45)
    _dispatch(node, "req-yield", "robot_1", "yield", {"passer_robot_id": "robot_2"})
    _dispatch(node, "req-yield", "robot_2", "temporary_wait")
    scene = {
        "robots": [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "linear_velocity": 0.5},
            {"robot_id": "robot_2", "x": 3.0, "y": 0.0, "linear_velocity": 0.1},
        ]
    }

    node._on_scene_state(_StringMsg(json.dumps(scene)))

    assert stops == []


_EQUIV_DISTANCES = (0.05, 0.30, 0.44, 0.46, 0.55, 0.65, 2.0)
_EQUIV_STATUSES = (
    ("MOVING", "MOVING"),
    ("STALE", "MOVING"),
    ("MOVING", "STALE"),
    ("STALE", "STALE"),
)
_EQUIV_PREVIOUS = (frozenset(), frozenset({"robot_1"}), frozenset({"robot_1", "robot_2"}))
_EQUIV_MEMORY = (None, 0.078, 0.5, 0.7)


def _equiv_shapes() -> dict[str, CoordinationTracker]:
    shapes: dict[str, CoordinationTracker] = {}
    for yielder, passer in (("robot_1", "robot_2"), ("robot_2", "robot_1")):
        tracker = CoordinationTracker()
        _yield_command(tracker, yielder, [passer])
        shapes[f"yield-{yielder}"] = tracker
        released = CoordinationTracker()
        _yield_command(released, yielder, [passer])
        released.record_status("req-yield", passer, "COMPLETED")
        shapes[f"yield-{yielder}-released"] = released
        derived = CoordinationTracker()
        _yield_command(
            derived,
            yielder,
            [passer],
            parameters={"passer_robot_id": passer, "crossing_order": [passer]},
        )
        shapes[f"yield-{yielder}-derived"] = derived
    shapes["yield-no-params"] = _tracker_with(
        ("req-yield", "robot_1", "yield"), ("req-yield", "robot_2", "temporary_wait")
    )
    shapes["reverse"] = _tracker_with(
        ("req-reverse", "robot_1", "reverse"), ("req-reverse", "robot_2", "reverse")
    )
    shapes["reroute"] = _tracker_with(
        ("req-reroute", "robot_1", "reroute"), ("req-reroute", "robot_2", "temporary_wait")
    )
    shapes["none"] = CoordinationTracker()
    return shapes


@pytest.mark.parametrize("shape", sorted(_equiv_shapes()))
def test_two_robot_pair_scope_matches_robot_scope(shape: str):
    # Byte-identity pin: with two robots whose clearing command names both, the
    # pair-scoped evaluation plus the speed-only subtraction equals the old
    # robot-scoped evaluation minus the exempt robots, on every combination of
    # distance, STALE status, prior latch and remembered distance.
    tracker = _equiv_shapes()[shape]
    exemption = tracker.exemption()
    robot_scoped = tracker.exempt_robots()
    for distance in _EQUIV_DISTANCES:
        for status_1, status_2 in _EQUIV_STATUSES:
            robots = [
                {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "status": status_1},
                {"robot_id": "robot_2", "x": distance, "y": 0.0, "status": status_2},
            ]
            for previous in _EQUIV_PREVIOUS:
                for remembered in _EQUIV_MEMORY:
                    memory = None if remembered is None else {_PAIR: remembered}
                    old = evaluate_latches(robots, _LIMITS, previous, memory, robot_scoped)
                    new = evaluate_latches(robots, _LIMITS, previous, memory, exemption)
                    old_effective = old.latched - robot_scoped
                    assert new.latched == old_effective
                    assert new.last_fresh_distances == old.last_fresh_distances
                    assert {r: new.reasons[r] for r in new.latched} == {
                        r: old.reasons[r] for r in old_effective
                    }
