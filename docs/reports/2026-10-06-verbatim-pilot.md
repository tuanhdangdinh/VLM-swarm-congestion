# Verbatim Pilot: When Do Live VLM Plans Execute Verbatim?

**Prepared:** 2026-10-06

**Revision history:**

- Initial draft: the 11 registered live episodes (ER-2 ×8, gpt-4o ×3) on the v2 tree `a8fc1bc`, with plan metrics, outcomes, refusal accounting and a pre-freeze recommendation.
- Rev 2: review corrections. ER-2's list order is id order or yielder-first, not slot order. The list-order finding is ER-2-only. The strategy-constraint wording is fixed. The "Exec" column is now "Verified legs". The reroute decision context is caveated. B1 junction_clear grounding is added (item G). The complexity trend is stated descriptively. The suite wording is fixed.

---

## Summary

This is the registered verbatim pilot. Its contract is the "Verbatim pilot (registered 2026-10-06)" block of `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` in the main checkout. It is a PILOT, so every episode is excluded from every confirmatory count.

- **Matrix:** all 11 episodes ran exactly as registered. The VM ran the v2 branch tip `a8fc1bc`, not the parked v3 costmap fix. `RECORD=0` throughout. No apparatus re-run was needed. One driver-argument mistake launched nothing and cost nothing (see Apparatus).
- **Emission and consistency:** trigger plans were emitted 11/11 and consistent 11/11. Over all 28 dispatched plans, 26/28 were emitted and 26/26 of those were consistent.
- **Provenance by cell (descriptive; the trend is not monotonic at this n).** Of the 11 trigger plans, 3 were `vlm_verbatim`, 7 `repaired` and 1 `m3_default`:
  - 1-robot reroute: 1/1 verbatim.
  - 2-robot head-on: 1/5 verbatim.
  - 3-robot B1: 1/2 verbatim.
  - 4-robot IB10: 0/3 verbatim.

  Repaired edit distances were 1, 1, 1, 1, 1, 2 and 4. The 4-edit IB10 plan sits exactly at the frozen bound of 4. Three of the four head-on repairs are the designed swap-gate re-grounding (the infeasible robot_1 was named), not a plan-shape defect.
- **ER-2's main repair driver is list order, not choice.** Four of the 7 ER-2 multi-robot trigger plans needed a `reorder` edit. ER-2 lists legs either yielder-first (head-on s44, B1 s42: both verbatim) or in robot-id order, never in prompt-slot order. With id order, the yield or reverse legs can land after the crosses. Two of the four (head-on s43, B1 s43) were reorder-only: they named the correct yielder and would otherwise have been verbatim. gpt-4o never listed a cross before its releasing yield leg (0 reorders in 16 plans).
- **The junction_clear shape mismatch is systematic.** Every ER-2 `junction_clear` plan (2/2 here, 3/3 counting the 2026-10-03 calibration) needed a `substitute` to turn an inside-pair robot into the `yield` leg. The v3.2 gloss describes "back out, then an ordered crossing" and never mentions that leg.
- **Recede axis is not stable.** ER-2's three IB10 recede sets were all different:
  - calibration (v3.1): E-W pair;
  - s42: the N-S pair, the oracle pair, ε-equivalent to χ order (margin 0.047 < 0.15);
  - s43: all four robots.

  gpt-4o never chose `junction_clear` (0/13 IB10 decisions). The mirror-axis question is confounded by the `id_asc` presentation order on this cell.
- **Verbatim is not quality.** gpt-4o's IB10 episode produced 11 `vlm_verbatim` plans: 5 under the unconstrained `reverse` and 6 under weakly constrained `temporary_wait` / `yield` rules. It still ended `clogged` 0/4 after 13 dispatches. 6 of the 16 verbatim plans in the pilot did not dispatch as proposed (`dispatch_matches_plan=false`).
- **Refusals:** gpt-4o had 1 refused attempt in 21 stage-1 attempts, recovered on retry. There were 0 terminal refusals, 0 grey-image fallbacks and 0 stage-2 refusals. ER-2 had 0 refusals.
- **Spend:** ≈ $0.33, about $0.23 gpt-4o and an estimated $0.10 ER-2 (rate assumed). The hard stop was $10.
- **VM time:** 02:56–06:39 UTC, 3 h 43 min.
- **Pre-freeze recommendation:** adjust the grammar on two evidence-backed points: list order, and the junction_clear leg shape. Clarify three metric definitions (no prompt change). Options are listed below; no edits were made.

---

## Apparatus

### Deploy and restore

