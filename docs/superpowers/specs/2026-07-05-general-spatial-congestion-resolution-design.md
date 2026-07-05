# General Spatial Congestion Resolution — Design

**Date:** 2026-07-05
**Status:** Approved in dialogue (user, 2026-07-05); pillar structure and
literature grounding reviewed conversationally before writing.
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
   problems (FCFS/auction/token-sequential replanning).

Literature anchors (read in full or via prior survey): SocialNav-SUB
(arXiv 2509.08757 — spatial relations are frontier VLMs' weakest axis,
PA≈0.55; set-of-mark + BEV prompting is the effective mitigation), VLM
frontier assignment (2310.07937 — VLM selects among system-generated,
image-annotated candidates; never emits coordinates), NOD corridor passage
(2504.20947 — who-commits/who-yields is the social decision that matters),
congestion-metric replanning (2202.11334 — token-based sequential
replanning), MIT REALM 2404.06413 + LLMDR 2503.00717 (foundation-model
arbiter over safe low-level control). Design principle adopted from these:
**the VLM selects among system-proposed, pre-verified, visually-annotated
discrete options and orders robots; it never generates metric poses.**

## Pillar 1 — Derived maneuver distances

`ground_reasoner_result` gains a `snapshot` parameter (the `SceneSnapshot`
already available at the `reasoning_pipeline.py` grounding call site).

- **Backup distance** = the reverse needed so the yielder's separation from
  the nearest *other involved robot* reaches pass-clearance
  (`2*min_distance_m + margin`), computed from actual poses; clamped to
  [0.5, 2.0] m.
- **Escort distance** = separation-at-hold + yielder clearance + margin,
  clamped to [1.0, 3.5] m; `passer_clear_m` = escort distance (same
  semantics as today).
- **Escort heading**: M4 uses the passer's own heading at escort start
  (from its odom), not yaw 0. The passer was navigating toward its goal
  when stopped, so its heading is goal-ward in every scenario.
- **Lateral magnitude** stays a config default (0.35 m) with per-scenario
  override. Map-derived lateral clearance is explicit future work — this
  design verifies against robot poses, it does not search the map.
- **Fallback:** `snapshot=None` (or malformed) → today's constants,
  logged as `distances=default`.

## Pillar 2 — VLM retreat-candidate selection (set-of-mark)

- The grounder computes 2–4 candidate retreat poses for the prospective
  yielder (left-rear / right-rear at the derived backup distance, ±
  variants), each pre-verified against the scene snapshot (no other robot
  within `min_distance_m`; within the aisle band). Candidates are
  robot-frame maneuvers rendered as world poses for annotation only.
- M1's annotation pass draws the candidates on the overhead frame as
  numbered markers (Ⓐ/Ⓑ/Ⓒ) when M5 requests an analysis frame (new field
  in the M5→M1 request path carrying candidate pixel positions; M5
  computes pixels via the existing homography).
- Schema: `vlm_decision` gains optional `"retreat_choice": "A"|"B"|"C"|"D"`.
  Prompt: when strategy is yield, pick the marked retreat spot with the
  most clear space, judged from the image; justify in one clause.
- Grounder maps the chosen label back to its signed lateral; absent or
  invalid label → first valid candidate (deterministic default), logged
  as `retreat=default`. A VLM hallucinating an unmarked label is thereby
  detectable and inert — this containment is the reason for
  selection-over-coordinates (SocialNav-SUB weakness + wrong-but-plausible
  failure mode of raw points).
- **Rejoin:** the yield's completion adds a final sidestep-back (negated
  chosen lateral) before COMPLETED publishes, so the yielder re-enters
  Nav2 from the lane centerline (fixes the run-13 tunnel-mouth wedge).

## Pillar 3 — Ordered crossing (sequenced release)

- Prompt: `involved_robots` is defined as the **crossing order** — first
  element yields, remainder ordered by who should proceed first.
- Grounder (yield strategy, N robots): `[0]` yields; `[1]` gets the
  escorted-transit wait; `[2:]` get linked waits with the same generous
  upper bound.
- M4: linked waits release **one robot per clearance event**: robot k+1
  releases when robot k's transit completes (escort terminal for `[1]`;
  odometry displacement ≥ clearance for later robots, reusing the
  passer-cleared subscription machinery keyed per robot).
- Two-robot case degenerates exactly to today's verified behavior (no
  `[2:]`), making head-on the regression baseline.

## Pillar 4 — Actuated anomaly semantics

- Schema: optional `"blocker_kind": "robot" | "object" | "transient"`.
  Prompt: when type is anomaly (or congestion involves a non-robot
  obstacle), classify what is blocking, from the image: another robot /
  a static object (fallen box, pallet) / a transient agent (person,
  temporary) — justify from visible evidence.
- Grounder mapping: `robot` → normal strategy templates; `object` →
  `reroute` (blockage will not clear itself); `transient` →
  `temporary_wait` with extended duration (it will likely clear).
  Absent/invalid → current behavior (strategy template as-is), logged
  `blocker=unclassified`.
- This converts the VLM's headline capability — knowing *what things are* —
  from logged prose into behavior, and is exercised by the existing
  `dynamic_anomaly.yaml` scenario (timed obstacle spawns mid-run).

## Explicitly out of scope (future work)

Rotation/roundabout strategy for dense crowding (enum gap identified in
the June literature survey); occupancy-grid free-space search; VLM metric
magnitudes / raw coordinate output (revisit as set-of-mark pointing
matures — the candidate-marker infrastructure is the on-ramp, densifying
candidates converges toward it with validation always in the loop);
multi-frame temporal context for M2 (ContextVLA direction).

## Failure containment (uniform rule)

Every new VLM field and every derived quantity is advisory-with-fallback:
missing/invalid input degrades to the previously verified behavior and is
logged with a `*=default` marker so degradation is measurable in decision
artifacts. No new failure mode reaches M4's primitives.

## Testing

- **Unit (offline):** distance derivations from synthetic snapshots
  (including clamp edges and missing-snapshot fallback); candidate
  generation + pre-verification filtering; label→lateral mapping +
  hallucinated-label fallback; N-robot action fan-out and one-per-event
  release chain (3- and 4-robot synthetic cases); blocker_kind mapping +
  fallback; rejoin phase ordering; schema/parser acceptance of all new
  optional fields (absent, valid, invalid).
- **E2E (host):** (1) `head_on_deadlock` regression — derived distances
  land near the proven 1.3/2.4, single cycle, goals reached; (2)
  `intersection_bottleneck` — 4 robots, ordered crossing, no re-collision
  on release; (3) `dynamic_anomaly` — blocker classified, mapped response
  executed. Decision artifacts must show the VLM's choices + justifications
  for retreat_choice, crossing order, and blocker_kind (thesis evidence).

## Files touched (expected)

- `reasoning/schemas/vlm_decision.schema.json`, `reasoning/vlm/models.py`,
  `output_parser.py`, `prompt_builder.py` (fields + prompt)
- `reasoning/rag/command_grounder.py` (snapshot param, derivations,
  candidates, ordering, blocker mapping)
- `ros2_ws/src/swarm_orchestrator/.../reasoning_pipeline.py` (pass
  snapshot; carry candidate annotations to M1 request)
- `ros2_ws/src/swarm_perception/.../annotation.py` (+node plumbing) for
  candidate markers
- `ros2_ws/src/swarm_execution/.../command_bus_node.py` (sequenced
  release, rejoin phase), `nav2_adapter.py` (escort heading from odom)
- Tests mirroring each of the above.
