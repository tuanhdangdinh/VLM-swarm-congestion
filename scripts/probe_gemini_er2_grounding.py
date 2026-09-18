#!/usr/bin/env python3
"""Image-grounding probe for Gemini Robotics-ER 2 (M2 `gemini` backend).

Answers the open item carried by
`docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`:
does ER-2 ground its congestion decisions in the overhead camera frame, or
does it only do arithmetic on the text robot-state block?

Three experiments, all against `gemini-robotics-er-2-preview` on the
Interactions API through the project's own `GeminiBackend` transport:

1. Native pointing: ask for `[{"point": [y, x], "label": ...}]` (normalized
   0-1000, `[y, x]` order) on each stimulus and score the returned points
   against the ArUco/M1 ground-truth robot centres. Tests perception only.
2. The discriminating 2x2: the project's real M2 prompt
   (`reasoning.vlm.prompt_builder`) with the image and the text robot states
   varied independently (congruent-conflict, congruent-clear, and the two
   incongruent cells). Tests whether the image moves the decision.
3. Experiment 2's two incongruent cells re-run with
   `ReasonerRequest.include_pairwise_geometry=False`, which withholds the
   derived distance/facing lines (raw coordinates and the image remain).

Every call is appended to a JSONL artifact under `data/logs/` (git-ignored)
carrying the request condition, the response, and token usage -- never the
API key and never base64 image data. The key is read only from the
environment (`GEMINI_API_KEY`, per `config/models.yaml`'s `vlm.gemini`
section) and is never accepted as a CLI argument.

Usage:
    python scripts/probe_gemini_er2_grounding.py --dry-run
    python scripts/probe_gemini_er2_grounding.py --experiment 1 --repeats 3 \
        --frame-conflict <path> --frame-clear <path>
    python scripts/probe_gemini_er2_grounding.py --experiment all --repeats 3 \
        --frame-conflict <path> --frame-clear <path> \
        --conflict-stamp 1789721320.33 --clear-stamp 1789721707.53 \
        --scene-log data/logs/m5_scene/<session>.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (REPO_ROOT, REPO_ROOT / "ros2_ws" / "src" / "swarm_perception"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
from pydantic import BaseModel, ConfigDict  # noqa: E402
from swarm_perception.calibration import load_calibration  # noqa: E402
from swarm_perception.detection import (  # noqa: E402
    build_marker_detections,
    detect_aruco_markers,
)
from swarm_perception.geometry import pixel_to_world, world_to_pixel  # noqa: E402

from reasoning.vlm.errors import BackendTimeoutError  # noqa: E402
from reasoning.vlm.gemini_backend import GeminiBackend  # noqa: E402
from reasoning.vlm.models import (  # noqa: E402
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.prompt_builder import SYSTEM_PROMPT  # noqa: E402
from reasoning.vlm.reasoner import Reasoner  # noqa: E402

DEFAULT_MODEL = "gemini-robotics-er-2-preview"
DEFAULT_CALIBRATION = "ros2_ws/src/swarm_perception/config/calibration.yaml"
DEFAULT_MARKER_DICTIONARY = "DICT_4X4_50"
DEFAULT_LOG_DIR = "data/logs/er2_grounding"

# A TurtleBot3 is ~0.3 m across, so half a robot width is a point that clearly
# landed on the robot and one full width still identifies the right robot.
ROBOT_WIDTH_M = 0.3
CLEAR_HIT_M = ROBOT_WIDTH_M / 2.0
RIGHT_ROBOT_M = ROBOT_WIDTH_M

# ER-2's documented pointing format: normalized 0-1000 in [y, x] order (design
# doc "Option B"). The project's own convention is pixel (u, v) and world
# (x, y) metres, so the axis swap is done explicitly in denormalize_point.
POINTING_PROMPT = (
    "This is an overhead camera view of a warehouse aisle with two mobile "
    "robots in it. Point to each robot you can see.\n"
    "Answer with ONLY a JSON list of items of the form "
    '{"point": [y, x], "label": "<short label>"}, where y and x are the point '
    "coordinates normalized to the range 0-1000 in [y, x] order. Emit exactly "
    "one item per robot. No markdown, no explanation."
)

# The two text robot-state conditions of the 2x2. Only distance/heading/status
# differ; no goals or tasks are sent in either, so nothing but the geometry can
# explain a difference between cells.
_CONFLICT_STATES = (
    {"robot_id": "robot_1", "x": -0.175, "y": 0.0, "theta": 0.0, "status": "STOPPED",
     "linear_velocity": 0.0, "angular_velocity": 0.0},
    {"robot_id": "robot_2", "x": 0.175, "y": 0.0, "theta": math.pi, "status": "STOPPED",
     "linear_velocity": 0.0, "angular_velocity": 0.0},
)
_CLEAR_STATES = (
    {"robot_id": "robot_1", "x": -1.25, "y": 0.0, "theta": math.pi, "status": "MOVING",
     "linear_velocity": 0.15, "angular_velocity": 0.0},
    {"robot_id": "robot_2", "x": 1.25, "y": 0.0, "theta": 0.0, "status": "MOVING",
     "linear_velocity": 0.15, "angular_velocity": 0.0},
)

CONFLICT_FRAME = "FRAME_CONFLICT"
CLEAR_FRAME = "FRAME_CLEAR"

# Cell order matters: A and D are the congruent gate cells. If A does not
# answer "conflict" and D does not answer "clear", the incongruent cells B and
# C are uninterpretable, so they are run last and read only after the gate.
CELLS: tuple[tuple[str, str, str], ...] = (
    ("A", CONFLICT_FRAME, "conflict"),
    ("D", CLEAR_FRAME, "clear"),
    ("B", CONFLICT_FRAME, "clear"),
    ("C", CLEAR_FRAME, "conflict"),
)

TextCondition = Literal["conflict", "clear"]


class RobotGroundTruth(BaseModel):
    """One robot's measured position in a stimulus frame."""

    model_config = ConfigDict(frozen=True)

    robot_id: str
    source: Literal["aruco", "scene_log"]
    center_pixel: tuple[float, float]
    center_world: tuple[float, float]
    theta: float | None = None


