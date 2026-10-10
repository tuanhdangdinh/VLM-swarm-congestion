import json
import math
import re
from collections.abc import Sequence
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


def echo_select(robots: Sequence[EchoRobot]) -> list[str]:
    """The robots an echo decision names, yielder first.

    prereg-v3 A20(3), apparatus only. Before A20 the echo named every stalled
    robot in presentation order and made the first one the yielder, so a
    robot merely dwelling on its task node (latch-free, often far from the
    conflict) was the yielder in 82/400 S1b Monte Carlo first conflicts.
    The trigger's robot set never reaches the prompt, and neither does the
    latch state; the echo stands in for it with a heuristic on what the
    structured state block does show:

    1. An ENGAGED LATCH PAIR is two stalled robots whose centres are closer
       than `ECHO_LATCH_RADIUS_M`. When there is one, the echo names the
       CLOSEST pair's two members only (prereg-v3 A21: one cluster, not every
       latched robot), the presentation-first member as the yielder (ties:
       presentation order of the pair).
    2. Otherwise the pre-A20 rule: every stalled robot in presentation order,
       the first one the yielder; every listed robot when none is stalled.

    Args:
        robots: The state block's robots in presentation order.

    Returns:
        Robot ids, yielder first.
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
    if not pairs:
        return [robot.robot_id for robot in stalled] or [robot.robot_id for robot in robots]
    # A21: ONE cluster, the closest pair's two members only. Naming every
    # latched robot (A20(3)) let the view's node-handoff search move the
    # yield into a second cluster (S1b pilot 2, E3: all 9 dispatches).
    _, i, j = min(pairs)
    return [stalled[i].robot_id, stalled[j].robot_id]


def echo_involved_robots(payload: PromptPayload) -> list[str]:
    """The robots an echo decision names, read off the prompt's state block.

    The trigger's robot set never reaches the request or the prompt text (M5
    uses it only to crop the zoom tile), so the echo stands in for it with
    the robots the structured state block reports as not moving: status
    STOPPED, SLOW or STALE (a robot without a status counts as not moving),
    preferring the members of an engaged latch pair (`echo_select`). Order is
    the block's, which is the request's presentation order
    (`known_robot_ids`), never the registry's, except that the yielder comes
    first.

    Args:
        payload: The rendered prompt.

    Returns:
        The robots `echo_select` names, yielder first.
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
    return echo_select(robots)


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

    def decision_for(self, payload: PromptPayload) -> dict[str, object]:
        """Build the echo decision object for one prompt (before JSON encoding)."""
        involved = echo_involved_robots(payload)
        decision: dict[str, object] = {
            "congestion_detected": True,
            "type": self._type,
            "involved_robots": involved,
            "root_cause": "echo-mock apparatus: stalled robots named from the state block.",
            "strategy": self._strategy,
            "justification": "echo-mock apparatus (A12(i)); not a model decision.",
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
