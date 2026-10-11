# The A27 Shield Safety Fix and the E21-E23 Mini-batch

**Prepared:** 2026-10-12

**Revision history:**

- Initial draft: A27(i)-(iv) built and merged (shield-only holds out of the clearing exemption, the S1 shield-cell 0.20 m floor, the B3 log line, the shield-excluded vb∧matched reading); deployed; mini-batch E21-E23 PRE-REGISTERED before any live call (§1). Results follow in later sections.

---

## 1. Pre-registration (written and committed before any live call)

PILOT-ONLY, RECORD = 0. This block is frozen at commit time. Later sections may
only add to it, never edit it.

### 1.1 Tree, deploy and condition

- **Tree:** `feat/v3-integration` @ `f2553f1` = `c08904a` + `feat/v3-shield-fix`:
  - `236f0f1` fix: shield-only holds out of the clearing exemption (M3 marks each hold `retreat_shield_hold: true`; M4 `admitted_partners` drops such members in every phase, and A19's command-start waiver treats them as bystanders), plus the floor file `config/safety/safety_floor020.yaml`;
  - `36598ac` feat: the B3 structured log line (`b3_fast_fail command=… robot=… phase=… elapsed_s=… deadline_s=… saved_s=… sim_t=… detail="…"`);
  - `93dd89f` feat: vb∧matched read with retreat-shielded robots excluded;
  - `fb6ef47` test: 61 new tests, plus one more (the key survives M5's validated dispatch) committed with this block.
- **Suite (at `fb6ef47`):** 62 failed / 6646 passed / 153 skipped / 3 errors → 62 / 6707 / 153 / 3, identical failing ids (65), on the branch and on a fresh `c08904a` worktree. The final count is in the results section.
- **Deploy** (`p8/deploy_p8.sh`; pre-images = the batch-3 p7 runtime, all verified):

| File | Layer | md5 |
|---|---|---|
| `reasoning/rag/retreat_shield.py` | M3, live mount | db0b6415 (was 1019f7d4) |
| `reasoning/rag/plan_metrics.py` | M3/M5 scorer, live mount | 9d3c1487 (was f403de5c) |
| `swarm_execution/safety.py` | M4, colcon | c6c9cbae (was a9425c70) |
| `swarm_execution/fresh_latch.py` | M4, colcon | 08d996a8 (was 021d63bd) |
| `swarm_execution/nav2_adapter.py` | M4, colcon | f139305c (was 0d290cfd) |
| `swarm_execution/command_bus_node.py` | M4, colcon | caad9edc (was 3d1f394f) |
| `config/safety/safety_floor020.yaml` (new) | M4 config source | c41913f0 |
| `swarm_execution` src + installed `safety.yaml` | M4 config, colcon | **c41913f0** (was pristine 59839662) |

  Checks: PRE-IMAGE, SOURCE, LIVE MOUNT, INSTALLED, PACKAGE SRC==INSTALLED and FLOOR INSTALLED all OK (`swarm_execution` build/ and install purged, colcon rc 0). In-container smoke: the M3 and M4 key literals agree, floor 0.2, passer pair exempt, shield pair NOT exempt, deadlines 195.0 / 148.2 s. M5 is unchanged (not rebuilt; `orchestrator_node` installed f149ecff).
- **Unchanged pins:** `orchestrator.yaml` 1f656533 (src + installed), `rag.yaml` e18c723c, `s1b_dynamic.yaml` 535f5281, `s1b_dynamic_shield.yaml` ee5fe68f, `command_grounder.py` 3436f10c, `fc_launch.sh` 5a5ee4ac, `mapd_5_s1b.yaml` 728e58df.
- **How "S1 shield cell" is operationalised for the floor.** The only reader of `hard_contact_floor_m` is the safety monitor, which loads the INSTALLED `swarm_execution` `safety.yaml`. A grounding-file key would be inert, so `s1b_dynamic_shield.yaml` (and the seed-21 overlay that points at it) is unchanged. The floor variant is committed as `config/safety/safety_floor020.yaml`, byte-identical to IB10's validated `c41913f0` (one line: `hard_contact_floor_m: 0.20`), and is swapped in install-wide for this batch (the IB10 `swap_safety.sh` precedent). It is restored to pristine 59839662 after the batch (`p8/restore_safety_p8.sh`). Every episode in this batch is a shield cell, so install-wide equals cell-scoped here.
- **Condition:** rule 15 verbatim (gemini-robotics-er-2-preview, plan channel on, suppression + `refusal_no_action` + `backend_failed` arming, churn bound OFF, Δ 2.5, H 600, REC_SEC 4800, NAV2_ACTIVE_TIMEOUT_SEC 360, `NAV2_BRINGUP_MODE=sequential`, MAX_ANALYSES 40, overlays `s1b_shield_orch_seed{k}.yaml` → `s1b_dynamic_shield.yaml`) on the A27 runtime with the floor installed.

### 1.2 Seeds, scenarios and overlays

| Episode | Seed (`config/s1_seeds.yaml` position) | Scenario yaml | USD (newer than yaml) | Overlay | Spawns (= draws) |
|---|---|---|---|---|---|
| E21 | 2107305794 (21) | 61fd6faf | 8a21596e (staged in batch 3) | 7e4d1a9f (staged in batch 3) | Wm N E S Wp |
| E22 | 1949376341 (22) | ccb674e8 | 7b87e464 | d79d04a0 | S Wp E Wm N |
| E23 | 1256773113 (23) | ea69ed93 | 7cf07059 | e6f4ddbd | N S Wp Wm E |

- Seed 21's staging needed no regeneration: neither the scenario nor the grounding file changed, and the exemption and floor live in M4 code and M4 config, which the USD does not encode.
- Seeds 22-23 (`p8/gen_s22_23.sh`, `p8/build_s22_23.sh`, `p8/ov_s22_23.sh`, the p4/p7 procedure): header sources non-comment-equal, yaml seeds equal the list, built alone as root in one SimulationApp (build rc 0, USDs newer than their yamls), usd_check spawns equal the draws, validate seed22 rc 0. The overlay procedure re-verified to byte-reproduce `s1b_orch_seed6.yaml`; each shield overlay differs from its unshielded base in exactly the `grounding_params_path` line; all three parse on the deployed tree as seed, junction [NW, SW, N, S], plan / supp / rna True, churn off, H 600, shield True 0.05, fast-fail True.
- **MC (echo, upper bound; `batch4/mc_seeds_21_23.py`):** s21 r1+r4 at 9.2 s → EXECUTABLE yield r1 (= batch 3's prediction); s22 r2+r5 at 11.6 s → EXECUTABLE yield r2; s23 r2+r4 at 13.4 s → REFUSED (no shared lane).

### 1.3 Run protocol and budget

- Episodes in order E21, E22, E23 (`p8/chain_p8.sh` = `chain_p7.sh` except: P8 paths, seeds 21-23, labels `s1b_E{k}_seed{k}_er2_e{a}` (e = batch 4), the A27 pins plus the installed-floor md5 in the between-episode pin gate, a post-episode gate on the safety monitor's startup line `hard_contact_floor_m=0.2` in `m4.log` (the loader silently falls back to 0.0), caps). Up to 3 attempts per episode on a bring-up abort; 2 consecutive episodes × 3 aborts → stop.
- **Budget (VM-enforced, A25 reserve-one-call rule):** the $0.15 cap and the $0.04 start reserve are the brief's; the per-episode cap rule is **agent-chosen**. Batch cap **$0.15** HARD over this batch's `_e` cost logs only. An episode starts only if remaining ≥ **$0.04**. Episode cap = **min($0.05, remaining)**; `cost_watch` (5 s poll) touches the Isaac stop flag once est + $0.008 (one call) reaches the episode cap. The agent-chosen $0.05 cap is fixed now so that all three seeds can run inside $0.15 (batch-3 episodes cost $0.040-0.065, so an episode may be truncated by the cap; a truncation is reported, not repaired). est is a lower bound (a timed-out stage-2 call records no usage).
- **If an episode would breach the cap or the start gate, it is not run, and that is reported.** No episode is added after seeing data.

### 1.4 Predictions (scoreable)

- **P1 (admits stay high).** Pooled over E21-E23, admitted / dispatched yields ≥ 0.6, where admitted = an m4.log `crossing_chain gate_admit command=<id>` line, and a yield failed by B3 or by any deadline counts as NOT admitted. Untestable (reported as such) if fewer than 2 yields are dispatched. P1 and P3 pull against each other: every B3 failure of a yield lowers P1.
- **P2 (no contact with the floor armed).** Zero contacts: no robot pair, at any time in any episode, comes below **0.18 m** centre distance in GT positions (`gt/ground_truth.jsonl`, computed from positions; the GT contacts field is not used, trap 20). Floor firings are allowed and counted: m4.log `safety stop robot=… reason=hard_contact_floor` lines (with their `pairs=` detail); for each firing the pair's GT minimum and closing speed are reported. **A floor firing whose pair still reaches GT < 0.18 m is a P2 FAILURE** (IB10 saw the floor latch at M1 0.200 while TF was already 0.175-0.136 m), reported with that GT minimum and closing speed, not excused.
- **P3 (B3 is an honest outcome).** Counted from the new `b3_fast_fail` log line only. Prediction: every B3 firing follows a fresh latch of the clearing robot during its backup or pull-off (a `safety stop robot=<clearing robot>` line after the step started, ≥ 2 s before the firing); no clearing robot is safety-stopped during its backup or pull-off for more than ~3 s without a B3 line; a shielded robot coming within 0.45 m of its yielder during the maneuver ends in a B3 failure, not a close pass. The count is reported per episode with elapsed vs deadline.
- **P4 (budget_k).** The pooled bar is ≥ 8 classified S1/S1b episodes with a nonzero productive count (7 of 27 now). At the pooled live rate 6/15, P(at least one of three nonzero) ≈ 0.78. Prediction: the bar is met. If met, the triple {budget_k, window_sim_sec, alternation_max} is derived by the rule-14 / A21 procedure: budget_k = nearest-rank p95 of per-event dispatches-into-group; window_sim_sec = max(p95 dispatch-to-credited-progress latency, the longest inter-dispatch gap in a productive group), rounded up to 10 s; alternation_max = the maximum alternations in a productive group; accepted only if a ChurnLedger replay withholds no productive event and does withhold inside E3. If not met: n_more = ceil((8 − k_nonzero) / r_live).

### 1.5 Capture and aggregates

- **Per episode:** the batch-3 bundle and capture schema (rule 15) pulled to `data/logs/vm_runs/batch4/`, PLUS: B3 firings from the log line, floor firings, all-pairs GT minimum and any contact interval, per shielded robot its closest approach to the yielder during the maneuver, and per-episode spend.
- **Rev 6 aggregates** over ALL live episodes E6-E23 (`scripts/s1b_live_batch_stats.py` with the A27(iv) change; `batch4/aggregate_b4.py` = `aggregate_b3.py` + the e-labels + MC 22-23, required to reproduce `agg_b3.json` block-for-block on the 15 prior bundles): admitted / dispatched pooled, clearance releases, first-conflict yield vs MC (Clopper-Pearson 95 %), livelock / alternations (A24 conjunction, A25(iii) ESCALATION), the budget_k bar, vb∧matched raw and shield-excluded (batch-3 reference 3 raw / 5 excluded, reproduced by the new scorer).

### 1.6 Known before the batch (disclosed, not tuned on)

- **The floor would not have caught E18.** In the E18 replay fixture the near pass is 0.231 m (M1), above 0.20. The de-exemption is the operative fix: under the new rule the yielder–r1 pair latches at the first scene inside 0.45 m (60.47 sim-s, 0.444 m). The replay is open loop and uses the scene's sim stamps as the watch clock, so its B3 firing 2.2 s later is in sim time; live, the debounce is 2.0 s WALL (about 0.8 sim-s at RTF 0.38), so B3 would fire about 2 wall-s after the latch, and the live yielder would already have stopped at the latch.
- **Floor pre-check over every live clearing command (63 exempt pairs, 15 episodes, `a27/kit/floor_check.py`).** Only one exempt pair ever went below 0.20 m: **E20 `6cf402ed`, yielder r1 ↔ escorted passer r3, M1 0.121 m / GT 0.109 m.** No pair started a clearing window below 0.20 m.
- **That pair is an unreported batch-3 contact.** All-pairs GT scan (`a27/kit/gt_contacts.py`): r3, escorted 1.843 m east along y ≈ −1.27, drove into r1 parked at its retreat point (2.16, −1.43), 0.14 m off the escort line. GT < 0.18 m from 251.8 sim-s, pushing r1 at about 0.02 m/s to 0.109 m, then both stopped there to the end of the episode. The release logged as `clearance` (escort odometry reached `passer_clear_m`). No other pair in the 15 live episodes ever came below 0.18 m. This is the floor's designed backstop case. With the floor armed, the same geometry should latch the pair at M1 0.20 m; the closing speed is far below IB10's 0.3 m/s. Owner ruling needed on the escort/retreat geometry (§ later).
