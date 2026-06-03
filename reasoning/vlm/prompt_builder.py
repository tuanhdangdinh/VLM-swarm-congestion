from collections.abc import Mapping, Sequence


def build_scene_prompt(robot_states: Sequence[Mapping[str, object]]) -> str:
    """Build a compact scene-analysis prompt from robot state dictionaries."""
    state_lines = [
        ", ".join(f"{key}={value}" for key, value in sorted(state.items()))
        for state in robot_states
    ]
    states = "\n".join(f"- {line}" for line in state_lines) or "- no robots observed"
    return (
        "Analyze the warehouse swarm scene for congestion or deadlock.\n"
        "Return strict JSON with congestion_detected, type, involved_robots, "
        "root_cause, strategy, and justification.\n\n"
        f"Robot states:\n{states}"
    )
