#!/usr/bin/env python3
"""Strategy-regret harness: per-scene strategy cost tables and decision regret.

Amendments item 29 registers strategy-regret scoring: forced-strategy mock
sweeps produce a per-scene strategy cost table (mean total time-to-goal per
executable strategy, from Isaac ground truth), and a recorded decision is
scored as time regret against the best executable strategy, alongside its
label. This generalises the T2b forced-order harness
(`scripts/t2b_forced_order.py`, whose ground-truth scorer it reuses) from two
yield orders to every executable arm of a scene. It prepares and scores only:
the VM smoke batch runs the sweeps through `scripts/vm/fc_launch.sh`.

An arm is identified by its executed roles, never by its label: a `convoy`
decision and "yield robot_2 + platoon order" execute identically (M3's
alias), so they are one arm; a label is scored separately.

Subcommands:

- `scenes`: list the registered scenes and their arms.
- `preflight --scene S --repo <tree>`: refuse to run unless the tree carries
  the scene's files and orchestrator.yaml / config/rag.yaml are set to the
  scene's goal-table row. Stdlib + PyYAML only, so it runs on the VM host.
- `plan --scene S --seeds 42 43 [--arms a b]`: the sweep matrix, arms
  interleaved per seed so drift hits every arm.
- `score --scene S --run <arm>:<ground-truth dir> ... [--out table.json]`: the
  strategy cost table.
- `regret --table table.json --decision <artifact or decision json>`: the
  decision's arm, regret against the best arm, and its label.

Usage:
    python3 scripts/strategy_regret.py plan --scene convoy_counterflow --seeds 42 43
    python3 scripts/strategy_regret.py score --scene convoy_counterflow \\
        --run oracle:runs/oracle_seed42/gt --run oracle:runs/oracle_seed43/gt \\
        --run alternative:runs/alternative_seed42/gt ... --out cost_table.json
    python3 scripts/strategy_regret.py regret --table cost_table.json \\
        --decision data/logs/m5_decisions/<request_id>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.t2b_forced_order import RunScore, score_ground_truth  # noqa: E402

ORCHESTRATOR_RELPATH = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
RAG_RELPATH = Path("config/rag.yaml")
MAPS_RELDIR = Path("ros2_ws/src/swarm_simulation/maps")
SCENARIOS_RELDIR = Path("isaac/config/scenarios")
MIN_RUNS_PER_ARM = 2

# Executed roles of one arm: ("yield", yielder, crossing order),
# ("reroute", robot), or ("temporary_wait", sorted robots).
Roles = tuple[Any, ...]


@dataclass(frozen=True)
class ArmSpec:
    """One executable strategy of a scene: its label, mock and executed roles."""

    strategy: str
    mock_decision_file: str
    # Every roles key this arm executes as. A yield M3 refuses and degrades
    # also matches its degraded command's roles.
    roles: tuple[Roles, ...]


@dataclass(frozen=True)
class SceneSpec:
    """A scene's goal-table row (what preflight checks) and its arms."""

    name: str
    initial_tasks: dict[str, dict[str, Any]]
    corridor: dict[str, Any]
    grounding_mode: str
    arms: dict[str, ArmSpec]
    scenario_geometry_arms: dict[str, dict[str, Any]] | None = None
    aisle_x_band_m: tuple[float, float] | None = None
    # Accepted labels by strategy, for label scoring (None: not a label tier).
    accepted_strategies: tuple[str, ...] | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    # Step-7b Part 3 (IB10 `junction_clear` regret extension): the
    # composite's own geometry overlay, additive-only -- every other scene
    # leaves these None and `preflight` skips the checks entirely, matching
    # `scenario_geometry_arms`/`aisle_x_band_m`'s own None-is-a-no-op
    # convention.
    junction_recede_offset_m: float | None = None
    junction_backup_clearance_m: float | None = None
    junction_recede_stagger_m: float | None = None
    tracked_extent_m: float | None = None
    shadow_classical_zones: tuple[dict[str, Any], ...] | None = None
    plan_channel_enabled: bool = False

    @property
    def scenario_relpath(self) -> Path:
        """The scene's scenario YAML, relative to the repo root."""
        return SCENARIOS_RELDIR / f"{self.name}.yaml"

    @property
    def map_relpath(self) -> Path:
        """The scene's Nav2 map YAML, relative to the repo root."""
        return MAPS_RELDIR / f"warehouse_map_{self.name}.yaml"


