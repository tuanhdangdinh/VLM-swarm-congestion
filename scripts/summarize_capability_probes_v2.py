#!/usr/bin/env python3
# ruff: noqa: E501
"""Summarize battery-v2 live runs (docs/reports/2026-10-04-battery-v2-results.md).

Reads `<run_root>/<backend>__<arm>/*.jsonl` (arm = main | trails_pair_off |
trails_pair_on) written by `scripts/capability_probes.py` and prints
accuracy with Wilson 95% CIs per backend x arm x type, the sub-splits the
report quotes (yes/no, edge/robot target, goal/stop, lower-id heuristic),
the trails-pair discordance table, letter/first-slot checks and spend at
list prices. Read-only; no backend calls.

Usage: python scripts/summarize_capability_probes_v2.py <run_root>
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from reasoning.vlm.capability_probes.scorer import wilson_interval  # noqa: E402

PRICES = {"openai": (2.50, 10.00), "gemini": (1.00, 5.00)}
manifest = json.loads((REPO / "reasoning/vlm/capability_probes/manifest_v2.json").read_text())
items = {i["item_id"]: i for i in manifest["items"]}
run_root = Path(sys.argv[1])

records = defaultdict(list)  # (backend, arm) -> records
for path in sorted(run_root.glob("*/*.jsonl")):
    if path.name.endswith("_aborted.jsonl"):
        continue
    arm = path.parent.name.split("__", 1)[1]
    for line in path.read_text().splitlines():
        r = json.loads(line)
        records[(r["backend_id"], arm)].append(r)


def fmt(c, n):
    lo, hi = wilson_interval(c, n)
    return f"{c}/{n} ({c / n:.0%}) [{lo:.3f}, {hi:.3f}]" if n else "-"


print("## accuracy")
for (backend, arm), recs in sorted(records.items()):
    by = defaultdict(list)
    for r in recs:
        by[r["probe_type"]].append(r)
    tot = sum(r["correct"] for r in recs)
    print(f"{backend} {arm}: overall {fmt(tot, len(recs))}")
    for t, rs in sorted(by.items()):
        causes = Counter(r["failure_cause"] or "none" for r in rs)
        chance = sum(1 / len(items[r["item_id"]]["options"]) for r in rs) / len(rs)
        print(
            f"   {t}: {fmt(sum(r['correct'] for r in rs), len(rs))} chance={chance:.3f} causes={dict(causes)}"
        )
        # sub-splits
        if t == "conflict_prediction":
            for ans in ("yes", "no"):
                sub = [r for r in rs if items[r["item_id"]]["correct_answer"] == ans]
                print(
                    f"      gt={ans}: {fmt(sum(r['correct'] for r in sub), len(sub))}; answered yes: "
                    f"{sum(1 for r in sub if r.get('parsed_option') == 'yes')}"
                )
        if t == "temporal_order":
            for kind in ("goal", "stop"):
                sub = [r for r in rs if items[r["item_id"]]["question_key"].startswith(kind)]
                if sub:
                    print(f"      {kind}: {fmt(sum(r['correct'] for r in sub), len(sub))}")
            sub = [r for r in rs]
            low = sum(
                1 for r in sub if r.get("parsed_option") == min(items[r["item_id"]]["options"])
            )
            base = sum(
                1
                for r in sub
                if items[r["item_id"]]["correct_answer"] == min(items[r["item_id"]]["options"])
            )
            print(
                f"      picked lower id: {low}/{len(sub)}; lower-id heuristic would score {base}/{len(sub)}"
            )
            for slot in (0, 1):
                ss = [
                    r
                    for r in rs
                    if items[r["item_id"]]["options"].index(items[r["item_id"]]["correct_answer"])
                    == slot
                ]
                if ss:
                    print(
                        f"      correct=slot{slot} (lower id={slot == 0}): {fmt(sum(r['correct'] for r in ss), len(ss))}"
                    )
        if t == "motion_direction":
            for kind in ("edge", "robot"):
                sub = [r for r in rs if items[r["item_id"]]["question_key"].startswith(kind)]
                if sub:
                    print(f"      {kind}: {fmt(sum(r['correct'] for r in sub), len(sub))}")
            r1 = [r for r in rs if r.get("parsed_option") == "robot_1"]
            r1w = [r for r in r1 if not r["correct"]]
            print(
                f"      robot_1 picks {len(r1)}, wrong {len(r1w)}; robot_1 correct in "
                f"{sum(1 for r in rs if items[r['item_id']]['correct_answer'] == 'robot_1')}"
            )
    letters = Counter(r["parsed_letter"] for r in recs)
    first = sum(
        1
        for r in recs
        if r["parsed_letter"] and r["listing_order"] and r["parsed_letter"] == r["listing_order"][0]
    )
    first_correct = sum(
        1 for r in recs if r["listing_order"] and r["correct_letter"] == r["listing_order"][0]
    )
    print(
        f"   letters={dict(letters)} first-listed picked={first}/{len(recs)} first-listed correct={first_correct}"
    )
    served = Counter(r.get("served_model") for r in recs)
    print(f"   served={dict(served)}")

print("## pairs")
for backend in sorted({b for b, _ in records}):
    off = {items[r["item_id"]]["pair_id"]: r for r in records.get((backend, "trails_pair_off"), [])}
    on = {items[r["item_id"]]["pair_id"]: r for r in records.get((backend, "trails_pair_on"), [])}
    by = defaultdict(lambda: Counter())
    for pid in sorted(set(off) & set(on)):
        t = items[off[pid]["item_id"]]["probe_type"]
        key = (off[pid]["correct"], on[pid]["correct"])
        for tt in (t, "ALL"):
            by[tt][key] += 1
    for t, c in sorted(by.items()):
        n = sum(c.values())
        offc = c[(True, True)] + c[(True, False)]
        onc = c[(True, True)] + c[(False, True)]
        print(
            f"{backend} {t}: n={n} off {fmt(offc, n)} on {fmt(onc, n)} both={c[(True, True)]} "
            f"off_only={c[(True, False)]} on_only={c[(False, True)]} neither={c[(False, False)]}"
        )

print("## spend")
total = 0.0
for backend in sorted({b for b, _ in records}):
    tin = tout = 0
    for (b, _), recs in records.items():
        if b != backend:
            continue
        for r in recs:
            u = r.get("token_usage") or {}
            tin += u.get("prompt_tokens", 0)
            tout += u.get("completion_tokens", 0) + u.get("thought_tokens", 0)
    pi, po = PRICES[backend]
    cost = tin / 1e6 * pi + tout / 1e6 * po
    total += cost
    print(f"{backend}: in={tin} out={tout} cost=${cost:.3f}")
print(f"total ${total:.3f}")
