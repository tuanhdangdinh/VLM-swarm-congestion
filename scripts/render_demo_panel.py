#!/usr/bin/env python3
"""Render a demo video: scene (camera or GT reconstruction) beside a log-replay terminal.

Offline post-processing only: reads one run bundle (never writes into it) and
writes an H.264 MP4, the terminal `transcript.json`, and optional PNG stills.

Examples:
    # One bundle; left pane reconstructed from ground truth (no camera footage):
    python3 scripts/render_demo_panel.py render \\
        --bundle data/logs/vm_runs/ib10_safety/runs/ib10S_e03_armA_a1 \\
        --out data/demo/ib10S_e03_armA_a1_panel.mp4 --stills

    # Same, with a real camera recording on the left (segments in order):
    python3 scripts/render_demo_panel.py render --bundle <bundle> \\
        --camera <bundle>/rec/annotated_000.mp4 <bundle>/rec/annotated_001.mp4 \\
        --camera-map <bundle>/rec/<frame_map>.json \\
        --camera-label "Camera: /perception/annotated_frame" \\
        --out data/demo/<label>_panel.mp4 --stills

    # Presentation profile (audience cut: staged, shortened terminal, captions
    # revealed with their events, zoom inset, intro/outro cards):
    python3 scripts/render_demo_panel.py render --profile presentation \\
        --script config/demo_presentation/<label>.json --bundle <bundle> \\
        --camera <bundle>/rec/annotated_000.mp4 ... --camera-map <map.json> \\
        --out data/demo/campaign/presentation/<label>_presentation.mp4 --stills

    # Combine finished per-scenario videos (JSON manifest, see docs/guides/demo_panel_video.md):
    python3 scripts/render_demo_panel.py combine --manifest <manifest.json> \\
        --out data/demo/<name>.mp4

    # Two bundles one after the other (e.g. VLM on, then Layer 2 off); per-bundle
    # footage with --camera-for <bundle index> <map.json> <segment> [<segment> ...]:
    python3 scripts/render_demo_panel.py sequence --bundle <on> --bundle <off> \\
        --camera-for 0 <on>/rec/<map>.json <on>/rec/annotated_000.mp4 \\
        --card "..." --card "..." --out data/demo/ib10_vlm_on_vs_off.mp4 --stills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from scripts.demo_panel.bundle import fallback_anchor_error, load_bundle  # noqa: E402
from scripts.demo_panel.combine import ManifestError, combine  # noqa: E402
from scripts.demo_panel.pipeline import (  # noqa: E402
    Prepared,
    compositor,
    prepare,
    prepare_present,
    render,
)
from scripts.demo_panel.present_render import (  # noqa: E402
    PresentCompositor,
    render_present,
    save_present_stills,
)
from scripts.demo_panel.presentation import load_script  # noqa: E402
from scripts.demo_panel.render import Compositor, Layout  # noqa: E402

FPS = 24.0


def still_times(p: Prepared) -> dict[str, float]:
    """Named video times for stills: mid model call, decision printed, dispatch, end."""
    tl, items = p.timeline, p.transcript.items
    out: dict[str, float] = {}
    for i, it in enumerate(items):
        if "starting analysis" in it.text and "call" not in out:
            nxt = tl.reveal[i + 1] if i + 1 < len(items) else tl.total_video_sec
            out["call"] = (tl.reveal[i] + nxt) / 2
        if it.kind == "output" and "decision" not in out and "provenance=" in it.text:
            out["decision"] = tl.reveal[i] + 1.5
        if "dispatch request=" in it.text and "dispatch" not in out:
            j = min(i + 8, len(items) - 1)
            out["dispatch"] = tl.reveal[j] + 0.2
        if "layer2=off" in it.text and "layer2_off" not in out:
            out["layer2_off"] = tl.reveal[i] + 1.0
    out["mid"] = tl.total_video_sec * 0.5
    out["end"] = tl.total_video_sec - 0.5
    return out


def save_stills(comp: Compositor, p: Prepared, out: Path) -> list[Path]:
    """Write PNG stills beside the video."""
    paths = []
    for name, t in still_times(p).items():
        path = out.with_name(f"{out.stem}_{name}.png")
        Image.fromarray(comp.frame(t)).save(path)
        paths.append(path)
    return paths


def _prepare(
    args: argparse.Namespace,
    bundle: Path,
    layout: Layout,
    fallback: float | None,
    camera: list[Path] | None,
    camera_map: Path | None,
) -> Prepared:
    return prepare(
        bundle, layout, camera, camera_map, fallback, font=args.font, camera_label=args.camera_label
    )


def _write_transcript(p: Prepared, out: Path) -> Path:
    path = out.with_name(f"{out.stem}_transcript.json")
    path.write_text(p.transcript.model_dump_json(indent=1))
    return path


def _combine(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    size = None
    if args.size:
        try:
            w, h = (int(v) for v in args.size.lower().split("x"))
        except ValueError:
            ap.error("--size must look like 1920x1080")
        size = (w, h)
    try:
        sidecar, dur = combine(
            args.manifest, args.out, args.fps, args.title_card_sec, size, args.font, args.crf
        )
    except (ManifestError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out} ({dur:.1f} s); sidecar {sidecar}")
    return 0


def _render_present(args: argparse.Namespace, ap: argparse.ArgumentParser) -> int:
    if args.script is None or not args.camera or args.camera_map is None:
        ap.error("--profile presentation needs --script, --camera and --camera-map")
    script = load_script(args.script)
    p = prepare_present(args.bundle, args.camera, args.camera_map, font=args.font)
    comp = PresentCompositor(p.pt, p.timeline, p.scene, p.pane, script)
    dur = render_present(comp, args.out, FPS, args.crf)
    path = args.out.with_name(f"{args.out.stem}_transcript.json")
    path.write_text(p.pt.model_dump_json(indent=1))
    print(f"wrote {args.out} ({dur:.1f} s); transcript {path}")
    print(f"time map: {p.tc.info.note}")
    if args.stills:
        for still in save_present_stills(comp, args.out, script.key_request):
            print(f"still {still}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="one bundle -> one MP4")
    r.add_argument("--bundle", type=Path, required=True)
    r.add_argument("--camera", type=Path, nargs="+", help="camera clip segment(s), in order")
    r.add_argument("--camera-map", type=Path, help="frame-to-sim JSON for --camera")
    r.add_argument(
        "--caption",
        action="append",
        default=[],
        help="extra caption line under the scene pane (repeatable: outcome, take, model)",
    )
    r.add_argument(
        "--profile",
        choices=("engineering", "presentation"),
        default="engineering",
        help="engineering (default, unchanged) or presentation (audience cut; needs --script)",
    )
    r.add_argument("--script", type=Path, help="presentation script JSON (captions, cards, zoom)")
    s = sub.add_parser("sequence", help="several bundles, one after the other, with caption cards")
    s.add_argument("--bundle", type=Path, action="append", required=True)
    s.add_argument(
        "--card", action="append", default=[], help="caption card shown before each bundle"
    )
    s.add_argument(
        "--calibrate-on",
        type=Path,
        help="bundle with sim-stamped log lines used to measure the fallback anchor's error",
    )
    s.add_argument(
        "--camera-for",
        nargs="+",
        action="append",
        default=[],
        metavar="ARG",
        help="INDEX MAP_JSON SEGMENT [SEGMENT ...]: camera footage for the INDEX-th --bundle",
    )
    c = sub.add_parser("combine", help="per-scenario videos -> one combined video (JSON manifest)")
    c.add_argument("--manifest", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--title-card-sec", type=float, default=3.0)
    c.add_argument("--fps", type=float, default=FPS)
    c.add_argument("--size", help="content area WxH (default: largest source)")
    c.add_argument("--font", help="monospace font file name or path")
    c.add_argument("--crf", type=int, default=23)
    for p in (r, s):
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--stills", action="store_true")
        p.add_argument("--font", help="monospace font file name or path")
        p.add_argument("--crf", type=int, default=23)
        p.add_argument("--camera-label", default="Camera recording", help="caption for footage")
    args = ap.parse_args(argv)
    if args.cmd == "combine":
        return _combine(args, ap)
    layout = Layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.cmd == "render" and args.profile == "presentation":
        return _render_present(args, ap)
    if args.cmd == "render":
        p = _prepare(args, args.bundle, layout, None, args.camera, args.camera_map)
        comp = compositor(p, layout, args.font, args.caption)
        dur = render([comp], args.out, FPS, layout, args.font, args.crf)
        print(f"wrote {args.out} ({dur:.1f} s); transcript {_write_transcript(p, args.out)}")
        print(f"time map: {p.tc.info.note}")
        if args.stills:
            for path in save_stills(comp, p, args.out):
                print(f"still {path}")
        return 0

    footage: dict[int, tuple[Path, list[Path]]] = {}
    for spec in args.camera_for:
        if len(spec) < 3:
            ap.error("--camera-for needs INDEX MAP_JSON SEGMENT [SEGMENT ...]")
        footage[int(spec[0])] = (Path(spec[1]), [Path(x) for x in spec[2:]])
    fallback = fallback_anchor_error(load_bundle(args.calibrate_on)) if args.calibrate_on else None
    clips: list = []
    for i, bundle in enumerate(args.bundle):
        cmap, segs = footage.get(i, (None, None))
        p = _prepare(args, bundle, layout, fallback, segs, cmap)
        comp = compositor(p, layout, args.font)
        if i < len(args.card):
            clips.append(([ln for ln in args.card[i].split("\\n")], 5.0))
        clips.append(comp)
        stem = args.out.with_name(f"{args.out.stem}_{p.bundle.name}")
        print(f"{p.bundle.name}: {p.timeline.total_video_sec:.1f} s; time map: {p.tc.info.note}")
        print(f"transcript {_write_transcript(p, stem.with_suffix('.mp4'))}")
        if args.stills:
            for path in save_stills(comp, p, stem.with_suffix(".mp4")):
                print(f"still {path}")
    dur = render(clips, args.out, FPS, layout, args.font, args.crf)
    print(f"wrote {args.out} ({dur:.1f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
