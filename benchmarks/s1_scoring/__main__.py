"""CLI: score S1 bundles per prereg-v3 A33 and write JSON lines.

Usage:
    python -m benchmarks.s1_scoring BUNDLE... --out results.jsonl
        [--free-flow TABLE.json] [--scene-key mapd_5_s1b] [--grid-s 1.0]
        [--merge-gap-s 2.0] [--min-duration-s 0.0] [--pre-s 0.0] [--post-s 5.0]
        [--min-overlap 1] [--accepted-type deadlock ...]
        [--incremental-fraction-bound 0.5]
        [--arm-a BUNDLE... --arm-b BUNDLE... [--reps 10000] [--boot-seed 20261021]]

One line per positional bundle (`kind: episode`, or `kind: not_an_episode`
with the reason for a bundle A33(0) refuses), then one `kind: arm_delta`
line when both arms are given (arm bundles must all be episodes). Every
PROPOSAL flag defaults to its A33 value.
Arms are labelled by the caller, never inferred from the backend.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmarks.s1_scoring.arm_delta import DEFAULT_BOOT_SEED, DEFAULT_REPS, arm_delta
from benchmarks.s1_scoring.bundle_io import NotAnEpisodeError, read_bundle
from benchmarks.s1_scoring.conflicts import ConflictParams
from benchmarks.s1_scoring.delay import DEFAULT_SCENE_KEY, load_segment_table
from benchmarks.s1_scoring.episode import score_records
from benchmarks.s1_scoring.throughput import DEFAULT_GRID_S


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        The parser.
    """
    defaults = ConflictParams()
    p = argparse.ArgumentParser(prog="python -m benchmarks.s1_scoring", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bundles", nargs="*", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--free-flow", type=Path, default=None)
    p.add_argument("--scene-key", default=DEFAULT_SCENE_KEY)
    p.add_argument("--grid-s", type=float, default=DEFAULT_GRID_S)
    p.add_argument("--merge-gap-s", type=float, default=defaults.merge_gap_s)
    p.add_argument("--min-duration-s", type=float, default=defaults.min_duration_s)
    p.add_argument("--pre-s", type=float, default=defaults.pre_s)
    p.add_argument("--post-s", type=float, default=defaults.post_s)
    p.add_argument("--min-overlap", type=int, default=defaults.min_overlap)
    p.add_argument("--accepted-type", action="append", default=None)
    p.add_argument("--incremental-fraction-bound", type=float,
                   default=defaults.incremental_fraction_bound)
    p.add_argument("--arm-a", nargs="+", type=Path, default=[])
    p.add_argument("--arm-b", nargs="+", type=Path, default=[])
    p.add_argument("--reps", type=int, default=DEFAULT_REPS)
    p.add_argument("--boot-seed", type=int, default=DEFAULT_BOOT_SEED)
    return p


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (sys.argv[1:] when None).

    Returns:
        The exit code: 0, or 2 when only one arm is given or nothing to score.
    """
    args = build_parser().parse_args(argv)
    if bool(args.arm_a) != bool(args.arm_b):
        print("--arm-a and --arm-b must be given together", file=sys.stderr)
        return 2
    if not args.bundles and not args.arm_a:
        print("no bundles given", file=sys.stderr)
        return 2
    params = ConflictParams(
        merge_gap_s=args.merge_gap_s, min_duration_s=args.min_duration_s, pre_s=args.pre_s,
        post_s=args.post_s, min_overlap=args.min_overlap,
        accepted_types=tuple(args.accepted_type) if args.accepted_type else ("deadlock",),
        incremental_fraction_bound=args.incremental_fraction_bound,
    )
    table = load_segment_table(args.free_flow) if args.free_flow else None
    lines = []
    for bundle in args.bundles:
        try:
            records = read_bundle(bundle)
        except NotAnEpisodeError as exc:
            lines.append({"kind": "not_an_episode", "bundle": bundle.name, "reason": str(exc)})
            continue
        scores = score_records(records, table=table, scene_key=args.scene_key,
                               grid_s=args.grid_s, params=params)
        lines.append({"kind": "episode", **scores.model_dump(mode="json")})
    if args.arm_a:
        result = arm_delta(
            [read_bundle(b) for b in args.arm_a], [read_bundle(b) for b in args.arm_b],
            table=table, scene_key=args.scene_key, params=params, reps=args.reps,
            boot_seed=args.boot_seed,
        )
        lines.append({"kind": "arm_delta", **result.model_dump(mode="json")})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
