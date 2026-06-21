# Module 4 — Phase 2 — Nav2 Stack & Adapter

**Prepared:** 2026-06-19

**Revision history:**

- Initial draft: Phase 2 of the M4 Nav2 rollout — RTX lidar, map, localization,
  per-robot Nav2, and the `Nav2Adapter` interface. Split out of
  `module4_navigation.md`.

---

## 1. Goal

Robots autonomously navigate to `(x, y, yaw)` goals via Nav2. Requires Phase 1
([phase1-drive-chain.md](phase1-drive-chain.md)) plus sensing, a map,
localization, and a per-robot Nav2 stack driven by M4's `Nav2Adapter`.

See [README.md](README.md) for the module overview, interfaces, dependencies, and
risks.

---

## 2. Sensing — RTX 2D lidar

Author the lidar (M6 FR6.4.9) → `/<robot_id>/scan`:

- Frame `robot_N/base_scan`, 360° FOV, 1° resolution, 10 Hz, range `0.12–3.5 m`.
- Keep the ArUco plate out of the scan plane **and** out of RTX lidar visibility
  (FR6.4.10): RTX lidar raytraces rendered geometry, not PhysX colliders, so
  disabling collision alone does not keep the plate out of `/<robot_id>/scan`.
  Validate `/scan` is clean before trusting Nav2 costmaps.

---

## 3. Per-robot namespacing

Multi-robot Nav2 runs one **namespaced** stack per robot — its own costmaps,
planner, controller, and BT navigator under `/<robot_id>/...`, sharing `/tf` and
`/tf_static` (uniqueness via frame prefixes, FR6.7.7). Verify the exact
namespaced-bringup mechanism against the Nav2 Jazzy docs before building;
multi-robot bringup conventions change across distros.

- Action server per robot: `/<robot_id>/navigate_to_pose`
  (`nav2_msgs/action/NavigateToPose`).
- Costmap sensor source: `/<robot_id>/scan`.
- Robot footprint ≈ `0.14 m × 0.18 m` Burger base.

---

## 4. Map

- **Option A (recommended for PoC):** author a `map.yaml` + `map.pgm` once from the
  known warehouse geometry (obstacle layout is deterministic; see
  `isaac/assets/obstacles/`). Served by `nav2_map_server`.
- **Option B:** run `slam_toolbox` online. Heavier; unnecessary while the map is
  static and known.

---

## 5. Localization (`map → odom`)

- **Option A (recommended for PoC):** publish a ground-truth `map → odom` TF from
  Isaac. Isaac knows each robot's true pose, so a small publisher emits a perfect
  `map → odom` per robot, bypassing AMCL and removing a large tuning surface.
  Justified because the goal is to test the *reasoning → motion* loop, not
  localization. This is a deliberate PoC shortcut, not a real-robot path.
- **Option B:** AMCL (`nav2_amcl`) per robot, consuming `/<robot_id>/scan` + the
  map. Realistic but adds particle-filter tuning and an initial-pose step.

---

## 6. Nav2 parameters

One params file per robot (or a templated file with namespace substitution):
controller (DWB or MPPI), planner (NavFn or Smac), both costmaps (global + local)
with the obstacle layer fed by `/<robot_id>/scan`, the BT navigator, and behavior
server. The controller's commanded velocity must stay at or below the
`safety.yaml` cap (`max_linear_velocity_mps: 0.2`), which is set deliberately
*below* the FR6.4.7 mechanical maximum (`0.22 m/s`) to leave margin; the two are
not equal and Nav2's `max_vel_x` should track the 0.2 safety cap, not 0.22.

**Verify — `cmd_vel` message type.** Confirm whether Jazzy Nav2 publishes
`geometry_msgs/Twist` or `TwistStamped` on `/<robot_id>/cmd_vel` (the
`use_stamped_cmd_vel` toggle; default has moved across distros) and match it to
the Isaac `ROS2SubscribeTwist` side from
[phase1-drive-chain.md](phase1-drive-chain.md). A mismatch silently drops every
command.

---

## 7. `Nav2Adapter` Interface (M4)

Replace the placeholder (`nav2_adapter.py`) with an action-client wrapper. The
adapter is the only component that talks to Nav2; the command bus and safety
monitor talk to the adapter.

- `send_goal(robot_id, x, y, yaw) -> GoalHandle` — sends a `NavigateToPose` goal
  to `/<robot_id>/navigate_to_pose`; pre-empts any active goal for that robot.
- `send_waypoints(robot_id, waypoints)` — `FollowWaypoints` action for a route
  (M3 `reroute`/`convoy` strategies).
- `cancel(robot_id)` — cancels the active goal (used by the safety monitor on a
  `min_distance_m` violation, and on `command_timeout_sec`).
