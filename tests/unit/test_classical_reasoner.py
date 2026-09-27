import math
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from reasoning.baselines.classical_reasoner import (
    ClassicalParams,
    ConflictZone,
    classify_scene,
    decide_classical,
    load_classical_params,
    resolve_classical,
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
            "arrived_exclusion_radius_m": 0.35,
        }

    def test_axis_window_rejects_inverted_bounds(self):
        with pytest.raises(ValueError):
            ClassicalParams(axis_cross_min_deg=100.0, axis_cross_max_deg=60.0)

    @pytest.mark.parametrize("radius", [0.0, -0.1])
    def test_arrived_exclusion_radius_rejects_non_positive(self, radius):
        with pytest.raises(ValidationError):
            ClassicalParams(arrived_exclusion_radius_m=radius)


def _parked_pair() -> tuple[RobotStateInput, RobotStateInput]:
    # T0 normal_flow after both arrivals: each robot ~0.1 m short of its own
    # goal, facing away from the other, 5 m apart.
    return (
        _robot("robot_1", 2.41, -0.35, 0.0, goal=(2.5, -0.35)),
        _robot("robot_2", -2.41, 0.35, math.pi, goal=(-2.5, 0.35)),
    )


class TestClassifyParkedAtGoal:
    def test_classify_none_when_stopped_robots_parked_at_goals(self):
        c = classify_scene([_frame(1.0, *_parked_pair())], [], _PARAMS)
        assert (c.scenario, c.congestion_type, c.involved_robots) == ("none", "none", [])

    def test_decide_parked_scene_reports_no_congestion_with_parked_cause(self):
        decision = decide_classical([_frame(1.0, *_parked_pair())], [], _PARAMS)
        assert (decision.congestion_detected, decision.strategy) == (False, "none")
        assert decision.root_cause == "classical: stopped robots are all parked at their goals"

    def test_classify_blocked_path_when_stopped_outside_arrived_radius(self):
        frame = _frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.36, 0.0)))
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_1"])

    def test_classify_none_when_stopped_exactly_at_arrived_radius(self):
        frame = _frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.35, 0.0)))
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "none"

    def test_classify_blocked_path_when_goalless_robot_stopped(self):
        frame = _frame(1.0, _robot("robot_1", 2.5, -0.35, 0.0))
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_1"])

    def test_classify_blocked_path_excludes_parked_robot(self):
        stuck = _robot("robot_3", 0.0, 2.0, 0.0, goal=(3.0, 2.0))
        c = classify_scene([_frame(1.0, *_parked_pair(), stuck)], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_3"])

    def test_classify_unknown_excludes_parked_robot(self):
        # robot_2 is parked (goal 0.2 m away) and sits in robot_1's front, so
        # robot_1 is not blocked_path; crosswise goals rule out head_on.
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.5, 0.2)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("unknown", ["robot_1"])

    def test_classify_head_on_keeps_robot_parked_at_goal(self):
        # robot_1's goal lies 0.2 m toward robot_2: parked by radius, but the
        # pair still meets every head_on condition, so it is not excluded.
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.2, 0.0)),
            _robot("robot_2", 0.4, 0.0, math.pi, goal=(-5.0, 0.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("head_on", ["robot_1", "robot_2"])

    def test_classify_t1_head_on_unaffected_by_arrived_radius(self):
        c = classify_scene([_frame(1.0, *_head_on_pair())], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("head_on", ["robot_1", "robot_2"])

    def test_classify_intersection_keeps_robot_parked_at_goal(self):
        frame = _frame(
            1.0,
            _robot("robot_1", -0.8, 0.0, 0.0, goal=(-0.6, 0.0)),
            _robot("robot_2", 0.0, -0.8, math.pi / 2, goal=(0.0, 5.0)),
        )
        c = classify_scene([frame], [_ZONE], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("intersection", ["robot_1", "robot_2"])


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


def _head_on_frames(r2_track: list[tuple[float, float]], r1_x: float = 0.0) -> list[SnapshotFrame]:
    """robot_1 parked at `r1_x`; robot_2 visits `(stamp, x)` points ending at 0.4."""
    return [
        _frame(
            stamp,
            _robot("robot_1", r1_x, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", x, 0.0, math.pi, goal=(-5.0, 0.0)),
        )
        for stamp, x in r2_track
    ]


class TestDecideClassicalHeadOn:
    def test_decide_head_on_emits_deadlock_yield(self):
        decision = decide_classical(_head_on_frames([(0.0, 0.4)]), [], _PARAMS)
        assert (decision.congestion_detected, decision.type, decision.strategy) == (
            True,
            "deadlock",
            "yield",
        )
        assert decision.involved_robots == ["robot_1", "robot_2"]

    def test_decide_head_on_yields_later_arrival(self):
        # robot_2 is 4.8 m from the pair midpoint at t=0 and enters at t=2.
        frames = _head_on_frames([(0.0, 5.0), (2.0, 0.4)])
        assert decide_classical(frames, [], _PARAMS).yield_robot == "robot_2"

    def test_resolve_head_on_passing_order_ends_with_yielder(self):
        frames = _head_on_frames([(0.0, 5.0), (2.0, 0.4)])
        resolution = resolve_classical(frames, [], _PARAMS)
        assert resolution.passing_order == ["robot_1", "robot_2"]
        assert resolution.decision.yield_robot == resolution.passing_order[-1]

    def test_decide_head_on_yields_less_committed_when_arrival_tied(self):
        # Both inside the zone from t=0; robot_2 has driven 0.6 m in-zone,
        # robot_1 only 0.1 m, so robot_2 passes despite sorting second by id.
        frames = [
            _frame(
                0.0,
                _robot("robot_1", -0.1, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 1.0, 0.0, math.pi, goal=(-5.0, 0.0)),
            ),
            *_head_on_frames([(0.5, 0.7), (1.0, 0.4)]),
        ]
        assert decide_classical(frames, [], _PARAMS).yield_robot == "robot_1"

    def test_decide_head_on_ties_arrivals_inside_tie_window(self):
        # robot_2 arrives 0.9 s after robot_1 (< arrival_tie_sec) but is the
        # more committed, so the tie cluster lets it pass first.
        frames = _head_on_frames([(0.0, 2.0), (0.9, 1.6), (1.8, 0.4)])
        assert decide_classical(frames, [], _PARAMS).yield_robot == "robot_1"

    def test_decide_head_on_orders_by_arrival_at_tie_window_boundary(self):
        # Same track, but robot_2 arrives exactly arrival_tie_sec later: no tie.
        frames = _head_on_frames([(0.0, 2.0), (1.0, 1.6), (2.0, 0.4)])
        assert decide_classical(frames, [], _PARAMS).yield_robot == "robot_2"

    def test_decide_head_on_breaks_full_tie_by_robot_id(self):
        frames = _head_on_frames([(0.0, 0.4), (2.0, 0.4)])
        assert decide_classical(frames, [], _PARAMS).yield_robot == "robot_2"

    def test_decide_head_on_measures_arrival_at_pair_not_mapped_zone(self):
        # A mapped zone elsewhere must not become the FCFS reference for a
        # head-on pair; against it neither robot would ever "arrive".
        far_zone = ConflictZone(zone_id="far", x=20.0, y=20.0, radius_m=1.5)
        frames = _head_on_frames([(0.0, 5.0), (2.0, 0.4)])
        resolution = resolve_classical(frames, [far_zone], _PARAMS)
        assert resolution.passing_order == ["robot_1", "robot_2"]


def _crossing_frames(
    tracks: dict[str, list[tuple[float, float]]], stamps: list[float]
) -> list[SnapshotFrame]:
    """Robots crossing at the origin; `tracks` gives each robot's (x, y) per stamp."""
    headings = {"robot_1": 0.0, "robot_2": math.pi / 2, "robot_3": math.pi}
    goals = {"robot_1": (5.0, 0.0), "robot_2": (0.0, 5.0), "robot_3": (-5.0, 0.3)}
    return [
        _frame(
            stamp,
            *(
                _robot(rid, *track[i], headings[rid], goal=goals[rid])
                for rid, track in sorted(tracks.items())
            ),
        )
        for i, stamp in enumerate(stamps)
    ]


class TestDecideClassicalIntersection:
    def test_decide_intersection_emits_bottleneck_yield(self):
        frames = _crossing_frames(
            {"robot_1": [(-0.8, 0.0), (-0.8, 0.0)], "robot_2": [(0.0, -3.0), (0.0, -0.8)]},
            [0.0, 2.0],
        )
        decision = decide_classical(frames, [_ZONE], _PARAMS)
        assert (decision.type, decision.strategy) == ("bottleneck", "yield")

    def test_decide_intersection_yields_last_arrival(self):
        frames = _crossing_frames(
            {"robot_1": [(-0.8, 0.0), (-0.8, 0.0)], "robot_2": [(0.0, -3.0), (0.0, -0.8)]},
            [0.0, 2.0],
        )
        assert decide_classical(frames, [_ZONE], _PARAMS).yield_robot == "robot_2"

    def test_resolve_intersection_orders_three_robots_by_arrival(self):
        frames = _crossing_frames(
            {
                "robot_1": [(-4.0, 0.0), (-0.8, 0.0), (-0.8, 0.0)],
                "robot_2": [(0.0, -4.0), (0.0, -4.0), (0.0, -0.8)],
                "robot_3": [(0.8, 0.3), (0.8, 0.3), (0.8, 0.3)],
            },
            [0.0, 2.0, 4.0],
        )
        resolution = resolve_classical(frames, [_ZONE], _PARAMS)
        assert resolution.passing_order == ["robot_3", "robot_1", "robot_2"]

    def test_resolve_intersection_robot_without_arrival_passes_last(self):
        # robot_1 is within r_conflict of the zone center (so it is involved)
        # but never inside the 0.5 m zone radius, so it has no arrival stamp.
        small_zone = ConflictZone(zone_id="crossing", x=0.0, y=0.0, radius_m=0.5)
        frames = _crossing_frames(
            {"robot_1": [(-0.8, 0.0), (-0.8, 0.0)], "robot_2": [(0.0, -0.3), (0.0, -0.8)]},
            [0.0, 2.0],
        )
        resolution = resolve_classical(frames, [small_zone], _PARAMS)
        assert resolution.passing_order == ["robot_2", "robot_1"]


class TestArmBEmitsPromptV2Fields:
    """Arm B fills the shared contract's `blocker_kind` and `crossing_order`."""

    def test_head_on_decision_carries_robot_blocker(self):
        decision = decide_classical(_head_on_frames([(0.0, 0.4)]), [], _PARAMS)
        assert decision.blocker_kind == "robot"

    def test_two_robot_decision_omits_crossing_order(self):
        # Mirrors the prompt: an order is asked for only at 3+ robots, and the
        # yielder alone already fixes a two-robot order.
        resolution = resolve_classical(_head_on_frames([(0.0, 5.0), (2.0, 0.4)]), [], _PARAMS)
        assert resolution.passing_order == ["robot_1", "robot_2"]
        assert resolution.decision.crossing_order is None

    def test_three_robot_intersection_decision_carries_passing_order(self):
        frames = _crossing_frames(
            {
                "robot_1": [(-4.0, 0.0), (-0.8, 0.0), (-0.8, 0.0)],
                "robot_2": [(0.0, -4.0), (0.0, -4.0), (0.0, -0.8)],
                "robot_3": [(0.8, 0.3), (0.8, 0.3), (0.8, 0.3)],
            },
            [0.0, 2.0, 4.0],
        )
        resolution = resolve_classical(frames, [_ZONE], _PARAMS)
        assert resolution.decision.blocker_kind == "robot"
        assert resolution.decision.crossing_order == ["robot_3", "robot_1", "robot_2"]
        assert resolution.decision.crossing_order[-1] == resolution.decision.yield_robot

    def test_blocked_path_decision_carries_forced_object_blocker(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.blocker_kind == "object"
        assert decision.crossing_order is None

    def test_unknown_decision_carries_no_blocker(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
                _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
            )
        ]
        assert decide_classical(frames, [], _PARAMS).blocker_kind is None

    def test_no_congestion_decision_carries_neither_field(self):
        frames = [_frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, v=0.4))]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.blocker_kind is None and decision.crossing_order is None


class TestDecideClassicalOtherScenarios:
    def _blocked_frames(self) -> list[SnapshotFrame]:
        return [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
            )
        ]

    def _mutual_block_frames(self) -> list[SnapshotFrame]:
        return [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
                _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
            )
        ]

    def test_decide_blocked_path_reroutes_without_yielder(self):
        decision = decide_classical(self._blocked_frames(), [], _PARAMS)
        assert (decision.type, decision.strategy, decision.yield_robot) == (
            "anomaly",
            "reroute",
            None,
        )

    def test_resolve_blocked_path_reports_object_blocker_without_order(self):
        resolution = resolve_classical(self._blocked_frames(), [], _PARAMS)
        assert resolution.classification.blocker_kind == "object"
        assert resolution.passing_order is None

    def test_decide_unknown_waits_on_first_attempt(self):
        decision = decide_classical(self._mutual_block_frames(), [], _PARAMS, prior_attempts=0)
        assert decision.strategy == "temporary_wait"

    def test_decide_unknown_reroutes_after_prior_attempt(self):
        decision = decide_classical(self._mutual_block_frames(), [], _PARAMS, prior_attempts=1)
        assert decision.strategy == "reroute"

    def test_decide_negative_prior_attempts_raise_value_error(self):
        with pytest.raises(ValueError):
            decide_classical(self._mutual_block_frames(), [], _PARAMS, prior_attempts=-1)

    def test_decide_none_when_no_robot_stopped(self):
        frames = [_frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, v=0.4))]
        decision = decide_classical(frames, [], _PARAMS)
        assert (
            decision.congestion_detected,
            decision.type,
            decision.strategy,
            decision.involved_robots,
        ) == (False, "none", "none", [])


