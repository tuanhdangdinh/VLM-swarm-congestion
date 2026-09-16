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
namespaced-bringup mechanism against the Nav2 Jazzy docs/container install before
building (see §9 — this phase targets the `ros:jazzy` container, while Isaac
Sim uses its bundled Jazzy bridge on the host);
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

### Verified (2026-06-22, Task 5 finish): `nav2_robot.launch.py` authored and TF chain confirmed

`ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py` publishes
`map -> <robot_id>/odom` via `tf2_ros static_transform_publisher`, using the
documented current flag syntax (`--x/--y/--z/--roll/--pitch/--yaw
--frame-id --child-frame-id`, not the deprecated 8-positional-arg form). The
transform value is **not** hardcoded identity or a scenario-specific lookup
table: the launch file declares `x`/`y`/`yaw` launch arguments **with no
default value** that the caller must supply with the robot's actual spawn
pose from the scenario config — a caller who forgets them gets a loud
missing-argument error at launch time instead of silently reintroducing the
identity-transform bug this task corrected — keeping the launch file reusable
across scenarios per CLAUDE.md's module-boundary guidance.

**Verification on host**, `head_on_deadlock`'s `robot_1` (`spawn: x=-0.6,
y=0.0, yaw_rad=0.0`):

- Launched `ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1
  x:=-0.6 y:=0.0 yaw:=0.0` as a genuine separate `ros2 launch` process (not
  in-process), confirmed via its own log: `translation: ('-0.600000',
  '0.000000', '0.000000')` ... `from 'map' to 'robot_1/odom'`.
- Brought up `head_on_deadlock` headless via the production scene-build
  sequence (`runner.py`'s own helpers, in `run_repetition()`'s order;
  `runner.py` itself untouched — the relative-path `.resolve()` workaround
  from Task 4/5 was applied only in the ephemeral verification script, not in
  `runner.py`/`paths.py`).
- Cross-process TF visibility required exporting a FastDDS UDP-only (no SHM)
  profile via `FASTRTPS_DEFAULT_PROFILES_FILE` on **both** the
  `static_transform_publisher` process and the Isaac-side process — confirmed
  this resolves the SHM-transport mismatch documented in Task 5's report
  (Isaac's bundled FastDDS build vs. the container ROS build): without
  the profile, an in-process `tf2_ros.Buffer` inside Isaac never saw the `map`
  frame at all (`"map" passed to lookupTransform argument target_frame does
  not exist`); with it, the buffer resolved `map -> robot_1/odom` and the full
  chain immediately.
- Resolved `map -> robot_1/base_link` in-process (Isaac-bundled rclpy +
  `tf2_ros.Buffer`/`TransformListener`) after ~3 s of advancing sim time:
  **`translation=(-0.6000, -0.0000, 0.0100)`**, matching the robot's true
  spawn pose (`x=-0.6`) to 4 decimal places (`z=0.01` is the chassis's
  mount-height offset, expected and unrelated to the `map->odom` hop). Hop
  breakdown: `map->robot_1/odom = (-0.6, 0, 0)` (the static publisher under
  test), `robot_1/odom->robot_1/base_footprint ≈ (0, 0, 0)` (spawn-relative
  odom, confirming Task 5's finding), `robot_1/base_footprint->robot_1/base_link
  = (0, 0, 0.01)` (static mount offset). The static spawn-pose transform
  composes correctly with the dynamic, correctly-stamped (Task 5b)
  `odom->base_footprint` edge.

### Resolved: `/odom` and `/tf_static` stamped 0 (Task 5b)

Task 5 found `/robot_1/odom` published with `header.stamp = 0` continuously
throughout multi-hundred-second runs (not a startup transient), via repeated
`[Warning] Frame robot_1/odom Timestamp is invalid` log lines, while
`sim_time` itself correctly advances. Task 5b root-caused and fixed this:
`ROS2PublishOdometry.inputs:timeStamp` had no `CONNECT` edge at all in
`create_robot_ros_graph` (`isaac/vgu_sim/ros_graphs.py`), so it used the
node's `.ogn`-schema default of `0.0` — confirmed against
`OgnROS2PublishOdometry.cpp` (reads `db.inputs.timeStamp()` as given) and the
node's `.ogn` schema (`"timeStamp": {"default": 0.0}`). The two
`ROS2PublishRawTransformTree` nodes publishing the static `base_footprint →
base_link` and `base_link → base_scan` mounts on `/tf_static`
(`pub_tf_base`/`pub_tf_scan`) had the identical bug — also unwired, also
defaulting to `0.0` — which is what actually produced the
`robot_1/base_link`/`robot_1/base_footprint` "Timestamp is invalid" warnings
Task 5 saw (transient-local QoS on `/tf_static` does not exempt a publisher
from being stamped correctly).

**The dynamic `odom → base_footprint` edge on `/tf` (`pub_tf`) was already
wired correctly and was never actually broken** — Task 5's report conflated
the `/tf_static` warning lines with this edge. Verified in-process on the
host: subscribing directly to `/tf` and filtering for
`child_frame_id == "<robot_id>/base_footprint"` showed `header.stamp`
advancing with sim time (e.g. `0.066...` → `15.866...` over an 8 s capture)
both before and after the fix below.

**Fix:** `pub_odom.inputs:timeStamp`, `pub_tf_base.inputs:timeStamp`, and
`pub_tf_scan.inputs:timeStamp` are now all wired to
`read_time.outputs:simulationTime`, the same source already feeding
`pub_tf.inputs:timeStamp`. Verified in-process post-fix: `/robot_1/odom` and
`/tf_static` both now advance with sim time, and the "Timestamp is invalid"
warning no longer appears anywhere in an 8 s run (0 occurrences, vs. dozens
before the fix). See `.superpowers/sdd/task-5b-stamp-fix-report.md` for full
evidence.

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

### Superseded resolution: host Humble retarget

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

Isaac Sim auto-selects `ROS_DISTRO=humble` on Ubuntu 22.04 when `ROS_DISTRO` is
unset, and ships bundled
internal bridge libraries for both (`exts/isaacsim.ros2.core/{humble,jazzy}/lib`
under the Isaac Sim install root). An earlier pass interpreted that as a reason
to retarget Phase 2 to host Humble. That direction is now **superseded**: the
confirmed project runtime is Isaac Sim on the host with `ROS_DISTRO=jazzy` using
its bundled Jazzy bridge, plus M1/M4/M5/Nav2 inside the `ros:jazzy` Docker
container. Host apt availability for Humble remains useful diagnostic evidence,
but host Humble is not the Phase 2 target. Phase 1's verified OmniGraph node interface
(`phase1-drive-chain.md` §2a) is unaffected: those are Isaac's own bridge node
wrappers (type names, `inputs:`/`outputs:` attribute keys), stable across the
`ROS_DISTRO` selection — only the underlying message-library linkage differs.

### Task 1 re-run in Jazzy container — PASS

Use the existing `vgu_ros`/`ros:jazzy` container, not host apt, for Nav2:

```bash
sudo docker start vgu_ros
sudo docker exec vgu_ros bash -lc \
  'source /opt/ros/jazzy/setup.bash && ros2 launch nav2_bringup bringup_launch.py --show-args'
