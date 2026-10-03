# VLM Planning Review Fixes: Plan Grammar, Metric Split, χ-Epsilon, ER-2 Calibration

**Prepared:** 2026-10-03

**Revision history:**

- Initial draft: FIX 1 (prompt v3.1 plan grammar) and FIX 2 (emission/consistency metric split) landed on `feat/v2-plan-grammar`. FIX 3 (χ-epsilon verbatim rule) is measured but NOT implemented: it is stopped for a ruling on a design-level dispatch conflict. FIX 4 ran one live ER-2 calibration episode on IB10 under prompt v3.1.

---

## Summary

Branch `feat/v2-plan-grammar`, cut from `feat/prereg-v2-composite` at
`af7cec5`. The spec is `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`
section (a0).

| Fix | Outcome |
|---|---|
| 1. Prompt v3.1 plan grammar | Landed (`13d7392`). One static, scenario-agnostic block plus a one-line gloss for every strategy token. v1/v2 pins are unchanged; the six v3 pins are re-pinned in place (pre-freeze, step-5 precedent). The block is byte-identical on head-on and junction renders (test-pinned). |
| 2. Emission/consistency split | Landed (`7bf4e89`). `emitted` now means "a parseable plan was supplied". The new `consistent: bool \| None` carries the rejection. `agreement`, `edit_distance`, provenance and oracle-order agreement are unchanged. Old artifacts score by recomputation (checked on three stored live decisions). |
| 3. χ-epsilon verbatim rule | **STOPPED for a ruling.** The measurement is done (table below). As specified, the rule reopens freeze-blocker 1: dispatch never follows the plan's recede order. With ε ≥ 0.02 m it also changes the step-7b bound-freeze outcome: bound 4 reaches full coverage. |
| 4. Live ER-2 calibration | One episode, PASS 4/4, `outcome_rank` (1, 4, 4), yielder last. **The plan shape changed.** Under v3.1, ER-2 proposed its first-ever recede legs (two `reverse`), on the E-W pair. The plan was consistent and `repaired` at exactly the frozen bound (3 edits). One apparatus re-run was used (Nav2 bringup flake). |

Suite: 63 failed / 4565 passed / 152 skipped / 3 errors, against the
clean detached baseline at `af7cec5` of 63 / 4551 / 152 / 3. The
failing-name set is identical; +14 are this branch's new tests.

---

## FIX 1 — Prompt v3.1 Plan Grammar

### Shipped block (`reasoning/vlm/prompt_builder.py::_PLAN_GRAMMAR`)

Rendered after the plan invitation and before the JSON field list:

```text
Plan actions, for "proposed_plan":
- "yield": back up, step aside, and hold until the passing robots have cleared
- "reverse": back straight out along its own lane
- "cross": proceed through in its assigned turn (the plan's list order)
- "wait": hold in place
- "reroute": take an alternative path
- "continue": proceed unchanged; not part of the resolution
A proposed plan must refine the chosen strategy; a plan that does not is ignored and the system derives the resolution instead:
- strategy "yield": exactly one "yield" leg
- strategy "temporary_wait": at least one "wait" leg
- strategy "reroute": at least one "reroute" leg
- strategy "junction_clear": at least one "reverse" or "yield" leg
- any other strategy: no constraint on the legs
```

The strategy tokens were bare in v3.0. To avoid giving any one strategy
more salience, all eight now get a gloss in the same register:

```text
- "strategy": one of
  - "none": no congestion to resolve
  - "yield": one robot (yield_robot) backs up and steps aside while the others pass
  - "reroute": a robot takes an alternative path around the blockage
  - "convoy": robots heading the same way pass through in single file, in order
  - "priority_override": the higher-priority robot passes first; the others give way
  - "temporary_wait": the involved robots hold in place until the way clears
  - "reverse": the involved robots back straight out along their own lanes
  - "junction_clear": multi-robot junction recovery: some robots first back out, then an ordered crossing
```

### Discipline and pins

