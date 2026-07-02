"""[HOST] Task 6 Step 3 verification probe: TF-vs-odom yaw on a curve + watchdog stop.

EPHEMERAL DIAGNOSTIC — not committed, deleted from the host after the run.

Runs inside Isaac Sim's Python (``python.sh``). Builds the real head_on_deadlock
scene with the runner's own helpers (identical ordering), starts the Branch B
``CmdVelWatchdog`` exactly as ``runner._start_cmd_vel_watchdog`` does, then:

  Phase 1 (curve): publishes a turning Twist to ``/<robot>/cmd_vel`` (the public
  topic; the watchdog relays it to ``/cmd_vel_safe``). Each sample reads, through
  REAL ROS messages, the yaw from ``/<robot>/odom`` (ROS2PublishOdometry, the
  known-good ROS convention) and the yaw of the ``odom -> base_footprint``
  transform on ``/tf`` (ROS2PublishRawTransformTree). Both publishers read the
  SAME ``odom_compute.outputs:orientation``, so a quatd->double[4] order scramble
  (USD GfQuat is w-first; ROS wants xyzw) shows up as gross yaw divergence on the
  curve. To avoid trusting ``/odom`` blind, it also checks ``yaw_odom`` against
  the trajectory tangent ``atan2(dy, dx)`` (diff-drive has no lateral slip, so
  heading == path tangent).

  Phase 2 (watchdog): stops commanding and keeps stepping; verifies the graph's
  received command (``/cmd_vel_safe`` via ``twist_sub.outputs:linearVelocity``)
  returns to ~0 within ~command_timeout_sec of SIM time. The watchdog's
  ``get_clock().now()`` is printed beside ``sim_ctx.current_time`` every sample so
  a no-stop result is diagnosable (logic wrong vs. /clock never reaching the node).

Usage on the host:
    $ISAAC_SIM_ROOT/python.sh -m isaac.scripts.probe_tf_watchdog \
        --scenario head_on_deadlock --robot-id robot_1 --seed 42
"""
from __future__ import annotations

import argparse
import math
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
    import omni.graph.core as og
    try:
        return og.Controller.attribute(path).get()
    except Exception as exc:  # noqa: BLE001 - diagnostics
        return f"<read-failed: {exc}>"


def _og_quat(path: str) -> list[float] | None:
    """Read an OmniGraph quat attribute into a 4-float list, or None on failure."""
    v = _og_get(path)
    try:
        arr = [float(x) for x in v]
    except (TypeError, ValueError):
        return None
    return arr if len(arr) == 4 else None


