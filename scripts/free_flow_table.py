#!/usr/bin/env python3
"""The per-cell free-flow baseline table: schema, loud loader and builder.

`delay_vs_free_flow` (prereg-v2 "Foundations round adopted (2026-10-05)",
`reports/Swarm congestion foundations.md` section 2) charges each robot its
actual travel time minus the time the same robot takes on the same cell when
it traverses ALONE. Free-flow speed is the fundamental diagram's zero-density
intercept (Greenshields 1935; Lighthill & Whitham 1955), so per-robot delay
against a single-robot baseline is exactly the flow-theoretic quantity, not
an analogy. This module owns the committed, frozen table those baselines
live in (suggested `config/free_flow/free_flow_v1.json`):

    {
      "schema_version": 1,
      "table_id": "free_flow_v1",
      "origin_rule": "own_departure",
      "arrival_rule": "gt_within_0.35_stay_0.5",
      "scenes": {
        "<scenario name>": {
          "<robot id>": {"time_sec": 31.2, "run_id": "...", "gt_hash": "<sha256>",
                         "mechanism": "solo_in_time" | "solo_in_space", ...}
        }
      }
    }

Timing rules (fixed here, shared with the episode scorer so a baseline and
an episode are measured identically):

- origin (`own_departure`): the robot's OWN first ground-truth sample faster
  than 0.03 m/s (`t2b_forced_order.DEPARTURE_SPEED_MPS`), not the run's
  common t0 -- a held-back robot (T2b robot_3 55 s, B1 robot_3 80 s, B3
  robot_3/robot_4 120 s) would otherwise carry its scripted hold as fake delay;
- arrival (`gt_within_0.35_stay_0.5`): the T2b forced-order rule (within
  0.35 m of the goal, never farther than 0.5 m afterwards), on Isaac sim time.
  M5's ArrivalGate log lines are wall-clock stamped (~0.27 real-time factor),
  so they corroborate arrival only and never time it.

Mechanisms: `solo_in_time` (one run, robots released one at a time) and
`solo_in_space` (one run per robot, the others absent). The builder refuses a
solo-in-time traversal during which any other robot moved.

Subcommands:

- `derive --scene S --gt DIR --mechanism M [--robot R ...] [--decisions DIR]`:
  one harvest run's entries (and its zero-dispatch check), printed as JSON.
- `build --entries F ... --table-id ID --out F`: assemble derived entries into
  a validated table.
- `check --table F`: validate a table (the loud loader), print a summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.t2b_forced_order import (  # noqa: E402
    ARRIVAL_STAY_M,
    ARRIVAL_TOLERANCE_M,
    DEPARTURE_SPEED_MPS,
)

DEFAULT_TABLE_PATH = REPO_ROOT / "config" / "free_flow" / "free_flow_v1.json"
ORIGIN_RULE = "own_departure"
ARRIVAL_RULE = "gt_within_0.35_stay_0.5"
_ROBOT_ID_RE = re.compile(r"^robot_\d+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FreeFlowTableError(ValueError):
    """The free-flow table is missing, unreadable or fails its schema."""


class FreeFlowEntry(BaseModel):
    """One robot's free-flow traversal time on one cell."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    time_sec: float = Field(gt=0.0)
    run_id: str = Field(min_length=1)
    gt_hash: str
    mechanism: Literal["solo_in_time", "solo_in_space"]
    departure_sec: float | None = None
    arrival_sec: float | None = None
    min_clearance_m: float | None = None

    @field_validator("gt_hash")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if not _SHA256_RE.match(value):
            raise ValueError("gt_hash must be the lowercase sha256 hex of ground_truth.jsonl")
        return value

    @model_validator(mode="after")
    def _time_matches_endpoints(self) -> FreeFlowEntry:
        if self.departure_sec is not None and self.arrival_sec is not None:
            span = self.arrival_sec - self.departure_sec
            if abs(span - self.time_sec) > 0.051:
                raise ValueError(
                    f"time_sec {self.time_sec} != arrival_sec - departure_sec = {span:.3f}"
                )
        return self


