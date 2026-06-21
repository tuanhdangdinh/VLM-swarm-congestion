"""Record M1's annotated overhead view while robots drive a scenario.

Operator/diagnostic tool (not a unit-tested module). It boots Isaac Sim headless,
builds the scenario, wires the M4 Phase-1 drive chain + overhead camera, drives the
robots open-loop with the speed-capped ``FixedTwistDriver``, and writes M1's
annotated frames to an mp4 by calling ``process_frame`` in-process.

Frame source: /camera/image_raw via rclpy subscriber (rgb8, decoded without
cv_bridge). The annotator-based approach was abandoned because the replicator
annotator's render product is a separate pipeline that doesn't update as physics
progresses — the OmniGraph camera ROS publisher does.

Why in-process: on this host rclpy only imports inside the Isaac runtime (the
ROS2-bridge extension injects it); cv_bridge is absent; a standalone recorder
process cannot import rclpy.

Usage (headless GCP box):
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.record_m1_drive --smoke
    ${ISAAC_SIM_ROOT}/python.sh -m isaac.scripts.record_m1_drive \\
        --scenario head_on_deadlock --seconds 12 --speed 0.10 \\
        --out data/logs/recordings/m1_drive.mp4
"""
import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record M1 annotated view while robots drive")
    parser.add_argument("--scenario", default="head_on_deadlock")
    parser.add_argument("--seconds", type=float, default=12.0,
                        help="Sim seconds to drive + record (full mode).")
    parser.add_argument("--speed", type=float, default=0.10,
                        help="Forward speed (m/s); capped at 0.15 by FixedTwistDriver.")
    parser.add_argument("--capture-fps", type=float, default=10.0,
                        help="Annotated frames captured per sim second.")
    parser.add_argument("--out", type=Path,
                        default=Path("data/logs/recordings/m1_drive.mp4"))
    parser.add_argument("--smoke", action="store_true",
                        help="Static gate: render a few frames, dump raw+annotated "
                             "PNG and the detected-robot count, then exit. No driving.")
    parser.add_argument("--topic-timeout-sec", type=float, default=20.0)
    args = parser.parse_args()

    import yaml

    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path

    cfg_path = scenario_config_path(args.scenario)
    if not cfg_path.exists():
        sys.exit(f"Scenario config not found: {cfg_path}")
    with open(cfg_path) as f:
        scenario = ScenarioConfig.model_validate(yaml.safe_load(f))

    config = ResolvedRunConfig(
        scenario_path=scenario_output_path(scenario.name).resolve(),
        scenario=scenario,
        headless=True,
        repetitions=1,
        output_dir=Path("data/logs/simulation"),
        topic_timeout_sec=args.topic_timeout_sec,
        ros_domain_id=None,
    )
    if not config.scenario_path.exists():
        sys.exit(f"Scenario USD not built: {config.scenario_path}")

    _record(config, args)


