"""Tests for the B2-visual load prop's mounting geometry (pure Python).

`load_prop_asset`'s constants and `marker_clearance_m`/`lidar_plane_clearance_m`
need no simulator; `author_load_prop` itself is pxr-only and is pinned
separately in `tests/unit/test_load_prop_asset_pxr.py` (skipped without
`pxr`, the project's existing convention for `isaac.vgu_sim` authoring
helpers, e.g. `tests/unit/test_m6_validation.py`).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.vgu_sim.load_prop_asset import (
    BASE_LINK_COLLISION_REAR_X_M,
    LOAD_PROP_CENTER_X_M,
    LOAD_PROP_SIZE_M,
    MARKER_REAR_X_M,
    lidar_plane_clearance_m,
    load_prop_front_edge_x_m,
    marker_clearance_m,
)


def test_shipped_mount_clears_the_marker():
    assert marker_clearance_m() > 0.0


def test_shipped_mount_clears_the_lidar_scan_plane():
    assert lidar_plane_clearance_m() > 0.0


def test_mount_is_flush_to_the_chassis_rear_with_no_floating_gap():
    assert load_prop_front_edge_x_m() == BASE_LINK_COLLISION_REAR_X_M


def test_marker_clearance_is_the_gap_behind_the_marker_within_the_chassis():
    # The free space already behind the marker's own rear edge, inside the
    # chassis footprint, before the prop adds anything new.
    expected = MARKER_REAR_X_M - BASE_LINK_COLLISION_REAR_X_M
    assert marker_clearance_m() == expected
    assert expected > 0.0


def test_a_mount_ahead_of_the_chassis_rear_would_clear_less():
    # Moving the mount 0.05 m forward (toward the marker) shrinks the gap by
    # exactly 0.05 m -- the clearance check is sensitive to the mount, not a
    # hardcoded pass.
    forward_mount = LOAD_PROP_CENTER_X_M + 0.05
    assert marker_clearance_m(forward_mount) == marker_clearance_m() - 0.05


def test_a_mount_overlapping_the_marker_reads_negative_clearance():
    assert marker_clearance_m(center_x_m=0.0) < 0.0


def test_prop_footprint_is_pallet_sized_not_marker_sized():
    # Comparable to the marker's own 0.12 m so it reads clearly, not
    # oversized into the neighbouring aisle geometry.
    x_m, y_m, z_m = LOAD_PROP_SIZE_M
    assert 0.08 <= x_m <= 0.20
    assert 0.08 <= y_m <= 0.20
    assert z_m < x_m  # low-profile, not a tall occluder
