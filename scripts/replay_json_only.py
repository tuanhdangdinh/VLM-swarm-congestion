"""Head-on JSON-only replay: the swapped-ID test with a JSON-only answer ending.

Pre-registered in docs/superpowers/specs/2026-11-14-head-on-json-only-replay-design.md.
The 12 standoff stimuli of the swapped-ID replay are re-sent through the production
`build_reasoner_request` / `Reasoner` path with one change: the v1 prompt's
`<think>` answer-format block is replaced by the JSON-only line the current (v3.4)
builder ends with. The replacement happens in this runner's prompt-condition layer,
the same code for every model; no backend is touched and nothing is keyed on the
backend. The re-ask suffix and the neutral-image fallback pass through unchanged.

Every model runs its shipped retry config plus
`final_refusal_categories=("reasoning_extraction",)` (owner approval 2026-11-14,
option 3).

Reuses the pure helpers of `scripts/replay_swapped_ids.py` (cells, scoring, row
building, ledger proxy, pricing); its caps, order and pilot rule are not used.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (REPO_ROOT, REPO_ROOT / "ros2_ws/src/swarm_orchestrator", REPO_ROOT / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from reasoning.vlm.backend_base import VLMBackend  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    RobotPresentationOrder,
)
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402
from scripts.replay_live_decisions import Artifact, reconstruct_request, sha256_text  # noqa: E402
from scripts.replay_swapped_ids import (  # noqa: E402
    NOTEXT_ARMS,
    REAL_FRAME_ARMS,
    ArmName,
    Cell,
    LedgerProxy,
    append_jsonl,
    git_commit,
    grey_image_for,
    ledger_totals,
    load_jsonl,
    load_model,
    load_stimuli,
    make_backend,
    probe_provider,
    row_cost,
    run_cell,
    swapped_artifact,
    worst_attempt_usd,
)

OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-head-on-json-only-replay"

# The closing line of the current builder (v3.4, reasoning/vlm/prompt_builder.py)
# and of the October roster diagnostic that Sonnet answered 3/3.
JSON_ONLY_LINE = "Write ONLY the final JSON object, with no surrounding text or markdown."
# The v1 answer-format block as rendered (reasoning/vlm/prompt_v1.py:91-98); the
# first <think> line varies with the geometry condition, so it is matched loosely.
V1_ANSWER_FORMAT_RE = re.compile(
    r"Answer using the following format:\n<think>\n.*?\n</think>\n"
    r"Immediately after the </think> tag, write ONLY the final JSON object, with no "
    r"surrounding text or markdown\.",
    re.S,
)

FINAL_REFUSAL_CATEGORIES: tuple[str, ...] = ("reasoning_extraction",)
MODELS: tuple[str, ...] = ("gemini", "openai", "anthropic")
TOTAL_CAP_USD = 5.00
MODEL_CAP_USD = 2.00
SEED = 20261114
# Priority tiers; cells within a tier are interleaved in a seeded order per model.
TIERS: tuple[tuple[ArmName, ...], ...] = (
    ("A_grey", "B_grey"),
    ("A_real",),
    ("C_real_notext", "D_grey_notext"),
)
ALL_ARMS: tuple[ArmName, ...] = tuple(arm for tier in TIERS for arm in tier)
ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")
REPLICATES: tuple[int, ...] = (1, 2)
TIER_MARGIN = 1.15
CELL_CHECK_RUNS = 8
CELL_CHECK_MAX_BAD = 4
WEST_PILOT, EAST_PILOT = "53264de9", "61119197"
# Compatibility pilot (owner addition 2026-11-14): 8 runs per provider, both sides,
# both orders, every cell; replicate 1. They count toward the 48 per cell.
COMPAT_PILOT: tuple[tuple[ArmName, str, RobotPresentationOrder], ...] = (
    ("A_grey", WEST_PILOT, "id_asc"),
    ("A_grey", EAST_PILOT, "id_desc"),
    ("B_grey", WEST_PILOT, "id_desc"),
    ("B_grey", EAST_PILOT, "id_asc"),
    ("A_real", WEST_PILOT, "id_desc"),
    ("A_real", EAST_PILOT, "id_asc"),
    ("C_real_notext", WEST_PILOT, "id_asc"),
    ("D_grey_notext", EAST_PILOT, "id_desc"),
)
COMPAT_MIN_ANSWERED = 7
CONTENT_FILTER_FINISH = frozenset(
    {"content_filter", "safety", "prohibited_content", "blocklist", "spii", "refusal"}
)
LIVE_CHECK_PREFIX = WEST_PILOT


def json_only(user_prompt: str) -> str:
    """Replace the v1 `<think>` answer-format block with the JSON-only line.

    Text after the block (a re-ask suffix) is kept.

    Args:
        user_prompt: A rendered v1 user prompt, possibly with a re-ask suffix.

    Returns:
        The prompt with exactly that block replaced.

    Raises:
        ValueError: If the block does not occur exactly once.
    """
    found = V1_ANSWER_FORMAT_RE.findall(user_prompt)
    if len(found) != 1:
        raise ValueError(f"v1 answer-format block found {len(found)} times")
    return V1_ANSWER_FORMAT_RE.sub(lambda _m: JSON_ONLY_LINE, user_prompt, count=1)


def file_sha256(path: str | Path) -> str:
    """SHA-256 of a file's bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PromptConditionProxy(LedgerProxy):
    """The runner's prompt-condition layer, then the ledger proxy.

    Applies `json_only` to every attempt's user prompt, whatever the backend, and
    records what was actually sent: user, system and image SHA-256.
    """

    def __init__(self, inner: VLMBackend, pace_sec: float) -> None:
        super().__init__(inner, pace_sec)
        self.sent: dict[int, dict[str, Any]] = {}

    def reset(self) -> None:
        """Clear per-run state before the next `Reasoner.run`."""
        super().reset()
        self.sent = {}

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Transform the prompt, record its hashes, then forward through the ledger.

        Args:
            payload: The payload the production `Reasoner` built (v1 text).
            config: Runtime decoding settings.

        Returns:
            The backend's response.
        """
        sent = payload.model_copy(update={"user_prompt": json_only(payload.user_prompt)})
        self.sent[self.attempt_index + 1] = {
            "v1_user_sha256": sha256_text(payload.user_prompt),
            "sent_user_sha256": sha256_text(sent.user_prompt),
            "sent_system_sha256": sha256_text(sent.system_prompt),
            "sent_image_sha256": file_sha256(sent.image_path),
            "reask_suffix": "Your previous response was invalid" in sent.user_prompt,
        }
        return super().analyze(sent, config)


def experiment_config(backend_id: str) -> tuple[ReasonerConfig, Any, dict[str, Any]]:
    """Shipped config plus the final-refusal option; returns config, backend config, effective."""
    shipped, backend_config, effective = load_model(backend_id)
    config = ReasonerConfig(
        **{**shipped.model_dump(), "final_refusal_categories": FINAL_REFUSAL_CATEGORIES}
    )
    effective = {
        **effective,
        "final_refusal_categories": list(FINAL_REFUSAL_CATEGORIES),
        "answer_format": "json_only",
    }
    return config, backend_config, effective


def _make_cell(
    backend_id: str,
    arm: ArmName,
    artifact: Artifact,
    order: RobotPresentationOrder,
    rep: int,
    grey: Path,
    pilot: bool,
) -> Cell:
    image = artifact.image_path if arm in REAL_FRAME_ARMS else grey
    return Cell(backend_id, arm, artifact, order, rep, image, pilot)


def build_plan(
    backend_id: str, stimuli: list[Artifact], grey: Path
) -> list[tuple[str, list[Cell]]]:
    """One model's execution plan: the compatibility pilot, then the seeded tiers.

    Args:
        backend_id: The model's `config/models.yaml` section.
        stimuli: The 12 standoff artifacts.
        grey: The neutral image of the grey cells.

    Returns:
        `(phase name, cells)` pairs: "pilot", then "tier1".."tier3". Each tier
        holds every remaining run of its cells (48 per cell minus pilot runs),
        shuffled by `random.Random(f"{SEED}|{backend_id}|{tier}")`.
    """
    by_prefix = {a.request_id[:8]: a for a in stimuli}
    pilot = [
        _make_cell(backend_id, arm, by_prefix[prefix], order, 1, grey, True)
        for arm, prefix, order in COMPAT_PILOT
    ]
    pilot_keys = {c.key() for c in pilot}
    plan: list[tuple[str, list[Cell]]] = [("pilot", pilot)]
    for index, arms in enumerate(TIERS, start=1):
        cells = [
            _make_cell(backend_id, arm, artifact, order, rep, grey, False)
            for arm in arms
            for rep in REPLICATES
            for artifact in stimuli
            for order in ORDERS
        ]
        cells = [c for c in cells if c.key() not in pilot_keys]
        random.Random(f"{SEED}|{backend_id}|tier{index}").shuffle(cells)
        plan.append((f"tier{index}", cells))
    return plan


def run_json_only_cell(
    cell: Cell,
    proxy: PromptConditionProxy,
    config: ReasonerConfig,
    effective: dict[str, Any],
    commit: str,
    phase: str,
) -> dict[str, Any]:
    """Run one cell through the production `Reasoner` under the JSON-only condition."""
    row = run_cell(cell, proxy, config, effective, commit)
    obstacle_text = cell.arm not in NOTEXT_ARMS
    v1 = build_prompt_payload(
        reconstruct_request(cell.request_artifact(), cell.order, cell.image_path, obstacle_text)
    )
    for attempt in row["attempts"]:
        attempt.update(proxy.sent.get(attempt["attempt"], {}))
    row.update(
        answer_format="json_only",
        wording_rev=0,
        phase=phase,
        prompt_v1_user_sha256=row["prompt_user_sha256"],
        prompt_user_sha256=sha256_text(json_only(v1.user_prompt)),
        prompt_system_sha256=sha256_text(v1.system_prompt),
        image_sha256=file_sha256(cell.image_path),
        final_refusal=bool(row["error"] and "final_refusal_categories" in row["error"]),
        attempt1_answered=row["decision"] is not None and row["n_attempts"] == 1,
    )
    return row


def compat_gate(rows: list[dict[str, Any]], backend_id: str) -> dict[str, Any]:
    """Apply the pre-registered compatibility-pilot criteria to one provider.

    Returns:
        Counts and `passed`; `complete` is False until all 8 pilot runs exist.
    """
    pilots = [r for r in rows if r["backend_id"] == backend_id and r["phase"] == "pilot"]
    provider_refusals = 0
    content_filter = 0
    format_failures = 0
    for r in pilots:
        for index, a in enumerate(r["attempts"]):
            if a["provider_refusal"]:
                provider_refusals += 1
            if (a["finish_reason"] or "").lower() in CONTENT_FILTER_FINISH:
                content_filter += 1
            answered_last = index == len(r["attempts"]) - 1 and r["decision"] is not None
            if (
                a["error"] is None
                and not a["provider_refusal"]
                and not a["text_refusal"]
                and not answered_last
            ):
                format_failures += 1
    answered = sum(1 for r in pilots if r["attempt1_answered"])
    fallback = sum(1 for r in pilots if r["image_fallback_used"])
    complete = len(pilots) == len(COMPAT_PILOT)
    passed = (
        complete
        and provider_refusals == 0
        and content_filter == 0
        and answered >= COMPAT_MIN_ANSWERED
        and fallback == 0
        and format_failures == 0
    )
    return {
        "backend_id": backend_id,
        "runs": len(pilots),
        "complete": complete,
        "answered_attempt1": answered,
        "provider_refusals": provider_refusals,
        "content_filter": content_filter,
        "format_failures": format_failures,
        "fallback_runs": fallback,
        "served_models": sorted({r["served_model"] or "" for r in pilots}),
        "passed": passed,
    }


def cell_stopped(rows: list[dict[str, Any]], backend_id: str, arm: str) -> bool:
    """Cell rule: more than 4 of a cell's first 8 runs with no decision or a fallback."""
    first = [r for r in rows if r["backend_id"] == backend_id and r["arm"] == arm]
    first = first[:CELL_CHECK_RUNS]
    if len(first) < CELL_CHECK_RUNS:
        return False
    bad = sum(1 for r in first if r["decision"] is None or r["image_fallback_used"])
    return bad > CELL_CHECK_MAX_BAD


