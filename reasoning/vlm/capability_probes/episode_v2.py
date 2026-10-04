"""Load battery-v2 frames and GT from run logs, and derive items per frame.

Shared by `scripts/build_capability_probe_manifest_v2.py` (selecting the
frozen item set) and `scripts/audit_capability_probe_manifest.py`
(re-deriving every v2 item from the same source files), so the two cannot
disagree on what a frame, a gate or an answer means -- the same discipline as
v1's `scanning.py`.

Two frame sources:

- **decision** frames: `<episode>/frames/<request_id>.png` beside
  `decisions/<request_id>.json`; M1's state is the artifact's `scene`
  (exactly what was drawn), and M1's overlays are read from the artifact's
  `prompt_conditions` (absent = none drawn, the pre-apparatus default).
- **snapshot** frames: the battery-v2 harvest's periodic dumps
  (`scripts/vm/frame_snapshots.py`): `snapshots/frames.jsonl` gives each
  annotated PNG's full-precision header stamp, and `snapshots/scene_state.jsonl`
  holds every M1 `SceneState`; a frame is used only when a scene state with
  the identical stamp exists (M1 publishes the state and the annotated frame
  from one `process_frame` call), so status colour and drawn position are
  exact, never interpolated. Overlays come from that state's
  `diagnostics.annotation_overlays`.

A frame with the metric grid drawn is never used (the grid is a separate A/B
condition, and a confound here); trails decide the item's frame condition.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from reasoning.vlm.capability_probes import dynamics as dyn
from reasoning.vlm.capability_probes import ground_truth as gtlib
from reasoning.vlm.capability_probes import scanning

# Scope bound shared with v1 and the v2 design (<= 5 active robots).
MAX_ROBOTS = 5

_ANALYSIS_RE = re.compile(
    r"\[(\d+\.\d+)\] \[orchestrator_node\]: starting analysis request=([0-9a-f]+)"
)
_DISPATCH_RE = re.compile(
    r"\[(\d+\.\d+)\] \[orchestrator_node\]: dispatch request=([0-9a-f]+) command=(\S+) robot=(\S+)"
)
_RESOLVED_RE = re.compile(
    r"\[(\d+\.\d+)\] \[orchestrator_node\]: command (\S+) resolved status=(\S+)"
)
_INF = float("inf")


@dataclass
class EpisodeData:
    """One episode's GT, identity and command-activity windows."""

    episode_dir: Path
    run_id: str
    scenario: str
    track: dyn.GtTrack
    # None when M5's log is missing or unmappable: conflict_prediction cannot
    # apply its exclusion rule, so it takes no items from such an episode.
    command_windows: list[tuple[float, float]] | None
    onset_windows: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class FrameRecord:
    """One annotated frame and the exact M1 state it was drawn from."""

    source: str  # "decision" | "snapshot"
    ref: str
    path: Path
    stamp: float
    m1_robots: dict[str, dict]
    overlays: tuple[str, ...]

    @property
    def condition(self) -> str | None:
        """`trails_on` / `trails_off`, or None when the metric grid is drawn."""
        if "metric_grid" in self.overlays:
            return None
        return "trails_on" if "motion_trails" in self.overlays else "trails_off"


def png_size(path: Path) -> tuple[int, int] | None:
    """Return `(width, height)` from a PNG's IHDR header, or None if not a PNG."""
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _scenario_name(episode_dir: Path) -> str:
    manifest = episode_dir / "gt" / "run_manifest.json"
    if manifest.is_file():
        try:
            return json.loads(manifest.read_text(encoding="utf-8")).get(
                "scenario", episode_dir.name
            )
        except (json.JSONDecodeError, OSError):
            pass
    return episode_dir.name


