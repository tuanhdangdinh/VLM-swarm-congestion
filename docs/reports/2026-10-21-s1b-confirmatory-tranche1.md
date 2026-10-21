# S1b Confirmatory Tranche 1: E27-E31, Two Arms

**Prepared:** 2026-10-21

**Revision history:**

- Rev 3 (2026-10-21, before any live call): Arm B's launch mode exists and is registered as prereg-v3 A35 (`feat/v3-design` `9a5eb8f`). M5 `reasoning_enabled: false` is delivered by the overlays `s1b_l2off_orch_seed{k}.yaml`, and the tranche is RUNNABLE. The new runtime commit is `feat/v3-arm-b-mode` `1624db1`, which is `3efcd78` plus `models.py` and `orchestrator_node.py`. The deploy delta is rebuilt (`delta_p10.tar` 6e8b40fab5ab68aebe4b3e4f827b7536, 6 files; `manifest_p10.txt` 50376db3b76b99a14f71942d175768f8). The Arm B gates are tightened (§1.2, §1.6). Nothing else changes, and nothing exploratory is added.
- Rev 2 (2026-10-21, before any live call): §1 updated for the owner rulings R6-R11 recorded in prereg-v3 A34 (`feat/v3-design` `0891cd8`), which close §1.8. The tranche is now 10 episodes (5 seeds × Arm A / Arm B, interleaved). RECORD is a dataset tag only (RECORD=0 to fc_launch). Episodes are capped by sim-s, with dollars as a guard. Every registered S1 measure is scored by `benchmarks/s1_scoring` at `feat/v3-freeflow-freeze` `3c71503`, with the frozen S1b free-flow table (md5 b4002d7697f4d8f27c31792a9b269162). Arm B (Layer-2-off classical) is ruled but has no launch mode, so the tranche is NOT RUNNABLE until it exists. Runtime commit `3efcd78`. Nothing exploratory is added.
- Initial draft: §1 pre-registration of the first confirmatory S1b tranche under prereg-v3 A32 (cell, arm, seeds, configs and md5s, the registered outcome measures quoted with line cites, safety gates, budget, abort rules) and the open items in §1.8 that the owner must rule before any live call. The VM kit is `data/logs/vm_runs/batch6/p10/` (gitignored), built offline. No VM was started. Results follow in later sections.

---

CONFIRMATORY (`confirmatory=1`), RECORD = 0 (A34 R6). RUNNABLE: A34 R9's Arm B launch mode exists (A35, Rev 3).

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

- **Contact gate** (the A30 P2 form, re-used as a validity gate):
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

## References

- **Rulings:** prereg-v3 A34 (R6-R11, run spec) and A33 (S1 scorer definitions) at `0891cd8`; A32 (R1-R5), A31, A30, A28(i), A27(iv), A25, A22, A21(iii), A15(iii), R3.6a, R3.7 (`feat/v3-design` @ `24fa2bc`); scene doc S1 table and oracle sketch.
- **Previous batch:** `docs/reports/2026-10-17-escort-filter-minibatch.md` (§1 is the template; §9 "Kit changes for the next kit").
- **Scorer:** `benchmarks/s1_scoring/` and `benchmarks/s1_scoring/data/free_flow_s1b_2026-10-10.json` at `feat/v3-freeflow-freeze` `3c71503`.
- **Code:** `reasoning/rag/command_grounder.py` (`DroppedCandidate`, `filter_escort_park_candidates`), `swarm_orchestrator/models.py` (`RetreatStage2Record.dropped_candidates`), `scripts/vm/fc_launch.sh` (`NAV2_STACK_ACTIVE_TIMEOUT_SEC`), `config/grounding/s1b_dynamic_shield_escort.yaml`, `config/s1_seeds.yaml`.
- **Kit** (gitignored, `data/logs/vm_runs/batch6/`): `NOTES_vm_b6.md`; `p10/` (`pins_pre_p10.sh`, `gen_p10.sh`, `build_p10.sh`, `deploy_p10.sh`, `floor_p10.sh`, `ov_p10.sh`, `chain_p10.sh`, `ep_run_p10.sh`, `cond_p10.py`, `cost_watch.py`, `pin_watch.py`, `restore_safety_p10.sh`, `parse_ov_p10.py`, `manifest_p10.txt`, `delta_p10.tar`, `kit_md5.txt`, `scen/`, `ovsrc/`, `overlays/`, `src/`, Mac generators and logs); `mc_seeds_p10.{py,jsonl}`; `score_p10.py`; `score_p10_gates.py`; `aggregate_b6.py`; `s1_scoring_pilots.jsonl` (pilot smoke with the frozen table). Kit md5s are in A34 and `p10/kit_md5.txt`.
