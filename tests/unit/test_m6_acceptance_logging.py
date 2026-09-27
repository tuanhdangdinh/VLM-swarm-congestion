import json
import math

import pytest

from isaac.vgu_sim import acceptance_logging
from isaac.vgu_sim.acceptance_logging import (
    AcceptanceLogger,
    RobotPoseTracker,
    RobotRuntimeState,
    build_acceptance_record,
    find_chassis_prim,
    planar_pose_from_transform,
    resolve_chassis_prim,
)
from isaac.vgu_sim.config import (
    ExpectedConflictConfig,
    Goal2D,
    Pose2D,
    RobotScenarioConfig,
    ScenarioConfig,
    ScenarioRuntimeOverrides,
)


def _head_on_scenario() -> ScenarioConfig:
    return ScenarioConfig(
        schema_version=1,
        name="head_on_deadlock",
        seed=42,
        duration_sec=45.0,
        robots=(
            RobotScenarioConfig(
                robot_id="robot_1",
                marker_id=1,
                spawn=Pose2D(x=-3.0, y=0.0, yaw_rad=0.0),
                goal=Goal2D(x=3.0, y=0.0),
                initial_task="cross_narrow_aisle",
            ),
            RobotScenarioConfig(
                robot_id="robot_2",
                marker_id=2,
                spawn=Pose2D(x=3.0, y=0.0, yaw_rad=3.141592653589793),
                goal=Goal2D(x=-3.0, y=0.0),
                initial_task="cross_narrow_aisle",
            ),
        ),
        timed_obstacles=(),
        expected_conflict=ExpectedConflictConfig(
            type="deadlock",
            involved_robots=("robot_1", "robot_2"),
            onset_window_sec=(8.0, 25.0),
            min_duration_sec=2.0,
        ),
        runtime=ScenarioRuntimeOverrides(),
    )


def test_build_head_on_record_marks_conflict_active_when_robots_are_close_and_stopped():
    scenario = _head_on_scenario()
    states = {
        "robot_1": RobotRuntimeState(
            robot_id="robot_1",
            x=-0.2,
            y=0.0,
            theta=0.0,
            speed_mps=0.005,
        ),
        "robot_2": RobotRuntimeState(
            robot_id="robot_2",
            x=0.2,
            y=0.0,
            theta=3.14159,
            speed_mps=0.005,
        ),
    }

    record = build_acceptance_record(8.25, scenario, states)

    assert record["sim_time_sec"] == 8.25
    assert record["conflict_active"] is True
    assert record["conflict_type"] == "deadlock"
    assert record["involved_robots"] == ["robot_1", "robot_2"]
    assert record["min_pairwise_distance_m"] == 0.4
    assert record["robot_static_contacts"] == []
    assert record["robot_robot_contacts"] == []
    assert record["robots"]["robot_1"]["distance_to_goal_m"] == 3.2


def test_build_record_marks_conflict_for_head_on_family_variant():
    scenario = ScenarioConfig.model_validate(
        {
            **_head_on_scenario().model_dump(mode="json"),
            "name": "head_on_asymmetric_w0p2_eopen_o0",
            "family": "head_on",
        }
    )
    states = {
        "robot_1": RobotRuntimeState(
            robot_id="robot_1",
            x=-0.2,
            y=0.0,
            theta=0.0,
            speed_mps=0.005,
        ),
        "robot_2": RobotRuntimeState(
            robot_id="robot_2",
            x=0.2,
            y=0.0,
            theta=3.14159,
            speed_mps=0.005,
        ),
    }

    record = build_acceptance_record(8.25, scenario, states)

    assert record["conflict_active"] is True


def test_acceptance_logger_writes_jsonl_only_on_10hz_ticks(tmp_path):
    scenario = _head_on_scenario()
    path = tmp_path / "ground_truth.jsonl"
    states = {
        "robot_1": RobotRuntimeState(
            robot_id="robot_1",
            x=-0.2,
            y=0.0,
            theta=0.0,
            speed_mps=0.005,
        ),
        "robot_2": RobotRuntimeState(
            robot_id="robot_2",
            x=0.2,
            y=0.0,
            theta=3.14159,
            speed_mps=0.005,
        ),
    }

    with path.open("w", encoding="utf-8") as handle:
        logger = AcceptanceLogger(handle, scenario, log_hz=10.0)
        logger.maybe_write(0.00, states)
        logger.maybe_write(0.0167, states)
        logger.maybe_write(0.1000, states)

    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["sim_time_sec"] for r in records] == [0.0, 0.1]


def test_pose_tracker_computes_speed_from_previous_sample():
    tracker = RobotPoseTracker()
    first = tracker.update_from_positions(
        sim_time_sec=1.0,
        positions={"robot_1": (0.0, 0.0, 0.0)},
    )
    second = tracker.update_from_positions(
        sim_time_sec=1.5,
        positions={"robot_1": (0.1, 0.0, 0.0)},
    )

    assert first["robot_1"].speed_mps == 0.0
    assert second["robot_1"].speed_mps == 0.2


_ARTICULATION_API = object()
"""Stand-in for `UsdPhysics.ArticulationRootAPI`, which pxr supplies at runtime."""


