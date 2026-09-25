# Head-On Asymmetric Scenario Family — Design (T1/T2a battery)

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: parametric head-on family with parked blockers, computed oracle, static obstacles with real geometry; approved in chat (user, 2026-09-18).
- Rev 2 (2026-09-18): plan-time corrections — box 0.3 × 0.3 m (a 0.5 m box leaves no Nav2-legal flank lane), blocker 0.2 m, `arrival_offset_m` fixed at 0 in v1 (an offset on a blocked side is spatially impossible), `fcfs_yielder` defined by the rev-8 tiebreak rule, grid v1 = 3 variants, repo-tracked VM launch script.
- Rev 3 (2026-09-19): resolved the open design-review banner below with the
  decision actually taken (engineering proceeded; both observability
  channels were built as default-off modalities on the owner's instruction);
  qualified the Status line to separate the family's T1/T2a *geometry* (done)
  from the T2a *oracle-agreement claim* (not answerable by Arm A as
  prompted); marked the "Explicitly not changed (YAGNI)" `yield_robot` bullet
  superseded. Implementation verified on `feat/failure-context-closed-loop`:
  plan `docs/superpowers/plans/2026-09-18-head-on-asymmetric-family.md`;
  hardware evidence `docs/reports/2026-09-18-head-on-family-validity.md`.
- Rev 4 (2026-09-26): added the two `_gshort` goal-short variants (each goal on
  the opposing spawn, so the parked blocker is off every goal path) behind a
  `--goal-mode` generator option; v1 files, manifest rows and oracle unchanged.
  See "Rev 4 (2026-09-26)" at the end of this document.

**Status:** The `head_on_asymmetric` family realizes the rev-8 battery cell T1
(`head_on_deadlock`-equivalent, both sides feasible) and T2a's **geometry**
("asymmetric retreat space: the correct yielder is not the FCFS pick") as one
parametric family instead of hand-authored instances — implemented and
verified against the frozen oracle by forced-yielder mock runs (all four
cells matched;
`docs/reports/2026-09-18-head-on-family-validity.md`, "Validity Pairs
(T2a)"). **T2a's oracle-agreement claim — whether the live VLM's yielder
choice agrees with the oracle for a reason connected to the scene — is not
answerable by Arm A as currently prompted**; see the design review below and
rev 8.6 of the parent spec. The two v1 T2a variants are instead reported as a
pre-registered order-vs-scene demonstration (Task 9's paired gpt-4o runs;
see the validity report). The RQ5/recovery value of the family is confirmed
by live evidence (both the 2026-09-18 `head_on_deadlock` precedent and the
2026-09-19 RQ5 recovery runs on `w0p2_eopen_o0`).

> **Resolved (2026-09-19) — was "open design review":**
> `2026-09-19-head-on-asymmetric-family-design-review.md` found the parked
> blocker was not present in any channel the reasoner read (obstacles absent
> from the M2 prompt, decision measured not to use the image) and that the
> "VLM lists the yielder first" channel was a constant in practice (`robot_1`
> first in 44/44 yields across 524 artifacts) — so, as written, the T2a
> contrast cell could not distinguish a reasoning failure from an
> observability failure. **Decision taken (owner, 2026-09-19): "do your
> recommendations"** — engineering proceeded rather than pausing on the
> review. Both channels the review identified as missing were built as
> declared, default-off modalities (module-2 FR2.1.9 `yield_robot`; FR2.1.8
> `prompt_static_obstacles`; rev-8.6) so both directions (modality off =
> today's information bound, on = the spatial-reasoning condition T2a was
> meant to be) stay comparable with every prior artifact. Task 9 then ran the
> blocked variant paired both ways and reports the result as an order-vs-scene
> demonstration, not a T2a oracle-agreement score — the RQ5/recovery value of
> the family is unaffected and now has live precedent both ways.

**Parent spec:** `2026-07-05-general-spatial-congestion-resolution-design.md`
(Scenario battery; Authored oracle blocks; Tuning-parity rule).

---

## Problem

Runs 1–6 used one scenario that a single yield resolves. RQ2/RQ3/RQ5 need
episodes where the obvious answer fails. The spec defines T2a but no instance
exists, and a single instance would not support a general claim or the
paired-seed matrix. Two engineering gaps stand in the way: timed obstacles are
authored as empty Xforms (no geometry, no collision, no lidar return), and the
scenario name is a closed `Literal`, so variants cannot be generated.

---

## Decision

### Asymmetry mechanism: a parked blocker at the aisle mouth

A static box (0.3 × 0.3 × 0.5 m, aisle-centred, static collider) is placed
on one side of the corridor, `blocker_<side>_m` metres behind that side's
spawn point. It occupies the yielder's straight backup lane and the derived
park point on that side, so a yield on that side cannot complete (M4 backup
blocked → FAILED / TIMED_OUT), while the passer's route to its goal beyond
the blocker stays open on either flank: the aisle is 1.2 m wide, so each
flank lane is 0.6 − 0.15 = 0.45 m ≥ 2 × 0.19 m (Nav2's inscribed radius,
applied from the box *and* from the rack wall). A 0.5 m box was rejected for
exactly that reason (0.35 m lane < 0.38 m). Goals stay at ±2.5 and remain
reachable (far face at |x| = 2.0 leaves 0.5 m) — the reason a sealing "cap"
was rejected: it would also block the other robot's goal. `null` = no
blocker (today's T1 side).

### Parameters (the family)

| Parameter | Meaning | Grid v1 |
|---|---|---|
| `blocker_west_m` | near-face distance behind robot_1's spawn point; `null` = none | `{0.2, null}` |
| `blocker_east_m` | same, behind robot_2's spawn point | `{0.2, null}` |
| `arrival_offset_m` | robot_2 spawns this much farther from the corridor than robot_1; recorded for future grids | `{0.0}` (fixed) |

Variant id `w<west>_e<east>_o<offset>` with `open` for `null` and floats
printed `:g`, e.g. `w0p2_eopen_o0`. Grid v1 = 3 variants:
`w0p2_eopen_o0` (T2a, contrast), `wopen_e0p2_o0` (T2a mirrored — FCFS
happens to be right; also exposes robot-id bias), `wopen_eopen_o0` (T1
control, geometrically identical to `head_on_deadlock`). The `w0p2_e0p2`
cell has no feasible yielder and is skipped by the generator (printed, not
written); no `--include-infeasible` flag in v1.

`arrival_offset_m > 0` is **not** realizable on a blocked side with this
geometry: a robot spawning 0.4 m farther back would sit inside any blocker
that covers the 1.79 m park point, and an offset on the open side makes the
FCFS pick coincide with the feasible yielder (no contrast). A future arrival
axis needs a different mechanism (spawn heading offset or a start delay);
the field stays in the schema so variant ids remain stable.

### Computed oracle (frozen into each yaml)

A side is **yield-feasible** iff the yielder can reach the derived park point
before the blocker. Room measured from the corridor mouth is
`0.5 + blocker_<side>_m` (spawn offset + blocker); required room is
`park_offset_m(geometry) − half_length_m + robot.half_width_m + 0.2`
(≈ 1.79 − 1.0 + 0.09 + 0.2 = 1.08 m with the current geometry). `null` is
feasible. v1: 0.7 m < 1.08 m → infeasible, and the park point (1.79) lies
inside the box ([1.7, 2.0]).

`fcfs_yielder` is what the rev-8 "FCFS + commitment tiebreak" control
answers: the later arriver yields; ties (Δ arrival < 1.0 s, equal
commitment) break lexicographically by `robot_id` → `robot_1`. With
`arrival_offset_m = 0` both robots arrive together, so `fcfs_yielder` is
`robot_1` in every v1 variant. `correct_yielder` is the feasible side's
robot, or `fcfs_yielder` when both sides are feasible. Written as:

```yaml
oracle:
  correct_yielder: robot_2
  fcfs_yielder: robot_1
  feasible_yielders: [robot_2]
  objective: min_total_time_to_goal
  rationale: "west blocker 0.20 m behind the spawn leaves 0.70 m from the mouth < 1.08 m required; robot_1 cannot park"
```

`contrasts_fcfs` (`correct_yielder != fcfs_yielder`) is derived, not
stored, and reported in the manifest. The oracle uses the same
`reasoning.rag.scene_geometry` functions M3 grounds with, loaded from M5's
`scenario_geometry` block in `swarm_orchestrator/config/orchestrator.yaml`,
so the pre-registered answer and the executed maneuver share one definition
(tuning-parity rule).

### Configuration model changes (`isaac/vgu_sim/config.py`)

- `name`: free identifier `^[a-z][a-z0-9_]*$` (legacy names still valid).
- `family: Literal["head_on", "intersection", "dynamic_anomaly"]` — inferred
  from the legacy names when absent (`head_on_deadlock → head_on`, …), so the
  three existing yamls change nothing. Ground-truth conflict dispatch and the
  `cmd_vel` watchdog key on `family`, not `name`.
- `ObstacleSize(x_m, y_m, z_m)` (all > 0; default 0.3 × 0.3 × 0.5),
  `StaticObstacleConfig(obstacle_id, pose: Pose2D, size: ObstacleSize)` and
  `static_obstacles: tuple[...] = ()`; obstacle ids unique across static and
  timed obstacles.
- `TimedObstacleConfig.size: ObstacleSize` (default) — fixes the empty-Xform
  bug for `dynamic_anomaly`.
- `parameters: HeadOnAsymmetricParams | None` (the three family parameters,
  recorded for analysis) and `oracle: OracleConfig | None` (fields above;
  robots must exist).

### Authoring (`isaac/vgu_sim/scenario_builder.py`, `validation.py`)

- `_author_box(stage, path, translate, yaw, size)` — collision cube helper
  (grey, `UsdPhysics.CollisionAPI`), used for static obstacles under
  `/World/Scenario/StaticObstacles/<id>` and for timed obstacles under
  `/World/DynamicObstacles/<id>` (Xform inactive until spawn, as today).
- `validation.py`: every configured static/timed obstacle prim exists.

### Nav2 map (`isaac/scripts/generate_warehouse_map.py`)

`--scenario` bakes `static_obstacles` footprints (`center, size.x, size.y`,
yaw ignored — axis-aligned in v1) in addition to the aisle barrier; timed
obstacles are never baked. Output `warehouse_map_<name>.{pgm,yaml}`.

### Generator (`isaac/scripts/generate_head_on_family.py`, local, no Isaac)

Writes `isaac/config/scenarios/family/head_on_asymmetric_<variant>.yaml`
(committed — frozen at `prereg-v1`) plus `family_manifest.csv` (variant,
parameters, oracle).

Placement, precisely: robots keep spawning 0.5 m outside their corridor mouth
(robot_1 at x = −1.5; robot_2 at `1.5 + arrival_offset_m`). `blocker_<side>_m`
is the blocker's **near-face distance behind that side's spawn point**, so
the box centre is at `|x| = 1.5 + blocker + 0.15` (west, v1: near face −1.70,
centre −1.85, far face −2.00). The passer's goal (−2.5) lies 0.5 m beyond
the far face and is reached around the box's flanks. The generator writes
this derivation as a comment into each yaml. Everything else (seed,
duration, corridor barrier, expected conflict, runtime) is copied from
`head_on_deadlock.yaml`, so `wopen_eopen_o0` differs from it only by name,
family, parameters and oracle.

### Runbook / M5 / M4

- The VM launch sequence becomes a repo-tracked script
  `scripts/vm/fc_launch.sh` (merging the ad-hoc `fc_check_launch.sh` /
  `fc_record_launch.sh` that live only on the VM) taking `SCENARIO=<name>`
  (default `head_on_deadlock`; family names resolve under
  `isaac/config/scenarios/family/`), `RECORD=0|1`, and reading each robot's
  spawn pose for the Nav2 launch from the scenario yaml instead of
  hard-coding ±1.5. Nav2 map `warehouse_map_<name>`; `VGU_RUN_ID` unchanged.
  M5 config unchanged (goals ±2.5, same corridor geometry); M3 needs nothing
  new — the blocked yield is *supposed* to fail.
- Authoring-time validity (spec rule): for each T2a variant, two mock-backend
  runs (`VGU_MOCK_DECISION_FILE`) forcing `involved_robots: [robot_1, robot_2]`
  vs `[robot_2, robot_1]` must show the oracle yielder's run reaching both
  goals and the other run's yield ending FAILED/TIMED_OUT. Recorded in the
  notes; a variant that fails this check is re-authored, not used.

---

## Explicitly not changed (YAGNI)

- ~~No new M2/M3 fields (`yield_robot` role fields remain Phase 1 Task 1); the
  VLM chooses the yielder by listing it first, which M3 already honours.~~
  **Superseded (Rev 3, 2026-09-19).** This claim is false as of the same
  branch: the design review measured that list position carries no choice
  (44/44 yields list `robot_1` first across 524 artifacts), and the owner's
  "do your recommendations" decision un-deferred exactly this field —
  `CongestionDecision.yield_robot` landed (module-2 FR2.1.9), scoped to
  `strategy == "yield"`, never required. See rev 8.6 of the parent spec and
  the Status line above.
- Intersection and dynamic-anomaly families beyond the `family` field and the
  obstacle-geometry fix.
- No motion table / stage-2 candidates.

---

## Testing

- Config: legacy yamls parse with inferred family; free-form name accepted,
  bad name rejected; static obstacle parse; timed obstacle size default;
  oracle robots validated; parameters round-trip.
- Oracle rule: feasible/infeasible boundary from `park_offset_m`; both
  feasible → FCFS; tie → `robot_1`; `contrasts_fcfs` derived.
- Generator: v1 grid produces 3 variants with the expected oracles; manifest
  rows; infeasible cell skipped.
- Map: static obstacle footprint occupied; timed obstacle not baked; passer
  flank stays free (cells at y = ±0.45 beside the box).
- Acceptance logging: `family == head_on` dispatch for a family variant.
- Builder/validation: pxr-dependent, host-only (like existing USD tests).

---

## Verification (VM)

1. `build_scenario` + `generate_warehouse_map` for all three variants; `wopen_eopen_o0` (T1 control) boots and both robots reach their goals under the mock backend.
2. Authoring-time validity pairs on both T2a variants (mock backend, both yielder orders), recorded.
3. One recorded gpt-4o run on `head_on_asymmetric_w0p2_eopen_o0`: expect yield(robot_1) → FAILED → previous-attempt block → yield with robot_2 first (or another feasible strategy) → both goals reached. Whatever the VLM does is the RQ5 evidence; record it either way.

---

## Files touched

`isaac/vgu_sim/config.py`, `scenario_builder.py`, `validation.py`,
`acceptance_logging.py`, `cmd_vel_watchdog_node.py` (family key),
`isaac/scripts/generate_warehouse_map.py`, new
`isaac/scripts/generate_head_on_family.py`, new `isaac/vgu_sim/family_oracle.py`,
`isaac/config/scenarios/family/*.yaml` + manifest,
`ros2_ws/src/swarm_simulation/maps/warehouse_map_head_on_asymmetric_*.{pgm,yaml}`,
`config/mock_decisions/head_on_yield_robot_2.json`, new
`scripts/vm/fc_launch.sh`, tests mirroring each; docs: module-6 spec
(scenario list, obstacle geometry), rev-8 spec (battery: family + rev 8.6
line), `docs/implementation_notes.md`.

---

## Rev 4 (2026-09-26): `_gshort` goal-short variants

**Problem.** The v1 goals are inherited from `head_on_deadlock`: ±2.5 on the
corridor axis. A blocker parked 0.2 m behind a spawn sits at |x| = 1.85 (near
face 1.70, far face 2.00), so the ±2.5 goal is **beyond** the box. Whichever
robot crosses to the blocked side must therefore thread the 0.20 m gap beside
the box on its own goal run. Five of twelve pilot episodes were lost exactly
there — wedged 0.004–0.064 m past the near face, or arrested 0.027–0.038 m
short of it (`docs/reports/2026-09-25-overnight-findings.md` §O, §U, §W item
6). That is a scenario artifact, not a coordination failure, and it truncates
the outcome measure the battery exists to produce.

**Decision.** Add two variants that keep the blocker and move only the goals:
each robot's goal becomes the **opposing robot's spawn** (robot_1 → (1.5, 0),
robot_2 → (−1.5, 0)). Goal paths then stop 0.20 m short of the box's near face
instead of passing it. Retreat room behind each spawn is untouched, so the
pre-registered oracle is unchanged.

- `head_on_asymmetric_w0p2_eopen_gshort_o0` — blocker west, correct yielder
  `robot_2`, contrasts FCFS, T2a.
- `head_on_asymmetric_wopen_e0p2_gshort_o0` — blocker east, correct yielder
  `robot_1`, T2a.

**Mechanism.** `--goal-mode {all,beyond,opponent_spawn}` on
`isaac/scripts/generate_head_on_family.py`. The goal mode is a **generator
option, not a `HeadOnAsymmetricParams` field**: `build_variant` dumps
`params` verbatim into the `parameters:` block, so a new field would add a
line to the three frozen v1 YAMLs and break their committed bytes. The mode is
recorded instead in the variant slug (`_gshort`, inserted between the blocker
and arrival-offset fields), in the per-file header comment, and in the
`prereg-v1-gshort` freeze tag. The v1 grid remains the generator default and
reproduces the committed v1 files byte-for-byte
(`test_write_family_default_goal_mode_reproduces_committed_v1_bytes`).

**Oracle invariance.** `compute_oracle` takes only `HeadOnAsymmetricParams` and
`SceneGeometry`; `required_room_m`, `room_from_mouth_m` and
`yield_retreat_room_m` carry no goal term at all (`yield_retreat_room_m` scans
`static_obstacles` between the corridor mouth and the retreat direction). The
`oracle`, `parameters`, `spawn` and `static_obstacles` blocks of each
`_gshort` file are therefore equal to those of its beyond-goal twin, asserted
in `test_build_variant_opponent_spawn_leaves_the_oracle_unchanged`.

**Maps.** `generate_warehouse_map.py` bakes perimeter walls, rack blocks,
`aisle_barrier` and `static_obstacles`; goals never reach the grid. The two
`_gshort` PGMs are byte-identical to their beyond-goal twins and the YAMLs
differ only in the `image:` filename. They are committed under their own stems
because `fc_launch.sh` resolves the map by scenario name
(`warehouse_map_${SCENARIO}.yaml`). `swarm_simulation/CMakeLists.txt:6`
installs the whole `maps` directory, so no glob change is needed.

**Consumer that must be changed per run (operator step).** M5's task registry
reads goals from `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
`initial_tasks`, **not** from the scenario YAML; `scripts/vm/fc_launch.sh`
parses only `spawn.{x,y,yaw_rad}` out of that YAML. Running a `_gshort`
scenario without editing `initial_tasks` to ±1.5 dispatches ±2.5 and the
variant silently degrades to its beyond-goal twin. This is the same
hand-mirrored pattern as `scenario_geometry` and `static_obstacles`; the
required values are now documented inline above `initial_tasks`.

**Known consequences of a goal inside the park offset.** With
`scenario_geometry` as configured, `park_offset_m` = 1.789 and
`pull_off_lateral_m` = 0.360, so the yielder parks at (±1.789, ±0.360) while
the passer now terminates at (±1.5, 0) — 0.461 m away, against M4's
`min_distance_m` 0.45 and M5's `proximity_threshold_m` 0.50. Three predicted
effects, all to be checked on the first VM runs:

1. A near-miss on the safety latch with ~0.011 m of margin. Under the ±2.5
   goals this approach was transient (the passer kept going); here it is the
   passer's terminal pose, held until the yielder resumes its own mission.
2. `congestion_detector._update_close_slow_pairs` ignores arrived status, so
   an arrived passer and a still-parked yielder inside 0.50 m for longer than
   `stall_threshold_sec` (12 s) would emit a spurious second episode.
3. M4's escort primitive drives the passer `|passer − park| + 0.65` m by raw
   `cmd_vel` (`command_bus_node.py:193`), i.e. past ±1.5 to roughly ±2.4;
   Nav2 then back-tracks it west to the goal. Harmless but visible in traces.

None of these blocks the variants; all three are properties of the ±1.5 goal
and must travel with any result measured on them. `arrived_radius_m` 0.5 now
spans [1.0, 2.0], abutting the corridor mouth at `half_length_m` = 1.0 (it
spanned [2.0, 3.0] before). Marker visibility is unaffected: 1.5 − 0.06 = 1.44
> `visibility_boundary_m` 1.329, so a marker parked at the goal clears the
occluder silhouette.

**Nav2: each goal cell is occupied by the other robot at t = 0.** The global
costmap runs `["static_layer", "obstacle_layer", "inflation_layer"]`
(`nav2_params.yaml:279`) with the lidar as its observation source, so at
dispatch robot_1's goal (1.5, 0) is inside robot_2's own footprint and vice
versa — under ±2.5 the goal cell was always empty space beyond the opponent.
`planner_server` sets no `tolerance`, so NavFn's 0.5 m default applies
(`nav2_params.yaml:167-186`): the first `ComputePathToPose` is expected to
clip ~0.5 m short rather than fail, which still sends each robot into the
corridor and forms the deadlock as designed. Once the yielder is parked at
(±1.789, ±0.360) its inflated footprint clears the goal by 0.348 m against the
global `inflation_radius: 0.10`, so the passer's final approach plans
normally. **Watch the first VM run's planner logs**: §(d) of the 2026-09-25
findings already records recurring planner errors here, and a `GoalOccupied`
at t = 0 would be the one way these variants fail to start.

**Consumers audited and found goal-agnostic.** `scripts/vm/fc_launch.sh:258-263`
(spawns only), `isaac/vgu_sim/acceptance_logging.py:46-47` (diagnostic
`distance_to_goal_m`), `isaac/vgu_sim/scenario_builder.py:91-95` (draws a goal
sphere), `isaac/scripts/run_simulation.py` and `validate_simulation.py` and
`isaac/vgu_sim/validation.py` (no goal reference at all),
`generate_warehouse_map.py` (no goal term).
