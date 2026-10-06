"""Conformance ruling F02: one retry policy for every arm and both stages.

429/5xx retry with exponential backoff (equal jitter) honouring Retry-After;
every other 4xx is final; attempt budgets unchanged. No live calls:
`requests.post` is replaced by a scripted fake and the sleep is recorded.
"""
from __future__ import annotations

import email.utils
import random
from pathlib import Path

import pytest
from PIL import Image

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.errors import BackendHTTPError, BackendTimeoutError, recorded_error_type
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import (
    ReasonerConfig,
    ReasonerRequest,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
)
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.reasoner import Reasoner
from reasoning.vlm.retreat_chooser import RetreatChooser
from reasoning.vlm.retry_policy import (
    BACKOFF_BASE_SEC,
    BACKOFF_CAP_SEC,
    MAX_TOTAL_BACKOFF_SEC,
    RETRY_AFTER_CAP_SEC,
    RetryPolicy,
    classify_failure,
    parse_retry_after,
)

_GOOD_DECISION = (
    '{"congestion_detected": true, "type": "deadlock", '
    '"involved_robots": ["robot_1"], "root_cause": "x", '
    '"strategy": "yield", "justification": "y"}'
)


class _Resp:
    def __init__(self, status_code: int, payload: dict | None = None, headers=None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = "" if payload is None else str(payload)

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("no body")
        return self._payload


def _openai_ok() -> _Resp:
    return _Resp(200, {"model": "m", "choices": [{"message": {"content": _GOOD_DECISION}}]})


def _script(monkeypatch, module: str, *responses) -> list[dict]:
    calls: list[dict] = []
    queue = list(responses)

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return queue.pop(0) if len(queue) > 1 else queue[0]

    monkeypatch.setattr(f"reasoning.vlm.{module}.requests.post", fake_post)
    return calls


def _request(tmp_path: Path) -> ReasonerRequest:
    frame = tmp_path / "f.png"
    Image.new("RGB", (8, 6)).save(frame)
    return ReasonerRequest(
        request_id="r",
        image_path=str(frame),
        frame_id="f",
        stamp=0.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0, y=0, theta=0)],
    )


def _recording_policy() -> tuple[RetryPolicy, list[float]]:
    sleeps: list[float] = []
    return RetryPolicy(sleep=sleeps.append, rng=random.Random(0)), sleeps


# --- the policy itself -------------------------------------------------------


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504, 529])
def test_classify_failure_backs_off_on_429_and_5xx(status):
    assert classify_failure(BackendHTTPError("x", status_code=status)) == "backoff"


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 408, 413, 422])
def test_classify_failure_stops_on_any_other_4xx(status):
    assert classify_failure(BackendHTTPError("x", status_code=status)) == "stop"


def test_classify_failure_backs_off_on_a_transport_error():
    assert classify_failure(ConnectionError("reset")) == "backoff"


def test_classify_failure_retries_a_timeout_without_waiting():
    assert classify_failure(BackendTimeoutError("slow")) == "immediate"


def test_classify_failure_retries_an_unexpected_exception_without_waiting():
    assert classify_failure(KeyError("choices")) == "immediate"


def test_http_error_is_recorded_under_the_connection_error_name():
    assert recorded_error_type(BackendHTTPError("x", status_code=429)) == "ConnectionError"


@pytest.mark.parametrize(("attempt", "low", "high"), [(1, 1.0, 2.0), (2, 2.0, 4.0), (3, 4.0, 8.0)])
def test_exponential_delay_uses_equal_jitter(attempt, low, high):
    policy = RetryPolicy(rng=random.Random(attempt))
    for _ in range(50):
        assert low <= policy.delay(attempt, None) <= high


def test_exponential_delay_is_capped():
    policy = RetryPolicy(rng=random.Random(1))
    assert BACKOFF_CAP_SEC / 2 <= policy.delay(12, None) <= BACKOFF_CAP_SEC


def test_documented_parameters():
    assert (BACKOFF_BASE_SEC, BACKOFF_CAP_SEC, RETRY_AFTER_CAP_SEC, MAX_TOTAL_BACKOFF_SEC) == (
        2.0,
        30.0,
        60.0,
        90.0,
    )


def test_retry_after_replaces_the_exponential_delay():
    assert RetryPolicy().delay(1, 7.0) == 7.0


def test_retry_after_is_clamped():
    assert RetryPolicy().delay(1, 3600.0) == RETRY_AFTER_CAP_SEC


def test_parse_retry_after_reads_seconds_case_insensitively():
    assert parse_retry_after({"retry-after": "56"}) == 56.0
    assert parse_retry_after({"Retry-After": "1.5"}) == 1.5


def test_parse_retry_after_reads_an_http_date():
    when = email.utils.formatdate(1_000_030, usegmt=True)
    assert parse_retry_after({"Retry-After": when}, now=1_000_000) == 30.0


def test_parse_retry_after_ignores_absent_or_invalid_values():
    assert parse_retry_after({}) is None
    assert parse_retry_after(None) is None
    assert parse_retry_after({"Retry-After": "soon"}) is None


def test_total_backoff_per_call_is_capped():
    policy, sleeps = _recording_policy()
    exc = BackendHTTPError("x", status_code=429, retry_after_sec=60.0)
    waited = 0.0
    for attempt in (1, 2, 3):
        waited += policy.wait_before_retry(exc, attempt, waited)
    assert sleeps == [60.0, 30.0]
    assert waited == MAX_TOTAL_BACKOFF_SEC


# --- stage 1 pins ------------------------------------------------------------