def _task(goal: list[float], **extra: Any) -> dict[str, Any]:
    return {"task": "cross_narrow_aisle", "goal": goal, **extra}


def _b2(member: str, urgent: str, routine: str) -> SceneSpec:
    goals = {"robot_1": [2.5, 0.0], "robot_2": [-2.5, 0.0]}
    yield_mock = {
        "robot_1": "config/mock_decisions/head_on_yield_once.json",
        "robot_2": "config/mock_decisions/head_on_yield_robot_2_once.json",
    }
    return SceneSpec(
        name=f"priority_urgent_{member}",
        initial_tasks={
            urgent: {"task": "urgent_order_delivery", "goal": goals[urgent], "priority": 1},
            routine: {"task": "routine_order_delivery", "goal": goals[routine]},
        },
        corridor={"axis": "x", "center_m": 0.0, "half_length_m": 1.0},
        grounding_mode="derived",
        arms={
            # priority_override executes as this arm (M3's registry alias).
            "yield_routine": ArmSpec(
                "yield", yield_mock[routine], (("yield", routine, (urgent,)),)
            ),
            "yield_urgent": ArmSpec(
                "yield", yield_mock[urgent], (("yield", urgent, (routine,)),)
            ),
        },
    )


SCENES: dict[str, SceneSpec] = {
    "t2b_flow_ordering": SceneSpec(
        name="t2b_flow_ordering",
        initial_tasks={
            "robot_1": _task([2.5, 0.0]),
            "robot_2": _task([-2.0, 0.0]),
            "robot_3": _task([1.85, 0.0], start_delay_sec=55.0),
        },
        corridor={"axis": "x", "center_m": 0.0, "half_length_m": 0.5},
        grounding_mode="legacy",
        arms={
            "oracle": ArmSpec(
                "yield", "config/mock_decisions/t2b_oracle_order_once.json",
                (("yield", "robot_2", ("robot_1", "robot_3")),),
            ),
            "alternative": ArmSpec(
                "yield", "config/mock_decisions/t2b_alternative_order_once.json",
                (("yield", "robot_1", ("robot_2", "robot_3")),),
            ),
        },
    ),
    "bottleneck_merge": SceneSpec(
        name="bottleneck_merge",
        initial_tasks={
            "robot_1": _task([2.45, -0.3]),
            "robot_2": _task([1.9, 0.0]),
            "robot_3": _task([2.45, 0.3], start_delay_sec=80.0),
        },
        # half_length_m raised 0.6 -> 1.1 by the rev-19b geometry fix
        # (isaac/config/scenarios/bottleneck_merge.yaml header): restores the
        # escort margin at the measured trigger poses without moving any
        # spawn, goal or barrier position.
        corridor={
            "axis": "x", "center_m": 0.0, "half_length_m": 1.1,
            "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
        },
        scenario_geometry_arms={
            "robot_1": {"axis": "x", "side": -1},
            "robot_2": {"axis": "y", "side": 1},
            "robot_3": {"axis": "x", "side": -1},
        },
        aisle_x_band_m=(-0.46, 0.46),
        grounding_mode="derived",
        arms={
            "oracle": ArmSpec(
                "yield", "config/mock_decisions/bottleneck_merge_yield_once.json",
                (("yield", "robot_2", ("robot_1", "robot_3")),),
            ),
            # Refused by derived grounding (robot_3 behind robot_1): it runs
            # as a reroute of robot_1.
            "alternative": ArmSpec(
                "yield", "config/mock_decisions/bottleneck_merge_alternative_order_once.json",
                (("yield", "robot_1", ("robot_2", "robot_3")), ("reroute", "robot_1")),
            ),
            "wait": ArmSpec(
                "temporary_wait", "config/mock_decisions/bottleneck_merge_wait_once.json",
                (("temporary_wait", ("robot_1", "robot_2", "robot_3")),),
            ),
        },
    ),
    "priority_urgent_r1": _b2("r1", "robot_1", "robot_2"),
    "priority_urgent_r2": _b2("r2", "robot_2", "robot_1"),
    "convoy_counterflow": SceneSpec(
        name="convoy_counterflow",
        # robot_1/robot_3 goal lateral raised 0.3 -> 0.36 (Rev 22 B3 goal-table
        # fix, notes 2026-09-30): the old +-0.3 stack (0.6 m apart) let
        # robot_3's released base-mission approach pass 0.426-0.444 m from
        # the parked robot_1 (< the 0.45 m floor), latching under the correct
        # passer-passer non-exemption in 3/4 VM replicates. 0.36 m is this
        # scene's own pull_off_lateral_m (isaac/config/scenarios/
        # convoy_counterflow.yaml header derives the full margin math).
        initial_tasks={
            "robot_1": _task([2.45, -0.36]),
            "robot_2": _task([-2.0, 0.0]),
            "robot_3": _task([2.45, 0.36], start_delay_sec=120.0),
            "robot_4": _task([1.85, 0.0], start_delay_sec=120.0),
        },
        corridor={"axis": "x", "center_m": 0.0, "half_length_m": 0.5},
        grounding_mode="legacy",
        accepted_strategies=("convoy", "yield"),
        arms={
            # convoy executes as this arm (M3's alias); one sweep covers both.
            "oracle": ArmSpec(
                "yield", "config/mock_decisions/convoy_counterflow_oracle_order_once.json",
                (("yield", "robot_2", ("robot_1", "robot_3", "robot_4")),),
            ),
            "alternative": ArmSpec(
                "yield", "config/mock_decisions/convoy_counterflow_alternative_order_once.json",
                (("yield", "robot_1", ("robot_2", "robot_3", "robot_4")),),
            ),
            # Arm B's shape: the queue is omitted (censored by construction).
            "pair_yield": ArmSpec(
                "yield", "config/mock_decisions/convoy_counterflow_pair_yield_once.json",
                (("yield", "robot_2", ("robot_1",)),),
            ),
        },
    ),
    # Step-7b Part 3 (IB10 oracle + regret extension, freezing IB10 scoring):
    # `junction_clear`-forced vs `best_single_yield`-forced. The T2b/T1-X
    # precedent this mirrors: v1's own finding (no architecture recovers a
    # formed four-way scrum from a single yielder) makes `best_single_yield`
    # a CENSORED arm by construction -- a forced sweep of
    # `intersection_yield_once.json` is expected not to reach 4/4, so its
    # regret is only ever a lower bound (`RunScore.censored`,
    # `cost_table`'s existing censored-reference handling), exactly T2b's
    # own margin semantics. `junction_clear` is this scene's `vlm_verbatim`
    # mock (`config/mock_decisions/intersection_junction_clear_vlm_verbatim_
    # once.json`): the chi-ranked recede pair in order, then the yield-axis
    # pair, so the (a0) engine finds every leg feasible and runs it
    # verbatim -- the cell this scoring freeze is about.
    "intersection_bottleneck": SceneSpec(
        name="intersection_bottleneck",
        initial_tasks={
            "robot_1": {"task": "cross_intersection", "goal": [1.75, 0.0]},
            "robot_2": {"task": "cross_intersection", "goal": [-1.75, 0.0]},
            "robot_3": {"task": "cross_intersection", "goal": [0.0, 1.75]},
            "robot_4": {"task": "cross_intersection", "goal": [0.0, -1.75]},
        },
        corridor={
            "axis": "x", "center_m": 0.0, "half_length_m": 0.6,
            "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
        },
        scenario_geometry_arms={
            "robot_1": {"axis": "x", "side": -1},
            "robot_2": {"axis": "x", "side": 1},
            "robot_3": {"axis": "y", "side": -1},
            "robot_4": {"axis": "y", "side": 1},
        },
        shadow_classical_zones=({"zone_id": "crossing_1", "x": 0.0, "y": 0.0, "radius_m": 1.5},),
        junction_recede_offset_m=1.2,
        junction_backup_clearance_m=1.1,
        junction_recede_stagger_m=0.2,
        tracked_extent_m=1.75,
        plan_channel_enabled=True,
        grounding_mode="derived",
        arms={
            "junction_clear": ArmSpec(
                "junction_clear",
                "config/mock_decisions/intersection_junction_clear_vlm_verbatim_once.json",
                (("reverse",),),
            ),
            # Forced single-yield (Arm B's own intersection shape, v1
            # vocabulary): expected CENSORED -- registered so the contrast
            # is expressible, not because this sweep is expected to pass.
            "best_single_yield": ArmSpec(
                "yield", "config/mock_decisions/intersection_yield_once.json",
                (("yield", "robot_2", ("robot_1", "robot_3", "robot_4")),),
            ),
        },
    ),
}


