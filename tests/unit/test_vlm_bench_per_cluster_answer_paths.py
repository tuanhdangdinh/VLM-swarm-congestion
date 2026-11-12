"""Characterisation of the per-cluster ask/validate/re-ask loop through the bench variant.

Written before the loop moved into `reasoning.vlm.per_cluster_runner`, and run
unchanged before and after the move: the bench answer on every path (first
try, re-ask, exhausted attempts, backend exception, stop-class 4xx) must not
change.
"""

from __future__ import annotations

import json
from typing import Any

from benchmarks.vlm_bench.run import rebuild_request
from benchmarks.vlm_bench.variants.base import ReplayContext
from benchmarks.vlm_bench.variants.per_cluster import GroundingFirstPerClusterVariant
from reasoning.vlm.errors import BackendHTTPError
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from tests.unit.vlm_bench_fixtures import synthetic_items


class _Scripted:
    """Answers from a script; an exception entry is raised instead of answered."""

    def __init__(self, entries: list[Any]) -> None:
        self.entries = list(entries)
        self.prompts: list[str] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.prompts.append(payload.user_prompt)
        entry = self.entries.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        text, usage, latency = entry
        return BackendResponse(
            text=text, backend_id="scripted", token_usage=usage, latency_ms=latency
        )


def _reply(choices: dict[str, Any]) -> str:
    return json.dumps({"type": "deadlock", "justification": "t", "choices": choices})


def _answer(entries: list[Any], tmp_path, max_attempts: int = 2):
    item = synthetic_items()["aaaa0002"]
    request = rebuild_request(item, str(tmp_path / "x.png"))
    backend = _Scripted(entries)
    config = ReasonerConfig(backend_id="scripted", max_attempts=max_attempts)
    context = ReplayContext(backend=backend, reasoner_config=config, reasoner=None)
    return GroundingFirstPerClusterVariant().answer(item, request, context), backend


def test_answer_valid_first_attempt(tmp_path):
    answer, backend = _answer([(_reply({"A": "1", "B": "8"}), {"in": 3}, 7)], tmp_path)
    assert (answer.parse_status, answer.attempts) == ("valid", 1)
    assert answer.token_usage == {"in": 3} and answer.latency_ms == 7
    assert answer.note == "choices=A:1,B:8; none_feasible=0/2"
    assert set(answer.group_decisions) == {"A", "B"}
    assert answer.extra["choices"] == {"A": "1", "B": "8"}
    assert len(backend.prompts) == 1


def test_answer_reask_after_invalid_is_marked_invalid(tmp_path):
    answer, backend = _answer(
        [(_reply({"A": "1"}), {"in": 1}, 5), (_reply({"A": "1", "B": "8"}), {"in": 2}, 6)],
        tmp_path,
    )
    assert (answer.parse_status, answer.attempts) == ("invalid", 2)
    assert answer.token_usage == {"in": 2} and answer.latency_ms == 6
    first, second = backend.prompts
    assert second.startswith(first) and len(second) > len(first)


def test_answer_reask_suffix_appears_once(tmp_path):
    bad = (_reply({"A": "1"}), None, 1)
    _, backend = _answer([bad, bad, bad], tmp_path, max_attempts=3)
    first, second, third = backend.prompts
    assert second == third and second != first


def test_answer_failed_keeps_last_response_fields(tmp_path):
    answer, _ = _answer(
        [(_reply({"A": "1"}), {"in": 1}, 5), ('{"choices": 3}', {"in": 9}, 4)], tmp_path
    )
    assert (answer.parse_status, answer.attempts) == ("failed", 2)
    assert answer.decision is None and answer.group_decisions is None
    assert answer.raw_text == '{"choices": 3}'
    assert answer.token_usage == {"in": 9} and answer.latency_ms == 4
    assert answer.note.startswith("parse_failure: missing \"choices\" object")
    assert answer.extra["choices"] is None


def test_answer_exception_then_valid_is_valid(tmp_path):
    answer, _ = _answer(
        [ValueError("boom"), (_reply({"A": "1", "B": "8"}), None, 3)], tmp_path
    )
    assert (answer.parse_status, answer.attempts) == ("valid", 2)


def test_answer_failure_after_exception_keeps_earlier_response(tmp_path):
    answer, _ = _answer(
        [(_reply({"A": "1"}), {"in": 1}, 5), ValueError("boom")], tmp_path
    )
    assert (answer.parse_status, answer.attempts) == ("failed", 2)
    assert answer.raw_text == _reply({"A": "1"})
    assert answer.token_usage == {"in": 1} and answer.latency_ms == 5
    assert answer.note == "parse_failure: ValueError: boom"


def test_answer_stop_class_error_ends_the_call(tmp_path):
    answer, backend = _answer(
        [BackendHTTPError("bad", status_code=400), (_reply({"A": "1", "B": "8"}), None, 1)],
        tmp_path,
        max_attempts=3,
    )
    assert (answer.parse_status, answer.attempts) == ("failed", 1)
    assert answer.raw_text is None and answer.token_usage is None
    assert answer.note == "parse_failure: BackendHTTPError: bad"
    assert len(backend.prompts) == 1
