"""Probe: does the ROS camera image change as robots drive?

Runs the sim, starts the drive chain, and checks whether successive camera
frames are pixel-identical. If images change, Fabric is syncing physics→render.
If they're static, something is wrong with the render pipeline.

Also runs ArUco detection every 50 frames to check marker visibility.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_cam_change
"""
from pathlib import Path


def main() -> None:
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
    print("CAMCHG app ready", flush=True)

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
        print("CAMCHG driver+watchdog started", flush=True)

        import numpy as np
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        import threading

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_cam_chg")
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
            print("CAMCHG ERROR: no camera frame during warmup", flush=True)
            return
        print(f"CAMCHG warmup done shape={cam_node.latest.shape} msg_count={cam_node.count}",
              flush=True)

        # ArUco setup
        import cv2
        from isaac.vgu_sim.paths import aruco_dict_name
        _dict_id = getattr(cv2.aruco, aruco_dict_name())
        aruco_dict = cv2.aruco.getPredefinedDictionary(_dict_id)
        aruco_params = cv2.aruco.DetectorParameters()

        def _detect(rgb: np.ndarray) -> dict:
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=aruco_params)
            if ids is None:
                return {}
            return {int(mid): (float(c[0][:, 0].mean()), float(c[0][:, 1].mean()))
                    for c, mid in zip(corners, ids.flatten())}

        prev_frame: np.ndarray | None = None
        change_count = 0
        same_count = 0

        for frame_idx in range(300):
            app.update()

            rgb = cam_node.latest
            if rgb is None:
                continue

            if prev_frame is not None:
                diff = np.abs(rgb.astype(int) - prev_frame.astype(int))
                max_diff = int(diff.max())
                changed_pixels = int((diff > 5).any(axis=2).sum())
                if changed_pixels > 100:
                    change_count += 1
                else:
                    same_count += 1

                if frame_idx % 50 == 0:
                    detections = _detect(rgb)
                    print(
                        f"CAMCHG frame={frame_idx} "
                        f"max_diff={max_diff} changed_px={changed_pixels} "
                        f"total_changes={change_count} total_same={same_count} "
                        f"msg_count={cam_node.count} "
                        f"aruco={detections}",
                        flush=True,
                    )
            elif frame_idx % 50 == 0:
                detections = _detect(rgb)
                print(f"CAMCHG frame={frame_idx} (first) aruco={detections}", flush=True)

            prev_frame = rgb.copy()

        if change_count > 0:
            print(f"CAMCHG RESULT: camera IS changing ({change_count} frames changed, "
                  f"{same_count} same) — Fabric sync OK", flush=True)
        else:
            print(f"CAMCHG RESULT: camera STATIC ({same_count} frames unchanged) "
                  f"— Fabric sync BROKEN", flush=True)

    finally:
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


if __name__ == "__main__":
    main()
