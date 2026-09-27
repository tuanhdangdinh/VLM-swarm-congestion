"""Offline replay of live M5 decisions against their real annotated camera frames.

The Arm A pilot runs stored, for every M2 analysis, the exact scene snapshot, the
rendered prompt with its SHA-256, the presentation order, and the PNG frame that
was actually sent. This probe rebuilds each `ReasonerRequest` through the
production `build_reasoner_request` / `build_prompt_payload` path, asserts the
rendered prompt is byte-identical to the stored one, and then re-sends it through
the shipped `Reasoner` with the real frame.

Six arms:

* ``R``    — every reconstructable artifact, stored order, real frame. Measures the
  attempt-1 refusal rate against the live rate on the same stimuli.
* ``grey`` — the live-refused artifacts and matched live-valid ones, same prompts,
  with a neutral grey image of identical dimensions. Isolates the image channel.
* ``O``    — the first-yield artifact of each run under both presentation orders.
  Measures order sensitivity on real stimuli.
* ``M``    — retry-policy comparison on the artifacts that refused in Arm R.
* ``S``    — the genuine-standoff artifacts under a fully crossed
  order x obstacle-text x image design. Arm O found that under ``id_desc`` the
  yielder choice tracks the obstacle side; this arm asks which input channel
  carries that side signal.
* ``D``    — the live-refused artifacts at full resolution against a 640 px-wide
  downscale. Asks whether image resolution moves the attempt-1 refusal rate.
* ``S2``   — Arm S's design re-run on the pilot batch-2 standoffs. The
  replication that decides whether the obstacle-text finding holds on twelve
  scenes rather than six.
* ``F``    — every batch-2 artifact under its annotated frame against the raw
  camera frame dumped beside it, paired per artifact. Asks whether the M1
  overlay, rather than the scene it is drawn on, carries the refusal trigger.
* ``X``    — the batch-2 live-refused artifacts under the four-attempt retry
  policy with and without the neutral-image fallback
  (`ReasonerConfig.image_fallback_after_attempts`). Measures what the mitigation
  buys on terminal refusal, and whether a fallback decision agrees with the
  decision the same scene produces with the frame still attached.

Production code is imported, never modified. `Reasoner.run` keeps only the last
attempt's text, so a recording proxy wraps the backend to capture every attempt;
the retry/re-ask logic itself stays byte-exact. The proxy also owns rate pacing
(per API call, not per `Reasoner.run`), 429 back-off, and the auth abort.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (REPO_ROOT, REPO_ROOT / "ros2_ws/src/swarm_orchestrator"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from swarm_orchestrator.models import SceneSnapshot  # noqa: E402
from swarm_orchestrator.reasoning_pipeline import build_reasoner_request  # noqa: E402

from reasoning.vlm.backend_base import VLMBackend  # noqa: E402
from reasoning.vlm.backend_factory import (  # noqa: E402
    backend_section,
    build_backend,
    resolve_reasoner_config,
)
from reasoning.vlm.errors import DecisionValidationError, VLMOutputParseError  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    FailureContext,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotPresentationOrder,
    StaticObstacleInput,
)
from reasoning.vlm.output_parser import parse_decision_text  # noqa: E402
from reasoning.vlm.prompt_builder import (  # noqa: E402
    build_prompt_payload,
    format_pairwise_geometry_lines,
)
from reasoning.vlm.reasoner import Reasoner  # noqa: E402

RUNS_DIR = REPO_ROOT / "data/logs/vm_runs"
OUT_DIR = REPO_ROOT / "data/experiments/2026-09-25-frame-replay"
MODELS_YAML = REPO_ROOT / "config/models.yaml"

PILOT_RUNS: tuple[str, ...] = (
    "20260925_063520",
    "20260925_065143",
    "20260925_070637",
    "20260925_072130",
    "20260925_073621",
    "20260925_075116",
)

# Pilot batch 2 (2026-09-25 afternoon): Q1-Q3 west-blocked (`w0p2_eopen`,
# obstacle x = -1.85, drew `id_desc`), Q4-Q6 east-blocked (`wopen_e0p2`,
# x = +1.85, drew `id_asc`). Every decision also stored the raw camera frame.
PILOT2_RUNS: tuple[str, ...] = (
    "20260925_155433",
    "20260925_160951",
    "20260925_162451",
    "20260925_163949",
    "20260925_165442",
    "20260925_170938",
)

RUN_SETS: dict[str, tuple[str, ...]] = {
    "batch1": PILOT_RUNS,
    "batch2": PILOT2_RUNS,
    "all": PILOT_RUNS + PILOT2_RUNS,
}

# Both phrasings seen in `raw_text`: with and without the "but". Matches the
# census regex in scripts/probe_refusals.py so the two reports count the same
# event.
REFUSAL_RE = re.compile(r"I(?:'m| am) sorry.{0,20}I can'?t assist", re.I)

# `Reasoner` keeps only the last attempt's text, so a live artifact whose attempt 1
# was refused and whose re-ask recovered stores JSON. The census (2026-09-25)
# established that this error message is the signature of such an attempt-1
# refusal: no other non-JSON failure mode appears in the corpus.
NO_JSON_ERROR = "VLM output contains no JSON object."

ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")

Arm = Literal["R", "grey", "O", "M", "S", "D", "S2", "F", "X"]
RetryPolicy = Literal[
    "shipped", "original_prompt", "max_attempts_4", "image_fallback_2"
]

# Arms recorded before the obstacle-text factor existed. Their cell keys must stay
# byte-identical or every already-recorded row would be re-run, so the factor is
# appended to the key only for the arms added afterwards.
LEGACY_ARMS = frozenset({"R", "grey", "O", "M"})

# A genuine head-on standoff, using the prompt's own facing rule (rendered by
# `format_pairwise_geometry_lines`) rather than a re-derivation.
STANDOFF_MAX_DISTANCE_M = 0.6
STANDOFF_MAX_SPEED_MPS = 0.02

# Words a trace would have to use to cite the blocker. `1.85` is the rendered
# obstacle coordinate; `box` is how the prompt itself names an obstacle.
OBSTACLE_MENTION_RE = re.compile(
    r"obstacle|blocker|barrier|obstruct|\bwall\b|\bboxe?s?\b|crate|1\.85", re.I
)
THINK_RE = re.compile(r"<think>(.*?)</think>", re.S | re.I)

ARM_D_DOWNSCALE_WIDTH_PX = 640

# The raw dump is grabbed from `/camera/image_raw` a little before or after the
# frame M1 annotated, so the two images are not the same instant. Below this
# separation the pair is close enough that a difference is attributable to the
# overlay rather than to robot motion.
ARM_F_TIGHT_SKEW_SEC = 0.2


# An exhausted credit balance arrives as HTTP 429 with these markers; a rate
# limit does not carry them.
QUOTA_RE = re.compile(r"insufficient_quota|credit_balance_exhausted|no credits remaining", re.I)


class AuthAbort(RuntimeError):
    """Raised when the API rejects our credentials, to stop the run immediately."""


class QuotaAbort(RuntimeError):
    """Raised when the API reports an exhausted credit balance, which no retry clears."""


def is_refusal(text: str | None) -> bool:
    """Return True when assistant text is an OpenAI safety refusal.

    Args:
        text: Raw assistant text, or None.

    Returns:
        True if the text matches either observed refusal phrasing.
    """
    return bool(text) and bool(REFUSAL_RE.search(text or ""))


def think_block(text: str | None) -> str:
    """Return the concatenated contents of every `<think>` block in assistant text.

    Args:
        text: Raw assistant text, or None.

    Returns:
        The reasoning trace, or an empty string when the text carries no block.
    """
    return "\n".join(THINK_RE.findall(text or ""))


def mentions_obstacle(text: str | None) -> bool:
    """Return True when text names the blocker in any of its rendered guises."""
    return bool(text) and bool(OBSTACLE_MENTION_RE.search(text or ""))


def parses_as_decision(text: str | None) -> bool:
    """Return True when assistant text parses as a valid `CongestionDecision`."""
    if not text:
        return False
    try:
        parse_decision_text(text)
    except (VLMOutputParseError, DecisionValidationError):
        return False
    return True


@dataclass(frozen=True)
class Artifact:
    """One stored live decision, reduced to what the replay needs."""

    run: str
    request_id: str
    path: Path
    image_path: Path
    scene: dict[str, Any]
    failure_context: dict[str, Any] | None
    stored_order: RobotPresentationOrder
    stored_user_sha256: str
    stored_system_sha256: str
    stored_user_prompt: str
    include_pairwise_geometry: bool
    include_static_obstacles: bool
    static_obstacles: tuple[StaticObstacleInput, ...]
    obstacle_x: float | None
    live_parse_status: str | None
    live_attempts: int | None
    live_error_message: str | None
    live_raw_text: str | None
    live_decision: dict[str, Any] | None
    stamp: float
    raw_frame_skew_sec: float | None = None
    # Absent (None) on every artifact written before the failure-context depth
    # policy (2026-09-27), which then reconstructs exactly as before.
    last_failed_context: dict[str, Any] | None = None
    # The prompt template the artifact was rendered with. Artifacts written
    # before the prompt-v2 bundle (2026-09-27) carry no `prompt_version` key
    # and were all rendered by the frozen v1 template.
    prompt_version: int = 1

    @property
    def raw_image_path(self) -> Path:
        """The raw camera frame dumped beside the annotated one for this request.

        M5 writes `<request_id>_raw.png` next to `<request_id>.png`; the two are
        the same camera at slightly different instants, `raw_frame_skew_sec`
        apart, with the M1 overlay drawn on only one of them.
        """
        return self.image_path.with_name(f"{self.request_id}_raw.png")

    @property
    def live_attempt1_refusal(self) -> bool:
        """Whether attempt 1 of the live call was a refusal.

        A terminal refusal is visible directly in `raw_text`; a recovered one is
        inferred from `parse_status="invalid"` plus the no-JSON error signature.
        """
        if is_refusal(self.live_raw_text):
            return True
        return (
            self.live_parse_status in ("invalid", "failed")
            and self.live_error_message == NO_JSON_ERROR
        )

    @property
    def correct_yielder(self) -> str | None:
        """The robot whose retreat direction is unobstructed in this run's scenario.

        robot_1 enters from the west and retreats west; robot_2 enters from the
        east and retreats east. M3's own feasibility gate recorded the mapping in
        the pilot artifacts ("robot_1 has 0.70 m retreat room < 1.08 m required;
        robot_2 feasible" in the runs whose obstacle sits at x = -1.85), so a
        west obstacle makes robot_2 the feasible yielder and an east obstacle
        makes it robot_1.
        """
        if self.obstacle_x is None:
            return None
        return "robot_2" if self.obstacle_x < 0 else "robot_1"

    @property
    def obstacle_side(self) -> str | None:
        """Which end of the corridor the blocker sits at, or None when undeclared."""
        if self.obstacle_x is None:
            return None
        return "west" if self.obstacle_x < 0 else "east"


def _analysis_order(run_dir: Path) -> dict[str, int]:
    """Map request_id to its position in the M5 log's analysis sequence."""
    order: dict[str, int] = {}
    log = run_dir / "component_logs" / "m5.log"
    if not log.is_file():
        return order
    pattern = re.compile(r"starting analysis request=(\w+)")
    for index, match in enumerate(pattern.finditer(log.read_text(errors="replace"))):
        order.setdefault(match.group(1), index)
    return order


_SKEW_RE = re.compile(r"raw frame skew_sec=(?P<skew>[+-]?[\d.]+) request=(?P<request>\w+)")


def _raw_frame_skews(run_dir: Path) -> dict[str, float]:
    """Map request_id to the signed seconds between its raw and annotated frames.

    Args:
        run_dir: One VM run directory.

    Returns:
        The skew per request as M5 logged it; empty when the run predates the
        raw-frame dump or its log is unavailable.
    """
    log = run_dir / "component_logs" / "m5.log"
    if not log.is_file():
        return {}
    return {
        match.group("request"): float(match.group("skew"))
        for match in _SKEW_RE.finditer(log.read_text(errors="replace"))
    }


def load_artifacts(
    runs: tuple[str, ...] = PILOT_RUNS, runs_dir: Path = RUNS_DIR
) -> list[Artifact]:
    """Load every decision artifact of the given runs, in analysis order.

    Args:
        runs: Run stamps to load.
        runs_dir: Directory holding one subdirectory per VM run.

    Returns:
        Artifacts ordered by run, then by the M5 log's analysis sequence
        (falling back to the scene stamp when the log is unavailable).

    Raises:
        FileNotFoundError: If a run directory or its config is missing.
    """
    artifacts: list[Artifact] = []
    for run in runs:
        run_dir = runs_dir / run
        config_path = run_dir / "orchestrator.yaml.used"
        if not config_path.is_file():
            raise FileNotFoundError(f"missing run config: {config_path}")
        config = yaml.safe_load(config_path.read_text())
        obstacles = tuple(
            StaticObstacleInput(**entry) for entry in (config.get("static_obstacles") or [])
        )
        obstacle_x = obstacles[0].x if obstacles else None
        log_order = _analysis_order(run_dir)
        skews = _raw_frame_skews(run_dir)
        loaded: list[Artifact] = []
        for path in sorted((run_dir / "decisions").glob("*.json")):
            data = json.loads(path.read_text())
            prompt = data.get("prompt") or {}
            diagnostics = data.get("diagnostics") or {}
            request_id = data["request_id"]
            loaded.append(
                Artifact(
                    run=run,
                    request_id=request_id,
                    path=path,
                    image_path=run_dir / "m5_frames" / f"{request_id}.png",
                    scene=data["scene"],
                    failure_context=data.get("failure_context"),
                    stored_order=data["robot_presentation_order"],
                    stored_user_sha256=prompt["user_sha256"],
                    stored_system_sha256=prompt["system_sha256"],
                    stored_user_prompt=prompt["user_prompt"],
                    include_pairwise_geometry=bool(config["prompt_pairwise_geometry"]),
                    include_static_obstacles=bool(config["prompt_static_obstacles"]),
                    static_obstacles=obstacles,
                    obstacle_x=obstacle_x,
                    live_parse_status=diagnostics.get("parse_status"),
                    live_attempts=diagnostics.get("attempts"),
                    live_error_message=diagnostics.get("error_message"),
                    live_raw_text=data.get("raw_text"),
                    live_decision=data.get("decision"),
                    stamp=float(data["scene"]["stamp"]),
                    raw_frame_skew_sec=skews.get(request_id),
                    last_failed_context=data.get("last_failed_context"),
                    prompt_version=int(data.get("prompt_version") or 1),
                )
            )
        loaded.sort(key=lambda a: (log_order.get(a.request_id, 10**6), a.stamp))
        artifacts.extend(loaded)
    return artifacts


def reconstruct_request(
    artifact: Artifact,
    order: RobotPresentationOrder | None = None,
    image_path: Path | None = None,
    include_static_obstacles: bool | None = None,
) -> ReasonerRequest:
    """Rebuild the `ReasonerRequest` M5 issued for one stored decision.

    Args:
        artifact: The stored decision.
        order: Presentation order to render with; None uses the stored order.
        image_path: Image to attach; None uses the real stored frame.
        include_static_obstacles: Whether to render the obstacle block; None uses
            the run's own setting, which is what the SHA-256 check asserts against.

    Returns:
        The reconstructed request.
    """
    failure_context = (
        FailureContext(**artifact.failure_context) if artifact.failure_context else None
    )
    last_failed_context = (
        FailureContext(**artifact.last_failed_context)
        if artifact.last_failed_context
        else None
    )
    obstacles = (
        artifact.include_static_obstacles
        if include_static_obstacles is None
        else include_static_obstacles
    )
    return build_reasoner_request(
        artifact.request_id,
        snapshot=SceneSnapshot(**artifact.scene),
        image_path=str(image_path or artifact.image_path),
        failure_context=failure_context,
        last_failed_context=last_failed_context,
        include_pairwise_geometry=artifact.include_pairwise_geometry,
        static_obstacles=list(artifact.static_obstacles),
        include_static_obstacles=obstacles,
        robot_presentation_order=order or artifact.stored_order,
        prompt_version=artifact.prompt_version,
    )


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class IntegrityResult:
    """Outcome of the prompt-reconstruction check across all artifacts."""

    matched: list[Artifact] = field(default_factory=list)
    mismatched: list[tuple[Artifact, str]] = field(default_factory=list)
    missing_image: list[Artifact] = field(default_factory=list)


def first_differing_line(expected: str, rendered: str) -> str:
    """Describe the first line where two prompts diverge."""
    left, right = expected.splitlines(), rendered.splitlines()
    for index, (a, b) in enumerate(zip(left, right, strict=False)):
        if a != b:
            return f"line {index + 1}: stored={a!r} rendered={b!r}"
    return f"line count: stored={len(left)} rendered={len(right)}"


def check_integrity(artifacts: list[Artifact]) -> IntegrityResult:
    """Verify each artifact's prompt re-renders byte-identically under its stored order.

    Args:
        artifacts: Artifacts to check.

    Returns:
        Matched artifacts (safe to replay), mismatched ones with the first
        differing line, and those whose frame PNG is missing.
    """
    result = IntegrityResult()
    for artifact in artifacts:
        rendered = build_prompt_payload(reconstruct_request(artifact)).user_prompt
        if sha256_text(rendered) != artifact.stored_user_sha256:
            result.mismatched.append(
                (artifact, first_differing_line(artifact.stored_user_prompt, rendered))
            )
            continue
        if not artifact.image_path.is_file():
            result.missing_image.append(artifact)
            continue
        result.matched.append(artifact)
    return result


@dataclass
class AttemptRecord:
    """One backend call made inside a single `Reasoner.run`."""

    attempt: int
    user_sha256: str
    text: str | None
    refused: bool
    parsed: bool
    latency_ms: int | None
    token_usage: dict[str, int] | None
    error: str | None
    # Basename of the image actually sent, so the neutral-image fallback can be
    # verified from the record rather than trusted from the diagnostics.
    image_name: str = ""


class RecordingBackend:
    """A `VLMBackend` proxy that records every attempt, paces calls and handles 429s.

    `Reasoner.run` overwrites the attempt-1 response with the re-ask response, so
    the shipped path alone cannot report an attempt-1 refusal rate. Wrapping the
    backend instead of re-implementing the retry loop keeps the production
    retry/re-ask semantics byte-exact.
    """

    def __init__(
        self,
        inner: VLMBackend,
        pace_sec: float,
        max_backoff_retries: int = 5,
    ) -> None:
        self._inner = inner
        self._pace_sec = pace_sec
        self._max_backoff_retries = max_backoff_retries
        self._last_call_ended: float | None = None
        self.attempts: list[AttemptRecord] = []

    def reset(self) -> None:
        """Clear the per-run attempt log before the next `Reasoner.run`."""
        self.attempts = []

    def _wait_for_slot(self) -> None:
        if self._last_call_ended is None:
            return
        remaining = self._pace_sec - (time.monotonic() - self._last_call_ended)
        if remaining > 0:
            time.sleep(remaining)

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Delegate to the wrapped backend, recording and pacing the call.

        Args:
            payload: Rendered prompt payload.
            config: Runtime decoding settings.

        Returns:
            The wrapped backend's response.

        Raises:
            AuthAbort: If the API rejects the credentials (HTTP 401/403).
            QuotaAbort: If the API reports an exhausted credit balance.
            ConnectionError: For any other transport failure, re-raised so the
                production `Reasoner` sees the error class it expects.
        """
        attempt = len(self.attempts) + 1
        user_sha = sha256_text(payload.user_prompt)
        image_name = Path(payload.image_path).name
        backoff = 5.0
        for retry in range(self._max_backoff_retries + 1):
            self._wait_for_slot()
            try:
                response = self._inner.analyze(payload, config)
            except ConnectionError as exc:
                self._last_call_ended = time.monotonic()
                message = str(exc)
                if re.search(r"HTTP 40[13]\b", message):
                    raise AuthAbort(f"credentials rejected: {message[:200]}") from exc
                # OpenAI returns an exhausted credit balance as HTTP 429, the same
                # status as a rate limit. Backing off cannot clear it, so the
                # quota codes abort the run rather than burning the back-off
                # ladder once per cell (this cost ~4 min/cell on 2026-09-25).
                if QUOTA_RE.search(message):
                    raise QuotaAbort(f"API quota exhausted: {message[:200]}") from exc
                if re.search(r"HTTP 429\b", message) and retry < self._max_backoff_retries:
                    print(f"  429 received; backing off {backoff:.0f}s")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                self.attempts.append(
                    AttemptRecord(
                        attempt=attempt,
                        user_sha256=user_sha,
                        text=None,
                        refused=False,
                        parsed=False,
                        latency_ms=None,
                        token_usage=None,
                        error=f"{type(exc).__name__}: {message[:300]}",
                        image_name=image_name,
                    )
                )
                raise
            self._last_call_ended = time.monotonic()
            self.attempts.append(
                AttemptRecord(
                    attempt=attempt,
                    user_sha256=user_sha,
                    text=response.text,
                    refused=is_refusal(response.text),
                    parsed=parses_as_decision(response.text),
                    latency_ms=response.latency_ms,
                    token_usage=response.token_usage,
                    error=None,
                    image_name=image_name,
                )
            )
            return response
        raise ConnectionError("exhausted 429 back-off retries")


@dataclass(frozen=True)
class Cell:
    """One configured replay cell: an artifact under one arm, order, image and policy."""

    arm: Arm
    artifact: Artifact
    order: RobotPresentationOrder
    image_label: str
    image_path: Path
    policy: RetryPolicy
    repeat: int
    obstacle_text: bool | None = None

    @property
    def include_static_obstacles(self) -> bool:
        """Whether this cell renders the obstacle block; None falls back to the run."""
        if self.obstacle_text is None:
            return self.artifact.include_static_obstacles
        return self.obstacle_text

    def key(self) -> str:
        """Stable identity used to resume an interrupted run."""
        parts = [
            self.arm,
            self.artifact.run,
            self.artifact.request_id,
            self.order,
            self.image_label,
            self.policy,
            str(self.repeat),
        ]
        if self.arm not in LEGACY_ARMS:
            parts.append("text_on" if self.include_static_obstacles else "text_off")
        return "|".join(parts)


# `shipped` tracks production, so its meaning moves when config/models.yaml
# does: rows recorded before 2026-09-26 predate `image_fallback_after_attempts:
# 2` and are not comparable with `shipped` rows recorded after it. The two named
# policies below pin the factor explicitly so Arm X's control cannot inherit it.
_POLICY_OVERRIDES: dict[RetryPolicy, dict[str, Any]] = {
    "shipped": {},
    "original_prompt": {"allow_reask": False},
    "max_attempts_4": {"max_attempts": 4, "image_fallback_after_attempts": None},
    "image_fallback_2": {"max_attempts": 4, "image_fallback_after_attempts": 2},
}


def load_shipped_config() -> tuple[ReasonerConfig, OpenAIBackendConfig]:
    """Read the shipped OpenAI reasoner and backend config from config/models.yaml.

    Returns:
        The `ReasonerConfig` (temperature 0.0, max_attempts 2 as shipped) and the
        `OpenAIBackendConfig` for the configured model.
    """
    raw_vlm = yaml.safe_load(MODELS_YAML.read_text())["vlm"]
    reasoner_config = resolve_reasoner_config(raw_vlm, "openai")
    backend_config = OpenAIBackendConfig(**backend_section(raw_vlm, "openai"))
    return reasoner_config, backend_config


def make_grey_image(path: Path, size: tuple[int, int]) -> Path:
    """Write a neutral mid-grey PNG of the given `(width, height)` and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((size[1], size[0], 3), 128, dtype=np.uint8)).save(path)
    return path


