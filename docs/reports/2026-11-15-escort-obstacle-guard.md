# Escort Obstacle Guard: Design, Tests and Offline Replay

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: the grounding-side escort obstacle guard (owner-approved), its unit tests, and an offline replay over the demo campaign and the October five-robot bundles.
- Rev 2 (2026-11-15): section 8, the same check extended to the `reverse` strategy behind a second key `grounding.reverse_obstacle_guard` (validation take `m5V_t01_a1`, decision `95066420`), with a manoeuvre-coverage table, tests, an offline replay over 17 dispatched reverses and a false-positive assessment.

---

## Scope

- **Branch:** `fix/escort-obstacle-guard`, based on 8933863, the tip of `fix/safety-exemption-scope` (the VM pin 68e67b5 plus the safety-exemption fix). Local commits only.
- **Change:** M3 grounding (`reasoning/rag/`). M5 gets one startup-line field and one Arm B shadow reason string. M4 is untouched.
- **Evidence grade:**
  - Unit tests.
  - An offline re-grounding replay of recorded decisions.
  - No live run. No VM, no API call.
- **Source of the defect:** `docs/reports/2026-11-15-demo-campaign-results.md` sections 8.7 and 8.8, on `demo/campaign-kits` (worktree v7j). That report was not edited.

---

## 1. Defect

In live take `m5D_t01_a1`, decision 2 (`a15f3fc5`) grounded an escort for robot_3:

- heading π, 1.604 m (turn-capped from 2.35 m), from the snapshot pose (1.354, 0.607);
- the leg runs straight through rack island `obstacle_2`, box x 0.25–0.80, y −0.90–0.70.

The robot drove 0.515 m into the island's east face and stayed pinned there until M4's deadline failed the escort (campaign report 8.7.2).

No stage compared the escort leg with the declared static obstacles:

- `derive_escort_distance` sizes the escort.
- `apply_escort_headings` and `_cap_escorts_at_turn` aim and cap it.
- `escort_park_clearance` checks it against the park point only.
- The static boxes reached M3 only for the yielder's retreat.

M4's `drive_heading` publishes raw `cmd_vel` downstream of Nav2's collision monitor. It ends only on distance or deadline.

---

## 2. Design

### 2.1 What Is Checked

`reasoning/rag/escort_obstacles.py`, new.

- **The leg.** Each escorted passer's straight leg is built exactly as the A28(ii) park check builds it:
  - start at the snapshot pose;
  - the dispatched heading;
  - the dispatched distance, after `apply_escort_headings` and the turn cap.

  The leg builder was factored out of `escort_clearance.escort_legs` into `escort_clearance.escort_drives`, so the leg no longer needs a park point. `escort_legs` returns the same values as before.
- **The footprint and margin.** Every declared static obstacle is grown by `geometry.robot.half_width_m + params.retreat_box_margin_m`: the footprint and margin the retreat-candidate sweep already uses (`retreat_candidates.generate_retreat_candidates`). That is 0.09 + 0.05 = 0.14 m in the S1b kit files. No new number was added.
- **Walls.** In the S1b floors the four walls are declared as boxes (`obstacle_3` … `obstacle_6`), so they are checked too. The `aisle_x_band_m` / `aisle_y_band_m` bands were not used. They are per-yielder retreat bands: for example, in `bottleneck_merge` the x band is the N-S aisle's walls, which an E-W escort legitimately leaves.
- **The test** (`segment_entry_m`). The centreline is clipped exactly against each grown box (slab method), not sampled at 0.1 m, so a corner clip shorter than one sweep step is still caught (unit test). Touching a grown face counts as clear: the margin is met exactly.
- **Starting inside a grown box.** This follows the retreat sweep's depth floor: the passer may move along or away from the box, never deeper. The depth along a line inside a box is concave, so the leg is blocked at 0 m exactly when the depth grows at the start; otherwise it never grows.
- **Clear length.** The result is how far the passer can drive before its grown footprint enters the box. This is the brief's "longest clear length minus margin", since the margin is in the growth.

### 2.2 Shorten or Refuse: Refuse, Following `escort_park_filtered`

There are two precedents:

- **`escort_turn_cap` shortens**, and caps the escort and `passer_clear_m` together. Its comment (`grounding_view._cap_escorts_at_turn`) states the reason: M4 holds an escorted passer under its linked wait until it has moved `clear_m`, so an escort shorter than its clearance leaves the passer parked until the hold backstop. The cap is legitimate because the passer's own route leaves the axis there.
- **`escort_park_clearance` refuses.** It drops each retreat candidate whose escort leg is unsafe before stage 2 (`retreat=escort_park_filtered:...`). When none survives, the yield is `yield=infeasible:escort_hits_park:...` and degrades to the reroute fallback, which M5 withholds under `refusal_no_action`.

The brief's shorten rule was "only if the shortened escort still meets `clear_m`". In derived grounding the escort and `clear_m` are always equal:

- both are set from one derivation (`_ground_derived`, `filter_escort_park_candidates`);
- the turn cap lowers them together.

So a blocked escort is always shorter than its `clear_m`. A shorten branch could never fire. Lowering `clear_m` too, as the turn cap does, would need a rule that lets the escort end short of the parked yielder for a reason other than the passer's own turn. No such rule exists (`derive_escort_distance`: "Out-of-band requirements are infeasible, never truncated"). The guard therefore refuses, through the `escort_park_filtered` path:

1. **Candidate filter.** In `filter_escort_park_candidates`, in the same pass as the park check and with one shared re-lettering, a candidate whose leg is blocked is dropped. Each drop is tagged `retreat=escort_obstacle_filtered:<label>:<passer>:<obstacle>:<clear m>` (provenance, cause None, in `DEGRADATION_TAGS`). The selection carries `escort_obstacle_filtered` and `escort_obstacle_infeasible`.
2. **Refusal.** When no candidate survives, the yield degrades to `_reroute_yielder` with `yield=infeasible:escort_hits_obstacle:<passer>:<obstacle>:<clear m>`, which counts as `infeasible_geometry`. M5's `empty_reroute_fallback` already matches the `yield=infeasible:` prefix, so the reroute is withheld exactly as other infeasible proposals are. No M5 logic changed.
3. **Cause naming.** The cause tag is the best-ranked dropped candidate's, from whichever check dropped it. With the guard off this is always the park check, as before.
4. **Backstop.** In `_ground_derived`, the chosen candidate's leg is re-swept after the stage-2 choice, as the A28(ii) backstop does.
5. **Every reader sees it.** The check sits in `prepare_filtered_retreat_selection`, so the A29 consumers get it with no extra wiring:
   - stage 2 (candidates not offered);
   - the plan verifier's yield→reroute model (`_derived_reroute_reason`, new reason "has no retreat candidate whose escort clears the static obstacles");
   - the A15(iv) partner retry: a swapped-in partner with no surviving candidate has no executable retreat;
   - Arm B's shadow retreat (`shadow_classical`, new reason string).

   A29's asymmetric rule is kept. The gate-kept yielder's retry trigger reads the unfiltered selection, so a kept yielder whose escorts are all blocked reroutes and does not swap. This is m5D decision 2's case: robot_2 stays the yielder.

