# IB10 `junction_clear` Composite Smoke (v2 build-order step 6)

**Prepared:** 2026-10-02

**Revision history:**

- Initial draft: local work (goal-table fields, loudness guard, repair-bound
  sweep) complete and committed; VM sections (mock smoke, live episode,
  STALE instrumentation, restore) in progress, drafted as stubs so the local
  findings are durable independent of the VM session's outcome.
- Rev 2 (post-VM, post-advisor-review): filled in all three VM runs, close-
  out, and API spend; then corrected three errors the review caught: the
  STALE analysis (a collapse-to-first-row method erased every real
  dropout), arrivals (now cited against the actual `ArrivalGate` log, not
  GT distance alone -- confirms the same 1/4 conclusion), and the live
  episode's second decision (its real trigger stamp is 96 s, not ~306 s as
  wall-clock estimated; traced the actual mechanism through `m4.log` + GT
  instead). Also folded run B's dispatch-order mismatch into the step-4
  metric-hole finding instead of calling it harmless, and added the full
  md5 manifest check. Every number this revision changed is marked
  "correction" in place; nothing is silently rewritten.
- Rev 3 (further review pass, before close-out): the live episode's
  "no net progress, Nav2 cycling" replacement claim was ALSO wrong -- a
  review pass measured this episode's own real-time factor directly from
  two decision stamps (0.273) and found `REC_SEC=450` only kept the ROS2
  control stack alive to sim~134.6 s, so everything in GT after that is a
  dead-stack artifact, not navigation. Retraced the real mechanism inside
  the alive window (a `continue` leg not exempted against a `reverse`,
  confirmed via `m4.log`'s safety-stop lines + GT's own trajectory, plus a
  newly-found out-of-tracked-band excursion coinciding with that robot's
  STALE streak) and re-ran the episode once more, with `REC_SEC`/`SIM_SEC`
  sized to the measured RTF, under the one-re-run allowance (harness
  truncation is an infra failure, not a result). Both episodes' decisions
  are kept as data. Also fixed run A/B's re-trigger sim-times (computed
  from wall-clock assuming 1x instead of the measured RTF) and added a
  consolidated freeze-blocking findings section.

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

**For the coordinator:** `feat/prereg-v2-composite` has moved from this
branch's merge-base (`955b962`) to `d193c39` while this task ran (other
work landed on it concurrently -- confirmed via the shared scratchpad and
VM evidence in the VM-preflight section below). This branch's own diff
(`git diff 955b962..HEAD`) is the correct, minimal one to review -- 9
files, two new JSON mocks, no deletions outside one 15-line orchestrator.
yaml edit; diffing against the CURRENT tip of `feat/prereg-v2-composite`
instead shows unrelated files this task never touched. A rebase (not
performed here, per "no merge, no push") will be needed before landing.

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
not a unilateral edit during a sizing sweep). **Confirmed live, not just
swept**: run B (below) independently reproduces the same category of gap
-- a `junction_clear` plan whose two recede legs are correctly MEMBERED but
wrongly ORDERED relative to each other also verifies `vlm_verbatim` with no
repair offered, because `_plan_problems` has no recede-vs-recede order
check either. Both the membership gap (this sweep) and the order gap (run
B) share one root cause: the junction_clear consistency/feasibility audit
checks recede-vs-yield-axis ordering only, never anything about the
recede set's own membership or internal order.

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
| Jam forms first | **PASS** -- stricter than a GT-proximity check: the trigger decision's OWN snapshot (`decision_junction_clear.json`'s `scene.stamp=34.333`) shows all four robots already `STOPPED` at the standoff (verified against GT, which independently shows all four within 0.15 m of the standoff reference by sim_time 26.5 s, 7.8 s before this exact trigger) |
| Full phase sequence executes (recede robot_4, then robot_3, staggered sequential; yield phase; done) | **PASS** -- `phase advance ... phase_reached=recede done=False` (robot_4), then `phase_reached=cross done=False` (robot_3), then `phase_reached=resolved done=True` (cross phase); never two recede legs in one command (confirmed from the dispatch lines: each recede command addresses exactly one active `reverse` robot) |
| Provenance correct | **PASS** -- decision artifact `5e42a221d4dc488c9632957e21a2acee.json`: `plan.provenance="m3_default"`, `plan.rejection_reason="plan absent"` (no `proposed_plan` in run A's mock, as designed), `plan.dispatch_matches_plan=true`, legs `[robot_4 reverse, robot_3 reverse, robot_1 yield, robot_2 cross]` -- the exact chi order |
| Deploy check (no `shipped_unsolved` tag) | **PASS** -- `grounding_degradations: ["junction_clear=recede"]` only, confirming both J2 fields reached the installed config |
| Ordered crossing (yielder re-enters last) | **PASS for the phase itself** -- the cross phase's own command grounded `robot_1` yield + `robot_2` cross per the solved row; see the FAIL below for what happens after |
| 4/4 position-verified arrivals | **FAIL within this run's window** -- scored by the actual scoring instrument, `swarm_orchestrator.arrival.ArrivalGate` (`docs/reports/2026-10-01-robot1-stale-rootcause.md`'s own finding of which gate governs scoring), not GT distance alone: `m5.log` carries exactly one `robot ... arrived at base goal` line for the whole run (`robot_2`, `distance_m=0.09`, `check=within_tolerance`), no `arrival rejected`/`arrival accepted late` lines at all. GT cross-check agrees: `robot_1`/`robot_3`/`robot_4` frozen (`speed_mps=0.000`) from sim_time ~120 s onward, `min_pairwise_distance_m` pinned at 0.398 m. See the correction below: this is the mock script's finite length, not a stable architectural deadlock -- M5 keeps re-triggering, the mock just has nothing new left to say. |

