"""Pure SE(2) maths behind camera-based localization (`map -> <robot>/odom`).

M1's overhead camera already measures every robot's absolute pose in the world
frame, which is the same frame Nav2 calls `map`. Nav2 does not consume poses
though — it consumes the TF edge `map -> <robot>/odom`, the edge AMCL normally
owns. This module derives that edge from two poses of the same robot base:

    T_map_odom = T_map_base . T_odom_base^-1

`T_map_base` is the camera measurement; `T_odom_base` is Isaac's odometry
(spawn-relative and drift-free). Everything here is planar SE(2) and free of
ROS imports so it can be unit-tested without a ROS 2 installation; the node
wrapper in `camera_localizer_node.py` owns all message and TF plumbing.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

Pose2D = tuple[float, float, float]
"""Planar pose as `(x, y, yaw)`: metres in the parent frame, yaw in radians."""

_REQUIRED_POSE_KEYS = ("x", "y", "theta")

DEFAULT_M1_LATENCY_COMPENSATION_SEC = 0.01
"""M1's measured upstream latency: a pose stamped `s` is the robot's pose at `s - d`.

Measured in the ROS domain only (truth = spawn . drift-free odometry, no GT
clock involved), on FRESH detections (robot stamp == scene stamp) with M1's
constant position bias removed, in the three costmap-probe bags
(`scripts/m1_latency_fit.py`, `docs/reports/2026-10-05-costmap-fix-validation.md`):
six per-run translation/rotation fits span -0.015..0.060 s, median 0.0075 s,
rounded to 0.01 s -- under a third of a 30 Hz camera frame. The probe report's
"M1 upstream 0.04-0.20 s" included carried-forward rows (see
`odom_lookup_stamp`); on fresh detections the latency is near zero.
"""

def _numeric(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def odom_lookup_stamp(
    scene_state: Mapping[str, object],
    robot_id: str,
    latency_compensation_sec: float = DEFAULT_M1_LATENCY_COMPENSATION_SEC,
) -> float | None:
    """Return the ROS time at which this robot's M1 pose was true (the A-prime pairing).

    The odometry pose composed with an M1 pose must be the odometry at the
    instant that M1 pose depicts. That instant is the robot entry's OWN `stamp`
    (the frame of its last fresh detection), not the scene stamp: during a fast
    turn M1 loses the marker for up to ~0.6 s and carries the last pose
    forward with its old stamp while the scene stamp advances, and pairing
    that carried pose with newer odometry injected up to 0.46 rad of yaw error
    (costmap-probe bags, `markers_detected: 0` rows). Pairing at the robot
    stamp instead reproduces the original correction exactly (odometry is
    drift-free), so a carried row becomes a natural hold. The measured
    upstream latency is then subtracted.

    Args:
        scene_state: Parsed `/perception/scene_state` payload.
        robot_id: Robot whose pose time is wanted.
        latency_compensation_sec: M1's upstream latency `d` (seconds).

    Returns:
        `robot.stamp - d`, or `scene.stamp - d` when the robot entry carries no
        usable stamp, or None when the robot is absent or no stamp is usable.
    """
    entry = _find_robot(scene_state, robot_id)
    if entry is None:
        return None
    stamp = _numeric(entry.get("stamp"))
    if stamp is None:
        stamp = _numeric(scene_state.get("stamp"))
    if stamp is None:
        return None
    return stamp - latency_compensation_sec


def normalize_yaw(yaw: float) -> float:
    """Wrap an angle into the half-open interval `(-pi, pi]`.

    Args:
        yaw: Angle in radians, of any magnitude.

    Returns:
        The equivalent angle in `(-pi, pi]`.
    """
    # atan2 is used rather than the `(yaw + pi) % (2 * pi) - pi` idiom because
    # that idiom maps an exact +pi to -pi, which would flip the heading of the
    # pi-spawned robot in this scenario on every normalization pass.
    wrapped = math.atan2(math.sin(yaw), math.cos(yaw))
    # atan2 returns [-pi, pi]; move the closed -pi endpoint to +pi so the
    # interval is exactly (-pi, pi] and the two endpoints cannot alternate.
    if wrapped <= -math.pi:
        return math.pi
    return wrapped


def compose(a: Pose2D, b: Pose2D) -> Pose2D:
    """Compose two planar transforms as `a . b`.

    Args:
        a: Transform from frame P to frame Q, as `(x, y, yaw)`.
        b: Transform from frame Q to frame R, expressed in frame Q.

    Returns:
        Transform from frame P to frame R.
    """
    ax, ay, ayaw = a
    bx, by, byaw = b
    cos_a = math.cos(ayaw)
    sin_a = math.sin(ayaw)
    return (
        ax + cos_a * bx - sin_a * by,
        ay + sin_a * bx + cos_a * by,
        normalize_yaw(ayaw + byaw),
    )


def invert(a: Pose2D) -> Pose2D:
    """Invert a planar transform.

    Args:
        a: Transform from frame P to frame Q, as `(x, y, yaw)`.

    Returns:
        Transform from frame Q to frame P.
    """
    ax, ay, ayaw = a
    cos_a = math.cos(ayaw)
    sin_a = math.sin(ayaw)
    return (
        -(cos_a * ax + sin_a * ay),
        sin_a * ax - cos_a * ay,
        normalize_yaw(-ayaw),
    )


def map_to_odom(camera_pose: Pose2D, odom_pose: Pose2D) -> Pose2D:
    """Derive the `map -> odom` correction from a camera pose and an odometry pose.

    Args:
        camera_pose: `map -> base` from the overhead camera, as `(x, y, yaw)`.
        odom_pose: `odom -> base` from wheel odometry, as `(x, y, yaw)`.

    Returns:
        `map -> odom` as `(x, y, yaw)`. With drift-free odometry this equals the
        robot's spawn pose, i.e. what the ground-truth static transform publishes.
    """
    return compose(camera_pose, invert(odom_pose))


def _pose_from_robot_entry(entry: Mapping[str, object]) -> Pose2D | None:
    """Read `(x, y, theta)` from one scene-state robot entry, or None if unusable."""
    values: list[float] = []
    for key in _REQUIRED_POSE_KEYS:
        value = entry.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        values.append(float(value))
    return (values[0], values[1], normalize_yaw(values[2]))


def _find_robot(
    scene_state: Mapping[str, object], robot_id: str
) -> Mapping[str, object] | None:
    """Return this robot's entry from a scene-state payload, or None if absent."""
    robots = scene_state.get("robots")
    if not isinstance(robots, list):
        return None
    for entry in robots:
        if isinstance(entry, Mapping) and entry.get("robot_id") == robot_id:
            return entry
    return None


