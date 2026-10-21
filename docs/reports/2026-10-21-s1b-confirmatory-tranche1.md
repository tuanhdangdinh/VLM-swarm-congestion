# S1b Confirmatory Tranche 1: E27-E31

**Prepared:** 2026-10-21

**Revision history:**

- Initial draft: §1 pre-registration of the first confirmatory S1b tranche under prereg-v3 A32 (cell, arm, seeds, configs and md5s, the registered outcome measures quoted with line cites, safety gates, budget, abort rules) and the open items in §1.8 that the owner must rule before any live call. The VM kit is `data/logs/vm_runs/batch6/p10/` (gitignored), built offline. No VM was started. Results follow in later sections.

---

CONFIRMATORY, RECORD = 1.

---

## 1. Pre-registration (written and committed before any live call)

CONFIRMATORY, RECORD = 1. This block is frozen at commit time, subject only to the owner rulings in §1.8, which are recorded as a new revision entry BEFORE the first live call. After the first live call, later sections may only add to this block, never edit it. Values marked "to be filled at deploy" are measurements of the VM, not choices. They go in §3 and do not edit this block.

All design citations are to `feat/v3-design` @ `24fa2bc`:

- **design doc** = `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`;
- **scene doc** = `docs/superpowers/specs/2026-10-06-v3-scene-design.md`.

### 1.1 What A32 fixes, and what it leaves open

- **Fixed by A32** (design doc lines 1439-1520, owner rulings R1-R5, 2026-10-21):
  - "FIRST CONFIRMATORY CELL NEEDS: shield config = the escort overlay (md5 40968886); episode cap $0.10; bring-up per-stack timeout 180 s; RECORD=1; churn bound off; plus the standing A28(i) requirement that the 0.20 m floor swap and the pre/post arm gates run "in EVERY future S1b live cell, shield or not"" (lines 1502-1506).
  - It also requires the VM deploy of `command_grounder.py`, `models.py`, `retreat_stage2.py` (rebuild, then md5 source against install) and `scripts/vm/fc_launch.sh` (lines 1506-1511).
- **Left open by A32:** "This addendum does not set N or name cells" (lines 1511-1512).
- **The registered figures A32 points to:**
  - "S1's own budget (R=20/arm ≈ 40–48 h)" (R3.7, line 506);
  - "Confirmatory n is **R = 20 per arm, registered**, from the first 20 seeds; seeds 21–100 are an extension only" (scene doc line 155);
  - "any departure from R = 20 per arm needs its own ruling" (design doc lines 1519-1520).
- **Pilots excluded:** "Episodes E6-E26 were pilots, run before this freeze, and stay excluded from every confirmatory count" (lines 1496-1500, citing Discipline item 2, lines 75-76).

### 1.2 Cell and arm (kit default; owner confirms in §1.8 (a))

- **Cell:** the S1b shield cell that A30 and A31 ran, made confirmatory with the A32 configuration.
  - Floor `mapd_5_s1b` (VM yaml 728e58df), N = 5, Δ 2.5, H = 600 sim-s.
  - Overlay grounding file `config/grounding/s1b_dynamic_shield_escort.yaml`, md5 **409688866d25289309e081dcb9433037**. A32 R1: it is "PROMOTED to the registered shield config for confirmatory S1b cells, unedited" (lines 1449-1452).
- **Arm:** Layer 2 ON, live `gemini-robotics-er-2-preview` (ER-2). This is the arm "Layer 2 on" of the registered pair "**Arms:** Layer 2 on, against Layer-2-off" (scene doc lines 370-371).
  - The in-episode classical shadow (`shadow_classical`) is recorded in every artifact, as in every pilot. It is not a separately run arm.
  - **Layer-2-off is not in this tranche.**