def _record(config, args) -> None:
    import numpy as np

    from isaac.vgu_sim import runner as R
    from isaac.vgu_sim.paths import aruco_dict_name

    app = R._get_app(headless=True)
    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()
        R._validate_stage(config.scenario_path)

        import omni.usd as _omni_usd
        R._set_timeline_window(_omni_usd.get_context().get_stage())

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        R._add_scene_lighting(_omni_usd.get_context().get_stage())
        R._wire_ros_graphs(config.scenario.robots)

        # Enable USD→Fabric notice handler so Newton articulation positions
        # reach the RTX renderer. Newton writes physics results to pxr USD
        # (updateToUsd=True by default). The RTX renderer reads Fabric via
        # usdrt_delegate. SimulationManager.enable_fabric_usd_notice_handler
        # wires USD change notices → Fabric, completing the chain.
        # We also manually write WORLD positions to Fabric after each step to
        # override the LOCAL translate that the notice handler syncs (base_link's
        # resetXformStack=True causes the renderer to treat local translate as
        # world position, so we must supply the actual world coordinates).
        import omni.usd as _omni_usd_pre
        _stage_for_fabric = _omni_usd_pre.get_context().get_stage()
        _stage_id_for_fabric = _omni_usd_pre.get_context().get_stage_id()
        from isaacsim.core.simulation_manager import SimulationManager
        SimulationManager.enable_fabric_usd_notice_handler(_stage_id_for_fabric, True)
        print("RECORD fabric_usd_notice_handler enabled", flush=True)

        # Collect (pxr_prim, usdrt_prim) pairs for all robot base_links
        from pxr import UsdGeom, Usd
        import usdrt as _usdrt
        _usdrt_stage = _usdrt.Usd.Stage.Attach(_stage_id_for_fabric)
        robot_prims = []
        for robot_cfg in config.scenario.robots:
            rid = robot_cfg.robot_id
            bl_path = f"/World/Robots/{rid}/Geometry/base_footprint/base_link"
            usd_p = _stage_for_fabric.GetPrimAtPath(bl_path)
            ur_p = _usdrt_stage.GetPrimAtPath(bl_path)
            if usd_p.IsValid() and ur_p.IsValid():
                robot_prims.append((usd_p, ur_p, rid))
                xf = UsdGeom.Xformable(usd_p)
                t0 = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                print(f"RECORD {rid} initial world ({float(t0[0]):.3f}, {float(t0[1]):.3f})", flush=True)

        sim_ctx.play()

        # _wait_for_ros_topics verifies /camera/image_raw is publishing, then
        # calls rclpy.shutdown() in its finally — required so the watchdog can
        # re-init rclpy cleanly (runner.py comment documents this pattern).
        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, config.topic_timeout_sec)

        # M1 pipeline objects (pure functions; no ROS).
        from swarm_perception.calibration import load_calibration
        from swarm_perception.models import Frame
        from swarm_perception.pipeline import process_frame
        from swarm_perception.state_estimator import StateEstimator

        cal_path = Path("ros2_ws/src/swarm_perception/config/calibration.yaml").resolve()
        calibration = load_calibration(str(cal_path))
        marker_dict = aruco_dict_name()
        estimator = StateEstimator(
            stopped_threshold_mps=0.01,
            slow_threshold_mps=0.05,
            stale_after_sec=1.0,
            velocity_alpha=0.3,
            frame_id="overhead_camera",
        )

        if args.smoke:
            # Smoke uses the annotator (static scene, no drive — it's fine).
            annot = R._attach_debug_rgb_annotator(config.scenario.robots)
            if annot is None:
                raise RuntimeError("rgb annotator unavailable")
            for _ in range(30):
                app.update()
            _run_smoke(app, annot, calibration, estimator, marker_dict,
                       Frame, process_frame, np)
            return

        # Full mode: watchdog + driver + camera ROS subscriber.
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        # Camera subscriber — created in the new rclpy context (after watchdog re-init).
        # Decodes rgb8 sensor_msgs/Image to (H, W, 3) uint8 numpy without cv_bridge.
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_rec_cam")
                from sensor_msgs.msg import Image as _Img
                self.latest: np.ndarray | None = None
                self.latest_stamp: float = 0.0
                self.create_subscription(_Img, "/camera/image_raw", self._cb, 10)

            def _cb(self, msg) -> None:
                h, w = msg.height, msg.width
                raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
                self.latest = np.ascontiguousarray(raw.reshape(h, w, 3))
                self.latest_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        cam_node = _CamNode()
        cam_exec = SingleThreadedExecutor()
        cam_exec.add_node(cam_node)

        import threading
        cam_thread = threading.Thread(target=cam_exec.spin, daemon=True)
        cam_thread.start()

        robot_ids = [robot.robot_id for robot in config.scenario.robots]
        from tests.simulation.stop_stub import FixedTwistDriver
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=args.speed)
        print("RECORD driver+watchdog+cam-sub started", flush=True)

        _run_full(app, config, args, physics_hz, physics_dt,
                  cam_node, calibration, estimator, marker_dict,
                  Frame, process_frame, np, R, driver, watchdog_executor,
                  robot_prims=robot_prims)

    finally:
        import omni.timeline
        try:
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        app.close()


def _run_smoke(app, annot, calibration, estimator, marker_dict,
               Frame, process_frame, np) -> None:
    import cv2

    data = np.asarray(annot.get_data())
    if data.ndim == 3 and data.shape[2] == 4:
        data = data[:, :, :3]
    rgb = np.ascontiguousarray(data, dtype=np.uint8)
    print(f"SMOKE raw rgb shape={rgb.shape} max={int(rgb.max())} "
          f"mean={float(rgb.mean()):.2f}", flush=True)

    frame = Frame(image=rgb, stamp=1.0, frame_id="overhead_camera",
                  source_id=calibration.source_id)
    scene_state, annotated = process_frame(
        frame, calibration, estimator, None, marker_dictionary=marker_dict)
    print(f"SMOKE detected_robots={len(scene_state.robots)} "
          f"diagnostics={dict(scene_state.diagnostics)}", flush=True)
    for r in scene_state.robots:
        print(f"  robot {r.robot_id} x={r.x:.2f} y={r.y:.2f} status={r.status}", flush=True)

    out_dir = Path("data/logs/recordings")
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "smoke_raw.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(out_dir / "smoke_annotated.png"),
                cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))
    print(f"SMOKE wrote {out_dir/'smoke_raw.png'} and {out_dir/'smoke_annotated.png'}",
          flush=True)


