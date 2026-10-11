"""PILOT (exploratory, non-confirmatory): shared helpers for the V-JEPA 2 probe pilot.

Frame sources (battery-v2 harvest snapshots and in-bundle `annotated_*.mp4`
recordings), burned-in clock OCR for the recordings, GT projection through the
M1 calibration, clip assembly at a fixed 0.5 sim-s spacing, and the clock-region
mask applied to every frame from every source.
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_left
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from reasoning.vlm.capability_probes import dynamics as dyn  # noqa: E402

MAIN_CHECKOUT = Path("/Users/tuanhdangdinh/Documents/vgu-vlm-swarm")
LOGS_ROOT = MAIN_CHECKOUT / "data" / "logs" / "vm_runs"
BATTERY_RESULTS = MAIN_CHECKOUT / "data" / "logs" / "capability_probes" / "battery_v2_20261004"
OUT_ROOT = REPO / "data" / "logs" / "vjepa_pilot_20261011"
MANIFEST_V2 = REPO / "reasoning" / "vlm" / "capability_probes" / "manifest_v2.json"
CALIBRATION = REPO / "ros2_ws" / "src" / "swarm_perception" / "config" / "calibration.yaml"

CLIP_FRAMES = 8
CLIP_SPACING_SEC = 0.5
END_TOL_SEC = 0.15
# 8 consecutive harvest snapshots normally span 3.5-4.5 s.
MAX_SNAPSHOT_SPAN_SEC = 6.0
# Burned-in recorder clock ("t=...s  f=N", top-left). Masked on EVERY frame
# from every source so absolute sim time cannot leak into the encoder and the
# snapshot and recording domains match.
CLOCK_MASK = (0, 0, 340, 48)  # x0, y0, x1, y1
FRAME_W, FRAME_H = 1280, 960


def load_homography() -> np.ndarray:
    """Return the M1 pixel-to-world homography from the calibration YAML."""
    data = yaml.safe_load(CALIBRATION.read_text())
    return np.asarray(data["homography"], dtype=np.float64)


H_PIX2WORLD = load_homography()
H_WORLD2PIX = np.linalg.inv(H_PIX2WORLD)


def world_to_pixel(x: float, y: float) -> tuple[float, float]:
    """Project a world point (m) to float pixel coordinates `(u, v)`."""
    uvw = H_WORLD2PIX @ np.array([x, y, 1.0])
    return float(uvw[0] / uvw[2]), float(uvw[1] / uvw[2])


def mask_clock(bgr: np.ndarray) -> np.ndarray:
    """Black out the recorder-clock region in place and return the frame."""
    x0, y0, x1, y1 = CLOCK_MASK
    bgr[y0:y1, x0:x1] = 0
    return bgr


def _yellow_mask(bgr: np.ndarray, h: int = 50, w: int = 640) -> np.ndarray:
    roi = bgr[:h, :w].astype(np.int16)
    b, g, r = roi[..., 0], roi[..., 1], roi[..., 2]
    return (r > 140) & (g > 140) & (b < 110)


def _segments(mask: np.ndarray) -> list[tuple[int, int, int, int]]:
    cols = mask.any(0)
    out = []
    x, w = 0, mask.shape[1]
    while x < w:
        if cols[x]:
            x0 = x
            while x < w and cols[x]:
                x += 1
            ys = np.where(mask[:, x0:x].any(1))[0]
            out.append((x0, x, int(ys.min()), int(ys.max()) + 1))
        else:
            x += 1
    return out


def _glyph_vec(mask: np.ndarray, seg: tuple[int, int, int, int]) -> np.ndarray:
    x0, x1, _, _ = seg
    crop = mask[12:38, x0:x1].astype(np.float32)
    vec = cv2.resize(crop, (12, 20), interpolation=cv2.INTER_AREA).ravel()
    return np.concatenate([vec, [(x1 - x0) / 4.0]])


def _split_fields(segs):
    """Split clock glyph segments into the `t` digits and the `f` digits."""
    if len(segs) < 8:
        return None
    gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
    s_idx = int(np.argmax(gaps))  # widest gap follows the 's' of the t field
    t_digits = segs[2:s_idx]  # skip 't' and '='
    f_digits = segs[s_idx + 3 :]  # skip 'f' and '='
    return t_digits, f_digits


class ClockOCR:
    """Template OCR for the recorder's burned-in clock.

    The Mac OpenCV build renders Hershey glyphs differently from the VM's,
    so templates are harvested from the video itself: the `f=` field is the
    recorder's running frame count, so its digits are known per frame.
    """

    def __init__(self) -> None:
        self.templates: dict[str, list[np.ndarray]] = {}

    def learn(self, bgr: np.ndarray, frame_count: int) -> None:
        mask = _yellow_mask(bgr)
        fields = _split_fields(_segments(mask))
        if fields is None:
            return
        _, f_digits = fields
        text = str(frame_count)
        if len(f_digits) != len(text):
            return
        for seg, ch in zip(f_digits, text):
            bucket = self.templates.setdefault(ch, [])
            if len(bucket) < 12:
                bucket.append(_glyph_vec(mask, seg))

    def ready(self) -> bool:
        return all(len(self.templates.get(str(d), [])) >= 2 for d in range(10))

    def _classify(self, mask, seg) -> str:
        if seg[3] - seg[2] < 9:
            return "."
        v = _glyph_vec(mask, seg)
        best, best_d = "?", 1e9
        for ch, vecs in self.templates.items():
            d = min(float(np.abs(v - t).sum()) for t in vecs)
            if d < best_d:
                best, best_d = ch, d
        return best

    def read(self, bgr: np.ndarray) -> tuple[float | None, int | None]:
        """Return `(t_sec, f_count)` read from one frame, None where unreadable."""
        mask = _yellow_mask(bgr)
        fields = _split_fields(_segments(mask))
        if fields is None:
            return None, None
        t_digits, f_digits = fields
        t_txt = "".join(self._classify(mask, s) for s in t_digits)
        f_txt = "".join(self._classify(mask, s) for s in f_digits)
        try:
            t = float(t_txt) if re.fullmatch(r"\d+\.\d\d", t_txt) else None
        except ValueError:
            t = None
        f = int(f_txt) if f_txt.isdigit() else None
        return t, f


def video_segments(bundle_dir: Path) -> list[Path]:
    """Return a bundle's `annotated_NNN.mp4` segments in recording order."""
    for d in (bundle_dir, bundle_dir / "fc_run"):
        segs = sorted(d.glob("annotated_[0-9][0-9][0-9].mp4"))
        if segs:
            return segs
    return []


