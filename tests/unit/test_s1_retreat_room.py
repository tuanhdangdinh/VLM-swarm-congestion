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
from swarm_execution.crossing_chain import plan_crossing
from swarm_execution.safety import crossing_order_from_parameters
from swarm_orchestrator.models import load_config
from swarm_orchestrator.reasoning_pipeline import load_grounding_source

from reasoning.rag.command_grounder import (
    filter_command_robot_ids,
    ground_reasoner_result,
    plan_matches_dispatch,
    resolve_yield_roles,
    verify_and_repair_plan,
)
from reasoning.rag.grounding_view import resolve_grounding_view
from reasoning.rag.maneuver_geometry import GroundingParams, derive_backup_distance
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


def test_plan_repair_never_hands_the_lane_yield_to_an_off_lane_robot():
    # Both lane robots are boxed 0.3 m behind; robot_3 waits in the
    # junction box with an empty strip. The plan channel's swap repair must
    # not move the yield onto robot_3: the plan falls back like the gate.
    poses = {
        "robot_1": (-1.6, 0.35, 0.0),
        "robot_2": (-1.2, 0.35, math.pi),
        "robot_3": (0.3, -0.3, 0.0),
    }
    blocks = [
        StaticObstacleInput(obstacle_id="b1", x=-2.0, y=0.35, size_x_m=0.2, size_y_m=1.2),
        StaticObstacleInput(obstacle_id="b2", x=-0.8, y=0.35, size_x_m=0.2, size_y_m=0.4),
    ]
    decision = CongestionDecision.model_validate(
        {
            **_decision(["robot_1", "robot_3", "robot_2"], "robot_1").model_dump(),
            "proposed_plan": [
                {"robot_id": "robot_1", "action": "yield"},
                {"robot_id": "robot_3", "action": "cross"},
                {"robot_id": "robot_2", "action": "cross"},
            ],
        }
    )
    plan = verify_and_repair_plan(
        decision,
        _frame(poses),
        geometry=_S1,
        static_obstacles=[*_SIX_BOXES, *blocks],
        yield_feasibility_mode="swap",
        grounding_params=_DYNAMIC,
    )
    assert ("robot_3", "yield") not in [(leg.robot_id, leg.action) for leg in plan.legs]
    assert plan.provenance == "m3_default"


# ---- the executed maneuver against the boxes (footprint band only) ----


def test_lane_sidestep_into_a_gate_jaw_deepens_the_backup():
    # 0.45 m latch standoff in the E bay: the gate passes robot_1 (nothing in
    # its strip), but the 1.7 m clearance backs it 1.25 m to x=0.67, where
    # either 0.36 m sidestep puts its body 6 cm into a gate jaw (x >= 0.7).
    # The backup deepens in 0.01 m steps until the body clears the jaw
    # (zero box margin under `_DYNAMIC`): x <= 0.7 - 0.09 = 0.61, a 1.31 m
    # backup, instead of rerouting the yielder.
    poses = {"robot_1": (1.92, 0.05, 0.0), "robot_2": (2.37, 0.0, math.pi)}
    command = _ground(_decision(["robot_1", "robot_2"], "robot_1"), _frame(poses))
    assert _gate_tags(command) == []
    action = command["actions"][0]
    assert (action["robot_id"], action["action"]) == ("robot_1", "yield")
    assert action["parameters"]["backup_distance_m"] == pytest.approx(1.31)
    assert action["parameters"]["retreat_x_m"] == pytest.approx(0.61, abs=1e-3)
    assert "retreat=deepened:1.25->1.31" in command["degradations"]


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
    # of the gate (x in [0.7, 1.7]) to x=0.606 -- 4 mm short of the 0.05 m
    # box margin (x <= 0.7 - 0.09 - 0.05 = 0.56). It deepens in 0.01 m steps
    # to 1.381 m, x=0.556, before the sidestep.
    assert action["parameters"]["backup_distance_m"] == pytest.approx(1.381)
    assert action["parameters"]["retreat_x_m"] == pytest.approx(0.556, abs=1e-3)


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


