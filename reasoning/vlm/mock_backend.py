import json
import math
import re
from collections.abc import Collection, Sequence
from typing import NamedTuple

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

_DEFAULT_RESPONSE = (
    '{"congestion_detected": false, "type": "none", "involved_robots": [], '
    '"root_cause": "No congestion detected.", "strategy": "none", '
    '"justification": "Scene is clear."}'
)


class MockBackend:
    """Deterministic VLM backend for offline tests.

    Returns a fixed response, a default no-congestion decision, or a scripted
    sequence (holding the last entry once exhausted). Records the most recent
    payload and config for assertions.
    """

    def __init__(
        self,
        response_text: str | None = None,
        backend_id: str = "mock",
        latency_ms: int = 0,
        response_sequence: list[str] | None = None,
    ) -> None:
        self._response_text = response_text
        self._backend_id = backend_id
        self._latency_ms = latency_ms
        self._sequence = list(response_sequence) if response_sequence else None
        self._index = 0
        self.last_payload: PromptPayload | None = None
        self.last_config: ReasonerConfig | None = None

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return a canned response and record the inputs."""
        self.last_payload = payload
        self.last_config = config
        if self._sequence is not None:
            text = self._sequence[min(self._index, len(self._sequence) - 1)]
            self._index += 1
        elif self._response_text is not None:
            text = self._response_text
        else:
            text = _DEFAULT_RESPONSE
        return BackendResponse(
            text=text,
            backend_id=self._backend_id,
            latency_ms=self._latency_ms,
        )


# The structured state line every prompt version renders per robot
# (`prompt_builder.format_robot_state_lines`, frozen v1/v2 copies alike);
# plan-state, failure-context and pairwise lines never carry `robot_id=`.
_STATE_LINE = re.compile(r"^\s*-\s*robot_id=(?P<robot_id>[^,\s]+),(?P<rest>.*)$")
_STATUS_FIELD = re.compile(r"\bstatus=(?P<status>[A-Za-z_]+)")
# M1 statuses that mean "not making way": the echo names these robots.
_NOT_MOVING = frozenset({"STOPPED", "SLOW", "STALE"})
ECHO_MOCK_MODE = "echo"


_COORD_FIELD = re.compile(r"\b(?P<axis>[xy])=(?P<value>-?[0-9.]+)")
# prereg-v3 A20(3): M4's min-distance latch radius (swarm_execution
# config/safety.yaml `min_distance_m`, = M3's `robot.safety_radius_m`). Two
# robots closer than this are held by an engaged latch. The prompt carries no
# latch state, so the echo reads it off the state block's coordinates
# (rounded to 0.01 m there, an error far below the 0.29-0.44 m live latch gaps).
ECHO_LATCH_RADIUS_M = 0.45


class EchoRobot(NamedTuple):
    """One robot as the echo reads it off the prompt's state block."""

    robot_id: str
    x: float | None
    y: float | None
    stalled: bool


class EchoSelection(NamedTuple):
    """What the echo names for one prompt, and which rule named it."""

    robot_ids: list[str]
    # "closest_pair" (A21), "rotated_pair" (A22: the closest pair not yet
    # refused this epoch), "all_refused_fallback" (A22: every engaged pair
    # refused, the pre-A20 all-stalled rule), or "no_engaged_pair" (pre-A20).
    rule: str
    refused_skipped: int


def echo_engaged_pairs(robots: Sequence[EchoRobot]) -> list[tuple[str, str]]:
    """Every engaged latch pair, in the echo's deterministic naming order.

    An engaged pair is two stalled robots whose centres are closer than
    `ECHO_LATCH_RADIUS_M`. Order: closest first; ties by the presentation
    index of the pair's first member, then of its second. Each pair is
    returned presentation-first.

    Args:
        robots: The state block's robots in presentation order.

    Returns:
        The engaged pairs as `(first, second)` robot ids.
    """
    stalled = [robot for robot in robots if robot.stalled]
    pairs: list[tuple[float, int, int]] = []
    for i, first in enumerate(stalled):
        for j in range(i + 1, len(stalled)):
            second = stalled[j]
            if None in (first.x, first.y, second.x, second.y):
                continue
            distance = math.hypot(first.x - second.x, first.y - second.y)
            if distance < ECHO_LATCH_RADIUS_M:
                pairs.append((distance, i, j))
    return [(stalled[i].robot_id, stalled[j].robot_id) for _, i, j in sorted(pairs)]


