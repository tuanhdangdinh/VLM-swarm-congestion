"""M5 stage-2 retreat selection: candidates, the second VLM call, degradation (no rclpy).

Rev-8 Appendix A.3. For a yield grounded in derived mode, M5 resolves the
grounded yielder and its validated retreat candidates exactly as the grounder
will, asks the VLM for one letter, and hands the parsed answer to grounding.
Stage 2 never blocks resolution: every failure, including an unexpected
exception here, degrades to `retreat_choice=None`, which the grounder turns
into the geometry-max candidate with a `retreat=default:*` tag.

Letters are counterbalanced (amendments item 22). M3 labels candidates in
generation order and breaks ranking ties on that label, so its label "A" is
the geometry-max default in every symmetric scene. The letters the VLM sees
are therefore a seeded permutation of those labels, drawn per call; the
answer is mapped back to M3's label before grounding, so the grounder is
unchanged and resolves the candidate that was shown under the chosen letter.

The listing order is randomized too (amendments item 26). With letters listed
in letter order, letter A always sat in the first-listed slot, so a first-slot
prior read as a letter-A prior. The prompt now lists the letters in a second,
independently seeded permutation, decoupling letter, listing slot and
geometry rank three ways.
"""
from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Sequence
from typing import Protocol

from reasoning.rag.command_grounder import (
    YieldFeasibilityMode,
    filter_escort_park_candidates,
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
from swarm_orchestrator.stage2_marks import CandidateMarker, Stage2Marks


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
        f"choice={choice} default_letter={record.default_letter} "
        f"listing={''.join(record.listing_order or []) or '-'} "
        f"grounded_label={record.grounded_label} default={record.default_label} "
        f"candidates={labels} "
        f"marks_drawn={record.marks_drawn} attempts={attempts} error={record.error}"
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_letter_seed(base_seed: int, draw_index: int) -> int:
    """Derive the seed of one stage-2 letter draw.

    Follows `derive_order_seed`: SHA-256, never `hash()`, so paired runs
    sharing a base seed draw the same letters for their n-th stage-2 call.
    The `stage2` salt keeps this stream independent of the presentation-order
    stream drawn from the same base seed.

    Args:
        base_seed: The run's seed (M5's presentation-order seed).
        draw_index: Zero-based index of the stage-2 draw within the M5 process.

    Returns:
        A 64-bit seed.
    """
    digest = hashlib.sha256(f"{base_seed}:stage2:{draw_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def derive_listing_seed(base_seed: int, draw_index: int) -> int:
    """Derive the seed of one stage-2 listing-order draw.

    The letter draw's scheme under its own `stage2list` salt, so for the same
    base seed and draw index the listing order is independent of the letters.

    Args:
        base_seed: The run's seed (the letter draw's `letter_seed_base`).
        draw_index: The letter draw's `letter_draw_index`.

    Returns:
        A 64-bit seed.
    """
    digest = hashlib.sha256(f"{base_seed}:stage2list:{draw_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def draw_listing_order(letters: Sequence[str], seed: int) -> list[str]:
    """Draw the order the stage-2 prompt lists the letters in.

    Args:
        letters: The shown letters, in any order.
        seed: The draw's seed (`derive_listing_seed`).

    Returns:
        The letters as a uniform random permutation of their sorted order, so
        each letter lands in each listing slot equally often.
    """
    order = sorted(letters)
    random.Random(seed).shuffle(order)
    return order


def assign_letters(candidate_count: int, seed: int) -> list[int]:
    """Draw which ranked candidate each letter shows.

    Args:
        candidate_count: Number of ranked candidates.
        seed: The draw's seed (`derive_letter_seed`).

    Returns:
        `order` with `order[i]` the ranked index shown under the i-th letter
        (A, B, ... in order); a uniform random permutation, so the
        geometry-max candidate (rank 0) lands on each letter equally often.
    """
    order = list(range(candidate_count))
    random.Random(seed).shuffle(order)
    return order


def _render_marks(
    marker: CandidateMarker | None,
    request_id: str,
    image_path: str,
    letters: Sequence[tuple[str, float, float]],
) -> Stage2Marks:
    reason = "marker_unavailable: no calibration wired"
    if marker is not None:
        try:
            return marker.render(request_id, image_path, letters)
        except Exception as exc:  # the drawing must never cost the stage-2 call
            reason = f"render_error: {type(exc).__name__}: {exc}"
    return Stage2Marks(
        marks_drawn=False, reason=reason, source_image_path=image_path, image_path=image_path
    )


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
    marker: CandidateMarker | None = None,
    letter_seed_base: int = 0,
    letter_draw_index: int = 0,
    goal_references: Mapping[str, tuple[float, float]] | None = None,
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
        marker: Draws the candidate letters on the stage-1 frame; None, or
            any drawing failure, sends that frame unmarked (`marks_drawn`
            false, with the reason in `marks`).
        letter_seed_base: The run seed the letter draw derives from.
        letter_draw_index: This draw's index within the M5 process.
        goal_references: Robot id -> current task node, as handed to the
            grounder; read only by the A28(ii) escort/park candidate filter
            (`filter_escort_park_candidates`), so the letters match.

    Returns:
        The choice to ground, in M3's labels (None grounds the default), and
        the artifact record.
    """
    try:
        return _run(
            request, decision, frame, params, caller, enabled,
            geometry, static_obstacles, yield_feasibility_mode, marker,
            letter_seed_base, letter_draw_index, goal_references,
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
    marker: CandidateMarker | None,
    letter_seed_base: int,
    letter_draw_index: int,
    goal_references: Mapping[str, tuple[float, float]] | None,
) -> tuple[RetreatChoiceDecision | None, RetreatStage2Record]:
    roles = resolve_yield_roles(
        decision,
        frame,
        geometry=geometry,
        static_obstacles=static_obstacles,
        yield_feasibility_mode=yield_feasibility_mode,
        params=params,
    )
    if roles.refusal_reason is not None:
        return None, RetreatStage2Record(
            status="skipped",
            skip_reason="yield_refused",
            yielder_id=roles.yielder_id,
            crossing_order=list(roles.crossing_order),
        )
    selection = prepare_retreat_selection(
        frame,
        roles.yielder_id,
        roles.crossing_order,
        params,
        geometry=geometry,
        static_obstacles=static_obstacles,
    )
    selection = filter_escort_park_candidates(
        selection, frame, params, geometry=geometry, goal_references=goal_references
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

    letter_seed = derive_letter_seed(letter_seed_base, letter_draw_index)
    order = assign_letters(len(candidates), letter_seed)
    # The shown letters are M3's own label set (A.. contiguous), so a letter
    # outside it is outside both and still grounds as `invalid_label`.
    letters = sorted(c.label for c in candidates)
    shown = {letter: candidates[rank] for letter, rank in zip(letters, order, strict=True)}
    default_letter = letters[order.index(0)]
    listing_seed = derive_listing_seed(letter_seed_base, letter_draw_index)
    listing_order = draw_listing_order(letters, listing_seed)
    lettered = {
        "candidates": [
            {**c.model_dump(mode="json"), "letter": letters[order.index(rank)]}
            for rank, c in enumerate(candidates)
        ],
        "default_letter": default_letter,
        "letter_seed_base": letter_seed_base,
        "letter_draw_index": letter_draw_index,
        "letter_seed": letter_seed,
        "letter_assignment": {
            letter: {
                "candidate_label": candidates[rank].label,
                "rank": rank,
                "x": candidates[rank].x,
                "y": candidates[rank].y,
            }
            for letter, rank in zip(letters, order, strict=True)
        },
        "listing_order": listing_order,
        "listing_seed": listing_seed,
    }
    marks = _render_marks(
        marker, request.request_id, request.image_path,
        [(letter, c.x, c.y) for letter, c in shown.items()],
    )
    choice_request = RetreatChoiceRequest(
        request_id=request.request_id,
        image_path=marks.image_path,
        marks_drawn=marks.marks_drawn,
        yielder_id=selection.yielder_id,
        crossing_order=list(selection.crossing_order),
        robot_states=list(frame.robots),
        candidates=[
            RetreatCandidateOption(
                label=letter, x=c.x, y=c.y, backup_m=c.backup_m, lateral_m=c.lateral_m
            )
            for letter, c in shown.items()
        ],
        listing_order=listing_order,
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
    grounded = result.choice
    if grounded is not None and grounded.retreat_choice in shown:
        grounded = grounded.model_copy(
            update={"retreat_choice": shown[grounded.retreat_choice].label}
        )
    return grounded, RetreatStage2Record(
        status="answered" if answered else "degraded",
        stage2_prompt_version=choice_request.prompt_version,
        prompt=prompt,
        response=result.model_dump(mode="json"),
        choice=None if result.choice is None else result.choice.model_dump(mode="json"),
        grounded_label=None if grounded is None else grounded.retreat_choice,
        failure_cause=result.failure_cause,
        marks_drawn=marks.marks_drawn,
        marks=marks.model_dump(mode="json"),
        **{**base, **lettered},
    )
