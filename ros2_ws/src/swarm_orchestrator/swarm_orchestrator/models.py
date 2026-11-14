"""Pydantic contracts and parsing helpers for the M5 orchestrator (no rclpy)."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
    model_validator,
)

from reasoning.baselines import ConflictZone
from reasoning.rag.command_grounder import (
    DispatchOrderSource,
    DispatchOrderSourceMode,
    DroppedCandidate,
    JunctionClearPhasePlan,
    PlanEdit,
    PlanProvenance,
    YieldFeasibilityMode,
)
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    ReasonerResult,
    StaticObstacleInput,
)
from swarm_orchestrator.permutation_votes import PermutationVoteRecord
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


class ContradictionTriggerConfig(BaseModel):
    """The prereg-v3 R3.4 contradiction trigger's settings (`contradiction_trigger:`).

    Disabled (the default), M5 arms nothing, fires nothing and writes no
    trigger-source key, so every run is byte-identical to before the block
    existed. Enabled, a dispatched command whose leg reports FAILED, or whose
    robot measurably departs from what its leg implies
    (`swarm_orchestrator.contradiction_trigger`), re-triggers analysis as soon
    as that command resolves, skipping the remaining cooldown, at most
    `per_event_replan_budget` times per congestion episode.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    # Must clear M1's frame-to-frame jitter on a parked robot with margin:
    # every predicate is measured relative to the robot's own first ACTIVE
    # position, so M1's constant ~0.1-0.3 m edge bias cancels, but a
    # marker-loss jump does not.
    divergence_bound_m: float = Field(default=0.5, gt=0.0)
    per_event_replan_budget: int = Field(default=1, ge=0)


class ReanalysisSuppressionConfig(BaseModel):
    """Scene-unchanged re-trigger suppression (`reanalysis_suppression:`, A12(iii)).

    Disabled (the default), every stall trigger the state machine admits
    starts an analysis exactly as before, and no log line or artifact key is
    added. Enabled, a stall-triggered analysis is skipped while its robot set
    and those robots' M1 positions match the last executed stall analysis
    that dispatched nothing (`swarm_orchestrator.reanalysis_suppression`
    holds the full predicate, the shipped default to be frozen at Step 6).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    # Must clear M1's position jitter on a stopped robot (pilot episode 1:
    # median 6 mm, p95 8 mm) with margin, and stay below any displacement
    # that changes what the model is shown (a backup is >= 0.2 m).
    pose_epsilon_m: float = Field(default=0.05, gt=0.0)
    # "task_stream_only" engages it only while `task_stream.enabled` (the S1
    # cells it was registered for); "all" in every scene.
    applies_to: Literal["task_stream_only", "all"] = "task_stream_only"


class ChurnBoundConfig(BaseModel):
    """Per-cluster clearing-dispatch bound (`churn_bound:`, prereg-v3 A21(b)).

    Built DEFAULT-OFF with its values deliberately unset: A21 rules "measure
    first, bound later", so `budget_k`, `window_sim_sec` and
    `alternation_max` are frozen only from churn data (target: p95 of
    productive-resolution counts) and enabled per registered cell. Disabled
    (the default), M5 constructs no ledger and every dispatch, log line and
    artifact is byte-identical to before this block existed. Enabled, a
    clearing dispatch (`swarm_orchestrator.churn.dispatch_identity`) is
    withheld like a refusal (`dispatch_withheld` reason `churn_budget` or
    `churn_alternation`) when its latch cluster already used `budget_k`
    clearing dispatches inside `window_sim_sec`, or when it would push the
    cluster's A-B-A alternations in the window past `alternation_max`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    budget_k: int | None = Field(default=None, ge=1)
    window_sim_sec: float | None = Field(default=None, gt=0.0)
    alternation_max: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _enabled_needs_values(self) -> ChurnBoundConfig:
        missing = [
            name
            for name in ("budget_k", "window_sim_sec", "alternation_max")
            if getattr(self, name) is None
        ]
        if self.enabled and missing:
            raise ValueError(
                f"churn_bound.enabled needs {', '.join(missing)}: the bound's values are "
                "frozen from churn data (prereg-v3 A21(b)), never defaulted"
            )
        return self