# ---- backup clearance under the footprint band (the sibling defect) ----
#
# Past the room gate the echo replay still refused all 216 ep1 yields with "no
# backup distance in band [0.5, 2.0] m satisfies clearance 1.7 m":
# `derive_backup_distance` projected every crossing-order robot onto the
# retreat axis, and the N-arm queue (robots 2-4, 0.67-1.42 m beside robot_1's
# lane) projects 1.98-2.25 m behind it, inside 1.7 m of every in-band backup.
# Under the footprint band only the side-fixing pair and robots inside the
# swept corridor (2 * half_width_m + FEASIBILITY_MARGIN_M = 0.38 m either side
# of the retreat line) count.

_EP1_ORDER = ["robot_5", "robot_2", "robot_3", "robot_4"]


def _ep1_view_geometry(poses: dict[str, Pose] | None = None) -> SceneGeometry:
    geometry, _, params = _shipped()
    view = resolve_grounding_view(
        _decision(_FIVE, "robot_1"), _frame(poses or _EP1_SCENE, _EP1_GOALS), geometry, params
    )
    assert view.geometry is not None
    assert view.geometry.rear_room_band == "footprint"
    assert view.geometry.lane_robots == ("robot_1", "robot_5")
    return view.geometry


def test_ep1_off_lane_queue_does_not_veto_the_lane_backup():
    _, _, params = _shipped()
    backup = derive_backup_distance(
        _frame(_EP1_SCENE, _EP1_GOALS),
        "robot_1",
        _EP1_ORDER,
        params,
        geometry=_ep1_view_geometry(),
    )
    # Hand-computed: robot_5 sits 0.369 m east of robot_1 (2.3066 - 1.9373),
    # so the 1.7 m clearance needs 1.7 - 0.369 = 1.331 m west. Robots 2-4 are
    # 1.419, 0.673 and 1.026 m beside the lane, outside the 0.38 m corridor.
    assert backup.feasible
    assert backup.value_m == pytest.approx(1.331)


def test_aisle_band_still_counts_the_off_lane_queue():
    # Same scene, same lane corridor, declared semantics: every crossing robot
    # is projected (the frozen v2 rule), so the queue still vetoes the backup.
    _, _, params = _shipped()
    aisle = _ep1_view_geometry().model_copy(update={"rear_room_band": "aisle"})
    backup = derive_backup_distance(
        _frame(_EP1_SCENE, _EP1_GOALS), "robot_1", _EP1_ORDER, params, geometry=aisle
    )
    assert not backup.feasible
    assert backup.reason == "no backup distance in band [0.5, 2.0] m satisfies clearance 1.7 m"


