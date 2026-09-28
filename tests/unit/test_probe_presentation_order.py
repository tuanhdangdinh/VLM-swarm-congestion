"""Unit tests for the offline presentation-order probe's planning and recording.

Covers the backend switch added for Gemini Robotics-ER 2: the default `openai`
path must plan and record exactly as before, and the `gemini` path must plan one
job per seed and carry the seed plus the sampling fields the Interactions API
could not honour into every persisted record. No API calls are made; backends are
built through a stubbed `build_backend`.
"""
from __future__ import annotations

import time

import pytest

from reasoning.vlm.models import (
    BackendResponse,
    CongestionDecision,
    GeminiBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerResult,
)
from scripts.probe_presentation_order import (
    Cell,
    CellContext,
    Job,
    PacedBackend,
    build_call_record,
    build_paced_backends,
    first_listed_standoff_robot,
    plan_jobs,
    plan_seeded_jobs,
    summarize_cells,
    summary_temperature,
)


def _context(variant: str = "w0p2_eopen", order: str = "id_asc") -> CellContext:
    cell = Cell(variant=variant, order=order, obstacle_channel=False)
    return CellContext(
        cell=cell,
        request=None,
        prompt_sha256="a" * 64,
        image_path="images/w0p2_eopen.png",
        first_listed_robot="robot_1",
        correct_yielder="robot_2",
        fcfs_yielder="robot_1",
    )


def _result(
    yield_robot: str = "robot_1", unsupported: dict[str, float] | None = None
) -> ReasonerResult:
    return ReasonerResult(
        request_id="req",
        decision=CongestionDecision(
            congestion_detected=True,
            type="deadlock",
            involved_robots=["robot_1", "robot_2"],
            strategy="yield",
            yield_robot=yield_robot,
            root_cause="head-on",
            justification="both stopped nose to nose",
        ),
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req",
            backend_id="gemini-robotics-er-2-preview",
            attempts=1,
            latency_ms=1234,
            parse_status="valid",
            unsupported_sampling=unsupported,
        ),
    )


def test_plan_jobs_default_path_leaves_every_seed_unset():
    jobs = plan_jobs([_context()], n_greedy=5, n_sampled=10, sampled_temperature=0.6)

    assert len(jobs) == 15
    assert {job.seed for job in jobs} == {None}


def test_plan_seeded_jobs_yields_one_job_per_cell_per_distinct_seed():
    contexts = [_context(order="id_asc"), _context(order="id_desc")]

    jobs = plan_seeded_jobs(contexts, n_seeds=15, temperature=0.6)

    assert len(jobs) == 30
    for context in contexts:
        seeds = [job.seed for job in jobs if job.cell == context.cell]
        assert seeds == list(range(15))


def test_plan_seeded_jobs_records_the_unhonoured_temperature_on_every_job():
    jobs = plan_seeded_jobs([_context()], n_seeds=3, temperature=0.6)

    assert {job.temperature for job in jobs} == {0.6}


def test_plan_seeded_jobs_rejects_a_non_positive_seed_count():
    with pytest.raises(ValueError, match="n_seeds"):
        plan_seeded_jobs([_context()], n_seeds=0, temperature=0.6)


def test_build_call_record_without_seed_omits_the_seeded_keys():
    job = Job(cell=_context().cell, temperature=0.0, sample_index=0)

    record = build_call_record("gpt-4o", job, _context(), _result(), retries=0)

    assert "seed" not in record
    assert "unsupported_sampling" not in record


def test_build_call_record_with_seed_carries_seed_and_unsupported_sampling():
    job = Job(cell=_context().cell, temperature=0.6, sample_index=4, seed=4)
    unsupported = {"temperature": 0.6, "top_p": 0.95, "top_k": 20.0, "presence_penalty": 0.0}

    record = build_call_record(
        "gemini-robotics-er-2-preview", job, _context(), _result(unsupported=unsupported), 0
    )

    assert record["seed"] == 4
    assert record["unsupported_sampling"] == unsupported


def test_build_paced_backends_builds_one_backend_per_seed(monkeypatch):
    built: list[GeminiBackendConfig] = []
    monkeypatch.setattr(
        "scripts.probe_presentation_order.build_backend",
        lambda backend_id, config: built.append(config) or object(),
    )
    jobs = plan_seeded_jobs([_context()], n_seeds=3, temperature=0.6)

    backends = build_paced_backends(
        "gemini", GeminiBackendConfig(), "gemini-robotics-er-2-preview", jobs, _NoPacer()
    )

    assert sorted(backends) == [0, 1, 2]
    assert [config.seed for config in built] == [0, 1, 2]


