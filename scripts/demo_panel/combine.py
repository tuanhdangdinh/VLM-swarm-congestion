"""Assemble per-scenario demo videos into one combined video, without altering them.

Pure logic (manifest validation, layout and trim arithmetic, caption text,
sidecar contents) is kept apart from the I/O (probing, decoding, drawing,
encoding) so it can be unit-tested without video files.

Per clip the output shows a plain title card, then the clip letterboxed (never
cropped) into a content area, with a thin caption bar above that area. The bar
is outside the content area, so nothing is drawn over the clip's own pixels.

With `"outcome_reveal": "after"` in the manifest, the title cards and caption
bars leave the outcome label out, and a clip marked `"outcome_card": true` is
followed by an outcome card, so the label is shown only after the excerpt
(the default, `"before"`, keeps the label on the card and the bar).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scripts.demo_panel.render import (
    CAPTION_RGB,
    DIM_RGB,
    PAGE_BG,
    H264Writer,
    load_mono_font,
)

OUTCOMES = (
    "VLM-driven execution",
    "M3-default resolution",
    "Unresolved failure",
    "Resolved — grounder held the queued robots; model chose strategy and yielder",
)
DISCLAIMER = "Illustrative demonstration, not controlled experimental evidence."
BAR_HEIGHT = 44
LETTERBOX_RGB = (0, 0, 0)
BAR_RGB = (30, 32, 36)
TRIM_TOLERANCE_SEC = 0.05


class ManifestError(ValueError):
    """The manifest, a clip file or a trim is invalid."""


class ClipSpec(BaseModel):
    """One manifest entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    outcome: Literal[
        "VLM-driven execution",
        "M3-default resolution",
        "Unresolved failure",
        "Resolved — grounder held the queued robots; model chose strategy and yielder",
    ]
    take: str = Field(min_length=1)
    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, gt=0)
    note: str | None = None
    outcome_card: bool = False
    outcome_note: str | None = None


class Manifest(BaseModel):
    """Ordered list of clips."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    clips: list[ClipSpec] = Field(min_length=1)
    outcome_reveal: Literal["before", "after"] = "before"


@dataclass(frozen=True)
class ClipInfo:
    """Probed properties of a source video."""

    width: int
    height: int
    fps: float
    frames: int

    @property
    def duration(self) -> float:
        """Source duration in seconds."""
        return self.frames / self.fps


@dataclass(frozen=True)
class Trim:
    """Resolved excerpt of a source clip, in source seconds."""

    start: float
    end: float
    source_duration: float

    @property
    def duration(self) -> float:
        """Excerpt length in seconds."""
        return self.end - self.start

    @property
    def trimmed(self) -> bool:
        """Whether any part of the source is left out."""
        return (
            self.start > TRIM_TOLERANCE_SEC or self.end < self.source_duration - TRIM_TOLERANCE_SEC
        )


def parse_manifest(data: object) -> Manifest:
    """Validate a decoded manifest.

    Args:
        data: Decoded JSON, expected `{"clips": [{...}, ...]}`.

    Returns:
        The validated manifest.

    Raises:
        ManifestError: Unknown outcome label, missing field, unknown key, or bad type.
    """
    try:
        return Manifest.model_validate(data)
    except ValidationError as exc:
        lines = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            if err["type"] == "literal_error":
                lines.append(f"{loc}: unknown outcome label; allowed: {', '.join(OUTCOMES)}")
            else:
                lines.append(f"{loc}: {err['msg']}")
        raise ManifestError("invalid manifest: " + "; ".join(lines)) from exc


def load_manifest(path: Path) -> Manifest:
    """Read and validate a manifest file.

    Args:
        path: JSON manifest.

    Returns:
        The validated manifest.

    Raises:
        ManifestError: Unreadable file, bad JSON or invalid content.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read manifest {path}: {exc}") from exc
    return parse_manifest(data)


def resolve_clip_path(spec: ClipSpec, manifest_dir: Path) -> Path:
    """Resolve a clip path; relative paths are relative to the manifest's directory.

    Args:
        spec: Manifest entry.
        manifest_dir: Directory holding the manifest.

    Returns:
        The path to the clip file.
    """
    p = Path(spec.path)
    return p if p.is_absolute() else manifest_dir / p


