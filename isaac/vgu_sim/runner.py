from __future__ import annotations

import datetime
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from isaac.vgu_sim.acceptance_logging import (
    AcceptanceLogger,
    RobotPoseTracker,
    sample_robot_positions,
)
from isaac.vgu_sim.config import ResolvedRunConfig, RunResult, TimedObstacleConfig
from isaac.vgu_sim.event_scheduler import EventScheduler, prim_activation_callbacks
from isaac.vgu_sim.paths import run_output_dir


def run_simulation(
    config: ResolvedRunConfig, stop_flag: Path | None = None
) -> tuple[RunResult, ...]:
    """Run every repetition of a scenario, then close the app.

    Args:
        config: The resolved run configuration.
        stop_flag: Optional file path; once it exists, the current repetition
            stops at its next loop iteration, still closing GT and writing its
            manifest (see `stop_requested`), and no further repetition runs.

    Returns:
        One `RunResult` per repetition that ran.
    """
    app = _get_app(config.headless)
    results: list[RunResult] = []
    try:
        for rep in range(config.repetitions):
            result = run_repetition(app, config, rep, stop_flag=stop_flag)
            results.append(result)
            if not result.completed:
                break
    finally:
        app.close()
    return tuple(results)


def stop_requested(stop_flag: Path | None) -> bool:
    """Return whether the harness has asked the simulation loop to stop early.

    Kit catches and swallows SIGTERM, so `pkill` cannot stop an aborted run,
    and SIGINT's SimulationApp handler exits without the manifest write. A
    flag file polled inside the loop lets the loop exit normally instead.

    Args:
        stop_flag: The flag path, or None when no flag was configured.

    Returns:
        True when a flag path is configured and the file exists.
    """
    return stop_flag is not None and stop_flag.exists()


def abort_manifest_fields(
    stop_flag: Path, phase: str, sim_time_sec: float | None
) -> dict[str, Any]:
    """Build the manifest keys that mark a stop-flag abort.

    Only aborted runs carry these keys, so a normal run's manifest keeps its
    pre-flag key set byte for byte.

    Args:
        stop_flag: The flag path that was found.
        phase: `"topic_wait"` (before the GT loop) or `"sim_loop"`.
        sim_time_sec: Loop sim time when the flag was seen; None before the loop.

    Returns:
        The keys to merge into the manifest.
    """
    return {
        "aborted": True,
        "abort_reason": "stop_flag",
        "abort_phase": phase,
        "aborted_at_sim_time_sec": sim_time_sec,
        "stop_flag_path": str(stop_flag),
    }