def test_build_paced_backends_default_path_builds_one_unseeded_backend(monkeypatch):
    built: list[OpenAIBackendConfig] = []
    monkeypatch.setattr(
        "scripts.probe_presentation_order.build_backend",
        lambda backend_id, config: built.append(config) or object(),
    )
    jobs = plan_jobs([_context()], n_greedy=2, n_sampled=2, sampled_temperature=0.6)

    backends = build_paced_backends(
        "openai", OpenAIBackendConfig(), "gpt-4o", jobs, _NoPacer()
    )

    assert list(backends) == [None]
    assert [config.model_id for config in built] == ["gpt-4o"]
    assert not any(hasattr(config, "seed") for config in built)


class _NoPacer:
    def wait(self) -> None:
        return None


class _SlowPacer:
    """Pacer whose wait dominates the call it precedes, as a rate-limited run's does."""

    def wait(self) -> None:
        time.sleep(0.25)


def test_paced_backend_latency_excludes_the_pacer_wait():
    response = BackendResponse(text="{}", backend_id="stub")

    paced = PacedBackend(_StubBackend(response), _SlowPacer())
    timed = paced.analyze(_payload(), ReasonerConfig(backend_id="stub"))

    assert timed.latency_ms is not None
    assert timed.latency_ms < 200


def test_paced_backend_keeps_a_latency_the_backend_reported():
    response = BackendResponse(text="{}", backend_id="stub", latency_ms=42)

    timed = PacedBackend(_StubBackend(response), _SlowPacer()).analyze(
        _payload(), ReasonerConfig(backend_id="stub")
    )

    assert timed.latency_ms == 42


class _StubBackend:
    def __init__(self, response: BackendResponse) -> None:
        self._response = response

    def analyze(self, payload, config) -> BackendResponse:
        return self._response


def _payload() -> PromptPayload:
    return PromptPayload(
        system_prompt="sys",
        user_prompt="user",
        image_path="images/w0p2_eopen.png",
        known_robot_ids=["robot_1", "robot_2"],
    )


def test_summary_temperature_is_the_temperature_for_an_unseeded_record():
    assert summary_temperature({"temperature": 0.0}) == 0.0


def test_summary_temperature_is_seeded_for_a_seeded_record():
    assert summary_temperature({"temperature": 0.6, "seed": 7}) == "seeded"


def _record(seed: int | None, yield_robot: str) -> dict[str, object]:
    record: dict[str, object] = {
        "model": "gemini-robotics-er-2-preview" if seed is not None else "gpt-4o",
        "variant": "w0p2_eopen",
        "presentation_order": "id_asc",
        "obstacle_channel": "off",
        "temperature": 0.6,
        "first_listed_robot": "robot_1",
        "correct_yielder": "robot_2",
        "prompt_sha256": "a" * 64,
        "latency_ms": 1000,
        "error_type": None,
        "decision": {"strategy": "yield", "yield_robot": yield_robot},
    }
    if seed is not None:
        record["seed"] = seed
    return record


def test_summarize_cells_pools_every_seed_of_a_cell_into_one_seeded_row():
    records = [_record(seed, "robot_1") for seed in range(15)]

    rows = summarize_cells(records)

    assert len(rows) == 1
    assert rows[0]["temperature"] == "seeded"
    assert rows[0]["n"] == 15
    assert rows[0]["p_yield_first_listed"] == 1.0


def test_summarize_cells_keeps_seeded_and_temperature_rows_column_compatible():
    rows = summarize_cells([_record(0, "robot_1"), _record(None, "robot_2")])

    assert len(rows) == 2
    assert list(rows[0]) == list(rows[1])


def _scenario(involved: list[str]):
    from types import SimpleNamespace

    return SimpleNamespace(expected_conflict=SimpleNamespace(involved_robots=involved))


def test_first_listed_standoff_robot_is_the_first_listed_robot_with_two_robots():
    pair = _scenario(["robot_1", "robot_2"])
    assert first_listed_standoff_robot(["robot_1", "robot_2"], pair) == "robot_1"
    assert first_listed_standoff_robot(["robot_2", "robot_1"], pair) == "robot_2"


def test_first_listed_standoff_robot_skips_a_queued_third_robot():
    pair = _scenario(["robot_1", "robot_2"])
    assert first_listed_standoff_robot(["robot_3", "robot_2", "robot_1"], pair) == "robot_2"


def test_first_listed_standoff_robot_falls_back_without_a_conflict():
    from types import SimpleNamespace

    assert first_listed_standoff_robot(
        ["robot_2", "robot_1"], SimpleNamespace(expected_conflict=None)
    ) == "robot_2"