def make_downscaled_image(
    source: Path, path: Path, width: int = ARM_D_DOWNSCALE_WIDTH_PX
) -> Path:
    """Write a width-limited copy of a frame, preserving aspect ratio, and return its path.

    Args:
        source: The real frame PNG.
        path: Destination PNG.
        width: Target width in pixels; the height follows the source aspect ratio.

    Returns:
        The destination path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        height = max(1, round(image.height * width / image.width))
        image.convert("RGB").resize((width, height), Image.LANCZOS).save(path)
    return path


def run_cell(
    cell: Cell,
    backend: RecordingBackend,
    base_config: ReasonerConfig,
) -> dict[str, Any]:
    """Execute one replay cell through the production `Reasoner` and record it.

    Args:
        cell: The configured cell.
        backend: Recording proxy wrapping the real backend.
        base_config: The shipped reasoner config, before per-policy overrides.

    Returns:
        A JSON-serializable record of the run, including every attempt.
    """
    config = base_config.model_copy(update=_POLICY_OVERRIDES[cell.policy])
    request = reconstruct_request(
        cell.artifact, cell.order, cell.image_path, cell.include_static_obstacles
    )
    payload_sha = sha256_text(build_prompt_payload(request).user_prompt)
    backend.reset()
    started = time.monotonic()
    error: str | None = None
    result = None
    try:
        result = Reasoner(backend, config).run(request)
    except (AuthAbort, QuotaAbort):
        raise
    except Exception as exc:  # noqa: BLE001 - transport failures are recorded as data
        error = f"{type(exc).__name__}: {str(exc)[:300]}"
    attempts = [vars(a) for a in backend.attempts]
    decision = (
        result.decision.model_dump(mode="json") if result and result.decision else None
    )
    return {
        "key": cell.key(),
        "arm": cell.arm,
        "run": cell.artifact.run,
        "request_id": cell.artifact.request_id,
        "order": cell.order,
        "stored_order": cell.artifact.stored_order,
        "image": cell.image_label,
        "raw_frame_skew_sec": cell.artifact.raw_frame_skew_sec,
        "obstacle_text": cell.include_static_obstacles,
        "side": cell.artifact.obstacle_side,
        "policy": cell.policy,
        "repeat": cell.repeat,
        "model_id": config.backend_id,
        "temperature": config.temperature,
        "max_attempts": config.max_attempts,
        "allow_reask": config.allow_reask,
        "image_fallback_after_attempts": config.image_fallback_after_attempts,
        "image_fallback_used": bool(
            result and result.diagnostics.image_fallback_used
        ),
        "image_fallback_attempt": (
            result.diagnostics.image_fallback_attempt if result else None
        ),
        "refusal_attempts": result.diagnostics.refusal_attempts if result else None,
        "prompt_user_sha256": payload_sha,
        "prompt_matches_live": payload_sha == cell.artifact.stored_user_sha256,
        "live_attempt1_refusal": cell.artifact.live_attempt1_refusal,
        "live_parse_status": cell.artifact.live_parse_status,
        "attempts": attempts,
        "n_attempts": len(attempts),
        "attempt1_refusal": bool(attempts) and attempts[0]["refused"],
        "attempt1_parsed": bool(attempts) and attempts[0]["parsed"],
        # Refused on entry and never recovered. Not `all(refused)`: `Reasoner.run`
        # retries a ConnectionError without a re-ask, so a transport failure would
        # append a non-refusal attempt and mask an otherwise-terminal refusal.
        "terminal_refusal": decision is None and bool(attempts) and attempts[0]["refused"],
        "parse_status": result.diagnostics.parse_status if result else None,
        "decision": decision,
        "strategy": (decision or {}).get("strategy"),
        "yield_robot": (decision or {}).get("yield_robot"),
        "correct_yielder": cell.artifact.correct_yielder,
        "think_obstacle_mention": any(
            mentions_obstacle(think_block(a["text"])) for a in attempts
        ),
        "text_obstacle_mention": any(mentions_obstacle(a["text"]) for a in attempts),
        "decision_obstacle_mention": mentions_obstacle(
            " ".join(str((decision or {}).get(k) or "") for k in ("root_cause", "justification"))
        ),
        "wall_ms": int((time.monotonic() - started) * 1000),
        "error": error,
    }


def load_done_keys(calls_path: Path) -> set[str]:
    """Return the cell keys already present in an existing `calls.jsonl`."""
    if not calls_path.is_file():
        return set()
    keys: set[str] = set()
    for line in calls_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            keys.add(json.loads(line)["key"])
        except (json.JSONDecodeError, KeyError):
            continue
    return keys


def execute(cells: list[Cell], out_dir: Path, pace_sec: float) -> list[dict[str, Any]]:
    """Run every not-yet-recorded cell, appending each result to `calls.jsonl`.

    Args:
        cells: Configured cells, in execution order.
        out_dir: Directory receiving `calls.jsonl`.
        pace_sec: Minimum seconds between API calls.

    Returns:
        The records produced by this invocation.

    Raises:
        AuthAbort: Propagated so an unusable key stops the run immediately.
        QuotaAbort: Propagated so an exhausted credit balance stops the run.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    done = load_done_keys(calls_path)
    pending = [c for c in cells if c.key() not in done]
    print(
        f"{len(cells)} cells, {len(cells) - len(pending)} already recorded, "
        f"{len(pending)} to run"
    )

    base_config, backend_config = load_shipped_config()
    backend = RecordingBackend(build_backend("openai", backend_config), pace_sec)

    records: list[dict[str, Any]] = []
    for index, cell in enumerate(pending):
        record = run_cell(cell, backend, base_config)
        records.append(record)
        with calls_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        print(
            f"[{index + 1}/{len(pending)}] {cell.arm} {cell.artifact.run} "
            f"{cell.artifact.request_id[:8]} {cell.order} {cell.image_label} "
            f"{cell.policy} r{cell.repeat} "
            f"att1_refusal={record['attempt1_refusal']} "
            f"strategy={record['strategy']} yield={record['yield_robot']}"
        )
    return records


