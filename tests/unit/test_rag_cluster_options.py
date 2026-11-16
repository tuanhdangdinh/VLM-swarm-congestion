"""Shared M3 per-group code on plain inputs: grouping, probing, executed keys, joint check."""

from __future__ import annotations

import inspect
import typing
from typing import Any

import pytest
from pydantic import ValidationError

from reasoning.rag import cluster_options
from reasoning.rag.cluster_options import (
    GroupingParams,
    ProbeInputs,
    executed_key,
    executed_key_v2,
    generate_cluster_candidates,
    ground_probe,
    observed_groups,
)
from reasoning.rag.joint_check import DEFAULT_SAFETY_RADIUS_M, joint_check
from reasoning.rag.maneuver_geometry import GroundingParams as M3Params
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.vlm.executable_options import OUTSIDE, SPAN, ClusterOption
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

_PROBE_FIELDS = {
    "request_id",
    "backend_id",
    "snapshot",
    "geometry",
    "static_obstacles",
    "yield_feasibility_mode",
    "params",
    "priorities",
    "goal_references",
    "task_intents",
}


def _frame(*robots: tuple[str, float, float, str]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0, status=status)
            for rid, x, y, status in robots
        ],
    )


def _two_groups() -> SnapshotFrame:
    # A = robot_1, robot_2 (+ robot_5 MOVING, 1.0 m from robot_2); B = robot_3, robot_4.
    return _frame(
        ("robot_1", 0.0, 0.0, "STOPPED"),
        ("robot_2", 1.0, 0.0, "STOPPED"),
        ("robot_3", 5.0, 0.0, "STOPPED"),
        ("robot_4", 6.0, 0.0, "SLOW"),
        ("robot_5", 2.0, 0.0, "MOVING"),
    )


def _as_asked(decision: dict[str, Any]) -> dict[str, Any]:
    """A fake M3 that executes every probe exactly as asked."""
    robots = decision["involved_robots"]
    strategy = decision["strategy"]
    if strategy == "yield":
        yielder = decision["yield_robot"]
        order = decision.get("crossing_order") or [r for r in robots if r != yielder]
        passers = [r for r in order if r != yielder]
        return {
            "actions": [
                {"action": "yield", "robot_id": yielder,
                 "parameters": {"crossing_order": passers, "retreat_x_m": 0.0,
                                "retreat_y_m": 1.0}},
                *({"action": "temporary_wait", "robot_id": p,
                   "parameters": {"linked_position": i}} for i, p in enumerate(passers)),
            ]
        }
    if strategy == "reroute":
        return {"actions": [{"action": "reroute", "robot_id": r,
                             "parameters": {"waypoints": [[0.0, 3.0]]}} for r in robots]}
    return {"actions": [{"action": strategy, "robot_id": r, "parameters": {}} for r in robots]}


def test_observed_groups_links_seeds_and_attaches_moving_robot():
    groups = observed_groups(_two_groups(), GroupingParams(threshold_m=1.5))
    assert [(g.label, g.robots, g.attached) for g in groups] == [
        ("A", ("robot_1", "robot_2", "robot_5"), ("robot_5",)),
        ("B", ("robot_3", "robot_4"), ()),
    ]


def test_observed_groups_moving_robot_does_not_bridge_groups():
    frame = _frame(
        ("robot_1", 0.0, 0.0, "STOPPED"),
        ("robot_2", 1.0, 0.0, "STOPPED"),
        ("robot_3", 2.0, 0.0, "MOVING"),
        ("robot_4", 3.0, 0.0, "STOPPED"),
        ("robot_5", 4.0, 0.0, "STOPPED"),
    )
    groups = observed_groups(frame, GroupingParams(threshold_m=1.0))
    assert [g.robots for g in groups] == [("robot_1", "robot_2", "robot_3"), ("robot_4", "robot_5")]


def test_observed_groups_boundary_distance_links():
    frame = _frame(("robot_1", 0.0, 0.0, "STALE"), ("robot_2", 1.5, 0.0, "STOPPED"))
    (group,) = observed_groups(frame, GroupingParams(threshold_m=1.5))
    assert group.robots == ("robot_1", "robot_2")