def test_a_429_with_retry_after_waits_that_long_then_retries(monkeypatch, tmp_path):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    calls = _script(
        monkeypatch,
        "openai_backend",
        _Resp(429, {"error": {"code": "rate_limit_exceeded"}}, headers={"Retry-After": "7"}),
        _openai_ok(),
    )
    policy, sleeps = _recording_policy()
    backend = OpenAIBackend(api_key_env="VGU_RETRY_KEY")
    config = ReasonerConfig(backend_id="a", max_attempts=4)
    reasoner = Reasoner(backend, config, retry_policy=policy)
    result = reasoner.run(_request(tmp_path))
    assert result.decision is not None
    assert (len(calls), result.diagnostics.attempts, sleeps) == (2, 2, [7.0])


def _adapter_and_module(name: str):
    if name == "anthropic":
        return AnthropicBackend(api_key_env="VGU_RETRY_KEY"), "anthropic_backend"
    if name == "gemini":
        return GeminiBackend(api_key_env="VGU_RETRY_KEY"), "gemini_backend"
    if name == "llama_server":
        return LlamaServerBackend(model_id="m"), "llama_server_backend"
    return OpenAIBackend(api_key_env="VGU_RETRY_KEY"), "openai_backend"


@pytest.mark.parametrize("adapter", ["openai", "anthropic", "gemini", "llama_server"])
def test_a_400_consumes_exactly_one_attempt(monkeypatch, tmp_path, adapter):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    backend, module = _adapter_and_module(adapter)
    calls = _script(monkeypatch, module, _Resp(400, {"error": {"code": "invalid_request"}}))
    policy, sleeps = _recording_policy()
    config = ReasonerConfig(backend_id="a", max_attempts=4)
    reasoner = Reasoner(backend, config, retry_policy=policy)
    result = reasoner.run(_request(tmp_path))
    assert result.decision is None
    assert (len(calls), result.diagnostics.attempts, sleeps) == (1, 1, [])
    assert result.diagnostics.error_type == "ConnectionError"
    assert "HTTP 400" in result.diagnostics.error_message
    assert result.diagnostics.attempt_token_usage == [None]


@pytest.mark.parametrize("adapter", ["openai", "anthropic", "gemini", "llama_server"])
def test_a_persistent_503_spends_the_budget_with_growing_waits(monkeypatch, tmp_path, adapter):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    backend, module = _adapter_and_module(adapter)
    calls = _script(monkeypatch, module, _Resp(503, {"error": {"code": "unavailable"}}))
    policy, sleeps = _recording_policy()
    config = ReasonerConfig(backend_id="a", max_attempts=4)
    reasoner = Reasoner(backend, config, retry_policy=policy)
    result = reasoner.run(_request(tmp_path))
    assert (len(calls), result.diagnostics.attempts) == (4, 4)
    assert len(sleeps) == 3
    for wait, (low, high) in zip(sleeps, [(1, 2), (2, 4), (4, 8)], strict=True):
        assert low <= wait <= high


class _TimesOutThenAnswers:
    def __init__(self) -> None:
        self.calls = 0

    def analyze(self, payload, config):
        from reasoning.vlm.models import BackendResponse

        self.calls += 1
        if self.calls == 1:
            raise BackendTimeoutError("slow")
        return BackendResponse(text=_GOOD_DECISION, backend_id="m")


def test_a_timeout_is_retried_without_a_wait(tmp_path):
    policy, sleeps = _recording_policy()
    result = Reasoner(
        _TimesOutThenAnswers(), ReasonerConfig(backend_id="a", max_attempts=2), retry_policy=policy
    ).run(_request(tmp_path))
    assert result.decision is not None
    assert sleeps == []


def test_no_wait_follows_the_final_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    _script(monkeypatch, "openai_backend", _Resp(500, {}, headers={"Retry-After": "3"}))
    policy, sleeps = _recording_policy()
    Reasoner(
        OpenAIBackend(api_key_env="VGU_RETRY_KEY"),
        ReasonerConfig(backend_id="a", max_attempts=2),
        retry_policy=policy,
    ).run(_request(tmp_path))
    assert sleeps == [3.0]


# --- stage 2 pins ------------------------------------------------------------


def _stage2_request(tmp_path: Path) -> RetreatChoiceRequest:
    frame = tmp_path / "frame.png"
    Image.new("RGB", (8, 6)).save(frame)
    return RetreatChoiceRequest(
        request_id="req-2",
        image_path=str(frame),
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


def test_stage2_a_400_consumes_exactly_one_attempt(monkeypatch, tmp_path):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    calls = _script(monkeypatch, "openai_backend", _Resp(400, {"error": {}}))
    policy, sleeps = _recording_policy()
    result = RetreatChooser(
        OpenAIBackend(api_key_env="VGU_RETRY_KEY"),
        ReasonerConfig(backend_id="a", max_attempts=2, timeout_sec=8),
        retry_policy=policy,
    ).choose(_stage2_request(tmp_path))
    assert (len(calls), result.attempts, result.failure_cause, sleeps) == (
        1,
        1,
        "backend_error",
        [],
    )


def test_stage2_a_429_with_retry_after_waits_then_retries(monkeypatch, tmp_path):
    monkeypatch.setenv("VGU_RETRY_KEY", "k")
    calls = _script(
        monkeypatch,
        "openai_backend",
        _Resp(429, {}, headers={"retry-after": "2"}),
        _Resp(200, {"choices": [{"message": {"content": '{"retreat_choice": "A"}'}}]}),
    )
    policy, sleeps = _recording_policy()
    result = RetreatChooser(
        OpenAIBackend(api_key_env="VGU_RETRY_KEY"),
        ReasonerConfig(backend_id="a", max_attempts=2, timeout_sec=8),
        retry_policy=policy,
    ).choose(_stage2_request(tmp_path))
    assert (len(calls), result.attempts, sleeps) == (2, 2, [2.0])
