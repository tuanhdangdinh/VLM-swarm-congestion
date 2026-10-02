# IB10 `junction_clear` Composite Smoke (v2 build-order step 6)

**Prepared:** 2026-10-02

**Revision history:**

- Initial draft: local work (goal-table fields, loudness guard, repair-bound
  sweep) complete and committed; VM sections (mock smoke, live episode,
  STALE instrumentation, restore) in progress, drafted as stubs so the local
  findings are durable independent of the VM session's outcome.

**commit:** branch `feat/v2-ib10-smoke`, worktree
`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v2-ib10`, branched from
`feat/prereg-v2-composite` at `955b962`.

---

## Scope

Executes `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` build-order
step 6: the IB10 `junction_clear` composite smoke (mock, then one live
episode) and sizing the repair bound. Prerequisite reading: step-5's landing
(`docs/implementation_notes.md` 2026-10-02 entries), the step-6 STALE gate
resolution (same spec, build order item 6), and
`docs/reports/2026-10-01-robot1-stale-rootcause.md`.

Base-branch divergence check (before any edit): `feat/prereg-v2-composite`
(`955b962`) differs from `fix/deadlock-collision-resolution` in
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` by exactly one hunk
(the step-9 loop-map phase-1 gate entry, irrelevant to step 6); every step-6
ruling this task reads (STALE gate resolution, plan lifecycle, repair-
semantics) is byte-identical on both branches. Step-5's `junction_clear`
machinery (`ground_junction_clear_phases`, `junction_phase_queue.py`,
`plan_tracker.py` wiring) is committed on the branch point, not pending.

---

## Step 1-2: IB10 goal-table fields + loudness guard

**PASS.**

- `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`'s
  `intersection_bottleneck` goal-table comment now documents the two
  required fields (`junction_recede_offset_m: 1.2`,
  `junction_backup_clearance_m: 1.1`) alongside the existing T1 entry,
  following the B3 goal-table precedent (Rev 22 note at the `convoy_
  counterflow` row), with the correct unsolved/solved-row numbers (backup
  1.151 m / retreat_x -1.37 m unsolved vs. backup 0.799 m / park |x| 1.018 m
  / escort 1.998 m solved -- the composite's cross phase is an E-W yield,
  not the N-S two-robot yield's 1.44 m/2.22 m numbers an earlier draft of
  this comment mistakenly cited).
- Verified through the REAL config-load path, not a hand-built dict: the
  exact orchestrator.yaml this task will deploy for IB10 (initial_tasks x4,
  `shadow_classical_zones`, junction `corridor`+`arms`, both junction
  fields, `plan_channel_enabled: true`) loads through `swarm_orchestrator.
  models.load_config` and grounds `junction_clear` to backup 0.799 m,
  retreat_x -1.018 m, escort 1.998 m, with no loudness-guard tag -- the
  solved row, end to end.
- **Loudness guard**, `reasoning/rag/command_grounder.py`: new
  `_junction_geometry_missing_fields`/`_shipped_unsolved_tag` helpers emit
  `junction_geometry=shipped_unsolved:missing=<field,field,...>`,
  independent of WHY `ranked` came back empty (a coordinator-review
  correction to the first draft, which only tagged the backup-clearance-
  missing case and let the pre-existing `junction_clear=fallback:
  no_candidates` tag -- which also fires for an unrelated reason, no
  cross-axis `arms` declared -- stand in for "a field is missing"). Applied
  at every site a caller could read: the top-level `no_candidates` fallback
  command, every recede phase, the cross phase, and the phase-sequence
  fallback command. Registered in `DEGRADATION_TAGS` (provenance-only,
  `None` cause) so `degradation_cause` does not raise on it.
- Tests: `tests/unit/test_junction_clear_grounding.py`
  `TestShippedUnsolvedLoudnessGuard` (6 tests: both missing, J2-alone,
  offset-alone, offset-alone-for-an-unrelated-structural-reason [no tag],
  both present [no tag, solved row], additive-only numeric equivalence);
  `tests/unit/test_intersection_bottleneck_scenario.py
  ::TestJunctionGeometry::test_goal_table_declares_the_step_6_junction_
  clear_fields` (goal-table substring pin, the `test_goal_table_declares_
  the_junction_and_every_arm` precedent).
- Commits: `3c56cad` (fields + first guard draft), `07f1b5c` (widened guard
  + fixed comment numbers + smoke mocks, below).

---

## Step 4: repair-bound sizing sweep (frozen before any live smoke)

**Script:** `scripts/junction_clear_repair_bound_sweep.py` (local, no VM
dependency; run with `PYTHONPATH=. python3 scripts/junction_clear_repair_
bound_sweep.py`). 17 deterministic cases across `wrong_recede_pair`,
`wrong_order`, `missing_legs`, `inconsistent_strategy`, `combined`, plus
absent/correct-verbatim controls, run through the REAL `verify_and_repair_
plan` engine on the IB10 standoff snapshot, both J2 fields declared,
`yield_feasibility_mode="off"` -- matching IB10's deployed `grounding_
yield_feasibility: "off"` (the orchestrator.yaml default, unchanged for this
scenario).

### Minimal-repair-depth distribution

| depth | cases | which |
|---|---|---|
| 0, `vlm_verbatim` (no repair needed) | 8 | 3 `wrong_recede_pair`, 3 of 4 `missing_legs`, 1 `combined`, 1 control |
| 0, rejected before repair (`inconsistent`/`absent`) | 4 | 3 `inconsistent_strategy`, `plan_absent` |
| 1 | 2 | `order_yield_first_only`, `combined_missing_leg_and_wrong_order` |
| 2 | 3 | `order_fully_reversed`, `order_cross_before_recede`, `missing_yielder` |
| exceeds probe bound (10) | 0 | -- |

Only 5 of 17 cases actually exercise the BFS repair search at all; the rest
either need no repair (`vlm_verbatim` -- see the finding below for why that
is itself notable) or are rejected before repair is ever attempted
(`inconsistent`/`absent`).

### % falling to `m3_default` per bound

All 17 cases:

| `max_repair_edits` | m3_default |
|---|---|
| 1 | 7/17 (41%) |
| 2 | 4/17 (24%) |
| 3 | 4/17 (24%) |

Repairable cases only (excludes `inconsistent_strategy`/`plan_absent`,
which are `m3_default` by contract, not by repair distance):

| `max_repair_edits` | m3_default |
|---|---|
| 1 | 3/13 (23%) |
| 2 | 0/13 (0%) |
| 3 | 0/13 (0%) |

### Recommendation

**bound = 2, conditionally.** Every repairable case in this sweep clears at
depth <= 2; depth 3 offers no additional benefit on this corpus (0% -> 0%).
This matches the shipped default (`PlanRepairParams.max_repair_edits = 2`)
exactly -- this sweep is a confirmation, not a change, and per the task's
instruction the default is **not** modified; the live episode (below) runs
on the current default.

**The condition, and why it is a freeze-blocking finding, not a footnote:**
the sweep also surfaces that the most *plausible* defect class --
`wrong_recede_pair` (the VLM names the wrong two robots as the recede set,
e.g. the yield-axis pair instead of the structural cross-axis candidates)
-- never reaches repair at all. All three `wrong_recede_pair` cases, and
3 of 4 `missing_legs` cases, verify as `vlm_verbatim` under the shipped
`yield_feasibility_mode="off"`: `_plan_problems`'s ordering audit only
checks relative POSITION of recede-vs-yield-axis legs, never recede-set
MEMBERSHIP, and `"off"` skips the room/obstacle feasibility check entirely.
Confirmed concretely (not just by code reading): a wrong-recede-pair plan
(`robot_1`/`robot_2` named `reverse`, the structural cross-axis pair
`robot_3`/`robot_4` named `yield`/`cross`) verifies `vlm_verbatim` via
`verify_and_repair_plan` -- but `junction_clear` dispatch always runs M3's
own chi-ranked phases (`ground_junction_clear_phases`) regardless of what
the plan said, so the actual M4 dispatch (`robot_4` reverse, `robot_3`
reverse, `robot_1` yield) has nothing in common with the "verbatim" plan.
`junction_clear_plan_matches_dispatch` correctly returns `False` on this
case -- but plan-quality metrics (ii) plan agreement rate and (iv) executed-
plan provenance, read from `verify_and_repair_plan`'s own output as (a0)
specifies, would score this as a clean VLM success. **This sweep cannot
size a bound against the defect class it cannot even detect**; the bound
recommendation above covers ordering/missing-leg defects only. Flagged for
the coordinator before freeze: either the (a0) consistency/feasibility
audit needs a `junction_clear`-specific recede-set-membership check, or
metrics (ii)/(iv) must be read alongside `dispatch_matches_plan`/the
oracle-order metric for this strategy specifically, never alone. Not fixed
here -- out of this task's scope (the engine is shared, v2-wide machinery;
amending it is a separate, scoped change the coordinator should decide,
not a unilateral edit during a sizing sweep).

Commit: `6e65ab1`.

---

## Step 3: mock composite smoke (VM)

**VM state at deploy:** standing host `vgu-vgu-thule-base-isaac-workstation-vm`
confirmed idle (`pgrep -f run_simulation` empty, no `ros2`/orchestrator/
perception/Nav2 process in `vgu_ros`, GPU 0%/171 MiB, container up 2h from
an apparently-unrelated prior task's clean exit earlier the same morning).
Pre-deploy md5 of `orchestrator.yaml`/`rag.yaml` (source + installed, host
and container) matched the standing convention exactly
(`1f656533a30a35882d57d0d64a57bd0d` / `e18c723cff9cada3f320d564c2ecee5a`),
backed up verbatim to `/tmp/ib10_pristine/` before any edit. **Correction
to this report's own earlier assumption:** the VM tree predates step 5
entirely (`grep -c ground_junction_clear_phases` on the VM's pre-deploy
`command_grounder.py` returned 0) -- the restore target after this task is
the standing `1f656533`/`e18c723` pair (the shared-VM convention every
other task's driver script restores to), not this branch's own committed
md5; this branch's `orchestrator.yaml` differs from `1f656533` by design
(the step-6 comment addition), which is expected drift, not a pristine-
state violation. Deployed via `git archive HEAD` (`bfc3000`) extracted over
the VM tree (USD/map build products untouched -- not git-tracked -- per
the task's "USD already built" note, confirmed present), the IB10-specific
`orchestrator.yaml` (initial_tasks x4, `shadow_classical_zones`, junction
`corridor`+`arms`, both J2 fields, `plan_channel_enabled: true` --
identical to the file this report's Step 1-2 section verified through
`load_config` locally) copied in over the archived shipped copy, and
`swarm_orchestrator`/`swarm_simulation` rebuilt via colcon. **Deploy check
passed**: installed config md5 matched the deployed source exactly
(`010805192c9e33b4b29a27fd7ecd8ea9`, both host and container copies), and
`reasoning/`/`config/mock_decisions/` (live-mounted at `/ws`, not colcon-
built) confirmed visible inside the container with the new code/mocks
present.

Mock decision files prepared and verified locally before any VM time is
spent (per the standing rule and specifically re-confirmed by review):

- `config/mock_decisions/intersection_junction_clear_m3_default_once.json`
  (run A: one `none` skip -- sized from the established IB9 20260929_084557
  smoke's own one-skip pattern, `config/mock_decisions/intersection_skip_
  then_yield_once.json`'s precedent -- then `junction_clear` with the
  strategy token only, no `proposed_plan`; then `none`). Verified locally:
  `verify_and_repair_plan` returns `provenance="m3_default"`, `rejection_
  reason="plan absent"`.
- `config/mock_decisions/intersection_junction_clear_vlm_verbatim_once.json`
  (run B: same one-skip pattern, then `junction_clear` with a `proposed_
  plan` naming the chi recede pair in chi order -- `robot_4` [D_SPACE
  0.923] before `robot_3` [D_SPACE 0.942] -- then the yield-axis `yield`/
  `cross` pair; then `none`). Verified locally: `verify_and_repair_plan`
  returns `provenance="vlm_verbatim"`, `edits=[]`, under the exact deployed
  geometry (both J2 fields, derived mode).
- Parse/shape tests: `tests/unit/test_intersection_bottleneck_scenario.py
  ::TestJunctionClearMockDecisions` (5 tests).

### Run A results (`m3_default`, run `20261002_111456`)

| Criterion | Result |
|---|---|
| Jam forms first | **PASS** -- all four robots within 0.15 m of the IB10 standoff reference positions by sim_time 26.5 s (GT `ground_truth.jsonl`); global min pairwise distance 0.133 m at 47.1 s |
| Full phase sequence executes (recede robot_4, then robot_3, staggered sequential; yield phase; done) | **PASS** -- `phase advance ... phase_reached=recede done=False` (robot_4), then `phase_reached=cross done=False` (robot_3), then `phase_reached=resolved done=True` (cross phase); never two recede legs in one command (confirmed from the dispatch lines: each recede command addresses exactly one active `reverse` robot) |
| Provenance correct | **PASS** -- decision artifact `5e42a221d4dc488c9632957e21a2acee.json`: `plan.provenance="m3_default"`, `plan.rejection_reason="plan absent"` (no `proposed_plan` in run A's mock, as designed), `plan.dispatch_matches_plan=true`, legs `[robot_4 reverse, robot_3 reverse, robot_1 yield, robot_2 cross]` -- the exact chi order |
| Deploy check (no `shipped_unsolved` tag) | **PASS** -- `grounding_degradations: ["junction_clear=recede"]` only, confirming both J2 fields reached the installed config |
| Ordered crossing (yielder re-enters last) | **PASS for the phase itself** -- the cross phase's own command grounded `robot_1` yield + `robot_2` cross per the solved row; see the FAIL below for what happens after |
| 4/4 position-verified arrivals | **FAIL within this run's window** -- at scenario end (sim_time 300 s), only `robot_2` arrived (`distance_to_goal_m=0.104`); `robot_1`/`robot_3`/`robot_4` frozen (`speed_mps=0.000`) from sim_time ~120 s onward, `min_pairwise_distance_m` pinned at 0.398 m. See the correction below: this is the mock script's finite length, not a stable architectural deadlock -- M5 keeps re-triggering, the mock just has nothing new left to say. |

**Root-cause finding, corrected after the live episode below surfaced the full picture (do not read this paragraph without that correction):** the composite's own phase sequence has no scope over what happens after `done=True`. M5's `junction_phase_queue` releases every held recede candidate back to its **original base-mission goal** the moment the cross phase resolves (`resume base mission robot=robot_4 goal=(0.0, -1.75)` / `robot=robot_3 goal=(0.0, 1.75)` in `fc_20261002_111456_m4.log`) -- robot_3 and robot_4 parked on OPPOSITE sides of the junction during their staggered recede and are released toward each other's original goals on the opposite arm, a fresh N-S encounter the `junction_clear` contract never orders. The scene log shows M5's congestion detector repeatedly noticing this and re-triggering a NEW analysis for the stuck robots -- 8 separate `starting analysis` calls for `['robot_1','robot_3','robot_4']`/subsets between sim_time ~230 s and run end (`request=8c60a56c...` through `request=37f2a5ab...`), not a one-time suppression. **The real cause the first pass of this report missed**: `MockBackend` (`reasoning/vlm/mock_backend.py`) replays `VGU_MOCK_DECISION_FILE`'s scripted array in order and **holds the LAST entry forever once exhausted** -- run A's 3-entry script ends on `none` (congestion_detected=false), so every one of those 8 re-triggers gets answered "no congestion" and nothing is ever dispatched for the stuck trio. This is a property of the finite mock script, not of M5's retry/cooldown machinery, which the live episode (Step 5 below) demonstrates DOES eventually resolve the identical secondary conflict once a backend that always answers something is in the loop. **Reported as a result, re-scoped by the live run**: the composite's own job (recede + yield + cross, phase-by-phase, provenance-correct, solved-row numbers) is fully verified working; the post-resolution base-mission release creates a genuine secondary conflict outside the composite's own scope, M5's detector does keep retrying it (not a suppression bug), and whether it resolves depends on the backend actually answering it -- which a finite scripted mock, by construction, cannot do indefinitely.

### STALE instrumentation (run A)

Per-robot streaks over the M5 scene log (`m5_scene/fbe42f6dee3b40b5b6dcf2f5540f26c2.jsonl`, 370 logged cycles), collapsed to DISTINCT M1 frame stamps first (M5's own cycle rate re-logs one unchanged M1 frame several times while M1 itself is between publishes, which inflates a naive row-count streak 15x without a single additional stale frame actually occurring -- confirmed by inspection: `robot_4`'s raw 15-row "streak" is one single frame at stamp 72.133 s, re-logged 15 times):

| Robot | Distinct-frame STALE events | Longest streak (distinct frames) | Window |
|---|---|---|---|
| robot_1 | 1 | 1 | t=6.0 s (pre-departure bring-up) |
| robot_2 | 0 | 0 | -- |
| robot_3 | 0 | 0 | -- |
| robot_4 | 1 | 1 | t=72.1 s (during its recede-pocket dwell) |

Neither event is a streak (both are single isolated frames) and neither coincides with a scoring-relevant window: robot_1's is pre-trigger bring-up (never a scored dwell), robot_4's is mid-recede-dwell under the stale-tolerant `ArrivalGate` (costs no credit per the resolved gate's own finding). Both are consistent with the established background noise floor (`docs/reports/2026-10-01-robot1-stale-rootcause.md`'s "a few percent of frames" mechanism), not the catastrophic 74-82% rate that mechanism's one failing pose produces. Per the ruling, this does NOT invalidate the run; flagged here per the instrumentation requirement.

### Run B results (`vlm_verbatim`, run `20261002_113936`)

| Criterion | Result |
|---|---|
| Jam forms first | **PASS** -- all four within 0.15 m of the standoff by sim_time 27.4 s |
| Full phase sequence executes | **PASS** -- `phase_reached=recede` (robot_3), then `phase_reached=cross` (robot_4), then `phase_reached=resolved done=True`; staggered, never simultaneous |
| Provenance correct | **PASS** -- `plan.provenance="vlm_verbatim"`, `edits=[]`: the scripted plan (naming `robot_4` then `robot_3`) verified feasible and executed with zero repair |
| Deploy check (no `shipped_unsolved` tag) | **PASS** -- `grounding_degradations: ["junction_clear=recede"]` only |
| Ordered crossing (yielder re-enters last) | **PASS for the phase itself**, same caveat as run A below |
| 4/4 position-verified arrivals | **FAIL within this run's window** -- only `robot_2` arrived (`dist_to_goal_m=0.069`); `robot_1` (1.202 m), `robot_3` (2.865 m), `robot_4` (0.961 m) frozen, `min_pairwise_distance_m` bottoming at 0.331 m -- same mock-exhaustion cause as run A (see below), not a second independent deadlock mechanism |

**Live-position chi re-ranking, confirmed in a real run (not just the hand-computed tie from the step-5 landing notes):** the actual dispatch order was **robot_3 first, then robot_4** -- the OPPOSITE of run A's order and of this run's own scripted `proposed_plan` (which named `robot_4` then `robot_3`, matching the synthetic standoff frame's D_SPACE numbers, 0.923 vs 0.942). `ground_junction_clear_phases` ranks chi from the LIVE snapshot at the actual trigger moment, not a fixed reference frame, and the two candidates are a near-exact tie there -- small real trajectory noise flips which one chi ranks cheaper. This did not cost `vlm_verbatim` provenance or `dispatch_matches_plan` (both stayed true): `junction_clear_plan_matches_dispatch` compares each robot's ASSIGNED ACTION, never the relative order between the two recede candidates (confirmed by reading `_plan_problems`'s junction_clear ordering audit, which only checks "every recede leg precedes every yield-axis leg," not recede-vs-recede order), and `_repair_plan`'s search space does not include a recede/recede reorder as a tracked edit either. This is consistent with -- and now empirically reproduces -- the step-5 landing note's own finding 5 ("the cosmetic `extra_holds` LIST ORDER... CAN differ... harmless and not actually exercised twice by this system").

Same root-cause as run A, corrected the same way: `resume base mission robot=robot_3 goal=(0.0, 1.75)` / `robot=robot_1 goal=(1.75, 0.0)` / `robot=robot_2 goal=(-1.75, 0.0)` fire the moment `done=True`, releasing the N-S pair toward each other's original goals with no further ordering. M5's detector re-triggers for this stuck set repeatedly (confirmed: `starting analysis` for `['robot_1','robot_3','robot_4']`/`['robot_3','robot_4']` fires at least 4 more times after resolution, e.g. `request=7f7b4550...`, `request=3fba3218...`, `request=04c41327...`, `request=9b2aec5d...`), and each is answered by `MockBackend`'s held-last-entry `none` (both `04c41327...` and `9b2aec5d...` decision artifacts confirm `backend_id="mock"`, `strategy="none"`, the run B script's own final justification text). **Two independent runs, same mock-exhaustion cause** -- the composite and M5's retry loop both work; a 3-entry scripted mock cannot answer a conflict it was never scripted to resolve.

### STALE instrumentation (run B)

| Robot | Distinct-frame STALE events | Longest streak | Window |
|---|---|---|---|
| robot_1 | 0 | 0 | -- |
| robot_2 | 0 | 0 | -- |
| robot_3 | 0 | 0 | -- |
| robot_4 | 0 | 0 | -- |

Zero STALE frames across all four robots for the whole 300 s episode (389 distinct M1 frames per robot). Consistent with the mechanism being a per-pose phase effect that does not fire on every run (the rootcause report's own framing); does not conflict with run A's two single-frame blips -- both are well inside the documented noise floor.

---

## Step 5: live episode (VM, ER-2)

Run `20261002_120337`, `BACKEND_ID=gemini` (`gemini-robotics-er-2-preview`,
pinned in `config/models.yaml`), plan channel on (prompt v3 rendered),
IB10's deployed obstacles config (none, as shipped). Preflight: one minimal
real call through `backend_factory.build_backend("gemini", ...)` before the
episode (two synthetic robots, a marker PNG as the image, `max_tokens=512`)
-- transport/auth/schema round-trip confirmed (`served_model=gemini-
robotics-er-2-preview`, a real `token_usage` block back); the call's own
output got truncated by the preflight script's deliberately small
`max_tokens`, which is a property of that throwaway script, not of the
deployed config (`ReasonerConfig`'s real default is 2048).

The live episode produced exactly two VLM-triggered decisions. Both quoted
verbatim from their decision artifacts:

**Decision 1** (`78d932839ee748f3a1946cbef11399e7`, dispatched at the
formed four-way standoff):

- strategy: `junction_clear`
- involved_robots: `[robot_1, robot_2, robot_3, robot_4]`
- crossing_order: `[robot_1, robot_2, robot_3, robot_4]`
- proposed_plan: `[{cross, robot_1}, {wait, robot_2}, {wait, robot_3}, {wait, robot_4}]`
- justification: "A sequential clearance of the junction is required where
  some robots yield or reverse to allow others to pass sequentially."
- token_usage: `{prompt_tokens: 2659, completion_tokens: 341, thought_tokens: 305, total_tokens: 3305}`

**Gate/repair handling:** the model picked the right strategy token
(`junction_clear`) but its own `proposed_plan` has **zero** `reverse` or
`yield` legs (`cross` + three `wait`), failing `junction_clear`'s own (a0)
consistency rule (">= 1 reverse or yield leg") outright -- an inconsistent
plan, never reaching the repair search. `verify_and_repair_plan` correctly
rejected it: `plan.provenance="m3_default"`, and M3's own chi-ranked
derivation ran the full composite exactly as runs A/B's `m3_default` case
did (`grounding_degradations: ["junction_clear=recede"]`, no `shipped_
unsolved` tag -- deploy check passes a third time). Phases executed and
resolved (`phase_reached=recede` x2, then `cross`, then `resolved done=True`)
precisely as before. **This is the (a0) safety net working on a REAL model
output, not a synthetic one**: a plausible-but-structurally-wrong plan
(the model named a passer and three waits, no recede/yield at all) was
caught and replaced before it ever reached M4, with the substitution
logged and attributable.

**Decision 2** (`4362ae3848e24ef7bde0a1e66dfe56c1`, dispatched 4.3 s after
the second trigger, itself fired at the same post-resolution N-S conflict
runs A/B hit -- `starting analysis ... robots=['robot_1','robot_3','robot_4']
reason=3 robot(s) stalled >= 12.0s`):

- strategy: `reverse` (not `junction_clear` -- a genuine result, per the
  task's own framing, not a failure to retry)
- involved_robots: `[robot_3, robot_4]` (`robot_1` named in the trigger but
  not in the decision's own involved set)
- proposed_plan: `[{reverse, robot_3}, {reverse, robot_4}, {continue, robot_1}, {continue, robot_2}]`
- justification: "Both robots are head-on and within the physical conflict
  distance threshold, so they must reverse to clear the deadlock."
- token_usage: `{prompt_tokens: 2756, completion_tokens: 273, thought_tokens: 370, total_tokens: 3399}`

**Gate/repair handling:** `plan.provenance="vlm_verbatim"`, `dispatch_
matches_plan=true`, zero edits -- the plan is internally consistent for a
plain `reverse` strategy and every leg feasible, so it executed exactly as
proposed: `dispatch request=4362ae... command=...-reverse robot=robot_3`
then `robot=robot_4`.

**Arrival result:** 1/4 at sim_time 300 s (`robot_2`, `distance_to_goal_m=
0.061`); `robot_1` (1.881 m) and `robot_4` (1.238 m) stationary; `robot_3`
(2.147 m) **still moving** (`speed_mps=0.133`) when the window closed. No
robot-robot or robot-static contacts anywhere in the GT (0/3001 rows).
**This is a materially different shape of result from runs A/B, and the
report says so plainly**: decision 2 dispatched at wall-elapsed ~306 s
since M5 start -- essentially at the edge of the scenario's own 300 s
window -- so `robot_3`/`robot_4`'s `reverse` maneuver had almost no time
to execute before recording stopped. Runs A/B's mock never got a real
answer to this same secondary conflict at all (it held `none` forever);
the live model answered correctly and promptly (two real calls, ~4-5 s
turnaround each) both times it was asked, and the composite + the post-
resolution recovery decision were both handled on their merits. Whether
the full episode would reach 4/4 given more wall time past 300 s is not
established by this run (not re-run, per the one-re-run-is-for-infra-
failures-only rule -- this is a timing/window observation on a result that
already landed, not an infra failure to retry past once).

### STALE instrumentation (live episode)

| Robot | Distinct-frame STALE events | Longest streak | Window |
|---|---|---|---|
| robot_1 | 1 | 1 | t=6.97 s (pre-departure bring-up) |
| robot_2 | 0 | 0 | -- |
| robot_3 | 0 | 0 | -- |
| robot_4 | 0 | 0 | -- |

Same shape as run A (one isolated pre-trigger blip), inside the documented
noise floor, no scoring-relevant window affected.

### API spend

Two live decision calls plus the one preflight call, this task's entire
live API usage:

| Call | prompt_tokens | completion_tokens | thought_tokens | total_tokens |
|---|---|---|---|---|
| Preflight | 2089 | 25 | 483 | 2597 |
| Decision 1 (`junction_clear`) | 2659 | 341 | 305 | 3305 |
| Decision 2 (`reverse`) | 2756 | 273 | 370 | 3399 |
| **Sum** | **7504** | **639** | **1158** | **9301** |

Published price, sourced live (WebSearch, cross-confirmed by two
independent listings -- [tldl.io](https://www.tldl.io/guides/gemini-api-pricing),
[aifreeapi.com](https://www.aifreeapi.com/en/posts/gemini-api-pricing-2026)):
**Gemini Robotics-ER 2 Preview: input $1.00 / 1M tokens, output $5.00 / 1M
tokens.** Neither source lists a separate rate for "thinking" tokens on
this model; this estimate **assumes** completion + thought tokens both
bill as output (the common Gemini thinking-model convention), flagged as
an assumption, not a confirmed line item:

- Input: 7504 tokens x $1.00/1M = **$0.0075**
- Output (639 + 1158 = 1797 tokens) x $5.00/1M = **$0.0090**
- **Total: ~$0.017** (1.7 cents) for this task's entire live-API footprint.

---

## Step 6: STALE instrumentation

Per the resolved gate's ruling (`docs/superpowers/specs/2026-09-30-prereg-
v2-design.md` build-order step 6), every run was checked for a long STALE
streak on any robot during any stationary dwell. Summary across all three
runs (full per-run tables in each run's own section above):

| Run | robot_1 | robot_2 | robot_3 | robot_4 |
|---|---|---|---|---|
| A (`m3_default` mock) | 1 frame @ t=6.0s (bring-up) | 0 | 0 | 1 frame @ t=72.1s (recede dwell) |
| B (`vlm_verbatim` mock) | 0 | 0 | 0 | 0 |
| Live (ER-2) | 1 frame @ t=6.97s (bring-up) | 0 | 0 | 0 |

No run showed a streak longer than a single distinct M1 frame (every
apparent multi-row "streak" in the raw scene log collapses to one frame
once M5's own re-logging of an unchanged M1 frame is accounted for -- see
run A's section for the worked example). None coincided with a scoring-
relevant window: the bring-up blips predate every trigger, and the one
recede-dwell blip (run A, robot_4) sits under the stale-tolerant
`ArrivalGate`, which costs no credit on a stale read. Per the ruling, this
flag does **not** invalidate any of the three runs; the registered fallback
(a 0.10 m symmetric spawn re-radius) is not triggered.

---

## Local verification

Full local unit suite, `--ignore` on the five documented `pxr`-only files
(the local/container environment split on record in `docs/
implementation_notes.md`): a disposable detached worktree at the exact
branch point (`955b962`) gives a trusted baseline of **58 failed / 4299
passed / 139 skipped**, identical failing-test-name set to this task's
every intermediate checkpoint. After all local commits above: **58 failed /
4311 passed / 139 skipped**, same failing-test-name set, zero delta.
`make lint` (ruff) clean on every touched Python file.

(Note: a scratchpad file this task used for an earlier, narrower baseline
comparison was overwritten mid-task by what the environment confirms is a
concurrent, unrelated process sharing the same scratchpad directory -- see
"VM preflight" below. The disposable-worktree baseline above is the
trustworthy one; it does not depend on that file.)

---

## VM preflight

**STATUS: IN PROGRESS.** To be filled in: idle-state confirmation
(`pgrep -f run_simulation`, no `ros2`/orchestrator/perception/Nav2 process
in `vgu_ros`, `nvidia-smi` idle, no stray `/tmp/*.tar` deploy artifacts, no
VM-tree files modified in the last 2 hours), pre-deploy md5 of orchestrator.
yaml/rag.yaml (source and installed, both expected `1f656533a30a35882d57
d0d64a57bd0d` / `e18c723cff9cada3f320d564c2ecee5a` per the standing VM
state the 2026-10-01 stale-rootcause task left it in), and a backup copy at
`/tmp/ib10_pristine/` before any deploy.
