"""Unit tests for the B1/B2/B3 ground-truth scorers (synthetic GT, offline)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from scripts.coverage_scene_scores import (
    Sample,
    conflict_timeline,
    decision_route,
    dispatched_junction_decision,
    final_crossing,
    first_passer,
    first_slipper,
    gate_passage,
    load_ground_truth,
    load_scenario,
    phase_reached,
    release_attribution,
    score_b1,
    score_b2,
    score_b2_episode,
    score_b3,
    score_chi_pair,
    score_conflict,
    score_ib10,
    score_inside_first,
    slip_onset_sec,
    stale_streaks,
    stop_time_sec,
)

DT = 0.1


def _write_gt(gt_dir: Path, frames: list[dict[str, tuple[float, float, float, float]]],
              goals: dict[str, tuple[float, float]]) -> Path:
    """frames[i] = robot -> (x, y, theta, speed) at sim t = i * DT."""
    gt_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, robots in enumerate(frames):
        lines.append(json.dumps({
            "sim_time_sec": round(i * DT, 4),
            "robots": {
                rid: {"x": x, "y": y, "theta": th, "speed_mps": v,
                      "goal_x": goals[rid][0], "goal_y": goals[rid][1],
                      "distance_to_goal_m": math.dist((x, y), goals[rid])}
                for rid, (x, y, th, v) in robots.items()
            },
        }))
    (gt_dir / "ground_truth.jsonl").write_text("\n".join(lines) + "\n")
    return gt_dir


def _track(points: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Piecewise-linear path through `points`, resampled to n positions."""
    if len(points) == 1:
        return points * n
    seg = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
    lengths = [math.dist(a, b) for a, b in seg]
    total = sum(lengths) or 1.0
    out = []
    for k in range(n):
        d = total * k / (n - 1)
        for (a, b), length in zip(seg, lengths, strict=True):
            if d <= length or (a, b) == seg[-1]:
                f = 0.0 if length == 0 else min(d / length, 1.0)
                out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
                break
            d -= length
    return out


def _frames(tracks: dict[str, list[tuple[float, float]]],
            headings: dict[str, float] | None = None):
    n = len(next(iter(tracks.values())))
    frames = []
    for i in range(n):
        robots = {}
        for rid, path in tracks.items():
            x, y = path[i]
            px, py = path[i - 1] if i else path[i]
            v = math.dist((x, y), (px, py)) / DT
            th = (headings or {}).get(rid, math.atan2(y - py, x - px) if v else 0.0)
            robots[rid] = (x, y, th, v)
        frames.append(robots)
    return frames


def _hold(point, n):
    return [point] * n


def test_stop_time_counts_only_spells_of_at_least_one_second():
    samples = [Sample(t=i * DT, x=0, y=0, theta=0, speed=0.0 if i < 5 or 10 <= i < 30 else 0.1,
                      distance_to_goal=1.0) for i in range(40)]
    # 0.0-0.4 (0.4 s, dropped) and 1.0-2.9 (1.9 s, kept)
    assert stop_time_sec(samples, 0.0, 4.0) == pytest.approx(1.9)


def test_gate_passage_uses_the_last_lane_crossing():
    xs = [0.5, 0.8, 1.2, 1.8, 1.5, 1.6, 1.75, 2.0]
    samples = [Sample(t=float(i), x=x, y=0.0, theta=0, speed=0.1, distance_to_goal=1.0)
               for i, x in enumerate(xs)]
    entry, exit_t = gate_passage(samples, (0.7, 1.7), 0.275)
    assert (entry, exit_t) == (1.0, 6.0)


def test_gate_passage_ignores_crossings_outside_the_lane():
    samples = [Sample(t=float(i), x=x, y=0.5, theta=0, speed=0.1, distance_to_goal=1.0)
               for i, x in enumerate([0.5, 1.0, 1.9])]
    assert gate_passage(samples, (0.7, 1.7), 0.275) == (None, None)


def test_final_crossing_ignores_a_yielder_that_pokes_past_and_backs_away():
    xs = [-0.5, 0.05, 0.05, -1.0, -1.7]
    samples = [Sample(t=float(i), x=x, y=0, theta=0, speed=0, distance_to_goal=1.0)
               for i, x in enumerate(xs)]
    assert final_crossing(samples, 0.0, 1.0) is None


