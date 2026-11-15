"""Load a run bundle and resolve its wall-clock to sim-time mapping.

The demo renderer only replays a bundle's own files; this module reads them
once and works out where each wall-stamped log line falls on the sim clock
(see `timemap` for the clock model and `build_time_map` for the anchors).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.demo_panel import logparse as lp
from scripts.demo_panel.models import TimeMapInfo
from scripts.demo_panel.timemap import Anchor, SceneClock, WallSimMap, estimate_offset

UNCERTAIN_SIM_SEC = 0.5
# Isaac's ground_truth.jsonl sim_time_sec runs 0.300 s behind ROS header stamps
# (docs/reports/2026-10-05-costmap-source-probe.md Rev 2; the same constant as
# scripts/gt_offset_audit.py GT_CLOCK_OFFSET_SEC). The panel clock is the ROS
# sim clock, so GT time = panel sim time - GT_CLOCK_OFFSET_SEC.
GT_CLOCK_OFFSET_SEC = 0.300


@dataclass
class Bundle:
    """Raw contents of one run bundle, loaded once."""

    root: Path
    condition: dict[str, str]
    condition_line: str
    m5: list[str]
    m4: list[str]
    cost: list[str]
    decisions: dict[str, tuple[str, dict[str, Any]]]
    scene_rows: list[tuple[int, dict[str, Any]]]
    manifest: dict[str, Any]
    m5_ros: list[tuple[int, lp.RosLine]] = field(default_factory=list)
    m4_ros: list[tuple[int, lp.RosLine]] = field(default_factory=list)
    scene_log: str = ""

    @property
    def name(self) -> str:
        """Bundle directory name."""
        return self.root.name


def find_scene_log(root: Path, m5_lines: list[str]) -> str:
    """Pick the bundle's M5 scene log file name.

    Rule, first match wins: `m5_scene.jsonl`; else `scene_<session_id>.jsonl`
    where `session_id` is the first `session_id=` value in `m5.log` (older
    bundles copied M5's `data/logs/m5_scene/<session>.jsonl` under that name);
    else the only `scene_*.jsonl` file.

    Args:
        root: Bundle directory.
        m5_lines: Raw `m5.log` lines.

    Returns:
        File name relative to `root`, or "" when the bundle has no scene log.

    Raises:
        ValueError: Several `scene_*.jsonl` files and none matches the session.
    """
    if (root / "m5_scene.jsonl").is_file():
        return "m5_scene.jsonl"
    cands = sorted(p.name for p in root.glob("scene_*.jsonl") if p.is_file())
    if not cands:
        return ""
    session = next(
        (m.group(1) for m in (re.search(r"session_id=([0-9a-fA-F]+)", ln) for ln in m5_lines) if m),
        None,
    )
    if session is not None and f"scene_{session}.jsonl" in cands:
        return f"scene_{session}.jsonl"
    if len(cands) == 1:
        return cands[0]
    raise ValueError(
        f"{root}: ambiguous scene log: {cands} and none is scene_<session_id>.jsonl "
        f"(session_id={session})"
    )


def load_bundle(root: Path) -> Bundle:
    """Load the files the panel reads from a bundle directory.

    Args:
        root: Bundle directory (e.g. `.../runs/ib10S_e03_armA_a1`).

    Returns:
        The loaded bundle; missing optional files load as empty.

    Raises:
        FileNotFoundError: `m5.log` or `gt/ground_truth.jsonl` is missing.
    """
    for required in ("m5.log", "gt/ground_truth.jsonl"):
        if not (root / required).is_file():
            raise FileNotFoundError(f"{root}: missing {required}")

    def lines(name: str) -> list[str]:
        p = root / name
        return lp.read_raw_lines(p) if p.is_file() else []

    cond_lines = lines("CONDITION.txt")
    decisions: dict[str, tuple[str, dict[str, Any]]] = {}
    ddir = root / "decisions"
    if ddir.is_dir():
        for p in sorted(ddir.glob("*.json")):
            decisions[p.stem] = (f"decisions/{p.name}", json.loads(p.read_text()))
    m5_lines = lines("m5.log")
    scene_log = find_scene_log(root, m5_lines)
    scene_rows = []
    for i, raw in enumerate(lines(scene_log) if scene_log else [], start=1):
        if raw.strip():
            scene_rows.append((i, json.loads(raw)))
    manifest_p = root / "gt" / "run_manifest.json"
    manifest = json.loads(manifest_p.read_text()) if manifest_p.is_file() else {}
    b = Bundle(
        root=root,
        condition=lp.parse_condition(cond_lines[0]) if cond_lines else {},
        condition_line=cond_lines[0] if cond_lines else "",
        m5=m5_lines,
        m4=lines("m4.log"),
        cost=lines("cost.log"),
        decisions=decisions,
        scene_rows=scene_rows,
        manifest=manifest,
        scene_log=scene_log,
    )
    b.m5_ros = lp.iter_ros_lines(b.m5)
    b.m4_ros = lp.iter_ros_lines(b.m4)
    return b


def collect_anchors(b: Bundle) -> list[Anchor]:
    """Collect `(wall, sim)` anchors from the bundle.

    Two kinds: M4/M5 lines that print their own `sim_t=` (same line carries the
    wall stamp), and each `starting analysis request=<id>` line paired with its
    decision artifact's `scene.stamp` (the snapshot analysed in that callback).

    Args:
        b: Loaded bundle.

    Returns:
        Anchors in file order.
    """
    out: list[Anchor] = []
    for fname, rows in (("m4.log", b.m4_ros), ("m5.log", b.m5_ros)):
        for ln, r in rows:
            s = lp.parse_sim_t(r.msg)
            if s is not None:
                out.append(Anchor(r.wall, s, f"{fname}:{ln}"))
    for ln, r in b.m5_ros:
        st = lp.parse_starting_analysis(r.msg)
        if st is None:
            continue
        dec = b.decisions.get(str(st["request"]))
        if dec is None:
            continue
        stamp = (dec[1].get("scene") or {}).get("stamp")
        if isinstance(stamp, (int, float)):
            out.append(Anchor(r.wall, float(stamp), f"m5.log:{ln}+{dec[0]}#scene.stamp"))
    return out


def scene_clock(b: Bundle) -> SceneClock | None:
    """Build the scene clock from the scene log (`find_scene_log`), or None if < 2 rows."""
    if len(b.scene_rows) < 2:
        return None
    return SceneClock(
        [float(r["t"]) for _, r in b.scene_rows],
        [float(r["scene"]["stamp"]) for _, r in b.scene_rows],
    )


def load_gt(b: Bundle) -> list[dict[str, Any]]:
    """Load ground-truth rows (sorted by sim time)."""
    rows = [json.loads(x) for x in lp.read_raw_lines(b.root / "gt" / "ground_truth.jsonl") if x]
    return sorted(rows, key=lambda r: r["sim_time_sec"])


def first_safety_stop(b: Bundle) -> tuple[int, float] | None:
    """Return `(line, wall)` of the first `safety stop` line in `m4.log`."""
    for ln, r in b.m4_ros:
        if lp.parse_safety_stop(r.msg):
            return ln, r.wall
    return None


def min_distance_threshold(b: Bundle) -> float | None:
    """Return the safety monitor's `min_distance_m` from its startup line."""
    for _, r in b.m4_ros:
        params = lp.parse_safety_start(r.msg)
        if params and "min_distance_m" in params:
            return float(params["min_distance_m"])
    return None


def fallback_anchor(b: Bundle, gt: list[dict[str, Any]]) -> Anchor | None:
    """Derive one coarse anchor when the bundle has no `sim_t`/decision anchors.

    Pairs the first `safety stop` wall stamp with the first GT row whose
    `min_pairwise_distance_m` falls below the safety monitor's
    `min_distance_m`. The monitor acts on M1 poses, not GT, so this anchor
    carries M1's pose bias and latency; its error is calibrated by
    `fallback_anchor_error` on a bundle that has real anchors.

    Args:
        b: Loaded bundle.
        gt: Ground-truth rows.

    Returns:
        The anchor, or None when either side is missing.
    """
    stop = first_safety_stop(b)
    thr = min_distance_threshold(b)
    if stop is None or thr is None:
        return None
    for row in gt:
        d = row.get("min_pairwise_distance_m")
        if isinstance(d, (int, float)) and d < thr:
            return Anchor(
                stop[1], float(row["sim_time_sec"]) + GT_CLOCK_OFFSET_SEC, f"m4.log:{stop[0]}+gt"
            )
    return None


def fallback_anchor_error(b: Bundle) -> float | None:
    """Sim-second error of `fallback_anchor` on a bundle with real anchors.

    Args:
        b: Bundle that has `sim_t` or decision anchors.

    Returns:
        `fallback mapped sim - true-map sim` at the first safety stop, or None.
    """
    clock = scene_clock(b)
    anchors = collect_anchors(b)
    if clock is None or not anchors:
        return None
    est = estimate_offset(anchors, clock)
    fb = fallback_anchor(b, load_gt(b))
    if est is None or fb is None:
        return None
    true_sim = WallSimMap(clock, est[0]).wall_to_sim(fb.wall)
    return None if true_sim is None else fb.sim - true_sim


@dataclass(frozen=True)
class TimeContext:
    """Resolved time mapping for one bundle."""

    wmap: WallSimMap | None
    info: TimeMapInfo


def build_time_map(
    b: Bundle, gt: list[dict[str, Any]], fallback_error: float | None = None
) -> TimeContext:
    """Resolve the wall-to-sim map and measure its error.

    Args:
        b: Loaded bundle.
        gt: Ground-truth rows (for the fallback anchor).
        fallback_error: Calibrated error of the fallback rule (sim-s), shown
            when the fallback is used.

    Returns:
        The mapping and its description.
    """
    clock = scene_clock(b)
    if clock is None:
        return TimeContext(
            None,
            TimeMapInfo(
                method="none (no scene log: m5_scene.jsonl or scene_*.jsonl)",
                offset_wall_minus_monotonic=None,
                anchor_count=0,
                anchor_spread_wall_sec=None,
                max_abs_error_sim_sec=None,
                uncertain=True,
                note="log events cannot be placed on the sim clock",
            ),
        )
    anchors = collect_anchors(b)
    est = estimate_offset(anchors, clock)
    if est is not None:
        wmap = WallSimMap(clock, est[0])
        res = wmap.residuals(anchors)
        max_err = max(abs(r) for _, r in res) if res else None
        n_sim_t = sum(1 for a in anchors if "+" not in a.source)
        checks = [
            f"{len(res)} anchors ({n_sim_t} log lines with sim_t=, "
            f"{len(res) - n_sim_t} analysis lines vs decision scene.stamp); "
            f"max |mapped - logged| = {max_err:.2f} sim-s"
        ]
        uncertain = max_err is None or max_err > UNCERTAIN_SIM_SEC
        return TimeContext(
            wmap,
            TimeMapInfo(
                method=(
                    f"wall -> {b.scene_log} monotonic (median offset over anchors) -> sim stamp"
                ),
                offset_wall_minus_monotonic=est[0],
                anchor_count=len(res),
                anchor_spread_wall_sec=est[1],
                max_abs_error_sim_sec=max_err,
                error_checks=tuple(checks),
                uncertain=uncertain,
                note=(
                    f"log-to-sim alignment within {max_err:.2f} sim-s at {len(res)} anchors"
                    if not uncertain
                    else f"log-to-sim alignment uncertain: up to {max_err:.2f} sim-s at anchors"
                ),
            ),
        )
    fb = fallback_anchor(b, gt)
    if fb is not None:
        mono = clock.monotonic_at_sim(fb.sim)
        if mono is not None:
            wmap = WallSimMap(clock, fb.wall - mono)
            err = f"{abs(fallback_error):.1f}" if fallback_error is not None else "unknown"
            return TimeContext(
                wmap,
                TimeMapInfo(
                    method=(
                        "fallback: first m4 safety stop <-> first GT row with min pairwise "
                        f"distance < min_distance_m, then {b.scene_log} clock"
                    ),
                    offset_wall_minus_monotonic=fb.wall - mono,
                    anchor_count=1,
                    anchor_spread_wall_sec=None,
                    max_abs_error_sim_sec=abs(fallback_error)
                    if fallback_error is not None
                    else None,
                    error_checks=(
                        f"fallback rule error calibrated on another bundle: {err} sim-s",
                    ),
                    uncertain=True,
                    note=(
                        f"alignment UNCERTAIN: no sim-stamped log line in this bundle; "
                        f"coarse anchor (rule off by {err} sim-s where checkable)"
                    ),
                ),
            )
    return TimeContext(
        None,
        TimeMapInfo(
            method="none (no anchor)",
            offset_wall_minus_monotonic=None,
            anchor_count=0,
            anchor_spread_wall_sec=None,
            max_abs_error_sim_sec=None,
            uncertain=True,
            note="log events cannot be placed on the sim clock",
        ),
    )
