"""Tables of the M4 stall-abort report from the packed replay episodes.

Report: docs/reports/2026-11-15-m4-stall-abort.md, sections 2.4, 4 and 6.
Read-only on the bundles; no VM, no API call.

Subcommands:

- `tables EPISODES.jsonl.gz --contact-root DIR --bundle-root DIR [...]
  [--write-expected FILE]`: replays every episode with the default config
  (`scripts/stall_abort_replay.py`), then prints:
  - completed primitives per group and primitive, judged counts, lowest
    travel and turn ratios (section 6.3);
  - every abort with its footprint contact at the abort, contact onset
    (first GT row with a footprint gap <= 5 mm), lag, the pinned plateau
    ratio (replay with `min_progress_ratio` 0.01) and the live end (6.2);
  - every live failure that did not fire, with its hold intervals, last
    motion and nearest contact (6.4);
  - the ramp of exact-start completed backups (2.4).
  `--contact-root` is a checkout carrying `isaac/vgu_sim/contact_geometry.py`
  (v7m, b5eaee5); `--bundle-root` directories are searched for the bundles.
  `--write-expected` writes the replay test's `expected.json`.
- `pin-fixture OUT.json BAG:ROBOT [...]`: writes the commanded `/cmd_vel`
  (non-zero samples, sim time from `/clock`) and `/odom` around them for each
  `bag.mcap:robot_N` (the test fixture `pinned_bag_samples.json`).

Usage (repo root):
    PYTHONPATH=.:ros2_ws/src/swarm_execution python scripts/stall_abort_analysis.py tables ...
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import importlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml
from swarm_execution.stall_abort import STALL_ABORT_DETAIL_PREFIX, StallAbortConfig

from scripts.stall_abort_replay import gt_motion, replay_episode

_CONTACT_M = 0.005


def _key(e: dict[str, Any]) -> str:
    return "|".join([e["bundle"], e["command_id"], e["robot_id"], e["primitive"]])


def _group(bundle: str) -> str:
    if bundle.startswith("ib10"):
        return "IB10 bags (Oct)"
    if bundle.startswith("s1b_"):
        return "S1b (Oct)"
    return "campaign (Nov)"


def _fired(result: dict[str, Any]) -> bool:
    return result["outcome"] == "FAILED" and result["detail"].startswith(STALL_ABORT_DETAIL_PREFIX)


class _Scene:
    """GT rows and authored boxes of one bundle, with footprint gaps."""

    def __init__(self, bundle: Path, contact: Any, config_module: Any) -> None:
        scenario = config_module.ScenarioConfig.model_validate(
            yaml.safe_load((bundle / "scenario.yaml").read_text(encoding="utf-8"))
        )
        self.boxes = contact.scene_static_boxes(scenario)
        self.contact = contact
        with (bundle / "gt" / "ground_truth.jsonl").open(encoding="utf-8") as handle:
            self.rows = [json.loads(line) for line in handle]

    def gaps(self, row: dict[str, Any], robot: str) -> tuple[tuple[float, str], tuple[float, str]]:
        me = row["robots"][robot]
        pose = (me["x"], me["y"], me["theta"])
        box = min(
            (
                (gap, b.obstacle_id)
                for b in self.boxes
                if (gap := self.contact.robot_box_gap(pose, b)) is not None
            ),
            default=(math.inf, "-"),
        )
        other = min(
            (
                (self.contact.robot_robot_gap(pose, (v["x"], v["y"], v["theta"])), k)
                for k, v in row["robots"].items()
                if k != robot
            ),
            default=(math.inf, "-"),
        )
        return box, other

    def row_at(self, t_ros: float, offset: float) -> dict[str, Any]:
        return min(self.rows, key=lambda r: abs(r["sim_time_sec"] + offset - t_ros))


def _tables(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(args.contact_root.resolve()))
    contact = importlib.import_module("isaac.vgu_sim.contact_geometry")
    config_module = importlib.import_module("isaac.vgu_sim.config")
    dirs: dict[str, Path] = {}
    for root in args.bundle_root:
        for m4 in sorted(root.glob("**/m4.log")):
            if "_backup_" not in str(m4) and "VOID" not in str(m4):
                dirs.setdefault(m4.parent.name, m4.parent)
    with gzip.open(args.episodes, "rt", encoding="utf-8") as handle:
        episodes = [json.loads(line) for line in handle]
    cfg = StallAbortConfig(enabled=True)
    low = StallAbortConfig(enabled=True, min_progress_ratio=0.01)
    results = [(e, replay_episode(e, cfg)) for e in episodes]
    contact_fired = {_key(e) for e, r in results if _fired(r)}

    print("== completed primitives (6.3)")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for e, r in results:
        if e["live_outcome"] == "COMPLETED":
            groups.setdefault((_group(e["bundle"]), e["primitive"]), []).append(
                {
                    "fired": _key(e) in contact_fired,
                    "ratios": r["min_ratio"],
                    "bag": e["odom_source"] == "bag",
                }
            )
    for (group, primitive), items in sorted(groups.items()):
        quiet = [i for i in items if not i["fired"]]
        lin = [i["ratios"]["linear"] for i in quiet if "linear" in i["ratios"]]
        ang = [i["ratios"]["angular"] for i in quiet if "angular" in i["ratios"]]
        print(
            f"{group}\t{primitive}\tn={len(items)}\tfired={len(items) - len(quiet)}\t"
            f"never_judged={sum(1 for i in quiet if not i['ratios'])}\t"
            f"bag={sum(i['bag'] for i in items)}\t"
            f"travel_judged={len(lin)} min={min(lin, default=math.nan):.3f} "
            f"median={statistics.median(lin) if lin else math.nan:.3f}\t"
            f"turn_judged={len(ang)} min={min(ang, default=math.nan):.3f}"
        )

    print("== aborts (6.2)")
    expected: dict[str, Any] = {}
    scene_cache: dict[str, _Scene] = {}

    def scene(bundle: str) -> _Scene:
        if bundle not in scene_cache:
            scene_cache.clear()
            scene_cache[bundle] = _Scene(dirs[bundle], contact, config_module)
        return scene_cache[bundle]

    for e, r in results:
        if not _fired(r):
            continue
        sc = scene(e["bundle"])
        box, other = sc.gaps(sc.row_at(r["t"], e["clock_offset_s"]), e["robot_id"])
        onset = None
        for row in sc.rows:
            t = row["sim_time_sec"] + e["clock_offset_s"]
            if e["start_sim"] <= t <= r["t"] + 0.01 and min(
                g[0] for g in sc.gaps(row, e["robot_id"])
            ) <= _CONTACT_M:
                onset = t
                break
        plateau = replay_episode(e, low)["min_ratio"].get(r["verdict"]["mode"])
        where = box if box[0] <= other[0] else other
        print(
            f"{_key(e)}\tlive={e['live_outcome']}\tabort={r['t']:.1f}\t"
            f"contact={where[1]}@{where[0] * 1000:.1f}mm\tonset={onset}\t"
            f"lag={(r['t'] - onset) if onset is not None else math.nan:.1f}\t"
            f"ratio={r['verdict']['measured'] / r['verdict']['commanded']:.3f}\t"
            f"plateau={plateau:.3f}\tlive_end={e['end_sim']:.1f}"
        )
        expected[_key(e)] = {
            "contact_onset_sim": None if onset is None else round(onset, 1),
            "contact": f"{where[1]} {where[0] * 1000:.1f} mm",
            "live_outcome": e["live_outcome"],
        }

    print("== live failures that did not fire (6.4)")
    for e, r in results:
        if e["live_outcome"] == "COMPLETED" or _fired(r):
            continue
        motion = gt_motion(e)
        sc = scene(e["bundle"])
        t = motion["stop_t"] if motion["stop_t"] is not None else e["end_sim"] - 1.0
        box, other = sc.gaps(sc.row_at(t, e["clock_offset_s"]), e["robot_id"])
        print(
            f"{_key(e)}\tlive={e['live_outcome']}\tmoved={motion['moved_m']:.3f}\t"
            f"last_motion={motion['stop_t']}\tholds={e['held']}\t"
            f"box={box[1]}@{box[0]:.4f}\trobot={other[1]}@{other[0]:.4f}"
        )

    print("== ramp of exact-start completed backups (2.4)")
    ramps = []
    for e, _r in results:
        if e["live_outcome"] != "COMPLETED" or e["primitive"] != "backup":
            continue
        if e["start_source"] != "handover_sim_t":
            continue
        rows = [q for q in e["odom"] if q[0] >= e["start_sim"] - 0.01]
        for a, b in zip(rows, rows[1:], strict=False):
            if b[0] > a[0] and math.hypot(b[1] - a[1], b[2] - a[2]) / (b[0] - a[0]) >= 0.08:
                ramps.append(b[0] - e["start_sim"])
                break
    ramps.sort()
    print(
        f"n={len(ramps)} reach_0.08mps median={statistics.median(ramps):.2f} "
        f"p95={ramps[int(0.95 * len(ramps))]:.2f} max={ramps[-1]:.2f}"
    )
    if args.write_expected is not None:
        note = (
            "Every other episode in replay_episodes.jsonl.gz must not fire. "
            "contact_onset_sim: first GT row (ROS sim time) with footprint gap <= 5 mm, "
            "v7m contact_geometry; written by scripts/stall_abort_analysis.py."
        )
        args.write_expected.write_text(
            json.dumps({"expected_fires": expected, "note": note}, indent=1)
        )


def _pin_fixture(args: argparse.Namespace) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mcap_lite

    out = []
    for spec in args.bags:
        bag, robot = spec.rsplit(":", 1)
        clock, odom, cmd = [], [], []
        topics = {"/clock", f"/{robot}/odom", f"/{robot}/cmd_vel"}
        for topic, log_time, payload in mcap_lite.iter_messages(Path(bag), topics):
            if topic == "/clock":
                clock.append((log_time, mcap_lite.decode_clock(payload)))
            elif topic.endswith("odom"):
                d = mcap_lite.decode_odometry(payload)
                yaw = 2 * math.atan2(d["qz"], d["qw"])
                odom.append([round(d["stamp"], 4), d["x"], d["y"], yaw])
            else:
                d = mcap_lite.decode_twist(payload)
                cmd.append((log_time, d["linear_x"], d["angular_z"]))
        clock.sort()
        logs = [c[0] for c in clock]

        def sim(log_time: int, _clock=clock, _logs=logs) -> float:
            return _clock[max(bisect.bisect_right(_logs, log_time) - 1, 0)][1]

        cmds = [[round(sim(t), 4), v, w] for t, v, w in cmd if abs(v) > 1e-3 or abs(w) > 1e-3]
        t0, t1 = cmds[0][0], cmds[-1][0]
        rows = sorted(o for o in odom if t0 - 0.5 <= o[0] <= t1 + 0.1)
        out.append({"source": bag, "robot_id": robot, "cmd_vel": cmds, "odom": rows})
    args.out.write_text(json.dumps(out, separators=(",", ":")))


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    tables = sub.add_parser("tables")
    tables.add_argument("episodes", type=Path)
    tables.add_argument("--contact-root", type=Path, required=True)
    tables.add_argument("--bundle-root", type=Path, action="append", required=True)
    tables.add_argument("--write-expected", type=Path, default=None)
    pin = sub.add_parser("pin-fixture")
    pin.add_argument("out", type=Path)
    pin.add_argument("bags", nargs="+")
    args = parser.parse_args()
    if args.command == "tables":
        _tables(args)
    else:
        _pin_fixture(args)


if __name__ == "__main__":
    main()