def test_ep1_five_robot_echo_yield_grounds_an_executable_backup():
    geometry, obstacles, params = _shipped()
    command = _ground(
        _decision(_FIVE, "robot_1"),
        _frame(_EP1_SCENE, _EP1_GOALS),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert not any(t.startswith("yield=infeasible") for t in command["degradations"])
    action = command["actions"][0]
    assert (action["robot_id"], action["action"]) == ("robot_1", "yield")
    # The clearance minimum (1.331 m) deepened past the box margin.
    assert action["parameters"]["backup_distance_m"] == pytest.approx(1.381)
    assert action["parameters"]["retreat_x_m"] == pytest.approx(0.556, abs=1e-3)


@pytest.mark.parametrize(
    "blocker",
    [
        (0.3, 0.05, 0.0),  # on the lane, 1.637 m behind robot_1
        (0.3, 0.38, 0.0),  # 0.332 m beside the lane: inside the 0.38 m corridor
    ],
)
def test_a_robot_in_the_backup_corridor_still_blocks_it(blocker: Pose):
    # robot_3 moved into robot_1's swept corridor, 1.637 m back: every
    # backup in [1.331, 2.0] m ends within 1.7 m of it (it would need
    # d >= 3.337 m), so the backup is refused before the candidate sweep.
    geometry, obstacles, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": blocker}
    frame = _frame(poses, _EP1_GOALS)
    backup = derive_backup_distance(
        frame, "robot_1", _EP1_ORDER, params, geometry=_ep1_view_geometry(poses)
    )
    assert not backup.feasible
    command = _ground(
        _decision(_FIVE, "robot_1"), frame, geometry=geometry, params=params, obstacles=obstacles
    )
    assert (
        "yield=infeasible:no backup distance in band [0.5, 2.0] m satisfies clearance 1.7 m"
        in command["degradations"]
    )
    assert command["actions"][0]["action"] == "reroute"
    # robot_3 is in the lane conflict now and stays in the order; the
    # off-lane robots 2 and 4 are dropped from it but still hold on the
    # reroute fallback, like every other involved robot.
    assert "order=lane_scoped:robot_2,robot_4" in command["degradations"]
    waits = {a["robot_id"] for a in command["actions"] if a["action"] == "temporary_wait"}
    assert waits == {"robot_2", "robot_3", "robot_4", "robot_5"}


def test_a_robot_just_outside_the_corridor_does_not_block():
    # The same 1.637 m back, 0.4 m beside the lane: outside the corridor.
    _, _, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": (0.3, 0.448, 0.0)}
    backup = derive_backup_distance(
        _frame(poses, _EP1_GOALS),
        "robot_1",
        _EP1_ORDER,
        params,
        geometry=_ep1_view_geometry(poses),
    )
    assert backup.feasible
    assert backup.value_m == pytest.approx(1.331)


def test_crossing_passer_off_the_retreat_line_still_sets_the_backup():
    # Crossing view: robot_1 retreats west along its W arm, the S-arm passer
    # robot_2 is 0.8 m beside that line but fixes the retreat side, so it is
    # always counted: 0.5 m behind robot_1's retreat (s = -0.5) -> 1.2 m.
    poses = {"robot_1": (-0.45, 0.35, 0.0), "robot_2": (0.05, -0.45, math.pi / 2)}
    frame = _frame(poses, {"robot_2": (0.0, 1.55)})
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_2"], "robot_1"), frame, _S1, _DYNAMIC
    )
    assert view.geometry is not None
    assert view.geometry.rear_room_band == "footprint"
    assert view.geometry.lane_robots is None
    backup = derive_backup_distance(frame, "robot_1", ["robot_2"], _DYNAMIC, geometry=view.geometry)
    aisle = view.geometry.model_copy(update={"rear_room_band": "aisle"})
    assert backup == derive_backup_distance(frame, "robot_1", ["robot_2"], _DYNAMIC, geometry=aisle)
    assert backup.value_m == pytest.approx(1.2)


# ---- lane-scoped crossing order and escort (the last link of the chain) ----
#
# Past the clearance fix the echo replay grounded 216/216 yields but dropped
# every escort: the crossing order still held the off-lane N-arm queue
# (robots 2-4), whose escort headings cannot be derived (`goal_behind` /
# `goal_reached`), and `apply_escort_headings` strips the whole yield's
# escort when any passer's heading fails -- robot_5's included. Under a lane
# view the order now holds only the lane conflict: the lane partner plus any
# robot inside the swept corridor (0.38 m either side of the retreat line).


def _ep1_five() -> dict[str, Any]:
    geometry, obstacles, params = _shipped()
    return _ground(
        _decision(_FIVE, "robot_1"),
        _frame(_EP1_SCENE, _EP1_GOALS),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )


def test_ep1_echo_order_holds_only_the_lane_conflict():
    command = _ep1_five()
    yield_parameters = command["actions"][0]["parameters"]
    assert yield_parameters["crossing_order"] == ["robot_5"]
    # One passer: no per-passer lists for an off-lane robot to sit in.
    assert "crossing_clear_m" not in yield_parameters
    assert "crossing_escort_m" not in yield_parameters
    assert "order=lane_scoped:robot_2,robot_3,robot_4" in command["degradations"]


