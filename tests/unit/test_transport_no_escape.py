"""Conformance fix F01: no exception class escapes `Reasoner.run` or stage 2.

Reproduces probe 1 of `docs/reports/2026-10-07-conformance-review.md`
(Verification): a local socket server on 127.0.0.1 answers every request
either with a body it closes mid-stream (`midbody`) or with a non-JSON
`text/html` 200 (`html200`), and each of the four adapters runs through the
real `Reasoner` with `max_attempts=4`. At tip 060abe0 four of the eight cases
escaped `run`; at the prereg-v1 tag six did (the openai adapter's malformed-
body guard postdates the tag). Transport hotfix for v1 collection. No
provider is contacted.
"""
from __future__ import annotations

import socket
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import (
    BackendResponse,
    ReasonerConfig,
    ReasonerRequest,
    RetreatCandidateOption,
    RetreatChoiceRequest,
    RobotStateInput,
)
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.reasoner import Reasoner
from reasoning.vlm.retreat_chooser import RetreatChooser

_KEY_ENV = "VGU_TEST_NO_ESCAPE_KEY"


class _ProbeServer:
    """One-shot HTTP responder whose reply shape is switched per test."""

    def __init__(self) -> None:
        self.mode = "midbody"
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self.base_url = f"http://127.0.0.1:{self._sock.getsockname()[1]}/v1"
        self._closed = False
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while not self._closed:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            try:
                conn.recv(1 << 20)
                try:
                    while True:
                        conn.settimeout(0.2)
                        if not conn.recv(1 << 20):
                            break
                except OSError:
                    pass
                if self.mode == "midbody":
                    conn.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                        b"Content-Length: 5000\r\n\r\n{\"id\":\"x\","
                    )
                else:
                    body = b"<html>gateway</html>"
                    conn.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                        b"Content-Length: %d\r\n\r\n" % len(body) + body
                    )
            finally:
                conn.close()

    def close(self) -> None:
        self._closed = True
        self._sock.close()


@pytest.fixture
def probe_server() -> Iterator[_ProbeServer]:
    server = _ProbeServer()
    yield server
    server.close()


def _request(tmp_path: Path) -> ReasonerRequest:
    frame = tmp_path / "f.png"
    Image.new("RGB", (64, 48)).save(frame)
    return ReasonerRequest(
        request_id="r",
        image_path=str(frame),
        frame_id="f",
        stamp=0.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0, y=0, theta=0)],
    )


def _adapter(name: str, base_url: str):
    if name == "anthropic":
        return AnthropicBackend(base_url=base_url, api_key_env=_KEY_ENV)
    if name == "llama_server":
        return LlamaServerBackend(base_url=base_url, model_id="m", mmproj_path="x")
    if name == "gemini":
        return GeminiBackend(base_url=base_url, api_key_env=_KEY_ENV)
    return OpenAIBackend(base_url=base_url, api_key_env=_KEY_ENV)


_ADAPTERS = ("anthropic", "llama_server", "gemini", "openai")


@pytest.mark.parametrize("mode", ["midbody", "html200"])
@pytest.mark.parametrize("adapter", _ADAPTERS)
def test_probe_case_ends_as_a_recorded_failure_not_an_escape(
    monkeypatch, tmp_path, probe_server, adapter, mode
):
    monkeypatch.setenv(_KEY_ENV, "dummy-not-a-key")
    probe_server.mode = mode
    config = ReasonerConfig(backend_id=adapter, max_attempts=4, timeout_sec=5)
    result = Reasoner(_adapter(adapter, probe_server.base_url), config).run(_request(tmp_path))
    assert result.decision is None
    assert result.diagnostics.attempts == 4
    assert result.diagnostics.error_type == "ConnectionError"


def _stage2_request(tmp_path: Path) -> RetreatChoiceRequest:
    frame = tmp_path / "frame.png"
    Image.new("RGB", (64, 48)).save(frame)
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


@pytest.mark.parametrize("mode", ["midbody", "html200"])
@pytest.mark.parametrize("adapter", _ADAPTERS)
def test_probe_case_on_stage2_ends_as_a_backend_error(
    monkeypatch, tmp_path, probe_server, adapter, mode
):
    monkeypatch.setenv(_KEY_ENV, "dummy-not-a-key")
    probe_server.mode = mode
    config = ReasonerConfig(backend_id=adapter, max_attempts=2, timeout_sec=5)
    chooser = RetreatChooser(_adapter(adapter, probe_server.base_url), config)
    result = chooser.choose(_stage2_request(tmp_path))
    assert result.choice is None
    assert (result.attempts, result.failure_cause) == (2, "backend_error")


class _RaisesUnexpected:
    def analyze(self, payload, config):
        raise KeyError("choices")


def test_an_unexpected_adapter_exception_is_a_recorded_attempt(tmp_path):
    config = ReasonerConfig(backend_id="arm", max_attempts=3)
    result = Reasoner(_RaisesUnexpected(), config).run(_request(tmp_path))
    assert (result.diagnostics.attempts, result.diagnostics.error_type) == (3, "KeyError")
    assert result.diagnostics.backend_id == "arm"


class _BilledThenParserExplodes:
    def analyze(self, payload, config):
        return BackendResponse(text="{}", backend_id="m", token_usage={"prompt_tokens": 9})


def test_an_unexpected_parser_exception_is_a_recorded_parse_failure(monkeypatch, tmp_path):
    def explode(text):
        raise RuntimeError("parser bug")

    monkeypatch.setattr("reasoning.vlm.reasoner.parse_decision_with_degradations", explode)
    config = ReasonerConfig(backend_id="arm", max_attempts=2)
    result = Reasoner(_BilledThenParserExplodes(), config).run(_request(tmp_path))
    assert result.decision is None
    assert result.diagnostics.error_type == "RuntimeError"
    assert (result.diagnostics.attempts, result.diagnostics.parse_status) == (2, "failed")


def test_an_unexpected_stage2_parser_exception_is_a_parse_failure(monkeypatch, tmp_path):
    def explode(text, labels):
        raise RuntimeError("parser bug")

    monkeypatch.setattr("reasoning.vlm.retreat_chooser.parse_retreat_choice_text", explode)
    config = ReasonerConfig(backend_id="arm", max_attempts=2)
    result = RetreatChooser(_BilledThenParserExplodes(), config).choose(
        _stage2_request(tmp_path)
    )
    assert (result.attempts, result.failure_cause, result.error_type) == (
        2,
        "parse_failure",
        "RuntimeError",
    )
