# The A30 Escort-Filter Mini-batch E24-E26

**Prepared:** 2026-10-17

**Revision history:**

- Initial draft: the A30 switch-on overlay built offline (grounding file, seeds 24-26, overlays, VM kit p9); mini-batch E24-E26 PRE-REGISTERED before any live call (§1). Results follow in later sections.
- Rev 2 (2026-10-19): §2-§9 added after the live run on the zone-moved VM clone: summary, deploy/build evidence (the §1 "to be filled" md5s), the E24-E26 episodes, P1-P4 scored (all PASS), Rev 7 aggregates, deviations, VM end state and owner rulings. §1 unchanged.
- Rev 3 (2026-10-20): §9.1 added, the offline switch-off re-ground of E24 `dfb33b91`, which answers the §9 item 3 measurement question; §1 unchanged.
- Rev 4 (2026-10-21): §9 owner rulings recorded (items 1, 3, 4 RULED as A32 R2, R1, R3) and the kit follow-ups for the next kit; §1 unchanged.

---

PILOT-ONLY, RECORD = 0.

---

## 1. Pre-registration (written and committed before any live call)

PILOT-ONLY, RECORD = 0. This block is frozen at commit time. Later sections may
only add to it, never edit it. Values marked "to be filled at deploy" are
measurements of the VM, not choices. They are entered in §3 and do not edit
this block.

### 1.1 Tree, deploy and condition

- **Tree:** `feat/v3-escort-live` @ `9a018ca` = integration `5fbec0f` (the merge of `feat/v3-filter-parity`, A29(i)) + one config commit:
  - `9a018ca` feat: `config/grounding/s1b_dynamic_shield_escort.yaml` (new) and `tests/unit/test_a30_escort_overlay.py` (3 tests). The runtime code at `9a018ca` is byte-identical to `5fbec0f`.
  - Runtime since the batch-4 runtime: A28(ii) candidate filtering (`6ce2b92`), then A29(i), one filtered selection for every reader (`5fbec0f`). Batch 4 ran `f2553f1`. `f2553f1` → `f6598e6` touched docs and tests only, so the pre-images below are taken at `f6598e6`.
- **Suite (at `9a018ca`, full testpaths, `--continue-on-collection-errors`):** 62 failed / 6815 passed / 153 skipped / 3 errors. That is A30's 62/6812/153/3 plus the 3 new overlay tests. The 65 failing ids are identical to the A27 reference list (`data/logs/vm_runs/a27/final_ids.txt`). Evidence: `data/logs/vm_runs/batch5/suite/`.
- **The escort leg.** A28(ii) said "the escort leg of the shield config stays OFF", and A30 lifts that. **No config switch for it exists.**
  - `s1b_dynamic_shield.yaml` (ee5fe68f) has no escort on/off key.
  - Its escort keys (`escort_clearance_m`, `escort_band_m`, `escort_turn_cap`) were live in batches 3 and 4. Escorts ran: E23 `9803bd34` `escort_m=2.35`, `escort complete: moved 2.353 m`.
  - The only A28 control is `GroundingParams.escort_park_clearance`. It defaults to False and is absent from the pinned file.
  - The "OFF" was therefore a ruling only, and re-enabling it adds exactly one key. No other key was invented.
- **New grounding overlay** `config/grounding/s1b_dynamic_shield_escort.yaml`, md5 **40968886** (`409688866d25289309e081dcb9433037`):
  - It equals `s1b_dynamic_shield.yaml` key for key, plus `escort_park_clearance: true`.
  - Through the real `load_grounding_source` it gives: mode derived, `retreat_shield` True, margin 0.05, `retreat_fast_fail` True, `escort_park_clearance` True, `dynamic_scene_arms` True.
  - With the switch reset to its default, the params equal the shield file's params exactly (tested).
- **Pinned files unchanged:** `s1b_dynamic_shield.yaml` ee5fe68f, `s1b_dynamic.yaml` 535f5281, `rag.yaml` e18c723c, VM `orchestrator.yaml` 1f656533 (src and installed), `fc_launch.sh` 5a5ee4ac, `safety.yaml` 59839662 (pristine; swapped per run), VM `mapd_5_s1b.yaml` 728e58df.
- **Deploy** (`p9/deploy_p9.sh`, `p9/manifest_p9.txt`, `p9/delta_p9.tar` md5 0d1ad655 = `git archive 9a018ca` of exactly these 10 files). `p9/mac_build_delta_p9.sh` checks that the list equals the code diff `f6598e6..5fbec0f`. Pre-images are at `f6598e6`.

| File | Layer | Pre (f6598e6) | Source md5 (9a018ca) | Installed md5 |
|---|---|---|---|---|
| `reasoning/rag/command_grounder.py` | M3, live mount `/ws` | 3436f10c | a4e8b5a8 | to be filled at deploy |
| `reasoning/rag/escort_clearance.py` | M3, live mount (NEW) | — | 50766aeb | to be filled at deploy |
| `reasoning/rag/grounding_view.py` | M3, live mount | d35d93a0 | e152fc74 | to be filled at deploy |
| `reasoning/rag/maneuver_geometry.py` | M3, live mount | bd78ceea | 8923c35c | to be filled at deploy |
| `reasoning/rag/retreat_candidates.py` | M3, live mount | 9c2bc8ac | 76f6b8d8 | to be filled at deploy |
| `config/grounding/s1b_dynamic_shield_escort.yaml` | M3 config, live mount (NEW) | — | 40968886 | to be filled at deploy |
| `swarm_orchestrator/models.py` | M5, colcon | 62424f8e | a76e3c00 | to be filled at deploy |
| `swarm_orchestrator/reasoning_pipeline.py` | M5, colcon | fbf18d2d | 39a51bfc | to be filled at deploy |
| `swarm_orchestrator/retreat_stage2.py` | M5, colcon | b12231af | 0bd96495 | to be filled at deploy |
| `swarm_orchestrator/shadow_classical.py` | M5, colcon | 507888dc | 1de9588a | to be filled at deploy |
| `swarm_execution` src + installed `safety.yaml` (`p9/floor_p9.sh`) | M4 config, colcon | pristine 59839662 | **c41913f0** (= `config/safety/safety_floor020.yaml`) | to be filled at deploy |

  - M4 code is unchanged. Its A27 pins stay: `safety.py` c6c9cbae, `fresh_latch.py` 08d996a8, `nav2_adapter.py` f139305c, `command_bus_node.py` caad9edc.
  - M5 `orchestrator_node.py` f149ecff and `task_stream.py` 6e67c9ae are unchanged, but are reinstalled by the `swarm_orchestrator` rebuild.
  - The `/ws` files `retreat_shield.py` db0b6415 and `plan_metrics.py` 9d3c1487 are unchanged.
  - `swarm_orchestrator` build/ and install are purged (trap 17), followed by one colcon build. The script then checks INSTALLED == manifest and PACKAGE SRC == INSTALLED.
  - The installed `orchestrator.yaml` must stay 1f656533. Git's `5fbec0f` copy is 677a4cd0 and is not in the tar.
  - The in-container smoke test loads `prepare_filtered_retreat_selection`, `filter_escort_park_candidates` and `escort_clearance`, and parses the new file with the flags above. The two pinned files must keep the switch False.
