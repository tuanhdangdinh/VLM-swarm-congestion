# Prereg-v3 Design — Fixed Stack, Detour Judgment, Emergent Congestion

**Prepared:** 2026-10-06

**Revision history:**

- Rev 2 (2026-10-06): full revision after independent advisor review
  (2 blockers, 6 majors, 17 minors — all addressed). Material
  corrections: Step 1's premise was WRONG (the 0.22/0.30 m NavFn
  flip is a baked-map inflation result, fix-invariant; NO-GO is now
  the expected branch and the live sim-54.8 discrepancy is restored
  to UNEXPLAINED status); Step 0 re-harvests the full free-flow
  table and adds outcome checks per scored family; the Layer-2-off
  pilot is registered-and-in-flight, not proven; Step 2 names the
  binding N-S yield-band constraint and extends χ-ε to axis sets;
  Step 3 states its build risks; v2-freeze-scope items are struck
  from the v3 freeze list. A correction to the v2 decision record's
  fold-in (which inherited the Step-1 error) is owed on
  `fix/deadlock-collision-resolution` — flagged to the session that
  owns that branch.
- Rev 1 (2026-10-06): initial design (superseded; its Step-1 premise
  was incorrect).

**Status:** DESIGN — nothing here is built for v3. The v3 freeze
happens only after v2 collection and analysis complete.

**SCENE DESIGN ATTACHED (2026-10-06):**
`docs/superpowers/specs/2026-10-06-v3-scene-design.md` (S1–S6,
code-derived geometry, migration table, 9-item build list) is the
detail layer under Steps 1–5. Coordinator rulings on its
escalations:
- **S1 density framing (material):** the literal Ghofrani analog is
  INFEASIBLE — our tracked band is ~51% racks, giving 5.4 free
  0.55 m cells/agent at N=5 vs their 40.5, i.e. OUR N=5 floor sits
  at their N≈37 density, beyond their N=25 regime where 76–91% of
  runs failed. S1 is therefore registered as "their structure, our
  (much harsher) density regime" — a documented deviation and an
  expectation-setter (low completion is a finding, not a failure),
  never presented as matched density.
- **MAPD-10 rung STRUCK from Step 5** (density worsens with N); the
  scale rungs are S5's convergence geometry at N=8 AND N=10 (the
  derived layout admits both), classification/triage-only.
