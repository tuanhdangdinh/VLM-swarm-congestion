# Escort Obstacle Guard: Design, Tests and Offline Replay

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: the grounding-side escort obstacle guard (owner-approved), its unit tests, and an offline replay over the demo campaign and the October five-robot bundles.

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
