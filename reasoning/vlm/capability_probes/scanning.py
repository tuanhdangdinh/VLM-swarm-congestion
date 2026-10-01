"""Shared GT-matching, legibility, and dedup-key logic for the probe battery.

Used by both `scripts/build_capability_probe_manifest.py` (selecting the
frozen item set) and `scripts/audit_capability_probe_manifest.py`
(independently re-verifying it from the same source logs): the two tools
must agree on what "a legible scene" or "a duplicate configuration" means, so
this is one definition, not two that could drift apart.
"""
from __future__ import annotations

import json
from pathlib import Path

from reasoning.vlm.capability_probes import ground_truth as gtlib

# How many GT-matched robots a frame's `scene.stamp` must land within, to be
# used at all. Episodes in this battery log GT at a fixed physics tick
# (<=1/60 s); a looser bound tolerates the coarser cadence of older runs.
GT_MATCH_TOLERANCE_SEC = 0.5


def load_gt_rows(gt_path: Path) -> list[dict]:
    """Load every row of a `ground_truth.jsonl` file."""
    rows = []
    with gt_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def nearest_gt_row(rows: list[dict], stamp: float) -> dict | None:
    """Return the GT row closest to `stamp`, or None if none is within tolerance.

    Args:
        rows: GT rows (`load_gt_rows`).
        stamp: A decision's `scene.stamp`.

    Returns:
        The closest row by `sim_time_sec`, or None when `rows` is empty or
        the closest row is more than `GT_MATCH_TOLERANCE_SEC` away.
    """
    if not rows:
        return None
    best = min(rows, key=lambda r: abs(r["sim_time_sec"] - stamp))
    if abs(best["sim_time_sec"] - stamp) > GT_MATCH_TOLERANCE_SEC:
        return None
    return best


def dedup_key(reference_robot_id: str | None, gt_robots: dict[str, dict]) -> str:
    """Return a scene-configuration fingerprint for duplicate detection.

    The reference robot plus every robot's GT position, rounded to 5 cm, so
    two frames of a stalled episode -- same robots, same positions, a few
    seconds apart -- fingerprint identically and cannot both enter the
    candidate pool as if they were independent evidence.

    Args:
        reference_robot_id: The item's named robot, or None (`robot_count`).
        gt_robots: GT robot_id -> `{"x", "y"}` for every tracked robot.

    Returns:
        A string key, equal for two calls with the same reference robot and
        the same (rounded) robot positions.
    """
    positions = ",".join(
        f"{rid}:{round(pos['x'] / 0.05)}:{round(pos['y'] / 0.05)}"
        for rid, pos in sorted(gt_robots.items())
    )
    return f"{reference_robot_id}|{positions}"


def scene_is_legible(
    m1_robots: dict[str, dict],
    m1_pixels: dict[str, tuple[int, int]],
    width: int,
    height: int,
) -> bool:
    """Return whether a frame's robots are all distinctly, fully, reliably drawn.

    Gates every probe type from a frame, not only `robot_count`: `nearest_first`'s
    other-robot options and `locate_robot`/`left_right`'s single named robot
    all need the same guarantee. Checked against M1's own drawn pixel
    positions, not GT: M1 is what the image actually shows, and GT can differ
    from it by up to `ground_truth.M1_GT_MAX_DISAGREEMENT_M`. Three
    conditions: every robot clear of the frame edge (full label visible),
    every pair of robots far enough apart that their boxes/labels cannot
    visually merge, and no robot M1 itself marked STALE (unreliable
    positioning, by the project's own notes).

    Args:
        m1_robots: M1 robot_id -> `{"x", "y", "status"}` (status optional).
        m1_pixels: M1 robot_id -> pixel `(u, v)`, matching `m1_robots`.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        True when the frame is legible under all three conditions.
    """
    pixels = list(m1_pixels.values())
    if any(not gtlib.is_away_from_frame_edge(u, v, width, height) for u, v in pixels):
        return False
    if any(robot.get("status") == "STALE" for robot in m1_robots.values()):
        return False
    for i in range(len(pixels)):
        for j in range(i + 1, len(pixels)):
            du = pixels[i][0] - pixels[j][0]
            dv = pixels[i][1] - pixels[j][1]
            if (du * du + dv * dv) ** 0.5 < gtlib.MIN_ROBOT_SEPARATION_PX:
                return False
    return True