**Alternative not taken:** `escort_off`, which drops the escort and releases the passer to Nav2 (`grounding_view.apply_escort_headings`). It would keep the yield, but it changes M4's crossing behaviour, and it is the path for an underivable heading, not for a known-unsafe leg.

### 2.3 Key

- **`GroundingParams.escort_obstacle_guard: bool = False`.**
  - It is read in derived mode, with a scene geometry and declared static obstacles.
  - When off, the serializer drops it from every dump, so the params dump in decision artifacts is unchanged.
  - When on, the leg sweeps are the only new work.
- **M5 startup line.** When the key is on, `escort_obstacle_guard=True` is appended to the `grounding mode=...` line. When it is off, the line is unchanged; the exact-equality test `test_startup_logs_the_grounding_mode` still passes.
- **Fragment:** `config/grounding/escort_obstacle_guard.fragment.yaml`. No pinned grounding or prereg file was edited.
- **Not covered:**
  - Legacy mode is not covered, like the A28(ii) park check ("derived mode only").
  - The convoy takes (`cv`) run legacy grounding and are not covered.

---

## 3. Tests

- **New file:** `tests/unit/test_escort_obstacle_guard.py`, 33 test functions, 35 cases.
  - Pure geometry:
    - clear;
    - crossing, with the exact entry distance;
    - ends before the face; ends exactly on the face;
    - runs along a face; touches only a corner;
    - zero length;
    - a diagonal heading, and a 0.028 m diagonal corner clip that 0.1 m samples miss;
    - starting inside the margin, heading deeper, away, or along the near face;
    - box growth;
    - grazing within the margin (blocked) and just beyond it (clear).
  - Margin: half-width plus `retreat_box_margin_m` = 0.14 m on the kit file.
  - Live legs:
    - m5D decision 2 enters `obstacle_2` after 0.414 m;
    - m5D decision 1 clears every box;
    - a leg with no park point is still swept.
  - Key off:
    - both m5D decisions reproduce the live yield action and the degradations (the A26 shield tags are excluded, since no task intents are replayed);
    - `False` grounds the same command as the key absent;
    - the dump omits the key.
  - Key on:
    - decision 2 grounds no yield;
    - it names the obstacle and the clear length;
    - it tags all three surviving candidates (D, A, C) beside the park drop B;
    - it keeps the kept yielder (no swap);
    - M5's `empty_reroute_fallback` withholds it;
    - the selection is empty with the obstacle cause;
    - the plan verifier agrees with dispatch (`plan_matches_dispatch`);
    - decision 1's command is identical with the key on and off.
  - Vocabulary, and the fragment pinned: merged over `s1b_dynamic_shield_escort.yaml`, it turns on only this key.
- **New in `tests/unit/test_m5_node_grounding.py`:** the startup line ends `stage2_retreat_selection=False escort_obstacle_guard=True` when the key is on.
- **Fixture:** `tests/unit/data/escort_obstacle_guard/m5d_t01_a1.json`, extracted from the read-only bundle. It holds both decisions, their snapshots, stage-2 labels, params, the bundle's scenario geometry and static obstacles, and the dispatched commands.
- **Test-first.** The tests were written first and run red: an import error for the new module, and a `ValidationError` for the startup-line test. Two expectations were then corrected against the implementation's output. The geometry of two corner tests had been specified wrongly. The decision-2 tags hold four candidates, not two (candidate B is park-filtered; D, A and C are obstacle-filtered).
- **Related files, all passing:** `test_escort_obstacle_guard`, `test_m5_node_grounding`, `test_a28_escort_park`, `test_a29_filter_parity` (including its switch-off goldens), `test_a30_escort_overlay`, `test_a26_retreat_shield`, `test_dynamic_grounding`, `test_command_grounder`, `test_command_grounder_derived`, `test_retreat_candidates`, `test_m5_retreat_stage2`. That is 563 passed and 1 skipped.
- **Full unit suite** (`pytest tests/unit --continue-on-collection-errors`, repo `.venv`):

  | | failed | passed | skipped | errors |
  |---|---|---|---|---|
  | Before (8933863) | 57 | 6967 | 151 | 3 |
  | After | 57 | 7003 | 151 | 3 |

  The failing set is identical (diffed):
  - 49 × `test_aruco_parity`;
  - `test_m5_congestion_detector`, `test_m5_reasoning_pipeline`, `test_m6_config`, 2 × `test_m6_validation`, 3 × `test_t2b_forced_order`;
  - 3 collection errors from `pxr`.

  The 36 new passes are the 35 cases plus the node test.

---

## 4. Offline Replay

`scripts/escort_obstacle_replay.py` (new on this branch; no replay script was merged in). For each escort-carrying command it does two things:

- **(a) Live-leg check.** It sweeps the live dispatched leg against the bundle's declared boxes, at the bundle's own margin and at the kit margin 0.05.
- **(b) Re-grounding.** It re-grounds the stored decision on this tree, through `ground_reasoner_result`, with the guard off and on. It uses the artifact's own params, the bundle's geometry and obstacles, the stored stage-2 label and the snapshot goals.

The verdict is on versus off on this tree. "Reproduced" is off versus live, on the yield action. "Physical" is the recorded outcome. For the campaign it comes from the campaign report's table 8.7.4. For October it comes from `m4.log` `gate_admit` / `gate_cleared` and that report's 8.7.4 notes.

### 4.1 Demo Campaign

| Escort | Passer, leg (snapshot) | Min centreline-to-bare-box | Guard verdict | Off reproduces live | Physical outcome | Match |
|---|---|---|---|---|---|---|
| m5D d1 `03bba450` | robot_4 (−0.629, −1.139) π 1.671 m | 0.200 m (west wall `obstacle_3`, at the leg end); 0.436 m from `obstacle_1` (report) | unchanged | yes | COMPLETED, reached the end | yes |
| m5D d2 `a15f3fc5` | robot_3 (1.354, 0.607) π 1.604 m | 0 (crosses `obstacle_2`) | **refused**: `yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414` (reroute, withheld by M5) | yes | FAILED, pinned on the island face after 0.515 m | yes |
| hoD `f40c0537` | robot_1 (−0.489, 0.000) 0 rad 2.928 m | 1.211 m (`obstacle_1`, behind it) | unchanged | yes | COMPLETED | yes |
| cvD t01–t03 (`35084986`, `759bdb94`, `ab6a10c5`) | legacy | no boxes declared (the barrier is not declared) | n/a (legacy mode, no boxes) | not re-grounded | stopped short, not box contacts (report 8.7.4) | not applicable |
| ibD t01_a2, t02–t05 (5 takes; `junction_clear` phase 2 and fallback) | robot_2 heading π, 1.893–2.927 m | no boxes declared | n/a (no declared boxes; phases not re-grounded) | not re-grounded | COMPLETED ×5 | not applicable |

