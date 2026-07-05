# General Spatial Congestion Resolution — Design

**Date:** 2026-07-05 (rev 2 — incorporates external review: two-stage VLM
flow, explicit yield/order fields, hold-until-last-clears, swept-segment
validation, no-blind-fallback rule, corrected attribution)
**Status:** In user review.
**Predecessor:** the verified head-on yield protocol (H3 runs 8–13: backup →
sidestep → hold/escort → passer-cleared, all raw-cmd_vel primitives
lane-servoed). This design generalizes it across scenarios and deepens the
VLM's decision surface.

## Problem

The working yield resolution is scenario-tuned and spatially blind:

1. **Blind constants.** `backup_distance_m=1.3`, escort `2.4`, lateral
   `+0.35` (always left) were tuned offline for `head_on_deadlock`'s
   corridor. Different standoff positions or layouts can park a robot into
   geometry.
2. **Head-on assumptions baked in.** Escort heading assumes odom yaw 0
   points at the goal (false for the intersection scenarios' north–south
   robots); the yield template handles exactly 2 robots
   (`intersection_bottleneck`/`dynamic_anomaly` have 4).
3. **VLM spatial ability unused.** The VLM chooses strategy and role order
   but nothing spatial; `root_cause` is logged, never actuated.
4. **All-at-once release.** Queued robots resume simultaneously and
   re-collide; literature treats bottleneck/crowding as ordered-crossing
   problems.

Literature anchors: SocialNav-SUB (arXiv 2509.08757 — spatial relations are
frontier VLMs' weakest axis, PA≈0.55; set-of-mark + BEV prompting is the
effective mitigation), VLM frontier assignment (2310.07937 — VLM selects
among system-generated, image-annotated candidates; never emits
coordinates), NOD corridor passage (2504.20947 — who-commits/who-yields is
the social decision that matters), Voronoi-cell + congestion-metric
replanning (2202.11334 — decentralized replanning driven by a congestion
metric; supports congestion-aware sequencing generally, not token-passing,
which appears there only as related work), MIT REALM 2404.06413 + LLMDR
2503.00717 (foundation-model arbiter over safe low-level control). Design
principle adopted: **the VLM selects among system-proposed, pre-verified,
visually-annotated discrete options and orders robots; it never generates
metric poses.**

## Decision flow (two-stage — resolves the candidate/yielder circularity)

Retreat candidates depend on knowing the yielder; the yielder is the VLM's
choice. Therefore:

- **Stage 1 (existing analysis call):** VLM sees the annotated scene and
  outputs congestion/type/strategy, `yield_robot`, `crossing_order`,
  `blocker_kind`, justification. No spatial candidates yet.
- **Stage 2 (only when strategy = yield):** M5 generates validated retreat
  candidates for `yield_robot` (Pillar 2), has M1 render them as markers
  on a fresh frame, and issues a second, narrow VLM call whose only output
  is `retreat_choice` + one-clause justification.
- **Latency:** one extra VLM round trip (~2–6 s) inside Layer 2's 0.5–2 Hz
  budget; the robots are stationary in a standoff, so the cost is benign.
- **Stage-2 failure** (timeout, parse failure, invalid label): proceed with
  the deterministic geometry-best candidate (see Fallback rules). Stage 2
  never blocks resolution.

## Pillar 1 — Derived maneuver distances

`ground_reasoner_result` gains a `snapshot` parameter (the `SceneSnapshot`
already available at the `reasoning_pipeline.py` grounding call site).

- **Backup distance** (formalized): the minimum retreat-axis motion `d`
  such that, at the retreated pose, the yielder's separation from **every
  other robot in `crossing_order`** is ≥ pass-clearance
  (`2*min_distance_m + margin`), computed by projecting each robot's
  position onto the yielder's retreat axis; clamped to [0.5, 2.0] m.
- **Escort distance** = signed distance along the transit axis from the
  passer's hold-start position to the point past the yielder's parked
  position by pass-clearance; clamped to [1.0, 3.5] m.
- **Clearance events use signed projected progress**, not raw odometry
  displacement: progress = projection of (current − start) onto the
  robot's transit axis. Raw displacement counts lateral drift and servo
  wobble as progress; projection cannot go backwards-positive.
