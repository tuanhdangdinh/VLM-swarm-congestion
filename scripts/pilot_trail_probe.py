#!/usr/bin/env python3
"""PILOT (exploratory, excluded from confirmatory counts): trails-on re-run of battery-v2 main items.

Builds a trails-on twin of every frozen battery-v2 `main` frame OFFLINE, by
compositing M1's own `draw_motion_trails` onto the recorded (frozen,
SHA-verified) annotated frame, then asks the same frozen v1 probe prompt
with only the image swapped. See docs/reports/2026-10-06-trail-on-pilot.md.

Composition (the live M1 order is: trails blended on the raw frame, robot
footprints restored, robot overlays drawn on top):
    out = recorded.copy(); draw_motion_trails(out, history, robots, cal)
    out[footprint | overlay_pixels] = recorded[...]
Exact everywhere except anti-aliased overlay fringe pixels a trail passes
under (counted per item as `aa_fringe_px`).

Subcommands:
    render    build trails-on frames + per-item fidelity metrics (no API)
    validate  replay the trail logic against the recorded live trails-on
              harvest runs (b2_headon_on / b2_convoy_on) and report IoU
    run       call one backend on one arm (`on` = composited frames, `off` =
              the frozen frames, same-day retest)

Keys come from the environment only (`set -a; source .env; set +a` in the
calling shell); nothing secret or base64 is ever written.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for extra in (REPO_ROOT / "ros2_ws" / "src" / "swarm_perception", REPO_ROOT, REPO_ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import swarm_perception.annotation as _annotation  # noqa: E402
from swarm_perception.annotation import (  # noqa: E402
    TrailHistory,
    _footprint_mask,
    draw_motion_trails,
    render_annotated_frame,
)
from swarm_perception.calibration import load_calibration  # noqa: E402
from swarm_perception.models import SceneState  # noqa: E402

CAL_PATH = REPO_ROOT / "ros2_ws/src/swarm_perception/config/calibration.yaml"
MANIFEST = REPO_ROOT / "reasoning/vlm/capability_probes/manifest_v2.json"
# Registered trail parameters (annotation.yaml).
TRAIL_KW = {"window_sec": 3.0, "min_step_sec": 0.1, "max_points": 40}
STAMP_EPS = 1e-4
# M1 positions come from marker-corner averages, so many robots project to
# exact half-pixel (u, v); `int(round(...))` then depends on the last ulp of
# inv(H) @ p, which differs between the VM's and this Mac's numpy/LAPACK.
# Ties are resolved per drawn point against the recorded frame (`_resolve_ties`)
# and applied through this override, which every drawing call here uses.
_TIE_OVERRIDE: dict[tuple[float, float], tuple[int, int]] = {}
_world_to_pixel_orig = _annotation.world_to_pixel


def _world_to_pixel(world_point, homography):
    key = (float(world_point[0]), float(world_point[1]))
    if key in _TIE_OVERRIDE:
        return _TIE_OVERRIDE[key]
    return _world_to_pixel_orig(world_point, homography)


_annotation.world_to_pixel = _world_to_pixel


def _tie_options(world_point, homography) -> list[tuple[int, int]]:
    uvw = np.linalg.inv(homography) @ np.array([world_point[0], world_point[1], 1.0])
    uvw /= uvw[2]
    axes = []
    for value in uvw[:2]:
        lo = int(np.floor(value))
        axes.append([lo, lo + 1] if abs(value - lo - 0.5) < 1e-6 else [int(round(float(value)))])
    return [(u, v) for u in axes[0] for v in axes[1]]


def _scene(raw: dict) -> SceneState:
    s = raw.get("scene", raw)
    robots = [
        {"angular_velocity": 0.0, "task": None, "goal": None, **r} for r in s["robots"]
    ]
    diagnostics = dict(s.get("diagnostics") or {})
    if "dropped_frame" in s:
        diagnostics.setdefault("dropped_frame", s["dropped_frame"])
    return SceneState(
        stamp=s["stamp"], frame_id=s.get("frame_id", "overhead_camera"), robots=robots,
        diagnostics=diagnostics,
    )


def _read_scenes(path: Path) -> list[SceneState]:
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(_scene(json.loads(line)))
    return out


def _snapshot_stamp(run_dir: Path, frame_ref: str) -> float:
    for line in (run_dir / "snapshots" / "frames.jsonl").read_text().splitlines():
        rec = json.loads(line)
        if rec["file"] == frame_ref:
            return rec["stamp_sec"] + rec["stamp_nanosec"] * 1e-9
    raise KeyError(frame_ref)


def _overlay_masks(shape, scene: SceneState, cal):
    black = np.zeros(shape, np.uint8)
    white = np.full(shape, 255, np.uint8)
    on_b = render_annotated_frame(black, scene, cal)
    on_w = render_annotated_frame(white, scene, cal)
    changed = np.any(on_b != 0, axis=2) | np.any(on_w != 255, axis=2)
    same = np.all(on_b == on_w, axis=2)
    opaque = changed & same
    return changed, opaque, changed & ~same, on_b


def _label_mask(shape, scene: SceneState, cal, pad: int = 2):
    # Robot-id labels are LINE_AA Hershey text, whose glyph rasterisation
    # differs between the VM's and this Mac's OpenCV builds, so label pixels
    # are compared and protected by their whole text rectangle.
    h, w = shape[:2]
    mask = np.zeros((h, w), bool)
    for robot in scene.robots:
        cx, cy = _world_to_pixel((robot.x, robot.y), cal.homography)
        (tw, th), base = cv2.getTextSize(robot.robot_id, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        x0, y0 = max(0, cx - 20), max(0, cy - 25)
        mask[max(0, y0 - th - pad):min(h, y0 + base + pad), max(0, x0 - pad):min(w, x0 + tw + pad)] = True
    return mask


def _opaque_match(recorded, scene, cal) -> tuple[float, int]:
    _, opaque, _, on_b = _overlay_masks(recorded.shape, scene, cal)
    opaque = opaque & ~_label_mask(recorded.shape, scene, cal)
    n = int(opaque.sum())
    if n == 0:
        return 1.0, 0
    return float(np.all(recorded[opaque] == on_b[opaque], axis=1).mean()), n


def _resolve_ties(recorded, scene: SceneState, cal) -> int:
    """Pick, per tied drawn point, the rounding the recorded frame shows; return #ties."""
    points = [(r.x, r.y) for r in scene.robots] + [r.goal for r in scene.robots if r.goal]
    n_ties = 0
    for point in points:
        key = (float(point[0]), float(point[1]))
        _TIE_OVERRIDE.pop(key, None)
        options = _tie_options(point, cal.homography)
        if len(options) == 1:
            continue
        n_ties += 1
        u0, v0 = options[0]
        window = (slice(max(0, v0 - 80), v0 + 80), slice(max(0, u0 - 80), u0 + 80))
        best = None
        for option in options:
            _TIE_OVERRIDE[key] = option
            _, opaque, _, on_b = _overlay_masks(recorded.shape, scene, cal)
            opaque = opaque & ~_label_mask(recorded.shape, scene, cal)
            sub = opaque[window]
            score = np.all(recorded[window][sub] == on_b[window][sub], axis=1).mean() if sub.any() else 0
            if best is None or score > best[0]:
                best = (score, option)
        _TIE_OVERRIDE[key] = best[1]
    return n_ties