**Root-cause finding, corrected after the live episode below surfaced the full picture (do not read this paragraph without that correction):** the composite's own phase sequence has no scope over what happens after `done=True`. M5's `junction_phase_queue` releases every held recede candidate back to its **original base-mission goal** the moment the cross phase resolves (`resume base mission robot=robot_4 goal=(0.0, -1.75)` / `robot=robot_3 goal=(0.0, 1.75)` in `fc_20261002_111456_m4.log`) -- robot_3 and robot_4 parked on OPPOSITE sides of the junction during their staggered recede and are released toward each other's original goals on the opposite arm, a fresh N-S encounter the `junction_clear` contract never orders. The scene log shows M5's congestion detector repeatedly noticing this and re-triggering a NEW analysis for the stuck robots -- 8 separate `starting analysis` calls for `['robot_1','robot_3','robot_4']`/subsets, spanning sim_time ~110-143 s by each request's own decision-artifact `scene.stamp` (`request=8c60a56c...` at 110.1 s through `request=37f2a5ab...` at 142.7 s), not a one-time suppression -- and this whole span sits inside the real, alive control window (this run's own measured real-time factor and `fc-launch cleanup` wall-time place the container teardown at approximately sim 141-144 s, essentially right at the last of these re-triggers, so none of this evidence depends on a dead-stack period). **The real cause the first pass of this report missed**: `MockBackend` (`reasoning/vlm/mock_backend.py`) replays `VGU_MOCK_DECISION_FILE`'s scripted array in order and **holds the LAST entry forever once exhausted** -- run A's 3-entry script ends on `none` (congestion_detected=false), so every one of those 8 re-triggers gets answered "no congestion" and nothing is ever dispatched for the stuck trio. This is a property of the finite mock script, not of M5's retry/cooldown machinery, which the live episode (Step 5 below) demonstrates DOES eventually resolve the identical secondary conflict once a backend that always answers something is in the loop. **Reported as a result, re-scoped by the live run**: the composite's own job (recede + yield + cross, phase-by-phase, provenance-correct, solved-row numbers) is fully verified working; the post-resolution base-mission release creates a genuine secondary conflict outside the composite's own scope, M5's detector does keep retrying it (not a suppression bug), and whether it resolves depends on the backend actually answering it -- which a finite scripted mock, by construction, cannot do indefinitely. GT positions reported as "frozen" in the arrivals row above span from sim~120 s to GT's own 300 s cap; only the ~120-144 s portion of that is a genuinely alive, actively-retriggering control window -- the remainder (~144-300 s) is the same kind of dead-stack artifact traced in detail for the live episode below (no process is running inside `vgu_ros` after the container restart), consistent with, not contradicting, the frozen positions already observed within the alive window.

