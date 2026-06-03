def recovery_time_sec(deadlock_start_sec: float, resolved_sec: float) -> float:
    return max(0.0, resolved_sec - deadlock_start_sec)