- **Pre-deploy state.** The VM source tree md5-matched `a8fc1bc` on all 742 tracked non-doc files. The one exception is the VM-pristine `orchestrator.yaml` (`1f656533…`, the prereg-v1 tag version, kept by every driver as the pristine reference). The four costmap-fix runtime files were at their `a8fc1bc` md5s in both the source and installed trees, not at the fix md5s (`3cdc250f…`, `65a9cc2a…`, `cbc33745…`, `9cf43a58…`).
- **Rebuild.** `swarm_execution`, `swarm_orchestrator`, `swarm_perception` and `swarm_simulation` were rebuilt with their `build/` caches purged first (`_vm_driver/vp_rebuild.sh`). Afterwards, 126 installed runtime files were checked against source with 0 mismatches. A body check of 49 `.pyc` files (bytes after the 16-byte header) found 0 differences. `swarm_interfaces` was not rebuilt: its source was unchanged and its generated tree was verified identical.
- **Restore (after the pilot).**
  - The source manifest is identical to the pre-deploy manifest.
  - The installed tree is identical to the pre-pilot snapshot except for `.pyc` headers: the nine `swarm_execution` modules from the rebuild, and `execution.launch` rewritten at run start (trap 19). All 49 `.pyc` bodies match a fresh compile.
  - Configs are `1f656533…` in both source and installed copies, and rag is `e18c723c…`.
  - No pilot GT directory was left behind, `pgrep` (Isaac, fc_launch, probe, watcher) is empty, and the GPU is at 0 % / 171 MiB.
  - The VM was left RUNNING as found.
- **Per-run gates.** Every counted run passed the following:
  - `pgrep -f run_simulation` was EMPTY before launch (0 s waits).
  - `GATE OK` was printed, and M5 was confirmed started by its session line and analysis count. `M5_STARTED.txt` is per run.
  - No 429 or quota lines appeared.
  - `RESTORE OK` was recorded with source and installed md5s.

  No Isaac process outlived its run, because every `REC_SEC` covered the scene duration. The `vp_chain.sh` settle step found the process table clear every time, so no PID kill was needed.

### Cell configurations (overlays, `_vm_driver/gen_vp_overlays.py`, every key asserted by `yaml.safe_load`)

| Cell | Overlay (md5) | Configuration |
|---|---|---|
| Head-on `head_on_asymmetric_w0p2_eopen_bshort_o0` | `ho_orchestrator.yaml` (`b571636a…`) | The 2026-09-28 calibration apparatus: goals (2.6, 0) / (−1.5, 0), gate `swap`, `prompt_robot_order: random` (seed null), obstacles ON (`obstacle_1` at x = −1.85, `MODALITY=on`), arrival check, shadow on, debug and raw frames. Added: `plan_channel_enabled: true`. |
| B1 `bottleneck_merge` | `b1_orchestrator.yaml` (`7e4ba315…`) | The registered goal-table row: robot_3 `start_delay_sec` 80, junction box `half_length_m` 1.1 with arms, `grounding_aisle_x_band_m` [−0.46, 0.46]. "FCFS zone" means `shadow_classical_zones: []` as registered: there is no Arm B FCFS referent, and rag.yaml `classical.fcfs_zone_radius_m` 1.0 is untouched. Also `static_obstacles` absent, `prompt_static_obstacles` false, the collection apparatus (gate `swap`, random order, debug and raw frames) and plan channel ON. The difference from the `b1_fix` smoke config is apparatus only (that smoke used gate `off`, `id_asc` and no plan channel); the geometry and goals are identical. |
| IB10 `intersection_bottleneck` | `ib10_orchestrator.yaml` (`d1e11073…`) | The step-6 / plan-grammar calibration overlay, verbatim. It has the junction fields (`junction_recede_offset_m` 1.2, `junction_backup_clearance_m` 1.1, `junction_recede_stagger_m` 0.2, `tracked_extent_m` 1.75), the `crossing_1` zone, gate `off`, **`id_asc`** and plan channel ON. |
| Reroute `loop_detour_probe_lethal` | `rr_orchestrator.yaml` (`1f019ae1…`) | The 2026-10-06 live reroute demo overlay, verbatim. robot_1 is held (`start_delay_sec` 75), `reroute_waypoints` [[0.3, 1.2], [1.8, 1.2]] are set, plan channel is ON, and the **stall detector is suppressed** (`stall_threshold_sec` 600). `REC_SEC` was 650 instead of the demo's 450, so the M5 tail reached sim 240.0. |

Common to all cells:

- prompt v3.2 (the `_PLAN_GRAMMAR` "must agree with your own yield_robot" line was present in 52/52 stage-1 prompts);
- derived grounding with stage 2 on;
- `max_repair_edits` 4, ε 0.15;
- `RECORD=0`;
- served models `gemini-robotics-er-2-preview` and `gpt-4o-2024-08-06`, each preflighted once (both parsed OK).

