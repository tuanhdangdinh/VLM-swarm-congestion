"""Head-on swapped-ID replay: does a model pick the yielder from the scene or the label?

Pre-registered in docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md.
Twelve genuine-standoff artifacts of the September replays are re-sent through the
production `build_reasoner_request` / `Reasoner` path under three arms:

* ``A_real`` - original IDs, the annotated frame sent live.
* ``A_grey`` - original IDs, a neutral grey image of the frame's size.
* ``B_grey`` - `robot_1` and `robot_2` exchanged in the scene state, same grey image.

Each arm runs under both presentation orders with two replicates. Every row is
scored on the PHYSICAL robot (the one that spawned west or east), because the
correct label flips under the swap.

Reuses `scripts/replay_live_decisions.py` for loading, the SHA-256 integrity check
and request reconstruction; that module is not modified.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (REPO_ROOT, REPO_ROOT / "ros2_ws/src/swarm_orchestrator", REPO_ROOT / "scripts"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from reasoning.vlm.backend_base import VLMBackend  # noqa: E402
from reasoning.vlm.backend_factory import (  # noqa: E402
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.errors import BackendHTTPError, BackendTimeoutError  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    RobotPresentationOrder,
)
from reasoning.vlm.output_parser import parse_decision_text  # noqa: E402
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402
from scripts.replay_live_decisions import (  # noqa: E402
    RUN_SETS,
    Artifact,
    check_integrity,
    is_refusal,
    load_artifacts,
    make_grey_image,
    reconstruct_request,
    sha256_text,
)

OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-head-on-swapped-id-replay"
MODELS_YAML = REPO_ROOT / "config/models.yaml"

# The 12 standoff stimuli of the September replays (re-score report, final section).
STIMULUS_PREFIXES: tuple[str, ...] = (
    "53264de9",
    "5e7b5a59",
    "2c3fbfa5",
    "61119197",
    "d053d0dc",
    "3120c65f",
    "810c9104",
    "42fb0cb8",
    "d4b96fbd",
    "189ae2a6",
    "e4b1bd03",
    "618a9f29",
)
PILOT_PREFIXES: tuple[str, ...] = ("53264de9", "61119197")

ArmName = Literal["A_real", "A_grey", "B_grey"]
ARMS: tuple[ArmName, ...] = ("A_real", "A_grey", "B_grey")
ORDERS: tuple[RobotPresentationOrder, ...] = ("id_asc", "id_desc")
REPLICATES: tuple[int, ...] = (1, 2)
LABEL_SWAP: dict[str, str] = {"robot_1": "robot_2", "robot_2": "robot_1"}

# Execution order is the pre-registered model priority.
MODEL_BACKENDS: tuple[str, ...] = (
    "gemini",
    "openai",
    "gemini_flash",
    "openai_gpt56sol",
    "anthropic",
)
# Amendment 2 (2026-11-14): one model per provider.
FINAL_MODELS: tuple[str, ...] = ("gemini", "openai", "anthropic")
PROVIDER_OF: dict[str, str] = {
    "gemini": "gemini",
    "gemini_flash": "gemini",
    "openai": "openai",
    "openai_gpt56sol": "openai",
    "anthropic": "anthropic",
}

# USD per token (input, output); thought tokens are charged as output.
RATES_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini": (1.00, 5.00),
    "openai": (2.50, 10.00),
    "gemini_flash": (0.75, 3.75),
    "openai_gpt56sol": (4.00, 20.00),
    "anthropic": (2.00, 10.00),
}
DEFAULT_PROMPT_TOKENS_BOUND = 3000
TOTAL_CAP_USD = 10.00
MODEL_CAP_USD = 3.00
MAX_TRANSIENT_PER_RUN = 2
PILOT_STOP_FAILURES = 3

# A credit or spend-cap condition no retry clears (OpenAI, Gemini, Anthropic wording).
QUOTA_RE = re.compile(
    r"insufficient_quota|credit|billing|spend(ing)?[ _-]?cap|quota|exceeded your current",
    re.I,
)


class ProviderStop(BackendHTTPError):
    """Raised by the proxy once a provider must not be called again.

    A non-retryable `BackendHTTPError`, so the production retry policy ends the
    run at once instead of spending its remaining attempts.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=499)