def test_final_crossing_takes_the_last_crossing_that_stays_past():
    xs = [-0.5, 0.05, -1.0, -0.2, 0.3, 2.4]
    samples = [Sample(t=float(i), x=x, y=0, theta=0, speed=0, distance_to_goal=1.0)
               for i, x in enumerate(xs)]
    assert final_crossing(samples, 0.0, 1.0) == 4.0


def _b2_gt(tmp_path: Path, first: str) -> Path:
    """robot_1 east (-1.5 -> 2.5), robot_2 west (1.5 -> -2.5); `first` passes first."""
    n_stand, n_pass, n_back = 40, 60, 60
    side = {"robot_1": -1.0, "robot_2": 1.0}
    goal = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}
    tracks = {}
    for rid in ("robot_1", "robot_2"):
        s = side[rid]
        standoff = (0.12 * s, 0.0)
        if rid == first:
            path = (_track([(1.5 * s, 0.0), standoff], n_stand) + _hold(standoff, n_back)
                    + _track([standoff, goal[rid]], n_pass) + _hold(goal[rid], n_pass))
        else:
            park = (1.8 * s, 0.36)
            path = (_track([(1.5 * s, 0.0), standoff], n_stand) + _track([standoff, park], n_back)
                    + _hold(park, n_pass) + _track([park, goal[rid]], n_pass))
        tracks[rid] = path
    return _write_gt(tmp_path / f"gt_{first}", _frames(tracks), goal)


def test_first_passer_is_the_robot_that_crosses_centre_first(tmp_path):
    from scripts.coverage_scene_scores import load_ground_truth

    series = load_ground_truth(_b2_gt(tmp_path, "robot_2"))
    passer, times = first_passer(series)
    assert passer == "robot_2"
    assert times["robot_1"] is not None and times["robot_2"] < times["robot_1"]


def test_b2_episode_scores_cp_against_the_members_urgent_robot(tmp_path):
    gt = _b2_gt(tmp_path, "robot_2")
    assert score_b2_episode("r2", gt)["cp"] is True
    assert score_b2_episode("r1", gt)["cp"] is False


def test_b2_pair_is_divergent_and_correct_only_when_both_members_score(tmp_path):
    r2_good = score_b2_episode("r2", _b2_gt(tmp_path / "a", "robot_2"))
    r1_good = score_b2_episode("r1", _b2_gt(tmp_path / "b", "robot_1"))
    r1_bad = score_b2_episode("r1", _b2_gt(tmp_path / "c", "robot_2"))
    result = score_b2([("r1", 42, r1_good), ("r2", 42, r2_good),
                       ("r1", 43, r1_bad), ("r2", 43, r2_good)])
    assert [p["divergent_and_correct"] for p in result["pairs"]] == [True, False]
    assert result["divergent_and_correct_rate"] == 0.5
    assert result["members"]["r1"]["cp_rate"] == 0.5
    assert result["members"]["r2"]["cp_rate"] == 1.0


def test_b2_label_blind_answer_scores_zero_pairs(tmp_path):
    # Arm B's shape: the same robot (robot_1) passes first in both members.
    r1 = score_b2_episode("r1", _b2_gt(tmp_path / "a", "robot_1"))
    r2 = score_b2_episode("r2", _b2_gt(tmp_path / "b", "robot_1"))
    assert score_b2([("r1", 1, r1), ("r2", 1, r2)])["divergent_and_correct_rate"] == 0.0


def test_decision_route_reads_priority_override_as_the_registry_maximum(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "grounded_command_present": True,
        "decision": {"congestion_detected": True, "strategy": "priority_override",
                     "involved_robots": ["robot_1", "robot_2"]},
    }))
    (tmp_path / "b.json").write_text(json.dumps({
        "grounded_command_present": False,
        "decision": {"congestion_detected": False, "strategy": "none", "involved_robots": []},
    }))
    route = decision_route(tmp_path, "robot_2")
    assert route["route"] == "priority_override"
    assert route["first_passer"] == "robot_2"