class _FakePrim:
    """Duck-type of the `Usd.Prim` surface the chassis resolver relies on."""

    def __init__(self, path, apis=(), children=(), valid=True):
        self._path = path
        self._apis = list(apis)
        self._children = list(children)
        self._valid = valid

    def GetName(self):
        return self._path.rsplit("/", 1)[-1]

    def GetPath(self):
        return self._path

    def GetChildren(self):
        return list(self._children)

    def HasAPI(self, api):
        return any(api is applied for applied in self._apis)

    def IsValid(self):
        return self._valid

    def invalidate(self):
        self._valid = False


class _FakeStage:
    """Duck-type of `Usd.Stage.GetPrimAtPath` over a fixed prim table."""

    def __init__(self, prims):
        self._prims = {prim.GetPath(): prim for prim in prims}

    def GetPrimAtPath(self, path):
        return self._prims.get(str(path))


def _robot_stage(robot_id="robot_1", chassis_apis=(_ARTICULATION_API,)):
    """Build a fake stage shaped like the imported TurtleBot3 hierarchy."""
    base = f"/World/Robots/{robot_id}"
    chassis = _FakePrim(f"{base}/Geometry/base_footprint/base_link", apis=chassis_apis)
    footprint = _FakePrim(f"{base}/Geometry/base_footprint", children=[chassis])
    geometry = _FakePrim(f"{base}/Geometry", children=[footprint])
    root = _FakePrim(base, children=[geometry])
    return _FakeStage([root, geometry, footprint, chassis]), root, chassis


class _FakeRotation:
    def __init__(self, yaw_deg):
        self._yaw_deg = yaw_deg

    def Decompose(self, *_axes):
        return (self._yaw_deg, 0.0, 0.0)


class _FakeMatrix:
    """Duck-type of the `Gf.Matrix4d` surface `planar_pose_from_transform` reads."""

    def __init__(self, translation, yaw_deg):
        self._translation = translation
        self._yaw_deg = yaw_deg

    def ExtractTranslation(self):
        return self._translation

    def ExtractRotation(self):
        return _FakeRotation(self._yaw_deg)


@pytest.fixture(autouse=True)
def _clear_chassis_cache():
    acceptance_logging._CHASSIS_PATH_CACHE.clear()
    yield
    acceptance_logging._CHASSIS_PATH_CACHE.clear()


def test_find_chassis_prim_returns_articulation_root_not_robot_root():
    _stage, root, chassis = _robot_stage()

    assert find_chassis_prim(root, _ARTICULATION_API) is chassis


def test_find_chassis_prim_falls_back_to_base_link_name_without_articulation_api():
    _stage, root, chassis = _robot_stage(chassis_apis=())

    assert find_chassis_prim(root, _ARTICULATION_API) is chassis


def test_find_chassis_prim_returns_none_when_subtree_has_no_chassis():
    root = _FakePrim("/World/Robots/robot_9", children=[_FakePrim("/World/Robots/robot_9/Marker")])

    assert find_chassis_prim(root, _ARTICULATION_API) is None


def test_resolve_chassis_prim_returns_chassis_for_known_robot():
    stage, _root, chassis = _robot_stage()

    assert resolve_chassis_prim(stage, "robot_1", _ARTICULATION_API) is chassis


def test_resolve_chassis_prim_raises_value_error_naming_robot_without_chassis():
    root = _FakePrim("/World/Robots/robot_7")
    stage = _FakeStage([root])

    with pytest.raises(ValueError, match="robot_7"):
        resolve_chassis_prim(stage, "robot_7", _ARTICULATION_API)


def test_resolve_chassis_prim_raises_value_error_when_robot_root_missing():
    with pytest.raises(ValueError, match="robot_3"):
        resolve_chassis_prim(_FakeStage([]), "robot_3", _ARTICULATION_API)


def test_resolve_chassis_prim_reresolves_after_cached_prim_is_invalidated():
    stage, _root, chassis = _robot_stage()
    assert resolve_chassis_prim(stage, "robot_1", _ARTICULATION_API) is chassis

    # A stage reload between repetitions invalidates the cached prim; the resolver
    # must walk the reloaded subtree instead of returning the dead handle.
    chassis.invalidate()
    reloaded_stage, _reloaded_root, reloaded_chassis = _robot_stage()

    resolved = resolve_chassis_prim(reloaded_stage, "robot_1", _ARTICULATION_API)

    assert resolved is reloaded_chassis
    assert resolved is not chassis


def test_planar_pose_from_transform_returns_world_xy_and_yaw_radians():
    matrix = _FakeMatrix(translation=(-0.9412, 0.0173, 0.0046), yaw_deg=90.0)

    x, y, yaw_rad = planar_pose_from_transform(matrix)

    assert (round(x, 4), round(y, 4)) == (-0.9412, 0.0173)
    assert round(yaw_rad, 6) == round(math.pi / 2, 6)


def test_build_record_reports_no_conflict_for_normal_flow():
    scenario = ScenarioConfig.model_validate(
        {
            **_head_on_scenario().model_dump(mode="json"),
            "name": "normal_flow",
            "family": "normal_flow",
            "expected_conflict": None,
        }
    )
    states = {
        "robot_1": RobotRuntimeState(robot_id="robot_1", x=0.0, y=-0.35, theta=0.0, speed_mps=0.0),
        "robot_2": RobotRuntimeState(robot_id="robot_2", x=0.0, y=0.35, theta=3.14, speed_mps=0.0),
    }

    record = build_acceptance_record(1.0, scenario, states)

    assert record["conflict_active"] is False
    assert record["conflict_type"] is None
    assert record["involved_robots"] == []
    assert record["min_pairwise_distance_m"] == 0.7
