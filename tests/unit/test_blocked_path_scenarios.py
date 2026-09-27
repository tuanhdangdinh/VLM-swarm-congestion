"""Tests for the T3a blocker-kind pair `blocked_path_object` / `blocked_path_transient`."""
from __future__ import annotations

import difflib
import json
import struct
import sys
import typing
from collections import deque
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from isaac.scripts.generate_warehouse_map import build_occupancy_grid, load_scenario
from isaac.vgu_sim.config import (
    BUILTIN_TIMED_OBSTACLE_ASSETS,
    BlockerOracleConfig,
    CameraConfig,
    OracleBlockerKind,
    OracleStrategy,
    WarehouseConfig,
)
from reasoning.vlm.models import BlockerKind, CongestionDecision

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = REPO_ROOT / "isaac/config/scenarios"
OBJECT_PATH = SCENARIO_DIR / "blocked_path_object.yaml"
TRANSIENT_PATH = SCENARIO_DIR / "blocked_path_transient.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
RAG_YAML = REPO_ROOT / "config/rag.yaml"
MOCK_DIR = REPO_ROOT / "config/mock_decisions"
ROBOT_DIR = REPO_ROOT / "isaac/assets/robots/turtlebot3_burger"
RESOLUTION_M = 0.05
# TurtleBot3 Burger width across the tires, and Nav2's inscribed radius (the
# footprint's smallest half-extent, nav2_params.yaml [[+-0.07, +-0.09]]).
ROBOT_WIDTH_M = 0.18
INSCRIBED_RADIUS_M = 0.07
# collision_monitor forward_stop polygon half-width (nav2_params.yaml).
STOP_BOX_HALF_WIDTH_M = 0.12
# Transit speed and the departure range seen on the VM: 10.6 s in the normal_flow
# T0 run 20260927_111348, 14.5 s in the T3c v2 smoke 20260927_125419.
TRANSIT_MPS = 0.15
DEPARTURES_SIM_SEC = (10.6, 14.5)
M5_FIRST_SCENE_SIM_SEC = 12.0
# T3c v2 smoke: robot stopped ~0.9 s after the obstacle spawned; VM real-time
# factor ~0.38 turns M5's wall-clock stall threshold into sim seconds.
STOP_DELAY_SIM_SEC = 1.0
REAL_TIME_FACTOR = 0.38
# command_grounder's temporary_wait duration_sec (a sim-time command_bus timer).
TEMPORARY_WAIT_HOLD_SIM_SEC = 8.0
# Replanning plus stale-costmap pause after the T3c v2 obstacle despawned
# (112 -> 138 s, "Failed to make progress"), less its own travel.
POST_DESPAWN_PAUSE_SIM_SEC = 22.0


def _both():
    return load_scenario(OBJECT_PATH), load_scenario(TRANSIENT_PATH)


def _blocker(scenario):
    (blocker,) = scenario.timed_obstacles
    return blocker


def _robot(scenario, robot_id: str):
    return next(r for r in scenario.robots if r.robot_id == robot_id)


def _x_at(robot, sim_sec: float, departure: float) -> float:
    direction = np.sign(robot.goal.x - robot.spawn.x)
    return robot.spawn.x + direction * TRANSIT_MPS * max(0.0, sim_sec - departure)


def _first_trigger_sim_sec(spawn_at: float) -> float:
    stall_wall = yaml.safe_load(ORCHESTRATOR_YAML.read_text())["stall_threshold_sec"]
    return spawn_at + STOP_DELAY_SIM_SEC + stall_wall * REAL_TIME_FACTOR


def _stl_triangles(path: Path) -> np.ndarray:
    data = path.read_bytes()
    (count,) = struct.unpack("<I", data[80:84])
    record = np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")])
    return np.frombuffer(data[84 : 84 + count * 50], dtype=record)["v"].reshape(-1, 3, 3)


