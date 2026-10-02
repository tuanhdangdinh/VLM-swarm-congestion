"""Unit tests for M5's pure plan-state tracker (prereg-v2 rev 4, "Plan lifecycle")."""

import threading

import pytest
from swarm_orchestrator.plan_tracker import PlanTracker

from reasoning.rag.command_grounder import PlanEdit, VerifiedPlan
from reasoning.rag.plan_metrics import classify_revision_cause
from reasoning.vlm.models import ProposedPlanLeg


def _verified(
    *legs: tuple[str, str],
    provenance: str = "vlm_verbatim",
    edits: list[PlanEdit] | None = None,
) -> VerifiedPlan:
    return VerifiedPlan(
        legs=[ProposedPlanLeg(robot_id=rid, action=action) for rid, action in legs],
        provenance=provenance,
        edits=edits or [],
    )


# ---- plan_id assignment ----


class TestPlanIdAssignment:
    def test_first_accepted_plan_gets_id_one(self):
        tracker = PlanTracker()
        acceptance = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert acceptance.plan.plan_id == 1
        assert acceptance.supersedes is None

    def test_plan_ids_are_monotonic_across_accepts(self):
        # Each accept must genuinely differ from the one before it, or the
        # hold ruling (2026-10-02) re-affirms instead of minting a new id.
        tracker = PlanTracker()
        actions = ["wait", "yield", "wait"]
        ids = [
            tracker.accept_plan(_verified(("robot_1", action))).plan.plan_id
            for action in actions
        ]
        assert ids == [1, 2, 3]

    def test_m3_default_plans_get_a_plan_id_too(self):
        # "every accepted plan (including m3_default ones) ... every executed
        # resolution has a plan" (prereg-v2 (a0)).
        tracker = PlanTracker()
        acceptance = tracker.accept_plan(
            _verified(("robot_1", "wait"), provenance="m3_default")
        )
        assert acceptance.plan.plan_id == 1
        assert acceptance.plan.provenance == "m3_default"

    def test_active_plan_tracks_the_most_recently_accepted(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "wait")))
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert tracker.active_plan is not None
        assert tracker.active_plan.plan_id == second.plan.plan_id == 2

    def test_plan_lookup_by_id_returns_a_superseded_plan_too(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "wait")))
        tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert tracker.plan(first.plan.plan_id) is not None
        assert tracker.plan(first.plan.plan_id).plan_id == first.plan.plan_id

    def test_unknown_plan_id_lookup_returns_none(self):
        tracker = PlanTracker()
        assert tracker.plan(999) is None

    def test_before_any_accept_active_plan_is_none(self):
        assert PlanTracker().active_plan is None


# ---- per-leg status state machine ----