def swap_scene_labels(
    scene: dict[str, Any], mapping: dict[str, str] = LABEL_SWAP
) -> dict[str, Any]:
    """Return a copy of a scene snapshot with the robot labels exchanged.

    Only `robots[*].robot_id` changes; every physical field stays with its robot.

    Args:
        scene: A stored `SceneSnapshot` mapping.
        mapping: Old label to new label.

    Returns:
        The relabelled scene.

    Raises:
        ValueError: If a robot carries a label the mapping does not cover.
    """
    swapped = json.loads(json.dumps(scene))
    for robot in swapped["robots"]:
        if robot["robot_id"] not in mapping:
            raise ValueError(f"no swap for robot_id {robot['robot_id']!r}")
        robot["robot_id"] = mapping[robot["robot_id"]]
    return swapped


def swapped_artifact(artifact: Artifact) -> Artifact:
    """Return the artifact with `robot_1` and `robot_2` exchanged in its scene.

    Args:
        artifact: An original-ID artifact with no failure context or plan state.

    Returns:
        The relabelled artifact.

    Raises:
        ValueError: If the artifact carries a context block that names robots,
            which this swap does not cover.
    """
    if artifact.failure_context or artifact.last_failed_context or artifact.plan_state:
        raise ValueError(f"{artifact.request_id}: context blocks are not swapped")
    if artifact.prompt_conditions and artifact.prompt_conditions.get("candidate_options"):
        raise ValueError(f"{artifact.request_id}: candidate options are not swapped")
    return dataclasses.replace(artifact, scene=swap_scene_labels(artifact.scene))


def label_to_physical(label: str | None, arm: ArmName) -> str | None:
    """Map a robot label to the physical robot it denotes in one arm.

    Args:
        label: `robot_1`, `robot_2`, or None.
        arm: The arm the label was rendered under.

    Returns:
        "west" (spawned west) or "east", or None for no or unknown label.
    """
    if label not in ("robot_1", "robot_2"):
        return None
    original = LABEL_SWAP[label] if arm == "B_grey" else label
    return "west" if original == "robot_1" else "east"


def correct_physical(obstacle_side: str | None) -> str | None:
    """Return the physical robot with free retreat room: the one away from the blocker."""
    if obstacle_side is None:
        return None
    return "east" if obstacle_side == "west" else "west"


def first_listed_physical(order: RobotPresentationOrder, arm: ArmName) -> str:
    """Return the physical robot listed first under one order and arm."""
    first_label = "robot_1" if order == "id_asc" else "robot_2"
    physical = label_to_physical(first_label, arm)
    assert physical is not None
    return physical


@dataclass(frozen=True)
class Cell:
    """One pre-registered run: a model, arm, stimulus, order and replicate."""

    backend_id: str
    arm: ArmName
    artifact: Artifact
    order: RobotPresentationOrder
    replicate: int
    image_path: Path
    pilot: bool = False

    def key(self) -> str:
        """Stable identity used to resume an interrupted run."""
        return "|".join(
            (self.backend_id, self.arm, self.artifact.request_id, self.order, f"r{self.replicate}")
        )

    def request_artifact(self) -> Artifact:
        """The artifact as rendered in this arm (relabelled in Arm B)."""
        return swapped_artifact(self.artifact) if self.arm == "B_grey" else self.artifact


def build_cells(backend_id: str, stimuli: list[Artifact], grey_image: Path) -> list[Cell]:
    """Build one model's cells in the pre-registered execution order.

    Pilot cells first (replicate 1 of the two pilot scenes, both orders, every
    arm), then replicate 1 and replicate 2 of the rest, scene by scene, order,
    then arm.

    Args:
        backend_id: The model's `config/models.yaml` section.
        stimuli: The 12 standoff artifacts.
        grey_image: The neutral image for the grey arms.

    Returns:
        144 cells.
    """

    def make(
        arm: ArmName, artifact: Artifact, order: RobotPresentationOrder, rep: int, pilot: bool
    ) -> Cell:
        image = artifact.image_path if arm == "A_real" else grey_image
        return Cell(backend_id, arm, artifact, order, rep, image, pilot)

    pilots = [a for p in PILOT_PREFIXES for a in stimuli if a.request_id.startswith(p)]
    cells = [make(arm, a, order, 1, True) for arm in ARMS for a in pilots for order in ORDERS]
    pilot_keys = {c.key() for c in cells}
    for rep in REPLICATES:
        for artifact in stimuli:
            for order in ORDERS:
                for arm in ARMS:
                    cell = make(arm, artifact, order, rep, False)
                    if cell.key() not in pilot_keys:
                        cells.append(cell)
    return cells