def build_arm_r_cells(matched: list[Artifact], n: int) -> list[Cell]:
    """Every matched artifact, stored order, real frame, shipped retry policy."""
    return [
        Cell("R", a, a.stored_order, "real", a.image_path, "shipped", i)
        for a in matched
        for i in range(n)
    ]


def select_grey_pairs(matched: list[Artifact], k: int) -> tuple[list[Artifact], list[Artifact]]:
    """Split matched artifacts into the live-refused set and a matched live-valid set.

    Controls are drawn from the same runs as the refusals, preferring artifacts
    that share the refusal's failure-context condition, so the pair differs in
    the image arm rather than in the prompt's structure.

    Args:
        matched: Artifacts whose prompt reconstructed exactly.
        k: Maximum number of controls to draw.

    Returns:
        The refused artifacts and the selected controls.
    """
    refused = [a for a in matched if a.live_attempt1_refusal]
    candidates = [a for a in matched if not a.live_attempt1_refusal]
    wanted = [(a.run, bool(a.failure_context)) for a in refused]
    controls: list[Artifact] = []
    for run, has_fc in wanted:
        pick = next(
            (
                c
                for c in candidates
                if c not in controls and c.run == run and bool(c.failure_context) == has_fc
            ),
            None,
        ) or next((c for c in candidates if c not in controls and c.run == run), None)
        if pick is not None:
            controls.append(pick)
    for c in candidates:
        if len(controls) >= k:
            break
        if c not in controls:
            controls.append(c)
    return refused, controls[:k]