Decision 2's clear length is 1.354 − (0.80 + 0.14) = 0.414 m. The centreline reaches the bare face after 0.554 m. Live, the robot stopped after 0.515 m from its GT start, with its 0.038 m nose on the face.

### 4.2 October Five-Robot Bundles (v3 `data/logs/vm_runs/`, Read-Only)

The globs were `batch2`–`batch6`, `churn_wave`, `s1b_pilot2` and `s1_resume/v3_s1_resume/runs` (so the `s1_resume` smoke bundle is excluded). They hold 24 escort-carrying dispatched commands (25 legs: E17 `6d37a549` has two passers). 19 commands were admitted (`gate_admit`), matching the campaign report's 19. The other 5 (E13, E14, E17 ×2, E3 `39022242`) were never admitted. s1r E1 runs on the S1a floor (`mapd_5`), not S1b; the replay uses each bundle's own obstacles.

| Escort | Admitted | Min centreline-to-bare-box | Guard verdict | Off reproduces live | Physical |
|---|---|---|---|---|---|
| E13 `984e3bdf` | no | 0.200 (wall) | unchanged | escort fields yes* | not driven |
| E14 `c5a5e687` | no | 0.200 (wall) | unchanged | yes* | not driven |
| E15 `8066f542` | yes | 0.200 (wall) | unchanged | yes* | never cleared, no motion |
| E17 `6745a136` | no | 0.450 | unchanged | yes* | not driven |
| E17 `6d37a549` (2 passers) | no | 0.262 / 0.440 | unchanged | yes* | not driven |
| **E18 `1feb2c4e`** | yes | **0.088 (`obstacle_1`)** | **refused**: no executable retreat; the swapped-in yielder robot_5 has no candidate whose escort clears (`escort_hits_obstacle:robot_2:obstacle_1:0.021`) | yes | never drove (GT 0.002 m) | not testable (the escort never moved) |
| E18 `56b599af` | yes | 0.450 | unchanged | yes | FAILED after 1.16 m, 0.465 m from the boxes by GT (campaign report) | yes (not an obstacle failure) |
| E20 `6cf402ed` | yes | 0.200 (wall) | unchanged | yes | COMPLETED | yes |
| E20 `f269ab37` | yes | 0.301 | unchanged | yes | COMPLETED | yes |
| E21 `04457772` | yes | 0.200 (wall) | unchanged | yes | COMPLETED | yes |
| E22 `07da775d` | yes | 0.200 (wall) | unchanged | yes | never cleared, no motion | yes |
| E23 `9803bd34` | yes | 0.357 | unchanged | yes | COMPLETED | yes |
| E24 `dfb33b91` | yes | 0.443 | unchanged | yes | COMPLETED | yes |
| E25 `c1fd8b36` | yes | 0.400 | unchanged | yes | COMPLETED | yes |
| E26 `cf77ca65` | yes | 0.278 | unchanged | yes | COMPLETED | yes |
| E28 `3c234140` | yes | 0.200 (wall) | unchanged | yes | COMPLETED | yes |
| E29 `14aefebe` | yes | 0.450 | unchanged | yes | COMPLETED | yes |
| E31 `60afd0c1` | yes | 0.543 | unchanged | yes | COMPLETED | yes |
| E6 `83baf2e4` | yes | 0.429 | unchanged | yes* | COMPLETED | yes |
| E3 `39022242` | no | 0.385 | unchanged | yes* | not driven | — |
| E3 `4fde241f`, `db780980`, `ff2171a7` | yes | 0.385 | unchanged | yes* | never cleared, no motion | yes |
| s1r E1 `cb78cd48` | yes | 0.275 | unchanged | yes* | COMPLETED | yes |

\* For the 11 starred rows (all bundles grounded before A25), the off re-grounding differs from live only by the A25 `backup_facing_rad` / `backup_reference_yaw_rad` keys. This was checked key by key on all 11. A25 postdates those bundles and is unconditional under dynamic arms. Every escort field (`passer_escort_*`, `passer_clear_m`, `crossing_order`, `retreat_*`) reproduces. The guard verdict there is also "clear" on the live leg itself.

### 4.3 What Changed Besides m5D Decision 2

**E18 `1feb2c4e` also changes.** It is the near-miss the brief flagged.

