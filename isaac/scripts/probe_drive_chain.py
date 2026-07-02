"""Headless drive-chain localization probe for M4 Phase 1 (diagnostics).

Runs inside Isaac Sim's Python (``python.sh``). Builds the *real* head_on_deadlock
scene with the runner's own helpers (identical ordering: open -> extensions ->
validate -> timeline window -> sim context -> reset -> lighting -> wire graphs ->
play), then publishes a forward ``Twist`` to ``/<robot>/cmd_vel`` and reads the
ENTIRE drive chain from source to sink each sample so a no-motion fault is
localized to one edge instead of guessed:

    subscriber-count -> twist_sub.linearVelocity -> break_lin.x
        -> diff_ctrl.velocityCommand -> wheel joint velocities
        -> odom_compute.position (live base pose, not the static USD Xform)

Plus free static read-backs (jointNames value, targetPrim/chassisPrim rel
targets) BEFORE the first step, which settle the binding candidates with zero
sim cost.

Usage on the host:
    $ISAAC_SIM_ROOT/python.sh -m isaac.scripts.probe_drive_chain \
        --scenario head_on_deadlock --robot-id robot_1 --seed 42
"""
from __future__ import annotations

import argparse
from pathlib import Path


def _build_config(scenario_arg: str, seed: int):
    import yaml

    from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig
    from isaac.vgu_sim.paths import scenario_config_path, scenario_output_path

    cfg_path = (Path(scenario_arg) if scenario_arg.endswith(".yaml")
                else scenario_config_path(scenario_arg))
    if not cfg_path.exists():
        raise SystemExit(f"Scenario config not found: {cfg_path}")
    with open(cfg_path) as f:
        raw = yaml.safe_load(f)
    raw["seed"] = seed
    scenario = ScenarioConfig.model_validate(raw)
    return ResolvedRunConfig(
        scenario_path=scenario_output_path(scenario.name),
        scenario=scenario,
        headless=True,
        repetitions=1,
        output_dir=Path("data/logs/simulation"),
        topic_timeout_sec=30.0,
        ros_domain_id=None,
    )


def _og_get(path: str):
    """Best-effort read of one OmniGraph attribute value. Returns repr or error."""
    import omni.graph.core as og
    try:
        return og.Controller.attribute(path).get()
    except Exception as exc:  # noqa: BLE001 - diagnostics
        return f"<read-failed: {exc}>"


def _rel_targets(stage, node_path: str, rel_name: str):
    """Best-effort read of a relationship-typed input's bound targets."""
    try:
        prim = stage.GetPrimAtPath(node_path)
        rel = prim.GetRelationship(rel_name)
        if not rel:
            return "<no relationship>"
        return [t.pathString for t in rel.GetTargets()]
    except Exception as exc:  # noqa: BLE001 - diagnostics
        return f"<read-failed: {exc}>"


