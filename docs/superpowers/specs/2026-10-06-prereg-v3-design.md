# Prereg-v3 Design — Fixed Stack, Detour Judgment, Emergent Congestion

**Prepared:** 2026-10-06

**Revision history:**

- Addendum A31 (2026-10-20): E24-E26 escort-filter mini-batch outcome, inserted after A26 and above A30, as A27-A30 were.
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

### R3.6a S1b amendments after advisor review (2026-10-07, supersedes
R3.6 where they conflict)

Four corrections from the advisor pass on R3.6's sketch:
1. **Latch-aware corridor width.** "≥2 robot widths" (0.712 m) is NOT
   passable under the 0.45 m M4 latch: two passing robots need
   center separation ≥0.45 m, so genuinely two-lane corridors around
   the rack islands must be **≥0.85–0.90 m** (Nav2 inflation checked
   on the real costmap). Acceptance includes a LIVE two-robot pass
   check in the M1-verification session, not a geometric claim.
2. **Regime axis, not density axis.** S1a→S1b changes both density
   and congestion class (deterministic single-lane → stochastic
   clogging), so the pair is registered as a **regime axis**;
   completion trend vs the GECCO agent-count table is cited as
   qualitative direction only. The phrase "two-point density axis"
   in R3.6 is retired.
3. **Inflation-adjusted density.** Free-cells-per-agent figures are
   recomputed on the **post-inflation Nav2 costmap** of each map
   (count free cells, divide by N); the geometric 5.4/10.5 numbers
   survive only with an explicit "nominal, pre-inflation" label.
   Rack coverage percentages are counted on the tracked band.
4. **MC gate derived, hypothesis de-directionalized.** The S1b
   Monte Carlo gate thresholds are derived from S1a's own MC
   (median first conflict 15 s; 309/400 junction share) plus the
   statistical requirement of ≥1 congestion event per episode, with
   the SAME conflict definition as S1a's MC; the specific numbers
   are frozen at Step 6, not invented per-map. The Arm A−Arm B
   comparison across regimes is registered as **CI estimation of
   the delta per regime**, with the Goldilocks expectation (delta
   maximal at intermediate difficulty) recorded as interpretation,
   not as a directional hypothesis.
Minor carried items: island/node placement stays inside verified M1
extents and away from the marker-edge STALE zone; the release
stagger Δ and its feasibility bound are recomputed for the new
layout (S1a's Δ=4 < 4.42 is geometry-specific).

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

---

## Rev 3 addenda (2026-10-08) — build-campaign rulings (append-only)

Rulings accumulated while building Steps 0/3/4 and S1/S6 on
`feat/v3-integration` (tip `11fa31a` at writing). Evidence lives in
the branch's commit messages, test files, and the build agents'
reports; nothing above this line is rewritten.

**A1. S6 pair-B poses amended.** robot_3 spawn → (0.25, 1.2, 0),
robot_4 spawn → (2.05, 1.2, π); goals unchanged. Reason: the spec-table
pose left robot_4's chassis overlapping the aisle end by 2 mm at t=0
(guaranteed depenetration artifact). After the move: rear clearance
0.048 m, midpoint separation 1.662 m preserved, pair-B spawn gap
1.80 m, lag 4.0 sim-s. The overlay's D=16 wall-s is PROVISIONAL (sits
just under the 16.7–19.0 ideal at RTF 0.21–0.24; both jams still form
by the first trigger) — D is re-derived in the S6 VM timing pilot.

**A2. S6 Arm-B degeneracy REGISTERED pre-collection.** The classical
`_head_on_pair` crowding rule rejects BOTH S6 pairs (inter-pair robot
distance at standoff 1.389–1.459 m < r_conflict 1.5 m — the spec's
1.66 m holds for jam midpoints, not robots), so Arm B is expected to
classify S6 as `unknown`. This is registered as expected comparator
degeneracy — evidence that the classical rule cannot decompose a
multi-conflict scene — and S6's confirmatory scoring is
decision-scored on the model plan (oracle `addresses_both`,
criterion_status: proposed), not Arm-B-compared.

**A3. Dispatch-off semantics (deviation from scene-doc build item 9).**
The shipped flag runs the FULL pipeline including M3 grounding and
artifact write, suppressing only the publish to M4 (scene doc said
"never grounded or dispatched"). Deliberate: log-only cells need
grounding provenance to be scorable. Artifact keys `dispatch_enabled`
/ `dispatch_suppressed` (absent when dispatch is on). Scorer rule for
log-only cells: skip any record with `dispatch_enabled: false` when
counting dispatches (the landed `dispatch_suppressed` guard alone
does not guarantee strict zero on non-OK/filter-emptied outcomes) —
implementation queued with the `free_flow_run.sh` glob fix. Known
wrinkle for Step 6: with the plan channel enabled under dispatch-off,
accepted plans' legs stay `pending` forever and appear so in the next
prompt's plan-state block.

**A4. S1 finished_mode: `park` shipped (scene-doc variant C);
wandering (variant D) NOT built.** Decision deferred to after the
first S1 pilot: either build wandering or register a park deviation
with evidence that parked finishers do not seed node blockage.
Harness notes: tasks_*.jsonl collection glob fixed in v2_final_run.sh;
same fix owed to free_flow_run.sh.

**A5. R3.3 freeze notes (from the build).** (i) The arm infers
"verified" from `vlm_verbatim` provenance — the verifier exposes no
standalone within-ε verdict; (ii) verifier-χ and dispatch-χ are
computed separately and agree only via the id tie-break + membership
checks (grounder permutation guard is the backstop); (iii) ε is
measured on unstaggered χ while dispatch drives staggered pockets;
(iv) `order_equivalent` now means plan-vs-χ in BOTH conditions;
(v) SAFETY INVARIANT to freeze: model-order dispatch is safe for
same-arm stacks only while the family's ε < the follower weight
(0.5) — any scene whose re-measured ε reaches 0.5 must not enable
condition B; (vi) `repaired` plans are excluded from model-order
dispatch even when no edit touched a recede leg — a finer
`PlanEdit.robot_ids` rule is an owner decision at freeze.

**A6. R3.4 freeze notes.** Divergence bound 0.5 m is a placeholder;
no persistence requirement on the divergence predicate (an M1 jump on
a non-STALE frame can arm a false contradiction — consider a 2-frame
persistence rule at freeze); the re-analysis detail text "congestion
re-detected for the same robots" is inaccurate on the contradiction
path (left unchanged for byte-discipline; reword behind the flag at
freeze); the failure-explanation phrases name no strategy values —
register-reviewed, final judgment at freeze.

**A8. IB10 release-lane defect: diagnosis ruled, remedy registered
(2026-10-08).** The merged-tree IB10 1/4 regression (two replicates)
is NOT a code regression: re-grounding the key snapshots under
0b2e755 and 071f9c1 exports is byte-identical; the release lead is χ
rank 0 by registered rule, and the robot_3/robot_4 χ margin is
0.000–0.133 across all 11 historical bundles (< ε) — the lead is
jam-formation noise and MUST remain unordered. The defect is a
latent step-7b release-design weakness: the held receder's pocket
sits on the lead's exit lane, and pre-fix passes survived on stale
costmap marks forcing wide avoidance (8/8 clean, +16..+166 mm after
11–38 s pauses); fix-H clearing removed that accidental cushion
(post-fix: +11 mm, contact, contact). REGISTERED REMEDY (build item,
config-gated, default-off, enabled only in v3 cells): (i) the held
receder's release yield gains a lateral pull-off (`pull_off_lateral_m`
— M4 already supports the parameter and its own comment names this
case) or equivalently a lateral pocket offset for χ rank ≥1;
magnitude derived from junction geometry, PROPOSED at build, frozen
at Step 6 after the validation arm; (ii) optional un-exempted
hard-contact floor in M4 (the release exemption allowed a 28 s push
with no stop). Explicitly REJECTED: registering a fixed lead
("robot_3 first" in the fix-branch run was a draw) and raising Nav2
inflation (touches every scene). VALIDATION ARM (VM, ~3–4 replicates
until both leads appear + remedy on under both leads): bag both
robots' costmaps/plans/scan through the release window; measure lead,
min distance, lateral offset at 0.6/0.4/0.2 m gaps. INSTRUMENTATION
CAVEAT escalated to the v2 lineage: GT `robot_robot_contacts` MISSED
a 0.084 m-centre contact with a 0.55 m push — the step-7b "zero GT
contacts" claim is unsupported by that field; v3 scorers must not
rely on it and the contact metric needs a distance-based recompute.

**A7a. Step 0 closure status (supersedes nothing; records the gate).**
Step 0 closes for: smoke (registered goals, PASS), free_flow_v2
(22/22 legs, per-leg delta −0.8..+0.2 s vs v1, mean −0.07 — FROZEN as
config/free_flow/free_flow_v2.json, build item queued), T3c (13.1–14.2
s vs 32.0 pre-fix, 3 replicates), blocked_path_transient (clean).
Step 0 stays OPEN for: IB10 (pending the A8 remedy + validation arm)
and the loop-map corner wedge (controller-side local minimum at the
second-aisle mouth, fix-invariant, now reproduced on ldt + perm_wait
+ diag_costmap — Step 1's NO-GO stands on direct evidence; no
controller tuning, per the carried exclusions; S4's immunity to the
wedge is checked in its own VM wave).

**A9. IB10 CLOSED under the A7a/A8 gate (2026-10-08).** The validation
arm ran until both leads appeared; the remedy held under both
(robot_3-led passes 0.438–0.499 m, robot_4-led 0.402–0.436 m; floor
silent in 8/8 clean passes; release on clearance; 4/4 arrivals in all
5 final-wave runs). FROZEN: pull-off 0.33 m (held-x −0.340..−0.354 vs
wall bound −0.36 — do not raise), side −x (held pulled −x 8/8, lead
passed +x 8/8 incl. 3/3 robot_3 leads), floor 0.20 m RULED a
push-limiter backstop, not a contact preventer (its one true positive
fired at/after contact; a speed-aware value is a Step 6 option, not a
default). The cross→release hand-off race is FIXED (M4 guard,
default-on with kill switch: suppress re-sends while a command owns
the robot, cancel-own-goal not cancel-all, repeated controller stop
for orphaned FollowPath — Nav2 1.3.12 bt_action_node halt() cannot
cancel a goal whose handle has not spun); precursor 9/10 pre-fix →
0/5 post-fix. SCORING RULING: frozen chi-pair criterion 2
(`order_correct`) must read the EXECUTED recede order from
`junction_phases`, not from `plan.legs` (which preserves the model's
raw order) — otherwise every robot_3-led episode mis-scores; applies
before any v3 IB10 cell is scored. The r3lead probe's Δ=0.15 nudge
did NOT shift the offset distribution as predicted — do not reuse it
to force leads. OPEN: the 0.32–0.35 m scan blind band (held robot
drops out of the lead's scan; cause unknown; clean remedy passes stay
above it).

