"""Backward-compat shim; use swarm_perception.geometry instead."""
from swarm_perception.geometry import pixel_to_world, pixels_to_world, world_to_pixel

__all__ = ["pixel_to_world", "pixels_to_world", "world_to_pixel"]