def _scene(name: str) -> SceneSpec:
    if name not in SCENES:
        raise SystemExit(f"unknown scene {name!r}; registered: {sorted(SCENES)}")
    return SCENES[name]


def preflight(scene: SceneSpec, repo: Path) -> list[str]:
    """Check a deployed tree is configured for one scene's sweep.

    Args:
        scene: The scene to run.
        repo: Root of the tree the runs will use.

    Returns:
        One message per failed check; empty when the tree may run.
    """
    problems: list[str] = []
    files = [scene.scenario_relpath, scene.map_relpath,
             *(Path(arm.mock_decision_file) for arm in scene.arms.values())]
    for relpath in files:
        if not (repo / relpath).is_file():
            problems.append(f"missing file {relpath}")
    orch_path = repo / ORCHESTRATOR_RELPATH
    if not orch_path.is_file():
        return [*problems, f"missing file {ORCHESTRATOR_RELPATH}"]
    config = yaml.safe_load(orch_path.read_text(encoding="utf-8")) or {}
    problems += _check_tasks(scene, config.get("initial_tasks") or {})
    geometry = config.get("scenario_geometry") or {}
    corridor = geometry.get("corridor") or {}
    for key, value in scene.corridor.items():
        if corridor.get(key) != value:
            problems.append(
                f"orchestrator.yaml scenario_geometry.corridor.{key} is {corridor.get(key)!r}, "
                f"{scene.name} needs {value!r}"
            )
    if (geometry.get("arms") or None) != scene.scenario_geometry_arms:
        problems.append(
            f"orchestrator.yaml scenario_geometry.arms is {geometry.get('arms')!r}, "
            f"{scene.name} needs {scene.scenario_geometry_arms!r}"
        )
    band = config.get("grounding_aisle_x_band_m")
    expected_band = None if scene.aisle_x_band_m is None else list(scene.aisle_x_band_m)
    if (None if band is None else list(band)) != expected_band:
        problems.append(
            f"orchestrator.yaml grounding_aisle_x_band_m is {band!r}, "
            f"{scene.name} needs {expected_band!r}"
        )
    for flag in ("t0_probe_mode", "prompt_static_obstacles"):
        if config.get(flag):
            problems.append(f"orchestrator.yaml {flag} must be false for {scene.name}")
    # Most scenes need an EMPTY zone list (a zone left over from another
    # scene would let Arm B's intersection rule fire on any scene with two
    # stopped robots whose goal axes cross near the centre); a scene that
    # registers its own zones (IB10) needs exactly those instead.
    expected_zones = [dict(z) for z in scene.shadow_classical_zones or ()]
    if (config.get("shadow_classical_zones") or []) != expected_zones:
        problems.append(
            f"orchestrator.yaml shadow_classical_zones is "
            f"{config.get('shadow_classical_zones')!r}, {scene.name} needs {expected_zones!r}"
        )
    # (a0) plan channel (step-7b Part 3): only `junction_clear` needs it on;
    # every other registered scene needs it off (byte-identical v1/v2
    # dispatch path is the regression gate the step-4 equivalence smoke
    # checks, elsewhere).
    if bool(config.get("plan_channel_enabled")) != scene.plan_channel_enabled:
        problems.append(
            f"orchestrator.yaml plan_channel_enabled is "
            f"{config.get('plan_channel_enabled')!r}, {scene.name} needs "
            f"{scene.plan_channel_enabled!r}"
        )
    for field_name, expected in (
        ("junction_recede_offset_m", scene.junction_recede_offset_m),
        ("junction_backup_clearance_m", scene.junction_backup_clearance_m),
        ("junction_recede_stagger_m", scene.junction_recede_stagger_m),
        ("tracked_extent_m", scene.tracked_extent_m),
    ):
        if expected is None:
            continue
        if geometry.get(field_name) != expected:
            problems.append(
                f"orchestrator.yaml scenario_geometry.{field_name} is "
                f"{geometry.get(field_name)!r}, {scene.name} needs {expected!r}"
            )
    rag_path = repo / RAG_RELPATH
    if not rag_path.is_file():
        problems.append(f"missing file {RAG_RELPATH}")
    else:
        rag = yaml.safe_load(rag_path.read_text(encoding="utf-8")) or {}
        mode = (rag.get("grounding") or {}).get("mode", "legacy")
        if mode != scene.grounding_mode:
            problems.append(
                f"config/rag.yaml grounding.mode is {mode!r}; {scene.name} needs "
                f"{scene.grounding_mode!r}"
            )
    return problems


