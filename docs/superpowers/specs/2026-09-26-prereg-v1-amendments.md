# Pre-Registration v1 Amendments — Pilot-Campaign Bindings

**Prepared:** 2026-09-26

**Revision history:**

- Initial draft: binds the decisions adjudicated by the 2026-09-24/26 pilot
  campaign (`docs/reports/2026-09-25-overnight-findings.md`, Rev 1–9) into the
  `prereg-v1` freeze of the research design
  (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`,
  rev 8.6), and lists the items still blocking that freeze.

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
  ±2.6 goal (n ≥ 3 each, in progress as of this draft). If either fails, the
  scenario question reopens and this amendment is void.
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

**Open safety item (pre-Arm-B blocker).** In G4 two stationary robots sat
interpenetrated at 0.076 m for ≈18 s while M4's safety monitor, the contact
detector, and M1's STALE fail-safe all stayed silent — the same geometry as
the July "Run D" incident cited in `safety.yaml`. Root-cause this before Arm
B collection; the classical arm dispatches without a VLM in the loop and
inherits whatever hole this is.

---

## A6. Model and Decoding Table Amendments

**Primary (gpt-4o).**

- `temperature=0.0`, `max_attempts: 4` (Arm M: terminal refusal 26.9% vs
  57.1% at the shipped 2, p = 0.031; Rev 6 §S), re-ask retained.
- The safety-refusal class is a documented model characteristic: the
  annotated camera frame is the trigger (22/60 real vs 0/120 grey,
  p = 1.5e-12, Rev 6 §S), attempt-1 rate 19–25% on real frames, terminal
  ≈10–12%, stimulus-locked. Refusal rates per cell are mandatory reporting;
  refusals consume analysis slots and are costed as such.
- `image_fallback_after_attempts: 2` is shipped but **unvalidated** (Arm X
  never ran; Rev 7 §AB). Until validated, decisions carrying
  `image_fallback_used: true` are reported separately from all pooled rates.

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

## Freeze Blockers (checklist, status as of 2026-09-26)

1. **Arm B does not exist.** `reasoning/baselines/classical_reasoner.py` is
   specified (spec rev 7) but absent from the tree, and with it shadow
   logging, the FCFS/commitment tiebreak, and the tuning-parity workflow.
   This is the largest single work item between here and the freeze.
2. **`_bshort` validation** — east n ≥ 3 plus west re-run at ±2.6 (in
   progress). A1 is conditional on it.
3. **Failure-context memory depth** — the context is one attempt deep; an
   intervening success evicts a failed yield and the same infeasible yielder
   is re-selected (Rev 1 §6(a), L4, D2). Decide last-N vs last-failed before
   Arm A collection; the choice changes the RQ5 prompt.
4. **Arm X** (image-fallback validation) — blocked on OpenAI credits; until
   run, the A6 separate-reporting rule stands.
5. **gpt-4o credit-blocked arms** — replay `--arm F`, the `--arm S2`
   remainder, the forced-order live cells, and the gpt-4o `_bshort` family
   pilot.
6. **G4 safety root cause** (A5) — pre-Arm-B blocker.
7. **B1 symmetric-`reverse` dispatch** — the handoff recommends keeping it as
   RQ5 evidence; ER-2 exercises it on every asymmetric episode. Confirm keep
   at freeze (Rev 3 §J item 3).
8. **T0 / T2b / T3 authoring** — the battery beyond T1/T2a (negative probes,
   downstream-traffic T2b, the three T3 tiers) has no authored scenarios or
   oracle blocks yet.
9. **REQUIRED model-table rows** — recorded at freeze (A6).
