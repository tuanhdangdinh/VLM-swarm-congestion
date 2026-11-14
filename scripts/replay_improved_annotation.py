"""Improved-annotation replay: does a legible frame let a model pick the yielder?

Pre-registered in docs/superpowers/specs/2026-11-14-improved-annotation-replay-design.md.
Twenty-four head-on standoff scenes (12 per blocked side) are re-sent through the
production `build_reasoner_request` / `Reasoner` path with obstacle text OFF,
original robot IDs and prompt v1, under both listing orders. Factors:

* image: ``C_ref`` (annotated frame), ``D_ref`` (grey), ``L2`` (legible labels +
  fixed crop/upscale; Type L), ``K1`` (L2 + obstacle outline; Type K);
* prompt line (``+P``): one neutral sentence appended to the head-on Guidance
  bullet, inserted into the payload the backend receives.

Reuses the recording proxy, cost and probe helpers of `scripts/replay_swapped_ids.py`
(unmodified). Every row records UTC timestamps, its shuffled sequence index and the
seed, the served model per attempt, the effective config, and hashes of the image
and of the prompt actually sent. No base64 image and no key material is stored.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (REPO_ROOT, REPO_ROOT / "ros2_ws/src/swarm_orchestrator", REPO_ROOT / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    RobotPresentationOrder,
)
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402
from scripts.render_annotation_variants import (  # noqa: E402
    ORIGINAL_12,
    load_scenes,
    md5_bytes,
    md5_file,
)
from scripts.replay_live_decisions import (  # noqa: E402
    Artifact,
    reconstruct_request,
    sha256_text,
)
from scripts.replay_swapped_ids import (  # noqa: E402
    DEFAULT_PROMPT_TOKENS_BOUND,
    LedgerProxy,
    _named,
    append_jsonl,
    attempt1_decision,
    git_commit,
    load_jsonl,
    load_model,
    make_backend,
    probe_provider,
    row_cost,
    worst_attempt_usd,
)

OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-improved-annotation-replay"

PROMPT_LINE = "A robot that backs up needs free floor behind it."
# The line is appended, after one space, to the end of the head-on Guidance bullet,
# right after the definition of the two back-up strategies.
PROMPT_LINE_ANCHOR = 'strategy="reverse" (both back up to clear).'

# cell -> (image variant, prompt line on)
CELL_SPECS: dict[str, tuple[str, bool]] = {
    "L2": ("L2", False),
    "D_ref": ("grey", False),
    "L2+P": ("L2", True),
    "D_ref+P": ("grey", True),
    "C_ref": ("C_ref", False),
    "K1": ("K1", False),
    "C_ref+P": ("C_ref", True),
    "K1+P": ("K1", True),
}
PRIORITY: tuple[str, ...] = tuple(CELL_SPECS)
# K1+P is cut before any call (design, "Budget"): the full set exceeds ER-2's cap.
PLANNED_CELLS: tuple[str, ...] = PRIORITY[:7]
CONTROL_OF: dict[str, str] = {
    "L2": "D_ref",
    "C_ref": "D_ref",
    "K1": "D_ref",
    "L2+P": "D_ref+P",
    "C_ref+P": "D_ref+P",
    "K1+P": "D_ref+P",
}
ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")
REPLICATES: dict[str, int] = {"gemini": 4, "openai": 2}
MODELS: tuple[str, ...] = ("gemini", "openai")
PROVIDER_OF: dict[str, str] = {"gemini": "gemini", "openai": "openai"}
PILOT_SCENES: tuple[str, ...] = ("810c9104", "189ae2a6")
SEED = 20261114

TOTAL_CAP_USD = 12.00
MODEL_CAP_USD = 6.00
PROJECTION_MARGIN = 1.10
PILOT_STOP_FAILURES = 3


def insert_prompt_line(user_prompt: str) -> str:
    """Return the prompt with the neutral line appended to the head-on bullet.

    Raises:
        ValueError: If the anchor does not occur exactly once, or the line is
            already present.
    """
    if PROMPT_LINE in user_prompt:
        raise ValueError("prompt line already present")
    if user_prompt.count(PROMPT_LINE_ANCHOR) != 1:
        raise ValueError("prompt-line anchor does not occur exactly once")
    return user_prompt.replace(PROMPT_LINE_ANCHOR, f"{PROMPT_LINE_ANCHOR} {PROMPT_LINE}")


class PromptLineProxy(LedgerProxy):
    """`LedgerProxy` that inserts the prompt line into the payload actually sent.

    `Reasoner.run` builds its payloads itself (re-ask and grey fallback included),
    so the line is inserted here, on every attempt, and the parent records the
    hash of the modified prompt.
    """

    def __init__(self, inner: Any, pace_sec: float) -> None:
        super().__init__(inner, pace_sec)
        self.prompt_line = False

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Insert the line when this cell asks for it, then forward and record.

        Raises:
            ValueError: A base prompt already carries the line.
        """
        if self.prompt_line:
            payload = payload.model_copy(
                update={"user_prompt": insert_prompt_line(payload.user_prompt)}
            )
        elif PROMPT_LINE in payload.user_prompt:
            raise ValueError("base cell prompt carries the prompt line")
        return super().analyze(payload, config)


