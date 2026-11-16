"""v4 per-cluster choice, Stage 1 live shadow: compute and record, dispatch nothing (no rclpy).

The shadow re-asks the scene of one ordinary analysis with the
`grounding_first_per_cluster` contract measured offline (R7): the v2 options
are enumerated per observed group on the analysis snapshot
(`reasoning.rag.cluster_options`), split into one slot per group
(`build_slots`), asked in one M2 call through the shared runner
(`reasoning.vlm.per_cluster_runner`), each chosen option is grounded alone
(`ground_probe`, stage 2 not run, as offline) and the chosen commands are
checked together (`reasoning.rag.joint_check`). Everything here is the
bench's code path; only the inputs come from live objects
(`live_probe_inputs`, built from the ordinary analysis's request and the
pipeline's own M3 inputs instead of a `BenchItem`).

`compute_per_cluster_shadow` never raises: a failure or an exceeded deadline
is the record's `status` and `error`, with every phase that completed kept.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.cluster_options import (
    GROUPING_RULE,
    GroupingParams,
    ProbeInputs,
    executed_key_v2,
    generate_cluster_candidates,
    ground_probe,
)
from reasoning.rag.command_grounder import YieldFeasibilityMode
from reasoning.rag.joint_check import joint_check
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_shield import RobotTaskIntent
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import ReasonerConfig, ReasonerRequest, StaticObstacleInput
from reasoning.vlm.per_cluster_choice import (
    GENERATOR_VERSION_PER_CLUSTER,
    NONE_FEASIBLE,
    SLOT_RULE,
    OptionIds,
    PerClusterCandidateSet,
    build_slots,
)
from reasoning.vlm.per_cluster_runner import PerClusterRunResult, run_per_cluster_choice
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy
from swarm_orchestrator.retreat_stage2 import snapshot_frame_from_request

ShadowStatus = Literal["ok", "parse_failed", "error", "timeout", "skipped"]
LookupsSource = Literal["ordinary_grounding", "recomputed"]
# Bounds the raw reply copied into the artifact; the prompt is never copied.
RAW_TEXT_MAX_CHARS = 4000


class GroundingLookups(BaseModel):
    """The registry-derived M3 inputs one ordinary grounding call actually used.

    `InProcessPipeline` reads goal references and task intents from M5's
    registry inside its worker, after the M2 call; it keeps the values it
    passed so the shadow grounds on the same ones. None means the ordinary
    call did not pass that input (the params do not use it).
    """

    model_config = ConfigDict(frozen=True)

    request_id: str
    goal_references: dict[str, tuple[float, float]] | None = None
    task_intents: dict[str, RobotTaskIntent] | None = None


def live_probe_inputs(
    request: ReasonerRequest,
    *,
    backend_id: str,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
    params: GroundingParams | None,
    priorities: Mapping[str, int],
    goal_references: Mapping[str, tuple[float, float]] | None,
    task_intents: Mapping[str, RobotTaskIntent] | None,
) -> ProbeInputs:
    """The shared probe inputs of one live analysis: what its ordinary M3 call received.

    The frame is `snapshot_frame_from_request(request)`, the one frame the
    live pipeline grounds on; the rest are the pipeline's own M3 inputs.

    Args:
        request: The ordinary analysis's request (its robot states are the
            analysed snapshot, registry goals and tasks attached).
        backend_id: Recorded in probe diagnostics only.
        geometry: The pipeline's scenario geometry.
        static_obstacles: The pipeline's static obstacles.
        yield_feasibility_mode: The pipeline's yield feasibility mode.
        params: The pipeline's grounding params.
        priorities: The pipeline's registry priorities.
        goal_references: What the ordinary call passed (None: not passed).
        task_intents: What the ordinary call passed (None: not passed).

    Returns:
        The inputs `reasoning.rag.cluster_options.ground_probe` takes.
    """
    return ProbeInputs(
        request_id=request.request_id,
        backend_id=backend_id,
        snapshot=snapshot_frame_from_request(request),
        geometry=geometry,
        static_obstacles=tuple(static_obstacles),
        yield_feasibility_mode=yield_feasibility_mode,
        params=params,
        priorities=dict(priorities),
        goal_references=dict(goal_references or {}),
        task_intents=dict(task_intents or {}),
    )


class ShadowOption(BaseModel):
    """One offered option, compact (the option text is not copied)."""

    model_config = ConfigDict(frozen=True)

    option_id: str
    strategy: str
    robots: tuple[str, ...]
    yield_robot: str | None = None
    key: tuple[str, ...]
    scope: str


class ShadowSlot(BaseModel):
    """One observed group the answer had to decide on."""

    model_config = ConfigDict(frozen=True)

    label: str
    robots: tuple[str, ...]
    options: tuple[ShadowOption, ...]


class ShadowChoice(BaseModel):
    """One slot's choice and what grounding it alone executes."""

    model_config = ConfigDict(frozen=True)

    label: str
    choice: str
    none_feasible: bool
    strategy: str | None = None
    robots: tuple[str, ...] = ()
    yield_robot: str | None = None
    # The offered option's key, and what the shadow grounding executes now.
    offered_key: tuple[str, ...] | None = None
    executed_key: tuple[str, ...] | None = None
    # executed_key equals offered_key (M3 executes the option as offered).
    feasible: bool = False
    command_id: str | None = None
    action_kinds: tuple[str, ...] = ()
    error: str | None = None


