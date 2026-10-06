"""Shared fixtures for the capability-probe test suite.

`synthetic_logs_root` builds a small, synthetic `data/logs/vm_runs`-shaped
tree (decisions + GT + tiny frame PNGs) used by both
`test_build_capability_probe_manifest.py` (the build script's own
scan-to-selection path) and `test_audit_capability_probe_manifest.py` (the
independent post-build audit, which re-reads the same tree from disk). A
shared pytest fixture here -- rather than importing one test module's fixture
into another -- is the standard pattern and avoids the name collisions a
cross-module fixture import creates for static analysis.
"""
import functools
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

# pyproject.toml's `pythonpath` already puts swarm_perception on sys.path for
# pytest; no sys.path surgery needed here. Anchored to this file, not the
# working directory: this module is collected for every one of the suite's
# ~4000 tests (not only the capability-probe ones), so it must not depend on
# pytest being invoked from the repo root.
CAPABILITY_PROBE_CALIBRATION_PATH = str(
    Path(__file__).resolve().parents[2]
    / "ros2_ws" / "src" / "swarm_perception" / "config" / "calibration.yaml"
)


@functools.lru_cache(maxsize=1)
def _calibration():
    # Loaded lazily (only once `synthetic_logs_root` is actually used, not at
    # collection time for every test module in this directory).
    from swarm_perception.calibration import load_calibration

    return load_calibration(CAPABILITY_PROBE_CALIBRATION_PATH)


def _world_at(u: float, v: float) -> dict[str, float]:
    """World-frame `{"x", "y"}` for a chosen pixel target, via the real calibration.

    Deriving fixture positions from pixel targets (rather than guessing world
    coordinates and hoping they land where intended) keeps them legible: each
    robot's placement relative to grid cells, badges, and frame edges is
    chosen in pixel space, where this battery's margins are also defined.
    """
    from swarm_perception.geometry import pixel_to_world

    x, y = pixel_to_world((u, v), _calibration().homography)
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
        gt_lines.append(json.dumps({"sim_time_sec": stamp, "robots": robots}))
        image = np.full((960, 1280, 3), 180, dtype=np.uint8)
        cv2.imwrite(str(episode_dir / "frames" / f"{request_id}.png"), image)
    (episode_dir / "gt" / "ground_truth.jsonl").write_text(
        "\n".join(gt_lines) + "\n", encoding="utf-8"
    )
    return episode_dir


def _robots_two(row_v: int, step: int) -> dict[str, dict[str, float]]:
    # robot_1 in cell 0 (top-left), robot_2 in cell 2 (top-right), both well
    # clear of their cell's centre (where a letter badge is drawn), of every
    # cell boundary, and of the frame edge; `step` walks each 15px further
    # from its own corner (still inside the same safe pocket) so every
    # episode is a distinct scene configuration -- the build script dedupes
    # candidates with identical robot layouts (2026-10-02, third correction).
    return {
        "robot_1": _world_at(90 + 15 * step, row_v),
        "robot_2": _world_at(1190 - 15 * step, row_v),
    }


def _robots_three(row_v: int, step: int) -> dict[str, dict[str, float]]:
    robots = _robots_two(row_v, step)
    # cell 7 (bottom-middle), equally clear of its centre/boundaries/edges.
    robots["robot_3"] = _world_at(550, 710 + 15 * step)
    return robots


@pytest.fixture
def synthetic_logs_root(tmp_path):
    for i in range(4):
        _write_episode(
            tmp_path, "run_a", f"ep_{i}", [(f"req_a{i}", _robots_two(90, i), float(i))],
            scenario="scene_a",
        )
    for i in range(4):
        _write_episode(
            tmp_path, "run_b", f"ep_{i}", [(f"req_b{i}", _robots_two(230, i), float(i))],
            scenario="scene_b",
        )
    for i in range(4):
        _write_episode(
            tmp_path, "run_c", f"ep_{i}", [(f"req_c{i}", _robots_three(90, i), float(i))],
            scenario="scene_c",
        )
    return tmp_path


@pytest.fixture(autouse=True)
def _no_real_retry_backoff(monkeypatch):
    """Make the shared M2 retry policy's default sleep a no-op in unit tests.

    The policy (conformance ruling F02) waits seconds between retryable
    attempts; tests that exercise retries would otherwise sleep for real.
    Tests that assert on the waits inject their own `RetryPolicy(sleep=...)`.
    """
    monkeypatch.setattr("reasoning.vlm.retry_policy._sleep_impl", lambda seconds: None)
