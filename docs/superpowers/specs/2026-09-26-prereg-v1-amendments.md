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
8. **T0 / T2b / T3 authoring** — the battery beyond T1/T2a (negative probes,
   downstream-traffic T2b, the three T3 tiers) has no authored scenarios or
   oracle blocks yet.
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
14. **T1 tuning basket** (tuning-parity rule applies: T1 only, before the
    tag): `stopped_threshold_mps` (parked STOPPED/SLOW flicker, ≈4×
    transitions since sim-time), the FCFS conflict-zone radius vs the
    1.5 m spawn distance (censoring), Arm B `stopped_speed_mps`, and the
    M4 0.2 m/s speed-rule margin vs Nav2's 0.18 cap.
