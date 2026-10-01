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
from reasoning.vlm.models import ProposedPlanLeg, RobotStateInput, SnapshotFrame


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
            "fcfs_zone_radius_m": None,
        }

    def test_axis_window_rejects_inverted_bounds(self):
        with pytest.raises(ValueError):
            ClassicalParams(axis_cross_min_deg=100.0, axis_cross_max_deg=60.0)

    @pytest.mark.parametrize("radius", [0.0, -0.1])
    def test_arrived_exclusion_radius_rejects_non_positive(self, radius):
        with pytest.raises(ValidationError):
            ClassicalParams(arrived_exclusion_radius_m=radius)

    def test_head_on_fcfs_radius_defaults_to_r_conflict(self):
        assert ClassicalParams(r_conflict_m=1.2).head_on_fcfs_radius_m == 1.2

    def test_head_on_fcfs_radius_uses_fcfs_zone_radius_when_set(self):
        assert ClassicalParams(fcfs_zone_radius_m=1.0).head_on_fcfs_radius_m == 1.0

    def test_fcfs_zone_radius_rejects_below_half_r_conflict(self):
        with pytest.raises(ValidationError):
            ClassicalParams(r_conflict_m=1.5, fcfs_zone_radius_m=0.7)

    def test_fcfs_zone_radius_accepts_half_r_conflict(self):
        assert ClassicalParams(r_conflict_m=1.5, fcfs_zone_radius_m=0.75).fcfs_zone_radius_m == 0.75


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


def _held_frame(stamp: float, held: tuple[str, ...], *robots: RobotStateInput) -> SnapshotFrame:
    return SnapshotFrame(stamp=stamp, robots=list(robots), held_robot_ids=held)


def _b1_merge(r1_x: float, r2: tuple[float, float, float]) -> list[RobotStateInput]:
    # Unified scene design, B1 bottleneck_merge: robot_1 stopped at the merge,
    # robot_2 latched coming down the north arm, robot_3 held at its spawn.
    return [
        _robot("robot_1", r1_x, 0.0, 0.0, goal=(2.45, -0.30)),
        _robot("robot_2", r2[0], r2[1], math.radians(r2[2]), goal=(1.90, 0.0)),
        _robot("robot_3", -2.45, 0.0, 0.0, goal=(2.45, 0.30)),
    ]


# The design doc's four predicted B1 standoff poses (robot_1 x; robot_2 x, y,
# heading in degrees).
_B1_POSES = [
    (0.10, (0.15, 0.45, -80.0)),
    (0.00, (0.20, 0.40, -70.0)),
    (0.20, (0.30, 0.42, -60.0)),
    (-0.10, (0.10, 0.35, -90.0)),
]


def _b3_standoff(separation: float, shift: float, jitter: float) -> list[RobotStateInput]:
    # Unified scene design, B3 convoy_counterflow: the robot_1/robot_2 standoff
    # (the T2b grid) with robot_3 and robot_4 held on the centreline, both
    # queued robots shifted by the M1 jitter.
    return [
        _robot("robot_1", shift - separation / 2, 0.0, 0.0, goal=(2.45, -0.30)),
        _robot("robot_2", shift + separation / 2, 0.0, math.pi, goal=(-2.00, 0.0)),
        _robot("robot_3", -1.90 + jitter, 0.0, 0.0, goal=(2.45, 0.30)),
        _robot("robot_4", -2.47 + jitter, 0.0, 0.0, goal=(1.85, 0.0)),
    ]


_B3_GRID = [
    (separation, shift, jitter)
    for separation in (0.24, 0.46, 0.70)
    for shift in (-0.2, -0.1, 0.0, 0.1, 0.2)
    for jitter in (-0.1, 0.0, 0.1)
]
# The 10 of 45 cases in which robot_3 crowds the head_on pair (within
# r_conflict_m of robot_1): Arm B read them as blocked_path [robot_3].
_B3_CROWDED = {
    (0.24, -0.2, 0.1),
    (0.46, -0.2, 0.0), (0.46, -0.2, 0.1), (0.46, -0.1, 0.1),
    (0.70, -0.2, -0.1), (0.70, -0.2, 0.0), (0.70, -0.2, 0.1),
    (0.70, -0.1, 0.0), (0.70, -0.1, 0.1), (0.70, 0.0, 0.1),
}


