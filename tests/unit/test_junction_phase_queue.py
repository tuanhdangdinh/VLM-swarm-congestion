"""Unit tests for M5's pure `junction_clear` phase queue (prereg-v2 (a) M5,
build-order step 5)."""
from __future__ import annotations

import json

from swarm_orchestrator.junction_phase_queue import JunctionPhaseQueue

from reasoning.rag.command_grounder import ground_junction_clear_phases
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import ReasonerDiagnostics, ReasonerResult, RobotStateInput, SnapshotFrame
from reasoning.vlm.output_parser import parse_decision_text

IB10_STANDOFF = {
    "robot_1": (-0.2192, -0.0014),
    "robot_2": (0.33, 0.0158),
    "robot_3": (-0.0208, -0.2583),
    "robot_4": (0.0045, 0.2773),
}
JUNCTION_ARMS = {
    "robot_1": ArmGeometry(axis="x", side=-1),
    "robot_2": ArmGeometry(axis="x", side=1),
    "robot_3": ArmGeometry(axis="y", side=-1),
    "robot_4": ArmGeometry(axis="y", side=1),
}


def _geometry() -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(corridor=corridor, arms=JUNCTION_ARMS, junction_recede_offset_m=1.2)


def _frame() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=xy[0], y=xy[1], theta=0.0, status="STOPPED")
            for rid, xy in IB10_STANDOFF.items()
        ],
    )


def _result(request_id: str = "req-jc") -> ReasonerResult:
    decision_json = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": list(IB10_STANDOFF),
        "root_cause": "four-way standoff",
        "strategy": "junction_clear",
        "justification": "jam",
    }
    decision = parse_decision_text(json.dumps(decision_json))
    return ReasonerResult(
        request_id=request_id,
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id=request_id, backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _plan():
    return ground_junction_clear_phases(
        _result(), snapshot=_frame(), params=GroundingParams(mode="derived"), geometry=_geometry()
    )


class TestStartAndOrdinaryAdvance:
    def test_start_returns_the_first_recede_phase(self):
        queue = JunctionPhaseQueue(_plan())
        command = queue.start()
        assert command["command_id"] == "req-jc-junction-recede-robot_4"
        assert queue.phase_reached == "recede"
        assert queue.done is False

    def test_completed_first_recede_advances_to_second_recede(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        advance = queue.on_resolved(first["command_id"], completed=True)
        assert advance.command["command_id"] == "req-jc-junction-recede-robot_3"
        assert advance.phase_reached == "recede"
        assert advance.done is False
        assert queue.phase_reached == "recede"

    def test_completed_second_recede_advances_to_cross(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        second = queue.on_resolved(first["command_id"], completed=True).command
        advance = queue.on_resolved(second["command_id"], completed=True)
        assert advance.command["command_id"] == "req-jc-junction-cross"
        assert advance.phase_reached == "cross"
        assert advance.done is False

    def test_completed_cross_resolves_the_queue(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        second = queue.on_resolved(first["command_id"], completed=True).command
        third = queue.on_resolved(second["command_id"], completed=True).command
        advance = queue.on_resolved(third["command_id"], completed=True)
        assert advance.command is None
        assert advance.phase_reached == "resolved"
        assert advance.done is True
        assert queue.done is True


class TestFailureFallback:
    def test_failed_first_recede_dispatches_the_fallback_not_a_retry(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        advance = queue.on_resolved(first["command_id"], completed=False)
        assert advance.command["command_id"] == "req-jc-yield"
        assert advance.phase_reached == "fallback"
        assert advance.done is False
        # Never the same recede command re-issued.
        assert advance.command["command_id"] != first["command_id"]

    def test_failed_second_recede_also_dispatches_the_fallback(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        second = queue.on_resolved(first["command_id"], completed=True).command
        advance = queue.on_resolved(second["command_id"], completed=False)
        assert advance.command["command_id"] == "req-jc-yield"
        assert advance.phase_reached == "fallback"

    def test_failed_cross_phase_also_dispatches_the_fallback(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        second = queue.on_resolved(first["command_id"], completed=True).command
        third = queue.on_resolved(second["command_id"], completed=True).command
        advance = queue.on_resolved(third["command_id"], completed=False)
        assert advance.command["command_id"] == "req-jc-yield"
        assert advance.phase_reached == "fallback"

    def test_fallback_resolution_completed_ends_the_queue(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        fallback = queue.on_resolved(first["command_id"], completed=False).command
        advance = queue.on_resolved(fallback["command_id"], completed=True)
        assert advance.command is None
        assert advance.phase_reached == "fallback"
        assert advance.done is True

    def test_fallback_resolution_failed_also_ends_the_queue_not_retried(self):
        # "falls back to v1 behavior" is itself the terminal step, whatever
        # its own outcome -- never a second fallback attempt.
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        fallback = queue.on_resolved(first["command_id"], completed=False).command
        advance = queue.on_resolved(fallback["command_id"], completed=False)
        assert advance.command is None
        assert advance.phase_reached == "fallback"
        assert advance.done is True


class TestForeignAndStaleStatus:
    def test_a_status_for_an_unrelated_command_id_is_ignored(self):
        queue = JunctionPhaseQueue(_plan())
        queue.start()
        advance = queue.on_resolved("some-other-command", completed=True)
        assert advance.command is None
        assert advance.done is False
        assert advance.phase_reached == "recede"

    def test_a_late_status_for_an_already_advanced_phase_is_ignored(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        second = queue.on_resolved(first["command_id"], completed=True).command
        # A late/duplicate COMPLETED for the already-superseded first phase.
        advance = queue.on_resolved(first["command_id"], completed=True)
        assert advance.command is None
        assert advance.done is False
        assert advance.phase_reached == "recede"
        # The queue's own progress (keyed on `second`) is unaffected.
        assert queue._active_command_id == second["command_id"]  # noqa: SLF001

    def test_a_status_after_done_is_ignored(self):
        queue = JunctionPhaseQueue(_plan())
        first = queue.start()
        fallback = queue.on_resolved(first["command_id"], completed=False).command
        queue.on_resolved(fallback["command_id"], completed=True)
        assert queue.done is True
        advance = queue.on_resolved(fallback["command_id"], completed=True)
        assert advance.command is None
        assert advance.done is True


class TestPhaseReachedOrdinal:
    def test_phase_reached_tracks_the_active_not_yet_resolved_phase(self):
        queue = JunctionPhaseQueue(_plan())
        assert queue.start()
        assert queue.phase_reached == "recede"
