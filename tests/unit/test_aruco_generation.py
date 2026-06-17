from pathlib import Path

from isaac.vgu_sim import paths


def test_marker_dict_slug_strips_prefix_and_lowercases():
    assert paths.marker_dict_slug("DICT_4X4_50") == "aruco_4x4_50"


def test_marker_png_path_uses_slug_and_id():
    p = paths.marker_png_path("DICT_4X4_50", 7)
    assert p == Path("isaac/assets/markers/aruco_4x4_50/marker_7.png")


def test_aruco_dict_name_reads_single_source_of_truth():
    # The configured dictionary is read from M1's aruco.yaml — one source for
    # generation AND scene authoring, so the two cannot desync.
    assert paths.aruco_dict_name() == "DICT_4X4_50"
