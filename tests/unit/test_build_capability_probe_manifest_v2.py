"""Battery-v2 build + audit on a synthetic two-episode (trails off/on) log tree."""

from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from reasoning.vlm.capability_probes import dynamics as dyn
from scripts.audit_capability_probe_manifest import audit_manifest_v2
from scripts.build_capability_probe_manifest_v2 import build_manifest
from tests.unit.conftest import CAPABILITY_PROBE_CALIBRATION_PATH as _CALIBRATION_PATH

_T_END = 45.0
_FRAME_TIMES = [float(t) for t in range(1, 35)]


def _pose(rid: str, t: float) -> tuple[float, float, float]:
    # robot_1 drives at a parked robot_2 and stops 0.35 m short (conflict
    # "yes", goal arrival ~21.7 s); robot_3 drives a parallel lane 1.5 m away
    # (conflict "no" with robot_1, goal arrival ~17.3 s).
    if rid == "robot_1":
        return -2.0 + 0.15 * min(max(t - 2.0, 0.0), 21.0), 0.0, 0.0
    if rid == "robot_2":
        return 1.5, 0.0, math.pi
    return -2.0 + 0.15 * min(max(t - 2.0, 0.0), 2.5 / 0.15), 1.5, 0.0


_GOALS = {"robot_1": (1.15, 0.0), "robot_2": (2.5, 0.0), "robot_3": (0.5, 1.5)}


def _gt_rows(shift_robot_3_m: float = 0.0) -> list[dict]:
    rows = []
    for i in range(int(_T_END * 10) + 1):
        t = round(i * 0.1, 4)
        robots = {}
        for rid in _GOALS:
            x, y, theta = _pose(rid, t)
            if rid == "robot_3":
                y += shift_robot_3_m
            gx, gy = _GOALS[rid]
            robots[rid] = {
                "x": x,
                "y": y,
                "theta": theta,
                "speed_mps": 0.0,
                "goal_x": gx,
                "goal_y": gy,
                "distance_to_goal_m": math.hypot(gx - x, gy - y),
            }
        rows.append({"sim_time_sec": t, "robots": robots})
    return rows


def _status(rid: str, t: float) -> str:
    (x0, y0, _), (x1, y1, _) = _pose(rid, t - 0.5), _pose(rid, t)
    speed = math.hypot(x1 - x0, y1 - y0) / 0.5
    if speed >= dyn.MOVING_MIN_SPEED_MPS:
        return "MOVING"
    return "STOPPED" if speed <= dyn.STATIONARY_MAX_SPEED_MPS else "SLOW"


def _write_episode(root: Path, name: str, overlays: list[str], m5_log: str = "") -> Path:
    episode = root / "harvest" / name
    (episode / "gt").mkdir(parents=True)
    snaps = episode / "snapshots"
    snaps.mkdir()
    with (episode / "gt" / "ground_truth.jsonl").open("w") as handle:
        for row in _gt_rows():
            handle.write(json.dumps(row) + "\n")
    (episode / "gt" / "run_manifest.json").write_text(json.dumps({"scenario": "synthetic_lane"}))
    (episode / "m5.log").write_text(m5_log)
    image = np.zeros((960, 1280, 3), dtype=np.uint8)
    with (
        (snaps / "frames.jsonl").open("w") as frames,
        (snaps / "scene_state.jsonl").open("w") as states,
    ):
        for t in _FRAME_TIMES:
            name_png = f"annotated_{t:08.2f}.png"
            cv2.imwrite(str(snaps / name_png), image)
            frames.write(
                json.dumps(
                    {
                        "file": name_png,
                        "topic": "annotated",
                        "stamp_sec": int(t),
                        "stamp_nanosec": 0,
                    }
                )
                + "\n"
            )
            robots = []
            for rid in _GOALS:
                x, y, theta = _pose(rid, t)
                robots.append(
                    {"robot_id": rid, "x": x, "y": y, "theta": theta, "status": _status(rid, t)}
                )
            diagnostics = {"annotation_overlays": overlays} if overlays else {}
            states.write(
                json.dumps({"stamp": t, "robots": robots, "diagnostics": diagnostics}) + "\n"
            )
    return episode


@pytest.fixture
def v2_logs_root(tmp_path: Path) -> Path:
    _write_episode(tmp_path, "off", [])
    _write_episode(tmp_path, "on", ["motion_trails"])
    return tmp_path


def _build(root: Path, **overrides):
    kwargs = {"seed": 7, "target_main": 10, "target_pairs": 10, "max_per_scene": 10}
    kwargs.update(overrides)
    return build_manifest(root, _CALIBRATION_PATH, **kwargs)


def test_build_is_deterministic(v2_logs_root):
    first, _, _ = _build(v2_logs_root)
    second, _, _ = _build(v2_logs_root)
    assert first.model_dump_json() == second.model_dump_json()


