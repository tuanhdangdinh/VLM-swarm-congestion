# Pre-Registration v1 Amendments — Pilot-Campaign Bindings

**Prepared:** 2026-09-26

**Revision history:**

- Initial draft: binds the decisions adjudicated by the 2026-09-24/26 pilot
  campaign (`docs/reports/2026-09-25-overnight-findings.md`, Rev 1–9) into the
  `prereg-v1` freeze of the research design
  (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`,
  rev 8.6), and lists the items still blocking that freeze.
- Rev 2 (2026-09-26): the `_bshort` validation batch (findings Rev 10 §AI)
  satisfies A1's condition — east 3/3, west 3/3 at ±2.6, all
  position-verified — discharging freeze blocker 2; A5 gains K1 as a second
  G4-class interpenetration instance.
- Rev 3 (2026-09-26): A5 rewritten from the root-cause analysis (findings
  Rev 11 §AK): the events were driven contact under M4's coordination
  exemption, the fix direction is adopted but unimplemented, and Arm B
  inherits the same `reroute` exposure, so blocker 6 gates both arms.
- Rev 4 (2026-09-26): A5 closed — the exemption fix landed (`45e55f4`) and
  passed both VM regressions (findings Rev 12 §AM). Blocker 1 discharged at
  the reasoning-core level by the Arm B merge (`65cc850`); its Phase-2
  wiring, the missing contract fields, and the M1 speed-scaling fix become
  tracked items 10–12.
- Rev 5 (2026-09-27): blockers 4 and 5 discharged (findings Rev 13
  §AN–§AO) — Arm X validates the image fallback (kept, separate reporting
  stands), Arm F shows the refusal trigger is the camera frame's content
  rather than the annotation, and the gpt-4o `_bshort` pilot lands 6/6 on
  the adopted apparatus, completing the baseline on both models. A6's
  trigger wording corrected accordingly.
- Rev 6 (2026-09-27): new A9 — the failure-context depth policy is decided
  and implemented (`7f9884d`), discharging blocker 3;
  `image_fallback_after_attempts` now recorded in
  `reasoner_config_effective` (`5386bd3`), closing that A6 note; the
  `feat/failure-context-closed-loop` branch is confirmed fully contained
  in HEAD.
- Rev 21 (2026-09-30): absorbed into the research design as rev 9.5
  (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`),
  which is now the authoritative text; this document remains the historical
  decision record. Absorbed: items 28–30 and the Rev 17–20 records (the
  B1/B2/B3 coverage battery, the STRATEGY-REGRET metric and its first
  frozen B1/B2 instances, the per-class flow/%CP/censored-queue metrics,
  the coverage-check scoping sentences, the prereg-v2 registry, and the
  Arm B held-robot exclusion generalized beyond A10), and the questions
  it leaves unresolved are the `[REV95-OPEN]` markers there, listed in
  its Status line — among them the two apparatus defects Rev 20 opened
  (a, b), the B1 trial-counting denominator, and B2's STRATEGY-REGRET
  ranking, which this absorption found not distinguishable from noise at
  n = 2 seeds/arm.
- Rev 22 (2026-09-30): defect round verdicts (notes `414037b`) SUPERSEDE
  Rev 20's framing in part: (b) is NOT a dispatch bug — the
  dispatch/retry/registry code is correct (one clean 4/4 B3 replicate
  falsifies "never in any run"); the real cause is the B3 goal table
  (robot_1/robot_3 goals 0.6 m apart → the release-approach passes
  0.426–0.444 m from the parked robot and latches under the correct
  passer-passer non-exemption). **B3 goal-table revision ORDERED**
  (B1-style: widen the goal stack, pins updated, smoke-verified);
  outcome collection stays gated until it lands. (a) is NOT a
  nominal-pose sweep bug (refuted at file:line) — the Nav2 sidestep's
  odometry drift overshoots only the FAR (2×, −0.72 m) candidate past
  the aisle band (4/4 at the adapter's exact 202.25 s deadline; the 1×
  candidate completes in 39 s). **Adopted scoring rule (resolves
  REV95-OPEN #4): B1 trials whose EXECUTED retreat is the 2× lateral
  candidate are excluded from flow metrics, decision-scored** — keyed
  on the executed candidate, not the degradation tag; the ranking
  tie-break revision (prefer lesser excursion on tied clearance) is
  REGISTERED for v2/tuning, not applied (it would re-rank T3b's
  pre-registered occupied candidate). Also recorded: the ~5 cm
  held-robot crawl (cmd_vel_watchdog invariant breach, M4 §8) as a
  standing apparatus note. Coordinator resolutions of the remaining
  REV95-OPEN items: #1 B1 counts 15 scored EVENT episodes (no-event
  rate reported, cap 25); #2/#3 the B1 and B2 strategy-regret columns
  are DESCRIPTIVE-ONLY at current n (B2's "best_arm=yield_urgent" in
  Rev 19 is annotated: it is the anti-priority arm and the ranking is
  indistinguishable from noise at n = 2); #6 B1/B2 do NOT join the
  "VLM can" conjunction — coverage cells are secondary; #7 the channel
  table records B2 as ON-vacuous (no obstacles declared; ON == OFF
  byte-identical, SHA-verified) and B1/B3 OFF per their headers; #8
  the container baseline is 2980 passed / 23 failed / 12 skipped with
  the five documented pxr-file ignores (the launch_testing collection
  bug is diagnosed in the notes); #9 the rev 9.5 spec text is the
  cost tables' freeze point (B3's table appends when its revision
  lands).
