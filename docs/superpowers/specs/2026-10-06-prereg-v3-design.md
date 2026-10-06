# Prereg-v3 Design — Fixed Stack, Detour Judgment, Emergent Congestion

**Prepared:** 2026-10-06

**Revision history:**

- Rev 1 (2026-10-06): initial design, drafted on `feat/v3-design`
  while v1 collection and the v2 freeze are still pending. Sources:
  the v2 design's accumulated v3 registrations
  (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, every
  dated "v3" item), the parked costmap fix and its validation
  (`docs/reports/2026-10-05-costmap-fix-validation.md`), the
  verbatim pilot (`docs/reports/2026-10-06-verbatim-pilot.md`), the
  seven literature rounds (`reports/`), and the MAPD mini-cell
  registration (GECCO '25, 10.1145/3712256.3726339).

**Status:** DESIGN — nothing here is built for v3. The v3 freeze
happens only after v2 collection and analysis complete. This
document collects and sequences what is already proven, registered,
or ruled; it invents as little as possible.

---

## Discipline (inherited, with one addition)

1. v2 collection runs from the v2 freeze; v3 development happens on
   branches cut from the v2 freeze tag, merged to a v3 integration
   branch, never into a collecting tree.
2. Every scored criterion is registered before its collection;
   pilots are excluded from confirmatory counts.
3. NEW: **the fixed stack is v3's ground truth.** The A′+H
   costmap/localizer fix merges FIRST (step 0), before any v3
   scenario or oracle work, because it changes execution timing
   everywhere (measured: T3c post-removal stall −18.4 s, IB10 last
   arrival −55.5 s). Every v2-era frozen number consulted during v3
   design must be re-read against the step-0 re-baselines, never
   assumed.

---

## What v3 inherits already proven

- **The A′+H fix** (`feat/v3-costmap-fix` @ 0b2e755, parked,
  validated 2026-10-06): stamp-matched latency-compensated
  localizer + `clearing: true` / raytrace 3.5. All validations
  passed on the parked branch: rotation closures 12–13/17 → 0 ×2,
  declared reroute completes ×2, IB10 4/4 + yielder-last, free-flow
  spot checks within ±0.8 s, loop pre-emption conclusion survives.
- **`follow_waypoints` validated end to end** (M4 leg-progress
  logging merged in v2) — the reroute action is real on the fixed
  stack.
- **The v2 coordinator contract** in its final pre-freeze shape:
  prompt v3.3 grammar, verify/repair with χ-ε, provenance +
  `repaired_order_only` + `verbatim_dispatch_matched` +
  strategy-conditioned analysis, hold semantics, phased
  `junction_clear`, outcome classes, flow metrics, free_flow_v1.
- **Instruments**: capability battery v1 (ceiling, baselined) and
  v2 (dynamic; conflict_prediction separates backends), the visual
  apparatus flags, permutation voting with the debiased ballot/tie
  rules, the Layer-2-off arm (pilot 2026-10-06; outcome governs its
  place in collection).

---

## v3 work program

### Step 0 — merge the fix; re-baseline

Merge `feat/v3-costmap-fix`; re-run the re-baseline batch on the
merged tree (IB10 composite, loop pre-emption, T3c A/B, free-flow
spot checks); re-harvest `free_flow` ONLY for cells whose spot
checks drift beyond the registered ±1.5 s (table becomes
`free_flow_v2` if any entry changes; otherwise v1 carries with a
validity note). Update every cell's expected-timing notes (T3c,
IB10) from the measured shifts. The GT clock offset is fitted
per run from odometry everywhere (trap 18); the −0.45 s constant is
retired from docstrings.

### Step 1 — detour-judgment family revival (GO/NO-GO)

The v2 deferral had three prerequisites; two are now met
(clean-costmap loop explained AND fixed; follow_waypoints
validated). The third — a planner-visible stall that does not
self-detour — may no longer be needed: the original stall-vs-plan
window analysis (NavFn flips between 0.30 and 0.22 m gaps vs the
0.24 m stop box) was measured on the UNFIXED stack, where phantom
marks inflated corridor cost. **Step 1 re-derives the NavFn sweep
and the live window on the fixed stack.** GO: a gap value exists
where the robot stalls (collision monitor) while the planner still
plans through — the family revives as registered in v2 (visual
persistence cells, forced-arm cost tables). NO-GO: design the
planner-invisible stall (last resort, must not require contact) or
keep the family classification-only (the persistence-judgment
probe cell from the v2 registrations).

