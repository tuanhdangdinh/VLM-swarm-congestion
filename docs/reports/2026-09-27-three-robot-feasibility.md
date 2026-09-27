# Three-Robot Feasibility for T2b — Layer-by-Layer Investigation

**Prepared:** 2026-09-27

**Revision history:**

- Initial draft: read-only audit of what a third robot (`robot_3`) needs in every layer for the T2b flow-ordering tier, with file:line evidence, per-layer verdicts, a build list and the dominant risk.

---

## Purpose

The scenario battery design
(`docs/superpowers/specs/2026-09-27-scenario-battery-design.md`, T2b
section, lines 78–126) makes "three-robot support end-to-end" a hard gate
for T2b. In that design, `robot_1` (west) and `robot_2` (east) form a
symmetric `wopen_eopen` head-on, and `robot_3` queues behind `robot_1` with
a goal to the east. The oracle order is `[robot_1, robot_3]` crossing, with
`robot_2` yielding once.

This report audits every layer against that design at tree `4a71ffb`. It
reads the code rather than assuming it and does not modify any. Where
live-run data exists, it is cited by run id.

The short answer:

- Nothing hard-codes two robots on the plumbing path: Isaac spawn, ArUco,
  per-robot Nav2 launch, M4 client fan-out, the M5 registry, the shadow
  buffer and the prompt all scale by data.
- The layers that decide what happens once the robots move do not scale:
  - M3 command shape.
  - M4 hold and release semantics.
  - M4 safety exemption scope.
  - Arm B's head-on rule.
  - The ROI/geometry budget.
- Those are the build.

---

## Sources Checked

| Area | Files (tree `4a71ffb`) |
|---|---|
| Scenario schema / Isaac | `isaac/vgu_sim/config.py`, `scenario_builder.py`, `marker_asset.py`, `robot_asset.py`, `runner.py`, `acceptance_logging.py`, `oracle.py`, `cmd_vel_watchdog_node.py`, `family_oracle.py`, `isaac/scripts/generate_head_on_family.py`, `isaac/vgu_sim/warehouse_builder.py` |
| Markers / M1 | `scripts/generate_aruco_markers.py`, `scripts/verify_marker_ids.py`, `isaac/vgu_sim/paths.py`, `ros2_ws/src/swarm_perception/config/{aruco,calibration}.yaml`, `perception.launch.py`, `perception_node.py`, `pipeline.py`, `state_estimator.py` |
| Nav2 / launch | `scripts/vm/fc_launch.sh`, `ros2_ws/src/swarm_simulation/launch/{nav2_robot,nav2_navigation}.launch.py`, `config/nav2_params.yaml`, `maps/warehouse_map_head_on_asymmetric_wopen_eopen_o0.*` |
| M3 / M4 | `reasoning/rag/command_grounder.py`, `maneuver_geometry.py`, `scene_geometry.py`, `config/rag.yaml`, `swarm_execution/{command_bus_node,coordination_client_node,base_mission,nav2_adapter,safety,safety_monitor_node}.py`, `config/safety.yaml` |
| M5 | `swarm_orchestrator/{orchestrator_node,congestion_detector,state_machine,presentation_order,command_lifecycle,shadow_classical,task_registry,reasoning_pipeline}.py`, `config/orchestrator.yaml`, `reasoning/baselines/classical_reasoner.py` |
| M2 | `reasoning/vlm/prompt_builder.py`, `motion_table.py` |
| Run data | `data/logs/vm_runs/t0_t3c_verify/{20260927_111348,20260927_113513}`, `data/logs/vm_runs/t3c_v2/{20260927_123505,20260927_124234,20260927_125419}`, findings Rev 15 §AS / Rev 16 §AT |
| Design refs | battery design (T2b), research design rev 8.6 §A.4 (Pillar 3), `docs/implementation_notes.md:193` |

---

## Verdict Matrix

