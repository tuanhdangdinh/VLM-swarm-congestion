#!/usr/bin/env python3
"""Standalone, one-call probe for Gemini Robotics-ER 2 via the Interactions API.

Answers the single open empirical question gating
`docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`:
given the real M2 prompt (`reasoning.vlm.prompt_builder`) plus one scene
image, sent to `gemini-robotics-er-2-preview` on the Interactions API with
`reasoning/schemas/vlm_decision.schema.json` as `response_format`, does the
response's extracted text pass the existing `reasoning.vlm.output_parser`?

This is not a pytest test and is not wired into `make test`; see
`tests/unit/test_probe_gemini_er2.py` for the mocked-HTTP unit tests of the
pure helpers (request-body construction, response-text extraction,
redaction). Every live invocation of this script (i.e. without --dry-run)
makes at most one billable call: a 401/403 on the first auth header
triggers exactly one fallback attempt with the alternate header (rejected
auth is not billed by the provider), never a retry loop.

Usage:
    python scripts/probe_gemini_er2.py --dry-run
    GEMINI_API_KEY=... python scripts/probe_gemini_er2.py
    GEMINI_API_KEY=... python scripts/probe_gemini_er2.py --no-schema --thinking-level high
    GEMINI_API_KEY=... python scripts/probe_gemini_er2.py --image data/some_scene.png

The key is never accepted as a CLI argument (it would appear in `ps aux`)
and is read only from GEMINI_API_KEY, falling back to GOOGLE_API_KEY.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# scripts/ is not installed as a package; running this file directly puts
# scripts/ (not the repo root) on sys.path[0], so `reasoning` would not
# resolve without this. Mirrors tests/unit/test_aruco_parity.py's pattern.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import requests  # noqa: E402

from reasoning.schemas import load_schema  # noqa: E402
from reasoning.vlm.errors import VLMOutputParseError  # noqa: E402
from reasoning.vlm.models import ReasonerRequest, RobotStateInput  # noqa: E402
from reasoning.vlm.output_parser import parse_decision_text, parse_vlm_decision  # noqa: E402
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_MODEL = "gemini-robotics-er-2-preview"
_KEY_ENV_VARS = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
_DECISION_SCHEMA_NAME = "vlm_decision"


def resolve_api_key() -> tuple[str | None, str]:
    """Read the Gemini API key from the environment, never from argv.

    Returns:
        A `(key, env_var_name)` pair. `key` is `None` and `env_var_name` is
        `""` when neither `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set.
    """
    for env_name in _KEY_ENV_VARS:
        value = os.environ.get(env_name)
        if value:
            return value, env_name
    return None, ""


def describe_key(key: str) -> str:
    """Build a safe, non-secret descriptor of an API key for logging.

    Args:
        key: The raw API key value.

    Returns:
        A string carrying only the key's length and first 3 characters,
        never enough to reconstruct or narrow down the key.
    """
    return f"length={len(key)} prefix={key[:3]!r}"


def redact_secret(text: str, secret: str | None) -> str:
    """Replace every occurrence of `secret` in `text` with a redaction marker.

    Args:
        text: Text that may contain the secret (e.g. an HTTP error body).
        secret: The literal secret value to scrub, or `None`/empty to skip.

    Returns:
        `text` with every occurrence of `secret` replaced by
        `***REDACTED***`; unchanged if `secret` is falsy.
    """
    if not secret:
        return text
    return text.replace(secret, "***REDACTED***")


def build_content_parts(user_text: str, image_b64: str, mime_type: str) -> list[dict[str, Any]]:
    """Build the Interactions API `input` array for one text+image turn.

    Args:
        user_text: Rendered user prompt text.
        image_b64: Base64-encoded image bytes (no `data:` URL prefix).
        mime_type: Image MIME type, e.g. `"image/png"`.

    Returns:
        A list of `Content` items: one `text` item, one `image` item.
    """
    return [
        {"type": "text", "text": user_text},
        {"type": "image", "data": image_b64, "mime_type": mime_type},
    ]


def build_request_body(
    model: str,
    system_instruction: str,
    user_text: str,
    image_b64: str,
    mime_type: str,
    thinking_level: str,
    include_schema: bool,
    schema: dict[str, Any] | None,
) -> dict[str, Any]:
    """Construct the Interactions API request body (no auth, ever, in the body).

    The Gemini API key is a header concern (`x-goog-api-key` or
    `Authorization: Bearer`, see `send_request`); it never belongs in the
    JSON body, so this function does not accept it as a parameter.

    Args:
        model: Model id, e.g. `gemini-robotics-er-2-preview`.
        system_instruction: Rendered system prompt (plain string field).
        user_text: Rendered user prompt text.
        image_b64: Base64-encoded scene image bytes.
        mime_type: Image MIME type.
        thinking_level: `"low"` or `"high"`.
        include_schema: Whether to attach `response_format` with `schema`.
        schema: The JSON Schema to attach when `include_schema` is true.

    Returns:
        The JSON-serializable request body.
    """
    body: dict[str, Any] = {
        "model": model,
        "system_instruction": system_instruction,
        "input": build_content_parts(user_text, image_b64, mime_type),
        "generation_config": {"thinking_level": thinking_level},
    }
    if include_schema:
        body["response_format"] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        }
    return body


def elide_image_data(body: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `body` with base64 image data replaced by its length.

    Args:
        body: A request body built by `build_request_body`.

    Returns:
        A deep copy of `body` safe to print: every `input` item of type
        `"image"` has its `data` field replaced with a length marker.
    """
    elided = json.loads(json.dumps(body))
    for item in elided.get("input", []):
        if item.get("type") == "image" and "data" in item:
            item["data"] = f"<elided, {len(item['data'])} base64 chars>"
    return elided


def extract_response_text(data: dict[str, Any]) -> str:
    """Extract and concatenate all response text from an Interactions API body.

    Walks every step in `steps[]` and every content entry in each step's
    `content[]`, keeping only entries whose `type` is `"text"`. A step with
    no text content (e.g. a `function_call` step) contributes nothing and is
    silently skipped rather than raising.

    Args:
        data: Parsed JSON response body from `POST /v1beta/interactions`.

    Returns:
        The concatenated text of every text content entry, in document order.

    Raises:
        RuntimeError: If no step contains any text content.
    """
    texts: list[str] = []
    for step in data.get("steps", []) or []:
        for entry in step.get("content", []) or []:
            if entry.get("type") == "text" and "text" in entry:
                texts.append(entry["text"])
    if not texts:
        raise RuntimeError("Interactions API response contained no text content in any step.")
    return "".join(texts)


def extract_usage(data: dict[str, Any]) -> dict[str, Any] | None:
    """Extract token usage from an Interactions API response, if present.

    The exact usage field name is not confirmed by the design doc's source
    facts, so both plausible keys are checked.

    Args:
        data: Parsed JSON response body.

    Returns:
        The usage mapping under `usage` or `usage_metadata`, or `None`.
    """
    for key in ("usage", "usage_metadata"):
        value = data.get(key)
        if value:
            return value
    return None


def build_reasoner_request(image_path: Path) -> ReasonerRequest:
    """Build the real M2 request the probe sends: a two-robot head-on scene.

    Reuses the project's actual `ReasonerRequest`/`RobotStateInput` contracts
    and `build_prompt_payload` so the probe exercises the same prompt M2
    sends in production, not an invented one.

    Args:
        image_path: Path to the scene image to reference.

    Returns:
        A `ReasonerRequest` with two robots in a head-on configuration.
    """
    return ReasonerRequest(
        request_id="probe-gemini-er2",
        image_path=str(image_path),
        frame_id="probe_frame",
        stamp=0.0,
        robot_states=[
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0, status="STOPPED"),
            RobotStateInput(
                robot_id="robot_2", x=1.0, y=0.0, theta=3.14159, status="STOPPED"
            ),
        ],
    )


def find_repo_scene_image(repo_root: Path) -> Path | None:
    """Search `data/` and `tests/` for a committed scene or annotated frame.

    Args:
        repo_root: Repository root to search under.

    Returns:
        The first matching image path (preferring names containing "scene",
        "annotated", or "frame"), or `None` if no image file is found.
    """
    candidates: list[Path] = []
    for base_name in ("data", "tests"):
        base = repo_root / base_name
        if not base.is_dir():
            continue
        for pattern in ("*.png", "*.jpg", "*.jpeg"):
            candidates.extend(sorted(base.rglob(pattern)))
    if not candidates:
        return None
    preferred = [
        path
        for path in candidates
        if any(tag in path.name.lower() for tag in ("scene", "annotated", "frame"))
    ]
    return (preferred or candidates)[0]


def synthesize_scene_image(path: Path) -> None:
    """Write a plain 640x480 RGB placeholder scene frame to `path`.

    Used only when no committed scene/annotated frame exists under `data/`
    or `tests/`. Two filled circles stand in for the two robots in
    `build_reasoner_request` so the image is not a blank rectangle.

    Args:
        path: Destination PNG path.
    """
    frame_rgb = np.full((480, 640, 3), 220, dtype=np.uint8)
    cv2.circle(frame_rgb, (200, 240), 20, (40, 90, 200), thickness=-1)
    cv2.circle(frame_rgb, (440, 240), 20, (200, 90, 40), thickness=-1)
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), frame_bgr)


def resolve_image_path(
    cli_image: Path | None, repo_root: Path, scratch_dir: Path
) -> tuple[Path, str]:
    """Resolve which scene image to send, per the probe's precedence rules.

    Precedence: an explicit `--image` path, then a committed scene/annotated
    frame under `data/` or `tests/`, then a synthesized placeholder.

    Args:
        cli_image: Path passed via `--image`, if any.
        repo_root: Repository root to search under.
        scratch_dir: Writable directory for a synthesized placeholder image.

    Returns:
        A `(path, note)` pair; `note` is a human-readable line describing
        which source was used, for the probe's report.
    """
    if cli_image is not None:
        return cli_image, f"image source: --image {cli_image}"
    found = find_repo_scene_image(repo_root)
    if found is not None:
        return found, f"image source: repo image at {found.relative_to(repo_root)}"
    synth_path = scratch_dir / "probe_gemini_er2_synthetic_scene.png"
    synthesize_scene_image(synth_path)
    return synth_path, (
        "image source: no committed scene/annotated frame found under data/ or "
        "tests/; synthesized a plain 640x480 RGB placeholder"
    )


def send_request(
    body: dict[str, Any], api_key: str, timeout_sec: float
) -> tuple[requests.Response, str]:
    """POST one interaction, trying the documented Gemini key header first.

    On a 401/403 from `x-goog-api-key`, retries exactly once with
    `Authorization: Bearer`. Any other status is returned as-is without a
    second call, preserving the at-most-one-billable-call property (a
    rejected-auth request is not billed).

    Args:
        body: Request body from `build_request_body`.
        api_key: The raw API key (never logged).
        timeout_sec: Per-request timeout in seconds.

    Returns:
        The final `requests.Response` and the name of the auth header that
        produced it.
    """
    goog_headers = {"x-goog-api-key": api_key, "content-type": "application/json"}
    resp = requests.post(INTERACTIONS_URL, json=body, headers=goog_headers, timeout=timeout_sec)
    if resp.status_code not in (401, 403):
        return resp, "x-goog-api-key"
    bearer_headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
    resp = requests.post(INTERACTIONS_URL, json=body, headers=bearer_headers, timeout=timeout_sec)
    return resp, "Authorization: Bearer"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--image", type=Path, default=None, help="Scene image to send (overrides repo search)."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Interactions API model id.")
    parser.add_argument(
        "--thinking-level",
        choices=["low", "high"],
        default="low",
        help="generation_config.thinking_level (default: low).",
    )
    parser.add_argument(
        "--schema",
        dest="include_schema",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Attach reasoning/schemas/vlm_decision.schema.json as response_format (default: on).",
    )
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="Per-request timeout in seconds."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request body and exit without any network call or API key.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the probe: build the real prompt, call the Interactions API once, report.

    Args:
        argv: Command-line arguments, or `None` to use `sys.argv[1:]`.

    Returns:
        Process exit code: 0 on success (including a successful `--dry-run`),
        1 on an HTTP/transport/no-text failure, 2 if no API key is set.
    """
    args = _parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="probe_gemini_er2_") as tmp_dir:
        image_path, image_note = resolve_image_path(args.image, REPO_ROOT, Path(tmp_dir))
        request = build_reasoner_request(image_path)
        prompt = build_prompt_payload(request)

        suffix = Path(image_path).suffix.lower()
        mime_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
        schema = load_schema(_DECISION_SCHEMA_NAME) if args.include_schema else None

        body = build_request_body(
            model=args.model,
            system_instruction=prompt.system_prompt,
            user_text=prompt.user_prompt,
            image_b64=image_b64,
            mime_type=mime_type,
            thinking_level=args.thinking_level,
            include_schema=args.include_schema,
            schema=schema,
        )

        if args.dry_run:
            print(image_note)
            print("DRY RUN: no network call made, no API key read or required.")
            print(json.dumps(elide_image_data(body), indent=2))
            return 0

        print(image_note)
        api_key, key_env_used = resolve_api_key()
        if api_key is None:
            print(
                "ERROR: set GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment.",
                file=sys.stderr,
            )
            return 2
        print(f"api key: {describe_key(api_key)} (from {key_env_used})")

        start = time.monotonic()
        try:
            resp, auth_used = send_request(body, api_key, timeout_sec=args.timeout)
        except requests.exceptions.RequestException as exc:
            print(f"ERROR: request failed: {type(exc).__name__}", file=sys.stderr)
            return 1
        latency_ms = int((time.monotonic() - start) * 1000)

        print(f"auth header used: {auth_used}")
        print(f"HTTP status: {resp.status_code}")
        print(f"latency_ms: {latency_ms}")

        if not 200 <= resp.status_code < 300:
            print(f"response body: {redact_secret(resp.text, api_key)[:2000]}")
            return 1

        data = resp.json()
        usage = extract_usage(data)
        print(f"token usage: {usage if usage is not None else 'not returned'}")

        try:
            text = extract_response_text(data)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print("response text:")
        print(text)

        tolerant_ok = True
        strict_ok = True
        decision = None
        try:
            decision = parse_decision_text(text)
        except VLMOutputParseError as exc:
            tolerant_ok = False
            print(f"parse_decision_text (tolerant) rejected output: {exc}")
        try:
            parse_vlm_decision(text)
        except VLMOutputParseError as exc:
            strict_ok = False
            print(f"parse_vlm_decision (strict jsonschema) rejected output: {exc}")

        print(f"tolerant parser (parse_decision_text) accepted: {tolerant_ok}")
        print(f"strict schema parser (parse_vlm_decision) accepted: {strict_ok}")
        if decision is not None:
            print(
                f"decision: congestion_detected={decision.congestion_detected} "
                f"type={decision.type} strategy={decision.strategy}"
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