**Reroute stall setting (stated as required).** The detector was SUPPRESSED, replicating the demo. The trigger used the demo apparatus: the manual trigger probe (`waypoint_probe.py` live copy, retries) plus its ONE operator follow-up trigger. The follow-up rule was fixed before it fired (`_vm_driver/rr_watch.py`): after robot_1 first moved more than 0.10 m, fire once if its odometry moved less than 0.05 m in any 20 sim-s window. It fired at sim 102.9. Suppression forfeits that episode's natural re-analysis data.

**One no-launch mistake (not an episode).** The first launch of chain B passed its spec strings through zsh, where `$HO:h…` is a path modifier, so the scenario name was mangled. The driver did not abort on the missing overlay file, and `fc_launch` refused the scenario in about 1 s. No Isaac process started, there were 0 API calls and the configs were restored OK. The run is kept as `_vm_driver/chain_logs/_INVALID_vp02_argparse_no_launch`. The driver now refuses on a missing overlay or an unknown backend. All later specs are read from files.

---

## Per-Episode Table

The trigger plan is each episode's first dispatched plan.

Abbreviations used in the next two tables:

- "yld pre": yielder agreement before repair against `correct_yielder` robot_2 (head-on and B1).
- "ord pre": `oracle_order_agreement` (B1 `correct_order` [robot_1, robot_3]), or the IB10 χ-pair scorer.
- "re-an": re-analyses after the trigger, split as no-congestion / dispatched.
- vb: `vlm_verbatim`; rep(n): `repaired` with n edits; m3: `m3_default`.
- yld: `yield`; rev: `reverse`; tw: `temporary_wait`; jc: `junction_clear`.

| # | Episode | Drawn order | Trigger plan, verbatim | Trigger prov. (edits) | yld pre / ord pre | Outcome (arrivals) | re-an | Replans / holds |
|---|---|---|---|---|---|---|---|---|
| 1 | ER-2 head-on s42 | id_desc | `yield` r1; [r1:yield, r2:cross] | rep(1): swap r1↔r2 | ✗ | resolved (2/2) | 4 / 0 | 0 / 0 |
| 2 | ER-2 head-on s43 | id_asc | `yield` r2; [r1:cross, r2:yield] | rep(1): reorder r1↔r2 | ✓ | resolved (2/2) | 4 / 0 | 0 / 0 |
| 3 | ER-2 head-on s44 | id_asc | `yield` r2, order [r1, r2]; [r2:yield, r1:cross] | vb | ✓ | resolved (2/2) | 2 / 0 | 0 / 0 |
| 4 | gpt-4o head-on s42 | id_desc | `yield` r1; [r1:yield, r2:cross] | rep(1): swap | ✗ | intermittent (2/2) | 0 / 1 | 1 / 0 |
| 5 | gpt-4o head-on s43 | id_asc | `yield` r1; [r1:yield, r2:cross] | rep(1): swap | ✗ | resolved (2/2) | 4 / 0 | 0 / 0 |
| 6 | ER-2 B1 s42 | [r3, r1, r2] | `yield` r2; [r2:yield, r1:cross, r3:continue] | vb | ✓ / ✗ | clogged (0/3) | 1 / 2 | 2 / 0 |
| 7 | ER-2 B1 s43 | [r3, r2, r1] | `yield` r2; [r1:cross, r2:yield, r3:continue] | rep(1): reorder r1↔r2 | ✓ / ✗ | clogged (0/3) | 0 / 2 | 2 / 0 |
| 8 | ER-2 IB10 s42 | id_asc | `junction_clear`, order [r1..r4]; [r1:cross, r2:wait, r3:reverse, r4:reverse] | rep(2): reorder r1↔r4, substitute r1→yield | pair ✓, order ε-equiv. | resolved (4/4), rank (1, 4, 4) | 5 / 0 | 0 / 0 |
| 9 | ER-2 IB10 s43 | id_asc | `junction_clear`, order [r1..r4]; [r1:rev, r2:rev, r3:rev, r4:rev] | rep(4): reorder r1↔r3, reorder r2↔r4, substitute r1→yield, substitute r2→cross | pair ✗ (all four) | resolved (4/4), rank (1, 4, 4) | 3 / 0 | 0 / 0 |
| 10 | gpt-4o IB10 s42 | id_asc | `yield` r1, order [r2, r3, r4, r1]; [r1:yield, r2:cross, r3:cross, r4:cross] | m3 (`repair_bound_exceeded`) | no jc | clogged (0/4), rank (0, 0, 0) | 0 / 12 | 12 / 0 |
| 11 | ER-2 reroute s42 | id_asc | `reroute`; [r1:reroute] | vb | — | resolved (1/1) | 0 / 0 (+1 no-congestion before) | 0 / 0 |

