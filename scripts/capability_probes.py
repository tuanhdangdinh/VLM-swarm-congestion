#!/usr/bin/env python3
"""Run the frozen capability-probe battery against one backend (prereg-v2 step 10).

Renders each manifest item (`reasoning.vlm.capability_probes.models.ProbeItem`)
through the existing `VLMBackend` adapters (`reasoning.vlm.backend_factory`),
scores the response against the item's GT-derived correct answer, and writes
a per-item JSONL plus a per-probe-type accuracy summary with Wilson
confidence intervals.

This script is the only part of the battery that calls a backend. Building
and freezing the manifest (`scripts/build_capability_probe_manifest.py`) is
pure log scanning and never touches a backend; this script never re-derives
ground truth, only asks and scores.

Hosted backends (`openai`, `gemini`) are configured exactly as M5 is, from
`config/models.yaml` via `resolve_reasoner_config`/`backend_section` (the
`scripts/probe_presentation_order.py` precedent), so the run sends the PINNED
snapshot ids (`gpt-4o-2024-08-06`, `gemini-robotics-er-2-preview`), never a
backend default alias. Temperature is forced to 0.0 (Gemini's Interactions
API drops it; the drop is recorded per call). Each item gets exactly one
`analyze` call: the reasoner's re-ask and grey-image refusal fallback are
deliberately not applied, so a refusal is scored as a refusal. Every record
carries the configured and the provider-reported served model.

Usage:
    set -a; source .env; set +a
    python scripts/capability_probes.py --backend gemini \\
        --logs-root /path/to/data/logs/vm_runs \\
        --out-dir data/logs/capability_probes/gemini_<stamp> \\
        --min-interval-sec 3

No secrets or base64 image data are ever written to the JSONL or summary;
only the backend's raw assistant text and the parsed/scored outcome.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2  # noqa: E402
import yaml  # noqa: E402

from reasoning.vlm.backend_factory import (  # noqa: E402
    BackendConfig,
    backend_section,
    build_backend,
    describe_effective_sampling,
    resolve_reasoner_config,
)
from reasoning.vlm.capability_probes.answer_parser import parse_probe_answer  # noqa: E402
from reasoning.vlm.capability_probes.grid import draw_grid_overlay  # noqa: E402
from reasoning.vlm.capability_probes.letters import ItemChoices, build_item_choices  # noqa: E402
from reasoning.vlm.capability_probes.manifest_io import (  # noqa: E402
    load_manifest,
    materialize_frame,
    sha256_file,
)
from reasoning.vlm.capability_probes.models import ProbeAnswerRecord, ProbeItem  # noqa: E402
from reasoning.vlm.capability_probes.prompt import (  # noqa: E402
    CAPABILITY_PROBE_PROMPT_VERSION,
    build_capability_probe_prompt_payload,
)
from reasoning.vlm.capability_probes.scorer import score_records  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    GeminiBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
)
from reasoning.vlm.reasoner import is_refusal  # noqa: E402

MODELS_YAML = REPO_ROOT / "config" / "models.yaml"
_BACKEND_CONFIG_TYPES = {"openai": OpenAIBackendConfig, "gemini": GeminiBackendConfig}
# The battery's standing policy: one `analyze` call per item, no re-ask.
RUNNER_MAX_ATTEMPTS = 1
# Errors that mean every remaining call would fail the same way (bad key,
# exhausted credits), so the run aborts instead of scoring dozens of
# `backend_error` rows as wrong answers. HTTP 429 rate limiting is not here:
# it is transient, and pacing (`--min-interval-sec`) is what prevents it.
_FATAL_ERROR_RE = re.compile(
    r"HTTP 401|HTTP 403|API_KEY_INVALID|PERMISSION_DENIED|UNAUTHENTICATED"
    r"|insufficient_quota|credit_balance_exhausted|billing",
    re.I,
)
_UNREPORTED_MODEL = "unreported"


class BatteryAbortedError(RuntimeError):
    """A credentials/quota failure made every remaining call pointless."""


def load_backend_settings(
    backend_id: str, models_yaml: Path = MODELS_YAML
) -> tuple[ReasonerConfig, BackendConfig | None]:
    """Resolve one backend's reasoner and backend config as M5 does, at temperature 0.

    Args:
        backend_id: `"mock"`, `"openai"` or `"gemini"`.
        models_yaml: Path to `config/models.yaml` (unused for `"mock"`).

    Returns:
        `(reasoner_config, backend_config)`; `backend_config` is None for the
        mock, which needs none.

    Raises:
        ValueError: `backend_id` is not one the battery supports.
    """
    if backend_id == "mock":
        return ReasonerConfig(backend_id="mock", temperature=0.0), None
    if backend_id not in _BACKEND_CONFIG_TYPES:
        raise ValueError(f"capability-probe battery does not support backend {backend_id!r}")
    raw_vlm = yaml.safe_load(models_yaml.read_text(encoding="utf-8"))["vlm"]
    reasoner_config = resolve_reasoner_config(raw_vlm, backend_id).model_copy(
        update={"temperature": 0.0}
    )
    backend_config = _BACKEND_CONFIG_TYPES[backend_id](**backend_section(raw_vlm, backend_id))
    return reasoner_config, backend_config


def _image_for_item(
    item: ProbeItem, source_frame: Path, choices: ItemChoices, out_dir: Path
) -> Path:
    """Return the path to send: the source frame, or a grid-overlaid copy."""
    if not item.image_choices:
        return source_frame
    image = cv2.imread(str(source_frame))
    if image is None:
        raise ValueError(f"could not read frame {source_frame} for item {item.item_id!r}")
    overlaid = draw_grid_overlay(image, choices.option_by_letter)
    dest = out_dir / "grids" / f"{item.item_id}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(dest), overlaid):
        raise ValueError(f"could not write grid overlay {dest}")
    return dest


def prepare_item(
    item: ProbeItem, logs_root: Path, out_dir: Path
) -> tuple[ItemChoices, PromptPayload]:
    """Materialize the frame and build the prompt for one item; never swallows errors.

    Deliberately separate from the backend call: a missing or drifted frame,
    or a grid-overlay drawing failure, is a battery-integrity problem, not a
    transient per-call one, so it must stop the whole run rather than be
    scored as if the backend had failed (2026-10-02, fourth correction --
    CLAUDE.md's "do not swallow exceptions silently").

    Args:
        item: The manifest item.
        logs_root: Root the item's frame is materialized relative to.
        out_dir: Where a `locate_robot` item's grid-overlay copy is written.

    Returns:
        `(choices, payload)`.

    Raises:
        FileNotFoundError: The item's frame is missing under `logs_root`.
        ValueError: The frame's content hash no longer matches, or (for a
            `locate_robot` item) the grid overlay could not be drawn/written.
    """
    choices = build_item_choices(item.options, item.correct_answer, item.seed)
    source_frame = materialize_frame(item, logs_root)
    image_path = _image_for_item(item, source_frame, choices, out_dir)
    payload = build_capability_probe_prompt_payload(
        question=item.question,
        choices=choices,
        image_path=str(image_path),
        image_choices=item.image_choices,
        known_robot_ids=[item.reference_robot_id] if item.reference_robot_id else [],
    )
    return choices, payload


def run_item(
    item: ProbeItem,
    choices: ItemChoices,
    payload: PromptPayload,
    backend,
    config: ReasonerConfig,
    configured_model_id: str | None = None,
) -> ProbeAnswerRecord:
    """Call the backend and score one already-prepared item; never raises.

    Args:
        item: The manifest item.
        choices: This item's seeded letter assignment (`prepare_item`).
        payload: This item's rendered prompt (`prepare_item`).
        backend: A constructed `VLMBackend`.
        config: Sampling config for the call (temperature 0 where supported).
        configured_model_id: The model id the backend was built with (the
            pinned snapshot), recorded beside the provider's served model.

    Returns:
        The scored record. Only a `backend.analyze` failure is caught here
        (as `"backend_error"`, with `error_type`/`error_message` set); a
        materialization or prompt-building failure is `prepare_item`'s to
        raise, before this function is ever called for the item.
    """
    valid_letters = sorted(choices.option_by_letter)
    lettering = {
        "configured_model_id": configured_model_id,
        "option_by_letter": dict(choices.option_by_letter),
        "listing_order": list(choices.listing_order),
    }
    try:
        response: BackendResponse = backend.analyze(payload, config)
    except Exception as exc:  # the battery must score every item, never crash on one
        return ProbeAnswerRecord(
            item_id=item.item_id,
            probe_type=item.probe_type,
            backend_id=config.backend_id,
            raw_text=None,
            parsed_letter=None,
            correct_letter=choices.correct_letter,
            correct=False,
            failure_cause="backend_error",
            latency_ms=None,
            attempts=RUNNER_MAX_ATTEMPTS,
            error_type=type(exc).__name__,
            error_message=str(exc),
            **lettering,
        )

    if response.text is not None and is_refusal(response.text):
        # Tagged ahead of the generic parser: a refusal and an unparseable
        # answer are different capability findings (see answer_parser's
        # AnswerFailureCause docstring), and gpt-4o's annotated-frame refusal
        # rate is a known, separately-tracked confound for this project.
        letter, failure_cause = None, "refusal"
    else:
        letter, failure_cause = parse_probe_answer(response.text, valid_letters)
    correct = failure_cause is None and letter == choices.correct_letter
    unsupported = response.raw.get("unsupported_sampling")
    return ProbeAnswerRecord(
        item_id=item.item_id,
        probe_type=item.probe_type,
        # The selector, not `response.backend_id` (which hosted backends set to
        # their model id), so success and error records key the same way.
        backend_id=config.backend_id,
        raw_text=response.text,
        parsed_letter=letter,
        correct_letter=choices.correct_letter,
        correct=correct,
        failure_cause=failure_cause,
        latency_ms=response.latency_ms,
        attempts=RUNNER_MAX_ATTEMPTS,
        served_model=response.served_model,
        token_usage=response.token_usage,
        unsupported_sampling=unsupported if isinstance(unsupported, dict) else None,
        parsed_option=choices.option_by_letter.get(letter) if letter else None,
        **lettering,
    )


def _write_jsonl(records: list[ProbeAnswerRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def run_battery(
    manifest_path: Path,
    backend_id: str,
    logs_root: Path,
    out_dir: Path,
    models_yaml: Path = MODELS_YAML,
    min_interval_sec: float = 0.0,
) -> tuple[list[ProbeAnswerRecord], dict]:
    """Run every manifest item through one backend and score the results.

    Args:
        manifest_path: Path to the frozen manifest JSON.
        backend_id: Selector passed to `reasoning.vlm.backend_factory.build_backend`.
        logs_root: Root the manifest's `frame_relpath` entries resolve against.
        out_dir: Where per-item JSONL, the summary, and grid-overlay copies land.
        models_yaml: Shipped model config the hosted backends are pinned from.
        min_interval_sec: Minimum spacing between call starts, so a run stays
            under the account's rate limit instead of scoring HTTP 429s.

    Returns:
        `(records, summary_dict)`.

    Raises:
        FileNotFoundError: Any item's frame is missing under `logs_root`.
        ValueError: Any frame's content hash has drifted, or a `locate_robot`
            item's grid overlay could not be drawn/written. Raised before any
            backend call is made for *any* item (not just the offending one):
            a battery-integrity problem should stop the run, not silently
            shrink or skew the scored set.
        BatteryAbortedError: A call failed on credentials or exhausted quota;
            the records so far are written to `*_aborted.jsonl` first.
    """
    manifest = load_manifest(manifest_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    prepared = [prepare_item(item, logs_root, out_dir) for item in manifest.items]

    config, backend_config = load_backend_settings(backend_id, models_yaml)
    backend = build_backend(backend_id, backend_config)
    configured_model_id = getattr(backend_config, "model_id", None)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    records: list[ProbeAnswerRecord] = []
    next_start = 0.0
    for item, (choices, payload) in zip(manifest.items, prepared, strict=True):
        delay = next_start - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        next_start = time.monotonic() + min_interval_sec
        record = run_item(item, choices, payload, backend, config, configured_model_id)
        records.append(record)
        print(
            f"{record.item_id} cause={record.failure_cause or 'none'} "
            f"correct={record.correct} served={record.served_model}",
            file=sys.stderr,
        )
        if record.failure_cause == "backend_error" and _FATAL_ERROR_RE.search(
            record.error_message or ""
        ):
            aborted_path = out_dir / f"{backend_id}_{timestamp}_aborted.jsonl"
            _write_jsonl(records, aborted_path)
            raise BatteryAbortedError(
                f"{record.item_id}: {record.error_type}: {(record.error_message or '')[:200]} "
                f"-- aborted after {len(records)} call(s); partial records in {aborted_path}"
            )

    chance_rate_by_item = {item.item_id: 1.0 / len(item.options) for item in manifest.items}
    effective = describe_effective_sampling(config, backend_config).model_copy(
        update={"max_attempts": RUNNER_MAX_ATTEMPTS, "image_fallback_after_attempts": None}
    )
    served_counts = Counter(record.served_model or _UNREPORTED_MODEL for record in records)
    summary = score_records(records, chance_rate_by_item, backend_id, manifest.seed).model_copy(
        update={
            "reasoner_config_effective": effective,
            "served_model_counts": dict(served_counts),
            "manifest_sha256": sha256_file(manifest_path),
            "prompt_version": CAPABILITY_PROBE_PROMPT_VERSION,
        }
    )

    jsonl_path = out_dir / f"{backend_id}_{timestamp}.jsonl"
    _write_jsonl(records, jsonl_path)
    summary_path = out_dir / f"{backend_id}_{timestamp}_summary.json"
    summary_path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")

    result = {
        "jsonl_path": str(jsonl_path),
        "summary_path": str(summary_path),
        **summary.model_dump(),
    }
    return records, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", required=True, help="e.g. mock, openai, gemini")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "reasoning/vlm/capability_probes/manifest_v1.json",
    )
    parser.add_argument("--logs-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--models-yaml", type=Path, default=MODELS_YAML)
    parser.add_argument(
        "--min-interval-sec",
        type=float,
        default=0.0,
        help="minimum spacing between calls (rate-limit pacing, not a retry)",
    )
    args = parser.parse_args()

    start = time.monotonic()
    _, summary = run_battery(
        args.manifest,
        args.backend,
        args.logs_root,
        args.out_dir,
        models_yaml=args.models_yaml,
        min_interval_sec=args.min_interval_sec,
    )
    elapsed = time.monotonic() - start

    print(json.dumps(summary, indent=2))
    print(f"ran {summary['n_items']} items in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