| Layer | Verdict | One-line reason |
|---|---|---|
| 1. Scenario schema / Isaac | WORKS (spawn) + NEEDS-BUILD (oracle schema) | Robot list is unbounded and the USD/graph chain is per-robot; `OracleConfig` cannot hold `correct_order` |
| 2. ArUco / M1 | WORKS | `marker_3.png` is committed, the dictionary has 50 ids, and the id filter is registry-driven; `robot_3` only has to be in `initial_tasks` |
| 3. Nav2 stacks | NEEDS-BUILD (small) | Launch file is per-robot generic; `fc_launch.sh` hard-codes exactly two stacks in four places |
| 4. M4 execution / safety | NEEDS-BUILD (large) + NEEDS-DECISION | Fan-out works; the hold ends at the first passer; `linked_position` is ignored; the clearing exemption is robot-scoped, so a yielder can reverse into `robot_3` unguarded |
| 4b. M3 command shape | NEEDS-BUILD | Legacy yield commands only `robot_ids[0:2]`, so `robot_3` gets nothing; derived mode is not live, and its backup rule can "pass through" a robot behind |
| 5. M5 orchestration | WORKS (registry, shadow buffer) + NEEDS-DECISION (episodes, order, Arm B) | A `robot_3`-only stall opens a new episode mid-maneuver; `id_asc`/`id_desc` do not counterbalance the standoff pair at N = 3; Arm B's head-on rule refuses a pair with a third stopped robot within 1.5 m |
| 6. M2 prompts | WORKS (+72 tokens est.) + NEEDS-DECISION (flow evidence) | Pairwise lines scale as N(N−1)/2; the "motion table and trails" the design relies on are not in the prompt |
| 7. Camera / ROI geometry | NEEDS-DECISION | The tracked x-range, park points, `r_conflict_m` and the 0.45 m latch leave no position for `robot_3` that satisfies every constraint at trigger time |

---

## Layer 1 — Scenario Schema and Isaac Side

### What exists

- **The robot count is unbounded.** `ScenarioConfig.robots` is a plain
  `tuple[RobotScenarioConfig, ...]` (`isaac/vgu_sim/config.py:219`).
  Validation enforces only:
  - the `robot_N` id format (`:32`);
  - `marker_id` in 1..49 (`:39`);
  - uniqueness (`:267–272`);
  - `marker_id == N` (`:274–279`).
- **USD authoring loops over all robots.**
  - `build_scenario_stage` iterates `config.robots` (`scenario_builder.py:51–52`).
  - Each robot is a reference to the one shared TurtleBot3 USD at
    `/World/Robots/<robot_id>` (`:79–89`), with its own goal sphere and
    ROS-graph prim (`:91–97`).
  - Each robot gets its own ArUco quad (`:104–106`).
  - Nothing names `robot_1` or `robot_2`.
- **The runtime is per-robot.**
  - The runner wires each robot's drive graph, contact friction and RTX lidar
    in a loop (`runner.py:384–398`).
  - It starts one cmd_vel watchdog per robot id (`runner.py:410–413` →
    `cmd_vel_watchdog_node.spin_in_thread`).
  - It waits for `/<id>/odom` and `/<id>/scan` for every robot (`runner.py:436–460`).
  - The only literal pair is the standalone `main()` in
    `cmd_vel_watchdog_node.py:141–155`, which the runner does not use.
- **The marker sits under the physics hierarchy per robot.** The quad is
  authored at
  `<robot>/Geometry/base_footprint/base_link/aruco_marker_link/aruco_marker`
  (`marker_asset.py:28–31`) for every robot, so the placement gotcha is
  satisfied automatically.
- **Proven live.**
  - `dynamic_anomaly.yaml` declares four robots. Its smoke runs
    (`20260927_113513`, `20260927_123505`) spawned all four.
  - Ground truth logs `robot_1..robot_4` from the first row
    (`ground_truth/ground_truth.jsonl`).
  - Isaac reached `completed: true` (`run_manifest.json`).
  - The Rev 15 §AS defect "four robots but two Nav2 stacks" is a launcher
    defect (Layer 3), not an Isaac one.

### What breaks or needs care

- **`OracleConfig` cannot express T2b's oracle.**
  - Its fields are `correct_yielder`, `fcfs_yielder`, `feasible_yielders`,
    `objective` and `rationale`, with `extra="forbid"` (`config.py:174–193`).
  - A YAML carrying the design's `correct_order` fails to load.
  - `feasible_yielders` must contain the correct yielder (`:185–193`), which
    is fine for T2b (`robot_2`).
  - Build: add an optional `correct_order: tuple[str, ...] | None`, validated
    as a permutation of the involved robots minus the yielder, plus a
    `margin_pct` or equivalent verification record if the oracle block should
    carry the ≥ 20% margin.
- **The ground-truth `conflict_active` needs exactly two involved robots.**
  `_head_on_active` returns `False` unless
  `len(expected_conflict.involved_robots) == 2` (`acceptance_logging.py:52`).
  `oracle.head_on_conflict_active` raises on anything else (`oracle.py:74–75`).
  T2b must keep `expected_conflict.involved_robots: [robot_1, robot_2]` and
  `family: head_on`. A three-robot involved list would silently log
  `conflict_active=false` for the whole run.
- **`ScenarioFamily`** (`config.py:208`) has no flow-ordering family. Reusing
  `head_on` works (see above). A new family literal would also need a
  `conflict_active` rule.

### Family generator two-robot assertions (enumerated; they stay)