```

The container must contain `ros-jazzy-navigation2` and
`ros-jazzy-nav2-bringup` (the devcontainer installs the same packages). Isaac
side runs should set `ROS_DISTRO=jazzy` before sourcing
`/home/ubuntu/IsaacSim/setup_ros_env.sh` so Isaac's bundled bridge matches the
container participants.

Verified on the GCP host (`isaacautomator-vgu-gcp2-isaac-workstation-vm`,
2026-06-22): `vgu_ros` is running from image `ros:jazzy`, `ROS_DISTRO=jazzy`,
and these packages are installed:

```text
ros-jazzy-nav2-bringup 1.3.12-1noble.20260616.082701
ros-jazzy-navigation2  1.3.12-1noble.20260615.181551
ros-jazzy-ros-base     0.11.0-1noble.20260412.071950
```

Smoke test passed:

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch nav2_bringup bringup_launch.py --show-args
```

The command printed the Jazzy launch argument list (`namespace`,
`use_namespace`, `slam`, `map`, `use_sim_time`, `params_file`, `autostart`,
`use_composition`, `use_respawn`, `log_level`, `use_localization`,
`use_lifecycle_manager`, `slam_params_file`, `container_name`) with no errors.

### Historical host-Humble smoke test — PASS, not current target

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