class StimulusMeasurement(BaseModel):
    """Objective measurement of one stimulus frame."""

    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    sha256: str
    image_size: tuple[int, int]
    aruco_marker_ids: list[int]
    robots: list[RobotGroundTruth]
    separation_m: float | None
    burned_in_stamp: float | None = None
    scene_log_stamp: float | None = None
    scene_log_delta_sec: float | None = None


class PointItem(BaseModel):
    """One `[{"point": [y, x], "label": ...}]` item returned by ER-2."""

    model_config = ConfigDict(frozen=True)

    label: str
    point_yx: tuple[float, float]


class PointScore(BaseModel):
    """Error of one returned point against one ground-truth robot centre."""

    model_config = ConfigDict(frozen=True)

    robot_id: str
    returned_label: str
    point_yx: tuple[float, float]
    point_pixel: tuple[float, float]
    truth_pixel: tuple[float, float]
    error_px: float
    error_m: float
    verdict: Literal["clear_hit", "right_robot", "miss"]


class PointScoring(BaseModel):
    """Forced one-to-one scoring of the returned points against the truths."""

    model_config = ConfigDict(frozen=True)

    scores: list[PointScore]
    total_error_m: float
    swapped_total_error_m: float | None
    returned_separation_m: float | None
    truth_separation_m: float | None


def sha256_file(path: Path) -> str:
    """Hash a file so a logged stimulus can be identified without embedding it.

    Args:
        path: File to hash.

    Returns:
        Lowercase hex SHA-256 digest.
    """
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def redact_secret(text: str, secret: str | None) -> str:
    """Replace every occurrence of `secret` in `text` with a redaction marker.

    Args:
        text: Text that may contain the secret (e.g. an HTTP error body).
        secret: The literal secret value to scrub, or `None`/empty to skip.

    Returns:
        `text` with every occurrence of `secret` replaced by `***REDACTED***`.
    """
    if not secret:
        return text
    return text.replace(secret, "***REDACTED***")