class TestLegStatusStateMachine:
    def test_legs_start_pending(self):
        tracker = PlanTracker()
        acceptance = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert {leg.robot_id: leg.status for leg in acceptance.plan.legs} == {
            "robot_1": "pending",
            "robot_2": "pending",
        }

    @pytest.mark.parametrize(
        "path",
        [
            ["active", "done"],
            ["active", "failed"],
            ["pending", "done"],
            ["pending", "failed"],
            ["pending", "active", "active", "done"],
        ],
    )
    def test_legal_transition_sequences_succeed(self, path):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        for status in path:
            leg = tracker.set_leg_status(plan_id, "robot_1", status)
            assert leg.status == status

    @pytest.mark.parametrize(
        "terminal",
        ["done", "failed"],
    )
    @pytest.mark.parametrize("attempted", ["pending", "active", "done", "failed"])
    def test_terminal_status_never_changes_again_unless_idempotent(self, terminal, attempted):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", terminal)
        if attempted == terminal:
            # Re-reporting the same terminal status is a no-op, not an error.
            assert tracker.set_leg_status(plan_id, "robot_1", attempted).status == terminal
        else:
            with pytest.raises(ValueError, match="invalid leg status transition"):
                tracker.set_leg_status(plan_id, "robot_1", attempted)

    def test_active_cannot_revert_to_pending(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", "active")
        with pytest.raises(ValueError, match="invalid leg status transition"):
            tracker.set_leg_status(plan_id, "robot_1", "pending")

    @pytest.mark.parametrize("origin", ["pending", "active", "failed"])
    def test_exhausted_is_reachable_from_pending_active_or_failed(self, origin):
        # Step-7a fix (freeze-blocking finding 5): `orchestrator_node.
        # _mark_fallback_exhausted` marks EVERY one of a failed fallback's
        # robots `exhausted`, including one still `pending` (held through
        # every phase, never individually resolved) or `active`, not only
        # one already `failed` from an earlier phase.
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        if origin != "pending":
            tracker.set_leg_status(plan_id, "robot_1", origin)
        leg = tracker.set_leg_status(plan_id, "robot_1", "exhausted")
        assert leg.status == "exhausted"

    def test_exhausted_is_terminal(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", "exhausted")
        # Re-reporting the same terminal status is a no-op, not an error.
        assert tracker.set_leg_status(plan_id, "robot_1", "exhausted").status == "exhausted"
        with pytest.raises(ValueError, match="invalid leg status transition"):
            tracker.set_leg_status(plan_id, "robot_1", "done")
        with pytest.raises(ValueError, match="invalid leg status transition"):
            tracker.set_leg_status(plan_id, "robot_1", "failed")

    def test_done_cannot_become_exhausted(self):
        # A genuinely completed leg is never retroactively exhausted.
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", "done")
        with pytest.raises(ValueError, match="invalid leg status transition"):
            tracker.set_leg_status(plan_id, "robot_1", "exhausted")

    def test_unknown_plan_id_raises_key_error(self):
        tracker = PlanTracker()
        with pytest.raises(KeyError):
            tracker.set_leg_status(999, "robot_1", "active")

    def test_unknown_robot_id_raises_key_error(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        with pytest.raises(KeyError):
            tracker.set_leg_status(plan_id, "robot_9", "active")

    def test_status_update_is_reflected_on_the_active_plan_snapshot(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", "active")
        assert tracker.active_plan.leg_for("robot_1").status == "active"

    def test_status_update_on_a_superseded_plan_does_not_touch_the_active_one(self):
        tracker = PlanTracker()
        old_id = tracker.accept_plan(_verified(("robot_1", "wait"))).plan.plan_id
        new = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(old_id, "robot_1", "failed")
        assert tracker.plan(old_id).leg_for("robot_1").status == "failed"
        assert tracker.active_plan.plan_id == new.plan.plan_id
        assert tracker.active_plan.leg_for("robot_1").status == "pending"


# ---- supersession and dependency-order cancellation ----


class TestSupersessionCancelOrder:
    def test_first_plan_has_no_supersession(self):
        tracker = PlanTracker()
        acceptance = tracker.accept_plan(_verified(("robot_1", "wait")))
        assert acceptance.supersedes is None

    def test_second_plan_explicitly_supersedes_the_first(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "wait")))
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.supersedes is not None
        assert second.supersedes.superseded_plan_id == first.plan.plan_id
        assert second.supersedes.new_plan_id == second.plan.plan_id

    def test_cancel_order_is_the_reverse_of_the_old_plans_leg_order(self):
        # Old plan: yielder first, then two passers in crossing order
        # (_derive_default_plan's convention: [yielder, *crossing_order]).
        # A totally different new plan changes every robot's action, so every
        # old leg is cancelled, tail of the OLD order first.
        tracker = PlanTracker()
        tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "cross"))
        )
        second = tracker.accept_plan(
            _verified(("robot_1", "wait"), ("robot_2", "wait"), ("robot_3", "wait"))
        )
        assert second.supersedes.cancel_order == ("robot_3", "robot_2", "robot_1")

    def test_a_leg_the_new_plan_carries_forward_unchanged_is_not_cancelled(self):
        tracker = PlanTracker()
        tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "cross"))
        )
        # Only robot_3's role changes (reordered/repaired to wait); robot_1 and
        # robot_2 keep their exact same action.
        second = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "wait"))
        )
        assert second.supersedes.cancel_order == ("robot_3",)

    def test_an_already_done_leg_is_never_cancelled(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_2", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_2", "done")
        second = tracker.accept_plan(_verified(("robot_1", "wait"), ("robot_2", "wait")))
        # robot_2's old leg is already done -- cancelling it would be
        # retiring a maneuver that already finished.
        assert second.supersedes.cancel_order == ("robot_1",)

    def test_a_plan_with_no_changed_legs_is_a_hold_not_a_supersession(self):
        # Superseded by the hold ruling (2026-10-02): an accept whose legs are
        # identical to the active plan's remaining legs is now a HOLD, not an
        # explicit supersession that happens to cancel nothing -- see
        # TestHoldSemantics below.
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.held is True
        assert second.supersedes is None

    def test_a_robot_the_new_plan_drops_entirely_is_cancelled(self):
        tracker = PlanTracker()
        tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "continue"))
        )
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.supersedes.cancel_order == ("robot_3",)


# ---- hold semantics (ruling 2026-10-02) ----


