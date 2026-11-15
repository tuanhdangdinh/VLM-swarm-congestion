import copy
import hashlib
import json
import math

import pytest
import yaml

from scripts.recompute_gt_contacts import BundleError, main, recompute_bundle
from tests.unit.test_m6_config import VALID_HEAD_ON


def _scenario_yaml() -> dict:
    data = copy.deepcopy(VALID_HEAD_ON)
    data["aisle_barrier"] = None
    data["rack_clearance"] = {"x_min_m": -2.5, "x_max_m": 2.5, "y_min_m": -1.8, "y_max_m": 1.8}
    data["static_obstacles"] = [
        {
            "obstacle_id": "obstacle_2",
            "pose": {"x": 0.525, "y": -0.1, "yaw_rad": 0.0},
            "size": {"x_m": 0.55, "y_m": 1.6, "z_m": 0.3},
        }
    ]
    return data


def _bundle(tmp_path, robot_1_x_by_row):
    bundle = tmp_path / "bundle"
    (bundle / "gt").mkdir(parents=True)
    (bundle / "scenario.yaml").write_text(yaml.safe_dump(_scenario_yaml()))
    lines = []
    for i, x in enumerate(robot_1_x_by_row):
        robots = {
            "robot_1": {"x": x, "y": 0.572, "theta": round(math.pi, 4), "speed_mps": 0.0},
            "robot_2": {"x": -2.0, "y": 0.0, "theta": 0.0, "speed_mps": 0.0},
        }
        lines.append(json.dumps({
            "sim_time_sec": round(0.1 * i, 4), "robots": robots,
            "robot_static_contacts": [], "robot_robot_contacts": [],
        }))
    (bundle / "gt" / "ground_truth.jsonl").write_text("\n".join(lines) + "\n")
    return bundle


def _digest(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_recompute_classifies_sustained_when_pinned_for_over_a_second(tmp_path):
    bundle = _bundle(tmp_path, [1.2] * 3 + [0.838] * 15 + [1.2] * 3)
    summary = recompute_bundle(bundle)
    pair = summary["static_pairs"]["robot_1|obstacle_2"]
    assert pair["verdict"] == "sustained_contact"
    assert pair["rows_in_contact"] == 15
    assert pair["first_sim_s"] == pytest.approx(0.3)


def test_recompute_classifies_graze_when_contact_is_brief(tmp_path):
    bundle = _bundle(tmp_path, [1.2] * 3 + [0.841] * 2 + [1.2] * 3)
    summary = recompute_bundle(bundle)
    assert summary["static_verdict"] == "brief_graze"
    pair = summary["static_pairs"]["robot_1|obstacle_2"]
    assert pair["min_gap_m"] == pytest.approx(0.003, abs=2e-4)


def test_recompute_reports_clear_with_minimum_gap_when_never_close(tmp_path):
    bundle = _bundle(tmp_path, [1.2] * 5)
    summary = recompute_bundle(bundle)
    assert summary["static_verdict"] == "clear"
    assert summary["robot_min_static_gap"]["robot_1"]["obstacle_id"] == "obstacle_2"
    assert summary["robot_min_static_gap"]["robot_1"]["min_gap_m"] == pytest.approx(0.362, abs=1e-4)


def test_recompute_cli_writes_sidecars_without_touching_bundle(tmp_path):
    bundle = _bundle(tmp_path, [0.838] * 4)
    before = _digest(bundle)
    out = tmp_path / "out"
    assert main([str(bundle), "--out-dir", str(out), "--rows"]) == 0
    assert _digest(bundle) == before
    rows = (out / "rows" / "bundle.contacts.jsonl").read_text().splitlines()
    assert json.loads(rows[0])["robot_static_contacts"][0]["obstacle_id"] == "obstacle_2"
    assert json.loads((out / "index.json").read_text())["bundle"]["static_verdict"] == "brief_graze"


def test_recompute_cli_refuses_out_dir_inside_bundle(tmp_path):
    bundle = _bundle(tmp_path, [1.2])
    with pytest.raises(BundleError):
        main([str(bundle), "--out-dir", str(bundle / "contacts")])