---

## 11. Verified per-robot Nav2 bringup (Jazzy container smoke)

Verified on 2026-06-22 in the `vgu_ros` (`ros:jazzy`) container after copying the
current Phase 2 launch/config changes into `/ws`:

```bash
source /opt/ros/jazzy/setup.bash
cd /ws/ros2_ws
colcon build --merge-install --packages-select swarm_simulation
source install/setup.bash
ros2 launch swarm_simulation nav2_robot.launch.py --show-args
```

Result: `swarm_simulation` built successfully and `nav2_robot.launch.py`
resolved its own required arguments (`robot_id`, `x`, `y`, `yaw`) plus the
included Jazzy `navigation_launch.py` arguments with no import or package
errors.

A short launch smoke test without Isaac Sim running:

```bash
ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1 x:=-0.6 y:=0.0 yaw:=0.0
```

exposed the expected namespaced action servers, including
`/robot_1/navigate_to_pose` and `/robot_1/follow_waypoints`, and loaded the
Jazzy Nav2 plugins configured in `nav2_params.yaml`:

- `nav2_navfn_planner::NavfnPlanner`
- `dwb_core::DWBLocalPlanner`
- DWB critics listed under `FollowPath`
- Jazzy lifecycle-managed auxiliary nodes (`smoother_server`, `route_server`,
  `velocity_smoother`, `collision_monitor`, `docking_server`)

The smoke run then waited for `robot_1/base_link -> robot_1/odom`, which is
expected because Isaac Sim was not running and therefore no robot TF was being
published. This smoke verifies the Jazzy Nav2 stack/launch/config path, not
closed-loop navigation. The next host verification must run Isaac Sim with
`ROS_DISTRO=jazzy` and the DDS UDP profile so `/clock`, `/tf`, `/robot_1/odom`,
and `/robot_1/scan` are present while Nav2 activates.

---

## 12. `localization:=amcl` (Option B)

### 2026-09-16: `localization:=amcl` (Option B) available, unverified

`nav2_robot.launch.py` now takes a `localization` argument (`static` | `amcl`),
**default `static`** — so the verified closed loop of S5/S11 and Task 8 is
unchanged unless the flag is passed explicitly. Nothing about the default path
was modified.

Added:

- `DeclareLaunchArgument("localization", default_value="static", ...)`.
- The `map_to_odom_ground_truth` static transform publisher is now gated on
  `localization == 'static'`; under `amcl` it is suppressed, since `nav2_amcl`
  owns the same `map -> <robot_id>/odom` edge and two publishers of one edge
  would fight.
- Inside the existing namespaced `GroupAction` (after
  `PushRosNamespace` + the two absolute-keyed `SetRemap` rules), gated on
  `localization == 'amcl'`: a `nav2_amcl` node named `amcl`, plus a
  `nav2_lifecycle_manager` named `lifecycle_manager_localization` managing only
  `["amcl"]`. The AMCL node deliberately carries **no** node-level `/tf`
  remappings — the group-level absolute-keyed rules are what keep TF on shared
  `/tf`/`/tf_static` (S5/docstring), and a node-level rule would reintroduce
  the candidate that lost.
