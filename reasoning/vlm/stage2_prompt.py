"""Stage-2 retreat-choice prompt (rev-8 Appendix A.3), set-of-mark letters.

M5 draws each candidate's letter on a copy of the stage-1 annotated frame
(set-of-mark) and the prompt says so; when that drawing degrades, the frame
goes unmarked and the prompt says the letters are not drawn instead. Either
way the letters are also listed with their world coordinates.

Candidates are listed in letter order, never in rank order, and without their
sweep clearances: either would leak the geometry-max answer the fallback
already supplies. Which candidate carries which letter is M5's (seeded,
counterbalanced) choice; this module renders whatever letters it is given.
"""

from reasoning.vlm.models import PromptPayload, RetreatChoiceRequest, RobotStateInput
from reasoning.vlm.prompt_builder import SYSTEM_PROMPT

STAGE2_SYSTEM_PROMPT = SYSTEM_PROMPT

# Version 2 (CURRENT_STAGE2_PROMPT_VERSION). The objective sentence is the
# research design's A.3 wording; "marked" is dropped when no marks are drawn.
_STAGE2_USER_TEMPLATE_V2 = """You are a warehouse swarm robotics traffic controller. \
{yielder_id} will yield so that {passers} can pass: it backs up, then steps aside \
to one of the lettered retreat positions below. Every position has already been \
checked to keep a safe distance from the listed robots along the whole path.

Robots (world frame, metres):
{robot_block}

Retreat positions for {yielder_id} (world frame, metres):
{candidate_block}

{image_sentence} The image shows the scene as it is now, including anything not \
listed above.

Choose the {marked}retreat position that best clears the conflict while preserving \
the passage space the other robots need and avoiding visible obstacles or traffic.

Respond with ONLY a JSON object, no other text:
{{"retreat_choice": "<one of {labels}>", "justification": "<one clause>"}}"""

_MARKS_DRAWN_SENTENCE = (
    "Each position is marked on the image by its letter in a white disc, inside a "
    "ring the size of the robot."
)
_MARKS_ABSENT_SENTENCE = (
    "The letters are not drawn on the image; locate each position from its coordinates."
)


def _role(state: RobotStateInput, request: RetreatChoiceRequest) -> str:
    if state.robot_id == request.yielder_id:
        return " (yielding)"
    if state.robot_id in request.crossing_order:
        return " (passing)"
    return ""


def build_stage2_prompt_payload(request: RetreatChoiceRequest) -> PromptPayload:
    """Render the stage-2 retreat-choice prompt for one yield.

    Args:
        request: The yielder, its passers, the scene robots and the lettered
            candidates of this stage-2 call.

    Returns:
        Payload whose image is the request's image (marked or not, as
        `request.marks_drawn` says) and whose `known_robot_ids` lists the
        scene robots in ID order.
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
    user_prompt = _STAGE2_USER_TEMPLATE_V2.format(
        yielder_id=request.yielder_id,
        passers=", ".join(request.crossing_order) or "the other robots",
        robot_block=robot_block,
        candidate_block=candidate_block,
        image_sentence=(
            _MARKS_DRAWN_SENTENCE if request.marks_drawn else _MARKS_ABSENT_SENTENCE
        ),
        marked="marked " if request.marks_drawn else "",
        labels=", ".join(labels),
    )
    return PromptPayload(
        system_prompt=STAGE2_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=[state.robot_id for state in states],
    )
