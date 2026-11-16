"""Draw the terminal pane, compose it beside the scene pane, and encode H.264 MP4.

Only the terminal transcript and the scene source are drawn; captions sit
outside the terminal (run label, sim clock, speed state, provenance sentence).
Frames are piped to the `ffmpeg` binary as raw RGB and encoded with
`libx264 -pix_fmt yuv420p -movflags +faststart` so the file plays in
QuickTime, browsers and phones.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from scripts.demo_panel.models import Transcript
from scripts.demo_panel.scene import GroundTruthScene, SceneSource
from scripts.demo_panel.timeline import Timeline

MONO_FONT_CANDIDATES = ("Menlo.ttc", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", "cour.ttf")
STYLE_RGB = {
    "m5": (232, 232, 232),
    "m4": (128, 196, 214),
    "warn": (229, 192, 90),
    "command": (126, 214, 126),
    "output": (214, 214, 214),
    "marker": (140, 140, 140),
}
TERM_BG = (16, 16, 16)
PAGE_BG = (44, 46, 50)
CAPTION_RGB = (226, 226, 226)
DIM_RGB = (165, 168, 172)
PROVENANCE = (
    "Terminal shows this run's own log files replayed in sync with simulation time; "
    "filter shown at top; '$' lines are read-only commands run on the bundle's files."
)


def load_mono_font(size: int, override: str | None = None) -> ImageFont.FreeTypeFont:
    """Load a monospace TrueType font by name from the system font directories.

    Args:
        size: Pixel size.
        override: Font file name or path to try first.

    Returns:
        The font.

    Raises:
        RuntimeError: None of the candidate fonts is available.
    """
    names = ([override] if override else []) + list(MONO_FONT_CANDIDATES)
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    raise RuntimeError(f"no monospace font found among {names}; pass --font")


def wrap_text(text: str, cols: int) -> list[str]:
    """Hard-wrap a line at exactly `cols` characters, as a terminal does.

    Args:
        text: One logical line (tabs expanded to 8 columns).
        cols: Terminal width in characters (>= 1).

    Returns:
        Screen rows; an empty line yields one empty row. No character is
        dropped: joining the rows gives back the tab-expanded text.
    """
    text = text.expandtabs(8)
    if not text:
        return [""]
    return [text[i : i + cols] for i in range(0, len(text), cols)]


@dataclass(frozen=True)
class Layout:
    """Pixel layout of one composite frame."""

    width: int = 1920
    height: int = 1080
    scene_box: tuple[int, int, int, int] = (40, 92, 800, 800)
    term_box: tuple[int, int, int, int] = (880, 80, 1020, 948)
    font_px: int = 15
    caption_px: int = 20


def fit_scene_box(layout: Layout, frame_size: tuple[int, int]) -> Layout:
    """Shrink the scene box's height to a camera clip's aspect ratio (width kept).

    The rows freed under the clip hold extra caption lines instead of letterbox bars.

    Args:
        layout: Current layout.
        frame_size: Clip frame `(width, height)` in pixels.

    Returns:
        The layout with the fitted scene box (unchanged for a taller clip).
    """
    x, y, w, h = layout.scene_box
    fw, fh = frame_size
    if fw <= 0 or fh <= 0:
        return layout
    return replace(layout, scene_box=(x, y, w, min(h, int(round(w * fh / fw)))))


class TerminalPane:
    """Renders the visible part of a transcript as a scrolling terminal."""

    def __init__(self, transcript: Transcript, size: tuple[int, int], font: ImageFont.FreeTypeFont):
        """Prepare wrapped rows.

        Args:
            transcript: Items to show.
            size: Pane `(width, height)` in pixels.
            font: Monospace font.
        """
        self.size = size
        self.font = font
        self.char_w = font.getlength("M")
        self.line_h = int(round(font.size * 1.27))
        self.pad = 10
        self.cols = max(20, int((size[0] - 2 * self.pad) // self.char_w))
        header_text = f"$ cd {transcript.bundle_name} && {transcript.filter_command}"
        self.header_rows = wrap_text(header_text, self.cols)
        self.item_rows = [wrap_text(it.text, self.cols) for it in transcript.items]
        self.items = transcript.items
        top = self.pad + len(self.header_rows) * self.line_h + 8
        self.body_top = top
        self.body_rows = max(1, (size[1] - top - self.pad) // self.line_h)

    def rows_of(self, index: int) -> int:
        """Screen rows used by item `index`."""
        return len(self.item_rows[index])

    def draw(self, visible: int) -> Image.Image:
        """Draw the pane with the first `visible` items printed."""
        img = Image.new("RGB", self.size, TERM_BG)
        d = ImageDraw.Draw(img)
        y = self.pad
        for row in self.header_rows:
            d.text((self.pad, y), row, font=self.font, fill=STYLE_RGB["command"])
            y += self.line_h
        d.line([(self.pad, y + 3), (self.size[0] - self.pad, y + 3)], fill=(70, 70, 70), width=1)
        rows: list[tuple[str, tuple[int, int, int]]] = []
        for i in range(visible - 1, -1, -1):
            color = STYLE_RGB[self.items[i].style]
            for r in reversed(self.item_rows[i]):
                rows.append((r, color))
            if len(rows) >= self.body_rows:
                break
        rows = list(reversed(rows[: self.body_rows]))
        y = self.body_top
        for text, color in rows:
            d.text((self.pad, y), text, font=self.font, fill=color)
            y += self.line_h
        return img


def _draw_wrapped(
    d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill, max_w: int
) -> int:
    words = text.split(" ")
    line = ""
    x, y = xy
    step = int(font.size * 1.3)
    for w in words:
        trial = f"{line} {w}".strip()
        if font.getlength(trial) > max_w and line:
            d.text((x, y), line, font=font, fill=fill)
            y += step
            line = w
        else:
            line = trial
    if line:
        d.text((x, y), line, font=font, fill=fill)
        y += step
    return y


class Compositor:
    """Composes scene pane, terminal pane and captions into video frames."""

    def __init__(
        self,
        transcript: Transcript,
        timeline: Timeline,
        scene: SceneSource,
        pane: TerminalPane,
        run_caption: str,
        layout: Layout | None = None,
        font_override: str | None = None,
        footer_note: str | None = None,
        captions: Sequence[str] = (),
    ) -> None:
        """Create the compositor.

        Args:
            transcript: Terminal content.
            timeline: Video timeline for that transcript.
            scene: Left-pane source.
            pane: Terminal pane built for `transcript` at `layout.term_box` size.
            run_caption: First caption line (run label, scenario, arm, backend).
            layout: Pixel layout.
            font_override: Monospace font name/path to prefer.
            footer_note: Extra footer text (e.g. alignment uncertainty).
            captions: Extra caption lines under the scene pane's own label (e.g.
                outcome label, take, model); never drawn inside the terminal.
        """
        self.captions = list(captions)
        self.t = transcript
        self.tl = timeline
        self.scene = scene
        self.layout = layout if layout is not None else Layout()
        self.cap_font = load_mono_font(self.layout.caption_px, font_override)
        self.small_font = load_mono_font(self.layout.caption_px - 3, font_override)
        self.term = pane
        self.run_caption = run_caption
        self.footer_note = footer_note
        self._term_cache: tuple[int, Image.Image] | None = None

    def frame(self, video_t: float) -> np.ndarray:
        """Render the composite RGB frame at a video time."""
        lay = self.layout
        sim = self.tl.sim_at(video_t)
        img = Image.new("RGB", (lay.width, lay.height), PAGE_BG)
        d = ImageDraw.Draw(img)
        d.text((20, 12), self.run_caption, font=self.cap_font, fill=CAPTION_RGB)
        d.text(
            (20, 44),
            f"sim t = {sim:7.2f} s   |   speed: {self.tl.caption_at(video_t)}",
            font=self.cap_font,
            fill=(240, 214, 120),
        )
        sx, sy, sw, sh = lay.scene_box
        pane = self.scene.frame_at(sim, (sw, sh))
        img.paste(Image.fromarray(pane), (sx, sy))
        if isinstance(self.scene, GroundTruthScene):
            for rid, (u, v) in self.scene.labels_at(sim):
                # Push the id label away from the junction centre so it does
                # not sit on the robot drawn there.
                du, dv = u - 0.5, v - 0.5
                norm = max((du * du + dv * dv) ** 0.5, 1e-6)
                lx = sx + u * sw + 34 * du / norm - 12
                ly = sy + v * sh + 34 * dv / norm - 12
                d.text(
                    (lx, ly),
                    rid.replace("robot_", "r"),
                    font=self.cap_font,
                    fill=(20, 20, 20),
                )
        y = _draw_wrapped(d, (sx, sy + sh + 6), self.scene.label, self.cap_font, CAPTION_RGB, sw)
        if self.scene.detail:
            y = _draw_wrapped(d, (sx, y), self.scene.detail, self.small_font, DIM_RGB, sw)
        for k, line in enumerate(self.captions):
            if k == 0:
                y = _draw_wrapped(d, (sx, y + 6), line, self.cap_font, (240, 214, 120), sw)
            else:
                y = _draw_wrapped(d, (sx, y + 4), line, self.small_font, CAPTION_RGB, sw)
        n = self.tl.visible_count(video_t)
        if self._term_cache is None or self._term_cache[0] != n:
            self._term_cache = (n, self.term.draw(n))
        tx, ty, _, _ = lay.term_box
        img.paste(self._term_cache[1], (tx, ty))
        footer = PROVENANCE
        if self.footer_note:
            footer += " " + self.footer_note
        _draw_wrapped(d, (20, lay.height - 48), footer, self.small_font, DIM_RGB, lay.width - 40)
        return np.asarray(img)


def title_card(
    lines: Sequence[str], layout: Layout | None = None, font_override: str | None = None
) -> np.ndarray:
    """A plain caption card (used between sequential clips)."""
    layout = layout if layout is not None else Layout()
    img = Image.new("RGB", (layout.width, layout.height), PAGE_BG)
    d = ImageDraw.Draw(img)
    font = load_mono_font(28, font_override)
    y = 380
    for ln in lines:
        y = _draw_wrapped(d, (160, y), ln, font, CAPTION_RGB, layout.width - 320) + 14
    return np.asarray(img)


def iter_frames(comp: Compositor, fps: float) -> Iterator[tuple[float, np.ndarray]]:
    """Yield `(video_t, frame)` for the whole timeline."""
    n = int(np.ceil(comp.tl.total_video_sec * fps))
    for i in range(n):
        t = i / fps
        yield t, comp.frame(t)


class H264Writer:
    """Pipe RGB frames to ffmpeg/libx264."""

    def __init__(self, path: Path, size: tuple[int, int], fps: float, crf: int = 23) -> None:
        """Start the encoder.

        Args:
            path: Output MP4.
            size: Frame `(width, height)`.
            fps: Frame rate.
            crf: x264 constant rate factor.

        Raises:
            RuntimeError: No `ffmpeg` binary on PATH.
        """
        exe = shutil.which("ffmpeg")
        if exe is None:
            raise RuntimeError("ffmpeg not found on PATH")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.size = size
        self._proc = subprocess.Popen(
            [
                exe,
                "-y",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{size[0]}x{size[1]}",
                "-r",
                f"{fps}",
                "-i",
                "-",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(path),
            ],
            stdin=subprocess.PIPE,
        )

    def write(self, frame: np.ndarray) -> None:
        """Append one RGB frame."""
        assert self._proc.stdin is not None
        self._proc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())

    def close(self) -> None:
        """Finish encoding.

        Raises:
            RuntimeError: ffmpeg exited with an error.
        """
        assert self._proc.stdin is not None
        self._proc.stdin.close()
        if self._proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
