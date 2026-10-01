"""Extract one lettered choice from a capability-probe backend response.

Deliberately tolerant of surrounding prose or a fenced code block (backends
vary in how strictly they honour "no other text"), but never guesses: a
response with no recognizable `{"choice": "<letter>"}` object and no bare
single-letter answer is a parse failure, and a letter that is not one of the
item's valid letters is `invalid_letter` -- both score as wrong, never
dropped, so refusal/parse-failure rates stay visible in the summary.
"""
from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Literal

AnswerFailureCause = Literal["empty_response", "parse_failure", "invalid_letter"]

_JSON_OBJECT_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)
_BARE_LETTER_RE = re.compile(r"^[A-Za-z]$")


def parse_probe_answer(
    raw_text: str | None, valid_letters: Sequence[str]
) -> tuple[str | None, AnswerFailureCause | None]:
    """Parse one backend response into an uppercase letter, or report why not.

    Args:
        raw_text: The backend's raw assistant text (`BackendResponse.text`).
        valid_letters: The letters this item actually offers.

    Returns:
        `(letter, None)` on a usable, valid answer; `(None, cause)` when no
        letter could be read at all; `(letter, "invalid_letter")` when a
        letter was read but it is not one `valid_letters` offers (kept so
        the caller can log what the model actually said).
    """
    if raw_text is None or not raw_text.strip():
        return None, "empty_response"
    text = raw_text.strip()

    candidate: str | None = None
    match = _JSON_OBJECT_RE.search(text)
    if match is not None:
        try:
            obj = json.loads(match.group(0))
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            value = obj.get("choice")
            if isinstance(value, str) and value.strip():
                candidate = value.strip()

    if candidate is None and _BARE_LETTER_RE.match(text):
        candidate = text

    if candidate is None:
        return None, "parse_failure"

    letter = candidate.strip().upper()
    if len(letter) != 1 or not letter.isalpha():
        return letter, "parse_failure"
    if letter not in valid_letters:
        return letter, "invalid_letter"
    return letter, None
