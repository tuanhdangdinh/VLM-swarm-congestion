"""Offline probe: does the VLM's chosen yielder follow slot, ID, or geometry?

A prior finding (2026-09-19) is that every live gpt-4o yield on the head-on
asymmetric family named `robot_1` — the robot the prompt always presents first —
even on the variant where a parked box makes `robot_1` unable to yield. Choice
and presentation order were perfectly confounded. This probe counterbalances the
presentation order offline and reports which of three signatures the data match:

- H_slot: the chosen yielder is whichever robot is listed first.
- H_id: the chosen yielder is always `robot_1`.
- H_geom: the chosen yielder is the scenario oracle's `correct_yielder`.

The probe is offline: it rebuilds the deadlock-onset `ReasonerRequest` M5 would
send and renders a synthetic top-down plan view instead of a live M1 annotated
frame. Results are indicative only and must be confirmed by live runs.

Usage:

    set -a; source .env; set +a
    python scripts/probe_presentation_order.py --dry-run     # prompts only, no API
    python scripts/probe_presentation_order.py
    python scripts/probe_presentation_order.py --models gpt-4o,gpt-4o-mini
    python scripts/probe_presentation_order.py --backend gemini --seeds 15

The `openai` backend varies `temperature` per job. The `gemini` backend cannot:
the Interactions API's `generation_config` has no `temperature`/`top_p`/`top_k`
fields at all, only `seed`, `max_output_tokens` and `thinking_level`. Under
`--backend gemini` the within-cell samples are therefore distinct `seed` values
rather than repeated draws at one temperature, and every record carries the
sampling fields the backend had to drop (`unsupported_sampling`).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import threading
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "isaac") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "isaac"))

from vgu_sim.config import ScenarioConfig  # noqa: E402

from reasoning.vlm.backend_base import VLMBackend  # noqa: E402
from reasoning.vlm.backend_factory import (  # noqa: E402
    BackendConfig,
    backend_section,
    build_backend,
    resolve_reasoner_config,
)
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    GeminiBackendConfig,
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    ReasonerResult,
    RobotPresentationOrder,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402

DEFAULT_OUT_DIR = Path("data/experiments/2026-09-25-presentation-order")
FAMILY_DIR = Path("isaac/config/scenarios/family")
MODELS_YAML = Path("config/models.yaml")

# Deadlock onset as M5 sees it: both robots STOPPED nose-to-nose in the corridor
# centre. 0.45 m apart is one robot body-length, inside the 0.5 m conflict radius
# the prompt's guidance uses, and matches the standoff distance the live runs
# triggered at.
_ONSET_HALF_GAP_M = 0.225
_ONSET_STAMP = 20.0
_FRAME_ID = "overhead_camera"

# Overhead camera ROI (vgu_sim CameraConfig): 6.0 m x 4.5 m onto 1280 x 960 px.
_IMAGE_W, _IMAGE_H = 1280, 960
_ROI_W_M, _ROI_H_M = 6.0, 4.5
_PX_PER_M = _IMAGE_W / _ROI_W_M

# M1 annotation constants (swarm_perception/annotation.py) so the synthetic frame
# reads like the annotated frame M5 actually forwards.
_BOX_HALF_PX = 20
_ARROW_LENGTH_PX = 40
_GOAL_RADIUS_PX = 8
_STOPPED_COLOR = (200, 0, 0)
_FLOOR_COLOR = (235, 235, 235)
_WALL_COLOR = (90, 90, 90)
_OBSTACLE_COLOR = (140, 110, 70)
_BARRIER_THICKNESS_M = 0.1

# OpenAI rejects a bad key with HTTP 401/403; the Gemini Interactions API answers
# HTTP 400 with an API_KEY_INVALID body and HTTP 403 with PERMISSION_DENIED, so the
# status code alone does not separate "bad credentials" from "bad request".
_AUTH_MARKERS = (
    "HTTP 401",
    "HTTP 403",
    "API_KEY_INVALID",
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
)
# The temperature column's value for backends whose samples are seeds, not draws.
_SEEDED_TEMPERATURE = "seeded"
_DEFAULT_SEEDS = 15
# Backoff after a transport failure. The shipped account caps gpt-4o at 30k
# tokens per minute and one probe call costs ~1.9k, so an unpaced run spends
# most of its calls on HTTP 429 instead of on data.
_BACKOFF_BASE_SEC = 5.0
_BACKOFF_CAP_SEC = 60.0
_ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")
_CHANNELS: tuple[bool, ...] = (False, True)

Hypothesis = Literal["H_slot", "H_id", "H_geom", "mixed", "insufficient"]


class AuthError(RuntimeError):
    """The API rejected the credentials; the whole run is aborted, not one cell."""


class Pacer:
    """Spaces out backend calls so a run stays inside the account's tokens-per-minute cap."""

    def __init__(self, min_interval_sec: float) -> None:
        self._min_interval_sec = min_interval_sec
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Block until this thread's turn, then reserve the next slot."""
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + self._min_interval_sec
        if delay > 0:
            time.sleep(delay)