def _check_tasks(scene: SceneSpec, tasks: dict[str, Any]) -> list[str]:
    problems = []
    defaults = {"start_delay_sec": 0.0, "priority": 0}
    for robot_id, expected in scene.initial_tasks.items():
        actual = tasks.get(robot_id)
        if actual is None:
            problems.append(f"orchestrator.yaml initial_tasks lacks {robot_id}")
            continue
        for key in ("task", "goal", "start_delay_sec", "priority"):
            want = expected.get(key, defaults.get(key))
            got = actual.get(key, defaults.get(key))
            if isinstance(got, (list, tuple)):
                got = list(got)
            if got != want:
                problems.append(
                    f"orchestrator.yaml initial_tasks.{robot_id}.{key} is {got!r}, "
                    f"{scene.name} needs {want!r}"
                )
    extra = sorted(set(tasks) - set(scene.initial_tasks))
    if extra:
        problems.append(f"orchestrator.yaml initial_tasks has robots {scene.name} lacks: {extra}")
    return problems


def plan_runs(
    scene: SceneSpec, seeds: list[int], arms: list[str] | None = None
) -> list[dict[str, Any]]:
    """Return the sweep matrix, arms interleaved per seed.

    Args:
        scene: The scene to sweep.
        seeds: Isaac seeds; each arm runs once per seed.
        arms: Arm names to sweep, or None for every arm of the scene.

    Returns:
        One entry per run: scene, arm, strategy, seed, mock and run label.

    Raises:
        ValueError: If an arm is not one of the scene's.
    """
    names = list(scene.arms) if arms is None else arms
    unknown = sorted(set(names) - set(scene.arms))
    if unknown:
        raise ValueError(f"{scene.name} has no arms {unknown}; arms: {sorted(scene.arms)}")
    return [
        {
            "scene": scene.name,
            "arm": arm,
            "strategy": scene.arms[arm].strategy,
            "seed": seed,
            "mock_decision_file": scene.arms[arm].mock_decision_file,
            "label": f"{scene.name}_{arm}_seed{seed}",
        }
        for seed in seeds
        for arm in names
    ]


