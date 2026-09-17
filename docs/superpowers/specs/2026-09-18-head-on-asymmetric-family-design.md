# Head-On Asymmetric Scenario Family — Design (T1/T2a battery)

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: parametric head-on family with parked blockers, computed oracle, static obstacles with real geometry; approved in chat (user, 2026-09-18).
- Rev 2 (2026-09-18): plan-time corrections — box 0.3 × 0.3 m (a 0.5 m box leaves no Nav2-legal flank lane), blocker 0.2 m, `arrival_offset_m` fixed at 0 in v1 (an offset on a blocked side is spatially impossible), `fcfs_yielder` defined by the rev-8 tiebreak rule, grid v1 = 3 variants, repo-tracked VM launch script.

**Status:** Approved for implementation. Realizes the rev-8 battery cells T1
(`head_on_deadlock`, both sides feasible) and T2a ("asymmetric retreat
space: the correct yielder is not the FCFS pick") as one parametric family
instead of hand-authored instances.

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

- No new M2/M3 fields (`yield_robot` role fields remain Phase 1 Task 1); the
  VLM chooses the yielder by listing it first, which M3 already honours.
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