- Rev 20 (2026-09-30): B1 geometry FIXED and validated (`5dbb3a5`:
  `half_length_m` 0.6→1.1 after both suggested levers were GPU-probed
  and rejected; feasibility pinned at all 8 MEASURED trigger poses,
  margin ≥ 0.167 m; the pre-fix grid's LEVEL_OR_PAST blind spot — 7/8
  real poses — is now a pinned regression class). B1 cost table:
  oracle regret-best by +132/+134 s over alternative/wait. Stage-2
  aperture live-check CLOSED (answered stage-2 prompt, 0 token hits).
  TWO NEW APPARATUS DEFECTS, fix ordered before B3 outcome collection:
  (a) B1's DEFAULT retreat candidate fails its own backup on
  min_distance_violation 3/3 (completes when stage-2 selects — so
  stage-2-degraded B1 trials contaminate outcomes; characterize + fix
  or scope); (b) a structural 4-robot dispatch gap — robot_4 never
  receives "Begin navigating"/M5 acceptance in any of 3 B3 runs
  despite reaching goal in GT, and robot_3's canceled Nav2 leg is
  never retried (the 0.36 m near-misses trace to retry logic, not the
  tolerance — no goal nudge). Residuals: M4 backup overshoots the
  NS band at 2/8 steep-heading poses (documented); suite baseline is
  environment-split (local 58/2921 vs container 63/2926) — container
  re-baseline before the tag.
- Rev 19 (2026-09-30): B-scene smoke batch complete with independent
  replication (an Opus rate-limit cutoff left a near-finished batch; the
  successor replicated before discovering it — both kept). **B2 full
  PASS twice over** (%CP 1.0 both members, divergent-and-correct 1.0,
  uncensored regret 13.1/5.1 s; tag-ready). **B3 mostly PASS** (alias
  executes as ordered yield; 4-stack gate 4/4-in-0s; geometry to
  design) with an arrival-variance watch item (replication 2/4 M5
  arrivals: one 0.36 m near-miss vs the 0.35 m tolerance, one missing
  arrival line at 0.10 m GT; predecessor 4/4). **B1 UNRESOLVABLE AS
  AUTHORED, 5/5 executions**: measured trigger poses leave 0.82–0.87 m
  escort vs the 1.0 m floor → yield grounds infeasible → reroute-all →
  permanent three-way latch, 0/3 arrivals (onset itself in-window).
  Geometry revision ORDERED before B1 enters the matrix. Also open:
  B1's stage-2 aperture-absence was unit-pinned but never live-checked
  (stage 2 always skipped). fc_launch gate landed at `ed75288`;
  inherited scorer commits verified (suite 2926).
- Rev 18 (2026-09-29): B1/B2/B3 BUILT (`2f5a2d1`…`ae11362`, 361 tests;
  suite 2885): held-robot exclusion (candidacy-only), arm-aware lateral
  band, M3-only `priority`, convoy/priority_override aliased onto the
  ordered yield (`strategy=aliased:*` tagged), the three scenes with
  C1–C13 grids, the strategy-regret harness (arms keyed by EXECUTED
  roles; censored arms never the reference), and the `fcfs_yielder`
  factual correction (blast radius: all 7 manifest rows now robot_2;
  `contrasts_fcfs` flipped on 7 rows — the FCFS-contrast set is
  reconstituted accordingly). Six design-doc claims corrected by
  measurement and pinned (B3 escorts 3.674/4.244 m; B1 heading gate
  0.174 at −62°; k=1 at 2 of 4 B1 stage-2 poses; etc.). Coordinator
  rulings, reviewable at the tag: (a) the held-robot exclusion is NOT
  extended to the head_on crowding check — Arm B answering `unknown`→
  wait on 10/45 crowded B3 grid cases is recorded as the baseline's own
  limitation (its B3 outcome is censored by construction regardless);
  (b) B1's refused robot_1 yield degrading to a reroute (no static
  obstacles → no swap re-grounding) stands — the regret metric prices
  the wrong decision. Still pending for the smoke batch: B1 gate-flow +
  B2 %CP + B3 censored-queue scorers, the fc_launch four-stack
  lifecycle gate, VM USDs and smokes.
- Rev 17 (2026-09-29): coverage-check decisions, USER-APPROVED ("Ok"):
  item 28 — build B1/B2/B3 per the unified scene design (`3b3a529`) under
  the CONSERVATIVE migration (existing scenes grandfathered, deviations
  D1–D3 recorded; zero re-validation): B1 with the aperture deliberately
  absent from every text channel and a registered image-only/text-only
  modality cell (the type call's image-dependence becomes a measured
  quantity); B2 as the 2-robot label-swapped pair (`priority` field read
  by M3 only, never rendered; no new prompt version); B3 first-to-slip
  to v2; plus the A10-mold Arm B rule change: a held robot
  (`start_pending`) is excluded from `blocked_path` candidacy (required
  by B1 and 10/45 B3 grid cases). Item 29 — STRATEGY-REGRET scoring
  registered: forced-strategy mock sweeps produce a per-scene strategy
  cost table, and the model's choice is scored as time regret against
  the best executable strategy, alongside label correctness. Item 30 —
  the prereg-v2 registry: (a) the composite recede-then-yield command
  (single cost-ranked yielder per the literature review), (b) the LOOP
  MAP (a second E-W aisle creating cycles, making `reroute` a genuine
  alternative and enabling wait-vs-detour trade-off scenes with visual
  blocker-persistence judgment), (c) the B2-VISUAL urgency pair (loaded
  vs empty robot via the prop machinery). Also ordered: the factual
  `fcfs_yielder` correction (full ties yield robot_2, not robot_1) in
  the family manifest, T2b YAML and spec annotations, with pin updates.
- Rev 16 (2026-09-29): item 27 — `intersection_bottleneck` audited and
  smoked pre-tag (light fixes `49ac434`; first live Arm B `intersection`
  classification, 35/35 correct): the four-way is structurally
  unresolvable by the single-yield primitive, so per USER DECISION C it
  leaves T1 (replaced by `head_on_asymmetric_wopen_eopen_o0`) and
  becomes the log-only T1-X classification cell (10 probes, RQ1);
  multi-axis M3 grounding is a prereg-v2 candidate (spec Rev 9.3).