def _without_goals(scene: SceneState) -> SceneState:
    return scene.model_copy(update={"robots": [r.model_copy(update={"goal": None}) for r in scene.robots]})


def item_sources(item: dict, logs_root: Path, recorded, cal):
    """Return (overlay_scene, history_scenes, quality, provenance) for one item."""
    run = logs_root / item["run_id"]
    if item["frame_source"] == "snapshot":
        stamp = _snapshot_stamp(run, item["frame_ref"])
        scenes = _read_scenes(run / "snapshots" / "scene_state.jsonl")
        hist = [s for s in scenes if s.stamp <= stamp + STAMP_EPS]
        exact = [s for s in scenes if abs(s.stamp - stamp) < STAMP_EPS]
        if len(exact) != 1:
            raise ValueError(f"{item['item_id']}: {len(exact)} exact-stamp states")
        _resolve_ties(recorded, exact[0], cal)
        return exact[0], hist, "exact", "snapshots/scene_state.jsonl (M1, every msg)"
    decision = json.loads((run / "decisions" / f"{item['frame_ref']}.json").read_text())
    dscene = _scene(decision["scene"])
    stamp = dscene.stamp
    full = run / "scene_full.jsonl"
    candidates = [("decision.scene", dscene), ("decision.scene-no-goals", _without_goals(dscene))]
    if full.is_file():
        scenes = _read_scenes(full)
        # M5 pairs the latest annotated frame with its scene within a skew
        # bound, so the drawing state may be a neighbouring M1 message.
        candidates = [
            (f"scene_full@{s.stamp - stamp:+.3f}s", s)
            for s in scenes if abs(s.stamp - stamp) <= 0.5 + STAMP_EPS
        ] + candidates
        quality, prov = "exact", "scene_full.jsonl (M1, every msg)"
    else:
        logs = sorted(run.glob("scene_*.jsonl")) or sorted(run.glob("m5_scene.jsonl"))
        if not logs:
            raise FileNotFoundError(f"{item['item_id']}: no scene history in {run}")
        scenes = _read_scenes(logs[0])
        hist = [s for s in scenes if s.stamp < stamp - STAMP_EPS] + [dscene]
        quality, prov = "approx", f"{logs[0].name} (M5 scene log, sparse) + decision.scene"
    scored = []
    for name, sc in candidates:
        _resolve_ties(recorded, sc, cal)
        scored.append((_opaque_match(recorded, sc, cal), name, sc))
    (match, _), name, best = max(scored, key=lambda t: t[0][0])
    _resolve_ties(recorded, best, cal)
    if full.is_file():
        hist = [s for s in scenes if s.stamp <= best.stamp + STAMP_EPS]
        if best is not hist[-1]:
            hist.append(best)
    # Trail colour / footprints come from the chosen overlay state; history
    # positions keep their own goals (goals never enter the trail).
    return best, hist, quality, f"{prov}; overlay state={name}"


