"""prereg-v3 A27: the retreat-shield safety fix, the S1 shield floor and the B3 log line.

A27(i): a robot a yield command addresses ONLY as a retreat-shield hold is not
a clearing agent, so M4 never exempts its pair with the yielder. A too-close
approach latches at `min_distance_m` and the B3 fast-fail ends the yield.
Clearing partners (passers) keep the exemption, and the M3 predicate (pin rule,
intent legs) is unchanged.

Fixtures:

- the 9 A25 yields (`data/a25_no_admit/yields.json`), whose 10 shield holds
  are grounded through the A26 path (`test_a26_retreat_shield._ground`);
- the E18 near-pass (`data/a27_shield_fix/e18_near_pass.json`): batch 3's
  dispatched command `56b599af` (yielder robot_2, shielded robot_1 among
  others) and the M1 scene states from its backup start to its hold start,
  extracted from the bundle's `m5_scene.jsonl`. Live, the exempt pair passed
  at 0.23 m centre distance.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_execution import safety
from swarm_execution.fresh_latch import (
    FAST_FAIL_LOG_EVENT,
    FRESH_LATCH_DETAIL_PREFIX,
    FreshLatchWatch,
    fast_fail_log_line,
)
from swarm_execution.nav2_adapter import backup_deadline_sec, sidestep_deadline_sec
from swarm_execution.safety import (
    SHIELD_HOLD_KEY,
    CoordinationTracker,
    SafetyLimits,
    admitted_partners,
    evaluate_latches,
    is_shield_hold,
)
from swarm_execution.yield_phase import BACKUP_STARTED_DETAIL, PULL_OFF_DETAIL

from reasoning.rag import retreat_shield
from tests.unit.test_a25_backup_axis import CASES
from tests.unit.test_a26_retreat_shield import (
    _SHIELD_KEYS,
    _YIELD_PARAMS,
    B_BLOCKERS,
    EXPECTED_SHIELD,
    _bus,
    _BusAdapter,
    _ground,
    _intents,
    _shielded,
    _yield_msg,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
E18 = json.loads(
    (Path(__file__).parent / "data/a27_shield_fix/e18_near_pass.json").read_text(encoding="utf-8")
)
SAFETY_FILE = REPO_ROOT / "ros2_ws/src/swarm_execution/config/safety.yaml"
FLOOR_FILE = REPO_ROOT / "config/safety/safety_floor020.yaml"
LIMITS = SafetyLimits(min_distance_m=0.45, max_linear_velocity_mps=0.2)
FLOOR_LIMITS = SafetyLimits(
    min_distance_m=0.45, max_linear_velocity_mps=0.2, hard_contact_floor_m=0.20
)


def _record(tracker: CoordinationTracker, command: dict[str, Any]) -> None:
    for action in command["actions"]:
        tracker.record_command(
            command["command_id"], action["robot_id"], action["action"], action.get("parameters")
        )


def _backing_up(tracker: CoordinationTracker, command_id: str, yielder: str) -> None:
    tracker.record_status(command_id, yielder, "ACTIVE", BACKUP_STARTED_DETAIL)


def _with_command_id(command: dict[str, Any], command_id: str = "c1") -> dict[str, Any]:
    return {**command, "command_id": command_id}


def _yielder(command: dict[str, Any]) -> str:
    return next(a["robot_id"] for a in command["actions"] if a["action"] == "yield")


def _passers(command: dict[str, Any]) -> set[str]:
    params = next(a for a in command["actions"] if a["action"] == "yield")["parameters"]
    return set(params.get("crossing_order") or [params.get("passer_robot_id")]) - {None}


# ---- the key: M3 marks every shield hold, M4 reads the same literal ----


def test_m3_and_m4_share_the_shield_hold_key():
    assert retreat_shield.SHIELD_HOLD_KEY == SHIELD_HOLD_KEY == "retreat_shield_hold"


@pytest.mark.parametrize("name", sorted(CASES))
def test_every_shield_hold_carries_the_m4_key(name):
    command = _ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS)
    for action in command["actions"]:
        marked = (action.get("parameters") or {}).get(SHIELD_HOLD_KEY) is True
        assert marked == (action["robot_id"] in _shielded(command))


@pytest.mark.parametrize("name", sorted(CASES))
def test_shield_predicate_outcomes_are_unchanged(name):
    # PIN RULE and intent legs untouched: the A26 registered outcomes stand.
    command = _ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS)
    assert _shielded(command) == EXPECTED_SHIELD[name]


def test_required_shield_fixtures_still_hold():
    for name, blocker in B_BLOCKERS.items():
        assert blocker in _shielded(_ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS))
    assert _shielded(_ground(CASES["E16"], intents=_intents("E16"), **_SHIELD_KEYS)) == set()


def test_shield_off_commands_carry_no_hold_key():
    for name in CASES:
        for action in _ground(CASES[name])["actions"]:
            assert SHIELD_HOLD_KEY not in (action.get("parameters") or {})


# ---- M4 pure rule ----


def test_is_shield_hold_needs_a_temporary_wait_with_the_key_true():
    assert is_shield_hold("temporary_wait", {SHIELD_HOLD_KEY: True})
    assert not is_shield_hold("temporary_wait", {SHIELD_HOLD_KEY: "true"})
    assert not is_shield_hold("temporary_wait", {"requested_strategy": "yield"})
    assert not is_shield_hold("temporary_wait", None)
    assert not is_shield_hold("yield", {SHIELD_HOLD_KEY: True})


def test_admitted_partners_drops_shield_holds_while_backing_up():
    partners = admitted_partners(
        "robot_1", "yield", ["robot_1", "robot_2", "robot_3"], ("robot_2",), set(),
        backing_up=True, shield_holds=frozenset({"robot_3"}),
    )
    assert partners == frozenset({"robot_2"})


def test_admitted_partners_drops_shield_holds_without_a_passer_order():
    partners = admitted_partners(
        "robot_1", "yield", ["robot_1", "robot_2", "robot_3"], None, set(),
        shield_holds=frozenset({"robot_3"}),
    )
    assert partners == frozenset({"robot_2"})


def test_admitted_partners_default_is_unchanged():
    members = ["robot_1", "robot_2", "robot_3"]
    assert admitted_partners(
        "robot_1", "yield", members, ("robot_2",), set(), backing_up=True
    ) == frozenset({"robot_2", "robot_3"})


# ---- the 9 A25 fixtures' 10 shield holds: shielded pairs latch, passers stay exempt ----


@pytest.mark.parametrize("name", sorted(n for n in CASES if EXPECTED_SHIELD[n]))
def test_shielded_pairs_are_not_exempt_while_the_yielder_backs_up(name):
    command = _with_command_id(_ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS))
    tracker = CoordinationTracker()
    _record(tracker, command)
    yielder = _yielder(command)
    _backing_up(tracker, "c1", yielder)
    exemption = tracker.exemption()
    for robot_id in _shielded(command):
        assert not exemption.covers_pair(yielder, robot_id)
    for passer in _passers(command):
        assert exemption.covers_pair(yielder, passer)


@pytest.mark.parametrize("name", sorted(n for n in CASES if EXPECTED_SHIELD[n]))
def test_shielded_robot_too_close_latches_the_yielder(name):
    command = _with_command_id(_ground(CASES[name], intents=_intents(name), **_SHIELD_KEYS))
    tracker = CoordinationTracker()
    _record(tracker, command)
    yielder = _yielder(command)
    _backing_up(tracker, "c1", yielder)
    shielded = sorted(_shielded(command))[0]
    robots = [
        {"robot_id": yielder, "x": 0.0, "y": 0.0},
        {"robot_id": shielded, "x": 0.30, "y": 0.0},
    ]
    evaluation = evaluate_latches(robots, LIMITS, exempt=tracker.exemption())
    assert evaluation.latched == frozenset({yielder, shielded})
    assert evaluation.reasons[yielder] == safety.REASON_MIN_DISTANCE


def test_pre_a27_hold_without_the_key_was_exempt():
    # The batch-3 runtime's command shape (no key): the pair WAS exempt.
    command = _with_command_id(_ground(CASES["E10"], intents=_intents("E10"), **_SHIELD_KEYS))
    stripped = {
        **command,
        "actions": [
            {**a, "parameters": {k: v for k, v in a["parameters"].items() if k != SHIELD_HOLD_KEY}}
            for a in command["actions"]
        ],
    }
    tracker = CoordinationTracker()
    _record(tracker, stripped)
    _backing_up(tracker, "c1", "robot_1")
    assert tracker.exemption().covers_pair("robot_1", "robot_3")


def test_lane_scoped_off_lane_hold_keeps_its_exemption():
    # A21's off-lane hold is a wait substituted for the yield (requested
    # strategy set) but carries no shield key: unchanged, still exempt.
    tracker = CoordinationTracker()
    tracker.record_command(
        "c1", "robot_1", "yield",
        {"backup_distance_m": 1.0, "hold_sec": 30.0, "passer_robot_id": "robot_2"},
    )
    tracker.record_command("c1", "robot_2", "temporary_wait", {"duration_sec": 30.0})
    tracker.record_command(
        "c1", "robot_4", "temporary_wait",
        {"duration_sec": 30.0, "requested_strategy": "yield", "reason": "lane-scoped hold"},
    )
    tracker.record_command(
        "c1", "robot_5", "temporary_wait",
        {"duration_sec": 30.0, "requested_strategy": "yield", SHIELD_HOLD_KEY: True},
    )
    _backing_up(tracker, "c1", "robot_1")
    exemption = tracker.exemption()
    assert exemption.covers_pair("robot_1", "robot_2")
    assert exemption.covers_pair("robot_1", "robot_4")
    assert not exemption.covers_pair("robot_1", "robot_5")


def test_shield_hold_standing_in_a_latch_at_start_is_waived_one_sided():
    # A shielded robot already latched with the yielder at command start is a
    # bystander under A19: the yielder may leave, the shielded robot is held.
    tracker = CoordinationTracker()
    tracker.record_command(
        "c1", "robot_1", "yield",
        {"backup_distance_m": 1.0, "hold_sec": 30.0, "passer_robot_id": "robot_2"},
    )
    tracker.record_command("c1", "robot_2", "temporary_wait", {"duration_sec": 30.0})
    tracker.record_command(
        "c1", "robot_3", "temporary_wait",
        {"duration_sec": 30.0, "requested_strategy": "yield", SHIELD_HOLD_KEY: True},
    )
    _backing_up(tracker, "c1", "robot_1")
    armed = tracker.capture_latch_partners(frozenset({("robot_1", "robot_3")}))
    assert armed == [("robot_1", "c1", ("robot_3",))]
    robots = [
        {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
        {"robot_id": "robot_3", "x": 0.40, "y": 0.0},
    ]
    evaluation = evaluate_latches(robots, LIMITS, exempt=tracker.exemption())
    assert evaluation.latched == frozenset({"robot_3"})


def test_shield_membership_is_evicted_with_the_command():
    tracker = CoordinationTracker()
    tracker.record_command("old", "robot_3", "temporary_wait", {SHIELD_HOLD_KEY: True})
    for i in range(CoordinationTracker.MAX_TRACKED_COMMANDS + 1):
        tracker.record_command(f"c{i}", "robot_1", "wait", None)
    assert "old" not in tracker._shield_by_command


# ---- the E18 near-pass: exempt then, latch -> B3 now ----


def _e18_command(with_key: bool) -> dict[str, Any]:
    prefix = "grounding=retreat_shield:"
    shielded = {t[len(prefix):] for t in E18["degradations"] if t.startswith(prefix)}
    actions = []
    for action in E18["actions"]:
        params = dict(action.get("parameters") or {})
        if with_key and action["robot_id"] in shielded:
            params[SHIELD_HOLD_KEY] = True
        actions.append({**action, "parameters": params})
    return {"command_id": E18["command_id"], "actions": actions}


def _replay_e18(
    with_key: bool, limits: SafetyLimits = LIMITS
) -> list[tuple[float, frozenset, dict]]:
    """Open-loop replay of the safety monitor over E18's live M1 scenes."""
    tracker = CoordinationTracker()
    _record(tracker, _e18_command(with_key))
    phases = E18["phase_start_sim"]
    previous: frozenset[str] = frozenset()
    memory = None
    out = []
    pull_off_seen = False
    for scene in E18["scenes"]:
        if scene["stamp"] < phases["backup"]:
            continue
        if scene["stamp"] >= phases["pull_off"] and not pull_off_seen:
            tracker.record_status(E18["command_id"], "robot_2", "ACTIVE", PULL_OFF_DETAIL)
            pull_off_seen = True
        else:
            tracker.record_status(E18["command_id"], "robot_2", "ACTIVE", BACKUP_STARTED_DETAIL)
        evaluation = evaluate_latches(
            scene["robots"], limits, previous, memory, exempt=tracker.exemption()
        )
        previous, memory = evaluation.latched, evaluation.last_fresh_distances
        out.append((scene["stamp"], evaluation.latched, evaluation.floor_breaches))
    return out


