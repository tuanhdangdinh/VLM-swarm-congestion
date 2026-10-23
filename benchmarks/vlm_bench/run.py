"""Bench runs: build items, score `recorded` / `classical`, `replay`, and write reports."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yaml
from PIL import Image

from benchmarks.vlm_bench.backends import DEFAULT_CACHE_DIR, CachedBackend
from benchmarks.vlm_bench.classical_ref import classical_decision, reproduces_recorded
from benchmarks.vlm_bench.grounder_offline import executable_yielders, ground_decision
from benchmarks.vlm_bench.items import REPO_ROOT, file_md5, read_items
from benchmarks.vlm_bench.models import BenchItem, ItemScore
from benchmarks.vlm_bench.scoring import Summary, score_item, summarize
from benchmarks.vlm_bench.variants import VARIANTS, ReplayContext, get_variant
from reasoning.vlm.models import (
    FailureContext,
    PlanStateContext,
    ReasonerRequest,
    RobotCandidateOptions,
    StaticObstacleInput,
)

BENCH_DIR = Path(__file__).resolve().parent
NEUTRAL_RGB = (128, 128, 128)
PROMPT_VARIANTS = VARIANTS


def score_items(items: Sequence[BenchItem], mode: str, oracle: bool = True) -> list[ItemScore]:
    """Score items in `recorded` or `classical` mode (zero API calls).

    Args:
        items: The items.
        mode: "recorded" (the stored answer) or "classical" (re-run chooser).
        oracle: Whether to run the geometry oracle on yield decisions.

    Returns:
        One score per item; classical scores carry the live-shadow
        reproduction flag in `note`.

    Raises:
        ValueError: For an unknown mode.
    """
    oracle_fn = executable_yielders if oracle else None
    out: list[ItemScore] = []
    for item in items:
        if mode == "recorded":
            out.append(
                score_item(item, item.recorded.decision, "recorded", ground_decision, oracle_fn)
            )
        elif mode == "classical":
            decision = classical_decision(item)
            score = score_item(
                item, decision, "classical", ground_decision, oracle_fn, with_cost=False
            )
            repro = reproduces_recorded(item, decision)
            out.append(score.model_copy(update={"note": f"reproduces_live_shadow={repro}"}))
        else:
            raise ValueError(f"unknown mode {mode!r}")
    return out


def plan_artifacts(items: Sequence[BenchItem]) -> list[list[dict[str, Any]]]:
    """Per-episode `{decision, plan, plan_state}` artifacts for A33(6) plan quality.

    Args:
        items: The items (recorded mode).

    Returns:
        One list per episode bundle, in stamp order.
    """
    by_bundle: dict[str, list[BenchItem]] = {}
    for item in items:
        by_bundle.setdefault(item.bundle, []).append(item)
    return [
        [
            {"decision": i.recorded.decision, "plan": i.live.plan, "plan_state": i.live.plan_state}
            for i in sorted(group, key=lambda i: i.stamp)
        ]
        for group in by_bundle.values()
    ]


def rebuild_request(item: BenchItem, image_path: str) -> ReasonerRequest:
    """Rebuild the live `ReasonerRequest` of one item through the production builder.

    Args:
        item: The bench item.
        image_path: Image to attach (frame or neutral stand-in).

    Returns:
        The request; under the `baseline` variant its rendered user prompt
        must hash to `item.prompt.user_sha256`.
    """
    from swarm_orchestrator.models import RobotView, SceneSnapshot
    from swarm_orchestrator.reasoning_pipeline import build_reasoner_request

    from benchmarks.vlm_bench.grounder_offline import item_config

    config = item_config(item)
    scene = item.scene
    snapshot = SceneSnapshot(
        stamp=scene["stamp"],
        frame_id=scene.get("frame_id", "overhead_camera"),
        dropped_frame=bool(scene.get("dropped_frame", False)),
        robots=[
            RobotView(
                robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                linear_velocity=r.get("linear_velocity", 0.0), status=r["status"],
                stamp=r.get("stamp", scene["stamp"]),
                goal=None if r.get("goal") is None else tuple(r["goal"]), task=r.get("task"),
            )
            for r in scene["robots"]
        ],
    )
    p = item.prompt
    conditions = p.prompt_conditions or {}
    kwargs: dict[str, Any] = {}
    if (conditions.get("metric_grid") or {}).get("stated"):
        kwargs["metric_grid_spacing_m"] = conditions.get("metric_grid_spacing_m")
    if (conditions.get("motion_trails") or {}).get("stated"):
        kwargs["motion_trails_drawn"] = True
    if conditions.get("candidate_options") is not None:
        kwargs["candidate_options"] = [
            RobotCandidateOptions(**entry) for entry in conditions["candidate_options"]
        ]
    return build_reasoner_request(
        item.request_id,
        snapshot=snapshot,
        image_path=image_path,
        failure_context=FailureContext(**p.failure_context) if p.failure_context else None,
        last_failed_context=(
            FailureContext(**p.last_failed_context) if p.last_failed_context else None
        ),
        include_pairwise_geometry=config.prompt_pairwise_geometry,
        static_obstacles=[StaticObstacleInput.model_validate(o) for o in config.static_obstacles],
        include_static_obstacles=config.prompt_static_obstacles,
        robot_presentation_order=p.robot_order,
        prompt_version=p.prompt_version,
        plan_state=PlanStateContext(**p.plan_state) if p.plan_state else None,
        **kwargs,
    )


def neutral_image(cache_dir: Path, size: tuple[int, int] = (1280, 720)) -> Path:
    """A mid-grey PNG used when an item has no frame.

    Args:
        cache_dir: Directory to write it in.
        size: `(width, height)`.

    Returns:
        The PNG path.
    """
    path = Path(cache_dir) / f"neutral_{size[0]}x{size[1]}.png"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, NEUTRAL_RGB).save(path, format="PNG")
    return path


def replay_items(
    items: Sequence[BenchItem],
    backend_id: str,
    variant: str = "baseline",
    cache_dir: Path = DEFAULT_CACHE_DIR,
    models_yaml: Path = REPO_ROOT / "config/models.yaml",
    backend_factory: Callable[[str, dict[str, Any]], Any] | None = None,
) -> tuple[list[ItemScore], dict[str, Any]]:
    """Re-ask a backend on every item under a prompt variant, through the response cache.

    Args:
        items: The items.
        backend_id: A `config/models.yaml` backend id.
        variant: A registered variant name (`variants.list_variants()`).
        cache_dir: Response cache directory.
        models_yaml: The models config.
        backend_factory: Test seam returning a backend for `(id, raw_vlm)`;
            None uses the production `build_backend`.

    Returns:
        The scores and a run-info dict: cache hits/misses, skipped items,
        the variant and its generator version, and per item the candidate
        count and the SHA-256 of the composed user prompt.

    Raises:
        ValueError: For an unknown variant.
    """
    from reasoning.vlm.backend_factory import (
        backend_adapter,
        build_backend,
        describe_effective_sampling,
        load_backend_config,
        resolve_reasoner_config,
    )
    from reasoning.vlm.reasoner import Reasoner

    plugin = get_variant(variant)
    raw_vlm = yaml.safe_load(Path(models_yaml).read_text())["vlm"]
    backend_config = load_backend_config(raw_vlm, backend_id)
    reasoner_config = resolve_reasoner_config(raw_vlm, backend_id)
    inner = (
        backend_factory(backend_id, raw_vlm)
        if backend_factory is not None
        else build_backend(backend_adapter(raw_vlm, backend_id), backend_config)
    )
    model_id = getattr(backend_config, "model_id", None)
    cached = CachedBackend(inner, backend_id, model_id, Path(cache_dir) / backend_id)
    reasoner = Reasoner(
        cached, reasoner_config, describe_effective_sampling(reasoner_config, backend_config)
    )
    from reasoning.vlm.prompt_builder import build_prompt_payload

    context = ReplayContext(backend=cached, reasoner_config=reasoner_config, reasoner=reasoner)
    grey = neutral_image(Path(cache_dir))
    scores: list[ItemScore] = []
    skipped: list[str] = []
    per_item: dict[str, dict[str, Any]] = {}
    for item in items:
        image = item.frame_path or str(grey)
        request = rebuild_request(item, image)
        # Every variant builds on the live prompt, so it must reproduce first.
        rendered = build_prompt_payload(request).user_prompt
        if hashlib.sha256(rendered.encode()).hexdigest() != item.prompt.user_sha256:
            skipped.append(item.item_id)
            continue
        answer = plugin.answer(item, request, context)
        score = score_item(
            item, answer.decision, f"replay:{variant}", ground_decision, executable_yielders,
            with_cost=False,
        )
        note = f"image={'frame' if item.frame_path else 'neutral'}"
        if answer.note is not None:
            note += f"; {answer.note}"
        scores.append(
            score.model_copy(
                update={
                    "token_usage": answer.token_usage,
                    "latency_ms": answer.latency_ms,
                    "note": note,
                }
            )
        )
        per_item[item.item_id] = {
            "n_candidates": answer.n_candidates,
            "prompt_sha256": answer.prompt_sha256,
            "attempts": answer.attempts,
            "parse_status": answer.parse_status,
        }
    info = {
        "backend_id": backend_id,
        "model_id": model_id,
        "variant": variant,
        "candidate_generator_version": plugin.generator_version,
        "cache_hits": cached.hits,
        "cache_misses": cached.misses,
        "skipped_prompt_mismatch": skipped,
        "per_item": per_item,
    }
    return scores, info


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_config(
    mode: str, items_path: Path, items: Sequence[BenchItem], extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    """The provenance block stored beside every run.

    Args:
        mode: The run mode.
        items_path: The item file.
        items: The items (for the grounding/rag files they reference).
        extra: Mode-specific fields (backend, variant, cache counts).

    Returns:
        The config dict.
    """
    params_files = sorted({i.grounding.params_path for i in items if i.grounding.params_path})
    variant = (extra or {}).get("variant")
    text = "live_builder" if variant in (None, "baseline") else f"live_builder+{variant}"
    return {
        "mode": mode,
        "items_path": str(items_path),
        "items_md5": file_md5(Path(items_path)),
        "n_items": len(items),
        "git_head": _git_head(),
        "bench_code_md5": {
            str(p.relative_to(BENCH_DIR)): file_md5(p) for p in sorted(BENCH_DIR.rglob("*.py"))
        },
        "grounding_files_md5": {p: file_md5(REPO_ROOT / p) for p in params_files},
        "rag_yaml_md5": file_md5(REPO_ROOT / "config/rag.yaml"),
        "recorded_params_match_file": {
            p: sorted({str(i.grounding.params_match_file) for i in items
                       if i.grounding.params_path == p})
            for p in params_files
        },
        "frames_present": sum(1 for i in items if i.frame_path),
        "representation": {"image": "frame_if_present_else_neutral", "text": text},
        **(extra or {}),
    }


def write_run(
    scores: Sequence[ItemScore],
    out: Path,
    summary_path: Path | None,
    config: dict[str, Any],
    items: Sequence[BenchItem],
) -> dict[str, Summary]:
    """Write the run JSONL, its `.config.json`, and the Markdown summary.

    Args:
        scores: The item scores.
        out: The JSONL path.
        summary_path: The Markdown path, or None.
        config: The run config.
        items: The items (for plan quality in recorded mode).

    Returns:
        Summaries keyed "all" and by batch.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as handle:
        for score in scores:
            handle.write(json.dumps(score.model_dump(mode="json"), sort_keys=True) + "\n")
    out.with_suffix(".config.json").write_text(json.dumps(config, indent=2, sort_keys=True))
    recorded = config.get("mode") == "recorded"
    batches = sorted({s.batch for s in scores}, key=batch_sort_key)
    summaries = {"all": summarize(scores, plan_artifacts(items) if recorded else None)}
    for batch in batches:
        subset = [s for s in scores if s.batch == batch]
        batch_items = [i for i in items if i.batch == batch]
        summaries[batch] = summarize(subset, plan_artifacts(batch_items) if recorded else None)
    if summary_path is not None:
        Path(summary_path).write_text(render_summary(summaries, config))
    return summaries