- The AMCL node's params file is wrapped exactly as the vendored
  `nav2_navigation.launch.py` wraps its own —
  `ParameterFile(RewrittenYaml(source_file=<ReplaceString'd nav2_params.yaml>,
  root_key=robot_id, param_rewrites={}, convert_types=True), allow_substs=True)`
  — because this node is declared by our launch file rather than by the
  vendored one, so nothing else roots the YAML under the namespace for it.
  Initial pose comes from the existing `x`/`y`/`yaw` arguments via
  `ParameterValue(..., value_type=float)` with `set_initial_pose: true`, i.e.
  the same spawn pose the static transform used.
- `nav2_params.yaml`: a new top-level `amcl:` block, Jazzy `nav2_bringup`
  defaults except `global_frame_id: map`,
  `odom_frame_id: "<robot_namespace>/odom"`,
  `base_frame_id: "<robot_namespace>/base_footprint"`,
  `scan_topic: "/<robot_namespace>/scan"`, `map_topic: /map`,
  `laser_min_range: 0.12` / `laser_max_range: 3.5` (matching
  `isaac/config/lidar/turtlebot3_lds_01.json`), `update_min_d: 0.05` /
  `update_min_a: 0.1`, and `use_sim_time: true`.
- `package.xml`: `<exec_depend>nav2_amcl</exec_depend>`.
- `tests/unit/test_nav2_params_config.py`: offline YAML/AST checks (namespace
  tokens in the odom/base frames, unprefixed `map` global frame, absolute
  `scan_topic`/`map_topic` literals, laser ranges equal to the lidar JSON's
  `minRange`/`maxRange`, and `localization`'s `default_value == "static"`).

`nav2_bringup`'s `localization_launch.py` is still not used, but the reason has
changed: it is no longer "this design bypasses AMCL" (S5 Option A) — it is that
`localization_launch.py` hardcodes its own `map_server` +
`lifecycle_manager`, which would collide by name with the shared,
non-namespaced pair this launch file already starts (S11). The shared
`map_server` stays correct under `amcl` because `amcl:`'s `map_topic` is the
absolute literal `/map`.

M4 impact: none expected. AMCL publishes only TF and `~/amcl_pose`; it never
writes `/<robot_id>/odom`, so the odometry-closed primitives (backup, hold —
`project_m4_backup_closed_loop_verified`) are unaffected by the flag.

### Verification still to run on the host

Authored and statically checked offline only (macOS, no ROS 2 installed): the
launch file parses under `ast.parse`, `ruff check` is clean, and the four YAML/
AST unit tests pass. **The launch file has not been executed.** Required on the
`vgu_ros` Jazzy container with Isaac Sim running:

1. `colcon build --merge-install --packages-select swarm_simulation`, then
   `ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1
   x:=-0.6 y:=0.0 yaw:=0.0 localization:=amcl`.
2. `ros2 topic echo /robot_1/amcl_pose` produces poses (AMCL reached `active`).
3. TF `map -> robot_1/odom` is now **dynamic** (`ros2 run tf2_ros tf2_echo map
   robot_1/odom` changes over time), and there is exactly one publisher of it —
   confirm the static node is absent.
4. `ros2 node info /robot_1/amcl` shows `Publishers: /tf` (**not**
   `/robot_1/tf`) — this is what proves the group-level `SetRemap` covers the
   broadcaster, not just the listeners.
5. `global_costmap` and `bt_navigator` reach lifecycle `active` with no
   "Timed out waiting for transform" for `map -> robot_1/base_link`. Under
   `amcl` there is no `map -> odom` at all until AMCL's first broadcast, so
   this is the discriminating check, more than `amcl_pose` alone. Prerequisite:
   the `base_footprint -> base_scan` edge must be present on `/tf_static`
   (URDF `scan_joint`) for AMCL's laser lookup.
6. Convergence: compare `/robot_1/amcl_pose` against M1's overhead-camera pose
   for the same robot over a drive leg, and re-run the Task 8 goal-reaching
   acceptance under `localization:=amcl` before treating Option B as verified.
7. Re-run the M4 backup/hold primitives under `amcl` to confirm the
   "no `/odom` change" claim empirically rather than by inspection.
8. Two-robot run (`head_on_deadlock.yaml`, the actual acceptance scenario —
   every step above is single-robot). Confirms the two assumptions this design
   leans on but has not tested: robot 2's AMCL joining late still receives the
   latched `/map` from robot 1's `map_server` (robot 2 launches with
   `start_map_server:=false`), and two AMCLs broadcasting to the shared `/tf`
   coexist with distinct child frames (`map -> robot_1/odom` and
   `map -> robot_2/odom`). Structurally there should be no node-name collision
   — both `amcl` and both `lifecycle_manager_localization` instances are
   namespaced — but that is inference, not evidence.

