# Thesis Evidence Register

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: one register of the best evidence per scenario family, grouped by robot count, with grades, caveats, sources and cross-document conflicts; the IB10 live experiment recorded as in progress.
- Rev 2 (2026-11-14): IB10 live experiment final row filled with the 2026-11-13 results.
- Rev 3 (2026-11-14): IB10 safety smoke and grounder-default arm row added (2026-11-14 run); the "no-VLM ablation not run" wording in the 2026-11-13 final row and in Gaps marked superseded.

---

## Scope

- **Purpose.** One place for the thesis author to find the best existing
  evidence for each scenario family, what kind of evidence it is, and where it
  is written down. This register summarises; the cited documents are the
  record. Quote numbers from the cited line, not from this page.
- **Built from** the repo's own reports and notes:
  - `docs/reports/` in this worktree (`R/` below) and in the main checkout
    `vgu-vlm-swarm/docs/reports/` (`RM/`, for files that exist only there);
  - `docs/implementation_notes.md` (`IN`);
  - the three 2026-11-13 reports;
  - the 12 November hardware README
    (`/Users/tuanhdangdinh/Downloads/verified_scenarios_12-11-2026/README.md`,
    `HW`, md5 26718adbffa7a3135ebd509630afc3c2; outside the repo).
- **Short names.**
  - `ON` = `R/2026-09-25-overnight-findings.md`.
  - `VP` = `R/2026-10-06-verbatim-pilot.md`.
  - `L2` = `R/2026-10-06-layer2off-pilot.md`.
  - `T1` = `R/2026-10-21-s1b-confirmatory-tranche1.md`.
- **Evidence kinds.**
  - **live**: closed loop in Isaac Sim with a real model;
  - **mock**: closed loop with a scripted or echo backend;
  - **decision-only**: offline or bench, nothing executed;
  - **hardware**: physical robots.
- **Grades** are as the source states them: confirmatory, pilot, probe, smoke
  or exploratory. A row with no stated grade is marked "none stated".

---

## Two Robots

| Family | Best evidence | n | Model | Headline (source wording) | Grade | Caveats | Source |
|---|---|---|---|---|---|---|---|
| head_on_deadlock (symmetric) | live | 1 per model | gpt-4o (E0), ER-2 (G0) | one `yield`, COMPLETED, 2/2 arrivals | none stated | n = 1 per model; a single-robot stall can fire the gate | `ON` 138-150, 774 |
| head_on, asymmetric `_bshort` (prereg head-on scene) | live | gpt-4o N 6 + J 3; ER-2 K 6; plus VP 5 | gpt-4o, ER-2 | "Outcome 6/6 position-verified" (gpt-4o); "15/15 position-verified episodes across both models". VP: 4 resolved, 1 intermittent | pilot | The yield parks the pair at 0.23-0.28 m. Resolution depends on M3's `swap` gate re-grounding an infeasible yielder (5/6 gpt-4o). Presentation-order prior | `ON` 2161-2197, 2510-2530; `VP` 98-102 |
| blocked_path (T3a) | live, decision-level probes | 1 per model per cell | ER-2, gpt-4o | ER-2 "answered anomaly/reroute/object: a full hit"; gpt-4o detected the blocker in 2 of 38 analyses | probe | The transient obstacle clears on despawn even with no command | `IN` 3730-3771; `R/2026-10-08-v3-step0-rebaseline.md` 22 |
| obstacle_in_candidate (T3b) | live, decision-level | 2 kept trials | gpt-4o, ER-2 | both avoided the occupied candidate; the D2 yield "FAILED on the 242.8 s wall bound" | probe | The registered 15-trial collection was not found | `IN` 3774-3781 |
| dynamic_anomaly_v2 (T3c) | live mechanical smoke + mock | 1 live, 3 mock | ER-2 (every call HTTP 429) | 2/2 arrivals, min pair 0.70 m, but "M2's answer on the anomaly scene was never observed" | smoke | Resolution follows the obstacle's removal, not a decision | `ON` 2800-2818 |
| normal_flow (T0) | live | 1 run, 28 scenes | ER-2 | "False-positive tally: ER-2 0/28 distinct scenes"; zero dispatches | verification | Only 5 moving-phase scenes | `ON` 2697-2717 |
| priority | mock only | 2 | scripted | "2/2 arrivals with zero contacts", loaded robot first | smoke | No live model episode. `priority_override` grounds as an aliased yield | `R/2026-10-03-loop-family-and-visual-pass.md` 247-251 (quote at 250); `RM/2026-10-07-forcing-audit.md` 48 |

