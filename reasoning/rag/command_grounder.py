from typing import Any

from jsonschema import Draft202012Validator

from reasoning.schemas import load_schema
from reasoning.vlm.models import ReasonerResult


class CommandGroundingError(ValueError):
    """Raised when a grounded command is incomplete or invalid."""


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


def ground_reasoner_result(result: ReasonerResult) -> dict[str, Any]:
    """Convert a validated VLM decision into an executable coordination command.

    This is a small deterministic bridge until the full retrieval-backed M3
    grounder is restored. yield/reverse emit a bounded backward clearing
    maneuver (the yielding robot reverses to open a blocked aisle), temporary_wait
    cancels Nav2 goals, reroute forwards explicit waypoints when present, and the
    remaining semantic strategies degrade to a temporary wait rather than
    inventing unsafe motion.
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")

    robot_ids = decision.involved_robots
    command_id = f"{result.request_id}-{decision.strategy}"
    duration_sec = 8.0
    # Distance the yielding robot reverses. Sized for the head-on deadlock
    # geometry: robots stop at ~0.3-0.45 m separation inside the aisle. 0.8 m
    # parked the yielder ~0.7 m from the gap's west exit — close enough that
    # its inflated footprint forced the passer into a tight S-curve right at
    # the 0.55 m gap mouth, and DWB stalled in "Failed to make progress"
    # loops without moving (observed 2026-07-03 run 4). 1.3 m parks it ~1.2 m
    # clear of the exit: the passer gets a straight run out of the gap and a
    # gentle arc past the yielder at >0.55 m separation (above the 0.45 m
    # safety latch threshold).
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
    # ~0.01 m/s creep, H3 runs 4-7). Distance sized so the hold only ends
    # once the passer is fully PAST the parked yielder's x with margin: from
    # hold start (~x=+0.25) past the yielder (backup 1.3 m parks it near
    # x=-1.65) plus the 0.45 m safety radius ≈ 2.35 m. Ending earlier would
    # make the resuming yielder cross the still-approaching passer at
    # <0.45 m lateral separation and latch both. 24+ sim-s at 0.1 m/s fits
    # the 45 sim-s hold backstop.
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
        yield_parameters: dict[str, Any] = {
            "backup_distance_m": backup_distance_m,
            "hold_sec": yield_hold_sec,
            "pull_off_lateral_m": pull_off_lateral_m,
            "reason": decision.root_cause,
        }
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