- **S3/S2 ε for axis sets:** adopt the per-episode equivalence rule
  (judged at the dispatched snapshot, out-of-ε stratum reported);
  ε_set sizing deferred to Step 0's fixed-stack jam corpus — note
  the trade-off recorded in the scene doc (ε_set≈0.28 cleans S3 but
  un-guarantees S2's floor at its weakest jams).
- **New build items absorbed into the Step-6 gate list:** the
  dispatch-off probe flag (t0_probe_mode does NOT suppress
  dispatch — scene-doc correction), the parked-robot exclusion in
  mirrored grounding, dynamic per-snapshot `arms` + node-handoff
  grounding (S1's largest prerequisite), and marker 5–10 rendering
  verification (never rendered to date).
- S1 remains the first item to slip under schedule pressure, per
  both documents.

**Reference pinning:** the cited reports live on specific branches,
not the spec lineage: `docs/reports/2026-10-05-costmap-fix-validation.md`
at `feat/v3-costmap-fix@0b2e755`; the source-probe, verbatim-pilot,
flow-metrics, free-flow-table, loop-family and waypoints reports at
`feat/prereg-v2-composite@b5cafe4`. The literature reviews are the
SIX untracked files under `reports/` in the main checkout.

---

## Discipline (inherited, with one addition)

1. v2 collection runs from the v2 freeze; v3 development happens on
   branches cut from the v2 freeze tag. The parked fix's code
   commits are CHERRY-PICKED onto the v3 integration branch (the
   fix branch predates the freeze, cut at a8fc1bc); its 12 tests
   are re-run after the pick.
2. Every scored criterion is registered before its collection;
   pilots are excluded from confirmatory counts.
3. **The fixed stack is v3's ground truth, and its effects are not
   assumed to be timing-only.** A′+H merges first (Step 0). The
   measured shifts are from TWO cells only (T3c: the 17.0 s
   post-removal stall vanishes, arrival after removal −18.4 s;
   IB10: last arrival −55.5 s, 183.9→128.4). The source-probe
   blast-radius table names every multi-robot and transient-blocker
   scene as possibly mark-persistence-dependent, so Step 0 checks
   OUTCOMES, not just timing, across the scored families.

---

## What v3 inherits

**Proven (runs dated 2026-10-05, ruling 2026-10-06):**
- **The A′+H fix** (`feat/v3-costmap-fix@0b2e755`, parked):
  stamp-matched localizer lookup (`odom_lookup_mode=stamped`,
  `m1_latency_compensation_sec` 0.01) + `clearing: true` /
  raytrace 3.5. Validations on the parked branch: rotation closures
  12–13/17 → 0 ×2; declared reroute completes ×2; IB10 4/4 with
  yielder-last; free-flow spot checks Δ 0.0 / −0.8 / +0.1 s; the
  loop pre-emption conclusion survives.
- **`follow_waypoints`** validated end to end ON THE FIX BRANCH
  (M4's log-only leg-progress lines are merged in v2); prerequisite
  status must be re-confirmed on the MERGED v3 tree in Step 0.
- **The v2 coordinator contract as frozen at the prereg-v2 tag**:
  prompt v3.3 grammar, verify/repair with χ-ε (order), provenance +
  `repaired_order_only` + `verbatim_dispatch_matched` +
  strategy-conditioned analysis, hold semantics, phased
  `junction_clear`, outcome classes, flow metrics, `free_flow_v1`.
- **Instruments**: capability batteries v1 (at ceiling) and v2
  (conflict_prediction separates backends), the visual apparatus
  flags, permutation voting with the debiased ballot/tie rules.

**Registered, NOT yet proven:**
- **The Layer-2-off arm** — registration only at the time of this
  revision; its pilot's handback is held by the session owning
  collection coordination. Whatever its v2-tree outcome, it is
  re-run on the merged v3 tree in Step 0 before serving as any v3
  control: removing persistent lidar marks changes the reactive
  layer itself, so a pre-fix latch/clog result does not transfer.

---

## v3 work program

### Step 0 — merge the fix; re-baseline with outcome checks

1. Cherry-pick the fix's code commits onto the v3 integration
   branch (Discipline 1); re-run its 12 tests.
2. Re-run on the merged tree: the rotation probe (expect 0
   closures), `wp_fwd` ×2 (follow_waypoints prerequisite
   re-confirmed), the IB10 composite, the loop pre-emption smoke,
   and ONE mock run per v2-scored family (head-on, T2b, B1,
   B2-visual, B3, T3a transient) recording OUTCOME CLASS as well as
   timing — the blast-radius table says transient-blocker and
   multi-robot scenes may change behavior, not just speed.
3. T3c A/B method: A′ toggles via `odom_lookup_mode`; H has no
   toggle, so the pre-fix arm is a separate deployment of the
   pre-merge tree, not a config flip. State per-arm trees in the
   report.
4. **Re-harvest the ENTIRE free-flow table as `free_flow_v2`**
   (~2 h VM, zero API): the v1 spot checks covered 3 of 22 entries,
   the turning route moved the most (−0.8 s, consistent with A′/H
   acting on rotation-heavy paths), five cells had no check at all,
   and a carried table would mix pre/post-fix provenance. The same
   generator pass adds the deferred `blocked_path_*` variants and
   the ruled `convoy_counterflow` aliases.
5. Re-run the Layer-2-off arm on the merged tree (see Inherits).
6. Re-check the DWB corner wedge: the probe named the local
   costmap's `clearing: false` as a candidate cause and H clears
   it — this may dissolve in Step 0 rather than remain an owner
   decision.
7. The GT clock offset is fitted per run from odometry everywhere
   (fix-validation report Part 0: 0.300 s single-robot, 0.500 s
   four-robot; NOT a constant); the −0.45 s docstring constant is
   retired.

### Step 1 — detour-judgment family: NO-GO expected; one mystery owed

Correcting rev 1: the 0.22/0.30 m NavFn flip is a STATIC-MAP
inflation-cost result (standalone sweep on baked maps — no
localizer, no lidar, no persistence; loop-family report §Mechanism)
and is therefore FIX-INVARIANT. A live GO window could exist only in
(flip point, 0.24 m stop threshold) — at most ~0.02 m, below the
0.05 m costmap cell. Prerequisite status: ONE of three is met
(follow_waypoints, pending Step-0 re-confirmation). The
"clean-costmap loop" (sim 54.8 in `perm_reroute_s42`: zero lethal
marks, zero-cost pinch centre, live planner loops while standalone
NavFn plans direct) remains UNEXPLAINED — phantom marks were a
candidate, never confirmed, and act in the wrong direction (they
closed the SECOND aisle, making the loop costlier); the unchased
lead is the live-vs-standalone wall-cost discrepancy (99 vs 80 at
y = ±0.525), which H does not remove.

- **Step 1a (offline, no VM):** refine the baked-map sweep across
  0.22–0.30 m at costmap resolution; also quantify option (a) —
  LENGTHENING the detour — which moves the flip point directly
  (cost-relative mechanism) and has band headroom: the y-extent
  report tracked |y| = 1.8 stationary clean and reached 2.0 in one
  run.
- **Step 1b (fixed stack, one probe run):** re-run the live
  `ComputePathToPose` probe on the clean pinch — settle the
  sim-54.8 discrepancy on the merged tree.
- **GO** (a ≥1-cell window exists, live and standalone agreeing):
  the family revives as registered in v2.
- **NO-GO (expected):** the fix-independent blockers also stand (a
  tracked faulted robot latches permanently, 0.45 m latch vs 0.38 m
  stop range; detour length is band-capped unless option (a)'s
  headroom suffices). Fall back to a **classification-only
  persistence-judgment cell** — NEW in this document, not a v2
  registration: same scenes, the scored question is the visual
  transient-vs-permanent call, no detour execution needed.

### Step 2 — axis-choice freedom at the junction

Mirroring the recede is the easy half (|x| ≈ 1.2–1.4 inside the
2.5 band). **The binding constraint is the mirrored YIELD/escort,
which lands on the short N-S axis**: the study's "2, N-S, J2" row
puts the passer end at |y| = 1.668 — +0.132 m to the 1.80 band, and
+0.032 m with the full M1 error budget charged (vs the current E-W
yield's 1.67 against 2.5). New stationary E-W pockets fall under
the STALE instrumentation rule (marker 1's reproducible dropout at
(−1.75, 0); the 1.75→1.65 re-radius is the registered fallback).

Oracle and audit, extended rather than contradicted: **axis choices
whose χ costs differ by less than ε form an equivalence class**
(the χ-ε rule extended from recede ORDER to recede SET); the
asymmetric-junction variant's "cheaper axis" is χ-defined; ε and
the repair bound are RE-MEASURED for each new family (inherited
rule); the repair tie-break "toward M3's derived plan" is
re-specified for two modeled axes (derived plan = the χ-cheaper
axis; within ε, the proposed axis stands). **v3 IB10 provenance is
not comparable with v2 IB10 repaired rates** — stated, not hidden.

Evidence basis, stated precisely: one calibration episode (prompt
v3.1, χ tie 0.000) chose the mirrored pair; two pilot episodes
(v3.2) chose N-S and all-four; all under id_asc and pre-v3.3 —
suggestive of axis multimodality, not a measured distribution.
Under the v2-ruled random order the choice is counterbalanced and
analyzed conditional on the draw. NOTE (deliberate): modeling both
axes removes the "axis-mirror error" as an error class — the
round-3 citable-novelty claim shifts from naming the error to
measuring the CHOICE; the naming claim remains available for the
v2-era data where the mirror was unexecutable.

### Step 3 — emergent congestion: MAPD mini-cell × multi-conflict

Fused build; scene = the existing C55/A55 warehouse map (the
unified-scene-design module), N = 5. Build risks stated up front:

- **Registry semantics are the real cost**: `TaskRegistry` holds a
  single base assignment that `assign()` replaces; pop-on-arrival
  task queues interact with overrides, active-plan `continue` legs,
  the arrival gate, and the race guard — this is M5 contract work,
  not a yaml.
- **Dwell-vs-stall**: pickup/delivery dwells look like stalls to
  the ≥12 s trigger; dwell windows must be excluded or the trigger
  parameterized per cell.
- **Density check before registration**: N=5 (N=10 in Step 5)
  inside |x| ≤ 2.5 / |y| ≤ 1.80 with 0.55 m aisles, the permanent
  0.45 m pair latch and sub-0.6 m marker-overlap STALE band — a
  feasibility sweep precedes any oracle.
- **Baselines**: delay_vs_free_flow needs PER-TASK-SEGMENT
  baselines; the solo-in-space method extends per segment (same
  single-method rule), a `free_flow` table keyed by (scene,
  segment).
- **Horizon and arrival process registered** with the cell.
- **Comparison framing**: measures are ANALOGOUS to GECCO '25
  (makespan, throughput, completeness on a continuous Nav2 floor vs
  their 15×15 grid), not directly comparable; a
  prediction-avoidance arm is an OPEN DESIGN QUESTION (a
  congestion-cost-biased Nav2 global-plan proxy would be the
  cheapest honest analog) — without it, the claim is limited to
  detection-resolution's own value on task streams, with
  Layer-2-off (re-run, Step 0) as the control.
- In-flight cancellation (registered out of v2) is decided HERE if
  task streams make pending-leg-only supersession insufficient.

### Step 4 — plan-channel apparatus, second generation

- **Per-leg selection from verifier candidate sets** (the published
  MAPF recipe; the candidate-options flag already built) is the
  PRIMARY adoption, per the round-3 source's ordering.
  **Composition-from-marked-candidates** is the novel extension —
  "no prior art FOUND" (eight searches; CoRL 2026 proceedings
  unswept) — pursued after selection baselines exist.
- **Battery v2.1 and the multi-image keyframes arm: conditional on
  the v2 freeze's call** — both are registered on the v2 side
  ("build when probes next run"; the keyframes arm is a v2
  A/B-registered cell); they appear here only if v2 defers them.

### Step 5 — boundary pilots

- **Scale**: classification/triage at N=8–10 (one scene) and the
  MAPD cell at N=10 — a PILOT ESTIMATE of the regime boundary
  (pilots are excluded from confirmatory counts; converting the
  estimate into a registered boundary requires a scored cell at the
  v3 freeze).
- **Model breadth**: the verbatim-pilot core (head-on + IB10) on a
  third backend via the existing anthropic adapter (key/funding =
  owner decision).
- **Physical-camera episode** (standing owner option).

### Step 6 — v3 freeze

Same procedure as v1/v2. The freeze record pins, beyond the usual
prompt/config hashes: the nav2_params md5 AND the localizer
defaults (`stamped`, 0.01 s); the free-flow table id
(`free_flow_v2`); any new stage-2/marked-option prompt hashes from
Steps 2/4; ε and the repair bound PER FAMILY; `accepted_strategies`
derivations for every new v3 cell (MAPD may have none — rule
explicitly); the per-run GT-offset fit as the only sanctioned
GT↔ROS join; the Layer-2-off decision on the fixed stack; and the
VM-time priority rule (v2 collection outranks v3 builds).

Reading/consistency gates: GenePlan (2603.09481) skim; re-run the
concurrent-work scan AND re-scan for marked-candidate composition;
**rewrite the claim-2/4/5 wordings** — their current text says
"cite as concurrent work" for GAVEL / Physical Agentic AI
(arXiv:2608.22657) / SyncPlan, and by v3 those (plus 2609.27816,
DuoMind, Fresh Memory Stale Plans, EvoPlan) are PRIOR work; the
differentiators survive, the framing sentence does not.

Owner decisions deliberately left to this freeze: second-level
recovery beyond `fallback_exhausted`; lifting the loop family's
do-not-collect (per Step 1's outcome); the three-active-robot B2
junction variant re-assessment (flagged in v2 once `junction_clear`
existed). Items that belong to the V2 freeze and are NOT carried
here: B1 junction fields (verbatim-pilot ruling G), the
`accepted_strategies` derivation, IB10 random order, the convoy
free-flow aliases (ruled; executed in Step 0's generator pass), and
the stale t2b header fix (tied to the next permitted touch).

---

## What v3 does NOT attempt (carried exclusions)

Crowding (dropped by user decision, token retained); swarm-scale
flow shaping (positioned against); decentralized variants;
shared-Nav2-param tuning beyond the ruled H change; the
robot-blocker anomaly and token-scale crowding scenes (still
unregistered); real-time guarantees.

---

## References

The v2 design spec (authoritative for inherited rulings, at the
prereg-v2 tag once cut; meanwhile `fix/deadlock-collision-resolution`);
pinned report locations as listed under "Reference pinning"; the six
untracked literature reports under `reports/`; the prereg-v1
amendments lineage.

---

## Rev 3 (2026-10-07) — inputs folded after rev 2 (append-only)

Seven input streams landed between rev 2 (@64fb148 + scene rulings
@0f65304) and this revision. Each item below carries a ruling; nothing
above this line is rewritten.

### R3.1 Scenario formalism adopted (design-wide)

Every v3 scene is restated, at freeze time, as the tuple
**S = (M, R, X₀, G, C, τ, Σ)** — map, robots, initial configuration,
tasks, congestion class, trigger condition, metric set — with two
operational definitions carried design-wide: congestion measured as
**excess delay vs the same-robot free-flow baseline**, and the
**unresolved-after-timeout outcome kept as its own class** (justified
by the clogging literature's divergence criterion rather than an
ad-hoc threshold). Source: the 2026-10-07 literature round "Định
nghĩa congestion scenarios trong swarm" (untracked report under
`reports/`), which found only four explicit operational congestion
definitions in the field and no sham-congestion specificity control —
T0 (and S4's box-vs-robot pair) are hereby ALSO framed as that
missing specificity control in any v3 claims text. ADOPTED.

### R3.2 Audit inheritance (forcing audit 2026-10-07)

v3 runs on the post-audit artifact contract: `junction_phases`
serialized into decision artifacts (A1), recorded==dispatched via the
pre-write registry record (A5b), `self_resolved` outcome class —
`resolved` requires ≥1 dispatched decision, `n_dispatches` top-level
(A3), `order=discarded_yield_axis` tag (A4), and the two frozen
analysis rules: headline accuracy splittable by
`refusal_attempts`/`image_fallback_used`, and `repaired`-plan credit
conditioned on logged edit count/ops. v3 scorers (S1–S6) MUST consume
`self_resolved` and the backend_id filter from the start — they are
written post-audit and get no grandfather clause. The thesis-claim
ceiling established by the audit ("the VLM selects among
pre-engineered resolutions; the deterministic stack executes") is the
Methods-chapter framing; R3.3 is the registered route for raising the
model's causal content. ADOPTED.

### R3.3 New arm: dispatch-model-order-when-verified

Motivation (claim-strength review 2026-10-07): under the inherited
contract the junction dispatch order is always χ, with the model's
order honored only as a verification-time equivalence flag — so the
model's causal content excludes ordering by construction. REGISTER a
two-condition arm on S2/S3 (and S6 if its build lands): when the
model's `proposed_plan` passes verification (strategy consistent,
roles legal, order within the scene's registered ε-set), condition B
dispatches THE MODEL'S order; condition A dispatches χ as inherited.
Unverified plans fall back to the inherited path in both conditions
(the verifier is untouched — this changes the dispatch ORDER SOURCE
for verified plans only). Metrics: outcome-class and
delay_vs_free_flow deltas A vs B, stratified by `order_equivalent`;
plan-stability unchanged. One M3 flag + an A/B condition in the
runner; build cost small. This arm is the registered answer to "the
claim is too weak" — it either shows model ordering is as good as χ
(strengthening verbatim-dispatch claims) or shows χ repairs are
load-bearing (strengthening the verify-repair contribution). Either
result is publishable; neither is assumed.

### R3.4 Prompt/input upgrades from the capability round (2026-10-06)

From "Nâng cao năng lực điều phối VLM" (five-researcher round):
- **SoM-ID verbatim match** — verify the annotated frame's robot
  label text is byte-identical to the token the prompt/JSON uses
  (`robot_1`, not `1`); if any mismatch exists, fixing it is a Step 0
  apparatus item with a before/after pin; if none, record that check.
  ADOPTED (check first, A/B only if a mismatch is found).
- **Homography metric grid** — the wave-1 `grid` flag (built,
  default-off, byte-identity pinned) gets a registered per-backend
  A/B in Step 4; literature shows large spatial gains for some
  backends and regressions for others, so NO backend inherits
  another's grid verdict. ADOPTED as Step 4 condition.
- **Permutation voting** — already built (distinct-order ballots,
  earliest-tied-ballot tie-break); REGISTERED as a Step 4 condition
  on the two most order-sensitive families (S2, S3), single-draw
  elsewhere. Literature positions it as the direct countermeasure to
  the measured first-slot/robot_1 prior.
- **Contradiction trigger + per-event replan budget** — M5 build
  item: re-query early when a commanded robot measurably diverges
  from its issued leg (definition to be frozen at Step 6: leg status
  FAILED or position divergence beyond a registered bound), with a
  per-event replan cap. Event-triggered-vs-periodic evidence: ~20×
  fewer replans at equal reward. ADOPTED into Step 4.
- **Failure-explanation line** — the failure context gains a
  classically-derived one-line cause (from leg statuses/refusal
  reasons already in artifacts), not a model-generated one; the
  literature's largest closed-loop gains attach to the explanation,
  and a classical source keeps the channel deterministic. ADOPTED
  into Step 4.
- **Cross-provider vote pilot** — gpt-4o + ER-2 vote on the strategy
  enum (and disagreement-triggered escalation variant): no published
  robotics result exists; measured error modes are decorrelated.
  REGISTERED as a Step 5 pilot.
- **RAG over past congestion episodes** (M3 episodic memory):
  unclaimed in 2024–2026 literature but a build of its own. DEFERRED
  (future-work section of the thesis; not a v3 cell).

### R3.5 Trail arm: RULED OUT at current settings

The 2026-10-06 offline pilot (feat/trail-probe-pilot@cb1c171, adopted
file-only at 88b3bb4): every backend×probe delta ≤1 vs a same-day
re-ask across the 59 frozen battery items; the 3 s trail renders a
median 222 px in a 1.23 Mpx frame. No v3 trail arm. A re-pilot
(~$0.30, same offline harness) is CONDITIONAL on all three of:
6–10 s window, bolder stroke, and the trail gloss added to the probe
prompt — and is only motivated if a v3 scene shows temporal-confusion
failures in collection.

### R3.6 S1 family: S1b sparse-warehouse variant REGISTERED (pending owner approval)

Companion to the S1 density ruling (@0f65304): a second S1 family
member on the SAME tracked-band footprint with minimal racks —
density moves from ~5.4 free cells/agent toward the ~11–12 ceiling
the camera footprint allows (their 40.5 stays unreachable; the
deviation note stands). S1a+S1b form a two-point density axis whose
completion trend is comparable-in-direction to the GECCO paper's
agent-count table. Build cost (precedented by the loop-map wave): USD
build + Nav2 map via the existing generators, hotspot Monte Carlo
re-run, ~18-leg free-flow harvest, one M1 coverage verification
session. Runs only if S1a lands and budget (R3.7) permits.

### R3.7 Episode budget correction (timing probe 2026-10-07)

Measured harness cycle is **1082 s median for a 2-robot cell** (probe
report `docs/reports/2026-10-07-shutdown-timing-probe.md`,
probe/shutdown-timing@8da4964) — not the ~12–13 min earlier sections
assumed. Facts folded: `fast_shutdown` is already the Isaac 6.0.1
default (shutdown ≈ 14 s; no patch); Kit swallows SIGTERM (the real
mechanism behind the Isaac-survives-cleanup trap); ~238 s/cycle is
fc_launch tailing after Isaac exits; 56% of a head-on cycle runs
after all arrivals. Two harness options sit with the coordinator:
**Option B** (stop tailing on Isaac exit; no outcome change;
−241 s/2-robot cycle) — v3 ASSUMES Option B lands before any v3
collection; **Option C** (in-loop stop flag on all-arrivals;
truncates post-arrival GT on resolved episodes) — if ruled in, v3
free-flow and flow-metric definitions are unaffected (all are
pre-arrival quantities), but the ruling must be append-only and
precede free_flow_v2. S1's own budget (R=20/arm ≈ 40–48 h) already
assumed ~1 h/episode and is NOT reduced by Option C (task-stream
episodes end on task completion, not arrivals). Every v3 cell-count
decision at Step 6 uses 18 min/episode (2-robot), ~23 min (3-robot),
and the scene doc's own figures for S1/S5, under the current harness,
minus Option B's saving once confirmed.

### R3.8 Roster, prompt lineage, and tiering

v2's roster grew (qwen3-vl, sonnet, deepseek-flash, gpt-5.6-sol
validated 2026-10-07; gpt-5.1 deprecated) and prompt moved to v3.4
(think block removed, family re-pinned). Consequences: (a) Step 6
re-pins the FINAL prompt digest at the v2 freeze tag — the v3.3
digest cited earlier in this doc is superseded by whatever the tag
carries, and per-backend calibration episodes post-v3.4 are a Step 0
item; (b) model scope is tiered: confirmatory v3 arms stay on the two
frozen backends; the wider roster enters ONLY through Step 5 as
tier-0 probe battery (all models, offline, ~$0.25/model) then tier-2
small pilot cells for the top 2–3 — the nine-arm full matrix is
explicitly NOT a v3 deliverable (cost ≈ 480–600 VM-h under the
measured harness).
