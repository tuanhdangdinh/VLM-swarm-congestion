import pytest
from isaac.vgu_sim.oracle import (
    is_stopped,
    is_slow,
    head_on_conflict_active,
    intersection_conflict_active,
    anomaly_conflict_active,
    classify_speed,
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
