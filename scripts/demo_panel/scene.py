"""Scene-pane sources: a top-down reconstruction from ground truth, or a camera clip.

Both implement `SceneSource.frame_at(sim_time, size)` returning an RGB image of
the requested pane size, so the panel compositor does not care where the
picture came from. `sim_time` is the panel's ROS sim clock.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
import yaml

from scripts.demo_panel.timemap import ClipTimeMap

ROBOT_COLORS_RGB = {
    "robot_1": (230, 85, 60),
    "robot_2": (40, 120, 220),
    "robot_3": (40, 165, 90),
    "robot_4": (170, 80, 200),
}
DEFAULT_COLOR_RGB = (90, 90, 90)


class SceneSource(Protocol):
    """Anything that can draw the scene at a sim time."""

    label: str
    detail: str

    def frame_at(self, sim_time: float, size: tuple[int, int]) -> np.ndarray:
        """Return an RGB `uint8` image of shape `(size[1], size[0], 3)`."""
        ...


@dataclass(frozen=True)
class Footprint:
    """Rectangular robot footprint in the robot frame (metres)."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    source: str


def load_footprint(nav2_params: Path) -> Footprint:
    """Read the first `footprint:` polygon from a Nav2 params file.

    Args:
        nav2_params: Path to `nav2_params.yaml`.

    Returns:
        The axis-aligned bounds of that polygon.

    Raises:
        ValueError: No footprint entry is found.
    """
    data = yaml.safe_load(nav2_params.read_text())

    def walk(node: Any) -> str | None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "footprint" and isinstance(v, str):
                    return v
                found = walk(v)
                if found:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = walk(v)
                if found:
                    return found
        return None

    text = walk(data)
    if text is None:
        raise ValueError(f"no footprint in {nav2_params}")
    pts = np.asarray(json.loads(text), dtype=float)
    return Footprint(
        float(pts[:, 0].min()),
        float(pts[:, 0].max()),
        float(pts[:, 1].min()),
        float(pts[:, 1].max()),
        source=nav2_params.name,
    )