def echo_selection(
    robots: Sequence[EchoRobot], refused_pairs: Collection[frozenset[str]] = ()
) -> EchoSelection:
    """The robots an echo decision names, yielder first, with the rule that named them.

    prereg-v3 A20(3)/A21/A22, apparatus only. Before A20 the echo named every
    stalled robot in presentation order and made the first one the yielder,
    so a robot merely dwelling on its task node (latch-free, often far from
    the conflict) was the yielder in 82/400 S1b Monte Carlo first conflicts.
    The trigger's robot set never reaches the prompt, and neither does the
    latch state; the echo stands in for it with a heuristic on what the
    structured state block does show:

    1. When there is an ENGAGED LATCH PAIR (`echo_engaged_pairs`), the echo
       names ONE pair's two members (A21: one cluster, not every latched
       robot), the presentation-first member as the yielder: the first pair
       in `echo_engaged_pairs` order that is not in `refused_pairs` (A22
       rotation; with nothing refused this is the closest pair, A21).
    2. When every engaged pair is in `refused_pairs` (A22), or there is no
       engaged pair, the pre-A20 rule: every stalled robot in presentation
       order, the first one the yielder; every listed robot when none is
       stalled.

    Args:
        robots: The state block's robots in presentation order.
        refused_pairs: Pairs (robot-id sets, never presentation indices, so
            the memory survives a presentation-order change) already refused
            in the current epoch (`EchoMockBackend.note_dispatch_outcome`).

    Returns:
        The named robot ids and the rule that named them.
    """
    stalled = [robot.robot_id for robot in robots if robot.stalled]
    fallback = stalled or [robot.robot_id for robot in robots]
    pairs = echo_engaged_pairs(robots)
    if not pairs:
        return EchoSelection(fallback, "no_engaged_pair", 0)
    refused = {frozenset(pair) for pair in refused_pairs}
    for skipped, pair in enumerate(pairs):
        if frozenset(pair) not in refused:
            # A21: ONE cluster. Naming every latched robot (A20(3)) let the
            # view's node-handoff search move the yield into a second
            # cluster (S1b pilot 2, E3: all 9 dispatches).
            rule = "closest_pair" if skipped == 0 else "rotated_pair"
            return EchoSelection(list(pair), rule, skipped)
    # A22: every engaged pair was refused once this epoch; the all-stalled
    # rule lets the view search the whole scene so it can still progress.
    return EchoSelection(fallback, "all_refused_fallback", len(pairs))


def echo_select(
    robots: Sequence[EchoRobot], refused_pairs: Collection[frozenset[str]] = ()
) -> list[str]:
    """The robots an echo decision names, yielder first (`echo_selection`).

    Args:
        robots: The state block's robots in presentation order.
        refused_pairs: Pairs already refused in the current epoch; empty
            (the default, and every stateless caller such as the MC replay)
            names exactly what the A21 echo named.

    Returns:
        Robot ids, yielder first.
    """
    return echo_selection(robots, refused_pairs).robot_ids


def echo_state_robots(payload: PromptPayload) -> list[EchoRobot]:
    """The prompt's state-block robots as the echo reads them, in presentation order.

    A robot without a status counts as not moving (stalled).

    Args:
        payload: The rendered prompt.

    Returns:
        One `EchoRobot` per known robot in the state block.
    """
    known = set(payload.known_robot_ids)
    robots: list[EchoRobot] = []
    for line in payload.user_prompt.splitlines():
        match = _STATE_LINE.match(line)
        if match is None or match["robot_id"] not in known:
            continue
        if any(robot.robot_id == match["robot_id"] for robot in robots):
            continue
        status = _STATUS_FIELD.search(match["rest"])
        coords = {m["axis"]: float(m["value"]) for m in _COORD_FIELD.finditer(match["rest"])}
        robots.append(
            EchoRobot(
                robot_id=match["robot_id"],
                x=coords.get("x"),
                y=coords.get("y"),
                stalled=status is None or status["status"].upper() in _NOT_MOVING,
            )
        )
    return robots