- **Condition:** rule 16 verbatim, with three exceptions: the runtime tree (A28(ii) + A29(i)), the grounding file (the new overlay), and the labels. Rule 16 is: gemini-robotics-er-2-preview, plan channel on, suppression + `refusal_no_action` + `backend_failed` arming, churn bound OFF, Δ 2.5, H 600, REC_SEC 4800, NAV2_ACTIVE_TIMEOUT_SEC 360, `NAV2_BRINGUP_MODE=sequential`, MAX_ANALYSES 40, and the 0.20 m floor installed (A28(i), mandatory in every S1b live cell).

### 1.2 Seeds, scenarios and overlays

| Episode | Seed (`config/s1_seeds.yaml` position) | Scenario yaml | Header source `hdr_a20_seed{k}` | USD (newer than yaml) | Overlay `s1b_shield_escort_orch_seed{k}.yaml` | Unshielded base | Spawns (= draws) |
|---|---|---|---|---|---|---|---|
| E24 | 1151798991 (24) | 03b7ac06 | 380ce501 | to be filled at build | c6599fb1 | af403385 | r1 Wm, r2 N, r3 S, r4 E, r5 Wp |
| E25 | 1556492460 (25) | b72efe45 | d0345a52 | to be filled at build | ccf6bbac | 72d24823 | r1 Wp, r2 Wm, r3 S, r4 E, r5 N |
| E26 | 387918679 (26) | 167ce05d | 019218b1 | to be filled at build | 86a925bc | 5d679b3a | r1 E, r2 Wp, r3 Wm, r4 S, r5 N |

- **Procedure** (`p9/mac_gen_ov_p9.sh`, log `p9/mac_gen_ov_p9.log`): the p4/p8 procedure exactly.
  - Scenario yamls come from `gen_s7.py` (638524a2) on VM `mapd_5_s1b.yaml` 728e58df (= git `629dd3b`).
  - Header sources come from `gen_s7.py` on `mapd_5_s1b_hdr_d7dae79.yaml` (3d2659b6).
  - Overlays = `build_overlay.py` (82815cfa) on pin 1f656533 + `hdr_a20_seed{k}`, then one `sed` of `grounding_params_path` → `config/grounding/s1b_dynamic_shield_escort.yaml`.
- **Reproduction checks:** the same Mac procedure byte-reproduces batch 4's seed-22/23 scenario yamls (ccb674e8 / ea69ed93), header sources (8945458f / a470e788) and shield overlays (d79d04a0 / e6f4ddbd), and it byte-reproduces `s1b_orch_seed6.yaml` (00c02245).
- **Verification:**
  - Header sources are non-comment-equal to their scenario yamls, and the yaml seeds equal the list.
  - Each overlay differs from its unshielded base in exactly the `grounding_params_path` line (2 diff lines). The bases differ from seed 6 by 14 / 12 / 14 lines (initial_tasks, start_nodes, task_stream.seed).
  - All three parse through `load_config` + `load_grounding_source` as: seed, junction [NW, SW, N, S], plan / supp / rna True, churn off, H 600, shield True 0.05, fast-fail True, dyn True, escort_park True.
- **On the VM**, `p9/gen_s24_26.sh` and `p9/ov_s24_26.sh` redo the generation and must byte-equal the Mac kit (they print `VM == MAC`). `p9/build_s24_26.sh` builds the three USDs as root in one SimulationApp; usd_check spawns must equal the draws, and validate seed 24 must return rc 0.
- **MC (echo, upper bound; `batch5/mc_seeds_24_26.py`, `.jsonl`).** The batch-4 pattern, grounded three ways per first conflict:
  - **pinned** = the batch-4 grounder verbatim (`s1b_dynamic.yaml`, no goal references);
  - **nofilter** = the new file with the switch forced off, plus goal references = snapshot goals;
  - **escort** = the new file as deployed, with the same goal references. The shield is inert in MC because there are no task intents.

| Seed | First conflict | Echo pair | pinned | nofilter (escort leg clearance) | escort (escort leg clearance; filter tags) |
|---|---|---|---|---|---|
| 24 | r1+r3 at 21.5 s | [r1, r3] | EXECUTABLE yield r1 | EXECUTABLE yield r1, **no escort leg** | EXECUTABLE yield r1, no escort leg; no tag |
| 25 | r1+r5 at 10.6 s | [r1, r5] | EXECUTABLE yield r1 | EXECUTABLE yield r1, leg r5 0.954 m | EXECUTABLE yield r1, leg r5 0.954 m; `escort_park_filtered:A:robot_5:0.126` (a non-default candidate dropped) |
| 26 | r2+r3 at 12.0 s | [r2, r3] | EXECUTABLE yield r2 | EXECUTABLE yield r2, leg r3 **0.179 m** (E20 class) | EXECUTABLE yield r2, leg r3 0.541 m; `escort_park_filtered:B:robot_3:0.179` (the default pick dropped, survivor grounds) |

  - MC upper bound on first-conflict yields: 3/3. The filter changes the dispatched pose on s26 only.
  - In MC the filter tag fires on 2 of 3 first conflicts (s25, s26).
  - Without the filter, s26's echo yield would park r2 0.179 m off its passer's escort line.

### 1.3 Run protocol and budget

- **Order:** episodes E24, E25, E26, via `p9/chain_p9.sh`. It is `chain_p8.sh` verbatim except for:
  - P9 paths, seeds 24-26;
  - labels `s1b_E{k}_seed{k}_er2_f{a}` (f = batch 5);
  - the cost-log glob `_er2_f*`, so batch 4's `_e` logs do not count;
  - the A28/A29 pins (M3 `/ws`, M5 installed, the escort yaml) plus the A27 pins and the installed floor in the between-episode pin gate;
  - the post-episode floor gate on `m4.log` (`hard_contact_floor_m=0.2`), unchanged;
  - a NEW post-episode condition gate, `p9/cond_p9.py`. Every decision artifact's `grounding_params_source.params` must carry `escort_park_clearance`, `retreat_shield` and `retreat_fast_fail` True, or the chain stops. The same line logs the live `escort_park_filtered` counts.