---

## Three Robots

| Family | Best evidence | n | Model | Headline | Grade | Caveats | Source |
|---|---|---|---|---|---|---|---|
| bottleneck_merge (B1) | live | 2 | ER-2 | s42 and s43 both "clogged (0/3)" | pilot | **No resolved B1 episode anywhere**; the oracle mock also failed (0/3); yields FAILED after about 250 s | `VP` 103-104; `IN` 267, 394, 3326 |
| t2b_flow_ordering | mock, forced order | 6 runs | none (mock) | all three arrive; oracle order 319.1 / 311.1 s vs alternative 514.3 / 524.6 s, margin 0.6485 (lower bound) | smoke | No live model episode | `IN` 3663-3704 |

---

## Four Robots

| Family | Best evidence | n | Model | Headline | Grade | Caveats | Source |
|---|---|---|---|---|---|---|---|
| intersection_bottleneck (IB10) | (a) live; (b) mock, remedy + race fix | (a) VP: 2 ER-2 + 1 gpt-4o, and 1 ER-2 demo; (b) closure 5 runs | ER-2, gpt-4o; mock | (a) ER-2 s42 and s43 "resolved (4/4), rank (1, 4, 4)"; gpt-4o "clogged (0/4)", never chose `junction_clear` (0/13). (b) race fix "Yes, on 5 / 5 runs"; remedy "Yes, 5 / 5", 4/4 arrivals, no contact | (a) pilot; (b) mock | Every live ER-2 resolve was M3-repaired (2 and 4 edits) or `m3_default`. The remedy-off baseline contacted in 4/4. `id_asc` order confounds the axis question | `VP` 20-33, 105-107; `IN` 712; `R/2026-10-08-ib10-closure.md` 15-21; `R/2026-10-08-ib10-remedy-validation.md` 15-20 |
| IB10 live resolution experiment (2026-11-13) | live, interim (superseded by the final row below) | **1 counted episode of 10** (Arm A E01 a2); E01 a1 excluded | ER-2 | a2: resolved, 4/4 arrivals, rank (1, 4, 4), time to full resolution 116.5 s from onset, GT min pair 0.3109 m, 0 floor stops, one `junction_clear` dispatch, provenance `repaired` | exploratory (registered) | a1 excluded as `harness_fail:condition`, attributed by the operator to a kit condition-gate bug (not re-verified here). Its frozen outcome was also resolved, 116.9 s, `m3_default`. n = 1; Arm B not yet run | `vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/summary/` (`summary.json` md5 14444c0e3b39b4a7640dff223a16ca2e, `episodes.jsonl` md5 4ebacd3e9d6a490af248c9b428989a5d); registration `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` on `feat/ib10-live-resolution` 50704c2 |
| IB10 live experiment, final (2026-11-13) | live, runtime `68e67b5`; Arm A Layer 2 on vs Arm B Layer 2 off | 5 + 5 counted (plus 1 excluded Arm A attempt) | ER-2 | Arm A resolved 4/5 (112.9, 115.5, 116.5, 116.6 s from onset; e09 censored), 16/20 arrivals; Arm B 0/5, 0/20 arrivals, robots frozen from jam formation to the 300 s horizon. 0 floor stops and 0 GT contacts in both arms; lowest GT pair A 0.2633 m (e09), B 0.2856 m. Attribution: 4 `repaired`, 1 `m3_default`, 0 `vlm_verbatim` | exploratory pilot, n=5/arm, simulation | Supports "the VLM + grounding pipeline clears the jam that Layer 1 alone never clears", not "the VLM's plan clears it"; the no-VLM (M3 default only) ablation was not run [superseded by the 2026-11-14 row below: a grounder-default arm was run on 2026-11-14, in a separate run with the key on, not pooled with this one]. One scene, near-deterministic: Arm B is five repeats of one state, Arm A about three trajectories, so not independent samples and no p-value. Arm B is a deterministic latch baseline. e09 failed after a degenerate 2-robot `junction_clear`; its closest approach was inside a still-exempt pair (exemption caveat open, fix branch `fix/safety-exemption-scope` not used). Excluded a1 (`harness_fail:condition`, kit gate bug) also resolved on `m3_default` | `docs/reports/2026-11-13-ib10-live-resolution-results.md` on branch `feat/ib10-live-resolution` (not on this branch); evidence `vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/` (gitignored; archive md5 `4d0b2c547bb3daa2d46136d4d5e9cc54`) |
| IB10 safety smoke and grounder-default arm (2026-11-14) | live + scripted mock, runtime `68e67b5` plus 3 safety-fix files, `scoped_clearing_exemption` on, 0.20 m floor armed; Arm A live ER-2 vs Arm C grounder default only (scripted mock `none` then `junction_clear` all four robots then `none`, M3 default plan, no VLM call) | A 5 (smoke + 4); C 4 valid of 5 slots (e02 `invalid_jam`, excluded from the denominator and reported) | ER-2 (A); none (C) | Arm A resolved 5/5 (114.3 to 116.9 s from onset), 20/20 arrivals; Arm C resolved 4/4 valid (115.5 to 118.6 s), 16/16 arrivals. 0 floor stops, 0 GT contacts, lowest GT pair A 0.3008 m, C 0.2965 m. Attribution A: 4 `repaired`, 1 `m3_default`; C: `m3_default` by construction. Spend A $0.056, C $0 | exploratory pilot, n=5 vs 4 valid, simulation | **Narrowed claim:** a Layer 2 trigger plus M3's default `junction_clear` plan clears this jam; the VLM's contribution in this scene is limited to selecting the strategy and robot set, which Arm C was given. It does not show the VLM is needed, nor that it is useless (Arm C cannot re-plan; 2026-11-13 e09 shows an off-pattern VLM choice that failed). Not independent samples (one scene, no pose jitter, about four near-repeat trajectories): no p-value, no interval. The exemption-scope fix was active but never fired (all key-on counters 0): not a live validation. Arm C dispatches about 3.4 s later (scripted `none`); times not strictly comparable. e02 was a Nav2 `map_server` start-up fault (never activated, no costmap map); the scorer still prints it "counted", `GATE OK` does not detect it, and it was not re-run. `SMOKE_ACCEPTED` was written under the owner's conditional instruction, not by the owner. Never pooled with prereg-v3 or with the 2026-11-13 arms | `docs/reports/2026-11-14-ib10-safety-default-arm-results.md` on branch `feat/ib10-safety-default-arm` (commit `93fab84`; not on this branch); evidence `vgu-vlm-swarm-v7d/data/logs/vm_runs/ib10_safety/` (gitignored; archive `ib10_safety_archive_20261114.tar.gz`, md5 `9cc5c5da3476924d110d4e0f3e0d640d`) |
| convoy_counterflow (B3) + `_slip` | mock (scripted oracle order) | demo 1 + harvest 2; L2-off 1 | scripted mock | Layer-2 off "`clogged`, 0/4" vs reference "`resolved`, 4/4" (harvest 4/4 ×2). "Scripted oracle decision only; no live B3 episode exists." `_slip`: GT scorer on a real log only | pilot (L2-off) / smoke | No model evidence | `L2` 153, 160 |
| s6_dual_conflict | live pilot + 1 mock | 1 live, 1 mock | ER-2 | both jams formed "in 2 of 2 runs". The live decision named only pair B; both-pairs check FAIL | "PILOT / demo episode", excluded from every confirmatory count | Execution unscored by design | `R/2026-10-08-s6-first-light.md` 17-25 |