class PacedBackend:
    """Backend decorator that paces every call, including `Reasoner`'s internal retries.

    It reports the wrapped call's own duration as `latency_ms`. Without that,
    `invoke_backend` would time the rate-limit wait too and every record after a
    run's first would read `workers * min_interval_sec` instead of a response time.
    """

    def __init__(self, backend: VLMBackend, pacer: Pacer) -> None:
        self._backend = backend
        self._pacer = pacer

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Pace, then delegate to the wrapped backend and time only that call."""
        self._pacer.wait()
        start = time.monotonic()
        response = self._backend.analyze(payload, config)
        if response.latency_ms is not None:
            return response
        return response.model_copy(
            update={"latency_ms": int((time.monotonic() - start) * 1000)}
        )


@dataclass(frozen=True)
class Cell:
    """One counterbalanced condition: variant x presentation order x obstacle channel."""

    variant: str
    order: RobotPresentationOrder
    obstacle_channel: bool

    @property
    def key(self) -> str:
        channel = "obs_on" if self.obstacle_channel else "obs_off"
        return f"{self.variant}__{self.order}__{channel}"


def load_family_scenarios(directory: Path) -> dict[str, ScenarioConfig]:
    """Load every head-on family scenario with the project's own config model.

    Args:
        directory: Directory holding the family `*.yaml` scenario files.

    Returns:
        Scenario configs keyed by the scenario `name` field.

    Raises:
        FileNotFoundError: If the directory holds no scenario YAML files.
    """
    paths = sorted(p for p in directory.glob("*.yaml"))
    if not paths:
        raise FileNotFoundError(f"no scenario yaml files under {directory}")
    scenarios: dict[str, ScenarioConfig] = {}
    for path in paths:
        config = ScenarioConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        scenarios[config.name] = config
    return scenarios


def variant_label(scenario_name: str) -> str:
    """Shorten `head_on_asymmetric_w0p2_eopen_o0` to its `w0p2_eopen` variant label."""
    stem = scenario_name.removeprefix("head_on_asymmetric_")
    return stem.removesuffix("_o0")


def world_to_pixel(x: float, y: float) -> tuple[int, int]:
    """Project a world-frame point onto the synthetic overhead image.

    Args:
        x: World x in metres (+x east).
        y: World y in metres (+y north).

    Returns:
        Pixel coordinate `(u, v)`; image v grows downward, so +y maps to -v.
    """
    return (
        int(round(_IMAGE_W / 2 + x * _PX_PER_M)),
        int(round(_IMAGE_H / 2 - y * _PX_PER_M)),
    )


def _box_pixels(x: float, y: float, size_x_m: float, size_y_m: float) -> tuple[int, int, int, int]:
    left, top = world_to_pixel(x - size_x_m / 2, y + size_y_m / 2)
    right, bottom = world_to_pixel(x + size_x_m / 2, y - size_y_m / 2)
    return left, top, right, bottom


def render_plan_view(
    scenario: ScenarioConfig,
    robot_states: Sequence[RobotStateInput],
    dest_path: Path,
) -> None:
    """Draw a deterministic synthetic top-down plan view of the onset scene.

    Stands in for the live M1 annotated frame: same ROI and scale, same
    status-coloured box, ID label, heading arrow and goal marker conventions as
    `swarm_perception/annotation.py`. It is not a camera image and carries no
    ArUco markers, lighting or perspective.

    Goals are drawn from the scenario rather than from `robot_states`, because
    M1 reads them from M5's task registry and annotates them even though the
    `ReasonerRequest` M5 builds never carries them as text.

    Args:
        scenario: Scenario supplying the aisle barrier, obstacles and goals.
        robot_states: Robot states to draw, in any order.
        dest_path: PNG file to write (parents created).
    """
    goals = {robot.robot_id: (robot.goal.x, robot.goal.y) for robot in scenario.robots}
    image = Image.new("RGB", (_IMAGE_W, _IMAGE_H), _FLOOR_COLOR)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    barrier = scenario.aisle_barrier
    if barrier is not None:
        half_width = barrier.effective_width_m / 2
        for side in (1.0, -1.0):
            centre_y = side * (half_width + _BARRIER_THICKNESS_M / 2)
            draw.rectangle(
                _box_pixels(barrier.center_x_m, centre_y, barrier.length_m, _BARRIER_THICKNESS_M),
                fill=_WALL_COLOR,
            )

    for obstacle in scenario.static_obstacles:
        draw.rectangle(
            _box_pixels(obstacle.pose.x, obstacle.pose.y, obstacle.size.x_m, obstacle.size.y_m),
            fill=_OBSTACLE_COLOR,
        )

    for state in sorted(robot_states, key=lambda s: s.robot_id):
        cx, cy = world_to_pixel(state.x, state.y)
        draw.rectangle(
            (cx - _BOX_HALF_PX, cy - _BOX_HALF_PX, cx + _BOX_HALF_PX, cy + _BOX_HALF_PX),
            outline=_STOPPED_COLOR,
            width=2,
        )
        draw.text((cx - _BOX_HALF_PX, cy - _BOX_HALF_PX - 14), state.robot_id,
                  fill=_STOPPED_COLOR, font=font)
        tip = (
            int(round(cx + _ARROW_LENGTH_PX * math.cos(state.theta))),
            int(round(cy - _ARROW_LENGTH_PX * math.sin(state.theta))),
        )
        draw.line(((cx, cy), tip), fill=_STOPPED_COLOR, width=3)
        draw.ellipse(
            (tip[0] - 5, tip[1] - 5, tip[0] + 5, tip[1] + 5), fill=_STOPPED_COLOR
        )
        goal = goals.get(state.robot_id)
        if goal is not None:
            gx, gy = world_to_pixel(*goal)
            draw.ellipse(
                (gx - _GOAL_RADIUS_PX, gy - _GOAL_RADIUS_PX,
                 gx + _GOAL_RADIUS_PX, gy + _GOAL_RADIUS_PX),
                outline=_STOPPED_COLOR,
                width=2,
            )
            draw.line(((gx - _GOAL_RADIUS_PX, gy), (gx + _GOAL_RADIUS_PX, gy)),
                      fill=_STOPPED_COLOR)
            draw.line(((gx, gy - _GOAL_RADIUS_PX), (gx, gy + _GOAL_RADIUS_PX)),
                      fill=_STOPPED_COLOR)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest_path, format="PNG")


def build_onset_robot_states(scenario: ScenarioConfig) -> list[RobotStateInput]:
    """Build the two STOPPED robot states M5 would report at deadlock onset.

    Headings and IDs come from the scenario spawns; the positions are the
    corridor-centre standoff, not the spawns. `goal` and `task` are deliberately
    left unset: `build_reasoner_request` projects a `SceneSnapshot`, whose
    `RobotView` carries neither, so no live prompt has ever contained them.

    Args:
        scenario: Scenario supplying robot IDs and spawn headings.

    Returns:
        One `RobotStateInput` per scenario robot, in scenario order.
    """
    states: list[RobotStateInput] = []
    for robot in scenario.robots:
        heading = robot.spawn.yaw_rad
        offset = _ONSET_HALF_GAP_M if math.cos(heading) < 0 else -_ONSET_HALF_GAP_M
        states.append(
            RobotStateInput(
                robot_id=robot.robot_id,
                x=offset,
                y=0.0,
                theta=heading,
                linear_velocity=0.0,
                status="STOPPED",
            )
        )
    return states


def scenario_prompt_obstacles(scenario: ScenarioConfig) -> list[StaticObstacleInput]:
    """Project the scenario's static obstacles onto neutral prompt-facing IDs.

    The prompt renders obstacle ids verbatim, so the probe follows the shipped M5
    config and renumbers them: the scenario file's `blocker_west` would tell the
    model both that the box is an obstruction and which side it obstructs — the
    inference under test.

    Args:
        scenario: Scenario supplying the static obstacles.

    Returns:
        One `StaticObstacleInput` per scenario obstacle, ids `obstacle_1` upward.
    """
    return [
        StaticObstacleInput(
            obstacle_id=f"obstacle_{index}",
            x=obstacle.pose.x,
            y=obstacle.pose.y,
            size_x_m=obstacle.size.x_m,
            size_y_m=obstacle.size.y_m,
        )
        for index, obstacle in enumerate(scenario.static_obstacles, start=1)
    ]


def build_cell_request(
    cell: Cell,
    scenario: ScenarioConfig,
    robot_states: Sequence[RobotStateInput],
    image_path: Path,
) -> ReasonerRequest:
    """Build the `ReasonerRequest` for one probe cell, mirroring M5's live build.

    Args:
        cell: The condition being rendered.
        scenario: Scenario supplying the static obstacles.
        robot_states: Onset robot states.
        image_path: Synthetic plan view for this variant.

    Returns:
        A frozen `ReasonerRequest` with `failure_context=None` (first decision of
        an episode) and the shipped M5 pairwise-geometry modality (on).
    """
    return ReasonerRequest(
        request_id=cell.key,
        image_path=str(image_path),
        frame_id=_FRAME_ID,
        stamp=_ONSET_STAMP,
        robot_states=list(robot_states),
        failure_context=None,
        include_pairwise_geometry=True,
        static_obstacles=scenario_prompt_obstacles(scenario),
        include_static_obstacles=cell.obstacle_channel,
        robot_presentation_order=cell.order,
    )


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_BACKEND_CONFIG_TYPES = {"openai": OpenAIBackendConfig, "gemini": GeminiBackendConfig}


def load_backend_settings(
    models_yaml: Path, backend_id: str
) -> tuple[dict, ReasonerConfig, BackendConfig]:
    """Read one shipped backend's settings so the probe is configured as M5 is.

    Args:
        models_yaml: Path to `config/models.yaml`.
        backend_id: `"openai"` or `"gemini"`.

    Returns:
        The raw `vlm:` mapping, the resolved reasoner config, and the backend config.

    Raises:
        ValueError: If `backend_id` is not a backend this probe supports.
    """
    if backend_id not in _BACKEND_CONFIG_TYPES:
        raise ValueError(f"probe does not support backend {backend_id!r}")
    raw_vlm = yaml.safe_load(models_yaml.read_text(encoding="utf-8"))["vlm"]
    reasoner_config = resolve_reasoner_config(raw_vlm, backend_id)
    backend_config = _BACKEND_CONFIG_TYPES[backend_id](**backend_section(raw_vlm, backend_id))
    return raw_vlm, reasoner_config, backend_config


def _is_auth_failure(result: ReasonerResult) -> bool:
    message = result.diagnostics.error_message or ""
    return any(marker in message for marker in _AUTH_MARKERS)


def _is_transport_failure(result: ReasonerResult) -> bool:
    return result.decision is None and result.diagnostics.error_type in {
        "ConnectionError",
        "BackendTimeoutError",
    }


def run_sample(reasoner: Reasoner, request: ReasonerRequest, max_retries: int) -> tuple[
    ReasonerResult, int
]:
    """Run one sample, retrying transport failures and aborting on auth failures.

    `OpenAIBackend` maps every HTTP >= 400 onto `ConnectionError` and `Reasoner`
    swallows it into `decision=None`, so an auth failure is detected by reading
    the diagnostics message rather than by catching an exception.

    Args:
        reasoner: Production M2 reasoner (parsing and validation included).
        request: The request for this cell.
        max_retries: Extra attempts after the first transport failure.

    Returns:
        The final result and the number of retries spent.

    Raises:
        AuthError: If the API reported HTTP 401 or 403.
    """
    retries = 0
    while True:
        result = reasoner.run(request)
        if _is_auth_failure(result):
            raise AuthError(result.diagnostics.error_message or "authentication rejected")
        if not _is_transport_failure(result) or retries >= max_retries:
            return result, retries
        # Jittered exponential backoff: without the jitter every worker that hit
        # the same rate-limit window would come back at the same instant.
        delay = min(_BACKOFF_CAP_SEC, _BACKOFF_BASE_SEC * 2**retries)
        time.sleep(delay * (0.5 + random.random()))
        retries += 1


def _decision_record(result: ReasonerResult) -> dict[str, object] | None:
    decision = result.decision
    if decision is None:
        return None
    return {
        "congestion_detected": decision.congestion_detected,
        "type": decision.type,
        "strategy": decision.strategy,
        "yield_robot": decision.yield_robot,
        "involved_robots": list(decision.involved_robots),
        "root_cause": decision.root_cause,
        "justification": decision.justification,
    }


@dataclass(frozen=True)
class Job:
    """One planned API call.

    `seed` is set only for backends whose within-cell samples are distinct seeds
    rather than repeated draws at one temperature (`gemini`). It is `None` for the
    temperature-swept `openai` path, and a `None` seed keeps the persisted record
    byte-identical to the pre-feature one.
    """

    cell: Cell
    temperature: float
    sample_index: int
    seed: int | None = None


def build_call_record(
    model: str,
    job: Job,
    cell_context: CellContext,
    result: ReasonerResult,
    retries: int,
) -> dict[str, object]:
    """Assemble the JSONL record persisted for one call.

    A seeded job adds `seed` and `unsupported_sampling`; a temperature-swept job
    omits both keys entirely rather than writing nulls, so records written by the
    default `openai` path stay byte-identical to the pre-feature ones.
    """
    record: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "cell": job.cell.key,
        "variant": job.cell.variant,
        "presentation_order": job.cell.order,
        "obstacle_channel": "on" if job.cell.obstacle_channel else "off",
        "temperature": job.temperature,
        "sample_index": job.sample_index,
        "prompt_sha256": cell_context.prompt_sha256,
        "image_path": str(cell_context.image_path),
        "image_synthetic": True,
        "first_listed_robot": cell_context.first_listed_robot,
        "correct_yielder": cell_context.correct_yielder,
        "fcfs_yielder": cell_context.fcfs_yielder,
        "parse_status": result.diagnostics.parse_status,
        "attempts": result.diagnostics.attempts,
        "transport_retries": retries,
        "latency_ms": result.diagnostics.latency_ms,
        "token_usage": result.diagnostics.token_usage,
        "error_type": result.diagnostics.error_type,
        "error_message": result.diagnostics.error_message,
        "raw_text": result.raw_text,
        "decision": _decision_record(result),
    }
    if job.seed is not None:
        record["seed"] = job.seed
        record["unsupported_sampling"] = result.diagnostics.unsupported_sampling
    return record


@dataclass(frozen=True)
class CellContext:
    """Everything fixed about a cell: its request, prompt hash and oracle answers."""

    cell: Cell
    request: ReasonerRequest
    prompt_sha256: str
    image_path: Path
    first_listed_robot: str
    correct_yielder: str
    fcfs_yielder: str


def prepare_cells(
    scenarios: dict[str, ScenarioConfig], out_dir: Path, prompt_dir: Path | None = None
) -> dict[str, CellContext]:
    """Render every variant's image and prompt, and build one context per cell.

    Args:
        scenarios: Family scenarios keyed by name.
        out_dir: Results directory; images are written to `<out_dir>/images`.
        prompt_dir: Where the rendered prompts go; defaults to `<out_dir>/prompts`.
            A per-model directory keeps a new run from overwriting the prompts an
            earlier model's committed results are checked against.

    Returns:
        Cell contexts keyed by `Cell.key`.
    """
    prompt_dir = prompt_dir if prompt_dir is not None else out_dir / "prompts"
    contexts: dict[str, CellContext] = {}
    for name in sorted(scenarios):
        scenario = scenarios[name]
        variant = variant_label(name)
        states = build_onset_robot_states(scenario)
        image_path = out_dir / "images" / f"{variant}.png"
        render_plan_view(scenario, states, image_path)
        oracle = scenario.oracle
        if oracle is None:
            raise ValueError(f"scenario {name} has no oracle block")
        for order in _ORDERS:
            for channel in _CHANNELS:
                cell = Cell(variant=variant, order=order, obstacle_channel=channel)
                request = build_cell_request(cell, scenario, states, image_path)
                payload = build_prompt_payload(request)
                prompt_path = prompt_dir / f"{cell.key}.txt"
                prompt_path.parent.mkdir(parents=True, exist_ok=True)
                prompt_path.write_text(payload.user_prompt, encoding="utf-8")
                contexts[cell.key] = CellContext(
                    cell=cell,
                    request=request,
                    prompt_sha256=sha256_text(payload.user_prompt),
                    image_path=image_path,
                    first_listed_robot=payload.known_robot_ids[0],
                    correct_yielder=oracle.correct_yielder,
                    fcfs_yielder=oracle.fcfs_yielder,
                )
    return contexts


def plan_jobs(
    contexts: Iterable[CellContext], n_greedy: int, n_sampled: int, sampled_temperature: float
) -> list[Job]:
    """Enumerate every planned call: `n_greedy` at T=0.0 plus `n_sampled` at the sampled T."""
    jobs: list[Job] = []
    for context in contexts:
        for index in range(n_greedy):
            jobs.append(Job(cell=context.cell, temperature=0.0, sample_index=index))
        for index in range(n_sampled):
            jobs.append(
                Job(cell=context.cell, temperature=sampled_temperature, sample_index=index)
            )
    return jobs


def plan_seeded_jobs(
    contexts: Iterable[CellContext], n_seeds: int, temperature: float
) -> list[Job]:
    """Enumerate one call per cell per seed `0..n_seeds-1`.

    Used for backends with no temperature control: the within-cell variation comes
    from `seed`, and `temperature` is carried on every job only to record what the
    shipped reasoner config asked for and the backend could not honour.

    Args:
        contexts: Cell contexts to cover.
        n_seeds: Number of distinct seeds per cell.
        temperature: The resolved reasoner temperature, recorded not sent.

    Returns:
        `n_seeds` jobs per cell, with seeds `0..n_seeds-1`.

    Raises:
        ValueError: If `n_seeds` is not positive.
    """
    if n_seeds < 1:
        raise ValueError(f"n_seeds must be >= 1, got {n_seeds}")
    return [
        Job(cell=context.cell, temperature=temperature, sample_index=seed, seed=seed)
        for context in contexts
        for seed in range(n_seeds)
    ]


def build_paced_backends(
    backend_id: str,
    backend_config: BackendConfig,
    model: str,
    jobs: Sequence[Job],
    pacer: Pacer,
) -> dict[int | None, VLMBackend]:
    """Build one paced backend per distinct seed in `jobs`, sharing one pacer.

    A seed is a backend-construction argument, not a per-call one, so a seeded run
    needs one backend instance per seed. They share a single `Pacer` so the run's
    overall request rate is unchanged by how many seeds it sweeps.

    Args:
        backend_id: Backend selector passed to `build_backend`.
        backend_config: Shipped backend config; `model_id` and `seed` are overridden.
        model: Model ID to send.
        jobs: Planned calls, whose `seed` values decide how many backends are built.
        pacer: Shared rate limiter.

    Returns:
        Paced backends keyed by seed (`None` for the unseeded path).
    """
    backends: dict[int | None, VLMBackend] = {}
    for seed in sorted({job.seed for job in jobs}, key=lambda s: (s is not None, s)):
        update: dict[str, object] = {"model_id": model}
        if seed is not None:
            update["seed"] = seed
        backends[seed] = PacedBackend(
            build_backend(backend_id, backend_config.model_copy(update=update)), pacer
        )
    return backends


def run_model(
    model: str,
    contexts: dict[str, CellContext],
    jobs: Sequence[Job],
    reasoner_config: ReasonerConfig,
    backend_config: BackendConfig,
    out_dir: Path,
    workers: int,
    max_retries: int,
    min_interval_sec: float,
    backend_id: str = "openai",
) -> list[dict[str, object]]:
    """Run every planned call for one model, appending each to `calls.jsonl` as it lands.

    Args:
        model: Model ID to send.
        contexts: Cell contexts keyed by cell key.
        jobs: Planned calls.
        reasoner_config: Shipped reasoner config; temperature is overridden per job.
        backend_config: Shipped backend config; `model_id` (and `seed`) are overridden.
        out_dir: Results root; records land in `<model>/calls.jsonl`.
        workers: Concurrent calls.
        max_retries: Transport retries per sample.
        min_interval_sec: Minimum spacing between backend calls, for the TPM cap.
        backend_id: Backend selector passed to `build_backend`.

    Returns:
        Every persisted record, in completion order.

    Raises:
        AuthError: Propagated from the first call the API rejects.
    """
    backends = build_paced_backends(
        backend_id, backend_config, model, jobs, Pacer(min_interval_sec)
    )
    model_dir = out_dir / model
    model_dir.mkdir(parents=True, exist_ok=True)
    calls_path = model_dir / "calls.jsonl"
    calls_path.write_text("", encoding="utf-8")
    lock = threading.Lock()
    records: list[dict[str, object]] = []

    def execute(job: Job) -> dict[str, object]:
        context = contexts[job.cell.key]
        config = reasoner_config.model_copy(update={"temperature": job.temperature})
        result, retries = run_sample(
            Reasoner(backends[job.seed], config), context.request, max_retries
        )
        record = build_call_record(model, job, context, result, retries)
        label = f"T={job.temperature}" if job.seed is None else f"seed={job.seed}"
        with lock:
            with open(calls_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            records.append(record)
            print(
                f"  [{len(records):>3}/{len(jobs)}] {job.cell.key} {label} "
                f"-> {(record['decision'] or {}).get('yield_robot')} "
                f"({(record['decision'] or {}).get('strategy')})",
                flush=True,
            )
        return record

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for future in [executor.submit(execute, job) for job in jobs]:
            future.result()
    return records


def _mode(values: Sequence[str]) -> tuple[str | None, float | None]:
    """Return the most common value and its share, or `(None, None)` when empty."""
    if not values:
        return None, None
    value, count = Counter(values).most_common(1)[0]
    return value, round(count / len(values), 3)


def summary_temperature(record: dict[str, object]) -> float | str:
    """Return the value a record contributes to the summary's temperature column.

    Args:
        record: One persisted call record.

    Returns:
        The record's `temperature` for a temperature-swept call, or `"seeded"`
        when the call's within-cell variation came from a `seed` instead.
    """
    if record.get("seed") is None:
        return record["temperature"]
    return _SEEDED_TEMPERATURE


def summarize_cells(records: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Aggregate raw call records into one row per model/cell/temperature.

    A seeded record pools with its cell's other seeds under the literal
    `"seeded"` in the temperature column, because its seed is a reproducibility
    handle and not a sampling setting the cells could be compared across.

    Args:
        records: Persisted call records.

    Returns:
        Summary rows sorted by model, variant, order, channel and temperature.
    """
    groups: dict[tuple, list[dict[str, object]]] = {}
    for record in records:
        key = (
            record["model"],
            record["variant"],
            record["presentation_order"],
            record["obstacle_channel"],
            summary_temperature(record),
        )
        groups.setdefault(key, []).append(record)

    rows: list[dict[str, object]] = []
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3], str(k[4]))):
        group = groups[key]
        model, variant, order, channel, temperature = key
        parsed = [r for r in group if r["decision"] is not None]
        yields = [r for r in parsed if (r["decision"] or {}).get("yield_robot")]
        chosen = [str((r["decision"] or {})["yield_robot"]) for r in yields]
        first_listed = group[0]["first_listed_robot"]
        correct = group[0]["correct_yielder"]
        not_yield = [r for r in parsed if (r["decision"] or {})["strategy"] != "yield"]
        rows.append(
            {
                "model": model,
                "variant": variant,
                "presentation_order": order,
                "obstacle_channel": channel,
                "temperature": temperature,
                "n": len(group),
                "n_parsed": len(parsed),
                "n_with_yield_robot": len(yields),
                "parse_failures": len(group) - len(parsed),
                "api_errors": sum(1 for r in group if _is_api_error(r)),
                "first_listed_robot": first_listed,
                "correct_yielder": correct,
                "modal_yield_robot": _mode(chosen)[0],
                "p_modal_yield_robot": _mode(chosen)[1],
                "p_yield_first_listed": _ratio(chosen, first_listed),
                "p_yield_robot_1": _ratio(chosen, "robot_1"),
                "p_yield_correct_yielder": _ratio(chosen, correct),
                "p_strategy_not_yield": (
                    round(len(not_yield) / len(parsed), 3) if parsed else None
                ),
                "median_latency_ms": _median_latency(group),
                "prompt_sha256": group[0]["prompt_sha256"],
            }
        )
    return rows


