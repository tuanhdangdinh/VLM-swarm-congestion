#!/usr/bin/env python3
"""Paid offline plan check for the VLM recede-order channel (2026-11-15).

Design: docs/superpowers/specs/2026-11-15-vlm-order-channel-plan-check.md.

For each recorded four-robot IB10 first-trigger `junction_clear` snapshot, the
request M5 sent is rebuilt through the production `build_reasoner_request` /
`build_prompt_payload` path and checked byte-for-byte against the stored prompt
(integrity gate). It is then re-rendered under two conditions:

* ``A``: the prompt v3.5 plan-grammar rules (`plan_grammar_rules=True`);
* ``B``: A plus the existing verifier-candidate-options block, built exactly as
  M5 builds it (`build_candidate_options`).

``run`` sends one condition to one configured backend arm through the shipped
`Reasoner` (its retry, re-ask and parse path), behind a guarding proxy that
keeps a running cost ledger, stops cleanly at the cap, and stops a provider on
401/402/403, a 429 or a refusal (Anthropic). Each call is appended to
``calls.jsonl`` (resumable; no images, no keys, no provider payloads).

``analyze`` replays every stored answer OFFLINE through the real M5/M3 path:
`InProcessPipeline._run_from_result` (parse output -> grounding ->
`verify_and_repair_plan` -> junction phases -> `model_when_verified`), once with
`plan_dispatch_order_source="chi"`, once with `"model_when_verified"`, and once
for the same decision with `proposed_plan=None` (the no-plan default). With
``--recorded`` it instead replays the recorded live answers, a fidelity check of
the offline path against what M5 recorded.

Usage (keys are read by the adapters from env vars; load them the repo's way):
    set -a; source .env; set +a
    python scripts/vlm_order_channel_plan_check.py stimuli --docs-root <dir>
    python scripts/vlm_order_channel_plan_check.py run --docs-root <dir> \\
        --backend gemini --conditions A,B --rep 0 --subcap 0.45
    python scripts/vlm_order_channel_plan_check.py analyze --docs-root <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in (
    REPO_ROOT,
    REPO_ROOT / "ros2_ws/src/swarm_orchestrator",
    REPO_ROOT / "ros2_ws/src/swarm_execution",
):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from swarm_orchestrator.models import (  # noqa: E402
    SceneSnapshot,
    load_config,
    registry_priorities,
)
from swarm_orchestrator.plan_tracker import PlanTracker  # noqa: E402
from swarm_orchestrator.reasoning_pipeline import (  # noqa: E402
    InProcessPipeline,
    build_candidate_options,
    build_reasoner_request,
    yield_refusal_fan_out,
)
from swarm_orchestrator.retreat_stage2 import snapshot_frame_from_request  # noqa: E402

from reasoning.rag.command_grounder import (  # noqa: E402
    _junction_recede_candidates,
    ground_reasoner_result,
    plan_recede_order,
    verify_and_repair_plan,
)
from reasoning.rag.maneuver_geometry import (  # noqa: E402
    GroundingParams,
    rank_recede_candidates,
    recede_cost,
)
from reasoning.vlm.backend_factory import (  # noqa: E402
    backend_adapter,
    build_backend,
    describe_effective_sampling,
    load_backend_config,
    resolve_reasoner_config,
)
from reasoning.vlm.errors import BackendHTTPError  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    BackendResponse,
    CongestionDecision,
    FailureContext,
    PlanStateContext,
    PromptPayload,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
)
from reasoning.vlm.prompt_builder import build_prompt_payload  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402

EXPERIMENT = "2026-11-15-vlm-order-channel-plan-check"
DEFAULT_OUT = REPO_ROOT / "data" / "experiments" / EXPERIMENT

# The 15 live ER-2 snapshots the 2026-11-15 plan-influence trace used (fidelity
# gate passed) and the 5 Arm C snapshots, as (class, bundle path relative to
# --docs-root, request_id prefix). `ceff5efa` is e09's THIRD trigger, not a
# first trigger; it carries a plan-state block and is flagged in the tables.
STIMULI: tuple[tuple[str, str, str], ...] = (
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e01_armA_a1", "0b9d2939"),
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e01_armA_a2", "d9374445"),
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e03_armA_a1", "6c5406d8"),
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e05_armA_a1", "a71c50a9"),
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e07_armA_a1", "d7da0457"),
    ("live_ib10L", "vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/runs/ib10L_e09_armA_a1", "ceff5efa"),
    ("live_ib10S", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e01_armA_a1", "bfaef39f"),
    ("live_ib10S", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e03_armA_a1", "18c2a25e"),
    ("live_ib10S", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e05_armA_a1", "580328a5"),
    ("live_ib10S", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e07_armA_a1", "1d8cbac7"),
    ("live_ib10S", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e09_armA_a1", "3f26b4c8"),
    ("live_oct", "vgu-vlm-swarm/data/logs/vm_runs/verbatim_pilot/vp08_er2_ib10_s42", "8fad1c84"),
    ("live_oct", "vgu-vlm-swarm/data/logs/vm_runs/verbatim_pilot/vp09_er2_ib10_s43", "339b0880"),
    ("live_oct", "vgu-vlm-swarm/data/logs/vm_runs/v2_demo/ep2_live_er2", "5dfbeb07"),
    ("live_oct", "vgu-vlm-swarm/data/logs/vm_runs/plan_grammar_cal/cal_ep1_rerun", "aec068b5"),
    ("ref_armC", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e02_armC_a2", "4edbbfa0"),
    ("ref_armC", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e04_armC_a1", "162362ef"),
    ("ref_armC", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e06_armC_a1", "83b5f75b"),
    ("ref_armC", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e08_armC_a1", "a59d90da"),
    ("ref_armC", "vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/runs/ib10S_e10_armC_a1", "5a46e51a"),
)

# USD per million tokens (input, output), and the source of each figure.
# Gemini: thought tokens bill as output. The ledger multiplies by
# LEDGER_MARGIN so the cap check is conservative.
PRICES: dict[str, tuple[float, float, str]] = {
    "gemini": (1.00, 5.00, "scripts/summarize_capability_probes_v2.py PRICES (ER-2 preview)"),
    "anthropic": (2.00, 10.00, "docs/reports/2026-10-06-roster-validation.md (Sonnet 5.5)"),
    "openai": (2.50, 10.00, "scripts/summarize_capability_probes_v2.py PRICES (gpt-4o)"),
}
LEDGER_MARGIN = 1.25
# Worst-case input tokens of one call (text ~2.0k + image ~1.6k, rounded up).
WORST_INPUT_TOKENS = 5000


def sha256_text(text: str) -> str:
    """Return the hex SHA-256 of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class Stimulus:
    """One recorded snapshot and everything needed to rebuild and ground its request."""

    cls: str
    bundle: Path
    rel: str
    request_id: str
    artifact: dict[str, Any]
    config: Any
    params: GroundingParams
    yfm: str
    frame: Path

    @property
    def label(self) -> str:
        """Short episode label (the bundle directory name)."""
        return self.bundle.name

    @property
    def first_trigger(self) -> bool:
        """False only for e09's third trigger, which carries a plan-state block."""
        return not self.artifact.get("plan_state")

    def base_request(self) -> ReasonerRequest:
        """Rebuild the request M5 sent, with the artifact's own prompt inputs."""
        art = self.artifact
        fc = art.get("failure_context")
        lfc = art.get("last_failed_context")
        ps = art.get("plan_state")
        order = art.get("robot_presentation_order") or "id_asc"
        if isinstance(order, list):
            order = tuple(order)
        return build_reasoner_request(
            self.request_id,
            SceneSnapshot(**art["scene"]),
            str(self.frame),
            failure_context=FailureContext(**fc) if fc else None,
            last_failed_context=FailureContext(**lfc) if lfc else None,
            include_pairwise_geometry=self.config.prompt_pairwise_geometry,
            static_obstacles=list(self.config.static_obstacles),
            include_static_obstacles=self.config.prompt_static_obstacles,
            robot_presentation_order=order,
            prompt_version=int(art.get("prompt_version") or 1),
            plan_state=PlanStateContext(**ps) if ps else None,
        )

    def request(self, condition: str) -> ReasonerRequest:
        """The request under condition A or B (both carry the v3.5 rules)."""
        base = self.base_request()
        update: dict[str, Any] = {"plan_grammar_rules": True}
        if condition == "B":
            update["candidate_options"] = build_candidate_options(
                SceneSnapshot(**self.artifact["scene"]),
                geometry=self.config.scenario_geometry,
                static_obstacles=self.config.static_obstacles,
                yield_feasibility_mode=self.yfm,
                grounding_params=self.params,
            )
        elif condition != "A":
            raise ValueError(f"unknown condition {condition!r}")
        return ReasonerRequest(**{**base.model_dump(), **update})