---

## Five Robots: mapd_5_s1b

| Item | Best evidence | n | Model | Headline | Grade | Caveats | Source |
|---|---|---|---|---|---|---|---|
| prereg-v3 tranche 1 (E27-E31) | live, Arm A vs Arm B (Layer 2 off) | 5 seed pairs, 10 episodes | ER-2 | "0/10 complete"; tasks Arm A 16/125, Arm B 12/125; throughput delta +0.032 [−0.008, +0.080]; delay lower bound −31.5 s [−71.6, −0.6]; contact gate PASS 10/10 (GT min 0.225-0.424 m) | **report as a PILOT** (owner decision 2026-11-13: tranche 2 will not be run; the source labels it confirmatory) | Pilot seeds reused (T1 line 195). No directional claim registered (T1 371-373). Dispatch column corrected (Conflicts, item 1) | `T1` 220-231, 292-304, 358-373 |
| S1b pilots E6-E26 | live | 21 episodes | ER-2 | first-conflict yield 6/21 (CI 0.113-0.522) vs MC 15/21; admitted/dispatched 14/20 pooled; 0 alternations | pilot | Mixed runtimes across batches | `R/2026-10-17-escort-filter-minibatch.md` 189, 300, 305 |
| v4 Stage 1 live shadow | live (shadow: decision-only, nothing dispatched) | 7 episodes, 50 analyses | ER-2 | 50/50 shadow blocks valid; 12 multi-group; joint flags 0/12; live: 14 dispatched, 33 withheld, 3 no decision | exploratory | Section 2 branch not settled; never dispatched | `R/2026-11-13-v4-stage1-shadow-results.md` (Summary, Exit criteria) |
| Grounding bottleneck (12 episodes) | decision-only re-grounding of live records | 78 analyses | ER-2 | 47 withheld, 26 dispatched (13 with motion), 5 no decision; 27/47 are the `junction_clear` static gate; parity 78/78 | exploratory | Nothing simulated forward | `R/2026-11-13-s1b-grounding-bottleneck.md` |
| v4 offline bench | decision-only, text-only (grey image) | 187 items (137 positive) from 31 live episodes | ER-2, Sonnet 5.5 | recorded ER-2 M3 feasibility "0.496 (68/137)"; per-cluster coverage R7a ER-2 0.832, R7b Sonnet 0.934 vs default first option 0.949; strict feasibility 168/168 and 181/181 | exploratory v4 | The models "match, and do not beat" the default-ordered first option (Rev 3). Text-only. Joint feasibility not executed | `R/2026-10-22-v4-bench-baseline.md` 89, 152; `R/2026-10-23-v4-replay-er2.md` 143-155; `R/2026-10-24-v4-gf-cluster-candidates.md`; `R/2026-11-12-v4-per-cluster-choice.md` 448-463 |
| S1a anchor | mock (echo) | 3 episodes | echo mock | A1 is "the first S1 episode in which Layer 2 executed a resolving yield closed-loop in task-stream traffic"; 2/25 tasks; the other two gridlocked | none stated | Echo backend, not a model | `R/2026-10-10-s1a-anchor.md` 17-31 |

