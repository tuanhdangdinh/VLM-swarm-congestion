import math

import pytest

from reasoning.baselines.classical_reasoner import (
    ClassicalParams,
    ConflictZone,
    classify_scene,
)
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def _robot(
    rid: str,
    x: float,
    y: float,
    theta: float,
    v: float = 0.0,
    goal: tuple[float, float] | None = None,
) -> RobotStateInput:
    return RobotStateInput(robot_id=rid, x=x, y=y, theta=theta, linear_velocity=v, goal=goal)


def _frame(stamp: float, *robots: RobotStateInput) -> SnapshotFrame:
    return SnapshotFrame(stamp=stamp, robots=list(robots))


_PARAMS = ClassicalParams()
_ZONE = ConflictZone(zone_id="crossing", x=0.0, y=0.0, radius_m=1.5)


def _head_on_pair() -> tuple[RobotStateInput, RobotStateInput]:
    return (
        _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
        _robot("robot_2", 0.4, 0.0, math.pi, goal=(-5.0, 0.0)),
    )


def _crossing_pair() -> tuple[RobotStateInput, RobotStateInput]:
    return (
        _robot("robot_1", -0.8, 0.0, 0.0, goal=(5.0, 0.0)),
        _robot("robot_2", 0.0, -0.8, math.pi / 2, goal=(0.0, 5.0)),
    )


class TestClassicalParams:
    def test_defaults_match_rev8_arm_b_section(self):
        assert _PARAMS.model_dump() == {
            "r_conflict_m": 1.5,
            "r_block_m": 1.0,
            "heading_opposition_min_deg": 150.0,
            "axis_cross_min_deg": 45.0,
            "axis_cross_max_deg": 135.0,
            "arrival_tie_sec": 1.0,
            "stopped_speed_mps": 0.05,
            "goal_beyond_max_deg": 60.0,
        }

    def test_axis_window_rejects_inverted_bounds(self):
        with pytest.raises(ValueError):
            ClassicalParams(axis_cross_min_deg=100.0, axis_cross_max_deg=60.0)


