"""Stage-2 retreat-choice call: parse and degrade paths, and its backend factory."""

import json
import threading

import pytest

from reasoning.vlm.backend_factory import build_retreat_choice_backend
from reasoning.vlm.errors import BackendTimeoutError
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    ReasonerConfig,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
)
from reasoning.vlm.retreat_chooser import RetreatChooser

_REFUSAL = "I'm sorry, I can't assist with that."


def _request() -> RetreatChoiceRequest:
    return RetreatChoiceRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        yielder_id="robot_1",
        crossing_order=["robot_2"],
        robot_states=[
            RobotStateInput(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.3, y=0.0, theta=3.14),
        ],
        candidates=[
            RetreatCandidateOption(label="A", x=-1.79, y=0.36, backup_m=1.49, lateral_m=0.36),
            RetreatCandidateOption(label="B", x=-1.79, y=-0.36, backup_m=1.49, lateral_m=-0.36),
        ],
        listing_order=["B", "A"],
    )


def _config(**update) -> ReasonerConfig:
    return ReasonerConfig(**{"backend_id": "mock", "max_attempts": 2, "timeout_sec": 5.0, **update})


def _choice(letter: str) -> str:
    return json.dumps({"retreat_choice": letter, "justification": "keeps the aisle open"})


class _ScriptedBackend:
    """Replays texts, or raises when an entry is an exception."""

    def __init__(self, *entries) -> None:
        self._entries = list(entries)
        self.payloads = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        entry = self._entries[min(len(self.payloads) - 1, len(self._entries) - 1)]
        if isinstance(entry, Exception):
            raise entry
        return BackendResponse(text=entry, backend_id="scripted", latency_ms=3)


class TestChoose:
    def test_rendered_letter_is_answered(self):
        backend = _ScriptedBackend(_choice("b"))
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice.retreat_choice == "B"
        assert result.failure_cause is None
        assert result.attempts == 1
        # The arm id from the config on every path (conformance fix F09),
        # not the backend's model id.
        assert result.backend_id == _config().backend_id

    def test_payload_carries_the_frame_and_stage2_prompt(self):
        backend = _ScriptedBackend(_choice("A"))
        RetreatChooser(backend, _config()).choose(_request())
        payload = backend.payloads[0]
        assert payload.image_path == "/tmp/frame.png"
        assert "Retreat positions for robot_1" in payload.user_prompt

    def test_invalid_letter_ends_the_call_and_keeps_the_letter(self):
        backend = _ScriptedBackend(_choice("D"), _choice("A"))
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.failure_cause == "invalid_label"
        assert result.choice.retreat_choice == "D"
        assert result.attempts == 1
        assert len(backend.payloads) == 1

    def test_refusal_shaped_text_degrades_to_no_choice(self):
        backend = _ScriptedBackend(_REFUSAL)
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice is None
        assert result.failure_cause == "refusal"
        assert result.refusal_attempts == 2
        assert result.attempts == 2
        assert result.raw_text == _REFUSAL

    def test_empty_text_degrades_to_parse_failure(self):
        result = RetreatChooser(_ScriptedBackend(""), _config()).choose(_request())
        assert result.choice is None
        assert result.failure_cause == "parse_failure"

    def test_parse_failure_reasks_then_accepts(self):
        backend = _ScriptedBackend("not json", _choice("A"))
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice.retreat_choice == "A"
        assert result.failure_cause is None
        assert result.attempts == 2
        assert "Your previous response was invalid" in backend.payloads[1].user_prompt

    def test_backend_exception_degrades_without_raising(self):
        backend = _ScriptedBackend(RuntimeError("HTTP 429: spending cap"))
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice is None
        assert result.failure_cause == "backend_error"
        assert "429" in result.error_message
        assert result.attempts == 2

    def test_timeout_degrades_within_the_attempt_budget(self):
        release = threading.Event()

        class _Hung:
            def analyze(self, payload, config):
                release.wait(2.0)
                return BackendResponse(text=_choice("A"), backend_id="hung")

        try:
            result = RetreatChooser(_Hung(), _config(timeout_sec=0.05)).choose(_request())
        finally:
            release.set()
        assert result.choice is None
        assert result.failure_cause == "timeout"
        assert result.error_type == BackendTimeoutError.__name__
        assert result.attempts == 2

    def test_single_attempt_budget_is_honoured(self):
        backend = _ScriptedBackend("not json", _choice("A"))
        result = RetreatChooser(backend, _config(max_attempts=1)).choose(_request())
        assert result.choice is None
        assert len(backend.payloads) == 1

    def test_result_records_the_budget_it_ran_under(self):
        backend = _ScriptedBackend(_choice("A"))
        result = RetreatChooser(backend, _config(max_attempts=3, timeout_sec=7.5)).choose(
            _request()
        )
        assert (result.max_attempts, result.timeout_sec) == (3, 7.5)

    def test_timeout_bounds_each_call_with_the_chooser_config(self):
        seen = []

        class _Recording:
            def analyze(self, payload, config):
                seen.append(config.timeout_sec)
                return BackendResponse(text=_choice("A"), backend_id="rec")

        RetreatChooser(_Recording(), _config(timeout_sec=8.0)).choose(_request())
        assert seen == [8.0]


class TestRetreatChoiceBackend:
    def test_real_backend_is_reused(self, monkeypatch):
        stage1 = object()
        monkeypatch.setenv("VGU_MOCK_RETREAT_CHOICE_FILE", "/nonexistent.json")
        assert build_retreat_choice_backend("openai", stage1) is stage1

    def test_mock_without_script_has_no_stage2_backend(self, monkeypatch):
        monkeypatch.delenv("VGU_MOCK_RETREAT_CHOICE_FILE", raising=False)
        assert build_retreat_choice_backend("mock", MockBackend()) is None

    def test_mock_script_gets_its_own_backend(self, monkeypatch, tmp_path):
        script = tmp_path / "choice.json"
        script.write_text(_choice("B"), encoding="utf-8")
        monkeypatch.setenv("VGU_MOCK_RETREAT_CHOICE_FILE", str(script))
        stage1 = MockBackend()
        backend = build_retreat_choice_backend("mock", stage1)
        assert backend is not stage1
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice.retreat_choice == "B"

    def test_shipped_retreat_choice_script_forces_b(self, monkeypatch):
        monkeypatch.setenv(
            "VGU_MOCK_RETREAT_CHOICE_FILE", "config/mock_decisions/retreat_choice_b.json"
        )
        backend = build_retreat_choice_backend("mock", MockBackend())
        result = RetreatChooser(backend, _config()).choose(_request())
        assert result.choice.retreat_choice == "B"

    def test_missing_script_fails_fast(self, monkeypatch, tmp_path):
        monkeypatch.setenv("VGU_MOCK_RETREAT_CHOICE_FILE", str(tmp_path / "absent.json"))
        with pytest.raises(FileNotFoundError, match="VGU_MOCK_RETREAT_CHOICE_FILE"):
            build_retreat_choice_backend("mock", MockBackend())

    def test_empty_script_array_fails_fast(self, monkeypatch, tmp_path):
        script = tmp_path / "choice.json"
        script.write_text("[]", encoding="utf-8")
        monkeypatch.setenv("VGU_MOCK_RETREAT_CHOICE_FILE", str(script))
        with pytest.raises(ValueError, match="empty"):
            build_retreat_choice_backend("mock", MockBackend())
