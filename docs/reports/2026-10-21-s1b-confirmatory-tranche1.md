# S1b Confirmatory Tranche 1: E27-E31, Two Arms

**Prepared:** 2026-10-21

**Revision history:**

- Rev 5 (2026-11-15): added the erratum "2026-11-15 Erratum — Contact Wording"; the contact gate's wording scoped to robot-robot pair distance; §1 annotated, not reworded; no number or verdict changed.
- Rev 4 (2026-10-22, after the tranche): results added in §2-§9 (10 episodes run to the 600 sim-s horizon on 2026-10-21, all gates passed, est. $0.2127). §1 is unchanged.
- Rev 3 (2026-10-21, before any live call): Arm B's launch mode exists and is registered as prereg-v3 A35 (`feat/v3-design` `9a5eb8f`). M5 `reasoning_enabled: false` is delivered by the overlays `s1b_l2off_orch_seed{k}.yaml`, and the tranche is RUNNABLE. The new runtime commit is `feat/v3-arm-b-mode` `1624db1`, which is `3efcd78` plus `models.py` and `orchestrator_node.py`. The deploy delta is rebuilt (`delta_p10.tar` 6e8b40fab5ab68aebe4b3e4f827b7536, 6 files; `manifest_p10.txt` 50376db3b76b99a14f71942d175768f8). The Arm B gates are tightened (§1.2, §1.6). Nothing else changes, and nothing exploratory is added.
- Rev 2 (2026-10-21, before any live call): §1 updated for the owner rulings R6-R11 recorded in prereg-v3 A34 (`feat/v3-design` `0891cd8`), which close §1.8. The tranche is now 10 episodes (5 seeds × Arm A / Arm B, interleaved). RECORD is a dataset tag only (RECORD=0 to fc_launch). Episodes are capped by sim-s, with dollars as a guard. Every registered S1 measure is scored by `benchmarks/s1_scoring` at `feat/v3-freeflow-freeze` `3c71503`, with the frozen S1b free-flow table (md5 b4002d7697f4d8f27c31792a9b269162). Arm B (Layer-2-off classical) is ruled but has no launch mode, so the tranche is NOT RUNNABLE until it exists. Runtime commit `3efcd78`. Nothing exploratory is added.
- Initial draft: §1 pre-registration of the first confirmatory S1b tranche under prereg-v3 A32 (cell, arm, seeds, configs and md5s, the registered outcome measures quoted with line cites, safety gates, budget, abort rules) and the open items in §1.8 that the owner must rule before any live call. The VM kit is `data/logs/vm_runs/batch6/p10/` (gitignored), built offline. No VM was started. Results follow in later sections.

---

CONFIRMATORY (`confirmatory=1`), RECORD = 0 (A34 R6). RUNNABLE: A34 R9's Arm B launch mode exists (A35, Rev 3).

---

## 2026-11-15 Erratum — Contact Wording

Ground truth's two contact lists, `robot_static_contacts` and `robot_robot_contacts`, are hard-coded to `[]` in `isaac/vgu_sim/acceptance_logging.py:99-100`. No contact detector exists, so an empty list shows nothing. The sound channel is the logged minimum pairwise distance (`min_pairwise_distance_m` and the GT positions), a centre-to-centre robot-robot distance. Nothing in GT logs contact with static obstacles. Same caveat: `docs/reports/2026-09-25-overnight-findings.md` (Metric correction 2 and its Rev 11 note) and `docs/reports/2026-10-08-s1-pilot.md` (GT `robot_static_contacts`); full account in section 8.7 of `docs/reports/2026-11-15-demo-campaign-results.md`.

- **What the statements rested on.** The contact gate (§1.6) is an all-pairs scan of GT robot positions for a centre distance < 0.18 m plus `hard_contact_floor` stops; the GT contact field is not used. Its PASS is a robot-robot statement and holds as such.
- **Affected statements.** §1.6 "Contact gate"; the status line ("Every pin, floor, condition, contact and escort gate passed"); the gate table row "Contact gate | PASS 10/10". Each is scoped in place and marked (corrected 2026-11-15, see erratum); §1 is annotated with a bracket, its text unchanged. The §-results row "Contact (all pairs, GT, < 0.18 m)" already names its scope and is unchanged.
- **What remains supported.** Robot-robot only: PASS 10/10, all-pairs GT minima A 0.424 / 0.333 / 0.261 / 0.349 / 0.341 m, B 0.395 / 0.225 / 0.301 / 0.297 / 0.388 m, 0 floor stops.
- **Static obstacles.** S1b has rack islands (`mapd_5_s1b`: `obstacle_1`, `obstacle_2`, `obstacle_3`), so the robot-static gap is material here: nothing in this report measures robot-to-island contact. A later offline recompute outside this report (demo-campaign report 8.7.4, URDF chassis box against the declared boxes, about 5 mm sampling) found every robot-to-box gap at least 7 mm, except E30 Arm A robot_2, 1.2 mm from `obstacle_1` at sim 48.6-49.2 s under Nav2: a possible graze, not established. The gate does not cover it.

---

## 1. Pre-registration (written and committed before any live call)

CONFIRMATORY, RECORD = 0 (a dataset tag only, A34 R6). This block is frozen at commit time, subject only to the owner rulings in §1.8, which are recorded as a new revision entry BEFORE the first live call (Rev 2 records R6-R11). After the first live call, later sections may only add to this block, never edit it. Values marked "to be filled at deploy" are measurements of the VM, not choices. They go in §3 and do not edit this block.

All design citations are to `feat/v3-design` @ `24fa2bc`, except A33 and A34, which are cited at `0891cd8`, and A35, cited at `9a5eb8f`:

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
- **Fixed by A33 and A34** (owner, 2026-10-21): A33 defines every registered S1 measure operationally, and A34 R11 rules all of its PROPOSAL parameters at their defaults. A34 R6-R10 set RECORD (dataset tag only), the sim-s cap with a dollar guard, the frozen S1b free-flow table, Arm B's identity (Layer-2-off classical) and the accepted types. A34 also sets the run spec: 5 seeds × 2 arms, interleaved.
- **Pilots excluded:** "Episodes E6-E26 were pilots, run before this freeze, and stay excluded from every confirmatory count" (lines 1496-1500, citing Discipline item 2, lines 75-76).

### 1.2 Cell and arms (A34 run spec)

- **Cell:** the S1b shield cell that A30 and A31 ran, made confirmatory with the A32 configuration.
  - Floor `mapd_5_s1b` (VM yaml 728e58df), N = 5, Δ 2.5, H = 600 sim-s.
  - Overlay grounding file `config/grounding/s1b_dynamic_shield_escort.yaml`, md5 **409688866d25289309e081dcb9433037**. A32 R1: it is "PROMOTED to the registered shield config for confirmatory S1b cells, unedited" (lines 1449-1452).
