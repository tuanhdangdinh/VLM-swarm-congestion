from dataclasses import dataclass


@dataclass(frozen=True)
class EstimatedState:
    robot_id: str
    x: float
    y: float
    theta: float
    status: str = "idle"
