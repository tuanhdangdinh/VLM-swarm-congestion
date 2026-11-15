# Validation Take: Escort Obstacle Guard and GT Contact Logging (`m5v`)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: registered before the VM starts. Purpose, deployed files, checks, caps, stop rules and pass/fail criteria for one five-robot validation take.

---

## 1. Purpose and Status

- **What.** ONE live five-robot take on the Isaac Sim VM, with two changes deployed together:
  1. the M3 escort obstacle guard (`fix/escort-obstacle-guard`, report `docs/reports/2026-11-15-escort-obstacle-guard.md`), switched ON;
  2. the always-on ground-truth contact logging (`feat/gt-contact-logging`, report `docs/reports/2026-11-15-gt-contact-logging.md`).
- **Owner approval (2026-11-15).** (1) Keep the guard's current margin rule (robot half-width + `retreat_box_margin_m` 0.05 m): no guard change. (2) One five-robot validation take with the guard on and the contact logging deployed.
- **Evidence grade.** VALIDATION ONLY, n = 1. It is not part of the demo campaign (`docs/superpowers/specs/2026-11-15-demo-campaign.md`), not demo footage and not experiment data. It is never pooled with any arm or scored. It checks that the two changes run live as designed.
- **Branch.** `demo/validation-guard-contacts` (worktree v7n), from `demo/campaign-kits` `cc1313d`, with `fix/escort-obstacle-guard` (`72c08c8`) merged in `4bbe4db` and `feat/gt-contact-logging` (`b5eaee5`) merged in `4c78593`. Conflict resolution only (`docs/implementation_notes.md`); no code change beyond the merges. Local commits; no push.

## 2. Offline Checks Before the Take (Done)

| Check | Result |
|---|---|
| Targeted tests: guard, M5 node grounding, contact geometry, acceptance logging, recompute, held-robot and plan-grammar prompt conditions | 254 passed, 1 skipped (`pxr`) |
| Full unit suite, merged tree vs `demo/campaign-kits` | 57 failed / 3 collection errors on both; failing ids identical (diffed); passes 7100 → 7189 |
| Guard replay (`scripts/escort_obstacle_replay.py`) on `m5D_t01_a1`, merged tree | decision 1 `03bba450` unchanged; decision 2 `a15f3fc5` refused, `yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414` (as the guard report) |
| Contact recompute (`scripts/recompute_gt_contacts.py`) on `m5D_t01_a1`, merged tree | summary JSON identical to the committed `data/experiments/2026-11-15-gt-contact-recompute/m5D_t01_a1.summary.json` (robot_3 vs `obstacle_2` sustained, min −0.16 mm) |
| Kit dry test `test_dry_dmc.sh` (v7n) | `TEST_DRY_DMC m5v OK` (`MIN_MAC_FREE_KB=3000000`, test only) |
| Kit restore test `test_restore_dmc.sh` | `TEST_RESTORE_DMC OK`, 7 cases; the real-delta case removes the 3 added files and their bytecode |

## 3. The Kit (`m5v`)

