"""Unit tests for the pure pieces of `scripts/failure_cause_reconcile.py` (no bundle, no code tree)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts" / "failure_cause_reconcile.py"
_SPEC = importlib.util.spec_from_file_location("failure_cause_reconcile", _PATH)
fcr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fcr)


def test_code_class_maps_each_family() -> None:
    assert [fcr.code_class(c) for c in ("V4", "G5", "X3", "EG1", "U:T1_fidelity", "N0", "V4j")] == [
        "V", "G", "X", "EG", "U", "N", "V"]


def test_kappa_perfect_agreement_is_one() -> None:
    assert fcr.cohen_kappa(["V", "G", "X"], ["V", "G", "X"]) == pytest.approx(1.0)


def test_kappa_known_value() -> None:
    # po = 0.5, pe = 0.5 -> kappa 0
    assert fcr.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == pytest.approx(0.0)


def test_kappa_undefined_when_one_category() -> None:
    assert fcr.cohen_kappa(["U"] * 10, ["U"] * 10) is None


def test_kappa_rejects_unequal_lengths() -> None:
    with pytest.raises(ValueError):
        fcr.cohen_kappa(["a"], ["a", "b"])


def test_agreement_counts_and_raw() -> None:
    out = fcr.agreement(["V", "G", "U", "U"], ["V", "X", "U", "U"])
    assert (out["n"], out["agree"], out["raw"]) == (4, 3, 0.75)


def test_final_codes_take_round2_where_in_scope() -> None:
    r1 = [{"sheet_id": "EV-1", "unit_id": "FU1", "primary_code": "G4", "step_fired": "4",
           "contributing_codes": ["X3"]},
          {"sheet_id": "EV-1", "unit_id": "FU2", "primary_code": "V1", "step_fired": "4"},
          {"sheet_id": "EV-1", "unit_id": "FU3", "primary_code": "NOT_FU:parked_finished",
           "step_fired": "-"},
          {"sheet_id": "EV-1", "unit_id": "EPISODE", "primary_code": "G4", "step_fired": "ep"}]
    r2 = [{"sheet_id": "EV-1", "unit_id": "FU1", "round1_primary_code": "G4",
           "round2_primary_code": "U:T1_fidelity", "s3_primary_code": "G4", "step_fired": "4+7",
           "contributing_codes": ["X3", "G4"]}]
    out = fcr.final_codes(r1, r2)
    assert set(out) == {("EV-1", "FU1"), ("EV-1", "FU2")}
    assert out[("EV-1", "FU1")]["final"] == "U:T1_fidelity"
    assert out[("EV-1", "FU1")]["s3"] == "G4"
    assert out[("EV-1", "FU2")]["final"] == out[("EV-1", "FU2")]["s3"] == "V1"


def test_final_codes_rejects_round1_mismatch() -> None:
    r1 = [{"sheet_id": "EV-1", "unit_id": "FU1", "primary_code": "G4", "step_fired": "4"}]
    r2 = [{"sheet_id": "EV-1", "unit_id": "FU1", "round1_primary_code": "X3",
           "round2_primary_code": "X3", "step_fired": "4"}]
    with pytest.raises(ValueError):
        fcr.final_codes(r1, r2)


def test_reconcile_agreed_text_and_unresolved() -> None:
    assert fcr.reconcile("V1", "V1", None)["basis"] == "agreed"
    text = fcr.reconcile("X3", "X2", {"ruling": "R-X3T", "adopt": "A"})
    assert (text["code"], text["basis"]) == ("X3", "text")
    tie = fcr.reconcile("G2", "G1", {"ruling": "R-TIE"})
    assert tie["code"].startswith("U:unresolved") and tie["basis"] == "unresolved"


def test_reconcile_disagreement_without_ruling_raises() -> None:
    with pytest.raises(ValueError):
        fcr.reconcile("G2", "G1", None)


def test_episode_primary_is_earliest_onset() -> None:
    units = [{"unit_id": "FU1", "t0_rel": 50.0, "robots": ["robot_1", "robot_2"]},
             {"unit_id": "FU2", "t0_rel": 10.0, "robots": ["robot_3"]}]
    assert fcr.episode_primary(units)["unit_id"] == "FU2"
    assert fcr.episode_primary([]) is None


def _leg(leg_id: str, robot: str, kind: str, dispatch: float, end: float | None) -> dict:
    return {"leg_id": leg_id, "robot": robot, "kind": kind, "dispatch_rel": dispatch,
            "end_rel_local": end}


def test_s1_links_leg_pinned_on_box_until_onset() -> None:
    legs = [_leg("a:robot_3:escort", "robot_3", "escort", 70.9, 172.0)]
    spans = {"robot_3|box:obstacle_2": [{"from_rel": 114.7, "to_rel": 568.5}]}
    out = fcr.s1_links(legs, ["robot_2", "robot_3"], 240.9, spans, [])
    assert [x["leg_id"] for x in out] == ["a:robot_3:escort"]
    assert out[0]["state"][0]["with"] == "obstacle_2"


def test_s1_no_link_when_later_command_to_robot() -> None:
    legs = [_leg("a:robot_3:escort", "robot_3", "escort", 70.9, 172.0),
            _leg("b:robot_3:wait", "robot_3", "wait", 200.0, 210.0)]
    spans = {"robot_3|box:obstacle_2": [{"from_rel": 114.7, "to_rel": 568.5}]}
    assert fcr.s1_links(legs, ["robot_3"], 240.9, spans, []) == []


def test_s1_no_link_when_state_breaks_before_onset() -> None:
    legs = [_leg("a:robot_3:escort", "robot_3", "escort", 70.9, 172.0)]
    spans = {"robot_3|box:obstacle_2": [{"from_rel": 114.7, "to_rel": 200.0}]}
    assert fcr.s1_links(legs, ["robot_3"], 240.9, spans, []) == []


def test_s1_links_through_robot_pair_interval_and_skips_waits() -> None:
    legs = [_leg("a:robot_1:reverse", "robot_1", "reverse", 10.0, 30.0),
            _leg("a:robot_1:wait", "robot_1", "wait", 10.0, 30.0)]
    pairs = [{"pair": ["robot_1", "robot_2"], "onset_s": 25.0, "end_s": 500.0}]
    out = fcr.s1_links(legs, ["robot_1", "robot_2"], 120.0, {}, pairs)
    assert [x["leg_id"] for x in out] == ["a:robot_1:reverse"]
    assert out[0]["state"][0]["kind"] == "robot"


def test_s2_blocked_rules() -> None:
    need = 0.14
    assert fcr.s2_blocked(0.10, 0.20, need) is True  # started clear, now inside
    assert fcr.s2_blocked(0.10, 0.10, need) is False  # started inside, moving along
    assert fcr.s2_blocked(0.12, 0.10, need) is False  # started inside, moving away
    assert fcr.s2_blocked(0.09, 0.10, need) is True  # started inside, deeper
    assert fcr.s2_blocked(0.15, 0.10, need) is False  # out of the clearance


def test_blocked_robots_parses_reverse_and_escort_verdicts() -> None:
    v = ("refused: reverse_hits_obstacle:robot_2:obstacle_2:0.584; "
         "reverse_hits_obstacle:robot_3:obstacle_1:0.696")
    assert fcr.blocked_robots(v) == {"robot_2": 0.584, "robot_3": 0.696}
    e = "refused: yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414"
    assert fcr.blocked_robots(e) == {"robot_3": 0.414}
    assert fcr.blocked_robots("unchanged") == {}


@pytest.mark.parametrize(("leg", "clear", "expected"), [
    ({"m4_terminal": "FAILED", "min_static_gap_m": -0.001, "gt_moved_max_m": 0.6}, 0.5,
     "contact_or_pinned"),
    ({"m4_terminal": "COMPLETED", "min_static_gap_m": 0.018, "gt_moved_max_m": 1.1}, 0.3,
     "submargin_graze"),
    ({"m4_terminal": "COMPLETED", "min_static_gap_m": 0.077, "gt_moved_max_m": 1.27}, 0.7,
     "false_positive"),
    ({"m4_terminal": "FAILED", "min_static_gap_m": 0.39, "gt_moved_max_m": 0.1}, 1.2, "untested"),
    ({"m4_terminal": "COMPLETED", "min_static_gap_m": 0.21, "gt_moved_max_m": 1.3}, None,
     "co_refused_clear:COMPLETED"),
])
def test_guard_leg_outcome(leg: dict, clear: float | None, expected: str) -> None:
    assert fcr.guard_leg_outcome(leg, clear) == expected


def test_stall_leg_outcome_classes() -> None:
    pinned = {"min_static_gap_m": -0.0002, "pinned_on": "box:obstacle_2"}
    free = {"min_static_gap_m": 0.3}
    assert fcr.stall_leg_outcome(pinned, fired=True, ran=True) == "contact_or_pinned"
    assert fcr.stall_leg_outcome(free, fired=True, ran=True) == "false_positive"
    assert fcr.stall_leg_outcome(free, fired=False, ran=True) == "not_fired"
    assert fcr.stall_leg_outcome(free, fired=False, ran=False) == "no_primitive_ran"


def test_table_counts_by_column_and_class() -> None:
    units = [{"column": "A", "c": "X3"}, {"column": "A", "c": "U:T1_fidelity"},
             {"column": "B", "c": "U:no_m4_clock_anchor"}]
    out = fcr.table_counts(units, "c")
    assert out["A"] == {"X": 1, "U": 1} and out["B"] == {"U": 1} and out["N"] == {}