def _run_full(app, config, args, physics_hz, physics_dt,
              cam_node, calibration, estimator, marker_dict,
              Frame, process_frame, np, R, driver, watchdog_executor,
              robot_prims=None) -> None:
    import cv2

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    capture_every = max(1, int(round(physics_hz / args.capture_fps)))
    writer = None
    frames_written = 0
    detected_max = 0

    # Let the camera subscriber warm up — pump updates until we get a fresh frame.
    import time
    t_warm = time.monotonic()
    while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
        app.update()
    if cam_node.latest is None:
        raise RuntimeError("Camera subscriber received no frames during warmup")
    print(f"RECORD cam warmup done; first frame shape={cam_node.latest.shape}", flush=True)

    from pxr import UsdGeom, Usd

    def _sync_world_to_fabric() -> None:
        """Write pxr USD WORLD positions to Fabric so RTX renders correct locations."""
        if not robot_prims:
            return
        for usd_p, ur_p, _rid in robot_prims:
            try:
                xf = UsdGeom.Xformable(usd_p)
                t = xf.ComputeLocalToWorldTransform(
                    Usd.TimeCode.Default()).ExtractTranslation()
                fa = ur_p.GetAttribute("xformOp:translate")
                if fa.IsValid():
                    fa.Set((float(t[0]), float(t[1]), float(t[2])))
            except Exception:
                pass

    sim_time = 0.0
    step = 0
    last_cam_stamp = -1.0
    try:
        while sim_time < args.seconds and app.is_running():
            app.update()
            _sync_world_to_fabric()
            if step % capture_every == 0:
                rgb = cam_node.latest
                if rgb is None or cam_node.latest_stamp == last_cam_stamp:
                    # No new camera frame yet — skip this capture slot.
                    sim_time += physics_dt
                    step += 1
                    continue
                last_cam_stamp = cam_node.latest_stamp
                rgb = np.ascontiguousarray(rgb)  # snapshot from subscriber thread
                frame = Frame(image=rgb, stamp=max(sim_time, 1e-3),
                              frame_id="overhead_camera",
                              source_id=calibration.source_id)
                scene_state, annotated = process_frame(
                    frame, calibration, estimator, None,
                    marker_dictionary=marker_dict)
                detected_max = max(detected_max, len(scene_state.robots))
                bgr = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
                if writer is None:
                    h, w = bgr.shape[:2]
                    writer = cv2.VideoWriter(
                        str(out_path), cv2.VideoWriter_fourcc(*"mp4v"),
                        args.capture_fps, (w, h))
                    if not writer.isOpened():
                        raise RuntimeError(f"VideoWriter failed to open {out_path}")
                writer.write(bgr)
                frames_written += 1
                if frames_written % 10 == 0:
                    r0 = scene_state.robots[0] if scene_state.robots else None
                    pos = f"robot[0]_x={r0.x:.3f}" if r0 else "no_detection"
                    print(f"RUN_FULL sim_t={sim_time:.1f} frames={frames_written} "
                          f"detected={len(scene_state.robots)} {pos}", flush=True)
            sim_time += physics_dt
            step += 1
        print(f"RUN_FULL loop done sim_t={sim_time:.2f} steps={step}", flush=True)
    except BaseException as exc:
        import traceback
        print(f"RUN_FULL EXCEPTION {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        raise
    finally:
        if driver is not None:
            driver.request_stop()
        if watchdog_executor is not None:
            try:
                watchdog_executor.shutdown()
            except Exception:
                pass
        if writer is not None:
            writer.release()

    print(f"RECORD wrote {frames_written} frames to {out_path} "
          f"(max detected robots in any frame={detected_max})", flush=True)
    if frames_written == 0:
        sys.exit("No frames written")
    if detected_max == 0:
        sys.exit("Recorded video but M1 never detected a robot — check markers/calibration")


if __name__ == "__main__":
    main()
