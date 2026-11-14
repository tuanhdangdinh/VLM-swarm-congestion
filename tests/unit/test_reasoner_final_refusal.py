"""`ReasonerConfig.final_refusal_categories`: refusal categories that end a run at once.

Owner approval 2026-11-14 ("I approve options 2 and 3"): a provider refusal whose
category is listed is final on its first occurrence (no re-ask, no neutral-image
fallback). Default off, so every shipped config keeps its recorded behaviour.
"""

from pathlib import Path

import pytest
import yaml
from PIL import Image
from pydantic import ValidationError

from reasoning.vlm.backend_factory import resolve_reasoner_config
from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.reasoner import Reasoner

_GOOD = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)
_BAD = "not json"
_TEXT_REFUSAL = "I'm sorry, I can't assist with that."
_REPO = Path(__file__).resolve().parents[2]


class _Scripted:
    """Replays scripted responses and keeps every payload and its image pixel."""

    def __init__(self, *responses: BackendResponse) -> None:
        self._responses = list(responses)
        self.payloads: list[PromptPayload] = []
        self.pixels: list[tuple[int, int, int]] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.payloads.append(payload)
        with Image.open(payload.image_path) as image:
            self.pixels.append(image.convert("RGB").getpixel((0, 0)))
        return self._responses[min(len(self.payloads) - 1, len(self._responses) - 1)]


def _refused(category: str | None = "reasoning_extraction") -> BackendResponse:
    return BackendResponse(text="", backend_id="c", refusal=True, refusal_category=category)


def _answer(text: str = _GOOD) -> BackendResponse:
    return BackendResponse(text=text, backend_id="c")


def _request(tmp_path: Path) -> ReasonerRequest:
    frame = tmp_path / "frame.png"
    Image.new("RGB", (16, 12), (10, 200, 30)).save(frame)
    return ReasonerRequest(
        request_id="req-final",
        image_path=str(frame),
        frame_id="cam",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
    )


def _config(**overrides) -> ReasonerConfig:
    base = {"backend_id": "anthropic", "max_attempts": 4, "image_fallback_after_attempts": 2}
    return ReasonerConfig(**{**base, **overrides})


def _sequence(backend: _Scripted) -> list[tuple[bool, bool, tuple[int, int, int]]]:
    """Per attempt: (re-ask suffix present, prompt unchanged, image pixel)."""
    first = backend.payloads[0].user_prompt
    return [
        ("previous response was invalid" in p.user_prompt, p.user_prompt == first, px)
        for p, px in zip(backend.payloads, backend.pixels)
    ]


def test_final_refusal_categories_default_is_empty():
    assert ReasonerConfig(backend_id="x").final_refusal_categories == ()


def test_final_refusal_categories_default_keeps_attempt_sequence_and_fallback(tmp_path):
    backend = _Scripted(_refused(), _refused(), _refused(), _refused())
    result = Reasoner(backend, _config()).run(_request(tmp_path))
    assert result.decision is None
    assert result.diagnostics.attempts == 4
    assert result.diagnostics.refusal_attempts == 4
    assert result.diagnostics.image_fallback_attempt == 3
    assert _sequence(backend) == [
        (False, True, (10, 200, 30)),
        (True, False, (10, 200, 30)),
        (False, True, (128, 128, 128)),
        (True, False, (128, 128, 128)),
    ]


def test_final_refusal_categories_default_recovers_a_late_answer(tmp_path):
    backend = _Scripted(_refused(), _refused(), _answer())
    result = Reasoner(backend, _config()).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 3


def test_final_refusal_listed_category_stops_after_attempt_one(tmp_path):
    backend = _Scripted(_refused(), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is None
    assert len(backend.payloads) == 1
    assert result.diagnostics.attempts == 1


def test_final_refusal_listed_category_uses_no_fallback(tmp_path):
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(_Scripted(_refused()), config).run(_request(tmp_path))
    assert result.diagnostics.image_fallback_used is False
    assert result.diagnostics.image_fallback_attempt is None


def test_final_refusal_result_carries_category_and_reason(tmp_path):
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(_Scripted(_refused()), config).run(_request(tmp_path))
    diag = result.diagnostics
    assert diag.parse_status == "failed"
    assert diag.refusal_attempts == 1
    assert diag.refusal_category == "reasoning_extraction"
    assert diag.error_type == "FinalRefusal"
    assert "reasoning_extraction" in (diag.error_message or "")
    assert "final_refusal_categories" in (diag.error_message or "")


def test_final_refusal_attempt_record_is_final_with_no_backoff(tmp_path):
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(_Scripted(_refused()), config).run(_request(tmp_path))
    (record,) = result.diagnostics.attempt_records
    assert record.outcome == "refusal"
    assert record.refusal_source == "provider"
    assert record.backoff_sec is None


def test_final_refusal_keeps_billed_usage(tmp_path):
    refused = _refused().model_copy(update={"token_usage": {"input_tokens": 3019}})
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(_Scripted(refused), config).run(_request(tmp_path))
    assert result.diagnostics.attempt_token_usage == [{"input_tokens": 3019}]


def test_final_refusal_listed_category_after_a_parse_failure_stops(tmp_path):
    backend = _Scripted(_answer(_BAD), _refused(), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is None
    assert len(backend.payloads) == 2
    assert result.diagnostics.error_type == "FinalRefusal"


def test_final_refusal_unlisted_category_follows_existing_policy(tmp_path):
    backend = _Scripted(_refused("general_harms"), _refused("general_harms"), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 3
    assert result.diagnostics.image_fallback_attempt == 3


def test_final_refusal_uncategorised_refusal_is_not_final(tmp_path):
    backend = _Scripted(_refused(None), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 2


def test_final_refusal_text_pattern_refusal_is_not_final(tmp_path):
    backend = _Scripted(_answer(_TEXT_REFUSAL), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is not None
    assert result.diagnostics.attempts == 2


def test_final_refusal_parse_failure_still_reasks(tmp_path):
    backend = _Scripted(_answer(_BAD), _answer())
    config = _config(final_refusal_categories=("reasoning_extraction",))
    result = Reasoner(backend, config).run(_request(tmp_path))
    assert result.decision is not None
    assert "previous response was invalid" in backend.payloads[1].user_prompt


def test_final_refusal_categories_rejects_empty_entry():
    with pytest.raises(ValidationError):
        ReasonerConfig(backend_id="x", final_refusal_categories=("",))


def test_final_refusal_categories_rejects_duplicates():
    with pytest.raises(ValidationError):
        ReasonerConfig(backend_id="x", final_refusal_categories=("a", "a"))


def test_final_refusal_categories_coerces_a_yaml_list():
    raw = {"reasoner": {"backend_id": "x"}, "anthropic": {"reasoner": {}}}
    raw["anthropic"]["reasoner"]["final_refusal_categories"] = ["reasoning_extraction"]
    config = resolve_reasoner_config(raw, "anthropic")
    assert config.final_refusal_categories == ("reasoning_extraction",)


def test_final_refusal_categories_absent_from_every_shipped_config():
    raw = yaml.safe_load((_REPO / "config/models.yaml").read_text())["vlm"]
    sections = [k for k, v in raw.items() if isinstance(v, dict) and k != "reasoner"]
    assert "final_refusal_categories" not in raw["reasoner"]
    for section in sections:
        assert "final_refusal_categories" not in (raw[section].get("reasoner") or {}), section