def load_stimuli(docs_root: Path) -> list[Stimulus]:
    """Load every stimulus; raise when a bundle, artifact or frame is missing."""
    out = []
    for cls, rel, prefix in STIMULI:
        bundle = docs_root / rel
        matches = sorted((bundle / "decisions").glob(f"{prefix}*.json"))
        if len(matches) != 1:
            raise FileNotFoundError(f"{rel}: expected one artifact {prefix}*, got {len(matches)}")
        art = json.loads(matches[0].read_text())
        config = load_config(yaml.safe_load((bundle / "orchestrator.overlaid.yaml").read_text()))
        params = GroundingParams(**art["grounding_params_source"]["params"])
        yfm = art.get("grounding_yield_feasibility") or config.grounding_yield_feasibility
        frame = bundle / "frames" / f"{art['request_id']}.png"
        if not frame.is_file():
            raise FileNotFoundError(frame)
        out.append(Stimulus(cls, bundle, rel, art["request_id"], art, config, params, yfm, frame))
    return out


def integrity(stimuli: list[Stimulus]) -> list[dict[str, Any]]:
    """Re-render each stored prompt and compare with the stored SHA-256."""
    rows = []
    for s in stimuli:
        stored = s.artifact["prompt"]
        rendered = build_prompt_payload(s.base_request()).user_prompt
        a = build_prompt_payload(s.request("A")).user_prompt
        b = build_prompt_payload(s.request("B")).user_prompt
        first_diff = None
        if rendered != stored["user_prompt"]:
            for i, (x, y) in enumerate(
                zip(stored["user_prompt"].splitlines(), rendered.splitlines(), strict=False)
            ):
                if x != y:
                    first_diff = {"line": i, "stored": x[:160], "rendered": y[:160]}
                    break
        rows.append(
            {
                "cls": s.cls,
                "episode": s.label,
                "request_id": s.request_id,
                "first_trigger": s.first_trigger,
                "frame": str(s.frame.relative_to(s.bundle)),
                "frame_sha256": sha256_file(s.frame),
                "stored_user_sha256": stored["user_sha256"],
                "rerendered_user_sha256": sha256_text(rendered),
                "matches_stored": sha256_text(rendered) == stored["user_sha256"],
                "len_delta_vs_stored": len(rendered) - len(stored["user_prompt"]),
                "first_diff": first_diff,
                "A_user_sha256": sha256_text(a),
                "B_user_sha256": sha256_text(b),
                "A_minus_base_chars": len(a) - len(rendered),
                "B_minus_A_chars": len(b) - len(a),
            }
        )
    return rows