BATCH_ORDER = (
    "churn_wave", "live_batch", "resume", "batch2", "batch3", "batch4", "batch5", "batch6",
)


def batch_sort_key(batch: str) -> tuple[int, str]:
    """Sort batches in collection order, unknown names last.

    Args:
        batch: The batch directory name.

    Returns:
        The sort key.
    """
    return (BATCH_ORDER.index(batch) if batch in BATCH_ORDER else len(BATCH_ORDER), batch)


SUMMARY_ROWS: tuple[tuple[str, Callable[[Summary], str]], ...] = (
    ("items / valid / positive", lambda s: f"{s.n_items} / {s.n_valid} / {s.n_positive}"),
    ("M3 feasibility (positives)", lambda s: s.feasibility.text()),
    ("M3 feasibility (yields)", lambda s: s.yield_feasibility.text()),
    ("live reproduction of refusal", lambda s: s.live_reproduction.text()),
    ("cluster coverage (valid, ≥1 cluster)", lambda s: s.coverage.text()),
    ("cluster coverage (positives)", lambda s: s.coverage_positive.text()),
    ("mean per-cluster recall", lambda s: _f(s.mean_cluster_recall)),
    ("involved F1, matched (n)", lambda s: f"{_f(s.f1_matched_mean)} ({s.n_matched})"),
    ("involved F1, unconditional", lambda s: _f(s.f1_unconditional_mean)),
    ("yielder vs M3 oracle", lambda s: f"{s.oracle_agreement.text()}; empty {s.oracle_empty}"),
    ("yielder vs live shadow", lambda s: s.classical_agreement.text()),
    ("yielder vs MC", lambda s: s.mc_agreement.text()),
    ("FP rate (no GT conflict in window)", lambda s: s.fp_rate.text()),
    ("unmatched positives (A33)", lambda s: str(s.unmatched_positives)),
    ("mean total tokens", lambda s: _f(s.mean_total_tokens, 0)),
    ("mean latency ms", lambda s: _f(s.mean_latency_ms, 0)),
    ("est $ (cost.log)", lambda s: _f(s.est_usd_total, 4)),
)