- **Why this cell:** A32 names no cells. This is the only S1b cell with a frozen configuration, the one A32 R1 configures, and the one A30/A31 ran. Non-shield S1b cells would keep `s1b_dynamic.yaml` (535f5281; A32 R1, "Every other cell keeps its current grounding file"), but no such cell has been run or kitted.
- **Condition:** rule 16 + A32. That is:
  - backend: ER-2, plan channel on;
  - suppression + `refusal_no_action` + `backend_failed` arming;
  - churn bound OFF (A32 R4);
  - REC_SEC 4800, NAV2_ACTIVE_TIMEOUT_SEC 360, `NAV2_BRINGUP_MODE=sequential` with `NAV2_STACK_ACTIVE_TIMEOUT_SEC` unset, so the A32 R3 default of 180 s applies (the chain unsets it explicitly);
  - MAX_ANALYSES 40;
  - the 0.20 m floor installed (A28(i));
  - RECORD=1 (§1.8 (c));
  - tag `confirmatory_t1` in every bundle's `CONDITION.txt`.

### 1.3 Seeds and labels (kit default; owner confirms in §1.8 (b))

The tranche is the first 5 of the registered first-20 confirmatory seeds: `config/s1_seeds.yaml` (md5 442a5e0f, append-only, sha256-pinned by `tests/unit/test_mapd_5_scenario.py`), positions 1-5.

| Episode | Position | Seed | Scenario yaml | Header `hdr_a20_seed{k}` | USD | Overlay `s1b_shield_escort_orch_seed{k}.yaml` | Unshielded base |
|---|---|---|---|---|---|---|---|
| E27 | 1 | 978442588 | d8cb4a0f | 65a577d8 | to be filled at build | d55cf337 | 4d2e540b |
| E28 | 2 | 1181837745 | f276a023 | a8391b9a | to be filled at build | eb047a43 | 2e248844 |
| E29 | 3 | 537191633 | c204935f | a4b15d6e | to be filled at build | 9565b6fe | ed573422 |
| E30 | 4 | 90907664 | 3b327906 | 2abcaeaa | to be filled at build | e0ec8543 | 6c459720 |
| E31 | 5 | 1912308941 | 7bae1aa0 | a13ea0c4 | to be filled at build | 71c975ed | b6a755b5 |

- **Labels:** E27-E31 continue the episode numbering after the last pilot (E26). The design mandates no labelling.
  - Bundles are `s1b_E{27..31}_seed{1..5}_er2_confT1_a{attempt}`.
  - The pilots used `E{k} = seed position k`, so E27-E31 deliberately break that pattern. `_seed{k}` still carries the position.
- **Procedure (p9 verbatim):**
  - `gen_s7.py` (638524a2) on `mapd_5_s1b.yaml` 728e58df gives the scenario yamls; on `mapd_5_s1b_hdr_d7dae79.yaml` 3d2659b6 it gives the header sources.
  - `build_overlay.py` (82815cfa) on pin 1f656533 + the header gives the base overlay.
  - One `sed` of `grounding_params_path` then points it at the escort overlay.
- **Reproduction gate:** before any p10 file was written, the same procedure on the 97d68e0 worktree byte-reproduced p9's seed-24..26 scenario yamls, headers, bases and overlays (`p10/mac_gen_ov_p10.log`).
- **Verification:**
  - All 5 headers are non-comment-equal to their scenario yamls.
  - The yaml seeds equal the list.
  - Each overlay differs from its base in exactly the `grounding_params_path` line.
  - All 5 parse through `load_config` + `load_grounding_source` as: junction [NW, SW, N, S], plan / supp / rna True, churn off, shield True 0.05, fast-fail True, dyn True, escort_park True, H 600.
- **On the VM**, `gen_p10.sh` and `ov_p10.sh` must print `VM == MAC`.
- **Pilot-era files** under the names `mapd_5_s1b_seed{1..5}` are md5-logged and backed up before `build_p10.sh` overwrites them.

### 1.4 Tree, deploy and pins

- **Tree:** `feat/v3-integration` @ `97d68e0` (the merge of `feat/v3-s1b-freeze`: R5 `6abea45`, R1 pin test `b2555b9`, R3 `d975f13`). The VM carries the A28/A29 runtime `9a018ca` (A31).
- **Delta:** `git diff --name-only 9a018ca 97d68e0 -- reasoning ros2_ws scripts config isaac` gives exactly 4 files. The escort overlay rides along at pre == new.
  - `delta_p10.tar` md5 **81d8c629c222777b1232786ec3f0badf** (`git archive 97d68e0`; `p10/mac_build_delta_p10.sh`).

