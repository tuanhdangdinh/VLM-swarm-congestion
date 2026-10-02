# Step 7a: Five IB10 Freeze-Blocker Fixes

**Prepared:** 2026-10-02

**Revision history:**

- Initial draft: all five fixes implemented and unit-pinned, local suite
  zero-delta confirmed, VM mock verification attempt 2 (attempt 1 was an
  infra-timing truncation) analyzed as a 0/4 design-level finding.
- Rev 2 (post-advisor-review): the attempt-2 "design-level finding" was
  wrong — it was this task's OWN bug. The release phase's `yield` action
  omitted `backup_distance_m`/`hold_sec`, so `command_bus_node` ran its
  default 0.3 m backup (an unrequested maneuver on an already-parked
  robot) and then skipped the hold/`CrossingChain` logic entirely
  (`hold_sec<=0`), releasing the held robots within ~35 s with no
  clearance wait at all. Fixed (`backup_distance_m: 0.0`, `hold_sec` set),
  re-verified locally, and re-run on the VM (attempt 3): 4/4 arrivals.
- Rev 3 (second advisor-review pass, same attempt-3 run, no further VM
  run): attempt 3's own criteria table first marked "ordered release"
  PASS on the strength of the 4/4 outcome alone. Re-reading the SAME
  attempt-3 logs more carefully shows that reading was also wrong: the
  release resolved via its sim-clock hold-timer backstop (clearance was
  structurally unreachable, since the lead never moved), and one held
  robot left independently through a pre-existing M4 race
  (`BaseMissionDriver` resuming a robot's base mission from a terminal
  status that arrived on an un-ordered topic, ahead of the next phase's
  own suppressing command) before the release's hold ever acted on it.
  4/4 stands as a fact (`ArrivalGate` confirms it); "ordered release"
  does not, and the criteria table and the attribution section below are
  corrected accordingly — this is the design-level finding for the
  coordinator.

**Commits:** branch `feat/v2-blockers`, worktree
`/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v2-fix`, branched from
`feat/prereg-v2-composite` at `d3aa0f3`. `1e6f628` (source, includes the
rev-2 release-command fix), `e54ad76` (test pins). No merge, no push.

---

## Scope and a base-branch discrepancy (read first)

Executes `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` build-order
step 7, scoped to the five freeze-blocking findings the 2026-10-02 IB10
composite smoke (`docs/reports/2026-10-02-ib10-composite-smoke.md`)
surfaced.

**Discrepancy, for the coordinator:** the task's setup command built this
worktree from `feat/prereg-v2-composite` (correct — that is where the real
`junction_clear` implementation and the composite-smoke report live). The
"STEP-6 OUTCOME ... FIVE FREEZE BLOCKERS" paragraph this task was told to
read verbatim, however, is committed only on `fix/deadlock-collision-
resolution` (commit `9c252e8`), a branch that diverged from
`feat/prereg-v2-composite`'s own common ancestor (`4307aa1`) with ONLY
eight documentation-only commits touching the design spec file — it has
none of the actual `junction_clear` code, the composite-smoke report, or
~100 other commits `feat/prereg-v2-composite` carries. The paragraph's own
content (five findings, each citing `docs/reports/2026-10-02-ib10-
composite-smoke.md`) is clearly describing `feat/prereg-v2-composite`'s
real state; it was evidently drafted on the wrong branch by an earlier
session. Read via `git show fix/deadlock-collision-resolution:docs/
superpowers/specs/2026-09-30-prereg-v2-design.md` for this task — confirmed
byte-identical in substance to the task's own five-fixes description — and
not ported into this branch's spec file (out of this task's scope; a
branch-hygiene fix, not a step-7a fix). Flagging so the coordinator can
reconcile the spec file's history separately.

---

## Fix 1: recede-set membership and order audit

**File:** `reasoning/rag/command_grounder.py` (`_plan_problems`, threading
`grounding_params` through `_repair_plan`/`verify_and_repair_plan`).

`_plan_problems`'s `junction_clear` block previously audited only the
RELATIVE POSITION of recede-vs-yield-axis legs ("recede before yield/
cross"). It never checked WHICH robots hold the recede legs, or the ORDER
between the two recede legs. Added:

- **Membership check:** any active leg with `action == "reverse"` whose
  robot is NOT a structural recede candidate (`_junction_recede_candidates`)
  is flagged; any structural candidate NOT given a `reverse` leg (including
  one lenient-completed to `continue`) is flagged.
- **Order check** (only once membership is clean): recomputes chi order via
  `rank_recede_candidates` on the SAME snapshot/`GroundingParams`
  `ground_junction_clear_phases` would use, and flags every recede leg if
  the proposed order disagrees — this is exactly run B's live bug (chi
  re-ranked the dispatch order opposite the VLM's own proposed order, which
  still verified `vlm_verbatim`).

