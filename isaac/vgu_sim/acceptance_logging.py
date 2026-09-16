from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, TextIO

from isaac.vgu_sim.config import ScenarioConfig
from isaac.vgu_sim.oracle import head_on_conflict_active

if TYPE_CHECKING:
    from pxr import Gf, Usd

CHASSIS_LINK_NAME = "base_link"


@dataclass(frozen=True)
class RobotRuntimeState:
    robot_id: str
    x: float
    y: float
    theta: float
    speed_mps: float


def _round4(value: float) -> float:
    return round(float(value), 4)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _min_pairwise_distance(states: dict[str, RobotRuntimeState]) -> float | None:
    robots = list(states.values())
    if len(robots) < 2:
        return None
    distances = [
        _distance((a.x, a.y), (b.x, b.y))
        for i, a in enumerate(robots)
        for b in robots[i + 1 :]
    ]
    return min(distances)


def _goal_lookup(scenario: ScenarioConfig) -> dict[str, tuple[float, float]]:
    return {robot.robot_id: (robot.goal.x, robot.goal.y) for robot in scenario.robots}


def _head_on_active(scenario: ScenarioConfig, states: dict[str, RobotRuntimeState]) -> bool:
    involved = list(scenario.expected_conflict.involved_robots)
    if len(involved) != 2 or any(robot_id not in states for robot_id in involved):
        return False
    positions = [(states[robot_id].x, states[robot_id].y) for robot_id in involved]
    speeds = [states[robot_id].speed_mps for robot_id in involved]
    return head_on_conflict_active(positions, speeds)


def build_acceptance_record(
    sim_time_sec: float,
    scenario: ScenarioConfig,
    states: dict[str, RobotRuntimeState],
) -> dict[str, object]:
    goals = _goal_lookup(scenario)
    robots: dict[str, dict[str, float | None]] = {}
    for robot_id in sorted(states):
        state = states[robot_id]
        goal = goals.get(robot_id)
        distance_to_goal = None
        if goal is not None:
            distance_to_goal = _distance((state.x, state.y), goal)
        robots[robot_id] = {
            "x": _round4(state.x),
            "y": _round4(state.y),
            "theta": _round4(state.theta),
            "speed_mps": _round4(state.speed_mps),
            "goal_x": _round4(goal[0]) if goal is not None else None,
            "goal_y": _round4(goal[1]) if goal is not None else None,
            "distance_to_goal_m": (
                _round4(distance_to_goal) if distance_to_goal is not None else None
            ),
        }

    conflict_active = False
    if scenario.name == "head_on_deadlock":
        conflict_active = _head_on_active(scenario, states)

    min_distance = _min_pairwise_distance(states)
    return {
        "sim_time_sec": _round4(sim_time_sec),
        "robots": robots,
        "conflict_active": conflict_active,
        "conflict_type": scenario.expected_conflict.type,
        "involved_robots": list(scenario.expected_conflict.involved_robots),
        "min_pairwise_distance_m": (
            _round4(min_distance) if min_distance is not None else None
        ),
        "robot_static_contacts": [],
        "robot_robot_contacts": [],
    }


class AcceptanceLogger:
    def __init__(self, file: TextIO, scenario: ScenarioConfig, log_hz: float = 10.0) -> None:
        self._file = file
        self._scenario = scenario
        self._period_sec = 1.0 / log_hz
        self._next_log_sec = 0.0

    def maybe_write(self, sim_time_sec: float, states: dict[str, RobotRuntimeState]) -> None:
        if sim_time_sec + 1e-9 < self._next_log_sec:
            return
        record = build_acceptance_record(sim_time_sec, self._scenario, states)
        self._file.write(json.dumps(record, sort_keys=True) + "\n")
        self._next_log_sec += self._period_sec


class RobotPoseTracker:
    def __init__(self) -> None:
        self._previous: dict[str, tuple[float, float, float]] = {}

    def update_from_positions(
        self,
        sim_time_sec: float,
        positions: dict[str, tuple[float, float, float]],
    ) -> dict[str, RobotRuntimeState]:
        states: dict[str, RobotRuntimeState] = {}
        for robot_id, (x, y, theta) in positions.items():
            speed = 0.0
            prev = self._previous.get(robot_id)
            if prev is not None:
                prev_time, prev_x, prev_y = prev
                dt = sim_time_sec - prev_time
                if dt > 0.0:
                    speed = _distance((x, y), (prev_x, prev_y)) / dt
            states[robot_id] = RobotRuntimeState(
                robot_id=robot_id,
                x=x,
                y=y,
                theta=theta,
                speed_mps=speed,
            )
            self._previous[robot_id] = (sim_time_sec, x, y)
        return states


