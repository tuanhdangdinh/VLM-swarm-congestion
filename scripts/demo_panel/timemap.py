"""Clock mappings for the demo panel: wall to sim, sim to video, video frame to sim.

Three clocks meet in a bundle:

* ROS log lines (`m5.log`, `m4.log`) carry wall-clock epoch stamps.
* `m5_scene.jsonl` rows carry M5's `time.monotonic()` receipt time `t` and the
  scene's sim-time `stamp`; ground truth carries `sim_time_sec`.
* Some M4 lines carry their own `sim_t=`, and each decision artifact carries the
  sim `scene.stamp` of the snapshot analysed at its `starting analysis` line.

`wall -> sim` is therefore `sim = clock(wall - offset)`, where `clock` is the
piecewise-linear `(t, stamp)` series of the scene log and `offset` (wall minus
monotonic, constant for one host process lifetime) is the median over the
anchors. The sim rate per wall second drifts (RTF ~0.2-0.3), so no global
linear fit is used.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


class SceneClock:
    """Piecewise-linear map between M5 monotonic receipt time and scene sim time."""

    def __init__(self, monotonic: Sequence[float], sim: Sequence[float]) -> None:
        """Build the clock from paired samples.

        Args:
            monotonic: M5 `time.monotonic()` receipt times (`t` in the scene log).
            sim: Scene sim-time stamps for the same rows.

        Raises:
            ValueError: Fewer than two samples, mismatched lengths, or sim
                time that decreases as monotonic time increases.
        """
        if len(monotonic) != len(sim) or len(monotonic) < 2:
            raise ValueError("SceneClock needs >= 2 paired samples")
        order = np.argsort(np.asarray(monotonic, dtype=float), kind="stable")
        mono = np.asarray(monotonic, dtype=float)[order]
        sims = np.asarray(sim, dtype=float)[order]
        if np.any(np.diff(sims) < 0):
            raise ValueError("scene sim stamps decrease over monotonic time")
        self._mono = mono
        self._sim = sims
        # For sim -> monotonic, keep the first row of each repeated stamp so
        # the abscissa is strictly increasing.
        keep = np.concatenate(([True], np.diff(sims) > 0))
        self._sim_u = sims[keep]
        self._mono_u = mono[keep]

    @property
    def sim_range(self) -> tuple[float, float]:
        """First and last sim stamp in the series."""
        return float(self._sim[0]), float(self._sim[-1])

    @property
    def monotonic_range(self) -> tuple[float, float]:
        """First and last monotonic receipt time in the series."""
        return float(self._mono[0]), float(self._mono[-1])

    def sim_at_monotonic(self, t: float) -> float | None:
        """Interpolate sim time at a monotonic time; None outside the series."""
        if t < self._mono[0] or t > self._mono[-1]:
            return None
        return float(np.interp(t, self._mono, self._sim))

    def monotonic_at_sim(self, s: float) -> float | None:
        """Interpolate monotonic receipt time at a sim time; None outside the series."""
        if s < self._sim_u[0] or s > self._sim_u[-1]:
            return None
        return float(np.interp(s, self._sim_u, self._mono_u))


@dataclass(frozen=True)
class Anchor:
    """One `(wall, sim)` correspondence read from a log line or artifact."""

    wall: float
    sim: float
    source: str


def estimate_offset(anchors: Sequence[Anchor], clock: SceneClock) -> tuple[float, float] | None:
    """Estimate the constant wall-minus-monotonic offset from anchors.

    Args:
        anchors: Wall/sim correspondences.
        clock: Scene clock used to place each anchor's sim time on the
            monotonic axis.

    Returns:
        `(median_offset, spread)` where spread is max-min over usable anchors,
        or None when no anchor falls inside the clock's sim range.
    """
    offsets = []
    for a in anchors:
        mono = clock.monotonic_at_sim(a.sim)
        if mono is not None:
            offsets.append(a.wall - mono)
    if not offsets:
        return None
    return statistics.median(offsets), max(offsets) - min(offsets)


class WallSimMap:
    """Map ROS wall-clock stamps to sim time through the scene clock."""

    def __init__(self, clock: SceneClock, offset: float) -> None:
        """Create the map.

        Args:
            clock: Monotonic/sim scene clock.
            offset: Wall minus monotonic seconds.
        """
        self.clock = clock
        self.offset = offset

    def wall_to_sim(self, wall: float) -> float | None:
        """Sim time at a wall stamp, or None before/after the scene log."""
        return self.clock.sim_at_monotonic(wall - self.offset)

    def sim_to_wall(self, sim: float) -> float | None:
        """Wall stamp at which M5 had received the scene with this sim stamp."""
        mono = self.clock.monotonic_at_sim(sim)
        return None if mono is None else mono + self.offset

    def residuals(self, anchors: Sequence[Anchor]) -> list[tuple[Anchor, float]]:
        """Return `(anchor, mapped_sim - anchor.sim)` for every mappable anchor."""
        out = []
        for a in anchors:
            mapped = self.wall_to_sim(a.wall)
            if mapped is not None:
                out.append((a, mapped - a.sim))
        return out

    def local_rtf(self, sim_start: float, sim_end: float) -> float | None:
        """Mean sim seconds per wall second over a sim interval."""
        w0 = self.sim_to_wall(sim_start)
        w1 = self.sim_to_wall(sim_end)
        if w0 is None or w1 is None or w1 <= w0:
            return None
        return (sim_end - sim_start) / (w1 - w0)


class ClipTimeMap:
    """Map a recorded camera clip's frame index to sim time and back.

    `record_topic_video.py` writes one container frame per received message
    and logs only the first frame's `header_stamp` plus a final frame count, so
    frame times are known exactly only at anchors: the first frame, and any
    frame whose burned-in overlay clock (`t=<stamp>s f=<n>`) was read. Between
    anchors the map is linear in frame index; outside them it is undefined.
    """

    def __init__(self, anchors: Sequence[tuple[int, float]]) -> None:
        """Create the map.

        Args:
            anchors: `(frame_index, sim_time)` pairs, 0-based frame index.

        Raises:
            ValueError: Fewer than two anchors, or non-increasing frame index
                or sim time.
        """
        pts = sorted(anchors)
        if len(pts) < 2:
            raise ValueError("ClipTimeMap needs >= 2 (frame, sim) anchors")
        frames = [p[0] for p in pts]
        sims = [p[1] for p in pts]
        if any(b <= a for a, b in zip(frames, frames[1:], strict=False)) or any(
            b <= a for a, b in zip(sims, sims[1:], strict=False)
        ):
            raise ValueError("anchors must increase in both frame index and sim time")
        self._frames = np.asarray(frames, dtype=float)
        self._sims = np.asarray(sims, dtype=float)

    @classmethod
    def from_recorder(cls, first_stamp: float, last_stamp: float, frame_count: int) -> ClipTimeMap:
        """Build a two-anchor map from the first and last frame stamps.

        Args:
            first_stamp: `header_stamp` of frame 0 (recorder `first frame:` line).
            last_stamp: Sim stamp of the last frame (its overlay clock).
            frame_count: Frames written (recorder `WROTE ... frames=` value).

        Returns:
            The map.
        """
        return cls([(0, first_stamp), (frame_count - 1, last_stamp)])

    @property
    def sim_range(self) -> tuple[float, float]:
        """Sim time of the first and last anchor."""
        return float(self._sims[0]), float(self._sims[-1])

    def sim_at_frame(self, index: int) -> float | None:
        """Sim time of a frame index; None outside the anchored range."""
        if index < self._frames[0] or index > self._frames[-1]:
            return None
        return float(np.interp(index, self._frames, self._sims))

    def frame_at_sim(self, sim: float) -> int | None:
        """Latest frame whose sim time is <= `sim`; None outside the range."""
        if sim < self._sims[0] or sim > self._sims[-1]:
            return None
        return int(np.floor(np.interp(sim, self._sims, self._frames) + 1e-9))