- Reports goal lifecycle (accepted / succeeded / aborted) back to M5 by having
  the command bus publish `CoordinationStatus` on `/coordination/status`
  (`command_id`, `robot_id`, `status`, `detail`); M5's `CommandTracker` consumes
  it. The adapter surfaces raw action feedback only to the command bus, never to
  M5 directly.

Boundary rules (CLAUDE.md): keep Nav2/action specifics inside the adapter; the
command bus and M5 see only grounded commands and lifecycle status, never raw
action feedback. M4 issues goals and pre-empts; it does not stream `cmd_vel`
directly while Nav2 owns a robot.

---

## 8. Testing & Validation

Assert `/<robot_id>/scan` is published and clean, the map loads, and a single
`NavigateToPose` goal drives the robot to within tolerance of a free-space goal
with obstacles present. Mark as a `ros2`/simulation test, not a unit test.

---

## 9. Verified host setup

**Status: BLOCKED.** `ros-jazzy-navigation2` / `ros-jazzy-nav2-bringup` cannot be
installed via the official apt repo on the current host OS. This phase's
heavyweight-dependency gate (CLAUDE.md "Dependencies") fails as specified and
needs rework before any Isaac authoring proceeds.

### Host

- GCP VM `isaacautomator-vgu-gcp2-isaac-workstation-vm` (zone `us-central1-a`,
  project `vlm-swarm`).
- OS: Ubuntu 22.04.5 LTS (Jammy Jellyfish) — confirmed via `/etc/os-release`.
- No ROS2 of any distro preinstalled (`/opt/ros` does not exist;
  `/etc/apt/sources.list.d/` had no ROS entry before this task).

### What was attempted

1. Checked for an existing ROS apt repo — none found (`NO_ROS_REPO`).
2. Registered the ROS2 apt repo using the **current official method**
   (`ros2-apt-source` deb package, per
   [docs.ros.org Jazzy Ubuntu binary install](https://docs.ros.org/en/jazzy/Installation/Alternatives/Ubuntu-Install-Binary.html)),
   superseding an earlier manual-keyring attempt that pointed at the same
   underlying repo:

   ```bash
   sudo apt-get update && sudo apt-get install -y curl
   export ROS_APT_SOURCE_VERSION=1.2.0   # latest tag from
       # https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest
   curl -L -o /tmp/ros2-apt-source.deb \
     "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.jammy_all.deb"
   sudo dpkg -i /tmp/ros2-apt-source.deb
   sudo apt-get update
   ```

   This installed cleanly and registered
   `deb822` source `/etc/apt/sources.list.d/ros2.sources`
   (`URIs: http://packages.ros.org/ros2/ubuntu`, `Suites: jammy`,
   `Components: main`) with an embedded signing key — the modern equivalent of
   the older manual-keyring instructions, same repo URL.

3. `sudo apt-get install -y ros-jazzy-ros-base ros-jazzy-navigation2 ros-jazzy-nav2-bringup`
   failed:

   ```
   E: Unable to locate package ros-jazzy-ros-base
   E: Unable to locate package ros-jazzy-navigation2
   E: Unable to locate package ros-jazzy-nav2-bringup
   ```

4. Root cause confirmed by inspecting the downloaded apt index directly:

   ```bash
   grep '^Package: ros-' /var/lib/apt/lists/packages.ros.org_ros2_ubuntu_dists_jammy_main_binary-amd64_Packages \
     | sed -E 's/^Package: ros-([a-z]+)-.*/\1/' | sort -u
   # -> build dev humble iron rolling
   ```

   The `packages.ros.org/ros2/ubuntu jammy` index — the correct, current,
   officially-registered repo — carries **no `ros-jazzy-*` packages at all**.
   This is not a misconfiguration: ROS2 Jazzy's Tier-1 supported platform is
   Ubuntu 24.04 (Noble); Ubuntu 22.04 (Jammy) only gets Humble/Iron/Rolling
   binaries from the official repo. Jazzy on Jammy would require a Tier-3
   source build or Docker, not an apt install.

### Smoke test (Step 2) and version capture (Step 3)

Not run — blocked upstream of this step. There is no `ros-jazzy-navigation2`
package to install, so `ros2 launch nav2_bringup bringup_launch.py --show-args`
cannot be exercised on this host with Jazzy.

### Decision needed (plan-level, not executable by this task)

One of:

- Reprovision the Isaac host as Ubuntu 24.04 (Noble) so `ros-jazzy-*` apt
  packages are available, or
- Retarget this phase to ROS2 Humble (`ros-humble-navigation2`,
  `ros-humble-nav2-bringup`), which **is** available on this Jammy host, or
- Build ROS2 Jazzy from source (Tier-3) on Jammy.

This task does not pick a direction — it stops at the gate per the brief
("If install fails, stop and report — do not substitute a different package
set without updating this plan").
