"""T0 negative-control probe scheduling and bookkeeping for M5 (no rclpy).

T0 invokes the VLM analysis off-trigger on normal-flow scenes in log-only mode:
a probe is analyzed and recorded exactly like a triggered analysis but can
never be grounded or dispatched (design spec, "Scenario battery", T0).
"""
from __future__ import annotations

# The `reason=` of a probe's `starting analysis` log line.
T0_PROBE_REASON = "t0_probe"


class ProbeScheduler:
    """Fixed-cadence probe clock with an optional cap on the number of probes.

    A probe is due once `interval_sec` has passed since the last recorded probe
    (or since `started_at` before the first). A due probe that cannot start yet
    stays due, so it fires on the first free tick instead of a whole interval
    later; only a probe that actually starts is recorded and counted.
    """

    def __init__(self, interval_sec: float, max_probes: int, started_at: float) -> None:
        """Create the scheduler.

        Args:
            interval_sec: Minimum seconds between probe starts; must be > 0.
            max_probes: Probes to start in total; 0 means unlimited.
            started_at: Monotonic time the cadence is measured from.

        Raises:
            ValueError: If `interval_sec` is not positive or `max_probes` is negative.
        """
        if interval_sec <= 0.0:
            raise ValueError(f"interval_sec must be > 0, got {interval_sec}")
        if max_probes < 0:
            raise ValueError(f"max_probes must be >= 0, got {max_probes}")
        self._interval_sec = interval_sec
        self._max_probes = max_probes
        self._anchor = started_at
        self._started = 0

    @property
    def probes_started(self) -> int:
        """Number of probes recorded so far."""
        return self._started

    @property
    def exhausted(self) -> bool:
        """True once `max_probes` probes have started (never when unlimited)."""
        return self._max_probes > 0 and self._started >= self._max_probes

    def due(self, now: float) -> bool:
        """Return whether a probe should start at `now`, if nothing blocks it.

        Args:
            now: Monotonic time in seconds.

        Returns:
            True when the interval has elapsed and the cap is not reached.
        """
        return not self.exhausted and now - self._anchor >= self._interval_sec

    def record_probe(self, now: float) -> int:
        """Record that a probe started at `now` and restart the interval.

        Args:
            now: Monotonic time the probe was submitted.

        Returns:
            The zero-based index of this probe within the run.

        Raises:
            RuntimeError: If the cap has already been reached.
        """
        if self.exhausted:
            raise RuntimeError(f"probe cap of {self._max_probes} already reached")
        index = self._started
        self._started += 1
        self._anchor = now
        return index


def probe_block_reason(
    *,
    analysis_in_flight: bool,
    probe_in_flight: bool,
    has_scene: bool,
    frame_ready: bool,
) -> str | None:
    """Return why a due probe cannot start now, or None when it may start.

    A real analysis always wins: a probe never starts while one is in flight.
    Like a triggered analysis, a probe needs a scene with robots and an
    annotated frame fresh against it.

    Args:
        analysis_in_flight: A triggered analysis is being reasoned about.
        probe_in_flight: The previous probe has not completed.
        has_scene: A scene snapshot with at least one robot is available.
        frame_ready: The annotated frame is fresh against that snapshot.

    Returns:
        `"analysis_in_flight"`, `"probe_in_flight"`, `"no_scene"`,
        `"frame_not_fresh"`, or None.
    """
    if analysis_in_flight:
        return "analysis_in_flight"
    if probe_in_flight:
        return "probe_in_flight"
    if not has_scene:
        return "no_scene"
    if not frame_ready:
        return "frame_not_fresh"
    return None


class ProbeLedger:
    """Request ids minted for probes, checked at the dispatch boundary.

    The probe path never calls grounding or dispatch; this ledger is the
    defensive second layer that refuses a probe outcome if one ever arrives
    there anyway. Empty whenever probe mode is off.
    """

    def __init__(self) -> None:
        self._request_ids: set[str] = set()

    def register(self, request_id: str) -> None:
        """Record `request_id` as a probe."""
        self._request_ids.add(request_id)

    def is_probe(self, request_id: str) -> bool:
        """Return whether `request_id` was minted for a probe."""
        return request_id in self._request_ids
