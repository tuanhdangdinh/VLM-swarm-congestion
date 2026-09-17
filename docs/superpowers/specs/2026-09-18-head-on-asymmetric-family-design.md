# Head-On Asymmetric Scenario Family — Design (T1/T2a battery)

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: parametric head-on family with parked blockers, computed oracle, static obstacles with real geometry; approved in chat (user, 2026-09-18).

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

A static box (default 0.5 × 0.5 × 0.5 m, aisle-centred) is placed on a side
of the corridor at `blocker_<side>_m` metres from the corridor mouth
(`|x| = half_length_m + blocker_<side>_m + 0.25`). It occupies the yielder's
straight backup lane and the derived park point on that side, so a yield on
that side cannot complete (M4 backup blocked → FAILED / TIMED_OUT), while the
passer's route to its goal beyond the blocker stays open on either flank
(1.2 m aisle − 0.5 m box = 0.35 m free per side ≥ inflated half-width 0.19 m,
baked into the Nav2 map). Goals stay at ±2.5 and remain reachable — the
reason a sealing "cap" was rejected: it would also block the other robot's
goal. `null` = no blocker (today's T1 side).

### Parameters (the family)

| Parameter | Meaning | Grid v1 |
|---|---|---|
| `blocker_west_m` | blocker near face distance from the west mouth; `null` = none | `{0.3, null}` |
| `blocker_east_m` | same, east side | `{0.3, null}` |
| `arrival_offset_m` | robot_2 spawns this much farther from the corridor than robot_1 (`1.5 + offset`), so robot_1 arrives first when > 0 | `{0.0, 0.4}` |

Variant id `w<west>_e<east>_o<offset>` with `open` for `null`, e.g.
`w0.3_eopen_o0.4`. Grid v1 = 3 feasible room combinations × 2 offsets = 6
variants; `w0.3_e0.3` (no feasible yielder) is generated only if
`--include-infeasible` (T0-style negative cell), default excluded.

### Computed oracle (frozen into each yaml)

A side is **yield-feasible** iff the yielder can reach the derived park point
before the blocker: `blocker_<side>_m ≥ park_offset_m(geometry) −
half_length_m + robot.half_width_m + 0.2` (≈ 0.79 + 0.09 + 0.2 = 1.08 m
with the current geometry; `null` is feasible). Written as:

```yaml
oracle:
  correct_yielder: robot_2          # the feasible side's robot; FCFS pick (first arriver) when both are feasible
  fcfs_yielder: robot_1             # who arrives first (from arrival_offset_m; robot_1 when 0)
  feasible_yielders: [robot_2]
  objective: min_total_time_to_goal
  rationale: "west blocker 0.30 m from the mouth < 1.08 m required; robot_1 cannot park"
```

The oracle uses the same `reasoning.rag.scene_geometry` functions M3 grounds
with, so the pre-registered answer and the executed maneuver share one
definition (tuning-parity rule).

### Configuration model changes (`isaac/vgu_sim/config.py`)

- `name`: free identifier `^[a-z][a-z0-9_]*$` (legacy names still valid).
- `family: Literal["head_on", "intersection", "dynamic_anomaly"]` — inferred
  from the legacy names when absent (`head_on_deadlock → head_on`, …), so the
  three existing yamls change nothing. Ground-truth conflict dispatch and the
  `cmd_vel` watchdog key on `family`, not `name`.
- `StaticObstacleConfig(obstacle_id, pose: Pose2D, size: ObstacleSize)` and
  `static_obstacles: tuple[...] = ()`.
- `TimedObstacleConfig.size: ObstacleSize` (default 0.3 × 0.3 × 0.5) — fixes
  the empty-Xform bug for `dynamic_anomaly`.
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
the box centre is at `|x| = 1.5 + blocker + 0.25` (west, v1: near face −1.80,
centre −2.05, far face −2.30). The retreat room measured from the mouth is
therefore `0.5 + blocker` (v1: 0.8 m), which the oracle rule compares with
the 1.08 m the derived park point needs — infeasible, as intended: the park
point (−1.79) sits inside the box. The passer's goal (−2.5) lies beyond the
far face and is reached around the box's flanks. The generator writes this
derivation as a comment into each yaml.

### Runbook / M5 / M4

- Launch scripts take `SCENARIO=<name>`; Nav2 map `warehouse_map_<name>`;
  `VGU_RUN_ID` unchanged. M5 config unchanged (goals ±2.5, same corridor
  geometry); M3 needs nothing new — the blocked yield is *supposed* to fail.
- Authoring-time validity (spec rule): for the T2a variants, two mock-backend
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
  feasible → FCFS; `arrival_offset_m` → `fcfs_yielder`.
- Generator: v1 grid produces 6 variants with the expected oracles; manifest
  rows; infeasible cell excluded by default.
- Map: static obstacle footprint occupied; timed obstacle not baked; passer
  flank stays free (cells at y = ±0.45 beside the box).
- Acceptance logging: `family == head_on` dispatch for a family variant.
- Builder/validation: pxr-dependent, host-only (like existing USD tests).

---

## Verification (VM)

1. `build_scenario` + `generate_warehouse_map` for `head_on_asymmetric_w0.3_eopen_o0.4` (T2a) and `wopen_eopen_o0.0` (T1 control).
2. Authoring-time validity pair on the T2a variant (mock backend, both yielder orders), recorded.
3. One recorded gpt-4o run on the T2a variant: expect yield(robot_1) → FAILED → previous-attempt block → yield with robot_2 first (or another feasible strategy) → both goals reached. Whatever the VLM does is the RQ5 evidence; record it either way.

---

## Files touched

`isaac/vgu_sim/config.py`, `scenario_builder.py`, `validation.py`,
`acceptance_logging.py`, `cmd_vel_watchdog_node.py` (family key),
`isaac/scripts/generate_warehouse_map.py`, new
`isaac/scripts/generate_head_on_family.py`, new `isaac/vgu_sim/family_oracle.py`,
`isaac/config/scenarios/family/*.yaml` + manifest, `config/mock_decisions/head_on_yield_robot_2.json`,
launch scripts (`SCENARIO`), tests mirroring each; docs: module-6 spec
(scenario list, obstacle geometry), rev-8 spec (battery: family + rev 8.6
line), `docs/implementation_notes.md`.