class TaskStreamConfig(BaseModel):
    """The v3 S1 (MAPD-5) task-stream mode's settings (`task_stream:`).

    Disabled (the default), the registry holds the one static `initial_tasks`
    assignment per robot and nothing here is read, so every run is
    byte-identical to before the block existed. Enabled, each robot works
    through a seeded FIFO queue of `tasks_per_robot` destination nodes
    (`swarm_orchestrator.task_stream`): its registry goal is its current task
    node, kept there through an accepted arrival and the dwell that follows
    (pop-on-dwell-end, so the detector's arrival excusal covers the dwell),
    and replaced by the next node only once the dwell ends.

    Clocks are part of the field names: the dwell and the horizon are in
    sim-s (M1 scene stamps). The release stagger is either wall-s
    (`release_stagger_wall_sec`, M5's monotonic clock through the existing
    `start_delay_sec` path) or sim-s (`release_stagger_sim_sec`, prereg-v3
    A12(ii), closing scene doc Open Question S1-10): robot k is released on
    the first accepted scene whose stamp reaches the stream's first scene
    stamp + k x the stagger, so the release spacing no longer scales with the
    real-time factor. The two keys are mutually exclusive.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = False
    # Node id -> world-frame (x, y) in metres. The registry carries no heading.
    nodes: dict[str, tuple[float, float]] = Field(default_factory=dict)
    tasks_per_robot: int = Field(default=5, ge=1)
    # Required when enabled: the registered seed of this episode (the S1
    # 100-seed list). Never derived, so a run cannot draw an unregistered
    # sequence.
    seed: int | None = None
    # Robot id -> the node it spawns on. None draws a distinct node per robot
    # from `seed` (`task_stream.draw_start_nodes`); either way the drawn
    # schedule is the first record of the run's tasks JSONL so a mismatch
    # with the actual spawn is detectable.
    start_nodes: dict[str, str] | None = None
    # Unordered node pairs never drawn as consecutive legs (S1: Wp-Wm).
    forbidden_legs: tuple[tuple[str, str], ...] = ()
    # Registry task labels, cycled per robot from its first task (GECCO's
    # pickup/delivery alternation; wording is scene doc Open Question S1-5).
    task_labels: tuple[str, ...] = Field(default=("pickup", "delivery"), min_length=1)
    # Robot k (0-based, natural robot-id order) is held `start_pending` for
    # k x this many wall-s after M5 starts. The registered value is 4 sim-s,
    # so the yaml carries 4 / RTF_pilot.
    release_stagger_wall_sec: float = Field(default=4.0, ge=0.0)
    # Sim-time stagger (A12(ii)): robot k is held until a scene stamp reaches
    # episode_start_sim + k x this many sim-s, where episode_start_sim is the
    # first non-dropped scene the stream sees (never the absolute M1 clock,
    # which already reads ~30 sim-s at M5's first scene). Every robot,
    # robot k = 0 included, is released on a scene callback, so each release
    # carries its sim_t. Consecutive releases land in [stagger - g, stagger + g)
    # sim-s, g = the largest gap between accepted scene stamps around them.
    # None (the default) keeps the wall-clock path.
    release_stagger_sim_sec: float | None = Field(default=None, gt=0.0)
    dwell_sim_sec: float = Field(default=5.0, ge=0.0)
    # Recorded in the manifest only; M5 never stops an episode.
    horizon_sim_sec: float | None = Field(default=None, gt=0.0)
    # What a robot does once its queue is empty. Only "park" (stay on its
    # last node, scene doc variant C) is built: the wandering analog (variant
    # D) waits on the ruling of scene doc Open Question S1-1.
    finished_mode: Literal["park"] = "park"

    @property
    def release_clock(self) -> Literal["wall", "sim"]:
        """Which clock the release stagger counts on."""
        return "wall" if self.release_stagger_sim_sec is None else "sim"

    @model_validator(mode="after")
    def _one_release_clock(self) -> TaskStreamConfig:
        # `model_fields_set`, not a value check: the wall key has a default,
        # so only an explicitly written wall key conflicts with the sim key.
        if (
            self.release_stagger_sim_sec is not None
            and "release_stagger_wall_sec" in self.model_fields_set
        ):
            raise ValueError(
                "task_stream.release_stagger_sim_sec and release_stagger_wall_sec are "
                "mutually exclusive: set exactly one release clock"
            )
        return self

    @model_serializer(mode="wrap")
    def _omit_unused_wall_stagger(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        # The wall key's default would otherwise be dumped beside the sim
        # key, and reloading that dump would trip the exclusion above; a
        # wall-clock config dumps exactly as before the sim key existed.
        data = handler(self)
        if self.release_stagger_sim_sec is None:
            data.pop("release_stagger_sim_sec", None)
        else:
            data.pop("release_stagger_wall_sec", None)
        return data

    @model_validator(mode="after")
    def _enabled_stream_is_drawable(self) -> TaskStreamConfig:
        if not self.enabled:
            return self
        if self.seed is None:
            raise ValueError("task_stream.seed is required when task_stream.enabled")
        if len(self.nodes) < 2:
            raise ValueError("task_stream.nodes needs at least two nodes")
        for leg in self.forbidden_legs:
            if leg[0] == leg[1] or not set(leg) <= set(self.nodes):
                raise ValueError(
                    f"task_stream.forbidden_legs entry {list(leg)} must name two distinct "
                    "known nodes"
                )
        forbidden = {frozenset(leg) for leg in self.forbidden_legs}
        for node in self.nodes:
            if not any(
                other != node and frozenset((node, other)) not in forbidden
                for other in self.nodes
            ):
                raise ValueError(f"task_stream node {node!r} has no legal next node")
        if self.start_nodes is not None:
            unknown = sorted(set(self.start_nodes.values()) - set(self.nodes))
            if unknown:
                raise ValueError(f"task_stream.start_nodes names unknown nodes {unknown}")
            if len(set(self.start_nodes.values())) != len(self.start_nodes):
                raise ValueError("task_stream.start_nodes must give each robot its own node")
        return self


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
    # prereg-v3 R3.3 arm (dispatch-model-order-when-verified): the RECEDE
    # dispatch order of a `junction_clear` resolution. "chi" (default) is the
    # inherited behaviour, byte-identical dispatch. "model_when_verified"
    # dispatches the model's own `proposed_plan` recede order when that plan
    # verified `vlm_verbatim`; repaired / m3_default plans stay chi. Recede
    # set, pockets, cross and release are unchanged in both modes. Recorded
    # in every decision artifact (`plan_dispatch_order_source`, beside the
    # per-decision `dispatch_order_source`). Needs `plan_channel_enabled`.
    plan_dispatch_order_source: DispatchOrderSourceMode = "chi"
    # Prompt apparatus (prereg-v2 rev 6 + round-3 deltas, 2026-10-04): five
    # registered A/B conditions, ALL default off, each recorded in every
    # decision artifact's `prompt_conditions` block whatever its value
    # (`docs/reports/2026-10-04-visual-apparatus.md`). The grid and the trails
    # are DRAWN by M1 (swarm_perception config/annotation.yaml); these two
    # flags only let M5 state them in the prompt, and only when M1's scene
    # diagnostics report it actually drew them (a mismatch is logged and
    # recorded, never papered over). The metric grid is a per-backend A/B,
    # never a default (round-3 delta: grid overlays can hurt some backends).
    prompt_metric_grid: bool = False
    prompt_motion_trails: bool = False
    # Second image: an enlarged crop of the annotated frame around the robots
    # the analysis was triggered for, `prompt_zoom_tile_margin_m` of world
    # margin around their bounding box, resized to `prompt_zoom_tile_width_px`.
    prompt_zoom_tile: bool = False
    prompt_zoom_tile_margin_m: float = Field(default=0.6, gt=0.0)
    prompt_zoom_tile_width_px: int = Field(default=640, ge=64)
    # Permutation voting: 1 = today's single call. N > 1 renders the SAME
    # snapshot under N cyclic shifts of the robot presentation order, makes N
    # full reasoner calls (N x the API cost and up to N x the latency) and
    # majority-votes the decision (`swarm_orchestrator.permutation_votes`).
    prompt_permutation_votes: int = Field(default=1, ge=1)
    # Verifier-candidate-options condition: list, per robot, the plan actions
    # M3's own audit accepts in the current scene. CONSTRUCT CHANGE: plan
    # metrics under this flag measure constrained selection, not free planning.
    prompt_candidate_options: bool = False
    # Plan-grammar rules condition (prompt v3.5, 2026-11-15): two generic
    # sentences in the plan grammar ("each robot exactly once", "a cross leg
    # after the yield leg that releases it"). Default off = the v3.4 prompt,
    # byte-identical; recorded as `prompt_conditions.plan_grammar_rules`.
    prompt_plan_grammar_rules: bool = False
    # prereg-v3 R3.4 contradiction trigger (closed-loop item); default off.
    contradiction_trigger: ContradictionTriggerConfig = Field(
        default_factory=ContradictionTriggerConfig
    )
    # prereg-v3 R3.4 failure-explanation line: append one classically derived
    # cause sentence to each failure-context block's `failure_detail`
    # (`reasoning_pipeline.explain_attempt`). Default off, so every prompt is
    # byte-identical to the v1/v2-era failure context.
    failure_explanation_enabled: bool = False
    # v3 S1 task-stream mode (MAPD-5); default off.
    task_stream: TaskStreamConfig = Field(default_factory=TaskStreamConfig)
    # prereg-v3 A12(iii) scene-unchanged re-trigger suppression; default off.
    reanalysis_suppression: ReanalysisSuppressionConfig = Field(
        default_factory=ReanalysisSuppressionConfig
    )
    # Dispatch-off probe flag (v3 build item, scene doc item 9): False runs
    # the full triggered pipeline -- trigger, M2, M3, artifact with every
    # provenance block -- but never publishes the command to M4, and the
    # artifact gains `dispatch_enabled: false` / `dispatch_suppressed`. Unlike
    # `t0_probe_mode` (off-trigger, stage-1 only probes), it acts on real
    # triggered analyses. For log-only scoring (S4/S5/S6).
    dispatch_enabled: bool = True
    # S1 episode loop (2026-10-09, E1 finding): a refused yield grounds to an
    # all-robot `temporary_wait` fan-out (`yield refused: ...`). Re-sent every
    # cooldown, those waits cancelled Nav2 goals before any progress-checker
    # recovery could fire (E1: 0 spins all episode, a box-pinned robot held in
    # place by Layer 2) and kept the scene-unchanged suppression from ever
    # arming. True, and ONLY while `task_stream.enabled`, such a refusal is
    # withheld instead: nothing reaches M4, the artifact records
    # `dispatch_withheld`, a cooldown starts and the suppression reference
    # arms (outcome `refusal_no_action`). False (the default), or with the
    # task stream off, the refusal fan-out dispatches byte-for-byte as before.
    refusal_no_action: bool = False
    # prereg-v3 A21(b) per-cluster clearing-dispatch bound; default off, values unset.
    churn_bound: ChurnBoundConfig = Field(default_factory=ChurnBoundConfig)
    # prereg-v3 A34 R9 Arm B ("Layer-2-off classical"). False skips Layer 2
    # entirely: no congestion detection, no M2/M3 call (the backend is never
    # even constructed), no decision artifact, no shadow_classical, no T0
    # probe, no contradiction trigger and no dispatch, while the registry,
    # task stream, arrival gate, tasks log and scene log run unchanged. Unlike
    # `dispatch_enabled: false` (M2/M3 still run and bill), nothing reaches a
    # backend. True (the default) is the unchanged node.
    reasoning_enabled: bool = True

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
    def _prompt_apparatus_needs_prompt_v3(self) -> OrchestratorConfig:
        # The apparatus sentences, the zoom tile and the options block are
        # rendered by the prompt-v3 template only (v1/v2 are frozen), and M5
        # renders v3 only behind `plan_channel_enabled`; a flag that could not
        # take effect fails here instead of silently running the control cell.
        requested = [
            name
            for name in (
                "prompt_metric_grid",
                "prompt_motion_trails",
                "prompt_zoom_tile",
                "prompt_candidate_options",
                "prompt_plan_grammar_rules",
            )
            if getattr(self, name)
        ]
        if requested and not self.plan_channel_enabled:
            raise ValueError(
                f"{', '.join(requested)} require plan_channel_enabled (prompt v3); "
                "the frozen v1/v2 templates render none of them"
            )
        return self

    @model_validator(mode="after")
    def _model_dispatch_order_needs_plan_channel(self) -> OrchestratorConfig:
        # Only the plan channel verifies a `proposed_plan` and seeds the
        # junction phase queue; without it condition B would silently run
        # condition A's dispatch.
        if self.plan_dispatch_order_source != "chi" and not self.plan_channel_enabled:
            raise ValueError(
                f"plan_dispatch_order_source={self.plan_dispatch_order_source!r} requires "
                "plan_channel_enabled (plans are only verified on the plan channel)"
            )
        return self

    @model_validator(mode="after")
    def _task_stream_matches_roster(self) -> OrchestratorConfig:
        stream = self.task_stream
        if not stream.enabled:
            return self
        robots = set(self.initial_tasks)
        if stream.start_nodes is not None and set(stream.start_nodes) != robots:
            raise ValueError(
                f"task_stream.start_nodes robots {sorted(stream.start_nodes)} must equal the "
                f"initial_tasks robots {sorted(robots)}"
            )
        if stream.start_nodes is None and len(stream.nodes) < len(robots):
            raise ValueError(
                f"task_stream draws a distinct start node per robot: {len(robots)} robots "
                f"need at least {len(robots)} nodes, got {len(stream.nodes)}"
            )
        delayed = sorted(rid for rid, task in self.initial_tasks.items() if task.start_delay_sec)
        if delayed:
            raise ValueError(
                f"initial_tasks start_delay_sec must be 0 under task_stream (robots {delayed}): "
                "the stream's release stagger owns every release"
            )
        if not self.arrival_position_check:
            # Unverified, a stale Nav2 success landing just after the next task
            # is issued would be accepted against it and skip that task.
            raise ValueError("task_stream requires arrival_position_check: true")
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
    # Ranked best-first, as `prepare_filtered_retreat_selection` returned
    # them (escort/park survivors only, re-lettered), with their sweep
    # clearances; `default_label` is the first one's M3 label (generation
    # order). When a call is made each also carries `letter`, the
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
    # prereg-v3 A29 item (ii): the candidates the escort/park filter dropped
    # before stage 2 (pre-filter label, park pose, passer, clearance), one
    # per violating escort leg; empty when the switch is off or nothing was
    # dropped, and then omitted from the dump.
    dropped_candidates: tuple[DroppedCandidate, ...] = ()

    @model_serializer(mode="wrap")
    def _omit_empty_dropped_candidates(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        # A switch-off record dumps byte-identically to before the field
        # existed (the A29 switch-off parity golden).
        data = handler(self)
        if not self.dropped_candidates:
            data.pop("dropped_candidates", None)
        return data


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
    # χ-epsilon verbatim rule (prereg-v2 (a0), RULED 2026-10-03): True when a
    # `junction_clear` plan's recede order differs from the χ order but
    # within `GroundingParams.junction_recede_order_epsilon`
    # (`command_grounder.JunctionDispatchMatch`). `dispatch_matches_plan` is
    # then still True; this flag is what keeps the divergence visible. False
    # for every other decision. Always measured against χ, also when
    # `PipelineOutcome.dispatch_order_source == "model"` (R3.3), where the
    # dispatched order IS the plan's: it is the A/B stratifier, true exactly
    # where condition B dispatches differently from condition A.
    order_equivalent: bool = False
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
    # `junction_clear`'s full precomputed phase sequence (prereg-v2 (a) M5,
    # build-order step 5): None unless `grounded_command`'s decision is
    # `junction_clear` AND a non-degenerate recede set was groundable
    # (`command_grounder.ground_junction_clear_phases`) AND plan tracking is
    # enabled (`plan_channel_enabled`) -- the SAME flag `plan` is gated on,
    # per the M5 spec section ("Behind the SAME `plan_channel_enabled`
    # flag"). `_dispatch` seeds a `JunctionPhaseQueue` from this instead of
    # dispatching `grounded_command` alone; a flag-off run never sets this,
    # so its dispatch is unchanged -- just the one phase
    # `grounded_command` already is (`ground_reasoner_result`'s own
    # single-command contract: "the NEXT unresolved step").
    junction_phases: JunctionClearPhasePlan | None = None
    # prereg-v3 R3.3: "model" exactly when `junction_phases`' recede phases
    # (and so `grounded_command`, their phase 0) follow the model's verified
    # `proposed_plan` order (`plan_dispatch_order_source:
    # model_when_verified` AND provenance `vlm_verbatim`); "chi" for every
    # other outcome -- the inherited order rule (vacuously so for a
    # decision with no recede sequence). The artifact records null instead
    # when no command was grounded.
    dispatch_order_source: DispatchOrderSource = "chi"
    # Permutation-voting record (`prompt_permutation_votes` > 1): every call's
    # order, prompt hashes, raw response and vote, plus the winner. None for a
    # single-call run, whose outcome is then unchanged.
    permutation_votes: PermutationVoteRecord | None = None


class RegistryDispatch(BaseModel):
    """What M5's task-registry robot filter leaves of one outcome's grounded command.

    The pipeline filters a grounded command to the robots in the request's
    snapshot; `_dispatch` then filters it again to the robots in
    `initial_tasks`. The two sets differ whenever M1 tracks a robot with no
    registry task (a T3a intruder), so the command M4 receives can address
    fewer robots than the grounded one. Computed once, before the decision
    artifact is written, and the SAME `command` is what `_dispatch` fans out
    (forcing-audit A5b, 2026-10-07), so the recorded and dispatched robot
    sets are equal by construction.
    """

    model_config = ConfigDict(frozen=True)

    # The registry-filtered command, exactly as `_dispatch` fans it out; None
    # when the filter refused it (no action left for a registry robot).
    command: dict[str, Any] | None
    # Robots the grounded command addressed that the filter removed.
    dropped_robot_ids: tuple[str, ...] = ()
    # Why the filter refused the command; None whenever `command` is set.
    error: str | None = None
    # `junction_clear` only (`PipelineOutcome.junction_phases` set): the
    # robot ids each later phase's command, and the fallback command, address
    # after the same filter, which `_dispatch_junction_phase` applies to them
    # at dispatch time. An empty tuple marks a phase the filter would refuse.
    junction_phase_robot_ids: tuple[tuple[str, ...], ...] | None = None
    junction_fallback_robot_ids: tuple[str, ...] | None = None

    @property
    def robot_ids(self) -> list[str]:
        """The robots the filtered command addresses, in action order."""
        if self.command is None:
            return []
        return [action["robot_id"] for action in self.command.get("actions", [])]


class AnnotationOverlayReport(BaseModel):
    """Which prompt-apparatus overlays M1 says it drew on its annotated frame."""

    model_config = ConfigDict(frozen=True)

    overlays: tuple[str, ...] = ()
    metric_grid_spacing_m: float | None = None

    @property
    def metric_grid(self) -> bool:
        """Whether the labeled metric grid was drawn."""
        return "metric_grid" in self.overlays

    @property
    def motion_trails(self) -> bool:
        """Whether motion trails were drawn."""
        return "motion_trails" in self.overlays


def parse_annotation_overlays(raw: str) -> AnnotationOverlayReport:
    """Read M1's `annotation_overlays` diagnostics off a SceneState JSON string.

    Kept apart from `SceneSnapshot` so the snapshot -- stored verbatim in every
    artifact and scene log -- is unchanged by the apparatus.

    Args:
        raw: JSON string published on `/perception/scene_state`.

    Returns:
        The report; empty when M1 drew no overlay or the payload is malformed.
    """
    try:
        diagnostics = json.loads(raw).get("diagnostics", {}) or {}
    except (json.JSONDecodeError, AttributeError):
        return AnnotationOverlayReport()
    overlays = diagnostics.get("annotation_overlays") or []
    spacing = diagnostics.get("metric_grid_spacing_m")
    return AnnotationOverlayReport(
        overlays=tuple(str(name) for name in overlays if isinstance(name, str)),
        metric_grid_spacing_m=(
            float(spacing)
            if isinstance(spacing, (int, float)) and not isinstance(spacing, bool) and spacing > 0
            else None
        ),
    )


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


REASONING_OFF_STATUS_LINE = (
    "reasoning_enabled=false layer2=off detection=off m2=off m3=off "
    "shadow_classical=off t0_probe=off contradiction_trigger=off dispatch=off"
)
"""M5's one startup line when `reasoning_enabled` is false (the Arm B condition gate greps it)."""


