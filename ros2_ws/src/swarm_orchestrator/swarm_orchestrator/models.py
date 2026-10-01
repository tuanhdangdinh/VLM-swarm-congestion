"""Pydantic contracts and parsing helpers for the M5 orchestrator (no rclpy)."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from reasoning.baselines import ConflictZone
from reasoning.rag.command_grounder import PlanEdit, PlanProvenance, YieldFeasibilityMode
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    ReasonerResult,
    StaticObstacleInput,
)
from swarm_orchestrator.plan_tracker import TrackedLeg
from swarm_orchestrator.presentation_order import RobotPresentationOrderMode

# Default ROS2 topic/service names (spec §5; overridable via config `topics`).
DEFAULT_TOPICS: dict[str, str] = {
    "scene_state": "/perception/scene_state",
    "annotated_frame": "/perception/annotated_frame",
    "coordination_status": "/coordination/status",
    "coordination_commands": "/coordination/commands",
    "coordination_tasks": "/coordination/tasks",
    "trigger_analysis": "/orchestrator/trigger_analysis",
}


class TerminalStage(str, Enum):
    """Where a reasoning pipeline run terminated, for diagnostics."""

    VLM = "vlm"
    GROUNDING = "grounding"
    OK = "ok"
    # A T0 log-only probe whose stage-1 analysis completed; grounding and
    # dispatch never run for it, so it can never be dispatched.
    PROBE = "probe"


class TaskAssignment(BaseModel):
    """A robot's base mission assignment: task label plus world-frame goal."""

    model_config = ConfigDict(frozen=True)

    task: str = Field(min_length=1)
    goal: tuple[float, float]
    # Hold-back (T2b's queued robot_3): M4 is given this robot's base goal to
    # drive only once this many seconds have passed since M5 started, on the
    # same wall clock as M5's stall and cooldown timers. Until then the robot is
    # published with `start_pending: true` (still in M1's allowlist, so tracked)
    # and gives no progress-stall evidence. 0 = released at startup.
    start_delay_sec: float = Field(default=0.0, ge=0.0)
    # Dispatch priority (B2 priority_urgent pair): higher passes first. Read
    # by M3 only, to resolve a `priority_override` decision's beneficiary; it
    # is never rendered into any prompt (rendering it would be a prompt
    # version change) and never published to M1/M4. 0 = routine, and every
    # scene without a priority is byte-identical to before the field existed.
    priority: int = 0


def registry_priorities(tasks: dict[str, TaskAssignment]) -> dict[str, int]:
    """Return the non-zero base priorities M3 grounds `priority_override` with.

    Args:
        tasks: The configured `initial_tasks`.

    Returns:
        Robot id -> priority for every robot with a non-zero one; empty when no
        scene priority is declared, which M5 treats as "pass nothing to M3".
    """
    return {rid: task.priority for rid, task in sorted(tasks.items()) if task.priority != 0}


