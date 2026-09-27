"""Unit tests for the offline arrival re-scoring script (FR5.1.9 follow-up).

Builds a synthetic run directory (M5 log, scene log, ground truth) under
`tmp_path` rather than relying on the git-ignored `data/logs/vm_runs/` runs,
so these tests are self-contained and offline.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

import scripts.rescore_arrivals as rescore_arrivals
from scripts.rescore_arrivals import (
    ClockReconciliationError,
    ObstacleBox,
    detect_clock_era,
    find_run_dirs,
    locate_gt_file,
    locate_scene_files,
    nearest_gt_by_position,
    nearest_scene_sample,
    overlapping_obstacle,
    parse_arrival_events,
    parse_session_id,
    score_run,
    stamp_to_monotonic,
)

SESSION_ID = "abc123"
GOAL_R1 = (2.5, 0.0)
GOAL_R2 = (-2.5, 0.0)
# The _bshort west variant: robot_2's goal is robot_1's spawn, 0.20 m in front
# of a 0.3 m box spanning x in [-2.00, -1.70].
BSHORT_GOAL_R2 = (-1.5, 0.0)
BLOCKER_WEST = {
    "obstacle_id": "blocker_west",
    "pose": {"x": -1.85, "y": 0.0, "yaw_rad": 0.0},
    "size": {"x_m": 0.3, "y_m": 0.3, "z_m": 0.5},
}


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
    run_dir: Path,
    run_id: str,
    samples: dict[str, list[tuple[float, float, float, str]]],
    t_of=lambda stamp: stamp,
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
        record = {"run_id": run_id, "scene": scene, "session_id": SESSION_ID, "t": t_of(stamp)}
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


def _write_scenario(
    run_dir: Path, scenarios_dir: Path, name: str, static_obstacles: list[dict]
) -> None:
    # extract_metadata reads the scenario name from a top-level launcher log.
    (run_dir / "launcher.log").write_text(f"starting Isaac Sim {name} (headless)\n")
    family_dir = scenarios_dir / "family"
    family_dir.mkdir(parents=True, exist_ok=True)
    (family_dir / f"{name}.yaml").write_text(
        yaml.safe_dump({"name": name, "static_obstacles": static_obstacles})
    )


def _score_bshort_arrival(
    tmp_path: Path, m1_xy: tuple[float, float], static_obstacles: list[dict]
) -> tuple[dict, list[str]]:
    run_id = "20260926_000001"
    run_dir = _build_run(
        tmp_path,
        run_id,
        arrivals=[(1010.0, "robot_2", BSHORT_GOAL_R2)],
        scene_samples={"robot_2": [(1009.9, m1_xy[0], m1_xy[1], "STOPPED")]},
        gt_rows=[(10.0, {"robot_2": m1_xy})],
    )
    scenarios_dir = tmp_path / "scenarios"
    _write_scenario(
        run_dir, scenarios_dir, "head_on_asymmetric_w0p2_eopen_bshort_o0", static_obstacles
    )

    rows, notes = score_run(
        run_dir, tolerance_m=0.35, max_age_sec=2.0, scenarios_dir=scenarios_dir
    )

    assert len(rows) == 1
    return rows[0].values, notes


def test_score_run_flags_box_overlap_without_changing_the_verdict(tmp_path: Path) -> None:
    # 0.10 m short of the goal is inside tolerance, but the centre is 0.10 m
    # from the near face, closer than ROBOT_HALF_WIDTH_M.
    row, notes = _score_bshort_arrival(tmp_path, (-1.6, 0.0), [BLOCKER_WEST])

    assert row["m1_verdict"] == "within_tolerance"
    assert row["flipped"] is False
    assert row["robot_arrived_m1"] is True
    assert row["box_overlap"] is True
    assert row["box_overlap_obstacle"] == "blocker_west"
    assert any(n.startswith("WARNING robot_2") and "blocker_west" in n for n in notes)


def test_score_run_reports_a_clear_pose_as_no_overlap(tmp_path: Path) -> None:
    row, notes = _score_bshort_arrival(tmp_path, (-1.45, 0.0), [BLOCKER_WEST])

    assert row["m1_verdict"] == "within_tolerance"
    assert row["box_overlap"] is False
    assert row["box_overlap_obstacle"] is None
    assert not any(n.startswith("WARNING") for n in notes)


def test_score_run_leaves_box_overlap_unset_without_static_obstacles(tmp_path: Path) -> None:
    row, notes = _score_bshort_arrival(tmp_path, (-1.6, 0.0), [])

    assert row["m1_verdict"] == "within_tolerance"
    assert row["box_overlap"] is None
    assert row["box_overlap_obstacle"] is None


def test_overlapping_obstacle_uses_the_box_frame_for_a_rotated_box() -> None:
    # A 1.0 x 0.2 m box rotated 90 degrees extends along y, not x.
    box = ObstacleBox(
        obstacle_id="rack", x=0.0, y=0.0, yaw_rad=math.pi / 2, half_x_m=0.5, half_y_m=0.1
    )

    assert overlapping_obstacle((0.0, 0.6), [box], half_width_m=0.175) == "rack"
    assert overlapping_obstacle((0.6, 0.0), [box], half_width_m=0.175) is None


# ---- clock eras (post-97634be sim-time scene stamps) ----

# Shaped like `simtime_shadow_val/20260927_081722` (S1): scene stamps are sim
# seconds (~10-300), `t` is M5's monotonic clock (~2.2e5), M5 log times are
# wall epochs (~1.79e9), and the sim runs at ~0.41x real time.
SIM_OFFSET = 1_790_272_483.644
SIM_T0 = 224_625.0
SIM_RTF = 0.41
SIM_RUN_ID = "20260927_081722"


def _sim_t(stamp: float) -> float:
    return SIM_T0 + (stamp - 10.0) / SIM_RTF


def _sim_wall(stamp: float) -> float:
    return SIM_OFFSET + _sim_t(stamp)


def _build_sim_run(
    tmp_path: Path, anchor_stamps: tuple[float, ...] = (50.0, 120.0), anchor_skew: float = 0.005
) -> Path:
    """S1-shaped run: robot_1 sits 0.05 m short of its goal from sim 100 s on."""
    run_dir = tmp_path / SIM_RUN_ID
    run_dir.mkdir()
    lines = [_m5_log_line(_sim_wall(5.0), f"session_id={SESSION_ID} run_id={SIM_RUN_ID}")]
    (run_dir / "decisions").mkdir()
    for i, stamp in enumerate(anchor_stamps):
        request = f"req{i}"
        lines.append(
            _m5_log_line(
                _sim_wall(stamp) + anchor_skew,
                f"starting analysis request={request} robots=['robot_1'] reason=stalled",
            )
        )
        (run_dir / "decisions" / f"{request}.json").write_text(
            json.dumps({"request_id": request, "scene": {"stamp": stamp, "robots": []}})
        )
    lines.append(
        _m5_log_line(_sim_wall(150.0) + 0.05, "robot robot_1 arrived at base goal (2.5, 0.0)")
    )
    (run_dir / f"fc_{SIM_RUN_ID}_m5.log").write_text("".join(lines))
    series = [
        (float(s), 2.45 if s >= 100 else -1.5 + 0.04 * (s - 10), 0.0, "STOPPED")
        for s in range(10, 301)
    ]
    _write_scene_log(run_dir, SIM_RUN_ID, {"robot_1": series}, t_of=_sim_t)
    _write_ground_truth(
        run_dir, [(0.0, {"robot_1": (-1.5, 0.0)}), (150.0, {"robot_1": (2.45, 0.0)})]
    )
    return run_dir


def test_detect_clock_era_returns_wall_when_stamps_overlap_log_span() -> None:
    assert detect_clock_era([1009.8, 1010.5], [1000.0, 1010.0]) == "wall"


def test_detect_clock_era_returns_sim_when_stamps_are_far_from_log_span() -> None:
    assert detect_clock_era([10.9, 150.0, 300.3], [1.79e9, 1.79e9 + 400.0]) == "sim"


def test_detect_clock_era_returns_wall_when_log_ends_before_scene_log() -> None:
    # bshort_gpt4o/20260926_204952: captured M5 log stops ~430 s before the
    # scene log's last row, so most scene stamps lie beyond the log span.
    stamps = [1000.0 + s for s in range(0, 700)]
    assert detect_clock_era(stamps, [1000.0, 1250.0]) == "wall"


def test_stamp_to_monotonic_interpolates_between_logged_rows() -> None:
    clock = [(10.0, 100.0), (11.0, 102.0)]
    assert stamp_to_monotonic(clock, 10.25) == pytest.approx(100.5)


def test_stamp_to_monotonic_returns_none_outside_range_without_extrapolation() -> None:
    clock = [(10.0, 100.0), (11.0, 102.0)]
    assert stamp_to_monotonic(clock, 9.0) is None
    assert stamp_to_monotonic(clock, 9.0, extrapolate=True) == pytest.approx(98.0)


def test_score_run_maps_sim_time_stamps_to_wall_clock(tmp_path: Path) -> None:
    rows, notes = score_run(_build_sim_run(tmp_path), tolerance_m=0.35, max_age_sec=2.0)

    row = rows[0].values
    assert row["clock_era"] == "sim"
    assert row["m1_verdict"] == "within_tolerance"
    assert row["m1_estimate_x"] == pytest.approx(2.45)
    # Nearest mapped sample is within one sim step (1 sim-s = 2.44 wall-s) / 2.
    assert row["m1_estimate_age_sec"] < 1.3
    assert any("sim-time scene stamps mapped" in n for n in notes)


def test_score_run_records_derived_wall_offset(tmp_path: Path) -> None:
    rows, _ = score_run(_build_sim_run(tmp_path), tolerance_m=0.35, max_age_sec=2.0)

    row = rows[0].values
    # Derived from the run's own analysis anchors, not hardcoded: the true
    # offset plus the 5 ms logging skew.
    assert row["clock_offset_sec"] == pytest.approx(SIM_OFFSET + 0.005, abs=1e-3)
    assert row["clock_anchor_count"] == 2
    assert row["clock_anchor_spread_sec"] == pytest.approx(0.0, abs=1e-3)


def test_score_run_leaves_wall_era_stamps_unmapped(tmp_path: Path) -> None:
    run_dir = _build_run(
        tmp_path,
        "20260925_000006",
        arrivals=[(1010.0, "robot_1", GOAL_R1)],
        scene_samples={"robot_1": [(1009.8, 2.48, 0.0, "STOPPED")]},
        gt_rows=[(10.0, {"robot_1": (2.48, 0.0)})],
    )

    row = score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)[0][0].values

    assert row["clock_era"] == "wall"
    assert row["clock_offset_sec"] is None
    assert row["m1_estimate_age_sec"] == pytest.approx(0.2)


def test_score_run_raises_instead_of_stale_rows_when_mapping_is_bypassed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Silent-corruption regression (F4): raw sim stamps vs wall events.

    With the era forced to "wall" the run is joined on raw stamps, exactly as
    the pre-fix script did; it must abort, never emit `stale_estimate` rows.
    """
    run_dir = _build_sim_run(tmp_path)
    monkeypatch.setattr(rescore_arrivals, "detect_clock_era", lambda *_: "wall")

    with pytest.raises(ClockReconciliationError, match="not on one clock"):
        score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)


