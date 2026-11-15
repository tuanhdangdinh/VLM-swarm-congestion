"""Extra tables for the head-on JSON-only replay; no network, no keys.

The pre-registered per-model tables come from `scripts/analyze_swapped_ids.py
--out-dir <this experiment>`. This script adds what the JSON-only design names
beyond them: the cross-provider prompt identity check against the manifest, the
compatibility pilot and live-prompt check tables, Sonnet's refusal rate, and the
answer-format side-by-side against the v1-prompt stratum (never pooled).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
NEW_DIR = REPO / "data/experiments/2026-11-14-head-on-json-only-replay"
OLD_DIR = REPO / "data/experiments/2026-11-14-head-on-swapped-id-replay"
ARMS = ("A_grey", "B_grey", "A_real", "C_real_notext", "D_grey_notext")


def load(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file; empty when missing."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def identity_check(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    """Attempt-1 sent hashes: equal across providers and equal to the manifest."""
    expected = {
        (e["scene"], e["order"], e["ids"], e["obstacle_text"]): (
            e["json_only_user_sha256"],
            e["system_sha256"],
        )
        for e in manifest["entries"]
    }
    by_cell: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    manifest_mismatch = 0
    for r in rows:
        a1 = r["attempts"][0]
        if a1.get("reask_suffix"):
            raise RuntimeError(f"{r['key']}: attempt 1 carries a re-ask suffix")
        sent = (a1["sent_user_sha256"], a1["sent_system_sha256"], a1["sent_image_sha256"])
        cell = r["key"].split("|", 1)[1]
        by_cell[cell].add(sent)
        want_user, want_system = expected[(r["scene"], r["order"], r["ids"], r["obstacle_text"])]
        want_image = (
            manifest["frame_sha256"][r["scene"]]
            if r["image_condition"] == "annotated_frame"
            else manifest["grey_image_sha256"]
        )
        if (
            a1["sent_user_sha256"] != want_user
            or r["prompt_user_sha256"] != want_user
            or a1["sent_system_sha256"] != want_system
            or a1["sent_image_sha256"] != want_image
        ):
            manifest_mismatch += 1
    providers: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        providers[r["key"].split("|", 1)[1]].add(r["backend_id"])
    shared = [c for c, p in providers.items() if len(p) > 1]
    differing = [c for c in shared if len(by_cell[c]) != 1]
    print("## Prompt identity (attempt 1, user/system/image SHA-256)")
    print(
        f"  rows {len(rows)}; mismatches against manifest (user, system, image) {manifest_mismatch}"
    )
    print(
        f"  cells run by more than one provider: {len(shared)}; "
        f"with differing sent hashes: {len(differing)}"
    )
    attempts = [a for r in rows for a in r["attempts"]]
    print(f"  attempts carrying '<think>' block: 0 by construction; total attempts {len(attempts)}")


def pilot_table(rows: list[dict[str, Any]], live: list[dict[str, Any]]) -> None:
    """Compatibility pilot per provider and the v3.4 live-prompt check."""
    print("\n## Compatibility pilot (8 runs per provider)")
    print(
        "| Provider | Runs | Answered on attempt 1 | Provider refusals | Parse failures | "
        "Fallback used | Served model |"
    )
    print("|---|---|---|---|---|---|---|")
    for b in dict.fromkeys(r["backend_id"] for r in rows):
        p = [r for r in rows if r["backend_id"] == b and r["phase"] == "pilot"]
        refusals = sum(a["provider_refusal"] for r in p for a in r["attempts"])
        parse = sum(1 for r in p if r["outcome"] == "parse_failure")
        served = sorted({r["served_model"] for r in p})
        print(
            f"| {b} | {len(p)} | {sum(r['attempt1_answered'] for r in p)} | {refusals} | "
            f"{parse} | {sum(r['image_fallback_used'] for r in p)} | {', '.join(served)} |"
        )
    print("\n## Live-prompt check (v3.4, 53264de9, id_asc, annotated frame, text on)")
    for r in live:
        d = r["decision"] or {}
        print(
            f"  {r['backend_id']}: served={r['served_model']} answered={r['decision'] is not None}"
            f" attempts={r['n_attempts']} refusals={r['refusal_attempts']}"
            f" category={r['refusal_category']} ends_json_only={r['ends_with_json_only_line']}"
            f" think_block={r['has_think_block']} strategy={d.get('strategy')}"
            f" yield={d.get('yield_robot')} usd={r['usd']:.4f}"
        )


def headline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Headline counts of one model x cell."""
    named = [r for r in rows if r["chosen_physical"] is not None]
    return {
        "n": len(rows),
        "census": dict(Counter(r["outcome"] for r in rows)),
        "correct": sum(r["outcome"] == "correct" for r in rows),
        "named": len(named),
        "robot1": sum(r["chosen_label"] == "robot_1" for r in named),
        "first": sum(r["chosen_physical"] == r["first_listed_physical"] for r in named),
        "strategies": dict(Counter(r["strategy"] for r in rows)),
        "att1_refused": sum(r["attempt1_refused"] for r in rows),
        "fallback": sum(r["image_fallback_used"] for r in rows),
    }