def ocr_timeline(segments: list[Path]) -> dict:
    """OCR every frame of a recording; return per-frame stamps and checks.

    Returns:
        Dict with `frames` (list of `[segment_index, frame_index, t, f]`) and
        validation counters (f-field self-consistency, monotonicity).
    """
    ocr = ClockOCR()
    # Pass 1: learn digit templates from the f field of the first segment.
    count = 0
    cap = cv2.VideoCapture(str(segments[0]))
    while not ocr.ready():
        ok, frame = cap.read()
        if not ok:
            break
        count += 1
        ocr.learn(frame, count)
    cap.release()
    frames, f_ok, f_bad, t_none = [], 0, 0, 0
    count = 0
    for si, seg in enumerate(segments):
        cap = cv2.VideoCapture(str(seg))
        fi = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
            t, f = ocr.read(frame)
            if f == count:
                f_ok += 1
            else:
                f_bad += 1
            if t is None:
                t_none += 1
            frames.append([si, fi, t, f])
            fi += 1
        cap.release()
    ts = [fr[2] for fr in frames if fr[2] is not None]
    nonmono = sum(1 for a, b in zip(ts, ts[1:]) if b < a)
    return {
        "segments": [str(s) for s in segments],
        "frames": frames,
        "n_frames": len(frames),
        "f_field_ok": f_ok,
        "f_field_bad": f_bad,
        "t_unreadable": t_none,
        "t_non_monotonic_steps": nonmono,
        "templates_ready": ocr.ready(),
    }


@dataclass
class FrameIndex:
    """Sim-time index over one episode's frames (snapshots or a recording)."""

    kind: str  # "snapshot" | "video"
    times: list[float]
    refs: list  # snapshot Path, or (segment_index, frame_index)
    segments: list[Path] = field(default_factory=list)
    _cache: dict = field(default_factory=dict)

    def nearest(self, t: float) -> tuple[int, float]:
        i = bisect_left(self.times, t)
        best = min(
            (j for j in (i - 1, i) if 0 <= j < len(self.times)),
            key=lambda j: abs(self.times[j] - t),
        )
        return best, abs(self.times[best] - t)


def snapshot_index(snap_dir: Path) -> FrameIndex:
    """Index harvest snapshots by the stamp in their file name."""
    items = []
    for p in snap_dir.glob("annotated_*.png"):
        m = re.match(r"annotated_(\d+\.\d+)\.png", p.name)
        if m:
            items.append((float(m.group(1)), p))
    items.sort()
    return FrameIndex("snapshot", [t for t, _ in items], [p for _, p in items])