def sonnet_stopped(rows: list[dict[str, Any]], backend_id: str) -> bool:
    """Sonnet rule: in any cell, more than 4 of the first 8 runs refused on attempt 1."""
    if backend_id != "anthropic":
        return False
    for arm in ALL_ARMS:
        first = [r for r in rows if r["backend_id"] == backend_id and r["arm"] == arm]
        first = first[:CELL_CHECK_RUNS]
        if len(first) == CELL_CHECK_RUNS:
            if sum(1 for r in first if r["attempt1_refused"]) > CELL_CHECK_MAX_BAD:
                return True
    return False


def tier_fits(
    remaining: int,
    mean_run_usd: float,
    worst_run_usd: float,
    model_spent: float,
    total_spent: float,
) -> bool:
    """Tier rule: start a tier only if all its remaining runs fit under both caps."""
    need = remaining * mean_run_usd * TIER_MARGIN + worst_run_usd
    return model_spent + need <= MODEL_CAP_USD and total_spent + need <= TOTAL_CAP_USD


def _ledger_row(
    key: str, backend_id: str, network_calls: int, transient: int, usd: float, ledger_path: Path
) -> None:
    total, per = ledger_totals(load_jsonl(ledger_path))
    append_jsonl(
        ledger_path,
        {
            "key": key,
            "backend_id": backend_id,
            "network_calls": network_calls,
            "transient_retries": transient,
            "usd": usd,
            "model_total": per.get(backend_id, 0.0) + usd,
            "grand_total": total + usd,
        },
    )