def _slice_y_intervals(triangles: np.ndarray, z: float) -> list[tuple[float, float]]:
    """Y extents of each triangle's intersection segment with the plane `z`."""
    intervals = []
    for tri in triangles:
        ys = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            za, zb = tri[a, 2], tri[b, 2]
            if (za - z) * (zb - z) <= 0 and za != zb:
                t = (z - za) / (zb - za)
                ys.append(tri[a, 1] + t * (tri[b, 1] - tri[a, 1]))
        if ys:
            intervals.append((min(ys), max(ys)))
    return intervals


def _slice_coverage(intervals, half_width: float, bin_m: float = 0.005) -> float:
    centers = np.arange(-half_width + bin_m / 2, half_width, bin_m)
    covered = [any(lo - bin_m / 2 <= c <= hi + bin_m / 2 for lo, hi in intervals) for c in centers]
    return float(np.mean(covered))


def _urdf_scan_height_m() -> float:
    # base_joint lifts base_link 0.010 m; scan_joint puts base_scan 0.172 above it.
    text = (ROBOT_DIR / "turtlebot3_burger.urdf").read_text()
    assert '<origin xyz="0.0 0.0 0.010" rpy="0 0 0"/>' in text
    assert '<origin xyz="-0.032 0 0.172" rpy="0 0 0"/>' in text
    return 0.010 + 0.172


def _plate_half_width_m(scale: float) -> float:
    """Half-width of the burger body the lidar plane cuts at `scale` (meters, scaled)."""
    base = _stl_triangles(ROBOT_DIR / "meshes/burger_base.stl") / 1000.0
    local_z = _urdf_scan_height_m() / scale - 0.010
    intervals = _slice_y_intervals(base, local_z)
    return scale * max(max(abs(lo), abs(hi)) for lo, hi in intervals)


def _lds_half_width_m() -> float:
    lds = _stl_triangles(ROBOT_DIR / "meshes/lds.stl") / 1000.0
    return max(max(abs(lo), abs(hi)) for lo, hi in _slice_y_intervals(lds, 0.0))


def _cell(x: float, y: float, cfg: WarehouseConfig) -> tuple[int, int]:
    return (
        int(np.floor((cfg.depth_m / 2 - y) / RESOLUTION_M)),
        int(np.floor((x + cfg.width_m / 2) / RESOLUTION_M)),
    )


def _scenario_grid(scenario):
    grid, _ = build_occupancy_grid(
        WarehouseConfig(),
        obstacles=[],
        resolution_m=RESOLUTION_M,
        aisle_barrier=scenario.aisle_barrier,
        static_obstacles=scenario.static_obstacles,
    )
    return grid


def _navfn_path_exists(scenario, blocker_half_width_m: float | None) -> bool:
    """Whether NavFn finds robot_1 a path on the static map plus the blocker's lidar face.

    Model of the global costmap: static-map lethal cells plus the cells the
    lidar marks on the blocker's west face (a `2 * blocker_half_width_m` wide
    cross-section), inflated to cost 253 within the inscribed radius, which
    NavFn treats as obstacle. Walls the lidar also marks are left out, so this
    is the optimistic (most plannable) case.
    """
    cfg = WarehouseConfig()
    lethal = _scenario_grid(scenario) == 0
    if blocker_half_width_m is not None:
        blocker = _blocker(scenario)
        face_x = blocker.pose.x - blocker.size.x_m / 2
        for y in np.linspace(-blocker_half_width_m, blocker_half_width_m, 80):
            lethal[_cell(face_x, blocker.pose.y + y, cfg)] = True
    reach = int(INSCRIBED_RADIUS_M / RESOLUTION_M) + 1
    blocked = lethal.copy()
    for dr in range(-reach, reach + 1):
        for dc in range(-reach, reach + 1):
            if (dr * dr + dc * dc) ** 0.5 * RESOLUTION_M <= INSCRIBED_RADIUS_M and (dr or dc):
                blocked |= np.roll(np.roll(lethal, dr, axis=0), dc, axis=1)
    r1 = _robot(scenario, "robot_1")
    start = _cell(r1.spawn.x, r1.spawn.y + 1e-6, cfg)
    goal = _cell(r1.goal.x, r1.goal.y + 1e-6, cfg)
    seen = {start}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        if (r, c) == goal:
            return True
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if (nr, nc) not in seen and not blocked[nr, nc]:
                seen.add((nr, nc))
                queue.append((nr, nc))
    return False