class OrchestratorConfig(BaseModel):
    """Runtime configuration for the orchestrator, loaded from YAML at startup."""

    model_config = ConfigDict(frozen=True)

    stall_threshold_sec: float = Field(ge=0.0)
    progress_epsilon_m: float = Field(ge=0.0)
    # Nav2's xy_goal_tolerance is 0.1 m; an arrived robot sits inside that band
    # forever and must not be read as stalled by the progress-stall check.
    goal_reached_tolerance_m: float = Field(default=0.15, ge=0.0)
    # Once M4 reports a robot's base goal reached (Nav2 success), M1 may still
    # place it outside goal_reached_tolerance_m (camera bias near the ROI edge);
    # the arrived mark excuses it from stall evidence while it stays within this
    # radius of that goal, and lapses once it is driven farther away.
    arrived_radius_m: float = Field(default=0.5, ge=0.0)
    # Nav2's "Goal succeeded" is not evidence the robot is at its goal: in run
    # 20260925_124609 bt_navigator succeeded for robot_2 while M1 put it 0.59 m
    # away, which would have scored as an episode success. Cross-check the
    # report against M1's position before marking the robot arrived (FR5.1.9).
    arrival_position_check: bool = True
    # Must exceed M1's ~0.1 m camera bias at the goal and stay at or below
    # arrived_radius_m (enforced below), or an accepted arrival would sit
    # outside the radius that excuses it from stall evidence. Setting it below
    # goal_reached_tolerance_m is legal but creates a limbo band where a robot
    # is neither accepted nor stall-eligible; prefer a value above it.
    arrival_position_tolerance_m: float = Field(default=0.35, gt=0.0)
    # Oldest M1 estimate still allowed to corroborate an arrival; beyond it the
    # arrival is accepted unverified rather than blocked on an M1 outage.
    arrival_estimate_max_age_sec: float = Field(default=2.0, gt=0.0)
    proximity_threshold_m: float = Field(default=0.5, ge=0.0)
    proximity_slow_speed_mps: float = Field(default=0.05, ge=0.0)
    cooldown_sec: float = Field(ge=0.0)
    command_timeout_sec: float = Field(ge=0.0)
    reasoning_backend_id: str = Field(min_length=1)
    initial_tasks: dict[str, TaskAssignment]
    topics: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_TOPICS))
    frame_dump_dir: str = Field(min_length=1)
    decision_log_dir: str = Field(default="data/logs/m5_decisions", min_length=1)
    # One JSONL scene snapshot per period per M5 session, independent of triggers,
    # for offline trajectory reconstruction; None disables.
    scene_log_dir: str | None = Field(default="data/logs/m5_scene")
    scene_log_period_sec: float = Field(default=1.0, gt=0.0)
    keep_debug_frames: bool = False
    # Also dump M1's *input* frame as `<request_id>_raw.png` beside the
    # annotated one, so an annotated-vs-raw comparison has both frames of the
    # same instant. Debug evidence only: the M2 request still carries the
    # annotated frame. Requires keep_debug_frames, which owns frame retention.
    keep_raw_frames: bool = False
    # The camera topic M1 itself subscribes to (perception.launch.py
    # `image_topic`); read only when keep_raw_frames is on. Not part of
    # `topics`, which is M5's own topic contract (spec §5).
    raw_frame_topic: str = Field(default="/camera/image_raw", min_length=1)
    frame_scene_max_skew_sec: float = Field(default=1.0, ge=0.0)
    frame_downscale_width: int | None = Field(default=None, gt=0)
    # Seconds after a command resolves during which its attempt is attached to a
    # re-analysis for overlapping robots as `failure_context` (rev-8 A.1). 0 disables
    # (RQ5 memoryless control). Must exceed cooldown + stall threshold or it can
    # never fire — enforced below.
    failure_context_window_sec: float = Field(default=60.0, ge=0.0)
    # Ablation axis (rev-8 modality table): withhold the derived pairwise
    # distance/facing lines from the VLM prompt when False.
    prompt_pairwise_geometry: bool = True
    # Ablation axis: include the declared static obstacles in the VLM prompt.
    # Default False — every decision artifact collected so far was produced
    # without this channel, so an ON default would break comparability.
    prompt_static_obstacles: bool = False
    # Ablation axis: the order the VLM prompt lists robots in. Default "id_asc"
    # matches every prompt rendered so far; "id_desc" is the counterbalanced
    # condition that separates a positional default from an ID or geometry one;
    # "random" draws one of the two per congestion episode.
    prompt_robot_order: RobotPresentationOrderMode = "id_asc"
    # Seed for the "random" draw; None derives it from VGU_RUN_ID, falling back
    # to the M5 session id, so paired runs sharing a run id see the same
    # sequence. Fixed modes ignore it. Stage-2 letter draws always derive from
    # it (a separate salted stream; `retreat_stage2.derive_letter_seed`).
    prompt_robot_order_seed: int | None = None
    # Fixed obstacles of the running scenario, mirrored from its scenario file;
    # rendered only when prompt_static_obstacles is true.
    static_obstacles: tuple[StaticObstacleInput, ...] = ()
    # Handed to M3 so the yield maneuver is derived from declared scene
    # dimensions; None keeps M3's hand-sized head_on_deadlock fallbacks.
    scenario_geometry: SceneGeometry | None = None
    # Whether M3 may move a yield off the robot M2 named when that robot is
    # boxed in. Needs both static_obstacles and scenario_geometry to do
    # anything; "off" keeps every grounded command byte-identical to the ones
    # collected before the gate existed.
    grounding_yield_feasibility: YieldFeasibilityMode = "off"
    # M3 grounding parameters file (its `grounding:` section, which holds the
    # legacy/derived mode switch), relative to M5's cwd like config/models.yaml.
    # Loaded once at startup; a missing file or an invalid section stops M5.
    grounding_params_path: str = Field(default="config/rag.yaml", min_length=1)
    # Per-scenario world-frame y band every retreat candidate's swept path must
    # stay inside, replacing the grounding file's `aisle_y_band_m`. Scenario
    # geometry like scenario_geometry, so it lives here and is set per
    # scenario; None keeps the file's value and every scenario's k unchanged.
    grounding_aisle_y_band_m: tuple[float, float] | None = None
    # Per-scenario world-frame x band for a yielder whose declared junction
    # arm runs along y (B1 bottleneck_merge's north-arm yielder): the N-S
    # aisle's walls. None (every scene before B1) changes nothing.
    grounding_aisle_x_band_m: tuple[float, float] | None = None
    # Stage-2 retreat selection (rev-8 A.3): in derived grounding mode, ask the
    # VLM to pick one of the validated retreat candidates of a yield. False
    # skips the call, and every yield grounds the geometry-max default
    # (tagged `retreat=default:no_choice`), so collection can run stage-2-less.
    stage2_retreat_selection: bool = True
    # M1's calibration file, used to draw the stage-2 candidate letters on the
    # frame (set-of-mark). None resolves the file M1 itself launches with
    # (swarm_perception's installed config/calibration.yaml). Loaded once at
    # startup; a missing or invalid file sends stage 2 the unmarked frame and
    # records why, it never stops M5.
    stage2_calibration_path: str | None = None
    # Stage-2 call budget, replacing stage 1's for the retreat-choice call
    # only. The worst case (attempts x timeout = 16 s) stays inside one
    # command_timeout_sec window (20 s) while the deadlocked robots wait on
    # it; 8 s is above every stage-1 call measured so far (gpt-4o 2.1-6.0 s,
    # ER-2 3.2-3.8 s) for a shorter prompt and a one-letter answer.
    stage2_max_attempts: int = Field(default=2, ge=1)
    stage2_timeout_sec: float = Field(default=8.0, gt=0.0)
    # Arm B shadow (rev-8 shadow logging): compute and log the classical answer
    # beside every VLM analysis. Observational only — it never dispatches or
    # alters the VLM decision — so it defaults on.
    shadow_classical: bool = True
    # Arm B thresholds file (its `classical:` section), relative to M5's cwd
    # like config/models.yaml.
    shadow_classical_params_path: str = Field(default="config/rag.yaml", min_length=1)
    # Snapshot history kept for FCFS arrival stamps, in M1 stamp seconds. The
    # first analysis needs zone entry -> stop (~10 s wall at M1's current
    # ~0.1 m/s reported speeds over ~1 m) plus stall_threshold_sec (12 s);
    # 60 s covers that ~2.5x and usually the first re-analysis too (>= 27 s
    # later). Older arrivals are censored to the oldest frame, which each
    # shadow record states. Must exceed stall_threshold_sec (enforced below).
    shadow_classical_window_sec: float = Field(default=60.0, gt=0.0)
    # Minimum stamp gap between buffered snapshots. 0.25 s quantizes arrival
    # stamps to a quarter of Arm B's 1.0 s arrival_tie_sec and damps M1 jitter
    # in the commitment path length; 60 s holds at most 240 frames. Must be
    # below arrival_tie_sec (checked against the loaded params at startup).
    shadow_classical_sample_period_sec: float = Field(default=0.25, gt=0.0)
    # Mapped conflict zones for the intersection rule (later tiers). Empty is
    # valid: the head-on rule derives its own pair zone.
    shadow_classical_zones: tuple[ConflictZone, ...] = ()
    # T0 negative control (design spec "Scenario battery"): every
    # t0_probe_interval_sec, run the stage-1 VLM analysis off-trigger on the
    # latest scene in log-only mode — recorded like a triggered analysis,
    # never grounded or dispatched. Off by default; only T0 normal-flow runs
    # turn it on. t0_probe_max_probes caps the probes per M5 process; 0 means
    # unlimited.
    t0_probe_mode: bool = False
    t0_probe_interval_sec: float = Field(default=20.0, gt=0.0)
    t0_probe_max_probes: int = Field(default=0, ge=0)
    # A probe is deferred once the latest SceneState was received more than
    # this many wall seconds ago. M1 publishes one scene per camera frame, so
    # a live feed stays well under it; after the simulator exits the scene
    # and frame stamps freeze together and pass the skew check, and only the
    # receipt age shows the feed is dead.
    t0_probe_max_snapshot_age_sec: float = Field(default=3.0, gt=0.0)
    # (a0) universal proposed_plan channel (prereg-v2 rev 4, build-order step
    # 4): off, `verify_and_repair_plan`/`PlanTracker` never run and the
    # dispatch path (grounded command, prompt version, decision artifact) is
    # byte-identical to before this channel existed. On, every triggered
    # analysis is also verified/repaired/tracked: the grounded command's
    # dispatched actions carry the accepted `plan_id`, M5 renders prompt v3
    # (the plan-state block plus the `proposed_plan` invitation) instead of
    # the current default, and the decision artifact gains a `plan` block.
    # Default False: this is the regression gate (prereg-v2 design.md build
    # order step 4's two-robot head-on equivalence smoke runs with it off).
    plan_channel_enabled: bool = False

    @field_validator("initial_tasks")
    @classmethod
    def _non_empty_robot_ids(cls, v: dict[str, TaskAssignment]) -> dict[str, TaskAssignment]:
        if any(not rid for rid in v):
            raise ValueError("initial_tasks robot ids must be non-empty strings")
        return v

    @model_validator(mode="after")
    def _failure_context_window_can_fire(self) -> OrchestratorConfig:
        window = self.failure_context_window_sec
        bound = self.cooldown_sec + self.stall_threshold_sec
        if 0.0 < window <= bound:
            raise ValueError(
                f"failure_context_window_sec={window} can never fire: a re-detection "
                f"takes at least cooldown_sec + stall_threshold_sec = {bound} s; set it "
                "above that bound, or 0 to disable"
            )
        return self

    @model_validator(mode="after")
    def _shadow_window_covers_stall(self) -> OrchestratorConfig:
        # The stall timer runs on M5's monotonic clock and the window on M1
        # stamps. Wall-clock stamps compare directly; sim-time stamps advance
        # slower than wall time below real-time, so the check stays conservative.
        if self.shadow_classical and self.shadow_classical_window_sec <= self.stall_threshold_sec:
            raise ValueError(
                f"shadow_classical_window_sec={self.shadow_classical_window_sec} must exceed "
                f"stall_threshold_sec={self.stall_threshold_sec}: every zone entry would "
                "fall out of the buffer before the analysis that needs it"
            )
        return self

    @model_validator(mode="after")
    def _arrival_tolerance_within_arrived_radius(self) -> OrchestratorConfig:
        if self.arrival_position_tolerance_m > self.arrived_radius_m:
            raise ValueError(
                f"arrival_position_tolerance_m={self.arrival_position_tolerance_m} exceeds "
                f"arrived_radius_m={self.arrived_radius_m}: an arrival accepted beyond that "
                "radius is not excused from stall evidence and would be re-flagged at once"
            )
        return self


