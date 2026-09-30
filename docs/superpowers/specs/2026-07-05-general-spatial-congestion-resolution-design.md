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
- Rev 8.6 (2026-09-18): modality-condition input table gains an
  `include_visual_crosscheck` row, `—` in all three columns (an
  off-by-default diagnostic ablation, not a registered condition), with the
  prereg implication that every reported Arm A decision must name its prompt
  variant. Evidence that Arm A's decision is text-driven under the registered
  variant — `gemini` and `openai` both followed the text state block in 100%
  of incongruent image/state trials — is in
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`.
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
    required. This is more than a schema addition: it is also a **permanent
    Arm A stimulus change**, since it has no OFF condition — the
    output-format bullet, the extended `<think>` step, and the removal of
    the old `strategy="yield" (first listed robot backs up)` clause apply to
    every request from this commit onward (module-2 FR2.1.9). Before this
    field, downstream grounding read list position in `involved_robots` as
    the yielder channel; a census of 524 decision artifacts found `robot_1`
    listed first in 44/44 `yield` decisions, i.e. position was never
    observed to carry a choice (design review Finding 2) — though that
    census was collected under a prompt that instructed "first listed robot
    backs up", so 44/44 is substantially compliance with an explicit
    instruction, not only an unused channel.
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
- Rev 9 (2026-09-29): absorbs the pre-registration amendment set
  (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`, A1–A10
  and the freeze checklist, items 1–26) in place — the built battery (T0
  `normal_flow`, T2a `_bshort`, T2b `t2b_flow_ordering`, T3a
  `blocked_path_*`, T3b
  `obstacle_in_candidate`, T3c `dynamic_anomaly_v2`), random seeded
  presentation order, the pre-gate RQ3 scoring rule, position-verified
  outcomes, distance-channel safety reporting, the gpt-4o/ER-2 model table,
  episode, provenance and failure-context-depth rules, the Arm B at-goal
  exclusion, prompt v2 / stage-2 v3 and the corrected T3a/T3b tests — with
  inline `Rev 9:` supersession notes and `[REV9-OPEN]` markers for questions
  the amendments leave unresolved.
- Rev 9.1 (2026-09-29): the nine `[REV9-OPEN]` markers are replaced by
  coordinator resolutions, each marked reviewable at the tag; the T3b
  oracle rationale is neutralised (`a7730ee`), and decision artifacts record
  the served model while the rescorer credits latched-at-goal arrivals
  (`37a0dd5`).
