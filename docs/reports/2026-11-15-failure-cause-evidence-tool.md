# Failure-Cause Evidence Tool: Methods, Coverage and Validation

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: an offline tool that computes the mechanical inputs of the frozen failure-cause rubric, and the evidence sheets it produced for 33 five-robot S1b episodes. No VM, no API call, no runtime code change; every bundle was only read.

---

## Scope

- **Rubric.** `docs/reports/2026-11-15-failure-cause-rubric-and-robot5.md`, section 7, frozen at `b70d925` on `demo/campaign-kits`. The file's last commit was verified to be `b70d925`. The rubric is not edited here.
- **Tool.** `scripts/failure_cause_evidence.py`, md5 `6c926768571403d7ee2da318d5b59ad9`. Every sheet records this md5, and all 33 sheets were produced by that file. Unit tests are in `tests/unit/test_failure_cause_evidence.py` (26 tests, all passing; only this file was run).
- **Outputs.** All under `data/experiments/2026-11-15-failure-cause-evidence/`:

| Path | Content | For |
|---|---|---|
| `rater/EV-*/sheet.{json,md}` | Events sheet: arm, episode id, seed, run and session ids, outcomes and guard verdicts removed; request ids replaced by `D1…Dn` | raters |
| `rater_gt/GT-*/sheet.{json,md}` | GT-only sheet: failure units, T2 at onset, X3 GT input, contacts. Its ids are not linked to `EV-*` | raters (arm-blind part) |
| `key/key.json` | Opaque id to episode, bundle, stratum, arm and decision-id map | reconciliation only |
| `full/<episode>/evidence.json`, `sheet.md` | Full sheet, with the frozen outcome fields | reconciliation only |
| `interception/legs.{tsv,json}` | Interception-table input | not raters |
| `coverage.json`, `leak_check.json` | Coverage per episode; leak grep result | — |
| `inputs/` | Episode manifest, exclusions, outcome fields copied from source files | — |
| `replay/` | Raw TSV from the v7l guard replays and the v7p stall-abort replay | — |
| `dumps/` (not committed) | Every hypothetical grounding per snapshot | — |

- **Rater rule.** Raters get `rater/`, `rater_gt/`, rubric section 7 and the bundles. They do not get `key/`, `full/`, `interception/` or `replay/`.

## Episodes

| Stratum | Episodes | Notes |
|---|---|---|
| prereg-v3 tranche 1 (registered; never pooled) | E27–E31, Arm A and Arm B (10) | E27 B is attempt `a2` |
| ER-2 pilots | E6–E26 (21) | E10, E17, E23, E24, E25 and E26 were cut short by the stop rule (A33 `censor_reason` `stop_flag`) and are flagged |
| November takes (illustrative; own stratum) | `m5D_t01_a1`, `m5V_t01_a1` | — |
| Excluded | E1–E5 | echo mock (apparatus) |
| Excluded | v4 shadow pos21–27 | exploratory, different kit |

- The bundle paths are in `inputs/episodes_manifest.json`.
- Outcome fields are copied by named key only from the rubric 5.3 sources:
  - `[T]` `batch6/scores_t1/s1_scoring.jsonl`;
  - `[O]` `batch5/agg_b5.json` `gridlock.tasks_completed` / `gt_end_rel_s`, with `[P]` censor reasons;
  - `[R]` the rubric's text for the two November takes.
- These fields appear only in the full sheets. The evidence computation reads no report.

## What the Tool Computes

**Code trees.** Each tree is asserted at start-up and recorded in every sheet.

