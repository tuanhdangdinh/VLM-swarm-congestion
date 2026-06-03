from dataclasses import dataclass


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


def pixel_to_world(point: Point2D) -> Point2D:
    """Placeholder homography transform."""
    return point