class StopProvider(RuntimeError):
    """Raised (and recorded by the Reasoner as a failed attempt) to stop a provider."""


class Ledger:
    """Running cost ledger persisted beside calls.jsonl."""

    def __init__(self, path: Path, cap: float) -> None:
        self.path = path
        self.cap = cap
        self.data = json.loads(path.read_text()) if path.is_file() else {"spent_usd": 0.0, "by": {}}

    @property
    def spent(self) -> float:
        """Total conservative spend so far."""
        return float(self.data["spent_usd"])

    def spent_by(self, key: str) -> float:
        """Spend of one ledger key (a backend arm, or a probe)."""
        return float(self.data["by"].get(key, 0.0))

    def add(self, key: str, usd: float) -> None:
        """Add a charge and persist."""
        self.data["spent_usd"] = round(self.spent + usd, 6)
        self.data["by"][key] = round(self.spent_by(key) + usd, 6)
        self.path.write_text(json.dumps(self.data, indent=1, sort_keys=True) + "\n")


def usage_cost(adapter: str, usage: dict[str, int] | None) -> tuple[float, int, int]:
    """Conservative USD of one attempt from its token usage: (usd, in_tokens, out_tokens)."""
    if not usage:
        return 0.0, 0, 0
    price_in, price_out, _ = PRICES[adapter]
    if adapter == "anthropic":
        tin = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get(
            "cache_read_input_tokens", 0
        )
        tout = usage.get("output_tokens", 0)
    elif adapter == "gemini":
        tin = usage.get("prompt_tokens", 0)
        tout = usage.get("completion_tokens", 0) + usage.get("thought_tokens", 0)
    else:
        tin = usage.get("prompt_tokens", 0)
        tout = usage.get("completion_tokens", 0)
    usd = (tin * price_in + tout * price_out) / 1e6 * LEDGER_MARGIN
    return usd, tin, tout


