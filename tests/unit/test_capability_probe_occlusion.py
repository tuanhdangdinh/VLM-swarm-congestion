"""M1-annotation-vs-grid-badge collision checks (2026-10-02 occlusion fix).

A grid badge drawn at a cell's centre must not land on the box or ID label
M1's own annotation pass would draw for the robot being asked about;
otherwise the item is unanswerable from the image. `robot_annotation_rects`
mirrors `swarm_perception.annotation.draw_robot_overlay`'s exact geometry, so
these tests also guard against that geometry silently drifting apart.
"""
from reasoning.vlm.capability_probes.grid import badge_radius_px, cell_center_px
from reasoning.vlm.capability_probes.occlusion import (
    robot_annotation_rects,
    robot_overlaps_any_grid_badge,
)

_WIDTH, _HEIGHT = 1280, 960


class TestRobotAnnotationRects:
    def test_box_rect_is_40px_square_centred_on_the_robot(self):
        box, _label = robot_annotation_rects("robot_1", 500, 500)
        x0, y0, x1, y1 = box
        assert (x1 - x0, y1 - y0) == (40, 40)
        assert (x0 + x1) / 2 == 500
        assert (y0 + y1) / 2 == 500

    def test_label_rect_sits_above_the_box(self):
        box, label = robot_annotation_rects("robot_1", 500, 500)
        assert label[3] <= box[1]  # label's bottom is at or above the box's top

    def test_longer_ids_get_a_wider_label_rect(self):
        _box, short_label = robot_annotation_rects("r1", 500, 500)
        _box, long_label = robot_annotation_rects("robot_12345", 500, 500)
        short_width = short_label[2] - short_label[0]
        long_width = long_label[2] - long_label[0]
        assert long_width > short_width


class TestRobotOverlapsAnyGridBadge:
    def test_robot_far_from_every_cell_centre_does_not_overlap(self):
        # Well inside a cell, away from its own centre and every other.
        assert not robot_overlaps_any_grid_badge("robot_1", 150, 150, _WIDTH, _HEIGHT)

    def test_robot_exactly_at_a_cell_centre_overlaps(self):
        cx, cy = cell_center_px(4, _WIDTH, _HEIGHT)
        assert robot_overlaps_any_grid_badge("robot_1", cx, cy, _WIDTH, _HEIGHT)

    def test_robot_just_outside_the_badge_radius_does_not_overlap(self):
        cx, cy = cell_center_px(4, _WIDTH, _HEIGHT)
        radius = badge_radius_px(_WIDTH)
        # The robot's box itself spans +/-20px; clear the badge by a healthy
        # margin so this is not testing a knife-edge case.
        far_u = cx + radius + 60
        assert not robot_overlaps_any_grid_badge("robot_1", far_u, cy, _WIDTH, _HEIGHT)

    def test_overlap_checked_against_every_cell_not_only_the_nearest(self):
        # A robot sitting near cell 0's centre also must not collide with any
        # of the other 8 badges -- trivially true here, but exercises the
        # full 9-cell loop rather than a single hardcoded comparison.
        cx, cy = cell_center_px(0, _WIDTH, _HEIGHT)
        assert robot_overlaps_any_grid_badge("robot_1", cx, cy, _WIDTH, _HEIGHT)
