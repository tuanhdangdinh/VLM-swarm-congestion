# Prereg-v2 Design — Composite Command, Loop Map, Visual Urgency

**Prepared:** 2026-09-30

**Revision history:**

- Rev 6 (2026-10-01): round-2 literature integration (`reports/VLM
  coordination recent advances.md`): claims 2/4/5 narrowed against
  four <4-month-old concurrent papers (GAVEL, Physical Agentic AI,
  SyncPlan, Seeing-Saying-Solving) while claims 1/3 stand; provenance
  term confirmed free (RoCo Table 2 re-plan counts = nearest kin);
  new "Prompt apparatus" subsection (adopt: metric grid,
  reasoning-first JSON, permutation voting, mirror-flip diagnostic;
  A/B: multi-frame/trails/schematic/zoom; prohibit: spatial text-CoT,
  VLM self-verifier); new "Statistics and reporting" section (paired
  McNemar/Wilson/clustered SEs, KM+RMST for censoring, prereg-claim
  phrasing, nondeterminism caveats, cost Pareto); reading gates moved
  to the v2 freeze checklist; timing note (concurrent-work framing
  decays — freeze v2 promptly after v1 collection).
- Rev 5 (2026-10-01): literature-review integration (user: "from those
  findings what can improve the v2"; review at `reports/VLM centralized
  multi robot coordination.md` + four note files). New "Positioning and
  claims" section (4 claims / 3 refusals / verification debts);
  plan-stability naming (Fox et al. 2006) and the registered
  provenance-conditioned outcome analysis; supersessions labeled
  incremental vs wholesale (persistent-plan articulation gap); the
  marked-choice rule for all spatial selections (SoM/MOKA);
  Arm B citation pedigree (zone-control + AIM-FCFS + A-DRIVE);
  per-backend capability-probe battery; robot-count scope bound (≤5);
  claim-1 camera wording + optional physical-camera episode (owner
  decision).
- Rev 4 (2026-10-01): USER DIRECTION — the architecture is named and
  completed as a **Centralized Multi-Agent Coordinator (VLM)**: new
  leading section defines the coordinator role; (a0) plans become
  scene-wide (every tracked robot gets a leg) with a plan lifecycle
  (`plan_id`, plan-state prompt block generalizing failure-context,
  explicit supersession, M5 plan tracking); plan-stability metrics
  registered; multi-conflict scenes recorded as an explicit
  include/exclude call at the v2 freeze (recommended: v3).
- Rev 3 (2026-10-01): USER DIRECTION — `proposed_plan` generalized from
  a `junction_clear`-only field to a strategy- and scenario-agnostic
  channel: new top-level section "(a0) Universal `proposed_plan`
  channel" owns the schema, the verify/repair contract, and the
  plan-quality metrics (now scored on **every** v2 decision, with
  oracle-order agreement wherever a cell defines a ground-truth
  order); section (a) keeps only the junction-specific constraints.
- Rev 2 (2026-10-01): USER DIRECTION — the composite command gains a
  VLM-emitted `proposed_plan` channel (propose-verify): the VLM may emit
  the full ordered action list, M3 audits and minimally repairs it
  rather than authoring the sequence outright, and plan agreement /
  edit distance / executed-plan provenance become registered metrics.
  Rewrites section (a)'s "Decision contract" and "Scoring"; the rev-1
  single-token contract survives as the degradation path.
- Rev 1 (2026-09-30): initial design, written immediately after the
  `prereg-v1` checkpoint tag, from the prereg-v2 registry (design spec
  rev 9.5 "Prereg-v2 registry", amendments item 30), the intersection
  resolvability study
  (`docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`),
  the unified scene design (`3b3a529`), and the two literature reviews
  (`reports/Four way intersection robot congestion.md`,
  `reports/Congestion scenario coverage check.md`).

**Status:** DESIGN — nothing here is built. The v2 freeze happens only
after v1 collection completes and this design survives its own smokes.

---

## Relationship to prereg-v1 (discipline rules)

1. **v1 collection runs from the `prereg-v1` tag.** Every confirmatory
   episode is collected from the tagged tree with the frozen config md5s.
   v2 development proceeds on a separate branch
   (`feat/prereg-v2-composite`) cut from the tag; it never merges into
   the collection tree until collection is complete.
2. **No v1-frozen artifact changes.** Prompts (`prompt_v1.py`, builder,
   stage-2), Arm B rules, oracles, scenario YAMLs in the v1 battery, and
   the two pinned configs are frozen. A v2 build that would touch one of
   them (the Arm B same-axis filter, below, is the known case) lands
   only on the v2 branch; if a defect in a frozen artifact is found
   during collection, that is a protocol deviation logged in the
   amendments doc, not a silent fix.
3. **v2 scoring is registered before v2 collection**, same as v1: this
   document grows the oracle tables and criteria before any scored
   episode runs, and pilots used to size or debug are excluded from
   confirmatory counts.

---

## What v2 measures that v1 cannot

| Gap in v1 | v2 instrument |
|---|---|
| Four-way jam is classification-only (T1-X); no architecture on earth in our survey commands recovery from a formed scrum | (a) composite recede-then-yield → (d) resolution-scored IB10 |
| Whether the VLM can *sequence* a multi-robot resolution (vs only name the situation) is unmeasured in v1 | (a0) universal `proposed_plan` propose-verify channel, scored on every v2 decision in every scenario (rev 3) |
| The VLM is invoked as a per-conflict consultant; whether it can *hold and revise* a coordination plan over an episode is unmeasured | VLM Coordinator contract (rev 4): scene-wide plans, plan lifecycle with execution-status feedback, plan-stability metrics |
| `reroute` is a no-op re-send on the single-aisle map, so wait-vs-detour judgment is untestable | (b) loop map with a genuine alternative path |
| B2 urgency rides a text label (`priority` field); the visual channel is untested for urgency | (c) loaded-vs-empty prop pair |
| B3 scores only the ordered outcome; who *initiates* the slip is unobserved | (e) B3 first-to-slip variant (Rev 17: "B3 first-to-slip to v2") |

The headline claim v2 targets is the citation gap both literature
reports record: **no published system performs centralized commanded
recovery from a formed multi-robot scrum.** (a)+(d) is that system;
everything else is supporting coverage.

---

## The VLM Coordinator (rev 4)

v2's architectural identity, per user direction: **the VLM is the
Centralized Multi-Agent Coordinator — a congestion-resolution
planner** — not a per-conflict consultant. The module roles under this
framing:

- **M2 (VLM)** plans: it owns the scene-wide resolution plan, sees its
  own active plan and that plan's execution status on every
  invocation, and may revise it.
- **M3** verifies: every plan is audited leg-by-leg and minimally
  repaired against geometric feasibility (the (a0) contract).
- **M5** executes the plan as a tracked object: each dispatched
  command carries the `plan_id` it serves; plan state (per-leg
  `pending/active/done/failed`) is M5's, and is what M2 is shown.
- **M4** remains the safety authority — a plan never overrides an
  invariant.
- **Arm B** is the classical coordinator run through the identical
  contract, so "VLM coordination vs classical coordination" is the
  experiment's headline comparison, phrased at the plan level.

What this adds concretely to rev 3 (all owned by (a0) below):

1. **Scene-wide scope.** A consistent plan assigns every tracked robot
   a leg; robots not involved in the resolution get `continue`. The
   plan is a complete coordination statement, not a conflict-pair
   excerpt.
2. **Plan lifecycle.** Plans are versioned (`plan_id`, monotonic). The
   prompt's failure-context block generalizes to a **plan-state
   block**: the active plan, each leg's execution status, and what
   changed since the last invocation. A new plan explicitly supersedes
   the active one; M5 cancels superseded legs in dependency order
   (reusing the ordered-release machinery) rather than blindly.
3. **Re-planning as measured behavior.** Plan-stability metrics
   (below): replan count per episode, churn (legs changed between
   consecutive plans), and whether each revision follows a leg
   `failed` status (evidence-driven) or none (dithering). The
   trigger cadence itself is unchanged — stall-triggered plus
   completion re-checks, as shipped — so stability is attributable to
   the model, not to a new scheduler.

**Multi-conflict scenes** (two simultaneous congestion events in one
plan) are the coordinator's full generality, but every v1/v2 battery
scene is single-conflict, and a multi-conflict scene is a fresh
scenario-engineering effort (natural host: two head-ons on the loop
map's two aisles). Recorded as an explicit include/exclude call at the
v2 freeze; **recommendation: exclude, first v3 item** — the
coordinator *contract* is fully testable single-conflict.

---

## Positioning and claims (rev 5, from the 2026-10-01 literature review)

Source: `reports/VLM centralized multi robot coordination.md` (+ four
note files in `research_notes/VLM centralized multi robot
coordination/`). The architecture is **CMAS at the semantic layer**
(Chen et al., arXiv:2309.15943); adopt the field's vocabulary for
discoverability: CMAS, fast–slow (dual-system) architecture,
event-triggered high-level replanning, plan stability.

**Claims v2 is designed to support** (each with its nearest prior to
differentiate):

1. **VLM coordinator on an overhead warehouse camera with a semantic
   strategy taxonomy** — vs Garg et al. (arXiv:2404.06413 / PMLR 2026:
   simulation, synthetic top-views, leader+waypoints, no taxonomy),
   Oxford CCTV (arXiv:2606.06762: real cameras, deliberately non-VLM),
   and — CARVE-OUT added 2026-10-04 from the user's paper folder
   (`research_notes/VLM planner coordinator recent work/
   user_paper_folder_review.md`) — SwarmVLM (arXiv:2508.07814:
   ceiling-camera VLM+RAG in a warehouse, but the VLM only
   feature-extracts obstacles for a six-row impedance-parameter
   lookup — no congestion classification, no strategy selection, no
   plans, no robot–robot conflict, n=2 leader–follower; cite its
   ImpedanceGPT/HetSwarm lineage as the orthogonal
   "VLM-tunes-control-parameters" family).
   WORDING CONSTRAINT: our frames are Isaac-rendered through the real
   M1 pipeline on a hardware-validated scenario family — phrase as
   such; "real physical camera" is claimable only if the optional
   physical-camera episode below runs.
2. **(NARROWED rev 6)** **Three-way per-leg provenance
   (verbatim/repaired/defaulted) as a first-class reported metric,
   with deterministic minimal repair of multi-robot congestion
   plans** — the repair-harness idea alone is now concurrent work:
   GAVEL (arXiv:2609.19315, Sep 2026, deterministic graph-world-model
   repair, single-robot) and Physical Agentic AI (arXiv:2608.22657,
   Aug 2026, per-dispatch deterministic gating of a multi-robot LLM
   plan with step-level fault stats) must be cited as such. What
   remains unclaimed (verified by deep-reads): the preserved-fraction
   trichotomy itself — Garg executes VLM JSON with zero verification
   or repair anywhere; LLMDR delegates validity to PIBT by
   construction; RoCo's Table 2 re-plan counts (e.g. 3.5 attempts,
   Pack Grocery) are the nearest kin — whole-plan *rejection
   iterations*, not per-leg *preserved fraction*; the AV/shielding
   vocabulary sweep (disengagement per-mile, shield intervention
   per-action, CBF activation per-cycle) found no equivalent. Framed
   as *plan stability (Fox, Gerevini, Long, Serina, ICAPS 2006)
   transplanted to the VLM-proposer setting*.
3. **Matched two-arm comparison**: central VLM congestion resolver vs
   a literature-grounded rule-based coordinator on identical Nav2
   warehouse scenarios — no published head-to-head exists (recheck
   held 2026-10-01). Cite Seeing-Saying-Solving (arXiv:2505.13376,
   decentralized warehouse conflict recovery with TL verification)
   as the decentralized cousin; Virtual Traffic Lights
   (arXiv:2511.07811) as live validation of Arm B's family.
4. **(NARROWED rev 6)** **Scene-wide ordered plan output,
   audited-and-repaired leg-by-leg with logged provenance** —
   audit-and-REFUSE now exists (Physical Agentic AI);
   audit-and-repair-with-provenance does not. Also vs
   leader+waypoints (Garg) and priority hints (LLMDR,
   arXiv:2503.00717).
5. **(NARROWED rev 6)** **Persistent central plan with minimal
   in-place edits, embodied (Nav2), integrated with provenance** —
   SyncPlan (arXiv:2608.01652, Aug 2026) now has a persistent central
   LLM plan with staleness-triggered correction and execution
   feedback, but in game environments, replan-not-edit, no
   embodiment; cite as concurrent work. Closed-loop robot systems
   still re-propose wholesale (COHERENT) or intervene per-event
   (Garg, LLMDR). Measured via the supersession label below.

**Claims to refuse** (prior art is immediate): centralized/commanded
deadlock recovery per se (A-DRIVE, LLMDR, Garg); the fast/slow rate
split or ~1 Hz central cadence (RHCR, VLM-UDMC, VLMLight);
LLM-vs-classical comparison in general; propose-verify over
multi-robot motion as such (RoCo) — the differentiator is *who
repairs and whether it is logged*.

**Arm B citation pedigree** (anti-strawman defense, recorded for the
paper): conflict detection ≈ zone-control circular-wait tests; yielder
selection = FCFS per Dresner & Stone's AIM (JAIR 2008); commanded
retreat ≈ A-DRIVE's detect-and-back-up (IV 2022). Arm B is a
literature-grounded representative of the classical family.

**Capability-probe battery (registered, pre-collection):** one cheap
per-backend probe set, run once per model before v2 collection and
frozen with the battery — locate-robot-by-id, left-vs-right of
aisle, robot count, nearest-first ordering — on project frames.
Rationale: Garg et al. pre-test model capabilities before trusting
them; probe results make plan-metric failures attributable to
measured primitive deficits rather than speculation.
CITATION CORRECTION (2026-10-04, from the baseline run's primary-text
check): the earlier "left/right near chance (LRR-Bench)" wording
OVERSTATED the paper — LRR-Bench's basic Position task has GPT-4o at
78–80% (humans 95); the near-chance/near-zero results are its
composite-position and 3D movement/rotation tasks; the previously
quoted 55.33% figure is unsourced in the paper and is withdrawn.
BASELINE RESULTS (2026-10-04, freeze-citable:
`docs/reports/2026-10-04-capability-probe-results.md`; manifest
`9659782d…`, prompt `b1af71e8…`): ER-2 60/60; gpt-4o 58/60 (both
misses near-centreline left_right), 0/60 refusals both backends,
no robot-id or first-slot prior visible in nearest_first (0/8 wrong
robot_1 picks). INTERPRETATION BOUND: the battery is at ceiling on
clean, filtered frames — it certifies primitives ≥~80% there and
cannot rank backends; it says nothing about crowded congestion-onset
frames. Visual primitives are therefore NOT the measured bottleneck;
plan-level failures must be attributed upstream of perception.

**Battery v2 — predictive/temporal probes (registered 2026-10-04,
from the user-folder review; SocialNav-SUB arXiv:2509.08757 is the
benchmark kin to cite):** the static battery is at ceiling and static
primitives are not the bottleneck, so a SECOND frozen manifest
(`manifest_v2`, separate from v1 for comparability) adds GT-derivable
DYNAMIC items on project frames: motion-direction ("which robot is
moving toward X"), conflict prediction ("will A and B come within
0.5 m in the next 10 s"), and temporal order ("which robot reached
the standoff first") — every answer machine-derived from ground
truth, seeded multiple-choice lettering, same auditor discipline.
These measure the motion-integration and conflict-prediction
reasoning that congestion detection and planning actually require —
the headroom above the v1 ceiling. Fresh mock VM runs may harvest
mid-motion frames+GT where logged frames lack dynamic moments; a
trails-on frame subset is harvested in the same runs so the battery
can compare the same question on trails-on vs trails-off frames.

**Trails = amortized temporal context (reframed 2026-10-04):** the
motion-trail overlay is the inference-time analog of ContextVLA's
amortized multi-frame context (arXiv:2510.04246; convergent evidence
CronusVLA 2506.19816, NaVid 2402.15852): history compressed into one
image at zero extra tokens. The frame A/B becomes a three-way —
single frame vs trails (amortized history) vs 2–3 keyframes (raw
history) — directly testing whether amortization captures what raw
frames provide.

**Battery v2 RESULTS + RULINGS (2026-10-05,
`docs/reports/2026-10-04-battery-v2-results.md`; manifest_v2
`faf1953b…`, 139 items, ~$0.70):**
- THE CEILING BROKE WHERE REGISTERED: `conflict_prediction`
  separates the backends — ER-2 16/20 vs gpt-4o 9/20 (at chance);
  gpt-4o also returned refusals on dynamic frames (6/139 + 24
  temporal abstentions; v1 static was 0/60) and shows a systematic
  temporal INVERSION (picks the later robot 13/15 when it answers).
  ER-2 is measurably stronger on dynamic scene reasoning.
- QUARANTINE: `temporal_order` scores are NOT capability scores —
  triply confounded (robot-id prior 15/19, lagging status colour
  23/30, wide event spacing) and missing the M1-agreement filter;
  correctly not rebuilt post-hoc. `motion_direction` is confounded
  by M1's own heading arrow (statically readable; ER-2 35/35
  ceiling).
- REGISTERED v2.1 FIXES (build when probes next run): manifest
  rebuild for temporal_order with the M1-agreement filter, id-prior
  counterbalancing, and tighter event spacing; an arrow-suppressed
  M1 overlay flag so motion_direction tests motion integration
  rather than arrow reading.
- TRAILS NULL (weak evidence): no gain in 40 matched pairs per
  backend (McNemar p=1.0 / 0.69) — but the frozen probe prompt
  carries no trail-convention sentence, arrows already encode
  motion, and n is 11–15 per type. The deployed-prompt three-way
  A/B (single vs trails vs keyframes) STAYS registered; the
  probe-level null does not test it. The keyframes arm needs a
  multi-image probe path (not yet built).
- RATIFIED: the three builder rules fixed pre-call (exact-geometry
  edge gate; yes-exclusion window asymmetry; reachability filter
  for "no" items) — all documented with candidate-level counts.

**Layer-2-off pilot (registered 2026-10-06, PILOT — excluded from
confirmatory counts):** small-sample no-intervention arm — the
decision layer answers no-congestion throughout (mock, zero
dispatches verified), Nav2 + M4 safety only — on head-on s42, B1
s42, B3 s42, IB10 s42. Measures outcome_class, arrivals, and
delay_vs_free_flow against the same cells' intervened episodes: the
on-our-geometry quantification of "the reactive layer alone does not
resolve congestion" (Marcolino-2017 / Garg low-level-only
precedents). If results match expectation (latch/clog), the full
no-intervention ARM is registered into collection; if any cell
self-resolves, that is a design finding for the oracle (the cell may
not need Layer 2) and goes to the owner before collection.

**Model-wiring RESULTS + RULINGS (2026-10-06,
`docs/reports/2026-10-06-model-wiring.md`):** Qwen3-VL-8B VALIDATED
to the full standard (probes 57/60 — CI-overlapping the frontier
baselines; co-resides with Isaac at 10.1/24.6 GB peak; multi-image
passes; $0 API) and gpt-5.1 to the pilot standard (probes 54/60
with a robot_count weakness + an all-"A" miss pattern; head-on:
VLM_VERBATIM yield plan, resolved, best-yet delay 143.8 s; ZERO
refusals — the 4o refusal profile did NOT carry over on static
frames, dynamics untested). Sonnet 5.5 and DeepSeek are WIRED +
unit-tested, live-blocked on missing keys (user supplies
ANTHROPIC_API_KEY / DEEPSEEK_API_KEY). RULINGS:
(1) the Sonnet arm's attempt/fallback config is set to PARITY with
the other hosted arms (4 attempts + grey-image fallback) —
comparability over conservatism;
(2) DeepSeek RE-PINNED to the live successor (`deepseek-flash`,
V4.1-Flash — the requested -exp ID is retired and served by
V4.1; image budget is now ≤1024 tokens/image, so the 384-token
compression question is OBSOLETE — update the exploratory-arm
notes; verify the serving name against the live listing at run);
(3) Qwen's plan-emission rate of 0/17 is a MEASURED MODEL PROPERTY,
not a defect: NO per-model prompt forks (the scenario-agnostic
single prompt is the design); the arm legitimately exercises the
m3_default path, and emission rate is exactly what metric (i-a)
measures;
(4) comparison caveat recorded: pilot rows ran v3.2, new rows
v3.3 — gpt-5.1's verbatim cannot be credited model-only; v3.3 is
the single prompt for everything from here. OPTIONAL follow-up
noted, not ordered: battery v2 (dynamics) on qwen + gpt-5.1
(~$0.35) — conflict_prediction is the type that separates
backends, and neither new arm has been tested on it.

**Battery manifest audit CAVEAT + second trails null (2026-10-06,
fork-session pilot; report `docs/reports/2026-10-06-trail-on-pilot.md`,
adopted file-only — the fork's branch carries the whole v2 lineage
from an old base and is NOT merged into this docs branch):**
(1) APPEND-ONLY CAVEAT on the battery manifests' audit claim: for
the 8 decision frames with full-rate M1 history, the M1 state that
DREW the annotated frame lies 0.20 s before to 0.23 s after the
decision record's scene stamp (M5 pairs frame and scene within a
skew bound) — so manifest_v1/v2's "exact M1 state" pairing and the
0.1 s GT gate were applied at the wrong stamp for those items. The
manifest audit claim must carry this caveat in any confirmatory
citation; fold the stamp fix into the registered battery-v2.1
rebuild. (2) TRAILS: second probe-level null (trails-on vs off on
the 59 frozen v2 items, every backend × type |net| ≤ 1, rule fixed
pre-call) — the fork rules NO v3 trail arm at the current 3 s
window; the deployed-prompt three-way frame A/B stays registered
but is DOWNGRADED to run only if collection's own data motivates
it (two nulls now stand against it, both probe-level).

**Model-wiring ruling (2026-10-06, from the landscape round —
`research_notes/VLM model landscape 2026/`):** WIRE NOW
`claude-sonnet-5-5` (existing Anthropic adapter; MUST omit
temperature — 400s on current gen, recorded `unsupported_sampling`
per the ER-2 precedent — and classify HTTP-200
`stop_reason:"refusal"` as a refusal outcome) and **Qwen3-VL-8B**
Q4_K_M via the existing llama_server adapter (official GGUF +
mmproj; smoke gates: multi-image under llama-server, and L4 VRAM
co-residency with Isaac verified by nvidia-smi headroom before any
joint run). PILOT ARM: `gpt-5.1-2025-11-13` with
`reasoning_effort:"none"` (legal temp-0, no reasoning billing) —
does the 4o refusal/chance profile persist? DEFERRED to v3: Cosmos
Reason2 (8B exceeds the L4; hosted trial-only; vendor-only
evidence). LIFECYCLE FACTS recorded: the `gpt-4o-2024-08-06` pin is
NOT deprecated (safe for v1 collection; the 4o line is winding
down — do not assume into 2027); `gemini-robotics-er-2-preview`
price DOUBLES after 2026-12-31 and preview deprecations get 2-week
notice — both argue for prompt collection. Validation standard for
every new backend: preflight, probe battery v1 (60 items), and two
head-on episodes (seeds 42/43) scored with the standard plan
metrics — directly comparable to the existing baselines.

**Layer-2-off pilot RESULT + ARM REGISTERED (2026-10-06,
`docs/reports/2026-10-06-layer2off-pilot.md`):** expectation HELD —
4/4 cells clogged, 0/13 robots arrived, robots latch 0.27–0.39 m
apart within a second of conflict onset and never separate; 230
analyses fired, zero dispatches (silencing proven). Delay contrast
(censored lower bounds): head-on ≥531 vs 150 s intervened; B3 ≥799
vs 238; IB10 ≥1026 vs 457–503. No self-resolving cell → no oracle
finding. REGISTERED into collection: the NO-INTERVENTION ARM, 35
episodes paired on (scenario, seed) keys against the intervened
arms — 10 each head-on/B3/IB10, 5 for B1 (both arms clog there
until the stage-2 defect is fixed; B1 stays decision-scored);
one layer-2-off episode per key pairs against both backend arms;
McNemar ≈ 0.002/cell at 10/10. Registered caveats: the proximate
cause (M4's 0.45 m stop) is the natural reading but untested (no
run disabled M4); the B3 intervened reference is a scripted
oracle, not a live model. ~13 VM-h, $0.

**Verbatim pilot (registered 2026-10-06, PILOT — excluded from every
confirmatory count, per the standing pilot rule):** a plan-complexity
ladder probing when live plans execute verbatim, on the v2 branch
(NOT the parked v3 fix — pilots must match collection behavior):
ER-2 3× two-robot head-on (2-leg plan shape), 2× B1 bottleneck
(3-robot), 2× IB10 (4-robot junction_clear, replicating the
calibration's repaired-3-edits), 1× single-robot reroute replicate;
gpt-4o 2× head-on + 1× IB10 (first live plans under the stated
grammar for that backend; refusals are data). Measured per episode:
emission, consistency, provenance, edit distance + which legs,
oracle-order agreement PRE-repair, recede-set choice stability
(mirror axis again?), outcome class. Purpose: preview the plan
metrics' live distributions and decide whether the grammar or
invitation needs a final pre-freeze adjustment.

**Verbatim-pilot RESULTS + RULINGS (2026-10-06,
`docs/reports/2026-10-06-verbatim-pilot.md`, 11 episodes, ~$0.33):**
HEADLINES — grammar works: trigger-plan emission AND consistency
11/11 (pre-grammar: 0/3); provenance (triggers) 3 verbatim / 7
repaired / 1 m3_default with NO monotonic complexity trend; ER-2's
repairs are mostly FORMAT (reorders — it lists legs by role
salience, not execution order; 2 plans were reorder-only from
verbatim) and all 3 of its composites needed the same cross→yield
substitution (the gloss never names the yielder); gpt-4o needed 0
reorders but NEVER chose junction_clear (0/13) and clogged IB10
with 11 trivially-verbatim reverse/wait plans — the
verbatim-inflation artifact of unconstrained strategies; ER-2's
recede set is UNSTABLE across episodes (E-W / N-S / all-four);
refusals: ER-2 0/32, gpt-4o 1 recovered /21. RULINGS:
(A) grammar v3.3 re-pin adds ONE line stating the list-order
convention ("the list order is the execution order — the robot
that acts first comes first"), plus a metrics-only
`repaired_order_only` sub-class;
(B) same re-pin extends the junction_clear gloss in-register
("…some robots first back out, one inside robot yields, then an
ordered crossing") — telling the contract, not the answer; the
substitution path stays for models that still omit it;
(C) provenance stays pure; add derived `verbatim_dispatch_matched`
and the registered analysis "provenance conditioned on
strategy-vs-oracle correctness" — the deliberate no-rule for
`reverse` etc. stands, with the inflation artifact documented;
(D) order-agreement scoring excludes robots that can only receive
`continue` (held robots) — definition fix, scorer-side;
(E) IB10 collection uses `prompt_robot_order: random` like every
other cell (the id_asc binding was a calibration artifact; the
recede-set/first-slot confound dies with it);
(G) junction_clear outside IB10 grounds the shipped row and is
TAGGED (the loudness guard worked as designed at B1); whether B1
gets derived junction fields is a v2-freeze decision — until then
the tag is the registered behavior. (F) B1's stage-2 rank-0 2×
defect recurred — already covered by the Rev 20/22 registered
exclusion; both B1 pilot episodes decision-scored only.
RULINGS A–D LANDED (2026-10-06, prompt v3.3, digests recorded in
the builder's version history and
`docs/reports/2026-10-06-verbatim-pilot.md`; +104 chars per pin,
v3.3 baseline `769802f0…`): list-order line + extended
junction_clear gloss; `repaired_order_only`,
`verbatim_dispatch_matched`, `strategy_correct` + the
provenance-by-strategy-correctness tabulation; held robots
excluded from order agreement. Re-derivation over all 28 pilot
plans confirms the intended effects (episodes 2/7 order-only; 6's
agreement no longer false-by-construction; gpt-4o's 11 verbatim
IB10 plans all conditioned out as strategy_incorrect).
RULING (follow-up to C): `accepted_strategies` is registered for
every cell by MECHANICAL DERIVATION from its existing oracle block
(the strategy the oracle's own rationale/fields name — e.g.
head-on family and B1 ⇒ {yield} from `correct_yielder`), never
fresh judgment; the derivation lands with pins at the next scorer
touch and MUST be in place before the v2 freeze so no cell sits in
`strategy_unscored` by omission.
congestion metric (the Arul & Manocha Voronoi-style scalar,
arXiv:2202.11334) into the stage-1 prompt — it IS the congestion
answer and would contaminate RQ1 classification. Permitted only
inside M3/diagnostics, where detection is not being measured.

**Scope bound:** v2 scenes stay at ≤ 5 active robots, justified by the
documented degradation of centralized model planning beyond ~6 agents
(survey arXiv:2502.03814) — a cited boundary, not an apology.

**Foundations round adopted (2026-10-05, `reports/Swarm congestion
foundations.md`):**
- METRIC CITATIONS adopted for the oracle cost tables and scorers:
  time-to-resolution ↔ cluster-dissolution time / jam duration
  (Aguilar Science 2018; arXiv:2403.08683); the censored
  never-resolves outcome ↔ Zuriguel's clogged-state divergence
  criterion (Sci Rep 2014) — retroactively the principled frame for
  T2b's censored margin and `fallback_exhausted`; asymptotic
  throughput (dos Passos, arXiv:2201.09335) where a cell measures
  flow; delay-vs-free-flow via one single-robot free-flow run per
  cell (cheap, registered as a per-cell baseline run at collection).
  METHOD RULED (2026-10-05): free-flow baselines are SOLO-IN-SPACE —
  each robot traverses the course ALONE (per-robot scenario
  variants, own USD builds; blocker cells get blocker-free variants;
  B2-visual r1 covers r2, the load prop is collision-free) — because
  solo-in-time fails in 5/6 v2 cells (swap-scene goals lie past
  other robots' spawns → 0.00 m clearance to the 0.45 m latch;
  per-order table in `docs/reports/2026-10-05-flow-metrics.md`), and
  because free flow in the flow literature means an unobstructed
  course: a parked robot is an obstacle. ONE method for the whole
  table (no B1 solo-in-time mixing). Scorer fields + outcome classes
  (resolved/intermittent/clogged) BUILT 2026-10-05, additive-only;
  pinned calibration passed (step-6 ep2 clogged, step-7b 4/4
  resolved, demo ep2 resolved). TABLE FROZEN (2026-10-05):
  `config/free_flow/free_flow_v1.json` — 22 solo-in-space runs, 8
  cells, 28 entries (priority family covered by measured identity,
  md5-verified maps + collision-free prop); all delays in the
  historical re-score positive, passer < held robots in every IB10
  episode, B1's unobstructed pair within 0.5 s of solo times
  (`docs/reports/2026-10-05-free-flow-table.md`). RULINGS:
  `convoy_counterflow` is COVERED by `convoy_counterflow_slip`'s
  entries (byte-identical geometry, pinned at step 9) — add the
  aliased rows via the generator at the next table touch, never by
  hand (the committed-equals-generated test governs);
  `blocked_path_*` baselines deferred (decision-scored cells, ~25
  min whenever wanted); the stale `--duration-sec` claim in
  t2b_flow_ordering.yaml's header is noted for the next permitted
  touch of that frozen file (the flag is parsed but unused — the
  variant yaml's duration_sec is what stops Isaac).
- TAXONOMY FOOTING: deadlock ↔ circular wait (AGV resource theory) /
  force-equilibrium (Grover, arXiv:1911.09146) / clogged absorbing
  state; bottleneck ↔ intermittent clogging at a constriction;
  `anomaly` has NO flow-physics counterpart — conceded in print. The
  resource-vs-dynamical unification is claimable synthesis.
- SCALE-BRIDGING CHAIN registered as the answer to the small-N
  objection (five verified links, macro transitions → few-body
  arches → tractable N=2–3 → micro-policy sets macro flow → conflict
  conventions eliminate the jammed branch): 2–5-robot structured
  cells are congestion's unit of formation.
- ANCHOR for the architecture premise: Marcolino et al. 2017 —
  reactive avoidance reaches a non-arriving equilibrium — the swarm
  field's own concession that a higher-level mechanism is needed.
- ABSENCE SENTENCE adopted verbatim (no semantic/VLM reasoning in
  the congestion canon; SwarmVLM/ImpedanceGPT carve-out). Strategy
  pedigree: SQF ≈ convoy, TRVF ≈ reroute.
- Pre-camera-ready debts tracked in the report's closing (venue/page
  verifications; ANTS sweep; arXiv:2506.12710 skim).

**`crowding` DROPPED from measured scope (USER DECISION 2026-10-05):**
the type stays in the M2 enum and schema (removing it would churn the
v1-frozen prompt lineage and break classification comparability with
v1 collection), but it is formally OUT of every coverage and accuracy
claim: no battery cell instantiates it, no GT labels it, and a live
`crowding` answer scores as a misclassification against the cell's
registered type. The type-coverage statement for the thesis is:
three measured congestion types + the none control, each with built
and smoked cells — deadlock (head-on family, T2b, B2/B2-visual pairs,
B3 + first-to-slip, T3b), bottleneck (B1, IB10 — the thinnest at two
cells, both v2-scored), anomaly (T3a blocked_path pair, T3c
dynamic_anomaly_v2; loop scenes exist but are do-not-collect) — plus
T0 normal_flow for none. The former token-scale crowding candidate
remains unregistered (rev 9.5 "Not registered here"), now with this
explicit drop on record.

**Optional physical-camera episode (owner decision):** a single
hardware episode (any n, demo-grade) with a physical overhead camera
would upgrade claim 1's wording to "real physical camera." Not
required by the design; recorded so the option is a conscious call.

**Round-3 scan deltas (2026-10-04, `reports/VLM planner coordinator
recent work.md`):** claim 2 WORDING TIGHTENED — GAVEL's eval (read)
quantifies repair-vs-replan only as an ablation (76.2% repair-only vs
91.8% full, 1.00 vs 1.5 LLM attempts), no per-leg or per-failure
tabulation; the claim emphasizes per-leg THREE-way provenance
(incl. defaulted) logged as an experimental quantity + multi-robot +
embodied Nav2 — four axes GAVEL lacks. New concurrent work to cite:
arXiv:2609.27816 (VLM-LLM + reachability gate; ego-camera,
audit-and-REJECT, no congestion, no baseline), DuoMind (2610.02161,
distributed manipulation), Fresh Memory Stale Plans (2609.03340,
persistent-plan currency, non-embodied — claim 5's "embodied"
qualifier holds). MDPI reading gates PARTIALLY CLEARED: both papers
identified (Pesjak & Žabkar MAKE 8(1):22; Peña Narváez et al.
Robotics 15(4):80), both single-robot, full text inaccessible on all
routes — cite as adjacent, never quote internals. EvoPlan GATE
CLOSED (2026-10-04, full 24-page read,
`research_notes/VLM planner coordinator recent work/evoplan_read.md`):
provenance claim UNTOUCHED — EvoPlan's LLM does both proposal and
repair ("invalid plans are demoted by the cascade, not by an LLM
critic"; validators gate, never edit), single-robot, text/symbolic
benchmarks, preprint-only, no code. Its validated-prefix fraction
(Fig. 2) is the nearest published quantity and must be named:
tracks validator acceptance per iteration, NOT per-leg origin — a
leg surviving verbatim and a leg rewritten five times are
indistinguishable in it. TWO TIGHTENED SENTENCES adopted for the
thesis text (full wording in the notes file): the
deterministic-minimal-repair sentence pre-empts EvoPlan's
regex-rewrite and prefix-truncation mechanisms; the no-per-leg-
provenance sentence names and distinguishes Fig. 2. Cite EvoPlan as
the closest propose-verify analogue, contrasted on origin labels /
repair agent / domain. OPTIONAL residual skim (low risk, same
family): GenePlan (2603.09481, ICAPS 2026, LLM-mutation
evolutionary PDDL). Supporting citations
gained: in-prompt grammar > constrained decoding (2505.14763, 7%→23%
vs 98%-semantically-wrong), "missing-step" failure taxonomy (EAI,
NeurIPS 2024) names the no-recede-legs class, Steps-to-Validity
(2508.01300) as nearest plan-scoring kin; axis-mirror errors and
mirror-scoring protocols have NO published analog (ours is a stated
novel choice); metric-grid overlays can HURT some backends — the
apparatus grid ships as a per-backend A/B, not a default.

**Verification debts** (rev 6 status): CLOSED 2026-10-01 by deep-reads
(`research_notes/VLM coordination recent advances/verification_debts.md`)
— Garg/LLMDR/RoCo/Grover extracted with page-level quotes; vocabulary
sweep negative; IDs verified (PIVOT 2402.07872 ✓, SpatialVLM
2401.12168 ✓, GameChat 2503.12333 ✓, SELP = 2409.19471 ICRA 2025,
multi-robot VADER = 2405.16021). One standing caution: Garg's
per-model reach rates exist only as figures — never quote numbers
from them. REMAINING, moved to the v2 freeze checklist: read GAVEL's
evaluation section (a two-way repaired-vs-replanned stat there would
force "three-way, per-leg, multi-robot" wording on claim 2); manually
fetch the two 403-blocked MDPI texts (MAKE 8(1):22, Robotics
15(4):80 — possible plan-preservation statistics); skim DeepFleet
(arXiv:2508.08574); confirm PhAIL's estimator is KM.

**Timing note (rev 6):** the concurrent-work framing for GAVEL /
Physical Agentic AI / SyncPlan is only credible while those papers
are months old — freeze v2 promptly once v1 collection completes.

**Prompt apparatus (rev 6, from the techniques review)**

Adopt as v2 defaults (prompt v3 territory, hash-frozen at the
freeze):

- **Labeled world-frame metric grid** drawn on the annotated frame
  (~1× cost; localization IoU 0.27→0.56 precedent, arXiv:2411.18270)
  — image and state block then share one coordinate language,
  attacking both the left/right weakness and the ignored-geometry
  finding.
- **Reasoning-field-first JSON**: the plan/decision schema opens with
  a bounded free-text reasoning field; strict JSON stays for
  classification fields (premature-serialization effect,
  arXiv:2408.02442 + two-pass recovery evidence).
- **Permutation voting**: 3 cyclic shifts of robot/menu order per
  decision, majority vote (3× API cost — owner-visible tradeoff).
  Cancels the registered first-slot/robot_1 prior per decision
  rather than per dataset, and doubles as the correct test-time
  ensemble at temperature 0 (and on ER-2, which has no temperature
  control). The single-draw condition is retained as an ablation
  cell so the voting gain is itself measured.
- **Mirror-flip consistency diagnostic** (log-only at first): the
  classical layer re-asks a horizontally flipped frame on a
  registered subsample; a yielder choice that fails to invert is
  logged. Own inference, no literature — flagged as such.

A/B-registered cells (each an arm against the single-frame default):
2–3 timestamped keyframes (+17–19pp direction-question precedent,
arXiv:2607.12304); motion-trail overlay baked into one frame (no
literature exists — a free novel measurement, trails are cheap in
M1's annotator); schematic re-render (also the only prompt-level
candidate against the gpt-4o realistic-frame refusals, 0/240
synthetic vs 22–25% live); zoomed congestion-crop tile.

Prohibited, with citations recorded: free-text spatial
chain-of-thought (degrades spatial accuracy across 17 models / 13
benchmarks, arXiv:2604.16060); any VLM self-verifier / best-of-N
self-selection / pairwise tournament (majority voting beats them;
reported verifier gains were a decoding artifact, arXiv:2506.17417,
arXiv:2608.01207) — M3 is the verifier; agentic image-tool loops
(infra cost; pre-rendered manipulations instead).

**Apparatus rulings (2026-10-04, after the wave-1 build + VM smoke;
report `docs/reports/2026-10-04-visual-apparatus.md`):**

- All five flags BUILT and VM-verified (grid recessive/legible, no
  marker occlusion — the 1.4% STALE at 0.149 m separation is the
  known marker-contact mechanism, present in overlays-off
  comparators; detection precedes annotation). Flag-off prompt,
  frame, and request bodies pinned byte-identical.
- VOTE BALLOT RULE (ruling): the majority is taken over DISTINCT
  rendered orders, one ballot each. A duplicated order's calls are
  first reconciled: agreement → one ballot; disagreement → no ballot
  from that order, and the disagreement is recorded as an
  `intra_order_inconsistency` flag — itself a measured quantity (a
  live T=0 same-prompt divergence was observed in the smoke,
  consistent with the registered nondeterminism caveat).
- TIE RULE (REVISED 2026-10-04, superseding the registry-order
  preference): ties go to the EARLIEST tied ballot's representative
  call. Rationale for the revision: the registry order is id_asc —
  the exact rendering the presentation-order finding tied to the
  first-slot/robot_1 priors — so preferring it would resolve every
  two-robot inter-order disagreement toward the biased order,
  reimporting the prior the vote exists to remove. The earliest
  ballot's representative is call 0, the episode's randomized draw:
  unbiased across episodes, deterministic within one. (Abstention
  interpretation ratified: a refused call is not a disagreement; a
  no-surviving-ballot vote dispatches nothing,
  `error_type=permutation_vote_no_ballot`.)
- CANDIDATE-OPTIONS CONTEXT TABLE: ratified as built — options are
  derived from M3's own `_plan_problems` audit under one fixed
  strategy context per action (incl. `reverse` under `junction_clear`
  when arms are declared); options are advisory, free-plan legality
  unchanged.
- `prompt_conditions` on EVERY artifact: ratified (deliberate break
  from add-when-set; condition visibility wins).
- ZOOM FRAMING (ruling): the tile frames the detector's INVOLVED
  set, not only the trigger robot (small follow-up fix).
- GRID × T0 PROBES (ruling): probe artifacts record the frame
  condition; grid-on runs' probes are NOT poolable with grid-off
  probes across cells — a documented comparability bound, since the
  frozen probe prompt cannot mention the grid.
- Trail window stays at the registered 3 s (A/B later if trails
  underperform at low speeds).

**Statistics and reporting (rev 6, from the methodology review)**

- Paired two-arm design keyed on (scenario, seed); McNemar exact
  tests on paired binary outcomes; Wilson CIs on proportions;
  scenario-clustered or bootstrap SEs (Kress-Gazit et al.
  arXiv:2409.09491; Miller arXiv:2411.00640). This exceeds the
  field's median practice (n=10–20, no CIs) — cite, don't apologize.
- Censored episodes: Kaplan–Meier time-to-resolution curves +
  RMST-difference at the horizon with bootstrap CI (Royston &
  Parmar; robotics precedent PhAIL arXiv:2605.29710). Naive means
  over censored runs are documented as biased (47%-censoring /
  3×-length example, arXiv:2605.24756). Applies retroactively in
  phrasing to T2b's censored margin.
- Pre-registration claim: *"we are not aware of any pre-registered
  evaluation of an LLM/VLM robot-coordination system"* — never
  "first pre-registered robotics experiment" (HRI counterexamples,
  arXiv:2309.01822). Option recorded: mirror the git tag to OSF for
  external timestamping.
- Nondeterminism caveats in the paper: temperature 0 is not
  determinism (arXiv:2511.07585); dated snapshots pinned (done at
  v1); report run-date windows and within-cell variance.
- Report dollar cost and latency as system variables (Pareto
  framing, arXiv:2407.01502) — Layer-2 latency couples into
  time-to-resolution here, which most LLM-agent papers cannot say.
- Related-work table situating the battery vs PARTNR,
  LLM-Coordination, Tool-RoCo, CoCoBench: none covers centralized
  VLM warehouse congestion; our metric set (regret, provenance,
  stability) is strictly richer.

---

## (a0) Universal `proposed_plan` channel (rev 3, scene-wide per rev 4)

A single optional field on the **stage-1 response for every strategy
and every scenario**, not a `junction_clear` extra: an ordered list of
`{robot_id, action}` entries that is the VLM's full proposed
resolution sequence. This is the channel that exercises multi-step
spatial reasoning (user direction, revs 2–3), and because it rides
every decision, plan-quality is measured across the whole v2 battery —
head-ons, junction scenes, convoys, and the loop map — not just IB10.

### Schema

- `proposed_plan: list[{robot_id, action}] | null`, Pydantic-validated:
  each robot at most once; unknown robot_ids rejected; list order is
  the proposed execution order.
- **Scene-wide scope (rev 4):** a complete plan assigns every tracked
  robot a leg (`continue` for uninvolved robots). A plan that omits
  robots is **leniently completed** — M3 appends `continue` legs for
  the missing robots, logged as `plan_completed_legs`, not counted as
  a repair — so partial plans degrade gracefully instead of being
  rejected, and omission rate is itself observable.
- **Plan lifecycle (rev 4; amended 2026-10-02 from the integration
  build):** every accepted plan gets a monotonic `plan_id`; dispatched
  commands carry the `plan_id` they serve; the prompt's plan-state
  block shows the active plan with per-leg status
  (`pending/active/done/failed`). A new plan supersedes the active one
  explicitly; supersession cancels the superseded plan's PENDING
  (never-dispatched) legs in dependency order — an in-flight leg runs
  to its terminal status and feeds the next invocation, because M4
  exposes no command-cancel channel and building one is a
  safety-relevant M4 capability registered OUT of v2 scope (the
  measured `cancel_order` and `dispatch_matches_plan` fields make the
  gap visible rather than hidden).
- **Hold semantics (ruling 2026-10-02):** when a new analysis's
  verified plan has legs identical to the active plan's REMAINING
  (non-done) legs, M5 records a HOLD — `plan_id` unchanged,
  `plan_holds` incremented — not a new acceptance. `replan_count`
  counts only genuinely different accepted plans, which is what makes
  the step-4 smoke criterion ("zero unforced replans" on the clean
  two-robot head-on) well-defined: post-resolution re-checks that
  find no congestion accept no plan, and a re-affirmed plan is a
  hold, not churn. The plan-state advice ("revise only for a
  reason") states exactly these semantics. REFINEMENT (2026-10-02,
  from the step-4 smoke): if any leg has reached `failed` since the
  last invocation, an identical re-issue is an **evidence-driven
  replan**, never a hold — a retry is a response to evidence, and
  counting it as a hold would hide exactly the revisions the
  stability metric exists to see. (Implementation lands with step 5.)
- **Probe prompts stay on their frozen version** (v2): T0 probes are
  an RQ1 instrument whose comparability spans v1 collection; a v2 run
  with the plan channel on therefore intentionally mixes prompt v3
  (triggered analyses) with v2 (probes), recorded here so the mix is
  a design fact, not an accident.
- **Action vocabulary = the grounded primitives, nothing else:**
  `yield` (backup + sidestep + hold), `reverse`, `cross` (an ordered
  release slot), `wait` (hold in place), `reroute`, `continue`
  (proceed unchanged). Every legal leg maps to a command M3/M4 can
  already ground and execute; the vocabulary grows only when a
  primitive does.
- **Consistency rule:** the strategy token stays the headline answer
  (classification scoring, Arm B comparability, v1 continuity), and
  the plan must refine it — `yield` ⇒ exactly one `yield` leg,
  `temporary_wait` ⇒ a `wait` leg, `reroute` ⇒ a `reroute` leg,
  `junction_clear` ⇒ at least one `reverse` or `yield`. An
  inconsistent plan is treated as unparseable (reason logged), never
  silently reinterpreted. DECIDED (2026-10-03, VLM-planning review
  item 5): `reverse`, `convoy`, `priority_override` and `none` carry
  NO consistency constraint by design — the spec defines none, and
  inventing one would be reinterpretation; recorded here so the v2
  freeze inherits a decision, not an omission.
- **Grammar-in-prompt rule (2026-10-03 review, fix 1):** prompt v3
  states the plan grammar — action semantics and the per-strategy
  refinement rules above — as ONE scenario-agnostic block rendered
  identically on every v3 decision in every scenario. Rationale: the
  contract is told, the application of it is measured; grading plans
  against unstated rules confounds "cannot sequence" with "was never
  told the grammar" (the live ER-2 plan rejections'
  construct-validity threat). The block never names a scene, a robot
  count, or a preferred strategy.
- **Emission/consistency split (2026-10-03 review, fix 2):** metric
  (i) splits into (i-a) *emission* — a parseable plan was supplied —
  and (i-b) *consistency rate given emission*; declining to plan and
  planning inconsistently are different behaviors, never binned
  together.
- **χ-epsilon verbatim rule (2026-10-03 review, fix 3; RULED same
  day after measurement):** the measurement refuted the
  snapshot-noise framing — within-run χ spread is ≤ 5 mm, while the
  nominally symmetric jam forms with between-run margins up to
  0.142 m; no structural ranking difference (≥ 0.5 per follower) was
  ever observed. RULING = option (b): ε applies to VERIFICATION
  ONLY — dispatch stays in χ order (deterministic, frozen 7b
  machinery untouched) — with `ε = 0.15`, absorbing every observed
  asymmetry and sitting far below the 0.5 smallest structural
  margin; ε must be re-measured for any scene family where follower
  counts differ. The dispatch-match check becomes order-aware with
  an `order_equivalent` flag so a within-ε divergence between the
  verified plan and the dispatched order is RECORDED, never hidden —
  this is what keeps freeze-blocker 1 closed (the recede-SET audit
  stays strict; within-ε order is a defined equivalence class, not
  an unaudited hole). Consequence, per the registered 7b bound
  procedure: with ε, `recede_order_swapped` leaves the defect corpus
  and bound 4 reaches full coverage of the remaining repairable
  cases — the repair bound RE-FREEZES AT 4 (procedure followed, not
  preference).
- **Mirrored-axis composite caveat (2026-10-03 calibration):** ER-2's
  first consistent live plan chose the E-W pair to recede — the
  axis-mirror of the geometry-fixed N-S candidate set. The audit
  scores this `repaired` BY CONVENTION (the mirrored composite is
  unmodeled — no derived pockets/clearances on that axis), not by
  proven infeasibility. Registered as an analysis caveat on IB10
  plan metrics and a v3 candidate (axis-choice freedom).
- **Oracle-order agreement stays gated on `consistent`** (review
  item 3): the registered population is consistent plans;
  inconsistent plans' orders remain recomputable offline for
  exploratory analysis, never for confirmatory counts.

### Verify/repair contract

Division of labor: **the VLM proposes, M3 verifies and minimally
repairs.** This generalizes the v1 swap gate from one robot to a
sequence, keeping the defense filmed in the 2026-09-30 live gpt-4o
demo. Per decision:

- Plan present, consistent, and every leg feasible (retreat room, band
  limits, exemption pairing, ordering executable) → **executed
  verbatim**, provenance `vlm_verbatim`.
- One or more legs infeasible → M3 applies the **minimal repair**
  (swap-style substitutions and reorderings toward its own derived
  plan, fewest edits first), provenance `repaired`, every edit logged
  with its reason (the sequence analogue of `yield_regrounded_reason`).
- Plan absent, unparseable, inconsistent, or repair distance over a
  registered bound → M3's own derived plan executes, provenance
  `m3_default` — which is exactly v1's behavior, so a plan-less answer
  degrades to the shipped pipeline in every scenario.

In two-robot head-ons the machinery reduces to the existing swap gate
(a one-leg plan repair), so v2 changes no v1 outcome semantics there —
it only starts *measuring* what the VLM proposed.

**Repair-semantics rulings (2026-10-02, from the contract-core build;
details in `docs/implementation_notes.md`):** (1) reorder repairs MAY
resolve 3+-robot plan-present scenes that v1's refuse-only ordering
policy would abandon — that capability is this contract's purpose and
v1 (plan-absent) behavior is untouched; (2) equal-cost repair
candidates tie-break TOWARD M3's derived plan, including its yielder
pick (the spec's "toward its own derived plan" made operational —
fixes the two swept cells where a yielder reassignment bypassed the
candidate scan); (3) the engine's `m3_default`/derived-plan path must
be verified equivalent to the SHIPPED derived-mode grounding, not
only legacy mode, before the head-on equivalence smoke counts.

Rationale for optional, not mandatory: the presentation-order study,
ER-2's unused geometry block, and the live demo's infeasible yielder
all say VLM sequencing may be unreliable; propose-verify turns that
reliability into a measured quantity instead of a source of unresolved
episodes, exactly as B1 turned image-dependence into a measured
quantity. Parse/refusal surface grows by one structured field at
temperature 0, with one scenario-agnostic invitation sentence in the
prompt (v3 template, hash-frozen at the v2 freeze).

### Plan-quality metrics (registered, scored on every v2 decision)

- (i-a) *plan emission rate* — a parseable plan was supplied; (i-b)
  *consistency rate* — given emission, the plan refines the strategy
  (split per the 2026-10-03 review, fix 2);
- (ii) *plan agreement rate* — verbatim-executable without repair;
- (iii) *plan edit distance* — repairs applied, with reasons;
- (iv) *executed-plan provenance* — `vlm_verbatim` / `repaired` /
  `m3_default`;
- (v) *oracle-order agreement* — wherever a cell defines a
  ground-truth order, the proposed order is scored against it
  **before** repair: T2b's `correct_order` [robot_1, robot_3], B2's
  priority-first, B3's convoy order, IB10's inside-first. This
  separates "can't sequence feasibly" from "sequences feasibly but
  picks the wrong order" — two different failure stories.
- (vi) *plan stability (rev 4; named for Fox et al., ICAPS 2006,
  per rev 5)* — replan count per episode, churn (legs changed between
  consecutive plans), revision cause: `evidence_driven` (a leg
  reported `failed` since the last invocation) vs `unforced` (nothing
  failed — dithering), and revision type: `incremental` (churn below
  a registered fraction of legs) vs `wholesale` — the measurement
  behind positioning claim 5. A good coordinator revises when
  execution contradicts the plan and otherwise holds it.

**Registered analysis (rev 5): provenance-conditioned outcomes.**
Episode outcome metrics (resolution, time-to-resolution, regret) are
analyzed split by executed-plan provenance (`vlm_verbatim` /
`repaired` / `m3_default`), pre-registered here so the decomposition
is confirmatory, not post-hoc. This is what makes a null result
interpretable: it separates "the VLM proposes well but repair erases
its contribution" from "the VLM's surviving decisions genuinely
outperform the classical arm."

**Marked-choice rule (rev 5):** every spatial selection offered to the
VLM anywhere in v2 is a set-of-mark multiple choice over annotated
options (as stage-2 already does), never a continuous coordinate —
MOKA's principle (arXiv:2403.03174) that VLMs are better at
multiple-choice than at producing continuous locations. (The former
supporting cite "near-chance left/right (LRR-Bench)" is WITHDRAWN per
the 2026-10-04 citation correction — LRR-Bench's basic position task
is 78–80% for GPT-4o; its near-chance results are composite/3D
tasks. The rule stands on MOKA plus the grounding-vs-regression
evidence, e.g. the Mark-Grid point-grounding gains.) In
particular, junction recede pockets are lettered marks, not
positions.

Arm B emits its plan through the identical field, so every metric has
a classical comparator. Condition on presentation order per amendments
A2. These are RQ-level outcomes, not diagnostics: they are the direct
measurement of whether the VLM performs multi-robot sequencing or only
situation naming.

---

## (a) Composite recede-then-yield command

### Decision contract

New M2 strategy enum value **`junction_clear`**, consuming the (a0)
channel with junction-specific validation: a consistent plan names the
recede set (≥ 1 `reverse` or `yield`) and a crossing order for the
rest. The VLM may alternatively emit only the strategy token — M3's
χ-ranked derivation then owns the sequence (`m3_default`), the rev-1
contract.

### Grounding (M3)

- **Cost-ranked recede selection:** χ = s·D_SPACE + t·N_f per A-DRIVE
  ([arXiv:2204.04910](https://arxiv.org/pdf/2204.04910)) — distance to a
  free evacuation pocket plus followers stacked behind. Single yielder
  by default; a two-robot recede (the IB10 cross pair) is a **staggered
  sequential** fallback, never simultaneous.
- **Geometry (from the study's Prereg-v2 Path):** the cross pair
  reverses along its own arms to |y| ≈ 1.2 (legs 0.93–0.95 m from
  ±0.25–0.27), landing in C′'s phase-1 geometry; the E-W yield then runs
  as already tabulated in the study.
- **Sequencing:** remaining robots cross in a per-episode priority
  order, inside-first; the yielder re-enters last. Reuses M4's ordered
  hold-until-last release (`crossing_chain.py`) unchanged.

### Prerequisites (build-order gates)

1. **J2 — junction-scoped backup clearance** (study build list item 1,
   ~10 lines + tests in shared M3). Binding: any N-S pass under the
   shipped `backup_clearance_m: 1.7` ends 0.28–0.45 m outside the
   tracked band and latches permanently for standoff offsets ≤ 0.13 m.
   Nothing else in (a)/(d) is smokeable before J2.
2. **Arm B same-axis filter** (study standing finding 2): waiting robots
   held in-zone from the first buffered frame lead Arm B's intersection
   order, making it inexecutable (escort through the partner at
   0.000 m). Mandatory for Arm B to be a fair v2 comparator. This edits
   a v1-frozen file → v2 branch only.
3. **M1 y-extent verification**: the study flags M1's y detection extent
   as unverified beyond the standoff band; the |y| ≈ 1.2 recede
   endpoints must be confirmed tracked before oracle design.

### Safety (M4)

No new M4 rules expected: `admitted_partners` already pairs a `reverse`
with every member of its own command, so the reverse legs (starting
0.24–0.34 m from the E-W pair) are exempt as-is. The standing
raw-`cmd_vel` obstacle-blindness note (amendments item 25) applies to
the recede legs — the scenario design must keep recede corridors free of
static obstacles, or M4 grows a leg-level check (decide at build time,
default: constrain the scene, not the safety code).

### M5

`junction_clear` dispatch is phased: recede phase (sequential, each leg
confirmed by odometry like `backup()`), then the yield phase, then the
ordered crossing. Failure at any phase falls back to the v1 behavior for
the remaining robots (single yield or no-op) and logs the phase reached
— partial credit is scorable.

### Scoring

- **Resolution-scored IB10** replaces T1-X's RQ1-only scoring: episode
  succeeds when all four robots reach goals, position-verified; phase
  reached is the ordinal partial score.
- **Plan-quality metrics:** per (a0), scored on every decision; IB10
  is simply the cell where the plan is hardest (four robots, two
  phases, inside-first oracle order).
- **Oracle:** correct recede pair by χ; correct order inside-first. The
  C′ caveat (GT oracle inactive at h = 1.2) applies to the *staged*
  variant, not the formed-jam composite — the jam forms first here, so
  `head_on_conflict_active`-style oracles need an intersection
  generalization; registered as design work, sized before freeze.
- **Regret:** extend the forced-strategy harness with `junction_clear`
  forced vs best single-yield forced; the v1 finding that single-yield
  cannot complete at all would make regret a censored feasibility
  contrast, mirroring T2b's cost model.

---

## (b) Loop map

A second E-W aisle plus two N-S connectors creates a cycle: `reroute`
becomes a genuine alternative with a measurable detour cost, not a
re-send.

- **Scene family:** blocker in the primary aisle; the manipulated
  variable is **blocker persistence**, encoded *visually* (prop class:
  fallen box = permanent vs a paused/faulted robot = plausibly
  transient) with no persistence hint in any text channel — B1's
  aperture logic applied to the temporal judgment. Oracle: timed cost of
  wait vs detour per episode; the correct answer flips with persistence
  and detour length.
- **Builds:** USD/map authoring (second aisle), Nav2 map + costmap
  update, M3 reroute grounding to a concrete alternate path (waypoint
  via the far aisle, not a goal re-send), scenario YAMLs, oracle cost
  tables from forced-wait and forced-reroute sweeps.
- **Phase-1 gate: PASS (2026-10-02,
  `docs/reports/2026-10-02-loop-preemption-smoke.md`).** Minimal loop
  built (second aisle at y=1.2, one new east connector, lowered
  connector-flanking racks for camera visibility); with the
  sub-lethal blocker, 0/~200 sampled Nav2 global plans entered the
  second aisle — the detour decision stays with M2/M3. M1 coverage
  on the loop verified (100% fresh, mm-level bias). PROTOCOL
  EXCEPTION recorded: `generate_warehouse_map.py`'s erroneous
  vertical flip (silently mirrored Y-asymmetric map features;
  invisible on all Y-symmetric v1 scenes) fixed on the v2 branch,
  proven a byte-identical no-op for every v1 map, regression-pinned.
  Follow-up check queued for step 9: whether T3b's Y-asymmetric
  static obstacle being absent from its baked map is by design
  (sensor-seen prop) — likely yes, verify when touching props.
- **PHASE-2 OUTCOME — the detour-judgment FAMILY is PROVISIONALLY
  DEFERRED TO v3 (coordinator ruling 2026-10-03, owner may
  override;** `docs/reports/2026-10-03-loop-family-and-visual-pass.md`).
  The phase-1 risk returned at family severity: a gap narrow enough
  to stall the robot (collision stop box 0.24 m) is already past
  the planner's flip point (NavFn direct at 0.30 m, loops at
  0.22 m), so Nav2 self-detours before the decision layer is ever
  asked (3/3 runs) — and the live planner looped even on a clean
  costmap, an UNEXPLAINED mechanism that makes any gap-tuning
  untrustworthy until resolved. Separately, a tracked faulted robot
  cannot be the transient blocker (the 0.45 m latch outranges the
  0.38 m collision stop → permanent latch). Detour length is capped
  by the tracked band, so "lengthen the detour" has no room; shared
  Nav2 param changes are rejected (blast radius over every
  validated scene); a sub-lidar stall box would require physical
  contact (violates the zero-contact invariant); scoring Nav2's own
  detour abandons the RQ. KEPT IN v2: the loop map + builder, M1
  coverage, the map-flip fix, `reroute_waypoints` grounding
  (M4 `follow_waypoints` live path marked UNVALIDATED — watchdog
  failure on first live use), oracle schema + scorer, and both
  family yamls with "do not collect" blocks. v3 prerequisites
  registered: explain the clean-costmap loop; validate
  follow_waypoints; a stall mechanism that is planner-invisible
  without contact.
  UPDATE (2026-10-05,
  `docs/reports/2026-10-05-follow-waypoints-validation.md`):
  `follow_waypoints` EXONERATED — the waypoint pipeline works end to
  end (waypoint 0 reached at 0.054/0.082 m in both validation runs;
  M4 gained log-only leg-progress lines, plain path pinned
  byte-identical). The REAL defect: PHANTOM LETHAL CELLS close the
  0.55 m second aisle in the shared global costmap (up to 16/17
  aisle columns lethal, nothing physically there) → planner failure
  → 0.5 m-tolerance fallback into the remnant corner → DWB
  near-zero-command wedge until the watchdog. Demonstrated
  contributor: `camera_localizer_node` pairs a 0.3–0.45 s-old M1
  pose with LATEST odometry, injecting up to 0.6 rad map→odom yaw
  error during in-place rotations; one closure (≤0.06 rad) is NOT
  explained — second source open. Leading candidate for the
  phase-2 "unexplained clean-costmap loop" above. All fix options
  are SHARED components; NONE APPLIED pending a discriminating
  static-aisle probe — a shared change would require re-validating
  v2-era frozen results (IB10 4/4, free_flow_v1); v1 collection is
  unaffected (runs from the tag). Secondary shared issue noted, not
  chased: the DWB corner wedge frees only on a new goal.
  SOURCE ATTRIBUTED + FIX RULED (2026-10-05,
  `docs/reports/2026-10-05-costmap-source-probe.md` Rev 2): one
  source — camera-localizer registration error (−ω·L, effective lag
  0.14–0.35 s; 66% of closure cells) — one amplifier — the costmap
  NEVER CLEARS (`obstacle_layer.scan.clearing: False`, the unset
  Jazzy default; raytrace 3.0 < obstacle 3.5) — and a geometry
  narrowing (17%) that never closes alone. Static robot: 0 columns
  closed in every phase; fast rotation: 12/17 within seconds;
  replay reproduces the costmap at recall 0.987–0.998. RULING: the
  fix is **A′ + H** (stamp-matched, latency-compensated localizer
  lookup + `clearing: true` with raytrace 3.5 — the only
  combination zeroing closures in both datasets), to be built and
  live-validated on a PARKED v3-prep branch, NOT merged into the v2
  line: no v2 scored cell exercises the defect, v2's frozen results
  are internally consistent under current behavior, and v1
  collection runs from the tag regardless. The parked branch ships
  with its re-validation batch (IB10 composite rerun, free-flow
  spot checks, loop re-smoke) so v3 inherits a proven fix, not a
  patch. CROSS-CUTTING CORRECTION to audit: GT `sim_time_sec` runs
  0.300 s behind ROS stamps — any analysis equating ROS-stamped
  data with ground_truth.jsonl at equal times is biased (two
  reports already corrected; audit the rest, incl. how the
  empirical −0.45 s M1↔GT join offset decomposes).
  FIX VALIDATED + PARKED (2026-10-06,
  `docs/reports/2026-10-05-costmap-fix-validation.md`; branch
  `feat/v3-costmap-fix` @ 0b2e755, local only, NOT merged): A′
  refined by root cause — M1 LOSES the marker for up to 0.6 s
  during fast turns and carries the old pose with a FROZEN stamp;
  the localizer now pairs odometry at the entry's own stamp (M1's
  true latency is ~0.0075 s median, not 0.04–0.20 — those were
  carried-forward rows). ALL validations PASS: rotation closures
  12–13/17 → 0 ×2; DECLARED REROUTE COMPLETES through the second
  aisle ×2 — the reroute gap is CLOSED on this branch; IB10 4/4 +
  yielder-last; free-flow spot checks within ±0.8 s; the loop
  pre-emption conclusion survives. Quantified v3 re-baselines: T3c
  post-removal stall −18.4 s; IB10 last arrival −55.5 s. GT AUDIT:
  NO frozen number moves (self_detour margins 6.4–10.7 s; 0/199
  probe-answer flips), but the GT clock offset is PER-RUN (0.300 s
  single-robot, 0.500 s four-robot — the −0.45 s join offset is
  mostly GT clock, not M1 latency): GT must be offset-fitted per
  run from odometry; 18/41 temporal_order frames fall inside the
  eligibility floor under shift — folded into the registered
  battery-v2.1 rebuild.
- **Risk (retired by the phase-1 gate for its original severity,
  kept for the record):** Nav2
  on a loop map may reroute *on its own* when the global
  costmap sees the blocker, pre-empting the decision layer. Design
  control: blocker placed so the global planner's path stays viable
  (narrowed-not-blocked, below costmap lethal threshold) while transit
  is throttled — the decision to detour must remain M2/M3's. This is
  the first thing the loop-map smoke must verify.

---

## (c) B2-visual urgency pair

v1 B2's `priority` field is read by M3 only and never rendered; v2 adds
the pair where urgency is *only* visual: one robot loaded (pallet prop
via the existing prop machinery), one empty, priority field absent.
Same 2-robot junction geometry, same oracle as B2 (priority robot
passes first). Scored as a modality contrast against the v1 B2 cell:
text-only (v1) vs image-only (v2) urgency. No new prompt version —
the prompt already carries no urgency text in the v2 cell by
construction.

BUILT 2026-10-02 (`priority_visual_r1/_r2`, flush-mounted load prop
with pinned marker/lidar clearances; both members' prompts
byte-identical; no-text pin at grep level). DESIGN NOTE recorded at
build: with no registry priority at all, `priority_override` cannot
ground in this cell (0–0 tie → unsupported); the executable oracle
route is `yield` naming the empty robot — an asymmetry vs v1 B2 that
is the point of the cell (urgency must come from the image), kept.
B3 first-to-slip also BUILT (`convoy_counterflow_slip`, slip-onset =
0.05 m sustained ≥1.0 s after conflict onset, identity + latency
scored; identity degenerate under correct execution, informative
under divergence). T3b map-bake question CLOSED: by design
(timed_obstacles are never baked). VM visual pass is turnkey per the
step-9 report checklist.

---

## (e) B3 first-to-slip

Registered "to v2" at Rev 17. The convoy_counterflow variant where the
scored question is which convoy member initiates the slip (first-to-slip
identity and latency), not just the ordered outcome. Needs only scenario
YAML + oracle additions on the built B3 scene; no contract changes.
Design detail deferred until (a) and (b) are smoked — it shares no
machinery with them.

---

## Explicitly not in v2 (unchanged from rev 9.5)

Multi-conflict scenes (two simultaneous congestion events in one
coordinator plan) carry a recommendation to defer to v3 — see "The VLM
Coordinator"; the v2 freeze makes the explicit call.

**v3 DESIGN DOC exists (2026-10-06):**
`docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (rev 1,
merged from `feat/v3-design` @ 7c69f56) consolidates every v3
registration below plus one addition: the detour family's
stall-vs-plan window must be RE-DERIVED on the fixed stack before
any new stall mechanism is designed (the 0.22/0.30 m NavFn flip
points were measured under phantom-mark inflation and may be
invalid). That doc is the v3 planning surface from here; the blocks
below remain the decision record.
CORRECTION (2026-10-06, from the rev-2 advisor review; doc updated
to rev 2 @ 64fb148): the 0.22/0.30 m NavFn flip points are from a
STANDALONE BAKED-MAP sweep (no live costmap, no localizer, no mark
persistence — loop-family report §Mechanism) and are therefore
FIX-INVARIANT; the sentence above overstated the fix's reach, and
the detour family does NOT revive for free — NO-GO remains the
expected branch, pending an offline sweep refinement and one live
probe of the still-unexplained sim-54.8 live-vs-standalone
discrepancy (phantom marks were only a candidate there and act in
the wrong direction for it).

**v3 candidate registered 2026-10-06 — the MAPD mini-cell (Ghofrani
scenario analog):** a continuous-space analog of the GECCO '25
MAPD setup (Asadi, Nowé, Ghofrani, 10.1145/3712256.3726339: 15×15
grid, ~10% obstacles, 5 task nodes, agents each running a SEQUENCE
of pickup→delivery tasks; congestion emergent from task streams,
handled there by DNN congestion-prediction-and-avoidance, avg
throughput doubling reported). Applying our method at THEIR N=5
sits exactly at our scope bound; their N=10/25 are the scale-probe
rungs. Build cost: M5 task-sequence queues (multi-goal registry,
pop-on-arrival), task-node props, an emergent-congestion scenario
family; our flow metrics already map to their measures (makespan ↔
time-to-full-resolution, throughput ↔ aperture_throughput,
completeness ↔ outcome classes, + delay_vs_free_flow which they
lack). The experiment it enables: prediction-avoidance vs
detection-resolution on the same task streams — the bridge between
the flow-shaping tradition and our event-resolution claim, with
the Layer-2-off arm as the shared control. Natural home: v3,
possibly fused with the multi-conflict item (emergent task-stream
congestion produces simultaneous conflicts for free). The robot-blocker
anomaly, the token-scale crowding scene, and the
three-active-robot B2 junction variant remain unregistered candidates.
The last is structurally impossible under v1 primitives (unified scene
design, B2 section); re-assess only after (a) exists, since
`junction_clear` may make it feasible — recorded here so the v2 freeze
makes an explicit include/exclude call.

---

## Build order

1. J2 + tests (shared M3; v2 branch).
2. Arm B same-axis filter + tests (v2 branch; protocol note that this
   diverges from the v1-frozen Arm B).
3. M1 y-extent verification run at |y| ≈ 1.2 (one VM session, mock).
4. (a0) coordinator contract: plan schema + consistency rules +
   lenient completion, the M3 verify/repair engine with provenance
   logging, M5 plan tracking (`plan_id`, per-leg status, supersession
   cancels), the plan-state prompt block (generalizing
   failure-context) and scenario-agnostic plan invitation
   (`prompt_v2 → v3` template, hash-frozen at v2), the plan-metrics
   scorer incl. stability, and Arm B plan emission. Smoked first on
   the two-robot head-on, where it must reproduce v1's outcomes
   exactly (the swap gate as a one-leg repair, zero unforced replans)
   — that equivalence is the regression gate for everything after it.
5. `junction_clear` contract on top of (a0): M3 χ-ranked grounding +
   staggered recede, M5 phased dispatch, junction consistency rules.
   The repair-distance bound for falling back to `m3_default` is sized
   from the mock sweep in step 6 and frozen before live smokes.
6. IB10 composite mock smoke → live smoke (phase-by-phase).
   GATE RESOLVED BY DIAGNOSIS (2026-10-02,
   `docs/reports/2026-10-01-robot1-stale-rootcause.md` rev 3): the
   robot_1 STALE loss at the IB10 spawn is a sub-pixel
   sampling-phase ArUco decode marginality — marker-pattern ×
   world-x specific, no occluder/homography/overlap mechanism, no
   config-exposed detector knob (a code fix would touch v1-frozen
   M1). Spawn-dwell only: the arrival gate is stale-tolerant, and
   robot_1's goal (100%/100%) and yield-park pose (100%/97.9%) are
   verified clean. RULING: proceed under INSTRUMENTATION — every
   step-6 (and later scored) run's analysis must flag any long
   STALE streak during any stationary dwell, any robot (the probe
   analysis script's streak check is the model); a 0.10 m symmetric
   spawn re-radius (1.75 → 1.65 both arms, preserving the
   equal-radii invariant; −1.65 verified clean, +1.65 untested) is
   the registered fallback IF the flag fires in scored runs — an
   owner scenario-redesign call, not applied now.
7. Intersection oracle + regret extension; freeze IB10 scoring.
   STEP-6 OUTCOME (2026-10-02,
   `docs/reports/2026-10-02-ib10-composite-smoke.md`): mocks PASS
   (full phase sequence, solved-row geometry, correct provenance);
   repair bound stays 2; live ER-2 episode 1 chose `junction_clear`
   (inconsistent own plan → clean m3_default fallback); episode 2
   (fully supervised, 10 live decisions) shows the PRIMARY jam
   clears but the run does NOT reach 4/4 — the released secondary
   N-S conflict freezes in the latch and even the fallback reroute
   fails. FIVE FREEZE BLOCKERS now define step 7's fix scope,
   before any scoring freeze:
   (1) audit recede-set membership + recede order (wrong pair
   currently verifies vlm_verbatim — metric hole);
   (2) ordered release of held base missions after the composite
   resolves (the secondary conflict must go through the ordered
   machinery, not a free-for-all);
   (3) exempt a `continue` leg against a `reverse` in a different
   command of the same plan (4th member of the exemption family;
   M4-adjacent — protocol note required);
   (4) bound plain `reverse` to the tracked band (|y| overshoot to
   2.38/2.42 reproduced in BOTH live episodes, same window);
   (5) define fallback-exhaustion semantics (cross-phase timeout →
   reroute fails → terminal state must be a scorable outcome, not
   an undefined freeze).
   STEP-7a OUTCOME (2026-10-03,
   `docs/reports/2026-10-02-step7a-blocker-fixes.md`): all five
   fixes landed and pinned; IB10 mock reached 4/4 — but NOT
   attributably to the designed ordering, because of a newly found
   M4-M5 RACE: `/coordination/commands` and `/coordination/status`
   have no cross-topic ordering, so a successor command processed
   before its predecessor's terminal status lets that terminal
   later free the robot permanently. RULINGS for 7b:
   (i) RACE GUARD — a terminal status frees a robot only when its
   command_id matches the robot's active command (narrow
   command_bus_node change, protocol note, v1-path regression
   pins);
   (ii) REPAIR BOUND freeze procedure — re-sweep bounds 1–4 with
   the full corpus (incl. recede_order_swapped); freeze the
   smallest bound with full repairable coverage; if none ≤ 4,
   freeze 3 and document the uncovered tail as
   m3_default-by-design;
   (iii) ATTRIBUTABLE RELEASE — CrossingChain gate events get
   sim-stamped logging; the 7b IB10 rerun (final code redeployed)
   passes only on 4/4 AND decidable ordering attribution;
   (iv) the 82 s recede-hold STALE streak: identify the parked
   pair's separation; if < 0.6 m (the known overlapping-marker
   band), prefer STAGGERED recede-pocket offsets within the
   tracked band over the spawn re-radius; re-radius stays the
   registered fallback;
   (v) clear `_last_trigger_robot_ids` after dispatch (latent
   staleness window).
   STEP-7b RULINGS (2026-10-03, after
   `docs/reports/2026-10-03-step7b-oracle-freeze.md`; rulings
   (i)–(v) landed, repair bound FROZEN AT 3 with a documented
   depth-4/5 m3_default tail, race guard lives in
   `base_mission.py`/`coordination_client_node.py` per the traced
   mechanism — accepted deviation from the spec's named file):
   (vi) RELEASE ORDER — the yielder chains BEHIND the second
   receder via the ordered multi-passer path (crossing_order
   [lead, second receder] + linked temporary_wait; M3-only): the
   spec's "yielder re-enters last," now implemented relative to
   every receder; requires one more VM rerun whose PASS is 4/4 +
   decidable attribution + yielder-last observed in the gate log;
   (vii) PHASE ORDINAL stays a process label; episode success
   stays arrivals-based; the scorer adds a derived `outcome_rank`
   ordering (ordinal 4, 4/4) strictly above (ordinal 4, partial)
   so the two can never read as the same score.
   STEP 7 CLOSED (2026-10-03, report Rev 2): the deciding IB10
   rerun PASSED ALL CRITERIA — 4/4 position-verified arrivals,
   every release by clearance, yielder-last decidable in the gate
   log (robot_3 at sim 153.7, robot_1 at 185.8), zero contacts,
   max STALE streak 1 row. The formed four-way jam is RESOLVED
   end-to-end by the composite command. Accepted deviation from
   ruling (vi)'s text: the second receder keeps a lead-gated
   passive `yield` (a linked `temporary_wait` would carry no
   `admitted_partners` exemption and latch the lead mid-pass);
   order and M3-only scope as ruled. IB10 scoring FROZEN at 11
   criteria (incl. `outcome_rank`, `yielder_last` no longer
   contingent) — the v2 freeze references the report's pin table.
8. Loop map: USD + Nav2 + reroute grounding; the pre-emption control
   smoke before any scenario authoring.
9. B2-visual pair + B3 first-to-slip scenarios + oracles.
10. Capability-probe battery: author the probe set on project frames,
    freeze it, run once per backend; results recorded in the freeze
    record (rev 5). BUILT 2026-10-02 (manifest_v1, 60 items, prompt
    hash-pinned). Freeze-time follow-ups before the live per-backend
    runs: (a) DONE 2026-10-04 (runner wired through
    `resolve_reasoner_config`; baseline runs executed — see the
    CITATION CORRECTION/BASELINE block above); (b) CONFIRMED
    2026-10-04: the left/right operationalization stays image-frame
    side of centre column — it coincides with the aisle side in
    every sourced scene, and the vertical-in-frame-aisle caveat
    stands as a documented validity bound on the item type; (c) note
    `locate_robot` covers 4 of 9 grid cells after filters, and
    `nearest_first`'s robot_2-skewed answers must be read against the
    recorded robot-id priors before attributing errors to spatial
    reasoning.
11. prereg-v2 freeze: hash table, pins, veto list, probe results —
    same procedure as v1 — plus the rev-6 reading gates: GAVEL's
    evaluation section, the two MDPI texts, DeepFleet skim, PhAIL
    estimator confirmation; adjust claim wording if any of them
    bites before freezing.

Steps 1–3 are independent of v1 collection and can start immediately;
step 4 onward should be sequenced against collection so GPU-VM time and
API spend go to collection first.

---

## References

- Intersection resolvability study (S1):
  `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
- Unified scene design: `docs/superpowers/specs/2026-09-29-unified-scene-design.md` (`3b3a529`)
- Research design rev 9.5: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
- Amendments (decision record): `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`
- Literature: `reports/Four way intersection robot congestion.md`,
  `reports/Congestion scenario coverage check.md`