Further notes on the table:

- **Outcome scorers:** `coverage_scene_scores.py flow` for head-on and reroute, `b1` for B1, `ib10` for IB10. Head-on: delay sums 147–153 s and conflict dissolution 66–69 s in every episode.
- **Episode 4:** its second dispatch is the "intermittent" class, a gpt-4o `reroute` of robot_2 at sim 97.3 (verbatim, but `dispatch_matches_plan=false`).
- **IB10 ER-2 episodes:** both are inside-first and yielder-last.
- **Episode 11:** the first trigger (robot held at spawn, sim 17.5) answered `congestion_detected=false`; the demo's first trigger had produced the reroute. robot_1 then self-detoured toward the loop and stalled at (0.46, 0.49) for about 20 s. The follow-up trigger's reroute COMPLETED (waypoint 0 reached at 0.036 m, waypoint 1 at 0.101 m), and robot_1 arrived 0.07 m from goal at sim 135.6. On the v2 tree the latch occurred, but the declared reroute still completed (n = 1). **Decision-context caveat:** the plan was made after robot_1 had already detoured toward the loop on its own and stalled about 0.7 m from waypoint 0. It was not held in the primary aisle as in the demo, or as in the pre-fix waypoint validation that failed. This completion is therefore NOT comparable to that failure and must not be cited against the costmap finding.
- **`order_equivalent`** was never true (0/28 plans). In IB10 s42 the repair's position swap happened to put the recede legs in χ order ([r4, r3]), so the recede ORDER matched dispatch and the flag could not fire. The plan as a whole still has `dispatch_matches_plan=false`, because robot_2's verified `wait` was dispatched as `cross`.
- **B1 outcomes are a known apparatus defect, not a plan effect.** In both trigger yields, ER-2's stage-2 letter "A" mapped to the rank-0 2× lateral candidate (−0.72 m). The yield ran about 250 s and FAILED, which is the Rev 20 (a) / Rev 22 defect. Under the registered Rev 22 rule, both B1 episodes are **decision-scored and excluded from flow metrics**.
- **Phantom `robot_17`.** A known M1 misdetection near robot_1's spawn caused about 10 s of early safety stops in B1 s42 (3 scene rows; seen in earlier runs too).

### Every dispatched plan, verbatim (decision fields as emitted)

Abbreviations: the `strategy` / `yield_robot` / `crossing_order` cell shows the proposed values. "Verified legs" are the plan block's accepted legs, NOT the dispatched commands; where "dm" (`dispatch_matches_plan`) is ✗, M5 dispatched something else. For example, in episode 8 robot_2 was dispatched `cross`, not the verified `wait`.

