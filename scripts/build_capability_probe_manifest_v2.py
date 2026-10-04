#!/usr/bin/env python3
"""Scan run logs and freeze the battery-v2 manifest (predictive/temporal probes).

Registered 2026-10-04 (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`,
"Battery v2 -- predictive/temporal probes"); results and the full rule list
in `docs/reports/2026-10-04-battery-v2-results.md`. Scans every episode under
`--logs-root` that holds Isaac GT plus decision frames and/or battery-v2
harvest snapshots, gates each frame (`episode_v2.gate_frame`), derives every
`motion_direction` / `conflict_prediction` / `temporal_order` question the
frame supports (`episode_v2.derive`, answers from GT only), and selects:

- **main**: trails-off frames only, near-duplicate scenes removed, a seeded
  balanced sample (`selection.balanced_sample`) of up to `--target-main` per
  type, at most `--max-per-scene` per episode;
- **trails_pair**: the same question on a trails-off and a trails-on frame
  of the same scenario whose GT configurations match (max per-robot
  displacement under `scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M`, same
  derived answer; temporal_order also within `PAIR_EVENT_LAG_TOLERANCE_SEC`
  of time-since-later-event). Pairing is by configuration, not by stamp:
  same-seed episodes drift 1-2.5 s apart. Both members share one lettering
  seed (derived from the pair id), so the only difference is the frame.

A type with too few eligible candidates is reported SHORT, never padded.
No backend calls; pure log scanning and GT arithmetic.

Usage:
    python scripts/build_capability_probe_manifest_v2.py \\
        --logs-root /path/to/data/logs/vm_runs \\
        --out reasoning/vlm/capability_probes/manifest_v2.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PERCEPTION_SRC = REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"
if str(PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(PERCEPTION_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from reasoning.vlm.capability_probes import dynamics as dyn  # noqa: E402, I001
from reasoning.vlm.capability_probes import episode_v2 as ep  # noqa: E402
from reasoning.vlm.capability_probes import scanning  # noqa: E402
from reasoning.vlm.capability_probes.manifest_io import sha256_file  # noqa: E402
from reasoning.vlm.capability_probes.models_v2 import (  # noqa: E402
    ProbeItemV2,
    ProbeManifestV2,
)
from reasoning.vlm.capability_probes.selection import balanced_sample  # noqa: E402

PROBE_TYPES_V2 = ("motion_direction", "conflict_prediction", "temporal_order")
PAIR_EVENT_LAG_TOLERANCE_SEC = dyn.PAIR_EVENT_LAG_TOLERANCE_SEC


@dataclass
class Candidate:
    """One derived question on one gated frame."""

    episode: ep.EpisodeData
    ctx: ep.FrameContext
    derived: ep.Derived

    @property
    def run_id(self) -> str:
        return self.episode.run_id

    @property
    def condition(self) -> str:
        return self.ctx.frame.condition

    @property
    def gt_positions(self) -> dict[str, dict]:
        return {rid: {"x": r["x"], "y": r["y"]} for rid, r in self.ctx.gt_robots.items()}


def registered_constants() -> dict[str, float]:
    """Return the `dynamics` constants this build ran under (for the manifest)."""
    names = [
        "DYNAMIC_GT_MATCH_TOLERANCE_SEC",
        "MOTION_WINDOW_SEC",
        "MOVING_MIN_SPEED_MPS",
        "STATIONARY_MAX_SPEED_MPS",
        "TOWARD_MAX_ANGLE_DEG",
        "NOT_TOWARD_MIN_ANGLE_DEG",
        "REVERSING_MIN_ANGLE_DEG",
        "CONFLICT_THRESHOLD_M",
        "CONFLICT_HORIZON_SEC",
        "CONFLICT_YES_MAX_M",
        "CONFLICT_NO_MIN_M",
        "CONFLICT_MIN_CURRENT_DISTANCE_M",
        "TEMPORAL_MIN_GAP_SEC",
        "GOAL_ARRIVAL_TOLERANCE_M",
        "GOAL_HOLD_TOLERANCE_M",
        "STOP_PRECEDING_MOTION_SEC",
        "STANDOFF_MAX_DISTANCE_M",
        "COMMAND_END_SLACK_SEC",
        "ONSET_HALF_WINDOW_SEC",
        "ONSET_SPEED_MPS",
        "PAIR_EVENT_LAG_TOLERANCE_SEC",
    ]
    constants = {name: float(getattr(dyn, name)) for name in names}
    constants["TEMPORAL_WINDOW_LO_SEC"] = float(dyn.TEMPORAL_WINDOW_SEC[0])
    constants["TEMPORAL_WINDOW_HI_SEC"] = float(dyn.TEMPORAL_WINDOW_SEC[1])
    constants["NEAR_DUPLICATE_MAX_DISPLACEMENT_M"] = scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M
    return constants


def scan_candidates(
    logs_root: Path, homography, image_size: tuple[int, int], drops: Counter
) -> list[Candidate]:
    """Gate every frame under `logs_root` and derive every v2 question it supports."""
    candidates: list[Candidate] = []
    for episode_dir in ep.discover_episodes(logs_root):
        episode = ep.load_episode(episode_dir, logs_root)
        if episode is None:
            continue
        frames = list(ep.iter_decision_frames(episode_dir)) + list(
            ep.iter_snapshot_frames(episode_dir)
        )
        for frame in frames:
            ctx, reason = ep.gate_frame(episode, frame, homography, image_size)
            if ctx is None:
                drops[f"frame:{reason}"] += 1
                continue
            for probe_type in PROBE_TYPES_V2:
                for key in ep.candidate_keys(ctx, probe_type):
                    result = ep.derive(episode, ctx, probe_type, key)
                    if isinstance(result, str):
                        drops[f"{probe_type}:{result}"] += 1
                        continue
                    candidates.append(Candidate(episode, ctx, result))
    return candidates


def dedupe(candidates: list[Candidate]) -> list[Candidate]:
    """Keep the first of each (question key, GT configuration) near-duplicate group."""
    return scanning.deduplicate_by_distance(
        candidates,
        reference_robot_id=lambda c: f"{c.derived.probe_type}/{c.derived.question_key}",
        gt_robots=lambda c: c.gt_positions,
    )


def balance_key(candidate: Candidate) -> str:
    """Balance axis per type: the answer for yes/no, the answer's slot otherwise.

    Balancing temporal_order on the answer's position in the sorted option
    list keeps "the lower id" from being right most of the time; for
    motion_direction the correct robot id itself is balanced, so no one
    robot (robot_1 especially, the project's known id prior) dominates.
    """
    d = candidate.derived
    if d.probe_type == "temporal_order":
        return str(d.options.index(d.correct_answer))
    return d.correct_answer


def strictly_balanced(chosen: list, answer=lambda c: c.derived.correct_answer) -> list:
    """Trim a yes/no selection to equal counts per answer (registered: balanced).

    `balanced_sample` alternates answer groups but keeps filling from the
    larger one once the smaller is exhausted; conflict_prediction is
    registered as balanced yes/no, so the surplus of the larger group is cut
    from the END of the selection order (the last-drawn items go first).
    """
    counts: Counter = Counter(answer(c) for c in chosen)
    if len(counts) < 2:
        return []
    keep = min(counts.values())
    taken: Counter = Counter()
    out = []
    for c in chosen:
        if taken[answer(c)] < keep:
            out.append(c)
            taken[answer(c)] += 1
    return out


def _same_question(a: Candidate, b: Candidate) -> bool:
    return (
        a.derived.probe_type == b.derived.probe_type
        and a.derived.question_key == b.derived.question_key
        and a.derived.options == b.derived.options
        and a.derived.correct_answer == b.derived.correct_answer
    )


def match_pairs(candidates: list[Candidate]) -> list[tuple[Candidate, Candidate]]:
    """Match each trails-off candidate to its closest-configuration trails-on twin.

    Only across episodes of the same scenario; each trails-on candidate is
    used at most once (greedy by smallest displacement).
    """
    off = [c for c in candidates if c.condition == "trails_off"]
    on = [c for c in candidates if c.condition == "trails_on"]
    proposals = []
    for c_off in off:
        for c_on in on:
            if c_on.episode.scenario != c_off.episode.scenario or c_on.run_id == c_off.run_id:
                continue
            if not _same_question(c_off, c_on):
                continue
            disp = scanning.max_displacement_m(c_off.gt_positions, c_on.gt_positions)
            if disp is None or disp >= scanning.NEAR_DUPLICATE_MAX_DISPLACEMENT_M:
                continue
            if c_off.derived.probe_type == "temporal_order":
                lag = abs(
                    c_off.derived.derivation["since_later_event_sec"]
                    - c_on.derived.derivation["since_later_event_sec"]
                )
                if lag > PAIR_EVENT_LAG_TOLERANCE_SEC:
                    continue
            proposals.append((disp, id(c_off), id(c_on), c_off, c_on))
    proposals.sort(key=lambda p: (p[0], p[3].run_id, p[3].ctx.frame.ref, p[4].ctx.frame.ref))
    used_off, used_on, pairs = set(), set(), []
    for _, off_id, on_id, c_off, c_on in proposals:
        if off_id in used_off or on_id in used_on:
            continue
        used_off.add(off_id)
        used_on.add(on_id)
        pairs.append((c_off, c_on))
    return pairs


def _item_seed(manifest_seed: int, key: str) -> int:
    digest = hashlib.sha256(f"{manifest_seed}:item:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def make_item(
    candidate: Candidate,
    item_id: str,
    seed: int,
    subset: str,
    pair_id: str | None,
    logs_root: Path,
) -> ProbeItemV2:
    """Freeze one candidate as a manifest item."""
    frame, d = candidate.ctx.frame, candidate.derived
    return ProbeItemV2(
        item_id=item_id,
        probe_type=d.probe_type,
        subset=subset,
        pair_id=pair_id,
        frame_condition=frame.condition,
        run_id=candidate.run_id,
        scenario=candidate.episode.scenario,
        frame_source=frame.source,
        frame_ref=frame.ref,
        frame_relpath=str(frame.path.relative_to(logs_root)),
        frame_sha256=sha256_file(frame.path),
        image_width=candidate.ctx.width,
        image_height=candidate.ctx.height,
        sim_time_sec=frame.stamp,
        gt_sim_time_sec=candidate.ctx.gt_row["sim_time_sec"],
        question_key=d.question_key,
        reference_robot_id=d.reference_robot_id,
        question=d.question,
        options=d.options,
        correct_answer=d.correct_answer,
        seed=seed,
        m1_gt_max_disagreement_m=candidate.ctx.disagreement_m,
        derivation=d.derivation,
    )


def build_manifest(
    logs_root: Path,
    calibration_path: Path,
    seed: int,
    target_main: int,
    target_pairs: int,
    max_per_scene: int,
) -> tuple[ProbeManifestV2, Counter, dict]:
    """Scan, select and freeze the battery-v2 item set.

    Returns:
        `(manifest, drop_counts, pool_sizes)`.
    """
    from swarm_perception.calibration import load_calibration

    calibration = load_calibration(str(calibration_path))
    drops: Counter = Counter()
    candidates = scan_candidates(logs_root, calibration.homography, calibration.image_size, drops)
    pools: dict[str, int] = {}
    items: list[ProbeItemV2] = []

    for probe_type in PROBE_TYPES_V2:
        of_type = [c for c in candidates if c.derived.probe_type == probe_type]
        main_pool = [c for c in of_type if c.condition == "trails_off"]
        deduped = dedupe(main_pool)
        drops[f"{probe_type}:duplicate_scene"] += len(main_pool) - len(deduped)
        pools[f"{probe_type}/main_eligible"] = len(deduped)
        chosen = balanced_sample(
            deduped,
            balance_key=balance_key,
            scene_key=lambda c: c.run_id,
            target=target_main,
            seed=seed,
            max_per_scene=max_per_scene,
        )
        if probe_type == "conflict_prediction":
            chosen = strictly_balanced(chosen)
        for index, candidate in enumerate(chosen):
            item_id = f"main_{probe_type}_{index:03d}"
            items.append(
                make_item(candidate, item_id, _item_seed(seed, item_id), "main", None, logs_root)
            )

        pairs = match_pairs(of_type)
        pairs_deduped = scanning.deduplicate_by_distance(
            pairs,
            reference_robot_id=lambda p: p[0].derived.question_key,
            gt_robots=lambda p: p[0].gt_positions,
        )
        pools[f"{probe_type}/pairs_eligible"] = len(pairs_deduped)
        chosen_pairs = balanced_sample(
            pairs_deduped,
            balance_key=lambda p: balance_key(p[0]),
            scene_key=lambda p: p[0].run_id,
            target=target_pairs,
            seed=seed,
            max_per_scene=target_pairs,
        )
        if probe_type == "conflict_prediction":
            chosen_pairs = strictly_balanced(
                chosen_pairs, answer=lambda p: p[0].derived.correct_answer
            )
        for index, (c_off, c_on) in enumerate(chosen_pairs):
            pair_id = f"pair_{probe_type}_{index:03d}"
            pair_seed = _item_seed(seed, pair_id)
            for suffix, candidate in (("off", c_off), ("on", c_on)):
                items.append(
                    make_item(
                        candidate,
                        f"{pair_id}_{suffix}",
                        pair_seed,
                        "trails_pair",
                        pair_id,
                        logs_root,
                    )
                )

    manifest = ProbeManifestV2(seed=seed, constants=registered_constants(), items=items)
    return manifest, drops, pools


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs-root", type=Path, required=True)
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / "ros2_ws" / "src" / "swarm_perception" / "config" / "calibration.yaml",
    )
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "reasoning/vlm/capability_probes/manifest_v2.json"
    )
    parser.add_argument("--seed", type=int, default=20261004)
    parser.add_argument("--target-main", type=int, default=20)
    parser.add_argument("--target-pairs", type=int, default=15)
    parser.add_argument("--max-per-scene", type=int, default=8)
    parser.add_argument("--report-json", type=Path, default=None)
    args = parser.parse_args()

    manifest, drops, pools = build_manifest(
        args.logs_root,
        args.calibration,
        args.seed,
        args.target_main,
        args.target_pairs,
        args.max_per_scene,
    )
    args.out.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    composition: Counter = Counter(
        (item.subset, item.probe_type, item.frame_condition) for item in manifest.items
    )
    print(f"wrote {args.out} ({len(manifest.items)} items, seed={args.seed})")
    for (subset, probe_type, condition), count in sorted(composition.items()):
        target = args.target_main if subset == "main" else args.target_pairs
        short = " SHORT" if count < target else ""
        print(f"  {subset}/{probe_type}/{condition}: {count}/{target}{short}")
    print("pool sizes:")
    for key, value in sorted(pools.items()):
        print(f"  {key}: {value}")
    print("dropped candidates:")
    for reason, count in sorted(drops.items()):
        print(f"  {reason}: {count}")
    if args.report_json is not None:
        args.report_json.write_text(
            json.dumps({"pools": pools, "drops": dict(sorted(drops.items()))}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