def resolve_trim(spec: ClipSpec, source_duration: float) -> Trim:
    """Turn the optional manifest start/end into a validated excerpt.

    Args:
        spec: Manifest entry.
        source_duration: Probed duration of the source in seconds.

    Returns:
        The excerpt; omitted bounds default to the clip's start and end.

    Raises:
        ManifestError: The range is empty or lies outside the source.
    """
    start = 0.0 if spec.start is None else spec.start
    end = source_duration if spec.end is None else spec.end
    if end > source_duration + TRIM_TOLERANCE_SEC:
        raise ManifestError(
            f"{spec.path}: trim end {end:g} s exceeds clip duration {source_duration:.2f} s"
        )
    end = min(end, source_duration)
    if start >= end:
        raise ManifestError(f"{spec.path}: trim start {start:g} s is not before end {end:g} s")
    return Trim(start, end, source_duration)


def _sec(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def trim_text(trim: Trim) -> str:
    """Caption text that states exactly what part of the source is shown.

    Args:
        trim: Resolved excerpt.

    Returns:
        `excerpt 12-95 s of 114.6 s` for a cut, `full clip` otherwise.
    """
    if not trim.trimmed:
        return "full clip"
    return f"excerpt {_sec(trim.start)}-{_sec(trim.end)} s of {_sec(trim.source_duration)} s"


def caption_text(spec: ClipSpec, trim: Trim, max_chars: int, reveal: str = "before") -> str:
    """One-line caption: scenario title, outcome label, take label, trim.

    Only the scenario title is shortened (with `...`) when the line is too
    long, so the outcome, take and trim are always visible.

    Args:
        spec: Manifest entry.
        trim: Resolved excerpt.
        max_chars: Characters that fit on the bar.
        reveal: `before` (outcome on the bar) or `after` (outcome left out).

    Returns:
        The caption line.
    """
    outcome = f" | {spec.outcome}" if reveal == "before" else ""
    tail = f"{outcome} | {spec.take} | {trim_text(trim)}"
    room = max_chars - len(tail)
    title = spec.title
    if len(title) > room:
        title = title[: max(1, room - 3)] + "..." if room > 4 else title[:1]
    return title + tail


def card_lines(spec: ClipSpec, reveal: str = "before") -> list[tuple[str, str]]:
    """Title-card content as `(role, text)` rows.

    Args:
        spec: Manifest entry.
        reveal: `before` (outcome on the card) or `after` (outcome left out).

    Returns:
        Rows in display order; roles are `title`, `body`, `note` and `fixed`.
    """
    rows = [("title", spec.title)]
    if reveal == "before":
        rows.append(("body", spec.outcome))
    rows.append(("body", spec.take))
    if spec.note:
        rows.append(("note", spec.note))
    rows.append(("fixed", DISCLAIMER))
    return rows


def outcome_card_lines(spec: ClipSpec) -> list[tuple[str, str]]:
    """Outcome-card content shown after a clip in `after` mode.

    Args:
        spec: Manifest entry.

    Returns:
        Rows: the title, `Outcome: <label>`, take, optional outcome note, fixed line.
    """
    rows = [("title", spec.title), ("body", f"Outcome: {spec.outcome}"), ("body", spec.take)]
    if spec.outcome_note:
        rows.append(("note", spec.outcome_note))
    rows.append(("fixed", DISCLAIMER))
    return rows


def _even(x: int) -> int:
    return x + (x % 2)


def output_size(
    infos: Sequence[ClipInfo], override: tuple[int, int] | None = None
) -> tuple[int, int, int]:
    """Common output geometry.

    The content area is the override, else the largest source width and height
    (so same-size sources are not rescaled); the caption bar sits above it.

    Args:
        infos: Probed sources.
        override: Requested content `(width, height)`.

    Returns:
        `(content_width, content_height, total_height)`, all even.
    """
    if override is not None:
        w, h = override
    else:
        w, h = max(i.width for i in infos), max(i.height for i in infos)
    w, h = _even(w), _even(h)
    return w, h, h + BAR_HEIGHT


def letterbox_rect(src: tuple[int, int], area: tuple[int, int]) -> tuple[int, int, int, int]:
    """Largest aspect-preserving rectangle for `src` inside `area`, centred.

    Args:
        src: Source `(width, height)`.
        area: Content area `(width, height)`.

    Returns:
        `(x, y, width, height)` inside the area; never crops.
    """
    scale = min(area[0] / src[0], area[1] / src[1])
    w = min(area[0], max(1, round(src[0] * scale)))
    h = min(area[1], max(1, round(src[1] * scale)))
    return (area[0] - w) // 2, (area[1] - h) // 2, w, h


def frame_count(seconds: float, fps: float) -> int:
    """Output frames for a duration (at least one)."""
    return max(1, int(round(seconds * fps)))


def source_index(out_i: int, fps: float, trim: Trim, src_fps: float, src_frames: int) -> int:
    """Source frame shown for output frame `out_i` (nearest-earlier resampling).

    Args:
        out_i: Output frame index within the clip.
        fps: Output frame rate.
        trim: Resolved excerpt.
        src_fps: Source frame rate.
        src_frames: Source frame count.

    Returns:
        Source frame index, clamped to the source.
    """
    t = trim.start + out_i / fps
    return min(src_frames - 1, int(math.floor(t * src_fps + 1e-6)))


def md5_of(path: Path) -> str:
    """MD5 hex digest of a file (identification only)."""
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_sidecar(
    out: Path,
    size: tuple[int, int],
    fps: float,
    card_sec: float,
    entries: Sequence[tuple[ClipSpec, Path, str, ClipInfo, Trim]],
    reveal: str = "before",
) -> dict:
    """Sidecar JSON content.

    Args:
        out: Output video path.
        size: Output `(width, height)`.
        fps: Output frame rate.
        card_sec: Title card length.
        entries: Per clip: spec, resolved path, md5, probed info, trim.
        reveal: Manifest `outcome_reveal`; `after` adds its keys to the sidecar.

    Returns:
        A JSON-serialisable dict.
    """
    side = {
        "output": out.name,
        "output_size": list(size),
        "output_fps": fps,
        "title_card_sec": card_sec,
        "fixed_card_line": DISCLAIMER,
        "clips": [
            {
                "source": str(path),
                "md5": md5,
                "source_size": [info.width, info.height],
                "source_fps": info.fps,
                "source_duration_sec": round(info.duration, 3),
                "trim": {
                    "start_sec": trim.start,
                    "end_sec": trim.end,
                    "trimmed": trim.trimmed,
                    "caption": trim_text(trim),
                },
                "title": spec.title,
                "outcome": spec.outcome,
                "take": spec.take,
                "note": spec.note,
                **(
                    {"outcome_card": spec.outcome_card, "outcome_note": spec.outcome_note}
                    if reveal == "after"
                    else {}
                ),
            }
            for spec, path, md5, info, trim in entries
        ],
    }
    if reveal == "after":
        side["outcome_reveal"] = "after"
    return side


def probe_clip(path: Path) -> ClipInfo:
    """Open a video and read its size, fps and frame count.

    Args:
        path: Video file.

    Returns:
        Probed properties.

    Raises:
        ManifestError: Missing file, or the video cannot be decoded.
    """
    if not path.is_file():
        raise ManifestError(f"clip file not found: {path}")
    cap = cv2.VideoCapture(str(path))
    try:
        ok, frame = cap.read() if cap.isOpened() else (False, None)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()
    if not ok or frame is None or fps <= 0 or frames <= 0:
        raise ManifestError(f"unreadable video (cannot decode a frame): {path}")
    h, w = frame.shape[:2]
    return ClipInfo(width=w, height=h, fps=float(fps), frames=frames)


def _wrap_words(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(trial) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    return lines


def render_card(
    spec: ClipSpec,
    size: tuple[int, int],
    font_override: str | None = None,
    rows: list[tuple[str, str]] | None = None,
) -> np.ndarray:
    """Draw a plain title card.

    Args:
        spec: Manifest entry.
        size: Frame `(width, height)`.
        font_override: Monospace font file name or path.
        rows: Card rows; default `card_lines(spec)`.

    Returns:
        RGB frame.
    """
    img = Image.new("RGB", size, PAGE_BG)
    d = ImageDraw.Draw(img)
    sizes = {"title": 40, "body": 30, "note": 26, "fixed": 24}
    colors = {"title": CAPTION_RGB, "body": CAPTION_RGB, "note": DIM_RGB, "fixed": DIM_RGB}
    margin = size[0] // 10
    rows = card_lines(spec) if rows is None else rows
    laid: list[tuple[str, str, ImageFont.FreeTypeFont]] = []
    total = 0
    for role, text in rows:
        font = load_mono_font(sizes[role], font_override)
        for ln in _wrap_words(text, font, size[0] - 2 * margin):
            laid.append((role, ln, font))
            total += int(font.size * 1.4) + (24 if role in ("title", "note") else 8)
    y = max(20, (size[1] - total) // 2)
    for role, ln, font in laid:
        d.text((margin, y), ln, font=font, fill=colors[role])
        y += int(font.size * 1.4) + (24 if role in ("title", "note") else 8)
    return np.asarray(img)


def render_bar(text: str, width: int, font_override: str | None = None) -> np.ndarray:
    """Draw the caption bar.

    Args:
        text: Caption line.
        width: Bar width in pixels.
        font_override: Monospace font file name or path.

    Returns:
        RGB array of shape `(BAR_HEIGHT, width, 3)`.
    """
    img = Image.new("RGB", (width, BAR_HEIGHT), BAR_RGB)
    font = load_mono_font(20, font_override)
    ImageDraw.Draw(img).text((16, (BAR_HEIGHT - 20) // 2 - 1), text, font=font, fill=CAPTION_RGB)
    return np.asarray(img)


def bar_capacity(width: int, font_override: str | None = None) -> int:
    """Characters of caption that fit on a bar of `width` pixels."""
    font = load_mono_font(20, font_override)
    return max(20, int((width - 32) // font.getlength("M")))


def iter_clip_frames(
    path: Path,
    info: ClipInfo,
    trim: Trim,
    fps: float,
    content: tuple[int, int],
) -> Iterator[np.ndarray]:
    """Yield letterboxed RGB content frames for one excerpt at the output fps.

    Args:
        path: Source video.
        info: Probed properties.
        trim: Resolved excerpt.
        fps: Output frame rate.
        content: Content area `(width, height)`.

    Yields:
        RGB frames of shape `(content_height, content_width, 3)`.

    Raises:
        ManifestError: The source stops decoding before the excerpt ends.
    """
    x, y, w, h = letterbox_rect((info.width, info.height), content)
    cap = cv2.VideoCapture(str(path))
    try:
        n_out = frame_count(trim.duration, fps)
        pos = -1
        last: np.ndarray | None = None
        for i in range(n_out):
            want = source_index(i, fps, trim, info.fps, info.frames)
            while pos < want:
                ok, bgr = cap.read()
                if not ok:
                    if last is None:
                        raise ManifestError(f"video stopped decoding early: {path}")
                    break
                pos += 1
                last = bgr
            assert last is not None
            canvas = np.empty((content[1], content[0], 3), dtype=np.uint8)
            canvas[:] = LETTERBOX_RGB
            rgb = cv2.cvtColor(last, cv2.COLOR_BGR2RGB)
            if (w, h) != (info.width, info.height):
                interp = cv2.INTER_AREA if w < info.width else cv2.INTER_LINEAR
                rgb = cv2.resize(rgb, (w, h), interpolation=interp)
            canvas[y : y + h, x : x + w] = rgb
            yield canvas
    finally:
        cap.release()


def combine(
    manifest_path: Path,
    out: Path,
    fps: float = 24.0,
    card_sec: float = 3.0,
    size: tuple[int, int] | None = None,
    font: str | None = None,
    crf: int = 23,
) -> tuple[Path, float]:
    """Build the combined video and its sidecar.

    All clips are probed and validated before any encoding starts.

    Args:
        manifest_path: JSON manifest.
        out: Output MP4; the sidecar is `<stem>_sources.json` beside it.
        fps: Common output frame rate.
        card_sec: Title-card length in seconds.
        size: Content-area `(width, height)`; default is the largest source.
        font: Monospace font file name or path.
        crf: x264 quality.

    Returns:
        `(sidecar path, total duration in seconds)`.

    Raises:
        ManifestError: Invalid manifest, missing or unreadable clip, bad trim.
    """
    manifest = load_manifest(manifest_path)
    base = manifest_path.resolve().parent
    entries: list[tuple[ClipSpec, Path, str, ClipInfo, Trim]] = []
    for spec in manifest.clips:
        path = resolve_clip_path(spec, base)
        info = probe_clip(path)
        entries.append((spec, path, md5_of(path), info, resolve_trim(spec, info.duration)))
    cw, ch, total_h = output_size([e[3] for e in entries], size)
    capacity = bar_capacity(cw, font)
    writer = H264Writer(out, (cw, total_h), fps, crf)
    total = 0.0
    try:
        reveal = manifest.outcome_reveal
        for spec, path, _md5, info, trim in entries:
            card = render_card(spec, (cw, total_h), font, card_lines(spec, reveal))
            for _ in range(frame_count(card_sec, fps)):
                writer.write(card)
            total += frame_count(card_sec, fps) / fps
            bar = render_bar(caption_text(spec, trim, capacity, reveal), cw, font)
            for content in iter_clip_frames(path, info, trim, fps, (cw, ch)):
                writer.write(np.vstack([bar, content]))
                total += 1 / fps
            if reveal == "after" and spec.outcome_card:
                oc = render_card(spec, (cw, total_h), font, outcome_card_lines(spec))
                for _ in range(frame_count(card_sec, fps)):
                    writer.write(oc)
                total += frame_count(card_sec, fps) / fps
    finally:
        writer.close()
    sidecar = out.with_name(f"{out.stem}_sources.json")
    side = build_sidecar(out, (cw, total_h), fps, card_sec, entries, manifest.outcome_reveal)
    sidecar.write_text(json.dumps(side, indent=1) + "\n")
    return sidecar, total