def base_prompt(artifact: Artifact, order: RobotPresentationOrder, image: Path) -> str:
    """The text-off prompt v1 rendered for one scene and order."""
    request = reconstruct_request(artifact, order, image, False)
    return build_prompt_payload(request).user_prompt


def cell_prompt(artifact: Artifact, order: RobotPresentationOrder, image: Path, line: bool) -> str:
    """The prompt a cell sends on attempt 1."""
    text = base_prompt(artifact, order, image)
    return insert_prompt_line(text) if line else text


def image_path_for(variant: str, artifact: Artifact, out_dir: Path) -> Path:
    """Path of one scene's stimulus image for an image variant."""
    if variant == "C_ref":
        return artifact.image_path
    if variant == "grey":
        return out_dir / "grey_1280x960.png"
    return out_dir / "stimuli" / f"{artifact.request_id[:8]}_{variant}.png"


@dataclass(frozen=True)
class Run:
    """One pre-registered run: model, cell, scene, order and replicate."""

    backend_id: str
    cell: str
    artifact: Artifact
    order: RobotPresentationOrder
    replicate: int
    pilot: bool

    @property
    def scene(self) -> str:
        """Eight-character scene id."""
        return self.artifact.request_id[:8]

    @property
    def variant(self) -> str:
        """Image variant of the cell."""
        return CELL_SPECS[self.cell][0]

    @property
    def prompt_line(self) -> bool:
        """Whether the cell carries the prompt line."""
        return CELL_SPECS[self.cell][1]

    def key(self) -> str:
        """Stable identity used to resume."""
        return "|".join(
            (self.backend_id, self.cell, self.artifact.request_id, self.order, f"r{self.replicate}")
        )


def build_runs(
    backend_id: str, scenes: list[Artifact], cells: tuple[str, ...], seed: int = SEED
) -> tuple[list[Run], list[list[Run]]]:
    """Build the pilot block and the main replicate blocks, each shuffled.

    The pilot is replicate 1 of the two pilot scenes, both orders, every cell.
    Main block r holds every (cell, scene, order) of replicate r not in the pilot.
    Each block is shuffled with `random.Random(f"{seed}|{backend_id}|<block>")`.

    Returns:
        `(pilot, [block_rep1, block_rep2, ...])`.
    """
    pilot = [
        Run(backend_id, cell, a, order, 1, True)
        for cell in cells
        for a in scenes
        if a.request_id[:8] in PILOT_SCENES
        for order in ORDERS
    ]
    random.Random(f"{seed}|{backend_id}|pilot").shuffle(pilot)
    pilot_keys = {r.key() for r in pilot}
    blocks = []
    for rep in range(1, REPLICATES[backend_id] + 1):
        block = [
            Run(backend_id, cell, a, order, rep, False)
            for cell in cells
            for a in scenes
            for order in ORDERS
        ]
        block = [r for r in block if r.key() not in pilot_keys]
        random.Random(f"{seed}|{backend_id}|rep{rep}").shuffle(block)
        blocks.append(block)
    return pilot, blocks


