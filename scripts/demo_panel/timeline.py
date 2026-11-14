"""Output-video timeline: when each terminal line appears and what sim time is shown.

The sim clock advances at a fixed speed away from activity, slower near log
lines, at 1x wall clock across each model call (so its true latency is seen),
and is *held* (not advanced) while a burst of lines or a command block is
printed at a readable rate. Every speed state carries a caption so the viewer
is told which one applies.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass

BURST_CAPTION = "SLOWED: sim clock held/slowed so a burst of log lines stays readable"


@dataclass(frozen=True)
class TimelineItem:
    """What the timeline needs to know about one terminal line."""

    sim_time: float
    rows: int
    in_block: bool
    block_end: bool = False
    block_hold_sec: float = 0.0
    sets_pace: bool = True


@dataclass(frozen=True)
class CallSpan:
    """A model call: request and response sim times and the true wall duration."""

    sim_start: float
    sim_end: float
    wall_sec: float


@dataclass(frozen=True)
class TimelineParams:
    """Speeds (sim seconds per video second) and print rates."""

    idle_speed: float = 8.0
    event_speed: float = 3.0
    tail_speed: float = 30.0
    event_before: float = 1.0
    event_after: float = 3.0
    log_rows_per_sec: float = 7.0
    block_rows_per_sec: float = 7.0
    end_hold_sec: float = 2.0
    min_caption_sec: float = 0.6


class Timeline:
    """Piecewise-linear video-time to sim-time map with captions and reveal times."""

    def __init__(
        self,
        keyframes: Sequence[tuple[float, float]],
        captions: Sequence[tuple[float, float, str]],
        reveal: Sequence[float],
    ) -> None:
        """Create the timeline.

        Args:
            keyframes: `(video_t, sim_t)` points, both non-decreasing.
            captions: `(video_start, video_end, text)` intervals.
            reveal: Video time at which each item appears.

        Raises:
            ValueError: Keyframes are empty or decrease.
        """
        if not keyframes:
            raise ValueError("no keyframes")
        for (v0, s0), (v1, s1) in zip(keyframes, keyframes[1:], strict=False):
            if v1 < v0 - 1e-9 or s1 < s0 - 1e-9:
                raise ValueError("keyframes must be non-decreasing")
        self.keyframes = tuple(keyframes)
        self.captions = tuple(captions)
        self.reveal = tuple(reveal)
        self._v = [k[0] for k in self.keyframes]

    @property
    def total_video_sec(self) -> float:
        """Video duration."""
        return self.keyframes[-1][0]

    def sim_at(self, video_t: float) -> float:
        """Sim time shown at a video time."""
        i = bisect.bisect_right(self._v, video_t) - 1
        if i < 0:
            return self.keyframes[0][1]
        if i >= len(self.keyframes) - 1:
            return self.keyframes[-1][1]
        (v0, s0), (v1, s1) = self.keyframes[i], self.keyframes[i + 1]
        if v1 - v0 <= 1e-12:
            return s1
        return s0 + (s1 - s0) * (video_t - v0) / (v1 - v0)

    def caption_at(self, video_t: float) -> str:
        """Speed caption at a video time."""
        for v0, v1, text in self.captions:
            if v0 <= video_t < v1:
                return text
        return self.captions[-1][2] if self.captions else ""

    def visible_count(self, video_t: float) -> int:
        """Number of items revealed by a video time."""
        return bisect.bisect_right(list(self.reveal), video_t + 1e-9)


def build_timeline(
    items: Sequence[TimelineItem],
    calls: Sequence[CallSpan],
    sim_end: float,
    params: TimelineParams | None = None,
) -> Timeline:
    """Lay out the video timeline.

    Args:
        items: Terminal items in display order.
        calls: Model calls (played at 1x wall clock).
        sim_end: Last sim second to show.
        params: Speeds and print rates.

    Returns:
        The timeline; `reveal[i]` is item `i`'s appearance time.
    """
    p = params if params is not None else TimelineParams()
    item_sims = [it.sim_time for it in items if not it.in_block and it.sets_pace]
    windows = sorted((max(0.0, s - p.event_before), s + p.event_after) for s in item_sims)
    last_item = max(item_sims) if item_sims else 0.0
    tail_after = min(sim_end, last_item + p.event_after)
    keyframes: list[tuple[float, float]] = [(0.0, 0.0)]
    captions: list[tuple[float, float, str]] = []
    state = {"v": 0.0, "s": 0.0}

    def push(v: float, s: float, caption: str) -> None:
        if v - state["v"] > 1e-9:
            if captions and captions[-1][2] == caption and abs(captions[-1][1] - state["v"]) < 1e-9:
                captions[-1] = (captions[-1][0], v, caption)
            else:
                captions.append((state["v"], v, caption))
        keyframes.append((v, s))
        state["v"], state["s"] = v, s

    def in_window(a: float, b: float) -> bool:
        i = bisect.bisect_right([w[0] for w in windows], a) - 1
        return any(w0 <= a and b <= w1 + 1e-9 for w0, w1 in windows[max(0, i - 3) : i + 1])

    def speed_caption(speed: float) -> str:
        return f"{speed:g}x sim time"

    def advance_to(target: float) -> None:
        if target <= state["s"] + 1e-9:
            return
        cuts = {state["s"], target, tail_after}
        for w0, w1 in windows:
            cuts.update((w0, w1))
        for c in calls:
            cuts.update((c.sim_start, c.sim_end))
        pts = sorted(x for x in cuts if state["s"] - 1e-9 <= x <= target + 1e-9)
        for a, b in zip(pts, pts[1:], strict=False):
            if b - a <= 1e-9:
                continue
            call = next(
                (c for c in calls if c.sim_start - 1e-9 <= a and b <= c.sim_end + 1e-9), None
            )
            if call is not None and call.sim_end > call.sim_start:
                dv = call.wall_sec * (b - a) / (call.sim_end - call.sim_start)
                rtf = (call.sim_end - call.sim_start) / call.wall_sec if call.wall_sec else 0
                cap = f"1x wall clock (real time) while waiting for the model; sim runs ~{rtf:.2f}x"
            else:
                if a >= tail_after - 1e-9:
                    speed = p.tail_speed
                elif in_window(a, b):
                    speed = p.event_speed
                else:
                    speed = p.idle_speed
                dv = (b - a) / speed
                cap = speed_caption(speed)
            push(state["v"] + dv, b, cap)

    reveal: list[float] = []
    last_v = -1e9
    last_rows = 0
    last_rate = p.log_rows_per_sec
    for it in items:
        advance_to(max(it.sim_time, state["s"]))
        earliest = last_v + last_rows / last_rate
        if state["v"] < earliest - 1e-9:
            cap = (
                "PAUSED (sim clock held) while the command output prints"
                if it.in_block
                else BURST_CAPTION
            )
            push(earliest, state["s"], cap)
        reveal.append(state["v"])
        last_v, last_rows = state["v"], it.rows
        last_rate = p.block_rows_per_sec if it.in_block else p.log_rows_per_sec
        if it.block_end and it.block_hold_sec > 0:
            push(
                state["v"] + it.rows / last_rate + it.block_hold_sec,
                state["s"],
                "PAUSED (sim clock held) while the command output prints",
            )
            last_v, last_rows = state["v"], 0
    advance_to(sim_end)
    push(state["v"] + max(p.end_hold_sec, 1e-3), state["s"], "end of episode")
    return Timeline(keyframes, smooth_captions(captions, p.min_caption_sec), reveal)


def smooth_captions(
    captions: Sequence[tuple[float, float, str]], min_sec: float
) -> list[tuple[float, float, str]]:
    """Remove caption flicker without changing interval bounds.

    During a burst the timeline alternates sub-second "held" stretches with
    near-zero "3x" stretches. Pass 1 relabels any stretch shorter than
    `min_sec` that lies between two stretches carrying the burst label with
    that label; pass 2 merges equal neighbours; pass 3 folds any remaining
    stretch shorter than `min_sec` into the one before it.

    Args:
        captions: `(start, end, text)` intervals in order.
        min_sec: Shortest interval that keeps its own label.

    Returns:
        Smoothed intervals covering the same span.
    """
    caps = [list(c) for c in captions]
    for i in range(1, len(caps) - 1):
        if caps[i][1] - caps[i][0] < min_sec and caps[i - 1][2] == caps[i + 1][2] == BURST_CAPTION:
            caps[i][2] = BURST_CAPTION
    merged: list[list] = []
    for c in caps:
        if merged and merged[-1][2] == c[2]:
            merged[-1][1] = c[1]
        else:
            merged.append(c)
    out: list[tuple[float, float, str]] = []
    for a, b, t in merged:
        if out and (b - a < min_sec or out[-1][2] == t):
            out[-1] = (out[-1][0], b, out[-1][2])
        else:
            out.append((a, b, t))
    return out
