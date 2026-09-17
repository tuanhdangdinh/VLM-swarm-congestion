"""M5 reasoning pipeline adapter, frame dump, request build, and fan-out (no rclpy)."""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from reasoning.rag.command_grounder import (
    filter_command_robot_ids,
    validate_coordination_command,
)
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    FailureContext,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
)
from swarm_orchestrator.command_lifecycle import AttemptRecord
from swarm_orchestrator.models import (
    PipelineOutcome,
    SceneSnapshot,
    TerminalStage,
)

ValidateFn = Callable[[dict[str, Any]], dict[str, Any]]


class GroundFn(Protocol):
    """M3 grounding callable: a reasoner result plus scene context -> command."""

    def __call__(
        self,
        result: ReasonerResult,
        robot_positions: dict[str, tuple[float, float]] | None = None,
        geometry: SceneGeometry | None = None,
    ) -> dict[str, Any]: ...


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
) -> ReasonerRequest:
    """Project a SceneSnapshot plus a dumped image path into a ReasonerRequest."""
    robot_states = [
        RobotStateInput(
            robot_id=r.robot_id,
            x=r.x,
            y=r.y,
            theta=r.theta,
            linear_velocity=r.linear_velocity,
            status=r.status,
            goal=r.goal if hasattr(r, "goal") else None,
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
    )


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


def write_decision_artifact(
    output_dir: str | Path,
    outcome: PipelineOutcome,
    failure_context: FailureContext | None = None,
) -> Path:
    """Persist one M2 decision outcome for capstone acceptance evidence.

    The artifact is intentionally written before dispatch handling in the ROS node,
    so it captures the M2 result even when M3 grounding terminates the cycle.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    result = outcome.reasoner_result
    payload = {
        "request_id": outcome.request_id,
        "terminal_stage": outcome.terminal_stage.value,
        "failure_reason": outcome.failure_reason,
        "grounded_command_present": outcome.grounded_command is not None,
        "decision": (
            None if result.decision is None else result.decision.model_dump(mode="json")
        ),
        "diagnostics": result.diagnostics.model_dump(mode="json"),
        "raw_text": result.raw_text,
        "failure_context": (
            None if failure_context is None else failure_context.model_dump(mode="json")
        ),
    }
    artifact_path = output_path / f"{outcome.request_id}.json"
    artifact_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return artifact_path


class ReasoningPipeline(Protocol):
    """Backend/transport-agnostic M2->M3 pipeline."""

    def run(self, request: ReasonerRequest) -> PipelineOutcome: ...


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
    ) -> None:
        self._reasoner = reasoner
        self._ground_fn = ground_fn
        # Declared scenario geometry from M5 config; None leaves M3 on its
        # hand-sized fallback distances.
        self._scene_geometry = scene_geometry
        # Default to the M3 schema validator (FR5.3.2 / spec §5: grounded commands
        # are schema-validated before they can reach OK and be dispatched).
        self._validate_fn = validate_fn or validate_coordination_command

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
        try:
            allowed_robot_ids = {robot.robot_id for robot in request.robot_states}
            # M3 grounds the yield distances from where the robots actually are
            # plus the declared scene, so hand it this cycle's snapshot
            # positions (the request carries them verbatim from
            # SceneSnapshot.robots) and the configured geometry.
            positions = {robot.robot_id: (robot.x, robot.y) for robot in request.robot_states}
            grounded = filter_command_robot_ids(
                self._ground_fn(
                    result, robot_positions=positions, geometry=self._scene_geometry
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
            )
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=result,
            grounded_command=grounded,
            terminal_stage=TerminalStage.OK,
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
