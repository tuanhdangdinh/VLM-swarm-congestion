# VLM as Congestion-Resolution Reasoner — Research Design

**Prepared:** 2026-07-05

**Revision history:**

- Initial draft: four-pillar general spatial congestion resolution design.
- Rev 2: two-stage flow, explicit yield/order fields, hold-until-last,
  swept validation, no-blind-fallback rule.
- Rev 3: feasibility bands, no-snapshot degrade, uniform
  projected-clearance release predicate.
- Rev 4: integrated-contribution framing, conservative related work.
- Rev 5: failure-context feedback for re-analysis (Reflexion-lite) + its
  ablation.
- Rev 6: temporal context via single-frame visual traces + motion table
  (multi-image rejected on TempVS/ACL-2025 evidence);
  semantic-conditioned strategy arbitration.
- Rev 7: restructured as a controlled two-arm experiment around the
  preserved research objective; rev-1..6 mechanisms become the apparatus.
- Rev 8: applied external design review — run matrix and statistical
  plan; Arm B fully specified with tuning-parity rule; T0 negative
  controls; paired-seed policy; disagreement analysis labeled
  descriptive; model/decoding pre-registration and freeze mechanism;
  modality-condition input table; hypotheses renamed RQ1–RQ5 (collision
  with the historical "H3" run series); authored oracle blocks; enum-name
  drift fixed; degradation-breakdown reporting; decision-frame rendering
  contract; rev-6 mechanism detail restored as Appendix A; header
  reformatted per `docs/standards/doc_style.md`.
- Rev 8.1 (2026-09-16): added Appendix A.7 disclosing which apparatus
  components are simulator-supplied ground truth, sensor-derived at
  runtime, or scripted/tuned, per the 2026-09-16 system audit.
- Rev 8.2 (2026-09-17): episode boundary for failure-context feedback fixed as
  a time window after command resolution, any outcome (design:
  `2026-09-17-failure-context-closed-loop-design.md`).
- Rev 8.3 (2026-09-17): the previous-attempt block names the maneuver M3
  actually executed when it differs from the decided strategy, and its
  closing advice explicitly allows `congestion_detected=false` (design rev 3).
- Rev 8.4 (2026-09-17): stage-1 prompt states pairwise distance and mutual
  facing and defines head-on as facing + ≤ 0.5 m (run-3 root cause: `|Δθ| ≈ π`
  read diverging robots as a deadlock); decoding resolved per backend, `openai`
  pinned to temperature 0.0 (module-2 FR2.1.7, FR2.2.3).
- Rev 8.5 (2026-09-17): the derived geometry lines become a switchable
  modality (`ReasonerRequest.include_pairwise_geometry`, M5
  `prompt_pairwise_geometry`) and an ablation axis, so RQ1 is not answered
  by a prompt that already contains a classical geometry summary.
- Rev 8.6 (2026-09-19): T1 and the T2a *geometry* are realized as the
  `head_on_asymmetric` scenario family — a parked static blocker behind one
  or both spawn points, parameterized (`HeadOnAsymmetricParams`) and paired
  with a computed `OracleConfig` frozen at generation time (design:
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
  rev 2; variants and their oracles: `family_manifest.csv`; hardware
  validity evidence: `docs/reports/2026-09-18-head-on-family-validity.md`).
  The family's oracle uses this document's FCFS + commitment tiebreak rule
  (RQ3 control, above): with `arrival_offset_m` fixed at 0 in v1 both
  robots arrive together, so the residual tie breaks lexicographically by
  `robot_id` → `robot_1`, exactly as specified. The T2a **oracle-agreement
  claim** is a separate matter from the geometry and is *not* answerable by
  Arm A as prompted, per the 2026-09-19 design review (below); this
  revision also un-defers two mechanisms this document's Appendix A.4
  already anticipated and adds them to Arm A as declared, default-off
  modalities:
  - The **decision schema gains `yield_robot: str | None`**
    (`CongestionDecision`, module-2 FR2.1.9) — the model's own stated
    choice of yielder, meaningful only when `strategy == "yield"` and never
    required. Before this field, downstream grounding read list position in
    `involved_robots` as the yielder channel; a census of 524 decision
    artifacts found `robot_1` listed first in 44/44 `yield` decisions, i.e.
    position was never observed to carry a choice (design review Finding
    2).
  - The **modality table gains `static_obstacles`** (module-2 FR2.1.8, M5
    `prompt_static_obstacles`), alongside `pairwise_geometry`, following the
    same declared-modality pattern rev 8.5 established: id/centre/extent
    only, default **off**, and an off prompt byte-identical to the
    pre-modality prompt (pinned by a length + SHA-256 test).

  **Both are Arm A changes to the model/decoding pre-registration**, and
  both must be named in it before either is scored as a T2a oracle-agreement
  cell: **every decision artifact collected before 2026-09-19 was produced
  without `yield_robot` and without the obstacle channel**, by construction
  (neither field existed). The paired variants collected under this plan
  (`w0p2_eopen_o0` vs `wopen_e0p2_o0`) are reported as an order-vs-scene
  demonstration, not a T2a oracle-agreement result — see the family design
  spec's Status line and the 2026-09-19 design review for the full
  reasoning.

Status: in user review. Predecessor system: the verified head-on yield
protocol (H3 runs 8–13) and the M1→M5→M2→M3→M4 closed loop, live on the
GCP/Isaac host.

---

## Research objective (preserved, primary)

> **Investigate whether a VLM can act as a high-level
> congestion-resolution reasoner for swarm/multi-robot navigation.**

This is a research question, not a system goal. The design below is an
**experimental apparatus** for answering it: the VLM holds the full
reasoner role (the hypothesis under test), classical methods form the
**control arm** (not a fallback spine), and the scenario battery is
designed so that either answer — including "no" — is credible and
reportable. The engineering contribution (containment, event-driven
execution) is what makes the experiment safe and controlled; the research
contribution is the answer and the evidence.