| File | Layer / installed path | Pre (9a018ca) | Source (97d68e0) | Installed md5 |
|---|---|---|---|---|
| `reasoning/rag/command_grounder.py` | M3, live mount `/ws/...` | a4e8b5a8 | **cfbd1fb8** | to be filled at deploy |
| `swarm_orchestrator/models.py` | M5, colcon → `site-packages/swarm_orchestrator/models.py` | a76e3c00 | **b9b4d6d9** | to be filled at deploy |
| `swarm_orchestrator/retreat_stage2.py` | M5, colcon → `site-packages/swarm_orchestrator/retreat_stage2.py` | 0bd96495 | **cf0dad3e** | to be filled at deploy |
| `scripts/vm/fc_launch.sh` | host launcher (run by `ep_run_p10.sh`) | 5a5ee4ac | **055db01e** | to be filled at deploy |
| `config/grounding/s1b_dynamic_shield_escort.yaml` | M3 config, live mount | 40968886 | 40968886 | to be filled at deploy |
| `swarm_execution` src + installed `safety.yaml` (`floor_p10.sh`) | M4 config, colcon | pristine 59839662 | **c41913f0** | to be filled at deploy |

- **Unchanged and gated before every episode:**
  - configs: `orchestrator.yaml` 1f656533 (src and installed), rag e18c723c, s1b_dynamic 535f5281, s1b_dynamic_shield ee5fe68f;
  - A30 runtime: `escort_clearance` 50766aeb, `grounding_view` e152fc74, `maneuver_geometry` 8923c35c, `retreat_candidates` 76f6b8d8, `reasoning_pipeline` 39a51bfc, `shadow_classical` 1de9588a, `orchestrator_node` f149ecff;
  - A27 files: `retreat_shield` db0b6415, `plan_metrics` 9d3c1487;
  - A27 M4 files: `safety.py` c6c9cbae, `fresh_latch` 08d996a8, `nav2_adapter` f139305c, `command_bus_node` caad9edc;
  - recorder `scripts/record_topic_video.py` 90aa8971;
  - the episode driver `ep_run_p10.sh`, by its kit md5.
- **Deploy gates** (`deploy_p10.sh`, in order): PRE-IMAGE, SOURCE, LIVE MOUNT, HOST LAUNCHER (md5 plus the `:-180` default), colcon rebuild of `swarm_orchestrator` inside `vgu_ros` after a build/install purge, INSTALLED, PACKAGE SRC==INSTALLED, ORCH PIN, and a smoke test.
  - The smoke checks R1's flags on the three grounding files.
  - It also checks the R5 field `RetreatStage2Record.dropped_candidates`, `RetreatSelection.escort_park_dropped`, and `DroppedCandidate.reason == escort_hits_park`.
- **Suite (at `97d68e0`, full testpaths, `--continue-on-collection-errors`, run 2026-10-21 for this kit):** 62 failed / 6833 passed / 153 skipped / 3 errors. That is p9's 62/6815/153/3 plus 18 passing tests from the freeze branch. The 65 failing ids are identical to the A27 reference list (`data/logs/vm_runs/a27/final_ids.txt`). Evidence: `data/logs/vm_runs/batch6/suite/`.

### 1.5 Outcome measures, exactly as registered (no new predictions)

This tranche is confirmatory. It adds NO hypothesis and NO threshold. It collects the registered S1 measures for the Layer-2-on arm on its first 5 seeds.

- **Per-run measures** (scene doc line 157, S1 Measures row): "Makespan and time-to-full-resolution; completeness via outcome classes; throughput as completed tasks / 25 over sim time; plus `delay_vs_free_flow` per segment".
  - Oracle sketch (scene doc lines 368-369): "Scoring per run: completeness (all 25 tasks done by H), makespan, throughput curve, and per-segment `delay_vs_free_flow`."