def test_decision_route_reads_a_yield_as_the_non_yielder(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({
        "grounded_command_present": True,
        "decision": {"congestion_detected": True, "strategy": "yield", "yield_robot": "robot_2",
                     "involved_robots": ["robot_1", "robot_2"]},
    }))
    assert decision_route(tmp_path, "robot_2")["first_passer"] == "robot_1"


def _b1_gt(tmp_path: Path, *, robot_2_first: bool = False) -> Path:
    goals = {"robot_1": (2.45, -0.3), "robot_2": (1.9, 0.0), "robot_3": (2.45, 0.3)}
    n = 60
    if robot_2_first:
        r2 = _track([(0.0, 1.75), (0.0, 0.0), (0.6, 0.0)], n) + _hold((0.6, 0.0), 200)
        r1 = _track([(-1.0, 0.0), (0.28, 0.0)], n) + _hold((0.28, 0.0), 200)
        r3 = _hold((-2.45, 0.0), n + 200)
        return _write_gt(tmp_path / "gt_follower",
                         _frames({"robot_1": r1, "robot_2": r2, "robot_3": r3}), goals)
    r1 = (_track([(-1.0, 0.0), (0.1, 0.0)], n) + _hold((0.1, 0.0), 60)
          + _track([(0.1, 0.0), (1.7, 0.0), (2.45, -0.3)], 120) + _hold(goals["robot_1"], 160))
    r2 = (_track([(0.0, 1.75), (0.15, 0.45)], n) + _hold((0.15, 0.45), 60)
          + _track([(0.15, 0.45), (0.3, 1.7)], 60) + _hold((0.3, 1.7), 100)
          + _track([(0.3, 1.7), (0.0, 0.0), (1.9, 0.0)], 120))
    r3 = (_hold((-2.45, 0.0), n + 60) + _hold((-2.45, 0.0), 60)
          + _track([(-2.45, 0.0), (1.7, 0.0), (2.45, 0.3)], 160) + _hold(goals["robot_3"], 60))
    headings = None
    frames = _frames({"robot_1": r1, "robot_2": r2, "robot_3": r3}, headings)
    # robot_2 comes down its arm heading -80 deg at the latch.
    for i in range(n, n + 60):
        x, y, _th, v = frames[i]["robot_2"]
        frames[i]["robot_2"] = (x, y, math.radians(-80.0), v)
    return _write_gt(tmp_path / "gt_b1", frames, goals)


def test_b1_scores_the_designed_perpendicular_latch(tmp_path):
    result = score_b1(_b1_gt(tmp_path))
    merge = result["merge"]
    assert merge["merge_mode"] == "perpendicular_latch"
    assert merge["robot_2_east_of_robot_1"] is True
    assert merge["standoff_gap_m"] == pytest.approx(math.dist((0.1, 0.0), (0.15, 0.45)), abs=0.01)
    assert result["conflict"]["onset_sec"] is not None
    assert result["n_arrived"] == 3
    assert result["makespan_sec"] is not None
    assert result["gate"]["n_exited"] == 3
    assert result["gate"]["flow_per_100s"] > 0


def test_b1_flags_the_follower_latch_when_robot_2_turns_in_first(tmp_path):
    result = score_b1(_b1_gt(tmp_path, robot_2_first=True))
    assert result["merge"]["merge_mode"] == "follower_latch"
    assert result["censored"] is True
    assert result["makespan_sec"] is None


def test_b1_stop_time_charges_the_held_robot_its_wait(tmp_path):
    result = score_b1(_b1_gt(tmp_path))
    assert result["stop_time_sec"]["robot_3"] > result["stop_time_sec"]["robot_1"]


def test_conflict_timeline_skips_pairs_parked_at_their_goals(tmp_path):
    from scripts.coverage_scene_scores import load_ground_truth

    goals = {"robot_1": (2.45, -0.3), "robot_3": (2.45, 0.3)}
    gt = _write_gt(tmp_path / "gt", _frames({"robot_1": _hold(goals["robot_1"], 30),
                                             "robot_3": _hold(goals["robot_3"], 30)}), goals)
    assert conflict_timeline(load_ground_truth(gt), (0.7, 1.7))["onset_sec"] is None


