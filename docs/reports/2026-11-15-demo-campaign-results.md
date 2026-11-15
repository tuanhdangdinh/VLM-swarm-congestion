# Demo Campaign Results

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: intersection live takes 1–3 (ER-2, B3), why live ER-2 gave no usable plan, and the Sonnet 5.5 arm built for takes 4–5.
- Rev 2 (2026-11-15): added section 5, convoy counterflow live takes 1–3, the root cause of the non-resolution, and the take 1 panel video.
- Rev 3 (2026-11-15): added section 6, head-on with obstacle, take 1 (ER-2), and its panel video.
- Rev 4 (2026-11-15): added section 7, intersection takes 4–5 (ER-2, B3), the adversarial verification of take 5 (the one VLM-driven take), its panel video, and the wall-share amendment.
- Rev 5 (2026-11-15): campaign closed. Added the final summary (all four scenarios, ledger totals, the three-way VLM count, open owner decisions, archive index), section 8 (five-robot take 1 and its video) and section 9 (the combined video). Fixed stale statements: the Sonnet offline spend is booked (sections 3.4, 3.6), and the ER-2 choice for takes 4–5 is now recorded in registration section 10.8 (running summary, section 7). The running summary below is otherwise kept as written per phase.
- Rev 6 (2026-11-15): added section 8.7, an offline follow-up showing that robot_3's escort in the five-robot take drove into rack island `obstacle_2`, with stills and an escort-segment check over the campaign and the October five-robot bundles. Scoped every contact statement: ground truth's two contact fields are hard-coded empty, so they show nothing. Added section 5.8, the outcome of the convoy held-robot prompt check. Updated the final summary, sections 8.2–8.6 and the open owner decisions.

---

## Final Summary (Campaign Closed, 2026-11-15)

Every take is an illustrative demo, not controlled experimental evidence. No take is pooled with experiment data, and n is 1 to 5 per scenario, so nothing here is a rate.

### Scenarios and Videos

| Scenario | Valid takes (bring-up aborts) | Outcomes | Selected take, label | Video (v7g `data/demo/campaign/`), md5 |
|---|---|---|---|---|
| 4-robot intersection (`ib`, ER-2, B3; sections 1, 7) | 5 (1) | take 1 Unresolved failure (3/4 arrived); takes 2, 3, 4 M3-default resolution; take 5 VLM-driven execution (all 4/4) | take 5, **VLM-driven execution** (chosen for its label; disclosed) | `ibD_t05_a1_panel.mp4`, `fdf07a82fcb657b738c44a89bfbe3dae` |
| Convoy counterflow (`cv`, ER-2, legacy grounding; section 5) | 3 (0) | takes 1–3 Unresolved failure, 0/4 arrived in each | take 1, **Unresolved failure** (selected take) | `cvD_t01_a1_panel.mp4`, `824319447d05aaef6623158d00d2818f`; a `_small` copy, `b78cff5b3db4b25f6b8e218111656a42` |
| Head-on with obstacle (`ho`, ER-2, prompt v2; section 6) | 1 (0) | take 1 resolved 2/2 | take 1, **M3-default resolution** (grounder-corrected) | `hoD_t01_a1_panel.mp4`, `2aa6534ad508d3440e51822fdcd3f0f0` |
| Five robots, seed position 21 (`m5`, ER-2; section 8) | 1 (0) | take 1 unresolved, 1/5 arrived | take 1, **Unresolved failure** (limitation demonstration) | `m5D_t01_a1_panel.mp4`, `75bf99e64c7ebea10573f08eb62440c3` |
| All four, excerpts (section 9) | — | — | — | `demo_campaign_combined.mp4`, md5 in section 9 |

### Ledger Totals (`ledger_dmc.py status`, After the Last Invocation)

| Item | Value |
|---|---|
| VM wall clock, campaign | 18 203 s of 43 200 s, over 10 invocations: `ib` 8239 s of 12 600 s, `cv` 4829 s of 9000 s, `ho` 1302 s of 1800 s, `m5` 3833 s of 14 400 s |
| API spend (estimates) | $2.6975 of $10: offline $2.2705 (the $2.00 registration booking plus $0.2705 for the Sonnet B3 check), live takes $0.4165, probes $0.0105 |
| Valid takes | 10: `ib` 5, `cv` 3, `ho` 1, `m5` 1 |
| Bring-up aborts | 1 of 3 allowed per scenario, all in `ib` (`ibD_t01_a1`, `change_state` timeout on robot_1); 0 in `cv`, `ho` and `m5` |

Wall is counted from VM start to TERMINATED. The `m5` invocation also spent about 24 min in 11 failed VM start attempts before the VM started, which are not booked.

### Valid Response, Accepted Plan, Changed Behaviour

The counts are per analysis (decision artifact); stage-2 retreat calls are not counted. The columns are:

- **Valid VLM response:** the call completed and the answer parsed (`finish_reason=completed`, `parse_status=valid`).
- **Accepted VLM plan:** plan verification kept the model's plan with no edit (`plan.provenance=vlm_verbatim`).
- **VLM plan changed executed behaviour:** the commands executed differ from M3's default plan for the same snapshot (`COUNTERFACTUAL executed_differs_from_m3_default=True`, the basis of the VLM-driven label). This is computed for the intersection only.

| Scenario | Valid VLM response | Accepted VLM plan | VLM plan changed executed behaviour |
|---|---|---|---|
| Intersection, 5 takes | 9 of 9: 5 jam decisions plus 4 "no congestion" answers | 1 (take 5). The other jam plans: 2 `repaired` (takes 2, 4), 2 nulled as invalid structure (takes 1, 3) | 1 (take 5): the recede order only, a 0.010 m chi near-tie. Takes 1–4: False |
| Convoy, 3 takes | 36 of 36 | 3 of 36 (15 `repaired`, 18 `m3_default`) | Not computed (no default comparison for this scenario). The first-trigger yield was executed as the model named it in 3 of 3 takes. |
| Head-on, 1 take | 2 of 2 | Not applicable: plan channel off (prompt v2) | Not computed. Both strategies (`reverse`, `yield`) were dispatched as named, but the gate swapped decision 2's yielder (robot_1 → robot_2). |
| Five robots, 1 take | 8 of 8 | 2 of 8, both executed as named (1 `repaired`, 5 `m3_default`; 6 of 8 withheld by grounding refusals) | Not computed |
| **Total** | **55 of 55** | **6** (of the 53 plan-channel analyses) | **1** |

### What This Does and Does Not Show

- **Intersection.** The pipeline carried a model-chosen order to execution, with all checks on, once in five takes (take 5). The choice was a near-tie, 0.010 m of chi against a 0.15 m tolerance, and it changed only the timing of the two recedes: robot_3 backed out about 9 sim-s before robot_4. Pockets, the cross, the release and the crossing order stayed on chi. The model's order follows ascending robot id, as it mostly does offline.
- **Head-on.** It resolved 2/2 because the feasibility gate corrected the model's yielder: robot_1 had 0.70 m of retreat room against 1.08 m required, so robot_2 yielded. The model's first strategy (`reverse`) ran and did not clear the scene.
- **Convoy: unresolved in 3 of 3.** The first yield ran as named, but the model named only the standoff pair. The two queued robots, never commanded, followed through the gate and latched. The legacy vocabulary then had no recovery: the 33 later proposals ran as 8 s waits. Stating the hold-back state in the prompt did not change this offline: 0 of 22 answers per condition grounded into the four-robot sequence, so no retake was run (section 5.8, Rev 6).
- **Five robots: unresolved.** Two model decisions were executed as named, but the yield pairs then latched within 0.45 m. robot_3's escort did not stall on its own: the straight escort segment crossed rack island `obstacle_2`, and robot_3 drove into the island's east face and stayed pinned there until the escort timed out (section 8.7, Rev 6). The six later proposals were refused by grounding checks (retreat room, junction or lane), and Layer 2 went quiet after sim 275.5 s, as the registration expected. The "unresolved" label therefore partly reflects an escort path error, not only the model's decisions or the grounding refusals.
- **Safety scope (Rev 6).** Ground truth logs no contacts of either kind: `robot_robot_contacts` and `robot_static_contacts` are hard-coded empty lists (`isaac/vgu_sim/acceptance_logging.py:99-100`). Every "0 contacts" statement in this report is scoped as follows:
  - **Robot-robot:** supported only by the GT closest centre distance, computed from poses (GT `min_pairwise_distance_m`, minimum per valid take 0.2176–0.3701 m). That is above the 0.20 m floor and the 0.076 m nose-to-nose contact distance.
  - **This follows a standing ruling.** The prereg-v2 caveats of 2026-10-08 and 2026-10-09 (main repo, `fc73151`) and `docs/reports/2026-09-25-overnight-findings.md`:1852–1871 already ruled that the GT contact fields are not evidence, and that contacts must be recomputed from distances. The Rev 1–5 contact lines of this report ran against that ruling.
  - **Robot-static:** not logged by ground truth. The only check is the distance recompute in section 8.7. It found robot_3 within 5 mm of `obstacle_2` in 4526 of the 4534 GT rows from sim 146.7 s to 600 s (8.7.2).
- **What it does not show.** Nothing here is controlled evidence. One VLM-driven take in five, with n ≤ 5 per scenario, gives no rate, no comparison with Layer 2 off, and no claim that the model reasons the order from the scene.

### Open Owner Decisions (as Identified in the Sections; No Further Recommendation)

- **Convoy fix options** (section 5.5): (a) prompt/kit: hold-back state or a platoon sentence; (b) grounding: hold uncommanded robots whose goals lie across the corridor, or refuse `continue` for them; (c) recovery: a post-gate cluster template. Each changes the registered convoy experiment's Arm A, so each needs a registration amendment or nothing. Rev 6: a prompt-only form of (a) was tested offline and is a no-go (section 5.8).
- **Options-detail prompt/parser fix** (section 2.5): (a) render the options detail so it cannot be read as an action, or (b) narrow parser tolerance for an exact offered `"<action> (<detail>)"`. Either is a third fix cycle and needs the owner's approval.
- **Log-filter lines** (sections 6.5, 7.3, 5.6, 8.5): whether to add the `yield re-grounded` swap line and `dispatch_order_source` to the demo panel's fixed filter, which these videos left unchanged. The convoy and five-robot refusal lines (`yield refused`, `refusal withheld`) are in the same position.
- **Intersection yielder gap** (registration 10.1, section 3.4): it stays open by owner decision.
- **Escort obstacle guard** (section 8.7, Rev 6): neither M3's escort grounding nor M4's `drive_heading` checks the straight escort segment against declared static obstacles. One option is for grounding to refuse, or shorten, an escort whose swept segment crosses a declared obstacle box grown by the chassis half-width. Any such change alters the S1b grounding that registered arms use, so it needs a registration amendment or nothing.
- **Static-contact logging** (section 8.7, Rev 6): `robot_static_contacts` (and `robot_robot_contacts`) are hard-coded empty (`isaac/vgu_sim/acceptance_logging.py:99-100`). The options are (a) a PhysX contact-report detector on the chassis and obstacle prims, or (b) a per-row distance recompute in the logger (the chassis collision box against the declared obstacle boxes, as section 8.7 does offline). Until then, robot-static contact claims need an offline recompute.
- **Known wording issue (Rev 6, not edited here):** several frozen reports on other branches state "0 GT contacts" or "no contact" from the empty fields, or from robot-pair distances alone in scenes with static obstacles. They are listed in section 8.7.6.

### Archive Index (Every Attempt Directory)

Bundles are under `data/logs/vm_runs/demo_campaign/<scn>/runs/`; manifests are under `data/logs/vm_runs/demo_campaign/<scn>/`. Each manifest also lists the attempt's `.cost.log` and `.outer.log`, plus the VM-side `vm/attempts.tsv`, `vm/chain_dmc.log` and `vm/probe.log`. On 2026-11-15 every `runs/` file matched its manifest (re-hashed). The `vm/` files differ in the earlier manifests of `ib` and `cv` because each later pull overwrites them by design. The `_backup_<label>/` directories (pre-run copies of `orchestrator.yaml` and `rag.yaml`) are in no manifest.

| Scenario | Attempt directory | Outcome | Manifest file | Manifest md5 (files) |
|---|---|---|---|---|
| `ib` | `ibD_t01_a1` | bring-up abort (`change_state` timeout, robot_1) | `MANIFEST_20261114T223205Z.md5` | `a4e4eaefd41a2eaab96d895cbb8f91c8` (81, both attempts) |
| `ib` | `ibD_t01_a2` | take 1, Unresolved failure | `MANIFEST_20261114T223205Z.md5` | `a4e4eaefd41a2eaab96d895cbb8f91c8` (81, both attempts) |
| `ib` | `ibD_t02_a1` | take 2, M3-default resolution | `MANIFEST_20261114T232322Z.md5` | `5dddd2fb84dcdf6237c59e65d097dd28` (55) |
| `ib` | `ibD_t03_a1` | take 3, M3-default resolution | `MANIFEST_20261114T235042Z.md5` | `a92ebe37ad224d99e4f99e332784b12a` (51) |
| `ib` | `ibD_t04_a1` | take 4, M3-default resolution | `MANIFEST_20261115T024528Z.md5` | `b7e7a6bf51743e34b744debc329d1725` (54) |
| `ib` | `ibD_t05_a1` | take 5, VLM-driven execution | `MANIFEST_20261115T031339Z.md5` | `0d2300c1de88ff24db3cc71d5dd0ff81` (57) |
| `cv` | `cvD_t01_a1` | take 1, Unresolved failure | `MANIFEST_20261115T002252Z.md5` | `92639ca105ce5ae2944784cf4e37850d` (72) |
| `cv` | `cvD_t02_a1` | take 2, Unresolved failure | `MANIFEST_20261115T010824Z.md5` | `c2356be80157864416bd666004cc706f` (72) |
| `cv` | `cvD_t03_a1` | take 3, Unresolved failure | `MANIFEST_20261115T014050Z.md5` | `682c9a59566cf32815e2edd66a8d8bbe` (72) |
| `ho` | `hoD_t01_a1` | take 1, M3-default resolution | `MANIFEST_20261115T021253Z.md5` | `31c7a4e580dc799fb385e218628f29f9` (64) |
| `m5` | `m5D_t01_a1` | take 1, Unresolved failure | `MANIFEST_20261115T035453Z.md5` | `bd7572c417c558fda4d19c40867363e1` (68) |

---

## Running Summary (Per Phase, as Written)