- **Bring-up aborts:** up to 3 attempts per episode. Two consecutive episodes with 3 aborts each stop the batch.
- **Budget (VM-enforced, the A25 reserve-one-call rule):**
  - Batch cap **$0.15 HARD**, summed over this batch's `_f` cost logs only.
  - An episode starts only if remaining ≥ **$0.04** (start floor).
  - Episode cap = **min($0.05, remaining)**.
  - `cost_watch.py` (= p8, 5 s poll) touches the Isaac stop flag once est + $0.008 (one call) reaches the episode cap.
  - est is a lower bound: a timed-out stage-2 call records no usage.
  - If an episode would breach the cap or the start gate, it is not run, and that is reported. No episode is added after seeing data.
- **VM procedure (in this order; every step's sentinel line must print before the next step):**
  1. **Start** the VM (`vgu-vgu-thu-base-isaac-workstation-vm`, project-5b0644ea-c6bd-4d13-a4a, asia-southeast1-b). Copy the kit to `~/v3_s1b/p9`. Never use `rsync --delete` (trap).
  2. **Pins check:** `sudo bash pins_pre_p9.sh` → `PINS_PRE OK`. This is the batch-4 end state: A27 pin line, pristine `safety.yaml`, no NEW files present.
  3. **Scenarios:** `bash gen_s24_26.sh` → `VM == MAC`, then `sudo bash build_s24_26.sh` → USDs newer, usd_check spawns = draws, validate rc 0.
  4. **Deploy:** `sudo bash deploy_p9.sh` → `PRE-IMAGE MD5 OK`, `SOURCE MD5 OK`, `LIVE MOUNT MD5 OK`, colcon rc 0, `INSTALLED MD5 OK`, `PACKAGE SRC==INSTALLED OK`, `ORCH PIN OK`, and the SMOKE line with escort_park True on the new file and False on both pinned files.
  5. **Floor swap:** `sudo bash floor_p9.sh` → `PRISTINE BACKUP OK`, `FLOOR INSTALLED OK`, and the SMOKE line with floor 0.2 and shield pair not exempt.
  6. **Gates:** `bash ov_s24_26.sh` → `PROCEDURE REPRODUCES s1b_orch_seed6.yaml`, `VM == MAC`, and three parse lines with escort_park True. The chain's own pin gate runs before every episode, and the floor gate and condition gate after every episode.
  7. **Chain:** `bash chain_p9.sh` as ubuntu (nohup) → `CHAIN_P9 DONE`.
  8. **Restore:** `sudo bash restore_safety_p9.sh` → `RESTORE PRISTINE OK`. The A28/A29 M3/M5 runtime stays deployed. It is inert without the overlay, because the switch defaults off.
  9. **Close-out:** re-run `pins_pre_p9.sh`. It now expects the A30 pin line (record it rather than gate on it). Pull the bundles plus `p9/` to `data/logs/vm_runs/batch5/`, and chown.
  10. **Stop** the VM (A30: "VM must be started for this batch and STOPPED after it").

### 1.4 Predictions (scoreable)

- **P1 (the escort clears the park point).** Every dispatched yield's escort legs clear its park point by ≥ 0.45 m.
  - Method: `escort_clearance.escort_legs(yielder, dispatched parameters, decision snapshot, the decision's dynamic grounding view)`, run on every dispatched command (`batch5/score_p9.py`).
  - The scorer was validated on the batch-3/4 bundles: it reproduces E21 `04457772` 0.558, E23 `9803bd34` 0.896, E20 `6cf402ed` 0.131 and `f269ab37` 0.447 m (`batch5/score_p9_validation_batch4.jsonl`).
  - A yield with no escort leg (MC s24) is reported **vacuous**, not a pass.
  - Any leg < 0.45 m is a P1 FAILURE.
  - Scope: the command at decision time. Dispatch-time drift (the E18 class) belongs to P2.
- **P2 (no contact; the floor is quiet).** Zero GT contacts and zero floor firings.
  - Contact: no robot pair, at any time in any episode, comes below **0.18 m** centre distance, by an all-pairs scan of GT positions (`gt/ground_truth.jsonl`, the `a27/kit/gt_contacts.py` scan; the GT contacts field is a stub, trap 20).
  - Floor firings: zero `m4.log` `safety stop robot=… reason=hard_contact_floor` lines.
  - A30 predicts zero floor firings, so any firing FAILS P2 (stricter than batch 4's P2). It is reported with its pair, GT minimum and closing speed.
  - Per episode, the all-pairs GT minimum is reported. So is the minimum GT distance between each escorted passer and its parked yielder.
- **P3 (the filter fires live).** At least one `retreat=escort_park_filtered:<label>:<passer>:<m>` tag fires live.
  - Scope: the tag in ANY decision artifact's `grounding_degradations` in E24-E26, dispatched or withheld. The dispatched subset is reported beside it.
  - `yield=infeasible:escort_hits_park` tags (filter emptied the set → reroute) are counted separately and do not satisfy P3.
  - MC predicts tags on the s25 and s26 first conflicts. The live model need not choose the echo pair, so P3 can fail honestly.
  - Untestable (reported as such) only if no episode produces a single grounded yield decision.
- **P4 (admits stay at batch 4's rate).** Batch 4 admitted 3/3, so **the bar is admitted == dispatched (rate 1.0)** over E24-E26.
  - Admitted = an `m4.log` `crossing_chain gate_admit command=<id>-yield` line.
  - A yield failed by B3 or by any deadline counts as NOT admitted.
  - A yield the filter turns into a reroute (`escort_hits_park`) is not a dispatched yield, and neither is a withheld one.
  - One un-admitted dispatched yield FAILS P4.
  - Untestable (reported as such) if no yield is dispatched.

### 1.5 Capture and aggregates

- **Per episode:** the rule-16 bundle and capture schema, pulled to `data/logs/vm_runs/batch5/`, plus:
  - `cond_p9.py`'s COND line;
  - `score_p9.py`'s per-yield legs and P1 verdicts;
  - per filter tag: the dropped label, the passer and the clearance, plus the dispatched `retreat_choice` (a post-filter letter; A29(iii): replay letters map through `escort_park_filtered`);
  - all-pairs GT minimum, floor and B3 firings, shield events, and per-episode spend.
- **Rev 7 aggregates over all live episodes:** `batch4/aggregate_b4.py` + the f-labels + MC 24-26, required to reproduce `agg_b4.json` block-for-block on the prior 18 live bundles.
  - Admitted/dispatched, pooled and A26+ runtime.
  - Clearance releases.
  - First-conflict yield vs MC (Clopper-Pearson 95 %).
  - Alternations / livelock.
  - vb∧matched, raw and shield-excluded.
  - The churn triple stays REGISTERED and DEFAULT-OFF (A29). It is not re-derived here.

### 1.6 Known before the batch (disclosed, not tuned on)

- **Recorded cost (A28(ii)):** the filter still vetoes E20 `f269ab37`, E17a/b and the declared head-on, because no candidate clears 0.45 m there. Those yields reroute and are then withheld by `refusal_no_action`. A live repeat-veto is therefore possible and would show up as `escort_hits_park` plus `empty_reroute` withholds, not as a yield.
- **A15(iv) asymmetry (A30 ruling):** the PARTNER side of a swap reads the filtered selection, but the KEPT-YIELDER trigger stays unfiltered. With the switch on, an S1 `sweep_regrounded_exec` case becomes a certified wait fan-out instead of a partner reroute.
- **Open, non-blocking (A29):** (ii) stage-2 records do not list dropped candidates (provenance is only in the degradations); (iii) replayed live letters denote post-filter poses; production shadow still grounds on declared geometry without goal references (the Arm B parity question).
- **MC caveat:** MC grounds the echo pair with snapshot goals as goal references and no task intents. The live shield and stage 2 can change the pick, so MC's leg clearances are not live predictions.

---

## 2. Summary of Results

**Status: the batch ran in full (E24, E25, E26) inside budget, on the zone-moved VM clone. All four pre-registered predictions PASS. The filter fired live once, on E24's dispatched yield. Every dispatched yield was admitted and released by clearance. There were no GT contacts, no floor firings and no B3 firings. All three episodes were cut by the $0.05 episode cap, between 133 and 174 sim-s of the 600 sim-s horizon.**

| Question | Answer |
|---|---|
| Host | `vgu-thu-base-isaac-vm-asia-northeast1-a` (asia-northeast1-a), the zone-moved snapshot clone of the batch-4 end-state disk. It runs the same image on a different physical host and zone. The cross-VM equivalence caveat is unchanged (§3.1) |
| Deploy | `PINS_PRE OK` with no drift. Every deploy, floor and overlay sentinel printed. Installed md5 = source md5 for all 10 manifest files plus the floor (§3.2) |
| Batch | 5 attempts: 2 sequential bring-up aborts at $0, then 3 episodes run. **Spend est. $0.1395 of $0.15** (E24 0.0488, E25 0.0470, E26 0.0437). Each episode was stopped by its cost-cap stop flag |
| P1 escort clears park ≥ 0.45 m | **PASS, 3/3 non-vacuous**: 0.575 / 1.730 / 1.036 m |
| P2 no contact, floor quiet | **PASS**: all-pairs GT minimum 0.404 / 0.338 / 0.323 m, no pair below 0.18 m, 0 floor firings |
| P3 filter fires live | **PASS**: 1 tag, `retreat=escort_park_filtered:A:robot_4:0.215` on E24 `dfb33b91`, which was dispatched. It fired on a cluster MC did not model. Neither MC-predicted tag (s25, s26) fired |
| P4 admitted == dispatched | **PASS, 3/3** |
| Rev 7 | Admitted/dispatched pooled **14/20**, and **11/11** on the A26+ runtime. First-conflict yield **6/21** live (CI 0.113-0.522) against MC 15/21. **0 alternations in 21 live episodes, NO LIVELOCK.** Productive nonzero 10/33 all-classified (live 9/21) |

PILOT-ONLY, RECORD = 0.

---

## 3. Deploy and Build Evidence (the §1 "to be filled" cells)

### 3.1 Host

- **The batch ran on the zone-moved clone, not the VM named in §1.3 step 1.**
  - §1.3 names `vgu-vgu-thu-base-isaac-workstation-vm` (asia-southeast1-b). That VM stayed TERMINATED and was not touched. An L4 stockout of about 57 h in asia-southeast1-b forced the move.
  - The batch ran on `vgu-thu-base-isaac-vm-asia-northeast1-a` (zone asia-northeast1-a, same project and account). That VM is built from snapshot `thu-base-snap-20261019` of the batch-4 end-state disk: L4, driver 595.91.07, g2-standard-8, ephemeral IP 34.104.242.245.
  - The owner authorized it (2026-10-17 run order; 2026-10-19 zone move). The VM was already RUNNING when the batch started. No cloud resource was created.
  - **Cross-VM equivalence caveat (unchanged):** this host has the same disk image as the batch-4 host, but different physical hardware and a different zone. The md5 pins in §3.2 establish software identity, not hardware identity.
- **No Mac-side helper in `p9/` hardcoded the old IP (35.198.230.72) or zone.** A grep over `p9/` and `batch5/*.py` matched only the prose runbook step 1 (line 41) in `NOTES_vm_b5.md`. No copies were made, and every VM-side script uses local paths only.
- The kit was copied with `rsync -a`, without `--delete`. The 24 files of `p9/` arrived with `delta_p9.tar` 0d1ad655 and `chain_p9.sh` cd58a53a, equal on the Mac and the VM.

### 3.2 Pins, scenarios, deploy and floor

- **Pins check (`pins_pre_p9.sh`): `PINS_PRE OK`, no drift.** All 26 pinned md5s and the 7 kit files matched. No NEW file was present, there were no leftover `_er2_f` run files, and the GPU was at 0 %.
- **Scenarios (`gen_s24_26.sh`):** seeds 24-26 NONCOMMENT_EQUAL, and `VM == MAC (scen + ovsrc, seeds 24-26)`. The yamls are 03b7ac06 / b72efe45 / 167ce05d and the headers 380ce501 / d0345a52 / 019218b1, as in §1.2.
- **Build (`build_s24_26.sh`, as root, one SimulationApp):** build rc 0. Every USD is newer than its yaml. `usd_check` spawns equal the draws for all three seeds, and validate seed 24 returned rc 0.

| Episode | Scenario yaml | USD md5 (newer than yaml) | Spawns (usd_check) |
|---|---|---|---|
| E24 | 03b7ac06 | **9f8a01d9** (`9f8a01d9d1987ad9674bcd6367f9ed1b`) | r1 (-2.30,-1.35) Wm, r2 (-0.25,1.35) N, r3 (-0.25,-1.35) S, r4 (2.30,0.00) E, r5 (-2.30,1.35) Wp |
| E25 | b72efe45 | **c4c97576** (`c4c975769443d32f083e5d7ff193d098`) | r1 Wp, r2 Wm, r3 S, r4 E, r5 N |
| E26 | 167ce05d | **8d6ff817** (`8d6ff8172df3de3a61ea3b47c5087cfe`) | r1 E, r2 Wp, r3 Wm, r4 S, r5 N |

- **Deploy (`deploy_p9.sh`):** `PRE-IMAGE MD5 OK`, `SOURCE MD5 OK`, `LIVE MOUNT MD5 OK`, colcon rc 0, `INSTALLED MD5 OK`, `PACKAGE SRC==INSTALLED OK`, `ORCH PIN OK` (1f656533 src and installed).
  - SMOKE line: `escort_file shield True 0.05 ff True escort_park True dyn True | shield_file escort_park False | s1b_dynamic escort_park False | same-but-switch True`.
- **Floor (`floor_p9.sh`):** `PRISTINE BACKUP OK`, `FLOOR INSTALLED OK`, and `hard_contact_floor_m: 0.20` installed.
  - A27 M4 pins: c6c9cbae / 08d996a8 / f139305c / caad9edc.
  - SMOKE line: `key True floor 0.2 passer_exempt True shield_exempt False`.
- **Overlays (`ov_s24_26.sh`):** `PROCEDURE REPRODUCES s1b_orch_seed6.yaml`, "(want 2): 2" for each of the three, and `VM == MAC (overlays, seeds 24-26)`.
  - Overlays: c6599fb1 / ccf6bbac / 86a925bc.
  - Three parse lines ending `shield True 0.05 ff True dyn True escort_park True H 600.0`.

| File | Source md5 (9a018ca) | **Installed md5 (measured)** |
|---|---|---|
| `reasoning/rag/command_grounder.py` (/ws) | a4e8b5a8 | a4e8b5a8 |
| `reasoning/rag/escort_clearance.py` (/ws, NEW) | 50766aeb | 50766aeb |
| `reasoning/rag/grounding_view.py` (/ws) | e152fc74 | e152fc74 |
| `reasoning/rag/maneuver_geometry.py` (/ws) | 8923c35c | 8923c35c |
| `reasoning/rag/retreat_candidates.py` (/ws) | 76f6b8d8 | 76f6b8d8 |
| `config/grounding/s1b_dynamic_shield_escort.yaml` (/ws, NEW) | 40968886 | 40968886 |
| `swarm_orchestrator/models.py` | a76e3c00 | a76e3c00 |
| `swarm_orchestrator/reasoning_pipeline.py` | 39a51bfc | 39a51bfc |
| `swarm_orchestrator/retreat_stage2.py` | 0bd96495 | 0bd96495 |
| `swarm_orchestrator/shadow_classical.py` | 1de9588a | 1de9588a |
| `swarm_execution` `safety.yaml` (src + installed) | c41913f0 | c41913f0 during the batch; restored to 59839662 (§8) |

- **The chain's pin gate passed before every attempt.** Both the A30 line and the A27 line were checked, the latter with installed `safety.yaml` c41913f0. The floor gate (`hard_contact_floor_m=0.2` safety-monitor startup line) and the condition gate (`switch_on = shield_on = artifacts = 6`, `ungrounded=0`) passed after every episode that ran.

---

## 4. Live Mini-batch E24-E26

| Episode | Attempts (stamp of run) | Sim-s reached (GT end) | Analyses: dispatched / withheld | Dispatched yield (VLM named → M3 dispatched) | Escort leg vs park (P1) | Admit → release (sim-s) | Filter tags | GT closest pair | Passer–parked-yielder GT min after admit | Floor / B3 | Tasks | Churn / productive | est $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E24 (seed 24) | f1 abort (robot_1 not active 120 s); **f2** 20261019_163801 | 137.3 (cost-cap stop) | 6: 2 / 2 refusal + 2 no-congestion | `dfb33b91`: VLM yield r4 → **yield r3 for passer r4** (`heading_regrounded`), post-filter `retreat_choice` B | r4 **0.575 m** | 106.4 → 128.2 **clearance** | **`A:robot_4:0.215`** (dispatched) | r3–r4 0.404 m (69.4) | 0.587 m | 0 / 0 | 6/25 | resolved / **1** | 0.0488 |
| E25 (seed 25) | f1 abort (robot_3 not active 120 s); **f2** 20261019_165623 | 173.8 (cost-cap stop) | 6: 3 / 3 refusal | `c1fd8b36`: VLM yield r5 → **yield r1 for passer r5** (`yield_robot=regrounded`, junction box N), `retreat_choice` A | r5 **1.730 m** | 74.2 → 88.8 **clearance** | none | r1–r5 0.338 m (45.0) | 1.736 m | 0 / 0 | 4/25 | resolved / **1** | 0.0470 |
| E26 (seed 26) | **f1** 20261019_171356 | 132.9 (cost-cap stop) | 6: 3 / 3 refusal | `cf77ca65`: VLM yield r1 → **yield r5 for passer r1** (`heading_regrounded`), single candidate (`retreat=default:no_choice`) | r1 **1.036 m** | 98.1 → 109.2 **clearance** | none | r2–r3 0.323 m (43.4) | 0.433 m (re-latch at end) | 0 / 0 | 1/25 | clogged / 0 | 0.0437 |

- **E24:**
  - The first analysis (45.9 sim-s) named r1+r5 and dispatched a `temporary_wait` on both. The live first latch was r1+r5 at 14.8 rel-s. MC's first conflict was r1+r3 at 21.5 s with an echo yield r1, so this is not a first-conflict yield.
  - Two follow-up yields on {r1, r5} were refused ("no shared lane … 88 deg across") and withheld.
  - The 4th analysis (71.2) named the second cluster {r3, r4} as yield r4. M3 regrounded the yielder to r3 (`heading_regrounded:robot_4->robot_3`) and capped r4's escort at 1.825 m (`escort_turn_cap:robot_4:2.35->1.825`).
  - **The filter dropped pre-filter candidate A, whose escort leg passed 0.215 m from its park point.** Stage 2's default was the post-filter B, the model chose B, and B was dispatched with a leg clearing the park point by 0.575 m.
  - What the dispatched pose would have been with the switch off was measured afterwards by an offline re-ground (§9.1). The post-filter letter B does not denote the same pose as the pre-filter label in the tag (A29(iii)).
  - The yield was admitted at 106.4, the escort completed (moved 1.826 m), and it was released by clearance at 128.2. The robots then made credited progress, so the event is **productive**. Two no-congestion analyses followed.
- **E25:**
  - The first analysis (43.2) named MC's pair, r1+r5. The VLM said yield r5; M3 regrounded it to **yield r1 for r5**, which is MC's echo yield.
  - Stage 2 chose letter B, which is label A (the default was label C). The leg cleared the park point by 1.730 m, against MC's 0.954 m. **The filter tag MC predicted (`A:robot_5:0.126`) did not fire live**, even though live had MC's pair and yielder at about the same episode time. The live decision was about 13.7 rel-s (43.2 absolute, minus E25's GT offset of about 29.5 s), against MC's 10.6 s encounter plus 2.5 s.
  - Observed differences: the live grounding ran through the dynamic crossing view (`dynamic_arms:crossing`, `junction_box:N`) with a 1.169 m escort, against MC's 1.95 m escort leg. MC records no grounding-view tags, so the cause is **not isolated** (the §1.6 MC caveat).
  - The yield was admitted at 74.2, the escort completed (1.177 m), and it was released by clearance at 88.8. **Productive.** This is the batch's only first-conflict yield.
  - The {r2, r3, r4} cluster (later with r1) drew three `junction_clear` analyses, each refused ("no feasible yielder", retreat room < 0) and withheld. It also drew two `reverse` analyses, dispatched as `temporary_wait` fan-outs. Suppression held the scene for 25 suppressed re-analyses.
- **E26:**
  - The first analysis (45.5) named r2+r3, which is MC's pair, as `reverse`. It was dispatched as `temporary_wait` on both, not a yield. MC predicted an executable yield r2 here, with the filter dropping the default pick B (0.179 m).
  - `f36969f3` (58.4) was a `junction_clear` naming both clusters. It was refused and withheld.
  - `cf77ca65` (67.8) named yield r1 for r5. M3 regrounded it to **yield r5 for passer r1** and capped r1's escort at 0.817 m. There was one candidate, so stage 2 was skipped. The leg cleared by 1.036 m.
  - The yield was admitted at 98.1, the escort completed (0.819 m), and it was released by clearance at 109.2.
  - **r1 and r5 then re-latched about 3 sim-s after the release**, at 0.433 m GT, and stayed latched to the end (no contact). The predicate scores the event unproductive. **That reading is censored by budget:** the cost cap ended the episode 23.7 sim-s after the release.
- **Shield:** armed on every artifact (`retreat_shield` and `retreat_fast_fail` True), but it placed **no hold**. There are 0 `retreat_shield_hold` keys in any dispatched command and 0 shield lines in `m4.log`. No A19 latch waiver was armed.
- **Bring-up:** 5 attempts, 2 sequential aborts. E24 f1 had robot_1 not active 120 s after launch; E25 f1 had robot_3. Both cost $0, ended `GATE OK` / `RESTORE OK`, and had their Isaac exit before the retry (idle gate 0 s). No run attempt shows a "jump back in time" line. Pooled sequential aborts go from 1/21 to **3/26**.
- **Budget:** the $0.04 start floor was met before every episode (spent $0 / $0.0488 / $0.0958). Each episode's `cost_watch` touched the stop flag once est. + $0.008 reached the $0.05 cap, at est. 0.0488 / 0.0470 / 0.0437. **Batch est. $0.1395 of $0.15.** The estimate is a lower bound, because a timed-out stage-2 call records no usage.

---

## 5. Predictions Scored (against §1.4)

| Prediction | Bar (§1.4) | Result | Evidence |
|---|---|---|---|
| P1 escort clears park | every dispatched yield's legs ≥ 0.45 m; a yield with no leg is vacuous | **PASS, 3/3 non-vacuous** (0.575, 1.730, 1.036 m) | `batch5/score_p9_results.jsonl` (`score_p9.py`, the scorer validated in §1.4) |
| P2 no contact, floor quiet | 0 GT pairs < 0.18 m (all pairs) AND 0 floor firings | **PASS** | `batch5/gt_contacts_b5.json`: minima 0.404 / 0.338 / 0.323 m, `contacts_below_018` empty. 0 `reason=hard_contact_floor` lines. Passer–yielder minima after admit 0.587 / 1.736 / 0.433 m |
| P3 filter fires live | ≥ 1 `retreat=escort_park_filtered:` tag in any artifact | **PASS, 1 tag (1 dispatched)**: E24 `dfb33b91` `A:robot_4:0.215` | 0 `yield=infeasible:escort_hits_park`. MC predicted tags on s25/s26; neither fired. s25 had the same pair and yielder at about the same time, with the cause not isolated (§4). On s26 the first analysis on MC's pair was a `reverse` dispatched as waits. The tag fired on the s24 second cluster, which MC did not model |
| P4 admits | admitted == dispatched | **PASS, 3/3** | `gate_admit` on `dfb33b91`, `c1fd8b36`, `cf77ca65`; 0 B3 firings, no yield failed |

The condition held on every artifact: COND `switch_on = shield_on = 6` in each episode, `ungrounded=0`.

---

## 6. Rev 7 Aggregates (All Live Episodes E6-E26)

Output: `batch5/agg_b5.json` (`aggregate_b5.py` over `batch5/live21.txt`), plus per-episode `batch5/stats_E2{4,5,6}.json` (`s1b_live_batch_stats.py`).

- **Reproduction gate:** `aggregate_b5.py` on batch 4's 18 bundles (`agg_b5_prior18.json`) equals `batch4/agg_b4.json` **block for block**. All 7 top-level blocks are EQUAL.

| Aggregate | Rev 6 (E6-E23) | **Rev 7 (E6-E26)** |
|---|---|---|
| Admitted / dispatched live yields | 11/17 pooled; A26+A27 runtime 8/8 | **14/20 pooled**: E6-E17 3/9, batch 3 5/5, batch 4 3/3, batch 5 3/3. **A26+ runtime 11/11** |
| Clearance releases | E6, E20 `f269ab37`, E21, E23 (+ E20 `6cf402ed`, a contact push) | **+3 in batch 5** (E24 `dfb33b91`, E25 `c1fd8b36`, E26 `cf77ca65`): 7 clearance releases + the one contact push |
| (a) Attribution | NO LIVELOCK, 5 opportunity / 0 ARCH, 0 alternations in 18 | **NO LIVELOCK**, 5 opportunity / 0 ARCH, **0 alternations in 21**. Batch 5 never reached the opportunity bar (max 1 clearing dispatch into one cluster) |
| Churn class (batch) | E21 clogged, E22 clogged, E23 resolved | E24 **resolved**, E25 **resolved**, E26 clogged |
| (b) Productive | all classified n = 30, 8 nonzero, p95 1; live 7/18, p95 2 | **n = 33, 10 nonzero, p95 1; live 9/21, p95 1** (nearest-rank moves from rank 18 of 18 to rank 20 of 21, so the single 2-event episode leaves the p95 rank; not a substantive drop). Events n = 11 (+E24, +E25); dispatches into the group sorted 1×7, 2×3, 3 → p95 **3**; dispatch → progress adds 56.9 / 63.1 s, p95 79.3 s |
| (c) First-conflict yield | 5/18 live, CI 0.097-0.535, vs MC 12/18 | **6/21 live (+E25), Clopper-Pearson 0.113-0.522, vs MC 15/21.** Batch 5 alone 1/3 against MC 3/3: s24 first analysis a wait on another pair; s26 first analysis `reverse` on MC's pair, dispatched as waits |
| (d) Both clusters | named 14/103; dispatched 7/103 | **named 15/121** (+E26 `f36969f3`, withheld); both-cluster plan dispatched 7/121 |
| (e) Wandering vs park | no finisher in batch 4 | no finisher in batch 5; still undecided |
| vb∧matched (A27(iv)) | 16 shield-excluded / 13 raw | **17 / 14** (E24 1 / 1; E25, E26 0 / 0) |
| (f) Cost | batch 4 $0.1069; all-live $0.7546 over 18 | **batch 5 $0.1395**; all-live **$0.8941 over 21**, median $0.0405, range 0.0174-0.0954. `agg_b5.json`'s `total_excl_E6` is $0.8606 |

- **budget_k triple:** not re-derived (A29: registered, default-off). For the record, the two new productive events (one dispatch each) cross no rank boundary. Dispatches-into-group p95 stays 3, latency p95 stays 79.3 s, and neither group is multi-dispatch, so no new inter-dispatch gap enters the window.

---

## 7. Deviations and Notes

- **Host (§1.3 step 1):** the batch ran on the zone-moved clone, not the named VM (§3.1). It was owner-authorized, and nothing else in the procedure changed.
- **Close-out pins check:** re-running `pins_pre_p9.sh` after the batch printed `PINS_PRE FAILED` **by design**, as `NOTES_vm_b5.md` says. It reported:
  - the 8 deployed M3/M5 files at their A30 md5s;
  - `s1b_dynamic_shield_escort.yaml` and `escort_clearance.py` present;
  - the batch's `_er2_f` run files present.

  Every other pin was ok (orchestrator.yaml 1f656533 src and installed, rag e18c723c, safety.yaml 59839662 after the restore). Recorded in `p9_vm/pins_post_p9.log`; it does not gate anything.
- **Runbook NOTES:** the VM log was appended twice, pre-chain and close-out, under `## Log`. The Mac kit copy `batch5/p9/NOTES_vm_b5.md` is the original. The VM copy is `batch5/p9_vm/NOTES_vm_b5.md`, also copied to `batch5/NOTES_vm_b5.md`.
- **Scorer path:** `score_p9.py` matches admits on the full command id against `m4.log`. All three dispatched yields matched.
- No corrections to earlier batches.

---

## 8. VM End State and Pins

- **Processes at close:** no `run_simulation`, Kit, `fc_launch`, `ep_run`, chain or watcher process. `vgu_ros` was up (restarted by the last `fc_launch` cleanup) and idle, running `sleep infinity` only. GPU 0 %, 155 MiB. `data/logs/simulation` was empty.
- **Ownership:** 5 root-owned `reasoning/rag/__pycache__/*.pyc` files (the deploy smoke) were chowned to ubuntu. `~/v3_s1b`, `m5_decisions` and `m5_scene` were chowned too.
- **`safety.yaml` restored:** `restore_safety_p9.sh` → `RESTORE PRISTINE OK`, src and installed **59839662**. The A28/A29 M3/M5 runtime stays deployed. It is inert without the escort overlay, because the switch defaults to off.
- **Pin line at close (A30):** command_grounder a4e8b5a8, escort_clearance 50766aeb, grounding_view e152fc74, maneuver_geometry 8923c35c, retreat_candidates 76f6b8d8, models a76e3c00, reasoning_pipeline 39a51bfc, retreat_stage2 0bd96495, shadow_classical 1de9588a.
  - Unchanged: orchestrator.yaml 1f656533 (src and installed), rag e18c723c, s1b_dynamic 535f5281, s1b_dynamic_shield ee5fe68f, fc_launch 5a5ee4ac, A27 M4 c6c9cbae / 08d996a8 / f139305c / caad9edc.
  - Staged: seed 24/25/26 yamls 03b7ac06 / b72efe45 / 167ce05d, USDs 9f8a01d9 / c4c97576 / 8d6ff817, overlays c6599fb1 / ccf6bbac / 86a925bc.
- **Bundles** are pulled to `data/logs/vm_runs/batch5/` (gitignored; 246 files, equal counts on the VM and the Mac):
  - 5 attempt directories `s1b_E2{4,5,6}_seed*_er2_f*`, including the two aborts, each with `.cost` / `.outer` / `.pin` / `.watch` logs;
  - the VM's `p9/` in `batch5/p9_vm/` (the Mac kit `batch5/p9/` is untouched): `chain_p9.log`, `attempts.tsv`, the deploy, floor, overlay, build and restore logs, `pins_pre_p9.log`, `pins_post_p9.log`.
- **The VM is STOPPED:** `gcloud compute instances stop` on `vgu-thu-base-isaac-vm-asia-northeast1-a`, then STATUS `TERMINATED`. The old asia-southeast1-b VM was untouched and is TERMINATED.

---

## 9. Owner Rulings Needed

**Rulings (owner, 2026-10-21; prereg-v3 A32).** Item 1 RULED (R2): episode cap $0.05 → $0.10 for confirmatory runs; batch cap and start floor set per cell in the kit. Item 3 RULED (R1): `escort_park_clearance` ON in shield cells via `config/grounding/s1b_dynamic_shield_escort.yaml` (40968886) as the registered shield config, OFF elsewhere. Item 4 RULED (R3): per-robot active timeout 120 → 180 s, landed in `scripts/vm/fc_launch.sh` (`NAV2_STACK_ACTIVE_TIMEOUT_SEC` default, `d975f13`). The A29(ii) stage-2 record gap is closed (R5, `6abea45`). Items 2 and 5 stay recorded, not ruled.

**Kit changes for the next kit (follow-ups).**

- R2: set the episode cap to $0.10 (was $0.05) and set the batch cap and start floor per cell.
- R3: keep `NAV2_BRINGUP_MODE=sequential` (the 180 s applies only there) and leave `NAV2_STACK_ACTIVE_TIMEOUT_SEC` unset so the new default applies, or set it to 180. The p9 chain sets the mode and not the variable, so it needs no edit for this.
- R1: point the shield cells' grounding source at `s1b_dynamic_shield_escort.yaml` and check its md5 is 40968886 in the pre-flight pins.
- Deploy `feat/v3-s1b-freeze` before the first confirmatory cell: `reasoning/rag/command_grounder.py` (live-mounted M3), `swarm_orchestrator/models.py` and `retreat_stage2.py` (colcon-built: rebuild `swarm_orchestrator`, then md5 source against install) and `scripts/vm/fc_launch.sh`. The VM still carries the A28/A29 runtime, which has neither R3 nor R5.

1. **Episode cap.** All three episodes were cut by the $0.05 cap, at 137 / 174 / 133 sim-s of H 600, with 6 analyses each. E26's yield was released 23.7 sim-s before the cut, so its "unproductive" score is censored by budget. Options: raise the episode cap for the next live cells, or accept cap-censored productive scoring. **RULED 2026-10-21 (R2): cap raised to $0.10 (kit change).**
2. **Admitted is still not productive (E26).** The escorted passer and its parked yielder re-latched at 0.433 m (no contact) about 3 sim-s after a clearance release and stayed latched to the end. This is the second admitted, unproductive pattern after batch 4's E21 and E22. Recorded, not ruled.
3. **What the filter changed (measured 2026-10-20, §9.1).** The filter dropped a non-default candidate, pre-filter A at 0.215 m (geometry rank 1). The switch-off default is the dispatched pose, so the filter did not change the default pick. It did change what stage 2 offered (4 → 3 marks, re-lettered). Whether the model would have picked the 0.215 m pose with the switch off cannot be replayed offline. MC's two predicted firings (s25, s26) did not occur live. E25 had the same pair and yielder at about the same time but grounded a different escort (1.169 m vs 1.95 m; cause not isolated). E26's first conflict got a `reverse`. Should `escort_park_clearance` become the default in shield cells (n = 1 live firing)? **RULED 2026-10-21 (R1): yes, ON in shield cells only, via the escort overlay.**
4. **Sequential bring-up aborts on the new host:** 2 of 5 attempts (robot_1, then robot_3, not active 120 s after launch), against 1 of 21 before. Pooled 3/26. Both retries succeeded. Whether to watch this as a host effect, or lengthen the per-robot active timeout, is the owner's call. **RULED 2026-10-21 (R3): timeout lengthened to 180 s (`d975f13`).**
5. **Shield and B3 are still unexercised live.** The shield was armed in all 18 artifacts but placed no hold, and B3 never fired. Batch 4's §8 item 4 stands.

### 9.1 E24 `dfb33b91` Re-grounded With the Switch Off (2026-10-20)

**Method.** The recorded grounding inputs of `dfb33b91` were replayed through the deployed runtime (`9a018ca`), once with the artifact's params and once with only `escort_park_clearance` set False:

- the inputs are the decision, the scene snapshot, `grounding_params_source.params`, the bundle's `orchestrator.overlaid.yaml` (geometry, obstacles, gate mode `swap`, registry priorities), and the stage-2 `letter_seed_base` and `letter_draw_index` 2;
- goal references and task intents come from the bundle's `tasks_*.jsonl` (the A26 extraction rule);
- the replay follows the A29 parity test: `run_retreat_stage2` with a fixed chooser, then `ground_reasoner_result`;
- leg clearances use `escort_legs` with the `score_p9.py` convention.

**Reproduction gate (switch on, recorded letter B): exact.** The replay matches the live artifact on the stage-2 candidates, the letter assignment, the listing order (A C B), the grounded label, every yield parameter and the degradation list. The leg clears by 0.575 m, as in P1.

**Upstream identity.** No earlier E24 artifact carries an `escort_park_filtered` tag. Its two earlier yields were refused before stage 2 (draws 0 and 1), so a switch-off run is identical up to 71.2 s, and draw index 2 holds.

| Pre-filter label (switch off) | Pose (x, y) | Lateral | Escort leg clearance r4 | Geometry rank | Letter shown, switch off | Switch on (live) |
|---|---|---|---|---|---|---|
| A | (0.022, 1.225) | +0.36 | **0.215 m** | 1 | C | **dropped** (the tag) |
| B | (-0.698, 1.225) | -0.36 | 0.505 m | 2 | A | label A, letter A |
| C | (0.382, 1.225) | +0.72 | 0.575 m | **0 (default)** | D | label B, letter B, **chosen and dispatched** |
| D | (-1.058, 1.225) | -0.72 | 0.865 m | 3 | B | label C, letter C |

The switch-off listing order is A B C D, and the yielder is robot_3 for passer robot_4 in both conditions. There is no `retreat=escort_park_filtered` tag with the switch off, and the default grounds with `retreat=default:no_choice`.

**Answer, in three separate claims:**

- **Deterministic.** With the switch off, stage 2 would have offered 4 candidates. Only pre-filter A violates the 0.45 m latch, and it is geometry rank 1, not the default. The geometry-max default is the same pose in both conditions: (0.382, 1.225), 0.575 m, which is the dispatched pose. So a defaulted or failed stage 2 would have dispatched the identical yield.
- **Not deterministic.** The stage-2 model answer, a sampled VLM call. With the switch off, the model would have seen 4 marks, lettered differently (the dispatched pose under D, the 0.215 m pose under C). The recorded answer is to the 3-mark prompt, so whether the model would have picked the 0.215 m pose cannot be determined offline.
- **Letter replay (A29(iii)).** The recorded letter B, read literally under the switch-off lettering, grounds pre-filter D at (-1.058, 1.225), 0.865 m. That is a different pose from the dispatched one, but not candidate A. Matched by pose, the live pick is pre-filter C (switch-off letter D). Under neither convention does the recorded answer map to candidate A.

**Verdict.** The filter removed a violating option the model could have chosen. It did not change the default pick, and it did not change the pose the model actually picked (rank 0). Whether it changed the dispatched pose of this yield is undeterminable, because it depends on a model answer that was never given. The n = 1 live firing is therefore no evidence that the filter averted a contact.

---

## References

- **Rulings:** prereg-v3 A28, A29, A30 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Previous batch:** `docs/reports/2026-10-12-shield-fix-and-minibatch.md` (§1 is the template).
- **Code:** `reasoning/rag/command_grounder.py` (`prepare_filtered_retreat_selection`, `filter_escort_park_candidates`), `reasoning/rag/escort_clearance.py`, `config/grounding/s1b_dynamic_shield_escort.yaml`.
- **Tests:** `tests/unit/test_a30_escort_overlay.py`, `tests/unit/test_a28_escort_park.py`, `tests/unit/test_a29_filter_parity.py`.
- **Kit** (gitignored, `data/logs/vm_runs/batch5/`): `p9/` (pins, gen, build, deploy, floor, overlay, chain, condition, cost and pin watch, restore scripts; `manifest_p9.txt`, `delta_p9.tar`, `scen/`, `ovsrc/`, `overlays/`, `src/`, `NOTES_vm_b5.md`); `mc_seeds_24_26.{py,jsonl}`; `score_p9.py` + its batch-4 validation; `suite/`.