**A10. S6 first light (2026-10-08): scene validated; perceptibility
gate REGISTERED before any S6 collection.** Mechanics all PASS (USD +
validators, amended poses confirmed, dual jams formed 2/2 in
overlapping windows, M1 100% FRESH on markers 3/4 incl. the 16 s
hold, spawns clean, no self-detour). D moves 16 → ~20 wall-s
PROVISIONAL (per-run ideal 17.4 and 24.7; M5 starts the delay clock
~3–5 wall-s before pair A's goals reach Nav2; a recording-off ≥3-run
timing pilot fixes it, or the delay is counted from pair A's dispatch
— code change, owner's pick at Step 6). CORE RULING: the live ER-2
pilot's FIRST decision named/addressed only pair B — but at that
snapshot pair A still read MOVING in M1 (GT standoff only ~0.3 s
earlier; M1 needs 0.6–1.3 s to report STOPPED). Scoring that snapshot
measures trigger racing, not scene-wide attention. REGISTERED:
S6's scored decision is the first triggered decision at which BOTH
pairs are M1-perceptible as stopped; episodes where that never
happens are invalid-formation, not model failures. A2's Arm-B
`unknown` expectation is conditioned the same way (mock: 35/35
`unknown` once both pairs stopped; the early live snapshot correctly
returned `head_on` on the only perceptible pair). The pilot's later
decisions all named both pairs — recorded as the first (n=1,
non-confirmatory) sign that scene-wide naming works once the scene is
perceptible. Harness: two new traps recorded (root-owned
isaac/scenarios defeats build_scenario silently; Option B cleanup
kills the video recorder — fc_launch fix owed); overlay for scoring
needs `plan_channel_enabled: true` (used in the pilot, noted as a
scoring-prereq for S6 cells).

**A11. Dynamic-grounding wave rulings (2026-10-08, integration tip
6d33508).** The dynamic arms / node-handoff / parked-exclusion wave
(flags default-off, 189 flags-off goldens byte-identical) surfaced
five rulings:
(i) **Rear-swap and reverse-exemption ACCEPTED** as part of the
`dynamic_scene_arms` mode contract: within the mode (S1 cells only)
a yielder facing away from its partner is swapped with one facing
it, and such a robot is dropped from a reversing set — physical
consistency with M4's backup semantics; every reassignment is
tagged (`grounding=rear_regrounded/rear_exempt/
node_handoff_regrounded`), and none of it operates with the flag
off. The node-handoff re-ground (arriver yields to the node
occupant regardless of M2's naming) follows the scene doc.
(ii) **junction_clear in S1: RECOMMENDED exclusion** from S1's
accepted-strategy set (S1 jams are corridor/node class; the
composite's grounding and its plain-yield fallback use declared
geometry, which reproduces the mid-route defect). Evidence basis:
the wave's hand-computed W-lane mid-route head-on (robots at −1.6 /
−1.2 on the +0.35 lane) is REFUSED outright by declared-geometry
grounding and grounds cleanly under the dynamic view (corridor
centre −1.4, park offset 0.646, backup 1.3 m — pinned in
test_dynamic_grounding.py); junction_clear's fallback is a plain
yield on that same declared path, so in an S1 mid-route jam the
composite's failure mode is exactly the refused case above. Final
call at Step 6; the alternative (routing the fallback through the
dynamic view) is recorded but not built.
(iii) **New S1-pilot BLOCKER (M4): escorts run
drive_heading(target_yaw=0.0)** — assumes spawn-facing-goal; under
task streams the passer (incl. a robot dwelling on a node) is
escorted along its spawn heading. Fix queued: derive escort heading
from the robot's current goal bearing (or an M3 escort-off rule for
dynamic mode). S1 overlay prerequisites recorded: declare
aisle_{x,y}_band_m; declare racks/band edges as static_obstacles
and run the gate in swap mode (else rear room is unbounded);
enable the mode via an S1-only grounding_params_path (never edit
the md5-pinned rag.yaml); check the 45 s hold backstop against
dwell+departure at measured RTF.
(iv) **Plan-channel refinement** (commit 5d5b867): plan consistency
is audited against the MODEL'S OWN decision while defaults/repair
use the dynamic view — an S2 plan giving the parked robot a role now
scores `repaired` (one substitute edit) instead of `m3_default`;
scoring reads provenance+edits as per the frozen analysis rules.
R2-comparability clause: a parked-robot substitute DOES consume the
repair bound and appears in the edit log as
(op=substitute, robot_id ∈ parked_robots), and the command carries
`grounding=parked_excluded:<id>` — so it is mechanically separable.
The v3 freeze defines a `repaired_parked_only` subclass (precedent:
`repaired_order_only`): plans whose ONLY edits are parked-robot
substitutes are reported as their own stratum, keeping R2's
edit-conditioned credit and the provenance distribution comparable
between dynamic-mode and static-mode arms.
(v) **Parked-robot mechanism = declared list**
(`scenario_geometry.parked_robots` + 0.35 m tolerance), not a
goal-arrived rule (which would strip S1 dwellers and IB10 leads);
the parked follower STILL counts in N_f — the S2 axis contrast
depends on that term; displacement beyond tolerance grounds
normally and tags `parked_displaced`.
Cross-lineage note: the fc_launch recorder clean-stop is commit
28a4c9c (single-patch rule: composite+hotfix take it by cherry-pick
from that hash only).

**A11(iii) addendum — BOTH spawn-frame blockers fixed (commits
e903544 + f0cc17b, merged @4d88bc1).** The escort fix landed as
ruled (M3 computes the escort turn from the passer's current
registry goal, snapped to the measured axis, passed as a
relative-to-start turn — a world yaw never crosses the M3/M4
boundary because each robot's odom yaw 0 is its spawn heading; an
escort-off rule tags `grounding=escort_off:<id>:<reason>` when the
passer has no usable goal, which makes a dwelling node-occupant
wait out its dwell under Nav2 — the 45 s hold backstop check is
therefore load-bearing for S1). The SIBLING defect found during
that fix: M4's `backup()` servoed every reversing robot toward the
odom y=0 spawn line (heading ≈ 0 assumed), so an off-spawn-heading
yielder backed along an ~0.2 m-radius arc. Fixed with the same
pattern: under `dynamic_scene_arms` only, M3 marks every grounded
yield/reverse backup (junction recedes and release holds included)
with boolean `backup_line_hold: true`, and M4 holds the line
through the backup's own start pose along its start heading with
the reversing correction sign. Absent the keys, dispatch and servo
are byte-for-byte pre-fix; the 189 flags-off goldens are
byte-identical. PILOT MEASUREMENT registered: M1 θ error on
stopped robots and escort lateral deviation (3° ≈ 12 cm over a
2.35 m escort vs a few-cm lane-to-rack margin).
CONTAINMENT (citable): the backup() servo defect does NOT taint any
v1/v2 number — every v1/v2 scored geometry spawns its yielders
aligned with their spawn heading, so the legacy odom-y=0 assumption
HELD wherever it was exercised, and the fix is flag-gated off
outside `dynamic_scene_arms` (byte-identical goldens). The defect
only ever expresses in task-stream geometries that no collected run
has used. GATE (not advisory): the S1 pilot treats the 45 s hold
backstop check (dwell + departure at measured RTF vs backstop)
as a PASS/FAIL gate — under the escort-off rule a dwelling occupant
leaves via Nav2, so a silent backstop regression now breaks S1
SEMANTICS (premature release), not just timing.

**A12. S1 pilot episode 1 rulings (2026-10-08, report
2026-10-08-s1-pilot.md @188ad55; VM stopped after).** One full
600 sim-s episode (seed 1, mock), stopped by the rack-wedge rule.
(i) **Default mock cannot exercise S1's grounding** — it answers
no-congestion and the pipeline stops before M3, so the episode was
effectively Layer-2-off; scripted fixed-id mocks cannot match
emergent stalls. REGISTERED APPARATUS: an **echo-mock** mode that
names the triggered robots in its decision (deterministic strategy
per config), existing solely to exercise grounding_view end-to-end
without API; apparatus-only, never a scored arm.
(ii) **Release stagger moves to sim-time** (closes open question
S1-10): wall-clock stagger × fluctuating RTF put 2/3 measured Δ
outside the (0, 4.42) sim-s window (4.633/4.533/4.367 at
release-RTF 0.188); the Δ-artifact jam at the E gate (arriver meets
a not-yet-released occupant) is the same defect's scene-level face.
(iii) **Re-trigger cadence**: 216 analyses/episode at ~16.5 wall-s
intervals, 195 naming all five robots — a live episode would spend
~216 calls and spam the registry. REGISTERED build item: a
scene-unchanged suppression policy for task-stream cells (skip
re-analysis while the stalled set and robot poses are unchanged
within a bound since the last no-action analysis; exact predicate
frozen at Step 6). The existing cooldown/exhausted semantics are
not sufficient for persistent multi-robot stalls.
(iv) **Corner wedge now has a PHYSICAL-CONTACT variant on S1 legs**:
robot_3 pinned at the SW rack corner 277 sim-s (cmd_vel actively
pushing; GT pose static within 1.6 cm; freed by a spin recovery).
Every S↔W*/N↔W* leg turns such a corner — S1 registration must
either accept-and-measure (wedge episodes as an outcome class) or
gate on a mitigation; decision at Step 6 with the Step-1 wedge
file. GT `robot_static_contacts` logged 0 rows during a physical
pin — audit-A8's distance-recompute rule extends to STATIC contacts.
(v) Gate outcomes recorded: 5-stack bring-up met (1/2 attempts; bond
timeout once — infra fix candidate), RTF 0.164 (predicted
0.15–0.19), hold-backstop PASS 40.3<45 (thin: fails below RTF
~0.129), M1 θ median 0.44°/p95 1.40° and position 6 mm median —
the M1-precision pilot question resolves FAVORABLY (5.7 cm p95
escort drift vs 12 cm budget). Arm B named only the E-gate pair in
216/216 — classical non-decomposition on task streams, consistent
with A2's register. (vi) **Wandering-vs-park stays OPEN** — no
finisher existed in a Layer-2-off episode; the datum requires live
(or echo-mock) dispatch. 3 occupied-node arrivals observed (1 of
them the Δ artifact).

