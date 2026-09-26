"""Snapshot history -> per-robot motion table (rev-8 temporal context, no ROS2)."""

import math
from collections.abc import Sequence

from reasoning.vlm.models import MotionTable, MotionTableEntry, SnapshotFrame


def derive_motion_table(
    frames: Sequence[SnapshotFrame],
    conflict_center: tuple[float, float],
    conflict_radius_m: float,
) -> MotionTable:
    """Summarize buffered snapshots into per-robot conflict-zone arrival evidence.

    A robot "arrives" in the first frame (by stamp) where its world-frame
    position lies within `conflict_radius_m` of `conflict_center`, boundary
    included. Arrival order ranks arrival stamps ascending; equal stamps rank
    by `robot_id`.

    Args:
        frames: Snapshot history in any order; sorted by stamp internally.
        conflict_center: World-frame center of the conflict zone `(x, y)` in
            meters.
        conflict_radius_m: Zone radius in meters.

    Returns:
        Table with one entry per robot present in the latest frame, sorted by
        `robot_id`.

    Raises:
        ValueError: If `frames` is empty or `conflict_radius_m` is not positive.
    """
    if not frames:
        raise ValueError("derive_motion_table requires at least one frame")
    if conflict_radius_m <= 0.0:
        raise ValueError(f"conflict_radius_m must be positive, got {conflict_radius_m}")
    ordered = sorted(frames, key=lambda frame: frame.stamp)

    arrival_by_id: dict[str, float | None] = {}
    for robot_id in sorted(state.robot_id for state in ordered[-1].robots):
        arrival_by_id[robot_id] = _arrival_stamp(
            ordered, robot_id, conflict_center, conflict_radius_m
        )

    ranked = sorted(
        (stamp, robot_id) for robot_id, stamp in arrival_by_id.items() if stamp is not None
    )
    order_by_id = {robot_id: rank + 1 for rank, (_, robot_id) in enumerate(ranked)}
    entries = [
        MotionTableEntry(
            robot_id=robot_id,
            arrival_order=order_by_id.get(robot_id),
            arrival_stamp=stamp,
        )
        for robot_id, stamp in arrival_by_id.items()
    ]
    return MotionTable(window_sec=ordered[-1].stamp - ordered[0].stamp, entries=entries)


def _arrival_stamp(
    ordered: list[SnapshotFrame],
    robot_id: str,
    center: tuple[float, float],
    radius_m: float,
) -> float | None:
    for frame in ordered:
        state = frame.find_robot(robot_id)
        if state is not None and math.hypot(state.x - center[0], state.y - center[1]) <= radius_m:
            return frame.stamp
    return None
