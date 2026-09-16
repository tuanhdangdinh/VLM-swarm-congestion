# AMCL Localization — Replacing the Ground-Truth Shortcut

**Prepared:** 2026-09-16

**Revision history:**

- Initial draft: two-step plan (AMCL wiring, then odometry noise) to replace
  the ground-truth `map -> odom` shortcut without regressing the verified
  Nav2 closed loop.

---

## Purpose

Nav2 currently localizes every robot via a static `map -> <robot_id>/odom`
transform equal to its spawn pose
(`ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py`), and Isaac's
`IsaacComputeOdometry` feeds `/robot_N/odom` from the chassis's true world
pose, not integrated wheel ticks, so it is noise-free. Appendix A.7
("Ground truth, sensor-derived, and scripted apparatus components", rev
8.1) of
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
discloses this as simulator-ground-truth, not sensor-derived. This plan
replaces it with real per-robot AMCL (Step 1) and, separately and later,
odometry noise (Step 2), without regressing the verified closed loop
(`backup`/`sidestep`/`drive_heading`, safety monitor, Task-8-style
acceptance). Confirmed live 2026-09-16: container `vgu_ros` already has
`nav2_amcl` and `nav2_map_server` installed — Step 1 needs no new install.

---

## Goal and Non-Goals

**Goal:** Localization becomes sensor-derived (AMCL against `/robot_N/scan`
and the static map), then odometry becomes noisy, each behind its own
opt-in flag so the default (`static`, noise-free) path — the one all prior
verification used — is unchanged unless requested.

**Non-goals:**

- Changing the experiment's two-arm decision-source comparison (Appendix
  A.7). Localization moves from "simulator ground truth" toward
  "sensor-derived"; M2/M3/M5's sensor-derived decisions are untouched.
- Editing `nav2_navigation.launch.py`'s pinned `lifecycle_nodes` — its
  header comment warns against this without host re-verification, and
  neither step needs it.
- Multi-robot map-merging or cross-robot localization fusion — each
  robot's AMCL instance stays independent, per the existing namespacing.

---

## Step 1 — AMCL localization, odometry unchanged

`nav2_robot.launch.py`:

- Add `DeclareLaunchArgument("localization", default_value="static")`.
- Gate the existing `map_to_odom_ground_truth` static TF node (lines
  ~210–231) on `localization == 'static'`.
- Inside the existing `GroupAction([PushRosNamespace(robot_id), ...])`
  (lines ~264–316), add an `amcl` `Node` plus a separate
  `lifecycle_manager_localization` (`node_names: ['amcl']`), both gated on
  `localization == 'amcl'`.
- Do **not** include `nav2_bringup`'s `localization_launch.py`: on Jazzy it
  hardcodes its own `map_server` with no disable flag and would collide
  with the shared, non-namespaced `map_server` already launched here
  (lines ~244–263).
- Do not edit `nav2_navigation.launch.py`'s pinned `lifecycle_nodes`.

`nav2_params.yaml` — add an `amcl:` block:

- `global_frame_id: map`, `odom_frame_id: "<robot_namespace>/odom"`,
  `base_frame_id: "<robot_namespace>/base_footprint"`,
  `scan_topic: "/<robot_namespace>/scan"`, `map_topic: /map` — absolute
  literals, not `SetRemap`, the same failure class already documented here
  for `global_costmap.map_topic` and `collision_monitor.scan.topic`
  (`Costmap2DROS`/AMCL build these subscriptions from the parameter value
  directly, bypassing the relative-name-plus-remap path `/tf` uses).
- `set_initial_pose: true`, `initial_pose.{x, y, yaw}` from the same spawn
  launch args already used by `map_to_odom_ground_truth`.
- `tf_broadcast: true`; `laser_max_range: 3.5`, `laser_min_range: 0.12`
  (matches `isaac/config/lidar/turtlebot3_lds_01.json`).
- Tighten `update_min_d`/`update_min_a` from Jazzy defaults (0.25 m / 0.2
  rad) to ~0.05–0.10 — otherwise a 0.8 m backup (the verified maneuver) can
  complete with zero filter updates.

**Acceptance:**

| Check | Expected |
|---|---|
| `localization:=static` (default) | Unchanged from today: static TF, no `amcl` node; `tests/unit/test_nav2_adapter.py` and a Task-8-style run pass unchanged. |
| `localization:=amcl` | `amcl` + `lifecycle_manager_localization` up namespaced under `robot_id`, no collision with the shared `map_server`. |
| AMCL convergence | Within 0.05 m / 3° of ground truth within 5 s (see Verification). |

---

## Step 2 — Odometry noise (after Step 1 lands)