def test_score_conflict_checks_the_onset_window(tmp_path):
    from scripts.coverage_scene_scores import load_ground_truth

    goals = {"robot_1": (2.45, -0.3), "robot_2": (-2.0, 0.0)}
    frames = _frames({
        "robot_1": _track([(-1.2, 0.0), (-0.12, 0.0)], 100) + _hold((-0.12, 0.0), 300),
        "robot_2": _track([(1.2, 0.0), (0.12, 0.0)], 100) + _hold((0.12, 0.0), 300),
    })
    result = score_conflict(load_scenario("convoy_counterflow"),
                            load_ground_truth(_write_gt(tmp_path / "gt", frames, goals)))
    assert result["onset_sec"] == pytest.approx(10.0, abs=0.2)
    assert result["onset_in_window"] is False  # window [15, 50]
    assert result["min_duration_met"] is True


def test_slip_onset_sec_ignores_jitter_below_threshold():
    # Noise up to 0.04 m, under the 0.05 m threshold, forever.
    samples = [Sample(t=i * DT, x=0.04 if i % 2 else -0.04, y=0.0, theta=0, speed=0.0,
                      distance_to_goal=1.0) for i in range(40)]
    assert slip_onset_sec(samples, (0.0, 0.0)) is None


def test_slip_onset_sec_ignores_a_poke_and_return_shorter_than_the_hold():
    # Departs past 0.05 m for 0.5 s (5 samples), then returns: shorter than
    # the 1.0 s hold, so it never counts as a slip.
    xs = [0.0] * 10 + [0.2] * 5 + [0.0] * 25
    samples = [Sample(t=i * DT, x=x, y=0.0, theta=0, speed=0.1, distance_to_goal=1.0)
               for i, x in enumerate(xs)]
    assert slip_onset_sec(samples, (0.0, 0.0)) is None


def test_slip_onset_sec_returns_the_first_sustained_spells_onset():
    # Departs at t=1.0 and stays departed for 1.5 s: the slip.
    xs = [0.0] * 10 + [0.2] * 15 + [0.4] * 5
    samples = [Sample(t=i * DT, x=x, y=0.0, theta=0, speed=0.1, distance_to_goal=1.0)
               for i, x in enumerate(xs)]
    assert slip_onset_sec(samples, (0.0, 0.0)) == pytest.approx(1.0)


def test_slip_onset_sec_returns_none_for_a_robot_that_never_moves():
    samples = [Sample(t=i * DT, x=-2.47, y=0.0, theta=0, speed=0.0, distance_to_goal=5.0)
               for i in range(300)]
    assert slip_onset_sec(samples, (-2.47, 0.0)) is None


def _b3_gt(tmp_path: Path, slip_order: tuple[str, str, str]) -> Path:
    """robot_1/robot_2 approach to the standoff (onset ~10 s); robot_3/robot_4
    held at spawn. `slip_order` gives when each of robot_1/robot_3/robot_4
    departs its onset-time position, earliest first (the never-moving member
    is last and stays put for the whole fixture)."""
    goals = {"robot_1": (2.45, -0.36), "robot_2": (-2.0, 0.0),
             "robot_3": (2.45, 0.36), "robot_4": (1.85, 0.0)}
    spawn = {"robot_1": (-1.2, 0.0), "robot_3": (-1.9, 0.0), "robot_4": (-2.47, 0.0)}
    standoff = {"robot_1": (-0.12, 0.0)}
    # Slip times (sim-s after t=0) for the first- and second-to-slip members;
    # the third never moves. 100 samples (10 s) to reach position, then hold
    # until its slip time, then a sustained 2 s move away.
    slip_time = {slip_order[0]: 15.0, slip_order[1]: 25.0}
    n_total = 400
    tracks: dict[str, list[tuple[float, float]]] = {}
    for rid in ("robot_1", "robot_3", "robot_4"):
        onset_pos = standoff.get(rid, spawn[rid])
        approach = _track([spawn[rid]] * 1 + [onset_pos], 100) if rid == "robot_1" else []
        pre_hold_n = 100 if rid == "robot_1" else 150
        path = (approach or _hold(onset_pos, 0)) + _hold(onset_pos, pre_hold_n - len(approach))
        t_slip = slip_time.get(rid)
        if t_slip is None:
            path += _hold(onset_pos, n_total - len(path))
        else:
            hold_n = round(t_slip / DT) - len(path)
            move_n = 20  # 2 s sustained move, well past the 1.0 s hold rule
            path += _hold(onset_pos, hold_n)
            path += _track([onset_pos, (onset_pos[0] + 0.5, onset_pos[1])], move_n)
            path += _hold((onset_pos[0] + 0.5, onset_pos[1]), n_total - len(path))
        tracks[rid] = path[:n_total]
    tracks["robot_2"] = (_track([(1.2, 0.0), (0.12, 0.0)], 100) + _hold((0.12, 0.0), n_total - 100))
    return _write_gt(tmp_path / f"gt_{slip_order[0]}", _frames(tracks), goals)


