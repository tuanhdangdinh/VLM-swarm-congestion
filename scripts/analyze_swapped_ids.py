"""Tables for the head-on swapped-ID replay, per the pre-registered rules.

Reads `calls.jsonl` and `ledger.jsonl` of
data/experiments/2026-11-14-head-on-swapped-id-replay and prints every table the
design names (docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md).
No network, no keys.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

OUT_DIR = (
    Path(__file__).resolve().parents[1] / "data/experiments/2026-11-14-head-on-swapped-id-replay"
)
COMBOS = (
    ("label right", "slot right"),
    ("label right", "slot wrong"),
    ("label wrong", "slot right"),
    ("label wrong", "slot wrong"),
)


def load(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def combo(row: dict[str, Any]) -> tuple[str, str]:
    """Label x slot combination of a row: does each prior point at the correct robot?"""
    label = "label right" if row["robot1_physical"] == row["correct_physical"] else "label wrong"
    slot = "slot right" if row["first_listed_physical"] == row["correct_physical"] else "slot wrong"
    return label, slot


def kn(rows: list[dict[str, Any]], pred) -> str:
    """Format k/n for a predicate over rows."""
    return f"{sum(1 for r in rows if pred(r))}/{len(rows)}" if rows else "-"


def scene_level(rows: list[dict[str, Any]], field: str = "outcome") -> str:
    """Count scenes whose replicates are all correct, of scenes present."""
    by_scene: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_scene[r["scene"]].append(r[field])
    full = sum(1 for v in by_scene.values() if v and all(o == "correct" for o in v))
    return f"{full}/{len(by_scene)}"


def model_tables(rows: list[dict[str, Any]], model: str, field: str) -> dict[str, Any]:
    """Print one model's tables for one outcome field; return the verdict inputs."""
    is_correct = lambda r: r[field] == "correct"  # noqa: E731
    print(f"\n### {model} [{field}]")
    print("\nOutcome census per arm:")
    for arm in ("A_real", "A_grey", "B_grey"):
        sub = [r for r in rows if r["arm"] == arm]
        print(
            f"  {arm}: n={len(sub)} {dict(Counter(r[field] for r in sub))} "
            f"fallback={sum(r['image_fallback_used'] for r in sub)} "
            f"att1_refused={sum(r['attempt1_refused'] for r in sub)}"
        )
    print("\nP(correct) by side x order x arm (calls; scenes with 2/2):")
    print("| Side | Order | A_real | A_grey | B_grey |")
    print("|---|---|---|---|---|")
    for side in ("west", "east"):
        for order in ("id_asc", "id_desc"):
            cells = []
            for arm in ("A_real", "A_grey", "B_grey"):
                sub = [
                    r for r in rows if r["arm"] == arm and r["side"] == side and r["order"] == order
                ]
                cells.append(f"{kn(sub, is_correct)} [{scene_level(sub, field)}]")
            print(f"| {side} | {order} | " + " | ".join(cells) + " |")
    verdict: dict[str, Any] = {}
    for label, arms in (("grey pair", ("A_grey", "B_grey")), ("A_real", ("A_real",))):
        print(f"\nLabel x slot combinations, {label} (calls; scenes with 2/2):")
        print("| Combination | P(correct) | Scenes 2/2 | Outcomes |")
        print("|---|---|---|---|")
        combos = {}
        for c in COMBOS:
            sub = [r for r in rows if r["arm"] in arms and combo(r) == c]
            k = sum(1 for r in sub if is_correct(r))
            by_scene: dict[str, list[str]] = defaultdict(list)
            for r in sub:
                by_scene[r["scene"]].append(r[field])
            full = sum(1 for v in by_scene.values() if all(o == "correct" for o in v))
            combos[c] = (k, len(sub), full, len(by_scene))
            print(
                f"| {c[0]}, {c[1]} | {k}/{len(sub)} | {full}/{len(by_scene)} | "
                f"{dict(Counter(r[field] for r in sub))} |"
            )
        verdict[label] = combos
    named = lambda r: r[field] in ("correct", "wrong")  # noqa: E731
    chosen = "chosen_physical" if field == "outcome" else "attempt1_chosen_physical"
    print("\nMarginal effects (runs naming a yielder; 0.5 = no effect):")
    for label, arms in (
        ("grey pair", ("A_grey", "B_grey")),
        ("A_grey", ("A_grey",)),
        ("B_grey", ("B_grey",)),
        ("A_real", ("A_real",)),
    ):
        sub = [r for r in rows if r["arm"] in arms and named(r)]
        print(
            f"  {label}: n={len(sub)} "
            f"label robot_1 {kn(sub, lambda r: r[chosen] == r['robot1_physical'])}; "
            f"first-listed {kn(sub, lambda r: r[chosen] == r['first_listed_physical'])}; "
            f"scene-correct {kn(sub, lambda r: r[chosen] == r['correct_physical'])}; "
            f"west robot {kn(sub, lambda r: r[chosen] == 'west')}"
        )
        verdict[f"named:{label}"] = sub
    for order in ("id_asc", "id_desc"):
        sub = [
            r for r in rows if r["arm"] in ("A_grey", "B_grey") and named(r) and r["order"] == order
        ]
        print(
            f"  grey pair {order}: first-listed "
            f"{kn(sub, lambda r: r[chosen] == r['first_listed_physical'])}"
        )
        verdict[f"named:grey:{order}"] = sub
    verdict["chosen"] = chosen
    return verdict


def frac(sub: list[dict[str, Any]], pred) -> float | None:
    """Fraction of rows meeting a predicate, or None for no rows."""
    return sum(1 for r in sub if pred(r)) / len(sub) if sub else None