def cost_table(
    scene: SceneSpec, scores: list[RunScore], min_runs: int = MIN_RUNS_PER_ARM
) -> dict[str, Any]:
    """Build the scene's strategy cost table from scored sweep runs.

    A censored run (a robot never arrived) counts its missing arrivals to the
    episode end, so its arm's cost is a lower bound, as in T2b's margin.

    Args:
        scene: The swept scene.
        scores: Every scored run (`RunScore.arm` names the arm).
        min_runs: Fewest runs an arm needs to enter the table.

    Returns:
        `{"scene", "arms": {arm: {...}}, "best_arm", "best_censored"}`, each
        arm with its strategy, runs, mean total time-to-goal (sim-s),
        censored flag and regret against the best arm.

    Raises:
        ValueError: If a run names an unknown arm, no arm has enough runs, or
            an arm with runs has fewer than `min_runs`.
    """
    by_arm: dict[str, list[RunScore]] = {}
    for score in scores:
        if score.arm not in scene.arms:
            raise ValueError(f"run {score.run_id} names unknown arm {score.arm!r}")
        by_arm.setdefault(score.arm, []).append(score)
    short = {arm: len(runs) for arm, runs in by_arm.items() if len(runs) < min_runs}
    if short or not by_arm:
        raise ValueError(f"arms below {min_runs} runs: {short or 'no runs at all'}")
    arms: dict[str, dict[str, Any]] = {}
    for arm, runs in by_arm.items():
        arms[arm] = {
            "strategy": scene.arms[arm].strategy,
            "roles": [list(_jsonable(r)) for r in scene.arms[arm].roles],
            "n": len(runs),
            "mean_total_sec": round(sum(r.total_sec for r in runs) / len(runs), 3),
            "censored": any(r.censored for r in runs),
            "run_ids": [r.run_id for r in runs],
        }
    # An uncensored arm is preferred as the reference: a censored cost is only
    # a lower bound, so a censored "best" cannot anchor a regret.
    best = min(arms, key=lambda a: (arms[a]["censored"], arms[a]["mean_total_sec"], a))
    for entry in arms.values():
        entry["regret_sec"] = round(entry["mean_total_sec"] - arms[best]["mean_total_sec"], 3)
        entry["regret_is_lower_bound"] = entry["censored"]
    return {
        "scene": scene.name,
        "metric": "total_time_to_goal_sec",
        "arms": arms,
        "best_arm": best,
        "best_censored": arms[best]["censored"],
    }