### STALE instrumentation (run A)

**Correction from this report's first draft**: the first pass collapsed
consecutive scene-log rows sharing one M1 frame stamp down to their FIRST
occurrence, on the theory that M5 re-logs one unchanged frame several times
per M1 publish. That collapse is wrong -- a frozen stamp is exactly what a
STALE dwell looks like (M1 stops advancing the stamp, M5 keeps logging at
its own rate, and status genuinely transitions STOPPED -> STALE across
those same-stamp rows as carried-forward age crosses the threshold); taking
the first row at each stamp discards every transition to STALE. Recomputed
using the project's own authoritative method (`scripts/m1_y_extent_probe_
analysis.py`'s `score_scene_log`: raw per-row counts, `age = scene_stamp -
robot_stamp`, streak = consecutive raw rows), over the real `m5_scene/
fbe42f6dee3b40b5b6dcf2f5540f26c2.jsonl` (370 rows/robot):

| Robot | STALE rows | % | Longest streak | max_age (s) | Window (sim-s) |
|---|---|---|---|---|---|
| robot_1 | 4 | 1.1% | 4 | 11.667 | 16.93-17.67 |
| robot_2 | 19 | 5.1% | 10 | 4.033 | 44.73-47.37 |
| robot_3 | 0 | 0.0% | 0 | 0.067 | -- |
| robot_4 | 26 | 7.0% | 15 | 5.767 | 73.37-77.90 |

None of these windows overlaps the `junction_clear` trigger's own snapshot
stamp (34.333 s, confirmed `STOPPED` for every robot in the decision
artifact itself). `robot_1`'s and `robot_2`'s windows are both pre-trigger
(bring-up and early approach). `robot_4`'s 15-row/4.5 s streak at 73.4-
77.9 s is confirmed directly from the raw scene log (position frozen at
`(0.000, 1.204)`, velocity ~0.003 m/s, continuously from sim 46.1 s to past
80 s) to fall inside its settled, PARKED recede-pocket hold -- robot_4
reached its recede pocket and stopped at sim~46 s, well before this STALE
window, and stayed there through the subsequent robot_3 recede and cross
phases. This is exactly the stationary-dwell category the resolved gate's
instrumentation rule targets, though the stale-tolerant `ArrivalGate`
still governs no credit either way for a mid-sequence hold. No run observed a STALE
event during `robot_1`'s OWN park dwell (the cross-phase yield, much later
in the run): this neither confirms nor rules out the solved-row park pose
(~(-1.018, 0.36), never directly probed by `docs/reports/2026-10-01-
robot1-stale-rootcause.md`'s yieldpark run, which tested the shipped-
clearance pose `(-1.37, 0.359)` instead) -- absence of an observed event
across three runs is suggestive, not a probe of that specific pose. Per the
resolved gate's ruling, none of these streaks invalidate the run (no
scored-arrival-window overlap), but they are materially different numbers
from the first draft's "1 isolated frame" claim and are reported as such.

### Run B results (`vlm_verbatim`, run `20261002_113936`)

| Criterion | Result |
|---|---|
| Jam forms first | **PASS** -- trigger snapshot `scene.stamp=34.4` shows all four `STOPPED` at the standoff (GT independently shows all four within 0.15 m by sim_time 27.4 s, 6.6 s earlier) |
| Full phase sequence executes | **PASS** -- `phase_reached=recede` (robot_3), then `phase_reached=cross` (robot_4), then `phase_reached=resolved done=True`; staggered, never simultaneous |
| Provenance correct | **PASS on action-membership, FAIL on sequence order -- see the finding below, folded into the step-4 freeze-blocking metric hole, not a separate harmless note** |
| Deploy check (no `shipped_unsolved` tag) | **PASS** -- `grounding_degradations: ["junction_clear=recede"]` only |
| Ordered crossing (yielder re-enters last) | **PASS for the phase itself**, same caveat as run A below |
| 4/4 position-verified arrivals | **FAIL within this run's window** -- `ArrivalGate` log: exactly one `arrived at base goal` line all run (`robot_2`, `distance_m=0.06`), no rejections/late-accepts. GT agrees: `robot_1` (1.202 m), `robot_3` (2.865 m), `robot_4` (0.961 m) frozen -- same mock-exhaustion cause as run A, not a second independent deadlock mechanism |

**Correction, folded into the step-4 freeze-blocking finding (this was wrongly called harmless in the first draft):** the actual dispatch order was **robot_3 first, then robot_4** -- the OPPOSITE of run A's order and of this run's own scripted `proposed_plan` (which named `robot_4` then `robot_3`). `ground_junction_clear_phases` ranks chi from the LIVE snapshot at the trigger moment, not a fixed reference frame, and the two candidates are a near-exact tie there. `verify_and_repair_plan` still reports `provenance="vlm_verbatim"` and `dispatch_matches_plan=true` -- **but "executed verbatim" is literally false for this plan**: the model proposed `[robot_4, robot_3, robot_1, robot_2]` and M5 dispatched `[robot_3, robot_4, robot_1, robot_2]`, a different sequence. `junction_clear_plan_matches_dispatch` masks this because it compares each robot's ASSIGNED ACTION, never the order between the two recede legs. This is **not** explained by step-5's finding 5 (which is about `extra_holds` list-order cosmetics, not the primary recede sequence), and it is **not** a case `_repair_plan` structurally cannot fix: its `reorder` op swaps any two touchable legs, including two `reverse` legs -- the reason this run's plan was never even offered to repair is that `_plan_problems`'s junction_clear audit only checks "every recede leg precedes every yield-axis leg," never recede-vs-recede relative order, so a plan with the two recede legs swapped is never flagged as a problem in the first place and is accepted verbatim at zero edits. **This is the step-4 metric hole's twin, now observed live, not just swept**: the (a0) consistency/feasibility audit has no recede-vs-recede order check, so provenance and `dispatch_matches_plan` both over-credit a plan whose proposed order the live dispatch did not follow.

Same root-cause as run A, corrected the same way: `resume base mission robot=robot_3 goal=(0.0, 1.75)` / `robot=robot_1 goal=(1.75, 0.0)` / `robot=robot_2 goal=(-1.75, 0.0)` fire the moment `done=True`, releasing the N-S pair toward each other's original goals with no further ordering. M5's detector re-triggers for this stuck set repeatedly (confirmed: `starting analysis` for `['robot_1','robot_3','robot_4']`/`['robot_3','robot_4']` fires at least 4 more times after resolution, e.g. `request=7f7b4550...` at sim 127.6 s by its own decision-artifact stamp, `request=3fba3218...`, `request=04c41327...`, `request=9b2aec5d...`), and each is answered by `MockBackend`'s held-last-entry `none` (both `04c41327...` and `9b2aec5d...` decision artifacts confirm `backend_id="mock"`, `strategy="none"`, the run B script's own final justification text). This run's own measured real-time factor (0.278, from the two decision stamps 34.4 s and 127.633 s against their wall-clock gap) places this run's container teardown at roughly sim 138 s -- all four re-triggers above are within or at the edge of that alive window; GT's own 300 s cap beyond that point is the same dead-stack artifact traced in detail for the live episode, not further evidence. **Two independent runs, same mock-exhaustion cause** -- the composite and M5's retry loop both work; a 3-entry scripted mock cannot answer a conflict it was never scripted to resolve.

### STALE instrumentation (run B)

Recomputed with the corrected raw-row method (see run A's correction note):

| Robot | STALE rows | % | Longest streak | max_age (s) | Window (sim-s) |
|---|---|---|---|---|---|
| robot_1 | 0 | 0.0% | 0 | 0.233 | -- |
| robot_2 | 2 | 0.5% | 2 | 1.633 | 30.37-30.60 |
| robot_3 | 0 | 0.0% | 0 | 0.267 | -- |
| robot_4 | 0 | 0.0% | 0 | 0.033 | -- |

`robot_2`'s brief 2-row/0.23 s blip at 30.37-30.60 s falls inside the
pre-trigger stall-accumulation window (the detector's own 12 s stall
threshold means it was accumulating evidence from roughly 22.4 s onward for
the 34.4 s trigger) but the trigger snapshot itself (34.4 s) shows
`robot_2` `STOPPED`, not `STALE` -- the blip resolved before the decision
was made. Much lower overall than run A (this run's own mechanism-level
background noise is simply quieter), consistent with the resolved gate's
framing of a per-pose phase effect that does not fire identically every
run. No streak invalidates this run.

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

**Decision 2** (`4362ae3848e24ef7bde0a1e66dfe56c1`, trigger snapshot
`stamp=96.267` -- confirmed by the decision artifact's own `scene` block,
not a wall-clock estimate -- dispatched 4.3 s after the second trigger,
itself fired at the same post-resolution N-S conflict runs A/B hit --
`starting analysis ... robots=['robot_1','robot_3','robot_4'] reason=3
robot(s) stalled >= 12.0s`):

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

**Correction, twice over -- both retracted, replaced with a traced
mechanism.** The first draft claimed "1/4, ran out of time" (wrong: decision
2's trigger stamp, read from its own artifact, is 96.267 s, not the ~306 s
a wall-clock estimate gave). The second draft then claimed "1/4, no net
progress for 170 s, Nav2 cycling" (also wrong, caught on a further review
pass): `REC_SEC=450` bounds how long `fc_launch.sh` keeps the ROS2 control
stack (M1/M4/M5/Nav2, everything inside the `vgu_ros` container) alive, in
WALL seconds -- and this episode's own two decision-artifact stamps give a
directly measured real-time factor: `(96.267 - 30.233) sim-s / (1790943022.82
- 1790942780.68) wall-s = 0.273`. At that RTF, 450 wall-seconds covers only
~123 sim-seconds from M5's own start, and the actual `fc-launch cleanup:
restarting container + killing Isaac` line lands at a wall-time that maps
to **sim_time ~134.6 s** -- so everything after that in GT (robot_4 "frozen
at a fixed point," robot_3 "oscillating in a small box") is a **dead-stack
artifact**: no M1/M4/M5/Nav2 process is running, so GT after 134.6 s is
just physics continuing to integrate whatever velocity each robot held at
shutdown, not navigation. **Arrivals in this episode are therefore not
meaningfully measured past sim~135 s** -- the `ArrivalGate` log shows the
same single `robot_2` acceptance as before, but the window during which a
second arrival could have happened was never actually run. A second
episode, with a corrected `REC_SEC`/`SIM_SEC` sized to this measured RTF,
follows below; this episode's own first ~135 s remain valid data.

**The traced mechanism, confirmed through `m4.log` + GT together, entirely
within the alive window (sim 96-135 s):**

1. Decision 2's own `proposed_plan` marks `robot_1` `continue` -- it is not
   involved in this trigger's conflict at all, and keeps driving its base
   mission uninterrupted while `robot_3`/`robot_4` reverse.
2. `robot_1` was already closing on `robot_4` before the trigger (GT:
   `d(robot_1, robot_4)` falls from 1.11 m at sim 94 s to 0.433 m by sim
   99.3 s -- below the 0.45 m safety latch) -- `robot_1` is not one of
   `robot_4`'s `admitted_partners` (that exemption only covers `robot_3`,
   the other member of command `4362ae...-reverse`), so M4's safety monitor
   fires `safety stop robot=robot_4 reason=min_distance_violation`
   repeatedly from wall 1790943020 onward.
3. `robot_4`'s `reverse` command never reaches `status=COMPLETED` anywhere
   in the alive window (last line is `status republished ... status=ACTIVE`
   at wall 1790943029.9) -- GT confirms it stops dead at `(0.169, -0.628)`
   by sim 99.5 s and never moves again, consistent with the command simply
   never resolving, not with a later architectural stall.
4. `robot_3`'s own `reverse` overshoots badly: GT shows it driving
   continuously south from `(0.04, -1.13)` at sim 97 s to `(0.00, -2.38)`
   by sim 111 s -- past the verified-tracked `|y| <= 1.75` extent and the
   homography's own 2.09 m edge. This is the EXACT window of this run's
   longest STALE streak (108.8-114.7 s, below) -- a real overlap between an
   active maneuver and a tracking dropout, not the coincidence a settled
   dwell would be. `robot_3`'s own `reverse` then does complete
   (`status=COMPLETED` at wall 1790943086) and `resume base mission
   robot=robot_3 goal=(0.0, 1.75)` fires correctly; GT shows it driving
   north at ~0.15-0.17 m/s from sim 112 s, reaching `(0.34, -0.60)` by sim
   124 s -- then slowing to a stop near `robot_4`'s frozen position
   (within the safety latch again) by sim 126-130 s, which is the last
   real-control-window state GT records before the ~134.6 s shutdown.
5. With `robot_4`'s own action inside command `4362ae...` never resolving,
   M5's busy-robot bookkeeping keeps the trigger suppressed for the rest of
   the alive window (confirmed: every subsequent `m5.log` line before
   shutdown is `trigger suppressed`, never another `starting analysis`).

**Reported as found, backup bound not fixed here**: a plain `reverse`
decision that leaves an uninvolved, still-approaching robot (`robot_1`) on
`continue` is not safety-exempted against the robots it is about to
encroach on (`admitted_partners` only covers same-command members); and
`robot_3`'s own backup distance for this 2-robot conflict geometry ran it
~1.2 m past the verified tracking extent, with no tracked-band bound the
way `junction_clear`'s own recede pockets have one. Both are M3/M4
grounding gaps for the plain `reverse` strategy, not `junction_clear`-
specific, and out of this task's scope to fix -- added to the freeze-
blocking list below.

### STALE instrumentation (episode 1)

Recomputed with the corrected raw-row method (see run A's correction note):

| Robot | STALE rows | % | Longest streak | max_age (s) | Window (sim-s) |
|---|---|---|---|---|---|
| robot_1 | 3 | 0.8% | 3 | 10.300 | 16.83-17.27 |
| robot_2 | 0 | 0.0% | 0 | 0.600 | -- |
| robot_3 | 25 | 6.4% | 25 | 7.233 | 108.80-114.73 |
| robot_4 | 0 | 0.0% | 0 | 0.467 | -- |

`robot_1`'s streak is pre-trigger bring-up (well before the 30.233 s
trigger). `robot_3`'s 25-row/5.9 s streak at 108.8-114.7 s overlaps its
out-of-tracked-band excursion traced above (step 4) almost exactly -- this
STALE streak is therefore DURING an active maneuver gone past the verified
tracking extent, not
an idle dwell. It does not change the finding (the mechanism traced above
is a safety-exemption gap confirmed independently through `m4.log`/GT, not
an M1 tracking artifact), but it is reported here because the resolved
gate's instrumentation rule asks for exactly this kind of overlap check,
and this is the one run where a real overlap exists.

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

Longest streak (raw rows, the project's own authoritative method --
`scripts/m1_y_extent_probe_analysis.py`'s `score_scene_log`) and whether it
overlaps a trigger snapshot or an active phase/maneuver window:

| Run | robot_1 | robot_2 | robot_3 | robot_4 |
|---|---|---|---|---|
| A (`m3_default` mock) | 4 rows @ 16.9-17.7s (bring-up) | 10 rows @ 44.7-47.4s (pre-trigger approach) | 0 | 15 rows @ 73.4-77.9s (parked recede-pocket HOLD, confirmed stationary from sim 46.1s) |
| B (`vlm_verbatim` mock) | 0 | 2 rows @ 30.4-30.6s (pre-trigger stall window, trigger itself fresh) | 0 | 0 |
| Live (ER-2) | 3 rows @ 16.8-17.3s (bring-up) | 0 | 25 rows @ 108.8-114.7s (DURING the unresolved post-decision-2 recovery attempt) | 0 |

**Correction from this report's first draft**: the first pass collapsed
repeated scene-log rows sharing one M1 stamp down to their first
occurrence, which erased every transition into STALE and undercounted
every one of these numbers to "0 or 1 isolated frame." Recomputed from raw
rows, two streaks genuinely overlap an active window (run A's robot_4
during its own recede backup; the live run's robot_3 during the unresolved
secondary-conflict recovery traced in Step 5) rather than a settled dwell.
No streak overlaps a `junction_clear` TRIGGER's own snapshot stamp in any
run -- every trigger snapshot (run A 34.333s, run B 34.4s, live decision 1
30.233s, live decision 2 96.267s) independently confirms every robot
`STOPPED`, not `STALE`, at that exact instant (from each decision
artifact's own `scene` block). `robot_1`'s own solved-row park dwell
(cross-phase yield) shows no STALE event in any of the three runs, but
that is an absence-of-evidence result, not a probe of that specific pose
(~(-1.018, 0.36), still never directly tested the way `docs/reports/
2026-10-01-robot1-stale-rootcause.md`'s yieldpark run tested the
shipped-clearance pose). Per the resolved gate's ruling, none of this
invalidates any of the three runs (no scored-arrival-window overlap in any
case -- the `ArrivalGate` governs none of the overlapping windows above);
the registered fallback (a 0.10 m symmetric spawn re-radius) is not
triggered.

---

## Freeze-blocking findings (consolidated)

Four findings this task surfaced that the (a0)/`junction_clear`/`reverse`
machinery does not currently cover, none fixed here (out of this task's
scope -- each is a separate, scoped change for the coordinator to decide):

1. **Recede-set membership and order are unaudited.** `_plan_problems`'s
   `junction_clear` check only verifies recede-legs-precede-yield-axis-legs
   ordering; it checks neither WHICH robots hold the recede legs (the
   step-4 sweep's wrong-recede-pair cases verify `vlm_verbatim`) nor the
   order BETWEEN the two recede legs themselves (run B's live dispatch
   order, the opposite of its own proposed plan, also verifies
   `vlm_verbatim`/`dispatch_matches_plan=true`). Plan-quality metrics (ii)/
   (iv) over-credit both defect classes unless read alongside
   `dispatch_matches_plan`/the oracle-order metric specifically.
2. **Releasing held robots' base missions after `junction_clear` resolves
   creates an unordered secondary conflict.** `junction_phase_queue`
   releases every recede candidate to its original base-mission goal the
   instant the cross phase resolves; when two candidates parked on
   opposite arms, this is a fresh encounter the composite's own contract
   never orders. M5's detector does keep re-triggering on it (confirmed:
   8+ real re-triggers across runs A/B); whether it resolves depends
   entirely on the backend answering with something new, which a finite
   scripted mock cannot do.
3. **A `continue` leg is not safety-exempted against a `reverse` leg in a
   different command.** `admitted_partners` only exempts members of the
   SAME command from each other; an uninvolved robot left on `continue`
   that closes within the safety latch of an active `reverse` triggers a
   `min_distance_violation` safety stop that can permanently stall the
   `reverse` command's own resolution (observed live: `robot_1`/`robot_4`
   in the live episode's decision 2).
4. **The plain `reverse` strategy has no tracked-band bound on its backup
   distance.** `junction_clear`'s own recede pockets are declared scene
   constants, kept inside the verified tracking extent by design (J2 +
   the pocket offset). The plain `reverse` grounding used for a 2-robot
   conflict outside `junction_clear` has no equivalent check: the live
   episode's `robot_3` backed up to `|y| = 2.38`, past the verified
   `|y| <= 1.75` extent and the homography's own 2.09 m edge, coinciding
   with that robot's longest STALE streak of the whole task.

---

## Local verification

Full local unit suite, `--ignore` on the five documented `pxr`-only files
(the local/container environment split on record in `docs/
implementation_notes.md`): a disposable detached worktree at the exact
branch point (`955b962`) gives a trusted baseline of **58 failed / 4299
passed / 139 skipped**. After every commit on this branch, re-run with the
identical command: **58 failed / 4311 passed / 139 skipped**, byte-identical
failing-test-name set to the baseline at every checkpoint, confirmed a
final time after all VM work and the restore above. `make lint` (ruff)
clean on every touched Python file, checked a final time too.

(Note: a scratchpad file this task used for an earlier, narrower baseline
comparison was overwritten mid-task by what the environment confirms is a
concurrent, unrelated process sharing the same scratchpad directory. The
disposable-worktree baseline above does not depend on that file and is the
one this report relies on throughout.)

---

## VM state: preflight and close-out

**Preflight** (before any deploy): `pgrep -f run_simulation` empty, no
`ros2`/orchestrator/perception/Nav2 process inside `vgu_ros`, GPU 0%/171 MiB,
pre-deploy md5 of `orchestrator.yaml`/`rag.yaml` matched the standing
convention exactly on every copy (source, installed, host, container):
`1f656533a30a35882d57d0d64a57bd0d` / `e18c723cff9cada3f320d564c2ecee5a`,
backed up verbatim to `/tmp/ib10_pristine/`. Three stray `/tmp/ship_*_
delta.tar` files predate this task (Sep 30) and are unrelated to it --
left alone, not this task's to clean up. The VM tree had files modified
within the prior ~2 hours (orchestrator.yaml itself, several `colcon`
build logs timestamped ~09:00-09:10 UTC the same morning) despite the
process/GPU checks showing idle -- consistent with a different task's
clean, completed run earlier that morning (its own restore left
`orchestrator.yaml` pristine, confirmed by the matching md5), not a
concurrent conflict; proceeded on that basis per the coordinator review.

**Close-out** (after the live episode, this task's last VM activity):
`orchestrator.yaml`/`rag.yaml` restored from the `/tmp/ib10_pristine/`
backup (plain copy + `touch`, not `copy2`, per the project's own documented
colcon-mtime-skip trap), `swarm_orchestrator` rebuilt, and **all four
copies re-verified pristine**: source `1f656533a30a35882d57d0d64a57bd0d`,
installed host `1f656533a30a35882d57d0d64a57bd0d`, installed container
`1f656533a30a35882d57d0d64a57bd0d`, `rag.yaml` `e18c723cff9cada3f320d
564c2ecee5a`. GPU idle (0%/171 MiB), no `run_simulation`/ROS2/orchestrator/
perception/Nav2 process anywhere, container `vgu_ros` up and clean. All of
this task's `/tmp` deploy artifacts removed from the VM (`ib10_deploy.tar`,
the deployed orchestrator.yaml, build logs, the log bundle, the pristine
backup directory, the three launcher logs). The pre-step-5 source tree this
task's `git archive` deploy overwrote (command_grounder.py, the
orchestrator package, tests, scripts, mock decisions) is left updated to
this branch's `bfc3000`/`47c4121`-era content on the VM -- an intentional,
expected side effect of deploying a real code change, not a config file
the standing convention restores, and consistent with the VM's own
"whoever deploys next" shared-tree model (confirmed by the VM having no
`.git` directory at all -- it is a plain extracted tree, not a clone).

**Manifest check** (standing trap: verify the deploy left nothing else
drifted): a full 724-file md5 manifest of this branch's `git ls-files` at
HEAD, generated locally and diffed against the live VM tree. Three
differences, all expected: `ros2_ws/src/swarm_orchestrator/config/
orchestrator.yaml` (the intentional pristine-restore difference above) and
`docs/implementation_notes.md`/`docs/reports/2026-10-02-ib10-composite-
smoke.md` (this task kept editing these two docs locally after its one
`git archive` deploy; the VM's copies are simply an earlier revision of the
same files -- inert, since nothing on the VM reads them). No other file
differs; the deploy is otherwise byte-identical to this branch's HEAD.
