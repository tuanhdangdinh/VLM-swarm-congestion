#!/usr/bin/env python3
"""One minimal real call to a configured VLM backend arm, through the backend factory.

The registered backend-validation standard (model-wiring ruling, 2026-10-06)
opens every new arm with this preflight: the arm is resolved from
`config/models.yaml` exactly as M5 resolves it (`backend_adapter`,
`load_backend_config`, `resolve_reasoner_config`), one neutral-grey image plus
a one-line JSON instruction is sent, and the served model, token usage and
the parsed reply are printed. With `--list-models`, a hosted OpenAI-compatible
or Anthropic arm's configured `model_id` is also checked against the
provider's live `GET /models` listing (the pin must be served, not assumed).

Secrets: the key is read by the adapter from the env var its section names;
it is never printed, and the listing request's headers are never echoed.

Usage:
    set -a; source .env; set +a
    python scripts/preflight_backend.py --backend openai_gpt51 --list-models
    python scripts/preflight_backend.py --backend llama_server_qwen3vl --two-images
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import requests
import yaml
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reasoning.vlm.backend_factory import (  # noqa: E402
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.models import PromptPayload  # noqa: E402

_LIST_TIMEOUT_SEC = 30


def list_served_models(adapter: str, base_url: str, api_key_env: str | None) -> list[str]:
    """Return the model ids a provider's or local server's model listing names.

    Args:
        adapter: "openai" (any OpenAI-compatible provider), "anthropic",
            "gemini" (`GET /models`, ids without the `models/` prefix) or
            "llama_server" (a local OpenAI-compatible server, no key).
        base_url: The arm's configured base URL.
        api_key_env: Name of the env var holding the key; None for a local server.

    Returns:
        Every listed model id (all pages for Anthropic and Gemini).

    Raises:
        ValueError: The key is not set, or the adapter has no listing here.
        ConnectionError: The listing request failed.
    """
    headers: dict[str, str] = {}
    if adapter != "llama_server":
        key = os.environ.get(api_key_env or "", "").strip()
        if not key:
            raise ValueError(f"{api_key_env} is not set in the environment")
        if adapter == "openai":
            headers = {"Authorization": f"Bearer {key}"}
        elif adapter == "anthropic":
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
        elif adapter == "gemini":
            headers = {"x-goog-api-key": key}
        else:
            raise ValueError(f"no model listing for adapter {adapter!r}")
    ids: list[str] = []
    params: dict[str, str] = {"pageSize": "1000"} if adapter == "gemini" else {}
    while True:
        resp = requests.get(
            f"{base_url.rstrip('/')}/models",
            headers=headers,
            params=params,
            timeout=_LIST_TIMEOUT_SEC,
        )
        if resp.status_code >= 400:
            raise ConnectionError(f"model listing HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if adapter == "gemini":
            ids.extend(
                entry["name"].removeprefix("models/")
                for entry in data.get("models", [])
                if "name" in entry
            )
            if data.get("nextPageToken"):
                params = {"pageSize": "1000", "pageToken": data["nextPageToken"]}
                continue
            return ids
        ids.extend(entry["id"] for entry in data.get("data", []) if "id" in entry)
        if adapter == "anthropic" and data.get("has_more") and data.get("last_id"):
            params = {"after_id": data["last_id"]}
            continue
        return ids


def _grey_png(path: Path, size: tuple[int, int]) -> str:
    Image.new("RGB", size, (128, 128, 128)).save(path, format="PNG")
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, help="a config/models.yaml backend section")
    parser.add_argument("--models-yaml", type=Path, default=REPO_ROOT / "config" / "models.yaml")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="also check model_id against the provider's live GET /models listing",
    )
    parser.add_argument(
        "--two-images",
        action="store_true",
        help="send a second (zoom-tile-sized) image after the frame",
    )
    args = parser.parse_args()

    vlm = yaml.safe_load(args.models_yaml.read_text(encoding="utf-8"))["vlm"]
    adapter = backend_adapter(vlm, args.backend)
    reasoner_config = resolve_reasoner_config(vlm, args.backend)
    backend_config = load_backend_config(vlm, args.backend)
    effective = describe_effective_sampling(reasoner_config, backend_config)
    print("backend", args.backend, "adapter", adapter)
    print("effective", json.dumps(effective.model_dump(mode="json"), sort_keys=True))

    if args.list_models:
        ids = list_served_models(
            adapter, backend_config.base_url, getattr(backend_config, "api_key_env", None)
        )
        listed = backend_config.model_id in ids
        print("listing_count", len(ids), "model_id_listed", listed)
        if not listed:
            near = sorted(i for i in ids if backend_config.model_id.split("-")[0] in i)
            print("listing_near_matches", near[:20])

    with tempfile.TemporaryDirectory(prefix="preflight-") as tmp:
        frame = _grey_png(Path(tmp) / "frame.png", (1280, 960))
        extra = [_grey_png(Path(tmp) / "zoom.png", (640, 480))] if args.two_images else []
        prompt = (
            'Reply with exactly one JSON object {"ok": true, "images": N}, where N is '
            "the number of images you were shown. No other text."
        )
        payload = PromptPayload(
            system_prompt="You are a test endpoint. Reply with a single JSON object only.",
            user_prompt=prompt,
            image_path=frame,
            known_robot_ids=["robot_1"],
            extra_image_paths=extra,
        )
        backend = build_backend(adapter, backend_config)
        response = backend.analyze(payload, reasoner_config)

    text = response.text.strip()
    parsed: dict | None = None
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        parsed = json.loads(text[start:end])
    except ValueError as exc:
        print("parse_error", type(exc).__name__)
    print("served_model", response.served_model, "refusal", response.refusal)
    print("token_usage", response.token_usage)
    print("text_head", repr(text[:120]))
    print("parsed", parsed)
    ok = isinstance(parsed, dict) and parsed.get("ok") is True and not response.refusal
    print("PREFLIGHT", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