_REPO_RAG_CONFIG = Path(__file__).resolve().parents[2] / "config" / "rag.yaml"


class TestLoadClassicalParams:
    def test_load_classical_params_repo_config_matches_rev8_defaults(self):
        assert load_classical_params(_REPO_RAG_CONFIG) == ClassicalParams()

    def test_load_classical_params_repo_config_declares_section(self):
        raw = yaml.safe_load(_REPO_RAG_CONFIG.read_text(encoding="utf-8"))
        assert set(raw["classical"]) == set(ClassicalParams.model_fields)

    def test_load_classical_params_missing_section_yields_defaults(self, tmp_path):
        config = tmp_path / "rag.yaml"
        config.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
        assert load_classical_params(config) == ClassicalParams()

    def test_load_classical_params_section_overrides_defaults(self, tmp_path):
        config = tmp_path / "rag.yaml"
        config.write_text("classical:\n  r_block_m: 0.8\n", encoding="utf-8")
        assert load_classical_params(config).r_block_m == 0.8

    def test_load_classical_params_unknown_key_raises(self, tmp_path):
        # A typo in a pre-registered threshold must fail loudly, not fall back.
        config = tmp_path / "rag.yaml"
        config.write_text("classical:\n  r_blok_m: 0.8\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_classical_params(config)
