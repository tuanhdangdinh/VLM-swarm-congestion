"""Scoped clearing exemption (`scoped_clearing_exemption`, M4, no ROS2).

A clearing robot's pair exemption is meant to cover only the robots its own
command addressed (`safety.admitted_partners`). Two paths widened it at the
deployed runtime (68e67b5), both left in place with the key off:

* P1/P2 -- `plan_continue_partners`: M5 names every `continue` leg of the
  scene-wide plan that is in the triggering event's robot set. The trigger
  set is every stalled robot in the scene, so a reverse in one cluster became
  exempt against another cluster's robots (Stage 1 pos27, decision 5d51cf8d:
  robot_1/robot_4 reverse in group B, exempt against robot_2/robot_3 of group
  A). The list is frozen at publish: it survived a newer plan and the
  partner going ACTIVE on its own command.
* P3 -- a robot whose leg of a command was rejected (FAILED with no ACTIVE,
  e.g. the bus's "robot busy") stayed a member of that command.

With the key on, M4 honours neither: every reverse/yield code path makes each
robot the decision named a member of the command (command_grounder reverse
fan-outs and the junction recede phases), so a named partner outside the
command is never a robot the decision was grounded against.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from swarm_execution.safety import (
    CoordinationTracker,
    SafetyLimits,
    detect_proximity_violations,
    evaluate_latches,
)
from swarm_execution.safety_monitor_node import limits_from_config, startup_log_line
from swarm_execution.yield_phase import BACKUP_STARTED_DETAIL

REPO = Path(__file__).resolve().parents[2]


def _fresh(robot_id: str, x: float, y: float) -> dict:
    return {"robot_id": robot_id, "x": x, "y": y, "status": "MOVING"}


def _reverse(tracker, command_id, robot_id, partners=None, **extra):
    params = dict(extra)
    if partners is not None:
        params["plan_continue_partners"] = partners
    tracker.record_command(command_id, robot_id, "reverse", params)
    tracker.record_status(command_id, robot_id, "ACTIVE")


def _wait(tracker, command_id, robot_id, params=None):
    tracker.record_command(command_id, robot_id, "temporary_wait", params or {})
    tracker.record_status(command_id, robot_id, "ACTIVE")


# P1: plan-continue partners outside the command


def test_cross_cluster_continue_partner_not_exempt_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])

    assert not tracker.exemption().covers_pair("robot_1", "robot_2")


def test_cross_cluster_continue_partner_exempt_with_key_off():
    # Legacy pin: the deployed behaviour the running experiment reproduces.
    tracker = CoordinationTracker(scoped_exemption=False)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])

    assert tracker.exemption().covers_pair("robot_1", "robot_2")


def test_same_decision_partner_still_exempt_with_key_on():
    # A partner the command itself addressed (the decision's own robot) keeps
    # its exemption whether or not M5 also named it as a continue partner.
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_4"])
    _reverse(tracker, "c-rev", "robot_4", partners=["robot_1"])

    assert tracker.exemption().pairs == {("robot_1", "robot_4")}


def test_junction_recede_hold_member_still_exempt_with_key_on():
    # IB10 recede phase: the reverser is exempt against every robot its
    # command holds, the junction crossing's precondition.
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-recede-4", "robot_4")
    for robot_id in ("robot_1", "robot_2", "robot_3"):
        _wait(tracker, "c-recede-4", robot_id)

    assert tracker.exemption().pairs == {
        ("robot_1", "robot_4"),
        ("robot_2", "robot_4"),
        ("robot_3", "robot_4"),
    }


def test_named_continue_partner_outside_command_not_exempt_with_key_on():
    # `test_reverse_exempts_a_same_plan_continue_partner`'s shape (step-7a
    # finding 3): robot_1 IS named on the reverse but was never addressed.
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "req-reverse", "robot_4", partners=["robot_1"])

    assert not tracker.exemption().covers_pair("robot_1", "robot_4")


def test_trigger_spanning_two_clusters_exempts_only_own_command_with_key_on():
    # Stage 1 pos27 decision 5d51cf8d: event = all five robots, decision =
    # robot_1/robot_4 (group B), continue legs robot_2/robot_3 (group A).
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "5d51-reverse", "robot_1", partners=["robot_2", "robot_3"])
    _reverse(tracker, "5d51-reverse", "robot_4", partners=["robot_2", "robot_3"])

    assert tracker.exemption().pairs == {("robot_1", "robot_4")}


def test_trigger_spanning_two_clusters_exempts_other_cluster_with_key_off():
    tracker = CoordinationTracker(scoped_exemption=False)
    _reverse(tracker, "5d51-reverse", "robot_1", partners=["robot_2", "robot_3"])
    _reverse(tracker, "5d51-reverse", "robot_4", partners=["robot_2", "robot_3"])

    assert tracker.exemption().pairs == {
        ("robot_1", "robot_2"),
        ("robot_1", "robot_3"),
        ("robot_1", "robot_4"),
        ("robot_2", "robot_4"),
        ("robot_3", "robot_4"),
    }


def test_partner_list_widened_by_plan_hold_not_honoured_with_key_on():
    # A plan hold overwrites `_trigger_robots_by_plan[plan_id]` with the new
    # event's set, so a later junction phase's reverse can carry a wider list.
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-recede-3", "robot_3", partners=["robot_5"], plan_id=1)
    _wait(tracker, "c-recede-3", "robot_1")

    assert tracker.exemption().pairs == {("robot_1", "robot_3")}


def test_contradiction_reanalysis_wide_partner_set_not_honoured_with_key_on():
    # A contradiction-trigger re-analysis carries the ORIGINAL event's robot
    # set forward, i.e. possibly the whole scene.
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(
        tracker,
        "c-contra-reverse",
        "robot_2",
        partners=["robot_1", "robot_3", "robot_4", "robot_5"],
    )

    assert tracker.exemption().pairs == frozenset()


def test_unexempted_cross_cluster_partner_latches_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.30, 0.0)]

    assert detect_proximity_violations(robots, 0.45, tracker.exemption()) == {
        "robot_1",
        "robot_2",
    }


# P2: partner lifetime


def test_partner_active_elsewhere_not_exempt_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])
    _wait(tracker, "c-other", "robot_2")

    assert not tracker.exemption().covers_pair("robot_1", "robot_2")


def test_partner_active_elsewhere_stays_exempt_with_key_off():
    # P2 legacy pin: the frozen list survives the partner's own command.
    tracker = CoordinationTracker(scoped_exemption=False)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])
    _wait(tracker, "c-other", "robot_2")

    assert tracker.exemption().covers_pair("robot_1", "robot_2")


def test_superseding_plan_does_not_reexempt_partner_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c1-reverse", "robot_1", partners=["robot_2"], plan_id=1)
    _reverse(tracker, "c2-reverse", "robot_3", partners=["robot_4"], plan_id=2)

    assert not tracker.exemption().covers_pair("robot_1", "robot_2")


def test_superseded_plan_partner_stays_exempt_with_key_off():
    tracker = CoordinationTracker(scoped_exemption=False)
    _reverse(tracker, "c1-reverse", "robot_1", partners=["robot_2"], plan_id=1)
    _reverse(tracker, "c2-reverse", "robot_3", partners=["robot_4"], plan_id=2)

    assert tracker.exemption().covers_pair("robot_1", "robot_2")


# P3: a rejected leg is not a member


def _busy_reject_setup(tracker: CoordinationTracker) -> None:
    _wait(tracker, "c-old", "robot_3")
    _reverse(tracker, "c-new", "robot_1")
    tracker.record_command("c-new", "robot_3", "temporary_wait", {})
    tracker.record_status("c-new", "robot_3", "FAILED", "robot busy: c-old")


def test_rejected_leg_robot_not_a_member_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _busy_reject_setup(tracker)

    assert not tracker.exemption().covers_pair("robot_1", "robot_3")


def test_rejected_leg_robot_stays_a_member_with_key_off():
    tracker = CoordinationTracker(scoped_exemption=False)
    _busy_reject_setup(tracker)

    assert tracker.exemption().covers_pair("robot_1", "robot_3")


def test_rejected_leg_stays_excluded_after_its_old_command_ends_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _busy_reject_setup(tracker)

    tracker.record_status("c-old", "robot_3", "COMPLETED")

    assert not tracker.exemption().covers_pair("robot_1", "robot_3")


def test_rejection_seen_before_its_command_still_excludes_with_key_on():
    # Commands (from M5) and statuses (from the bus) have no cross-topic order.
    tracker = CoordinationTracker(scoped_exemption=True)
    _wait(tracker, "c-old", "robot_3")
    _reverse(tracker, "c-new", "robot_1")
    tracker.record_status("c-new", "robot_3", "FAILED", "robot busy: c-old")
    tracker.record_command("c-new", "robot_3", "temporary_wait", {})

    assert not tracker.exemption().covers_pair("robot_1", "robot_3")


def test_rejected_passer_in_crossing_order_not_partner_while_backing_up_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    _wait(tracker, "c-old", "robot_2")
    tracker.record_command(
        "c-yield",
        "robot_1",
        "yield",
        {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_3"]},
    )
    tracker.record_status("c-yield", "robot_1", "ACTIVE", BACKUP_STARTED_DETAIL)
    tracker.record_command("c-yield", "robot_2", "temporary_wait", {"linked_position": 0})
    tracker.record_status("c-yield", "robot_2", "FAILED", "robot busy: c-old")
    _wait(tracker, "c-yield", "robot_3", {"linked_position": 1})

    assert tracker.exemption().pairs == {("robot_1", "robot_3")}


def test_member_failing_after_it_was_active_is_unchanged_with_key_on():
    # Only a leg that never went ACTIVE is a rejection; a leg that ran and
    # then failed keeps the legacy membership.
    on = CoordinationTracker(scoped_exemption=True)
    off = CoordinationTracker(scoped_exemption=False)
    for tracker in (on, off):
        _reverse(tracker, "c-rev", "robot_1")
        _wait(tracker, "c-rev", "robot_2")
        tracker.record_status("c-rev", "robot_2", "FAILED", "wait aborted")

    assert on.exemption() == off.exemption()


# Key off is byte-identical; key on never ADDS an exemption


def _script(tracker: CoordinationTracker) -> list:
    snapshots = []
    _reverse(tracker, "a-rev", "robot_1", partners=["robot_2", "robot_5"], plan_id=1)
    snapshots.append(tracker.exemption())
    _wait(tracker, "a-rev", "robot_4")
    tracker.record_command(
        "b-yield",
        "robot_3",
        "yield",
        {"passer_robot_id": "robot_2", "crossing_order": ["robot_2", "robot_5"]},
    )
    tracker.record_status("b-yield", "robot_3", "ACTIVE", BACKUP_STARTED_DETAIL)
    snapshots.append(tracker.exemption())
    tracker.record_command("b-yield", "robot_4", "temporary_wait", {})
    tracker.record_status("b-yield", "robot_4", "FAILED", "robot busy: a-rev")
    _wait(tracker, "b-yield", "robot_2", {"linked_position": 0})
    snapshots.append(tracker.exemption())
    tracker.record_status("b-yield", "robot_3", "ACTIVE", "holding for passing robot")
    tracker.record_status("b-yield", "robot_2", "COMPLETED")
    snapshots.append(tracker.exemption())
    tracker.record_status("a-rev", "robot_1", "COMPLETED")
    snapshots.append(tracker.exemption())
    return snapshots


def test_default_tracker_is_key_off():
    assert _script(CoordinationTracker()) == _script(CoordinationTracker(scoped_exemption=False))


def test_key_on_only_removes_pairs():
    for on, off in zip(
        _script(CoordinationTracker(scoped_exemption=True)),
        _script(CoordinationTracker(scoped_exemption=False)),
        strict=True,
    ):
        assert on.pairs <= off.pairs
        assert on.clearing_robots == off.clearing_robots
        assert on.waivers == off.waivers


def test_latch_waiver_capture_key_off_keeps_plan_partner_in_own_set():
    # 68e67b5 pin: a named plan partner is "own", so A19 never waives it.
    latched = frozenset({("robot_1", "robot_2"), ("robot_1", "robot_3")})
    tracker = CoordinationTracker(scoped_exemption=False)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])

    assert tracker.capture_latch_partners(latched) == [("robot_1", "c-rev", ("robot_3",))]


def test_latch_waiver_capture_key_on_treats_unhonoured_partner_as_third_robot():
    latched = frozenset({("robot_1", "robot_2"), ("robot_1", "robot_3")})
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])

    assert tracker.capture_latch_partners(latched) == [
        ("robot_1", "c-rev", ("robot_2", "robot_3"))
    ]


# Config key, loader and startup line


_BASE = {
    "min_distance_m": 0.45,
    "max_linear_velocity_mps": 0.2,
    "stale_pose_is_unsafe": True,
    "stale_unsafe_distance_m": 0.6,
    "hard_contact_floor_m": 0.2,
}


def test_limits_key_defaults_off():
    assert limits_from_config(_BASE).scoped_clearing_exemption is False


def test_limits_key_on_when_true():
    limits = limits_from_config({**_BASE, "scoped_clearing_exemption": True})

    assert limits.scoped_clearing_exemption is True


@pytest.mark.parametrize("value", ["true", 1, "yes", None])
def test_limits_key_off_unless_exactly_true(value):
    data = {**_BASE, "scoped_clearing_exemption": value}

    assert limits_from_config(data).scoped_clearing_exemption is False


def test_limits_from_config_matches_legacy_fields():
    assert limits_from_config(_BASE) == SafetyLimits(
        min_distance_m=0.45,
        max_linear_velocity_mps=0.2,
        stale_pose_is_unsafe=True,
        stale_unsafe_distance_m=0.6,
        hard_contact_floor_m=0.2,
    )


def test_startup_line_key_off_is_the_68e67b5_line():
    line = startup_log_line(limits_from_config(_BASE))

    assert line == (
        "Safety monitor started min_distance_m=0.45 max_linear_velocity_mps=0.2 "
        "stale_pose_is_unsafe=True stale_unsafe_distance_m=0.6 "
        "hard_contact_floor_m=0.2 exempt_actions=reverse,yield"
    )


def test_startup_line_names_the_key_when_on():
    line = startup_log_line(limits_from_config({**_BASE, "scoped_clearing_exemption": True}))

    assert " scoped_clearing_exemption=True" in line


@pytest.mark.parametrize(
    "pinned",
    ["ros2_ws/src/swarm_execution/config/safety.yaml", "config/safety/safety_floor020.yaml"],
)
def test_overlay_fragment_adds_only_the_key(pinned):
    base = yaml.safe_load((REPO / pinned).read_text())["safety"]
    fragment = yaml.safe_load(
        (REPO / "config/safety/scoped_clearing_exemption.fragment.yaml").read_text()
    )["safety"]
    merged = {**base, **fragment}

    assert fragment == {
        "scoped_clearing_exemption": True,
        "waiver_closing_tolerance_m": 0.05,
        "waiver_closing_readings": 3,
    }
    assert limits_from_config(merged) == SafetyLimits(
        **{**limits_from_config(base).__dict__, "scoped_clearing_exemption": True}
    )


def test_key_on_cross_cluster_pair_latches_in_evaluate_latches():
    tracker = CoordinationTracker(scoped_exemption=True)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])
    limits = SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_2", 0.30, 0.0)]

    evaluation = evaluate_latches(robots, limits, exempt=tracker.exemption())

    assert evaluation.latched == {"robot_1", "robot_2"}


# Manoeuvres that depend on own-command scope must keep it with the key on


def _convoy_sequence(tracker: CoordinationTracker) -> list:
    # convoy_counterflow_slip: robot_2 yields, robot_1/robot_3/robot_4 pass
    # one by one; robot_3 and robot_4 are ~2 m away at dispatch.
    snapshots = []
    order = {"passer_robot_id": "robot_1", "crossing_order": ["robot_1", "robot_3", "robot_4"]}
    tracker.record_command("c-convoy", "robot_2", "yield", order)
    tracker.record_status("c-convoy", "robot_2", "ACTIVE", BACKUP_STARTED_DETAIL)
    for position, passer in enumerate(("robot_1", "robot_3", "robot_4")):
        _wait(tracker, "c-convoy", passer, {"linked_position": position})
    snapshots.append(tracker.exemption().pairs)
    tracker.record_status("c-convoy", "robot_2", "ACTIVE", "holding for passing robot")
    snapshots.append(tracker.exemption().pairs)
    for passer in ("robot_1", "robot_3", "robot_4"):
        tracker.record_status("c-convoy", passer, "COMPLETED", "released: passer cleared")
        snapshots.append(tracker.exemption().pairs)
    return snapshots


def test_convoy_passers_exempt_against_yielder_when_admitted_with_key_on():
    on = _convoy_sequence(CoordinationTracker(scoped_exemption=True))

    assert on[1] == {("robot_1", "robot_2")}
    assert ("robot_2", "robot_3") in on[2]
    assert ("robot_2", "robot_4") in on[3]


def test_convoy_sequence_identical_with_key_on_and_off():
    assert _convoy_sequence(CoordinationTracker(scoped_exemption=True)) == _convoy_sequence(
        CoordinationTracker(scoped_exemption=False)
    )


def test_junction_crossing_yielder_exempt_against_all_three_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    tracker.record_command(
        "c-junction-cross",
        "robot_1",
        "yield",
        {"passer_robot_id": "robot_2", "crossing_order": ["robot_2"]},
    )
    tracker.record_status("c-junction-cross", "robot_1", "ACTIVE", BACKUP_STARTED_DETAIL)
    for robot_id in ("robot_2", "robot_4", "robot_3"):
        _wait(tracker, "c-junction-cross", robot_id)

    assert tracker.exemption().pairs == {
        ("robot_1", "robot_2"),
        ("robot_1", "robot_3"),
        ("robot_1", "robot_4"),
    }


def test_s6_four_robot_reverse_keeps_own_command_scope_with_key_on():
    # s6_dual_conflict: one reverse naming all four robots exempts pairs
    # across both head-on conflicts (P5, deliberately unchanged).
    tracker = CoordinationTracker(scoped_exemption=True)
    for robot_id in ("robot_1", "robot_2", "robot_3", "robot_4"):
        _reverse(tracker, "c-s6-reverse", robot_id)

    assert len(tracker.exemption().pairs) == 6


def _node_logs(key_on: bool) -> list[str]:
    import json as _json
    from types import SimpleNamespace

    from swarm_execution.safety_monitor_node import SafetyMonitorNode

    node = SafetyMonitorNode.__new__(SafetyMonitorNode)
    node._limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, scoped_clearing_exemption=key_on
    )
    node._coordination = CoordinationTracker(scoped_exemption=key_on)
    logs: list[str] = []
    logger = SimpleNamespace(info=logs.append, warning=logs.append)
    node.get_logger = lambda: logger
    node._on_coord_command(
        SimpleNamespace(
            command_id="c-rev",
            robot_id="robot_1",
            action="reverse",
            parameters_json=_json.dumps({"plan_continue_partners": ["robot_2"]}),
        )
    )
    node._on_coord_status(SimpleNamespace(command_id="c-rev", robot_id="robot_1", status="ACTIVE"))
    node._on_coord_status(
        SimpleNamespace(
            command_id="c-rev", robot_id="robot_3", status="FAILED", detail="robot busy: c-old"
        )
    )
    return logs


def test_node_key_off_emits_no_new_log_lines():
    assert not any("not honoured" in m or "rejected leg" in m for m in _node_logs(False))


def test_node_key_on_logs_unhonoured_partners_and_rejected_leg():
    logs = _node_logs(True)

    assert any("plan continue partners not honoured" in m and "robot_2" in m for m in logs)
    assert any("rejected leg not a member robot=robot_3" in m for m in logs)


# A19 inputs with the key on (owner ruling 2026-11-14): an unhonoured plan
# partner and a rejected-leg robot are third robots, so a reverser that
# starts latched with one is released one-sidedly and the other robot held.

_LIMITS = SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2)
_LIMITS_FLOOR = SafetyLimits(
    min_distance_m=0.45, max_linear_velocity_mps=0.2, hard_contact_floor_m=0.20
)


class _Monitor:
    """The monitor's per-scene sequence (`SafetyMonitorNode._on_scene_state`)."""

    def __init__(self, tracker: CoordinationTracker, limits: SafetyLimits = _LIMITS) -> None:
        self.tracker = tracker
        self.limits = limits
        self.latched: frozenset[str] = frozenset()
        self.pairs: frozenset[tuple[str, str]] = frozenset()
        self.memory: dict = {}
        self.revoked: list = []

    def tick(self, robots: list[dict]) -> frozenset[str]:
        self.tracker.capture_latch_partners(self.pairs)
        self.revoked += self.tracker.revoke_closing_waivers(robots)
        evaluation = evaluate_latches(
            robots, self.limits, self.latched, self.memory, self.tracker.exemption()
        )
        self.latched, self.pairs = evaluation.latched, evaluation.latched_pairs
        self.memory = evaluation.last_fresh_distances
        self.tracker.release_separated_waivers(self.pairs)
        return self.latched