- **Arms:** the registered pair "**Arms:** Layer 2 on, against Layer-2-off" (scene doc lines 370-371), on the same seeds.
  - **Arm A:** Layer 2 ON, live `gemini-robotics-er-2-preview` (ER-2). The in-episode classical shadow (`shadow_classical`) is recorded in every artifact, as in every pilot. It is not a separately run arm.
  - **Arm B:** Layer-2-off classical (A34 R9): the Nav2 stack only, no congestion mock, and M2/M3/M5 reasoning disabled. It uses the same scenario yaml, USD and seed as Arm A, the same 0.20 m floor swap and the same GT scan.
    - **Mechanism (A35):** the M5 config key `reasoning_enabled: false`. M5 then skips stall detection and never constructs a VLM backend, so there is no M2/M3 call, no decision artifact and no dispatch. `shadow_classical`, T0 probes and the contradiction trigger are forced off. The registry, task stream, arrival gate, `tasks_*.jsonl` and `m5_scene.jsonl` run unchanged. At startup M5 logs one line: `reasoning_enabled=false layer2=off detection=off m2=off m3=off shadow_classical=off t0_probe=off contradiction_trigger=off dispatch=off`.
    - **Overlays:** `s1b_l2off_orch_seed{k}.yaml` = `base_s1b_orch_seed{k}.yaml` + that one line. There is no escort grounding line, because M3 never runs. md5s: seed1 0bb7c9e1e89588af3dbdb351ce5067a9, seed2 cec7590c7743e2926ef73aab04b06f9a, seed3 7097f3a73cf85e5843dac246a4ee7486, seed4 397e0399867ec322912c741f0bc6d3d2, seed5 77bc12f2b872844802c095f8abb7479d. BACKEND stays gemini but is never constructed.
- **Why this cell:** A32 names no cells. This is the only S1b cell with a frozen configuration, the one A32 R1 configures, and the one A30/A31 ran. Non-shield S1b cells would keep `s1b_dynamic.yaml` (535f5281; A32 R1, "Every other cell keeps its current grounding file"), but no such cell has been run or kitted.
- **Condition (Arm A):** rule 16 + A32 + A34. That is:
  - backend: ER-2, plan channel on;
  - suppression + `refusal_no_action` + `backend_failed` arming;
  - churn bound OFF (A32 R4);
  - REC_SEC 4800, NAV2_ACTIVE_TIMEOUT_SEC 360, `NAV2_BRINGUP_MODE=sequential` with `NAV2_STACK_ACTIVE_TIMEOUT_SEC` unset, so the A32 R3 default of 180 s applies (the chain unsets it explicitly);
  - MAX_ANALYSES 0, so there is no analysis-count stop (A34 R7);
  - the 0.20 m floor installed (A28(i));
  - RECORD=0 (A34 R6);
  - `tag=confirmatory_t1 record=0 confirmatory=1 arm=<A|B>` in every bundle's `CONDITION.txt`.
- **Condition (Arm B):** A34 R9 as built by A35. Before launch, `ep_run_p10.sh` parses the overlaid yaml with the deployed loader and refuses unless `reasoning_enabled` is False (True for Arm A). The reason: `OrchestratorConfig` ignores unknown keys, so a stale runtime would otherwise run a billed Arm A. After the episode, the gate requires 0 decision artifacts, 0 `starting analysis` lines, exactly one status line, one `tasks_*.jsonl` and a non-empty `m5_scene.jsonl` (`cond_p10.py`).

### 1.3 Seeds, order and labels (A33(8), A34 R11)

The tranche is the first 5 of the registered first-20 confirmatory seeds: `config/s1_seeds.yaml` (md5 442a5e0f, append-only, sha256-pinned by `tests/unit/test_mapd_5_scenario.py`), positions 1-5.

| Episode | Position | Seed | Scenario yaml | Header `hdr_a20_seed{k}` | USD | Overlay `s1b_shield_escort_orch_seed{k}.yaml` | Unshielded base |
|---|---|---|---|---|---|---|---|
| E27 | 1 | 978442588 | d8cb4a0f | 65a577d8 | to be filled at build | d55cf337 | 4d2e540b |
| E28 | 2 | 1181837745 | f276a023 | a8391b9a | to be filled at build | eb047a43 | 2e248844 |
| E29 | 3 | 537191633 | c204935f | a4b15d6e | to be filled at build | 9565b6fe | ed573422 |
| E30 | 4 | 90907664 | 3b327906 | 2abcaeaa | to be filled at build | e0ec8543 | 6c459720 |
| E31 | 5 | 1912308941 | 7bae1aa0 | a13ea0c4 | to be filled at build | 71c975ed | b6a755b5 |

- **Order** (A33(9), ruled A34 R11): position 1 A→B, 2 B→A, 3 A→B, 4 B→A, 5 A→B, so 10 episodes. A bring-up abort retries the same (seed, arm). `DRY_RUN=1 bash chain_p10.sh` prints this table.
- **Labels:** E27-E31 continue the episode numbering after the last pilot (E26). The design mandates no labelling.
  - Bundles are `s1b_E{27..31}_seed{1..5}_armA_er2_confT1_a{attempt}` and `s1b_E{27..31}_seed{1..5}_armB_l2off_confT1_a{attempt}`. The scorer reads each arm from `CONDITION.txt`, never from the name.
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

- **Tree (Rev 3, A35):** runtime commit `feat/v3-arm-b-mode` @ `1624db1`. It equals `3efcd78` plus the `reasoning_enabled` switch in `models.py` and `orchestrator_node.py` (`mac_build_delta_p10.sh` checks exactly that). The delta is `git diff --name-only 9a018ca 1624db1` = the 4 files below + `orchestrator_node.py`. `delta_p10.tar` md5 **6e8b40fab5ab68aebe4b3e4f827b7536** (6 files, `git archive 1624db1`) and `manifest_p10.txt` 50376db3b76b99a14f71942d175768f8 supersede the A34 values in the next two bullets. In the table, `models.py`'s source is now **273bbf7f**, and `orchestrator_node.py` f149ecff → **e1b3b289** joins the colcon-built rows. The same single `swarm_orchestrator` rebuild installs both.
- **Tree (Rev 2, superseded by Rev 3):** runtime commit `feat/v3-integration` @ `3efcd78` (A34), the merge of `feat/v3-s1-scorers`. It is identical to `97d68e0` (the merge of `feat/v3-s1b-freeze`: R5 `6abea45`, R1 pin test `b2555b9`, R3 `d975f13`) over `reasoning`, `ros2_ws`, `scripts`, `config` and `isaac`. The VM carries the A28/A29 runtime `9a018ca` (A31).
- **Delta:** `git diff --name-only 9a018ca 3efcd78 -- reasoning ros2_ws scripts config isaac` gives exactly 4 files. The escort overlay rides along at pre == new.
  - `delta_p10.tar` md5 **d19466a764b785dbc2abde6af722ea5b** (`git archive 3efcd78`; `p10/mac_build_delta_p10.sh`). `manifest_p10.txt` is unchanged (7e59322ca8029c3d430adbd15d8eeb3f). The pre-A34 tar 81d8c629 held the same 5 files; only the archive commit id differs.
  - `benchmarks/s1_scoring` is not shipped. Scoring stays on the Mac.

| File | Layer / installed path | Pre (9a018ca) | Source (3efcd78 = 97d68e0) | Installed md5 |
|---|---|---|---|---|
| `reasoning/rag/command_grounder.py` | M3, live mount `/ws/...` | a4e8b5a8 | **cfbd1fb8** | to be filled at deploy |
| `swarm_orchestrator/models.py` | M5, colcon → `site-packages/swarm_orchestrator/models.py` | a76e3c00 | **273bbf7f** (Rev 3; b9b4d6d9 at 3efcd78) | to be filled at deploy |
| `swarm_orchestrator/orchestrator_node.py` (Rev 3) | M5, colcon → `site-packages/swarm_orchestrator/orchestrator_node.py` | f149ecff | **e1b3b289** | to be filled at deploy |
| `swarm_orchestrator/retreat_stage2.py` | M5, colcon → `site-packages/swarm_orchestrator/retreat_stage2.py` | 0bd96495 | **cf0dad3e** | to be filled at deploy |
| `scripts/vm/fc_launch.sh` | host launcher (run by `ep_run_p10.sh`) | 5a5ee4ac | **055db01e** | to be filled at deploy |
| `config/grounding/s1b_dynamic_shield_escort.yaml` | M3 config, live mount | 40968886 | 40968886 | to be filled at deploy |
| `swarm_execution` src + installed `safety.yaml` (`floor_p10.sh`) | M4 config, colcon | pristine 59839662 | **c41913f0** | to be filled at deploy |