def mean_scale_m_per_px(homography: np.ndarray) -> float:
    """Return the ground-plane scale of a pixel-to-world homography.

    Args:
        homography: Pixel-to-world matrix (M1 `CalibrationArtifact.homography`).

    Returns:
        Metres per pixel, averaged over the x and y image axes at the image
        origin, so callers can convert a pixel tolerance into metres.
    """
    origin = np.array(pixel_to_world((0.0, 0.0), homography))
    step_u = np.array(pixel_to_world((1.0, 0.0), homography))
    step_v = np.array(pixel_to_world((0.0, 1.0), homography))
    return float((np.linalg.norm(step_u - origin) + np.linalg.norm(step_v - origin)) / 2.0)


def denormalize_point(
    point_yx: tuple[float, float], image_size: tuple[int, int]
) -> tuple[float, float]:
    """Convert an ER-2 `[y, x]` 0-1000 point into project pixel `(u, v)`.

    Args:
        point_yx: Point as returned by ER-2: `[y, x]`, each normalized 0-1000.
        image_size: Image size as `(width, height)` in pixels.

    Returns:
        Pixel coordinate as `(u, v)` — note the axis swap: ER-2 returns row
        first, this project's convention is column first.
    """
    width, height = image_size
    y_norm, x_norm = point_yx
    return (x_norm / 1000.0 * float(width), y_norm / 1000.0 * float(height))


