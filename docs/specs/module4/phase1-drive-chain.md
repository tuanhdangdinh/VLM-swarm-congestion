# Module 4 — Phase 1 — Isaac Drive Chain

**Prepared:** 2026-06-19

**Revision history:**

- Initial draft: Phase 1 of the M4 Nav2 rollout — make robots drive via
  `/cmd_vel`. Split out of `module4_navigation.md`.

---

## 1. Goal

Implement the M6 FR6.7.4 drive subset so a `geometry_msgs/Twist` on
`/<robot_id>/cmd_vel` moves the robot. No Nav2, no new heavy dependency. This
validates the articulation drives correctly and lets a test script command motion
so the head-on deadlock can emerge **dynamically** instead of being a static spawn
snapshot.

See [README.md](README.md) for the module overview and current-state gap analysis.

---

## 2. Isaac Drive & Sense Graph

Extend `create_robot_ros_graph` (ros_graphs.py:96) from the current odometry-only
graph to the full per-robot graph. Node type names below are indicative and
**must be verified against Isaac Sim 6.0 / Jazzy** before implementation
(CLAUDE.md external-library-verification rule).

| Function | OmniGraph node (verify) | Output |
|---|---|---|
| Twist input | `isaacsim.ros2.bridge.ROS2SubscribeTwist` | — |
| Twist → wheel vel | `isaacsim.robot.wheeled_robots.DifferentialController` | wheel targets |
| Apply wheels | articulation controller | joint commands |
| Odometry | `isaacsim.core.nodes.IsaacComputeOdometry` (present today) | `/<id>/odom` |
| Odom TF | `ROS2PublishRawTransformTree` (dynamic, single `odom→base_footprint`) | `/tf` |
| Static TF | `ROS2PublishRawTransformTree` (once, `staticPublisher=true`) | `/tf_static` |

> The node-type names and the dynamic-vs-raw TF choice above are **verified** —
> see §2a (captured 2026-06-19).

The lidar (`/<robot_id>/scan`) is **not** required in Phase 1; it is added in
[phase2-nav2-stack.md](phase2-nav2-stack.md).

**Verify — `Twist` vs `TwistStamped`.** `ROS2SubscribeTwist` expects plain
`geometry_msgs/Twist`. Jazzy Nav2 has a `use_stamped_cmd_vel` toggle and the
default has moved across distros, so the Nav2 controller may publish
`geometry_msgs/TwistStamped` on `/<robot_id>/cmd_vel`. Before wiring Phase 2,
confirm the two agree; if not, use the stamped subscribe variant or insert a
relay. In Phase 1 this is moot (the test publishes plain `Twist`), but pin the
Isaac side now so Phase 2 doesn't silently drop commands.

---

## 2a. Verified node interface (captured 2026-06-19, Isaac Sim 6.0.0-rc.59)

Captured headlessly via `isaac/scripts/introspect_drive_nodes.py` (creates one of
each node type and dumps its attributes). Exact attribute keys to transcribe into
`ros_graphs.py`; do not guess. Resolves the three Phase 1 verification gaps:

**(a) Twist vs TwistStamped — RESOLVED: plain `Twist`.** `ROS2SubscribeTwist` has
no stamp/`frameId` input and emits `outputs:linearVelocity` / `outputs:angularVelocity`
as `double3`. The Phase 2 Nav2 controller must therefore publish plain
`geometry_msgs/Twist` (`use_stamped_cmd_vel:=false`), or a relay must strip the
stamp.

**(b) Watchdog primitive — RESOLVED: does NOT exist → use a relay node (Branch B).**
`DifferentialController` inputs are `linearVelocity`, `angularVelocity`, `dt`,
`maxAcceleration`, `maxAngularAcceleration`, `maxAngularSpeed`, `maxDeceleration`,
`maxLinearSpeed`, `maxWheelSpeed`, `wheelDistance`, `wheelRadius` — there is **no
timeout/keep-alive input**. The FR6.4.8 `0.5 s` watchdog must be a separate rclpy
relay node (`/cmd_vel → /cmd_vel_safe`, `use_sim_time=True`) wrapping the pure
`watchdog_velocity` core (`isaac/vgu_sim/cmd_vel_watchdog.py`); the graph's
`ROS2SubscribeTwist` subscribes to `/cmd_vel_safe`.

**(c) Odometry TF emission — RESOLVED: `ROS2PublishOdometry` does NOT emit TF.** Its
inputs are `position`, `orientation`, `linearVelocity`, `angularVelocity`,
`odomFrameId`, `chassisFrameId`, `timeStamp` — it publishes only the `nav_msgs/Odometry`
topic, no `/tf`. The dynamic `odom → base_footprint` transform must come from a
separate publisher (feed `IsaacComputeOdometry` `position`/`orientation` into a
`ROS2PublishRawTransformTree` with `staticPublisher=false`, `topicName=/tf`). No
double-publish conflict exists; the Task 6 odom-TF guard is therefore unnecessary.