- **Unchanged and gated before every episode:**
  - configs: `orchestrator.yaml` 1f656533 (src and installed), rag e18c723c, s1b_dynamic 535f5281, s1b_dynamic_shield ee5fe68f;
  - A30 runtime: `escort_clearance` 50766aeb, `grounding_view` e152fc74, `maneuver_geometry` 8923c35c, `retreat_candidates` 76f6b8d8, `reasoning_pipeline` 39a51bfc, `shadow_classical` 1de9588a (`orchestrator_node` moved to the deploy table, Rev 3);
  - A27 files: `retreat_shield` db0b6415, `plan_metrics` 9d3c1487;
  - A27 M4 files: `safety.py` c6c9cbae, `fresh_latch` 08d996a8, `nav2_adapter` f139305c, `command_bus_node` caad9edc;
  - recorder `scripts/record_topic_video.py` 90aa8971 (a tree pin only; it never starts at RECORD=0);
  - the episode driver `ep_run_p10.sh`, by its kit md5.
- **Deploy gates** (`deploy_p10.sh`, in order): PRE-IMAGE, SOURCE, LIVE MOUNT, HOST LAUNCHER (md5 plus the `:-180` default), colcon rebuild of `swarm_orchestrator` inside `vgu_ros` after a build/install purge, INSTALLED, PACKAGE SRC==INSTALLED, ORCH PIN, and a smoke test.
  - The smoke checks R1's flags on the three grounding files.
  - It also checks the R5 field `RetreatStage2Record.dropped_candidates`, `RetreatSelection.escort_park_dropped`, and `DroppedCandidate.reason == escort_hits_park`.
  - Rev 3: it also prints the A35 smoke `reasoning_enabled` default True and the status-line token.
- **Suite (at `97d68e0`, full testpaths, `--continue-on-collection-errors`, run 2026-10-21 for this kit):** 62 failed / 6833 passed / 153 skipped / 3 errors. That is p9's 62/6815/153/3 plus 18 passing tests from the freeze branch. The 65 failing ids are identical to the A27 reference list (`data/logs/vm_runs/a27/final_ids.txt`). Evidence: `data/logs/vm_runs/batch6/suite/`.
- **Suite (scorer commit `3c71503`, `pytest tests/unit -q --continue-on-collection-errors`):** 57 failed / 6877 passed / 151 skipped / 3 errors. That equals the `3efcd78` baseline of 57 failed / 3 errors for this invocation.
- **Suite (Rev 3, runtime `1624db1`, same invocation):** 57 failed / 6903 passed / 151 skipped / 3 errors. The extra 26 passing tests are `tests/unit/test_m5_node_reasoning_off.py`. The 60 failing/erroring ids equal `a27/final_ids.txt` minus `tests/simulation`. A Mac smoke (`p10/smoke_armb/mac_armb_smoke.log`) ran the seed-1 Arm B overlay through the real node with no pipeline injected: 240 stall scenes, 0 backend builds, 0 analyses, 0 artifacts, one status line, and the tasks and scene logs written.

### 1.5 Outcome measures, exactly as registered (no new predictions)

This tranche is confirmatory. It adds NO hypothesis and NO threshold. It collects the registered S1 measures for both arms on the first 5 seeds.

- **Per-run measures** (scene doc line 157, S1 Measures row): "Makespan and time-to-full-resolution; completeness via outcome classes; throughput as completed tasks / 25 over sim time; plus `delay_vs_free_flow` per segment".
  - Oracle sketch (scene doc lines 368-369): "Scoring per run: completeness (all 25 tasks done by H), makespan, throughput curve, and per-segment `delay_vs_free_flow`."
- **Per-conflict measures** (scene doc lines 366-367): "Scoring per conflict episode: detection (GT encounter → trigger latency), type label, involved-set F1, and plan-quality metrics (i-a)–(vi) as in v2."
  - Also: "**No `accepted_strategies` per episode.** Rule it explicitly at the freeze" (scene doc lines 364-365).
- **Conflict class** (design doc lines 973-975, A15(iii)): "latch-on-pass is REGISTERED as S1b's conflict class, and the S1a/S1b axis is re-registered as a RESOLVABILITY axis".
- **Comparison form** (design doc lines 480-484, R3.6a item 4): "The Arm A−Arm B comparison across regimes is registered as **CI estimation of the delta per regime**, with the Goldilocks expectation (delta maximal at intermediate difficulty) recorded as interpretation, not as a directional hypothesis."
  - This tranche estimates it for S1b by A33(7): pairs keyed by seed, each on its common window τ_i, with a paired percentile bootstrap (B = 10000, seed 20261021, 95%). Arm B has no reasoning, so its per-conflict deltas are `degenerate_arm_b` by construction (A34 R9).
- **Registered secondary readings** carried by the pilots' tracked scorers, reported as such:
  - A21(iii)(a) churn metrics and intermittent classification, "MEASURE NOW" (design doc line 1236);
  - A27(iv) vb∧matched, "READ with shielded robots excluded (lane-scope precedent; raw count co-reported)" (lines 1809-1811);
  - A28(iii) admitted ≠ productive as a metric distinction;
  - MC is "REGISTERED as an upper bound for live yield probability" (A22, lines 1281-1283). MC is context, not a prediction.