def echo_involved_robots(
    payload: PromptPayload, refused_pairs: Collection[frozenset[str]] = ()
) -> list[str]:
    """The robots an echo decision names, read off the prompt's state block.

    The trigger's robot set never reaches the request or the prompt text (M5
    uses it only to crop the zoom tile), so the echo stands in for it with
    the robots the structured state block reports as not moving: status
    STOPPED, SLOW or STALE (a robot without a status counts as not moving),
    preferring the members of an engaged latch pair (`echo_selection`). Order
    is the block's, which is the request's presentation order
    (`known_robot_ids`), never the registry's, except that the yielder comes
    first.

    Args:
        payload: The rendered prompt.
        refused_pairs: Pairs already refused in the current epoch (A22).

    Returns:
        The robots `echo_selection` names, yielder first.
    """
    return echo_select(echo_state_robots(payload), refused_pairs)


class EchoMockBackend:
    """Apparatus-only mock that names the prompt's stalled robots in its decision.

    prereg-v3 A12(i): the default mock answers no-congestion, so a mock
    episode never reaches M3; a fixed scripted decision cannot match emergent
    stalls. The echo builds a congestion decision from each request instead
    (`echo_involved_robots`), with a configured type and strategy, so M3's
    grounding runs end to end without an API. It is never a scored arm:
    `backend_id` stays "mock" and every response carries
    `raw["mock_mode"] = "echo"`, which the reasoner records in the
    artifact's diagnostics.
    """

    def __init__(
        self,
        decision_type: str = "deadlock",
        strategy: str = "yield",
        backend_id: str = "mock",
    ) -> None:
        self._type = decision_type
        self._strategy = strategy
        self._backend_id = backend_id
        self.last_payload: PromptPayload | None = None
        self.last_config: ReasonerConfig | None = None
        # prereg-v3 A22 rotation memory (see `note_dispatch_outcome`).
        self._refused_pairs: set[frozenset[str]] = set()
        self._last_named: frozenset[str] | None = None

    @property
    def refused_pairs(self) -> frozenset[frozenset[str]]:
        """The pairs refused in the current epoch (A22), as robot-id sets."""
        return frozenset(self._refused_pairs)

    def note_dispatch_outcome(self, refused: bool, dispatched: bool) -> None:
        """Record what M5 did with the echo's last decision (prereg-v3 A22).

        Apparatus only; no live backend has this hook, so M5's call is a
        no-op on every scored arm. S1b E5 showed the one-cluster echo
        STARVING: it re-named the same unresolvable closest pair after every
        refusal while the second cluster was never analysed. So:

        * REFUSED (M5 withheld the dispatch: `dispatch_withheld` set, e.g.
          `refusal_no_action` or `empty_reroute`): the robots the echo last
          named join the epoch's refused set, and the next analysis names the
          next engaged pair (`echo_selection`).
        * DISPATCHED (a command was published): the EPOCH ENDS and the
          refused set clears. A dispatch is the only epoch boundary. The
          suppression reference also resets on a trigger-set change or pose
          drift, but every E5 re-analysis came through such a reset, so an
          epoch tied to the reference would never rotate.
        * Anything else (no decision, no command, dispatch-suppressed runs)
          leaves the memory as it is.

        Args:
            refused: M5 withheld the last decision's dispatch.
            dispatched: M5 published the last decision's command.
        """
        if refused:
            if self._last_named is not None:
                self._refused_pairs.add(self._last_named)
        elif dispatched:
            self._refused_pairs.clear()
        self._last_named = None

    def decision_for(self, payload: PromptPayload) -> dict[str, object]:
        """Build the echo decision object for one prompt (before JSON encoding)."""
        selection = echo_selection(echo_state_robots(payload), self._refused_pairs)
        involved = selection.robot_ids
        self._last_named = frozenset(involved) if involved else None
        justification = "echo-mock apparatus (A12(i)); not a model decision."
        if selection.rule in ("rotated_pair", "all_refused_fallback"):
            justification += (
                f" A22 rotation: {selection.rule}, {selection.refused_skipped} engaged "
                "pair(s) refused this epoch skipped."
            )
        decision: dict[str, object] = {
            "congestion_detected": True,
            "type": self._type,
            "involved_robots": involved,
            "root_cause": "echo-mock apparatus: stalled robots named from the state block.",
            "strategy": self._strategy,
            "justification": justification,
        }
        if self._strategy == "yield" and involved:
            decision["yield_robot"] = involved[0]
        return decision

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Return the echo decision for `payload` and record the inputs."""
        self.last_payload = payload
        self.last_config = config
        return BackendResponse(
            text=json.dumps(self.decision_for(payload)),
            backend_id=self._backend_id,
            latency_ms=0,
            raw={"mock_mode": ECHO_MOCK_MODE},
        )
