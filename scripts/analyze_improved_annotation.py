"""Tables and pre-registered verdicts for the improved-annotation replay.

Written and frozen with the design before the first paid call
(docs/superpowers/specs/2026-11-14-improved-annotation-replay-design.md). Reads
`calls_<model>.jsonl`, `ledger_<model>.jsonl`, `probes.jsonl` and `budget_<model>.json`
of data/experiments/2026-11-14-improved-annotation-replay, and the earlier replay's
`calls.jsonl` for the same-day drift comparison. Counts only. No network, no keys.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-improved-annotation-replay"
PREV_DIR = REPO_ROOT / "data/experiments/2026-11-14-head-on-swapped-id-replay"

CELLS = ("L2", "D_ref", "L2+P", "D_ref+P", "C_ref", "K1", "C_ref+P", "K1+P")
CONTROL_OF = {
    "L2": "D_ref",
    "C_ref": "D_ref",
    "K1": "D_ref",
    "L2+P": "D_ref+P",
    "C_ref+P": "D_ref+P",
    "K1+P": "D_ref+P",
}
REPLICATES = {"gemini": 4, "openai": 2}
SIDES = ("west", "east")
ORDERS = ("id_asc", "id_desc")
SCENES_PER_SIDE = 12
RUN_SHARE = 0.75  # of runs correct in each side x order cell
SCENE_SHARE = 0.75  # of a scene's replicates correct, for a scene to count
SCENES_NEEDED = 8  # of 12 scenes per side x order cell
CONTROL_MARGIN = 0.25
LEGIBILITY_MARGIN = 0.15
LINE_FLAG_OVERALL = 0.15
LINE_FLAG_SIDE = 0.25
MIN_DECISIONS = 20
COND_MIN_NAMED_PER_SIDE = 12
COND_MIN_SCENES_PER_SIDE = 6
COND_MIN_PER_ORDER = 4
COND_ACCURACY = 0.80


def load(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, tolerating a missing file."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def planned_runs(model: str) -> int:
    """Runs per cell: 24 scenes x 2 orders x replicates."""
    return 2 * SCENES_PER_SIDE * len(ORDERS) * REPLICATES[model]


def p_correct(rows: list[dict[str, Any]], field: str = "outcome") -> float | None:
    """Share of rows whose outcome is correct, or None for no rows."""
    return sum(r[field] == "correct" for r in rows) / len(rows) if rows else None


def scenes_mostly_correct(rows: list[dict[str, Any]], field: str = "outcome") -> int:
    """Scenes whose replicates are at least 75% correct (2/2 gpt-4o, 3/4 ER-2)."""
    by: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by[r["scene"]].append(r[field])
    return sum(
        1 for v in by.values() if v and sum(o == "correct" for o in v) >= SCENE_SHARE * len(v)
    )


def assessable(model: str, rows: list[dict[str, Any]], cell: str) -> tuple[bool, str]:
    """A cell is assessable when complete and holding at least 20 decisions."""
    sub = [r for r in rows if r["cell"] == cell]
    decided = sum(r["decision"] is not None for r in sub)
    if len(sub) < planned_runs(model):
        return False, f"incomplete ({len(sub)}/{planned_runs(model)} runs)"
    if decided < MIN_DECISIONS:
        return False, f"{decided} decisions < {MIN_DECISIONS}"
    return True, f"{len(sub)} runs, {decided} decisions"


def rule1(
    model: str, rows: list[dict[str, Any]], cell: str, field: str = "outcome"
) -> dict[str, Any]:
    """Rule 1 (image use) for one cell against its same-prompt grey control.

    All three must hold:
    - in each side x order cell, correct runs >= 75% of the planned runs there
      (gpt-4o 18/24, ER-2 36/48);
    - in each side x order cell, >= 8 of the side's 12 scenes have >= 75% of their
      replicates correct (gpt-4o 2/2, ER-2 3/4);
    - P(correct | cell) - P(correct | control) >= 0.25 over all runs.
    """
    control = CONTROL_OF[cell]
    ok_v, why_v = assessable(model, rows, cell)
    ok_c, why_c = assessable(model, rows, control)
    out: dict[str, Any] = {"cell": cell, "control": control}
    if not (ok_v and ok_c):
        out["verdict"] = f"NOT ASSESSABLE ({cell}: {why_v}; {control}: {why_c})"
        return out
    per_cell_runs = planned_runs(model) // 4
    cells_ok = True
    detail = {}
    for side in SIDES:
        for order in ORDERS:
            sub = [
                r for r in rows if r["cell"] == cell and r["side"] == side and r["order"] == order
            ]
            k = sum(r[field] == "correct" for r in sub)
            s = scenes_mostly_correct(sub, field)
            passed = k >= RUN_SHARE * per_cell_runs and s >= SCENES_NEEDED
            detail[f"{side}/{order}"] = f"{k}/{len(sub)} runs, {s}/12 scenes"
            cells_ok &= passed
    pv = p_correct([r for r in rows if r["cell"] == cell], field)
    pc = p_correct([r for r in rows if r["cell"] == control], field)
    margin_ok = pv - pc >= CONTROL_MARGIN
    out.update(
        detail=detail,
        cells_ok=cells_ok,
        p=pv,
        p_control=pc,
        margin=pv - pc,
        margin_ok=margin_ok,
        verdict="PASSES" if cells_ok and margin_ok else "FAILS",
    )
    return out


def conditional_rule(model: str, rows: list[dict[str, Any]], cell: str) -> dict[str, Any]:
    """ER-2 conditional image use, among runs that name a yielder (orders pooled).

    Per side: >= 12 named runs, from >= 6 of the 12 scenes, >= 4 in each order;
    named-correct >= 0.80 on each side; and either the control is not assessable
    on the same criteria, or the cell's conditional accuracy (sides pooled)
    exceeds the control's by >= 0.25.
    """

    def stats(c: str) -> dict[str, Any]:
        named = [r for r in rows if r["cell"] == c and r["outcome"] in ("correct", "wrong")]
        res: dict[str, Any] = {"named": len(named), "sides": {}}
        enough = True
        for side in SIDES:
            sub = [r for r in named if r["side"] == side]
            per_order = {o: sum(r["order"] == o for r in sub) for o in ORDERS}
            scenes = len({r["scene"] for r in sub})
            acc = p_correct(sub)
            res["sides"][side] = {
                "named": len(sub),
                "scenes": scenes,
                "per_order": per_order,
                "accuracy": acc,
            }
            enough &= (
                len(sub) >= COND_MIN_NAMED_PER_SIDE
                and scenes >= COND_MIN_SCENES_PER_SIDE
                and min(per_order.values()) >= COND_MIN_PER_ORDER
            )
        res["assessable"] = enough
        res["accuracy"] = p_correct(named)
        return res

    control = CONTROL_OF[cell]
    v, c = stats(cell), stats(control)
    if not v["assessable"]:
        verdict = "NOT ASSESSABLE (too few named runs)"
    else:
        sides_ok = all(s["accuracy"] >= COND_ACCURACY for s in v["sides"].values())
        if c["assessable"]:
            margin_ok = v["accuracy"] - c["accuracy"] >= CONTROL_MARGIN
        else:
            margin_ok = True
        verdict = "PASSES" if sides_ok and margin_ok else "FAILS"
    return {
        "cell": cell,
        "control": control,
        "cell_stats": v,
        "control_stats": c,
        "verdict": verdict,
    }


def legibility(r_l: dict[str, Any], r_c: dict[str, Any]) -> str:
    """Rule 2: L passes rule 1, C fails it, and P(L) - P(C) >= 0.15."""
    if "p" not in r_l or "p" not in r_c:
        return "NOT ASSESSABLE"
    ok = (
        r_l["verdict"] == "PASSES"
        and r_c["verdict"] == "FAILS"
        and r_l["p"] - r_c["p"] >= LEGIBILITY_MARGIN
    )
    return f"{'SUPPORTED' if ok else 'NOT SUPPORTED'} (P(L) - P(C) = {r_l['p'] - r_c['p']:+.3f})"


def line_effect(rows: list[dict[str, Any]], with_line: str, without: str) -> dict[str, Any]:
    """Change in P(correct) from adding the line, overall and per side x order."""
    a = [r for r in rows if r["cell"] == with_line]
    b = [r for r in rows if r["cell"] == without]
    if not a or not b:
        return {"pair": f"{with_line} - {without}", "delta": None}
    out: dict[str, Any] = {
        "pair": f"{with_line} - {without}",
        "delta": p_correct(a) - p_correct(b),
        "per_side": {},
        "per_cell": {},
    }
    for side in SIDES:
        sa = [r for r in a if r["side"] == side]
        sb = [r for r in b if r["side"] == side]
        out["per_side"][side] = p_correct(sa) - p_correct(sb)
        for order in ORDERS:
            ca = [r for r in sa if r["order"] == order]
            cb = [r for r in sb if r["order"] == order]
            out["per_cell"][f"{side}/{order}"] = p_correct(ca) - p_correct(cb)
    return out


def line_alone_flag(effect: dict[str, Any]) -> str:
    """D_ref+P check: does the line move correctness with the grey image?

    Flags when D_ref+P - D_ref >= 0.15 overall (leak), or when either side moves
    by >= 0.25 in absolute value (a bias shift that may cancel overall).
    """
    if effect["delta"] is None:
        return "NOT ASSESSABLE"
    side_shift = max(abs(v) for v in effect["per_side"].values())
    if effect["delta"] >= LINE_FLAG_OVERALL:
        return f"FLAG: leak (overall {effect['delta']:+.3f})"
    if side_shift >= LINE_FLAG_SIDE:
        return f"FLAG: bias shift (largest side change {side_shift:+.3f})"
    return f"no flag (overall {effect['delta']:+.3f}, largest side change {side_shift:.3f})"


def census(rows: list[dict[str, Any]], cells: tuple[str, ...]) -> None:
    """Outcome census and strategy distribution per cell."""
    print(
        "\n| Cell | Runs | Correct | Wrong | No yielder | Refusal | Parse fail | Error | "
        "Fallback | Att-1 refused | Strategies |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for cell in cells:
        sub = [r for r in rows if r["cell"] == cell]
        if not sub:
            continue
        c = Counter(r["outcome"] for r in sub)
        strat = Counter(r["strategy"] for r in sub)
        rev_noy = sum(1 for r in sub if r["strategy"] == "reverse" and not r["yield_robot"])
        print(
            f"| `{cell}` | {len(sub)} | {c['correct']} | {c['wrong']} | {c['no_yielder']} | "
            f"{c['refusal']} | {c['parse_failure']} | {c['error']} | "
            f"{sum(r['image_fallback_used'] for r in sub)} | "
            f"{sum(r['attempt1_refused'] for r in sub)} | "
            f"{dict(strat)}; reverse w/o yielder {rev_noy} |"
        )


def side_order_table(
    rows: list[dict[str, Any]], cells: tuple[str, ...], field: str = "outcome"
) -> None:
    """P(correct) per side x order x cell: runs, and scenes >= 75% correct of 12."""
    present = [c for c in cells if any(r["cell"] == c for r in rows)]
    print("\n| Side | Order | " + " | ".join(f"`{c}`" for c in present) + " |")
    print("|---|---|" + "---|" * len(present))
    for side in SIDES:
        for order in ORDERS:
            out = []
            for cell in present:
                sub = [
                    r
                    for r in rows
                    if r["cell"] == cell and r["side"] == side and r["order"] == order
                ]
                k = sum(r[field] == "correct" for r in sub)
                out.append(f"{k}/{len(sub)} [{scenes_mostly_correct(sub, field)}]")
            print(f"| {side} | `{order}` | " + " | ".join(out) + " |")
    tot = []
    for cell in present:
        sub = [r for r in rows if r["cell"] == cell]
        tot.append(f"{sum(r[field] == 'correct' for r in sub)}/{len(sub)}")
    print("| all | all | " + " | ".join(tot) + " |")


def named_table(rows: list[dict[str, Any]], cells: tuple[str, ...]) -> None:
    """Among runs naming a yielder: correct, west robot, first-listed robot."""
    print(
        "\n| Cell | Named | Correct | West robot | First-listed | West side correct | "
        "East side correct |"
    )
    print("|---|---|---|---|---|---|---|")
    for cell in cells:
        named = [r for r in rows if r["cell"] == cell and r["outcome"] in ("correct", "wrong")]
        if not any(r["cell"] == cell for r in rows):
            continue
        w = [r for r in named if r["side"] == "west"]
        e = [r for r in named if r["side"] == "east"]
        print(
            f"| `{cell}` | {len(named)} | {sum(r['outcome'] == 'correct' for r in named)} | "
            f"{sum(r['chosen_physical'] == 'west' for r in named)} | "
            f"{sum(r['chosen_physical'] == r['first_listed_physical'] for r in named)} | "
            f"{sum(r['outcome'] == 'correct' for r in w)}/{len(w)} | "
            f"{sum(r['outcome'] == 'correct' for r in e)}/{len(e)} |"
        )


def scene_table(rows: list[dict[str, Any]], cells: tuple[str, ...]) -> None:
    """Per scene x cell: correct replicates over both orders (asc / desc)."""
    present = [c for c in cells if any(r["cell"] == c for r in rows)]
    print("\n| Scene | Side | Set | " + " | ".join(f"`{c}` asc/desc" for c in present) + " |")
    print("|---|---|---|" + "---|" * len(present))
    scenes = sorted(
        {(r["side"], r["scene"], r["scene_set"]) for r in rows},
        key=lambda t: (t[0] != "west", t[2] != "original", t[1]),
    )
    for side, scene, sset in scenes:
        out = []
        for cell in present:
            parts = []
            for order in ORDERS:
                sub = [
                    r
                    for r in rows
                    if r["scene"] == scene and r["cell"] == cell and r["order"] == order
                ]
                parts.append(f"{sum(r['outcome'] == 'correct' for r in sub)}/{len(sub)}")
            out.append(" ".join(parts))
        print(f"| `{scene}` | {side} | {sset} | " + " | ".join(out) + " |")


def drift(rows: list[dict[str, Any]], prev: list[dict[str, Any]], model: str) -> None:
    """Same-day drift check: earlier C_real_notext / D_grey_notext vs C_ref / D_ref.

    Original 12 scenes only, side by side, never pooled.
    """
    print(
        "\n| Side | Order | earlier `C_real_notext` | this `C_ref` | earlier `D_grey_notext` | "
        "this `D_ref` |"
    )
    print("|---|---|---|---|---|---|")
    old = [r for r in prev if r["backend_id"] == model]
    new = [r for r in rows if r["scene_set"] == "original"]
    for side in SIDES:
        for order in ORDERS:
            out = []
            for src, cell in (
                (old, "C_real_notext"),
                (new, "C_ref"),
                (old, "D_grey_notext"),
                (new, "D_ref"),
            ):
                key = "arm" if src is old else "cell"
                sub = [
                    r for r in src if r[key] == cell and r["side"] == side and r["order"] == order
                ]
                out.append(f"{sum(r['outcome'] == 'correct' for r in sub)}/{len(sub)}")
            print(f"| {side} | `{order}` | " + " | ".join(out) + " |")
    for src, key, cells in (
        (old, "arm", ("C_real_notext", "D_grey_notext")),
        (new, "cell", ("C_ref", "D_ref")),
    ):
        for cell in cells:
            sub = [r for r in src if r[key] == cell]
            print(
                f"  {cell}: {dict(Counter(r['outcome'] for r in sub))}; "
                f"strategies {dict(Counter(r['strategy'] for r in sub))}"
            )


def report_model(model: str, rows: list[dict[str, Any]], prev: list[dict[str, Any]]) -> None:
    """Print every table and verdict for one model."""
    cells = tuple(c for c in CELLS if any(r["cell"] == c for r in rows))
    print(f"\n## {model}: {len(rows)} runs; cells present {cells}")
    print(f"  served models: {dict(Counter(r['served_model'] for r in rows))}")
    print(
        "  served per attempt: "
        f"{dict(Counter(m for r in rows for m in r['served_models_per_attempt']))}"
    )
    print(
        f"  prompt sent matches manifest: {dict(Counter(r['prompt_sent_matches'] for r in rows))}"
    )
    print(f"  pilot rows: {dict(Counter(r['cell'] for r in rows if r['pilot']))}")
    print(f"  errors: {dict(Counter((r['error'] or '')[:80] for r in rows if r['error']))}")
    categories = Counter(r["refusal_category"] for r in rows if r["refusal_category"])
    print(f"  refusal categories: {dict(categories)}")
    stamps = sorted(r["stamp_start_utc"] for r in rows)
    if stamps:
        print(f"  first call {stamps[0]}, last call {stamps[-1]}")
    print("\n### Census")
    census(rows, cells)
    print("\n### P(correct), runs [scenes with >= 75% of replicates correct, of 12]")
    side_order_table(rows, cells)
    print("\n### Runs naming a yielder")
    named_table(rows, cells)
    print("\n### Verdicts")
    results = {}
    for cell in ("L2", "C_ref", "L2+P", "C_ref+P", "K1", "K1+P"):
        if cell not in cells:
            continue
        res = rule1(model, rows, cell)
        results[cell] = res
        heading = (
            "annotation reading (rule 3, Type K)" if cell.startswith("K1") else "image use (rule 1)"
        )
        print(f"- `{cell}` {heading} vs `{res['control']}`: **{res['verdict']}**")
        if "detail" in res:
            print(
                f"    {res['detail']}; P={res['p']:.3f} control={res['p_control']:.3f} "
                f"margin={res['margin']:+.3f}"
            )
    for l_cell, c_cell in (("L2", "C_ref"), ("L2+P", "C_ref+P")):
        if l_cell in results and c_cell in results:
            print(
                f"- legibility (rule 2) `{l_cell}` vs `{c_cell}`: "
                f"{legibility(results[l_cell], results[c_cell])}"
            )
    print("\n### Prompt-line effect (D_ref+P check first)")
    d_eff = line_effect(rows, "D_ref+P", "D_ref")
    print(f"- D_ref+P - D_ref: {d_eff}")
    print(f"  -> line-alone check: **{line_alone_flag(d_eff)}**")
    for pair in (("L2+P", "L2"), ("C_ref+P", "C_ref"), ("K1+P", "K1")):
        print(f"- {line_effect(rows, *pair)}")
    if model == "gemini":
        print("\n### ER-2 conditional image use (named runs only)")
        for cell in ("L2", "C_ref", "L2+P", "C_ref+P", "K1", "K1+P"):
            if cell not in cells:
                continue
            res = conditional_rule(model, rows, cell)
            label = " (annotation reading)" if cell.startswith("K1") else ""
            print(f"- `{cell}`{label} vs `{res['control']}`: **{res['verdict']}**")
            print(f"    cell {res['cell_stats']}")
            print(f"    control {res['control_stats']}")
    if model == "openai":
        no_fb = [r for r in rows if not r["image_fallback_used"]]
        print(f"\n### Excluding {len(rows) - len(no_fb)} fallback rows")
        side_order_table(no_fb, cells)
        print("\n### Attempt-1 outcome")
        side_order_table(rows, cells, "attempt1_outcome")
    print("\n### Scene level (correct replicates; asc / desc)")
    scene_table(rows, cells)
    print("\n### Same-day drift: earlier replay vs this run, original 12 scenes")
    drift(rows, prev, model)


def main() -> None:
    """Print the ledger, every table and every verdict."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--prev-dir", type=Path, default=PREV_DIR)
    args = parser.parse_args()
    prev = load(args.prev_dir / "calls.jsonl")
    print("## Ledger")
    grand = 0.0
    for probe in load(args.out_dir / "probes.jsonl"):
        print(
            f"  probe {probe['backend_id']}: ok={probe['ok']} usd={probe.get('usd', 0):.5f} "
            f"served={probe.get('served_model')}"
        )
        grand += probe.get("usd", 0.0)
    for model in REPLICATES:
        ledger = load(args.out_dir / f"ledger_{model}.jsonl")
        usd = sum(e["usd"] for e in ledger)
        calls = sum(e["network_calls"] for e in ledger)
        retries = sum(e["transient_retries"] for e in ledger)
        grand += usd
        print(
            f"  {model}: runs={len(ledger)} network_calls={calls} transient_retries={retries} "
            f"usd={usd:.4f}"
        )
        budget = args.out_dir / f"budget_{model}.json"
        if budget.is_file():
            print(f"  {model} budget decision: {budget.read_text()}")
    print(f"  TOTAL usd={grand:.4f}")
    for model in REPLICATES:
        rows = load(args.out_dir / f"calls_{model}.jsonl")
        if rows:
            report_model(model, rows, prev)


if __name__ == "__main__":
    main()