def side_by_side(new: list[dict[str, Any]], old: list[dict[str, Any]]) -> None:
    """Answer-format comparison per model and cell; never pooled."""
    print("\n## Answer-format side by side (v1 stratum | JSON-only stratum; not pooled)")
    print(
        "| Model | Cell | Stratum | n | correct | named | label robot_1 / named | "
        "first-listed / named | att-1 refused | fallback | outcomes | strategies |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for b in dict.fromkeys(r["backend_id"] for r in new):
        for arm in ARMS:
            for name, src in (("v1", old), ("json_only", new)):
                sub = [r for r in src if r["backend_id"] == b and r["arm"] == arm]
                if not sub:
                    print(f"| {b} | {arm} | {name} | 0 | - | - | - | - | - | - | - | - |")
                    continue
                h = headline(sub)
                print(
                    f"| {b} | {arm} | {name} | {h['n']} | {h['correct']} | {h['named']} | "
                    f"{h['robot1']}/{h['named']} | {h['first']}/{h['named']} | "
                    f"{h['att1_refused']} | {h['fallback']} | {h['census']} | {h['strategies']} |"
                )


def refusal_summary(new: list[dict[str, Any]]) -> None:
    """Refusals and final refusals per model."""
    print("\n## Refusals in the JSON-only stratum")
    for b in dict.fromkeys(r["backend_id"] for r in new):
        sub = [r for r in new if r["backend_id"] == b]
        att = [a for r in sub for a in r["attempts"]]
        print(
            f"  {b}: runs {len(sub)}, attempts {len(att)}, attempt-1 refused "
            f"{sum(r['attempt1_refused'] for r in sub)}, provider-refused attempts "
            f"{sum(a['provider_refusal'] for a in att)}, final refusals "
            f"{sum(r['final_refusal'] for r in sub)}, categories "
            f"{dict(Counter(a['refusal_category'] for a in att if a['refusal_category']))}, "
            f"errors {sum(1 for a in att if a['error'])}, transient "
            f"{sum(a['transient_retry'] for a in att)}"
        )


def main() -> None:
    """Print the extra tables."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=NEW_DIR)
    parser.add_argument("--old-dir", type=Path, default=OLD_DIR)
    args = parser.parse_args()
    new = load(args.out_dir / "calls.jsonl")
    old = load(args.old_dir / "calls.jsonl")
    manifest = json.loads((args.out_dir / "prompt_manifest.json").read_text())
    identity_check(new, manifest)
    pilot_table(new, load(args.out_dir / "live_v34_check.jsonl"))
    refusal_summary(new)
    side_by_side(new, old)
    ledger = load(args.out_dir / "ledger.jsonl")
    spend: dict[str, float] = defaultdict(float)
    for e in ledger:
        spend[e["backend_id"]] += e["usd"]
    print("\n## Ledger (all paid calls of this job)")
    for b, usd in spend.items():
        kinds = Counter(
            e["key"].split("|")[0] if "|" in e["key"] else e["key"]
            for e in ledger
            if e["backend_id"] == b
        )
        print(f"  {b}: usd={usd:.4f} rows={dict(kinds)}")
    print(f"  TOTAL usd={sum(spend.values()):.4f}")


if __name__ == "__main__":
    main()
