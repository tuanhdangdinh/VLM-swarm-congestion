"""Verify Fabric sync: check carb settings at each stage, try omni.physxfabric
after extension load, and read Fabric prim positions directly to see if physics
writes to Fabric.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_fabric_verify
"""
from pathlib import Path
import traceback


def main() -> None:
    try:
        _run()
    except Exception:
        traceback.print_exc()


def _check_carb(label: str) -> None:
    import carb
    s = carb.settings.get_settings()
    print(f"FABV [{label}] updateToUsd={s.get('/physics/updateToUsd')} "
          f"updateParticles={s.get('/physics/updateParticlesToUsd')} "
          f"updateVelocities={s.get('/physics/updateVelocitiesToUsd')}", flush=True)


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
    print("FABV app ready", flush=True)

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

        # Check carb settings before Fabric enable
        _check_carb("before-fabric-enable")

        import carb
        import omni.kit.app
        _settings = carb.settings.get_settings()
        _ext_mgr = omni.kit.app.get_app().get_extension_manager()
        result = _ext_mgr.set_extension_enabled_immediate("omni.physx.fabric", True)
        print(f"FABV enable omni.physx.fabric result={result}", flush=True)

        # Check if omni.physxfabric Python becomes available after extension load
        try:
            import omni.physxfabric
            iface = omni.physxfabric.get_physx_fabric_interface()
            print(f"FABV omni.physxfabric available! iface={iface}", flush=True)
        except Exception as e:
            print(f"FABV omni.physxfabric NOT available: {e}", flush=True)

        _check_carb("after-ext-enable-before-carb-set")

        _settings.set_bool("/physics/updateToUsd", False)
        _settings.set_bool("/physics/updateParticlesToUsd", False)
        _settings.set_bool("/physics/updateVelocitiesToUsd", False)
        _settings.set_bool("/physics/updateForceSensorsToUsd", False)
        _check_carb("after-carb-set")

        sim_ctx.play()
        _check_carb("after-play")  # ← key: did play reset the settings?

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        _check_carb("after-wait-for-topics")

        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("FABV driver started", flush=True)

        import numpy as np
        import threading
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_fabv")
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
            print("FABV ERROR: no camera frame during warmup", flush=True)
            return
        print(f"FABV warmup done shape={cam_node.latest.shape}", flush=True)

        # Try to read Fabric directly — check if robot prim positions change there
        try:
            import omni.fabric as _fabric
            _usd_ctx = _omni_usd.get_context()
            _stage = _usd_ctx.get_stage()

            # Try to get Fabric stage accessor
            try:
                from omni.fabric import StageReaderWriter, IPath
                fabric_stage = StageReaderWriter(_usd_ctx.get_stage_id())
                print("FABV omni.fabric StageReaderWriter available", flush=True)

                robot_path = f"/World/Robots/{config.scenario.robots[0].robot_id}/base_link"
                try:
                    prim_view = fabric_stage.get_prim(IPath(robot_path))
                    print(f"FABV Fabric prim at {robot_path}: {prim_view}", flush=True)
                except Exception as e:
                    print(f"FABV Fabric prim query failed: {e}", flush=True)
            except Exception as e:
                print(f"FABV StageReaderWriter not available: {e}", flush=True)

            # Also try usd_rt
            try:
                from pxr import Usd
                from omni.fabric import usd
                print(f"FABV omni.fabric.usd available: {dir(usd)}", flush=True)
            except Exception as e:
                print(f"FABV omni.fabric.usd not available: {e}", flush=True)

        except Exception as e:
            print(f"FABV omni.fabric import failed: {e}", flush=True)

        # Try SimulationManager.enable_fabric approach
        try:
            from isaacsim.core.simulation_manager import SimulationManager
            is_enabled = SimulationManager.is_fabric_enabled()
            print(f"FABV SimulationManager.is_fabric_enabled()={is_enabled}", flush=True)
        except Exception as e:
            print(f"FABV SimulationManager not available: {e}", flush=True)

        # Run 120 frames and track pixel mean + odom
        import omni.graph.core as og
        means = []
        odom_xs = []

        for i in range(120):
            app.update()
            rgb = cam_node.latest
            if rgb is not None:
                means.append(float(rgb.mean()))

            # Read odom from OmniGraph
            try:
                robot_id = config.scenario.robots[0].robot_id
                node_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"
                node = og.get_node_by_path(node_path)
                if node and node.is_valid():
                    pos = node.get_attribute("outputs:position").get()
                    if pos is not None:
                        odom_xs.append(float(pos[0]))
            except Exception:
                pass

            if i % 30 == 0:
                odom_x = odom_xs[-1] if odom_xs else None
                mean = means[-1] if means else None
                print(f"FABV i={i} msg_count={cam_node.count} "
                      f"mean={mean:.3f if mean is not None else 'N/A'} "
                      f"odom_x={odom_x:.4f if odom_x is not None else 'N/A'}", flush=True)

        _check_carb("end-of-loop")

        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            print(f"FABV done. max_mean_diff={max_diff:.4f}", flush=True)
            if max_diff > 0.5:
                print("FABV RESULT: camera IS changing!", flush=True)
            else:
                print("FABV RESULT: camera still static", flush=True)

        if len(odom_xs) >= 2:
            total_odom_travel = abs(odom_xs[-1] - odom_xs[0])
            print(f"FABV odom travel: {total_odom_travel:.4f}m "
                  f"(odom_x[0]={odom_xs[0]:.4f} odom_x[-1]={odom_xs[-1]:.4f})", flush=True)
            if total_odom_travel > 0.01:
                print("FABV ODOM: robot IS moving in PhysX", flush=True)
            else:
                print("FABV ODOM: robot NOT moving", flush=True)

    finally:
        print("FABV cleanup", flush=True)
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