| Piece | Tree | Functions |
|---|---|---|
| Failure units, matching | this tree's `benchmarks/s1_scoring` (no diff to `3c71503`) | `bundle_io.read_bundle`, `conflicts.conflict_episodes(ConflictParams())`, `classify_analysis`, `match_analysis` |
| T1 | v7n `a412949`; `command_grounder.py` md5 `951c23b7…` checked | `ground_reasoner_result`; `reasoning_pipeline.yield_refusal_fan_out` and `empty_reroute_fallback` (M5's withhold rules) |
| Contacts, T2 footprint | v7m `b5eaee5`, imported by path, not copied | `contact_geometry.compute_contact_frame`, `scene_static_boxes`, `robot_box_gap`, `robot_robot_gap`; `recompute_gt_contacts.recompute_bundle` |

**1. Failure units (rubric 7.1).**

- Conflict FUs are A33 conflict episodes with `to_end` true.
- A lone stall is a robot within 0.05 m of its final GT pose over the last 60 s that is not dwelling at censoring and is in no conflict FU.
- Each unit carries:
  - the evidence-gate inputs (step 1);
  - the chain-rule links (step 2): dispatched in [t0 − 60, t0] or executing at t0. An end-window variant is emitted as well.
  - the chain start;
  - the V1 input;
  - an X3 GT input: an FU pair within 0.45 m with both robots below 0.05 m/s until censoring;
  - an X2 input (see Limits);
  - its GT contacts.

**2. Event timeline per unit.** In rel-s, from 60 s before t0 (or from the chain start) to censoring:

- analyses (raw text and parsed decision, parse status, parser degradations, contract checks C1–C3);
- grounding: provenance, edits, refusal, degradation tags, swap/handoff tags, robots dropped, the `vlm_verbatim`-but-contradicted flag;
- dispatched or withheld commands;
- M4 leg starts and terminal statuses;
- GT contact and sub-margin spans;
- M1 STALE spans;
- exempt-pair changes and safety-stop spans;
- Nav2 abort lines.

Wall-clock lines are mapped with the linear fit over `sim_t=` lines in `m4.log`. The fit and its residual are in each sheet's `clock`.

**3a. T1 decision substitution.**

- **Snapshots:** the onset snapshot (first `m5_scene.jsonl` row within 1 s after t0) and each analysis matched to the FU.
- **H:** over the FU robots plus the two nearest others:
  - every yielder/passer pair;
  - every yield with 2–3 passers in every order, with the yielder last (the schema requires `crossing_order` to be a permutation of `involved_robots`);
  - every `reverse` of 1- and 2-subsets and of the full set;
  - `reroute` with each lead;
  - `temporary_wait`;
  - `convoy`, `priority_override` and `junction_clear` with each lead.

  That is 237 hypotheticals for 5 candidates and 88 for 4.
- **Motion:** an FU robot gets a reverse, backup, escort or reroute *with waypoints*, and M5 would not withhold the command. A reroute without waypoints is a no-op in M4 (`empty_reroute_fallback` docstring). It is counted separately as `n_motion_counting_empty_reroute`.
- **Variants:**
  - as written (the inputs rubric 7.4 lists);
  - plus M5 task intents rebuilt from `tasks_*.jsonl`;
  - all guards on (`escort_obstacle_guard` and `escort_park_clearance`, the only obstacle guards in `a412949`; the reverse guard does not exist in that tree).

**3b. T2.**

- Footprint: the URDF chassis box.
- 8 headings, 0.01 m steps, up to 3.0 m.
- Required gap: half-width (scenario geometry `robot.half_width_m` 0.09) + 0.05 = 0.14 m, to every builder box (active at that GT time) and to every other robot's chassis.
- Success: a pose at least 0.45 m (centre distance) from every other robot.
- Output: per robot and heading, the start-pose gaps, a `start_within_required_clearance` flag and the shortest move.

**3c. T3 execution check.** Per dispatched backup, reverse and escort leg:

- M4 terminal status and text;
- GT maximum displacement and its fraction of the commanded distance (< 50 % gives `not_executed`);
- minimum footprint gap to any builder box (with id, declared or not, and time), and to any robot;
- contact spans in the window.

Tags are orthogonal fields:

- `completed`;
- `pinned_on_{declared|undeclared}_box:<id>`: at the leg's end the gap is ≤ 0.005 m and the robot moved < 0.05 m over the last 10 s;
- `pinned_on_robot`;
- `stalled_clear`: not COMPLETED, still for the last 10 s, and nothing within 0.05 m;
- `ended_by_deadline`: FAILED with an explicit "timed out" line, or, for backups, wall-clock elapsed ≥ max(15 × L / 0.1, 30) − 1 s (v7n `nav2_adapter.py:176-190`);
- `escort_not_admitted`: no `gate_admit` line.

Leg windows start at the M4 handover `sim_t` (escorts: `gate_admit sim_t`). They end at the terminal line, mapped by piecewise interpolation between neighbouring anchors. The single fit has residuals up to 1.9 s, which is large against a 13 s leg. Event ordering keeps the rubric's single fit.

**3d. Guard verdicts.**

- `escort_obstacle_replay.py` and `reverse_obstacle_replay.py --contact-root v7m` were run from v7l `92158d3` (md5 `b3fd89c9…`, `23cd7a12…`) over the 23 Arm A bundles, read-only. They wrote to `replay/`.
- They feed only the interception table. Per rubric 6 and 7.2, G5 is the live-leg check or the recomputed GT gap of a commanded leg, both of which are on the sheets. No rubric clause uses the on/off verdict for a cause code.

**4. Blinding.** Rubric 5.1 and 7.7: arm can be hidden only on GT-derived fields. Two renderings exist, with unlinked opaque ids:

- an events sheet. Arm is not stated, but decision content reveals it (rubric 7.7 says this cannot be blinded);
- a GT-only sheet, which keeps T2 at onset only (analysis snapshots exist in Layer-2-on arms only).

Report text is never read. The `attribution` and `churn_class` fields are never read.

## Results

**Units.**

- 58 FUs: 55 conflicts and 3 lone stalls; none was excluded for dwelling.
- By stratum: tranche 1 A 10 (8 + 2 lone), tranche 1 B 11 (10 + 1 lone), pilots 33, November 4.
- All 3 lone stalls are robots that had finished their tasks at censoring. See the clause list.

**Decision-substitution fidelity.** Recorded positive decisions re-grounded on v7n `a412949`:

| Stratum | As written (rubric inputs) | + stage-2 label | + stage-2 + task intents |
|---|---|---|---|
| Tranche 1 Arm A | 24/26 | 25/26 | 26/26 |
| Pilots E6–E26 | 100/111 | 106/111 | 108/111 |
| November takes | 15/17 | 15/17 | 17/17 |
| Arm B | no recorded decisions (fidelity unverifiable in-bundle; T1 params taken from the paired Arm A bundle's artifact nearest before the snapshot) | | |

- **Every miss is the A26 retreat shield.** Waits lack `retreat_shield_hold`, or shield tags are missing, or the stage-2 letter is missing. Under "+ intents" only 3 remain: E18 `56b599af` and E20 `f269ab37` / `c18ade97`. There the rebuilt task intents do not reproduce the live shield choice.
- **Episode-level gate as written:**
  - fully usable: E6–E9, E12, E14–E17, E19, E23, E26, E27A, E30A, E31A, `m5V`;
  - unusable (at least one decision does not reproduce): E10, E11, E13, E18, E20–E22, E24, E25, E28A, E29A, `m5D`.
- Under "+ intents", only E18 and E20 stay unusable. Per-snapshot status is in each sheet. The rubric's `U:T1_fidelity` applies to the as-written column.

**T1 at onset.**

- The motion set is non-empty at every one of the 58 onset snapshots, in every arm.
- The cause is mostly 1-robot `reverse` hypotheticals: the grounder's `reverse` branch refuses only same-side reverses.
- Under the strict motion definition, EG1 and G7 therefore cannot fire at t0 (rubric 7.5 step 3) in this data set.

**T2.** 62 of the 160 T2 snapshots have an FU robot that already starts inside the 0.14 m clearance (see the clause list).

**Interception table.** 57 dispatched escort and reverse legs:

- 35 reverse legs, all reproduced by the v7l replay. 31 are in commands the reverse guard refuses; 4 are unchanged (E17 `150b95a6`; m5V `b07a700f` ×3).
- 22 escort legs: 2 refused (E18 `1feb2c4e`; `m5D` `a15f3fc5`) and 20 unchanged. Two of the unchanged were never admitted (E17 `6745a136`, `6d37a549`), so they have no physical outcome.
- The stall-abort column was filled from v7p (see below).

## Validation on the Two Documented Cases (Not Used for Tuning)

Every tool parameter was fixed in code before either case's output was read.

- **`m5D_t01_a1`, verified by running.** Leg `a15f3fc5:robot_3:escort` belongs to decision 2 in time order (`D2` on the events sheet).
  - M4 FAILED, "escort timed out in phase drive"; `ended_by_deadline` true.
  - GT moved 0.516 of 1.604 m, so `not_executed(<50%)`.
  - Minimum gap −0.0002 m to `obstacle_2`.
  - Tag `pinned_on_declared_box:obstacle_2`, pinned from 115.24 rel-s (= GT sim 146.70 s; ROS sim 147.34 s) to 172.04 rel-s, 56.8 s.
  - This matches the documented "pinned on `obstacle_2` from sim 146.7 s" on the GT clock.
  - The A33 FU containing robot_3, {robot_2, robot_3}, opens later (t0 240.94 rel-s). Under the rubric's 60 s chain window the escort is therefore not linked to that unit in either window variant. The earlier robot_2/robot_3 encounter (≈ sim 103) closed and is not a to-end unit.
- **October reverse `d374802a`, verified by running.** The v7l replay table places it in E12 (`batch2/s1b_E12_seed12_er2_c1`).
  - `d374802a:robot_2:reverse`: COMPLETED, GT moved 1.301 m, minimum gap −0.0015 m on `rack/NW_north`, an undeclared builder box. Contact span 28.44–32.24 rel-s.
  - robot_4: COMPLETED, minimum gap 0.211 m.
  - Both match the v7l §8.5 row (−0.0015 m, rack/NW_north; r4 0.208 m; our window is 0.003 m different).
  - The legs are chain-linked to FU2 {robot_2, robot_4} (t0 40.44 rel-s).
  - The guard verdict is refused (`obstacle_5`@1.267), from the replay.

## Rater-Sheet Leak Check (Verified by Running)

`leak_check.json` holds zero hits over 66 rater sheets (33 events sheets and 33 GT sheets, JSON and Markdown). The patterns were word-aware:

- arm labels: `arm a/b`, `armA`, `l2off`, `er-2`, `gemini`, `confT1`, `confirmatory`, `echo`;
- episode labels E1–E31, `m5D`, `m5V`;
- `attribution`, `churn_class`, "primary cause", "conclusion";
- `data/logs`, `/Users/`, the repository name;
- `tranche`, `pilot`, `demo`, `run_id`, `session_id`, "seed";
- literals: every bundle name, seed, run id and session id.

A separate plain `grep` for the same literals, and for the request-id prefixes cited in reports (`d374802a`, `a15f3fc5`, `95066420`), also found nothing.

## Rubric Clauses Not Applied Mechanically as Written

1. **7.1, wall-clock mapping.** "wall-clock lines are mapped with the linear fit over `sim_t=` lines in `m4.log`."
   - All 5 Arm B `m4.log` files contain zero `sim_t=` lines, because nothing is dispatched.
   - Arm B wall-clock events (Nav2 abort lines, safety-stop spans) are left unmapped and marked `U:no_m4_clock_anchor`. No other clock was substituted.
   - GT-derived and M1-stamped events are unaffected.
2. **7.4 T1, "Inputs"** (params, geometry, obstacles, snapshot goals). The gate cannot reproduce retreat-shield commands without M5 task intents, which the clause does not list. Rates are given three ways (above). The as-written column sets `U:T1_fidelity`.
3. **7.4 T2.** "The swept footprint must stay at least half-width + 0.05 m from every scene box … and from every other robot's footprint."
   - Applied literally: the start pose is part of the sweep.
   - A robot that starts within 0.14 m of a box or robot therefore fails every heading, including moves away. This affects 62 of 160 snapshots, and each is flagged per robot.
   - The clause does not say which half-width; the declared 0.09 m was used.
   - It also gives no maximum move; 3.0 m was used.
   - A robot already at least 0.45 m from all others passes at 0.01 m.
4. **7.1, lone stall.**
   - "the start of the lone stall's stationary run" is undefined. Read as the earliest sample after which every pose stays within 0.05 m of the final pose.
   - The rubric excludes only dwelling robots. All 3 lone stalls found are robots that had finished their tasks and are parked; they are kept and flagged.
5. **7.2 X2,** "under an active Nav2 goal." Goals are not logged. The input is a run of at least 60 s, stationary, with no M4 leg covering it and the task phase `traveling`. Each run carries the fraction covered by the robot's own safety-stop spans; M4 cancels Nav2 goals under a latch.
6. **7.4 H.**
   - "every multi-passer yield with every crossing order of at most 4 robots" is read as 2–3 passers plus the yielder, which comes last.
   - `convoy`, `priority_override` and `junction_clear` "with each lead" put the lead first in `involved_robots`, with no `crossing_order`.
7. **7.4 T1, "sensitivity column with every guard on".** Tree `a412949` has no reverse guard, so "every guard" means the two escort guards.
8. **7.2 V5.** No `accepted_strategies` is registered for the S1b cell, so V5 is not applicable.
9. **T1 at t0.** No recorded decision exists to gate, so the episode-level gate is used.
10. **7.1, "sub-margin interval"** has no threshold. 0.05 m was used.

## Stall-Abort Column

- `vgu-vlm-swarm-v7p` (`fix/m4-stall-abort`) is uncommitted work in progress: `stall_abort.py` md5 `2afb5b86…`, `scripts/stall_abort_replay.py` md5 `b0c89606…`, with tree state in `replay/stall_abort_tree_state.txt`.
- It has a pure detector and a documented replay entry point, so it was run read-only over the 23 Arm A bundles.
- Of 100 primitives it fired on 10; 8 of them are interception-table legs. Examples:
  - `m5D` `a15f3fc5` robot_3 escort fires 10.9 sim-s after admission;
  - E12 `d374802a` robot_2 fires on a COMPLETED reverse.
- These values are **provisional** and must be rerun once that branch is committed.

## Limits

- T1 grounds through `ground_reasoner_result` (the v7l replay precedent), not through M5's full pipeline. Stage 2 is not re-asked: hypotheticals use the top-ranked candidate.
- T1's motion test makes 1-robot `reverse` nearly always count as motion. This is a property of the rubric's T1 definition plus the grounder, and it is not compensated here.
- The task-intent rebuild misses 3 live shield choices.
- T3's "pinned" and "stalled" tags look only at the leg's last 10 s. A pin that clears earlier shows up only in `contacts_in_window`.
- Arm B has no wall-clock mapping (clause 1).
- No primary or contributing code is assigned here; coding is the raters' job.

## Verified and Inferred

| Claim | Status |
|---|---|
| Rubric commit `b70d925`; tree assertions | verified (run) |
| Fidelity rates, unit counts, T1/T2 counts | verified (run) |
| Both validation cases | verified (run) |
| Leak check zero hits | verified (run) |
| Shield as the cause of every fidelity miss | verified from the diffs |
| `retreat_shield` needs intents that the rubric omitted, rather than another cause | inferred |
| Stall-abort column values | provisional (uncommitted code) |