**Claim scoping.** The answer is inherently model-scoped: it holds for
the pre-registered model(s) under this prompting and containment
apparatus (see Model & decoding pre-registration), not for "VLMs" in
general. Thesis claims must carry this scope; a "no" means "not this
model under this apparatus," which the secondary-model cells partially
de-risk.

**Congestion scoping.** "Congestion" here means localized spatial
conflict events requiring coordinated resolution (deadlocks,
bottlenecks, blocked corridors) at small robot counts. Swarm-scale
flow/throughput congestion (density-driven slowdown without a discrete
conflict) is out of scope (see Out of scope).

---

## Research questions (RQ1–RQ5, thesis skeleton)

Renamed from H1–H5 to avoid collision with the historical "H3" fix/run
series cited throughout project logs.

- **RQ1 Perception/classification:** the VLM correctly classifies
  congestion type and `blocker_kind` from the annotated scene (vs.
  authored ground-truth labels), and discriminates congestion from
  normal flow on log-only negative probes (T0). *Scope note:* both arms
  share the same stall-timeout trigger, so open-world detection recall
  is not measurable — the VLM only ever sees post-trigger scenes. RQ1
  therefore measures post-trigger classification plus false-positive
  discrimination, not detection recall.
- **RQ2 Strategy competence:** its strategy choices resolve congestion
  (vs. the Arm B per-type policy table, outcome-measured).
- **RQ3 Social reasoning:** its `yield_robot`/`crossing_order`
  assignments are effective (vs. FCFS + commitment-tiebreak baseline;
  oracle-scored on T2).
- **RQ4 Semantic advantage:** it exploits information no classical
  baseline has — blocker semantics and untracked visual elements (T3).
- **RQ5 Closed-loop adaptation:** failure feedback deliberately changes
  its subsequent decisions (vs. memoryless re-analysis, same episodes).

---

## Experimental arms, pairing, and shadow logging

- **Arm A (treatment):** VLM reasoner — all decision points below.
- **Arm B (control):** classical reasoner — same detection trigger, same
  grounding validation, same M4 execution; decisions per the Arm B
  specification section. The execution layer is identical across arms —
  outcomes are attributable to the reasoner alone.
- **Paired-seed policy (primary comparison design):** every episode
  instance is defined by (scenario variant, seed), where the seed fixes
  spawn jitter, goal assignment, and (where applicable) obstacle timing.
  Each instance in a paired cell runs once per arm with the identical
  seed, making the arm comparison paired at episode level. *Caveat
  (pre-registered):* Isaac physics is not bit-deterministic; pairing
  guarantees identical initial conditions, and residual physics noise is
  treated as episode noise.
- **Shadow logging:** in Arm A, the classical answer is *also* computed
  and logged for every decision; disagreements are first-class events.
  Every episode yields comparison data.
- **Disagreement-outcome analysis is descriptive.** "When the VLM
  deviated from classical, did it help?" cannot be answered causally
  from Arm A alone: the classical counterfactual outcome is unobserved
  and disagreements correlate with scene difficulty. Pre-registered
  reading: disagreement analysis is hypothesis-generating; causal
  attribution comes only from (a) the paired-seed arm comparison and
  (b) tiers whose construction defines the correct answer (T2/T3 oracle
  blocks).
- **Modality conditions (Arm A only):** dual-channel (default) /
  text-only / image-only, defined block-by-block in the apparatus
  section. The state table intentionally duplicates much of the image
  content; these conditions locate where the reasoning actually lives.

---

## Arm B — classical reasoner specification

New in rev 7, previously one line per component; pinned here because the
credibility of every "VLM vs. classical" claim rests on the control not
being a strawman. Implemented in
`reasoning/baselines/classical_reasoner.py`; consumes the same snapshot
ring buffer as Arm A's motion table; sees **no image** (that asymmetry
is the point of T3).

### Geometry classifier (RQ1 control)

Inputs: tracked robot states from the snapshot ring buffer (positions,
headings, velocities, goals). Rules, evaluated in order at trigger time:

- **head_on:** exactly 2 stopped robots within `r_conflict` (default
  1.5 m) of each other, heading opposition > 150°, and each robot's goal
  bearing lies beyond the other robot.
- **intersection:** ≥ 2 stopped robots within `r_conflict` of a mapped
  conflict zone with crossing transit axes (pairwise axis angle in
  [45°, 135°]).
- **blocked_path:** a stopped robot with no other tracked robot within
  `r_block` (default 1.0 m) ahead along its transit axis. Classical
  `blocker_kind` is always `object` here — it has no channel that could
  distinguish `object` from `transient`. This forced non-divergence is
  what T3a measures against.
- **unknown:** anything else.

### Per-type policy table (RQ2 control)

| Classical type | Strategy | Roles |
|---|---|---|
| head_on | `yield` | yielder = tiebreak loser; retreat = geometry-max candidate |
| intersection | `yield` + ordered crossing | order = FCFS by arrival stamp; yielder = last arrival |
| blocked_path (`object`) | `reroute` | — |
| unknown | `temporary_wait` (bounded, once) → `reroute` on second trigger | — |

### FCFS + commitment tiebreak (RQ3 control)

Order by arrival stamp at the conflict zone (from the motion table).
Ties (Δ arrival < 1.0 s) break by **commitment** = normalized progress
into the conflict zone (distance traveled past the zone entry / zone
length, from the ring buffer); higher commitment passes first. Residual
ties break by lexicographic `robot_id`. This is both Arm B's ordering
and the shadow answer logged in Arm A.

### Stage-2 control

