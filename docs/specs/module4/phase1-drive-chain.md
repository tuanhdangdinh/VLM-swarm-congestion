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
| Odom TF | `ROS2PublishTransformTree` (dynamic) | `/tf` |
| Static TF | `ROS2PublishRawTransformTree` (once) | `/tf_static` |

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

## 4. Testing & Validation

- **Offline:** unit-test the differential-drive math (twist → wheel velocities)
  without Isaac.
- **In sim:** publish a fixed `Twist` to `/<robot_id>/cmd_vel` and assert
  `/<robot_id>/odom` integrates forward, then stops; assert the watchdog zeroes
  wheel targets after `0.5 s` with no command. Extend
  `tests/simulation/stop_stub.py` (it already publishes `Twist` to
  `/<robot_id>/cmd_vel`). Mark as a simulation test, not a fast unit test.