class TestHoldSemantics:
    def test_hold_on_identical_remaining_legs(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.held is True
        assert second.plan.plan_id == first.plan.plan_id
        assert second.supersedes is None

    def test_replan_on_different_legs(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        second = tracker.accept_plan(_verified(("robot_1", "wait"), ("robot_2", "cross")))
        assert second.held is False
        assert second.plan.plan_id == first.plan.plan_id + 1
        assert second.supersedes is not None
        assert second.supersedes.superseded_plan_id == first.plan.plan_id

    def test_reordered_same_actions_is_a_replan_not_a_hold(self):
        # Same per-robot actions, different execution order -- a REORDER
        # repair, exactly one of the revisions plan-stability must catch, so
        # it must never be absorbed into a hold.
        tracker = PlanTracker()
        first = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "cross"))
        )
        second = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_3", "cross"), ("robot_2", "cross"))
        )
        assert second.held is False
        assert second.plan.plan_id == first.plan.plan_id + 1

    def test_an_added_robot_the_active_plan_did_not_cover_is_a_replan(self):
        # A scene-wide plan gaining a leg for a robot the active plan's
        # remaining legs never named is not identical, even though every
        # robot the active plan DOES cover is unchanged.
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        second = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"), ("robot_3", "continue"))
        )
        assert second.held is False
        assert second.plan.plan_id == first.plan.plan_id + 1

    def test_hold_survives_after_some_remaining_legs_are_done(self):
        # robot_1's leg completes; robot_2's "cross" is still open. A new
        # analysis that still names the SAME action for robot_2 (whatever it
        # says, or omits, about the now-done robot_1) is a hold.
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "done")
        second = tracker.accept_plan(_verified(("robot_1", "continue"), ("robot_2", "cross")))
        assert second.held is True
        assert second.plan.plan_id == first.plan.plan_id

    def test_a_done_robots_action_is_not_compared_at_all(self):
        # Same scenario, but the new plan re-proposes a DIFFERENT action for
        # the already-done robot_1 -- still a hold, because only the
        # remaining (non-done) legs are compared.
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "done")
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.held is True
        assert second.plan.plan_id == first.plan.plan_id

    def test_replan_when_the_one_remaining_leg_after_completion_changes(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "done")
        second = tracker.accept_plan(_verified(("robot_1", "continue"), ("robot_2", "wait")))
        assert second.held is False
        assert second.supersedes.superseded_plan_id == first.plan.plan_id

    def test_failed_leg_reproposed_identically_is_an_evidence_driven_replan(self):
        # REFINEMENT (2026-10-02, spec "(a0) Hold semantics", landed with
        # build-order step 5): "non-done" (the ruling's own wording) includes
        # `failed`, not just `pending`/`active`, so without this refinement
        # a re-analysis that proposes the EXACT SAME action for a robot
        # whose leg just FAILED (e.g. a retry after a timeout) would read as
        # a hold, not an evidence-driven replan. Previously pinned as a
        # FLAGGED gap by
        # `test_failed_leg_reproposed_identically_is_still_a_hold_flagged_gap`;
        # now pins the ruling instead -- a retry after a failure always gets
        # a NEW plan_id and is classifiable `evidence_driven`
        # (`plan_metrics.classify_revision_cause(["robot_1"])`).
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "failed")
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.held is False
        assert second.plan.plan_id == first.plan.plan_id + 1
        assert second.supersedes is not None
        assert second.supersedes.superseded_plan_id == first.plan.plan_id
        assert classify_revision_cause(["robot_1"]) == "evidence_driven"

    def test_a_plan_where_every_leg_is_already_done_is_never_a_hold(self):
        # Nothing remains to re-affirm; the next accepted plan is judged
        # fresh, even if its content happens to repeat the exhausted one.
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "done")
        second = tracker.accept_plan(_verified(("robot_1", "yield")))
        assert second.held is False
        assert second.plan.plan_id == first.plan.plan_id + 1

    def test_the_first_accepted_plan_is_never_a_hold(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield")))
        assert first.held is False

    def test_hold_does_not_reset_leg_statuses(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
        second = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        assert second.held is True
        assert second.plan.leg_for("robot_1").status == "active"
        assert second.plan.leg_for("robot_2").status == "pending"
        assert tracker.active_plan.leg_for("robot_1").status == "active"

    def test_hold_does_not_consume_a_plan_id(self):
        tracker = PlanTracker()
        tracker.accept_plan(_verified(("robot_1", "yield")))
        tracker.accept_plan(_verified(("robot_1", "yield")))  # hold
        third = tracker.accept_plan(_verified(("robot_1", "wait")))  # genuine replan
        assert third.plan.plan_id == 2

    def test_plan_holds_counter_increments_only_on_a_hold(self):
        tracker = PlanTracker()
        assert tracker.plan_holds == 0
        tracker.accept_plan(_verified(("robot_1", "yield")))
        assert tracker.plan_holds == 0  # the episode's first plan is never a hold
        tracker.accept_plan(_verified(("robot_1", "yield")))  # hold
        assert tracker.plan_holds == 1
        tracker.accept_plan(_verified(("robot_1", "yield")))  # hold again
        assert tracker.plan_holds == 2
        tracker.accept_plan(_verified(("robot_1", "wait")))  # genuine replan
        assert tracker.plan_holds == 2


# ---- plan-state context for the prompt-v3 plan-state block ----


class TestPlanStateContext:
    def test_first_invocation_has_no_changed_robots(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        context = tracker.plan_state_context(plan_id, since_plan_id=None)
        assert context.plan_id == plan_id
        assert context.changed_robot_ids == ()

    def test_same_plan_shown_twice_has_no_changed_robots_the_second_time(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        context = tracker.plan_state_context(plan_id, since_plan_id=plan_id)
        assert context.changed_robot_ids == ()

    def test_a_new_plan_reports_its_changed_robots_against_the_superseded_one(self):
        tracker = PlanTracker()
        first_id = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"))
        ).plan.plan_id
        second_id = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "wait"))
        ).plan.plan_id
        context = tracker.plan_state_context(second_id, since_plan_id=first_id)
        assert context.changed_robot_ids == ("robot_2",)

    def test_plan_state_context_carries_every_legs_action_and_status(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"))
        ).plan.plan_id
        tracker.set_leg_status(plan_id, "robot_1", "active")
        context = tracker.plan_state_context(plan_id, since_plan_id=None)
        by_robot = {leg.robot_id: (leg.action, leg.status) for leg in context.legs}
        assert by_robot == {"robot_1": ("yield", "active"), "robot_2": ("cross", "pending")}

    def test_unknown_plan_id_raises_key_error(self):
        tracker = PlanTracker()
        with pytest.raises(KeyError):
            tracker.plan_state_context(999, since_plan_id=None)

    def test_unknown_since_plan_id_raises_key_error(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(_verified(("robot_1", "yield"))).plan.plan_id
        with pytest.raises(KeyError):
            tracker.plan_state_context(plan_id, since_plan_id=999)


# ---- concurrency: accept_plan (pipeline worker thread) vs set_leg_status /
# plan_state_context (rclpy spin thread), per orchestrator_node.py's threading
# model (`InProcessPipeline.run` is submitted to a `ThreadPoolExecutor`; status
# callbacks and request-building run on the spin thread) ----


class TestConcurrentAccess:
    def test_active_plan_never_reverts_under_concurrent_accept_and_status_updates(self):
        tracker = PlanTracker()
        first = tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", "cross")))
        plan_count = 200

        def accept_many() -> None:
            # Alternate the legs every iteration so each accept genuinely
            # differs from the one immediately before it -- an identical
            # accept is a hold (ruling 2026-10-02) and would not mint a new
            # plan_id, which would break this test's own plan_id arithmetic
            # independently of the race it is checking for.
            for i in range(plan_count):
                # Start on "wait" (i=0): the already-active first plan is
                # "cross", so every iteration differs from whatever was
                # active just before it.
                robot_2_action = "wait" if i % 2 == 0 else "cross"
                tracker.accept_plan(_verified(("robot_1", "yield"), ("robot_2", robot_2_action)))

        def update_first_plan_status() -> None:
            # Hammers the FIRST plan's leg status concurrently with new plans
            # being accepted; without PlanTracker's internal lock, a
            # `set_leg_status` call that reads `self._active` as the first
            # plan (stale) and later writes `self._active = updated_plan`
            # could race a concurrent `accept_plan` and revert the active
            # plan pointer back to a superseded one.
            for _ in range(plan_count):
                try:
                    tracker.set_leg_status(first.plan.plan_id, "robot_1", "active")
                except ValueError:
                    pass  # already terminal/active from a previous iteration

        threads = [
            threading.Thread(target=accept_many),
            threading.Thread(target=update_first_plan_status),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # The last-accepted plan must still be active: plan_id 1 + plan_count
        # new accepts (the first accept_plan above, plus plan_count more).
        assert tracker.active_plan is not None
        assert tracker.active_plan.plan_id == 1 + plan_count

    def test_set_leg_status_and_plan_state_context_do_not_corrupt_each_other(self):
        tracker = PlanTracker()
        plan_id = tracker.accept_plan(
            _verified(("robot_1", "yield"), ("robot_2", "cross"))
        ).plan.plan_id
        errors: list[Exception] = []

        def flip_status() -> None:
            for status in ["active", "done"] * 100:
                try:
                    tracker.set_leg_status(plan_id, "robot_1", status)
                except ValueError:
                    pass

        def read_state() -> None:
            for _ in range(200):
                try:
                    tracker.plan_state_context(plan_id, since_plan_id=None)
                except Exception as exc:  # pragma: no cover - failure path only
                    errors.append(exc)

        threads = [threading.Thread(target=flip_status), threading.Thread(target=read_state)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