- `_PLAN_GRAMMAR` is a constant outside every conditional sub-block. A
  test extracts the invitation-to-schema region from a two-robot head-on
  render (with goals and an obstacle) and from an IB10 four-robot render
  (with a plan-state block). The two regions are byte-equal, and both
  equal `_PLAN_INVITATION + "\n" + _PLAN_GRAMMAR + "\n"`.
- Rule parity: per-strategy tests check each rule line against
  `command_grounder._is_consistent` at, below and above its threshold.
  Every unlisted strategy is unconstrained.
- Agnosticism: no robot ids, compass words, scene nouns, examples or
  digits (word-level check).
- **Not stated, flagged:** the second path to "inconsistent",
  `_plan_disagrees_with_decision_fields`. A `yield` leg or cross order
  that contradicts the same answer's `yield_robot`/`crossing_order` is
  also rejected. Stating it would add a rule the user did not list, so
  it was left out for an owner call.
- The v3 template comment says any edit is a new version. Per the step-5
  precedent (v3 is not frozen until the prereg-v2 freeze), v3.1 re-pins
  in place under `prompt_version=3`. Stored artifacts carry
  `prompt_version: 3` either way, so `user_sha256` tells them apart. The
  v3.0 baseline pin was
  `22baf2df179c58fbbf1a757f2e7fe9ed435a533c434d966b272be3dcec551286`.

| Pin | v3.0 length | v3.1 length | v3.1 SHA-256 |
|---|---|---|---|
| baseline | 4661 | 5916 | `42463ce2c2610273d649dd5eca9dc61ff8bf3272023730a2feba3703130b9a4c` |
| id_desc | 4661 | 5916 | `1f37f1a6310c66d63907e6708dd5244ca844d969498e179c2ea9be73b3110a1b` |
| no_geometry | 4475 | 5730 | `53950df569eff3c5cf7d5f79c265390e571e60d60088455fd8119bf6eb713175` |
| goals_obstacles | 5064 | 6319 | `74391670baedd21204882607d147f24316588b90b296186d0be87081e9b8591d` |
| plan_state | 4943 | 6198 | `7f11e58db4827c75815d0ec07856f4911b9d48f2c471bd608154085703c45383` |
| failure_context | 5020 | 6275 | `066b774bda38da683f6efe88d623fbf2cbe01e61ea745ed7d36de00ab48dc988` |

Every cell grows by the same +1255 characters. The v1/v2 frozen pins
(`test_prompt_v1_frozen.py`, `test_prompt_builder.py`,
`test_prompt_builder_v2.py`) pass unchanged.

---

## FIX 2 — Emission/Consistency Metric Split

`reasoning/rag/plan_metrics.py::PlanDecisionMetrics`:

| Field | Before | After |
|---|---|---|
| `emitted` | parseable AND consistent (`rejection_stage` not in absent/unknown_robot/inconsistent) | parseable: `rejection_stage` not in absent/unknown_robot |
| `consistent` | — | new `bool \| None`: None when not emitted; False on `rejection_stage == "inconsistent"` (both inconsistency paths); else True, including repaired and `repair_bound_exceeded` |
| `agreement` | `emitted and vlm_verbatim` | `consistent is True and vlm_verbatim` (same values) |
| `edit_distance`, `provenance`, `rejection_stage` | — | unchanged |
| `oracle_order_agreement` | gated on old `emitted` | **gated on `consistent is True`**, so its population is unchanged. This was a deliberate choice: scoring the order of inconsistent plans would be a new metric decision, left to the owner. |

- An emitted-but-inconsistent plan still ends `m3_default` with
  `rejection_stage="inconsistent"`. `verify_and_repair_plan` is untouched.
- **Consumers:** `score_plan_decision` has no non-test consumer. No
  artifact writer or scorer surfaces `emitted`, and decision artifacts do
  not store `rejection_stage`. No writer change was needed.
- **Backward readability:** metrics are always recomputed from the
  decision plus `VerifiedPlan`. `verify_and_repair_plan` was re-run on
  the three stored live ER-2 trigger artifacts, using the IB10 geometry
  and `config/rag.yaml` params. Each gives `emitted=True, consistent=False,
  provenance=m3_default, rejection_stage=inconsistent`. The artifacts are
  `ib10_smoke/live_20261002_120337/78d93283…`,
  `ib10_smoke/episode2_20261002_125412/32ead4ee…` and
  `v2_demo/ep2_live_er2/decisions/5dfbeb07…`.