_CHASSIS_PATH_CACHE: dict[str, str] = {}


def find_chassis_prim(robot_root: Usd.Prim, articulation_api: type) -> Usd.Prim | None:
    """Find the physics chassis prim inside a robot's USD subtree.

    Args:
        robot_root: Robot root prim whose subtree is searched breadth-first.
        articulation_api: Articulation-root schema handed to `prim.HasAPI`.

    Returns:
        The prim carrying `articulation_api`, else the shallowest prim named
        `base_link`, else `None`.
    """
    fallback: Usd.Prim | None = None
    queue = [robot_root]
    while queue:
        prim = queue.pop(0)
        if prim.HasAPI(articulation_api):
            return prim
        if fallback is None and prim.GetName() == CHASSIS_LINK_NAME:
            fallback = prim
        queue.extend(prim.GetChildren())
    return fallback


def resolve_chassis_prim(
    stage: Usd.Stage, robot_id: str, articulation_api: type
) -> Usd.Prim:
    """Resolve a robot's chassis prim on `stage`, caching the subtree walk.

    The cache stores the resolved path rather than the prim handle, so a stage
    reload between repetitions cannot hand back an invalidated prim.

    Args:
        stage: USD stage holding `/World/Robots/<robot_id>`.
        robot_id: Robot id to resolve.
        articulation_api: Articulation-root schema handed to `prim.HasAPI`.

    Returns:
        The robot's chassis prim.

    Raises:
        ValueError: If the robot root prim or its chassis prim is not found.
    """
    cached_path = _CHASSIS_PATH_CACHE.get(robot_id)
    if cached_path is not None:
        cached_prim = stage.GetPrimAtPath(cached_path)
        if cached_prim and cached_prim.IsValid():
            return cached_prim

    root_path = f"/World/Robots/{robot_id}"
    root = stage.GetPrimAtPath(root_path)
    if not root or not root.IsValid():
        raise ValueError(
            f"Robot root prim not found for robot {robot_id!r} at {root_path}"
        )
    chassis = find_chassis_prim(root, articulation_api)
    if chassis is None:
        raise ValueError(
            f"No chassis prim found for robot {robot_id!r} under {root_path}: "
            f"expected a prim with ArticulationRootAPI or named "
            f"{CHASSIS_LINK_NAME!r}"
        )
    _CHASSIS_PATH_CACHE[robot_id] = str(chassis.GetPath())
    return chassis


def planar_pose_from_transform(matrix: Gf.Matrix4d) -> tuple[float, float, float]:
    """Extract a planar pose from a world transform matrix.

    Args:
        matrix: World transform whose translation is in meters.

    Returns:
        Planar pose as `(x, y, yaw_rad)`, yaw measured about world +Z.
    """
    translation = matrix.ExtractTranslation()
    rotation = matrix.ExtractRotation()
    yaw_rad = math.radians(rotation.Decompose((0, 0, 1), (0, 1, 0), (1, 0, 0))[0])
    return (float(translation[0]), float(translation[1]), yaw_rad)


def sample_robot_positions(
    stage: Usd.Stage, robot_ids: list[str]
) -> dict[str, tuple[float, float, float]]:
    """Sample each robot's world-frame planar pose from its chassis prim.

    Args:
        stage: USD stage holding `/World/Robots/<robot_id>`.
        robot_ids: Robots to sample.

    Returns:
        Mapping of robot id to `(x, y, yaw_rad)` in world meters and radians.

    Raises:
        ValueError: If a robot's root prim or chassis prim is not found.
    """
    from pxr import Usd, UsdGeom, UsdPhysics

    positions: dict[str, tuple[float, float, float]] = {}
    for robot_id in robot_ids:
        # Sample the chassis link, never /World/Robots/<id>: under the Newton
        # backend the robot root Xform keeps its authored spawn transform for the
        # whole run while physics writes pose onto the articulation's links, so
        # reading the root logged every robot parked at spawn with speed 0.
        chassis = resolve_chassis_prim(stage, robot_id, UsdPhysics.ArticulationRootAPI)
        matrix = UsdGeom.Xformable(chassis).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
        positions[robot_id] = planar_pose_from_transform(matrix)
    return positions