class RobotView(BaseModel):
    """M5's internal projection of one M1 RobotState (decoupled from swarm_perception)."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    x: float
    y: float
    theta: float
    linear_velocity: float
    status: str
    stamp: float = Field(ge=0.0)
    # From M5's task registry, not from M1 (`attach_registry_assignments`), so
    # the prompt sees the goals Arm B's shadow reads. None until attached, and
    # absent from every scene stored before the prompt-v2 bundle.
    goal: tuple[float, float] | None = None
    task: str | None = None


class SceneSnapshot(BaseModel):
    """M5's internal projection of one M1 SceneState JSON message."""

    model_config = ConfigDict(frozen=True)

    stamp: float = Field(ge=0.0)
    frame_id: str = Field(min_length=1)
    robots: list[RobotView]
    dropped_frame: bool = False


class CongestionEvent(BaseModel):
    """A detected sustained-stall event handed to the state machine."""

    model_config = ConfigDict(frozen=True)

    involved_robots: list[str] = Field(min_length=1)
    stall_durations_sec: dict[str, float]
    detected_at: float
    reason: str
    # M1's distance-to-goal per progress-stalled robot, for diagnosing spurious
    # triggers on parked robots; close/slow-only robots may be absent.
    distance_to_goal_m: dict[str, float] = Field(default_factory=dict)

    @field_validator("involved_robots")
    @classmethod
    def _sorted_unique(cls, v: list[str]) -> list[str]:
        return sorted(set(v))