def test_every_type_yields_main_and_pair_items(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    for probe_type in ("motion_direction", "conflict_prediction", "temporal_order"):
        assert any(i.probe_type == probe_type and i.subset == "main" for i in manifest.items)
        assert any(i.probe_type == probe_type and i.subset == "trails_pair" for i in manifest.items)


def test_main_items_are_trails_off_only(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    assert {i.frame_condition for i in manifest.items if i.subset == "main"} == {"trails_off"}


def test_pairs_share_question_answer_and_lettering_seed(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    pairs: dict[str, list] = {}
    for item in manifest.items:
        if item.pair_id:
            pairs.setdefault(item.pair_id, []).append(item)
    assert pairs
    for off, on in (sorted(m, key=lambda i: i.frame_condition) for m in pairs.values()):
        assert (off.frame_condition, on.frame_condition) == ("trails_off", "trails_on")
        assert off.run_id != on.run_id
        assert (off.question, off.options, off.correct_answer, off.seed) == (
            on.question,
            on.options,
            on.correct_answer,
            on.seed,
        )


def test_conflict_items_are_balanced_yes_no(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    main = [
        i for i in manifest.items if i.subset == "main" and i.probe_type == "conflict_prediction"
    ]
    answers = [i.correct_answer for i in main]
    assert answers.count("yes") == answers.count("no") > 0


def test_conflict_answers_match_the_synthetic_geometry(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    for item in manifest.items:
        if item.probe_type != "conflict_prediction":
            continue
        expected = "yes" if item.question_key == "robot_1|robot_2" else "no"
        assert item.correct_answer == expected


def test_temporal_goal_items_name_the_earlier_arrival(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    goal_items = [i for i in manifest.items if i.question_key == "goal:robot_1|robot_3"]
    assert goal_items
    assert {i.correct_answer for i in goal_items} == {"robot_3"}


def test_fresh_build_passes_the_audit(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    assert audit_manifest_v2(manifest, v2_logs_root, _CALIBRATION_PATH) == {}


def test_audit_catches_changed_ground_truth(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    gt = v2_logs_root / "harvest" / "off" / "gt" / "ground_truth.jsonl"
    with gt.open("w") as handle:
        for row in _gt_rows(shift_robot_3_m=-1.2):
            handle.write(json.dumps(row) + "\n")
    failures = audit_manifest_v2(manifest, v2_logs_root, _CALIBRATION_PATH)
    assert failures


def test_audit_catches_a_drifted_frame(v2_logs_root):
    manifest, _, _ = _build(v2_logs_root)
    item = next(i for i in manifest.items if i.subset == "main")
    path = v2_logs_root / item.frame_relpath
    cv2.imwrite(str(path), np.full((960, 1280, 3), 9, dtype=np.uint8))
    failures = audit_manifest_v2(manifest, v2_logs_root, _CALIBRATION_PATH)
    assert any("materialization" in f for f in failures[item.item_id])


def test_command_window_excludes_conflict_items_in_its_horizon(tmp_path):
    # Analysis at wall 1000 <- decision stamp 10.0; resolution maps to ~20 s.
    prefix = "[orchestrator_node-1] [INFO] [{}] [orchestrator_node]: "
    log = (
        prefix.format("1000.000000000") + "starting analysis request=ab12 robots=[] reason=x\n"
        + prefix.format("1000.500000000")
        + "dispatch request=ab12 command=ab12-yield robot=robot_1 plan_id=1\n"
        + prefix.format("1010.000000000") + "command ab12-yield resolved status=completed\n"
    )
    episode = _write_episode(tmp_path, "off", [], m5_log=log)
    (episode / "decisions").mkdir()
    (episode / "decisions" / "ab12.json").write_text(
        json.dumps({"request_id": "ab12", "scene": {"stamp": 10.0, "robots": []}})
    )
    manifest, drops, _ = _build(tmp_path)
    assert drops["conflict_prediction:command_in_horizon"] > 0
    window_end = 10.0 + 10.0 + dyn.COMMAND_END_SLACK_SEC  # wall_to_sim extrapolates at RTF 1
    for item in manifest.items:
        if item.probe_type == "conflict_prediction":
            t = item.sim_time_sec
            assert t + dyn.CONFLICT_HORIZON_SEC < 10.0 or t > window_end


def test_grid_drawn_frames_are_never_used(tmp_path):
    _write_episode(tmp_path, "grid", ["metric_grid", "motion_trails"])
    _write_episode(tmp_path, "off", [])
    manifest, drops, _ = _build(tmp_path)
    assert drops["frame:metric_grid_drawn"] == len(_FRAME_TIMES)
    assert all("grid" not in i.run_id for i in manifest.items)


def _calibration_homography():
    from swarm_perception.calibration import load_calibration

    return load_calibration(_CALIBRATION_PATH).homography


def test_v2_edge_gate_keeps_a_fully_drawn_robot_near_the_edge():
    from reasoning.vlm.capability_probes.episode_v2 import scene_is_legible_v2

    robots = {"robot_1": {"status": "STOPPED"}, "robot_2": {"status": "STOPPED"}}
    # u = 1218: inside v1's 70 px margin, but every drawn rect ends <= 1253.
    pixels = {"robot_1": (1218, 480), "robot_2": (640, 480)}
    assert scene_is_legible_v2(robots, pixels, 1280, 960, _calibration_homography())


def test_v2_edge_gate_drops_a_clipped_label():
    from reasoning.vlm.capability_probes.episode_v2 import scene_is_legible_v2

    robots = {"robot_1": {"status": "STOPPED"}, "robot_2": {"status": "STOPPED"}}
    pixels = {"robot_1": (1250, 480), "robot_2": (640, 480)}
    assert not scene_is_legible_v2(robots, pixels, 1280, 960, _calibration_homography())


def test_v2_legibility_keeps_v1_separation_and_stale_rules():
    from reasoning.vlm.capability_probes.episode_v2 import scene_is_legible_v2

    h = _calibration_homography()
    close = {"robot_1": (600, 480), "robot_2": (650, 480)}
    stopped = {"robot_1": {"status": "STOPPED"}, "robot_2": {"status": "STOPPED"}}
    assert not scene_is_legible_v2(stopped, close, 1280, 960, h)
    stale = {"robot_1": {"status": "STALE"}, "robot_2": {"status": "STOPPED"}}
    far = {"robot_1": (300, 480), "robot_2": (900, 480)}
    assert not scene_is_legible_v2(stale, far, 1280, 960, h)
