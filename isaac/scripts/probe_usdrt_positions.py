"""Probe: read Fabric positions via usdrt to verify PhysX→Fabric sync.

Also enumerates children of /World/Robots/robot_1 to find articulation root.
Also tries SimulationManager.enable_fabric(True) after extension load.

Key questions:
1. Is Fabric actually getting PhysX position updates?
2. What is the correct physics body prim path?
3. Does SimulationManager.enable_fabric() work after extension is loaded?

Run on host:
    source /home/ubuntu/IsaacSim/setup_ros_env.sh
    export PYTHONPATH="/home/ubuntu/vgu-vlm-swarm/ros2_ws/src/swarm_perception:${PYTHONPATH:-}"
    cd /home/ubuntu/vgu-vlm-swarm
    /home/ubuntu/IsaacSim/python.sh -m isaac.scripts.probe_usdrt_positions
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
    print("USDRT app ready", flush=True)

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

        # --- Step 1: Enumerate robot prim children to find articulation root ---
        robot_id = config.scenario.robots[0].robot_id
        robot_root_path = f"/World/Robots/{robot_id}"
        robot_root = stage.GetPrimAtPath(robot_root_path)
        print(f"USDRT robot root prim valid: {robot_root.IsValid()}", flush=True)

        if robot_root.IsValid():
            print(f"USDRT children of {robot_root_path}:", flush=True)
            for child in robot_root.GetChildren():
                cpath = child.GetPath()
                apis = child.GetAppliedSchemas()
                print(f"  {cpath}  type={child.GetTypeName()}  apis={apis}", flush=True)
                # also show grandchildren
                for gc in child.GetChildren():
                    gcapis = gc.GetAppliedSchemas()
                    print(f"    {gc.GetPath()}  type={gc.GetTypeName()}  apis={gcapis}", flush=True)

        # Find the articulation root prim
        from pxr import UsdPhysics, UsdGeom, Usd
        articulation_prim = None
        for ppath_candidate in [
            f"/World/Robots/{robot_id}/base_footprint",
            f"/World/Robots/{robot_id}/base_link",
            f"/World/Robots/{robot_id}",
        ]:
            p = stage.GetPrimAtPath(ppath_candidate)
            if p.IsValid():
                apis = p.GetAppliedSchemas()
                print(f"USDRT candidate {ppath_candidate}: valid={p.IsValid()} apis={apis}", flush=True)
                if "PhysicsArticulationRootAPI" in apis or ppath_candidate.endswith("base_footprint"):
                    articulation_prim = p
                    print(f"USDRT using articulation prim: {ppath_candidate}", flush=True)
                    break

        # --- Step 2: Enable Fabric AFTER stage open (current correct approach) ---
        import carb
        import omni.kit.app
        _settings = carb.settings.get_settings()
        _ext_mgr = omni.kit.app.get_app().get_extension_manager()

        result = _ext_mgr.set_extension_enabled_immediate("omni.physx.fabric", True)
        print(f"USDRT enable omni.physx.fabric: result={result}", flush=True)

        # --- Step 3: Try SimulationManager.enable_fabric() ---
        try:
            from isaacsim.core.simulation_manager import SimulationManager
            was_enabled = SimulationManager.is_fabric_enabled()
            print(f"USDRT SimulationManager.is_fabric_enabled() before: {was_enabled}", flush=True)
            SimulationManager.enable_fabric(True)
            after_enabled = SimulationManager.is_fabric_enabled()
            print(f"USDRT SimulationManager.enable_fabric(True) called; after: {after_enabled}", flush=True)
        except Exception as e:
            print(f"USDRT SimulationManager.enable_fabric failed: {e}", flush=True)
            # Fall back to manual carb settings
            _settings.set_bool("/physics/updateToUsd", False)
            _settings.set_bool("/physics/updateParticlesToUsd", False)
            _settings.set_bool("/physics/updateVelocitiesToUsd", False)
            _settings.set_bool("/physics/updateForceSensorsToUsd", False)
            print("USDRT set carb flags manually", flush=True)

        upd = _settings.get("/physics/updateToUsd")
        print(f"USDRT /physics/updateToUsd after fabric enable: {upd}", flush=True)

        # --- Step 4: Play ---
        sim_ctx.play()
        upd2 = _settings.get("/physics/updateToUsd")
        print(f"USDRT /physics/updateToUsd after play: {upd2}", flush=True)

        R._wait_for_ros_topics(sim_ctx, config.scenario.robots, 20.0)
        watchdog_executor = R._start_cmd_vel_watchdog(config.scenario.robots)

        from tests.simulation.stop_stub import FixedTwistDriver
        robot_ids = [r.robot_id for r in config.scenario.robots]
        driver = FixedTwistDriver.spin_in_thread(robot_ids, speed_mps=0.10)
        print("USDRT driver started", flush=True)

        # Warmup
        import time
        for _ in range(10):
            app.update()
            time.sleep(0.01)

        # --- Step 5: Try reading Fabric positions via usdrt ---
        usdrt_stage = None
        try:
            import usdrt
            stage_id = _omni_usd.get_context().get_stage_id()
            usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)
            print(f"USDRT usdrt.Usd.Stage.Attach succeeded: {usdrt_stage}", flush=True)
        except Exception as e:
            print(f"USDRT usdrt import/attach failed: {e}", flush=True)

        # Camera subscriber
        import numpy as np
        import threading
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
        from sensor_msgs.msg import Image as _Img

        class _CamNode(Node):
            def __init__(self):
                super().__init__("_probe_usdrt")
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

        # Warmup camera
        t_warm = time.monotonic()
        while cam_node.latest is None and time.monotonic() - t_warm < 5.0:
            app.update()
        print(f"USDRT cam warmup done count={cam_node.count}", flush=True)

        means = []
        fabric_positions = []
        usd_positions = []

        import omni.graph.core as og

        odom_node_path = f"/World/ROSGraphs/{robot_id}/drive_graph/odom_compute"

        for i in range(120):
            app.update()

            # Camera mean
            if cam_node.latest is not None:
                means.append(float(cam_node.latest.mean()))

            # usdrt Fabric position
            if usdrt_stage is not None:
                for ppath_candidate in [
                    f"/World/Robots/{robot_id}/base_footprint",
                    f"/World/Robots/{robot_id}/base_link",
                    f"/World/Robots/{robot_id}",
                ]:
                    try:
                        prim = usdrt_stage.GetPrimAtPath(ppath_candidate)
                        if prim.IsValid():
                            xf = usdrt.UsdGeom.Xformable(prim)
                            t = xf.ComputeLocalToWorldTransform(
                                usdrt.Usd.TimeCode.Default()
                            ).ExtractTranslation()
                            fabric_positions.append((ppath_candidate, float(t[0]), float(t[1])))
                            break
                    except Exception:
                        pass

            # USD prim position (for comparison)
            if articulation_prim is not None:
                try:
                    xf = UsdGeom.Xformable(articulation_prim)
                    t = xf.ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
                    usd_positions.append((float(t[0]), float(t[1])))
                except Exception:
                    usd_positions.append(None)

            if i % 30 == 0:
                mean_s = f"{means[-1]:.3f}" if means else "N/A"
                fab_s = str(fabric_positions[-1]) if fabric_positions else "N/A"
                usd_s = str(usd_positions[-1]) if usd_positions else "N/A"
                # Also check odom
                odom_s = "N/A"
                try:
                    node = og.get_node_by_path(odom_node_path)
                    if node and node.is_valid():
                        pos = node.get_attribute("outputs:position").get()
                        if pos is not None:
                            odom_s = f"({float(pos[0]):.4f},{float(pos[1]):.4f})"
                except Exception:
                    pass
                print(f"USDRT i={i} cam_mean={mean_s} fabric={fab_s} usd={usd_s} odom={odom_s}",
                      flush=True)

        # Results
        if len(means) > 1:
            max_diff = max(abs(means[j] - means[j-1]) for j in range(1, len(means)))
            print(f"USDRT camera max_mean_diff={max_diff:.4f}", flush=True)
            if max_diff > 0.5:
                print("USDRT RESULT: camera IS changing!", flush=True)
            else:
                print("USDRT RESULT: camera still static", flush=True)

        if len(fabric_positions) >= 2:
            x0, y0 = fabric_positions[0][1], fabric_positions[0][2]
            xN, yN = fabric_positions[-1][1], fabric_positions[-1][2]
            dist = ((xN - x0)**2 + (yN - y0)**2) ** 0.5
            print(f"USDRT Fabric displacement: {dist:.4f}m "
                  f"first=({x0:.4f},{y0:.4f}) last=({xN:.4f},{yN:.4f})", flush=True)
            if dist > 0.01:
                print("USDRT FABRIC: positions ARE changing — PhysX→Fabric sync works", flush=True)
            else:
                print("USDRT FABRIC: positions FROZEN — PhysX→Fabric sync NOT working", flush=True)

        valid_usd = [p for p in usd_positions if p is not None]
        if len(valid_usd) >= 2:
            dx = abs(valid_usd[-1][0] - valid_usd[0][0])
            dy = abs(valid_usd[-1][1] - valid_usd[0][1])
            print(f"USDRT USD displacement: {(dx**2+dy**2)**0.5:.4f}m", flush=True)

        # Save final frame
        if cam_node.latest is not None:
            try:
                import cv2
                out_dir = Path("data/logs/recordings")
                out_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out_dir / "usdrt_final.png"),
                            cv2.cvtColor(cam_node.latest, cv2.COLOR_RGB2BGR))
                print("USDRT saved usdrt_final.png", flush=True)
            except Exception as e:
                print(f"USDRT cv2 error: {e}", flush=True)

    finally:
        print("USDRT cleanup", flush=True)
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