def _decision_stamps(episode_dir: Path) -> dict[str, float]:
    stamps: dict[str, float] = {}
    decisions = episode_dir / "decisions"
    if not decisions.is_dir():
        return stamps
    for path in decisions.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            stamps[data["request_id"]] = float(data["scene"]["stamp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return stamps


def command_windows_from_log(
    m5_log_text: str, decision_stamps: dict[str, float]
) -> list[tuple[float, float]] | None:
    """Return each dispatched request's sim-time activity window from M5's log.

    A window opens at the request's decision scene stamp (the analysis's
    input, which precedes the dispatch) and closes at the last `resolved`
    line of its commands, mapped into sim time via `(wall, sim)` anchors
    (`starting analysis` line wall time <-> decision stamp) plus
    `COMMAND_END_SLACK_SEC`; never resolved = open to the episode end.

    Args:
        m5_log_text: The episode's `m5.log`.
        decision_stamps: request_id -> decision `scene.stamp`.

    Returns:
        The windows, or None when a dispatch exists but no anchor can map it.
    """
    anchors = [
        (float(m.group(1)), decision_stamps[m.group(2)])
        for m in _ANALYSIS_RE.finditer(m5_log_text)
        if m.group(2) in decision_stamps
    ]
    dispatched: dict[str, list[tuple[float, str]]] = {}
    for m in _DISPATCH_RE.finditer(m5_log_text):
        dispatched.setdefault(m.group(2), []).append((float(m.group(1)), m.group(3)))
    if not dispatched:
        return []
    if not anchors:
        return None
    resolved: dict[str, float] = {}
    for m in _RESOLVED_RE.finditer(m5_log_text):
        resolved[m.group(2)] = max(resolved.get(m.group(2), 0.0), float(m.group(1)))
    windows = []
    for request_id, dispatches in dispatched.items():
        if request_id in decision_stamps:
            start = decision_stamps[request_id]
        else:
            # No artifact: map the dispatch wall time and pad generously early.
            start = dyn.wall_to_sim(min(w for w, _ in dispatches), anchors) - 5.0
        ends = [resolved.get(command_id) for _, command_id in dispatches]
        if any(end is None for end in ends):
            end = _INF
        else:
            end = dyn.wall_to_sim(max(ends), anchors) + dyn.COMMAND_END_SLACK_SEC
        windows.append((start, end))
    return sorted(windows)


def load_episode(episode_dir: Path, logs_root: Path) -> EpisodeData | None:
    """Load one episode's GT track and exclusion windows, or None without GT."""
    gt_path = episode_dir / "gt" / "ground_truth.jsonl"
    if not gt_path.is_file():
        return None
    track = dyn.GtTrack(scanning.load_gt_rows(gt_path))
    m5_log = episode_dir / "m5.log"
    windows = None
    if m5_log.is_file():
        windows = command_windows_from_log(
            m5_log.read_text(encoding="utf-8", errors="replace"), _decision_stamps(episode_dir)
        )
    onsets = dyn.motion_onset_times(track)
    return EpisodeData(
        episode_dir=episode_dir,
        run_id=str(episode_dir.relative_to(logs_root)),
        scenario=_scenario_name(episode_dir),
        track=track,
        command_windows=windows,
        onset_windows=[
            (t - dyn.ONSET_HALF_WINDOW_SEC, t + dyn.ONSET_HALF_WINDOW_SEC) for t in onsets.values()
        ],
    )


def _m1_robots(robots: list[dict]) -> dict[str, dict]:
    return {
        r["robot_id"]: {
            "x": r["x"],
            "y": r["y"],
            "theta": r.get("theta"),
            "status": r.get("status"),
        }
        for r in robots
    }


def _decision_overlays(decision: dict) -> tuple[str, ...]:
    conditions = decision.get("prompt_conditions") or {}
    return tuple(
        name
        for name in ("metric_grid", "motion_trails")
        if isinstance(conditions.get(name), dict) and conditions[name].get("m1_drawn")
    )


def iter_decision_frames(episode_dir: Path) -> Iterator[FrameRecord]:
    """Yield every decision frame with its exact M1 state (scan order: file name)."""
    decisions, frames = episode_dir / "decisions", episode_dir / "frames"
    if not (decisions.is_dir() and frames.is_dir()):
        return
    for path in sorted(decisions.glob("*.json")):
        try:
            decision = json.loads(path.read_text(encoding="utf-8"))
            request_id = decision["request_id"]
            stamp = float(decision["scene"]["stamp"])
            robots = _m1_robots(decision["scene"]["robots"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        frame = frames / f"{request_id}.png"
        if frame.is_file():
            yield FrameRecord(
                "decision", request_id, frame, stamp, robots, _decision_overlays(decision)
            )


def _snapshot_states(snap_dir: Path) -> dict[float, dict]:
    states: dict[float, dict] = {}
    path = snap_dir / "scene_state.jsonl"
    if not path.is_file():
        return states
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                state = json.loads(line)
                states[round(float(state["stamp"]), 3)] = state
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
    return states


def iter_snapshot_frames(episode_dir: Path) -> Iterator[FrameRecord]:
    """Yield every annotated snapshot that has an exact-stamp M1 state."""
    snap_dir = episode_dir / "snapshots"
    index = snap_dir / "frames.jsonl"
    if not index.is_file():
        return
    states = _snapshot_states(snap_dir)
    with index.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    for row in rows:
        if row.get("topic") != "annotated":
            continue
        stamp = row["stamp_sec"] + row["stamp_nanosec"] * 1e-9
        state = states.get(round(stamp, 3))
        path = snap_dir / row["file"]
        if state is None or not path.is_file():
            continue
        overlays = tuple((state.get("diagnostics") or {}).get("annotation_overlays") or ())
        yield FrameRecord(
            "snapshot", row["file"], path, stamp, _m1_robots(state["robots"]), overlays
        )


def find_frame(episode_dir: Path, source: str, ref: str) -> FrameRecord | None:
    """Return the one frame `(source, ref)` of an episode, or None."""
    frames = (
        iter_decision_frames(episode_dir)
        if source == "decision"
        else iter_snapshot_frames(episode_dir)
    )
    return next((frame for frame in frames if frame.ref == ref), None)


@dataclass
class FrameContext:
    """A frame that passed every frame-level gate, with its GT and motion facts."""

    frame: FrameRecord
    gt_row: dict
    gt_robots: dict[str, dict]
    width: int
    height: int
    disagreement_m: float
    motions: dict[str, dyn.RobotMotion]


def gate_frame(
    episode: EpisodeData,
    frame: FrameRecord,
    homography,
    calibration_image_size: tuple[int, int],
) -> tuple[FrameContext | None, str]:
    """Apply the frame-level gates shared by all three v2 types.

    Gates, in order: metric grid not drawn; a GT row within
    `DYNAMIC_GT_MATCH_TOLERANCE_SEC`; 2..`MAX_ROBOTS` robots; M1 and GT
    tracking the same robots within `M1_GT_MAX_DISAGREEMENT_M`; frame size
    equal to the calibration's; v1's `scene_is_legible` (edge clearance,
    separation, no STALE, no box/label overlap) on M1's drawn positions;
    and GT motion available for every robot.

    Returns:
        `(context, "ok")`, or `(None, drop_reason)`.
    """
    if frame.condition is None:
        return None, "metric_grid_drawn"
    row = episode.track.row_near(frame.stamp)
    if row is None:
        return None, "no_matching_gt"
    gt_robots = {rid: dict(r) for rid, r in row["robots"].items()}
    if not 2 <= len(gt_robots) <= MAX_ROBOTS:
        return None, "robot_count_out_of_scope"
    disagreement = gtlib.max_m1_gt_disagreement_m(frame.m1_robots, gt_robots)
    if disagreement > gtlib.M1_GT_MAX_DISAGREEMENT_M:
        return None, "m1_gt_disagreement"
    size = png_size(frame.path)
    if size is None:
        return None, "frame_missing"
    if size != tuple(calibration_image_size):
        return None, "calibration_scale_mismatch"
    width, height = size
    m1_pixels = {
        rid: gtlib.world_to_pixel(r["x"], r["y"], homography) for rid, r in frame.m1_robots.items()
    }
    if not scanning.scene_is_legible(frame.m1_robots, m1_pixels, width, height):
        return None, "scene_not_legible"
    motions: dict[str, dyn.RobotMotion] = {}
    for rid, r in gt_robots.items():
        velocity = episode.track.velocity(rid, frame.stamp)
        if velocity is None:
            return None, "no_matching_gt"
        speed = (velocity[0] ** 2 + velocity[1] ** 2) ** 0.5
        # Project the 0.5 s displacement through the homography in float
        # (integer pixels would quantise slow motion to zero).
        u1, v1 = _world_to_pixel_float(
            r["x"] + velocity[0] * dyn.MOTION_WINDOW_SEC,
            r["y"] + velocity[1] * dyn.MOTION_WINDOW_SEC,
            homography,
        )
        u0f, v0f = _world_to_pixel_float(r["x"], r["y"], homography)
        motions[rid] = dyn.RobotMotion(
            robot_id=rid,
            speed_mps=speed,
            motion=dyn.motion_class(speed),
            reversing=dyn.is_reversing(velocity, r["theta"]) if speed > 0 else False,
            pixel_motion=(u1 - u0f, v1 - v0f),
            pixel=(u0f, v0f),
        )
    return (
        FrameContext(frame, row, gt_robots, width, height, disagreement, motions),
        "ok",
    )


def _world_to_pixel_float(x: float, y: float, homography) -> tuple[float, float]:
    # Same direction and maths as `swarm_perception.geometry.world_to_pixel`
    # (inverse of M1's pixel-to-world homography), without the int rounding.
    import numpy as np

    inverse = np.linalg.inv(np.asarray(homography, dtype=float))
    p = inverse @ np.array([x, y, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


@dataclass(frozen=True)
class Derived:
    """One derived item's question, options and answer, before selection."""

    probe_type: str
    question_key: str
    question: str
    options: list[str]
    correct_answer: str
    reference_robot_id: str | None
    derivation: dict


def question_text(probe_type: str, question_key: str) -> str:
    """Return the registered question wording for a question key."""
    if probe_type == "motion_direction":
        kind, _, name = question_key.partition(":")
        if kind == "robot":
            return f"Which robot is currently moving toward robot {name}?"
        return f"Which robot is currently moving toward the {name} edge of the image?"
    if probe_type == "conflict_prediction":
        a, b = question_key.split("|")
        return (
            f"Will robots {a} and {b} come within 0.5 m of each other (centre to centre) "
            "at any point in the next 10 seconds?"
        )
    if probe_type == "temporal_order":
        kind, _, pair = question_key.partition(":")
        a, b = pair.split("|")
        if kind == "goal":
            return (
                f"Robots {a} and {b} have both reached their goals. "
                "Which of them reached its goal first?"
            )
        return f"Robots {a} and {b} have both come to a stop. Which of them stopped first?"
    raise ValueError(f"unknown v2 probe_type {probe_type!r}")


def candidate_keys(ctx: FrameContext, probe_type: str) -> list[str]:
    """Return every question key a frame could pose for one probe type."""
    ids = sorted(ctx.gt_robots)
    pairs = [f"{a}|{b}" for i, a in enumerate(ids) for b in ids[i + 1 :]]
    if probe_type == "motion_direction":
        keys = [f"edge:{side}" for side in dyn.EDGE_DIRECTIONS_PX]
        if len(ids) >= 3:
            keys += [f"robot:{rid}" for rid in ids]
        return keys
    if probe_type == "conflict_prediction":
        return pairs
    if probe_type == "temporal_order":
        return [f"{kind}:{pair}" for kind in ("goal", "stop") for pair in pairs]
    raise ValueError(f"unknown v2 probe_type {probe_type!r}")


def _m1_consistent(m1_status: str | None, motion: str) -> bool:
    if motion == "moving":
        return m1_status in ("MOVING", "SLOW")
    if motion == "stationary":
        return m1_status == "STOPPED"
    return False


def derive(
    episode: EpisodeData, ctx: FrameContext, probe_type: str, question_key: str
) -> Derived | str:
    """Derive one item from a gated frame, or return the drop reason.

    The answer-level rules on top of `dynamics`: for motion_direction and
    conflict_prediction, M1's drawn status of every robot the answer depends
    on must agree with its GT motion class (MOVING/SLOW for moving, STOPPED
    for stationary) -- the image must not contradict the GT answer, v1's
    `m1_gt_answer_disagreement` rule; conflict_prediction additionally
    applies the command-activity exclusion.
    """
    t = ctx.frame.stamp
    if probe_type == "motion_direction":
        answer, reason, classes = dyn.motion_direction_answer(ctx.motions, question_key)
        if answer is None:
            return reason
        options = sorted(classes)
        for rid in options:
            if not _m1_consistent(ctx.frame.m1_robots[rid].get("status"), ctx.motions[rid].motion):
                return "m1_gt_answer_disagreement"
        kind, _, name = question_key.partition(":")
        derivation = {f"class_{rid}": c for rid, c in classes.items()}
        derivation.update({f"speed_{rid}": round(ctx.motions[rid].speed_mps, 4) for rid in options})
        return Derived(
            probe_type,
            question_key,
            question_text(probe_type, question_key),
            options,
            answer,
            name if kind == "robot" else None,
            derivation,
        )

    if probe_type == "conflict_prediction":
        a, b = question_key.split("|")
        if episode.command_windows is None:
            return "no_command_log"
        answer, reason, facts = dyn.conflict_prediction_answer(episode.track, a, b, t)
        if answer is None:
            return reason
        for rid in (a, b):
            m = ctx.motions[rid]
            if m.motion == "ambiguous":
                return "ambiguous_motion"
            if m.motion == "moving" and m.reversing:
                return "reversing_robot"
            if not _m1_consistent(ctx.frame.m1_robots[rid].get("status"), m.motion):
                return "m1_gt_answer_disagreement"
        windows = list(episode.command_windows) + list(episode.onset_windows)
        if not dyn.horizon_is_command_free(t, dyn.CONFLICT_HORIZON_SEC, windows):
            return "command_in_horizon"
        derivation = {k: round(v, 4) for k, v in facts.items()}
        return Derived(
            probe_type,
            question_key,
            question_text(probe_type, question_key),
            ["yes", "no"],
            answer,
            a,
            derivation,
        )

    if probe_type == "temporal_order":
        kind, _, pair = question_key.partition(":")
        a, b = pair.split("|")
        answer, reason, facts = dyn.temporal_order_answer(episode.track, kind, a, b, t)
        if answer is None:
            return reason
        derivation = {k: round(v, 4) for k, v in facts.items()}
        derivation.update(
            {f"m1_status_{rid}": ctx.frame.m1_robots[rid].get("status") for rid in (a, b)}
        )
        return Derived(
            probe_type,
            question_key,
            question_text(probe_type, question_key),
            [a, b],
            answer,
            None,
            derivation,
        )

    raise ValueError(f"unknown v2 probe_type {probe_type!r}")


def discover_episodes(logs_root: Path) -> list[Path]:
    """Return every episode dir under `logs_root` holding GT and some frame source."""
    episodes = set()
    for gt in logs_root.rglob("gt/ground_truth.jsonl"):
        episode = gt.parent.parent
        if (episode / "decisions").is_dir() or (episode / "snapshots" / "frames.jsonl").is_file():
            episodes.add(episode)
    return sorted(episodes)
