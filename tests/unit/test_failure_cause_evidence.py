"""Unit tests for the pure pieces of `scripts/failure_cause_evidence.py` (no bundle, no code tree)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "failure_cause_evidence.py"
_SPEC = importlib.util.spec_from_file_location("failure_cause_evidence", _PATH)
fce = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fce)


def _gt(seconds: float, poses_at) -> list[tuple[float, dict[str, tuple[float, float]]]]:
    return [(t / 10.0, poses_at(t / 10.0)) for t in range(int(seconds * 10) + 1)]


def test_lone_stall_found_when_robot_still_for_last_60s() -> None:
    gt = _gt(100.0, lambda t: {"robot_1": (min(t, 30.0) * 0.1, 0.0), "robot_2": (t * 0.1, 1.0)})
    stalls = fce.lone_stalls(gt, fu_robots=set(), dwelling_at_end=set())
    assert [s["robot"] for s in stalls] == ["robot_1"]


def test_lone_stall_onset_is_start_of_stationary_run() -> None:
    gt = _gt(100.0, lambda t: {"robot_1": (min(t, 30.0) * 0.1, 0.0)})
    (stall,) = fce.lone_stalls(gt, fu_robots=set(), dwelling_at_end=set())
    assert stall["onset"] == pytest.approx(29.6, abs=0.11)


def test_lone_stall_skips_robot_in_conflict_unit() -> None:
    gt = _gt(100.0, lambda t: {"robot_1": (0.0, 0.0)})
    assert fce.lone_stalls(gt, fu_robots={"robot_1"}, dwelling_at_end=set()) == []


def test_lone_stall_dwelling_robot_marked_excluded() -> None:
    gt = _gt(100.0, lambda t: {"robot_1": (0.0, 0.0)})
    (stall,) = fce.lone_stalls(gt, fu_robots=set(), dwelling_at_end={"robot_1"})
    assert stall["excluded"] is True


def test_lone_stall_not_found_when_moved_in_window() -> None:
    gt = _gt(100.0, lambda t: {"robot_1": (t * 0.01, 0.0)})
    assert fce.lone_stalls(gt, fu_robots=set(), dwelling_at_end=set()) == []


def test_task_phase_dwelling_reports_remaining_dwell() -> None:
    events = [
        {"event": "issued", "robot_id": "robot_1", "sim_t": 10.0, "task_index": 0,
         "node": "N", "goal": [0.0, 1.0]},
        {"event": "arrived", "robot_id": "robot_1", "sim_t": 20.0},
    ]
    ph = fce.task_phase_at(events, "robot_1", 22.0, dwell_s=5.0)
    assert (ph["phase"], ph["dwell_left_s"]) == ("dwelling", 3.0)


def test_task_phase_finished_after_last_dwell_complete() -> None:
    events = [
        {"event": "issued", "robot_id": "robot_1", "sim_t": 10.0, "task_index": 0, "node": "N"},
        {"event": "arrived", "robot_id": "robot_1", "sim_t": 20.0},
        {"event": "dwell_complete", "robot_id": "robot_1", "sim_t": 25.0},
    ]
    assert fce.task_phase_at(events, "robot_1", 30.0, dwell_s=5.0)["phase"] == "finished"


def test_contract_c1_flags_reverse_plan_differing_from_involved() -> None:
    decision = {
        "strategy": "reverse", "involved_robots": ["robot_4", "robot_5"],
        "proposed_plan": [{"robot_id": "robot_4", "action": "reverse"},
                          {"robot_id": "robot_5", "action": "continue"}],
    }
    assert fce.contract_checks(decision)["C1"] is True


def test_contract_c2_passes_single_matching_yield_leg() -> None:
    decision = {
        "strategy": "yield", "involved_robots": ["robot_2", "robot_3"], "yield_robot": "robot_2",
        "proposed_plan": [{"robot_id": "robot_2", "action": "yield"},
                          {"robot_id": "robot_3", "action": "cross"}],
    }
    assert fce.contract_checks(decision)["C2"] is False


def test_command_kinds_marks_escorted_passer() -> None:
    command = {"actions": [{"robot_id": "robot_2", "action": "yield", "parameters": {
        "backup_distance_m": 1.4, "passer_robot_id": "robot_3", "passer_escort_distance_m": 1.6}}]}
    assert fce.command_kinds(command) == {"robot_2": ["backup"], "robot_3": ["escort"]}


def test_command_kinds_reroute_without_waypoints_is_empty() -> None:
    command = {"actions": [{"robot_id": "robot_1", "action": "reroute", "parameters": {}}]}
    assert fce.command_kinds(command) == {"robot_1": ["reroute_empty"]}


def test_reproduces_ignores_plan_id_and_a25_keys_only() -> None:
    live = {"actions": [{"robot_id": "r", "action": "reverse", "parameters": {
        "backup_distance_m": 1.3, "plan_id": 2, "backup_facing_rad": 0.1}}], "degradations": ["x"]}
    replay = {"actions": [{"robot_id": "r", "action": "reverse", "parameters": {
        "backup_distance_m": 1.3}}], "degradations": ["x"]}
    assert fce.reproduces(replay, live) is True


def test_reproduces_fails_on_missing_shield_key() -> None:
    live = {"actions": [{"robot_id": "r", "action": "temporary_wait", "parameters": {
        "retreat_shield_hold": True}}], "degradations": []}
    replay = {"actions": [{"robot_id": "r", "action": "temporary_wait", "parameters": {}}],
              "degradations": []}
    assert fce.reproduces(replay, live) is False


def test_hypothesis_set_size_for_five_candidates() -> None:
    hs = fce.hypothesis_set([f"robot_{i}" for i in range(1, 6)])
    # 20 pairs + 5 x (P(4,2) + P(4,3)) multi-passer + 16 reverse + 5 reroute + 1 wait + 15
    assert len(hs) == 20 + 5 * (12 + 24) + 16 + 5 + 1 + 15


def test_hypothesis_crossing_order_is_permutation_of_involved() -> None:
    for h in fce.hypothesis_set(["robot_1", "robot_2", "robot_3"]):
        if h["crossing_order"] is not None:
            assert sorted(h["crossing_order"]) == sorted(h["involved"])


def test_fit_wall_to_sim_recovers_line() -> None:
    fit = fce.fit_wall_to_sim([(1000.0 + w, 0.2 * w + 30.0) for w in range(0, 100, 10)])
    assert (fit["a"], fit["b"] + 1000.0 * fit["a"]) == pytest.approx((0.2, 30.0))


def test_fit_wall_to_sim_none_without_two_anchors() -> None:
    assert fce.fit_wall_to_sim([(1.0, 2.0)]) is None


def test_parse_m4_reads_handover_status_and_anchor(tmp_path: Path) -> None:
    log = tmp_path / "m4.log"
    log.write_text(
        "[c-2] [INFO] [1794716845.184701324] [coordination_client_node]: handoff guard: "
        "controller stop robot=robot_1 command=abc-yield action=yield reason=handover sim_t=46.267\n"
        "[s-3] [INFO] [1794716845.3] [safety_monitor_node]: safety stop robot=robot_1 "
        "reason=min_distance_violation\n"
        "[b-1] [INFO] [1794717115.596077663] [command_bus_node]: status published "
        "command=abc-yield robot=robot_1 status=COMPLETED\n"
    )
    m4 = fce.parse_m4(log)
    assert (m4["anchors"], m4["handover"][0][1:], m4["status"][0][1:],
            sorted(m4["safety_stop"])) == (
        [(1794716845.184701324, 46.267)],
        ("robot_1", "abc-yield", "yield", "handover", "46.267"),
        ("abc-yield", "robot_1", "COMPLETED"),
        [("robot_1", "min_distance_violation")],
    )


def test_timeline_orders_events_and_drops_other_robots() -> None:
    unit = {"robots": ["robot_2", "robot_3"], "t0_rel": 100.0, "analyses_on_fu": []}
    decisions = [{"request_id": "d1", "t_rel": 90.0, "analysis_class": "positive",
                  "decision": {"strategy": "yield", "involved_robots": ["robot_2", "robot_3"],
                               "yield_robot": "robot_2"},
                  "grounding": {"actions": [{"robot": "robot_2", "action": "yield"}],
                                "withheld": None}}]
    legs = [{"leg_id": "d1:robot_3:escort", "robot": "robot_3", "kind": "escort",
             "start_rel": 95.0, "end_rel": 120.0, "commanded_m": 1.6, "m4_terminal": "FAILED"},
            {"leg_id": "dX:robot_1:reverse", "robot": "robot_1", "kind": "reverse",
             "start_rel": 96.0, "end_rel": 99.0}]
    stale = {"robot_3": [{"from_rel": 110.0, "to_rel": 130.0, "duration_s": 20.0, "ge_10s": True}]}
    contacts = {"spans_within_0.05m_rel": {"robot_3|box:obstacle_2": [
        {"from_rel": 105.0, "to_rel": 120.0, "min_gap_m": -0.0002, "contact": True}]}}
    latch = {"exempt_changes": [], "safety_stop_spans": {}}
    tl = fce.Episode.timeline(None, unit, decisions, legs, stale, contacts, latch, [])
    assert [(e["rel"], e["type"]) for e in tl] == [
        (90.0, "analysis"), (90.0, "dispatched"), (95.0, "m4_leg_start"),
        (105.0, "gt_contact"), (110.0, "m1_stale"), (120.0, "m4_terminal")]


def test_chain_links_rubric_window_on_dispatch_time() -> None:
    legs = [{"leg_id": "a", "robot": "robot_1", "dispatch_rel": 50.0, "start_rel": 52.0,
             "end_rel": 70.0},
            {"leg_id": "b", "robot": "robot_1", "dispatch_rel": 10.0, "start_rel": 12.0,
             "end_rel": 30.0}]
    assert fce.chain_links(legs, {"robot_1"}, t0=100.0) == {"rubric": ["a"], "end_window": ["a"]}


def test_chain_links_executing_at_onset_counts() -> None:
    legs = [{"leg_id": "a", "robot": "robot_1", "dispatch_rel": 10.0, "start_rel": 12.0,
             "end_rel": None}]
    assert fce.chain_links(legs, {"robot_1"}, t0=100.0)["rubric"] == ["a"]


def _full_sheet() -> dict:
    return {
        "label": "E12", "bundle": "/x/s1b_E12_seed12_er2_c1", "stratum": "pilot_er2", "arm": "A",
        "seed": 1404977387, "run_id": "20261011_124312", "session_id": "abc",
        "provenance": {"tool": "x"}, "outcome": {"tasks": 3},
        "censor": {"t_end_rel": 570.1, "reason_a33": "horizon"},
        "units": [{"fu": "FU1", "kind": "conflict", "robots": ["robot_1"], "t0_rel": 1.0,
                   "end_rel": 2.0, "pairs": [], "excluded": False, "flags": []}],
        "decisions": [{"request_id": "d374802a" + "0" * 24,
                       "plan": {"provenance": "vlm_verbatim"},
                       "grounding": {"degradations": []}}],
        "t2": {"FU1": {"t0": {"result": True}, "d374802a" + "0" * 24: {"result": False}}},
        "t1": {"FU1": {"t0": {"params_source": "s1b_E12_seed12_er2_c1:d374802a"}}},
        "contacts": {},
    }


def test_rater_view_drops_arm_ids_and_outcome() -> None:
    full = _full_sheet()
    view = fce.rater_view(full, {full["decisions"][0]["request_id"]: "D1"})
    text = json.dumps(view)
    assert not any(k in text for k in ("1404977387", "pilot_er2", "outcome", "d374802a",
                                       "s1b_E12", "\"arm\""))


def test_rater_view_keeps_plan_provenance() -> None:
    full = _full_sheet()
    view = fce.rater_view(full, {full["decisions"][0]["request_id"]: "D1"})
    assert view["decisions"][0]["plan"]["provenance"] == "vlm_verbatim"


def test_gt_view_keeps_only_onset_snapshot() -> None:
    assert list(fce.gt_view(_full_sheet())["t2"]["FU1"]) == ["t0"]


def test_leak_hits_word_aware() -> None:
    assert fce.leak_hits("grounding=dynamic_arms:lane:x armature", []) == []


def test_leak_hits_finds_episode_label_and_seed() -> None:
    hits = fce.leak_hits("E12 seed 1404977387", ["1404977387"])
    assert len(hits) >= 2