def _jsonable(roles: Roles) -> list[Any]:
    return [list(part) if isinstance(part, tuple) else part for part in roles]


def _as_roles(value: Any) -> Roles:
    return tuple(tuple(part) if isinstance(part, list) else part for part in value)


def roles_from_command(command: dict[str, Any]) -> Roles | None:
    """Read the executed roles off a grounded coordination command.

    Args:
        command: The decision artifact's `grounded_command`.

    Returns:
        The roles key, or None for a command with no recognisable lead action.
    """
    actions = command.get("actions") or []
    for action in actions:
        if action.get("action") == "yield":
            parameters = action.get("parameters") or {}
            order = parameters.get("crossing_order")
            if not order:
                passer = parameters.get("passer_robot_id")
                order = [] if passer is None else [passer]
            return ("yield", action["robot_id"], tuple(order))
    for action in actions:
        if action.get("action") == "reverse":
            # `junction_clear`'s own phase commands (step-7b Part 3): a plain
            # `reverse` strategy also dispatches this action, but on THIS
            # scene's only registered arms, every `reverse` dispatch is a
            # `junction_clear` phase (the plain-`reverse` strategy has no
            # registered arm here) -- coarse by kind, not by WHICH robot
            # recedes first, since chi order can vary by trigger snapshot
            # while the scene registers only one `junction_clear` arm.
            return ("reverse",)
    for action in actions:
        if action.get("action") == "reroute":
            return ("reroute", action["robot_id"])
    if actions and all(a.get("action") == "temporary_wait" for a in actions):
        return ("temporary_wait", tuple(sorted(a["robot_id"] for a in actions)))
    return None