def test_ep1_off_lane_robots_still_hold_unlinked():
    command = _ep1_five()
    waits = {
        a["robot_id"]: a["parameters"]
        for a in command["actions"]
        if a["action"] == "temporary_wait"
    }
    assert set(waits) == {"robot_2", "robot_3", "robot_4", "robot_5"}
    assert waits["robot_5"]["linked_position"] == 0
    for robot_id in ("robot_2", "robot_3", "robot_4"):
        assert "linked_position" not in waits[robot_id]
        assert waits[robot_id]["requested_strategy"] == "yield"
        assert waits[robot_id]["duration_sec"] == waits["robot_5"]["duration_sec"]


def test_ep1_echo_keeps_the_lane_passer_escort():
    command = _ep1_five()
    assert not any(t.startswith("grounding=escort_off") for t in command["degradations"])
    parameters = command["actions"][0]["parameters"]
    # robot_5 at x=2.3066 to the park at x=0.556 plus the 0.65 m passer
    # clearance; its goal (0, -1.55) lies west, the direction the escort
    # distance was measured in, so it drives at pi.
    assert parameters["passer_robot_id"] == "robot_5"
    assert parameters["passer_escort_distance_m"] == pytest.approx(2.4, abs=1e-3)
    assert parameters["passer_escort_heading_rad"] == pytest.approx(math.pi)
    assert parameters["passer_escort_reference_yaw_rad"] == pytest.approx(3.1172)