class GuardedBackend:
    """VLMBackend proxy: cost reservation per attempt, provider stop rules, attempt log."""

    def __init__(
        self, inner: Any, adapter: str, key: str, ledger: Ledger, subcap: float, max_tokens: int
    ) -> None:
        self._inner = inner
        self._adapter = adapter
        self._key = key
        self._ledger = ledger
        self._subcap = subcap
        price_in, price_out, _ = PRICES[adapter]
        self._reserve = (
            (WORST_INPUT_TOKENS * price_in + max_tokens * price_out) / 1e6 * LEDGER_MARGIN
        )
        self.stop_reason: str | None = None
        self.attempts: list[dict[str, Any]] = []

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Delegate one attempt unless a stop rule or the cap forbids it."""
        if self.stop_reason is not None:
            raise StopProvider(self.stop_reason)
        if self._ledger.spent + self._reserve > self._ledger.cap:
            self.stop_reason = f"cap: spent {self._ledger.spent:.4f} + reserve {self._reserve:.4f}"
            raise StopProvider(self.stop_reason)
        if self._ledger.spent_by(self._key) + self._reserve > self._subcap:
            self.stop_reason = f"subcap {self._subcap:.2f} for {self._key}"
            raise StopProvider(self.stop_reason)
        record: dict[str, Any] = {
            "attempt": len(self.attempts) + 1,
            "user_sha256": sha256_text(payload.user_prompt),
            "image": Path(payload.image_path).name,
        }
        try:
            response = self._inner.analyze(payload, config)
        except BackendHTTPError as exc:
            record["error"] = f"HTTP {exc.status_code}: {str(exc)[:300]}"
            self.attempts.append(record)
            if exc.status_code in (401, 402, 403, 429):
                self.stop_reason = f"HTTP {exc.status_code}"
            raise
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            self.attempts.append(record)
            raise
        usd, tin, tout = usage_cost(self._adapter, response.token_usage)
        self._ledger.add(self._key, usd)
        record.update(
            {
                "text": response.text,
                "token_usage": response.token_usage,
                "usd": round(usd, 6),
                "served_model": response.served_model,
                "finish_reason": response.finish_reason,
                "refusal": response.refusal,
                "refusal_category": response.refusal_category,
                "latency_ms": response.latency_ms,
            }
        )
        self.attempts.append(record)
        if self._adapter == "anthropic" and (
            response.refusal or re.search(r"\bI can(?:no|')t help\b", response.text or "")
        ):
            self.stop_reason = "anthropic refusal"
        return response


def load_done(calls: Path) -> set[str]:
    """Keys already recorded in calls.jsonl."""
    if not calls.is_file():
        return set()
    return {json.loads(line)["key"] for line in calls.read_text().splitlines() if line.strip()}


def cmd_stimuli(args: argparse.Namespace) -> int:
    """Write and print the integrity table."""
    rows = integrity(load_stimuli(Path(args.docs_root)))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stimuli.json").write_text(json.dumps(rows, indent=1) + "\n")
    for r in rows:
        print(
            f"{r['cls']:11} {r['episode']:22} {r['request_id'][:8]} first={r['first_trigger']!s:5} "
            f"match={r['matches_stored']!s:5} dlen={r['len_delta_vs_stored']:+5d} "
            f"A+{r['A_minus_base_chars']} B+{r['B_minus_A_chars']}"
        )
        if r["first_diff"]:
            print(f"    first diff line {r['first_diff']['line']}: {r['first_diff']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Paid calls: one per stimulus per condition for one backend arm and replicate."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    calls_path = out / "calls.jsonl"
    ledger = Ledger(out / "ledger.json", args.cap)
    done = load_done(calls_path)
    vlm = yaml.safe_load((REPO_ROOT / "config" / "models.yaml").read_text())["vlm"]
    adapter = backend_adapter(vlm, args.backend)
    reasoner_config = resolve_reasoner_config(vlm, args.backend)
    backend_config = load_backend_config(vlm, args.backend)
    guard = GuardedBackend(
        build_backend(adapter, backend_config),
        adapter,
        args.backend,
        ledger,
        args.subcap,
        reasoner_config.max_tokens,
    )
    reasoner = Reasoner(
        guard, reasoner_config, describe_effective_sampling(reasoner_config, backend_config)
    )
    stimuli = load_stimuli(Path(args.docs_root))
    if args.only:
        stimuli = [s for s in stimuli if any(s.request_id.startswith(x) for x in args.only.split(","))]
    conditions = args.conditions.split(",")
    for s in stimuli:
        for condition in conditions:
            key = f"{args.backend}|{condition}|{args.rep}|{s.request_id}"
            if key in done:
                continue
            if guard.stop_reason is not None:
                print(f"STOP {args.backend}: {guard.stop_reason}")
                return 0
            request = s.request(condition)
            guard.attempts = []
            started = time.time()
            result = reasoner.run(request)
            usd = sum(a.get("usd", 0.0) for a in guard.attempts)
            billed = [a for a in guard.attempts if "usd" in a]
            if not billed and guard.stop_reason is not None:
                print(f"STOP {args.backend}: {guard.stop_reason} (no call made for {key})")
                return 0
            record = {
                "key": key,
                "backend": args.backend,
                "adapter": adapter,
                "model_id": getattr(backend_config, "model_id", None),
                "condition": condition,
                "rep": args.rep,
                "cls": s.cls,
                "episode": s.label,
                "request_id": s.request_id,
                "first_trigger": s.first_trigger,
                "user_sha256": sha256_text(build_prompt_payload(request).user_prompt),
                "frame_sha256": sha256_file(s.frame),
                "reasoner_config": reasoner_config.model_dump(mode="json"),
                "wall_start": round(started, 1),
                "attempts": guard.attempts,
                "result": result.model_dump(mode="json"),
                "usd": round(usd, 6),
                "stop_reason": guard.stop_reason,
            }
            with calls_path.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
            dec = result.decision
            print(
                f"{key[:60]:60} parse={result.diagnostics.parse_status} "
                f"strategy={dec.strategy if dec else None} plan={'Y' if dec and dec.proposed_plan else 'N'} "
                f"usd={usd:.4f} total={ledger.spent:.4f}"
            )
            time.sleep(args.pace)
    print(f"done {args.backend} rep={args.rep}; ledger total {ledger.spent:.4f}")
    return 0


def _strip(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if k not in ("reason", "plan_id")}


def phase_sig(phases: list[dict[str, Any]]) -> list[Any]:
    """Per phase: label, acting robot, every action with parameters (reason/plan_id dropped)."""
    return [
        (
            p["label"],
            p.get("robot_id"),
            sorted(
                (a["robot_id"], a["action"], json.dumps(_strip(a["parameters"]), sort_keys=True))
                for a in p["command"]["actions"]
            ),
        )
        for p in phases
    ]


def command_sig(cmd: dict[str, Any] | None) -> list[Any] | None:
    """Action signature of a single grounded command."""
    if cmd is None:
        return None
    return sorted(
        (a["robot_id"], a["action"], json.dumps(_strip(a.get("parameters", {})), sort_keys=True))
        for a in cmd.get("actions", [])
    )


def outcome_sig(outcome: Any) -> list[Any] | None:
    """Phase signature when junction phases exist, else the grounded command's."""
    if outcome.junction_phases is not None:
        return phase_sig(outcome.junction_phases.model_dump(mode="json")["phases"])
    return command_sig(outcome.grounded_command)


