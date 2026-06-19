# tests/unit/test_m6_stop_stub.py
import math

import pytest

sensor_msgs = pytest.importorskip("sensor_msgs", reason="sensor_msgs requires ROS 2")
from sensor_msgs.msg import LaserScan


def _make_scan(ranges: list[float], angle_increment_deg: float = 1.0) -> LaserScan:
    msg = LaserScan()
    msg.angle_increment = math.radians(angle_increment_deg)
    msg.ranges = [float(r) for r in ranges]
    return msg


class TestStopStub:
    def setup_method(self):
        # Import here so rclpy/geometry_msgs import failures are deferred
        from tests.simulation.stop_stub import StopStub
        self.StopStub = StopStub

    def test_moves_when_path_clear(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        # 360 ranges all at 3.0 m (clear)
        scan = _make_scan([3.0] * 360)
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.10)
        assert cmd.angular.z == pytest.approx(0.0)

    def test_stops_when_obstacle_close_in_front(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        # First 30 ranges (forward sector) at 0.20 m (< 0.25 threshold)
        ranges = [0.20] * 30 + [3.0] * 330
        scan = _make_scan(ranges)
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.0)

    def test_does_not_stop_for_side_walls(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        # Side ranges (indices 90-270) close, forward clear
        ranges = [3.0] * 360
        for i in range(90, 271):
            ranges[i] = 0.10
        scan = _make_scan(ranges)
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.10)

    def test_empty_scan_returns_zero_twist(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        scan = _make_scan([])
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.0)

    def test_speed_limit_enforced(self):
        with pytest.raises(ValueError, match="0.15"):
            self.StopStub("robot_1", speed_mps=0.20)

    def test_stops_at_exact_threshold(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        # Forward obstacle at exactly 0.25 m should allow movement (>= threshold)
        ranges = [0.25] * 30 + [3.0] * 330
        scan = _make_scan(ranges)
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.10)

    def test_nan_ranges_ignored(self):
        stub = self.StopStub("robot_1", speed_mps=0.10)
        # Forward NaN and inf should be filtered; path treated as clear
        ranges = [float("nan")] * 30 + [3.0] * 330
        scan = _make_scan(ranges)
        cmd = stub.on_scan(scan)
        assert cmd.linear.x == pytest.approx(0.10)


class TestFixedTwistDriver:
    def test_speed_limit_enforced(self):
        # FixedTwistDriver reuses the StopStub speed guard (FR6.8.5a). The cap is
        # checked before super().__init__, so this raises without a ROS context.
        from tests.simulation.stop_stub import FixedTwistDriver

        with pytest.raises(ValueError, match="0.15"):
            FixedTwistDriver(["robot_1"], speed_mps=0.20)
