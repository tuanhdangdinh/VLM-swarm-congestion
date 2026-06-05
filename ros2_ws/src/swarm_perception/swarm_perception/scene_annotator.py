"""Backward-compat shim; use swarm_perception.annotation instead."""
from swarm_perception.annotation import render_annotated_frame, status_to_color

__all__ = ["render_annotated_frame", "status_to_color"]