def _vp10_robots() -> list[dict]:
    # vp10 reverse 1296b5b8 at command start: robot_3 (continue) 0.354 m from
    # robot_1 and 0.244 m from robot_2; robot_4 0.47 m from robot_3.
    return [
        _fresh("robot_1", -0.104, 0.0),
        _fresh("robot_2", 0.25, 0.25),
        _fresh("robot_3", 0.25, 0.006),
        _fresh("robot_4", 0.25, -0.464),
    ]


def _vp10(key_on: bool) -> frozenset[str]:
    tracker = CoordinationTracker(scoped_exemption=key_on)
    monitor = _Monitor(tracker)
    robots = _vp10_robots()
    monitor.tick(robots)  # latches standing before the command
    for robot_id in ("robot_1", "robot_2", "robot_4"):
        _reverse(tracker, "c-1296-reverse", robot_id, partners=["robot_3"])
    monitor.tick(robots)  # capture at command start
    return monitor.tick(robots)


def test_vp10_key_on_releases_reversers_and_holds_continuing_robot():
    assert _vp10(True) == {"robot_3"}


def test_vp10_key_off_holds_nobody():
    # Legacy: robot_3 is an exempt plan partner of every reverser.
    assert _vp10(False) == frozenset()


def test_rejected_leg_robot_is_waived_and_held_with_key_on():
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]
    _wait(tracker, "c-old", "robot_3")
    monitor.tick(robots)
    _busy_reject_setup_new_only(tracker)
    monitor.tick(robots)

    assert monitor.tick(robots) == {"robot_3"}


