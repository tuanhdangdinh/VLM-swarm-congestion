def collisions_per_minute(collisions: int, duration_sec: float) -> float:
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    return collisions / (duration_sec / 60.0)
