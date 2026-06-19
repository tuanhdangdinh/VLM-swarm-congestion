# M4 Phase 1 — Isaac Drive Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each simulated robot drive in response to a `geometry_msgs/Twist` on `/<robot_id>/cmd_vel`, with a TF tree and a 0.5 s command watchdog, so the head-on deadlock emerges *dynamically* instead of being a static spawn snapshot.

**Architecture:** Extend the existing odometry-only OmniGraph in `isaac/vgu_sim/ros_graphs.py::create_robot_ros_graph` into the full per-robot drive+sense graph specified by M6 FR6.7.4–6.7.6: `ROS2SubscribeTwist → DifferentialController → ArticulationController`, plus dynamic odom TF and static mount TF. The robot's wheel joints must be switched to velocity drive so the controller's wheel-velocity targets actually move the chassis. The 0.5 s command watchdog (FR6.4.8) mechanism is **resolved from the on-host node-interface capture (Task 1)**: a built-in `DifferentialController`/subscriber timeout input if one exists, otherwise a small ROS 2 watchdog **relay node** (Task 4) running with `use_sim_time` so the timeout is measured in simulation time. Lidar (`/scan`) is explicitly out of scope — that is Phase 2.

**Tech Stack:** Isaac Sim 6.0 embedded Python, OmniGraph (`omni.graph.core`), `isaacsim.ros2.bridge`, `isaacsim.robot.wheeled_robots`, `isaacsim.core.nodes`, USD (`pxr.UsdPhysics`), ROS 2 Jazzy, pytest.

---

## Reality Check — read before starting

This plan does **not** follow a pure local red-green-commit loop, because most of Phase 1 is OmniGraph wiring that can only be exercised inside Isaac Sim on the **GCP Isaac host** (see `project_m6_timeline_clock_blocker` and the existing run scripts `/tmp/run_sim_host.sh`). Each task below is tagged:

- **[OFFLINE]** — pure Python, real TDD, runs on any dev machine in CI.
- **[HOST]** — requires the GCP Isaac Sim host; "red/green" means observing ROS 2 topic behaviour, not pytest.

