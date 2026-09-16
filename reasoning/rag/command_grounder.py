from typing import Any

from jsonschema import Draft202012Validator

from reasoning.schemas import load_schema
from reasoning.vlm.models import ReasonerResult


class CommandGroundingError(ValueError):
    """Raised when a grounded command is incomplete or invalid."""


# Absolute map x the yielder parks at. The head_on_deadlock barrier blocks are
# 0.90 m tall and span x in [-1, 1]; the overhead camera sits at (0, 0, 3), so
# a block's top face (z = 0.9) projects onto the marker plane (z = 0.21) out
# to |x| ~= 1.0*(3-0.21)/(3-0.9) ~= 1.33. Add the 0.06 m marker half-width and
# a 0.3 m margin for odometry error after the reverse/sidestep leg: 1.33 +
# 0.06 + 0.3 ~= 1.69, rounded up to 1.8. 1.5 left only ~0.11 m of clearance
# and lost the marker in a live run (2026-09-16 run 7).
PARK_ABS_X_M = 1.8
# Bounds on the derived backup leg: under 0.3 m the reverse does not open the
# aisle at all, and 2.5 m is the longest run that stays inside the mapped aisle.
MIN_BACKUP_M = 0.3
MAX_BACKUP_M = 2.5
# Added to the passer's distance-to-park so the hold only ends once the passer
# is clear of the parked yielder: 0.45 m safety radius (M4 min_distance_m) plus
# a 0.20 m margin.
PASSER_CLEARANCE_M = 0.65
# Bounds on the derived escort leg. The upper bound must stay under what the
# 45 s hold backstop covers at the 0.1 m/s escort speed (4.5 m), otherwise the
# hold would expire mid-escort and both robots would re-enter the aisle.
MIN_ESCORT_M = 0.5
MAX_ESCORT_M = 4.0


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def validate_coordination_command(command: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema("coordination_command")
    errors = sorted(Draft202012Validator(schema).iter_errors(command), key=str)
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise CommandGroundingError(f"Command failed schema validation: {messages}")
    return command


def filter_command_robot_ids(
    command: dict[str, Any], allowed_robot_ids: set[str] | None
) -> dict[str, Any]:
    """Drop grounded actions for robots absent from the current scene snapshot."""
    if allowed_robot_ids is None:
        return command

    actions = [
        action for action in command.get("actions", []) if action.get("robot_id") in allowed_robot_ids
    ]
    if not actions:
        raise CommandGroundingError(
            "Command contains no actions for known robots: "
            f"allowed={sorted(allowed_robot_ids)}"
        )
    return {**command, "actions": actions}


def ground_reasoner_result(
    result: ReasonerResult,
    robot_positions: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Convert a validated VLM decision into an executable coordination command.

    This is a small deterministic bridge until the full retrieval-backed M3
    grounder is restored. yield/reverse emit a bounded backward clearing
    maneuver (the yielding robot reverses to open a blocked aisle), temporary_wait
    cancels Nav2 goals, reroute forwards explicit waypoints when present, and the
    remaining semantic strategies degrade to a temporary wait rather than
    inventing unsafe motion.

    When `robot_positions` carries both yield participants, the yield distances
    are derived from where the robots actually are instead of the legacy
    constants sized for one assumed standoff pose. Deadlock onset is bimodal in
    this scenario — a nose-to-nose standoff near x=0 or a planner stall at ~1 m
    separation (observed 2026-09-16) — and fixed distances cannot suit both.

    Args:
        result: Validated M2 reasoner output whose decision is grounded.
        robot_positions: Optional map of robot_id to world-frame `(x, y)` in
            metres, from the M5 scene snapshot. When it covers both the yielder
            and the passer, yield distances are scene-derived; otherwise the
            legacy fixed distances are used.

    Returns:
        Schema-validated coordination command dict.

    Raises:
        CommandGroundingError: If the decision is empty, reports no congestion,
            or names an unsupported strategy, or if the built command fails
            schema validation.
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")

    robot_ids = decision.involved_robots
    command_id = f"{result.request_id}-{decision.strategy}"
    duration_sec = 8.0
    # Fallback distance the yielding robot reverses, used when the caller
    # supplies no positions (and by `reverse`, which has no park target). Sized
    # for a nose-to-nose standoff near x=0: robots stop at ~0.3-0.45 m
    # separation inside the aisle, and 0.8 m parked the yielder only ~0.7 m from
    # the gap's west exit — close enough that its inflated footprint forced the
    # passer into a tight S-curve right at the 0.55 m gap mouth, where DWB
    # stalled in "Failed to make progress" loops (observed 2026-07-03 run 4).
    # 1.3 m parks it ~1.2 m clear of that exit. The scene-aware path below
    # replaces this with |yielder_x - park_x|.
    backup_distance_m = 1.3
    # A straight backup alone re-deadlocks this scenario: the yielder stays on
    # the passer's line, and with min_distance_m=0.45 in the 1.2 m aisle the
    # passer cannot clear a centerline-parked yielder without tripping the
    # safety latch. The yielder therefore steps laterally off the centerline.
    # Expressed as a robot-frame lateral offset (positive = left), not an
    # absolute map pose: in head_on_deadlock.yaml both robots face each other
    # along x, so "step left" moves them to opposite sides of the aisle
    # regardless of which robot yields — no per-robot table or TF needed.
    # M4 executes it as a raw-cmd_vel turn-drive-turn (Nav2Adapter.sidestep);
    # the Nav2-planned pull-off it replaces stalled in DWB recovery loops
    # once motion BVH let the costmap see the other robot (2026-07-03).
    # 0.35 m keeps the yielder inside the wall clearance (aisle half-width
    # 0.6 m, inflated half-width ~0.19 m) while giving the passer 0.7 m of
    # centerline separation, above the 0.45 m safety threshold.
    pull_off_lateral_m = 0.35
    # Upper-bound backstop for the yielder's hold, not the primary release:
    # M4 ends the hold the moment the passer's odometry shows it displaced
    # passer_clear_m since hold start (event-driven). A fixed 12 s hold
    # expired mid-traverse at low realtime factors and both robots re-entered
    # the aisle together (2026-07-03). 45 s covers a slow traverse with wide
    # margin; only reached if the passer never moves.
    yield_hold_sec = 45.0
    # The passer is DRIVEN through the gap by M4's raw-cmd_vel escort during
    # the hold (DWB could not transit the gap even with a widened free band —
    # ~0.01 m/s creep, H3 runs 4-7). The hold must only end once the passer is
    # fully PAST the parked yielder's x with margin, or the resuming yielder
    # crosses the still-approaching passer at <0.45 m separation and latches
    # both. These fallback values assume that same x=0 standoff (passer at
    # ~+0.25, yielder parked near x=-1.65, plus the 0.45 m safety radius);
    # the scene-aware path below replaces them with
    # |passer_x - park_x| + PASSER_CLEARANCE_M.
    passer_clear_m = 2.4
    passer_escort_distance_m = 2.4
    # Generous safety upper bound, not a motion-duration estimate (which was
    # wrong at any Isaac Sim realtime factor != 1). In the normal path the M4
    # command bus releases this wait the instant the linked yield reaches a
    # terminal status (event-driven); this constant is only reached if that
    # terminal-status signal is lost.
    passing_wait_sec = 120.0
    # Generous safety upper bound for the full yield cycle, used as
    # expected_resolution_time_sec. With M5 no longer expiring commands whose
    # robots are ACTIVE, this only bounds the PENDING/lost-dispatch case.
    yield_total_sec = 150.0

    if decision.strategy == "yield":
        park_x: float | None = None
        if len(robot_ids) > 1 and robot_positions is not None:
            yielder_position = robot_positions.get(robot_ids[0])
            passer_position = robot_positions.get(robot_ids[1])
            if yielder_position is not None and passer_position is not None:
                yielder_x = yielder_position[0]
                passer_x = passer_position[0]
                # Park on the yielder's own side of the corridor, away from the
                # passer, so the two never swap sides mid-maneuver.
                park_x = -PARK_ABS_X_M if yielder_x < passer_x else PARK_ABS_X_M
                already_parked = yielder_x <= park_x if park_x < 0 else yielder_x >= park_x
                # A yielder already past the park point must not reverse
                # further away from the aisle; MIN_BACKUP_M is just enough of a
                # nudge for M4's reverse leg to report progress.
                backup_distance_m = (
                    MIN_BACKUP_M
                    if already_parked
                    else round(_clamp(abs(yielder_x - park_x), MIN_BACKUP_M, MAX_BACKUP_M), 3)
                )
                escort_m = round(
                    _clamp(
                        abs(passer_x - park_x) + PASSER_CLEARANCE_M,
                        MIN_ESCORT_M,
                        MAX_ESCORT_M,
                    ),
                    3,
                )
                passer_clear_m = escort_m
                passer_escort_distance_m = escort_m
        yield_parameters: dict[str, Any] = {
            "backup_distance_m": backup_distance_m,
            "hold_sec": yield_hold_sec,
            "pull_off_lateral_m": pull_off_lateral_m,
            "reason": decision.root_cause,
        }
        if park_x is not None:
            # Traceability only: M4 derives the backup from backup_distance_m
            # and reads parameters with .get, so the extra key is inert there.
            yield_parameters["park_x_m"] = park_x
        if len(robot_ids) > 1:
            yield_parameters["passer_robot_id"] = robot_ids[1]
            yield_parameters["passer_clear_m"] = passer_clear_m
            yield_parameters["passer_escort_distance_m"] = passer_escort_distance_m
        actions = [
            {
                "robot_id": robot_ids[0],
                "action": "yield",
                "parameters": yield_parameters,
            },
        ]
        if len(robot_ids) > 1:
            # Suppress the passing robot so M5 does not dispatch a competing
            # command while the aisle is still blocked. The M4 command bus
            # releases this wait the moment the linked yield reaches a
            # terminal status (event-driven); passing_wait_sec only bounds
            # the case where that release signal is lost.
            actions.append(
                {
                    "robot_id": robot_ids[1],
                    "action": "temporary_wait",
                    "parameters": {"duration_sec": passing_wait_sec},
                }
            )
    elif decision.strategy == "reverse":
        actions = [
            {
                "robot_id": robot_id,
                "action": "reverse",
                "parameters": {
                    "backup_distance_m": backup_distance_m,
                },
            }
            for robot_id in robot_ids
        ]
    elif decision.strategy == "temporary_wait":
        actions = [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {"duration_sec": duration_sec},
            }
            for robot_id in robot_ids
        ]
    elif decision.strategy == "reroute":
        # Asymmetric: first robot navigates, remaining robots wait long enough
        # for it to clear the contested zone. Sending all robots simultaneously
        # causes them to approach each other and re-collide immediately.
        clearance_wait_sec = 15.0
        actions = [
            {
                "robot_id": robot_ids[0],
                "action": "reroute",
                "parameters": {"waypoints": []},
            }
        ] + [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {"duration_sec": clearance_wait_sec},
            }
            for robot_id in robot_ids[1:]
        ]
    elif decision.strategy in {"convoy", "priority_override"}:
        actions = [
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {
                    "duration_sec": duration_sec,
                    "requested_strategy": decision.strategy,
                },
            }
            for robot_id in robot_ids
        ]
    else:
        raise CommandGroundingError(f"unsupported strategy: {decision.strategy}")

    resolution_sec = yield_total_sec if decision.strategy == "yield" else duration_sec
    return validate_coordination_command(
        {
            "command_id": command_id,
            "actions": actions,
            "expected_resolution_time_sec": resolution_sec,
            "fallback": "stop",
        }
    )