def test_first_slipper_is_the_earliest_departing_platoon_member(tmp_path):
    from scripts.coverage_scene_scores import load_ground_truth

    series = load_ground_truth(_b3_gt(tmp_path, ("robot_1", "robot_3", "robot_4")))
    slipper, onsets = first_slipper(series, ("robot_1", "robot_3", "robot_4"), onset_sec=10.0)
    assert slipper == "robot_1"
    assert onsets["robot_4"] is None
    assert onsets["robot_1"] < onsets["robot_3"]


def test_first_slipper_identity_is_not_hardcoded_to_robot_1(tmp_path):
    """robot_3 slips first here: the identity tracks the GT, not queue order."""
    from scripts.coverage_scene_scores import load_ground_truth

    series = load_ground_truth(_b3_gt(tmp_path, ("robot_3", "robot_1", "robot_4")))
    slipper, _onsets = first_slipper(series, ("robot_1", "robot_3", "robot_4"), onset_sec=10.0)
    assert slipper == "robot_3"


def test_score_b3_reports_identity_and_latency_from_conflict_onset(tmp_path):
    result = score_b3(
        _b3_gt(tmp_path, ("robot_1", "robot_3", "robot_4")),
        scenario=load_scenario("convoy_counterflow_slip"),
    )
    assert result["conflict"]["onset_sec"] == pytest.approx(10.0, abs=0.2)
    assert result["first_slipper"] == "robot_1"
    assert result["slip_onset_sec"]["robot_4"] is None
    assert result["first_slip_latency_sec"] == pytest.approx(5.0, abs=0.3)


# ---- IB10 junction_clear resolution oracle (step-7b Part 3) ----

IB10_GOALS = {
    "robot_1": (1.75, 0.0),
    "robot_2": (-1.75, 0.0),
    "robot_3": (0.0, 1.75),
    "robot_4": (0.0, -1.75),
}
# The designed episode: the four-way jam forms at ~15 s; the lead robot_4
# recedes north to its 1.2 pocket, robot_3 south to its staggered 1.0 pocket,
# robot_1 yields west and robot_2 crosses; then robot_4 re-enters first and
# robot_3 and the yielder robot_1 last.
IB10_DESIGNED = {
    "robot_1": [(0, -1.75, 0.0), (10, -1.75, 0.0), (15, -0.25, 0.0), (25, -0.25, 0.0),
                (35, -1.0, 0.0), (72, -1.0, 0.0), (87, 1.75, 0.0)],
    "robot_2": [(0, 1.75, 0.0), (10, 1.75, 0.0), (15, 0.25, 0.0), (40, 0.25, 0.0),
                (55, -1.75, 0.0)],
    "robot_3": [(0, 0.0, -1.75), (10, 0.0, -1.75), (15, 0.0, -0.25), (28, 0.0, -0.25),
                (33, 0.0, -1.0), (70, 0.0, -1.0), (85, 0.0, 1.75)],
    "robot_4": [(0, 0.0, 1.75), (10, 0.0, 1.75), (15, 0.0, 0.25), (25, 0.0, 0.25),
                (28, 0.0, 1.2), (55, 0.0, 1.2), (70, 0.0, -1.75)],
}


def _keyframe_position(keys: list[tuple[float, float, float]], t: float) -> tuple[float, float]:
    if t >= keys[-1][0]:
        return keys[-1][1], keys[-1][2]
    for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:], strict=False):
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return x0 + f * (x1 - x0), y0 + f * (y1 - y0)
    return keys[0][1], keys[0][2]