def _busy_reject_setup_new_only(tracker: CoordinationTracker) -> None:
    _reverse(tracker, "c-new", "robot_1")
    tracker.record_command("c-new", "robot_3", "temporary_wait", {})
    tracker.record_status("c-new", "robot_3", "FAILED", "robot busy: c-old")


def test_rejection_after_capture_still_waives_start_latch_with_key_on():
    # The bus FAILs a busy leg on receipt, but a scene tick can capture the
    # waiver before that status arrives; the start-time latch still counts.
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]
    _wait(tracker, "c-old", "robot_3")
    monitor.tick(robots)
    _reverse(tracker, "c-new", "robot_1")
    tracker.record_command("c-new", "robot_3", "temporary_wait", {})
    monitor.tick(robots)  # capture: robot_3 still looks like a member
    tracker.record_status("c-new", "robot_3", "FAILED", "robot busy: c-old")

    assert monitor.tick(robots) == {"robot_3"}


def test_rejected_leg_without_start_latch_is_not_waived_with_key_on():
    # A19 is frozen at command start: a latch that forms later still holds both.
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker)
    _wait(tracker, "c-old", "robot_3")
    monitor.tick([_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 1.0, 0.0)])
    _busy_reject_setup_new_only(tracker)
    monitor.tick([_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 1.0, 0.0)])

    assert monitor.tick([_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]) == {
        "robot_1",
        "robot_3",
    }


