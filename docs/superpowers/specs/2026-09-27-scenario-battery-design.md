# Scenario Battery Build-Out — T0, T2b, T3 Design and Work Breakdown

**Prepared:** 2026-09-27

**Revision history:**

- Initial draft: design and dependency map for the unbuilt tiers of the
  rev-8 scenario battery (T0 negative controls, T2b flow-ordering, T3a/b/c
  semantics tiers), the prompt-v2 contract bundle, and the build order.

---

## Purpose

The run matrix (research design rev 8.6, "Scenario battery" and "Run
matrix") requires five tiers. T1 exists (`head_on_deadlock`,
`intersection_bottleneck`), T2a is the validated `_bshort` family
(amendments A1). T0, T2b and T3a/b/c have no scenarios, no oracles and —
for T0 and T3b — missing apparatus. This document designs them, maps
their dependencies, and fixes the build order. It is a design document:
each section ends with acceptance criteria, and implementation happens
per section, not from this document as a whole.

---

## The Prompt-v2 Bundle (build first — everything downstream emits into it)

Three pending changes each alter every prompt or the output schema; they
must land **together, once, before the freeze**, so pilots are
re-baselined a single time:

1. **`blocker_kind` output field** (`CongestionDecision`, optional
   `Literal["object", "transient", "robot"] | None`): required by T3a —
   the tier scores the VLM's blocker verdict against the classical arm's
   forced `object`. Prompt schema gains the field with a one-line
   instruction; absent in the answer stays valid (None).
