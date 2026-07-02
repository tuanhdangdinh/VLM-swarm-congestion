"""Probe: does omni.physics.stageupdate fix chassis USD position sync?

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_stageupdate
"""
import sys
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
    print("PROBE app ready", flush=True)

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        # Enable stageupdate AFTER other extensions (requires omni.kit.app runtime)
        import omni.kit.app
        mgr = omni.kit.app.get_app().get_extension_manager()
        su = mgr.set_extension_enabled_immediate("omni.physics.stageupdate", True)
        print(f"PROBE stageupdate enabled={su}", flush=True)

        import omni.usd as _omni_usd
        from pxr import UsdGeom
        R._set_timeline_window(_omni_usd.get_context().get_stage())

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz

        sim_ctx = R._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        R._add_scene_lighting(_omni_usd.get_context().get_stage())
        R._wire_ros_graphs(config.scenario.robots)
        sim_ctx.play()

        # Wait for ROS topics (verifies drive graphs wired)
        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)

        # Start watchdog + driver
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("PROBE driver started", flush=True)

        # Get robot chassis prims
        stage = _omni_usd.get_context().get_stage()
        chassis_prims = {}
        for r in config.scenario.robots:
            for path_candidate in [
                f"/World/Robots/{r.robot_id}/base_link",
                f"/World/Robots/{r.robot_id}",
            ]:
                prim = stage.GetPrimAtPath(path_candidate)
                if prim.IsValid():
                    chassis_prims[r.robot_id] = prim
                    print(f"PROBE chassis {r.robot_id} at {path_candidate}", flush=True)
                    break

        import omni.timeline
        tl = omni.timeline.get_timeline_interface()

        for frame in range(200):
            app.update()

            if frame % 40 == 0:
                tc = tl.get_current_time() * tl.get_time_codes_per_seconds()
                for rid, prim in chassis_prims.items():
                    xf = UsdGeom.Xformable(prim)
                    pos_t0 = xf.ComputeLocalToWorldTransform(0.0).ExtractTranslation()
                    pos_tc = xf.ComputeLocalToWorldTransform(tc).ExtractTranslation()
                    print(
                        f"POS frame={frame} tc={tc:.1f} {rid} "
                        f"t0=({pos_t0[0]:.4f},{pos_t0[2]:.4f}) "
                        f"tc=({pos_tc[0]:.4f},{pos_tc[2]:.4f})",
                        flush=True,
                    )

        print("PROBE done", flush=True)

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
