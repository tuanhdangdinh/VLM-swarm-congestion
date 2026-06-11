import json

from reasoning.vlm.models import PromptPayload, ReasonerRequest, RobotStateInput

SYSTEM_PROMPT = (
    "You are a warehouse swarm robotics traffic controller.\n"
    "Your task is to analyze overhead camera views of autonomous mobile robots\n"
    "and detect congestion patterns such as deadlocks, bottlenecks, crowding,\n"
    "and anomalies. You always respond with only valid JSON — no other text."
)

_USER_TEMPLATE = """Analyze the overhead warehouse scene for congestion or deadlock.

Robot states (sorted by ID):
{robot_state_block}

Known robot IDs: {known_robot_ids_json}

Return ONLY a JSON object with exactly these fields:
{{
  "congestion_detected": <true|false>,
  "type": <"none"|"deadlock"|"bottleneck"|"crowding"|"anomaly">,
  "involved_robots": [<robot_id strings, must be from known IDs only>],
  "root_cause": "<one sentence>",
  "strategy": <"none"|"yield"|"reroute"|"convoy"|"priority_override"|"temporary_wait"|"reverse">,
  "justification": "<one or two sentences>"
}}

Rules:
- Only use robot IDs from the known list above.
- When congestion_detected is false: set type="none", strategy="none", involved_robots=[].
- Return ONLY the JSON object. Do not include any text, markdown, or explanation."""


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
