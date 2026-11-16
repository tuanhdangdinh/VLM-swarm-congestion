"""Read M3's yield feasibility outcome back off a grounded command.

Pure helpers over a grounded command dict, shared by the live M5 pipeline
(`swarm_orchestrator.reasoning_pipeline` re-exports them) and the offline
option probing in `reasoning.rag.cluster_options`.
"""

from __future__ import annotations

from typing import Any, NamedTuple


class YieldGroundingProvenance(NamedTuple):
    """Where a grounded yield ended up, and why M3 moved or refused it."""

    grounded_from: str | None
    grounded_to: str | None
    regrounded_reason: str | None
    refusal_reason: str | None


def summarize_yield_grounding(command: dict[str, Any] | None) -> YieldGroundingProvenance:
    """Read M3's yield feasibility outcome back off a grounded command.

    The gate leaves its only trace in the command: a swap tags the yield
    action's parameters with `yield_robot_grounded_from`, while a refusal drops
    the yield action altogether and fans out `temporary_wait` actions whose
    `reason` opens with `"yield refused:"`. The prefix test is load-bearing — a
    yield that grounded normally also carries a `reason`, the M2 root cause.

    Args:
        command: The grounded coordination command, or None when grounding
            raised or its output failed schema validation.

    Returns:
        The provenance fields, all None when the feasibility gate did not fire.
    """
    if command is None:
        return YieldGroundingProvenance(None, None, None, None)
    grounded_from: str | None = None
    grounded_to: str | None = None
    regrounded_reason: str | None = None
    refusal_reason: str | None = None
    for action in command.get("actions", []):
        parameters = action.get("parameters") or {}
        if action.get("action") == "yield":
            grounded_to = action.get("robot_id")
            grounded_from = parameters.get("yield_robot_grounded_from")
            regrounded_reason = parameters.get("yield_regrounded_reason")
        reason = parameters.get("reason")
        if (
            refusal_reason is None
            and isinstance(reason, str)
            and reason.startswith("yield refused:")
        ):
            # Fanned out to every involved robot, so only the first is recorded.
            refusal_reason = reason
    return YieldGroundingProvenance(
        grounded_from, grounded_to, regrounded_reason, refusal_reason
    )


# Derived-mode tags `_ground_derived` records before degrading a yield to its
# reroute fallback (`command_grounder._reroute_yielder`); a reroute M2 chose
# itself never carries them.
_YIELD_REROUTE_TAG_PREFIXES = ("retreat=no-valid-candidate", "yield=infeasible:")


def empty_reroute_fallback(command: dict[str, Any] | None) -> str | None:
    """Return why a command is a yield's empty-waypoint reroute fallback.

    When a derived yield has no executable retreat, M3 reroutes the yielder
    with no waypoints and waits the rest (`_reroute_yielder`). With no
    declared detour M4 has nothing to drive: it re-sends a task goal the
    command does not carry, so the reroute completes as a no-op
    (`command_bus_node` returns False), while the waits still cancel the
    robots' Nav2 goals. prereg-v3 A15(iv): `refusal_no_action` withholds it
    like a refusal. The test is "a reroute with no waypoints, every other
    action a wait, and a yield-degradation tag", so a reroute M2 decided
    itself, or one along a declared detour, is never matched.

    Args:
        command: A grounded (or registry-filtered) coordination command.

    Returns:
        The first yield-degradation tag (e.g. `retreat=no-valid-candidate`),
        or None when the command is anything else.
    """
    if command is None:
        return None
    actions = command.get("actions") or []
    reroutes = [action for action in actions if action.get("action") == "reroute"]
    if not reroutes or any(
        action.get("action") not in ("reroute", "temporary_wait") for action in actions
    ):
        return None
    if any((action.get("parameters") or {}).get("waypoints") for action in reroutes):
        return None
    return next(
        (
            tag
            for tag in command.get("degradations") or []
            if isinstance(tag, str) and tag.startswith(_YIELD_REROUTE_TAG_PREFIXES)
        ),
        None,
    )
