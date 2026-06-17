"""Unit tests for the Task-10 pre-flight marker-id verifier (offline, no ROS2)."""
from __future__ import annotations

from scripts.verify_marker_ids import check_scene_ids, expected_robot_ids_from_config


def _config(*marker_ids: int) -> dict:
    return {"robots": [{"robot_id": f"robot_{m}", "marker_id": m} for m in marker_ids]}


def _scene(*robot_ids: str) -> dict:
    return {"robots": [{"robot_id": rid, "x": 0.0, "y": 0.0} for rid in robot_ids]}


def test_expected_ids_derive_from_marker_id():
    # The expected identity is what the marker is supposed to DECODE to, so it is
    # derived from marker_id (robot_<marker_id>), not the config's robot_id field.
    assert expected_robot_ids_from_config(_config(1, 2)) == {"robot_1", "robot_2"}


def test_check_passes_when_detected_equals_expected():
    check = check_scene_ids(_scene("robot_1", "robot_2"), {"robot_1", "robot_2"})
    assert check.ok
    assert check.missing == [] and check.extra == []
    assert check.matched == ["robot_1", "robot_2"]


def test_check_fails_when_a_robot_is_missing():
    # Marker rendered too small / occluded: one robot never appears.
    check = check_scene_ids(_scene("robot_1"), {"robot_1", "robot_2"})
    assert not check.ok
    assert check.missing == ["robot_2"]
    assert check.extra == []


def test_check_fails_on_mirrored_marker_decoding_to_wrong_id():
    # A mirrored UV quad decodes marker 2 as some other id -> shows as robot_7.
    # "non-empty" would pass here; id-match must NOT.
    check = check_scene_ids(_scene("robot_1", "robot_7"), {"robot_1", "robot_2"})
    assert not check.ok
    assert check.missing == ["robot_2"]
    assert check.extra == ["robot_7"]


def test_empty_expected_never_passes():
    # A config with no robots must not vacuously pass.
    check = check_scene_ids(_scene("robot_1"), set())
    assert not check.ok


def test_empty_scene_reports_all_missing():
    check = check_scene_ids(_scene(), {"robot_1", "robot_2"})
    assert not check.ok
    assert check.missing == ["robot_1", "robot_2"]