def _is_api_error(record: dict[str, object]) -> bool:
    # Only a call that never produced a decision counts: `Reasoner` keeps the
    # last error on the diagnostics even when a retry then succeeded.
    return record["decision"] is None and record["error_type"] in {
        "ConnectionError",
        "BackendTimeoutError",
    }


def _ratio(chosen: Sequence[str], target: str) -> float | None:
    if not chosen:
        return None
    return round(sum(1 for c in chosen if c == target) / len(chosen), 3)


def _median_latency(group: Sequence[dict[str, object]]) -> int | None:
    values = [r["latency_ms"] for r in group if isinstance(r["latency_ms"], int)]
    return int(statistics.median(values)) if values else None


def read_persisted_calls(out_dir: Path) -> list[dict[str, object]]:
    """Read every `<model>/calls.jsonl` under a results directory.

    Args:
        out_dir: Results root written by an earlier run.

    Returns:
        Every persisted call record.

    Raises:
        FileNotFoundError: If no `calls.jsonl` exists under `out_dir`.
    """
    paths = sorted(out_dir.glob("*/calls.jsonl"))
    if not paths:
        raise FileNotFoundError(f"no calls.jsonl under {out_dir}")
    records: list[dict[str, object]] = []
    for path in paths:
        records.extend(
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        )
    return records


