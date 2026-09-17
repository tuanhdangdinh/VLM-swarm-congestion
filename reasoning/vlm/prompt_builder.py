import json
import math

from reasoning.vlm.models import FailureContext, PromptPayload, ReasonerRequest, RobotStateInput

# "faces" = the robot's heading is within 60° of the direction to the other robot.
# Opposite headings alone cannot tell head-on from diverging; the VLM misread two
# robots driving apart as a deadlock when only |Δθ| ≈ π was offered (run 3, 2026-09-17).
_FACING_COS = 0.5
_PAIRWISE_GEOMETRY_HEADER = (
    "Pairwise geometry (faces = heading within 60° of the direction to the other robot):"
)

# Cosmos Reason 2 is a chain-of-thought reasoning VLM built on Qwen3-VL. NVIDIA's
# prompt guide specifies a minimal system prompt ("we are more aligned with Qwen's
# use of system prompt ... different from Reason 1, where the system prompt was
# heavily used") and prompt-driven structured output. The task framing therefore
# lives in the user prompt, and the image is placed before the text by the backend.
# Ref: https://nvidia-cosmos.github.io/cosmos-cookbook/getting_started/prompt_guide/reason_guide.html
SYSTEM_PROMPT = "You are a helpful assistant."

_USER_TEMPLATE = """You are a warehouse swarm robotics traffic controller. Analyze the \
overhead camera view together with the robot states below and detect congestion \
patterns such as deadlocks, bottlenecks, crowding, or anomalies.

Robot states (sorted by ID):
{robot_state_block}
{pairwise_geometry_block}
Known robot IDs: {known_robot_ids_json}
{failure_context_block}
Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each \
other as physically conflicting. Use the pairwise geometry above; do not \
re-derive distances or facing from the coordinates.
- theta is heading in radians: 0=east(+x), π/2=north(+y), π or -π=west(-x), \
-π/2=south(-y). Opposite headings alone do NOT mean head-on: two robots are \
head-on only when each faces the other (pairwise geometry) AND they are within \
~0.5 m. Robots heading away from each other are diverging, not conflicting.
- deadlock: two or more robots each blocked by the other. The most common case \
is a head-on standoff — two robots within ~0.5 m, each facing the other, in the \
same narrow aisle, both STOPPED or STALE, unable to pass. This IS a deadlock \
even with only two robots. Two robots that are stopped but farther apart than \
~0.5 m, or not facing each other, are NOT deadlocked — answer \
congestion_detected=false unless another pattern applies. \
bottleneck: several robots queued waiting behind one slow robot or blocked passage \
(one-way congestion, not opposing). crowding: many robots packed into a small \
area. anomaly: unexpected or unsafe configuration.
- For head-on deadlock (two stopped/stale robots within ~0.5 m, each facing the \
other): classify as type="deadlock" and strategy="yield" \
(first listed robot backs up) or strategy="reverse" (both back up to clear).
- For a simple bottleneck (robots queued in the same direction): classify as \
type="bottleneck" and strategy="temporary_wait" or "yield".
- Decide from the robot coordinates and the image, not from assumptions about intent.

Produce a JSON object with exactly these fields:
- "congestion_detected": true or false
- "type": "none" | "deadlock" | "bottleneck" | "crowding" | "anomaly"
- "involved_robots": list of robot_id strings, from the known IDs only
- "root_cause": one sentence
- "strategy": "none" | "yield" | "reroute" | "convoy" | "priority_override" | \
"temporary_wait" | "reverse"
- "justification": one or two sentences

Rules:
- Only use robot IDs from the known list above.
- When congestion_detected is false: set type="none", strategy="none", involved_robots=[].
- When congestion_detected is true: type and strategy must not be "none", and \
involved_robots must be non-empty.

Answer using the following format:
<think>
Read the pairwise geometry (distance and whether each robot faces the other), \
check the robot statuses, identify any conflicts, and decide the congestion \
type and strategy.
</think>
Immediately after the </think> tag, write ONLY the final JSON object, with no \
surrounding text or markdown."""

_FAILURE_CONTEXT_ADVICE = (
    "If the congestion is no longer present, report congestion_detected=false. "
    "If it persists and the previous strategy did not clear it, prefer a different "
    "strategy unless the scene has changed."
)


