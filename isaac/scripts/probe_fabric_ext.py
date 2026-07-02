"""Probe: check omni.physx.fabric extension and carb physics settings.

Then enable Fabric and check if camera sees robot movement.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_fabric_ext
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
    print("FABEXT app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        import omni.usd as _omni_usd
        R._set_timeline_window(_omni_usd.get_context().get_stage())

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        R._add_scene_lighting(_omni_usd.get_context().get_stage())
        R._wire_ros_graphs(config.scenario.robots)

        # Check carb settings BEFORE play
        import carb
        settings = carb.settings.get_settings()
        update_to_usd = settings.get("/physics/updateToUsd")
        print(f"FABEXT /physics/updateToUsd = {update_to_usd}", flush=True)

        # Check if omni.physx.fabric extension exists
        import omni.kit.app
        ext_mgr = omni.kit.app.get_app().get_extension_manager()

        for ext_name in ["omni.physx.fabric", "omni.physics.fabric", "isaacsim.physics.fabric"]:
            try:
                enabled = ext_mgr.is_extension_enabled(ext_name)
                print(f"FABEXT ext {ext_name}: enabled={enabled}", flush=True)
            except Exception as e:
                print(f"FABEXT ext {ext_name}: query error: {e}", flush=True)

        # Try to enable omni.physx.fabric
        try:
            result = ext_mgr.set_extension_enabled_immediate("omni.physx.fabric", True)
            print(f"FABEXT enable omni.physx.fabric: result={result}", flush=True)
        except Exception as e:
            print(f"FABEXT enable omni.physx.fabric failed: {e}", flush=True)

        # Check carb settings AFTER enabling fabric
        update_to_usd2 = settings.get("/physics/updateToUsd")
        print(f"FABEXT /physics/updateToUsd after fabric enable = {update_to_usd2}", flush=True)

        sim_ctx.play()
        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)

        # Check carb settings AFTER play
        update_to_usd3 = settings.get("/physics/updateToUsd")
        print(f"FABEXT /physics/updateToUsd after play = {update_to_usd3}", flush=True)

        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("FABEXT driver started", flush=True)

        import numpy as np
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        import threading

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_fab_ext")
                from sensor_msgs.msg import Image as _Img
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
            print("FABEXT ERROR: no camera frame during warmup", flush=True)
            return
        print(f"FABEXT warmup done shape={cam_node.latest.shape}", flush=True)

        # Save frame 0
        out_dir = Path("data/logs/recordings")
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            import cv2
            cv2.imwrite(str(out_dir / "fabext_frame0.png"),
                        cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
            print("FABEXT saved frame0", flush=True)
        except Exception as e:
            print(f"FABEXT cv2 error: {e}", flush=True)

        means = []
        for i in range(120):
            app.update()
            rgb = cam_node.latest
            if rgb is not None:
                means.append(float(rgb.mean()))
            if i % 30 == 0:
                print(f"FABEXT i={i} msg_count={cam_node.count} "
                      f"mean={means[-1]:.3f}" if means else f"FABEXT i={i} no frame",
                      flush=True)

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            print(f"FABEXT done. max_mean_diff={max_diff:.4f}", flush=True)
            if max_diff > 0.5:
                print("FABEXT RESULT: camera IS changing — Fabric sync working!", flush=True)
            else:
                print("FABEXT RESULT: camera static — Fabric sync still broken", flush=True)

        # Save final frame
        if cam_node.latest is not None:
            try:
                cv2.imwrite(str(out_dir / "fabext_frame_final.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("FABEXT saved final frame", flush=True)
            except Exception:
                pass

    finally:
        print("FABEXT cleanup", flush=True)
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
