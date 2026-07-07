# VLM as Congestion-Resolution Reasoner — Research Design

**Date:** 2026-07-07 (rev 7 — restructured as a controlled experiment around
the preserved research objective; the rev-1..6 mechanisms survive as the
apparatus. Prior revision history: rev 6 — temporal context via
single-frame visual traces + motion table, multi-image rejected on
TempVS/ACL-2025 evidence, semantic-conditioned strategy arbitration; rev 5
— failure-context feedback (Reflexion-lite); rev 4 — integrated-contribution
framing, conservative related work; rev 3 — feasibility bands, no-snapshot
degrade, uniform projected-clearance release; rev 2 — two-stage flow,
explicit yield/order fields, hold-until-last, swept validation, no-blind
fallback; rev 1 — pillars.)
**Status:** In user review.
**Predecessor system:** the verified head-on yield protocol (H3 runs 8–13)
and the M1→M5→M2→M3→M4 closed loop, live on the GCP/Isaac host.

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

## Hypotheses (thesis skeleton)

- **H1 Perception/classification:** the VLM recognizes congestion and its
  type from the annotated scene (vs. ground truth labels).
- **H2 Strategy competence:** its strategy choices resolve congestion
  (vs. a classical per-type policy, outcome-measured).
- **H3 Social reasoning:** its `yield_robot`/`crossing_order` assignments
  are effective (vs. FCFS + commitment-tiebreak baseline).
- **H4 Semantic advantage:** it exploits information no classical baseline
  has — blocker semantics and untracked visual elements.
- **H5 Closed-loop adaptation:** failure feedback deliberately changes its
  subsequent decisions (vs. memoryless re-analysis).

## Experimental arms & shadow logging

- **Arm A (treatment):** VLM reasoner — all decision points below.
- **Arm B (control):** classical reasoner — same detection trigger, same
  grounding validation, same M4 execution; decisions by: geometry
  classifier (H1), per-type policy table (H2), FCFS + commitment tiebreak
  (H3), geometry-max retreat (stage 2). The execution layer is identical
  across arms — outcomes are attributable to the reasoner alone.
- **Shadow logging:** in Arm A, the classical answer is *also* computed
  and logged for every decision; disagreements are first-class events.
  Every episode yields comparison data; disagreement-outcome analysis
  ("when the VLM deviated from classical, did it help?") is a primary
  result.
- **Modality conditions (Arm A only):** dual-channel (default) /
  text-only / image-only. The state table intentionally duplicates much
  of the image content; these conditions locate where the reasoning
  actually lives rather than leaving the redundancy untreated.

## Scenario battery (three tiers — the discriminating instrument)

- **T1 Geometry-sufficient** (non-inferiority tier): current
  `head_on_deadlock` (0.55×2.0 corridor) and `intersection_bottleneck`.
  Classical solves these; the VLM must match it (success rate within
  margin, no safety violations).
- **T2 Geometry-ambiguous** (reasoning tier): variants where naive
  geometry is wrong or arbitrary — (a) asymmetric retreat space (one
  side's candidates infeasible; correct yielder is NOT the FCFS pick
  because the first-arriver has no retreat room); (b) symmetric standoff
  with asymmetric downstream traffic (correct order depends on flow, in
  the trails/motion table).
- **T3 Semantics-required** (only-VLM tier): (a) paired blocker
  counterfactuals — near-identical geometry, static object vs transient
  agent (divergent correct responses: reroute vs wait); (b)
  obstacle-in-candidate — an **untracked** visual obstacle inside the
  geometry-max retreat candidate (classical picks it; correct choice
  requires vision); (c) `dynamic_anomaly` timed-obstacle runs. Note: M1
  tracks only ArUco robots, so untracked elements exist in the image and
  in NO text channel — this asymmetry is what makes T3 vision-load-bearing
  by construction.
- Authoring T2/T3 variants (scenario yamls + USD rebuilds + obstacle
  assets) is a first-class work item, not an afterthought — without them
  the experiment cannot discriminate.

## Pre-registered success criteria

Defined before data collection; "VLM cannot" is a reportable outcome:

- **"VLM can" requires all of:** T1 non-inferiority (resolution success
  within 10 pp of classical, zero safety-envelope violations — the
  containment layer makes violations structurally impossible, so this
  measures degradation frequency instead: `*=default` rate < 20%);
  T3 superiority (blocker counterfactuals: correct divergent behavior
  where classical cannot diverge; obstacle-in-candidate: avoids the
  occupied candidate above chance); H5 adaptation (second decision changes
  in the informed direction on forced-failure episodes).
- **Partial answers are findings:** e.g., "competent arbiter on T1/T2,
  decisive only on T3 semantics" or "text-only equals dual-channel
  everywhere except T3" are publishable characterizations.

## The apparatus (mechanisms; adopted techniques, none claimed novel)

