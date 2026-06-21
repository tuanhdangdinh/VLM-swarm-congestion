"""Probe: write WORLD position (not local) to Fabric after each step.

Root cause: enable_fabric_usd_notice_handler syncs LOCAL USD translate to Fabric.
With omni:fabric:resetXformStack=True on base_link, Fabric uses that local value
as the WORLD position for rendering. So robots render at x≈0 instead of x=±0.6.

Fix: after each app.update(), read WORLD position from pxr USD
(ComputeLocalToWorldTransform) and write it to Fabric xformOp:translate.

If camera shows movement → this confirms the root cause and fixes it.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_world_fabric
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
    print("WFAB app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        import omni.usd as _omni_usd
        stage = _omni_usd.get_context().get_stage()
        stage_id = _omni_usd.get_context().get_stage_id()
        R._set_timeline_window(stage)

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        R._add_scene_lighting(stage)
        R._wire_ros_graphs(config.scenario.robots)

        # Enable USD→Fabric notice handler
        from isaacsim.core.simulation_manager import SimulationManager
        SimulationManager.enable_fabric_usd_notice_handler(stage_id, True)
        print(f"WFAB notice handler: {SimulationManager.is_fabric_usd_notice_handler_enabled(stage_id)}", flush=True)

        # Setup pxr USD and usdrt Fabric refs for ALL robots
        from pxr import UsdGeom, Usd
        import usdrt

        usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)

        robot_prims = []  # (usd_prim, usdrt_prim, robot_id)
        for robot in config.scenario.robots:
            rid = robot.robot_id
            base_link_path = f"/World/Robots/{rid}/Geometry/base_footprint/base_link"
            usd_prim = stage.GetPrimAtPath(base_link_path)
            ur_prim = usdrt_stage.GetPrimAtPath(base_link_path)
            print(f"WFAB robot {rid}: usd={usd_prim.IsValid()} usdrt={ur_prim.IsValid()}", flush=True)

            if usd_prim.IsValid():
                xf = UsdGeom.Xformable(usd_prim)
                t0 = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                print(f"WFAB {rid} initial world pos: ({float(t0[0]):.4f}, {float(t0[1]):.4f}, {float(t0[2]):.4f})", flush=True)

            if usd_prim.IsValid() and ur_prim.IsValid():
                fa = ur_prim.GetAttribute("xformOp:translate")
                if fa.IsValid():
                    print(f"WFAB {rid} initial fabric translate: {fa.Get()}", flush=True)
                robot_prims.append((usd_prim, ur_prim, rid))

        sim_ctx.play()
        print("WFAB play started", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("WFAB driver started", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_wfab")
                self.latest: np.ndarray | None = None
                self.count: int = 0
                self.frames: list = []
                self.create_subscription(_Img, "/camera/image_raw", self._cb, 10)

            def _cb(self, msg) -> None:
                h, w = msg.height, msg.width
                raw = np.frombuffer(bytes(msg.data), dtype=np.uint8)
                frame = np.ascontiguousarray(raw.reshape(h, w, 3))
                self.latest = frame
                self.count += 1
                if self.count in (1, 5, 10, 20, 50, 100):
                    self.frames.append((self.count, frame.copy()))

        cam_node = _CamNode()
        cam_exec = SingleThreadedExecutor()
        cam_exec.add_node(cam_node)
        cam_thread = threading.Thread(target=cam_exec.spin, daemon=True)
        cam_thread.start()

        import time
        t_warm = time.monotonic()
        while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
            app.update()
        print(f"WFAB warmup done count={cam_node.count}", flush=True)

        import omni.graph.core as og
        odom_path = f"/World/ROSGraphs/{config.scenario.robots[0].robot_id}/drive_graph/odom_compute"

        def _write_world_to_fabric() -> None:
            """After notice handler syncs local translate, overwrite with WORLD position."""
            for usd_prim, ur_prim, rid in robot_prims:
                try:
                    xf = UsdGeom.Xformable(usd_prim)
                    t = xf.ComputeLocalToWorldTransform(
                        Usd.TimeCode.Default()).ExtractTranslation()
                    fa = ur_prim.GetAttribute("xformOp:translate")
                    if fa.IsValid():
                        # Write world position as tuple (avoids usdrt.Gf import issues)
                        fa.Set((float(t[0]), float(t[1]), float(t[2])))
                except Exception as e:
                    print(f"WFAB write error {rid}: {e}", flush=True)

        means = []
        odom_xs = []
        first_frame: np.ndarray | None = None
        world_xs = {r.robot_id: [] for r in config.scenario.robots}

        for i in range(250):
            app.update()

            # Write WORLD position to Fabric (overrides notice handler's local write)
            _write_world_to_fabric()

            if cam_node.latest is not None:
                m = float(cam_node.latest.mean())
                means.append(m)
                if first_frame is None:
                    first_frame = cam_node.latest.copy()

            # Track world positions
            for usd_prim, _, rid in robot_prims:
                try:
                    xf = UsdGeom.Xformable(usd_prim)
                    t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                    world_xs[rid].append(float(t[0]))
                except Exception:
                    pass

            try:
                node = og.get_node_by_path(odom_path)
                if node and node.is_valid():
                    pos = node.get_attribute("outputs:position").get()
                    if pos is not None:
                        odom_xs.append(float(pos[0]))
            except Exception:
                pass

            if i % 50 == 0:
                mean_s = f"{means[-1]:.3f}" if means else "N/A"
                odom_s = f"{odom_xs[-1]:.4f}" if odom_xs else "N/A"
                wx = {}
                for rid, xs in world_xs.items():
                    wx[rid] = f"{xs[-1]:.4f}" if xs else "N/A"
                print(f"WFAB i={i} cam={mean_s} odom_x={odom_s} world_x={wx}", flush=True)

        print(f"WFAB total camera frames: {cam_node.count}", flush=True)

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            result = "CHANGING!" if max_diff > 0.5 else "static"
            print(f"WFAB camera max_mean_diff={max_diff:.4f} ({result})", flush=True)
            diff_fl = abs(means[-1] - means[0])
            print(f"WFAB camera first_vs_last_diff={diff_fl:.4f}", flush=True)

        for rid, xs in world_xs.items():
            if len(xs) >= 2:
                dist = abs(xs[-1] - xs[0])
                print(f"WFAB {rid} world x-displacement: {dist:.4f}m "
                      f"first={xs[0]:.4f} last={xs[-1]:.4f} "
                      f"({'MOVING!' if dist > 0.01 else 'FROZEN'})", flush=True)

        if len(odom_xs) >= 2:
            dist = abs(odom_xs[-1] - odom_xs[0])
            print(f"WFAB odom x-displacement: {dist:.4f}m", flush=True)

        # Save frames
        try:
            import cv2
            out_dir = Path("data/logs/recordings")
            out_dir.mkdir(parents=True, exist_ok=True)

            if first_frame is not None:
                cv2.imwrite(str(out_dir / "wfab_first.png"),
                            cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR))
                print("WFAB saved wfab_first.png", flush=True)

            if cam_node.latest is not None:
                cv2.imwrite(str(out_dir / "wfab_last.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("WFAB saved wfab_last.png", flush=True)

            for count, frame in cam_node.frames:
                cv2.imwrite(str(out_dir / f"wfab_frame{count:03d}.png"),
                            cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            if cam_node.frames:
                print(f"WFAB saved {len(cam_node.frames)} keyed frames", flush=True)

        except Exception as e:
            print(f"WFAB cv2 error: {e}", flush=True)

    finally:
        print("WFAB cleanup", flush=True)
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