- **Escort heading**: M4 uses the passer's own heading at escort start
  (from its odom), not yaw 0.
- **Lateral magnitude** stays a config default (0.35 m) with per-scenario
  override. Map-derived lateral clearance is future work — this design
  verifies against robot poses, not the occupancy grid.
- **Fallback:** `snapshot=None`/malformed → clamp-midpoint constants,
  logged `distances=default`. (Distances are magnitudes along verified
  axes; a mid-clamp default is safe in a way a blind lateral is not.)

## Pillar 2 — VLM retreat-candidate selection (set-of-mark, stage 2)

- **Candidate generation (M5/grounder):** 2–4 retreat poses for
  `yield_robot` (left-rear / right-rear at the Pillar-1 backup distance,
  ± lateral variants). **Validation covers the swept path, not only the
  endpoint:** the straight backup segment and the sidestep segment are
  sampled at ≤0.1 m intervals; every sample must keep ≥ `min_distance_m`
  from all other robots and stay inside the aisle band. Candidates failing
  any sample are discarded.
- **Ranking:** surviving candidates are scored by a deterministic geometry
  metric (min clearance along the swept path, tie-break: distance from the
  transit corridor). The top-ranked candidate is the **default**.
- **Annotation:** M5 converts candidate poses to pixels via the existing
  homography and passes them in the M1 frame request; M1's annotation pass
  draws numbered markers (Ⓐ/Ⓑ/Ⓒ).
- **Prompt (stage 2):** "choose the marked retreat position that best
  clears the conflict while preserving the passage space the other robots
  need and avoiding visible obstacles or traffic; answer with the letter
  and one clause of justification." (Not "most clear space" — the
  objective is conflict clearance, not open floor.)
- **Fallback rules (strict):** invalid/absent label → the geometry-best
  valid candidate, logged `retreat=default`. **Zero valid candidates →
  the yield is not executable: grounder returns a `reroute`-or-reanalyze
  outcome to M5 instead of a yield command. The old blind lateral constant
  is never used as a fallback.**
- **Rejoin:** after release (see Pillar 3), the yielder sidesteps back by
  the negated chosen lateral before COMPLETED publishes, re-entering Nav2
  from the lane centerline (fixes the run-13 tunnel-mouth wedge).

## Pillar 3 — Ordered crossing (explicit fields, sequenced release)

- **Schema:** new explicit fields — `yield_robot: str` and
  `crossing_order: [str]` — replacing the overloaded `involved_robots`
  ordering convention. `involved_robots` remains the unordered set (backward
  compatible). Validation: `yield_robot ∈ involved_robots`;
  `crossing_order` is a permutation of `involved_robots − {yield_robot}`;
  violations → decision rejected at parse (same containment as any schema
  failure), logged.
- **Grounder (yield, N robots):** `yield_robot` yields;
  `crossing_order[0]` gets the escorted transit; `crossing_order[1:]` get
  linked waits.
- **Release chain:** robot k+1 releases when robot k's transit completes —
  escort terminal for `crossing_order[0]`, signed projected progress ≥
  clearance for later robots (per-robot odometry subscriptions reusing the
  passer-cleared machinery).
- **The yielder holds until the LAST robot in `crossing_order` clears**,
  then rejoins (sidestep-back) and publishes COMPLETED. With N=2 the
  behavior degenerates to the verified head-on flow plus rejoin.
- **Timeout semantics (changed):** a linked wait's upper bound expiring
  does **not** release the robot into an unresolved conflict. It publishes
  FAILED (detail `wait expired unresolved`) for the whole resolution
  command, and the coordination client **keeps affected robots
  suppressed** pending M5's reanalysis (suppression transfers to the
  follow-up command's ACTIVE; it does not lapse on this FAILED). M5 treats
  the FAILED as terminal and reanalyzes — error handling, not silent
  resumption.

## Pillar 4 — Actuated anomaly semantics

- **Schema:** optional `blocker_kind: "robot" | "object" | "transient"`.
  Prompt: when type is anomaly (or congestion involves a non-robot
  obstacle), classify the blocker from visible evidence.