- **Per-conflict measures** (scene doc lines 366-367): "Scoring per conflict episode: detection (GT encounter → trigger latency), type label, involved-set F1, and plan-quality metrics (i-a)–(vi) as in v2."
  - Also: "**No `accepted_strategies` per episode.** Rule it explicitly at the freeze" (scene doc lines 364-365).
- **Conflict class** (design doc lines 973-975, A15(iii)): "latch-on-pass is REGISTERED as S1b's conflict class, and the S1a/S1b axis is re-registered as a RESOLVABILITY axis".
- **Comparison form** (design doc lines 480-484, R3.6a item 4): "The Arm A−Arm B comparison across regimes is registered as **CI estimation of the delta per regime**, with the Goldilocks expectation (delta maximal at intermediate difficulty) recorded as interpretation, not as a directional hypothesis."
  - A single-arm tranche cannot estimate that delta. This tranche contributes Layer-2-on runs only.
- **Registered secondary readings** carried by the pilots' tracked scorers, reported as such:
  - A21(iii)(a) churn metrics and intermittent classification, "MEASURE NOW" (design doc line 1236);
  - A27(iv) vb∧matched, "READ with shielded robots excluded (lane-scope precedent; raw count co-reported)" (lines 1809-1811);
  - A28(iii) admitted ≠ productive as a metric distinction;
  - MC is "REGISTERED as an upper bound for live yield probability" (A22, lines 1281-1283). MC is context, not a prediction.
- **Scorer coverage today** (stated, so nothing is improvised after the data):
  - **Computed by tracked code:**
    - tasks completed / 25 and the censoring point `gt_end_rel_s` (`s1b_live_batch_stats` → `s1_gridlock_stats`);
    - churn class, alternations, productive events (`s1_churn_stats`);
    - provenance and vb∧matched, raw and shield-excluded;
    - first-conflict yield;
    - cost.
  - **Kit scorers:** `batch6/score_p10.py` (per bundle) and `batch6/aggregate_b6.py` (confirmatory-only; refuses untagged bundles; never pooled with E6-E26).
  - **NOT computed by any current scorer:** makespan / time-to-full-resolution as defined for S1, the throughput curve, per-segment `delay_vs_free_flow` (needs `free_flow_v2` keyed by (scene, segment)), detection latency, type label, involved-set F1, and plan-quality metrics (i-a)-(vi) for emergent S1b conflicts.
  - These need Step-6 freeze items (free-flow table id, GT conflict detector, the `accepted_strategies` ruling) that A32 does not record as frozen. They are owed before any confirmatory S1b number is reported (§1.8 (f)).

### 1.6 Safety and validity gates (gates, not hypotheses)

- **Contact gate** (the A30 P2 form, re-used as a validity gate):
  - No robot pair, at any time, below **0.18 m** GT centre distance. This is an all-pairs scan of `gt/ground_truth.jsonl` (`a27/kit/gt_contacts.py` rule, inlined in `score_p10.py`). The GT contacts field is a stub (A14 corrigendum).
  - Zero `safety stop robot=… reason=hard_contact_floor` lines in `m4.log`.
  - A breach is reported with its pair, onset and minimum.
  - The episode is NOT dropped from the confirmatory count: it is a safety finding, scored as it ran.
- **Floor gate** (chain, after every episode): the `m4.log` startup line `hard_contact_floor_m=0.2` must appear. Otherwise the chain stops.
- **Condition gate** (`cond_p10.py`, after every episode). The chain stops on any failure. The gate requires:
  - every grounded artifact carries `escort_park_clearance`, `retreat_shield` and `retreat_fast_fail` True;
  - `CONDITION.txt` carries `tag=confirmatory_t1 record=1`.

  The same line also reports:
  - the `retreat=escort_park_filtered` tag counts;
  - the R5 `stage2.dropped_candidates` count (key absent → 0);
  - whether the recording dir is present.
