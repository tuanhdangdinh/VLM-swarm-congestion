# Convoy Live Resolution Experiment (Exploratory)

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: registration of a 15-slot, three-arm `convoy_counterflow_slip` run on the IB10 safety runtime, written offline before any episode ran.

---

## 1. Question and Status

The owner's instruction (2026-11-14), verbatim:

> "go ahead, prepare the convoy kit offline"

This document registers the experiment. Nothing has run: no VM was started, no `gcloud` or `ssh` command was issued, and no model was called.

**Question.** Does the Layer 2 pipeline clear a second four-robot jam that the reactive layer does not clear? The pipeline is the M5 trigger, then M2, then M3 legacy grounding, then the M4 crossing chain. The scene is a counter-flow robot (`robot_2`) meeting a three-robot platoon (`robot_1`, `robot_3`, `robot_4`) at a 0.55 m gate.

The run has three arms:

- **Arm A:** Layer 2 on, live ER-2.
- **Arm B:** Layer 2 off.
- **Arm C:** Layer 2 on, a scripted oracle decision, no VLM.

Arm C against Arm A asks whether the live model adds anything beyond a scripted oracle decision.

**Can the experiment be meaningful as designed?** Yes, with one condition that only the smoke can settle:

- The 0.20 m hard-contact floor may latch the yielder at the start of its backup.
- In 2 of 10 recorded convoy runs, the robot_1–robot_2 standoff gap was already below 0.20 m when the yield began: 0.187 m and 0.192 m on GT, 0.19 m on M1.
- No predictor of the gap was found. Runs at a similar real-time factor (RTF) to this VM's (b3_fix, B3S and B3DEMO, anchored RTF 0.298–0.302) had gaps of 0.26–0.33 m.
- No recorded convoy run had the floor armed.
- If the floor pins `robot_2`, every Layer-2-on episode stalls by apparatus, while Arm B is unaffected.
- The smoke (one scripted-oracle episode) is designed to show this before any live episode runs (sections 8.4 and 15).

It is exploratory:

- It is never pooled with prereg-v3 or with either IB10 run (2026-11-13, 2026-11-14).
- It is simulation only.
- The scene has never run with a live model, so a failed Arm A is a possible and reportable outcome.

---

## 2. Runtime and Scene

| Item | Value |
|---|---|
| Base | The v3 pin on the VM, git `68e67b5`, as in both IB10 runs. |
| Code delta | The same two files as the IB10 safety run, from `fix/safety-exemption-scope` (`8933863`): `safety.py` `3011d9a7` and `safety_monitor_node.py` `c2cad302`, replacing `c6c9cbae` / `7b45075f`. |
| Safety config | `swarm_execution/config/safety.yaml` = the 0.20 m floor file (`c41913f0`) plus `scoped_clearing_exemption: true`, `waiver_closing_tolerance_m: 0.05`, `waiver_closing_readings: 3`. The merged file is `65fb84a3`, byte-identical to the IB10 safety run's. |
| Key assertion | Every episode is gated on M4's startup line ending in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`. |
| Grounding | `config/grounding/cvl_convoy_legacy.yaml` (`63f50f91`) is installed by the kit, untracked, and removed by the restore. It is 68e67b5 `config/rag.yaml` (`e18c723c`) with its one `mode: derived` line set to `mode: legacy`, and is byte-identical to `layer2off_pilot/overlays/b3_rag.yaml`, the rag file of every recorded convoy run. `config/rag.yaml` itself stays pristine. All three arms name the same file. |
| Scene | `isaac/config/scenarios/convoy_counterflow_slip.yaml` (`9684b5fc`), unedited: 4 robots, `duration_sec: 260.0`, `seed: 42` (a label only; no pose jitter exists). The USD is built fresh from it in every invocation. |
| Map | `warehouse_map_convoy_counterflow_slip.yaml` / `.pgm` (`2cf00224` / `f48cb508`). The installed copy has never been recorded on this VM. `ov_cvl.sh` checks it and stops the run before any episode if it is absent or different. |
| Overlay, Arms A and C | `cvl_l2on.yaml` (`7e3ab552`) = the convoy overlay of the 2026-10-06 layer2off pilot (`b3_orchestrator.yaml`, `a6473853`) with three edits: `keep_debug_frames: true`, `grounding_params_path: config/grounding/cvl_convoy_legacy.yaml` and `plan_channel_enabled: true`. |
| Overlay, Arm B | `cvl_l2off.yaml` (`8457f756`) = `cvl_l2on.yaml` + `reasoning_enabled: false`, the 2026-11-13 IB10 Arm B switch. |
| Nav2 bring-up | Parallel, as every convoy and IB10 record. |

**Loader-resolved overlay comparison (verified offline with the v7f `load_config`):**

- `cvl_l2on.yaml` differs from the IB10 Arm A/C overlay (`0196f1e8`) only in `grounding_params_path`, `initial_tasks`, `scenario_geometry` and `shadow_classical_zones`.
- It differs from `b3_orchestrator.yaml` only in `grounding_params_path`, `keep_debug_frames` and `plan_channel_enabled`.
- Every other M5 setting is the intersection runs' setting:
  - the 12 s stall threshold;
  - the 15 s cooldown;
  - the prompt's pairwise geometry;
  - robot order `id_asc`;
  - stage 2 on (inert in legacy mode).

---

## 3. Design

| Item | Value |
|---|---|
| Arm A | Layer 2 on, live `gemini-robotics-er-2-preview` (`BACKEND=gemini`). A Gemini probe runs before every Arm A episode, and the run stops on HTTP 429/402 or any other probe error. |
| Arm B | Layer 2 off: no congestion detection, no M2 or M3 call, no dispatch. M5 still loads `initial_tasks`, including the 120 wall-s hold-back of `robot_3`/`robot_4`, and logs the M1 scene. The backend id is passed as `gemini`, exactly as the 2026-11-13 IB10 Arm B: no pipeline is built, so no call can be made. |
| Arm C | Layer 2 on. The scripted `MockBackend` replays the tracked `config/mock_decisions/convoy_counterflow_oracle_order_once.json` (`436457c0`). That is the scene's oracle decision with no plan, so M3 builds the plan. No VLM call (section 7). |
| Smoke | e01 = Arm C, run alone (`run_cvl.sh smoke`). |
| Follow-up order | Fixed in advance: e02 A, e03 B, e04 C, e05 A, e06 B, e07 C, e08 A, e09 B, e10 C, e11 A, e12 B, e13 C, e14 A, e15 B. |
| n | 5 per arm. The smoke counts as Arm C episode 1 under the IB10 smoke rule: its harness gates passed (`ran`) and the owner wrote `SMOKE_ACCEPTED`. Otherwise it is scored and reported as excluded, and Arm C has 4. |
| Labels | `cvL_eNN_armX_aK`. VM directory `~/cvl`, separate from `~/ib10` and `~/ib10s`. |

