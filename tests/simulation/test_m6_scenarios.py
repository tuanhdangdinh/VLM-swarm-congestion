# tests/simulation/test_m6_scenarios.py
import json
import time
from pathlib import Path

import pytest


@pytest.mark.isaac_sim
def test_head_on_stage_validates():
    from isaac.vgu_sim.validation import validate_scenario_stage
    scenario = Path("isaac/scenarios/head_on_deadlock.usd")
    assert scenario.exists(), "Build head_on_deadlock.usd first (build_scenario.py)"
    validate_scenario_stage(scenario)


@pytest.mark.isaac_sim
def test_intersection_stage_validates():
    from isaac.vgu_sim.validation import validate_scenario_stage
    scenario = Path("isaac/scenarios/intersection_bottleneck.usd")
    assert scenario.exists()
    validate_scenario_stage(scenario)


@pytest.mark.isaac_sim
def test_dynamic_anomaly_stage_validates():
    from isaac.vgu_sim.validation import validate_scenario_stage
    scenario = Path("isaac/scenarios/dynamic_anomaly.usd")
    assert scenario.exists()
    validate_scenario_stage(scenario)


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_head_on_conflict_forms_and_collision_free(tmp_path):
    import yaml
    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path
    from isaac.vgu_sim.runner import run_simulation
    from tests.simulation.stop_stub import StopStubNode

    with open(scenario_config_path("head_on_deadlock")) as f:
        cfg = ScenarioConfig.model_validate(yaml.safe_load(f))

    run_cfg = ResolvedRunConfig(
        scenario_path=scenario_output_path("head_on_deadlock"),
        scenario=cfg,
        headless=True,
        repetitions=3,
        output_dir=tmp_path,
        topic_timeout_sec=20.0,
        ros_domain_id=None,
    )

    stub_node = StopStubNode.spin_in_thread(["robot_1", "robot_2"], speed_mps=0.10)
    results = run_simulation(run_cfg)

    assert all(r.completed for r in results), \
        f"Some repetitions failed: {[r.failure for r in results if not r.completed]}"

    for rep, result in enumerate(results):
        gt_path = tmp_path / f"head_on_deadlock-seed42-rep{rep:03d}" / "ground_truth.jsonl"
        _assert_conflict_formed(gt_path, min_duration_sec=2.0)
        _assert_no_static_contacts(gt_path)


def _assert_conflict_formed(gt_path: Path, min_duration_sec: float) -> None:
    records = [json.loads(line) for line in gt_path.read_text().splitlines() if line.strip()]
    dt = 0.1
    consecutive = 0.0
    for rec in records:
        if rec.get("conflict_active", False):
            consecutive += dt
            if consecutive >= min_duration_sec:
                return
        else:
            consecutive = 0.0
    pytest.fail(f"Conflict never active for {min_duration_sec}s in {gt_path}")


def _assert_no_static_contacts(gt_path: Path) -> None:
    for line in gt_path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        contacts = rec.get("robot_static_contacts", [])
        if contacts:
            pytest.fail(
                f"Robot-static contact at t={rec['sim_time_sec']}: {contacts}"
            )


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_ros_topics_published_at_correct_rates():
    import rclpy
    from collections import defaultdict
    from rclpy.node import Node
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, LaserScan

    counts: dict[str, int] = defaultdict(int)
    last_clock: list[float] = [0.0]

    rclpy.init(args=None)
    node = Node("_m6_rate_checker")

    node.create_subscription(Image, "/camera/image_raw",
                             lambda _: counts.__setitem__("rgb", counts["rgb"] + 1), 5)
    node.create_subscription(LaserScan, "/robot_1/scan",
                             lambda _: counts.__setitem__("scan", counts["scan"] + 1), 5)
    node.create_subscription(Clock, "/clock",
                             lambda m: last_clock.__setitem__(
                                 0, m.clock.sec + m.clock.nanosec * 1e-9), 10)

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node()
    rclpy.shutdown()

    assert 81 <= counts["rgb"] <= 99, f"Camera rate off: {counts['rgb']} msgs in 3s"
    assert 27 <= counts["scan"] <= 33, f"Lidar rate off: {counts['scan']} msgs in 3s"
    assert last_clock[0] > 0.0, "/clock never received"
