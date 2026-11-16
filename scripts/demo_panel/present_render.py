"""Draw presentation-profile frames: header, stage strip, camera, zoom, terminal, captions.

Nothing is drawn on the camera image. The zoom inset is a crop of the same
native camera frame, scaled up and placed beside it, and labelled with its
zoom factor. The terminal pane shows only `PresentTranscript` items. Every
other text (header, stage strip, captions, legend, cards) is outside both.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from scripts.demo_panel.models import Transcript
from scripts.demo_panel.presentation import (
    STAGES,
    PresentScript,
    PresentTranscript,
    anchor_time,
    caption_at,
    caption_schedule,
    merged_caption_schedule,
    stage_at,
)
from scripts.demo_panel.render import PAGE_BG, TERM_BG, H264Writer, load_mono_font, wrap_text
from scripts.demo_panel.scene import CameraClipScene
from scripts.demo_panel.timeline import Timeline

SANS_FONT_CANDIDATES = (
    "Helvetica.ttc",
    "Arial.ttf",
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
)
MONO_BOLD_CANDIDATES = (("Menlo.ttc", 1), ("DejaVuSansMono-Bold.ttf", 0))
PRESENT_STYLES: dict[str, tuple[tuple[int, int, int], bool]] = {
    "m5": ((226, 226, 226), False),
    "m4": ((128, 196, 214), False),
    "warn": ((229, 192, 90), False),
    "command": ((112, 200, 112), False),
    "output": ((206, 206, 206), False),
    "marker": ((118, 118, 118), False),
    "dim": ((104, 104, 104), False),
    "decision": ((255, 221, 92), True),
    "action": ((132, 236, 142), True),
    "check": ((255, 170, 88), True),
}
CAPTION_YELLOW = (244, 214, 110)
TEXT = (232, 232, 232)
DIM = (160, 163, 168)
STAGE_ACTIVE_BG = (242, 200, 64)
STAGE_IDLE_BG = (52, 55, 60)
INTRO_SEC = 13.0
OUTRO_SEC = 10.0
PROVENANCE = (
    "Right: this run's own m5/m4 log files, replayed in sync with simulation time; the filter "
    "command is pinned at the top; '$' lines are read-only commands run on the run's files."
)


def load_sans_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a proportional font (bold face when available), falling back to monospace."""
    for name in SANS_FONT_CANDIDATES:
        try:
            if name.endswith(".ttc"):
                return ImageFont.truetype(name, size, index=1 if bold else 0)
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return load_mono_font(size)


def load_mono_bold(size: int, override: str | None = None) -> ImageFont.FreeTypeFont:
    """Load a bold monospace font with the same metrics as `load_mono_font`."""
    for name, idx in MONO_BOLD_CANDIDATES:
        try:
            return ImageFont.truetype(name, size, index=idx)
        except OSError:
            continue
    return load_mono_font(size, override)


@dataclass(frozen=True)
class PresentLayout:
    """Pixel layout of a presentation frame (1920x1080)."""

    width: int = 1920
    height: int = 1080
    strip_box: tuple[int, int, int, int] = (24, 86, 1872, 40)
    scene_box: tuple[int, int, int, int] = (24, 138, 640, 480)
    inset_box: tuple[int, int, int, int] = (24, 626, 384, 288)
    term_box: tuple[int, int, int, int] = (688, 138, 1208, 772)
    band_top: int = 918
    term_font_px: int = 20
    header_font_px: int = 14


