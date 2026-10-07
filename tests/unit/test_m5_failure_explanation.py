"""prereg-v3 R3.4 failure-explanation line: templates, bound, byte-identity, node wiring."""
# ruff: noqa: F811
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from swarm_orchestrator.command_lifecycle import (
    AttemptContexts,
    AttemptMemory,
    AttemptRecord,
)
from swarm_orchestrator.reasoning_pipeline import (
    FAILURE_EXPLANATION_MAX_CHARS,
    build_failure_context,
    build_failure_contexts,
    explain_attempt,
)

from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _make_node,
    _trigger_real,
    node_env,
)

# Every strategy-enum value plus the M4 action names: a refusal or
# replacement sentence must name none of them.
_MANEUVER_WORDS = (
    "yield",
    "reverse",
    "reroute",
    "convoy",
    "temporary_wait",
    "priority_override",
    "junction_clear",
    "wait",
)
_LEGACY_DETAIL = "yield failed after 20 s; congestion re-detected for the same robots"


def _record(**fields) -> AttemptRecord:
    base = dict(
        command_id="c1",
        robot_ids=["robot_1", "robot_2"],
        strategy="yield",
        yield_robot="robot_2",
        dispatched_at=40.0,
        resolved_at=60.0,
        outcome_status="failed",
    )
    base.update(fields)
    return AttemptRecord(**base)


def _failed_yield() -> AttemptRecord:
    return _record(
        leg_outcomes={"robot_2": ("yield", "failed"), "robot_1": ("temporary_wait", "completed")}
    )


def _names_a_maneuver(text: str) -> bool:
    return any(re.search(rf"\b{word}\b", text) for word in _MANEUVER_WORDS)


# ---- byte-identity (flag off) ----


def test_flag_off_detail_is_byte_identical_despite_sources():
    record = _failed_yield()
    record.refusal_reason = "yield refused: no feasible yielder"
    record.arrival_rejections = {"robot_1": 0.6}
    assert build_failure_context(record, now=90.0).failure_detail == _LEGACY_DETAIL


def test_flag_off_contexts_pair_is_byte_identical():
    latest, failed = build_failure_contexts(AttemptContexts(_failed_yield(), None), now=90.0)
    assert latest.failure_detail == _LEGACY_DETAIL
    assert failed is None


def test_flag_on_without_any_source_leaves_detail_unchanged():
    assert build_failure_context(_record(), now=90.0, explain=True).failure_detail == (
        _LEGACY_DETAIL
    )


def test_flag_on_appends_one_sentence_to_detail():
    detail = build_failure_context(_failed_yield(), now=90.0, explain=True).failure_detail
    assert detail == f"{_LEGACY_DETAIL}. Cause: robot_2's yield leg failed during execution."


def test_flag_on_explains_both_context_blocks():
    latest = _record(
        command_id="c2",
        strategy="temporary_wait",
        outcome_status="completed",
        leg_outcomes={
            "robot_1": ("temporary_wait", "completed"),
            "robot_2": ("temporary_wait", "completed"),
        },
    )
    first, second = build_failure_contexts(
        AttemptContexts(latest, _failed_yield()), now=90.0, explain=True
    )
    assert first.failure_detail.endswith(
        "Cause: no leg failed; every commanded robot reported completion."
    )
    assert second.failure_detail.endswith("Cause: robot_2's yield leg failed during execution.")


# ---- each source ----


def test_failed_leg_names_robot_and_its_own_leg():
    assert explain_attempt(_failed_yield()) == (
        "Cause: robot_2's yield leg failed during execution."
    )


def test_two_failed_legs_are_listed_sorted():
    record = _record(
        strategy="reverse",
        leg_outcomes={"robot_2": ("reverse", "failed"), "robot_1": ("reverse", "failed")},
    )
    assert explain_attempt(record) == (
        "Cause: the legs of robot_1 (reverse) and robot_2 (reverse) failed during execution."
    )


def test_many_failed_legs_are_capped():
    record = _record(
        leg_outcomes={f"robot_{i}": ("reverse", "failed") for i in range(1, 5)},
    )
    assert explain_attempt(record) == (
        "Cause: the legs of robot_1 (reverse), robot_2 (reverse) and 2 more "
        "failed during execution."
    )


def test_timed_out_leg_reports_it_never_started():
    record = _record(
        outcome_status="timed_out",
        leg_outcomes={
            "robot_2": ("yield", "timed_out"),
            "robot_1": ("temporary_wait", "completed"),
        },
    )
    assert explain_attempt(record) == (
        "Cause: robot_2's yield leg never started before the command deadline."
    )


def test_failed_leg_outranks_timed_out_leg():
    record = _record(
        leg_outcomes={"robot_2": ("yield", "failed"), "robot_1": ("temporary_wait", "timed_out")},
    )
    assert "failed during execution" in explain_attempt(record)