class Layer2Gate(BaseModel):
    """Which Layer-2 paths M5 runs, resolved once from the config at startup.

    Every field is False when `reasoning_enabled` is false, whatever the
    individual flags say; otherwise each is that flag's own value.
    """

    model_config = ConfigDict(frozen=True)

    reasoning_enabled: bool
    shadow_classical: bool
    t0_probe_mode: bool
    contradiction_trigger: bool
    overridden: tuple[str, ...] = ()


def resolve_layer2_gate(config: OrchestratorConfig) -> Layer2Gate:
    """Resolve the Layer-2 paths M5 may run under `config`.

    Args:
        config: The loaded orchestrator config.

    Returns:
        The gate; `overridden` names each flag that was set on but is forced
        off because `reasoning_enabled` is false, so M5 can warn about it.
    """
    requested = {
        "shadow_classical": config.shadow_classical,
        "t0_probe_mode": config.t0_probe_mode,
        "contradiction_trigger": config.contradiction_trigger.enabled,
    }
    if config.reasoning_enabled:
        return Layer2Gate(reasoning_enabled=True, **requested)
    return Layer2Gate(
        reasoning_enabled=False,
        shadow_classical=False,
        t0_probe_mode=False,
        contradiction_trigger=False,
        overridden=tuple(name for name, on in requested.items() if on),
    )


def should_submit_pipeline(config: OrchestratorConfig) -> bool:
    """Return whether M5 may run congestion detection and submit an M2/M3 analysis.

    Args:
        config: The loaded orchestrator config.

    Returns:
        False under Arm B (`reasoning_enabled: false`): no stall, manual or
        contradiction trigger may start an analysis.
    """
    return config.reasoning_enabled


def reasoning_status_line(config: OrchestratorConfig) -> str | None:
    """Return M5's Layer-2-off startup line, or None when reasoning is enabled.

    Args:
        config: The loaded orchestrator config.

    Returns:
        `REASONING_OFF_STATUS_LINE` under `reasoning_enabled: false`, else None
        (a reasoning-on node logs nothing new).
    """
    return None if config.reasoning_enabled else REASONING_OFF_STATUS_LINE


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