### Step 2 — axis-choice freedom at the junction

Derive the E–W mirrored composite (pockets, clearances, stagger on
the x-band, which is wider than y): both axes become modeled,
executable resolutions; the verifier accepts either; the recede-set
audit scores CHOICE, not convention. This converts ER-2's unstable
recede set (three different sets in three live episodes) from a
repair statistic into a measured spatial decision — and under
`prompt_robot_order: random` (ruled for IB10) the choice is
unconfounded. Oracle: either axis correct unless the scene is made
asymmetric (an asymmetric-junction variant — one axis cheaper — is
the natural scored cell: does the model pick the cheaper axis?).

### Step 3 — emergent congestion: MAPD mini-cell × multi-conflict

Fused build (one scenario family serves both registrations):
- M5 task-sequence queues (multi-goal registry, pop-on-arrival).
- Task-node props; the existing warehouse map at N=5.
- Congestion emerges from task streams; simultaneous conflicts
  occur naturally — the coordinator's scene-wide plan and
  supersession machinery finally get exercised as designed.
- Measures: makespan, aperture/task throughput, completeness,
  delay_vs_free_flow, interventions per episode, plan metrics —
  directly comparable to the GECCO '25 prediction-avoidance
  results; the Layer-2-off arm is the shared control.
- Open M4 question to decide at build: whether pending-leg-only
  supersession suffices under task streams, or in-flight
  cancellation (registered out of v2) must finally be built.

### Step 4 — plan-channel apparatus, second generation

- **Marked-candidate plan composition** (no prior art; claimable):
  render per-robot candidate maneuvers as lettered marks; the VLM
  composes the plan from marks. Fallback published pattern:
  per-leg selection from the verifier's candidate sets (the
  candidate-options flag, already built, becomes the text-channel
  arm of this A/B).
- **Battery v2.1**: temporal_order rebuilt (M1-agreement filter,
  id-prior counterbalance, tighter event spacing, per-run GT
  offset), arrow-suppressed motion_direction variant (M1 overlay
  flag), multi-image probe path enabling the 2–3-keyframe arm of
  the registered three-way frame A/B.

### Step 5 — boundary pilots

- **Scale probe**: classification/triage at N=8–10 (one scene), and
  the MAPD cell at N=10 (their middle config) — converting the ≤5
  scope bound into a measured regime boundary.
- **Model breadth**: the verbatim-pilot matrix (or its head-on/IB10
  core) on a third backend through the existing anthropic adapter
  (key/funding = owner decision).
- **Physical-camera episode** (standing owner option; upgrades
  claim-1 wording).

### Step 6 — v3 freeze

Same procedure as v1/v2: pins, hashes, veto list, probe results,
reading-gate check (GenePlan skim still optional-open; re-run the
concurrent-work scan — GAVEL/PAAI/SyncPlan will no longer be
"months old", so the related-work framing shifts from concurrent to
prior, which the claims already tolerate by their wording).

Decision points deliberately left to the owner at freeze time: B1
junction fields (groundable vs tag-only), second-level recovery
beyond `fallback_exhausted`, the DWB corner-wedge shared issue
(chase or document), lifting the loop family's do-not-collect, and
the frozen-file touchups now permitted post-v2 (the stale t2b
`--duration-sec` header, convoy free-flow aliases via the
generator).

---

## What v3 does NOT attempt (carried exclusions)

Crowding (dropped by user decision, token retained); swarm-scale
flow shaping (positioned against, not attempted); decentralized
variants; shared-Nav2-param tuning beyond the ruled H change; the
robot-blocker anomaly and token-scale crowding scenes (still
unregistered); real-time guarantees.

---

## References

Everything dated: the v2 design spec (authoritative for inherited
rulings), `docs/reports/2026-10-05-costmap-fix-validation.md`,
`2026-10-05-costmap-source-probe.md`,
`2026-10-06-verbatim-pilot.md`, `2026-10-05-flow-metrics.md`,
`2026-10-05-free-flow-table.md`, the seven literature reports under
`reports/`, and the prereg-v1 amendments lineage.
