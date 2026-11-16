"""Bench backends behind the `VLMBackend` protocol: recorded answers and a response cache.

No live backend is wired here. `replay` builds one by id through the
production `build_backend` and wraps it in `CachedBackend`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from benchmarks.vlm_bench.models import BenchItem
from reasoning.vlm.backend_base import VLMBackend
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

DEFAULT_CACHE_DIR = Path("data/bench/cache")


class RecordedBackend:
    """Answers every call with one item's stored raw text (zero network)."""

    def __init__(self, item: BenchItem) -> None:
        """Bind the backend to one item.

        Args:
            item: The item whose `recorded.raw_text` is returned.
        """
        self._item = item

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return the recorded answer.

        Args:
            payload: Ignored; the answer does not depend on it.
            config: Ignored.

        Returns:
            The recorded text, tokens and latency.

        Raises:
            ValueError: When the item has no recorded text.
        """
        text = self._item.recorded.raw_text
        if text is None:
            raise ValueError(f"{self._item.item_id}: no recorded raw_text")
        return BackendResponse(
            text=text,
            backend_id=self._item.recorded.backend_id or "recorded",
            latency_ms=self._item.recorded.latency_ms,
            token_usage=self._item.recorded.token_usage,
            served_model=self._item.recorded.model_id,
        )


def _file_sha(path: str) -> str:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else f"missing:{path}"


def cache_key(
    backend_id: str, model_id: str | None, payload: PromptPayload, config: ReasonerConfig
) -> str:
    """Content hash of one call: backend, model, prompts, image bytes and sampling.

    Args:
        backend_id: The configured backend id.
        model_id: The pinned model id (None when the adapter has none).
        payload: The rendered payload.
        config: The reasoner config (sampling fields enter the key).

    Returns:
        The SHA-256 hex key.
    """
    blob = {
        "backend_id": backend_id,
        "model_id": model_id,
        "system": payload.system_prompt,
        "user": payload.user_prompt,
        "images": [_file_sha(p) for p in [payload.image_path, *payload.extra_image_paths]],
        "config": config.model_dump(mode="json", exclude={"timeout_sec"}),
    }
    return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()


class CachedBackend:
    """Wraps any `VLMBackend`; identical calls are answered from disk.

    Re-asks are separate keys (their user prompt differs), so a cached run
    replays the retry sequence exactly.
    """

    def __init__(
        self,
        inner: VLMBackend,
        backend_id: str,
        model_id: str | None,
        cache_dir: Path = DEFAULT_CACHE_DIR,
    ) -> None:
        """Wrap a backend.

        Args:
            inner: The backend called on a miss.
            backend_id: The configured backend id (part of the key).
            model_id: The pinned model id (part of the key).
            cache_dir: Where responses are stored, one JSON file per key.
        """
        self._inner = inner
        self._backend_id = backend_id
        self._model_id = model_id
        self._dir = Path(cache_dir)
        self.hits = 0
        self.misses = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return the cached response, or call the inner backend and store it.

        Args:
            payload: The rendered payload.
            config: The reasoner config.

        Returns:
            The backend response.
        """
        key = cache_key(self._backend_id, self._model_id, payload, config)
        path = self._dir / key[:2] / f"{key}.json"
        if path.is_file():
            self.hits += 1
            return BackendResponse.model_validate_json(path.read_text())
        self.misses += 1
        response = self._inner.analyze(payload, config)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.model_dump_json())
        return response
