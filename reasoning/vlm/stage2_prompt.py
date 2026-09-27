"""Stage-2 retreat-choice prompt (rev-8 Appendix A.3), text-only letters.

The design has M1 draw the lettered candidates on a fresh decision frame
(set-of-mark). That rendering path does not exist yet, so this template lists
the letters with their world coordinates and says plainly that nothing is drawn
on the image, which is the stage-1 annotated frame reused as-is.

Candidates are listed in letter order, never in rank order, and without their
sweep clearances: either would leak the geometry-max answer the fallback
already supplies.
"""

from reasoning.vlm.models import PromptPayload, RetreatChoiceRequest, RobotStateInput
from reasoning.vlm.prompt_builder import SYSTEM_PROMPT

STAGE2_SYSTEM_PROMPT = SYSTEM_PROMPT

# Version 1 (CURRENT_STAGE2_PROMPT_VERSION). The objective sentence is the
# research design's A.3 wording with "marked" dropped, since no marks are drawn.
_STAGE2_USER_TEMPLATE_V1 = """You are a warehouse swarm robotics traffic controller. \
{yielder_id} will yield so that {passers} can pass: it backs up, then steps aside \
to one of the lettered retreat positions below. Every position has already been \
checked to keep a safe distance from the listed robots along the whole path.

Robots (world frame, metres):
{robot_block}

Retreat positions for {yielder_id} (world frame, metres):
{candidate_block}

The letters are not drawn on the image; locate each position from its \
coordinates. The image shows the scene as it is now, including anything not \
listed above.

Choose the retreat position that best clears the conflict while preserving the \
passage space the other robots need and avoiding visible obstacles or traffic.

Respond with ONLY a JSON object, no other text:
{{"retreat_choice": "<one of {labels}>", "justification": "<one clause>"}}"""


def _role(state: RobotStateInput, request: RetreatChoiceRequest) -> str:
    if state.robot_id == request.yielder_id:
        return " (yielding)"
    if state.robot_id in request.crossing_order:
        return " (passing)"
    return ""


def build_stage2_prompt_payload(request: RetreatChoiceRequest) -> PromptPayload:
    """Render the stage-2 retreat-choice prompt for one yield.

    Args:
        request: The yielder, its passers, the scene robots and the validated
            candidates of this stage-2 call.

    Returns:
        Payload whose image is the request's frame, unchanged, and whose
        `known_robot_ids` lists the scene robots in ID order.
    """
    states = sorted(request.robot_states, key=lambda state: state.robot_id)
    robot_block = "\n".join(
        f"- {state.robot_id}: x={state.x:.2f}, y={state.y:.2f}{_role(state, request)}"
        for state in states
    )
    candidates = sorted(request.candidates, key=lambda candidate: candidate.label)
    candidate_block = "\n".join(
        f"- {c.label}: x={c.x:.2f}, y={c.y:.2f} (back up {c.backup_m:.2f} m, then "
        f"step {abs(c.lateral_m):.2f} m aside)"
        for c in candidates
    )
    labels = [c.label for c in candidates]
    user_prompt = _STAGE2_USER_TEMPLATE_V1.format(
        yielder_id=request.yielder_id,
        passers=", ".join(request.crossing_order) or "the other robots",
        robot_block=robot_block,
        candidate_block=candidate_block,
        labels=", ".join(labels),
    )
    return PromptPayload(
        system_prompt=STAGE2_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=[state.robot_id for state in states],
    )
