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

- **2026-09-16** — **Yield sizing derived from declared scene geometry**
  (`8cfb186`). Supersedes the constant-based sizing in the two entries
  below: `PARK_ABS_X_M` (1.8), `pull_off_lateral_m` (0.35) and
  `PASSER_CLEARANCE_M` (0.65) remain only as the no-geometry fallback.
  M5 now loads a `scenario_geometry` block from `orchestrator.yaml`
  (corridor axis/centre/half-length 1.0, aisle half-width 0.6, occluder
  height 0.9, camera 3.0, marker 0.21, robot half-width 0.09, marker
  half-size 0.06, safety radius 0.45, margins 0.3/0.15/0.2) and the
  pipeline passes it to `ground_reasoner_result(…, geometry=…)`.
  `reasoning/rag/scene_geometry.py` derives: visibility boundary
  = half_length·(cam−marker)/(cam−occluder) = 1.329; park offset =
  boundary + marker half + park margin = **1.689**; side-step =
  aisle half − robot half − wall margin = **0.36**; passer clearance =
  safety radius + margin = 0.65. The grounder works along the declared
  corridor axis (x or y) relative to `center_m`, emits `park_axis` and
  `park_coord_m` (and `park_x_m` when the axis is x), and its
  already-parked test is centre-relative (the old `park_x < 0` test
  silently assumed a corridor at 0). **Why:** the constants were
  scenario knowledge hidden in M3; the derivation makes the dependence
  explicit and lets another scenario declare different geometry instead
  of retuning code. The head_on park offset moves 1.80 → 1.69 m (still
  0.36 m outside the projected silhouette); live re-verification pending.
  The geometry block must be kept in sync with
  `isaac/config/scenarios/head_on_deadlock.yaml`, `isaac/config/warehouse.yaml`
  and `CameraConfig` by hand until M5 reads the scenario file.