| Location | Assertion |
|---|---|
| `isaac/scripts/generate_head_on_family.py:250–253` | `_opponent_spawn_goals` raises unless exactly two robots |
| `isaac/scripts/generate_head_on_family.py:307–310` | `_blocked_short_goals` raises unless exactly two robots |
| `isaac/scripts/generate_head_on_family.py:391` | only `robot_2`'s spawn is shifted by `arrival_offset_m` |
| `isaac/scripts/generate_head_on_family.py:574` | manifest tier is `T1` if `len(feasible_yielders) == 2`, else `T2a` |
| `isaac/vgu_sim/family_oracle.py:23` | `SIDE_ROBOT = {"west": "robot_1", "east": "robot_2"}` |
| `isaac/vgu_sim/family_oracle.py:79, 139` | FCFS and `feasible_yielders` are hard-wired to `robot_1`/`robot_2` |

T2b needs its own generator function or a hand-authored YAML, as the design
says. None of these should be loosened.

**Verdict: WORKS for spawning. NEEDS-BUILD (S) for the oracle schema.**

---

## Layer 2 — ArUco Markers and M1

### What exists

- **The asset exists.**
  `isaac/assets/markers/aruco_4x4_50/marker_3.png` is committed (57 tracked
  files under `isaac/assets`, `marker_1..marker_49`).
  - The generator writes ids `range(1, 50)` (`scripts/generate_aruco_markers.py:31`).
  - The dictionary is `DICT_4X4_50`
    (`ros2_ws/src/swarm_perception/config/aruco.yaml:2`), with ids 0–49.
  - Scenario authoring resolves the PNG through the same config
    (`isaac/vgu_sim/paths.py:50–65`).
  - Marker 3 has been rendered and detected live: `robot_3` appears in
    `20260927_113513`'s first M5 scene row at (−0.003, −2.007).
- **`verify_marker_ids.py` is N-generic.** It derives the expected set from
  every `robots[].marker_id` (`scripts/verify_marker_ids.py:54–67`).
- **The M1 id filter is registry-driven, not a fixed list.**
  - `process_frame` uses `set(task_registry)` as the allowlist whenever M5's
    `/coordination/tasks` is non-empty, else the optional
    `expected_robot_ids` launch argument (`pipeline.py:44–53`).
  - `StateEstimator.update` drops tracked ids outside the allowlist
    (`state_estimator.py:129–131`) and skips detections outside it (`:163–166`).
  - The launch argument defaults to empty, meaning unfiltered
    (`perception.launch.py:42–50`).

### What breaks or needs care

- **`robot_3` must be in M5's `initial_tasks`.** Otherwise M1 filters it out
  of every scene once the registry arrives.
  - In `20260927_113513`, M5's scene log has `robot_3`/`robot_4` in the first
    row (stamp 11.97) and then 145 rows with no robots at all. `robot_1` and
    `robot_2` were outside the frame, and robots 3 and 4 were outside the
    registry.
  - That matches the registry filter. The M1 and M5 logs for that run are
    truncated (6 lines each), so this is the code path, not a logged
    confirmation.
- The same `initial_tasks` set is also the dispatch filter
  (`orchestrator_node.py:676–679` → `command_grounder.filter_command_robot_ids`,
  `command_grounder.py:123`). One config entry feeds both.

**Verdict: WORKS.** The only requirement is an `initial_tasks.robot_3` entry.

---

## Layer 3 — Nav2 Stacks

### Where the count is decided

Only in the VM driver `scripts/vm/fc_launch.sh`. There is no compose file in
the repo; the `vgu_ros` `ros:jazzy` container is VM-side. Every other layer
is generic.

| `fc_launch.sh` line | Two-robot hardcode |
|---|---|
| `:19–20` | header: "Assumes exactly two robots, robot_1 and robot_2" |
| `:240–241`, `:343` | only `NAV2_R1_LOG` and `NAV2_R2_LOG` exist and are collected |
| `:419–432` | spawn parse extracts only `R1_*` and `R2_*` and validates those six |
| `:459–462` | Isaac topic wait loops over `robot_1 robot_2` only |
| `:486–493` | two `nav2_robot.launch.py` calls and two `wait_action` calls |

The VM-side config generator is also two-robot templated
(`data/logs/vm_runs/t3c_v2/_vm_driver/gen_orch_t3c.py:23–27`, "robot_1 goal,
robot_2 goal").

### What exists per robot

- **`nav2_robot.launch.py` is parametrised on `robot_id` alone.**
  - `ReplaceString` substitutes `<robot_namespace>` across `nav2_params.yaml`
    (`:270–273`).
  - One `PushRosNamespace(robot_id)` group holds the full navigation stack and
    the per-robot `camera_localizer` (`:393–532`).
  - `start_map_server:=false` is already documented as "for the second (and
    further) robot" (`:308–316`).