def _ib10_gt(tmp_path: Path, keys: dict, end_sec: float = 100.0, name: str = "gt") -> Path:
    n = round(end_sec / DT) + 1
    tracks = {
        rid: [_keyframe_position(k, i * DT) for i in range(n)] for rid, k in keys.items()
    }
    return _write_gt(tmp_path / name, _frames(tracks), IB10_GOALS)


def _ib10_record(proposed: list[str] | None, executed: list[str]) -> dict:
    # The trigger snapshot: the IB10 GT standoff, where chi ranks robot_4
    # (0.923 m to its pocket) before robot_3 (0.942 m).
    standoff = {
        "robot_1": (-0.2192, -0.0014), "robot_2": (0.33, 0.0158),
        "robot_3": (-0.0208, -0.2583), "robot_4": (0.0045, 0.2773),
    }
    decision = {"congestion_detected": True, "strategy": "junction_clear"}
    if proposed is not None:
        decision["proposed_plan"] = [
            *({"robot_id": r, "action": "reverse"} for r in proposed),
            {"robot_id": "robot_1", "action": "yield"},
            {"robot_id": "robot_2", "action": "cross"},
        ]
    return {
        "decision": decision,
        "grounded_command_present": True,
        "scene": {
            "stamp": 33.9,
            "robots": [
                {"robot_id": r, "x": x, "y": y, "theta": 0.0, "status": "STOPPED"}
                for r, (x, y) in standoff.items()
            ],
        },
        "plan": {
            "provenance": "repaired",
            "legs": [
                *({"robot_id": r, "action": "reverse"} for r in executed),
                {"robot_id": "robot_1", "action": "yield"},
                {"robot_id": "robot_2", "action": "cross"},
            ],
        },
    }


class TestIb10OracleBlock:
    def test_oracle_block_names_the_pairs_and_the_canonical_ordinal(self):
        oracle = load_scenario("intersection_bottleneck")["oracle"]
        assert oracle["correct_strategy"] == "junction_clear"
        assert oracle["recede_pair"] == ["robot_3", "robot_4"]
        assert oracle["inside_pair"] == ["robot_1", "robot_2"]
        assert oracle["jam_robots_in_radius"] == 4
        assert oracle["phase_ordinal"] == ["recede", "cross", "release", "resolved"]


class TestIb10FormedJam:
    def test_designed_jam_passes_the_validity_gate(self, tmp_path):
        result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED))
        jam = result["formed_jam"]
        assert jam["onset_sec"] == pytest.approx(15.0, abs=0.3)
        assert jam["robots_in_radius_at_onset"] == 4
        assert jam["valid"] is True

    def test_a_jam_forming_after_the_window_is_invalid_not_failed(self, tmp_path):
        late = {
            rid: [(t + 30 if t >= 10 else t, x, y) for t, x, y in keys]
            for rid, keys in IB10_DESIGNED.items()
        }
        result = score_ib10(_ib10_gt(tmp_path, late, end_sec=130.0))
        assert result["formed_jam"]["onset_in_window"] is False
        assert result["formed_jam"]["valid"] is False
        assert result["resolved"] is None

    def test_a_three_robot_jam_fails_the_four_robot_gate(self, tmp_path):
        three = dict(IB10_DESIGNED)
        three["robot_4"] = [(0, 0.0, 1.75), (100, 0.0, 1.75)]
        result = score_ib10(_ib10_gt(tmp_path, three))
        assert result["formed_jam"]["robots_in_radius_at_onset"] == 3
        assert result["formed_jam"]["valid"] is False


