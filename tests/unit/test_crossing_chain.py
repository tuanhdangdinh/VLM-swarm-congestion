"""Unit tests for the ordered hold-until-last release chain (no ROS2 runtime)."""
from __future__ import annotations

import pytest
from swarm_execution.crossing_chain import CrossingChain, PasserPlan, plan_crossing


def _two_passer_parameters(**extra) -> dict:
    return {
        "passer_robot_id": "robot_1",
        "passer_clear_m": 2.6,
        "passer_escort_distance_m": 2.6,
        "crossing_order": ["robot_1", "robot_3"],
        "crossing_clear_m": [2.6, 4.9],
        "crossing_escort_m": [2.6, 4.9],
        **extra,
    }


def test_plan_without_passer_is_empty():
    assert plan_crossing({"backup_distance_m": 0.8, "hold_sec": 45.0}) == ()


def test_plan_single_passer_matches_legacy_parameters():
    plan = plan_crossing(
        {"passer_robot_id": "robot_2", "passer_clear_m": 2.4, "passer_escort_distance_m": 2.4}
    )

    assert plan == (PasserPlan("robot_2", 2.4, 2.4),)


def test_plan_single_passer_defaults_clear_distance_and_no_escort():
    assert plan_crossing({"passer_robot_id": "robot_2"}) == (PasserPlan("robot_2", 1.5, None),)


def test_plan_single_entry_crossing_order_is_single_passer():
    # The derived grounder always emits crossing_order, one entry for two robots.
    plan = plan_crossing(
        {"passer_robot_id": "robot_2", "passer_clear_m": 2.0, "crossing_order": ["robot_2"]}
    )

    assert plan == (PasserPlan("robot_2", 2.0, None),)


def test_plan_orders_every_passer_with_its_own_distances():
    assert plan_crossing(_two_passer_parameters()) == (
        PasserPlan("robot_1", 2.6, 2.6),
        PasserPlan("robot_3", 4.9, 4.9),
    )


def test_plan_later_passers_fall_back_to_first_passer_distances():
    parameters = _two_passer_parameters()
    del parameters["crossing_clear_m"]
    del parameters["crossing_escort_m"]

    assert plan_crossing(parameters) == (
        PasserPlan("robot_1", 2.6, 2.6),
        PasserPlan("robot_3", 2.6, 2.6),
    )


def test_plan_later_passers_unescorted_when_first_is_unescorted():
    parameters = _two_passer_parameters()
    del parameters["passer_escort_distance_m"]
    del parameters["crossing_escort_m"]

    assert [p.escort_m for p in plan_crossing(parameters)] == [None, None]


@pytest.mark.parametrize(
    "order",
    [
        ["robot_3", "robot_1"],  # disagrees with passer_robot_id
        ["robot_1", "robot_1"],  # duplicate
        ["robot_1", ""],
        "robot_1",
    ],
)
def test_plan_inconsistent_order_falls_back_to_single_passer(order):
    plan = plan_crossing(_two_passer_parameters(crossing_order=order))

    assert plan == (PasserPlan("robot_1", 2.6, 2.6),)


def test_plan_misaligned_distance_list_falls_back_to_first_passer_distance():
    plan = plan_crossing(_two_passer_parameters(crossing_clear_m=[2.6]))

    assert plan[1].clear_m == 2.6


def test_chain_starts_at_first_passer():
    chain = CrossingChain(plan_crossing(_two_passer_parameters()))

    assert chain.current.robot_id == "robot_1"
    assert chain.is_multi_passer is True


def test_chain_first_odometry_sample_is_the_reference():
    chain = CrossingChain((PasserPlan("robot_2", 1.5, None),))

    assert chain.on_odometry("robot_2", 10.0, 0.0) is None
    assert chain.on_odometry("robot_2", 8.6, 0.0) is None


