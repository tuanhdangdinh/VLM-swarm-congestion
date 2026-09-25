"""Pydantic contracts and parsing helpers for the M5 orchestrator (no rclpy)."""
from __future__ import annotations

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