def _third_robot_waiver(limits: SafetyLimits = _LIMITS, gap_m: float = 0.30) -> _Monitor:
    """robot_1 reverses; robot_3 is an unhonoured plan partner latched at start."""
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker, limits)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", gap_m, 0.0)]
    monitor.tick(robots)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_3"])
    monitor.tick(robots)
    return monitor


def _gap(monitor: _Monitor, gaps: list[float], stale: bool = False) -> list[frozenset[str]]:
    held = []
    for gap in gaps:
        robot_1 = _fresh("robot_1", 0.30 - gap, 0.0)
        if stale:
            robot_1["status"] = "STALE"
        held.append(monitor.tick([robot_1, _fresh("robot_3", 0.30, 0.0)]))
    return held


def test_closing_reverser_is_reheld_after_debounce():
    # Direction check (owner ruling 2026-11-14): shrinking by more than
    # waiver_closing_tolerance_m (0.05) below the widest gap seen, on
    # waiver_closing_readings (3) consecutive fresh readings, ends the waiver.
    monitor = _third_robot_waiver()

    held = _gap(monitor, [0.29, 0.24, 0.23, 0.22])

    assert held == [{"robot_3"}, {"robot_3"}, {"robot_3"}, {"robot_1", "robot_3"}]


def test_revoked_waiver_stays_revoked_when_the_gap_reopens():
    monitor = _third_robot_waiver()
    _gap(monitor, [0.24, 0.23, 0.22])

    assert _gap(monitor, [0.40]) == [{"robot_1", "robot_3"}]
    assert [(r, c, p) for r, c, p, _d, _m in monitor.revoked] == [("robot_1", "c-rev", "robot_3")]