def _r1_r2(scene: dict[str, Any]) -> float:
    pos = {r["robot_id"]: (r["x"], r["y"]) for r in scene["robots"]}
    return math.dist(pos["robot_1"], pos["robot_2"])


def test_e18_fixture_reproduces_the_live_near_pass():
    window = [s for s in E18["scenes"] if E18["phase_start_sim"]["backup"] <= s["stamp"]]
    closest = min(window, key=_r1_r2)
    assert 0.22 < _r1_r2(closest) < 0.24
    assert E18["phase_start_sim"]["backup"] <= closest["stamp"] < E18["phase_start_sim"]["pull_off"]


def test_e18_pre_a27_runtime_never_latched_the_yielder():
    # Live (batch-3 runtime): the yielder-r1 pair was exempt and never held.
    assert all("robot_2" not in latched for _t, latched, _f in _replay_e18(with_key=False))


def test_e18_floor_alone_would_not_have_caught_the_pass():
    # 0.23 m is above the 0.20 m floor: the de-exemption is the operative fix,
    # the floor the backstop for pairs that stay exempt.
    replay = _replay_e18(with_key=False, limits=FLOOR_LIMITS)
    assert all(not breaches for _t, _l, breaches in replay)


def _first_latch(replay: list[tuple[float, frozenset, dict]]) -> float:
    return next(t for t, latched, _f in replay if {"robot_1", "robot_2"} <= latched)


