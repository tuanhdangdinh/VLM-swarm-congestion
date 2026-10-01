"""The independent post-build audit (`scripts/audit_capability_probe_manifest.py`).

Builds a manifest from the same synthetic log tree
`test_build_capability_probe_manifest.py` uses, then re-verifies it with the
audit's own, separately-re-derived checks -- exercising the "reload from disk
and recompute" path a pure in-memory build-script test cannot.
"""
import json

from scripts.audit_capability_probe_manifest import audit_manifest
from scripts.build_capability_probe_manifest import build_manifest
from tests.unit.conftest import CAPABILITY_PROBE_CALIBRATION_PATH as _CALIBRATION_PATH

# `synthetic_logs_root` is a pytest fixture from conftest.py, available to
# every test module in this directory without an import.


class TestAuditPassesAFreshlyBuiltManifest:
    def test_every_item_passes(self, synthetic_logs_root):
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        failures = audit_manifest(manifest, synthetic_logs_root, _CALIBRATION_PATH)
        assert failures == {}


class TestAuditCatchesSourceDrift:
    def test_a_moved_gt_robot_is_caught(self, synthetic_logs_root):
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        item = next(i for i in manifest.items if i.probe_type == "left_right")
        gt_path = synthetic_logs_root / item.run_id / "gt" / "ground_truth.jsonl"
        rows = [json.loads(line) for line in gt_path.read_text().splitlines() if line]
        for row in rows:
            if abs(row["sim_time_sec"] - item.sim_time_sec) < 1e-6:
                # Flip the named robot to the opposite side of the frame's
                # centre column -- the source data no longer agrees with the
                # answer the manifest was frozen with.
                pos = row["robots"][item.reference_robot_id]
                pos["x"] = -pos["x"]
        gt_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

        failures = audit_manifest(manifest, synthetic_logs_root, _CALIBRATION_PATH)
        assert item.item_id in failures
        assert any("left_right" in f for f in failures[item.item_id])

    def test_a_missing_decision_file_is_caught(self, synthetic_logs_root):
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        item = manifest.items[0]
        decision_path = synthetic_logs_root / item.run_id / "decisions" / f"{item.request_id}.json"
        decision_path.unlink()

        failures = audit_manifest(manifest, synthetic_logs_root, _CALIBRATION_PATH)
        assert item.item_id in failures
        assert any("source re-load" in f for f in failures[item.item_id])
