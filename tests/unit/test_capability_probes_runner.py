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
from reasoning.vlm.models import ReasonerConfig
from scripts.capability_probes import prepare_item, run_battery, run_item


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