def test_e18_now_latches_at_the_first_scene_inside_min_distance():
    replay = _replay_e18(with_key=True)
    first_close = next(
        s["stamp"] for s in E18["scenes"]
        if s["stamp"] >= E18["phase_start_sim"]["backup"] and _r1_r2(s) < 0.45
    )
    assert _first_latch(replay) == first_close
    assert first_close < E18["phase_start_sim"]["pull_off"]


def test_e18_latch_fires_b3_after_the_debounce():
    # Open loop: the scene stamps stand in for the bus's monotonic clock (the
    # live yielder would stop at the latch; only the instant and the firing
    # are asserted).
    replay = _replay_e18(with_key=True)
    watch = FreshLatchWatch()
    watch.arm("robot_2", E18["command_id"], E18["phase_start_sim"]["backup"])
    fired = None
    for stamp, latched, _f in replay:
        watch.on_holds(latched, stamp)
        detail = watch.check("robot_2", stamp, "backup")
        if detail is not None:
            fired = (stamp, detail)
            break
    assert fired is not None
    stamp, detail = fired
    assert stamp - _first_latch(replay) >= 2.0
    assert detail.startswith(f"{FRESH_LATCH_DETAIL_PREFIX}: robot_2 latched during backup")
    assert "robot_1" in detail.split("co_held=")[1]