def attempt_cost_usd(backend_id: str, usage: dict[str, int] | None) -> float | None:
    """Price one attempt from its recorded usage, or None when no usage exists."""
    if not usage:
        return None
    rate_in, rate_out = (r / 1_000_000 for r in RATES_PER_MTOK[backend_id])
    prompt = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    prompt += usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
    output = usage.get("completion_tokens", usage.get("output_tokens", 0))
    # Gemini reports thought tokens apart from output; both are billed as output.
    output += usage.get("thought_tokens", 0)
    return prompt * rate_in + output * rate_out


def worst_attempt_usd(backend_id: str, config: ReasonerConfig, prompt_bound: int) -> float:
    """Upper bound on one attempt: the prompt bound in, the full output cap out."""
    rate_in, rate_out = (r / 1_000_000 for r in RATES_PER_MTOK[backend_id])
    return prompt_bound * rate_in + config.max_tokens * rate_out


@dataclass
class ProxyAttempt:
    """One network call made by the proxy, billed or not."""

    attempt: int
    image_name: str
    user_sha256: str
    text: str | None
    provider_refusal: bool
    text_refusal: bool
    refusal_category: str | None
    finish_reason: str | None
    served_model: str | None
    token_usage: dict[str, int] | None
    latency_ms: int | None
    error: str | None
    status_code: int | None
    transient_retry: bool


class LedgerProxy:
    """A `VLMBackend` proxy that records every call, paces, and enforces stop rules."""

    def __init__(self, inner: VLMBackend, pace_sec: float) -> None:
        self._inner = inner
        self._pace_sec = pace_sec
        self._last_call_ended: float | None = None
        self.calls: list[ProxyAttempt] = []
        self.transient_failures = 0
        self.attempt_index = 0
        self.provider_stop: str | None = None

    def reset(self) -> None:
        """Clear per-run state before the next `Reasoner.run`."""
        self.calls = []
        self.transient_failures = 0
        self.attempt_index = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Forward one attempt to the real backend unless a stop rule forbids it.

        Args:
            payload: Rendered prompt payload.
            config: Runtime decoding settings.

        Returns:
            The wrapped backend's response.

        Raises:
            ProviderStop: The provider is stopped, or this run's transient budget
                is spent; raised without a network call.
            Exception: The wrapped backend's own error, after recording it.
        """
        self.attempt_index += 1
        if self.provider_stop:
            raise ProviderStop(f"provider stopped: {self.provider_stop}")
        if self.transient_failures > MAX_TRANSIENT_PER_RUN:
            raise ProviderStop("transient budget for this run spent")
        if self._last_call_ended is not None:
            remaining = self._pace_sec - (time.monotonic() - self._last_call_ended)
            if remaining > 0:
                time.sleep(remaining)
        image_name = Path(payload.image_path).name
        user_sha = sha256_text(payload.user_prompt)
        try:
            response = self._inner.analyze(payload, config)
        except Exception as exc:
            self._last_call_ended = time.monotonic()
            status = exc.status_code if isinstance(exc, BackendHTTPError) else None
            message = str(exc)[:400]
            transient = isinstance(exc, (BackendTimeoutError, ConnectionError)) and (
                status is None or status == 429 or status >= 500
            )
            if status in (401, 403):
                self.provider_stop = f"HTTP {status} (auth)"
            elif status == 402 or (status == 429 and QUOTA_RE.search(message)):
                self.provider_stop = f"HTTP {status} (quota/credit)"
            elif transient:
                self.transient_failures += 1
                if status == 429 and self.transient_failures > MAX_TRANSIENT_PER_RUN:
                    self.provider_stop = "HTTP 429 persisted past the transient budget"
            self.calls.append(
                ProxyAttempt(
                    attempt=self.attempt_index,
                    image_name=image_name,
                    user_sha256=user_sha,
                    text=None,
                    provider_refusal=False,
                    text_refusal=False,
                    refusal_category=None,
                    finish_reason=None,
                    served_model=None,
                    token_usage=None,
                    latency_ms=None,
                    error=f"{type(exc).__name__}: {message}",
                    status_code=status,
                    transient_retry=transient,
                )
            )
            raise
        self._last_call_ended = time.monotonic()
        self.calls.append(
            ProxyAttempt(
                attempt=self.attempt_index,
                image_name=image_name,
                user_sha256=user_sha,
                text=response.text,
                provider_refusal=bool(response.refusal),
                text_refusal=is_refusal(response.text),
                refusal_category=response.refusal_category,
                finish_reason=response.finish_reason,
                served_model=response.served_model,
                token_usage=response.token_usage,
                latency_ms=response.latency_ms,
                error=None,
                status_code=None,
                transient_retry=False,
            )
        )
        return response


def _named(decision: dict[str, Any] | None) -> str | None:
    label = (decision or {}).get("yield_robot")
    return label if label in ("robot_1", "robot_2") else None


def attempt1_decision(text: str | None) -> dict[str, Any] | None:
    """Parse attempt 1's text into a decision mapping, or None."""
    if not text:
        return None
    try:
        return parse_decision_text(text).model_dump(mode="json")
    except Exception:  # noqa: BLE001 - any parse failure means no attempt-1 decision
        return None