def test_ep1_echo_yield_equals_the_lane_pair_grounding():
    # The two-robot grounding (escort kept on all 216 replay scenes) is the
    # reference: the three off-lane robots change nothing about the yield.
    geometry, obstacles, params = _shipped()
    pair = _ground(
        _decision(["robot_1", "robot_5"], "robot_1"),
        _frame(_EP1_SCENE, _EP1_GOALS),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert _ep1_five()["actions"][0] == pair["actions"][0]


def test_ep1_dispatched_chain_references_only_lane_robots():
    command = _ep1_five()
    (yield_action,) = [a for a in command["actions"] if a["action"] == "yield"]
    parameters = yield_action["parameters"]
    lane = {"robot_1", "robot_5"}
    # M4 reads the chain through `plan_crossing`; the safety monitor pairs
    # the yielder with exactly those passers.
    assert [p.robot_id for p in plan_crossing(parameters)] == ["robot_5"]
    assert crossing_order_from_parameters("yield", parameters) == ("robot_5",)
    linked = {
        a["robot_id"]: a["parameters"]["linked_position"]
        for a in command["actions"]
        if "linked_position" in (a.get("parameters") or {})
    }
    assert linked == {"robot_5": 0}
    assert set(parameters["crossing_order"]) <= lane
    # M5's absent-robot filter keeps the chain as it is when an off-lane
    # robot drops out of the snapshot.
    filtered = filter_command_robot_ids(command, {"robot_1", "robot_2", "robot_4", "robot_5"})
    (filtered_yield,) = [a for a in filtered["actions"] if a["action"] == "yield"]
    assert filtered_yield == yield_action
    assert "robot_3" not in {a["robot_id"] for a in filtered["actions"]}


def test_ep1_default_plan_waits_the_off_lane_robots_and_matches_dispatch():
    geometry, obstacles, params = _shipped()
    decision = _decision(_FIVE, "robot_1")
    frame = _frame(_EP1_SCENE, _EP1_GOALS)
    view = resolve_grounding_view(decision, frame, geometry, params)
    plan = verify_and_repair_plan(
        view.decision,
        frame,
        geometry=view.geometry,
        static_obstacles=obstacles,
        yield_feasibility_mode="swap",
        grounding_params=params,
    )
    assert {leg.robot_id: leg.action for leg in plan.legs} == {
        "robot_1": "yield",
        "robot_5": "cross",
        "robot_2": "wait",
        "robot_3": "wait",
        "robot_4": "wait",
    }
    assert plan_matches_dispatch(plan.legs, _ep1_five(), _FIVE)


@pytest.mark.parametrize(
    ("pose", "kept"),
    [
        ((2.8, 0.0, math.pi), True),  # on the lane, behind the partner
        ((0.3, 0.38, 0.0), True),  # 0.332 m beside the lane: inside the corridor
        ((0.3, 0.448, 0.0), False),  # 0.4 m beside it: outside
    ],
)
def test_lane_scope_keeps_robots_inside_the_swept_corridor(pose: Pose, kept: bool):
    geometry, obstacles, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": pose}
    frame = _frame(poses, _EP1_GOALS)
    view = resolve_grounding_view(_decision(_FIVE, "robot_1"), frame, geometry, params)
    roles = resolve_yield_roles(
        view.decision,
        frame,
        geometry=view.geometry,
        static_obstacles=obstacles,
        yield_feasibility_mode="swap",
        params=params,
    )
    assert roles.crossing_order[0] == "robot_5"
    assert ("robot_3" in roles.crossing_order) is kept
    assert ("robot_3" in roles.off_lane) is not kept
    assert set(roles.crossing_order) | set(roles.off_lane) == set(_FIVE) - {"robot_1"}


# ep1 request f0989c8a219241d78f8a9fb4688fd716 (and two more): robot_3 dwells
# at the W node, on robot_1's lane axis (0.25 m beside it) but 4.17 m behind
# it. The clearance's reach is backup_band_m[1] + 1.7 = 3.7 m.
_W_NODE_DWELL: Pose = (-2.234, 0.299, 0.245)


def test_lane_scope_drops_a_corridor_robot_beyond_the_clearance_reach():
    geometry, obstacles, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": _W_NODE_DWELL}
    goals = {**_EP1_GOALS, "robot_3": (-2.3, 0.35)}
    command = _ground(
        _decision(_FIVE, "robot_1"),
        _frame(poses, goals),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert "order=lane_scoped:robot_2,robot_3,robot_4" in command["degradations"]
    assert not any(t.startswith("grounding=escort_off") for t in command["degradations"])
    pair = _ground(
        _decision(["robot_1", "robot_5"], "robot_1"),
        _frame(poses, goals),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert command["actions"][0] == pair["actions"][0]


def test_lane_scope_bound_is_off_without_params():
    # The lateral rule alone keeps the dwelling robot (no reach to bound by).
    geometry, obstacles, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": _W_NODE_DWELL}
    frame = _frame(poses, {**_EP1_GOALS, "robot_3": (-2.3, 0.35)})
    view = resolve_grounding_view(_decision(_FIVE, "robot_1"), frame, geometry, params)
    roles = resolve_yield_roles(view.decision, frame, geometry=view.geometry)
    assert roles.crossing_order == ["robot_5", "robot_3"]


def test_a_corridor_robot_within_the_clearance_reach_stays_and_binds():
    # 3.0 m behind robot_1 on its lane: its clearance interval (1.3, 4.7)
    # covers every backup robot_5 allows (>= 1.331 m), so it is in the
    # conflict, stays in the order, and the backup is refused.
    geometry, obstacles, params = _shipped()
    poses = {**_EP1_SCENE, "robot_3": (1.9373 - 3.0, 0.05, 0.0)}
    command = _ground(
        _decision(_FIVE, "robot_1"),
        _frame(poses, _EP1_GOALS),
        geometry=geometry,
        params=params,
        obstacles=obstacles,
    )
    assert "order=lane_scoped:robot_2,robot_4" in command["degradations"]
    assert (
        "yield=infeasible:no backup distance in band [0.5, 2.0] m satisfies clearance 1.7 m"
        in command["degradations"]
    )


def test_crossing_view_order_is_not_lane_scoped():
    # A crossing view has no lane pair: its perpendicular passers are real
    # passers, however far they sit from the retreat line.
    poses = {
        "robot_1": (-0.45, 0.35, 0.0),
        "robot_2": (0.05, -0.45, math.pi / 2),
        "robot_3": (0.05, -1.2, math.pi / 2),
    }
    frame = _frame(poses, {"robot_2": (0.0, 1.55), "robot_3": (0.0, 1.55)})
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_2", "robot_3"], "robot_1"), frame, _S1, _DYNAMIC
    )
    assert view.geometry is not None and view.geometry.lane_robots is None
    roles = resolve_yield_roles(view.decision, frame, geometry=view.geometry)
    assert roles.crossing_order == ["robot_2", "robot_3"]
    assert roles.off_lane == []
    assert not any(t.startswith("order=lane_scoped") for t in roles.degradations)


def test_empty_off_lane_stays_out_of_the_roles_dump():
    roles = resolve_yield_roles(_decision(["robot_1", "robot_2"], "robot_1"), _frame(_W_LANE))
    assert "off_lane" not in roles.model_dump(mode="json")


# ---- the PROPOSED box margin of the candidate sweep ----


def test_s1_file_declares_the_proposed_box_margin():
    _, _, params = _shipped()
    assert params.retreat_box_margin_m == pytest.approx(0.05)


def test_zero_margin_reproduces_the_unmargined_park():
    # The a8e9a51 sweep (no margin): the clearance minimum survives as is.
    geometry, obstacles, params = _shipped()
    command = _ground(
        _decision(["robot_1", "robot_5"], "robot_1"),
        _frame(_EP1_SCENE, _EP1_GOALS),
        geometry=geometry,
        params=params.model_copy(update={"retreat_box_margin_m": 0.0}),
        obstacles=obstacles,
    )
    parameters = command["actions"][0]["parameters"]
    assert parameters["backup_distance_m"] == pytest.approx(1.331)
    assert parameters["retreat_x_m"] == pytest.approx(0.606, abs=1e-3)
    assert not any(t.startswith("retreat=deepened") for t in command["degradations"])


def test_margin_deepens_the_ep1_backup_and_tags_it():
    command = _ep1_five()
    assert "retreat=deepened:1.331->1.381" in command["degradations"]


def test_a_margin_met_at_the_clearance_minimum_does_not_deepen():
    # W lane: nothing within reach of the 1.3 m backup or either sidestep.
    command = _ground(
        _decision(["robot_1", "robot_2"], "robot_1"),
        _frame(_W_LANE),
        params=_DYNAMIC.model_copy(update={"retreat_box_margin_m": 0.05}),
    )
    assert command["actions"][0]["parameters"]["backup_distance_m"] == pytest.approx(1.3)
    assert not any(t.startswith("retreat=deepened") for t in command["degradations"])


def test_margin_vetoes_a_body_within_it_of_a_box():
    # The unmargined clearance-minimum park (x=0.606) sits 4 mm from the gate
    # jaw's west face: inside a 0.05 m margin, so no candidate survives at
    # that depth.
    geometry, obstacles, params = _shipped()
    frame = _frame(_EP1_SCENE, _EP1_GOALS)
    view = resolve_grounding_view(
        _decision(["robot_1", "robot_5"], "robot_1"), frame, geometry, params
    )
    shallow = generate_retreat_candidates(
        frame,
        "robot_1",
        1.331,
        params,
        geometry=view.geometry,
        passer_id="robot_5",
        static_obstacles=obstacles,
    )
    assert shallow == []
    deep = generate_retreat_candidates(
        frame,
        "robot_1",
        1.381,
        params,
        geometry=view.geometry,
        passer_id="robot_5",
        static_obstacles=obstacles,
    )
    assert deep


def test_margin_stays_out_of_the_params_dump_unless_set_under_dynamic_arms():
    assert "retreat_box_margin_m" not in GroundingParams(mode="derived").model_dump()
    assert "retreat_box_margin_m" not in _DYNAMIC.model_dump()
    off = GroundingParams(mode="derived", retreat_box_margin_m=0.05)
    assert "retreat_box_margin_m" not in off.model_dump()
    on = _DYNAMIC.model_copy(update={"retreat_box_margin_m": 0.05})
    assert on.model_dump()["retreat_box_margin_m"] == 0.05
    assert GroundingParams(**on.model_dump()) == on