---

## Hardware (12 November 2026)

| Scenario | Robots | Decision | Command outcome | Source |
|---|---|---|---|---|
| A: two simultaneous head-on pairs | 4 | deadlock, `reverse` | 4/4 completed | `HW` 22-62, 205 |
| C: triangular | 3 | deadlock, `reverse` | 3/3 completed | `HW` 63-101, 206 |
| D: central four | 4 | crowding, `reverse` | 4/4 completed | `HW` 102-146, 207 |
| E: compact dual lane | 4 | deadlock, `reverse` | 3 completed, robot 3 failed | `HW` 147-189, 208 |

- **Setup.** Physical TurtleBot3s, an overhead RealSense, ArUco, Zenoh,
  `dry_run=False`, safety monitor on (`HW` 18).
- **Model.** `gemini-3.1-flash-lite` (`HW` 18). Confirmed in artifact
  `8c9b01cd…1bc8`, `diagnostics.backend_id`.
- **Robots had no goals.** The README never mentions goals. In the checked
  artifact, the robot state carries only `robot_id, x, y, theta,
  linear_velocity, status, stamp`, and the prompt has no "goal". So
  "completed" means the reverse command finished. It does not mean a conflict
  was resolved toward task progress.
- **Exclusions.** Two parse failures (`HW` 192-195). Earlier
  `priority_override` and `reroute` attempts are not counted (`HW` 197).