def test_score_run_raises_when_sim_era_has_no_clock_anchors(tmp_path: Path) -> None:
    run_dir = _build_sim_run(tmp_path, anchor_stamps=())

    with pytest.raises(ClockReconciliationError, match="no clock anchor"):
        score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)


def test_score_run_raises_when_clock_anchors_disagree(tmp_path: Path) -> None:
    run_dir = _build_sim_run(tmp_path, anchor_stamps=(50.0, 120.0, 200.0))
    # Point two of three artifacts at scenes 30 and 60 sim-s away from the
    # ones their log lines were written for.
    for request, stamp in (("req1", 150.0), ("req2", 140.0)):
        (run_dir / "decisions" / f"{request}.json").write_text(
            json.dumps({"scene": {"stamp": stamp}})
        )

    with pytest.raises(ClockReconciliationError, match="disagree"):
        score_run(run_dir, tolerance_m=0.35, max_age_sec=2.0)


def test_main_aborts_without_writing_csv_on_clock_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    _build_sim_run(runs_dir, anchor_stamps=())
    out = tmp_path / "out.csv"
    monkeypatch.setattr(
        "sys.argv", ["rescore_arrivals.py", "--runs-dir", str(runs_dir), "--out", str(out)]
    )

    assert rescore_arrivals.main() == 2
    assert not out.exists()


_S1_RUN = (
    Path(__file__).resolve().parents[2] / "data/logs/vm_runs/simtime_shadow_val" / SIM_RUN_ID
)


@pytest.mark.skipif(not _S1_RUN.is_dir(), reason="git-ignored S1 validation run not present")
def test_score_run_scores_real_s1_run_within_tolerance() -> None:
    rows, _ = score_run(_S1_RUN, tolerance_m=0.35, max_age_sec=2.0)

    assert [r.values["m1_verdict"] for r in rows] == ["within_tolerance"] * 2
    assert rows[0].values["clock_offset_sec"] == pytest.approx(1_790_272_483.644, abs=0.05)
