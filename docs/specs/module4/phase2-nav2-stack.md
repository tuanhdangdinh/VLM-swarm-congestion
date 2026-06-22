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
namespaced-bringup mechanism against the Nav2 Humble docs before building (see
§9 — this phase targets Humble, not Jazzy, on this host);
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

### Correction (2026-06-22, Task 5): `/odom` is spawn-relative, not absolute-world

The Phase 2 plan's "Reality Check" locked in a simplification of Option A:
since `IsaacComputeOdometry` reads the chassis's pose directly (no encoder
integration), the plan assumed `/<robot_id>/odom` already equals the
absolute world/map-frame pose, making `map → odom` a trivial **static
identity** transform — no publisher needed.

Task 5 verified this for real and found it **false**. 300 in-process
`nav_msgs/Odometry` reads of `/robot_1/odom` over 10s of sim time all show
`position ≈ (0, 0, 0)`, while the chassis's true USD world pose (cross-checked
independently via `ground_truth.jsonl`) stays at `x=-0.6` the entire time —
the robot is stationary at its spawn pose, not at the origin.
`IsaacComputeOdometry` computes pose **relative to its reference at node
initialization** (i.e., spawn-relative, the same semantics as real wheel
encoders), not absolute-world. The "no drift, reads the chassis directly"
property is real (confirmed: it doesn't integrate noisy encoder ticks), but
that only means *zero accumulated error relative to its own spawn-time
reference* — not that the reference is the world origin.

**Corrected design:** `map → <robot_id>/odom` must be a static transform
equal to each robot's **spawn pose** (`x, y, yaw` from the scenario config),
not identity. This is still Option A's spirit (no AMCL, no tuning surface) —
only the transform *value* changes, from identity to
`(spawn_x, spawn_y, spawn_yaw)`. Whether `IsaacComputeOdometry`'s actual
zero-reference exactly equals the scenario YAML's nominal spawn pose, or some
other pose taken at first node evaluation, was not independently verified —
re-check before treating "spawn pose" as exact if precision matters.

### Independent, also-blocking finding: `/odom` and dynamic `/tf` stamped 0

Task 5 found `/robot_1/odom` and the dynamic `odom → base_footprint` TF edge
are published with `header.stamp = 0` continuously throughout multi-hundred-
second runs (not a startup transient) — confirmed via repeated
`[Warning] Frame robot_1/odom Timestamp is invalid. Timestamp 0 will be
neglected for all published ROS messages` log lines, while `sim_time` itself
correctly advances (per `ground_truth.jsonl` and the in-process probe's own
elapsed-time tracking). `tf2` drops stamp-0 transforms outright, so the
`odom → base_footprint` edge does not survive into the TF buffer Nav2/`tf2_echo`
read from — this **independently blocks** the localization chain regardless
of how `map → odom` is corrected above. Task 4's RTX lidar gets correctly
advancing `header.stamp`s from a structurally similar graph, but that sensor
stamps itself via its own Replicator-writer clock, not via the
`on_tick → IsaacReadSimulationTime → pub_odom/pub_tf.inputs:timeStamp` wiring
that the drive/odom graph uses — these are different stamping mechanisms, so
Task 4's success does not imply this one works. Root cause not yet
determined; needs its own host investigation (likely in
`isaac/vgu_sim/ros_graphs.py`'s `create_robot_ros_graph` clock wiring) before
any Nav2 task that depends on a valid TF tree can proceed.

---

## 6. Nav2 parameters

One params file per robot (or a templated file with namespace substitution):
controller (DWB or MPPI), planner (NavFn or Smac), both costmaps (global + local)
with the obstacle layer fed by `/<robot_id>/scan`, the BT navigator, and behavior
server. The controller's commanded velocity must stay at or below the
`safety.yaml` cap (`max_linear_velocity_mps: 0.2`), which is set deliberately
*below* the FR6.4.7 mechanical maximum (`0.22 m/s`) to leave margin; the two are
not equal and Nav2's `max_vel_x` should track the 0.2 safety cap, not 0.22.

**Verify — `cmd_vel` message type.** Confirm whether Humble Nav2 publishes
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

### Resolution: retarget to ROS2 Humble

Isaac Automator (the deployment tool used for this host) has no Ubuntu 24.04
option — Isaac Sim 6.0 itself targets Ubuntu 22.04. Reprovisioning to Noble is
not available. Checked Isaac Sim's own `/home/ubuntu/IsaacSim/setup_ros_env.sh`
on the host:

```bash
DEFAULT_ROS_DISTRO="jazzy"
if [[ "$UBUNTU_VERSION" == "22.04" ]]; then
    DEFAULT_ROS_DISTRO="humble"
elif [[ "$UBUNTU_VERSION" == "24.04" ]]; then
    DEFAULT_ROS_DISTRO="jazzy"
fi
```

Isaac Sim auto-selects `ROS_DISTRO=humble` on Ubuntu 22.04, and ships bundled
internal bridge libraries for both (`exts/isaacsim.ros2.core/{humble,jazzy}/lib`
under the Isaac Sim install root). Humble is Isaac Sim's own intended pairing
for this exact host OS, not a fallback compromise — **Phase 2 is retargeted to
ROS2 Humble** (`ros-humble-navigation2`, `ros-humble-nav2-bringup`). Every
`ros-jazzy-*` reference in this spec and in the Phase 2 plan
(`docs/superpowers/plans/2026-06-21-m4-phase2-nav2-stack.md`) is corrected
accordingly. Phase 1's verified OmniGraph node interface
(`phase1-drive-chain.md` §2a) is unaffected: those are Isaac's own bridge node
wrappers (type names, `inputs:`/`outputs:` attribute keys), stable across the
`ROS_DISTRO` selection — only the underlying message-library linkage differs.

### Task 1 re-run on Humble — PASS

```bash
sudo apt-get install -y ros-humble-ros-base ros-humble-navigation2 ros-humble-nav2-bringup
```

Installed cleanly (apt resolved and configured the full Nav2 stack: DWB/MPPI
controllers, NavFn planner, BT navigator, behavior server, AMCL, slam_toolbox,
rviz plugins, etc. — no errors).

Installed versions:

```
ros-humble-nav2-bringup/jammy,now 1.1.20-1jammy.20260425.085132 amd64 [installed]
ros-humble-navigation2/jammy,now 1.1.20-1jammy.20260425.084326 amd64 [installed]
ros-humble-ros-base/jammy,now 0.10.0-1jammy.20260423.142225 amd64 [installed]
```

Smoke test:

```bash
source /opt/ros/humble/setup.bash && ros2 launch nav2_bringup bringup_launch.py --show-args
```

Printed the full launch argument list (`namespace`, `use_namespace`, `slam`,
`map`, `use_sim_time`, `params_file` default
`/opt/ros/humble/share/nav2_bringup/params/nav2_params.yaml`, `autostart`,
`use_composition`, `use_respawn`, `log_level`) with no errors. **Gate: PASS.**

---

## 10. Verified RTX lidar / ArUco exclusion (Isaac Sim 6.0)

**Status: GO.** The ArUco marker plate does not appear as a phantom obstacle
in `/<robot_id>/scan`. No exclusion API was needed — the existing height
separation between the lidar's scan plane and the marker plate (already
authored for the camera-occlusion concern, see `marker_asset.py`) turns out to
also fully solve the RTX-visibility concern, because a 2D RTX lidar only
raytraces within its single horizontal elevation plane.

### Authoring helper

`isaac/vgu_sim/lidar.py::author_rtx_lidar(stage, robot_prim_path, lidar_link)`
creates an `Xform` at `<lidar_link prim>/rtx_lidar` (e.g.
`/World/Robots/robot_1/Geometry/base_footprint/base_link/base_scan/rtx_lidar`),
raising `ValueError` if `lidar_link` is not found under `robot_prim_path`.
Offline-testable (no Isaac Sim/RTX renderer needed) — see
`tests/unit/test_lidar.py`.

### RTX lidar sensor creation (verified on host)

Modern Isaac Sim 6.0 API, **not** the deprecated `omni.kit.commands.execute("IsaacSensorCreateRtxLidar", ...)` path shown as a placeholder in the Phase 2
plan brief (that command still exists in `isaacsim.sensors.rtx`'s deprecated
extension but the experimental API is the one the official standalone example
(`source/standalone_examples/api/isaacsim.ros2.bridge/rtx_lidar.py`) uses):

```python
from isaacsim.sensors.experimental.rtx import Lidar, LidarSensor

lidar = Lidar.create(
    path=f"{lidar_xform_path}/rtx_sensor",
    config="RPLIDAR_S2E",   # SLAMTEC RPLIDAR S2E: 2D rotary, nearRangeM=0.05,
                             # farRangeM=30.0, single elevation ray at 0 deg —
                             # NOT the deceptively-named "Example_Rotary_2D"
                             # config, whose nearRangeM=1.0m is well above the
                             # marker plate's mount radius and would clip any
                             # phantom return regardless of the exclusion
                             # hypothesis under test, making it useless as a
                             # go/no-go probe. FR6.4.9 wants range 0.12-3.5m;
                             # RPLIDAR_S2E's 0.05-30m covers it (a tighter
                             # custom config can be authored later if the
                             # 30m far range needs trimming for performance).
    tick_rate=10.0,
)
sensor = LidarSensor(lidar, annotators=[])
sensor.attach_writer(
    "RtxLidarROS2PublishLaserScan",
    topicName=f"{robot_id}/scan",
    frameId=f"{robot_id}/base_scan",
    horizontalFov=360.0, horizontalResolution=..., depthRange=[...],
    rotationRate=10.0, azimuthRange=[-180.0, 180.0],
    # (read from the lidar prim's omni:sensor:Core:* attributes, see
    # _read_laser_scan_metadata() in the cited standalone example)
)
```

### ArUco-plate exclusion mechanism: height separation (no special API)

Investigated, in the brief's order:

1. **`UsdGeom.Imageable(plate_prim).MakeInvisible()`** — not tried in the final
   run (confirmed by code inspection to also exclude the plate from RGB
   cameras, breaking M1, exactly as the brief predicted); superseded by
   finding option 3 already works.
2. **RTX-specific per-sensor visibility/exclusion API** — searched the
   installed `isaacsim.sensors.rtx` / `isaacsim.sensors.experimental.rtx`
   extension source on the host (`IsaacSim-source/source/.../impl/commands.py`,
   `nonvisual_materials.py`). No per-prim "exclude from this lidar only" flag
   exists. `nonvisual_materials.py`'s `apply_nonvisual_material()` /
   `get_material_id()` only tag material **reflectance** properties (base
   material / coating / attribute, e.g. `"aluminum"`, `"glass"`) for intensity
   simulation — they do not exclude a prim from raytracing.
3. **Height separation (FR6.4.10's own fallback)** — already in place,
   unintentionally solving this: `marker_asset.py` mounts
   `aruco_marker_link` at `z=0.21` (URDF `aruco_marker_joint` origin) "above
   the lidar (base_scan at z=0.172) so a nadir camera is not occluded." The
   marker quad is a flat horizontal sheet (`z=0` in its own local frame, all 4
   corners), so its entire physical extent sits at world `z=0.21`, 3.8 cm
   above the lidar's single-elevation scan plane at `z=0.172`. RTX lidar
   configs used here (`RPLIDAR_S2E`, and the deprecated configs surveyed:
   `Debug_Rotary`, `Example_Rotary_2D`) all fire one ray per azimuth at
   `elevationDeg: [0]` — a strictly planar 2D scan — so a ray traveling in the
   `z=0.172` plane geometrically cannot intersect a flat plate lying entirely
   at `z=0.21`. No code change or exclusion attribute was needed.

### Verification

Ran the `head_on_deadlock` scenario (robot_1 at `x=-0.6`, robot_2 at `x=+0.6`,
facing each other 1.2 m apart) headless on the GCP host, with `author_rtx_lidar()` + the real `RPLIDAR_S2E` RTX lidar sensor wired to
`/robot_1/scan` via `RtxLidarROS2PublishLaserScan`, robot held still. Captured
3 `LaserScan` messages in-process via an `rclpy` subscription (not
`ros2 topic echo` in a separate shell, to avoid timing races):

- `num_ranges=3200`, `range_min=0.05`, `range_max=30.0`,
  `angle_increment=0.1125°` (full 360° sweep).
- Global minimum range: **0.595 m**, in two symmetric angular clusters
  centered at exactly **+90°** (idx 2373-2874, range 87.0-143.3°) and **-90°**
  (idx 327-827, range -143.2 to -87.0°), varying smoothly from ~0.6 m at ±90°
  out to ~1.0 m at ±144°. This is the cross-aisle wall/rack boundary at
  `y≈±0.6 m` (`nominal_aisle_width_m=1.2` in `isaac/vgu_sim/config.py`,
  `WarehouseConfig`), not robot_2 — forward (0°) and the ±9° to ±81° band show
  a clean decreasing sweep out to the far wall (6.6 m at 0°), with **no** close
  return anywhere near 0° where robot_2 (spawned 1.2 m away in `+x`) would be
  expected if the lidar's azimuth-0 aligns with robot-forward. The symmetric,
  smoothly-varying V-profile on each side is the signature of a flat wall
  surface, not a rigid robot body or a single-ray spike — so this scan is read
  as "two real aisle walls, no robot_2 return," not "robot_2, no walls." Why
  robot_2 itself produced no near-range return was not root-caused (candidates:
  lidar azimuth-0 not aligned with robot-forward — `marker_asset.py` documents
  a separate -90° heading correction for the ArUco quad's own UV convention,
  suggesting frame/azimuth conventions in this stack are easy to get
  off-by-90° — or robot_2's RTX-visible geometry not intersecting the scan
  plane at this exact pose); this is **out of scope for the go/no-go gate**,
  which only requires the marker plate to be absent, and does not block this
  task's verdict, but is worth investigating before relying on `/scan` for
  inter-robot collision avoidance in later Nav2 tasks.
- **Zero** range returns under 0.3 m anywhere in the full 3200-ray scan — in
  particular, none in the `[0.05, 0.15] m` band where a phantom hit on the
  marker plate (mount radius ≈0.032-0.21 m from the lidar center) would have
  to appear if the plate were visible to RTX.
- The lidar is demonstrably sensing real scene geometry, not just returning
  no-hits: smooth, physically-plausible wall ranges from 0.595 m (±90°) up to
  6.6 m (0°, far wall down the aisle), with `-1.0` (no-hit) only at a handful
  of indices (corner gaps / grazing angles).

**Conclusion: no phantom obstacle at the ArUco plate's bearing. Gate: GO** —
downstream costmap/Nav2 tasks in this phase may proceed on `/<robot_id>/scan`
as authored, using the existing marker height (`MARKER_HEIGHT_M = 0.21`,
`marker_asset.py`) relative to the lidar mount (`base_scan` at `z=0.172`,
`turtlebot3_burger.urdf` `scan_joint`). Any future change to either height
must re-run this check — the margin is only 3.8 cm.
