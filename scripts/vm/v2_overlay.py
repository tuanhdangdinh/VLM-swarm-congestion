#!/usr/bin/env python3
"""Apply one v2-final-wave scene's config overlay (VM helper).

Every scene below needs hand-set M5/M3 settings per run, by this project's
convention (orchestrator.yaml's own goal-table header): no scenario-keyed
table exists, only the one `initial_tasks:` block and the one
`scenario_geometry:` block, hand-edited per run. This script makes those
edits on the PRISTINE files and nothing else:

- `loop_*` (prereg-v2 (b) loop-detour family and its probes):
  `initial_tasks` (robot_1 -> (2.3, 0.0); the tracked probe adds robot_2)
  and `scenario_geometry.reroute_waypoints` (the far-aisle detour M3
  grounds a `reroute` to), inserted as one line after `  passer_margin_m:`.
- `convoy_slip` (B3 first-to-slip, goal-table row "convoy_counterflow_slip
  -> identical M5 settings to convoy_counterflow"): the four-robot
  `initial_tasks`, `scenario_geometry.corridor.half_length_m: 0.5`, and
  `config/rag.yaml` `grounding.mode: legacy`.
- `apparatus_annotation` / `apparatus_votes` (prompt-apparatus VM smoke,
  2026-10-04, `docs/reports/2026-10-04-visual-apparatus.md`): the
  `_bshort` head-on `initial_tasks` (robot_1 -> (2.6, 0), robot_2 ->
  (-1.5, 0)), `keep_debug_frames: true`, and the apparatus flags appended
  at the end of the file -- annotation: plan channel (prompt v3) + grid,
  trails and zoom-tile sentences, plus `keep_raw_frames: true`; votes:
  `prompt_permutation_votes: 3` only. `config/rag.yaml` untouched.
- `battery_v2_head_on` (battery-v2 frame harvest, 2026-10-04,
  `docs/reports/2026-10-04-battery-v2-results.md`): the same `_bshort`
  head-on `initial_tasks`, `keep_debug_frames: true` and the plan channel
  (so the annotation smoke's known-good `*_plan_once` yield mock resolves
  the jam), but none of the prompt-apparatus flags: the trails-off and
  trails-on harvest runs share this one M5 overlay, and only M1's
  `annotation.yaml` differs between them. `config/rag.yaml` untouched.

Restoring is NOT this script's job: the driver copies the verbatim backups
back (plain copy, fresh mtime) and verifies the pristine md5s.

Usage:
    v2_overlay.py --orchestrator <orchestrator.yaml> --rag <rag.yaml> <scene>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LOOP_ROBOT_1 = "  robot_1: { task: cross_narrow_aisle, goal: [2.3, 0.0] }"
SCENE_TASKS: dict[str, list[str]] = {
    "loop_permanent": [LOOP_ROBOT_1],
    "loop_transient": [LOOP_ROBOT_1],
    "loop_lethal": [LOOP_ROBOT_1],
    "loop_tracked": [
        LOOP_ROBOT_1,
        "  robot_2: { task: cross_narrow_aisle, goal: [2.0, -0.45], start_delay_sec: 200.0 }",
    ],
    "convoy_slip": [
        "  robot_1: { task: cross_narrow_aisle, goal: [2.45, -0.36] }",
        "  robot_2: { task: cross_narrow_aisle, goal: [-2.0, 0.0] }",
        "  robot_3: { task: cross_narrow_aisle, goal: [2.45, 0.36], start_delay_sec: 120 }",
        "  robot_4: { task: cross_narrow_aisle, goal: [1.85, 0.0], start_delay_sec: 120 }",
    ],
    "apparatus_annotation": [
        "  robot_1: { task: cross_narrow_aisle, goal: [2.6, 0.0] }",
        "  robot_2: { task: cross_narrow_aisle, goal: [-1.5, 0.0] }",
    ],
    "apparatus_votes": [
        "  robot_1: { task: cross_narrow_aisle, goal: [2.6, 0.0] }",
        "  robot_2: { task: cross_narrow_aisle, goal: [-1.5, 0.0] }",
    ],
    "battery_v2_head_on": [
        "  robot_1: { task: cross_narrow_aisle, goal: [2.6, 0.0] }",
        "  robot_2: { task: cross_narrow_aisle, goal: [-1.5, 0.0] }",
    ],
}
# Prompt-apparatus smoke: `^key: value$` replacements, then lines appended at
# the end (the keys the pristine file does not carry).
APPARATUS_REPLACE: dict[str, dict[str, str]] = {
    "apparatus_annotation": {"keep_debug_frames": "true", "keep_raw_frames": "true"},
    "apparatus_votes": {"keep_debug_frames": "true"},
    "battery_v2_head_on": {"keep_debug_frames": "true"},
}
APPARATUS_APPEND: dict[str, list[str]] = {
    "apparatus_annotation": [
        "plan_channel_enabled: true",
        "prompt_metric_grid: true",
        "prompt_motion_trails: true",
        "prompt_zoom_tile: true",
    ],
    "apparatus_votes": ["prompt_permutation_votes: 3"],
    "battery_v2_head_on": ["plan_channel_enabled: true"],
}
WAYPOINTS_LINE = "  reroute_waypoints: [[0.3, 1.2], [1.8, 1.2]]"
TASKS_RE = re.compile(r"^initial_tasks:\n(?:  robot_\d+:.*\n)+", re.MULTILINE)
MARGIN_RE = re.compile(r"^(scenario_geometry:\n(?:  .*\n)*?  passer_margin_m:.*\n)", re.MULTILINE)
CORRIDOR_RE = re.compile(r"^(  corridor: \{.*half_length_m: )1\.0(,.*\})$", re.MULTILINE)
RAG_MODE_RE = re.compile(r"^(grounding:\n  mode: )derived$", re.MULTILINE)


def _sub_once(pattern: re.Pattern[str], repl, text: str, what: str) -> str:
    if len(pattern.findall(text)) != 1:
        raise ValueError(f"expected exactly one {what}")
    return pattern.sub(repl, text, count=1)


def overlay_orchestrator(text: str, scene: str) -> str:
    """Return orchestrator.yaml `text` with the scene's settings applied.

    Args:
        text: Pristine orchestrator.yaml contents.
        scene: One of `SCENE_TASKS`.

    Returns:
        The overlaid contents.

    Raises:
        ValueError: If the scene is unknown or the file shape is unexpected
            (including an already-overlaid file).
    """
    if scene not in SCENE_TASKS:
        raise ValueError(f"unknown scene {scene!r}; known: {sorted(SCENE_TASKS)}")
    if re.search(r"^  reroute_waypoints:", text, re.MULTILINE):
        raise ValueError("reroute_waypoints already present: restore the pristine file first")
    tasks = "initial_tasks:\n" + "\n".join(SCENE_TASKS[scene]) + "\n"
    text = _sub_once(TASKS_RE, lambda _m: tasks, text, "initial_tasks: block")
    if scene in APPARATUS_REPLACE:
        for key, value in APPARATUS_REPLACE[scene].items():
            text = _sub_once(
                re.compile(rf"^{key}: .*$", re.MULTILINE),
                lambda _m, k=key, v=value: f"{k}: {v}", text, f"{key}: line",
            )
        appended: list[str] = []
        for line in APPARATUS_APPEND[scene]:
            key = line.split(":")[0]
            pattern = re.compile(rf"^{key}: .*$", re.MULTILINE)
            found = pattern.findall(text)
            if any(value.strip() == line for value in found):
                raise ValueError(f"{line!r} already set: restore the pristine file first")
            if found:
                # A newer pristine file already carries the key (default off).
                text = _sub_once(pattern, lambda _m, new=line: new, text, f"{key}: line")
            else:
                appended.append(line)
        if not appended:
            return text
        return text.rstrip("\n") + "\n" + "\n".join(appended) + "\n"
    if scene.startswith("loop_"):
        return _sub_once(
            MARGIN_RE, lambda m: m.group(1) + WAYPOINTS_LINE + "\n", text,
            "scenario_geometry block with passer_margin_m",
        )
    return _sub_once(
        CORRIDOR_RE, lambda m: m.group(1) + "0.5" + m.group(2), text,
        "scenario_geometry corridor line with half_length_m: 1.0",
    )


def overlay_rag(text: str, scene: str) -> str | None:
    """Return config/rag.yaml `text` overlaid, or None when the scene keeps it.

    Args:
        text: Pristine rag.yaml contents.
        scene: One of `SCENE_TASKS`.

    Returns:
        The overlaid contents, or None (the loop scenes run the shipped
        derived mode, whose reroute reuses the legacy template).

    Raises:
        ValueError: If the file shape is unexpected.
    """
    if scene != "convoy_slip":
        return None
    return _sub_once(RAG_MODE_RE, lambda m: m.group(1) + "legacy", text, "grounding.mode: derived")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--orchestrator", type=Path, required=True)
    parser.add_argument("--rag", type=Path, required=True)
    parser.add_argument("scene", choices=sorted(SCENE_TASKS))
    args = parser.parse_args()
    try:
        orch = overlay_orchestrator(args.orchestrator.read_text(encoding="utf-8"), args.scene)
        rag = overlay_rag(args.rag.read_text(encoding="utf-8"), args.scene)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.orchestrator.write_text(orch, encoding="utf-8")
    if rag is not None:
        args.rag.write_text(rag, encoding="utf-8")
    print(f"overlaid for scene {args.scene} (rag.yaml {'changed' if rag else 'untouched'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