| Episode | Sim (s) | Proposed `strategy` / `yield_robot` / `crossing_order` | Proposed plan | Provenance (edits) | Verified legs (plan block) | dm |
|---|---|---|---|---|---|---|
| 1 | 27.2 | yield / r1 / — | [r1:yield, r2:cross] | rep: swap r1↔r2 ("robot_1 has 0.70 m retreat room < 1.08 m required") | [r2:yield, r1:cross] | ✓ |
| 2 | 27.3 | yield / r2 / — | [r1:cross, r2:yield] | rep: reorder ("cross leg has no preceding yield leg to release it") | [r2:yield, r1:cross] | ✓ |
| 3 | 25.5 | yield / r2 / [r1, r2] | [r2:yield, r1:cross] | vb | same | ✓ |
| 4 | 27.0 | yield / r1 / — | [r1:yield, r2:cross] | rep: swap | [r2:yield, r1:cross] | ✓ |
| 4 | 97.3 | reroute / — / — | [r2:reroute, r1:continue] | vb | same | ✗ |
| 5 | 26.6 | yield / r1 / — | [r1:yield, r2:cross] | rep: swap | [r2:yield, r1:cross] | ✓ |
| 6 | 29.9 | yield / r2 / — | [r2:yield, r1:cross, r3:continue] | vb | same | ✓ |
| 6 | 110.2 | yield / r3 / [r1, r3] | [r3:yield, r1:cross, r2:continue] | vb | same | ✓ |
| 6 | 196.5 | junction_clear / — / [r1, r2, r3] | `null` | m3 (absent) | [r3:yield, r1:cross, r2:cross] | ✓ |
| 7 | 29.0 | yield / r2 / — | [r1:cross, r2:yield, r3:continue] | rep: reorder r1↔r2 | [r2:yield, r1:cross, r3:continue] | ✓ |
| 7 | 112.0 | temporary_wait / — / — | [r1:cross, r3:wait, r2:continue] | rep: substitute r1→wait | [r1:wait, r3:wait, r2:continue] | ✓ |
| 7 | 126.7 | junction_clear / — / [r2, r1, r3] | [r3:reverse, r2:cross, r1:wait] | rep: swap r2↔r3, substitute r3 | [r2:reverse, r3:wait, r1:wait] | ✗ |
| 8 | 34.5 | junction_clear / — / [r1, r2, r3, r4] | [r1:cross, r2:wait, r3:reverse, r4:reverse] | rep: reorder r1↔r4, substitute r1→yield | [r4:rev, r2:wait, r3:rev, r1:yield] | ✗ |
| 9 | 34.8 | junction_clear / — / [r1, r2, r3, r4] | [r1:rev, r2:rev, r3:rev, r4:rev] | rep: reorder r1↔r3, reorder r2↔r4, substitute r1→yield, substitute r2→cross | [r3:rev, r4:rev, r1:yield, r2:cross] | ✓ |
| 10 | 35.3 | yield / r1 / [r2, r3, r4, r1] | [r1:yield, r2:cross, r3:cross, r4:cross] | m3 (repair bound exceeded) | [r1:yield, r2:cross, r4:continue, r3:continue] | ✓ |
| 10 | 67.1 | reverse / — / — | [r1:rev, r2:rev, r4:rev, r3:continue] | vb | same | ✓ |
| 10 | 86.8 | temporary_wait / — / — | `null` | m3 (absent) | [r3:wait, r4:wait, r1:continue, r2:continue] | ✓ |
| 10 | 99.5 | reverse / — / — | [r1:rev, r2:rev, r3:continue, r4:continue] | vb | same | ✓ |
| 10 | 119.0 | reverse / — / — | [r1:continue, r2:continue, r3:rev, r4:rev] | vb | same | ✓ |
| 10 | 153.5 | yield / r1 / [r2, r1] | [r1:yield, r2:cross, r3:continue, r4:continue] | vb | same | ✗ |
| 10 | 179.6 | reverse / — / — | [r1:rev, r2:rev, r3:continue, r4:continue] | vb | same | ✓ |
| 10 | 198.0 | temporary_wait / — / — | [r1:continue, r2:continue, r3:wait, r4:wait] | vb | same | ✓ |
| 10 | 210.7 | yield / r1 / [r2, r1] | [r1:yield, r2:cross, r3:wait, r4:wait] | vb | same | ✗ |
| 10 | 237.7 | reverse / — / — | [r1:rev, r2:rev, r3:wait, r4:wait] | vb | same | ✗ |
| 10 | 256.8 | temporary_wait / — / — | [r1:wait, r2:wait, r3:wait, r4:wait] | vb | same | ✓ |
| 10 | 269.9 | yield / r3 / — | [r1:continue, r2:continue, r3:yield, r4:cross] | vb | same | ✗ |
| 10 | 296.5 | yield / r3 / [r4, r3] | [r1:continue, r2:continue, r3:yield, r4:cross] | vb | same | ✗ |
| 11 | 102.9 | reroute / — / — | [r1:reroute] | vb | same | ✓ |

Trigger-plan justifications, verbatim:

1. "Robot 1 should reverse to clear the corridor and yield to Robot 2, allowing Robot 2 to cross first."
2. "Robot 2 has clear space to back up to the right and let Robot 1 pass first through the narrow section."
3. "Robot 2 should yield and back out of the narrow aisle to the east to allow Robot 1 to continue to its goal."
4. "Robot_1 should yield as it is closer to the entrance of the aisle, allowing Robot_2 to proceed."
5. "Robot 1 should yield to allow Robot 2 to pass, as Robot 2 is closer to its goal."
6. "robot_2 has its heading directed towards robot_1 at very close range (0.37m), so it must yield and step aside to allow robot_1 to proceed through the narrow passage."
7. "Robot 2 should yield and wait while Robot 1 crosses the narrow aisle first, resolving the bottleneck."
8. "All four robots are within ~0.5 meters of each other and facing inwards at the intersection, completely blocking each other's paths." Its reasoning field reads: "…robot_4 and robot_3 back out to allow robot_1 and robot_2 to pass sequentially."
9. "A junction clear strategy forces the robots to back out of the intersection lanes to create space, then cross sequentially."
10. "Robot_1 yielding will allow the others to proceed and clear the intersection."
11. "The robot cannot proceed through the blocked corridor and must find an alternative route to reach its goal."