**A13. S1 fix chain complete (2026-10-08, integration @4bfcd43).**
The A12 fixes landed and surfaced, then closed, a three-link
lane-scoping defect chain in dynamic-mode grounding:
(i) **Shipped per A12:** sim-time stagger (anchored at the stream's
FIRST SCENE, not the absolute M1 clock — Δ in-window by construction
at any RTF; S1-10 closed); echo-mock apparatus (robot set parsed
from the prompt's structured status lines — the trigger set never
reaches the request; `diagnostics.mock_mode="echo"`;
apparatus-only); scene-unchanged suppression (set-equal + poses
within ε=0.05 + no-dispatch reference; measured 216→6
analyses/episode on the ep1 replay; the dispatched-loop residual —
clause (c) never arms after a dispatch — is a Step 6 call).
BUDGET LINE: live-dispatch cadence projects 95–216 analyses/episode
(ER-2 ≈ $0.70–1.59, ×2 from 2027-01-01); S1's MAX_ANALYSES is sized
from that row, not from the no-dispatch row.
(ii) **Lane-scoping chain (all three links the same defect class —
dynamic lanes measured against whole-aisle machinery):** rear room
counted flanking racks via the 0.6 aisle band and lane mouths at the
yielder's own pose → 0.00 m for every robot (fixed: footprint-band
measurement + tracked-band end caps obstacle_7..10 + candidate-vs-box
sweep + repair held to the lane pair); backup clearance projected
EVERY crossing-order robot onto the retreat axis (fixed: swept
corridor |lateral| ≤ 0.38 m, plus a 3.7 m reach bound behind the
yielder); crossing order/escort included off-lane robots so one
failed escort heading stripped the on-lane passer's escort (fixed:
lane-scoped order with `order=lane_scoped:<ids>` tag; off-lane
robots get unlinked waits carrying requested_strategy). Box-sweep
margin 0.05 m PROPOSED (= the aisle band's own chassis margin;
deeper-backup-over-refusal via `retreat=deepened` — PROVENANCE ONLY
for analysis). End state: ep1 replay grounds an executable yield
216/216 (backup 1.380–1.381 m, park gap 0.053–0.054 m, escort
2.40 m heading π), byte-identical to the two-robot reference.
Caveat recorded: ep1 is ONE jam grounded 216 times, not 216
conflicts.
(iii) **RULING NEEDED at Step 6 — Arm B on S1 is blind:** the
classical shadow uses declared aisle-band geometry and refuses
216/216 with 0.00 m room. Options: (a) give the shadow the SAME
footprint-band measurement in S1 cells (measurement parity, not
strategy help — RECOMMENDED, it preserves the only system-level A/B
contrast S1 has); (b) register Arm B as degenerate on S1 (the
S6/S4 precedent). Until ruled, no S1 A/B claim is valid.
COORDINATED POSITION (both sessions, 2026-10-08, final call at
Step 6): measurement parity, under one HARD CONDITION — the
shadow's footprint band comes from the SAME code path and inputs
as M3's dynamic view (a shared function, never a parallel
reimplementation), flag-scoped to S1 cells with declared-geometry
goldens pinned everywhere else. Rationale: Arm B means "classical
reasoning over the same perceived world"; in v1/v2 both arms read
declared geometry so the contrast was reasoning-only — if S1's
grounder moves to the footprint view while the shadow stays
declared, the cell measures input asymmetry, not reasoning. One
definition, two geometry sources, each arm-pair always sharing one.
(iv) **Registered residuals → resume checklist:** separate the
clearance set from the crossing order (an in-reach goal_behind
robot can still strip escorts — did not occur in ep1); M4's
no-escort single-passer path releases ALL waits at hold start
(early release of the off-lane trio if an escort drops live);
120 s off-lane waits are tight vs backup+hold+escort; live escort
headings use registry mission goals (replay used snapshot goals);
stage 2 live selection unexercised; the whole chain is
closed-loop-unverified on the VM (static replay only).

**A14. S1 episode dynamics: findings, fixes, environment exonerated
(2026-10-09; reports s1-pilot-resume, s1-e2-e3, env-audit; integration
@face0f1 lineage).**
(i) **Closed-loop verdicts for the A13 chain (E1, one executed
yield):** backup line-hold 1.2 mm lateral over 1.37 m; sidestep
1.3 cm; escort tracking 3.5 cm vs the 12 cm budget; M4 clearance
release correct. The mechanical chain is live-verified.
(ii) **Fixes shipped (flag-gated, dynamic/task-stream only):**
`refusal_no_action` (refusal wait fan-outs withheld, artifact gets a
dispatch_withheld block, suppression arms — E1's 46 analyses → E2's
4–5 with ~200 avoided; ACCOUNTING RULE: artifacts with
dispatch_withheld count as NOT dispatched even though
dispatched_command is populated); `escort_turn_cap` (escort+clearance
capped at the passer's distance-to-turn; E1 measured the uncapped
2.35 m carrying the passer 0.4 m past its turn into a latch). UNITS
RULING: hold backstop and wait timers run in SIM seconds
(use_sim_time); the A11(iii) wall-second gate arithmetic is
superseded — in sim units the backstop passes at any RTF.
(iii) **The 0.00 m ambiguous-path defect:** a robot heading >30° off
an axis falls to the declared-geometry fallback whose corridor
mouths sit on the rack faces → fake 1.1e-16 room for everyone.
Step 6 item: the ambiguous path must refuse with its true reason,
never a fabricated 0.00. The outcome in S1 is unchanged by the
defect (hand-checks: the refused robots were genuinely pinned or
latch-bound).
(iv) **CENTRAL FINDING — latch-cluster gridlock:** at S1a density the
0.45 m safety latch forms permanent multi-robot clusters (2 pairs in
E1; 5/5 robots from ~47 sim-s in E2 before Layer 2 acted; the OLD
VM's seed-1 pilot froze identically at +19.2 s vs E2's +18.7). The
only latch release is an exempt clearing maneuver, and the dynamic
view refuses exactly these sandwiched/ambiguous configurations
(verified genuine geometry, not a bug, for the latch-bound cases).
E1 additionally measured Layer-2 wait-spam cancelling Nav2 goals
before recoveries could fire (0 recoveries; the old pilot's
self-free spin never ran) — mitigated by refusal_no_action but not
yet re-verified closed-loop on a wedge.
(v) **ENVIRONMENT EXONERATED (pre-registered A/B):** Nav2-1.3.12
container reproduces E2 (first latch Δ0.4 s, same pairs, 5/5 frozen,
paths ≤1.8 cm); package delta reduces to pydantic+GPU-driver, covered
by cross-VM seed-1 kinematics (≤1.2 cm, ≤0.14 s); DDS profile live
on all nodes; seed draws byte-equal (Mac/container/runtime, 3
seeds); both boxes are 6.0.1 SOURCE builds with identical Kit
stamps. CORRECTIONS: A9's "Nav2 1.3.12" is the upstream SOURCE
version read during that work, not the installed version — both VMs
run 1.3.13 (inferred for the old box); bt_action_node.hpp is
unchanged 1.3.12→1.3.13 so A9's mechanism stands, label amended.
The s1-pilot-resume caveat "old box = automator release build" is
wrong (both source builds).
(vi) **Open:** seed 2 is a 1-in-144 harsh draw (4 robots to S);
robot_2's SW-corner graze is deterministic but asymmetric vs its
mirror (0.040 vs 0.11 m, unexplained); empty-reroute fallback (no
waypoints) is dispatchable and M4's handling is unverified;
wandering-vs-park remains undecided (0 finishers in pilot/E1/E2);
the stop-rule window (150 sim-s) is shorter than the one measured
self-free (277 sim-s). S1's direction (engineer cluster-clearing vs
accept the clogged regime and prioritize the registered S1b) is an
OWNER decision pending.