**First failure mode to check.** `lifecycle_manager_localization` manages
`["amcl"]` only, and nothing sequences AMCL's activation after the shared
`map_server`'s: `lifecycle_manager_map_server` autostarts independently. If
`/robot_1/amcl_pose` is silent, grep the AMCL log for "Waiting for map" before
suspecting TF or parameters. This should self-resolve — `map_server` latches
`/map` with `TRANSIENT_LOCAL` durability (verified in S11: 1 publisher,
`TRANSIENT_LOCAL`), so AMCL's subscription receives it whenever it is created,
regardless of activation order. Do **not** "fix" it by adding `map_server` to
this manager's `node_names`: the manager is namespaced with AMCL, so
`"map_server"` would resolve to the nonexistent `/robot_1/map_server` and block
the whole localization bringup.

### Parameter-name sources verified (CLAUDE.md "External Library Verification")

- Nav2 Jazzy AMCL configuration guide:
  <https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/others/configuring_amcl/>
  (confirms the exact spellings `global_frame_id`, `odom_frame_id`,
  `base_frame_id`, `scan_topic`, `map_topic`, `tf_broadcast`,
  `laser_min_range`, `laser_max_range`, `update_min_d`, `update_min_a`,
  `robot_model_type`, `set_initial_pose`, `always_reset_initial_pose`,
  `first_map_only`, and `initial_pose` as a `Pose2D` with `x`/`y`/`z`/`yaw`).
  Note: `https://docs.nav2.org/configuration/packages/configuring-amcl.html`
  (the unversioned path) returns 404 as of this date; use the versioned path.
- `nav2_bringup/params/nav2_params.yaml`, `jazzy` branch:
  <https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_bringup/params/nav2_params.yaml>
  (source of the default values copied into the `amcl:` block).

One discrepancy between the two sources: `nav2_bringup`'s `jazzy` block gives
`z_short: 0.05` while the docs table gives `0.005`. The `nav2_bringup` value
(`0.05`) was taken, since that file is the shipped configuration; worth
re-checking against `ros2 param get /robot_1/amcl z_short` on the host.
`bond_heartbeat_period` appears in the docs table but not in `nav2_bringup`'s
block, so it was left unset. `laser_model_type: "likelihood_field"` means the
`z_short`/`lambda_short` beam-model terms are not used in scoring anyway.

---

## 13. `localization:=camera` (Option C — overhead camera)

### 2026-09-16: `localization:=camera` available, unverified

`nav2_robot.launch.py`'s `localization` argument accepts a third value,
`camera`, alongside `static` | `amcl`. **Default remains `static`**, so the
verified closed loop of S5/S11 and Task 8 is untouched unless the flag is
passed.

