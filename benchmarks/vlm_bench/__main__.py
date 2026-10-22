"""CLI: `python -m benchmarks.vlm_bench build-items|score|replay ...` (spec v4_vlm_bench)."""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

from benchmarks.s1_scoring.bundle_io import NotAnEpisodeError
from benchmarks.vlm_bench.items import build_bundle_items, load_mc_references, write_items
from benchmarks.vlm_bench.run import load, replay_items, run_config, score_items, write_run


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m benchmarks.vlm_bench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-items", help="bundles -> items JSONL")
    build.add_argument("bundles", nargs="+", type=Path)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--mc", nargs="*", type=Path, default=None,
                       help="mc_seeds_*.jsonl files; default: those beside each bundle")
    score = sub.add_parser("score", help="score recorded or classical answers (no API calls)")
    score.add_argument("--mode", choices=("recorded", "classical"), required=True)
    score.add_argument("--items", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    score.add_argument("--summary", type=Path, default=None)
    score.add_argument("--no-oracle", action="store_true")
    replay = sub.add_parser("replay", help="re-ask a backend through the response cache")
    replay.add_argument("--backend", required=True)
    replay.add_argument("--prompt-variant", default="baseline")
    replay.add_argument("--items", type=Path, required=True)
    replay.add_argument("--out", type=Path, required=True)
    replay.add_argument("--summary", type=Path, default=None)
    replay.add_argument("--cache-dir", type=Path, default=Path("data/bench/cache"))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments (None reads `sys.argv`).

    Returns:
        The exit code.
    """
    args = _parser().parse_args(argv)
    if args.cmd == "build-items":
        mc_files = args.mc
        if mc_files is None:
            mc_files = sorted({Path(p) for b in args.bundles
                               for p in glob.glob(str(b.parent / "mc_seeds_*.jsonl"))})
        mc = load_mc_references(mc_files)
        items = []
        for bundle in args.bundles:
            try:
                built = build_bundle_items(bundle, mc)
            except NotAnEpisodeError as exc:
                print(f"skip {bundle}: {exc}")
                continue
            print(f"{bundle.name}: {len(built)} items")
            items.extend(built)
        write_items(items, args.out)
        print(f"wrote {len(items)} items -> {args.out}")
        return 0
    items = load(args.items)
    if args.cmd == "score":
        scores = score_items(items, args.mode, oracle=not args.no_oracle)
        config = run_config(args.mode, args.items, items)
    else:
        scores, info = replay_items(items, args.backend, args.prompt_variant, args.cache_dir)
        config = run_config(f"replay:{args.prompt_variant}", args.items, items, info)
    write_run(scores, args.out, args.summary, config, items)
    print(f"scored {len(scores)} items -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