def outcome_of(
    decision: dict[str, Any] | None,
    refused: bool,
    error: str | None,
    correct: str | None,
    arm: ArmName,
) -> str:
    """Classify a final decision: correct, wrong, no_yielder, refusal, parse_failure, error."""
    if decision is None:
        if refused:
            return "refusal"
        return "error" if error else "parse_failure"
    chosen = label_to_physical(_named(decision), arm)
    if chosen is None:
        return "no_yielder"
    return "correct" if chosen == correct else "wrong"


def score_fields(cell: Cell, decision: dict[str, Any] | None) -> dict[str, Any]:
    """Physical-robot scoring fields for one row."""
    label = _named(decision)
    return {
        "chosen_label": label,
        "chosen_physical": label_to_physical(label, cell.arm),
        "first_listed_physical": first_listed_physical(cell.order, cell.arm),
        "correct_physical": correct_physical(cell.artifact.obstacle_side),
        "robot1_physical": label_to_physical("robot_1", cell.arm),
        "correct_label": next(
            lab
            for lab in ("robot_1", "robot_2")
            if label_to_physical(lab, cell.arm) == correct_physical(cell.artifact.obstacle_side)
        ),
    }


def git_commit() -> str:
    """Return the short HEAD commit of this checkout."""
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def run_cell(
    cell: Cell, proxy: LedgerProxy, config: ReasonerConfig, effective: dict[str, Any], commit: str
) -> dict[str, Any]:
    """Execute one cell through the production `Reasoner` and return its row."""
    request = reconstruct_request(cell.request_artifact(), cell.order, cell.image_path, True)
    user_prompt = build_prompt_payload(request).user_prompt
    payload_sha = sha256_text(user_prompt)
    proxy.reset()
    started = time.monotonic()
    error: str | None = None
    result = None
    try:
        result = Reasoner(proxy, config).run(request)
    except Exception as exc:  # noqa: BLE001 - recorded as data, never dropped
        error = f"{type(exc).__name__}: {str(exc)[:300]}"
    diag = result.diagnostics if result else None
    decision = result.decision.model_dump(mode="json") if result and result.decision else None
    attempts = [dataclasses.asdict(a) for a in proxy.calls]
    first = proxy.calls[0] if proxy.calls else None
    terminal_refusal = decision is None and bool(diag and diag.refusal_attempts)
    run_error = error or (diag.error_message if diag and decision is None else None)
    correct = correct_physical(cell.artifact.obstacle_side)
    a1 = attempt1_decision(first.text) if first and not first.provider_refusal else None
    a1_refused = bool(first and (first.provider_refusal or first.text_refusal))
    row = {
        "key": cell.key(),
        "commit": commit,
        "backend_id": cell.backend_id,
        "model_id": effective.get("model_id"),
        "served_model": diag.served_model if diag else None,
        "effective_config": effective,
        "unsupported_sampling": diag.unsupported_sampling if diag else None,
        "arm": cell.arm,
        "pilot": cell.pilot,
        "request_id": cell.artifact.request_id,
        "scene": cell.artifact.request_id[:8],
        "run": cell.artifact.run,
        "side": cell.artifact.obstacle_side,
        "order": cell.order,
        "replicate": cell.replicate,
        "image_condition": "annotated_frame" if cell.arm == "A_real" else "grey",
        "image_name": cell.image_path.name,
        "ids": "swapped" if cell.arm == "B_grey" else "original",
        "prompt_user_sha256": payload_sha,
        "prompt_matches_live": payload_sha == cell.artifact.stored_user_sha256,
        "image_fallback_used": bool(diag and diag.image_fallback_used),
        "image_fallback_attempt": diag.image_fallback_attempt if diag else None,
        "n_attempts": diag.attempts if diag else len(attempts),
        "n_network_calls": len(attempts),
        "refusal_attempts": diag.refusal_attempts if diag else None,
        "refusal_category": diag.refusal_category if diag else None,
        "terminal_refusal": terminal_refusal,
        "parse_status": diag.parse_status if diag else None,
        "attempts": attempts,
        "decision": decision,
        "strategy": (decision or {}).get("strategy"),
        "yield_robot": _named(decision),
        "outcome": outcome_of(decision, terminal_refusal, run_error, correct, cell.arm),
        "attempt1_refused": a1_refused,
        "attempt1_decision": a1,
        "attempt1_outcome": outcome_of(
            a1, a1_refused, first.error if first else "no call", correct, cell.arm
        ),
        "attempt1_chosen_physical": label_to_physical(_named(a1), cell.arm),
        **score_fields(cell, decision),
        "wall_ms": int((time.monotonic() - started) * 1000),
        "error": run_error,
        "provider_stop": proxy.provider_stop,
    }
    return row