def build_grey_cells(
    refused: list[Artifact], controls: list[Artifact], grey: Path, n: int
) -> list[Cell]:
    """Grey-image cells for the refused artifacts and their matched controls."""
    return [
        Cell("grey", a, a.stored_order, "grey", grey, "shipped", i)
        for a in refused + controls
        for i in range(n)
    ]


def first_yield_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    """The first artifact of each run whose live decision chose `yield`.

    `artifacts` must already be in analysis order (as `load_artifacts` returns
    them), so "first" is the run's first yield decision.
    """
    seen: set[str] = set()
    picks: list[Artifact] = []
    for artifact in artifacts:
        if artifact.run in seen:
            continue
        if (artifact.live_decision or {}).get("strategy") == "yield":
            picks.append(artifact)
            seen.add(artifact.run)
    return picks


def build_arm_o_cells(yields: list[Artifact], n: int) -> list[Cell]:
    """Each first-yield artifact under both presentation orders, real frame."""
    return [
        Cell("O", a, order, "real", a.image_path, "shipped", i)
        for a in yields
        for order in ORDERS
        for i in range(n)
    ]


_PAIRWISE_RE = re.compile(
    r"distance (?P<distance>[\d.]+) m; "
    r"\S+ faces \S+: (?P<first>yes|no); \S+ faces \S+: (?P<second>yes|no)"
)


def is_standoff(
    artifact: Artifact,
    max_distance_m: float = STANDOFF_MAX_DISTANCE_M,
    max_speed_mps: float = STANDOFF_MAX_SPEED_MPS,
) -> bool:
    """Whether an artifact's scene is a genuine two-robot head-on standoff.

    Both robots must be stationary (`STOPPED`, or below `max_speed_mps`), within
    `max_distance_m` of each other, and mutually facing. Facing and distance come
    from the rendered pairwise-geometry line, so the filter uses exactly the rule
    the prompt states rather than a second implementation of it.

    Args:
        artifact: The stored decision.
        max_distance_m: Inclusive separation ceiling.
        max_speed_mps: Speed below which a robot counts as stationary.

    Returns:
        True when the scene is a standoff.
    """
    states = reconstruct_request(artifact).robot_states
    if len(states) != 2:
        return False
    stationary = all(
        state.status == "STOPPED" or abs(state.linear_velocity or 0.0) < max_speed_mps
        for state in states
    )
    if not stationary:
        return False
    lines = format_pairwise_geometry_lines(states, artifact.stored_order)
    if len(lines) != 1:
        return False
    match = _PAIRWISE_RE.search(lines[0])
    if match is None:
        return False
    return (
        float(match.group("distance")) <= max_distance_m
        and match.group("first") == "yes"
        and match.group("second") == "yes"
    )


def select_standoff_artifacts(
    matched: list[Artifact], exclude_failure_context: bool = True
) -> list[Artifact]:
    """The standoff artifacts of the corpus, optionally dropping failure-context ones.

    Args:
        matched: Artifacts whose prompt reconstructed exactly.
        exclude_failure_context: Drop artifacts carrying a rendered failure-context
            block, which is a second manipulated channel.

    Returns:
        The selected artifacts, in the input order.
    """
    return [
        a
        for a in matched
        if is_standoff(a) and not (exclude_failure_context and a.failure_context)
    ]


def build_arm_s_cells(
    standoffs: list[Artifact], grey: Path, n: int, arm: Arm = "S"
) -> list[Cell]:
    """The fully crossed order x obstacle-text x image design on the standoff scenes.

    Args:
        standoffs: The selected standoff artifacts.
        grey: Neutral image of the same size as the real frames.
        n: Replicates per cell.
        arm: Arm label, so the batch-2 replication records under `S2` and its
            keys never collide with the already-recorded batch-1 `S` rows.

    Returns:
        The configured cells.
    """
    return [
        Cell(
            arm,
            artifact,
            order,
            image_label,
            grey if image_label == "grey" else artifact.image_path,
            "shipped",
            index,
            obstacle_text=obstacle_text,
        )
        for artifact in standoffs
        for order in ORDERS
        for obstacle_text in (True, False)
        for image_label in ("real", "grey")
        for index in range(n)
    ]


def build_arm_d_cells(refused: list[Artifact], downscaled: dict[str, Path], n: int) -> list[Cell]:
    """Full-resolution against downscaled frames on the live-refused artifacts."""
    return [
        Cell(
            "D",
            artifact,
            artifact.stored_order,
            image_label,
            artifact.image_path if image_label == "real" else downscaled[artifact.request_id],
            "shipped",
            index,
        )
        for artifact in refused
        for image_label in ("real", f"down{ARM_D_DOWNSCALE_WIDTH_PX}")
        for index in range(n)
    ]


def build_arm_f_cells(artifacts: list[Artifact], n: int) -> list[Cell]:
    """Each artifact's stored request under its annotated frame and its raw frame.

    Everything except `image_path` is held at the live setting — stored order,
    the run's own obstacle-text setting, the shipped retry policy — so the pair
    differs only in which PNG is attached.

    Args:
        artifacts: Artifacts whose prompt reconstructed exactly.
        n: Replicates per image.

    Returns:
        The configured cells, `annotated` before `raw` for each artifact.
    """
    return [
        Cell(
            "F",
            artifact,
            artifact.stored_order,
            image_label,
            artifact.image_path if image_label == "annotated" else artifact.raw_image_path,
            "shipped",
            index,
        )
        for artifact in artifacts
        for image_label in ("annotated", "raw")
        for index in range(n)
    ]


def build_arm_x_cells(refused: list[Artifact], n: int) -> list[Cell]:
    """Image-fallback comparison cells on the artifacts that refused live.

    Both policies run four attempts; they differ only in whether a refusal on
    attempt 2 swaps the frame for a neutral image on attempt 3. The control pins
    `image_fallback_after_attempts` to None rather than using `shipped`, which now
    carries the mitigation.

    This module keeps its own `is_refusal` (the census definition already baked
    into every recorded `refused` flag) rather than importing the production one,
    so old and new rows stay comparable. On 1407 recorded attempt texts the two
    agree except on 7 "I'm sorry, but I can't help with that." responses, which
    only the production detector counts; the recorded `refused` flag therefore
    slightly under-counts what the mitigation itself acts on.

    Args:
        refused: Artifacts whose live attempt 1 was refused.
        n: Replicates per policy.

    Returns:
        The configured cells, control policy before fallback policy.
    """
    policies: tuple[RetryPolicy, ...] = ("max_attempts_4", "image_fallback_2")
    return [
        Cell("X", artifact, artifact.stored_order, "real", artifact.image_path, policy, index)
        for artifact in refused
        for policy in policies
        for index in range(n)
    ]


def build_arm_m_cells(refusing: list[Artifact], n: int) -> list[Cell]:
    """Retry-policy comparison cells on the artifacts that refused in Arm R."""
    policies: tuple[RetryPolicy, ...] = ("shipped", "original_prompt", "max_attempts_4")
    return [
        Cell("M", a, a.stored_order, "real", a.image_path, policy, i)
        for a in refusing
        for policy in policies
        for i in range(n)
    ]


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for the 2x2 table `[[a, b], [c, d]]`.

    Args:
        a: Successes in group 1.
        b: Failures in group 1.
        c: Successes in group 2.
        d: Failures in group 2.

    Returns:
        The two-sided p-value, or 1.0 for a degenerate table.
    """
    total, row1, col1 = a + b + c + d, a + b, a + c
    if total == 0 or min(row1, col1, total - row1, total - col1) < 0:
        return 1.0

    def hypergeom(x: int) -> float:
        return (
            math.comb(row1, x)
            * math.comb(total - row1, col1 - x)
            / math.comb(total, col1)
        )

    observed = hypergeom(a)
    low, high = max(0, col1 - (total - row1)), min(row1, col1)
    return min(
        1.0,
        sum(hypergeom(x) for x in range(low, high + 1) if hypergeom(x) <= observed + 1e-12),
    )


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar (sign) p-value for `b` and `c` discordant pairs.

    The exact binomial form is used rather than the chi-square approximation
    because the discordant count here is small.

    Args:
        b: Pairs favouring the first condition.
        c: Pairs favouring the second.

    Returns:
        The two-sided p-value; 1.0 when there is no discordance.
    """
    total = b + c
    if total == 0:
        return 1.0
    tail = sum(math.comb(total, i) for i in range(min(b, c) + 1)) / 2**total
    return min(1.0, 2 * tail)


