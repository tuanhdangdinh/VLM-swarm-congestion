"""Probe: kinematic USD prim update — write OmniGraph odom positions to USD each frame.

IsaacComputeOdometry reads from PhysX directly (confirmed working in prior probes)
and outputs world-frame or integrated position. We read that and manually set the
USD prim translation so the camera renderer sees robots at updated positions.

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_kinematic
"""
import sys
from pathlib import Path


def _get_odom_node(robot_id: str):
    import omni.graph.core as og
    node_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"
    node = og.get_node_by_path(node_path)
    if node is None or not node.is_valid():
        print(f"KINEMATIC ERROR: odom node not found at {node_path}", flush=True)
        return None
    return node


def _read_odom_pos(node) -> tuple[float, float, float] | None:
    try:
        pos = node.get_attribute("outputs:position").get()
        if pos is None:
            return None
        return (float(pos[0]), float(pos[1]), float(pos[2]))
    except Exception as e:
        print(f"KINEMATIC ERROR reading odom: {e}", flush=True)
        return None


def _set_prim_translate(prim, x: float, y: float, z: float) -> None:
    from pxr import UsdGeom, Gf
    xf = UsdGeom.Xformable(prim)
    ops = xf.GetOrderedXformOps()
    for op in ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            op.Set(Gf.Vec3d(x, y, z))
            return
    # No translate op found — add one
    op = xf.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionDouble)
    op.Set(Gf.Vec3d(x, y, z))


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
    print("KINEMATIC app ready", flush=True)

    try:
        R._open_stage(config.scenario_path)
        R._enable_extensions()

        import omni.usd as _omni_usd
        from pxr import UsdGeom, Gf
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
        print("KINEMATIC driver started", flush=True)

        # Warm up — let the drive chain settle
        for _ in range(30):
            app.update()

        stage = _omni_usd.get_context().get_stage()

        # Get chassis prims and odom nodes
        chassis_info = {}
        for r in config.scenario.robots:
            prim = None
            for path in [f"/World/Robots/{r.robot_id}/base_link",
                         f"/World/Robots/{r.robot_id}"]:
                p = stage.GetPrimAtPath(path)
                if p.IsValid():
                    prim = p
                    break
            if prim is None:
                print(f"KINEMATIC ERROR: no prim for {r.robot_id}", flush=True)
                continue

            odom_node = _get_odom_node(r.robot_id)
            if odom_node is None:
                continue

            # USD initial position
            xf = UsdGeom.Xformable(prim)
            t = xf.ComputeLocalToWorldTransform(0.0).ExtractTranslation()
            usd_init = (float(t[0]), float(t[1]), float(t[2]))

            # Odom position right now (after warmup) — this is the baseline
            odom_init = _read_odom_pos(odom_node)
            if odom_init is None:
                odom_init = (0.0, 0.0, 0.0)

            chassis_info[r.robot_id] = {
                "prim": prim,
                "odom_node": odom_node,
                "usd_init": usd_init,
                "odom_init": odom_init,
            }
            print(
                f"KINEMATIC {r.robot_id} usd_init=({usd_init[0]:.3f},{usd_init[1]:.3f},{usd_init[2]:.3f}) "
                f"odom_init=({odom_init[0]:.3f},{odom_init[1]:.3f},{odom_init[2]:.3f})",
                flush=True,
            )

        import omni.timeline
        tl = omni.timeline.get_timeline_interface()

        for frame in range(300):
            app.update()

            # After each physics step, read odom and update USD prim position
            for rid, info in chassis_info.items():
                odom_pos = _read_odom_pos(info["odom_node"])
                if odom_pos is None:
                    continue
                ox, oy, oz = odom_pos
                ix, iy, iz = info["odom_init"]
                ux, uy, uz = info["usd_init"]
                # Displacement from odom baseline + USD initial position
                new_x = ux + (ox - ix)
                new_y = uy + (oy - iy)
                new_z = uz + (oz - iz)
                _set_prim_translate(info["prim"], new_x, new_y, new_z)

            if frame % 60 == 0:
                for rid, info in chassis_info.items():
                    odom_pos = _read_odom_pos(info["odom_node"])
                    xf = UsdGeom.Xformable(info["prim"])
                    tc = tl.get_current_time() * tl.get_time_codes_per_seconds()
                    t = xf.ComputeLocalToWorldTransform(tc).ExtractTranslation()
                    print(
                        f"CHECK frame={frame} {rid} odom=({odom_pos[0]:.3f},{odom_pos[1]:.3f}) "
                        f"usd_pos=({t[0]:.3f},{t[1]:.3f})",
                        flush=True,
                    )

        print("KINEMATIC done", flush=True)

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
