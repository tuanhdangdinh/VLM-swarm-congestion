"""PILOT (exploratory, non-confirmatory): frozen V-JEPA 2 features for the probe clips.

Encoder: `facebook/vjepa2-vitl-fpc64-256` (ViT-L/16, 300M params, MIT), frozen,
fp32 on MPS. Input: 8 frames x 256x256 RGB, ImageNet mean/std, giving
4 (tubelet 2) x 16 x 16 tokens of width 1024 from `get_vision_features`.

Crops (clock region masked first, zero-padded outside the frame):

- conflict: square of side 960 px centred on the pair midpoint at `t_end`;
- temporal robot: square of side 480 px centred on the robot at `t_end`.

Pooled and saved per clip (fp16), never the raw tokens:

- `g`: mean over all tokens (1024);
- `gt`: per-tubelet mean (4 x 1024);
- `ra` / `rb` (conflict) or `ra` (temporal): per-tubelet mean of the 3x3
  patch neighbourhood at the robot's GT-projected position in that tubelet's
  second frame (4 x 1024 each).

Two variants per clip: `dyn` (the real clip) and `static` (the last frame
repeated 8 times; the single-frame control that sees what a one-image VLM
sees, minus the text prompt).

Writes OUT_ROOT/features/<variant>.npz plus OUT_ROOT/features/index.json.
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c  # noqa: E402

HF_ID = "facebook/vjepa2-vitl-fpc64-256"
RES = 256
PATCH = 16
GRID = RES // PATCH
CROP = {"conflict": 960, "temporal_robot": 480}
HALF = 0.5  # frames cached at half resolution to bound memory
TEMPORAL_STRIDE = {"train": 2, "test": 3}  # keep every Nth whole-second t_end per episode
BATCH = 4
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def select_samples(ds: dict) -> list[dict]:
    """All conflict and battery samples; temporal robot samples thinned by whole-t_end stride."""
    out = []
    for s in ds["samples"]:
        if s["task"] == "conflict":
            out.append(s)
        elif s["task"] == "temporal_robot":
            if int(round(s["t_end"])) % TEMPORAL_STRIDE[s["role"]] == 0:
                out.append(s)
    # Battery-rule temporal pairs: one robot sample per pair member at the pair's t_end.
    for s in ds["samples"]:
        if s["task"] == "temporal_pair":
            for rid in s["pair"]:
                out.append({**s, "task": "temporal_robot", "robot": rid, "from_pair": True})
    for b in ds["battery"]:
        if not b.get("mappable"):
            continue
        if b["probe_type"] == "conflict_prediction":
            out.append({**b, "task": "conflict", "pair": b["pair"]})
        else:
            for rid in b["pair"]:
                out.append({**b, "task": "temporal_robot", "robot": rid})
    for i, s in enumerate(out):
        s["uid"] = i
    return out


class EpisodeFrames:
    """Half-resolution masked frames of one episode, decoded forward-only with eviction."""

    def __init__(self, index: c.FrameIndex) -> None:
        self.index = index
        self.loader = c.FrameLoader(index)
        self.cache: dict[int, np.ndarray] = {}

    def get(self, j: int) -> np.ndarray:
        if j not in self.cache:
            full = self.loader.get(j)
            self.cache[j] = cv2.resize(full, None, fx=HALF, fy=HALF, interpolation=cv2.INTER_AREA)
        return self.cache[j]

    def evict_before(self, t: float) -> None:
        for j in [j for j in self.cache if self.index.times[j] < t]:
            del self.cache[j]


def crop_half(img_half: np.ndarray, cx: float, cy: float, side: int) -> np.ndarray:
    """Crop at half resolution with full-resolution centre/side; return 256x256 RGB."""
    return c.square_crop(img_half, cx * HALF, cy * HALF, int(round(side * HALF)), RES)


def patch_of(u: float, v: float, cx: float, cy: float, side: int) -> tuple[int, int]:
    """Patch (row, col) of full-res pixel (u, v) inside a crop centred at (cx, cy)."""
    x = (u - (cx - side / 2.0)) * RES / side
    y = (v - (cy - side / 2.0)) * RES / side
    col = int(np.clip(np.floor(x / PATCH), 0, GRID - 1))
    row = int(np.clip(np.floor(y / PATCH), 0, GRID - 1))
    return row, col


def robot_px(track, rid: str, t: float) -> tuple[float, float]:
    row = track.row_near(t, tolerance=0.2)
    if row is None or rid not in row["robots"]:
        row = track.row_near(t, tolerance=1.0)
    r = row["robots"][rid]
    return c.world_to_pixel(r["x"], r["y"])


def build_clip(sample: dict, frames: EpisodeFrames, track) -> tuple[np.ndarray, np.ndarray, list]:
    """Return (dyn clip, static clip) as (8,3,256,256) float32, and per-robot tubelet patches."""
    t_end = sample["t_end"]
    side = CROP[sample["task"]]
    robots = sample["pair"] if sample["task"] == "conflict" else [sample["robot"]]
    pts = [robot_px(track, rid, t_end) for rid in robots]
    cx = float(np.mean([p[0] for p in pts]))
    cy = float(np.mean([p[1] for p in pts]))
    imgs = [crop_half(frames.get(j), cx, cy, side) for j in sample["frames"]]
    times = [frames.index.times[j] for j in sample["frames"]]
    patches = []
    for rid in robots:
        per_tub = []
        for k in range(len(imgs) // 2):
            u, v = robot_px(track, rid, times[2 * k + 1])
            per_tub.append(patch_of(u, v, cx, cy, side))
        patches.append(per_tub)
    arr = (np.stack(imgs).astype(np.float32) / 255.0 - MEAN) / STD
    arr = arr.transpose(0, 3, 1, 2)
    static = np.repeat(arr[-1:], len(imgs), axis=0)
    return arr, static, patches


def pool(tokens: torch.Tensor, patches: list) -> dict[str, np.ndarray]:
    """Pool (T'*16*16, D) tokens into the saved summaries."""
    d = tokens.shape[-1]
    grid = tokens.reshape(-1, GRID, GRID, d)
    out = {"g": grid.mean(dim=(0, 1, 2)), "gt": grid.mean(dim=(1, 2))}
    for name, per_tub in zip(("ra", "rb"), patches):
        vecs = []
        for k, (r, col) in enumerate(per_tub):
            r0, r1 = max(0, r - 1), min(GRID, r + 2)
            c0, c1 = max(0, col - 1), min(GRID, col + 2)
            vecs.append(grid[k, r0:r1, c0:c1].mean(dim=(0, 1)))
        out[name] = torch.stack(vecs)
    return {k: v.float().cpu().numpy().astype(np.float16) for k, v in out.items()}


VARIANTS = ("dyn", "static")


def pool_patches(variant: str, patches: list) -> list:
    """Robot pooling positions per tubelet for a variant.

    The static clip shows only the last frame, so it pools every tubelet at
    the robot's last-frame position. Pooling it at the GT trajectory (the
    Rev 1 bug, fixed 2026-10-11) leaked motion into the "static" control via
    where the pool was taken.
    """
    if variant == "static":
        return [[per_tub[-1]] * len(per_tub) for per_tub in patches]
    return patches


def main() -> None:
    from transformers import AutoModel

    ds = json.loads((c.OUT_ROOT / "dataset.json").read_text())
    samples = select_samples(ds)
    inv = {r["run_id"]: r for r in json.loads((c.OUT_ROOT / "inventory.json").read_text())}
    feat_dir = c.OUT_ROOT / "features"
    feat_dir.mkdir(exist_ok=True)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = AutoModel.from_pretrained(HF_ID, torch_dtype=torch.float32).eval().to(device)
    by_run = defaultdict(list)
    for s in samples:
        by_run[s["run_id"]].append(s)
    store = {v: defaultdict(dict) for v in VARIANTS}
    t0 = time.time()
    done = 0
    for run_id, items in sorted(by_run.items()):
        rec = inv[run_id]
        index = (
            c.snapshot_index(c.LOGS_ROOT / run_id / "snapshots")
            if rec["source"] == "snapshot"
            else c.video_index(json.loads((c.OUT_ROOT / "timelines" / (run_id.replace("/", "__") + ".json")).read_text()))
        )
        assert index.times == ds["frame_indexes"][run_id]["times"], run_id
        frames = EpisodeFrames(index)
        track = c.load_gt(c.LOGS_ROOT / run_id)
        items.sort(key=lambda s: s["t_end"])
        for b0 in range(0, len(items), BATCH):
            batch = items[b0 : b0 + BATCH]
            frames.evict_before(batch[0]["t_end"] - 10.0)
            built = [build_clip(s, frames, track) for s in batch]
            for vi, variant in enumerate(("dyn", "static")):
                if variant not in VARIANTS:
                    continue
                x = torch.from_numpy(np.stack([b[vi] for b in built])).to(device)
                with torch.no_grad():
                    tok = model.get_vision_features(x)
                for s, b, tk in zip(batch, built, tok):
                    for k, v in pool(tk, pool_patches(variant, b[2])).items():
                        store[variant][k][s["uid"]] = v
            done += len(batch)
            if done % 100 < BATCH:
                el = time.time() - t0
                print(f"{done}/{len(samples)} {el:.0f}s ({el / done:.2f}s/sample) {run_id}", flush=True)
    for variant, d in store.items():
        arrays = {}
        uids = sorted(d["g"])
        arrays["uid"] = np.array(uids)
        for k in ("g", "gt", "ra", "rb"):
            if k == "rb":
                arrays[k] = np.stack([d[k].get(u, np.zeros_like(d["ra"][u])) for u in uids])
            else:
                arrays[k] = np.stack([d[k][u] for u in uids])
        np.savez_compressed(feat_dir / f"{variant}.npz", **arrays)
    meta = [{k: v for k, v in s.items() if k != "frames"} | {"frame_times": [ds["frame_indexes"][s["run_id"]]["times"][j] for j in s["frames"]]} for s in samples]
    if set(VARIANTS) != {"dyn", "static"}:
        print("partial run; index.json left untouched", VARIANTS)
        return
    (feat_dir / "index.json").write_text(json.dumps({"hf_id": HF_ID, "device": device, "samples": meta, "seconds": time.time() - t0}, default=float))
    print("done", len(samples), f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        VARIANTS = tuple(sys.argv[1].split(","))
    main()