def parse_point_items(text: str) -> list[PointItem]:
    """Extract `[{"point": [y, x], "label": ...}]` items from a model response.

    Tolerates markdown fences and leading/trailing prose by taking the first
    balanced JSON array in the text, mirroring `output_parser`'s tolerance for
    the decision JSON. Items without a two-element `point` are skipped.

    Args:
        text: Raw response text.

    Returns:
        The parsed point items, in response order; empty when nothing parses.
    """
    start = text.find("[")
    if start < 0:
        return []
    depth = 0
    end = -1
    for index in range(start, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end < 0:
        return []
    try:
        payload = json.loads(text[start:end])
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    items: list[PointItem] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        point = entry.get("point")
        if not isinstance(point, list) or len(point) != 2:
            continue
        try:
            coords = (float(point[0]), float(point[1]))
        except (TypeError, ValueError):
            continue
        items.append(PointItem(label=str(entry.get("label", "")), point_yx=coords))
    return items


def world_distance_m(
    pixel_a: tuple[float, float], pixel_b: tuple[float, float], homography: np.ndarray
) -> float:
    """Return the ground-plane distance in metres between two pixel points.

    Args:
        pixel_a: First pixel coordinate as `(u, v)`.
        pixel_b: Second pixel coordinate as `(u, v)`.
        homography: Pixel-to-world homography.

    Returns:
        Distance in metres after mapping both pixels through the homography.
    """
    world_a = pixel_to_world(pixel_a, homography)
    world_b = pixel_to_world(pixel_b, homography)
    return math.hypot(world_a[0] - world_b[0], world_a[1] - world_b[1])


def classify_point_error(error_m: float) -> Literal["clear_hit", "right_robot", "miss"]:
    """Grade one point error against the pre-stated robot-width criteria.

    Args:
        error_m: Distance in metres from the point to the true robot centre.

    Returns:
        `"clear_hit"` within half a robot width, `"right_robot"` within one
        robot width, `"miss"` beyond that.
    """
    if error_m <= CLEAR_HIT_M:
        return "clear_hit"
    if error_m <= RIGHT_ROBOT_M:
        return "right_robot"
    return "miss"


def score_points(
    items: list[PointItem],
    truths: list[RobotGroundTruth],
    image_size: tuple[int, int],
    homography: np.ndarray,
) -> PointScoring:
    """Score returned points against the ground truth with a forced assignment.

    Points are assigned one-to-one to robots by minimising total metric error,
    never by nearest-neighbour: two points collapsed onto the same blob must
    not both count as hits. The assignment's total error is reported next to
    the best alternative (swapped) assignment, and the returned points' own
    separation next to the true separation, so a "both points on one robot"
    response is visible in the artifact rather than hidden by a low error.

    Args:
        items: Points parsed from the response.
        truths: Ground-truth robot centres for this stimulus.
        image_size: Image size as `(width, height)`.
        homography: Pixel-to-world homography.

    Returns:
        The scoring for the best assignment, with the runner-up total.
    """
    pixels = [denormalize_point(item.point_yx, image_size) for item in items]
    truth_separation = (
        world_distance_m(truths[0].center_pixel, truths[1].center_pixel, homography)
        if len(truths) == 2
        else None
    )
    returned_separation = (
        world_distance_m(pixels[0], pixels[1], homography) if len(pixels) == 2 else None
    )
    if not items or not truths:
        return PointScoring(
            scores=[],
            total_error_m=float("inf"),
            swapped_total_error_m=None,
            returned_separation_m=returned_separation,
            truth_separation_m=truth_separation,
        )

    size = min(len(items), len(truths))
    best: tuple[float, list[PointScore]] | None = None
    totals: list[float] = []
    for truth_order in itertools.permutations(range(len(truths)), size):
        scores: list[PointScore] = []
        total = 0.0
        for item_index, truth_index in enumerate(truth_order):
            truth = truths[truth_index]
            pixel = pixels[item_index]
            error_m = world_distance_m(pixel, truth.center_pixel, homography)
            total += error_m
            scores.append(
                PointScore(
                    robot_id=truth.robot_id,
                    returned_label=items[item_index].label,
                    point_yx=items[item_index].point_yx,
                    point_pixel=pixel,
                    truth_pixel=truth.center_pixel,
                    error_px=math.dist(pixel, truth.center_pixel),
                    error_m=error_m,
                    verdict=classify_point_error(error_m),
                )
            )
        totals.append(total)
        if best is None or total < best[0]:
            best = (total, scores)

    assert best is not None
    runner_up = sorted(totals)[1] if len(totals) > 1 else None
    return PointScoring(
        scores=best[1],
        total_error_m=best[0],
        swapped_total_error_m=runner_up,
        returned_separation_m=returned_separation,
        truth_separation_m=truth_separation,
    )


def build_text_states(condition: TextCondition) -> list[RobotStateInput]:
    """Build the text robot-state block for one condition of the 2x2.

    Args:
        condition: `"conflict"` (0.35 m apart, mutually facing, both STOPPED)
            or `"clear"` (2.5 m apart, headings diverging, both MOVING).

    Returns:
        Two `RobotStateInput` values, robot_1 first.
    """
    raw = _CONFLICT_STATES if condition == "conflict" else _CLEAR_STATES
    return [RobotStateInput(**state) for state in raw]


def build_cell_request(
    cell: str,
    repeat: int,
    image_path: Path,
    condition: TextCondition,
    include_pairwise_geometry: bool,
) -> ReasonerRequest:
    """Build the real M2 request for one 2x2 cell and repeat.

    Args:
        cell: Cell label (`"A"`..`"D"`).
        repeat: 1-based repeat index within the cell.
        image_path: Stimulus frame to attach.
        condition: Text robot-state condition.
        include_pairwise_geometry: Rev-8 modality axis; `False` withholds the
            derived distance/facing lines.

    Returns:
        A `ReasonerRequest` carrying the project's production contract.
    """
    geometry_tag = "geom" if include_pairwise_geometry else "nogeom"
    return ReasonerRequest(
        request_id=f"er2-grounding-{cell}-{geometry_tag}-{repeat}",
        image_path=str(image_path),
        frame_id="overhead_camera",
        stamp=0.0,
        robot_states=build_text_states(condition),
        include_pairwise_geometry=include_pairwise_geometry,
    )


def nearest_scene_row(rows: list[dict[str, Any]], stamp: float) -> tuple[dict[str, Any], float]:
    """Find the M1 scene-log row closest to a frame's header stamp.

    Args:
        rows: Parsed scene-log records, each with a `scene.stamp`.
        stamp: Frame header stamp (the recorder burns this into the frame).

    Returns:
        The closest row and the absolute stamp delta in seconds.

    Raises:
        ValueError: If `rows` is empty.
    """
    if not rows:
        raise ValueError("scene log contained no rows with a scene.stamp")
    best = min(rows, key=lambda row: abs(float(row["scene"]["stamp"]) - stamp))
    return best, abs(float(best["scene"]["stamp"]) - stamp)


def load_scene_rows(path: Path) -> list[dict[str, Any]]:
    """Read an M1/M5 scene JSONL log into records that carry a scene stamp.

    Args:
        path: Path to `data/logs/m5_scene/<session>.jsonl`.

    Returns:
        Records whose `scene.stamp` and `scene.robots` are present.
    """
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            scene = record.get("scene")
            if isinstance(scene, dict) and "stamp" in scene and scene.get("robots"):
                rows.append(record)
    return rows


def measure_stimulus(
    name: str,
    path: Path,
    calibration: Any,
    marker_dictionary: str,
    scene_rows: list[dict[str, Any]] | None,
    burned_in_stamp: float | None,
) -> StimulusMeasurement:
    """Measure a stimulus frame's robot positions objectively.

    Runs the project's own ArUco detector over the frame first. The stimuli are
    M1 *annotated* frames (the production M2 input), whose overlay boxes and
    velocity arrows are drawn on top of the markers, so re-detection can fail
    on a robot that M1 itself detected in the raw frame; for those robots the
    fallback is M1's own recorded state at the frame's header stamp, which the
    recorder burns into the frame.

    Args:
        name: Stimulus label, e.g. `"FRAME_CONFLICT"`.
        path: Frame path.
        calibration: Loaded `CalibrationArtifact`.
        marker_dictionary: ArUco dictionary name.
        scene_rows: Parsed scene-log rows, or `None` to skip the fallback.
        burned_in_stamp: The frame's header stamp as read from the overlay.

    Returns:
        The measurement, including the measured robot separation in metres.

    Raises:
        FileNotFoundError: If the frame cannot be read.
    """
    import cv2

    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"could not read stimulus frame: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    marker_ids, corners = detect_aruco_markers(rgb, marker_dictionary)
    detections = build_marker_detections(marker_ids, corners, calibration)

    robots: dict[str, RobotGroundTruth] = {}
    for detection in detections:
        robot_id = f"robot_{detection.marker_id}"
        robots[robot_id] = RobotGroundTruth(
            robot_id=robot_id,
            source="aruco",
            center_pixel=detection.center_pixel,
            center_world=detection.center_world,
            theta=detection.theta,
        )

    scene_stamp: float | None = None
    scene_delta: float | None = None
    if scene_rows and burned_in_stamp is not None:
        row, scene_delta = nearest_scene_row(scene_rows, burned_in_stamp)
        scene_stamp = float(row["scene"]["stamp"])
        for robot in row["scene"]["robots"]:
            robot_id = str(robot["robot_id"])
            if robot_id in robots:
                continue
            world = (float(robot["x"]), float(robot["y"]))
            pixel = world_to_pixel(world, calibration.homography)
            robots[robot_id] = RobotGroundTruth(
                robot_id=robot_id,
                source="scene_log",
                center_pixel=(float(pixel[0]), float(pixel[1])),
                center_world=world,
                theta=float(robot["theta"]),
            )

    ordered = [robots[key] for key in sorted(robots)]
    separation = None
    if len(ordered) == 2:
        separation = math.hypot(
            ordered[0].center_world[0] - ordered[1].center_world[0],
            ordered[0].center_world[1] - ordered[1].center_world[1],
        )
    return StimulusMeasurement(
        name=name,
        path=str(path),
        sha256=sha256_file(path),
        image_size=(width, height),
        aruco_marker_ids=sorted(int(marker_id) for marker_id in marker_ids),
        robots=ordered,
        separation_m=separation,
        burned_in_stamp=burned_in_stamp,
        scene_log_stamp=scene_stamp,
        scene_log_delta_sec=scene_delta,
    )


class JsonlWriter:
    """Append-only JSONL writer for the probe's auditable call log."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> None:
        """Append one record with a UTC timestamp.

        Args:
            record: JSON-serializable record; must not contain the API key or
                base64 image data.
        """
        payload = {"ts": datetime.now(timezone.utc).isoformat(), **record}
        with self.path.open("a") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")


def run_experiment_1(
    backend: GeminiBackend,
    config: ReasonerConfig,
    stimuli: dict[str, StimulusMeasurement],
    homography: np.ndarray,
    repeats: int,
    writer: JsonlWriter,
    api_key: str | None,
) -> None:
    """Ask ER-2 to point at the robots and score the points against ground truth.

    Args:
        backend: Constructed `GeminiBackend` (same transport as production M2).
        config: Reasoner config carrying timeout and max_tokens.
        stimuli: Measured stimuli keyed by name.
        homography: Pixel-to-world homography for the metric error.
        repeats: Calls per stimulus.
        writer: JSONL artifact writer.
        api_key: Key value, used only to scrub it from error text.
    """
    for name, measurement in stimuli.items():
        for repeat in range(1, repeats + 1):
            payload = PromptPayload(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=POINTING_PROMPT,
                image_path=measurement.path,
                known_robot_ids=[robot.robot_id for robot in measurement.robots],
            )
            start = time.monotonic()
            error: str | None = None
            text = ""
            usage: dict[str, int] | None = None
            try:
                response = backend.analyze(payload, config)
                text = response.text
                usage = response.token_usage
            except (BackendTimeoutError, ConnectionError, ValueError) as exc:
                error = redact_secret(f"{type(exc).__name__}: {exc}", api_key)
            latency_ms = int((time.monotonic() - start) * 1000)

            items = parse_point_items(text)
            scoring = score_points(items, measurement.robots, measurement.image_size, homography)
            print(
                f"[exp1] {name} repeat={repeat} n_points={len(items)} "
                f"total_error_m={scoring.total_error_m:.3f} "
                f"returned_sep_m={scoring.returned_separation_m} "
                f"verdicts={[score.verdict for score in scoring.scores]} error={error}"
            )
            writer.write(
                {
                    "experiment": 1,
                    "stimulus": name,
                    "stimulus_sha256": measurement.sha256,
                    "repeat": repeat,
                    "model_id": backend.model_id,
                    "thinking_level": backend.thinking_level,
                    "prompt": "pointing",
                    "raw_text": text,
                    "points": [item.model_dump(mode="json") for item in items],
                    "scoring": scoring.model_dump(mode="json"),
                    "latency_ms": latency_ms,
                    "token_usage": usage,
                    "error": error,
                }
            )


def run_decision_cells(
    reasoner: Reasoner,
    cells: tuple[tuple[str, str, str], ...],
    stimuli: dict[str, StimulusMeasurement],
    repeats: int,
    include_pairwise_geometry: bool,
    experiment: int,
    writer: JsonlWriter,
    model_id: str,
    thinking_level: str,
    api_key: str | None,
) -> None:
    """Run the real M2 decision prompt over a set of image/text cells.

    Args:
        reasoner: Project `Reasoner` wrapping the `gemini` backend.
        cells: `(cell, stimulus_name, text_condition)` triples, in run order.
        stimuli: Measured stimuli keyed by name.
        repeats: Calls per cell.
        include_pairwise_geometry: Rev-8 modality axis for every cell here.
        experiment: Experiment number recorded in the artifact (2 or 3).
        writer: JSONL artifact writer.
        model_id: Backend model id, recorded per call.
        thinking_level: Backend thinking level, recorded per call.
        api_key: Key value, used only to scrub it from error text.
    """
    for cell, stimulus_name, condition in cells:
        measurement = stimuli[stimulus_name]
        for repeat in range(1, repeats + 1):
            request = build_cell_request(
                cell,
                repeat,
                Path(measurement.path),
                condition,
                include_pairwise_geometry,
            )
            start = time.monotonic()
            error: str | None = None
            decision_dump: dict[str, Any] | None = None
            diagnostics: dict[str, Any] | None = None
            raw_text = ""
            try:
                result = reasoner.run(request)
                raw_text = result.raw_text or ""
                diagnostics = result.diagnostics.model_dump(mode="json")
                if result.decision is not None:
                    decision_dump = result.decision.model_dump(mode="json")
            except (BackendTimeoutError, ConnectionError, ValueError) as exc:
                error = redact_secret(f"{type(exc).__name__}: {exc}", api_key)
            latency_ms = int((time.monotonic() - start) * 1000)

            summary = "none" if decision_dump is None else (
                f"{decision_dump['congestion_detected']}/{decision_dump['type']}"
                f"/{decision_dump['strategy']}"
            )
            print(
                f"[exp{experiment}] cell={cell} image={stimulus_name} text={condition} "
                f"geometry={include_pairwise_geometry} repeat={repeat} -> {summary} "
                f"latency_ms={latency_ms} error={error}"
            )
            writer.write(
                {
                    "experiment": experiment,
                    "cell": cell,
                    "stimulus": stimulus_name,
                    "stimulus_sha256": measurement.sha256,
                    "text_condition": condition,
                    "include_pairwise_geometry": include_pairwise_geometry,
                    "repeat": repeat,
                    "model_id": model_id,
                    "thinking_level": thinking_level,
                    "request": request.model_dump(mode="json"),
                    "decision": decision_dump,
                    "diagnostics": diagnostics,
                    "raw_text": raw_text,
                    "latency_ms": latency_ms,
                    "error": error,
                }
            )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--frame-conflict",
        type=Path,
        default=Path(DEFAULT_LOG_DIR) / "stimuli" / "frame_conflict.png",
        help="Stimulus frame where the robots are nose-to-nose.",
    )
    parser.add_argument(
        "--frame-clear",
        type=Path,
        default=Path(DEFAULT_LOG_DIR) / "stimuli" / "frame_clear.png",
        help="Stimulus frame where the robots are far apart.",
    )
    parser.add_argument(
        "--conflict-stamp",
        type=float,
        default=None,
        help="Header stamp burned into the conflict frame, for scene-log lookup.",
    )
    parser.add_argument(
        "--clear-stamp",
        type=float,
        default=None,
        help="Header stamp burned into the clear frame, for scene-log lookup.",
    )
    parser.add_argument(
        "--scene-log",
        type=Path,
        default=None,
        help="M1/M5 scene JSONL used as ground truth where ArUco re-detection fails.",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=REPO_ROOT / DEFAULT_CALIBRATION,
        help="Calibration YAML (homography + image size).",
    )
    parser.add_argument(
        "--marker-dictionary",
        default=DEFAULT_MARKER_DICTIONARY,
        help="ArUco dictionary name used by M1.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Interactions API model id.")
    parser.add_argument(
        "--thinking-level",
        choices=["low", "high"],
        default="low",
        help="generation_config.thinking_level (default: low, as in the live run).",
    )
    parser.add_argument(
        "--experiment",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Which experiment to run.",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Calls per stimulus or cell.")
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Per-request timeout in seconds."
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=None,
        help="JSONL artifact path (default: data/logs/er2_grounding/<UTC>.jsonl).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Measure the stimuli and print the plan; no network call, no API key needed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Measure the stimuli, then run the selected experiments against ER-2.

    Args:
        argv: Command-line arguments, or `None` to use `sys.argv[1:]`.

    Returns:
        Process exit code: 0 on success (including `--dry-run`), 1 on a
        measurement failure, 2 if no API key is set for a live run.
    """
    args = _parse_args(argv)
    calibration = load_calibration(args.calibration)
    scale = mean_scale_m_per_px(calibration.homography)
    scene_rows = load_scene_rows(args.scene_log) if args.scene_log is not None else None

    try:
        stimuli = {
            CONFLICT_FRAME: measure_stimulus(
                CONFLICT_FRAME,
                args.frame_conflict,
                calibration,
                args.marker_dictionary,
                scene_rows,
                args.conflict_stamp,
            ),
            CLEAR_FRAME: measure_stimulus(
                CLEAR_FRAME,
                args.frame_clear,
                calibration,
                args.marker_dictionary,
                scene_rows,
                args.clear_stamp,
            ),
        }
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    criteria = {
        "robot_width_m": ROBOT_WIDTH_M,
        "clear_hit_m": CLEAR_HIT_M,
        "clear_hit_px": CLEAR_HIT_M / scale,
        "right_robot_m": RIGHT_ROBOT_M,
        "right_robot_px": RIGHT_ROBOT_M / scale,
        "scale_m_per_px": scale,
    }
    print(f"calibration scale: {scale:.6f} m/px")
    print(
        "pass criteria: clear hit <= "
        f"{CLEAR_HIT_M:.2f} m ({criteria['clear_hit_px']:.1f} px), right robot <= "
        f"{RIGHT_ROBOT_M:.2f} m ({criteria['right_robot_px']:.1f} px)"
    )
    for measurement in stimuli.values():
        print(
            f"{measurement.name}: separation="
            f"{'n/a' if measurement.separation_m is None else f'{measurement.separation_m:.3f} m'} "
            f"aruco_ids={measurement.aruco_marker_ids} "
            f"sources={[robot.source for robot in measurement.robots]} "
            f"scene_log_delta_sec={measurement.scene_log_delta_sec}"
        )
        for robot in measurement.robots:
            print(
                f"  {robot.robot_id}: world={robot.center_world} pixel={robot.center_pixel} "
                f"source={robot.source}"
            )

    incomplete = [m.name for m in stimuli.values() if len(m.robots) != 2]
    if incomplete:
        print(
            f"WARNING: no two-robot ground truth for {incomplete}; "
            "pass --scene-log and the frames' burned-in stamps",
            file=sys.stderr,
        )

    if args.dry_run:
        print("DRY RUN: no network call made, no API key read or required.")
        for cell, stimulus_name, condition in CELLS:
            states = build_text_states(condition)
            print(
                f"  cell {cell}: image={stimulus_name} text={condition} "
                f"states={[state.model_dump(mode='json') for state in states]}"
            )
        print("  experiment 3 re-runs cells B and C with include_pairwise_geometry=False")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: set GEMINI_API_KEY in the environment.", file=sys.stderr)
        return 2

    log_path = args.log_path or (
        REPO_ROOT
        / DEFAULT_LOG_DIR
        / f"grounding_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    )
    writer = JsonlWriter(log_path)
    print(f"artifact: {log_path}")

    # seed is left unset on purpose: with generation_config.seed pinned the
    # repeats would be one sample reported three times, and the Interactions
    # API offers no temperature control to hold constant instead.
    backend = GeminiBackend(
        model_id=args.model,
        thinking_level=args.thinking_level,
        force_schema=False,
        seed=None,
    )
    config = ReasonerConfig(backend_id="gemini", timeout_sec=args.timeout)
    reasoner = Reasoner(backend, config)

    writer.write(
        {
            "record_type": "meta",
            "model_id": args.model,
            "thinking_level": args.thinking_level,
            "force_schema": False,
            "seed": None,
            "repeats": args.repeats,
            "experiment": args.experiment,
            "criteria": criteria,
            "reasoner_config": config.model_dump(mode="json"),
            "stimuli": {
                name: measurement.model_dump(mode="json")
                for name, measurement in stimuli.items()
            },
        }
    )

    selected = args.experiment
    if selected in ("1", "all"):
        run_experiment_1(
            backend,
            config,
            stimuli,
            calibration.homography,
            args.repeats,
            writer,
            api_key,
        )
    if selected in ("2", "all"):
        run_decision_cells(
            reasoner,
            CELLS,
            stimuli,
            args.repeats,
            True,
            2,
            writer,
            args.model,
            args.thinking_level,
            api_key,
        )
    if selected in ("3", "all"):
        ablation_cells = tuple(cell for cell in CELLS if cell[0] in ("B", "C"))
        run_decision_cells(
            reasoner,
            ablation_cells,
            stimuli,
            args.repeats,
            False,
            3,
            writer,
            args.model,
            args.thinking_level,
            api_key,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