class ShadowM2(BaseModel):
    """The per-group M2 call, without prompt or image data."""

    model_config = ConfigDict(frozen=True)

    backend_id: str
    max_attempts: int
    call_timeout_sec: float
    prompt_sha256: str
    attempts: int
    parse_status: str
    error: str | None = None
    raw_text: str | None = None
    raw_text_truncated: bool = False
    token_usage: dict[str, int] | None = None
    attempt_token_usage: tuple[dict[str, int] | None, ...] = ()
    latency_ms: int | None = None
    attempt_latency_ms: tuple[int | None, ...] = ()
    served_model: str | None = None
    backoff_sec: float = 0.0


class ShadowTimings(BaseModel):
    """Wall-clock milliseconds per phase (None for a phase that did not run)."""

    model_config = ConfigDict(frozen=True)

    enumeration_ms: int | None = None
    m2_call_ms: int | None = None
    grounding_ms: int | None = None
    total_ms: int | None = None


class PerClusterShadowRecord(BaseModel):
    """The `per_cluster_shadow` block of one analysis's decision artifact."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    status: ShadowStatus
    error: str | None = None
    generator_version: str = GENERATOR_VERSION_PER_CLUSTER
    grouping: dict[str, Any] = Field(default_factory=dict)
    lookups_source: LookupsSource | None = None
    image_path: str | None = None
    groups: tuple[dict[str, Any], ...] = ()
    slots: tuple[ShadowSlot, ...] = ()
    n_options: int = 0
    n_slots: int = 0
    m2: ShadowM2 | None = None
    choices: dict[str, str] | None = None
    per_choice: tuple[ShadowChoice, ...] = ()
    none_feasible: dict[str, bool] = Field(default_factory=dict)
    joint_check: dict[str, Any] | None = None
    joint_exact_conflict: bool | None = None
    timings: ShadowTimings = Field(default_factory=ShadowTimings)


class ShadowDeadlineExceededError(RuntimeError):
    """The shadow's deadline passed between two phases."""


def skipped_record(request_id: str, reason: str) -> PerClusterShadowRecord:
    """A record for a shadow that was never computed.

    Args:
        request_id: The ordinary analysis.
        reason: Why (backlog, no backend, submit failure).

    Returns:
        A `skipped` record carrying the reason as `error`.
    """
    return PerClusterShadowRecord(request_id=request_id, status="skipped", error=reason)


def _ms(start: float, clock: Callable[[], float]) -> int:
    return int((clock() - start) * 1000)


def _slots(candidates: PerClusterCandidateSet) -> tuple[ShadowSlot, ...]:
    return tuple(
        ShadowSlot(
            label=slot.label,
            robots=slot.robots,
            options=tuple(
                ShadowOption(
                    option_id=option_id,
                    strategy=option.strategy,
                    robots=option.robots,
                    yield_robot=option.yield_robot,
                    key=option.key,
                    scope=option.scope,
                )
                for option_id, option in zip(slot.option_ids, slot.options, strict=True)
            ),
        )
        for slot in candidates.slots
    )