class TestIb10ChiPair:
    def test_correct_pair_in_chi_order_scores_correct_on_both_plans(self):
        result = score_chi_pair(
            _ib10_record(["robot_4", "robot_3"], ["robot_4", "robot_3"]),
            load_scenario("intersection_bottleneck")["oracle"],
        )
        assert result["chi_order"] == ["robot_4", "robot_3"]
        assert result["proposed_pair_correct"] is True
        assert result["proposed_order_correct"] is True
        assert result["executed_order_correct"] is True
        assert result["yielder"] == "robot_1"

    def test_proposed_order_is_scored_before_repair(self):
        result = score_chi_pair(
            _ib10_record(["robot_3", "robot_4"], ["robot_4", "robot_3"]),
            load_scenario("intersection_bottleneck")["oracle"],
        )
        assert result["proposed_pair_correct"] is True
        assert result["proposed_order_correct"] is False
        assert result["executed_order_correct"] is True

    def test_wrong_recede_pair_is_a_pair_error(self):
        result = score_chi_pair(
            _ib10_record(["robot_1", "robot_2"], ["robot_4", "robot_3"]),
            load_scenario("intersection_bottleneck")["oracle"],
        )
        assert result["proposed_pair_correct"] is False

    def test_strategy_token_only_has_no_proposed_score(self):
        result = score_chi_pair(
            _ib10_record(None, ["robot_4", "robot_3"]),
            load_scenario("intersection_bottleneck")["oracle"],
        )
        assert result["proposed_recede"] is None
        assert result["proposed_pair_correct"] is None
        assert result["executed_pair_correct"] is True

    def test_dispatched_decision_is_the_earliest_junction_clear(self, tmp_path):
        early = _ib10_record(None, ["robot_4", "robot_3"])
        late = {**early, "scene": {**early["scene"], "stamp": 90.0}}
        skip = {"decision": {"congestion_detected": False, "strategy": "none"},
                "grounded_command_present": False, "scene": {"stamp": 1.0}}
        for name, record in (("a.json", late), ("b.json", early), ("c.json", skip)):
            (tmp_path / name).write_text(json.dumps(record))
        found = dispatched_junction_decision(tmp_path)
        assert found["_artifact"] == "b.json"


class TestIb10InsideFirst:
    def test_designed_order_is_inside_first_with_the_yielder_last(self, tmp_path):
        result = score_ib10(_ib10_gt(tmp_path, IB10_DESIGNED))
        order = score_inside_first(
            load_ground_truth(tmp_path / "gt"), load_scenario("intersection_bottleneck"), "robot_1"
        )
        assert order["inside_robots"] == ["robot_2"]
        assert order["inside_first"] is True
        assert order["yielder_last"] is True
        assert order["crossing_order"][0] == "robot_2"
        assert result["all_arrived"] is True
        assert result["resolved"] is True

    def test_a_recede_robot_crossing_before_the_passer_breaks_inside_first(self, tmp_path):
        early = dict(IB10_DESIGNED)
        early["robot_4"] = [(0, 0.0, 1.75), (10, 0.0, 1.75), (15, 0.0, 0.25), (25, 0.0, 0.25),
                            (38, 0.0, -1.75)]
        early["robot_2"] = [(0, 1.75, 0.0), (10, 1.75, 0.0), (15, 0.25, 0.0), (45, 0.25, 0.0),
                            (60, -1.75, 0.0)]
        series = load_ground_truth(_ib10_gt(tmp_path, early))
        order = score_inside_first(series, load_scenario("intersection_bottleneck"), "robot_1")
        assert order["inside_first"] is False

    def test_a_passer_that_never_crosses_leaves_the_order_undecided(self, tmp_path):
        stuck = dict(IB10_DESIGNED)
        stuck["robot_2"] = [(0, 1.75, 0.0), (10, 1.75, 0.0), (15, 0.25, 0.0)]
        series = load_ground_truth(_ib10_gt(tmp_path, stuck))
        order = score_inside_first(series, load_scenario("intersection_bottleneck"), "robot_1")
        assert order["inside_first"] is None


IB10_M5_LOG = """\
[orchestrator_node]: dispatch request=r1 command=r1-junction-recede-robot_4 robot=robot_4 plan_id=1
[orchestrator_node]: junction_clear phase advance command=r1-junction-recede-robot_4 \
completed=True phase_reached=recede done=False
[orchestrator_node]: junction_clear phase advance command=r1-junction-recede-robot_3 \
completed=True phase_reached=cross done=False
[orchestrator_node]: junction_clear phase advance command=r1-junction-cross \
completed=True phase_reached=release done=False
"""


