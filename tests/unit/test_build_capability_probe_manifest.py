"""End-to-end manifest building from a synthetic `data/logs/vm_runs`-shaped tree.

Exercises the real scan -> GT-match -> candidate -> balanced-selection path
(`scripts/build_capability_probe_manifest.py`) against fixture decisions/GT
rather than the real (gitignored) run logs, so this stays a fast, offline
unit test. Uses the repository's own calibration file (checked in, not
gitignored) for a real homography.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path("ros2_ws/src/swarm_perception").resolve()))
from swarm_perception.calibration import load_calibration  # noqa: E402
from swarm_perception.geometry import pixel_to_world  # noqa: E402

from scripts.build_capability_probe_manifest import build_manifest  # noqa: E402

_CALIBRATION_PATH = "ros2_ws/src/swarm_perception/config/calibration.yaml"
_CALIBRATION = load_calibration(_CALIBRATION_PATH)


def _world_at(u: float, v: float) -> dict[str, float]:
    """World-frame `{"x", "y"}` for a chosen pixel target, via the real calibration.

    Deriving fixture positions from pixel targets (rather than guessing world
    coordinates and hoping they land where intended) keeps them legible: each
    robot's placement relative to grid cells, badges, and frame edges is
    chosen in pixel space, where this battery's margins are also defined.
    """
    x, y = pixel_to_world((u, v), _CALIBRATION.homography)
    return {"x": x, "y": y}


def _write_episode(root, run_name, episode_name, robots_by_request, scenario="synthetic_scene"):
    episode_dir = root / run_name / episode_name
    (episode_dir / "decisions").mkdir(parents=True)
    (episode_dir / "gt").mkdir(parents=True)
    (episode_dir / "frames").mkdir(parents=True)
    (episode_dir / "gt" / "run_manifest.json").write_text(
        json.dumps({"scenario": scenario}), encoding="utf-8"
    )

    gt_lines = []
    for request_id, robots, stamp in robots_by_request:
        decision = {
            "request_id": request_id,
            "scene": {
                "stamp": stamp,
                "robots": [
                    {"robot_id": rid, "x": pos["x"], "y": pos["y"]} for rid, pos in robots.items()
                ],
            },
        }
        (episode_dir / "decisions" / f"{request_id}.json").write_text(
            json.dumps(decision), encoding="utf-8"
        )
        gt_lines.append(
            json.dumps({"sim_time_sec": stamp, "robots": robots})
        )
        image = np.full((960, 1280, 3), 180, dtype=np.uint8)
        cv2.imwrite(str(episode_dir / "frames" / f"{request_id}.png"), image)
    (episode_dir / "gt" / "ground_truth.jsonl").write_text(
        "\n".join(gt_lines) + "\n", encoding="utf-8"
    )
    return episode_dir


@pytest.fixture
def synthetic_logs_root(tmp_path):
    # Pixel targets, not hand-derived world coordinates: each chosen to clear
    # every build-script margin at once on a 1280x960 frame -- >=70px from
    # every frame edge, >=60px from a grid-cell boundary, and far enough from
    # every cell's centre (where a letter badge is drawn) and from the other
    # robots that no occlusion or minimum-separation check can trip.
    robots_two = {
        "robot_1": _world_at(120, 100),  # left side, top row
        "robot_2": _world_at(1150, 100),  # right side, top row
    }
    robots_three = {
        "robot_1": _world_at(120, 100),
        "robot_2": _world_at(1150, 100),
        "robot_3": _world_at(560, 850),  # bottom row, away from both others
    }
    for i in range(4):
        _write_episode(
            tmp_path, "run_a", f"ep_{i}", [(f"req_a{i}", robots_two, float(i))],
            scenario="scene_a",
        )
    for i in range(4):
        _write_episode(
            tmp_path, "run_b", f"ep_{i}", [(f"req_b{i}", robots_two, float(i))],
            scenario="scene_b",
        )
    for i in range(4):
        _write_episode(
            tmp_path, "run_c", f"ep_{i}", [(f"req_c{i}", robots_three, float(i))],
            scenario="scene_c",
        )
    return tmp_path


class TestBuildManifest:
    def test_produces_items_spanning_at_least_three_scenes(self, synthetic_logs_root):
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        scenarios = {item.scenario for item in manifest.items}
        assert len(scenarios) >= 3

    def test_produces_every_probe_type_that_has_eligible_candidates(self, synthetic_logs_root):
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        probe_types = {item.probe_type for item in manifest.items}
        # nearest_first needs >=3 robots: only scene_c qualifies.
        assert probe_types == {"robot_count", "left_right", "locate_robot", "nearest_first"}

    def test_same_seed_is_reproducible(self, synthetic_logs_root):
        first, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=5, target_per_type=10, max_per_scene=2
        )
        second, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=5, target_per_type=10, max_per_scene=2
        )
        assert first == second

    def test_different_seed_can_select_differently(self, synthetic_logs_root):
        first, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=5, target_per_type=2, max_per_scene=1
        )
        second, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=6, target_per_type=2, max_per_scene=1
        )
        first_ids = {(i.run_id, i.request_id, i.probe_type) for i in first.items}
        second_ids = {(i.run_id, i.request_id, i.probe_type) for i in second.items}
        assert first_ids != second_ids

    def test_every_item_passes_its_own_schema_validation(self, synthetic_logs_root):
        # Construction above already validates each ProbeItem; this just
        # confirms the manifest as a whole round-trips through JSON.
        from reasoning.vlm.capability_probes.models import ProbeManifest

        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        restored = ProbeManifest.model_validate_json(manifest.model_dump_json())
        assert restored == manifest