def render_failure_context_block(context: FailureContext) -> str:
    """Render the previous-attempt block for a re-analysis prompt (rev-8 A.1).

    Args:
        context: Prior-attempt summary supplied by M5.

    Returns:
        A multi-line block with no leading or trailing newline.
    """
    attempt = f"strategy={context.strategy}"
    if context.yield_robot is not None:
        attempt += f", yield_robot={context.yield_robot}"
    attempt += f", outcome={context.outcome_status}"
    # crossing_order is accepted on FailureContext but not rendered in this slice
    # (Phase 1 plan Task 5 adds the ordered-crossing prompt block).
    return "\n".join(
        [
            "Previous attempt in this episode:",
            f"- {attempt}",
            f"- detail: {context.failure_detail}",
            _FAILURE_CONTEXT_ADVICE,
        ]
    )


def format_robot_state_lines(robot_states: list[RobotStateInput]) -> list[str]:
    """Render robot states as deterministic key=value lines for the prompt.

    Args:
        robot_states: Robot states to render (caller sorts beforehand).

    Returns:
        One comma-separated line per robot; optional fields omitted when None.
    """
    lines: list[str] = []
    for state in robot_states:
        parts = [
            f"robot_id={state.robot_id}",
            f"x={state.x:.2f}",
            f"y={state.y:.2f}",
            f"theta={state.theta:.2f}",
        ]
        if state.status is not None:
            parts.append(f"status={state.status}")
        if state.goal is not None:
            parts.append(f"goal_x={state.goal[0]:.2f}, goal_y={state.goal[1]:.2f}")
        if state.task is not None:
            parts.append(f"task={state.task}")
        if state.linear_velocity is not None:
            parts.append(f"linear_velocity={state.linear_velocity:.2f}")
        if state.angular_velocity is not None:
            parts.append(f"angular_velocity={state.angular_velocity:.2f}")
        lines.append(", ".join(parts))
    return lines


def _faces(theta: float, dx: float, dy: float, distance: float) -> bool:
    if distance < 1e-6:
        return False
    return (math.cos(theta) * dx + math.sin(theta) * dy) / distance >= _FACING_COS


def format_pairwise_geometry_lines(robot_states: list[RobotStateInput]) -> list[str]:
    """Render distance and mutual facing for every robot pair, sorted by ID.

    Args:
        robot_states: Robot states; pairs are formed in robot-ID order.

    Returns:
        One line per pair, e.g. `robot_1 <-> robot_2: distance 1.00 m;
        robot_1 faces robot_2: yes; robot_2 faces robot_1: no`; empty with fewer
        than two robots.
    """
    ordered = sorted(robot_states, key=lambda s: s.robot_id)
    lines: list[str] = []
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            dx, dy = second.x - first.x, second.y - first.y
            distance = math.hypot(dx, dy)
            first_faces = "yes" if _faces(first.theta, dx, dy, distance) else "no"
            second_faces = "yes" if _faces(second.theta, -dx, -dy, distance) else "no"
            lines.append(
                f"{first.robot_id} <-> {second.robot_id}: distance {distance:.2f} m; "
                f"{first.robot_id} faces {second.robot_id}: {first_faces}; "
                f"{second.robot_id} faces {first.robot_id}: {second_faces}"
            )
    return lines


def build_prompt_payload(request: ReasonerRequest) -> PromptPayload:
    """Build a deterministic, fully-rendered prompt payload from a request.

    Args:
        request: Validated reasoning request from M5/M1.

    Returns:
        Frozen `PromptPayload` with fixed system prompt and dynamic user prompt.
    """
    sorted_states = sorted(request.robot_states, key=lambda s: s.robot_id)
    known_ids = [s.robot_id for s in sorted_states]
    lines = format_robot_state_lines(sorted_states)
    block = "\n".join(f"- {line}" for line in lines) or "- no robots observed"
    geometry_lines = format_pairwise_geometry_lines(sorted_states)
    geometry_block = ""
    if geometry_lines:
        bullets = [f"- {line}" for line in geometry_lines]
        geometry_block = "\n" + "\n".join([_PAIRWISE_GEOMETRY_HEADER, *bullets]) + "\n"
    failure_block = (
        ""
        if request.failure_context is None
        else "\n" + render_failure_context_block(request.failure_context) + "\n"
    )
    user_prompt = _USER_TEMPLATE.format(
        robot_state_block=block,
        known_robot_ids_json=json.dumps(known_ids),
        pairwise_geometry_block=geometry_block,
        failure_context_block=failure_block,
    )
    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=known_ids,
    )
