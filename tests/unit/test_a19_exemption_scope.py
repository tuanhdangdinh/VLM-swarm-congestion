"""prereg-v3 A19 latch-aware exemption scope (M4 safety monitor, no ROS2).

A2 of the S1a anchor (docs/reports/2026-10-10-s1a-anchor.md) dispatched an
echo yield (robot_1 yields, robot_5 passes) while robot_1 was already latched
to a THIRD robot, robot_2, at 0.38 m. The exemption was pair-scoped
(robot_1+robot_5), so the robot_1+robot_2 min-distance latch kept zeroing the
backup and the bus FAILED the yield with no motion.

Ruling (A19): during a clearing command's window the commanded robot is
exempted from the latch against every robot it was ALREADY latched with when
the command started. One-sided (only the commanded robot is released; the
other robot stays held), frozen at command start (a latch formed during the
window still fires), ended per partner once the pair is seen at or beyond
`min_distance_m` again, and under the hard-contact floor when it is enabled.

The A2 fixture (`data/a19_exemption/a2_seed4_c2fcb3ed.json`) replays the M1
scene rows and the dispatched command of the real run. It proves the LATCH
flips (robot_1 is no longer held, robot_2 still is); it cannot prove motion,
which only a live run shows.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from swarm_execution.safety import (
    REASON_HARD_CONTACT_FLOOR,
    REASON_MIN_DISTANCE,
    REASON_STALE_POSE,
    ClearingExemption,
    CoordinationTracker,
    SafetyLimits,
    detect_proximity_violations,
    evaluate_latches,
)
from swarm_execution.safety_monitor_node import SafetyMonitorNode
from swarm_execution.yield_phase import BACKUP_STARTED_DETAIL, HOLD_STARTED_DETAIL

_FIXTURE = Path(__file__).parent / "data" / "a19_exemption" / "a2_seed4_c2fcb3ed.json"
_LIMITS = SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2)


def _a2() -> dict:
    return json.loads(_FIXTURE.read_text())


class _Msg:
    def __init__(self, **fields) -> None:
        self.__dict__.update(fields)


class _Logger:
    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []

    def info(self, msg) -> None:
        self.infos.append(str(msg))

    def warning(self, msg) -> None:
        self.warnings.append(str(msg))


def _node() -> tuple[SafetyMonitorNode, _Logger]:
    node = SafetyMonitorNode.__new__(SafetyMonitorNode)
    node._limits = _LIMITS
    node._latched_stops = set()
    node._coordination = CoordinationTracker()
    node._exempt_pairs = frozenset()
    node._last_fresh_distances = {}
    node._cancel_nav2_goal = lambda _robot_id: None
    node._emergency_stop = lambda _robot_id: None
    node._publish_holds = lambda: None
    logger = _Logger()
    node.get_logger = lambda: logger
    return node, logger


def _scene(node: SafetyMonitorNode, robots: list[dict]) -> None:
    node._on_scene_state(_Msg(data=json.dumps({"robots": robots})))


def _command(node: SafetyMonitorNode, command_id: str, action: dict) -> None:
    node._on_coord_command(
        _Msg(
            command_id=command_id,
            robot_id=action["robot_id"],
            action=action["action"],
            parameters_json=json.dumps(action["parameters"]),
        )
    )


def _status(node, command_id: str, robot_id: str, status: str, detail: str | None = None):
    node._on_coord_status(
        _Msg(command_id=command_id, robot_id=robot_id, status=status, detail=detail)
    )


def _dispatch_a2(node: SafetyMonitorNode, a2: dict) -> str:
    """Feed the A2 yield as the bus published it: commands, ACTIVE, backup start."""
    command_id = a2["command_id"]
    yielder, passer = a2["actions"]
    _command(node, command_id, yielder)
    _status(node, command_id, yielder["robot_id"], "ACTIVE")
    _command(node, command_id, passer)
    _status(node, command_id, passer["robot_id"], "ACTIVE")
    _status(node, command_id, yielder["robot_id"], "ACTIVE", BACKUP_STARTED_DETAIL)
    return command_id


def _rows(a2: dict, lo: float, hi: float) -> list[list[dict]]:
    return [row["robots"] for row in a2["scene_rows"] if lo <= row["stamp"] < hi]


def _replay_a2_until_dispatch(node: SafetyMonitorNode, a2: dict) -> None:
    for robots in _rows(a2, 0.0, a2["active_sim_t"]):
        _scene(node, robots)


def _pose(robots: list[dict], robot_id: str) -> dict:
    return next(r for r in robots if r["robot_id"] == robot_id)


def _moved(robots: list[dict], robot_id: str, distance_m: float) -> list[dict]:
    # M4 backs a yielder up along its own -heading.
    out = []
    for robot in robots:
        if robot["robot_id"] == robot_id:
            theta = robot["theta"]
            robot = {
                **robot,
                "x": robot["x"] - distance_m * math.cos(theta),
                "y": robot["y"] - distance_m * math.sin(theta),
            }
        out.append(robot)
    return out


def _gap(robots: list[dict], a: str, b: str) -> float:
    pa, pb = _pose(robots, a), _pose(robots, b)
    return math.hypot(pa["x"] - pb["x"], pa["y"] - pb["y"])


# ---------------------------------------------------------------------------
# The A2 fixture: reproduce, then flip.
# ---------------------------------------------------------------------------


def test_a2_fixture_robot_1_is_latched_to_robot_2_before_the_dispatch():
    a2 = _a2()
    node, _ = _node()

    _replay_a2_until_dispatch(node, a2)

    assert {"robot_1", "robot_2"} <= node._latched_stops
    last = _rows(a2, 0.0, a2["active_sim_t"])[-1]
    assert _gap(last, "robot_1", "robot_2") < 0.45
    assert _gap(last, "robot_1", "robot_5") > 0.45


def test_a2_fixture_commanded_yielder_is_released_from_its_third_robot_latch():
    a2 = _a2()
    node, _ = _node()
    _replay_a2_until_dispatch(node, a2)
    _dispatch_a2(node, a2)

    # Every recorded row after ACTIVE: the robots never moved in the real run.
    for robots in _rows(a2, a2["active_sim_t"], 53.0):
        _scene(node, robots)
        assert "robot_1" not in node._latched_stops, robots[0]
        assert "robot_2" in node._latched_stops


def test_a2_fixture_the_pair_exemption_alone_is_unchanged():
    a2 = _a2()
    node, _ = _node()
    _replay_a2_until_dispatch(node, a2)
    _dispatch_a2(node, a2)
    # Capture happens on the first scene tick after the command is known.
    _scene(node, _rows(a2, a2["active_sim_t"], 53.0)[0])

    exemption = node._coordination.exemption()

    assert exemption.pairs == {("robot_1", "robot_5")}
    assert exemption.waivers == {("robot_1", "robot_2")}


def test_a2_fixture_backup_separates_the_pair_and_ends_the_waiver():
    a2 = _a2()
    node, logger = _node()
    _replay_a2_until_dispatch(node, a2)
    _dispatch_a2(node, a2)
    start = _rows(a2, a2["active_sim_t"], 53.0)[0]

    released_at = None
    for step in range(1, 11):
        robots = _moved(start, "robot_1", 0.05 * step)
        _scene(node, robots)
        assert "robot_1" not in node._latched_stops
        if _gap(robots, "robot_1", "robot_2") < 0.45:
            assert "robot_2" in node._latched_stops
        elif released_at is None:
            released_at = step
            assert "robot_2" not in node._latched_stops

    assert released_at is not None
    assert node._coordination.exemption().waivers == frozenset()
    assert any(
        "latch waiver released robot=robot_1" in line and "partner=robot_2" in line
        and "reason=separated" in line
        for line in logger.infos
    )


def test_a2_fixture_re_approach_after_separation_latches_again():
    a2 = _a2()
    node, _ = _node()
    _replay_a2_until_dispatch(node, a2)
    _dispatch_a2(node, a2)
    start = _rows(a2, a2["active_sim_t"], 53.0)[0]
    _scene(node, _moved(start, "robot_1", 0.4))
    assert node._coordination.exemption().waivers == frozenset()

    _scene(node, start)

    assert {"robot_1", "robot_2"} <= node._latched_stops


def test_a2_fixture_arming_is_logged_once_with_the_command():
    a2 = _a2()
    node, logger = _node()
    _replay_a2_until_dispatch(node, a2)
    _dispatch_a2(node, a2)
    for robots in _rows(a2, a2["active_sim_t"], 40.0):
        _scene(node, robots)

    armed = [line for line in logger.infos if "latch waiver armed" in line]
    assert armed == [
        f"latch waiver armed robot=robot_1 command={a2['command_id']} partners=robot_2"
    ]


def test_a2_fixture_waiver_ends_when_the_yield_fails():
    a2 = _a2()
    node, _ = _node()
    _replay_a2_until_dispatch(node, a2)
    command_id = _dispatch_a2(node, a2)
    rows = _rows(a2, a2["active_sim_t"], 53.0)
    _scene(node, rows[0])

    _status(node, command_id, "robot_1", "FAILED")
    _scene(node, rows[1])

    assert node._coordination.exemption().waivers == frozenset()
    assert "robot_1" in node._latched_stops


# ---------------------------------------------------------------------------
# Scope: who, when, toward whom.
# ---------------------------------------------------------------------------


def _fresh(robot_id: str, x: float, y: float) -> dict:
    return {"robot_id": robot_id, "x": x, "y": y, "status": "MOVING"}


def _yield(tracker: CoordinationTracker, yielder: str, passer: str, cid: str = "c-yield"):
    tracker.record_command(cid, yielder, "yield", {"passer_robot_id": passer})
    tracker.record_status(cid, yielder, "ACTIVE")
    tracker.record_command(cid, passer, "temporary_wait", {"linked_position": 0})
    tracker.record_status(cid, passer, "ACTIVE")


def _pairs(*pairs: tuple[str, str]) -> frozenset[tuple[str, str]]:
    return frozenset(tuple(sorted(p)) for p in pairs)


def test_capture_takes_only_latched_pairs_not_a_radius():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")

    # robot_3 is close but was never latched with robot_1 (not in the pairs).
    armed = tracker.capture_latch_partners(_pairs(("robot_1", "robot_2")))

    assert armed == [("robot_1", "c-yield", ("robot_2",))]
    assert tracker.exemption().waivers == {("robot_1", "robot_2")}


def test_capture_is_frozen_at_command_start():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")
    tracker.capture_latch_partners(frozenset())

    armed = tracker.capture_latch_partners(_pairs(("robot_1", "robot_3")))

    assert armed == []
    assert tracker.exemption().waivers == frozenset()


def test_latch_formed_during_the_window_still_fires():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")
    tracker.capture_latch_partners(_pairs(("robot_1", "robot_2")))
    robots = [
        _fresh("robot_1", 0.0, 0.0),
        _fresh("robot_2", 0.38, 0.0),
        _fresh("robot_3", 0.0, -0.40),
        _fresh("robot_5", 0.0, 1.4),
    ]

    result = evaluate_latches(robots, _LIMITS, exempt=tracker.exemption())

    assert result.latched == {"robot_1", "robot_2", "robot_3"}


def test_passer_wait_never_arms_a_waiver():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")

    tracker.capture_latch_partners(_pairs(("robot_5", "robot_4"), ("robot_1", "robot_2")))
    robots = [
        _fresh("robot_1", 0.0, 0.0),
        _fresh("robot_2", 0.38, 0.0),
        _fresh("robot_5", 2.0, 0.0),
        _fresh("robot_4", 2.3, 0.0),
    ]
    result = evaluate_latches(robots, _LIMITS, exempt=tracker.exemption())

    assert tracker.exemption().waivers == {("robot_1", "robot_2")}
    assert {"robot_4", "robot_5", "robot_2"} <= result.latched
    assert "robot_1" not in result.latched


def test_navigation_leg_never_arms_a_waiver():
    tracker = CoordinationTracker()
    tracker.record_command("c-reroute", "robot_1", "reroute", {"waypoints": []})
    tracker.record_status("c-reroute", "robot_1", "ACTIVE")

    armed = tracker.capture_latch_partners(_pairs(("robot_1", "robot_2")))

    assert armed == []
    assert tracker.exemption().waivers == frozenset()


def test_reverse_robot_is_a_commanded_robot():
    tracker = CoordinationTracker()
    tracker.record_command("c-reverse", "robot_1", "reverse", {})
    tracker.record_status("c-reverse", "robot_1", "ACTIVE")

    tracker.capture_latch_partners(_pairs(("robot_1", "robot_3")))

    assert tracker.exemption().waivers == {("robot_1", "robot_3")}


def test_a_new_command_recaptures():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5", "c1-yield")
    tracker.capture_latch_partners(_pairs(("robot_1", "robot_2")))
    tracker.record_status("c1-yield", "robot_1", "COMPLETED")
    assert tracker.exemption().waivers == frozenset()

    _yield(tracker, "robot_1", "robot_5", "c2-yield")
    tracker.capture_latch_partners(_pairs(("robot_1", "robot_3")))

    assert tracker.exemption().waivers == {("robot_1", "robot_3")}


def test_waiver_survives_the_hold_phase_while_still_engaged():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")
    tracker.record_status("c-yield", "robot_1", "ACTIVE", BACKUP_STARTED_DETAIL)
    tracker.capture_latch_partners(_pairs(("robot_1", "robot_2")))

    tracker.record_status("c-yield", "robot_1", "ACTIVE", HOLD_STARTED_DETAIL)

    assert tracker.exemption().waivers == {("robot_1", "robot_2")}


def test_release_is_per_partner():
    tracker = CoordinationTracker()
    _yield(tracker, "robot_1", "robot_5")
    tracker.capture_latch_partners(_pairs(("robot_1", "robot_2"), ("robot_1", "robot_3")))

    released = tracker.release_separated_waivers(_pairs(("robot_1", "robot_3")))

    assert released == [("robot_1", "c-yield", "robot_2")]
    assert tracker.exemption().waivers == {("robot_1", "robot_3")}


# ---------------------------------------------------------------------------
# One-sidedness, the floor and the STALE rule.
# ---------------------------------------------------------------------------


def _waived() -> ClearingExemption:
    return ClearingExemption(
        clearing_robots=frozenset({"robot_1"}),
        pairs=frozenset({("robot_1", "robot_5")}),
        waivers=frozenset({("robot_1", "robot_2")}),
    )


def test_waiver_is_one_sided_in_the_proximity_rule():
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.38, 0.0)]

    assert detect_proximity_violations(robots, 0.45, _waived()) == {"robot_2"}


def test_waived_pair_is_reported_as_latched():
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.38, 0.0)]

    result = evaluate_latches(robots, _LIMITS, exempt=_waived())

    assert result.latched == {"robot_2"}
    assert result.reasons == {"robot_2": REASON_MIN_DISTANCE}
    assert result.latched_pairs == {("robot_1", "robot_2")}


def test_hard_contact_floor_still_latches_a_waived_yielder():
    limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, hard_contact_floor_m=0.20
    )
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.15, 0.0)]

    result = evaluate_latches(robots, limits, exempt=_waived())

    assert result.latched == {"robot_1", "robot_2"}
    assert result.reasons["robot_1"] == REASON_HARD_CONTACT_FLOOR
    assert result.reasons["robot_2"] == REASON_MIN_DISTANCE
    assert result.floor_breaches == {("robot_1", "robot_2"): pytest.approx(0.15)}


def test_hard_contact_floor_leaves_a_waived_yielder_above_it_free():
    limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, hard_contact_floor_m=0.20
    )
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.30, 0.0)]

    result = evaluate_latches(robots, limits, exempt=_waived())

    assert result.latched == {"robot_2"}
    assert result.floor_breaches == {}


def test_stale_pair_rule_is_one_sided_for_a_waived_pair():
    robots = [_fresh("robot_1", 0.0, 0.0), {**_fresh("robot_2", 0.38, 0.0), "status": "STALE"}]
    memory = {("robot_1", "robot_2"): 0.38}

    result = evaluate_latches(
        robots, _LIMITS, previous_latched={"robot_1", "robot_2"},
        last_fresh_distances=memory, exempt=_waived(),
    )

    assert "robot_1" not in result.latched
    assert result.reasons["robot_2"] in (REASON_MIN_DISTANCE, REASON_STALE_POSE)
    assert ("robot_1", "robot_2") in result.latched_pairs


# ---------------------------------------------------------------------------
# Byte-identity where the situation cannot arise.
# ---------------------------------------------------------------------------


def test_no_third_party_latch_leaves_the_exemption_identical():
    plain = CoordinationTracker()
    _yield(plain, "robot_1", "robot_5")
    captured = CoordinationTracker()
    _yield(captured, "robot_1", "robot_5")

    captured.capture_latch_partners(_pairs(("robot_1", "robot_5"), ("robot_3", "robot_4")))

    assert captured.exemption() == plain.exemption()
    assert captured.exemption() == ClearingExemption(
        clearing_robots=frozenset({"robot_1"}), pairs=frozenset({("robot_1", "robot_5")})
    )


def test_node_logs_nothing_new_without_a_multi_latched_yielder():
    node, logger = _node()
    node._on_coord_command(
        _Msg(command_id="c", robot_id="robot_1", action="yield",
             parameters_json=json.dumps({"passer_robot_id": "robot_2"}))
    )
    _status(node, "c", "robot_1", "ACTIVE")
    _scene(node, [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.3, 0.0)])

    assert not [line for line in logger.infos if "waiver" in line]


@pytest.mark.parametrize("distance", [0.10, 0.30, 0.44, 0.46, 1.0])
def test_empty_waivers_evaluate_identically(distance: float):
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", distance, 0.0)]
    exemption = ClearingExemption(
        clearing_robots=frozenset({"robot_1"}), pairs=frozenset({("robot_1", "robot_3")})
    )
    limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, hard_contact_floor_m=0.20
    )

    result = evaluate_latches(robots, limits, exempt=exemption)

    expected = {"robot_1", "robot_2"} if distance < 0.45 else set()
    assert result.latched == expected
    assert result.floor_breaches == {}