def test_pair_yamls_load_as_blocked_path_family():
    names = ("blocked_path_object", "blocked_path_transient")
    for scenario, name in zip(_both(), names, strict=True):
        assert scenario.name == name
        assert scenario.family == "blocked_path"
        assert [r.robot_id for r in scenario.robots] == ["robot_1", "robot_2"]


def test_pair_differs_only_in_name_blocker_entity_and_oracle():
    obj, tra = (yaml.safe_load(p.read_text()) for p in (OBJECT_PATH, TRANSIENT_PATH))
    for key in ("name", "timed_obstacles", "oracle"):
        obj.pop(key), tra.pop(key)

    assert obj == tra


def test_pair_blocker_entries_differ_only_in_asset_and_removal():
    obj, tra = (_blocker(s).model_dump() for s in _both())
    for key in ("asset", "remove_at_sec"):
        obj.pop(key), tra.pop(key)

    assert obj == tra


def test_pair_text_diff_is_confined_to_name_blocker_and_oracle_blocks():
    def block_of(lines: list[str], index: int) -> str:
        for line in reversed(lines[: index + 1]):
            if line and not line.startswith((" ", "#")):
                return line.split(":")[0]
        return ""

    obj = OBJECT_PATH.read_text().splitlines()
    tra = TRANSIENT_PATH.read_text().splitlines()
    touched = set()
    matcher = difflib.SequenceMatcher(a=obj, b=tra, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        touched |= {block_of(obj, i) for i in range(i1, max(i2, i1 + 1))}
        touched |= {block_of(tra, j) for j in range(j1, max(j2, j1 + 1))}

    assert touched == {"name", "timed_obstacles", "oracle"}


def test_object_blocker_is_a_static_box_that_never_despawns():
    blocker = _blocker(load_scenario(OBJECT_PATH))

    assert blocker.asset == "static_box"
    assert blocker.remove_at_sec is None


def test_transient_blocker_is_the_marker_less_robot_visual_and_despawns():
    blocker = _blocker(load_scenario(TRANSIENT_PATH))

    assert blocker.asset == "robot_visual_no_marker"
    assert blocker.remove_at_sec is not None


def test_object_oracle_is_object_reroute_agreeing_with_classical():
    oracle = load_scenario(OBJECT_PATH).oracle

    assert isinstance(oracle, BlockerOracleConfig)
    assert (oracle.correct_blocker_kind, oracle.correct_strategy) == ("object", "reroute")
    assert oracle.contrasts_classical is False


def test_transient_oracle_is_transient_wait_diverging_from_classical():
    oracle = load_scenario(TRANSIENT_PATH).oracle

    assert isinstance(oracle, BlockerOracleConfig)
    assert (oracle.correct_blocker_kind, oracle.correct_strategy) == (
        "transient",
        "temporary_wait",
    )
    assert oracle.contrasts_classical is True


def test_pair_classical_answer_is_the_forced_object_reroute():
    # Arm B's blocked_path rule has no image: blocker_kind is always object.
    for scenario in _both():
        assert (scenario.oracle.classical_blocker_kind, scenario.oracle.classical_strategy) == (
            "object",
            "reroute",
        )


def test_oracle_literals_match_the_decision_contract():
    strategy = CongestionDecision.model_fields["strategy"].annotation

    assert typing.get_args(OracleBlockerKind) == typing.get_args(BlockerKind)
    assert typing.get_args(OracleStrategy) == typing.get_args(strategy)


def test_blocker_oracle_rejects_a_strategy_other_than_the_kind_default():
    with pytest.raises(ValidationError, match="temporary_wait"):
        BlockerOracleConfig(
            correct_blocker_kind="transient",
            correct_strategy="reroute",
            classical_blocker_kind="object",
            classical_strategy="reroute",
            rationale="x",
        )


def test_blocker_oracle_rejects_robot_kind_without_a_default():
    with pytest.raises(ValidationError, match="no default"):
        BlockerOracleConfig(
            correct_blocker_kind="robot",
            correct_strategy="yield",
            classical_blocker_kind="object",
            classical_strategy="reroute",
            rationale="x",
        )


def test_pair_blocker_assets_are_built_ins():
    # A misspelt built-in name is a valid label that authors the legacy red box.
    for scenario in _both():
        assert _blocker(scenario).asset in BUILTIN_TIMED_OBSTACLE_ASSETS


def test_pair_expects_an_anomaly_on_robot_1_only():
    for scenario in _both():
        assert scenario.expected_conflict.type == "anomaly"
        assert scenario.expected_conflict.involved_robots == ("robot_1",)


def test_pair_spawns_and_goals_inside_camera_roi_with_margin():
    camera = CameraConfig()
    half_x, half_y = camera.roi_width_m / 2 - 0.5, camera.roi_depth_m / 2 - 0.5

    for robot in load_scenario(OBJECT_PATH).robots:
        for x, y in ((robot.spawn.x, robot.spawn.y), (robot.goal.x, robot.goal.y)):
            assert abs(x) <= half_x + 1e-9 and abs(y) <= half_y + 1e-9, (robot.robot_id, x, y)


def test_blocker_sits_on_robot_1_lane_between_spawn_and_goal():
    scenario = load_scenario(OBJECT_PATH)
    blocker, r1 = _blocker(scenario), _robot(scenario, "robot_1")

    half_width = blocker.size.y_m / 2
    assert blocker.pose.y - half_width <= r1.spawn.y <= blocker.pose.y + half_width
    assert r1.spawn.x < blocker.pose.x - blocker.size.x_m / 2
    assert blocker.pose.x + blocker.size.x_m / 2 < r1.goal.x


def test_blocker_footprint_lies_inside_the_corridor():
    scenario = load_scenario(OBJECT_PATH)
    blocker, barrier = _blocker(scenario), scenario.aisle_barrier
    half_length = barrier.length_m / 2

    assert barrier.center_x_m - half_length < blocker.pose.x - blocker.size.x_m / 2
    assert blocker.pose.x + blocker.size.x_m / 2 < barrier.center_x_m + half_length


def test_blocker_leaves_no_physical_gap_for_a_robot():
    scenario = load_scenario(OBJECT_PATH)
    blocker = _blocker(scenario)
    gap = scenario.aisle_barrier.effective_width_m / 2 - blocker.size.y_m / 2

    assert gap < ROBOT_WIDTH_M


def test_empty_corridor_clears_the_collision_monitor_stop_box():
    scenario = load_scenario(OBJECT_PATH)

    assert scenario.aisle_barrier.effective_width_m / 2 - STOP_BOX_HALF_WIDTH_M >= 0.12


def test_blocker_size_matches_scaled_robot_visual_footprint():
    from isaac.vgu_sim.config import ROBOT_VISUAL_NO_MARKER_SCALE as scale

    base = _stl_triangles(ROBOT_DIR / "meshes/burger_base.stl").reshape(-1, 3) / 1000.0
    # URDF visual placement: the base mesh spans the body's length, the tires
    # sit at y +-0.08 (0.0182 m wide), and the LDS top is at 0.191 m.
    length = base[:, 0].max() - base[:, 0].min()
    width = 2 * (0.080 + 0.0091)
    height = 0.191
    size = _blocker(load_scenario(TRANSIENT_PATH)).size

    assert size.x_m == pytest.approx(scale * length, abs=0.01)
    assert size.y_m == pytest.approx(scale * width, abs=0.01)
    assert size.z_m == pytest.approx(scale * height, abs=0.01)


def test_lidar_plane_cuts_the_scaled_robot_mid_plate_with_margin():
    from isaac.vgu_sim.config import ROBOT_VISUAL_NO_MARKER_SCALE as scale

    base = _stl_triangles(ROBOT_DIR / "meshes/burger_base.stl") / 1000.0
    scan = _urdf_scan_height_m()
    # +-7 mm of scaled height around the plane (tilt or settling of the scanner).
    for delta in (-0.007, 0.0, 0.007):
        local_z = (scan + delta) / scale - 0.010
        coverage = _slice_coverage(_slice_y_intervals(base, local_z), half_width=0.065)
        assert coverage >= 0.95, (delta, coverage)


def test_robot_2_parks_in_the_sealed_north_pocket():
    scenario = load_scenario(OBJECT_PATH)
    r2 = _robot(scenario, "robot_2")
    pocket_half = WarehouseConfig().nominal_aisle_width_m / 2
    barrier = scenario.aisle_barrier

    for x, y in ((r2.spawn.x, r2.spawn.y), (r2.goal.x, r2.goal.y)):
        assert abs(x) <= pocket_half - 0.25
        assert y >= pocket_half + 0.25
    # The barrier blocks close the pocket's mouth onto the aisle.
    assert barrier.center_x_m - barrier.length_m / 2 <= -pocket_half
    assert barrier.center_x_m + barrier.length_m / 2 >= pocket_half


def test_robot_2_is_beyond_classical_r_block_when_robot_1_stops():
    scenario = load_scenario(OBJECT_PATH)
    r1, r2 = _robot(scenario, "robot_1"), _robot(scenario, "robot_2")
    r_block = yaml.safe_load(RAG_YAML.read_text())["classical"]["r_block_m"]
    stop_t = _blocker(scenario).spawn_at_sec + STOP_DELAY_SIM_SEC

    for departure in DEPARTURES_SIM_SEC:
        x1 = _x_at(r1, stop_t, departure)
        nearest = min(np.hypot(x1 - p.x, r1.spawn.y - p.y) for p in (r2.spawn, r2.goal))
        assert nearest > r_block + 0.5, (departure, nearest)


def test_blocker_spawns_after_m5_startup():
    for scenario in _both():
        assert _blocker(scenario).spawn_at_sec > M5_FIRST_SCENE_SIM_SEC


def test_robot_1_stops_in_open_aisle_with_a_straight_run_into_the_corridor():
    scenario = load_scenario(OBJECT_PATH)
    r1, barrier = _robot(scenario, "robot_1"), scenario.aisle_barrier
    mouth = barrier.center_x_m - barrier.length_m / 2
    stop_t = _blocker(scenario).spawn_at_sec + STOP_DELAY_SIM_SEC

    for departure in DEPARTURES_SIM_SEC:
        x_stop = _x_at(r1, stop_t, departure)
        assert mouth - x_stop >= 0.4, (departure, x_stop)


def test_onset_window_spans_spawn_and_first_stall_trigger():
    for scenario in _both():
        start, end = scenario.expected_conflict.onset_window_sec
        spawn = _blocker(scenario).spawn_at_sec

        assert start == pytest.approx(spawn)
        assert start < _first_trigger_sim_sec(spawn) < end


def test_transient_window_outlasts_several_temporary_wait_holds():
    blocker = _blocker(load_scenario(TRANSIENT_PATH))
    after_first_analysis = blocker.remove_at_sec - _first_trigger_sim_sec(blocker.spawn_at_sec)

    assert after_first_analysis >= 4 * TEMPORARY_WAIT_HOLD_SIM_SEC


def test_transient_member_leaves_time_to_arrive_after_despawn():
    scenario = load_scenario(TRANSIENT_PATH)
    blocker, r1 = _blocker(scenario), _robot(scenario, "robot_1")
    stop_x = _x_at(r1, blocker.spawn_at_sec + STOP_DELAY_SIM_SEC, max(DEPARTURES_SIM_SEC))
    travel = (r1.goal.x - stop_x) / TRANSIT_MPS

    arrival = blocker.remove_at_sec + travel + POST_DESPAWN_PAUSE_SIM_SEC
    assert arrival + 30.0 <= scenario.duration_sec


def test_navfn_plans_through_the_empty_corridor():
    assert _navfn_path_exists(load_scenario(OBJECT_PATH), None)


def test_box_blocker_closes_the_corridor_for_navfn():
    scenario = load_scenario(OBJECT_PATH)

    assert not _navfn_path_exists(scenario, _blocker(scenario).size.y_m / 2)


def test_scaled_robot_visual_closes_the_corridor_for_navfn():
    from isaac.vgu_sim.config import ROBOT_VISUAL_NO_MARKER_SCALE as scale

    assert not _navfn_path_exists(load_scenario(TRANSIENT_PATH), _plate_half_width_m(scale))


def test_unscaled_robot_visual_would_leave_navfn_a_path():
    # Why the visual is scaled: at scale 1 the lidar plane only meets the 7 cm
    # LDS head, and NavFn routes round it -- no stall, no M5 trigger.
    assert _navfn_path_exists(load_scenario(TRANSIENT_PATH), _lds_half_width_m())


def test_pair_maps_are_identical_and_bake_the_corridor_not_the_blocker():
    cfg = WarehouseConfig()
    obj, tra = _both()
    grid = _scenario_grid(obj)
    blocker = _blocker(obj)

    assert np.array_equal(grid, _scenario_grid(tra))
    assert grid[_cell(blocker.pose.x, blocker.pose.y + 1e-6, cfg)] == 255
    assert grid[_cell(blocker.pose.x, 0.4, cfg)] == 0
    assert grid[_cell(blocker.pose.x, -0.4, cfg)] == 0


def test_robot_lanes_are_free_in_generated_map():
    cfg = WarehouseConfig()
    scenario = load_scenario(OBJECT_PATH)
    grid = _scenario_grid(scenario)
    r1, r2 = _robot(scenario, "robot_1"), _robot(scenario, "robot_2")

    for x in np.arange(r1.spawn.x, r1.goal.x + 1e-9, RESOLUTION_M):
        assert grid[_cell(x, r1.spawn.y + 1e-6, cfg)] == 255, x
    for y in np.arange(r2.spawn.y, r2.goal.y + 1e-9, RESOLUTION_M):
        assert grid[_cell(r2.spawn.x + 1e-6, y, cfg)] == 255, y


@pytest.mark.parametrize("path", [OBJECT_PATH, TRANSIENT_PATH])
def test_committed_map_matches_scenario_yaml(path):
    scenario = load_scenario(path)
    map_yaml = MAPS_DIR / f"warehouse_map_{scenario.name}.yaml"
    data = yaml.safe_load(map_yaml.read_text())
    committed = np.flipud(np.array(Image.open(map_yaml.parent / data["image"])))

    assert data["image"] == f"warehouse_map_{scenario.name}.pgm"
    assert data["resolution"] == pytest.approx(RESOLUTION_M)
    assert data["origin"][:2] == [-6.0, -4.0]
    assert np.array_equal(committed, _scenario_grid(scenario))


@pytest.mark.parametrize(
    ("mock_file", "path"),
    [
        ("blocked_path_reroute_once.json", OBJECT_PATH),
        ("blocked_path_wait_once.json", TRANSIENT_PATH),
    ],
)
def test_mock_decision_forces_the_oracle_answer_once(mock_file, path):
    first, *rest = json.loads((MOCK_DIR / mock_file).read_text())
    decision = CongestionDecision.model_validate(first)
    oracle = load_scenario(path).oracle

    assert (decision.blocker_kind, decision.strategy) == (
        oracle.correct_blocker_kind,
        oracle.correct_strategy,
    )
    assert decision.involved_robots == ["robot_1"]
    assert [CongestionDecision.model_validate(d).strategy for d in rest] == ["none"]


def test_orchestrator_goal_table_lists_the_pair_goals():
    text = ORCHESTRATOR_YAML.read_text()

    assert "blocked_path_object / blocked_path_transient" in text
    assert "robot_1\n#     [2.5, 0.0], robot_2 [0.0, 1.75]" in text
