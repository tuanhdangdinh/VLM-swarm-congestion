"""`--backend mock` end-to-end: materialize, prompt, score, write outputs.

Builds a tiny synthetic manifest and frame under `tmp_path` rather than real
`data/logs/vm_runs` frames (the "no synthetic padding" rule is about the
frozen item set, not about test fixtures).
"""
import json

import cv2
import numpy as np
import pytest

from reasoning.vlm.capability_probes.manifest_io import save_manifest, sha256_file
from reasoning.vlm.capability_probes.models import ProbeItem, ProbeManifest
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    GeminiBackendConfig,
    OpenAIBackendConfig,
    ReasonerConfig,
)
from scripts import capability_probes
from scripts.capability_probes import (
    BatteryAbortedError,
    load_backend_settings,
    prepare_item,
    run_battery,
    run_item,
)

_PINNED_OPENAI = "gpt-4o-2024-08-06"
_PINNED_GEMINI = "gemini-robotics-er-2-preview"


def _write_frame(path, width=120, height=90) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((height, width, 3), 200, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)


def _robot_count_item(frame_sha256: str) -> ProbeItem:
    return ProbeItem(
        item_id="robot_count_000",
        probe_type="robot_count",
        run_id="run_a/ep_1",
        scenario="head_on",
        request_id="req1",
        frame_relpath="run_a/ep_1/frames/req1.png",
        frame_sha256=frame_sha256,
        image_width=120,
        image_height=90,
        sim_time_sec=1.0,
        reference_robot_id=None,
        question="How many robots are visible in the image?",
        options=["1", "2", "3", "4", "5"],
        correct_answer="2",
        image_choices=False,
        seed=111,
        m1_gt_max_disagreement_m=0.0,
    )


def _locate_robot_item(frame_sha256: str) -> ProbeItem:
    return ProbeItem(
        item_id="locate_robot_000",
        probe_type="locate_robot",
        run_id="run_a/ep_1",
        scenario="head_on",
        request_id="req1",
        frame_relpath="run_a/ep_1/frames/req1.png",
        frame_sha256=frame_sha256,
        image_width=120,
        image_height=90,
        sim_time_sec=1.0,
        reference_robot_id="robot_1",
        question="Which lettered grid cell is robot robot_1 in?",
        options=[str(i) for i in range(9)],
        correct_answer="4",
        image_choices=True,
        seed=222,
        m1_gt_max_disagreement_m=0.0,
    )


@pytest.fixture
def logs_root(tmp_path):
    frame_path = tmp_path / "run_a" / "ep_1" / "frames" / "req1.png"
    _write_frame(frame_path)
    return tmp_path, frame_path


