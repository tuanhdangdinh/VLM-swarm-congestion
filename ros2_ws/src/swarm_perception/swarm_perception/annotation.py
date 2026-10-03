from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from swarm_perception.geometry import pixel_to_world, world_to_pixel
from swarm_perception.models import CalibrationArtifact, RobotState, SceneState

_STATUS_COLORS: dict[str, tuple[int, int, int]] = {
    "MOVING": (0, 200, 0),
    "SLOW": (200, 200, 0),
    "STOPPED": (200, 0, 0),
    "STALE": (128, 128, 128),
}

_ARROW_LENGTH_PX = 40
_GOAL_RADIUS_PX = 8

# Prereg-v2 rev-6 prompt apparatus overlays (2026-10-04). Both are opt-in and
# drawn UNDER the robot overlays; with neither requested,
# `render_annotated_frame` runs exactly the pre-apparatus code path, so the
# shipped frame stays byte-identical (pinned in test_annotation_apparatus.py).
#
# Every overlay pixel inside a robot's footprint disc is restored from the
# un-overlaid frame afterwards, so neither the grid nor a trail can ever cover
# a robot body or its ArUco marker in the image M2 sees. 0.20 m = the ~0.15 m
# TurtleBot3 footprint radius plus slack for M1's position error. (M1's own
# detection runs on the undistorted frame BEFORE annotation, so overlays can
# never affect tracking; this mask protects the VLM's view only.)
_OVERLAY_ROBOT_CLEAR_RADIUS_M = 0.20

# Recessive styling: thin, alpha-blended white lines and labels. White reads
# on the dark floor and stays below the saturated status colours in salience.
_GRID_RGB = (255, 255, 255)
_GRID_LINE_ALPHA = 0.40
_GRID_LINE_THICKNESS_PX = 1
_GRID_LABEL_ALPHA = 0.80
_GRID_LABEL_FONT_SCALE = 0.45
_GRID_LABEL_MARGIN_PX = 4
# An edge cell whose visible part is narrower than this fraction of the
# spacing gets no margin label (it would crowd its neighbour's label or the
# corner); the cell keeps its address, the labels around it imply it.
_GRID_LABEL_MIN_VISIBLE_FRACTION = 0.4
_SHADOW_RGB = (0, 0, 0)

# Trail fading: segments are bucketed by age so the blend runs a bounded number
# of times per frame (one per bucket), whatever the trail length.
_TRAIL_ALPHA_BUCKETS = (0.20, 0.40, 0.65, 0.90)
_TRAIL_THICKNESS_PX = 2


def status_to_color(status: str) -> tuple[int, int, int]:
    return _STATUS_COLORS.get(status, (128, 128, 128))