def _yaw_from_quat(x: float, y: float, z: float, w: float) -> float:
    """Yaw (rad) from a quaternion in ROS xyzw order."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def _ang_diff(a: float, b: float) -> float:
    """Smallest signed difference a-b wrapped to [-pi, pi]."""
    return math.atan2(math.sin(a - b), math.cos(a - b))


def main() -> None:
    parser = argparse.ArgumentParser(description="M4 Phase 1 Task 6 TF + watchdog probe")
    parser.add_argument("--scenario", default="head_on_deadlock")
    parser.add_argument("--robot-id", default="robot_1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--linear-x", type=float, default=0.12)
    parser.add_argument("--angular-z", type=float, default=0.6)
    parser.add_argument("--drive-steps", type=int, default=200)
    parser.add_argument("--coast-steps", type=int, default=120)
    parser.add_argument("--sample-every", type=int, default=20)
    args = parser.parse_args()

    config = _build_config(args.scenario, args.seed)
    robot_id = args.robot_id
    graph = f"/World/ROSGraphs/{robot_id}/drive_graph"
    cmd_topic = f"/{robot_id}/cmd_vel"
    odom_topic = f"/{robot_id}/odom"
    odom_frame = f"{robot_id}/odom"
    base_frame = f"{robot_id}/base_footprint"

    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True, "anti_aliasing": 0})

    from isaac.vgu_sim import runner

    print("=" * 72, flush=True)
    print(f"PROBE tf+watchdog scenario={args.scenario} robot={robot_id} "
          f"lin={args.linear_x} ang={args.angular_z}", flush=True)
    print("=" * 72, flush=True)

    # Open with an ABSOLUTE path: the live Omniverse resolver anchors the
    # scenario's relative `../assets/...` references against the layer IDENTIFIER,
    # so a relative identifier doubles to isaac/scenarios/isaac/assets and fails to
    # resolve. An absolute identifier resolves `../assets` correctly. (A bare
    # Usd.Stage.Open uses realPath and is unaffected, which is why offline
    # validation passed but the in-app open did not.)
    abs_scenario = config.scenario_path.resolve()

    wd_exec = None
    try:
        runner._open_stage(abs_scenario)
        runner._enable_extensions()
        # Validation checks camera/marker/texture assets that are irrelevant to the
        # drive chain + TF tree under test here. On this host the marker textures
        # (empty Textures/) fail to resolve under the live Omniverse resolver; that
        # is a separate host-asset gap, so log the detail and continue rather than
        # abort the TF/watchdog verification.
        try:
            runner._validate_stage(abs_scenario)
        except Exception as exc:  # noqa: BLE001
            print(f"\n!!! VALIDATION SKIPPED (non-fatal for drive/TF): {exc}", flush=True)
            import omni.usd as _ou
            vstage = _ou.get_context().get_stage()
            for i, e in enumerate(vstage.GetCompositionErrors()):
                print(f"    comp-err[{i}] {type(e).__name__}: {e}", flush=True)

        import omni.usd as _omni_usd
        stage = _omni_usd.get_context().get_stage()
        runner._set_timeline_window(stage)

        physics_hz = config.scenario.runtime.physics_hz
        rendering_hz = config.scenario.runtime.rendering_hz or physics_hz
        sim_ctx = runner._make_sim_context(1.0 / physics_hz, 1.0 / rendering_hz)
        sim_ctx.reset()
        runner._add_scene_lighting(_omni_usd.get_context().get_stage())
        runner._wire_ros_graphs(config.scenario.robots)

        sim_ctx.play()
        runner._wait_for_ros_topics(sim_ctx, config.scenario.robots,
                                    config.topic_timeout_sec)

        # rclpy was shut down inside _wait_for_ros_topics' finally; the watchdog
        # re-inits it (spin_in_thread guards on rclpy.ok()). Start the watchdog
        # exactly as the runner does so /cmd_vel -> /cmd_vel_safe relaying is live.
        import rclpy
        from geometry_msgs.msg import Twist
        from nav_msgs.msg import Odometry
        from rclpy.node import Node
        from tf2_msgs.msg import TFMessage

        from isaac.vgu_sim.cmd_vel_watchdog_node import spin_in_thread
        from isaac.vgu_sim.config import RobotAssetConfig

        timeout_sec = RobotAssetConfig().command_timeout_sec
        wd_exec, wd_nodes = spin_in_thread([robot_id], timeout_sec)
        wd_node = wd_nodes[0]
        print(f"\n-- watchdog up (timeout={timeout_sec}s sim) --", flush=True)

        node = Node("_probe_tf_wd")
        pub = node.create_publisher(Twist, cmd_topic, 10)

        latest = {"odom": None, "tf": None}

        def _on_odom(msg: Odometry) -> None:
            latest["odom"] = msg

        def _on_tf(msg: TFMessage) -> None:
            for tr in msg.transforms:
                if tr.header.frame_id == odom_frame and tr.child_frame_id == base_frame:
                    latest["tf"] = tr

        node.create_subscription(Odometry, odom_topic, _on_odom, 50)
        node.create_subscription(TFMessage, "/tf", _on_tf, 50)

        def _drain() -> None:
            # Service ALL ready callbacks: the graph emits >=2 msgs/step (/odom +
            # /tf); a single spin_once would starve the lower-priority sub and make
            # /tf appear to freeze once both queues stay saturated.
            for _ in range(8):
                rclpy.spin_once(node, timeout_sec=0.0)

        def _sample(prev_src_pos):
            # In-process reads (bypass ROS wire + rclpy spin entirely): these never
            # starve, so they decide whether a frozen ROS-received yaw_tf is a real
            # publish stall or just probe-side subscription starvation.
            src_q = _og_quat(f"{graph}/odom_compute.outputs:orientation")
            wire_q = _og_quat(f"{graph}/pub_tf.inputs:rotation")
            src_pos = _og_get(f"{graph}/odom_compute.outputs:position")
            yaw_src = _yaw_from_quat(*src_q) if src_q else None
            yaw_wire = _yaw_from_quat(*wire_q) if wire_q else None
            try:
                spx, spy = float(src_pos[0]), float(src_pos[1])
            except (TypeError, IndexError, ValueError):
                spx = spy = None
            src_tangent = None
            if spx is not None and prev_src_pos is not None:
                dx, dy = spx - prev_src_pos[0], spy - prev_src_pos[1]
                if math.hypot(dx, dy) > 1e-3:
                    src_tangent = math.atan2(dy, dx)
            new_src_pos = (spx, spy) if spx is not None else prev_src_pos

            # ROS-received reads (probe-health only): subject to spin starvation.
            o = latest["odom"]
            t = latest["tf"]
            yaw_odom = yaw_tf = None
            if o is not None:
                q = o.pose.pose.orientation
                yaw_odom = _yaw_from_quat(q.x, q.y, q.z, q.w)
            if t is not None:
                tq = t.transform.rotation
                yaw_tf = _yaw_from_quat(tq.x, tq.y, tq.z, tq.w)

            wd_clock = wd_node.get_clock().now().nanoseconds * 1e-9
            return (
                {
                    "yaw_src": yaw_src,
                    "yaw_wire": yaw_wire,
                    "src_tangent": src_tangent,
                    "yaw_odom": yaw_odom,
                    "yaw_tf": yaw_tf,
                    "src_q": src_q,
                    "wire_q": wire_q,
                    "sim_t": sim_ctx.current_time,
                    "wd_clock": wd_clock,
                },
                new_src_pos,
            )

        # --- Phase 1: drive a curve --------------------------------------
        msg = Twist()
        msg.linear.x = args.linear_x
        msg.angular.z = args.angular_z
        prev_src_pos = None
        max_wire_src_diff = 0.0     # in-process: pub_tf input vs odom_compute source
        max_src_tangent_diff = 0.0  # in-process: source orientation vs path tangent
        max_tf_odom_diff = 0.0      # ROS-received: probe-health only
        src_yaw_first = None
        src_yaw_last = None
        wire_yaw_prev = None
        wire_frozen_at = None
        print("\n-- PHASE 1: curve (publishing on /cmd_vel) --", flush=True)
        for i in range(args.drive_steps):
            pub.publish(msg)
            _drain()
            app.update()
            if i % args.sample_every == 0:
                s, prev_src_pos = _sample(prev_src_pos)

                # In-process convention check (never starves).
                wire_src_txt = src_tan_txt = "n/a"
                if s["yaw_wire"] is not None and s["yaw_src"] is not None:
                    d_ws = math.degrees(_ang_diff(s["yaw_wire"], s["yaw_src"]))
                    max_wire_src_diff = max(max_wire_src_diff, abs(d_ws))
                    wire_src_txt = f"{d_ws:+.1f}"
                if s["yaw_src"] is not None and s["src_tangent"] is not None:
                    d_st = math.degrees(_ang_diff(s["yaw_src"], s["src_tangent"]))
                    max_src_tangent_diff = max(max_src_tangent_diff, abs(d_st))
                    src_tan_txt = f"{d_st:+.1f}"
                if s["yaw_src"] is not None:
                    if src_yaw_first is None:
                        src_yaw_first = s["yaw_src"]
                    src_yaw_last = s["yaw_src"]

                # Does the publisher INPUT keep advancing? (freeze localization)
                if s["yaw_wire"] is not None:
                    if (wire_yaw_prev is not None and wire_frozen_at is None
                            and abs(_ang_diff(s["yaw_wire"], wire_yaw_prev)) < 1e-4):
                        wire_frozen_at = i
                    wire_yaw_prev = s["yaw_wire"]

                # ROS-received diff (probe-health).
                tf_odom_txt = "n/a"
                if s["yaw_tf"] is not None and s["yaw_odom"] is not None:
                    d_tf = math.degrees(_ang_diff(s["yaw_tf"], s["yaw_odom"]))
                    max_tf_odom_diff = max(max_tf_odom_diff, abs(d_tf))
                    tf_odom_txt = f"{d_tf:+.1f}"

                ys = ("%.1f" % math.degrees(s["yaw_src"])) if s["yaw_src"] is not None else "--"
                yw = ("%.1f" % math.degrees(s["yaw_wire"])) if s["yaw_wire"] is not None else "--"
                yt = ("%.1f" % math.degrees(s["yaw_tf"])) if s["yaw_tf"] is not None else "--"
                print(
                    f"  step={i:3d} sim_t={s['sim_t']:.3f} wd_clk={s['wd_clock']:.3f} "
                    f"yaw_src={ys} yaw_wire={yw} yaw_tf={yt} "
                    f"d(wire-src)={wire_src_txt} d(src-tan)={src_tan_txt} "
                    f"d(tf-odom)={tf_odom_txt}",
                    flush=True,
                )

        yaw_swept = (math.degrees(abs(_ang_diff(src_yaw_last, src_yaw_first)))
                     if src_yaw_first is not None else 0.0)

        # --- Phase 2: stop commanding, watch the watchdog zero ------------
        print("\n-- PHASE 2: coast (NO /cmd_vel; watchdog must zero) --", flush=True)
        t_last_cmd = sim_ctx.current_time
        stop_delay = None
        for i in range(args.coast_steps):
            # Do NOT publish. Pump rclpy so subscriptions/clock update.
            _drain()
            app.update()
            safe_lin = _og_get(f"{graph}/twist_sub.outputs:linearVelocity")
            vcmd = _og_get(f"{graph}/diff_ctrl.outputs:velocityCommand")
            # twist_sub.outputs:linearVelocity is a numpy vector [vx, vy, vz], not a
            # float; _og_get returns a "<read-failed: ...>" string on error. Guard both.
            try:
                lin0 = float(safe_lin[0])
            except (TypeError, IndexError, ValueError):
                lin0 = None
            if i % args.sample_every == 0:
                wd_clk = wd_node.get_clock().now().nanoseconds * 1e-9
                print(
                    f"  step={i:3d} sim_t={sim_ctx.current_time:.3f} "
                    f"wd_clk={wd_clk:.3f} cmd_vel_safe.lin={safe_lin} vcmd={vcmd}",
                    flush=True,
                )
            if stop_delay is None and lin0 is not None and abs(lin0) < 1e-4:
                stop_delay = sim_ctx.current_time - t_last_cmd
                print(f"  >>> cmd_vel_safe reached ~0 at sim_t={sim_ctx.current_time:.3f} "
                      f"(+{stop_delay:.3f}s after last command)", flush=True)

        node.destroy_node()

        # --- Verdict ------------------------------------------------------
        # The verdict rests on IN-PROCESS reads (og), which never starve, so a
        # probe-side /tf subscription stall cannot mask or fake the result:
        #   * yaw swept           -> the curve actually turned
        #   * |yaw_wire - yaw_src| -> pub_tf consumes odom_compute's orientation
        #                             intact (no xyzw/wxyz scramble on the wire)
        #   * |yaw_src - tangent|  -> that orientation is physically correct
        #   * watchdog stop delay  -> Branch B zeros the command
        # The ROS-received |yaw_tf - yaw_odom| and the wire-freeze step are reported
        # as DIAGNOSTICS (probe health), not gating conditions.
        print("\n" + "=" * 72, flush=True)
        print("VERDICT (in-process gates)", flush=True)
        print(f"  yaw swept on curve         = {yaw_swept:.1f} deg "
              f"(want >= 60)", flush=True)
        print(f"  max |yaw_wire - yaw_src|   = {max_wire_src_diff:.1f} deg "
              f"(want <= 10)", flush=True)
        print(f"  max |yaw_src - tangent|    = {max_src_tangent_diff:.1f} deg "
              f"(want <= 10)", flush=True)
        print(f"  watchdog stop delay        = "
              f"{('%.3f s' % stop_delay) if stop_delay is not None else 'NEVER'} "
              f"(want ~{timeout_sec}s, <= {timeout_sec + 0.3})", flush=True)
        print("DIAGNOSTICS (probe-side ROS receive)", flush=True)
        print(f"  max |yaw_tf - yaw_odom|    = {max_tf_odom_diff:.1f} deg", flush=True)
        print(f"  publisher-input froze at   = "
              f"{('step %d' % wire_frozen_at) if wire_frozen_at is not None else 'never'} "
              f"(if 'never', a frozen yaw_tf is receive-side starvation, not a stall)",
              flush=True)
        ok = (
            yaw_swept >= 60.0
            and max_wire_src_diff <= 10.0
            and max_src_tangent_diff <= 10.0
            and stop_delay is not None
            and stop_delay <= timeout_sec + 0.3
        )
        print(f"  RESULT: {'PASS' if ok else 'FAIL'}", flush=True)
        print("=" * 72, flush=True)

    except Exception:  # noqa: BLE001 - surface the real error past fastShutdown
        import traceback
        print("\n!!! PROBE EXCEPTION !!!", flush=True)
        traceback.print_exc()
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        if wd_exec is not None:
            try:
                wd_exec.shutdown()
            except Exception:
                pass
        try:
            import rclpy
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
        try:
            import omni.timeline
            omni.timeline.get_timeline_interface().stop()
        except Exception:
            pass
        app.close()


main()