**Why near-repeats.**

- There is no pose jitter (verified: `jitter` and `random` appear nowhere in `isaac/vgu_sim/config.py`, `runner.py` or `scenario_builder.py`; `seed` is used only for the run name and the manifest, `runner.py:94,100,260` and `scenario_builder.py:92`), so the episodes are repeated runs of one scene.
- The repeats are not identical where it matters. In the 10 recorded convoy runs the standoff gap ranged 0.187–0.383 m and the goal-stack minimum 0.458–0.485 m (±0.36 runs). A difference of one or two episodes between arms can come from this apparatus spread alone.
- Arm A's one legitimate source of variation is model sampling. ER-2's sampling fields are dropped from the request, so its temperature is not controlled.
- Trigger timing and RTF add small state variation.
- Counts only: no p-values, no intervals.

---

## 4. Outcomes (Fixed Before Any Episode)

All scoring is `kit/score_cvl.py`. It wraps the pinned `scripts/coverage_scene_scores.py` (`a17ac751`, byte-identical to 68e67b5):

- `score_b3` and its `score_conflict`;
- `score_ground_truth`, from `scripts/t2b_forced_order.py` (`81974c3b`): arrival within 0.35 m of the goal and never beyond 0.5 m afterwards; t0 is the first GT sample with any robot faster than 0.03 m/s;
- `first_passer`.

Nothing frozen is reimplemented.

### 4.1 Primary

| Outcome | Definition |
|---|---|
| Valid jam | `score_conflict`'s `onset_in_window` ([15, 50] sim-s, from the yaml's `expected_conflict`) AND `min_duration_met` (≥ 2.0 s), on GT. |
| **Resolved** | Valid jam AND all four robots arrived inside the 260 sim-s horizon. `None` for an invalid jam. |
| **Episode success** | Resolved AND 0 manoeuvre floor stops (4.3) AND 0 GT frames with any pair < 0.18 m in the safety window [onset + 2.0 s, end]. |

`outcome_class` is reported beside the primary, never used for it. It reads `resolved` only with exactly one dispatch, so a live episode with a re-dispatch would read `intermittent`.

### 4.2 Secondary

| Outcome | Definition |
|---|---|
| Gate cleared | Valid jam AND every robot made its final crossing of x = 0 toward its goal. The gate jam dissolved, whatever happened at the goals afterwards. It exists so that the goal-stack defect (4.4) cannot erase the architecture result. |
| Time to full resolution | Last arrival minus the GT conflict onset, in sim-s. Censored at the horizon when not resolved. |
| Arrivals | Count out of 4, and per robot after t0. |
| Success, IB10 rule | Resolved AND 0 floor stops of any kind AND GT minimum pairwise distance after t0 ≥ 0.18 m. Reported beside the primary for comparability with both IB10 runs. |

### 4.3 Safety Counts

- **Floor stops.** M4 lines `safety stop robot=… reason=hard_contact_floor hard_contact_floor_m=0.2 pairs=…`.
  - A line is **standoff-inherited** if all three hold:
    - its pair is the first dispatched command's yielder and a member of that command;
    - that pair's M1 distance in the dispatched decision's scene snapshot was already < 0.21 m (the 0.20 m floor plus a 10 mm tolerance for M1 noise while both robots stand still);
    - it falls within 30 wall-s of that command's first `dispatch` line.
  - Every other floor line is a **manoeuvre** floor stop.
  - Both counts are reported.
- **GT contact.** Frames with any pair < 0.18 m, counted over all frames, after t0, and in the safety window.
- **GT minimum pairwise centre distance.** After t0 (the IB10 field), and in the window.
- **GT standoff gap.** The robot_1–robot_2 minimum in [onset, onset + 2 s].
- **Key-on events.** Parsed by `keyon_cvl.py`, the IB10 safety definitions unchanged: not-honoured and rejected-leg lines, `latch waiver revoked … reason=closing`, third-robot waivers, deadline-ended commands and key-on stalls.

Why the safety window and the split differ from IB10:

- In all 10 recorded convoy runs, the closest approach of the whole episode is the robot_1–robot_2 standoff at jam onset, before any dispatch: GT 0.187–0.383 m.
- That approach is the reactive layer's, identical in every arm.
- Section 8.4 explains why a pre-existing standoff gap under the floor produces a floor line at the yielder's first motion that is not a manoeuvre failure.
- Both rules are reported in every case. Which one is primary is owner decision 1 (section 15).

### 4.4 Labels

- **`goal_stack_latch`:**
  - `robot_3` never arrived, AND the GT robot_1–robot_3 distance fell below 0.45 m after `robot_3`'s escort ended;
  - the escort end is M4 `crossing_chain gate_admit … passer=robot_4 … sim_t=`, or failing that `robot_3`'s first GT x ≥ 1.6 after onset;
  - `goal_stack_min_m` is reported for every episode.
- **`late_dispatch`:**
  - no dispatch naming both `robot_3` and `robot_4` before M5's `start delay elapsed, base mission released` line (wall epochs in `m5.log`);
  - Arms A and C only.
- **Timing:** wall seconds after M5's session line for the first analysis, the first dispatch, the first robot_3+robot_4 dispatch and the release. Logged in every COND line and scored.

### 4.5 Decision Content and Attribution

For every dispatched decision the scorer reports:

- strategy (`convoy` and `yield` scored apart);
- `yield_robot` and `involved_robots`;
- whether `robot_3` and `robot_4` are involved;
- `crossing_order`;
- `plan.provenance` and `dispatch_matches_plan`;
- `grounding_degradations` (including `strategy=aliased:*`);
- the plan's rejection and edit reasons.

Executed order is the M4 `gate_admit` passer order and the GT final-crossing order of the platoon. `first_slipper` and its latency (`score_b3`) are reported only: under correct execution the identity is degenerate (scene header), and in Arm B it is meaningless.

