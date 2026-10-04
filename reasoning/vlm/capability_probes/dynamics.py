"""GT-derived answers for the battery-v2 dynamic probe types (registered 2026-10-04).

Battery v2 (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "Battery
v2 -- predictive/temporal probes") adds three probe types whose answers depend
on robot MOTION, not on a single pose: `motion_direction`,
`conflict_prediction` and `temporal_order`. Every answer here is computed from
Isaac Sim's own ground-truth log (`gt/ground_truth.jsonl`, 10 Hz world-frame
poses), never hand-labeled. These are pure functions over already-loaded GT
rows and log-derived event windows, so the build script and the auditor share
one definition and the rules are unit-testable on synthetic tracks.

Motion is always the GT POSITION difference over a short backward window,
never `theta x speed_mps`: GT `speed_mps` is unsigned, and M1's drawn arrow
follows the heading even when a robot reverses (M4 backup), so a heading-based
velocity would be wrong exactly when the frame is most misleading.

Registered constants (frozen with `manifest_v2`; changing one is a new
manifest, never a silent edit) are module-level below, each with its reason.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# Dynamic items need the GT row AT the frame, not near it: a robot moving at
# 0.2 m/s covers 0.1 m in 0.5 s, v1's (static) tolerance. GT is logged at
# 10 Hz, so the nearest row is always within 0.05 s when the log is intact.
DYNAMIC_GT_MATCH_TOLERANCE_SEC = 0.1

# Velocity is the backward difference over this window ending at the frame:
# "currently moving" must be judgeable from what already happened by the
# stamp (the trail overlay and M1's arrow both summarise the past).
MOTION_WINDOW_SEC = 0.5

# Speed bands (m/s). A robot is MOVING at or above the upper bound and
# STATIONARY at or below the lower bound; between them its motion is too slow
# to call either way, and any item whose answer depends on such a robot is
# dropped. 0.08 sits under Nav2's ~0.09 m/s creep speed seen in the head-on
# runs; 0.03 is well above GT jitter on a parked robot (< 0.005).
MOVING_MIN_SPEED_MPS = 0.08
STATIONARY_MAX_SPEED_MPS = 0.03

# "Moving toward X": the robot is MOVING and its image-space motion direction
# is within this angle of the bearing to X. "Not moving toward X": STATIONARY,
# or MOVING at least `NOT_TOWARD_MIN_ANGLE_DEG` away from the bearing. The gap
# between the two is the registered margin: an option robot inside it makes
# the item ambiguous, so it is dropped.
TOWARD_MAX_ANGLE_DEG = 30.0
NOT_TOWARD_MIN_ANGLE_DEG = 75.0

# A MOVING robot whose motion is more than this far off its own GT heading is
# reversing; M1 draws its arrow along the heading, so the frame shows the
# opposite of its real motion. Items naming or offering such a robot are
# dropped (the arrow would be evidence AGAINST the GT answer).
REVERSING_MIN_ANGLE_DEG = 90.0

# Conflict prediction: "will A and B come within 0.5 m (centre to centre) in
# the next 10 s". The registered threshold/horizon from the spec, plus a margin
# band on the future minimum distance -- head-on standoffs settle at 0.2-0.4 m
# and convoy following gaps near the threshold, so a minimum distance inside
# (0.40, 0.65) is too close to 0.5 m to grade either way and is dropped.
CONFLICT_THRESHOLD_M = 0.5
CONFLICT_HORIZON_SEC = 10.0
CONFLICT_YES_MAX_M = 0.40
CONFLICT_NO_MIN_M = 0.65
# The pair must be clearly apart at the stamp (else the item is a static
# proximity question, not a prediction) and at least one of them MOVING (for
# yes and no items alike, so "no" cannot be answered by "nothing moves").
CONFLICT_MIN_CURRENT_DISTANCE_M = 0.75
# ...and the threshold must be reachable at the pair's CURRENT speeds within
# the horizon (gap - 0.5 m <= 10 s x (speed_a + speed_b)); otherwise "no" is
# answerable from separation alone, which would make the no-class trivial
# (the dry scan of the logged decision frames was 20/20 such "no" items at
# 3.5-4.1 m apart, 2026-10-04).

# Temporal order: the frame is taken AFTER both events, within the trail
# window after the later one (M1 `motion_trail_window_sec` = 3.0 s), so the
# later robot's approach is still drawn on a trails-on frame; and the two
# events are at least 2 s apart so "first" is not a near-tie.
TEMPORAL_WINDOW_SEC = (0.5, 3.0)
TEMPORAL_MIN_GAP_SEC = 2.0
# Trails pairs (same question on a trails-off and a trails-on frame of
# matched GT configuration): for temporal_order the two frames must also sit
# at nearly the same time after the later event, so the trail shows the same
# amount of the later robot's approach.
PAIR_EVENT_LAG_TOLERANCE_SEC = 0.5
# Goal arrival = GT distance-to-goal at or under this (M5's own arrival
# tolerance is 0.35 m; tighter here so the event time is the physical arrival,
# not a tolerance-band entry).
GOAL_ARRIVAL_TOLERANCE_M = 0.20
# A robot still counts as "at its goal" at the frame within this distance.
GOAL_HOLD_TOLERANCE_M = 0.35
# Standoff stop = the start of the robot's current STATIONARY run, preceded
# by MOVING motion within this many seconds, with the pair within
# `STANDOFF_MAX_DISTANCE_M` of each other at the frame.
STOP_PRECEDING_MOTION_SEC = 1.5
STANDOFF_MAX_DISTANCE_M = 1.0

# Command-activity windows (conflict_prediction exclusion): a dispatched
# command's sim-time window is widened by this slack at its end, and a robot's
# first motion onset (initial / delayed task dispatch) is an event window of
# +-`ONSET_HALF_WINDOW_SEC`.
COMMAND_END_SLACK_SEC = 1.0
ONSET_HALF_WINDOW_SEC = 1.0
ONSET_SPEED_MPS = 0.05

EDGE_DIRECTIONS_PX: dict[str, tuple[float, float]] = {
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
    "top": (0.0, -1.0),
    "bottom": (0.0, 1.0),
}


class GtTrack:
    """Time-indexed GT rows of one episode, with nearest-row and velocity lookups."""

    def __init__(self, rows: Sequence[dict]) -> None:
        """Index `rows` (any order) by `sim_time_sec`.

        Args:
            rows: Parsed `ground_truth.jsonl` rows.
        """
        self.rows = sorted(rows, key=lambda r: r["sim_time_sec"])
        self.times = [r["sim_time_sec"] for r in self.rows]

    @property
    def end_time(self) -> float:
        """Sim time of the last GT row (or -inf for an empty log)."""
        return self.times[-1] if self.times else -math.inf

    def row_near(self, t: float, tolerance: float = DYNAMIC_GT_MATCH_TOLERANCE_SEC) -> dict | None:
        """Return the row nearest `t`, or None when none is within `tolerance`."""
        if not self.rows:
            return None
        i = bisect.bisect_left(self.times, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(self.rows):
                if best is None or abs(self.times[j] - t) < abs(self.times[best] - t):
                    best = j
        if best is None or abs(self.times[best] - t) > tolerance:
            return None
        return self.rows[best]

    def rows_between(self, start: float, end: float) -> list[dict]:
        """Return rows with `start < sim_time_sec <= end`."""
        lo = bisect.bisect_right(self.times, start)
        hi = bisect.bisect_right(self.times, end)
        return self.rows[lo:hi]

    def velocity(
        self, robot_id: str, t: float, window: float = MOTION_WINDOW_SEC
    ) -> tuple[float, float] | None:
        """Return the backward-difference world velocity `(vx, vy)` m/s at `t`.

        Returns:
            None when either end of the window has no GT row in tolerance or
            the robot is missing from one of them.
        """
        now = self.row_near(t)
        before = self.row_near(t - window)
        if now is None or before is None:
            return None
        if robot_id not in now["robots"] or robot_id not in before["robots"]:
            return None
        dt = now["sim_time_sec"] - before["sim_time_sec"]
        if dt <= 0:
            return None
        a, b = before["robots"][robot_id], now["robots"][robot_id]
        return (b["x"] - a["x"]) / dt, (b["y"] - a["y"]) / dt

    def speed(self, robot_id: str, t: float) -> float | None:
        """Return `|velocity(robot_id, t)|`, or None when unavailable."""
        v = self.velocity(robot_id, t)
        return None if v is None else math.hypot(*v)


def motion_class(speed: float | None) -> str:
    """Classify a speed as "moving", "stationary" or "ambiguous" (registered bands)."""
    if speed is None:
        return "ambiguous"
    if speed >= MOVING_MIN_SPEED_MPS:
        return "moving"
    if speed <= STATIONARY_MAX_SPEED_MPS:
        return "stationary"
    return "ambiguous"


def angle_between_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return the unsigned angle between two 2D vectors, degrees (180 if either is zero)."""
    na, nb = math.hypot(*a), math.hypot(*b)
    if na == 0 or nb == 0:
        return 180.0
    cos = max(-1.0, min(1.0, (a[0] * b[0] + a[1] * b[1]) / (na * nb)))
    return math.degrees(math.acos(cos))