def draw_robot_overlay(
    image: np.ndarray,
    robot: RobotState,
    color: tuple[int, int, int],
    calibration: CalibrationArtifact,
) -> None:
    """Draw status box, ID label, velocity arrow, and goal marker on image in-place."""
    import cv2

    h, w = image.shape[:2]
    cx, cy = world_to_pixel((robot.x, robot.y), calibration.homography)

    box_half = 20
    pt1 = (max(0, cx - box_half), max(0, cy - box_half))
    pt2 = (min(w - 1, cx + box_half), min(h - 1, cy + box_half))
    cv2.rectangle(image, pt1, pt2, color, 2)

    cv2.putText(
        image,
        robot.robot_id,
        (max(0, cx - box_half), max(0, cy - box_half - 5)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        color,
        1,
        cv2.LINE_AA,
    )

    if abs(robot.linear_velocity) > 1e-3:
        ax = int(round(cx + _ARROW_LENGTH_PX * math.cos(robot.theta)))
        ay = int(round(cy - _ARROW_LENGTH_PX * math.sin(robot.theta)))  # image y flipped
        ax = max(0, min(w - 1, ax))
        ay = max(0, min(h - 1, ay))
        cv2.arrowedLine(image, (cx, cy), (ax, ay), color, 2, tipLength=0.3)

    if robot.goal is not None:
        gx, gy = world_to_pixel(robot.goal, calibration.homography)
        gx = max(0, min(w - 1, gx))
        gy = max(0, min(h - 1, gy))
        cv2.circle(image, (gx, gy), _GOAL_RADIUS_PX, color, 2)
        cv2.drawMarker(image, (gx, gy), color, cv2.MARKER_CROSS, _GOAL_RADIUS_PX * 2, 1)


class MetricGridSpec(BaseModel):
    """A world-frame metric grid aligned to the calibrated camera's visible floor.

    Columns are lettered west to east (`A` = smallest world x), rows numbered
    north to south (`1` = largest world y), so a cell label such as `C4` is a
    world-frame address independent of how the camera is mounted. The grid
    starts on a multiple of `spacing_m` and covers the whole visible floor;
    edge cells may be only partly in view.
    """

    model_config = ConfigDict(frozen=True)

    spacing_m: float = Field(gt=0)
    # West edge of column A and north edge of row 1, world metres.
    x0_m: float
    y0_m: float
    n_cols: int = Field(ge=1)
    n_rows: int = Field(ge=1)
    # Visible floor extent, world metres, as `(x_min, x_max, y_min, y_max)`.
    visible_extent_m: tuple[float, float, float, float]


def _column_letters(index: int) -> str:
    # Spreadsheet-style: A..Z, AA, AB, ...; zero-based index.
    letters = ""
    index += 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _column_index(letters: str) -> int:
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def metric_grid_spec(calibration: CalibrationArtifact, spacing_m: float) -> MetricGridSpec:
    """Lay a metric grid over the floor area the calibrated camera sees.

    Args:
        calibration: M1's calibration (pixel-to-world homography and image size).
        spacing_m: Grid line spacing in world metres.

    Returns:
        The grid layout, derived from the calibration alone (static per camera).

    Raises:
        ValueError: If `spacing_m` is not positive.
    """
    if spacing_m <= 0:
        raise ValueError(f"spacing_m must be > 0, got {spacing_m}")
    width, height = calibration.image_size
    corners = [
        pixel_to_world((u, v), calibration.homography)
        for u, v in ((0, 0), (width, 0), (0, height), (width, height))
    ]
    xs = [x for x, _ in corners]
    ys = [y for _, y in corners]
    x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
    # Rounded before floor/ceil so a calibration edge sitting on a grid line
    # (to float noise) does not grow a sliver column or row.
    x0 = math.floor(round(x_min / spacing_m, 9)) * spacing_m
    y0 = math.ceil(round(y_max / spacing_m, 9)) * spacing_m
    n_cols = max(1, math.ceil(round((x_max - x0) / spacing_m, 9)))
    n_rows = max(1, math.ceil(round((y0 - y_min) / spacing_m, 9)))
    return MetricGridSpec(
        spacing_m=spacing_m,
        x0_m=x0,
        y0_m=y0,
        n_cols=n_cols,
        n_rows=n_rows,
        visible_extent_m=(x_min, x_max, y_min, y_max),
    )


def metric_grid_cell_label(spec: MetricGridSpec, x: float, y: float) -> str | None:
    """Return the grid cell label (e.g. `C4`) containing a world point.

    Args:
        spec: The grid layout.
        x: World x in metres.
        y: World y in metres.

    Returns:
        The column-letter + row-number label, or None outside the grid.
    """
    col = math.floor((x - spec.x0_m) / spec.spacing_m)
    row = math.floor((spec.y0_m - y) / spec.spacing_m)
    if not (0 <= col < spec.n_cols and 0 <= row < spec.n_rows):
        return None
    return f"{_column_letters(col)}{row + 1}"


def metric_grid_cell_bounds(
    spec: MetricGridSpec, label: str
) -> tuple[float, float, float, float]:
    """Map a cell label back to its world-frame bounds (the verifier direction).

    Args:
        spec: The grid layout.
        label: Column letters then a 1-based row number, e.g. `C4`.

    Returns:
        `(x_min, x_max, y_min, y_max)` of the cell, world metres.

    Raises:
        ValueError: If the label is malformed or outside the grid.
    """
    letters = "".join(ch for ch in label if ch.isalpha())
    digits = label[len(letters):]
    if not letters or not letters.isupper() or not digits.isdigit():
        raise ValueError(f"malformed grid label {label!r}")
    col = _column_index(letters)
    row = int(digits) - 1
    if not (0 <= col < spec.n_cols and 0 <= row < spec.n_rows):
        raise ValueError(f"grid label {label!r} is outside the {spec.n_cols}x{spec.n_rows} grid")
    x_min = spec.x0_m + col * spec.spacing_m
    y_max = spec.y0_m - row * spec.spacing_m
    return x_min, x_min + spec.spacing_m, y_max - spec.spacing_m, y_max


class TrailHistory:
    """Per-robot ring buffer of recent world positions for the motion-trail overlay.

    The state estimator keeps no position history (it filters velocity from
    the previous pose only), so the trail owns its own small buffer. Only
    positions detected in the current frame are appended -- a STALE robot's
    carried-forward pose is not motion -- and the window is measured on the
    frame stamps (sim-time in Isaac runs), so the trail's length does not
    depend on camera fps or the simulator's real-time factor.
    """

    def __init__(
        self, window_sec: float = 3.0, min_step_sec: float = 0.1, max_points: int = 40
    ) -> None:
        """Create an empty history.

        Args:
            window_sec: Positions older than this (frame-stamp seconds) are dropped.
            min_step_sec: A new position is kept only this long after the last one.
            max_points: Hard cap per robot (ring buffer length).

        Raises:
            ValueError: If any bound is not positive.
        """
        if window_sec <= 0 or min_step_sec <= 0 or max_points < 2:
            raise ValueError(
                "window_sec and min_step_sec must be > 0 and max_points >= 2; got "
                f"{window_sec}, {min_step_sec}, {max_points}"
            )
        self.window_sec = window_sec
        self.min_step_sec = min_step_sec
        self.max_points = max_points
        self._points: dict[str, deque[tuple[float, float, float]]] = {}
        self._last_stamp: float | None = None

    def clear(self) -> None:
        """Drop every robot's history (e.g. on a clock reset)."""
        self._points.clear()
        self._last_stamp = None

    def update(self, scene_state: SceneState) -> None:
        """Fold one processed scene into the history.

        Args:
            scene_state: M1's output for the frame just processed.
        """
        if scene_state.diagnostics.get("dropped_frame"):
            return
        stamp = scene_state.stamp
        if scene_state.diagnostics.get("clock_reset") or (
            self._last_stamp is not None and stamp < self._last_stamp
        ):
            self.clear()
        self._last_stamp = stamp
        present = {robot.robot_id for robot in scene_state.robots}
        for robot_id in list(self._points):
            if robot_id not in present:
                del self._points[robot_id]
        for robot in scene_state.robots:
            points = self._points.setdefault(robot.robot_id, deque(maxlen=self.max_points))
            fresh = robot.status != "STALE" and robot.stamp == stamp
            # The epsilon keeps a step that is exactly min_step_sec in decimal
            # stamps (e.g. 1.2 - 1.0) from being rejected by float rounding.
            if fresh and (not points or stamp - points[-1][0] >= self.min_step_sec - 1e-9):
                points.append((stamp, robot.x, robot.y))
            while points and stamp - points[0][0] > self.window_sec:
                points.popleft()

    def points(self, robot_id: str) -> list[tuple[float, float, float]]:
        """Return `(stamp, x, y)` positions of one robot, oldest first."""
        return list(self._points.get(robot_id, ()))


def _footprint_mask(
    shape: tuple[int, int], robots: Sequence[RobotState], calibration: CalibrationArtifact
) -> np.ndarray:
    import cv2

    mask = np.zeros(shape, dtype=np.uint8)
    for robot in robots:
        cx, cy = world_to_pixel((robot.x, robot.y), calibration.homography)
        ex, ey = world_to_pixel(
            (robot.x + _OVERLAY_ROBOT_CLEAR_RADIUS_M, robot.y), calibration.homography
        )
        radius = max(1, int(math.ceil(math.hypot(ex - cx, ey - cy))))
        cv2.circle(mask, (cx, cy), radius, 255, -1)
    return mask


def _blend(
    image: np.ndarray, color: tuple[int, int, int], coverage: np.ndarray, alpha: float
) -> None:
    # In-place blend of a flat colour into `image`, weighted per pixel by
    # `alpha` times the anti-aliased coverage mask (0..255).
    sel = coverage > 0
    if not sel.any():
        return
    weight = (coverage[sel].astype(np.float32) / 255.0 * alpha)[:, None]
    mixed = image[sel].astype(np.float32) * (1.0 - weight) + np.asarray(
        color, dtype=np.float32
    ) * weight
    image[sel] = np.clip(np.rint(mixed), 0, 255).astype(np.uint8)


def draw_metric_grid(
    image: np.ndarray, spec: MetricGridSpec, calibration: CalibrationArtifact
) -> None:
    """Draw the labeled metric grid in-place: thin blended lines plus margin labels.

    Column letters run along the top margin and row numbers along the left
    margin, each at the centre of its cell's visible part, so no label sits on
    the floor where robots drive.

    Args:
        image: RGB frame `(H, W, 3)` at the calibrated resolution.
        spec: The grid layout (`metric_grid_spec`).
        calibration: M1's calibration, for the world-to-pixel projection.
    """
    import cv2

    height, width = image.shape[:2]
    rect = (0, 0, width, height)
    homography = calibration.homography
    line_mask = np.zeros((height, width), dtype=np.uint8)
    y_top = spec.y0_m
    y_bottom = spec.y0_m - spec.n_rows * spec.spacing_m
    x_left = spec.x0_m
    x_right = spec.x0_m + spec.n_cols * spec.spacing_m
    segments = [
        ((x_left + k * spec.spacing_m, y_top), (x_left + k * spec.spacing_m, y_bottom))
        for k in range(spec.n_cols + 1)
    ] + [
        ((x_left, y_top - k * spec.spacing_m), (x_right, y_top - k * spec.spacing_m))
        for k in range(spec.n_rows + 1)
    ]
    for start, end in segments:
        inside, p1, p2 = cv2.clipLine(
            rect, world_to_pixel(start, homography), world_to_pixel(end, homography)
        )
        if inside:
            cv2.line(line_mask, p1, p2, 255, _GRID_LINE_THICKNESS_PX, cv2.LINE_AA)
    _blend(image, _GRID_RGB, line_mask, _GRID_LINE_ALPHA)

    x_min, x_max, y_min, y_max = spec.visible_extent_m
    font = cv2.FONT_HERSHEY_SIMPLEX
    shadow_mask = np.zeros((height, width), dtype=np.uint8)
    text_mask = np.zeros((height, width), dtype=np.uint8)
    labels: list[tuple[str, tuple[float, float], str]] = []
    for col in range(spec.n_cols):
        lo = max(spec.x0_m + col * spec.spacing_m, x_min)
        hi = min(spec.x0_m + (col + 1) * spec.spacing_m, x_max)
        if hi - lo >= _GRID_LABEL_MIN_VISIBLE_FRACTION * spec.spacing_m:
            labels.append((_column_letters(col), ((lo + hi) / 2.0, y_max), "top"))
    for row in range(spec.n_rows):
        hi = min(spec.y0_m - row * spec.spacing_m, y_max)
        lo = max(spec.y0_m - (row + 1) * spec.spacing_m, y_min)
        if hi - lo >= _GRID_LABEL_MIN_VISIBLE_FRACTION * spec.spacing_m:
            labels.append((str(row + 1), (x_min, (lo + hi) / 2.0), "left"))
    for text, world_point, edge in labels:
        (text_w, text_h), _ = cv2.getTextSize(text, font, _GRID_LABEL_FONT_SCALE, 1)
        u, v = world_to_pixel(world_point, homography)
        if edge == "top":
            origin = (u - text_w // 2, _GRID_LABEL_MARGIN_PX + text_h)
        else:
            origin = (_GRID_LABEL_MARGIN_PX, v + text_h // 2)
        # Skip a label that would not fit inside the frame (a sliver edge cell).
        if origin[0] < 0 or origin[0] + text_w > width or origin[1] > height:
            continue
        cv2.putText(shadow_mask, text, (origin[0] + 1, origin[1] + 1), font,
                    _GRID_LABEL_FONT_SCALE, 255, 2, cv2.LINE_AA)
        cv2.putText(text_mask, text, origin, font, _GRID_LABEL_FONT_SCALE, 255, 1, cv2.LINE_AA)
    _blend(image, _SHADOW_RGB, shadow_mask, _GRID_LABEL_ALPHA)
    _blend(image, _GRID_RGB, text_mask, _GRID_LABEL_ALPHA)


def draw_motion_trails(
    image: np.ndarray,
    history: TrailHistory,
    robots: Sequence[RobotState],
    calibration: CalibrationArtifact,
) -> None:
    """Draw each robot's recent positions as a fading polyline in its status colour.

    Older segments are fainter; the newest segment ends at the robot's last
    detected position.

    Args:
        image: RGB frame `(H, W, 3)`, drawn on in-place.
        history: The trail buffer, already updated with this frame.
        robots: Robots of this frame (colour comes from each one's status).
        calibration: M1's calibration, for the world-to-pixel projection.
    """
    import cv2

    height, width = image.shape[:2]
    buckets = len(_TRAIL_ALPHA_BUCKETS)
    for robot in robots:
        pixels = [
            world_to_pixel((x, y), calibration.homography)
            for _, x, y in history.points(robot.robot_id)
        ]
        segments = [(a, b) for a, b in zip(pixels, pixels[1:], strict=False) if a != b]
        if not segments:
            continue
        masks = [np.zeros((height, width), dtype=np.uint8) for _ in range(buckets)]
        for index, (a, b) in enumerate(segments):
            bucket = min(buckets - 1, (index * buckets) // len(segments))
            cv2.line(masks[bucket], a, b, 255, _TRAIL_THICKNESS_PX, cv2.LINE_AA)
        color = status_to_color(robot.status)
        for mask, alpha in zip(masks, _TRAIL_ALPHA_BUCKETS, strict=True):
            _blend(image, color, mask, alpha)


def render_annotated_frame(
    image: np.ndarray,
    scene_state: SceneState,
    calibration: CalibrationArtifact,
    style: Mapping[str, object] | None = None,
    *,
    metric_grid: MetricGridSpec | None = None,
    motion_trails: TrailHistory | None = None,
) -> np.ndarray:
    """Draw M1's annotation on a copy of an RGB frame.

    Args:
        image: RGB frame `(H, W, 3)`.
        scene_state: Robots to annotate.
        calibration: M1's calibration.
        style: Reserved; unused.
        metric_grid: Draw this labeled metric grid under the robot overlays
            (prompt-apparatus A/B condition); None draws none.
        motion_trails: Draw the robots' recent positions from this (already
            updated) history as fading trails; None draws none.

    Returns:
        The annotated RGB copy; `image` is untouched.
    """
    annotated = image.copy()
    if metric_grid is not None or motion_trails is not None:
        clean = annotated.copy()
        if metric_grid is not None:
            draw_metric_grid(annotated, metric_grid, calibration)
        if motion_trails is not None:
            draw_motion_trails(annotated, motion_trails, scene_state.robots, calibration)
        keep = _footprint_mask(annotated.shape[:2], scene_state.robots, calibration).astype(bool)
        annotated[keep] = clean[keep]
    for robot in scene_state.robots:
        color = status_to_color(robot.status)
        draw_robot_overlay(annotated, robot, color, calibration)
    return annotated
