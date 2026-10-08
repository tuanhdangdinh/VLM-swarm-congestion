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
