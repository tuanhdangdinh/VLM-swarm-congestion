def mean_waiting_time(wait_times_sec: list[float]) -> float:
    return sum(wait_times_sec) / len(wait_times_sec) if wait_times_sec else 0.0
