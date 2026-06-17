"""Acceptance checks for the TurtleBot asset prerequisites (Task 6).

The URDF must be importable by Isaac: fully xacro-expanded, referencing only
vendored local meshes, with the ArUco marker frame raised above the lidar and the
placeholder box visual removed (the detectable marker is an authored USD quad).

The four STL meshes must be vendored from `turtlebot3_description` under
`meshes/`. Until they are present, the mesh-existence check is skipped (it
self-activates once the files are added); the on-Isaac import (plan Task 10) is
the ultimate gate.
"""
from pathlib import Path

import pytest

URDF = Path("isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf")
MESH_DIR = Path("isaac/assets/robots/turtlebot3_burger/meshes")
MESHES = ["burger_base.stl", "left_tire.stl", "right_tire.stl", "lds.stl"]
_MESHES_PRESENT = all((MESH_DIR / m).exists() for m in MESHES)


def test_urdf_has_no_xacro_or_namespace_tokens():
    text = URDF.read_text()
    assert "${" not in text
    assert "xacro" not in text


def test_urdf_references_only_local_meshes():
    text = URDF.read_text()
    assert "package://" not in text


@pytest.mark.skipif(
    not _MESHES_PRESENT,
    reason="vendor turtlebot3_description STLs under meshes/ (Task 6 manual step)",
)
@pytest.mark.parametrize("name", MESHES)
def test_vendored_mesh_exists_and_nonempty(name: str):
    p = MESH_DIR / name
    assert p.exists() and p.stat().st_size > 0


def test_marker_joint_raised_above_lidar():
    text = URDF.read_text()
    # aruco_marker_joint origin z must clear the lidar (base_scan at z=0.172).
    assert 'name="aruco_marker_joint"' in text
    assert 'xyz="0 0 0.21"' in text


def test_marker_link_has_no_box_visual():
    # The marker is now an authored USD quad; the URDF link is a frame only.
    text = URDF.read_text()
    marker_block = text.split('name="aruco_marker_link"', 1)[1]
    assert "<box" not in marker_block.split("</link>", 1)[0]