**Pins:** `tests/unit/test_junction_clear_grounding.py::TestRecedeSetAudit`
(3 tests: correct plan stays `vlm_verbatim`; the wrong-pair plan is no
longer `vlm_verbatim`; a plan with both recede legs correctly membered but
in the wrong relative order becomes `repaired` via exactly one `reorder`
edit, reproducing run B's fix). `test_tagged_and_untagged_runs_ground_
identical_numbers_elsewhere` and the two loudness-guard yielder-lookup
tests updated to exclude the new `release` phase (added by fix 2) from
their `plan.phases[-1]` lookups.

**Parity check (confirmed, not assumed):** the order audit must rank with
the SAME chi weights `ground_junction_clear_phases` actually dispatches
with, or it polices a different ranking than the one that runs.
`InProcessPipeline.run` (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/
reasoning_pipeline.py`) calls `self._ground_fn(..., params=params,
snapshot=frame, geometry=self._scene_geometry, ...)` for the dispatch and
`verify_and_repair_plan(decision, frame, geometry=self._scene_geometry,
..., grounding_params=params)` for the audit a few lines later in the SAME
method, `params = self._grounding_params` — the identical object, not two
separately-constructed ones, and the identical `frame`. Confirmed by
reading both call sites together, not inferred.

### Sweep re-run (`scripts/junction_clear_repair_bound_sweep.py`)

Added one new case (`recede_order_swapped`, modeling run B's exact bug —
previously untested by this 17-case corpus, since every existing case's
chi order already matched list order). New distribution (18 cases):

| depth | cases |
|---|---|
| 0 (`vlm_verbatim`) | 1 (`plan_correct_verbatim`) |
| 0 (rejected pre-repair) | 4 (`inconsistent_strategy` x3, `plan_absent`) |
| 1 | 2 (`recede_order_swapped`, `order_yield_first_only`) |
| 2 | 3 |
| 3 | 4 |
| 4 | 1 (`missing_both_recede_candidates`) |
| 5 | 2 (`recede_pair_full_axis_swap`, `combined_wrong_pair_and_order`) |

**`max_repair_edits=2` does NOT still hold uniformly.** % falling to
`m3_default`, repairable cases only (excludes `inconsistent_strategy`/
`plan_absent`, always `m3_default` by contract): bound=1 → 11/14 (79%);
**bound=2 → 7/14 (50%)**; bound=3 → 3/14 (21%). Before this fix, bound=2
covered 100% of repairable cases — because membership defects were
invisible to the engine and verified `vlm_verbatim` at zero edits. The new
distribution is a direct, correct consequence of fixing the metric hole,
not a regression: the pure ORDER-only defect (`recede_order_swapped`) is
cheap (depth 1, a single `reorder`, exactly matching run B's own fix), but
MEMBERSHIP defects are expensive (depth 2–5) because `_repair_plan`'s
`_ops` never generates a `swap` touching a `yield`-holding position under
`yield_feasibility_mode="off"` (the shipped IB10 mode) — by design, to keep
the yielder-reassignment contract hard-closed under `"off"`/`"refuse"` — so
a full axis-swap membership defect can only be fixed by one `substitute`
per misassigned robot plus a `reorder`, not by a cheap pairwise swap.
**This is a new freeze-relevant finding for the coordinator**: whether to
raise `max_repair_edits` for `junction_clear` specifically, accept
`m3_default` for severe membership defects, or leave it as current
behavior (now correctly scored instead of silently over-credited) is a
coordinator call, not made here — consistent with the step-6 sweep's own
"report, don't change the default" discipline.

**Residual hole, reported not fixed, confirmed by running it (not just
read from the sweep table):** `missing_everything_but_one_reverse` (only
`robot_4` named, `robot_1`/`robot_2`/`robot_3` lenient-completed) repairs
at depth 1 to `[("robot_4","reverse"), ("robot_1","continue"),
("robot_2","continue"), ("robot_3","reverse")]` — but calling
`junction_clear_plan_matches_dispatch` on exactly these `repaired` legs
against the real `ground_junction_clear_phases` output for the same
decision/snapshot returns `False` (quoted from the actual call, not
inferred). So metrics (ii)/(iv) are NOT over-credited here — the hole is
scoped to cases that reach `vlm_verbatim`/`repaired` AND pass `dispatch_
matches_plan`; this one does not, so it is already caught by the existing
cross-check, not a new gap.

---

## Fix 2: ordered post-composite release

**Files:** `reasoning/rag/command_grounder.py`
(`ground_junction_clear_phases`, `junction_clear_plan_matches_dispatch`),
`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/junction_phase_queue.py`
(`JunctionPhaseReached` ordinal).

Root cause (traced from the composite-smoke report plus this task's own
code reading): the cross phase holds EVERY recede candidate via
`temporary_wait` in its own command; when that command resolves, EVERY
held robot's suppression (M4's `BaseMissionDriver`, keyed per command_id)
lapses together, releasing them all back to their base-mission goals at
once — on the IB10 geometry, both recede pockets sit on the IDENTICAL axis
coordinate (there is no lateral room to pass), so simultaneous release is a
fresh, unordered encounter on the same line the composite just cleared.

