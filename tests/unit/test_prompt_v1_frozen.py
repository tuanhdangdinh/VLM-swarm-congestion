"""Frozen prompt v1: every stored pre-bundle prompt must re-render byte-identically.

The SHA-256 values below were rendered at 4a71ffb (the last commit before the
prompt-v2 bundle), by the builder that produced every decision artifact stored
to date. The replay program re-hashes stored prompts against `user_sha256`, so
`prompt_version=1` has to keep producing exactly these strings. The matrix
covers every rendering branch the v1 template has, including the goal/task
path no live prompt ever exercised. If a test fails after a fixture below was
edited, the fixture moved, not the renderer: restore the fixture rather than
regenerating a constant.
"""

import hashlib
from collections.abc import Callable

import pytest

from reasoning.vlm.models import (
    FailureContext,
    ReasonerRequest,
    RobotStateInput,
    StaticObstacleInput,
)
from reasoning.vlm.prompt_builder import build_prompt_payload


def _base() -> ReasonerRequest:
    return ReasonerRequest(
        request_id="req-1",
        image_path="/tmp/frame.png",
        frame_id="overhead_camera",
        stamp=12.5,
        robot_states=[
            RobotStateInput(robot_id="robot_2", x=1.0, y=2.0, theta=1.57, status="MOVING"),
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
        ],
    )


def _with(**update: object) -> ReasonerRequest:
    return ReasonerRequest(**{**_base().model_dump(), **update})


def _completed_wait() -> FailureContext:
    return FailureContext(
        strategy="temporary_wait",
        outcome_status="completed",
        failure_detail=(
            "temporary_wait completed 17 s ago; congestion re-detected for the same robots"
        ),
    )


def _failed_yield() -> FailureContext:
    return FailureContext(
        strategy="yield",
        yield_robot="robot_1",
        outcome_status="failed",
        failure_detail="yield failed after 122 s; congestion re-detected for the same robots",
    )


def _obstacle() -> StaticObstacleInput:
    return StaticObstacleInput(obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3)


def _goal_task_states() -> list[RobotStateInput]:
    return [
        RobotStateInput(
            robot_id="robot_1",
            x=-0.2,
            y=0.0,
            theta=0.0,
            linear_velocity=0.01,
            status="STOPPED",
            task="cross_narrow_aisle",
            goal=(2.5, 0.0),
        ),
        RobotStateInput(
            robot_id="robot_2",
            x=0.2,
            y=0.0,
            theta=3.14,
            linear_velocity=0.0,
            status="STALE",
            task="cross_narrow_aisle",
            goal=(-2.5, 0.0),
        ),
        RobotStateInput(robot_id="robot_3", x=-1.2, y=0.0, theta=0.0, status="MOVING"),
    ]


_MATRIX: dict[str, Callable[[], ReasonerRequest]] = {
    "baseline": _base,
    "id_desc": lambda: _with(robot_presentation_order="id_desc"),
    "no_geometry": lambda: _with(include_pairwise_geometry=False),
    "obstacles_on": lambda: _with(static_obstacles=[_obstacle()], include_static_obstacles=True),
    "crosscheck_on": lambda: _with(include_visual_crosscheck=True),
    "crosscheck_no_geometry": lambda: _with(
        include_visual_crosscheck=True, include_pairwise_geometry=False
    ),
    "single_failure": lambda: _with(failure_context=_failed_yield()),
    "double_failure": lambda: _with(
        failure_context=_completed_wait(), last_failed_context=_failed_yield()
    ),
    "goal_task_three_robots_desc": lambda: _with(
        robot_states=_goal_task_states(),
        robot_presentation_order="id_desc",
        static_obstacles=[_obstacle()],
        include_static_obstacles=True,
    ),
}

# name -> (length, SHA-256) of the v1 user prompt, rendered at 4a71ffb.
_V1_PINS: dict[str, tuple[int, str]] = {
    "baseline": (
        3338,
        "3b77d224bb1c6de2f73ccd69c08b6ac686ae41dd9dca86442e5f34d278164001",
    ),
    "crosscheck_no_geometry": (
        3924,
        "80fd93a0736b074b6ca3b1ea30ffa52f5366a64a51f890205c9fdcf707086e4d",
    ),
    "crosscheck_on": (
        4169,
        "4eab5002f87b1a687693e47850c12ceb1c97679c5795571084bb16ffcec4f8e5",
    ),
    "double_failure": (
        3963,
        "2cddfa30f806e218dd97341e1a390aee4317852196b92feab3c646229fdcc56f",
    ),
    "goal_task_three_robots_desc": (
        4004,
        "9d742a0b0edc49fbf04697cc7c6b30a81f1be547f2fb08447b746eb4bd69610e",
    ),
    "id_desc": (
        3338,
        "a56166152d809f1ecfaf332e230e74e1de2e77a7b40fc22c0f712deef444d540",
    ),
    "no_geometry": (
        3152,
        "a9c8abfc900a47d77a725b4855252a3ae623698a00e3ca394808cbed281945ed",
    ),
    "obstacles_on": (
        3576,
        "9fa91b27b08a279cebda44b727abbaaf73c520b3581c7061f81ed7b84977a9f0",
    ),
    "single_failure": (
        3697,
        "5c58e47ca9d65ed07aada587d3bb55112cfdba40c53516062f067291ba1486fe",
    ),
}


def _v1(name: str) -> ReasonerRequest:
    return ReasonerRequest(**{**_MATRIX[name]().model_dump(), "prompt_version": 1})


@pytest.mark.parametrize("name", sorted(_MATRIX))
def test_v1_prompt_is_byte_identical_to_pre_bundle_render(name: str) -> None:
    prompt = build_prompt_payload(_v1(name)).user_prompt
    length, digest = _V1_PINS[name]
    # Length first: it names the size of any drift, which the hash alone withholds.
    assert len(prompt) == length
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == digest


def test_v1_baseline_pin_matches_the_long_standing_prompt_builder_pin() -> None:
    # The same string `test_prompt_builder._PRE_OBSTACLE_OFF_PROMPT_SHA256` has
    # pinned since the static-obstacle modality landed.
    assert _V1_PINS["baseline"] == (
        3338,
        "3b77d224bb1c6de2f73ccd69c08b6ac686ae41dd9dca86442e5f34d278164001",
    )