def apply_rules(model: str, rows: list[dict[str, Any]], v: dict[str, Any]) -> None:
    """Print the pre-registered verdicts."""
    chosen = v["chosen"]
    decided = {
        arm: sum(1 for r in rows if r["arm"] == arm and r["decision"] is not None)
        for arm in ("A_real", "A_grey", "B_grey")
    }
    print(f"\nVerdicts for {model} (decisions per arm {decided}):")
    if min(decided["A_grey"], decided["B_grey"]) < 20:
        print("  scene use (grey pair): NOT ASSESSABLE (< 20 decisions in a grey arm)")
    else:
        ok = all(k >= 18 and full >= 9 and n == 24 for k, n, full, _ in v["grey pair"].values())
        print(
            f"  scene use (grey pair, >=18/24 and >=9/12 scenes 2/2 in all four): "
            f"{'SUPPORTED' if ok else 'NOT SUPPORTED'}"
        )
        pa = frac(v["named:A_grey"], lambda r: r[chosen] == r["robot1_physical"])
        pb = frac(v["named:B_grey"], lambda r: r[chosen] == r["robot1_physical"])
        if pa is not None and pb is not None and pa >= 0.75 and pb >= 0.75:
            lab = "SUPPORTED toward robot_1"
        elif pa is not None and pb is not None and pa <= 0.25 and pb <= 0.25:
            lab = "SUPPORTED toward robot_2"
        else:
            lab = "NOT SUPPORTED"
        print(f"  label bias: P(robot_1) A_grey={pa} B_grey={pb} -> {lab}")
        sa = frac(v["named:grey:id_asc"], lambda r: r[chosen] == r["first_listed_physical"])
        sd = frac(v["named:grey:id_desc"], lambda r: r[chosen] == r["first_listed_physical"])
        slot = (
            "SUPPORTED"
            if sa is not None and sd is not None and sa >= 0.75 and sd >= 0.75
            else "NOT SUPPORTED"
        )
        print(f"  slot bias: P(first) asc={sa} desc={sd} -> {slot}")
    if decided["A_real"] < 20:
        print("  real-frame secondary: NOT ASSESSABLE (< 20 decisions)")
    else:
        ok = all(k >= 9 and full >= 4 and n == 12 for k, n, full, _ in v["A_real"].values())
        print(
            f"  real-frame secondary (>=9/12 and >=4/6 scenes in all four; side confounded): "
            f"{'PASSES' if ok else 'FAILS'}"
        )


def per_scene(rows: list[dict[str, Any]], model: str) -> None:
    """Print the scene-level table: chosen physical robot per replicate."""
    print(f"\nScene level, {model} (W/E = chosen physical robot, - = none; correct marked *):")
    print(
        "| Scene | Side | "
        + " | ".join(
            f"{a} {o[3:]}" for a in ("A_real", "A_grey", "B_grey") for o in ("id_asc", "id_desc")
        )
        + " |"
    )
    print("|---|---|" + "---|" * 6)
    scenes = sorted({(r["side"], r["scene"]) for r in rows}, key=lambda t: (t[0] != "west", t[1]))
    for side, scene in scenes:
        cells = []
        for arm in ("A_real", "A_grey", "B_grey"):
            for order in ("id_asc", "id_desc"):
                sub = sorted(
                    (
                        r
                        for r in rows
                        if r["scene"] == scene and r["arm"] == arm and r["order"] == order
                    ),
                    key=lambda r: r["replicate"],
                )
                marks = []
                for r in sub:
                    p = r["chosen_physical"]
                    m = {"west": "W", "east": "E"}.get(p, "-")
                    marks.append(m + ("*" if r["outcome"] == "correct" else ""))
                cells.append(" ".join(marks) or "n/a")
        print(f"| `{scene}` | {side} | " + " | ".join(cells) + " |")


def main() -> None:
    """Print all tables."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    rows = load(args.out_dir / "calls.jsonl")
    ledger = load(args.out_dir / "ledger.jsonl")
    spend: dict[str, float] = defaultdict(float)
    calls: dict[str, int] = defaultdict(int)
    for e in ledger:
        spend[e["backend_id"]] += e["usd"]
        calls[e["backend_id"]] += e["network_calls"]
    print("## Ledger")
    for b in spend:
        runs = sum(1 for r in rows if r["backend_id"] == b)
        print(f"  {b}: runs={runs} network_calls={calls[b]} usd={spend[b]:.4f}")
    print(f"  TOTAL usd={sum(spend.values()):.4f}")
    models = list(dict.fromkeys(r["backend_id"] for r in rows))
    for model in models:
        sub = [r for r in rows if r["backend_id"] == model]
        print(
            f"\n## {model} ({sub[0]['model_id']}; served {Counter(r['served_model'] for r in sub)})"
        )
        print(
            f"  prompt_matches_live by arm/order: "
            f"{Counter((r['arm'], r['order'], r['prompt_matches_live']) for r in sub)}"
        )
        print(f"  strategies: {Counter(r['strategy'] for r in sub)}")
        print(
            "  refusal categories: "
            f"{Counter(r['refusal_category'] for r in sub if r['refusal_category'])}"
        )
        print(f"  errors: {Counter((r['error'] or '')[:80] for r in sub if r['error'])}")
        v = model_tables(sub, model, "outcome")
        apply_rules(model, sub, v)
        no_fb = [r for r in sub if not r["image_fallback_used"]]
        if len(no_fb) != len(sub):
            print(f"\n  ({len(sub) - len(no_fb)} fallback rows; tables without them follow)")
            model_tables(no_fb, model + " excluding fallback rows", "outcome")
        model_tables(sub, model, "attempt1_outcome")
        per_scene(sub, model)


if __name__ == "__main__":
    main()
