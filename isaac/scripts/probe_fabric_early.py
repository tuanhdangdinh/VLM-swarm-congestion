"""Probe: enable omni.physx.fabric BEFORE opening the stage.

Hypothesis: Fabric bindings for physics bodies are set up at stage load time.
Enabling Fabric after stage open leaves bodies without Fabric bindings.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_fabric_early
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
    print("FABE app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        # *** ENABLE FABRIC BEFORE opening the stage ***
        import carb
        import omni.kit.app
        _settings = carb.settings.get_settings()
        _ext_mgr = omni.kit.app.get_app().get_extension_manager()

        result = _ext_mgr.set_extension_enabled_immediate("omni.physx.fabric", True)
        print(f"FABE enable omni.physx.fabric (pre-stage): result={result}", flush=True)

        # Check if omni.physxfabric is importable now
        try:
            import omni.physxfabric
            iface = omni.physxfabric.get_physx_fabric_interface()
            print(f"FABE omni.physxfabric available: {iface}", flush=True)
        except Exception as e:
            print(f"FABE omni.physxfabric not available: {e}", flush=True)

        _settings.set_bool("/physics/updateToUsd", False)
        _settings.set_bool("/physics/updateParticlesToUsd", False)
        _settings.set_bool("/physics/updateVelocitiesToUsd", False)
        _settings.set_bool("/physics/updateForceSensorsToUsd", False)
        print(f"FABE carb set: updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        # NOW open the stage (physics bodies will bind to Fabric at load time)
        R._open_stage(config.scenario_path)
        R._enable_extensions()
        print("FABE stage opened", flush=True)

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

        # Verify carb settings didn't get reset
        print(f"FABE carb after reset: updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        sim_ctx.play()
        print("FABE play called", flush=True)

        # Verify again after play
        print(f"FABE carb after play: updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        print("FABE ros topics ready", flush=True)

        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("FABE driver started", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_fabe")
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

        # Warmup
        import time
        t_warm = time.monotonic()
        while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
            app.update()
        if cam_node.latest is None:
            print("FABE ERROR: no camera frame", flush=True)
            return
        print(f"FABE warmup done shape={cam_node.latest.shape}", flush=True)

        # Also check OmniGraph odom + prim USD position
        import omni.graph.core as og
        from pxr import UsdGeom, Usd

        robot_0 = config.scenario.robots[0]
        robot_id = robot_0.robot_id

        robot_prim = None
        for ppath in [f"/World/Robots/{robot_id}/base_link",
                      f"/World/Robots/{robot_id}"]:
            p = stage.GetPrimAtPath(ppath)
            if p.IsValid():
                robot_prim = p
                print(f"FABE prim at {ppath}", flush=True)
                break

        odom_node = og.get_node_by_path(
            f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute")

        means = []
        usd_positions = []
        odom_positions = []

        for i in range(120):
            app.update()

            rgb = cam_node.latest
            if rgb is not None:
                means.append(float(rgb.mean()))

            if robot_prim:
                try:
                    xf = UsdGeom.Xformable(robot_prim)
                    t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                    usd_positions.append((float(t[0]), float(t[1])))
                except Exception:
                    pass

            if odom_node and odom_node.is_valid():
                try:
                    pos = odom_node.get_attribute("outputs:position").get()
                    if pos is not None:
                        odom_positions.append((float(pos[0]), float(pos[1])))
                except Exception:
                    pass

            if i % 30 == 0:
                ustr = str(usd_positions[-1]) if usd_positions else "N/A"
                ostr = str(odom_positions[-1]) if odom_positions else "N/A"
                mstr = str(round(means[-1], 3)) if means else "N/A"
                print(f"FABE i={i} cam_mean={mstr} usd={ustr} odom={ostr}", flush=True)

        # Results
        if means:
            diffs = [abs(means[j] - means[j-1]) for j in range(1, len(means))]
            max_diff = max(diffs) if diffs else 0.0
            print(f"FABE camera max_mean_diff={max_diff:.4f}", flush=True)
            if max_diff > 0.5:
                print("FABE RESULT: camera IS changing!", flush=True)
            else:
                print("FABE RESULT: camera still static", flush=True)

        if len(usd_positions) >= 2:
            dx = abs(usd_positions[-1][0] - usd_positions[0][0])
            dy = abs(usd_positions[-1][1] - usd_positions[0][1])
            dist = (dx**2 + dy**2) ** 0.5
            print(f"FABE USD travel: {dist:.4f}m "
                  f"first={usd_positions[0]} last={usd_positions[-1]}", flush=True)

        if len(odom_positions) >= 2:
            dx = abs(odom_positions[-1][0] - odom_positions[0][0])
            dy = abs(odom_positions[-1][1] - odom_positions[0][1])
            dist = (dx**2 + dy**2) ** 0.5
            print(f"FABE odom travel: {dist:.4f}m "
                  f"first={odom_positions[0]} last={odom_positions[-1]}", flush=True)

        # Save frame comparison
        if cam_node.latest is not None:
            try:
                import cv2
                out_dir = Path("data/logs/recordings")
                out_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_dir / "fabe_final.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("FABE saved fabe_final.png", flush=True)
            except Exception as e:
                print(f"FABE cv2 error: {e}", flush=True)

    finally:
        print("FABE cleanup", flush=True)
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