def execute_phase(
    backend_id: str,
    phase: str,
    cells: list[Cell],
    out_dir: Path,
    pace_sec: float,
    commit: str,
) -> str:
    """Run one phase of one model under every stop rule; return why it ended."""
    calls_path, ledger_path = out_dir / "calls.jsonl", out_dir / "ledger.jsonl"
    config, backend_config, effective = experiment_config(backend_id)
    rows = load_jsonl(calls_path)
    done = {r["key"] for r in rows}
    remaining = [c for c in cells if c.key() not in done]
    if not remaining:
        return "complete"
    prompt_bound = 3000
    for r in rows:
        if r["backend_id"] != backend_id:
            continue
        for a in r["attempts"]:
            usage = a["token_usage"] or {}
            seen = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            prompt_bound = max(prompt_bound, int(seen * 1.2))
    worst = config.max_attempts * worst_attempt_usd(backend_id, config, prompt_bound)
    total, per = ledger_totals(load_jsonl(ledger_path))
    if phase != "pilot":
        own = [r["usd"] for r in rows if r["backend_id"] == backend_id]
        if not own:
            return "tier not started: no pilot rows to estimate cost from"
        mean = sum(own) / len(own)
        if not tier_fits(len(remaining), mean, worst, per.get(backend_id, 0.0), total):
            return (
                f"tier not started: {len(remaining)} runs x {mean:.4f} x {TIER_MARGIN} + "
                f"{worst:.4f} does not fit (model {per.get(backend_id, 0.0):.4f}, "
                f"total {total:.4f})"
            )
    proxy = PromptConditionProxy(make_backend(backend_id, backend_config), pace_sec)
    for cell in remaining:
        if sonnet_stopped(rows, backend_id):
            return "Sonnet refusal stop (more than 4 of 8 attempt-1 refusals in a cell)"
        if phase != "pilot" and cell_stopped(rows, backend_id, cell.arm):
            continue
        total, per = ledger_totals(load_jsonl(ledger_path))
        worst = config.max_attempts * worst_attempt_usd(backend_id, config, prompt_bound)
        if per.get(backend_id, 0.0) + worst > MODEL_CAP_USD:
            return f"model cap: spent {per.get(backend_id, 0.0):.4f}, next worst {worst:.4f}"
        if total + worst > TOTAL_CAP_USD:
            return f"TOTAL cap: spent {total:.4f}, next worst {worst:.4f}"
        row = run_json_only_cell(cell, proxy, config, effective, commit, phase)
        for attempt in row["attempts"]:
            usage = attempt["token_usage"] or {}
            seen = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            prompt_bound = max(prompt_bound, int(seen * 1.2))
        row["usd"] = row_cost(row, config, prompt_bound)
        row["seq"] = len(rows)
        append_jsonl(calls_path, row)
        _ledger_row(
            row["key"],
            backend_id,
            row["n_network_calls"],
            sum(1 for a in row["attempts"] if a["transient_retry"]),
            row["usd"],
            ledger_path,
        )
        rows.append(row)
        print(
            f"{phase} {row['key']} outcome={row['outcome']} yield={row['yield_robot']} "
            f"att={row['n_attempts']} fb={row['image_fallback_used']} "
            f"final_ref={row['final_refusal']} usd={row['usd']:.4f}",
            flush=True,
        )
        if proxy.provider_stop:
            return f"provider stop: {proxy.provider_stop}"
    return "complete"