def video_index(timeline: dict) -> FrameIndex:
    """Index a recording's OCR'd frames, keeping the first frame per stamp.

    A stamp is kept only when it agrees (within 1 s) with the median of its
    +/-4 neighbours, so a single misread digit cannot enter the index or
    block the monotone sequence after it.
    """
    frames = timeline["frames"]
    raw = [fr[2] for fr in frames]
    seen, times, refs = set(), [], []
    for k, (si, fi, t, _) in enumerate(frames):
        if t is None or t in seen:
            continue
        neigh = [x for x in raw[max(0, k - 4) : k + 5] if x is not None]
        if abs(t - float(np.median(neigh))) > 1.0:
            continue
        if times and t < times[-1]:
            continue
        seen.add(t)
        times.append(t)
        refs.append((si, fi))
    return FrameIndex("video", times, refs, [Path(s) for s in timeline["segments"]])


def clip_times(t_end: float, gaps: list[float] | None = None) -> list[float]:
    """Return the 16 target stamps of a clip ending at `t_end`.

    `gaps` (15 values, oldest last) sets the spacing between successive
    frames; default is a fixed `CLIP_SPACING_SEC`.
    """
    gaps = gaps or [CLIP_SPACING_SEC] * (CLIP_FRAMES - 1)
    out = [t_end]
    for g in gaps:
        out.append(out[-1] - g)
    return out[::-1]


def match_clip(
    index: FrameIndex, t_end: float, tol: float, spacing: float = CLIP_SPACING_SEC
) -> list[int] | None:
    """Return frame positions for a clip ending at `t_end`, or None if not covered.

    Snapshot episodes take the CLIP_FRAMES consecutive snapshots ending at the
    one nearest `t_end` (the harvest grabber's real spacing is 0.5-0.6 sim-s,
    occasionally more; the span is capped at MAX_SNAPSHOT_SPAN_SEC).
    Recordings take, for targets `spacing` apart, the nearest frame within
    `tol`; a frame may repeat across a recorder hole. The last frame must
    lie within END_TOL_SEC of `t_end`.
    """
    if index.kind == "snapshot":
        j, err = index.nearest(t_end)
        if err > END_TOL_SEC or j < CLIP_FRAMES - 1:
            return None
        frames = list(range(j - CLIP_FRAMES + 1, j + 1))
        if index.times[frames[-1]] - index.times[frames[0]] > MAX_SNAPSHOT_SPAN_SEC:
            return None
        return frames
    out = []
    for k in range(CLIP_FRAMES - 1, -1, -1):
        j, err = index.nearest(t_end - spacing * k)
        if err > tol:
            return None
        out.append(j)
    if abs(index.times[out[-1]] - t_end) > END_TOL_SEC:
        return None
    return out


class FrameLoader:
    """Load masked BGR frames by FrameIndex position, decoding videos sequentially."""

    def __init__(self, index: FrameIndex) -> None:
        self.index = index
        self._cap = None
        self._cap_seg = None
        self._pos = -1

    def get(self, j: int) -> np.ndarray:
        ref = self.index.refs[j]
        if self.index.kind == "snapshot":
            img = cv2.imread(str(ref))
            return mask_clock(img)
        si, fi = ref
        if self._cap is None or self._cap_seg != si or fi <= self._pos:
            if self._cap is not None:
                self._cap.release()
            self._cap = cv2.VideoCapture(str(self.index.segments[si]))
            self._cap_seg, self._pos = si, -1
            if fi > 0:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                self._pos = fi - 1
        frame = None
        while self._pos < fi:
            ok, frame = self._cap.read()
            if not ok:
                raise RuntimeError(f"decode failed at segment {si} frame {fi}")
            self._pos += 1
        return mask_clock(frame)


def load_gt(bundle_dir: Path) -> dyn.GtTrack:
    """Load a bundle's GT log into a GtTrack."""
    rows = [json.loads(l) for l in (bundle_dir / "gt" / "ground_truth.jsonl").open() if l.strip()]
    return dyn.GtTrack(rows)


def square_crop(bgr: np.ndarray, cx: float, cy: float, side: int, out: int = 256) -> np.ndarray:
    """Return an `out`x`out` RGB crop of side `side` px centred at `(cx, cy)`, zero-padded."""
    half = side / 2.0
    x0, y0 = int(round(cx - half)), int(round(cy - half))
    canvas = np.zeros((side, side, 3), dtype=np.uint8)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(bgr.shape[1], x0 + side), min(bgr.shape[0], y0 + side)
    if sx1 > sx0 and sy1 > sy0:
        canvas[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = bgr[sy0:sy1, sx0:sx1]
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    return cv2.resize(rgb, (out, out), interpolation=cv2.INTER_AREA)