- **Status.** Every take here is an illustrative demo, not controlled experimental evidence. Takes are never pooled with experiment data.
- **Intersection, ER-2 under B3, 3 takes (2026-11-14/15 UTC).** Take 1 unresolved (3 of 4 arrived), takes 2 and 3 resolved. None is VLM-driven: the labels are Unresolved, M3-default, M3-default. No GT contact, no floor stop. (Rev 6: robot-robot only, from the GT closest pair. The GT contact fields are hard-coded empty, and this scene declares no static obstacles.)
- **Why ER-2 gave no usable plan live (section 2).** The live prompt is byte-identical to the offline B3 prompt for the same snapshot, and nothing was truncated. The three takes failed for three different reasons:
  - take 3: the known options-detail copy (`"reverse (south arm)"`);
  - take 2: the known missing releasing `yield`;
  - take 1: a trigger on an approach snapshot caused by a one-frame M1 identity glitch, plus a malformed leg key never seen offline.
  Had take 3's two actions been parsed as `reverse`, it would have been the demo event.
- **Take 1 unresolved (section 2.4).** The M3 default plan ran on that pre-jam geometry. The release gate for robot_1 needed robot_3 to travel 2.65 m, but robot_3's goal was only about 2.54 m away. Its fallback hold of 240 s outlasted the 300 s horizon. This is not related to the model's output.
- **Sonnet 5.5 arm built and dry-tested (section 3).** It is a separate kit, `demo_campaign/ib_sonnet/kit`. The probe works from the Mac.
- **Offline Sonnet B3 check (n = 16, $0.216 at list).** 16/16 answered and valid, and 11 were `vlm_verbatim`. But only 1 of 15 first triggers would be classified VLM-driven, because of the yielder gap: chance over 2 takes is about 13 %.
- **Recommendation: no-go for Sonnet takes as a route to a "VLM-driven" video; owner decision.** Launching also needs an owner-approved take-budget deviation (section 3.5).
- **Intersection takes 4–5 (ER-2, B3; section 7).** Both resolved 4/4. Take 4 is M3-default (plan `repaired`). Take 5 is the only **VLM-driven execution** so far: ER-2's plan was verified `vlm_verbatim` with no edit, and its recede order robot_3 → robot_4 was dispatched and executed as written, with robot_1 as the yielder. The default order was robot_4 → robot_3 (computed offline). Checks 1–8 pass from the raw files.
  - Caveats: the two orders differ in chi by 0.010 m (a near-tie; the verifier tolerance is 0.15). By design only the timing of the two recedes changed; pockets, the cross, the release and the crossing order stayed on chi, and the model's `crossing_order` was not used. The order follows ascending robot id, as ER-2 mostly does offline. This is 1 VLM-driven take out of 5 live intersection takes; illustrative, not controlled evidence.
  - Takes 4–5 ran on the ER-2 kit, not the Sonnet arm that section 10.5 of the registration plans. (Rev 5: this choice is now recorded in registration section 10.8.)
- **Wall-share amendment (registration 10.7).** `ib` share 9000 → 12600 s, `ho` 5400 → 1800 s; the totals are unchanged (37 800 s of shares, 43 200 s and $10 campaign caps).
- **Convoy counterflow, ER-2, 3 takes (2026-11-15 UTC; section 5).** All three unresolved, 0 of 4 robots arrived in each. The first trigger's yield was executed as the model named it, but the model named only the standoff pair. The two queued robots, never commanded, followed through the gate and the scene latched for good. The 33 later proposals all ran as 8 s waits. Cause: the first decision's content, in a scene built so that such an answer cannot resolve, and then no recovery strategy in legacy grounding. Not a harness issue.
- **Head-on with obstacle, ER-2, 1 take (section 6; Rev 5 bullet).** Resolved 2/2. The label is M3-default resolution (grounder-corrected): the feasibility gate swapped the model's yielder robot_1 (0.70 m retreat room < 1.08 m) to robot_2. 0 contacts, 0 floor stops. (Rev 6: robot-robot by GT closest pair; robot-static not logged by GT. The section 8.7 recompute gives a minimum chassis-to-box gap of 0.0445 m.)
- **Five robots, seed position 21, ER-2, 1 take (section 8; Rev 5 bullet).** Unresolved, 1 of 5 arrived; a limitation demonstration. Two decisions were executed as named (yield + escort). Six later proposals were refused by grounding checks and withheld, with no analysis after sim 275.5 s. 0 contacts, 0 floor stops. (Rev 6: robot-robot only. robot_3 was against island `obstacle_2` from sim 146.7 s, within 5 mm in all but 8 GT rows to the end, which GT does not log; see section 8.7.)

---

## 1. Intersection Live Takes 1–3 (ER-2, B3)

Illustrative, not controlled evidence. Kit `demo_campaign/ib/kit`, effective overlay `614beed0` (B3), delta `5c7973d3`, live `gemini-robotics-er-2-preview`. Sources: `ib/runs/<label>/`, `ib/driver_ib_*.log`, `ib/take*_stdout.log`, `take_class_dmc.py`.

| Take (label) | Resolved | Label (`TAKE_CLASS`) | Provenance | Dispatched recede order | Default (chi) order | GT min pair | Safety | Recording frames (annotated / raw) | Manifest md5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 (`ibD_t01_a2`; a1 = bring-up abort, `change_state` timeout on robot_1) | no, 3/4 (robot_1 not arrived) | Unresolved failure | `m3_default` (plan absent) | robot_3, robot_4 | robot_3, robot_4 | 0.370 m | floor stops 0, GT contacts 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 2182, `stale_pose_unsafe` 2 | 1481 / 2271 | `a4e4eaef` (81 files, both attempts) |
| 2 (`ibD_t02_a1`) | yes, 4/4 | M3-default resolution | `repaired` | robot_4, robot_3 | robot_4, robot_3 | 0.288 m | floor stops 0, GT contacts 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 13787 | 1605 / 2213 | `5dddd2fb` (55 files) |
| 3 (`ibD_t03_a1`) | yes, 4/4 | M3-default resolution | `m3_default` (plan absent) | robot_4, robot_3 | robot_4, robot_3 | 0.314 m | floor stops 0, GT contacts 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 10321 | 1423 / 1975 | `a92ebe37` (51 files) |

- Every `VIDEO_VERIFY` was OK, every `STARTUP_CHECK` OK, every condition gate passed. `executed_differs_from_m3_default=False` in all three.
- Model calls: 4 in total (take 2 had a second, no-congestion call), each 1 attempt, no refusal, no stage-2 call. Estimated spend $0.0069, $0.0145 and $0.0066.
- Ledger after take 3: `ib` 5014 s of 9000 s, valid 3 of 5, 1 bring-up abort of 3, next take 4.
- The GT minimum pair (0.29–0.37 m) is the standing jam separation. The many `min_distance_violation` lines are the latched stop of the jammed robots, not contacts.

---

## 2. Why Live ER-2 Gave No Plan (Part A)

### 2.1 Every Model Call (Verified From the Bundles)

| Take, request | Snapshot (stamp) | Raw output (relevant part) | Parser | Verification and dispatch |
|---|---|---|---|---|
| 1, `a1ec9ee1` | 25.43 s; pairs 1.0–1.8 m apart; robot_1, 3, 4 MOVING, robot_2 STOPPED | `crowding`, `junction_clear`; plan `[{robot_2 yield}, {"robot_1": "robot_1", "action": "cross"}, {robot_3 cross}, {robot_4 cross}]` | nulled, `proposed_plan=default:invalid_structure`: the second leg has no `robot_id` key | `m3_default` "plan absent"; chi recede 3→4 dispatched |
| 2, `b7f2641a` | 31.47 s; jam, all STOPPED at about ±0.22 m | `deadlock`, `junction_clear`; plan `3rev 4rev 1cross 2cross` | kept | `repaired`: "robot_1: cross infeasible: cross leg has no preceding yield leg"; legs `3rev 4rev 1yield 2cross`; repaired → chi order 4→3 dispatched |
| 2, `ba66a058` | 134.37 s; resolving | `congestion_detected: false`, plan null | kept | nothing dispatched |
| 3, `e83921e7` | 30.6 s; jam | `deadlock`, `junction_clear`; plan `3:"reverse (south arm)" 4:"reverse (north arm)" 1yield 2cross` | nulled, `invalid_structure`: both actions are outside the action enum | `m3_default` "plan absent"; chi 4→3 dispatched |

Every call has `finish_reason=completed`, 294–330 completion tokens (cap 2048), 368–723 thought tokens and `parse_status=valid`. The JSON was complete in all four. The offline replay through the runner's real pipeline reproduces the recorded provenance and junction phases of all three first-trigger artifacts (verified).

### 2.2 The Five Candidate Explanations

| Candidate | Verdict | Evidence |
|---|---|---|
| (i) Prompt difference | **ruled out** (verified) | The runner's B3 rebuild of each live artifact's request equals the stored live prompt byte for byte (4/4). Both grammar sentences, the release sentence and the candidate-options block are present. Against offline stimuli (`ib10L_e01`, `ib10S_e03`), only the robot-state and pairwise lines differ. No `<think>` block; JSON-only ending. |
| (iii) Truncation or backend path | **ruled out** (verified) | Same backend settings as offline (`thinking_level low`, max_tokens 2048, the same payload format); finish completed; complete JSON. |
| (ii) Scene/state difference | **cause for take 1** (verified chain, one inferred link) | The trigger fired on an approach snapshot unlike any offline stimulus (all offline stimuli are jam snapshots). Chain in 2.3. |
| (iv) Parser strictness on something harmless | **take 3 only, and only in a narrow form** (verified counterfactual) | Take 3 used the options block's own detail text as the action. Take 1's key typo is not harmless: fixed by hand it still verifies only as `repaired`. |
| (v) Sampling noise | **consistent for takes 2 and 3** (inferred) | Offline B3: 14/29 verbatim, so P(0 verbatim in 3) ≈ (15/29)³ ≈ 14 %. The invalid-action copy was 2/29 in B3 (11/69 in B and B3 together). Two nulls in three are not noise on their own, because take 1 is (ii). |

### 2.3 Take 1's Early Trigger (Verified Except Where Marked)

1. At stamp 22.567 s, one M1 scene sample (`m5_scene.jsonl`) puts robot_2 at (−1.05, 0.0), on top of robot_1 (pair 0.01 m). GT has robot_2 at about +1.05 m. The samples before and after are correct. `m1.log` holds only 6 lines, so the glitch's cause is not recorded.
2. At wall 1794697369.54 the safety monitor latches `min_distance_violation` for robot_2 and robot_1 and cancels both Nav2 goals.
3. Robot_2 stays stopped at x ≈ 0.98. Robot_1 resumes about 1 s later (GT). Why only robot_2 stayed stopped is inferred, not shown.
4. 12.06 wall-s after the latch, M5 starts the analysis: "1 robot(s) stalled >= 12.0s", robot_2, 2.73 m from goal.
5. The prompt therefore shows three robots MOVING 1.0–1.8 m apart. ER-2 answered `crowding` with a cross-heavy plan and a malformed leg. No offline stimulus resembles this scene.

### 2.4 Take 1 Unresolved (Verified From m4/m5 Logs and GT; the Geometric Reason Is Inferred)

- **Dispatched (M3 default, four phases):**
  1. recede robot_3 (0.569 m), completed;
  2. recede robot_4 (0.375 m), completed;
  3. cross: robot_1 yields to robot_2. `gate_admit` at sim 57.8 s; cleared by clearance at 90.6 s (moved 2.929 of 2.927 m);
  4. release: robot_4 and robot_1 yield to robot_3, then robot_4.
- **The release gate never cleared.** It needed robot_3 to move 2.65 m (`passer_clear_m`) from its position at admission (sim 90.6 s, y ≈ −0.87). Robot_3 drove to its goal (y = 1.67, 0.08 m short of 1.75) and stopped: about 2.54 m, and at most about 2.62 m to the goal. So the gate could never be met.
- **The fallbacks ran out of time.** Robot_4's release ended by its 120 s hold timer (sim 224 s) and robot_4 arrived. Robot_1's yield (`hold_sec` 240 from sim 90.6 s) would only expire at sim 330.6 s, past the 300 s horizon. Robot_1 stayed at its pull-off point (−0.96, 0.37) from sim 90 s to the end.
- **In takes 2 and 3** the same phases ran from a jam snapshot. The receders started about 0.22 m from the centre, the 2.65 m and 2.076 m gates cleared by clearance, and all robots arrived.
- **Relation to the model:** none. The plan was nulled, so this is the M3 default on a pre-jam geometry, the same as with no VLM. Inferred: a release clearance distance longer than the passer's remaining path to its goal can only end by the hold timer.

### 2.5 Cause and Proposed Fix (NOT Applied: This Scenario Has Used Its Two Fix Cycles)