def _m2_block(
    run: PerClusterRunResult, backend_id: str, config: ReasonerConfig
) -> ShadowM2:
    raw = run.raw_text
    truncated = raw is not None and len(raw) > RAW_TEXT_MAX_CHARS
    return ShadowM2(
        backend_id=backend_id,
        max_attempts=config.max_attempts,
        call_timeout_sec=config.timeout_sec,
        prompt_sha256=run.prompt_sha256,
        attempts=run.attempts,
        parse_status=run.parse_status,
        error=run.error,
        raw_text=raw[:RAW_TEXT_MAX_CHARS] if truncated else raw,
        raw_text_truncated=truncated,
        token_usage=run.token_usage,
        attempt_token_usage=run.attempt_token_usage,
        latency_ms=run.latency_ms,
        attempt_latency_ms=run.attempt_latency_ms,
        served_model=run.served_model,
        backoff_sec=run.backoff_sec,
    )


def _choice(
    label: str,
    choice: str,
    candidates: PerClusterCandidateSet,
    model_answer: Mapping[str, Any],
    ground: Callable[[dict[str, Any]], dict[str, Any]],
) -> ShadowChoice:
    if choice == NONE_FEASIBLE:
        return ShadowChoice(label=label, choice=choice, none_feasible=True)
    option = candidates.slot(label).option(choice)
    fields: dict[str, Any] = {
        "label": label,
        "choice": choice,
        "none_feasible": False,
        "strategy": option.strategy,
        "robots": option.robots,
        "yield_robot": option.yield_robot,
        "offered_key": option.key,
    }
    try:
        command = ground(option.decision(dict(model_answer)))
    except Exception as exc:  # recorded like the live GROUNDING terminal stage
        return ShadowChoice(**fields, error=f"{type(exc).__name__}: {exc}")
    key = executed_key_v2(option.strategy, command)
    return ShadowChoice(
        **fields,
        executed_key=key,
        feasible=key is not None and key == option.key,
        command_id=command.get("command_id"),
        action_kinds=tuple(str(a.get("action")) for a in command.get("actions") or []),
    )