class CameraLocalizer:
    """Track one robot's `map -> odom` correction from M1 scene states.

    The correction is held rather than dropped whenever a usable fix is missing
    (robot absent from the frame, marker `STALE`, or no odometry yet). Odometry
    is drift-free here, so a held correction stays valid indefinitely — the same
    behaviour AMCL exhibits between its own updates, and the reason a dropped
    camera frame does not break a costmap that needs `map -> odom` every cycle.
    """

    def __init__(
        self, robot_id: str, initial_map_to_odom: Pose2D | None = None
    ) -> None:
        """Create a localizer for one robot.

        Args:
            robot_id: Robot id as it appears in scene-state `robots[].robot_id`.
            initial_map_to_odom: Optional `map -> odom` seed, held as `latest`
                until the first real camera fix replaces it. Mirrors AMCL's
                `set_initial_pose`: odometry is spawn-relative (identity at
                t=0), so the robot's spawn pose in `map` already equals
                `map -> odom` at startup, letting a Nav2 costmap that needs
                this edge activate immediately instead of blocking on this
                localizer's first scene-state fix. Does not count toward
                `updates` — it is a seed, not a fix.
        """
        self._robot_id = robot_id
        self._latest = initial_map_to_odom
        self._seeded = initial_map_to_odom is not None
        self._last_update_stamp: float | None = None
        self.updates = 0
        self.holds = 0

    @property
    def robot_id(self) -> str:
        """Robot id this localizer tracks."""
        return self._robot_id

    @property
    def latest(self) -> Pose2D | None:
        """Most recent `map -> odom` correction, or None before the first fix."""
        return self._latest

    @property
    def seeded(self) -> bool:
        """True while `latest` is still the constructor seed, not a camera fix.

        False when constructed without a seed, and permanently False from the
        moment the first real camera fix lands, even if that fix is later held
        over by subsequent misses.
        """
        return self._seeded

    @property
    def last_update_stamp(self) -> float | None:
        """Scene-state stamp of the last successful update, or None if never."""
        return self._last_update_stamp

    def update(
        self, scene_state: Mapping[str, object], odom_pose: Pose2D | None
    ) -> Pose2D | None:
        """Fold one scene state and one odometry pose into the held correction.

        Args:
            scene_state: Parsed `/perception/scene_state` payload.
            odom_pose: `odom -> base` pose from TF, or None when unavailable.

        Returns:
            The new correction, or the held one when this scene state carries no
            usable fix for this robot (None if there has never been a fix).
        """
        entry = _find_robot(scene_state, self._robot_id)
        camera_pose = None if entry is None else _pose_from_robot_entry(entry)
        # A STALE marker means M1 is extrapolating a robot it can no longer see,
        # so its pose must not correct the TF tree; hold instead.
        stale = entry is not None and entry.get("status") == "STALE"
        if camera_pose is None or stale or odom_pose is None:
            self.holds += 1
            return self._latest

        self._latest = map_to_odom(camera_pose, odom_pose)
        self._seeded = False
        stamp = scene_state.get("stamp")
        if isinstance(stamp, (int, float)) and not isinstance(stamp, bool):
            self._last_update_stamp = float(stamp)
        self.updates += 1
        return self._latest
