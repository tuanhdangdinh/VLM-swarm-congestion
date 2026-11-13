# Safety Exemption Scope: Code Trace

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: code trace of five paths by which the M4 clearing exemption and A19 waivers reach further than intended, with test coverage and the owner ruling.

---

## Scope

- **Question.** While a robot executes a clearing command (`yield` or
  `reverse`), the M4 safety monitor exempts certain pairs from the
  min-distance and STALE-pair latches, and A19 waives pre-existing latches.
  Does that scope reach robots it should not?
- **Method.** Static code trace only, on `feat/v4-per-cluster-parity` at
  fdf333d. Every file:line was re-derived on that tree. Nothing was run live:
  no VM, no simulation, no API. The three related unit-test files were run
  offline to confirm the current behaviour (225 passed in 0.46 s). Several of
  those tests assert the wider scope as correct.
- **Evidence grade:** code reading. No incident in a recorded run has been
  attributed to these paths. In every recent live cell, the 0.20 m
  hard-contact floor was armed as a backstop (Stage 1: 0 floor stops, GT
  minimum 0.2151 m).
- **Owner ruling (2026-11-13):** fix and test before any additional live
  experiment. The fix for paths 1-3 is assigned to branch
  `fix/safety-exemption-scope` (worktree `vgu-vlm-swarm-v7c`). It is in
  progress and uncommitted. When this report was committed, the branch had no
  commits beyond its base 68e67b5. The worktree had uncommitted edits to
  `safety.py` and `safety_monitor_node.py`, plus new untracked files
  `tests/unit/test_safety_exemption_scope.py` and
  `config/safety/scoped_clearing_exemption.fragment.yaml`. They were not
  reviewed here.

---

## Data Flow

