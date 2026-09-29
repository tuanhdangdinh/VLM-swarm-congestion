import pytest

from isaac.vgu_sim.oracle import (
    anomaly_conflict_active,
    bottleneck_conflict_active,
    classify_speed,
    head_on_conflict_active,
    intersection_conflict_active,
    is_slow,
    is_stopped,
)


def test_is_stopped_below_threshold():
    assert is_stopped(0.005) is True


def test_is_stopped_at_threshold():
    assert is_stopped(0.01) is False  # strictly less than


def test_is_slow_below_threshold():
    assert is_slow(0.02) is True


def test_is_slow_at_threshold():
    assert is_slow(0.03) is False  # strictly less than


def test_classify_speed_stopped():
    assert classify_speed(0.0) == "STOPPED"


def test_classify_speed_slow():
    assert classify_speed(0.02) == "SLOW"


def test_classify_speed_moving():
    assert classify_speed(0.1) == "MOVING"


def test_head_on_active_when_both_stopped_and_close():
    positions = [(-0.2, 0.0), (0.2, 0.0)]
    speeds = [0.005, 0.005]
    assert head_on_conflict_active(positions, speeds) is True


def test_head_on_not_active_when_too_far():
    positions = [(-1.0, 0.0), (1.0, 0.0)]
    speeds = [0.005, 0.005]
    assert head_on_conflict_active(positions, speeds) is False


def test_head_on_not_active_when_one_moving():
    positions = [(-0.2, 0.0), (0.2, 0.0)]
    speeds = [0.005, 0.15]
    assert head_on_conflict_active(positions, speeds) is False


def test_intersection_active_three_in_radius():
    positions = [(0.3, 0.0), (-0.3, 0.0), (0.0, 0.3), (2.0, 2.0)]
    speeds = [0.01, 0.01, 0.01, 0.15]
    assert intersection_conflict_active(positions, speeds) is True


def test_intersection_not_active_only_two_in_radius():
    positions = [(0.3, 0.0), (-0.3, 0.0), (2.0, 2.0), (2.0, -2.0)]
    speeds = [0.01, 0.01, 0.01, 0.01]
    assert intersection_conflict_active(positions, speeds) is False


def test_intersection_not_active_mean_speed_too_high():
    positions = [(0.3, 0.0), (-0.3, 0.0), (0.0, 0.3), (0.0, -0.3)]
    speeds = [0.05, 0.05, 0.05, 0.05]
    assert intersection_conflict_active(positions, speeds) is False


def test_anomaly_active_when_obstacle_present_and_robot_slow_upstream():
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(0.5, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=True) is True


def test_anomaly_not_active_when_obstacle_absent():
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(0.5, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=False) is False


def test_anomaly_not_active_when_robot_too_far():
    obstacle_pose = (1.5, 0.0)
    robot_positions = [(-1.0, 0.0)]
    robot_speeds = [0.01]
    assert anomaly_conflict_active(obstacle_pose, robot_positions, robot_speeds, obstacle_active=True) is False


B1_GATE = (0.7, 1.7)  # bottleneck_merge A55-E: barrier centre 1.2, length 1.0
B3_GATE = (-0.5, 0.5)  # convoy_counterflow A55-J: barrier centre 0.0, length 1.0


def test_bottleneck_active_at_the_b1_designed_merge_latch():
    positions = [(0.10, 0.0), (0.15, 0.45), (-2.45, 0.0)]
    speeds = [0.0, 0.0, 0.0]
    assert bottleneck_conflict_active(positions, speeds, B1_GATE) is True


def test_bottleneck_active_at_the_b3_head_on_standoff_inside_the_gate():
    positions = [(-0.12, 0.0), (0.12, 0.0), (-1.9, 0.0), (-2.47, 0.0)]
    assert bottleneck_conflict_active(positions, [0.0] * 4, B3_GATE) is True


def test_bottleneck_inactive_when_one_of_the_pair_moves():
    positions = [(0.10, 0.0), (0.15, 0.45)]
    assert bottleneck_conflict_active(positions, [0.0, 0.05], B1_GATE) is False


def test_bottleneck_inactive_for_the_b3_held_queue_at_spawn():
    # robot_1-robot_3 are 0.70 m apart but their midpoint (-1.55, 0) is 1.05 m
    # from the gate's west mouth; robot_3-robot_4 sit further out still.
    positions = [(-1.2, 0.0), (1.2, 0.0), (-1.9, 0.0), (-2.47, 0.0)]
    assert bottleneck_conflict_active(positions, [0.0] * 4, B3_GATE) is False


def test_bottleneck_inactive_for_robots_parked_at_neighbouring_goals():
    # B1 goals (2.45, -0.3) and (2.45, 0.3): 0.6 m apart, midpoint 0.75 m
    # from the east mouth, but both robots are at their goals.
    positions = [(2.45, -0.3), (2.45, 0.3)]
    assert bottleneck_conflict_active(
        positions, [0.0, 0.0], B1_GATE, distances_to_goal=[0.02, 0.03]
    ) is False


def test_bottleneck_counts_goal_parked_pair_without_goal_distances():
    positions = [(2.45, -0.3), (2.45, 0.3)]
    assert bottleneck_conflict_active(positions, [0.0, 0.0], B1_GATE) is True


def test_bottleneck_inactive_when_pair_is_too_far_apart():
    positions = [(0.0, 0.0), (0.0, 0.85)]
    assert bottleneck_conflict_active(positions, [0.0, 0.0], B1_GATE) is False


def test_bottleneck_inactive_when_pair_is_far_from_the_gate():
    positions = [(-1.8, 0.0), (-1.4, 0.0)]
    assert bottleneck_conflict_active(positions, [0.0, 0.0], B1_GATE) is False


def test_bottleneck_active_for_a_follower_latch_at_the_gate_mouth():
    positions = [(0.5, 0.0), (0.18, 0.0)]
    assert bottleneck_conflict_active(positions, [0.0, 0.0], B1_GATE) is True


def test_bottleneck_rejects_misaligned_inputs():
    with pytest.raises(ValueError):
        bottleneck_conflict_active([(0.0, 0.0)], [0.0, 0.0], B1_GATE)


def test_bottleneck_rejects_a_reversed_span():
    with pytest.raises(ValueError):
        bottleneck_conflict_active([(0.0, 0.0)], [0.0], (1.7, 0.7))