- Per robot, `nav2_navigation.launch.py:56–65` starts eight lifecycle nodes
  as separate processes (`use_composition` defaults to `False`, `:107–111`):
  - controller at 20 Hz, smoother, planner, behavior;
  - `collision_monitor`, `bt_navigator`, `waypoint_follower`, docking.
- It also starts one lifecycle manager and one `camera_localizer`. A third
  stack is therefore about 10 more processes.
- **Maps are shared.** One non-namespaced `map_server` serves the
  per-scenario map to every stack. No per-robot map or params file is needed.
  Every frame, topic and polygon in `nav2_params.yaml` goes through the
  namespace token (`:33–36`, `:205–232`, `:346–380`).

### Load headroom (g2-standard-8, 8 vCPU)

- **No CPU or load data exists in any report or run log.** Headroom is
  unknown.
- **Throughput evidence.** Steady-state real-time factor (RTF) from M5 scene
  logs, `Δ(scene stamp)/Δ(wall t)` over the like-for-like 12→60 sim-s window:

| Run | Isaac robots | Nav2 stacks | RTF (12→60 s) |
|---|---|---|---|
| `20260927_111348` (T0) | 2 | 2 | 0.388 |
| `20260927_124234` (T0) | 2 | 2 | 0.393 |
| `20260927_125419` (T3c v2) | 2 | 2 | 0.395 |
| `20260927_113513` (old `dynamic_anomaly`) | 4 | 2 | 0.310 |
| `20260927_123505` (old `dynamic_anomaly`) | 4 | 2 | 0.277 |

- **Interpretation.**
  - Two extra Isaac robots cost about 0.08–0.12 RTF with the Nav2 count held
    at two. That is roughly 0.05 per robot, from lidar render products, drive
    graphs and physics.
  - Interpolating, a three-robot T2b would run near RTF ≈ 0.34 before its
    third Nav2 stack is counted. That stack's cost has never been measured.
- **Two consequences.**
  - M5's stall and cooldown clocks are wall time (`implementation_notes.md:40–50`).
    At RTF 0.34 the 12 s stall trigger is about 4.1 sim-s, down from about
    4.6. The `robot_3` timing in Layer 7 is sensitive to this.
  - The first three-robot smoke should record `uptime`/`mpstat` alongside the
    run.

**Verdict: NEEDS-BUILD (S).** Generalise `fc_launch.sh` to loop over the
scenario's robot list for the spawn parse, topic waits, Nav2 launches, action
waits and log collection. Do the same for the VM `gen_orch` script.

---

## Layer 4 — M4 Execution and Safety

### Fan-out: WORKS

- `Nav2Adapter` creates action clients lazily per robot id
  (`nav2_adapter.py:133–151`).
- `BaseMissionDriver` issues one `navigate_to_pose` per registry entry
  (`base_mission.py:55–84`).
- `CommandBusNode` keys every in-flight wait on `(command_id, robot_id)`
  (`command_bus_node.py:54–56`).
- A `robot_3` in the registry gets its base mission, cancels and holds with
  no code change.
- The safety monitor iterates over whatever robots the scene carries
  (`safety_monitor_node.py:154–206`).

### The yield hold ends at the FIRST passer (Pillar 3 question)

- The yield command watches a single `passer_robot_id`. It subscribes to that
  robot's odometry and finishes the hold when it has moved `passer_clear_m`
  (`command_bus_node.py:184–194`, `:239–253`).
- The escort also drives only that one robot (`:196–207`).
- At the yield's terminal status:
  - `_release_linked_waits` releases **every** wait under the command id at
    once (`command_bus_node.py:405–432`).
  - `BaseMissionDriver.on_status` re-issues the yielder's base goal
    (`base_mission.py:105–130`).
- `linked_position` is never read by M4. It appears only in the derived
  grounder (`command_grounder.py:1018`).
- "Pillar 3 release chain" (research design rev 8.6 §A.4, spec lines 788–817;
  flagged in `docs/implementation_notes.md:193`) has two parts:
  - robot k+1 releases on robot k's projected clearance;
  - **the yielder holds until the last robot in `crossing_order` clears**.
    None of this is built.
- **For T2b's oracle order** (`robot_2` yields, `[robot_1, robot_3]` cross):
  1. `robot_2`'s hold ends once `robot_1` has cleared.
  2. `robot_2` resumes west while `robot_3` is still approaching or inside the
     0.55 m corridor.
  3. That is a second head-on, `robot_2` against `robot_3`.
- Sequencing via yields means `robot_2` yields twice. The oracle's
  total-time margin would then measure a second standoff, not the ordering
  the tier exists to test.
- **T2b needs at least the hold-until-last half of Pillar 3.** The yielder's
  hold watches `crossing_order[-1]`, and later waits are released on the
  earlier robot's clearance. A strict chain is not required for N = 3 if the
  single wait is released at hold start, as the no-escort path already does
  (`:209–218`).

