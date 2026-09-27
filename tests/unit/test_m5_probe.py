"""Unit tests for M5's T0 log-only probe scheduling and ledger (no rclpy)."""
from __future__ import annotations

import pytest
from swarm_orchestrator.probe import (
    T0_PROBE_REASON,
    ProbeLedger,
    ProbeScheduler,
    probe_block_reason,
)


def test_probe_reason_is_t0_probe():
    assert T0_PROBE_REASON == "t0_probe"


def test_scheduler_not_due_before_first_interval():
    scheduler = ProbeScheduler(interval_sec=20.0, max_probes=0, started_at=100.0)
    assert scheduler.due(119.9) is False


def test_scheduler_due_once_interval_elapsed():
    scheduler = ProbeScheduler(interval_sec=20.0, max_probes=0, started_at=100.0)
    assert scheduler.due(120.0) is True


def test_scheduler_measures_next_interval_from_last_probe():
    scheduler = ProbeScheduler(interval_sec=20.0, max_probes=0, started_at=100.0)
    scheduler.record_probe(125.0)
    assert scheduler.due(144.9) is False
    assert scheduler.due(145.0) is True


def test_scheduler_stays_due_while_probe_not_recorded():
    # A deferred probe (analysis in flight) fires on the first free tick rather
    # than waiting a whole further interval.
    scheduler = ProbeScheduler(interval_sec=20.0, max_probes=0, started_at=0.0)
    assert scheduler.due(20.0) is True
    assert scheduler.due(33.0) is True


def test_scheduler_returns_zero_based_probe_indices():
    scheduler = ProbeScheduler(interval_sec=1.0, max_probes=0, started_at=0.0)
    assert [scheduler.record_probe(t) for t in (1.0, 2.0, 3.0)] == [0, 1, 2]
    assert scheduler.probes_started == 3


def test_scheduler_stops_when_max_probes_reached():
    scheduler = ProbeScheduler(interval_sec=1.0, max_probes=2, started_at=0.0)
    scheduler.record_probe(1.0)
    scheduler.record_probe(2.0)
    assert scheduler.exhausted is True
    assert scheduler.due(100.0) is False


def test_scheduler_unlimited_when_max_probes_zero():
    scheduler = ProbeScheduler(interval_sec=1.0, max_probes=0, started_at=0.0)
    for t in range(1, 51):
        scheduler.record_probe(float(t))
    assert scheduler.exhausted is False
    assert scheduler.due(52.0) is True


def test_scheduler_rejects_record_when_exhausted():
    scheduler = ProbeScheduler(interval_sec=1.0, max_probes=1, started_at=0.0)
    scheduler.record_probe(1.0)
    with pytest.raises(RuntimeError):
        scheduler.record_probe(2.0)


@pytest.mark.parametrize(("interval", "max_probes"), [(0.0, 0), (-1.0, 0), (1.0, -1)])
def test_scheduler_rejects_invalid_settings(interval, max_probes):
    with pytest.raises(ValueError):
        ProbeScheduler(interval_sec=interval, max_probes=max_probes, started_at=0.0)


def _block(**overrides):
    base = {
        "analysis_in_flight": False,
        "probe_in_flight": False,
        "has_scene": True,
        "frame_ready": True,
    }
    base.update(overrides)
    return probe_block_reason(**base)


def test_probe_allowed_when_idle_with_fresh_scene():
    assert _block() is None


def test_probe_blocked_when_analysis_in_flight():
    assert _block(analysis_in_flight=True) == "analysis_in_flight"


def test_probe_blocked_when_probe_in_flight():
    assert _block(probe_in_flight=True) == "probe_in_flight"


def test_probe_blocked_when_no_scene():
    assert _block(has_scene=False, frame_ready=False) == "no_scene"


def test_probe_blocked_when_frame_stale():
    assert _block(frame_ready=False) == "frame_not_fresh"


def test_probe_block_reports_analysis_first_when_several_apply():
    assert _block(analysis_in_flight=True, probe_in_flight=True, has_scene=False) == (
        "analysis_in_flight"
    )


def test_ledger_identifies_registered_probe():
    ledger = ProbeLedger()
    ledger.register("abc")
    assert ledger.is_probe("abc") is True


def test_ledger_rejects_unregistered_request():
    ledger = ProbeLedger()
    ledger.register("abc")
    assert ledger.is_probe("def") is False