# ---- the S1 shield cell's floor (A27(i)) ----


def test_floor_file_is_safety_yaml_with_only_the_floor_enabled():
    base = yaml.safe_load(SAFETY_FILE.read_text())["safety"]
    floor = yaml.safe_load(FLOOR_FILE.read_text())["safety"]
    assert base["hard_contact_floor_m"] == 0.0
    assert floor["hard_contact_floor_m"] == 0.20
    assert {k: v for k, v in floor.items() if k != "hard_contact_floor_m"} == {
        k: v for k, v in base.items() if k != "hard_contact_floor_m"
    }
    base_lines = SAFETY_FILE.read_text().splitlines()
    floor_lines = FLOOR_FILE.read_text().splitlines()
    assert len(base_lines) == len(floor_lines)
    assert [i for i, (a, b) in enumerate(zip(base_lines, floor_lines, strict=True)) if a != b] == [
        base_lines.index("  hard_contact_floor_m: 0.0")
    ]


def test_floor_file_loads_as_valid_limits():
    data = yaml.safe_load(FLOOR_FILE.read_text())["safety"]
    limits = SafetyLimits(
        min_distance_m=float(data["min_distance_m"]),
        max_linear_velocity_mps=float(data["max_linear_velocity_mps"]),
        hard_contact_floor_m=float(data["hard_contact_floor_m"]),
    )
    assert limits.hard_contact_floor_m == 0.20 < limits.min_distance_m


