"""PILOT (exploratory, non-confirmatory): dataset-card statistics for the V-JEPA 2 probe pilot."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402
import probe as P  # noqa: E402


def main() -> None:
    ds = json.loads((c.OUT_ROOT / "dataset.json").read_text())
    inv = json.loads((c.OUT_ROOT / "inventory.json").read_text())
    meta = json.loads((P.FEAT / "index.json").read_text())
    S = meta["samples"]
    out = {"extraction_seconds": meta["seconds"], "n_extracted": len(S)}
    out["inventory_unusable"] = [(r["run_id"], r.get("reason")) for r in inv if not r.get("usable") and not r["run_id"].endswith(".log")]
    out["episodes"] = [
        {k: e[k] for k in ("run_id", "role", "role_reason", "scenario", "seed", "source", "n_robots")}
        for e in ds["episodes"]
    ]
    out["roles"] = Counter(e["role"] for e in ds["episodes"])
    conf = defaultdict(Counter)
    for s in S:
        if s["task"] == "conflict" and s.get("role") in ("train", "test"):
            conf[s["role"]][("cmdfree" if s.get("command_free") else "cmd") + ("_yes" if s["label"] else "_no")] += 1
    out["conflict_counts"] = conf
    temp = defaultdict(Counter)
    for s in S:
        if s["task"] == "temporal_robot" and s.get("role") in ("train", "test") and not s.get("from_pair"):
            b = s["still_sec"]
            bucket = "moving(<0.5)" if b < 0.5 else "0.5-3" if b <= 3 else "3-8" if b <= 8 else "8-30" if b < 30 else ">=30"
            temp[s["role"]][bucket] += 1
    out["temporal_robot_counts"] = temp
    for role in ("train", "test"):
        pairs = P.broad_pairs(P.temporal_train_set(S, role))
        lo = sum(P.lower_id(a["robot"], b["robot"]) == f for a, b, f in pairs)
        out[f"broad_pairs_{role}"] = {"n": len(pairs), "lower_id_correct": lo, "episodes": len({a["run_id"] for a, _, _ in pairs})}
    out["battery_mapping"] = Counter("|".join(map(str, k)) for k in ((b["probe_type"], b["mappable"], b.get("unmappable_reason")) for b in ds["battery"]))
    out["battery_mapped_items"] = [b["item_id"] for b in ds["battery"] if b["mappable"]]
    spans = [s["frame_times"][-1] - s["frame_times"][0] for s in S]
    dups = sum(1 for s in S if len(set(s["frame_times"])) < len(s["frame_times"]))
    out["clip_span_sec"] = {"min": min(spans), "max": max(spans), "mean": sum(spans) / len(spans)}
    out["clips_with_repeated_frame"] = dups
    (c.OUT_ROOT / "stats.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
