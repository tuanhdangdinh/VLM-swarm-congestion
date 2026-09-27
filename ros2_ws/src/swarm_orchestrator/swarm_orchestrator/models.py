"""Pydantic contracts and parsing helpers for the M5 orchestrator (no rclpy)."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from reasoning.baselines import ConflictZone
from reasoning.rag.command_grounder import YieldFeasibilityMode
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    ReasonerResult,
    StaticObstacleInput,
)
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


class TaskAssignment(BaseModel):
    """A robot's base mission assignment: task label plus world-frame goal."""

    model_config = ConfigDict(frozen=True)

    task: str = Field(min_length=1)
    goal: tuple[float, float]


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
    # sequence. Fixed modes ignore it.
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


class PipelineOutcome(BaseModel):
    """Result of one M2->M3 reasoning pipeline run."""

    model_config = ConfigDict(frozen=True)

    request_id: str = Field(min_length=1)
    reasoner_result: ReasonerResult
    grounded_command: dict[str, Any] | None
    terminal_stage: TerminalStage
    failure_reason: str | None = None


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
        rid: TaskAssignment(task=spec["task"], goal=tuple(spec["goal"]))
        for rid, spec in tasks_in.items()
    }
    # Merge configured topic overrides over defaults so partial overrides keep the rest.
    topics = {**DEFAULT_TOPICS, **raw.get("topics", {})}
    merged = {**raw, "initial_tasks": initial_tasks, "topics": topics}
    return OrchestratorConfig(**merged)