def is_reversing(velocity: tuple[float, float], theta: float) -> bool:
    """Return whether world `velocity` points more than 90 deg off heading `theta`."""
    return angle_between_deg(velocity, (math.cos(theta), math.sin(theta))) > REVERSING_MIN_ANGLE_DEG


@dataclass(frozen=True)
class RobotMotion:
    """One robot's motion at the frame stamp, in both world and image terms."""

    robot_id: str
    speed_mps: float
    motion: str  # "moving" | "stationary" | "ambiguous"
    reversing: bool
    # Image-space unit-free motion direction `(du, dv)` (pixels per 0.5 s of
    # the GT velocity, projected through the homography), and the robot's
    # pixel position.
    pixel_motion: tuple[float, float]
    pixel: tuple[float, float]


def toward_class(motion: RobotMotion, bearing_px: tuple[float, float]) -> str:
    """Classify a robot as "toward", "not_toward" or "ambiguous" w.r.t. an image bearing."""
    if motion.motion == "stationary":
        return "not_toward"
    if motion.motion == "ambiguous":
        return "ambiguous"
    angle = angle_between_deg(motion.pixel_motion, bearing_px)
    if angle <= TOWARD_MAX_ANGLE_DEG:
        return "toward"
    if angle >= NOT_TOWARD_MIN_ANGLE_DEG:
        return "not_toward"
    return "ambiguous"