class TestRunItemWithAScriptedCorrectAnswer:
    def test_text_choice_item_scores_correct_when_the_backend_answers_right(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item(sha256_file(frame_path))
        choices, payload = prepare_item(item, root, root)
        backend = MockBackend(response_text=f'{{"choice": "{choices.correct_letter}"}}')
        config = ReasonerConfig(backend_id="mock", temperature=0.0)
        record = run_item(item, choices, payload, backend, config)
        assert record.correct is True
        assert record.failure_cause is None
        assert record.parsed_letter == choices.correct_letter

    def test_image_choice_item_draws_a_grid_and_scores_correct(self, logs_root, tmp_path):
        root, frame_path = logs_root
        item = _locate_robot_item(sha256_file(frame_path))
        out_dir = tmp_path / "out"
        choices, payload = prepare_item(item, root, out_dir)
        backend = MockBackend(response_text=f'{{"choice": "{choices.correct_letter}"}}')
        config = ReasonerConfig(backend_id="mock", temperature=0.0)
        record = run_item(item, choices, payload, backend, config)
        assert record.correct is True
        assert (out_dir / "grids" / f"{item.item_id}.png").is_file()

    def test_wrong_letter_scores_incorrect(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item(sha256_file(frame_path))
        choices, payload = prepare_item(item, root, root)
        wrong_letter = next(
            letter for letter in choices.option_by_letter if letter != choices.correct_letter
        )
        backend = MockBackend(response_text=f'{{"choice": "{wrong_letter}"}}')
        config = ReasonerConfig(backend_id="mock", temperature=0.0)
        record = run_item(item, choices, payload, backend, config)
        assert record.correct is False
        assert record.failure_cause is None  # a valid but wrong letter, not a parse failure

    def test_a_refusal_is_tagged_separately_from_a_parse_failure(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item(sha256_file(frame_path))
        choices, payload = prepare_item(item, root, root)
        backend = MockBackend(response_text="I'm sorry, but I can't assist with that request.")
        config = ReasonerConfig(backend_id="mock", temperature=0.0)
        record = run_item(item, choices, payload, backend, config)
        assert record.correct is False
        assert record.failure_cause == "refusal"
        assert record.parsed_letter is None

    def test_a_structured_refusal_is_tagged_as_a_refusal(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item(sha256_file(frame_path))
        choices, payload = prepare_item(item, root, root)

        class _RefusingBackend:
            def analyze(self, payload, config):
                return BackendResponse(
                    text='{"choice": "A"}', backend_id="claude", refusal=True,
                    refusal_category="general_harms",
                )

        config = ReasonerConfig(backend_id="anthropic", temperature=0.0)
        record = run_item(item, choices, payload, _RefusingBackend(), config)
        assert record.failure_cause == "refusal"
        assert record.parsed_letter is None


class TestRunItemBackendFailureHandling:
    def test_a_backend_exception_is_scored_as_backend_error_with_diagnostics(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item(sha256_file(frame_path))
        choices, payload = prepare_item(item, root, root)

        class _ExplodingBackend:
            def analyze(self, payload, config):
                raise ConnectionError("upstream reset the connection")

        config = ReasonerConfig(backend_id="mock", temperature=0.0)
        record = run_item(item, choices, payload, _ExplodingBackend(), config)
        assert record.correct is False
        assert record.failure_cause == "backend_error"
        assert record.error_type == "ConnectionError"
        assert "upstream reset" in record.error_message


class TestPrepareItemFailsLoudly:
    def test_missing_frame_raises_rather_than_being_scored(self, tmp_path):
        # No frame was ever written under tmp_path: a battery-integrity
        # problem, which must stop the run, not silently become a scored
        # "backend_error" record (2026-10-02, fourth correction).
        item = _robot_count_item("a" * 64)
        with pytest.raises(FileNotFoundError):
            prepare_item(item, tmp_path, tmp_path)

    def test_hash_mismatch_raises_rather_than_being_scored(self, logs_root):
        root, frame_path = logs_root
        item = _robot_count_item("a" * 64)  # wrong hash for the frame actually on disk
        with pytest.raises(ValueError, match="hash"):
            prepare_item(item, root, root)


class TestRunBatteryEndToEnd:
    def test_backend_mock_runs_without_crashing_and_writes_outputs(self, logs_root, tmp_path):
        root, frame_path = logs_root
        frame_hash = sha256_file(frame_path)
        manifest = ProbeManifest(
            seed=1, items=[_robot_count_item(frame_hash), _locate_robot_item(frame_hash)]
        )
        manifest_path = tmp_path / "manifest.json"
        save_manifest(manifest, manifest_path)
        out_dir = tmp_path / "out"

        records, summary = run_battery(manifest_path, "mock", root, out_dir)

        assert len(records) == 2
        assert summary["n_items"] == 2
        assert summary["backend_id"] == "mock"
        jsonl_path = summary["jsonl_path"]
        assert jsonl_path.rsplit("/", 1)[-1].startswith("mock_")
        with open(jsonl_path, encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        assert len(lines) == 2
        # The default (unscripted) mock answer is the stage-1 congestion JSON,
        # which never parses as a probe letter -- documents the parse-failure
        # path rather than asserting a specific accuracy.
        assert all(line["failure_cause"] is not None for line in lines)

    def test_a_missing_frame_aborts_the_whole_run_before_any_backend_call(self, tmp_path):
        bogus_item = _robot_count_item("a" * 64)  # no frame written anywhere under tmp_path
        manifest = ProbeManifest(seed=1, items=[bogus_item])
        manifest_path = tmp_path / "manifest.json"
        save_manifest(manifest, manifest_path)
        out_dir = tmp_path / "out"

        with pytest.raises(FileNotFoundError):
            run_battery(manifest_path, "mock", tmp_path, out_dir)
        # No JSONL/summary should exist: the run aborted in the prepare phase.
        assert list(out_dir.glob("*.jsonl")) == []


class _ServedMock(MockBackend):
    """A mock that also reports a served model, token usage and dropped sampling."""

    def __init__(self, served_model, unsupported=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._served_model = served_model
        self._unsupported = unsupported

    def analyze(self, payload, config):
        response = super().analyze(payload, config)
        raw = {"unsupported_sampling": self._unsupported} if self._unsupported else {}
        return response.model_copy(
            update={
                "served_model": self._served_model,
                "token_usage": {"prompt_tokens": 900, "completion_tokens": 8},
                "raw": raw,
            }
        )


class _RaisingBackend:
    def __init__(self, message: str) -> None:
        self.calls = 0
        self._message = message

    def analyze(self, payload, config):
        self.calls += 1
        raise ConnectionError(self._message)


def _two_item_manifest(tmp_path, frame_path):
    frame_hash = sha256_file(frame_path)
    manifest = ProbeManifest(
        seed=1, items=[_robot_count_item(frame_hash), _locate_robot_item(frame_hash)]
    )
    manifest_path = tmp_path / "manifest.json"
    save_manifest(manifest, manifest_path)
    return manifest_path


@pytest.fixture
def captured_build(monkeypatch):
    """Replace the runner's `build_backend`, capturing what it was asked to build."""
    captured: dict = {}

    def install(backend):
        def fake_build_backend(backend_id, backend_config=None):
            captured["backend_id"] = backend_id
            captured["backend_config"] = backend_config
            return backend

        monkeypatch.setattr(capability_probes, "build_backend", fake_build_backend)
        return captured

    return install


class TestLoadBackendSettingsFromShippedConfig:
    def test_openai_resolves_to_the_pinned_snapshot(self):
        _, backend_config = load_backend_settings("openai")
        assert isinstance(backend_config, OpenAIBackendConfig)
        assert backend_config.model_id == _PINNED_OPENAI

    def test_openai_samples_at_temperature_zero(self):
        reasoner_config, _ = load_backend_settings("openai")
        assert reasoner_config.temperature == 0.0
        assert reasoner_config.backend_id == "openai"

    def test_gemini_resolves_to_the_pinned_preview_id(self):
        _, backend_config = load_backend_settings("gemini")
        assert isinstance(backend_config, GeminiBackendConfig)
        assert backend_config.model_id == _PINNED_GEMINI

    def test_gemini_temperature_is_forced_to_zero_over_the_shared_preset(self):
        reasoner_config, _ = load_backend_settings("gemini")
        assert reasoner_config.temperature == 0.0

    def test_mock_needs_no_backend_config(self):
        reasoner_config, backend_config = load_backend_settings("mock")
        assert backend_config is None
        assert reasoner_config.temperature == 0.0

    def test_an_unsupported_backend_is_rejected(self):
        with pytest.raises(ValueError, match="does not support"):
            load_backend_settings("no_such_backend")


class TestRunBatteryModelPinWiring:
    def test_openai_backend_is_built_with_the_pinned_model(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        captured = captured_build(_ServedMock(_PINNED_OPENAI, response_text='{"choice": "A"}'))
        run_battery(_two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out")
        assert captured["backend_id"] == "openai"
        assert captured["backend_config"].model_id == _PINNED_OPENAI

    def test_each_call_is_sent_at_temperature_zero(self, logs_root, tmp_path, captured_build):
        root, frame_path = logs_root
        backend = _ServedMock(_PINNED_OPENAI, response_text='{"choice": "A"}')
        captured_build(backend)
        run_battery(_two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out")
        assert backend.last_config.temperature == 0.0

    def test_records_carry_configured_and_served_model_and_usage(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        captured_build(_ServedMock("gpt-4o-2024-08-06", response_text='{"choice": "A"}'))
        records, _ = run_battery(
            _two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out"
        )
        for record in records:
            assert record.backend_id == "openai"
            assert record.configured_model_id == _PINNED_OPENAI
            assert record.served_model == "gpt-4o-2024-08-06"
            assert record.token_usage == {"prompt_tokens": 900, "completion_tokens": 8}

    def test_summary_records_effective_config_with_the_one_call_policy(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        captured_build(_ServedMock(_PINNED_OPENAI, response_text='{"choice": "A"}'))
        _, summary = run_battery(
            _two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out"
        )
        effective = summary["reasoner_config_effective"]
        assert effective["model_id"] == _PINNED_OPENAI
        assert effective["temperature"] == 0.0
        assert effective["max_attempts"] == 1
        assert effective["image_fallback_after_attempts"] is None
        assert summary["served_model_counts"] == {_PINNED_OPENAI: 2}
        assert summary["prompt_version"] == 1
        assert len(summary["manifest_sha256"]) == 64

    def test_gemini_dropped_sampling_is_recorded_per_call(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        dropped = {"temperature": 0.0, "top_p": 0.95, "top_k": 20, "presence_penalty": 0.0}
        captured = captured_build(
            _ServedMock(None, unsupported=dropped, response_text='{"choice": "A"}')
        )
        records, summary = run_battery(
            _two_item_manifest(tmp_path, frame_path), "gemini", root, tmp_path / "out"
        )
        assert captured["backend_config"].model_id == _PINNED_GEMINI
        assert all(record.unsupported_sampling == dropped for record in records)
        assert summary["served_model_counts"] == {"unreported": 2}

    def test_parsed_option_and_lettering_are_recorded(self, logs_root, tmp_path, captured_build):
        root, frame_path = logs_root
        captured_build(_ServedMock(_PINNED_OPENAI, response_text='{"choice": "B"}'))
        records, _ = run_battery(
            _two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out"
        )
        for record in records:
            assert record.parsed_option == record.option_by_letter["B"]
            assert sorted(record.listing_order) == sorted(record.option_by_letter)


class TestRunBatteryAbortsOnFatalBackendErrors:
    def test_exhausted_quota_aborts_after_the_first_call(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        backend = _RaisingBackend('OpenAI returned HTTP 429: {"code": "insufficient_quota"}')
        captured_build(backend)
        out_dir = tmp_path / "out"
        with pytest.raises(BatteryAbortedError, match="insufficient_quota"):
            run_battery(_two_item_manifest(tmp_path, frame_path), "openai", root, out_dir)
        assert backend.calls == 1
        assert len(list(out_dir.glob("*_aborted.jsonl"))) == 1
        assert list(out_dir.glob("*_summary.json")) == []

    def test_a_transient_rate_limit_is_scored_not_aborted(
        self, logs_root, tmp_path, captured_build
    ):
        root, frame_path = logs_root
        backend = _RaisingBackend("OpenAI returned HTTP 429: rate_limit_exceeded")
        captured_build(backend)
        records, _ = run_battery(
            _two_item_manifest(tmp_path, frame_path), "openai", root, tmp_path / "out"
        )
        assert backend.calls == 2
        assert all(record.failure_cause == "backend_error" for record in records)
