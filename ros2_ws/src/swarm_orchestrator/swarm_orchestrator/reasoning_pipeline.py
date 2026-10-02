"""M5 reasoning pipeline adapter, frame dump, request build, and fan-out (no rclpy)."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple, Protocol

import cv2
import numpy as np
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

from reasoning.rag.command_grounder import (
    CommandGroundingError,
    JunctionClearPhasePlan,
    PlanRepairParams,
    YieldFeasibilityMode,
    filter_command_robot_ids,
    ground_junction_clear_phases,
    plan_matches_dispatch,
    resolve_strategy_alias,
    validate_coordination_command,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CURRENT_PROMPT_VERSION,
    FailureContext,
    PlanStateContext,
    PromptVersion,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotOrder,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from swarm_orchestrator.command_lifecycle import AttemptContexts, AttemptRecord
from swarm_orchestrator.models import (
    PipelineOutcome,
    PlanDispatchInfo,
    RetreatStage2Record,
    SceneSnapshot,
    TerminalStage,
)
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.presentation_order import RobotPresentationOrderMode
from swarm_orchestrator.retreat_stage2 import (
    RetreatChoiceCaller,
    run_retreat_stage2,
    snapshot_frame_from_request,
)
from swarm_orchestrator.stage2_marks import CandidateMarker

ValidateFn = Callable[[dict[str, Any]], dict[str, Any]]


class GroundFn(Protocol):
    """M3 grounding callable: a reasoner result plus scene context -> command.

    Mirrors `ground_reasoner_result`. The keyword-only arguments drive derived
    mode and are ignored in legacy mode; `crossing_order` is not passed, so
    the grounder reads it off the decision. `priorities` is passed only when
    the scene declares a non-zero registry priority, so every other call is
    the call made before the field existed.
    """

    def __call__(
        self,
        result: ReasonerResult,
        robot_positions: dict[str, tuple[float, float]] | None = None,
        geometry: SceneGeometry | None = None,
        static_obstacles: Sequence[StaticObstacleInput] = (),
        yield_feasibility_mode: YieldFeasibilityMode = "off",
        *,
        snapshot: SnapshotFrame | None = None,
        params: GroundingParams | None = None,
        retreat_choice: RetreatChoiceDecision | None = None,
        priorities: Mapping[str, int] | None = None,
    ) -> dict[str, Any]: ...


class GroundingParamsSource(BaseModel):
    """The M3 grounding parameters M5 runs on, and where they came from."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    # False when the file has no `grounding:` section, which silently means
    # the legacy defaults; recorded so that case is visible in every artifact.
    section_present: bool
    params: GroundingParams
    # The per-scenario retreat band from orchestrator.yaml, when one replaced
    # the file's `aisle_y_band_m` in `params`; None when the file's value (or
    # its default) is in force.
    aisle_y_band_override_m: tuple[float, float] | None = None
    # The per-scenario world x band for yielders retreating along y, when one
    # was set; omitted from the dump when None so artifacts of every scene
    # without it are unchanged.
    aisle_x_band_override_m: tuple[float, float] | None = None

    @model_serializer(mode="wrap")
    def _omit_unset_x_band(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data = handler(self)
        if data.get("aisle_x_band_override_m") is None:
            data.pop("aisle_x_band_override_m", None)
        return data


def load_grounding_source(path: Path) -> GroundingParamsSource:
    """Load M3's grounding parameters once at M5 startup; fail fast on any fault.

    Unlike the Arm B shadow's thresholds, these drive what M5 dispatches, so
    a missing file stops M5 instead of falling back to a default mode.

    Args:
        path: The RAG config (`config/rag.yaml`), relative to M5's cwd.

    Returns:
        The params with their provenance; an absent section gives the
        defaults (`mode="legacy"`) with `section_present=False`.

    Raises:
        FileNotFoundError: If `path` does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        ValueError: If the file is not a YAML mapping.
        pydantic.ValidationError: If the section has unknown keys or
            out-of-range values.
    """
    if not path.is_file():
        raise FileNotFoundError(f"grounding params file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a YAML mapping, got {type(raw).__name__}")
    section = raw.get("grounding")
    return GroundingParamsSource(
        path=str(path),
        section_present=bool(section),
        params=GroundingParams(**(section or {})),
    )


def apply_aisle_y_band_override(
    source: GroundingParamsSource, band_m: tuple[float, float] | None
) -> GroundingParamsSource:
    """Replace the retreat-candidate aisle band with a per-scenario one.

    The band is scenario geometry, like `scenario_geometry`, so it is declared
    per scenario in orchestrator.yaml rather than in the shared RAG config.
    Applied once at startup, before the pipeline and the Arm B shadow are
    built, so both rank candidates from the same params.

    Args:
        source: The params loaded by `load_grounding_source`.
        band_m: World-frame `(low, high)` y band, or None to keep `source`.

    Returns:
        `source` unchanged for None; otherwise a copy whose params carry the
        band, with the override recorded.

    Raises:
        pydantic.ValidationError: If the band's lower bound exceeds its upper
            bound.
    """
    if band_m is None:
        return source
    params = GroundingParams(**{**source.params.model_dump(), "aisle_y_band_m": band_m})
    return source.model_copy(update={"params": params, "aisle_y_band_override_m": band_m})


def apply_aisle_x_band_override(
    source: GroundingParamsSource, band_m: tuple[float, float] | None
) -> GroundingParamsSource:
    """Set the world x band that bounds a y-axis yielder's retreat candidates.

    The x counterpart of `apply_aisle_y_band_override`, for a yielder whose
    declared junction arm runs along y (B1's north-arm merge yielder); every
    other yielder ignores it.

    Args:
        source: The params, possibly already carrying a y-band override.
        band_m: World-frame `(low, high)` x band, or None to keep `source`.

    Returns:
        `source` unchanged for None; otherwise a copy whose params carry the
        band, with the override recorded.

    Raises:
        pydantic.ValidationError: If the band's lower bound exceeds its upper
            bound.
    """
    if band_m is None:
        return source
    params = GroundingParams(**{**source.params.model_dump(), "aisle_x_band_m": band_m})
    return source.model_copy(update={"params": params, "aisle_x_band_override_m": band_m})


def build_failed_outcome(request_id: str, reason: str) -> PipelineOutcome:
    """Build a VLM-terminal outcome with a synthetic failed ReasonerResult.

    Used when no real `ReasonerResult` is available — e.g. the reasoner call or the
    worker-thread frame dump raised before producing one. Keeps the contract that a
    cycle always resolves to a `PipelineOutcome` (FR5.3.2).
    """
    result = ReasonerResult(
        request_id=request_id,
        decision=None,
        raw_text=None,
        diagnostics=ReasonerDiagnostics(
            request_id=request_id,
            backend_id="unknown",
            attempts=1,
            parse_status="failed",
            error_message=reason,
        ),
    )
    return PipelineOutcome(
        request_id=request_id,
        reasoner_result=result,
        grounded_command=None,
        terminal_stage=TerminalStage.VLM,
        failure_reason=reason,
    )


def build_reasoner_request(
    request_id: str,
    snapshot: SceneSnapshot,
    image_path: str,
    failure_context: FailureContext | None = None,
    include_pairwise_geometry: bool = True,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    include_static_obstacles: bool = False,
    robot_presentation_order: RobotOrder = "id_asc",
    last_failed_context: FailureContext | None = None,
    prompt_version: PromptVersion = CURRENT_PROMPT_VERSION,
    plan_state: PlanStateContext | None = None,
) -> ReasonerRequest:
    """Project a SceneSnapshot plus a dumped image path into a ReasonerRequest.

    Each robot's goal and task label come from its `RobotView`, which M5 fills
    from the task registry (`attach_registry_assignments`) before calling this;
    a snapshot straight from M1, or one stored before the prompt-v2 bundle,
    carries neither and renders without them.

    Args:
        request_id: Identifier of the analysis cycle.
        snapshot: The M1 scene, registry assignments attached.
        image_path: Path of the dumped frame the VLM will see.
        failure_context: Most recent resolved attempt, if any.
        include_pairwise_geometry: Pairwise-geometry modality switch.
        static_obstacles: Declared fixed obstacles.
        include_static_obstacles: Static-obstacle modality switch.
        robot_presentation_order: Order the prompt lists robots in.
        last_failed_context: Most recent failed attempt when it is not the
            attempt in `failure_context`.
        prompt_version: Prompt template to render; replay passes a stored
            artifact's version so its prompt reconstructs byte-identically.
        plan_state: The (a0) plan channel's active plan for the prompt-v3
            plan-state block; None (the default) renders byte-identically to
            every request built before plan tracking existed. Only the v3
            template reads it.

    Returns:
        The request M2 is called with.
    """
    robot_states = [
        RobotStateInput(
            robot_id=r.robot_id,
            x=r.x,
            y=r.y,
            theta=r.theta,
            linear_velocity=r.linear_velocity,
            status=r.status,
            task=r.task,
            goal=r.goal,
        )
        for r in snapshot.robots
    ]
    return ReasonerRequest(
        request_id=request_id,
        image_path=image_path,
        frame_id=snapshot.frame_id,
        stamp=snapshot.stamp,
        robot_states=robot_states,
        failure_context=failure_context,
        last_failed_context=last_failed_context,
        include_pairwise_geometry=include_pairwise_geometry,
        static_obstacles=list(static_obstacles),
        include_static_obstacles=include_static_obstacles,
        robot_presentation_order=robot_presentation_order,
        prompt_version=prompt_version,
        plan_state=plan_state,
    )


def attach_registry_assignments(
    snapshot: SceneSnapshot,
    goal_of: Callable[[str], tuple[float, float] | None],
    task_of: Callable[[str], str | None],
) -> SceneSnapshot:
    """Copy a scene with each robot's registry goal and task label attached.

    M5's task registry is the goal source (the same lookup the Arm B shadow
    uses), so Arm A's prompt and Arm B's rules see the same goals.

    Args:
        snapshot: The M1 scene as M5 received it.
        goal_of: A robot's effective goal, or None when it has no assignment.
        task_of: A robot's mission task label, or None when it has none.

    Returns:
        A new snapshot; the input is left untouched.
    """
    robots = [
        view.model_copy(update={"goal": goal_of(view.robot_id), "task": task_of(view.robot_id)})
        for view in snapshot.robots
    ]
    return snapshot.model_copy(update={"robots": robots})


def build_failure_context(record: AttemptRecord, now: float) -> FailureContext:
    """Project M5's last resolved attempt into the M2 previous-attempt block (rev-8 A.1).

    Args:
        record: A resolved `AttemptRecord` from `AttemptMemory.context_for`.
        now: Monotonic time of the new analysis, for the elapsed-seconds wording.

    Returns:
        A `FailureContext` whose `failure_detail` follows the spec wording.
    """
    resolved_at = record.resolved_at if record.resolved_at is not None else now
    status = record.outcome_status if record.outcome_status is not None else "unknown"
    if status == "completed":
        attempt = f"{record.strategy} completed {now - resolved_at:.0f} s ago"
    else:
        attempt = f"{record.strategy} {status} after {resolved_at - record.dispatched_at:.0f} s"
    # M3 may degrade a strategy (a refused yield runs as temporary_wait); tell the
    # VLM what actually ran so it does not reason about a maneuver that never happened.
    if record.executed_strategy is not None and record.executed_strategy != record.strategy:
        attempt += f" (executed as {record.executed_strategy})"
    detail = f"{attempt}; congestion re-detected for the same robots"
    return FailureContext(
        strategy=record.strategy,
        yield_robot=record.yield_robot,
        outcome_status=status,
        failure_detail=detail,
    )


def build_failure_contexts(
    contexts: AttemptContexts, now: float
) -> tuple[FailureContext | None, FailureContext | None]:
    """Project M5's remembered attempts into the two M2 failure-context blocks.

    Args:
        contexts: The latest and last-failed attempts from `AttemptMemory.contexts_for`.
        now: Monotonic time of the new analysis, for the elapsed-seconds wording.

    Returns:
        `(failure_context, last_failed_context)`, each None when the matching
        attempt is absent.
    """
    latest = None if contexts.latest is None else build_failure_context(contexts.latest, now)
    last_failed = (
        None
        if contexts.last_failed is None
        else build_failure_context(contexts.last_failed, now)
    )
    return latest, last_failed


def dump_frame_png(frame_rgb: np.ndarray, dest_path: str, downscale_width: int | None) -> None:
    """Write an RGB frame to disk as PNG for the VLM backend.

    The M1 boundary is RGB; OpenCV writes BGR, so we convert at this boundary
    (annotation status colors are semantic — a swapped-channel dump corrupts what
    M2 reads). Optionally downscale to `downscale_width`, preserving aspect ratio.

    Args:
        frame_rgb: RGB image array `(H, W, 3)`.
        dest_path: Destination PNG path.
        downscale_width: Target width in pixels, or None for full resolution.
    """
    image = frame_rgb
    if downscale_width is not None and image.shape[1] > downscale_width:
        scale = downscale_width / image.shape[1]
        new_size = (downscale_width, max(1, round(image.shape[0] * scale)))
        image = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(dest_path, bgr)


def raw_frame_dump_path(frame_dump_dir: str | Path, request_id: str) -> Path:
    """Return where the raw camera frame for one analysis is dumped.

    Sits beside the annotated dump (`<request_id>.png`) so the two frames of one
    instant are found together.

    Args:
        frame_dump_dir: Directory the annotated frame is dumped into.
        request_id: Identifier of the analysis cycle.

    Returns:
        The `<frame_dump_dir>/<request_id>_raw.png` path.
    """
    return Path(frame_dump_dir) / f"{request_id}_raw.png"


def raw_frame_skew_sec(raw_stamp: float, annotated_stamp: float) -> float:
    """Signed stamp skew of the raw frame against the annotated one, in seconds.

    Positive means the raw frame is the newer of the two. The sign is the point:
    an annotated-vs-raw comparison is only fair if the two frames show the same
    instant, and the direction says which one leads.

    Args:
        raw_stamp: Stamp of the buffered raw camera frame.
        annotated_stamp: Stamp of the annotated frame sent to M2.

    Returns:
        `raw_stamp - annotated_stamp`.
    """
    return raw_stamp - annotated_stamp


class LatestRawFrame:
    """Single-slot holder for the newest raw camera frame (no queue, best effort).

    The raw frame is debug evidence, never pipeline input: only the most recent
    one is kept, and an older frame arriving late simply replaces it — nothing
    reorders or backfills, matching the best-effort, depth-1 subscription.
    """

    def __init__(self) -> None:
        self._frame: np.ndarray | None = None
        self._stamp: float | None = None

    def update(self, frame_rgb: np.ndarray, stamp: float) -> None:
        """Replace the held frame with a newly received one.

        Args:
            frame_rgb: RGB image array `(H, W, 3)`.
            stamp: The frame's header stamp in seconds.
        """
        self._frame = frame_rgb
        self._stamp = stamp

    def latest(self) -> tuple[np.ndarray, float] | None:
        """Return the held `(frame_rgb, stamp)`, or None if none has arrived."""
        if self._frame is None or self._stamp is None:
            return None
        return self._frame, self._stamp


def _attach_plan_id(grounded: dict[str, Any], plan_id: int) -> dict[str, Any]:
    """Tag every dispatched action with the (a0) plan it serves.

    "Dispatched commands carry the `plan_id` they serve" (prereg-v2 rev 4,
    "Plan lifecycle"). `parameters` is an unconstrained object in the
    coordination-command schema (`reasoning/schemas/coordination_command.schema.json`),
    already used this way for a reroute's injected `goal` -- so this needs no
    schema change and M4's per-action handlers, which read known keys by name
    and ignore the rest, are unaffected by the new one. Only called behind
    `plan_channel_enabled`; the flag-off path never calls this.

    Args:
        grounded: A schema-valid grounded command (post `validate_fn`).
        plan_id: The plan id this command's actions serve.

    Returns:
        A new command dict with `plan_id` added to every action's parameters;
        `grounded` itself is left untouched.
    """
    return {
        **grounded,
        "actions": [
            {**action, "parameters": {**action.get("parameters", {}), "plan_id": plan_id}}
            for action in grounded["actions"]
        ],
    }


def fan_out_command(
    grounded: dict[str, Any], fallback_timeout: float
) -> list[tuple[str, str, str, str, float]]:
    """Expand a grounded command into per-robot (id, robot, action, params, timeout) tuples.

    Mapping per spec §9.2. `parameters` serialize with sorted keys; an absent or
    zero `expected_resolution_time_sec` falls back to `fallback_timeout`.
    """
    command_id = grounded["command_id"]
    resolution = grounded.get("expected_resolution_time_sec") or 0
    timeout = float(resolution) if resolution else fallback_timeout
    messages: list[tuple[str, str, str, str, float]] = []
    for action in grounded["actions"]:
        params_json = json.dumps(action.get("parameters", {}), sort_keys=True)
        messages.append(
            (command_id, action["robot_id"], action["action"], params_json, timeout)
        )
    return messages


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class YieldGroundingProvenance(NamedTuple):
    """Where a grounded yield ended up, and why M3 moved or refused it."""

    grounded_from: str | None
    grounded_to: str | None
    regrounded_reason: str | None
    refusal_reason: str | None


def summarize_yield_grounding(command: dict[str, Any] | None) -> YieldGroundingProvenance:
    """Read M3's yield feasibility outcome back off a grounded command.

    The gate leaves its only trace in the command: a swap tags the yield
    action's parameters with `yield_robot_grounded_from`, while a refusal drops
    the yield action altogether and fans out `temporary_wait` actions whose
    `reason` opens with `"yield refused:"`. The prefix test is load-bearing — a
    yield that grounded normally also carries a `reason`, the M2 root cause.

    Args:
        command: The grounded coordination command, or None when grounding
            raised or its output failed schema validation.

    Returns:
        The provenance fields, all None when the feasibility gate did not fire.
    """
    if command is None:
        return YieldGroundingProvenance(None, None, None, None)
    grounded_from: str | None = None
    grounded_to: str | None = None
    regrounded_reason: str | None = None
    refusal_reason: str | None = None
    for action in command.get("actions", []):
        parameters = action.get("parameters") or {}
        if action.get("action") == "yield":
            grounded_to = action.get("robot_id")
            grounded_from = parameters.get("yield_robot_grounded_from")
            regrounded_reason = parameters.get("yield_regrounded_reason")
        reason = parameters.get("reason")
        if (
            refusal_reason is None
            and isinstance(reason, str)
            and reason.startswith("yield refused:")
        ):
            # Fanned out to every involved robot, so only the first is recorded.
            refusal_reason = reason
    return YieldGroundingProvenance(
        grounded_from, grounded_to, regrounded_reason, refusal_reason
    )


def write_decision_artifact(
    output_dir: str | Path,
    outcome: PipelineOutcome,
    failure_context: FailureContext | None = None,
    request: ReasonerRequest | None = None,
    snapshot: SceneSnapshot | None = None,
    distance_to_goal_m: dict[str, float] | None = None,
    run_id: str | None = None,
    session_id: str | None = None,
    prompt_robot_order_mode: RobotPresentationOrderMode | None = None,
    prompt_robot_order_seed: int | None = None,
    episode_index: int | None = None,
    grounding_yield_feasibility: YieldFeasibilityMode | None = None,
    last_failed_context: FailureContext | None = None,
    shadow_classical: dict[str, Any] | None = None,
    probe_index: int | None = None,
    grounding_source: GroundingParamsSource | None = None,
) -> Path:
    """Persist one M2 decision outcome for capstone acceptance evidence.

    The artifact is intentionally written before dispatch handling in the ROS node,
    so it captures the M2 result even when M3 grounding terminates the cycle. With
    `request` it also records the rendered prompt (and always
    `reasoner_config_effective`, the sampling parameters the call ran under,
    whenever the reasoner was given them — M5 always is) (re-built by the pure prompt
    builder, so the base prompt the VLM saw is reproducible; a re-ask suffix on a
    retry is not captured) with SHA-256 hashes for the pre-registration freeze,
    and with `snapshot` the M1 scene the request was built from.

    Args:
        output_dir: Directory the `<request_id>.json` file is written into.
        outcome: The pipeline outcome to record.
        failure_context: Previous-attempt block attached to this request, if any.
        request: The `ReasonerRequest` sent to M2, for prompt persistence.
        snapshot: The M1 scene snapshot the request was built from.
        distance_to_goal_m: The detector's per-robot distance at trigger time.
        run_id: Scenario run identifier (`VGU_RUN_ID`), if the launcher set one.
        session_id: Identifier of the M5 process that wrote the artifact.
        prompt_robot_order_mode: The configured presentation-order mode, which
            may be `"random"`; the effective order is read off `request`, so the
            artifact records the order actually rendered.
        prompt_robot_order_seed: The effective integer seed of the draw.
        episode_index: Zero-based congestion episode this analysis belongs to.
        grounding_yield_feasibility: The configured M3 yield feasibility mode.
            Recorded even when the gate did not fire, so an artifact set can be
            partitioned by the condition it was collected under; the gate's
            actual outcome is read off the grounded command.
        last_failed_context: Earlier-failed-attempt block attached to this
            request, if any; recorded in the same shape as `failure_context` so
            replay can rebuild the prompt.
        shadow_classical: The Arm B shadow block (`ShadowClassicalRecord`
            dumped to JSON) computed on this analysis's evidence, or None when
            the shadow is disabled. Taken as a plain dict, built before this
            call, so a shadow failure can never skip the artifact write.
        probe_index: Zero-based index of a T0 log-only probe, or None for a
            triggered analysis. A probe artifact gains `probe: true` and
            `probe_index`; a triggered one gains neither key, so its bytes
            are unchanged from before probes existed.
        grounding_source: The M3 grounding parameters M5 loaded at startup.
            Recorded as `grounding_mode` and `grounding_params_source` (null
            when absent), so an artifact set can be partitioned by the mode
            it was grounded under. The grounded command's own `degradations`
            list (derived mode only) is lifted to `grounding_degradations`,
            and a derived yield's stage-2 record to `stage2`.

    `outcome.plan` (the (a0) plan channel, behind `plan_channel_enabled`) adds
    a `plan` key with `plan_id`, `provenance`, `legs`, `edits`,
    `rejection_reason`, `superseded_plan_id`, `cancel_order` and `plan_held`
    -- only when it is not None, same conditional-add pattern as
    `probe`/`probe_index`, so a flag-off artifact is byte-identical to one
    written before this channel existed. `plan_held` (ruling 2026-10-02) is
    true exactly when this decision re-affirmed the already-active plan
    (`plan_id` is then that unchanged active plan_id, not a new one) rather
    than being accepted as a new one. `outcome.plan_error`, likewise
    conditional, records why the channel itself raised (`plan` is then None
    but the command still dispatched -- a plan-channel failure never costs an
    otherwise-successful decision).

    Returns:
        The artifact path.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    result = outcome.reasoner_result
    prompt = None
    if request is not None:
        rendered = build_prompt_payload(request)
        prompt = {
            "system_prompt": rendered.system_prompt,
            "user_prompt": rendered.user_prompt,
            "system_sha256": _sha256(rendered.system_prompt),
            "user_sha256": _sha256(rendered.user_prompt),
        }
    yield_grounding = summarize_yield_grounding(outcome.grounded_command)
    payload = {
        "request_id": outcome.request_id,
        "run_id": run_id,
        "session_id": session_id,
        "terminal_stage": outcome.terminal_stage.value,
        "failure_reason": outcome.failure_reason,
        "grounded_command_present": outcome.grounded_command is not None,
        "decision": (
            None if result.decision is None else result.decision.model_dump(mode="json")
        ),
        "diagnostics": result.diagnostics.model_dump(mode="json"),
        # Lifted out of `diagnostics` to a top-level key as well: an artifact
        # set is partitioned by the decoding parameters it was collected under,
        # so the block must be readable without walking into diagnostics.
        "reasoner_config_effective": (
            None
            if result.diagnostics.reasoner_config_effective is None
            else result.diagnostics.reasoner_config_effective.model_dump(mode="json")
        ),
        "raw_text": result.raw_text,
        "failure_context": (
            None if failure_context is None else failure_context.model_dump(mode="json")
        ),
        "last_failed_context": (
            None
            if last_failed_context is None
            else last_failed_context.model_dump(mode="json")
        ),
        "prompt": prompt,
        # Absent on every artifact written before the prompt-v2 bundle; the
        # replay reconstructor reads a missing key as v1.
        "prompt_version": None if request is None else request.prompt_version,
        "robot_presentation_order": (
            None if request is None else request.robot_presentation_order
        ),
        "prompt_robot_order_mode": prompt_robot_order_mode,
        "prompt_robot_order_seed": prompt_robot_order_seed,
        "episode_index": episode_index,
        "grounding_yield_feasibility": grounding_yield_feasibility,
        "yield_robot_grounded_from": yield_grounding.grounded_from,
        "yield_regrounded_reason": yield_grounding.regrounded_reason,
        "yield_refusal_reason": yield_grounding.refusal_reason,
        "scene": None if snapshot is None else snapshot.model_dump(mode="json"),
        "distance_to_goal_m": dict(distance_to_goal_m or {}),
        "shadow_classical": shadow_classical,
        "grounding_mode": None if grounding_source is None else grounding_source.params.mode,
        "grounding_params_source": (
            None if grounding_source is None else grounding_source.model_dump(mode="json")
        ),
        # Per-action messages never carry this list, so the artifact is the
        # only place a derived command's degradations survive.
        "grounding_degradations": (
            None
            if outcome.grounded_command is None
            else outcome.grounded_command.get("degradations")
        ),
        "stage2": None if outcome.stage2 is None else outcome.stage2.model_dump(mode="json"),
    }
    if probe_index is not None:
        payload["probe"] = True
        payload["probe_index"] = probe_index
    # (a0) plan channel (prereg-v2 rev 4): added only when plan tracking is
    # on (`outcome.plan is not None`), same conditional-add pattern as
    # `probe`/`probe_index` above, so a flag-off artifact is byte-identical
    # to one written before this channel existed -- no `"plan": null` key.
    if outcome.plan is not None:
        payload["plan"] = outcome.plan.model_dump(mode="json")
    if outcome.plan_error is not None:
        payload["plan_error"] = outcome.plan_error
    # v3's plan-state block (unlike failure_context/last_failed_context,
    # which predate flag-gating and are always-present-but-nullable keys)
    # is added only when set, so a flag-off/pre-v3 artifact's bytes are
    # unchanged. Needed for replay: the integrity arm rebuilds a
    # ReasonerRequest from stored artifact fields and re-asserts the
    # rendered prompt's SHA-256 (`scripts/replay_live_decisions.py`
    # `reconstruct_request`), and a v3 artifact's plan-state block cannot be
    # rebuilt without this.
    if request is not None and request.plan_state is not None:
        payload["plan_state"] = request.plan_state.model_dump(mode="json")
    artifact_path = output_path / f"{outcome.request_id}.json"
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return artifact_path


def append_scene_log(
    path: str | Path,
    snapshot: SceneSnapshot,
    session_id: str,
    run_id: str | None,
    now: float,
) -> None:
    """Append one M1 scene snapshot as a JSON line for offline trajectory analysis.

    Args:
        path: JSONL file (created with its parent directory if missing).
        snapshot: The scene to record.
        session_id: Identifier of the M5 process writing the log.
        run_id: Scenario run identifier, or None if the launcher set none.
        now: Monotonic time of the record.
    """
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "t": now,
        "session_id": session_id,
        "run_id": run_id,
        "scene": snapshot.model_dump(mode="json"),
    }
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


class ReasoningPipeline(Protocol):
    """Backend/transport-agnostic M2->M3 pipeline."""

    def run(self, request: ReasonerRequest) -> PipelineOutcome: ...


class Stage1Analyzer(Protocol):
    """Runs only the M2 analysis of a request, for T0 log-only probes."""

    def analyze(self, request: ReasonerRequest) -> PipelineOutcome: ...


class InProcessPipeline:
    """Default adapter: calls M2 `Reasoner.run` then M3 grounding, both in-process.

    Failures from either stage are caught and reported via `failure_reason`; they
    are never raised past this adapter (FR5.3.2, E3/E4).
    """

    def __init__(
        self,
        reasoner: Any,
        ground_fn: GroundFn,
        validate_fn: ValidateFn | None = None,
        scene_geometry: SceneGeometry | None = None,
        static_obstacles: Sequence[StaticObstacleInput] = (),
        yield_feasibility_mode: YieldFeasibilityMode = "off",
        grounding_params: GroundingParams | None = None,
        retreat_chooser: RetreatChoiceCaller | None = None,
        stage2_enabled: bool = True,
        candidate_marker: CandidateMarker | None = None,
        stage2_letter_seed: int = 0,
        priorities: Mapping[str, int] | None = None,
        plan_tracker: PlanTracker | None = None,
        plan_repair_params: PlanRepairParams | None = None,
    ) -> None:
        self._reasoner = reasoner
        # Registry priorities (`registry_priorities`), M3-only: never part of
        # the request, so the prompt cannot see them. Empty or None passes
        # nothing to M3, keeping every priority-less scene's call unchanged.
        self._priorities = dict(priorities or {})
        self._ground_fn = ground_fn
        # None grounds in legacy mode, as every caller did before derived mode
        # was wired; derived mode also enables stage 2 for yields.
        self._grounding_params = grounding_params
        # None means no backend can answer stage 2 (a mock without a stage-2
        # script); the call is skipped and recorded, never attempted.
        self._retreat_chooser = retreat_chooser
        self._stage2_enabled = stage2_enabled
        # Draws the stage-2 letters on the dumped frame; None (or a marker
        # without calibration) sends stage 2 the unmarked frame, recorded.
        self._candidate_marker = candidate_marker
        # Stage-2 letters are drawn from this run seed, one draw per derived
        # yield in call order; the worker is single-threaded, so the counter
        # needs no lock.
        self._stage2_letter_seed = stage2_letter_seed
        self._stage2_draws = 0
        # Declared scenario geometry from M5 config; None leaves M3 on its
        # hand-sized fallback distances.
        self._scene_geometry = scene_geometry
        # Read only by M3's yield feasibility gate; with no obstacles declared
        # the gate is a no-op whatever the mode says.
        self._static_obstacles = static_obstacles
        self._yield_feasibility_mode = yield_feasibility_mode
        # Default to the M3 schema validator (FR5.3.2 / spec §5: grounded commands
        # are schema-validated before they can reach OK and be dispatched).
        self._validate_fn = validate_fn or validate_coordination_command
        # (a0) plan channel (prereg-v2 rev 4, build-order step 4), behind the
        # `plan_channel_enabled` flag: None (the default, every caller before
        # this step) means `run()` never calls `verify_and_repair_plan` and
        # never touches the grounded command's parameters, so the dispatch
        # path is byte-identical to before this channel existed.
        self._plan_tracker = plan_tracker
        self._plan_repair_params = plan_repair_params

    def run(self, request: ReasonerRequest) -> PipelineOutcome:
        try:
            result = self._reasoner.run(request)
        except Exception as exc:  # unexpected M2 failure — bounded here, never raised
            return build_failed_outcome(request.request_id, f"reasoner raised: {exc}")
        decision = result.decision
        if decision is None:
            return self._vlm_terminal(request.request_id, result, "decision=None")
        if not decision.congestion_detected:
            return self._vlm_terminal(request.request_id, result, "congestion_detected=false")
        # One frame for stage 2 and grounding alike: the stage-2 letters are
        # positional, so both must resolve them against the same poses.
        frame = snapshot_frame_from_request(request)
        params = self._grounding_params
        retreat_choice: RetreatChoiceDecision | None = None
        stage2: RetreatStage2Record | None = None
        # A convoy / priority_override decision that M3 grounds as an ordered
        # yield gets the yield's stage 2 too, on the same aliased roles the
        # grounder derives again from the same frame.
        alias = resolve_strategy_alias(
            decision, frame, geometry=self._scene_geometry, priorities=self._priorities
        )
        staged = decision if alias is None else alias.decision
        if params is not None and params.mode == "derived" and staged.strategy == "yield":
            retreat_choice, stage2 = run_retreat_stage2(
                request,
                staged,
                frame,
                params,
                self._retreat_chooser,
                enabled=self._stage2_enabled,
                geometry=self._scene_geometry,
                static_obstacles=self._static_obstacles,
                yield_feasibility_mode=self._yield_feasibility_mode,
                marker=self._candidate_marker,
                letter_seed_base=self._stage2_letter_seed,
                letter_draw_index=self._stage2_draws,
            )
            self._stage2_draws += 1
        try:
            allowed_robot_ids = {robot.robot_id for robot in request.robot_states}
            # M3 grounds the yield distances from where the robots actually are
            # plus the declared scene, so hand it this cycle's snapshot
            # positions (the request carries them verbatim from
            # SceneSnapshot.robots) and the configured geometry.
            positions = {robot.robot_id: (robot.x, robot.y) for robot in request.robot_states}
            priority_kwargs: dict[str, Any] = (
                {"priorities": dict(self._priorities)} if self._priorities else {}
            )
            grounded = filter_command_robot_ids(
                self._ground_fn(
                    result,
                    robot_positions=positions,
                    geometry=self._scene_geometry,
                    static_obstacles=self._static_obstacles,
                    yield_feasibility_mode=self._yield_feasibility_mode,
                    snapshot=frame,
                    params=params,
                    retreat_choice=retreat_choice,
                    **priority_kwargs,
                ),
                allowed_robot_ids,
            )
            grounded = self._validate_fn(grounded)
        except Exception as exc:  # grounding or schema-validation failure — bounded here
            return PipelineOutcome(
                request_id=request.request_id,
                reasoner_result=result,
                grounded_command=None,
                terminal_stage=TerminalStage.GROUNDING,
                failure_reason=f"grounding failed: {exc}",
                stage2=stage2,
            )
        plan_info: PlanDispatchInfo | None = None
        plan_error: str | None = None
        junction_phases: JunctionClearPhasePlan | None = None
        if self._plan_tracker is not None:
            # A plan-channel failure must never cost an otherwise-successful
            # dispatch (the adapter's own "never raised past this adapter"
            # contract, FR5.3.2, extended to this channel): `grounded` here
            # is already the fully validated command, so on any exception it
            # is dispatched exactly as grounded, untouched by `_attach_plan_id`.
            try:
                verified = verify_and_repair_plan(
                    decision,
                    frame,
                    geometry=self._scene_geometry,
                    static_obstacles=self._static_obstacles,
                    yield_feasibility_mode=self._yield_feasibility_mode,
                    repair_params=self._plan_repair_params,
                    priorities=dict(self._priorities) if self._priorities else None,
                    grounding_params=params,
                )
                acceptance = self._plan_tracker.accept_plan(verified)
                known_robot_ids = [robot.robot_id for robot in request.robot_states]
                dispatch_matches_plan = plan_matches_dispatch(
                    verified.legs, grounded, known_robot_ids
                )
                grounded = _attach_plan_id(grounded, acceptance.plan.plan_id)
                if (
                    decision.strategy == "junction_clear"
                    and params is not None
                    and params.mode == "derived"
                    and self._scene_geometry is not None
                ):
                    # `junction_clear`'s full precomputed phase sequence
                    # (prereg-v2 (a) M5, build-order step 5), behind the
                    # SAME `plan_channel_enabled` flag `plan_info` is
                    # (`self._plan_tracker is not None`): the ONE place this
                    # pipeline seeds M5's phase queue, from the SAME
                    # snapshot/params/geometry `grounded` (phase 0 already)
                    # was computed from.
                    try:
                        junction_phases = ground_junction_clear_phases(
                            result,
                            snapshot=frame,
                            params=params,
                            geometry=self._scene_geometry,
                            static_obstacles=self._static_obstacles,
                            yield_feasibility_mode=self._yield_feasibility_mode,
                            retreat_choice=retreat_choice,
                        )
                    except CommandGroundingError:
                        # No recede candidate survives chi ranking: `grounded`
                        # above already took the SAME plain-`yield` fallback
                        # path (`_ground_derived`'s own `junction_clear`
                        # branch, same geometry), so there is nothing to
                        # queue -- one ordinary yield command, no phases.
                        junction_phases = None
                plan_info = PlanDispatchInfo(
                    plan_id=acceptance.plan.plan_id,
                    provenance=verified.provenance,
                    legs=acceptance.plan.legs,
                    dispatch_matches_plan=dispatch_matches_plan,
                    edits=tuple(verified.edits),
                    rejection_reason=verified.rejection_reason,
                    superseded_plan_id=(
                        acceptance.supersedes.superseded_plan_id
                        if acceptance.supersedes is not None
                        else None
                    ),
                    cancel_order=(
                        acceptance.supersedes.cancel_order
                        if acceptance.supersedes is not None
                        else ()
                    ),
                    plan_held=acceptance.held,
                )
            except Exception as exc:  # plan channel failure — bounded here, never raised
                plan_error = f"plan channel failed: {exc}"
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=result,
            grounded_command=grounded,
            terminal_stage=TerminalStage.OK,
            failure_reason=None,
            stage2=stage2,
            plan=plan_info,
            plan_error=plan_error,
            junction_phases=junction_phases,
        )

    def analyze(self, request: ReasonerRequest) -> PipelineOutcome:
        """Run the M2 stage only, for a T0 log-only probe; M3 is never called.

        Structurally the first no-dispatch layer: the outcome never carries a
        grounded command, whatever the decision says. A completed decision
        terminates at `PROBE`; a missing one or a raised reasoner at `VLM`,
        as in `run`.

        Args:
            request: The probe's reasoner request.

        Returns:
            The outcome with `grounded_command=None`.
        """
        try:
            result = self._reasoner.run(request)
        except Exception as exc:  # unexpected M2 failure — bounded here, never raised
            return build_failed_outcome(request.request_id, f"reasoner raised: {exc}")
        if result.decision is None:
            return self._vlm_terminal(request.request_id, result, "decision=None")
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=result,
            grounded_command=None,
            terminal_stage=TerminalStage.PROBE,
            failure_reason=None,
        )

    @staticmethod
    def _vlm_terminal(
        request_id: str, result: ReasonerResult, reason: str
    ) -> PipelineOutcome:
        return PipelineOutcome(
            request_id=request_id,
            reasoner_result=result,
            grounded_command=None,
            terminal_stage=TerminalStage.VLM,
            failure_reason=reason,
        )