def write_summary_csv(rows: Sequence[dict[str, object]], path: Path) -> None:
    """Write the per-cell summary rows as CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


MIN_MODAL_SHARE = 0.7


def asymmetric_rows(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Keep only the cells that discriminate between the hypotheses."""
    return [r for r in rows if r["variant"] != "wopen_eopen"]


def weakest_modal_share(rows: Sequence[dict[str, object]]) -> float | None:
    """Return the smallest modal share across the discriminating cells."""
    shares = [r["p_modal_yield_robot"] for r in asymmetric_rows(rows) if r["p_modal_yield_robot"]]
    return min(shares) if shares else None


def classify_hypothesis(
    rows: Sequence[dict[str, object]], min_modal_share: float = MIN_MODAL_SHARE
) -> Hypothesis:
    """Match the two asymmetric variants' modal yielders against the three signatures.

    The four asymmetric cells (variant x order) jointly separate the hypotheses:
    H_slot follows the first-listed slot, H_id always names `robot_1`, and H_geom
    follows the scenario oracle's `correct_yielder`. A cell whose modal answer wins
    by less than `min_modal_share` is a near-coin-flip whose label is decided by one
    sample, so the verdict degrades to `"mixed"` rather than inheriting that noise.

    Args:
        rows: Summary rows for one model, temperature and obstacle channel.
        min_modal_share: Share the weakest discriminating cell must reach.

    Returns:
        The matching signature, `"mixed"` when no signature fits every cell or a
        cell is too close to call, or `"insufficient"` when cells are missing.
    """
    asymmetric = asymmetric_rows(rows)
    if len(asymmetric) < 4 or any(r["modal_yield_robot"] is None for r in asymmetric):
        return "insufficient"
    weakest = weakest_modal_share(rows)
    if weakest is None or weakest < min_modal_share:
        return "mixed"
    if all(r["modal_yield_robot"] == r["first_listed_robot"] for r in asymmetric):
        return "H_slot"
    if all(r["modal_yield_robot"] == "robot_1" for r in asymmetric):
        return "H_id"
    if all(r["modal_yield_robot"] == r["correct_yielder"] for r in asymmetric):
        return "H_geom"
    return "mixed"