def row_cost(row: dict[str, Any], config: ReasonerConfig, prompt_bound: int) -> float:
    """Charge a row: priced usage per network call, worst case where no usage exists."""
    total = 0.0
    for attempt in row["attempts"]:
        cost = attempt_cost_usd(row["backend_id"], attempt["token_usage"])
        if cost is None:
            # An HTTP status error is not billed by any provider here; a timeout
            # or dropped connection might be, so it is charged in full.
            billed = attempt["status_code"] is None
            cost = worst_attempt_usd(row["backend_id"], config, prompt_bound) if billed else 0.0
        total += cost
    return total


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, tolerating a missing file."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def ledger_totals(ledger: list[dict[str, Any]]) -> tuple[float, dict[str, float]]:
    """Return the total spend and spend per backend from ledger rows."""
    per: dict[str, float] = {}
    for entry in ledger:
        per[entry["backend_id"]] = per.get(entry["backend_id"], 0.0) + entry["usd"]
    return sum(per.values()), per


def load_model(backend_id: str) -> tuple[ReasonerConfig, Any, dict[str, Any]]:
    """Return a model's shipped reasoner config, backend config and effective block."""
    raw_vlm = yaml.safe_load(MODELS_YAML.read_text())["vlm"]
    reasoner_config = resolve_reasoner_config(raw_vlm, backend_id)
    backend_config = load_backend_config(raw_vlm, backend_id)
    effective = describe_effective_sampling(reasoner_config, backend_config).model_dump(mode="json")
    effective["allow_reask"] = reasoner_config.allow_reask
    effective["timeout_sec"] = reasoner_config.timeout_sec
    return reasoner_config, backend_config, effective


def make_backend(backend_id: str, backend_config: Any) -> VLMBackend:
    """Construct the real backend for one configured arm."""
    raw_vlm = yaml.safe_load(MODELS_YAML.read_text())["vlm"]
    return build_backend(backend_adapter(raw_vlm, backend_id), backend_config)