### Safety monitor pair logic

- **Pairs scale correctly.** `detect_proximity_violations` and the STALE rule
  use `itertools.combinations(robots, 2)` (`safety.py:237`, `:326`, `:334`).
  Three robots give three pairs.
- **The clearing exemption is robot-scoped, not pair-scoped. This breaks with
  a third robot.**
  - `detect_proximity_violations` skips every pair with an exempt member
    (`safety.py:237–239`). The STALE rule does the same (`:337–338`,
    `:346–348`).
  - The node never latches an exempt robot: `effective = flagged - exempt`
    (`safety_monitor_node.py:186`).
  - The exemption was designed for the yielder–passer pair (`safety.py:218–225`).
    With `robot_3` present it also silences the yielder–bystander pair.
  - `yield`/`reverse` backups publish raw `/<id>/cmd_vel`, bypassing
    `collision_monitor` (`nav2_adapter.py:196–231`). Its polygon is
    forward-only in any case (`nav2_params.yaml:365–370`).
  - **In the non-oracle order** (`robot_1` yields), `robot_1` reverses up to
    about 1.44 m, from about −0.35 to the −1.789 park point, straight along
    the lane where `robot_3` is queued, and no layer watches that pair.
  - The design's "scripted executions of both orders" harness would drive
    `robot_1` into `robot_3`.
  - **Build:** scope the exemption to the pair `(yielder, crossing robots it
    is clearing for)`. A clearing robot stays latchable against any other
    robot.
- **A trailing robot latches the passer (proximity rule).**
  - `robot_3` following `robot_1` is stopped by its own `collision_monitor`
    `forward_stop` polygon (x 0.02–0.25 m ahead of `base_link`,
    `nav2_params.yaml:369`).
  - Adding `robot_1`'s 0.07 m rear half-length (footprint
    `nav2_params.yaml:219`) gives a centre gap of about 0.32 m. That is
    inside `min_distance_m: 0.45` (`config/safety.yaml:2`).
  - M4 then latches both robots, and neither is exempt: `robot_1`'s action is
    a linked wait and `robot_3` may have no command at all.
  - The Isaac watchdog zeroes `robot_1`'s `cmd_vel_safe`, so the escort
    cannot move it.
  - Release needs a fresh reading at ≥ 0.45 m (`safety.py:287–289`), which
    cannot come while both robots are held. The run stalls permanently.
  - Whether `robot_3` actually closes to 0.32 m or its planner fails earlier
    is unmeasured; see Layer 7.

**Verdict: NEEDS-BUILD (L) + NEEDS-DECISION.** Two items:

- Hold-until-last release (Pillar 3 minimum).
- Pair-scoped clearing exemption.

The decision is how a queued follower may stand relative to the 0.45 m
latch (Layer 7).

### Layer 4b — M3 command shape (feeds M4; T2b cannot run without it)

- **Legacy yield (the live mode).** `rag.yaml:13` sets `mode: legacy`. The
  command has exactly two actions:
  - `yield` for `robot_ids[0]`;
  - `temporary_wait` for `robot_ids[1]` (`command_grounder.py:536–560`).
  - A third involved robot receives **no action**. Its base mission is never
    suppressed, and it keeps driving under Nav2 into the maneuver.
  - The park side and passer are computed from `robot_ids[1]` only (`:448–449`).
  - The feasibility gate's retreat side is documented as exact only for two
    robots (`:213–216`).
- **Derived mode (not live).**
  - It emits one `temporary_wait` with `linked_position` per
    `crossing_order` entry (`:1008–1022`), which M4 ignores.
  - `derive_backup_distance` accepts `d ≥ s + c` for a robot at positive
    retreat-axis offset `s` (`maneuver_geometry.py:262–266`). That means
    reversing *through* a robot queued behind.
  - With `backup_clearance_m: 1.7` (`rag.yaml:15`) and band [0.5, 2.0], a
    robot 0.5–3.7 m behind the yielder makes the yield infeasible. It then
    degrades to a reroute of the yielder (`:963–968`).
  - For T2b's non-oracle arm this is arguably the right answer, but it is not
    the "slower but valid" execution the harness assumes.
- **The contract is missing.** `crossing_order` does not exist yet (prompt-v2
  bundle, battery design lines 37–40). Without it, the command cannot name
  `robot_3`'s position.

**Verdict: NEEDS-BUILD (M).** Build an N-robot yield command:

- a yield for the yielder;
- an escort or release for `crossing_order[0]`;
- linked waits for the rest.

Fix the "pass through" branch of `derive_backup_distance` for robots behind
the yielder. Whichever grounding mode T2b runs in (legacy is live) must be
the one that is built.

---

## Layer 5 — M5 Orchestration

### What works