def correct_physical(side: str | None) -> str | None:
    """The robot with free retreat room: the one away from the blocker."""
    if side is None:
        return None
    return "east" if side == "west" else "west"


def physical_of(label: str | None) -> str | None:
    """Original IDs: `robot_1` spawned west, `robot_2` east (asserted per scene)."""
    return {"robot_1": "west", "robot_2": "east"}.get(label or "")


def outcome(decision: dict[str, Any] | None, refused: bool, error: str | None, side: str) -> str:
    """Classify: correct, wrong, no_yielder, refusal, parse_failure, error."""
    if decision is None:
        if refused:
            return "refusal"
        return "error" if error else "parse_failure"
    chosen = physical_of(_named(decision))
    if chosen is None:
        return "no_yielder"
    return "correct" if chosen == correct_physical(side) else "wrong"


def utc_now() -> str:
    """UTC timestamp with milliseconds."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def execute_run(
    run: Run,
    proxy: PromptLineProxy,
    config: ReasonerConfig,
    effective: dict[str, Any],
    commit: str,
    out_dir: Path,
    manifest: dict[str, Any],
    seq: int,
    block: str,
) -> dict[str, Any]:
    """Execute one run through the production `Reasoner` and return its row.

    Raises:
        RuntimeError: If the stimulus image or the prompt differs from the manifest.
    """
    image = image_path_for(run.variant, run.artifact, out_dir)
    entry = manifest["scenes"][run.scene] if run.variant != "grey" else manifest["grey"]
    image_md5 = md5_file(image)
    if image_md5 != entry["grey" if run.variant == "grey" else run.variant]:
        raise RuntimeError(f"{run.key()}: image md5 differs from the manifest")
    expected_prompt = cell_prompt(run.artifact, run.order, image, run.prompt_line)
    prompt_md5 = md5_bytes(expected_prompt.encode("utf-8"))
    want = manifest["scenes"][run.scene]["prompts"][run.order][
        "plus" if run.prompt_line else "base"
    ]
    if prompt_md5 != want:
        raise RuntimeError(f"{run.key()}: prompt md5 differs from the manifest")
    request = reconstruct_request(run.artifact, run.order, image, False)
    proxy.reset()
    proxy.prompt_line = run.prompt_line
    started_utc = utc_now()
    started = time.monotonic()
    error: str | None = None
    result = None
    try:
        result = Reasoner(proxy, config).run(request)
    except Exception as exc:  # noqa: BLE001 - recorded as data, never dropped
        error = f"{type(exc).__name__}: {str(exc)[:300]}"
    diag = result.diagnostics if result else None
    decision = result.decision.model_dump(mode="json") if result and result.decision else None
    attempts = [dict(a.__dict__) for a in proxy.calls]
    first = proxy.calls[0] if proxy.calls else None
    terminal_refusal = decision is None and bool(diag and diag.refusal_attempts)
    run_error = error or (diag.error_message if diag and decision is None else None)
    side = run.artifact.obstacle_side
    a1 = attempt1_decision(first.text) if first and not first.provider_refusal else None
    a1_refused = bool(first and (first.provider_refusal or first.text_refusal))
    label = _named(decision)
    return {
        "key": run.key(),
        "seq": seq,
        "block": block,
        "seed": SEED,
        "stamp_start_utc": started_utc,
        "stamp_end_utc": utc_now(),
        "commit": commit,
        "backend_id": run.backend_id,
        "model_id": effective.get("model_id"),
        "served_model": diag.served_model if diag else None,
        "served_models_per_attempt": [a["served_model"] for a in attempts],
        "effective_config": effective,
        "unsupported_sampling": diag.unsupported_sampling if diag else None,
        "cell": run.cell,
        "image_variant": run.variant,
        "prompt_line": run.prompt_line,
        "pilot": run.pilot,
        "request_id": run.artifact.request_id,
        "scene": run.scene,
        "scene_set": "original" if run.artifact.run in ORIGINAL_12 else "extra",
        "run": run.artifact.run,
        "side": side,
        "order": run.order,
        "replicate": run.replicate,
        "obstacle_text": False,
        "image_name": image.name,
        "image_md5": image_md5,
        "prompt_md5": prompt_md5,
        "prompt_sent_matches": bool(first and first.user_sha256 == sha256_text(expected_prompt)),
        "prompt_base_sha256": sha256_text(base_prompt(run.artifact, run.order, image)),
        "image_fallback_used": bool(diag and diag.image_fallback_used),
        "image_fallback_attempt": diag.image_fallback_attempt if diag else None,
        "n_attempts": diag.attempts if diag else len(attempts),
        "n_network_calls": len(attempts),
        "refusal_attempts": diag.refusal_attempts if diag else None,
        "refusal_category": diag.refusal_category if diag else None,
        "terminal_refusal": terminal_refusal,
        "parse_status": diag.parse_status if diag else None,
        "attempts": attempts,
        "decision": decision,
        "strategy": (decision or {}).get("strategy"),
        "yield_robot": label,
        "chosen_physical": physical_of(label),
        "correct_physical": correct_physical(side),
        "first_listed_physical": "west" if run.order == "id_asc" else "east",
        "outcome": outcome(decision, terminal_refusal, run_error, side),
        "attempt1_refused": a1_refused,
        "attempt1_decision": a1,
        "attempt1_outcome": outcome(a1, a1_refused, first.error if first else "no call", side),
        "attempt1_chosen_physical": physical_of(_named(a1)),
        "wall_ms": int((time.monotonic() - started) * 1000),
        "error": run_error,
        "provider_stop": proxy.provider_stop,
    }


def completed_keys(rows: list[dict[str, Any]]) -> set[str]:
    """Keys a resume skips.

    Amendment 1: a run cut off by a provider stop has no model outcome, so its key
    is not done and a resume re-runs it; the analysis drops the stop row.
    """
    return {r["key"] for r in rows if not (r["decision"] is None and r.get("provider_stop"))}


def total_spend(out_dir: Path) -> tuple[float, dict[str, float]]:
    """Spend from every model's ledger plus the probes."""
    per: dict[str, float] = {}
    for path in sorted(out_dir.glob("ledger_*.jsonl")):
        for entry in load_jsonl(path):
            per[entry["backend_id"]] = per.get(entry["backend_id"], 0.0) + entry["usd"]
    for probe in load_jsonl(out_dir / "probes.jsonl"):
        per[probe["backend_id"]] = per.get(probe["backend_id"], 0.0) + probe.get("usd", 0.0)
    return sum(per.values()), per