def print_report(rows: Sequence[dict[str, object]]) -> None:
    """Print the per-cell table and the hypothesis verdict per model and temperature."""
    header = (
        f"{'model':<12} {'variant':<12} {'order':<8} {'obs':<4} {'T':<4} "
        f"{'n':>3} {'fail':>4} {'modal':<9} {'P(1st)':>7} {'P(r1)':>6} "
        f"{'P(ok)':>6} {'P(!yld)':>7}"
    )
    print("\n" + header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['model']:<12} {row['variant']:<12} {row['presentation_order']:<8} "
            f"{row['obstacle_channel']:<4} {row['temperature']:<4} {row['n']:>3} "
            f"{row['parse_failures']:>4} {str(row['modal_yield_robot']):<9} "
            f"{_fmt(row['p_yield_first_listed']):>7} {_fmt(row['p_yield_robot_1']):>6} "
            f"{_fmt(row['p_yield_correct_yielder']):>6} {_fmt(row['p_strategy_not_yield']):>7}"
        )

    print("\nHypothesis signatures (asymmetric cells only):")
    # str() on every component: the temperature column holds floats for a
    # temperature-swept model and "seeded" for a seeded one, which do not compare.
    keys = sorted(
        {(r["model"], r["temperature"], r["obstacle_channel"]) for r in rows},
        key=lambda k: (str(k[0]), str(k[1]), str(k[2])),
    )
    for model, temperature, channel in keys:
        subset = [
            r
            for r in rows
            if r["model"] == model
            and r["temperature"] == temperature
            and r["obstacle_channel"] == channel
        ]
        print(
            f"  {model:<12} T={temperature:<4} obstacles={channel:<4} "
            f"-> {classify_hypothesis(subset):<12} "
            f"(weakest discriminating cell P(modal)={_fmt(weakest_modal_share(subset))})"
        )