@dataclass(frozen=True)
class OccupancyMap:
    """A Nav2 occupancy map image with its world placement."""

    image: np.ndarray
    resolution: float
    origin_x: float
    origin_y: float
    source: str

    @classmethod
    def load(cls, map_yaml: Path) -> OccupancyMap:
        """Load a Nav2 map YAML and its PGM image.

        Args:
            map_yaml: Path to the map YAML.

        Returns:
            The map.

        Raises:
            FileNotFoundError: The image named by the YAML is missing.
        """
        meta = yaml.safe_load(map_yaml.read_text())
        img_path = map_yaml.parent / meta["image"]
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(img_path)
        return cls(
            img,
            float(meta["resolution"]),
            float(meta["origin"][0]),
            float(meta["origin"][1]),
            map_yaml.name,
        )

    def occupied_at(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Boolean occupancy for world coordinates (out-of-map counts as occupied)."""
        h, w = self.image.shape
        col = np.floor((x - self.origin_x) / self.resolution).astype(int)
        row = h - 1 - np.floor((y - self.origin_y) / self.resolution).astype(int)
        inside = (col >= 0) & (col < w) & (row >= 0) & (row < h)
        out = np.ones(x.shape, dtype=bool)
        out[inside] = self.image[row[inside], col[inside]] < 128
        return out


class GroundTruthTrack:
    """Ground-truth poses interpolated in time."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        """Index GT rows.

        Args:
            rows: Rows of `ground_truth.jsonl`, any order.

        Raises:
            ValueError: No rows.
        """
        if not rows:
            raise ValueError("no GT rows")
        rows = sorted(rows, key=lambda r: r["sim_time_sec"])
        self.times = np.asarray([r["sim_time_sec"] for r in rows], dtype=float)
        self.robot_ids = sorted(rows[0]["robots"])
        self.rows = rows
        self._xy = {
            rid: np.asarray([[r["robots"][rid]["x"], r["robots"][rid]["y"]] for r in rows])
            for rid in self.robot_ids
        }
        self._th = {
            rid: np.unwrap(np.asarray([r["robots"][rid]["theta"] for r in rows]))
            for rid in self.robot_ids
        }

    @classmethod
    def load(cls, path: Path) -> GroundTruthTrack:
        """Load `ground_truth.jsonl`."""
        return cls([json.loads(x) for x in path.read_text().splitlines() if x.strip()])

    def pose(self, robot_id: str, t: float) -> tuple[float, float, float]:
        """Interpolated `(x, y, theta)` at GT time `t` (clamped to the range)."""
        xy = self._xy[robot_id]
        x = float(np.interp(t, self.times, xy[:, 0]))
        y = float(np.interp(t, self.times, xy[:, 1]))
        th = float(np.interp(t, self.times, self._th[robot_id]))
        return x, y, th

    def trail(self, robot_id: str, t: float, window: float) -> np.ndarray:
        """GT positions over `[t - window, t]` as an `(N, 2)` array."""
        lo = np.searchsorted(self.times, t - window)
        hi = np.searchsorted(self.times, t, side="right")
        return self._xy[robot_id][lo:hi]

    def row_at(self, t: float) -> dict[str, Any]:
        """The GT row nearest to time `t`."""
        i = int(np.clip(np.searchsorted(self.times, t), 0, len(self.rows) - 1))
        if i > 0 and abs(self.times[i - 1] - t) < abs(self.times[i] - t):
            i -= 1
        return self.rows[i]


class GroundTruthScene:
    """Top-down scene reconstructed from ground-truth poses."""

    label = "Reconstructed from ground-truth poses (no camera recording for this run)"

    def __init__(
        self,
        track: GroundTruthTrack,
        footprint: Footprint,
        occupancy: OccupancyMap | None,
        gt_offset_sec: float,
        extent_m: float = 2.4,
        trail_sec: float = 20.0,
        detail: str = "",
    ) -> None:
        """Create the reconstruction.

        Args:
            track: GT poses.
            footprint: Robot footprint to draw.
            occupancy: Optional static map drawn behind the robots.
            gt_offset_sec: Panel sim time minus GT time.
            extent_m: Half-width of the square world window shown.
            trail_sec: Seconds of past GT path drawn behind each robot.
            detail: Second caption line (where the map/footprint came from).
        """
        self.detail = detail
        self.track = track
        self.footprint = footprint
        self.occupancy = occupancy
        self.gt_offset = gt_offset_sec
        self.extent = extent_m
        self.trail_sec = trail_sec
        self._bg_cache: dict[tuple[int, int], np.ndarray] = {}

    def _to_px(self, x: float, y: float, size: tuple[int, int]) -> tuple[float, float]:
        w, h = size
        u = (x + self.extent) / (2 * self.extent) * w
        v = (self.extent - y) / (2 * self.extent) * h
        return u, v

    def _background(self, size: tuple[int, int]) -> np.ndarray:
        if size in self._bg_cache:
            return self._bg_cache[size].copy()
        w, h = size
        img = np.full((h, w, 3), 236, dtype=np.uint8)
        if self.occupancy is not None:
            us = (np.arange(w) + 0.5) / w * 2 * self.extent - self.extent
            vs = self.extent - (np.arange(h) + 0.5) / h * 2 * self.extent
            xx, yy = np.meshgrid(us, vs)
            occ = self.occupancy.occupied_at(xx, yy)
            img[occ] = (120, 128, 140)
        # 0.5 m grid so distances can be judged by eye.
        step = 0.5
        g = -math.floor(self.extent / step) * step
        while g <= self.extent + 1e-9:
            u, _ = self._to_px(g, 0, size)
            _, v = self._to_px(0, g, size)
            color = (205, 205, 205) if abs(g) > 1e-9 else (185, 185, 185)
            cv2.line(img, (int(round(u)), 0), (int(round(u)), h - 1), color, 1)
            cv2.line(img, (0, int(round(v))), (w - 1, int(round(v))), color, 1)
            g += step
        self._bg_cache[size] = img
        return img.copy()

    def frame_at(self, sim_time: float, size: tuple[int, int]) -> np.ndarray:
        """Draw the scene at panel sim time `sim_time` (GT time = sim - offset)."""
        t = sim_time - self.gt_offset
        img = self._background(size)
        scale = size[0] / (2 * self.extent)
        row = self.track.row_at(t)
        for rid in self.track.robot_ids:
            color = ROBOT_COLORS_RGB.get(rid, DEFAULT_COLOR_RGB)
            gx, gy = row["robots"][rid]["goal_x"], row["robots"][rid]["goal_y"]
            gu, gv = self._to_px(gx, gy, size)
            r = int(0.09 * scale)
            cv2.line(
                img, (int(gu - r), int(gv - r)), (int(gu + r), int(gv + r)), color, 3, cv2.LINE_AA
            )
            cv2.line(
                img, (int(gu - r), int(gv + r)), (int(gu + r), int(gv - r)), color, 3, cv2.LINE_AA
            )
            trail = self.track.trail(rid, t, self.trail_sec)
            if len(trail) > 1:
                pts = np.asarray([self._to_px(px, py, size) for px, py in trail])
                faded = tuple(int(c * 0.45 + 255 * 0.55) for c in color)
                cv2.polylines(img, [np.round(pts).astype(np.int32)], False, faded, 3, cv2.LINE_AA)
        for rid in self.track.robot_ids:
            color = ROBOT_COLORS_RGB.get(rid, DEFAULT_COLOR_RGB)
            x, y, th = self.track.pose(rid, t)
            fp = self.footprint
            corners = np.asarray(
                [
                    [fp.x_min, fp.y_min],
                    [fp.x_max, fp.y_min],
                    [fp.x_max, fp.y_max],
                    [fp.x_min, fp.y_max],
                ]
            )
            c, s = math.cos(th), math.sin(th)
            world = corners @ np.asarray([[c, s], [-s, c]]) + np.asarray([x, y])
            px = np.asarray([self._to_px(wx, wy, size) for wx, wy in world])
            cv2.fillPoly(img, [np.round(px).astype(np.int32)], color, cv2.LINE_AA)
            cv2.polylines(img, [np.round(px).astype(np.int32)], True, (30, 30, 30), 2, cv2.LINE_AA)
            u, v = self._to_px(x, y, size)
            hu, hv = self._to_px(x + 0.16 * c, y + 0.16 * s, size)
            cv2.arrowedLine(
                img,
                (int(u), int(v)),
                (int(hu), int(hv)),
                (20, 20, 20),
                3,
                cv2.LINE_AA,
                tipLength=0.35,
            )
        return img

    def labels_at(self, sim_time: float) -> list[tuple[str, tuple[float, float]]]:
        """Robot id and normalised pane position `(u, v)` in [0, 1] for text labels."""
        t = sim_time - self.gt_offset
        out = []
        for rid in self.track.robot_ids:
            x, y, _ = self.track.pose(rid, t)
            out.append(
                (
                    rid,
                    ((x + self.extent) / (2 * self.extent), (self.extent - y) / (2 * self.extent)),
                )
            )
        return out

    def min_pairwise_at(self, sim_time: float) -> float | None:
        """GT `min_pairwise_distance_m` of the nearest GT row."""
        v = self.track.row_at(sim_time - self.gt_offset).get("min_pairwise_distance_m")
        return float(v) if isinstance(v, (int, float)) else None


class CameraClipScene:
    """Scene pane from a recorded camera clip (one or more segments), synced on sim time.

    `scripts/record_topic_video.py --segment-frames N` writes `out_000.mp4`,
    `out_001.mp4`, ...; the segments are treated as one clip whose frame index
    runs on across them. Frames are decoded sequentially and cached, so
    forward playback decodes each frame at most once.
    """

    def __init__(
        self,
        videos: Path | Sequence[Path],
        time_map: ClipTimeMap,
        detail: str = "",
        label: str = "Camera recording",
    ) -> None:
        """Open the clip.

        Args:
            videos: One MP4, or the recorder's segments in order.
            time_map: Frame-index (across all segments) to sim-time map.
            detail: Second caption line (clip files, timing source).
            label: First caption line (e.g. which topic was recorded).

        Raises:
            FileNotFoundError: A segment cannot be opened.
        """
        self.label = label
        self.detail = detail
        paths = [videos] if isinstance(videos, Path) else list(videos)
        self._caps = []
        self._starts = [0]
        for p in paths:
            cap = cv2.VideoCapture(str(p))
            if not cap.isOpened():
                raise FileNotFoundError(p)
            self._caps.append(cap)
            self._starts.append(self._starts[-1] + int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        self.frame_count = self._starts[-1]
        self.time_map = time_map
        self._next = [0] * len(self._caps)
        self._last: tuple[int, np.ndarray] | None = None

    def _read(self, index: int) -> np.ndarray | None:
        if self._last is not None and self._last[0] == index:
            return self._last[1]
        seg = int(np.searchsorted(self._starts, index, side="right") - 1)
        if seg < 0 or seg >= len(self._caps):
            return None
        local = index - self._starts[seg]
        cap = self._caps[seg]
        if local < self._next[seg]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, local)
            self._next[seg] = local
        frame = None
        while self._next[seg] <= local:
            ok, frame = cap.read()
            self._next[seg] += 1
            if not ok:
                return None
        if frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._last = (index, rgb)
        return rgb

    def frame_index_at(self, sim_time: float) -> int | None:
        """Clip frame shown at a sim time, or None outside the clip."""
        idx = self.time_map.frame_at_sim(sim_time)
        if idx is None or idx >= self.frame_count:
            return None
        return idx

    def frame_at(self, sim_time: float, size: tuple[int, int]) -> np.ndarray:
        """Return the clip frame for `sim_time`, letterboxed to `size` (grey if none)."""
        w, h = size
        canvas = np.full((h, w, 3), 40, dtype=np.uint8)
        idx = self.frame_index_at(sim_time)
        frame = None if idx is None else self._read(idx)
        if frame is None:
            return canvas
        fh, fw = frame.shape[:2]
        s = min(w / fw, h / fh)
        nw, nh = int(fw * s), int(fh * s)
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        y0, x0 = (h - nh) // 2, (w - nw) // 2
        canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
        return canvas