def live_check(
    backend_id: str, stimuli: list[Artifact], out_dir: Path, pace_sec: float, commit: str
) -> dict[str, Any]:
    """One call of the CURRENT production prompt (v3.4) per provider; outside every table.

    Stimulus `53264de9`, `id_asc`, annotated frame, obstacle text on, rendered by
    the current builder (`prompt_version=3`) with no transform.
    """
    path = out_dir / "live_v34_check.jsonl"
    existing = [r for r in load_jsonl(path) if r["backend_id"] == backend_id]
    if existing:
        return existing[0]
    config, backend_config, effective = experiment_config(backend_id)
    artifact = next(a for a in stimuli if a.request_id.startswith(LIVE_CHECK_PREFIX))
    request = reconstruct_request(
        dataclasses.replace(artifact, prompt_version=3), "id_asc", artifact.image_path, True
    )
    payload = build_prompt_payload(request)
    proxy = LedgerProxy(make_backend(backend_id, backend_config), pace_sec)
    result = Reasoner(proxy, config).run(request)
    diag = result.diagnostics
    row = {
        "key": f"live_v34|{backend_id}|{artifact.request_id}|id_asc",
        "commit": commit,
        "backend_id": backend_id,
        "served_model": diag.served_model,
        "prompt_version": 3,
        "user_sha256": sha256_text(payload.user_prompt),
        "system_sha256": sha256_text(payload.system_prompt),
        "image_sha256": file_sha256(payload.image_path),
        "ends_with_json_only_line": payload.user_prompt.endswith(JSON_ONLY_LINE),
        "has_think_block": "<think>" in payload.user_prompt,
        "attempts": [dataclasses.asdict(a) for a in proxy.calls],
        "n_attempts": diag.attempts,
        "parse_status": diag.parse_status,
        "refusal_attempts": diag.refusal_attempts,
        "refusal_category": diag.refusal_category,
        "image_fallback_used": diag.image_fallback_used,
        "error": diag.error_message if result.decision is None else None,
        "decision": result.decision.model_dump(mode="json") if result.decision else None,
    }
    row["usd"] = row_cost(row, config, 7000)
    append_jsonl(path, row)
    _ledger_row(
        row["key"], backend_id, len(row["attempts"]), 0, row["usd"], out_dir / "ledger.jsonl"
    )
    return row


