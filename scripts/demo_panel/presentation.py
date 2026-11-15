"""Presentation profile: a shorter, staged terminal for showing a run to an audience.

The terminal content follows the same rules as the engineering profile
(`terminal.py`): only lines printed by commands that are themselves shown,
run for real on the bundle's files. What changes:

1. The filter adds M5's check lines (`yield re-grounded`, `yield refused`,
   `refusal withheld`) and ends in a displayed `sed -E` stage that shortens
   each line: the `[proc] [LEVEL] [wall] [name_node]: ` prefix becomes
   `name: ` and every 32-hex id keeps its first 8 characters. `sed` maps one
   line to one line, so the renderer also runs the filter without the `sed`
   stage and pairs the two outputs by index: the stamped original times and
   collapses the line, the shortened one is what is shown.
2. The decision block prints the model's plan (or its `yield_robot`), and the
   check verdict, and proves the image input (`file -b` on the frame M5 sent).
   `dispatched_robot_ids` is no longer printed (it reads as the model's order
   but holds the first phase's recipients, and is filled for withheld decisions).
3. Each item gets a stage (Trigger, VLM request, VLM response, Check,
   Dispatch, Execution) from fixed log anchors and block roles, and holds
   (sim clock paused) after the model's answer and after the check verdict.

Captions, the stage strip, the zoom inset and the intro/outro cards are drawn
outside the terminal (`present_render.py`) from a per-video script
(`PresentScript`), whose captions are revealed only when their anchor line
is printed.
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.demo_panel.bundle import Bundle, TimeContext
from scripts.demo_panel.models import Transcript
from scripts.demo_panel.terminal import (
    FILTER_PATTERN,
    LOG_FILES,
    BlockCommand,
    collect_items,
    run_shell,
)

GATE_PATTERN = "yield re-grounded|yield refused|refusal withheld"
PRESENT_FILTER_PATTERN = f"{FILTER_PATTERN}|{GATE_PATTERN}"
SHORTEN_SED = (
    r"s/^\[[^]]+\] \[[A-Z]+\] \[[0-9.]+\] \[([a-z_]+)_node\]: /\1: /; "
    r"s/([0-9a-f]{8})[0-9a-f]{24}/\1/g"
)
_PREFIX_RX = re.compile(r"^\[[^\]]+\] \[[A-Z]+\] \[[0-9.]+\] \[([a-z_]+)_node\]: ")
_ID_RX = re.compile(r"([0-9a-f]{8})[0-9a-f]{24}")

STAGES = ("Trigger", "VLM request", "VLM response", "Check", "Dispatch", "Execution")
TRIGGER_SEC = 1.5
DISPATCH_SEC = 3.0
IDLE_AFTER_SEC = 4.0
RESPONSE_HOLD_SEC = 7.0
CHECK_HOLD_SEC = 4.0
NO_CONGESTION_HOLD_SEC = 2.5
RESPONSE_CAPTION = "PAUSED (sim clock held) so the model's answer can be read"
CHECK_CAPTION = "PAUSED (sim clock held) so the check result can be read"

_DISPATCH_RX = re.compile(r"dispatch request=|command received")
_EXEC_RX = re.compile(r"crossing_chain|phase advance")
_CHECK_RX = re.compile(GATE_PATTERN + r"|no dispatch")
_END_CHECK_RX = re.compile(r"no dispatch|refusal withheld")
_REQ_IN_LINE = re.compile(r"request=([0-9a-f]{8})")


def raw_filter_command() -> str:
    """The presentation filter without its `sed` stage (stamped originals, for timing)."""
    files = " ".join(LOG_FILES)
    return f"grep -hE {shlex.quote(PRESENT_FILTER_PATTERN)} {files} | sort -s -t'[' -k4,4n"


def present_filter_command() -> str:
    """The displayed filter: `raw_filter_command()` piped through the shortening `sed`."""
    return f"{raw_filter_command()} | sed -E {shlex.quote(SHORTEN_SED)}"


def shorten_line(line: str) -> str:
    """Pure-Python equivalent of the `sed` stage, used to cross-check it in tests."""
    return _ID_RX.sub(r"\1", _PREFIX_RX.sub(r"\1: ", line, count=1))


def present_style(raw: str, shown: str) -> str:
    """Colour class of a shown log line.

    Safety-latch lines are dim (they are M4 holding stopped robots, not
    errors); commands reaching a robot (`action=`) and M5's check lines are
    highlighted; other lines keep the orchestrator/robot-side colours.
    """
    if "safety stop" in shown:
        return "dim"
    if "action=" in shown:
        return "action"
    if _CHECK_RX.search(shown):
        return "check"
    if shown.startswith("orchestrator:"):
        return "m5"
    return "m4"


def _artifact_arg(b: Bundle, request_id: str, folder: str, suffix: str) -> str:
    short = f"{folder}/{request_id[:8]}*{suffix}"
    matches = sorted((b.root / folder).glob(f"{request_id[:8]}*{suffix}"))
    if len(matches) == 1 and matches[0].name == f"{request_id}{suffix}":
        return short
    return f"{folder}/{request_id}{suffix}"


def _null_safe_join(field: str) -> str:
    return f'\\({field} | if . then join(", ") else . end)'


def present_block(b: Bundle, request_id: str, dec: dict[str, Any]) -> list[BlockCommand]:
    """Read-only commands printed at one decision, grouped by stage role.

    Roles: `request` (the prompt's first line; the image file M5 sent),
    `response` (model call, decision, and the plan or yield choice), `check`
    (plan verification and order source, or the yield gate's fields).
    Commands are chosen per artifact by which fields it holds, so `jq` never
    fails on a missing or null field; a null value is printed as `null`.

    Args:
        b: Loaded bundle (for resolving file globs).
        request_id: Full request id.
        dec: The decision artifact.

    Returns:
        Commands in display order.
    """
    f = _artifact_arg(b, request_id, "decisions", ".json")
    cmds = [BlockCommand(f"jq -r .prompt.user_prompt {f} | head -n 1", "request")]
    if (b.root / "frames" / f"{request_id}.png").is_file():
        cmds.append(BlockCommand(f"file -b frames/{request_id}.png", "request"))
    diag = dec.get("diagnostics") or {}
    fields = "served_model, latency_ms, attempts"
    if isinstance(diag.get("token_usage"), dict) and "input_tokens_image" in diag["token_usage"]:
        fields += ", image_tokens: .token_usage.input_tokens_image"
    cmds.append(BlockCommand(f"jq -c '.diagnostics | {{{fields}}}' {f}", "response"))
    cmds.append(
        BlockCommand(
            "jq -r '.decision | \"strategy=\\(.strategy) involved=\\(.involved_robots | "
            f'join(","))", .justification\' {f}',
            "response",
            "decision",
        )
    )
    decision = dec.get("decision") or {}
    if decision.get("congestion_detected") is False:
        return cmds
    has_plan = dec.get("plan") is not None
    if has_plan:
        plan = (
            '"plan: \\(.proposed_plan | if . then map(.robot_id + " " + .action) | '
            'join(", ") else . end)"'
        )
    else:
        plan = '"yield_robot: \\(.yield_robot)"'
    cmds.append(
        BlockCommand(
            f"jq -r '.decision | {plan}, \"crossing_order: "
            f"{_null_safe_join('.crossing_order')}\"' {f}",
            "response",
            "decision",
        )
    )
    order = (
        " dispatch_order_source=\\(.dispatch_order_source)"
        if "dispatch_order_source" in dec
        else ""
    )
    if has_plan:
        check = (
            f"jq -r '\"provenance=\\(.plan.provenance) "
            f"reason=\\(.plan.rejection_reason){order}\"' {f}"
        )
        cmds.append(BlockCommand(check, "check", "check"))
    elif "yield_robot_grounded_from" in dec:
        keys = "yield_robot_grounded_from"
        if order:
            keys += ", dispatch_order_source"
        cmds.append(BlockCommand(f"jq -c '{{{keys}}}' {f}", "check", "check"))
    return cmds


class PresentTranscript(BaseModel):
    """A presentation transcript: the terminal items plus per-item stage tags and holds."""

    model_config = ConfigDict(frozen=True)

    transcript: Transcript
    raw_filter_command: str
    tags: tuple[str, ...]
    stages: tuple[str | None, ...] = Field(description="stage anchored by each item, or None")
    ends_cycle: tuple[bool, ...] = Field(description="item ends a decision without dispatch")
    holds: tuple[float, ...]
    hold_captions: tuple[str, ...]


def item_stage(tag: str, text: str) -> tuple[str | None, bool]:
    """Stage anchored by one terminal item, and whether it ends the cycle without dispatch.

    Mapping (log anchors, then block roles; other items keep the current stage):

    - `starting analysis` -> Trigger (shown as VLM request after `TRIGGER_SEC`)
    - `decision artifact written` and `request` commands -> VLM request
    - `response` commands -> VLM response
    - `check` commands, `yield re-grounded`, `yield refused` -> Check
    - `no dispatch`, `refusal withheld` -> Check, ending the cycle (idle later)
    - `dispatch request=`, `command received` -> Dispatch (shown as Execution
      `DISPATCH_SEC` after the last one)
    - `crossing_chain`, `phase advance` -> Execution (arrivals anchor nothing:
      one can land while a new model call is in flight)

    Args:
        tag: Item tag from `collect_items` (`log`, `marker`, `poll`, `<req>:<role>`).
        text: Shown text.

    Returns:
        `(stage or None, ends_cycle)`.
    """
    if tag == "log":
        if "starting analysis" in text:
            return "Trigger", False
        if "decision artifact written" in text:
            return "VLM request", False
        if _END_CHECK_RX.search(text):
            return "Check", True
        if _CHECK_RX.search(text):
            return "Check", False
        if _DISPATCH_RX.search(text):
            return "Dispatch", False
        if _EXEC_RX.search(text):
            return "Execution", False
        return None, False
    role = tag.split(":", 1)[1] if ":" in tag else ""
    return {"request": "VLM request", "response": "VLM response", "check": "Check"}.get(role), False


def compute_holds(
    items: Sequence[Any], tags: Sequence[str], decisions: dict[str, tuple[str, dict[str, Any]]]
) -> tuple[list[float], list[str]]:
    """Clock holds after the model's answer and after the check verdict, per decision.

    The response hold follows the last `response` item of a decision block;
    the check hold follows the last check item: the block's `check` command
    output, or a later M5 check line of the same request (`yield
    re-grounded`, `yield refused`, `refusal withheld`, `no dispatch`)
    printed before the next block or dispatch. A decision the model answered
    with `congestion_detected=false` gets short holds.

    Args:
        items: Terminal items.
        tags: Their tags.
        decisions: Bundle decisions by full request id.

    Returns:
        `(hold seconds, hold caption)` per item.
    """
    holds = [0.0] * len(items)
    caps = [""] * len(items)
    last_resp: dict[str, int] = {}
    last_check: dict[str, int] = {}
    short_of: dict[str, bool] = {}
    for i, tag in enumerate(tags):
        if ":" in tag:
            req, role = tag.split(":", 1)
            key = req[:8]
            dec = decisions.get(req, ("", {}))[1]
            short_of[key] = (dec.get("decision") or {}).get("congestion_detected") is False
            if role == "response":
                last_resp[key] = i
            elif role == "check":
                last_check[key] = i
        elif tag == "log" and _CHECK_RX.search(items[i].text):
            m = _REQ_IN_LINE.search(items[i].text)
            if m and m.group(1) in short_of:
                last_check[m.group(1)] = i
    for key, i in last_resp.items():
        holds[i] = NO_CONGESTION_HOLD_SEC if short_of.get(key) else RESPONSE_HOLD_SEC
        caps[i] = RESPONSE_CAPTION
    for key, i in last_check.items():
        holds[i] = NO_CONGESTION_HOLD_SEC if short_of.get(key) else CHECK_HOLD_SEC
        caps[i] = CHECK_CAPTION
    return holds, caps


def build_present_transcript(b: Bundle, tc: TimeContext, sim_end: float) -> PresentTranscript:
    """Build the presentation transcript for a bundle.

    Args:
        b: Loaded bundle.
        tc: Its wall-to-sim mapping.
        sim_end: Last sim second of the episode.

    Returns:
        The transcript with stages and holds.

    Raises:
        ValueError: The `sed` stage changed the number of lines.
    """
    raw_cmd = raw_filter_command()
    shown_cmd = present_filter_command()
    raw = run_shell(raw_cmd, b.root)
    shown = run_shell(shown_cmd, b.root)
    parts = collect_items(
        b,
        tc,
        raw,
        shown,
        lambda req, dec: present_block(b, req, dec),
        present_style,
        poll_style="dim",
    )
    pairs = [item_stage(t, it.text) for t, it in zip(parts.tags, parts.items, strict=True)]
    stages = [s for s, _ in pairs]
    ends = [e for _, e in pairs]
    holds, caps = compute_holds(parts.items, parts.tags, b.decisions)
    transcript = Transcript(
        bundle_name=b.name,
        bundle_dir=str(b.root),
        filter_command=shown_cmd,
        items=tuple(parts.items),
        calls=tuple(parts.calls),
        blocks=tuple(parts.blocks),
        time_map=tc.info,
        sim_end=sim_end,
    )
    return PresentTranscript(
        transcript=transcript,
        raw_filter_command=raw_cmd,
        tags=tuple(parts.tags),
        stages=tuple(stages),
        ends_cycle=tuple(ends),
        holds=tuple(holds),
        hold_captions=tuple(caps),
    )


def stage_at(
    video_t: float, reveal: Sequence[float], stages: Sequence[str | None], ends: Sequence[bool]
) -> str | None:
    """Stage highlighted on the strip at a video time.

    The stage is the one anchored by the last revealed item that anchors one.
    A Trigger becomes VLM request `TRIGGER_SEC` after it is revealed, a
    Dispatch becomes Execution `DISPATCH_SEC` after, and a cycle that ended
    without dispatch goes idle (None) `IDLE_AFTER_SEC` after.

    Args:
        video_t: Video time within the take (excluding the intro card).
        reveal: Reveal time of each item.
        stages: Stage anchored by each item.
        ends: Whether each item ends a cycle without dispatch.

    Returns:
        A name from `STAGES`, or None before the first trigger and when idle.
    """
    for i in range(len(reveal) - 1, -1, -1):
        if reveal[i] > video_t + 1e-9 or stages[i] is None:
            continue
        age = video_t - reveal[i]
        if stages[i] == "Trigger" and age > TRIGGER_SEC:
            return "VLM request"
        if stages[i] == "Dispatch" and age > DISPATCH_SEC:
            return "Execution"
        if ends[i] and age > IDLE_AFTER_SEC:
            return None
        return stages[i]
    return None


class Anchor(BaseModel):
    """When a caption or zoom starts or ends.

    Exactly one of: `match` (regex searched in shown terminal text; the
    `nth` match, 1-based), `sim` (the first moment the sim clock reaches
    that second, for facts with no log line, taken from the campaign
    report), `start` (video start of the take) or `end` (the end-of-episode
    hold, after the last line).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    match: str | None = None
    nth: int = Field(default=1, ge=1)
    sim: float | None = None
    start: bool = False
    end: bool = False

    @model_validator(mode="after")
    def _one_kind(self) -> Anchor:
        kinds = (self.match is not None, self.sim is not None, self.start, self.end)
        if sum(kinds) != 1:
            raise ValueError("anchor needs exactly one of match / sim / start / end")
        return self


class Caption(BaseModel):
    """A caption line revealed at its anchor and kept until the next one."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    at: Anchor
    text: str = Field(min_length=1)


class Zoom(BaseModel):
    """A zoomed crop of the real camera frame shown beside it between two anchors.

    `crop` is `[x, y, w, h]` in the camera's native pixels, aspect 4:3.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: Anchor
    stop: Anchor
    crop: tuple[int, int, int, int]


class PresentScript(BaseModel):
    """Everything drawn outside the terminal for one presentation video."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    header: str = Field(min_length=1)
    camera_label: str = Field(min_length=1)
    intro_title: str = Field(min_length=1)
    intro_lines: list[str] = Field(min_length=1)
    watch_for: list[str] = Field(min_length=1, max_length=3)
    captions: list[Caption] = Field(min_length=1)
    outcome: Caption
    legend: str = Field(min_length=1)
    disclosure: str = Field(min_length=1)
    outro_title: str = Field(min_length=1)
    outro_lines: list[str] = Field(min_length=1)
    zooms: list[Zoom] = []
    key_request: str | None = None
    outcome_kind: Literal["VLM-driven execution", "M3-default resolution", "Unresolved failure"]


def load_script(path: Path) -> PresentScript:
    """Read and validate a presentation script JSON."""
    return PresentScript.model_validate(json.loads(path.read_text()))


def anchor_time(
    anchor: Anchor,
    texts: Sequence[str],
    reveal: Sequence[float],
    end_t: float,
    video_at_sim: Callable[[float], float] | None = None,
) -> float:
    """Video time (within the take) at which an anchor fires.

    Args:
        anchor: The anchor.
        texts: Shown text of each item.
        reveal: Reveal time of each item.
        end_t: Start of the end-of-episode hold.
        video_at_sim: Sim-to-video map (required for `sim` anchors).

    Returns:
        The time.

    Raises:
        ValueError: A `match` anchor has fewer than `nth` matches, or a `sim`
            anchor has no sim-to-video map.
    """
    if anchor.start:
        return 0.0
    if anchor.sim is not None:
        if video_at_sim is None:
            raise ValueError("sim anchor needs a timeline")
        return video_at_sim(anchor.sim)
    if anchor.end:
        return end_t
    rx = re.compile(anchor.match or "")
    hits = [reveal[i] for i, t in enumerate(texts) if rx.search(t)]
    if len(hits) < anchor.nth:
        raise ValueError(f"anchor {anchor.match!r} #{anchor.nth}: only {len(hits)} match(es)")
    return hits[anchor.nth - 1]


def caption_schedule(
    captions: Sequence[Caption],
    texts: Sequence[str],
    reveal: Sequence[float],
    end_t: float,
    video_at_sim: Callable[[float], float] | None = None,
) -> list[tuple[float, str]]:
    """Caption start times, sorted; each caption shows until the next starts.

    Raises:
        ValueError: An anchor does not resolve.
    """
    return sorted((anchor_time(c.at, texts, reveal, end_t, video_at_sim), c.text) for c in captions)


def caption_at(schedule: Sequence[tuple[float, str]], video_t: float) -> str:
    """The caption showing at a video time (empty before the first)."""
    text = ""
    for t0, t in schedule:
        if t0 <= video_t + 1e-9:
            text = t
    return text


_TRIGGER_REASON = re.compile(r"starting analysis request=\S+ robots=\[[^\]]*\] reason=(.*?) order=")


def trigger_caption(text: str) -> str | None:
    """Generic caption for a `starting analysis` line, or None for other lines.

    It restates the line's own trigger reason in plain words, so a script
    caption from an earlier decision never stays on screen into a new one.
    """
    m = _TRIGGER_REASON.search(text)
    if m is None:
        return None
    reason = m.group(1).replace(">=", "for at least").replace("12.0s", "12 s")
    return (
        f"Trigger: {reason}. The system asks the model again, sending a text prompt "
        "and the current camera image."
    )


_REFUSED = re.compile(r"yield refused request=\S+ reason=yield refused: (.*)$")


def generic_caption(text: str) -> str | None:
    """Generic caption for a trigger, refusal or no-congestion line, else None.

    Each restates only the line's own content, so a script caption from an
    earlier step never stays on screen over a newer one.
    """
    cap = trigger_caption(text)
    if cap is not None:
        return cap
    m = _REFUSED.search(text)
    if m is not None:
        return f"Check: a grounding check refused this proposal ('{m.group(1)}')."
    if "no dispatch" in text and "congestion_detected=false" in text:
        return "The model answered 'no congestion', so nothing is sent."
    return None


def merged_caption_schedule(
    schedule: Sequence[tuple[float, str]], texts: Sequence[str], reveal: Sequence[float]
) -> list[tuple[float, str]]:
    """Add a generic caption at each trigger, refusal or no-congestion line left uncovered.

    A script caption anchored at (or after) the same moment wins.
    """
    starts = [t0 for t0, _ in schedule]
    out = list(schedule)
    for i, text in enumerate(texts):
        cap = generic_caption(text)
        if cap is None:
            continue
        nxt = next((t0 for t0 in starts if t0 >= reveal[i] - 1e-9), None)
        if nxt is not None and nxt <= reveal[i] + 1e-9:
            continue
        out.append((reveal[i], cap))
    return sorted(out, key=lambda x: x[0])