def pilot_stopped(rows: list[dict[str, Any]], cell: str) -> bool | None:
    """Pilot rule: None until 4 pilot runs exist; True when 3+ ended undecided or fell back."""
    pilots = [r for r in rows if r["cell"] == cell and r["pilot"]]
    if len(pilots) < len(PILOT_SCENES) * len(ORDERS):
        return None
    bad = sum(1 for r in pilots if r["decision"] is None or r["image_fallback_used"])
    return bad >= PILOT_STOP_FAILURES


def project_cells(
    backend_id: str,
    rows: list[dict[str, Any]],
    cells: tuple[str, ...],
    spent: float,
    reserve: float,
) -> tuple[tuple[str, ...], list[dict[str, Any]]]:
    """Cut cells from the bottom of the priority list until the projection fits.

    Projection = spent + 1.10 x sum over kept cells of (mean pilot cost of the
    cell x its remaining runs). It must not exceed the model cap minus one
    worst-case run (`reserve`), which is where the per-run pre-check stops.

    Returns:
        `(kept cells, log of each projection step)`.
    """
    per_cell_runs = 24 * len(ORDERS) * REPLICATES[backend_id]
    kept = list(cells)
    log = []
    while kept:
        projected = spent
        for cell in kept:
            pilots = [r for r in rows if r["cell"] == cell and r["pilot"]]
            mean = sum(r["usd"] for r in pilots) / len(pilots)
            done = sum(1 for r in rows if r["cell"] == cell)
            projected += PROJECTION_MARGIN * mean * (per_cell_runs - done)
        fits = projected <= MODEL_CAP_USD - reserve
        log.append({"cells": list(kept), "projected_usd": round(projected, 4), "fits": fits})
        if fits:
            break
        kept.pop()
    return tuple(kept), log