def build_manifest(stimuli: list[Artifact], grey: Path) -> dict[str, Any]:
    """Prompt manifest: v1 and JSON-only SHA per stimulus x order x ID/text condition.

    Raises:
        RuntimeError: If any transformed prompt differs from its v1 prompt by more
            than the answer-format block.
    """
    entries = []
    conditions = (("original", True), ("swapped", True), ("original", False))
    for artifact in stimuli:
        for order in ORDERS:
            for ids, text in conditions:
                art = swapped_artifact(artifact) if ids == "swapped" else artifact
                payload = build_prompt_payload(reconstruct_request(art, order, grey, text))
                v1 = payload.user_prompt
                sent = json_only(v1)
                (block,) = V1_ANSWER_FORMAT_RE.findall(v1)
                head, tail = v1.split(block)
                if tail != "" or sent != head + JSON_ONLY_LINE or v1 != head + block:
                    raise RuntimeError(f"{artifact.request_id[:8]} {order} {ids}: diff not exact")
                entries.append(
                    {
                        "scene": artifact.request_id[:8],
                        "side": artifact.obstacle_side,
                        "order": order,
                        "ids": ids,
                        "obstacle_text": text,
                        "v1_user_sha256": sha256_text(v1),
                        "json_only_user_sha256": sha256_text(sent),
                        "system_sha256": sha256_text(payload.system_prompt),
                        "removed_block_sha256": sha256_text(block),
                        "diff_is_block_only": True,
                    }
                )
    return {
        "json_only_line": JSON_ONLY_LINE,
        "grey_image_sha256": file_sha256(grey),
        "frame_sha256": {a.request_id[:8]: file_sha256(a.image_path) for a in stimuli},
        "entries": entries,
    }


