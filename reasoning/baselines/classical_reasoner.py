"""Arm B: the rev-8 classical congestion reasoner (geometry rules, no image).

Normative rules: "Arm B — classical reasoner specification" in
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
"""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from reasoning.vlm.models import (
    BlockerKind,
    CongestionDecision,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.motion_table import derive_motion_table

_STOPPED_STATUSES = frozenset({"STOPPED", "STALE"})

ClassicalScenario = Literal["none", "head_on", "intersection", "blocked_path", "unknown"]


class ConflictZone(BaseModel):
    """Mapped conflict zone from scenario config: a world-frame circle."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1)
    x: float
    y: float
    radius_m: float = Field(gt=0)


class ClassicalParams(BaseModel):
    """Arm B thresholds (rev-8); tunable on T1 only, frozen at `prereg-v1`."""

    # Forbid unknown keys: a typo in a pre-registered threshold must fail
    # loudly instead of silently running on the default.
    model_config = ConfigDict(frozen=True, extra="forbid")

    r_conflict_m: float = Field(default=1.5, gt=0)
    r_block_m: float = Field(default=1.0, gt=0)
    heading_opposition_min_deg: float = Field(default=150.0, gt=0, le=180)
    axis_cross_min_deg: float = Field(default=45.0, ge=0, le=180)
    axis_cross_max_deg: float = Field(default=135.0, ge=0, le=180)
    arrival_tie_sec: float = Field(default=1.0, gt=0)
    stopped_speed_mps: float = Field(default=0.05, gt=0)
    goal_beyond_max_deg: float = Field(default=60.0, gt=0, le=180)
    # A stopped robot this close to its own goal has arrived, not stalled, so
    # it is no blocked_path / unknown candidate. Aligned with M5's
    # arrival_position_tolerance_m (0.35 m, orchestrator.yaml), the radius
    # inside which M5 accepts an arrival; keep the two equal so Arm B never
    # calls a robot blocked that M5 has already counted as arrived. Rule
    # added 2026-09-27, pre-freeze, after T0 verification showed a 100%
    # parked-phase blocked_path rate by rule (VERIFY_SUMMARY F-T0-2).
    arrived_exclusion_radius_m: float = Field(default=0.35, gt=0)
    # Radius of the head_on FCFS zone around the pair midpoint, i.e. where
    # arrival stamps and commitment are measured; None keeps the rev-8
    # coupling to r_conflict_m. Decoupled pre-freeze (T1 basket, 2026-09-29)
    # because T1/T2a robots spawn 1.5 m from the standoff midpoint, exactly on
    # an r_conflict_m-sized zone boundary, so a robot could sit inside the
    # zone at the oldest buffered frame and get a censored arrival stamp.
    fcfs_zone_radius_m: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_axis_window(self) -> "ClassicalParams":
        if self.axis_cross_min_deg > self.axis_cross_max_deg:
            raise ValueError(
                f"axis_cross_min_deg {self.axis_cross_min_deg} exceeds "
                f"axis_cross_max_deg {self.axis_cross_max_deg}"
            )
        return self

    @model_validator(mode="after")
    def _check_fcfs_zone_radius(self) -> "ClassicalParams":
        # head_on pairs are at most r_conflict_m apart, so each member is at
        # most r_conflict_m / 2 from the midpoint; a smaller FCFS zone could
        # leave a classified robot never inside it, with no arrival stamp.
        if self.fcfs_zone_radius_m is not None and self.fcfs_zone_radius_m < self.r_conflict_m / 2:
            raise ValueError(
                f"fcfs_zone_radius_m {self.fcfs_zone_radius_m} is below "
                f"r_conflict_m / 2 ({self.r_conflict_m / 2})"
            )
        return self

    @property
    def head_on_fcfs_radius_m(self) -> float:
        """Radius of the head_on FCFS zone: `fcfs_zone_radius_m`, else `r_conflict_m`."""
        if self.fcfs_zone_radius_m is None:
            return self.r_conflict_m
        return self.fcfs_zone_radius_m


class ClassicalClassification(BaseModel):
    """Geometry-classifier verdict (RQ1 control).

    `conflict_center`/`conflict_radius_m` locate the zone the verdict was
    reached at, so FCFS arrival is measured where the conflict is: the pair
    midpoint with `ClassicalParams.head_on_fcfs_radius_m` for `head_on`, the
    matched mapped zone for `intersection`, and None for the scenarios that
    carry no ordering.
    """

    model_config = ConfigDict(frozen=True)

    scenario: ClassicalScenario
    congestion_type: Literal["none", "deadlock", "bottleneck", "anomaly"]
    blocker_kind: BlockerKind | None
    involved_robots: list[str]
    conflict_center: tuple[float, float] | None = None
    conflict_radius_m: float | None = Field(default=None, gt=0)
    zone_id: str | None = None


def classify_scene(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
) -> ClassicalClassification:
    """Classify the latest frame with the rev-8 Arm B geometry rules.

    Rules evaluate in order `head_on` -> `intersection` -> `blocked_path` ->
    `unknown`; the verdict is `none` when no robot is stopped, or when no
    rule matches and every stopped robot is parked at its goal or held. A robot is
    stopped when `|linear_velocity| < stopped_speed_mps`, or, with no
    velocity, when its status is STOPPED or STALE.

    - `head_on`: exactly two stopped robots within `r_conflict_m` of each
      other (no third stopped robot within `r_conflict_m` of either), heading
      opposition >= `heading_opposition_min_deg`, and each goal bearing
      within `goal_beyond_max_deg` of the bearing to the other robot. When
      either goal is unknown the goal check is skipped.
    - `intersection`: >= 2 stopped robots within `r_conflict_m` of a mapped
      zone's center, two of which have goal-bearing axes crossing at an
      angle in `[axis_cross_min_deg, axis_cross_max_deg]`.
    - `blocked_path`: stopped robots with no tracked robot within
      `r_block_m` in their forward half-plane. The classifier has no image
      channel, so `blocker_kind` is always `object` here: the forced
      non-divergence T3a measures.
    - Parked robots: a stopped robot within `arrived_exclusion_radius_m` of
      its own goal has arrived, so it is excluded from the `blocked_path`
      candidates and the `unknown` involved set (verdict `none` when no
      other stopped robot remains). It still counts for `head_on`,
      `intersection`, and as another robot's blocker: reaching its goal does
      not stop it obstructing someone else. A robot with no goal is never
      excluded.
    - Held robots: a robot in the latest frame's `held_robot_ids` (M5 still
      holds its base mission back, `start_pending`) has not been sent
      anywhere, so standing still is not a stall. It is excluded exactly like
      a parked robot: no `blocked_path` candidate, not in the `unknown`
      involved set, still counted for `head_on` (including its crowding
      check), `intersection`, and as another robot's blocker. Rule added
      2026-09-29, pre-freeze (amendments item 28), after the unified scene
      design found Arm B naming the held queue robot `blocked_path` in the
      bottleneck merge and in 10 of 45 convoy standoff cases.

    Args:
        frames: Snapshot history; only the latest frame (by stamp) is
            classified.
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.

    Returns:
        Classification with sorted involved robot ids.

    Raises:
        ValueError: If `frames` is empty.
    """
    if not frames:
        raise ValueError("classify_scene requires at least one frame")
    latest = max(frames, key=lambda frame: frame.stamp)
    stopped = sorted(
        (state for state in latest.robots if _is_stopped(state, params)),
        key=lambda state: state.robot_id,
    )
    if not stopped:
        return ClassicalClassification(
            scenario="none", congestion_type="none", blocker_kind=None, involved_robots=[]
        )

    pair = _head_on_pair(stopped, params)
    if pair is not None:
        a, b = pair
        return ClassicalClassification(
            scenario="head_on",
            congestion_type="deadlock",
            blocker_kind="robot",
            involved_robots=[a.robot_id, b.robot_id],
            conflict_center=((a.x + b.x) / 2.0, (a.y + b.y) / 2.0),
            conflict_radius_m=params.head_on_fcfs_radius_m,
        )

    for zone in zones:
        crossing = _intersection_robots(stopped, zone, params)
        if crossing:
            return ClassicalClassification(
                scenario="intersection",
                congestion_type="bottleneck",
                blocker_kind="robot",
                involved_robots=crossing,
                conflict_center=(zone.x, zone.y),
                conflict_radius_m=zone.radius_m,
                zone_id=zone.zone_id,
            )

    held = set(latest.held_robot_ids)
    candidates = [
        s for s in stopped if not _parked_at_goal(s, params) and s.robot_id not in held
    ]
    if not candidates:
        return ClassicalClassification(
            scenario="none", congestion_type="none", blocker_kind=None, involved_robots=[]
        )

    blocked = [s.robot_id for s in candidates if not _has_robot_ahead(s, latest.robots, params)]
    if blocked:
        return ClassicalClassification(
            scenario="blocked_path",
            congestion_type="anomaly",
            blocker_kind="object",
            involved_robots=blocked,
        )

    return ClassicalClassification(
        scenario="unknown",
        congestion_type="anomaly",
        blocker_kind=None,
        involved_robots=[s.robot_id for s in candidates],
    )


class ClassicalResolution(BaseModel):
    """Arm B's full answer: the shared decision plus the evidence behind it.

    Since the prompt-v2 bundle the decision itself carries the classifier's
    blocker verdict (`blocker_kind`, T3a) and, at 3+ robots, the FCFS passing
    order (`crossing_order`, RQ3), so an Arm-B-executed decision grounds the
    same fields an Arm A one does. The classification and the full passing
    order (two-robot orders included) stay here for shadow logging.
    """

    model_config = ConfigDict(frozen=True)

    decision: CongestionDecision
    classification: ClassicalClassification
    # First entry passes first; the last entry is the yielder. None when the
    # scenario carries no ordering (none, blocked_path, unknown).
    passing_order: list[str] | None = None


def resolve_classical(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
    prior_attempts: int = 0,
) -> ClassicalResolution:
    """Arm B: classify the scene and apply the rev-8 per-type policy table.

    Policy: `head_on` -> `yield` with the tiebreak loser as yielder;
    `intersection` -> `yield` with FCFS passing order and the last arrival as
    yielder; `blocked_path` -> `reroute` (blocker always `object`);
    `unknown` -> `temporary_wait` on the first attempt, `reroute` once
    `prior_attempts >= 1`.

    Passing order is FCFS by arrival stamp at the classification's conflict
    zone. Arrivals less than `arrival_tie_sec` after a cluster's first
    arrival tie with it; within a tie cluster, higher commitment (in-zone path
    length / zone diameter) passes first, then lower `robot_id`. Robots never
    seen inside the zone pass last, by `robot_id`.

    Args:
        frames: Snapshot history (ring-buffer contents), any order.
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.
        prior_attempts: Resolution attempts already made this episode.

    Returns:
        Frozen resolution; its `decision` has `congestion_detected=False` when
        nothing is stopped or only robots parked at their goals or held are.

    Raises:
        ValueError: If `frames` is empty or `prior_attempts` is negative.
    """
    if prior_attempts < 0:
        raise ValueError(f"prior_attempts must be >= 0, got {prior_attempts}")
    classification = classify_scene(frames, zones, params)
    involved = classification.involved_robots
    scenario = classification.scenario

    if scenario == "none":
        latest = max(frames, key=lambda frame: frame.stamp)
        stopped_ids = {s.robot_id for s in latest.robots if _is_stopped(s, params)}
        if not stopped_ids:
            root_cause = "classical: no stopped robots"
        elif stopped_ids & set(latest.held_robot_ids):
            root_cause = "classical: stopped robots are all parked at their goals or held back"
        else:
            root_cause = "classical: stopped robots are all parked at their goals"
        decision = CongestionDecision(
            congestion_detected=False,
            type="none",
            involved_robots=[],
            root_cause=root_cause,
            strategy="none",
            justification="classical geometry classifier found no congestion",
        )
        return ClassicalResolution(decision=decision, classification=classification)

    if scenario in ("head_on", "intersection"):
        order = _passing_order(frames, classification, params)
        yielder = order[-1]
        decision = CongestionDecision(
            congestion_detected=True,
            type=classification.congestion_type,
            involved_robots=involved,
            root_cause=f"classical: {scenario} between {', '.join(involved)}",
            strategy="yield",
            justification=(
                f"classical FCFS with commitment tiebreak: passing order "
                f"{', '.join(order)}; {yielder} arrived last or is least committed"
            ),
            yield_robot=yielder,
            blocker_kind=classification.blocker_kind,
            # Emitted where the prompt asks the VLM for one (3+ robots); a
            # two-robot order is fixed by the yielder alone.
            crossing_order=order if len(order) >= 3 else None,
        )
        return ClassicalResolution(
            decision=decision, classification=classification, passing_order=order
        )

    if scenario == "blocked_path":
        decision = CongestionDecision(
            congestion_detected=True,
            type=classification.congestion_type,
            involved_robots=involved,
            root_cause=f"classical: {', '.join(involved)} stopped with a clear front",
            strategy="reroute",
            justification="classical policy: blocked_path blocker is always object -> reroute",
            blocker_kind=classification.blocker_kind,
        )
        return ClassicalResolution(decision=decision, classification=classification)

    strategy = "temporary_wait" if prior_attempts == 0 else "reroute"
    decision = CongestionDecision(
        congestion_detected=True,
        type=classification.congestion_type,
        involved_robots=involved,
        root_cause=f"classical: unclassified stall of {', '.join(involved)}",
        strategy=strategy,
        justification=(
            "classical policy: unknown scenario waits once, then reroutes "
            f"(prior_attempts={prior_attempts})"
        ),
        blocker_kind=classification.blocker_kind,
    )
    return ClassicalResolution(decision=decision, classification=classification)


def decide_classical(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
    prior_attempts: int = 0,
) -> CongestionDecision:
    """Arm B decision on the same inputs as Arm A, in the VLM's contract.

    Emits the same `CongestionDecision` type the VLM emits, so grounding,
    validation, and M4 execution are shared across arms, `blocker_kind` and
    (at 3+ robots) `crossing_order` included. Use `resolve_classical` when the
    classification or a two-robot passing order is needed.

    Args:
        frames: Snapshot history (ring-buffer contents), any order.
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.
        prior_attempts: Resolution attempts already made this episode.

    Returns:
        Frozen decision; `congestion_detected=False` when nothing is stopped
        or only robots parked at their goals are.

    Raises:
        ValueError: If `frames` is empty or `prior_attempts` is negative.
    """
    return resolve_classical(frames, zones, params, prior_attempts).decision


def load_classical_params(path: Path = Path("config/rag.yaml")) -> ClassicalParams:
    """Load the `classical:` section of the RAG config.

    Args:
        path: YAML config path.

    Returns:
        Validated params; an absent or empty section yields the rev-8 defaults.

    Raises:
        FileNotFoundError: If `path` does not exist.
        pydantic.ValidationError: If the section has unknown keys or
            out-of-range values.
    """
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return ClassicalParams(**(raw.get("classical") or {}))


def _is_stopped(state: RobotStateInput, params: ClassicalParams) -> bool:
    if state.linear_velocity is not None:
        return abs(state.linear_velocity) < params.stopped_speed_mps
    return (state.status or "").upper() in _STOPPED_STATUSES


def _parked_at_goal(state: RobotStateInput, params: ClassicalParams) -> bool:
    if state.goal is None:
        return False
    return (
        math.hypot(state.x - state.goal[0], state.y - state.goal[1])
        <= params.arrived_exclusion_radius_m
    )


def _distance(a: RobotStateInput, b: RobotStateInput) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _angle_between_deg(a: float, b: float) -> float:
    diff = abs(a - b) % (2 * math.pi)
    if diff > math.pi:
        diff = 2 * math.pi - diff
    return math.degrees(diff)


def _head_on_pair(
    stopped: list[RobotStateInput], params: ClassicalParams
) -> tuple[RobotStateInput, RobotStateInput] | None:
    for i, a in enumerate(stopped):
        for b in stopped[i + 1 :]:
            if _distance(a, b) > params.r_conflict_m:
                continue
            crowded = any(
                other.robot_id not in (a.robot_id, b.robot_id)
                and min(_distance(other, a), _distance(other, b)) <= params.r_conflict_m
                for other in stopped
            )
            if crowded:
                continue
            if _angle_between_deg(a.theta, b.theta) < params.heading_opposition_min_deg:
                continue
            if a.goal is not None and b.goal is not None:
                if not (_goal_beyond(a, a.goal, b, params) and _goal_beyond(b, b.goal, a, params)):
                    continue
            return a, b
    return None


def _goal_beyond(
    robot: RobotStateInput,
    goal: tuple[float, float],
    other: RobotStateInput,
    params: ClassicalParams,
) -> bool:
    goal_bearing = math.atan2(goal[1] - robot.y, goal[0] - robot.x)
    other_bearing = math.atan2(other.y - robot.y, other.x - robot.x)
    return _angle_between_deg(goal_bearing, other_bearing) <= params.goal_beyond_max_deg


def _intersection_robots(
    stopped: list[RobotStateInput], zone: ConflictZone, params: ClassicalParams
) -> list[str]:
    in_zone = [s for s in stopped if math.hypot(s.x - zone.x, s.y - zone.y) <= params.r_conflict_m]
    axes = [math.atan2(s.goal[1] - s.y, s.goal[0] - s.x) for s in in_zone if s.goal is not None]
    for i, axis_a in enumerate(axes):
        for axis_b in axes[i + 1 :]:
            angle = _angle_between_deg(axis_a, axis_b)
            if params.axis_cross_min_deg <= angle <= params.axis_cross_max_deg:
                return [s.robot_id for s in in_zone]
    return []


def _has_robot_ahead(
    robot: RobotStateInput, all_robots: list[RobotStateInput], params: ClassicalParams
) -> bool:
    heading = (math.cos(robot.theta), math.sin(robot.theta))
    for other in all_robots:
        if other.robot_id == robot.robot_id:
            continue
        dx, dy = other.x - robot.x, other.y - robot.y
        if math.hypot(dx, dy) <= params.r_block_m and dx * heading[0] + dy * heading[1] > 0:
            return True
    return False


def _passing_order(
    frames: Sequence[SnapshotFrame],
    classification: ClassicalClassification,
    params: ClassicalParams,
) -> list[str]:
    center = classification.conflict_center
    radius = classification.conflict_radius_m
    if center is None or radius is None:
        raise ValueError(f"{classification.scenario} classification carries no conflict zone")
    involved = classification.involved_robots
    table = derive_motion_table(frames, center, radius)
    arrival = {e.robot_id: e.arrival_stamp for e in table.entries if e.robot_id in involved}
    commitment = {rid: _commitment(frames, rid, center, radius) for rid in involved}

    arrived = sorted(
        (rid for rid in involved if arrival.get(rid) is not None),
        key=lambda rid: (arrival[rid], rid),
    )
    order: list[str] = []
    i = 0
    while i < len(arrived):
        anchor = arrival[arrived[i]]
        j = i + 1
        while j < len(arrived) and arrival[arrived[j]] - anchor < params.arrival_tie_sec:
            j += 1
        order.extend(sorted(arrived[i:j], key=lambda rid: (-commitment[rid], rid)))
        i = j
    order.extend(sorted(rid for rid in involved if arrival.get(rid) is None))
    return order


def _commitment(
    frames: Sequence[SnapshotFrame],
    robot_id: str,
    center: tuple[float, float],
    radius: float,
) -> float:
    # Path length summed over consecutive buffered frames that both have the
    # robot inside the zone: the ring buffer's estimate of distance travelled
    # past zone entry, normalized by zone length (diameter).
    path = 0.0
    previous: RobotStateInput | None = None
    for frame in sorted(frames, key=lambda f: f.stamp):
        state = frame.find_robot(robot_id)
        if state is None:
            continue
        if math.hypot(state.x - center[0], state.y - center[1]) > radius:
            previous = None
            continue
        if previous is not None:
            path += math.hypot(state.x - previous.x, state.y - previous.y)
        previous = state
    return path / (2.0 * radius)
