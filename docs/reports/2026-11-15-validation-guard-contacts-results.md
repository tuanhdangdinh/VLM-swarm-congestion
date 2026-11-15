# Validation Take Results: Escort Obstacle Guard and GT Contact Logging

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: results of the one live validation take `m5V_t01_a1`, offline evaluation of the pulled bundle, and the verdict for each change.

---

## Scope

- **VALIDATION ONLY, n = 1.** This take is not demo footage and not experiment data. It is never pooled or scored. Registration: `docs/superpowers/specs/2026-11-15-validation-guard-contacts.md` (`9a68539`, committed before the VM started).
- **Changes under test:** the M3 escort obstacle guard, switched on (`docs/reports/2026-11-15-escort-obstacle-guard.md`), and the GT contact logging (`docs/reports/2026-11-15-gt-contact-logging.md`). Both run from branch `demo/validation-guard-contacts` (v7n; merges `4bbe4db` and `4c78593`).
- **Bundle (read only, never edited):** `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/m5v/runs/m5V_t01_a1/` (gitignored).
  - Manifest: `m5v/MANIFEST_20261115T075158Z.md5`, 68 files, md5 `782264e692d3c0231b31cec6c272c5c6`.
  - All 68 files re-checked against the manifest after the evaluation: unchanged.
  - The kit's video verify writes frame maps into `rec/` after the manifest, as in every campaign take.
- **Evidence labels:** "verified" means read from the bundle or re-computed here. "Inferred" means reasoned from it.

---

## 1. The Run

| Item | Value |
|---|---|
| Driver | `bash run_dmc.sh --episodes 1` in `m5v/kit` (kit md5 `1e17de79` / all files `11575dfa`); driver log `m5v/driver_m5v_20261115T075158Z.log` |
| GPU stockout | 15 failed starts of the same VM in `asia-northeast1-a`, 07:52–08:26Z (about 34.5 min). Started on attempt 16. Nothing was created; the zone was not changed. |
| VM up | 08:26:35Z → TERMINATED 09:35:39Z. Booked 4144 s. |
| Prep | snapshot, USD build, deploy and overlay took 08:27:35–08:31:07Z |
| Take | 08:31:17–09:32:56Z: 600 sim-s horizon, `outcome=ran` |
| Bring-up aborts | 0 |
| Gates | every gate passed: `GATE OK`, `RESTORE OK`, `STARTUP_CHECK OK`, `CLASSIFY launched`, M4 floor key line, `COND failed=none` (all 25 checks, including the four new m5v checks) |
| Spend | $0.0692 est. (cost_watch) + $0.0010 probes |
| Restore | `RESTORE_DMC OK`, `PINS_V3 OK`. The 3 added files and the bytecode of the 2 added modules were removed (VM restore log); the installed packages equal the snapshot |
| VM status after exit | `TERMINATED`, verified by the driver and again by hand with `gcloud compute instances describe ... --format='value(status)'` |
| Ledger after | campaign 22 347 s of 43 200 s, $2.7677 of $10 (booked); `m5v` 4144 s of 9000 s, $0.0702 of $0.60, valid 1 of 1, bring-up aborts 0 of 3 |

Arm check before the take, through the deployed loader (verified, `[ov]` lines):

- the profile fields equal `WANT_ARM`;
- `plan_dispatch_order_source=chi`, and the three B3 keys and `prompt_held_robot_state` are False;
- `load_grounding_source(...).params.escort_obstacle_guard` is True;
- `contact_geometry.py` is `77e862ce` and `acceptance_logging.py` is `1d8b3b9d` at `/ws/isaac/vgu_sim/`.

The deploy regenerated the guard grounding file on the VM from its own backed-up pin `40968886`, byte-equal to the delta and the installed file, and loaded it as `GUARD_LOAD derived True`.

---

## 2. GT Contact Logging

### 2.1 Fields Present

- All 6001 GT rows carry `contact_model == "urdf_footprint_v1"` and numeric `min_static_gap_m` and `min_robot_robot_gap_m`. No row is non-numeric or null (verified; also the post-take gate `gt_contact_fields`).
- `gt/run_manifest.json` reports `completed: true, failure: null`. The logger did not crash Isaac.

### 2.2 Row-by-Row Recompute

- **Method.** For every row, the frame was recomputed with v7n's `contact_geometry.compute_contact_frame`, from the row's own recorded (rounded) pose, against `scene_static_boxes` of the bundle's `scenario.yaml` (14 boxes). Then `scripts/recompute_gt_contacts.py` was run on the bundle, with output in the scratchpad.
- **Result.** 6001 of 6001 rows match exactly: both contact lists, `min_static_gap_m` and `min_robot_robot_gap_m`.
  - Maximum absolute difference: 0.0 for both minima.
  - Mismatching rows: 0.