**Why.** S12's Option B localizes to ~2 cm while both robots sit near the
corridor, then degenerates during the yield manoeuvre: this warehouse is
symmetric, the aisle barrier makes every scan pose-ambiguous along the
corridor axis, and the manoeuvre is exactly where pose error matters. The
apparatus already carries a *global* sensor that has none of those failure
modes — M1's overhead camera measures each robot's absolute pose from its ArUco
marker, and M1's world frame is the Nav2 `map` frame (verified). Option C turns
that measurement into the one TF edge Nav2 actually consumes.

**Math (planar SE(2)).** The camera gives `T_map_base`; TF's
`<robot>/odom -> <robot>/base_footprint` (published by Isaac, spawn-relative
and drift-free) gives `T_odom_base`. The published correction is

```text
T_map_odom = T_map_base . T_odom_base^-1
```

With drift-free odometry this equals the robot's spawn pose — i.e. Option C
converges on what the `static` publisher hardcodes, but measures it rather than
trusting it, and tracks it if the chassis is ever displaced.

**Holding.** When the robot is `STALE` or missing from `robots[]`, the last
correction is held rather than dropped. Odometry is drift-free, so a held
correction stays valid indefinitely — the same behaviour AMCL has between its
own updates, and the reason an occasional dropped camera frame (CLAUDE.md
gotcha 5) cannot starve a costmap that needs `map -> odom` every cycle.

**Timing — the one non-obvious constraint.** `scene_state.stamp` is the camera
image header time, which Isaac fills from **SYSTEM** time, while TF and every
node in this stack run on **SIM** time (`use_sim_time: true`). The two stamps
are not comparable, so the node never looks up TF at the scene stamp; it looks
up the **latest** `odom -> base_footprint` (`Time()`) and accepts the resulting
latency error, bounded by speed * camera latency (<= 0.2 m/s * ~0.1 s
= <= 2 cm) — below the error AMCL degenerates to in the case this replaces.
Outgoing transforms are stamped `now + transform_tolerance_sec` (AMCL's own
convention, so consumers may extrapolate) and broadcast from a fixed-rate timer
(`publish_rate_hz`, default 20 Hz), independent of camera frame arrival.

Added:

- `ros2_ws/src/swarm_perception/swarm_perception/camera_localizer.py` — pure
  SE(2) maths, no ROS imports: `Pose2D`, `normalize_yaw` (to `(-pi, pi]`),
  `compose`, `invert`, `map_to_odom`, and `class CameraLocalizer` holding one
  robot's correction plus `updates`/`holds` counters and `last_update_stamp`.
  `normalize_yaw` uses `atan2(sin, cos)` rather than the
  `(yaw + pi) % (2*pi) - pi` idiom, which maps an exact `+pi` to `-pi` and
  would flip robot_2's spawn heading on every pass.
- `camera_localizer_node.py` — `CameraLocalizerNode`, one instance per robot.
  Parameters: `robot_id` (required, fails fast), `scene_state_topic`
  (default the **absolute** `/perception/scene_state` — a relative default
  would resolve to `/<robot_id>/perception/scene_state` under the namespace
  push and never receive anything), `map_frame` (`map`), `odom_frame`
  (default `<robot_id>/odom`), `base_frame` (default
  `<robot_id>/base_footprint`), `publish_rate_hz` (20.0),
  `transform_tolerance_sec` (0.3). Subscribes `std_msgs/String` depth 10, keeps
  a `tf2_ros.Buffer` + `TransformListener`, broadcasts via
  `TransformBroadcaster`. TF lookup failures warn at most once per 5 s
  (`throttle_duration_sec=5.0`). ROS imports are guarded so the module is
  importable without `rclpy`, matching `swarm_execution/nav2_adapter.py`.
- `nav2_robot.launch.py` — a `camera_localizer` node inside the existing
  namespaced `GroupAction`, gated on `localization == 'camera'`, with no
  node-level `/tf` remaps (the group-level absolute-keyed `SetRemap` rules are
  what keep its listener *and* broadcaster on shared `/tf`; S12). No lifecycle
  manager: it is a plain rclpy node, not a nav2 lifecycle node. The static
  ground-truth publisher stays gated on `static` only, so it is absent here —
  one writer per TF edge.