def run_repetition(
    app, config: ResolvedRunConfig, repetition: int, stop_flag: Path | None = None
) -> RunResult:
    import carb
    import omni.timeline

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
    abort_fields: dict[str, Any] | None = None
    watchdog_executor = None

    scheduler = build_obstacle_scheduler(config.scenario.timed_obstacles, _current_stage)

    try:
        _open_stage(config.scenario_path)
        _enable_extensions()
        _validate_stage(config.scenario_path)

        import omni.usd as _omni_usd
        _set_timeline_window(_omni_usd.get_context().get_stage())

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        # Drive the sim with timeline.play() + app.update(), the NVIDIA
        # standalone ROS2-camera idiom — NOT SimulationContext.step(). step()
        # advances the physics step counter and renders, but it does not tick the
        # Isaac simulation clock that the OmniGraph publishers read
        # (IsaacReadSimulationTime stayed 0, so odom stamped 0 and the camera's
        # IsaacSimulationGate dropped every frame). A full Kit app.update() while
        # the timeline is playing advances simulation time, so the gate passes.
        # SimulationContext is still created+reset() to arm physics and to host
        # the graph wiring; we just don't call its step() in the loop.
        sim_ctx = _make_sim_context(physics_dt, 1.0 / rendering_hz)

        # Order matters: reset() reloads the stage to its initial USD state,
        # which WIPES any OmniGraph prims (and detaches the camera render-product
        # writer) created before it — that left the graphs advertised but never
        # ticking. So arm physics with reset() FIRST, then wire the ROS graphs
        # onto the live post-reset stage, then play() to start the timeline so
        # OnPlaybackTick fires with an advancing clock.
        sim_ctx.reset()
        # reset() reloads the on-disk USD, which has NO lights authored (only the
        # markers are emissive). An unlit RTX scene tonemaps to a fully-black
        # frame (max==0), so M1 sees nothing. Add lighting AFTER reset so it is
        # not wiped, same as the graph wiring below.
        _add_scene_lighting(_omni_usd.get_context().get_stage())
        _lidar_sensors = _wire_ros_graphs(config.scenario.robots)
        debug_annot = _attach_debug_rgb_annotator(config.scenario.robots)
        sim_ctx.play()

        _wait_for_ros_topics(
            sim_ctx, config.scenario.robots, config.topic_timeout_sec, stop_flag
        )

        # Start the Branch B cmd_vel watchdog (FR6.4.8). The drive graphs listen on
        # /<id>/cmd_vel_safe, so without this relay no robot moves on a real run —
        # it forwards /cmd_vel and zeros it after command_timeout_sec of silence.
        # Started after _wait_for_ros_topics (which shuts rclpy down in its finally)
        # so spin_in_thread re-inits cleanly; runs on use_sim_time off /clock.
        watchdog_executor = _start_cmd_vel_watchdog(config.scenario.robots)

        # One-shot in-process render readout: disambiguate "render product is
        # black" (camera/render-pipeline fault) from "ROS capture path is black"
        # (gate/transport fault). If this is non-zero but the ROS frame is black,
        # the fault is downstream of the render product.
        if debug_annot is not None:
            try:
                data = debug_annot.get_data()
                import numpy as _np
                arr = _np.asarray(data)
                print(
                    f"DEBUG render-product rgb shape={arr.shape} "
                    f"max={int(arr.max()) if arr.size else 'NA'} "
                    f"mean={float(arr.mean()):.2f}" if arr.size else "DEBUG rgb empty",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001 - debug-only
                print(f"DEBUG annotator readout failed: {exc}", flush=True)

        duration = config.scenario.runtime.duration_sec or config.scenario.duration_sec
        robot_ids = [robot.robot_id for robot in config.scenario.robots]
        pose_tracker = RobotPoseTracker()

        import omni.usd
        stage = omni.usd.get_context().get_stage()

        # sim_ctx.current_time already includes whatever this repetition spent
        # inside _wait_for_ros_topics before this loop starts, so anchor
        # sim_time to that baseline. Without it, `duration`, the scheduler's
        # spawn_at_sec/remove_at_sec (authored relative to recording start,
        # e.g. dynamic_anomaly.yaml's spawn_at_sec: 8.0), and the logged GT
        # sim_time_sec would all be offset by that startup time.
        loop_start_time = float(sim_ctx.current_time)
        sim_time = 0.0
        with open(gt_path, "w", encoding="utf-8") as gt_file:
            logger = AcceptanceLogger(gt_file, config.scenario, log_hz=10.0)
            while sim_time < duration and app.is_running():
                if stop_requested(stop_flag):
                    abort_fields = abort_manifest_fields(stop_flag, "sim_loop", sim_time)
                    break
                app.update()
                # One app.update() is not one physics step: rendering (and
                # thus app.update()) runs at rendering_hz (30) while physics
                # runs at physics_hz (60), so counting updates as physics
                # steps under-advanced sim_time by ~1.9x versus Isaac's own
                # /clock. Read the context's own clock instead.
                sim_time = float(sim_ctx.current_time) - loop_start_time
                applied = scheduler.apply_due_events(sim_time)
                if applied:
                    # The only record of a spawn/remove: GT carries robots only.
                    obstacle_states = {oid: scheduler.is_active(oid) for oid in applied}
                    print(
                        f"timed obstacle event sim_time={sim_time:.2f} "
                        f"active={obstacle_states}",
                        flush=True,
                    )
                positions = sample_robot_positions(stage, robot_ids)
                states = pose_tracker.update_from_positions(sim_time, positions)
                logger.maybe_write(sim_time, states)

        elapsed = sim_time
        # An aborted run's GT stops short of the horizon, so it must not read
        # as a completed episode to anything that trusts `completed`.
        if abort_fields is None:
            completed = True
        else:
            failure = f"aborted: stop flag {stop_flag} at sim_time_sec={sim_time:.2f}"
            print(f"stop flag seen: {failure}", flush=True)

    except _StopRequestedError as exc:
        failure = str(exc)
        abort_fields = abort_manifest_fields(stop_flag, "topic_wait", None)
        print(f"stop flag seen: {failure}", flush=True)
    except _TopicTimeoutError as exc:
        failure = str(exc)
        carb.log_error(failure)
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        carb.log_error(failure)
    finally:
        if watchdog_executor is not None:
            try:
                watchdog_executor.shutdown()
            except Exception:
                pass
        try:
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        # reset() now deactivates live prims; a failure there must not skip
        # the manifest write below.
        try:
            scheduler.reset()
        except Exception as exc:
            carb.log_warn(f"timed obstacle reset failed: {type(exc).__name__}: {exc}")

    manifest: dict[str, Any] = {
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
    }
    if abort_fields is not None:
        manifest.update(abort_fields)
    _write_manifest(manifest_path, manifest)

    return RunResult(
        run_id=run_id,
        repetition=repetition,
        completed=completed,
        elapsed_simulation_sec=elapsed,
        manifest_path=manifest_path,
        failure=failure,
    )


def build_obstacle_scheduler(
    timed_obstacles: list[TimedObstacleConfig] | tuple[TimedObstacleConfig, ...],
    get_stage: Callable[[], Any],
) -> EventScheduler:
    """Build the timed-obstacle scheduler wired to toggle prims on the live stage.

    Args:
        timed_obstacles: The scenario's `TimedObstacleConfig` entries.
        get_stage: Returns the live USD stage at event time.

    Returns:
        A scheduler whose spawn/remove events activate/deactivate the
        obstacles' prims.
    """
    activate_fn, deactivate_fn = prim_activation_callbacks(get_stage)
    return EventScheduler(timed_obstacles, activate_fn, deactivate_fn)


def _current_stage():
    import omni.usd
    return omni.usd.get_context().get_stage()


class _TopicTimeoutError(RuntimeError):
    pass


class _StopRequestedError(RuntimeError):
    pass


def _get_app(headless: bool):
    from isaacsim import SimulationApp

    # RTX lidar motion BVH: without this the raytracer only sees static
    # geometry and MOVING robots are absent from every /robot_N/scan, so
    # Nav2 costmaps and collision_monitor are blind to an approaching robot
    # (observed as head-on interpenetration). All three settings must be
    # passed together at boot — this is NVIDIA's own combination from
    # isaacsim.sensors.rtx's extension.toml. `enabled` alone (with or
    # without the engine-masking pair) breaks Hydra engine creation and
    # silences every render-dependent sensor (camera + both lidars,
    # observed 2026-07-03 both as a post-init carb mutation and as a lone
    # kit arg).
    return SimulationApp(
        {
            "headless": headless,
            "anti_aliasing": 0,
            "extra_args": [
                "--/renderer/raytracingMotion/enabled=true",
                "--/renderer/raytracingMotion/enableHydraEngineMasking=true",
                "--/renderer/raytracingMotion/enabledForHydraEngines=0,1,2,3",
            ],
        }
    )


def _open_stage(scenario_path: Path) -> None:
    import omni.usd
    omni.usd.get_context().open_stage(str(scenario_path.resolve()))


def _set_timeline_window(stage) -> None:
    """Give the stage a non-zero timeline so the playback cursor can advance.

    The scenario builder sets timeCodesPerSecond but never authors start/end
    time codes, so they default to 0/0 — a zero-length timeline. omni.timeline
    plays that as a frozen cursor at t=0, which pins IsaacReadSimulationTime at 0:
    odom messages get stamp 0 (dropped) and the camera's IsaacSimulationGate
    (keyed on sim time) drops every frame. A large end time code gives the
    timeline room to advance under SimulationContext.step(); the run length is
    still bounded by the step loop, not by this window.
    """
    stage.SetStartTimeCode(0.0)
    stage.SetEndTimeCode(10_000_000.0)


def _enable_extensions() -> None:
    import omni.kit.app
    manager = omni.kit.app.get_app().get_extension_manager()
    for ext in [
        # Foundational graph + render runtime that ros_graphs.py builds on:
        # OmniGraph core, Isaac core graph nodes (OnPhysicsStep, IsaacComputeOdometry,
        # IsaacArticulationController), and replicator (camera render product).
        "omni.graph.core",
        "omni.graph.action",
        "omni.replicator.core",
        "isaacsim.core.nodes",
        "isaacsim.ros2.bridge",
        "isaacsim.ros2.nodes",
        "isaacsim.robot.wheeled_robots",
        "isaacsim.sensors.rtx",
    ]:
        manager.set_extension_enabled_immediate(ext, True)


def _validate_stage(scenario_path: Path) -> None:
    from isaac.vgu_sim.validation import ValidationError, validate_scenario_stage
    try:
        validate_scenario_stage(scenario_path.resolve())
    except ValidationError as exc:
        raise RuntimeError(f"Stage validation failed: {exc}") from exc


def _make_sim_context(physics_dt: float, rendering_dt: float):
    from isaacsim.core.api import SimulationContext
    return SimulationContext(
        physics_dt=physics_dt,
        rendering_dt=rendering_dt,
        stage_units_in_meters=1.0,
    )


def _add_scene_lighting(stage) -> None:
    """Author a dome light so the RTX render is not a fully-black frame.

    The warehouse asset ships with no lights (only emissive markers), so an
    unlit scene renders pure black and M1 detects nothing. A dome light gives
    uniform ambient illumination that lights the floor, robots, and markers
    without casting harsh shadows. Authored after reset() so it survives.
    """
    from pxr import Sdf, UsdLux

    # Keep illumination moderate. An earlier dome(1000)+distant(2000) setup
    # overexposed the scene (mean ~196 with a blown-out central hotspot), which
    # washed out the ArUco markers' black/white contrast — defeating their whole
    # point (the markers are emissive and self-lit, so they need only enough
    # ambient to read the floor/robots, not a bright key light). A single modest
    # dome gives flat, even illumination without the specular hotspot; the
    # distant light is dropped because it was the source of the overexposure.
    light_path = "/World/Environment/DomeLight"
    dome = UsdLux.DomeLight.Define(stage, Sdf.Path(light_path))
    dome.CreateIntensityAttr(500.0)


def _attach_debug_rgb_annotator(robots):
    """Attach an rgb annotator to the camera render product for an in-process
    pixel readout. Returns the annotator or None if replicator is unavailable."""
    try:
        import omni.replicator.core as rep

        from isaac.vgu_sim.config import CameraConfig

        cam_cfg = CameraConfig()
        rp = rep.create.render_product(
            cam_cfg.prim_path, (cam_cfg.width, cam_cfg.height)
        )
        annot = rep.AnnotatorRegistry.get_annotator("rgb")
        annot.attach([rp])
        return annot
    except Exception as exc:  # noqa: BLE001 - debug-only
        print(f"DEBUG annotator attach failed: {exc}", flush=True)
        return None


def _wire_ros_graphs(robots) -> list:
    import omni.usd

    from isaac.vgu_sim.config import CameraConfig, RobotAssetConfig
    from isaac.vgu_sim.robot_drive import (
        configure_contact_friction,
        configure_wheel_velocity_drive,
    )
    from isaac.vgu_sim.ros_graphs import (
        create_global_ros_graphs,
        create_robot_lidar_sensor,
        create_robot_ros_graph,
    )

    stage = omni.usd.get_context().get_stage()
    camera_cfg = CameraConfig()
    create_global_ros_graphs(stage, camera_cfg.prim_path, camera_cfg)

    robot_asset_cfg = RobotAssetConfig()
    # LidarSensor objects must stay referenced for the simulation's lifetime:
    # their __del__ detaches the ROS2 writer and destroys the render product,
    # which would silently stop /<robot_id>/scan if they were GC'd.
    lidar_sensors = []
    for robot in robots:
        robot_prim_path = f"/World/Robots/{robot.robot_id}"
        # Switch the wheel joints to velocity drive before wiring the graph, so the
        # DifferentialController's velocity targets actually move the articulation
        # (position-mode drives would ignore them). See M4 Phase 1 Task 3.
        configure_wheel_velocity_drive(stage, robot_prim_path, robot_asset_cfg)
        # Bind a friction material to the wheel/floor contact; without it PhysX
        # uses a frictionless default and the spinning wheels slip in place.
        configure_contact_friction(stage, robot_prim_path, robot_asset_cfg)
        create_robot_ros_graph(stage, robot, robot_prim_path, robot_asset_cfg)
        lidar_sensors.append(
            create_robot_lidar_sensor(stage, robot, robot_prim_path, robot_asset_cfg)
        )
    return lidar_sensors


def _start_cmd_vel_watchdog(robots):
    """Launch one Branch B cmd_vel watchdog per robot in a background thread.

    Returns the executor (so the caller can shut it down) or None if rclpy is
    unavailable. Failure here is non-fatal: the sim still renders, but robots
    will not move because the drive graphs only consume /<id>/cmd_vel_safe.
    """
    from isaac.vgu_sim.cmd_vel_watchdog_node import spin_in_thread
    from isaac.vgu_sim.config import RobotAssetConfig

    robot_ids = [robot.robot_id for robot in robots]
    timeout = RobotAssetConfig().command_timeout_sec
    executor, _nodes = spin_in_thread(robot_ids, timeout)
    return executor


def _wait_for_ros_topics(
    sim_ctx, robots, timeout_sec: float, stop_flag: Path | None = None
) -> None:
    import time

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Image, LaserScan

    # Topic advertisement alone is not enough: Isaac can create DDS endpoints
    # before the OmniGraph publishers are actually ticking. Require one live
    # sample from the camera plus each robot's odom and scan stream so downstream
    # M1/M4/M5 nodes do not start against advertised-but-silent topics.
    import omni.kit.app
    import omni.timeline
    timeline = omni.timeline.get_timeline_interface()
    kit_app = omni.kit.app.get_app()

    required = ["/camera/image_raw"]
    for robot in robots:
        required.extend([f"/{robot.robot_id}/odom", f"/{robot.robot_id}/scan"])

    received: set[str] = set()
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )

    rclpy.init(args=None)
    node = Node("_m6_topic_waiter")
    subscriptions = [
        node.create_subscription(
            Image,
            "/camera/image_raw",
            lambda _msg, topic="/camera/image_raw": received.add(topic),
            qos,
        )
    ]
    for robot in robots:
        odom_topic = f"/{robot.robot_id}/odom"
        scan_topic = f"/{robot.robot_id}/scan"
        subscriptions.append(
            node.create_subscription(
                Odometry,
                odom_topic,
                lambda _msg, topic=odom_topic: received.add(topic),
                qos,
            )
        )
        subscriptions.append(
            node.create_subscription(
                LaserScan,
                scan_topic,
                lambda _msg, topic=scan_topic: received.add(topic),
                qos,
            )
        )
    deadline = time.monotonic() + timeout_sec
    available: set[str] = set()
    tick = 0
    try:
        while time.monotonic() < deadline:
            if stop_requested(stop_flag):
                raise _StopRequestedError(
                    f"aborted: stop flag {stop_flag} during the ROS topic wait"
                )
            # Pump a full Kit app.update() while the timeline plays: this advances
            # simulation time (IsaacReadSimulationTime), which OnPlaybackTick, the
            # camera render product, and the camera's IsaacSimulationGate all
            # depend on. SimulationContext.step() does not tick that clock.
            kit_app.update()
            # Instrumentation: timeline must be playing AND simulation time must
            # advance. is_playing False => play() did not stick; is_playing True
            # but the clocks stay 0 => sim time never advances and the camera gate
            # drops frames.
            if tick % 30 == 0:
                print(
                    f"TL is_playing={timeline.is_playing()} "
                    f"timeline_t={timeline.get_current_time():.4f} "
                    f"sim_t={sim_ctx.current_time:.4f}",
                    flush=True,
                )
            tick += 1
            available = {name for name, _ in node.get_topic_names_and_types()}
            rclpy.spin_once(node, timeout_sec=0.0)
            if all(t in received for t in required):
                return
            time.sleep(0.1)
        raise _TopicTimeoutError(
            f"ROS topic samples not ready within {timeout_sec}s. "
            f"Missing topics: {set(required) - available}. "
            f"Silent topics: {set(required) - received}"
        )
    finally:
        for sub in subscriptions:
            node.destroy_subscription(sub)
        node.destroy_node()
        rclpy.shutdown()


def _write_manifest(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