class RetreatStage2Record(BaseModel):
    """What stage 2 did for one derived-mode yield, for the decision artifact.

    `status` is `answered` when a rendered letter came back, `degraded` when
    a call ran (or raised) without one, and `skipped` when no call was made;
    `skip_reason` then says why (`disabled`, `yield_refused`,
    `no_candidates`, `single_candidate`, `no_backend`). Every non-answer
    grounds the geometry-max candidate, tagged by the grounder.
    """

    model_config = ConfigDict(frozen=True)

    status: Literal["answered", "degraded", "skipped"]
    skip_reason: str | None = None
    stage2_prompt_version: int | None = None
    yielder_id: str | None = None
    crossing_order: list[str] = Field(default_factory=list)
    # Ranked best-first, as `prepare_retreat_selection` returned them, with
    # their sweep clearances; `default_label` is the first one's M3 label
    # (generation order). When a call is made each also carries `letter`, the
    # letter the VLM was shown for it.
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    default_label: str | None = None
    # Letter counterbalancing (amendments item 22), set only when a call is
    # made: the letter the default (rank 0) was shown under, and the draw
    # that placed it. `letter_seed` is `derive_letter_seed(letter_seed_base,
    # letter_draw_index)`, and `assign_letters(len(candidates), letter_seed)`
    # reproduces `letter_assignment` (shown letter -> candidate_label, rank,
    # x, y).
    default_letter: str | None = None
    letter_seed_base: int | None = None
    letter_draw_index: int | None = None
    letter_seed: int | None = None
    letter_assignment: dict[str, dict[str, Any]] | None = None
    # Listing randomization (amendments item 26, stage-2 prompt v3), set only
    # when a call is made: the shown letters in the order the prompt listed
    # them, and the draw's seed, `derive_listing_seed(letter_seed_base,
    # letter_draw_index)`; `draw_listing_order(letters, listing_seed)`
    # reproduces it. None on v2 records, which listed in letter order.
    # Three distinct "positional" readings of an answer, never to be merged:
    # chose the first-listed is `choice == listing_order[0]`; chose the
    # default is `choice == default_letter`; chose letter A is
    # `choice == "A"`. Under v2 the first and third coincide.
    listing_order: list[str] | None = None
    listing_seed: int | None = None
    # The rendered stage-2 prompt with SHA-256 hashes and the image path the
    # call referenced (never the image bytes); None when no call was made.
    prompt: dict[str, Any] | None = None
    # Whether the call's image carried the candidate letters (set-of-mark);
    # None when no call was made. `marks` is the `Stage2Marks` block: the
    # marked image path, each letter's pixel position, and on False why.
    marks_drawn: bool | None = None
    marks: dict[str, Any] | None = None
    # `RetreatChoiceResult` dumped to JSON; None when no call was made.
    response: dict[str, Any] | None = None
    # The answer as the VLM gave it, in shown letters (an unrendered letter
    # included, which the grounder tags `retreat=default:invalid_label`).
    choice: dict[str, Any] | None = None
    # The M3 label that answer was mapped to and handed to the grounder; the
    # grounded command's `retreat_choice` carries this label, not the shown
    # letter. An unrendered letter passes through unmapped.
    grounded_label: str | None = None
    failure_cause: str | None = None
    # An unexpected exception inside stage 2, recorded instead of raised.
    error: str | None = None


