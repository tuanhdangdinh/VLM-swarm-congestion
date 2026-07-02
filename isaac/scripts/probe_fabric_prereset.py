"""Probe: enable Fabric BEFORE sim_ctx.reset() so PhysX bodies bind to Fabric.

Hypothesis: PhysX body→Fabric bindings are established at sim_ctx.reset().
If omni.physx.fabric is enabled AFTER reset(), bodies have no Fabric binding.

Order tested here:
  open_stage() → enable_extensions() → enable Fabric + carb settings
  → make_sim_context() → sim_ctx.reset() → play()

This differs from previous probes which enabled Fabric AFTER reset().

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_fabric_prereset
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
    print("PREP app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        import omni.usd as _omni_usd
        stage = _omni_usd.get_context().get_stage()
        R._set_timeline_window(stage)

        # *** Enable Fabric BEFORE sim_ctx.reset() ***
        import carb
        import omni.kit.app
        _settings = carb.settings.get_settings()
        _ext_mgr = omni.kit.app.get_app().get_extension_manager()
        result = _ext_mgr.set_extension_enabled_immediate("omni.physx.fabric", True)
        print(f"PREP enable omni.physx.fabric (pre-reset): result={result}", flush=True)

        try:
            from isaacsim.core.simulation_manager import SimulationManager
            SimulationManager.enable_fabric(True)
            print(f"PREP SimulationManager.enable_fabric done; is_enabled={SimulationManager.is_fabric_enabled()}", flush=True)
        except Exception as e:
            _settings.set_bool("/physics/updateToUsd", False)
            _settings.set_bool("/physics/updateParticlesToUsd", False)
            _settings.set_bool("/physics/updateVelocitiesToUsd", False)
            _settings.set_bool("/physics/updateForceSensorsToUsd", False)
            print(f"PREP used carb directly: {e}", flush=True)

        print(f"PREP /physics/updateToUsd before reset: {_settings.get('/physics/updateToUsd')}", flush=True)

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        # NOW make sim context and reset (physics bodies initialize WITH Fabric)
        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        print(f"PREP /physics/updateToUsd after reset: {_settings.get('/physics/updateToUsd')}", flush=True)

        R._add_scene_lighting(stage)
        R._wire_ros_graphs(config.scenario.robots)

        # Check usdrt initial position
        import usdrt
        stage_id = _omni_usd.get_context().get_stage_id()
        usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)
        robot_id = config.scenario.robots[0].robot_id
        base_link_path = f"/World/Robots/{robot_id}/Geometry/base_footprint/base_link"
        usdrt_prim = usdrt_stage.GetPrimAtPath(base_link_path)
        print(f"PREP usdrt prim valid: {usdrt_prim.IsValid()}", flush=True)

        def _read_fabric_x() -> float | None:
            try:
                attr = usdrt_prim.GetAttribute("xformOp:translate")
                if attr.IsValid():
                    val = attr.Get()
                    if val is not None:
                        return float(val[0])
                xfable = usdrt.UsdGeom.Xformable(usdrt_prim)
                t = xfable.ComputeLocalToWorldTransform(
                    usdrt.Usd.TimeCode.Default()).ExtractTranslation()
                return float(t[0])
            except Exception:
                return None

        x0_pre = _read_fabric_x()
        print(f"PREP Fabric x before play: {x0_pre}", flush=True)

        sim_ctx.play()
        print(f"PREP /physics/updateToUsd after play: {_settings.get('/physics/updateToUsd')}", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("PREP driver started", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_prep")
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
        print(f"PREP warmup done count={cam_node.count}", flush=True)

        import omni.graph.core as og
        odom_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"

        means = []
        fabric_xs = []
        odom_xs = []

        for i in range(120):
            app.update()

            if cam_node.latest is not None:
                means.append(float(cam_node.latest.mean()))

            fx = _read_fabric_x()
            fabric_xs.append(fx)

            try:
                node = og.get_node_by_path(odom_path)
                if node and node.is_valid():
                    pos = node.get_attribute("outputs:position").get()
                    if pos is not None:
                        odom_xs.append(float(pos[0]))
            except Exception:
                pass

            if i % 30 == 0:
                mean_s = f"{means[-1]:.3f}" if means else "N/A"
                fab_s = f"{fabric_xs[-1]:.4f}" if fabric_xs and fabric_xs[-1] is not None else "N/A"
                odom_s = f"{odom_xs[-1]:.4f}" if odom_xs else "N/A"
                print(f"PREP i={i} cam={mean_s} fabric_x={fab_s} odom_x={odom_s}", flush=True)

        print(f"PREP end: /physics/updateToUsd={_settings.get('/physics/updateToUsd')}", flush=True)

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            print(f"PREP camera max_mean_diff={max_diff:.4f} "
                  f"({'CHANGING!' if max_diff > 0.5 else 'static'})", flush=True)

        valid_fab = [x for x in fabric_xs if x is not None]
        if len(valid_fab) >= 2:
            dist = abs(valid_fab[-1] - valid_fab[0])
            print(f"PREP Fabric x-displacement: {dist:.4f}m "
                  f"first={valid_fab[0]:.4f} last={valid_fab[-1]:.4f} "
                  f"({'MOVING!' if dist > 0.01 else 'frozen'})", flush=True)
        else:
            print(f"PREP Fabric: only {len(valid_fab)} valid readings", flush=True)

        if len(odom_xs) >= 2:
            dist = abs(odom_xs[-1] - odom_xs[0])
            print(f"PREP odom x-displacement: {dist:.4f}m "
                  f"({'MOVING' if dist > 0.01 else 'frozen'})", flush=True)

        # Save comparison frame
        if cam_node.latest is not None:
            try:
                import cv2
                out_dir = Path("data/logs/recordings")
                out_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_dir / "prep_final.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("PREP saved prep_final.png", flush=True)
            except Exception as e:
                print(f"PREP cv2 error: {e}", flush=True)

    finally:
        print("PREP cleanup", flush=True)
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
