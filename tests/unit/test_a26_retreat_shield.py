"""prereg-v3 A26: the retreat shield (B1 + M5 intent) and the B3 fresh-latch fast-fail.

Fixtures: the 9 live S1b yields of the A25 no-admit diagnosis
(`data/a25_no_admit/yields.json`) plus M5's task intent at each decision
(`data/a26_retreat_shield/intents.json`, reconstructed from each bundle's
`tasks_*.jsonl`: current task node, next node, dwell left).

Required outcomes (A26(i)): the mechanism-B blockers are shielded -- E10 r3
and E13 r2 on their current leg, E14 r2 and E17b r2 only through the intent
read (the leg after they arrive, dwell and depart); E16, a yield that
COMPLETED, shields nobody: its r3 crosses the corridor but stands latched
with r2 (0.413 m, frozen 105-200 sim-s in GT), so it cannot move.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_execution import nav2_adapter
from swarm_execution.fresh_latch import FRESH_LATCH_DETAIL_PREFIX, FreshLatchWatch
from swarm_execution.nav2_adapter import Nav2Adapter
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline, load_grounding_source
from swarm_orchestrator.task_stream import TaskStreamTracker, build_task_stream_plan

from reasoning.rag.command_grounder import (
    degradation_cause,
    ground_reasoner_result,
    project_dispatched_legs,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import (
    FAST_FAIL_KEY,
    SHIELD_TAG,
    RobotTaskIntent,
    apply_fresh_latch_fast_fail,
    nominal_motion_sec,
    segment_distance,
    shield_verdicts,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerRequest,
    RetreatChoiceDecision,
    RobotStateInput,
)
from tests.unit.test_a25_backup_axis import CASES, _yield
from tests.unit.test_m5_task_stream import ROBOTS, _stream
from tests.unit.test_nav2_adapter import _FakeNode, _odom_at
from tests.unit.test_s1_resolvability import _floor, _frame, _reasoner_result

REPO_ROOT = Path(__file__).resolve().parents[2]
INTENTS = json.loads(
    (Path(__file__).parent / "data/a26_retreat_shield/intents.json").read_text(encoding="utf-8")
)["cases"]
SHIELD_FILE = REPO_ROOT / "config/grounding/s1b_dynamic_shield.yaml"
S1B_FILE = REPO_ROOT / "config/grounding/s1b_dynamic.yaml"
_SHIELD_KEYS = {"retreat_shield": True, "retreat_shield_margin_m": 0.05, "retreat_fast_fail": True}

# The registered outcome per case (shielded robot ids), frozen on the
# shipped margin 0.05. Necessary: E10 r3, E13 r2, E14 r2, E17b r2. The rest
# are scored necessary/over-hold in the A26 report against live GT.
EXPECTED_SHIELD = {
    "E6": {"robot_3"},
    "E10": {"robot_3"},
    "E11": {"robot_1", "robot_2"},
    "E13": {"robot_2"},
    "E14": {"robot_2", "robot_3"},
    "E15": {"robot_3"},
    "E16": set(),
    "E17a": set(),
    "E17b": {"robot_2", "robot_5"},
}
B_BLOCKERS = {"E10": "robot_3", "E13": "robot_2", "E14": "robot_2", "E17b": "robot_2"}


def _intents(name: str) -> dict[str, RobotTaskIntent]:
    return {
        rid: RobotTaskIntent(
            goal=tuple(v["goal"]),
            next_goal=None if v["next_goal"] is None else tuple(v["next_goal"]),
            dwell_sec=v["dwell_sec"],
        )
        for rid, v in INTENTS[name]["robots"].items()
        if v is not None
    }


def _ground(
    case: dict[str, Any],
    *,
    intents: dict[str, RobotTaskIntent] | None = None,
    rows: list[dict[str, Any]] | None = None,
    **updates: Any,
) -> dict[str, Any]:
    config, params = _floor("s1b")
    if updates:
        params = params.model_copy(update=updates)
    frame = _frame(rows or case["rows"])
    choice = (
        None
        if case["retreat_choice"] is None
        else RetreatChoiceDecision(retreat_choice=case["retreat_choice"], justification="live")
    )
    kwargs: dict[str, Any] = {} if intents is None else {"task_intents": intents}
    return ground_reasoner_result(
        _reasoner_result(CongestionDecision.model_validate(case["decision"])),
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        snapshot=frame,
        params=params,
        retreat_choice=choice,
        **kwargs,
    )


def _shielded(command: dict[str, Any]) -> set[str]:
    return {
        tag.split(":", 1)[1]
        for tag in command.get("degradations", [])
        if tag.startswith(f"{SHIELD_TAG}:")
    }


# ---- fixtures ----


def test_intent_fixture_covers_every_yield_case():
    assert set(INTENTS) == set(CASES)
    for name, case in CASES.items():
        assert INTENTS[name]["stamp"] == case["rows"][0]["stamp"]
        # The registry goal M5 rendered equals the intent's current node for
        # every robot (no override was active on a bystander).
        for row in case["rows"]:
            assert tuple(INTENTS[name]["robots"][row["robot_id"]]["goal"]) == tuple(row["goal"])


def test_no_blocker_was_dwelling_at_its_decision():
    # The "dwelling blockers" of E14/E17b were still TRAVELING to the node
    # they would dwell at; the leg that hits the retreat starts after it.
    for name in ("E14", "E17b"):
        assert INTENTS[name]["robots"][B_BLOCKERS[name]]["phase"] == "traveling"


# ---- default off: byte-identical ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_shield_off_grounds_the_pre_a26_command(name):
    case = CASES[name]
    baseline = _ground(case)
    assert _ground(case, intents=_intents(name)) == baseline
    assert _shielded(baseline) == set()
    assert FAST_FAIL_KEY not in _yield(baseline)["parameters"]


def test_params_dump_omits_the_switches_when_off():
    _config, params = _floor("s1b")
    dumped = params.model_dump(mode="json")
    for key in _SHIELD_KEYS:
        assert key not in dumped


def test_params_dump_carries_the_switches_when_on():
    _config, params = _floor("s1b")
    dumped = params.model_copy(update=_SHIELD_KEYS).model_dump(mode="json")
    for key, value in _SHIELD_KEYS.items():
        assert dumped[key] == value


def test_switches_need_dynamic_arms_in_the_dump():
    dumped = GroundingParams(mode="derived", **_SHIELD_KEYS).model_dump(mode="json")
    for key in _SHIELD_KEYS:
        assert key not in dumped


def test_shield_file_is_the_pinned_s1b_file_plus_three_keys():
    shield = yaml.safe_load(SHIELD_FILE.read_text())["grounding"]
    pinned = yaml.safe_load(S1B_FILE.read_text())["grounding"]
    assert {k: v for k, v in shield.items() if k not in _SHIELD_KEYS} == pinned
    assert {k: shield[k] for k in _SHIELD_KEYS} == _SHIELD_KEYS
    params = load_grounding_source(SHIELD_FILE).params
    assert params.retreat_shield and params.retreat_fast_fail
    defaults = {k: GroundingParams.model_fields[k].default for k in _SHIELD_KEYS}
    assert params.model_copy(update=defaults) == load_grounding_source(S1B_FILE).params


# ---- the registered fixture outcomes ----


@pytest.mark.parametrize("name", sorted(CASES))
def test_shield_on_holds_the_registered_robots(name):
    command = _ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS)
    assert _shielded(command) == EXPECTED_SHIELD[name]


@pytest.mark.parametrize("name", sorted(B_BLOCKERS))
def test_every_mechanism_b_blocker_is_shielded(name):
    command = _ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS)
    assert B_BLOCKERS[name] in _shielded(command)


@pytest.mark.parametrize("name", ["E14", "E17b"])
def test_blocker_is_shielded_only_through_the_intent_read(name):
    # Without M5's intent the blocker is scored on its snapshot goal alone,
    # whose leg never comes near the retreat.
    command = _ground(CASES[name], **_SHIELD_KEYS)
    assert B_BLOCKERS[name] not in _shielded(command)
    verdict = _verdict(name, B_BLOCKERS[name])
    assert verdict.shielded and verdict.next_leg


@pytest.mark.parametrize("name", ["E10", "E13"])
def test_current_leg_blockers_need_no_intent(name):
    command = _ground(CASES[name], **_SHIELD_KEYS)
    assert B_BLOCKERS[name] in _shielded(command)


def _verdict(name: str, robot_id: str):
    case = CASES[name]
    command = _ground(case, intents=_intents(name), **_SHIELD_KEYS)
    members = {a["robot_id"] for a in command["actions"]} - _shielded(command)
    verdicts = shield_verdicts(
        _frame(case["rows"]), _yield(command), members, 0.45, 0.05, _intents(name)
    )
    return next(v for v in verdicts if v.robot_id == robot_id)


def test_e16_r3_crosses_the_corridor_but_is_pinned():
    verdict = _verdict("E16", "robot_3")
    assert verdict.distance_m == 0.0
    assert verdict.pinned_with == ("robot_2",)
    assert not verdict.shielded


def test_e16_r3_would_be_shielded_if_it_were_free_to_move():
    # The pin is the discriminating condition: the same scene with r2 MOVING
    # (so the r2-r3 pair is no standing latch) shields r3.
    case = CASES["E16"]
    rows = [{**r, "status": "MOVING"} if r["robot_id"] == "robot_2" else r for r in case["rows"]]
    command = _ground(case, intents=_intents("E16"), rows=rows, **_SHIELD_KEYS)
    assert "robot_3" in _shielded(command)


def test_e16_r5_stays_outside_the_margin():
    verdict = _verdict("E16", "robot_5")
    assert 0.5 < verdict.distance_m < 0.6
    assert not verdict.shielded


def test_e17b_r2_sits_inside_the_margin():
    verdict = _verdict("E17b", "robot_2")
    assert 0.45 > verdict.distance_m > 0.4


# ---- the shield's command shape (lane-scope precedent) ----


@pytest.mark.parametrize("name", sorted(B_BLOCKERS))
def test_shield_leaves_the_yield_and_its_passers_unchanged(name):
    case = CASES[name]
    base = _ground(case)
    shielded = _ground(case, intents=_intents(name), **_SHIELD_KEYS)
    base_yield = _yield(base)["parameters"]
    new_yield = {k: v for k, v in _yield(shielded)["parameters"].items() if k != FAST_FAIL_KEY}
    assert new_yield == base_yield
    assert shielded["actions"][: len(base["actions"])][1:] == base["actions"][1:]
    # Shielded robots are never passers.
    assert not _shielded(shielded) & set(base_yield["crossing_order"])
    assert base_yield["passer_robot_id"] not in _shielded(shielded)


@pytest.mark.parametrize("name", sorted(B_BLOCKERS))
def test_shield_wait_is_unlinked_and_uses_the_yield_wait_budget(name):
    case = CASES[name]
    command = _ground(case, intents=_intents(name), **_SHIELD_KEYS)
    passer_waits = [
        a for a in command["actions"]
        if a["action"] == "temporary_wait" and "linked_position" in a["parameters"]
    ]
    holds = [a for a in command["actions"] if a["robot_id"] in _shielded(command)]
    assert holds and passer_waits
    for hold in holds:
        assert hold["action"] == "temporary_wait"
        assert "linked_position" not in hold["parameters"]
        assert hold["parameters"]["duration_sec"] == passer_waits[0]["parameters"]["duration_sec"]
        assert hold["parameters"]["requested_strategy"] == "yield"
        assert hold["parameters"]["reason"].startswith("retreat shield:")


def test_shield_wait_projects_as_a_wait_leg():
    command = _ground(CASES["E10"], intents=_intents("E10"), **_SHIELD_KEYS)
    legs = project_dispatched_legs(command, [f"robot_{i}" for i in range(1, 6)])
    assert legs["robot_3"] == "wait"
    assert legs["robot_5"] == "cross"


def test_shield_tag_is_a_provenance_marker():
    assert degradation_cause(f"{SHIELD_TAG}:robot_3") is None


def test_shield_needs_the_dynamic_switch():
    command = _ground(
        CASES["E10"], intents=_intents("E10"), dynamic_scene_arms=False, **_SHIELD_KEYS
    )
    assert _shielded(command) == set()


# ---- geometry helpers ----


def test_segment_distance_crossing_and_parallel():
    assert segment_distance((0, 0), (2, 0), (1, -1), (1, 1)) == 0.0
    assert segment_distance((0, 0), (2, 0), (0, 0.5), (2, 0.5)) == pytest.approx(0.5)


def test_nominal_motion_time_matches_m4_naive_formulas():
    assert nominal_motion_sec(1.4, 0.0) == pytest.approx(14.0)
    assert nominal_motion_sec(1.4, 0.72) == pytest.approx(14.0 + math.pi / 0.5 + 7.2)


def test_next_leg_read_only_when_departure_fits_the_motion_time():
    frame = _frame(
        [
            {"robot_id": "robot_1", "x": 0.0, "y": 0.0, "theta": 0.0, "status": "STOPPED",
             "goal": [5.0, 0.0]},
            {"robot_id": "robot_2", "x": 3.0, "y": 2.0, "theta": 0.0, "status": "MOVING",
             "goal": [3.0, 1.0]},
        ]
    )
    action = {
        "robot_id": "robot_1",
        "action": "yield",
        "parameters": {"backup_distance_m": 1.0, "retreat_x_m": -1.0, "retreat_y_m": 0.0},
    }
    # The current leg (3,2) -> (3,1) is far from the corridor (x in [-1, 0],
    # y = 0); only the next leg (3,1) -> (-0.5,0.3) comes near it.
    near = RobotTaskIntent(goal=(3.0, 1.0), next_goal=(-0.5, 0.3), dwell_sec=5.0)
    (verdict,) = shield_verdicts(frame, action, {"robot_1"}, 0.45, 0.05, {"robot_2": near})
    # 1 m at 0.2 m/s + 5 s dwell = 10 s <= the 10 s backup: next leg read.
    assert verdict.next_leg and verdict.shielded
    far = near.model_copy(update={"dwell_sec": 5.5})
    (verdict,) = shield_verdicts(frame, action, {"robot_1"}, 0.45, 0.05, {"robot_2": far})
    assert not verdict.next_leg and not verdict.shielded


# ---- B3 key (M3 side) ----


def test_fast_fail_key_on_yield_with_the_switch():
    command = _ground(CASES["E10"], intents=_intents("E10"), **_SHIELD_KEYS)
    assert _yield(command)["parameters"][FAST_FAIL_KEY] is True
    waits = [a for a in command["actions"] if a["action"] == "temporary_wait"]
    assert all(FAST_FAIL_KEY not in a["parameters"] for a in waits)


def test_fast_fail_key_marks_reverse_actions():
    params = GroundingParams(mode="derived", dynamic_scene_arms=True, retreat_fast_fail=True)
    command = {
        "command_id": "c",
        "actions": [
            {"robot_id": "robot_1", "action": "reverse", "parameters": {"backup_distance_m": 0.5}},
            {"robot_id": "robot_2", "action": "temporary_wait", "parameters": {}},
        ],
    }
    marked = apply_fresh_latch_fast_fail(command, params)
    assert marked["actions"][0]["parameters"][FAST_FAIL_KEY] is True
    assert FAST_FAIL_KEY not in marked["actions"][1]["parameters"]
    assert apply_fresh_latch_fast_fail(command, params.model_copy(
        update={"retreat_fast_fail": False})) is command


# ---- M5: the intent channel ----


def _stream_tracker() -> tuple[TaskStreamTracker, Any]:
    plan = build_task_stream_plan(_stream(), ROBOTS)
    tracker = TaskStreamTracker(plan, 5.0)
    tracker.start(0.0, ROBOTS)
    return tracker, plan


def test_departure_while_traveling_is_the_next_node_after_a_full_dwell():
    tracker, plan = _stream_tracker()
    assert tracker.departure("robot_1", 1.0) == (plan.tasks["robot_1"][1].goal, 5.0)


def test_departure_while_dwelling_counts_the_dwell_left():
    tracker, plan = _stream_tracker()
    task = tracker.current_task("robot_1")
    tracker.on_scene(10.0, 10.0)
    tracker.on_arrival("robot_1", task.goal, 10.0, 10.0)
    assert tracker.departure("robot_1", 12.0) == (plan.tasks["robot_1"][1].goal, 3.0)


def test_departure_is_none_for_held_and_unknown_robots():
    plan = build_task_stream_plan(_stream(), ROBOTS)
    tracker = TaskStreamTracker(plan, 5.0)
    assert tracker.departure("robot_1", 1.0) is None
    assert tracker.departure("robot_9", 1.0) is None


def _request(name: str) -> ReasonerRequest:
    rows = CASES[name]["rows"]
    return ReasonerRequest(
        request_id="r1",
        image_path="/tmp/r1.png",
        frame_id="cam0",
        stamp=rows[0]["stamp"],
        robot_states=[RobotStateInput.model_validate(r) for r in rows],
    )


class _FakeReasoner:
    def __init__(self, decision: CongestionDecision) -> None:
        self._decision = decision

    def run(self, request):
        return _reasoner_result(self._decision)


def _pipeline(name: str, params: GroundingParams, seen: dict[str, Any]) -> InProcessPipeline:
    config, _ = _floor("s1b")

    def ground(result, **kwargs):
        seen.update(kwargs)
        return ground_reasoner_result(result, **kwargs)

    intents = _intents(name)
    return InProcessPipeline(
        reasoner=_FakeReasoner(CongestionDecision.model_validate(CASES[name]["decision"])),
        ground_fn=ground,
        scene_geometry=config.scenario_geometry,
        static_obstacles=config.static_obstacles,
        yield_feasibility_mode=config.grounding_yield_feasibility,
        grounding_params=params,
        stage2_enabled=False,
        task_intent_of=intents.get,
    )


def test_pipeline_feeds_task_intents_with_the_shield_on():
    _config, params = _floor("s1b")
    seen: dict[str, Any] = {}
    outcome = _pipeline("E14", params.model_copy(update=_SHIELD_KEYS), seen).run(_request("E14"))
    assert seen["task_intents"] == _intents("E14")
    assert "robot_2" in _shielded(outcome.grounded_command)


def test_pipeline_passes_no_task_intents_with_the_shield_off():
    _config, params = _floor("s1b")
    seen: dict[str, Any] = {}
    outcome = _pipeline("E14", params, seen).run(_request("E14"))
    assert "task_intents" not in seen
    assert _shielded(outcome.grounded_command) == set()


# ---- M4: B3 fresh-latch fast-fail ----


def test_watch_ignores_an_unarmed_robot():
    watch = FreshLatchWatch()
    watch.on_holds({"robot_1"}, 0.0)
    assert watch.check("robot_1", 10.0, "backup") is None


def test_watch_ignores_a_hold_standing_at_arm_time():
    watch = FreshLatchWatch()
    watch.on_holds({"robot_1"}, 0.0)
    watch.arm("robot_1", "c1", 1.0)
    assert watch.check("robot_1", 10.0, "backup") is None


def test_watch_fires_after_the_debounce_on_a_fresh_latch():
    watch = FreshLatchWatch(debounce_sec=2.0)
    watch.arm("robot_1", "c1", 0.0)
    watch.on_holds({"robot_1", "robot_3"}, 11.0)
    assert watch.check("robot_1", 12.5, "backup") is None
    detail = watch.check("robot_1", 13.0, "backup")
    assert detail is not None and detail.startswith(FRESH_LATCH_DETAIL_PREFIX)
    assert "during backup" in detail and "co_held=robot_3" in detail


def test_watch_resets_when_the_hold_releases():
    watch = FreshLatchWatch(debounce_sec=2.0)
    watch.arm("robot_1", "c1", 0.0)
    watch.on_holds({"robot_1"}, 5.0)
    watch.on_holds(set(), 6.0)
    watch.on_holds({"robot_1"}, 6.5)
    assert watch.check("robot_1", 8.0, "pull_off") is None
    assert watch.check("robot_1", 8.5, "pull_off") is not None


def test_watch_disarm_is_scoped_to_its_command():
    watch = FreshLatchWatch(debounce_sec=0.0)
    watch.arm("robot_1", "c2", 0.0)
    watch.disarm("robot_1", "c1")
    watch.on_holds({"robot_1"}, 1.0)
    assert watch.check("robot_1", 1.0, "backup") is not None
    watch.disarm("robot_1", "c2")
    assert watch.check("robot_1", 1.0, "backup") is None


def test_backup_fails_fast_when_the_abort_check_fires(monkeypatch):
    node = _FakeNode()
    adapter = Nav2Adapter(node)
    monkeypatch.setattr(nav2_adapter.time, "monotonic", lambda: 100.0)
    statuses: list[tuple[str, str]] = []
    verdict = {"detail": None}
    adapter.backup(
        "robot_1", 1.4, on_result=lambda s, d: statuses.append((s, d)),
        hold_start_line=True, abort_check=lambda: verdict["detail"],
    )
    odom_sub, timer = node.subscriptions[-1], node.timers[-1]
    odom_sub.callback(_odom_at(0.0, 0.0))
    timer.tick()
    assert statuses[-1][0] == "ACTIVE"
    odom_sub.callback(_odom_at(-0.5, 0.0))
    verdict["detail"] = "fresh latch fast-fail: robot_1 latched during backup"
    timer.tick()
    assert statuses[-1][0] == "FAILED"
    assert statuses[-1][1].startswith("fresh latch fast-fail")
    assert "moved=0.500m of 1.400m" in statuses[-1][1]
    assert timer.cancelled


def test_backup_without_abort_check_runs_to_completion():
    node = _FakeNode()
    adapter = Nav2Adapter(node)
    statuses: list[tuple[str, str]] = []
    adapter.backup("robot_1", 0.5, on_result=lambda s, d: statuses.append((s, d)))
    odom_sub, timer = node.subscriptions[-1], node.timers[-1]
    odom_sub.callback(_odom_at(0.0, 0.0))
    odom_sub.callback(_odom_at(-0.5, 0.0))
    timer.tick()
    assert statuses[-1][0] == "COMPLETED"


def test_sidestep_fails_fast_when_the_abort_check_fires():
    node = _FakeNode()
    adapter = Nav2Adapter(node)
    statuses: list[tuple[str, str]] = []
    adapter.sidestep(
        "robot_1", 0.36, on_result=lambda s, d: statuses.append((s, d)),
        abort_check=lambda: "fresh latch fast-fail: robot_1 latched during pull_off",
    )
    odom_sub, timer = node.subscriptions[-1], node.timers[-1]
    odom_sub.callback(_odom_at(0.0, 0.0, yaw=0.0))
    timer.tick()
    assert statuses[-1][0] == "FAILED"
    assert statuses[-1][1].endswith("phase=turn_out")


# ---- M4: command bus wiring ----


class _BusAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def backup(self, robot_id, distance_m, on_result=None, **kwargs):
        self.calls.append(("backup", kwargs))
        self.backup_on_result = on_result

    def sidestep(self, robot_id, lateral_m, on_result=None, **kwargs):
        self.calls.append(("sidestep", kwargs))
        self.sidestep_on_result = on_result


def _bus(adapter: _BusAdapter):
    from swarm_execution.command_bus_node import CommandBusNode

    from tests.unit.test_command_bus_node import _FixedClock, _NullLogger

    node = CommandBusNode.__new__(CommandBusNode)
    node._adapter = adapter
    node._nav_watchdogs = {}
    node._active_waits = {}
    statuses: list[tuple[str, str]] = []
    node._publish_status = lambda command, status, detail, **kw: statuses.append((status, detail))
    node.create_timer = lambda period, cb: object()
    node.destroy_timer = lambda t: None
    node.get_logger = lambda: _NullLogger()
    node.get_clock = lambda: _FixedClock()
    subscriptions: list[str] = []
    node.create_subscription = lambda msg_type, topic, cb, qos: subscriptions.append(topic)
    return node, statuses, subscriptions


def _yield_msg():
    from tests.unit.test_command_bus_node import _Msg

    return _Msg(command_id="c1", robot_id="robot_1", action="yield")


_YIELD_PARAMS = {
    "backup_distance_m": 1.3,
    "hold_sec": 45.0,
    "pull_off_lateral_m": 0.36,
    "backup_line_hold": True,
}


def test_bus_without_the_key_never_watches_holds():
    adapter = _BusAdapter()
    node, _statuses, subscriptions = _bus(adapter)
    node._dispatch(_yield_msg(), dict(_YIELD_PARAMS))
    adapter.backup_on_result("COMPLETED", "backup complete")
    assert subscriptions == []
    assert [kw for _name, kw in adapter.calls] == [{"hold_start_line": True}, {}]


def test_bus_with_the_key_passes_abort_checks_to_backup_and_pull_off(monkeypatch):
    from swarm_execution import command_bus_node

    now = {"t": 50.0}
    monkeypatch.setattr(command_bus_node.time, "monotonic", lambda: now["t"])
    adapter = _BusAdapter()
    node, _statuses, subscriptions = _bus(adapter)
    node._dispatch(_yield_msg(), {**_YIELD_PARAMS, "fresh_latch_fast_fail": True})
    assert subscriptions == ["/safety/holds"]
    backup_check = adapter.calls[0][1]["abort_check"]
    assert backup_check() is None
    node._on_safety_holds(type("M", (), {"data": json.dumps({"held": ["robot_1", "robot_3"]})}))
    now["t"] = 52.5
    detail = backup_check()
    assert detail.startswith(FRESH_LATCH_DETAIL_PREFIX) and "co_held=robot_3" in detail
    # A second flagged command reuses the one subscription.
    node._dispatch(
        type(_yield_msg())(command_id="c2", robot_id="robot_2", action="reverse"),
        {"backup_distance_m": 0.5, "fresh_latch_fast_fail": True},
    )
    assert subscriptions == ["/safety/holds"]


def test_bus_disarms_the_watch_at_hold_start(monkeypatch):
    from swarm_execution import command_bus_node

    monkeypatch.setattr(command_bus_node.time, "monotonic", lambda: 10.0)
    adapter = _BusAdapter()
    node, statuses, _subs = _bus(adapter)
    node._dispatch(_yield_msg(), {**_YIELD_PARAMS, "fresh_latch_fast_fail": True})
    adapter.backup_on_result("COMPLETED", "backup complete")
    pull_off_check = adapter.calls[1][1]["abort_check"]
    adapter.sidestep_on_result("COMPLETED", "side step complete")
    assert ("ACTIVE", "holding for passing robot") in statuses
    node._on_safety_holds(type("M", (), {"data": json.dumps({"held": ["robot_1"]})}))
    node._fresh_latch.on_holds({"robot_1"}, 0.0)
    assert pull_off_check() is None