def motion_direction_answer(
    motions: dict[str, RobotMotion], target: str
) -> tuple[str | None, str, dict[str, str]]:
    """Return the single robot moving toward `target`, or why there is none.

    Args:
        motions: robot_id -> `RobotMotion` for every robot in the frame.
        target: `"robot:<id>"` (options = every other robot; needs >= 3
            robots) or `"edge:<left|right|top|bottom>"` (options = every
            robot; needs >= 2).

    Returns:
        `(correct_robot_id | None, reason, classes)`; `reason` is `"ok"` or a
        drop reason (`too_few_options`, `ambiguous_option`, `reversing_robot`,
        `no_robot_toward`, `several_robots_toward`); `classes` maps each
        option robot to its toward-class (for the manifest's derivation
        record).
    """
    kind, _, name = target.partition(":")
    if kind == "robot":
        if name not in motions:
            return None, "target_missing", {}
        options = sorted(rid for rid in motions if rid != name)
        tx, ty = motions[name].pixel
    elif kind == "edge" and name in EDGE_DIRECTIONS_PX:
        options = sorted(motions)
    else:
        raise ValueError(f"unknown motion_direction target {target!r}")
    if len(options) < 2:
        return None, "too_few_options", {}

    classes: dict[str, str] = {}
    for rid in options:
        m = motions[rid]
        if kind == "robot":
            bearing = (tx - m.pixel[0], ty - m.pixel[1])
        else:
            bearing = EDGE_DIRECTIONS_PX[name]
        classes[rid] = toward_class(m, bearing)
    if any(motions[rid].motion == "moving" and motions[rid].reversing for rid in options):
        return None, "reversing_robot", classes
    if any(c == "ambiguous" for c in classes.values()):
        return None, "ambiguous_option", classes
    toward = [rid for rid, c in classes.items() if c == "toward"]
    if not toward:
        return None, "no_robot_toward", classes
    if len(toward) > 1:
        return None, "several_robots_toward", classes
    return toward[0], "ok", classes


def pair_distance(row: dict, a: str, b: str) -> float:
    """Centre-to-centre GT distance between robots `a` and `b` in one row."""
    ra, rb = row["robots"][a], row["robots"][b]
    return math.hypot(ra["x"] - rb["x"], ra["y"] - rb["y"])