The full artifacts are in `data/logs/vm_runs/verbatim_pilot/<run>/decisions/` (gitignored). Per-analysis extracts are in `_analysis/<run>_plans.json`, and the aggregate is in `_analysis/summary.json`.

---

## Provenance Distribution by Plan Complexity and Backend

Metrics were recomputed with the project's own `score_plan_decision`. `rejection_stage` is not stored in artifacts, so it was recovered from the `rejection_reason` strings (`_analysis/plan_table.py`).

| Cell (legs) / backend | Trigger plans: vb / rep / m3 | All dispatched: vb / rep / m3 | Trigger edit distances |
|---|---|---|---|
| Reroute (1) / ER-2 | 1 / 0 / 0 | 1 / 0 / 0 | 0 |
| Head-on (2) / ER-2 | 1 / 2 / 0 | 1 / 2 / 0 | 1, 1, 0 |
| Head-on (2) / gpt-4o | 0 / 2 / 0 | 1 / 2 / 0 | 1, 1 |
| B1 (3) / ER-2 | 1 / 1 / 0 | 2 / 3 / 1 (absent) | 0, 1 |
| IB10 (4) / ER-2 | 0 / 2 / 0 | 0 / 2 / 0 | 2, 4 |
| IB10 (4) / gpt-4o | 0 / 0 / 1 (bound) | 11 / 0 / 2 (bound, absent) | — |
| **Total** | **3 / 7 / 1** | **16 / 9 / 3** | median 1 |

Edits by type, across all 9 repaired plans:

| Edit type | Count | Reason |
|---|---|---|
| reorder | 5 | All of the form "a cross leg precedes a yield/recede leg". Every one is in an ER-2 plan. |
| substitute | 5 | Three are IB10 inside-pair role fixes (cross or reverse → yield/cross). Two are B1: cross → wait in the `temporary_wait` replan, and a re-role in the `junction_clear` replan. |
| swap | 4 | Three are head-on yielder re-grounding ("0.70 m retreat room < 1.08 m"); this is the swap gate itself. One is B1 junction_clear. |

Which legs:

- **Head-on:** both legs (role swap), or both legs' positions.
- **B1:** the robot_1/robot_2 pair.
- **IB10:** E-W roles were edited in both episodes: r1 in s42, and r1 and r2 in s43. The N-S recede legs were only moved, never re-assigned. In s43 the extra E-W `reverse` legs were re-roled to yield and cross.

Other plan facts:

- **Edit distance:** never above 4. The single 4-edit plan (IB10 s43) is `repaired` only because the bound was re-frozen at 4 on 2026-10-03; at the old bound of 3 it would have been `m3_default`.
- **Consistency:** 26/26 emitted plans were consistent. No plan was rejected as inconsistent. That inverts the v3.0 era, when all three live IB10 plans were inconsistent.
- **gpt-4o vs ER-2:** gpt-4o's verbatim rate rises (11/13 on IB10) because its strategies (`reverse`, `temporary_wait`, `yield` with passive legs) carry no or weak leg constraints, not because the plans are better. See below.

---

## Recede-Axis Stability (IB10)

| Run | Backend | Prompt | Proposed recede set | χ margin r3 − r4 (m) | Pair correct (pre-repair) |
|---|---|---|---|---|---|
| Calibration 2026-10-03 | ER-2 | v3.1 | E-W {r1, r2} (mirror axis) | 0.000 (tie) | ✗ |
| Pilot s42 | ER-2 | v3.2 | N-S {r3, r4}, listed [r3, r4] | +0.047 (χ order [r4, r3]; ε-equivalent) | ✓ |
| Pilot s43 | ER-2 | v3.2 | all four {r1, r2, r3, r4} | −0.004 | ✗ (superset) |
| Pilot s42 | gpt-4o | v3.2 | none (`yield` r1 + three crosses) | — | — (no `junction_clear` in 13 decisions) |

**Answer: not stable, either across episodes or across backends.**

- **ER-2:** three junction plans gave three different recede sets. The mirror axis did not recur as such; s43 includes it within an all-reverse plan.
- **gpt-4o:** never proposed the composite. Its later `reverse` strategy plans alternated between the E-W pair (with or without robot_4) and the N-S pair.
- **Confound:** IB10 runs `id_asc` (the calibration config is binding), so robot_1/robot_2 always sit in the first prompt slots. ER-2's leg list order is id order or yielder-first, not slot-driven (head-on and B1 show it). But its recede-SET choice cannot be separated from a first-slot prior on this cell.

---

## Oracle and Yielder Agreement Before Repair