def test_floor_still_latches_an_exempt_passer_pair_in_contact():
    tracker = CoordinationTracker()
    tracker.record_command(
        "c1", "robot_1", "yield",
        {"backup_distance_m": 1.0, "hold_sec": 30.0, "passer_robot_id": "robot_2"},
    )
    tracker.record_command("c1", "robot_2", "temporary_wait", {"duration_sec": 30.0})
    _backing_up(tracker, "c1", "robot_1")
    robots = [
        {"robot_id": "robot_1", "x": 0.0, "y": 0.0},
        {"robot_id": "robot_2", "x": 0.15, "y": 0.0},
    ]
    evaluation = evaluate_latches(robots, FLOOR_LIMITS, exempt=tracker.exemption())
    assert evaluation.latched == frozenset({"robot_1", "robot_2"})
    assert evaluation.floor_breaches


# ---- A27(iii): the B3 structured log line ----


def test_deadline_helpers_match_the_a25_formulas():
    assert backup_deadline_sec(1.3) == pytest.approx(195.0)
    assert backup_deadline_sec(0.1) == 30.0
    assert sidestep_deadline_sec(0.36) == pytest.approx((math.pi / 0.5 + 3.6) * 15.0)
    assert sidestep_deadline_sec(0.72) == pytest.approx(202.2, abs=0.1)


def test_fast_fail_log_line_is_structured():
    line = fast_fail_log_line(
        "c1", "robot_3", "backup", 8.1, 195.0, 63.25,
        "fresh latch fast-fail: robot_3 latched during backup held_for=2.0s co_held=robot_1",
    )
    assert line.startswith(f"{FAST_FAIL_LOG_EVENT} command=c1 robot=robot_3 phase=backup ")
    assert "elapsed_s=8.1 deadline_s=195.0 saved_s=186.9 sim_t=63.250" in line
    assert line.endswith('co_held=robot_1"')


def _capturing_bus():
    adapter = _BusAdapter()
    node, statuses, subscriptions = _bus(adapter)
    from tests.unit.test_command_bus_node import _NullLogger

    logger = _NullLogger()
    node.get_logger = lambda: logger
    return adapter, node, logger


def test_bus_logs_the_b3_firing_once_with_elapsed_and_deadline(monkeypatch):
    from swarm_execution import command_bus_node

    now = {"t": 50.0}
    monkeypatch.setattr(command_bus_node.time, "monotonic", lambda: now["t"])
    adapter, node, logger = _capturing_bus()
    node._dispatch(_yield_msg(), {**_YIELD_PARAMS, "fresh_latch_fast_fail": True})
    backup_check = adapter.calls[0][1]["abort_check"]
    assert backup_check() is None
    assert not [line for line in logger.lines if FAST_FAIL_LOG_EVENT in line]
    node._on_safety_holds(type("M", (), {"data": json.dumps({"held": ["robot_1", "robot_3"]})}))
    now["t"] = 58.1
    detail = backup_check()
    assert detail.startswith(FRESH_LATCH_DETAIL_PREFIX)
    b3 = [line for line in logger.lines if line.startswith(FAST_FAIL_LOG_EVENT)]
    assert len(b3) == 1
    assert "command=c1 robot=robot_1 phase=backup elapsed_s=8.1 deadline_s=195.0" in b3[0]
    assert "co_held=robot_3" in b3[0]