def probe_provider(backend_id: str, out_dir: Path) -> dict[str, Any]:
    """Make one minimal paid call to a provider and record the outcome.

    Args:
        backend_id: The arm whose provider is probed.
        out_dir: Experiment directory receiving `probes.jsonl` and the probe image.

    Returns:
        The probe row, with `ok` False on any HTTP error.
    """
    config, backend_config, effective = load_model(backend_id)
    image = make_grey_image(out_dir / "probe_64.png", (64, 64))
    payload = PromptPayload(
        system_prompt="You are a test endpoint.",
        user_prompt='Reply with exactly this JSON and nothing else: {"ok": true}',
        image_path=str(image),
        known_robot_ids=[],
    )
    probe_config = config.model_copy(update={"max_tokens": min(config.max_tokens, 2048)})
    row: dict[str, Any] = {
        "backend_id": backend_id,
        "model_id": effective.get("model_id"),
        "stamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    try:
        response = make_backend(backend_id, backend_config).analyze(payload, probe_config)
    except Exception as exc:  # noqa: BLE001 - the probe's job is to record the failure
        status = exc.status_code if isinstance(exc, BackendHTTPError) else None
        row.update(
            ok=False, status_code=status, error=f"{type(exc).__name__}: {str(exc)[:300]}", usd=0.0
        )
    else:
        row.update(
            ok=True,
            status_code=200,
            text=(response.text or "")[:200],
            token_usage=response.token_usage,
            served_model=response.served_model,
            usd=attempt_cost_usd(backend_id, response.token_usage) or 0.0,
        )
    append_jsonl(out_dir / "probes.jsonl", row)
    return row


def load_stimuli(runs_dir: Path) -> list[Artifact]:
    """Load the 12 standoff artifacts, SHA-verified, in the pre-registered order.

    Raises:
        RuntimeError: If any stimulus is missing, fails the prompt SHA check, or
            lacks its frame.
    """
    integrity = check_integrity(load_artifacts(RUN_SETS["all"], runs_dir))
    stimuli: list[Artifact] = []
    for prefix in STIMULUS_PREFIXES:
        found = [a for a in integrity.matched if a.request_id.startswith(prefix)]
        if len(found) != 1:
            raise RuntimeError(f"stimulus {prefix}: {len(found)} SHA-verified matches")
        stimuli.append(found[0])
    return stimuli


def grey_image_for(stimuli: list[Artifact], out_dir: Path) -> Path:
    """Write the single grey image used by both grey arms (all frames share one size)."""
    from PIL import Image

    sizes = set()
    for artifact in stimuli:
        with Image.open(artifact.image_path) as image:
            sizes.add(image.size)
    if len(sizes) != 1:
        raise RuntimeError(f"frames differ in size: {sorted(sizes)}")
    ((width, height),) = sizes
    return make_grey_image(out_dir / f"grey_{width}x{height}.png", (width, height))


def pilot_failed(rows: list[dict[str, Any]], backend_id: str, arm: str) -> bool | None:
    """Apply the pilot rule: None until all 4 pilot runs exist, then True to stop the arm."""
    pilots = [r for r in rows if r["backend_id"] == backend_id and r["arm"] == arm and r["pilot"]]
    if len(pilots) < len(PILOT_PREFIXES) * len(ORDERS):
        return None
    # Amendment 2: Sonnet's real-frame arm stops on any fallback, because a
    # fallback decision is a grey-image decision, not a real-frame one.
    if (
        backend_id == "anthropic"
        and arm == "A_real"
        and any(r["image_fallback_used"] for r in pilots)
    ):
        return True
    bad = sum(1 for r in pilots if r["decision"] is None or r["image_fallback_used"])
    return bad >= PILOT_STOP_FAILURES


def execute_model(
    backend_id: str,
    stimuli: list[Artifact],
    grey: Path,
    out_dir: Path,
    pace_sec: float,
    commit: str,
) -> str:
    """Run one model's cells under every stop rule; return why it ended."""
    calls_path, ledger_path = out_dir / "calls.jsonl", out_dir / "ledger.jsonl"
    config, backend_config, effective = load_model(backend_id)
    proxy = LedgerProxy(make_backend(backend_id, backend_config), pace_sec)
    rows = load_jsonl(calls_path)
    done = {r["key"] for r in rows}
    prompt_bound = DEFAULT_PROMPT_TOKENS_BOUND
    for cell in build_cells(backend_id, stimuli, grey):
        if cell.key() in done:
            continue
        if not cell.pilot and pilot_failed(rows, backend_id, cell.arm):
            continue
        ledger = load_jsonl(ledger_path)
        total, per = ledger_totals(ledger)
        worst = config.max_attempts * worst_attempt_usd(backend_id, config, prompt_bound)
        if per.get(backend_id, 0.0) + worst > MODEL_CAP_USD:
            return f"model cap: spent {per.get(backend_id, 0.0):.4f}, next worst {worst:.4f}"
        if total + worst > TOTAL_CAP_USD:
            return f"TOTAL cap: spent {total:.4f}, next worst {worst:.4f}"
        row = run_cell(cell, proxy, config, effective, commit)
        for attempt in row["attempts"]:
            usage = attempt["token_usage"] or {}
            seen = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            prompt_bound = max(prompt_bound, int(seen * 1.2))
        usd = row_cost(row, config, prompt_bound)
        row["usd"] = usd
        append_jsonl(calls_path, row)
        total += usd
        append_jsonl(
            ledger_path,
            {
                "key": row["key"],
                "backend_id": backend_id,
                "network_calls": row["n_network_calls"],
                "transient_retries": sum(1 for a in row["attempts"] if a["transient_retry"]),
                "usd": usd,
                "model_total": per.get(backend_id, 0.0) + usd,
                "grand_total": total,
            },
        )
        rows.append(row)
        print(
            f"{row['key']} outcome={row['outcome']} yield={row['yield_robot']} "
            f"att={row['n_attempts']} fb={row['image_fallback_used']} usd={usd:.4f} "
            f"total={total:.4f}",
            flush=True,
        )
        if proxy.provider_stop:
            return f"provider stop: {proxy.provider_stop}"
    return "complete"


def main() -> None:
    """Probe providers, then run the pre-registered cells model by model."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--runs-dir",
        type=Path,
        required=True,
        help="directory holding the 2026-09-25 pilot run folders",
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--models", nargs="*", default=list(FINAL_MODELS))
    parser.add_argument("--pace-sec", type=float, default=1.0)
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument(
        "--check-only", action="store_true", help="verify stimuli and print the plan; no network"
    )
    args = parser.parse_args()

    stimuli = load_stimuli(args.runs_dir)
    grey = grey_image_for(stimuli, args.out_dir)
    commit = git_commit()
    print(f"{len(stimuli)} stimuli SHA-verified; grey image {grey.name}; commit {commit}")
    for backend_id in args.models:
        print(f"{backend_id}: {len(build_cells(backend_id, stimuli, grey))} cells")
    if args.check_only:
        return

    probes = {r["backend_id"]: r for r in load_jsonl(args.out_dir / "probes.jsonl")}
    provider_ok: dict[str, bool] = {}
    for backend_id in args.models:
        provider = PROVIDER_OF[backend_id]
        if provider in provider_ok:
            continue
        probe_id = next(b for b in MODEL_BACKENDS if PROVIDER_OF[b] == provider)
        probe = probes.get(probe_id) or probe_provider(probe_id, args.out_dir)
        provider_ok[provider] = bool(probe["ok"])
        print(
            f"probe {provider} via {probe_id}: ok={probe['ok']} status={probe.get('status_code')}"
        )
    if args.probe_only:
        return

    for backend_id in args.models:
        if not provider_ok[PROVIDER_OF[backend_id]]:
            print(f"{backend_id}: skipped, provider probe failed")
            continue
        reason = execute_model(backend_id, stimuli, grey, args.out_dir, args.pace_sec, commit)
        print(f"{backend_id}: ended - {reason}", flush=True)
        if reason.startswith("TOTAL cap"):
            break
        if reason.startswith("provider stop"):
            provider_ok[PROVIDER_OF[backend_id]] = False


if __name__ == "__main__":
    main()
