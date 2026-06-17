"""Every generated marker PNG must decode to its own id under M1's configured dict."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import pytest

from isaac.vgu_sim.paths import aruco_dict_name, marker_png_path

# M1 perception is a ROS2 package; add its src to the path to import detection.
_PERCEPTION_SRC = Path("ros2_ws/src/swarm_perception")
if str(_PERCEPTION_SRC) not in sys.path:
    sys.path.insert(0, str(_PERCEPTION_SRC))

from swarm_perception.detection import detect_aruco_markers  # noqa: E402


@pytest.mark.parametrize("marker_id", range(1, 50))
def test_generated_marker_decodes_to_its_id(marker_id: int):
    name = aruco_dict_name()
    png = marker_png_path(name, marker_id)
    img = cv2.imread(str(png), cv2.IMREAD_GRAYSCALE)
    assert img is not None, f"missing {png} (run scripts.generate_aruco_markers)"
    ids, _ = detect_aruco_markers(img, dictionary_name=name)
    assert ids == [marker_id]
