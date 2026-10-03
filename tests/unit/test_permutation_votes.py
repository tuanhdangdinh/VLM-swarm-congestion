"""Permutation voting over presentation order (prereg-v2 rev 6 apparatus, 2026-10-04)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image
from swarm_orchestrator.models import PipelineOutcome, TerminalStage
from swarm_orchestrator.permutation_votes import (
    TIE_RULE,
    cyclic_shift_orders,
    permutation_votes_log,
    run_permutation_votes,
    shifted_request,
    vote_key,
)
from swarm_orchestrator.reasoning_pipeline import InProcessPipeline, write_decision_artifact

from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import Reasoner


def _decision_json(strategy="yield", yield_robot="robot_1", detected=True, **extra) -> str:
    body = {
        "congestion_detected": detected,
        "type": "deadlock" if detected else "none",
        "involved_robots": ["robot_1", "robot_2"] if detected else [],
        "root_cause": extra.pop("root_cause", "standoff"),
        "strategy": strategy if detected else "none",
        "justification": extra.pop("justification", "j"),
        "yield_robot": yield_robot if detected and strategy == "yield" else None,
        **extra,
    }
    return json.dumps(body)


_REFUSAL = "I'm sorry, I can't assist with that."


class _OrderRecordingBackend(MockBackend):
    """Answers per call from a script and records the presentation order of each call."""

    def __init__(self, texts: list[str]):
        super().__init__(response_sequence=texts)
        self.payloads: list[PromptPayload] = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        return super().analyze(payload, config)


def _frame(tmp_path: Path) -> str:
    path = tmp_path / "frame.png"
    Image.new("RGB", (32, 24), (40, 40, 40)).save(path)
    return str(path)


def _request(tmp_path: Path, robots=("robot_1", "robot_2", "robot_3"), **update) -> ReasonerRequest:
    return ReasonerRequest(
        request_id="req-v",
        image_path=_frame(tmp_path),
        frame_id="c",
        stamp=1.0,
        robot_states=[
            RobotStateInput(robot_id=rid, x=float(i), y=0.0, theta=0.0, status="STOPPED")
            for i, rid in enumerate(robots)
        ],
        prompt_version=3,
        **update,
    )


def _reasoner(
    texts: list[str], max_attempts: int = 1, **config
) -> tuple[Reasoner, _OrderRecordingBackend]:
    backend = _OrderRecordingBackend(texts)
    return (
        Reasoner(backend, ReasonerConfig(backend_id="mock", max_attempts=max_attempts, **config)),
        backend,
    )


class TestCyclicShifts:
    def test_three_robots_three_distinct_rotations(self):
        assert cyclic_shift_orders(["a", "b", "c"], 3) == [
            ("a", "b", "c"),
            ("b", "c", "a"),
            ("c", "a", "b"),
        ]

    def test_two_robots_wrap_so_the_base_order_repeats(self):
        assert cyclic_shift_orders(["a", "b"], 3) == [("a", "b"), ("b", "a"), ("a", "b")]

    def test_single_vote_is_the_base_order(self):
        assert cyclic_shift_orders(["b", "a"], 1) == [("b", "a")]

    def test_shift_zero_request_is_the_original_object(self, tmp_path):
        request = _request(tmp_path)
        assert shifted_request(request, ("robot_1", "robot_2", "robot_3"), 0) is request


class TestVoting:
    def test_three_calls_render_three_shifted_orders(self, tmp_path):
        reasoner, backend = _reasoner([_decision_json()] * 3)
        _, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert [call.order for call in record.calls] == [
            ("robot_1", "robot_2", "robot_3"),
            ("robot_2", "robot_3", "robot_1"),
            ("robot_3", "robot_1", "robot_2"),
        ]
        assert [p.known_robot_ids for p in backend.payloads] == [
            list(call.order) for call in record.calls
        ]
        assert record.distinct_orders == 3

    def test_per_call_prompt_hashes_match_the_rendered_prompts(self, tmp_path):
        reasoner, backend = _reasoner([_decision_json()] * 3)
        _, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        for call, payload in zip(record.calls, backend.payloads, strict=True):
            assert call.user_sha256 == hashlib.sha256(payload.user_prompt.encode()).hexdigest()
        assert len({call.user_sha256 for call in record.calls}) == 3

    def test_call_zero_prompt_is_byte_identical_to_the_single_call(self, tmp_path):
        request = _request(tmp_path)
        reasoner, backend = _reasoner([_decision_json()] * 3)
        run_permutation_votes(reasoner, request, 3)
        assert backend.payloads[0].user_prompt == build_prompt_payload(request).user_prompt

    def test_majority_wins_over_the_first_call(self, tmp_path):
        texts = [
            _decision_json(yield_robot="robot_1"),
            _decision_json(yield_robot="robot_2"),
            _decision_json(yield_robot="robot_2"),
        ]
        reasoner, _ = _reasoner(texts)
        result, record, winning_request = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert result.decision.yield_robot == "robot_2"
        assert record.winner_index == 1
        assert not record.tie_broken
        assert winning_request.robot_presentation_order == ("robot_2", "robot_3", "robot_1")

    def test_three_way_tie_goes_to_call_zero_the_drawn_order(self, tmp_path):
        texts = [
            _decision_json(
                yield_robot="robot_3", involved_robots=["robot_1", "robot_2", "robot_3"]
            ),
            _decision_json(yield_robot="robot_1"),
            _decision_json(yield_robot="robot_2"),
        ]
        reasoner, _ = _reasoner(texts)
        result, record, winning_request = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert record.tie_broken
        assert record.winner_index == 0
        assert result.decision.yield_robot == "robot_3"
        assert winning_request.robot_presentation_order == "id_asc"
        assert record.tie_rule == TIE_RULE

    def test_tie_without_call_zero_goes_to_the_earliest_voting_call(self, tmp_path):
        texts = [_REFUSAL, _decision_json(strategy="reverse"), _decision_json(strategy="yield")]
        reasoner, _ = _reasoner(texts)
        result, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert record.calls[0].vote is None
        assert record.tie_broken and record.winner_index == 1
        assert result.decision.strategy == "reverse"

    def test_failed_calls_abstain(self, tmp_path):
        texts = [
            _REFUSAL,
            _decision_json(yield_robot="robot_2"),
            _decision_json(yield_robot="robot_1"),
        ]
        reasoner, _ = _reasoner(texts)
        _, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert sum(vc.count for vc in record.vote_counts) == 2

    def test_all_calls_failing_returns_call_zero_failure(self, tmp_path):
        reasoner, _ = _reasoner([_REFUSAL] * 3)
        result, record, request = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert result.decision is None
        assert record.winner_index is None and record.winner_vote is None
        assert request.robot_presentation_order == "id_asc"

    def test_free_text_and_plan_come_from_the_winning_call_only(self, tmp_path):
        texts = [
            _decision_json(yield_robot="robot_1", root_cause="first", justification="j0"),
            _decision_json(
                yield_robot="robot_2", root_cause="second", justification="j1",
                proposed_plan=[{"robot_id": "robot_2", "action": "yield"},
                               {"robot_id": "robot_1", "action": "cross"}],
            ),
            _decision_json(yield_robot="robot_2", root_cause="third", justification="j2"),
        ]
        reasoner, _ = _reasoner(texts)
        result, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert record.winner_index == 1
        assert result.decision.root_cause == "second"
        assert result.decision.justification == "j1"
        assert [leg.robot_id for leg in result.decision.proposed_plan] == ["robot_2", "robot_1"]
        assert result.raw_text == texts[1]

    def test_vote_ignores_free_text_fields(self, tmp_path):
        a = vote_key(_parsed(_decision_json(root_cause="x")))
        b = vote_key(_parsed(_decision_json(root_cause="y", justification="other")))
        assert a == b

    def test_each_call_keeps_the_single_call_retry_policy(self, tmp_path):
        # Each call gets its own max_attempts budget: call 0 refuses then
        # recovers on its re-ask, exactly as a single call would.
        texts = [_REFUSAL, _decision_json(), _decision_json(), _decision_json()]
        reasoner, backend = _reasoner(texts, max_attempts=2)
        _, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        assert [call.diagnostics.attempts for call in record.calls] == [2, 1, 1]
        assert record.calls[0].diagnostics.refusal_attempts == 1
        assert record.total_backend_attempts == 4 == len(backend.payloads)

    def test_two_robot_scene_records_two_distinct_orders(self, tmp_path):
        reasoner, _ = _reasoner([_decision_json()] * 3)
        _, record, _ = run_permutation_votes(
            reasoner, _request(tmp_path, robots=("robot_1", "robot_2")), 3
        )
        assert record.distinct_orders == 2
        assert record.calls[0].user_sha256 == record.calls[2].user_sha256

    def test_votes_below_one_raise(self, tmp_path):
        reasoner, _ = _reasoner([_decision_json()])
        with pytest.raises(ValueError):
            run_permutation_votes(reasoner, _request(tmp_path), 0)

    def test_log_line_names_every_vote(self, tmp_path):
        reasoner, _ = _reasoner([_decision_json()] * 3)
        _, record, _ = run_permutation_votes(reasoner, _request(tmp_path), 3)
        line = permutation_votes_log("req-v", record)
        assert "n=3" in line and "winner=0" in line and "yield/robot_1" in line


def _parsed(text: str):
    from reasoning.vlm.output_parser import parse_decision_text

    return parse_decision_text(text)


def _never_ground(*args, **kwargs):
    raise AssertionError("grounding must not run for a no-congestion decision")


class _GroundSpy:
    def __init__(self):
        self.results = []

    def __call__(self, result, **kwargs):
        self.results.append(result)
        return {"command_id": "c1", "strategy": result.decision.strategy, "actions": []}


class TestPipelineIntegration:
    def test_single_vote_pipeline_makes_one_call_and_records_nothing(self, tmp_path):
        reasoner, backend = _reasoner([_decision_json(detected=False)])
        outcome = InProcessPipeline(reasoner=reasoner, ground_fn=_never_ground).run(
            _request(tmp_path)
        )
        assert len(backend.payloads) == 1
        assert outcome.permutation_votes is None

    def test_grounding_consumes_the_winning_call(self, tmp_path):
        texts = [
            _decision_json(yield_robot="robot_1"),
            _decision_json(yield_robot="robot_2"),
            _decision_json(yield_robot="robot_2"),
        ]
        reasoner, _ = _reasoner(texts)
        spy = _GroundSpy()
        outcome = InProcessPipeline(
            reasoner=reasoner, ground_fn=spy, validate_fn=lambda c: c, permutation_votes=3
        ).run(_request(tmp_path))
        assert spy.results[0].decision.yield_robot == "robot_2"
        assert outcome.reasoner_result.decision.yield_robot == "robot_2"
        assert outcome.permutation_votes.winner_index == 1

    def test_vlm_terminal_outcome_still_carries_the_record(self, tmp_path):
        reasoner, _ = _reasoner([_decision_json(detected=False)] * 3)
        outcome = InProcessPipeline(
            reasoner=reasoner, ground_fn=_never_ground, permutation_votes=3
        ).run(_request(tmp_path))
        assert outcome.terminal_stage is TerminalStage.VLM
        assert len(outcome.permutation_votes.calls) == 3

    def test_probe_analyze_never_votes(self, tmp_path):
        reasoner, backend = _reasoner([_decision_json()] * 3)
        InProcessPipeline(reasoner=reasoner, ground_fn=_never_ground, permutation_votes=3).analyze(
            _request(tmp_path)
        )
        assert len(backend.payloads) == 1

    def test_pipeline_rejects_zero_votes(self):
        with pytest.raises(ValueError):
            InProcessPipeline(reasoner=None, ground_fn=_never_ground, permutation_votes=0)


class TestArtifact:
    def _outcome(self, tmp_path):
        texts = [
            _decision_json(yield_robot="robot_1"),
            _decision_json(yield_robot="robot_2"),
            _decision_json(yield_robot="robot_2"),
        ]
        reasoner, _ = _reasoner(texts)
        request = _request(tmp_path)
        result, record, _ = run_permutation_votes(reasoner, request, 3)
        outcome = PipelineOutcome(
            request_id="req-v", reasoner_result=result, grounded_command=None,
            terminal_stage=TerminalStage.VLM, failure_reason="x", permutation_votes=record,
        )
        return outcome, request, record

    def test_artifact_carries_every_call(self, tmp_path):
        outcome, request, _ = self._outcome(tmp_path)
        payload = json.loads(
            write_decision_artifact(tmp_path / "out", outcome, request=request).read_text()
        )
        block = payload["permutation_votes"]
        assert [len(call["order"]) for call in block["calls"]] == [3, 3, 3]
        assert {call["user_sha256"] for call in block["calls"]} == {
            call["user_sha256"] for call in block["calls"]
        }
        assert len({call["user_sha256"] for call in block["calls"]}) == 3
        assert [call["raw_text"] is not None for call in block["calls"]] == [True] * 3
        assert block["winner_index"] == 1
        assert block["tie_rule"] == TIE_RULE

    def test_top_level_prompt_and_order_are_the_winners(self, tmp_path):
        outcome, request, record = self._outcome(tmp_path)
        payload = json.loads(
            write_decision_artifact(tmp_path / "out", outcome, request=request).read_text()
        )
        assert payload["robot_presentation_order"] == ["robot_2", "robot_3", "robot_1"]
        assert payload["prompt"]["user_sha256"] == record.calls[1].user_sha256
        assert payload["decision"]["yield_robot"] == "robot_2"

    def test_single_call_artifact_has_no_votes_block(self, tmp_path):
        reasoner, _ = _reasoner([_decision_json()])
        request = _request(tmp_path)
        outcome = PipelineOutcome(
            request_id="req-v", reasoner_result=reasoner.run(request), grounded_command=None,
            terminal_stage=TerminalStage.VLM, failure_reason="x",
        )
        payload = json.loads(
            write_decision_artifact(tmp_path / "out", outcome, request=request).read_text()
        )
        assert "permutation_votes" not in payload
        assert payload["robot_presentation_order"] == "id_asc"
