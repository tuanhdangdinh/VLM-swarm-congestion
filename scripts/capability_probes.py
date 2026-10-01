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

Usage:
    python scripts/capability_probes.py --backend mock \\
        --manifest reasoning/vlm/capability_probes/manifest_v1.json \\
        --logs-root /path/to/data/logs/vm_runs \\
        --out-dir /tmp/capability_probe_run

No secrets or base64 image data are ever written to the JSONL or summary;
only the backend's raw assistant text and the parsed/scored outcome.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2  # noqa: E402

from reasoning.vlm.backend_factory import build_backend  # noqa: E402
from reasoning.vlm.capability_probes.answer_parser import parse_probe_answer  # noqa: E402
from reasoning.vlm.capability_probes.grid import draw_grid_overlay  # noqa: E402
from reasoning.vlm.capability_probes.letters import ItemChoices, build_item_choices  # noqa: E402
from reasoning.vlm.capability_probes.manifest_io import (  # noqa: E402
    load_manifest,
    materialize_frame,
)
from reasoning.vlm.capability_probes.models import ProbeAnswerRecord, ProbeItem  # noqa: E402
from reasoning.vlm.capability_probes.prompt import (  # noqa: E402
    build_capability_probe_prompt_payload,
)
from reasoning.vlm.capability_probes.scorer import score_records  # noqa: E402
from reasoning.vlm.models import BackendResponse, ReasonerConfig  # noqa: E402


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


def run_item(
    item: ProbeItem,
    backend,
    config: ReasonerConfig,
    logs_root: Path,
    out_dir: Path,
) -> ProbeAnswerRecord:
    """Materialize, prompt, call the backend, and score one item; never raises.

    Args:
        item: The manifest item.
        backend: A constructed `VLMBackend`.
        config: Sampling config for the call (temperature 0 where supported).
        logs_root: Root the item's frame is materialized relative to.
        out_dir: Where a `locate_robot` item's grid-overlay copy is written.

    Returns:
        The scored record. A materialization, drawing, or backend failure is
        captured as a `"backend_error"` record, never raised past this call.
    """
    choices = build_item_choices(item.options, item.correct_answer, item.seed)
    valid_letters = sorted(choices.option_by_letter)
    try:
        source_frame = materialize_frame(item, logs_root)
        image_path = _image_for_item(item, source_frame, choices, out_dir)
        payload = build_capability_probe_prompt_payload(
            question=item.question,
            choices=choices,
            image_path=str(image_path),
            image_choices=item.image_choices,
            known_robot_ids=[item.reference_robot_id] if item.reference_robot_id else [],
        )
        response: BackendResponse = backend.analyze(payload, config)
    except Exception:  # the battery must score every item, never crash on one
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
            attempts=1,
        )

    letter, failure_cause = parse_probe_answer(response.text, valid_letters)
    correct = failure_cause is None and letter == choices.correct_letter
    return ProbeAnswerRecord(
        item_id=item.item_id,
        probe_type=item.probe_type,
        backend_id=response.backend_id,
        raw_text=response.text,
        parsed_letter=letter,
        correct_letter=choices.correct_letter,
        correct=correct,
        failure_cause=failure_cause,
        latency_ms=response.latency_ms,
        attempts=1,
    )


def run_battery(
    manifest_path: Path, backend_id: str, logs_root: Path, out_dir: Path
) -> tuple[list[ProbeAnswerRecord], dict]:
    """Run every manifest item through one backend and score the results.

    Args:
        manifest_path: Path to the frozen manifest JSON.
        backend_id: Selector passed to `reasoning.vlm.backend_factory.build_backend`.
        logs_root: Root the manifest's `frame_relpath` entries resolve against.
        out_dir: Where per-item JSONL, the summary, and grid-overlay copies land.

    Returns:
        `(records, summary_dict)`.
    """
    manifest = load_manifest(manifest_path)
    backend = build_backend(backend_id)
    config = ReasonerConfig(backend_id=backend_id, temperature=0.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[ProbeAnswerRecord] = []
    for item in manifest.items:
        records.append(run_item(item, backend, config, logs_root, out_dir))

    chance_rate_by_item = {item.item_id: 1.0 / len(item.options) for item in manifest.items}
    summary = score_records(records, chance_rate_by_item, backend_id, manifest.seed)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    jsonl_path = out_dir / f"{backend_id}_{timestamp}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")
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
    args = parser.parse_args()

    start = time.monotonic()
    _, summary = run_battery(args.manifest, args.backend, args.logs_root, args.out_dir)
    elapsed = time.monotonic() - start

    print(json.dumps(summary, indent=2))
    print(f"ran {summary['n_items']} items in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
