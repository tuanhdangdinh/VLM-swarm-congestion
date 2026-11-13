"""Build `BenchItem`s from S1b episode bundles (spec `docs/specs/v4_vlm_bench.md`).

One decision artifact is one item. Each item is self-contained, so scoring never
re-reads the bundle: it carries the stored prompt, the recorded answer, the live
M3 outcome, the grounding inputs, the classical history window and the A33 GT
context. Missing frames are normal for S1b (none were harvested); `frame_path`
is then None.
"""

from __future__ import annotations

import glob
import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import yaml

from benchmarks.s1_scoring.bundle_io import BundleRecords, read_bundle
from benchmarks.s1_scoring.conflicts import ConflictParams, conflict_episodes
from benchmarks.vlm_bench.models import (
    BenchItem,
    ClassicalWindow,
    GroundingContext,
    GTCluster,
    GTContext,
    LiveOutcome,
    MCReference,
    PromptRecord,
    RecordedAnswer,
    RobotIntent,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_COST_RE = re.compile(r"billed_calls=(\d+)\s+est_usd=([0-9.]+)")


def file_md5(path: Path) -> str | None:
    """Return a file's md5 hex digest, or None when it does not exist.

    Args:
        path: The file.

    Returns:
        The digest, or None.
    """
    return hashlib.md5(path.read_bytes()).hexdigest() if path.is_file() else None


def _read_condition(bundle: Path) -> dict[str, str]:
    path = bundle / "CONDITION.txt"
    if not path.is_file():
        return {}
    pairs = (tok.split("=", 1) for tok in path.read_text().split() if "=" in tok)
    return {k: v for k, v in pairs}


def _episode_label(bundle: Path) -> str:
    match = re.search(r"_(E\d+)_", bundle.name)
    return match.group(1) if match else bundle.name


def est_usd_per_call(bundle: Path) -> float | None:
    """Per-call dollar estimate from the bundle's `cost.log` last line.

    Args:
        bundle: The bundle directory.

    Returns:
        `est_usd / billed_calls`, or None when the log is absent or has no calls.
    """
    path = bundle / "cost.log"
    if not path.is_file():
        return None
    matches = _COST_RE.findall(path.read_text())
    if not matches:
        return None
    calls, usd = matches[-1]
    return float(usd) / int(calls) if int(calls) > 0 else None


def task_stream_state(
    events: Sequence[dict[str, Any]],
    stream: dict[str, Any],
    stamp: float,
) -> tuple[dict[str, tuple[float, float]], dict[str, RobotIntent], set[str]]:
    """Rebuild M5's registry goal, task intent and held set at one stamp.

    Mirrors `TaskRegistry.mission_goal` (the current task node, from the latest
    `issued` event) and `TaskStream.departure` (next node, remaining dwell).

    Args:
        events: Task events (`released`, `issued`, `arrived`, `dwell_complete`,
            `robot_done`) on the M1 clock.
        stream: The `stream_start` record.
        stamp: The analysis stamp (M1 clock).

    Returns:
        `(goal_references, task_intents, held_robot_ids)`.
    """
    nodes = {k: (float(v[0]), float(v[1])) for k, v in (stream.get("nodes") or {}).items()}
    sequences = stream.get("sequences") or {}
    dwell = float(stream.get("dwell_sim_sec") or 0.0)
    goals: dict[str, tuple[float, float]] = {}
    intents: dict[str, RobotIntent] = {}
    released: set[str] = set()
    per_robot: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        if ev.get("sim_t") is None or ev["sim_t"] > stamp + 1e-9:
            continue
        rid = ev.get("robot_id")
        if rid is None:
            continue
        per_robot.setdefault(rid, []).append(ev)
    for rid, evs in per_robot.items():
        evs.sort(key=lambda e: e["sim_t"])
        if any(e["event"] == "released" for e in evs):
            released.add(rid)
        issued = [e for e in evs if e["event"] == "issued"]
        if not issued:
            continue
        last = issued[-1]
        k = int(last["task_index"])
        goal = tuple(last.get("goal") or nodes[last["node"]])
        goals[rid] = (float(goal[0]), float(goal[1]))
        done = any(e["event"] == "robot_done" for e in evs)
        completed = any(
            e["event"] == "dwell_complete" and e.get("task_index") == k for e in evs
        )
        if done or completed:
            intents[rid] = RobotIntent(goal=goals[rid])
            continue
        seq = sequences.get(rid) or []
        next_goal = nodes.get(seq[k + 1]) if k + 1 < len(seq) else None
        arrived = [e for e in evs if e["event"] == "arrived" and e.get("task_index") == k]
        remaining = dwell if not arrived else max(0.0, dwell - (stamp - arrived[-1]["sim_t"]))
        intents[rid] = RobotIntent(goal=goals[rid], next_goal=next_goal, dwell_sec=remaining)
    all_ids = set(sequences)
    held = all_ids - released
    return goals, intents, held


def _history_frames(
    scene_rows: Sequence[dict[str, Any]],
    stamp: float,
    window_sec: float,
    sample_period_sec: float,
    events: Sequence[dict[str, Any]],
    stream: dict[str, Any],
    latest_scene: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """The shadow ring buffer's contents at `stamp`, rebuilt from `m5_scene.jsonl`."""
    frames: list[dict[str, Any]] = []
    last: float | None = None
    for row in scene_rows:
        scene = row.get("scene") or {}
        st = scene.get("stamp")
        if st is None or scene.get("dropped_frame") or not scene.get("robots"):
            continue
        if st < stamp - window_sec or st >= stamp:
            continue
        if last is not None and st - last < sample_period_sec:
            continue
        last = st
        goals, _, held = task_stream_state(events, stream, st)
        frames.append(_frame(st, scene["robots"], goals, held))
    goals, _, held = task_stream_state(events, stream, stamp)
    scene_goals = {
        r["robot_id"]: tuple(r["goal"]) for r in latest_scene["robots"] if r.get("goal")
    }
    frames.append(_frame(stamp, latest_scene["robots"], {**goals, **scene_goals}, held))
    return tuple(frames)


def _frame(stamp, robots, goals, held):
    return {
        "stamp": float(stamp),
        "held_robot_ids": sorted(held & {r["robot_id"] for r in robots}),
        "robots": [
            {
                "robot_id": r["robot_id"],
                "x": r["x"],
                "y": r["y"],
                "theta": r["theta"],
                "linear_velocity": r.get("linear_velocity"),
                "status": r.get("status"),
                "goal": list(goals[r["robot_id"]]) if r["robot_id"] in goals else None,
            }
            for r in robots
        ],
    }


def load_mc_references(paths: Iterable[Path]) -> dict[int, MCReference]:
    """Read S1 MC first-conflict prediction files, keyed by stream seed.

    Batch 5/6 files carry per-grounder blocks; the `escort` block (the grounding
    file those batches ran) is preferred, then `pinned`, then the flat fields.

    Args:
        paths: `mc_seeds_*.jsonl` files.

    Returns:
        Seed -> reference.
    """
    out: dict[int, MCReference] = {}
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            block = rec.get("escort") or rec.get("pinned") or rec
            first = (rec.get("encounters") or [{}])[0]
            pair = tuple(rec.get("echo_names") or first.get("pair") or ())
            out[int(rec["seed"])] = MCReference(
                pair=pair,
                yielder=block.get("yielder"),
                outcome=block.get("outcome"),
                source=Path(path).name,
            )
    return out


def _clusters(conflicts, t_s, params: ConflictParams) -> tuple[GTCluster, ...]:
    return tuple(
        c for c in conflicts if c.onset_s - params.pre_s <= t_s <= c.end_s + params.post_s
    )


def _recorded(artifact: dict[str, Any], usd: float | None) -> RecordedAnswer:
    diag = artifact.get("diagnostics") or {}
    cfg = artifact.get("reasoner_config_effective") or diag.get("reasoner_config_effective") or {}
    usage = diag.get("token_usage")
    return RecordedAnswer(
        raw_text=artifact.get("raw_text"),
        decision=artifact.get("decision"),
        parse_status=diag.get("parse_status"),
        attempts=diag.get("attempts"),
        token_usage={k: int(v) for k, v in usage.items() if v is not None} if usage else None,
        latency_ms=diag.get("latency_ms"),
        backend_id=diag.get("backend_id"),
        model_id=cfg.get("model_id") or diag.get("served_model"),
        est_usd_per_call=usd,
    )


def _live(artifact: dict[str, Any]) -> LiveOutcome:
    from swarm_orchestrator.reasoning_pipeline import empty_reroute_fallback

    command = artifact.get("dispatched_command")
    refusal = artifact.get("yield_refusal_reason") or empty_reroute_fallback(command)
    stage2 = artifact.get("stage2") or {}
    return LiveOutcome(
        refusal_reason=refusal,
        dispatched_kinds=tuple(a.get("action") for a in (command or {}).get("actions") or []),
        stage2_status=stage2.get("status"),
        plan=artifact.get("plan"),
        # Read only by plan quality (`run.plan_artifacts`): a plan block the
        # prompt left out (v4 refusal feedback) still holds the failed legs a
        # revision answers. The prompt rebuild reads `PromptRecord.plan_state`.
        plan_state=(
            artifact.get("plan_state")
            or (artifact.get("plan_state_hidden") or {}).get("plan_state")
        ),
    )


def build_bundle_items(
    bundle: Path,
    mc: dict[int, MCReference] | None = None,
    conflict_params: ConflictParams | None = None,
    repo_root: Path = REPO_ROOT,
) -> list[BenchItem]:
    """Build one item per decision artifact of one episode bundle.

    Args:
        bundle: The bundle directory (must be an A33(0) episode).
        mc: MC references by seed; None attaches none.
        conflict_params: A33 matching-window parameters (A33 defaults when None).
        repo_root: Tree whose grounding files are md5-checked.

    Returns:
        Items in scene-stamp order; empty for a bundle without artifacts
        (Arm B).

    Raises:
        NotAnEpisodeError: When the bundle is not an episode under A33(0).
    """
    bundle = Path(bundle)
    params = conflict_params or ConflictParams()
    records: BundleRecords = read_bundle(bundle)
    if not records.artifacts:
        return []
    conflicts = tuple(
        GTCluster(
            index=c.index, onset_s=c.onset_s, end_s=c.end_s, involved=c.involved, pairs=c.pairs
        )
        for c in conflict_episodes(records, params)
    )
    task_file = sorted(glob.glob(str(bundle / "decisions" / "tasks_*.jsonl")))[0]
    task_rows = [json.loads(line) for line in Path(task_file).open() if line.strip()]
    stream = next(r for r in task_rows if r.get("event") == "stream_start")
    events = [r for r in task_rows if r.get("robot_id") and r.get("sim_t") is not None]
    scene_rows = [
        json.loads(line) for line in (bundle / "m5_scene.jsonl").open() if line.strip()
    ] if (bundle / "m5_scene.jsonl").is_file() else []
    overlay = yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text()) or {}
    condition = _read_condition(bundle)
    usd = est_usd_per_call(bundle)
    mc_ref = (mc or {}).get(records.seed) if records.seed is not None else None
    items: list[BenchItem] = []
    for art in records.artifacts:
        items.append(
            _build_item(
                bundle, art, records, conflicts, params, stream, events, scene_rows,
                overlay, condition, usd, mc_ref, repo_root,
            )
        )
    return items


def _build_item(
    bundle, art, records, conflicts, params, stream, events, scene_rows,
    overlay, condition, usd, mc_ref, repo_root,
) -> BenchItem:
    scene = art["scene"]
    stamp = float(scene["stamp"])
    t_s = records.m1_to_rel(stamp)
    goals, intents, _ = task_stream_state(events, stream, stamp)
    source = art.get("grounding_params_source") or {}
    params_path = source.get("path")
    recorded_params = source.get("params")
    file_md5_value = file_md5(repo_root / params_path) if params_path else None
    match_file = None
    if params_path and (repo_root / params_path).is_file() and recorded_params is not None:
        from swarm_orchestrator.reasoning_pipeline import load_grounding_source

        file_params = load_grounding_source(repo_root / params_path).params
        match_file = (
            file_params is not None
            and file_params.model_dump(mode="json")
            == _normalize_params(recorded_params, file_params)
        )
    shadow = art.get("shadow_classical") or {}
    window = float(shadow.get("window_sec") or 60.0)
    period = float(shadow.get("sample_period_sec") or 0.25)
    frames = _history_frames(scene_rows, stamp, window, period, events, stream, scene)
    prompt = art.get("prompt") or {}
    frame = bundle / "m5_frames" / f"{art['request_id']}.png"
    return BenchItem(
        item_id=f"{bundle.name}:{art['request_id']}",
        bundle=str(bundle),
        batch=bundle.parent.name,
        episode=_episode_label(bundle),
        condition=condition.get("tag", "pilot"),
        seed=records.seed,
        request_id=art["request_id"],
        stamp=stamp,
        t_s=t_s,
        scene=scene,
        prompt=PromptRecord(
            system_prompt=prompt.get("system_prompt"),
            user_prompt=prompt.get("user_prompt"),
            system_sha256=prompt.get("system_sha256"),
            user_sha256=prompt.get("user_sha256"),
            prompt_version=int(art.get("prompt_version") or 1),
            robot_order=str(art.get("robot_presentation_order") or "id_asc"),
            failure_context=art.get("failure_context"),
            last_failed_context=art.get("last_failed_context"),
            plan_state=art.get("plan_state"),
            prompt_conditions=art.get("prompt_conditions"),
        ),
        frame_path=str(frame) if frame.is_file() else None,
        recorded=_recorded(art, usd),
        live=_live(art),
        grounding=GroundingContext(
            overlay=overlay,
            params=recorded_params,
            params_path=params_path,
            params_file_md5=file_md5_value,
            params_match_file=match_file,
            goal_references=goals,
            task_intents=intents,
        ),
        classical=ClassicalWindow(
            window_sec=window,
            sample_period_sec=period,
            prior_attempts=int(shadow.get("prior_attempts") or 0),
            params=shadow.get("params"),
            frames=frames,
            recorded_decision=shadow.get("decision"),
        ),
        gt=GTContext(
            clusters=_clusters(conflicts, t_s, params),
            episode_conflicts=conflicts,
            pre_s=params.pre_s,
            post_s=params.post_s,
            t_end_s=records.t_end_rel,
        ),
        mc=mc_ref,
    )


def _normalize_params(recorded: dict[str, Any], _file_params: Any) -> dict[str, Any]:
    from reasoning.rag.maneuver_geometry import GroundingParams

    return GroundingParams(**recorded).model_dump(mode="json")


def write_items(items: Sequence[BenchItem], out: Path) -> None:
    """Write items as JSONL.

    Args:
        items: The items.
        out: Destination path (parents are created).
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for item in items:
            handle.write(json.dumps(item.model_dump(mode="json"), sort_keys=True) + "\n")


def read_items(path: Path) -> list[BenchItem]:
    """Read items written by `write_items`.

    Args:
        path: The JSONL file.

    Returns:
        The items.
    """
    return [
        BenchItem.model_validate(json.loads(line))
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