def test_single_passer_clearing_finishes_the_chain():
    chain = CrossingChain((PasserPlan("robot_2", 1.5, None),))
    chain.on_odometry("robot_2", 0.3, 0.0)

    step = chain.on_odometry("robot_2", -1.3, 0.0)

    assert step is not None
    assert step.cleared.robot_id == "robot_2"
    assert step.next is None
    assert chain.finished is True


def test_first_passer_clearing_advances_to_second_passer():
    chain = CrossingChain(plan_crossing(_two_passer_parameters()))
    chain.on_odometry("robot_1", 0.0, 0.0)

    step = chain.on_odometry("robot_1", 2.7, 0.0)

    assert step.cleared.robot_id == "robot_1"
    assert step.next.robot_id == "robot_3"
    assert chain.current.robot_id == "robot_3"
    assert chain.finished is False


def test_later_passer_motion_ignored_until_its_turn():
    chain = CrossingChain(plan_crossing(_two_passer_parameters()))
    chain.on_odometry("robot_3", 0.0, 0.0)

    assert chain.on_odometry("robot_3", 9.0, 0.0) is None
    assert chain.current.robot_id == "robot_1"


def test_later_passer_displacement_measured_from_its_admission():
    chain = CrossingChain(plan_crossing(_two_passer_parameters()))
    chain.on_odometry("robot_3", -2.0, 0.0)  # sample before its turn: ignored
    chain.on_odometry("robot_1", 0.0, 0.0)
    chain.on_odometry("robot_1", 2.7, 0.0)

    assert chain.on_odometry("robot_3", -2.5, 0.0) is None  # reference
    assert chain.on_odometry("robot_3", 2.3, 0.0) is None  # 4.8 m < 4.9
    step = chain.on_odometry("robot_3", 2.5, 0.0)

    assert step.cleared.robot_id == "robot_3"
    assert step.next is None
    assert chain.finished is True


def test_finished_chain_ignores_further_odometry():
    chain = CrossingChain((PasserPlan("robot_2", 1.5, None),))
    chain.on_odometry("robot_2", 0.0, 0.0)
    chain.on_odometry("robot_2", 2.0, 0.0)

    assert chain.on_odometry("robot_2", 5.0, 0.0) is None


def test_chain_rejects_empty_plan():
    with pytest.raises(ValueError):
        CrossingChain(())


# prereg-v3 addendum A8 (i): `seed_reference` fixes the first passer's
# reference at the yield's dispatch, before its (pull-off-delayed) admission.


def test_seed_reference_measures_first_passer_from_the_seed():
    chain = CrossingChain([PasserPlan("robot_4", 2.65, None)])
    assert chain.seed_reference("robot_4", 0.0, 1.2) is True
    assert chain.on_odometry("robot_4", 0.0, -0.2) is None
    step = chain.on_odometry("robot_4", 0.0, -1.45)
    assert step is not None and step.next is None
    assert step.moved_m == pytest.approx(2.65)


def test_seed_reference_ignored_once_a_reference_exists():
    chain = CrossingChain([PasserPlan("robot_4", 1.0, None)])
    chain.on_odometry("robot_4", 0.0, 0.0)
    assert chain.seed_reference("robot_4", 0.0, 5.0) is False
    step = chain.on_odometry("robot_4", 0.0, -1.0)
    assert step is not None and step.moved_m == pytest.approx(1.0)


def test_seed_reference_ignored_for_another_robot():
    chain = CrossingChain([PasserPlan("robot_4", 1.0, None)])
    assert chain.seed_reference("robot_3", 0.0, 0.0) is False
    assert chain.on_odometry("robot_4", 0.0, 0.0) is None


def test_seed_reference_ignored_after_the_first_passer():
    chain = CrossingChain([PasserPlan("robot_4", 1.0, None), PasserPlan("robot_3", 1.0, None)])
    chain.on_odometry("robot_4", 0.0, 0.0)
    chain.on_odometry("robot_4", 0.0, 1.0)
    assert chain.seed_reference("robot_3", 0.0, 0.0) is False
