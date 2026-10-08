"""Rear retreat room on the S1 rack-flanked floor under the dynamic-arms views.

S1 pilot ep1 (`s1_ep1_seed1_mock_a2`, echo replay of all 216 trigger scenes)
refused every yield with "no feasible yielder ... 0.00 m retreat room" for
every robot. `yield_retreat_room_m` checked static obstacles across the whole
aisle width either side of the yielder, and S1 declares the racks that flank
every aisle as static obstacles: a robot in a 1.2 m aisle sits <= 0.6 m from
both flanking racks, a dynamic lane's mouth is the robot's own position (a
crossing's is the junction box edge, where the racks start), so each flanking
rack straddled the mouth and read as 0 m. The dynamic views now check rear
room across the robot's swept footprint (`SceneGeometry.rear_room_band`), and
the yield gate scores only a lane's own pair (`SceneGeometry.lane_robots`).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from swarm_orchestrator.models import load_config
from swarm_orchestrator.reasoning_pipeline import load_grounding_source

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_candidates import generate_retreat_candidates
from reasoning.rag.scene_geometry import SceneGeometry, required_room_m, yield_retreat_room_m
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPD = REPO_ROOT / "isaac/config/scenarios/mapd_5.yaml"
ORCH = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
GROUNDING_FILE = REPO_ROOT / "config/grounding/s1_dynamic.yaml"

Pose = tuple[float, float, float]

# The pilot overlay's six boxes: four rack quadrants (|x| in [0.6, 2.5],
# |y| in [0.6, 1.8]) and the A55-E gate jaws (x in [0.7, 1.7],
# |y| in [0.275, 0.6]).
_SIX_BOXES = [
    StaticObstacleInput(obstacle_id=f"obstacle_{i}", x=x, y=y, size_x_m=sx, size_y_m=sy)
    for i, (x, y, sx, sy) in enumerate(
        [
            (-1.55, 1.2, 1.9, 1.2),
            (1.55, 1.2, 1.9, 1.2),
            (-1.55, -1.2, 1.9, 1.2),
            (1.55, -1.2, 1.9, 1.2),
            (1.2, 0.4375, 1.0, 0.325),
            (1.2, -0.4375, 1.0, 0.325),
        ],
        start=1,
    )
]
# The S1 overlay's declared geometry: the junction box, no arms.
_S1 = SceneGeometry.model_validate(
    {
        "corridor": {
            "axis": "x",
            "center_m": 0.0,
            "half_length_m": 0.6,
            "aisle_half_width_m": 0.6,
            "occluder_height_m": 0.9,
        },
    }
)
_DYNAMIC = GroundingParams(
    mode="derived",
    dynamic_scene_arms=True,
    aisle_y_band_m=(-0.46, 0.46),
    aisle_x_band_m=(-0.46, 0.46),
)

# Real ep1 scene: request 2b64d25e2c0b49acb063f8b842874a75, M1 stamp 559.7,
# a 5-robot close/slow trigger (decision artifact `scene`, rounded to 0.1 mm).
# robot_1 is stopped in the A55-E bay short of E, which robot_5 still holds;
# robots 2-4 queue on the N arm.
_EP1_SCENE: dict[str, Pose] = {
    "robot_1": (1.9373, 0.0479, -0.095),
    "robot_2": (-0.0458, 1.4666, 0.245),
    "robot_3": (-0.3116, 0.7213, 0.8885),
    "robot_4": (-0.1395, 1.0743, 0.8885),
    "robot_5": (2.3066, 0.0011, 3.1172),
}
_EP1_GOALS = {
    "robot_1": (2.3, 0.0),
    "robot_2": (-2.3, 0.35),
    "robot_3": (0.0, 1.55),
    "robot_4": (0.0, 1.55),
    "robot_5": (0.0, -1.55),
}
_FIVE = ["robot_1", "robot_2", "robot_3", "robot_4", "robot_5"]


def _frame(
    poses: dict[str, Pose], goals: dict[str, tuple[float, float]] | None = None
) -> SnapshotFrame:
    goals = goals or {}
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta, goal=goals.get(rid))
            for rid, (x, y, theta) in poses.items()
        ],
    )


def _decision(involved: list[str], yield_robot: str) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=involved,
        root_cause="standoff",
        strategy="yield",
        justification="jam",
        yield_robot=yield_robot,
    )


def _ground(
    decision: CongestionDecision,
    frame: SnapshotFrame,
    *,
    geometry: SceneGeometry = _S1,
    params: GroundingParams = _DYNAMIC,
    obstacles: list[StaticObstacleInput] | tuple[StaticObstacleInput, ...] = tuple(_SIX_BOXES),
) -> dict[str, Any]:
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    result = ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)
    return ground_reasoner_result(
        result,
        robot_positions={s.robot_id: (s.x, s.y) for s in frame.robots},
        geometry=geometry,
        static_obstacles=obstacles,
        yield_feasibility_mode="swap",
        snapshot=frame,
        params=params,
    )


def _overlay() -> dict[str, Any]:
    lines = MAPD.read_text().splitlines()
    begin = lines.index("#   --- M5 overlay begin ---")
    end = lines.index("#   --- M5 overlay end ---")
    return yaml.safe_load("\n".join(line[4:] for line in lines[begin + 1:end]))


def _gate_tags(command: dict[str, Any]) -> list[str]:
    return [t for t in command.get("degradations", []) if t.startswith("yield=infeasible:")]


# ---- the band itself ----

# W arm +0.35 lane, mid-route head-on: robot_1 faces east, robot_2 west.
_W_LANE: dict[str, Pose] = {"robot_1": (-1.6, 0.35, 0.0), "robot_2": (-1.2, 0.35, math.pi)}


def test_lane_room_ignores_the_racks_flanking_the_lane():
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_2"], "robot_1"), _frame(_W_LANE), _S1, _DYNAMIC
    )
    assert view.geometry is not None
    assert view.geometry.rear_room_band == "footprint"
    assert view.geometry.lane_robots == ("robot_1", "robot_2")
    # Rack obstacle_1 (y >= 0.6) is 0.25 m beside robot_1's centre, outside
    # its 0.09 m half-width: nothing declared lies in its strip to the west.
    assert yield_retreat_room_m((-1.6, 0.35), -1.0, _SIX_BOXES, view.geometry) is None


def test_aisle_band_reads_the_same_flanking_rack_as_zero_room():
    # The declared-corridor semantics, unchanged: across the aisle width the
    # rack straddles the lane mouth at x=-1.6 and reads as 0 m. This is the
    # pilot's 0.00 m on the lane geometry before the fix.
    lane = SceneGeometry.model_validate(
        {
            "corridor": {
                "axis": "x",
                "center_m": -1.4,
                "half_length_m": 0.2,
                "aisle_half_width_m": 0.6,
                "occluder_height_m": 0.0,
            },
        }
    )
    assert lane.rear_room_band == "aisle"
    assert yield_retreat_room_m((-1.6, 0.35), -1.0, _SIX_BOXES, lane) == 0.0


def test_lane_room_still_counts_a_box_across_the_footprint():
    # robot_1 in the E bay at y=0.2: its strip [0.11, 0.29] meets the gate
    # jaw obstacle_5 (y >= 0.275), whose east face is at x=1.7.
    poses = {"robot_1": (1.95, 0.2, 0.0), "robot_2": (2.3, 0.2, math.pi)}
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_2"], "robot_1"), _frame(poses), _S1, _DYNAMIC
    )
    assert view.geometry is not None
    room = yield_retreat_room_m((1.95, 0.2), -1.0, _SIX_BOXES, view.geometry)
    assert room == pytest.approx(0.25)
    assert room < required_room_m(view.geometry)


def test_declared_geometry_rejects_an_unpaired_lane():
    with pytest.raises(ValueError, match="two different robots"):
        SceneGeometry.model_validate(
            {**_S1.model_dump(), "lane_robots": ("robot_1", "robot_1")}
        )


# ---- the yield gate under the dynamic views ----


def test_lane_yield_passes_the_gate_between_the_racks():
    command = _ground(_decision(["robot_1", "robot_2"], "robot_1"), _frame(_W_LANE))
    assert command["actions"][0]["robot_id"] == "robot_1"
    assert command["actions"][0]["action"] == "yield"
    assert _gate_tags(command) == []


def test_crossing_yield_passes_the_gate_between_the_racks():
    # W-lane robot heading east meets an S-arm robot heading north. Every
    # arm mouth is the junction box edge, where the racks start.
    poses = {"robot_1": (-0.45, 0.35, 0.0), "robot_2": (0.05, -0.45, math.pi / 2)}
    command = _ground(
        _decision(["robot_1", "robot_2"], "robot_1"), _frame(poses, {"robot_2": (0.0, 1.55)})
    )
    assert "grounding=dynamic_arms:crossing" in command["degradations"]
    assert command["actions"][0]["robot_id"] == "robot_1"
    assert command["actions"][0]["action"] == "yield"
    assert _gate_tags(command) == []


def test_lane_gate_swaps_only_within_the_lane_pair():
    # robot_1 is boxed by the gate jaw (0.25 m < required). robot_3, waiting
    # west of the junction, is listed before robot_2 and has an empty strip
    # behind it, but the lane robot_1/robot_2 says nothing about robot_3's
    # retreat: the swap goes to the lane partner.
    poses = {
        "robot_1": (1.95, 0.2, 0.0),
        "robot_2": (2.3, 0.2, math.pi),
        "robot_3": (-1.5, 0.0, 0.0),
    }
    command = _ground(_decision(["robot_1", "robot_3", "robot_2"], "robot_1"), _frame(poses))
    assert command["actions"][0]["robot_id"] == "robot_2"
    assert command["actions"][0]["action"] == "yield"
    assert "yield_robot=regrounded" in command["degradations"]


def test_lane_gate_refusal_names_only_the_lane_pair():
    # A box right behind each pair robot: the refusal lists the pair's rooms,
    # not an off-lane robot scored against a corridor that is not its own.
    poses = {
        "robot_1": (1.95, 0.2, 0.0),
        "robot_2": (2.3, 0.2, math.pi),
        "robot_3": (-1.5, 0.0, 0.0),
    }
    end_cap = StaticObstacleInput(obstacle_id="cap", x=2.75, y=0.0, size_x_m=0.5, size_y_m=1.2)
    command = _ground(
        _decision(["robot_1", "robot_3", "robot_2"], "robot_1"),
        _frame(poses),
        obstacles=[*_SIX_BOXES, end_cap],
    )
    (tag,) = _gate_tags(command)
    assert "robot_1 0.25 m, robot_2 0.20 m retreat room" in tag
    assert "robot_3" not in tag


# ---- the executed maneuver against the boxes (footprint band only) ----


def test_lane_sidestep_into_a_gate_jaw_is_not_a_candidate():
    # 0.45 m latch standoff in the E bay: the gate passes robot_1 (nothing in
    # its strip), but the 1.7 m clearance backs it 1.25 m to x=0.67, where
    # either 0.36 m sidestep puts its body 6 cm into a gate jaw (x >= 0.7).
    poses = {"robot_1": (1.92, 0.05, 0.0), "robot_2": (2.37, 0.0, math.pi)}
    command = _ground(_decision(["robot_1", "robot_2"], "robot_1"), _frame(poses))
    assert _gate_tags(command) == []
    assert (command["actions"][0]["robot_id"], command["actions"][0]["action"]) == (
        "robot_1",
        "reroute",
    )
    assert "retreat=no-valid-candidate" in command["degradations"]


def test_lane_backup_past_the_park_point_into_a_box_is_not_a_candidate():
    # A block across robot_1's strip 1.0 m behind it: enough for the gate's
    # park-point room (~0.75 m), not for the executed 1.3 m backup.
    block = StaticObstacleInput(obstacle_id="b", x=-2.7, y=0.35, size_x_m=0.2, size_y_m=1.2)
    command = _ground(
        _decision(["robot_1", "robot_2"], "robot_1"),
        _frame(_W_LANE),
        obstacles=[*_SIX_BOXES, block],
    )
    assert _gate_tags(command) == []
    assert command["actions"][0]["action"] == "reroute"
    assert "retreat=no-valid-candidate" in command["degradations"]


def test_declared_geometry_candidates_ignore_static_obstacles():
    # The aisle band keeps the pre-fix candidate set: no box sweep at all.
    frame = _frame(_W_LANE)
    block = StaticObstacleInput(obstacle_id="b", x=-2.7, y=0.35, size_x_m=0.2, size_y_m=1.2)
    without = generate_retreat_candidates(
        frame, "robot_1", 1.3, _DYNAMIC, geometry=_S1, passer_id="robot_2"
    )
    with_boxes = generate_retreat_candidates(
        frame,
        "robot_1",
        1.3,
        _DYNAMIC,
        geometry=_S1,
        passer_id="robot_2",
        static_obstacles=[*_SIX_BOXES, block],
    )
    assert with_boxes == without


def test_a_box_the_yielder_already_touches_does_not_veto_its_retreat():
    # robot_1 rides 0.08 m off rack obstacle_1's face (y >= 0.6): its body
    # already overlaps the rack, and so does every sample of a 0.8 m backup
    # (it ends at x=-2.4, still alongside the rack). The backup may keep that
    # contact; only the sidestep away from the rack may follow it.
    poses = {"robot_1": (-1.6, 0.52, 0.0), "robot_2": (-1.2, 0.52, math.pi)}
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_2"], "robot_1"),
        _frame(poses),
        _S1,
        GroundingParams(mode="derived", dynamic_scene_arms=True),
    )
    candidates = generate_retreat_candidates(
        _frame(poses),
        "robot_1",
        0.8,
        GroundingParams(mode="derived", dynamic_scene_arms=True),
        geometry=view.geometry,
        passer_id="robot_2",
        static_obstacles=_SIX_BOXES,
    )
    assert candidates
    assert all(c.y < 0.52 for c in candidates)


# ---- regression: one real S1 pilot ep1 scene through the shipped config ----


def _shipped() -> tuple[SceneGeometry, tuple[StaticObstacleInput, ...], GroundingParams]:
    raw = yaml.safe_load(ORCH.read_text())
    raw.update(_overlay())
    config = load_config(raw)
    assert config.scenario_geometry is not None
    params = load_grounding_source(GROUNDING_FILE).params
    return config.scenario_geometry, config.static_obstacles, params


def test_ep1_gate_pair_yield_is_feasible_with_a_hand_computed_room():
    geometry, obstacles, params = _shipped()
    frame = _frame(_EP1_SCENE, _EP1_GOALS)
    decision = _decision(["robot_1", "robot_5"], "robot_1")
    view = resolve_grounding_view(decision, frame, geometry, params)
    assert view.tags == (
        "grounding=node_handoff:robot_1->robot_5",
        "grounding=dynamic_arms:lane:x",
    )
    assert view.geometry is not None
    # Hand-computed: robot_1's strip y in [-0.042, 0.138] westward from
    # x=1.937 passes the gate jaws (|y| >= 0.275) and the racks (|y| >= 0.6)
    # and first meets the W tracked-band cap at x=-2.5: 1.937 + 2.5. Before
    # the fix the flanking rack obstacle_2 (x in [0.6, 2.5], 0.552 m beside
    # it) read as 0.00 m.
    room = yield_retreat_room_m((1.9373, 0.0479), -1.0, obstacles, view.geometry)
    assert room == pytest.approx(4.437, abs=1e-3)
    assert room >= required_room_m(view.geometry)
    # robot_5 holds E, 0.193 m inside the E cap: honestly infeasible, so the
    # swap gate can never back it out of tracking.
    assert yield_retreat_room_m((2.3066, 0.0011), 1.0, obstacles, view.geometry) == (
        pytest.approx(0.193, abs=1e-3)
    )
    command = _ground(decision, frame, geometry=geometry, params=params, obstacles=obstacles)
    assert _gate_tags(command) == []
    action = command["actions"][0]
    assert (action["robot_id"], action["action"]) == ("robot_1", "yield")
    # Clearance 1.7 from robot_5 0.369 m ahead: a 1.331 m backup west, out
    # of the gate (x in [0.7, 1.7]) to x=0.606 before the sidestep.
    assert action["parameters"]["backup_distance_m"] == pytest.approx(1.331)
    assert action["parameters"]["retreat_x_m"] == pytest.approx(0.606, abs=1e-3)


def test_ep1_five_robot_echo_yield_clears_the_room_gate():
    # The echo mock's decision on this scene: every robot involved, robot_1
    # (first stalled in prompt order) yields. The gate scores the lane pair
    # and passes robot_1.
    geometry, obstacles, params = _shipped()
    command = _ground(
        _decision(_FIVE, "robot_1"),
        _frame(_EP1_SCENE, _EP1_GOALS),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert not any("no feasible yielder" in t for t in _gate_tags(command))
