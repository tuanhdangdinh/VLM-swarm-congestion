import pytest
from pydantic import ValidationError

from reasoning.vlm.models import MotionTableEntry, RobotStateInput, SnapshotFrame


class TestSnapshotFrame:
    def test_find_robot_returns_matching_state(self):
        frame = SnapshotFrame(
            stamp=12.5,
            robots=[RobotStateInput(robot_id="robot_1", x=1.0, y=2.0, theta=0.0)],
        )
        state = frame.find_robot("robot_1")
        assert state is not None
        assert state.x == 1.0

    def test_find_robot_returns_none_for_unknown_id(self):
        frame = SnapshotFrame(stamp=0.0, robots=[])
        assert frame.find_robot("robot_9") is None

    def test_snapshot_frame_is_frozen(self):
        frame = SnapshotFrame(stamp=0.0, robots=[])
        with pytest.raises(ValidationError):
            frame.stamp = 1.0

    def test_snapshot_frame_rejects_negative_stamp(self):
        with pytest.raises(ValidationError):
            SnapshotFrame(stamp=-1.0, robots=[])


class TestMotionTableEntry:
    def test_arrival_fields_default_none(self):
        entry = MotionTableEntry(robot_id="robot_1")
        assert entry.arrival_order is None
        assert entry.arrival_stamp is None

    def test_arrival_order_rejects_zero(self):
        with pytest.raises(ValidationError):
            MotionTableEntry(robot_id="robot_1", arrival_order=0, arrival_stamp=0.0)