- **Escort/park check** (`score_p10.py`): every dispatched yield's escort legs vs the 0.45 m park clearance (A28(ii)). A leg below 0.45 m is a SAFETY FLAG, not a test. Tags and `dropped_candidates` are compared per artifact; a mismatch is reported, never repaired.
- **Pin gate** (chain, before every episode): every md5 in §1.4. Pin watch (A22 rule 4/11) and live watch run as in p9.

### 1.7 Budget and abort rules

- **Budget** (VM-enforced, A25 reserve-one-call rule). A32 R2 sets "batch cap and the start floor are per cell and are set in the kit" (lines 1461-1465). One header block in `p10/chain_p10.sh`:
  - **CAP_EP = $0.10**;
  - **CAP_TOTAL = $0.55 HARD**, summed over this tranche's `_er2_confT1_a*` cost logs only (5 × $0.10 + $0.05 slack);
  - **MIN_REMAINING = $0.08** (start floor).
- **Episode cap** = min(CAP_EP, remaining). `cost_watch.py` (p9 verbatim) touches the Isaac stop flag once est + $0.008 reaches it.
  - est is a lower bound: a timed-out stage-2 call records no usage.
- **No top-up:** an episode that would breach the floor is not run and is reported. No episode is added after seeing data.
- **Bring-up:** up to 3 attempts per episode.
  - `ON_SEED_FAIL=stop` (default): a seed whose 3 attempts all abort stops the tranche for an owner ruling. It is never skipped or substituted. See §1.8 (e).
- **Chain stops** on any pin, floor or condition gate failure, `STOP_CHAIN`, or the budget gate.
- **VM:** started for this tranche and STOPPED after it. The kit steps are in `batch6/NOTES_vm_b6.md`: pins → gen → build → deploy (orchestrator rebuild) → floor → overlays → chain → `restore_safety_p10.sh` → close-out → stop.

### 1.8 Owner rulings needed BEFORE the first live call

The kit defaults are listed first in each item. A32 does not fix any of these.

- **(a) Cell and arm.**
  - Default: the shield cell, Layer-2-on (ER-2), as §1.2 above.
  - Open: whether the Layer-2-off arm (the registered S1 control) and any non-shield S1b cell are collected, and in what order relative to this tranche.
- **(b) Seeds.**
  - Default: positions 1-5, the plain reading of "the first 20 seeds".
  - Every position 1-20 already ran as a pilot (E1-E5 echo, E6-E20 live). The pilots stay excluded (A32), but the confirmatory seeds are not unseen.
- **(c) RECORD=1.** The harness's only RECORD switch is `fc_launch.sh`'s video recorder.
  - Every pilot ran RECORD=0, because `ep_run.sh` hard-coded it.
  - With RECORD=1 the recorder starts before Nav2 bring-up and runs on the annotated-frame topic: a harness difference from every pilot (CPU and RTF load during the 5-stack bring-up).
  - The kit sets RECORD=1 (`ep_run_p10.sh` passes it through) AND tags every bundle `confirmatory_t1`.
  - If A32's "RECORD=1" means the dataset flag only, set `RECORD=0` in the chain header; the tag stays.
  - Optional, recommended only: a $0 `BRINGUP_ONLY=1 RECORD=1` launch on seed position 1 would test the recorder plus the 5-stack sequential bring-up on this host before any confirmatory attempt is spent.
- **(d) Censoring.** At the pilots' rate (about $0.0078 per analysis; A31: 6 analyses at 133-174 sim-s under $0.05), $0.10 buys about 12 analyses, roughly 270-350 sim-s of H = 600.
  - Completeness and makespan stay censored. Each run's censoring point (`gt_end_rel_s`) is reported.