**Design:** a `swarm_simulation` node subscribes `/robot_N/odom`, integrates
a Gaussian-noisy twist into a drifting pose, and publishes
`/robot_N/odom_noisy` plus `odom -> base_footprint` TF. Gate off the
existing `pub_tf` wiring in `isaac/vgu_sim/ros_graphs.py` (node at line
284, connections ~314–317, inputs ~345–348) so Isaac stops publishing it
when noise is enabled. Isaac-side noise is a non-starter:
`IsaacComputeOdometry` reads the chassis prim's pose directly via
`chassisPrim` (node at line 282, input at line 340), never wheel ticks, so
physics-side slip cannot reach `/odom` — noise must be injected downstream.
No citable TurtleBot3 σ exists (Gazebo's diff-drive `gaussianNoise`
defaults to `0.0`); start from AMCL's own `alpha1–4: 0.2`, coupled pair
σ_v ≈ 0.02·|v| plus a small floor, tuned during verification.

**Dependency on an M4 change:** `nav2_adapter.py`'s `backup`, `sidestep`,
`drive_heading` each close their loop on raw `/robot_N/odom` (subscriptions
at lines 218, 345, 464). AMCL alone leaves these unaffected, but Step 2's
noise breaks them and corrupts `local_costmap.global_frame` if left on the
noisy frame — hence Step 1 before Step 2, not concurrently; Step 2 needs
its own adapter-side fix (Risk #1, Effort below).

**Acceptance:**

| Check | Expected |
|---|---|
| Noise disabled (default) | `/robot_N/odom` unchanged; no `/robot_N/odom_noisy`. |
| Noise enabled | `/robot_N/odom_noisy` drift scales with σ; adapter's closed-loop methods re-pointed at the correct frame and still converge. |

---

## Risks (ranked)

1. **Sequencing.** AMCL alone doesn't touch `/odom`, so `backup`/`sidestep`/
   `drive_heading` are unaffected by Step 1 alone but broken by Step 2's
   noise, which also corrupts `local_costmap.global_frame`. Do not land
   both in one change.
2. **Symmetric-corridor degeneracy.** The 1.2 m aisle's mirror-image lidar
   geometry risks a laterally flipped particle mode. Jazzy `nav2_amcl` has
   no `initial_cov_*` parameter (confirmed in `amcl_node.cpp`) — use
   `/initialpose` (`PoseWithCovarianceStamped`) if precise initial
   covariance matters.
3. **Tight goal tolerance.** `xy_goal_tolerance: 0.1` leaves little margin
   for added AMCL pose error.
4. **M1/map-frame alignment.** Whether M1's world frame matches
   `warehouse_map.yaml`'s origin (−6, −4) is unverified — a prerequisite
   check (see Open Questions).
5. **Safety monitor untouched.** `safety_monitor_node.py` reads only
   `/perception/scene_state` (its only subscription, confirmed at lines
   87–89), so the safety net is unaffected by either step.

---

## Verification Procedure

- Compare AMCL pose vs. M1's `scene_state` vs. Isaac's chassis pose at
  startup: pass at ≤ 0.05 m / 3° within ≤ 5 s.
- Repeat through a full `backup`/`sidestep` maneuver, not just at rest.
- With noise enabled, measure `/robot_N/odom_noisy` drift rate vs. σ.
- Rerun `tests/unit/test_nav2_adapter.py` after each step.
- Rerun a Task-8-style acceptance run under `localization:=static`
  (default) to confirm zero regression when the new flags are unused.

---

## Effort and Sequencing

Total ≈ 20–25 h; about half needs the GPU VM (Isaac Sim host).

| Piece | Desk | VM |
|---|---|---|
| Step 1: AMCL launch/param wiring | 4–6 h | 3–4 h |
| Step 2: odometry noise node | 4 h (offline-testable) | 2 h |
| `nav2_adapter.py` map-frame end-condition fix (Step 2 dependency) | 3–4 h | 2 h |

Step 1 must be fully verified, including the static-default regression
check, before Step 2 starts. The adapter fix is an M4 change outside this
plan's file list — flag it to whoever picks up Step 2.

---

## Open Questions

- **M1/map alignment check.** Whether M1's perception world frame matches
  `warehouse_map.yaml`'s origin (−6, −4) is unverified. Confirm before
  starting Step 1's AMCL convergence check.
- **Should the experiment run under AMCL at all before preregistration is
  frozen?** A research-design decision, not engineering — left open here.

---

## Sources

- [Nav2 (Jazzy) — AMCL configuration](https://docs.nav2.org/configuration/packages/configuring-amcl.html)
- [`ros-navigation/navigation2`, Jazzy branch](https://github.com/ros-navigation/navigation2/tree/jazzy) — `nav2_bringup/launch/localization_launch.py`, `nav2_amcl/src/amcl_node.cpp`
