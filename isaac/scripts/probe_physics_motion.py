"""Probe: verify robots physically move by reading USD prim position each step.

Uses DEFAULT carb settings (updateToUsd=True) so PhysX writes to pxr USD.
Reads prim position via ComputeLocalToWorldTransform each frame.
Also reads OmniGraph odom outputs:position.

If prim position changes -> physics IS running, camera is the problem.
If prim position stays same -> physics NOT running (drive chain broken).

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_physics_motion
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
    print("PHYMO app ready", flush=True)

    watchdog_executor = None
    driver = None

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

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

        # Use DEFAULT settings (updateToUsd=True) so we can read positions via USD API
        import carb
        carb_settings = carb.settings.get_settings()
        print(f"PHYMO updateToUsd={carb_settings.get('/physics/updateToUsd')}", flush=True)

        sim_ctx.play()
        print("PHYMO play called", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        print("PHYMO ros topics ready", flush=True)

        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("PHYMO driver started", flush=True)

        # Warmup: 10 app.update() to let physics settle
        import time
        for _ in range(10):
            app.update()
            time.sleep(0.01)
        print("PHYMO warmup done", flush=True)

        # Read prim positions and odom each step
        from pxr import UsdGeom, Usd
        import omni.graph.core as og

        robot_0 = config.scenario.robots[0]
        robot_id = robot_0.robot_id

        # Find the robot prim
        robot_prim = None
        for ppath in [f"/World/Robots/{robot_id}/base_link",
                      f"/World/Robots/{robot_id}"]:
            p = stage.GetPrimAtPath(ppath)
            if p.IsValid():
                robot_prim = p
                print(f"PHYMO found prim at {ppath}", flush=True)
                break
        if robot_prim is None:
            print(f"PHYMO ERROR: no prim found for {robot_id}", flush=True)
            # List what's under /World/Robots
            robots_prim = stage.GetPrimAtPath("/World/Robots")
            if robots_prim.IsValid():
                for child in robots_prim.GetChildren():
                    print(f"PHYMO  child: {child.GetPath()}", flush=True)
            return

        odom_node_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"
        odom_node = og.get_node_by_path(odom_node_path)
        if odom_node is None or not odom_node.is_valid():
            print(f"PHYMO WARNING: odom node not found at {odom_node_path}", flush=True)

        positions_usd = []
        positions_odom = []

        for i in range(120):
            app.update()

            # Read USD prim position
            try:
                xf = UsdGeom.Xformable(robot_prim)
                t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                positions_usd.append((float(t[0]), float(t[1]), float(t[2])))
            except Exception as e:
                positions_usd.append(None)

            # Read OmniGraph odom
            try:
                if odom_node and odom_node.is_valid():
                    pos = odom_node.get_attribute("outputs:position").get()
                    if pos is not None:
                        positions_odom.append((float(pos[0]), float(pos[1]), float(pos[2])))
                    else:
                        positions_odom.append(None)
                else:
                    positions_odom.append(None)
            except Exception:
                positions_odom.append(None)

            if i % 30 == 0:
                usd_pos = positions_usd[-1]
                odom_pos = positions_odom[-1] if positions_odom else None
                usd_str = f"({usd_pos[0]:.4f},{usd_pos[1]:.4f})" if usd_pos else "N/A"
                odom_str = f"({odom_pos[0]:.4f},{odom_pos[1]:.4f})" if odom_pos else "N/A"
                print(f"PHYMO i={i} usd={usd_str} odom={odom_str}", flush=True)

        # Summarize
        valid_usd = [p for p in positions_usd if p is not None]
        valid_odom = [p for p in positions_odom if p is not None]

        if len(valid_usd) >= 2:
            dx = abs(valid_usd[-1][0] - valid_usd[0][0])
            dy = abs(valid_usd[-1][1] - valid_usd[0][1])
            dist = (dx**2 + dy**2) ** 0.5
            print(f"PHYMO USD displacement: {dist:.4f}m "
                  f"(first={valid_usd[0]} last={valid_usd[-1]})", flush=True)
            if dist > 0.01:
                print("PHYMO RESULT: physics IS moving robots (USD position changed)", flush=True)
            else:
                print("PHYMO RESULT: physics NOT moving robots (USD position frozen)", flush=True)

        if len(valid_odom) >= 2:
            dx = abs(valid_odom[-1][0] - valid_odom[0][0])
            dy = abs(valid_odom[-1][1] - valid_odom[0][1])
            dist = (dx**2 + dy**2) ** 0.5
            print(f"PHYMO odom displacement: {dist:.4f}m "
                  f"(first={valid_odom[0]} last={valid_odom[-1]})", flush=True)

    finally:
        print("PHYMO cleanup", flush=True)
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