- `recompute_gt_contacts.py`: static `clear`, robot–robot `clear`, `logged_rows_with_contact_model` 6001.

### 2.3 Contact Events and Minima

- **No contact event.** No robot–static or robot–robot pair came within the 5 mm threshold on any row. Both logged lists are empty on all 6001 rows, and the recompute agrees.
- **Closest static approach: a 5.5 mm near-miss.** robot_4 vs `obstacle_1` (declared rack island, x −1.30 to −0.75, y −0.70 to 0.90), at sim 81.5–81.6 s:
  - The gap profile is 55.8 → 38.9 → 24.5 → 12.9 → **5.5** → 7.5 → 48.8 mm (79.5–82.5 s, every 0.5 s).
  - robot_4 backed at a steady 0.091 m/s past the island's south-west corner (−1.30, −0.70), heading 1.967 rad.
  - This was M4's `reverse` from decision `95066420` (`vlm_verbatim`, dispatched 75.9 s, COMPLETED). It was not an escort.
- **Per-robot static minima:**

  | Robot | Box | Gap | Sim time |
  |---|---|---|---|
  | robot_1 | `rack/SW_west` | 97.9 mm | 22.0 s |
  | robot_2 | `obstacle_2` | 82.2 mm | 60.0 s |
  | robot_3 | `rack/SE_east` | 213.1 mm | 72.6 s |
  | robot_4 | `obstacle_1` | 5.5 mm | 81.6 s |
  | robot_5 | `obstacle_1` | 19.1 mm | 87.4 s |

- **Robot–robot minimum:** 156.1 mm footprint gap (robot_1/robot_4, 37.1 s). The GT centre-distance minimum is 0.3101 m.
- **Camera check.** The camera_raw frame at sim 81.73 s (segment 000, frame 246) shows robot_4 beside the island's south-west corner, with no visible overlap. At about 4 mm per pixel on the box top, with perspective from the 0.3 m box height, the image cannot resolve 5 mm. It agrees with a close pass, not a pin. The frame was extracted to the scratchpad, not into the bundle.

### 2.4 Real-Time Factor

| | `m5D_t01_a1` (campaign, stub logger) | `m5V_t01_a1` (contact logger) |
|---|---|---|
| RTF, GT `started_at_utc` → GT last write | 0.184 (600 sim-s in 3265 s) | 0.168 (600 sim-s in 3578 s) |
| RTF from `m5_scene.jsonl`, sim 30–100 / 100–300 / 300–600 s | 0.200 / 0.176 / 0.182 | 0.168 / 0.161 / 0.169 |

- The take ran about 8.5 % slower than `m5D_t01_a1`, and the slowdown is uniform across the run.
- **Logger cost, measured offline.** `compute_contact_frame` on these 6001 rows takes 7.2 s on the Mac (1.2 ms per row). The wall-time difference is 313 s. Even at several times the Mac's per-row cost, the logger explains a few percent of it at most.
- **Inferred: the slowdown is not attributable to the logger.** Run-to-run variance between two VM starts is the likelier cause, and both values lie inside the 0.16–0.19 range recorded for tranche 1 and v4 (`m5` profile). With n = 1 per side, this is not proven.

### 2.5 pxr Builder-Parity Test

- **Not run.** Isaac's Python (`/home/ubuntu/IsaacSim/kit/python/bin/python3`) has no `pytest`: `No module named pytest` (`m5v/vm/pxr_test/pxr_test.log`, `pxr_test_full.log`).
- As registered, nothing was installed and the step was non-fatal. The USD-builder parity of the scene boxes therefore still rests on the map-generator parity and the shared config helpers (contact report, section 4).
- Running it later needs either a `pytest` in Isaac's Python or a small `pytest`-free runner for that one test function. Either would need its own approval.

### 2.6 Verdict: PARTIALLY VALIDATED

- **Validated live:**
  - the fields are present and numeric on every row;
  - the offline recompute reproduces every row exactly;
  - the logger ran a full 600 sim-s five-robot take without failure;
  - a 5.5 mm near-miss was measured and is consistent with the camera.
- **Missing:**
  - no live contact occurred, so this take does not show entries appearing in the logged lists when a robot is pressed against a box (the offline positive controls, `m5D_t01_a1` and G4, remain the evidence for that);
  - the `pxr` builder-parity test did not run;
  - RTF is about 8.5 % lower than `m5D_t01_a1`, inferred but not proven to be unrelated to the logger.

---

## 3. Escort Obstacle Guard

### 3.1 Armed