**A15. S1b first light: pass-check falsified the passing premise;
S1b re-registered on a RESOLVABILITY axis (2026-10-10; report
2026-10-09-s1b-first-light.md; integration @d470470 lineage).**
(i) **Built and gated:** the S1b sparse floor (two staggered 0.30 m
C55 islands, 9.78% tracked-band coverage, all gaps ≥0.90 m vs the
0.88 m latch-aware bound; regime-axis density per agent: S1a
5.44 nominal/5.02 inflated vs S1b 10.74/10.02). The S1a Monte Carlo
was rebuilt (scripts/s1_mc.py, reproduces the published S1a row)
and the MC gate was DERIVED from real S1a bundles (live-vs-MC lag
1.25×): all six thresholds PASS (G1 1.000, G2 p90 20.1 sim-s,
G3 0.275, G4 0, G5a-geo 0.818, G5b 2.55). Δ RULED 2.5 sim-s for
this layout (R3.6a recompute; 4.0 produces 41/400 release
artifacts). Node set and forbidden Wp-Wm leg kept so each seed
draws the identical task stream on both floors.
(ii) **LIVE PASS CHECK FAILED — premise falsified:** two opposing
robots on the 0.90 m gap latched at 0.423 m M1 gap, offset only
~0.15 m despite a 0.70 m zero-cost band (one run, narrowest gap;
DWB-offset cause is inferred). Prior S1a bundles corroborate: 0/4
opposing approaches ever cleared 0.45 m, even in a 1.2 m strip.
CONCLUSION: autonomous passing does not exist on this stack at any
tested width — corridor geometry was never the binding constraint;
the latch is.
(iii) **RULING — latch-on-pass is REGISTERED as S1b's conflict
class, and the S1a/S1b axis is re-registered as a RESOLVABILITY
axis** (supersedes the R3.6a "regime axis" wording): S1b = low-rate,
predominantly pairwise conflicts, 81.8% geometrically resolvable by
a single yield (G5a); S1a = early multi-robot latch clusters that
grounding correctly refuses (A14). The architecture's passing
mechanism IS Layer 2, by design. Alternatives RECORDED and ranked
behind: one-way gaps (engineers the flow — adjacent to the carried
swarm-flow-shaping exclusion), keep-right costmap bias (inside the
Nav2-tuning exclusion unless map-scoped, registration burden),
opposing-pair latch relaxation with the 0.20 m floor as backstop
(amends the safety invariant — heaviest burden).
(iv) **M3 resolution cap measured:** executable-yield rate on MC
first conflicts is 0.405 (S1b) / 0.345 (S1a); causes: the
ambiguous-branch refusal (A14(iii) item, now PRIORITIZED) and the
swap gate retaining a yielder whose sweep finds no room → empty
reroute no-op (NEW Step-6-priority item: swap to the partner when
the sweep fails; also `refusal_no_action` does not withhold empty
reroutes — close that hole with it).
(v) **Latch-cluster exposure on S1b is NOT transient without
Layer 2** (346/400 ≥3-robot clusters by 60 s vs S1a's 360/400,
forming later: median 19.2 vs 11.3 s) — S1b's claim rests on
Layer-2 intervention BEFORE cluster closure, which its later onset
and pairwise-first structure make feasible where S1a's 7 s window
did not. The S1b pilot (staged) is the test of exactly that.
(v-bis) **Citation pair for the thesis (coordinated note):** the
forcing audit's Section 3 F3 observed this mechanism from code
alone — "inside a 1.2 m aisle the 0.45 m latch makes NON-commanded
resolution nearly impossible — the safety layer is simultaneously
the reason 'VLM plan resolved it' is credible and the reason almost
any spatial strategy token resolves." A15(ii) upgrades that
read-only observation to a MEASURED architectural property (0/4
clears at 1.2 m; 0.423 m latch at 0.90 m) — cited together, the
resolvability-axis re-registration is the audit's prediction
confirmed, not a retreat. The same pair cuts both ways before a
committee: Layer 2 is NECESSARY (the strength) AND resolution
credit partially belongs to the exemption machinery (the audit's
honest-claim boundary) — the provenance metrics carry that load.

(vi) Program stopped at the pass check per the pre-registered rule;
staged and not run: S1b pilot episodes, M1 coverage session,
free-flow legs, S1a anchor (anchor since authorized and running
separately). Merge state: feat/v3-s1b → integration @a0e2f44 +
docs @d470470, suite zero-delta.

**A16. M3 resolvability fixes + rulings (2026-10-10; integration
@31c8ce0).** Shipped (footprint/dynamic mode only, goldens
byte-identical, suite zero-delta): bearing-axis fallback for
ambiguous passers (tag `dynamic_arms:bearing_lane`), yield handover
to a lane-aligned facing partner for ambiguous yielders
(`heading_regrounded`), partner retry when the kept yielder has no
executable retreat — infeasible backup OR failed sweep OR infeasible
escort (`yield_robot=sweep_regrounded`, 37/8 occurrences
S1b/S1a), honest refusals with true reasons everywhere
(`ambiguous_refused`, `parallel_refused`; zero fabricated 0.00 m on
the ambiguous branch), and `refusal_no_action` extended to withhold
the empty-waypoint reroute fallback (`dispatch_withheld:
empty_reroute`; M2-chosen or declared-detour reroutes still
dispatch). Replay rates: S1b 0.405→0.515, S1a 0.345→0.365; empty
reroutes 124/166→0/0. RULINGS: (i) shared-heading-axis lanes for
side-by-side pairs (+19/+29 yields) REJECTED — raises executed-path
robot conflicts; (ii) node-handoff occupants stay EXCLUDED from the
retry (would be 0.55) — the arriver-yields/occupant-passes semantic
is registered and not traded for rate; (iii) NEW GUARD RULED: the
crossing view requires a DECLARED junction in scenario_geometry —
on S1b (none declared) it anchored to S1a's junction and grounded
phantom geometry for 57/400 first conflicts; absent a declaration it
must refuse honestly (fix rides the S1b pilot deploy); (iv) the S1a
anchor runs on pre-A16 M3 — any S1a/S1b floor comparison must use
same-M3 data (re-run the 3 anchor seeds on A16 M3 if the comparison
is ever confirmatory). Residuals carried (pre-existing, found not
caused): sweep follows the lane axis while M4 backs along heading
(18–27° off → up to 0.7 m drift); room-gate swap checks no heading;
lane yields with an away-facing yielder still ground; model-proposed
plan yield legs are room-checked without the partner retry (echo
emits no plan — live plans WILL hit this). All A16 behavior is
offline-replay-verified only; closed-loop verification belongs to
the S1b pilot.
**A16(v) COORDINATED RULING (both sessions, 2026-10-10): the
plan-leg/derived-path retry asymmetry is a provenance-fairness
defect (audit-R2 class) and MUST be fixed before any live S1b
episode with the plan channel on.** Model-proposed plan yield legs
failing room checks that the derived path retries around would
differentially convert would-be vlm_verbatim outcomes into
repaired/m3_default — biasing the distribution the
dispatch-model-order arm exists to measure. Fix shape per the
A13(iii) shared-function principle: plan-leg feasibility calls the
SAME retry logic as the derived path (one function, both provenance
classes, identical treatment); pinned offline by a scripted-plan
fixture whose named yielder fails the sweep while the partner
passes. Cross-reference: A16's honest-refusal package (zero
fabricated 0.00 m) discharges the measurement half of A14(iii); the
remaining A14(iii) residue is only the Step-6 wording.

**A17. Plan-leg parity shipped; bias direction corrected; heading
handover ruled (2026-10-10; integration @aca00de).** A16(v)'s fix
landed with one factual correction: the asymmetry OVER-credited the
plan channel, not under- (pre-fix, a plan naming a sweep-failing
yielder verified `vlm_verbatim` with dispatch_matches_plan=False
while dispatch retried to the partner). Shipped semantics — the
verifier's verdict equals what dispatch does, via the shared
`resolve_yield_roles` call (`_plan_yield_verdict`): retry-success →
`repaired` with exactly one logged swap matching
`yield_robot=sweep_regrounded`; retry-refusal → `m3_default` with
the dispatched waits. MC provenance shift (400 first conflicts):
S1b vb/rep/m3 222/98/80 → 132/95/173; S1a 216/116/68 → 107/54/239;
zero cases move away from dispatch. The model's leg is never
silently rewritten — every change is a logged edit. Scorer fix: the
`plan unrepairable` prefix now maps to `repair_bound_exceeded` in
plan_metrics (round-trip pinned). ADOPTED for the freeze:
`repaired_yield_retry_only` stratum (edits = exactly one swap whose
ids equal the sweep_regrounded pair; precedent repaired_order_only/
parked_only). NEW RULING (same R2 principle): the A16 heading
handover (`heading_regrounded`) produces the identical over-credit
(8+7/400) — the plan verdict must reflect the FULL derived
pipeline's final yielder (view handover included), fixed BEFORE any
plan-channel live episode; echo pilots unaffected. Residuals
carried: refuse-mode/declared-geometry plan legs still get no
backup/sweep/escort check; junction_clear yield-axis sub-plans
don't consult the verdict; a plan naming the partner directly stays
`inconsistent` (contradicts its own yield_robot — registered
behavior); 12+2 MC repaired cases mismatch only on the pre-existing
lane-scoped off-lane cross hold.