Geometry-max ranking over the identical validated candidate set (Pillar
2's deterministic ranker). By construction, Arm A's stage-2 fallback IS
Arm B's stage-2 answer — the fallback is the control.

### Tuning-parity rule (pre-registered)

Arm B parameters (`r_conflict`, `r_block`, angle windows, arrival-tie
window) may be tuned **only on T1 scenarios, only before the
pre-registration freeze** (see Run matrix). They are frozen at the
`prereg-v1` tag together with this document. Any post-freeze change
invalidates affected collected cells, which must be re-run. This
preempts both "strawman baseline" and "tuned-on-test" critiques.

---

## Scenario battery (the discriminating instrument)

- **T0 Negative controls (log-only probes):** normal-flow episodes with
  no congestion; stage-1 analysis is invoked off-trigger on probe frames
  in **log-only mode** (no command may be emitted — enforced, tested).
  Measures the false-positive side of RQ1 that the shared trigger
  otherwise hides.
- **T1 Geometry-sufficient** (non-inferiority tier): current
  `head_on_deadlock` (0.55×2.0 corridor) and `intersection_bottleneck`.
  Classical solves these; the VLM must match it.
- **T2 Geometry-ambiguous** (reasoning tier): variants where naive
  geometry is wrong or arbitrary — (a) asymmetric retreat space (one
  side's candidates infeasible; the correct yielder is NOT the FCFS pick
  because the first-arriver has no retreat room); (b) symmetric standoff
  with asymmetric downstream traffic (the correct order depends on flow,
  visible in the trails/motion table).
  **T2a's geometry (rev 8.6, 2026-09-19)** is realized by the
  `head_on_asymmetric` scenario family: `head_on_asymmetric_w0p2_eopen_o0`
  (blocked west, `correct_yielder: robot_2`, contrasts the FCFS pick) and
  `head_on_asymmetric_wopen_e0p2_o0` (blocked east, `correct_yielder:
  robot_1`, FCFS happens to be right — included to expose robot-id bias),
  both against the `head_on_asymmetric_wopen_eopen_o0` T1 control. Design:
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
  (rev 2); frozen parameters and oracles: `family_manifest.csv`. The
  **oracle-agreement claim** these two variants exist to support is not
  currently answerable by Arm A as prompted (rev 8.6, above; design review
  Findings 1–2) — collecting it needs the `yield_robot` field and the
  static-obstacle modality named in the Arm A pre-registration first.
- **T3 Semantics-required** (only-VLM tier): (a) paired blocker
  counterfactuals — near-identical geometry, static object vs. transient
  agent (divergent correct responses: `reroute` vs. `temporary_wait`);
  (b) obstacle-in-candidate — an **untracked** visual obstacle inside
  the geometry-max retreat candidate (classical picks it; the correct
  choice requires vision); (c) `dynamic_anomaly` timed-obstacle runs.
  M1 tracks only ArUco robots, so untracked elements exist in the image
  and in NO text channel — this asymmetry makes T3 vision-load-bearing
  by construction.
- **Authored oracle blocks:** every T2/T3 scenario YAML carries an
  `oracle:` block — the pre-registered correct answer and the objective
  it optimizes — authored with the scenario and frozen at `prereg-v1`.
  For T2b the objective is minimum total time-to-goal, and oracle
  validity is itself verified at authoring time: scripted executions of
  both orders must show the oracle order dominating by ≥ 20% total
  delay, else the variant is re-authored.

```yaml
oracle:
  correct_yielder: robot_2        # T2a
  correct_order: [robot_1, robot_3]
  objective: min_total_time_to_goal
  rationale: >
    robot_2's rear corridor is the only feasible retreat volume;
    FCFS would pick robot_1, whose candidates all fail the sweep.
```

- Authoring T2/T3 variants (scenario yamls + USD rebuilds + obstacle
  assets) is a first-class work item, not an afterthought — without them
  the experiment cannot discriminate.

---

## Run matrix and statistical plan

### Why paired, and what N buys

An unpaired two-proportion non-inferiority test at margin δ = 10 pp
(success rates ≈ 0.9, one-sided α = 0.05, power 0.8) needs ≈ 110
episodes **per arm per scenario** — infeasible. The paired-seed design
tests the *paired difference*: with a low discordant rate `p_d`
(expected 0.10–0.15 on T1), the one-sided 95% bound half-width is
≈ 1.645·√(p_d/n), i.e. ≈ 10 pp at n = 30–40 pairs. Pre-registered rule:
**N = 30 pairs per T1 scenario; if the observed one-sided 95% bound on
the paired success-rate difference exceeds the 10 pp margin while the
point estimate is inside it, extend once to N = 60 pairs** (a
pre-specified conditional extension, reported as such).

### Run matrix (pre-registered cells)

| Cell | Scenarios | Arms / condition | N | Primary test |
|---|---|---|---|---|
| T1 non-inferiority | `head_on_deadlock`, `intersection_bottleneck` | A vs B paired, dual | 30 pairs/scenario (→ 60 by extension rule) | one-sided 95% bound on paired Δ success ≤ 10 pp (McNemar-style) |
| T2 oracle agreement | T2a, T2b | A vs B paired, dual | 15 pairs/variant | oracle-agreement rate A vs B, Fisher exact, α = 0.05 |
| T3a counterfactual pairs | object/transient pair | A executed (B shadow), dual; B executed on 5 pairs for outcome contrast | 15 pairs (= 30 episodes) + 10 B | divergent-and-correct rate: one-sided 95% binomial lower bound > 0.5 |
| T3b obstacle-in-candidate | 1 scenario, k = 3 candidates | A executed (B shadow), dual; 5 B executed | 15 + 5 | binomial vs. chance 1/3, α = 0.05 (≥ 9/15 correct avoidance) |
| T3c timed obstacle | `dynamic_anomaly` | A vs B paired, dual | 10 pairs | descriptive (time-to-resolution, degradations) |
| T0 negative probes | normal-flow runs | A log-only, dual | 20 probes | false-positive rate ≤ 10% (≤ 2/20) |
| RQ5 adaptation | forced-failure episodes | A informed vs A memoryless, dual | 15 + 15 | Fisher exact informed vs memoryless, α = 0.05; secondary: ≥ 11/15 informed-direction (binomial vs 0.5) |
| Modality | 1 T1 scenario + T3a + T3b | A only: text-only, image-only | 10 per condition·scenario | descriptive deltas; T3 binomial per condition |
| Ablation: temporal | T2b (order-sensitive) | A, dual minus traces+motion table | 10 | oracle-agreement delta |
| Ablation: annotation scheme | T3 subset | A, legacy vs legible | 10 per scheme | task-metric delta |

Seeds are drawn once per cell and reused across arms/conditions within
that cell. All tests, margins, and N values above are frozen at
`prereg-v1`; deviations are reported as protocol deviations.

### Budget estimate (planning numbers)

≈ 390 episodes baseline, ≤ ≈ 510 with the T1 extension; at ≈ 5 min
wall-clock per episode ⇒ ≈ 33–43 h of simulation (batched unattended
runs on the GCP/Isaac host). ≤ ≈ 1,200 VLM calls (1–3 per episode);
hosted-API cost is negligible relative to sim time. The budget-shaping
fact: T3 effects are constructed to be large, so T3 cells are cheap;
T1 non-inferiority carries most of the episode budget.

### Pre-registration freeze

Tag `prereg-v1` freezes: this document, Arm B config/thresholds, oracle
blocks, prompt templates, and the model/decoding table. Episodes run
before the tag are pilot data, excluded from headline results.

---

## Pre-registered success criteria

Defined before data collection; "VLM cannot" is a reportable outcome.

- **"VLM can" requires all of:**
  - **T1 non-inferiority:** one-sided 95% bound on the paired
    success-rate difference within 10 pp per T1 scenario (per the run
    matrix), **and** aggregate degradation (`*=default`) rate < 20%.
    (The containment layer makes safety-envelope violations structurally
    impossible, so degradation frequency is the measured quantity; the
    per-cause breakdown below is mandatory reporting.)
  - **T0 discrimination:** false-positive rate ≤ 10% on log-only probes.
  - **T3 superiority:** T3a divergent-and-correct lower bound > 0.5
    (classical shadow non-divergent by construction); T3b ≥ 9/15
    avoidance of the occupied candidate (vs. chance 1/3).
  - **RQ5 adaptation:** informed vs. memoryless difference significant
    (Fisher exact, α = 0.05) with informed-direction change in ≥ 11/15
    informed episodes.
- **Partial answers are findings:** e.g., "competent arbiter on T1/T2,
  decisive only on T3 semantics" or "text-only equals dual-channel
  everywhere except T3" are publishable characterizations.

---

## Model and decoding pre-registration

The apparatus supports four backends behind the `VLMBackend` protocol
(`mock`, `llama_server`, `openai`, `anthropic` in
`reasoning/vlm/backend_factory.py`). The research answer is scoped to
the pinned models below; the mock backend is for plumbing tests only and
appears in no reported cell.

| Field | Value | Status |
|---|---|---|
| Primary backend | `openai` (hosted API; swap from mock is on the critical path, blocked on API key) | pinned |
| Primary `model_id` | exact model string + version/date | **REQUIRED before freeze** |
| Secondary backend | `llama_server` (local; per the 2026-06-12 llama-server design) | pinned |
| Secondary `model_id` | exact local model + quantization | **REQUIRED before freeze** |
| Temperature | 0.0 for `openai` (classification workload, per coding standards); `llama_server` keeps the Cosmos Reason 2 CoT preset (0.6/0.95/20) via the per-backend `vlm.<backend>.reasoner` override in `config/models.yaml` — resolves the 2026-07-08 reconciliation item | pinned (rev 8.4) |
| Images per call | 1 (single-frame rule; multi-image rejected rev 6) | pinned |
| Image resolution | exact W×H of the annotated decision frame | **REQUIRED before freeze** |
| Max output tokens | fixed value | **REQUIRED before freeze** |
| Retry budget | transport retries and schema-repair reprompts, as implemented in the M2 reasoner | record exact values at freeze |
| Prompt templates | content hash of stage-1/stage-2 templates per condition | recorded at freeze |

Rules: data collection may not start until every REQUIRED row is frozen
at `prereg-v1`. The **secondary model runs the headline cells only**
(one T1 scenario + T3a + T3b, dual channel) so that a "no" is not
attributable to a single model, and a "yes" gets a robustness check.
Mid-experiment model deprecation ⇒ freeze a `prereg-v2` with the
replacement and re-run affected cells.

---

## The apparatus (mechanisms; adopted techniques, none claimed novel)

The four pillars from revs 1–6 are the machinery both arms run on.
**Normative mechanism detail is Appendix A** (restored from rev 6);
summaries below.

### Decision flow (two-stage)

- **Stage 1:** VLM receives the annotated frame with **fading trajectory
  trails** (~8 s, from M5's snapshot ring buffer; single frame — image
  sequences rejected on TempVS evidence, traces supported by TraceVLA) +
  a **derived motion table** (arrival order, seconds stopped,
  displacement, prior yields) + full robot state + (on re-analysis) the
  **failure-context block** (rev 5). Outputs: congestion/type,
  `blocker_kind`, strategy within the semantically compatible set,
  `yield_robot`, `crossing_order`, justification.
- **Stage 2 (yield only):** system generates 2–4 retreat candidates
  (swept-path validated, feasibility-banded), M1 renders them as
  set-of-mark letters, VLM selects `retreat_choice` + one-clause
  justification. Stage-2 failure → geometry-best candidate (= Arm B's
  answer — the fallback IS the control).
- **Annotation legibility (from the noise review):** identity = color,
  status = box style; boxes shrunk toward true footprint; labeled goals
  (G1/G2); candidate letters in a reserved color; leader-line labels in
  clusters; stage-2 frames drop arrows/goal markers; the prompt explains
  the annotation scheme in one sentence.
- **Decision-frame rendering contract:** M5 invokes a pure rendering
  function in `swarm_perception.annotation`, passing snapshot history
  (trail points) and candidate pixels. Decision frames are produced
  on demand at decision time and are distinct from the live 20–50 Hz
  `/perception/annotated_frame` stream; trails and candidate letters
  never appear on the live stream.

### Modality-condition input table (Arm A)

| Input block | dual (default) | text-only | image-only |
|---|---|---|---|
| Annotated frame + trails | ✓ | — | ✓ |
| Robot state table | ✓ | ✓ | — |
| Derived pairwise geometry lines (distance, mutual facing; rev 8.5, `prompt_pairwise_geometry`) | ✓ | ✓ | — |
| Static obstacles (id/centre/extent; rev 8.6, `prompt_static_obstacles`, default off) | ✓ | ✓ | — |
| Motion table | ✓ | ✓ | — |
| Failure-context block (re-analysis) | ✓ | ✓ | — |
| Annotation-scheme sentence | ✓ | — | ✓ |
| Stage-2 set-of-mark frame | ✓ | — (stage 2 skipped → geometry-max, logged `stage2=condition_constrained`, not a degradation; identical to Arm B stage 2 by definition) | ✓ |

Image-only cells are excluded from RQ5 (the failure context is textual).
The offline input-encoding harness
(`2026-06-15-m2-input-ablation-design.md`) remains the spec for the
benchmark runner and encoder seam; live-loop conditions here reuse that
seam, and **where definitions conflict, this document governs the live
experiment**.

### Pillar summaries (normative detail: Appendix A)

1. **Derived geometry:** backup/escort distances from actual poses with
   feasibility bands (out-of-band ⇒ infeasible ⇒ reroute/reanalyze; no
   clamped or blind execution); no-snapshot ⇒ non-spatial wait;
   projected-progress clearance predicates; escort heading from odom.
2. **Candidate selection:** set-of-mark selection among pre-verified
   options (adopts 2310.11441/2310.07937/CoNVOI); geometry-max ranking
   is simultaneously the default, the fallback, and the control arm.
3. **Ordered crossing:** explicit `yield_robot`/`crossing_order` fields,
   permutation-validated; event-driven sequenced release (uniform
   projected-clearance predicate incl. first passer); yielder holds
   until last clears, then rejoins; wait-expiry ⇒ FAILED + suppression
   retained + reanalysis, never silent release.
4. **Semantic-conditioned strategy arbitration:** `blocker_kind`
   constrains the compatible strategy set — `robot` → full set;
   `object` → {`reroute`, `temporary_wait` (admissible only as a
   bounded first probe)}; `transient` → {`temporary_wait`, `reroute`} —
   and the VLM selects within it using scene, traces, and failure
   context; out-of-set ⇒ per-kind default, logged. **Naming rule:** all
   strategy tokens in this document are values of the existing enum in
   `reasoning/schemas/vlm_decision.schema.json` (`yield`, `reroute`,
   `convoy`, `priority_override`, `temporary_wait`, `reverse`); informal
   shorthand like "wait" always denotes `temporary_wait`, and this
   design introduces **no new enum entries**.

### Containment (the laboratory's safety glass — unchanged)

VLM outputs restricted to system-generated discrete options; geometric
revalidation at grounding (swept segments, permutations, feasibility);
verified-or-degrade everywhere; all degradations logged `*=default` and
counted in the metrics. A wrong VLM answer produces a logged
degradation, never unsafe motion — which is precisely what makes Arm A
safe to run.

---

## Measurement plan

Per episode: resolution success, time-to-resolution, cycles, safety
stops, degradation counts, full decision artifacts (both stages,
justifications, shadow answers, disagreement flags, seed, arm,
condition).

- **Degradation breakdown (mandatory reporting):** the aggregate
  `*=default` rate is the criterion, but it is always reported
  decomposed by cause — {`parse_failure`, `invalid_label`,
  `out_of_set_strategy`, `non_permutation_order`, `infeasible_geometry`,
  `no_snapshot`, `wait_expired`} — so a passing aggregate cannot hide a
  concentrated failure at one decision point. Any single cause > 30% of
  its decision opportunities is flagged as a finding.
- **Analyses:** per-tier paired arm comparison (RQ1–RQ3),
  counterfactual divergence (RQ4), adaptation trajectories (RQ5),
  modality deltas, disagreement-outcome analysis (descriptive, per the
  arms section).
- **Secondary stage-2 analysis (retained from rev 6):** on identical
  candidate sets, compare retreat policies — VLM choice vs.
  geometry-max vs. fixed-left vs. random-valid — to isolate the value of
  visual selection within the validated set.
- **Qualitative:** justification review on disagreement cases.

---

## Ablations

All ablation cells are enumerated in the run matrix; this section only
names the axes. Modality (dual / text-only / image-only) **is** the
with/without-image axis — it is not listed twice. Remaining axes:
with/without temporal context (traces + motion table); with/without
failure context (forced-failure episodes, = the RQ5 memoryless control);
with/without derived pairwise geometry lines (rev 8.5,
`prompt_pairwise_geometry`) — checks whether RQ1's classification result
survives when the VLM is not handed a classical geometry summary, since
those lines are exactly what an Arm B classifier computes;
annotation scheme (legible vs. legacy) on a T3 subset — checks whether
the noise fixes matter.

---

## Related-work positioning (conservative; writing rule unchanged)

Mechanisms adopt: set-of-mark (2310.11441), candidate selection
(2310.07937, CoNVOI), LLM-arbiter ordering (LLMDR), social corridor
decision (NOD 2504.20947), trace prompting (TraceVLA), structured motion
summaries (MotionVLA); versus REALM (2404.06413): discrete bounded
arbitration instead of free waypoints over CBFs, warehouse BEV setting,
and — the actual contribution — the **controlled two-arm evaluation with
shadow logging and a tiered battery answering when/whether the VLM
helps**. Avoid "first"/per-pillar novelty claims; SocialNav-SUB
(2509.08757) and TempVS (2506.10415) motivate input design (weak VLM
spatial/sequence reasoning → text tables + traces +
selection-not-generation).

---

## Out of scope (future work)

Rotation/roundabout strategy; occupancy-grid free-space search; VLM
metric coordinate output (candidate densification is the on-ramp);
multi-frame/video input (rejected on TempVS evidence; revisit as models
improve); task-level escalation via M5's registry (MRTA/TAMP scope);
**swarm-scale flow/throughput congestion** (density-driven degradation
without a discrete conflict event — different battery, different
metrics) and larger robot counts beyond the 2–4-robot conflict scenarios.

---

## Testing

- **Unit (offline):** all rev-3..6 items (derivations, feasibility
  edges, candidate sweep validation, ranking determinism, label
  fallback, order validation, release chain incl.
  escort-terminal-not-clearance case, hold-until-last, wait-expiry
  suppression retention, compatibility-matrix enforcement, ring
  buffer/trails/motion-table, failure-context block presence — full
  normative list in Appendix A / rev 6) **plus:** Arm B classical
  reasoner (deterministic outputs on synthetic snapshots — classifier
  rules, policy table, commitment tiebreak incl. tie edge cases);
  shadow-logging plumbing (disagreement flag correctness);
  modality-condition prompt assembly (block inclusion per the input
  table, incl. `stage2=condition_constrained` path); **T0 log-only mode
  emits no command under any decision output**; oracle-block schema
  validation; seed plumbing (same seed ⇒ identical spawn/goal/obstacle
  config).
- **E2E (host):** per tier — T1 regression both arms (paired seeds); T2
  variants (the FCFS-wrong case exercises the disagreement machinery);
  T3 counterfactual pairs + obstacle-in-candidate + adaptation
  trajectory (wait → forced expiry → informed reroute); one T0
  normal-flow probe episode. Decision artifacts must contain both arms'
  answers per decision, plus seed/arm/condition fields.

---

## Files touched (expected)

- `reasoning/schemas/` (stage-1 fields, stage-2 response schema),
  `reasoning/vlm/` (models, parser, prompt builder: temporal/failure
  blocks, modality conditions, annotation-scheme sentence)
- `reasoning/rag/command_grounder.py` (snapshot param, derivations,
  candidates, ordering, compatibility matrix, infeasible outcomes) + a
  new `reasoning/baselines/classical_reasoner.py` (Arm B + shadow)
- `swarm_orchestrator/` (two-stage orchestration, ring buffer, motion
  table, arm/condition switching, seed plumbing, T0 log-only probe
  mode, shadow logging in decision artifacts)
- `swarm_perception/annotation.py` (legibility pass, trails, candidate
  markers; pure decision-frame rendering entry point)
- `swarm_execution/` (sequenced release, rejoin, wait-expiry semantics,
  escort heading, projected-progress predicates)
- `isaac/config/scenarios/` + assets (T2/T3 battery with `oracle:`
  blocks, T0 normal-flow scenario, obstacle assets, USD rebuilds)
- **Docs kept in sync (required by project standards):**
  `docs/specs/module2_vlm_reasoning.md`, `module3_rag_grounding.md`,
  `module5_orchestrator.md`, and `reasoning/schemas/` docs for every
  schema/field change above; supersession note added to
  `2026-06-15-m2-input-ablation-design.md` (live-loop modality
  conditions governed here).
- Pre-registration freeze artifacts: `prereg-v1` git tag; Arm B config;
  model/decoding table values.
- Tests mirroring each.

---

## Appendix A — Apparatus mechanism detail (normative)

Restored from rev 6 (commit `c63fb79`) as the normative mechanism
specification; the body's pillar summaries defer to this appendix.
Lightly edited for cross-references only.

### A.1 Decision flow (two-stage — resolves the candidate/yielder circularity)

Retreat candidates depend on knowing the yielder; the yielder is the
VLM's choice. Therefore:

- **Stage 1 (existing analysis call):** VLM receives **temporal context
  rendered into a single frame**, not an image sequence: (a) each
  robot's past ~8 s trajectory drawn as a fading polyline trail on the
  current annotated frame (M5 sends trail points from its snapshot ring
  buffer with the frame request — the same plumbing pattern as stage-2
  candidate markers); (b) a compact per-robot motion table derived from
  buffered snapshots (arrival order at the conflict zone, seconds
  stopped, displacement over the window, prior yields this episode).
  Mechanism choice is survey-driven: image-SEQUENCE temporal reasoning
  is unreliable in current MLLMs (TempVS/"Burn After Reading", ACL
  2025: 38 SOTA models substantially below human on event ordering;
  CHRONOSIGHT's "chronological blindness"), whereas trace overlays on a
  single frame demonstrably enhance spatiotemporal awareness (TraceVLA,
  ICLR 2025) and structured motion summaries beat raw frame history
  (MotionVLA 2606.08288). Outputs: congestion/type, `blocker_kind`,
  strategy (semantically conditioned — see A.5), `yield_robot`,
  `crossing_order`, justification — role choices can thus depend on
  approach order, commitment, and traffic flow rather than a static
  configuration. Fallback: history unavailable (episode start, buffer
  gap) → traceless frame + no motion table, logged
  `history=unavailable`.
- **Stage 2 (only when strategy = yield):** M5 generates validated
  retreat candidates for `yield_robot` (A.3), has M1 render them as
  markers on a fresh frame, and issues a second, narrow VLM call whose
  only output is `retreat_choice` + one-clause justification.
- **Latency:** one extra VLM round trip (~2–6 s) inside Layer 2's
  0.5–2 Hz budget; the robots are stationary in a standoff, so the cost
  is benign.
- **Stage-2 failure** (timeout, parse failure, invalid label): proceed
  with the deterministic geometry-best candidate (see A.3 fallback
  rules). Stage 2 never blocks resolution.
- **Failure-context feedback (Reflexion-lite):** when M5 re-analyzes a
  congestion episode after a prior resolution (originally "after a failed
  or expired resolution"; widened to any outcome in rev 8.2), the stage-1
  prompt includes a short "previous attempt" block — last strategy,
  chosen roles, outcome status, and failure detail (e.g. `wait expired
  unresolved`) — sourced from the decision artifact M5 already stores.
  The episode loop thereby becomes deliberate observe-and-adapt rather
  than accidental re-derivation (run 12 showed the VLM switching
  strategies without knowing its yield had failed). Contained: this
  adds prompt context only — no new action space, outputs remain the
  same bounded fields. Scope: context covers the current episode's
  prior attempt(s) only; no cross-episode memory.
  Episode boundary (rev 8.2): the previous attempt is retained for
  `failure_context_window_sec` after its command resolves, whatever the
  outcome (a `completed` yield that did not clear the standoff is fed back
  too), and is dropped on expiry or when an analysis starts for a disjoint
  robot set.
  Fidelity (rev 8.3): `strategy` in the block is the decided strategy, but
  when M3 degraded it (a refused yield fans out as `temporary_wait`) the
  detail names the executed maneuver — `"yield completed 15 s ago (executed
  as temporary_wait); …"` — so the VLM never reasons about a maneuver that
  did not run; and the block's closing advice states that
  `congestion_detected=false` is the right answer when the congestion is
  gone, so memory does not bias the model toward always choosing a strategy.

### A.2 Pillar 1 — Derived maneuver distances

`ground_reasoner_result` gains a `snapshot` parameter (the
`SceneSnapshot` already available at the `reasoning_pipeline.py`
grounding call site).

- **Backup distance** (formalized): the minimum retreat-axis motion `d`
  such that, at the retreated pose, the yielder's separation from
  **every other robot in `crossing_order`** is ≥ pass-clearance
  (`2*min_distance_m + margin`), computed by projecting each robot's
  position onto the yielder's retreat axis. **Feasibility band, not a
  clamp:** if the required `d` falls outside [0.5, 2.0] m, the yield is
  **infeasible with this geometry** — the grounder returns the
  reroute/reanalyze outcome (same path as zero valid candidates).
  Clamping an out-of-band requirement would execute a backup that
  silently fails its own clearance premise.
- **Escort distance** = signed distance along the transit axis from the
  passer's hold-start position to the point past the yielder's parked
  position by pass-clearance; same rule — required distance outside
  [1.0, 3.5] m ⇒ infeasible ⇒ reroute/reanalyze, never a truncated
  transit.
- **Clearance events use signed projected progress**, not raw odometry
  displacement: progress = projection of (current − start) onto the
  robot's transit axis. Raw displacement counts lateral drift and servo
  wobble as progress; projection cannot go backwards-positive.
- **Escort heading**: M4 uses the passer's own heading at escort start
  (from its odom), not yaw 0.
- **Lateral magnitude** stays a config default (0.35 m) with
  per-scenario override. Map-derived lateral clearance is future work —
  this design verifies against robot poses, not the occupancy grid.
- **Fallback:** `snapshot=None`/malformed → the spatial yield is **not
  executable**: derivation and candidate validation both need the
  snapshot, so nothing about the maneuver can be verified. The grounder
  degrades to a non-spatial outcome (`temporary_wait` + reanalysis),
  logged `distances=unavailable`. Blind executable constants — midpoint
  or otherwise — are never emitted, consistent with the A.3 rule.

### A.3 Pillar 2 — VLM retreat-candidate selection (set-of-mark, stage 2)

- **Candidate generation (M5/grounder):** 2–4 retreat poses for
  `yield_robot` (left-rear / right-rear at the A.2 backup distance,
  ± lateral variants). **Validation covers the swept path, not only the
  endpoint:** the straight backup segment and the sidestep segment are
  sampled at ≤ 0.1 m intervals; every sample must keep
  ≥ `min_distance_m` from all other robots and stay inside the aisle
  band. Candidates failing any sample are discarded.
- **Ranking:** surviving candidates are scored by a deterministic
  geometry metric (min clearance along the swept path, tie-break:
  distance from the transit corridor). The top-ranked candidate is the
  **default**.
- **Annotation:** M5 converts candidate poses to pixels via the
  existing homography and passes them in the M1 frame request; M1's
  annotation pass draws lettered markers (Ⓐ/Ⓑ/Ⓒ).
- **Prompt (stage 2):** "choose the marked retreat position that best
  clears the conflict while preserving the passage space the other
  robots need and avoiding visible obstacles or traffic; answer with
  the letter and one clause of justification." (Not "most clear
  space" — the objective is conflict clearance, not open floor.)
- **Fallback rules (strict):** invalid/absent label → the geometry-best
  valid candidate, logged `retreat=default`. **Zero valid candidates →
  the yield is not executable: grounder returns a `reroute`-or-reanalyze
  outcome to M5 instead of a yield command. The old blind lateral
  constant is never used as a fallback.**
- **Rejoin:** after release (see A.4), the yielder sidesteps back by
  the negated chosen lateral before COMPLETED publishes, re-entering
  Nav2 from the lane centerline (fixes the run-13 tunnel-mouth wedge).

### A.4 Pillar 3 — Ordered crossing (explicit fields, sequenced release)

- **Schema:** explicit fields — `yield_robot: str` and
  `crossing_order: [str]` — replacing the overloaded `involved_robots`
  ordering convention. `involved_robots` remains the unordered set
  (backward compatible). Validation: `yield_robot ∈ involved_robots`;
  `crossing_order` is a permutation of
  `involved_robots − {yield_robot}`; violations → decision rejected at
  parse (same containment as any schema failure), logged.
- **Grounder (yield, N robots):** `yield_robot` yields;
  `crossing_order[0]` gets the escorted transit; `crossing_order[1:]`
  get linked waits.
- **Release chain (uniform predicate):** robot k+1 releases when robot
  k's **signed projected progress along its transit axis ≥ its
  clearance threshold** — the same odometry-projection predicate for
  every robot, including `crossing_order[0]`. The escort's terminal
  status is command bookkeeping only, never a release trigger: an
  escort can complete its commanded distance (or FAIL at its bound)
  without the robot actually clearing the conflict zone, so releases
  key exclusively on measured clearance.
- **The yielder holds until the LAST robot in `crossing_order` clears**
  (same projected predicate), then rejoins (sidestep-back) and
  publishes COMPLETED. With N=2 the behavior degenerates to the
  verified head-on flow plus rejoin.
- **Timeout semantics:** a linked wait's upper bound expiring does
  **not** release the robot into an unresolved conflict. It publishes
  FAILED (detail `wait expired unresolved`) for the whole resolution
  command, and the coordination client **keeps affected robots
  suppressed** pending M5's reanalysis (suppression transfers to the
  follow-up command's ACTIVE; it does not lapse on this FAILED). M5
  treats the FAILED as terminal and reanalyzes — error handling, not
  silent resumption.

### A.5 Pillar 4 — Semantic-conditioned strategy arbitration

- **Schema:** optional `blocker_kind: "robot" | "object" | "transient"`.
  Prompt: classify what is blocking, from visible evidence.
- **Conditioned arbitration, not a lookup:** `blocker_kind` does not
  fix the strategy; it constrains the **compatible strategy set**, and
  the VLM selects the final strategy within that set using current
  scene context, the rendered motion history, and previous-attempt
  execution feedback (A.1 failure-context block). Compatibility matrix
  (grounder-enforced):
  - `robot` → {`yield`, `reverse`, `temporary_wait`, `reroute`,
    `convoy`, `priority_override`} (full multi-robot set)
  - `object` → {`reroute`, `temporary_wait`} (an object won't move
    itself; wait is admissible only as a bounded first probe)
  - `transient` → {`temporary_wait`, `reroute`}

  This is what makes adaptation deliberate: a transient blocker
  reasonably draws `temporary_wait` first; after a `wait expired
  unresolved` outcome arrives via failure context, the VLM may escalate
  to `reroute` — same bounded vocabulary, evidence-dependent choice.
- **Validation & fallback:** strategy outside the compatible set for
  the declared `blocker_kind` → replaced by the deterministic default
  for that kind (`robot` → template as-is, `object` → `reroute`,
  `transient` → `temporary_wait`), logged
  `strategy=incompatible-defaulted`. Absent/invalid `blocker_kind` →
  unconstrained strategy set, logged `blocker=unclassified`.

### A.6 Failure containment (precise claims)

- VLM outputs are restricted to system-generated discrete options
  (candidate labels, robot ids, enum values); every accepted choice is
  **geometrically revalidated at grounding time** (swept-segment checks
  for retreat; permutation checks for ordering). A schema-valid but
  geometrically-invalidated choice is replaced by the deterministic
  default and logged.
- What can still reach M4: a *valid but suboptimal* choice (e.g., the
  worse of two safe retreat sides). This is bounded by construction —
  every executable option passed the same swept-path safety checks —
  and is exactly the residual the stage-2 secondary analysis measures.
- Degradations are logged with `*=default` markers so fallback
  frequency is measurable from decision artifacts.

### A.7 Ground truth, sensor-derived, and scripted apparatus components (rev 8.1)

Audited 2026-09-16 against the running system, so the two-arm
decision-source comparison is read correctly: which parts of the
apparatus are simulator-supplied, which are decided from sensor data
at runtime, and which are scripted or scenario-tuned.

- **Simulator ground truth.** Localization is bypassed: each robot's
  `map -> <robot>/odom` transform is a static transform equal to its
  known spawn pose
  (`ros2_ws/src/swarm_simulation/launch/nav2_robot.launch.py`), and
  AMCL is deliberately not launched — robots do not localize
  themselves. `/robot_N/odom` comes from Isaac Sim's
  `IsaacComputeOdometry` on the simulated chassis pose (effectively
  noise-free); M4's backup/sidestep/escort primitives close their
  distance loops on this odometry. M1's camera calibration
  (`ros2_ws/src/swarm_perception/config/calibration.yaml`) is computed
  analytically from the simulated camera's known intrinsics and pose,
  not measured.
- **Decided at runtime from sensor data.** M1 robot poses come from
  ArUco detection in the rendered overhead image, mapped through the
  homography; M5's congestion detection and the M2 decision input use
  these perception poses, not odometry. Nav2's global planner and DWB
  controller run on live rendered-lidar costmaps over the static
  map — except the 0.55 m corridor gap, which DWB cannot traverse:
  that transit is M4's scripted escort primitive driving raw
  `cmd_vel`, bypassing Nav2 and the collision monitor. The M2 decision
  (deadlock type, strategy, involved robots) is produced by the VLM
  from image + state in live runs.
- **Scripted, templated, or tuned.** M3 grounding
  (`reasoning/rag/command_grounder.py`) is a deterministic
  strategy-to-template bridge, not retrieval: `yield` expands to
  reverse-to-park, side-step 0.35 m, hold, escort the passer; `convoy`,
  `priority_override`, and waypoint-less `reroute` all degrade to a
  temporary wait; the yielder is always the first-listed robot in the
  VLM's `involved_robots`. Park position, side-step and escort length
  are computed from the robots' perceived positions and from a
  *declared* scene geometry (`scenario_geometry` in
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`: corridor
  extent, barrier height, camera height, marker height, aisle width,
  robot size, safety radius, margins) via derivations in
  `reasoning/rag/scene_geometry.py` — for `head_on_deadlock` that yields
  a park offset of ≈ 1.79 m (0.4 m of the margin is empirical — see
  `docs/implementation_notes.md`, run A) and a 0.36 m side-step. The geometry block
  is hand-maintained to mirror the Isaac scenario and warehouse configs;
  it is still scenario knowledge, but explicit and testable rather than
  embedded in M3. M5 congestion detection is rule-based (stall ≥ 12 s without
  progress, or a close/slow pair; thresholds in
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`). The
  `head_on_deadlock` scenario itself was tuned iteratively — corridor
  width, spawn positions, backup/escort distances, hold, stale
  threshold, safety envelope — until the deadlock forms and the
  maneuver succeeds; the corridor is physically passable two-abreast,
  and the deadlock is enforced by the 0.45 m safety envelope (comment
  in `isaac/config/scenarios/head_on_deadlock.yaml`). Deadlock onset
  is not deterministic across runs: since visual meshes were added to
  the robots (2026-09-16), robots are mutually visible to lidar, and
  onset has been observed both as a planner stall at ~1 m separation
  and as a nose-to-nose standoff (`docs/implementation_notes.md`, M6,
  2026-09-16).
- **Implication.** The decision-source comparison remains valid
  because the execution layer is fixed and identical across arms; the
  apparatus does not support claims about autonomous localization,
  generalization beyond the tuned scenario, or Nav2's resolving the
  corridor unaided. Successful resolution in pilot runs demonstrates
  that the pipeline functions, not that the VLM adds value over a
  rule-based decision — that is precisely what Arm B tests.