| Cell | Metric | ER-2 | gpt-4o |
|---|---|---|---|
| Head-on | yielder named = `correct_yielder` robot_2 | 2/3 (s43, s44) | 0/2 |
| B1 | yielder named = robot_2 | 2/2 | — |
| B1 | `oracle_order_agreement` vs [robot_1, robot_3], consistent plans | 1/5 (trigger plans 0/2) | — |
| IB10 | recede pair correct | 1/2 (s42) | 0/1 (no composite) |
| IB10 | recede order (strict / within ε) | 0/1 strict, 1/1 within ε (s42) | — |

**Head-on vs drawn order.** ER-2 named the second-listed robot 3/3: robot_1 under `id_desc`, robot_2 under `id_asc` ×2. gpt-4o named robot_1 2/2, once listed first and once second. The swap gate re-grounded every wrong naming. n is too small for a prior claim; this is descriptive only.

**B1 order metric artifact.** At the trigger (sim 29–30) robot_3 is still held (`start_delay_sec` 80) and is given `continue`. `plan_metrics` drops `continue` legs from the proposed order, so a trigger plan cannot fully name [robot_1, robot_3], and the metric is False by construction. The one True result is a later plan ([r1:cross, r3:wait]).

---

## Refusal and Abstention Accounting (gpt-4o)

| Item | Count |
|---|---|
| Stage-1 calls / attempts | 20 / 21 |
| Calls with ≥ 1 refused attempt | 1 (head-on s43, post-resolution re-analysis at sim 111.4; recovered on attempt 2 → `congestion_detected=false`) |
| Terminal refusals (decision None) | 0 |
| Grey-image fallback used | 0 |
| Stage-2 calls answered / skipped | 4 / 3 (`no_candidates`, IB10) ; 0 refused attempts |
| Abstentions (`congestion_detected=false`) | 4 (all head-on s43 post-resolution re-checks) |

Because no plan came after a grey-image fallback, none needs to be tagged separately.

ER-2 had 32 stage-1 calls with 0 refusals and 6 stage-2 calls answered. ER-2's abstentions (`congestion_detected=false`) were all post-resolution re-checks, plus the reroute cell's first trigger, taken while the robot was held.

**Intra-episode behaviour:**

- `plan_held` was never true, so there were no holds.
- Post-resolution re-analyses on ER-2 cells always answered no congestion, and none dispatched.
- Replans happened only in the clogged or degraded episodes: B1 ×2 each (both after the failed 2× retreat) and gpt-4o IB10 ×12, plus gpt-4o head-on s42's post-yield reroute.

---

## Spend

| Backend | Stage-1 tokens (prompt / completion + thought) | Stage-1 USD | Stage-2 (est.) | Total |
|---|---|---|---|---|
| gpt-4o-2024-08-06 | 53,781 / 6,141 | 0.196 | ≈ 0.03 (4 calls; tokens are not logged) | ≈ 0.23 |
| ER-2 preview | 93,075 / 20,382 | ≈ 0.08* | ≈ 0.01 (6 calls) | ≈ 0.09* |

\*ER-2 has no published preview price in this repo, so Gemini 2.5 Flash list rates ($0.30 / $2.50 per M) are assumed. The preflights add under $0.01. The pilot total is ≈ $0.33, against the < $1 budget.

---

## Pre-Freeze Recommendation (Options, Not Edits)

n is 11 episodes and 28 plans. These are the recommendations the pilot's purpose asks for. Each is evidence-backed and none has been applied.

### A. List-order semantics: adjust before the freeze (strongest evidence)

**Evidence (ER-2-specific; gpt-4o never listed a cross before its releasing yield leg in any of its 16 plans and needed 0 reorders, so a grammar line would likely leave gpt-4o unaffected).**

- 4 of the 9 repaired plans include a `reorder` (5 reorder edits in all, all ER-2).
- 4/7 ER-2 multi-robot trigger plans needed one, and 2 of those were reorder-only. The yielder was correct, so they would otherwise have been `vlm_verbatim`.
- ER-2 lists legs yielder-first or in robot-id order, never in prompt-slot order. With id order, releasing legs can follow the crosses.
- v3.2 states list order only inside the `cross` gloss ("in its assigned turn (the plan's list order)"). It never says that a releasing `yield`/`reverse` leg must come before the crosses it releases.
- As it stands, the agreement rate partly measures list-writing convention.

**Options:**

1. **Grammar (v3.3).** State "list legs in execution order: any yield/reverse legs first, then cross legs in their turn".
2. **Verifier.** Treat the plan as a role assignment and order role classes canonically (yield/reverse before cross) before auditing. A reorder then occurs only within a class, for example a χ order beyond ε.
3. **Metrics only.** Keep both as they are and register a `repaired_order_only` sub-class (verbatim modulo list order) beside the 3-way provenance.