- Rev 15 (2026-09-29): absorbed into the research design as rev 9
  (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`),
  which is now the authoritative text; this document remains the
  historical decision record, and the questions it left unresolved are
  the `[REV9-OPEN]` markers there.
- Rev 14 (2026-09-28): T3b is built and mock-smoked (`e205f5f`…`19fafa0`)
  — the set-of-mark path verified live (parallax PASS), the classical
  arm picks the occupied candidate by construction, and the
  occupied-default run shows the tier's real outcome contrast: M4's
  sidestep (raw `cmd_vel`, no Nav2/collision-monitor guard) drives the
  yielder into the box, pinning it 71 sim-s until the wall-clock bound
  fails the yield. New items 23–25: the T3b yielder-side restriction,
  the T3b criterion correction (chance of avoiding one occupied
  candidate among three is 2/3, not the spec's 1/3 — ≥9/15 is
  meaningless), and the standing M4 raw-`cmd_vel` obstacle-blindness
  note (third instance of the family: exemption pairs, T2b backup path,
  now maneuver legs vs obstacles).
- Rev 13 (2026-09-28): items 21–22 closed (`49416c7`…`3366502`) —
  set-of-mark letters drawn via `swarm_perception.geometry.world_to_pixel`
  with a never-fatal fallback chain (`marks_drawn` recorded), seeded
  letter counterbalancing (letter↔label mapping + seed in every stage-2
  artifact; "chose the default" is `choice == default_letter`, never a
  comparison against M3's `retreat_choice`), stage-2 budget 2 × 8 s, and
  `classical_retreat` in the shadow block. Tag-review notes: letters are
  drawn on the stage-1 *annotated* frame rather than a fresh frame
  (deviation from rev-8 A.1/A.3, recorded); the marker-plane homography
  parallax (~29 px at floor level vs the 34 px ring) obliges a
  frame-level footprint check during T3b authoring; stage 2 has no grey
  fallback, so openai stage-2 refusals will surface as recorded
  defaults.
- Rev 12 (2026-09-28): derived grounding + stage-2 retreat selection are
  wired into M5 and the mode is flipped (`e358229`, `1648dd2` — the flip
  is one-commit revertible); stage-2 prompt v1 pinned, full
  degradation-to-geometry-max chain, mock retreat-letter support. New
  measurement rule: post-flip decisions are not poolable with
  legacy-grounded ones (`degradations`, `retreat_*`/`linked_position`
  keys, out-of-band-yield behavior differ). New items 21–22: T3b is
  blocked on set-of-mark letter drawing (text-only letters cannot tie a
  letter to a seen obstacle) and on letter counterbalancing (ties order
  by letter, so the default and first-listed coincide — a first-slot
  confound); plus a stage-2 attempts/timeout key before the first funded
  run and Arm B's stage-2 answer in the shadow block.
- Rev 11 (2026-09-27): T3a is built and mock-smoked (both members PASS,
  real marker-less robot blocker; `ad379f1`…`71f6fdd`) and forces a
  run-matrix amendment — item 18: **T3a has no outcome contrast in this
  apparatus** (reroute merely re-sends the goal, which M4 already does;
  the object member is unresolvable and the transient member resolves
  under any strategy), so T3a is scored on the decision
  (divergent-and-correct rate, already its primary test) and the "B
  executed on 5 pairs for outcome contrast" cell is dropped at rev 9
  absorption. Items 19–20 record the 1.82× blocker-scale visual
  confound and the T3a apparatus deviations for tag-time review.
- Rev 10 (2026-09-27): the prompt-v2 bundle lands (`991ffae`…`ed152c7`) —
  items 10 and 13 discharged (`blocker_kind` + `crossing_order` on the
  contract and prompt; goals + task labels in the state block, goals on
  the coordinator's recommended default with explicit user confirmation
  still pending); prompt template versioning keeps every stored artifact
  reconstructing byte-identically (130/130 integrity + 654/654 wider
  sweep). New freeze-checklist items 15–17: three prompt-wording
  sign-offs, the calibration mini-pilot (funding-blocked), and the T2b
  scope decision from `docs/reports/2026-09-27-three-robot-feasibility.md`.
- Rev 9 (2026-09-27): new A10 — Arm B's `blocked_path` rule gains a
  parked-at-goal exclusion (`arrived_exclusion_radius_m: 0.35`,
  `5e13805`), a pre-freeze rule change forced by the T0 verification
  run's 60/60 rule-level false positives on parked robots; T0 is
  live-verified (ER-2 FP 0/28) and T3c is re-scoped to a v2 re-author
  (findings Rev 15 §AS).
- Rev 8 (2026-09-27): blocker 8 progress — T0 tier and the Pillar 2
  stage-2 retreat machinery are built (battery design spec committed at
  `d255a09`; T0 `33232b8`…`ff96ead`; Pillar 2 merged `d3c2a7d`), leaving
  the prompt-v2 bundle as the gate for T3a/T2b authoring.
- Rev 7 (2026-09-27): blockers 11 and 12 discharged — the sim-time-stamp
  fix (root cause was Isaac's `useSystemTime`, not M1) and the M5 shadow
  wiring are merged at `97634be` and live-verified (findings Rev 14 §AQ).
  New items 13–14: the Arm A goals-parity gap (pre-freeze decision) and
  the T1-tuning basket (parked-flicker threshold, FCFS zone radius vs
  spawn distance, Arm B stopped threshold, M4 speed-rule margin). A4
  gains the sim-time measurement notes (rescore era fix, −0.45 s join
  offset).

---

## Purpose and Status

This document is an amendment set, not a new design. At freeze time its
bindings are absorbed into the research design spec as rev 9 and frozen with
the `prereg-v1` tag; until that tag exists, nothing here is frozen. Every run
of 2026-09-16 through 2026-09-26 is pilot data and is excluded from headline
results per the spec's freeze rule.

Evidence citations of the form "Rev N §X" refer to
`docs/reports/2026-09-25-overnight-findings.md`.

---

## A1. Scenario Instrument: T2a Moves to the `_bshort` Family Variants

**Binding.** The T2a cells run on `head_on_asymmetric_w0p2_eopen_bshort_o0`
and `head_on_asymmetric_wopen_e0p2_bshort_o0`: blocked-side goal at the
blocked robot's spawn (±1.5), open-side passer goal at ±2.6, spawns, blockers
and oracle blocks byte-identical to the frozen v1 variants (commits `e708ffa`,
`dcfa144`).

**Rationale.** The v1 (±2.5) goals put the blocker on the passer's own goal
path, which cost 5 of 12 pilot episodes plus G4 (Rev 6 §W item 6, Rev 7 §AC);
the `_gshort` symmetric ±1.5 goals removed those losses but placed the
passer's rest pose inside the yielder's return path, losing 2 of 6 episodes to
a permanent M4 safety hold (Rev 8 §AD). `_bshort` shortens only the
blocked-side goal; its west pilot was 3/3 position-verified with a 0.000 m
passer backtrack (Rev 9 §AG). The passer goal was widened 2.5 → 2.6 to take
the escort-endpoint margin from 0.061 m to 0.161 m, above the ≈0.1 m drift
the `FEASIBILITY_MARGIN_M` comment cites (commit `dcfa144`).

**Conditions attached.**

- Adoption is conditional on the east `_bshort` pilot and a west re-run at the
  ±2.6 goal (n ≥ 3 each). **Satisfied 2026-09-26** (findings Rev 10 §AI):
  east 3/3 and west 3/3, all position-verified, correct yielder executed
  6/6, zero blocker-path losses and zero park-beyond-goal holds. Caveat
  recorded there: Nav2 stops the passer ≈0.07–0.10 m short of the nominal
  goal, so the realised escort margin is 0.063–0.096 m, not the designed
  0.161 m.
- Arrival re-scoring must carry the `box_overlap` flag (commit `8e77bc4`): the
  blocked-side goal leaves 0.13 m chassis-front clearance to the box near
  face, and the 0.35 m arrival tolerance could otherwise accept an overlapping
  pose (Rev 9 §AH item 3).
- Operator steps are part of the protocol: `orchestrator.yaml`
  `initial_tasks` hand-set per variant (M5 does not read scenario-YAML goals),
  scenario USDs regenerated after any YAML change, installed configs verified
  by content/md5, never by build exit code (Rev 8 §AE).

---

## A2. Presentation Order: Random, Seeded, Analysis-Conditioned

**Binding.** `prompt_robot_order: random` with a per-run seed
(`prompt_robot_order_seed`, else derived from `VGU_RUN_ID`), one draw per
episode, recorded in every decision artifact
(`robot_presentation_order`, `prompt_robot_order_mode`,
`prompt_robot_order_seed`, `episode_index`). Every analysis of an
obstacle-channel or feasibility effect must condition on the drawn order.

**Rationale.** The yielder gpt-4o names under the production-default `id_asc`
is a positional artifact: the first-slot and `robot_1` priors agree and swamp
the feasibility evidence (124/125 `robot_1` in the §T control). The obstacle
text is read only when the priors cancel under `id_desc` (P(feasible) 0.962
vs 0.556, p = 8.8e-4, Rev 6 §T; direction replicated, magnitude
scene-dependent 0–1, Rev 7 §AA). An unconditioned analysis therefore averages
an observable cell with a blind one.

**Guard.** Random draws can align with side by chance — batch 2 drew
`id_desc` on all three west runs and `id_asc` on all three east runs,
realising exactly the confound this binding exists to prevent (Rev 7 §Z).
Per-cell drawn-order counts are mandatory reporting, and cells left empty by
the draws are filled with forced-order runs, labelled as such.

---

## A3. M3 Yield Feasibility Gate: `swap`, Scored Pre-Gate

**Binding.** `grounding_yield_feasibility: "swap"` (quoted — a bare `off` is
YAML `false`) in the shared M3 grounding stage, with the audit fields
(`yield_robot_grounded_from`, `yield_regrounded_reason`,
`yield_refusal_reason`) in every artifact.

**Rationale.** The gate is the only mechanism that has made the blocked cell
succeed (L1, G1; Rev 2 §C item 1, Rev 4 §L item 4); without it that cell is
the deterministic pre-gate failure mode (R2, L4, D2, O1, O2). `refuse` is
inferior (L5). The gate never harmed a run across 20+ pilot episodes.

**Scoring consequence (pre-registered).** Because M3 grounding is shared by
both arms, the gate would also rescue Arm B's FCFS pick on T2a. RQ3
oracle-agreement is therefore scored on the reasoner's **pre-gate** named
assignment (`decision.yield_robot` for Arm A, the FCFS answer for Arm B);
episode outcome includes the gate identically in both arms. This keeps the
gate from laundering either arm's social-reasoning score while keeping the
executed system safe.

---

## A4. Outcome Metrics: Position-Verified Episode Outcome Primary

**Binding.** Primary per-episode outcome: both robots' arrivals accepted by
the arrival position check (`arrival_position_check: true`, tolerance 0.35 m,
M1 cross-check; commits `4f39899`–`069e1f2`), re-scored offline from the
scene log matching both acceptance lines (`scripts/rescore_arrivals.py`).
Secondary: first answer (the pre-gate strategy and yielder of the episode's
first analysis). Resolution time (first analysis → both arrived) is reported
descriptively.

**Sim-time measurement notes (2026-09-27, findings Rev 14 §AQ).** Scene
logs carry sim-time stamps since merge `97634be`; `rescore_arrivals.py`
must use its era-aware path (a pre-fix script silently scores every
post-flip arrival `stale_estimate`). Offline joins of M1 to ground truth
by time shift by −0.45 s (constant M1 stamp lag). Pre-flip and post-flip
runs must not be pooled on any speed- or status-derived measure without
noting the basis change (M1 speeds ≈2.6× larger, parked-robot
STOPPED/SLOW flicker ≈4× more transitions).

**Definition to pin at freeze.** The passer-backtrack statistic has two
defensible definitions that disagree on gshort H2 (0.878 m peak-minus-minimum
vs 0.580 m first-turnaround; findings Rev 10 §AI metric note); the
measurement plan must pin one before the statistic is quoted comparatively.

**Rationale.** First answer and episode outcome disagree on the same
mechanism (D2 2/2 vs L4 0/2; Rev 4 §L item 6). Nav2 goal success is not
arrival: E1's false success sat 0.59 m from goal (Rev 6 §V); re-scoring all 31
pilot runs flipped exactly that one event (Rev 7 §X). ER-2's first decision is
additionally non-comparable to gpt-4o's because of its opening-`reverse`
habit (Rev 3 §I item 2, trigger-qualified by Rev 6 §U).

---

## A5. Safety Reporting: Distance Channels, Not Contact Flags

**Binding.** Standard safety columns per run: minimum pairwise
centre-to-centre distance and the percentage of ground-truth rows below
`safety.yaml` `min_distance_m` (0.45 m). Ground-truth contact flags
(`robot_robot_contacts`, `robot_static_contacts`) are disqualified as
evidence: the detector stayed silent through a sustained 0.076 m wedge
(Rev 7 §AC, metric correction 2).

**Context to report with the columns.** 5–7% of rows below 0.45 m is the
design-expected signature of a completed yield (head-on robots must close to
pass); sustained breaches near contact depth (G4-class) are incidents and are
reported individually.

**Safety item — CLOSED 2026-09-26.** The exemption fix landed at `45e55f4`
(only `yield`/`reverse` exempt a pair; per-robot action from
`/coordination/commands`; unseen commands fail closed) and passed both VM
regressions: the mock-forced G4/K1 exposure now latches and holds the pair
at 0.381 m with no contact, and the ER-2 yield flow is unchanged (findings
Rev 12 §AM). Two tracked, non-blocking residuals: the latch-first (K1)
ordering is unit-covered but not host-reproducible, and a Nav2 leg going
ACTIVE after a latch holds its goal until the 120 s watchdog (root-cause
report mitigation 2). Original item, for the record:

**Open safety item (pre-Arm-B blocker) — root cause found, fix pending.**
G4 and K1 were ≈51 s each of driven nose-to-nose **contact** at 0.076 m
(exactly touching for this chassis), not interpenetration
(`docs/reports/2026-09-26-close-approach-analysis.md`, findings Rev 11
§AK). Cause: M4's coordination exemption disarms the 0.45 m rule and the
STALE fail-safe for any pair with an ACTIVE command; an ER-2 `reroute`
grounded onto the post-`reverse` re-approach put both robots ACTIVE and one
drove into its waiting partner. The contact fields are hard-coded `[]` — no
detector exists. Adopted fix direction (unimplemented): only `yield` and
`reverse` exempt a pair; Nav2-goal legs and waits do not, paired with a
prompt no-progress failure for Nav2 legs. Arm B's policy table emits
`reroute` for `blocked_path`, so the classical arm inherits the identical
exposure — the fix must land and be regression-verified on the VM before
either arm collects. This item stays a freeze blocker until then.

---

## A6. Model and Decoding Table Amendments

**Primary (gpt-4o).**

- `temperature=0.0`, `max_attempts: 4` (Arm M: terminal refusal 26.9% vs
  57.1% at the shipped 2, p = 0.031; Rev 6 §S), re-ask retained.
- The safety-refusal class is a documented model characteristic: the
  **camera frame's content** is the trigger (22/60 real vs 0/120 grey,
  p = 1.5e-12, Rev 6 §S; the annotation overlay is NOT causal — raw frames
  refuse at least as often on the skew-gated pairs, Rev 13 §AN), attempt-1
  rate 14–25% on real frames, stimulus-locked. Refusal rates per cell are
  mandatory reporting; refusals consume analysis slots and are costed as
  such. Annotation masking and downscaling are both ruled out as
  mitigations; grey substitution is the only image-side lever.
- `image_fallback_after_attempts: 2` is **validated** (Arm X, Rev 13 §AN:
  terminal refusals 10/84 → 0/84, p = 1.5e-3) and kept. Decisions carrying
  `image_fallback_used: true` are still reported separately from all pooled
  rates: yielder agreement under the fallback rests on n = 1, and the grey
  stimulus is the cell that moves yielder choice on standoffs. The field
  `image_fallback_after_attempts` must be added to
  `reasoner_config_effective` (it is currently absent from artifacts).

**Secondary backend: Gemini Robotics-ER 2 replaces `llama_server`.**

- Rationale: working drop-in (Rev 3 §I item 1), zero refusals in 300+ live
  and replay calls against gpt-4o's ≈23% attempt-1 (Rev 5 §P), preferred
  wherever a lost analysis slot is costly.
- Two structural confounds travel with every ER-2 number: the Interactions
  API exposes no sampling controls (`unsupported_sampling` recorded per
  call), and thinking is billed but never emitted, so its reasoning is not
  inspectable (Rev 3 §F).
- Model characteristics documented, not fixed: the opening `reverse` on
  asymmetric scenes (trigger-confounded, Rev 6 §U — opening-strategy analyses
  must condition on trigger type), and an unanchored, near-chance yielder
  choice (no `robot_1`/first-slot prior; Rev 7 §AC).
- Per the spec's secondary-model rule it runs the headline cells only.

**Unchanged REQUIRED-at-freeze rows** (exact model strings and versions,
image resolution, max output tokens, prompt-template hashes) still gate data
collection.

---

## A7. Episode Rule and Trigger Taxonomy

**Binding.** An episode is the `AttemptMemory` scope: opened on a disjoint
robot set, closed only on a position-check-accepted arrival of a tracked
robot; the presentation order is drawn once per episode. Solo-stall triggers
enter the M2 pipeline (E0 deviation, Rev 1) and are legitimate episode
openers; every per-episode analysis that touches opening strategy must
condition on trigger type (solo vs pair stall, Rev 6 §U).

---

## A8. Run Provenance Requirements

Every collected run must carry: VM tree verified by md5 against the named
commit; installed orchestrator YAML asserted by content before launch;
`reasoner_config_effective` in every decision artifact (commit `b518ed4`);
`keep_debug_frames: true` and `keep_raw_frames: true` (raw/annotated pairs
are not same-instant — |skew| mean 0.40 s — so annotation comparisons gate on
the ≤0.2 s subset, Rev 7 §Y); `ground_truth.jsonl` rescued into the run
directory before the next launch (Rev 8 §AE item 4).

---

## A9. Failure-Context Depth: Most Recent Attempt Plus Most Recent Failure

**Binding.** Re-analysis prompts carry the most recent resolved attempt
(the existing "Previous attempt in this episode:" block, unchanged) and,
when it is not itself the failure, the most recent failed attempt as a
second "Earlier failed attempt in this episode:" block
(`ReasonerRequest.last_failed_context`, commit `7f9884d`). Semantics,
pre-registered:

- "Failed" is any resolved outcome other than completed — `timed_out`
  included.
- The failed block lives under `AttemptMemory`'s existing overlap-plus-
  window scope: it must overlap the analysed robots and is dropped with the
  window (60 s default) or on a disjoint robot set. A failure older than
  the window is gone; this is a documented boundary of the policy, not a
  defect. A newer failure replaces an older one; a completed attempt never
  displaces the stored failure.
- Prompts with no second block are byte-identical to the pre-policy
  rendering (SHA-pinned; artifact replay reconstruction verified 130/130),
  so all pilot artifacts remain reconstructable.

**Rationale.** The one-attempt-deep context let a completed
`temporary_wait` evict a failed yield, and M2 re-selected the same
infeasible yielder (R2 request `7482f0ad`, L4 request `ca63fbd5`;
findings Rev 1 "Secondary Findings (a)", Rev 2 §D item 3). Both blocks are
persisted structurally in decision artifacts for the RQ5 analysis.

---

## A10. Arm B Rule Amendment: Parked-at-Goal Exclusion

**Binding.** `classify_scene`'s `blocked_path` candidacy (and the
`unknown` involved set) excludes a stopped robot whose position lies
within `arrived_exclusion_radius_m` (default 0.35, aligned with M5's
`arrival_position_tolerance_m`) of its own goal; head-on and
intersection rules, and the robot-ahead blocker check, are unchanged —
an arrived robot can still block someone else. A goalless robot is never
excluded. Commit `5e13805`; this amends the rev-8 Arm B specification at
rev 9 absorption.

**Rationale and evidence.** The T0 verification run exposed a rule-level
false-positive rate of 100% on parked scenes: 60/60 post-arrival probes
classified `blocked_path`/`anomaly`/`reroute` because the classifier has
no concept of "stopped because arrived". Replaying all 65 recorded probe
scenes: the old rule reproduces the recorded 60/5 tally exactly; the new
rule gives 65× `none`. Pre-freeze rule changes to Arm B are legitimate
under the tuning-parity clause (frozen at `prereg-v1` with everything
else); this one is recorded here precisely because it post-dates the
original Arm B specification.

---

## Freeze Blockers (checklist, status as of 2026-09-26)

1. ~~**Arm B does not exist.**~~ — **discharged at the reasoning-core level
   2026-09-26** (merge `65cc850`, findings Rev 12 §AM):
   `reasoning/baselines/` now holds the rev-8 classifier, policy table with
   FCFS/commitment tiebreak, shadow comparator and `classical:` config
   loader, 70 tests. Remaining Arm B work is items 10–12 below plus the
   tuning-parity pass on T1 before the freeze.
2. ~~**`_bshort` validation**~~ — **discharged 2026-09-26** (findings Rev 10
   §AI): east 3/3, west 3/3, A1's condition satisfied. The gpt-4o `_bshort`
   family pilot remains under blocker 5.
3. ~~**Failure-context memory depth**~~ — **discharged 2026-09-27**: policy
   decided (most recent attempt + most recent failed attempt) and
   implemented at `7f9884d`; see A9. Evidence correction: the displacement
   instances are R2 (`7482f0ad`) and L4 (`ca63fbd5`); D2's prompts would
   have been unchanged.
4. ~~**Arm X**~~ — **discharged 2026-09-27** (findings Rev 13 §AN): the
   fallback is validated and kept; the separate-reporting rule stands as a
   reporting rule, no longer as an unvalidated-mitigation guard.
5. ~~**gpt-4o credit-blocked arms**~~ — **discharged 2026-09-27** (findings
   Rev 13 §AN–§AO): arms F and S2 ran; the gpt-4o `_bshort` pilot is 6/6 on
   the adopted apparatus. The forced-order cells on the retired ±2.5
   variants are dropped as superseded by the `_bshort` adoption.
6. ~~**G4 safety root cause** (A5)~~ — **closed 2026-09-26** (see A5): fix
   landed and regression-verified. Residuals tracked in A5, non-blocking.
7. **B1 symmetric-`reverse` dispatch** — the handoff recommends keeping it as
   RQ5 evidence; ER-2 exercises it on every asymmetric episode. Confirm keep
   at freeze (Rev 3 §J item 3).
8. **T0 / T2b / T3 authoring** — design and build order fixed in
   `docs/superpowers/specs/2026-09-27-scenario-battery-design.md`.
   Progress 2026-09-27: **T0 built** (normal_flow scenario + M5 log-only
   probe mode with structural and defensive no-dispatch layers; VM
   verification pending) and **Pillar 2 stage-2 retreat machinery built**
   (retreat-choice contract; `GroundingParams` with `legacy` default
   pinned byte-identical by a SHA over 576 grounder outputs;
   candidates/sweep/ranking with `ranked[0]` = classical stage-2 by
   construction; derived grounding composed after the yield gate) —
   unblocking T3b. Still open: the prompt-v2 bundle (gates T3a/T2b;
   subsumes items 10 and 13), T3c oracle + smoke, T3a pairs, T2b
   (3-robot verification + forced-order harness), the T3b scenario with a
   widened `aisle_y_band_m`, and the M5 derived-mode wiring/config flip
   after the bundle.
9. **REQUIRED model-table rows** — recorded at freeze (A6).
10. **Shared-contract fields for Arm B parity** — `CongestionDecision` has
    no `blocker_kind` or `crossing_order` (plan Task 1's additive optional
    fields). Costs nothing on two-robot cells; degrades Arm B's executed
    decision at 3+-robot intersections and blocks the T3a blocker-verdict
    comparison. Decide with the T3 authoring (blocker 8).
11. ~~**M1 speed-scaling convention**~~ — **discharged 2026-09-27**
    (findings Rev 14 §AQ): root cause was Isaac's `useSystemTime=True` on
    the camera helpers, not M1; flipped at `a1aa81d` with the M1
    clock-reset guard and `stale_after_sec` retuned to 1.15, live-verified
    (M1 transit speed 0.14 vs ground truth 0.15; trigger timing
    unchanged). Threshold retunes go to the T1 basket (item 14).
12. ~~**Arm B Phase-2 wiring**~~ — **discharged 2026-09-27** (findings
    Rev 14 §AQ): shadow logging live on every analysis (`6d70238`,
    merged `97634be`), verified 13/13 with clean records; first data show
    classical vs ER-2 disagreeing on 12/13. Caveat tracked: FCFS arrival
    censoring when a robot spawns on the zone boundary
    (`censored_arrivals` flag in progress; radius question in item 14).
13. **Arm A goals-parity gap (pre-freeze decision)** —
    `build_reasoner_request` has never carried goals (the robot view has
    no goal field, so every prompt ever sent had `goal=None`), while Arm
    B's shadow frames carry registry goals that its head-on/intersection
    rules use. Decide before the tag: give the VLM goals (changes every
    prompt; breaks comparability with all pilots) or pre-register the
    asymmetry as a documented arms difference.
14. **T1 tuning basket — discharged 2026-09-29, pending coordinator
    review** (`docs/reports/2026-09-29-t1-tuning-basket.md`, `caaf95f`):
    new `fcfs_zone_radius_m` 1.0; the M1 thresholds, Arm B
    `stopped_speed_mps` and the M4 0.2 m/s rule kept (0.03 recorded as
    the rejected `stopped_threshold_mps` option). Original item
    (tuning-parity rule applies: T1 only, before the tag): `stopped_threshold_mps` (parked STOPPED/SLOW flicker, ≈4×
    transitions since sim-time), the FCFS conflict-zone radius vs the
    1.5 m spawn distance (censoring), Arm B `stopped_speed_mps`, and the
    M4 0.2 m/s speed-rule margin vs Nav2's 0.18 cap.
10. ~~**Shared-contract fields**~~ and 13. ~~**goals-parity gap**~~ —
    **discharged 2026-09-27** by the prompt-v2 bundle (Rev 10 above).
    Goals rider: implemented on the recommended default; explicit user
    confirmation pending, revert isolated.
15. **Prompt-v2 wording sign-offs — decided 2026-09-27 by the
    coordinator, reviewable until the tag:** (a) the guidance line is
    reworded to permit stated goals/tasks as evidence while forbidding
    invented intent ("Decide from the robot states (including their
    stated goals and tasks) and the image; do not assume intentions
    beyond what is stated." — implemented at `b4a8d91`, v2 re-pinned
    once pre-freeze, v1 and replay integrity untouched); (b) **confirmed**:
    T3a's untracked robot-shaped blocker labels `transient` — "robot" is
    defined as a listed robot and the blocker is deliberately unlisted;
    this is the tier's oracle; (c) **confirmed**: the leakage-guard
    exemption for the literal schema token `"blocker_kind"` is correct.
    The user's standing "continue" covers these defaults; final veto at
    the tag.
16. ~~**Calibration mini-pilot**~~ — **discharged 2026-09-28** (both
    backends funded; 6/6 position-verified, first yield 150.8–152.7 s
    and safety columns all in band; stage-2 healthy 6/6 first-attempt;
    the image fallback's first closed-loop use executed a yield decided
    on the grey image, reported separately). Two divergences recorded:
    (a) gpt-4o named `robot_2` on west 3/3 (gate 0/3, vs 3/3 in the N
    batch) — cause ambiguous at n = 3 between the trigger-scene change
    (robot_1 SLOW, a sim-time-era status) and v2's rendered goals; the
    gate stays (it is a no-op on feasible namings) and the
    gate-necessity claim is scoped to v1-era evidence in the prereg
    text; (b) the stage-2 letter-A prior → item 26.
26. **Stage-2 candidate-listing randomization — IMPLEMENTED 2026-09-28**
    (`526d957`; stage-2 prompt v3; v2 preserved with byte-reproduction
    and the calibration corpus re-verified through it; three-way scorer
    taxonomy — first-listed vs default vs letter-A — pinned; deploy-skew
    trap: trust `listing_order` only when `stage2_prompt_version == 3`).
    Original decision record:** both models chose
    letter "A" 6/6 (p = 1/64), including over the default letter — a
    letter/slot prior the instrument should not carry. Fix: list the
    candidates in seeded-random order in the stage-2 prompt (decoupling
    letter, slot and rank three ways), stage-2 prompt v3, re-pinned
    pre-freeze. A pick-A policy would read null (chance) in the
    approved T3b test either way, so this is a power fix, not a
    validity fix. Also recorded: stage-2 justifications hallucinate
    obstacles on featureless scenes — a caution against reading stage-2
    justification text as evidence.
17a. **T3a outcome-contrast amendment (item 18, decided 2026-09-27,
    reviewable at the tag):** T3a is scored on the decision — the
    divergent-and-correct rate against the pre-registered per-kind
    strategies (object → `reroute`, transient → `temporary_wait`) and
    the `blocker_kind` verdict — because the apparatus offers no outcome
    contrast: `reroute` re-sends the goal that M4 already re-sends every
    2 s, so the object member cannot resolve under any strategy and the
    transient member resolves under any once the blocker despawns. The
    run matrix's "B executed on 5 pairs for outcome contrast" T3a cell
    is dropped at rev 9 absorption; the classical shadow (forced
    `object`/`reroute` non-divergence) is recorded on every T3a
    decision, preserving the tier's contrast where it actually lives.
17b. **T3a apparatus deviations for tag-time review (items 19–20):**
    the transient blocker is the robot visual scaled **1.82×** so the
    single-plane lidar at 0.182 m intersects a plate (at 1× only the
    7 cm head is scannable and Nav2 simply plans around it) — a visible
    size confound between "a robot-shaped transient agent" and the
    tracked robots, accepted with this record; both blockers spawn via
    `timed_obstacles` at 16 s on byte-identical maps (a baked or
    t=0-present box either strands the robot at spawn or moves the
    stall point ≈1.5 m — the members must differ only in the entity);
    corridor 0.50 m (vs T1's 0.55) for closability; robot_2 runs the
    north pocket; per-robot task labels now differ truthfully
    (`traverse_aisle`) and render in v2 prompts.
23. **T3b yielder-side restriction (decision before funded collection):**
    only `robot_1` works as the yielder in the authored junction
    geometry — a `robot_2` yield parks at x = 2.723 whose top-ranked
    candidate sits inside the NE rack past the image edge (Arm B named
    robot_2 in the smoke on a first-come tie). Options: score only
    executed-robot_1-yield trials (recording the discard rate), or
    force the yielder. **Coordinator recommendation:** condition on the
    executed yielder (no scene or gate change; the discard rate is
    itself reportable), sizing n upward to compensate.
    **APPROVED by user 2026-09-28** as recommended.
24. **T3b criterion correction (blocks freezing the tier's test):** with
    k = 3 and one occupied candidate, chance of avoiding the occupied
    one is 2/3, not the run matrix's 1/3 — "≥ 9/15 vs chance 1/3" is
    vacuous (p = 0.80). **Coordinator recommendation:** re-specify the
    primary test as the occupied-choice rate BELOW chance 1/3 (exact
    one-sided binomial; ≤ 1/15 rejects at α ≈ 0.017), or raise n; fix
    the oracle `rationale` wording to neutral text once decided.
    **APPROVED by user 2026-09-28**: occupied-choice rate < 1/3, exact
    one-sided binomial; oracle rationale to be neutralised at rev 9
    absorption.
25. **M4 raw-`cmd_vel` obstacle blindness (standing safety note):**
    maneuver legs (backup, sidestep) bypass Nav2 and the collision
    monitor entirely — third instance of this family after the
    exemption-pair scope and the T2b backup-through-robot finding. In
    T3b it is the *intended* outcome mechanism (occupied-default trials
    deliberately produce robot-obstacle contact in sim); outside T3b it
    remains an M4 hardening item for any post-prereg roadmap.
17. **T2b scope decision** — the three-robot feasibility investigation
    (`docs/reports/2026-09-27-three-robot-feasibility.md`) prices T2b at
    a 12-item build list including two REQUIRED safety changes before
    any wrong-order verification run (pair-scoped clearing exemption;
    hold-until-last ordered release — the minimum Pillar-3 chain), with
    the dominant risk that the "wrong order" is a collision rather than
    a slower run. Decide: build it, redesign the tier cheaper, or drop
    it (weakens RQ3's ambiguous-ordering evidence) — before any T2b
    authoring.
    **Coordinator recommendation (2026-09-27, not a decision): DEFER**
    T2b behind T3a and T3b. If it is built, land the investigation's
    items 9 and 11 first as standalone safety work (the pair-scoped
    exemption closes a real hole — a yielder is currently unguarded
    against any bystander — and hold-until-last is the minimum ordered
    release), then re-cost the tier. A cheaper 2-robot re-design was
    considered and rejected: without a moving third robot there is no
    ordering dimension, only another feasibility contrast, which T2a
    already provides. Explicit user decision still required.
    **DECIDED by user 2026-09-28: BUILD.** Execution order per the
    feasibility report: safety items 9 (pair-scoped clearing exemption)
    and 11 (hold-until-last ordered release) land and verify FIRST;
    no wrong-order run before both are live.
    **Safety slice LANDED 2026-09-28** (`9c38042`…`b0ff818`; the
    feasibility report's own build-table numbering is #8/#10 — both
    numberings cited in the notes entry): pair-scoped exemption with
    fail-closed semantics and the bystander guarantee, ordered
    hold-until-last release (`crossing_chain.py`), a first-passer guard
    that refuses mis-ordered yields (which would otherwise reverse the
    yielder onto the queued robot while exempt), M3 multi-passer yield
    fan-out with per-passer clearances, and two-robot behavior pinned
    byte-identical (status-stream pins written against the pre-change
    code). Live VM regression pending the next batch. Remaining T2b
    slices: launcher 3-robot loop, oracle `correct_order`, episode
    scoping, order scheme, scenario + forced-order harness.
    **Main slices LANDED 2026-09-28** (`4295de2`…`3362a54`, 11 commits):
    oracle `correct_order` + margin record; launcher robot loop
    (golden-pinned two-robot byte-identity); `start_delay_sec`
    hold-back; episode fold + close-on-last-arrival (300-sequence
    two-robot pin); `random` order FIXED to draw uniform permutations at
    N ≥ 3 (it never put robot_2 first before — a real instrument gap);
    per-passer derived clearances; the `t2b_flow_ordering` scenario with
    mutation-checked constraint pins; and the forced-order harness with
    a hard safety preflight. Coordinator defaults recorded, reviewable
    at the tag: (a) **a censored alternative arm counts as dominated** —
    the wrong order most likely ends in a permanent bystander latch, so
    the ≥20% margin is reported as a lower bound and the harness labels
    it LOWER-BOUND, never PASS; (b) **T2b is pre-registered on legacy
    grounding** — derived mode breaks both arms geometrically (backup
    clearance vs queued robot; escort end vs passer goal), the tier
    tests ordering rather than retreat selection, and legacy is the only
    mode with the first-passer guard; a tier-scoped apparatus difference
    to state in the prereg text; (c) corridor shortened to 1.0 m
    (escort-end geometry, same authoring logic as T3b's junction). Watch
    item: the episode fold rule has no proximity test — any 3+-robot
    scene folds a solo stall into a busy pair's episode until its
    command resolves. VM: USD, 3-robot smoke (record RTF and robot_3's
    position at trigger), and the forced-order margin runs pending.
    **VM batch COMPLETE 2026-09-29** (notes `544000f`; artifacts
    `data/logs/vm_runs/t2b_smoke/`): three-robot smoke PASS (ordered
    release live, robot_3 admitted 0.04 s after robot_1 clears, yielder
    resumes with the last passer; 55 s hold-back validated with 11–12 s
    headroom at RTF 0.34; all arrivals verified), the **bystander latch
    verified live** (the alternative arm's robot_2+robot_3 pair latched
    at 0.43 m within 4 s of both moving, zero contacts — the safety
    slice's missing live test, PASS on both seeds), and the **oracle
    margin frozen: LOWER-BOUND 0.6485** (censored per the approved
    rule; `7400482` writes it into the YAML with updated pins). Scorer
    definition to pin at rev 9 (batch finding F6): what counts as an
    arrival for a robot latched at its goal — harness GT scoring and
    M5/rescore currently disagree. Also resurfaced: `--duration-sec`
    is STILL a dead flag (F1, first logged Rev 1 §7 item 5); Arm B's
    FCFS yielder at the symmetric standoff is a live coin flip (F4,
    fine for the tier — the shadow records the actual pick).