def recede_order_of(outcome: Any) -> list[str]:
    """Robot ids of the dispatched recede phases, in dispatch order."""
    if outcome.junction_phases is None:
        return []
    return [p.robot_id for p in outcome.junction_phases.phases if p.label == "recede"]


def make_pipeline(s: Stimulus, mode: str) -> InProcessPipeline:
    """The M5 default pipeline for this snapshot's recorded config, offline (no stage-2 call)."""
    cfg = s.config
    return InProcessPipeline(
        reasoner=None,
        ground_fn=ground_reasoner_result,
        scene_geometry=cfg.scenario_geometry,
        static_obstacles=cfg.static_obstacles,
        yield_feasibility_mode=s.yfm,
        grounding_params=s.params,
        retreat_chooser=None,
        stage2_enabled=cfg.stage2_retreat_selection,
        candidate_marker=None,
        priorities=registry_priorities(cfg.initial_tasks),
        plan_tracker=PlanTracker(),
        registry_order=tuple(cfg.initial_tasks),
        dispatch_order_source=mode,
    )


def raw_plan_verdict(raw_text: str | None) -> tuple[str, list[Any] | None]:
    """Why a plan is absent after parsing, from the model's own text."""
    from reasoning.vlm.output_parser import _extract_json_object

    try:
        obj = _extract_json_object(raw_text or "")
    except Exception as exc:
        return f"no_json: {type(exc).__name__}", None
    if not isinstance(obj, dict) or "proposed_plan" not in obj:
        return "absent", None
    plan = obj["proposed_plan"]
    if plan is None:
        return "null", None
    if not isinstance(plan, list):
        return "not_a_list", None
    legs = [(x.get("robot_id"), x.get("action")) if isinstance(x, dict) else x for x in plan]
    ids = [x[0] for x in legs if isinstance(x, tuple)]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        return f"duplicate_robot: {dup}", legs
    return "present_in_raw", legs


