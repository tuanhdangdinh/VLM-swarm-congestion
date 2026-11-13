"""v4 refusal feedback Change 2: the pure pieces (no node).

The record M5 keeps of a withheld decision (`WithheldMemory`), the plain-words
reason it states (`refusal_feedback_reason`), the prompt block that states it
(`render_refused_proposals_block`), and the plan tracker's prompt-only marking
of a plan M5 never dispatched (`PlanTracker.mark_withheld` / `shown_plan`).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from swarm_orchestrator.command_lifecycle import WithheldMemory
from swarm_orchestrator.plan_tracker import PlanTracker
from swarm_orchestrator.reasoning_pipeline import explain_attempt, refusal_feedback_reason

from reasoning.rag.command_grounder import VerifiedPlan
from reasoning.vlm.models import ProposedPlanLeg, ReasonerRequest, RefusedProposal
from reasoning.vlm.prompt_builder import build_prompt_payload, render_refused_proposals_block

RECORDED = Path(__file__).parent / "data/refusal_feedback/s1b_recorded_requests.jsonl"
_MANEUVER_WORDS = (
    "yield", "reverse", "reroute", "convoy", "temporary_wait", "priority_override",
    "junction_clear", "wait",
)
NO_YIELDER = (
    "yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m "
    "retreat room < 1.70 m required)"
)


def _names_a_maneuver(text: str) -> bool:
    return any(re.search(rf"\b{word}\b", text) for word in _MANEUVER_WORDS)


def _request(**update: Any) -> ReasonerRequest:
    row = json.loads(RECORDED.read_text().splitlines()[0])
    return ReasonerRequest.model_validate({**row["request"], **update})


def _proposal(**update: Any) -> RefusedProposal:
    fields: dict[str, Any] = {
        "strategy": "junction_clear",
        "involved_robots": ("robot_2", "robot_3", "robot_4"),
        "yield_robot": None,
        "reason": "no involved robot had enough room to retreat",
    }
    return RefusedProposal(**{**fields, **update})


def _verified(*legs: tuple[str, str]) -> VerifiedPlan:
    return VerifiedPlan(
        legs=[ProposedPlanLeg(robot_id=rid, action=action) for rid, action in legs],
        provenance="m3_default",
        edits=[],
    )


class TestRefusalFeedbackReason:
    def test_refusal_reason_uses_failure_explanation_phrase(self):
        withheld = {"reason": "refusal_no_action", "refusal_reason": NO_YIELDER}
        assert refusal_feedback_reason(withheld, []) == (
            "no involved robot had enough room to retreat"
        )

    @pytest.mark.parametrize(
        ("refusal", "phrase"),
        [
            (
                "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes "
                "(beyond the 30 deg snap)",
                "a robot's heading was not aligned with either aisle axis",
            ),
            (
                "yield refused: no shared lane: robot_4 and robot_3 both run along y but "
                "sit 47 deg across",
                "the robots were not in one shared lane",
            ),
            (
                "yield refused: no executable retreat (robot_5 has no retreat candidate "
                "surviving the sweep",
                "no retreat position passed the clearance checks at the robots' positions",
            ),
            (
                "yield refused: no declared junction: robot_4 runs along y and robot_3 "
                "along x (a crossing)",
                "the robots' lanes cross where the scene declares no junction",
            ),
            ("yield refused: something new", "a feasibility check on the robots' positions failed"),
        ],
    )
    def test_refusal_classes_map_to_plain_phrases(self, refusal, phrase):
        withheld = {"reason": "refusal_no_action", "refusal_reason": refusal}
        assert refusal_feedback_reason(withheld, []) == phrase

    def test_junction_fallback_on_undeclared_scene_says_so(self):
        withheld = {"reason": "refusal_no_action", "refusal_reason": NO_YIELDER}
        tags = [
            "junction_clear=fallback:no_candidates",
            "junction_geometry=shipped_unsolved:missing=junction_recede_offset_m",
        ]
        assert refusal_feedback_reason(withheld, tags) == (
            "this scene declares no junction recovery geometry, and the fallback check "
            "found that no involved robot had enough room to retreat"
        )

    def test_junction_fallback_on_declared_scene_names_no_geometry_gap(self):
        withheld = {"reason": "refusal_no_action", "refusal_reason": NO_YIELDER}
        reason = refusal_feedback_reason(withheld, ["junction_clear=fallback:no_candidates"])
        assert reason == (
            "no involved robot could back out of the junction, and the fallback check "
            "found that no involved robot had enough room to retreat"
        )

    def test_empty_reroute_reads_fallback_reason(self):
        withheld = {
            "reason": "empty_reroute",
            "fallback_reason": "yield=infeasible:escort_hits_park:robot_2:0.316",
        }
        assert refusal_feedback_reason(withheld, []) == (
            "the passing robot's route came too close to the retreat position"
        )

    def test_no_shared_lane_is_not_read_as_room_shortfall(self):
        refusal = (
            "yield refused: no shared lane: robot_1 and robot_2 both run along x but sit "
            "90 deg across it (side by side); no retreat room was measured"
        )
        withheld = {"reason": "refusal_no_action", "refusal_reason": refusal}
        assert refusal_feedback_reason(withheld, []) == "the robots were not in one shared lane"

    def test_churn_bound_reason(self):
        assert refusal_feedback_reason({"reason": "churn_budget"}, []) == (
            "the limit on repeated commands for these robots was reached"
        )

    @pytest.mark.parametrize(
        "withheld",
        [
            {"reason": "refusal_no_action", "refusal_reason": NO_YIELDER},
            {"reason": "empty_reroute", "fallback_reason": "yield=infeasible:escort_hits_park:r:1"},
            {"reason": "churn_alternation"},
        ],
    )
    def test_reason_names_no_maneuver(self, withheld):
        assert not _names_a_maneuver(refusal_feedback_reason(withheld, []))

    def test_failure_explanation_phrases_unchanged(self):
        from swarm_orchestrator.command_lifecycle import AttemptRecord

        record = AttemptRecord(
            command_id="c", robot_ids=["robot_1"], strategy="yield", yield_robot="robot_1",
            dispatched_at=0.0, resolved_at=1.0, outcome_status="completed",
            refusal_reason="yield refused: ambiguous lane: robot_3 heads 39 deg off both axes",
        )
        assert explain_attempt(record) == (
            "Cause: the planned maneuver was refused before dispatch because a feasibility "
            "check on the robots' positions failed."
        )


class TestRefusedProposalsBlock:
    def test_block_states_proposal_and_not_executed(self):
        block = render_refused_proposals_block([_proposal(yield_robot="robot_4", times=3)])
        assert block.splitlines()[1] == (
            "- strategy=junction_clear, involved=robot_2, robot_3, robot_4, "
            "yield_robot=robot_4: not executed (proposed 3 times) because no involved "
            "robot had enough room to retreat"
        )

    def test_single_proposal_has_no_count(self):
        block = render_refused_proposals_block([_proposal()])
        assert "times" not in block

    def test_block_has_header_and_advice(self):
        lines = render_refused_proposals_block([_proposal()]).splitlines()
        assert lines[0].startswith("Proposals the system withheld")
        assert lines[-1].startswith("If the congestion persists")

    def test_prompt_renders_block_when_set(self):
        user = build_prompt_payload(_request(refused_proposals=[_proposal()])).user_prompt
        assert render_refused_proposals_block([_proposal()]) in user

    def test_prompt_block_follows_known_ids(self):
        user = build_prompt_payload(_request(refused_proposals=[_proposal()])).user_prompt
        assert user.index("Known robot IDs") < user.index("Proposals the system withheld")
        assert user.index("Proposals the system withheld") < user.index("Guidance:")

    def test_prompt_unchanged_without_proposals(self):
        base = build_prompt_payload(_request()).user_prompt
        assert build_prompt_payload(_request(refused_proposals=None)).user_prompt == base

    def test_v2_request_ignores_proposals(self):
        base = build_prompt_payload(_request(prompt_version=2)).user_prompt
        user = build_prompt_payload(
            _request(prompt_version=2, refused_proposals=[_proposal()])
        ).user_prompt
        assert user == base

    def test_proposal_needs_robots(self):
        with pytest.raises(ValidationError):
            _proposal(involved_robots=())


class TestWithheldMemory:
    def test_overlapping_set_sees_proposal(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        memory.record(_proposal(), {"robot_2", "robot_3", "robot_4"}, now=0.0)
        assert memory.proposals_for(["robot_4", "robot_5"], now=1.0) == [_proposal()]

    def test_disjoint_set_sees_nothing(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        memory.record(_proposal(), {"robot_2", "robot_3", "robot_4"}, now=0.0)
        assert memory.proposals_for(["robot_1", "robot_5"], now=1.0) == []

    def test_disjoint_query_keeps_proposal(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        memory.record(_proposal(), {"robot_2", "robot_3"}, now=0.0)
        memory.proposals_for(["robot_5"], now=1.0)
        assert memory.proposals_for(["robot_2"], now=2.0) == [_proposal()]

    def test_identical_proposal_folds_and_counts(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        for now in (0.0, 1.0, 2.0):
            memory.record(_proposal(), {"robot_2"}, now=now)
        assert memory.proposals_for(["robot_2"], now=3.0) == [_proposal(times=3)]

    def test_repeat_moves_proposal_to_most_recent(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        memory.record(_proposal(), {"robot_2"}, now=0.0)
        memory.record(_proposal(strategy="yield", yield_robot="robot_2"), {"robot_2"}, now=1.0)
        memory.record(_proposal(), {"robot_2"}, now=2.0)
        shown = memory.proposals_for(["robot_2"], now=3.0)
        assert [p.strategy for p in shown] == ["yield", "junction_clear"]

    def test_only_most_recent_entries_shown(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=2)
        for index, robot in enumerate(("robot_1", "robot_2", "robot_3")):
            memory.record(_proposal(yield_robot=robot), {"robot_9"}, now=float(index))
        shown = memory.proposals_for(["robot_9"], now=5.0)
        assert [p.yield_robot for p in shown] == ["robot_2", "robot_3"]

    def test_stored_entries_are_bounded(self):
        memory = WithheldMemory(window_sec=1000.0, max_entries=2)
        for index in range(50):
            memory.record(_proposal(reason=f"r{index}"), {f"robot_{index}"}, now=float(index))
        assert len(memory) <= 8

    def test_expired_proposal_dropped(self):
        memory = WithheldMemory(window_sec=10.0, max_entries=3)
        memory.record(_proposal(), {"robot_2"}, now=0.0)
        assert memory.proposals_for(["robot_2"], now=10.5) == []

    def test_repeat_restarts_expiry(self):
        memory = WithheldMemory(window_sec=10.0, max_entries=3)
        memory.record(_proposal(), {"robot_2"}, now=0.0)
        memory.record(_proposal(), {"robot_2"}, now=8.0)
        assert memory.proposals_for(["robot_2"], now=15.0) == [_proposal(times=2)]

    def test_dispatch_to_overlapping_set_forgets(self):
        memory = WithheldMemory(window_sec=100.0, max_entries=3)
        memory.record(_proposal(), {"robot_2", "robot_3"}, now=0.0)
        other = _proposal(yield_robot="robot_5", involved_robots=("robot_5", "robot_1"))
        memory.record(other, {"robot_5", "robot_1"}, now=0.0)
        assert memory.forget_overlapping(["robot_3"]) == 1
        assert memory.proposals_for(["robot_2", "robot_5"], now=1.0) == [other]


class TestWithheldPlanMarking:
    def test_shown_plan_skips_withheld_plan(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        new = tracker.accept_plan(_verified(("robot_3", "wait")))
        assert tracker.mark_withheld(new.plan.plan_id) is True
        assert tracker.shown_plan().plan_id == 1

    def test_active_plan_unchanged_by_mark(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "wait")))
        new = tracker.accept_plan(_verified(("robot_3", "wait")))
        tracker.mark_withheld(new.plan.plan_id)
        assert tracker.active_plan.plan_id == new.plan.plan_id

    def test_hold_judged_against_unmarked_active_plan(self):
        # Dispatch-relevant decisions (holds, plan ids) are those of the
        # unmarked tracker, so the mark cannot change what M5 dispatches.
        marked, plain = PlanTracker(), PlanTracker()
        for tracker in (marked, plain):
            tracker.accept_plan(_verified(("robot_1", "wait")))
            tracker.accept_plan(_verified(("robot_3", "wait")))
        marked.mark_withheld(2)
        again = [t.accept_plan(_verified(("robot_3", "wait"))) for t in (marked, plain)]
        assert again[0].held == again[1].held and again[0].plan.plan_id == again[1].plan.plan_id

    def test_only_withheld_plans_shows_nothing(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "wait")))
        tracker.mark_withheld(first.plan.plan_id)
        assert tracker.shown_plan() is None

    def test_shown_plan_skips_a_chain_of_withheld_plans(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "wait")))
        for action in ("yield", "reverse"):
            tracker.mark_withheld(tracker.accept_plan(_verified(("robot_1", action))).plan.plan_id)
        assert tracker.shown_plan().plan_id == 1

    def test_shown_plan_keeps_latest_leg_statuses(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        new = tracker.accept_plan(_verified(("robot_3", "wait")))
        tracker.set_leg_status(1, "robot_1", "done")
        tracker.mark_withheld(new.plan.plan_id)
        assert [leg.status for leg in tracker.shown_plan().legs] == ["done", "pending"]

    def test_unknown_plan_not_marked(self):
        assert PlanTracker().mark_withheld(7) is False

    def test_shown_plan_equals_active_without_marks(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "wait")))
        assert tracker.shown_plan() == tracker.active_plan
