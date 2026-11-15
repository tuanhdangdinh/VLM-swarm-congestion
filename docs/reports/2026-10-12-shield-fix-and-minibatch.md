# The A27 Shield Safety Fix and the E21-E23 Mini-batch

**Prepared:** 2026-10-12

**Revision history:**

- Initial draft: A27(i)-(iv) built and merged (shield-only holds out of the clearing exemption, the S1 shield-cell 0.20 m floor, the B3 log line, the shield-excluded vb∧matched reading); deployed; mini-batch E21-E23 PRE-REGISTERED before any live call (§1). Results follow in later sections.
- Rev 2: Summary added above the frozen §1; §2-§8 add the build detail, the batch results, the predictions scored, the Rev 6 aggregates with the derived budget_k triple, the E20 contact correction, the VM end state and the owner rulings needed.
- Rev 3 (2026-11-15): added the erratum "2026-11-15 Erratum — Contact Wording"; P2's contact wording scoped to robot-robot pair distance; §1 annotated, not reworded; no number or verdict changed.

---

## 2026-11-15 Erratum — Contact Wording

Ground truth's two contact lists, `robot_static_contacts` and `robot_robot_contacts`, are hard-coded to `[]` in `isaac/vgu_sim/acceptance_logging.py:99-100`. No contact detector exists, so an empty list shows nothing. The sound channel is the logged minimum pairwise distance (`min_pairwise_distance_m` and the GT positions), a centre-to-centre robot-robot distance. Nothing in GT logs contact with static obstacles. Same caveat: `docs/reports/2026-09-25-overnight-findings.md` (Metric correction 2 and its Rev 11 note) and `docs/reports/2026-10-08-s1-pilot.md` (GT `robot_static_contacts`); full account in section 8.7 of `docs/reports/2026-11-15-demo-campaign-results.md`.

- **What the statements rested on.** P2 is defined on robot-pair GT centre distance < 0.18 m, computed from positions, not on the GT contact field (§1 P2). So "0 GT contacts" and "zero contacts" here are robot-robot distance statements, and they hold as such.
- **Affected statements.** Summary table, Predictions row ("0 GT contacts"); §1 P2 ("no contact with the floor armed", "Zero contacts"); the P2 row of the predictions table ("zero contacts"). Each is scoped in place and marked (corrected 2026-11-15, see erratum); §1 is annotated with a bracket, its text unchanged.
- **What remains supported.** Robot-robot only: all-pairs GT minimum 0.305 / 0.328 / 0.409 m, no pair below 0.18 m, 0 floor firings. P2 PASS stands as registered (a robot-pair prediction). The E20 contact (§6) was found by the same distance scan and is unaffected.
- **Static obstacles.** S1b has rack islands (`mapd_5_s1b`: `obstacle_1`, `obstacle_2`, `obstacle_3`), so the robot-static gap is material here: nothing in this report measures robot-to-island contact. A later offline escort-segment check (demo-campaign report 8.7.4) found no admitted escort segment in the October batches 2-6 crossing a declared box; that is a centreline check, not a contact measurement.

---

## Summary

**Status: all four A27 rulings built, merged and deployed; the pre-registered mini-batch ran all three seeds inside budget. The budget_k bar is met (8 of 30), and the derived triple is (budget_k 3, window_sim_sec 130, alternation_max 0). It passes the ChurnLedger acceptance replay. The de-exemption and B3 were armed live but never exercised: no shielded robot came within 0.75 m of its yielder.**