def execute_model(
    backend_id: str, scenes: list[Artifact], out_dir: Path, pace_sec: float, manifest: dict
) -> str:
    """Run one model's pilot, pilot rule, budget projection and main blocks."""
    calls_path = out_dir / f"calls_{backend_id}.jsonl"
    ledger_path = out_dir / f"ledger_{backend_id}.jsonl"
    config, backend_config, effective = load_model(backend_id)
    proxy = PromptLineProxy(make_backend(backend_id, backend_config), pace_sec)
    commit = git_commit()
    rows = load_jsonl(calls_path)
    done = completed_keys(rows)
    prompt_bound = DEFAULT_PROMPT_TOKENS_BOUND
    for r in rows:
        for a in r["attempts"]:
            usage = a["token_usage"] or {}
            prompt_bound = max(
                prompt_bound, int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) * 1.2)
            )
    pilot, blocks = build_runs(backend_id, scenes, PLANNED_CELLS)
    decisions_path = out_dir / f"budget_{backend_id}.json"

    def step(run: Run, seq: int, block: str) -> str | None:
        nonlocal prompt_bound
        total, per = total_spend(out_dir)
        worst = config.max_attempts * worst_attempt_usd(backend_id, config, prompt_bound)
        if per.get(backend_id, 0.0) + worst > MODEL_CAP_USD:
            return f"model cap: spent {per.get(backend_id, 0.0):.4f}, next worst {worst:.4f}"
        if total + worst > TOTAL_CAP_USD:
            return f"TOTAL cap: spent {total:.4f}, next worst {worst:.4f}"
        row = execute_run(run, proxy, config, effective, commit, out_dir, manifest, seq, block)
        for attempt in row["attempts"]:
            usage = attempt["token_usage"] or {}
            seen = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            prompt_bound = max(prompt_bound, int(seen * 1.2))
        usd = row_cost(row, config, prompt_bound)
        row["usd"] = usd
        append_jsonl(calls_path, row)
        model_total = per.get(backend_id, 0.0) + usd
        append_jsonl(
            ledger_path,
            {
                "key": row["key"],
                "backend_id": backend_id,
                "stamp_utc": row["stamp_end_utc"],
                "network_calls": row["n_network_calls"],
                "transient_retries": sum(1 for a in row["attempts"] if a["transient_retry"]),
                "usd": usd,
                "model_total": model_total,
                "grand_total": total + usd,
            },
        )
        rows.append(row)
        print(
            f"{seq} {row['key']} {row['outcome']} y={row['yield_robot']} s={row['strategy']} "
            f"att={row['n_attempts']} fb={row['image_fallback_used']} usd={usd:.4f} "
            f"model={model_total:.4f} total={total + usd:.4f}",
            flush=True,
        )
        if proxy.provider_stop:
            return f"provider stop: {proxy.provider_stop}"
        return None

    for seq, run in enumerate(pilot):
        if run.key() in done:
            continue
        stop = step(run, seq, "pilot")
        if stop:
            return stop
    stopped = {cell for cell in PLANNED_CELLS if pilot_stopped(rows, cell)}
    if decisions_path.is_file():
        kept = tuple(json.loads(decisions_path.read_text())["kept_cells"])
    else:
        _, per = total_spend(out_dir)
        config_worst = config.max_attempts * worst_attempt_usd(backend_id, config, prompt_bound)
        live = tuple(c for c in PLANNED_CELLS if c not in stopped)
        kept, log = project_cells(backend_id, rows, live, per.get(backend_id, 0.0), config_worst)
        decisions_path.write_text(
            json.dumps(
                {
                    "stamp_utc": utc_now(),
                    "pilot_stopped_cells": sorted(stopped),
                    "kept_cells": list(kept),
                    "projection_log": log,
                },
                indent=1,
            )
        )
    print(f"{backend_id}: pilot stopped {sorted(stopped)}; main cells {kept}", flush=True)
    seq = len(pilot)
    for index, block in enumerate(blocks, start=1):
        for run in block:
            seq += 1
            if run.key() in done or run.cell not in kept:
                continue
            stop = step(run, seq, f"rep{index}")
            if stop:
                return stop
    return "complete"