def test_bus_logs_a_pull_off_firing_against_the_sidestep_deadline(monkeypatch):
    from swarm_execution import command_bus_node

    now = {"t": 10.0}
    monkeypatch.setattr(command_bus_node.time, "monotonic", lambda: now["t"])
    adapter, node, logger = _capturing_bus()
    node._dispatch(_yield_msg(), {**_YIELD_PARAMS, "fresh_latch_fast_fail": True})
    adapter.backup_on_result("COMPLETED", "backup complete")
    pull_off_check = adapter.calls[1][1]["abort_check"]
    node._on_safety_holds(type("M", (), {"data": json.dumps({"held": ["robot_1"]})}))
    now["t"] = 13.0
    assert pull_off_check() is not None
    b3 = [line for line in logger.lines if line.startswith(FAST_FAIL_LOG_EVENT)]
    assert len(b3) == 1
    assert "phase=pull_off elapsed_s=3.0" in b3[0]
    assert f"deadline_s={sidestep_deadline_sec(0.36):.1f}" in b3[0]


def test_bus_without_the_key_logs_nothing(monkeypatch):
    adapter, node, logger = _capturing_bus()
    node._dispatch(_yield_msg(), dict(_YIELD_PARAMS))
    assert "abort_check" not in adapter.calls[0][1]
    assert not [line for line in logger.lines if FAST_FAIL_LOG_EVENT in line]


# ---- A27(iv): vb AND dispatch_matched READ with shielded robots excluded ----

BATCH3 = json.loads(
    (Path(__file__).parent / "data/a27_shield_fix/batch3_plan_artifacts.json").read_text(
        encoding="utf-8"
    )
)["artifacts"]


def _vb_counts(artifacts: list[dict[str, Any]]) -> tuple[int, int]:
    from reasoning.rag.plan_metrics import shield_excluded_dispatch_match

    raw = excluded = 0
    for art in artifacts:
        if art["plan"]["provenance"] != "vlm_verbatim":
            continue
        match = shield_excluded_dispatch_match(art)
        raw += match.raw is True
        excluded += match.excluded is True
    return raw, excluded


def test_batch3_regression_three_raw_five_excluded():
    assert _vb_counts(BATCH3) == (3, 5)


def test_shielded_artifacts_flip_only_through_the_shield_legs():
    from reasoning.rag.plan_metrics import shield_excluded_dispatch_match

    flipped = {}
    for art in BATCH3:
        match = shield_excluded_dispatch_match(art)
        if match.shielded:
            assert match.raw is False and match.excluded is True
            assert match.shielded_legs_continue is True
            flipped[art["request_id"][:8]] = match.shielded
        else:
            assert match.excluded == match.raw
    assert flipped == {
        "56b599af": ("robot_1", "robot_4", "robot_5"),
        "f269ab37": ("robot_5",),
        "c18ade97": ("robot_3", "robot_4", "robot_5"),
    }


def test_recomputed_raw_match_must_equal_the_stored_one():
    from reasoning.rag.plan_metrics import shield_excluded_dispatch_match

    art = next(a for a in BATCH3 if a["request_id"].startswith("f269ab37"))
    tampered = {**art, "plan": {**art["plan"], "dispatch_matches_plan": True}}
    with pytest.raises(ValueError):
        shield_excluded_dispatch_match(tampered)


def test_excluding_nothing_is_the_live_plan_matches_dispatch():
    from reasoning.rag.command_grounder import plan_matches_dispatch
    from reasoning.rag.plan_metrics import dispatch_matches_plan_excluding
    from reasoning.vlm.models import ProposedPlanLeg

    for art in BATCH3:
        if not art["dispatched_command"]:
            continue
        known = [r["robot_id"] for r in art["scene"]["robots"]]
        legs = [ProposedPlanLeg(**leg) for leg in art["plan"]["legs"]]
        assert dispatch_matches_plan_excluding(
            art["plan"]["legs"], art["dispatched_command"], known
        ) == plan_matches_dispatch(legs, art["dispatched_command"], known)


def test_plan_parity_scorer_carries_the_shield_excluded_reading():
    from reasoning.rag.plan_metrics import (
        score_decision_artifact,
        tabulate_provenance_by_strategy_correctness,
    )

    metrics = [score_decision_artifact(a) for a in BATCH3]
    table = tabulate_provenance_by_strategy_correctness(m for m in metrics if m is not None)
    row = table["strategy_unscored"]
    assert row.verbatim_dispatch_matched == 3
    assert row.verbatim_dispatch_matched_shield_excluded == 5
    for art, m in zip(BATCH3, metrics, strict=True):
        if art["plan"]["provenance"] != "vlm_verbatim":
            assert m.verbatim_dispatch_matched_shield_excluded is None
