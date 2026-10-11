"""PILOT (exploratory, non-confirmatory): inventory frame+GT episodes for the V-JEPA 2 probe.

For every bundle under the main checkout's `data/logs/vm_runs` with GT and
either harvest snapshots or an in-bundle `annotated_*.mp4` recording:

- OCR the recording's burned-in clock (cached under OUT_ROOT/timelines);
- check the OCR (f-field self-consistency, monotonic t, first t vs rec.log);
- check GT-to-pixel geometry (projected GT robot centres land on drawn boxes);
- read scenario/seed from CONDITION.txt.

Writes OUT_ROOT/inventory.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402


def condition_fields(bundle: Path) -> dict[str, str]:
    p = bundle / "CONDITION.txt"
    if not p.is_file():
        return {}
    return dict(re.findall(r"(\w+)=(\S+)", p.read_text()))


def rec_first_stamp(bundle: Path) -> float | None:
    p = bundle / "rec.log"
    if not p.is_file():
        return None
    m = re.search(r"header_stamp=([\d.]+)", p.read_text(errors="replace"))
    return float(m.group(1)) if m else None


def box_hit_rate(index: c.FrameIndex, track, n_probe: int = 6) -> dict:
    """Fraction of projected GT robot centres with a saturated (status-coloured) box nearby.

    Compared with the same statistic at random offsets, to show the
    projection, not chance, explains the hit.
    """
    loader = c.FrameLoader(index)
    picks = np.linspace(len(index.times) * 0.2, len(index.times) * 0.9, n_probe).astype(int)
    hits = tot = rnd_hits = rnd_tot = 0
    rng = np.random.default_rng(0)
    for j in picks:
        t = index.times[j]
        row = track.row_near(t, tolerance=0.1)
        if row is None:
            continue
        img = loader.get(int(j))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat = (hsv[..., 1] > 120) & (hsv[..., 2] > 100)
        for r in row["robots"].values():
            u, v = c.world_to_pixel(r["x"], r["y"])
            for target, is_rnd in (((u, v), False), ((u + rng.uniform(150, 300), v + rng.uniform(-200, 200)), True)):
                uu, vv = int(target[0]), int(target[1])
                if not (35 <= uu < c.FRAME_W - 35 and 35 <= vv < c.FRAME_H - 35):
                    continue
                win = sat[vv - 32 : vv + 32, uu - 32 : uu + 32]
                hit = win.sum() > 40
                if is_rnd:
                    rnd_hits += hit
                    rnd_tot += 1
                else:
                    hits += hit
                    tot += 1
    return {
        "hit": hits,
        "n": tot,
        "rate": hits / tot if tot else None,
        "random_rate": rnd_hits / rnd_tot if rnd_tot else None,
    }


def main() -> None:
    c.OUT_ROOT.mkdir(parents=True, exist_ok=True)
    tl_dir = c.OUT_ROOT / "timelines"
    tl_dir.mkdir(exist_ok=True)
    bundles = set()
    for p in c.LOGS_ROOT.rglob("annotated_[0-9][0-9][0-9].mp4"):
        b = p.parent.parent if p.parent.name == "fc_run" else p.parent
        bundles.add(b)
    for p in (c.LOGS_ROOT / "battery_v2_harvest").glob("b2_*"):
        bundles.add(p)
    rows = []
    for b in sorted(bundles):
        rel = str(b.relative_to(c.LOGS_ROOT))
        rec = {"run_id": rel, "condition": condition_fields(b)}
        if not (b / "gt" / "ground_truth.jsonl").is_file():
            rec["usable"], rec["reason"] = False, "no_gt"
            rows.append(rec)
            continue
        if "_aborted" in rel or "_discarded" in rel:
            rec["usable"], rec["reason"] = False, "aborted_or_discarded_run"
            rows.append(rec)
            continue
        track = c.load_gt(b)
        rec["gt_span"] = [track.times[0], track.times[-1]]
        snap = b / "snapshots"
        if snap.is_dir():
            index = c.snapshot_index(snap)
            rec["source"] = "snapshot"
        else:
            segs = c.video_segments(b)
            cap = cv2.VideoCapture(str(segs[0]))
            nframes = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            ok, _ = cap.read()
            cap.release()
            if not ok or nframes <= 0:
                rec["usable"], rec["reason"] = False, "video_unreadable_truncated"
                rows.append(rec)
                continue
            cache = tl_dir / (rel.replace("/", "__") + ".json")
            if cache.is_file():
                tl = json.loads(cache.read_text())
            else:
                tl = c.ocr_timeline(segs)
                cache.write_text(json.dumps(tl))
            rec["source"] = "video"
            rec["ocr"] = {k: v for k, v in tl.items() if k not in ("frames", "segments")}
            rec["rec_first_stamp"] = rec_first_stamp(b)
            index = c.video_index(tl)
            rec["ocr"]["first_t"] = index.times[0] if index.times else None
        if len(index.times) < c.CLIP_FRAMES:
            rec["usable"], rec["reason"] = False, "too_few_frames"
            rows.append(rec)
            continue
        rec["frame_span"] = [index.times[0], index.times[-1]]
        rec["n_indexed_frames"] = len(index.times)
        gaps = np.diff(index.times)
        rec["median_frame_gap_sec"] = float(np.median(gaps))
        rec["geometry"] = box_hit_rate(index, track)
        rec["robots"] = sorted(track.rows[0]["robots"])
        rec["usable"] = True
        rows.append(rec)
        print(rel, rec.get("source"), rec["frame_span"], rec["geometry"], rec.get("ocr", {}).get("f_field_bad"), flush=True)
    (c.OUT_ROOT / "inventory.json").write_text(json.dumps(rows, indent=1, default=float))


if __name__ == "__main__":
    main()