class TestIb10PhaseReached:
    def test_no_dispatch_is_ordinal_zero(self):
        result = phase_reached("nothing here\n")
        assert result["phase_reached"] == "none"
        assert result["phase_ordinal"] == 0

    def test_release_is_ordinal_three(self):
        result = phase_reached(IB10_M5_LOG)
        assert result["phase_reached"] == "release"
        assert result["phase_ordinal"] == 3
        assert result["fallback"] is False

    def test_resolved_is_ordinal_four(self):
        log = IB10_M5_LOG + (
            "[orchestrator_node]: junction_clear phase advance command=r1-junction-release "
            "completed=True phase_reached=resolved done=True\n"
        )
        assert phase_reached(log)["phase_ordinal"] == 4

    def test_fallback_keeps_the_last_phase_and_flags_exhaustion(self):
        log = (
            "dispatch request=r1 command=r1-junction-recede-robot_4 robot=robot_4\n"
            "junction_clear phase advance command=r1-junction-recede-robot_4 completed=True "
            "phase_reached=recede done=False\n"
            "junction_clear phase advance command=r1-junction-recede-robot_3 completed=False "
            "phase_reached=fallback done=False\n"
            "junction_clear fallback exhausted command=r1-fb robots=['robot_1'] "
            "outcome=fallback_exhausted\n"
        )
        result = phase_reached(log)
        assert result["phase_reached"] == "recede"
        assert result["fallback"] is True
        assert result["fallback_exhausted"] is True


class TestIb10ReleaseAttribution:
    def test_clearance_releases_are_an_ordered_release(self):
        log = (
            "crossing_chain gate_admit command=r1-junction-release yielder=robot_3 "
            "passer=robot_4 clear_m=2.650 escort_m=None sim_t=100.000\n"
            "crossing_chain gate_cleared command=r1-junction-release yielder=robot_3 "
            "passer=robot_4 moved_m=2.700 clear_m=2.650 sim_t=150.000\n"
            "crossing_chain gate_release command=r1-junction-release yielder=robot_3 "
            "reason=clearance sim_t=150.100\n"
            "crossing_chain gate_release command=r1-junction-release yielder=robot_1 "
            "reason=clearance sim_t=150.200\n"
            "crossing_chain gate_release command=r1-junction-cross yielder=robot_1 "
            "reason=hold_timer sim_t=90.000\n"
        )
        result = release_attribution(log)
        assert result["release_reason"] == {"robot_3": "clearance", "robot_1": "clearance"}
        assert result["ordered_release"] is True
        assert [e["event"] for e in result["events"]] == [
            "gate_admit", "gate_cleared", "gate_release", "gate_release",
        ]
        assert result["events"][1]["passer"] == "robot_4"

    def test_a_hold_timer_release_is_not_attributable(self):
        log = (
            "crossing_chain gate_release command=r1-junction-release yielder=robot_3 "
            "reason=hold_timer sim_t=150.100\n"
        )
        assert release_attribution(log)["ordered_release"] is False

    def test_no_release_events_is_undecided(self):
        assert release_attribution("")["ordered_release"] is None


class TestIb10Instrumentation:
    def test_an_excursion_past_the_tracked_band_is_flagged(self, tmp_path):
        out = dict(IB10_DESIGNED)
        out["robot_4"] = [*IB10_DESIGNED["robot_4"][:5], (40, 0.0, 2.38), (55, 0.0, 1.2),
                          (70, 0.0, -1.75)]
        result = score_ib10(_ib10_gt(tmp_path, out))
        assert result["tracked_band"]["in_band"] is False
        assert result["tracked_band"]["max_abs_xy"]["robot_4"][1] == pytest.approx(2.38)

    def test_stale_streak_rows_and_span(self, tmp_path):
        lines = []
        for i, status in enumerate(["STOPPED", "STALE", "STALE", "STALE", "STOPPED", "STALE"]):
            lines.append(json.dumps({"scene": {"stamp": 10.0 + i, "robots": [
                {"robot_id": "robot_3", "status": status, "stamp": 10.0},
            ]}}))
        path = tmp_path / "scene.jsonl"
        path.write_text("\n".join(lines) + "\n")
        result = stale_streaks(path)["robot_3"]
        assert result["stale_rows"] == 4
        assert result["longest_streak_rows"] == 3
        assert result["longest_streak_sec"] == 2.0
