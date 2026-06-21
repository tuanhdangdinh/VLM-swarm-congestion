"""Probe: manually sync Newton USD positions → Fabric after each step.

Confirmed: Newton writes to pxr USD correctly (0.56m odom/USD match).
Problem: pxr USD → Fabric sync doesn't auto-trigger in headless mode.
         RTX renderer reads Fabric (via usdrt_delegate), sees frozen scene.

Fix attempt: after each app.update(), read world pos from pxr USD and
write it to Fabric's xformOp:translate (world-space, since
omni:fabric:resetXformStack=True on base_link).

If camera shows movement after this → manual sync fixes it → apply to recorder.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_manual_fabric_sync
"""
from pathlib import Path
import traceback


def main() -> None:
    try:
        _run()
    except Exception:
        traceback.print_exc()


def _run() -> None:
    import yaml
    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path
    from isaac.vgu_sim import runner as R

    scenario_name = "head_on_deadlock"
    cfg_path = scenario_config_path(scenario_name)
    with open(cfg_path) as f:
        scenario = ScenarioConfig.model_validate(yaml.safe_load(f))

    config = ResolvedRunConfig(
        scenario_path=scenario_output_path(scenario.name).resolve(),
        scenario=scenario,
        headless=True,
        repetitions=1,
        output_dir=Path("data/logs/simulation"),
        topic_timeout_sec=20.0,
        ros_domain_id=None,
    )

    app = R._get_app(headless=True)
    print("MSYNC app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        import omni.usd as _omni_usd
        stage = _omni_usd.get_context().get_stage()
        R._set_timeline_window(stage)

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        R._add_scene_lighting(stage)
        R._wire_ros_graphs(config.scenario.robots)

        # Default settings — Newton writes to pxr USD
        import carb
        _settings = carb.settings.get_settings()
        print(f"MSYNC updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        # Setup pxr USD prims for ALL robots
        from pxr import UsdGeom, Usd
        import usdrt

        stage_id = _omni_usd.get_context().get_stage_id()
        usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)

        robot_prims = []  # list of (usd_prim, usdrt_prim, name)
        for robot in config.scenario.robots:
            rid = robot.robot_id
            base_link_path = f"/World/Robots/{rid}/Geometry/base_footprint/base_link"
            usd_prim = stage.GetPrimAtPath(base_link_path)
            ur_prim = usdrt_stage.GetPrimAtPath(base_link_path)
            print(f"MSYNC robot {rid}: usd_valid={usd_prim.IsValid()} "
                  f"usdrt_valid={ur_prim.IsValid()}", flush=True)
            if usd_prim.IsValid() and ur_prim.IsValid():
                # Check initial fabric translate
                fa = ur_prim.GetAttribute("xformOp:translate")
                if fa.IsValid():
                    init_val = fa.Get()
                    print(f"MSYNC {rid} initial fabric translate: {init_val}", flush=True)
                # Check initial usd world pos
                xf = UsdGeom.Xformable(usd_prim)
                t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                print(f"MSYNC {rid} initial usd world: ({float(t[0]):.4f},{float(t[1]):.4f})",
                      flush=True)
                robot_prims.append((usd_prim, ur_prim, rid))

        sim_ctx.play()
        print(f"MSYNC after play: updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("MSYNC driver started", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_msync")
                self.latest: np.ndarray | None = None
                self.count: int = 0
                self.create_subscription(_Img, "/camera/image_raw", self._cb, 10)

            def _cb(self, msg) -> None:
                h, w = msg.height, msg.width
                raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
                self.latest = np.ascontiguousarray(raw.reshape(h, w, 3))
                self.count += 1

        cam_node = _CamNode()
        cam_exec = SingleThreadedExecutor()
        cam_exec.add_node(cam_node)
        cam_thread = threading.Thread(target=cam_exec.spin, daemon=True)
        cam_thread.start()

        import time
        t_warm = time.monotonic()
        while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
            app.update()
        print(f"MSYNC warmup done count={cam_node.count}", flush=True)

        import omni.graph.core as og
        odom_path = f"/World/ROSGraphs/{config.scenario.robots[0].robot_id}/drive_graph/odom_compute"

        means = []
        odom_xs = []
        first_frame: np.ndarray | None = None

        def _sync_fabric() -> None:
            """Copy world position from pxr USD to Fabric for each robot body."""
            for usd_prim, ur_prim, rid in robot_prims:
                try:
                    xf = UsdGeom.Xformable(usd_prim)
                    t = xf.ComputeLocalToWorldTransform(
                        Usd.TimeCode.Default()).ExtractTranslation()
                    fa = ur_prim.GetAttribute("xformOp:translate")
                    if fa.IsValid():
                        fa.Set(usdrt.Gf.Vec3d(float(t[0]), float(t[1]), float(t[2])))
                except Exception as e:
                    print(f"MSYNC sync error {rid}: {e}", flush=True)

        for i in range(200):
            app.update()

            # Manually sync pxr USD → Fabric BEFORE next render
            _sync_fabric()

            if cam_node.latest is not None:
                m = float(cam_node.latest.mean())
                means.append(m)
                if first_frame is None:
                    first_frame = cam_node.latest.copy()

            try:
                node = og.get_node_by_path(odom_path)
                if node and node.is_valid():
                    pos = node.get_attribute("outputs:position").get()
                    if pos is not None:
                        odom_xs.append(float(pos[0]))
            except Exception:
                pass

            if i % 40 == 0:
                mean_s = f"{means[-1]:.3f}" if means else "N/A"
                odom_s = f"{odom_xs[-1]:.4f}" if odom_xs else "N/A"
                print(f"MSYNC i={i} cam={mean_s} odom_x={odom_s}", flush=True)

        print(f"MSYNC total camera frames: {cam_node.count}", flush=True)

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            result = "CHANGING!" if max_diff > 0.5 else "static"
            print(f"MSYNC camera max_mean_diff={max_diff:.4f} ({result})", flush=True)
            # Also check first vs last mean
            diff_fl = abs(means[-1] - means[0])
            print(f"MSYNC camera first_vs_last_diff={diff_fl:.4f}", flush=True)

        if len(odom_xs) >= 2:
            dist = abs(odom_xs[-1] - odom_xs[0])
            print(f"MSYNC odom x-displacement: {dist:.4f}m", flush=True)

        # Save comparison frames
        try:
            import cv2
            out_dir = Path("data/logs/recordings")
            out_dir.mkdir(parents=True, exist_ok=True)

            if first_frame is not None:
                cv2.imwrite(str(out_dir / "msync_first.png"),
                            cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR))
                print("MSYNC saved msync_first.png", flush=True)

            if cam_node.latest is not None:
                cv2.imwrite(str(out_dir / "msync_last.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("MSYNC saved msync_last.png", flush=True)

        except Exception as e:
            print(f"MSYNC cv2 error: {e}", flush=True)

    finally:
        print("MSYNC cleanup", flush=True)
        try:
            import omni.timeline
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        if watchdog_executor:
            try:
                watchdog_executor.shutdown()
            except Exception:
                pass
        if driver:
            try:
                driver.request_stop()
            except Exception:
                pass
        app.close()


if __name__ == "__main__":
    main()
