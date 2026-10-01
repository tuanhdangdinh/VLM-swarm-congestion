#!/usr/bin/env python3
"""Replace orchestrator.yaml's `initial_tasks:` block in place, or restore it.

A scenario run that needs every tracked robot parked at specific poses (e.g.
the M1 y-extent probe, `m1_y_extent_probe.sh`) must rewrite `initial_tasks`
before launch, per this project's standing convention (orchestrator.yaml's
own header: "Set per scenario by hand like initial_tasks (goal table
above)" -- there is no scenario-keyed table, only this one block, hand-edited
per run). A bare `sed`/text edit risks drifting the surrounding comments or
leaving a partial block; this script finds the exact `initial_tasks:` line
and its contiguous `  robot_N: { ... }` lines with a regex and replaces (or
backs up / restores) only that span, so every other byte of the file --
every comment, every other key -- is untouched. `--restore` is a plain file
copy, so the restored file is byte-identical to the backup (md5-verifiable).

Usage:
    patch_initial_tasks.py <orchestrator.yaml> --backup <path>
    patch_initial_tasks.py <orchestrator.yaml> --set <block.txt>
    patch_initial_tasks.py <orchestrator.yaml> --restore <backup>
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

BLOCK_RE = re.compile(r"^initial_tasks:\n(?:  robot_\d+:.*\n)+", re.MULTILINE)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup", type=Path, help="save a verbatim copy here")
    group.add_argument(
        "--set",
        type=Path,
        help="file holding the replacement '  robot_N: { ... }' lines, "
        "one per line, already 2-space indented",
    )
    group.add_argument("--restore", type=Path, help="restore verbatim from a backup")
    args = parser.parse_args()

    if args.backup is not None:
        shutil.copy2(args.config, args.backup)
        print(f"backed up {args.config} -> {args.backup}")
        return

    if args.restore is not None:
        shutil.copy2(args.restore, args.config)
        print(f"restored {args.config} <- {args.restore}")
        return

    new_lines = args.set.read_text().splitlines()
    new_lines = [line for line in new_lines if line.strip()]
    if not new_lines:
        sys.exit("ERROR: --set file has no non-blank lines")
    for line in new_lines:
        if not re.match(r"^  robot_\d+: \{.*\}$", line):
            sys.exit(f"ERROR: malformed replacement line (want '  robot_N: {{ ... }}'): {line!r}")

    text = args.config.read_text()
    match = BLOCK_RE.search(text)
    if not match:
        sys.exit("ERROR: initial_tasks: block not found (unexpected file shape)")

    replacement = "initial_tasks:\n" + "\n".join(new_lines) + "\n"
    text = text[: match.start()] + replacement + text[match.end() :]
    args.config.write_text(text)
    print(f"patched initial_tasks in {args.config} ({len(new_lines)} robot lines)")


if __name__ == "__main__":
    main()