def roles_from_decision(
    scene: SceneSpec, decision: dict[str, Any], frame_robots: list[dict[str, Any]] | None = None
) -> Roles | None:
    """Derive a decision's executed roles, resolving M3's strategy aliases.

    `convoy` and `priority_override` resolve through `resolve_strategy_alias`
    on the analysed scene (the artifact's `scene` robots, with the registry
    goals M5 attached) or, without one, on the scenario's spawns and goals,
    with the goal-table priorities.

    Args:
        scene: The scene the decision was made in.
        decision: A `CongestionDecision` as JSON.
        frame_robots: The artifact's `scene.robots`, or None.

    Returns:
        The roles key, or None for a decision with no executable mapping.
    """
    from reasoning.rag.command_grounder import resolve_strategy_alias
    from reasoning.vlm.models import CongestionDecision, RobotStateInput, SnapshotFrame

    parsed = CongestionDecision.model_validate(decision)
    if not parsed.congestion_detected:
        return None
    if frame_robots:
        robots = [
            RobotStateInput(robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"],
                            goal=None if r.get("goal") is None else tuple(r["goal"]))
            for r in frame_robots
        ]
    else:
        scenario = yaml.safe_load(
            (REPO_ROOT / scene.scenario_relpath).read_text(encoding="utf-8")
        )
        robots = [
            RobotStateInput(robot_id=r["robot_id"], x=r["spawn"]["x"], y=r["spawn"]["y"],
                            theta=r["spawn"]["yaw_rad"], goal=(r["goal"]["x"], r["goal"]["y"]))
            for r in scenario["robots"]
        ]
    priorities = {rid: t.get("priority", 0) for rid, t in scene.initial_tasks.items()}
    alias = resolve_strategy_alias(
        parsed, SnapshotFrame(stamp=0.0, robots=robots), priorities=priorities
    )
    if alias is not None:
        parsed = alias.decision
    involved = list(parsed.involved_robots)
    if parsed.strategy == "yield":
        yielder = parsed.yield_robot or involved[0]
        order = [r for r in (parsed.crossing_order or involved) if r != yielder]
        return ("yield", yielder, tuple(order))
    if parsed.strategy == "reroute":
        return ("reroute", involved[0])
    if parsed.strategy == "junction_clear":
        # Matches `roles_from_command`'s own coarse-by-kind key (step-7b
        # Part 3): this scene registers only one `junction_clear` arm.
        return ("reverse",)
    if parsed.strategy in ("temporary_wait", "convoy", "priority_override"):
        # An unmapped alias runs as the legacy bounded wait.
        return ("temporary_wait", tuple(sorted(involved)))
    return None


def roles_from_record(scene: SceneSpec, record: dict[str, Any]) -> tuple[Roles | None, str]:
    """Derive the executed roles of a recorded decision.

    Accepts a record carrying the grounded command itself, an M5 decision
    artifact (which records the decision, the analysed scene and M3's yield
    provenance, not the command), or a bare decision.

    Args:
        scene: The scene the decision was made in.
        record: The record.

    Returns:
        The roles key (None when nothing executable maps) and its source.
    """
    command = record.get("grounded_command")
    if command:
        roles = roles_from_command(command)
        if roles is not None:
            return roles, "grounded_command"
    decision = record.get("decision", record)
    if decision is None:
        return None, "decision"
    frame_robots = (record.get("scene") or {}).get("robots")
    roles = roles_from_decision(scene, decision, frame_robots)
    if roles is None or roles[0] != "yield" or "decision" not in record:
        return roles, "decision"
    # M3's provenance in the artifact: a refused yield fans out waits, and a
    # derived yield with an infeasible backup or escort reroutes the yielder.
    if record.get("yield_refusal_reason"):
        involved = decision["involved_robots"]
        return ("temporary_wait", tuple(sorted(involved))), "artifact_refusal"
    tags = record.get("grounding_degradations") or []
    if any(str(tag).startswith("yield=infeasible") for tag in tags):
        return ("reroute", roles[1]), "artifact_degradation"
    if record.get("yield_robot_grounded_from"):
        return roles, "decision_pre_gate"
    return roles, "artifact_decision"