**Fix:** with 2+ recede candidates, `ground_junction_clear_phases` appends
one trailing `"release"` phase after `"cross"`. `ranked[0]` (chi-cheapest,
already first to recede) is addressed by NO action in this phase, so
nothing re-suppresses it — it resumes immediately. Every OTHER recede
candidate, plus the grounded yielder (`"the yielder re-enters last"`, per
(a) Sequencing), is held via a plain `yield` action naming `ranked[0]` as
`passer_robot_id` — reusing M4's existing odometry-gated `CrossingChain`
(`swarm_execution.crossing_chain`) UNCHANGED, never a fixed timer (which
would reproduce the exact bug: two identical waits release together
regardless of real clearance). Clearance is geometry-derived:
`2 * junction_recede_offset_m + params.min_distance_m` (IB10: 2.85 m) — far
enough that the lead has passed the second candidate's own pocket with the
safety-latch margin, reusing the SAME `recede_axis_offset_m` convention
`junction_recede_offset_m` itself uses, not a hardcoded constant.

**Scope limit, stated in the docstring:** one release stage only (correct
for IB10's 2-candidate case); a 3+-candidate scene would need a full N-way
chain, not built here.

**Implementation bug found by the VM run, fixed before the final
verification counted:** the first draft's release actions carried only
`passer_robot_id`/`passer_clear_m`, on the assumption that a `yield` action
with no backup/pull-off parameters is a passive hold. It is not.
`command_bus_node`'s `yield`/`reverse` branch unconditionally runs
`Nav2Adapter.backup(robot_id, distance_m, ...)` FIRST, where `distance_m =
params.get("backup_distance_m", 0.3)` — an unrequested 0.3 m backup on a
robot that is already correctly parked. Worse, `hold_sec = params.get(
"hold_sec", 0.0)`, and `_on_backup_result` only calls `_start_hold` (where
the `CrossingChain`/odometry-gated wait actually lives) when `hold_sec >
0`; left unset, the command published COMPLETED right after the (near-
instant) backup step, **never engaging the clearance wait at all**. The
VM's second attempt (below) is exactly this: a 0.3 m backup moved the held
robots away from their parked positions, the "hold" resolved in 35 s with
no relation to the lead's actual clearance, and the released robots
collided with the still-nearby lead. Fixed: the release action now sets
`"backup_distance_m": 0.0` (completes on the first odometry tick, no real
motion) and `"hold_sec": params.junction_recede_hold_sec` (the SAME
constant the recede phases already reuse as a `temporary_wait` `duration_
sec` for their OWN held robots — both are consumed by `create_timer`,
which runs on the NODE's clock, i.e. SIM time under this project's
standing `use_sim_time`, not wall time; M5's OWN, SEPARATE wall-clock
command-timeout tracking (`CommandTracker.check_timeouts`, `time.
monotonic()`) is a different backstop in a different layer. Still
reachable as a backstop even with this fix in place — see attempt 3
below, where it is in fact what ended the hold). Pinned:
`test_release_phase_actions_are_a_passive_hold_not_a_maneuver`.

**`junction_clear_plan_matches_dispatch` fix (needed for fix 2 to be
correct, not just cosmetic):** the function's per-phase projection
previously overwrote a robot's dispatched action with `project_dispatched_
legs`'s "continue" default whenever that robot was not `held` in a LATER
phase — which clobbered the chi-lead's REAL recede action with `"continue"`
the moment the new release phase (which addresses it with no command at
all) was reached. Fixed: a phase only contributes a robot's action when
that phase's command actually NAMES the robot.

**Pins:** `tests/unit/test_junction_phase_queue.py` (`test_completed_cross_
advances_to_the_staggered_release_phase`, `test_completed_release_resolves_
the_queue`), `tests/unit/test_m5_node_junction_clear.py`
(`TestOrdinaryPhaseAdvance`/`TestAttemptResolutionDeferred` updated for the
extra phase), `tests/unit/test_junction_clear_grounding.py`
(`test_release_phase_actions_are_a_passive_hold_not_a_maneuver`; phase-
label/count assertions updated)/`test_m5_reasoning_pipeline.py`
(phase-label/count assertions updated).

---

## Fix 3: cross-command continue-vs-reverse exemption (M4-adjacent)

**Files:** `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_
node.py` (`_with_plan_continue_partners`), `ros2_ws/src/swarm_execution/
swarm_execution/safety.py` (`plan_continue_partners_from_parameters`,
`admitted_partners`, `CoordinationTracker`).

Episode 1 decision 2's `proposed_plan` had `robot_1: continue` alongside
`robot_3`/`robot_4: reverse` in the SAME plan. `admitted_partners` only
exempts a `reverse` against the OTHER members of its OWN dispatched
command; a `continue` robot receives no command at all, so it is never a
`member` of anything — `robot_1` closed to within the 0.45 m latch of the
reversing `robot_4` and triggered a permanent safety stop.

**Smallest possible change:** there is no `plan_id` on the wire
`CoordinationCommand` message, so membership cannot be looked up
cross-command at the safety monitor. Instead, M5 (`_with_plan_continue_
partners`, called from `_publish_fanned_out` only for `action == "reverse"`
with a non-None `plan_id`) looks up the SAME tracked plan's OTHER
`continue` legs and writes them into the reverse leg's OWN
`parameters_json` as `plan_continue_partners`. `safety.py`'s
`admitted_partners` reads this as an ADDITIVE exemption, scoped to exactly
the named robots — never a blanket same-plan-or-wider exemption. Untouched
(byte-identical) when `plan_id` is None: the v1 (no-plan-channel) path.

**M4 protocol note:** this touches `ros2_ws/src/swarm_execution/
swarm_execution/safety.py`, a v1-frozen, safety-relevant file. The change
is additive-only (a new optional `plan_partners` parameter, defaulting to
empty, consulted only for a `reverse` action whose OWN parameters name it)
and is v2-branch-only; no v1 scenario's `CoordinationCommand` ever carries
`plan_continue_partners`, so no v1 exemption behavior changes. Recorded
here and in `docs/implementation_notes.md` per the task's instruction that
a safety-relevant M4 change needs a protocol note.

**Pins:** `tests/unit/test_safety_monitor.py`
(`test_no_plan_reverse_plus_an_uninvolved_robot_still_latches` — v1
regression pin; `test_reverse_exempts_a_same_plan_continue_partner`;
`test_reverse_does_not_exempt_an_other_plan_continue_robot` — pair-scope
discipline pin), `tests/unit/test_m5_node_plan_channel.py`
(`test_reverse_leg_carries_the_same_plans_continue_partner`;
`test_reverse_leg_without_a_tracked_plan_carries_no_continue_partners` —
flag-off/no-plan regression pin against the real node).

---

## Fix 4: reverse tracked-band bound

**Files:** `reasoning/rag/scene_geometry.py` (`SceneGeometry.
tracked_extent_m`), `reasoning/rag/command_grounder.py`
(`_clamp_reverse_distance_to_tracked_band`, wired into `_ground_legacy`'s
plain `reverse` branch).

Root cause, traced through both live episodes: the plain `reverse`
strategy's `backup_distance_m` is a fixed constant (1.3 m, unrelated to
current position). In both episodes, `robot_3` received this fixed backup
while ALREADY well outward on its own arm (mid-transit after the
composite's post-resolution release problem fix 2 addresses), landing at
`|y| = 2.38`/`2.42` — past the verified `|y| <= 1.75` M1 tracking extent,
at the SAME sim-time window both times.

**Fix:** new `SceneGeometry.tracked_extent_m` field (`None` default, every
existing scene byte-identical). `_clamp_reverse_distance_to_tracked_band`
clamps a `reverse` leg's distance, for a robot with a DECLARED arm only
(same precondition `junction_recede_offset_m` uses), so its post-backup
progress along its own arm (`maneuver_geometry.recede_axis_offset_m`, the
SAME convention `junction_recede_offset_m` itself is measured in) never
exceeds `tracked_extent_m`. IB10's goal-table comment updated to require
`tracked_extent_m: 1.75` alongside the existing J2 fields.

**Pins:** `tests/unit/test_command_grounder.py`
(`test_reverse_is_clamped_to_the_tracked_band_when_declared` — pinned
against episode 1's exact numbers, robot_3 at y=-1.13 backing up 1.3 m
would land at -2.43, clamped to stop exactly at -1.75;
`test_reverse_near_the_junction_is_not_clamped`; `test_reverse_not_clamped_
without_a_declared_tracked_extent`; `test_reverse_not_clamped_for_a_robot_
with_no_declared_arm`), `tests/unit/test_intersection_bottleneck_
scenario.py` (goal-table declaration pin + shipped-default-is-None pin).

---

## Fix 5: fallback-exhaustion semantics

**Files:** `reasoning/vlm/models.py` (`PlanLegStatus` += `"exhausted"`),
`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/plan_tracker.py`
(`_VALID_TRANSITIONS`), `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/
orchestrator_node.py` (`_mark_fallback_exhausted`, `_exhausted_robots`),
`reasoning/rag/plan_metrics.py` (`any_leg_exhausted`).

Episode 2's composite fallback (the documented plain-`yield` recovery)
itself failed for every robot. Before this fix, that outcome was
indistinguishable from an ordinary phase failure that a fallback still
follows — both routed to plain `failed`, and M5's detector would keep
re-triggering the identical, already-exhausted conflict indefinitely
(**advisor review correctly identified this re-trigger source as M2/M5's
own detector, not the phase queue, which already terminates correctly on a
failed fallback** — `JunctionPhaseQueue.on_resolved`'s fallback branch
already sets `done=True` unconditionally and is pinned never to retry;
confirmed unchanged).

**Fix:** `_resolve_command` detects the fallback's OWN terminal resolution
(`advance.phase_reached == "fallback" and advance.done`) being a failure
(`outcome_status != "completed"`) and calls `_mark_fallback_exhausted`,
which: logs loudly (`outcome=fallback_exhausted`, grep-able independent of
any artifact); re-routes every one of the fallback's robots' plan legs to
the new terminal `PlanLegStatus` `"exhausted"` (reachable from `pending`,
`active`, or `failed` — covering a robot that was simply held through
every phase and never individually resolved, the same precedent the
existing `pending -> failed` transition already set); and adds those
robots to `_exhausted_robots`, a PERMANENT (never time-expiring, unlike
`_cooldown`) set folded into `cooldown_robots` at every future trigger
check — reusing the EXISTING suppression gate (`state_machine.on_event`'s
`cooldown_robots | busy_robots` check) rather than inventing a new
directive kind. `any_leg_exhausted` (`plan_metrics.py`) is the "scorable
flag" building block: a pure function over a tracked plan's leg statuses,
matching this module's existing offline-scoring-building-block convention.
The leg status itself (not a new artifact field) is what makes the outcome
scorable going forward — `PlanStateContext`/decision artifacts already
serialize whatever `PlanLegStatus` a tracked leg carries.

**Pins:** `tests/unit/test_m5_plan_tracker.py` (`test_exhausted_is_
reachable_from_pending_active_or_failed`, `test_exhausted_is_terminal`,
`test_done_cannot_become_exhausted`), `tests/unit/test_plan_metrics.py`
(`TestAnyLegExhausted`, 3 tests), `tests/unit/test_m5_node_junction_clear.py`
(`TestFallbackExhaustion`: logged loudly, every leg marked `exhausted`, the
robots are never re-triggered again, and — regression pin — a fallback
that DOES recover is never marked `exhausted`).

---

## Local verification

Clean detached baseline at the branch point (`d3aa0f3`), fresh worktree
(not the scratchpad's shared `base`/`baseline` worktrees, per the review
note that a concurrent process had clobbered that scratchpad once):
**63 failed / 4384 passed / 152 skipped / 3 collection errors** (the five
`pxr`-only files reduced to three that actually fail to collect in this
environment; the local/container split documented elsewhere in this log).
After both commits on this branch (including the rev-2 release-command
fix and its new pin), re-run with the identical command:
**63 failed / 4413 passed / 152 skipped / 3 errors**, byte-identical
failing-test-name set to the baseline (`diff` confirmed empty). The +29
passing count is this task's own new/renamed pins. `ruff check` clean on
every touched file, confirmed a final time after the last fix.

---

## VM verification run (IB10, scripted `junction_clear`, mock)

**VM:** `vgu-vgu-thule-base-isaac-workstation-vm`. Preflight (every
attempt): idle confirmed (`pgrep -fl kit.exe`/`python3.*isaac` matched only
the invoking SSH shell itself — a self-match, not a real process; the
container's OWN `ps aux` showed no M1/M4/M5/Nav2 process), GPU 0%/171 MiB,
pristine md5 of `orchestrator.yaml`/`rag.yaml` confirmed on all four
copies (source + installed, host + container):
`1f656533a30a35882d57d0d64a57bd0d` / `e18c723cff9cada3f320d564c2ecee5a`,
backed up before each deploy. Deployed via `git archive HEAD` extracted
over the host tree (the `tar: ... Cannot utime` warnings on several
pre-existing, differently-owned directories are non-fatal — every file's
CONTENT verified landed correctly by `grep`-ing a marker string from each
fix, including files near the end of the archive). IB10's deployed
`orchestrator.yaml` (initial_tasks x4, `shadow_classical_zones`, junction
`corridor`+`arms`, `junction_recede_offset_m: 1.2`, `junction_backup_
clearance_m: 1.1`, the step-7a `tracked_extent_m: 1.75`,
`plan_channel_enabled: true`) built via a small script that loads the
shipped goal-table YAML, overlays exactly these keys, and verifies the
result through the REAL `swarm_orchestrator.models.load_config` path
before writing it out — confirmed locally first (the composite grounds to
the exact solved-row numbers: backup 0.799 m, retreat_x -1.018 m, escort
1.998 m). Rebuilt via `colcon build --merge-install --packages-select
swarm_orchestrator swarm_execution swarm_interfaces` (the standing
merged-install layout) after every deploy.

Three attempts were needed: the first was an infra-timing truncation, the
second surfaced the real implementation bug fix 2's own section above
describes (and was WRONGLY reported, in this report's first draft, as an
unfixable design limitation), and the third — after fixing that bug and
redeploying — is the valid result.

### Attempt 1: truncated (infra, not a result)

`REC_SEC=600 SIM_SEC=320`. GT recording stopped at sim 188 s because
`REC_SEC=600` under-covers this scenario's measured real-time factor
(~0.27-0.31, not close to 1x even for a zero-latency mock run — Isaac's
own physics/rendering overhead dominates), the same RTF-miscalibration
trap the live episode reports hit. Also found: the host Isaac process
outlived `fc-launch`'s own "killing Isaac" cleanup line by 10+ minutes,
consuming GPU the whole time — killed by hand, confirmed gone. Treated as
an infrastructure truncation under the project's one-re-run allowance.

### Attempt 2: complete, but exercising a real bug in this task's own code

`REC_SEC=1050 SIM_SEC=1100` (sized to the measured RTF). The full phase
sequence reached and resolved the new release phase, but the run ended
**0/4** — strictly worse than the composite-smoke report's own episode 2
(1/4). This report's first draft misread the trajectory evidence as an
unfixable design limitation (a 120 s hold-backstop releasing early, "M4's
reverse going the wrong way"). An advisor review of that draft caught
timestamp arithmetic that didn't support either claim and pointed at
`command_bus_node.py`'s `yield` branch directly — which is where the fix 2
section above's "implementation bug found by the VM run" actually was: the
release action's `yield` ran an unrequested 0.3 m backup (the robots
visibly moved) and never engaged the hold/`CrossingChain` logic at all
(`hold_sec` unset), so `robot_1`/`robot_3` were released within ~35 s with
no relation to `robot_4`'s real clearance, closed on the still-nearby
`robot_4`, and the scene converged to a persistent cluster
(`min_pairwise_distance_m = 0.118`) for the rest of the run. Fixed (see fix
2's section above) and re-verified locally before redeploying. This
attempt's own detailed trajectory numbers are superseded by this
correction and are not restated here; the bug and its fix are documented
once, in fix 2's own section.

**Also observed, independent of the bug, in both attempts 2 and 3**: the
two recede candidates ended up on the SAME side of the junction (close
together), not opposite declared sides. Traced in attempt 3 below to a
specific, pre-existing M4 mechanism, not left as an open question.

### Attempt 3: full sequence and 4/4, but the ordered release is NOT demonstrated

Same `REC_SEC=1050 SIM_SEC=1100`. The phase sequence completed
(`recede`(robot_3) -> `recede`(robot_4) -> `cross` -> `release` ->
`resolved done=True`, no fallback) and all four robots arrived
(`ArrivalGate`, read from `orchestrator_node`'s own log lines, not GT
distance alone: `robot_2 distance_m=0.06`, `robot_4 distance_m=0.07`,
`robot_3 distance_m=0.06`, `robot_1 distance_m=0.08`, all `check=within_
tolerance`). **But re-reading the SAME run's logs more carefully (an
advisor review caught this after the first pass of this section wrongly
marked "ordered release" PASS) shows the 4/4 was not reached through fix
2's designed gating.** Three findings, from the logs already collected
(no VM re-run):

1. **The lead did not move.** GT: `robot_3` (ranked[0], the chi-lead)
   stayed at speed 0.00-0.04 m/s from sim ~100 s to ~180 s, 0.076-0.15 m
   from `robot_4`. The release's `CrossingChain` (`passer_robot_id=
   robot_3`) requires 2.85 m of `robot_3`'s own odometry displacement to
   admit the held robots — structurally unreachable while `robot_3` is
   not moving.
2. **A held robot left anyway.** `/tmp/fc_20261002_160626_m4.log`:
   `resume base mission robot=robot_4 goal=(0.0, -1.75)` fires at wall
   `1790957587.891` — the SAME instant the cross phase resolves and the
   release command (which is supposed to hold `robot_4` via a `yield`
   naming `robot_3` as the passer) is dispatched. `robot_4` then arrives
   at its own goal at wall `1790958022.056` — BEFORE the release
   command's own COMPLETED status (`1790958039.438`). A robot genuinely
   held by a `yield` cannot independently drive ~3 m to its goal; `robot_
   4` escaped the hold via `BaseMissionDriver`'s own resume path, not
   through anything fix 2 dispatched.
3. **The release command's own 452 s duration matches the HOLD TIMER, not
   clearance.** `ACTIVE` at wall `1790957587.49`, `COMPLETED` at
   `1790958039.44` = 452 wall-s. This project's `create_timer` calls run
   on the node clock, which tracks `/clock` (sim time) under this
   project's standing `use_sim_time`; at this run's own measured RTF
   (~0.27, from the trigger's own `scene.stamp=34.2` and later decision
   stamps), 452 wall-s is ~122 sim-s — matching `hold_sec=junction_
   recede_hold_sec=120` almost exactly. The hold ended on the TIMER
   backstop this fix reuses, not on `_finish_hold("yield complete: passer
   cleared")` (which (1) shows could never have fired).

**Attribution — the same mechanism explains the same-side placement too.**
`BaseMissionDriver` resumes a robot's base mission on the terminal status
of whichever command currently "owns" it; `CoordinationTracker`'s own
module docstring states "Commands and statuses arrive on separate topics
with no cross-topic ordering guarantee." A later phase's new command
(e.g. the release's `yield`, meant to re-suppress `robot_4`) is not
guaranteed to land before `BaseMissionDriver` processes the PRIOR phase's
terminal status for the same robot and issues a fresh Nav2 goal. The SAME
race explains `robot_3`'s own recede landing it close to `robot_4`'s side
in the first place (both receded while repeatedly becoming briefly
"un-suppressed" at each intermediate phase boundary — `m4.log` shows
`resume base mission robot=robot_3` firing six times across the run, at
every phase transition `robot_3` is held through) — this single,
pre-existing M4 mechanism (a) produced the same-side placement fix 2's
clearance-distance derivation assumed would not happen (two pockets on
OPPOSITE sides, per the (a) Grounding geometry), (b) let a held robot
leave before fix 2's hold could gate it, and (c) made the 2.85 m
clearance target unreachable once the lead stopped moving. It is a
pre-existing M4 architecture property (not touched by, and not fixable
within, this task's five fixes) that this report did not identify
correctly on the first pass; the corrected attribution is the design-level
finding the task asked for.

**Criteria table (corrected):**

| Criterion | Result |
|---|---|
| Jam forms first | **PASS** — GT: all four robots within 1 m of the junction centre and stopped by sim 28.0 s, before this run's OWN trigger stamp (`scene.stamp=34.2` s, from decision artifact `fff3e18...`). |
| Full phase sequence executes (recede x2, cross, **release**) | **PASS** — all four phases dispatched and resolved `completed=True`, no fallback needed. |
| Ordered secondary release (fix 2's own criterion) | **FAIL — not demonstrated.** The release command resolved via its sim-clock hold-timer backstop, not via the `CrossingChain`'s real clearance tracking (unreachable, since the lead never moved); one held robot left independently through the pre-existing `BaseMissionDriver` race before the release's own hold could act on it at all. See the traced mechanism above. |
| 4/4 position-verified arrivals | **PASS, but not attributable to fix 2's ordering** — reached through the `BaseMissionDriver` race (item 2 above) plus the hold-timer backstop eventually releasing everyone else, not through genuine clearance-gated sequencing. |
| No tracked-band excursion | **PASS** — GT max `\|x\|`/`\|y\|` per robot over the whole run: `robot_1` (1.7501, 0.37), `robot_2` (1.7501, 0.03), `robot_3` (0.27, 1.7501), `robot_4` (0.35, 1.7501) — every extreme is the robot's OWN goal coordinate, never exceeded. The plain `reverse` strategy (fix 4's target) was never dispatched this run (the mock script never answers the secondary conflict with `reverse`), so fix 4 itself is not exercised by this run — confirmed separately by unit pins. |
| Safety during the close-parked window | **No physical contact recorded** — GT's own `robot_robot_contacts` field is empty for every row of the entire run, including the 0.0761 m minimum-separation row at sim 106.1 s. The safety monitor DID log many `min_distance_violation` stops through this window (14,910 lines over the whole run), consistent with `robot_3`/`robot_4` being mutually close but not necessarily in actual contact; not traced further to which specific pairs/exemptions produced each line. |
| STALE streak check | **FLAGGED, run not invalidated.** `robot_1`: longest streak 1 row (trivial). `robot_2`: 0. **`robot_3` and `robot_4`: a 275-row streak each, sim 101.2-183.2 s (~82 s)** — materially longer than any streak this program has recorded before (prior max 26 rows / ~6 s). Coincides exactly with the two recede candidates sitting parked 0.08-0.15 m apart (the `BaseMissionDriver`-race characteristic traced above) — plausibly an ArUco occlusion/confusion effect from two markers that close together, not traced further (M1 territory, out of scope). Per the resolved gate's own ruling, this does NOT invalidate the run: the streak is during a stationary, non-scored dwell, with no overlap with the trigger snapshot or either arrival. It IS a new data point for the registered instrumentation rule, reported here as required, and is materially bigger than prior observations — worth the coordinator's attention for whether the registered 1.65 m spawn-re-radius fallback should now be considered, still an owner call, not applied here. |

**This is the design-level finding for the coordinator** (the task's own
anticipated outcome: "if the ordered release STILL doesn't reach 4/4 ...
STOP there and report the trajectory evidence"; here the composite DID
reach 4/4, but not through the mechanism fix 2 built, which is the more
precise version of the same finding). Fix 2's own phase-level machinery
(the new `release` phase, its triggering, the geometry-derived clearance
distance, reusing `CrossingChain` unchanged) is implemented as specified
and is not what failed; what defeats it is a pre-existing M4 race between
two ROS2 topics with no ordering guarantee between them, which no
phase-based hold — not this one, and not the cross/recede phases' own
existing holds, which the SAME race evidently also perturbs — can fully
rely on without a change to `BaseMissionDriver`/`command_bus_node` or the
message contract between them. That change is out of this task's scope to
make.

### VM state: close-out

`orchestrator.yaml` restored from its pristine backup after EACH of the
three attempts (plain copy + `touch`, the documented colcon-mtime-skip
convention), `swarm_orchestrator` rebuilt each time, **all four copies
re-verified pristine** after the final attempt: source and installed
(host + container) `orchestrator.yaml` `1f656533a30a35882d57d0d64a57bd0d`,
`rag.yaml` `e18c723cff9cada3f320d564c2ecee5a` (never modified, re-confirmed
unchanged throughout). GPU idle (0%/171 MiB) and no stray Isaac/ROS2/Nav2
process after each attempt, including killing attempts 1 and 2's leftover
Isaac processes by hand (attempt 3 exited cleanly on its own). This task's
own `/tmp` artifacts removed after the final attempt (both deploy
archives, both pristine-backup directories, all three run logs, the small
GT-analysis scripts copied in for the criteria table); the three
pre-existing, unrelated `ship_*_delta.tar` files from Sep 30 left
untouched. The VM's source tree is left at this branch's final commit's
code (the intentional, expected side effect of deploying a real code
change, per the standing "whoever deploys next" shared-tree model this VM
has no `.git` directory to enforce otherwise) — only the two config files
are the standing-convention pristine-restore target.

---

## Mock API spend

Zero. Entire verification was `BACKEND_ID=mock`, all three attempts.
