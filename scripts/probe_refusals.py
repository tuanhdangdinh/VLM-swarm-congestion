"""Census and offline replay probe for gpt-4o safety refusals in M2 decisions.

Two subcommands:

* `census` scans every decision artifact under `data/logs/vm_runs/` and
  tabulates refusals against total analyses per run, backend, static-obstacle
  condition, failure-context presence, and solo/pair stall.
* `replay` re-sends stored prompts through the production OpenAI backend
  (`build_backend("openai", ...)` plus `invoke_backend`/`parse_decision_text`)
  and records the refusal rate per prompt, plus wording ablations.

Rendered prompt text is replayed verbatim from the artifacts; the prompt
builder is never re-run, so ablations act on copies of the recorded text and
production prompt code stays untouched. The original overhead frames live on
the simulation VM only, so replays substitute a synthetic image: either a
neutral grey field or a crude top-down render of the recorded robot poses.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reasoning.vlm.backend_factory import build_backend  # noqa: E402
from reasoning.vlm.errors import DecisionValidationError, VLMOutputParseError  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    OpenAIBackendConfig,
    PromptPayload,
    ReasonerConfig,
)
from reasoning.vlm.output_parser import parse_decision_text  # noqa: E402
from reasoning.vlm.reasoner import invoke_backend  # noqa: E402

RUNS_DIR = REPO_ROOT / "data/logs/vm_runs"
OUT_DIR = REPO_ROOT / "data/experiments/2026-09-25-refusals"

# Both phrasings observed in `raw_text`: with and without the "but".
REFUSAL_RE = re.compile(r"I(?:'m| am) sorry.{0,20}I can'?t assist", re.I)
OBSTACLE_HEADER = "Static obstacles (world-frame axis-aligned boxes):"
FAILURE_CONTEXT_HEADER = "Previous attempt in this episode:"
# `Reasoner` records the configured id ("openai") on a failed result but the
# backend-reported id ("gpt-4o") on a successful one; fold them together.
OPENAI_BACKEND_IDS = frozenset({"openai", "gpt-4o"})

# Copied from `reasoning.vlm.reasoner._REASK_SUFFIX` so the reask ablation can
# reproduce attempt 2 without importing a private module member.
REASK_SUFFIX = (
    "\n\nYour previous response was invalid: {error_message}\n"
    "Please return ONLY a valid JSON object matching the schema above.\n"
    "Do not include any text, markdown, or explanation outside the JSON."
)

# Wording groups tested one at a time in ablation (c). Each maps a phrase that
# plausibly reads as physical-harm or coercion language onto a neutral synonym.
WORD_GROUPS: dict[str, dict[str, str]] = {
    "collision": {
        "deadlocks": "mutual blocks",
        "deadlock": "mutual block",
        "standoff": "face-to-face stop",
        "physically conflicting": "spatially overlapping",
        "blocked": "obstructed",
    },
    "motion": {
        "backs up": "moves rearward",
        "back up to clear": "move rearward to clear",
        "reverse": "rearward",
    },
    "authority": {
        "priority_override": "priority_first",
        "unsafe": "irregular",
        "anomaly": "unusual_pattern",
        "anomalies": "unusual patterns",
    },
}


def is_refusal(text: str | None) -> bool:
    """Return True when assistant text is an OpenAI safety refusal."""
    return bool(text) and bool(REFUSAL_RE.search(text or ""))


@dataclass
class ArtifactRow:
    """One decision artifact reduced to the fields the census tabulates."""

    run: str
    path: Path
    request_id: str
    backend: str
    obstacles: bool
    failure_context: bool
    stall: str
    parse_status: str | None
    attempts: int | None
    error_type: str | None
    refusal: bool
    user_prompt: str = field(repr=False, default="")
    system_prompt: str = field(repr=False, default="")


def _run_log_text(run_dir: Path) -> str:
    parts = []
    for path in sorted(run_dir.glob("*.log")) + sorted(run_dir.glob("component_logs/*m5*.log")):
        try:
            parts.append(path.read_text(errors="replace"))
        except OSError:
            continue
    return "\n".join(parts)


def _analysis_robot_counts(run_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    pattern = re.compile(r"starting analysis request=(\w+) robots=\[([^\]]*)\]")
    for match in pattern.finditer(_run_log_text(run_dir)):
        counts[match.group(1)] = len(re.findall(r"'([^']+)'", match.group(2)))
    return counts


def collect_artifacts(runs_dir: Path = RUNS_DIR) -> list[ArtifactRow]:
    """Load every decision artifact under `runs_dir` into census rows.

    Args:
        runs_dir: Directory holding one subdirectory per VM run.

    Returns:
        One `ArtifactRow` per decision artifact, ordered by run then filename.
    """
    rows: list[ArtifactRow] = []
    for run_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        decision_dirs = [
            d for d in (run_dir / "decisions", run_dir / "m5_decisions") if d.is_dir()
        ]
        if not decision_dirs:
            continue
        robot_counts = _analysis_robot_counts(run_dir)
        for decision_dir in decision_dirs:
            for path in sorted(decision_dir.glob("*.json")):
                data = json.loads(path.read_text())
                prompt = data.get("prompt") or {}
                user_prompt = prompt.get("user_prompt") or ""
                diagnostics = data.get("diagnostics") or {}
                request_id = data.get("request_id") or path.stem
                backend_id = diagnostics.get("backend_id")
                n_robots = robot_counts.get(request_id)
                rows.append(
                    ArtifactRow(
                        run=run_dir.name,
                        path=path,
                        request_id=request_id,
                        backend="gpt-4o" if backend_id in OPENAI_BACKEND_IDS else str(backend_id),
                        obstacles=OBSTACLE_HEADER in user_prompt,
                        failure_context=FAILURE_CONTEXT_HEADER in user_prompt,
                        stall={1: "solo", 2: "pair"}.get(n_robots or 0, "unknown"),
                        parse_status=diagnostics.get("parse_status"),
                        attempts=diagnostics.get("attempts"),
                        error_type=diagnostics.get("error_type"),
                        refusal=is_refusal(data.get("raw_text")),
                        user_prompt=user_prompt,
                        system_prompt=prompt.get("system_prompt") or "",
                    )
                )
    return rows


def _tabulate(rows: list[ArtifactRow], key) -> list[tuple]:
    buckets: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        bucket = buckets[key(row)]
        bucket["total"] += 1
        bucket["refusal"] += int(row.refusal)
        bucket["failed"] += int(row.parse_status == "failed")
        # "invalid" means attempt 1 produced no JSON but the re-ask recovered;
        # both statuses therefore mark an attempt-1 non-JSON response.
        bucket["attempt1_nonjson"] += int(row.parse_status in ("failed", "invalid"))
        bucket["fc"] += int(row.failure_context)
        bucket[row.stall] += 1
    return [(k, buckets[k]) for k in sorted(buckets, key=str)]


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for the 2x2 table [[a, b], [c, d]]."""
    total, row1, col1 = a + b + c + d, a + b, a + c
    if min(row1, col1, total - row1, total - col1) < 0 or total == 0:
        return 1.0

    def hypergeom(x: int) -> float:
        return (
            math.comb(row1, x)
            * math.comb(total - row1, col1 - x)
            / math.comb(total, col1)
        )

    observed = hypergeom(a)
    low, high = max(0, col1 - (total - row1)), min(row1, col1)
    return sum(hypergeom(x) for x in range(low, high + 1) if hypergeom(x) <= observed + 1e-12)


