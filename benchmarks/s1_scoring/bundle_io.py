"""Read the S1 bundle records that prereg-v3 A33(0) names, on one clock.

Implements A33(0) (`docs/superpowers/specs/2026-10-06-prereg-v3-design.md`,
`feat/v3-design`): the files and keys read, the per-run GT-offset fit ("the
only sanctioned GT<->ROS join"), the episode origin (robot_1's `released`),
the observation end T_end and the single censoring rule. The reading logic is
a minimal copy of the key names the batch-6 kit scorer uses; the offset fit
is `scripts/s1_live_conflict_stats.py` `_gt_offset` at 97d68e0, copied so the
scorer does not import an unpackaged script.

A bundle without a task stream, a `stream_start` or a robot_1 `released`
event is not an episode (`NotAnEpisodeError`); there is no fallback t0.

Never read: GT `conflict_type` / `involved_robots` / `robot_robot_contacts`
(scenario-declared or stubs), any `m5.log` stamp (wall clock), and
`run_manifest.completed` as a task outcome.
"""

from __future__ import annotations

import bisect
import glob
import json
import math
import statistics
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

CensorReason = Literal["horizon", "stop_flag", "aborted_other", "common_window"]

# A33(0): offset grid 0.00-1.00 s in 0.01 s steps, MOVING rows capped at 3000.
OFFSET_STEPS = 101
OFFSET_MAX_ROWS = 3000


class NotAnEpisodeError(ValueError):
    """A bundle that A33(0) does not count as an episode (e.g. a bring-up abort)."""


class GTSample(BaseModel):
    """One ground-truth sample on the GT clock."""

    model_config = ConfigDict(frozen=True)

    t: float
    poses: dict[str, tuple[float, float, float]]  # robot_id -> (x, y, speed_mps)


class BundleRecords(BaseModel):
    """Everything the S1 scorers read from one bundle, already on one clock.

    All `*_rel` values are rel-s: GT sim-s minus t0_gt, where t0_gt is robot_1's
    release mapped onto the GT clock (A33(0)). M1-clock times map as
    `sim_t - t0_m1` because the offset cancels.
    """

    model_config = ConfigDict(frozen=True)

    bundle: str
    seed: int | None
    tasks_total: int
    nodes: dict[str, tuple[float, float]]
    start_nodes: dict[str, str]
    sequences: dict[str, list[str]]
    task_events: list[dict[str, Any]]
    manifest_makespan_sim_sec: float | None
    gt: list[GTSample]
    gt_offset_s: float
    t0_m1: float
    t0_gt: float
    t_end_rel: float
    abs_gt_end: float
    censor_reason: CensorReason
    artifacts: list[dict[str, Any]]

    def m1_to_rel(self, t_m1: float) -> float:
        """Map an M1-clock time (tasks `sim_t`, artifact `scene.stamp`) to rel-s."""
        return t_m1 - self.t0_m1

    def gt_to_rel(self, t_gt: float) -> float:
        """Map a GT-clock time to rel-s."""
        return t_gt - self.t0_gt


def _jl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open() if line.strip()]


