"""Offline checks on the global camera graph wiring in isaac/vgu_sim/ros_graphs.py.

Isaac's `pxr` / `omni.*` modules are not installed off-VM, so they are stubbed in
`sys.modules` and `og.Controller.edit` is recorded instead of executed.
"""
from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def recorded_edits(monkeypatch) -> list[tuple[dict, dict]]:
    edits: list[tuple[dict, dict]] = []

    og = MagicMock()
    og.Controller.edit.side_effect = lambda graph, spec: edits.append((graph, spec))
    rep = MagicMock()
    rep.create.render_product.return_value.path = "/Render/RP"

    omni = types.ModuleType("omni")
    omni_graph = types.ModuleType("omni.graph")
    omni_replicator = types.ModuleType("omni.replicator")
    omni.graph = omni_graph
    omni.replicator = omni_replicator
    omni_graph.core = og
    omni_replicator.core = rep
    for name, module in {
        "pxr": MagicMock(),
        "omni": omni,
        "omni.graph": omni_graph,
        "omni.graph.core": og,
        "omni.replicator": omni_replicator,
        "omni.replicator.core": rep,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    for name in ("isaac.vgu_sim.ros_graphs", "isaac.vgu_sim.lidar"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    ros_graphs = importlib.import_module("isaac.vgu_sim.ros_graphs")
    from isaac.vgu_sim.config import CameraConfig

    ros_graphs.create_global_ros_graphs(MagicMock(), "/World/Camera", CameraConfig())
    yield edits
    for name in ("isaac.vgu_sim.ros_graphs", "isaac.vgu_sim.lidar"):
        sys.modules.pop(name, None)


def _set_values(edits: list[tuple[dict, dict]], graph_suffix: str) -> dict[str, object]:
    for graph, spec in edits:
        if graph["graph_path"].endswith(graph_suffix):
            return dict(spec[sys.modules["omni.graph.core"].Controller.Keys.SET_VALUES])
    raise AssertionError(f"no graph ending in {graph_suffix}")


def test_camera_image_stamped_with_sim_time(recorded_edits):
    values = _set_values(recorded_edits, "camera_rgb_graph")
    assert values["pub_rgb.inputs:useSystemTime"] is False


def test_camera_info_stamped_with_sim_time(recorded_edits):
    values = _set_values(recorded_edits, "camera_info_graph")
    assert values["pub_cam_info.inputs:useSystemTime"] is False