GPT4O_USD_PER_PROMPT_TOKEN = 2.50 / 1_000_000
GPT4O_USD_PER_COMPLETION_TOKEN = 10.00 / 1_000_000


def _rate(numerator: int, denominator: int) -> str:
    """Format a count over a denominator as `k/n (p%)`."""
    if denominator == 0:
        return "0/0 (n/a)"
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)"


def terminal_refusal(record: dict[str, Any]) -> bool:
    """Whether a recorded run refused on attempt 1 and never produced a decision.

    Recomputed from the stored attempts rather than read from the record, so that
    rows written before this definition was tightened are scored the same way.
    """
    attempts = record.get("attempts") or []
    return record.get("decision") is None and bool(attempts) and attempts[0]["refused"]


def _attempt1_stats(records: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (attempt-1 refusals, runs) over records that produced at least one attempt."""
    usable = [r for r in records if r.get("n_attempts")]
    return sum(int(r["attempt1_refusal"]) for r in usable), len(usable)


def analyze(records: list[dict[str, Any]], artifacts: list[Artifact]) -> None:
    """Print the report-ready tables for every arm present in `records`.

    Args:
        records: Every recorded call, as read from `calls.jsonl`.
        artifacts: The loaded artifacts, for the live-rate comparison.
    """
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_arm[record["arm"]].append(record)
    by_id = {a.request_id: a for a in artifacts}

    arm_r = by_arm.get("R", [])
    if arm_r:
        refusals, runs = _attempt1_stats(arm_r)
        terminal = sum(int(terminal_refusal(r)) for r in arm_r)
        errors = sum(int(bool(r.get("error"))) for r in arm_r)
        print("\n## Arm R (real frame, stored order)")
        print(f"runs={runs} attempt-1 refusals={_rate(refusals, runs)} "
              f"terminal={_rate(terminal, runs)} transport errors={errors}")
        reasked = [r for r in arm_r if r["attempt1_refusal"]]
        recovered = sum(1 for r in reasked if r.get("decision") is not None)
        print(f"re-ask recovered {_rate(recovered, len(reasked))} of the refused runs")

        print("\nrun,artifacts,runs,attempt1_refusals,rate")
        for run in sorted({r["run"] for r in arm_r}):
            group = [r for r in arm_r if r["run"] == run]
            k, n = _attempt1_stats(group)
            print(f"{run},{len({r['request_id'] for r in group})},{n},{k},{k / n:.3f}")

        print("\nlive_attempt1_refusal,runs,attempt1_refusals,rate")
        for flag in (True, False):
            group = [r for r in arm_r if r["live_attempt1_refusal"] is flag]
            k, n = _attempt1_stats(group)
            print(f"{flag},{n},{k},{(k / n if n else 0):.3f}")
        a = sum(int(r["attempt1_refusal"]) for r in arm_r if r["live_attempt1_refusal"])
        b = sum(1 for r in arm_r if r["live_attempt1_refusal"]) - a
        c = sum(int(r["attempt1_refusal"]) for r in arm_r if not r["live_attempt1_refusal"])
        d = sum(1 for r in arm_r if not r["live_attempt1_refusal"]) - c
        print(f"live-refused vs live-valid artifacts: fisher p={fisher_two_sided(a, b, c, d):.4g}")

        print("\nfailure_context,runs,attempt1_refusals,rate")
        for flag in (True, False):
            group = [
                r for r in arm_r if bool(by_id[r["request_id"]].failure_context) is flag
            ]
            k, n = _attempt1_stats(group)
            print(f"{flag},{n},{k},{(k / n if n else 0):.3f}")

        per_artifact = defaultdict(list)
        for record in arm_r:
            per_artifact[record["request_id"]].append(int(record["attempt1_refusal"]))
        ever = sum(1 for v in per_artifact.values() if any(v))
        always = sum(1 for v in per_artifact.values() if all(v))
        print(f"\nartifacts refusing at least once: {_rate(ever, len(per_artifact))}; "
              f"on every replicate: {_rate(always, len(per_artifact))}")

    arm_grey = by_arm.get("grey", [])
    if arm_grey:
        print("\n## Grey-image sub-arm (paired on the same prompts)")
        print("live_status,image,runs,attempt1_refusals,rate")
        for flag in (True, False):
            label = "live_refused" if flag else "live_valid"
            ids = {r["request_id"] for r in arm_grey if r["live_attempt1_refusal"] is flag}
            for image, pool in (("real", arm_r), ("grey", arm_grey)):
                group = [r for r in pool if r["request_id"] in ids]
                k, n = _attempt1_stats(group)
                print(f"{label},{image},{n},{k},{(k / n if n else 0):.3f}")
        grey_ids = {r["request_id"] for r in arm_grey}
        real = [r for r in arm_r if r["request_id"] in grey_ids]
        a, an = _attempt1_stats(real)
        c, cn = _attempt1_stats(arm_grey)
        print(f"pooled real {a}/{an} vs grey {c}/{cn}, "
              f"fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g}")

    arm_o = by_arm.get("O", [])
    if arm_o:
        print("\n## Arm O (order on real stimuli)")
        header = (
            "run,request_id,stored_order,order,n,decided,yield,"
            "P(yield=robot_1),P(first_listed),P(correct),non_yield"
        )
        print(header)
        for run in sorted({r["run"] for r in arm_o}):
            for order in ORDERS:
                group = [r for r in arm_o if r["run"] == run and r["order"] == order]
                if not group:
                    continue
                yields = [r for r in group if r["strategy"] == "yield"]
                decided = [r for r in group if r.get("decision") is not None]
                first_listed = "robot_1" if order == "id_asc" else "robot_2"
                n_y = len(yields)
                r1 = sum(1 for r in yields if r["yield_robot"] == "robot_1")
                fl = sum(1 for r in yields if r["yield_robot"] == first_listed)
                ok = sum(1 for r in yields if r["yield_robot"] == r["correct_yielder"])
                print(
                    f"{run},{group[0]['request_id'][:8]},{group[0]['stored_order']},{order},"
                    f"{len(group)},{len(decided)},{n_y},"
                    f"{(r1 / n_y if n_y else 0):.3f},{(fl / n_y if n_y else 0):.3f},"
                    f"{(ok / n_y if n_y else 0):.3f},{len(decided) - n_y}"
                )
        for label, pool in (
            ("pooled", arm_o),
            ("attempt-1 only", [r for r in arm_o if not r["attempt1_refusal"]]),
        ):
            cells = {}
            for order in ORDERS:
                yields = [r for r in pool if r["order"] == order and r["strategy"] == "yield"]
                cells[order] = (
                    sum(1 for r in yields if r["yield_robot"] == "robot_1"),
                    len(yields),
                )
            (a, an), (c, cn) = cells["id_asc"], cells["id_desc"]
            print(
                f"{label}: P(yield=robot_1) id_asc {a}/{an} vs id_desc {c}/{cn}, "
                f"fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g}"
            )
            # First-listed is robot_1 under id_asc and robot_2 under id_desc, so the
            # id_desc first-listed count is the complement of its robot_1 count.
            print(
                f"{label}: P(yield=first-listed) id_asc {_rate(a, an)} vs "
                f"id_desc {_rate(cn - c, cn)}; pooled {_rate(a + cn - c, an + cn)}"
            )
            ok = sum(
                1
                for r in pool
                if r["strategy"] == "yield" and r["yield_robot"] == r["correct_yielder"]
            )
            print(f"{label}: P(correct yielder) {_rate(ok, an + cn)} of yields")

    arm_m = by_arm.get("M", [])
    if arm_m:
        print("\n## Arm M (retry policy on the Arm-R refusers)")
        print(
            "policy,runs,attempt1_refusals,terminal_refusals,terminal_rate,"
            "mean_attempts,transport_errors"
        )
        for policy in ("shipped", "original_prompt", "max_attempts_4"):
            group = [r for r in arm_m if r["policy"] == policy]
            if not group:
                continue
            k, n = _attempt1_stats(group)
            terminal = sum(int(terminal_refusal(r)) for r in group)
            mean_attempts = sum(r["n_attempts"] for r in group) / len(group)
            errors = sum(int(bool(r.get("error"))) for r in group)
            print(
                f"{policy},{n},{k},{terminal},{(terminal / n if n else 0):.3f},"
                f"{mean_attempts:.2f},{errors}"
            )
        # Conditional on a refused attempt 1, which is the quantity the retry
        # policy actually acts on.
        print("policy,refused_attempt1,still_terminal,conditional_terminal_rate")
        for policy in ("shipped", "original_prompt", "max_attempts_4"):
            refused = [r for r in arm_m if r["policy"] == policy and r["attempt1_refusal"]]
            if not refused:
                continue
            terminal = sum(int(terminal_refusal(r)) for r in refused)
            print(f"{policy},{len(refused)},{terminal},{terminal / len(refused):.3f}")

    if by_arm.get("X"):
        analyze_arm_x(by_arm["X"])
    if by_arm.get("S"):
        analyze_arm_s(by_arm["S"], "batch 1")
    if by_arm.get("S2"):
        analyze_arm_s(by_arm["S2"], "batch 2 replication")
    if by_arm.get("S") and by_arm.get("S2"):
        analyze_arm_s(by_arm["S"] + by_arm["S2"], "pooled batch 1+2")
    if by_arm.get("D"):
        analyze_arm_d(by_arm["D"], by_arm.get("R", []))
    if by_arm.get("F"):
        analyze_arm_f(by_arm["F"])

    prompt_tokens = sum(
        (a.get("token_usage") or {}).get("prompt_tokens", 0)
        for r in records
        for a in (r.get("attempts") or [])
    )
    completion_tokens = sum(
        (a.get("token_usage") or {}).get("completion_tokens", 0)
        for r in records
        for a in (r.get("attempts") or [])
    )
    api_calls = sum(len(r.get("attempts") or []) for r in records)
    cost = (
        prompt_tokens * GPT4O_USD_PER_PROMPT_TOKEN
        + completion_tokens * GPT4O_USD_PER_COMPLETION_TOKEN
    )
    print(
        f"\n## Cost\nreasoner runs={len(records)} api calls={api_calls} "
        f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} "
        f"est_usd={cost:.2f}"
    )


ARM_X_POLICIES: tuple[RetryPolicy, ...] = ("max_attempts_4", "image_fallback_2")


def _decision_keys(records: list[dict[str, Any]]) -> dict[str, set[tuple[str, str | None]]]:
    """Map each artifact to the `(strategy, yield_robot)` pairs it produced."""
    keys: dict[str, set[tuple[str, str | None]]] = defaultdict(set)
    for record in records:
        decision = record.get("decision")
        if decision:
            keys[record["request_id"]].add(
                (decision["strategy"], decision.get("yield_robot"))
            )
    return keys


def analyze_arm_x(records: list[dict[str, Any]]) -> None:
    """Print the image-fallback comparison: refusal cost, and decision agreement.

    Agreement is computed on the fired subset alone. Most fallback-policy runs
    never trigger the swap (attempt 1 already parsed), so pooling them would
    compare a cell with itself and drive agreement to 100% by construction.

    Args:
        records: Arm-X call records.
    """
    print("\n## Arm X (neutral-image fallback vs four attempts alone)")
    print(
        "policy,runs,attempt1_refusals,terminal_refusals,terminal_rate,decided,"
        "fallback_used,mean_attempts,transport_errors"
    )
    terminals: dict[str, tuple[int, int]] = {}
    for policy in ARM_X_POLICIES:
        group = [r for r in records if r["policy"] == policy]
        if not group:
            continue
        refusals, runs = _attempt1_stats(group)
        terminal = sum(int(terminal_refusal(r)) for r in group)
        # Denominator is the usable runs, as in Arm M: a transport-error row made
        # no attempt, so counting it as a non-terminal run would flatter the policy.
        terminals[policy] = (terminal, runs)
        print(
            f"{policy},{runs},{refusals},{terminal},"
            f"{(terminal / runs if runs else 0):.3f},"
            f"{sum(1 for r in group if r.get('decision') is not None)},"
            f"{sum(int(bool(r.get('image_fallback_used'))) for r in group)},"
            f"{sum(r['n_attempts'] for r in group) / len(group):.2f},"
            f"{sum(int(bool(r.get('error'))) for r in group)}"
        )
    if len(terminals) == 2:
        (a, an), (c, cn) = terminals["max_attempts_4"], terminals["image_fallback_2"]
        print(
            f"terminal refusal {_rate(a, an)} vs {_rate(c, cn)}, "
            f"fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g}"
        )

    # Conditional on the quantity the policy acts on: a refused attempt 1.
    print("policy,refused_attempt1,still_terminal,conditional_terminal_rate")
    for policy in ARM_X_POLICIES:
        refused = [r for r in records if r["policy"] == policy and r["attempt1_refusal"]]
        if refused:
            terminal = sum(int(terminal_refusal(r)) for r in refused)
            print(f"{policy},{len(refused)},{terminal},{terminal / len(refused):.3f}")

    fired = [
        r
        for r in records
        if r.get("image_fallback_used") and r.get("decision") is not None
    ]
    control = _decision_keys([r for r in records if r["policy"] == "max_attempts_4"])
    strategy_ok = sum(
        1
        for r in fired
        if r["strategy"] in {k[0] for k in control.get(r["request_id"], set())}
    )
    yields = [
        r
        for r in fired
        if r["strategy"] == "yield"
        and any(k[0] == "yield" for k in control.get(r["request_id"], set()))
    ]
    yield_ok = sum(
        1
        for r in yields
        if r["yield_robot"]
        in {k[1] for k in control.get(r["request_id"], set()) if k[0] == "yield"}
    )
    fired_all = sum(1 for r in records if r.get("image_fallback_used"))
    print(
        f"\nfallback fired on {fired_all} runs "
        f"({len({r['request_id'] for r in records if r.get('image_fallback_used')})} artifacts); "
        f"{len(fired)} produced a decision"
    )
    print(
        f"decision agreement with the frame-attached control: "
        f"strategy {_rate(strategy_ok, len(fired))}, "
        f"yield_robot {_rate(yield_ok, len(yields))} of the paired yields"
    )


S_CHANNELS: tuple[tuple[bool, str], ...] = (
    (True, "real"),
    (True, "grey"),
    (False, "real"),
    (False, "grey"),
)


def _yield_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The records in `records` whose decision chose `yield`."""
    return [r for r in records if r.get("strategy") == "yield"]


def _counts(records: list[dict[str, Any]], field_name: str, value: Any) -> tuple[int, int]:
    """Return (matches, total) for `field_name == value` over yield decisions."""
    rows = _yield_rows(records)
    return sum(1 for r in rows if r.get(field_name) == value), len(rows)


def _feasible_counts(records: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (yields naming the feasible robot, total yields)."""
    rows = _yield_rows(records)
    return sum(1 for r in rows if r["yield_robot"] == r["correct_yielder"]), len(rows)


def _side_blind_baseline(records: list[dict[str, Any]]) -> tuple[float, float]:
    """P(feasible) that the two side-blind constant rules would score on these yields.

    P(feasible) is only centred on 0.5 when the corpus carries equally many
    west- and east-blocked scenes. On an unbalanced corpus - which a
    quota-truncated run produces - "always `robot_1`" and "always `robot_2`"
    score these two values instead, and they bracket what any side-blind rule
    (first-listed, ID-anchored, coin flip) can reach.

    Args:
        records: Call records for one cell.

    Returns:
        P(feasible) for always-`robot_1` and for always-`robot_2`.

    """
    rows = _yield_rows(records)
    if not rows:
        return 0.0, 0.0
    r1 = sum(1 for r in rows if r["correct_yielder"] == "robot_1") / len(rows)
    return r1, 1.0 - r1


def _side_split(records: list[dict[str, Any]]) -> tuple[int, int, int, int, float]:
    """Return west/east P(robot_1) counts and the Fisher p for the side association."""
    w, wn = _counts([r for r in records if r["side"] == "west"], "yield_robot", "robot_1")
    e, en = _counts([r for r in records if r["side"] == "east"], "yield_robot", "robot_1")
    return w, wn, e, en, fisher_two_sided(w, wn - w, e, en - e)


def _s_cell(
    records: list[dict[str, Any]], order: str, text: bool, image: str
) -> list[dict[str, Any]]:
    """Select one Arm-S design cell."""
    return [
        r
        for r in records
        if r["order"] == order and r["obstacle_text"] is text and r["image"] == image
    ]


def _print_s_table(records: list[dict[str, Any]], label: str) -> None:
    """Print the 8-cell table, pooled and split by obstacle side."""
    print(f"\n### Arm S cells ({label})")
    print(
        "order,obstacle_text,image,n,decided,yields,P(robot_1),P(feasible),"
        "west_P(robot_1),east_P(robot_1),side_fisher_p,think_mentions,decision_mentions"
    )
    for order in ORDERS:
        for text, image in S_CHANNELS:
            cell = _s_cell(records, order, text, image)
            if not cell:
                continue
            r1, n_y = _counts(cell, "yield_robot", "robot_1")
            ok, _ = _feasible_counts(cell)
            w, wn, e, en, p = _side_split(cell)
            decided = sum(1 for r in cell if r.get("decision") is not None)
            think = sum(1 for r in cell if r.get("think_obstacle_mention"))
            said = sum(1 for r in cell if r.get("decision_obstacle_mention"))
            print(
                f"{order},{'on' if text else 'off'},{image},{len(cell)},{decided},{n_y},"
                f"{(r1 / n_y if n_y else 0):.3f},{(ok / n_y if n_y else 0):.3f},"
                f"{(w / wn if wn else 0):.3f},{(e / en if en else 0):.3f},{p:.4g},"
                f"{think},{said}"
            )


def _contrast(
    records: list[dict[str, Any]],
    order: str,
    left: tuple[bool, str],
    right: tuple[bool, str],
    label: str,
) -> None:
    """Print a between-cell Fisher test on P(feasible), the side-tracking summary.

    P(feasible) pooled over the two sides is 0.5 under any side-blind rule
    (first-listed, always-`robot_1`, coin flip) and rises above it only when the
    choice tracks the obstacle side, so it is the quantity a channel ablation
    should move if that channel carries the signal.
    """
    left_cell, right_cell = _s_cell(records, order, *left), _s_cell(records, order, *right)
    a, an = _feasible_counts(left_cell)
    c, cn = _feasible_counts(right_cell)
    baselines = (_side_blind_baseline(left_cell), _side_blind_baseline(right_cell))
    print(
        f"{label}: P(feasible) {_rate(a, an)} vs {_rate(c, cn)}, "
        f"fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g} "
        f"(side-blind baselines {baselines[0][0]:.3f}/{baselines[0][1]:.3f} vs "
        f"{baselines[1][0]:.3f}/{baselines[1][1]:.3f})"
    )


def _per_scene_consistency(records: list[dict[str, Any]], order: str) -> None:
    """Print the text-on vs text-off P(feasible) contrast scene by scene.

    Every Fisher test in this arm treats replicates of six (or twelve) scenes as
    independent, so the honest evidence for a replication is how many individual
    scenes move in the same direction.

    Args:
        records: Arm-S (or Arm-S2) call records.
        order: Presentation order whose contrast to break down.
    """
    print(f"\n### Per-scene consistency under `{order}`, real frame")
    print("run,request_id,side,P(feasible)|text_on,P(feasible)|text_off,delta")
    moved = 0
    compared = 0
    scenes = sorted({(r["run"], r["request_id"], r["side"]) for r in records})
    for run, request_id, side in scenes:
        rows = [r for r in records if r["request_id"] == request_id]
        on, on_n = _feasible_counts(_s_cell(rows, order, True, "real"))
        off, off_n = _feasible_counts(_s_cell(rows, order, False, "real"))
        if not on_n or not off_n:
            print(f"{run},{request_id[:8]},{side},{_rate(on, on_n)},{_rate(off, off_n)},n/a")
            continue
        compared += 1
        delta = on / on_n - off / off_n
        moved += int(delta > 0)
        print(
            f"{run},{request_id[:8]},{side},{_rate(on, on_n)},{_rate(off, off_n)},"
            f"{delta:+.3f}"
        )
    print(
        f"scenes with a positive text-on - text-off delta: {moved}/{compared} "
        f"comparable ({len(scenes)} scenes in the arm)"
    )


def analyze_arm_s(records: list[dict[str, Any]], label: str = "") -> None:
    """Print the Arm-S design tables and the three channel contrasts.

    Args:
        records: Every recorded Arm-S call.
        label: Corpus label for the heading, e.g. `batch 2` or `pooled`.
    """
    by_side: dict[str, set[str]] = defaultdict(set)
    for record in records:
        by_side[record["side"]].add(record["request_id"])
    suffix = f" - {label}" if label else ""
    print(f"\n## Arm S (which channel carries the side signal){suffix}")
    always_r1, always_r2 = _side_blind_baseline(records)
    print(
        "artifacts: "
        + ", ".join(f"{side} {len(ids)}" for side, ids in sorted(by_side.items()))
        + f"; side-blind P(feasible) baselines: always robot_1 {always_r1:.3f}, "
        f"always robot_2 {always_r2:.3f}"
    )
    attempt1 = [r for r in records if not r["attempt1_refusal"]]
    _print_s_table(attempt1, "attempt-1 only, primary")
    _print_s_table(records, "pooled, includes re-ask-derived decisions")

    for label, pool in (("attempt-1 only", attempt1), ("pooled", records)):
        print(f"\n### id_desc channel contrasts ({label})")
        _contrast(
            pool, "id_desc", (True, "real"), (False, "real"), "(a) real frame, text on vs off"
        )
        _contrast(pool, "id_desc", (True, "real"), (True, "grey"), "(b) text on, real vs grey")
        w, wn, e, en, p = _side_split(_s_cell(pool, "id_desc", False, "grey"))
        print(
            f"(c) states only (text off + grey): west P(robot_1) {_rate(w, wn)} vs "
            f"east {_rate(e, en)}, fisher p={p:.4g}"
        )
        print(f"\n### id_asc control ({label}) - is the first-position default unbroken?")
        for text, image in S_CHANNELS:
            cell = _s_cell(pool, "id_asc", text, image)
            r1, n_y = _counts(cell, "yield_robot", "robot_1")
            ok, _ = _feasible_counts(cell)
            print(
                f"text={'on' if text else 'off'},image={image}: "
                f"P(robot_1) {_rate(r1, n_y)}, P(feasible) {_rate(ok, n_y)}"
            )

    _per_scene_consistency(attempt1, "id_desc")

    think = sum(1 for r in records if r.get("think_obstacle_mention"))
    said = sum(1 for r in records if r.get("decision_obstacle_mention"))
    any_text = sum(1 for r in records if r.get("text_obstacle_mention"))
    print(
        f"\nobstacle mentions across {len(records)} Arm-S runs: "
        f"<think> {think}, decision fields {said}, anywhere in the raw text {any_text}"
    )
    print("obstacle_text,image,runs,think_mentions,decision_mentions,any_text_mentions")
    for text, image in S_CHANNELS:
        cell = [r for r in records if r["obstacle_text"] is text and r["image"] == image]
        if not cell:
            continue
        print(
            f"{'on' if text else 'off'},{image},{len(cell)},"
            f"{sum(1 for r in cell if r.get('think_obstacle_mention'))},"
            f"{sum(1 for r in cell if r.get('decision_obstacle_mention'))},"
            f"{sum(1 for r in cell if r.get('text_obstacle_mention'))}"
        )


def analyze_arm_d(records: list[dict[str, Any]], arm_r: list[dict[str, Any]]) -> None:
    """Print the downscaled-frame refusal comparison.

    Args:
        records: Every recorded Arm-D call.
        arm_r: Arm-R records, for an out-of-session consistency note on the same
            artifacts at full resolution.
    """
    print("\n## Arm D (frame resolution and refusal)")
    print("image,runs,attempt1_refusals,rate,terminal_refusals")
    labels = sorted({r["image"] for r in records})
    stats: dict[str, tuple[int, int]] = {}
    for image in labels:
        group = [r for r in records if r["image"] == image]
        k, n = _attempt1_stats(group)
        stats[image] = (k, n)
        terminal = sum(int(terminal_refusal(r)) for r in group)
        print(f"{image},{n},{k},{(k / n if n else 0):.3f},{terminal}")
    if len(labels) == 2:
        (a, an), (c, cn) = stats[labels[0]], stats[labels[1]]
        print(
            f"{labels[0]} vs {labels[1]}: fisher p="
            f"{fisher_two_sided(a, an - a, c, cn - c):.4g}"
        )
    ids = {r["request_id"] for r in records}
    k, n = _attempt1_stats([r for r in arm_r if r["request_id"] in ids])
    print(f"same artifacts in Arm R (full-res, earlier session): {_rate(k, n)}")


ARM_F_IMAGES: tuple[str, str] = ("annotated", "raw")


def _paired_refusal_counts(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, tuple[int, int]]]:
    """Per artifact, the attempt-1 refusals and runs under each image."""
    paired: dict[str, dict[str, tuple[int, int]]] = defaultdict(dict)
    for request_id in {r["request_id"] for r in records}:
        for image in ARM_F_IMAGES:
            group = [
                r for r in records if r["request_id"] == request_id and r["image"] == image
            ]
            paired[request_id][image] = _attempt1_stats(group)
    return paired


def _arm_f_paired_test(records: list[dict[str, Any]], label: str) -> None:
    """Print the artifact-paired annotated-vs-raw refusal comparison for one subset.

    The artifact is the unit of analysis: each contributes one refusal count per
    image, and the sign test asks how many artifacts refuse more under one image
    than the other. The pooled run-level rate is printed alongside as a
    descriptive figure, not as the inferential claim, because replicates of the
    same artifact are not independent.

    Args:
        records: Arm-F call records for the subset.
        label: Subset name for the heading.
    """
    paired = _paired_refusal_counts(records)
    rates = {
        image: (
            sum(paired[rid][image][0] for rid in paired),
            sum(paired[rid][image][1] for rid in paired),
        )
        for image in ARM_F_IMAGES
    }
    (a, an), (c, cn) = rates["annotated"], rates["raw"]
    b_pairs = sum(
        1
        for rid in paired
        if paired[rid]["annotated"][0] > paired[rid]["raw"][0]
    )
    c_pairs = sum(
        1
        for rid in paired
        if paired[rid]["raw"][0] > paired[rid]["annotated"][0]
    )
    print(
        f"\n{label}: {len(paired)} artifacts; annotated {_rate(a, an)} vs "
        f"raw {_rate(c, cn)} of runs (fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g})"
    )
    print(
        f"  paired by artifact: annotated>raw {b_pairs}, raw>annotated {c_pairs}, "
        f"tied {len(paired) - b_pairs - c_pairs}, exact McNemar p="
        f"{mcnemar_exact(b_pairs, c_pairs):.4g}"
    )


def analyze_arm_f(records: list[dict[str, Any]]) -> None:
    """Print the annotated-vs-raw frame refusal comparison and the retry reconciliation.

    Args:
        records: Every recorded Arm-F call.
    """
    print("\n## Arm F (annotated overlay against the raw camera frame)")
    print("image,artifacts,runs,attempt1_refusals,rate,terminal_refusals,mean_attempts")
    for image in ARM_F_IMAGES:
        group = [r for r in records if r["image"] == image]
        if not group:
            continue
        k, n = _attempt1_stats(group)
        terminal = sum(int(terminal_refusal(r)) for r in group)
        mean_attempts = sum(r["n_attempts"] for r in group) / len(group)
        print(
            f"{image},{len({r['request_id'] for r in group})},{n},{k},"
            f"{(k / n if n else 0):.3f},{terminal},{mean_attempts:.2f}"
        )

    _arm_f_paired_test(records, "all artifacts")
    tight = [
        r
        for r in records
        if r.get("raw_frame_skew_sec") is not None
        and abs(r["raw_frame_skew_sec"]) <= ARM_F_TIGHT_SKEW_SEC
    ]
    if tight:
        _arm_f_paired_test(tight, f"|skew| <= {ARM_F_TIGHT_SKEW_SEC} s")

    print("\n### Stimulus locking (did the live refusers refuse again?)")
    print("live_attempt1_refusal,image,artifacts,runs,attempt1_refusals,rate")
    for flag in (True, False):
        subset = [r for r in records if r["live_attempt1_refusal"] is flag]
        for image in ARM_F_IMAGES:
            group = [r for r in subset if r["image"] == image]
            k, n = _attempt1_stats(group)
            print(
                f"{flag},{image},{len({r['request_id'] for r in group})},{n},{k},"
                f"{(k / n if n else 0):.3f}"
            )
    for image in ARM_F_IMAGES:
        group = [r for r in records if r["image"] == image]
        a = sum(int(r["attempt1_refusal"]) for r in group if r["live_attempt1_refusal"])
        an = sum(1 for r in group if r["live_attempt1_refusal"])
        c = sum(int(r["attempt1_refusal"]) for r in group if not r["live_attempt1_refusal"])
        cn = sum(1 for r in group if not r["live_attempt1_refusal"])
        print(
            f"{image}: live-refused {_rate(a, an)} vs live-valid {_rate(c, cn)}, "
            f"fisher p={fisher_two_sided(a, an - a, c, cn - c):.4g}"
        )

    print("\n### Retry policy at the shipped max_attempts, conditional on a refused attempt 1")
    print("image,refused_attempt1,still_terminal,conditional_terminal_rate,mean_attempts")
    for image in ARM_F_IMAGES:
        refused = [r for r in records if r["image"] == image and r["attempt1_refusal"]]
        if not refused:
            continue
        terminal = sum(int(terminal_refusal(r)) for r in refused)
        mean_attempts = sum(r["n_attempts"] for r in refused) / len(refused)
        print(
            f"{image},{len(refused)},{terminal},{terminal / len(refused):.3f},"
            f"{mean_attempts:.2f}"
        )


SUMMARY_FIELDS = [
    "arm",
    "run",
    "request_id",
    "order",
    "image",
    "obstacle_text",
    "policy",
    "n",
    "attempt1_refusals",
    "attempt1_refusal_rate",
    "terminal_refusals",
    "decided",
    "yield_decisions",
    "yield_robot_1",
    "yield_first_listed",
    "yield_correct",
    "think_obstacle_mentions",
    "errors",
    "prompt_tokens",
    "completion_tokens",
]

# Rows recorded before the obstacle-text factor existed carry no flag; every one
# of them rendered the run's own setting.
_STORED_TEXT = "stored"


def write_summary(records: list[dict[str, Any]], out_dir: Path) -> None:
    """Aggregate call records into `summary.csv`, one row per cell group.

    Args:
        records: Every recorded call (this run plus any resumed ones).
        out_dir: Directory receiving `summary.csv`.
    """
    buckets: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for record in records:
        key = (
            record["arm"],
            record["run"],
            record["request_id"],
            record["order"],
            record["image"],
            _STORED_TEXT if record.get("obstacle_text") is None else str(record["obstacle_text"]),
            record["policy"],
        )
        bucket = buckets[key]
        bucket["n"] += 1
        bucket["attempt1_refusals"] += int(record.get("attempt1_refusal", False))
        bucket["terminal_refusals"] += int(terminal_refusal(record))
        bucket["think_obstacle_mentions"] += int(record.get("think_obstacle_mention", False))
        bucket["errors"] += int(bool(record.get("error")))
        decision = record.get("decision")
        bucket["decided"] += int(decision is not None)
        if decision and decision.get("strategy") == "yield":
            bucket["yield_decisions"] += 1
            yielder = decision.get("yield_robot")
            bucket["yield_robot_1"] += int(yielder == "robot_1")
            first_listed = "robot_1" if record["order"] == "id_asc" else "robot_2"
            bucket["yield_first_listed"] += int(yielder == first_listed)
            bucket["yield_correct"] += int(yielder == record.get("correct_yielder"))
        for attempt in record.get("attempts") or []:
            usage = attempt.get("token_usage") or {}
            bucket["prompt_tokens"] += usage.get("prompt_tokens", 0)
            bucket["completion_tokens"] += usage.get("completion_tokens", 0)

    with (out_dir / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for key in sorted(buckets, key=str):
            v = buckets[key]
            row = dict(zip(SUMMARY_FIELDS[:7], key, strict=True))
            row["n"] = int(v["n"])
            row["attempt1_refusals"] = int(v["attempt1_refusals"])
            row["attempt1_refusal_rate"] = f"{v['attempt1_refusals'] / v['n']:.3f}"
            for name in SUMMARY_FIELDS[10:]:
                row[name] = int(v[name])
            writer.writerow(row)
    print(f"wrote {out_dir / 'summary.csv'}")


def load_records(out_dir: Path) -> list[dict[str, Any]]:
    """Read every recorded call from `calls.jsonl`."""
    path = out_dir / "calls.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def print_integrity(result: IntegrityResult, total: int) -> None:
    """Print the reconstruction-integrity tally and any mismatches."""
    print(f"reconstruction: {len(result.matched)}/{total} exact SHA-256 matches")
    if result.mismatched:
        print(f"  {len(result.mismatched)} mismatches:")
        for artifact, detail in result.mismatched:
            print(f"    {artifact.run} {artifact.request_id[:8]}: {detail}")
    if result.missing_image:
        print(f"  {len(result.missing_image)} matched prompts with a missing frame PNG:")
        for artifact in result.missing_image:
            print(f"    {artifact.run} {artifact.request_id[:8]}: {artifact.image_path}")


def main() -> None:
    """Parse arguments and run the requested arm (or the integrity check alone)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arm",
        choices=[
            "integrity", "R", "grey", "O", "M", "S", "D", "S2", "F", "X",
            "summary", "analyze",
        ],
        default="integrity",
        help="which arm to run; 'integrity' only checks reconstruction",
    )
    parser.add_argument(
        "--runs",
        choices=sorted(RUN_SETS),
        default="batch1",
        help="which pilot batch's runs to load",
    )
    parser.add_argument(
        "--extra-records",
        type=Path,
        nargs="*",
        default=[],
        help="additional experiment directories whose calls.jsonl joins the analysis",
    )
    parser.add_argument("--n", type=int, default=3, help="replicates per cell")
    parser.add_argument("--controls", type=int, default=10, help="grey-arm control count")
    parser.add_argument(
        "--m-artifacts", type=int, default=3, help="arm-M artifact count (strongest refusers)"
    )
    parser.add_argument(
        "--pace-sec", type=float, default=5.2, help="minimum seconds between API calls"
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    artifacts = load_artifacts(runs=RUN_SETS[args.runs], runs_dir=args.runs_dir)
    integrity = check_integrity(artifacts)
    print_integrity(integrity, len(artifacts))
    matched = integrity.matched
    if args.arm == "integrity":
        return
    if args.arm == "summary":
        write_summary(load_records(args.out_dir), args.out_dir)
        return
    if args.arm == "analyze":
        records = load_records(args.out_dir)
        live_refusals = sum(1 for a in artifacts if a.live_attempt1_refusal)
        print(f"live attempt-1 refusals on these stimuli: {live_refusals}/{len(artifacts)}")
        # Only this directory's own rows go into its summary; pooled rows are for
        # the cross-batch tables alone.
        write_summary(records, args.out_dir)
        for extra in args.extra_records:
            extra_records = load_records(extra)
            print(f"pooling {len(extra_records)} records from {extra}")
            records += extra_records
        analyze(records, artifacts)
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.arm == "R":
        cells = build_arm_r_cells(matched, args.n)
    elif args.arm == "grey":
        with Image.open(matched[0].image_path) as image:
            size = image.size
        grey = make_grey_image(args.out_dir / "images" / f"grey_{size[0]}x{size[1]}.png", size)
        refused, controls = select_grey_pairs(matched, args.controls)
        print(f"grey arm: {len(refused)} live-refused, {len(controls)} controls, image {size}")
        cells = build_grey_cells(refused, controls, grey, args.n)
    elif args.arm == "O":
        yields = first_yield_artifacts(matched)
        print(f"arm O: {len(yields)} first-yield artifacts: " + ", ".join(
            f"{a.run}/{a.request_id[:8]}({a.stored_order})" for a in yields
        ))
        cells = build_arm_o_cells(yields, args.n)
    elif args.arm in ("S", "S2"):
        standoffs = select_standoff_artifacts(matched)
        sizes = {Image.open(a.image_path).size for a in standoffs}
        if len(sizes) != 1:
            raise ValueError(f"standoff frames differ in size: {sorted(sizes)}")
        size = sizes.pop()
        grey = make_grey_image(args.out_dir / "images" / f"grey_{size[0]}x{size[1]}.png", size)
        by_side_count = defaultdict(int)
        for a in standoffs:
            by_side_count[a.obstacle_side] += 1
        print(
            f"arm {args.arm}: {len(standoffs)} standoff artifacts "
            f"({dict(by_side_count)}), grey {size}: "
            + ", ".join(f"{a.run}/{a.request_id[:8]}" for a in standoffs)
        )
        cells = build_arm_s_cells(standoffs, grey, args.n, args.arm)
    elif args.arm == "F":
        missing = [a for a in matched if not a.raw_image_path.is_file()]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)} artifacts have no raw frame, first: "
                f"{missing[0].raw_image_path}"
            )
        no_skew = [a for a in matched if a.raw_frame_skew_sec is None]
        print(
            f"arm F: {len(matched)} artifacts x annotated/raw x {args.n}; "
            f"{len(no_skew)} without a logged skew"
        )
        cells = build_arm_f_cells(matched, args.n)
    elif args.arm == "X":
        refused = [a for a in matched if a.live_attempt1_refusal]
        print(
            f"arm X: {len(refused)} live-refused artifacts x "
            f"{len(ARM_X_POLICIES)} policies x {args.n}"
        )
        cells = build_arm_x_cells(refused, args.n)
    elif args.arm == "D":
        refused = [a for a in matched if a.live_attempt1_refusal]
        downscaled = {
            a.request_id: make_downscaled_image(
                a.image_path,
                args.out_dir
                / "images"
                / f"down{ARM_D_DOWNSCALE_WIDTH_PX}_{a.request_id[:8]}.png",
            )
            for a in refused
        }
        print(f"arm D: {len(refused)} live-refused artifacts, downscaled to "
              f"{ARM_D_DOWNSCALE_WIDTH_PX} px wide")
        cells = build_arm_d_cells(refused, downscaled, args.n)
    else:
        rates: dict[str, list[int]] = defaultdict(list)
        for record in load_records(args.out_dir):
            if record["arm"] == "R":
                rates[record["request_id"]].append(int(record["attempt1_refusal"]))
        refusing_ids = [rid for rid, hits in rates.items() if any(hits)]
        # Budget is finite, so Arm M runs the strongest refusers: those that
        # refused on the most Arm-R replicates.
        refusing_ids.sort(key=lambda rid: (-sum(rates[rid]), rid))
        by_id = {a.request_id: a for a in matched}
        refusing = [by_id[rid] for rid in refusing_ids[: args.m_artifacts]]
        print(
            f"arm M: {len(refusing_ids)} artifacts refused at least once in Arm R; "
            f"running the top {len(refusing)}: "
            + ", ".join(f"{a.request_id[:8]}({sum(rates[a.request_id])}/3)" for a in refusing)
        )
        cells = build_arm_m_cells(refusing, args.n)

    if args.dry_run:
        print(f"{len(cells)} cells (dry run)")
        return
    execute(cells, args.out_dir, args.pace_sec)
    write_summary(load_records(args.out_dir), args.out_dir)


if __name__ == "__main__":
    main()