def analyze_one(s: Stimulus, result: ReasonerResult, condition: str) -> dict[str, Any]:
    """Replay one answer offline through the real pipeline, three ways."""
    request = s.request(condition) if condition in ("A", "B") else s.base_request()
    row: dict[str, Any] = {}
    dec = result.decision
    row["valid"] = dec is not None
    row["parse_status"] = result.diagnostics.parse_status
    row["degradations"] = list(result.diagnostics.decision_degradations or [])
    if dec is None:
        return row
    known = sorted(r.robot_id for r in request.robot_states)
    row["strategy"] = dec.strategy
    row["involved"] = list(dec.involved_robots)
    row["yield_robot"] = dec.yield_robot
    row["jc_all_four"] = dec.strategy == "junction_clear" and sorted(dec.involved_robots) == known
    row["plan_present"] = dec.proposed_plan is not None
    row["plan"] = (
        [(leg.robot_id, leg.action) for leg in dec.proposed_plan] if dec.proposed_plan else None
    )
    verdict, raw_legs = raw_plan_verdict(result.raw_text)
    row["raw_plan_verdict"] = verdict
    if not row["plan_present"]:
        row["raw_plan"] = raw_legs
    frame = snapshot_frame_from_request(request)
    geometry = s.config.scenario_geometry
    if dec.strategy == "junction_clear":
        candidates = _junction_recede_candidates(dec, geometry)
        ranked = rank_recede_candidates(frame, candidates, geometry, s.params)
        costs = {r: recede_cost(frame, r, geometry, s.params) for r in candidates}
        row["chi_order"] = ranked
        row["chi_costs"] = {k: (None if v is None else round(v, 4)) for k, v in costs.items()}
        if len(ranked) >= 2 and all(costs[r] is not None for r in ranked[:2]):
            row["chi_margin"] = round(abs(costs[ranked[1]] - costs[ranked[0]]), 4)
    vp = verify_and_repair_plan(
        dec,
        frame,
        geometry=geometry,
        static_obstacles=s.config.static_obstacles,
        yield_feasibility_mode=s.yfm,
        grounding_params=s.params,
        priorities=registry_priorities(s.config.initial_tasks) or None,
    )
    row["verify_provenance"] = vp.provenance
    row["verify_rejection"] = vp.rejection_reason
    row["verify_edits"] = [(e.op, list(e.robot_ids), e.reason) for e in vp.edits]
    row["verified_legs"] = [(leg.robot_id, leg.action) for leg in vp.legs]
    row["plan_recede_order"] = plan_recede_order(vp.legs) if dec.proposed_plan else None
    outcomes = {}
    no_plan = result.model_copy(
        update={"decision": dec.model_copy(update={"proposed_plan": None})}
    )
    for name, mode, res in (
        ("chi", "chi", result),
        ("mwv", "model_when_verified", result),
        ("noplan", "chi", no_plan),
    ):
        o = make_pipeline(s, mode)._run_from_result(request, res)
        outcomes[name] = o
        row[f"{name}_terminal"] = str(o.terminal_stage)
        row[f"{name}_failure"] = o.failure_reason
        row[f"{name}_recede_order"] = recede_order_of(o)
        row[f"{name}_dispatch_order_source"] = o.dispatch_order_source
        if o.plan is not None:
            row[f"{name}_provenance"] = o.plan.provenance
            row[f"{name}_dispatch_matches_plan"] = o.plan.dispatch_matches_plan
            row[f"{name}_order_equivalent"] = o.plan.order_equivalent
        row[f"{name}_plan_error"] = o.plan_error
        row[f"{name}_yield_refusal"] = yield_refusal_fan_out(o.grounded_command)
        if o.junction_phases is not None:
            ph = o.junction_phases.phases
            cross = next((p for p in ph if p.label == "cross"), None)
            row[f"{name}_executed_yielder"] = (
                next(
                    (
                        a["robot_id"]
                        for a in cross.command["actions"]
                        if a["action"] == "yield"
                    ),
                    None,
                )
                if cross is not None
                else None
            )
            row[f"{name}_phase_labels"] = [p.label for p in ph]
    sig_mwv = outcome_sig(outcomes["mwv"])
    sig_noplan = outcome_sig(outcomes["noplan"])
    sig_chi = outcome_sig(outcomes["chi"])
    row["mwv_differs_from_noplan"] = sig_mwv != sig_noplan
    row["chi_differs_from_noplan"] = sig_chi != sig_noplan
    if sig_mwv != sig_noplan and outcomes["mwv"].junction_phases and outcomes["noplan"].junction_phases:
        a = phase_sig(outcomes["mwv"].junction_phases.model_dump(mode="json")["phases"])
        b = phase_sig(outcomes["noplan"].junction_phases.model_dump(mode="json")["phases"])
        row["mwv_changed_phase_labels"] = sorted(
            {x[0] for x, y in zip(a, b, strict=False) if x != y} | ({"<length>"} if len(a) != len(b) else set())
        )
    return row