- **Cause, by take:**
  - take 3 = a known prompt-format defect: the options block renders details as `reverse (south arm)`, and ER-2 copies them (verified);
  - take 2 = the known releasing-yield omission (verified repair reason);
  - take 1 = a perception glitch that triggered analysis on a non-jam snapshot, plus a malformed key (verified chain; the glitch's cause is unknown).
- **The one small, generic, safe fix the evidence supports** addresses take 3's class. Either option needs the owner's approval as a third cycle.
  - **(a) Prompt format.** Render the options detail so it cannot be read as an action token, for example `reverse — backs out into the south arm`, or details on their own line. Pros: no parser change. Cons: changes the B3 prompt bytes, so it needs a new offline ER-2 check (about $0.35).
  - **(b) Parser tolerance, narrowly.** Accept `"<action> (<detail>)"` only when it equals exactly an option the block offered that robot in this request, and normalise it to `<action>`. It must not be a general parenthetical strip, which would accept a contradictory arm.
- **Counterfactual for (b), take 3 (verified, offline, free):** with the two actions normalised, the plan `3rev 4rev 1yield 2cross` verifies `vlm_verbatim`, the dispatch source becomes `model`, the recede order 3→4 differs from chi 4→3, and `dispatch_matches_plan=true`. That is the demo event.
- **No tolerance is proposed for take 1's missing `robot_id` key.** Fixed by hand, that plan still verifies only `repaired` (four structural edits). Nothing proposed weakens verification, feasibility or safety.

---

## 3. Sonnet 5.5 Arm for the Intersection (Part B)

### 3.1 What Was Built

`demo_campaign/ib_sonnet/spec/` was assembled by the unchanged `common/assemble_dmc.sh ib_sonnet` into `ib_sonnet/kit/` (`kit_md5_dmc.txt` `120487a9`, `kit_md5_all_dmc.txt` `f1b5fced`). The spec files override the common files of the same name. Nothing under `common/`, `ib/`, `runtime_delta/` or the ledger was modified (verified): `ib/kit` passes `KIT_MD5 OK`, every unforked common file is byte-equal in `ib/kit`, and every bundle file in the three `ib` manifests still matches. Only the `vm/` tree files, which each later pull overwrites by design, differ in the first two manifests.

**Unchanged from `ib`:** the scene, overlay `0196f1e8` and B3 delta (effective `614beed0`), the safety floor and key line, grounding, the classifier, the take classifier and every `ib` gate.

**Changes:**

- **Backend:** `BACKEND_ID=anthropic` through fc_launch's existing switch. Models.yaml section `anthropic` = `claude-sonnet-5-5` (the id the 2026-11-15 plan-check Sonnet calls used), `between_tools`, 4 attempts, grey-image fallback after 2. **No runtime file changes**: models.yaml `aa6c4e98` and `anthropic_backend.py` `45032243` equal 68e67b5 and are now pinned in the profile.
- **Ledger and labels:** SCN_KEY stays `ib` (the same entry, take numbers continue: `next_take=4`). Labels are `ibD_sonnet55_tNN_aK`. The VM home is `~/dmc_ib_sonnet`, so the pull never brings back ER-2 bundles.
- **Key delivery.** The common kit delivers no key: it only sources the `/ws/.env` already on the VM. The design here:
  - `run_dmc.sh` checks the Mac source first (`$HOME/Documents/vgu-vlm-swarm/.env`, mode 600, exactly one `ANTHROPIC_API_KEY=sk-ant-` line). After the dead-man is armed, it pipes that one line over ssh stdin to `anthropic_key_dmc.sh install`. The key is never on an argv, never in a shell variable, never printed.
  - The install refuses unless the VM's `.env` is group/other-free. It replaces any existing Anthropic line (reported `pre_existing=1`), rewrites the file in place (owner and mode kept), and verifies one line on the host and inside `vgu_ros`. Temp files sit next to `.env` with umask 077 and are shredded.
  - Removal runs in three places:
    - `restore_dmc.sh`, first step, on every path; a failure fails the restore;
    - the dead-man, before poweroff;
    - the driver trap, verified.
  - A failed or unreachable removal writes `KEY_NOT_REMOVED_<ts>`, which blocks the next invocation.
  - **Policy for a pre-existing Anthropic line on the VM: it is removed too.** The key does not outlive the invocation. Whether one exists now is unknowable offline.
- **Probe:** `anthropic_probe_dmc.py/.sh`, a one-token Messages call (`max_tokens 1`) through the container's `/ws/.env`. Exit codes:
  - 0: 2xx and the served id equals `claude-sonnet-5-5`;
  - 3: 402, 429, or a credit-balance 400;
  - 4: any other status;
  - 5: no key or network.
  None is ever retried. The Gemini probe files are refusing stubs.
- **Cost guard:** `cost_watch.py` prices Anthropic usage at $2 / $10 per MTok, with a $0.031 reserve. The common guard would price every Sonnet call at $0.
- **Arm check (deployed loader).** The `ib` fields plus what the deployed backend factory resolves from the deployed models.yaml: `anthropic claude-sonnet-5-5 between_tools 2048 4 2`.
- **Condition gate (post-take; failure = never retried).** The `ib` checks plus:
  - fc_launch's `reasoning_backend_id: openai -> anthropic` and `starting M5 orchestrator (anthropic backend, CWD /ws)` lines;
  - M5's first-call line `Anthropic claude-sonnet-5-5 rejects`, and no Gemini line;
  - every artifact's `backend_id` = `anthropic`, served model and `reasoner_config_effective.model_id` = `claude-sonnet-5-5`, `thinking_mode` = `between_tools`;
  - the JSON-only prompt ending, and no `<think>`.
  Refusals are reported, not failed.
- **The `reasoning_extraction` refusal does not apply** (verified). The live B3 prompts end with "Write ONLY the final JSON object, with no surrounding text or markdown." and carry no `<think>` block (prompt v3.4+). The offline run below had 0 refusals in 16.
- **M5 starts with this backend (verified offline, dummy key).** M5's own `_build_default_pipeline` builds on the effective overlay with `reasoning_backend_id: anthropic` (fc_launch's rewrite), with ROS imports stubbed. It yields `AnthropicBackend` `claude-sonnet-5-5` / `between_tools` for the Reasoner AND for the stage-2 `RetreatChooser`: stage 2 is on in this overlay, so a stage-2 call also bills Sonnet, which the cost guard counts. Without the key, M5 startup raises `ANTHROPIC_API_KEY is not set`, which the probe before every take guards.
- **Per-take budget travel.** The VM re-sources the profile and never sees the Mac's environment, so the budget is passed explicitly as `start_chain_dmc.sh` argument 6 (`EP_BUDGET_OVERRIDE`; forked `start_chain_dmc.sh` and `chain_dmc.sh`). The dry test proves it: with `DMC_EP_BUDGET_SEC` unset, a 2000 s deadline refuses the profile's 3000 s take, and the override 1500 admits it.
- **Key temp copies.** `remove` also sweeps and verifies any `.env.key.*` / `.env.dmc.*` left next to `.env` by a killed install. HUP, INT and TERM run the cleanup.
- **The real Mac key line** passes both the driver's and the install's format checks (counted, not printed).
- **Not possible without a runtime change, so not done.** M5 logs no startup line naming the backend or model. The backend and model are asserted from fc_launch's lines, M5's first-call line, the deployed-loader resolution and every artifact.

### 3.2 Dry Test (Verified by Running)

`cd ib_sonnet/kit && MIN_MAC_FREE_KB=3000000 bash test_dry_dmc.sh` ends with `TEST_DRY_DMC ib OK`. The name is the ledger key `ib`. All cases OK:

- **1:** syntax and kit md5; `test_key_dmc.sh` (install, replace and remove byte-exact; refusals; mode kept; container count; no temp files; leftover temp copies swept; key never printed); no VM path calls the Gemini probe.
- **6:** also the budget travel (above).
- **2–6:** the `ib` cases. The take table reads `live Sonnet 5.5 claude-sonnet-5-5`; labels are `ibD_sonnet55_tNN_aK`.
- **7:** the real ER-2 take-3 bundle FAILS exactly `a_backend_anthropic, a_served_model, a_rce_model, launcher_line, launcher_line_2, m5_line_3, m5_line_absent`, and 27 checks pass.
- **9:** fc_launch DRY_RUN switches to `anthropic`.
- **10:** driver paths:
  - key install after the dead-man and before the probe;
  - verified removal in the trap, also after a probe abort;
  - `KEY_NOT_REMOVED` written and blocking the next invocation;
  - missing, two-line and 644 key sources refused before any start;
  - the dummy key never printed;
  - `DMC_EP_BUDGET_SEC=1500` gives a need of 3300 s and is forwarded to `start_chain` as argument 6;
  - the ER-2 kit's cases unchanged.
- **12b:** the fake-VM restore removes a key line from `.env` (mode 600 kept).
- **12c:** a Sonnet re-labelled copy of take 3 PASSES all 34 checks. Without the Anthropic line exactly `m5_line_3` fails; with one ER-2 artifact exactly the 3 backend/model checks fail.

The 5 GiB Mac floor was lowered for the test only: the Mac had 6.85 GB free, with the convoy run recording at the time.

### 3.3 Probe (Verified by Running, Once, From the Mac)

`PROBE http=200 verdict=OK latency_ms=838 model=claude-sonnet-5-5`, rc 0. The no-key case gives rc 5. Cost is under $0.0001.

### 3.4 Offline Sonnet Check (Verified; Pre-Registered in `b103ff4`)

Full table: `docs/reports/2026-11-15-vlm-order-channel-plan-check.md` section 11.

- n = 16 B3 calls on the plan-check stimuli; 16 answered, 0 refused, 16 structurally valid.
- 11 `vlm_verbatim`; 6 verbatim with recede order ≠ chi; 1 of those 6 executed as written.
- Yielder gap: 8 of 10 verbatim pair plans name robot_2 as yielder, and in 6 of them dispatch yields robot_1. That disqualifies 5 of the 6 order changes under the classifier rule (a yielder-swapped plan is M3-default).
- VLM-driven per first trigger: 1/15 (6.7 %); over 2 takes about 13 % (inferred). ER-2 B3 offline: 7/27.
- Spend: $0.216 at list ($0.2705 ledger units). When this section was written, the spend was not yet booked, because the convoy run was writing the ledger. Rev 5: it is booked, ledger row `spend ib offline_sonnet_b3 0.2705` at 2026-11-15T02:10:11Z (section 3.6).

### 3.5 Go/No-Go and Launch

- **The three section 10.1 criteria, Sonnet B3:**
  - (a) met: 16/16 valid;
  - (b) mostly not met: the yielder gap swaps 6 of 10 verbatim pair plans;
  - (c) the order differs in 6/15, but only 1/15 qualifies.
- **Recommendation: no-go** for Sonnet takes if the aim is a "VLM-driven execution" video. With about 13 % over 2 takes, the likely result is two M3-default takes, which cost about 2850 s of the remaining 3986 s. Running them anyway is the owner's call.
- **A comparison, not a recommendation to act:** ER-2 B3 plus the narrow take-3 fix (section 2.5) would have been a demo event on take 3. That needs a third fix cycle and an owner decision.
- **Admission as built REFUSES.** The registered need (prep 900 + take 3000 + teardown 900 = 4800 s) exceeds `ib`'s remaining 3986 s (verified with `ledger_dmc.py admit` on a ledger copy).
- **Measured one-take invocations:** prep 269–281 s, take 1144–1178 s, teardown 125–165 s; 1559–1606 s in total (1849 s with one bring-up retry).
- **Owner-declared deviation that fits 2 takes:** take budget 1500 s (27 % over the longest measured take), in ONE invocation with `--episodes 2`. Need 3300 s is ADMITTED (verified on the ledger copy: `next_take=4 valid=3 aborts_left=2`).
  - The chain admits take 2 only if it can end before T0 + 3086 s. That is expected at about T0 + 1480 s, with about 100 s of margin.
  - A bring-up retry in take 1 makes the kit refuse take 2 rather than overrun.
  - Two one-take invocations do not fit at any budget the registration allows.