def test_refusal_reports_room_class_without_echoing_m3_text():
    record = _record(
        outcome_status="completed",
        executed_strategy="temporary_wait",
        refusal_reason=(
            "yield refused: no feasible yielder (robot_1 0.40 m, robot_2 0.55 m retreat room "
            "< 1.20 m required)"
        ),
        leg_outcomes={
            "robot_1": ("temporary_wait", "completed"),
            "robot_2": ("temporary_wait", "completed"),
        },
    )
    sentence = explain_attempt(record)
    assert sentence == (
        "Cause: the planned maneuver was refused before dispatch because no involved robot "
        "had enough room to retreat."
    )
    assert "1.20" not in sentence


def test_refusal_outranks_completed_legs():
    # A refused yield resolves `completed` (its substitute waits complete).
    record = _record(
        outcome_status="completed",
        refusal_reason="yield refused: no other involved robot to pass",
        leg_outcomes={"robot_1": ("temporary_wait", "completed")},
    )
    assert "refused before dispatch" in explain_attempt(record)


@pytest.mark.parametrize(
    ("reason", "phrase"),
    [
        (
            "yield refused: both robots outside the corridor on the same side; "
            "a reverse would traverse it",
            "both robots were outside the corridor on the same side",
        ),
        (
            "yield refused: crossing order unverifiable without every robot's position",
            "the crossing order did not match the tracked robot positions",
        ),
        (
            "yield refused: first passer robot_3 is not the passer nearest the yielder robot_1",
            "the crossing order did not match the tracked robot positions",
        ),
        (
            "yield refused: every involved robot is paired against a same-axis partner "
            "holding the opposite side",
            "no involved robot was positioned to pass",
        ),
        ("yield refused: something new", "a feasibility check on the robots' positions failed"),
    ],
)
def test_refusal_classes_map_to_fixed_phrases_naming_no_maneuver(reason, phrase):
    sentence = explain_attempt(_record(refusal_reason=reason))
    assert sentence.endswith(f"because {phrase}.")
    assert not _names_a_maneuver(sentence)


def test_infeasible_geometry_degradation_reports_replacement():
    record = _record(
        executed_strategy="reroute",
        degradations=["retreat=default:no_choice", "yield=infeasible:escort blocked"],
        leg_outcomes={"robot_2": ("reroute", "completed")},
    )
    sentence = explain_attempt(record)
    assert sentence == (
        "Cause: the planned maneuver was replaced before dispatch because no retreat fit "
        "the scene geometry at the robots' positions."
    )
    assert not _names_a_maneuver(sentence)


def test_reverse_infeasible_degradation_reports_no_room_behind():
    record = _record(strategy="reverse", degradations=["reverse=infeasible:no room"])
    sentence = explain_attempt(record)
    assert sentence.endswith("because there was not enough room behind the robots.")
    assert not _names_a_maneuver(sentence)


def test_non_failure_degradation_is_not_a_cause():
    record = _record(
        degradations=["retreat=default:no_choice", "order=implicit"],
        leg_outcomes={"robot_2": ("yield", "failed")},
    )
    assert explain_attempt(record) == "Cause: robot_2's yield leg failed during execution."


def test_arrival_rejection_reports_camera_distance():
    record = _record(
        outcome_status="completed",
        leg_outcomes={
            "robot_2": ("yield", "completed"),
            "robot_1": ("temporary_wait", "completed"),
        },
        arrival_rejections={"robot_1": 0.594},
    )
    assert explain_attempt(record) == (
        "Cause: robot_1 was reported at its goal by its navigator, but the camera placed it "
        "0.59 m from the goal."
    )


def test_arrival_rejection_without_estimate_and_others():
    record = _record(
        leg_outcomes={"robot_1": ("yield", "completed")},
        arrival_rejections={"robot_2": None, "robot_1": 0.7},
    )
    assert explain_attempt(record) == (
        "Cause: robot_1 was reported at its goal by its navigator, but the camera placed it "
        "0.70 m from the goal (1 more robots likewise)."
    )
    only_none = _record(arrival_rejections={"robot_2": None})
    assert "the camera did not confirm it there" in explain_attempt(only_none)


def test_all_completed_reports_no_leg_failed():
    record = _record(
        outcome_status="completed",
        leg_outcomes={
            "robot_1": ("yield", "completed"),
            "robot_2": ("temporary_wait", "completed"),
        },
    )
    assert explain_attempt(record) == (
        "Cause: no leg failed; every commanded robot reported completion."
    )


def test_no_sources_gives_no_sentence():
    assert explain_attempt(_record()) is None


def test_explanation_is_deterministic():
    assert explain_attempt(_failed_yield()) == explain_attempt(_failed_yield())