def recorded_result(s: Stimulus) -> ReasonerResult:
    """The recorded live answer as a ReasonerResult (decision + raw text)."""
    art = s.artifact
    dec = art.get("decision")
    decision = (
        CongestionDecision(**{k: v for k, v in dec.items() if k in CongestionDecision.model_fields})
        if dec
        else None
    )
    diag = art.get("diagnostics") or {}
    return ReasonerResult(
        request_id=s.request_id,
        decision=decision,
        raw_text=art.get("raw_text"),
        diagnostics=ReasonerDiagnostics(
            request_id=s.request_id,
            backend_id=diag.get("backend_id") or "recorded",
            attempts=diag.get("attempts") or 1,
            parse_status=diag.get("parse_status") or "valid",
            decision_degradations=diag.get("decision_degradations") or [],
        ),
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    """Offline replay of stored answers; write analysis.jsonl (or the fidelity file)."""
    out = Path(args.out)
    stimuli = {s.request_id: s for s in load_stimuli(Path(args.docs_root))}
    rows = []
    if args.recorded:
        for s in stimuli.values():
            if not s.cls.startswith("live"):
                continue
            row = analyze_one(s, recorded_result(s), "recorded")
            plan = s.artifact.get("plan") or {}
            jp = s.artifact.get("junction_phases")
            row.update(
                {
                    "episode": s.label,
                    "request_id": s.request_id,
                    "recorded_provenance": plan.get("provenance"),
                    "recorded_dispatch_order_source": s.artifact.get("dispatch_order_source"),
                    "provenance_reproduced": plan.get("provenance") == row.get("chi_provenance"),
                }
            )
            if jp:
                rec_sig = phase_sig(jp["phases"])
                o = make_pipeline(s, "chi")._run_from_result(s.base_request(), recorded_result(s))
                row["phases_reproduced"] = outcome_sig(o) == rec_sig
            rows.append(row)
        path = out / "fidelity_recorded.jsonl"
    else:
        for line in (out / "calls.jsonl").read_text().splitlines():
            rec = json.loads(line)
            s = stimuli[rec["request_id"]]
            result = ReasonerResult(**rec["result"])
            row = analyze_one(s, result, rec["condition"])
            row.update(
                {
                    k: rec[k]
                    for k in ("key", "backend", "condition", "rep", "cls", "episode", "request_id",
                              "first_trigger", "usd")
                }
            )
            row["stopped_call"] = not any("usd" in a for a in rec["attempts"])
            row["n_attempts"] = len(rec["attempts"])
            row["refusal_attempts"] = sum(1 for a in rec["attempts"] if a.get("refusal"))
            rows.append(row)
        path = out / "analysis.jsonl"
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    print(f"wrote {len(rows)} rows -> {path}")
    return 0


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("stimuli", "run", "analyze"):
        p = sub.add_parser(name)
        p.add_argument("--docs-root", required=True, help="directory holding the vgu-vlm-swarm* worktrees")
        p.add_argument("--out", default=str(DEFAULT_OUT))
        if name == "run":
            p.add_argument("--backend", required=True, help="models.yaml arm id")
            p.add_argument("--conditions", default="A,B")
            p.add_argument("--rep", type=int, default=0)
            p.add_argument("--cap", type=float, default=1.50)
            p.add_argument("--subcap", type=float, required=True)
            p.add_argument("--pace", type=float, default=1.0)
            p.add_argument("--only", default="", help="comma-separated request id prefixes")
        if name == "analyze":
            p.add_argument("--recorded", action="store_true")
    args = ap.parse_args()
    return {"stimuli": cmd_stimuli, "run": cmd_run, "analyze": cmd_analyze}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