def _f(value: float | None, digits: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def render_summary(summaries: dict[str, Summary], config: dict[str, Any]) -> str:
    """Render the Markdown summary: pooled column first, then one column per batch.

    Args:
        summaries: Summaries keyed "all" and by batch.
        config: The run config.

    Returns:
        The Markdown text.
    """
    cols = list(summaries)
    lines = [
        f"# VLM bench run: {config.get('mode')}",
        "",
        f"Items: `{config.get('items_path')}` (md5 {config.get('items_md5')}); "
        f"git {config.get('git_head')}.",
        "",
        "| Metric | " + " | ".join(cols) + " |",
        "|---|" + "---|" * len(cols),
    ]
    for label, fn in SUMMARY_ROWS:
        lines.append(f"| {label} | " + " | ".join(fn(summaries[c]) for c in cols) + " |")
    pooled = summaries["all"]
    lines += ["", "Refusal histogram (pooled): " + (
        ", ".join(f"{k} {v}" for k, v in pooled.refusal_histogram.items()) or "none"
    )]
    lines += ["", "Strategies (pooled positives): " + ", ".join(
        f"{k} {v}" for k, v in pooled.strategy_counts.items()
    )]
    if pooled.plan_quality is not None:
        lines += ["", "Plan quality (A33(6), pooled): " + json.dumps(pooled.plan_quality)]
    return "\n".join(lines) + "\n"


def load(items_path: Path) -> list[BenchItem]:
    """Read an item file.

    Args:
        items_path: The JSONL path.

    Returns:
        The items.
    """
    return read_items(Path(items_path))