Two honesty notes, decided up front (see the spec's own §4 tension and the README §7 open questions):

1. **No isolated twist→wheel math.** Isaac's `DifferentialController` node owns and tests twist→wheel-velocity. We do **not** reimplement it — an isolated `twist_to_wheel_speeds()` unit test would assert against a copy of Isaac's own arithmetic and validate nothing about the robot (test theater). The spec's "unit-test the diff-drive math offline" line is satisfied **end-to-end** instead: a tiny labelled oracle (`forward_distance`, Task 2) predicts the expected odometry displacement, and the [HOST] integration assertion in Task 7 checks the robot actually moved that far. That exercises the *whole* drive path (subscribe → controller → articulation → physics → odom), which an isolated math test cannot.
2. **Config is already done.** `RobotAssetConfig` (`isaac/vgu_sim/config.py:182-197`) already carries every constant this phase needs — `wheel_left_joint`, `wheel_right_joint`, `wheel_radius_m=0.033`, `wheel_separation_m=0.160`, `max_linear_velocity_mps=0.22`, `max_angular_velocity_radps=2.84`, `wheel_drive_stiffness=0.0`, `wheel_drive_damping=1000.0`, `command_timeout_sec=0.5`. **Do not add new config.** Read these values from the passed-in `RobotAssetConfig`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `isaac/vgu_sim/ros_graphs.py` | Per-robot OmniGraph authoring | Modify `create_robot_ros_graph` (currently odometry-only, lines 96-152) |
| `isaac/vgu_sim/robot_drive.py` | USD wheel-joint velocity-drive authoring helper | Create |
| `isaac/vgu_sim/diff_drive_oracle.py` | Pure-Python test oracle: expected forward displacement | Create |
| `isaac/vgu_sim/cmd_vel_watchdog.py` | Pure stale-command core `watchdog_velocity` (fallback path, Task 4) — no rclpy import, offline-testable | Create |
| `isaac/vgu_sim/cmd_vel_watchdog_node.py` | Thin rclpy `CmdVelWatchdog` relay node wrapping the core (Branch B; authored at host time in Task 6) | Create (host) |
| `docs/specs/module4/phase1-drive-chain.md` | Record the verified OmniGraph node/attribute names (Task 1) | Modify (append a "Verified node interface" subsection) |
| `tests/unit/test_diff_drive_oracle.py` | Unit tests for the oracle | Create |
| `tests/unit/test_robot_drive.py` | Unit tests for the wheel-drive authoring helper (USD in-memory stage) | Create |
| `tests/unit/test_cmd_vel_watchdog.py` | Unit tests for the watchdog stale-command core | Create |
| `tests/simulation/stop_stub.py` | Twist publisher used to drive robots in-sim | Modify (add a fixed-twist drive mode for the Phase 1 test) |
| `tests/simulation/test_m4_phase1_drive.py` | [HOST] in-sim drive + watchdog acceptance test | Create |

---

## Task 1 — [HOST] Capture and record the verified node interface

**Why first:** The OmniGraph node *type names* are known, but the exact `inputs:`/`outputs:` attribute keys for `DifferentialController`, `ROS2SubscribeTwist`, and the TF publishers are version-sensitive (Isaac Sim 6.0 / `isaacsim.robot.wheeled_robots` v5.1.2). The spec mandates verification (CLAUDE.md "External Library Verification"). Writing graph wiring with guessed attribute names produces a graph that errors on first evaluation. This task turns the guesses into a recorded, authoritative reference that Tasks 5–6 transcribe.

**Files:**
- Modify: `docs/specs/module4/phase1-drive-chain.md` (append subsection "## 5. Verified node interface (Isaac Sim 6.0)")

- [ ] **Step 1: On the Isaac host, build the reference graph via the GUI wizard.** Launch Isaac Sim GUI (or the source build), load any turtlebot3_burger, and use **Tools → Robotics → ROS 2 OmniGraphs** to generate the "Differential Controller" graph and the "Odometry Publisher" graph (these wizards live in `isaacsim.robot.wheeled_robots.ui.menu_graphs` and `isaacsim.ros2.ui.Ros2OdometryGraph`). The wizard wires the exact production attribute names.

- [ ] **Step 2: Read back the generated attribute keys.** For each created node, run in the Script Editor:

```python
import omni.graph.core as og
g = og.get_graph_by_path("/Graphs/differential_controller")  # adjust to the wizard's path
for n in g.get_nodes():
    print(n.get_prim_path(), "::", n.get_type_name())
    for a in n.get_attributes():
        print("   ", a.get_name())
```

Repeat for the odometry/TF graph path.

- [ ] **Step 3: Record the verified names in the spec.** Append a table to `phase1-drive-chain.md` mapping each node to its exact attribute keys, e.g. (fill in from Step 2 — do **not** copy these guesses without confirming):

```markdown
## 5. Verified node interface (Isaac Sim 6.0, isaacsim.robot.wheeled_robots 5.1.2)

| Node type | Key inputs | Key outputs |
|---|---|---|
| isaacsim.ros2.bridge.ROS2SubscribeTwist | topicName, (context/nodeNamespace) | execOut, linearVelocity, angularVelocity |
| isaacsim.robot.wheeled_robots.DifferentialController | wheelRadius, wheelDistance, maxLinearSpeed, maxAngularSpeed, maxWheelSpeed, linearVelocity, angularVelocity, execIn | velocityCommand (2-vector: [left, right]) |
| isaacsim.core.nodes.IsaacArticulationController | targetPrim, jointNames (or jointIndices), velocityCommand, execIn | — |
| isaacsim.ros2.bridge.ROS2PublishTransformTree | topicName, parentPrim, targetPrims, execIn | — |
| isaacsim.ros2.bridge.ROS2PublishRawTransformTree | topicName, parentFrameId, childFrameId, translation, rotation, execIn | — |
```

Confirm specifically — these three answers are **deliverables** that select branches in later tasks:

- **(a) Twist vs TwistStamped:** does `ROS2SubscribeTwist` emit plain `Twist` or `TwistStamped` (the `use_stamped_cmd_vel` concern)? Selects Task 5's publisher message type.
- **(b) Watchdog primitive:** does `DifferentialController` (or `ROS2SubscribeTwist`) expose a command/message-timeout input? **Yes →** Task 4's watchdog collapses to one `SET_VALUES` line and the relay node is not built. **No →** Task 4 builds the relay node. Record the chosen branch.
- **(c) Odometry TF emission:** does the existing `pub_odom` (the `ROS2PublishOdometry`/odometry-graph the wizard generated) **already publish the `odom → base_footprint` dynamic TF** itself (the wizard's `_tf`/`publishOdomTF`-style flag)? If yes, Task 6 must **not** add a second `ROS2PublishTransformTree` for that edge or `/tf` will carry it twice — instead reuse/enable the existing emitter. Record which node owns `odom → base_footprint`.

- [ ] **Step 4: Commit the recorded reference.**

```bash
git add docs/specs/module4/phase1-drive-chain.md
git commit -m "docs: record verified Isaac 6.0 drive/TF OmniGraph node interface"
```

---

## Task 2 — [OFFLINE] Forward-displacement test oracle

**Why:** Gives the [HOST] integration test (Task 7) a numeric expectation to assert against, so "the robot moved" becomes "the robot moved the predicted distance ± tolerance". This is a **test utility**, not production code — it never runs on the drive path. It deliberately does **not** include a `twist_to_wheel_speeds` function: that would copy Isaac's own controller math into a unit test that nothing on the drive path consumes (see Reality Check note 1). The whole twist→wheel→motion chain is validated end-to-end in Task 7.

**Files:**
- Create: `isaac/vgu_sim/diff_drive_oracle.py`
- Test: `tests/unit/test_diff_drive_oracle.py`

- [ ] **Step 1: Write the failing tests.**

```python
import pytest

from isaac.vgu_sim.diff_drive_oracle import forward_distance


def test_forward_distance_integrates_constant_speed():
    # 0.10 m/s for 2.0 s = 0.20 m
    assert forward_distance(0.10, 2.0) == pytest.approx(0.20, rel=1e-9)


def test_forward_distance_zero_duration_is_zero():
    assert forward_distance(0.10, 0.0) == 0.0


def test_forward_distance_zero_speed_is_zero():
    assert forward_distance(0.0, 3.0) == 0.0
```

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_diff_drive_oracle.py -v`
Expected: FAIL — `ModuleNotFoundError: isaac.vgu_sim.diff_drive_oracle`.

- [ ] **Step 3: Implement the oracle.**

```python
"""Forward-displacement reference used as a TEST ORACLE only.

This module is never on the production drive path — Isaac's
`DifferentialController` OmniGraph node owns the in-sim twist→wheel math. This
function predicts the straight-line displacement of a constant forward command
so the in-sim integration test (tests/simulation/test_m4_phase1_drive.py) can
assert the robot actually moved that far end-to-end.
"""
from __future__ import annotations


def forward_distance(linear_x: float, duration_sec: float) -> float:
    """Return the straight-line distance covered at a constant forward speed.

    Args:
        linear_x: Forward body velocity in m/s.
        duration_sec: Drive duration in seconds.

    Returns:
        Distance in meters.
    """
    return linear_x * duration_sec
```

- [ ] **Step 4: Run to verify pass.**

Run: `pytest tests/unit/test_diff_drive_oracle.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit.**

```bash
git add isaac/vgu_sim/diff_drive_oracle.py tests/unit/test_diff_drive_oracle.py
git commit -m "test: add forward-distance oracle for in-sim drive assertions"
```

---

## Task 3 — [OFFLINE] Wheel-joint velocity-drive authoring helper

**Why:** A `DifferentialController` only emits wheel-velocity *targets*; the wheels move only if the USD wheel joints are configured for **velocity drive** (stiffness 0, damping > 0 — exactly the `wheel_drive_stiffness=0.0`, `wheel_drive_damping=1000.0` already in `RobotAssetConfig`). The turtlebot3 asset may ship with position drives or zero damping; this helper sets them deterministically. It is pure USD authoring on an in-memory stage, so it is unit-testable offline.

**Files:**
- Create: `isaac/vgu_sim/robot_drive.py`
- Test: `tests/unit/test_robot_drive.py`

- [ ] **Step 1: Write the failing test (in-memory USD stage, no Isaac runtime).**

```python
from pxr import Usd, UsdGeom, UsdPhysics

from isaac.vgu_sim.config import RobotAssetConfig
from isaac.vgu_sim.robot_drive import configure_wheel_velocity_drive


def _make_stage_with_wheel(joint_name: str) -> tuple[Usd.Stage, str]:
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")
    joint_path = f"/Robot/{joint_name}"
    UsdPhysics.RevoluteJoint.Define(stage, joint_path)
    return stage, joint_path


def test_sets_angular_drive_to_velocity_mode():
    cfg = RobotAssetConfig()
    stage, joint_path = _make_stage_with_wheel(cfg.left_wheel_joint)

    configure_wheel_velocity_drive(stage, "/Robot", cfg)

    drive = UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath(joint_path), "angular")
    assert drive.GetStiffnessAttr().Get() == cfg.wheel_drive_stiffness
    assert drive.GetDampingAttr().Get() == cfg.wheel_drive_damping


def test_missing_wheel_joint_raises():
    cfg = RobotAssetConfig()
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, "/Robot")  # no wheel joints

    with pytest.raises(ValueError, match="wheel_left_joint"):
        configure_wheel_velocity_drive(stage, "/Robot", cfg)
```

Add `import pytest` at the top.

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_robot_drive.py -v`
Expected: FAIL — `ModuleNotFoundError: isaac.vgu_sim.robot_drive`.

Note: this requires `pxr` (USD) which is available inside the Isaac Python env and in CI if `usd-core` is installed. If `pxr` is unavailable on the dev machine, mark the test with `pytest.importorskip("pxr")` at module top and run it on the host.

- [ ] **Step 3: Implement the helper.**

```python
"""Author velocity drives on a robot's wheel joints.

A DifferentialController emits wheel *velocity* targets; the wheels only
respond if their USD angular drive is in velocity mode (zero stiffness,
non-zero damping). Constants come from RobotAssetConfig (M6 FR6.4.7).
"""
from __future__ import annotations

from pxr import Usd, UsdPhysics

from isaac.vgu_sim.config import RobotAssetConfig


def configure_wheel_velocity_drive(
    stage: Usd.Stage,
    robot_prim_path: str,
    config: RobotAssetConfig,
) -> None:
    """Set both wheel joints to velocity drive under `robot_prim_path`.

    Args:
        stage: The USD stage holding the robot.
        robot_prim_path: Root prim of the robot subtree.
        config: Asset config supplying joint names and drive gains.

    Raises:
        ValueError: If either named wheel joint is not found in the subtree.
    """
    root = stage.GetPrimAtPath(robot_prim_path)
    by_name = {
        p.GetName(): p
        for p in Usd.PrimRange(root)
        if p.IsA(UsdPhysics.RevoluteJoint)
    }
    for label, joint_name in (
        ("wheel_left_joint", config.left_wheel_joint),
        ("wheel_right_joint", config.right_wheel_joint),
    ):
        prim = by_name.get(joint_name)
        if prim is None:
            raise ValueError(
                f"{label}={joint_name!r} not found under {robot_prim_path}"
            )
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        # Velocity control: zero position stiffness, non-zero damping.
        drive.CreateStiffnessAttr(config.wheel_drive_stiffness)
        drive.CreateDampingAttr(config.wheel_drive_damping)
        drive.CreateTargetVelocityAttr(0.0)
```

- [ ] **Step 4: Run to verify pass.**

Run: `pytest tests/unit/test_robot_drive.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit.**

```bash
git add isaac/vgu_sim/robot_drive.py tests/unit/test_robot_drive.py
git commit -m "feat: author wheel velocity drives from RobotAssetConfig gains"
```

---

## Task 4 — [OFFLINE] Command-watchdog mechanism

**Branch on Task 1(b).** The watchdog mechanism is not pre-decided — it depends on what Task 1 found:

- **Branch A — built-in timeout exists.** If `DifferentialController`/`ROS2SubscribeTwist` exposes a message-timeout input, the watchdog is one `SET_VALUES` line in Task 6 (`("diff_ctrl.inputs:<verified_timeout_attr>", config.command_timeout_sec)`). **Skip the rest of this task** — do not build the relay node — and record "Branch A" in the spec's verified-interface subsection.
- **Branch B — no built-in timeout (build this task).** Add a small ROS 2 **watchdog relay node**: it subscribes `/<robot_id>/cmd_vel`, republishes to `/<robot_id>/cmd_vel_safe`, and publishes a zero `Twist` once no command has arrived for `config.command_timeout_sec`. The Isaac graph subscribes to `/<robot_id>/cmd_vel_safe` (Task 5). Run it with `use_sim_time=True` so the timeout is measured in *simulation* time (FR6.4.8); Isaac publishes `/clock`. The public `/cmd_vel` contract from the README interface table is unchanged — `cmd_vel_safe` is an internal hop.

The stale-command decision is pure and unit-testable (built **now**, OFFLINE); the rclpy plumbing is thin and lives in a **separate** module authored at host time in Task 6 (so the offline unit test never imports `rclpy`). This split is the CLAUDE.md ROS 2 rule: keep reusable logic outside node classes when it can be tested without ROS 2.

**Files (Branch B only):**
- Create (OFFLINE, now): `isaac/vgu_sim/cmd_vel_watchdog.py` — the pure `watchdog_velocity` core, no `rclpy` import.
- Test (OFFLINE, now): `tests/unit/test_cmd_vel_watchdog.py`
- Create (HOST, Task 6): `isaac/vgu_sim/cmd_vel_watchdog_node.py` — the thin `CmdVelWatchdog` rclpy node importing `watchdog_velocity`.

- [ ] **Step 1: Write the failing tests for the pure core.**

```python
from isaac.vgu_sim.cmd_vel_watchdog import watchdog_velocity

TIMEOUT = 0.5


def test_no_command_yet_is_zero():
    assert watchdog_velocity(None, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_fresh_command_passes_through():
    assert watchdog_velocity(0.1, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)


def test_stale_command_is_zeroed():
    assert watchdog_velocity(0.6, (0.2, 0.1), TIMEOUT) == (0.0, 0.0)


def test_exactly_at_timeout_still_passes():
    # stale only when strictly older than the timeout
    assert watchdog_velocity(0.5, (0.2, 0.1), TIMEOUT) == (0.2, 0.1)
```

- [ ] **Step 2: Run to verify failure.**

Run: `pytest tests/unit/test_cmd_vel_watchdog.py -v`
Expected: FAIL — `ModuleNotFoundError: isaac.vgu_sim.cmd_vel_watchdog`.

- [ ] **Step 3: Implement the pure core** (`isaac/vgu_sim/cmd_vel_watchdog.py`). The rclpy node is authored separately at host time (Task 6) so this module imports cleanly offline.

```python
"""Command watchdog core (fallback when no built-in controller timeout).

Pure stale-command decision used by the rclpy relay node in
`cmd_vel_watchdog_node.py`: forward the last `/<robot_id>/cmd_vel` to
`/<robot_id>/cmd_vel_safe` until no command has arrived for
command_timeout_sec, then zero it (FR6.4.8). Kept rclpy-free so it is
unit-testable without ROS 2 (CLAUDE.md: logic outside node classes).
"""
from __future__ import annotations


def watchdog_velocity(
    elapsed_sec: float | None,
    commanded: tuple[float, float],
    timeout_sec: float,
) -> tuple[float, float]:
    """Return the (linear_x, angular_z) to forward, zeroed if stale.

    Args:
        elapsed_sec: Simulation seconds since the last command, or None if no
            command has been received yet.
        commanded: The last commanded `(linear_x, angular_z)`.
        timeout_sec: Stale threshold in seconds.

    Returns:
        `commanded` if a command arrived within `timeout_sec`, else `(0.0, 0.0)`.
    """
    if elapsed_sec is None or elapsed_sec > timeout_sec:
        return (0.0, 0.0)
    return commanded
```

The thin rclpy node below goes in a **separate** file `isaac/vgu_sim/cmd_vel_watchdog_node.py`, authored and verified at [HOST] in Task 6 — not created or imported in this OFFLINE task:

```python
from isaac.vgu_sim.cmd_vel_watchdog import watchdog_velocity

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class CmdVelWatchdog(Node):
    def __init__(self, robot_id: str, timeout_sec: float) -> None:
        super().__init__(f"{robot_id}_cmd_vel_watchdog")
        self._timeout = timeout_sec
        self._last: tuple[float, float] = (0.0, 0.0)
        self._last_stamp: float | None = None
        self._pub = self.create_publisher(Twist, f"/{robot_id}/cmd_vel_safe", 10)
        self.create_subscription(Twist, f"/{robot_id}/cmd_vel", self._on_cmd, 10)
        self.create_timer(0.05, self._tick)  # 20 Hz relay/guard

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_cmd(self, msg: Twist) -> None:
        self._last = (msg.linear.x, msg.angular.z)
        self._last_stamp = self._now()

    def _tick(self) -> None:
        elapsed = None if self._last_stamp is None else self._now() - self._last_stamp
        vx, wz = watchdog_velocity(elapsed, self._last, self._timeout)
        out = Twist()
        out.linear.x, out.angular.z = vx, wz
        self._pub.publish(out)
```

- [ ] **Step 4: Run to verify pass.**

Run: `pytest tests/unit/test_cmd_vel_watchdog.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit.**

```bash
git add isaac/vgu_sim/cmd_vel_watchdog.py tests/unit/test_cmd_vel_watchdog.py
git commit -m "feat: add cmd_vel watchdog stale-command core"
```

---

## Task 5 — [HOST] Extend the graph: cmd_vel → differential → articulation

**Files:**
- Modify: `isaac/vgu_sim/ros_graphs.py` — `create_robot_ros_graph` (lines 96-152). Keep the existing odometry nodes; add the drive subgraph. Use the **verified** attribute names from Task 1.

- [ ] **Step 1: Call the wheel-drive helper before building the graph.** At the top of `create_robot_ros_graph`, after resolving `chassis_path`, ensure wheel joints are velocity-driven:

```python
from isaac.vgu_sim.robot_drive import configure_wheel_velocity_drive

configure_wheel_velocity_drive(stage, robot_prim_path, config)
```

- [ ] **Step 2: Add the drive nodes to the existing `og.Controller.edit` call.** Extend `CREATE_NODES` with the subscribe/controller/articulation nodes and wire them. Transcribe attribute names from Task 1; the shape (confirm each `inputs:`/`outputs:` key against the recorded reference):

```python
# --- drive chain (M6 FR6.7.4) ---
("sub_twist",   "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
("diff_ctrl",   "isaacsim.robot.wheeled_robots.DifferentialController"),
("art_ctrl",    "isaacsim.core.nodes.IsaacArticulationController"),
```

CONNECT (verify exact attribute names against Task 1):

```python
("on_tick.outputs:tick",            "sub_twist.inputs:execIn"),
("sub_twist.outputs:execOut",       "diff_ctrl.inputs:execIn"),
("sub_twist.outputs:linearVelocity",  "diff_ctrl.inputs:linearVelocity"),
("sub_twist.outputs:angularVelocity", "diff_ctrl.inputs:angularVelocity"),
("diff_ctrl.outputs:execOut",       "art_ctrl.inputs:execIn"),
("diff_ctrl.outputs:velocityCommand", "art_ctrl.inputs:velocityCommand"),
```

SET_VALUES (constants from `config`, names from Task 1):

```python
# topicName: `/{robot_id}/cmd_vel` for Branch A (built-in timeout) or no
# watchdog yet; `/{robot_id}/cmd_vel_safe` for Branch B (Task 4 relay in front).
("sub_twist.inputs:topicName",     f"/{robot_id}/cmd_vel"),
("diff_ctrl.inputs:wheelRadius",   config.wheel_radius_m),
("diff_ctrl.inputs:wheelDistance", config.wheel_separation_m),
("diff_ctrl.inputs:maxLinearSpeed",  config.max_linear_velocity_mps),
("diff_ctrl.inputs:maxAngularSpeed", config.max_angular_velocity_radps),
("art_ctrl.inputs:targetPrim",     chassis_path),
("art_ctrl.inputs:jointNames",     [config.left_wheel_joint, config.right_wheel_joint]),
```

- [ ] **Step 3: [HOST] Bring up the sim and drive one robot.** On the GCP host, launch the sim (`/tmp/run_sim_host.sh`, head_on_deadlock), then from the container publish a steady forward twist:

```bash
# Branch A / no watchdog yet: publish to /cmd_vel. Branch B: the graph listens on
# /cmd_vel_safe, so publish there to test the drive chain in isolation (or start the
# Task 4 watchdog and publish /cmd_vel through it).
ros2 topic pub -r 10 /robot_1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.1}}'
```

Expected (green): `ros2 topic echo /robot_1/odom` shows `pose.pose.position` increasing along the robot's heading; the camera feed shows robot_1 moving. Expected before the fix (red): odom static.

- [ ] **Step 4: Commit.**

```bash
git add isaac/vgu_sim/ros_graphs.py
git commit -m "feat: add cmd_vel drive chain to per-robot Isaac graph (FR6.7.4)"
```

---

## Task 6 — [HOST] Add TF tree + in-graph watchdog

**Files:**
- Modify: `isaac/vgu_sim/ros_graphs.py` — same `create_robot_ros_graph`.

- [ ] **Step 1: Add the dynamic odom→base_footprint TF and static mount TF.** Per FR6.7.5–6.7.6, the tree is `robot_N/odom → base_footprint (dynamic, /tf)` and `base_footprint → base_link → base_scan (static, /tf_static)`.

  **First check Task 1(c):** if the existing `pub_odom`/odometry graph **already emits** `odom → base_footprint` on `/tf`, do **not** add a `ROS2PublishTransformTree` for that edge — that would double-publish the dynamic transform and make TF flap. In that case skip the dynamic node here (enable the existing emitter if it is off) and add only the static node. Add (verify node + attribute names against Task 1):

```python
# Add the dynamic publisher ONLY if pub_odom does not already emit odom->base_footprint (Task 1c).
("pub_tf",     "isaacsim.ros2.bridge.ROS2PublishTransformTree"),     # dynamic /tf
("pub_tf_static", "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"), # /tf_static
```

Wire `on_tick.outputs:tick` into each added node's `execIn`; set `pub_tf` `parentPrim`/`targetPrims` to the odom→base_footprint pair and topic `/tf`; set the static publisher for the fixed `base_link`/`base_scan` mount offsets on `/tf_static`. Frame ids use the `{robot_id}/...` prefix already used by `pub_odom` (FR6.7.7 uniqueness via prefixes).

- [ ] **Step 2: Wire the watchdog per the branch chosen in Task 4.**
  - **Branch A (built-in timeout, Task 1b = yes):** add exactly one `SET_VALUES` line to the drive subgraph and keep `sub_twist.inputs:topicName = /<id>/cmd_vel`:

    ```python
    ("diff_ctrl.inputs:<verified_timeout_attr>", config.command_timeout_sec),
    ```

  - **Branch B (relay node, Task 1b = no):** no graph node is added here. Instead (i) set `sub_twist.inputs:topicName = f"/{robot_id}/cmd_vel_safe"` in Task 5, (ii) author `isaac/vgu_sim/cmd_vel_watchdog_node.py` — the thin `CmdVelWatchdog` rclpy node wrapping the Task 4 `watchdog_velocity` core (code block in Task 4 Step 3) — and (iii) launch it per robot alongside the sim (in the runner's bring-up or the launch file) with `use_sim_time=True`. Record "Branch B" in a comment at the graph's `sub_twist` node.

- [x] **Step 3: [HOST] Verify TF and watchdog.** ✅ PASS on GCP host (2026-06-19).
  - TF: `robot_1/odom → robot_1/base_footprint` updates on `/tf` while driving a curve; ROS-received TF yaw tracked the full 13°→164° sweep at a steady −1.0° offset vs `/odom`. In-process `pub_tf.inputs:rotation` equalled `odom_compute.outputs:orientation` to 0.0° (no quaternion-convention scramble); source orientation matched the path tangent to 9.3° (the residual is the expected chord-vs-tangent finite-difference lag). `/tf_static` carries `base_link`/`base_scan`.
  - Watchdog: a single non-repeating twist coasted to a stop; `/robot_1/cmd_vel_safe` (and `diff_ctrl.outputs:velocityCommand`) returned to 0 in 0.567 s of sim time after commands stopped (~0.5 s timeout + relay tick).
  - Verified with an ephemeral in-sim probe (`isaac/scripts/probe_tf_watchdog.py`, not committed; removed from the host after the run). Note for Task 7: the ROS `/tf` subscriber must drain all ready callbacks per step (≥2 msgs/step: `/odom` + `/tf`) or the lower-priority `/tf` queue starves and appears frozen.

- [ ] **Step 4: Commit.**

```bash
git add isaac/vgu_sim/ros_graphs.py
git commit -m "feat: add TF tree and 0.5s cmd_vel watchdog to robot graph (FR6.7.5, FR6.4.8)"
```

---

## Task 7 — [HOST] In-sim drive + watchdog acceptance test

**Files:**
- Modify: `tests/simulation/stop_stub.py` — add a `FixedTwistDriver` (or a `drive_forward` mode) that publishes a constant `Twist` to `/<robot_id>/cmd_vel` for a fixed duration, mirroring the existing `StopStubNode` structure (reuse its publisher setup; do not duplicate spin helpers).
- Create: `tests/simulation/test_m4_phase1_drive.py`

- [x] **Step 1: Add the fixed-twist driver to `stop_stub.py`.** A small node that publishes `linear.x = speed` to each `/<rid>/cmd_vel` at 10 Hz; speed-capped at `0.15` like `StopStub` (reuse the existing guard). Done (`997fb7e`): `FixedTwistDriver` mirrors `StopStubNode` (10 Hz timer, `request_stop` cancels the timer so the watchdog — not the driver — zeroes the wheels), and the `>0.15 → ValueError` guard was extracted to a shared `_check_speed` reused by both. Offline guard test added in `tests/unit/test_m6_stop_stub.py::TestFixedTwistDriver`.

- [x] **Step 2: Write the acceptance test.** Done (`997fb7e`): `tests/simulation/test_m4_phase1_drive.py`. No `isaac_host` fixture exists, so — as this step sanctions — the test is **marked-skip** and its docstring documents the full manual [HOST] procedure (start pose → `FixedTwistDriver` → displacement vs `forward_distance(0.10, 3.0)=0.30 m` `rel=0.20` → `request_stop` → watchdog stop `<0.01 m/s`), including the Task 6 carry-forward to drain all rclpy callbacks per step. The drive chain + watchdog were already verified on host in Task 6 (see report). Use the **`isaac_sim` + `ros2` markers** registered in `tests/simulation/conftest.py` (there is no `simulation` marker; the existing `test_m6_scenarios.py` stacks `@pytest.mark.isaac_sim` / `@pytest.mark.ros2`). It drives `robot_1` forward for `T` seconds, records start/end `/robot_1/odom`, asserts the integrated displacement matches the oracle within tolerance, then asserts the watchdog stop:

```python
import pytest

from isaac.vgu_sim.diff_drive_oracle import forward_distance

SPEED = 0.10
DRIVE_SEC = 3.0


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_robot_drives_predicted_distance_then_watchdog_stops(isaac_host):
    start = isaac_host.odom("robot_1")
    isaac_host.drive_forward("robot_1", SPEED, DRIVE_SEC)
    moved = isaac_host.odom("robot_1").distance_to(start)
    assert moved == pytest.approx(forward_distance(SPEED, DRIVE_SEC), rel=0.20)

    # stop commanding; watchdog must zero the wheels within ~0.5s sim time
    isaac_host.wait_sim_seconds(1.0)
    assert abs(isaac_host.odom("robot_1").linear_velocity) < 0.01
```

`isaac_host` is a fixture wrapping the running sim + ROS 2 (mirror the existing simulation test harness in `tests/simulation/`; if no such fixture exists yet, the test documents the manual [HOST] procedure and is marked `skip` with a reason pointing at the manual steps in Tasks 5–6). The 20 % tolerance absorbs spin-up/spin-down and friction.

- [x] **Step 3: [HOST] Run it.** N/A for the as-built test: it is a documented-**skip**, so it `SKIPPED`s on the host exactly as it does in CI and produces no new signal beyond the Task 6 host verification. Verified locally it collects and skips cleanly (`pytest tests/simulation/test_m4_phase1_drive.py -v` → 1 skipped). The equivalent live verification was performed manually on the host in Task 6 (`docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md`).

Run: `pytest tests/simulation/test_m4_phase1_drive.py -v -m "isaac_sim and ros2"`
Expected: PASS on the Isaac host; deselected/SKIPPED in CI (markers gate it like the M6 scenario tests).

- [x] **Step 4: Commit.** Done (`997fb7e`).

```bash
git add tests/simulation/stop_stub.py tests/simulation/test_m4_phase1_drive.py
git commit -m "test: in-sim Phase 1 drive + watchdog acceptance test"
```

---

## Task 8 — Update docs and close the gap-analysis row

**Files:**
- Modify: `docs/specs/module4/README.md` — flip the phase1 status and the gap-analysis row.
- Modify: `docs/specs/module4/phase1-drive-chain.md` — mark §4 testing as implemented; cross-link the test.

- [ ] **Step 1:** In README §2 change the phase1 row Status `Planned → Done`; in §3.2 update "Isaac `/cmd_vel` drive chain + TF" from "Specified, not built" to "Built (Phase 1)".

- [ ] **Step 2: Commit.**

```bash
git add docs/specs/module4/README.md docs/specs/module4/phase1-drive-chain.md
git commit -m "docs: mark M4 Phase 1 drive chain implemented"
```

---

## Self-Review

- **Spec coverage** (`phase1-drive-chain.md`): §2 drive+sense graph → Tasks 5–6; §3 diff-drive constants → read from `RobotAssetConfig` in Task 5 (constants already exist, FR6.4.7); §3 watchdog → Tasks 4 + 6 (FR6.4.8); §3 TF tree → Task 6 (FR6.7.5–6.7.6, with the double-publish guard from Task 1c); §4 offline diff-drive math → addressed end-to-end (Task 7 odom-displacement vs the Task 2 `forward_distance` oracle), not as an isolated `twist_to_wheel_speeds` copy of Isaac's math; §4 in-sim drive + watchdog test → Task 7. Lidar correctly excluded (Phase 2). Twist-vs-TwistStamped verify → Task 1(a).
- **No placeholders in the hardest task:** the watchdog is no longer a vague "add a node that tracks sim-time." Task 4 resolves it from Task 1(b) into one of two concrete branches — a single `SET_VALUES` line (built-in timeout) or a fully-specced, unit-tested `CmdVelWatchdog` relay node — and Task 6 Step 2 wires exactly the chosen branch.
- **Decisions surfaced, not hidden:** the "no isolated twist→wheel unit test" and "watchdog mechanism is Task-1-contingent" choices are stated with rationale and revisit conditions, matching the README §7 open questions.
- **Verification before fiction:** Task 1 records real attribute names (and the Twist/TwistStamped, timeout, and odom-TF facts) before Tasks 5–6 transcribe them — no guessed OmniGraph keys, no guessed watchdog primitive, committed as production wiring.
- **Type consistency:** `forward_distance` (Task 2), `configure_wheel_velocity_drive` (Task 3), and `watchdog_velocity`/`CmdVelWatchdog` (Task 4) are referenced by the same names in Tasks 5–7. The acceptance test uses the real `isaac_sim`/`ros2` markers from `conftest.py`, not a non-existent `simulation` marker.
- **Open risk:** if Task 1 reveals `ROS2SubscribeTwist` only accepts `TwistStamped` on Jazzy, Task 5's publisher commands (and the Phase 2 Nav2 `cmd_vel`) must switch to `TwistStamped`; this is flagged in Task 1(a) and the phase2 spec's verify-note.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-m4-phase1-drive-chain.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks. Note Tasks 1, 5, 6, 7 are **[HOST]** and need the GCP Isaac Sim host; Tasks 2, 3, and 4 (Branch B) are **[OFFLINE]** and run anywhere. Task 4 is gated on Task 1(b): if Task 1 finds a built-in timeout it collapses to a one-liner in Task 6.
2. **Inline Execution** — execute in this session with checkpoints; the [OFFLINE] tasks (2, 3, and 4's pure core) can be done immediately, the [HOST] tasks batched for a sim session.

Which approach?
