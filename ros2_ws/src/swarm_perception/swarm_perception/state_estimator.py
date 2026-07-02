from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Literal

from swarm_perception.models import MarkerDetection, RobotState, SceneState


def estimate_velocity(
    previous: RobotState,
    current_pose: tuple[float, float, float],
    current_stamp: float,
) -> tuple[float, float]:
    """Return (linear_velocity m/s, angular_velocity rad/s) from two poses.

    Returns ``(0.0, 0.0)`` for a non-positive time delta (``dt <= 0``), which
    covers duplicate stamps and out-of-order/reordered frames after a ROS time
    jump. Without this guard a stale frame would yield a negative speed and
    corrupt motion classification.
    """
    dt = current_stamp - previous.stamp
    if dt <= 0.0:
        return 0.0, 0.0
    dx = current_pose[0] - previous.x
    dy = current_pose[1] - previous.y
    linear_velocity = math.sqrt(dx * dx + dy * dy) / dt
    dtheta = current_pose[2] - previous.theta
    dtheta = (dtheta + math.pi) % (2 * math.pi) - math.pi  # normalize to [-π, π]
    angular_velocity = dtheta / dt
    return linear_velocity, angular_velocity


def low_pass_filter(previous_value: float, measured_value: float, alpha: float) -> float:
    """First-order low-pass: alpha=1 → raw measurement; alpha=0 → no change."""
    return alpha * measured_value + (1.0 - alpha) * previous_value


def classify_motion_status(
    linear_velocity: float,
    age_sec: float,
    stopped_threshold_mps: float,
    slow_threshold_mps: float,
    stale_after_sec: float,
) -> Literal["MOVING", "SLOW", "STOPPED", "STALE"]:
    if age_sec >= stale_after_sec:
        return "STALE"
    speed = abs(linear_velocity)
    if speed < stopped_threshold_mps:
        return "STOPPED"
    if speed < slow_threshold_mps:
        return "SLOW"
    return "MOVING"


def build_scene_diagnostics(
    detections: Sequence[MarkerDetection],
    expected_robot_ids: set[str],
    dropped_frame: bool = False,
) -> dict[str, object]:
    """Build per-frame health diagnostics; called internally by StateEstimator.update."""
    detected_ids = {f"robot_{d.marker_id}" for d in detections}
    ids_missing = sorted(expected_robot_ids - detected_ids)
    ids_unexpected = sorted(detected_ids - expected_robot_ids) if expected_robot_ids else []
    return {
        "markers_detected": len(detections),
        "ids_missing": ids_missing,
        "ids_unexpected": ids_unexpected,
        "dropped_frame": dropped_frame,
    }


class StateEstimator:
    def __init__(
        self,
        stopped_threshold_mps: float = 0.01,
        slow_threshold_mps: float = 0.05,
        stale_after_sec: float = 1.0,
        velocity_alpha: float = 0.3,
        frame_id: str = "overhead_camera",
    ) -> None:
        self._stopped = stopped_threshold_mps
        self._slow = slow_threshold_mps
        self._stale = stale_after_sec
        self._alpha = velocity_alpha
        self._frame_id = frame_id
        self._tracked: dict[str, RobotState] = {}
        self._last_stamp: float | None = None

    def update(
        self,
        detections: Sequence[MarkerDetection],
        stamp: float,
        task_registry: Mapping[str, Mapping[str, object]] | None = None,
        expected_robot_ids: set[str] | None = None,
        dropped_frame: bool = False,
        frame_id: str | None = None,
    ) -> SceneState:
        registry = task_registry or {}
        # None means no allowlist (standalone mode); a set (even empty) means filter strictly.
        filter_ids = expected_robot_ids
        expected = expected_robot_ids or set()

        # Remove any previously tracked IDs that are no longer in the allowlist.
        # This prevents a rogue marker seen before a registry was established from
        # carrying forward indefinitely as STALE.
        if filter_ids is not None:
            for rogue_id in set(self._tracked) - filter_ids:
                del self._tracked[rogue_id]

        # A frame older than the latest one already processed is a late frame.
        # We cannot build a temporally consistent snapshot for a past time
        # (carried-forward robots would carry newer stamps than the frame), so we
        # suppress robot output and flag it as dropped. Downstream consumers
        # (M2/M5) are expected to ignore dropped frames.
        if self._last_stamp is not None and stamp < self._last_stamp:
            diagnostics = build_scene_diagnostics(detections, expected, dropped_frame=True)
            return SceneState(
                stamp=stamp,
                frame_id=frame_id or self._frame_id,
                robots=[],
                diagnostics=diagnostics,
            )

        updated_ids: set[str] = set()
        for det in detections:
            robot_id = f"robot_{det.marker_id}"
            if filter_ids is not None and robot_id not in filter_ids:
                continue
            prev = self._tracked.get(robot_id)

            # Ignore out-of-order detections: a stamp not newer than the tracked
            # state would overwrite the current pose with a stale one and then
            # produce a spurious velocity on the next in-order frame. The robot
            # is left to carry forward its existing state below.
            if prev is not None and stamp <= prev.stamp:
                continue
            updated_ids.add(robot_id)

            reg = registry.get(robot_id) or {}
            task: str | None = reg.get("task")  # type: ignore[assignment]
            goal: tuple[float, float] | None = None
            goal_raw = reg.get("goal")
            if goal_raw is not None:
                try:
                    goal = (float(goal_raw["x"]), float(goal_raw["y"]))
                except (TypeError, KeyError):
                    goal = None

            pose = (det.center_world[0], det.center_world[1], det.theta)

            if prev is not None:
                raw_lv, raw_av = estimate_velocity(prev, pose, stamp)
                lv = low_pass_filter(prev.linear_velocity, raw_lv, self._alpha)
                av = low_pass_filter(prev.angular_velocity, raw_av, self._alpha)
            else:
                lv, av = 0.0, 0.0

            status = classify_motion_status(lv, 0.0, self._stopped, self._slow, self._stale)
            robot_state = RobotState(
                robot_id=robot_id,
                x=pose[0],
                y=pose[1],
                theta=pose[2],
                linear_velocity=lv,
                angular_velocity=av,
                task=task,
                status=status,
                goal=goal,
                stamp=stamp,
            )
            self._tracked[robot_id] = robot_state

        robots: list[RobotState] = [self._tracked[rid] for rid in updated_ids]

        for robot_id, prev_state in self._tracked.items():
            if robot_id in updated_ids:
                continue
            age = stamp - prev_state.stamp
            status = classify_motion_status(
                prev_state.linear_velocity, age, self._stopped, self._slow, self._stale
            )
            carry = RobotState(
                robot_id=prev_state.robot_id,
                x=prev_state.x,
                y=prev_state.y,
                theta=prev_state.theta,
                linear_velocity=prev_state.linear_velocity,
                angular_velocity=prev_state.angular_velocity,
                task=prev_state.task,
                status=status,
                goal=prev_state.goal,
                stamp=prev_state.stamp,
            )
            self._tracked[robot_id] = carry
            robots.append(carry)

        self._last_stamp = stamp if self._last_stamp is None else max(self._last_stamp, stamp)

        diagnostics = build_scene_diagnostics(detections, expected, dropped_frame)
        return SceneState(
            stamp=stamp,
            frame_id=frame_id or self._frame_id,
            robots=robots,
            diagnostics=diagnostics,
        )