- **Launch command (only after the owner's go, the convoy run finished, and the VM verified TERMINATED):**

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/ib_sonnet/kit && DMC_EP_BUDGET_SEC=1500 bash run_dmc.sh --episodes 2
```

- **Would stop a launch:**
  - the owner's no-go, or no approval of the budget deviation;
  - the VM not TERMINATED (convoy in progress);
  - Mac free space under 5 GiB (6.85 GB before the convoy's recordings land);
  - any `RESTORE_FAILED_*`, `VM_NOT_STOPPED_*` or `KEY_NOT_REMOVED_*` marker;
  - an unbooked offline spend (book first, below);
  - the VM's `.env` not mode 600, or a pin mismatch for models.yaml or `anthropic_backend.py` (the kit refuses either fail-fast);
  - Anthropic billing or quota (probe rc 3).
- **Video caption** for a VLM-driven Sonnet take: the section 10.2 sentence with "The VLM (Claude Sonnet 5.5)". Labels are `ibD_sonnet55_t04_a1` and `ibD_sonnet55_t05_a1`.

### 3.6 Ledger Booking (Done 2026-11-15T02:10:11Z)

When this section was written, the booking was owed, because the convoy driver was writing the ledger. Rev 5: the ledger now holds the row `spend ib offline_sonnet_b3 0.2705` (note "Sonnet B3 offline check") at 2026-11-15T02:10:11Z. The command was:

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/ib_sonnet/kit && python3 ledger_dmc.py book-spend ib offline_sonnet_b3 0.2705 "Sonnet B3 offline check, 16 calls + 1 probe (ledger units)"
```

---

## 4. Verified and Inferred

| Claim | Status |
|---|---|
| Live prompts equal the offline B3 rendering for the same snapshot | verified (byte-equal re-render, 4/4) |
| Raw outputs, parser verdicts, provenance, dispatch | verified (bundle artifacts, m5/m4 logs, offline replay fidelity 3/3) |
| Take 3 would have been the demo event with the actions normalised | verified (offline replay, free) |
| Take 1's early trigger came from a one-sample M1 identity glitch | verified from `m5_scene.jsonl`, m4 and m5; the glitch's cause is unknown |
| Why robot_2 alone stayed stopped | inferred |
| Take 1's release gate was unreachable (2.65 m against at most 2.62 m left to the goal) | verified from m4 and GT; the general reading is inferred |
| Sonnet kit dry test, probe, offline counts | verified by running |
| 13 % over 2 Sonnet takes, about 2850 s for 2 takes | inferred |

---

## 5. Convoy Counterflow Live Takes 1–3 (ER-2; Added 2026-11-15)

**Status.** Illustrative, not controlled evidence. These takes preview the registered convoy experiment's VLM arm (Arm A of v7f `docs/superpowers/specs/2026-11-14-convoy-live-resolution-experiment.md`). They are not part of that experiment and must not be used to change its registered rules (campaign spec section 4.2).

**Setup.** Kit `demo_campaign/cv/kit`, overlay `cvl_l2on.yaml` `7e3ab552`, legacy grounding `cvl_convoy_legacy.yaml`, inert delta `4843a776`, live `gemini-robotics-er-2-preview`, seed 42, 260 sim-s horizon, both recorders on. Sources: `cv/runs/<label>/`, `cv/driver_cv_*.log`, `cv/MANIFEST_*.md5`. The convoy scorer `score_cvl.py` (v7f kit) was also run offline on the three bundles (`--no-harness-check`, output outside the bundles).

### 5.1 Takes (Verified From the Bundles)

| Take (label) | Wall (UTC) | Resolved | Label | Provenance (12 decisions) | Executed | GT min pair | Safety | Recording frames (annotated / raw) | Manifest md5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 (`cvD_t01_a1`) | 00:44:55–01:04:47 | no, 0/4 | Unresolved failure | 1 `vlm_verbatim`, 3 `repaired`, 8 `m3_default` | t 27.8 s: robot_2 `yield` (backup 0.903 m to park x 1.124, lateral 0.36), robot_1 escort 1.898 m; 11 later: `temporary_wait` 8 s | 0.343 m | floor stops 0, GT contact 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 161 517 | 1151 / 2083 | `92639ca1` (72 files) |
| 2 (`cvD_t02_a1`) | 01:17:36–01:37:48 | no, 0/4 | Unresolved failure | 1 / 7 / 4 | t 28.9 s: robot_1 `yield` (backup 0.993 m to park x −1.124), robot_2 escort 1.904 m; 11 later: `temporary_wait` 8 s | 0.262 m | 0, 0; 175 043 | 1166 / 2054 | `c2356be8` (72 files) |
| 3 (`cvD_t03_a1`) | 01:45:39–02:05:26 | no, 0/4 | Unresolved failure | 1 / 5 / 6 | t 29.3 s: robot_2 `yield` (backup 0.88 m to park x 1.124), robot_1 escort 1.807 m; 11 later: `temporary_wait` 8 s | 0.274 m | 0, 0; 161 242 | 1173 / 2022 | `682c9a59` (72 files) |

- Times are the chain's START and END lines. Every `STARTUP_CHECK`, `VIDEO_VERIFY` and condition gate passed (`GATE OK`, `RESTORE OK`).
- Model calls: 12 per take, each 1 attempt, `finish_reason=completed`, `parse_status=valid`, 0 refusals; latency 6.7–11.5 s. Estimated spend $0.0898, $0.0953 and $0.0910; tokens 265 830, 270 352 and 266 938.
- Provenance over the 36 decisions: 3 `vlm_verbatim`, 15 `repaired`, 18 `m3_default`. The live-run agent's summary said 16 and 17; the artifacts give 15 and 18.
- The GT minimum pair is the robot_1–robot_2 standoff gap at 25.7–29.7 s, before any dispatch. It is not the separation of the final jam (0.41–0.45 m).
- The many `min_distance_violation` lines are the latched stop of the jammed robots, not contacts.
- Label: the classifier (`take_class_dmc.py`) labels intersection takes only. These are Unresolved failure under the section 7 rule: 0 of 4 arrived.

### 5.2 What the First Yield Achieved (Verified From m4/m5 and GT)

**Takes 1 and 3: robot_2 yields, robot_1 passes.**

1. Robot_2 backed out and pulled off to (1.13, −0.38), its park point (park x 1.124, lateral 0.36).
2. M4 admitted robot_1 at sim 53.8 / 55.1 s (`crossing_chain gate_admit`). Robot_1 crossed x = 0 at 54.9 / 55.3 s.
3. 4.2 and 9.0 wall-seconds before that admission, M5 logged `start delay elapsed, base mission released robots=['robot_3', 'robot_4']`, 119.7 wall-s after its session line. The first command had not named them, so nothing held them. They drove their own Nav2 goals through the gate behind robot_1, crossing x = 0 at 65.0 s and 68.6–68.9 s.
4. By about 75 s all four stood east of the gate: robot_1 (1.61–1.71, 0.00), robot_3 (1.21–1.31, +0.17–0.19), robot_4 (0.81–0.83, −0.08 to −0.10), robot_2 parked. GT pairs robot_2–robot_4 0.42 m and robot_1–robot_3 0.44 m are below M4's `min_distance_m` 0.45. Only robot_1+robot_2 was an exempt pair, and it was cleared at `gate_release … reason=hold_timer` (98.8 / 100.1 s).
5. No robot moved again from about 75 s to 260 s. Take 1's escort ended `FAILED escort timed out in phase drive`, with robot_1 stopped 0.07 m short of its escort end.

**Take 2: the model named robot_1 as the yielder.** Robot_1 backed west to (−1.13, +0.37), and robot_2 was escorted west across x = 0 (56.5 s). The released robot_3 and robot_4 drove east to meet it. From about 70 s, robot_2 (−0.90, 0.01), robot_3 (−1.31, 0.00) and robot_4 (−1.69, −0.16) stood 0.41–0.42 m apart, west of the gate, until the end. The scene file names this as the censored alternative ("yielding robot_1 instead escorts robot_2 west … a latch").

**Pre-stated.** The scene file (`convoy_counterflow_slip.yaml` header) says: "Any answer that omits the queued robots ends in the permanent bystander latch". The registration lists, as something only the VM can show, "whether [a live ER-2] names `robot_3` and `robot_4`" on the first trigger. Here the answer is no, in 3 of 3: the scorer's `late_dispatch=True` in all three. The first dispatch naming both came 355–831 wall-s after the session start, long after the latch.

### 5.3 The First Decision (Verified From the Artifacts)

- All three answers: `deadlock`, `yield`, `involved_robots` [robot_1, robot_2]. Takes 1 and 3 name robot_2 as yielder; take 2 names robot_1. The plans give robot_3 and robot_4 `continue` (takes 1 and 3) or `wait` (take 2). Take 3's reasoning mentions that "robot_3 and robot_4 are also queueing from the left", but still leaves them out of the resolution.
- Plan verification accepted takes 1 and 3 as `vlm_verbatim` with the `continue` legs. Legacy grounding commands only the robots it names: the yielder and one passer with a 120 s linked wait.
- What the prompt showed (verified text): robot_3 and robot_4 `STOPPED` at spawn, 1.78–2.70 m from the standoff pair, with goals east of the gate. Nothing says they are held back or when they will start. The guidance says "Two robots that are stopped but farther apart than ~0.5 m … are NOT deadlocked" and "do not assume intentions beyond what is stated". Whether this steered the model is inferred.
- **Smoke comparison (scripted oracle, Arm C, `cvL_e01_armC_a1`, 2026-11-14).** Same overlay md5 `7e3ab552` and the same M4 startup line. Its decision named all four robots, `yield` robot_2 and order [robot_1, robot_3, robot_4, robot_2]. Grounded as yield robot_2 with linked waits for robot_1, robot_3 and robot_4, it executed `gate_admit` in order robot_1, robot_3, robot_4 and resolved 4/4: arrivals 59.1, 100.2, 141.9 and 163.9 s after t0, floor stops 0. It is n = 1 and was not owner-accepted, so it shows that the scene can be resolved, not a rate.

### 5.4 Why Every Later Proposal Became a Wait (Verified; Code at 68e67b5)

The legacy grounder and plan verifier at 68e67b5 (equal to v7f's reasoning code) were replayed offline on each artifact's own scene snapshot. They reproduce all 36 dispatched commands (36/36).

| Mechanism (33 later decisions) | Take 1 | Take 2 | Take 3 |
|---|---|---|---|
| Yield or reverse refused by the corridor same-side check ("both robots outside the corridor on the same side") | 9 | 0 | 3 |
| Yield refused by the first-passer check ("first passer … is not the passer nearest the yielder") | 1 | 5 | 2 |
| No legacy template: `junction_clear`, `convoy` or `priority_override` → 8 s wait fan-out | 1 | 6 | 6 |

Take 2's two `convoy` decisions are aliased to the ordered yield and refused by the first-passer check, so they sit in that row. Plan verification also substituted every `cross` leg without a preceding `yield` leg. Plans more than 4 edits from a valid one fell back to `m3_default` ("repair distance exceeds bound 4").

**Are the refusals correct?**

- **Same-side check.** Its condition holds: in takes 1 and 3 every robot is past the corridor mouth (|x| > 0.5) on the east side. Its stated reason, "a reverse would traverse it", does not literally apply in take 1. Robot_2 already sits at its park coordinate (x 1.13 against 1.124), so the template would only have nudged it by the minimum backup (from code). Had it not refused, the template would have escorted robot_4 east into robot_3 and robot_1, which are non-exempt partners (inferred). The check is coarse, but it is not what kept the scene jammed.
- **First-passer check.** Correct by its rule. For example, take 1's four-robot answer at 219.5 s, `yield` robot_2 with order [robot_1, robot_3, robot_4], put robot_1 first while robot_4 was nearest to robot_2 (0.42 m against robot_1's 0.69 m). It was the oracle-shaped answer, given about 190 s after the first trigger, when every yield was refused anyway.
- **No template.** By design: legacy mode has no feasibility bands for a `junction_clear` sequence (`command_grounder.py`, legacy branch).

**Could any strategy have been grounded? (verified offline for grounding).** On one post-latch snapshot per take, 76 hypothetical decisions were grounded through the pinned legacy grounder:

- every yielder/passer pair;
- every four-robot yield with every crossing order;
- every reverse pair;
- `reroute`, `temporary_wait`, `convoy`, `priority_override` and `junction_clear`, each with every lead robot.

72 of 76 became waits. Only `reroute` (4 of 76) produced motion: one robot's Nav2 goal is re-sent (this scene declares no waypoints) while the others wait 15 s. Inferred: `reroute` is not an M4-exempt action (`exempt_actions=reverse,yield`), and every robot stood within 0.45 m of a non-exempt neighbour, so the latch would have held it. The model never proposed `reroute`.

**Harness ruled out (verified).** Gates, video verify and condition gate passed; all 36 calls were complete and valid; the offline replay reproduces every dispatched command.

### 5.5 Conclusion and Proposed Fixes (NOT Applied)

**Conclusion.**

- **Primary cause: the first decision's content (model limitation; verified).** In 3 of 3 takes ER-2 named only the standoff pair and left the queued platoon out. The scene is built so that such an answer cannot resolve: the scene file pre-states the bystander latch, the scripted oracle decision resolved it, and GT shows the latch in all three takes.
- **Contributing: information and verification design (verified text; the effect on the model is inferred).**
  - The prompt carries no hold-back state.
  - Its guidance reads distant stopped robots as not involved.
  - Plan verification accepts `continue` for robots whose goals lie across the gate.
  - Legacy grounding commands only the robots the decision names.
- **No recovery: a grounding and strategy-coverage limitation (grounding verified; the M4 outcome inferred).** Once four robots latch on one side of the gate, no strategy in the legacy vocabulary grounds a motion that the latch allows.
- **Not a scenario defect.** The scene behaves as designed and resolves under the oracle decision. It does make the first decision single-shot.
- **Not a harness issue.**

**Fixes.** Each one changes the registered convoy experiment's Arm A, so it is an owner decision: either a registration amendment before Arm A runs, or nothing.

- **(a) Prompt or kit, small.**
  - Change: show the hold-back state on the held robots' state lines (for example `held; base mission starts in ~N s`), or add one guidance sentence: robots queued behind a standoff whose goals lie past it belong in `involved_robots` and `crossing_order`.
  - Cost: it changes the registered prompt bytes and needs an offline ER-2 check on the recorded first-trigger snapshots (about 12 calls).
  - What it tests: whether the model can do it when it is told.
- **(b) Grounding, medium (M3 change).**
  - Change: when grounding a corridor yield, hold every uncommanded robot whose goal lies across the corridor with a linked wait, and append it to the crossing order nearest-first, which is what the oracle command does. Alternatively, plan verification could refuse `continue` for such robots.
  - What it gives: the outcome no longer depends on the model naming the platoon.
- **(c) Recovery, large (architecture).**
  - Change: a post-gate cluster template, for example release in goal-distance order with scoped exemptions, or derived-mode grounding for this scene.
  - What it gives: it addresses the 33 dead waits, not the cause.

### 5.6 Video (Take 1)

- **File.** v7g `data/demo/campaign/cvD_t01_a1_panel.mp4` (git-ignored), md5 `82431944`. Beside it: transcript, five stills and `cvD_t01_a1_panel.md5`. Renderer v7g `5198c0b`, which adds `render --caption`.
- **Why take 1.** Takes 1 and 3 show the same majority pattern. In take 1 the mandated caption sentence is literally true for 10 of the 11 later triggers: 9 same-side and 1 first-passer refusal, against 5 of 11 in take 3 (5.4). It is also the tie-break default.
- **Camera: annotated stream.** The guide has no raw-versus-annotated recommendation; its camera example and the campaign runbook (section 8) both use `/perception/annotated_frame`, which is also the image the model receives.
- **Captions** (outside the terminal): "Unresolved failure — take 1 of 3 (selected take)"; the model `gemini-robotics-er-2-preview`, Layer 2 on, 0 of 4 arrived; "First decision: the model's yield was executed as named; all 11 later proposals ran as 8 s waits (10 refused by grounding checks, 1 had no legacy template)"; and the section 7 disclosure lines.
- **Checks (verified).**
  - ffprobe: H.264, 1920x1080, 24 fps, yuv420p, 6559 frames, 273.29 s. The full take, not cut.
  - Time map: log-to-sim alignment within 0.29 sim-s at 92 anchors.
  - The first `dispatch` line maps to sim 30.032 s; M4's own `handoff guard … sim_t=30.000` comes 12 ms later. Error about 0.03 sim-s.
  - The camera's burned-in clock against the caption clock: 29.90 / 30.03 s at the first decision (0.13 s, one frame step at about 4.7 frames per sim-s), 163.03 / 163.06 s mid-take.
- **Known gaps.**
  - The left pane is blank before sim 14.8 s (first recorded frame) and after 259.97 s (last frame), so the end still is blank.
  - The fixed filter does not match M5's `yield refused … reason=` lines. On screen the later triggers show as `provenance=m3_default reason=repair distance exceeds bound 4` and `action=temporary_wait`, not the geometric reason. The caption states the reason; the filter was not widened.

### 5.7 Verified and Inferred

| Claim | Status |
|---|---|
| Per-take outcomes, provenance counts, executed commands, safety counts, frames, manifests | verified (bundles, driver logs, offline scorer) |
| The first yield ran as named; robot_3/robot_4 were released uncommanded and the scene latched at about 75 s (takes 1 and 3) and about 70 s (take 2) | verified (m4/m5 lines, GT) |
| The model named only the standoff pair in 3 of 3 first decisions | verified (artifacts) |
| The prompt carried no hold-back state | verified (prompt text); its effect on the model is inferred |
| Refusal mechanisms for the 33 later decisions | verified (artifacts; offline replay 36/36) |
| The same-side refusal's stated reason did not literally apply in take 1 | verified from code and snapshot; that an unrefused yield would still have latched is inferred |
| No legacy strategy grounds motion except `reroute` | verified offline (76 decisions × 3 snapshots) |
| `reroute` would have been held by the M4 latch | inferred |
| The scene is resolvable with the oracle decision | verified on one smoke episode, not owner-accepted |

### 5.8 Follow-Up: Held-Robot Prompt Check, No-Go (Added 2026-11-15, Rev 6)

This tests fix option (a) of 5.5 offline. Full report: `docs/reports/2026-11-15-convoy-held-robot-prompt-check.md`. The check was pre-registered in `4ba2175`, and the condition is `prompt_held_robot_state` (`2f83faf`, default off).

- **Calls.** 44 ER-2 calls, 22 per condition ($0.2990 at list price), on the four convoy first-trigger snapshots: takes 1–3 and the scripted smoke. Control C is the recorded prompt. Treatment H marks robot_3 and robot_4 `start_pending=true` and adds one factual note.
- **Result.** In both C and H, 0 of 22 answers grounded into the smoke's four-robot sequence (yield, linked waits for the other three, all three in the crossing order). Every answer named only robot_1 and robot_2 in `involved_robots`, so the model still names only the pair. Under H, the plans gave both queued robots `wait` in 16 of 22 answers, against 2 of 22 under C. Legacy grounding commands only the robots the decision names, so all 44 grounded commands name robot_1 and robot_2 only.
- **Verdict: no-go** under the pre-registered rule, which counts the three live takes only: P = 0 of 18 under both C and H. Go needed P of at least 9 of 18 under H and H − C of at least +6. The four-robot structure appeared in 0 of 18 treated answers, so the point estimate is about 0, with a rule-of-three 95 % upper bound of about 17 %. The report therefore puts a live retake's chance of resolving 4 of 4 through the first decision well under 17 %.
- **No convoy retake was run.** The convoy rows of this report are unchanged.

---

## 6. Head-on With Obstacle, Take 1 (ER-2; Added 2026-11-15)

**Status.** Illustrative, not controlled evidence. n = 1: one valid take, so no rate or comparison can be drawn from it. It is not pooled with experiment data.

**Setup.** Kit `demo_campaign/ho/kit`, scenario `head_on_asymmetric_w0p2_eopen_bshort_o0`, overlay `ho_w0p2_bshort_on.yaml` `3929a087` (obstacle text on, feasibility gate on), inert delta `4843a776`, live `gemini-robotics-er-2-preview` (temperature 0.6, thinking `low`), seed 42, 300 sim-s horizon, both recorders on. Sources: `ho/runs/hoD_t01_a1/`, `ho/driver_ho_20261115T021253Z.log`, `ho/MANIFEST_20261115T021253Z.md5`. The take classifier `take_class_dmc.py` labels intersection takes only; I did not run it. The label below comes from the spec section 7 rule that a yielder-swapped plan is M3-default and from the live-run agent's reading.

### 6.1 The Take (Verified From the Bundle)

| Item | Value |
|---|---|
| Take (label) | 1 (`hoD_t01_a1`), the only valid take; 0 bring-up aborts |
| Wall (UTC) | 02:17:47–02:32:12 (chain START and END lines); the VM was stopped and verified TERMINATED at 02:34:50 |
| Resolved | yes, 2 of 2 arrived (GT rule `distance_to_goal < 0.3 m`: robot_1 at sim 112.5 s, robot_2 at 136.1 s; M5 `arrived at base goal` lines at about 125.2 s and 142.3 s on the mapped sim clock; both 0.07 and 0.08 m from goal) |
| Label | M3-default resolution (grounder-corrected) |
| Model calls | 3 billed: 2 decisions plus one stage-2 retreat-position call in decision 2; each 1 attempt, `finish_reason=completed`, `parse_status=valid`, 0 refusals; decision latency 7.1 s and 8.1 s; 32 532 tokens; est. $0.0154 |
| GT closest pair | 0.2176 m at sim 22.3 s (see 6.3) |
| Safety | GT contact rows 0 (robot-robot 0, robot-static 0), but both fields are hard-coded empty (`isaac/vgu_sim/acceptance_logging.py:99-100`). Robot-robot is supported by the GT closest pair (6.3). Robot-static is not logged; the section 8.7 recompute gives a minimum chassis-to-box gap of 0.0445 m (barrier block) and 0.098 m (`blocker_west`). Hard-floor stops 0 (floor 0.20 m); `min_distance_violation` stop lines 3352 (M4's 0.45 m latch, not the floor) |
| Recording frames | 3536 annotated (12 segments) / 2919 raw (10 segments); frame maps decoded per frame |
| Manifest md5 | `31c7a4e580dc799fb385e218628f29f9` (64 files) |

### 6.2 The Two Decisions (Verified From `decisions/*.json`, m5 and m4 Logs)

| | Decision 1 (`4de32642`) | Decision 2 (`f40c0537`) |
|---|---|---|
| Scene stamp / dispatch (sim s) | 26.7 / 29.6 | 50.6 / 56.9 |
| Scene | both STOPPED, 0.22 m apart, facing each other | both MOVING again, 0.97 m apart (the second standoff began about 52 s) |
| Model answer | `deadlock`, strategy `reverse`, `yield_robot` null | `deadlock`, strategy `yield`, `yield_robot` robot_1, `crossing_order` robot_2 then robot_1 |
| Grounding gate | none needed (no yielder named) | `yield re-grounded request=f40c0537… from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible` (`degradations=['yield_robot=regrounded']`) |
| Dispatched | `reverse` to robot_1 and robot_2, backup 1.3 m, provenance none | `yield` to robot_2 (backup 1.312 m, pull-off lateral −0.36 m, retreat point (1.789, 0.36)); `temporary_wait` 120 s to robot_1 |
| Outcome | commands resolved `completed`; the pair separated to 2.5 m, then re-approached (GT 0.28 m at about 52.5 s) and M5 re-triggered; failure context "reverse completed 17 s ago; congestion re-detected" | `crossing_chain gate_admit` (robot_1 passer, sim_t 85.6), `gate_release reason=clearance` (sim_t 118.2); both robots arrived |

- The scenario's oracle yielder is robot_2. Robot_1 had 0.70 m of retreat room against 1.08 m required, so the model's choice was infeasible.
- The prompt in decision 2 carried the obstacle text (obstacle_1, centre (−1.85, 0.00)) and the failed `reverse`. Robot presentation order `id_desc`.
- The stage-2 call picked retreat letter A, which mapped to candidate label B; M3 dispatched `retreat_choice` B (lateral −0.36 m). That step is a second model-driven input, but it acts on the gate's already-swapped yielder.

### 6.3 Closest Pair 0.2176 m (Verified From GT)

- It occurred at GT sim 22.3 s. That is during the first standoff, about 7 s before decision 1 dispatched and before any command ran. The robots had been driving toward each other under Nav2 and stopped nose to nose (GT 0.2176–0.2181 m from 22.3 to 25 s, both at speed 0).
- It is above the hard floor (0.20 m) by 0.0176 m. No contact was logged and no floor stop occurred. (Rev 6: "no contact was logged" carries no weight, because the GT contact fields are hard-coded empty. The centre distance of 0.2176 m is the evidence.)
- The second standoff reached 0.2829 m at 52.5 s, also before its dispatch. The pair was within 0.45 m again at 100.7–105.9 s while robot_1 passed the parked robot_2, an M4-exempt pair under the yield.
- The `min_distance_violation` lines are M4's 0.45 m latch holding the stopped robots, last logged at wall 258.99, about 0.3 s after decision 2's dispatch.

### 6.4 What This Take Shows

- The model's strategy was used: `reverse` in decision 1 and `yield` in decision 2 were both dispatched as the model named them.
- The model's choice of yielder in decision 2 was infeasible (robot_1 lacked retreat room). The grounding feasibility gate corrected it to robot_2, which matches the oracle.
- The resolution is therefore grounder-corrected, not VLM-driven. The label is M3-default resolution under the section 7 rule. Without the gate, the dispatched yield would have sent robot_1 into 0.70 m of room; what that would have done is not shown by this take.
- Decision 1's `reverse` did not clear the scene: the robots drove back together. That is a fact of this single take, not a rate.

### 6.5 Video

- **File.** v7g `data/demo/campaign/hoD_t01_a1_panel.mp4` (git-ignored), md5 `2aa6534a`, 6.8 MB (no `_small` copy needed). Beside it: transcript, seven stills (start, call, dispatch, decision 2, mid, arrival, end) and `hoD_t01_a1_panel.md5`. Renderer v7g `feat/demo-panel-renderer`, same arguments as the convoy video.
- **Left pane.** Real camera recording, `/perception/annotated_frame`, all 12 segments, per-frame decoded time map.
- **Captions** (outside the terminal): "M3-default resolution (grounder-corrected) — take 1 of 1"; the model and "2 of 2 robots arrived"; "Decision 2: the model chose robot_1 to yield; the feasibility gate swapped it to robot_2 (robot_1 lacked retreat room)."; "Illustrative demo, not controlled experimental evidence. Single take (n = 1); the resolution is grounder-corrected, not VLM-driven."
- **Checks (verified).** ffprobe: H.264, 1920x1080, 24 fps, yuv420p, 1825 frames, 76.04 s, the full take, not cut. Time map: 17 anchors within 0.28 sim-s. The camera's burned-in clock against the caption clock: 29.50 / 29.57 s at decision 1 (0.07 s) and 56.60 / 56.87 s at decision 2 (0.27 s).
- **Known gaps.**
  - The fixed filter does not match M5's `yield re-grounded` line. On screen decision 2 shows `strategy=yield involved=robot_1,robot_2`, then `dispatch … robot=robot_2` with `action=yield` and `robot=robot_1` with `action=temporary_wait`. The swap is visible only through the dispatched robots and the caption. The filter was not widened.
  - The left pane is blank before sim 11.2 s (first recorded frame).

### 6.6 Verified and Inferred

| Claim | Status |
|---|---|
| Decisions, gate swap, dispatch, outcomes, arrivals, safety counts, closest pair, manifest md5 | verified (bundle artifacts, m4/m5 logs, GT, driver log) |
| Label M3-default resolution (grounder-corrected) | verified against the section 7 rule; the classifier was not run (intersection only) |
| Without the swap the take would not have resolved | not shown (inferred only) |

---

## 7. Intersection Live Takes 4–5 (ER-2, B3; Added 2026-11-15)

**Status.** Illustrative, not controlled evidence. Takes are never pooled with experiment data. Same kit and configuration as takes 1–3 (section 1): `demo_campaign/ib/kit`, effective overlay `614beed0` (B3), delta `5c7973d3`, live `gemini-robotics-er-2-preview` (temperature 0.6, thinking `low`), seed 42, 300 sim-s horizon, both recorders on. Each take was a one-take invocation run after the wall-share amendment (registration section 10.7). Sources: `ib/runs/ibD_t04_a1/`, `ib/runs/ibD_t05_a1/`, `ib/take4_stdout.log`, `ib/take5_stdout.log`, `ib/MANIFEST_20261115T024528Z.md5`, `ib/MANIFEST_20261115T031339Z.md5`, `take_class_dmc.py`.

**Take plan deviation.** Section 10.5 plans up to 3 ER-2 takes, then up to 2 Sonnet 5.5 takes only if none is VLM-driven. Takes 4 and 5 ran on the ER-2 kit, not the Sonnet arm (section 3). When this section was written, the registration did not record that choice. Rev 5: it is now recorded in registration section 10.8 (2026-11-15).

### 7.1 Takes (Verified From the Bundles)

| Take (label) | Wall (UTC, `fc_launch`) | Resolved (GT rule `distance_to_goal < 0.3 m`, first sim s) | Label (`TAKE_CLASS`) | Provenance | Model plan (legs) | Dispatched recede order | Default (chi) order, computed offline | GT closest pair | Safety | Recording frames (annotated / raw) | Manifest md5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 (`ibD_t04_a1`) | 02:50:23–03:09:22 | yes, 4/4: robot_2 93.0, robot_3 113.3, robot_4 129.7, robot_1 144.1 | M3-default resolution | `repaired` (robot_1 `cross` → `yield`: "cross leg has no preceding yield leg to release it") | `3rev 4rev 1cross 2cross` | robot_3, robot_4 (`dispatch_order_source=chi`) | robot_3, robot_4 | 0.308 m (robot_2–robot_3, sim 28.2 s, before any command) | floor stops 0, GT contacts 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 10034 | 1573 / 2024 | `b7e7a6bf` (54 files) |
| 5 (`ibD_t05_a1`) | 03:31:24–03:50:34 | yes, 4/4: robot_2 95.1, robot_4 115.3, robot_3 131.9, robot_1 146.4 | **VLM-driven execution** | `vlm_verbatim` (0 edits) | `3rev 4rev 1yield 2cross` | robot_3, robot_4 (`dispatch_order_source=model`) | robot_4, robot_3 | 0.329 m (robot_1–robot_4, sim 27.9 s, before any command) | floor stops 0, GT contacts 0 (robot-robot only, from the GT min pair; see Rev 6 safety scope); `min_distance_violation` lines 9593, `stale_pose_unsafe` 2 | 1502 / 2122 | `0d2300c1` (57 files) |

- Every `VIDEO_VERIFY` was OK, every `STARTUP_CHECK` OK, every condition gate passed (`COND arm=A … failed=none`), `RESTORE OK`, VM TERMINATED (verified) after each.
- Model calls: take 4 two (the jam decision `858a783c` at stamp 30.93 s and a no-congestion call `da922782` at 132.4 s), est. $0.0115; take 5 three (`510f79e2` at 20.27 s, no congestion; `df397030` at 30.33 s, the jam; `bc712975` at 133.97 s, no congestion), est. $0.0180. Each 1 attempt, `finish_reason=completed`, `parse_status=valid`, no refusal, no stage-2 call.
- `COUNTERFACTUAL executed_differs_from_m3_default`: take 4 False, take 5 True.
- Take 4's model order (3→4) happened to equal chi's (3→4, chi 0.941 vs 0.958), so even without the repair the dispatch would not have differed from the default.
- Ledger after take 5 (driver output): `ib` 8239 s of 12600 s, spend $2.3335, valid 5, bring-up aborts 1/3; campaign 14370 s of 43200 s, $2.629 of $10.
- The GT closest pairs (0.31–0.33 m) are the standing jam separation, before any command. The `min_distance_violation` lines are M4's 0.45 m latch holding the jammed robots, not contacts.

### 7.2 Take 5 Adversarial Verification (Part A)

Each check below was run from the raw bundle files, not from the classifier, except where marked.

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Raw model output equals the parsed plan | **pass** (verified) | `raw_text` (fenced JSON) parsed with `json.loads` equals `decision` on every key; `proposed_plan` = `[robot_3 reverse, robot_4 reverse, robot_1 yield, robot_2 cross]` = `plan.legs`. Strategy `junction_clear`, type `deadlock`, `yield_robot` null. |
| 2 | Verification accepted it with no repair | **pass** (verified) | `plan.provenance=vlm_verbatim`, `edits=[]`, `rejection_reason=null`, `order_equivalent=true`, `dispatch_matches_plan=true`, `plan_held=false`; `dispatch_order_source=model`; `stage2=null`; no re-grounding fields set. |
| 3 | Dispatch and execution order | **pass** (verified) | m5: `dispatch … junction-recede-robot_3` at wall …659.54; `phase advance … recede-robot_3 completed=True` and `dispatch … junction-recede-robot_4` at …697.97; `junction-cross` at …736.34; `junction-release` at …887.91. m4: `action=reverse` for robot_3 first (`handoff guard … sim_t=32.367`), then for robot_4; `junction-cross robot=robot_1 action=yield`. GT: robot_3 starts backing at sim 32.9 s (y −0.22 → −1.01 by about 41 s) while robot_4 stays at y +0.22; robot_4 starts at 41.9 s (y +0.22 → +1.21 by about 53 s); robot_1 backs and pulls off from 52.9 s, reaching (−1.03, −0.38) by about 72 s. The yielder commanded and executed was robot_1, the plan's `yield` leg. |
| 4 | Nothing later changed what ran | **pass** (verified) | m4 received exactly 14 commands, all under `df397030` (two recedes, cross, release; no fallback, no stage-2). Every recede and the cross resolved `completed`; gates released by clearance (`gate_release reason=clearance` at sim 97.97 s and 115.7 s; robot_1's release gate cleared at 129.5 s). The other two decisions answered `congestion_detected=false` and logged `no dispatch` (`510f79e2` before the jam, `bc712975` after the release while robot_1 was still 2.16 m from its goal). `failure_context=null`. |
| 5 | Resolved | **pass** (verified) | GT 4/4 within 0.3 m (times in 7.1); M5 `arrived at base goal` for all four (robot_2, robot_4, robot_3, robot_1), final distances 0.06–0.09 m. |
| 6 | Safety | **pass** (verified) | GT closest pair 0.329 m (robot_1–robot_4) at sim 27.9 s, during the jam, before dispatch; 0 robot-robot and 0 robot-static contact rows in 3001 GT rows (Rev 6: both fields are hard-coded empty, `isaac/vgu_sim/acceptance_logging.py:99-100`, so the pass rests on the 0.329 m closest pair; the scene declares no static obstacles); no floor stop (no stop reason other than `min_distance_violation` ×9593 and `stale_pose_unsafe` ×2; floor 0.20 m armed per the M4 startup line). |
| 7 | Default (chi) order recomputed | **pass, near-tie** (verified by running the classifier's code path, `rank_recede_candidates` over `_junction_recede_candidates`, grounder files unchanged since `68e67b5`) | chi robot_4 = 0.971, robot_3 = 0.981 (no followers; cost = recede distance in m). Default order robot_4 → robot_3. Margin **0.010 m** against the verifier's tolerance `junction_recede_order_epsilon` 0.15. The default order is 4→3 on every M1 sample from 27.5 to 32.7 s (margin 0.008–0.020) and on the GT poses at 29–32 s (margin 0.005). |
| 8 | Prompt carried the options block and the grammar sentences | **pass** (verified) | `user_prompt` (sha256 `cbc947c4…`, matches the stored hash) contains the header "Plan actions the system's verifier accepts for each robot in the current scene", the two v3.5 sentences ("Name each robot exactly once: …", "A \"cross\" leg must come after the \"yield\" leg that releases it.") and the release sentence ("A plan with any \"cross\" leg must also contain a \"yield\" leg listed before it; …"). Only robot_3 and robot_4 were offered `reverse`. |

**Verdict.** Checks 1–5 pass, so the take is VLM-driven under the section 10.4 rule, matching `take_class_dmc.py`. The caveats below limit what it shows.

**Caveats.**

- **What the model chose.** It selected each robot's action from the listed actions the verifier accepts, and it chose the recede order. It did not compose free-form motion: the recede set (robot_3, robot_4) was fixed by geometry and listed in the prompt, and the yielder robot_1 is also M3's yielder.
- **The order is a near-tie.** The two orders differ in chi by 0.010 m (about 1 cm of recede distance), and the verifier accepts any order within 0.15. Any accepted order that differs from the default is a near-tie by construction.
- **Only the timing of the two recedes changed.** By design (`ground_junction_clear_phases`, R3.3), the model's order changes only the order in which the recede legs are dispatched. Pockets, the cross phase, the release lead (robot_4, chi rank 0) and the release crossing order stay keyed to chi. So the configuration after both recedes and everything after it are the same as under the default plan. What differs in the video is that robot_3 backs out first, about 9 sim-s before robot_4.
- **The model's `crossing_order` was not used.** It was robot_2, robot_1, robot_3, robot_4. The executed order (GT arrivals) was robot_2, robot_4, robot_3, robot_1: the release lead is chi's robot_4, and the yielder re-enters last.
- **The order choice mostly follows robot id, not the scene.** Offline (registration 10.2), ER-2 put robot_3 first in 19 of 24 B3 plans that reverse both robots, and changed order between replicates of the same snapshot. Here it wrote ascending id order again. Under `id_asc`, id order and listing slot cannot be separated.
- **One take.** 1 VLM-driven take out of 5 live takes (1 Unresolved, 3 M3-default, 1 VLM-driven). This is in line with the offline 7/27 rate (registration 10.1) but says nothing about a rate. It is illustrative, not controlled evidence.
- **Selection.** Take 5 is the only VLM-driven take, so it was chosen for the video because of its label; that is disclosed.

### 7.3 Video (Take 5)

- **File.** v7g `data/demo/campaign/ibD_t05_a1_panel.mp4` (git-ignored), md5 `fdf07a82`, 14.3 MB (no `_small` copy needed). Beside it: transcript, nine stills (start, call, decision, dispatch, r3_backing, r4_backing, mid, arrival, end) and `ibD_t05_a1_panel.md5`. Renderer v7g `feat/demo-panel-renderer` (`5198c0b`), the same arguments as the convoy and head-on videos.
- **Left pane.** Real camera recording, `/perception/annotated_frame`, all 6 segments, `annotated_framemap.json`.
- **Captions** (outside the terminal): "VLM-driven execution — take 5 of 5"; "Model: Gemini Robotics-ER 2 (gemini-robotics-er-2-preview); Layer 2 on; 4 of 4 robots arrived."; the registration 10.2 sentence with "(robot_3 first)" and "(robot_4 first, computed offline)"; "Takes 1–4: one unresolved, three resolved by the default plan."; "Illustrative demo, not controlled experimental evidence." (the section 7 wording).
- **What the terminal shows at the decision.** The concise `jq` lines print `strategy=junction_clear involved=robot_1,robot_2,robot_3,robot_4`, the justification, and `provenance=vlm_verbatim reason=null degradations= dispatch_order=robot_3,robot_1,robot_2,robot_4`. Then come the m5 `dispatch … junction-recede-robot_3` lines and the m4 `action=reverse` for robot_3. Later, `junction-recede-robot_4 … action=reverse` and `junction-cross robot=robot_1 action=yield` appear. `dispatch_order_source=model` is not printed (the fixed filter and `jq` do not include it); the filter was not widened. The default order appears in no terminal line (checked in the transcript), only in the caption.
- **Checks (verified).**
  - ffprobe: H.264, 1920x1080, 24 fps, yuv420p, 2499 frames, 104.13 s. The full take (sim 0–300.3 s), not cut.
  - Time map: log-to-sim alignment within 0.45 sim-s at 51 anchors.
  - The first `dispatch` line maps to sim 32.296 s; M4's `handoff guard … sim_t=32.367` follows it. Error about 0.07 sim-s.
  - The camera's burned-in clock against the caption clock: 32.73 / 33.07 s at the dispatch (the clock is held while the output prints), 36.37 / 36.50 s with robot_3 backing out, 46.33 / 46.50 s with robot_4 backing out, 146.80 / 147.00 s at arrival.
  - Stills viewed: robot_3 backs out while robot_4 stays at the centre, then robot_4 backs out with robot_3 parked at its pocket, and all four are at their goals at sim 147 s. One frame extracted from the encoded mp4 at video 43.45 s matches the robot_3 still.
- **Known gaps.**
  - The left pane is blank before sim 16.67 s (first recorded frame).
  - The automatic "call" still is the first call (`510f79e2`, no congestion); the jam call is on the dispatch still.

---

## 8. Five-Robot Scene, Take 1 (ER-2; Added 2026-11-15)

**Status.** Illustrative, not controlled evidence. n = 1. This take is a limitation demonstration, and the registration expected this outcome for the scene (section 4.4: no resolution, few motion commands, withheld analyses, Layer 2 going quiet). Seed position 21 is an exploratory extension seed, outside the preregistered list (positions 1–20). It was already seen in pilot E21 and in the v4 Stage 1 shadow run, so this take is no new evidence on that seed.

**Setup.** Kit `demo_campaign/m5/kit`; scenario `mapd_5_s1b_seed21`, seed 2107305794. Overlay `s1b_shield_escort_orch_seed21.yaml` `09bc16e6`, derived grounding `s1b_dynamic_shield_escort.yaml`, yield gate `swap`, stage 2 on. Inert delta `4843a776`, live `gemini-robotics-er-2-preview`, 600 sim-s horizon, sequential bring-up, both recorders on. The scene is a pickup-and-delivery task stream: 25 tasks over the 5 robots (`task_stream ... completed=0/25`). Sources: `m5/runs/m5D_t01_a1/`, `m5/driver_m5_20261115T035453Z.log`, `m5/MANIFEST_20261115T035453Z.md5`.

### 8.1 The Take (Verified From the Bundle)

| Item | Value |
|---|---|
| Take (label) | 1 (`m5D_t01_a1`), the only take; 0 bring-up aborts |
| Wall (UTC) | Chain START 04:23:20, END 05:19:46. Before that, 11 VM start attempts failed (03:55–04:16, the driver's stockout retry), and the VM started at 04:18:40. It was stopped and verified TERMINATED at 05:22:33. Invocation booked: 3833 s, counted from VM start. |
| Resolved | no. 1 of 5 arrived (GT rule `distance_to_goal < 0.3 m`): robot_5 at GT sim 185.7 s (M5 `arrived at base goal` and `task_stream event=arrived` at sim 187.8 s) |
| Label | Unresolved failure (section 7 rule; the take classifier labels intersection takes only and was not run) |
| Model calls | 9 billed: 8 analyses plus one stage-2 retreat call in analysis 2. Each took 1 attempt, `finish_reason=completed`, `parse_status=valid`, 0 refusals. Latency 7.0–13.0 s, 188 172 tokens (`COND` line), est. $0.0675. |
| Provenance (8 analyses) | 2 `vlm_verbatim`, 1 `repaired`, 5 `m3_default` |
| Reached M4 | 2 decisions (7 m5 `dispatch` lines). The other 6 were refused by grounding and withheld (6 m5 `refusal withheld … (refusal_no_action)` lines) |
| Re-analysis | Last analysis at scene stamp 275.47 s (`704fab63`). 147 `reanalysis suppressed reason=scene_unchanged` lines in total, 117 of them after the last analysis; max displacement 0.000–0.002 m against epsilon 0.05 m |
| GT closest pair | 0.2582 m, robot_1–robot_4, at sim 42.6 s (under 0.27 m from 42.5 to 46.0 s). This is their head-on standoff, before the first dispatch (M4 `handoff guard … sim_t=46.267`) |
| Safety | GT contact rows 0 robot-robot and 0 robot-static in 6001 rows. (Rev 6: both fields are hard-coded empty, `isaac/vgu_sim/acceptance_logging.py:99-100`. Robot-robot is supported only by the 0.2582 m closest pair. Robot-static is wrong in substance: robot_3 drove into island `obstacle_2` at sim 146.7 s and stayed against it; see 8.7.) Hard-floor stops 0 (floor 0.20 m armed per the M4 startup line). All 557 508 `safety stop` lines are `min_distance_violation` (M4's 0.45 m latch, not the floor). |
| Recording frames | 2014 annotated (7 segments, sim 31.47–600.23) / 4104 raw (14 segments); `VIDEO_VERIFY` OK |
| Manifest md5 | `bd7572c417c558fda4d19c40867363e1` (68 files) |

`goal_check` misprints the dispatch counts for this take: `GOAL_SUMMARY … dispatches=8 withheld=0` and `LIMITATION … grounded_dispatches=8 withheld=0`. Every artifact carries a grounded command, but m5 dispatched only two of them and withheld six (counted from the m5 log above).

### 8.2 The Eight Analyses (Verified From `decisions/*.json`, m5 and m4 Logs)

| # | Request, scene stamp (sim s) | Model answer | Provenance | What happened |
|---|---|---|---|---|
| 1 | `03bba450`, 44.47 | `yield`, yielder robot_1, passer robot_4 | `vlm_verbatim` (0 edits) | **Executed as named.** robot_1 `yield` (backup 1.514 m, pull-off +0.72 m), robot_4 passer; robot_3 and robot_5 `temporary_wait` 120 s ("retreat shield"). `gate_admit` sim 80.73 (escort 1.671 m); `gate_cleared` / `gate_release reason=clearance` sim 99.90 (moved 1.672 m); escort and all four commands COMPLETED. |
| 2 | `a15f3fc5`, 103.03 | `yield`, yielder robot_2, passer robot_3 (failure context: "yield completed 21 s ago; congestion re-detected") | `vlm_verbatim` (0 edits); stage 2 answered C, the default | **Executed as named.** robot_2 `yield` (backup 1.408 m, pull-off −0.72 m), robot_3 passer, robot_5 retreat-shield wait. `gate_admit` sim 138.70 (escort 1.604 m). robot_3 moved about 0.51 m (x 1.35 → 0.84) and stopped at sim 147, against the east face of island `obstacle_2` (Rev 6, 8.7). `gate_release reason=hold_timer` sim 183.70; then `escort robot_3: FAILED escort timed out in phase drive` (mapped sim 201.8). |
| 3 | `c2f7094b`, 186.70 | `yield` robot_4 | `m3_default` (repair distance > 4) | Refused: "no feasible yielder (robot_4 0.00 m, robot_1 0.00 m retreat room < 0.77 m required)"; withheld |
| 4 | `28865c06`, 191.53 | `yield` robot_4 | `m3_default` (same) | Refused: same reason; withheld |
| 5 | `f53de038`, 213.63 | `yield` robot_1 | `m3_default` | Refused: "no declared junction: robot_1 runs along x and robot_5 along y (a crossing), but no declared junction box (NW, SW, N, S) holds both robots"; withheld |
| 6 | `cc6332da`, 267.60 | `yield` robot_1 | `m3_default` | Refused: "no shared lane: robot_5 and robot_4 both run along y but sit 47 deg across it (side by side)"; withheld |
| 7 | `596b794b`, 271.47 | `junction_clear` | `repaired` (robot_5 `cross` → `wait`) | Refused: "no feasible yielder (robot_1 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)"; withheld |
| 8 | `704fab63`, 275.47 | `junction_clear`, no plan | `m3_default` (plan absent) | Refused: no feasible yielder (all five 0.00–0.15 m); withheld |

The yield refusals sum to "no feasible yielder" ×4, "no declared junction" ×1 and "no shared lane" ×1. None of the six refused proposals moved a robot.

### 8.3 Where Each Robot Ended (GT, Sim 600 s)

| Robot | Final position | Its goal | What it did |
|---|---|---|---|
| robot_1 | (−2.17, −0.68) | S (−0.25, −1.35), 2.03 m away | Yielder of decision 1; stayed at its pull-off point from sim 100.2 s |
| robot_4 | (−2.36, −1.06) | Wp (−2.30, 1.35), 2.41 m away | Escorted passer of decision 1; stopped at the escort end from sim 100.3 s, 0.425 m from robot_1 |
| robot_5 | (−1.78, −0.51) | — | Reached its first goal, pickup N, at GT 185.7 s (the 1 arrival). Its dwell ended at 192.8 s and it was issued task 2, delivery Wm (−2.30, −1.35). It drove toward Wm and stopped at sim 210.8 s, 0.422 m from robot_1. GT `distance_to_goal` (2.41 m) still refers to the first goal. Tasks completed: 1 of 25. |
| robot_2 | (0.51, 0.84) | E (2.30, 0.00), 1.98 m away | Yielder of decision 2; parked near its retreat point (−0.36, 0.10) about 140–183 s. After the hold-timer release it moved to (0.07, 0.64), then at 268–272 s to its final spot, 0.398 m from robot_3 |
| robot_3 | (0.84, 0.62) | N (−0.25, 1.35), 1.31 m away | Passer of decision 2; stopped at sim 147 s, about 0.51 m into a 1.604 m escort, nose against island `obstacle_2`'s east face (x 0.80; Rev 6, 8.7) |

Three pairs stayed under M4's `min_distance_m` 0.45 continuously to the end (GT): robot_1–robot_4 from sim 100.5 s, robot_1–robot_5 from 211.0 s and robot_2–robot_3 from 272.4 s. The `min_distance_violation` stop lines continue for all five robots until the last m4 line.

### 8.4 Why It Stayed Unresolved

**Verified.**

- **Decision 1 moved one pair through, and then the pair latched.** The yield cleared by distance at sim 99.9 s. The exemption for robot_1+robot_4 ended in the same second (`exempt pairs changed pairs=-`). From sim 100.5 s the two stood 0.42 m apart and never moved again.
- **Decision 2's escort stalled.** robot_3 stopped at sim 147 s with no robot within 1.29 m (GT) and no robot_3 safety stop in that window. From that moment its Nav2 log repeats `camera_localizer … no TF robot_3/odom->robot_3/base_footprint at stamp=147.06` (456 lines, last stamp 268.46). The yield was closed by its 45 s hold timer, and the escort failed. Why robot_3 stopped is not established. (Superseded by section 8.7, Rev 6: the escort segment ran into island `obstacle_2`, and robot_3 stopped against its east face. The TF warnings follow from M1 losing the marker at the face.)
- **Every later proposal was refused by grounding.** The robots near each conflict had 0.00–0.15 m of retreat room against 0.77 m required, or the pair had no declared junction or no shared lane. Each refusal withheld the command and armed the re-analysis suppression. After sim 275.5 s, nothing moved more than 0.05 m between checks, so no further analysis ran.

**Inferred (not tested here).**

- The final clusters were held by M4's 0.45 m latch: the pairs were not exempt and stood within `min_distance_m`.
- The grounded vocabulary offers no motion to robots with no retreat room, so no later decision could have moved them.
- This take does not show whether different first decisions would have avoided the clusters.

### 8.5 Video

- **File.** v7g `data/demo/campaign/m5D_t01_a1_panel.mp4` (git-ignored), md5 `75bf99e64c7ebea10573f08eb62440c3`, 21.0 MB (no `_small` copy needed). Beside it: transcript, five stills (call, decision, dispatch, mid, end) and `m5D_t01_a1_panel.md5`. Renderer v7g `feat/demo-panel-renderer` (`5198c0b`), unchanged, with the same arguments as the other campaign videos.
- **Left pane.** Real camera recording, `/perception/annotated_frame`, all 7 segments, `annotated_framemap.json`.
- **Captions** (outside the terminal):
  1. "Unresolved failure — take 1 of 1 (limitation demonstration)";
  2. "Model: Gemini Robotics-ER 2 (gemini-robotics-er-2-preview); Layer 2 on; 1 of 5 robots arrived.";
  3. "Two decisions were executed (yield + escort); six later proposals were refused by grounding checks; the scene stayed jammed.";
  4. "Illustrative demo, not controlled experimental evidence. Seed position 21 (exploratory extension seed); shows a current limitation." (the section 7 lines).
- **Checks (verified).**
  - ffprobe: H.264, 1920x1080, 24 fps, yuv420p, 4839 frames, 201.63 s. The full take (sim 0–600 s), not cut.
  - Time map: log-to-sim alignment within 0.32 sim-s at 52 anchors.
  - The first `dispatch` line maps to sim 46.01 s, and M4's `handoff guard … sim_t=46.267` follows it: an error of about 0.26 sim-s. The first `starting analysis` maps to 44.56 s against the scene stamp 44.47 s.
  - The camera's burned-in clock against the caption clock: 46.60 / 46.71 s at the dispatch, 269.20 / 269.45 s at analysis 6 (the clock is held while the output prints), and 596.90 / 597.08 s near the end.
  - Stills viewed: the dispatch (robot_1 yield, three `temporary_wait`s, exempt pair robot_1+robot_4); analysis 6 with the "no shared lane" reason on screen; sim 597 s with the two clusters still in place.
- **Known gaps (the filter was not widened).**
  - The fixed filter does not match m5's `yield refused`, `refusal withheld` or `reanalysis suppressed` lines, or m4's `escort … FAILED` line. On screen, the "no feasible yielder" refusals show only as `provenance=m3_default reason=repair distance exceeds bound 4`. The "no declared junction" and "no shared lane" refusals show in full, because they are the plan's rejection reason.
  - The `jq` grounding line prints `dispatch_order=…` for the six withheld decisions too: it reads `dispatched_robot_ids`, which is filled although nothing was sent. The absence of m5 `dispatch` and m4 `command received` lines after those decisions shows the withholding; the caption states it.
  - The left pane is blank before sim 31.47 s (first recorded frame) and in the last frames after 600.23 s, so the end still is blank.
  - **Rev 6: the captions predate the escort finding (8.7).** They do not say that robot_3's escort drove into a rack island. The video and the combined video (section 9) were not re-rendered. A re-render should add one caption line: "Decision 2's escort drove robot_3 straight into a rack island (the escort path has no obstacle check); it stayed against the island until the escort timed out." Caption 3's "the scene stayed jammed" is then true, but incomplete without that line.

### 8.6 Verified and Inferred

| Claim | Status |
|---|---|
| Analyses, provenance, refusal reasons, dispatches, gate events, escort failure, arrival, safety counts, closest pair, manifest md5 | verified (bundle artifacts, m4/m5 logs, GT, driver log) |
| Robot_5's arrival was its first task goal; it then left on task 2 | verified (`task_stream` lines, GT) |
| robot_3's stall coincides with missing odom TF warnings | verified as co-occurrence; the cause is not established (superseded by 8.7: robot_3 stopped against island `obstacle_2`, which is confirmed; the TF warnings are a downstream symptom, which is inferred) |
| The final clusters were held by the M4 latch, and no grounded strategy could move them | inferred |
| `goal_check`'s `withheld=0` is wrong for this take | verified against the m5 log |

### 8.7 Follow-Up: robot_3's Escort Drove Into Rack Island `obstacle_2` (Added 2026-11-15, Rev 6)

This is an offline re-reading of the bundles: no VM, no API call. The bundles were not changed.

**Verdict: confirmed.** The evidence is GT poses, the URDF collision box, the scene builder code and the overhead recording. They agree to the millimetre. Decision 2's straight escort segment crossed island `obstacle_2`. robot_3 drove west into the island's east face, stopped there at sim 146.9 s, and was held against it until M4's monotonic deadline failed the escort (mapped sim 201.8 s). The only inferred parts are the downstream ones, marked below.

#### 8.7.1 Recording (Viewed; Stills Under `docs/reports/assets/2026-11-15-demo-campaign/`)

Frames were taken from `rec/camera_raw_*.mp4` and `rec/annotated_*.mp4` through each stream's per-frame time map, using the burned-in `t=` clock. Each still is a crop around robot_3 and the island, 645 × 414 px, about 20 KB.

| Still | Sim t (burned-in) | What is visible |
|---|---|---|
| `m5D_escort_138p03s_raw.jpg` | 138.03 | robot_3 at its start, east of the island, before the turn |
| `m5D_escort_144p97s_raw.jpg` | 144.97 | robot_3 heading west toward the island's east face, marker and chassis fully visible |
| `m5D_escort_147p13s_raw.jpg` | 147.13 | robot_3 at the island's east face, next to its north-east corner; the chassis is no longer visible beside the marker |
| `m5D_escort_147p30s_annotated.jpg` | 147.30 | M1's last box for robot_3 at the face, with its velocity arrow still pointing west |
| `m5D_escort_150p00s_raw.jpg` | 150.00 | the marker's west part is hidden by the island's top edge; M1 no longer tracks robot_3 |
| `m5D_escort_199p90s_raw.jpg` | 199.90 | robot_3 still at the face, about 2 s before the escort's deadline |

The recording shows robot_3 driving into the island and stopping against it, with nothing else nearby. It cannot resolve millimetres; the contact itself rests on 8.7.2.

#### 8.7.2 Trajectory and Geometry (Verified)

- **Command.** `a15f3fc5`: `passer_escort_heading_rad` π (due west), `passer_escort_distance_m` 1.604. Degradations: `grounding=dynamic_arms:bearing_lane:robot_3:37`, `grounding=dynamic_arms:lane:x` and `grounding=escort_turn_cap:robot_3:2.35->1.604`. The turn cap is the goal's along-axis distance, |−0.25 − 1.35| ≈ 1.60 m: the escort was sized to end at the goal's x, straight through the island.
- **Segment.** From the GT pose at admission (1.353, 0.603), heading π, for 1.604 m, the segment ends at (−0.251, 0.603). Its centreline enters the `obstacle_2` box (x 0.25–0.80, y −0.90–0.70) after 0.553 m. The chassis spans y 0.53–0.67, entirely inside the face's y range.
- **GT motion.** The robot turned in place from 139 to 141 s, then drove at about 0.09 m/s on a heading of −3.08 rad (about 3.5° south of west). At 146.0 s it was at x 0.905. At 146.9 s it stopped at (0.838, 0.572) after 0.515 m. Its heading then snapped to exactly π and stayed there to 180 s: the chassis squared up against a flat face. By 200 s it had turned to 2.996 rad and moved 0.01 m east, (0.848, 0.601), still at the face.
- **The 0.038 m gap is the chassis nose.** GT logs the `base_link` pose (`isaac/vgu_sim/acceptance_logging.py:14`). The URDF collision box of `base_link` is 0.140 × 0.140 m, centred 0.032 m behind the link origin (`isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf:63-68`), so it reaches +0.038 m forward. The lidar cylinder also reaches +0.038 m (−0.032 + 0.015 + 0.055), and the wheels reach +0.033 m. Heading west at x 0.838, the nose is at 0.838 − 0.038 = 0.800 m, exactly the face. No overlap and no ride-up is needed. The centre-to-face distance equals the forward half-extent, not a gap.
- **Island collision shape = the yaml box.** `_author_static_obstacles` → `_author_box` (`isaac/vgu_sim/scenario_builder.py:149-201`) authors a cube of size 2.0, scaled by the half-extents, translated to the yaml centre at z = h/2, with `UsdPhysics.CollisionAPI`. The face is therefore at x 0.525 + 0.275 = 0.800. This is verified from code; the generated USD is not in the bundle.
- **Why M1 lost the marker (inferred).** The 0.12 m marker (`isaac/vgu_sim/marker_asset.py:6`) sits 0.21 m up on `base_link` (URDF `aruco_marker_joint`). At x 0.838, its west 0.022 m lies over the island's footprint, below the 0.30 m top. With the camera nadir west of the island (about x −0.07, estimated from the frame), the island's top edge hides that strip. M1's last track is at stamp 147.07 s, x 0.866. The 456 `camera_localizer … no TF` warnings frozen at stamp 147.06 then follow from the lost marker.
- **Distance recompute (an ad hoc offline check, no committed script).** For every GT row, the URDF chassis box and wheels were placed at the `base_link` pose and heading, and the gap to each declared box was measured, sampled at about 5 mm. robot_3 to `obstacle_2`: the gap is 5 mm or less in 4526 of the 4534 GT rows from sim 146.7 s to 600 s, with a minimum of −0.2 mm (touching, within the sampling). The exceptions are 8 rows at 266.5–267.7 s, up to 13.5 mm, while the line-hold servo turned the robot against the face. GT is sampled at 10 Hz, so a moving robot's true minimum gap can be a few mm lower than any row shows. The shapes are the URDF's; the imported USD collision shapes were not inspected. robot_2 to `obstacle_2`: 3.8 mm at sim 270.7–270.9 s, during its 268–272 s move. That is a possible brief graze, not established.

#### 8.7.3 What the Code Checks (Verified, v7j Working Tree)

| Stage | Check that exists | Static obstacles used? |
|---|---|---|
| M3 escort length (`reasoning/rag/maneuver_geometry.py:484-532`, `derive_escort_distance`) | travel past the parked yielder plus `escort_clearance_m`, inside `escort_band_m` | no |
| M3 escort heading and turn cap (`reasoning/rag/grounding_view.py:938-999`, `derive_escort_heading`; `:1027-1060`, `_cap_escorts_at_turn`; `:1063-1140`, `apply_escort_headings`) | axis from the lane, sign from the goal, length capped at the goal's along-axis distance | no |
| M3 `escort_park_clearance` (`reasoning/rag/escort_clearance.py:159-241`; `command_grounder.py:2143`ff, `filter_escort_park_candidates`) | escort leg against the parked yielder's park point, within `min_distance_m` | no (module docstring, lines 1-38: park point only) |
| M3 yielder retreat (`command_grounder.py:532-533`, `yield_retreat_room_m` and `yield_feasible`; `retreat_candidates.py:120`) | the yielder's retreat room and the retreat-candidate sweep against the static boxes | yes, for the yielder only |
| M4 `drive_heading` (`ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py:662-799`) | ends only when the odometry distance reaches `distance_m` (COMPLETED) or at the monotonic deadline (FAILED, `max(15 × naive, 30 s)` = 335 s here); line-hold heading servo | no |
| Command path | the escort publishes raw `Twist` on `/<robot>/cmd_vel` (`nav2_adapter.py:694`). Nav2's `collision_monitor` reads `cmd_vel_nav` and writes `cmd_vel` (`ros2_ws/src/swarm_simulation/config/nav2_params.yaml:364-365`), so the escort bypasses it | no |
| M4 safety monitor | robot-robot `min_distance_m` latch and 0.20 m floor (no file in `swarm_execution/` references obstacles or scans) | no |

So no stage compares the escort's straight segment with a declared static obstacle. The static boxes reach M3 only through the yielder's retreat checks.

#### 8.7.4 Every Escort in the Campaign (GT and m4 Logs; the Segment From the GT Pose at `gate_admit`)

"Boxes" are the scenario's `static_obstacles` plus the `aisle_barrier` blocks. The barrier blocks are derived from the yaml through `_author_aisle_barrier`, not declared as boxes. The heading is the decision's `passer_escort_heading_rad` where present. Otherwise it is measured from the first 0.3 m of GT motion: legacy M4 drives odom yaw 0, the spawn heading. The intersection takes declare no boxes; their warehouse walls were not checked.

| Bundle | Command | Passer | Start (m) | Heading | Length (m) | Segment centreline crosses a box? | Min centreline-to-box (m) | Outcome (m4) | GT motion |
|---|---|---|---|---|---|---|---|---|---|
| `m5D_t01_a1` decision 1 | `03bba450` | robot_4 | (−0.626, −1.136) | π (decision) | 1.671 | no | 0.436 (`obstacle_1`) | COMPLETED, 1.672 m | reached the segment end |
| `m5D_t01_a1` decision 2 | `a15f3fc5` | robot_3 | (1.353, 0.603) | π (decision) | 1.604 | **yes, `obstacle_2` after 0.553 m** | 0 | FAILED (deadline, phase drive) | stopped against the face after 0.515 m |
| `cvD_t01_a1` | `35084986` | robot_1 | (−0.095, −0.015) | 0.013 (GT) | 1.898 | no | 0.260 (barrier) | FAILED (deadline, phase drive) | 1.80 m, stopped at x 1.706 |
| `cvD_t02_a1` | `759bdb94` | robot_2 | (0.096, 0.037) | −3.109 (GT) | 1.904 | no | 0.238 (barrier) | no terminal line | 0.99 m |
| `cvD_t03_a1` | `ab6a10c5` | robot_1 | (−0.010, −0.033) | 0.028 (GT) | 1.807 | no | 0.242 (barrier) | no terminal line | 1.62 m |
| `hoD_t01_a1` | `f40c0537` | robot_1 | (−0.136, −0.008) | 0.007 (GT) | 2.928 | no | 0.267 (barrier); 1.564 (`blocker_west`) | COMPLETED, 2.932 m | reached the segment end |
| `ibD_t01_a2` … `ibD_t05_a1` (5 takes) | junction-cross | robot_2 | x 0.23 to 0.73, y ≈ 0 | ≈ π (GT) | 1.893 to 2.927 | no boxes declared | — | COMPLETED, all 5 | reached the segment end |

- Only `a15f3fc5` crosses a box. The convoy escorts that failed or never logged an end stopped short with their centreline at least 0.238 m from the barrier blocks (chassis clearance at least 0.148 m). The recompute's minimum chassis-to-box gap in the convoy takes is 0.097 m. Those stops are therefore not box contacts; their cause was not examined here.
- Every decision file with a dispatched escort was admitted (`gate_admit` in m4). The six withheld five-robot decisions dispatched nothing.

**October five-robot bundles (v3 `data/logs/vm_runs/`, read-only).** These are 19 admitted escorts in 15 S1b/S1a bundles: `batch2`–`batch6` (including tranche-1 E28, E29, E31; E27 and E30 had none), `churn_wave` E6, `s1b_pilot2` E3 and `s1_resume` E1.

- **No segment crosses a declared box.** The minimum centreline-to-box distance is 0.093 m, for E18 `1feb2c4e`, robot_2 against `obstacle_1`. That is about 4 mm more than the 0.089 m wheel half-width. That escort never drove: GT motion was 0.002 m and there was no terminal line.
- **Outcomes:** 12 COMPLETED; 1 FAILED (E18 `56b599af`, robot_3, after 1.16 m, 0.465 m from the boxes); 6 with no terminal line (E15, E22, E18 `1feb2c4e`, E3 ×3). None of those 6 moved more than 0.002 m.
- The seed-21 pilot E21 escort (`04457772`, robot_4 west along y −1.14, 1.692 m) is the same manoeuvre as decision 1 here, and it completed.
- **Static-contact recompute over tranche 1 (11 bundles, E27–E31, both arms).** The minimum gap is at least 7 mm, except in E30 Arm A, where robot_2 came within 1.2 mm of `obstacle_1` at sim 48.6–49.2 s. That was under Nav2, not an escort. It is a possible graze, not established.

So the escort-into-island failure is new to this take. It is the first escort, in the campaign and the October five-robot bundles checked, whose straight segment crossed a declared box.

#### 8.7.5 What This Changes

- **The label.** The take stays an Unresolved failure, but "unresolved" partly reflects an escort path error. The model's decision 2 (robot_2 yields, robot_3 passes) was executed as named. Grounding then sized and aimed the escort without regard to the island. The failure is neither the VLM's decision nor the later grounding refusals alone. Whether robot_3 would have reached its goal on a feasible path is not shown.
- **Safety statements.** Ground truth's "0 robot-static contacts" for this take is wrong in substance, not only unsupported. See the safety scope in the final summary.
- **Options for the owner (not applied).**
  - (a) **Escort guard.** Grounding refuses or shortens an escort whose swept segment (centreline grown by the chassis half-width plus a margin) crosses a declared obstacle box, using the same `static_obstacles` the yielder retreat already receives.
  - (b) **Static-contact logging.** Replace the hard-coded lists with a PhysX contact report on the chassis and obstacle prims, or with a per-row chassis-box-to-obstacle distance, as in 8.7.2.

#### 8.7.6 Known Wording Issue in Other Reports (Listed, Not Edited)

These reports are frozen evidence on other branches or worktrees, or earlier reports on this branch. They state "0 GT contacts" or "no contact" from the empty fields, or from robot-pair distances alone in scenes that have static obstacles.

- **Read from the empty GT fields:**
  - v7d `docs/reports/2026-11-14-ib10-safety-default-arm-results.md`:62 (the 0.18 m distance claim is sound; "the GT contact lists are also empty" carries no weight), :74 and :360 (table "GT contacts 0 / 0"), :334 ("0 GT contact entries").
- **Method ambiguous (the "contact frames" count does not say whether it read the empty field or frames below 0.18 m; robot-robot only either way, and IB10 declares no static obstacles):**
  - v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md`:35, :59, :63, :144 ("zero contact frames in every GT file"); its success criterion at :25 is distance-based;
  - v6d `docs/reports/2026-11-13-thesis-evidence-register.md`:74–75 ("0 GT contacts", the two IB10 entries); :55 ("2/2 arrivals with zero contacts", quoted from `2026-10-03-loop-family-and-visual-pass.md`:250, mock smoke); :72 ("no contact", IB10 closure, mock).
- **From robot-pair distances, stated as general "contact" in scenes with static islands:**
  - v6d `docs/reports/2026-11-13-thesis-evidence-register.md`:85 ("contact gate PASS 10/10 (GT min 0.225-0.424 m)", S1b tranche 1, robot pairs only);
  - this branch: `2026-10-12-shield-fix-and-minibatch.md`:25, :86, :176 and `2026-10-17-escort-filter-minibatch.md`:135, :186, :284 (S1b, "zero contacts" from pair distances).
- **Older reports on this branch reading the empty fields:** `2026-10-03-step7b-oracle-freeze.md`:246, `2026-10-05-follow-waypoints-validation.md`:24, :161, :178, `2026-10-07-gpt56-sol-swap.md`:307 (method not re-checked here). `2026-09-25-overnight-findings.md`:232, :262 are already corrected in that report (:1852–1871). `2026-10-08-s1-pilot.md`:174 already carries the caveat.
- **Not an over-claim:** v7c `docs/reports/2026-11-14-safety-exemption-fix.md`:261, a positive contact found by distance.

### 8.8 Verified and Inferred (Section 8.7)

| Claim | Status |
|---|---|
| robot_3's escort segment crossed `obstacle_2`; robot_3 stopped at its east face at sim 146.9 s and stayed there | verified (decision file, GT, URDF, scene builder code, recording) |
| The 0.038 m centre-to-face distance is the chassis's forward half-extent | verified (URDF collision box; GT is `base_link`) |
| No M3 or M4 stage checks the escort segment against static obstacles | verified (code, file:line in 8.7.3) |
| The `no TF` warnings and M1's marker loss are caused by the island hiding the marker | inferred |
| No other campaign or October five-robot escort segment crossed a declared box | verified (19 + 11 admitted escorts) |
| Brief grazes (m5D robot_2 at 270.8 s; tranche-1 E30 robot_2 at 48.6–49.2 s) | possible, not established (an ad hoc recompute at about 5 mm resolution, using URDF shapes) |

---

## 9. Combined Video (Added 2026-11-15)

- **File.** v7g `data/demo/campaign/demo_campaign_combined.mp4` (git-ignored), md5 `ace3cc0d765a504441a29d54e74ac3df`, 25.6 MB. Beside it: the manifest `demo_campaign_combined_manifest.json`, the tool's sidecar `demo_campaign_combined_sources.json` (each source's path, md5, trim and labels) and `demo_campaign_combined.md5`. It was made with `render_demo_panel.py combine` (renderer `5198c0b`, unchanged) at `--crf 25`. The default crf 23 gave 29.3 MB, over the 28 MB limit.
- **Output (ffprobe, verified).** H.264, 1920x1124 (a 44 px caption bar above the 1080p clips), 24 fps, yuv420p, 5518 frames, 229.92 s.
- **Order and trims** (source video seconds; each excerpt follows a 3 s title card, and the caption bar prints the trim):

| # | Source | Title card: outcome, take | Excerpt | What it contains |
|---|---|---|---|---|
| 1 | `ibD_t05_a1_panel.mp4` (104.1 s) | VLM-driven execution, take 5 of 5 | 22.5–97.5 s | jam call `df397030`, `provenance=vlm_verbatim`, recede dispatch robot_3 then robot_4, cross and release, robot_1's arrival (sim 149 s) |
| 2 | `cvD_t01_a1_panel.mp4` (273.3 s) | Unresolved failure, take 1 of 3 | 5.5–37 s | first call, `vlm_verbatim` yield, dispatch, `gate_admit` and `gate_release`; the latch forms at about sim 75 s |
| 3 | same | Unresolved failure, take 1 of 3 (later excerpt) | 255–271.9 s | the last proposal (`m3_default`, a wait) and the jam at sim 250–260 s, up to the last camera frame |
| 4 | `hoD_t01_a1_panel.mp4` (76.0 s) | M3-default resolution, take 1 of 1 | 26.5–69 s | decision 2 call, `yield` robot_1 in the answer and the dispatched yield to robot_2, gate, both arrivals |
| 5 | `m5D_t01_a1_panel.mp4` (201.6 s) | Unresolved failure, take 1 of 1 | 7.5–37 s | first call, `vlm_verbatim` yield, dispatch, `gate_admit`, `gate_cleared` |
| 6 | same | Unresolved failure, take 1 of 1 (later excerpt) | 183–199.5 s | the last analysis (`plan absent`), then 30x sim time to sim 597 s with both clusters in place |

- **Title-card notes** (one line each, consistent with sections 5–8):
  - intersection: "Model chose the back-out order (robot_3 first); default was robot_4 first by ~1 cm; 1 VLM-driven take of 5";
  - convoy: "The model's yield ran as named, but it left out the two queued robots; they followed through the gate and the scene latched";
  - convoy, later: "All 11 later proposals ran as 8 s waits; 0 of 4 robots arrived by the end (sim 260 s); takes 2-3 were also 0 of 4";
  - head-on: "Grounder corrected the model's yielder: robot_1 had 0.70 m retreat room (< 1.08 m), so robot_2 yielded; 2 of 2 arrived";
  - five robots: "Limitation demonstration: first decision (robot_1 yields, robot_4 escorted) executed and completed";
  - five robots, later: "Six later proposals were refused by grounding checks; no analysis after sim 275.5 s; 1 of 5 arrived by sim 600 s".
  Each card also carries the tool's fixed line "Illustrative demonstration, not controlled experimental evidence.". The per-scenario disclosure captions of the source videos stay visible under each scene pane.
- **Checks (verified).**
  - Before combining, ffprobe frame counts matched each source's duration: 2499 / 104.125 s, 6559 / 273.29 s, 1825 / 76.04 s and 4839 / 201.63 s. No excerpt ends past a source's last frame.
  - Stills viewed: all six title cards, and one frame from inside each excerpt. Each frame's caption bar names the scenario, outcome, take and trim. The text is legible at crf 25 (checked on a full-resolution frame of excerpt 4).
- **Rev 6.** The five-robot title cards and captions predate section 8.7 and do not mention the escort into the island. Per the table above, excerpt 5 covers decision 1 (`gate_admit`, `gate_cleared`), and excerpt 6 runs from the last analysis to sim 597 s, a period when robot_3 was already against island `obstacle_2` (not re-checked frame by frame in the combined video). It was not re-rendered; a re-render should add the 8.5 caption line to the "five robots, later" card.
- **Why two excerpts for each unresolved take.** One contiguous excerpt could not show both the first executed decision and the late, still-jammed scene within about 4 minutes. The cut is never hidden: each part has its own title card, and the caption bar prints its trim.
