from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import TextIO

from isaac.vgu_sim.config import ScenarioConfig
from isaac.vgu_sim.oracle import head_on_conflict_active


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


def sample_robot_positions(stage, robot_ids: list[str]) -> dict[str, tuple[float, float, float]]:
    from pxr import UsdGeom

    positions: dict[str, tuple[float, float, float]] = {}
    for robot_id in robot_ids:
        prim = stage.GetPrimAtPath(f"/World/Robots/{robot_id}")
        if not prim or not prim.IsValid():
            continue
        matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0.0)
        translation = matrix.ExtractTranslation()
        rotation = matrix.ExtractRotation()
        yaw_rad = math.radians(rotation.Decompose((0, 0, 1), (0, 1, 0), (1, 0, 0))[0])
        positions[robot_id] = (float(translation[0]), float(translation[1]), yaw_rad)
    return positions