def write_census(rows: list[ArtifactRow], out_dir: Path) -> None:
    """Write the census JSON and print the summary tables to stdout."""
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "run": r.run,
            "file": str(r.path.relative_to(REPO_ROOT)),
            "request_id": r.request_id,
            "backend": r.backend,
            "obstacles": r.obstacles,
            "failure_context": r.failure_context,
            "stall": r.stall,
            "parse_status": r.parse_status,
            "attempts": r.attempts,
            "error_type": r.error_type,
            "refusal": r.refusal,
        }
        for r in rows
    ]
    (out_dir / "census.json").write_text(json.dumps(payload, indent=2))

    print(f"artifacts: {len(rows)}")
    print("\nrun,backend,obstacles,total,refusal,attempt1_nonjson,fc,solo,pair")
    for key, v in _tabulate(rows, lambda r: (r.run, r.backend, r.obstacles)):
        print(
            f"{key[0]},{key[1]},{key[2]},{v['total']},{v['refusal']},"
            f"{v['attempt1_nonjson']},{v['fc']},{v['solo']},{v['pair']}"
        )
    print("\nbackend,obstacles,total,refusal,attempt1_nonjson")
    for key, v in _tabulate(rows, lambda r: (r.backend, r.obstacles)):
        print(f"{key[0]},{key[1]},{v['total']},{v['refusal']},{v['attempt1_nonjson']}")
    print("\nbackend,failure_context,stall,total,refusal,attempt1_nonjson")
    for key, v in _tabulate(rows, lambda r: (r.backend, r.failure_context, r.stall)):
        print(
            f"{key[0]},{key[1]},{key[2]},{v['total']},{v['refusal']},{v['attempt1_nonjson']}"
        )

    # The re-ask recovery rate: of the attempt-1 non-JSON responses, how many
    # were still non-JSON on attempt 2 ("failed") rather than recovered
    # ("invalid"). This is the quantity the retry policy acts on.
    gpt_nonjson = [
        r for r in rows if r.backend == "gpt-4o" and r.parse_status in ("failed", "invalid")
    ]
    persisted = sum(1 for r in gpt_nonjson if r.parse_status == "failed")
    print(
        f"\ngpt-4o attempt-1 non-JSON: {len(gpt_nonjson)}/"
        f"{sum(1 for r in rows if r.backend == 'gpt-4o')}; "
        f"re-ask recovered {len(gpt_nonjson) - persisted}/{len(gpt_nonjson)}"
    )
    print("failure_context,persisted,attempt1_nonjson")
    for flag in (True, False):
        group = [r for r in gpt_nonjson if r.failure_context is flag]
        print(f"{flag},{sum(1 for r in group if r.parse_status == 'failed')},{len(group)}")

    gpt = [r for r in rows if r.backend == "gpt-4o"]
    fc_yes = [r for r in gpt if r.failure_context]
    fc_no = [r for r in gpt if not r.failure_context]
    a, b = sum(r.refusal for r in fc_yes), len(fc_yes) - sum(r.refusal for r in fc_yes)
    c, d = sum(r.refusal for r in fc_no), len(fc_no) - sum(r.refusal for r in fc_no)
    print(
        f"\npooled failure_context: {a}/{a + b} vs {c}/{c + d}, "
        f"fisher p={fisher_two_sided(a, b, c, d):.4g}"
    )

    a2 = sum(1 for r in fc_yes if r.parse_status in ("failed", "invalid"))
    c2 = sum(1 for r in fc_no if r.parse_status in ("failed", "invalid"))
    print(
        f"pooled failure_context on attempt-1 non-JSON: {a2}/{len(fc_yes)} vs "
        f"{c2}/{len(fc_no)}, "
        f"fisher p={fisher_two_sided(a2, len(fc_yes) - a2, c2, len(fc_no) - c2):.4g}"
    )

    # Artifacts cluster by run (and failure_context is itself a marker of
    # re-analysis position), so the pooled test above overstates independence.
    print("\nwithin-run stratification (gpt-4o runs with >=1 refusal)")
    print("run,fc_refusal,fc_total,nofc_refusal,nofc_total")
    for run in sorted({r.run for r in gpt if r.refusal}):
        run_rows = [r for r in gpt if r.run == run]
        yes = [r for r in run_rows if r.failure_context]
        no = [r for r in run_rows if not r.failure_context]
        print(
            f"{run},{sum(r.refusal for r in yes)},{len(yes)},"
            f"{sum(r.refusal for r in no)},{len(no)}"
        )


