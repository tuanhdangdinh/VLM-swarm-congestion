from pathlib import Path

import cv2
import pytest

from isaac.vgu_sim import paths
from scripts.generate_aruco_markers import generate_markers


def test_marker_dict_slug_strips_prefix_and_lowercases():
    assert paths.marker_dict_slug("DICT_4X4_50") == "aruco_4x4_50"


def test_marker_png_path_uses_slug_and_id():
    p = paths.marker_png_path("DICT_4X4_50", 7)
    assert p == Path("isaac/assets/markers/aruco_4x4_50/marker_7.png")


def test_aruco_dict_name_reads_single_source_of_truth():
    # The configured dictionary is read from M1's aruco.yaml — one source for
    # generation AND scene authoring, so the two cannot desync.
    assert paths.aruco_dict_name() == "DICT_4X4_50"


def test_generate_writes_all_ids_and_is_deterministic(tmp_path):
    generate_markers("DICT_4X4_50", tmp_path, ids=range(1, 50))
    files = sorted(
        (p.name for p in tmp_path.glob("*.png")),
        key=lambda f: int(f.replace("marker_", "").replace(".png", ""))
    )
    assert files == [f"marker_{i}.png" for i in range(1, 50)]

    first = (tmp_path / "marker_1.png").read_bytes()
    generate_markers("DICT_4X4_50", tmp_path, ids=[1])  # regenerate
    assert (tmp_path / "marker_1.png").read_bytes() == first  # deterministic


def test_generated_marker_is_square(tmp_path):
    generate_markers("DICT_4X4_50", tmp_path, ids=[3])
    img = cv2.imread(str(tmp_path / "marker_3.png"), cv2.IMREAD_GRAYSCALE)
    assert img.shape[0] == img.shape[1]


def test_unsupported_dictionary_raises(tmp_path):
    with pytest.raises(ValueError, match="NOT_A_DICT"):
        generate_markers("NOT_A_DICT", tmp_path, ids=[1])
