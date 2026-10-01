"""Shared GT-matching, legibility, and duplicate-scene logic for the probe battery.

Used by both `scripts/build_capability_probe_manifest.py` (selecting the
frozen item set) and `scripts/audit_capability_probe_manifest.py`
(independently re-verifying it from the same source logs): the two tools
must agree on what "a legible scene" or "a duplicate configuration" means, so
this is one definition, not two that could drift apart. This matters
concretely for duplicate detection: an earlier, bucket-rounded key let a
position a millimetre on either side of a rounding boundary pass as
"different" (2026-10-02, third-correction review found 6 such near-duplicate
pairs the key had missed); `deduplicate_by_distance` replaces it with a
direct distance comparison every caller shares.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar

from reasoning.vlm.capability_probes import ground_truth as gtlib
from reasoning.vlm.capability_probes import occlusion

# How many GT-matched robots a frame's `scene.stamp` must land within, to be
# used at all. Episodes in this battery log GT at a fixed physics tick
# (<=1/60 s); a looser bound tolerates the coarser cadence of older runs.
GT_MATCH_TOLERANCE_SEC = 0.5

# Two scenes naming the same reference robot, over the same tracked robot
# set, whose largest per-robot GT displacement is under this are treated as
# the same configuration: consecutive decision calls during a stalled
# episode log nearly identical positions a few seconds apart, and should not
# both count as independent evidence.
NEAR_DUPLICATE_MAX_DISPLACEMENT_M = 0.10

T = TypeVar("T")


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


def max_displacement_m(a: dict[str, dict], b: dict[str, dict]) -> float | None:
    """Return the largest per-robot GT displacement between two scenes.

    Args:
        a: robot_id -> `{"x", "y"}`.
        b: robot_id -> `{"x", "y"}`.

    Returns:
        The max Euclidean per-robot displacement, or None when `a` and `b`
        do not track the same set of robots (not comparable -- never counted
        as a duplicate of each other).
    """
    if set(a) != set(b):
        return None
    return max(
        ((a[rid]["x"] - b[rid]["x"]) ** 2 + (a[rid]["y"] - b[rid]["y"]) ** 2) ** 0.5
        for rid in a
    )


def deduplicate_by_distance(
    candidates: Sequence[T],
    reference_robot_id: Callable[[T], str | None],
    gt_robots: Callable[[T], dict[str, dict]],
    max_displacement: float = NEAR_DUPLICATE_MAX_DISPLACEMENT_M,
) -> list[T]:
    """Keep the first of each near-duplicate scene-configuration group.

    Two candidates are the same configuration when they name the same
    reference robot (or both name none, e.g. `robot_count`) and
    `max_displacement_m` between their GT robot positions is under
    `max_displacement`. O(n^2) in `len(candidates)`; the battery's candidate
    pools (low thousands at most) make this cheap enough for a one-shot
    build script.

    Args:
        candidates: Candidates to deduplicate, in scan order (the first of
            a duplicate group is kept, so scan order decides which).
        reference_robot_id: Accessor for a candidate's named robot.
        gt_robots: Accessor for a candidate's GT robot_id -> `{"x", "y"}`.
        max_displacement: Threshold below which two scenes are "the same".

    Returns:
        `candidates` with later members of each duplicate group removed.
    """
    kept: list[T] = []
    kept_data: list[tuple[str | None, dict[str, dict]]] = []
    for candidate in candidates:
        ref = reference_robot_id(candidate)
        robots = gt_robots(candidate)
        is_duplicate = False
        for other_ref, other_robots in kept_data:
            if other_ref != ref:
                continue
            displacement = max_displacement_m(robots, other_robots)
            if displacement is not None and displacement < max_displacement:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(candidate)
            kept_data.append((ref, robots))
    return kept


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
    from it by up to `ground_truth.M1_GT_MAX_DISAGREEMENT_M`. Four
    conditions: every robot clear of the frame edge (full label visible), no
    robot M1 itself marked STALE (unreliable positioning, by the project's
    own notes), every pair of robots far enough apart that their boxes/labels
    cannot visually merge, and -- the centre-distance check alone does not
    rule this out (two centres 70 px apart can still have one robot's status
    box overlapping the other's label rect) -- no robot's drawn box or label
    rect overlaps another robot's.

    Args:
        m1_robots: M1 robot_id -> `{"x", "y", "status"}` (status optional).
        m1_pixels: M1 robot_id -> pixel `(u, v)`, matching `m1_robots`.
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        True when the frame is legible under all four conditions.
    """
    pixels = list(m1_pixels.values())
    if any(not gtlib.is_away_from_frame_edge(u, v, width, height) for u, v in pixels):
        return False
    if any(robot.get("status") == "STALE" for robot in m1_robots.values()):
        return False
    ids = list(m1_pixels)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            (u_i, v_i), (u_j, v_j) = m1_pixels[ids[i]], m1_pixels[ids[j]]
            du, dv = u_i - u_j, v_i - v_j
            if (du * du + dv * dv) ** 0.5 < gtlib.MIN_ROBOT_SEPARATION_PX:
                return False
            rects_i = occlusion.robot_annotation_rects(ids[i], u_i, v_i)
            rects_j = occlusion.robot_annotation_rects(ids[j], u_j, v_j)
            if any(
                occlusion.rects_overlap(rect_i, rect_j)
                for rect_i in rects_i
                for rect_j in rects_j
            ):
                return False
    return True