def make_grey_image(path: Path, size: tuple[int, int] = (640, 480)) -> Path:
    """Write a neutral mid-grey placeholder image and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((size[1], size[0], 3), 128, dtype=np.uint8)).save(path)
    return path


def make_overhead_image(
    path: Path,
    robots: list[dict],
    size: tuple[int, int] = (640, 480),
    metres_per_view: float = 8.0,
) -> Path:
    """Render a crude top-down view of recorded robot poses in a corridor.

    Args:
        path: Destination PNG path.
        robots: Recorded robot states with `x`, `y`, `theta` in world metres.
        size: Output image size as `(width, height)`.
        metres_per_view: World width the image spans, for the pixel scale.

    Returns:
        The written path.
    """
    width, height = size
    canvas = np.full((height, width, 3), 210, dtype=np.uint8)
    scale = width / metres_per_view
    aisle_half_px = int(0.9 * scale)
    canvas[height // 2 - aisle_half_px : height // 2 + aisle_half_px, :] = 235
    for index, robot in enumerate(robots):
        cx = int(width / 2 + robot["x"] * scale)
        cy = int(height / 2 - robot["y"] * scale)
        half = max(3, int(0.15 * scale))
        colour = (40, 90, 200) if index % 2 == 0 else (200, 120, 40)
        y0, y1 = max(0, cy - half), min(height, cy + half)
        x0, x1 = max(0, cx - half), min(width, cx + half)
        canvas[y0:y1, x0:x1] = colour
        hx = int(cx + math.cos(robot["theta"]) * half * 1.8)
        hy = int(cy - math.sin(robot["theta"]) * half * 1.8)
        if 0 <= hx < width and 0 <= hy < height:
            canvas[max(0, hy - 3) : hy + 3, max(0, hx - 3) : hx + 3] = (20, 20, 20)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(path)
    return path


def apply_word_group(prompt: str, group: str) -> str:
    """Return `prompt` with one wording group's phrases replaced by neutral synonyms."""
    out = prompt
    for needle, replacement in WORD_GROUPS[group].items():
        out = out.replace(needle, replacement)
    return out