def _make_articulation(chassis_path: str):
    """Return a best-effort articulation handle for joint-velocity reads, or None."""
    # API moved across Isaac releases; try the known locations and degrade
    # gracefully — the og reads are the load-bearing diagnostics, joints are a
    # bonus that splits "controller commanded" from "physics moved".
    for mod, cls in (
        ("isaacsim.core.prims", "SingleArticulation"),
        ("isaacsim.core.prims", "Articulation"),
        ("isaacsim.core.api.articulations", "Articulation"),
    ):
        try:
            module = __import__(mod, fromlist=[cls])
            art_cls = getattr(module, cls)
            art = art_cls(chassis_path)
            art.initialize()
            return art
        except Exception:  # noqa: BLE001 - probing API surface
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="M4 Phase 1 drive-chain probe")
    parser.add_argument("--scenario", default="head_on_deadlock")
    parser.add_argument("--robot-id", default="robot_1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--linear-x", type=float, default=0.15)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--sample-every", type=int, default=15)
    args = parser.parse_args()

    config = _build_config(args.scenario, args.seed)
    robot_id = args.robot_id
    graph = f"/World/ROSGraphs/{robot_id}/drive_graph"
    cmd_topic = f"/{robot_id}/cmd_vel"

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    # Import runner helpers AFTER the app exists (they import omni.* lazily).
    from isaac.vgu_sim import runner

    print("=" * 72, flush=True)
    print(f"PROBE drive chain  scenario={args.scenario} robot={robot_id} "
          f"linear_x={args.linear_x}", flush=True)
    print("=" * 72, flush=True)

    try:
        runner._open_stage(config.scenario_path)
        runner._enable_extensions()
        runner._validate_stage(config.scenario_path)

        import omni.usd as _omni_usd
        stage = _omni_usd.get_context().get_stage()
        runner._set_timeline_window(stage)

        physics_hz = config.scenario.runtime.physics_hz
        physics_dt = 1.0 / physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz
        sim_ctx = runner._make_sim_context(physics_dt, 1.0 / rendering_hz)
        sim_ctx.reset()
        runner._add_scene_lighting(_omni_usd.get_context().get_stage())
        runner._wire_ros_graphs(config.scenario.robots)

        stage = _omni_usd.get_context().get_stage()

        # --- Free static read-backs (post-wire, pre-step) -------------------
        print("\n-- STATIC READ-BACKS (pre-step) --", flush=True)
        jn = _og_get(f"{graph}/art_ctrl.inputs:jointNames")
        print(f"  art_ctrl.inputs:jointNames        = {jn!r}", flush=True)
        print(f"  art_ctrl targetPrim rel targets   = "
              f"{_rel_targets(stage, f'{graph}/art_ctrl', 'inputs:targetPrim')}",
              flush=True)
        # Some node types resolve targetPrim into the value slot rather than a
        # USD relationship; read both ways so neither convention hides a binding.
        print(f"  art_ctrl.inputs:targetPrim (val)  = "
              f"{_og_get(f'{graph}/art_ctrl.inputs:targetPrim')!r}", flush=True)
        print(f"  odom_compute chassisPrim rel tgts = "
              f"{_rel_targets(stage, f'{graph}/odom_compute', 'inputs:chassisPrim')}",
              flush=True)
        print(f"  odom_compute.inputs:chassisPrim   = "
              f"{_og_get(f'{graph}/odom_compute.inputs:chassisPrim')!r}", flush=True)
        print(f"  diff_ctrl.inputs:maxWheelSpeed    = "
              f"{_og_get(f'{graph}/diff_ctrl.inputs:maxWheelSpeed')!r}", flush=True)
        print(f"  diff_ctrl.inputs:maxAcceleration  = "
              f"{_og_get(f'{graph}/diff_ctrl.inputs:maxAcceleration')!r}", flush=True)
        print(f"  diff_ctrl.inputs:wheelRadius      = "
              f"{_og_get(f'{graph}/diff_ctrl.inputs:wheelRadius')!r}", flush=True)
        print(f"  diff_ctrl.inputs:wheelDistance    = "
              f"{_og_get(f'{graph}/diff_ctrl.inputs:wheelDistance')!r}", flush=True)

        # Find the articulation-root path the same way ros_graphs.py does, for
        # the joint-velocity readout.
        from pxr import Usd, UsdPhysics
        root_prim = stage.GetPrimAtPath(f"/World/Robots/{robot_id}")
        art_roots = [p for p in Usd.PrimRange(root_prim)
                     if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
        chassis_path = art_roots[0].GetPath().pathString if art_roots else None
        print(f"  articulation-root path            = {chassis_path}", flush=True)

        sim_ctx.play()
        runner._wait_for_ros_topics(sim_ctx, config.scenario.robots,
                                    config.topic_timeout_sec)

        art = _make_articulation(chassis_path) if chassis_path else None
        dof_names = None
        if art is not None:
            try:
                dof_names = list(art.dof_names)
            except Exception:  # noqa: BLE001
                dof_names = None
        print(f"\n-- ARTICULATION handle={'OK' if art else 'NONE'} "
              f"dof_names={dof_names} --", flush=True)

        # --- Live cmd_vel with full-chain reads -----------------------------
        import rclpy
        from geometry_msgs.msg import Twist
        from rclpy.node import Node

        rclpy.init(args=None)
        node = Node("_probe_cmd_pub")
        pub = node.create_publisher(Twist, cmd_topic, 10)
        msg = Twist()
        msg.linear.x = args.linear_x

        print(f"\n-- LIVE cmd_vel loop (publishing {args.linear_x} m/s on "
              f"{cmd_topic}) --", flush=True)
        for i in range(args.steps):
            pub.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.0)
            app.update()
            if i % args.sample_every == 0:
                subs = node.count_subscribers(cmd_topic)
                tw_lin = _og_get(f"{graph}/twist_sub.outputs:linearVelocity")
                br_x = _og_get(f"{graph}/break_lin.outputs:x")
                vcmd = _og_get(f"{graph}/diff_ctrl.outputs:velocityCommand")
                opos = _og_get(f"{graph}/odom_compute.outputs:position")
                jvel = None
                if art is not None:
                    try:
                        jvel = art.get_joint_velocities()
                    except Exception as exc:  # noqa: BLE001
                        jvel = f"<read-failed: {exc}>"
                print(
                    f"  step={i:3d} subs={subs} "
                    f"twist.lin={tw_lin} break.x={br_x} "
                    f"vcmd={vcmd} jvel={jvel} odom.pos={opos}",
                    flush=True,
                )

        node.destroy_node()
        rclpy.shutdown()
        print("\nPROBE DONE", flush=True)

    finally:
        try:
            import omni.timeline
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        app.close()


main()
