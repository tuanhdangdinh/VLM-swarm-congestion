"""GT-derived correct answers for each probe type.

Uses an identity homography (pixel == world) so pixel/world arithmetic is
checked without depending on any particular calibration file; the homography
math itself is `swarm_perception.geometry`'s own responsibility, already
tested there.
"""
import numpy as np
import pytest

from reasoning.vlm.capability_probes.ground_truth import (
    grid_cell_answer,
    left_right_answer,
    max_m1_gt_disagreement_m,
    nearest_first_answer,
    robot_count_answer,
)

_IDENTITY_H = np.eye(3)
_WIDTH, _HEIGHT = 300, 300  # centre column/row at world (150, 150)


class TestRobotCountAnswer:
    def test_counts_every_robot(self):
        robots = {"robot_1": {"x": 0.0, "y": 0.0}, "robot_2": {"x": 1.0, "y": 1.0}}
        assert robot_count_answer(robots) == "2"

    def test_single_robot(self):
        assert robot_count_answer({"robot_1": {"x": 0.0, "y": 0.0}}) == "1"


class TestNearestFirstAnswer:
    def test_returns_the_closer_other_robot_and_the_gap(self):
        robots = {
            "robot_1": {"x": 0.0, "y": 0.0},
            "robot_2": {"x": 1.0, "y": 0.0},
            "robot_3": {"x": 5.0, "y": 0.0},
        }
        nearest_id, gap = nearest_first_answer(robots, "robot_1")
        assert nearest_id == "robot_2"
        assert gap == 4.0

    def test_none_with_fewer_than_two_other_robots(self):
        robots = {"robot_1": {"x": 0.0, "y": 0.0}, "robot_2": {"x": 1.0, "y": 0.0}}
        assert nearest_first_answer(robots, "robot_1") is None

    def test_ties_resolve_to_a_single_nearest_deterministically(self):
        robots = {
            "robot_1": {"x": 0.0, "y": 0.0},
            "robot_2": {"x": 1.0, "y": 0.0},
            "robot_3": {"x": -1.0, "y": 0.0},
        }
        nearest_id, gap = nearest_first_answer(robots, "robot_1")
        assert nearest_id in ("robot_2", "robot_3")
        assert gap == 0.0


class TestLeftRightAnswer:
    def test_world_x_left_of_centre_is_left(self):
        side, margin = left_right_answer(100.0, _IDENTITY_H, _WIDTH, _HEIGHT)
        assert side == "left"
        assert margin == 50.0

    def test_world_x_right_of_centre_is_right(self):
        side, margin = left_right_answer(200.0, _IDENTITY_H, _WIDTH, _HEIGHT)
        assert side == "right"
        assert margin == 50.0

    def test_margin_is_distance_from_centre(self):
        _, margin = left_right_answer(149.0, _IDENTITY_H, _WIDTH, _HEIGHT)
        assert margin == 1.0


class TestGridCellAnswer:
    def test_centre_point_is_the_centre_cell(self):
        assert grid_cell_answer(150.0, 150.0, _IDENTITY_H, _WIDTH, _HEIGHT) == 4

    def test_top_left_point_is_cell_zero(self):
        # Clear of the grid's own boundary margin (not the literal corner).
        assert grid_cell_answer(40.0, 40.0, _IDENTITY_H, _WIDTH, _HEIGHT) == 0

    def test_off_frame_point_is_none(self):
        assert grid_cell_answer(-10.0, 10.0, _IDENTITY_H, _WIDTH, _HEIGHT) is None


class TestMaxM1GtDisagreement:
    def test_zero_when_identical(self):
        robots = {"robot_1": {"x": 1.0, "y": 2.0}}
        assert max_m1_gt_disagreement_m(robots, robots) == 0.0

    def test_reports_the_largest_per_axis_difference(self):
        m1 = {"robot_1": {"x": 1.0, "y": 2.0}}
        gt = {"robot_1": {"x": 1.05, "y": 2.2}}
        assert max_m1_gt_disagreement_m(m1, gt) == pytest.approx(0.2)

    def test_infinite_when_robot_sets_disagree(self):
        m1 = {"robot_1": {"x": 0.0, "y": 0.0}}
        gt = {"robot_1": {"x": 0.0, "y": 0.0}, "robot_2": {"x": 1.0, "y": 1.0}}
        assert max_m1_gt_disagreement_m(m1, gt) == float("inf")
