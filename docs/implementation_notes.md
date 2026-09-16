# Implementation Notes

**Prepared:** 2026-07-11

**Revision history:**

- Initial draft: living log created; seeded with verified notes from M1/M4/M6 work through 2026-07-08 and the congestion-reasoner program state.

---

## Purpose and Maintenance Rules

This is the project's **living implementation log**: dated, append-only notes
recording decisions, verified fixes, gotchas, and open items that do not fit a
one-shot report. It complements — never replaces — the other document types:

- **Specs** (`docs/specs/`, `docs/superpowers/specs/`) define what to build.
- **Plans** (`docs/superpowers/plans/`) define how to build it, task by task.
- **Reports** (`docs/reports/`) are one-shot deep dives on a completed module
  or investigation (structure in `docs/standards/doc_style.md`).
- **This file** captures the connective tissue: "we learned X on date Y,
  evidence at Z" — the facts you need before touching a subsystem.

Rules for maintaining it:

- One bullet per note: `- **YYYY-MM-DD** — fact (pointer to commit, doc, or file).`
- Append under the matching module section, newest entry first. Do not rewrite
  or delete old entries; if a note is superseded, append the new fact and mark
  the old one `superseded by <date> entry`.
- Convert relative dates to absolute before writing.
- Link evidence (commit hash, spec, report, config file) instead of restating
  detail that lives elsewhere.
- Update the header revision history only for structural changes to this
  document, not for routine entries.

---

## Congestion-Resolution Experiment (research program: M2/M3/M5)

- **2026-07-11** — Phase 1 execution deliberately deferred. Prerequisites
  before data collection: commit the rev-8 spec + Phase 1 plan; fill the two
  REQUIRED pre-registration fields (primary `openai` `model_id` — blocked on
  API key — and secondary `llama_server` `model_id`); then tag `prereg-v1`.
- **2026-07-08** — Phase 1 implementation plan written:
  `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`
  (15 TDD tasks, offline reasoning core + Arm B). Not yet executed. Key
  decision: `GroundingParams.mode` = `legacy` (default) / `derived`;
  `config/rag.yaml` stays `legacy` until Phase 2 flips the M5 call site, so
  the live loop is untouched by Phase 1. Planned phase split: 1 reasoning
  core, 2 M5/M1 integration, 3 M4 execution semantics, 4 scenario battery +
  oracle blocks, 5 harness + pre-registration freeze.