def composite(recorded, overlay_scene, hist, cal):
    trails = TrailHistory(**TRAIL_KW)
    for s in hist:
        trails.update(s)
    changed, _opaque, aa, _ = _overlay_masks(recorded.shape, overlay_scene, cal)
    footprint = _footprint_mask(recorded.shape[:2], overlay_scene.robots, cal).astype(bool)
    out = recorded.copy()
    draw_motion_trails(out, trails, overlay_scene.robots, cal)
    trail_px = np.any(out != recorded, axis=2)
    labels = _label_mask(recorded.shape, overlay_scene, cal)
    keep = footprint | changed | labels
    out[keep] = recorded[keep]
    visible = np.any(out != recorded, axis=2)
    n_points = {r.robot_id: len(trails.points(r.robot_id)) for r in overlay_scene.robots}
    return out, {
        "trail_px_drawn": int(visible.sum()),
        "aa_fringe_px": int((trail_px & aa & ~labels).sum()),
        "label_rect_suppressed_px": int((trail_px & labels & ~changed).sum()),
        "trail_points": n_points,
    }


def _load_rgb(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def cmd_render(args) -> int:
    from reasoning.vlm.capability_probes.manifest_io import sha256_file

    cal = load_calibration(CAL_PATH)
    manifest = json.loads(MANIFEST.read_text())
    out_dir = args.out_dir / "frames_on"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in manifest["items"]:
        if item["subset"] != "main":
            continue
        src = args.logs_root / item["frame_relpath"]
        if sha256_file(src) != item["frame_sha256"]:
            raise ValueError(f"{item['item_id']}: frozen frame SHA drift")
        recorded = _load_rgb(src)
        overlay_scene, hist, quality, prov = item_sources(item, args.logs_root, recorded, cal)
        match, n_opaque = _opaque_match(recorded, overlay_scene, cal)
        out, stats = composite(recorded, overlay_scene, hist, cal)
        dest = out_dir / f"{item['item_id']}.png"
        cv2.imwrite(str(dest), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        # Round-trip: decoded composite equals what we built (lossless PNG).
        assert np.array_equal(_load_rgb(dest), out)
        rows.append({
            "item_id": item["item_id"], "probe_type": item["probe_type"],
            "quality": quality, "provenance": prov,
            "opaque_overlay_match": round(match, 4), "opaque_overlay_px": n_opaque,
            "frame_sha256_on": sha256_file(dest), **stats,
        })
        print(f"{item['item_id']} {quality} match={match:.4f}/{n_opaque} "
              f"trail_px={stats['trail_px_drawn']} fringe={stats['aa_fringe_px']} "
              f"pts={stats['trail_points']}", file=sys.stderr)
    (args.out_dir / "render_metrics.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows))
    return 0


def cmd_validate(args) -> int:
    """Replay trails for recorded live trails-on snapshots and compare chroma masks."""
    cal = load_calibration(CAL_PATH)
    rows = []
    for run_id in ("battery_v2_harvest/b2_headon_on", "battery_v2_harvest/b2_convoy_on"):
        run = args.logs_root / run_id
        scenes = _read_scenes(run / "snapshots" / "scene_state.jsonl")
        frames = [json.loads(x) for x in (run / "snapshots" / "frames.jsonl").read_text().splitlines()]
        # Static-floor background: per-pixel median over the run's snapshots
        # (robots and their trails are transient at any one pixel).
        background = np.median(np.stack([
            _load_rgb(run / "snapshots" / f["file"]) for f in frames[:: max(1, len(frames) // 120)]
        ]), axis=0).astype(np.int16)
        frames = frames[:: max(1, len(frames) // args.per_run)]
        for fr in frames:
            stamp = fr["stamp_sec"] + fr["stamp_nanosec"] * 1e-9
            exact = [s for s in scenes if abs(s.stamp - stamp) < STAMP_EPS]
            if len(exact) != 1:
                continue
            scene = exact[0]
            recorded_probe = _load_rgb(run / "snapshots" / fr["file"])
            _resolve_ties(recorded_probe, scene, cal)
            recorded = _load_rgb(run / "snapshots" / fr["file"])
            trails = TrailHistory(**TRAIL_KW)
            for s in scenes:
                if s.stamp > stamp + STAMP_EPS:
                    break
                trails.update(s)
            changed, _o, _aa, _ = _overlay_masks(recorded.shape, scene, cal)
            excl = changed | _label_mask(recorded.shape, scene, cal) | _footprint_mask(recorded.shape[:2], scene.robots, cal).astype(bool)
            predicted = background.astype(np.uint8).copy()
            draw_motion_trails(predicted, trails, scene.robots, cal)
            pred_delta = np.abs(predicted.astype(np.int16) - background).max(axis=2)
            mask = (pred_delta > args.chroma) & ~excl
            if mask.sum() < 20:
                continue
            rec16 = recorded.astype(np.int16)
            # Control: the same predicted trail displaced 4 px down; a correct
            # replay fits the live frame far better than its displaced copy or
            # than "no trail at all" (the background).
            shifted = np.roll(predicted, 4, axis=0).astype(np.int16)
            smask = np.roll(mask, 4, axis=0) & ~excl
            rows.append({
                "run": run_id, "file": fr["file"], "trail_px": int(mask.sum()),
                "mae_replay": float(np.abs(predicted.astype(np.int16) - rec16)[mask].mean()),
                "mae_no_trail": float(np.abs(background - rec16)[mask].mean()),
                "mae_shift4": float(np.abs(shifted - rec16)[smask].mean()),
            })
    def med(key):
        return float(np.median([r[key] for r in rows]))

    summary = {"frames_with_trails": len(rows), "median_mae_replay": med("mae_replay"),
               "median_mae_no_trail": med("mae_no_trail"), "median_mae_shift4": med("mae_shift4"),
               "frames_replay_beats_both": sum(
                   r["mae_replay"] < min(r["mae_no_trail"], r["mae_shift4"]) for r in rows),
               "delta_threshold": args.chroma}
    (args.out_dir / "validate_live_trails.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


def cmd_run(args) -> int:
    from capability_probes import load_backend_settings, run_item
    from reasoning.vlm.backend_factory import build_backend
    from reasoning.vlm.capability_probes.letters import build_item_choices
    from reasoning.vlm.capability_probes.manifest_io import load_any_manifest, materialize_frame, sha256_file
    from reasoning.vlm.capability_probes.prompt import build_capability_probe_prompt_payload
    from reasoning.vlm.capability_probes.scorer import score_records

    manifest = load_any_manifest(MANIFEST)
    metrics = {json.loads(x)["item_id"]: json.loads(x)
               for x in (args.out_dir / "render_metrics.jsonl").read_text().splitlines()}
    types = set(args.types.split(","))
    items = [i for i in manifest.items if i.subset == "main" and i.probe_type in types]
    prepared = []
    for item in items:
        frozen = materialize_frame(item, args.logs_root)  # SHA-verified
        choices = build_item_choices(item.options, item.correct_answer, item.seed)
        p_off = build_capability_probe_prompt_payload(
            question=item.question, choices=choices, image_path=str(frozen),
            image_choices=item.image_choices, known_robot_ids=[])
        if args.arm == "off":
            prepared.append((item, choices, p_off))
            continue
        on_path = args.out_dir / "frames_on" / f"{item.item_id}.png"
        if sha256_file(on_path) != metrics[item.item_id]["frame_sha256_on"]:
            raise ValueError(f"{item.item_id}: trails-on frame drifted since render")
        p_on = p_off.model_copy(update={"image_path": str(on_path)})
        a, b = p_off.model_dump(), p_on.model_dump()
        a.pop("image_path"), b.pop("image_path")
        assert a == b, f"{item.item_id}: prompt differs beyond the image"
        prepared.append((item, choices, p_on))

    config, backend_config = load_backend_settings(args.backend)
    backend = build_backend(args.backend, backend_config)
    model_id = getattr(backend_config, "model_id", None)
    run_dir = args.out_dir / f"{args.backend}__{args.arm}"
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    records, next_start = [], 0.0
    for item, choices, payload in prepared:
        delay = next_start - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        next_start = time.monotonic() + args.min_interval_sec
        rec = run_item(item, choices, payload, backend, config, model_id)
        records.append(rec)
        print(f"{rec.item_id} cause={rec.failure_cause or 'none'} correct={rec.correct}",
              file=sys.stderr)
        if rec.failure_cause == "backend_error":
            print(f"  error_type={rec.error_type}", file=sys.stderr)
    (run_dir / f"{args.backend}_{stamp}.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in records))
    summary = score_records(records, {i.item_id: 1.0 / len(i.options) for i in items},
                            args.backend, manifest.seed)
    usage = Counter()
    for r in records:
        for k, v in (r.token_usage or {}).items():
            if isinstance(v, (int, float)):
                usage[k] += v
    out = {"pilot": True, "arm": args.arm, "types": sorted(types), "n": len(records),
           "token_usage_total": dict(usage), **summary.model_dump(mode="json")}
    (run_dir / f"{args.backend}_{stamp}_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("arm", "n", "token_usage_total")}), file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("render", "validate", "run"):
        p = sub.add_parser(name)
        p.add_argument("--logs-root", type=Path, required=True)
        p.add_argument("--out-dir", type=Path, required=True)
        if name == "validate":
            p.add_argument("--per-run", type=int, default=60)
            p.add_argument("--chroma", type=int, default=20)
        if name == "run":
            p.add_argument("--backend", required=True, choices=["openai", "gemini"])
            p.add_argument("--arm", required=True, choices=["on", "off"])
            p.add_argument("--types", default="motion_direction,conflict_prediction,temporal_order")
            p.add_argument("--min-interval-sec", type=float, default=3.0)
    args = parser.parse_args()
    return {"render": cmd_render, "validate": cmd_validate, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
