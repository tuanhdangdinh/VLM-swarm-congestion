"""Capability-probe prompt, version 1: frozen, self-contained, instrument-only.

Independent of the stage-1 (`PromptVersion` 1/2/3) and stage-2
(`Stage2PromptVersion` 2/3) lineages in `reasoning.vlm.models`: this battery
is a different instrument (pre-test model capabilities, not run the
congestion pipeline), so it shares no template, wording table, or helper with
`prompt_builder`/`prompt_v1`/`prompt_v2`/`stage2_prompt`. A wording change
here is a new `CAPABILITY_PROBE_PROMPT_VERSION`, never a silent edit; both the
raw template and two rendered fixtures are SHA-256 pinned in
`tests/unit/test_capability_probe_prompt.py`.

The prompt never states a robot's coordinates or world-frame position (the
rev-6 marked-choice rule): a `locate_robot` item's choices are read off
letter badges drawn on the image; every other probe type's choices are a
closed, pre-declared list of answer values (counts, "left"/"right", or robot
ids already visible in the frame's own ID labels).
"""
from __future__ import annotations

from reasoning.vlm.capability_probes.letters import ItemChoices
from reasoning.vlm.models import PromptPayload

CAPABILITY_PROBE_PROMPT_VERSION = 1

CAPABILITY_PROBE_SYSTEM_PROMPT = (
    "You are a careful visual question-answering assistant. You answer only "
    "from what is visible in the image, and you always respond in the exact "
    "format requested."
)

# The frozen template. `{question}` is the item's own rendered question
# (stored on `ProbeItem.question`); `{choices_block}` and `{letter_list}` are
# filled by `build_capability_probe_prompt_payload` from the item's seeded
# letter draw (`reasoning.vlm.capability_probes.letters`).
CAPABILITY_PROBE_PROMPT_V1 = (
    "{question}\n\n"
    "{choices_block}\n\n"
    'Respond with strict JSON of the form {{"choice": "<letter>"}}, where '
    "<letter> is exactly one of: {letter_list}. Do not include any other "
    "text, explanation, or punctuation outside the JSON object."
)

_IMAGE_CHOICES_BLOCK = (
    "The image has a 3x3 grid overlaid on it. Each grid cell has a single "
    "letter badge drawn at its centre. Find the robot named in the question "
    "above (its ID is labelled on the image), then answer with the letter "
    "badge of the grid cell that robot is in."
)


def _text_choices_block(choices: ItemChoices) -> str:
    lines = [f"{letter}: {choices.option_by_letter[letter]}" for letter in choices.listing_order]
    return "Options:\n" + "\n".join(lines)


def build_capability_probe_prompt_payload(
    question: str,
    choices: ItemChoices,
    image_path: str,
    image_choices: bool,
    known_robot_ids: list[str],
) -> PromptPayload:
    """Render one capability-probe item into a `PromptPayload`.

    Args:
        question: The item's own question text (`ProbeItem.question`).
        choices: The item's seeded letter assignment and listing order.
        image_path: Path to the frame the call is sent (the grid-overlaid
            copy for `locate_robot`; the manifest's annotated frame otherwise).
        image_choices: `ProbeItem.image_choices` -- True suppresses the option
            text block (the image carries the choices).
        known_robot_ids: Robot ids visible in the frame, passed through for
            parity with `PromptPayload.known_robot_ids`; unused by the prompt
            text itself (no probe type asks the model to name an unlisted id).

    Returns:
        The payload a `VLMBackend.analyze` call takes.
    """
    letters = sorted(choices.option_by_letter)
    choices_block = _IMAGE_CHOICES_BLOCK if image_choices else _text_choices_block(choices)
    user_prompt = CAPABILITY_PROBE_PROMPT_V1.format(
        question=question,
        choices_block=choices_block,
        letter_list=", ".join(letters),
    )
    return PromptPayload(
        system_prompt=CAPABILITY_PROBE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=image_path,
        known_robot_ids=known_robot_ids,
    )
