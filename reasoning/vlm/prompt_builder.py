import json

from reasoning.vlm.models import PromptPayload, ReasonerRequest, RobotStateInput

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

Known robot IDs: {known_robot_ids_json}

Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each \
other as physically conflicting.
- theta is heading in radians: 0=east(+x), π/2=north(+y), π or -π=west(-x), \
-π/2=south(-y). Two robots with |theta_1 - theta_2| close to π are facing \
each other head-on.
- deadlock: two or more robots each blocked by the other. The most common case \
is a head-on standoff — two robots facing opposite directions (theta values \
differing by ~π) in the same narrow aisle, both STOPPED or STALE, unable to \
pass. This IS a deadlock even with only two robots. \
bottleneck: several robots queued waiting behind one slow robot or blocked passage \
(one-way congestion, not opposing). crowding: many robots packed into a small \
area. anomaly: unexpected or unsafe configuration.
- For head-on deadlock (two stopped/stale robots with opposing headings and/or \
opposing goal directions): classify as type="deadlock" and strategy="yield" \
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
Compute the pairwise distance between robots, check theta values for opposing \
headings (head-on deadlock), inspect goal positions for opposing directions, \
identify any conflicts, and decide the congestion type and strategy.
</think>
Immediately after the </think> tag, write ONLY the final JSON object, with no \
surrounding text or markdown."""


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
    user_prompt = _USER_TEMPLATE.format(
        robot_state_block=block,
        known_robot_ids_json=json.dumps(known_ids),
    )
    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_path=request.image_path,
        known_robot_ids=known_ids,
    )
