"""GT-row matching, scene legibility, and distance-based duplicate detection.

Shared by both the build script and the audit script
(`reasoning.vlm.capability_probes.scanning`), so these are tested directly
once rather than only indirectly through either tool.
"""
import json

import pytest

from reasoning.vlm.capability_probes.scanning import (
    NEAR_DUPLICATE_MAX_DISPLACEMENT_M,
    deduplicate_by_distance,
    load_gt_rows,
    max_displacement_m,
    nearest_gt_row,
    scene_is_legible,
)

_WIDTH, _HEIGHT = 1280, 960


class TestLoadAndMatchGtRows:
    def test_load_gt_rows_parses_each_line(self, tmp_path):
        path = tmp_path / "ground_truth.jsonl"
        path.write_text(
            json.dumps({"sim_time_sec": 0.0, "robots": {}}) + "\n"
            + json.dumps({"sim_time_sec": 1.0, "robots": {}}) + "\n",
            encoding="utf-8",
        )
        rows = load_gt_rows(path)
        assert [r["sim_time_sec"] for r in rows] == [0.0, 1.0]

    def test_load_gt_rows_skips_blank_lines(self, tmp_path):
        path = tmp_path / "ground_truth.jsonl"
        path.write_text(json.dumps({"sim_time_sec": 0.0, "robots": {}}) + "\n\n", encoding="utf-8")
        assert len(load_gt_rows(path)) == 1

    def test_nearest_gt_row_picks_the_closest_stamp(self):
        rows = [{"sim_time_sec": 0.0}, {"sim_time_sec": 1.0}, {"sim_time_sec": 2.0}]
        assert nearest_gt_row(rows, 1.2)["sim_time_sec"] == 1.0

    def test_nearest_gt_row_none_beyond_tolerance(self):
        rows = [{"sim_time_sec": 0.0}]
        assert nearest_gt_row(rows, 10.0) is None

    def test_nearest_gt_row_none_for_empty_rows(self):
        assert nearest_gt_row([], 0.0) is None


def _robots(*entries: tuple[str, float, float]) -> dict[str, dict]:
    return {rid: {"x": x, "y": y} for rid, x, y in entries}


class TestSceneIsLegible:
    def test_two_well_separated_robots_are_legible(self):
        m1 = _robots(("robot_1", 0.0, 0.0), ("robot_2", 0.0, 0.0))
        pixels = {"robot_1": (200, 200), "robot_2": (900, 700)}
        assert scene_is_legible(m1, pixels, _WIDTH, _HEIGHT)

    def test_a_robot_near_the_frame_edge_is_not_legible(self):
        m1 = _robots(("robot_1", 0.0, 0.0))
        pixels = {"robot_1": (5, 200)}
        assert not scene_is_legible(m1, pixels, _WIDTH, _HEIGHT)

    def test_a_stale_robot_is_not_legible(self):
        m1 = {"robot_1": {"x": 0.0, "y": 0.0, "status": "STALE"}}
        pixels = {"robot_1": (200, 200)}
        assert not scene_is_legible(m1, pixels, _WIDTH, _HEIGHT)

    def test_two_robots_too_close_together_are_not_legible(self):
        m1 = _robots(("robot_1", 0.0, 0.0), ("robot_2", 0.0, 0.0))
        pixels = {"robot_1": (200, 200), "robot_2": (210, 200)}  # 10 px apart
        assert not scene_is_legible(m1, pixels, _WIDTH, _HEIGHT)

    def test_two_robots_whose_labels_overlap_despite_centre_separation_are_not_legible(self):
        # Centres 70+ px apart (clears the coarse distance check) but close
        # enough that one robot's box covers part of the other's label rect.
        m1 = _robots(("robot_1", 0.0, 0.0), ("robot_2", 0.0, 0.0))
        pixels = {"robot_1": (200, 200), "robot_2": (250, 150)}
        assert not scene_is_legible(m1, pixels, _WIDTH, _HEIGHT)


class TestMaxDisplacement:
    def test_identical_positions_is_zero(self):
        a = _robots(("robot_1", 1.0, 2.0))
        assert max_displacement_m(a, a) == pytest.approx(0.0)

    def test_returns_the_largest_per_robot_displacement(self):
        a = _robots(("robot_1", 0.0, 0.0), ("robot_2", 0.0, 0.0))
        b = _robots(("robot_1", 0.03, 0.0), ("robot_2", 0.0, 0.5))
        assert max_displacement_m(a, b) == pytest.approx(0.5)

    def test_none_when_robot_sets_differ(self):
        a = _robots(("robot_1", 0.0, 0.0))
        b = _robots(("robot_2", 0.0, 0.0))
        assert max_displacement_m(a, b) is None


class _Candidate:
    def __init__(self, ref, robots):
        self.ref = ref
        self.robots = robots


class TestDeduplicateByDistance:
    def test_near_duplicate_scenes_collapse_to_the_first(self):
        far = NEAR_DUPLICATE_MAX_DISPLACEMENT_M * 10
        candidates = [
            _Candidate("robot_1", _robots(("robot_1", 0.0, 0.0))),
            _Candidate("robot_1", _robots(("robot_1", 0.001, 0.0))),  # near-duplicate
            _Candidate("robot_1", _robots(("robot_1", far, 0.0))),  # clearly distinct
        ]
        kept = deduplicate_by_distance(candidates, lambda c: c.ref, lambda c: c.robots)
        assert len(kept) == 2
        assert kept[0] is candidates[0]
        assert kept[1] is candidates[2]

    def test_different_reference_robots_are_never_duplicates(self):
        candidates = [
            _Candidate("robot_1", _robots(("robot_1", 0.0, 0.0), ("robot_2", 1.0, 1.0))),
            _Candidate("robot_2", _robots(("robot_1", 0.0, 0.0), ("robot_2", 1.0, 1.0))),
        ]
        kept = deduplicate_by_distance(candidates, lambda c: c.ref, lambda c: c.robots)
        assert len(kept) == 2

    def test_differing_robot_sets_are_never_duplicates(self):
        candidates = [
            _Candidate("robot_1", _robots(("robot_1", 0.0, 0.0))),
            _Candidate("robot_1", _robots(("robot_1", 0.0, 0.0), ("robot_2", 5.0, 5.0))),
        ]
        kept = deduplicate_by_distance(candidates, lambda c: c.ref, lambda c: c.robots)
        assert len(kept) == 2

    def test_none_reference_robot_count_items_dedupe_against_each_other(self):
        candidates = [
            _Candidate(None, _robots(("robot_1", 0.0, 0.0))),
            _Candidate(None, _robots(("robot_1", 0.0, 0.0))),
        ]
        kept = deduplicate_by_distance(candidates, lambda c: c.ref, lambda c: c.robots)
        assert len(kept) == 1