class TestClassifyHeldRobot:
    """A10-mold held-robot exclusion (amendments item 28)."""

    def test_held_robot_is_not_a_blocked_path_candidate(self):
        frame = _held_frame(1.0, ("robot_1",), _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0)))
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("none", [])

    def test_unheld_twin_is_blocked_path(self):
        frame = _held_frame(1.0, (), _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0)))
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_1"])

    def test_decide_held_only_scene_reports_held_cause(self):
        frame = _held_frame(1.0, ("robot_1",), _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0)))
        decision = decide_classical([frame], [], _PARAMS)
        assert (decision.congestion_detected, decision.strategy) == (False, "none")
        assert decision.root_cause == (
            "classical: stopped robots are all parked at their goals or held back"
        )

    def test_decide_parked_cause_unchanged_without_held_robots(self):
        decision = decide_classical([_frame(1.0, *_parked_pair())], [], _PARAMS)
        assert decision.root_cause == "classical: stopped robots are all parked at their goals"

    def test_unknown_excludes_held_robot(self):
        # robot_2 is held and sits in robot_1's front, so robot_1 is not
        # blocked_path; crosswise goals rule out head_on.
        frame = _held_frame(
            1.0,
            ("robot_2",),
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.5, 3.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("unknown", ["robot_1"])

    def test_held_robot_still_blocks_another(self):
        # The held robot sits ahead of robot_1, so robot_1 is not blocked_path.
        frame = _held_frame(
            1.0,
            ("robot_2",),
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi / 2, goal=(3.0, 3.0)),
        )
        assert classify_scene([frame], [], _PARAMS).scenario == "unknown"

    def test_head_on_keeps_held_robot(self):
        c = classify_scene([_held_frame(1.0, ("robot_1",), *_head_on_pair())], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("head_on", ["robot_1", "robot_2"])

    def test_held_robot_still_crowds_head_on(self):
        # Like a parked robot, a held one still counts for the crowding check.
        crowd = _robot("robot_3", -1.0, 0.0, 0.0, goal=(5.0, 0.0))
        c = classify_scene(
            [_held_frame(1.0, ("robot_3",), *_head_on_pair(), crowd)], [], _PARAMS
        )
        assert c.scenario == "unknown"
        assert c.involved_robots == ["robot_1", "robot_2"]

    def test_intersection_keeps_held_robot(self):
        c = classify_scene(
            [_held_frame(1.0, ("robot_2",), *_crossing_pair())], [_ZONE], _PARAMS
        )
        assert (c.scenario, c.involved_robots) == ("intersection", ["robot_1", "robot_2"])

    def test_only_latest_frame_held_set_is_read(self):
        robot = _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0))
        frames = [_held_frame(0.0, ("robot_1",), robot), _held_frame(1.0, (), robot)]
        assert classify_scene(frames, [], _PARAMS).scenario == "blocked_path"

    def test_held_id_of_absent_robot_is_inert(self):
        robot = _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0))
        held = resolve_classical([_held_frame(1.0, ("robot_9",), robot)], [], _PARAMS)
        plain = resolve_classical([_frame(1.0, robot)], [], _PARAMS)
        assert held.model_dump_json() == plain.model_dump_json()

    @pytest.mark.parametrize(
        "frames",
        [
            [_frame(1.0, *_head_on_pair())],
            [_frame(1.0, *_crossing_pair())],
            [_frame(1.0, *_parked_pair())],
            [_frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, goal=(3.0, 0.0)))],
        ],
    )
    def test_no_held_robot_resolution_byte_identical(self, frames):
        # Frames built without the field and with an explicit empty held set
        # resolve to the same bytes: the rule is inert until M5 marks a robot.
        explicit = [f.model_copy(update={"held_robot_ids": ()}) for f in frames]
        for zones in ([], [_ZONE]):
            assert (
                resolve_classical(frames, zones, _PARAMS).model_dump_json()
                == resolve_classical(explicit, zones, _PARAMS).model_dump_json()
            )

    @pytest.mark.parametrize(("r1_x", "r2"), _B1_POSES)
    def test_b1_merge_without_exclusion_names_held_robot_3(self, r1_x, r2):
        # The recorded pre-rule behaviour: robot_3, held with a clear front,
        # reads as blocked_path and Arm B would reroute (release) it.
        c = classify_scene([_frame(30.0, *_b1_merge(r1_x, r2))], [], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_3"])

    @pytest.mark.parametrize(("r1_x", "r2"), _B1_POSES)
    def test_b1_merge_with_held_robot_3_is_unknown_merge_pair(self, r1_x, r2):
        frame = _held_frame(30.0, ("robot_3",), *_b1_merge(r1_x, r2))
        resolution = resolve_classical([frame], [], _PARAMS)
        assert resolution.classification.scenario == "unknown"
        assert resolution.decision.involved_robots == ["robot_1", "robot_2"]
        assert resolution.decision.strategy == "temporary_wait"

    @pytest.mark.parametrize(("r1_x", "r2"), _B1_POSES)
    def test_b1_merge_zone_changes_nothing(self, r1_x, r2):
        # The design doc's optional gate-mouth zone: goal axes are parallel,
        # so the intersection rule cannot fire either way.
        zone = ConflictZone(zone_id="aperture_1", x=0.4, y=0.0, radius_m=1.5)
        frame = _held_frame(30.0, ("robot_3",), *_b1_merge(r1_x, r2))
        c = classify_scene([frame], [zone], _PARAMS)
        assert (c.scenario, c.involved_robots) == ("unknown", ["robot_1", "robot_2"])

    def test_b3_grid_without_exclusion_flips_10_of_45(self):
        flipped = set()
        for case in _B3_GRID:
            c = classify_scene([_frame(30.0, *_b3_standoff(*case))], [], _PARAMS)
            if c.scenario != "head_on":
                assert (c.scenario, c.involved_robots) == ("blocked_path", ["robot_3"])
                flipped.add(case)
        assert flipped == _B3_CROWDED

    @pytest.mark.parametrize("case", _B3_GRID)
    def test_b3_grid_with_held_queue(self, case):
        # Candidacy-only exclusion: the held robot_3 still crowds the pair, so
        # the 10 crowded cases read unknown [robot_1, robot_2] (a wait), not
        # head_on; the design doc's "45/45 head_on" presumed the held robots
        # also left the crowding check, which item 28 did not approve.
        frame = _held_frame(30.0, ("robot_3", "robot_4"), *_b3_standoff(*case))
        c = classify_scene([frame], [], _PARAMS)
        expected = "unknown" if case in _B3_CROWDED else "head_on"
        assert (c.scenario, c.involved_robots) == (expected, ["robot_1", "robot_2"])


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

    def test_classify_head_on_conflict_radius_is_fcfs_zone_radius_when_set(self):
        params = ClassicalParams(fcfs_zone_radius_m=1.0)
        c = classify_scene([_frame(1.0, *_head_on_pair())], [], params)
        assert c.conflict_radius_m == 1.0

    def test_classify_head_on_verdict_unchanged_by_fcfs_zone_radius(self):
        # The FCFS zone only dates arrivals; which robots form a head_on pair
        # is still decided by r_conflict_m.
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 1.4, 0.0, math.pi, goal=(-5.0, 0.0)),
        )
        legacy = classify_scene([frame], [], _PARAMS)
        tuned = classify_scene([frame], [], ClassicalParams(fcfs_zone_radius_m=0.75))
        assert legacy.model_dump(exclude={"conflict_radius_m"}) == tuned.model_dump(
            exclude={"conflict_radius_m"}
        )
        assert tuned.scenario == "head_on"

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

    def test_decide_head_on_dates_arrival_at_fcfs_zone_not_r_conflict(self):
        # robot_1 starts 1.4 m from the final pair midpoint (inside r_conflict
        # 1.5, outside a 1.0 m FCFS zone) and enters the smaller zone at t=3;
        # robot_2 enters it at t=1. With the zone coupled to r_conflict_m,
        # robot_1's arrival is censored at t=0 and it passes first.
        frames = [
            _frame(
                stamp,
                _robot("robot_1", x1, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", x2, 0.0, math.pi, goal=(-5.0, 0.0)),
            )
            for stamp, x1, x2 in [
                (0.0, -1.4, 2.0),
                (1.0, -1.3, 0.9),
                (3.0, -0.9, 0.5),
                (5.0, -0.3, 0.3),
            ]
        ]
        coupled = resolve_classical(frames, [], _PARAMS)
        tuned = resolve_classical(frames, [], ClassicalParams(fcfs_zone_radius_m=1.0))
        assert coupled.passing_order == ["robot_1", "robot_2"]
        assert tuned.passing_order == ["robot_2", "robot_1"]

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


class TestArmBEmitsProposedPlan:
    """Arm B emits its plan through the identical `proposed_plan` field
    (prereg-v2 (a0), "Arm B emits its plan through the identical field"):
    its OWN yielder/FCFS order/strategy, never M3's `_derive_default_plan`
    (which would make the comparator M3's own default instead of Arm B's).

    `proposed_plan` is additive: every assertion elsewhere in this file about
    `congestion_detected`/`type`/`strategy`/`yield_robot`/`blocker_kind`/
    `crossing_order` is unchanged (regression pin by the rest of this test
    module passing unmodified); these tests check only the new field.
    """

    def test_head_on_plan_names_yielder_first_then_the_passer(self):
        resolution = resolve_classical(_head_on_frames([(0.0, 5.0), (2.0, 0.4)]), [], _PARAMS)
        assert resolution.decision.yield_robot == "robot_2"
        assert resolution.decision.proposed_plan == [
            ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ProposedPlanLeg(robot_id="robot_1", action="cross"),
        ]

    def test_intersection_plan_names_yielder_first_then_passers_in_fcfs_order(self):
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
        assert resolution.decision.yield_robot == "robot_2"
        assert resolution.decision.proposed_plan == [
            ProposedPlanLeg(robot_id="robot_2", action="yield"),
            ProposedPlanLeg(robot_id="robot_3", action="cross"),
            ProposedPlanLeg(robot_id="robot_1", action="cross"),
        ]

    def test_blocked_path_plan_reroutes_the_blocked_robot_only(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.proposed_plan == [
            ProposedPlanLeg(robot_id="robot_1", action="reroute"),
            ProposedPlanLeg(robot_id="robot_2", action="continue"),
        ]

    def test_unknown_plan_waits_on_first_attempt(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
                _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS, prior_attempts=0)
        assert decision.strategy == "temporary_wait"
        assert {leg.robot_id: leg.action for leg in decision.proposed_plan} == {
            "robot_1": "wait",
            "robot_2": "wait",
        }

    def test_unknown_plan_reroutes_after_prior_attempt(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
                _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS, prior_attempts=1)
        assert decision.strategy == "reroute"
        assert {leg.robot_id: leg.action for leg in decision.proposed_plan} == {
            "robot_1": "reroute",
            "robot_2": "reroute",
        }

    def test_no_congestion_emits_no_plan(self):
        frames = [_frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, v=0.4))]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.proposed_plan is None

    def test_plan_is_scene_wide_uninvolved_robot_continues(self):
        # A third, uninvolved robot elsewhere in the same frame gets `continue`,
        # not omission: the (a0) contract is scene-wide, and Arm B's own plan
        # must satisfy it like any other.
        frames = [
            _frame(
                1.0,
                *_head_on_pair(),
                _robot("robot_3", 10.0, 10.0, 0.0, v=0.4),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert {leg.robot_id: leg.action for leg in decision.proposed_plan}["robot_3"] == (
            "continue"
        )


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
    def test_load_classical_params_repo_config_matches_rev8_defaults_plus_t1_basket(self):
        # The T1 tuning basket (2026-09-29) set exactly one value away from
        # the rev-8 defaults: the head_on FCFS zone radius.
        assert load_classical_params(_REPO_RAG_CONFIG) == ClassicalParams(fcfs_zone_radius_m=1.0)

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
