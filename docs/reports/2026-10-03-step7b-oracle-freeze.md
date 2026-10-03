# Step 7b: Race Guard, Bound Freeze, Stagger, IB10 Oracle

**Prepared:** 2026-10-03

**Revision history:**

- Initial draft: rulings (i)-(v) landed and pinned, the IB10 resolution
  oracle and regret extension built, one scripted IB10 mock rerun on the
  final runtime code. The rerun FAILS 4/4 (2/4) on a new design-level
  release-sequencing finding, reported here for a ruling; no fix attempted.

---

## Summary

Executes build-order step 7 of
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, the STEP-7a
OUTCOME rulings (i)-(v), on branch `feat/v2-step7b` (cut from
`feat/prereg-v2-composite` at `cf368ec`).

| Ruling | Outcome |
|---|---|
| (i) race guard | Landed in `base_mission.py` + `coordination_client_node.py`, **not** `command_bus_node.py` (file deviation, below). Live-verified: 36 `race guard:` lines in the rerun, zero same-arm parking. |
| (ii) repair bound | Re-swept bounds 1-4 on the full 18-case corpus. No bound reaches full coverage; frozen at **3** with a three-case documented tail. |
| (iii) gate logging | Sim-stamped `crossing_chain gate_admit/gate_cleared/gate_release` lines with `reason=clearance\|hold_timer`. Live-verified: release attribution decidable. |
| (iv) 82 s STALE streak | Pair separation 0.076-0.144 m (< 0.6), race-caused. Staggered pockets implemented (second candidate 1.0 m, lead 1.2 m). Rerun: no streak (max 5 rows / 1.37 s); the lead parks 0.69 m from the second pocket instead of 0.45 m, no latch between them. |
| (v) trigger staleness | `_last_trigger_robot_ids` cleared after each dispatch; later junction phases read a plan-bound copy. |
| Part 3 | IB10 oracle block + `coverage_scene_scores.py ib10` + `JunctionOracleConfig`; regret arms registered. IB10 scoring frozen (section below). |
| Rerun (Part 2) | **FAIL: 2/4.** Full composite reached `resolved`, ordered release attributable (both held robots `reason=clearance` at sim 139.967), no band excursion, no STALE streak. But the release frees the second receder and the yielder **on the same gate at the same instant**, onto crossing paths; they latch for good 3 s later (0.416 m). **Design-level: STOP.** |

---

## Ruling (i): race guard

**File deviation.** The spec names `command_bus_node.py`. Step 7a traced
the race to `BaseMissionDriver`
(`ros2_ws/src/swarm_execution/swarm_execution/base_mission.py`) and its
node, `coordination_client_node.py`: a successor command seen before the
predecessor's terminal status let that terminal free the robot. The guard
therefore lives there (commits `372b698`, `cdf18b5`). A terminal status
releases a robot only when its `command_id` matches the robot's
suppression owner. A stale terminal is logged and ignored; a superseded
terminal promotes the already-seen successor. M4 protocol note:
`docs/implementation_notes.md` M4 section, 2026-10-03.

Pins (`tests/unit/test_base_mission.py`):
`test_v1_single_command_path_is_byte_identical`,
`test_7a_race_successor_seen_before_predecessor_terminal_is_not_freed`,
`test_race_successor_terminal_arrives_before_predecessor_terminal`,
`test_three_command_phase_chain_recede_cross_release`,
`test_genuine_busy_reject_terminal_still_does_not_free_the_owner`,
`test_command_terminal_seen_before_its_own_on_command_is_not_stranded`,
`test_redelivered_on_command_for_an_already_resolved_pending_is_discarded`.

Live evidence (rerun `fc_run_20261003_022532`, `m4.log`): 31
`race guard: stale terminal ignored` and 5 `race guard: superseded terminal
ignored ... promoted_to=<req>-junction-cross` lines. Every recede robot
reached its own pocket on its own arm (GT: robot_4 (0.00, 1.21), robot_3
(0.01, -1.01)).

---

## Ruling (ii): repair-bound freeze

`scripts/junction_clear_repair_bound_sweep.py`, `CANDIDATE_BOUNDS =
(1, 2, 3, 4)`, full 18-case corpus including `recede_order_swapped`:

| Case | Category | Min depth | b=1 | b=2 | b=3 | b=4 |
|---|---|---|---|---|---|---|
| recede_pair_full_axis_swap | wrong_recede_pair | 5 | m3 | m3 | m3 | m3 |
| recede_pair_one_wrong_robot1 | wrong_recede_pair | 3 | m3 | m3 | rep | rep |
| recede_pair_one_wrong_robot2 | wrong_recede_pair | 2 | m3 | rep | rep | rep |
| order_fully_reversed | wrong_order | 2 | m3 | rep | rep | rep |
| order_yield_first_only | wrong_order | 2 | m3 | rep | rep | rep |
| order_cross_before_recede | wrong_order | 3 | m3 | m3 | rep | rep |
| recede_order_swapped | wrong_recede_order | 1 | rep | rep | rep | rep |
| missing_one_recede_candidate | missing_legs | 3 | m3 | m3 | rep | rep |
| missing_yielder | missing_legs | 2 | m3 | rep | rep | rep |
| missing_both_recede_candidates | missing_legs | 4 | m3 | m3 | m3 | rep |
| missing_everything_but_one_reverse | missing_legs | 1 | rep | rep | rep | rep |
| combined_wrong_pair_and_order | combined | 5 | m3 | m3 | m3 | m3 |
| combined_missing_leg_and_wrong_order | combined | 3 | m3 | m3 | rep | rep |
| inconsistent_all_continue / _wait / _cross | inconsistent | n/a | m3 | m3 | m3 | m3 |
| plan_absent | control | n/a | m3 | m3 | m3 | m3 |
| plan_correct_verbatim | control | 0 | verb | verb | verb | verb |

Repairable cases falling to `m3_default`: 11/14 (b=1), 7/14 (b=2), 3/14
(b=3), 2/14 (b=4). No bound reaches full coverage (two depth-5 cases at
every bound), so the ruling's fallback applies: **frozen at 3**
(`PlanRepairParams.max_repair_edits`, commit `8071f8a`). The documented
m3_default-by-design tail is `recede_pair_full_axis_swap` (5),
`combined_wrong_pair_and_order` (5) and `missing_both_recede_candidates`
(4). Pins: `test_default_bound_is_frozen_at_three`
(`test_plan_verifier.py`),
`test_missing_both_recede_candidates_falls_to_m3_default_at_the_frozen_bound`
and the `repair_bound_exceeded` assertion on the full-axis-swap case
(`test_junction_clear_grounding.py`). The bound is global; raising it only
makes more plans repairable, and every step-4 swap-gate repair costs one
edit.

---

## Ruling (iii): sim-stamped gate events

`command_bus_node.py` logs `crossing_chain gate_admit`, `gate_cleared`
(with `moved_m`/`clear_m`) and `gate_release` (`reason=clearance` or
`reason=hold_timer`), state transitions only, stamped with sim time
(commit `b37ba57`). Pins (`test_command_bus_node.py`):
`test_gate_events_log_admit_cleared_and_clearance_release`,
`test_gate_release_logs_hold_timer_reason_when_passer_never_clears`,
`test_gate_release_reason_distinguishes_clearance_from_hold_timer_single_passer`.

---

## Ruling (iv): the 82 s STALE streak and staggered pockets

**Attempt-3 mechanism (GT, sim 101.2-183.2).** The parked pair was
robot_3 and robot_4, 0.076-0.144 m apart (median 0.079), both on the
**south** arm near y = -0.9. robot_4 never receded north: the race let its
base mission resume through the junction (GT y = +0.23 at 45 s to -0.74 at
55 s), and the release later drove robot_3 north into it head-on. The
designed pockets sit 2.4 m apart on opposite arms, so this streak was a
race artifact, not a pocket-geometry one.

**The race-free endgame (predecessor's rerun `fc_run_20261002_191845`,
code `cdf18b5`, no stagger).** With the race fixed, the pockets were
reached correctly (robot_4 +1.21, robot_3 -1.21), but the run ended
**3/4**. The lead robot_4, released first, drives to its goal on the
second candidate's arm and parked at (0.08, -1.65), **0.45 m** behind
robot_3's pocket (0.01, -1.21), exactly `min_distance_m`. The pair latched
for good (permanent `min_distance_violation` on robot_3/robot_4, M5
suppressing the trigger). That run's STALE check was already clean (max 2
rows): the race guard alone removed the 82 s streak.

**Stagger (commit `7070813`).** Separation < 0.6 m, so the ruling's
stagger branch applies, designed against that endgame:

- New `SceneGeometry.junction_recede_stagger_m` (None default:
  byte-identical). The k-th candidate in chi order recedes to
  `junction_recede_offset_m - k * stagger`
  (`maneuver_geometry.recede_pocket_offset_m`). Offsets are assigned after
  ranking; chi always measures the unstaggered offset, so the lead never
  changes.
- Release clearance becomes lead pocket + second pocket + `min_distance_m`
  (2.85 m unstaggered, unchanged; 2.65 m at IB10's stagger).
- IB10 value 0.2 (second pocket 1.0 m). Window: the lead stops ~0.10 m
  short of its 1.75 goal, so `1.65 - p >= 0.6` (the STALE band) gives
  p <= 1.05. The S1 study's h window (worst-lane yielder return >= 0.55 m)
  gives p >= ~1.0. 1.0 is the only round value in [1.0, 1.05].

Pins: `TestStaggeredRecedePockets` (10 tests,
`test_junction_clear_grounding.py`),
`test_goal_table_declares_the_step_7b_recede_stagger` and
`test_staggered_second_pocket_clears_the_lead_goal_and_the_yielder_return`
(`test_intersection_bottleneck_scenario.py`), plus
`strategy_regret.preflight`'s field check.

**Rerun result.** robot_3 parked at (0.01, -1.01). The lead arrived at
(0.05, -1.69), 0.69 m from that pocket (vs 0.45 m unstaggered). There was
no robot_3/robot_4 latch: robot_3 was released as the lead cleared and
drove away north.
STALE: longest streak robot_1 5 rows / 1.37 s, robot_3 3 rows / 0.50 s,
robot_2/robot_4 0. **No long STALE streak.**

---

## Ruling (v): trigger staleness

`_last_trigger_robot_ids` is cleared at the end of every `_handle_outcome`.
The junction's later phases read `_trigger_robots_by_plan[plan_id]`,
captured at dispatch (commit `d685cc9`). Pins:
`test_last_trigger_robot_ids_cleared_after_dispatch`,
`test_junction_phase2_reverse_still_gets_plan_continue_partners`.

---

## VM rerun (Part 2)

**Deploy.** `git archive 7070813` extracted with `tar -m` (fresh mtimes,
so colcon never skips a file), IB10 overlay (the step-7a key set plus
`junction_recede_stagger_m: 0.2`) checked through the real
`load_config`, `colcon build --merge-install` of swarm_orchestrator,
swarm_execution and swarm_interfaces. Manifest: all 741 tracked files
md5-match local `7070813` except the intentionally overlaid
`orchestrator.yaml`. Every installed `swarm_orchestrator`/`swarm_execution`
module matches its source. Pristine configs backed up first (md5
`1f656533...`/`e18c723c...`).

**Run.** `fc_run_20261003_022532`, mock
`intersection_junction_clear_vlm_verbatim_once.json`, `REC_SEC=1050
SIM_SEC=1100`, `logs saved to` gate present (`fc_rc=141`, SIGPIPE inside
the launcher's own cleanup, after logs were saved). A first launch attempt
two minutes earlier aborted before Isaac started (run as `ubuntu`, not
root, so the `sed` backend switch could not write the root-owned config
dir). That was infrastructure, not a result.

**Score (`coverage_scene_scores.py ib10`):**

| Criterion | Result |
|---|---|
| Formed-jam gate | valid: onset 26.6 s (window 8-40), longest 16.7 s, 4/4 in radius |
| chi-pair | chi order [robot_4, robot_3]; proposed and executed both correct; provenance `vlm_verbatim`; yielder robot_1 |
| Inside-first | True: robot_2 crosses at 77.0 s, robot_4 at 130.1 s |
| Phase reached | `resolved` (ordinal 4), no fallback, not exhausted |
| Ordered release | **decidable, by clearance** (gate lines below) |
| Arrivals | **2/4**: robot_2 75.7 s, robot_4 122.8 s after t0; robot_1 and robot_3 never |
| Tracked band | in band (max \|y\| 1.750 at robot_4's spawn) |
| STALE | no long streak (above) |
| `resolved` | **False** |

Gate log, quoted (`m4.log`, request id elided as `<req>`):

```text
crossing_chain gate_admit command=<req>-junction-cross yielder=robot_1 passer=robot_2 clear_m=1.931 escort_m=1.931 sim_t=73.833
crossing_chain gate_cleared command=<req>-junction-cross yielder=robot_1 passer=robot_2 moved_m=1.933 clear_m=1.931 sim_t=95.800
crossing_chain gate_release command=<req>-junction-cross yielder=robot_1 reason=clearance sim_t=95.800
crossing_chain gate_admit command=<req>-junction-release yielder=robot_3 passer=robot_4 clear_m=2.650 escort_m=None sim_t=95.867
crossing_chain gate_admit command=<req>-junction-release yielder=robot_1 passer=robot_4 clear_m=2.650 escort_m=None sim_t=95.867
crossing_chain gate_cleared command=<req>-junction-release yielder=robot_3 passer=robot_4 moved_m=2.653 clear_m=2.650 sim_t=139.967
crossing_chain gate_release command=<req>-junction-release yielder=robot_3 reason=clearance sim_t=139.967
crossing_chain gate_cleared command=<req>-junction-release yielder=robot_1 passer=robot_4 moved_m=2.653 clear_m=2.650 sim_t=139.967
crossing_chain gate_release command=<req>-junction-release yielder=robot_1 reason=clearance sim_t=139.967
```

M5 phase sequence: `phase_reached=recede` → `cross` → `release` →
`resolved done=True`.

### Design-level finding: the release frees two robots onto crossing paths

At sim 139.967 the release gate frees **both** held robots at once:
robot_3 (second receder, heading north from (0.007, -0.978)) and robot_1
(the yielder, heading east from (-0.985, -0.408)). Their paths cross just
south-west of the junction centre. At 143.0 s they are inside 0.45 m. The
monitor latches both (`min_distance_violation`, robot_1 and robot_3 only,
to the end). They stay frozen at (-0.50, -0.40) and (-0.10, -0.50),
0.416 m apart, from 145 s to the end (285.9 s); GT records zero contacts.
M5 then suppresses re-triggers for robot_1/robot_3, and the once-mock
answers `none` anyway.

The cause is structural, not a tuning slip. Step 7a's fix 2 gates every
non-lead receder **and** the yielder on the same passer (the lead), so they
release together. The spec's sequencing says "the yielder re-enters last"
((a) Grounding, Sequencing). The release phase does not implement that
"last" relative to the second receder. With the race fixed and the pockets
staggered, this is the first time the two have actually been released
together from their designed positions. In attempt 3, robot_4's race exit
masked it.

Candidate fix (NOT applied; needs a ruling, since it changes the release
sequencing 7a designed). Use M4's existing ordered multi-passer path, which
the spec says to reuse (`crossing_chain.py`: `plan_crossing` reads
`crossing_order`/`crossing_clear_m`; `CrossingChain` admits one passer at a
time; `command_bus_node._release_wait` releases each later passer's linked
`temporary_wait` only when its predecessor clears). The release command
would carry one `yield` for the yielder with `passer_robot_id` = lead,
`crossing_order` = [lead, second] and per-passer clearances. The second
receder would be held by a linked `temporary_wait` instead of its own
`yield`. Order: lead, then second receder, then yielder. This is an M3-only
change to `ground_junction_clear_phases` with M4 unchanged. A second VM
rerun would be needed after the ruling.

Also observed, not a blocker: the lead stalled at (0.25, 0.20) for ~22 sim
s (105-127 s) before passing robot_3 at 0.34 m (exempt pair, same release
command). The predecessor's rerun shows the same stall at (0.36, 0.44).

---

## IB10 scoring frozen

Oracle: `isaac/config/scenarios/intersection_bottleneck.yaml` `oracle:`
(schema `isaac/vgu_sim/config.py::JunctionOracleConfig`, additive in the
`ScenarioConfig.oracle` union). Scorer: `scripts/coverage_scene_scores.py
ib10` (`score_ib10`). Regret: `scripts/strategy_regret.py`
`SCENES["intersection_bottleneck"]`. Every criterion, its definition and
its pin:

| # | Criterion | Definition | Implementation | Pins |
|---|---|---|---|---|
| 1 | Formed-jam validity gate | `intersection_conflict_active` over GT; onset in `expected_conflict.onset_window_sec` [8, 40]; longest interval >= 2.0 s; >= `jam_robots_in_radius` (4) robots within 1.0 m at onset. Failing it makes the run INVALID (`resolved: None`), not failed. | `formed_jam` | `TestIb10FormedJam` (3) |
| 2 | chi-pair correctness | recede set = `reverse` legs; `pair_correct`: set == `recede_pair` [robot_3, robot_4]; `order_correct`: order == chi order recomputed at the dispatched decision's snapshot (`rank_recede_candidates`, rag.yaml weights). Scored on the proposed plan (pre-repair, None if token-only) and the executed plan; provenance reported beside it. | `score_chi_pair`, `chi_order`, `dispatched_junction_decision` | `TestIb10ChiPair` (5) |
| 3 | Inside-first order | GT final junction-centre crossing on each robot's travel axis. True iff every `inside_pair` robot except the grounded yielder crosses, and every recede robot that crosses does so later. None if an inside robot never crosses. `yielder_last` is reported but **contingent on the release ruling**: today's release frees the yielder and the second receder together, which is the defect above. If the yielder is chained last, that order becomes deterministic and `yielder_last` is a candidate oracle criterion again. | `score_inside_first`, `junction_crossing` | `TestIb10InsideFirst` (3) |
| 4 | Phase-reached ordinal | none 0 < recede 1 < cross 2 < release 3 < resolved 4, from M5 `dispatch ... -junction-recede-` and `phase advance ... phase_reached=` lines. **Open item:** this is M5's own phase label, and `resolved` means the release command completed, not that robots arrived. This rerun scored ordinal 4 with 2/4 arrivals, the same partial score as a full success. Options for the coordinator: require all arrivals for ordinal 4, or keep the label and score success only via criterion 6. Not changed here. | `phase_reached` | `TestIb10PhaseReached` (4) |
| 5 | `fallback` / `fallback_exhausted` | flags: a `phase_reached=fallback` advance; M5's `outcome=fallback_exhausted`. | `phase_reached` | `test_fallback_keeps_the_last_phase_and_flags_exhaustion` |
| 6 | Arrivals (episode success) | `score_ground_truth`'s rule (within 0.35 m, never beyond 0.5 m after); `resolved` = gate valid AND all four arrived. | `score_ib10` | `test_designed_order_is_inside_first_with_the_yielder_last` |
| 7 | Ordered-release attribution | `-junction-release` gate events; `ordered_release` True iff every held robot's `gate_release` has `reason=clearance`. | `release_attribution` | `TestIb10ReleaseAttribution` (3) |
| 8 | Tracked band | max \|x\| <= 2.5, \|y\| <= 1.80 per robot after t0. | `tracked_band` | `test_an_excursion_past_the_tracked_band_is_flagged` |
| 9 | STALE instrumentation | longest STALE streak per robot (rows, scene-stamp span) from the M5 scene log; reported, per the step-6 gate ruling. | `stale_streaks` | `test_stale_streak_rows_and_span` |
| 10 | Regret | `junction_clear`-forced (`intersection_junction_clear_vlm_verbatim_once.json`) vs `best_single_yield`-forced (`intersection_yield_once.json`). The single-yield arm is censored by construction (v1 T1-X), so its regret is a lower bound (`regret_is_lower_bound`, T2b semantics). The oracle block's `margin:` stays pending the forced-arm sweep. | `SCENES["intersection_bottleneck"]`, `cost_table`, `score_regret`, `preflight` | `TestIntersectionBottleneck` (4) |

Schema pins: `test_t1_carries_only_the_v2_junction_oracle_and_no_scene_objects`,
`TestIb10OracleBlock`.

---

## Verification

Full local suite, `pytest -q --continue-on-collection-errors`. The clean
detached baseline is at the branch point `cf368ec`
(`scratchpad/step7b/baseline_cf368ec`): 63 failed / 4416 passed / 152
skipped / 3 collection errors. At `aefbecb`: 63 failed / 4472 passed / 152
skipped / 3 errors. The failing-name set is identical (`diff` empty). The
63 failures are pre-existing environment ones (`pxr`/USD, API key, ArUco
parity); +56 passes are this branch's new pins.

## VM state

Pristine `orchestrator.yaml` restored (plain copy + `touch`), rebuilt, and
re-verified on source and installed copies, with `rag.yaml` never
modified: `1f656533a30a35882d57d0d64a57bd0d` /
`e18c723cff9cada3f320d564c2ecee5a`. No Isaac, Kit or `run_simulation`
process remains, the GPU is idle (0 %, 171 MiB), and the `vgu_ros`
container is up and idle. Run bundle:
`/home/ubuntu/step7b_runs/ib10_7b_20261003_022532` (local copy in the
session scratchpad).

## Mock API spend

Zero (`BACKEND_ID=mock`).