- **Scorer coverage** (frozen before any confirmatory episode; nothing is improvised after the data):
  - **Every registered S1 measure** is computed by `benchmarks/s1_scoring` at `feat/v3-freeflow-freeze` `3c71503` (code `9651988` + A34 R8 `f008616`), exactly as A33 defines it, with the A34 R10/R11 parameters as the CLI defaults. The measures are completeness, makespan ≡ time-to-full-resolution, the throughput curve, per-segment `delay_vs_free_flow`, GT conflict episodes, detection latency, type label (accepted {"deadlock"}), involved-set F1, plan quality (i-a)-(vi), and the Arm A − Arm B delta.
  - `delay_vs_free_flow` uses the frozen S1b table `benchmarks/s1_scoring/data/free_flow_s1b_2026-10-10.json`, md5 **b4002d7697f4d8f27c31792a9b269162**, by default for `mapd_5*` scenes (A34 R8; it is the 2026-10-10 harvest re-derived under the scorer's own departure rule).
  - **Also computed by tracked code** (the pilots' scorers, reported as secondary readings):
    - tasks completed / 25 and the censoring point `gt_end_rel_s` (`s1b_live_batch_stats` → `s1_gridlock_stats`);
    - churn class, alternations, productive events (`s1_churn_stats`);
    - provenance and vb∧matched, raw and shield-excluded;
    - first-conflict yield;
    - cost.
  - **Kit scorers:**
    - `batch6/score_p10.py`, the A34 wrapper: the gates of `batch6/score_p10_gates.py` plus `python -m benchmarks.s1_scoring` on every bundle, and the arm delta when both arms are present;
    - `batch6/aggregate_b6.py`, the Arm A decision-layer aggregates. It refuses anything but `tag=confirmatory_t1 record=0 confirmatory=1 arm=A` and is never pooled with E6-E26.

### 1.6 Safety and validity gates (gates, not hypotheses)

- **Contact gate** (the A30 P2 form, re-used as a validity gate): [Robot-robot only: GT does not log robot-static contact, and this gate does not cover it (corrected 2026-11-15, see erratum).]
  - No robot pair, at any time, below **0.18 m** GT centre distance. This is an all-pairs scan of `gt/ground_truth.jsonl` (`a27/kit/gt_contacts.py` rule, inlined in `score_p10_gates.py`). The GT contacts field is a stub (A14 corrigendum).
  - Zero `safety stop robot=… reason=hard_contact_floor` lines in `m4.log`. This applies to both arms (`score_p10_gates.py`).
  - A breach is reported with its pair, onset and minimum.
  - The episode is NOT dropped from the confirmatory count: it is a safety finding, scored as it ran.
- **Floor gate** (chain, after every episode): the `m4.log` startup line `hard_contact_floor_m=0.2` must appear. Otherwise the chain stops.
- **Condition gate** (`cond_p10.py`, after every episode). The chain stops on any failure. The gate requires:
  - `CONDITION.txt` carries `tag=confirmatory_t1 record=0 confirmatory=1 arm=<the arm run>`;
  - Arm A: every grounded artifact carries `escort_park_clearance`, `retreat_shield` and `retreat_fast_fail` True;
  - Arm B: 0 decision artifacts and 0 `starting analysis` lines in `m5.log`. Rev 3 (A35) adds exactly one M5 status line, exactly one `decisions/tasks_*.jsonl` and a non-empty `m5_scene.jsonl`, so that an M5 crash cannot pass as silence;
  - Arm A (Rev 3): 0 status lines.

  The same line also reports:
  - the `retreat=escort_park_filtered` tag counts;
  - the R5 `stage2.dropped_candidates` count (key absent → 0);
  - whether a recording dir is present (none is expected at RECORD=0).
- **Escort/park check** (`score_p10_gates.py`, via `score_p10.py`): every dispatched yield's escort legs vs the 0.45 m park clearance (A28(ii)). A leg below 0.45 m is a SAFETY FLAG, not a test. Tags and `dropped_candidates` are compared per artifact; a mismatch is reported, never repaired.
- **Pin gate** (chain, before every episode): every md5 in §1.4. Pin watch (A22 rule 4/11) and live watch run as in p9.

### 1.7 Budget and abort rules

- **Cap by sim-s (A34 R7):** every episode runs to the Isaac 600 sim-s horizon. Dollars are a safety ceiling only, set in one header block in `p10/chain_p10.sh`:
  - **CAP_EP = $0.25**, a guard: `cost_watch.py` touches the Isaac stop flag once est + $0.008 (A25 reserve-one-call rule) reaches min(CAP_EP, remaining);
  - **CAP_TOTAL = $1.30**, summed over this tranche's `_armA_er2_confT1_a*` cost logs only;
  - **MIN_REMAINING = $0.25**, the start floor, checked before each Arm A episode;
  - Arm B spends $0 (no VLM) and has no budget gate;
  - **MAX_ANALYSES = 0**: there is no analysis-count stop (`cost_watch.py` treats 0 as off).
  - est is a lower bound: a timed-out stage-2 call records no usage.
- **Censoring:** an episode cut by the guard, or by the pre-registered pin stop rule (`pin_watch.py`, rule 4/11), is right-censored at T_end with reason `stop_flag` (A33(0)). It is never dropped. A33(7)'s common window absorbs a shortened Arm A episode.
- **No top-up:** an episode that would breach the floor is not run and is reported. No episode is added after seeing data.
- **Bring-up:** up to 3 attempts per (seed, arm).
  - `ON_SEED_FAIL=stop`: a (seed, arm) whose 3 attempts all abort stops the tranche for an owner ruling. It is never skipped or substituted. See §1.8 (e).
- **Chain stops** on any pin, floor or condition gate failure, `STOP_CHAIN`, or the budget gate. It refuses at preflight, before any episode, while the Arm B launch mode is absent (A34 R9). Since Rev 3, `ARM_B_MODE=reasoning_enabled_false`. Before either arm of a seed runs, the chain checks that both arms' overlays exist, that the key is absent from Arm A's and that the last line of Arm B's is `reasoning_enabled: false`.
- **VM:** started for this tranche and STOPPED after it. The kit steps are in `batch6/NOTES_vm_b6.md`: pins → gen → build → deploy (orchestrator rebuild) → floor → overlays → chain → `restore_safety_p10.sh` → close-out → stop.

### 1.8 Owner rulings (ruled 2026-10-21: A33(8)-(9), A34 R6-R11)

Each item below was open in the initial draft. It is now ruled, and its kit default is replaced where the ruling differs.

- **(a) Cell and arms: RULED** (A34 run spec, R9). The cell is the shield cell, with both arms on the same seeds: Arm A Layer-2-on (ER-2) and Arm B Layer-2-off classical. No non-shield S1b cell is in this tranche. Arm B's launch mode was BLOCKED at A34 and is built by A35 (Rev 3): M5 `reasoning_enabled: false`.
- **(b) Seeds: RULED** (A33(8)). Positions 1-5 are kept. Every position 1-20 already ran as a pilot (E1-E5 echo, E6-E20 live). The pilots stay excluded (A32), and the fact that the confirmatory seeds are not unseen is a recorded LIMITATION.
- **(c) RECORD: RULED** (A34 R6). RECORD is a dataset tag only. fc_launch gets RECORD=0, as in every pilot, so no recorder runs. The confirmatory status is `confirmatory=1` in `CONDITION.txt`.
- **(d) Censoring: RULED** (A34 R7). Episodes are capped by sim-s, with a $0.25 guard (§1.7). A guard-cut episode is censored `stop_flag`. Each run's T_end and absolute GT end are reported; "by H" means by T_end of an uncut run (A34 R11).
- **(e) Seed-fail rule: RULED** (A34 run spec). `ON_SEED_FAIL=stop`, with 3 attempts per (seed, arm).
- **(f) Scorers: RULED** (A33, A34 R8, R10, R11). Every registered S1 measure has a frozen definition (A33) and a frozen scorer (`benchmarks/s1_scoring` at `3c71503`, free-flow table md5 b4002d7697f4d8f27c31792a9b269162). Its parameters are the A33 defaults ruled by R11, and accepted types are {"deadlock"} (R10). Accepted strategies were not ruled, so the scorer keeps `accepted_strategies=None`. Both these and the tracked-scorer measures of §1.5 are computed only after the pull (runbook step 13, from the scorer worktree), never from code written after the data.

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

## 2. Summary of Results

**Status: the tranche ran in full. All 10 confirmatory episodes (5 seeds × Arm A / Arm B, in the A33(9) order) ran to the 600 sim-s horizon. Every pin, floor, condition, contact (robot-robot (corrected 2026-11-15, see erratum)) and escort gate passed. Arm A spent est. $0.2127 of the $1.30 cap, and no guard or pin stop fired. No episode completed all 25 tasks, so completeness is "failed" and makespan is censored at the horizon in all 10.**

| Question | Answer |
|---|---|
| Host | `vgu-thu-base-isaac-vm-asia-northeast1-a` (asia-northeast1-a), the same zone-moved clone as batch 5. Ephemeral IP 34.84.196.224. It started at the first attempt (§3.1) |
| Deploy | `PINS_PRE OK`. Every gen, build, deploy, floor and overlay sentinel printed, including `SMOKE A35 reasoning_enabled default True status_line reasoning_enabled=false`. Installed md5 = source md5 for all 6 manifest rows and the floor (§3.2) |
| Tranche | 11 attempts: one sequential bring-up abort (E27 Arm B a1, $0), then 10 runs, one per (seed, arm). Arm B's silence gate passed 5/5. **Spend est. $0.2127 of $1.30** |
| Contact gate (robot-robot only (corrected 2026-11-15, see erratum)) | **PASS 10/10**: all-pairs GT minimum 0.225-0.424 m, no pair below 0.18 m, 0 `hard_contact_floor` stops |
| Escort/park check | **PASS**: 3 dispatched yields with a leg (0.490 / 0.538 / 0.458 m), 1 with no leg. 0 SAFETY FLAGs, and tags match `dropped_candidates` |
| A33 completeness / makespan | 0/10 complete. Makespan is censored (`horizon`) in all 10. Tasks completed: Arm A 16/125, Arm B 12/125 |
| A33(7) arm delta (A − B, 5 seed pairs, paired percentile bootstrap, 95 %) | throughput at τ **+0.032 [−0.008, +0.080]**; mean delay lower bound **−31.5 s [−71.6, −0.6]**; restricted makespan 0.0 [0.0, 0.0] (both arms censored at τ). The per-conflict measures are `degenerate_arm_b` by construction |
| A33 conflicts (Arm A) | 11 GT conflicts, 9 detected (recall 0.818). 0 false positives in 26 positive analyses. Type accuracy 0.778, involved-set F1 0.915, mean detection latency 17.6 s. Arm B: 10 GT conflicts, 0 detected (no reasoning) |

CONFIRMATORY (`confirmatory=1`), RECORD = 0. The arm delta is reported as a CI estimate (§1.5). It is not a test, and the tranche adds no hypothesis.

---

## 3. Deploy and Build Evidence (the §1 "to be filled" cells)

### 3.1 Host

- **VM:** `vgu-thu-base-isaac-vm-asia-northeast1-a`, zone asia-northeast1-a, project `project-5b0644ea-c6bd-4d13-a4a`. It is the batch-5 host: the snapshot clone of the batch-4 end-state disk, with an L4 GPU. The cross-VM equivalence caveat of the escort-filter report §3.1 is unchanged.
- **Start:** it started from TERMINATED at the first attempt (no stockout). Ephemeral IP 34.84.196.224. `vgu_ros` came up by itself.
- **Kit copy:** `rsync -a` without `--delete` into a fresh `~/v3_s1b/p10`. `md5sum -c kit_md5.txt` passed on the VM, with delta 6e8b40fab5ab68aebe4b3e4f827b7536.

### 3.2 Pins, scenarios, build, deploy and floor

- **Pins (`pins_pre_p10.sh`): `PINS_PRE OK`.** It checked the 26 p9 pins, the manifest pre-images, recorder 90aa8971, and the kit md5s including delta 6e8b40fa and the 5 Arm B overlays. The "info existing" lines are the pilot-era seed 2-5 scenarios.
- **Scenarios (`gen_p10.sh`):** seeds 1-5 NONCOMMENT_EQUAL, `VM == MAC (scen + ovsrc, seed positions 1-5)`, GEN_DONE. The yamls and headers equal §1.3.
- **Build (`build_p10.sh`):** the 5 yamls were installed == MAC, build rc 0, every USD is newer than its yaml, `usd_check` spawns equal the draws, and validate seed 1 returned rc 0.

| Episode | Scenario yaml | **USD md5 (measured)** |
|---|---|---|
| E27 | d8cb4a0f | `2c16f8d2285df079c1a853c5e26af228` |
| E28 | f276a023 | `b0ce58126f0ce6f3782ea6d1c44992ed` |
| E29 | c204935f | `1364fd432a2440fb4a3d8a910651daee` |
| E30 | 3b327906 | `29331415f1574424ef9971651cd514ae` |
| E31 | 7bae1aa0 | `e170acf03ccea2181091defc140f2766` |

- **The seed 2-5 USDs are byte-identical to their pilot-era USDs** (b0ce5812 / 1364fd43 / 29331415 / e170acf0, backed up by `build_p10.sh`). The pilot-era yamls for seeds 2-4 differ from the new ones in comments only: a comment-stripped diff is empty, and the seed 5 yaml is identical. A deterministic rebuild is therefore expected to give the same bytes. Seed 1 had no pilot-era file.
- **Deploy (`deploy_p10.sh`):** `PRE-IMAGE MD5 OK`, `SOURCE MD5 OK`, `LIVE MOUNT MD5 OK`, `HOST LAUNCHER MD5 OK` (055db01e, `:-180`), colcon rc 0 (swarm_orchestrator rebuilt), `INSTALLED MD5 OK`, `PACKAGE SRC==INSTALLED OK`, `ORCH PIN OK` (1f656533 src and installed).
  - `SMOKE escort_file shield True 0.05 ff True escort_park True dyn True | shield_file escort_park False | s1b_dynamic escort_park False | same-but-switch True`
  - `SMOKE R5 record_field True selection_field True dc_reason escort_hits_park`
  - `SMOKE A35 reasoning_enabled default True status_line reasoning_enabled=false`
- **Floor (`floor_p10.sh`):** `PRISTINE BACKUP OK`, `FLOOR INSTALLED OK`, `hard_contact_floor_m: 0.20`, A27 M4 pins c6c9cbae / 08d996a8 / f139305c / caad9edc, and `SMOKE key True floor 0.2 passer_exempt True shield_exempt False`.
- **Overlays (`ov_p10.sh`):**
  - `PROCEDURE REPRODUCES s1b_orch_seed6.yaml`.
  - The checks printed 5× "(want 2): 2", 5× "(want 1): 1" and 5× "(want 3): 3", then `VM == MAC (overlays, seed positions 1-5, Arm A + Arm B)`.
  - The 5 Arm A parse lines end `escort_park True H 600.0 reasoning_enabled True`; the 5 Arm B lines end `escort_park False H 600.0 reasoning_enabled False`.
  - The 10 overlays the chain reads (`~/v3_s1b/overlays/`) equal the kit.

| File (§1.4 rows) | Pre | New | **Installed md5 (measured)** |
|---|---|---|---|
| `reasoning/rag/command_grounder.py` (/ws live mount) | a4e8b5a8 | cfbd1fb8 | `cfbd1fb882e5cf9d3b9f45c6e8f67aec` |
| `swarm_orchestrator/models.py` (installed) | a76e3c00 | 273bbf7f | `273bbf7f7d01755226506fd892a380fa` |
| `swarm_orchestrator/orchestrator_node.py` (installed) | f149ecff | e1b3b289 | `e1b3b289ec05e3c21921fa0253829542` |
| `swarm_orchestrator/retreat_stage2.py` (installed) | 0bd96495 | cf0dad3e | `cf0dad3ebf6b96c09f32ec8d5fbe1301` |
| `scripts/vm/fc_launch.sh` (host) | 5a5ee4ac | 055db01e | `055db01eff423c72d74de6ed30cbc3b6` |
| `config/grounding/s1b_dynamic_shield_escort.yaml` (/ws) | 40968886 | 40968886 | `409688866d25289309e081dcb9433037` |
| `swarm_execution` `safety.yaml` (src + installed) | 59839662 | c41913f0 | `c41913f02cf4e988162c30a44a5dda04` during the tranche; restored to 59839662 (§9) |

- **Unchanged pins at deploy:** rag e18c723c, s1b_dynamic 535f5281, s1b_dynamic_shield ee5fe68f, task_stream 6e67c9ae, reasoning_pipeline 39a51bfc, shadow_classical 1de9588a.
- **Chain gates:** the pin gate passed before all 11 attempts, on the A32, A30 and A27 lines, with models 273bbf7f, orchestrator_node e1b3b289 and installed `safety.yaml` c41913f0. The `ep_run_p10.sh` arm check printed `ARM=<A|B> overlay reasoning_enabled=<True|False> (want <same>)` for every attempt.

---

## 4. Live Tranche E27-E31

The chain ran from 2026-10-21 14:07:06Z to 23:25:33Z, 9 h 18 min (§8). The HEADER line matched §1.7: `CAP_EP=0.25 CAP_TOTAL=1.30 MIN_REMAINING=0.25 MAX_ANALYSES=0 ON_SEED_FAIL=stop`, `arm_order=[1:AB 2:BA 3:AB 4:BA 5:AB]`, `arm_b_mode=[reasoning_enabled_false]`.

| # | Episode / arm | Attempts (stamp of the run) | Sim-s reached (T_end rel; censor) | Analyses: dispatched / not dispatched | Yields dispatched (yielder for passer; leg vs park) | Filter tags / dropped | GT closest pair (sim-s) | Floor stops | Tasks | Arm B silence gate | est $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | E27 seed 1, **A** | a1 20261021_140709 | 600.0 (570.7; horizon) | 11: 9 / 2 (`congestion_detected=false`) | 0 (4 yields refused: no shared lane ×2, no feasible yielder ×2) | 0 / 0 | r3–r5 0.424 m (78.6) | 0 | 8/25 | n/a (0 status lines) | 0.0859 |
| 2 | E27 seed 1, **B** | a1 abort (robot_2 not active 180 s, $0); **a2** 20261021_150711 | 600.0 (571.1; horizon) | 0 | n/a | n/a | r3–r4 0.395 m (600.0) | 0 | 5/25 | **PASS** (0 artifacts, 0 analyses, 1 status line, 1 tasks log, 2465 scene lines) | 0 |
| 3 | E28 seed 2, **B** | a1 20261021_160247 | 600.0 (570.4; horizon) | 0 | n/a | n/a | r1–r5 0.225 m (44.8) | 0 | 1/25 | **PASS** (2484 scene lines) | 0 |
| 4 | E28 seed 2, **A** | a1 20261021_165913 | 600.0 (568.8; horizon) | 4: 4 / 0 | `3c234140`: yield r1 for r5, **0.490 m**, admitted | 3 (`A:robot_5:0.230`, `A:robot_2:0.316` ×2) / 3 | r1–r5 0.333 m (45.5) | 0 | 2/25 | n/a | 0.0340 |
| 5 | E29 seed 3, **A** | a1 20261021_175338 | 600.0 (570.1; horizon) | 5: 5 / 0 | `14aefebe`: yield r1 for r4, **0.538 m**; `5622ed9c`: VLM yield r2 → dispatched yielder r3, no leg; both admitted | 2 (`B:robot_4:0.263`, `A:robot_4:0.262`) / 2 | r1–r4 0.261 m (46.4) | 0 | 0/25 | n/a | 0.0373 |
| 6 | E29 seed 3, **B** | a1 20261021_184839 | 600.0 (570.7; horizon) | 0 | n/a | n/a | r1–r4 0.301 m (600.0) | 0 | 0/25 | **PASS** (2441) | 0 |
| 7 | E30 seed 4, **B** | a1 20261021_194305 | 600.0 (572.0; horizon) | 0 | n/a | n/a | r3–r4 0.297 m (43.3) | 0 | 6/25 | **PASS** (2430) | 0 |
| 8 | E30 seed 4, **A** | a1 20261021_203816 | 600.0 (570.7; horizon) | 5: 5 / 0 | 0 (4 yields refused: ambiguous lane) | 0 / 0 | r3–r4 0.349 m (600.0) | 0 | 5/25 | n/a | 0.0317 |
| 9 | E31 seed 5, **A** | a1 20261021_213517 | 600.0 (569.2; horizon) | 3: 3 / 0 | `60afd0c1`: VLM yield r4 → **yield r3 for r4** (regrounded), **0.458 m**, admitted | 0 / 0 | r1–r5 0.341 m (255.3) | 0 | 1/25 | n/a | 0.0238 |
| 10 | E31 seed 5, **B** | a1 20261021_222955 | 600.0 (571.2; horizon) | 0 | n/a | n/a | r1–r2 0.388 m (57.1) | 0 | 0/25 | **PASS** (2487) | 0 |

- **Dispatched / not dispatched.** "Dispatched" means the artifact sent a command. A refused yield degrades to `temporary_wait` and is still dispatched. "Not dispatched" are the two E27 `congestion_detected=false` analyses.
- **Arm A condition (COND line):** `switch_on = shield_on = artifacts` in every Arm A run (11 / 4 / 5 / 5 / 3), `ungrounded=0`, `l2off_status=0`, `rec_dir=absent`. `dispatched_yields` was 0 / 1 / 2 / 0 / 1, and `escort_hits_park` 0 / 2 / 1 / 0 / 0.
- **Arm B condition:** exactly one M5 status line (`reasoning_enabled=false layer2=off ...`), 0 artifacts, 0 `starting analysis` lines, one `tasks_*.jsonl`, and a non-empty `m5_scene.jsonl`, in all 5 runs. The run order equals §1.3.
- **MC (upper bound, §1.9) against live first-conflict yields:**
  - Live first-conflict yields came out 2/5 (s2, s5) against MC 3/5 (s2, s4, s5).
  - s1: MC predicted a refusal, and live refused.
  - s2: live dispatched MC's pair and yielder, and **MC's predicted filter tag fired live** (`A:robot_5:0.230`, against MC's 0.231).
  - s3: MC predicted EMPTY_REROUTE. Live, the filter dropped `B:robot_4:0.263` and the dispatched candidate cleared the park point by 0.538 m.
  - s4: MC predicted an executable yield r4. Live, all four yields on r3+r4 were refused as "ambiguous lane": r3 headed 39° off both axes.
  - s5: MC predicted yield r3 at 0.767 m; live dispatched yield r3 at 0.458 m. The MC caveat of §1.9 applies.
- **Bring-up:** 11 attempts, with 1 sequential abort under the R3 180 s per-stack default (E27 B a1, robot_2). It cost $0, ended `GATE OK` / `RESTORE OK`, and the retry passed the idle gate at 0 s.
- **Budget:** the budget gate passed before every Arm A episode (spent $0 / 0.0859 / 0.1199 / 0.1572 / 0.1889). No episode came near its $0.25 guard; the highest was E27 A at $0.0859. **Tranche est. $0.2127 of $1.30.** The estimate is a lower bound (§1.7). `aggregate_b6.py` reads E30 A as $0.0318 against the cost log's $0.0317 (a rounding difference), so its total is $0.2128.

---

## 5. Registered S1 Measures (A33, `benchmarks/s1_scoring`)

Run: `score_p10.py` from `vgu-vlm-swarm-v3` @ `e794952` (`feat/v3-integration`, which contains `3c71503`), with `PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution:scripts`, on the 10 ran bundles (bring-up abort excluded). Scorer md5s: `score_p10.py` 7378ba25, `score_p10_gates.py` 49e4592f, `aggregate_b6.py` e2f0c554 (the A34-registered values). Free-flow table b4002d7697f4d8f27c31792a9b269162. Output: `batch6/scores_t1/s1_scoring.jsonl` (rc 0).

### 5.1 Per-run measures

| Episode / arm | T_end rel (s) | Censor | Tasks / 25 | Completeness | Makespan | Delay segments: scored / censored / never departed | Mean scored delay (s) |
|---|---|---|---|---|---|---|---|
| E27 A | 570.7 | horizon | 8 | failed | censored 570.7 | 8 / 4 / 0 | −0.13 |
| E27 B | 571.1 | horizon | 5 | failed | censored 571.1 | 6 / 3 / 1 | −0.13 |
| E28 A | 568.8 | horizon | 2 | failed | censored 568.8 | 2 / 5 / 0 | 25.45 |
| E28 B | 570.4 | horizon | 1 | failed | censored 570.4 | 1 / 4 / 1 | 0.00 |
| E29 A | 570.1 | horizon | 0 | failed | censored 570.1 | 1 / 4 / 0 | −0.20 |
| E29 B | 570.7 | horizon | 0 | failed | censored 570.7 | 1 / 4 / 0 | −0.20 |
| E30 A | 570.7 | horizon | 5 | failed | censored 570.7 | 6 / 3 / 0 | 0.23 |
| E30 B | 572.0 | horizon | 6 | failed | censored 572.0 | 6 / 3 / 1 | 0.03 |
| E31 A | 569.2 | horizon | 1 | failed | censored 569.2 | 1 / 4 / 1 | 40.60 |
| E31 B | 571.2 | horizon | 0 | failed | censored 571.2 | 0 / 5 / 0 | n/a |

- **Totals:** Arm A 16/125 tasks, delay segments 18 scored / 20 censored / 1 never departed. Arm B 12/125 tasks, 14 / 19 / 3.
- **Censored delays** carry a lower bound (`delay_lower_bound_s`), which the arm delta uses. Small negative scored delays (−0.2 s or less) are arrivals within the free-flow table's rounding.

### 5.2 Per-conflict measures (Arm A; Arm B is `degenerate_arm_b` by construction)

| Episode | GT conflicts | Detected | Positive analyses / false positives | Type labels (accepted {"deadlock"}) | Involved-set F1 per detected conflict | Detection latency (s) |
|---|---|---|---|---|---|---|
| E27 A | 1 | 1 | 9 / 0 (2 negatives) | bottleneck 4, deadlock 1, crowding 4 | 0.67 | 1.9 |
| E28 A | 2 | 2 | 4 / 0 | deadlock 4 | 1.00, 0.57 | 1.7, 51.9 |
| E29 A | 3 | 2 | 5 / 0 | deadlock 5 | 1.00, 1.00 | 2.5, 56.1 |
| E30 A | 2 | 1 | 5 / 0 | deadlock 5 | 1.00 | 1.6 |
| E31 A | 3 | 3 | 3 / 0 | deadlock 2, crowding 1 | 1.00, 1.00, 1.00 | 37.6, 1.4, 3.3 |

- **Arm A pooled:** recall 9/11 (0.818), precision 1.0, type accuracy 0.778, involved-set F1 0.915, mean detection latency 17.6 s. 0 `backend_failed`.
- **Plan quality:** emission rate 0.923, agreement rate 0.077. Per-run plan quality (edit distance, provenance, churn fractions, revision types) is in the jsonl.
- **Arm B:** 10 GT conflicts, 0 detected, as expected with Layer 2 off.

### 5.3 Arm A − Arm B delta (A33(7))

There are 5 pairs keyed by seed, each on its common window τ_i (570.7 / 568.8 / 570.1 / 570.7 / 569.2 s), and no unpaired bundles. Paired percentile bootstrap, B = 10000, seed 20261021, 95 %. The scorer labels the delta "conditional on owner decision D4 (Arm B identity and parity, A13(iii))".

| Measure | Arm A | Arm B | Delta A − B | 95 % CI | Status |
|---|---|---|---|---|---|
| throughput at τ (completed / 25) | 0.128 | 0.096 | **+0.032** | [−0.008, +0.080] | ok |
| restricted makespan (s) | 569.88 | 569.88 | 0.0 | [0.0, 0.0] | ok (both arms censored at τ in every pair) |
| mean delay lower bound (s) | 323.4 | 354.9 | **−31.5** | [−71.6, −0.6] | ok |
| detection recall | 0.818 | 0.0 | 0.818 | [0.636, 1.0] | degenerate_arm_b |
| detection latency (s) | 17.6 | n/a | n/a | n/a | degenerate_arm_b |
| type accuracy | 0.778 | n/a | n/a | n/a | degenerate_arm_b |
| involved-set F1 | 0.915 | n/a | n/a | n/a | degenerate_arm_b |
| plan emission rate | 0.923 | n/a | n/a | n/a | degenerate_arm_b |
| plan agreement rate | 0.077 | n/a | n/a | n/a | degenerate_arm_b |

- **Reading, without a hypothesis (§1.5):**
  - The throughput delta's CI includes 0.
  - The delay-lower-bound CI excludes 0 by 0.6 s, with Arm A lower.
  - With N = 5 pairs and every run censored at the horizon, these are interval estimates for the S1b regime only. No directional claim is registered.

---

## 6. Arm A Decision-Layer Aggregates (secondary readings, `aggregate_b6.py`)

Output: `batch6/agg_b6.json` (rc 0, 5 Arm A bundles, `confirmatory_t1 only (pilots E6-E26 excluded)`). It is never pooled with `batch5/agg_b5.json`.

| Aggregate | Value |
|---|---|
| Tasks / 25 (censoring point `gt_end_rel_s`) | E27 8 (570.7), E28 2 (568.8), E29 0 (570.1), E30 5 (570.7), E31 1 (569.2) |
| Churn class (A21(iii)) | clogged, resolved, intermittent, clogged, resolved. **Max alternations in one cluster: 0 in all 5** |
| Attribution | INDETERMINATE (0/5 episodes had ≥ 3 clearing dispatches into one cluster) |
| Productive events (A28(iii)) | 2 nonzero / 5 (E28 `3c234140` dispatch → progress 64.1 s; E31 `60afd0c1` 44.6 s), p95 1 |
| First-conflict yield | **2/5** (E28, E31), Clopper-Pearson [0.053, 0.853], against the MC upper bound 3/5 |
| Both clusters | 28 valid analyses, 9 with two clusters present, 0 named both, 0 dispatched both |
| vb∧matched (A27(iv)), raw / shield-excluded | E28 0 / 1, every other episode 0 / 0 |
| Provenance | E27 repaired 5, m3_default 4; E28 vlm_verbatim 2, m3_default 2; E29 m3_default 3, repaired 2; E30 m3_default 4, repaired 1; E31 repaired 1, m3_default 2 |
| Cost | $0.0859 / 0.0340 / 0.0373 / 0.0318 / 0.0238, total $0.2128 (cost logs $0.2127, §4) |

---

## 7. Safety and Validity Gates (§1.6)

Output: `batch6/scores_t1/gates_p10.jsonl` (`score_p10_gates.py` via `score_p10.py`).

| Gate | Result |
|---|---|
| Contact (all pairs, GT, < 0.18 m) | **PASS 10/10.** Minima: A 0.424 / 0.333 / 0.261 / 0.349 / 0.341 m; B 0.395 / 0.225 / 0.301 / 0.297 / 0.388 m (seeds 1-5). `contacts_below_018` empty everywhere |
| `hard_contact_floor` stops in `m4.log` | **0** in all 10. 0 B3 fast-fail firings |
| Floor gate (chain) | OK after all 10 runs (`hard_contact_floor_m=0.2` startup line) |
| Condition gate (chain `cond_p10.py`, and `condition_ok` in the scorer) | OK 10/10. Tags `tag=confirmatory_t1 record=0 confirmatory=1 arm=<A|B>` |
| Escort/park (P1 form, 0.45 m) | **PASS.** Legs 0.490 (E28 `3c234140`), 0.538 (E29 `14aefebe`), 0.458 m (E31 `60afd0c1`); E29 `5622ed9c` has no leg. 0 SAFETY FLAGs, and `tags_vs_dropped_mismatch` is empty in every bundle |
| Pin gate (chain) | OK before all 11 attempts. No `pin_watch` stop |

---

## 8. Deviations and Notes

- **Wall-clock time:** the tranche took 9 h 18 min of chain time. The real-time factor was about 0.18 and each full-horizon episode about 55 min, consistent with the full-horizon pilots E7/E8. The operator brief had quoted about 3 h. That figure matches batch 5, whose $0.05 cap cut episodes at about 140 sim-s. A34 R7 runs every episode to 600 sim-s. No wall-clock or GPU-hour cap is registered in §1, A34 or the runbook, so the chain was not stopped. This is recorded in `NOTES_vm_b6.md`.
- **Runbook copies:** the runbook used was `batch6/p10/NOTES_vm_b6.md`, the A35 revision pinned in `kit_md5.txt`. `batch6/NOTES_vm_b6.md` is an older pre-A35 copy ("NOT RUNNABLE") and was neither used nor edited. The VM log entries are appended to the Mac kit copy. The VM's copy is in `batch6/p10_vm/`.
- **Scorer worktree:** step 13 names `vgu-vlm-swarm-v5d` at `3c71503` or later. Scoring ran from `vgu-vlm-swarm-v3` at `e794952`, which contains `3c71503`, as the operator brief directed.
  - `git diff 3c71503 e794952 -- benchmarks/s1_scoring` is empty, so the A33 scorer code is byte-identical to the registered tree.
  - `git diff 97d68e0 e794952` is empty over the tracked scripts the kit scorers import (`s1_churn_stats`, `s1b_live_batch_stats`, `s1_gridlock_stats`, `s1_grounding_replay`, `s1b_episode_stats`) and over the `reasoning` modules `score_p10_gates.py` imports.
  - The only difference is `swarm_orchestrator/models.py` (A32 R5 + A35). Its scorer-tree md5 is 273bbf7f, the deployed runtime, so the gates parse the overlays with the loader that ran.
- **Log-line counts (operator notes):** each Arm B `m5.log` has two `reasoning_enabled=false` lines, the status line and the `shadow_classical ... forced off` warning. `l2off_status=1` is the expected value, as the runbook notes.
- **Extra pulled files:** `ep_run_p10.sh` leaves an `_backup_<label>` directory (orchestrator.yaml, rag.yaml) per attempt. The runbook's pull glob does not name these. They were pulled as well, giving 66 entries with the VM list equal to the Mac list.
- **USD identity:** see §3.2. The seed 2-5 USDs are byte-identical to the pilot-era ones because the yamls differ in comments only.
- No corrections to earlier batches.

---

## 9. VM End State and Pins

- **Processes at close:** no `run_simulation`, Kit, `fc_launch`, `ep_run`, chain or watcher process. `vgu_ros` was up (restarted by the last `fc_launch` cleanup). GPU 0 %, 155 MiB. `~/v3_s1b` was chowned to ubuntu.
- **`safety.yaml` restored:** `restore_safety_p10.sh` printed `RESTORE PRISTINE OK`, with src and installed **59839662**.
- **Close-out pins (`pins_pre_p10.sh`, recorded, not gated):** `PINS_PRE FAILED` **by design**.
  - It flags exactly the 5 deployed files: fc_launch 055db01e, command_grounder cfbd1fb8, orchestrator_node e1b3b289, models 273bbf7f, retreat_stage2 cf0dad3e.
  - It also flags the leftover `_confT1_` run files. Every other pin was ok.
  - The A35 runtime stays deployed. Without an overlay setting `reasoning_enabled: false`, it defaults to reasoning on.
  - Log: `p10_vm/pins_post.log`.
- **Bundles** are in `data/logs/vm_runs/batch6/` (gitignored; pulled with `rsync -a`, without `--delete`):
  - 11 attempt directories `s1b_E{27..31}_seed*_arm{A,B}_*_confT1_a*`, each with `.cost` / `.outer` / `.pin` / `.watch` logs;
  - 11 `_backup_*` directories;
  - the VM kit in `batch6/p10_vm/`: `chain_p10.log`, `attempts.tsv`, the pins, gen, build, deploy, floor, overlay and restore logs, and `pins_post.log`.
- **Scores:** `batch6/scores_t1/` (`gates_p10.jsonl`, `s1_scoring.jsonl`), `batch6/scores_t1.log`, and `batch6/agg_b6.json`.
- **The VM is STOPPED:** `gcloud compute instances stop`, then STATUS `TERMINATED`.

---

## References

- **Rulings:** prereg-v3 A34 (R6-R11, run spec) and A33 (S1 scorer definitions) at `0891cd8`; A32 (R1-R5), A31, A30, A28(i), A27(iv), A25, A22, A21(iii), A15(iii), R3.6a, R3.7 (`feat/v3-design` @ `24fa2bc`); scene doc S1 table and oracle sketch.
- **Previous batch:** `docs/reports/2026-10-17-escort-filter-minibatch.md` (§1 is the template; §9 "Kit changes for the next kit").
- **Scorer:** `benchmarks/s1_scoring/` and `benchmarks/s1_scoring/data/free_flow_s1b_2026-10-10.json` at `feat/v3-freeflow-freeze` `3c71503`.
- **Code:** `reasoning/rag/command_grounder.py` (`DroppedCandidate`, `filter_escort_park_candidates`), `swarm_orchestrator/models.py` (`RetreatStage2Record.dropped_candidates`), `scripts/vm/fc_launch.sh` (`NAV2_STACK_ACTIVE_TIMEOUT_SEC`), `config/grounding/s1b_dynamic_shield_escort.yaml`, `config/s1_seeds.yaml`.
- **Kit** (gitignored, `data/logs/vm_runs/batch6/`): `NOTES_vm_b6.md`; `p10/` (`pins_pre_p10.sh`, `gen_p10.sh`, `build_p10.sh`, `deploy_p10.sh`, `floor_p10.sh`, `ov_p10.sh`, `chain_p10.sh`, `ep_run_p10.sh`, `cond_p10.py`, `cost_watch.py`, `pin_watch.py`, `restore_safety_p10.sh`, `parse_ov_p10.py`, `manifest_p10.txt`, `delta_p10.tar`, `kit_md5.txt`, `scen/`, `ovsrc/`, `overlays/`, `src/`, Mac generators and logs); `mc_seeds_p10.{py,jsonl}`; `score_p10.py`; `score_p10_gates.py`; `aggregate_b6.py`; `s1_scoring_pilots.jsonl` (pilot smoke with the frozen table). Kit md5s are in A34 and `p10/kit_md5.txt`.