def drop_failure_context(prompt: str) -> str:
    """Remove the `Previous attempt in this episode:` block from a rendered prompt.

    The block runs from its header to the blank line that follows it, which
    includes the trailing "if the congestion is no longer present" sentence;
    that blank line is dropped too so the surrounding spacing is unchanged.
    """
    kept: list[str] = []
    skipping = False
    for line in prompt.splitlines():
        if line.startswith(FAILURE_CONTEXT_HEADER):
            skipping = True
            continue
        if skipping:
            if line.strip():
                continue
            skipping = False
            continue
        kept.append(line)
    return "\n".join(kept)


def drop_think_instruction(prompt: str) -> str:
    """Remove the `<think>` scaffolding, leaving a bare JSON-only instruction."""
    marker = "Answer using the following format:"
    head = prompt.split(marker)[0].rstrip()
    return head + "\n\nReturn ONLY the final JSON object, with no surrounding text or markdown."


@dataclass
class Trial:
    """One configured replay cell: a prompt variant, image arm and sampling temperature."""

    label: str
    source_request_id: str
    arm: str
    system_prompt: str
    user_prompt: str
    image_path: Path
    temperature: float
    model_id: str
    known_robot_ids: list[str]
    n: int


def run_trials(
    trials: list[Trial],
    out_dir: Path,
    pace_sec: float,
    seed: int = 0,
) -> list[dict]:
    """Execute replay trials against the OpenAI backend, appending each call to JSONL.

    Args:
        trials: Configured cells; each is repeated `Trial.n` times.
        out_dir: Directory receiving `calls.jsonl` and `summary.csv`.
        pace_sec: Minimum delay between API calls, to respect the shared rate cap.
        seed: Unused by the API but recorded for reproducibility of trial order.

    Returns:
        One result record per call.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"
    rng = random.Random(seed)
    records: list[dict] = []
    by_model: dict[str, object] = {}

    plan = [(t, i) for t in trials for i in range(t.n)]
    rng.shuffle(plan)
    for index, (trial, repeat) in enumerate(plan):
        if trial.model_id not in by_model:
            by_model[trial.model_id] = build_backend(
                "openai", OpenAIBackendConfig(model_id=trial.model_id)
            )
        backend = by_model[trial.model_id]
        config = ReasonerConfig(
            backend_id="openai",
            temperature=trial.temperature,
            timeout_sec=120.0,
            max_attempts=1,
            allow_reask=False,
        )
        payload = PromptPayload(
            system_prompt=trial.system_prompt,
            user_prompt=trial.user_prompt,
            image_path=str(trial.image_path),
            known_robot_ids=trial.known_robot_ids,
        )
        record = {
            "label": trial.label,
            "arm": trial.arm,
            "source_request_id": trial.source_request_id,
            "model_id": trial.model_id,
            "temperature": trial.temperature,
            "repeat": repeat,
            "image": trial.image_path.name,
        }
        started = time.monotonic()
        try:
            response = invoke_backend(backend, payload, config)
            record["text"] = response.text
            record["refusal"] = is_refusal(response.text)
            record["token_usage"] = response.token_usage
            record["latency_ms"] = response.latency_ms
            try:
                parse_decision_text(response.text)
                record["parsed"] = True
            except (VLMOutputParseError, DecisionValidationError) as exc:
                record["parsed"] = False
                record["parse_error"] = type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - probe records transport failures as data
            message = f"{type(exc).__name__}: {exc}"
            record["error"] = message
            # OpenAI sometimes returns a policy block as HTTP 400 rather than as
            # assistant text; counting those as transport noise would hide them.
            record["policy_block"] = bool(
                re.search(r"content[_ ]policy|policy violation|content_filter", message, re.I)
            )
            record["refusal"] = False
            record["parsed"] = False
        records.append(record)
        with calls_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
        print(
            f"[{index + 1}/{len(plan)}] {trial.label} t={trial.temperature} "
            f"refusal={record.get('refusal')} parsed={record.get('parsed')}"
        )
        remaining = pace_sec - (time.monotonic() - started)
        if remaining > 0 and index + 1 < len(plan):
            time.sleep(remaining)
    return records


def write_summary(records: list[dict], out_dir: Path) -> None:
    """Aggregate call records into `summary.csv` keyed by label, model and temperature."""
    buckets: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for record in records:
        key = (record["label"], record["arm"], record["model_id"], record["temperature"])
        bucket = buckets[key]
        bucket["n"] += 1
        bucket["refusals"] += int(record.get("refusal", False))
        bucket["parsed"] += int(record.get("parsed", False))
        bucket["errors"] += int("error" in record)
        bucket["policy_blocks"] += int(record.get("policy_block", False))
        usage = record.get("token_usage") or {}
        bucket["prompt_tokens"] += usage.get("prompt_tokens", 0)
        bucket["completion_tokens"] += usage.get("completion_tokens", 0)
    lines = [
        "label,arm,model_id,temperature,n,refusals,refusal_rate,parsed,errors,"
        "policy_blocks,prompt_tokens,completion_tokens"
    ]
    for key in sorted(buckets, key=str):
        v = buckets[key]
        rate = v["refusals"] / v["n"] if v["n"] else 0.0
        lines.append(
            f"{key[0]},{key[1]},{key[2]},{key[3]},{int(v['n'])},{int(v['refusals'])},"
            f"{rate:.3f},{int(v['parsed'])},{int(v['errors'])},{int(v['policy_blocks'])},"
            f"{int(v['prompt_tokens'])},{int(v['completion_tokens'])}"
        )
    (out_dir / "summary.csv").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def _artifact_scene_robots(path: Path) -> list[dict]:
    return (json.loads(path.read_text()).get("scene") or {}).get("robots") or []


def build_replay_trials(
    rows: list[ArtifactRow],
    refusal_ids: list[str],
    control_ids: list[str],
    ablation_id: str,
    out_dir: Path,
    n: int,
) -> list[Trial]:
    """Assemble the replay and ablation trial list from stored prompts.

    Args:
        rows: Census rows for every artifact.
        refusal_ids: Request-id prefixes of the refusing analyses to replay.
        control_ids: Request-id prefixes of matched non-refusing analyses.
        ablation_id: Request-id prefix of the refusing prompt used for ablations.
        out_dir: Directory receiving the rendered prompt copies and images.
        n: Repeats per cell.

    Returns:
        The configured trials.
    """
    by_prefix = {r.request_id[:8]: r for r in rows}
    prompt_dir = out_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    grey = make_grey_image(out_dir / "images" / "neutral_grey.png")

    trials: list[Trial] = []
    for prefix in refusal_ids + control_ids:
        row = by_prefix[prefix]
        kind = "refusal" if prefix in refusal_ids else "control"
        (prompt_dir / f"{kind}_{prefix}.txt").write_text(row.user_prompt)
        known = re.findall(r'"(robot_\d+)"', row.user_prompt) or ["robot_1", "robot_2"]
        overhead = make_overhead_image(
            out_dir / "images" / f"overhead_{prefix}.png", _artifact_scene_robots(row.path)
        )
        reask_prompt = row.user_prompt + REASK_SUFFIX.format(
            error_message="VLM output contains no JSON object."
        )
        # The stored `raw_text` is attempt 2's answer, so the string that was
        # actually refused came from the re-ask prompt, not the attempt-1 prompt
        # the artifact stores; the re-ask arm is what separates the two.
        cells: list[tuple[str, str, Path, float]] = [
            ("overhead", row.user_prompt, overhead, 0.0),
            ("overhead", row.user_prompt, overhead, 0.6),
            ("reask", reask_prompt, overhead, 0.0),
        ]
        if kind == "refusal":
            cells += [
                ("grey", row.user_prompt, grey, 0.0),
                ("reask", reask_prompt, overhead, 0.6),
            ]
        for arm, text, image, temperature in cells:
            trials.append(
                Trial(
                    label=f"{kind}_{prefix}",
                    source_request_id=row.request_id,
                    arm=arm,
                    system_prompt=row.system_prompt,
                    user_prompt=text,
                    image_path=image,
                    temperature=temperature,
                    model_id="gpt-4o",
                    known_robot_ids=sorted(set(known)),
                    n=n,
                )
            )

    base = by_prefix[ablation_id]
    known = sorted(set(re.findall(r'"(robot_\d+)"', base.user_prompt))) or ["robot_1", "robot_2"]
    overhead = out_dir / "images" / f"overhead_{ablation_id}.png"
    variants: list[tuple[str, str, str]] = [
        ("abl_no_failure_context", drop_failure_context(base.user_prompt), "gpt-4o"),
        ("abl_no_think", drop_think_instruction(base.user_prompt), "gpt-4o"),
        ("abl_mini", base.user_prompt, "gpt-4o-mini"),
    ]
    variants += [
        (f"abl_words_{group}", apply_word_group(base.user_prompt, group), "gpt-4o")
        for group in WORD_GROUPS
    ]
    for label, text, model_id in variants:
        (prompt_dir / f"{label}.txt").write_text(text)
        trials.append(
            Trial(
                label=label,
                source_request_id=base.request_id,
                arm="overhead",
                system_prompt=base.system_prompt,
                user_prompt=text,
                image_path=overhead,
                temperature=0.0,
                model_id=model_id,
                known_robot_ids=known,
                n=n,
            )
        )
    return trials


def main() -> None:
    """Parse arguments and dispatch to the census or replay subcommand."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("census", help="tabulate refusals across stored decision artifacts")
    replay = sub.add_parser("replay", help="re-send stored prompts through the OpenAI backend")
    replay.add_argument("--refusals", default="a35f1ff9,2ddffe4c,ba3b2f47")
    replay.add_argument("--controls", default="9f257ee1,099e3c33,1d28a81a")
    replay.add_argument("--ablation-prompt", default="2ddffe4c")
    replay.add_argument("--n", type=int, default=8)
    replay.add_argument("--pace-sec", type=float, default=5.0)
    replay.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = collect_artifacts()
    if args.command == "census":
        write_census(rows, OUT_DIR)
        return

    trials = build_replay_trials(
        rows,
        args.refusals.split(","),
        args.controls.split(","),
        args.ablation_prompt,
        OUT_DIR,
        args.n,
    )
    total = sum(t.n for t in trials)
    print(f"{len(trials)} cells, {total} calls, ~{total * args.pace_sec / 60:.1f} min")
    if args.dry_run:
        for t in trials:
            print(f"  {t.label} arm={t.arm} model={t.model_id} t={t.temperature} n={t.n}")
        return
    write_summary(run_trials(trials, OUT_DIR, args.pace_sec), OUT_DIR)


if __name__ == "__main__":
    main()
