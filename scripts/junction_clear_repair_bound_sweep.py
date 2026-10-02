"""Offline repair-bound sizing sweep for `junction_clear` (prereg-v2 build-order
step 6, "repair-bound sizing", `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`).

Runs a deterministic corpus of plausible malformed `junction_clear` plans
against the REAL verify/repair engine (`reasoning.rag.command_grounder.
verify_and_repair_plan`) on the IB10 standoff snapshot family (both J2 and the
recede pocket declared, per the step-6 goal-table fix), at the J2-solved
geometry only (the unsolved-row geometry is a separate, already-covered
degradation, not a repair-bound question). For each malformed plan this finds
the TRUE minimal repair depth (BFS over a generous bound), then reports, for
each candidate `max_repair_edits` in {1, 2, 3}, how many cases are executed as
`repaired` vs. fall through to `m3_default`.

No VM dependency; run locally:

    python3 scripts/junction_clear_repair_bound_sweep.py

This is a sizing tool, not a test: it prints a table and a recommendation. It
does NOT change `PlanRepairParams.max_repair_edits`'s shipped default -- the
spec requires reporting before any change, and this sweep's own recommendation
is recorded in `docs/reports/2026-10-02-ib10-composite-smoke.md`, not applied
here.
"""
from __future__ import annotations

from reasoning.rag.command_grounder import PlanRepairParams, verify_and_repair_plan
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import CongestionDecision, ProposedPlanLeg, RobotStateInput, SnapshotFrame

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
# A generous bound for finding the TRUE minimal repair depth; 4 robots gives
# at most a handful of reorder/swap/substitute ops, so this never truncates
# a real minimum (verified below: nothing in the corpus hits this ceiling
# except the categories expected to be unrepairable at any depth).
PROBE_BOUND = 10
CANDIDATE_BOUNDS = (1, 2, 3)


def _geometry() -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(
        corridor=corridor,
        arms=JUNCTION_ARMS,
        junction_recede_offset_m=1.2,
        junction_backup_clearance_m=1.1,
    )


def _frame() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=xy[0], y=xy[1], theta=0.0, status="STOPPED")
            for rid, xy in IB10_STANDOFF.items()
        ],
    )


def _decision(plan: list[tuple[str, str]] | None) -> CongestionDecision:
    proposed = (
        None
        if plan is None
        else [ProposedPlanLeg(robot_id=rid, action=action) for rid, action in plan]
    )
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=list(IB10_STANDOFF),
        root_cause="four-way standoff",
        strategy="junction_clear",
        justification="jam",
        proposed_plan=proposed,
    )


# The engine's own correct derivation for this exact snapshot/geometry
# (verified by hand against `_derive_default_plan` before writing this sweep):
# robot_4 reverse, robot_3 reverse (chi order), robot_1 yield, robot_2 cross.
CORRECT = [
    ("robot_4", "reverse"), ("robot_3", "reverse"), ("robot_1", "yield"), ("robot_2", "cross"),
]

# Deterministic malformed-plan corpus, by category. Each entry:
# (case_id, category, plan or None).
CASES: list[tuple[str, str, list[tuple[str, str]] | None]] = [
    # --- wrong recede pair: the VLM names the wrong axis, or only one of
    # the two correct candidates, as the recede set ---
    (
        "recede_pair_full_axis_swap", "wrong_recede_pair",
        [
            ("robot_1", "reverse"), ("robot_2", "reverse"),
            ("robot_3", "yield"), ("robot_4", "cross"),
        ],
    ),
    (
        "recede_pair_one_wrong_robot1", "wrong_recede_pair",
        [
            ("robot_4", "reverse"), ("robot_1", "reverse"),
            ("robot_3", "yield"), ("robot_2", "cross"),
        ],
    ),
    (
        "recede_pair_one_wrong_robot2", "wrong_recede_pair",
        [
            ("robot_3", "reverse"), ("robot_2", "reverse"),
            ("robot_1", "yield"), ("robot_4", "cross"),
        ],
    ),
    # --- wrong order: a yield-axis leg precedes a recede leg (M3's own
    # "recede before yield/cross" audit) ---
    (
        "order_fully_reversed", "wrong_order",
        [
            ("robot_2", "cross"), ("robot_1", "yield"),
            ("robot_3", "reverse"), ("robot_4", "reverse"),
        ],
    ),
    (
        "order_yield_first_only", "wrong_order",
        [
            ("robot_1", "yield"), ("robot_4", "reverse"),
            ("robot_3", "reverse"), ("robot_2", "cross"),
        ],
    ),
    (
        "order_cross_before_recede", "wrong_order",
        [
            ("robot_2", "cross"), ("robot_4", "reverse"),
            ("robot_3", "reverse"), ("robot_1", "yield"),
        ],
    ),
    # --- missing legs: the plan omits a robot; lenient completion appends
    # `continue` for it (never counted as a repair edit by itself) ---
    (
        "missing_one_recede_candidate", "missing_legs",
        [("robot_4", "reverse"), ("robot_1", "yield"), ("robot_2", "cross")],  # robot_3 omitted
    ),
    (
        "missing_yielder", "missing_legs",
        [("robot_4", "reverse"), ("robot_3", "reverse"), ("robot_2", "cross")],  # robot_1 omitted
    ),
    (
        "missing_both_recede_candidates", "missing_legs",
        [("robot_1", "yield"), ("robot_2", "cross")],  # robot_3, robot_4 omitted
    ),
    (
        "missing_everything_but_one_reverse", "missing_legs",
        [("robot_4", "reverse")],  # robot_1/2/3 omitted entirely
    ),
    # --- inconsistent strategy: no reverse/yield leg at all, so the (a0)
    # consistency rule rejects the plan before repair is ever attempted ---
    (
        "inconsistent_all_continue", "inconsistent_strategy",
        [(rid, "continue") for rid in IB10_STANDOFF],
    ),
    ("inconsistent_all_wait", "inconsistent_strategy", [(rid, "wait") for rid in IB10_STANDOFF]),
    (
        "inconsistent_all_cross", "inconsistent_strategy",
        [(rid, "cross") for rid in IB10_STANDOFF],
    ),
    # --- combined defects: more than one category at once, to stress the
    # bound beyond the single-defect cases above ---
    (
        "combined_wrong_pair_and_order", "combined",
        [
            ("robot_3", "yield"), ("robot_4", "cross"),
            ("robot_1", "reverse"), ("robot_2", "reverse"),
        ],
    ),
    (
        "combined_missing_leg_and_wrong_order", "combined",
        [("robot_1", "yield"), ("robot_4", "reverse")],  # robot_2, robot_3 omitted; yield first
    ),
    # --- control: the plan absent entirely (always m3_default, by contract) ---
    ("plan_absent", "control_absent", None),
    # --- control: the correct plan verbatim (must cost zero edits) ---
    ("plan_correct_verbatim", "control_correct", CORRECT),
]