def conflict_prediction_answer(
    track: GtTrack, a: str, b: str, t: float
) -> tuple[str | None, str, dict[str, float]]:
    """Return "yes"/"no" for "will a and b come within 0.5 m in the next 10 s".

    Kinematic conditions only (current separation, one of the pair moving,
    the future minimum distance outside the margin band, GT covering the
    horizon); the command-activity exclusion is `horizon_is_command_free`'s
    job, applied by the caller.

    Returns:
        `(answer | None, reason, facts)` with `facts` holding the current
        distance, the future minimum distance and both speeds.
    """
    now = track.row_near(t)
    if now is None or a not in now["robots"] or b not in now["robots"]:
        return None, "no_matching_gt", {}
    if track.end_time < t + CONFLICT_HORIZON_SEC:
        return None, "horizon_beyond_gt", {}
    d0 = pair_distance(now, a, b)
    sa, sb = track.speed(a, t), track.speed(b, t)
    facts = {"current_distance_m": d0}
    if sa is None or sb is None:
        return None, "no_matching_gt", facts
    facts.update({"speed_a_mps": sa, "speed_b_mps": sb})
    if d0 < CONFLICT_MIN_CURRENT_DISTANCE_M:
        return None, "already_close", facts
    if motion_class(sa) != "moving" and motion_class(sb) != "moving":
        return None, "pair_not_moving", facts
    if d0 - CONFLICT_THRESHOLD_M > CONFLICT_HORIZON_SEC * (sa + sb):
        return None, "threshold_unreachable", facts
    future = [
        r
        for r in track.rows_between(t, t + CONFLICT_HORIZON_SEC)
        if a in r["robots"] and b in r["robots"]
    ]
    if not future:
        return None, "horizon_beyond_gt", facts
    d_min = min(pair_distance(r, a, b) for r in future)
    facts["future_min_distance_m"] = d_min
    if d_min <= CONFLICT_YES_MAX_M:
        return "yes", "ok", facts
    if d_min >= CONFLICT_NO_MIN_M:
        return "no", "ok", facts
    return None, "margin_too_small", facts


def horizon_is_command_free(
    t: float, horizon: float, windows: Iterable[tuple[float, float]]
) -> bool:
    """Return whether `[t, t + horizon]` overlaps no command-activity window.

    The registered exclusion: an item is judgeable from the kinematics visible
    at its stamp only if no dispatched command is active at the stamp or
    starts/acts within the horizon. Since the no-command outcome cannot be
    observed, this is a conservative SUPERSET of "a command changes the
    answer": any overlap excludes the item.
    """
    end = t + horizon
    return all(w_end < t or w_start > end for w_start, w_end in windows)


def wall_to_sim(wall: float, anchors: Sequence[tuple[float, float]]) -> float:
    """Map an epoch wall time into sim time via `(wall, sim)` anchors.

    Linear interpolation between the bracketing anchors; outside them, the
    sim clock is assumed to advance at most as fast as wall time (Isaac runs
    at real-time factor <= 1 on this host), which over-estimates elapsed sim
    time -- conservative for an END time, and the caller uses decision stamps
    (never this mapping) for START times.

    Args:
        wall: Epoch seconds from a ROS log line.
        anchors: `(wall_sec, sim_sec)` pairs, any order, at least one.
    """
    if not anchors:
        raise ValueError("need at least one (wall, sim) anchor")
    pts = sorted(anchors)
    if wall <= pts[0][0]:
        return pts[0][1] - (pts[0][0] - wall)
    if wall >= pts[-1][0]:
        return pts[-1][1] + (wall - pts[-1][0])
    for (w0, s0), (w1, s1) in zip(pts, pts[1:], strict=False):
        if w0 <= wall <= w1:
            if w1 == w0:
                return max(s0, s1)
            return s0 + (s1 - s0) * (wall - w0) / (w1 - w0)
    return pts[-1][1]


def motion_onset_times(track: GtTrack) -> dict[str, float]:
    """Return each robot's first motion onset (GT speed >= `ONSET_SPEED_MPS`).

    A robot's first move is the effect of a task dispatch (initial or
    delayed start), not visible before it happens.
    """
    onsets: dict[str, float] = {}
    for row in track.rows:
        for rid in row["robots"]:
            if rid in onsets:
                continue
            speed = track.speed(rid, row["sim_time_sec"])
            if speed is not None and speed >= ONSET_SPEED_MPS:
                onsets[rid] = row["sim_time_sec"]
    return onsets