def test_opening_reverser_stays_released():
    monitor = _third_robot_waiver()

    assert _gap(monitor, [0.31, 0.34, 0.38, 0.42]) == [{"robot_3"}] * 4


def test_stationary_pair_is_releasable():
    # A reverser that has not started moving must be able to start.
    monitor = _third_robot_waiver()

    assert _gap(monitor, [0.30] * 10) == [{"robot_3"}] * 10


def test_m1_jitter_does_not_flap_the_hold():
    # Stationary M1 pair-distance noise peaks at 0.0045 m peak-to-peak in the
    # recorded IB10/S1b scenes; even 10x that, alternating, never accumulates
    # three consecutive readings past the tolerance.
    monitor = _third_robot_waiver()

    gaps = [0.30, 0.255, 0.30, 0.255, 0.30, 0.24, 0.30, 0.24, 0.30]

    assert _gap(monitor, gaps) == [{"robot_3"}] * len(gaps)


def test_rotate_in_place_stays_released():
    # A diff-drive turn moves the marker centre only by its offset from the
    # rotation axis; a 0.02 m circle stays inside the tolerance.
    import math

    monitor = _third_robot_waiver()
    held = []
    for step in range(12):
        angle = step * math.pi / 6
        robot_1 = _fresh("robot_1", 0.02 * math.cos(angle), 0.02 * math.sin(angle))
        held.append(monitor.tick([robot_1, _fresh("robot_3", 0.30, 0.0)]))

    assert held == [{"robot_3"}] * 12