- **2026-07-08** — Spec rev 8 applied (external design review):
  `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
  Adds run matrix + statistical plan (paired-seed, N=30 pairs per T1 scenario
  with a one-time extension rule), full Arm B classical-reasoner
  specification with tuning-parity rule, T0 log-only negative probes,
  RQ1–RQ5 renaming (was H1–H5, collided with the "H3" run series),
  model/decoding pre-registration table, and rev-6 mechanism detail restored
  as Appendix A.
- **2026-07-08** — Open reconciliation item for the pre-registration freeze:
  the rev-8 model table pins temperature 0.0 (classification rule), but
  `ReasonerConfig` deliberately defaults to 0.6/0.95/20 because Cosmos
  Reason 2 is a chain-of-thought model that degrades at temperature 0.0
  (comment in `reasoning/vlm/models.py`). Resolution: 0.0 for non-CoT
  backends, model-card preset for CoT models, exact values recorded at
  freeze.

---

## M1 Perception

- **2026-07-03** — Colliding/overlapping ArUco markers make robots go STALE
  (marker lost), not STOPPED, which delays stall detection. Mitigation:
  `stale_after_sec` ≥ 3.0 and `velocity_alpha` ≈ 0.15 in the perception
  config for congestion scenarios.
- **2026-06-17** — Marker placement contract: the ArUco marker prim must live
  under `aruco_marker_link` (a `base_link` child inside the physics
  hierarchy), not under the robot root, or physics parses fail;
  `isaac/vgu_sim/validation.py` checks this and must be updated in sync with
  any marker-asset change (silent crash otherwise). See
  `docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md`.

---

## M2 VLM / M5 Orchestrator Pipeline

- **2026-07-05** — M6→M1→M5→M2 closed loop runs end-to-end on the GCP/Isaac
  host with the mock backend; the only remaining swap for live reasoning is
  `backend_id: openai`, blocked on an API key.
- **2026-06-15** — Offline input-encoding ablation harness spec:
  `docs/superpowers/specs/2026-06-15-m2-input-ablation-design.md`. Rev-8 of
  the congestion spec governs live-loop modality conditions; the 06-15 doc
  remains the spec for the offline benchmark runner and encoder seam.

---

## M4 Execution & Nav2

- **2026-07-03** — Deadlock fix "H3" branch merged and verified (runs 8–13):
  separation and single-cycle resolution fixed; motion BVH requires the
  triple kit-arg. Open item at merge time: Nav2 pull-off recovery loop
  (superseded in design by the rev-8 derived-candidate retreat).
- **2026-07-02/03** — Backup-not-moving fix (commit `05ab38f`): robots stayed
  stationary despite backup COMPLETED because of a cancel-all race plus
  `collision_monitor` `stop_pub_timeout: 2.0` both zeroing `cmd_vel`.
  Odometry-based `backup()` then verified end-to-end on a fresh natural
  deadlock: 0.8 m backup + hold + yield complete.
- **2026-06-28** — Nav2 stall (M4 Phase 2 Task 8) resolved in `09778fa`:
  scan-namespace remap + DWB goal-tolerance fixes; clean rebuild reproduced
  goal reach at 0.0964 m.
- **2026-06-25** — Nav2 Jazzy parameter typing: integer parameters supplied
  as floats crash `bt_navigator` silently (`default_server_timeout: 60`
  works, `60.0` dies). Applies to all Nav2 YAML in
  `ros2_ws/src/swarm_simulation`.
- **2026-06-24** — M4 Phase 2 runs Nav2 in a `ros:jazzy` container with the
  Isaac side overridden to `ROS_DISTRO=jazzy`; transport/TF/map remap bugs
  from the pivot are confirmed fixed. See `docs/specs/module4/`.
- **2026-06-21** — Drive-chain fixed-base bug: the URDF importer's `fix_base`
  welded `base_link` to the world; freeing the chassis requires disabling
  the generated `base_joint`. Verified and landed (M4 Phase 1; report:
  `docs/reports/2026-06-21-m4-phase1-completion.md`).

---

## M6 Simulation / Isaac Sim

- **2026-09-16** — Simulation rebuilt and re-verified on a new host after the
  old VM was deleted: `vgu-canary-base-isaac-workstation-vm` (project
  `summer-flux-501516-n6`, us-central1-a, g2-standard-8 + L4, Isaac Sim
  6.0.0-rc.59 source build at `/home/ubuntu/IsaacSim`). Full asset chain
  rebuilt from a clean checkout — URDF import → `warehouse_base.usd` →
  `head_on_deadlock.usd` → `validate_simulation` **PASS** → headless run
  `completed: true, failure: null`, 451 ground-truth records over 45 sim-s,
  camera render product live (`rgb (960,1280,4) mean=127.95`). Isaac's bundled
  Jazzy `rclpy` loads inside Kit, so no host ROS 2 is needed for a sim-only
  run. Three facts worth keeping:
  - **Robot visual meshes were never in the repo.** The committed URDF
    references `meshes/{burger_base,left_tire,right_tire,lds}.stl`, which do
    not exist, so a plain import of it yields collision primitives only.
    Supplying the four ROBOTIS STLs next to the URDF imports 4 visual meshes
    (burger_base 48 040 pts). **Confirmed** as the cause of the bodyless robots
    in `data/logs/recordings/h3_final_demo_v13.mp4`: a fresh overhead render on
    this host (mean 127.93, matching the run's render product) shows chassis,
    both wheels, and a cast shadow where the July frame had only a floating
    marker quad. The meshes currently exist **only on the VM**, not in git, so
    a rebuild from `git archive HEAD` on a fresh host reproduces the mesh-less
    import. Note the marker renders offset from the body centroid — expected,
    not a perception bias: `aruco_marker_joint` is at `base_link` with no x/y
    offset, while the `base_link` visual mesh carries a `-0.032 m` origin and
    `base_link` itself sits at the wheel axis. M1's marker-derived pose is
    therefore in the same frame as odom and ground truth.
  - **Nothing validates visual geometry.** `validate_robot_asset` checks the
    articulation root, wheel `DriveAPI`, and disabled `base_joint`;
    `validation.py` checks metadata, namespace, camera frustum, marker mesh,
    and unresolved references. A mesh-less import passes every gate.
  - **Imported meshes are instanced**, so `Usd.Stage.Traverse()` reports zero
    `UsdGeom.Mesh` prims. Use `Traverse(Usd.TraverseInstanceProxies())` when
    checking an imported robot asset, or the geometry looks absent when it is
    not.
  - The `turtlebot3_burger_1/` import collision (2026-06-18 report, item 3) is
    avoidable without a post-hoc merge: move the committed URDF+meshes to a
    staging dir, free `isaac/assets/robots/turtlebot3_burger/`, then import —
    the importer writes the un-suffixed path `paths.robot_asset_path()` expects.
- **2026-09-16** — `vgu_ros` container rebuilt from scratch and verified
  against host Isaac. The container was never defined in the repo (only
  `.devcontainer/Dockerfile`, which is a *different* base —
  `osrf/ros:jazzy-desktop`), so it died with the old VM. Recipe that works,
  from plain `ros:jazzy` (the image every Nav2 param finding in
  `docs/specs/module4/phase2-nav2-stack.md` was validated against — do not
  swap the base without revalidating those):
  ```
  docker run -d --name vgu_ros --network host --ipc=host \
    -v /home/ubuntu/vgu-vlm-swarm:/ws -w /ws ros:jazzy sleep infinity
  apt-get install -y --no-install-recommends ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup python3-colcon-common-extensions python3-opencv \
    python3-jsonschema python3-pip
  pip3 install --break-system-packages "pydantic>=2.7"
  colcon build --symlink-install --merge-install   # in /ws/ros2_ws
  ```
  Verified: 5 swarm packages registered, `swarm_interfaces` msgs import,
  `/clock` delivering at ~12 Hz **inside** the container (data, not just
  discovery — the 2026-06-19 root cause), `/robot_1/odom` and `/tf` echoing,
  and `controller_server`/`planner_server`/`bt_navigator` all lifecycle
  `active` with `/robot_1/navigate_to_pose` live. Notes:
  - `--network host --ipc=host` plus `FASTRTPS_DEFAULT_PROFILES_FILE=
    /ws/config/dds/fastdds.xml` on **both** sides remains mandatory.
  - Stock `ros:jazzy` has numpy and yaml but **no** cv2, pydantic, or
    jsonschema, and zero nav2 packages.
  - apt `python3-opencv` is 4.6.0, which exposes `DetectorParameters` but
    **not** `ArucoDetector`. That is fine and deliberate: `detection.py`
    version-gates on `ArucoDetector` and takes the legacy
    `DetectorParameters_create()` path. Do **not** pip-install
    `opencv-contrib-python` on top — mixing the two is what the 4.6.0 segfault
    comment in `detection.py` warns about.
  - apt `jsonschema` is 4.10.3, below `requirements.txt`'s `>=4.22`. The only
    API used (`Draft202012Validator`) exists in 4.10, so it was left alone —
    revisit if schema validation misbehaves.
  - Without Isaac running, `local_costmap` blocks on
    `robot_1/base_link -> robot_1/odom` and Nav2 never activates. That is
    expected, not a container fault: the frame comes from Isaac. Nav2 activates
    on its own once the sim publishes TF.
- **2026-07-04** — Aisle-width congestion gap closed: 0.55 m × 2.0 m
  `aisle_barrier` corridor built and verified in
  `isaac/config/scenarios/head_on_deadlock.yaml`.
- **2026-07-01** — Scenario YAML edits are inert until `build_scenario`
  regenerates the USD; a stale USD cost ~10 debugging runs. Always rebuild
  after editing anything under `isaac/config/scenarios/`.
- **2026-06-30** — Host-launched Isaac needs
  `FASTRTPS_DEFAULT_PROFILES_FILE` forcing UDP transport; otherwise
  shared-memory transport silently drops all data to the Nav2 container and
  the system looks hung.
- **2026-06-21** — Fabric/USD sync for Newton articulations: enable
  `enable_fabric_usd_notice_handler` and write world positions to Fabric
  after each step; `omni.physx.fabric` does **not** work for Newton
  articulations (report:
  `docs/reports/2026-06-21-m6-fabric-sync-investigation.md`).
- **2026-06-18** — The Isaac Sim machine is Windows: guides and commands for
  that host use PowerShell and `python.bat` (see `docs/guides/`).
