def is_congested(wait_time_sec: float, threshold_sec: float) -> bool:
    return wait_time_sec >= threshold_sec