class FreeFlowTable(BaseModel):
    """The committed, frozen per-cell free-flow table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1]
    table_id: str = Field(min_length=1)
    origin_rule: Literal["own_departure"]
    arrival_rule: Literal["gt_within_0.35_stay_0.5"]
    scenes: dict[str, dict[str, FreeFlowEntry]]

    @field_validator("scenes")
    @classmethod
    def _non_empty(cls, scenes: dict[str, dict[str, FreeFlowEntry]]):
        if not scenes:
            raise ValueError("a free-flow table must hold at least one scene")
        for scene, robots in scenes.items():
            if not robots:
                raise ValueError(f"scene {scene!r} has no robots")
            bad = [rid for rid in robots if not _ROBOT_ID_RE.match(rid)]
            if bad:
                raise ValueError(f"scene {scene!r}: malformed robot ids {bad}")
        return scenes

    def lookup(self, scene: str, robot_id: str) -> FreeFlowEntry | None:
        """The entry for `robot_id` on `scene`, or None when the table lacks it."""
        return (self.scenes.get(scene) or {}).get(robot_id)


def load_free_flow_table(path: Path) -> FreeFlowTable:
    """Load and validate a free-flow table, failing loudly.

    Args:
        path: The table JSON.

    Returns:
        The validated table.

    Raises:
        FreeFlowTableError: If the file is missing, is not JSON, or fails the
            schema (an empty table included).
    """
    if not path.is_file():
        raise FreeFlowTableError(f"free-flow table not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FreeFlowTableError(f"{path}: not JSON ({exc})") from exc
    try:
        return FreeFlowTable.model_validate(data)
    except ValueError as exc:
        raise FreeFlowTableError(f"{path}: invalid free-flow table: {exc}") from exc


def default_table() -> tuple[FreeFlowTable | None, Path | None]:
    """The committed default table if it exists (loaded loudly), else `(None, None)`."""
    if not DEFAULT_TABLE_PATH.is_file():
        return None, None
    return load_free_flow_table(DEFAULT_TABLE_PATH), DEFAULT_TABLE_PATH


def file_sha256(path: Path) -> str:
    """Lowercase sha256 hex of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(gt_dir: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in (gt_dir / "ground_truth.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise ValueError(f"{gt_dir}: empty ground truth")
    return rows


def departure_sec(track: list[tuple[float, dict[str, Any]]]) -> float | None:
    """A robot's own departure: its first sample faster than `DEPARTURE_SPEED_MPS`.

    Args:
        track: `(sim time, robot GT dict)` pairs in time order.

    Returns:
        Sim time, or None when the robot never moves.
    """
    return next((t for t, r in track if r["speed_mps"] > DEPARTURE_SPEED_MPS), None)


def arrival_sec(track: list[tuple[float, dict[str, Any]]]) -> float | None:
    """The accepted arrival: within 0.35 m of the goal and never beyond 0.5 m after.

    Same rule as `t2b_forced_order.score_ground_truth`.

    Args:
        track: `(sim time, robot GT dict)` pairs in time order.

    Returns:
        Sim time, or None when the robot never arrives.
    """
    distances = [(t, r["distance_to_goal_m"]) for t, r in track]
    for index, (stamp, distance) in enumerate(distances):
        if distance <= ARRIVAL_TOLERANCE_M and all(
            later <= ARRIVAL_STAY_M for _t, later in distances[index:]
        ):
            return stamp
    return None


def derive_entries(
    gt_dir: Path,
    *,
    mechanism: str,
    run_id: str,
    robots: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Derive free-flow entries from one harvest run's ground truth.

    Args:
        gt_dir: The run's ground-truth directory.
        mechanism: `solo_in_time` or `solo_in_space`.
        run_id: The run's identifier (driver label + fc_launch stamp).
        robots: Robots to derive (default: every robot in the GT).

    Returns:
        Robot id -> entry fields (validated as `FreeFlowEntry`).

    Raises:
        ValueError: If a robot never departs or never arrives, or (solo in
            time) another robot moved during its traversal.
    """
    rows = _rows(gt_dir)
    tracks: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for row in rows:
        for rid, robot in row["robots"].items():
            tracks.setdefault(rid, []).append((row["sim_time_sec"], robot))
    gt_hash = file_sha256(gt_dir / "ground_truth.jsonl")
    out: dict[str, dict[str, Any]] = {}
    for rid in robots or sorted(tracks):
        if rid not in tracks:
            raise ValueError(f"{gt_dir}: {rid} not in ground truth")
        start, end = departure_sec(tracks[rid]), arrival_sec(tracks[rid])
        if start is None or end is None:
            raise ValueError(f"{gt_dir}: {rid} departure={start} arrival={end}; not a traversal")
        clearance = None
        for row in rows:
            if not start <= row["sim_time_sec"] <= end:
                continue
            me = row["robots"][rid]
            for other, robot in row["robots"].items():
                if other == rid:
                    continue
                if mechanism == "solo_in_time" and robot["speed_mps"] > DEPARTURE_SPEED_MPS:
                    raise ValueError(
                        f"{gt_dir}: {other} moved at {row['sim_time_sec']} during {rid}'s "
                        f"solo traversal [{start}, {end}]"
                    )
                gap = ((me["x"] - robot["x"]) ** 2 + (me["y"] - robot["y"]) ** 2) ** 0.5
                clearance = gap if clearance is None else min(clearance, gap)
        entry = {
            "time_sec": round(end - start, 2),
            "run_id": run_id,
            "gt_hash": gt_hash,
            "mechanism": mechanism,
            "departure_sec": round(start, 2),
            "arrival_sec": round(end, 2),
            "min_clearance_m": None if clearance is None else round(clearance, 3),
        }
        out[rid] = FreeFlowEntry.model_validate(entry).model_dump(mode="json")
    return out


def count_dispatches(decisions_dir: Path) -> int:
    """Decision artifacts that dispatched: a detected congestion with a grounded command.

    Shared by the free-flow harvest's zero-dispatch check and the outcome
    class's re-trigger count (`coverage_scene_scores.classify_outcome`); a
    re-analysis answering no congestion is not counted.

    Args:
        decisions_dir: The run's copied M5 decision artifacts.

    Returns:
        The count.
    """
    count = 0
    for path in sorted(decisions_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if (record.get("decision") or {}).get("congestion_detected") and record.get(
            "grounded_command_present"
        ):
            count += 1
    return count


def build_table(table_id: str, scenes: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """Assemble and validate a table from per-scene derived entries.

    Args:
        table_id: The table's identifier (e.g. `free_flow_v1`).
        scenes: Scene -> robot -> entry fields.

    Returns:
        The validated table as JSON-safe data.
    """
    table = FreeFlowTable(
        schema_version=1, table_id=table_id, origin_rule=ORIGIN_RULE,
        arrival_rule=ARRIVAL_RULE, scenes=scenes,
    )
    return table.model_dump(mode="json")


def _cmd_derive(args: argparse.Namespace) -> int:
    gt_dir = Path(args.gt)
    dispatches = None
    if args.decisions:
        dispatches = count_dispatches(Path(args.decisions))
        if dispatches:
            print(f"ERROR: {dispatches} dispatched decision(s); a free-flow run must have none",
                  file=sys.stderr)
            return 1
    entries = derive_entries(gt_dir, mechanism=args.mechanism, run_id=args.run_id,
                             robots=args.robot or None)
    print(json.dumps({"scene": args.scene, "dispatches": dispatches, "entries": entries},
                     indent=2))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    scenes: dict[str, dict[str, dict[str, Any]]] = {}
    for path in args.entries:
        derived = json.loads(Path(path).read_text(encoding="utf-8"))
        robots = scenes.setdefault(derived["scene"], {})
        for rid, entry in derived["entries"].items():
            if rid in robots:
                print(f"ERROR: {derived['scene']}/{rid} derived twice", file=sys.stderr)
                return 1
            robots[rid] = entry
    text = json.dumps(build_table(args.table_id, scenes), indent=2, sort_keys=True) + "\n"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    table = load_free_flow_table(Path(args.table))
    for scene, robots in sorted(table.scenes.items()):
        for rid, entry in sorted(robots.items()):
            print(f"{scene} {rid} {entry.time_sec:.2f}s {entry.mechanism} {entry.run_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    derive = sub.add_parser("derive", help="one harvest run's free-flow entries")
    derive.add_argument("--scene", required=True)
    derive.add_argument("--gt", required=True)
    derive.add_argument("--mechanism", required=True, choices=["solo_in_time", "solo_in_space"])
    derive.add_argument("--run-id", required=True)
    derive.add_argument("--robot", action="append")
    derive.add_argument("--decisions")
    derive.set_defaults(func=_cmd_derive)
    build = sub.add_parser("build", help="assemble derived entries into a table")
    build.add_argument("--entries", nargs="+", required=True)
    build.add_argument("--table-id", required=True)
    build.add_argument("--out", required=True)
    build.set_defaults(func=_cmd_build)
    check = sub.add_parser("check", help="validate a table")
    check.add_argument("--table", required=True)
    check.set_defaults(func=_cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