---

## 5. Smoke Pass Criteria

`smoke_check_cvl.py` prints `SMOKE_CHECK PASS` only if all six hold:

1. **Harness gates.**
   - `attempts.tsv` records the bundle `ran`.
   - `GATE OK` and `RESTORE OK` are present.
   - The map start-up check is OK.
   - Every Arm C check of `cond_cvl.py` passes (section 9), including the key line and legacy grounding in every artifact.
2. **Valid jam.**
3. **Resolved:** 4/4 arrived.
4. **0 manoeuvre floor stops.**
5. **0 GT frames under 0.18 m in the safety window.**
6. **0 key-on stalls.** Conservative: a FAIL means "inspect".

The verdict also prints, as WARN or INFO:

- standoff-inherited floor stops (WARN), with their pair and distance;
- the GT and M1 standoff gap;
- the goal-stack minimum and latch label;
- the dispatch and release timing and the late-dispatch label;
- the gate-admit and GT crossing order;
- the slack to the 260 s horizon, with a WARN under 30 s;
- `outcome_class`, waivers and revocations.

**If the smoke does not resolve, the experiment stops for owner review.** `run_cvl.sh follow` refuses without `SMOKE_ACCEPTED`, which only the owner writes, and unless `SMOKE_CHECK.txt` says PASS.

---

## 6. Exclusions and Counting

| Case | Treatment |
|---|---|
| Nav2 bring-up abort (`NAV2_BRINGUP_FAILED`) | Not counted. The slot is retried, up to 3 attempts. Three aborts skip the slot; two skipped slots in a row stop the run. |
| Map start-up failure: `map_server` never `Activating`, `lifecycle_manager_map_server` never `Managed nodes are active`, or any `no map received` / `Costmap timed out waiting for update` | **New (proposed default):** an explicit `PROBLEM` verdict is caught by the chain right after the episode as `bringup_abort:map_startup` and retried like a bring-up abort, so it is never `ran`. This is the IB10 safety e02 failure, which that kit found only after scoring, as an invalid jam. A missing verdict (the check crashed or printed nothing) is `harness_fail:startup_check` and stops the chain; it is never retried. Alternative: report only (owner decision 7). |
| Invalid jam | Excluded from the primary denominator and reported (`EXCLUDED:invalid_jam`). The IB10 2026-11-13 rule as amended 2026-11-14. |
| Harness failure: no `logs saved to`, failed per-episode restore, key line missing, arm check refused, condition gate failed | Excluded and reported. The chain stops, and the slot is not marked `ran`. A later invocation, started by the owner after inspection, re-runs it under a new attempt label. |
| Truncated (cost cap or wall-clock stop, GT end < 259 sim-s) | Counted only if all four robots had arrived. Otherwise excluded as `truncated` and reported. |
| Arm A episode in which M5 ran but no analysis happened | Counted, as data. |
| Gemini probe failure before an Arm A episode | The episode never starts. The run stops. |
| Goal-stack latch | Labelled. Counted as not resolved in the primary (proposed default). `gate_cleared` and a sensitivity line that excludes latched episodes are reported. Never re-run. |
| Late dispatch | Labelled. Counted by its GT outcome (proposed default). Never re-run. |
| Third attempt | None beyond the bring-up retries above. There is no rerun mode in this kit. |

---

## 7. Arm C Mechanism (No Runtime Code Change)

Arm C uses existing code and config only. It is the same five-step chain as the IB10 safety Arm C (addendum section 5), with the convoy script:

1. **Driver.** `ep_run_cvl.sh` starts `scripts/vm/fc_launch.sh` (`055db01e`) with `MOCK_DECISION_FILE=config/mock_decisions/convoy_counterflow_oracle_order_once.json`.
2. **fc_launch.** A set `MOCK_DECISION_FILE` forces `BACKEND_ID=mock` (`fc_launch.sh:258`) and exports `VGU_MOCK_DECISION_FILE` to M5. Verified for this scene by the real `fc_launch.sh` in DRY_RUN with Arm C's environment (`test_dry_cvl.sh` step 8). It printed `reasoning_backend_id: openai -> mock`, the exported path, the convoy map and the four convoy spawns.
3. **Backend factory.** `reasoning/vlm/backend_factory.py:326-337`: for `mock`, the file is read through `_load_mock_script` (`:201`) into a `MockBackend` sequence. The kit never sets `VGU_MOCK_RETREAT_CHOICE_FILE`, so there is no stage-2 backend.
4. **Mock backend.** `reasoning/vlm/mock_backend.py:43-45` replays the entries in order and holds the last one. It makes no network call. `mock_backend.py` `c27742a0` is a hard pin here: the IB10 safety snapshot recorded it on this VM on 2026-11-14 (`match`, in all three pin logs).
5. **M3 default plan.** The legacy grounder turns the decision into the oracle command. With no `proposed_plan`, plan verification returns `m3_default` / `"plan absent"` (`command_grounder.py:4947`).

**The script** (tracked at 68e67b5, md5 checked before every Arm C episode) has two entries:

1. `yield`, `yield_robot: robot_2`, `involved_robots` all four, `crossing_order: [robot_1, robot_3, robot_4, robot_2]`, no plan;
2. `none`, held for every later analysis.

**Why not the intersection's `[none, decision, none]`.** The convoy does not need the skip-first entry, and adding it would cost something.

- In all 6 recorded oracle runs, the first analysis is the robot_1/robot_2 standoff itself. It came 38.0–46.7 wall-s after M5's session line and was dispatched 0.3–0.6 s later (verified from `m5.log`: b3_fix s42/s43, harvest off/on, B3DEMO, B3DISP).
- IB10 needed the skip because its first trigger was a start-up stall. The convoy has none.
- A skip-first script would cost one 15 s cooldown of the release margin (section 8.3).
- It would also need a new untracked file on the VM.
- The tracked two-entry file is what every recorded 4/4 convoy oracle run used.
- The three-entry variant stays an owner option (decision 9).

**Re-grounded offline (`reground_cvl.py`).** The scripted decision was grounded through the v7f M3, which equals 68e67b5, exactly as `reasoning_pipeline.py:1604-1645` calls it. It ran on 6 recorded first-trigger snapshots. Under the legacy file it gives the oracle command every time:

- `yield` `robot_2`, with `temporary_wait` for `robot_1`, `robot_3` and `robot_4`;
- order [robot_1, robot_3, robot_4];
- backup 0.987–1.028 m, park x 1.124;
- `robot_1` escort 1.855–1.968 m;
- no degradation;
- plan `m3_default` / `plan absent`, with legs yield r2 and cross r1, r3, r4.

The harvest-on escort, 1.863 m, equals the M4 `gate_admit escort_m=1.863` that the recorded run executed.

**What Arm C is.** The script supplies the whole decision: strategy, yielder, robot set and order. Arm C is therefore an oracle reference for the live loop. It is not a "grounder default" in the IB10 sense, where the script gave only the strategy and the robot set. An Arm A that matches Arm C shows that the model's answers led to the oracle's executed outcome. It does not show that the model is unnecessary.

---

## 8. Findings That Decide Whether the Experiment Is Meaningful

### 8.1 Grounding: Legacy, the Same in All Arms (Caveat vs IB10)

- **Verified.**
  - The shipped `config/rag.yaml` (`e18c723c`) is `mode: derived`.
  - Every recorded convoy run used `mode: legacy` (`rag_used.yaml` / `rag_md5=63f50f91`), as did the scene design (yaml header: "with legacy grounding").
  - The IB10 runs used the derived `config/rag.yaml`; their `junction_clear` grounding is derived-only.
- **Legacy vs derived on the same 6 snapshots (verified):**
  - derived gives backup 1.37–1.51 m (legacy 0.99–1.03), the base escort 2.35 m (legacy 1.86–1.97) and `retreat=default:no_choice` on all 6;
  - in Arm A, derived mode would add a stage-2 Gemini call for every yield (`reasoning_pipeline.py:1551-1581` runs stage 2 only when `params.mode == "derived"`); Arm C's mock has no stage-2 backend.
  - The derived geometry has never run on this scene. The scope document's derived latch prediction for `robot_4` is inference, not re-verified here.
- **Registered:** legacy in all three arms, through one kit-installed file that is md5-pinned, snapshot as `grounding ABSENT`, installed by the deploy, loaded by the installed M5 loader (`GROUNDING_MODE legacy True`) and removed by the restore.
  - Gated per episode in Arms A and C: M5 logs `grounding mode=legacy params=config/grounding/cvl_convoy_legacy.yaml`, and every artifact records `grounding_mode: legacy` and that path.
  - **Caveat:** the convoy runs on legacy grounding and IB10 on derived. The "second scene" result is therefore a second pipeline configuration as well.

### 8.2 The Goal-Stack Latch Margin

The calculation, reproduced from GT:

- The latch is M4's `min_distance_m` 0.45 m, on M1 positions.
- `robot_1` and `robot_3` are both passers. They are never exempt from each other (E4), with the key on or off.
- The 0.20 m floor plays no part: it applies only to exempt or waived pairs (`safety.py:970-985`).

The robot_1–robot_3 GT minimum after `robot_3`'s escort ended, in the recorded runs:

| Goal table | Run | GT min (m) | Margin over 0.45 m | robot_3 arrived |
|---|---|---|---|---|
| ±0.36 | b3_fix s42 | 0.4746 | 24.6 mm | yes |
| ±0.36 | b3_fix s43 | 0.4628 | 12.8 mm | yes |
| ±0.36 | harvest off | 0.4579 | 7.9 mm | yes |
| ±0.36 | harvest on | 0.4735 | 23.5 mm | yes |
| ±0.36 | B3DEMO | 0.4847 | 34.7 mm | yes |
| ±0.30 | B3S | 0.4624 | 12.4 mm | yes |
| ±0.30 | B3DISP | 0.4361 | latched | no |
| ±0.30 | B3PROBE | 0.4255 | latched | no |
| ±0.30 | b3_oracle 2026-09-30 | 0.4441 | latched | no |

Reading the table:

- The 8–35 mm range is verified on the 5 ±0.36 runs on disk.
- M1, sampled at 1 Hz, gives 0.4595–0.4758 for the four runs that have a scene log.
- At ±0.36, 0 of the 5 runs on disk latched. The 0.4448 m "loop-family" latch the scope document cites is not on disk and is not verified.

**What happens on a latch.**

- `robot_1` (parked at its goal) and `robot_3` (approaching its goal) hold each other permanently.
- `robot_3` never arrives, so `score_ground_truth` gives 3/4 and the episode is not resolved.
- In Arm C the held `none` answers any re-trigger.
- In Arm A a live re-analysis could dispatch a fix. That is an Arm A capability, reported as such.

**Counting rule (proposed, fixed before the run):**

- The primary counts a goal-stack latch as **not resolved**.
- `gate_cleared` is reported beside it, so a latched episode still shows whether the gate jam was cleared.
- A sensitivity line excludes latched episodes.
- Never re-run.

**Scenario edit (option only, needs owner approval; not recommended for this run).**

- Widening the goal stack is not possible within the rack margin. The scene header says ±0.41 extrapolates to only about 0.49 m, and ±0.45 undercuts the 0.15 m wall margin.
- Moving `robot_3`'s goal or its approach line is a scene redesign: a new yaml md5, re-pinned tests, a new map check, and the USD rebuilt on the VM.
- A yaml edit is inert until the USD is rebuilt, and `build_all.sh` re-touches every staged yaml. The kit therefore builds only this scene, from the pinned yaml, and gates each episode on the USD being newer than the yaml.

### 8.3 The 120 Wall-s Release and the Decision Deadline

- **What it is (verified).**
  - `robot_3` and `robot_4` carry `start_delay_sec: 120` in `initial_tasks`.
  - `task_registry.py:68` sets `release_at = now + start_delay_sec` from M5's start, and `orchestrator_node.py:1013-1017` releases them on the monotonic wall clock, logging `start delay elapsed, base mission released`.
  - The release happens in every arm, Arm B included.