def score_regret(table: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """Score one recorded decision's time regret against the scene's best arm.

    Args:
        table: `cost_table` output.
        record: An M5 decision artifact, a record carrying the grounded
            command, or a bare decision (`roles_from_record`).

    Returns:
        The matched arm (None when the decision executes as no swept arm),
        its regret and whether that regret is a lower bound, the roles it
        was matched by, and the label with its acceptance.
    """
    scene = _scene(table["scene"])
    decision = record.get("decision", record) or {}
    roles, source = roles_from_record(scene, record)
    arm = None
    if roles is not None:
        arm = next(
            (
                name
                for name, spec in scene.arms.items()
                if roles in spec.roles and name in table["arms"]
            ),
            None,
        )
    label = decision.get("strategy") if isinstance(decision, dict) else None
    result: dict[str, Any] = {
        "scene": scene.name,
        "roles": None if roles is None else _jsonable(roles),
        "roles_source": source,
        "arm": arm,
        "label": label,
        "label_accepted": (
            None if scene.accepted_strategies is None else label in scene.accepted_strategies
        ),
        "best_arm": table["best_arm"],
        "regret_sec": None,
        "regret_is_lower_bound": None,
    }
    if arm is not None and not table["best_censored"]:
        entry = table["arms"][arm]
        result["regret_sec"] = entry["regret_sec"]
        result["regret_is_lower_bound"] = bool(entry["censored"])
    elif arm is not None:
        # Every arm was censored, so the reference is itself only a lower
        # bound and no regret is defined.
        result["note"] = "best arm censored: no regret reference"
    return result


def _cmd_scenes(_args: argparse.Namespace) -> int:
    for name, scene in SCENES.items():
        arms = ", ".join(f"{arm} ({spec.strategy})" for arm, spec in scene.arms.items())
        print(f"{name}: {arms}")
    return 0


def _cmd_preflight(args: argparse.Namespace) -> int:
    scene = _scene(args.scene)
    problems = preflight(scene, Path(args.repo))
    for problem in problems:
        print(f"PREFLIGHT FAIL: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"PREFLIGHT OK: {scene.name} files and goal-table row present")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    for run in plan_runs(_scene(args.scene), args.seeds, args.arms):
        if args.tsv:
            print("\t".join(str(run[k]) for k in ("arm", "seed", "mock_decision_file", "label")))
        else:
            print(json.dumps(run))
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    scene = _scene(args.scene)
    scores = []
    for item in args.run:
        arm, _, path = item.partition(":")
        if arm not in scene.arms or not path:
            raise SystemExit(
                f"--run must be <{'|'.join(scene.arms)}>:<ground-truth dir>; got {item!r}"
            )
        scores.append(score_ground_truth(arm, Path(path)))
    table = cost_table(scene, scores, args.min_runs)
    for arm, entry in sorted(table["arms"].items(), key=lambda kv: kv[1]["mean_total_sec"]):
        bound = ">=" if entry["censored"] else "="
        print(f"{arm:14s} {entry['strategy']:15s} n={entry['n']} total{bound}"
              f"{entry['mean_total_sec']:.2f}s regret{bound}{entry['regret_sec']:.2f}s")
    print(f"best={table['best_arm']} best_censored={table['best_censored']}")
    if args.out:
        Path(args.out).write_text(json.dumps(table, indent=2) + "\n", encoding="utf-8")
    return 0


def _cmd_regret(args: argparse.Namespace) -> int:
    table = json.loads(Path(args.table).read_text(encoding="utf-8"))
    record = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    if isinstance(record, list):
        record = record[0]
    print(json.dumps(score_regret(table, record)))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scenes", help="list registered scenes and arms").set_defaults(
        func=_cmd_scenes
    )
    pre = sub.add_parser("preflight", help="refuse unless the tree is set for the scene")
    pre.add_argument("--scene", required=True)
    pre.add_argument("--repo", default=str(REPO_ROOT))
    pre.set_defaults(func=_cmd_preflight)
    plan = sub.add_parser("plan", help="print the sweep matrix")
    plan.add_argument("--scene", required=True)
    plan.add_argument("--seeds", type=int, nargs="+", default=[42, 43])
    plan.add_argument("--arms", nargs="+", default=None)
    plan.add_argument("--tsv", action="store_true", help="arm, seed, mock, label per line")
    plan.set_defaults(func=_cmd_plan)
    score = sub.add_parser("score", help="score sweep runs into the strategy cost table")
    score.add_argument("--scene", required=True)
    score.add_argument("--run", action="append", required=True)
    score.add_argument("--min-runs", type=int, default=MIN_RUNS_PER_ARM)
    score.add_argument("--out")
    score.set_defaults(func=_cmd_score)
    regret = sub.add_parser("regret", help="score a recorded decision's regret")
    regret.add_argument("--table", required=True)
    regret.add_argument("--decision", required=True)
    regret.set_defaults(func=_cmd_regret)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
