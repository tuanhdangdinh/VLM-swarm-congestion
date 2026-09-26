import pytest

from reasoning.vlm.models import RobotStateInput, SnapshotFrame
from reasoning.vlm.motion_table import derive_motion_table


def _frame(stamp: float, *robots: tuple[str, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=stamp,
        robots=[RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0) for rid, x, y in robots],
    )


class TestDeriveMotionTable:
    def test_arrival_order_follows_zone_entry_sequence(self):
        frames = [
            _frame(0.0, ("robot_1", 0.2, 0.0), ("robot_2", 5.0, 0.0)),
            _frame(1.0, ("robot_1", 0.2, 0.0), ("robot_2", 0.8, 0.0)),
            _frame(2.0, ("robot_1", 0.2, 0.0), ("robot_2", 0.5, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        by_id = {e.robot_id: e for e in table.entries}
        assert (by_id["robot_1"].arrival_order, by_id["robot_1"].arrival_stamp) == (1, 0.0)
        assert (by_id["robot_2"].arrival_order, by_id["robot_2"].arrival_stamp) == (2, 1.0)

    def test_arrival_uses_first_entry_when_robot_leaves_and_reenters(self):
        frames = [
            _frame(0.0, ("robot_1", 0.5, 0.0)),
            _frame(1.0, ("robot_1", 4.0, 0.0)),
            _frame(2.0, ("robot_1", 0.5, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        assert table.entries[0].arrival_stamp == 0.0

    def test_arrival_counts_robot_on_zone_boundary(self):
        frames = [_frame(0.0, ("robot_1", 1.5, 0.0))]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        assert table.entries[0].arrival_stamp == 0.0

    def test_arrival_absent_when_robot_never_in_zone(self):
        frames = [_frame(0.0, ("robot_1", 9.0, 9.0))]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        assert (table.entries[0].arrival_order, table.entries[0].arrival_stamp) == (None, None)

    def test_frames_sorted_by_stamp_when_given_out_of_order(self):
        frames = [
            _frame(2.0, ("robot_1", 0.5, 0.0)),
            _frame(0.0, ("robot_1", 5.0, 0.0)),
            _frame(1.0, ("robot_1", 1.0, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        assert table.entries[0].arrival_stamp == 1.0

    def test_arrival_order_ties_break_by_robot_id(self):
        frames = [_frame(0.0, ("robot_2", 0.5, 0.0), ("robot_1", -0.5, 0.0))]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        by_id = {e.robot_id: e.arrival_order for e in table.entries}
        assert by_id == {"robot_1": 1, "robot_2": 2}

    def test_entries_cover_latest_frame_robots_only(self):
        frames = [
            _frame(0.0, ("robot_1", 0.0, 0.0), ("robot_3", 0.0, 0.0)),
            _frame(1.0, ("robot_2", 0.0, 0.0), ("robot_1", 1.0, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.0)
        assert [e.robot_id for e in table.entries] == ["robot_1", "robot_2"]

    def test_window_sec_spans_first_to_last_stamp(self):
        frames = [_frame(3.0, ("robot_1", 0.0, 0.0)), _frame(7.5, ("robot_1", 0.0, 0.0))]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.0)
        assert table.window_sec == pytest.approx(4.5)

    def test_empty_frames_raise_value_error(self):
        with pytest.raises(ValueError):
            derive_motion_table([], conflict_center=(0.0, 0.0), conflict_radius_m=1.0)

    def test_nonpositive_radius_raises_value_error(self):
        frames = [_frame(0.0, ("robot_1", 0.0, 0.0))]
        with pytest.raises(ValueError):
            derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=0.0)
