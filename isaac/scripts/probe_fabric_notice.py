"""Probe: enable SimulationManager.enable_fabric_usd_notice_handler for USD→Fabric sync.

Root cause identified:
- Newton writes correct world positions to pxr USD (confirmed: 0.56m travel)
- RTX renderer reads Fabric (usdrt_delegate)
- USD→Fabric sync requires the "fabric USD notice handler" to be enabled
- SimulationManager.enable_fabric_usd_notice_handler(stage_id, True) enables this sync

The comment in simulation_manager.py:
  "PhysX only - Newton handles fabric updates differently"
  cls._physx_fabric_interface.update(...)  # only for PhysX

Newton "handles fabric differently" = Newton writes to USD + fabric_usd_notice_handler
syncs USD → Fabric. The handler must be enabled for this chain to work.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_fabric_notice
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
    print("FNOT app ready", flush=True)

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

        # Check current state of fabric USD notice handler
        from isaacsim.core.simulation_manager import SimulationManager
        handler_enabled_before = SimulationManager.is_fabric_usd_notice_handler_enabled(stage_id)
        print(f"FNOT fabric_usd_notice_handler before: {handler_enabled_before}", flush=True)

        # Enable it
        SimulationManager.enable_fabric_usd_notice_handler(stage_id, True)
        handler_enabled_after = SimulationManager.is_fabric_usd_notice_handler_enabled(stage_id)
        print(f"FNOT fabric_usd_notice_handler after enable: {handler_enabled_after}", flush=True)

        import carb
        _settings = carb.settings.get_settings()
        print(f"FNOT updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        robot_id = config.scenario.robots[0].robot_id
        base_link_path = f"/World/Robots/{robot_id}/Geometry/base_footprint/base_link"

        from pxr import UsdGeom, Usd
        base_link_prim = stage.GetPrimAtPath(base_link_path)
        print(f"FNOT base_link valid: {base_link_prim.IsValid()}", flush=True)

        # Check usdrt fabric position
        import usdrt
        usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)
        usdrt_prim = usdrt_stage.GetPrimAtPath(base_link_path)
        if usdrt_prim.IsValid():
            fa = usdrt_prim.GetAttribute("xformOp:translate")
            if fa.IsValid():
                print(f"FNOT initial fabric translate: {fa.Get()}", flush=True)

        sim_ctx.play()
        print(f"FNOT after play: updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        # Check again after play
        handler_after_play = SimulationManager.is_fabric_usd_notice_handler_enabled(stage_id)
        print(f"FNOT fabric_usd_notice_handler after play: {handler_after_play}", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("FNOT driver started", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_fnot")
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
        print(f"FNOT warmup done count={cam_node.count}", flush=True)

        import omni.graph.core as og
        odom_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"

        means = []
        usd_xs = []
        fabric_xs = []
        odom_xs = []
        first_frame: np.ndarray | None = None

        for i in range(200):
            app.update()

            if cam_node.latest is not None:
                m = float(cam_node.latest.mean())
                means.append(m)
                if first_frame is None:
                    first_frame = cam_node.latest.copy()

            # pxr USD position
            if base_link_prim.IsValid():
                try:
                    xf = UsdGeom.Xformable(base_link_prim)
                    t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                    usd_xs.append(float(t[0]))
                except Exception:
                    usd_xs.append(None)

            # Fabric position
            if usdrt_prim.IsValid():
                try:
                    fa = usdrt_prim.GetAttribute("xformOp:translate")
                    if fa.IsValid():
                        val = fa.Get()
                        if val is not None:
                            fabric_xs.append(float(val[0]))
                        else:
                            fabric_xs.append(None)
                    else:
                        fabric_xs.append(None)
                except Exception:
                    fabric_xs.append(None)

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
                usd_s = (f"{usd_xs[-1]:.4f}" if usd_xs and usd_xs[-1] is not None else "N/A")
                fab_s = (f"{fabric_xs[-1]:.4f}"
                         if fabric_xs and fabric_xs[-1] is not None else "N/A")
                odom_s = f"{odom_xs[-1]:.4f}" if odom_xs else "N/A"
                print(f"FNOT i={i} cam={mean_s} usd_x={usd_s} fab_x={fab_s} odom_x={odom_s}",
                      flush=True)

        print(f"FNOT total frames: {cam_node.count}", flush=True)

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            result = "CHANGING!" if max_diff > 0.5 else "static"
            print(f"FNOT camera max_mean_diff={max_diff:.4f} ({result})", flush=True)
            diff_fl = abs(means[-1] - means[0])
            print(f"FNOT camera first_vs_last_diff={diff_fl:.4f}", flush=True)

        valid_usd = [x for x in usd_xs if x is not None]
        if len(valid_usd) >= 2:
            dist = abs(valid_usd[-1] - valid_usd[0])
            print(f"FNOT USD x-displacement: {dist:.4f}m ({('MOVING!' if dist > 0.01 else 'FROZEN')})",
                  flush=True)

        valid_fab = [x for x in fabric_xs if x is not None]
        if len(valid_fab) >= 2:
            dist = abs(valid_fab[-1] - valid_fab[0])
            print(f"FNOT Fabric x-displacement: {dist:.4f}m ({('MOVING!' if dist > 0.01 else 'FROZEN')})",
                  flush=True)
        else:
            print(f"FNOT Fabric: {len(valid_fab)} valid readings", flush=True)

        if len(odom_xs) >= 2:
            dist = abs(odom_xs[-1] - odom_xs[0])
            print(f"FNOT odom x-displacement: {dist:.4f}m", flush=True)

        try:
            import cv2
            out_dir = Path("data/logs/recordings")
            out_dir.mkdir(parents=True, exist_ok=True)
            if first_frame is not None:
                cv2.imwrite(str(out_dir / "fnot_first.png"),
                            cv2.cvtColor(first_frame, cv2.COLOR_RGB2BGR))
                print("FNOT saved fnot_first.png", flush=True)
            if cam_node.latest is not None:
                cv2.imwrite(str(out_dir / "fnot_last.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("FNOT saved fnot_last.png", flush=True)
        except Exception as e:
            print(f"FNOT cv2 error: {e}", flush=True)

    finally:
        print("FNOT cleanup", flush=True)
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