def test_stale_reading_freezes_the_direction_check():
    # No fresh distance, no verdict: a STALE pair keeps its waiver state
    # (A19's own STALE handling is unchanged).
    monitor = _third_robot_waiver()

    _gap(monitor, [0.24, 0.23, 0.22], stale=True)

    assert monitor.revoked == []


def test_legacy_a19_waiver_has_no_direction_check():
    # Approved scope: only the 2026-11-14 third-robot path is checked. A
    # bystander latched at start (an A19 waiver since prereg-v3) is not.
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]
    monitor.tick(robots)
    _reverse(tracker, "c-rev", "robot_1")
    monitor.tick(robots)

    assert _gap(monitor, [0.24, 0.23, 0.22, 0.21]) == [{"robot_3"}] * 4


def test_waived_reverser_closing_below_hard_contact_floor_is_held():
    # The floor still latches both robots of a waived pair at once.
    monitor = _third_robot_waiver(_LIMITS_FLOOR)

    assert _gap(monitor, [0.15]) == [{"robot_1", "robot_3"}]


def test_direction_check_is_a_no_op_with_key_off():
    tracker = CoordinationTracker(scoped_exemption=False)
    monitor = _Monitor(tracker)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]
    monitor.tick(robots)
    _reverse(tracker, "c-rev", "robot_1", partners=["robot_3"])
    monitor.tick(robots)

    assert _gap(monitor, [0.24, 0.23, 0.22, 0.21]) == [frozenset()] * 4
    assert monitor.revoked == []