- **2026-09-16** — **Yield grounding is now scene-aware** (`039d92e`).
  `ground_reasoner_result(result, robot_positions=...)` takes the robots'
  world (x, y) — the pipeline passes them from `request.robot_states`, one
  hop from `SceneSnapshot.robots` — and, for `yield`, parks the yielder at
  `park_x = ∓PARK_ABS_X_M` (1.5 m; its own side, away from the passer) with
  `backup = clamp(|yielder_x − park_x|, 0.3, 2.5)` and
  `escort = passer_clear = clamp(|passer_x − park_x| + 0.65, 0.5, 4.0)`
  (0.45 m safety radius + 0.2 m). `park_x_m` is emitted in the params for
  traceability. Without positions the old 1.3 m / 2.4 m constants remain as
  the fallback, so `reverse` and all prior tests are unchanged. **Why:**
  the fixed distances were sized for one standoff position; onset is
  bimodal (run 4 stall at ~1 m vs run 6 standoff at ~0.1 m), and the
  fixed park spot sat in the 0.9 m barrier's camera shadow (see run 6
  finding below). 1.5 m clears the block top by ≥ 0.24 m for any y.
  Base goals also moved ±3.0 → ±2.5 (`orchestrator.yaml`,
  `head_on_deadlock.yaml`): ±3.0 is the ROI edge (`roi_width_m 6.0`), so a
  robot at its goal was half off-frame. Goal spheres are baked into the
  scenario USD, so this needs `build_scenario` on the sim host. `GroundFn`
  became a `Protocol` to express the keyword. 11 new unit tests; suite
  failures unchanged from the pre-existing 21.
  **Live verification (run 7, 07:32–07:38 UTC, gpt-4o):** grounded from
  the real standoff — `park_x_m −1.5`, `backup 1.528` (yielder at x≈+0.03),
  `escort = passer_clear 2.287` (passer at ≈+0.14; M1 read 0.143). Yielder
  parked at world ≈ −1.47 (odom), passer escorted 2.291 m then Nav2 to
  −2.5; **both robots reached their ±2.5 goals and were detected there
  (`STOPPED`, not `STALE`)** — the ROI change works, and it is the first
  run in which the yielder completed its mission afterwards rather than
  looping in DWB recovery (runs 4, 6). gpt-4o: deadlock/yield, 1 743
  tokens, 5.5 s; 9 post-resolution analyses all `congestion_detected=false`.
  **Open defect:** at the poll nearest `COMPLETED`, M1 reported
  `markers_detected: 1, ids_missing: ["robot_1"]` — the yielder was
  undetected while parked at ≈(−1.47, +0.35). The barrier-occlusion model
  does **not** explain this pose (the camera ray crosses x = −1 at y ≈ 0.24,
  over the corridor gap, at z ≈ 1.1 m), so occlusion by the 0.9 m blocks is
  at most a partial explanation of run 6 and not the mechanism here. Common
  factor across runs 6/7 is the +0.35 m lateral offset near the corridor
  mouth; spawn (−1.5, 0) and the goals are detected.
  **Resolved by static render probe (same day):** rendering the stage with
  robot_1 placed at five poses and running `cv2.aruco` on each frame:
  spawn (−1.5, 0) ✓, parked (−1.47, +0.35) ✓, mirror (−1.47, −0.35) ✓,
  parked facing +y ✓, but (−1.20, +0.35) ✗ — the block covers all but a
  sliver. In the (−1.47, +0.35) crop the marker sits flush against the
  block's projected silhouette. The correct occlusion model is the block's
  *projected footprint on the marker plane*, not the ray to the marker
  centre: the block top (z = 0.9) projects to |x| ≈ 1.0·(3−0.21)/(3−0.9)
  ≈ 1.33 and |y| ≥ 0.275·1.329 ≈ 0.37, so a 0.12 m marker centred at
  |x| = 1.47 has ~0.08 m of clearance — inside the odometry error of a
  1.5 m reverse plus a turn-drive-turn sidestep, and inside anti-aliasing
  flicker at the silhouette. Fix: `PARK_ABS_X_M` 1.5 → 1.8
  (= 1.33 + 0.06 half-width + 0.3 margin). Downstream still fits: worst-case
  backup ≈ 2.4 (< 2.5 cap), escort ≈ 3.04 (< 4.0 cap, < 45 s hold), passer
  parks at ≈ −2.45 (goal −2.5).
  **Verified live (run 8, 08:11–08:17 UTC, gpt-4o):** yield params
  `park_x_m −1.8, backup 1.697, escort = clear 2.466` (yielder at −0.103);
  yielder parked at world (−1.785, +0.361), passer escorted 2.468 m; both
  `COMPLETED` at T+2 m 28 s; both robots reached their goals. A continuous
  `/perception/status` recording (4 022 msgs over the 5.5 min window,
  `dropped_frame` never true) shows **robot_1 missing in 13 of 835 frames
  (1.6 %) while parked, longest gap 0.86 s** — versus minutes-long loss in
  run 6 and a miss at the only sample in run 7. The occlusion defect is
  closed. What remains is detection flicker on *moving* robots: 483/4 022
  frames (12 %) miss one marker, max gap 1.5 s; robot_1's three longest
  gaps (1.30 / 1.02 / 0.90 s) all fall inside the turn-drive-turn sidestep,
  robot_2's 65 gaps (max 0.59 s) all inside its escort. All gaps are under
  `stale_after_sec: 3.0`, so none reached M5 as STALE. One frame reported
  `ids_unexpected: ['robot_41']` (a spurious id-41 detection), handled by
  M1's unexpected-id path. Safety monitor latched both robots at the
  standoff before dispatch and released for the backup, as designed.
