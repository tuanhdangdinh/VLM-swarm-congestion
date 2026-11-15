"""Recompute footprint contacts offline from an existing run bundle.

Reads a bundle's ground truth (`gt/ground_truth.jsonl`) and its
`scenario.yaml`, places the TurtleBot3 Burger URDF collision shapes at every
logged `base_link` pose, and measures the signed gap to every box the scene
builders author and to every other robot, with the same functions the live
logger uses (`isaac/vgu_sim/contact_geometry.py`). Bundles are only read;
everything is written under `--out-dir`, which must lie outside every bundle.

Per bundle it writes `<label>.summary.json` (contact events, minima, the
classification) and, with `--rows`, `rows/<label>.contacts.jsonl` holding the
fields a new-style GT row carries (`robot_static_contacts`,
`robot_robot_contacts`, `min_static_gap_m`, `min_robot_robot_gap_m`).
`index.json` collects the per-bundle verdicts.

Classification of one robot-obstacle or robot-robot pair:
  * `sustained_contact`: some run of consecutive rows within
    `CONTACT_GAP_THRESHOLD_M` spans at least `SUSTAINED_CONTACT_MIN_SEC`;
  * `brief_graze`: within the threshold, but never for that long. At 10 Hz a
    moving robot advances `speed * 0.1 s` between rows, reported per event
    as `row_resolution_m`, so a millimetre-level brief graze is within the
    pose and sampling noise and is not established contact;
  * `clear`: never within the threshold.

Usage:
    python scripts/recompute_gt_contacts.py BUNDLE [BUNDLE ...] --out-dir DIR [--rows]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from isaac.vgu_sim.config import ScenarioConfig  # noqa: E402
from isaac.vgu_sim.contact_geometry import (  # noqa: E402
    CONTACT_GAP_THRESHOLD_M,
    CONTACT_MODEL_ID,
    compute_contact_frame,
    scene_static_boxes,
    unmodelled_obstacle_ids,
)

# One second of consecutive in-threshold rows (10 at 10 Hz) separates a
# robot held against something from one brushing past it.
SUSTAINED_CONTACT_MIN_SEC = 1.0
# Pairs within this gap keep their exact value in the per-row sidecar.
NEAR_CUTOFF_M = 0.02
_GT_CANDIDATES = ("gt/ground_truth.jsonl", "ground_truth/ground_truth.jsonl", "ground_truth.jsonl")


class BundleError(ValueError):
    """A bundle lacks what the recompute needs."""


@dataclass
class _Event:
    start_t: float
    end_t: float
    n_rows: int = 0
    min_gap: float = float("inf")
    min_gap_t: float = 0.0
    gaps: list[float] = field(default_factory=list)
    max_speed: float = 0.0
    speed_at_min: float = 0.0


def find_ground_truth(bundle: Path) -> Path:
    """Locate a bundle's ground-truth JSONL.

    Args:
        bundle: Bundle directory.

    Returns:
        Path of the JSONL.

    Raises:
        BundleError: If none of the known locations exists.
    """
    for rel in _GT_CANDIDATES:
        path = bundle / rel
        if path.is_file():
            return path
    raise BundleError(f"no ground truth under {bundle} (tried {', '.join(_GT_CANDIDATES)})")


def load_scenario(path: Path) -> ScenarioConfig:
    """Parse a bundle's scenario YAML.

    Args:
        path: The `scenario.yaml`.

    Returns:
        The validated scenario.

    Raises:
        BundleError: If the file is missing.
    """
    if not path.is_file():
        raise BundleError(f"scenario yaml missing: {path}")
    return ScenarioConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _ensure_outside(out_dir: Path, bundles: list[Path]) -> None:
    out = out_dir.resolve()
    for bundle in bundles:
        root = bundle.resolve()
        if out == root or root in out.parents:
            raise BundleError(f"--out-dir {out_dir} lies inside bundle {bundle}; refusing to write")


def _close(
    event_map: dict[Any, _Event], open_keys: set[Any], seen: set[Any], done: dict[Any, list]
) -> None:
    for key in list(open_keys - seen):
        done.setdefault(key, []).append(event_map.pop(key))
        open_keys.discard(key)


def _event_json(ev: _Event, dt: float) -> dict[str, Any]:
    span = ev.end_t - ev.start_t + dt
    return {
        "start_sim_s": ev.start_t,
        "end_sim_s": ev.end_t,
        "n_rows": ev.n_rows,
        "span_s": round(span, 3),
        "min_gap_m": round(ev.min_gap, 5),
        "min_gap_sim_s": ev.min_gap_t,
        "median_gap_m": round(statistics.median(ev.gaps), 5),
        "max_gap_m": round(max(ev.gaps), 5),
        "speed_at_min_mps": round(ev.speed_at_min, 4),
        "max_speed_mps": round(ev.max_speed, 4),
        "row_resolution_m": round(ev.max_speed * dt, 4),
        "class": "sustained_contact" if span >= SUSTAINED_CONTACT_MIN_SEC else "brief_graze",
    }


def _pair_summary(events: list[_Event], dt: float) -> dict[str, Any]:
    items = [_event_json(ev, dt) for ev in events]
    classes = {item["class"] for item in items}
    verdict = "sustained_contact" if "sustained_contact" in classes else "brief_graze"
    all_gaps = [g for ev in events for g in ev.gaps]
    return {
        "verdict": verdict,
        "first_sim_s": items[0]["start_sim_s"],
        "last_sim_s": items[-1]["end_sim_s"],
        "rows_in_contact": sum(i["n_rows"] for i in items),
        "n_events": len(items),
        "longest_span_s": max(i["span_s"] for i in items),
        "min_gap_m": min(i["min_gap_m"] for i in items),
        "gap_p50_m": round(statistics.median(all_gaps), 5),
        "gap_p95_m": round(sorted(all_gaps)[int(0.95 * (len(all_gaps) - 1))], 5),
        "events": items,
    }


def recompute_bundle(
    bundle: Path,
    scenario_path: Path | None = None,
    rows_out: Path | None = None,
) -> dict[str, Any]:
    """Recompute contacts for one bundle.

    Args:
        bundle: Bundle directory.
        scenario_path: Scenario YAML; defaults to `<bundle>/scenario.yaml`.
        rows_out: When given, the per-row sidecar JSONL to write.

    Returns:
        The bundle summary (JSON-ready).

    Raises:
        BundleError: If ground truth or scenario is missing, or rows lack poses.
    """
    gt_path = find_ground_truth(bundle)
    scenario = load_scenario(scenario_path or bundle / "scenario.yaml")
    boxes = scene_static_boxes(scenario)
    category = {b.obstacle_id: b.category for b in boxes}

    static_open: dict[tuple[str, str], _Event] = {}
    robot_open: dict[tuple[str, str], _Event] = {}
    static_done: dict[tuple[str, str], list[_Event]] = {}
    robot_done: dict[tuple[str, str], list[_Event]] = {}
    robot_min: dict[str, dict[str, Any]] = {}
    category_min: dict[str, dict[str, Any]] = {}
    pair_min: dict[str, Any] | None = None
    times: list[float] = []
    logged_nonempty = {"robot_static_contacts": 0, "robot_robot_contacts": 0}
    rows_with_model = 0
    n_rows = 0

    sidecar = rows_out.open("w", encoding="utf-8") if rows_out is not None else None
    try:
        with gt_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                n_rows += 1
                t = float(row["sim_time_sec"])
                times.append(t)
                for key in logged_nonempty:
                    if row.get(key):
                        logged_nonempty[key] += 1
                if "contact_model" in row:
                    rows_with_model += 1
                robots = row.get("robots") or {}
                try:
                    poses = {rid: (r["x"], r["y"], r["theta"]) for rid, r in robots.items()}
                except KeyError as exc:
                    raise BundleError(f"{gt_path}: row at {t} lacks pose key {exc}") from exc
                speeds = {rid: float(r.get("speed_mps") or 0.0) for rid, r in robots.items()}
                frame = compute_contact_frame(poses, boxes, t, near_cutoff_m=NEAR_CUTOFF_M)

                for rid, (gap, oid) in frame.robot_min_static.items():
                    cur = robot_min.get(rid)
                    if cur is None or gap < cur["min_gap_m"]:
                        robot_min[rid] = {"min_gap_m": gap, "obstacle_id": oid,
                                          "category": category[oid], "sim_s": t}
                for (rid, oid), gap in frame.static_gaps_near.items():
                    cat = category[oid]
                    cur = category_min.get(cat)
                    if cur is None or gap < cur["min_gap_m"]:
                        category_min[cat] = {"min_gap_m": gap, "robot_id": rid,
                                             "obstacle_id": oid, "sim_s": t}
                if frame.robot_pair_min is not None:
                    gap, ids = frame.robot_pair_min
                    if pair_min is None or gap < pair_min["min_gap_m"]:
                        pair_min = {"min_gap_m": gap, "robot_ids": list(ids), "sim_s": t}

                seen_static: set[tuple[str, str]] = set()
                for (rid, oid), gap in frame.static_gaps_near.items():
                    if gap > CONTACT_GAP_THRESHOLD_M:
                        continue
                    key = (rid, oid)
                    seen_static.add(key)
                    ev = static_open.setdefault(key, _Event(t, t))
                    _extend(ev, t, gap, speeds.get(rid, 0.0))
                _close(static_open, set(static_open), seen_static, static_done)

                seen_robot: set[tuple[str, str]] = set()
                for key, gap in frame.robot_gaps_near.items():
                    if gap > CONTACT_GAP_THRESHOLD_M:
                        continue
                    seen_robot.add(key)
                    ev = robot_open.setdefault(key, _Event(t, t))
                    _extend(ev, t, gap, max(speeds.get(key[0], 0.0), speeds.get(key[1], 0.0)))
                _close(robot_open, set(robot_open), seen_robot, robot_done)

                if sidecar is not None:
                    sidecar.write(json.dumps({
                        "sim_time_sec": t,
                        "robot_static_contacts": frame.static_contacts,
                        "robot_robot_contacts": frame.robot_contacts,
                        "min_static_gap_m": frame.min_static_gap_m,
                        "min_robot_robot_gap_m": frame.min_robot_robot_gap_m,
                        "contact_model": CONTACT_MODEL_ID,
                    }, sort_keys=True) + "\n")
    finally:
        if sidecar is not None:
            sidecar.close()
    _close(static_open, set(static_open), set(), static_done)
    _close(robot_open, set(robot_open), set(), robot_done)

    if n_rows == 0:
        raise BundleError(f"{gt_path} has no rows")
    steps = [b - a for a, b in zip(times, times[1:], strict=False)]
    dt = statistics.median(steps) if steps else 0.1
    static_pairs = {
        f"{rid}|{oid}": {"robot_id": rid, "obstacle_id": oid, "category": category[oid],
                         **_pair_summary(evs, dt)}
        for (rid, oid), evs in sorted(static_done.items())
    }
    robot_pairs = {
        f"{a}|{b}": {"robot_ids": [a, b], **_pair_summary(evs, dt)}
        for (a, b), evs in sorted(robot_done.items())
    }

    def _verdict(pairs: dict[str, Any]) -> str:
        verdicts = {p["verdict"] for p in pairs.values()}
        for v in ("sustained_contact", "brief_graze"):
            if v in verdicts:
                return v
        return "clear"

    def _rounded(entry: dict[str, Any] | None) -> dict[str, Any] | None:
        if entry is None:
            return None
        return {**entry, "min_gap_m": round(entry["min_gap_m"], 5)}

    return {
        "bundle": str(bundle),
        "ground_truth": str(gt_path),
        "scenario": scenario.name,
        "family": scenario.family,
        "contact_model": CONTACT_MODEL_ID,
        "threshold_m": CONTACT_GAP_THRESHOLD_M,
        "sustained_min_sec": SUSTAINED_CONTACT_MIN_SEC,
        "n_rows": n_rows,
        "sim_span_s": [times[0], times[-1]],
        "row_dt_s": round(dt, 4),
        "declared_static_obstacles": [o.obstacle_id for o in scenario.static_obstacles],
        "timed_obstacles": [o.obstacle_id for o in scenario.timed_obstacles],
        "unmodelled_obstacles": list(unmodelled_obstacle_ids(scenario)),
        "n_boxes": len(boxes),
        "logged_rows_nonempty": logged_nonempty,
        "logged_rows_with_contact_model": rows_with_model,
        "static_verdict": _verdict(static_pairs),
        "robot_robot_verdict": _verdict(robot_pairs),
        "static_pairs": static_pairs,
        "robot_pairs": robot_pairs,
        "robot_min_static_gap": {rid: _rounded(v) for rid, v in sorted(robot_min.items())},
        "category_min_gap_within_near_cutoff": {
            k: _rounded(v) for k, v in sorted(category_min.items())
        },
        "near_cutoff_m": NEAR_CUTOFF_M,
        "min_robot_robot_gap": _rounded(pair_min),
    }


def _extend(ev: _Event, t: float, gap: float, speed: float) -> None:
    ev.end_t = t
    ev.n_rows += 1
    ev.gaps.append(gap)
    ev.max_speed = max(ev.max_speed, speed)
    if gap < ev.min_gap:
        ev.min_gap, ev.min_gap_t, ev.speed_at_min = gap, t, speed


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments; defaults to `sys.argv[1:]`.

    Returns:
        Process exit code: 0 when every bundle was recomputed, else 1.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bundles", nargs="+", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--rows", action="store_true", help="also write per-row sidecars")
    args = parser.parse_args(argv)

    _ensure_outside(args.out_dir, args.bundles)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.rows:
        (args.out_dir / "rows").mkdir(exist_ok=True)

    index_path = args.out_dir / "index.json"
    index: dict[str, Any] = {}
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    failed = 0
    for bundle in args.bundles:
        label = bundle.name
        try:
            rows_out = args.out_dir / "rows" / f"{label}.contacts.jsonl" if args.rows else None
            summary = recompute_bundle(bundle, rows_out=rows_out)
        except (BundleError, ValueError) as exc:
            failed += 1
            index[label] = {"bundle": str(bundle), "error": str(exc)}
            print(f"{label}: ERROR {exc}", file=sys.stderr)
            continue
        (args.out_dir / f"{label}.summary.json").write_text(
            json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        rmin = summary["min_robot_robot_gap"]
        smin = min(
            summary["robot_min_static_gap"].values(), key=lambda v: v["min_gap_m"], default=None
        )
        index[label] = {
            "bundle": str(bundle),
            "static_verdict": summary["static_verdict"],
            "robot_robot_verdict": summary["robot_robot_verdict"],
            "min_static_gap": smin,
            "min_robot_robot_gap": rmin,
            "static_pairs": {
                k: {kk: v[kk] for kk in ("verdict", "first_sim_s", "last_sim_s", "rows_in_contact",
                                         "longest_span_s", "min_gap_m")}
                for k, v in summary["static_pairs"].items()
            },
            "robot_pairs": {
                k: {kk: v[kk] for kk in ("verdict", "first_sim_s", "last_sim_s", "rows_in_contact",
                                         "longest_span_s", "min_gap_m")}
                for k, v in summary["robot_pairs"].items()
            },
        }
        static_txt = (
            f"min {smin['min_gap_m'] * 1000:.1f} mm {smin['obstacle_id']}" if smin else "no boxes"
        )
        robot_txt = f"min {rmin['min_gap_m'] * 1000:.1f} mm" if rmin else "one robot"
        print(
            f"{label}: static={summary['static_verdict']} ({static_txt}) "
            f"robot={summary['robot_robot_verdict']} ({robot_txt})"
        )
    index_path.write_text(json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