- Rev 9.5 (2026-09-30): absorbs the coverage-battery amendments
  (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`, items 28–30
  and the Rev 17–20 records) in place — the B1 `bottleneck_merge`, B2
  `priority_urgent_r1`/`_r2`, and B3 `convoy_counterflow` scenes
  (`16df6d5`…`5dbb3a5`) and their run-matrix cells, the STRATEGY-REGRET
  metric (amendments item 29) and its first frozen B1/B2 cost-table
  instances, per-class gate-flow/%CP/censored-omitted-queue metrics, the
  coverage-check scoping sentences (`reports/Congestion scenario coverage
  check.md`), a new prereg-v2 registry section, and the Arm B held-robot
  exclusion generalized beyond A10 — with inline `Rev 9.5:` supersession
  notes (including two stale rev-9.4 FCFS-text corrections this document
  never carried through), and `[REV95-OPEN]` markers for the two apparatus
  defects Rev 20 opened (a: B1's DEFAULT-retreat backup failure; b: B3's
  robot_4 dispatch gap) and the residuals they leave.
- Rev 9.4 (2026-09-29): factual correction — head-on FCFS at equal speeds is always a tie and the tiebreak yields robot_2, so every `fcfs_yielder: robot_1` record was wrong; the family manifest and YAMLs are corrected at `6d511be`, `contrasts_fcfs` flips on 7 rows, and any FCFS-contrast cell reads from the corrected manifest. Scoring is unaffected (rev 9 scores Arm B's ACTUAL answer).
- Rev 9.3 (2026-09-29): T1 amendment by user decision C — `intersection_bottleneck` removed from the non-inferiority tier (structurally unresolvable by the single-yield primitive; Arm B's own answer inexecutable 33/35 live, the executable yield correctly held by the pair-scoped latch) and replaced with `head_on_asymmetric_wopen_eopen_o0`; the realigned scenario becomes the new log-only T1-X classification cell (10 probes, RQ1 only); multi-axis M3 grounding recorded as a prereg-v2 candidate.
- Rev 9.2 (2026-09-29): T1 tuning basket (amendments item 14) — new Arm B
  parameter `fcfs_zone_radius_m` 1.0 m added to the tuning-parity list;
  M1 thresholds, Arm B `stopped_speed_mps` and the M4 speed rule kept
  (`docs/reports/2026-09-29-t1-tuning-basket.md`).

Status: **rev 9.5 — the binding text for the `prereg-v1` tag** (the tag
does not exist yet; nothing here is frozen until it does). From rev 9 this
document is authoritative; the amendments document remains the historical
decision record, and its item numbers are cited below as "amendments A*n*"
or "amendments item *n*". Still open before the tag: amendments items 7
(keep the symmetric-`reverse` dispatch nicknamed **"B1"** in the pilot
findings, `docs/reports/2026-09-25-overnight-findings.md` §J item 3 —
unrelated to the rev-9.5 coverage scene `bottleneck_merge`, also
nicknamed B1; disambiguated on first use in this document), 9 (the
prompt-template hashes, the one model-table row still REQUIRED, plus the
tag-time `gpt-4o-2024-08-06` pin in `config/models.yaml`), 14 (T1 tuning
basket; discharged pending coordinator review at Rev 9.2),
the item-15 wording veto, the explicit confirmation of the prompt-v2 goals
rider (items 10/13), the coordinator defaults marked "reviewable at the
tag" (items 15, 17 T2b defaults, 17a, 17b), and the nine rev-9 open
questions, now settled as coordinator resolutions (Rev 9.1) that are
likewise reviewable at the tag.
Residuals those resolutions leave open are named where they occur: the
absent-decision rule for T0 and T2 RQ3 (run-matrix notes) and T0's
`prompt_static_obstacles` value (per-tier channel table).
**Rev 9.5 open items** (amendments items 28–30, Rev 17–20). A
`[REV95-OPEN]` marker recurs in the body at each place a distinct item
below is discussed (several appear in both a battery entry and the
measurement plan or run matrix); this list names each distinct item once:
the B1 trial-counting denominator (no-event/censored episodes;
run-matrix notes); the B1 STRATEGY-REGRET table's censored reference arm
(measurement plan); whether B2's STRATEGY-REGRET is interpretable at
n = 2 seeds/arm at all, and if so which arm is the reference — the
cost-minimizing arm or the `urgent_first`-correct arm (measurement plan,
battery entry); the scoring rule for DEFAULT-retreat B1 trials pending
apparatus defect (a)'s verdict, keyed on the executed candidate rather
than only `retreat=default:no_choice` (measurement plan); B3 outcome
collection gated on apparatus defect (b), and B3 having no cost table or
margin at all yet (scenario battery, run matrix); whether B1's and B2's
cells belong in the "VLM can" success-criteria conjunction (success
criteria); the B2 and B3 `prompt_static_obstacles` collection-value
mismatch against their T1/T2b bases (per-tier channel table, two rows);
the Rev 20 vs. YAML/notes discrepancy over the adopted geometry's
floor-clearance margin, "≥ 0.167 m" vs. 0.267 m (scenario battery); the
container-vs-local suite baseline split (58/2921 vs 63/2926 —
re-baseline the container before the tag); and whether the B-scene
cost-table values, which live under the git-ignored `data/logs/vm_runs/`
tree, need a
YAML-side freeze point the way T2b's margin got one (`7400482`) rather
than resting on this document's text alone.
Predecessor system: the verified head-on yield protocol (H3 runs 8–13) and
the M1→M5→M2→M3→M4 closed loop, live on the GCP/Isaac host.

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
  oracle-scored on T2). *Rev 9 (amendments A3):* oracle agreement is
  scored on each reasoner's **pre-gate** named assignment
  (`decision.yield_robot`/`crossing_order` for Arm A, the FCFS answer
  for Arm B), never on the post-gate executed assignment — see "M3 yield
  feasibility gate" in the arms section.
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
- **Presentation order (rev 9, amendments A2):** `prompt_robot_order:
  random`, seeded per run (`prompt_robot_order_seed`, else derived from
  `VGU_RUN_ID`), drawn **once per episode** and constant across that
  episode's re-analyses. With two scene robots the draw is
  `id_asc`/`id_desc`; with three or more it is a **uniform permutation**
  (`9d20b39`; before that fix `random` never listed `robot_2` first at
  N = 3). Every decision artifact records `robot_presentation_order`,
  `prompt_robot_order_mode`, `prompt_robot_order_seed` and
  `episode_index`. **Every analysis of an obstacle-channel or feasibility
  effect conditions on the drawn order**: under `id_asc` the first-slot
  and `robot_1` priors coincide and swamp the feasibility evidence, so an
  unconditioned rate averages an observable cell with a blind one
  (findings Rev 6 §T, Rev 7 §AA). Per-cell drawn-order counts are
  mandatory reporting; cells the draws leave empty are filled with
  forced-order runs, labelled as such (findings Rev 7 §Z: batch 2 drew
  order perfectly aligned with side).
- **M3 yield feasibility gate (rev 9, amendments A3):**
  `grounding_yield_feasibility: "swap"` (quoted; a bare `off` is YAML
  `false`) in the shared M3 grounding stage, with
  `yield_robot_grounded_from`, `yield_regrounded_reason` and
  `yield_refusal_reason` in every artifact. Because grounding is shared,
  the gate would also rescue Arm B's FCFS pick; RQ3 is therefore scored
  **pre-gate** (see RQ3), while the episode outcome includes the gate
  identically in both arms. The claim that the gate is *necessary* is
  scoped to prompt-v1-era evidence: in the prompt-v2 calibration pilot
  gpt-4o named the feasible `robot_2` on `_bshort` west 3/3 (gate 0/3),
  cause ambiguous at n = 3 between the sim-time-era trigger scenes and
  v2's rendered goals (amendments item 16(a)); the gate stays, as a
  no-op on feasible namings.
- **Episode rule (rev 9, amendments A7):** an episode is M5's
  `AttemptMemory` scope — opened by a trigger on a robot set disjoint
  from any open episode, closed only on a position-check-accepted arrival
  of a tracked robot; the presentation order is drawn once per
  episode. Solo-stall triggers enter the M2 pipeline and legitimately
  open episodes; every per-episode analysis touching the opening strategy
  conditions on trigger type (solo vs pair stall; findings Rev 6 §U).
  **Three or more robots (T2b, `f76ae31`):** a solo stall outside a busy
  command of two or more robots is *folded* — no analysis starts, and the
  robot joins the episode's members and `AttemptMemory` scope; members
  include dispatched command robots, overlap is tested against the
  members, and the episode closes on the **last** member's arrival. The
  fold has no proximity test: any 3+-robot scene defers a solo stall
  anywhere during another pair's command until that command resolves (a
  watch item). Two-robot semantics are pinned unchanged.

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
- **Parked-at-goal exclusion (rev 9, amendments A10, `5e13805`):** the
  `blocked_path` candidacy and the `unknown` involved set exclude a
  stopped robot within `arrived_exclusion_radius_m` (default 0.35 m,
  aligned with M5's `arrival_position_tolerance_m`) of its own goal. The
  head-on and intersection rules and the robot-ahead blocker check are
  unchanged — an arrived robot can still block another — and a goalless
  robot is never excluded. Evidence: the T0 verification run's classical
  shadow classified 60/60 parked-phase probes `blocked_path`/`anomaly`/
  `reroute`; replaying all 65 recorded probe scenes, the old rule
  reproduces 60/5 and the new rule gives 65× `none` (findings Rev 15 §AS).
  **A10 is a rule-gap fix, not tuning** (coordinator resolution
  2026-09-29, reviewable at the tag). It corrects a category error — a
  robot stopped at its own goal is not congestion — rather than fitting a
  threshold to improve a score, so it sits outside the tuning-parity
  clause below. Its provenance is disclosed: it was found on
  T0 (test-tier) probe data. The tuning-parity rule continues to govern
  threshold values, A10's `arrived_exclusion_radius_m` included.
- **Held-robot exclusion (rev 9.5, amendments item 28, `2f5a2d1`; an
  A10-mold rule-gap fix, generalizing A10 beyond parked-at-goal):**
  `blocked_path` candidacy and the `unknown` involved set additionally
  exclude a robot in the latest frame's `held_robot_ids` — M5's
  `start_pending`, fed from `TaskRegistry.is_pending` (B1's `robot_3`,
  B3's `robot_3`/`robot_4`). A robot M5 has not yet sent anywhere is not
  stalling, so it is excluded exactly like a parked robot: no
  `blocked_path` candidacy, not in the `unknown` involved set. **Candidacy
  only** — the held robot still counts for `head_on` and `intersection`,
  **including the `head_on` crowding check**, and as another robot's
  blocker. Coordinator ruling (amendments Rev 18 (a)): the exclusion is
  **not** extended to the `head_on` crowding check, so Arm B answering
  `unknown` → `temporary_wait` on 10 of 45 crowded B3 grid cases is
  recorded as the baseline's own limitation, not a further rule change —
  see the B3 battery entry. Provenance disclosed: found on the B1 and B3
  standoff grids (unified scene design). The tuning-parity rule is
  unaffected: this is a category-error fix, not a threshold change.

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

*Rev 9 notes (live behavior, not rule changes).* At a symmetric standoff
the FCFS yielder is a live coin flip: in the T2b smoke Arm B yielded
`robot_1` in only 3/6 runs (finding F4, notes 2026-09-29), although
`t2b_flow_ordering.yaml` records `fcfs_yielder: robot_1` *(Rev 9.5: this
sentence is now stale text this document never carried through the rev-9.4
correction — `6d511be` corrected `t2b_flow_ordering.yaml`'s
`fcfs_yielder` to `robot_2`, verified in the committed YAML)*. Arm B's RQ3
score is the FCFS answer Arm B actually produced on each decision
(amendments A3) — its executed decision, or in Arm A episodes the pick
the shadow block recorded — never the YAML's `fcfs_yielder`. Arrival stamps are censored when a
robot spawns on the conflict-zone boundary (`censored_arrivals` flag;
findings Rev 14 §AQ); the zone radius versus the 1.5 m spawn distance is
in the T1 tuning basket (amendments item 14). *Rev 9.2:* the basket
decoupled the head_on FCFS zone from `r_conflict` — a new
`fcfs_zone_radius_m`, 1.0 m (`caaf95f`), dates arrivals and commitment
while `r_conflict` 1.5 m still decides the head_on pairing
(`docs/reports/2026-09-29-t1-tuning-basket.md`).

### Stage-2 control

Geometry-max ranking over the identical validated candidate set (Pillar
2's deterministic ranker). By construction, Arm A's stage-2 fallback IS
Arm B's stage-2 answer — the fallback is the control.

### Tuning-parity rule (pre-registered)

Arm B parameters (`r_conflict`, `r_block`, angle windows, arrival-tie
window, the head_on FCFS zone radius `fcfs_zone_radius_m`) may be tuned **only on T1 scenarios, only before the
pre-registration freeze** (see Run matrix). They are frozen at the
`prereg-v1` tag together with this document. Any post-freeze change
invalidates affected collected cells, which must be re-run. This
preempts both "strawman baseline" and "tuned-on-test" critiques.

*Rev 9 status.* Arm B's reasoning core is merged (`65cc850`) and its
shadow logging is live on every analysis (`6d70238`, merged `97634be`).
Pre-freeze rule changes on record: the parked-at-goal exclusion
(amendments A10, above; classified a rule-gap fix, not tuning). Still to
do before the tag (amendments item 14, T1 only): `stopped_threshold_mps`
(parked STOPPED/SLOW flicker, ≈4× more transitions since sim-time stamps),
the FCFS conflict-zone radius versus the 1.5 m spawn distance
(censoring), Arm B `stopped_speed_mps`, and the M4 0.2 m/s speed-rule
margin versus Nav2's 0.18 m/s cap. *Rev 9.2:* discharged pending
coordinator review — `fcfs_zone_radius_m` 1.0 added, the other four
values kept (`docs/reports/2026-09-29-t1-tuning-basket.md`).

---

## Scenario battery (the discriminating instrument)

- **T0 Negative controls (log-only probes):** normal-flow episodes with
  no congestion; stage-1 analysis is invoked off-trigger on probe frames
  in **log-only mode** (no command may be emitted — enforced, tested).
  Measures the false-positive side of RQ1 that the shared trigger
  otherwise hides.
  **Rev 9 realization:** scenario `normal_flow` (two robots on parallel
  right-hand-traffic lanes, `|x| ≤ 2.5` inside the tracked ROI, 0.70 m
  pass at the nadir) plus M5 `t0_probe_mode` (`33232b8`…`ff96ead`):
  off-trigger stage-1 analyses every `t0_probe_interval_sec`, artifacts
  marked `probe: true` with their own order draw and null
  `episode_index`, a structural and a defensive no-dispatch layer, and a
  receipt-age gate that stops probes on a frozen scene (`089d56e`).
  Live-verified (findings Rev 15 §AS, Rev 16 §AT): zero dispatches, zero
  M4 traffic beyond base missions, ER-2 false positives 0/28 distinct
  scenes. **Collection-protocol note:** that run yielded only 5
  moving-phase scenes (22 parked, 1 transitional), so reaching 20
  informative probes needs looped tasks or several runs per cell. T0
  carries no `oracle:` block: every probe scene is non-congested by
  construction, so any `congestion_detected=true` answer is a false
  positive. **Denominator** (coordinator resolution 2026-09-29,
  reviewable at the tag): the false-positive criterion runs over **20
  distinct moving-phase probe scenes**, collected via looped tasks or
  multiple runs. Parked-phase
  probes and frozen-replicate probes (the same scene re-probed) are
  reported as separate strata and do not count toward the 20.
- **T1 Geometry-sufficient** (non-inferiority tier): `head_on_deadlock`
  (0.55×2.0 corridor) and `head_on_asymmetric_wopen_eopen_o0` (the
  validated symmetric-open family variant). Classical solves these; the
  VLM must match it. *Rev 9.3 (user decision C, 2026-09-29):
  `intersection_bottleneck` is REMOVED from this tier — the 2026-09-29
  smoke (`data/logs/vm_runs/intersection_smoke/`, notes `c58f688`)
  established the four-way plus geometry is structurally unresolvable by
  the single-yield primitive regardless of the reasoner: Arm B's own
  grounded answer was inexecutable in 33/35 live analyses, and the one
  executable yield was correctly held by the pair-scoped safety latch
  (the yielder sits < 0.45 m from robots outside its exempt pair). This
  is recorded as an architecture finding, not a reasoner result. The
  scenario itself (realigned at `49ac434`) moves to the new
  T1-X classification cell below; multi-axis M3 grounding is a
  prereg-v2 candidate.*
- **T1-X Intersection classification probes** (log-only, RQ1 only):
  the realigned `intersection_bottleneck` run with `t0_probe_mode`
  machinery — the standoff forms and is probed; no resolution is
  attempted or scored (it is structurally impossible, above). Scores
  stage-1 classification (`type`, involved set) for Arm A against the
  authored ground truth, with the Arm B shadow's `intersection` verdict
  (35/35 correct in the smoke, zone `crossing_1`) recorded per probe.
  n = 10 standoff-phase probes.
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
  robot_1`, FCFS happens to be right — included to expose robot-id bias)
  *(Rev 9.5: this framing is backwards under the rev-9.4 correction, never
  carried through here — a full-tie FCFS nominally yields `robot_2`, so
  `w0p2_eopen`'s `correct_yielder: robot_2` matches the nominal FCFS pick
  (`contrasts_fcfs` nominally **false**) and `wopen_e0p2`'s `correct_yielder:
  robot_1` is the member that nominally **contrasts** it; the live picks
  are coin flips around the tie regardless, so no score is affected, per
  rev 9.4)*,
  both against the `head_on_asymmetric_wopen_eopen_o0` T1 control. Design:
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
  (rev 2); frozen parameters and oracles: `family_manifest.csv`. The
  **oracle-agreement claim** these two variants exist to support is not
  currently answerable by Arm A as prompted (rev 8.6, above; design review
  Findings 1–2) — collecting it needs the `yield_robot` field and the
  static-obstacle modality named in the Arm A pre-registration first.
  *Rev 9: the two ±2.5-goal variants above are superseded as the T2a
  instrument (amendments A1).*
  **Rev 9 T2a instrument (amendments A1):** the cells run on
  `head_on_asymmetric_w0p2_eopen_bshort_o0` and
  `head_on_asymmetric_wopen_e0p2_bshort_o0` — blocked-side goal at the
  blocked robot's spawn (±1.5), open-side passer goal at ±2.6, spawns,
  blockers and oracle blocks byte-identical to the v1 variants (`e708ffa`,
  `dcfa144`). The v1 ±2.5 goals put the blocker on the passer's goal path
  (5 of 12 pilot episodes lost); the symmetric `_gshort` ±1.5 goals put
  the passer's rest pose in the yielder's return path. The passer goal
  was widened 2.5 → 2.6 to take the designed escort-endpoint margin from
  0.061 m to 0.161 m; Nav2 stops the passer ≈0.07–0.10 m short, so the
  realised margin is 0.063–0.096 m. Validation: east 3/3 and west 3/3
  position-verified (findings Rev 10 §AI), and the gpt-4o pilot 6/6
  (Rev 13 §AO). Attached conditions: arrival re-scoring carries the
  `box_overlap` flag (`8e77bc4`; the blocked-side goal leaves 0.13 m
  chassis-front clearance to the box near face, so the 0.35 m tolerance
  could otherwise accept an overlapping pose); operator steps are part of
  the protocol — `orchestrator.yaml` `initial_tasks` hand-set per variant
  (M5 does not read scenario-YAML goals), scenario USDs regenerated after
  any YAML change, installed configs verified by content/md5, never by
  build exit code. The `yield_robot` field exists (rev 8.6) and the
  static-obstacle channel is implemented. Its pre-registered per-tier
  value — on for T2a — is pinned in the **per-tier channel table**
  (modality section, after the condition table; coordinator resolution
  2026-09-29, reviewable at the tag).
- **T2b flow ordering (rev 9 realization; amendments item 17):** built on
  the user's 2026-09-28 BUILD decision as `t2b_flow_ordering` — a
  symmetric open head-on between `robot_1` (west, spawn −1.5, goal +2.5)
  and `robot_2` (east, spawn +1.5, goal −2.0), both retreats feasible,
  with `robot_3` queued behind `robot_1` (spawn −2.45, goal +1.85) as
  eastbound downstream traffic, held stationary by
  `initial_tasks.robot_3.start_delay_sec: 55` so that it is tracked but
  not moving at the trigger (validated in the smoke: stationary 6/6, RTF
  0.34, 11–12 s headroom). Oracle: `robot_2` yields,
  `correct_order: [robot_1, robot_3]`; FCFS contrasts only by chance
  (see the FCFS rev 9 note). Tier-scoped apparatus differences, stated
  as such in the pre-registration (coordinator defaults, reviewable at
  the tag): **(a) legacy grounding** — T2b runs with `config/rag.yaml`
  `grounding.mode: legacy` in both arms, because derived mode breaks
  both orders geometrically (backup clearance versus the queued robot;
  escort end versus the passer goal), the tier tests ordering rather
  than retreat selection, and legacy is the only mode with the
  first-passer guard; T2b decisions are therefore not poolable with
  derived-mode decisions; **(b) corridor 1.0 m** (barrier 0.55 × 1.0 m
  at x = 0), not the family's 2.0 m: M4's ordered release drives every
  passer to the yielder's park point + 0.65 m, and with a 2.0 m corridor
  `robot_3`'s escort end sits 0.06 m from `robot_1`'s goal, so even the
  oracle order would latch; **(c) the censored-margin rule** (below,
  oracle blocks). Required safety changes landed first (pair-scoped
  exemption with fail-closed semantics and a bystander guarantee,
  hold-until-last ordered release, first-passer guard; `9c38042`…
  `b0ff818`) and were verified live: the bystander latch held the
  alternative arm's `robot_2`+`robot_3` pair at 0.43 m with zero
  contacts on both seeds. Three-robot smoke PASS (ordered release live,
  `robot_3` admitted 0.04 s after `robot_1` clears, all arrivals
  verified; notes 2026-09-29). Arm B still sees a two-robot `head_on`:
  the stationary `robot_3` is > `r_conflict` from both pair members
  (unit-pinned). Watch items: the episode fold (arms section) was not
  exercised in the smoke; `run_simulation --duration-sec` is a dead flag
  (Isaac stops at the YAML's `duration_sec`); `robot_2`'s return leg
  stalls 8–19 sim-s at the east aisle mouth in every oracle run.
- **T3 Semantics-required** (only-VLM tier): (a) paired blocker
  counterfactuals — near-identical geometry, static object vs. transient
  agent (divergent correct responses: `reroute` vs. `temporary_wait`);
  (b) obstacle-in-candidate — an **untracked** visual obstacle inside
  the geometry-max retreat candidate (classical picks it; the correct
  choice requires vision); (c) `dynamic_anomaly` timed-obstacle runs
  (rev 9: `dynamic_anomaly_v2`, below).
  M1 tracks only ArUco robots, so untracked elements exist in the image
  and in NO text channel — this asymmetry makes T3 vision-load-bearing
  by construction.
  - **T3a, rev 9 realization — `blocked_path_object` /
    `blocked_path_transient`** (`ad379f1`…`71f6fdd`; both members
    mock-smoked PASS). A `blocked_path` scene: `robot_1` transiting its
    lane meets a blocker; `robot_2` runs the north pocket, out of
    conflict. The members are byte-identical except the blocker entity
    and the oracle block: a static box (`object` → `reroute`) versus an
    **unmarked robot-shaped agent** (zero M1 detections; `transient` →
    `temporary_wait`), which is "not a robot" because "robot" means a
    *listed* robot (amendments item 15(b), confirmed). **Decision-scored,
    no outcome contrast (amendments item 17a / item 18):** in this
    apparatus `reroute` re-sends the goal M4 already re-sends every 2 s,
    so the object member cannot resolve under any strategy and the
    transient member resolves under any once the blocker despawns; T3a
    is scored on the decision — the divergent-and-correct rate against
    the per-kind strategies and the `blocker_kind` verdict — with the
    classical shadow's forced `object`/`reroute` recorded on every T3a
    decision. **Recorded apparatus deviations (amendments item 17b /
    items 19–20, reviewable at the tag):** the transient blocker is the
    robot visual scaled **1.82×** so the 0.182 m single-plane lidar
    intersects a plate (at 1× only the 7 cm head is scannable and Nav2
    plans around it) — a visible size confound between the transient
    agent and the tracked robots, accepted with this record; both
    blockers spawn via `timed_obstacles` at 16 s on byte-identical maps
    (a baked or t = 0 box strands the robot at spawn or moves the stall
    point ≈1.5 m, and the members must differ only in the entity);
    corridor 0.50 m (versus T1's 0.55) for closability; per-robot task
    labels differ truthfully (`traverse_aisle`) and render in v2 prompts.
  - **T3b, rev 9 realization — `obstacle_in_candidate`**
    (`e205f5f`…`19fafa0`; mock-smoked PASS, parallax PASS). A head-on
    yield where `robot_1`'s k = 3 retreat candidates are A (+0.36 m),
    B (−0.36 m) and C (+0.72 m) at the park point x = −0.323 in the
    junction, and an untracked 0.40 × 0.30 × 0.35 m box fills C — the
    geometry-max `ranked[0]`, hence the stage-2 default and Arm B's
    stage-2 answer (pinned over 269 parameter cases). Deviation from the
    `wopen_eopen` shape (corridor 1.6 m, shifted east to put the park
    point in the junction) is justified in the YAML header. Requires
    derived grounding and stage 2 (see Decision flow) with a widened
    `grounding_aisle_y_band_m`. **Yielder conditioning (amendments item
    23, user-approved 2026-09-28):** only `robot_1` works as the yielder
    in this geometry (a `robot_2` yield's top candidate lies inside the
    NE rack past the image edge), so T3b is scored on
    executed-`robot_1`-yield trials only, in both arms, with the discard
    rate reported; no scene or gate change. **Outcome contrast:** the
    occupied-default run shows the real one — M4's sidestep (raw
    `cmd_vel`, no Nav2 or collision-monitor guard) drives the yielder
    into the box and pins it until the wall-clock bound fails the yield
    (amendments item 25; in T3b this contact is the *intended* outcome
    mechanism). Oracle `rationale` wording: neutralised per amendments
    item 24 (`a7730ee`; coordinator resolution 2026-09-29, reviewable at
    the tag). It now states only the construction: C is occupied and is
    `ranked[0]`, either unoccupied candidate is correct, and the scoring
    is the occupied-choice rate below chance 1/3 on answered stage-2
    trials with `robot_1` as the executed yielder. No test pins the
    rationale text; the scenario suite passes unchanged.
  - **T3c, rev 9 realization — `dynamic_anomaly_v2`** (`89884a3`;
    re-authored after the `dynamic_anomaly` smoke found six defects,
    findings Rev 15 §AS). `normal_flow`'s lanes; a 0.3 × 1.05 m box at
    (1.5, −0.075), active 30–110 of 200 sim-s, spanning `robot_1`'s lane
    so the detour is physically denied; untracked, in no text channel
    (`prompt_static_obstacles` off), not baked into the Nav2 map.
    Mechanically smoked PASS (findings Rev 16 §AT); the first model
    answers came in funded battery 1. Descriptive tier, **exempt from
    the mandatory `oracle:` block** (coordinator resolution 2026-09-29,
    reviewable at the tag): T3c records its expected mechanics in
    `expected_conflict` only. A `blocker_kind`
    oracle would be ill-posed here, because the despawning pallet (the
    0.3 × 1.05 m box above) is box-shaped and transient at once: in funded
    battery 1 both models called it `object` (notes 2026-09-29), a
    reasonable reading of its appearance rather than a miss.
- **Coverage battery (rev 9.5, amendments item 28, Rev 17–20; unified scene
  design `docs/superpowers/specs/2026-09-29-unified-scene-design.md`,
  `3b3a529`):** three scenes closing the bottleneck/priority/convoy gaps the
  coverage check identified (`reports/Congestion scenario coverage
  check.md`), built on the existing C55 single-lane aperture module under
  the **CONSERVATIVE migration** (existing scenes grandfathered, deviations
  D1–D3 recorded, zero re-validation runs). Shared build items, landed
  `16df6d5`…`ae11362`: the held-robot exclusion (below, Arm B section) and
  the `convoy`/`priority_override` grounding alias (`cb44d7a`, tag
  `strategy=aliased:*`; **pooling addendum** — no decision carrying those
  strategies pools across this commit, measurement-plan pooling rule (e)).
  - **B1 `bottleneck_merge`** (type `bottleneck`, 3 robots): `robot_1`
    (main-aisle lead) and `robot_3` (held, `start_delay_sec: 80`) approach
    the A55-E gate from the west; `robot_2` merges from the north arm; no
    robot opposes another. The aperture is declared in no text channel
    (`static_obstacles: []`, `prompt_static_obstacles: false`), so the
    `bottleneck` type call rests on the image — the registered
    image-only/text-only modality cell (run matrix) measures that
    dependence. Trimodal onset by design (`robot_1` leads `robot_2` to the
    gate by Δt ≈ +1.4 s nominal): the designed perpendicular latch
    (0 < Δt < ~2.5 s), a no-event episode (Δt ≥ ~3 s, counted, never
    re-run), and a same-direction follower latch (Δt < 0, censored as an
    apparatus failure, counted).
    **Geometry FIXED at `5dbb3a5`:**
    `scenario_geometry.corridor.half_length_m` 0.6 → 1.1 in
    `orchestrator.yaml`'s B1 goal-table row,
    after two other levers (shifting the gate east; moving `robot_2`'s
    spawn ± 0.2–0.35 m) were GPU-probed and rejected on measured data, not
    hand-derived. At 0.6 the crossing-arm escort formula
    (`required_escort = half_length_m − robot_1.x + 0.65`) gave a
    **required** escort of only 0.77–0.87 m across all 8 measured GT
    trigger poses — **short of** the 1.0 m `escort_band_m` floor every
    time, grounding the oracle yield infeasible — 7 of those 8 poses the
    untested LEVEL_OR_PAST sub-case (`robot_2.x < robot_1.x`) the pre-fix
    constraint grid excluded from every feasibility check. The formula has
    slope 1 in `half_length_m`, so raising it 0.6 → 1.1 (+0.5) shifts every
    pose's required escort by the same +0.5 m: **≈ 1.27–1.37 m at 1.1,
    derived, not separately tabulated**, giving a floor-clearance margin
    of ≈ 0.27–0.37 m — the tightest pose (`SW1_wait_s42`) at ≈ 0.267 m,
    which reproduces the YAML's own figure. **Discrepancy, not resolved
    here:** amendments Rev 20 states the margin as "≥ 0.167 m," a figure
    the YAML header and the implementation notes instead attribute to
    `half_length_m` **1.0** (the bare-minimum candidate, not the adopted
    1.1, where they both give 0.267 m at the tightest pose). Flagged for
    reconciliation, not adjudicated by this absorption. The design grid's
    four nominal standoff poses (a *different*, smaller set than the 8
    measured GT poses) give post-fix escorts `robot_1` 1.55–1.85 m,
    `robot_3` 4.20 m (both +0.5 m over the pre-fix design-grid values
    1.05–1.35 m / 3.70 m). **The oracle is
    feasibility-determined, like T2a:** a `robot_1` yield is refused (no
    backup distance in `[0.5, 2.0]` m keeps the 1.7 m clearance with
    `robot_3` behind it) and **degrades to a reroute of `robot_1` alone —
    it is NOT re-grounded to `robot_2`**, because the frozen `swap` gate
    (amendments A3) needs static obstacles to re-ground onto, and B1
    declares none (amendments Rev 18 ruling (b); corrects the unified
    scene design's contrary "re-grounded to robot_2" reading at its line
    ~555). `correct_yielder: robot_2`, `feasible_yielders: [robot_2]`,
    `correct_order: [robot_1, robot_3]`; the forced-order harness has no
    executable alternative arm, so **the margin is absent by construction,
    not measured**; the YAML's `fcfs_yielder: robot_2` is a naive-FCFS
    annotation for the record, never an Arm B answer — Arm B never
    classifies this scene `head_on` or `intersection`, so its FCFS rule
    never runs here (below). Reverse-along-heading gate: `x0 ≥
    1.35·cos|θ| − 0.46` (≥ 0.174 m at −62°; amendments Rev 18); `k = 1` (a
    single valid retreat candidate) at 2 of the design's 4 stage-2 grid
    poses (pinned offline; `k` at the 8 measured GT trigger poses is
    unrecorded). **Residual, not fixed by the geometry change:** M4's actual
    reverse-along-heading backup overshoots the N-S band's west edge at 2
    of the 8 measured poses (heading −52.5°, end x −0.486; heading −55.9°,
    end x −0.466), independent of `half_length_m` (set by the 1.7 m
    clearance to `robot_1`, not the escort formula this fix touches) —
    Rev 20 calls these the "steep" measured headings while the fix notes
    and the YAML call them the "shallowest"; recorded here by heading
    degree, not adjective, pending reconciliation.
    **Apparatus defect (a), Rev 20 — OPEN:** the DEFAULT retreat candidate
    (`retreat=default:no_choice`) fails its own backup on
    `min_distance_violation`, reproduced 3/3 on every run that skipped
    stage 2; the one run that forced stage-2 candidate B via
    `VGU_MOCK_RETREAT_CHOICE_FILE` completed cleanly. This exposure is
    wider than "stage 2 was skipped": the text-only modality cell always
    hits it (stage 2 is `condition_constrained` off by the modality
    table); a `k = 1` pose (2 of the design's 4 stage-2 grid poses) defaults
    identically even when stage 2 is answered, because there is nothing to
    choose; and — only the `no_choice`-default path has been observed
    failing (3/3) — an answered stage-2 call that names the default letter
    executes the same candidate and is **unverified**, not confirmed safe.
    **[REV95-OPEN]:** the B1 scoring treatment in the measurement
    plan below is this absorption's proposal, not a recorded ruling — Rev
    20 orders "characterize + fix or scope," and the verdict belongs to
    the parallel apparatus-defect track, not yet returned.
    **Arm B** (`classify_scene`): no path to `bottleneck` — it never
    classifies this scene `head_on` or `intersection` (the goal axes are
    parallel, never crossing at 45–135°), so its FCFS rule never runs
    here. Without the held-robot exclusion: `blocked_path [robot_3]` at
    the designed standoff (`robot_2` counts as ahead of `robot_1` there),
    `blocked_path [robot_1, robot_3]` at the measured LEVEL_OR_PAST
    sub-case (7 of 8 poses, where `robot_2` no longer does). **With the
    exclusion** (`robot_3` is held, dropped from candidacy): at the
    **designed** standoff, `unknown [robot_1, robot_2]` → `temporary_wait`
    → `reroute` — the unified scene design's reading holds here. At the
    **measured LEVEL_OR_PAST sub-case** (7 of 8 poses), it does **not**:
    `robot_1` alone has no robot ahead of it once `robot_3` drops out, so
    the verdict is `blocked_path [robot_1]` → `reroute`, not `unknown`.
    **Metrics:** gate flow rate (exits at x = 1.7 per 100 sim-s, from
    first entry at x = 0.7), per-robot stop time (GT speed < 0.02 m/s,
    spells ≥ 1 s), makespan, the A4 outcome, the type label — scorer built
    at `34d6b53` (`scripts/coverage_scene_scores.py`).
  - **B2 `priority_urgent_r1` / `priority_urgent_r2`** (strategy
    `priority_override`, 2 robots): a label-counterfactual pair
    hand-authored from the validated T1 `head_on_asymmetric_wopen_eopen_o0`
    geometry — byte-identical except `name`, the two task labels, and the
    oracle block (the T3a pattern; pinned in
    `tests/unit/test_priority_urgent_scenarios.py`). The urgent robot is
    `robot_2` in `_r2` and `robot_1` in `_r1`, counterbalancing the
    robot_1 and first-slot priors. Urgency reaches the VLM only through
    the task label (`urgent_order_delivery` / `routine_order_delivery`)
    under the frozen v2 template — **no v3**: the template SHA and
    `prompt_version: 2` are unchanged. `TaskAssignment` gains
    `priority: int = 0` (additive, default 0, byte-identical when absent;
    `6dfef27`), read by M3 alone to resolve a `priority_override` answer's
    beneficiary (the registry maximum) — it is never rendered. Because two
    equal-speed robots' FCFS arrival is always an exact tie (rev 9.4), Arm
    B's answer is identical in both members (`yield`, nominal `robot_2` by
    the robot-id tie-break), so its divergent rate is 0 by construction,
    the T3a semantic-channel shape. `PriorityOracleConfig`
    (`urgent_robot`, `correct_yielder`, `correct_first_passer`,
    `classical_yielder`, `objective: "urgent_first"`). Scoring is
    decision-level by route: the yield route's first passer is the
    non-yielder, the `priority_override` route's is the registry maximum;
    both are reported. **Metrics:** divergent-and-correct rate over pairs
    (primary; one-sided 95% binomial lower bound > 0.5); %CP per episode
    (urgent robot crosses x = 0 first, from GT, tested against chance 0.5;
    scorer at `34d6b53`); urgent time-to-goal; the `priority_override`
    label rate; the A4 outcome. **Mock smoke (`bscene_smoke`, both
    members, 2026-09-29/30 — apparatus validation, not a reasoner
    result):** alias tag correct, %CP 1.0 both members,
    divergent-and-correct 1.0 both members. **STRATEGY-REGRET (amendments
    item 29), uncensored, but likely noise at this n:** the harness's two
    arms are named by who is *forced* to yield — `yield_routine` forces
    the routine robot to yield (the `priority_override` route's executed
    arm, matching `PriorityOracleConfig.correct_yielder`); `yield_urgent`
    forces the urgent robot to yield instead
    (`scripts/strategy_regret.py`'s `_b2`, the anti-priority arm). `_r1`:
    `yield_urgent` (`robot_1`, urgent, yields) 188.85 s (cost-minimizing),
    `yield_routine` (`robot_2` yields, `robot_1` passes first, matching
    the oracle) 201.95 s (**+13.1 s regret**). `_r2`: `yield_urgent`
    (`robot_2`, urgent, yields) 190.7 s (cost-minimizing), `yield_routine`
    (`robot_1` yields, `robot_2` passes first, matching the oracle) 195.8 s
    (**+5.1 s regret**); n = 2 seeds/arm each. **Caveat that undercuts
    reading this as a systematic priority-vs-cost conflict:** the two
    members are physically identical scenes (labels and the M3-only
    `priority` are the only difference), so the *same* physical maneuver
    can be compared across members — "`robot_1` yields" costs 188.85 s in
    `_r1` but 195.8 s in `_r2` (a 6.95 s spread); "`robot_2` yields" costs
    201.95 s in `_r1` but 190.7 s in `_r2` (an 11.25 s spread). Those
    cross-member spreads, for what should be the same maneuver, are the
    same size as the regrets above, and which yielder is cheaper flips
    between members. At n = 2 seeds/arm, "the urgent robot yielding is
    cheaper in both members" is not distinguishable from noise.
    **[REV95-OPEN]:** whether B2's STRATEGY-REGRET is interpretable at
    this n at all, and — separately — which arm should be the reference
    (the cost-minimizing arm, as computed above, or the
    `urgent_first`-correct arm) once/if it is. The cost-table JSON files
    sit under `data/logs/vm_runs/bscene_smoke/`, which is git-ignored
    (`data/logs/*`), so these values are frozen **in this text**, not by
    the tag over the files.
  - **B3 `convoy_counterflow`** (strategy `convoy`, 4 robots; **first to
    slip to v2** if the freeze is threatened): a T2b extension on the
    A55-J gate with **legacy grounding** (tier-scoped apparatus
    difference, as T2b). `robot_1` leads an eastbound platoon; `robot_3`
    and `robot_4` queue behind it, held (`start_delay_sec: 120`);
    `robot_2` is the counter-flow robot. Correct: one yield by `robot_2`,
    then the platoon nose-to-tail (`correct_order: [robot_1, robot_3,
    robot_4]`, `correct_strategy: convoy`, `accepted_strategies: [convoy,
    yield]`, `platoon: [robot_1, robot_3, robot_4]` — `OracleConfig`'s new
    convoy fields). `convoy`/`priority_override` ground as the ordered
    yield by the unique involved robot whose goal bearing opposes the
    majority (`cb44d7a`); in this apparatus `convoy` and "`yield` robot_2
    + platoon order" are executionally identical, so the label is scored
    separately (secondary, novelty claim, no external baseline) from the
    primary platoon-correct decision rate. Escorts, pinned (correcting the
    unified scene design's pre-measurement 3.574/4.174 m, computed from a
    rejected east-shifted queue): `robot_1`/`robot_3`/`robot_4` 1.89–1.97 /
    **3.674** / **4.244** m, every escort ending at x = 1.774. **Arm B,
    without the held-robot exclusion:** `head_on (robot_1, robot_2)`,
    `yield`, nominal `robot_2` (rev 9.4 tie-break), `crossing_order: null`,
    over 35/45 of the standoff grid; **10/45 flip** to `blocked_path
    [robot_3]` (`robot_3` within `r_conflict`). **With the exclusion:**
    those 10/45 read `unknown [robot_1, robot_2]` → `temporary_wait`
    (amendments Rev 18 ruling (a); the held-robot exclusion is
    candidacy-only and is **not** extended to the `head_on` crowding
    check, so `robot_3`/`robot_4` still count there — recorded as the
    baseline's own limitation, not a further rule change). `convoy` is
    never in Arm B's policy table: it sees only the two robots involved in
    `head_on`, so it never orders the platoon and never emits `convoy`.
    **The omitted-queue trap — Arm B's B3 outcome is censored by
    construction:** any two-robot command (Arm B's, or an Arm A answer
    that lists only the pair) leaves `robot_3`/`robot_4` outside the
    linked wait; the released queue transits past the parked `robot_2` at
    lateral 0.36 m, below the 0.45 m floor, reproducing T2b's permanent
    bystander latch. `censored_omitted_queue` flags this in the arrival
    rescorer (`4393155`). **Metrics:** platoon-correct decision rate
    (primary), `convoy` label rate (secondary, novelty), makespan and
    executed-yield count (Arm A vs. the forced-order harness's
    oracle/alternative arms — Arm B has no executed side to compare), and
    total transit time; the T1-X `intersection_bottleneck` probe's
    `convoy` count (should be 0) is a zero-build-cost negative check on
    the same label. **Apparatus defect (b), Rev 20 — OPEN, gates B3
    outcome collection:** `robot_4` never receives a "Begin
    navigating"/M5 acceptance in any of 3 B3 runs to date despite reaching
    goal in GT (0.090 m clean at the latest run); `robot_3`'s single Nav2
    leg is canceled ~8 s after starting and never retried (its
    0.3586–0.3757 m near-misses, just outside the 0.35 m tolerance, trace
    to this missing retry, not the tolerance value). No cost table or
    margin exists for B3 yet: the strategy-regret sweep and the
    four-robot forced-order harness extension were not run
    (`correct_order` is pinned; `margin: pending` in the YAML).
    **[REV95-OPEN]:**
    outcome collection stays gated until defect (b) is characterized and
    fixed or scoped by the parallel apparatus track; the mechanical smoke
    (four-stack lifecycle gate, alias tag, park position, vacated-spawn
    clearance) is otherwise replicated.
- **Authored oracle blocks:** every scored T2/T3 scenario YAML carries an
  `oracle:` block — the pre-registered correct answer and the objective
  it optimizes — authored with the scenario and frozen at `prereg-v1`.
  Descriptive tiers (T3c) are exempt (rev 9.1).
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

- **Rev 9 — realized oracle schemas** (`isaac/vgu_sim/config.py`; the
  block above is the rev-8 illustration, which mixed a T2a yielder with a
  T2b order). Three frozen, `extra="forbid"` shapes, plus a rev-9.5
  fourth:
  - `OracleConfig` (T2a, T2b, and rev 9.5: B1, B3): `correct_yielder`,
    `fcfs_yielder`, `feasible_yielders`, `objective: min_total_time_to_goal`,
    `rationale`, `correct_order` (every robot but the yielder, first to
    pass first; T2b, B1, B3) plus a `margin` record (`OracleMarginRecord`:
    oracle and alternative totals, alternative yielder/order,
    `margin = alternative/oracle − 1`, `threshold` 0.20, `censored`,
    `n_per_order`, run ids — **B1's margin is absent by construction**, no
    executable alternative arm exists; **B3's margin is `pending`**,
    the four-robot harness has not run), and rev-9.5 convoy fields
    `correct_strategy`, `accepted_strategies`, `platoon` (B3 only; a
    validator requires all three set together and `correct_strategy` to be
    a member of `accepted_strategies`).
  - `PriorityOracleConfig` (rev 9.5, B2): `urgent_robot`, `correct_yielder`,
    `correct_first_passer` (validated to equal `urgent_robot`),
    `classical_yielder` (Arm B's label-blind answer, identical in both
    pair members), `objective: "urgent_first"`, `rationale`; a
    `contrasts_classical` property reports whether Arm B's yielder is the
    urgent robot.
  - `BlockerOracleConfig` (T3a): `correct_blocker_kind`,
    `correct_strategy` (validated to be that kind's A.5 default),
    `classical_blocker_kind`, `classical_strategy`,
    `objective: blocker_kind_default`, `rationale`.
  - `RetreatOracleConfig` (T3b): `yielder`, `passer`, `candidate_count`,
    `occupied_candidate`, `correct_candidates` (partitioning the labels
    with the occupied one), `classical_candidate` (= `ranked[0]`),
    `objective: avoid_occupied_candidate`, `rationale`. Labels are M3's
    generation-order candidate labels, never the counterbalanced letters
    the VLM sees; the oracle holds only when `yielder` is the robot that
    yields.
- **Rev 9 — T2b oracle validity, censored-margin rule (amendments item
  17, coordinator default (a), reviewable at the tag):** the ≥ 20%
  dominance check is run by the forced-order harness
  (`scripts/t2b_forced_order.py`, n = 2 seeds per order). **A censored
  alternative arm counts as dominated**: a wrong order that never
  finishes within the horizon makes the alternative total, and so the
  margin, a **lower bound**; the harness labels it `LOWER-BOUND`, never
  `PASS`, and writes it to the YAML only with `--accept-censored`.
  Frozen record (`7400482`): oracle total 315.1 s, alternative total
  519.45 s (alternative ended in the permanent `robot_2`+`robot_3`
  bystander latch on both seeds, `robot_3` censored at the 300 sim-s
  horizon), **margin ≥ 0.6485, `censored: true`**. Two qualifications
  travel with it: the latch is permanent only because the mock answers
  `none` after its first call (a live VLM would get the 34 re-analyses),
  so "infeasible" means "infeasible without a second intervention"; and
  the harness's ground-truth scorer credited the latched alternative
  `robot_2` (0.09 m from its goal) as arrived at 57.5 s, which M5 and the
  rescorer never do (finding F6) — the rev-9 arrival definition in the
  measurement plan adopts the harness's reading, and crediting it lowers
  the alternative total, so the bound stays conservative.
- Authoring T2/T3 variants (scenario yamls + USD rebuilds + obstacle
  assets) is a first-class work item, not an afterthought — without them
  the experiment cannot discriminate. *Rev 9:* all tiers are built
  (`docs/superpowers/specs/2026-09-27-scenario-battery-design.md`, build
  table); scenario files under `isaac/config/scenarios/`: `normal_flow`,
  `family/head_on_asymmetric_*_bshort_o0`, `t2b_flow_ordering`,
  `blocked_path_object`, `blocked_path_transient`,
  `obstacle_in_candidate`, `dynamic_anomaly_v2` (the original
  `dynamic_anomaly` is retired from the battery).

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
| T1 non-inferiority | `head_on_deadlock`, `head_on_asymmetric_wopen_eopen_o0` *(rev 9.3: replaces `intersection_bottleneck`, structurally unresolvable — see the tier entry)* | A vs B paired, dual | 30 pairs/scenario (→ 60 by extension rule) | one-sided 95% bound on paired Δ success ≤ 10 pp (McNemar-style) |
| T1-X intersection classification | `intersection_bottleneck` (realigned, `49ac434`) | A log-only probes, dual; Arm B shadow recorded | 10 standoff-phase probes | classification accuracy vs authored ground truth, descriptive; no resolution scored; rev 9.5: add the `convoy` label count over the same probes (should be 0), zero build cost |
| B1 bottleneck (rev 9.5) | `bottleneck_merge` | A vs B paired, dual; derived | 15 pairs | Descriptive: `bottleneck` type-label rate, one-sided 95% binomial bound; pre-gate yielder/order agreement against the feasibility-determined oracle; gate-flow/stop-time/makespan (battery entry). Arm B has no classification path to `bottleneck` (structural, disclosed). **[REV95-OPEN]:** the N = 15 counting rule — whether it counts triggered pairs, event pairs only, or something else; how a no-event (Δt ≥ ~3 s) or same-direction-latch (Δt < 0) episode is counted and paired against its seed-mate — is not pinned; `scripts/coverage_scene_scores.py`'s `merge_mode` classifies the three outcomes but no T0/T3b-style denominator rule has been written for it |
| B2 priority (rev 9.5) | `priority_urgent_r1` / `_r2` | A executed (B shadow), dual; derived | 15 pairs (= 30 episodes) | Divergent-and-correct rate, one-sided 95% binomial lower bound > 0.5; secondary %CP vs chance 0.5 per member (battery entry) |
| B3 convoy (rev 9.5) | `convoy_counterflow` | A vs B paired, dual; legacy (not poolable with derived) | 10 pairs | Descriptive: platoon-correct decision rate; `convoy` label rate (novelty, no baseline); makespan vs the forced-order harness's oracle/alternative arms; Arm B outcome censored by construction (omitted-queue latch, battery entry). **[REV95-OPEN]:** collection is gated on the Rev 20 apparatus defect-(b) fix (battery entry) |
| T2 oracle agreement | T2a (`_bshort` west/east), T2b (`t2b_flow_ordering`, legacy grounding — rev 9) | A vs B paired, dual | 15 pairs/variant | oracle-agreement rate A vs B, Fisher exact, α = 0.05; scored pre-gate (rev 9) |
| T3a counterfactual pairs | `blocked_path_object` / `blocked_path_transient` | A executed (B shadow), dual (rev 9: B-executed outcome cell dropped) | 15 pairs (= 30 episodes) | divergent-and-correct rate (decision-scored): one-sided 95% binomial lower bound > 0.5 |
| T3b obstacle-in-candidate | `obstacle_in_candidate`, k = 3 candidates | A executed (B shadow), dual; 5 B executed; executed-`robot_1`-yield trials only (rev 9) | 15 scored, cap 30 episodes (rev 9.1) + 5 | rev 9: occupied-choice rate < 1/3, exact one-sided binomial, α = 0.05 (≤ 1/15 at n = 15) |
| T3c timed obstacle | `dynamic_anomaly_v2` (rev 9) | A vs B paired, dual | 10 pairs | descriptive (time-to-resolution, degradations) |
| T0 negative probes | `normal_flow` runs, `t0_probe_mode` (rev 9) | A log-only, dual | 20 distinct moving-phase probe scenes (looped tasks or several runs; parked and frozen-replicate probes are separate strata — rev 9.1) | false-positive rate ≤ 10% (≤ 2/20) |
| RQ5 adaptation | forced-failure episodes | A informed vs A memoryless, dual | 15 + 15 | Fisher exact informed vs memoryless, α = 0.05; secondary: ≥ 11/15 informed-direction (binomial vs 0.5) |
| Modality | 1 T1 scenario + T3a + T3b + B1 (rev 9.5: type-call dependence, amendments item 28) | A only: text-only, image-only | 10 per condition·scenario | descriptive deltas; T3 binomial per condition (rev 9: T3b per the corrected occupied-choice test); B1: `bottleneck` type-call rate per condition, descriptive — text-only B1 trials also skip stage 2 by `condition_constrained`, so every text-only B1 yield hits apparatus defect (a) below (measurement plan) |
| Ablation: temporal | T2b (order-sensitive) | A, dual minus traces+motion table | 10 | oracle-agreement delta |
| Ablation: annotation scheme | T3 subset | A, legacy vs legible | 10 per scheme | task-metric delta |

Seeds are drawn once per cell and reused across arms/conditions within
that cell. All tests, margins, and N values above are frozen at
`prereg-v1`; deviations are reported as protocol deviations.

**Rev 9 changes to the matrix (amendments items 17a, 17, 23–24).**

- *T3a:* the rev-8 cell read "A executed (B shadow), dual; B executed on
  5 pairs for outcome contrast | 15 pairs (= 30 episodes) + 10 B". The
  B-executed outcome contrast is dropped (item 17a): the apparatus
  offers T3a no outcome contrast, and the tier's contrast lives in the
  decision, where the classical shadow's forced non-divergence is
  recorded on every T3a decision.
- *T3b:* the rev-8 test "binomial vs. chance 1/3, α = 0.05 (≥ 9/15
  correct avoidance)" was vacuous — with k = 3 and one occupied
  candidate, chance of *avoiding* it is 2/3 (P(≥ 9/15 | 2/3) ≈ 0.80;
  item 24). The primary test is the **occupied-choice rate below chance
  1/3, exact one-sided binomial**; at n = 15, ≤ 1/15 rejects
  (P(X ≤ 1 | 1/3) ≈ 0.019; the amendments' "≈ 0.017" is P(X = 1)),
  ≤ 2/15 does not (≈ 0.079). The unit is an executed-`robot_1`-yield
  trial in both arms (item 23), with the discard rate reported; the
  item's own recommendation is to size n upward to compensate.
  **Stopping rule** (coordinator resolution 2026-09-29, reviewable at
  the tag): collect until **15 scored trials** — an
  executed-`robot_1`-yield episode whose stage-2 invocation was answered
  — with a **hard cap of 30 episodes**. The
  discard rate and the degraded rate are mandatory reporting. If the cap
  is reached before 15 scored trials, the cell is reported as
  underpowered; it is not extended.
- *T2b:* the cell is pre-registered on legacy grounding (tier-scoped
  apparatus difference; battery section), and Arm B is scored on the
  FCFS answer it actually produced, not the YAML's `fcfs_yielder` (FCFS
  rev 9 note).
- *T2a:* the variants are the `_bshort` pair (amendments A1).
- *Decision-scored units* (coordinator resolution 2026-09-29, reviewable
  at the tag). The scored unit is the episode's **first yield-deciding
  analysis**: for T3a, the first
  analysis with congestion detected; for T3b, the first answered stage-2
  invocation. The classical shadow is recorded on every analysis
  regardless. Absent or degraded decisions, per tier:
  - *T3a:* a terminal refusal, `decision=None`, or non-detection across
    the whole episode scores as a **miss**, because detection is part of
    the tier's task.
  - *T3b:* the choice test runs over **answered** stage-2 trials only.
    Refusals, timeouts and defaults are excluded from the choice test —
    stage 2 has no grey-image fallback, so a refused call defaults to
    `ranked[0]`, the occupied candidate by construction, and the default
    is not the model's choice. They are reported in a mandatory
    degraded-rate column. Validity condition: a cell with **> 30%
    degraded trials is inconclusive**.
  - *Residual, not covered by this resolution:* the absent-decision rule
    for T0 probes (not episode-based) and for T2 RQ3 remains open at the
    tag.

**Rev 9.5 changes to the matrix (amendments item 28; unified scene design
§5).** Three new cells — B1, B2, B3, above — plus the B1 modality cell and
the T1-X `convoy`-count addendum. Per-class metrics are registered with
the cells (battery entries): bottleneck (B1) gate flow rate, per-robot
stop time, makespan, type label; priority (B2) divergent-and-correct,
%CP, urgent time-to-goal, route split; convoy (B3) platoon-correct
decision, `convoy` label rate, makespan, executed-yield count. Scoring
these on the T1/T2 deadlock rubric would reproduce the coverage gap one
level down, so the per-class metrics above are the registered ones, not a
substitute for A4/A5 (still mandatory on every B-scene episode). The
STRATEGY-REGRET metric (amendments item 29) is registered in the
measurement plan below. **[REV95-OPEN]:** B1's trial-counting denominator
(above) and the B1/B3 scoring exposure to apparatus defects (a)/(b)
(measurement plan) are not settled by any record.

### Budget estimate (planning numbers)

≈ 390 episodes baseline, ≤ ≈ 510 with the T1 extension; at ≈ 5 min
wall-clock per episode ⇒ ≈ 33–43 h of simulation (batched unattended
runs on the GCP/Isaac host). ≤ ≈ 1,200 VLM calls (1–3 per episode);
hosted-API cost is negligible relative to sim time. The budget-shaping
fact: T3 effects are constructed to be large, so T3 cells are cheap;
T1 non-inferiority carries most of the episode budget. *Rev 9: not
re-costed.* The T3a B-executed cell (10 episodes) is dropped; T2b runs
three robots at RTF ≈ 0.34 (two robots ≈ 0.39); T3b's yielder
conditioning adds discarded episodes; gpt-4o refusals consume analysis
slots (amendments A6).

**Rev 9.5 budget delta (amendments item 28; unified scene design §5).**
The three new cells add **+80 episodes and ≈ 16 h** of simulation on top
of the baseline above (that is +37–48%): B1 30 episodes at ≈ 200 sim-s /
RTF 0.34 (≈ 10 min wall each, ≈ 5 h); B2 30 episodes at ≈ 200 sim-s /
RTF 0.39 (≈ 8.5 min each, ≈ 4.3 h); B3 20 episodes at ≈ 260 sim-s /
RTF 0.21 (≈ 21 min each, ≈ 6.9 h). This figure does **not** include the
B1 modality cell (10 per condition × 2 conditions = 20 more episodes, ≈
3.3 h at B1's per-episode wall time) added to the Modality row above — the
two deltas are reported separately, not summed into "+80." ≈ 80–240 more
VLM calls at 1–3 per episode; OpenAI credit is exhausted, so gpt-4o cells
are gated on a top-up (unified scene design §5, "Budget"); ≈ 15
pre-collection smoke runs.

### Pre-registration freeze

Tag `prereg-v1` freezes: this document, Arm B config/thresholds, oracle
blocks, prompt templates, and the model/decoding table. Episodes run
before the tag are pilot data, excluded from headline results.

*Rev 9 — what the tag freezes, concretely.* This document at rev 9
(the amendments document is its decision record, not a second source);
Arm B's rules including the A10 exclusion and the T1-basket values; every
battery YAML's `oracle:` block including the T2b margin record; the
stage-1 prompt template **v2** and the stage-2 prompt template **v3**
with their content hashes (v1 and stage-2 v2 stay in the tree only for
byte-identical replay of pilot artifacts); the model/decoding table
below; and the collection configuration the amendments bind —
`prompt_robot_order: random` (A2), `grounding_yield_feasibility: "swap"`
(A3), `arrival_position_check: true` with 0.35 m tolerance (A4),
`failure_context_window_sec: 60` with the A9 depth policy,
`keep_debug_frames` and `keep_raw_frames` true (A8), derived grounding
with stage 2 on (except T2b, legacy), per-tier `initial_tasks`, and the
per-tier text-channel values (`prompt_static_obstacles`,
`prompt_pairwise_geometry`; per-tier channel table, rev 9.1). At the tag,
`config/models.yaml` pins the dated `gpt-4o-2024-08-06` snapshot in place
of the alias (rev 9.1). The repo's committed `orchestrator.yaml`
defaults (for example `id_asc` and gate `"off"`) are not the collection
configuration; the installed YAML is asserted by content before every
collected run (A8). Every run of 2026-09-16 through the tag is pilot
data.

*Rev 9.5 additions to the freeze.* The four B-scene YAMLs
(`bottleneck_merge.yaml`, `priority_urgent_r1.yaml`,
`priority_urgent_r2.yaml`, `convoy_counterflow.yaml`) with their `oracle:`
blocks (B1's absent margin, B3's `correct_order` pinned but `margin:
pending` — see battery entries); the held-robot exclusion and the
`convoy`/`priority_override` aliasing commit (`cb44d7a`); the per-tier
channel table's three new rows (below). **Scenario geometry lives in
`orchestrator.yaml`'s goal table, not the scenario YAML** (each B-scene
YAML's own header says so — "M5 does not read this file"; also the
operator-steps precedent in amendments A1) — **so the freeze must also
cover the per-scene collection settings there:** B1's
`scenario_geometry.corridor` (`half_length_m: 1.1`, fixed at `5dbb3a5`,
plus its arms), `grounding_aisle_x_band_m: [-0.46, 0.46]`, and
`robot_3`'s `start_delay_sec: 80`; B2's per-member task labels and
`priority` values in `initial_tasks`, and its `scenario_geometry.corridor`
(`half_length_m: 1.0`, as shipped, unchanged from T1); B3's
`scenario_geometry.corridor` (`half_length_m: 0.5`), `grounding.mode:
legacy`, and
`robot_3`/`robot_4`'s `start_delay_sec: 120`. **The B1 and B2
STRATEGY-REGRET cost
tables are not freezable as files**: `data/logs/vm_runs/b1_fix/` and
`data/logs/vm_runs/bscene_smoke/` sit under `data/logs/*`, which
`.gitignore` excludes (confirmed by `git check-ignore`), unlike T2b's
margin, which was written into a tracked YAML (`7400482`). Until an
equivalent tracked home exists, this document's measurement-plan text is
the frozen record of the B1/B2 values, the same role the YAML plays for
T2b. **[REV95-OPEN]:** whether a tracked freeze point (a YAML `margin`-style
field, or a committed cost-table snapshot) is required before the tag, or
whether this document's text suffices, is not decided by any record.
B3 has no cost table to freeze at all (gated on apparatus defect (b),
above). The container-vs-local suite baseline split (58/2921 vs 63/2926,
Rev 20) is a pre-tag item: re-baseline the container before the tag.

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
    *Rev 9 (amendments A4):* "success" is the **position-verified
    episode outcome** defined in the measurement plan, not Nav2 goal
    success.
  - **T0 discrimination:** false-positive rate ≤ 10% on log-only probes.
    *Rev 9.1:* over 20 distinct moving-phase probe scenes; parked-phase
    and frozen-replicate probes are separate, uncounted strata (T0
    battery entry).
  - **T3 superiority:** T3a divergent-and-correct lower bound > 0.5
    (classical shadow non-divergent by construction); T3b ≥ 9/15
    avoidance of the occupied candidate (vs. chance 1/3). *Rev 9:*
    T3a is **decision-scored** — the divergent-and-correct rate against
    the pre-registered per-kind strategies (object → `reroute`,
    transient → `temporary_wait`) and the `blocker_kind` verdict, with
    the classical shadow's forced `object`/`reroute` recorded on every
    decision (amendments item 17a); no executed outcome enters it. The
    T3b criterion "≥ 9/15 avoidance vs. chance 1/3" is superseded
    (amendments item 24, user-approved 2026-09-28): **T3b occupied-choice
    rate below chance 1/3, exact one-sided binomial, α = 0.05**, on
    executed-`robot_1`-yield trials (item 23). *Rev 9.1 (coordinator
    resolutions, reviewable at the tag; run-matrix notes):* the scored unit
    is the episode's first yield-deciding analysis. T3a scores a terminal
    refusal, `decision=None` or non-detection across the episode as a
    miss. T3b's test runs over **answered** stage-2 trials only, with
    refusals, timeouts and defaults reported as a degraded rate. A T3b
    cell with > 30% degraded trials is inconclusive, and one that reaches
    the 30-episode cap before 15 scored trials is reported as
    underpowered, not extended.
  - **RQ5 adaptation:** informed vs. memoryless difference significant
    (Fisher exact, α = 0.05) with informed-direction change in ≥ 11/15
    informed episodes.
- **Partial answers are findings:** e.g., "competent arbiter on T1/T2,
  decisive only on T3 semantics" or "text-only equals dual-channel
  everywhere except T3" are publishable characterizations.
- **Rev 9.5 (B1/B2/B3):** no amendments record assigns the coverage-battery
  cells into the "VLM can" conjunction above; they are additional
  descriptive/superiority findings reported alongside it, per their
  per-class metrics (run matrix, measurement plan). **[REV95-OPEN]:**
  whether they should be folded into the conjunction (e.g., a B2
  divergent-and-correct criterion alongside T3a's) is not settled by any
  record.

---

## Model and decoding pre-registration

The apparatus supports four backends behind the `VLMBackend` protocol
(`mock`, `llama_server`, `openai`, `anthropic` in
`reasoning/vlm/backend_factory.py`) *(rev 9: five — `gemini` is also registered and
is the secondary model below)*. The research answer is scoped to
the pinned models below; the mock backend is for plumbing tests only and
appears in no reported cell.

*Rev 9 (amendments A6):* the table below replaces the rev-8 table. Rev-8
values it supersedes: primary backend "`openai` (… swap from mock is on
the critical path, blocked on API key)" — the key is live since
2026-09-16; secondary backend "`llama_server` (local; per the
2026-06-12 llama-server design)" with "exact local model +
quantization" REQUIRED — replaced by ER-2; temperature "`llama_server`
keeps the Cosmos Reason 2 CoT preset (0.6/0.95/20)" — no longer a
reported cell. `llama_server` and `anthropic` remain in the backend
factory and, like `mock`, appear in no reported cell. Values below are
read from `config/models.yaml`, `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`,
the camera config, and the `reasoner_config_effective` block recorded in
funded decision artifacts.

| Field | Value | Status |
|---|---|---|
| Primary backend | `openai` (hosted API, chat completions) | pinned |
| Primary `model_id` | `gpt-4o-2024-08-06`, pinned in `config/models.yaml` at tag time (config currently carries the alias `gpt-4o`; the API served that snapshot in the 2026-09-16 key check and the 2026-09-28 funding probe); every stage-1 `reasoner_config_effective` records the provider-reported `served_model` per call (`37a0dd5`) | pin at tag (rev 9.1) |
| Secondary backend | `gemini` — Gemini Robotics-ER 2 via the Interactions API, replacing `llama_server` (amendments A6) | pinned (rev 9) |
| Secondary `model_id` | `gemini-robotics-er-2-preview`, `thinking_level: low`, `force_schema: false`; the preview id carries no version/date and the API exposes none, so it is recorded as-is with the probe date (served 2026-09-28, funding probe) | recorded as-is with probe date (rev 9.1) |
| Temperature / sampling | gpt-4o: `temperature` 0.0 (plus the shared block's `top_p` 0.95, which the backend sends; `top_k` is omitted); ER-2: **no sampling control** — the API has no sampling fields, so the shared block's 0.6/0.95/20 are dropped and recorded per call as `unsupported_sampling` | pinned (rev 8.4; ER-2 rev 9) |
| Images per call | 1 (single-frame rule; multi-image rejected rev 6) | pinned |
| Image resolution | 1280 × 960 RGB PNG as sent (`camera.yaml`, calibration `image_size`; `frame_downscale_width: null`; stage-2 frames the same); gpt-4o requests `detail: "high"`; each provider rescales internally | filled (rev 9) |
| Max output tokens | 2048 (`vlm.reasoner.max_tokens`; `max_tokens` for gpt-4o, `max_output_tokens` for ER-2; stage 2 inherits it) | filled (rev 9) |
| Retry budget | stage 1: gpt-4o `max_attempts: 4` (amendments A6; terminal refusal 26.9% vs 57.1% at 2, p = 0.031), re-ask on, `image_fallback_after_attempts: 2` (same prompt text with a neutral grey image after two refused attempts); ER-2 `max_attempts: 2`, re-ask on, no image fallback; `timeout_sec: 120` per call for both. Stage 2: `stage2_max_attempts: 2` × `stage2_timeout_sec: 8.0`, no grey fallback | filled (rev 9) |
| Prompt templates | stage-1 template v2 (`prompt_version: 2`), stage-2 template v3 (`stage2_prompt_version: 3`); content hashes per condition | hashes **REQUIRED — recorded at tag time** |

**Model id** (coordinator resolution 2026-09-29, reviewable at the
tag): both. The dated snapshot `gpt-4o-2024-08-06` is pinned in
`config/models.yaml` at tag time, so an alias re-point cannot change the
model mid-collection. And the served
model string is recorded per call from the API response into
`reasoner_config_effective.served_model` (also `diagnostics.served_model`;
`37a0dd5`), so any mismatch is visible from the artifact alone. The field
is `null` where a backend reports no model string. Scope: stage-1 calls
only — the stage-2 `RetreatChooser` record does not yet carry it. ER-2's
unversioned preview id is recorded as-is with the probe date.

Rules: data collection may not start until every REQUIRED row is frozen
at `prereg-v1`. The **secondary model runs the headline cells only**
(one T1 scenario + T3a + T3b, dual channel) so that a "no" is not
attributable to a single model, and a "yes" gets a robustness check.
Mid-experiment model deprecation ⇒ freeze a `prereg-v2` with the
replacement and re-run affected cells.

**Rev 9 model characteristics and reporting rules (amendments A6).**

- **gpt-4o safety refusals** are a documented model characteristic,
  stimulus-locked: the trigger is the **camera frame's content**, not the
  text and not the annotation overlay (22/60 real vs 0/120 grey frames,
  p = 1.5e-12, findings Rev 6 §S; raw frames refuse at least as often as
  annotated ones on the skew-gated pairs, Rev 13 §AN); attempt-1 rate
  14–25% on real head-on frames. Funded battery 1 found 0 refusals in 41
  calls, 38 of which were T3a/T3c scenes with the robots metres apart —
  consistent with the trigger being the close-robot head-on frame, which
  the findings digest reads as sharpening the trigger from "camera
  frames" to "the head-on frame" (findings Rev 17 §AU). Annotation masking and
  downscaling are ruled out as mitigations; grey substitution is the only
  image-side lever. **Refusal rates per cell are mandatory reporting**;
  refusals consume analysis slots and are costed as such.
- **Image fallback:** validated (Arm X: terminal refusals 10/84 → 0/84,
  p = 1.5e-3) and kept; `image_fallback_after_attempts` is recorded in
  `reasoner_config_effective` (`5386bd3`). Decisions with
  `image_fallback_used: true` are **reported separately from every pooled
  rate** (yielder agreement under the fallback rests on n = 1, and the
  grey stimulus is the cell that moves yielder choice on standoffs).
- **ER-2** (zero refusals in 300+ live and replay calls, preferred where a
  lost analysis slot is costly) carries two structural confounds with
  every number: no sampling controls (`unsupported_sampling` per call),
  and thinking that is billed but never emitted, so its reasoning is not
  inspectable. Documented characteristics, not fixed: an opening
  `reverse` on asymmetric scenes (trigger-confounded — opening-strategy
  analyses condition on trigger type) and an unanchored, near-chance
  yielder choice (no `robot_1`/first-slot prior). ER-2's first decision
  is not comparable to gpt-4o's first decision (amendments A4).

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
- **Stage-1 prompt v2 (rev 9, amendments items 10, 13, 15;
  `991ffae`…`ed152c7`, `b4a8d91`):** the output schema gains optional
  `blocker_kind` (`object`/`transient`/`robot`, absent = valid) and
  `crossing_order` (non-permutations degrade as `non_permutation_order`);
  the state block carries each robot's **registry goal and task label**
  (before v2 every prompt sent `goal=None`, while Arm B's rules read
  goals — the goals-parity gap is closed by giving the VLM goals);
  the header no longer claims "sorted by ID" under a non-ascending draw;
  the guidance line reads "Decide from the robot states (including their
  stated goals and tasks) and the image; do not assume intentions beyond
  what is stated." (item 15(a), coordinator decision, user veto open
  until the tag); the leakage-guard exemption for the literal schema
  token `"blocker_kind"` is confirmed (item 15(c)). Templates are
  versioned (`prompt_version`): v1 stays in the tree and every stored
  artifact reconstructs byte-identically (130/130 integrity, 654/654
  sweep). Nothing straddling the v1/v2 break is poolable. The goals
  rider was implemented on the coordinator's recommended default;
  explicit user confirmation is recorded as pending in amendments
  item 13.
- **Stage 2 as built (rev 9, amendments items 21–22, 26; `e358229`,
  `1648dd2`, `49416c7`…`3366502`, `526d957`):** derived grounding and
  stage-2 retreat selection are wired into M5 and the grounding mode is
  flipped to `derived` (one-commit revertible). Set-of-mark letters are
  drawn via `swarm_perception.geometry.world_to_pixel` with a
  never-fatal fallback chain (`marks_drawn` recorded). **Deviation from
  A.1/A.3:** letters are drawn on the stage-1 *annotated* frame
  (`<request_id>_stage2.png`), not on a fresh frame. The marker-plane
  homography puts rings ≈29 px off at floor level (versus the 34 px
  ring), so a frame-level footprint check is part of authoring any
  stage-2 tier. **Letter counterbalancing:** the letter↔M3-label mapping
  is seeded per draw and recorded with its seed in every stage-2
  artifact; the letter the VLM sees is never M3's label. **Listing
  randomization (stage-2 prompt v3, item 26):** candidates are listed in
  a seeded order independent of the letters, decoupling letter, listing
  slot and geometry rank three ways (the calibration pilot showed a
  letter-A prior 6/6 across both models, p = 1/64; v2 listed in letter
  order). v2 is preserved for byte-reproduction. Budget 2 attempts ×
  8 s; **no grey-image fallback in stage 2**, so gpt-4o stage-2
  refusals surface as recorded defaults. `classical_retreat` (Arm B's
  stage-2 answer) is in the shadow block. Stage-2 justification text
  hallucinates obstacles on featureless scenes and is not evidence.
  Scorer taxonomy and pooling rules: measurement plan.
- **Annotation legibility (from the noise review):** identity = color,
  status = box style; boxes shrunk toward true footprint; labeled goals
  (G1/G2); candidate letters in a reserved color; leader-line labels in
  clusters; stage-2 frames drop arrows/goal markers; the prompt explains
  the annotation scheme in one sentence. *(Rev 9: as built, the stage-2
  frame is the stage-1 annotated frame plus letters — "Stage 2 as built"
  above — so it does not drop the stage-1 overlays; a recorded
  deviation, amendments items 21–22.)*
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
| Image/state cross-check block (`ReasonerRequest.include_visual_crosscheck`, 2026-09-18) | — | — | — |
| Motion table | ✓ | ✓ | — |
| Failure-context block (re-analysis) | ✓ | ✓ | — |
| Annotation-scheme sentence | ✓ | — | ✓ |
| Stage-2 set-of-mark frame | ✓ | — (stage 2 skipped → geometry-max, logged `stage2=condition_constrained`, not a degradation; identical to Arm B stage 2 by definition) | ✓ |

The cross-check row is `—` in every column on purpose: it is an **off-by-default
diagnostic ablation, not a pre-registered condition**, and no registered cell
sends it. It exists because the registered prompt's "do not re-derive distances
or facing from the coordinates" clause (Fix B) makes Arm A's decision
text-driven: with the block off, `gemini` and `openai` each followed the text
state block in 100% of incongruent image/state trials, and with it on
`gemini` inverted to 10/10 image-consistent
(`docs/reports/2026-09-18-gemini-er2-image-grounding.md`). **Prereg
implication:** every reported Arm A decision must state which prompt variant
produced it, and a "correct" Arm A decision under the registered (off) variant
is evidence about arithmetic on M1's state block rather than about visual
scene understanding — for the `openai` primary cell as much as for `gemini`.
Turning the block on would change what Arm A is, so it stays out of the
registered design until the type/strategy drift that report documents is
resolved.

*Rev 9:* under prompt v2 the robot state table row includes each
robot's registry goal and task label; the failure-context row carries up
to two blocks (amendments A9; Appendix A.1). The per-tier values of the
two switchable rows are pinned in the table below.

**Per-tier channel table** (coordinator resolution 2026-09-29,
reviewable at the tag):

| Tier | `prompt_static_obstacles` | `prompt_pairwise_geometry` | Basis |
|---|---|---|---|
| T0 (`normal_flow`) | not set by the resolution (residual) | true | geometry: rev 8.4 everywhere; no static obstacle is declared, so on and off render the same prompt |
| T1 | on | true | adopted collection default since findings Rev 2 §D item 1 (reaffirmed Rev 4 §N item 1) |
| T2a (`_bshort`) | on | true | as T1; every `_bshort` pilot ran it on |
| T2b (`t2b_flow_ordering`) | on | true | as T1; its `static_obstacles` is empty, so on renders no block |
| T3a, T3b, T3c | off | true | blockers are untracked by construction and must appear in no text channel (their YAML headers already require it) |
| B1 (`bottleneck_merge`, rev 9.5) | off | true | the YAML header states this explicitly (amendments item 28): the aperture must appear in no text channel so the `bottleneck` type call rests on the image (modality cell, above) |
| B2 (`priority_urgent_r1`/`_r2`, rev 9.5) | **off** | true | the YAML header states `off` explicitly, despite B2 being hand-authored from the T1 `wopen_eopen` geometry whose own row above is `on` — **flagged inconsistency, not yet reconciled:** functionally inert either way (B2 declares no `static_obstacles`, so on and off render the same prompt, as for T0), but the collection-value convention differs from its T1 base without a recorded reason; `[REV95-OPEN]` |
| B3 (`convoy_counterflow`, rev 9.5) | **off** | true | as T2b (empty `static_obstacles`), but the YAML header states `off` explicitly rather than following T2b's `on` convention — the same kind of unreconciled convention mismatch as B2's row above; also functionally inert (empty list); `[REV95-OPEN]` |

The repo default for `prompt_static_obstacles` is `false`; the collection
value is asserted per run through the installed orchestrator YAML (A8).
With the channel on, an empty `static_obstacles` list renders no block, so
both the system and user prompts are byte-identical to off (checked by
SHA-256 for prompt v1 and v2). Of the battery's scenario YAMLs only T2a's
`_bshort` variants declare a static box (T2b's list is empty; T0 and T1
declare none), so "on" is load-bearing for T2a alone. There the installed
`static_obstacles` must carry the variant's blocker — an operator step
covered by the A8 content assertion — because with the list commented out
the launcher reports the channel on while nothing renders (findings Rev 2
apparatus notes).

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
   design introduces **no new enum entries**. **Rev 9.5 (amendments items
   28–29, `cb44d7a`):** `convoy` and `priority_override` — previously
   always `strategy=unsupported`, degrading to a bounded `temporary_wait`
   — now ground as the ordered yield by the unique involved robot whose
   goal bearing opposes the majority, tagged `strategy=aliased:*`. Aliased
   decisions **execute**, they do not degrade; no decision pools across
   this commit (measurement-plan pooling rule (e)).

### Containment (the laboratory's safety glass — unchanged)

VLM outputs restricted to system-generated discrete options; geometric
revalidation at grounding (swept segments, permutations, feasibility);
verified-or-degrade everywhere; all degradations logged `*=default` and
counted in the metrics. A wrong VLM answer produces a logged
degradation, never unsafe motion — which is precisely what makes Arm A
safe to run.

*Rev 9 — M4 safety state and its limits (amendments A5, items 17, 25).*
The claim above holds for the grounding layer; M4's execution layer has
had three instances of one family of gaps, recorded here so the claim is
read correctly:

- **Coordination exemption (closed, `45e55f4`):** the G4 and K1 events
  were ≈51 s each of driven nose-to-nose contact at 0.076 m, caused by
  M4's exemption disarming the 0.45 m rule and the STALE fail-safe for
  any pair with an ACTIVE command (an ER-2 `reroute` put both robots
  ACTIVE). Now only `yield` and `reverse` exempt a pair, the per-robot
  action comes from `/coordination/commands`, and unseen commands fail
  closed; verified on the VM (the mock-forced exposure latches at
  0.381 m with no contact). Arm B's `reroute` for `blocked_path` had the
  identical exposure, so the fix gated both arms. Tracked non-blocking
  residuals: the latch-first (K1) ordering is unit-covered but not
  host-reproducible, and a Nav2 leg going ACTIVE after a latch holds its
  goal until the 120 s watchdog.
- **Pair scope and ordered release (landed for T2b, `9c38042`…
  `b0ff818`):** the exemption is pair-scoped with fail-closed semantics
  and a bystander guarantee (a yielder is no longer unguarded against a
  third robot), the release is ordered hold-until-last
  (`crossing_chain.py`), and a first-passer guard refuses mis-ordered
  yields that would reverse the yielder onto a queued robot; two-robot
  behavior is pinned byte-identical. The bystander latch is verified live
  (0.43 m, zero contacts, both seeds).
- **Raw-`cmd_vel` obstacle blindness (standing note, item 25):** maneuver
  legs (backup, sidestep; the escort is raw `cmd_vel` too, Appendix A.7)
  bypass Nav2 and the collision monitor entirely, so they are blind to
  untracked obstacles. In T3b this is the *intended* outcome mechanism
  (an occupied-default trial drives the yielder into the box in sim);
  outside T3b it is an M4 hardening item for any post-prereg roadmap,
  reproduced on a rack in funded battery 1.

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

### Rev 9 outcome, safety, and provenance rules (amendments A4, A5, A8)

- **Primary per-episode outcome (A4):** every involved robot's arrival
  **accepted by the arrival position check** (`arrival_position_check:
  true`, tolerance 0.35 m, M1 cross-check; `4f39899`–`069e1f2`),
  re-scored offline from the scene log by matching the acceptance lines
  (`scripts/rescore_arrivals.py`), with the `box_overlap` flag on `_bshort`
  (A1). "Resolution success" above means this outcome; Nav2 goal success
  is not arrival (E1's false success sat 0.59 m from goal). Secondary:
  the **first answer** — the pre-gate strategy and yielder of the
  episode's first analysis. Resolution time (first analysis → last robot
  arrived) is descriptive. First answer and outcome are reported
  separately because they disagree on the same mechanism. At N = 3 the
  rescorer's `run_both_arrived_*` columns mean "all arrived".
- **Arrival definition, pinned at rev 9 (T2b finding F6, amendments item
  17):** an arrival counts **only when accepted by the position check** —
  the robot within the 0.35 m tolerance of its goal, cross-checked
  against M1 — never on Nav2 goal success alone. **A robot latched at its
  goal** (held by an M4 safety latch while within that tolerance, so Nav2
  never reports success and M5 never emits an acceptance line) **counts as
  arrived for the outcome, flagged `latched_at_goal`**, and flagged
  arrivals are reported per cell. This is the definition the forced-order
  harness's ground-truth scorer already applies — it credited the
  alternative arm's latched `robot_2`, 0.09 m from its goal, at 57.5 s —
  so the frozen T2b margin was computed under it. Tooling consequence:
  `rescore_arrivals.py` currently emits rows only for M5-reported
  arrivals, so it needs a latched-at-goal path before collection.
- **Sim-time measurement notes (A4, findings Rev 14 §AQ):** scene logs
  carry sim-time stamps since merge `97634be` (root cause: Isaac's
  `useSystemTime` on the camera helpers, flipped at `a1aa81d`);
  `rescore_arrivals.py` must use its era-aware path (a pre-fix script
  silently scores every post-fix arrival `stale_estimate`). Offline joins
  of M1 to ground truth shift by **−0.45 s** (constant M1 stamp lag).
  M5's stall and cooldown thresholds still run on wall time (12 wall-s
  ≈ 4.6 sim-s at RTF 0.38).
- **Pooling rules.** Never pool, without stating the basis change: (a)
  runs before and after the sim-time-stamp fix on any speed- or
  status-derived measure (M1 speeds ≈2.6× larger post-fix; parked
  STOPPED/SLOW flicker ≈4× more transitions); (b) decisions before and
  after the **grounding-mode flip** to derived (`1648dd2`) —
  `degradations`, `retreat_*`/`linked_position` keys and out-of-band
  yield behavior differ — which also keeps T2b (legacy) apart from the
  derived tiers; (c) anything straddling the stage-1 v1/v2 prompt break;
  (d) stage-2 records across the v2/v3 break; (e) rev 9.5: no decision
  carrying `strategy=aliased:convoy` or `strategy=aliased:priority_override`
  pools across the aliasing commit (`cb44d7a`) — before it those strategies
  degraded to a bounded `temporary_wait` (`strategy=unsupported`); after it
  they execute.
- **Passer backtrack** (coordinator resolution 2026-09-29, reviewable at
  the tag): **peak-|x| minus the minimum |x| after the peak** — the
  definition the K, N and S batches used; it is direction-free and the
  stricter of the two. The
  first-turnaround variant is rejected (the two disagree on `_gshort` H2,
  0.878 m vs 0.580 m; findings Rev 10 §AI).
- **Safety columns (A5):** per run, the minimum pairwise centre-to-centre
  distance and the percentage of ground-truth rows below `safety.yaml`
  `min_distance_m` (0.45 m). Ground-truth contact flags
  (`robot_robot_contacts`, `robot_static_contacts`) are **disqualified as
  evidence** — no detector exists and they stayed silent through a
  sustained 0.076 m wedge. 5–7% of rows below 0.45 m is the
  design-expected signature of a completed head-on yield; sustained
  breaches near contact depth (G4-class) are incidents, reported
  individually. Ground truth records robots only, not obstacles.
- **Stage-2 scoring taxonomy (amendments items 22, 26):** every stage-2
  choice is scored three ways — chose the **first-listed** candidate,
  chose the **default** (`choice == default_letter`, never a comparison
  against M3's `retreat_choice`), chose **letter A**. Trust
  `listing_order` only when `stage2_prompt_version == 3` (a v2-stamped
  record with a listing means a stale deploy).
- **Mandatory per-cell counts:** drawn presentation orders (A2),
  refusal rates and `image_fallback_used` decisions (A6, the latter
  reported separately), the T3b yielder-discard rate (item 23), and the
  T3b stage-2 degraded rate (refusals, timeouts and defaults excluded from
  the choice test; > 30% makes the cell inconclusive — rev 9.1).
- **Run provenance (A8):** every collected run carries the VM tree
  verified by md5 against the named commit; the installed orchestrator
  YAML asserted by content before launch; `reasoner_config_effective` in
  every decision artifact (`b518ed4`); `keep_debug_frames: true` and
  `keep_raw_frames: true` (raw/annotated pairs are not same-instant —
  |skew| mean 0.40 s — so annotation comparisons gate on the ≤ 0.2 s
  subset); and `ground_truth.jsonl` rescued into the run directory before
  the next launch.

### Rev 9.5 coverage-battery metrics (amendments items 28–30)

- **STRATEGY-REGRET (amendments item 29, `scripts/strategy_regret.py`,
  `78fca50`).** Forced-strategy mock sweeps produce a per-scene cost table
  keyed by **executed roles** (`roles_from_command`, not the decided
  strategy label): each arm reports its mean total time-to-goal
  (`mean_total_sec`, n seeds/arm), whether it is `censored` (did not
  complete within the episode horizon), and its `regret_sec` — the
  difference from the lowest-mean **uncensored** arm, which is the
  reference. **Censored arms are never the reference** (mirroring the T2b
  margin rule). The model's decided strategy is scored two ways: label
  correctness (per-tier criteria above) and time regret against the best
  *executable* strategy in the table.
  - **B2 — frozen, uncensored, likely noise at this n.** The harness's
    arms are named by who is *forced* to yield: `yield_routine` forces
    the routine robot (the `priority_override` route's executed arm,
    matching `PriorityOracleConfig.correct_yielder`); `yield_urgent`
    forces the urgent robot instead (the anti-priority arm,
    `scripts/strategy_regret.py`'s `_b2`). `priority_urgent_r1`:
    `yield_urgent` (`robot_1`, urgent, yields) 188.85 s (cost-minimizing,
    reference, regret 0), `yield_routine` (`robot_2` yields, matching the
    oracle) 201.95 s (**regret +13.1 s**). `priority_urgent_r2`:
    `yield_urgent` (`robot_2`, urgent, yields) 190.7 s (reference),
    `yield_routine` (`robot_1` yields, matching the oracle) 195.8 s
    (**regret +5.1 s**). Both n = 2 seeds/arm, `bscene_smoke`,
    2026-09-29/30. **Caveat:** the two members are the same physical
    scene (labels and the M3-only `priority` are the only difference), so
    the same maneuver is comparable across members — "`robot_1` yields"
    costs 188.85 s in `_r1` vs. 195.8 s in `_r2` (6.95 s spread);
    "`robot_2` yields" costs 201.95 s in `_r1` vs. 190.7 s in `_r2`
    (11.25 s spread). Those spreads are the same size as the regrets
    above and the cheaper yielder flips between members, so "the urgent
    robot yielding is cheaper in both members" is not distinguishable
    from noise at n = 2. **[REV95-OPEN]:** whether B2's STRATEGY-REGRET is
    interpretable at this n, and which arm should be the reference (the
    cost-minimizing arm above, or the `urgent_first`-correct arm) if it
    is.
  - **B1 — frozen with a censoring caveat.**
    `data/logs/vm_runs/b1_fix/COST_TABLE_bottleneck_merge.json` (`5dbb3a5`
    validation, n = 2 seeds/arm): `oracle` (yield robot_2) mean 424.1 s,
    `alternative` (yield robot_1, degrades to a robot_1 reroute) mean
    556.35 s, `wait` mean 558.0 s — **all three arms report
    `censored: true`**, including `oracle`, the reference. Recorded
    regrets: alternative **+132.25 s**, wait **+133.9 s**, both flagged
    `regret_is_lower_bound: true` by the harness. **[REV95-OPEN]:** with
    the reference arm itself GT-censored (by apparatus defect (a) above —
    the DEFAULT retreat candidate's backup fails its own safety check), the
    recorded regrets are a difference of two lower bounds, which has no
    proven bound direction; the harness's own `regret_is_lower_bound: true`
    label does not resolve this. This table freezes as a record of what
    the sweep measured, not as a validated regret bound, until apparatus
    defect (a) is characterized/fixed or a clean re-sweep is run. One
    observation, not a finding: the `alternative` (robot_1-yield/reroute)
    and `wait` arms **roughly** correspond to Arm B's two possible executed
    answers on this scene (blocked_path→reroute or unknown→wait — the
    sweep's `wait` arm holds all three robots, where Arm B's `unknown`
    holds only the two non-held robots, so the correspondence is not
    exact), and both sweep arms are censored — consistent with, though not
    proof of, the scenario battery's prediction that Arm B's B1 outcome is
    censored
    either way.
  - **B3 — no table.** The four-robot forced-order harness extension and
    the strategy-regret sweep were not run; the YAML's `correct_order` has
    no `margin` (`margin: pending`). **[REV95-OPEN]**, gated on apparatus
    defect (b).
  - **Freeze mechanics.** The cost-table JSON files above sit under
    `data/logs/vm_runs/`, which `.gitignore` excludes (`data/logs/*`,
    confirmed by `git check-ignore`) — unlike T2b's margin, written into a
    tracked YAML at `7400482`. Until an equivalent tracked home exists,
    the values recorded in this section are the frozen record (freeze
    list, above).
- **B1 gate-flow metrics** (`scripts/coverage_scene_scores.py`, `34d6b53`):
  gate flow rate (exits at x = 1.7 per 100 sim-s from
  first entry at x = 0.7), per-robot stop time (GT speed < 0.02 m/s over
  spells ≥ 1 s), makespan (first departure → last position-verified
  arrival); registered per battery entry, above.
- **B2 %CP** (`scripts/coverage_scene_scores.py`, `34d6b53`): the urgent
  robot's first GT crossing of x = 0 toward its goal, tested against
  chance 0.5; registered per battery entry, above.
- **B3 `censored_omitted_queue`** (`scripts/rescore_arrivals.py`,
  `4393155`): flags a rescored arrival where a queued robot outside the
  executed command has closed to < 0.45 m of a parked yielder — the T2b
  bystander-latch mechanism (battery entry, above).
- **B1 scoring exposure to apparatus defect (a) — coordinator proposal,
  not a recorded ruling.** The defect belongs to the **DEFAULT retreat
  candidate** (`selection.candidates[0]`), not narrowly to
  `retreat=default:no_choice`: any B1 trial that **executes that
  candidate** is exposed, whether it got there via
  `retreat=default:no_choice` (stage 2 `condition_constrained` off —
  always true for the B1 text-only modality cell — or a `k = 1` candidate
  set, 2 of the design's 4 stage-2 grid poses, or an unanswered stage-2
  call) **or** via an answered stage-2 call whose `retreat_choice` names
  the default letter (`choice == default_letter`). Only the
  `no_choice`-default path has been observed failing, 3/3
  (`min_distance_violation`); the answered-default path executes the
  identical candidate but has **not** been separately run, so its failure
  rate is unverified, not confirmed either way. **Proposed treatment:**
  a trial matching either key remains **decision-scored** (the
  type/strategy/yielder call still counts toward the type-label rate and
  the pre-gate agreement test) but is **excluded from the flow metrics**
  (gate flow rate, per-robot stop time, makespan), which the M4 defect
  confounds independently of the reasoning being scored. Keying only on
  `retreat=default:no_choice` would exclude some default executions
  (unanswered/condition-constrained) but not others (answered-default),
  biasing the flow metrics against whichever models more often *choose*
  the default letter on request. **This is this absorption's proposal,
  not amendments text:** Rev 20 orders "characterize + fix or scope," and
  does not itself state a scoring rule. **[REV95-OPEN]** pending the
  parallel apparatus-defect track's verdict; if the fix lands and clears
  the exposure, this note is superseded rather than rewritten.

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

**Rev 9.5 scoping sentences (amendments item 28; coverage check,
`reports/Congestion scenario coverage check.md`), registered verbatim
where quoted:**

- **Throughput.** *"No episodic ≤4-robot battery can measure the
  throughput-defined congestion regimes that dominate warehouse
  literature; the study's construct is conflict-resolution quality at
  constrictions, for which the mini-games metric set (success/deadlock
  rate, time-to-goal, stop time, flow rate, %CP) is the established
  instrument."*
- **Crowding.** Stays in the classification enum as a documented
  distractor label with no elicitor, following the ≥ 5-agent CrowdNav
  circle-crossing convention and its dependence on the throughput regime
  above; at the study's 4-robot cap an open-area crowding scene would be
  geometrically indistinguishable from the intersection scene.
- **Blind/L-corner and roundabout.** Blind corner and L-corner are
  excluded architecturally: the overhead camera removes occlusion and
  limited observability by design, which is a principled exclusion, not a
  gap. Roundabout/circular traffic has no counterpart geometry on the
  plus-shaped free floor of a rack warehouse.
- **Livelock and queue spillback.** Left unanchored, not added as named
  phenomena: no 2024–2026 AMR paper scores either separately from
  deadlock, so they would be unanchored labels with no scoring precedent.

These four are the ones this absorption registers; the unified scene
design's §5 "Scoping sentences to register" lists two more — novelty
claims with no external baseline (`convoy` as a commanded, scored
strategy; priority override from a text urgency channel) and the
fidelity/latency scoping (the sim is 2.6–4.1× slow for its size, 11–20×
more forgiving of reasoner latency than the MiR250 reference) — left out
of this section because this absorption registers only the four above;
they are not contradicted, only not yet registered here.
The battery **represents** the canonical episodic classes reachable under
its constraints; it does not claim to be exhaustive (coverage check,
same paragraph).

---

## Prereg-v2 registry (rev 9.5, amendments item 30)

Candidates the amendments set explicitly registers for a `prereg-v2`
freeze, distinct from the **Out of scope** exclusions above (which this
document does not intend to measure at all): these already have design or
literature work behind them and are deferred only by build cost or
by needing machinery this freeze does not build.

- **(a) Composite recede-then-yield command.** A single, cost-ranked
  default yielder — A-DRIVE's χ = s·D_SPACE + t·N_f (distance to a free
  evacuation pocket plus followers stacked behind it) — recedes along its
  own arrival arm; a two-robot recede, where genuinely required, is a
  staggered sequential fallback, never simultaneous (A-DRIVE rejects
  simultaneous multi-vehicle backing as "difficult and time- and
  fuel-consuming"). The remaining robots then cross in a per-episode
  priority order, inside-first, with the yielder re-entering last.
  Grounded in the literature review at `reports/Four way intersection
  robot congestion.md` (A-DRIVE, [arXiv:2204.04910](https://arxiv.org/pdf/2204.04910))
  and `reports/Congestion scenario coverage check.md`. No published system
  performs centralized commanded recovery from a formed multi-robot scrum
  — both reports record this as a citation gap and a defensible novelty
  claim, not a coverage requirement.
- **(b) The loop map.** A second E–W aisle creating cycles, so `reroute`
  becomes a genuine alternative rather than a no-op re-send; enables
  wait-vs-detour trade-off scenes that require a **visual
  blocker-persistence judgment** (amendments item 30(b)).
- **(c) The B2-visual urgency pair.** A loaded-vs-empty robot via the
  existing prop machinery, replacing B2's text-label urgency channel with
  a visual one (amendments item 30(c)).
- **(d) The resolution-scored four-way intersection.** Folds in the
  T1/T1-X tier's rev-9.3 note (multi-axis M3 grounding is a prereg-v2
  candidate) and the intersection-resolvability design study's verdict
  (`docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`,
  recommendation D: the T1-X log-only fallback stands, because a formed
  four-way jam's first-passer transit is ≤ 0.351 m against the 0.45 m
  floor under every scheme tried, and the schemes that do complete
  degenerate to two sequential head-ons, losing the tier's identity). The
  genuine four-way needs exactly the (a) composite command above — the
  same two reports are the grounding for both.

**Not registered here** (coverage-check and unified-scene-design
candidates without a Rev 17 registry item; reported, not silently
dropped): the robot-blocker anomaly (a faulted, stationary tracked robot
narrowing an aisle), the token-scale crowding scene at the plus-junction,
and the three-active-robot B2 variant at the junction (structurally
impossible under v1 primitives — unified scene design, B2 section).

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
  blocks, T0 normal-flow scenario, obstacle assets, USD rebuilds) —
  *rev 9: built*, file names in the scenario battery section; oracle
  schemas in `isaac/vgu_sim/config.py`; T2b forced-order harness
  `scripts/t2b_forced_order.py`; arrival re-scoring
  `scripts/rescore_arrivals.py`
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
  only output is `retreat_choice` + one-clause justification. *Rev 9
  (amendments items 21–22): as built, the markers are drawn on the
  stage-1 annotated frame, not a fresh frame — a recorded deviation; see
  "Stage 2 as built" in the Decision flow.*
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
  Depth (rev 9, amendments A9, `7f9884d`): re-analysis prompts carry the
  most recent resolved attempt (the "Previous attempt in this episode:"
  block, unchanged) and, when that attempt is not itself the failure,
  the most recent failed attempt as a second "Earlier failed attempt in
  this episode:" block (`ReasonerRequest.last_failed_context`). "Failed"
  is any resolved outcome other than completed, `timed_out` included.
  The failed block lives under `AttemptMemory`'s overlap-plus-window
  scope — it must overlap the analysed robots and is dropped with the
  window (60 s default) or on a disjoint robot set; a failure older than
  the window is gone (a documented boundary, not a defect); a newer
  failure replaces an older one; a completed attempt never displaces the
  stored failure. Prompts without the second block are byte-identical to
  the pre-policy rendering (SHA-pinned; replay 130/130). Both blocks are
  persisted structurally in decision artifacts for RQ5. Motivation: the
  one-deep context let a completed `temporary_wait` evict a failed yield,
  and M2 re-selected the same infeasible yielder (R2 `7482f0ad`, L4
  `ca63fbd5`). The "Scope: … current episode's prior attempt(s) only"
  rule above is unchanged; the episode is defined in the arms section
  (amendments A7).

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
  annotation pass draws lettered markers (Ⓐ/Ⓑ/Ⓒ). *Rev 9 (amendments
  items 21–22, 26): as built, letters are drawn onto the stage-1
  annotated frame via `swarm_perception.geometry.world_to_pixel`; the
  letter↔candidate mapping is seeded per draw (so the letter shown is
  never M3's label) and, from stage-2 prompt v3, the listing order is
  seeded independently of the letters.*
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
  verified head-on flow plus rejoin. *Rev 9 (amendments item 17):* the
  hold-until-last ordered release is implemented
  (`crossing_chain.py`, `9c38042`…`b0ff818`) together with the
  pair-scoped exemption and a first-passer guard that refuses
  mis-ordered yields; M3 fans a multi-passer yield out with per-passer
  clearances. The first-passer guard exists in legacy grounding only,
  one reason T2b is pre-registered on legacy grounding. Verified live in
  the three-robot smoke (notes 2026-09-29).
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
  Prompt: classify what is blocking, from visible evidence. *Rev 9
  (amendments item 15(b), confirmed):* `robot` means a **listed** robot
  (one in the prompt's robot state table), so T3a's deliberately unlisted
  robot-shaped blocker labels `transient` — the tier's oracle depends on
  this definition. The field is
  in the contract and the prompt from stage-1 prompt v2.
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
- **Rev 9 pointer (this audit is dated 2026-09-16 and is not rewritten).**
  Changes since it that alter the "scripted" bullet: the yielder is no
  longer read from list position — the decision's `yield_robot` (rev
  8.6) passes the M3 `swap` feasibility gate (arms section); M3 runs
  **derived** grounding with stage-2 retreat selection by default
  (`1648dd2`), legacy only on T2b; the M4 exemption is scoped to
  `yield`/`reverse` pairs and pair-scoped, with ordered hold-until-last
  release (Containment, rev 9 notes); M1 and scene-log stamps are
  sim-time since `97634be`; and localization and odometry remain
  simulator ground truth as stated above.