- **n = 1 per scenario.** The code lineage is not in this repo. Grade: the
  README's own "Full end-to-end success" / "Partial execution success".

---

## Executed Evidence by Strategy

| Strategy | Live executed evidence of resolving a multi-robot conflict | Source |
|---|---|---|
| yield | Yes. 2-robot head-on (gpt-4o 6/6, ER-2 K batch). 5-robot S1b productive yields (T1 E28 `3c234140`, E31 `60afd0c1`; Stage 1 9/9 yields `completed`). Not in B1 (yields FAILED) | `ON` 2172-2181, 2519; `T1` 386; bottleneck report, Outcomes |
| reverse | Only inside IB10 `junction_clear` phases. Alone it "cannot resolve a two-robot head-on" in Isaac. Hardware reverses completed, but without goals. S1b live: 2 of 4 reverses `failed` | `R/2026-09-18-head-on-family-validity.md` 994, 1135; `VP` 105-106; bottleneck report |
| junction_clear | Yes, IB10 only (ER-2 4/4 ×2 plus demo; the 2026-11-13 live experiment, Arm A 4/5). Every case repaired or `m3_default`. It never grounds on S1b (static gate, 0/3430 poses) | `VP` 26, 105-106; `IN` 712; bottleneck report |
| reroute | Single robot only ("ER-2 reroute s42 … resolved (1/1)") | `VP` 108 |
| priority_override | **None.** It degrades to a wait or is aliased to a yield | `IN` 3771; `RM/2026-10-07-forcing-audit.md` 48 |
| convoy | **None live.** Scripted mock only | `L2` 153, 160 |
| temporary_wait | No resolving evidence | `VP` B1 rows; `IN` 3771 |

---

## Claims the Evidence Supports / Does Not Support

**Supports:**

- Executed, closed-loop evidence exists for `yield` (2-robot head-on, some
  5-robot S1b first conflicts), for `reverse` as a phase of `junction_clear`,
  and for `junction_clear` on the 4-robot IB10.
- Where the system resolved a multi-robot conflict, M3 supplied or repaired
  the plan:
  - the swap gate re-grounded an infeasible yielder (`ON` 1055-1060,
    1138-1145, 2185-2186, 2527-2530);
  - IB10 plans needed `substitute` or `reorder` edits, or `m3_default`
    (`VP` 20-26);
  - tranche-1 provenance was mostly `repaired` / `m3_default` (`T1` 390).
- In three cells, with the 0.20 m floor armed, no GT pair came below 0.18 m
  and no floor stop fired: tranche 1 (10 episodes), Stage 1 (7) and IB10 live
  (11 attempts, both arms; lowest GT pair 0.2633 m). This is not a general safety claim. Earlier cells recorded
  GT contacts: the head-on K1 driven nose-to-nose contact (`ON` 17), and IB10
  with the remedy off (contacts in 4/4 baseline runs,
  `R/2026-10-08-ib10-remedy-validation.md` 15-20). The exemption-scope
  findings are open (`R/2026-11-13-safety-exemption-trace.md`).
