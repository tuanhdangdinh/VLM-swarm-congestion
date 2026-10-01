"""End-to-end manifest building from a synthetic `data/logs/vm_runs`-shaped tree.

Exercises the real scan -> GT-match -> candidate -> balanced-selection path
(`scripts/build_capability_probe_manifest.py`) against fixture decisions/GT
rather than the real (gitignored) run logs, so this stays a fast, offline
unit test. Uses the repository's own calibration file (checked in, not
gitignored) for a real homography. `synthetic_logs_root` lives in
`conftest.py`, shared with `test_audit_capability_probe_manifest.py`.
"""
from reasoning.vlm.capability_probes.models import ProbeManifest
from scripts.build_capability_probe_manifest import build_manifest
from tests.unit.conftest import CAPABILITY_PROBE_CALIBRATION_PATH as _CALIBRATION_PATH


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
        manifest, _ = build_manifest(
            synthetic_logs_root, _CALIBRATION_PATH, seed=1, target_per_type=10, max_per_scene=2
        )
        restored = ProbeManifest.model_validate_json(manifest.model_dump_json())
        assert restored == manifest