**Wiring note — scalar pickoff required.** `ROS2SubscribeTwist` emits `double3`
vectors but `DifferentialController` takes scalar `double` `linearVelocity` /
`angularVelocity`. Insert a vector-component extraction (e.g.
`omni.graph.nodes.BreakVector3`, verify at wire time) to feed `x` of the linear
vector and `z` of the angular vector into the controller.

Verified attribute keys (inputs unless noted):

| Node | Key attributes |
|---|---|
| `ROS2SubscribeTwist` | in: `context`, `topicName`, `nodeNamespace`, `qosProfile`, `queueSize`, `execIn`; out: `linearVelocity` (double3), `angularVelocity` (double3), `execOut` |
| `DifferentialController` | in: `linearVelocity` (double), `angularVelocity` (double), `dt`, `wheelRadius`, `wheelDistance`, `maxLinearSpeed`, `maxAngularSpeed`, `maxWheelSpeed`, `maxAcceleration`, `maxDeceleration`, `maxAngularAcceleration`, `execIn`; out: `velocityCommand` (double[]) |
| `IsaacArticulationController` | in: `velocityCommand` (double[]), `positionCommand`, `effortCommand`, `jointNames` (token[]), `jointIndices` (int[]), `robotPath`, `targetPrim` (rel), `execIn` |
| `IsaacComputeOdometry` | in: `chassisPrim` (rel), `execIn`; out: `position` (double3), `orientation` (double4), `linearVelocity`, `angularVelocity`, `execOut` |
| `ROS2PublishOdometry` | in: `position`, `orientation`, `linearVelocity`, `angularVelocity`, `odomFrameId`, `chassisFrameId`, `topicName`, `timeStamp`, `context`, `execIn` |
| `ROS2PublishRawTransformTree` | in: `parentFrameId`, `childFrameId`, `translation` (double3), `rotation` (double4), `staticPublisher` (bool), `topicName`, `timeStamp`, `context`, `execIn` |
| `ROS2PublishTransformTree` | in: `parentFrames`/`childFrames` (token[]), `translations`/`orientations` (arrays), `parentPrim`/`targetPrims` (rel), `staticPublisher` (bool), `topicName`, `timeStamp`, `context`, `execIn` |

---

## 3. Parameters

Differential-drive constants (M6 FR6.4.7):

- Wheel radius: `0.033 m`
- Wheel separation: `0.160 m`
- Maximum linear velocity: `0.22 m/s`
- Maximum angular velocity: `2.84 rad/s`

Command watchdog (M6 FR6.4.8): zero both wheel targets when no valid
`/<robot_id>/cmd_vel` is received for `0.5 s` of simulation time.

TF tree (M6 FR6.7.5–6.7.6):

```text
robot_N/odom
    -> robot_N/base_footprint      (dynamic, /tf)
    -> robot_N/base_link           (static, /tf_static)
    -> robot_N/base_scan           (static, /tf_static)
```

Only `odom -> base_footprint` is time-varying; the rest are fixed mount offsets
published once on `/tf_static`.

---

## 4. Testing & Validation — implemented

- **Offline (implemented):** Isaac's `DifferentialController` owns the twist →
  wheel-velocity math, so it is validated **end-to-end** rather than by an
  isolated copy of its arithmetic: the labelled oracle `forward_distance`
  (`isaac/vgu_sim/diff_drive_oracle.py`, unit-tested in
  `tests/unit/test_m6_oracle.py`) predicts the expected odometry displacement,
  and the speed-cap safety guard (FR6.8.5a) is unit-tested for both commanders in
  `tests/unit/test_m6_stop_stub.py`.
- **In sim (host-verified):** `tests/simulation/stop_stub.py` gained
  `FixedTwistDriver`, which publishes a fixed forward `Twist` to
  `/<robot_id>/cmd_vel` at 10 Hz (capped at 0.15 m/s) and ceases on
  `request_stop` so the watchdog zeroes the wheels. The drive chain (`/cmd_vel →
  /cmd_vel_safe → DifferentialController → physics → /odom + /tf`) and the
  Branch B watchdog stop were **verified on the Isaac host** — yaw/TF convention
  correct over a 166° sweep, watchdog zeroing in ~0.5 s of sim time
  (`docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md`).
- **Automated acceptance test:** `tests/simulation/test_m4_phase1_drive.py`
  (markers `isaac_sim`/`ros2`). There is no in-process `isaac_host` fixture yet,
  so it is a **documented-skip**: its docstring records the exact manual [HOST]
  drive + watchdog procedure that was run, and it skips in both CI and on the
  host. The live verification of record is the Task 6 host report above, not an
  automated pass.