- `swarm_perception/package.xml`: `tf2_ros`, `geometry_msgs` exec_depends;
  `setup.py`: `camera_localizer_node` console script.
  `swarm_simulation/package.xml`: `<exec_depend>swarm_perception</exec_depend>`.
- `tests/unit/test_camera_localizer.py` (8 offline tests) and
  `test_nav2_params_config.py::test_camera_localization_mode_is_declared`.

**Operational prerequisite.** M1 must already be publishing
`/perception/scene_state` before Nav2 activates: under `camera` there is no
`map -> odom` at all until the first camera fix, so the costmaps block waiting
for that edge exactly as they do under `amcl`. Launch order is
Isaac -> M1 -> Nav2.

M4 impact: none expected, for the same reason as S12 — this node publishes only
TF and never writes `/<robot_id>/odom`, so the odometry-closed primitives
(backup, hold) are unaffected by the flag.

### Verification still to run on the host

Authored and statically checked offline only (macOS, no ROS 2 installed):
`ruff check` clean on all touched Python, the launch file parses under
`ast.parse`, `camera_localizer_node` imports successfully with `rclpy` absent,
and `tests/unit/test_camera_localizer.py` +
`tests/unit/test_nav2_params_config.py` pass (15 tests). **Neither the node nor
the launch file has been executed.** Required on the `vgu_ros` Jazzy container
with Isaac Sim and M1 running:

1. `colcon build --merge-install --packages-select swarm_perception
   swarm_simulation`, then launch M1, then
   `ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1
   x:=-0.6 y:=0.0 yaw:=0.0 localization:=camera`.
2. The INFO line `camera localization acquired robot=robot_1 map_odom=(...)`
   appears, and its `(x, y, yaw)` matches the robot's spawn pose to a few cm —
   the fastest check that `compose`/`invert` are composed in the right order
   (a reversed composition still publishes a plausible-looking transform).
3. `ros2 run tf2_ros tf2_echo map robot_1/odom` is live and changing slightly,
   with exactly one publisher — confirm the static node is absent.
4. `ros2 node info /robot_1/camera_localizer` shows `Publishers: /tf` and
   `Subscribers: /tf, /tf_static, /perception/scene_state` — **not**
   `/robot_1/tf` or `/robot_1/perception/scene_state`. This is the check that
   the group-level remaps cover a node this launch file declares itself, and
   that the absolute scene-state default survived the namespace push.
5. `global_costmap` and `bt_navigator` reach lifecycle `active` with no
   "Timed out waiting for transform" for `map -> robot_1/base_link`.
6. Accuracy: compare `map -> robot_1/base_footprint` (camera-corrected) against
   M1's reported pose for the same robot over a drive leg; the residual is the
   latency error argued above and should stay at the few-cm scale, including
   *during* the yield manoeuvre — the case where AMCL degenerated (S12 / AMCL
   runs B2 and C).
7. Re-run the Task 8 goal-reaching acceptance and the head-on deadlock scenario
   under `localization:=camera` (two robots, robot 2 with
   `start_map_server:=false`) before treating Option C as verified. Two
   `camera_localizer` instances broadcasting distinct child frames should
   coexist on shared `/tf` — structurally sound (both are namespaced) but
   inference, not evidence.

**First failure mode to check.** If no TF `map -> robot_1/odom` ever appears,
grep the node's log for the throttled
`no TF robot_1/odom->robot_1/base_footprint` warning before suspecting the
camera path: the node holds `None` until *both* a camera fix and that odometry
edge exist. If instead the warning is absent but the acquired line never
prints, the robot is missing from `robots[]` or permanently `STALE` — check
M1's marker visibility first (`project_m1_stale_vs_stopped`: overlapping
markers report `STALE`, not `STOPPED`).