def build_manifest(scenes: list[Artifact], out_dir: Path, image_md5s: dict) -> dict[str, Any]:
    """Assemble the stimulus and prompt manifest (md5 of every image and prompt)."""
    scenes_out: dict[str, Any] = {}
    for a in scenes:
        key = a.request_id[:8]
        prompts = {}
        for order in ORDERS:
            texts = {
                v: base_prompt(a, order, image_path_for(v, a, out_dir))
                for v in ("C_ref", "grey", "L2", "K1")
            }
            if len(set(texts.values())) != 1:
                raise RuntimeError(f"{key} {order}: prompt depends on the image variant")
            base = texts["C_ref"]
            prompts[order] = {
                "base": md5_bytes(base.encode("utf-8")),
                "plus": md5_bytes(insert_prompt_line(base).encode("utf-8")),
                "base_sha256": sha256_text(base),
            }
        scenes_out[key] = {
            "request_id": a.request_id,
            "run": a.run,
            "side": a.obstacle_side,
            "correct_physical": correct_physical(a.obstacle_side),
            "raw_frame": a.raw_image_path.is_file(),
            "stored_order": a.stored_order,
            **{k: v for k, v in image_md5s[key].items()},
            "prompts": prompts,
        }
    return {
        "seed": SEED,
        "prompt_line": PROMPT_LINE,
        "prompt_line_anchor": PROMPT_LINE_ANCHOR,
        "planned_cells": list(PLANNED_CELLS),
        "priority": list(PRIORITY),
        "replicates": REPLICATES,
        "pilot_scenes": list(PILOT_SCENES),
        "grey": image_md5s["grey"],
        "scenes": scenes_out,
    }


def main() -> None:
    """Write the manifest, or probe providers, or run one model."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--model", choices=MODELS)
    parser.add_argument("--pace-sec", type=float, default=1.0)
    args = parser.parse_args()

    scenes = load_scenes(args.runs_dir)
    manifest_path = args.out_dir / "manifest.json"
    if args.write_manifest:
        from scripts.render_annotation_variants import write_stimuli

        manifest = build_manifest(scenes, args.out_dir, write_stimuli(scenes, args.out_dir))
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
        print(f"manifest written: {len(manifest['scenes'])} scenes")
        return
    manifest = json.loads(manifest_path.read_text())
    if args.probe_only:
        done = {r["backend_id"] for r in load_jsonl(args.out_dir / "probes.jsonl")}
        for backend_id in MODELS:
            if backend_id in done:
                continue
            row = probe_provider(backend_id, args.out_dir)
            print(
                f"probe {backend_id}: ok={row['ok']} status={row.get('status_code')} "
                f"served={row.get('served_model')}"
            )
        return
    if args.model is None:
        parser.error("--model is required for a run")
    probe = next(
        (r for r in load_jsonl(args.out_dir / "probes.jsonl") if r["backend_id"] == args.model),
        None,
    )
    if not probe or not probe["ok"]:
        print(f"{args.model}: no passing probe; not run")
        return
    reason = execute_model(args.model, scenes, args.out_dir, args.pace_sec, manifest)
    print(f"{args.model}: ended - {reason}", flush=True)


if __name__ == "__main__":
    main()