class PlanDispatchInfo(BaseModel):
    """The (a0) plan channel's outcome for one dispatched decision, behind `plan_channel_enabled`.

    Present on `PipelineOutcome.plan` only when plan tracking is on; None
    (the default) keeps every flag-off outcome, and the decision artifact
    built from it, byte-identical to before this field existed.
    """

    model_config = ConfigDict(frozen=True)

    plan_id: int = Field(ge=1)
    provenance: PlanProvenance
    # Every leg of the accepted plan (robot_id, action, status) at acceptance
    # time -- all "pending" for a genuine accept; on a hold (`plan_held`
    # True) this is the ALREADY-active plan's current legs, whatever their
    # live status is, since a hold never resets them. Later status
    # transitions live in the `PlanTracker` instance and are not
    # re-persisted per transition (that would mean a new artifact write per
    # status change). "Per-leg status tracked by M5 and persisted into
    # decision artifacts" (prereg-v2 rev 4).
    legs: tuple[TrackedLeg, ...]
    edits: tuple[PlanEdit, ...] = ()
    rejection_reason: str | None = None
    # None when no plan was previously active (the episode's first plan);
    # set whenever this plan explicitly superseded one.
    superseded_plan_id: int | None = Field(default=None, ge=1)
    # Robots whose superseded leg must be retired, in dependency order
    # (`plan_tracker._cancel_order`); empty when nothing superseded, or when
    # the new plan carries every old non-terminal leg forward unchanged.
    cancel_order: tuple[str, ...] = ()
    # Whether this plan's legs are the SAME per-robot actions the command
    # actually dispatched (`command_grounder.plan_matches_dispatch`). True for
    # every two-robot head-on (verified exhaustively); a plan-present 3+-robot
    # scene with a pure-reorder repair (ruling 1), or a derived-mode yield
    # the backup-band sweep would reroute but `_plan_problems` does not model,
    # can legitimately be False -- the engine measures what the VLM proposed,
    # it does not drive what M4 receives. Exists so that divergence is
    # measured, not silently assumed away.
    dispatch_matches_plan: bool
    # Hold semantics (ruling 2026-10-02): True when `plan_tracker.PlanTracker
    # .accept_plan` re-affirmed the already-active plan (`plan_id` above is
    # that unchanged active plan_id, not a new one) rather than accepting a
    # new one. False for every genuine accept, including the episode's first.
    plan_held: bool = False


