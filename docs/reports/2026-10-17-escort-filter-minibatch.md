# The A30 Escort-Filter Mini-batch E24-E26

**Prepared:** 2026-10-17

**Revision history:**

- Initial draft: the A30 switch-on overlay built offline (grounding file, seeds 24-26, overlays, VM kit p9); mini-batch E24-E26 PRE-REGISTERED before any live call (§1). Results follow in later sections.

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

## References

- **Rulings:** prereg-v3 A28, A29, A30 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Previous batch:** `docs/reports/2026-10-12-shield-fix-and-minibatch.md` (§1 is the template).
- **Code:** `reasoning/rag/command_grounder.py` (`prepare_filtered_retreat_selection`, `filter_escort_park_candidates`), `reasoning/rag/escort_clearance.py`, `config/grounding/s1b_dynamic_shield_escort.yaml`.
- **Tests:** `tests/unit/test_a30_escort_overlay.py`, `tests/unit/test_a28_escort_park.py`, `tests/unit/test_a29_filter_parity.py`.
- **Kit** (gitignored, `data/logs/vm_runs/batch5/`): `p9/` (pins, gen, build, deploy, floor, overlay, chain, condition, cost and pin watch, restore scripts; `manifest_p9.txt`, `delta_p9.tar`, `scen/`, `ovsrc/`, `overlays/`, `src/`, `NOTES_vm_b5.md`); `mc_seeds_24_26.{py,jsonl}`; `score_p9.py` + its batch-4 validation; `suite/`.