- **(e) Seed-fail rule.**
  - Default: stop.
  - The alternative (p9's "skip; two consecutive → stop") makes the confirmatory set depend on bring-up luck.
- **(f) Missing scorers** (§1.5): S1 makespan, throughput curve, `delay_vs_free_flow` (`free_flow_v2`), and the per-conflict detection, type and involved-F1 scoring for emergent conflicts must be built and frozen before any confirmatory number is reported.
  - The tracked-scorer measures listed under "Computed by tracked code" in §1.5 are FROZEN by this block, at the scorer code of `97d68e0` plus `batch6/score_p10.py` and `batch6/aggregate_b6.py` as kitted (md5 in `batch6/NOTES_vm_b6.md`). They may be computed after the pull (runbook step 13).
  - The unbuilt measures (S1 makespan / time-to-full-resolution, throughput curve, `delay_vs_free_flow`, and per-conflict detection, type, involved-F1 and plan quality) must have their definitions and scorers frozen BEFORE they are computed on E27-E31. They are never derived from these episodes' data.

### 1.9 MC context (echo, upper bound; `batch6/mc_seeds_p10.{py,jsonl}`; not predictions)

`batch5/mc_seeds_24_26.py` with the seeds changed, on 97d68e0. The first conflict was grounded three ways: pinned, nofilter, and escort (the deployed file with goal references).

| Seed | First conflict | Echo pair | pinned | escort (leg clearance; filter tag) |
|---|---|---|---|---|
| 1 | r3+r4 at 15.2 s | [r3, r4] | REFUSED (no shared lane) | REFUSED (no shared lane) |
| 2 | r1+r5 at 13.2 s | [r1, r5] | EXECUTABLE yield r1, 0.849 m | EXECUTABLE yield r1, 0.849 m; `A:robot_5:0.231` |
| 3 | r1+r4 at 14.5 s | [r1, r4] | EXECUTABLE yield r1, **0.200 m** | EMPTY_REROUTE (`escort_hits_park:robot_4:0.200`; the filter drops the only candidate) |
| 4 | r3+r4 at 14.4 s | [r3, r4] | EXECUTABLE yield r4, 0.679 m | EXECUTABLE yield r4, 0.679 m; `A:robot_3:0.357` |
| 5 | r1+r5 at 10.5 s; echo names r3+r4 | [r3, r4] | EXECUTABLE yield r3, 0.447 m | EXECUTABLE yield r3, 0.767 m; `A:robot_4:0.447` (the default pick dropped) |

- **MC upper bound on first-conflict executable yields (escort):** 3/5.
- The MC caveat of the A30 report §1.6 applies unchanged: no task intents, so the shield is inert in MC, and live stage 2 and the grounding view can change the pick.

---

## References

- **Rulings:** prereg-v3 A32 (R1-R5), A31, A30, A28(i), A27(iv), A25, A22, A21(iii), A15(iii), R3.6a, R3.7 (`feat/v3-design` @ `24fa2bc`); scene doc S1 table and oracle sketch.
- **Previous batch:** `docs/reports/2026-10-17-escort-filter-minibatch.md` (§1 is the template; §9 "Kit changes for the next kit").
- **Code:** `reasoning/rag/command_grounder.py` (`DroppedCandidate`, `filter_escort_park_candidates`), `swarm_orchestrator/models.py` (`RetreatStage2Record.dropped_candidates`), `scripts/vm/fc_launch.sh` (`NAV2_STACK_ACTIVE_TIMEOUT_SEC`), `config/grounding/s1b_dynamic_shield_escort.yaml`, `config/s1_seeds.yaml`.
- **Kit** (gitignored, `data/logs/vm_runs/batch6/`): `NOTES_vm_b6.md`; `p10/` (`pins_pre_p10.sh`, `gen_p10.sh`, `build_p10.sh`, `deploy_p10.sh`, `floor_p10.sh`, `ov_p10.sh`, `chain_p10.sh`, `ep_run_p10.sh`, `cond_p10.py`, `cost_watch.py`, `pin_watch.py`, `restore_safety_p10.sh`, `parse_ov_p10.py`, `manifest_p10.txt`, `delta_p10.tar`, `kit_md5.txt`, `scen/`, `ovsrc/`, `overlays/`, `src/`, Mac generators and logs); `mc_seeds_p10.{py,jsonl}`; `score_p10.py`; `aggregate_b6.py`.