def wrap_words(text: str, font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    """Word-wrap caption text to a pixel width (outside the terminal only)."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and font.getlength(trial) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_px: int,
    spacing: float = 1.25,
) -> int:
    """Draw word-wrapped text; return the y below it."""
    x, y = xy
    for ln in wrap_words(text, font, max_px):
        d.text((x, y), ln, font=font, fill=fill)
        y += int(font.size * spacing)
    return y


class PresentPane:
    """Terminal pane: pinned filter header in a small font, larger scrolling body."""

    def __init__(
        self,
        transcript: Transcript,
        size: tuple[int, int],
        body_px: int,
        header_px: int,
        font_override: str | None = None,
    ) -> None:
        """Prepare wrapped rows.

        Args:
            transcript: Items to show.
            size: Pane `(width, height)` in pixels.
            body_px: Body font size.
            header_px: Pinned header font size.
            font_override: Monospace font name/path to prefer.
        """
        self.size = size
        self.font = load_mono_font(body_px, font_override)
        self.bold = load_mono_bold(body_px, font_override)
        self.header_font = load_mono_font(header_px, font_override)
        self.pad = 10
        self.line_h = int(round(body_px * 1.27))
        self.header_line_h = int(round(header_px * 1.27))
        self.cols = max(20, int((size[0] - 2 * self.pad) // self.font.getlength("M")))
        hcols = max(20, int((size[0] - 2 * self.pad) // self.header_font.getlength("M")))
        self.header_rows = wrap_text(
            f"$ cd {transcript.bundle_name} && {transcript.filter_command}", hcols
        )
        self.items = transcript.items
        self.item_rows = [wrap_text(it.text, self.cols) for it in transcript.items]
        self.body_top = self.pad + len(self.header_rows) * self.header_line_h + 10
        self.body_rows = max(1, (size[1] - self.body_top - self.pad) // self.line_h)
        self._cache: tuple[int, Image.Image] | None = None

    def rows_of(self, index: int) -> int:
        """Screen rows used by item `index`."""
        return len(self.item_rows[index])

    def visible_rows(self, visible: int) -> list[tuple[int, str]]:
        """`(item index, row text)` on screen once the first `visible` items are printed."""
        rows: list[tuple[int, str]] = []
        for i in range(visible - 1, -1, -1):
            for r in reversed(self.item_rows[i]):
                rows.append((i, r))
            if len(rows) >= self.body_rows:
                break
        return list(reversed(rows[: self.body_rows]))

    def draw(self, visible: int) -> Image.Image:
        """Draw the pane with the first `visible` items printed."""
        if self._cache is not None and self._cache[0] == visible:
            return self._cache[1]
        img = Image.new("RGB", self.size, TERM_BG)
        d = ImageDraw.Draw(img)
        y = self.pad
        for row in self.header_rows:
            d.text((self.pad, y), row, font=self.header_font, fill=(96, 160, 96))
            y += self.header_line_h
        d.line([(self.pad, y + 4), (self.size[0] - self.pad, y + 4)], fill=(70, 70, 70), width=1)
        y = self.body_top
        for i, text in self.visible_rows(visible):
            color, bold = PRESENT_STYLES.get(self.items[i].style, ((206, 206, 206), False))
            d.text((self.pad, y), text, font=self.bold if bold else self.font, fill=color)
            y += self.line_h
        self._cache = (visible, img)
        return img


@dataclass(frozen=True)
class ZoomWindow:
    """A resolved zoom: take-time window and native crop."""

    t0: float
    t1: float
    crop: tuple[int, int, int, int]


def zoom_factor(crop_w: int, inset_w: int, scene_w: int, frame_w: int) -> float:
    """Zoom of the inset relative to the full camera view shown beside it."""
    return (inset_w / crop_w) / (scene_w / frame_w)


def validate_crop(crop: tuple[int, int, int, int], frame_size: tuple[int, int]) -> None:
    """Check a crop lies inside the frame and is 4:3.

    Raises:
        ValueError: The crop is outside the frame or not 4:3 within 1 %.
    """
    x, y, w, h = crop
    fw, fh = frame_size
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > fw or y + h > fh:
        raise ValueError(f"zoom crop {crop} outside the {fw}x{fh} frame")
    if abs(w / h - 4 / 3) > 0.01 * 4 / 3:
        raise ValueError(f"zoom crop {crop} is not 4:3")


class PresentCompositor:
    """Composes intro card, take frames and outro card for one presentation video."""

    def __init__(
        self,
        pt: PresentTranscript,
        timeline: Timeline,
        scene: CameraClipScene,
        pane: PresentPane,
        script: PresentScript,
        layout: PresentLayout | None = None,
    ) -> None:
        """Resolve anchors and prepare fonts.

        Args:
            pt: Presentation transcript.
            timeline: Its timeline (take time, intro excluded).
            scene: Camera clip.
            pane: Terminal pane built for `pt.transcript`.
            script: Captions, cards, zooms.
            layout: Pixel layout.

        Raises:
            ValueError: An anchor does not resolve, a zoom crop is invalid, or
                the header and the disclosure do not fit on one line.
        """
        self.pt = pt
        self.tl = timeline
        self.scene = scene
        self.pane = pane
        self.script = script
        self.lay = layout if layout is not None else PresentLayout()
        self.texts = [it.text for it in pt.transcript.items]
        self.end_t = max(0.0, timeline.total_video_sec - 2.0)
        vs = timeline.video_at_sim
        self.schedule = merged_caption_schedule(
            caption_schedule(script.captions, self.texts, timeline.reveal, self.end_t, vs),
            self.texts,
            timeline.reveal,
        )
        self.outcome_t = anchor_time(script.outcome.at, self.texts, timeline.reveal, self.end_t, vs)
        self.zooms: list[ZoomWindow] = []
        for z in script.zooms:
            validate_crop(z.crop, scene.frame_size)
            t0 = anchor_time(z.start, self.texts, timeline.reveal, self.end_t, vs)
            t1 = anchor_time(z.stop, self.texts, timeline.reveal, self.end_t, vs)
            self.zooms.append(ZoomWindow(t0, t1, z.crop))
        self.f_title = load_sans_font(30, bold=True)
        self.f_clock = load_mono_font(20)
        self.f_disc = load_sans_font(17)
        self.f_strip = load_sans_font(20, bold=True)
        self.f_label = load_sans_font(16)
        self.f_cap = load_sans_font(25, bold=True)
        self.f_outcome = load_sans_font(23, bold=True)
        self.f_small = load_sans_font(16)
        free = self.lay.width - 48 - self.f_title.getlength(script.header) - 40
        if self.f_disc.getlength(script.disclosure) > free:
            raise ValueError("header and disclosure overlap; shorten one of them")
        self._intro = self._card(intro=True)
        self._outro = self._card(intro=False)

    @property
    def total_sec(self) -> float:
        """Video length: intro card, the take, outro card."""
        return INTRO_SEC + self.tl.total_video_sec + OUTRO_SEC

    def zoom_at(self, take_t: float) -> ZoomWindow | None:
        """Zoom window active at a take time, if any."""
        for z in self.zooms:
            if z.t0 <= take_t < z.t1:
                return z
        return None

    def frame(self, video_t: float) -> np.ndarray:
        """RGB frame at a video time (intro, take or outro)."""
        if video_t < INTRO_SEC:
            return self._intro
        take_t = video_t - INTRO_SEC
        if take_t >= self.tl.total_video_sec:
            return self._outro
        return self.take_frame(take_t)

    def take_frame(self, t: float) -> np.ndarray:
        """RGB frame at a take time (intro excluded)."""
        lay = self.lay
        sim = self.tl.sim_at(t)
        img = Image.new("RGB", (lay.width, lay.height), PAGE_BG)
        d = ImageDraw.Draw(img)
        d.text((24, 10), self.script.header, font=self.f_title, fill=TEXT)
        d.text(
            (24, 52),
            f"sim t = {sim:7.2f} s   |   speed: {self.tl.caption_at(t)}",
            font=self.f_clock,
            fill=CAPTION_YELLOW,
        )
        disc_w = self.f_disc.getlength(self.script.disclosure)
        d.text((lay.width - 24 - disc_w, 18), self.script.disclosure, font=self.f_disc, fill=DIM)
        self._strip(d, stage_at(t, self.tl.reveal, self.pt.stages, self.pt.ends_cycle))
        sx, sy, sw, sh = lay.scene_box
        img.paste(Image.fromarray(self.scene.frame_at(sim, (sw, sh))), (sx, sy))
        ix, iy, iw, _ = lay.inset_box
        lx = ix + iw + 14
        y_lab = draw_text_block(
            d, (lx, iy), self.script.camera_label, self.f_label, DIM, sx + sw - lx
        )
        z = self.zoom_at(t)
        if z is not None:
            self._inset(img, d, z, sim, (lx, y_lab + 10))
        n = self.tl.visible_count(t)
        tx, ty, _, _ = lay.term_box
        img.paste(self.pane.draw(n), (tx, ty))
        y = lay.band_top
        cap = caption_at(self.schedule, t)
        if cap:
            y = draw_text_block(d, (24, y), cap, self.f_cap, CAPTION_YELLOW, lay.width - 48, 1.2)
        else:
            y += int(self.f_cap.size * 1.2)
        if t + 1e-9 >= self.outcome_t:
            y = draw_text_block(
                d, (24, y + 2), self.script.outcome.text, self.f_outcome, TEXT, lay.width - 48, 1.2
            )
        y = draw_text_block(d, (24, y + 4), self.script.legend, self.f_small, DIM, lay.width - 48)
        draw_text_block(d, (24, y + 2), PROVENANCE, self.f_small, DIM, lay.width - 48)
        return np.asarray(img)

    def _strip(self, d: ImageDraw.ImageDraw, active: str | None) -> None:
        x0, y0, w, h = self.lay.strip_box
        gap = 34
        bw = (w - gap * (len(STAGES) - 1)) / len(STAGES)
        for k, name in enumerate(STAGES):
            bx = x0 + k * (bw + gap)
            on = name == active
            d.rounded_rectangle(
                [bx, y0, bx + bw, y0 + h], radius=8, fill=STAGE_ACTIVE_BG if on else STAGE_IDLE_BG
            )
            label = f"{k + 1}  {name}"
            lw = self.f_strip.getlength(label)
            d.text(
                (bx + (bw - lw) / 2, y0 + (h - self.f_strip.size) / 2 - 2),
                label,
                font=self.f_strip,
                fill=(24, 24, 24) if on else (150, 152, 156),
            )
            if k < len(STAGES) - 1:
                ax = bx + bw + gap / 2
                d.text((ax - 6, y0 + 6), "›", font=self.f_strip, fill=(150, 152, 156))

    def _inset(
        self,
        img: Image.Image,
        d: ImageDraw.ImageDraw,
        z: ZoomWindow,
        sim: float,
        label_xy: tuple[int, int],
    ) -> None:
        ix, iy, iw, ih = self.lay.inset_box
        frame = self.scene.native_frame_at(sim)
        if frame is None:
            return
        x, y, w, h = z.crop
        crop = cv2.resize(frame[y : y + h, x : x + w], (iw, ih), interpolation=cv2.INTER_LINEAR)
        img.paste(Image.fromarray(crop), (ix, iy))
        sw = self.lay.scene_box[2]
        n = zoom_factor(w, iw, sw, self.scene.frame_size[0])
        label = (
            f"Zoom (at left) ×{n:.1f} of the camera view: a crop of the same camera frame, "
            "enlarged so the robot ids can be read. Nothing is drawn on it."
        )
        lx, ly = label_xy
        draw_text_block(
            d, (lx, ly), label, self.f_label, CAPTION_YELLOW, self.lay.scene_box[0] + sw - lx
        )

    def _card(self, intro: bool) -> np.ndarray:
        lay = self.lay
        img = Image.new("RGB", (lay.width, lay.height), PAGE_BG)
        d = ImageDraw.Draw(img)
        s = self.script
        x, w = 150, lay.width - 300
        y = 120
        title = s.intro_title if intro else s.outro_title
        y = draw_text_block(d, (x, y), title, load_sans_font(46, True), CAPTION_YELLOW, w) + 18
        body = load_sans_font(29)
        for ln in s.intro_lines if intro else s.outro_lines:
            y = draw_text_block(d, (x, y), ln, body, TEXT, w) + 12
        if intro:
            y += 10
            y = (
                draw_text_block(
                    d, (x, y), "Things to watch for:", load_sans_font(29, True), TEXT, w
                )
                + 4
            )
            for k, ln in enumerate(s.watch_for, 1):
                y = draw_text_block(d, (x + 30, y), f"{k}. {ln}", body, TEXT, w - 30) + 6
            y += 14
            strip = "The strip at the top marks the stage: " + "  ›  ".join(STAGES) + "."
            y = draw_text_block(d, (x, y), strip, load_sans_font(24), DIM, w) + 8
        draw_text_block(
            d, (x, max(y + 16, lay.height - 120)), s.disclosure, load_sans_font(26), DIM, w
        )
        return np.asarray(img)


def still_times(comp: PresentCompositor, key_request: str | None) -> dict[str, float]:
    """Video times for named stills: intro, trigger, response, check, dispatch, mid, outcome, outro.

    The key decision is `key_request` (8-hex prefix) or the first decision
    whose block has a `check` item followed by a dispatch.
    """
    pt, tl = comp.pt, comp.tl
    tags, items = pt.tags, pt.transcript.items
    reqs = [t.split(":", 1)[0] for t in tags if ":" in t]
    key = key_request
    if key is None:
        key = next((r[:8] for r in reqs if f"{r}:check" in tags), reqs[0][:8] if reqs else "")
    out: dict[str, float] = {"intro": INTRO_SEC / 2}

    def first(pred) -> int | None:
        return next((i for i, it in enumerate(items) if pred(i, it)), None)

    trig = first(lambda i, it: "starting analysis" in it.text and f"request={key}" in it.text)
    resp = [i for i, tg in enumerate(tags) if tg.startswith(key) and tg.endswith(":response")]
    chk = [
        i
        for i, tg in enumerate(tags)
        if (tg.startswith(key) and tg.endswith(":check"))
        or (tg == "log" and pt.stages[i] == "Check" and f"request={key}" in items[i].text)
    ]
    disp = first(lambda i, it: "dispatch request=" in it.text and f"request={key}" in it.text)
    if trig is not None:
        out["trigger"] = INTRO_SEC + tl.reveal[trig] + 0.8
    if resp:
        out["response"] = INTRO_SEC + tl.reveal[resp[-1]] + 3.0
    if chk:
        out["check"] = INTRO_SEC + tl.reveal[chk[-1]] + 2.0
    if disp is not None:
        j = min(disp + 6, len(items) - 1)
        out["dispatch"] = INTRO_SEC + tl.reveal[j] + 0.2
    out["mid"] = INTRO_SEC + (comp.outcome_t + (tl.reveal[disp] if disp is not None else 0)) / 2
    out["outcome"] = INTRO_SEC + min(comp.outcome_t + 1.0, tl.total_video_sec - 0.1)
    out["outro"] = comp.total_sec - OUTRO_SEC / 2
    return out


def render_present(comp: PresentCompositor, out: Path, fps: float, crf: int = 23) -> float:
    """Encode one presentation video.

    Args:
        comp: The compositor.
        out: Output MP4.
        fps: Frame rate.
        crf: x264 quality.

    Returns:
        Duration in seconds.
    """
    w = H264Writer(out, (comp.lay.width, comp.lay.height), fps, crf)
    n = int(comp.total_sec * fps + 0.999)
    try:
        for i in range(n):
            w.write(comp.frame(i / fps))
    finally:
        w.close()
    return n / fps


def save_present_stills(comp: PresentCompositor, out: Path, key: str | None) -> list[Path]:
    """Write named PNG stills beside the video."""
    paths = []
    for name, t in still_times(comp, key).items():
        p = out.with_name(f"{out.stem}_{name}.png")
        Image.fromarray(comp.frame(t)).save(p)
        paths.append(p)
    return paths


def visible_item_indices(pane: PresentPane, tl: Timeline, take_t: float) -> set[int]:
    """Item indices with at least one row on screen at a take time."""
    return {i for i, _ in pane.visible_rows(tl.visible_count(take_t))}


def hold_windows(tl: Timeline, holds: Sequence[float]) -> list[tuple[int, float, float]]:
    """`(item, start, end)` take-time windows of each clock hold after an item."""
    out = []
    for i, h in enumerate(holds):
        if h > 0:
            end = tl.reveal[i + 1] if i + 1 < len(tl.reveal) else tl.total_video_sec
            out.append((i, tl.reveal[i], end))
    return out