- **Task registry.** `initial_tasks` is `dict[str, TaskAssignment]`
  (`models.py:84`), loaded generically (`task_registry.py:33–37`) and
  serialised for every robot (`:67–73`). Adding `robot_3` is config only
  (`config/orchestrator.yaml:88–90`).
- **Stall detector.**
  - The per-robot progress stall covers every robot with a goal
    (`congestion_detector.py:80–109`).
  - The close/slow rule is all-pairs (`:149–165`).
  - The event carries every stalled robot (`:125–131`).
- **Shadow buffer.** `snapshot_to_frame` projects every robot in the snapshot
  (`shadow_classical.py:40–69`). The ring buffer is robot-agnostic (`:147–191`).

### What misbehaves with three robots

- **`robot_3` can open a new episode in the middle of the maneuver.**
  1. While `robot_1` and `robot_2` are busy, `robot_3` stalls behind them.
  2. Its event `{robot_3}` is disjoint from the busy set, so the gate passes
     it (`state_machine.py:62–64`, busy set from `orchestrator_node.py:935–940`).
  3. A fresh analysis starts, and its command can reach `robot_3`
     mid-maneuver.
  4. `EpisodeOrderTracker` treats a disjoint set as a new episode and redraws
     the order (`presentation_order.py:105–109`).
  5. `AttemptMemory` drops context on a disjoint set (`command_lifecycle.py:205`).
  6. The next re-analysis of `{robot_1, robot_2}` is disjoint from `{robot_3}`
     and draws again, splitting one T2b episode into three.
  - The inverse also happens. `end_episode` closes the whole episode on **any**
    member's arrival (`presentation_order.py:114–127`, called at
    `orchestrator_node.py:906, 923`). `robot_1` arriving first closes the
    episode while `robot_2` and `robot_3` are still resolving.
- **Presentation order does not counterbalance the standoff pair at N = 3.**
  - Only `id_asc` and `id_desc` are drawable (`presentation_order.py:16`), and
    ordering is a plain id sort (`prompt_builder.py:279`).
  - Under `id_desc` the first slot goes to `robot_3`, the non-standoff robot.
    Under `id_asc` `robot_1` always precedes `robot_2`. `robot_2` never gets
    the first slot.
  - The Rev-14 finding is that gpt-4o's choice follows a first-slot prior plus
    a `robot_1` prior. T2b's contrast is exactly "`robot_2` should yield", so
    this confound lands on the scored variable.
  - Options: a pair-swap order (`robot_2, robot_1, robot_3`) as the second
    drawable order, or all six permutations with conditioning.
- **Arm B's head-on rule refuses the T2b scene.**
  - `_head_on_pair` rejects a pair when any third *stopped* robot is within
    `r_conflict_m` of either member (`classical_reasoner.py:389–404`;
    `r_conflict_m: 1.5`, `rag.yaml:31`, frozen under tuning parity).
  - With `robot_3` stopped behind `robot_1`, Arm B falls through to
    `blocked_path`/`unknown`, and the FCFS contrast the tier exists for
    disappears.
  - The design already names this as an open question (battery design lines
    117–122). Layer 7 shows it cannot be satisfied by spawn placement alone.

**Verdict: WORKS for the registry and shadow buffer. NEEDS-DECISION + BUILD
(M) for:**

- episode scoping at N = 3 (union-find over overlapping sets, and close on
  last arrival rather than first);
- a stall gate that treats a queued follower as part of the busy pair's
  episode;
- a three-robot presentation-order scheme;
- whether Arm B's crowding clause is amended pre-freeze.

---

## Layer 6 — M2 Prompts

- **Nothing is hard-coded to two robots.**
  - The state block renders every robot in the snapshot
    (`reasoning_pipeline.py:94–104` → `prompt_builder.py:235–263`).
  - Pairwise geometry is all-pairs, in presentation order
    (`prompt_builder.py:288–321`).
  - "Known robot IDs" lists all of them.
- **Measured rendering (offline, `build_prompt_payload`).**
  - Adding `robot_3` adds one state line and two pairwise lines: +286
    characters, about +72 text tokens (3402 → 3688 characters). This is a
    chars/4 estimate because `tiktoken` is not installed.
  - The image dominates the request, so the cost is negligible.
- **Content observations for T2b.**
  - All three robots lie on y = 0, so the facing test marks `robot_2 ↔ robot_3`
    as mutually facing at 1.55 m. That is a second "head-on-looking" pair line
    that the guidance's 0.5 m clause has to discount.
  - The template's head-on guidance is written for "two robots"
    (`prompt_builder.py:40–56`).
  - The header says "sorted by ID" regardless of order (`:34`), a known
    prompt-v2 rider.