- **Spec text to amend at the next spec revision:** (a0) metric (i) still
  reads "a parseable, consistent plan was supplied". It should become
  "parseable" (emission), with consistency as its own rate.

---

## FIX 3 — χ-Epsilon Verbatim Rule (stopped for a ruling)

### Measurement

The measurement covers every IB10 run with geometry on disk: the step-6
`ib10_smoke` bundles, both step-7b reruns (session scratchpad copies),
both v2-demo episodes, and this calibration episode. χ was recomputed
with the project's own `maneuver_geometry.recede_cost`, using weights
from `config/rag.yaml` (s=1.0, t=0.5) and IB10 geometry (pocket 1.2 m).
N_f = 0 for both candidates in every snapshot. The margin is
χ(robot_3) − χ(robot_4); negative means robot_3 recedes first.

| Run | Trigger margin (m) | Settled-dwell mean (m) | Within-run spread (m) | χ order | Proposed recede order | Provenance |
|---|---|---|---|---|---|---|
| step-6 run A (mock) | +0.048 | +0.0488 | 0.003 | [r4, r3] | none (plan absent) | m3_default |
| step-6 run B (mock) | −0.003 | −0.0023 | 0.002 | [r3, r4] | [r4, r3] | vlm_verbatim (the freeze-blocker-1 hole) |
| step-6 live 1 (ER-2) | −0.094 | −0.0941 | 0.005 | [r3, r4] | none (cross + waits) | m3_default |
| step-6 episode 2 (ER-2) | −0.140 | −0.1417 | 0.001 | [r3, r4] | none (cross + waits) | m3_default |
| 7b rerun 1 (mock) | +0.008 | +0.0081 | 0.001 | [r4, r3] | [r4, r3] | vlm_verbatim |
| 7b rerun 2 (mock) | +0.031 | +0.0310 | 0.000 | [r4, r3] | [r4, r3] | vlm_verbatim |
| v2 demo ep1 (mock) | −0.044 | −0.0438 | 0.001 | [r3, r4] | [r4, r3] | repaired |
| v2 demo ep2 (ER-2) | −0.032 | −0.0317 | 0.001 | [r3, r4] | none (cross + waits) | m3_default |
| **this calibration (ER-2, v3.1)** | **0.000 (tie, broken by id)** | +0.0008 | 0.002 (+0.002 → 0.000 within the dwell) | [r3, r4] | r1/r2 (off-axis) | repaired (3) |

"Settled dwell" means jam frames in which all four robots are within
0.45 m of the centre and stationary.

There are two separate populations, and this refutes the 2026-10-03
notes entry's "snapshot-timing dependent" reading:

- **Snapshot noise (within one run):** the settled margin moves by at
  most 5 mm (sd ≤ 1.2 mm). It flips the χ order only when the settled
  margin is itself within a few millimetres of zero. Run B sits at
  −0.001 to −0.003. This calibration run sits at +0.002 → 0.000: a real
  within-run flip, resolved by the robot-id tie-break.
- **Jam-formation asymmetry (between runs):** settled margins are +0.049,
  −0.002, −0.094, −0.142, +0.008, +0.031, −0.044, −0.032 and 0.000, in a
  scene that is symmetric by design (equal spawn radii). The cross-run
  order "flips" (7b [r4, r3] vs demo [r3, r4]) come from here, not from
  snapshot timing.
- **No genuine ranking difference was ever observed** in formed-jam IB10
  geometry. The nearest structural one is one follower (t·N_f = 0.5 m of
  χ). The later episode-2 snapshots (+0.185, −0.934) are disordered
  secondary-conflict scenes, not formed-jam recede decisions.

There is therefore no clean gap inside the formed-jam data. The two
defensible readings:

| ε | Absorbs | Does not absorb | Headroom |
|---|---|---|---|
| ≈ 0.01 m (2× max within-run spread) | pure snapshot noise (run B, this calibration) | between-run asymmetry (7b vs demo, 0.03–0.05) | ~0.5 m below one follower |
| ≈ 0.15 m | every observed formed-jam margin (max 0.142) | nothing observed | 8 mm above the largest observed; still far below 0.5 |

### Why it is stopped: dispatch never follows the plan's recede order

`InProcessPipeline.run` (`reasoning_pipeline.py` ~901–969) grounds
`grounded` and `ground_junction_clear_phases(result, …)` from the RAW
decision, before `verify_and_repair_plan` runs. Nothing feeds
`verified.legs` order into dispatch, and the recede phases always go out
in `rank_recede_candidates` order. `junction_clear_plan_matches_dispatch`
compares per-robot actions only, never order. So a within-ε plan that
verifies `vlm_verbatim` in the opposite order is dispatched in χ order
and reported as matching. That is exactly freeze-blocker 1 (run B: margin
−0.003, proposed [r4, r3], dispatched [r3, r4], `vlm_verbatim`), which
step 7a closed. Any ε ≥ 0.003 reopens it on run B itself. Options for
the coordinator:

- **(a) Dispatch honors the plan's recede order within ε.** The verified
  order is passed into `ground_junction_clear_phases`, and phase 0 is
  re-grounded after verification. This changes which robot gets the
  rank-0 pocket and the stagger, which robot is the release lead
  (`ranked[0]`), and the yielder-behind-receders chain. All of that is
  frozen step-7 machinery (IB10 scoring frozen at 11 criteria).
- **(b) Verification-only ε, with the gap made visible.** Add an
  order-aware `dispatch_matches_plan`, or a separate `order_equivalent`
  flag, so a within-ε verbatim plan dispatched in χ order is recorded,
  not hidden.

### Side effects measured offline (scratch monkeypatch of the audit, not committed)

- **Sweep fixture:** `IB10_STANDOFF`'s margin is 0.019 (0.942 vs 0.923).
  Any ε > 0.019 turns `recede_order_swapped` into `vlm_verbatim`. The
  `wrong_recede_order` category then loses its only case, and the unit
  tests pinning the recede-order audit on that fixture flip too.
- **Bound freeze changes:**

  | ε | m3_default (of 14 repairable), bounds 1 / 2 / 3 / 4 |
  |---|---|
  | 0 (shipped) | 11 / 7 / 3 / 2 |
  | ≥ 0.02 | 9 / 5 / 3 / **0** |

  With ε, the two depth-5 cases (`recede_pair_full_axis_swap`,
  `combined_wrong_pair_and_order`) drop to depth 4. Under the step-7b
  ruling (ii) procedure ("smallest full-coverage bound ≤ 4, else 3"),
  this would freeze **bound 4, not 3**. The m3_default tail at bound 3
  is unchanged: `missing_both_recede_candidates`,
  `recede_pair_full_axis_swap`, `combined_wrong_pair_and_order`.
- **This episode's plan:** its provenance at bound 3 depends on the
  ε question. It was repaired with exactly 3 edits because the χ tie
  broke toward robot_3. Shifting robot_3 inward by 0.01 m (χ order
  [r4, r3]) makes the same plan `m3_default` (`repair_bound_exceeded`)
  without ε, and `repaired` (3) with ε = 0.15.

---

## FIX 4 — Live ER-2 Calibration Episode (IB10, prompt v3.1)

### Apparatus

The configuration was the exact v2-demo ep2 setup:

- Overlay `/home/ubuntu/v2_demo_runs/overlays/ep2_orchestrator.yaml`
  (md5 `d1e11073…`; plan channel on, `keep_debug_frames` +
  `keep_raw_frames`, `id_asc`).
- `BACKEND=gemini`: `fc_launch` rewrites the overlay's
  `reasoning_backend_id: openai` and restores it on exit. The served
  model was confirmed as `gemini-robotics-er-2-preview`.
- Seed 42, `REC_SEC=1400` / `SIM_SEC=1800` as in ep2, so the YAML
  `duration_sec: 300` governs at about 0.27 RTF (about 25 min wall).
  `RECORD=0`.

Run steps:

- **Deploy:** the VM tree was md5-manifest-verified against `af7cec5`
  first. The only mismatches were the docs file and the known pristine
  `orchestrator.yaml`. Then `prompt_builder.py` and `plan_metrics.py`
  were copied, touched and md5-checked on both the host and the
  container's live-mounted `/ws`. An in-container render confirmed
  `_PLAN_GRAMMAR` in a v3 prompt (block sha256 prefix `a57ee860…`,
  matching local).
- **Preflight:** one minimal real call returned
  `served_model=gemini-robotics-er-2-preview`, parsed OK, 1123 tokens.
- **Attempt 1:** apparatus failure. Robot_3's Nav2 lifecycle aborted
  (`bt_navigator/get_state service client: async_send_request failed`),
  and M5 never started, so there was zero API spend. Two traps followed:
  - The driver's `GATE OK` fired anyway, because `logs saved to` is
    printed on the failure path. The gate does not prove a run happened.
  - That Isaac outlived cleanup by more than 12 min (it simulates out its
    300 sim-s at 0.27 RTF). The re-run's own 420 s guard refused to
    launch. The leftover Isaac was killed by PID, and the GPU was
    confirmed idle (0 %, 171 MiB).
- **Re-run (the one allowed):** `fc_run_20261003_154833`, 15:48–16:13
  UTC.
- **After the run:**
  - `RESTORE OK`: `orchestrator.yaml` src = installed =
    `1f656533a30a35882d57d0d64a57bd0d`, `rag.yaml`
    `e18c723cff9cada3f320d564c2ecee5a`.
  - The two reasoning files were restored to their `af7cec5` versions
    (copied, touched, container md5 verified).
  - The full manifest re-check shows the same two known mismatches as
    before the run.
  - No Isaac process remained.
- **Evidence:** every decision artifact's `prompt.user_prompt` contains
  `_PLAN_GRAMMAR` byte-for-byte. The trigger's `user_sha256` is
  `9957de3f…`. The scan for secrets and base64 images was clean.

Run bundle (gitignored):
`data/logs/vm_runs/plan_grammar_cal/cal_ep1_rerun/` (plus the failed
attempt and the refused-launch directory beside it, and the
`ib10_score.json` scorer output).

### The trigger decision, verbatim (`aec068b5…`, sim 30.17 s, 4677 ms)

```json
{
  "reasoning": "Four robots are stopped at a 4-way intersection in extremely close proximity, facing each other head-on in both the horizontal and vertical directions. This represents a multi-robot deadlock that requires a junction clearing strategy to resolve.",
  "congestion_detected": true,
  "type": "deadlock",
  "involved_robots": ["robot_1", "robot_2", "robot_3", "robot_4"],
  "root_cause": "Four robots arrived at the center of the intersection simultaneously and blocked one another's paths.",
  "strategy": "junction_clear",
  "justification": "A junction clear strategy is needed to back two of the robots out of the intersection so that the other two can proceed before the first two return to cross.",
  "yield_robot": null,
  "blocker_kind": "robot",
  "crossing_order": ["robot_3", "robot_4", "robot_1", "robot_2"],
  "proposed_plan": [
    {"robot_id": "robot_1", "action": "reverse"},
    {"robot_id": "robot_2", "action": "reverse"},
    {"robot_id": "robot_3", "action": "cross"},
    {"robot_id": "robot_4", "action": "cross"}
  ]
}
```

### Verification and outcome

- **Consistency:** PASS. The plan has two `reverse` legs, and
  `junction_clear` needs ≥ 1 `reverse` or `yield`. Metrics:
  `emitted=True, consistent=True, agreement=False, edit_distance=3`.
- **Provenance:** `repaired`, 3 edits, exactly the frozen bound:
  1. `swap` robot_1 ↔ robot_3: robot_1 holds a `reverse` but is not a
     structural recede candidate.
  2. `swap` robot_2 ↔ robot_4: same reason.
  3. `substitute` robot_1 `cross` → `yield`: there was no preceding yield
     leg to release a cross.

  The executed legs were robot_3 `reverse`, robot_4 `reverse`, robot_1
  `yield`, robot_2 `cross`. `dispatch_matches_plan=true`. χ tied at
  0.939/0.939, so the order broke by id to [r3, r4].