def main() -> None:
    """Run one pre-registered phase: check, probe, pilot, live check or batch."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--models", nargs="*", default=list(MODELS))
    parser.add_argument("--pace-sec", type=float, default=1.0)
    parser.add_argument(
        "--phase", choices=("check", "probe", "pilot", "live", "batch"), required=True
    )
    args = parser.parse_args()

    stimuli = load_stimuli(args.runs_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    grey = grey_image_for(stimuli, args.out_dir)
    commit = git_commit()
    print(f"{len(stimuli)} stimuli SHA-verified; commit {commit}")
    if args.phase == "check":
        manifest = build_manifest(stimuli, grey)
        (args.out_dir / "prompt_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
        order = {
            b: {phase: [c.key() for c in cells] for phase, cells in build_plan(b, stimuli, grey)}
            for b in MODELS
        }
        (args.out_dir / "run_order.json").write_text(json.dumps(order, indent=1) + "\n")
        print(f"manifest: {len(manifest['entries'])} prompts, all block-only diffs")
        for b, phases in order.items():
            print(b, {p: len(k) for p, k in phases.items()})
        return
    if args.phase == "probe":
        for backend_id in args.models:
            row = probe_provider(backend_id, args.out_dir)
            _ledger_row(
                f"probe|{backend_id}", backend_id, 1, 0, row["usd"], args.out_dir / "ledger.jsonl"
            )
            print(f"probe {backend_id}: ok={row['ok']} status={row.get('status_code')}")
        return
    if args.phase == "live":
        for backend_id in args.models:
            row = live_check(backend_id, stimuli, args.out_dir, args.pace_sec, commit)
            print(
                f"live v3.4 {backend_id}: answered={row['decision'] is not None} "
                f"attempts={row['n_attempts']} refusals={row['refusal_attempts']} "
                f"category={row['refusal_category']} usd={row['usd']:.4f}"
            )
        return
    plans = {b: dict(build_plan(b, stimuli, grey)) for b in args.models}
    if args.phase == "pilot":
        for backend_id in args.models:
            reason = execute_phase(
                backend_id,
                "pilot",
                plans[backend_id]["pilot"],
                args.out_dir,
                args.pace_sec,
                commit,
            )
            print(f"{backend_id} pilot: ended - {reason}")
        rows = load_jsonl(args.out_dir / "calls.jsonl")
        for backend_id in args.models:
            print(json.dumps(compat_gate(rows, backend_id)))
        return
    rows = load_jsonl(args.out_dir / "calls.jsonl")
    gates = {b: compat_gate(rows, b) for b in args.models}
    stopped: set[str] = set()
    for tier in ("tier1", "tier2", "tier3"):
        for backend_id in args.models:
            if not gates[backend_id]["passed"]:
                print(f"{backend_id} {tier}: skipped, compatibility pilot not passed")
                continue
            if backend_id in stopped:
                continue
            reason = execute_phase(
                backend_id, tier, plans[backend_id][tier], args.out_dir, args.pace_sec, commit
            )
            print(f"{backend_id} {tier}: ended - {reason}", flush=True)
            if reason.startswith("TOTAL cap"):
                return
            if reason.startswith(("provider stop", "Sonnet refusal stop", "model cap")):
                stopped.add(backend_id)


if __name__ == "__main__":
    main()