def test_observed_groups_ignore_moving_only_scene():
    frame = _frame(("robot_1", 0.0, 0.0, "MOVING"), ("robot_2", 0.5, 0.0, "MOVING"))
    assert observed_groups(frame, GroupingParams(threshold_m=1.5)) == ()


def test_generate_cluster_candidates_lists_groups_in_label_order():
    candidates = generate_cluster_candidates(
        _two_groups(), "req-1", GroupingParams(threshold_m=1.5), _as_asked
    )
    sections = [o.section for o in candidates.options]
    assert sections == sorted(sections)
    assert set(sections) == {"A", "B"}
    assert candidates.options[0].scope == "group"
    assert candidates.options[0].strategy == "yield"
    assert candidates.item_id == "req-1"
    assert candidates.threshold_m == 1.5


def test_generate_cluster_candidates_keeps_span_and_outside_on_request():
    candidates = generate_cluster_candidates(
        _two_groups(), "req-1", GroupingParams(threshold_m=1.5), _as_asked,
        offgroup="keep", cross_group="keep",
    )
    assert SPAN in candidates.section_counts()


def test_generate_cluster_candidates_dedupes_on_executed_key():
    options = generate_cluster_candidates(
        _two_groups(), "req-1", GroupingParams(threshold_m=1.5), _as_asked, True, "keep", "keep"
    ).options
    assert len({o.key for o in options}) == len(options)


