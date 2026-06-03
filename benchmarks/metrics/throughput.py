def tasks_per_minute(completed_tasks: int, duration_sec: float) -> float:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    return completed_tasks / (duration_sec / 60.0)