| Question | Answer |
|---|---|
| (i) De-exemption | M3 marks each shield hold `retreat_shield_hold: true`. M4's `admitted_partners` drops such members in every phase, and A19's command-start waiver treats them as bystanders. Passers keep the exemption, and so do the A21 lane-scoped off-lane holds. Live: all 4 dispatched shield holds (E21, E22) carried the key |
| (i) E18-class fixture | Replay of E18's live M1 scenes through the tracker and latch rules. The pre-A27 command never latched the yielder (0.231 m pass). The fixed command latches r2+r1 at the first scene inside 0.45 m (60.47 sim-s, 0.444 m), and `FreshLatchWatch` then fires B3. A 0.20 floor alone would not have caught it (0.231 > 0.20) |
| (i) Floor | `config/safety/safety_floor020.yaml` (= IB10's c41913f0) installed for the batch. Every episode's safety monitor started with `hard_contact_floor_m=0.2`. Restored to pristine 59839662 afterwards |
| (iii) B3 log | One structured line per firing: `b3_fast_fail command=… robot=… phase=… elapsed_s=… deadline_s=… saved_s=… sim_t=… detail="…"`, with the deadline from new pure helpers shared with `Nav2Adapter`. Live: 0 firings |
| (iv) Scorer | `plan_metrics.shield_excluded_dispatch_match` + `score_decision_artifact` + `s1b_live_batch_stats.py`. Batch-3 regression **3 raw / 5 excluded reproduced**. Pooled E6-E23: 13 raw / 16 excluded |
| Suite | 62 / 6646 / 153 / 3 → **62 / 6708 / 153 / 3**, identical failing ids (65); +62 tests |
| Batch | E21, E22 (second attempt after one sequential bring-up abort) and E23 ran. **Spend $0.1069 of $0.15**; E23 was cut by its $0.05 episode cap at 200.5 sim-s |
| Predictions | **P1 PASS** (admitted 3/3). **P2 PASS** (0 robot pairs below 0.18 m GT centre distance, 0 floor firings; robot-robot only (corrected 2026-11-15, see erratum)). **P3: two clauses vacuous, one held** (0 B3 firings and no shielded robot within 0.45 m; but no clearing robot was held in its step without a B3 line, tested on 3 yields). **P4 PASS** (bar 8/30) |
| Rev 6 | Admitted/dispatched pooled 11/17 (A26+A27 runtime 8/8). Clearance releases 2 in this batch. First-conflict yield 5/18 live (CI 0.097-0.535) against MC 12/18. **0 alternations in 18 live episodes; NO LIVELOCK** (5 opportunity episodes, 0 ARCH). Both clusters named 14/103 |
| Correction | **Batch 3's E20 `6cf402ed` "clearance release" was a contact**: the escorted passer r3 drove into the parked yielder r1 (GT < 0.18 m from 251.8 sim-s, min 0.109 m, then frozen to the end). It was found by the pre-arm floor check (§1.6). It was not a productive event, so budget_k is unaffected |
| Owner rulings | (1) escort-into-retreat geometry (E20 contact); (2) which registered cells enable the churn bound with the frozen triple, and whether to accept it with budget_k and the window each set by one observation; (3) how the floor is selected for future shield cells (the VM is back on pristine `safety.yaml`); (4) the shield's latch → B3 path has no live exercise yet (§8) |

PILOT-ONLY, RECORD = 0.

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
- **P2 (no contact with the floor armed).** Zero contacts: no robot pair, at any time in any episode, comes below **0.18 m** centre distance in GT positions (`gt/ground_truth.jsonl`, computed from positions; the GT contacts field is not used, trap 20). [Robot-robot only: GT does not log robot-static contact, and this prediction does not cover it (corrected 2026-11-15, see erratum).] Floor firings are allowed and counted: m4.log `safety stop robot=… reason=hard_contact_floor` lines (with their `pairs=` detail); for each firing the pair's GT minimum and closing speed are reported. **A floor firing whose pair still reaches GT < 0.18 m is a P2 FAILURE** (IB10 saw the floor latch at M1 0.200 while TF was already 0.175-0.136 m), reported with that GT minimum and closing speed, not excused.
- **P3 (B3 is an honest outcome).** Counted from the new `b3_fast_fail` log line only. Prediction: every B3 firing follows a fresh latch of the clearing robot during its backup or pull-off (a `safety stop robot=<clearing robot>` line after the step started, ≥ 2 s before the firing); no clearing robot is safety-stopped during its backup or pull-off for more than ~3 s without a B3 line; a shielded robot coming within 0.45 m of its yielder during the maneuver ends in a B3 failure, not a close pass. The count is reported per episode with elapsed vs deadline.
- **P4 (budget_k).** The pooled bar is ≥ 8 classified S1/S1b episodes with a nonzero productive count (7 of 27 now). At the pooled live rate 6/15, P(at least one of three nonzero) ≈ 0.78. Prediction: the bar is met. If met, the triple {budget_k, window_sim_sec, alternation_max} is derived by the rule-14 / A21 procedure: budget_k = nearest-rank p95 of per-event dispatches-into-group; window_sim_sec = max(p95 dispatch-to-credited-progress latency, the longest inter-dispatch gap in a productive group), rounded up to 10 s; alternation_max = the maximum alternations in a productive group; accepted only if a ChurnLedger replay withholds no productive event and does withhold inside E3. If not met: n_more = ceil((8 − k_nonzero) / r_live).

### 1.5 Capture and aggregates

- **Per episode:** the batch-3 bundle and capture schema (rule 15) pulled to `data/logs/vm_runs/batch4/`, PLUS: B3 firings from the log line, floor firings, all-pairs GT minimum and any contact interval, per shielded robot its closest approach to the yielder during the maneuver, and per-episode spend.
- **Rev 6 aggregates** over ALL live episodes E6-E23 (`scripts/s1b_live_batch_stats.py` with the A27(iv) change; `batch4/aggregate_b4.py` = `aggregate_b3.py` + the e-labels + MC 22-23, required to reproduce `agg_b3.json` block-for-block on the 15 prior bundles): admitted / dispatched pooled, clearance releases, first-conflict yield vs MC (Clopper-Pearson 95 %), livelock / alternations (A24 conjunction, A25(iii) ESCALATION), the budget_k bar, vb∧matched raw and shield-excluded (batch-3 reference 3 raw / 5 excluded, reproduced by the new scorer).

### 1.6 Known before the batch (disclosed, not tuned on)

- **The floor would not have caught E18.** In the E18 replay fixture the near pass is 0.231 m (M1), above 0.20. The de-exemption is the operative fix: under the new rule the yielder–r1 pair latches at the first scene inside 0.45 m (60.47 sim-s, 0.444 m). The replay is open loop and uses the scene's sim stamps as the watch clock, so its B3 firing 2.2 s later is in sim time; live, the debounce is 2.0 s WALL (about 0.8 sim-s at RTF 0.38), so B3 would fire about 2 wall-s after the latch, and the live yielder would already have stopped at the latch.
- **Floor pre-check over every live clearing command (63 exempt pairs, 15 episodes, `a27/kit/floor_check.py`).** Only one exempt pair ever went below 0.20 m: **E20 `6cf402ed`, yielder r1 ↔ escorted passer r3, M1 0.121 m / GT 0.109 m.** No pair started a clearing window below 0.20 m.
- **That pair is an unreported batch-3 contact.** All-pairs GT scan (`a27/kit/gt_contacts.py`): r3, escorted 1.843 m east along y ≈ −1.27, drove into r1 parked at its retreat point (2.16, −1.43), 0.14 m off the escort line. GT < 0.18 m from 251.8 sim-s, pushing r1 at about 0.02 m/s to 0.109 m, then both stopped there to the end of the episode. The release logged as `clearance` (escort odometry reached `passer_clear_m`). No other pair in the 15 live episodes ever came below 0.18 m. This is the floor's designed backstop case. With the floor armed, the same geometry should latch the pair at M1 0.20 m; the closing speed is far below IB10's 0.3 m/s. Owner ruling needed on the escort/retreat geometry (§ later).

---

## 2. What Was Built

### 2.1 A27(i): shield-only holds out of the clearing exemption

- **M3** (`reasoning/rag/retreat_shield.py`): each shield hold's parameters carry `SHIELD_HOLD_KEY = "retreat_shield_hold": true`. The predicate itself (corridor, intent legs, PIN RULE, margin) is untouched. All 9 A25 fixtures keep their registered outcomes, including the 5 required ones: E10 r3, E13 r2, E14 r2 and E17b r2 shielded, and E16 nobody.
- **M4** (`swarm_execution/safety.py`): `is_shield_hold(action, parameters)` reads the same literal (M4 does not import M3). `CoordinationTracker` records shield-only members per command and evicts them with the command.
  - `admitted_partners(..., shield_holds=)` subtracts them in every branch: the reverse / no-order branch, the backing-up branch and the hold branch.
  - `capture_latch_partners` no longer counts them as "own". A shielded robot already latched with the yielder at command start is therefore a bystander under A19: the yielder may leave, and the shielded robot is held. This is a deliberate choice, tested (`test_shield_hold_standing_in_a_latch_at_start_is_waived_one_sided`).
  - Without that, a pre-existing latch would hold the yielder from the start, and B3 (which ignores holds that stand at arm time) would never fire, so the yield would run to its deadline.
- **What did not change:** passers (incl. multi-passer chains) and A21 lane-scoped off-lane holds (a `requested_strategy` wait without the key) stay exempt. The floor still applies to every exempt or waived pair.
- **Fixtures** (`tests/unit/test_a27_shield_fix.py`):
  - the 10 shield holds of the 9 A25 fixtures: every shielded pair is NOT exempt while the yielder backs up; every passer pair is; a shielded robot 0.30 m from the yielder latches both;
  - the pre-A27 command shape (no key) WAS exempt;
  - **E18 near-pass** (`tests/unit/data/a27_shield_fix/e18_near_pass.json`, 154 live M1 scenes of command `56b599af` from backup start to hold start). The old runtime never holds the yielder, and the floor alone never fires (0.231 m). The new runtime latches r2+r1 at the first scene inside 0.45 m, 60.47 sim-s, before the pull-off. Fed to `FreshLatchWatch`, B3 fires after the debounce with `co_held` naming r1 (open-loop replay on sim stamps, §1.6).

### 2.2 A27(i): the S1 shield-cell floor

See §1.1 for how "shield cell" was operationalised: an install-wide swap for the batch, then a restore. `test_floor_file_is_safety_yaml_with_only_the_floor_enabled` pins the variant as `safety.yaml` with exactly one line changed. `test_floor_still_latches_an_exempt_passer_pair_in_contact` checks the backstop on a pair that stays exempt.

### 2.3 A27(iii): the B3 log line

- `nav2_adapter.backup_deadline_sec` / `sidestep_deadline_sec` are the primitives' own deadline formulas, factored out. The primitives now call them, so the arithmetic is unchanged: 195.0 s for a 1.3 m backup, 148.2 s for a 0.36 m sidestep.
- `fresh_latch.fast_fail_log_line` formats the line. `CommandBusNode._dispatch` wraps each B3 abort check: the first non-None detail (the primitive fails the step on it) logs once, at INFO, with the step's wall elapsed time against its deadline and the sim time.
- Tests: one firing → exactly one line, with `elapsed_s` / `deadline_s` for both the backup and the pull-off; no key → no line.
- The batch scorer (`batch4/b4_extras.py`) counts the line. The batch-3 timing inference stays alongside it as a cross-check, and it reproduces E19's inferred firing from the safety-stop runs (hold run 6.0 wall-s into the step, held 2.0 s).

### 2.4 A27(iv): the shield-excluded vb∧matched reading

- `plan_metrics.shield_excluded_dispatch_match(artifact)` recomputes the dispatch match only for commands carrying `grounding=retreat_shield:` tags, first asserting that the recomputed raw match equals the stored one. It returns raw, excluded, the shielded ids and whether their plan legs were all `continue`.
- `score_decision_artifact` sets `verbatim_dispatch_matched_shield_excluded`. `tabulate_provenance_by_strategy_correctness` counts it beside the raw count.
- `scripts/s1b_live_batch_stats.py` adds per-row `dispatch_matches_plan_shield_excluded` / `shielded` / `shielded_legs_continue` and the per-episode `vb_and_dispatch_matched_shield_excluded`. The new fields are additive only.
- **Regression:** on batch 3, raw 1/0/1 and excluded 1/0/3 for E18/E19/E20, i.e. **3 raw / 5 excluded**. All three shielded artifacts flip only through their shield legs, all of which are `continue` in the plan. A committed fixture pins this (`batch3_plan_artifacts.json`).
- `batch4/aggregate_b4.py` reproduces `agg_b3.json` block-for-block on the 15 prior bundles once the new fields are stripped.

### 2.5 Suite and commits

- `236f0f1` fix, `36598ac` feat (B3 log), `93dd89f` feat (scorer), `fb6ef47` test, `8ba6715` prereg (+1 test); merged as `f2553f1` and `ce7a8a6`.
- Full suite: **62 failed / 6646 passed / 153 skipped / 3 errors → 62 / 6708 / 153 / 3**, identical 65 failing ids (baseline also re-run on a fresh `c08904a` worktree: 62 / 6646 / 153 / 3).
- Ruff is clean on every changed file except `nav2_adapter.py`'s two pre-existing findings (I001, E501), which were left in place.

---

## 3. Live Mini-batch E21-E23

| Episode | Stamp | Analyses | est $ | Yields → admitted (release) | Shield holds (closest approach to yielder) | B3 | Floor | GT closest pair | Tasks | Churn | Productive |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E21 (seed 21) | 20261011_223557 | 4 | 0.0324 | 1 → **1** (clearance, 98.2) | r5 (2.12 m), r3 (2.95 m) | 0 | 0 | r2–r3 0.305 m | 1/25 | clogged | 0 |
| E22 (seed 22) | 20261011_233545 (attempt 2) | 4 | 0.0320 | 1 → **1** (hold timer, 123.6) | r3 (1.49 m), r1 (0.75 m) | 0 | 0 | r2–r5 0.328 m | 3/25 | clogged | 0 |
| E23 (seed 23) | 20261012_003217 | 6 | 0.0425 (cap) | 1 → **1** (clearance, 123.0) | none | 0 | 0 | r2–r3 0.409 m | 6/25 (censored 200.5 sim-s) | resolved | **1** |

- **E21:**
  - The first analysis (42.2 sim-s) named the MC pair: a verbatim yield r1 for r4. M3 grounded it as a node handoff on lane x and shielded r5 and r3 (both carrying the key).
  - It was admitted at 79.3 and released by **clearance** at 98.2. The escort reached its distance, but neither r1 nor r4 made credited progress in the window, so the event is unproductive.
  - Three later yields on {r2, r3} were refused ("no executable retreat": r2 has no candidate surviving the sweep, r3 would back off its axis) and withheld. Suppression held the scene (177 suppressed re-analyses).
- **E22:**
  - Attempt 1 aborted in sequential bring-up (robot_1 not active 120 s after launch, $0). This is the first sequential abort since A24: pooled sequential now 1 in 21 attempts.
  - In attempt 2, the first analysis named the MC pair as yield r5 for r2. M3 regrounded it to r2 (`node_handoff_regrounded`), so the plan is `repaired` with one swap. r3 and r1 were shielded.
  - It was admitted at 78.6 and released by the hold timer at 123.6, again unproductive.
  - Then came a no-congestion analysis, a 5-robot `temporary_wait` dispatch and a `junction_clear` refused ("no feasible yielder").
- **E23:**
  - The first analysis was a `temporary_wait` on r2+r4 (repaired). MC had predicted a refusal here, so this is not a first-conflict yield.
  - The second (59.8) was a verbatim yield r5 for r1 with no shield. It was admitted at 96.2 and released by **clearance** at 123.0, and r1 then arrived (133.8). **Productive.**
  - Four `junction_clear` analyses on {r2, r3, r4} were refused and withheld.
  - The $0.05 cap's stop flag fired at est $0.0425, and the episode ended at 200.5 sim-s with 6/25 tasks.
- **Bring-up:** 3 episodes, 4 attempts, 1 abort. GATE OK and RESTORE OK on every attempt. The floor gate was OK on every episode that ran. The attempt after the abort is clean of trap-16a contamination: the abort's Isaac had exited ("Isaac gone ... 0 alive"), there was no leftover ground-truth directory, and there are 0 "jump back in time" lines in its `m4.log` and `isaac.log`.

---

## 4. Predictions Scored

| Prediction | Result | Evidence |
|---|---|---|
| P1 admits ≥ 0.6 | **PASS, 3/3** | `gate_admit` on 04457772, 07da775d, 9803bd34; no yield failed |
| P2 zero contacts (robot-robot (corrected 2026-11-15, see erratum)), floor counted | **PASS** | All-pairs GT minimum 0.305 / 0.328 / 0.409 m; no pair below 0.18 m; 0 `reason=hard_contact_floor` lines |
| P3 B3 honest | **Per clause: 2 vacuous, 1 held** | (a) "every B3 follows a fresh latch": vacuous, 0 `b3_fast_fail` lines (matching 0 inferred). (b) "a shielded robot within 0.45 m of its yielder ends in B3": vacuous, the closest shielded approach was E22 r1 at 0.75 m, at dispatch. (c) "no clearing robot held more than ~3 s in its step without a B3 line": **held** on all 3 live yields, whose only in-step holds were the A19 command-start flicker (0.1-0.7 wall-s at step start, before the monitor knows the command). The E18 replay fixture remains the only evidence that the de-exemption converts a near pass into latch → B3 |
| P4 budget_k bar | **PASS, 8 of 30** | E23 is the 8th nonzero classified episode (live 7/18). The triple is derived in §5.2 |

---

## 5. Rev 6 Aggregates (All Live Episodes E6-E23)

Output: `batch4/agg_b4.json` (`aggregate_b4.py` over `batch4/live18.txt`); extras in `batch4/extras_E2{1,2,3}.json`.

### 5.1 The rule-14 blocks

| Aggregate | Rev 6 |
|---|---|
| Admitted / dispatched live yields | **11/17 pooled**: E6-E17 3/9 (pre-A25/A26), batch 3 5/5, batch 4 3/3. On the A26+A27 runtime 8/8 |
| Clearance releases | Batch 4: 2 (E21 `04457772`, E23 `9803bd34`). Pooled: E6, E20 `f269ab37`, E20 `6cf402ed` (**a contact push, §6**), E21, E23 |
| (a) Attribution | **NO LIVELOCK UNDER THE REAL MODEL**: 5 opportunity episodes (E13, E16, E17, E18, E20; unchanged), 0 ARCH, **0 alternations in all 18 live episodes**. Batch 4 never reached the opportunity bar (max 1 clearing dispatch into one cluster) |
| (b) Productive | All classified n = 30, **8 nonzero** (S1a A1, E6, E10, E11, E17, E18, E20, **E23**), p95 1. Live 7/18 nonzero, p95 2. **Bar (≥ 8) MET** |
| (c) First-conflict yield | **5/18 live** (E15, E18, E20, E21, E22), Clopper-Pearson 0.097-0.535, against MC 12/18. Batch 4 alone 2/3 against MC 2/3: s21 and s22 executable and taken; s23 MC-refused and live a `temporary_wait` |
| (d) Both clusters | Named 14/103 valid analyses (0/14 in batch 4); a both-cluster plan dispatched 7/103 |
| (e) Wandering vs park | No finisher in batch 4; still one S1b finisher ever. Undecided |
| (f) Cost | Batch 4 $0.1069 (E21 0.0324, E22 0.0320 + $0 abort, E23 0.0425). All-live median $0.0335, range 0.0174-0.0954, **all-live total $0.7546** over 18 episodes |
| vb∧matched (A27(iv) registered reading) | **16 shield-excluded / 13 raw** over E6-E23 (batch 3: 5 / 3; batch 4: 2 / 1, E21's shielded verbatim yield flipping) |

### 5.2 budget_k: the derived triple

The procedure is the one pre-stated in rule 14 (§1.4 P4): `batch4/derive_triple.py` → `triple_derivation.json`, with the acceptance replay `batch2/triple_check.py` → `triple_3_130_0.json`.

| Input | Values (n = 9 productive events, 30 classified episodes) | Result |
|---|---|---|
| Dispatches into the group up to and including each productive event | sorted 1, 1, 1, 1, 1, 2, 2, 2, 3 | nearest-rank p95 (rank 9) = **budget_k 3** |
| Dispatch → first credited progress (s) | 5.6, 18.7, 31.2, 35.4, 62.5, 65.4, 69.9, 70.4, 79.3 | p95 = 79.3 s |
| Longest inter-dispatch gap in a productive group | S1a A1 88.5, E6 **122.6**, E11 44.2, E17 66.9, E18 83.6, E20 80.0 (single-dispatch groups 0) | 122.6 s |
| window_sim_sec | max(79.3, 122.6) = 122.6, rounded up to 10 s | **130** |
| Alternations inside productive groups | all 0 | **alternation_max 0** |

- **Acceptance replay: PASS.** The ChurnLedger replay over all 30 classified bundles withholds no productive event. It withholds S1b E3 twice (alternation, the required condition) and 6 of S1a A3's 12 identical reroutes (budget). No live episode has a withhold.
- **Frozen triple (by rule 14: bar met, replay passed): {budget_k 3, window_sim_sec 130, alternation_max 0}.** It equals the Rev 4 reference-only triple. Enabling it per cell is the owner's (§8). E23's new event (1 dispatch, 69.9 s) moved no input across a rank boundary.
- **Caveats for the freeze ruling:**
  - It rests on n = 9 events. budget_k 3 is set by one event (E17 `9cf93ebe`, the 3rd of 4 dispatches), and the window by one gap (E6, 122.6 s).
  - alternation_max 0 means any A-B-A in a window is withheld, so the bound turns on at the first alternation; none has occurred live.

---

## 6. Correction to Batch 3: the E20 Contact

- **What happened.** In batch 3's E20, command `6cf402ed` (yield r1 for r3, admitted 234.4) parked r1 at its retreat point (2.156, −1.428). The escort then drove r3 1.843 m east along y ≈ −1.27. That line passes 0.14 m from the parked yielder, and the yielder–passer pair is exempt.
  - GT: below 0.45 m at 248.1, **below 0.18 m at 251.8**, then r3 pushed r1 at about 0.02 m/s down to 0.109 m by 263.
  - The escort's odometry reached `passer_clear_m` and the hold released as `clearance` (263.4). Both robots then stood at 0.11 m (a mutual min-distance latch) to the end of the episode.
  - The GT contacts field logged nothing (trap 20).
- **What it changes.** Batch 3's headline "two clearance releases" holds only for `f269ab37`. `6cf402ed` was a contact push, not a clearance. It was not a credited productive event (`f269ab37` was), so budget_k, the bar and the Rev 5/6 productive blocks are unaffected. No other pair in E6-E23 ever came below 0.18 m.
- **The floor's role.** This is the case the 0.20 m floor backstops: at M1 0.20 m the pair would latch before contact at this closing speed (the floor pre-check, `a27/kit/floor_check.py`). It was armed for all of batch 4 and never fired.
- **Root cause (not fixed here):** the escort distance and line do not check the parked yielder's footprint. That is an M3 grounding defect (escort/retreat geometry) and needs a ruling (§8).

---

## 7. VM End State and Pins

- **Processes:** no Isaac, Kit, fc_launch, chain or watcher process. `vgu_ros` is up and idle; GPU 0 %, 136 MiB; `data/logs/simulation` is empty. 58 stray root-owned files under the repo (src `__pycache__` from the root USD build) were chowned to ubuntu, and 0 non-ubuntu files remain outside the colcon trees.
- **safety.yaml restored to pristine** (`p8/restore_safety_p8.sh`: plain cp + touch, `build/` and install purged, rebuild, `RESTORE PRISTINE OK`). Future shield cells must re-swap the floor (`deploy_p8.sh`'s floor step) until a ruling says otherwise.
- **Pin line (A27), verified at close:**

| File | md5 (deployed, at close) |
|---|---|
| `reasoning/rag/retreat_shield.py` (/ws) | db0b6415 |
| `reasoning/rag/plan_metrics.py` (/ws) | 9d3c1487 |
| `swarm_execution/safety.py` (installed = src) | c6c9cbae |
| `swarm_execution/fresh_latch.py` | 08d996a8 |
| `swarm_execution/nav2_adapter.py` | f139305c |
| `swarm_execution/command_bus_node.py` | caad9edc |
| `config/safety/safety_floor020.yaml` (on disk, not installed) | c41913f0 |
| `swarm_execution` `safety.yaml`, src + installed | **59839662** at close (c41913f0 during the batch) |
| Unchanged | `orchestrator.yaml` 1f656533 src + installed, `orchestrator_node` f149ecff, `command_grounder` 3436f10c, `s1b_dynamic_shield.yaml` ee5fe68f, `rag.yaml` e18c723c, `fc_launch.sh` 5a5ee4ac |
| Staged scenarios | seed 22 USD 7b87e464 / yaml ccb674e8, seed 23 USD 7cf07059 / yaml ea69ed93; overlays d79d04a0 / e6f4ddbd |

- **NOTES:** rule 16 (the pre-registration) was appended before the first live call, and the end state after the batch (`~/v3_s1b/NOTES.md`; copy at `batch4/NOTES_vm_b4.md`).
- **Bundles** are under `data/logs/vm_runs/batch4/` (gitignored), including the aborted `s1b_E22_seed22_er2_e1`.
- **The VM is RUNNING.**

---

## 8. Owner Rulings Needed

1. **Escort-into-retreat geometry (§6).**
   - Batch 3's E20 `6cf402ed` was a real contact: an escorted passer pushed its parked yielder for about 11 sim-s.
   - The floor now backstops it, but the grounding should not produce an escort line 0.14 m off the yielder's park point.
   - Ruling: fix the escort or retreat geometry (an M3 sweep of the escort leg against the parked yielder's footprint), or accept the floor as the only guard.
2. **Enabling the frozen triple (3, 130, 0).** By rule 14 the triple is frozen once the bar is met and the replay passes, and both hold. What remains open for the owner: (a) which registered cells enable the churn bound (A21(b): "enabled per registered cell"); (b) whether to accept a triple whose budget_k (E17's one 3-dispatch event) and window (E6's one 122.6 s gap) each rest on a single observation of n = 9 (§5.2).
3. **Floor selection for shield cells.** This batch used an install-wide swap, restored afterwards. Options:
   - (a) keep the swap as part of every shield-cell run line;
   - (b) make 0.20 the shipped default for all v3 S1 cells;
   - (c) build a per-run M4 config selector (needs a launch/fc_launch change, which touches pinned files).
4. **P3 has no live evidence.** The de-exemption and B3 were armed in every episode, but no shielded robot came near its yielder (closest 0.75 m). Should the shield's safety claim rest on the E18 replay fixture, or wait for a live exercise?
5. **Admitted is not productive.** E21 and E22 each had an admitted yield (one clearance, one hold timer) that the predicate scored unproductive: no robot of the cluster made credited progress in the window. This is recorded, not ruled; it bears on reading admit rates as resolution.
6. **Budget rule.** The agent-chosen $0.05 episode cap cut E23 at 200.5 sim-s. Its productive event came first, so the bar is unaffected. The batch spent $0.1069 of the $0.15 cap.

---

## References

- **Rulings:** prereg-v3 A27 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Previous wave:** `docs/reports/2026-10-12-shield-and-batch3.md`.
- **Code:**
  - `reasoning/rag/retreat_shield.py`, `reasoning/rag/plan_metrics.py`;
  - `ros2_ws/src/swarm_execution/swarm_execution/{safety,fresh_latch,nav2_adapter,command_bus_node}.py`;
  - `config/safety/safety_floor020.yaml`;
  - `scripts/s1b_live_batch_stats.py`.
- **Tests:** `tests/unit/test_a27_shield_fix.py`, `tests/unit/data/a27_shield_fix/`.
- **Kits** (gitignored):
  - `data/logs/vm_runs/a27/` (suite evidence, `kit/extract_e18.py`, `kit/extract_b3_parity.py`, `kit/floor_check.py`, `kit/gt_contacts.py`, `floor_check.json`, `gt_contacts_live15.json`);
  - `data/logs/vm_runs/batch4/` (`p8/` deploy, gen, build, overlay, chain, cost watch and restore scripts; `mc_seeds_21_23.*`, `aggregate_b4.py`, `b4_extras.py`, `derive_triple.py`, `agg_b4.json`, `triple_derivation.json`, `triple_3_130_0.json`, the bundles).