1. **M5 computes partners.** `orchestrator_node._publish_fanned_out`
   (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py`
   1850) passes every `reverse` leg through `_with_plan_continue_partners`
   (1909-1980; call at 1892-1893). That writes `plan_continue_partners` into
   the leg's `parameters_json`.
2. **Transport.** `/coordination/commands` (`CoordinationCommand.parameters_json`)
   and per-robot statuses on `/coordination/status`. The wire message has no
   `plan_id`.
3. **M4 records.** `safety_monitor_node._on_coord_command` (171) calls
   `CoordinationTracker.record_command` (`ros2_ws/src/swarm_execution/swarm_execution/safety.py`
   397), and `_on_coord_status` (192) calls `record_status` (448).
4. **Per scene tick** (`_on_scene_state`, 215): `capture_latch_partners`
   (558), `exemption()` (517, which calls `admitted_partners` 186 for each
   clearing robot), `evaluate_latches` (699) with `_proximity_violations`
   (670), then `release_separated_waivers` (607).
5. **End.** The exemption exists only while the robot's own clearing command
   is active. A terminal status removes the robot's action, backup phase and
   waiver.

---

## The Five Paths

### Path 1: Plan-continue partners cross clusters (bug)

- **Mechanism.** `_with_plan_continue_partners` (1909-1980) takes the
  plan's `continue` legs that are also in `_trigger_robots_by_plan[plan_id]`
  (read at 1968, filter 1969-1975). That set is written at `_dispatch` (1792)
  from `_last_trigger_robot_ids` (handoff at 1328), which is the event's
  `involved_robots`. `CongestionDetector.update`
  (`congestion_detector.py` 57) sets `involved_robots=sorted(stalled)` (126):
  every stalled robot in the scene, with no cluster grouping. M4 adds the
  list through `plan_continue_partners_from_parameters` (safety.py 134) into
  `admitted_partners` (`extra`, 234-247).
- **Effect.** When two separate conflicts stall in the same detector tick, a
  `reverse` in one cluster is exempt against the stalled `continue` robots of
  the other cluster for the whole reverse.
- **Already noted** in `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md`
  ("A cross-group exemption exists today"). Its line references
  (`orchestrator_node.py:1648-1665`) are stale at fdf333d.
- **Tests.** `tests/unit/test_m5_node_plan_channel.py`:
  - `test_reverse_leg_carries_the_same_plans_continue_partner` (246);
  - `test_manual_trigger_reverse_gets_no_plan_continue_partners` (296);
  - `test_plan_continue_partners_narrowed_to_the_triggering_event_not_the_whole_scene`
    (333; the trigger set is hand-set to one group);
  - `test_plan_continue_partners_empty_when_the_plan_channel_tracks_no_plan` (373).

  `tests/unit/test_safety_monitor.py`:
  - `test_reverse_exempts_a_same_plan_continue_partner` (1120);
  - `test_reverse_does_not_exempt_an_other_plan_continue_robot` (1136).

  **Not covered:** a trigger event spanning two separate groups.

### Path 2: Stale partner lists (exists, narrower than first framed)

The robot's own exemption does end with its command. What goes stale is the
partner side:

- **(a) Hold overwrite.** On a plan hold the same `plan_id` returns, and
  `_dispatch` (1792) overwrites `_trigger_robots_by_plan[plan_id]` with a
  later event's set. That dict is declared at 577 and never evicted. A
  pending `junction_clear` later phase of the earlier command reuses the
  `plan_id` and narrows against the new set. This is inferred from code; no
  test covers it.
- **(b) Frozen at publish.** `plan_continue_partners` is fixed when the
  reverse is published and held in M4 for the command's lifetime
  (`record_command` 420-427). A `continue` robot has no command, so it is not
  in `_busy_robots` (2836) and can be given a new command while it is still
  exempt against the reverser.
- **(c) Membership never shrinks.** `record_status` does not drop a member
  whose leg ended, and `admitted_partners` for a reverse ignores `completed`.
  This is deliberate (`docs/specs/module4/safety-monitor.md` §10) and pinned
  by `test_passer_stays_partner_after_it_takes_a_new_command`
  (test_safety_monitor.py 1073).
- **(d) Missed terminal status.** There is no timeout. An active entry lives
  until 256-command eviction (`record_command` 441-446). This is a residual
  risk, not observed.

**Tests:**
- `test_safety_monitor.py`: `test_exempt_robots_clear_when_command_completes`
  (750), `test_tracker_bounds_commands_without_terminal_status` (769),
  `test_exemption_ends_when_yield_completes` (1189).
- `test_m5_node_plan_channel.py`: `test_last_trigger_robot_ids_cleared_after_dispatch`
  (394), `test_junction_phase2_reverse_still_gets_plan_continue_partners` (412).
- `tests/unit/test_a19_exemption_scope.py`: `test_capture_is_frozen_at_command_start`
  (292), `test_a_new_command_recaptures` (358).

**Not covered:** (a), (b) and (d). (c) is covered only as intended behaviour.

### Path 3: Busy robot counted as a member (bug)

- **Mechanism.** M5's busy gate tests only the event's trigger set
  (`state_machine.py` 103-105). The decision can address any robot in the
  snapshot, and no busy filter runs at dispatch. The M4 command bus
  busy-rejects that robot (`command_bus_node._on_command` 114, `robot busy`
  at 135). But the safety monitor had already added it as a member
  (`record_command` 429-432), and the FAILED status does not remove it.
- **Effect.** The new command's clearing robot is exempt against a robot that
  is executing a different command, possibly under Nav2, for the clearing
  robot's whole command.
- **Tests.** `test_busy_rejected_earlier_passer_does_not_admit_later_passer`
  (test_safety_monitor.py 1178) asserts the pair is still exempt after the
  busy-reject. That pins the wide membership; the test's purpose is
  later-passer admission. **Not covered:** a busy-rejected member losing
  partner status.

### Path 4: Mutual A19 waivers (bug)

- **Mechanism.** `capture_latch_partners` (safety.py 558-605) excludes only
  the clearing robot's own command robots (`own`, 589-594). A waived pair
  stays in `latched_pairs`. If its partner later starts its own clearing
  command, or two latched robots start clearing commands on different
  commands, both sides waive each other. `_proximity_violations` (682-685)
  and the STALE pair rule (825-827) then hold neither robot. The STALE
  keep-latch is lifted for clearing robots (831-833). The waiver lasts until
  the pair separates (`release_separated_waivers`).
- **Backstop.** Only the hard-contact floor (786-798) remains. It is 0.0 (off)
  in `ros2_ws/src/swarm_execution/config/safety.yaml:26`, and on (0.20 m) only
  through the `config/safety/safety_floor020.yaml` swap used in the recent
  live cells.
- **Tests.** `test_a19_exemption_scope.py` 281-448, including
  `test_waiver_is_one_sided_in_the_proximity_rule` (406) and
  `test_stale_pair_rule_is_one_sided_for_a_waived_pair` (448), all with a
  single clearing robot. **Not covered:** two clearing robots that waive each
  other.

### Path 5: Own-command scope (by design)

- **Mechanism.** `admitted_partners` (186-247): a reverse or orderless yield
  pairs with all its own command's members. An ordered yield admits passers
  progressively, or all members while backing up. Shield-only members are
  removed (A27(i)). `CLEARING_ACTIONS` is `{yield, reverse}` (safety.py 43).
- **Why it is intended.** Clearing primitives must work inside
  `min_distance_m`. Bystanders outside the command stay protected. This is
  documented in `docs/specs/module4/safety-monitor.md` §10 and in the
  safety.py 33-43 rationale, and pinned by many `test_safety_monitor.py` tests
  (for example `test_two_robot_pair_scope_matches_robot_scope`, 1430).

---

## Summary Table

| Path | Status | Live impact recorded | Test for the widened case |
|---|---|---|---|
| 1. Cross-cluster plan-continue partners | bug | none attributed | none |
| 2. Stale partner lists (a, b, d) | bug / risk | none attributed | none ((c) pinned as intended) |
| 3. Busy-robot membership | bug | none attributed | none (a test pins the wide behaviour) |
| 4. Mutual A19 waivers | bug | none attributed | none |
| 5. Own-command scope | by design | n/a | covered |

---

## What Was Not Done

- No run reproduces any path, live or in a node-level test.
- No fix is made here. The owner ruling assigns paths 1-3 to
  `fix/safety-exemption-scope`. Path 4 is not in that assignment as recorded
  in the brief, and needs an owner decision.
- Recorded bundles were not searched for occurrences. Whether any past episode
  hit paths 1-4 is unknown.

---

## References

- M4 spec: `docs/specs/module4/safety-monitor.md` §10.
- A19 design: `docs/implementation_notes.md` (A19 entry, M4 section).
- Per-cluster design note (path 1): `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md`.