def compute_per_cluster_shadow(
    request: ReasonerRequest,
    inputs: ProbeInputs,
    grouping: GroupingParams,
    backend: VLMBackend,
    reasoner_config: ReasonerConfig,
    *,
    include_wait: bool = True,
    option_ids: OptionIds = "numbered",
    lookups_source: LookupsSource | None = None,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    retry_policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> PerClusterShadowRecord:
    """Enumerate, ask, ground and joint-check one analysis's scene; never raises.

    Args:
        request: The ordinary analysis's request: its prompt (rebuilt by the
            production builder) and its frame (`image_path`) are reused.
        inputs: `live_probe_inputs` of the same analysis.
        grouping: The observed-grouping rule (the classical `r_conflict_m`).
        backend: The shadow's M2 backend.
        reasoner_config: Attempt budget, per-call timeout and sampling.
        include_wait: List `temporary_wait` options too.
        option_ids: "numbered" (R7) or "opaque".
        lookups_source: Where the goal references and intents came from.
        deadline: `clock()` value after which the next phase is not started.
        clock: Monotonic clock (injected by tests).
        retry_policy: Backoff between failed backend calls.

    Returns:
        The record; `status` is `ok` on a valid answer, `parse_failed` when no
        valid answer came after the attempts, `timeout` or `error` otherwise.
    """
    start = clock()
    grouping_record = {
        "rule": GROUPING_RULE,
        "threshold_m": grouping.threshold_m,
        "slot_rule": SLOT_RULE,
        "include_wait": include_wait,
        "option_ids": option_ids,
        "offgroup": "drop",
        "cross_group": "drop",
    }
    fields: dict[str, Any] = {
        "request_id": request.request_id,
        "grouping": grouping_record,
        "lookups_source": lookups_source,
        "image_path": request.image_path,
    }
    timings: dict[str, int | None] = {}
    ground = partial(ground_probe, inputs)

    def check_deadline(phase: str) -> None:
        if deadline is not None and clock() > deadline:
            raise ShadowDeadlineExceededError(f"deadline passed before {phase}")

    try:
        phase_start = clock()
        base = generate_cluster_candidates(
            inputs.snapshot, request.request_id, grouping, ground, include_wait, "drop", "drop"
        )
        candidates, _, _ = build_slots(base, option_ids)
        timings["enumeration_ms"] = _ms(phase_start, clock)
        fields.update(
            groups=tuple(g.model_dump(mode="json") for g in base.groups),
            slots=_slots(candidates),
            n_options=candidates.n_options,
            n_slots=len(candidates.slots),
        )
        check_deadline("the M2 call")
        if not Path(request.image_path).is_file():
            raise FileNotFoundError(f"frame missing: {request.image_path}")
        phase_start = clock()
        run = run_per_cluster_choice(
            backend, reasoner_config, build_prompt_payload(request), candidates, retry_policy
        )
        timings["m2_call_ms"] = _ms(phase_start, clock)
        fields["m2"] = _m2_block(run, reasoner_config.backend_id, reasoner_config)
        if run.choices is None:
            return PerClusterShadowRecord(
                **fields,
                status="parse_failed",
                error=run.error,
                timings=ShadowTimings(**timings, total_ms=_ms(start, clock)),
            )
        fields["choices"] = dict(run.choices)
        fields["none_feasible"] = {k: v == NONE_FEASIBLE for k, v in run.choices.items()}
        check_deadline("grounding")
        phase_start = clock()
        fields["per_choice"] = tuple(
            _choice(label, choice, candidates, run.model_answer, ground)
            for label, choice in run.choices.items()
        )
        chosen = {
            slot.label: (
                None
                if run.choices[slot.label] == NONE_FEASIBLE
                else slot.option(run.choices[slot.label])
            )
            for slot in candidates.slots
        }
        check = joint_check(inputs.snapshot, chosen, ground, inputs.geometry)
        timings["grounding_ms"] = _ms(phase_start, clock)
        fields["joint_check"] = check.model_dump(mode="json")
        fields["joint_exact_conflict"] = check.exact_conflict
        return PerClusterShadowRecord(
            **fields,
            status="ok",
            timings=ShadowTimings(**timings, total_ms=_ms(start, clock)),
        )
    except ShadowDeadlineExceededError as exc:
        status: ShadowStatus = "timeout"
        error = str(exc)
    except Exception as exc:  # recorded in the artifact, never raised into M5
        status = "error"
        error = f"{type(exc).__name__}: {exc}"
    return PerClusterShadowRecord(
        **fields,
        status=status,
        error=error,
        timings=ShadowTimings(**timings, total_ms=_ms(start, clock)),
    )


def pending_block(request_id: str) -> dict[str, Any]:
    """The placeholder written with the decision artifact, replaced when the shadow ends.

    A node that dies before its shadow ends leaves this block, so a missing
    shadow is visible in the artifact rather than absent.

    Args:
        request_id: The analysis.

    Returns:
        `{"request_id": ..., "status": "pending"}`.
    """
    return {"request_id": request_id, "status": "pending"}


def attach_shadow_block(artifact_path: str | Path, block: Mapping[str, Any]) -> None:
    """Replace the artifact's `per_cluster_shadow` block, atomically.

    The artifact is re-serialized exactly as `write_decision_artifact` writes
    it (indent 2, sorted keys); the temporary file's name does not end in
    `.json`, so no `decisions/*.json` reader or collector can pick it up.

    Args:
        artifact_path: The decision artifact (`<request_id>.json`).
        block: The record, JSON-safe.

    Raises:
        OSError: If the artifact cannot be read or replaced.
        ValueError: If the artifact is not a JSON object.
    """
    path = Path(artifact_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    payload["per_cluster_shadow"] = dict(block)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def format_per_cluster_log(record: PerClusterShadowRecord) -> str:
    """One key-value log line for a finished shadow (no prompt, reply or image data).

    Args:
        record: The record.

    Returns:
        The line.
    """
    choices = (
        "-"
        if record.choices is None
        else ",".join(f"{k}:{v}" for k, v in record.choices.items())
    )
    attempts = None if record.m2 is None else record.m2.attempts
    parse = None if record.m2 is None else record.m2.parse_status
    return (
        f"per_cluster_shadow request={record.request_id} status={record.status} "
        f"slots={record.n_slots} options={record.n_options} choices={choices} "
        f"parse_status={parse} attempts={attempts} "
        f"exact_conflict={record.joint_exact_conflict} "
        f"enumeration_ms={record.timings.enumeration_ms} m2_ms={record.timings.m2_call_ms} "
        f"grounding_ms={record.timings.grounding_ms} total_ms={record.timings.total_ms} "
        f"error={record.error}"
    )


__all__ = [
    "RAW_TEXT_MAX_CHARS",
    "GroundingLookups",
    "LookupsSource",
    "PerClusterShadowRecord",
    "ShadowChoice",
    "ShadowDeadlineExceededError",
    "ShadowM2",
    "ShadowOption",
    "ShadowSlot",
    "ShadowStatus",
    "ShadowTimings",
    "attach_shadow_block",
    "compute_per_cluster_shadow",
    "format_per_cluster_log",
    "live_probe_inputs",
    "pending_block",
    "skipped_record",
]