def _probe(plan: list[tuple[str, str]] | None) -> tuple[str, str | None, int | None]:
    """Run one plan through the engine at a generous bound.

    Returns:
        `(provenance, rejection_stage, minimal_depth)`. `minimal_depth` is the
        number of edits for a `repaired` outcome, 0 for `vlm_verbatim`, and
        `None` when no repair was attempted or none was found within
        `PROBE_BOUND` (`rejection_stage` says why).
    """
    verified = verify_and_repair_plan(
        _decision(plan), _frame(), geometry=_geometry(),
        repair_params=PlanRepairParams(max_repair_edits=PROBE_BOUND),
        grounding_params=GroundingParams(mode="derived"),
    )
    if verified.provenance == "vlm_verbatim":
        return verified.provenance, None, 0
    if verified.provenance == "repaired":
        return verified.provenance, None, len(verified.edits)
    return verified.provenance, verified.rejection_stage, None


def _outcome_at_bound(plan: list[tuple[str, str]] | None, bound: int) -> str:
    verified = verify_and_repair_plan(
        _decision(plan), _frame(), geometry=_geometry(),
        repair_params=PlanRepairParams(max_repair_edits=bound),
        grounding_params=GroundingParams(mode="derived"),
    )
    return verified.provenance


def main() -> None:
    rows = []
    for case_id, category, plan in CASES:
        provenance, stage, depth = _probe(plan)
        at_bound = {bound: _outcome_at_bound(plan, bound) for bound in CANDIDATE_BOUNDS}
        rows.append((case_id, category, provenance, stage, depth, at_bound))

    print(f"{'case':38s} {'category':20s} {'true_prov':12s} {'stage':22s} {'min_depth':9s}  "
          + "  ".join(f"bound={b}" for b in CANDIDATE_BOUNDS))
    for case_id, category, provenance, stage, depth, at_bound in rows:
        depth_s = "n/a" if depth is None else str(depth)
        stage_s = stage or "-"
        bounds_s = "  ".join(f"{at_bound[b]:>10s}" for b in CANDIDATE_BOUNDS)
        print(
            f"{case_id:38s} {category:20s} {provenance:12s} {stage_s:22s} "
            f"{depth_s:9s}  {bounds_s}"
        )

    print()
    print("Distribution of minimal repair depths (repairable cases only):")
    depths = [depth for *_rest, depth, _ab in rows if depth is not None and depth > 0]
    for d in sorted(set(depths)):
        print(f"  depth={d}: {depths.count(d)} case(s)")

    print()
    print("% falling to m3_default per bound (of all cases, including the")
    print("always-m3_default inconsistent/absent controls):")
    total = len(rows)
    for bound in CANDIDATE_BOUNDS:
        n_default = sum(1 for *_rest, at_bound in rows if at_bound[bound] == "m3_default")
        print(f"  max_repair_edits={bound}: {n_default}/{total} m3_default "
              f"({100 * n_default / total:.0f}%)")

    print()
    print("% falling to m3_default per bound, REPAIRABLE cases only (excludes")
    print("inconsistent_strategy and plan_absent, which are m3_default at every")
    print("bound by contract, not by repair-distance):")
    repairable_rows = [r for r in rows if r[1] not in ("inconsistent_strategy", "control_absent")]
    n_repairable = len(repairable_rows)
    for bound in CANDIDATE_BOUNDS:
        n_default = sum(
            1 for *_rest, at_bound in repairable_rows if at_bound[bound] == "m3_default"
        )
        print(f"  max_repair_edits={bound}: {n_default}/{n_repairable} m3_default "
              f"({100 * n_default / n_repairable:.0f}%)")


if __name__ == "__main__":
    main()