- **2026-09-16** — **First live-VLM closed loop on the new VM** (run 6,
  06:27–06:33 UTC, `reasoning_backend_id: openai`, `gpt-4o-2024-08-06`):
  one analysis (`2 robot(s) close/slow >= 12.0s`) → decision
  `type=deadlock, strategy=yield, involved=[robot_1, robot_2]`,
  `parse_status=valid`, 1 attempt, 4.5 s latency, 1 814 tokens (≈ $0.006) →
  dispatch → M4 yield/temporary_wait → `COMPLETED` both at T+2 m 16 s →
  robot_2 reached its goal (odom 4.415 m ≈ run 4's 4.43). Zero backend
  errors. Artifact: `data/logs/m5_decisions/9fa91fded10c41a5ab3d0764077ec8d2.json`
  (on the VM). The model's `<think>` trace is sound: pairwise distance from
  M1 positions (0.12 m), opposing headings (Δθ ≈ π), both STALE → deadlock →
  first-listed robot yields. Findings:
  - **Scenario dynamics are not deterministic across runs.** Run 4 stalled
    at ~1 m (planner failure, single-robot stall trigger); run 6 formed a
    tight nose-to-nose standoff (M1 centres 0.12 m apart, close/slow
    trigger). Both are consistent with the new lidar visibility (see M6
    note); the experiment needs several runs to characterise the onset
    distribution before Arm A/B collection, and the congestion spec should
    admit both signatures or pin one.
  - **The yielder parks in the barrier's camera shadow.** M1 lost robot_1
    (`markers_detected: 0`, `ids_missing: [robot_1, robot_2]`) 1–3 min after
    dispatch in both runs 4 and 6. Geometry: barrier blocks are 0.90 m tall
    (`z_center 0.45, z_half 0.45`, `scenario_builder._author_aisle_barrier`)
    over x ∈ [−1, 1]; the overhead camera is at (0, 0, 3). After backing
    1.3 m and side-stepping +0.35 m the yielder sits near (−1.3, +0.35); the
    camera→marker ray crosses the block's west face at z ≈ 0.92 m (marker
    centre) and lower for the near half — partially occluded at run 6's
    pose, fully occluded (z ≈ 0.64 m) at run 4's (−1.18, 0.27). robot_2 is
    separately lost at its goal (x ≈ −2.93 is 15 px from the ROI edge). Net
    effect: M5 is blind to both robots exactly when it should confirm
    resolution or catch a re-deadlock. Options (undecided): lower the
    barrier (≈ 0.3 m keeps it a lidar wall at z = 0.172 while clearing the
    camera ray); widen the ROI; or park the yielder short of the block end.
  - Pre-flight gotcha: `/ws/.env` had `OPENAI_API_KEY= sk-…` (space after
    `=`), so `source` set the key empty and returned non-zero, which would
    have short-circuited the `set -a && source … && ros2 launch` chain.
    Fixed in place on the VM (untracked file). Worth a startup check in the
    demo script.
  - At analysis time both M1 tracks were already STALE (near-contact
    markers, the known 2026-06 behaviour), so the VLM decided on the last
    good positions. Fine here, but it means the decision input is frozen
    for the duration of any standoff.