- **The leg.** robot_2 heads north (+π/2) for 2.211 m from the snapshot pose (−0.6625, −0.8608). The leg runs parallel to `obstacle_1`'s east face at x = −1.025 + 0.275 = −0.750.
- **Centreline-to-face distance.**
  - From the snapshot: 0.0875 m.
  - From GT at admission: 0.093 m (the report's figure).
  - The URDF wheel half-width is 0.089 m.
- **Margin arithmetic, from the snapshot pose.**
  - Kit margin 0.05: grown face at −0.61, so the centre sits 0.052 m inside. The leg enters the grown box at y = −0.70 − 0.14 = −0.84, after 0.021 m. **Blocked.**
  - Margin 0 (half-width 0.09 only): grown face at −0.66, so the centre sits 0.0025 m inside. Entry after 0.071 m. **Blocked, by 2.5 mm.**
- **Margin arithmetic, from the GT pose (0.093 m).**
  - Margin 0: clear, by 3 mm.
  - Kit margin 0.05: blocked.
- **The physical outcome cannot arbitrate.** The escort was admitted but never drove (GT motion 0.002 m), so whether the leg would have grazed is not shown.
- **Assessment: an owner decision, not a settled verdict.** On perception's pose the body would pass 0.0875 − 0.089 ≈ −1 mm from the rack, so the refusal is defensible by the margin. But it also turns on two things that are not about the graze:
  - **Pose precision.** M1's pose decides it to the millimetre: margin 0 refuses on the snapshot pose and admits on the GT pose.
  - **The start-inside rule (§2.1).** A passer that starts inside the grown box may run parallel to a face. E18 is refused only because its start, y −0.861, lies 0.021 m south of the grown box's south edge (−0.84). The leg enters across that edge, through the south face. Computed with `segment_entry_m`: any start at y ≥ −0.7875 (0.073 m further north), with the same x and the same 1.6 m run along the face, is admitted at both margins. From there the east face is the nearest one, and the run never goes deeper. That y is where the start sits as far inside the south edge as inside the east one.

  So the guard does not treat "a leg grazing a face along its length" consistently: it depends on whether the graze starts inside or outside the grown box. The options for the owner are:
  - (a) keep the retreat sweep's floor rule, as built;
  - (b) for escorts, treat a parallel run within the margin as blocked even when it starts inside;
  - (c) lower the escort margin to the bare half-width.

  Each changes E18 and nothing else in this replay.
- **How it is refused.** It goes through the A15(iv) partner-retry path: the yield had already been swapped to robot_5. The result is a refusal wait fan-out (M5's `yield_refusal_fan_out`, withheld under `refusal_no_action`), not a reroute.

**Nothing else changes.**

- Many escorts end exactly 0.200 m from a wall. The turn-capped node goals sit 0.20 m inside the walls. Against the 0.14 m growth, that is 0.06 m to spare, so no end-of-leg wall graze was refused.
- The smallest other clearance is 0.262 m.

---

## 5. Limits

- **Declared obstacles only.**
  - Undeclared geometry is invisible: the convoy and head-on aisle barriers built from the scenario yaml, the IB10 warehouse walls, and anything not in `static_obstacles`.
  - Legacy-mode grounding (the `cv` takes) is not covered.
  - `junction_clear` cross phases are covered only through `_ground_derived`, and IB10 declares no boxes.
- **Start pose from perception.** The leg starts at the decision snapshot's M1 pose, as the park check's does. E18 shows the decision can turn on a few millimetres of pose error. The leg also assumes M4 drives the dispatched heading exactly. Live, robot_3 drove about 3.5° south of west.
- **Footprint is a square of half-width 0.09 m, axis-aligned with the box.**
  - **Forward:** it is conservative (the URDF nose reaches only +0.038 m).
  - **Diagonal headings:** at 45° the 0.14 m chassis box, centred 0.032 m behind the link, reaches up to about 0.12 m per axis from the link origin. That is inside the 0.14 m growth, but only 0.02 m of the margin is left. No S1b escort is diagonal: headings are snapped to axes.
- **The partner retry is unaware of the guard.** The gate-kept yielder's retry trigger stays unfiltered, under the A29 asymmetric rule. So a kept yielder whose escorts are all blocked reroutes rather than trying the partner, even if the partner's escort would be clear. This is the A29 precedent, not a new rule.
- **No M4 backstop.** The guard cannot see undeclared obstacles, or a robot that drifts off the leg. An execution-side backstop (not built) could be:
  - abort `drive_heading` with FAILED when the commanded linear speed is non-zero but odometry progress along the leg stays below a few centimetres for N seconds (for example 3 s at 0.09 m/s, against a 335 s deadline here);
  - or route escort `cmd_vel` through `cmd_vel_nav`, so Nav2's `collision_monitor` (which sees the lidar) can slow or stop it. That would change the latch-exempt escort's behaviour near the yielder and needs its own analysis.

  Either is an M4 change and is out of scope here.
- **Stage-2 record not extended.** A29 item (ii) (owner ruling R5) lists park-filtered candidates in the stage-2 record's `dropped_candidates` (`DroppedCandidate`, `reason: escort_hits_park`). Obstacle drops are NOT listed there. Adding them would need a new `reason` value and an `obstacle_id` field on `DroppedCandidate`, which changes the key-off bytes of every record that already lists a park drop. They appear only as `retreat=escort_obstacle_filtered:...` tags in the command's degradations. Not done.
- **Not exercised live.** Every result here is unit-test or offline-replay evidence. Stage 2 is not re-run. When the guard drops some but not all candidates, live stage 2 would see a smaller, re-lettered set. In this replay no row had a partial drop.

---

## 6. What a Kit Must Do to Use It

- **Overlay key.** Add exactly one line to the `grounding:` section of the grounding file the kit installs. For the five-robot demo that is `config/grounding/s1b_dynamic_shield_escort.yaml` (md5 `409688866d25289309e081dcb9433037`, unchanged):

  ```yaml
    escort_obstacle_guard: true
  ```

  `config/grounding/escort_obstacle_guard.fragment.yaml` is that fragment. Do not edit the pinned prereg or kit files in place.
- **Runtime delta, relative to 8933863** (md5 base → new):

  | File | Base md5 | New md5 |
  |---|---|---|
  | `reasoning/rag/escort_obstacles.py` | (new) | `c22a6c81349a2b998f5ee808176593ed` |
  | `reasoning/rag/escort_clearance.py` | `50766aeb4efee9516c59e5ede28b158f` | `69e3404af67dff2c143305294957045c` |
  | `reasoning/rag/command_grounder.py` | `cfbd1fb882e5cf9d3b9f45c6e8f67aec` | `951c23b7f2e0168dab10022abccff77a` |
  | `reasoning/rag/maneuver_geometry.py` | `8923c35c0f0c4468e5502aba16a0c421` | `fabe5fdec265acb225dc5aee35132923` |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/shadow_classical.py` | `1de9588a53023b78e555dddd3d80673b` | `24539c25863d1683bf85bad9a0d68fb8` |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `e1b3b289ec05e3c21921fa0253829542` | `791f0bf5f576b3bac27b198b53721a38` |
  | `config/grounding/escort_obstacle_guard.fragment.yaml` | (new) | `9a13e6feb34cc0093c87ef3564bb43d2` |

- **Two caveats on the delta.**
  - The two `swarm_orchestrator` files are colcon-built: rebuild `swarm_orchestrator` after syncing, or the installed copies run the old code.
  - `demo/campaign-kits` carries its own `orchestrator_node.py` changes. A kit built from that branch must merge this branch's changes, not copy the md5 above.
- **Fail-loud property.** On a tree without the guard, `GroundingParams` forbids unknown keys, so M5 refuses to start on the overlaid file. The guard cannot silently run as off.
- **Arm check.** Assert per episode from M5's startup log, not from the yaml:
  - the line `grounding mode=derived params=<file> ... escort_obstacle_guard=True` is present;
  - each decision artifact's `grounding_params_source.params.escort_obstacle_guard` is `true`.

  A key-off arm must show neither.
- **Registration.** The change alters S1b grounding for any registered arm that turns it on: the E18 `1feb2c4e` row would have been refused. Using it in a scored arm needs a registration amendment (campaign report, open owner decisions, the "Escort obstacle guard" bullet).

---

## 7. Verified and Inferred

| Claim | Status |
|---|---|
| m5D decision 2 is refused with the guard on, cause `escort_hits_obstacle:robot_3:obstacle_2:0.414`, and M5 withholds it | verified (unit test and replay) |
| m5D decision 1, hoD, and all October escorts but E18 `1feb2c4e` are unchanged | verified (replay) |
| E18 `1feb2c4e` is refused at both margin 0 and 0.05 from the snapshot pose | verified (replay plus arithmetic); whether it would have grazed physically is not shown |
| Key off is byte-identical | verified for both m5D decisions and the A29 goldens; full suite failing set unchanged |
| A shorten branch would be unreachable because escort equals `clear_m` in derived grounding | verified by code reading (`_ground_derived`, `filter_escort_park_candidates`, `_cap_escorts_at_turn`) |
| The guard would have prevented the live pin | inferred (the decision would have been withheld; what the scene did next is not shown) |
| The suggested M4 no-progress abort would bound similar failures on undeclared obstacles | inferred, not built |

---

## 8. Reverse Extension (Rev 2, 2026-11-15)

### 8.1 Finding That Prompted It

In validation take `m5V_t01_a1` (bundle on v7j, read-only; report `docs/reports/2026-11-15-validation-guard-contacts-results.md` on v7n), the closest robot–static approach was 5.5 mm: robot_4 at `obstacle_1`'s south-west corner, sim 81.6 s, while reversing under `95066420-reverse`, a `vlm_verbatim` VLM `reverse`. The take ran with `escort_obstacle_guard: true`, which covers escorts only.

### 8.2 Facts (Step 1)

**How a `reverse` strategy is grounded** (verified by code reading; `command_grounder.py`):

- Derived mode reaches the legacy template (`_ground_derived` → `_ground_legacy`). Every involved robot (`resolve_robot_order`, i.e. `involved_robots` after the grounding view) gets one `reverse` action.
- The distance is the fixed `_FALLBACK_BACKUP_M` = 1.3 m, clamped per robot only by `_clamp_reverse_distance_to_tracked_band`, which applies only to robots with a declared arm and `tracked_extent_m`.
- The direction is not in the command. M4 backs up along the robot's own heading.
- Existing geometry checks:
  - the corridor same-side refusal on the first two involved robots (`_beyond_corridor_same_side`);
  - the tracked-band clamp.
- There is no retreat-room check, no robot-sweep check and no static-obstacle check. `static_obstacles` are passed to `_ground_legacy`, but the reverse branch never reads them.
- **Existing refusal path.** A refused reverse becomes a `temporary_wait` (8 s) to every involved robot, with `requested_strategy: reverse` and the refusal `reason`. `_legacy_template_degradations` tags it `reverse=infeasible:<reason>` (cause `infeasible_geometry`).
  - M5 dispatches those waits. `yield_refusal_fan_out` matches only `"yield refused:"` and `empty_reroute_fallback` only reroutes, so `refusal_no_action` does not withhold a refused reverse.
  - Verified on the live artifacts `m5V` `929335f4` and `2acc6130`: same-side refusals, 8 s waits to r2–r5, `dispatch_withheld` None.
  - This differs from the escort refusal, which M5 withholds (section 2.2).

**M4's backup** (verified by code reading plus Nav2 config):

- `Nav2Adapter.backup` publishes a negative `Twist` straight to `/<robot>/cmd_vel`.
- `collision_monitor` reads `cmd_vel_nav` and writes `cmd_vel` (`ros2_ws/src/swarm_simulation/config/nav2_params.yaml`), so the backup bypasses the monitor and its lidar polygons. The safety monitor checks robot pairs only.
- Under `backup_line_hold` (set for every `reverse` when `dynamic_scene_arms` is on, `grounding_view.apply_backup_line_hold`), the backup holds the line through its start pose along its start heading. `line_turn_rad` applies only to `yield`. Without the key it servos toward the odom y = 0 spawn line.
- It ends only on:
  - odometry distance (`COMPLETED`);
  - an OS-monotonic deadline `max(15 × L / 0.1, 30)` s, which is 195 s for 1.3 m (`FAILED backup timed out`);
  - or, with `fresh_latch_fast_fail`, a fresh robot–robot latch.
- There is no stall or no-progress abort, and nothing sees a static box.

**Manoeuvre coverage: straight raw-cmd_vel motion the grounder can dispatch, and whether a declared-box sweep exists**

| Manoeuvre | Built by | Declared-box sweep before this change | After |
|---|---|---|---|
| `reverse` strategy, every involved robot | `_ground_legacy` (reached from derived) | **none** | swept under the new key `reverse_obstacle_guard` (derived only) |
| Derived yield: backup leg | `generate_retreat_candidates` | yes, only under a dynamic-arms view (`rear_room_band == "footprint"`), **sampled at 0.1 m**, not clipped exactly | unchanged |
| Derived yield: pull-off (sidestep) leg | same | same as the backup (sampled, footprint band only) | unchanged |
| Derived yield on a declared (non-dynamic) geometry: backup and pull-off | same | **none** (the boxes are added only under the footprint band; the yield gate's rear-room check is not a box sweep of the leg) | unchanged; finding |
| Legacy-mode yield: backup and pull-off | `_ground_legacy` | **none** (gate rear room only) | unchanged; out of scope (legacy) |
| Derived yield: escort | `escort_obstacles` | yes, `escort_obstacle_guard` (exact clip) | unchanged |
| `junction_clear` recede phases (a `reverse` action per receder) | `_ground_junction_clear_phases` | **none** | unchanged; finding (IB10 declares no boxes, so it is moot there today) |
| `junction_clear` cross phase and fallback yield | `_ground_derived` | as a derived yield | unchanged |
| `junction_clear` release phase: hand-built `yield` holds with `backup_distance_m` 0.0 and, for a receder, a raw-cmd_vel pull-off (`release_pull_off_lateral_m`) | `_ground_junction_clear_phases` (`_receder_hold`) | **none** on the pull-off (not through the candidate sweep; verified by code reading) | unchanged; finding |
| reroute, waits | Nav2 / no motion | Nav2 costmap and collision monitor apply | n/a |

The guard was not extended to any other row. Recommendation: before any scene with declared boxes runs `junction_clear` or a declared-geometry yield, sweep the recede and release legs with `reverse_obstacle_hits`, and the declared-geometry yield's backup and pull-off with `segment_entry_m`. Each needs its own key, test and replay, like this one.

**`95066420-reverse` by the guard's arithmetic** (verified, unit tests):

- Box: `obstacle_1`, bare x −1.30…−0.75, y −0.70…0.90. Grown by 0.09 + 0.05 = 0.14 m, it is x −1.44…−0.61, y −0.84…1.04.
- **robot_4.** Snapshot (−1.5559, −0.3519), θ 1.9601 rad, so it backs up along −1.1815 rad (cos 0.3803, sin −0.9249) for 1.3 m.
  - x reaches −1.44 after 0.1159 / 0.3803 = **0.305 m**, at y −0.634, inside the grown y range: **blocked**.
  - Minimum centreline-to-bare-box distance: 0.105 m, i.e. 0.015 m of body clearance under a 0.09 m half-width.
  - GT: COMPLETED after 1.283 m; minimum URDF-footprint gap **5.5 mm** at 81.6 s.
- **robot_5.** Snapshot (−1.6496, 0.0076), θ −1.8218, so it backs up along 1.3198 rad.
  - x reaches −1.44 after **0.844 m**, at y 0.825: **blocked**.
  - Minimum centreline-to-bare-box distance: 0.117 m.
  - GT: COMPLETED after 1.274 m; minimum gap **19.1 mm** (`obstacle_1`'s north-west corner, 87.4 s).
- **The guard refuses the command:** `reverse=infeasible:reverse_hits_obstacle:robot_4:obstacle_1:0.305` and `…:robot_5:obstacle_1:0.844`.
- Side note (finding, not changed): the VLM's own plan for this decision gave robot_5 `continue`. Dispatch reversed both involved robots anyway, because the reverse template reverses every involved robot. The 19 mm approach was robot_5's.

### 8.3 Design

- **Shared geometry, no new geometry code.**
  - `escort_obstacles.reverse_obstacle_hits(legs, snapshot, static_obstacles, margin_m)`. Each leg starts at the snapshot pose, heads `theta + pi`, and runs the dispatched distance.
  - It uses the escort guard's `segment_entry_m` through a factored `_first_entry` that `escort_obstacle_hits` now also uses (behaviour unchanged).
  - It uses the same growth (`escort_obstacle_margin_m`: half-width + `retreat_box_margin_m`), so the owner's start-inside rule applies unchanged.
  - Reason string: `reverse_hits_obstacle:<robot>:<obstacle>:<clear m>`.
- **One predicate for every reader.** `command_grounder._reverse_obstacle_refusal(robot_ids, snapshot, geometry, params, static_obstacles)` rebuilds each robot's dispatched leg (`_FALLBACK_BACKUP_M` after the tracked-band clamp). Three readers call it:
  - dispatch (`_ground_derived`, only when the legacy template actually produced `reverse` actions);
  - the default plan (`_derive_default_plan`);
  - the plan audit (`_plan_problems`), which also serves the candidate-options probe (`derive_candidate_options`), so with the key on a blocked reverse option is flagged there too (not unit-tested).
- **What a refusal looks like.** It follows the same-side precedent:
  - any blocked leg refuses the whole reverse;
  - every involved robot gets the 8 s `temporary_wait` (`requested_strategy: reverse`, `reason` = the first hit's reason);
  - the command carries one `reverse=infeasible:reverse_hits_obstacle:...` tag per blocked leg, before the view tags;
  - M5 dispatches the waits, as it does every refused reverse.

  A partial reverse of the clear robots was not built: no precedent exists, and the same-side refusal and the default plan's any-pair rule both hold everyone.
- **Second key, `grounding.reverse_obstacle_guard`, not a widened `escort_obstacle_guard`.**
  - `m5V_t01_a1` ran with `escort_obstacle_guard: true` and dispatched `95066420`. Under a widened key, the same kit yaml and the same recorded params would now refuse that decision. The artifact could no longer say which version ran, and the validated configuration would not reproduce.
  - With two keys, `escort_obstacle_guard` keeps exactly its 72c08c8 meaning, which a unit test pins.
  - The new key has default false and is dropped from every params dump when off.
  - M5's startup line appends ` reverse_obstacle_guard=True` after the escort field, only when on.
  - Fragment: `config/grounding/reverse_obstacle_guard.fragment.yaml`.
  - Derived mode with a scene geometry and declared boxes only; legacy mode ignores the key (unit test).

### 8.4 Tests

- **New file:** `tests/unit/test_reverse_obstacle_guard.py`, 25 functions, 29 cases. Fixture: `tests/unit/data/escort_obstacle_guard/reverse_cases.json`, extracted read-only from m5V `95066420` and `b07a700f` and October E12 `d374802a`.
  - Geometry reuse:
    - the leg starts at the snapshot pose and runs at θ + π;
    - `clear_m` equals `segment_entry_m` on the grown box;
    - reason format;
    - no boxes gives no hits;
    - a robot missing from the snapshot is skipped.
  - `95066420` arithmetic: 0.305 m for robot_4 and 0.844 m for robot_5.
  - Key on:
    - `95066420` becomes the 8 s wait fan-out with the exact parameters and tags;
    - M5 does not withhold it (`yield_refusal_fan_out` and `empty_reroute_fallback` are None);
    - the tag's cause is `infeasible_geometry`;
    - the clear `b07a700f` is identical with the key on and off.
  - Multi-robot: in E12 `d374802a`, robot_2 is blocked by the declared north wall `obstacle_5` at 1.267 m and robot_4 is clear. Both robots wait, and there is one tag.
  - Key off:
    - all three cases reproduce the live actions and degradations (M5's `plan_id` aside);
    - `False` equals absent;
    - the dump omits the key;
    - `escort_obstacle_guard` alone leaves `95066420` a reverse;
    - legacy mode ignores the key.
  - Plan verifier:
    - with no plan, the default plan waits robot_4 and `plan_matches_dispatch` holds;
    - a reverse/reverse plan is repaired to wait/wait and matches dispatch;
    - with the key off, the same plan stays `vlm_verbatim` and matches;
    - a clear plan's verdict is the same with the key on and off.
  - Fragment pinned.
- **Two node tests in `tests/unit/test_m5_node_grounding.py`:** the startup-line field alone, and after the escort field.
- **Test-first.** The new file ran red first (an import error for `reverse_hits_obstacle_reason`).
- **Related files.** After the change, the new file, `test_m5_node_grounding`, the escort, A26/A28/A29/A30, dynamic and derived grounder, retreat, stage-2 and `test_plan_verifier` tests all pass: 1576 passed, 129 skipped.
- **Full suite:** see 8.7.
- **Existing gap, not fixed: plan/dispatch mismatch for reverse.** The verifier's same-side audit flags only the first two involved robots, and a plan `continue` leg on an involved robot is never flagged. Dispatch, meanwhile, holds or reverses every involved robot. So `dispatch_matches_plan` was already False live for `95066420`, `929335f4` and `2acc6130`. The new check flags every involved robot's `reverse` leg, but it cannot change a plan's `continue` legs either.

### 8.5 Offline Replay

`scripts/reverse_obstacle_replay.py` (new). For each artifact whose strategy is `reverse` and whose dispatched command has a `reverse` action, it reports:

- the live-leg check;
- an off/on re-grounding on this tree;
- M4's last status for the command (`m4.log`);
- from GT: the distance moved from M4's handover until the leg's distance is reached, the robot turns back, or 150 s pass.

With `--contact-root` pointing at v7m (`b5eaee5`, the GT contact-recompute branch, `isaac/vgu_sim/contact_geometry.py`), it also gives the minimum URDF-footprint gap over that window to every box the scene builders author. The v7m recompute summaries are whole-run and do not window by leg, so they were not used for the per-leg figures.

**Scope searched** (`find -name decisions`, `_backup_*` excluded):

- the 36 campaign bundles;
- every bundle under v3 `data/logs/vm_runs/` and under the main checkout's `data/logs/vm_runs/`;
- 375 bundles in all.

**What was found:**

- **17 dispatched derived `reverse` commands with declared boxes:**
  - hoD `4de32642`;
  - m5V `95066420` and `b07a700f`;
  - 14 October S1b commands in `batch2`, `batch3`, `churn_wave`, `live_batch` and `resume`. Four of these (`live_batch` E7, E8, E10 and `resume` E11) lie outside the escort replay's globs.
- **Not replayable:**
  - s6 `s6_live_er2_pilot` `46b0f4dd` declares no boxes, so the guard sees nothing there.
  - 41 `reverse` decisions in 37 September head-on bundles (main checkout `20260925_*`, `bshort*`, `gshort`, `m4fix`, `simtime_shadow_val`) predate derived grounding. They have no `grounding_mode` or `dispatched_command`, so they are out of scope. A leg-only check (snapshot pose, every involved robot 1.3 m backward, against the declared `blocker_west` at margin 0.14) on the 26 that have `orchestrator.yaml.used` finds 2 that the rule would block (`20260925_040539` `668f8830` and `20260925_011246` `7d8a0c07`, robot_1 at 0.881 and 0.722 m); the other 15 have no config to check; no GT was compared. Their count matches the audit's "reverse 41" (campaign report §11.4), but the audit's bundle list was not available to confirm they are the same decisions.
  - The head-on scenes declare `obstacle_1` (`blocker_west`, 0.3 m square at x −1.85) but not the aisle barrier. The guard cannot see the barrier.
  - `junction_clear` recede reverses (ibD ×5) are a different manoeuvre: not covered and not replayed.
- **Off reproduces live for all 17** (actions and degradations).

**FAILED-leg windows checked.** The script's window is not bounded by M4's terminal status. For every FAILED leg, the FAILED line's wall time was mapped to sim time with a linear fit over every `sim_t=` line in `m4.log` (real-time factor 0.17–0.23). Every contact in the table falls inside its command's window. Those legs failed on the 195 wall-s backup deadline, about 35–45 sim-s after handover, with the robot pinned on the face. `09647748` r3 failed after 1.6 sim-s, having moved 0.065 m. Only `150b95a6` changed: the script's unbounded window had shown 1.297 m.

**Results per command:**

| Command | Robots (blocked legs: obstacle @ clear m) | Guard on | M4 / GT per robot (moved; min footprint gap) | Physical verdict |
|---|---|---|---|---|
| hoD `4de32642` | r1, r2 (none) | unchanged | r1 COMPLETED 1.286, 0.172 (`blocker_west`); r2 COMPLETED 1.293, 0.183 (barrier) | correct admit |
| m5V `95066420` | r4 (`obstacle_1`@0.305), r5 (`obstacle_1`@0.844) | refused | r4 COMPLETED 1.283, **0.0055**; r5 COMPLETED 1.274, **0.0191** | justified (sub-margin graze ×2) |
| m5V `b07a700f` | r1, r2, r3 (none) | unchanged | COMPLETED ×3; 0.241 / 0.082 / 0.213 | correct admit |
| E12 `d374802a` | r2 (`obstacle_5`@1.267); r4 clear | refused | r2 COMPLETED 1.260, **−0.0015** (rack/NW_north); r4 COMPLETED, 0.208 | justified (contact) |
| E13 `652ac9ac` | r5 (`obstacle_1`@0.337) | refused | r5 COMPLETED 1.263, **0.0179** | justified (sub-margin graze) |
| E13 `ea23b1a7` | r1 (`obstacle_3`@0.539); r3, r4 clear | refused | r1 **FAILED** after 0.550, **0.000** (rack/NW_west); r3, r4 COMPLETED | justified (contact, stall) |
| E16 `ede6d209` | r3 (`obstacle_3`@1.157); r4 clear | refused | r3 FAILED after 0.618, 0.243; r4 FAILED after 0.304 | untested (the leg's end is on the rack face line x −2.50; never reached) |
| E17 `150b95a6` | r3 (none) | unchanged | r3 FAILED after 0.409 m, 0.368 (window bounded by the FAILED line) | admit; failure not a box contact |
| E17 `9cf93ebe` | r2 (`obstacle_2`@0.584), r3 (`obstacle_1`@0.696), r5 (`obstacle_4`@0.710); r4 clear | refused | r2 **FAILED** after 0.578, **−0.0001**; r3 COMPLETED, 0.061; r5 COMPLETED, 0.312; r4 COMPLETED | justified by r2 (contact); r3 and r5 are robot-level false positives |
| E18 `8bf906be` | r5 (`obstacle_3`@0.843); r4 clear | refused | r5 **FAILED** after 1.188, **−0.0017** (rack/SW_west); r4 COMPLETED, 0.075 | justified (contact) |
| E19 `09647748` | r3 (`obstacle_3`@1.201); r4 clear | refused | r3 FAILED after 0.065 (barely moved); r4 COMPLETED | untested (the leg would end 0.044 m centreline from the rack face) |
| E6 `93100ae3` | r3 (`obstacle_3`@0.727); r1 clear | refused | r3 **FAILED** after 0.743, **0.000** (rack/SW_west); r1 FAILED after 1.135 | justified (contact) |
| E6 `a3bbc017` | r3 (`obstacle_6`@0.692); r5 clear | refused | r3 **FAILED** after 0.978, **−0.0015** (rack/SW_south); r5 COMPLETED | justified (contact) |
| E10 `d5541ff0` | r2 (`obstacle_2`@0.487) | refused | r2 **FAILED** after 0.552, **−0.0014** | justified (contact) |
| E7 `c7aeaac1` | r1 (`obstacle_2`@0.363), r3 (`obstacle_4`@0.935), r4 (`obstacle_3`@0.599); r2 clear | refused | r4 **FAILED** after 0.606, **0.000**; r1 COMPLETED, 0.076; r3 COMPLETED, 0.271 | justified by r4 (contact); r1 and r3 are robot-level false positives |
| E8 `f06c33b3` | r2 (`obstacle_2`@1.137), r4 (`obstacle_6`@1.236) | refused | r2 COMPLETED, 0.058; r4 FAILED after 0.497 (not near a box) | untested: r2 is a robot-level false positive and r4 never reached its box |
| E11 `c417cbff` | r1 (`obstacle_2`@0.742); r5 clear | refused | r1 COMPLETED 1.272, **0.077** | **false positive** |

### 8.6 False-Positive Assessment

**Criterion.** Only the 0.05 m threshold (the guard's own margin) was fixed before the GT gaps were printed; the three-way split below was written after. A refusal is a false positive when every blocked leg was driven to completion and its GT footprint gap stayed at or above the 0.05 m margin. It is justified when some blocked leg's gap fell below the margin (the GT contact threshold is 0.005 m). It is untested when no blocked leg was driven far enough to reach the box.

**Command level** (14 of 17 commands refused):

| Verdict | Count | Commands |
|---|---|---|
| justified | 10 | 8 by contact (`d374802a`, `ea23b1a7`, `9cf93ebe`, `8bf906be`, `93100ae3`, `a3bbc017`, `d5541ff0`, `c7aeaac1`); 2 by sub-margin graze (`95066420` 5.5 mm, `652ac9ac` 18 mm) |
| untested | 3 | `ede6d209`, `09647748`, `f06c33b3` |
| false positive | 1 | `c417cbff` |

- **Rate:** 1/14 (7 %); at most 4/14 if every untested refusal were also a false positive.
- **Unchanged:** the 3 admitted commands (hoD `4de32642`, `b07a700f`, `150b95a6`). None touched a box.

**Robot level** (20 blocked legs counted per robot):

- Blocked legs that reached contact or a sub-margin graze: 11.
- Blocked legs never driven far enough to reach the box (untested): 3 (`ede6d209` r3, `09647748` r3, `f06c33b3` r4).
- Robot-level false-positive rate: 6 of the 17 blocked legs that have a physical answer (35 %).
- Blocked legs driven to completion with a gap of 0.05 m or more: 6 (`9cf93ebe` r3 0.061 and r5 0.312; `c7aeaac1` r1 0.076 and r3 0.271; `f06c33b3` r2 0.058; `c417cbff` r1 0.077).

**Two causes of the robot-level false positives.** Both are the shared escort/retreat rule, not new to reverse:

- **Square corners.** The grown boxes have square corners: Minkowski growth with a square, not a disc. Near a corner the test is stricter than the Euclidean margin, by up to 0.14 × (√2 − 1) ≈ 0.058 m. `c417cbff` r1, `c7aeaac1` r1 and `f06c33b3` r2 hit the grown box with centreline-to-bare-box distances of 0.140, 0.151 and 0.157 m.
- **Declared walls over-approximate open arms.** The declared walls `obstacle_3` and `obstacle_4` (x ±2.5…±3.0, y −2.3…2.3) span the open west and east arms, where the real racks leave y −0.6…0.6 free. `9cf93ebe` r5 and `c7aeaac1` r3 backed into the open east arm: GT gaps 0.31 and 0.27 m.

**Effect on scenes that resolve through reverse:**

- In the campaign, hoD decision 1 (`4de32642`) is unchanged, and so is `b07a700f`.
- In October, 10 of the 14 refused commands had at least one reverse leg FAILED live. Seven of those were pinned on a box face until the 195 wall-s deadline (verified with the bounded windows above). The others failed without reaching a box.
- With the key on, each would instead hold its robots 8 s and re-analyse. What the scene does next is not shown offline.
- The September head-on reverses that the audit's 41 most likely counts are legacy-mode and untouched.

### 8.7 Full Unit Suite

`pytest tests/unit --continue-on-collection-errors` (repo `.venv`), run under the resource rule:

| | failed | passed | skipped | errors |
|---|---|---|---|---|
| Before (72c08c8) | 57 | 7003 | 151 | 3 |
| After (7551f03) | 57 | 7034 | 151 | 3 |

- The failing and erroring ids are identical (diffed): the same 57 failures and the 3 `pxr` collection errors as section 3.
- The 31 new passes are the 29 cases of `test_reverse_obstacle_guard.py` plus the two node tests.

### 8.8 Limits

- **The leg model is exact only under `backup_line_hold`** (`dynamic_scene_arms` on). 16 of the 17 replayed reverses had it. hoD `4de32642` did not, so its leg is approximate (M4 servoed toward odom y = 0). Without it, M4 servos toward the odom y = 0 spawn line, so the straight backward leg is an approximation.
- **Start pose and heading come from the M1 snapshot**, as for escorts. M4 holds its odometry start heading at handover, not the snapshot heading.
- **Declared boxes only.** The head-on aisle barrier, the IB10 walls, and the open arms behind the declared S1b walls are not modelled as they are.
- **The refusal dispatches 8 s waits; it does not withhold.** This follows the reverse precedent. Whether the reverse refusal should instead be withheld under `refusal_no_action` (as yields are) is an owner question.
- **No M4 backstop.** The no-progress abort of section 5 would also bound the 195 s pinned-reverse deadlines seen in October.
- **Refuse, not shorten.** The escort's reason for refusing (escort length equals `clear_m`) does not carry over to reverse. A reverse could instead be shortened to its clear length. That was not built, because the owner approved the same check (refuse) and a shortened reverse may not open the standoff. It is an open owner option.
- **Not run live.**

### 8.9 Kit Instructions (Reverse Guard)

- **Overlay key.** Add `  reverse_obstacle_guard: true` to the `grounding:` section of the installed grounding file (fragment `config/grounding/reverse_obstacle_guard.fragment.yaml`).
  - It is independent of `escort_obstacle_guard`; a kit wanting both adds both lines.
  - The base `s1b_dynamic_shield_escort.yaml` is unchanged.
- **Arm check, per episode:**
  - M5's startup line ends `... reverse_obstacle_guard=True` (after `escort_obstacle_guard=True` when both are on);
  - each artifact's `grounding_params_source.params.reverse_obstacle_guard` is `true`.
  - **Meaning of `escort_obstacle_guard` is unchanged:** `m5V_t01_a1` ran exactly that, and its reverse was not swept.
- **Runtime delta relative to 72c08c8** (md5 at 7551f03):

  | File | md5 |
  |---|---|
  | `reasoning/rag/escort_obstacles.py` | `538945facf94de08da8438c416204c8c` |
  | `reasoning/rag/command_grounder.py` | `d8fb03ce7797888f317ba646a4523375` |
  | `reasoning/rag/maneuver_geometry.py` | `281358a2795acec623790e618e581d74` |
  | `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (colcon-built: rebuild `swarm_orchestrator`) | `bfb4cefbbb70019e392de97e41a406eb` |
  | `config/grounding/reverse_obstacle_guard.fragment.yaml` (new) | `d063e86c8d2e1a77dc99228ae0a329de` |

  Section 6's md5 table is stale at this tip for `escort_obstacles.py`, `command_grounder.py`, `maneuver_geometry.py` and `orchestrator_node.py`; use this table. Unchanged since section 6: `escort_clearance.py` `69e3404af67dff2c143305294957045c`, `shadow_classical.py` `24539c25863d1683bf85bad9a0d68fb8`, `escort_obstacle_guard.fragment.yaml` `9a13e6feb34cc0093c87ef3564bb43d2`.

  As in section 6, `demo/campaign-kits` must merge `orchestrator_node.py`, not copy it.
- **Fail-loud property.** An older tree rejects the unknown key at startup.
- **Registration.** Turning it on changes S1b reverse grounding: 14 of 17 recorded reverses would be refused. A scored arm needs a registration amendment.

### 8.10 Verified and Inferred

| Claim | Status |
|---|---|
| `reverse` grounding had no static-obstacle check | verified (code) |
| M4's backup bypasses the collision monitor and has no stall abort | verified (code and `nav2_params.yaml`) |
| A refused reverse is dispatched as 8 s waits, not withheld | verified (code and live artifacts `929335f4`, `2acc6130`) |
| `95066420` is refused (0.305 and 0.844 m) | verified (unit test and replay) |
| Key off is byte-identical; 17 of 17 live reverses reproduce | verified (tests and replay) |
| 14 of 17 refused; 10 justified, 3 untested, 1 false positive | verified (replay and GT, FAILED windows bounded by M4 status), under the criterion stated in 8.6 (split written after the GT output) |
| The refusals would have improved those scenes | inferred, not shown |
| The uncovered manoeuvres in 8.2 can graze declared boxes | inferred from code; no instance checked |