- **The flow evidence the design relies on is absent.**
  - The battery design says the correct order is "visible in the motion table
    and trails" (line 83). The motion table (`reasoning/vlm/motion_table.py`)
    feeds only Arm B's shadow; `prompt_builder.py` never references it.
  - M1's annotation draws no trails.
  - Goals are sent as `None` (`reasoning_pipeline.py:101`; the RobotView has
    no goal) until the prompt-v2 goals decision.
  - Today the VLM sees only `robot_3`'s position and heading, not that it is
    traffic headed east.

**Verdict: WORKS mechanically. NEEDS-DECISION:** does T2b require goals
(prompt-v2 item 3) and/or a rendered motion table before its oracle is
fair to the VLM?

---

## Layer 7 — Camera/ROI and T2b Geometry

### The tracked area is narrower than "ROI ±3.0"

- The M1 homography maps the full 1280 × 960 image at marker height
  (`plane_height_m: 0.21`) to **x ∈ [−2.789, +2.789], y ∈ [−2.092, +2.092]**
  (`ros2_ws/src/swarm_perception/config/calibration.yaml`, homography row
  offsets −2.7893 and +2.0920 with scale 0.004358 m/px).
- The 6.0 × 4.5 m `CameraConfig` ROI (`isaac/vgu_sim/config.py:379–380`) is
  checked at floor level (`validation.py:64–70`).
- **Evidence.** ±2.5 is verified (head-on family, `normal_flow`), and ±3.0
  gave 0/146 detections (Rev 15 §AS, `dynamic_anomaly`).
- **The practical robot-centre limit is |x| ≲ 2.6.**

### The aisle and rack blocks are fine

- Rack blocks fill the four quadrants outside the 1.2 m cross aisles
  (`warehouse_builder.py:101–113`).
- The `wopen_eopen` map is free for |y| < 0.6 at every x from −2.8 to −1.2
  (sampled from `warehouse_map_head_on_asymmetric_wopen_eopen_o0.pgm`). The
  0.55 m barrier corridor starts at x = −1.0.
- A `robot_3` at (−2.0 … −2.6, 0.0) is inside the aisle, 0.6 m from the rack
  faces, and inside the tracked area.
- T2b can reuse that map as the per-scenario map. The launcher requires
  `warehouse_map_<SCENARIO>.yaml` (`fc_launch.sh:183`).

### The constraints at trigger time do not close

| Constraint | Source | Implied `robot_3` x |
|---|---|---|
| Tracked by M1 | homography edge 2.789, verified ±2.5 | ≥ −2.6 |
| No latch against `robot_1` at spawn (`robot_1` at −1.5) | `safety.yaml:2` (0.45 m) + M1 bias | ≤ −2.0 |
| Arm B sees a two-robot head-on | `r_conflict_m` 1.5 from `robot_1` at standoff ≈ −0.35 | ≤ −1.85 while *stopped* |
| `robot_1` can reach its park point (non-oracle arm) | park at −1.789 (`scene_geometry.park_offset_m`) + 0.45 latch | ≤ −2.24 |
| `robot_1` backup feasible in derived mode | `backup_clearance_m` 1.7 | ≤ −3.5 (outside frame) |
| `robot_2`'s `wopen_eopen` goal | goal (−2.5, 0.0) in the family YAML | collides with `robot_3`'s spot |

The dynamics make it worse:

1. Both robots drive at `max_vel_x: 0.18` (`nav2_params.yaml:96`), and
   `BaseMissionDriver` dispatches every registry goal at once. There is no
   per-robot start delay anywhere.
2. The spawn gap of at most about 1.1 m (−2.6 vs −1.5) is therefore still at
   most about 1.1 m when `robot_1` stops.
3. `robot_3` then closes that gap. About 0.8 m at 0.18 m/s takes about
   4.4 sim-s, which is the same as M5's about 4.1–4.6 sim-s wall-clock stall
   window.
4. At trigger time `robot_3` is therefore either just stopping about 0.32 m
   behind `robot_1`, which gives the Layer 4 latch deadlock and Arm B
   crowding, or still moving.
5. **Alternative.** Its global planner may fail once `robot_1` and `robot_2`
   block the 0.55 m corridor, and stop it wherever it is. T3c v2 saw a stall
   1.43 m short of a box, at the point where planning first failed (Rev 16
   §AT). That is still inside 1.5 m of `robot_1`.

In the non-oracle arm, the design's premise ("`robot_3` is blocked behind the
parked yielder") also does not match the mechanics:

- The yielder parks at x = −1.789, pulled 0.36 m off-centre
  (`scene_geometry.pull_off_lateral_m`).
- That leaves a Nav2 lane of y ∈ [−0.41, +0.08] for `robot_3` in the 1.2 m
  aisle, so a parked yielder does not block it.
- What actually happens is that the yielder cannot *reach* its park point
  because `robot_3` is standing on it.