class PipelineOutcome(BaseModel):
    """Result of one M2->M3 reasoning pipeline run."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    reasoner_result: ReasonerResult
    grounded_command: dict[str, Any] | None
    terminal_stage: TerminalStage
    failure_reason: str | None = None
    # Set only for a yield grounded in derived mode (the stage-2 applicable
    # case); None everywhere else.
    stage2: RetreatStage2Record | None = None
    # (a0) plan channel outcome; None unless `plan_channel_enabled` (the
    # default), so a flag-off run's outcome is unchanged from before this
    # field existed.
    plan: PlanDispatchInfo | None = None
    # Set when `plan_channel_enabled` but `verify_and_repair_plan`/
    # `PlanTracker.accept_plan` itself raised: `plan` is then None (no plan_id
    # was assigned, so the grounded command is dispatched untouched) but the
    # command still reaches OK -- a plan-channel failure must never cost an
    # otherwise-successful dispatch (FR5.3.2's "never raised past this
    # adapter", extended to this channel). None in every other case.
    plan_error: str | None = None


def parse_scene_snapshot(raw: str) -> SceneSnapshot:
    """Parse an M1 SceneState JSON string into M5's internal SceneSnapshot.

    Args:
        raw: JSON string published on `/perception/scene_state`.

    Returns:
        The projected snapshot. `dropped_frame` is read from `diagnostics`.

    Raises:
        ValueError: If the payload is not valid JSON or fails schema projection.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed SceneState JSON: {exc}") from exc
    diagnostics = data.get("diagnostics", {}) or {}
    robots = [
        RobotView(
            robot_id=r["robot_id"],
            x=r["x"],
            y=r["y"],
            theta=r["theta"],
            linear_velocity=r["linear_velocity"],
            status=r["status"],
            stamp=r["stamp"],
        )
        for r in data.get("robots", [])
    ]
    return SceneSnapshot(
        stamp=data["stamp"],
        frame_id=data["frame_id"],
        robots=robots,
        dropped_frame=bool(diagnostics.get("dropped_frame", False)),
    )


def load_config(raw: dict[str, Any]) -> OrchestratorConfig:
    """Build an OrchestratorConfig from a plain dict (e.g. parsed YAML).

    Args:
        raw: Mapping of config keys; `initial_tasks` values may use list goals.
            A `scenario_geometry` mapping is passed through untouched for
            Pydantic to validate into a `SceneGeometry`.

    Returns:
        A validated, frozen config.

    Raises:
        pydantic.ValidationError: If required fields are missing or invalid.
    """
    tasks_in = raw.get("initial_tasks", {})
    initial_tasks = {
        rid: TaskAssignment(
            task=spec["task"],
            goal=tuple(spec["goal"]),
            start_delay_sec=spec.get("start_delay_sec", 0.0),
            priority=spec.get("priority", 0),
        )
        for rid, spec in tasks_in.items()
    }
    # Merge configured topic overrides over defaults so partial overrides keep the rest.
    topics = {**DEFAULT_TOPICS, **raw.get("topics", {})}
    merged = {**raw, "initial_tasks": initial_tasks, "topics": topics}
    return OrchestratorConfig(**merged)