Option 1 changes the prompt pins. Option 2 changes the repair-bound sweep and probably lowers it. Option 3 is the cheapest and keeps every pin.

### B. junction_clear leg shape: adjust before the freeze

**Evidence.**

- 3/3 ER-2 composite plans (calibration plus 2 pilot) needed the inside-pair robot substituted to `yield`.
- The v3.2 gloss ("some robots first back out, then an ordered crossing") and the rule ("at least one reverse or yield leg") never name the composite's yielder.
- ER-2 follows the gloss literally (reverse, then cross or wait).

**Options:**

1. Extend the gloss, for example "…then one robot yields while the others cross in order".
2. In the verifier, accept the last inside-pair `cross` as the yielder-equivalent leg.
3. Register the substitute as an expected vocabulary repair and report IB10 edit distance net of it.

### C. Vacuous verbatim under unconstrained strategies: metric clarification (no prompt change needed)

**Evidence.**

- gpt-4o IB10 had 11/13 `vlm_verbatim` plans under `reverse`, `temporary_wait` and multi-passer `yield`, and ended `clogged` 0/4.
- 6 of 16 pilot verbatim plans did not dispatch as proposed (`dispatch_matches_plan=false`).

**Options:**

1. Report agreement conditional on strategy correctness (the cell's `accepted_strategies`).
2. Report "executed-verbatim" = `vlm_verbatim` ∧ `dispatch_matches_plan`.
3. Add a leg rule for the one unconstrained strategy, `reverse` (≥ 1 reverse leg, covering 5 of the 11 gpt-4o IB10 verbatim plans). That would need a grammar line and a pin change. `temporary_wait` and `yield` are already constrained; they are weak here because a 4-robot `yield` with passive legs passes them.

### D. B1 oracle-order population: metric clarification

At the trigger, the held robot_3 can only be `continue`, so `oracle_order_agreement` is False by construction (0/2 trigger plans). Options:

1. Restrict the oracle order to robots released at decision time (B1 trigger: [robot_1]).
2. Treat a not-yet-released robot's `continue` as neutral.

### E. IB10 presentation order: caveat or config

Recede-axis results on IB10 are confounded with `id_asc`. Options:

1. Collect IB10 under the collection config's random permutation.
2. Register the confound as a caveat beside the mirrored-axis caveat.

### G. B1 cannot ground `junction_clear`: config or scope decision

ER-2 picked `junction_clear` in a replan of BOTH B1 episodes: s42 at sim 196.5 (no plan) and s43 at sim 126.7. Both grounded with `junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m` and `junction_clear=fallback:no_candidates`, because the B1 goal-table row carries no junction fields. The universal strategy gloss offers a strategy this cell's overlay cannot ground. Options:

1. Add solved junction fields to the B1 row, if the geometry admits them.
2. Register `junction_clear` on B1 as out-of-scope, and score it as a strategy error rather than a grounding failure.
3. Leave it, and report it as an apparatus-limited replan class.

### F. Not grammar: flagged only

- B1 stage 2 chose the rank-0 2× lateral candidate 2/2 and both yields failed. That is the known Rev 20 (a) / Rev 22 defect, so v2 B1 outcomes will be dominated by the Rev 22 exclusion rule. The registered "prefer lesser excursion" tie-break revision is the lever for v2.
- The v2-tree reroute completed (n = 1) despite the latch before dispatch, from a non-demo decision context (see the episode 11 caveat).

**Bottom line.**

- A (ER-2-specific) and B are cheap, evidence-backed grammar points worth settling before the freeze. A's metrics-only option 3 avoids a re-pin.
- C and D are metric definitions and need no prompt change.
- E and G are configuration decisions.
- Every choice is the owner's.

---

## Artifacts and Verification

Bundles live in the main checkout, which is gitignored: `data/logs/vm_runs/verbatim_pilot/`. They contain:

- 11 run directories;
- `_vm_driver/` (overlays generator, `vp_run.sh`, `vp_chain.sh`, `vp_rebuild.sh`, `rr_launch_vp.sh`, `rr_watch.py`, the preflights, manifests and chain logs);
- `overlays/`;
- `_analysis/` (`plan_table.py`, `chi_margin.py`, `summarize.py`, per-run JSON, scorer outputs, `summary.json`).

A secret scan of the bundle (API-key patterns) was clean.

Suite (docs-only change): 63 failed / 5117 passed / 153 skipped / 3 errors at `a8fc1bc`, and the same after this commit. The counts are identical, and the diff touches no code or tests.
