"""Minimal camera probe: run 20 frames, print every frame, save 3 PNGs.

No ArUco. No complex logic. Just show whether the camera image changes.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_cam_minimal
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
    print("CAMMIN app ready", flush=True)

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
        sim_ctx.play()

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)

        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("CAMMIN driver started", flush=True)

        import numpy as np
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        import threading

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_cam_min")
                from sensor_msgs.msg import Image as _Img
                self.latest: np.ndarray | None = None
                self.count: int = 0
                self.create_subscription(_Img, "/camera/image_raw", self._cb, 10)

            def _cb(self, msg) -> None:
                h, w = msg.height, msg.width
                raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
                self.latest = np.ascontiguousarray(raw.reshape(h, w, 3))
                self.count += 1

        print("CAMMIN creating cam_node...", flush=True)
        cam_node = _CamNode()
        cam_exec = SingleThreadedExecutor()
        cam_exec.add_node(cam_node)
        cam_thread = threading.Thread(target=cam_exec.spin, daemon=True)
        cam_thread.start()
        print("CAMMIN cam_node started", flush=True)

        # Warmup
        import time
        t_warm = time.monotonic()
        warmup_frames = 0
        while cam_node.latest is None and time.monotonic() - t_warm < 10.0:
            app.update()
            warmup_frames += 1
        if cam_node.latest is None:
            print("CAMMIN ERROR: no camera frame during warmup!", flush=True)
            return
        print(f"CAMMIN warmup done: app_frames={warmup_frames} msg_count={cam_node.count} "
              f"shape={cam_node.latest.shape}", flush=True)

        # Save frame 0
        out_dir = Path("data/logs/recordings")
        out_dir.mkdir(parents=True, exist_ok=True)

        print("CAMMIN saving frame 0...", flush=True)
        try:
            import cv2
            cv2.imwrite(str(out_dir / "cam_frame0.png"),
                        cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
            print("CAMMIN frame0 saved", flush=True)
        except Exception as e:
            print(f"CAMMIN cv2 save error: {e}", flush=True)

        prev_means = []

        print("CAMMIN starting frame loop...", flush=True)
        for i in range(120):
            try:
                app.update()
            except Exception as e:
                print(f"CAMMIN app.update() error at i={i}: {e}", flush=True)
                traceback.print_exc()
                break

            rgb = cam_node.latest
            mean_val = float(rgb.mean()) if rgb is not None else -1.0
            prev_means.append(mean_val)

            if i % 20 == 0:
                print(f"CAMMIN i={i} msg_count={cam_node.count} "
                      f"mean={mean_val:.3f}", flush=True)
                if rgb is not None and i in (40, 100):
                    try:
                        import cv2 as _cv2
                        fname = out_dir / f"cam_frame{i}.png"
                        _cv2.imwrite(str(fname),
                                     _cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                        print(f"CAMMIN saved {fname}", flush=True)
                    except Exception as e:
                        print(f"CAMMIN save error: {e}", flush=True)

        if len(prev_means) > 1:
            diffs = [abs(prev_means[j] - prev_means[j-1]) for j in range(1, len(prev_means))]
            max_diff = max(diffs)
            print(f"CAMMIN done. max_mean_diff={max_diff:.4f} "
                  f"(>0.01 means image is changing)", flush=True)
        else:
            print("CAMMIN done (no frame data collected)", flush=True)

    finally:
        print("CAMMIN cleanup...", flush=True)
        try:
            import omni.timeline
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        try:
            watchdog_executor.shutdown()
        except Exception:
            pass
        try:
            driver.request_stop()
        except Exception:
            pass
        app.close()
        print("CAMMIN closed", flush=True)


if __name__ == "__main__":
    main()