- On S1b the bottleneck is M3 grounding, not detection. Detection recall was
  0.818 in tranche 1 (`T1` 231). 47/78 analyses were withheld by
  deterministic M3 refusals.

**Does not support:**

- `reroute` or `priority_override` resolving a multi-robot conflict (no
  live evidence).
- A model resolving `convoy_counterflow` (scripted mock only) or
  `bottleneck_merge` (0 resolved).
- A directional Layer-2 benefit on S1b. The tranche-1 throughput CI includes
  0, it is now a pilot, and tranche 2 will not run.
- The models choosing better than M3's default-ordered first option on the
  bench (they match it).
- Per-group dispatch improving S1b (Stage 1 is shadow only).
- Hardware conflict resolution toward goals (the robots had no goals).

---

## Conflicts Between Documents

1. **Tranche-1 "dispatched" column.** `T1` 292-304 gives 9/4/5/5/3
   dispatched and says a refused yield "is still dispatched". The real
   dispatches that reached M4 were 5/2/2/1/2, with 4/2/3/4/1 withheld.
   Verified against M4 `command received` lines
   (`R/2026-11-13-v4-stage1-shadow-results.md`, Corrections).
2. **Recorded ER-2 cluster coverage:** 0.639 (94/147)
   (`R/2026-10-22-v4-bench-baseline.md` 91) vs 0.686 (94/137)
   (`R/2026-10-23-v4-replay-er2.md` 149). Different denominators.
3. **Recorded ER-2 mean per-cluster recall:** 0.660 (baseline 92) vs 0.710
   (replay 150).
4. **Recorded ER-2 involved F1, unconditional:** 0.843 (baseline 94) vs
   0.904 (replay 152).
5. **Tranche-1 cost:** $0.2127 (cost logs) vs $0.2128 (`aggregate_b6`),
   acknowledged as rounding (`T1` 314, 391).
6. **ER-2 E1-E6 head-on:** 3/6 by log vs 2/6 position-verified (`ON` 1461,
   1490, 1618). The document reconciles them itself; cite the
   position-verified 2/6.
7. **ER-2 opening reverse:** 3/3 (`ON` 823) vs 5/6 live (`ON` 991).
8. **IB10 scripted composite:** 4/4 on the fix branch vs 1/4 on the merged
   tree (`R/2026-10-08-v3-step0-rebaseline.md` 23).
9. **Run labels G1-G3 are reused** for different runs in `ON` (775-777 vs
   1802-1807). Cite by stamp, not label.
10. **Scorer validity.** `RM/2026-10-07-forcing-audit.md` 13, 165-166 says
    `classify_outcome` can award `resolved` with zero dispatches. Whether
    that was fixed was not checked for this register.
11. **Stale line references.** The per-cluster design note cites
    `orchestrator_node.py:1648-1665` for the plan-continue partners. At
    fdf333d the function is at 1909-1980.

Items 2-10 were collected by reading the cited lines. They were not
re-derived from raw data. `IN` line numbers refer to
`docs/implementation_notes.md` as of this register's commit; later entries
shift them, so cite notes entries by date and title.

---

## Gaps

- No live evidence for 3-robot families resolving, for `reroute` or
  `priority_override` in multi-robot scenes, or for model-chosen convoy.
- No hardware run with goals.
- No confirmatory-grade evidence remains: tranche 1 is reported as a pilot.
- The IB10 live experiment is complete (n=5 per arm, exploratory); there is
  still no M3-default-only (no-VLM) arm to separate the model's contribution. [superseded by Rev 3: the 2026-11-14 run added a grounder-default-only arm (Arm C, n=4 valid, exploratory). It was handed the strategy and robot set, so it does not separate strategy and robot-set selection from the plan content, and it cannot re-plan.]