The four pillars from revs 1–6 are the machinery both arms run on. Full
mechanism detail as previously specified; summarized with their roles:

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
  (swept-path validated, feasibility-banded per rev 3), M1 renders them
  as set-of-mark letters, VLM selects `retreat_choice` + one-clause
  justification. Stage-2 failure → geometry-best candidate (which is
  Arm B's answer — the fallback IS the control).
- **Annotation legibility (from the noise review):** identity = color,
  status = box style; boxes shrunk toward true footprint; labeled goals
  (G1/G2); candidate letters in a reserved color; leader-line labels in
  clusters; stage-2 frames drop arrows/goal markers; the prompt explains
  the annotation scheme in one sentence.

### Pillar summaries (mechanism detail: revs 2–6, unchanged)

1. **Derived geometry:** backup/escort distances from actual poses with
   feasibility bands (out-of-band ⇒ infeasible ⇒ reroute/reanalyze; no
   clamped or blind execution); no-snapshot ⇒ non-spatial wait;
   projected-progress clearance predicates; escort heading from odom.
2. **Candidate selection:** set-of-mark selection among pre-verified
   options (adopts 2310.11441/2310.07937/CoNVOI); geometry-max ranking is
   simultaneously the default, the fallback, and the control arm.
3. **Ordered crossing:** explicit `yield_robot`/`crossing_order` fields,
   permutation-validated; event-driven sequenced release (uniform
   projected-clearance predicate incl. first passer); yielder holds until
   last clears, then rejoins; wait-expiry ⇒ FAILED + suppression retained
   + reanalysis, never silent release.
4. **Semantic-conditioned strategy arbitration:** `blocker_kind`
   constrains the compatible strategy set (robot→full set;
   object→{reroute, bounded wait-probe}; transient→{wait, reroute}); VLM
   selects within it using scene, traces, and failure context; out-of-set
   ⇒ per-kind default, logged.

### Containment (the laboratory's safety glass — unchanged)

VLM outputs restricted to system-generated discrete options; geometric
revalidation at grounding (swept segments, permutations, feasibility);
verified-or-degrade everywhere; all degradations logged `*=default` and
counted in the metrics. A wrong VLM answer produces a logged degradation,
never unsafe motion — which is precisely what makes Arm A safe to run.

## Measurement plan

Per episode: resolution success, time-to-resolution, cycles, safety stops,
degradation counts, full decision artifacts (both stages, justifications,
shadow answers, disagreement flags). Analyses: per-tier arm comparison
(H1–H3), counterfactual divergence (H4), adaptation trajectories (H5),
modality deltas, disagreement-outcome analysis. Qualitative: justification
review on disagreement cases.

## Ablations

With/without image (stage 1 and stage 2); with/without temporal context
(traces + motion table); with/without failure context (forced-failure
episodes); annotation scheme (legible vs legacy) on a T3 subset — checks
whether the noise fixes matter.

## Related-work positioning (conservative; writing rule unchanged)

Mechanisms adopt: set-of-mark (2310.11441), candidate selection
(2310.07937, CoNVOI), LLM-arbiter ordering (LLMDR), social corridor
decision (NOD 2504.20947), trace prompting (TraceVLA), structured motion
summaries (MotionVLA); versus REALM (2404.06413): discrete bounded
arbitration instead of free waypoints over CBFs, warehouse BEV setting,
and — the actual contribution — the **controlled two-arm evaluation with
shadow logging and a tiered battery answering when/whether the VLM helps**.
Avoid "first"/per-pillar novelty claims; SocialNav-SUB (2509.08757) and
TempVS (2506.10415) motivate input design (weak VLM spatial/sequence
reasoning → text tables + traces + selection-not-generation).

## Out of scope (future work)

Rotation/roundabout strategy; occupancy-grid free-space search; VLM metric
coordinate output (candidate densification is the on-ramp); multi-frame/
video input (rejected on TempVS evidence; revisit as models improve);
task-level escalation via M5's registry (MRTA/TAMP scope).

## Testing

- **Unit (offline):** all rev-3..6 items (derivations, feasibility edges,
  candidate sweep validation, ranking determinism, label fallback,
  order validation, release chain incl. escort-terminal-not-clearance
  case, hold-until-last, wait-expiry suppression retention,
  compatibility-matrix enforcement, ring buffer/trails/motion-table,
  failure-context block presence) **plus:** Arm B classical reasoner
  (deterministic outputs on synthetic snapshots), shadow-logging
  plumbing (disagreement flag correctness), modality-condition prompt
  assembly.
- **E2E (host):** per tier — T1 regression both arms; T2 variants
  (FCFS-wrong case shows the disagreement machinery); T3 counterfactual
  pairs + obstacle-in-candidate + adaptation trajectory (wait → forced
  expiry → informed reroute). Decision artifacts must contain both arms'
  answers per decision.

## Files touched (expected)

- `reasoning/schemas/` (stage-1 fields, stage-2 response schema),
  `reasoning/vlm/` (models, parser, prompt builder: temporal/failure
  blocks, modality conditions, annotation-scheme sentence)
- `reasoning/rag/command_grounder.py` (snapshot param, derivations,
  candidates, ordering, compatibility matrix, infeasible outcomes) + a
  new `reasoning/baselines/classical_reasoner.py` (Arm B + shadow)
- `swarm_orchestrator/` (two-stage orchestration, ring buffer, motion
  table, arm/condition switching, shadow logging in decision artifacts)
- `swarm_perception/annotation.py` (legibility pass, trails, candidate
  markers)
- `swarm_execution/` (sequenced release, rejoin, wait-expiry semantics,
  escort heading, projected-progress predicates)
- `isaac/config/scenarios/` + assets (T2/T3 battery, obstacle assets,
  USD rebuilds)
- Tests mirroring each.