2. **`crossing_order` output field** (optional `list[str] | None`):
   required by T2b's ordered crossing at three robots, and closes
   amendments item 10 (Arm B's `passing_order` becomes comparable).
   Non-permutation answers degrade per the measurement plan's
   `non_permutation_order` cause.
3. **Goals in the state block** (amendments item 13): `RobotView` gains
   the registry goal so `build_reasoner_request` stops sending
   `goal=None`. Recommendation: **include it** — Arm B's rules read
   goals, T2b's flow-ordering is undecidable without knowing where
   robots are headed, and bundling costs no extra comparability break.
   *Requires user sign-off; the bundle can ship without it.*
   *Status 2026-09-27 (later): adopted — the user continued twice past
   the explicit flag without objection. The revert remains isolated and
   available until the calibration pilot collects data under v2.*

**Bundle riders (2026-09-27):** two cosmetic prompt defects fix in the
same break — the task label never renders in the state block, and the
prompt header says "sorted by ID" regardless of the drawn order.

**Consequences.** All pre-bundle decision artifacts remain valid (fields
are additive-optional; old prompts reconstruct byte-identically). All
post-bundle prompts differ from every pilot; nothing straddling the
bundle may be pooled. After landing: a calibration mini-pilot (n = 3 per
model on `_bshort` west) to confirm no behavioral cliff, then the prompt
template hashes freeze at `prereg-v1`.

**Acceptance:** contract + prompt-builder changes with SHA pins for the
new rendering; parser accepts/degrades the new fields per the degradation
taxonomy; shadow comparator extends `DisagreementRecord` with
`blocker_kind_match` and `order_match`; calibration pilot clean.

---

## T0 — Negative Controls (in progress, separate task)

Normal-flow scenario (two robots, parallel non-conflicting lanes) plus an
M5 log-only probe mode: off-trigger stage-1 analyses on a timer,
artifacts marked `probe: true`, a structural and a defensive no-dispatch
layer, default off and byte-identical when off. Criterion: FP rate
≤ 10% on 20 probes. Being built now; live verification on the VM joins
the next deployment batch.

---

## T2b — Symmetric Standoff, Asymmetric Downstream Traffic

**Requirement.** Geometry-ambiguous ordering: a symmetric head-on
standoff both of whose retreats are feasible, where the *correct* yield
order is determined by flow — traffic behind one side — visible in the
motion table and trails. Oracle: `correct_order` +
`objective: min_total_time_to_goal`, validity verified at authoring time
by scripted executions of both orders, oracle order dominating by ≥ 20%
total delay, else re-authored. N = 15 pairs.

**Design.** Three robots. `robot_1` (west spawn) and `robot_2` (east
spawn) meet head-on at the corridor centre on the symmetric open variant
(`wopen_eopen` geometry — both retreats feasible). `robot_3` spawns
behind `robot_1` (west), same lane, goal east — downstream traffic on
the west side. If `robot_1` yields (parks off-corridor), `robot_3` is
blocked behind the parked yielder and total delay grows; the oracle
order is therefore `[robot_1, robot_3]` crossing first with `robot_2`
yielding once — the side with traffic passes first. FCFS picks by
arrival stamp and is indifferent to `robot_3`; that is the contrast the
tier exists for.

**Dependencies to verify before authoring (each a hard gate):**

- **Three-robot support end-to-end**: scenario schema (robots list is
  generic), ArUco marker 3 asset (`generate_aruco_markers.py`), a third
  Nav2 namespace in the launch path, M4 per-robot client fan-out, M5
  registry with three tasks, and the family generator's two-robot
  assertions (T2b gets its own generator function or hand-authored
  YAMLs — do NOT loosen `_blocked_short_goals`'s two-robot checks).
- **`crossing_order` in the contract** (prompt-v2 bundle) — without it
  the VLM cannot express the answer and only the yielder is scorable.
- **The authoring-time verification harness**: a scripted-execution mode
  that forces each order (the forced-yielder mock machinery from the
  2026-09-19 validity runs extends to a forced-order sequence) and
  measures total time-to-goal from ground truth over both orders,
  n ≥ 2 seeds per order. This harness is itself new code on the VM
  driver side.

**Open questions (resolve during implementation, record in the YAML
header):** `robot_3` spawn distance (far enough to not join the standoff
pair — outside `r_conflict` of both at trigger time, so the classical
classifier still sees a two-robot head-on; close enough that its delay
dominates the oracle margin); whether M5's congestion gate needs
`robot_3` excluded from the involved set or tolerates a three-robot
episode (episode rule A7 says disjoint-set opening — verify).

**Acceptance:** committed scenario YAML(s) with frozen oracle block; the
both-orders verification run recorded in a report with the ≥ 20% margin;
three-robot smoke run completing on the VM.

---

## T3a — Blocker-Kind Counterfactual Pairs

**Requirement.** Near-identical geometry; static object vs transient
agent as the blocker; divergent correct responses (`reroute` vs
`temporary_wait`). Classical `blocker_kind` is forced `object`
(non-divergence by construction). N = 15 pairs + 10 Arm-B-executed.

**Design.** A `blocked_path` scene: one robot transiting its lane meets
a blocker sitting on the path (no head-on partner in `r_block`). Pair
members:

- **T3a-object**: a static box (`static_obstacles`, as the family
  blockers) — correct answer `reroute`, `blocker_kind: object`.
- **T3a-transient**: the *same pose* occupied by a robot-shaped asset
  **without an ArUco marker** (untracked by M1, so it exists in the
  image and in no text channel — the vision-load-bearing construction),
  despawned by the existing `timed_obstacles` machinery after a window
  longer than `temporary_wait`'s hold but shorter than the episode.
  Correct answer `temporary_wait`, `blocker_kind: transient`.

The second robot of the swarm runs a distant, non-conflicting lane so
the M4 pair machinery and M1 tracking stay in their normal regime.

**Dependencies:** `blocker_kind` output field (prompt-v2); a marker-less
robot visual asset in `isaac/` (the robot USD minus the marker — verify
the ArUco-under-physics-hierarchy constraint has a clean "no marker"
variant, cf. the marker-placement gotcha); `timed_obstacles` supporting
a despawn of an arbitrary asset (today it schedules boxes — check
`dynamic_anomaly.yaml`'s schema and extend minimally if it is box-only).

**Open question:** whether M1's phantom-marker robustness item interacts
(an unmarked robot must produce zero M1 detections — verify against the
`robot_17` misread finding; an unmarked robot has no quad, so risk is
low, but confirm in the smoke run).

**Acceptance:** the pair's YAMLs byte-identical except the blocker
entity and the oracle block; smoke run per member on the VM showing the
untracked entity in the frame and absent from `SceneState`.

---

## T3b — Obstacle-in-Candidate (build LAST; largest dependency chain)

**Requirement.** An untracked visual obstacle inside the geometry-max
retreat candidate; k = 3 candidates; the classical stage-2 answer
(geometry-max) picks the occupied candidate, the VLM should avoid it.
Binomial vs chance 1/3, ≥ 9/15.

**Dependency reality:** this tier needs the stage-2 retreat-candidate
machinery — Pillar 2 of the Phase 1 plan (Tasks 3, 8, 9, 11:
retreat-choice contract, `GroundingParams` derived mode, candidate
generation/validation/ranking, grounder wiring) — which is **unbuilt**.
The M3 grounder today computes one park point internally; there is no
candidate set for an obstacle to sit inside, no stage-2 VLM call, and no
`retreat_choice` parsing. Building Pillar 2 is a Phase-1-plan slice of
the same shape as the Arm B slice (offline, TDD, the plan's task specs
are written) plus an M5 wiring pass.

**Decision recorded here:** T3b is sequenced after T0/T2b/T3a/T3c, and
`prereg-v1` **may freeze without T3b collected** only by explicit
amendment (it carries T3's superiority claim together with T3a — losing
it weakens RQ4; the default plan is to build Pillar 2, not to descope).

**Acceptance (for the Pillar 2 slice):** the plan's Task 3/8/9/11 tests
green, `ranked[0]` equal to the shadow stage-2 answer by construction,
M5 emitting stage-2 artifacts. Scenario authoring follows.

---

## T3c — Timed-Obstacle Runs (re-scoped 2026-09-27: re-author, not reuse)

The smoke run (findings Rev 15 §AS) found `dynamic_anomaly.yaml`
unusable as authored: timed obstacles never spawn (`EventScheduler`
constructed with no-op callbacks — runner fix in progress), the robots
live at the camera-ROI edge where M1 never detects them, there is no
per-scenario Nav2 map, the YAML's four robots exceed the two Nav2
stacks, the obstacle window closes before M5 is up, and the layout is a
head-on by construction. **T3c v2**: two robots on tracked lanes inside
the ROI, a per-scenario map, an off-axis timed obstacle whose window
opens after M5 startup (≳ 60 sim-s) and spans a robot's approach, and an
`oracle:` block (`anomaly`/`transient` semantics once the prompt-v2
field exists). Gates: the scheduler-wiring fix verified live, then
authoring. Size: M (was S).

---

## Build Order and Effort Map

| # | Item | Depends on | Size | Status |
|---|---|---|---|---|
| 1 | T0 scenario + probe mode | — | M | **landed** (`33232b8`…`ff96ead`; VM/USD verification pending) |
| 2 | Prompt-v2 bundle (fields + goals decision) | user sign-off on goals | M | **landed** (`991ffae`…`ed152c7`; v1 frozen, integrity 130/130 + 654/654; goals on recommended default, confirmation pending; calibration pilot pending funding) |
| 3 | T3c v2 re-author (see re-scoped section) | scheduler fix live-verified ✓ | M | **authored + mechanically smoked** (`89884a3`); reasoning half + oracle pending funding and prompt-v2 |
| 4 | T3a pair (assets + YAMLs + oracle) | 2 ✓; 15b ✓ | M | **built + mock-smoked, both members PASS** (`ad379f1`…`71f6fdd`); decision-scored per amendments 17a (no outcome contrast in this apparatus); funded VLM run pending |
| 5 | T2b (3-robot + harness + oracle) | 2 ✓; feasibility report (`docs/reports/2026-09-27-three-robot-feasibility.md`) | XL + NEEDS-DECISION | investigation done: 12-item build list; safety items 9+11 (pair-scoped exemption, hold-until-last) REQUIRED before any wrong-order run — the both-orders harness otherwise collides or re-deadlocks; scope decision pending |
| 6 | Pillar 2 slice + M5 wiring + derived flip | — | L | **complete** (`d3c2a7d`; wiring `e358229`, flip `1648dd2`; stage-2 prompt v1 pinned; VM deploy pending) |
| 7 | T3b scenario | 6 ✓; asset ✓; wider band (test-proven); **NEW: set-of-mark letter drawing + letter counterbalancing (amendments items 21–22)** | M+M | blocked on 21–22 |

Items 3 and 6 are parallel-safe with everything; 4 and 5 gate on the
bundle so their oracles freeze against the final contract. Every tier's
first VM run doubles as the deployment carrier for whatever code landed
since the previous batch (current gap: `1a38379`).

---

## References

- Research design: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (rev 8.6)
- Amendments: `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` (Rev 7)
- Phase 1 plan (Pillar 2 task specs): `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`
- Family generator and validity method: `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