**A17-bis (coordinated, 2026-10-10).** Two cross-lineage notes:
(1) the "only post-A17 vb is load-bearing" rule has a REGISTERED
v1/v2 mirror — `verbatim_dispatch_matched` (added 2026-10-06 against
gpt-4o's trivially-verbatim plans) — so BOTH lineages headline
vb∧dispatch_matched, never raw vb; the thesis states the invariant
once. (2) FREEZE-TIME FAMILY RULE proposed for the repair strata
(now three: repaired_order_only, repaired_parked_only,
repaired_yield_retry_only): any mechanically-separable repair cause
gets its own stratum — defined once as a rule rather than
enumerated ad hoc.

**A18. Verdict identity rule shipped; residual map final
(2026-10-10; integration @72151a6).** The A17 heading-handover fix
landed as an IDENTITY rule — the verdict fires whenever the full
derived pipeline's final yielder differs from the robot a consistent
plan must name (shared `_resolve_yield_outcome`, extracted verbatim
from the default-plan builder; any future re-grounding layer is
covered automatically). SCOPE EXPANSION ACCEPTED: node-handoff and
rear re-groundings are corrected by the same rule (S1b +1 vb→rep,
+6 repaired-yielder corrections; S1a +1). CORRECTION to A17's
figures: the true heading over-credit was 6/400 S1b and 0/400 S1a
(the 8+7 counted tags, including handover-then-retry-refusals
A16(v) already scored correctly). Final MC split: S1b 126/101/173,
S1a 106/55/239; zero moves away from dispatch-match. Composed
handover+retry-success is structurally impossible (the retry's only
partner is the handed-from robot, which fails backup_follows_retreat
— 0/800 carry both tags). STRATUM RULED: rename to
`repaired_regrounding_only` with per-layer sub-counts (view: heading
/rear/node-handoff; retry: sweep) — one stratum, the A17-bis family
rule applied; the room gate's `yield_robot=regrounded:` stays
outside (different tag grammar, different mechanism).
RESIDUAL MAP (post-fix, ranked), with the defusing note that the
A17-bis headline invariant (vb∧dispatch_matched, never raw vb)
already prevents these from inflating CLAIMS — they matter for
repair attribution and the dispatch-order arm:
(1) OFF-LANE CROSS HOLD — plan gives `cross` to a lane_scoped robot
dispatch holds; never checked (S1a 36/106 vb mismatch; size is
script-dependent). RULED: fix before any plan-channel LIVE episode,
as a repair (substitute cross→wait, one edit, separable) — same
gate as the A16(v)/A17 chain, lower urgency than they were because
the invariant defangs claim inflation.
(2) Non-retry refusals stay verdict-free BY DESIGN (dispatch
waits-all, plan keeps its yield → mismatched vb/repaired; J1
no-passer + same-side classes, ~13-25/floor) — carried, invariant
covers claims.
(3) The verdict's one hole: it reads the default-plan derivation,
which disagrees with dispatch in 6-7/400 per floor (predates this
change; mostly node-handoff + multi-passer nearest-first) —
"verdict = dispatch" is exact except there; carried with sizes.
(4) Declared-geometry/refuse-mode plan legs and junction_clear
yield-axis sub-plans remain outside the verdict (registered);
a plan naming the handed-over partner directly stays
`inconsistent` (under-credit, registered).

**A19. S1a anchor complete; first task-stream resolution; exemption
scope ruled (2026-10-10; report 2026-10-10-s1a-anchor.md; integration
@56836a4 lineage).** 3/3 anchor episodes (seeds 3-5, H=300, echo,
pre-A16 deployed tree). COMBINED ANCHOR ROW (n=6): time-to-gridlock
median 60.8 rel-s (24.6–338.2; E2-condition n=4 median 31.6), first
encounter median 17.64 (14.44–19.17), outcomes 3 partial/3 gridlock,
every episode ends in permanent latch clusters; no spontaneous latch
self-free anywhere — the one transient latch was cleared BY a yield.
MILESTONE: A1 holds the FIRST closed-loop resolution event in
task-stream traffic (executed yield 32ce6702: gate_admit 55.6 →
release 100.6 on the 45 sim-s backstop → 2 tasks, gridlock delayed
to 147.1). Seed variance is order-of-magnitude — single-episode
gridlock comparisons are UNINFORMATIVE (cell design note).
NEW RULING — latch-aware exemption scope: a dispatched clearing
command is futile when the yielder is latched to a THIRD robot (A2:
pair-scoped exemption r1+r5 while r1 was latched to r2 → zero
motion, FAILED ~15 s). During a clearing command's window the
yielder must be exempted against ALL its latch partners (the 0.20 m
hard-contact floor remains the backstop); fix rides the S1b pilot
deploy. LIVE CONFIRMATIONS: the dispatched-fallback loop at full
cadence (A3: 12 near-identical reroute+wait dispatches to horizon,
each cancelling held Nav2 goals — the already-merged
empty_reroute_fallback withhold @31c8ce0 targets exactly this; A3
is its named regression scenario); escort_turn_cap live-exercised
(2.485→1.558 m). BOOKKEEPING: censoring caveat (ep1's 338.2
gridlock and ~282 wedge self-free would be right-censored at
H=300); the s1b report's ep1 first-encounter 20.5 is corrected to
19.17 by the committed stats script (append-only note); anchor ran
on the pre-A16 M3 per the A16(iv) caveat. OPS: the new VM's clock
lags ~1 day — STAMP dates on it read 2026-10-09; join runs by run
id, never by STAMP date.

**A20. S1b pilot 1: zero events, three ruling artifacts identified
(2026-10-10; report 2026-10-10-s1b-pilot.md; integration @47fde2d).**
Both echo episodes refused everything (13/13 withheld, 0 dispatches,
0 events). Diagnosis — all three causes are apparatus/ruling
artifacts, not floor physics: (1) E1's 8/8 = the A16(iii) crossing
guard, correctly blocking S1a-phantom geometry but exposing that
S1b DECLARES NO real crossings; counterfactual: ungated, E1's one
"executable" yield would have grounded on the phantom box — the
guard did its job. RULED: S1b's overlay declares its REAL crossing
boxes, measured from its own island-corner geometry (build item).
(2) E2's 5/5 = ambiguous handoff arriver at 33° (3° past the snap).
RULED: an ambiguous ARRIVER yields along ITS OWN HEADING (retreat
axis = heading; the footprint sweep runs along that axis — M4
natively backs along heading, so this is the physically consistent
conversion the A16 snap-widening rejection does not forbid), capped
at 45° with the sweep as guard. (3) Echo names the lowest-id
stalled robot — often latch-free and dwelling (82/400 MC). RULED
(apparatus): echo prefers members of an engaged latch pair for
involved/yielder. POSITIVES: A3 regression PASS on the new tree
(13/12 hammer → 3/1, suppression armed, gridlock 24.6→62.9 — and
the empty-reroute withhold now has NO live regression scene, noted);
A19 exemption fixture flipped (one-sided waiver, frozen partner
set); free-flow 18/18 (median 0.176 m/s — MC's 0.15 assumption is
conservative, legs ~0.85×); M1 coverage 24/25 (marker 2 @Wp 0.874,
one 8.3 s static STALE burst — recheck next pass). CARRIED NEW:
backup-into-moving-traffic (A3-rerun: grounded yield backed into a
parallel-track robot 0.34 m off the line — the latch caught it;
sweep-vs-moving-traffic is a Step 6 design question, not patched
ad hoc); five-stack bring-up aborts 3/11 (raise
NAV2_LAUNCH_STAGGER_SEC next wave). CORRECTION to A19's ops note:
the "VM clock lags ~1 day" is a timezone artifact (VM on UTC, Mac
UTC+7) — join by run id stands, the lag claim is withdrawn. MC
prediction for the two live seeds was 1 event/2 episodes; seed 2
lost it to a 0.5 s arrival-order flip — single-pilot event counts
carry seed noise (cell-design note, echoing A19's variance warning).

**A21. Churn ruling (owner choice iii, 2026-10-10): measure first,
bound later from data.** E3's phenomenon is CLASSIFIED: family S1
(emergent), configuration = S6-class dual-conflict (two simultaneous
latch clusters, self-formed in traffic), dynamics =
coordination-level LIVELOCK (the Layer-2 analogue of the reciprocal
dance: the coordinator alternates interventions between conflict
groups — state changes, no progress), outcome class = the registered
`intermittent` (first live specimen). E3 is thereby empirical
motivation for S6's addresses-both oracle: serial pairwise
intervention on a multi-conflict scene can oscillate indefinitely;
a scene-wide plan has nothing to alternate between.
CROSS-CITATION (coordinated): A19's "no spontaneous latch self-free
anywhere" across the n=6 anchor is the strongest corroboration of
A15(ii)'s passing-does-not-exist conclusion — the two entries cite
each other; and A19's all-partners exemption scope is structurally
sound on safety-invariant grounds precisely because the A9-era
0.20 m hard-contact floor remains the un-exempted limit beneath it.
RULED (iii): (a) MEASURE NOW — intermittent classification for S1
episodes + churn metrics (dispatches per latch-break, alternation
count, resolution-time share), zero behavior change; (b) BOUND
LATER — per-cluster dispatch budget + alternation-aware loop
detector built DEFAULT-OFF, parameter values frozen only after
churn data exists (target: p95 of productive-resolution counts),
enabled per registered cell; (c) the attribution test is a LIVE
episode — E3's oscillation arose under the echo's naive yielder
choice, so architecture-churn vs apparatus-churn separates only
with a real model. Consequence: the LAST pre-plan-live gate (A18's
off-lane cross hold: plan cross leg on a lane_scoped held robot →
substitute cross→wait, one edit) is built in this wave, clearing
the first live S1b episode WITH the plan channel on. Minor
apparatus fixes ride along: echo names ONE cluster (the closest),
refusal text names the 45° cap when the cap is what refused.

**A22. First live S1b episode; S6-in-S1 answered; batch ruled
(2026-10-10; report 2026-10-10-churn-and-first-live.md; integration
@d7dae79).** E6 (ER-2, plan channel ON — all pre-live gates closed):
5 analyses, 0 refusals, churn_class RESOLVED (alternation 0), two
productive resolutions incl. S1b's FIRST clearance-released yield
(model named r4, M3 swapped to r2 — repaired∧matched — executed
end-to-end), 4/25 tasks, gridlock 173.2 rel-s, ~$0.034. ANSWERS:
(i) S6-in-S1 = NO — the model named ONE cluster in all 5 analyses
and no plan addressed both (S6's reason-to-exist now has live
evidence); (ii) churn attribution INDETERMINATE by the
pre-registered opportunity rule (max 2 clearing dispatches into one
cluster vs required ≥3) — provisional direction: no livelock under
a real model, and the corrected echo did not reproduce E3 either;
(iii) first field vb∧dispatch_matched: 1/5 analyses, 1/3 dispatched
(vb 1/rep 2/m3 2; the one mismatch is the known A18 residual-2, not
a parity failure). PARITY COMPLETE at MC level: after the off-lane
hold fix (cross/continue on lane_scoped held robots → substitute
wait, stratum repaired_lane_scope_only), vb-mismatched = 0/400 on
BOTH floors; final vb∧matched S1a 0.3775, S1b 0.455. NEW APPARATUS
FINDING (E5): the one-cluster echo STARVES — it re-names the same
unresolvable pair while suppression holds the scene, and the second
cluster is never analysed; RULED: the echo rotates to the next
engaged pair after a refusal on the current one (apparatus-only).
RULINGS/DEFERRALS: junction_clear on S1b = OUT OF SCOPE (extends
A11(ii); its junction geometry is unsolved there — the model's one
junction_clear fell to a 0.00-m legacy refusal, withheld); composed
repairs (regrounding swap + lane-scope substitutes, sitting at the
bound of 4) get a `repair_bound_pressure` flag and an A17-bis
family-rule extension (strata compose as a multiset of separable
causes) — final wording at Step 6 with data; MC is REGISTERED as an
upper bound for live yield probability (0/5 live first-conflict
yields vs 4/5 predicted across pilots); churn-bound values still
unfreezable (productive counts: A1=1, E6=2). OWNER-APPROVED NEXT:
echo-rotation fix + a 3–5 episode LIVE batch (~$0.10–0.17) to power
the attribution rule, accumulate productive-resolution counts for
the A21 bound, and replace MC with empirical event rates. Bring-up
remains the infra sore spot (2/4 aborts at stagger 6).

**A23. Live batch closed (2026-10-11; report s1b-live-batch Rev 2;
integration @dfe4e49).** Four live episodes ran (E6-E8, E10 censored
at 123.5 sim-s by credit exhaustion); E9/E11 never ran (3 bring-up
aborts each). FINAL AGGREGATES: (a) churn attribution INDETERMINATE
by the opportunity rule (0/4 episodes reached ≥3 clearing dispatches
into one cluster) — but 0 alternations anywhere; the provisional
direction (no livelock under a real model) stands unrefuted;
(b) productive resolutions [2,0,0,1*]; all-episode p95 = 2;
dispatches-per-productive-event p95 = 2 — STILL TOO THIN to freeze
budget_k; (c) live first-conflict yield 0/4 (CI 0-0.60) vs MC 2/4 —
the MC-is-upper-bound registration is reconfirmed; (d) wandering vs
park UNDECIDED (one finisher ever; 0/21 occupied-node arrivals
involved a finisher); (e) cost median $0.0281/episode, batch total
$0.107 incl. E6. E7-OVERTURN QUANTIFIED: both clusters named in
2/15 valid live analyses (2/8 two-cluster scenes); a scene-wide plan
dispatched verbatim∧matched ONCE (E7) — real but rare; the S6
rationale stands WITH the nuance that the capability exists
unprompted at low frequency. NEW RULING (apparatus/pipeline): a
backend failure (decision=None) must arm the scene-unchanged
suppression (outcome backend_failed) — E10's dead-backend 402 loop
re-analysed every ~3 sim-s until MAX_ANALYSES(40); fix rides the
next wave. INFRA ESCALATION: five-stack bring-up aborts 9/16 (0.56)
across the stagger-6 era, abort class now includes planner_server
bond timeouts — stagger tuning is NOT the fix; a dedicated bring-up
investigation (sequential lifecycle bring-up or per-stack
retry-with-backoff) is REGISTERED as the next infra wave; until
fixed it is the dominant wall-clock cost of every S1 wave.
BLOCKER: Gemini prepaid credits DEPLETED 20:13Z 2026-10-10 (HTTP 402)
— no live ER-2 until the owner tops up; OpenAI credit state unknown
(exhausted 09-25, possibly topped up before the 10-06 pilot). All
live-dependent items (attribution n, budget_k freeze, yield-rate CI,
wandering) are PAUSED on billing, not on engineering.
A23 CORRIGENDUM (2026-10-11): a direct 1-token probe of
gemini-robotics-er-2-preview returned HTTP 200 (serviceTier
standard) — credits are WORKING again (cycle refresh or untracked
top-up); the billing blocker is lifted and live work is unblocked.

**A24. Bring-up solved; E11 ruled; V-JEPA pilot closed
(2026-10-11; reports bringup-and-resume, s1b-live-batch Rev 3,
vjepa-probe-pilot; integration @4be1d84).**
(i) BRING-UP: all five-stack aborts share a launch-overlap signature
(bond timeouts at the moment another stack launches; get_state during
concurrent configure; GUI autorun exonerated; timeout bumps ruled out
— the Jazzy bond wait is a hard 2 s and get_state has no parameter).
FIX: NAV2_BRINGUP_MODE=sequential (harness-only; stack k+1 waits for
k active + health check). Validation 0/8 vs parallel 9/20 (Fisher
p≈0.024); cost +21 s/attempt, M5 starts ~6 sim-s later. RULED:
sequential is the DEFAULT for all S1 run lines.
(ii) backend_failed suppression shipped (E10's 402 loop replays
38→2); trade-off recorded: a transient backend failure on a frozen
scene silences re-analysis until the scene moves.
(iii) E11 RULED: NOT citable as architecture-churn — the opportunity
precondition is unmet (annotation degenerates to "1 of 0"), zero
alternations, and both "unproductive" labels are window-attribution
artifacts (r4 reached S immediately after r5's clearing reverse;
credited to neither event). PREDICATE FIX registered: progress by
any robot of the dispatched cluster within the window — including
arrivals enabled by the cleared path — counts productive; and the
architecture-churn verdict henceforth requires BOTH the ≥3-dispatch
opportunity bar AND ≥1 alternation. Pooled verdict stands:
no livelock evidence under a real model (0 alternations across 6
live episodes).
(iv) AGGREGATES (E6-E11): first-conflict yield 0/6 (CI 0-0.46) vs
MC 3/6; productive p95=2 (budget_k still unfreezable); both-clusters
2/31 analyses, scene-wide plan dispatched once (E7); cost median
$0.031/ep, all-live total $0.227. E12 skipped on the $0.04 budget
floor.
(v) V-JEPA PILOT CLOSED (side branch feat/v3-vjepa-probe, unmerged):
verdict "a paragraph, not a table" — the frozen V-JEPA 2 probe's
13/13 + 12/12 on mapped battery items is matched by a single-frame
control on conflict and does not transfer (held-out 0.53 vs a
classical closest-approach rule's 0.83). SHARPENED INSIGHT for the
thesis: gpt-4o's temporal failure is NOT missing pixel information
(status colour alone scores 11/12) — it is a REASONING/inversion
failure. H-JEPA assessment verdict (a) is now empirically confirmed
on our own data (with state available, video adds no forecasting
value at this scale). Future-protocol note: a meaningful
encoder-vs-VLM test needs raw unannotated recordings (recorder
change) + an arrow/colour-free condition.

**A25. Batch 2: escalation class ruled; no-admit yield defect is
the registered mystery (2026-10-12; reports live-batch2 + Rev 4;
integration @cd35ae1).**
(i) DISCLOSURE: batch spent $0.2568 vs the $0.25 cap (one call over;
cost_watch checks post-billing). FIX RULED: caps reserve one
estimated call. All-live spend $0.4840.
(ii) Predicate fix landed exactly as designed: ONE label flipped
(E11 c417cbff → productive via released-robot credit; E11 class →
resolved, verdict → INDETERMINATE); E3 remains the only ARCH episode
(echo). 27 tests, zero-delta.
(iii) NEW CLASS RULED — ESCALATION: intermittent + opportunity bar
met + 0 alternations (E13/E16/E17). It is neither ARCH-livelock
(no oscillation) nor an apparatus artifact (real model, real
grounding): the coordinator persistently retries different
strategies on the SAME blocking cluster. The livelock question is
now answered more strongly: 0 alternations across 23 live clearing
dispatches — oscillation was the echo's disease (cites A21/A24).
(iv) THE REGISTERED MYSTERY: 6/9 dispatched live yields ran ACTIVE
191-294 s then FAILED with NO gate_admit, while all 3 admitted
yields COMPLETED. This single defect plausibly suppresses the yield
rate (1/12 live vs MC 7/12), starves the productive distribution
(budget_k bar unmet: 5/24 nonzero vs the pre-registered ≥8), and
manufactures ESCALATION episodes. RULED: diagnose the six no-admit
bundles OFFLINE before buying more live episodes — the cheapest
path to budget_k runs through this fix, not through 9-18 more
episodes. Reference-only triple (3, 130 s, 0) recorded, explicitly
undefendable at n=6 events.
(v) Updates: both-clusters naming 12/36 in batch 2 (14/67 pooled,
E17 alone 7 — scene-wide attention is commoner than the E6-era
read); E17 best live episode (9/25 tasks, censored by the cap);
sequential bring-up 6/6 first-attempt, pooled 0/14 vs parallel 9/20
— the A24 fix holds at batch scale; backend_failed suppression still
unexercised live; wandering-vs-park still undecided (1 finisher,
0/33).

**A26. No-admit mystery resolved: two mechanisms; shield ruled
(2026-10-12; report no-admit-diagnosis; integration @0f9d423).**
The 6 no-admit yield failures split cleanly: MECHANISM A (2 cases,
FIXED) — M3 checked retreats along the snapped lane axis while M4
backed along the robot's own heading (18-23° off → 0.42-0.62 m path
miss → island contact); fix mirrors the escort pattern
(backup_facing/reference keys, dynamic-footprint-only, ≤45° turns,
declared-mode byte-identical) — controller replay on all 9 real
yields lands ≤0.031 m from M3's target and island contact
disappears. The passer_reference hypothesis was RULED OUT (unset on
all 9 incl. the completers; gate_admit fires at hold start
regardless of the passer). The step time limits that fired are M4's
own motion formulas (backup max(d/0.1·15,30); sidestep
(π/0.5+|L|/0.1)·15). MECHANISM B (4 cases): a semantics gap — M3
checks retreats only against decision-time positions; a moving
bystander enters the retreat mid-maneuver, forming a NEW latch that
A19's command-start waiver does not cover; both robots freeze to
the limit. RULINGS: (i) B1 ADOPTED WITH INTENT — a retreat shield:
grounding holds (unlinked, tagged grounding=retreat_shield:<id>)
any bystander whose current-goal path crosses the active retreat,
with M3 reading M5's task intent through the SAME registry channel
the node-handoff rule already uses; precedent for holding unnamed
robots = the lane-scope waits; config-gated, default-off, S1 cells
only; the intent read is what covers dwelling-robot blockers (E14/
E17b). (ii) B3 ADOPTED as stop-gap: M4 fails fast when the clearing
robot and its blocker share a fresh latch (saves ~150-200 s/event,
earlier failure context). (iii) B2 REJECTED (banning node-adjacent
retreats would refuse most yields by construction). "Admitted ⇒
completed" is recorded as uninformative (the hold timer guarantees
completion; only E6 released on real clearance). Projected effect
of A alone: admits 3/9→5/9; B is the bigger lever (covers both
MC-matched failed yields). Deploy note: A touches live-mounted M3
files AND colcon-built M4 files — rebuild + md5 both.

**A31. E24-E26 escort-filter mini-batch outcome: P1-P4 all PASS;
the one live filter firing dropped a non-default candidate; all
three episodes budget-censored (2026-10-20; report
escort-filter-minibatch Rev 3; integration @d80ee49 = merge of
`feat/v3-escort-live`).** The A30 batch ran as pre-registered on
the A28/A29 runtime with the switch-on overlay
`s1b_dynamic_shield_escort.yaml` (40968886), the 0.20 m floor swap
and every pre/post gate; deploy md5s matched source on all 10
manifest files plus the floor; COND `switch_on = shield_on = 6`
in every episode. HOST CHANGE: an L4 stockout (~57 h) in
asia-southeast1-b moved the batch to the zone-moved snapshot clone
`vgu-thu-base-isaac-vm-asia-northeast1-a` (same disk image,
different physical host and zone; owner-authorized 2026-10-19);
the md5 pins establish software identity only, so the cross-VM
caveat stands. Spend est $0.1395 of $0.15; VM STOPPED after;
pristine `safety.yaml` restored (59839662). The A28/A29 M3/M5
runtime REMAINS DEPLOYED with `escort_park_clearance` default-off,
inert without the overlay. PREDICTIONS: P1 escort clears park
>= 0.45 m — PASS 3/3 non-vacuous (0.575 / 1.730 / 1.036 m); P2 no
GT pair < 0.18 m and zero floor firings — PASS (all-pairs minima
0.404 / 0.338 / 0.323 m, 0 floor, 0 B3); P3 filter fires live —
PASS, one tag `retreat=escort_park_filtered:A:robot_4:0.215` on
E24 `dfb33b91`, dispatched, on a cluster MC never modelled; P4
admitted == dispatched — PASS 3/3, all released by clearance.

| Ep | Dispatched yield (VLM → M3) | Leg clearance | Filter tag | GT closest pair | Productive | est $ |
|---|---|---|---|---|---|---|
| E24 | `dfb33b91` yield r4 → r3 yields for r4, post-filter B | 0.575 m | `A:robot_4:0.215` | r3–r4 0.404 m | 1 | 0.0488 |
| E25 | `c1fd8b36` yield r5 → r1 yields for r5, letter B = label A | 1.730 m | none | r1–r5 0.338 m | 1 | 0.0470 |
| E26 | `cf77ca65` yield r1 → r5 yields for r1, single candidate | 1.036 m | none | r2–r3 0.323 m | 0 (censored) | 0.0437 |

REV 7 vs REV 6 (E6-E26 vs E6-E23; `aggregate_b5.py` reproduces
`agg_b4.json` block-for-block on the prior 18): admitted/dispatched
pooled 11/17 → 14/20, A26+ runtime 8/8 → 11/11; clearance releases
4 → 7 (+ the one E20 contact push); first-conflict yield 5/18 (CI
0.097-0.535) vs MC 12/18 → 6/21 (CI 0.113-0.522) vs MC 15/21;
alternations 0 in 18 → 0 in 21, NO LIVELOCK; productive nonzero
8/30 → 10/33 all-classified (live 7/18 → 9/21); vb∧matched 16 / 13
→ 17 / 14 (shield-excluded / raw); all-live cost $0.7546 over 18 →
$0.8941 over 21. The churn triple stays registered and default-off
(A29), not re-derived.

E24 OFFLINE RE-GROUND (report §9.1; the §9 item 3 measurement).
The recorded inputs of `dfb33b91` replayed on `9a018ca` with the
switch on reproduce the live stage-2 record and dispatched yield
exactly (candidates, letters, listing, parameters, degradations);
no earlier E24 artifact carries a filter tag, so draw index 2
holds. With the switch OFF stage 2 offers 4 candidates: pre-A
(0.022, 1.225) 0.215 m rank 1 (the dropped one), pre-B 0.505 m,
pre-C (0.382, 1.225) 0.575 m rank 0, pre-D 0.865 m. DETERMINISTIC:
the dropped candidate is NOT the default; the switch-off default is
pre-C, the dispatched pose, so a defaulted or failed stage 2 would
have dispatched the identical yield; the live model picked rank 0.
NOT DETERMINISTIC: the stage-2 model's answer to the switch-off
4-mark prompt (letters A→pre-B, B→pre-D, C→pre-A, D→pre-C), so
whether it would have picked the 0.215 m pose is undeterminable
offline. LETTER REPLAY (A29(iii)): the recorded letter B read under
the switch-off lettering grounds pre-D (0.865 m), not A; matched by
pose the live pick is pre-C. The n = 1 firing is no evidence that
the filter averted a contact.

FINDINGS (not predicted). (i) BUDGET CENSORING: all three episodes
were stopped by the $0.05 episode cap at 137 / 174 / 133 of 600
sim-s with 6 analyses each, so the productive scores are weak;
E26's yield released 23.7 sim-s before the cut. OWNER DECISION
NEEDED: raise the episode cap for the next live cells, or accept
cap-censored productive scoring. (ii) MC-PREDICTED TAGS DID NOT
FIRE: neither the s25 (`A:robot_5:0.126`) nor the s26
(`B:robot_3:0.179`) tag fired. E25 had MC's pair and yielder at
about MC's time but grounded through the dynamic crossing view
with a 1.169 m escort against MC's 1.95 m leg; MC records no
grounding-view tags, so the cause is NOT ISOLATED (the §1.6 MC
caveat). E26's first conflict on MC's pair was a `reverse`
dispatched as waits. Recorded; no ruling. (iii) E26 RE-LATCH: the
escorted passer r1 and its parked yielder r5 re-latched at 0.433 m
GT about 3 sim-s after the clearance release and stayed latched to
the cut (no contact) — another admitted, unproductive yield after
E21 and E22 (A28(iii)), and budget-censored. Recorded, not ruled. (iv)
BRING-UP ABORTS ON THE NEW HOST: 2 of 5 attempts (E24 f1 robot_1,
E25 f1 robot_3 not active 120 s after launch), both $0, both
retries succeeded; pooled sequential aborts 1/21 → 3/26. OWNER
DECISION NEEDED: watch as a host effect, or lengthen the
per-robot active timeout. Still open from the report: whether
`escort_park_clearance` becomes the default in shield cells
(n = 1 live firing, which by the re-ground changed no default);
shield and B3 still unexercised live (shield armed on all 18
artifacts, no hold placed).

**A30. A29(i) closed: one filtered retreat selection for every
reader; kept-yielder swap trigger stays unfiltered; next = switch-on
overlay + mini-batch E24-E26 (2026-10-17; integration @5fbec0f =
merge of `feat/v3-filter-parity`).** The escort/park filter now runs
ONCE in `command_grounder.prepare_filtered_retreat_selection`; the
two per-call-site applications are removed. Dispatch, stage 2
(`retreat_stage2._run`), `shadow_classical.classical_retreat_answer`,
the plan verifier (`_derived_reroute_reason(escort_park=True)` →
`_plan_yield_verdict` reroute branch) and the junction yield phases
all read that selection with the grounder's `goal_references`;
dropped candidates persist only in `escort_park_filtered`. The
verifier certifies a no-survivor yield as a legitimate
yield→reroute degradation (E20 `f269ab37`: `m3_default`,
`dispatch_matches_plan` True; was `vlm_verbatim` + mismatch). A15(iv)
swap: the PARTNER side treats zero survivors as no executable
retreat (same as a sweep-empty partner) — with the switch ON this
turns the S1 `s1a/s1b_sweep_regrounded_exec` cases from
partner-reroute into a certified wait fan-out; the KEPT-YIELDER
trigger stays UNFILTERED (RULING, owner 2026-10-17: filtering it
would turn `f269ab37` from A29's recorded reroute into a wait
fan-out; not adopted before the mini-batch). Switch OFF is
byte-identical to 6ce2b92 on all eight fixtures (golden
`tests/unit/data/a29_filter_parity/golden_off.json`, written before
the code change). Suite 62/6812/153/3, same 65 failing ids. Still
open, non-blocking: A29(ii) stage-2 record omits dropped
candidates; A29(iii) replay kits must map letters through
`escort_park_filtered`; production shadow still grounds on declared
geometry without goal refs (Arm B parity question, unchanged).
RULING (owner 2026-10-17): proceed to a PRE-REGISTERED mini-batch
E24-E26 on the A28/A29 runtime with a NEW overlay grounding file
that sets `escort_park_clearance: true` and re-enables the shield
config's escort leg (A28(ii) carry-forward lifted by A29/A30);
pinned grounding files unchanged; 0.20 m floor swap + pre/post arm
gates mandatory (A28(i)); budget cap $0.15, start floor $0.04,
per-episode cap $0.05; predictions to be frozen in the report's §1
before any live call, including: P1 every dispatched yield's
escort leg clears its park point by >= 0.45 m (sweep on the
dispatched command); P2 zero GT contacts and zero floor firings;
P3 at least one `retreat=escort_park_filtered` tag fires live;
P4 admitted/dispatched stays >= batch-4 rate. VM must be started
for this batch and STOPPED after it.

**A29. A28(ii) escort/park fix landed as CANDIDATE FILTERING;
churn-bound option sweep; lineage pushed (2026-10-16; integration
@6ce2b92 = merge of `feat/v3-escort-park`; churn sweep
`data/logs/vm_runs/batch4/churn_options/REPORT.md`).** The rule
"escort leg clears the parked partner's park point by >= 0.45 m"
was first built as a post-selection veto of the chosen yield
(`reasoning/rag/escort_clearance.py`: point-to-segment distance from
(retreat_x_m, retreat_y_m) to each passer's escort leg, mirroring
M4's heading incl. turn cap and the odometry release distance).
Offline re-grounding showed the blanket veto rejects yields that
were SAFE live, because the default pull-off lateral is 0.36 m:
E20 `f269ab37` 0.447 m, E6 0.438 m, E17a/b 0.235/0.208 m, the
canonical declared head-on 0.360 m; only the E20 contact `6cf402ed`
(0.131 m) was the target, and in that scene candidates B/C cleared
by 0.589/0.949 m — only the model's pick A hit the park point.
RULING (owner, 2026-10-16): the rule moves to candidate filtering
BEFORE stage 2 (`command_grounder.filter_escort_park_candidates`,
also applied in `retreat_stage2._run`, which now receives the
grounder's `goal_references` so both sides letter identically);
violating candidates are dropped and survivors re-letter A.. in
rank order (the existing sweep-veto precedent,
`retreat_candidates.reletter_candidates`); the yield is infeasible
(`yield=infeasible:escort_hits_park:<passer>:<m>` → reroute
fallback) only when NO candidate survives; the post-selection check
stays as a backstop. Provenance: `retreat=escort_park_filtered:
<label>:<passer>:<m>` per dropped candidate (cause None) plus
`RetreatSelection.escort_park_filtered`. Everything sits behind
`GroundingParams.escort_park_clearance` (default OFF, absent from
params dumps when off); pinned grounding files unchanged
(rag e18c723c, s1b_dynamic 535f5281, s1b_dynamic_shield ee5fe68f).
Fixture outcomes with the switch ON: E20 `6cf402ed` A dropped,
B/C survive, grounds; E21 `04457772` and E23 `9803bd34` keep their
live pose; E6/E10/E13/E14/E15 each lose a sub-0.45 candidate and
keep a 0.53–0.92 m one; E20 `f269ab37`, E17a, E17b and the
declared head-on are STILL VETOED (no candidate clears 0.45 m) —
accepted as the rule applied as stated, recorded as a known cost.
Suite 62/6772/153/3, same 65 failing ids (+34 new tests, −7
superseded veto tests). OPEN before any live cell enables the
switch: (i) `shadow_classical`, the plan verifier
(`_derived_yield_degrades_to_reroute`) and the A15(iv) swap read
the UNFILTERED selection, so certification/shadow can disagree
with dispatch when the switch is on — must be reconciled first;
(ii) stage-2 records do not list dropped candidates (provenance
only in degradations); (iii) a replayed live letter now denotes a
different pose (E20 live "A" grounds old B) — replay kits must
map through `escort_park_filtered`. Escort leg of the shield
config stays OFF until (i) lands (A28(ii) carried forward).

CHURN-BOUND SWEEP (offline replay, same 30 classified episodes as
A28, first-order withholds). Baseline 3/130/0 reproduced (0
productive withheld; E3 2 by alternation; A3 6 by budget). Grid
budget_k {2,3,4,5} × window {90,130,200,300,∞}: only k=2 with
window >= 130 withholds a productive event (E17 `9cf93ebe`); k=3
with window >= 200 withholds one unproductive live dispatch; every
grid point still catches E3; A3 is lost at k >= 4 with window 90.
The two halves catch different failures: alternation_max=0 is
load-bearing for E3 (dispatches 38–77 s apart never trip the
budget), budget alone catches A3 (12 dispatches, no alternation);
raising alternation_max to 1 loses E3. Leave-one-out: budget_k ∈
{2,3} (set by the single E17 event; the triple derived without E17
is (2,130,0) and withholds E17 itself), window ∈ {90,130} (set by
the single E6 gap; 90 never withholds a productive event, only
weakens the catch). Per-cell enablement at 3/130/0: S1a-only
withholds A3 6; S1b (incl. shield) withholds E3 2; shield-only 0;
all 30 → 8; NO option withholds a productive event and NO option
changes any of the 18 live episodes (0 real-model alternations
ever). RULING: triple (3,130,0) stays REGISTERED and DEFAULT-OFF
in every cell; no k=4 ruling is opened (it adds margin but is not
what the registered procedure yields); re-derive budget_k when
~20 productive events exist, when the nearest-rank p95 stops
being the maximum.

LINEAGE: `feat/v3-integration` f6598e6 and `feat/v3-design`
d54e19b pushed to origin 2026-10-16 (first remote copies);
`feat/prereg-v2-composite` dd5f93c and `prereg-v1-hotfix` 3988524
fast-forwarded on origin. VM `vgu-vgu-thu-base-isaac-workstation-vm`
found TERMINATED 2026-10-16; next start must re-apply the 0.20 m
floor swap before any S1b live cell (A28(i)).

**A28. Mini-batch E21-E23: triple derived (3/130/0); E20
clearance-release corrigendum (2026-10-12; report
shield-fix-and-minibatch; integration @f6598e6).** All four A27
rulings landed: de-exemption (M3 tags `retreat_shield_hold`; M4
drops those robots from `admitted_partners` in every phase; A19's
command-start waiver treats a shielded robot as a bystander so a
standing latch cannot freeze the yielder before B3 can fire), the
0.20 m floor as a per-run install swap (`safety_floor020.yaml`,
byte-identical to IB10's c41913f0) with pre/post arm gates, the B3
structured log line, and the shielded-excluded vb∧matched reading
(reproduces batch 3's 3 raw / 5 excluded). Suite 62/6708/153/3,
same 65 failing ids. E18 replay fixture: under the new command the
yielder latches at the first scene inside 0.45 m and B3 fires; the
floor ALONE would not have caught E18 (0.231 m > 0.20) — the
de-exemption is load-bearing. Mini-batch: 3/3 dispatched yields
admitted, 2 clearance releases (E21, E23), zero contacts, zero
floor/B3 firings, one productive event (E23, the 8th nonzero
episode), spend $0.1069 of $0.15. P1/P2/P4 pass; P3 partially
untested — no live B3 opportunity arose, so latch→B3 evidence
remains replay-only (recorded, not citable as live). TRIPLE
DERIVED at the ≥8 bar: budget_k=3 (p95 of [1,1,1,1,1,2,2,2,3]),
window_sim_sec=130 (max of 79.3 s latency p95 and the 122.6 s E6
gap, rounded up), alternation_max=0; ChurnLedger replay over all
30 classified episodes withholds no productive event and withholds
in E3 (2) and A3 (6) as designed; equals the reference-only
triple. RULING: the triple is REGISTERED as the frozen bound
values but the bound stays DEFAULT-OFF per A21(iii); per-cell
enablement is a future owner call; fragility disclosed (budget_k's
single 3 and the window's single 122.6 s gap each rest on one
observation in 9).

CORRIGENDUM to A26/A27 and the batch-3 report: E20 release
`6cf402ed` was a CONTACT, not a clearance release. The escorted
passer r3 drove into the parked yielder r1 on an escort line 0.14 m
off its park point; GT distance fell below 0.18 m from 251.8 sim-s
(minimum 0.109 m) and both robots stayed frozen to episode end.
Batch-3 clearance releases read 2→1; A27's "TWO released by real
passer clearance" reads ONE. It was not a productive event, so
budget_k and the triple are unaffected (checked). This is the
first live contact on the A26 runtime and was caught by the
distance-recompute policy (fc73151 lineage) at the pre-arm gate.
RULINGS: (i) the E20 class (clearing pair: escort into parked
yielder) is NOT covered by A27 de-exemption — clearing pairs keep
their exemption by design — but IS backstopped by the 0.20 floor
(0.109 < 0.20): the floor swap + mandatory pre/post arm gates are
therefore required in EVERY future S1b live cell, shield or not;
the pinned install default stays 59839662 and no config selector
is built for now. (ii) Escort grounding must clear a parked
partner's park point by at least the 0.45 m latch radius; queued
as the next integration fix with its own fixture set — the escort
leg of the shield config stays OFF until it lands. (iii) Admitted
≠ productive recorded as a metric distinction (E21 and E22 each
had an admitted, unproductive yield). VM state: pristine
safety.yaml restored; the box is NOT shield-ready without
re-applying the swap; rule-16 pre-registration lives in VM NOTES.

**A27. Batch 3: admits 5/5; shield safety ruled; budget_k one
short (2026-10-12; report shield-and-batch3 + Rev 5; integration
@c08904a).** The A26 stack's first live outing: admitted/dispatched
5/5 (vs 3/9 pre-A26), TWO clearance releases (only E6 ever before),
E20 8/25 tasks, first-conflict yield 3/15 (CI 0.043-0.481) vs MC
10/15. The shield met all five required fixtures with NO E16
special case (the discriminator is the PIN RULE: a robot mutually
pinned with a non-command robot is never shielded) and needed a
SECOND intent leg (next task node + remaining dwell via
TaskStreamTracker.departure — no A25 blocker was actually dwelling
at decision time). RULINGS: (i) E18's near-pass (shielded robot
drifted 0.70 m during the M2 call; yielder passed at 0.23 m centres)
— shield-only robots are REMOVED from the clearing exemption
(option b): they are not clearing agents; a too-close hold now
latches and B3 fast-fails — honest refusal-by-physics; PLUS the
0.20 m hard-contact floor is ENABLED in S1 shield cells (its A9
backstop role); option (a) predictive re-check recorded as optional
refinement. The shield stays OFF until this lands. (ii) E21 +
seeds 22-23 form the next PRE-REGISTERED mini-batch (the agent's
floor-discipline stop is endorsed; n_more=3 puts the ≥8 budget_k
bar in reach — the triple is derived in that batch if met).
(iii) B3 gains a structured log line before any measured citation
(one live firing so far, inferred from timing). (iv) vb∧matched is
READ with shielded robots excluded (lane-scope precedent; raw
count co-reported) — batch 3: 3 raw / 5 excluded. Over-holds
(5/10 fixtures, ~6/7 live) accepted as recorded cost. Rev 5:
livelock still ZERO under the real model (5 opportunity episodes,
0 alternations/15); both-clusters 14/89; wandering undecided
(1 finisher, 0/41); cost median $0.0335/ep, all-live $0.6477.

**A14 corrigendum (2026-10-09).** A14(iv)'s "GT
robot_static_contacts logged 0 rows during a physical pin" implied
an under-detecting detector. The truth is stronger:
acceptance_logging.py:99 HARD-CODES the field to [] on every
lineage — it never could log any static contact. The docs-lineage
caveat (fc73151) states it that way; v3 scorers must treat the
field as a stub, not a measurement, until a real detector ships.

**A7. Step 0 status note.** The merged tree's rotation-probe
signature PASSED (0/142 closed columns vs 12–13 pre-fix). The stage-1
smoke failure was on an OFF-DESIGN route (goals routing around the
blocker — no scored cell does); the acceptance smoke was re-defined
to the cell's REGISTERED goals and the off-design "north-grind"
behavior (box-face hugging at 0.038 m under clearing:true) is
tracked as a named finding relevant to Step 1's detour family.
Re-baseline stages 2–5 run on tip `071f9c1`-lineage with
orchestrator.yaml held at the VM-pinned md5 (new keys are default-off
Pydantic fields).
