"""Computed yield-feasibility oracle for the head-on asymmetric scenario family.

Derives, from the same scene-geometry functions M3 uses to ground yield
maneuvers, which robot must yield in a given `HeadOnAsymmetricParams`
variant. This keeps the pre-registered oracle answer and the executed
maneuver defined against one shared geometry, rather than two independent
guesses that can silently drift apart.
"""
from pathlib import Path
from typing import Literal

import yaml

from isaac.vgu_sim.config import HeadOnAsymmetricParams, OracleConfig
from reasoning.rag.scene_geometry import (
    SceneGeometry,
    required_room_m,
    room_is_feasible,
)

SPAWN_OFFSET_M: float = 0.5
BOX_LENGTH_M: float = 0.3
SIDE_ROBOT: dict[str, str] = {"west": "robot_1", "east": "robot_2"}


def load_scene_geometry(orchestrator_yaml: Path) -> SceneGeometry:
    """Load the M5 scene-geometry block from the orchestrator config.

    Args:
        orchestrator_yaml: Path to `orchestrator.yaml`.

    Returns:
        The declared scene geometry, validated.
    """
    data = yaml.safe_load(orchestrator_yaml.read_text())["scenario_geometry"]
    return SceneGeometry.model_validate(data)


def room_from_mouth_m(blocker_m: float | None) -> float | None:
    """Room left between the corridor mouth and a parked blocker, if any.

    Args:
        blocker_m: Distance of the blocker behind the spawn point, or `None`
            when that side has no blocker.

    Returns:
        Room in meters from the corridor mouth, or `None` when there is no
        blocker on this side.
    """
    if blocker_m is None:
        return None
    return SPAWN_OFFSET_M + blocker_m


def side_feasible(blocker_m: float | None, geometry: SceneGeometry) -> bool:
    """Whether a robot on this side can still complete the park maneuver.

    Args:
        blocker_m: Distance of the blocker behind the spawn point, or `None`
            when that side has no blocker.
        geometry: Declared scene geometry.

    Returns:
        True when the side is open, or the blocker leaves enough room.
    """
    return room_is_feasible(room_from_mouth_m(blocker_m), geometry)


# The recorded correct yielder when both sides can park (T1, wopen_eopen).
# It was once derived from the FCFS tiebreak under the robot_1 reading; the
# 2026-09-29 fcfs_yielder correction changes the fact, not this answer, which
# only an owner decision may change. T1 is geometry-sufficient: Arm B's own
# answer is its scoring reference (unified scene design, oracle conventions).
SIDE_ROBOT_BOTH_FEASIBLE_YIELDER: str = "robot_1"


def fcfs_yielder(arrival_offset_m: float) -> str:
    """The robot Arm B's first-come-first-served rule picks to yield.

    Arm B orders a head-on pair by arrival, then by commitment, then by
    robot id, and yields the last (`classical_reasoner._passing_order`). An
    equal-speed standoff is always a full tie (unified scene design, B2
    section), which the id tie-break resolves as robot_1 first, robot_2
    yielding (`test_decide_head_on_breaks_full_tie_by_robot_id`). Before
    2026-09-29 this returned robot_1 for a tie, the opposite reading;
    corrected as a recorded fact (amendments item 28), not an oracle change.

    Args:
        arrival_offset_m: How much later robot_2 arrives at the corridor
            relative to robot_1, in meters of travel; `0.0` is a tie.

    Returns:
        `"robot_2"` when it arrives later or ties, otherwise `"robot_1"`.
    """
    return "robot_2" if arrival_offset_m >= 0 else "robot_1"


def blocker_center_x_m(
    side: Literal["west", "east"],
    blocker_m: float,
    arrival_offset_m: float,
    geometry: SceneGeometry,
) -> float:
    """World-frame x-coordinate of a blocker box's center.

    Args:
        side: Which side of the corridor the blocker sits on.
        blocker_m: Distance of the blocker behind the spawn point.
        arrival_offset_m: Extra spawn offset applied on the east side only.
        geometry: Declared scene geometry.

    Returns:
        The blocker's center x-coordinate in meters.

    Raises:
        ValueError: If `side` is not `"west"` or `"east"`.
    """
    h = geometry.corridor.half_length_m
    if side == "west":
        return -(h + SPAWN_OFFSET_M + blocker_m + BOX_LENGTH_M / 2)
    if side == "east":
        return h + SPAWN_OFFSET_M + arrival_offset_m + blocker_m + BOX_LENGTH_M / 2
    raise ValueError(f"side must be 'west' or 'east'; got {side!r}")


def compute_oracle(
    params: HeadOnAsymmetricParams, geometry: SceneGeometry
) -> OracleConfig | None:
    """Compute the pre-registered yield oracle for a head-on asymmetric variant.

    Args:
        params: The scenario's blocker and arrival-offset parameters.
        geometry: Declared scene geometry.

    Returns:
        The oracle decision, or `None` when neither side can park (no
        feasible yielder exists).
    """
    west_feasible = side_feasible(params.blocker_west_m, geometry)
    east_feasible = side_feasible(params.blocker_east_m, geometry)
    fcfs = fcfs_yielder(params.arrival_offset_m)
    req = required_room_m(geometry)

    if not west_feasible and not east_feasible:
        return None

    if west_feasible and east_feasible:
        rationale = (
            f"both sides can park (required room {req:.2f} m); the recorded "
            f"answer is {SIDE_ROBOT_BOTH_FEASIBLE_YIELDER} (Arm B's FCFS full "
            f"tie yields {fcfs})"
        )
        return OracleConfig(
            correct_yielder=SIDE_ROBOT_BOTH_FEASIBLE_YIELDER,
            fcfs_yielder=fcfs,
            feasible_yielders=("robot_1", "robot_2"),
            rationale=rationale,
        )

    if not west_feasible:
        infeasible_side, blocker_m = "west", params.blocker_west_m
    else:
        infeasible_side, blocker_m = "east", params.blocker_east_m
    assert blocker_m is not None  # side_feasible(None, ...) is always True

    feasible_side = "east" if infeasible_side == "west" else "west"
    infeasible_robot = SIDE_ROBOT[infeasible_side]
    correct = SIDE_ROBOT[feasible_side]
    room = room_from_mouth_m(blocker_m)
    rationale = (
        f"{infeasible_side} blocker {blocker_m:.2f} m behind the spawn leaves "
        f"{room:.2f} m from the mouth < {req:.2f} m required; "
        f"{infeasible_robot} cannot park"
    )
    return OracleConfig(
        correct_yielder=correct,
        fcfs_yielder=fcfs,
        feasible_yielders=(correct,),
        rationale=rationale,
    )
