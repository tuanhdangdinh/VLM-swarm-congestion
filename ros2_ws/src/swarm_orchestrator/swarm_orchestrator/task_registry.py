from dataclasses import dataclass, field


@dataclass
class TaskRegistry:
    tasks_by_robot: dict[str, str] = field(default_factory=dict)

    def assign(self, robot_id: str, task: str) -> None:
        self.tasks_by_robot[robot_id] = task
