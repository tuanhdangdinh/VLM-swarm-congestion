# isaac/scripts/generate_head_on_family.py
"""CLI: generate the head-on asymmetric scenario family and its manifest.

Usage:
    python isaac/scripts/generate_head_on_family.py
    python isaac/scripts/generate_head_on_family.py --out-dir /tmp/family \
        --geometry ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml
    python isaac/scripts/generate_head_on_family.py --goal-mode opponent_spawn \
        --out-dir /tmp/family

Writes one scenario YAML per feasible cell of the v1 parameter grid plus
`family_manifest.csv` into --out-dir (default `isaac/config/scenarios/family`).
Each variant differs from `head_on_deadlock.yaml` only in the parked blocker
boxes, robot_2's spawn offset, the base-mission goals, and the
`parameters`/`oracle` blocks.

`--goal-mode opponent_spawn` adds the `_gshort` cells: the same blockers with
each robot's goal on the opposing spawn instead of +-2.5, so no goal path
crosses a blocker box. `--goal-mode blocked_short` adds the `_bshort` cells,
which shorten only the goal that lies past the blocker and widen the open-side
goal to +-2.6, past the M3 escort endpoint by a drift-tolerant margin. The goal
mode is a generator option, deliberately not a
`HeadOnAsymmetricParams` field -- adding it there would emit a new line in the
`parameters:` block of the v1 variants and break their frozen bytes.

The oracle is computed by `isaac/vgu_sim/family_oracle.py` from the same M5
`scenario_geometry` block M3 grounds yield maneuvers against, so the
pre-registered answer cannot drift from the executed maneuver. The generated
YAMLs are committed so that answer is frozen and reviewable in git; a unit test
regenerates them into a temp directory and compares file text, so never
hand-edit a file under the output directory -- change this generator and re-run
it instead.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Literal, get_args

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.vgu_sim.config import (
    HeadOnAsymmetricParams,
    ObstacleSize,
    Pose2D,
    ScenarioConfig,
    StaticObstacleConfig,
)
from isaac.vgu_sim.family_oracle import (
    SIDE_ROBOT,
    SPAWN_OFFSET_M,
    blocker_center_x_m,
    compute_oracle,
    load_scene_geometry,
    required_room_m,
    room_from_mouth_m,
)
from reasoning.rag.scene_geometry import SceneGeometry, park_offset_m, passer_clearance_m

FAMILY_DIR = Path("isaac/config/scenarios/family")
BASE_SCENARIO = Path("isaac/config/scenarios/head_on_deadlock.yaml")
DEFAULT_GEOMETRY_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
GENERATOR_PATH = "isaac/scripts/generate_head_on_family.py"
MANIFEST_NAME = "family_manifest.csv"
NAME_PREFIX = "head_on_asymmetric"

# Where each robot's base-mission goal sits along the corridor axis.
#   beyond          - the v1 goals inherited from head_on_deadlock (+-2.5),
#                     which lie past the opposing spawn AND past any blocker
#                     box parked behind it, so the robot crossing to that side
#                     must squeeze through the 0.20 m gap beside the box.
#   opponent_spawn  - each robot's goal is the other robot's spawn (+-1.5), so
#                     no goal path crosses a blocker. Retreat room behind each
#                     spawn, and therefore the oracle, is untouched.
#   blocked_short   - only the goal on the BLOCKED side is shortened to the
#                     blocked robot's spawn; the goal on the OPEN side moves
#                     out to +-2.6 (BLOCKED_SHORT_PASSER_GOAL_M). No goal path
#                     crosses a blocker, and the passer's goal stays beyond the
#                     yielder's park point, so an arrived passer never sits in
#                     the yielder's return path (the 2026-09-25 gshort west
#                     losses H2/H3).
GoalMode = Literal["beyond", "opponent_spawn", "blocked_short"]
GOAL_MODES: tuple[GoalMode, ...] = get_args(GoalMode)
DEFAULT_GOAL_MODE: GoalMode = "beyond"
# Slug inserted into the variant id for a non-default goal mode. The default
# mode contributes nothing, so v1 variant ids and filenames are unchanged.
GOAL_MODE_SLUG: dict[GoalMode, str] = {
    "beyond": "",
    "opponent_spawn": "gshort",
    "blocked_short": "bshort",
}
PREREG_TAG_BY_GOAL_MODE: dict[GoalMode, str] = {
    "beyond": "prereg-v1",
    "opponent_spawn": "prereg-v1-gshort",
    "blocked_short": "prereg-v1-bshort",
}
PREREG_TAG = PREREG_TAG_BY_GOAL_MODE[DEFAULT_GOAL_MODE]
# |x| of the open-side passer's goal in blocked_short mode. The inherited +-2.5
# cleared the M3 escort endpoint (park_offset_m + passer_clearance_m, 2.439 m)
# by only 0.061 m, less than the ~0.1 m odometry drift FEASIBILITY_MARGIN_M
# budgets for; 2.6 clears it by 0.161 m and stays well inside the camera ROI
# (+-3.0) and the warehouse walls (+-6).
BLOCKED_SHORT_PASSER_GOAL_M = 2.6
BLOCKER_SIZE = ObstacleSize(x_m=0.3, y_m=0.3, z_m=0.5)
MANIFEST_COLUMNS: tuple[str, ...] = (
    "name",
    "variant",
    "blocker_west_m",
    "blocker_east_m",
    "arrival_offset_m",
    "correct_yielder",
    "fcfs_yielder",
    "feasible_yielders",
    "contrasts_fcfs",
    "tier",
)
# Sums of decimal blocker offsets carry a binary tail (1.0 + 0.5 + 0.2 + 0.15 is
# 1.8499999999999999), which would land verbatim in a pre-registered artifact.
# Rounding well below simulator resolution keeps the committed YAML readable.
_COORD_DECIMALS = 6


def _slug(value: float | None) -> str:
    if value is None:
        return "open"
    return f"{value:g}".replace(".", "p")


def _number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def _open_or_number(value: float | None) -> str:
    return "open" if value is None else f"{value:g}"


def load_scenario(path: Path) -> ScenarioConfig:
    """Load and validate one scenario YAML config.

    Args:
        path: Path to a file under `isaac/config/scenarios/`.

    Returns:
        The validated scenario config.
    """
    with open(path) as f:
        return ScenarioConfig.model_validate(yaml.safe_load(f))


def variant_id(
    params: HeadOnAsymmetricParams, goal_mode: GoalMode = DEFAULT_GOAL_MODE
) -> str:
    """Filesystem-safe identifier for one cell of the family grid.

    Floats print in `:g` form with the decimal point replaced by `p` and an
    absent blocker printed as `open`, because `ScenarioConfig.name` forbids
    dots: `blocker_west_m=0.2` with both other knobs default gives
    `w0p2_eopen_o0`. A non-default goal mode adds its slug between the blocker
    and arrival-offset fields, giving `w0p2_eopen_gshort_o0`.

    Args:
        params: The cell's blocker and arrival-offset parameters.
        goal_mode: Where the cell's base-mission goals sit.

    Returns:
        The variant identifier.
    """
    slug = GOAL_MODE_SLUG[goal_mode]
    goal_part = f"_{slug}" if slug else ""
    return (
        f"w{_slug(params.blocker_west_m)}"
        f"_e{_slug(params.blocker_east_m)}"
        f"{goal_part}"
        f"_o{_slug(params.arrival_offset_m)}"
    )


def scenario_name(
    params: HeadOnAsymmetricParams, goal_mode: GoalMode = DEFAULT_GOAL_MODE
) -> str:
    """Scenario name for one cell of the family grid.

    Args:
        params: The cell's blocker and arrival-offset parameters.
        goal_mode: Where the cell's base-mission goals sit.

    Returns:
        The scenario name, e.g. `head_on_asymmetric_w0p2_eopen_o0`.
    """
    return f"{NAME_PREFIX}_{variant_id(params, goal_mode)}"


def grid_v1() -> list[HeadOnAsymmetricParams]:
    """The pre-registered v1 parameter grid, in west-major order.

    Both blockers range over `{0.2, None}` at a zero arrival offset, so the
    grid holds one double-blocker cell (no feasible yielder, skipped when
    generating), two single-blocker cells, and the open baseline.

    Returns:
        The grid's four parameter sets.
    """
    return [
        HeadOnAsymmetricParams(blocker_west_m=west, blocker_east_m=east, arrival_offset_m=0.0)
        for west in (0.2, None)
        for east in (0.2, None)
    ]


def grid_gshort() -> list[HeadOnAsymmetricParams]:
    """The goal-short grid: the two single-blocker cells of `grid_v1`.

    The open baseline gains nothing from moving the goals (it has no blocker to
    keep off a goal path) and the double-blocker cell has no feasible yielder,
    so only the two T2a cells are regenerated in `opponent_spawn` goal mode.

    Returns:
        The two single-blocker parameter sets, in west-major order.
    """
    return [
        params
        for params in grid_v1()
        if (params.blocker_west_m is None) != (params.blocker_east_m is None)
    ]


def _opponent_spawn_goals(robots: list[dict]) -> dict[str, tuple[float, float]]:
    """Map each robot id to the spawn position of the robot facing it.

    Only the two-robot head-on layout is supported: the goal of each robot is
    the other's spawn point, projected onto the corridor centreline (`y = 0`)
    so a goal never carries the spawn's lateral jitter.

    Args:
        robots: The scenario's robot blocks, as plain dicts.

    Returns:
        Goal `(x, y)` per robot id.

    Raises:
        ValueError: If the scenario does not hold exactly two robots.
    """
    if len(robots) != 2:
        raise ValueError(
            f"goal_mode 'opponent_spawn' needs exactly two robots; got {len(robots)}"
        )
    first, second = robots
    return {
        first["robot_id"]: (second["spawn"]["x"], 0.0),
        second["robot_id"]: (first["spawn"]["x"], 0.0),
    }


def _blocked_side(params: HeadOnAsymmetricParams) -> Literal["west", "east"]:
    """Which side of the corridor carries the single blocker box.

    Args:
        params: The cell's blocker and arrival-offset parameters.

    Returns:
        `"west"` or `"east"`.

    Raises:
        ValueError: If the cell has no blocker or a blocker on both sides.
    """
    west, east = params.blocker_west_m is not None, params.blocker_east_m is not None
    if west and not east:
        return "west"
    if east and not west:
        return "east"
    raise ValueError(
        "goal_mode 'blocked_short' needs exactly one blocked side; got "
        f"west={params.blocker_west_m}, east={params.blocker_east_m}"
    )


def _blocked_short_goals(
    robots: list[dict], params: HeadOnAsymmetricParams
) -> dict[str, tuple[float, float]]:
    """Map each robot id to its goal with only the blocked-side goal shortened.

    The robot spawned on the blocked side -- the passer -- keeps the direction
    of its base-mission goal, but at `BLOCKED_SHORT_PASSER_GOAL_M` instead of
    +-2.5, so the goal lies on the open side beyond both the yielder's park
    point and the M3 escort endpoint. The robot on the open side -- the
    oracle's yielder, whose base goal lies past the blocker box -- has its
    goal pulled back to the blocked robot's spawn, stopping it short of the
    box instead of squeezing it past.

    Args:
        robots: The scenario's robot blocks, as plain dicts.
        params: The cell's blocker and arrival-offset parameters.

    Returns:
        Goal `(x, y)` per robot id.

    Raises:
        ValueError: If the scenario does not hold exactly two robots.
    """
    if len(robots) != 2:
        raise ValueError(
            f"goal_mode 'blocked_short' needs exactly two robots; got {len(robots)}"
        )
    blocked_robot = SIDE_ROBOT[_blocked_side(params)]
    by_id = {robot["robot_id"]: robot for robot in robots}
    if blocked_robot not in by_id:
        raise ValueError(f"scenario has no {blocked_robot} to anchor the shortened goal on")
    shortened_x = by_id[blocked_robot]["spawn"]["x"]
    passer_goal_x = math.copysign(BLOCKED_SHORT_PASSER_GOAL_M, by_id[blocked_robot]["goal"]["x"])
    return {
        robot["robot_id"]: (
            (passer_goal_x, 0.0)
            if robot["robot_id"] == blocked_robot
            else (shortened_x, 0.0)
        )
        for robot in robots
    }


def build_variant(
    base: ScenarioConfig,
    params: HeadOnAsymmetricParams,
    geometry: SceneGeometry,
    goal_mode: GoalMode = DEFAULT_GOAL_MODE,
) -> ScenarioConfig | None:
    """Derive one family variant from the base head-on scenario.

    robot_1's spawn is untouched; robot_2's spawn slides east by
    `arrival_offset_m` so it reaches the corridor mouth later. Each non-null
    blocker side gains a parked box behind that robot's spawn.

    Goals move only in `opponent_spawn` and `blocked_short` modes, and only
    the goals: spawns, blockers, and therefore the oracle are identical to the
    `beyond` cell with the same `params`.

    Args:
        base: The base `head_on_deadlock` scenario config.
        params: The variant's blocker and arrival-offset parameters.
        geometry: Declared scene geometry.
        goal_mode: Where the base-mission goals sit; `beyond` keeps the base
            scenario's own goals.

    Returns:
        The validated variant config, or `None` when neither side can park and
        the cell therefore has no pre-registrable oracle.
    """
    oracle = compute_oracle(params, geometry)
    if oracle is None:
        return None

    spawn_x = round(
        geometry.corridor.half_length_m + SPAWN_OFFSET_M + params.arrival_offset_m,
        _COORD_DECIMALS,
    )
    obstacles = [
        StaticObstacleConfig(
            obstacle_id=f"blocker_{side}",
            pose=Pose2D(
                x=round(
                    blocker_center_x_m(side, blocker_m, params.arrival_offset_m, geometry),
                    _COORD_DECIMALS,
                ),
                y=0.0,
                yaw_rad=0.0,
            ),
            size=BLOCKER_SIZE,
        )
        for side, blocker_m in (
            ("west", params.blocker_west_m),
            ("east", params.blocker_east_m),
        )
        if blocker_m is not None
    ]

    # Editing a plain dump and re-validating keeps every cross-field invariant
    # in play, which nested `model_copy` on frozen submodels would bypass.
    data = base.model_dump(mode="json")
    data["name"] = scenario_name(params, goal_mode)
    data["family"] = "head_on"
    data["parameters"] = params.model_dump(mode="json")
    data["oracle"] = oracle.model_dump(mode="json")
    data["static_obstacles"] = [o.model_dump(mode="json") for o in obstacles]
    for robot in data["robots"]:
        if robot["robot_id"] == "robot_2":
            robot["spawn"]["x"] = spawn_x
    goals: dict[str, tuple[float, float]] | None = None
    if goal_mode == "opponent_spawn":
        goals = _opponent_spawn_goals(data["robots"])
    elif goal_mode == "blocked_short":
        goals = _blocked_short_goals(data["robots"], params)
    if goals is not None:
        for robot in data["robots"]:
            goal_x, goal_y = goals[robot["robot_id"]]
            robot["goal"]["x"] = goal_x
            robot["goal"]["y"] = goal_y
    return ScenarioConfig.model_validate(data)


def render_yaml(
    config: ScenarioConfig,
    geometry: SceneGeometry,
    goal_mode: GoalMode = DEFAULT_GOAL_MODE,
) -> str:
    """Render one variant config as commented YAML text.

    The header records the generator, the pre-registration tag, the variant's
    parameters, the park-room comparison that decided the oracle, and each
    blocker box's near/centre/far faces, so a reviewer can check the frozen
    oracle without re-running the generator. It carries no timestamp or
    absolute path, because a unit test compares the committed text byte for
    byte against a fresh generation.

    Args:
        config: The variant config to render.
        geometry: Declared scene geometry the header numbers come from.
        goal_mode: The mode the config was built in, described in the header.

    Returns:
        The YAML document text, header comments first.
    """
    header = "\n".join(_header_lines(config, geometry, goal_mode))
    body = yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False)
    return f"{header}\n{body}"


def _header_lines(
    config: ScenarioConfig,
    geometry: SceneGeometry,
    goal_mode: GoalMode = DEFAULT_GOAL_MODE,
) -> list[str]:
    params = config.parameters
    if params is None:
        raise ValueError(f"scenario {config.name!r} has no parameters block to describe")

    required = required_room_m(geometry)
    lines = [
        f"# Generated by {GENERATOR_PATH} -- do not edit by hand.",
        f"# Frozen at {PREREG_TAG_BY_GOAL_MODE[goal_mode]}: the oracle block below is "
        "the pre-registered answer",
        "# for this cell, computed by isaac/vgu_sim/family_oracle.py from the M5",
        "# scenario_geometry block, not authored by hand.",
        "#",
        f"# parameters: blocker_west_m={_open_or_number(params.blocker_west_m)}, "
        f"blocker_east_m={_open_or_number(params.blocker_east_m)}, "
        f"arrival_offset_m={_number(params.arrival_offset_m)}",
        f"# required_room_m = {required:.3f} (room from the corridor mouth a blocked "
        "spawn must keep to park)",
    ]
    if goal_mode != DEFAULT_GOAL_MODE:
        lines.extend(_goal_mode_lines(config, geometry, goal_mode))

    for side in ("west", "east"):
        blocker_m = getattr(params, f"blocker_{side}_m")
        robot = SIDE_ROBOT[side]
        if blocker_m is None:
            lines.append(f"# {side}: no blocker -- {robot} can park")
            continue
        room = room_from_mouth_m(blocker_m)
        feasible = room >= required
        lines.append(
            f"# {side}: room_from_mouth_m {room:.3f} {'>=' if feasible else '<'} "
            f"{required:.3f} -- {robot} {'can' if feasible else 'cannot'} park"
        )

    for obstacle in config.static_obstacles:
        half = obstacle.size.x_m / 2.0
        sign = 1.0 if obstacle.pose.x >= 0.0 else -1.0
        lines.append(
            f"# {obstacle.obstacle_id} box faces along x: "
            f"near {obstacle.pose.x - sign * half:.3f}, "
            f"centre {obstacle.pose.x:.3f}, "
            f"far {obstacle.pose.x + sign * half:.3f}"
        )

    return lines


def _goal_mode_lines(
    config: ScenarioConfig, geometry: SceneGeometry, goal_mode: GoalMode
) -> list[str]:
    goals = ", ".join(f"{r.robot_id} -> ({r.goal.x:g}, {r.goal.y:g})" for r in config.robots)
    lines = [f"# goal_mode: {goal_mode} -- {goals}"]
    if goal_mode == "opponent_spawn":
        lines.append(
            "# Each goal is the opposing robot's spawn, so no goal path crosses a "
            "blocker box."
        )
        lines.append(
            "# Spawns, blockers and the oracle are byte-identical to the "
            "corresponding beyond-goal"
        )
        lines.append(
            "# variant. M5 does NOT read these goals: set orchestrator.yaml "
            "initial_tasks to match."
        )
    if goal_mode == "blocked_short":
        lines.append(
            "# Only the blocked-side goal is shortened, to the blocked robot's "
            "spawn; the open-side"
        )
        lines.append(
            f"# goal moves to +-{BLOCKED_SHORT_PASSER_GOAL_M:g}, so the passer's goal "
            "stays beyond the yielder's park point and an"
        )
        lines.append(
            "# arrived passer never sits in the yielder's return path (the "
            "gshort H2/H3 losses)."
        )
        park = park_offset_m(geometry)
        escort_end = park + passer_clearance_m(geometry)
        lines.append(
            f"# Passer goal margins: {BLOCKED_SHORT_PASSER_GOAL_M - park:.3f} m beyond the "
            f"yielder's park point ({park:.3f}) and"
        )
        lines.append(
            f"# {BLOCKED_SHORT_PASSER_GOAL_M - escort_end:.3f} m beyond the M3 escort "
            f"endpoint ({escort_end:.3f} = park + passer_clearance_m)."
        )
        lines.append(
            "# Spawns, blockers and the oracle are byte-identical to the "
            "corresponding beyond-goal"
        )
        lines.append(
            "# variant. M5 does NOT read these goals: set orchestrator.yaml "
            "initial_tasks to"
        )
        for robot in config.robots:
            lines.append(
                f"#   {robot.robot_id}: {{ task: {robot.initial_task}, "
                f"goal: [{robot.goal.x:g}, {robot.goal.y:g}] }}"
            )
    return lines


def manifest_rows(configs: list[ScenarioConfig]) -> list[dict[str, str]]:
    """Summarize each generated variant as one manifest row.

    Args:
        configs: The generated variant configs, in grid order.

    Returns:
        One string-valued row per config, keyed by `MANIFEST_COLUMNS`.

    Raises:
        ValueError: If a config carries no `parameters` or no `oracle` block.
    """
    rows: list[dict[str, str]] = []
    for config in configs:
        params, oracle = config.parameters, config.oracle
        if params is None or oracle is None:
            raise ValueError(
                f"scenario {config.name!r} needs both parameters and oracle to be listed"
            )
        rows.append(
            {
                "name": config.name,
                # Taken from the name rather than rebuilt from `params`, because
                # the goal mode is a generator option and not a params field.
                "variant": config.name.removeprefix(f"{NAME_PREFIX}_"),
                "blocker_west_m": _number(params.blocker_west_m),
                "blocker_east_m": _number(params.blocker_east_m),
                "arrival_offset_m": _number(params.arrival_offset_m),
                "correct_yielder": oracle.correct_yielder,
                "fcfs_yielder": oracle.fcfs_yielder,
                "feasible_yielders": "|".join(oracle.feasible_yielders),
                "contrasts_fcfs": "true" if oracle.contrasts_fcfs else "false",
                "tier": "T1" if len(oracle.feasible_yielders) == 2 else "T2a",
            }
        )
    return rows


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    # newline="" is the csv module's contract; "\n" keeps the committed artifact
    # from carrying the module's default CRLF endings.
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(MANIFEST_COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def grid_for(goal_mode: GoalMode) -> list[HeadOnAsymmetricParams]:
    """The parameter cells generated in one goal mode.

    Every goal mode that moves a goal only has something to say about a cell
    holding a blocker, so all of them share `grid_gshort`'s two cells.

    Args:
        goal_mode: Where that mode's base-mission goals sit.

    Returns:
        The mode's parameter sets, in west-major order.
    """
    return grid_v1() if goal_mode == DEFAULT_GOAL_MODE else grid_gshort()


def write_family(
    out_dir: Path,
    geometry_yaml: Path,
    goal_modes: tuple[GoalMode, ...] = GOAL_MODES,
) -> list[Path]:
    """Generate every feasible family variant plus the manifest into a directory.

    Cells with no feasible yielder are skipped with a printed line. Modes are
    generated in `goal_modes` order and the manifest rows follow that order, so
    restricting the modes yields a strict prefix of the full manifest.

    Args:
        out_dir: Directory to write the variant YAMLs and manifest into.
        geometry_yaml: Path to the orchestrator config holding the M5
            `scenario_geometry` block.
        goal_modes: Goal modes to generate, in output order.

    Returns:
        The written scenario YAML paths, in grid order; the manifest is written
        but not listed.
    """
    geometry = load_scene_geometry(geometry_yaml)
    base = load_scenario(BASE_SCENARIO)
    out_dir.mkdir(parents=True, exist_ok=True)

    configs: list[ScenarioConfig] = []
    written: list[Path] = []
    for goal_mode in goal_modes:
        for params in grid_for(goal_mode):
            config = build_variant(base, params, geometry, goal_mode)
            if config is None:
                print(f"skipped {variant_id(params, goal_mode)}: no feasible yielder")
                continue
            path = out_dir / f"{config.name}.yaml"
            path.write_text(render_yaml(config, geometry, goal_mode))
            configs.append(config)
            written.append(path)

    _write_manifest(out_dir / MANIFEST_NAME, manifest_rows(configs))
    return written


def main(argv: list[str] | None = None) -> None:
    """Entry point for the head-on asymmetric family generator CLI."""
    parser = argparse.ArgumentParser(
        description="Generate the head-on asymmetric scenario family and its manifest"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=FAMILY_DIR,
        help=f"Output directory for the variant YAMLs and manifest (default: {FAMILY_DIR})",
    )
    parser.add_argument(
        "--geometry",
        type=Path,
        default=DEFAULT_GEOMETRY_YAML,
        help="Orchestrator config supplying the M5 scenario_geometry block "
        f"(default: {DEFAULT_GEOMETRY_YAML})",
    )
    parser.add_argument(
        "--goal-mode",
        choices=("all", *GOAL_MODES),
        default="all",
        help="Which goal modes to generate: 'beyond' keeps the base scenario's "
        "+-2.5 goals, 'opponent_spawn' puts each robot's goal on the other's "
        "spawn, 'blocked_short' shortens only the blocked-side goal and moves "
        f"the open-side goal to +-{BLOCKED_SHORT_PASSER_GOAL_M:g} (default: all)",
    )
    args = parser.parse_args(argv)

    goal_modes = GOAL_MODES if args.goal_mode == "all" else (args.goal_mode,)
    for path in write_family(args.out_dir, args.geometry, goal_modes):
        print(f"wrote {path}")
    print(f"wrote {args.out_dir / MANIFEST_NAME}")


if __name__ == "__main__":
    main()