def _fmt(value: object) -> str:
    return "-" if value is None else f"{float(value):.2f}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the probe."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--backend",
        choices=("openai", "gemini"),
        default="openai",
        help="which shipped backend to probe; gemini sweeps seeds instead of temperature",
    )
    parser.add_argument(
        "--models",
        default=None,
        help="comma-separated model IDs; default is config/models.yaml vlm.<backend>.model_id. "
        "A secondary model runs only if the primary finished with zero API errors.",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=None,
        help=f"gemini only: samples per cell, one per seed 0..N-1 (default {_DEFAULT_SEEDS})",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--prompt-dir",
        type=Path,
        default=None,
        help="where rendered prompts are written; default <out-dir>/prompts",
    )
    parser.add_argument("--family-dir", type=Path, default=FAMILY_DIR)
    parser.add_argument("--models-yaml", type=Path, default=MODELS_YAML)
    parser.add_argument("--n-greedy", type=int, default=5, help="samples at temperature 0.0")
    parser.add_argument("--n-sampled", type=int, default=10, help="samples at --temperature")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument(
        "--min-interval-sec",
        type=float,
        default=4.0,
        help="minimum spacing between backend calls; 4.0 keeps gpt-4o under a 30k TPM cap",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="render images and prompts, print the plan, make no API calls",
    )
    parser.add_argument(
        "--from-calls",
        action="store_true",
        help="rebuild summary.csv and the report from the persisted calls.jsonl files",
    )
    args = parser.parse_args(argv)
    if args.backend != "gemini" and args.seeds is not None:
        parser.error("--seeds applies only to --backend gemini")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Render the cells, run the probe, and report per-cell results.

    Returns:
        0 on success, 2 when a run was aborted by an authentication failure.
    """
    args = parse_args(argv)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir = args.prompt_dir if args.prompt_dir is not None else out_dir / "prompts"
    scenarios = load_family_scenarios(args.family_dir)
    contexts = prepare_cells(scenarios, out_dir, prompt_dir)
    _, reasoner_config, backend_config = load_backend_settings(args.models_yaml, args.backend)
    if args.backend == "gemini":
        n_seeds = args.seeds if args.seeds is not None else _DEFAULT_SEEDS
        jobs = plan_seeded_jobs(contexts.values(), n_seeds, reasoner_config.temperature)
    else:
        jobs = plan_jobs(contexts.values(), args.n_greedy, args.n_sampled, args.temperature)
    print(f"{len(contexts)} cells, {len(jobs)} calls per model -> {out_dir}")

    if args.from_calls:
        records = read_persisted_calls(out_dir)
        rows = summarize_cells(records)
        write_summary_csv(rows, out_dir / "summary.csv")
        print_report(rows)
        return 0

    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models
        else [backend_config.model_id]
    )
    if args.dry_run:
        for key in sorted(contexts):
            print(f"  {key}  sha={contexts[key].prompt_sha256[:12]}  "
                  f"first={contexts[key].first_listed_robot}  "
                  f"correct={contexts[key].correct_yielder}")
        print(f"dry run: prompts under {prompt_dir}, images under {out_dir / 'images'}")
        return 0

    all_records: list[dict[str, object]] = []
    for index, model in enumerate(models):
        print(f"\n=== {model} ===")
        try:
            records = run_model(
                model,
                contexts,
                jobs,
                reasoner_config,
                backend_config,
                out_dir,
                args.workers,
                args.max_retries,
                args.min_interval_sec,
                backend_id=args.backend,
            )
        except AuthError as exc:
            print(f"ABORT: authentication rejected ({exc}); no further calls made")
            return 2
        all_records.extend(records)
        errors = sum(1 for r in records if _is_api_error(r))
        if errors and index + 1 < len(models):
            print(f"{model} finished with {errors} API errors; skipping the remaining models")
            break

    rows = summarize_cells(all_records)
    write_summary_csv(rows, out_dir / "summary.csv")
    print_report(rows)
    print(f"\nsummary -> {out_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