def test_limits_direction_defaults():
    limits = limits_from_config(_BASE)

    assert (limits.waiver_closing_tolerance_m, limits.waiver_closing_readings) == (0.05, 3)


def test_limits_direction_thresholds_from_config():
    data = {**_BASE, "waiver_closing_tolerance_m": 0.08, "waiver_closing_readings": 5}
    limits = limits_from_config(data)

    assert (limits.waiver_closing_tolerance_m, limits.waiver_closing_readings) == (0.08, 5)


@pytest.mark.parametrize(
    ("field", "value"), [("waiver_closing_tolerance_m", 0.0), ("waiver_closing_readings", 0)]
)
def test_limits_reject_nonpositive_direction_thresholds(field, value):
    with pytest.raises(ValueError):
        SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2, **{field: value})


def test_startup_line_names_direction_thresholds_when_on():
    line = startup_log_line(limits_from_config({**_BASE, "scoped_clearing_exemption": True}))

    assert line.endswith(
        " scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3"
    )


def test_closing_reverser_against_rejected_leg_is_reheld():
    tracker = CoordinationTracker(scoped_exemption=True)
    monitor = _Monitor(tracker)
    robots = [_fresh("robot_1", 0.0, 0.0), _fresh("robot_3", 0.30, 0.0)]
    _wait(tracker, "c-old", "robot_3")
    monitor.tick(robots)
    _busy_reject_setup_new_only(tracker)
    monitor.tick(robots)

    assert _gap(monitor, [0.24, 0.23, 0.22])[-1] == {"robot_1", "robot_3"}