class TestClassifyHeadOn:
    def test_classify_head_on_when_opposed_pair_goals_beyond(self):
        c = classify_scene([_frame(1.0, *_head_on_pair())], [], _PARAMS)
        assert (c.scenario, c.congestion_type, c.blocker_kind) == ("head_on", "deadlock", "robot")
        assert c.involved_robots == ["robot_1", "robot_2"]

    def test_classify_head_on_conflict_center_is_pair_midpoint(self):
        c = classify_scene([_frame(1.0, *_head_on_pair())], [], _PARAMS)
        assert c.conflict_center == pytest.approx((0.2, 0.0))
        assert c.conflict_radius_m == _PARAMS.r_conflict_m
        assert c.zone_id is None

    def test_classify_head_on_ignores_distant_stopped_bystander(self):
        bystander = _robot("robot_3", 8.0, 8.0, 0.0, goal=(9.0, 8.0))
        c = classify_scene([_frame(1.0, *_head_on_pair(), bystander)], [], _PARAMS)
        assert c.scenario == "head_on"
        assert c.involved_robots == ["robot_1", "robot_2"]

    def test_classify_not_head_on_when_third_stopped_robot_within_r_conflict(self):
        third = _robot("robot_3", 0.2, 1.0, math.pi / 2, goal=(0.2, 5.0))
        c = classify_scene([_frame(1.0, *_head_on_pair(), third)], [], _PARAMS)
        assert c.scenario != "head_on"

    def test_classify_not_head_on_when_heading_opposition_below_threshold(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 0.4, 0.0, math.radians(140.0), goal=(-5.0, 0.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario != "head_on"

    def test_classify_not_head_on_when_pair_beyond_r_conflict(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 2.0, 0.0, math.pi, goal=(-5.0, 0.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario != "head_on"

    def test_classify_not_head_on_when_goal_not_beyond_other(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario != "head_on"

    def test_classify_head_on_when_goals_missing(self):
        # Goal-beyond is only checkable with goals; without them the geometric
        # standoff alone decides (plan leniency, documented in the module).
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0),
            _robot("robot_2", 0.4, 0.0, math.pi),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "head_on"


class TestClassifyIntersection:
    def test_classify_intersection_when_axes_cross_at_zone(self):
        c = classify_scene([_frame(1.0, *_crossing_pair())], [_ZONE], _PARAMS)
        assert (c.scenario, c.congestion_type, c.blocker_kind) == (
            "intersection",
            "bottleneck",
            "robot",
        )
        assert c.involved_robots == ["robot_1", "robot_2"]

    def test_classify_intersection_conflict_zone_is_matched_zone(self):
        far_zone = ConflictZone(zone_id="far", x=20.0, y=20.0, radius_m=1.0)
        c = classify_scene([_frame(1.0, *_crossing_pair())], [far_zone, _ZONE], _PARAMS)
        assert c.zone_id == "crossing"
        assert c.conflict_center == (0.0, 0.0)
        assert c.conflict_radius_m == 1.5

    def test_classify_not_intersection_when_axes_parallel(self):
        frame = _frame(
            1.0,
            _robot("robot_1", -0.8, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 0.0, -0.8, 0.0, goal=(5.0, -0.8)),
        )
        c = classify_scene([frame], [_ZONE], _PARAMS)
        assert c.scenario != "intersection"

    def test_classify_not_intersection_without_mapped_zone(self):
        c = classify_scene([_frame(1.0, *_crossing_pair())], [], _PARAMS)
        assert c.scenario != "intersection"


class TestClassifyBlockedPath:
    def test_classify_blocked_path_object_when_front_clear(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.congestion_type, c.blocker_kind) == (
            "blocked_path",
            "anomaly",
            "object",
        )
        assert c.involved_robots == ["robot_1"]

    def test_classify_blocked_path_when_nearby_robot_is_behind(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", -0.5, 0.0, 0.0, v=0.3),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "blocked_path"

    def test_classify_blocked_path_has_no_conflict_zone(self):
        frame = _frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)))
        c = classify_scene([frame], [], _PARAMS)
        assert (c.conflict_center, c.conflict_radius_m, c.zone_id) == (None, None, None)


class TestClassifyOther:
    def test_classify_unknown_when_stopped_robots_block_each_other(self):
        # Opposed headings but crosswise goals: goal-beyond fails head_on, and
        # each robot has the other within r_block ahead, so blocked_path fails.
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.congestion_type, c.blocker_kind) == ("unknown", "anomaly", None)
        assert c.involved_robots == ["robot_1", "robot_2"]

    def test_classify_none_when_all_moving(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, v=0.4),
            _robot("robot_2", 0.4, 0.0, math.pi, v=0.4),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.congestion_type, c.involved_robots) == ("none", "none", [])

    def test_classify_stopped_by_status_when_velocity_missing(self):
        state = RobotStateInput(
            robot_id="robot_1", x=0.0, y=0.0, theta=0.0, status="STALE", goal=(5.0, 0.0)
        )
        c = classify_scene([_frame(1.0, state)], [], _PARAMS)
        assert c.scenario == "blocked_path"

    def test_classify_moving_by_status_when_velocity_missing(self):
        state = RobotStateInput(
            robot_id="robot_1", x=0.0, y=0.0, theta=0.0, status="MOVING", goal=(5.0, 0.0)
        )
        c = classify_scene([_frame(1.0, state)], [], _PARAMS)
        assert c.scenario == "none"

    def test_classify_uses_latest_frame_by_stamp(self):
        moving = _frame(5.0, _robot("robot_1", 0.0, 0.0, 0.0, v=0.4))
        stopped = _frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)))
        c = classify_scene([moving, stopped], [], _PARAMS)
        assert c.scenario == "none"

    def test_classify_empty_frames_raise_value_error(self):
        with pytest.raises(ValueError):
            classify_scene([], [], _PARAMS)