def gt_offset(gt: list[dict[str, Any]], scene: list[dict[str, Any]]) -> float:
    """Fit the per-run GT offset (GT sim-s = M1 stamp - offset), A33(0).

    Args:
        gt: Parsed `gt/ground_truth.jsonl` rows.
        scene: Parsed `m5_scene.jsonl` rows.

    Returns:
        The offset in seconds on the 0.00-1.00 s grid whose median position
        error over MOVING M1 rows is smallest (0.0 without MOVING rows).
    """
    gt_t = [r["sim_time_sec"] for r in gt]

    def at(t: float) -> dict[str, Any]:
        i = bisect.bisect_left(gt_t, t)
        return gt[min(max(i, 0), len(gt) - 1)]

    moving = [
        (r["scene"]["stamp"], v["robot_id"], v["x"], v["y"])
        for r in scene
        if r["scene"].get("stamp") is not None
        for v in r["scene"]["robots"]
        if v["status"] == "MOVING"
    ]
    moving = moving[:: max(1, len(moving) // OFFSET_MAX_ROWS)]
    best: tuple[float, float] | None = None
    for k in range(OFFSET_STEPS):
        off = k / 100.0
        errs = [
            math.hypot(x - at(st - off)["robots"][rid]["x"], y - at(st - off)["robots"][rid]["y"])
            for st, rid, x, y in moving
            if rid in at(st - off)["robots"]
        ]
        if errs:
            med = statistics.median(errs)
            if best is None or med < best[1]:
                best = (off, med)
    return best[0] if best else 0.0


def censor_reason(run_manifest: dict[str, Any]) -> CensorReason:
    """Label why observation ended, from `gt/run_manifest.json` (A33(0)).

    Args:
        run_manifest: The parsed run manifest (may be empty).

    Returns:
        `horizon` when Isaac ran its full length, `stop_flag` for a stop-flag
        abort (cost cap or operator stop), else `aborted_other`.
    """
    if run_manifest.get("completed") is True:
        return "horizon"
    if run_manifest.get("abort_reason") == "stop_flag":
        return "stop_flag"
    return "aborted_other"


def read_bundle(bundle: Path) -> BundleRecords:
    """Read one bundle's A33(0) records and put them on one clock.

    Args:
        bundle: The bundle directory.

    Returns:
        The records.

    Raises:
        NotAnEpisodeError: When the bundle is not an episode under A33(0): no
            tasks JSONL, no `stream_start`, no robot_1 `released` event, or
            no GT JSONL (a bring-up abort's attempt directory).
        ValueError: When the bundle holds more than one tasks JSONL.
    """
    bundle = Path(bundle)
    task_files = sorted(glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")))
    if not task_files:
        raise NotAnEpisodeError(f"{bundle}: no decisions/tasks_*.jsonl")
    if len(task_files) > 1:
        raise ValueError(f"{bundle}: {len(task_files)} tasks JSONL files, expected one")
    gt_path = bundle / "gt" / "ground_truth.jsonl"
    if not gt_path.exists():
        raise NotAnEpisodeError(f"{bundle}: no gt/ground_truth.jsonl")
    tasks = _jl(Path(task_files[0]))
    stream = next((r for r in tasks if r.get("event") == "stream_start"), None)
    if stream is None:
        raise NotAnEpisodeError(f"{bundle}: tasks JSONL has no stream_start event")
    manifests = [r for r in tasks if r.get("event") == "manifest"]
    events = [
        r for r in tasks
        if r.get("event") in ("released", "issued", "arrived", "dwell_complete")
    ]
    gt_rows = _jl(gt_path)
    scene = _jl(bundle / "m5_scene.jsonl")
    run_manifest_path = bundle / "gt" / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text()) if run_manifest_path.exists() else {}

    off = gt_offset(gt_rows, scene)
    t0_m1 = next(
        (r["sim_t"] for r in events if r["event"] == "released" and r["robot_id"] == "robot_1"),
        None,
    )
    if t0_m1 is None:
        raise NotAnEpisodeError(f"{bundle}: no robot_1 released event (A33(0): no fallback t0)")
    t0_gt = t0_m1 - off

    gt = [
        GTSample(
            t=r["sim_time_sec"],
            poses={
                rid: (v["x"], v["y"], float(v.get("speed_mps") or 0.0))
                for rid, v in r["robots"].items()
            },
        )
        for r in gt_rows
    ]
    artifacts = []
    for path in glob.glob(str(bundle / "decisions" / "*.json")):
        artifact = json.loads(Path(path).read_text())
        if (artifact.get("scene") or {}).get("stamp") is None:
            continue
        artifacts.append(artifact)
    artifacts.sort(key=lambda a: (a["scene"]["stamp"], a.get("request_id") or ""))

    return BundleRecords(
        bundle=bundle.name,
        seed=stream.get("seed"),
        tasks_total=int(stream.get("tasks_total") or 25),
        nodes={k: (float(v[0]), float(v[1])) for k, v in (stream.get("nodes") or {}).items()},
        start_nodes=dict(stream.get("start_nodes") or {}),
        sequences={k: list(v) for k, v in (stream.get("sequences") or {}).items()},
        task_events=events,
        manifest_makespan_sim_sec=manifests[-1].get("makespan_sim_sec") if manifests else None,
        gt=gt,
        gt_offset_s=off,
        t0_m1=t0_m1,
        t0_gt=t0_gt,
        t_end_rel=gt[-1].t - t0_gt,
        abs_gt_end=gt[-1].t,
        censor_reason=censor_reason(run_manifest),
        artifacts=artifacts,
    )


def truncate(records: BundleRecords, tau_rel: float) -> BundleRecords:
    """Cut a bundle's observation at rel-s tau, for A33(7)'s common window.

    GT samples, task events and analyses after tau are dropped and the
    episode is re-labelled censored at tau (`common_window`) unless tau is at
    or beyond its own T_end, in which case the records are returned unchanged.

    Args:
        records: The full records.
        tau_rel: The window end in rel-s.

    Returns:
        The truncated records.
    """
    if tau_rel >= records.t_end_rel:
        return records
    t_gt_cut = records.t0_gt + tau_rel
    gt = [s for s in records.gt if s.t <= t_gt_cut]
    events = [e for e in records.task_events if records.m1_to_rel(e["sim_t"]) <= tau_rel]
    artifacts = [
        a for a in records.artifacts if records.m1_to_rel(a["scene"]["stamp"]) <= tau_rel
    ]
    return records.model_copy(
        update={
            "gt": gt,
            "task_events": events,
            "artifacts": artifacts,
            "t_end_rel": tau_rel,
            "abs_gt_end": t_gt_cut,
            "censor_reason": "common_window",
            "manifest_makespan_sim_sec": None,
        }
    )