- **M5 startup line (verified):** `grounding mode=derived params=config/grounding/s1b_dynamic_shield_escort.yaml section_present=True aisle_y_band_m=(-1.66, 1.66) band_override=False stage2_retreat_selection=True escort_obstacle_guard=True`
- **Decision params:** all 9 decision artifacts have `grounding_params_source.params.escort_obstacle_guard == true` (verified; gate check `artifacts_param_escort_obstacle_guard`).

### 3.2 Escorts and Guard Events

- **No escort was grounded in this take.**
  - None of the 9 decisions dispatched or proposed a command with `passer_escort_*` fields.
  - No degradation tag contains `escort_obstacle_filtered` or `escort_hits_obstacle`.
  - `m5.log` has no such line.
- **Why there were none.** Every `yield` decision (four) and the one `junction_clear`, any of which could have carried an escort, was refused earlier in grounding, before any escort was derived:
  - "no shared lane" (robot_1/robot_4, twice);
  - "no declared junction" (robot_2/robot_3, twice);
  - "no feasible yielder" (the `junction_clear` at 126.6 s).
- **No robot entered a declared box.** By the logged fields and by the recompute, the closest any robot came was robot_4's 5.5 mm pass, under a `reverse`.

### 3.3 Verdict: VALIDATED AS ARMED AND HARMLESS ONLY

- **Shown live.** The guard is armed: the startup line and every artifact's params. It did not crash or perturb M5: 9 analyses and every gate passed.
- **Not shown live.** The guard never had occasion to fire. This take gives no live evidence that it blocks an escort into a box.
- **The blocking evidence remains offline.** The replay on `m5D_t01_a1` refuses decision 2 (`yield=infeasible:escort_hits_obstacle:robot_3:obstacle_2:0.414`); it was re-run on the merged tree and reproduced (registration section 2).

---

## 4. Take Outcome (For the Record Only)

| Item | Value |
|---|---|
| Arrived (GT, 0.3 m) | 2 of 5 (robot_1, robot_5); unresolved at the 600 s horizon. `m5.log` logs 3 arrivals (robot_1 reached a second task goal). |
| Analyses | 9, all ER-2, 209 170 tokens |
| Provenance (goal check) | 5 `m3_default`, 3 `repaired`, 1 `vlm_verbatim` |
| Dispatched | `b07a700f` reverse r1/r2/r3; `95066420` reverse r4/r5 (`vlm_verbatim`); `929335f4` and `2acc6130` reverse proposals degraded to temporary waits for r2–r5 ("both robots outside the corridor on the same side"). Every dispatched leg COMPLETED. |
| Refusals withheld (`refusal_no_action`) | 5: `2461ee6b` and `597e224f` (no shared lane), `6a621c29` and `45f50dce` (no declared junction), `6e4c8849` (no feasible yielder: retreat room ≤ 0.15 m < 0.77 m) |
| Closest pair | GT centre distance 0.3101 m; footprint gap 156.1 mm |
| Hard-floor (0.20 m) stops | 0 |

As in the campaign, `goal_check_dmc.py` prints `withheld=0`. Count the refusals from `m5.log`.

---

## 5. Anything Unexpected

- **The guard's scope missed the closest approach.** The tightest static approach of the take (5.5 mm, robot_4 at `obstacle_1`'s corner) happened under a VLM-named `reverse`, not an escort. The guard checks escort legs only. No stage sweeps a `reverse` leg against declared boxes. This is a finding, not a defect of either change under test.
- **Pre-existing kit quirk.** The driver's "new bundles" glob `<TOKEN>_t*` also matches `m5V_t01_a1.cost.log` and `.outer.log`. Its startup-check, video-verify and goal-check lines therefore print MISSING / FLAGGED / empty entries for those two files. It affects reporting only, and the campaign kits share it.
- **Discrepancy in the campaign total.** The ledger books $2.6975 before this run, while the owner's brief says ≈ $3.07. Nothing extra was booked. Either figure leaves ample room.

---

## 6. Verified and Inferred

| Claim | Status |
|---|---|
| Every GT row carries the contact fields; the recompute matches all 6001 rows exactly | verified |
| No contact event; closest static 5.5 mm (robot_4, `obstacle_1`, 81.6 s, under `reverse`) | verified (fields, recompute, one camera frame) |
| Guard on in the startup line and in all 9 artifacts; no escort grounded; no guard event | verified |
| VM restored to its pin (added files and bytecode removed) and TERMINATED | verified (restore log, `gcloud`) |
| The RTF drop (0.184 → 0.168) is not caused by the logger | inferred (offline per-row cost; n = 1 per side) |
| The guard would block a live escort into a box | not shown live; offline replay only |
| `pxr` builder parity | not run (no pytest in Isaac's Python) |
