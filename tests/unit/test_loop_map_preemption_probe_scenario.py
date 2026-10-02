"""Constraint pins for the loop-map pre-emption control smoke scenarios.

Geometry derivation: `docs/reports/2026-10-02-loop-preemption-smoke.md`.
Mirrors the project's standard-constraint-check pattern
(`docs/superpowers/specs/2026-09-29-unified-scene-design.md`, "Standard
constraint-check table") at the scope this probe needs: tracked-band
membership (C1), the baseline/blocker pair diffing by exactly one
obstacle, and the blocker leaving the registered C55 gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import load_scenario

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "isaac/config/scenarios"

# M1 tracked extent, verified clean (docs/reports/2026-10-01-m1-y-extent-
# verification.md Rev 2, PASS).
TRACKED_X = 2.5
TRACKED_Y = 2.0


def _load(name: str):
    return load_scenario(SCENARIOS_DIR / f"{name}.yaml")


def test_baseline_and_blocker_differ_by_exactly_one_obstacle():
    baseline = _load("loop_map_preemption_probe_baseline")
    blocker = _load("loop_map_preemption_probe")

    assert baseline.robots == blocker.robots
    assert baseline.loop_map == blocker.loop_map
    assert baseline.aisle_barrier == blocker.aisle_barrier is None
    assert baseline.timed_obstacles == ()
    assert len(blocker.timed_obstacles) == 1


def test_spawn_goal_and_loop_geometry_inside_tracked_band():
    for name in ("loop_map_preemption_probe_baseline", "loop_map_preemption_probe"):
        cfg = _load(name)
        robot = cfg.robots[0]
        for point in (
            (robot.spawn.x, robot.spawn.y),
            (robot.goal.x, robot.goal.y),
        ):
            assert abs(point[0]) <= TRACKED_X, (name, point)
            assert abs(point[1]) <= TRACKED_Y, (name, point)

        loop = cfg.loop_map
        aisle_y_max = loop.second_aisle_center_y_m + loop.second_aisle_width_m / 2.0
        assert loop.second_aisle_x_max_m <= TRACKED_X
        assert aisle_y_max <= TRACKED_Y


def test_robot_spawn_avoids_the_registered_robot1_stale_point():
    # docs/reports/2026-10-01-m1-y-extent-verification.md, "Registered risk":
    # robot_1/marker_id 1 at (x=-1.75, y=0, yaw=0) reproducibly loses
    # tracking. Both probe scenarios must spawn robot_1 elsewhere.
    for name in ("loop_map_preemption_probe_baseline", "loop_map_preemption_probe"):
        robot = _load(name).robots[0]
        assert robot.marker_id == 1
        flagged = robot.spawn.x == -1.75 and robot.spawn.y == 0.0 and robot.spawn.yaw_rad == 0.0
        assert not flagged, name


def test_blocker_leaves_the_registered_c55_gap():
    cfg = _load("loop_map_preemption_probe")
    blocker = cfg.timed_obstacles[0]

    # Blocker spans y in [pose.y - size.y_m/2, pose.y + size.y_m/2]; the
    # remaining aisle gap runs from that box's north face to the aisle's own
    # north edge (nominal_aisle_width_m / 2 = 0.6).
    box_north_face = blocker.pose.y + blocker.size.y_m / 2.0
    remaining_gap = 0.6 - box_north_face
    assert abs(remaining_gap - 0.55) < 1e-9, remaining_gap

    # Sub-lethal per the registered C55 floor (unified scene design doc,
    # "the single-lane module C55"): [0.50, 0.63) m is the proven-plannable
    # band.
    assert 0.50 <= remaining_gap < 0.63


def test_blocker_sits_strictly_between_the_arm_and_the_new_connector():
    cfg = _load("loop_map_preemption_probe")
    blocker = cfg.timed_obstacles[0]
    loop = cfg.loop_map

    blocker_x_min = blocker.pose.x - blocker.size.x_m / 2.0
    blocker_x_max = blocker.pose.x + blocker.size.x_m / 2.0
    connector_x_min = loop.connector_center_x_m - loop.connector_width_m / 2.0

    # East of the existing N-S strip (the loop's west leg, always open).
    assert blocker_x_min > 0.6
    # West of the new connector's mouth, so the only bypass is the real loop.
    assert blocker_x_max < connector_x_min


def test_blocker_lidar_cross_section_clears_the_scan_plane():
    # nav2_params.yaml / T3a header: the lidar scans a single plane at
    # 0.182 m. A blocker shorter than that is invisible to Nav2 regardless
    # of its footprint.
    cfg = _load("loop_map_preemption_probe")
    blocker = cfg.timed_obstacles[0]
    assert blocker.size.z_m > 0.182