- The wrong order is therefore infeasible, or a collision under today's
  exemption, rather than measurably slower.

**Verdict: NEEDS-DECISION.** No spawn placement satisfies the tracked-area,
latch, Arm B and park-point constraints together. Candidate resolutions, each
new mechanism or a design change:

- (a) a per-robot start delay in `initial_tasks`, so `robot_3` is released
  after the trigger;
- (b) a per-robot speed cap for `robot_3`;
- (c) a scene where `robot_3` waits stationary at x ≈ −2.5 until its release,
  as parked downstream traffic;
- (d) move the conflict off the ROI centre, or raise the camera, to buy
  x-range;
- (e) re-state T2b's cost model: the wrong order is infeasible rather than
  slower, which changes the ≥ 20% margin criterion into a feasibility
  contrast. That overlaps T2a.

---

## Decision — Consolidated Build List (by effort)

| # | Item | Layer | Effort | Blocks |
|---|---|---|---|---|
| 1 | Add `robot_3` to `initial_tasks` (M1 allowlist + dispatch filter) and to the VM `gen_orch` template | M1/M5 config | XS | everything |
| 2 | Reuse the `wopen_eopen` map as `warehouse_map_<t2b>.yaml`; build the T2b USD on the VM | M6 | XS | smoke |
| 3 | `OracleConfig.correct_order` (optional, permutation-validated) + margin record; keep `expected_conflict.involved_robots` at two | M6 schema | S | oracle freeze |
| 4 | `fc_launch.sh`: loop spawn parse, topic waits, Nav2 launch/`wait_action` and log collection over the scenario's robot list | M6 driver | S | smoke |
| 5 | Load capture (`mpstat`/`uptime`) in the first three-robot smoke; record RTF against the 0.39 baseline | M6 ops | S | capacity sign-off |
| 6 | M5 episode scoping at N = 3: merge overlapping sets, close on last arrival, and fold a queued follower's stall into the busy pair's episode (gate) | M5 | M | clean artifacts |
| 7 | Three-robot presentation-order scheme (pair-swap or permutations) | M5/M2 | S–M, plus design decision | scoring validity |
| 8 | Pair-scoped clearing exemption in `safety.py` (clearing robot stays latchable against non-partners) | M4 | M | safe forced-order harness |
| 9 | N-robot yield grounding (crossing-order escort/release + waits for all) in the mode T2b runs; fix `derive_backup_distance` "pass-through" for robots behind | M3 | M | `robot_3` suppression |
| 10 | Hold-until-last + ordered release in `command_bus_node` (Pillar 3 minimum; honour `linked_position` / `crossing_order`) | M4 | L | oracle order executes as "`robot_2` yields once" |
| 11 | Forced-order harness (mock `crossing_order` sequences, total time-to-goal from ground truth, n ≥ 2 seeds per order) | M6 driver | M | oracle validity |
| 12 | Geometry resolution from Layer 7 (start delay, speed cap, stationary `robot_3`, or reframed cost model) | design + M4/M5 | M–L, plus decision | everything after the smoke |

Decisions the owner must make before items 6–12 are specified:

1. The Layer 7 geometry resolution (a–e).
2. Whether Arm B's crowding clause is amended pre-freeze, or T2b accepts that
   Arm B is not a head-on classifier here.
3. Whether T2b requires goals and/or the motion table in the prompt.
4. The three-robot presentation-order scheme.

---

## Risks and Mitigations

- **Biggest risk: the T2b scene as designed does not fit the apparatus.**
  - The camera's tracked x-range (≈ ±2.6), the fixed park points (±1.789),
    Arm B's frozen `r_conflict_m` (1.5 m) and M4's 0.45 m latch together leave
    no position where `robot_3` is "far enough not to join the standoff" at
    trigger time.
  - A follower that closes in latches the passer into a permanent hold.
  - In the wrong-order arm, the yielder's retreat path runs through `robot_3`,
    and today's robot-scoped exemption leaves that pair unguarded.
  - **Mitigation:** settle the Layer 7 decision on paper before any code.
    Then run a mechanical smoke with the mock backend and a stationary or
    delayed `robot_3`, measuring:
    - `robot_3`'s stop distance behind `robot_1`;
    - latch events;
    - Arm B's classification.
- **The oracle order re-deadlocks without Pillar 3.** The yielder resumes
  after the first passer. Mitigation: item 10 before any oracle-validity run.
- **The forced-order harness can cause a collision.** Mitigation: item 8
  lands before the wrong-order arm is ever executed.
- **Presentation-order confound on the scored variable.** Mitigation: item 7,
  with the decision recorded in the T2b YAML header.
- **Lower RTF shifts every wall-clock M5 threshold in sim-time.** Mitigation:
  item 5. Author `robot_3` timing from the measured three-robot RTF, not 0.38.