def goal_arrival_time(track: GtTrack, robot_id: str, t: float) -> float | None:
    """Return when `robot_id` reached the goal it still holds at `t`, or None.

    The robot must be within `GOAL_HOLD_TOLERANCE_M` of the same goal at every
    GT row from the arrival to `t` (it has arrived and stayed), and the
    arrival is the first row of that run at or under
    `GOAL_ARRIVAL_TOLERANCE_M`.
    """
    now = track.row_near(t)
    if now is None or robot_id not in now["robots"]:
        return None
    goal_now = (now["robots"][robot_id].get("goal_x"), now["robots"][robot_id].get("goal_y"))
    if goal_now[0] is None or now["robots"][robot_id].get("distance_to_goal_m") is None:
        return None
    if now["robots"][robot_id]["distance_to_goal_m"] > GOAL_HOLD_TOLERANCE_M:
        return None
    i = bisect.bisect_right(track.times, now["sim_time_sec"]) - 1
    arrival = None
    while i >= 0:
        r = track.rows[i]["robots"].get(robot_id)
        if r is None or (r.get("goal_x"), r.get("goal_y")) != goal_now:
            break
        dist = r.get("distance_to_goal_m")
        if dist is None or dist > GOAL_HOLD_TOLERANCE_M:
            break
        if dist <= GOAL_ARRIVAL_TOLERANCE_M:
            arrival = track.times[i]
        i -= 1
    return arrival


def stop_time(track: GtTrack, robot_id: str, t: float) -> float | None:
    """Return when `robot_id`'s current STATIONARY run began, or None.

    None when the robot is not STATIONARY at `t`, or its run was not
    preceded by MOVING motion within `STOP_PRECEDING_MOTION_SEC` (a robot
    that was never moving, or crept to a halt through the ambiguous band
    for longer, has no well-defined stop instant).
    """
    if motion_class(track.speed(robot_id, t)) != "stationary":
        return None
    i = bisect.bisect_right(track.times, t + 1e-9) - 1
    start = None
    while i >= 0:
        ti = track.times[i]
        if motion_class(track.speed(robot_id, ti)) != "stationary":
            break
        start = ti
        i -= 1
    if start is None or i < 0:
        return None
    lookback = [
        track.times[j]
        for j in range(i, -1, -1)
        if track.times[j] >= start - STOP_PRECEDING_MOTION_SEC
    ]
    if not any(motion_class(track.speed(robot_id, tj)) == "moving" for tj in lookback):
        return None
    return start


def temporal_order_answer(
    track: GtTrack, kind: str, a: str, b: str, t: float
) -> tuple[str | None, str, dict[str, float]]:
    """Return which of `a`, `b` reached `kind` ("goal" | "stop") first, judged at `t`.

    Returns:
        `(first_robot | None, reason, facts)`; drop reasons:
        `event_missing` (either robot has not had the event, or left its
        event state, by `t`), `outside_window` (`t` not within
        `TEMPORAL_WINDOW_SEC` after the later event), `gap_too_small`,
        `not_a_standoff` (stop kind, pair farther apart than
        `STANDOFF_MAX_DISTANCE_M` at `t`).
    """
    if kind == "goal":
        ea, eb = goal_arrival_time(track, a, t), goal_arrival_time(track, b, t)
    elif kind == "stop":
        ea, eb = stop_time(track, a, t), stop_time(track, b, t)
    else:
        raise ValueError(f"unknown temporal_order kind {kind!r}")
    if ea is None or eb is None:
        return None, "event_missing", {}
    facts = {"event_a_sec": ea, "event_b_sec": eb}
    later = max(ea, eb)
    since = t - later
    facts["since_later_event_sec"] = since
    if not TEMPORAL_WINDOW_SEC[0] <= since <= TEMPORAL_WINDOW_SEC[1]:
        return None, "outside_window", facts
    if abs(ea - eb) < TEMPORAL_MIN_GAP_SEC:
        return None, "gap_too_small", facts
    if kind == "stop":
        now = track.row_near(t)
        if now is None or pair_distance(now, a, b) > STANDOFF_MAX_DISTANCE_M:
            return None, "not_a_standoff", facts
    return (a if ea < eb else b), "ok", facts