- **Dispatch:** recede robot_3, recede robot_4, cross (gate admits robot_2
  past robot_1, released by clearance at sim 94.5), then release (lead
  robot_3, robot_4 released at 151.6, yielder robot_1 last at 184.1).
- **Outcome (`coverage_scene_scores.py ib10`):** formed jam valid (onset
  27.6 s); phase `resolved` (ordinal 4); 4/4 arrived and
  position-verified (robot_2 at 73.9 s, robot_3 134.1, robot_4 168.8,
  robot_1 201.0 after t0); `inside_first` and `yielder_last` true; in
  band; max STALE streak 1 row; `outcome_rank` (1, 4, 4). Oracle:
  `proposed_pair_correct=false`, `executed_pair_correct=true`,
  `executed_order_correct=true`.
- **Re-checks:** four later re-checks (sim 188.5–204.8, plan-state block
  showing every leg `done`) all answered `congestion_detected=false` with
  no plan, so no replan and no hold.

### Read: did the plan shape change?

**Yes, in the asked-for direction.** In the three previous live ER-2
trigger decisions under v3.0, every plan was one `cross` plus three
`wait` legs, with zero recede legs, and all three were inconsistent →
`m3_default`. Under v3.1 the model emitted two `reverse` legs and an
ordered crossing for the rest. That is the composite's shape, and for the
first time it passed the consistency rule.

What did not change: it picked the **E-W pair** (robot_1/robot_2, the
registered yield axis) as the receders, the axis-mirror of the designed
N-S recede set. Its justification ("…before the first two return to
cross") describes a mirror-image composite that the one-leg-per-robot
vocabulary cannot express, which is why the repair needed two
role-swaps. Whether "wrong axis" is a model error or a property of the
oracle's geometry-fixed recede set is a scenario question, not settled
here.

Caveats: this is n = 1, temperature unsupported (0.6 ignored by the
Interactions API), and a single prompt change. The shape change is
**suggestive, not attributable**.

---

## Open Items for the Coordinator

1. FIX 3 ruling: option (a) or (b) above, and which ε reading (≈ 0.01 or
   ≈ 0.15) if any. Note the bound-4 consequence for the step-7b freeze
   procedure.
2. Whether the grammar block should also state the second inconsistency
   path (plan vs the decision's own `yield_robot`/`crossing_order`).
3. Whether oracle-order agreement should be scored on emitted-but-
   inconsistent plans (currently not, so its population is unchanged).
4. Spec (a0) metric (i) wording, to match the split.
5. The IB10 recede-set convention vs ER-2's E-W-axis proposal.
6. Apparatus: `GATE OK` is not proof of a run (it fires on a Nav2-abort
   cleanup). A failed early run leaves Isaac alive for its full 300 sim-s
   (more than 12 min), longer than the 231–356 s figure, so a re-run
   needs a PID kill or a longer wait.
7. The `convoy` gloss ("robots heading the same way pass through in
   single file, in order") is broader than what M3 can ground.
   `resolve_strategy_alias` maps `convoy` only when there is a unique
   counter-flow robot that gives way (3+ involved). A pure same-direction
   queue, which is B1's shape and where the guidance points to
   `temporary_wait`/`yield`, falls through to `strategy=unsupported`.
   Suggested wording: "…pass through in single file, in order, while an
   opposing robot gives way". Not edited here: that would re-pin v3.1
   and orphan this calibration run's `user_sha256` (`9957de3f…`).

Evidence notes:

- The step-6 run A/B, both 7b reruns and v2-demo ep1 are mock-backend
  runs (`reasoner_config_effective.backend_id: mock`). Their proposed
  plans are scripted fixtures, so run B's [r4, r3] order was written by
  a fixture, not a model.
- The 7b bundles are not under `ib10_smoke`. Local copies exist only in
  the earlier session's scratchpad (`…/scratchpad/step7b/ib10_7b_*`);
  the originals are on the VM at `/home/ubuntu/step7b_runs/`.
