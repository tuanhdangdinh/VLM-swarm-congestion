import pytest

from isaac.vgu_sim.diff_drive_oracle import forward_distance


def test_forward_distance_integrates_constant_speed():
    # 0.10 m/s for 2.0 s = 0.20 m
    assert forward_distance(0.10, 2.0) == pytest.approx(0.20, rel=1e-9)


def test_forward_distance_zero_duration_is_zero():
    assert forward_distance(0.10, 0.0) == 0.0


def test_forward_distance_zero_speed_is_zero():
    assert forward_distance(0.0, 3.0) == 0.0
