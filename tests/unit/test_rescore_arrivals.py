"""Unit tests for the offline arrival re-scoring script (FR5.1.9 follow-up).

Builds a synthetic run directory (M5 log, scene log, ground truth) under
`tmp_path` rather than relying on the git-ignored `data/logs/vm_runs/` runs,
so these tests are self-contained and offline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.rescore_arrivals import (
    find_run_dirs,
    locate_gt_file,
    locate_scene_files,
    nearest_gt_by_position,
    nearest_scene_sample,
    parse_arrival_events,
    parse_session_id,
    score_run,
)

SESSION_ID = "abc123"
GOAL_R1 = (2.5, 0.0)
GOAL_R2 = (-2.5, 0.0)


def _m5_log_line(epoch: float, text: str) -> str:
    return f"[orchestrator_node-1] [INFO] [{epoch:.9f}] [orchestrator_node]: {text}\n"


ArrivalSpec = tuple[float, str, tuple[float, float]]


def _write_m5_log(run_dir: Path, run_id: str, arrivals: list[ArrivalSpec]) -> None:
    lines = [
        _m5_log_line(1000.0, f"session_id={SESSION_ID} run_id={run_id}"),
        _m5_log_line(1005.0, "starting analysis request=r1 robots=['robot_1'] reason=1 stalled"),
    ]
    for ts, robot, goal in arrivals:
        lines.append(_m5_log_line(ts, f"robot {robot} arrived at base goal ({goal[0]}, {goal[1]})"))
    (run_dir / "component_logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "component_logs" / f"{run_id}_m5.log").write_text("".join(lines))


def _write_scene_log(
    run_dir: Path, run_id: str, samples: dict[str, list[tuple[float, float, float, str]]]
) -> None:
    (run_dir / "scene").mkdir(parents=True, exist_ok=True)
    # Interleave robots per timestamp, as the real logger does.
    all_stamps = sorted({s[0] for series in samples.values() for s in series})
    lines = []
    for stamp in all_stamps:
        robots = []
        for robot_id, series in samples.items():
            for s in series:
                if s[0] == stamp:
                    robots.append(
                        {
                            "robot_id": robot_id,
                            "stamp": s[0],
                            "x": s[1],
                            "y": s[2],
                            "status": s[3],
                            "linear_velocity": 0.0,
                            "theta": 0.0,
                        }
                    )
        scene = {
            "dropped_frame": False,
            "frame_id": "overhead_camera",
            "robots": robots,
            "stamp": stamp,
        }
        record = {"run_id": run_id, "scene": scene, "session_id": SESSION_ID, "t": stamp}
        lines.append(json.dumps(record))
    (run_dir / "scene" / f"{SESSION_ID}.jsonl").write_text("\n".join(lines) + "\n")


def _write_ground_truth(
    run_dir: Path, rows: list[tuple[float, dict[str, tuple[float, float]]]]
) -> None:
    (run_dir / "ground_truth").mkdir(parents=True, exist_ok=True)
    lines = []
    for sim_t, positions in rows:
        robots = {}
        for robot_id, (x, y) in positions.items():
            goal = GOAL_R1 if robot_id == "robot_1" else GOAL_R2
            import math

            robots[robot_id] = {
                "x": x,
                "y": y,
                "goal_x": goal[0],
                "goal_y": goal[1],
                "distance_to_goal_m": math.dist((x, y), goal),
                "speed_mps": 0.0,
                "theta": 0.0,
            }
        record = {
            "conflict_active": False,
            "conflict_type": "deadlock",
            "involved_robots": ["robot_1", "robot_2"],
            "min_pairwise_distance_m": 1.0,
            "robot_robot_contacts": [],
            "robot_static_contacts": [],
            "robots": robots,
            "sim_time_sec": sim_t,
        }
        lines.append(json.dumps(record))
    (run_dir / "ground_truth" / "ground_truth.jsonl").write_text("\n".join(lines) + "\n")


def _build_run(
    tmp_path: Path,
    run_id: str,
    arrivals: list[tuple[float, str, tuple[float, float]]],
    scene_samples: dict[str, list[tuple[float, float, float, str]]],
    gt_rows: list[tuple[float, dict[str, tuple[float, float]]]],
) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    _write_m5_log(run_dir, run_id, arrivals)
    _write_scene_log(run_dir, run_id, scene_samples)
    _write_ground_truth(run_dir, gt_rows)
    return run_dir


def test_find_run_dirs_skips_non_stamp_entries(tmp_path: Path) -> None:
    (tmp_path / "20260925_120000").mkdir()
    (tmp_path / "ARM_A_PILOT_SUMMARY.txt").write_text("not a run")
    (tmp_path / "not_a_stamp").mkdir()

    found = find_run_dirs(tmp_path)

    assert [p.name for p in found] == ["20260925_120000"]


def test_parse_arrival_events_extracts_robot_and_goal() -> None:
    text = _m5_log_line(1234.5, "robot robot_1 arrived at base goal (2.5, 0.0)")

    events = parse_arrival_events(text)

    assert len(events) == 1
    assert events[0].robot_id == "robot_1"
    assert events[0].goal == (2.5, 0.0)
    assert events[0].ts == pytest.approx(1234.5)
    assert events[0].kind == "reported"


def test_parse_session_id_reads_the_startup_line() -> None:
    text = _m5_log_line(1000.0, "session_id=deadbeef run_id=20260925_000000")

    assert parse_session_id(text) == "deadbeef"


def test_locate_scene_files_selects_by_session_id_ignoring_stray_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260925_000000"
    (run_dir / "scene").mkdir(parents=True)
    (run_dir / "scene" / "real_session.jsonl").write_text("")
    (run_dir / "scene" / "stray_leftover_session.jsonl").write_text("")

    found = locate_scene_files(run_dir, session_id="real_session")

    assert [p.name for p in found] == ["real_session.jsonl"]


def test_locate_gt_file_finds_nested_scenario_subdirectory(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260925_000000"
    nested = run_dir / "ground_truth" / "some_scenario-seed42-rep000"
    nested.mkdir(parents=True)
    (nested / "ground_truth.jsonl").write_text("")

    found = locate_gt_file(run_dir)

    assert found == nested / "ground_truth.jsonl"


def test_nearest_scene_sample_picks_closest_by_absolute_time() -> None:
    from scripts.rescore_arrivals import SceneSample

    samples = [
        SceneSample(stamp=100.0, x=0.0, y=0.0, status="STOPPED"),
        SceneSample(stamp=110.0, x=1.0, y=0.0, status="STOPPED"),
    ]

    nearest = nearest_scene_sample(samples, ts=108.0)

    assert nearest is not None
    assert nearest.stamp == 110.0


def test_nearest_gt_by_position_returns_closest_row_and_residual() -> None:
    from scripts.rescore_arrivals import GTRow

    rows = [
        GTRow(sim_time_sec=0.0, x=0.0, y=0.0, dist_to_goal_m=2.5, goal=GOAL_R1),
        GTRow(sim_time_sec=10.0, x=2.5, y=0.0, dist_to_goal_m=0.0, goal=GOAL_R1),
    ]

    matched, residual = nearest_gt_by_position(rows, (2.48, 0.0))

    assert matched.sim_time_sec == 10.0
    assert residual == pytest.approx(0.02, abs=1e-6)


def test_score_run_accepts_an_arrival_within_tolerance(tmp_path: Path) -> None:
    run_id = "20260925_000001"
    run_dir = _build_run(
        tmp_path,
        run_id,
        arrivals=[(1010.0, "robot_1", GOAL_R1)],
        scene_samples={"robot_1": [(1009.8, 2.48, 0.0, "STOPPED")]},
        gt_rows=[(10.0, {"robot_1": (2.48, 0.0)})],
    )

    rows, notes = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)

    assert len(rows) == 1
    row = rows[0].values
    assert row["m1_verdict"] == "within_tolerance"
    assert row["flipped"] is False
    assert row["robot_arrived_m1"] is True
    assert row["gt_dist_m"] == pytest.approx(0.02, abs=1e-6)


def test_score_run_flips_an_arrival_reported_but_beyond_tolerance(tmp_path: Path) -> None:
    """Reproduces the motivating case: Nav2/M5 report success, M1 disagrees.

    Mirrors `20260925_124609` robot_2, whose Nav2-reported arrival placed it
    0.59 m from the goal by M1's own estimate.
    """
    run_id = "20260925_000002"
    run_dir = _build_run(
        tmp_path,
        run_id,
        arrivals=[(1010.0, "robot_2", GOAL_R2)],
        scene_samples={"robot_2": [(1009.9, -1.9, -0.26, "STOPPED")]},
        gt_rows=[(10.0, {"robot_2": (-1.96, -0.26)})],
    )

    rows, notes = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)

    assert len(rows) == 1
    row = rows[0].values
    assert row["m1_verdict"] == "beyond_tolerance"
    assert row["flipped"] is True
    assert row["robot_arrived_m1"] is False
    assert row["run_both_arrived_m1"] is False
    # Ground truth agrees the robot is well outside tolerance too.
    assert row["gt_dist_m"] > 0.35


def test_score_run_falls_back_when_m1_estimate_is_too_old(tmp_path: Path) -> None:
    run_id = "20260925_000003"
    run_dir = _build_run(
        tmp_path,
        run_id,
        arrivals=[(1010.0, "robot_1", GOAL_R1)],
        # Nearest scene sample is 5s away: older than max_age_sec=2.0.
        scene_samples={"robot_1": [(1005.0, 2.49, 0.0, "STOPPED")]},
        gt_rows=[(10.0, {"robot_1": (2.49, 0.0)})],
    )

    rows, notes = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)

    row = rows[0].values
    assert row["m1_verdict"] == "stale_estimate"
    # Stale estimates are accepted unverified (legacy pass-through), not a flip.
    assert row["flipped"] is False


def test_score_run_reports_no_scene_log_and_uses_gt_final_row(tmp_path: Path) -> None:
    run_id = "20260925_000004"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    _write_m5_log(run_dir, run_id, arrivals=[(1010.0, "robot_1", GOAL_R1)])
    gt_rows = [(0.0, {"robot_1": (0.0, 0.0)}), (10.0, {"robot_1": (2.5, 0.0)})]
    _write_ground_truth(run_dir, rows=gt_rows)
    (run_dir / "scene").mkdir()  # present but empty: no file for this session

    rows, notes = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)

    assert any("no scene log" in n for n in notes)
    row = rows[0].values
    assert row["no_scene_log"] is True
    assert row["gt_dist_m"] == pytest.approx(0.0, abs=1e-6)


def test_score_run_computes_gt_min_distance_over_whole_run(tmp_path: Path) -> None:
    run_id = "20260925_000005"
    run_dir = _build_run(
        tmp_path,
        run_id,
        # M1's estimate at report time sits near the t=10 position (dist 0.06
        # from goal), not near the run's closest approach at t=5 (dist 0.03).
        arrivals=[(1010.0, "robot_1", GOAL_R1)],
        scene_samples={"robot_1": [(1009.9, 2.44, 0.0, "STOPPED")]},
        gt_rows=[
            (0.0, {"robot_1": (-1.5, 0.0)}),
            (5.0, {"robot_1": (2.47, 0.0)}),  # closest approach: dist 0.03
            (10.0, {"robot_1": (2.44, 0.0)}),  # report-time position: dist 0.06
        ],
    )

    rows, notes = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)

    row = rows[0].values
    # gt_dist_m is the position-matched value at report time...
    assert row["gt_dist_m"] == pytest.approx(0.06, abs=1e-6)
    # ...distinct from gt_min_dist_m, the minimum anywhere in the run.
    assert row["gt_min_dist_m"] == pytest.approx(0.03, abs=1e-6)