- **Grounder mapping:** `robot` → normal strategy templates; `object` →
  `reroute` (won't clear itself); `transient` → extended `temporary_wait`
  (likely clears). Absent/invalid → strategy template as-is, logged
  `blocker=unclassified`.
- **Evaluation (paired semantic counterfactuals):** two `dynamic_anomaly`
  variants with near-identical blockage geometry — (a) a static object in
  the aisle, (b) a transient agent at the same location. Success = the
  VLM's `blocker_kind` differs correctly between the pair AND the executed
  responses diverge (reroute vs wait/reassess). This isolates *semantic*
  understanding from geometric cueing — the capability no classical
  baseline has.

## Evaluation baselines (thesis evidence)

For retreat selection (Pillar 2), compare the VLM's choices against three
policies on the same candidate sets: **fixed-left** (today's behavior),
**random-valid**, and **geometry-max-clearance** (the deterministic
ranker). Metrics: resolution success rate, time-to-resolution, and
disagreement cases where the VLM's pick beats/loses to geometry-max
(qualitative review of justifications). Decision artifacts already capture
everything needed.

## Explicitly out of scope (future work)

Rotation/roundabout strategy for dense crowding; occupancy-grid free-space
search; VLM metric magnitudes / raw coordinate output (the candidate
infrastructure is the on-ramp — densify candidates as set-of-mark pointing
matures); multi-frame temporal context for M2 (ContextVLA direction).

## Failure containment (precise claims)

- VLM outputs are restricted to system-generated discrete options
  (candidate labels, robot ids, enum values); every accepted choice is
  **geometrically revalidated at grounding time** (swept-segment checks for
  retreat; permutation checks for ordering). A schema-valid but
  geometrically-invalidated choice is replaced by the deterministic
  default and logged.
- What can still reach M4: a *valid but suboptimal* choice (e.g., the
  worse of two safe retreat sides). This is bounded by construction —
  every executable option passed the same swept-path safety checks — and
  is exactly the residual the baselines section measures.
- Degradations are logged with `*=default` markers so fallback frequency
  is measurable from decision artifacts.

## Testing

- **Unit (offline):** Pillar-1 derivations from synthetic snapshots
  (multi-robot clearance, projection math, clamp edges, missing-snapshot
  fallback); candidate generation with swept-path filtering (cases: both
  sides valid / one side blocked by a robot on the swept segment — not
  endpoint — / zero valid → reroute outcome); ranking determinism;
  label mapping + hallucinated-label → geometry-best; yield_robot /
  crossing_order validation (missing, non-member, non-permutation);
  release-chain ordering for 3- and 4-robot synthetic cases; hold-until-
  last + rejoin phase ordering; wait-timeout → FAILED + suppression
  retention; blocker_kind mapping + fallback; parser round-trips for all
  new fields.
- **E2E (host):** (1) `head_on_deadlock` regression — derived distances
  near 1.3/2.4, single cycle, rejoin works, goals reached; (2)
  `intersection_bottleneck` — 4 robots, ordered crossing, yielder holds
  until last clears, no re-collision; (3) `dynamic_anomaly` paired
  counterfactuals — object vs transient variants, divergent classified
  responses. Decision artifacts show stage-1 and stage-2 outputs +
  justifications.

## Files touched (expected)

- `reasoning/schemas/vlm_decision.schema.json` (+ a stage-2 response
  schema), `reasoning/vlm/models.py`, `output_parser.py`,
  `prompt_builder.py` (stage-1 fields + stage-2 prompt)
- `reasoning/rag/command_grounder.py` (snapshot param, derivations,
  candidate generation/validation/ranking, ordering, blocker mapping,
  no-valid-candidate reroute outcome)
- `ros2_ws/src/swarm_orchestrator/.../reasoning_pipeline.py` (two-stage
  orchestration; snapshot pass-through; candidate pixels to M1)
- `ros2_ws/src/swarm_perception/.../annotation.py` (+node plumbing) for
  candidate markers
- `ros2_ws/src/swarm_execution/.../command_bus_node.py` (sequenced release
  chain, hold-until-last, rejoin, timeout-FAILED semantics),
  `coordination_client_node.py`/`base_mission.py` (suppression retention on
  unresolved FAILED), `nav2_adapter.py` (escort heading from odom, signed
  projected progress)
- Tests mirroring each of the above.
