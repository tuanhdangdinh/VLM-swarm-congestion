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


def test_key_on_leaves_latch_waiver_capture_unchanged():
    # A19 reads the legacy own-command set (plan partners included), so the
    # captured waivers are the same with the key on; P4 is out of scope.
    latched = frozenset({("robot_1", "robot_2"), ("robot_1", "robot_3")})
    results = []
    for key in (False, True):
        tracker = CoordinationTracker(scoped_exemption=key)
        _reverse(tracker, "c-rev", "robot_1", partners=["robot_2"])
        results.append(tracker.capture_latch_partners(latched))

    assert results[0] == results[1] == [("robot_1", "c-rev", ("robot_3",))]


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

    assert line.endswith(" scoped_clearing_exemption=True")


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

    assert fragment == {"scoped_clearing_exemption": True}
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
