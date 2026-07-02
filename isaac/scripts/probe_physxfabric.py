"""Probe: does physxfabric.update() in a POST_PHYSICS_STEP callback fix the camera view?

Checks three preconditions explicitly:
  1. Whether Fabric writeback is enabled (and enables it if not).
  2. Whether the physxfabric interface is importable and callable.
  3. Whether the callback fires at all.

Judges success via ArUco detection on /camera/image_raw — not via
ComputeLocalToWorldTransform (which reads pxr USD, not Fabric).

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_physxfabric
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
    print("PROBE_FAB app ready", flush=True)

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

        # --- Precondition 1: check and enable Fabric writeback ---
        fab_enabled = False
        try:
            fab_enabled = sim_ctx.is_fabric_enabled()
            print(f"PROBE_FAB fabric already enabled: {fab_enabled}", flush=True)
        except AttributeError:
            print("PROBE_FAB sim_ctx has no is_fabric_enabled()", flush=True)
        if not fab_enabled:
            try:
                sim_ctx.enable_fabric()
                fab_enabled = True
                print("PROBE_FAB enable_fabric() called OK", flush=True)
            except Exception as exc:
                print(f"PROBE_FAB enable_fabric() failed: {exc}", flush=True)

        sim_ctx.play()
        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)

        # --- Precondition 2: import physxfabric ---
        _fabric_iface = None
        try:
            import omni.physxfabric
            _fabric_iface = omni.physxfabric.get_physx_fabric_interface()
            print(f"PROBE_FAB physxfabric interface: {_fabric_iface}", flush=True)
        except Exception as exc:
            print(f"PROBE_FAB physxfabric NOT available: {exc}", flush=True)

        # --- Precondition 3: register POST_PHYSICS_STEP callback ---
        _cb_count = [0]
        _sim_t = [0.0]

        def _post_phys(step_dt, context):
            _cb_count[0] += 1
            if _fabric_iface is not None:
                try:
                    _fabric_iface.update(_sim_t[0], step_dt)
                except Exception as exc:
                    if _cb_count[0] <= 3:
                        print(f"PROBE_FAB fabric.update error: {exc}", flush=True)
            _sim_t[0] += step_dt

        import omni.physx
        _physx_sub = omni.physx.get_physx_simulation_interface().subscribe_physics_on_step_events(
            on_update=_post_phys, pre_step=False
        )
        print("PROBE_FAB physics callback registered", flush=True)

        # Start drive chain.
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)
        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("PROBE_FAB driver+watchdog started", flush=True)

        # Camera subscriber — judge success via ArUco detection.
        import numpy as np
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        import threading

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_fab_cam")
                from sensor_msgs.msg import Image as _Img
                self.latest: np.ndarray | None = None
                self.create_subscription(_Img, "/camera/image_raw", self._cb, 10)

            def _cb(self, msg) -> None:
                h, w = msg.height, msg.width
                raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
                self.latest = np.ascontiguousarray(raw.reshape(h, w, 3))

        cam_node = _CamNode()
        cam_exec = SingleThreadedExecutor()
        cam_exec.add_node(cam_node)
        cam_thread = threading.Thread(target=cam_exec.spin, daemon=True)
        cam_thread.start()

        # Warm up.
        import time
        t_warm = time.monotonic()
        while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
            app.update()
        if cam_node.latest is None:
            print("PROBE_FAB ERROR: no camera frame during warmup", flush=True)
            return
        print(f"PROBE_FAB cam warmup done; cb_count={_cb_count[0]}", flush=True)

        # ArUco setup.
        import cv2
        from isaac.vgu_sim.paths import aruco_dict_name
        _dict_id = getattr(cv2.aruco, aruco_dict_name())
        aruco_dict = cv2.aruco.getPredefinedDictionary(_dict_id)
        aruco_params = cv2.aruco.DetectorParameters()

        def _detect(rgb: np.ndarray):
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=aruco_params)
            if ids is None:
                return {}
            result = {}
            for corner, mid in zip(corners, ids.flatten()):
                cx = float(corner[0][:, 0].mean())
                cy = float(corner[0][:, 1].mean())
                result[int(mid)] = (cx, cy)
            return result

        # Run 200 frames and report ArUco pixel positions every 50.
        prev_rgb = None
        for frame in range(200):
            app.update()
            if frame % 50 == 0:
                rgb = cam_node.latest
                if rgb is not None:
                    detections = _detect(rgb)
                    changed = "CHANGED" if (prev_rgb is not None and
                                            not np.array_equal(rgb, prev_rgb)) else "same"
                    print(
                        f"PROBE_FAB frame={frame} cb={_cb_count[0]} "
                        f"cam_img={changed} "
                        f"detections={detections}",
                        flush=True,
                    )
                    prev_rgb = rgb.copy()
                else:
                    print(f"PROBE_FAB frame={frame} cam=None", flush=True)

        print(f"PROBE_FAB done. total_cb_fires={_cb_count[0]}", flush=True)

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
