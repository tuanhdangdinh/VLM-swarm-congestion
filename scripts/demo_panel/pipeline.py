"""Glue: bundle -> transcript -> timeline -> composite frames -> MP4."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.demo_panel.bundle import (
    GT_CLOCK_OFFSET_SEC,
    Bundle,
    TimeContext,
    build_time_map,
    load_bundle,
    load_gt,
)
from scripts.demo_panel.models import Transcript
from scripts.demo_panel.render import (
    Compositor,
    H264Writer,
    Layout,
    TerminalPane,
    load_mono_font,
    title_card,
)
from scripts.demo_panel.scene import (
    CameraClipScene,
    GroundTruthScene,
    GroundTruthTrack,
    OccupancyMap,
    SceneSource,
    load_footprint,
)
from scripts.demo_panel.terminal import build_transcript
from scripts.demo_panel.timeline import (
    CallSpan,
    Timeline,
    TimelineItem,
    TimelineParams,
    build_timeline,
)
from scripts.demo_panel.timemap import ClipTimeMap

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = REPO_ROOT / "ros2_ws" / "src" / "swarm_simulation" / "maps"
NAV2_PARAMS = REPO_ROOT / "ros2_ws" / "src" / "swarm_simulation" / "config" / "nav2_params.yaml"
DECISION_BLOCK_HOLD_SEC = 4.0
SMALL_BLOCK_HOLD_SEC = 1.5


@dataclass
class Prepared:
    """Everything needed to render one bundle."""

    bundle: Bundle
    tc: TimeContext
    transcript: Transcript
    pane: TerminalPane
    timeline: Timeline
    scene: SceneSource


def load_clip_map(path: Path) -> ClipTimeMap:
    """Read a camera clip's frame-to-sim mapping from JSON.

    Accepted shapes (first match wins):
    `{"anchors": [[frame_index, sim_time], ...]}`,
    `{"frame_sim_times": [sim_time_of_frame_0, ...]}`, or
    `{"first_stamp": s0, "last_stamp": s1, "frames": n}`.

    Args:
        path: JSON file.

    Returns:
        The map.

    Raises:
        ValueError: None of the accepted shapes is present.
    """
    data = json.loads(path.read_text())
    if "anchors" in data:
        return ClipTimeMap([(int(i), float(s)) for i, s in data["anchors"]])
    if "frame_sim_times" in data:
        times = [float(s) for s in data["frame_sim_times"]]
        pts: list[tuple[int, float]] = []
        for i, s in enumerate(times):
            if not pts or s > pts[-1][1]:
                pts.append((i, s))
        return ClipTimeMap(pts)
    if {"first_stamp", "last_stamp", "frames"} <= set(data):
        return ClipTimeMap.from_recorder(
            float(data["first_stamp"]), float(data["last_stamp"]), int(data["frames"])
        )
    raise ValueError(f"{path}: no anchors / frame_sim_times / first_stamp+last_stamp+frames")


def gt_scene(b: Bundle) -> GroundTruthScene:
    """Ground-truth reconstruction with the repo's static map for the bundle's scenario."""
    track = GroundTruthTrack.load(b.root / "gt" / "ground_truth.jsonl")
    fp = load_footprint(NAV2_PARAMS)
    map_name = b.condition.get("map") or b.condition.get("scenario")
    occ = None
    map_yaml = MAPS_DIR / f"warehouse_map_{map_name}.yaml"
    if map_name and map_yaml.is_file():
        occ = OccupancyMap.load(map_yaml)
    detail = (
        f"Racks: repo map {map_yaml.name if occ else '(none found)'} (not part of the bundle); "
        f"footprint {fp.x_max - fp.x_min:.2f} x {fp.y_max - fp.y_min:.2f} m from {fp.source}; "
        f"GT drawn at sim t - {GT_CLOCK_OFFSET_SEC:.3f} s (documented GT clock offset); grid 0.5 m."
    )
    return GroundTruthScene(track, fp, occ, GT_CLOCK_OFFSET_SEC, detail=detail)


def run_caption(b: Bundle) -> str:
    """Top caption: run label, scenario, arm, backend, start date (UTC)."""
    c = b.condition
    started = str(b.manifest.get("started_at_utc", ""))[:16].replace("T", " ")
    layer2_off = any("reasoning_enabled=false" in ln for ln in b.m5)
    return (
        f"{c.get('label', b.name)}  |  {c.get('scenario')}  |  arm {c.get('arm')}  |  "
        f"{'Layer 2 OFF' if layer2_off else 'backend ' + str(c.get('backend'))}  |  {started} UTC"
    )


def timeline_items(t: Transcript, pane: TerminalPane) -> list[TimelineItem]:
    """Timeline inputs: rows per item, command-block membership and holds."""
    kinds = [it.kind for it in t.items]
    out: list[TimelineItem] = []
    i = 0
    while i < len(kinds):
        if kinds[i] in ("command", "output"):
            j = i
            while j < len(kinds) and kinds[j] in ("command", "output"):
                j += 1
            n_cmds = sum(1 for k in kinds[i:j] if k == "command")
            hold = DECISION_BLOCK_HOLD_SEC if n_cmds > 1 else SMALL_BLOCK_HOLD_SEC
            for k in range(i, j):
                out.append(
                    TimelineItem(
                        t.items[k].sim_time,
                        pane.rows_of(k),
                        in_block=True,
                        block_end=k == j - 1,
                        block_hold_sec=hold if k == j - 1 else 0.0,
                    )
                )
            i = j
        else:
            out.append(
                TimelineItem(
                    t.items[i].sim_time,
                    pane.rows_of(i),
                    in_block=False,
                    sets_pace=t.items[i].kind != "marker",
                )
            )
            i += 1
    return out


def prepare(
    bundle_dir: Path,
    layout: Layout,
    camera: Sequence[Path] | None = None,
    camera_map: Path | None = None,
    fallback_error: float | None = None,
    params: TimelineParams | None = None,
    font: str | None = None,
    camera_label: str = "Camera recording",
) -> Prepared:
    """Load a bundle and build its transcript, timeline and scene source.

    Args:
        bundle_dir: Run bundle.
        layout: Frame layout (sets the terminal width in characters).
        camera: Optional camera clip segments (in order) for the left pane.
        camera_map: JSON frame-to-sim mapping for `camera` (required with it).
        fallback_error: Calibrated fallback-anchor error for bundles without
            sim-stamped log lines.
        params: Timeline speeds and print rates.
        font: Monospace font override.
        camera_label: Caption naming the recorded camera topic.

    Returns:
        The prepared bundle.

    Raises:
        ValueError: `camera` given without `camera_map`.
    """
    b = load_bundle(bundle_dir)
    gt = load_gt(b)
    sim_end = float(gt[-1]["sim_time_sec"]) + GT_CLOCK_OFFSET_SEC
    tc = build_time_map(b, gt, fallback_error)
    transcript = build_transcript(b, tc, sim_end)
    tb = layout.term_box
    pane = TerminalPane(transcript, (tb[2], tb[3]), load_mono_font(layout.font_px, font))
    calls = [CallSpan(a, s, w) for a, s, w in transcript.calls]
    tl = build_timeline(timeline_items(transcript, pane), calls, sim_end, params)
    if camera:
        if camera_map is None:
            raise ValueError("--camera needs --camera-map")
        names = ", ".join(c.name for c in camera)
        scene: SceneSource = CameraClipScene(
            list(camera),
            load_clip_map(camera_map),
            detail=f"{names}; frame-to-sim timing from {camera_map.name}",
            label=camera_label,
        )
    else:
        scene = gt_scene(b)
    return Prepared(b, tc, transcript, pane, tl, scene)


def compositor(p: Prepared, layout: Layout, font: str | None = None) -> Compositor:
    """Compositor for a prepared bundle, with the alignment note when uncertain."""
    note = None
    if p.tc.info.uncertain:
        note = f"Log/sim {p.tc.info.note}."
    return Compositor(
        p.transcript, p.timeline, p.scene, p.pane, run_caption(p.bundle), layout, font, note
    )


def render(
    clips: list[Compositor | tuple[list[str], float]],
    out: Path,
    fps: float,
    layout: Layout,
    font: str | None = None,
    crf: int = 23,
) -> float:
    """Encode a sequence of composited clips and caption cards to one MP4.

    Args:
        clips: Compositors, or `(caption lines, seconds)` title cards.
        out: Output path.
        fps: Frame rate.
        layout: Frame layout.
        font: Monospace font override.
        crf: x264 quality.

    Returns:
        Total duration in seconds.
    """
    w = H264Writer(out, (layout.width, layout.height), fps, crf)
    total = 0.0
    try:
        for clip in clips:
            if isinstance(clip, Compositor):
                n = int(clip.tl.total_video_sec * fps + 0.999)
                for i in range(n):
                    w.write(clip.frame(i / fps))
                total += n / fps
            else:
                card = title_card(clip[0], layout, font)
                n = int(clip[1] * fps)
                for _ in range(n):
                    w.write(card)
                total += n / fps
    finally:
        w.close()
    return total