- **Location (gitignored).** `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/m5v/` (`spec/` + assembled `kit/`), beside the campaign kits so it shares the campaign ledger and the sibling-marker check. Assembled by `bash common/assemble_dmc.sh m5v <v7n>`. No shared file (`common/`, `runtime_delta*/`, other kits) was edited.
- **Kit md5s.** `kit_md5_dmc.txt` (VM files) `1e17de794f629cb875e2d2412d8dec5f`; `kit_md5_all_dmc.txt` `11575dfab1c48b5c0418342e9c9099ab`. The driver, chain and episode runner are the campaign's bytes (`run_dmc.sh` `e811bbd2`, `chain_dmc.sh` `b8a32893`, `ep_run_dmc.sh` `25203d1b`).
- **Same as `m5`.** Scene `mapd_5_s1b`, seed position 21 (`2107305794`), overlay `s1b_shield_escort_orch_seed21.yaml` (`09bc16e6`, byte-identical, empty overlay fragment), scenario yaml `mapd_5_s1b_seed21.yaml` (`61fd6faf`; USD rebuilt fresh, yaml untouched), live ER-2, sequential Nav2 bring-up, the four campaign prompt keys at their defaults, the safety-exemption fix and the 0.20 m floor (M4 key line), `CAP_EP` $0.50, episode budget 6600 s, recording.
- **Differences (all kit-local):**
  - (a) **Runtime delta** `demo_campaign/runtime_delta_m5v/`, DELTA_ID `dde5befb4a2167bd79049ac02b08f625` (14 files): every file of v7n HEAD under `ros2_ws reasoning config isaac` that differs from the VM pin `68e67b5`, except the 3 safety files the kit manages; bytes from HEAD (section 4).
  - (b) **Guard on.** The installed `config/grounding/s1b_dynamic_shield_escort.yaml` = the pinned `40968886` file + exactly one line `  escort_obstacle_guard: true` as the first key of `grounding:` (`gen_guard_grounding_dmc.sh`; the fragment's merge rule). HEAD keeps the pin; the preflight checks the bytes regenerate from HEAD's pin + HEAD's fragment, and the deploy regenerates them on the VM from its own backed-up pin.
  - (c) **Arm check** (deployed loader, before the take): the four inert keys, `prompt_held_robot_state` False, `load_grounding_source(...).params.escort_obstacle_guard` True, and the md5s of `isaac/vgu_sim/contact_geometry.py` and `acceptance_logging.py` at `/ws`.
  - (d) **Post-take gate** (`cond_dmc.py`): M5's startup line `grounding mode=derived params=config/grounding/s1b_dynamic_shield_escort.yaml section_present=True ... stage2_retreat_selection=True escort_obstacle_guard=True`; every decision artifact's `grounding_params_source.params.escort_obstacle_guard` is True; every GT row has `contact_model == "urdf_footprint_v1"`, numeric `min_static_gap_m` and `min_robot_robot_gap_m`, and list-valued contact fields.
  - (e) **Restore** returns the VM to its pin as the other kits do; added files (snapshot ABSENT) are removed, and so is the bytecode of added modules. The restore verifies none is left.
  - `delta_dmc.py` accepts `isaac/` as a live path (host Isaac imports `isaac/` from the repo with `PYTHONPATH=$R`, no colcon). The contact logger's import closure (`acceptance_logging.py`, `config.py`, `oracle.py`) is pinned at its `68e67b5` bytes before the snapshot.
  - Own VM home `~/dmc_m5v`, labels `m5V_tNN_aK`, tag `validation_m5v`.
- **pxr test.** After the deploy, `tests/unit/test_contact_geometry.py` (kit copy == HEAD, `533811c5`) runs in Isaac's Python as `ubuntu` from `~/dmc_m5v/pxr_test/` against the deployed tree: first the builder-parity test alone, then the whole file. Non-fatal and bounded (300 s each). A skip is not a pass. If `pytest` or `pxr` is missing, the test is recorded as not run; nothing is installed.

## 4. What Is Deployed (Relative to the VM Pin `68e67b5`)

| File | Kind | Pin md5 | Deployed md5 |
|---|---|---|---|
| `config/grounding/escort_obstacle_guard.fragment.yaml` | live (new) | absent | `9a13e6feb34cc0093c87ef3564bb43d2` |
| `config/grounding/s1b_dynamic_shield_escort.yaml` | live (generated) | `409688866d25289309e081dcb9433037` | `5ba3767654c7930e31ddbba4eddbecab` |
| `isaac/vgu_sim/acceptance_logging.py` | live | `e10eb6374b10cf95393a0dc00fb5af9d` | `1d8b3b9d02bcda38e581459c7ad0e06f` |
| `isaac/vgu_sim/contact_geometry.py` | live (new) | absent | `77e862cef200009b7bf4f5c791b6cc08` |
| `reasoning/rag/command_grounder.py` | live | `cfbd1fb882e5cf9d3b9f45c6e8f67aec` | `951c23b7f2e0168dab10022abccff77a` |
| `reasoning/rag/escort_clearance.py` | live | `50766aeb4efee9516c59e5ede28b158f` | `69e3404af67dff2c143305294957045c` |
| `reasoning/rag/escort_obstacles.py` | live (new) | absent | `c22a6c81349a2b998f5ee808176593ed` |
| `reasoning/rag/maneuver_geometry.py` | live | `8923c35c0f0c4468e5502aba16a0c421` | `fabe5fdec265acb225dc5aee35132923` |
| `reasoning/vlm/models.py` | live | `0c0c844971278a92da844a9f38793e4e` | `52cba14c5f94b50567f1766cbcd4ff17` |
| `reasoning/vlm/prompt_builder.py` | live | `9007becb85773b9a14b16875a40dfcb2` | `f2f33b778360c5a0f4a6cd82b10c42b5` |
| `ros2_ws/.../swarm_orchestrator/models.py` | colcon (rebuilt) | `273bbf7f7d01755226506fd892a380fa` | `3a0edecd4406e1174e58e4ff4639db31` |
| `ros2_ws/.../swarm_orchestrator/orchestrator_node.py` | colcon (rebuilt) | `e1b3b289ec05e3c21921fa0253829542` | `3ad5bda25a3db21872ba3834cbbb6fce` |
| `ros2_ws/.../swarm_orchestrator/reasoning_pipeline.py` | colcon (rebuilt) | `39a51bfc0de66a42b6f6ac4c78a60478` | `e65f594c0fdf1d891b54b810e4024b60` |
| `ros2_ws/.../swarm_orchestrator/shadow_classical.py` | colcon (rebuilt) | `1de9588a53023b78e555dddd3d80673b` | `24539c25863d1683bf85bad9a0d68fb8` |
| `swarm_execution` `safety.py`, `safety_monitor_node.py`, `config/safety.yaml` | kit base delta (as every campaign kit) | `c6c9cbae`, `7b45075f`, `59839662` | `3011d9a7`, `c2cad302`, `65fb84a3` |

- `orchestrator_node.py` is the MERGE of the campaign branch's and the guard branch's edits (not the guard report's `791f0bf5`).
- **Disclosed difference from `m5D_t01_a1`.** The campaign's `runtime_delta_inert/` froze at `edeb98c`. `2f83faf` (default-off `prompt_held_robot_state`, convoy follow-up) landed on `demo/campaign-kits` after it, so the four reasoning/orchestrator files carry that code too. Its key is off, asserted by the arm check; with it off, prompts are byte-identical (its unit tests).

## 5. Caps and Ledger

- Ledger key `m5v` in the campaign ledger (`demo_campaign/ledger/campaign_ledger.tsv`); caps in the kit's own `caps_dmc.tsv` copy: wall 9000 s, API $0.60 (`usd_m5v`, enforced by this kit's `ledger_dmc.py`: spend left = min(campaign left, $0.60 − m5v booked)), 1 valid take, 3 bring-up aborts. Other scenarios' rows and the campaign totals (43 200 s, $10) are unchanged.
- Admission needs 900 + 6600 + 900 = 8400 s of the 9000 s. A second full invocation fits only if the first booked ≤ 600 s.
- Campaign before this run: 18 203 s of 43 200 s; the ledger books $2.6975 of $10, the owner's brief says ≈ $3.07 (offline spend not booked in the ledger). Nothing extra is booked; either figure leaves room.

## 6. Stop Rules

- One invocation, `bash run_dmc.sh --episodes 1`. GPU stockout: the kit retries the SAME VM's start only (never create a VM or change zone).
- Bring-up aborts are retried by the chain within the 3-abort budget.
- A harness failure is diagnosed from the evidence before anything else; at most one kit fix (dry-tested) and one re-run, and only within the caps.
- An unresolved scene is a valid result: no re-run.
- Gemini 429/402 or any probe failure: stop.
- On every path the VM must be verified TERMINATED (`gcloud compute instances describe ... --format='value(status)'`); otherwise the kit's restore/stop path is run and the status verified again.

## 7. Pass/Fail Criteria

### 7.1 GT Contact Logging

- **Validated** when all hold:
  - the gate passes: every GT row carries `contact_model == "urdf_footprint_v1"` and numeric minima;
  - the offline recompute on the pulled bundle reproduces the logged fields row by row (gaps computed from the rounded recorded pose: max absolute difference 0, identical contact lists);
  - the `pxr` builder-parity test passes in Isaac's Python on the VM (`1 passed`);
  - the sim real-time factor is not materially below `m5D_t01_a1`'s.
- **Partially validated** when the fields are present and reproduce, but a part is missing: no logged contact or near-miss to show entries appearing live, the `pxr` test not run, or a slowdown not attributable either way.
- **Failed** when any row lacks the fields, the recompute disagrees, or the logger crashes or stalls Isaac.

### 7.2 Escort Obstacle Guard

- **Validated as armed and harmless** when:
  - M5's startup line and every decision artifact's params show the guard on;
  - no escort drives into a declared box: no sustained `obstacle_*` contact during an escort, by the logged fields and by the recompute.
- **Validated as firing** when, in addition, an `escort_obstacle_filtered` / `escort_hits_obstacle` event occurs, its arithmetic matches (clear length = distance from the snapshot start to the grown face; growth 0.09 + 0.05 = 0.14 m), and an infeasible yield is withheld. If the guard never has occasion to fire, the live evidence shows only that it is armed and harmless. The offline replay stays the evidence that it blocks the island case.
- **Failed** when the guard is not on in the line or params, an escort enters a declared box, or the guard crashes M5.

### 7.3 Take Outcome

Robots arrived, decisions by provenance, refusals by reason, closest pair and floor stops are recorded for the record only. They are not a criterion.

## 8. Outputs

- Bundle under `demo_campaign/m5v/runs/`, manifest `demo_campaign/m5v/MANIFEST_<ts>.md5`, the pxr logs under `demo_campaign/m5v/vm/pxr_test/`. Bundles are never edited.
- Results: `docs/reports/2026-11-15-validation-guard-contacts-results.md` and a dated entry in `docs/implementation_notes.md`.