# ---- length bound ----


@pytest.mark.parametrize(
    "record",
    [
        _record(
            leg_outcomes={
                f"robot_with_a_very_long_identifier_{i:03d}": ("temporary_wait", "failed")
                for i in range(4)
            }
        ),
        _record(
            leg_outcomes={
                f"robot_with_a_very_long_identifier_{i:03d}": ("temporary_wait", "timed_out")
                for i in range(4)
            }
        ),
        _record(arrival_rejections={"r" * 300: 12.345, "robot_2": 0.5}),
        _record(refusal_reason="yield refused: " + "x" * 500),
        _record(degradations=["yield=infeasible:" + "x" * 500]),
        _failed_yield(),
    ],
)
def test_explanation_never_exceeds_bound(record):
    sentence = explain_attempt(record)
    assert sentence is not None
    assert len(sentence) <= FAILURE_EXPLANATION_MAX_CHARS
    assert sentence.startswith("Cause: ")


# ---- lifecycle capture ----


def test_attempt_memory_records_refusal_and_degradations():
    memory = AttemptMemory(window_sec=60.0)
    memory.record(
        "c1",
        ["robot_1", "robot_2"],
        "yield",
        None,
        10.0,
        refusal_reason="yield refused: x",
        degradations=["yield=infeasible:x"],
    )
    memory.resolve("c1", "completed", 20.0)
    record = memory.context_for(["robot_1"], 21.0)
    assert record.refusal_reason == "yield refused: x"
    assert record.degradations == ["yield=infeasible:x"]


def test_attempt_memory_resolve_keeps_latest_leg_outcomes():
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c1", ["robot_1", "robot_2"], "yield", "robot_2", 10.0)
    memory.resolve("c1", "failed", 20.0, leg_outcomes={"robot_2": ("yield", "failed")})
    memory.resolve("c1", "failed", 21.0)
    record = memory.context_for(["robot_1"], 22.0)
    assert record.resolved_at == 20.0
    assert record.leg_outcomes == {"robot_2": ("yield", "failed")}


def test_attempt_memory_notes_arrival_rejection_only_for_attempt_robots():
    memory = AttemptMemory(window_sec=60.0)
    memory.record("c1", ["robot_1", "robot_2"], "yield", "robot_2", 10.0)
    memory.note_arrival_rejection("robot_1", 0.6)
    memory.note_arrival_rejection("robot_9", 0.6)
    memory.resolve("c1", "completed", 20.0)
    assert memory.context_for(["robot_1"], 21.0).arrival_rejections == {"robot_1": 0.6}


def test_attempt_memory_arrival_rejection_without_record_is_ignored():
    memory = AttemptMemory(window_sec=60.0)
    memory.note_arrival_rejection("robot_1", 0.6)
    assert memory.context_for(["robot_1"], 1.0) is None


# ---- node wiring ----


def _artifact(node, request_id: str) -> dict:
    return json.loads(
        (Path(node._config.decision_log_dir) / f"{request_id}.json").read_text()
    )


def _fail_first_command_then_retrigger(node, clock, pipeline) -> dict:
    _trigger_real(node)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()
    command_id = f"cmd-{pipeline.run_calls[0]}"
    node._on_status(SimpleNamespace(command_id=command_id, robot_id="robot_2", status="FAILED"))
    node._on_status(
        SimpleNamespace(command_id=command_id, robot_id="robot_1", status="COMPLETED")
    )
    clock.t += 20.0  # past cooldown_sec=15
    _trigger_real(node, stamp=80.0)
    node._future.result(timeout=WAIT_SEC)
    node._on_timer()
    return _artifact(node, pipeline.run_calls[1])


def test_node_flag_on_failure_context_carries_cause(node_env, tmp_path):
    from tests.unit.test_m5_node_probe import _FakePipeline

    pipeline = _FakePipeline()
    node, clock = _make_node(
        node_env, tmp_path, pipeline, t0_probe_mode=False, failure_explanation_enabled=True
    )
    payload = _fail_first_command_then_retrigger(node, clock, pipeline)

    detail = payload["failure_context"]["failure_detail"]
    assert detail.endswith(". Cause: robot_2's yield leg failed during execution.")
    assert detail in payload["prompt"]["user_prompt"]


def test_node_flag_off_failure_context_has_no_cause(node_env, tmp_path):
    from tests.unit.test_m5_node_probe import _FakePipeline

    pipeline = _FakePipeline()
    node, clock = _make_node(node_env, tmp_path, pipeline, t0_probe_mode=False)
    payload = _fail_first_command_then_retrigger(node, clock, pipeline)

    detail = payload["failure_context"]["failure_detail"]
    assert detail.endswith("; congestion re-detected for the same robots")
    assert "Cause:" not in payload["prompt"]["user_prompt"]
