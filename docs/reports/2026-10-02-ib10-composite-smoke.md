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
| 4/4 position-verified arrivals | **FAIL** -- at scenario end (sim_time 300 s, Isaac given 450 s, 150 s of slack beyond the scenario's own `duration_sec`), only `robot_2` arrived (`distance_to_goal_m=0.104`). `robot_1` (1.931 m), `robot_3` (0.965 m), `robot_4` (2.886 m) did not. GT confirms `robot_1`/`robot_3`/`robot_4` are fully **stationary** (`speed_mps=0.000`, positions frozen) continuously from sim_time ~120 s to 300 s (180 s), `min_pairwise_distance_m` pinned at exactly 0.398 m the whole time -- a genuine stable deadlock, not insufficient run time. |

**Root-cause finding (confirms the coordinator-review flag before this run, not a new discovery made blind):** the composite's own phase sequence has no scope over what happens after `done=True`. M5's `junction_phase_queue` releases every held recede candidate back to its **original base-mission goal** the moment the cross phase resolves (`resume base mission robot=robot_4 goal=(0.0, -1.75)` / `robot=robot_3 goal=(0.0, 1.75)` in `fc_20261002_111456_m4.log`) -- robot_3 and robot_4 parked on OPPOSITE sides of the junction during their staggered recede (robot_3 south pocket, robot_4 north pocket) and are then released simultaneously toward each other's original goals on the opposite arm, a fresh N-S encounter the `junction_clear` contract never orders. The scene log shows M5's congestion detector DID notice the resulting conflict (`trigger suppressed robots=['robot_1', 'robot_3', 'robot_4'] frame_ready=True`, repeated from roughly sim_time 230 s onward) but the trigger stayed suppressed (cooldown/busy guard in `_machine.on_event`, not investigated further -- out of this task's scope to fix), so no second decision ever dispatches and the three robots freeze at the mutual safety latch (`min_distance_m=0.45` in `config/rag.yaml`; observed separation 0.398 m, just inside it). This is exactly the gap the M5 spec section's "remaining robots cross inside-first" language does not cover and the step-5 landing's own "FLAGGED, not resolved by static reading" note anticipated for a different race (base-mission resumption timing) but not this one (base-mission *destination*, post-resolution). **Reported as a result, not patched**: the composite's own job (recede + yield + cross, phase-by-phase, provenance-correct, solved-row numbers) is fully verified working; a second, separable gap exists one layer up, in what M5 does with the held robots' own base missions after the composite resolves.

### STALE instrumentation (run A)

Per-robot streaks over the M5 scene log (`m5_scene/fbe42f6dee3b40b5b6dcf2f5540f26c2.jsonl`, 370 logged cycles), collapsed to DISTINCT M1 frame stamps first (M5's own cycle rate re-logs one unchanged M1 frame several times while M1 itself is between publishes, which inflates a naive row-count streak 15x without a single additional stale frame actually occurring -- confirmed by inspection: `robot_4`'s raw 15-row "streak" is one single frame at stamp 72.133 s, re-logged 15 times):

| Robot | Distinct-frame STALE events | Longest streak (distinct frames) | Window |
|---|---|---|---|
| robot_1 | 1 | 1 | t=6.0 s (pre-departure bring-up) |
| robot_2 | 0 | 0 | -- |
| robot_3 | 0 | 0 | -- |
| robot_4 | 1 | 1 | t=72.1 s (during its recede-pocket dwell) |

Neither event is a streak (both are single isolated frames) and neither coincides with a scoring-relevant window: robot_1's is pre-trigger bring-up (never a scored dwell), robot_4's is mid-recede-dwell under the stale-tolerant `ArrivalGate` (costs no credit per the resolved gate's own finding). Both are consistent with the established background noise floor (`docs/reports/2026-10-01-robot1-stale-rootcause.md`'s "a few percent of frames" mechanism), not the catastrophic 74-82% rate that mechanism's one failing pose produces. Per the ruling, this does NOT invalidate the run; flagged here per the instrumentation requirement.

### Run B results

**STATUS: IN PROGRESS at the time this section was written** -- filled in below once the run resolves.

---

## Step 5: live episode (VM, ER-2)

**STATUS: PENDING.**

To be filled in after the run: the live model's verbatim decision (strategy,
`recede_axis`/`proposed_plan`, justification), gate/repair handling,
provenance, phase execution, arrival verification, STALE streaks, and API
spend (computed from logged token usage x published ER-2 price; stated
explicitly if the price cannot be sourced, not estimated from memory).

---

## Step 6: STALE instrumentation

**STATUS: PENDING** (applies to every run above; filled in alongside each
run's results).

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
