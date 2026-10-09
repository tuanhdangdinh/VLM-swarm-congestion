"""Measure S1 live episodes under the S1 Monte Carlo's own conflict definition.

The S1 kinematic Monte Carlo (scene design S1 "Sources and Method") calls an
*encounter* a ground-truth centre gap below 0.45 m between two robots. This
script applies exactly that definition to recorded S1 bundles (GT JSONL at
10 Hz) and, in parallel, to M1's scene log (the poses the M4 safety monitor
latches on), so the S1b Monte Carlo gate can be derived from measured S1a
data rather than invented (prereg-v3 R3.6a item 4).

Times are reported relative to the episode start: robot_1's release on the
M1 scene clock (tasks JSONL ``released`` event), mapped onto the GT clock by
the bundle's fitted GT offset (GT sim-s = M1 stamp - offset; the same fit as
the S1 bundle analyser, grid 0.00-1.00 s, median position error of MOVING
rows).

Usage:
    python scripts/s1_live_conflict_stats.py <bundle_dir> [<bundle_dir> ...]

Prints one JSON object per bundle.
"""

from __future__ import annotations

import bisect
import glob
import json
import math
import statistics
import sys
from pathlib import Path

ENCOUNTER_M = 0.45


def _jl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open() if line.strip()]


def _gt_offset(gt: list[dict], scene: list[dict]) -> float:
    gt_t = [r["sim_time_sec"] for r in gt]

    def at(t: float) -> dict:
        i = bisect.bisect_left(gt_t, t)
        return gt[min(max(i, 0), len(gt) - 1)]

    moving = [
        (r["scene"]["stamp"], v["robot_id"], v["x"], v["y"])
        for r in scene
        if r["scene"].get("stamp") is not None
        for v in r["scene"]["robots"]
        if v["status"] == "MOVING"
    ]
    moving = moving[:: max(1, len(moving) // 3000)]
    best: tuple[float, float] | None = None
    for k in range(101):
        off = k / 100.0
        errs = [
            math.hypot(x - at(st - off)["robots"][rid]["x"], y - at(st - off)["robots"][rid]["y"])
            for st, rid, x, y in moving
        ]
        if errs:
            med = statistics.median(errs)
            if best is None or med < best[1]:
                best = (off, med)
    return best[0] if best else 0.0


def _pair_intervals(
    samples: list[tuple[float, dict[str, tuple[float, float]]]],
) -> dict[tuple[str, str], list[dict]]:
    """Contiguous intervals with centre gap < ENCOUNTER_M, per robot pair."""
    out: dict[tuple[str, str], list[dict]] = {}
    open_: dict[tuple[str, str], dict] = {}
    for t, poses in samples:
        ids = sorted(poses, key=lambda r: int(r.split("_")[1]))
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                pa, pb = poses[a], poses[b]
                gap = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                key = (a, b)
                if gap < ENCOUNTER_M:
                    iv = open_.get(key)
                    if iv is None:
                        iv = {
                            "onset": t,
                            "end": t,
                            "min_gap": gap,
                            "mid": ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2),
                        }
                        open_[key] = iv
                    iv["end"] = t
                    iv["min_gap"] = min(iv["min_gap"], gap)
                elif key in open_:
                    out.setdefault(key, []).append(open_.pop(key))
    for key, iv in open_.items():
        iv["to_end"] = True
        out.setdefault(key, []).append(iv)
    return out


def _clusters(samples, t_rel) -> dict:
    """Times at which the largest <0.45 m connected component first reaches k."""
    first_k: dict[int, float] = {}
    for t, poses in samples:
        ids = list(poses)
        parent = {r: r for r in ids}

        def find(r, parent=parent):
            while parent[r] != r:
                parent[r] = parent[parent[r]]
                r = parent[r]
            return r

        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if math.hypot(poses[a][0] - poses[b][0], poses[a][1] - poses[b][1]) < ENCOUNTER_M:
                    parent[find(a)] = find(b)
        sizes: dict[str, int] = {}
        for r in ids:
            sizes[find(r)] = sizes.get(find(r), 0) + 1
        big = max(sizes.values()) if sizes else 0
        for k in range(2, big + 1):
            first_k.setdefault(k, round(t_rel(t), 2))
    return first_k


def analyse(bundle: Path) -> dict:
    """Return the encounter/latch statistics of one S1 bundle."""
    gt = _jl(bundle / "gt" / "ground_truth.jsonl")
    scene = _jl(bundle / "m5_scene.jsonl")
    tasks = _jl(Path(sorted(glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")))[0]))
    releases = {e["robot_id"]: e.get("sim_t") for e in tasks if e.get("event") == "released"}
    off = _gt_offset(gt, scene)
    t0_m1 = releases.get("robot_1")
    if t0_m1 is None:
        # Pilot ep1 (wall-clock stagger): robot_1's release precedes the first
        # scene; the bundle analyser maps it onto the first scene stamp.
        t0_m1 = min(r["scene"]["stamp"] for r in scene if r["scene"].get("stamp") is not None)
    t0_gt = t0_m1 - off

    gt_samples = [
        (r["sim_time_sec"], {rid: (v["x"], v["y"]) for rid, v in r["robots"].items()}) for r in gt
    ]
    gt_ivs = _pair_intervals(gt_samples)
    m1_samples = []
    for r in scene:
        st = r["scene"].get("stamp")
        if st is None or r["scene"].get("dropped_frame"):
            continue
        m1_samples.append(
            (
                st,
                {
                    v["robot_id"]: (v["x"], v["y"])
                    for v in r["scene"]["robots"]
                    if v["status"] != "STALE"
                },
            )
        )
    m1_ivs = _pair_intervals(m1_samples)
    end_gt = gt_samples[-1][0]

    def rows(ivs, t_ref, end):
        flat = []
        for (a, b), lst in ivs.items():
            for iv in lst:
                flat.append(
                    {
                        "pair": f"{a}+{b}",
                        "onset_rel_s": round(iv["onset"] - t_ref, 2),
                        "duration_s": round(iv["end"] - iv["onset"], 2),
                        "to_episode_end": bool(iv.get("to_end")),
                        "min_gap_m": round(iv["min_gap"], 3),
                        "mid_xy": [round(iv["mid"][0], 2), round(iv["mid"][1], 2)],
                    }
                )
        flat.sort(key=lambda r: r["onset_rel_s"])
        return flat

    gt_rows = rows(gt_ivs, t0_gt, end_gt)
    m1_rows = rows(m1_ivs, t0_m1, None)
    return {
        "bundle": str(bundle),
        "gt_offset_s": off,
        "release_m1_sim": releases,
        "t0_m1_sim": t0_m1,
        "gt_end_rel_s": round(end_gt - t0_gt, 1),
        "gt_encounters": gt_rows,
        "gt_first_encounter_rel_s": gt_rows[0]["onset_rel_s"] if gt_rows else None,
        "gt_pairs_ever": len(gt_ivs),
        "gt_permanent_pairs": sum(1 for r in gt_rows if r["to_episode_end"]),
        "gt_transient_intervals": sum(1 for r in gt_rows if not r["to_episode_end"]),
        "gt_cluster_first_k_rel_s": _clusters(gt_samples, lambda t: t - t0_gt),
        "m1_latch_encounters": m1_rows,
        "m1_first_latch_rel_s": m1_rows[0]["onset_rel_s"] if m1_rows else None,
        "m1_first_latch_abs_sim": round(m1_rows[0]["onset_rel_s"] + t0_m1, 2) if m1_rows else None,
    }


def main() -> None:
    """Entry point."""
    for arg in sys.argv[1:]:
        print(json.dumps(analyse(Path(arg))))


if __name__ == "__main__":
    main()
