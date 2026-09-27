"""M5 stage-2 retreat selection: candidates, the second VLM call, degradation (no rclpy).

Rev-8 Appendix A.3. For a yield grounded in derived mode, M5 resolves the
grounded yielder and its validated retreat candidates exactly as the grounder
will, asks the VLM for one letter, and hands the parsed answer to grounding.
Stage 2 never blocks resolution: every failure, including an unexpected
exception here, degrades to `retreat_choice=None`, which the grounder turns
into the geometry-max candidate with a `retreat=default:*` tag.
"""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Protocol

from reasoning.rag.command_grounder import (
    YieldFeasibilityMode,
    prepare_retreat_selection,
    resolve_yield_roles,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerRequest,
    RetreatCandidateOption,
    RetreatChoiceDecision,
    RetreatChoiceRequest,
    RetreatChoiceResult,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload
from swarm_orchestrator.models import RetreatStage2Record


class RetreatChoiceCaller(Protocol):
    """The stage-2 VLM call (`reasoning.vlm.RetreatChooser`)."""

    def choose(self, request: RetreatChoiceRequest) -> RetreatChoiceResult: ...


def snapshot_frame_from_request(request: ReasonerRequest) -> SnapshotFrame:
    """Project the analysed scene back out of the stage-1 request.

    M5 builds the request from the analysis snapshot with registry goals and
    tasks attached (`build_reasoner_request`), so its robot states are that
    scene verbatim. Stage 2 and grounding both take this one frame: the
    candidate letters are positional, so the two must see the same poses.

    Args:
        request: The stage-1 request of this analysis.

    Returns:
        The frame, stamped with the scene stamp.
    """
    return SnapshotFrame(stamp=request.stamp, robots=list(request.robot_states))


def format_stage2_log(request_id: str, record: RetreatStage2Record) -> str:
    """One key-value log line summarizing a stage-2 record.

    Args:
        request_id: The analysis the record belongs to.
        record: The stage-2 record of that analysis.

    Returns:
        The log line (no prompt text, no image data).
    """
    choice = None if record.choice is None else record.choice.get("retreat_choice")
    attempts = None if record.response is None else record.response.get("attempts")
    labels = ",".join(str(c.get("label")) for c in record.candidates) or "-"
    return (
        f"stage2 request={request_id} status={record.status} "
        f"skip_reason={record.skip_reason} failure_cause={record.failure_cause} "
        f"choice={choice} default={record.default_label} candidates={labels} "
        f"attempts={attempts} error={record.error}"
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_retreat_stage2(
    request: ReasonerRequest,
    decision: CongestionDecision,
    frame: SnapshotFrame,
    params: GroundingParams,
    caller: RetreatChoiceCaller | None,
    *,
    enabled: bool = True,
    geometry: SceneGeometry | None = None,
    static_obstacles: Sequence[StaticObstacleInput] = (),
    yield_feasibility_mode: YieldFeasibilityMode = "off",
) -> tuple[RetreatChoiceDecision | None, RetreatStage2Record]:
    """Run stage 2 for one yield decision; never raises.

    The grounder's own inputs (frame, params, geometry, obstacles, gate mode,
    the decision's crossing order) must be passed unchanged, so the
    candidates offered here are the ones grounding resolves the letter
    against.

    Args:
        request: The stage-1 request (for its id and decision frame image).
        decision: The stage-1 decision, with `strategy == "yield"`.
        frame: The analysed scene (`snapshot_frame_from_request`).
        params: Derived-mode grounding parameters.
        caller: The stage-2 VLM caller, or None when no backend can answer
            (a mock without a stage-2 script).
        enabled: M5's `stage2_retreat_selection` switch.
        geometry: Declared scene geometry, as handed to the grounder.
        static_obstacles: Declared obstacles, as handed to the grounder.
        yield_feasibility_mode: The yield gate mode, as handed to the grounder.

    Returns:
        The choice to ground (None grounds the default) and the artifact
        record.
    """
    try:
        return _run(
            request, decision, frame, params, caller, enabled,
            geometry, static_obstacles, yield_feasibility_mode,
        )
    except Exception as exc:  # stage 2 must never stall or fail the cycle
        return None, RetreatStage2Record(
            status="degraded", error=f"{type(exc).__name__}: {exc}"
        )


def _run(
    request: ReasonerRequest,
    decision: CongestionDecision,
    frame: SnapshotFrame,
    params: GroundingParams,
    caller: RetreatChoiceCaller | None,
    enabled: bool,
    geometry: SceneGeometry | None,
    static_obstacles: Sequence[StaticObstacleInput],
    yield_feasibility_mode: YieldFeasibilityMode,
) -> tuple[RetreatChoiceDecision | None, RetreatStage2Record]:
    roles = resolve_yield_roles(
        decision,
        frame,
        geometry=geometry,
        static_obstacles=static_obstacles,
        yield_feasibility_mode=yield_feasibility_mode,
    )
    if roles.refusal_reason is not None:
        return None, RetreatStage2Record(
            status="skipped",
            skip_reason="yield_refused",
            yielder_id=roles.yielder_id,
            crossing_order=list(roles.crossing_order),
        )
    selection = prepare_retreat_selection(
        frame, roles.yielder_id, roles.crossing_order, params, geometry=geometry
    )
    candidates = selection.candidates
    base = {
        "yielder_id": selection.yielder_id,
        "crossing_order": list(selection.crossing_order),
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        "default_label": candidates[0].label if candidates else None,
    }
    if not candidates:
        return None, RetreatStage2Record(status="skipped", skip_reason="no_candidates", **base)
    if len(candidates) < 2:
        # Nothing to choose between: the one candidate is the default anyway.
        return None, RetreatStage2Record(
            status="skipped", skip_reason="single_candidate", **base
        )
    if not enabled:
        return None, RetreatStage2Record(status="skipped", skip_reason="disabled", **base)
    if caller is None:
        return None, RetreatStage2Record(status="skipped", skip_reason="no_backend", **base)

    choice_request = RetreatChoiceRequest(
        request_id=request.request_id,
        image_path=request.image_path,
        yielder_id=selection.yielder_id,
        crossing_order=list(selection.crossing_order),
        robot_states=list(frame.robots),
        candidates=[
            RetreatCandidateOption(
                label=c.label, x=c.x, y=c.y, backup_m=c.backup_m, lateral_m=c.lateral_m
            )
            for c in candidates
        ],
    )
    payload = build_stage2_prompt_payload(choice_request)
    prompt = {
        "system_prompt": payload.system_prompt,
        "user_prompt": payload.user_prompt,
        "system_sha256": _sha256(payload.system_prompt),
        "user_sha256": _sha256(payload.user_prompt),
        "image_path": payload.image_path,
    }
    result = caller.choose(choice_request)
    answered = result.choice is not None and result.failure_cause is None
    return result.choice, RetreatStage2Record(
        status="answered" if answered else "degraded",
        stage2_prompt_version=choice_request.prompt_version,
        prompt=prompt,
        response=result.model_dump(mode="json"),
        choice=None if result.choice is None else result.choice.model_dump(mode="json"),
        failure_cause=result.failure_cause,
        **base,
    )
