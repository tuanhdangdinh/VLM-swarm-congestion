"""Recorded, classical and replay modes, the response cache, and a CLI smoke run."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from benchmarks.vlm_bench.backends import CachedBackend, RecordedBackend
from benchmarks.vlm_bench.classical_ref import classical_decision, reproduces_recorded
from benchmarks.vlm_bench.run import rebuild_request, replay_items, score_items, write_run
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.prompt_builder import build_prompt_payload
from tests.unit.vlm_bench_fixtures import BUNDLE, DATA, synthetic_items

REPO = Path(__file__).resolve().parents[2]


class _FakeBackend:
    def __init__(self, text: str) -> None:
        self.calls = 0
        self._text = text

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        self.calls += 1
        return BackendResponse(text=self._text, backend_id="fake")


def _payload(tmp_path: Path, user: str = "u") -> PromptPayload:
    image = tmp_path / "img.png"
    image.write_bytes(b"png")
    return PromptPayload(
        system_prompt="s", user_prompt=user, image_path=str(image), known_robot_ids=[]
    )


def test_recorded_mode_end_to_end_summary(tmp_path):
    items = list(synthetic_items().values())
    scores = score_items(items, "recorded")
    summaries = write_run(
        scores, tmp_path / "run.jsonl", tmp_path / "run.md", {"mode": "recorded"}, items
    )
    pooled = summaries["all"]
    assert (pooled.n_items, pooled.n_valid, pooled.n_positive) == (5, 4, 3)
    assert (pooled.feasibility.num, pooled.feasibility.den) == (2, 3)
    assert (pooled.live_reproduction.num, pooled.live_reproduction.den) == (3, 3)
    assert pooled.refusal_histogram == {"ambiguous lane": 1}
    assert (tmp_path / "run.config.json").is_file()
    assert "M3 feasibility" in (tmp_path / "run.md").read_text()


def test_classical_mode_reproduces_live_shadow():
    item = synthetic_items()["aaaa0002"]
    decision = classical_decision(item)
    assert decision["strategy"] == "reroute"
    assert reproduces_recorded(item, decision) is True


def test_classical_mode_scores_every_item():
    scores = score_items(list(synthetic_items().values()), "classical")
    assert len(scores) == 5
    assert all(score.source == "classical" for score in scores)


def test_recorded_backend_returns_stored_text(tmp_path):
    item = synthetic_items()["aaaa0002"]
    response = RecordedBackend(item).analyze(_payload(tmp_path), ReasonerConfig(backend_id="x"))
    assert response.text == item.recorded.raw_text


def test_cached_backend_miss_then_hit(tmp_path):
    fake = _FakeBackend("{}")
    cached = CachedBackend(fake, "fake", "m", tmp_path / "cache")
    config = ReasonerConfig(backend_id="fake")
    first = cached.analyze(_payload(tmp_path), config)
    second = cached.analyze(_payload(tmp_path), config)
    assert (fake.calls, cached.misses, cached.hits) == (1, 1, 1)
    assert first == second


def test_cached_backend_miss_on_changed_prompt(tmp_path):
    fake = _FakeBackend("{}")
    cached = CachedBackend(fake, "fake", "m", tmp_path / "cache")
    config = ReasonerConfig(backend_id="fake")
    cached.analyze(_payload(tmp_path, "a"), config)
    cached.analyze(_payload(tmp_path, "b"), config)
    assert fake.calls == 2


def test_replay_skips_item_when_prompt_hash_differs(tmp_path):
    item = synthetic_items()["aaaa0003"]
    fake = _FakeBackend("{}")
    scores, info = replay_items(
        [item], "gemini", cache_dir=tmp_path, backend_factory=lambda _id, _raw: fake
    )
    assert (scores, fake.calls) == ([], 0)
    assert info["skipped_prompt_mismatch"] == [item.item_id]


def test_replay_baseline_calls_backend_once_then_cache(tmp_path):
    item = synthetic_items()["aaaa0003"]
    rendered = build_prompt_payload(rebuild_request(item, str(tmp_path / "x.png"))).user_prompt
    prompt = item.prompt.model_copy(
        update={"user_sha256": hashlib.sha256(rendered.encode()).hexdigest()}
    )
    item = item.model_copy(update={"prompt": prompt})
    fake = _FakeBackend(json.dumps(item.recorded.decision))
    for _ in range(2):
        scores, info = replay_items(
            [item], "gemini", cache_dir=tmp_path, backend_factory=lambda _id, _raw: fake
        )
    assert fake.calls == 1
    assert (info["cache_hits"], info["cache_misses"]) == (1, 0)
    assert scores[0].strategy == "temporary_wait"
    assert scores[0].note == "image=neutral"


def test_cli_build_and_score_smoke(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            str(REPO / p)
            for p in (".", "ros2_ws/src/swarm_orchestrator", "ros2_ws/src/swarm_execution")
        ),
    }
    items = tmp_path / "items.jsonl"
    cmd = [sys.executable, "-m", "benchmarks.vlm_bench"]
    subprocess.run(
        [*cmd, "build-items", str(BUNDLE), "--mc", str(DATA / "mc_seeds_synth.jsonl"),
         "--out", str(items)],
        cwd=REPO, env=env, check=True, capture_output=True,
    )
    for mode in ("recorded", "classical"):
        subprocess.run(
            [*cmd, "score", "--mode", mode, "--items", str(items),
             "--out", str(tmp_path / f"{mode}.jsonl"), "--summary", str(tmp_path / f"{mode}.md")],
            cwd=REPO, env=env, check=True, capture_output=True,
        )
    lines = (tmp_path / "recorded.jsonl").read_text().splitlines()
    assert len(lines) == 5
    assert (tmp_path / "classical.md").read_text().startswith("# VLM bench run: classical")