def test_node_scene_path_revokes_and_logs_a_closing_third_robot_waiver():
    import json as _json
    from types import SimpleNamespace

    from swarm_execution.safety_monitor_node import SafetyMonitorNode

    node = SafetyMonitorNode.__new__(SafetyMonitorNode)
    node._limits = SafetyLimits(
        min_distance_m=0.45, max_linear_velocity_mps=0.2, scoped_clearing_exemption=True
    )
    node._coordination = CoordinationTracker(scoped_exemption=True)
    node._latched_stops = set()
    node._exempt_pairs = frozenset()
    node._last_fresh_distances = {}
    node._cancel_nav2_goal = lambda _r: None
    node._emergency_stop = lambda _r: None
    node._publish_holds = lambda: None
    logs: list[str] = []
    logger = SimpleNamespace(info=logs.append, warning=logs.append)
    node.get_logger = lambda: logger

    def scene(gap):
        robots = [
            {"robot_id": "robot_1", "x": 0.30 - gap, "y": 0.0, "status": "MOVING"},
            {"robot_id": "robot_3", "x": 0.30, "y": 0.0, "status": "MOVING"},
        ]
        node._on_scene_state(SimpleNamespace(data=_json.dumps({"robots": robots})))

    scene(0.30)
    _reverse(node._coordination, "c-rev", "robot_1", partners=["robot_3"])
    for gap in (0.30, 0.24, 0.23, 0.22):
        scene(gap)

    assert node._latched_stops == {"robot_1", "robot_3"}
    assert any("latch waiver revoked robot=robot_1" in m and "reason=closing" in m for m in logs)