def test_generate_cluster_candidates_drops_probes_that_raise():
    def refuse(_decision: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("grounder refused")

    candidates = generate_cluster_candidates(
        _two_groups(), "req-1", GroupingParams(threshold_m=1.5), refuse
    )
    assert candidates.options == ()
    assert [g.label for g in candidates.groups] == ["A", "B"]


def test_generate_cluster_candidates_falls_back_to_outside_without_groups():
    frame = _frame(("robot_1", 0.0, 0.0, "MOVING"), ("robot_2", 0.5, 0.0, "MOVING"))
    candidates = generate_cluster_candidates(
        frame, "req-1", GroupingParams(threshold_m=1.5), _as_asked
    )
    assert {o.section for o in candidates.options} == {OUTSIDE}


def test_executed_key_none_for_refused_yield():
    command = {
        "actions": [
            {"action": "temporary_wait", "robot_id": "robot_1",
             "parameters": {"reason": "yield refused: no shared lane"}},
        ]
    }
    assert executed_key("yield", command) is None


def test_executed_key_none_for_empty_reroute_fallback():
    command = {
        "actions": [
            {"action": "reroute", "robot_id": "robot_1", "parameters": {"waypoints": []}},
            {"action": "temporary_wait", "robot_id": "robot_2", "parameters": {}},
        ],
        "degradations": ["retreat=no-valid-candidate"],
    }
    assert executed_key("yield", command) is None


def test_executed_key_v2_appends_unlinked_holds():
    command = {
        "actions": [
            {"action": "yield", "robot_id": "robot_3",
             "parameters": {"crossing_order": ["robot_4"]}},
            {"action": "temporary_wait", "robot_id": "robot_4",
             "parameters": {"linked_position": 0}},
            {"action": "temporary_wait", "robot_id": "robot_5", "parameters": {}},
        ],
    }
    assert executed_key_v2("yield", command) == ("yield", "robot_3", "robot_4", "hold", "robot_5")


def _inputs(**changes: Any) -> ProbeInputs:
    fields: dict[str, Any] = {
        "request_id": "req-1",
        "backend_id": "test",
        "snapshot": _two_groups(),
        "priorities": {"robot_1": 2},
        "goal_references": {"robot_1": (1.0, 2.0)},
        "task_intents": {"robot_1": RobotTaskIntent(goal=(1.0, 2.0))},
    }
    fields.update(changes)
    return ProbeInputs(**fields)


def _captured_kwargs(monkeypatch, inputs: ProbeInputs) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def fake(result, **kwargs):
        seen.update(kwargs, request_id=result.request_id)
        return {"actions": []}

    monkeypatch.setattr(cluster_options, "ground_reasoner_result", fake)
    decision = {
        "congestion_detected": True, "type": "deadlock", "involved_robots": ["robot_1"],
        "root_cause": "x", "strategy": "temporary_wait", "justification": "x",
    }
    ground_probe(inputs, decision)
    return seen


def test_ground_probe_passes_snapshot_and_priorities(monkeypatch):
    seen = _captured_kwargs(monkeypatch, _inputs())
    assert seen["request_id"] == "req-1"
    assert seen["priorities"] == {"robot_1": 2}
    assert set(seen["robot_positions"]) == {f"robot_{i}" for i in range(1, 6)}
    assert "goal_references" not in seen
    assert "task_intents" not in seen


def test_ground_probe_omits_empty_priorities(monkeypatch):
    assert "priorities" not in _captured_kwargs(monkeypatch, _inputs(priorities={}))


def test_ground_probe_passes_goal_references_only_with_dynamic_arms(monkeypatch):
    params = M3Params(dynamic_scene_arms=True)
    seen = _captured_kwargs(monkeypatch, _inputs(params=params))
    assert seen["goal_references"] == {"robot_1": (1.0, 2.0)}
    assert "task_intents" not in seen


def test_ground_probe_passes_task_intents_with_retreat_shield(monkeypatch):
    params = M3Params(dynamic_scene_arms=True, retreat_shield=True)
    seen = _captured_kwargs(monkeypatch, _inputs(params=params))
    assert set(seen["task_intents"]) == {"robot_1"}


def test_probe_inputs_fields_hold_no_ground_truth():
    assert set(ProbeInputs.model_fields) == _PROBE_FIELDS


def test_probe_inputs_refuse_a_ground_truth_field():
    with pytest.raises(ValidationError):
        _inputs(gt={"clusters": []})


@pytest.mark.parametrize(
    "function", [observed_groups, generate_cluster_candidates, ground_probe, joint_check]
)
def test_shared_entry_points_take_no_bench_item(function):
    names = set(inspect.signature(function).parameters)
    assert not names & {"item", "gt", "ground_truth"}
    hints = typing.get_type_hints(function)
    rendered = [repr(hint) for hint in hints.values()]
    assert not [h for h in rendered if "benchmarks" in h or "BenchItem" in h]


def _yield_option(label: str, yielder: str, passer: str) -> ClusterOption:
    return ClusterOption(
        strategy="yield", robots=(yielder, passer), yield_robot=yielder,
        key=("yield", yielder, passer), separation_m=1.0, text="x", section=label,
        scope="pair", base_key=("yield", yielder, passer),
    )


def test_joint_check_flags_retreat_clash_and_uses_default_radius():
    chosen = {
        "A": _yield_option("A", "robot_1", "robot_2"),
        "B": _yield_option("B", "robot_3", "robot_4"),
    }
    check = joint_check(_two_groups(), chosen, _as_asked, None)
    # The fake M3 parks every yielder at (0, 1): an exact retreat clash.
    assert check.retreat_clashes == (("A", "B"),)
    assert check.exact_conflict
    assert check.safety_radius_m == DEFAULT_SAFETY_RADIUS_M
    assert check.n_commands == 2


def test_joint_check_flags_shared_robot():
    chosen = {
        "A": _yield_option("A", "robot_1", "robot_2"),
        "B": _yield_option("B", "robot_3", "robot_2"),
    }
    assert joint_check(_two_groups(), chosen, _as_asked, None).shared_robots == ("robot_2",)


def test_joint_check_skips_none_feasible_slots():
    chosen = {"A": _yield_option("A", "robot_1", "robot_2"), "B": None}
    check = joint_check(_two_groups(), chosen, _as_asked, None)
    assert check.n_commands == 1
    assert not check.exact_conflict
    assert check.path_proximity == ()
