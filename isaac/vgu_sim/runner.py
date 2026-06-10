from __future__ import annotations

import datetime
import json
from pathlib import Path

from isaac.vgu_sim.config import ResolvedRunConfig, RunResult, ScenarioConfig
from isaac.vgu_sim.event_scheduler import EventScheduler
from isaac.vgu_sim.paths import run_output_dir


def run_simulation(config: ResolvedRunConfig) -> tuple[RunResult, ...]:
    app = _get_app(config.headless)
    results: list[RunResult] = []
    try:
        for rep in range(config.repetitions):
            result = run_repetition(app, config, rep)
            results.append(result)
            if not result.completed:
                break
    finally:
        app.close()
    return tuple(results)


def run_repetition(app, config: ResolvedRunConfig, repetition: int) -> RunResult:
    import omni.timeline
    import carb

    output_dir = run_output_dir(
        config.output_dir, config.scenario.name, config.scenario.seed, repetition
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "run_manifest.json"
    gt_path = output_dir / "ground_truth.jsonl"

    run_id = f"{config.scenario.name}-seed{config.scenario.seed}-rep{repetition:03d}"
    started_at = datetime.datetime.utcnow().isoformat() + "Z"

    failure: str | None = None
    elapsed: float = 0.0
    completed = False

    scheduler = EventScheduler(config.scenario.timed_obstacles)

    try:
        _open_stage(config.scenario_path)
        _enable_extensions()
        _validate_stage(config.scenario_path)
        _init_physics()

        timeline = omni.timeline.get_timeline_interface()
        timeline.play()

        _wait_for_ros_topics(config.scenario.robots, config.topic_timeout_sec)

        physics_dt = 1.0 / 60.0
        render_every_n = 2
        duration = config.scenario.runtime.duration_sec or config.scenario.duration_sec

        step = 0
        sim_time = 0.0
        with open(gt_path, "w") as gt_file:
            while sim_time < duration and app.is_running():
                app.update()
                scheduler.apply_due_events(sim_time)
                _write_ground_truth(gt_file, sim_time, config.scenario)
                sim_time += physics_dt
                step += 1

        elapsed = sim_time
        completed = True

    except _TopicTimeoutError as exc:
        failure = str(exc)
        carb.log_error(failure)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        carb.log_error(failure)
    finally:
        try:
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        scheduler.reset()

    _write_manifest(manifest_path, {
        "run_id": run_id,
        "scenario": config.scenario.name,
        "scenario_schema_version": config.scenario.schema_version,
        "seed": config.scenario.seed,
        "repetition": repetition,
        "headless": config.headless,
        "isaac_sim_version": "6.0",
        "ros_distribution": "jazzy",
        "physics_hz": config.scenario.runtime.physics_hz,
        "rendering_hz": config.scenario.runtime.rendering_hz,
        "started_at_utc": started_at,
        "completed": completed,
        "failure": failure,
    })

    return RunResult(
        run_id=run_id,
        repetition=repetition,
        completed=completed,
        elapsed_simulation_sec=elapsed,
        manifest_path=manifest_path,
        failure=failure,
    )


class _TopicTimeoutError(RuntimeError):
    pass


def _get_app(headless: bool):
    from isaacsim import SimulationApp
    return SimulationApp({"headless": headless, "anti_aliasing": 0})


def _open_stage(scenario_path: Path) -> None:
    import omni.usd
    omni.usd.get_context().open_stage(str(scenario_path))


def _enable_extensions() -> None:
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    for ext in [
        "isaacsim.ros2.bridge",
        "isaacsim.ros2.nodes",
        "isaacsim.robot.wheeled_robots",
        "isaacsim.sensors.rtx",
    ]:
        manager.set_extension_enabled_immediate(ext, True)


def _validate_stage(scenario_path: Path) -> None:
    from isaac.vgu_sim.validation import validate_scenario_stage, ValidationError
    try:
        validate_scenario_stage(scenario_path)
    except ValidationError as exc:
        raise RuntimeError(f"Stage validation failed: {exc}") from exc


def _init_physics() -> None:
    import omni.physx
    omni.physx.get_physx_interface().start_simulation()


def _wait_for_ros_topics(robots, timeout_sec: float) -> None:
    import time
    import rclpy
    from rclpy.node import Node

    required = ["/camera/image_raw", "/clock"] + [
        f"/{r.robot_id}/odom" for r in robots
    ]
    rclpy.init(args=None)
    node = Node("_m6_topic_waiter")
    deadline = time.monotonic() + timeout_sec
    try:
        while time.monotonic() < deadline:
            available = {name for name, _ in node.get_topic_names_and_types()}
            if all(t in available for t in required):
                return
            time.sleep(0.5)
        raise _TopicTimeoutError(
            f"ROS topics not ready within {timeout_sec}s. "
            f"Missing: {set(required) - available}"
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _write_ground_truth(file, sim_time: float, scenario: ScenarioConfig) -> None:
    record = {"sim_time_sec": round(sim_time, 4)}
    file.write(json.dumps(record) + "\n")


def _write_manifest(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