- **Recorded timing (6 oracle runs, wall s after M5's session line).**
  - First trigger: 38.0–46.7.
  - Mock dispatch: 38.4–47.2.
  - Release: 119.2–119.9.
  - The anchored RTF of these runs was 0.257–0.302 (B3DISP 0.257, the others 0.288–0.302); the current VM's is 0.293–0.299. The trigger time should carry over (inference).
- **Live ER-2.**
  - The 19 IB10 Arm A calls on 2026-11-13/14 took 5.9–11.0 s (median 8.1 s).
  - The brief's "up to 18 s" is not seen in those calls; the S6 pilot's calls took 3.6–5.3 s.
  - Expected first dispatch: about 44–58 wall-s, leaving about 60–75 s of margin before the release.
  - If the first answer does not dispatch, M5's 15 s cooldown and a re-trigger allow about three more analyses before the release.
  - The recorded post-resolution re-analyses came every 15.0–15.5 s.
- **Worst case.**
  - `max_attempts: 2` at the 120 s `timeout_sec` (`config/models.yaml`) is 240 s, longer than the release.
  - A hung call would make the dispatch late.
- **What the kit does.**
  - Nothing changes mid-episode: no early release and no extension.
  - The scorer labels `late_dispatch` when no dispatch naming both `robot_3` and `robot_4` precedes the release line, and logs every timing.
  - A pair-only answer (`yield` robot_2 with only robot_1 and robot_2) grounds to `yield` plus `robot_1`'s wait, leaving `robot_3` and `robot_4` uncommanded (re-grounded offline). That is the scene's designed bystander-latch failure, and it is labelled late as well.
  - Counted by GT outcome (proposed).

### 8.4 New: The 0.20 m Floor at the Convoy Standoff

- **Verified.**
  - `evaluate_latches` latches **both** robots of an exempt or waived pair closer than `hard_contact_floor_m` (`safety.py:970-985`).
  - `robot_2`'s yield makes the pair (robot_1, robot_2) exempt the moment it goes ACTIVE. The replay of the recorded streams with the v7f tracker shows this in the first exempt row, with (robot_2, robot_3) and (robot_2, robot_4) as well.
  - The robot_1–robot_2 standoff gap in the 10 recorded convoy runs, on GT:

    | Gap | Runs |
    |---|---|
    | 0.187, 0.192 | harvest on, harvest off |
    | 0.243–0.383 | the other 8 |

  - M1 read 0.182–0.196 m in the two harvest runs.
  - Five bundles have the command streams the replay needs (harvest on, harvest off, B3DEMO, B3DISP, B3S). Replaying them with the floor at 0.20 m (key on or off) gives a floor breach for (robot_1, robot_2) at the first exempt row in the two harvest runs only. (robot_2, robot_3) and (robot_2, robot_4) are exempt from that first row in the harvest runs and B3DISP.
- **Inferred, not observable offline.**
  - With the floor armed, the monitor publishes zero Twist to both robots while the backup publishes reverse Twist directly to `cmd_vel` (`nav2_adapter.py:354-370`).
  - The robot either crawls out once M1 reads ≥ 0.20 m, logging one floor-stop line pair, or stays pinned, with no resolution.
  - The recorded trajectories cannot tell which, because they ran without the floor.
  - The harvest pair ran at anchored RTF 0.288–0.293. b3_fix, B3S and B3DEMO ran at 0.298–0.302 with gaps of 0.26–0.33 m, so RTF does not predict the gap, and no other predictor was found. Whether this VM's standoff falls under 0.20 m is VM-only.
- **Consequences, fixed now.**
  - A floor line from this pre-existing gap is labelled standoff-inherited (4.3) and is not a manoeuvre failure in the primary.
  - The IB10-rule success counts it and is reported.
  - If the smoke shows `robot_2` pinned (not resolved), the experiment stops. Options for the owner (none chosen here):
    - accept the scene as unresolvable with the floor at this runtime;
    - run the convoy with the floor off, which then differs from the IB10 safety runtime;
    - lower the floor, which needs a new safety review.

---

## 9. Condition Gates

`cond_cvl.py` runs after every episode. It evaluates every check, prints `CHECK PASS|FAIL` lines and one `COND` line with the counts and timing, and stops the chain with `harness_fail:condition` on any failure.

| Arms | Checks |
|---|---|
| All | `CONDITION.txt` carries `tag=convoy_live`, `record=0`, `confirmatory=0`, the arm, and the arm's overlay name; `ARM_CHECK.txt` equals the deployed loader's wanted reading for the arm (Layer-2 fields, `half_length_m 0.5`, the legacy file, its loaded mode, plan channel, `robot_3` delay 120); M4 key line (end-anchored); the handoff guard line; an M5 session line; a non-empty `m5_scene.jsonl`. |
| A, C | No Layer-2-off line; M5 `grounding mode=legacy params=config/grounding/cvl_convoy_legacy.yaml`; every artifact `grounding_mode: legacy` with that path. |
| A | `backend=gemini` with no mock file; every artifact's `backend_id` (both fields) is `gemini`; every artifact with a decision or a served model has `served_model` `gemini-robotics-er-2-preview` (a failed call, with no decision and no model, is allowed); no `mock_mode`; a probe line ending `rc=0`. |
| B | `backend=gemini` with no mock file; exactly one Layer-2-off line; 0 artifacts, 0 analyses, 0 dispatch lines; no cost log; no probe line. |
| C | ≥ 1 artifact; exactly 1 dispatched artifact; `backend=mock` with the script path and md5; `backend_id` `mock` (both fields); no served model; no `mock_mode`; 0 tokens; no cost log; no probe line; the dispatched artifact is `m3_default` / `plan absent` and equals the script's first entry. |

**Map start-up gate.** `startup_check_cvl.py` is the IB10 safety `startup_check_ibs.py`, logic unchanged. It runs on the VM after every episode, before the condition gate. A `PROBLEM` verdict becomes a bring-up abort; a missing verdict stops the chain (section 6). Separately, the installed convoy map is checked in the snapshot step, before anything is changed, and again in `ov`. On recorded bundles it flags only the known-bad IB10 safety e02 a1 and is OK on the other 24:

- 10 IB10 safety bundles;
- 11 IB10 live bundles;
- harvest on and off;
- `l2_03`.

**Offline gate test (`kit/test_gates_cvl.py`, 55 cases, all PASS).** Every failing set is asserted exactly. The source bundles are only read.

| Fixture | Checked as | Result |
|---|---|---|
| Harvest on (recorded convoy oracle mock), as recorded | C | Fails exactly the harness fields, the key line, the handoff guard, the legacy line, the legacy artifacts, `c_cond_backend` and `c_m3_default`. |
| Harvest on and off, kit-patched (harness fields only) | C | Fails exactly `c_m3_default`: they were recorded with the plan channel off. |
| Same, plus a synthetic plan block (`m3_default` / `plan absent`, as `reground_cvl.py` shows) | C | Pass. |
| C fixture with a probe line / a sibling cost log / a wrong yielder / two dispatches / a derived artifact | C | Exactly `c_no_probe` / `c_no_cost_log` / `c_scripted_decision` / `c_dispatched` / `legacy_artifacts`. |
| IB10 safety Arm A e01, e03, e05, e07, e09, as recorded | A | Exactly the harness fields + `m5_legacy_line` + `legacy_artifacts` (derived grounding). |
| Same, as recorded | C | The no-VLM set and `c_scripted_decision`. |
| IB10 safety e03, kit-patched | A | Pass. The real recorded probe line passes; a 429 probe fails `a_probe_ok`. |
| Kit-patched mock convoy | A | Fails the model checks. |
| IB10 live Arm B e02, e04, e06, e08, e10, as recorded | B | Exactly the harness fields + `floor_key_line` (key off on 2026-11-13). |
| IB10 live Arm B e02, kit-patched | B | Pass; a probe line fails `b_no_probe`. |
| Layer2off pilot `l2_03_b3_s42` (the OLD Layer-2-off mechanism: mock no-congestion backend), kit-patched | B | **Fails** exactly `b_cond_backend`, `b_l2off_one`, `b_no_artifacts`, `b_no_analyses`. |
| Key-on parser on harvest on/off and B3DEMO | — | 0 key-on lines, 0 deadline-ended commands, 0 stalls (baseline). |
| Floor split, timing and counting rules (synthetic lines) | — | Inherited vs manoeuvre; a 0.203 m snapshot gap is still inherited (tolerance); same pair after 30 wall-s is manoeuvre; a pair-only dispatch is late; a recorded oracle run is not late; smoke not accepted is excluded; invalid jam is excluded; a map-start-up abort is excluded and the retry counted. |
| Smoke verdict on a kit-patched harvest-on bundle | C | PASS. An injected standoff floor line gives PASS with WARN; an injected manoeuvre floor line gives FAIL; an unresolved, latched recorded run (`b3_oracle` 2026-09-30, ±0.30) gives FAIL with `goal_stack_latch=True`. |

**Scorer reference (`score_cvl.py --history`, the recorded convoy bundles).**

- 5/5 ±0.36 oracle runs: valid, resolved, gate cleared, 173.9–179.7 s from onset, last arrival 201.0–205.3 sim-s (55–59 s of slack).
- ±0.30 runs: 3 of 4 latched, with the gate cleared.
- `l2_03` (Layer-2-off pilot): valid jam, 0/4 arrived, gate not cleared.

---

## 10. Caps and Wall Time

| Cap | Value | Enforcement |
|---|---|---|
| Wall clock | **6.5 h in total** (23,400 s), VM start to TERMINATED, summed over every invocation (`wallclock_ledger.tsv`) | A VM never starts with less than 1.5 h left. An episode starts only if it can end within its 30 min admission budget before the chain deadline (the invocation cap minus a 30 min teardown reserve). A VM dead-man restores and powers off at the cap + 20 min. |
| Spend | **$1.00 est in total** | Arm A only: `cost_watch.py` per-episode guard $0.20; no Arm A episode starts with less than $0.20 left, so five fit unless one runs away. Arms B and C make no calls. Probes are not in the estimate. |
| Analyses | No count cap (`MAX_ANALYSES=0`) | As both IB10 runs. |

**Estimate.**

- **Episode slot.** 260 sim-s / RTF + about 160 s overhead:
  - about 17.3 min at the measured 0.296 (11 IB10 safety episodes: 0.293–0.299);
  - about 19.3 min at 0.26;
  - about 23 min at the scene header's 0.21.
- **Smoke invocation.** About 25–35 min. The IB10 safety smoke took 1,531 s with a 19 min slot.
- **Follow invocation.**
  - About 4.4–5.0 h at RTF 0.26–0.296, in **one invocation**: all 14 slots are admitted under the cap.
  - At RTF 0.21 only 12 of 14 would be admitted, and less than 1.5 h would remain to resume.
- **Total.** About 4.8–5.5 VM-h (the `test_dry_cvl.sh` step 6 admission table).
- **Gemini.** About $0.04–0.05 per Arm A episode (6–8 calls at about $0.006; the recorded oracle runs had 6–8 analyses), about $0.25 in total.

**Invocations.** Two:

- the smoke (owner gate);
- the follow-up, in one invocation.

The VM is restored to `PINS_V3 OK` and stopped (TERMINATED verified) at the end of each. If the follow-up stops on the wall clock, a second `follow` resumes at the first slot not `ran`, within the remaining cap.

---

## 11. Runtime Delta, Deploy, Restore and Dry Test

**On the VM, by step:**

| Step | Action |
|---|---|
| `snapshot_cvl.sh` | Refuses unless `PINS_V3 OK` (v3 pin + convoy-path pins) and the installed convoy map is the 68e67b5 bytes. Backs up, by kind: config (`orchestrator.yaml`, `rag.yaml`, `safety.yaml`), code (2 files), mock (the Arm C script, normally present), grounding (the legacy file, normally ABSENT), scenario yaml and USD (normally ABSENT). Also records the md5s of the installed `swarm_orchestrator` and `swarm_execution` plus a tarball. |
| `build_cvl.sh` | The convoy USD from the pinned yaml (`build_scenario`), checked newer than the yaml, then `usd_check` and `validate_simulation`. Not `build_all.sh`. |
| `deploy_cvl.sh` | Copies the 2 code files, the merged `safety.yaml`, the mock script (only if absent) and the legacy file, with plain `cp` + `touch`. One purge + colcon build of `swarm_execution`. Verifies: installed == src; installed md5s; the key line derived by the installed loader; `GROUNDING_MODE legacy True` from the installed M5 loader. The merged file and the legacy file are regenerated on the VM from the VM's own files and byte-compared with the kit's copies. |
| `ov_cvl.sh` | Regenerates both overlays and byte-compares them. Checks the installed convoy map md5s. Parses both overlays through the deployed loader. |
| `ep_run_cvl.sh` | Swaps in the overlay per episode; the restore verifies the pristine `orchestrator.yaml`/`rag.yaml` and the installed copy. |
| `restore_cvl.sh` | Every file back to the snapshot, kind by kind (ABSENT files removed). Purge + rebuild of both packages. Then verifies the host files, the installed md5 list == the snapshot, and `PINS_V3 OK` with the same ok-line count. |
| Driver EXIT trap | Restore, pull (`rsync -a`, never `--delete`), stop, then verify `TERMINATED`. |

**Offline dry test.** `bash test_dry_cvl.sh` ended `TEST_DRY_CVL OK` on 2026-11-14. It covers:

1. syntax checks and kit md5s;
2. the git preflight (19 checks, including the 3-file runtime delta and the scorer pins);
3. the key line, the generators and both overlays through the v7f loader;
4. the episode tables and slot resolution on a fake VM tree;
5. every driver DRY_RUN path and the ledger;
6. the admission table;
7. `test_restore_cvl.sh`, `test_gates_cvl.py`, `score_cvl.py --history` and `reground_cvl.py`;
8. the real `fc_launch.sh` in DRY_RUN;
9. a rename audit: no IB10 VM path, label, process name or env override left.

`test_restore_cvl.sh` runs the real snapshot, deploy, pins and restore on a fake VM tree extracted from 68e67b5, with shimmed `docker`, `colcon` and `md5sum`. The deploy's Python checks run for real on the fake installed packages, and so does `ep_run_cvl.sh`'s arm check: its `GOT_RE` line is extracted and executed verbatim on both overlays, and returned exactly `WANT_ON` and `WANT_OFF`. It passed 10 cases:

- happy + double restore;
- half-deployed (code + legacy file, no rebuild);
- installed-only drift;
- mock absent (installed, then removed);
- foreign mock;
- foreign file at the legacy path;
- drifted `rag.yaml`;
- installed convoy map missing (the snapshot refuses before backing anything up; the restore reports nothing changed);
- tampered backup (FAILED, then OK after repair);
- colcon failure.

After every case: `PINS_V3 OK`, legacy file removed, USD removed, `config/rag.yaml` untouched.

---

## 12. What the Outcome Can and Cannot Support (Written Before the Run)

| Outcome | Supports | Does not support |
|---|---|---|
| A and/or C resolve, B does not | A second four-robot scene for the architecture claim: the trigger plus grounding clear a jam that the reactive layer does not clear, in simulation, under legacy grounding and the IB10 safety runtime. | Generality beyond two authored scenes; any confirmatory claim; pooling with prereg-v3 or IB10. |
| C resolves, A does not | The live loop around the oracle decision works; the model's decisions (content, latency or re-dispatches) did not reach the oracle outcome on this scene. Reportable as is. | That the model "cannot" do it: near-repeats, one prompt configuration, uncontrolled sampling. A one- or two-episode gap can be apparatus spread (section 3). |
| A resolves as often as C | Here the model's answers led to the oracle's executed outcome. | That the VLM adds nothing beyond a scripted decision: the script was written with the oracle. |
| A resolves more often than C | Possibly something A does beyond the first decision, for example a re-dispatch after a goal-stack latch; read the traces. | Any conclusion from a one- or two-episode gap alone: the standoff gap and the goal-stack margin vary between repeats (section 3). |
| C does not resolve (smoke) | The scene is not resolvable at this runtime as configured (floor, key or goal stack); the experiment stops for owner review. | A verdict on the model. |
| Time differences | Nothing quantitative. A carries model latency; A and C both dispatch at the first trigger. | — |

---

## 13. Caveats

These hold whatever the results are.

- **(a) Near-repeats with apparatus spread.** One scene, one seed label, no pose jitter: no p-values, no intervals. The repeats still differ in the standoff gap (0.187–0.383 m recorded) and the goal-stack margin (7.9–34.7 mm), so a small difference between arms is not evidence of an arm effect. The run is exploratory.
- **(b) Arm C is an oracle reference.** It is not a grounder-default arm (section 7).
- **(c) Legacy grounding differs from IB10's derived grounding** (section 8.1).
- **(d) First live run.** The scene has never run with a live model. Before this run it had only these on record:
  - scripted oracle mocks, 5/5 resolved at ±0.36, plan channel off, floor off, key off, on older code (2026-09-30 to 2026-10-04 trees);
  - one Layer-2-off pilot on the old mechanism.
- **(e) First run with the floor, the key and the plan channel.** Every recorded convoy run had the plan channel off and the floor absent. This is the first with all three on (section 8.4).
- **(f) Arm A re-analyses.** After the resolution, Arm A's re-analyses are live calls. In the recorded runs they were robot_2-alone stalls, answered `none` by the mock. A live answer may dispatch, and with the plan channel on a new plan supersedes the old one. Arm C's held `none` cannot.
- **(g) Simulation only.**

---

## 14. Runbook

From `data/logs/vm_runs/convoy_live/kit/` in the `vgu-vlm-swarm-v7f` worktree:

```bash
bash test_dry_cvl.sh     # offline, must print TEST_DRY_CVL OK
bash run_cvl.sh smoke    # step 1: e01, Arm C, key on, 0.20 m floor
# inspect (below); only on SMOKE_CHECK PASS and owner acceptance:
touch ../SMOKE_ACCEPTED
bash run_cvl.sh follow   # step 2: e02-e15 = A B C A B C A B C A B C A B
```

Between the two commands, check:

1. **VM state.** The driver log ends with `VM TERMINATED (verified)`, and there is no `RESTORE_FAILED_*` or `VM_NOT_STOPPED_*` marker in `..`. First-contact note: the convoy yaml and src maps are v3-time pins never checked on this VM. If one differs, the snapshot refuses with nothing changed, but the restore's no-snapshot branch fails the same pins and writes a `RESTORE_FAILED_*` marker. In that case `vm/deploy/` has no `SNAPSHOT.done`; read `pins_v3_restore.log`, then rule.
2. **Map.** The `ov` step printed `MAP OK`. The installed convoy map had never been seen on this VM before.
3. **Smoke verdict.** `../SMOKE_CHECK.txt` says PASS. Read every line:
   - all six `CRITERION` lines;
   - any `WARN standoff-inherited floor stops` line, and whether `robot_2` then backed up at once;
   - `standoff_gap_gt_m`;
   - `goal_stack_min_m`;
   - the timing line, where the dispatch should come well before the release (about 120 s);
   - `slack_to_260s_horizon`, which needs ≥ 30 s.
4. **RTF.** If the smoke shows RTF below about 0.25 (slot over 20 min), decide on the cap before the follow-up (section 10).
5. **Stop rule.** If the smoke did not resolve, or the check failed, stop and ask the owner. Do not run `follow`.

---

## 15. Owner Decisions Needed Before Launch

Each has a recommended default, which the kit implements.

1. **Primary safety rule.** Default: success = resolved + 0 **manoeuvre** floor stops + 0 GT contact frames in [onset + 2 s, end]; the IB10 rule (any floor stop, GT min from t0) is reported beside it. Alternative: the IB10 rule as primary, which may fail Layer-2-on episodes on the pre-existing standoff gap alone.
2. **Floor at the standoff (section 8.4).** Default: run as registered and let the smoke show it. If `robot_2` is pinned, stop and rule. The floor-off and lower-floor options are not pre-approved.
3. **Goal-stack latch.** Default: not resolved in the primary; `gate_cleared` and a sensitivity line excluding latched episodes reported; never re-run.
4. **Late dispatch.** Default: labelled, counted by its GT outcome. The scope document proposed counting it as a failure.
5. **Grounding.** Default: legacy (`63f50f91`) in all arms, stated as a caveat against IB10. Alternative: derived, never run on this scene.
6. **Hold-back.** Default: keep 120 wall-s. The measured margin is about 60–75 s at RTF about 0.30.
7. **Map start-up failure.** Default: retry the slot as a bring-up abort (`MAP_STARTUP_GATE=retry`). Alternative: report only, the IB10 safety behaviour.
8. **Wall clock.** Default: 6.5 h cumulative, with the follow-up in one invocation. Alternative: a lower cap with the follow-up split over two invocations (the resume is automatic).
9. **Arm C script.** Default: the tracked `[oracle, none]`. Alternative: the intersection-style `[none, oracle, none]`, which costs one cooldown of margin and needs an untracked file on the VM.
10. **n.** Default: 5 per arm, with the smoke counted as Arm C 1 once accepted.

---

## 16. Corrections and Updates to the Scope Document

`docs/reports/2026-11-13-convoy-s6-live-experiments-scope.md` is committed unedited. Where it is wrong or out of date:

- **The fix is no longer unknown.** Its sections 3, 8 and 11 say the fix branch has no code and the key is unknown. The fix landed (`8933863`), with the key `scoped_clearing_exemption` and the closing-waiver thresholds 0.05 m / 3 readings. The IB10 safety run used it on 2026-11-14.
- **Bridge-2 is moot.** IB10 has since run on the fixed runtime with the key on (`docs/reports/2026-11-14-ib10-safety-default-arm-results.md`): Arm A 5/5, Arm C 4/4 valid plus the re-run.
- **The floor at the standoff was missed.** It notes the floor was never used on the convoy, but not that the convoy standoff can sit below it (section 8.4 here).
- **Caps and arms changed.** Its caps ($3.00 total, $0.50 per episode, 6 h per invocation) and its arm set (O1 + 5 A + 5 B, no Arm C) are replaced here, per the brief: $1.00 total, a cumulative 6.5 h, and Arm C added.
- **Late dispatch.** Its proposal to count a late dispatch as a failure is replaced by counting it by GT outcome (owner decision 4).
- **The 1-in-6 latch rate is half-verified.** "1 latch in 6 oracle runs" at ±0.36 rests on the 0.4448 m loop-family run, which is not on disk. 0 of the 5 runs on disk latched.
- **Derived-mode claims only partly re-checked.** Park x 1.611, escorts 4.171 / 4.743 and the `robot_4` latch were not re-verified here. Only the backup (1.37–1.51 m), the base escort (2.35 m) and `retreat=default:no_choice` were.
- **Legacy lateral not re-checked.** "Lateral 0.36" was not re-checked; `reground_cvl.py` does not print a lateral key.
- **Wall-time estimate.** Its 17–22 min per slot is consistent with this document's 17–23 min.
- **Repeats.** Its "no pose jitter" is verified here. Its reading that repeats are near-identical holds for the decision inputs, not for the standoff gap or the goal-stack margin (section 3).
- **Layer2off pilot as an Arm B reference.** `l2_03_b3_s42` used the mock no-congestion backend with Layer 2 on, not `reasoning_enabled: false`. It is a must-fail fixture for this Arm B gate, not a positive. The Arm B positives are the 2026-11-13 IB10 Arm B bundles.

---

## 17. Verified Offline, and What Only the VM Can Show

**Verified offline (2026-11-14):**

- md5s at 68e67b5 and HEAD of every pinned file;
- the 3-file runtime delta;
- the merged safety file (= the IB10 safety run's);
- the legacy file (= `b3_rag.yaml`);
- both overlays and their loader-resolved diff;
- Arm C re-grounding on 6 snapshots, legacy vs derived;
- the standoff gaps and the floor replay (5 bundles);
- the absence of pose jitter;
- `ep_run_cvl.sh`'s arm check, executed verbatim on the fake tree;
- the goal-stack minima;
- the trigger, dispatch and release timing of the 6 recorded oracle runs;
- the ER-2 latencies;
- `fc_launch.sh` in DRY_RUN for Arm C;
- the gates (55 cases), restore (10 cases) and dry test.

**Only the VM can show:**

- that the convoy yaml and src maps are at the 68e67b5 bytes (first contact; a mismatch stops the run at the snapshot);

- that the installed convoy map is present at the 68e67b5 bytes;
- that the convoy USD builds and validates on this VM;
- the real colcon deploy and the key line in a live M4 log;
- whether the floor pins or only slows `robot_2` at the standoff;
- the convoy's RTF and standoff gap on this VM;
- the plan channel and the key-on monitor on a live convoy;
- the goal-stack latch rate at this runtime;
- what a live ER-2 answers on the first trigger, and whether it names `robot_3` and `robot_4`. The smoke (Arm C) never exercises the Gemini path; e02 is the first live call, preceded by the probe;
- the Gemini quota.

**Kit** (`data/logs/vm_runs/convoy_live/kit/`, gitignored):

- `kit_md5_cvl.txt` (VM list, 33 entries) `d681f6a92804a2b2ca28513e1aae17a2`;
- `kit_md5_all_cvl.txt` (45 entries) `1502eff375f1afdd0e8ee65f257cd2f4`.
