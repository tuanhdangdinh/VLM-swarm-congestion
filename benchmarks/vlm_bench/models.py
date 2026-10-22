"""Frozen data contracts of the v4 offline VLM bench (`docs/specs/v4_vlm_bench.md`)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GTCluster(BaseModel):
    """One A33(5) GT conflict episode, times in rel-s."""

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    onset_s: float
    end_s: float
    involved: tuple[str, ...]
    pairs: tuple[tuple[str, str], ...] = ()


class GTContext(BaseModel):
    """The item's GT conflicts: those active in its A33 window, and the whole episode's."""

    model_config = ConfigDict(frozen=True)

    clusters: tuple[GTCluster, ...] = ()
    episode_conflicts: tuple[GTCluster, ...] = ()
    pre_s: float = 0.0
    post_s: float = 5.0
    t_end_s: float | None = None


class RecordedAnswer(BaseModel):
    """The live M2 answer stored in the decision artifact."""

    model_config = ConfigDict(frozen=True)

    raw_text: str | None = None
    decision: dict[str, Any] | None = None
    parse_status: str | None = None
    attempts: int | None = None
    token_usage: dict[str, int] | None = None
    latency_ms: int | None = None
    backend_id: str | None = None
    model_id: str | None = None
    est_usd_per_call: float | None = None


class LiveOutcome(BaseModel):
    """What M3/M5 did with the recorded answer live."""

    model_config = ConfigDict(frozen=True)

    refusal_reason: str | None = None
    dispatched_kinds: tuple[str, ...] = ()
    stage2_status: str | None = None
    plan: dict[str, Any] | None = None
    plan_state: dict[str, Any] | None = None


class RobotIntent(BaseModel):
    """A robot's task intent rebuilt from the task stream (`RobotTaskIntent` fields)."""

    model_config = ConfigDict(frozen=True)

    goal: tuple[float, float]
    next_goal: tuple[float, float] | None = None
    dwell_sec: float = Field(default=0.0, ge=0.0)


class GroundingContext(BaseModel):
    """Everything the offline grounder needs, as the episode ran it."""

    model_config = ConfigDict(frozen=True)

    overlay: dict[str, Any]
    params: dict[str, Any] | None = None
    params_path: str | None = None
    params_file_md5: str | None = None
    params_match_file: bool | None = None
    goal_references: dict[str, tuple[float, float]] = Field(default_factory=dict)
    task_intents: dict[str, RobotIntent] = Field(default_factory=dict)


class ClassicalWindow(BaseModel):
    """The shadow's inputs for one analysis: history frames plus its settings."""

    model_config = ConfigDict(frozen=True)

    window_sec: float = 60.0
    sample_period_sec: float = 0.25
    prior_attempts: int = Field(default=0, ge=0)
    params: dict[str, Any] | None = None
    frames: tuple[dict[str, Any], ...] = ()
    recorded_decision: dict[str, Any] | None = None


class MCReference(BaseModel):
    """The S1 MC first-conflict prediction for the episode's seed (an upper bound, A22)."""

    model_config = ConfigDict(frozen=True)

    pair: tuple[str, ...]
    yielder: str | None = None
    outcome: str | None = None
    source: str


class PromptRecord(BaseModel):
    """The stored rendered prompt and the apparatus needed to rebuild the request."""

    model_config = ConfigDict(frozen=True)

    system_prompt: str | None = None
    user_prompt: str | None = None
    system_sha256: str | None = None
    user_sha256: str | None = None
    prompt_version: int = 1
    robot_order: str = "id_asc"
    failure_context: dict[str, Any] | None = None
    last_failed_context: dict[str, Any] | None = None
    plan_state: dict[str, Any] | None = None
    prompt_conditions: dict[str, Any] | None = None


class BenchItem(BaseModel):
    """One recorded analysis: inputs, recorded answer, live outcome and GT context."""

    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    bundle: str
    batch: str
    episode: str
    condition: str
    seed: int | None = None
    request_id: str
    stamp: float
    t_s: float
    scene: dict[str, Any]
    prompt: PromptRecord
    frame_path: str | None = None
    recorded: RecordedAnswer
    live: LiveOutcome
    grounding: GroundingContext
    classical: ClassicalWindow
    gt: GTContext
    mc: MCReference | None = None


class GroundingOutcome(BaseModel):
    """One offline M3 grounding of one decision."""

    model_config = ConfigDict(frozen=True)

    feasible: bool
    refusal_reason: str | None = None
    refusal_class: str | None = None
    error: str | None = None
    grounded_yielder: str | None = None
    action_kinds: tuple[str, ...] = ()


class ItemScore(BaseModel):
    """Every per-item metric field for one decision (one JSONL line of a run)."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    batch: str
    episode: str
    source: str
    decision: dict[str, Any] | None
    valid: bool
    positive: bool
    strategy: str | None = None
    involved: tuple[str, ...] = ()
    grounding: GroundingOutcome | None = None
    live_refused: bool | None = None
    n_clusters: int = 0
    covered: bool | None = None
    cluster_recalls: tuple[float, ...] = ()
    matched_conflict: int | None = None
    f1_matched: float | None = None
    f1_unconditional: float | None = None
    yielder: str | None = None
    oracle_yielders: tuple[str, ...] | None = None
    oracle_agree: bool | None = None
    classical_yielder: str | None = None
    classical_agree: bool | None = None
    mc_yielder: str | None = None
    mc_agree: bool | None = None
    no_gt_conflict: bool = False
    token_usage: dict[str, int] | None = None
    latency_ms: int | None = None
    est_usd: float | None = None
    note: str | None = None
