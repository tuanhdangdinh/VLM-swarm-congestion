"""Fixed 3x3 pixel-space grid partition and overlay drawing."""
import numpy as np

from reasoning.vlm.capability_probes.grid import (
    GRID_CELL_COUNT,
    cell_bounds_px,
    cell_center_px,
    cell_index_for_pixel,
    draw_grid_overlay,
)


class TestCellBounds:
    def test_nine_cells_tile_the_image_exactly(self):
        bounds = cell_bounds_px(1280, 960)
        assert len(bounds) == GRID_CELL_COUNT
        assert bounds[0][:2] == (0, 0)
        assert bounds[-1][2:] == (1280, 960)

    def test_row_major_order_top_left_to_bottom_right(self):
        bounds = cell_bounds_px(1280, 960)
        # Cell 0 (top-left) and cell 2 (top-right) share the top row.
        assert bounds[0][1] == bounds[2][1] == 0
        # Cell 6 (bottom-left) and cell 8 (bottom-right) share the bottom row.
        assert bounds[6][3] == bounds[8][3] == 960


class TestCellIndexForPixel:
    def test_image_centre_is_the_centre_cell(self):
        assert cell_index_for_pixel(640, 480, 1280, 960) == 4

    def test_top_left_area_is_cell_zero(self):
        # Not the literal corner pixel: must clear the boundary margin on
        # both axes (see test_point_on_a_cell_boundary_is_none).
        assert cell_index_for_pixel(50, 50, 1280, 960) == 0

    def test_bottom_right_area_is_the_last_cell(self):
        assert cell_index_for_pixel(1200, 900, 1280, 960) == GRID_CELL_COUNT - 1

    def test_off_frame_point_is_none(self):
        assert cell_index_for_pixel(-5, 100, 1280, 960) is None
        assert cell_index_for_pixel(1280, 100, 1280, 960) is None

    def test_point_on_a_cell_boundary_is_none(self):
        # x=426/427 is the first column boundary for width 1280 (1280/3).
        boundary_u = round(1280 / 3)
        assert cell_index_for_pixel(boundary_u, 480, 1280, 960) is None

    def test_point_well_inside_a_cell_is_not_none(self):
        assert cell_index_for_pixel(100, 100, 1280, 960) == 0


class TestCellCenterRoundTrip:
    def test_cell_center_resolves_back_to_its_own_cell(self):
        for index in range(GRID_CELL_COUNT):
            u, v = cell_center_px(index, 1280, 960)
            assert cell_index_for_pixel(u, v, 1280, 960) == index


class TestDrawGridOverlay:
    def test_returns_a_new_array_same_shape(self):
        image = np.full((960, 1280, 3), 128, dtype=np.uint8)
        drawn = draw_grid_overlay(image, {"A": "4"})
        assert drawn.shape == image.shape
        assert not np.array_equal(drawn, image)

    def test_does_not_mutate_the_input(self):
        image = np.full((960, 1280, 3), 128, dtype=np.uint8)
        original = image.copy()
        draw_grid_overlay(image, {"A": "0", "B": "8"})
        assert np.array_equal(image, original)