- **2026-09-16** — **Full closed loop verified key-less on the new VM** (run 4,
  05:19–05:28 UTC): Isaac → M1 → M5 stall detection → scripted mock decision
  (`VGU_MOCK_DECISION_FILE=config/mock_decisions/head_on_yield.json`) → M3
  grounding → `dispatch` → M4 `command received ... action=yield` (robot_1)
  + `temporary_wait` (robot_2) → backup → pull-off → hold + escort → both
  `COMPLETED` → `resume base mission`. Stage durations (36 s backup, 33 s
  pull-off, 74 s escort) match the grounded 1.3 m / 0.35 m / 2.4 m at
  0.1 m/s and a ~0.35× realtime factor; robot_2 finished at map x≈−2.93
  (goal −3.0). This is the first time M3/M4 dispatch has been driven
  without a live VLM. Caveats, all observed in the same run:
  - **The trigger was not the July standoff.** No `safety stop` fired and
    `/safety/holds` stayed empty; M5 fired on `robots=['robot_2'] reason=1
    robot(s) stalled` after robot_2's planner failed (`Failed to create a
    plan from potential`) at ~1 m separation (odom: robot_1 +1.03 m,
    robot_2 +0.91 m from ±1.5 spawns). Leading hypothesis, unconfirmed: the
    newly added visual meshes make each robot visible to the other's RTX
    lidar, so Nav2 blocks earlier than the 0.45 m safety envelope. If true,
    the experiment's "deadlock" now manifests as a planner stall, not a
    nose-to-nose standoff — revalidate the congestion spec's onset
    assumptions before collecting Arm A/B runs.
  - robot_1 stuck after resume (`Failed to make progress` ×3 from
    1789536382), parked at odom (0.46, 0.34) near the wall — the open
    pull-off Nav2 recovery-loop item from 2026-07-03, reproduced.
  - M1 reported both robots `STALE` from 05:25:45 with byte-identical
    `scene_state` payloads thereafter; robot_2 at x≈−2.93 is at the ±3 m ROI
    edge, but robot_1 at x≈−1.18 was in view, so this looks like frames
    stopping rather than detection failing. Not yet diagnosed.
  - Nav2 ERROR on both robots: `inflation radius (0.070) is smaller than
    the computed inscribed radius (0.080) of your footprint`. Pre-existing
    and deliberate, not a regression: `local_costmap.inflation_radius: 0.07`
    has been set since `05ab38f` (2026-06-28) because Nav2's 0.55 m default
    is wider than the aisle; the 0.14×0.18 m footprint's inscribed radius is
    0.08, so Nav2 logs this on every launch. Safe to ignore.
  - Perception stamps ran ~9 s ahead of M5's clock (wall vs sim time);
    `frame_scene_max_skew_sec` did not block this run but worth knowing.
- **2026-09-16** — Key-less closed loop on the new VM stalls at M2 by design,
  not by fault: with `reasoning_backend_id: mock` M5 detected the standoff
  (`2 robot(s) close/slow >= 12.0s`, later `stalled >= 12.0s`), started an
  analysis every ~15 s and wrote a decision artifact each time, but every one
  ended `no dispatch stage=vlm reason=congestion_detected=false` — the mock's
  hard-coded `_DEFAULT_RESPONSE`. M4 therefore never received a command. The
  ~41k `trigger suppressed ... frame_ready=True` lines are just cooldown/busy
  gaps between those analyses, not a blocker. `build_backend("mock")` had no
  way to script a decision; a `VGU_MOCK_DECISION_FILE` hook was added so the
  loop can be exercised end-to-end without an API key (fixture:
  `config/mock_decisions/head_on_yield.json`). This supersedes the reading of
  the 2026-07-05 entry that only the openai swap remained: M3/M4 dispatch had
  never actually been driven from a mock decision.
- **2026-07-05** — M6→M1→M5→M2 closed loop runs end-to-end on the GCP/Isaac
  host with the mock backend; the only remaining swap for live reasoning is
  `backend_id: openai`, blocked on an API key.
- **2026-06-15** — Offline input-encoding ablation harness spec:
  `docs/superpowers/specs/2026-06-15-m2-input-ablation-design.md`. Rev-8 of
  the congestion spec governs live-loop modality conditions; the 06-15 doc
  remains the spec for the offline benchmark runner and encoder seam.

---

## M4 Execution & Nav2

- **2026-09-16** — **`localization:=amcl` option added, host-unverified.**
  `nav2_robot.launch.py` now takes `localization:=static|amcl` (default
  `static`, behaviour unchanged). Under `amcl`, the static
  `map_to_odom_ground_truth` node is not launched; instead a namespaced
  `nav2_amcl` node (params via the same `RewrittenYaml(root_key=robot_id)`
  wrapper the vendored navigation launch uses; initial pose from the
  `x/y/yaw` args; no node-level `/tf` remaps, per the launch docstring's
  findings) plus a `lifecycle_manager_localization` managing only `amcl`.
  `nav2_params.yaml` gains an `amcl:` block: Jazzy nav2_bringup defaults
  except namespace-token frames, absolute `scan_topic`/`map_topic`
  literals (same failure class as `global_costmap.map_topic`),
  `laser_{min,max}_range` = LDS 0.12/3.5, `update_min_d/a` tightened to
  0.05 m / 0.1 rad so a short backup still triggers filter updates.
  nav2_bringup's `localization_launch.py` is deliberately not used (it
  hardcodes its own `map_server`, colliding with the shared one).
  **Why:** the static transform is a ground-truth shortcut (disclosed in
  the experiment spec, App. A.7); AMCL leaves `/odom` untouched, so M4's
  odometry-closed primitives are unaffected by this step alone. Plan,
  risks (symmetric-corridor particle flip; `xy_goal_tolerance 0.1` margin;
  M1/map alignment unverified) and the odometry-noise follow-up:
  `docs/superpowers/plans/2026-09-16-amcl-localization-plan.md`. Host
  checks still to run are listed in `docs/specs/module4/phase2-nav2-stack.md`
  (2026-09-16 section).
- **2026-09-16** — Goal coordinates verified end-to-end on the rebuilt stack:
  with `nav2_robot.launch.py` given the scenario spawns (`x:=-1.5` /
  `x:=1.5 yaw:=3.14159265`), Nav2 logged `Begin navigating from current
  location (-1.50, -0.00) to (3.00, 0.00)` for robot_1 and `(1.50, 0.00) →
  (-3.00, 0.00)` for robot_2 — map-frame pose equals the YAML spawn, goal
  equals `orchestrator.yaml`'s `initial_tasks`. Both robots then drove into
  the aisle (M1 placed robot_1 at x≈0.00; `/robot_1/odom` on a fresh run
  showed 0.8 m forward travel), met head-on, and the safety monitor latched
  `min_distance_violation` on both — the intended standoff. Two caveats:
  (1) `scripts/run_phase3_demo.sh` still hardcodes `x:=-0.6 / 0.6` (stale
  since commit `0a0604c` moved spawns to ±1.5), which would misplace
  `map→odom` by 0.9 m — do not use it unpatched. (2) `safety_monitor_node`
  emitted 58 `safety stop ... min_distance_violation` WARN lines in 0.48 s
  at latch time (alternating robots) — noisy but not yet shown to be harmful.
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
- **2026-09-16** — **Ground-truth oracle fixed for position; time axis
  still wrong.** `acceptance_logging.sample_robot_positions` now reads the
  chassis prim (`/World/Robots/<id>/Geometry/base_footprint/base_link`,
  the single `ArticulationRootAPI` prim; `base_link` name as fallback) via
  `ComputeLocalToWorldTransform(Usd.TimeCode.Default())`, resolved once
  per robot and cached by *path* so a stage reload cannot return a dead
  prim. Host probe compared four sources on the same step: root Xform
  frozen at spawn; chassis USD world pose = `RigidPrim.get_world_poses()`
  exactly; a raw Fabric attribute read returned only the local translate
  (rejected). Verified on the VM with both robots driven at 0.1 m/s:
  `x` now changes (robot_1 −1.5 → −0.049, robot_2 +1.5 → +0.021 at the
  deadlock), `speed_mps` non-zero while moving, `conflict_active` true for
  the first time, and the logged positions match spawn+odom to four
  decimals for both robots (opposite signs). Pre-fix file preserved on the
  VM as `ground_truth.jsonl.prefix_buggy_*`. Supersedes the "not a motion
  oracle" entry below for *positions*.
  **Still open — time axis:** `runner.py` advances `sim_time` by one
  `physics_dt` per `app.update()`, but at `rendering_hz 30` /
  `physics_hz 60` each update steps physics twice, so the counter runs at
  ~½ true sim time (GT 25.4 s vs `/clock` 48 s). Consequences: every
  velocity in `ground_truth.jsonl` is inflated ~1.9× (0.181 logged vs
  ~0.116 true), and a declared `duration_sec` runs ~1.9× longer in real
  sim time. **Fixed in code, host-unverified:** the loop now sets
  `sim_time = sim_ctx.current_time − loop_start_time`, anchored at
  recording start because `event_scheduler` `spawn_at_sec` and
  `duration_sec` are authored relative to it (a raw clock would include
  the topic-wait startup time). The step-count sampling gate was removed
  (it would have halved the log rate to 5 Hz); `AcceptanceLogger`'s own
  10 Hz throttle governs. Host check: GT `sim_time_sec` vs `/clock` slope
  ≈ 1.0 (constant offset expected), logged `speed_mps` ≈ commanded.
- **2026-09-16** — **Robots are now mutually visible to RTX lidar; they were
  not before the mesh fix.** Probe (fresh sim, no Nav2, robots parked at
  ±1.5 facing each other, 3.0 m apart): each robot's forward ±10° sector
  returns 1.6–2.3 m (the 0.55 m corridor wall, at exactly the ranges
  `0.275/sin(bearing)` predicts) and then a cluster at **2.99–3.12 m** —
  matching the other robot's front plate edge (~2.99), LDS body (~3.06)
  and rear structure (~3.1) from the observer's lidar origin. Nothing else
  in the scene lies 3 m straight ahead (far wall > 3.5 m `range_max`).
  Caveat: the probe kept bearings only for sector minima, so "at 0°" is
  inferred from geometry, not measured. Why this is new: the scan plane is
  z = 0.172 m; before the STLs the only render geometry on a robot was the
  marker quad at z = 0.21 m (see `lidar.exclude_from_rtx_lidar` docstring,
  2026-06-25), and collision prims are not rendered — so July's robots had
  no lidar cross-section at all, which is why motion-BVH work was needed to
  get *anything* into the costmap. **Consequence:** Nav2 now sees the
  oncoming robot from 3 m. In run 4 the planner blocked at ~1 m separation
  and no standoff formed; in run 6 (same config) a tight nose-to-nose
  standoff did form. So the 0.45 m standoff the July H3 runs and the
  congestion spec assume is now one of at least two onset modes, not the
  only one. The spec's onset window and the safety-monitor's role need
  revalidating over several runs before Arm A/B data collection.
  Options, not yet decided: accept planner-stall as the deadlock signature;
  or exclude robot meshes from the lidar (Isaac RTX-visibility / semantic
  filtering) to restore the July geometry while keeping the camera view.
- **2026-09-16** — OpenAI key verified on the VM for `gpt-4o`
  (`/v1/models/gpt-4o` 200; 2-token chat completion answered from
  `gpt-4o-2024-08-06`). Stored only in `/home/ubuntu/vgu-vlm-swarm/.env`
  (`chmod 600`), sourced inside the container via `set -a && source
  /ws/.env && set +a` immediately before launching M5 — never on a command
  line.
- **2026-09-16** — **`ground_truth.jsonl` does not track robot motion.**
  `acceptance_logging.sample_robot_positions` reads
  `UsdGeom.Xformable(/World/Robots/<id>).ComputeLocalToWorldTransform(0.0)` —
  the USD transform of the robot *root* prim, which physics never updates
  (Newton moves the articulation in Fabric; see the 2026-06-21 Fabric entry).
  Evidence from one run: the file reported `x=-1.5, speed=0.0` for both
  robots for 300 sim-s while Nav2 logged navigation from that spawn, M1 saw
  robot_1 at x≈0.00, and `/robot_1/odom` showed ~0.8 m of travel. So
  `conflict_active`, `min_pairwise_distance_m`, and `speed_mps` in the
  acceptance log are all constant-at-spawn and must not be used as a motion
  oracle until this is fixed (read the chassis/`base_link` prim through
  Fabric/usdrt, or reuse the odom bridge). `/robot_N/odom` is the honest
  arbiter in the meantime. Unclear whether the July H3 runs relied on this
  file; their conclusions were drawn from M1 and odom, per the M4 notes.
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
