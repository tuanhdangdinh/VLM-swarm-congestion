# Demo Campaign Results

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: intersection live takes 1–3 (ER-2, B3), why live ER-2 gave no usable plan, and the Sonnet 5.5 arm built for takes 4–5.
- Rev 2 (2026-11-15): added section 5, convoy counterflow live takes 1–3, the root cause of the non-resolution, and the take 1 panel video.
- Rev 3 (2026-11-15): added section 6, head-on with obstacle, take 1 (ER-2), and its panel video.
- Rev 4 (2026-11-15): added section 7, intersection takes 4–5 (ER-2, B3), the adversarial verification of take 5 (the one VLM-driven take), its panel video, and the wall-share amendment.
- Rev 5 (2026-11-15): campaign closed. Added the final summary (all four scenarios, ledger totals, the three-way VLM count, open owner decisions, archive index), section 8 (five-robot take 1 and its video) and section 9 (the combined video). Fixed stale statements: the Sonnet offline spend is booked (sections 3.4, 3.6), and the ER-2 choice for takes 4–5 is now recorded in registration section 10.8 (running summary, section 7). The running summary below is otherwise kept as written per phase.
- Rev 6 (2026-11-15): added section 8.7, an offline follow-up showing that robot_3's escort in the five-robot take drove into rack island `obstacle_2`, with stills and an escort-segment check over the campaign and the October five-robot bundles. Scoped every contact statement: ground truth's two contact fields are hard-coded empty, so they show nothing. Added section 5.8, the outcome of the convoy held-robot prompt check. Updated the final summary, sections 8.2–8.6 and the open owner decisions.
- Rev 7 (2026-11-15): re-rendered the five-robot video and the combined video with the escort-into-island caption line and a new middle five-robot excerpt (sim about 106-182 s); the first renders are kept with a `_v1` suffix. Updated the final summary's video table and sections 8.5, 8.7 and 9.
- Rev 8 (2026-11-15): section 8.7.6 updated for the errata now carried by the older reports (current line numbers, old numbers kept in brackets, commits cited); section 8.7.2's exception-row span corrected to 266.5–268.0 s; added section 10 (the escort obstacle guard and ground-truth contact logging follow-up builds, by reference); updated the open owner decisions.
- Rev 9 (2026-11-15): added section 11, an offline verification of the 2026-09-30 ER2LIVE head-on run. The model named robot_2 and retreat B; the feasibility gate kept the choice, and it was executed. Also the audit's wider counts. Its video was not rendered (disk floor), so section 9 and the video table are unchanged.
- Rev 10 (2026-11-15): rendered the ER2LIVE panel video and combined video v3 with it as a new excerpt after the head-on take; the previous combined set is kept with a `_v2` suffix. Section 11.5 records the render, the frame-map validation and the hard-floor metric finding (the 0.20 m floor is on centre distance, not body gap); the Rev 9 decoder claim (0 of 3745 frames) did not reproduce. Updated section 9 and the final summary's video table.

- Rev 11 (2026-11-15): added section 12, convoy takes 4–5 with the M3 queued-robot hold (both Unresolved failure: the model chose robot_1 as yielder both times, the latch the scene file names; the grounder held robot_3 and robot_4 as designed), and the simulator-only test (pytest installed beside Isaac's Python; the `pxr` test SKIPPED: no `pxr` in a bare `python.sh`). Updated the final summary's convoy rows, the three-way count and the archive index.
- Rev 12 (2026-11-15): added section 13, a presentation cut of the five demo videos and a combined presentation video for an audience (offline, renderer profile `presentation`); the engineering cuts stay the record and are unchanged.
- Rev 13 (2026-11-15): added section 14, the convoy rerun with the queued-robot hold and the counterflow yielder correction (kit `cvy`, one demonstration take): resolved 4/4, labelled "Resolved — grounder held the queued robots; model chose strategy and yielder" (the model named robot_2 itself; the correction was armed and did not fire). Updated the final summary's convoy row, ledger note, "What This Does and Does Not Show" and the archive index. The five earlier convoy takes stay reported as they were.
---

## Final Summary (Campaign Closed, 2026-11-15)

Every take is an illustrative demo, not controlled experimental evidence. No take is pooled with experiment data, and n is 1 to 5 per scenario, so nothing here is a rate.

### Scenarios and Videos

| Scenario | Valid takes (bring-up aborts) | Outcomes | Selected take, label | Video (v7g `data/demo/campaign/`), md5 |
|---|---|---|---|---|
| 4-robot intersection (`ib`, ER-2, B3; sections 1, 7) | 5 (1) | take 1 Unresolved failure (3/4 arrived); takes 2, 3, 4 M3-default resolution; take 5 VLM-driven execution (all 4/4) | take 5, **VLM-driven execution** (chosen for its label; disclosed) | `ibD_t05_a1_panel.mp4`, `fdf07a82fcb657b738c44a89bfbe3dae` |
| Convoy counterflow (`cv`, ER-2, legacy grounding; sections 5, 12) | 5 (1) | takes 1–3 Unresolved failure, 0/4 arrived in each; takes 4–5 (queued-robot hold, Rev 11) Unresolved failure, 1/4 arrived in each | take 1, **Unresolved failure** (selected take) | `cvD_t01_a1_panel.mp4`, `824319447d05aaef6623158d00d2818f`; a `_small` copy, `b78cff5b3db4b25f6b8e218111656a42` |
| Four-robot convoy counterflow scene, rerun (`cvy`, ER-2, legacy grounding, queued-robot hold + counterflow yielder correction; section 14, Rev 13) | 1 (1) | demonstration take 1 resolved, 4/4 arrived (GT) | take 1 (`cvY_t01_a2`), **Resolved — grounder held the queued robots; model chose strategy and yielder** | not rendered yet (candidate: `cvY_t01_a2`, section 14.6) |
| Head-on with obstacle (`ho`, ER-2, prompt v2; section 6) | 1 (0) | take 1 resolved 2/2 | take 1, **M3-default resolution** (grounder-corrected) | `hoD_t01_a1_panel.mp4`, `2aa6534ad508d3440e51822fdcd3f0f0` |
| Five robots, seed position 21 (`m5`, ER-2; section 8) | 1 (0) | take 1 unresolved, 1/5 arrived | take 1, **Unresolved failure** (limitation demonstration) | `m5D_t01_a1_panel.mp4`, `33e9f5eedd7fb56edd007d8b728ea8c0` (Rev 7; v1 kept as `m5D_t01_a1_panel_v1.mp4`, `75bf99e64c7ebea10573f08eb62440c3`) |
| Head-on with obstacle, earlier run ER2LIVE (2026-09-30, not part of the campaign; section 11) | — | 1 run, 2/2 arrived | **VLM-driven execution** (model's yielder kept by the gate; escort and Nav2 recovery are the system's) | `ER2LIVE_20260930_panel.mp4`, `93cbfe7108e6a9ca9a71fc4c7c79bd47` (Rev 10) |
| All four, excerpts, plus the ER2LIVE excerpt (section 9) | — | — | — | `demo_campaign_combined.mp4`, `de8cb6ed07e42008b8acb3f9274352db` (Rev 10, v3; Rev 7 kept as `demo_campaign_combined_v2.mp4`, `1e0fd52025624da723766701ec412131`; v1 kept as `demo_campaign_combined_v1.mp4`, `ace3cc0d765a504441a29d54e74ac3df`) |

### Ledger Totals (`ledger_dmc.py status`, After the Last Invocation)

| Item | Value |
|---|---|
| VM wall clock, campaign | 18 203 s of 43 200 s, over 10 invocations: `ib` 8239 s of 12 600 s, `cv` 4829 s of 9000 s, `ho` 1302 s of 1800 s, `m5` 3833 s of 14 400 s |
| API spend (estimates) | $2.6975 of $10: offline $2.2705 (the $2.00 registration booking plus $0.2705 for the Sonnet B3 check), live takes $0.4165, probes $0.0105 |
| Valid takes | 10: `ib` 5, `cv` 3, `ho` 1, `m5` 1 |
| Bring-up aborts | 1 of 3 allowed per scenario, all in `ib` (`ibD_t01_a1`, `change_state` timeout on robot_1); 0 in `cv`, `ho` and `m5` |

**Rev 11 update (after convoy takes 4–5; `ledger_dmc.py status`):** campaign 25 667 s of 43 200 s and $2.8637 of $10, now including the `m5v` validation take (4144 s) and the two convoy invocations (1718 s and 1602 s); `cv` 8149 s of its amended 12 600 s share, $0.3751, valid 5, bring-up aborts 1 of 3 (`cvH_t04_a1`). Wall shares were amended a second time (registration section 12.4). The table above is kept as written at Rev 5.

**Rev 13 update (after the convoy rerun; `ledger_dmc.py status`):** campaign 27 223 s of 43 200 s and $2.8784 of $10; `cvy` 1556 s of its 7200 s share (registration section 13.6), $0.0147, valid 1, bring-up aborts 1 of 3 (`cvY_t01_a1`).

Wall is counted from VM start to TERMINATED. The `m5` invocation also spent about 24 min in 11 failed VM start attempts before the VM started, which are not booked.

### Valid Response, Accepted Plan, Changed Behaviour

The counts are per analysis (decision artifact); stage-2 retreat calls are not counted. The columns are:

- **Valid VLM response:** the call completed and the answer parsed (`finish_reason=completed`, `parse_status=valid`).
- **Accepted VLM plan:** plan verification kept the model's plan with no edit (`plan.provenance=vlm_verbatim`).
- **VLM plan changed executed behaviour:** the commands executed differ from M3's default plan for the same snapshot (`COUNTERFACTUAL executed_differs_from_m3_default=True`, the basis of the VLM-driven label). This is computed for the intersection only.

| Scenario | Valid VLM response | Accepted VLM plan | VLM plan changed executed behaviour |
|---|---|---|---|
| Intersection, 5 takes | 9 of 9: 5 jam decisions plus 4 "no congestion" answers | 1 (take 5). The other jam plans: 2 `repaired` (takes 2, 4), 2 nulled as invalid structure (takes 1, 3) | 1 (take 5): the recede order only, a 0.010 m chi near-tie. Takes 1–4: False |
| Convoy, 5 takes (Rev 11: + takes 4–5; Rev 13: + rerun take `cvY_t01_a2`, now 6 valid takes across `cv` and `cvy`) | 48 of 48 (Rev 13: 50 of 50) | 3 of 48 (20 `repaired`, 25 `m3_default`; takes 4–5 add 0 verbatim, 5 `repaired`, 7 `m3_default`). Rev 13: the rerun adds 2 valid analyses, 0 accepted unchanged (1 `repaired` yield, 1 "no congestion") | Not computed (no default comparison for this scenario). The first-trigger yield was executed as the model named it in 3 of 3 takes; in takes 4–5 (Rev 11) the model's strategy and yielder were executed, and M3 added robot_3 and robot_4. |
| Head-on, 1 take | 2 of 2 | Not applicable: plan channel off (prompt v2) | Not computed. Both strategies (`reverse`, `yield`) were dispatched as named, but the gate swapped decision 2's yielder (robot_1 → robot_2). |
| Five robots, 1 take | 8 of 8 | 2 of 8, both executed as named (1 `repaired`, 5 `m3_default`; 6 of 8 withheld by grounding refusals) | Not computed |
| **Total** | **67 of 67** (Rev 11; 55 of 55 at Rev 5; Rev 13: 69 of 69) | **6** (of the 65 plan-channel analyses) | **1** |

### What This Does and Does Not Show

- **Intersection.** The pipeline carried a model-chosen order to execution, with all checks on, once in five takes (take 5). The choice was a near-tie, 0.010 m of chi against a 0.15 m tolerance, and it changed only the timing of the two recedes: robot_3 backed out about 9 sim-s before robot_4. Pockets, the cross, the release and the crossing order stayed on chi. The model's order follows ascending robot id, as it mostly does offline.
- **Head-on.** It resolved 2/2 because the feasibility gate corrected the model's yielder: robot_1 had 0.70 m of retreat room against 1.08 m required, so robot_2 yielded. The model's first strategy (`reverse`) ran and did not clear the scene.
- **Convoy: unresolved in 3 of 3.** The first yield ran as named, but the model named only the standoff pair. The two queued robots, never commanded, followed through the gate and latched. The legacy vocabulary then had no recovery: the 33 later proposals ran as 8 s waits. Stating the hold-back state in the prompt did not change this offline: 0 of 22 answers per condition grounded into the four-robot sequence, so no retake was run (section 5.8, Rev 6). **Rev 11:** the owner then approved grounding fix (b); with it, takes 4–5 were run (section 12). Both were again Unresolved failure (1/4): the hold kept robot_3 and robot_4 in place as designed, but the model chose robot_1 as yielder both times, and robot_2's escort west latched against the held robot_3.
- **Convoy rerun (Rev 13, section 14): one system-corrected resolution.** In one further demonstration take (kit `cvy`) all four robots arrived. The model chose the strategy (yield) and, this time, the feasible yielder robot_2; it again named only robot_1 and robot_2. The grounder's queued-robot hold added robot_3 and robot_4 to the crossing order and held them until their turn; the counterflow yielder correction was armed but had nothing to correct, so it was not exercised live (the hold alone gives the same command). n = 1 and illustrative: it shows the corrected pipeline can execute the resolving sequence live, not that the VLM resolves convoy congestion. The five earlier convoy takes stay Unresolved failure.
- **Five robots: unresolved.** Two model decisions were executed as named, but the yield pairs then latched within 0.45 m. robot_3's escort did not stall on its own: the straight escort segment crossed rack island `obstacle_2`, and robot_3 drove into the island's east face and stayed pinned there until the escort timed out (section 8.7, Rev 6). The six later proposals were refused by grounding checks (retreat room, junction or lane), and Layer 2 went quiet after sim 275.5 s, as the registration expected. The "unresolved" label therefore partly reflects an escort path error, not only the model's decisions or the grounding refusals.
- **Safety scope (Rev 6).** Ground truth logs no contacts of either kind: `robot_robot_contacts` and `robot_static_contacts` are hard-coded empty lists (`isaac/vgu_sim/acceptance_logging.py:99-100`). Every "0 contacts" statement in this report is scoped as follows:
  - **Robot-robot:** supported only by the GT closest centre distance, computed from poses (GT `min_pairwise_distance_m`, minimum per valid take 0.2176–0.3701 m). That is above the 0.20 m floor and the 0.076 m nose-to-nose contact distance.
  - **This follows a standing ruling.** The prereg-v2 caveats of 2026-10-08 and 2026-10-09 (main repo, `fc73151`) and `docs/reports/2026-09-25-overnight-findings.md`:1852–1871 already ruled that the GT contact fields are not evidence, and that contacts must be recomputed from distances. The Rev 1–5 contact lines of this report ran against that ruling.
  - **Robot-static:** not logged by ground truth. The only check is the distance recompute in section 8.7. It found robot_3 within 5 mm of `obstacle_2` in 4526 of the 4534 GT rows from sim 146.7 s to 600 s (8.7.2).
- **What it does not show.** Nothing here is controlled evidence. One VLM-driven take in five, with n ≤ 5 per scenario, gives no rate, no comparison with Layer 2 off, and no claim that the model reasons the order from the scene.

### Open Owner Decisions (as Identified in the Sections; No Further Recommendation)

- **Convoy fix options** (section 5.5): (a) prompt/kit: hold-back state or a platoon sentence; (b) grounding: hold uncommanded robots whose goals lie across the corridor, or refuse `continue` for them; (c) recovery: a post-gate cluster template. Each changes the registered convoy experiment's Arm A, so each needs a registration amendment or nothing. Rev 6: a prompt-only form of (a) was tested offline and is a no-go (section 5.8). Rev 11: option (b) was built (`fix/convoy-hold-queued-robots`, default off) and used for demo takes 4–5 only (section 12); the registered experiment's Arm A is untouched.
- **Options-detail prompt/parser fix** (section 2.5): (a) render the options detail so it cannot be read as an action, or (b) narrow parser tolerance for an exact offered `"<action> (<detail>)"`. Either is a third fix cycle and needs the owner's approval.
- **Log-filter lines** (sections 6.5, 7.3, 5.6, 8.5): whether to add the `yield re-grounded` swap line and `dispatch_order_source` to the demo panel's fixed filter, which these videos left unchanged. The convoy and five-robot refusal lines (`yield refused`, `refusal withheld`) are in the same position.
- **Intersection yielder gap** (registration 10.1, section 3.4): it stays open by owner decision.
- **Escort obstacle guard** (section 8.7, Rev 6; built, live check pending, Rev 8: see section 10): neither M3's escort grounding nor M4's `drive_heading` checks the straight escort segment against declared static obstacles. One option is for grounding to refuse, or shorten, an escort whose swept segment crosses a declared obstacle box grown by the chassis half-width. Any such change alters the S1b grounding that registered arms use, so it needs a registration amendment or nothing.
- **Static-contact logging** (section 8.7, Rev 6; built, Isaac validation pending, Rev 8: see section 10): `robot_static_contacts` (and `robot_robot_contacts`) are hard-coded empty (`isaac/vgu_sim/acceptance_logging.py:99-100`). The options are (a) a PhysX contact-report detector on the chassis and obstacle prims, or (b) a per-row distance recompute in the logger (the chassis collision box against the declared obstacle boxes, as section 8.7 does offline). Until then, robot-static contact claims need an offline recompute.
- **Follow-up builds (Rev 8, section 10):** the escort obstacle guard is built on a separate branch (default off, offline replay only, live check pending, E18 margin rule awaits the owner), and ground-truth contact logging is built on another (always on, Isaac validation pending).
- **Known wording issue (Rev 6; corrected by errata, Rev 8):** several reports on other branches state "0 GT contacts" or "no contact" from the empty fields, or from robot-pair distances alone in scenes with static obstacles. They are listed in section 8.7.6. Each now carries a dated erratum (v7d `f30869e`/`04a1956`, v7a `88aad36`/`3cb947e`, v6d `b534d17`, v7j `d076a54`/`7586857`).

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
| `cv` (kit `cvh`) | `cvH_t04_a1` | bring-up abort (`NAV2_BRINGUP_FAILED`, robot_3 stack, 3/4 active) | `cvh/MANIFEST_20261115T102615Z.md5` | `6c9d0e22f423db6cd24a999b7c47c062` (89, both attempts) |
| `cv` (kit `cvh`) | `cvH_t04_a2` | take 4, Unresolved failure (1/4) | `cvh/MANIFEST_20261115T102615Z.md5` | `6c9d0e22f423db6cd24a999b7c47c062` (89, both attempts) |
| `cv` (kit `cvh`) | `cvH_t05_a1` | take 5, Unresolved failure (1/4) | `cvh/MANIFEST_20261115T105655Z.md5` | `bd017429311c049d350941d932882581` (61) |
| `cvy` | `cvY_t01_a1` | bring-up abort (`NAV2_BRINGUP_FAILED`, robot_3 stack, 2/4 active) | `cvy/MANIFEST_20261115T142504Z.md5` | `073e8d029b51e135ea9bd194bf82c9cb` (82, both attempts) |
| `cvy` | `cvY_t01_a2` | demonstration take 1, Resolved (4/4) | `cvy/MANIFEST_20261115T142504Z.md5` | `073e8d029b51e135ea9bd194bf82c9cb` (82, both attempts) |
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
- **No convoy retake was run.** The convoy rows of this report are unchanged. (Rev 11: a retake was later run with grounding fix (b) instead; see section 12.)

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

- **File.** v7g `data/demo/campaign/m5D_t01_a1_panel.mp4` (git-ignored), md5 `33e9f5eedd7fb56edd007d8b728ea8c0`, 21.3 MB (Rev 7 re-render; no `_small` copy needed). The first render is kept beside it with a `_v1` suffix (`m5D_t01_a1_panel_v1.mp4`, md5 `75bf99e64c7ebea10573f08eb62440c3`, with its transcript, stills and md5 file). Beside it: transcript, five stills (call, decision, dispatch, mid, end) and `m5D_t01_a1_panel.md5`. Renderer v7g `feat/demo-panel-renderer` (`5198c0b`), unchanged, with the same arguments as the other campaign videos. The Rev 7 render used the v1 arguments plus one caption line (below).
- **Left pane.** Real camera recording, `/perception/annotated_frame`, all 7 segments, `annotated_framemap.json`.
- **Captions** (outside the terminal):
  1. "Unresolved failure — take 1 of 1 (limitation demonstration)";
  2. "Model: Gemini Robotics-ER 2 (gemini-robotics-er-2-preview); Layer 2 on; 1 of 5 robots arrived.";
  3. "Two decisions were executed (yield + escort); six later proposals were refused by grounding checks; the scene stayed jammed.";
  4. (Rev 7) "Decision 2's escort drove robot_3 straight into a rack island (the escort path has no obstacle check); it stayed against the island until the escort timed out." (inserted before the disclosure line);
  5. "Illustrative demo, not controlled experimental evidence. Seed position 21 (exploratory extension seed); shows a current limitation." (the section 7 lines).
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
  - **Rev 7: the captions now carry the escort finding (8.7).** The Rev 7 render adds the 8.7 caption line (item 4 above) and keeps all other lines. All five caption lines fit above the footer with the renderer's usual wrapping. The terminal pane is unchanged: the transcript JSON is byte-identical to v1 (`diff` clean, md5 `40ca685a5b6219c592efa88a5ca8b0f4`), and the filter was not widened. ffprobe: H.264, 1920x1080, 24 fps, 4839 frames, 201.63 s, 21,312,857 bytes. The new line was checked on the call still. The v1 video (kept) lacks the line; its caption 3 ("the scene stayed jammed") is true but incomplete.

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
- **Distance recompute (an ad hoc offline check, no committed script).** For every GT row, the URDF chassis box and wheels were placed at the `base_link` pose and heading, and the gap to each declared box was measured, sampled at about 5 mm. robot_3 to `obstacle_2`: the gap is 5 mm or less in 4526 of the 4534 GT rows from sim 146.7 s to 600 s, with a minimum of −0.2 mm (touching, within the sampling). The exceptions are 8 rows at 266.5–268.0 s, up to 13.5 mm (Rev 8: the span read 266.5–267.7 s before; section 10.2), while the line-hold servo turned the robot against the face. GT is sampled at 10 Hz, so a moving robot's true minimum gap can be a few mm lower than any row shows. The shapes are the URDF's; the imported USD collision shapes were not inspected. robot_2 to `obstacle_2`: 3.8 mm at sim 270.7–270.9 s, during its 268–272 s move. That is a possible brief graze, not established.

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

#### 8.7.6 Known Wording Issue in Other Reports (Listed; Corrected by Errata 2026-11-15)

This list was written before the errata. Each report below has since received a dated erratum ("2026-11-15 Erratum — Contact Wording") that scopes its contact statements to the robot-pair distance, and its affected lines carry "(corrected 2026-11-15, see erratum)". The errata are v7d `f30869e` and `04a1956`, v7a `88aad36` and `3cb947e`, v6d `b534d17`, and v7j `d076a54` and `7586857`. The errata inserted about 10 to 14 lines near the top of each report, so the line numbers below are the current ones; they replace the pre-erratum numbers this section first gave. Before correction, the reports stated "0 GT contacts" or "no contact" from the empty fields, or from robot-pair distances alone in scenes that have static obstacles.

- **Read from the empty GT fields:**
  - v7d `docs/reports/2026-11-14-ib10-safety-default-arm-results.md`:74 (was :62; the 0.18 m distance claim is sound; "the GT contact lists are also empty" carries no weight), :86 and :372 (was :74 and :360; table "GT contacts 0 / 0"), :346 (was :334; "0 GT contact entries").
- **Method ambiguous (the "contact frames" count does not say whether it read the empty field or frames below 0.18 m; robot-robot only either way, and IB10 declares no static obstacles):**
  - v7a `docs/reports/2026-11-13-ib10-live-resolution-results.md`:47, :71, :75, :156 (was :35, :59, :63, :144; "zero contact frames in every GT file"); its success criterion at :37 (was :25) is distance-based;
  - v6d `docs/reports/2026-11-13-thesis-evidence-register.md`:91–92 (was :74–75; "0 GT contacts", the two IB10 entries); :72 (was :55; "2/2 arrivals with zero contacts", quoted from `2026-10-03-loop-family-and-visual-pass.md`:250, mock smoke; that cited report was not edited, so :250 is unchanged); :89 (was :72; "no contact", IB10 closure, mock).
- **From robot-pair distances, stated as general "contact" in scenes with static islands:**
  - v6d `docs/reports/2026-11-13-thesis-evidence-register.md`:102 (was :85; "contact gate PASS 10/10 (GT min 0.225-0.424 m)", S1b tranche 1, robot pairs only);
  - this branch: `2026-10-12-shield-fix-and-minibatch.md`:37, :98, :188 (was :25, :86, :176) and `2026-10-17-escort-filter-minibatch.md`:147, :198, :296 (was :135, :186, :284) (S1b, "zero contacts" from pair distances).
- **Older reports on this branch reading the empty fields:** `2026-10-03-step7b-oracle-freeze.md`:257 (was :246), `2026-10-05-follow-waypoints-validation.md`:36, :173, :190 (was :24, :161, :178), `2026-10-07-gpt56-sol-swap.md`:318 (was :307) (method not re-checked here; each carries an erratum now). `2026-10-08-s1-pilot.md`:174 and `2026-09-25-overnight-findings.md`:232, :262 were not edited, so their numbers are unchanged. Those two overnight-findings lines are already corrected in that report (:1852–1871), and `2026-10-08-s1-pilot.md`:174 already carries the caveat.
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

- **Rev 10 (v3, current).** v7g `data/demo/campaign/demo_campaign_combined.mp4`, md5 `de8cb6ed07e42008b8acb3f9274352db`, 26.0 MB (26,041,624 bytes), `--crf 26`, renderer v7g `8069734`. ffprobe (verified): H.264, 1920x1124, 24 fps, yuv420p, 6610 frames, 275.42 s. Same manifest as Rev 7 plus one clip inserted after excerpt 4 (row 4b below). The Rev 7 set is renamed with a `_v2` suffix (`demo_campaign_combined_v2.mp4`, md5 `1e0fd52025624da723766701ec412131`, with its manifest, sidecar and md5 file; file names inside the md5 file updated, contents unchanged). crf 26 rather than 25 keeps it under 28 MB; text was checked legible on full-resolution stills of the 4b title card and of a mid-excerpt frame (sim 86.33 s, robot_1 escorted past the parked robot_2; caption bar "excerpt 5.5-33.5 s of 80 s"). The bullets below describe the Rev 7 file, now `_v2`, unless marked.
- **File (Rev 7, now `_v2`).** v7g `data/demo/campaign/demo_campaign_combined.mp4` (git-ignored), md5 `1e0fd52025624da723766701ec412131`, 26.8 MB (26,757,620 bytes; Rev 7 re-render, `--crf 25`, 244.4 s, 5866 frames, 1920x1124). The first combined video is kept with a `_v1` suffix (`demo_campaign_combined_v1.mp4`, md5 `ace3cc0d765a504441a29d54e74ac3df`, 25.6 MB, 229.9 s, with its manifest, sidecar and md5 file). Beside the new one: the manifest `demo_campaign_combined_manifest.json`, the tool's sidecar `demo_campaign_combined_sources.json` (each source's path, md5, trim and labels) and `demo_campaign_combined.md5`. It was made with `render_demo_panel.py combine` (renderer `5198c0b`, unchanged) at `--crf 25`. The default crf 23 gave 29.3 MB, over the 28 MB limit.
- **Output (ffprobe, verified).** H.264, 1920x1124 (a 44 px caption bar above the 1080p clips), 24 fps, yuv420p, 5866 frames, 244.42 s (Rev 7; v1: 5518 frames, 229.92 s).
- **Order and trims** (source video seconds; each excerpt follows a 3 s title card, and the caption bar prints the trim):

| # | Source | Title card: outcome, take | Excerpt | What it contains |
|---|---|---|---|---|
| 1 | `ibD_t05_a1_panel.mp4` (104.1 s) | VLM-driven execution, take 5 of 5 | 22.5–97.5 s | jam call `df397030`, `provenance=vlm_verbatim`, recede dispatch robot_3 then robot_4, cross and release, robot_1's arrival (sim 149 s) |
| 2 | `cvD_t01_a1_panel.mp4` (273.3 s) | Unresolved failure, take 1 of 3 | 5.5–37 s | first call, `vlm_verbatim` yield, dispatch, `gate_admit` and `gate_release`; the latch forms at about sim 75 s |
| 3 | same | Unresolved failure, take 1 of 3 (later excerpt) | 255–271.9 s | the last proposal (`m3_default`, a wait) and the jam at sim 250–260 s, up to the last camera frame |
| 4 | `hoD_t01_a1_panel.mp4` (76.0 s) | M3-default resolution, take 1 of 1 | 26.5–69 s | decision 2 call, `yield` robot_1 in the answer and the dispatched yield to robot_2, gate, both arrivals |
| 4b (Rev 10) | `ER2LIVE_20260930_panel.mp4` (80.0 s) | VLM-driven execution, "recorded 2026-09-30 (earlier run)"; card title "Head-on with obstacle (ER-2), earlier run" | 5.5–33.5 s (sim about 27.7–98.8 s) | call `67d5cb88`, decision (yield, robot_2), dispatch (yield to robot_2, `temporary_wait` to robot_1), robot_2 backing out, the escort pass at sim 86 s and robot_1's `arrived at base goal` line (video 32.3 s). The excerpt ends about 2 sim-s into robot_2's stall; the Nav2 recovery and robot_2's arrival (sim about 120–136 s) are outside it |
| 5 | `m5D_t01_a1_panel.mp4` (201.6 s) | Unresolved failure, take 1 of 1 | 7.5–37 s | first call, `vlm_verbatim` yield, dispatch, `gate_admit`, `gate_cleared` |
| 5b (Rev 7) | same | Unresolved failure, take 1 of 1 (middle excerpt); card title "escort into a rack island" | 62–73.5 s (sim about 106–182 s) | decision 2: `vlm_verbatim` yield for robot_2, dispatch, `gate_admit` (escort 1.604 m, sim 138.7 s), and robot_3 stopped at the island's east face at sim about 147 s |
| 6 | same | Unresolved failure, take 1 of 1 (later excerpt) | 183–199.5 s | the last analysis (`plan absent`), then 30x sim time to sim 597 s with both clusters in place |

- **Title-card notes** (one line each, consistent with sections 5–8):
  - intersection: "Model chose the back-out order (robot_3 first); default was robot_4 first by ~1 cm; 1 VLM-driven take of 5";
  - convoy: "The model's yield ran as named, but it left out the two queued robots; they followed through the gate and the scene latched";
  - convoy, later: "All 11 later proposals ran as 8 s waits; 0 of 4 robots arrived by the end (sim 260 s); takes 2-3 were also 0 of 4";
  - head-on: "Grounder corrected the model's yielder: robot_1 had 0.70 m retreat room (< 1.08 m), so robot_2 yielded; 2 of 2 arrived";
  - five robots: "Limitation demonstration: first decision (robot_1 yields, robot_4 escorted) executed and completed";
  - five robots, middle excerpt (Rev 7): "Limitation demonstration. Decision 2's escort drove robot_3 into a rack island (no obstacle check on the escort path).";
  - head-on, earlier run (Rev 10): "Same head-on scene. Here the model chose the feasible yielder and the gate kept it; the escort and Nav2 recovery are the system's. In today's take the model chose the other robot and the gate swapped it.";
  - five robots, later: "Six later proposals were refused by grounding checks; no analysis after sim 275.5 s; 1 of 5 arrived by sim 600 s".
  Each card also carries the tool's fixed line "Illustrative demonstration, not controlled experimental evidence.". The per-scenario disclosure captions of the source videos stay visible under each scene pane.
- **Checks (verified).**
  - Before combining, ffprobe frame counts matched each source's duration: 2499 / 104.125 s, 6559 / 273.29 s, 1825 / 76.04 s and 4839 / 201.63 s. No excerpt ends past a source's last frame.
  - Stills viewed: all six title cards, and one frame from inside each excerpt. Each frame's caption bar names the scenario, outcome, take and trim. The text is legible at crf 25 (checked on a full-resolution frame of excerpt 4).
- **Rev 7.** The five-robot cards now cover the escort finding through a third five-robot excerpt (5b), placed between excerpts 5 and 6. The new card note is on this middle excerpt (decision 2 and the escort into the island); the "five robots, later" card keeps its original note, so no disclosure was dropped. Order and all other trims are as in v1. The video time for sim about 147 s was taken from the render's timeline (video 62–73.5 s runs at 8x sim time, sim about 106 to 182 s). Verified on stills of the combined video: the 5b title card, and a frame at sim 146.3 s showing robot_3 at the island's east face (the new caption line is on the five-robot panel; the caption bar prints "excerpt 62-73.5 s of 201.6 s"). ffprobe of the combined video as above; total 4 min 4 s, under 28 MB. The terminal pane of the five-robot video is unchanged (transcript diff clean, see 8.5).
- **Why two excerpts for each unresolved take.** One contiguous excerpt could not show both the first executed decision and the late, still-jammed scene within about 4 minutes. The cut is never hidden: each part has its own title card, and the caption bar prints its trim.

## 10. Follow-Up Builds (Added 2026-11-15, Rev 8)

Two fixes for the defects in section 8.7 were built afterwards on separate branches. This report was not edited by them, and neither was run live in Isaac Sim. Each result below is quoted from that branch's report, not re-run here.

### 10.1 Escort Obstacle Guard

- **Where.** Branch `fix/escort-obstacle-guard`, worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7l`, report `docs/reports/2026-11-15-escort-obstacle-guard.md` there (tip `72c08c8`). Based on `8933863` (VM pin `68e67b5` plus the safety-exemption fix).
- **What it is.** An M3 grounding key `grounding.escort_obstacle_guard`, default off. Each escorted passer's straight leg is clipped against every declared static obstacle grown by the chassis half-width plus the retreat margin (0.09 + 0.05 = 0.14 m). It refuses rather than shortens: a shortened escort could never meet `clear_m`, because the two are equal in derived grounding. A blocked yield degrades to `yield=infeasible:escort_hits_obstacle:...`, which M5 withholds. Key off is byte-identical. M4 is untouched.
- **Offline replay (re-grounding stored decisions; no live run).**
  - m5D decision 2 (`a15f3fc5`) is refused: `escort_hits_obstacle:robot_3:obstacle_2:0.414`.
  - m5D decision 1, the head-on escort and every other campaign escort are unchanged. Among the 24 October five-robot escort commands only E18 `1feb2c4e` changes.
  - E18 `1feb2c4e` is also refused. It was admitted but never drove (GT motion 0.002 m), so the physical outcome cannot show whether it would have grazed.
- **Tests.** 33 test functions (35 cases) added. Full unit suite: failing set unchanged (57 before and after), 6967 to 7003 passed.
- **Owner decision pending: the E18 margin rule.** The refusal turns on a start-inside-the-grown-box rule and on M1's pose to the millimetre. The report lists (a) keep the retreat sweep's rule as built, (b) treat a parallel run within the margin as blocked even from inside, (c) lower the escort margin to the bare half-width. Each changes E18 and nothing else in the replay.
- **Not covered.** Undeclared geometry, legacy-mode grounding (the convoy takes) and M4 execution. Using the key in a scored arm needs a registration amendment (the open owner decision in the final summary).
- **Status.** Built, not run live. A live check is pending.

### 10.2 Ground-Truth Contact Logging

- **Where.** Branch `feat/gt-contact-logging`, worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7m`, report `docs/reports/2026-11-15-gt-contact-logging.md` there (tip `b5eaee5`). Also based on `8933863`.
- **What it is.** `isaac/vgu_sim/contact_geometry.py` places the URDF collision shapes at each logged `base_link` pose and measures the signed planar gap to every authored box and to each other robot. A gap of 5 mm or less is a contact entry. It is always on, with no flag: no pinned scorer changes its verdict between old and new logs. Rows carry `contact_model: urdf_footprint_v1`, plus unthresholded `min_static_gap_m` and `min_robot_robot_gap_m`. A PhysX contact report was not built.
- **Recompute over 44 recorded bundles** (11 demo, 11 IB10 live, 11 IB10 safety, 11 tranche 1; read-only; in all 44 the logged lists are the empty stub):
  - one sustained robot-static contact: `m5D_t01_a1`, robot_3 against `obstacle_2`, 4526 of 4534 rows from 146.7 s within 5 mm, minimum −0.16 mm;
  - two brief grazes within noise, not established contacts: m5D robot_2 against `obstacle_2` (minimum 3.79 mm at 270.8 s) and tranche-1 E30 Arm A robot_2 against `obstacle_1` (minimum 0.97 mm at 48.9 s);
  - no robot-robot contact in any bundle (closest pair 82.1 mm, `ib10L_e09_armA_a1`). A recorded robot-robot contact (G4, 0.076 m nose to nose) was recomputed as a positive control: sustained contact from 53.1 to 104.3 s.
- **Discrepancy with section 8.7.2, resolved.** That report states the 8 exception rows at 266.5–267.7 s. The contact-logging report finds them running to 268.0 s (rows 267.8–268.0 s at 13.45, 9.4 and 7.0 mm). The count (8), the 13.5 mm maximum, the 4526 of 4534 figure and the minimum all agree. I kept the contact-logging report's 268.0 s and corrected 8.7.2. Two reasons: it comes from a committed tool at exact gaps, where 8.7.2 was an ad hoc 5 mm-sampled check with no script; and the count fits only the longer span. At 10 Hz, 266.5–267.7 s holds 13 rows, of which 266.6 s and 266.8–267.4 s (8 rows) are within 5 mm, leaving 5 exceptions, not 8. The raw bundle was not re-opened here. Two smaller differences are inside 8.7.2's own sampling: robot_2 at 270.7–271.0 s (here 270.7–270.9 s) and E30's 1.0 mm (8.7.4: 1.2 mm).
- **Tests.** 54 new tests. Full unit suite: failing set unchanged (57 before and after), 6967 to 7020 passed.
- **Status.** Built, not validated in Isaac Sim. The new values are a geometric footprint measure. They become citable only after a live run confirms entries appear when a robot is pinned. The `fc73151` ruling (v1/v2 contact scoring by distance recompute) stands.

### 10.3 Open Items After Rev 8

- Escort guard: live check, and the owner's E18 margin rule.
- Contact logging: Isaac Sim validation run.
- Older-report wording: corrected by the errata listed in section 8.7.6.

## 11. Earlier Recorded Run With an Uncorrected VLM Decision (ER2LIVE, 2026-09-30; Added 2026-11-15, Rev 9)

**Status.** Illustrative, not controlled evidence, and not part of this campaign. n = 1. The run was selected *because* it qualifies, after a read-only audit searched the recorded bundles for such a case, so it says nothing about how often this happens. The verification below was done offline on the bundle (read-only). The planned panel video and its addition to the combined video were **not rendered**: the Mac had 5.06 GiB free against the 5.5 GiB floor set to protect a live VM take (see 11.5). Rev 10: both were rendered afterwards (11.5).

**Run.** Bundle `data/logs/vm_runs/live_demo/ER2LIVE_20260930_152222/` (main checkout). `CONDITION.txt`: scenario `head_on_asymmetric_w0p2_eopen_bshort_o0`, backend `gemini`, `tree=3959d7f` (2026-09-30), `record=1`, `purpose=live_vlm_demo_video`. The same scene as section 6.

### 11.1 Verification (Verified From the Bundle Unless Marked)

| # | Check | Result |
|---|---|---|
| 1 | Model output, request `67d5cb88` (scene stamp 29.83 s) | `raw_text` and parsed `.decision`: `deadlock`, strategy `yield`, `yield_robot` robot_2, `crossing_order` robot_1 then robot_2, `blocker_kind` robot. `gemini-robotics-er-2-preview`, 1 attempt, `parse_status=valid`, 0 refusals, 4.9 s latency. Prompt v2 with no plan channel (`plan` key absent), presentation order `id_asc` (robot_1 listed first; the model named the second-listed robot). **Pass** |
| 2 | Gate mode, no swap | `grounding_yield_feasibility: "swap"` (gate on). `yield_regrounded_reason`, `yield_robot_grounded_from` and `yield_refusal_reason` null; `grounding_degradations` empty; no `yield re-grounded` line in m5.log. The gate logs room figures only on a shortfall, so **this run logged no feasibility numbers**. The scenario's generator header (at `3959d7f`) gives west room 0.70 m < 1.079 m required (robot_1 cannot park), east open (robot_2 can). The `regrounded_from: robot_1` in the artifact belongs to the classical *shadow* (`shadow_classical.classical_retreat`, whose FCFS rule picked robot_1), not the executed path. **Pass** |
| 3 | Stage 2 | Candidates A (1.789, −0.36) and B (1.789, +0.36): mirror images, identical backup 1.633 m, lateral clearance 1.901 m, sweep clearance 0.268 m. Listing order **B, A**; default A; the model answered B ("free of obstacles"); grounded label B. GT: robot_2 parked at x 1.80, y 0.34–0.37 (sim 60–90 s), i.e. B was dispatched and reached. **Pass**, but the pick was the first-listed of two equivalent options, so it shows that the choice was executed, not that it was better |
| 4 | Commands, other analyses, resolution path | Two commands under `67d5cb88-yield`: `yield` to robot_2 and `temporary_wait` to robot_1 (m4 `command received`). M4 phases (GT): robot_2 backs from sim 33.4 s, reaches x 1.78 at 51.3 s, steps aside by 60.0 s; M4 escort of robot_1 starts (m4 `escort robot_1: ACTIVE`), robot_1 moves from 65.0 s, passes robot_2's x at 86.0 s; `escort complete: moved 2.557 m`; both commands `COMPLETED`; robot_1 at goal (M5 `arrived at base goal`, 0.10 m). Then M4 `resume base mission` for both. Robot_2's resumed Nav2 goal stalled at about (1.22, 0.15) from sim about 97 to 119.8 s; three further analyses (`fbaa01a8`, `26dcc7a3`, `a5d170d6`) each answered `congestion_detected=false`, `no dispatch`; robot_2 moved again right after Nav2's own `Failed to make progress` abort and local-costmap clear (nav2_r2 wall …082.94, mapped to sim about 120 s via the camera-localizer `scene_stamp` lines; GT motion resumes 119.8 s) and arrived. No fallback, default substitution or re-dispatch. **The standoff was resolved by the model's yield as executed** (robot_2 out of the corridor, robot_1 escorted through). Robot_2's own final leg was base-mission resume plus a Nav2 recovery, not a model decision. **Pass** |
| 5 | Arrivals, closest pair, contacts | GT `distance_to_goal < 0.3 m`: robot_1 at sim 91.6 s, robot_2 at 135.9 s (M5 `arrived at base goal` lines at wall …015.43 and …138.25, 0.10 and 0.08 m). GT closest centre distance 0.2643 m at sim 25.5 s, during the approach before the call (M4's 0.45 m latch stopped the pair); 0.370 m at 86.1 s while robot_1 passed the parked robot_2. Offline recompute (v7m `scripts/recompute_gt_contacts.py`, called through `recompute_bundle` with the scenario YAML taken from `3959d7f`, because the bundle has no `scenario.yaml`; output in scratch): robot-robot verdict `clear`, minimum footprint gap 0.186 m at 25.5 s; robot-static `clear`, minimum 0.098 m (robot_1 to `blocker_west`, at spawn) and 0.127 m (robot_2 to the north aisle-barrier block at 120.7 s). **Pass** |
| 6 | Code and config | `tree=3959d7f`. `orchestrator_used.yaml` and `rag_used.yaml` match today's head-on take (`hoD_t01_a1` `orchestrator.overlaid.yaml`, `rag.overlaid.yaml`) line for line after comments are stripped: obstacle text on (`prompt_static_obstacles: true`), pairwise geometry on, feasibility gate `swap`, stage-2 selection on, order `random`, classical shadow on. The yaml's `reasoning_backend_id: openai` is the restored file; `launcher.log` shows the swap `openai -> gemini` for the run and back on exit. The code differs from today's kit: M4 here has no `hard_contact_floor_m`, `scoped_clearing_exemption` or `crossing_chain` gate (its startup line ends at `exempt_actions=reverse,yield`), and the pass is driven by the older escort phase |
| 7 | Oracle | Scenario `oracle.correct_yielder: robot_2`, `feasible_yielders: [robot_2]` (at `3959d7f`). The model's yielder matches it |

### 11.2 What Was the Model's and What Was the System's

- **Model:** congestion type, strategy `yield`, yielder robot_2, and the stage-2 side (B).
- **System:** the trigger (robot_1 stalled ≥ 12 s after M4's 0.45 m latch stopped both), the 1.633 m backup and both retreat candidates (M3 derived grounding), robot_1's `temporary_wait`, the escort that drove robot_1 2.557 m to its goal, the base-mission resume, and Nav2's recovery for robot_2's last leg.
- **Contrast with section 6 (same scene, today).** There the model named robot_1 and the gate swapped it to robot_2. Here the model named robot_2 and the gate had nothing to correct. Both are single takes; no rate follows.

### 11.3 Caveats

- n = 1, an earlier code version (`3959d7f`), selected because it qualifies.
- The stage-2 pick was between mirror-equivalent positions and matched the listing's first slot.
- Robot_2's arrival needed about 22 sim-s of Nav2 stall and recovery after the yield completed.
- No feasibility numbers were logged for this request (11.1, row 2).

### 11.4 Wider Counts (Quoted From a Read-Only Audit, Not Re-Checked Here)

A read-only audit of the recorded log bundles (which did not view video frames) reported:

- about 110 decisions in 71 recorded log bundles that were dispatched with no yielder swap, repair, substitution or default (ER-2 79; strategies: reverse 41, yield 40);
- 66 further candidates it could not verify (no m5 log);
- only three sources with camera recordings: ER2LIVE, the 2026-10-06 single-robot reroute demo (`data/logs/vm_runs/reroute_demo_live/v3_live_er2_reroute/`, request `28ffca8b`), and this campaign's takes.

In this campaign the two dispatched five-robot decisions were the two `vlm_verbatim` ones, with no yielder swap. The system added shield waits, and decision 1's retreat was the default (section 8; stated in the task brief as confirmed, not re-checked in this section).

### 11.5 Video (Rendered in Rev 10)

- **Files** (v7g `data/demo/campaign/`, git-ignored). `ER2LIVE_20260930_panel.mp4`, md5 `93cbfe7108e6a9ca9a71fc4c7c79bd47`, 7.8 MB (7,806,653 bytes; no `_small` copy needed); ffprobe (verified): H.264, 1920x1080, 24 fps, yuv420p, 1919 frames, 79.96 s. Beside it: `ER2LIVE_20260930_panel_transcript.json` (md5 `6e58b0337893920e81877e44312d5da1`), the frame map `ER2LIVE_20260930_framemap.json` (md5 `583ce01badc9026dc737ee5c2939261c`), stills and `ER2LIVE_20260930_panel.md5`. Renderer v7g `8069734`: `0212306` adds the scene-log fallback (`m5_scene.jsonl`, else `scene_<session_id>.jsonl` from `m5.log`, else the only `scene_*.jsonl`, else an error), `8069734` reads `variant=` as the scenario in the top caption and leaves out a missing arm. Unit tests `test_demo_panel.py` and `test_demo_combine.py`: 53 passed. Camera pane: `annotated_000.mp4` + `annotated_001.mp4`. Terminal: the fixed filter and `jq` lines unchanged; no grounding line (no `plan`).
- **Frame map.** The campaign decoder `ho/kit/overlay_framemap.py` (md5 `a5f2dd256222b03e93784995fa6ec0a5`), run **unchanged** (Python 3.11.7, OpenCV 4.13.0), decoded **3745 of 3745** frames (median IoU 0.849; 3739 strictly increasing anchors, six frames repeat the previous stamp; largest gap 0.77 sim-s, at frame 1538). The Rev 9 statements in the gaps list below (0 of 3745 decoded, glyphs drawn larger) did not reproduce: the expected string rendered with the recorder's own call spans x 13–252 px, the frame's mask x 14–252 px. The overlay code at `3959d7f` is the same call as today's. The cause of the earlier 0 is not known.
- **Frame-map check by eye.** 16 frames spread over the run, read from the burned-in clock by eye and compared with the map. Frame index (0-based) and eye reading: 0 7.57, 250 33.33, 520 54.50, 780 74.70, 1050 93.10, 1300 112.80, 1560 138.17, 1820 160.83, 1999 175.00, 2000 175.03 (segment boundary), 2300 195.33, 2600 214.30, 2900 234.03, 3200 254.03, 3500 279.57, 3744 300.30. Residual 0.00 s at every frame, and each frame's burned-in `f=` equals index + 1, so no frame was lost from the index.
- **Log-to-sim alignment.** The wall-to-sim map has 4 anchors (the four `starting analysis` lines against their decisions' `scene.stamp`; this M4 prints no `sim_t=`); max error 0.03 sim-s. At the decision call the panel clock reads 30.50 s and the camera pane's burned-in clock 30.50 s. Over the stills below, panel minus burned-in is 0.00–0.13 s, which is within one camera frame interval.
- **Captions as rendered** (under the scene pane; the first is highlighted):
  1. "VLM decision accepted and executed — recorded 2026-09-30 (earlier run, not part of the 2026-11-15 campaign)"
  2. "Model: gemini-robotics-er-2-preview — 2 of 2 robots arrived."
  3. "VLM: chose yield with robot_2 as yielder; the feasibility gate kept the choice (no swap) and it was executed."
  4. "System, not the VLM: back-out distance, escort of robot_1 past robot_2, Nav2 recovery after robot_2 stalled (sim ~97–120 s)."
  5. "Predates the current 0.20 m hard floor (on centre distance) and the safety-exemption fix; closest centre distance 0.264 m, body-to-body gap 0.19 m."
  6. "Illustrative demo, not controlled experimental evidence."
  The retreat pick (B, one of two equal-clearance options) is left out of the captions.
- **Hard-floor metric (verified in code).** `hard_contact_floor_m` is compared against the **centre-to-centre** distance of M1 poses, `math.hypot(a["x"] - b["x"], a["y"] - b["y"])`, at `ros2_ws/src/swarm_execution/swarm_execution/safety.py:981-982` (commit `8933863`). It applies only to pairs a clearing manoeuvre exempts or waives; any other pair already latches at `min_distance_m` 0.45. The default in `ros2_ws/src/swarm_execution/config/safety.yaml:26` is 0.0; 0.20 comes from `config/safety/safety_floor020.yaml:26`, which today's kits run (`hard_contact_floor_m=0.2` in the M4 startup line). So the sentence "the recorded minimum robot-to-robot gap was 0.19 m, below the current 0.20 m floor" compares a body gap (0.186 m) with a centre-distance floor. On the floor's own metric this run's minimum, 0.2643 m, is above 0.20 m. That minimum was at sim 25.5 s on the approach, where the pair was not exempt and the 0.45 m latch applied.
- **Stills viewed** (from the encoded video): the model call (sim 30.50 s, robots nose to nose, call line printed); the decision `jq` output (strategy yield, justification "Robot 2 should yield"); dispatch (yield to robot_2, `temporary_wait` to robot_1, exempt pair); robot_2 backing east (46.33 s); robot_1 escorted past robot_2, which is parked to the side (86.33 s); robot_1 at its goal with robot_2 still parked (93.17 s); robot_2 stalled at the east end of the barrier (110.10 s; terminal shows the "no congestion" answers); robot_2 moving west through the corridor (123.71 s); robot_2 at its goal (140.57 s). The pass and robot_1's arrival play at 8x sim time (video about 26–32 s).
- **Combined video.** Added as excerpt 4b (section 9).

The Rev 9 text follows, as written then.

#### Not Rendered (Rev 9)

- **Blocker.** Free disk was 5.06 GiB (`df -k`, checked three times) against the 5.5 GiB floor. No panel, combined v3 or `_v2` rename was made, and section 9 and the final summary's video table are unchanged.
- **Readiness (checked offline):**
  - The renderer's fixed filter matches this bundle's m5/m4 lines.
  - The `jq` request, model-call and decision lines return values. There is no `plan`, so no grounding line is printed, and the yielder and the B pick show only through the dispatch lines and captions.
  - Camera: `annotated_000.mp4` and `annotated_001.mp4` (`/perception/annotated_frame`, 3745 frames, 1280x960, burned-in `t=…s f=…` clock; e.g. frame 501 reads t = 53.10 s). `live_er2_demo_…mp4` is a 3745-frame H.264 copy of the same stream.
- **Two gaps to close before rendering:**
  1. The renderer loads only `m5_scene.jsonl`; this bundle has `scene_8e616116….jsonl`. It needs a documented, tested loader fallback, not a mirrored bundle.
  2. The campaign's clock decoder (`ho/kit/overlay_framemap.py`) decoded 0 of 3745 frames here. The September overlay is drawn larger: the glyphs span x 14–252 px against 12–203 px expected. A one-frame Hershey scale fit reached only IoU 0.32. Without a per-frame map, the recorder's first stamp (7.567 s) and frame count would assume a uniform rate, which best-effort capture does not give. So the 0.5 sim-s alignment is not yet shown.

---

## 12. Convoy Takes 4–5 with the Queued-Robot Hold (ER-2; Added 2026-11-15, Rev 11)

**Status.** These takes are illustrative, not controlled evidence, with n = 2. They are the demo campaign's convoy scenario (ledger `cv`, takes 4 and 5 of 5), not the registered convoy experiment, whose VLM arm remains unrun.

**Setup.**

- **Kit and registration.** Kit `demo_campaign/cvh/kit`, registration section 12. It equals the `cv` setup of section 5, plus the M3 queued-robot hold (`fix/convoy-hold-queued-robots`, v7o `d85d1ed`; delta `8fa937e6`; overlay fragment `grounding_hold_queued_crossers: true`).
- **Sources.** `cvh/runs/<label>/`, `cvh/driver_cv_*.log`, `cvh/MANIFEST_*.md5` and `cvh/vm/pxr_test/`.
- **Contacts.** v7m `scripts/recompute_gt_contacts.py` (output in the session scratchpad, outside the bundles).

### 12.1 Invocations (Verified From the Driver Logs and the Ledger)

| Invocation | VM up (booked) | Stockout | Attempts | VM after |
|---|---|---|---|---|
| Take 4 (10:26:15Z) | 1718 s | none (started on the 1st try) | `cvH_t04_a1` bring-up abort: `NAV2_BRINGUP_FAILED`, robot_3 stack, 3/4 active; retried by the chain as `cvH_t04_a2`, which ran (10:33:14–10:53:03Z) | TERMINATED (verified by the driver and by `gcloud … describe`) |
| Take 5 (10:56:55Z) | 1602 s | 12 failed start attempts, about 26 min (10:57:05–11:22:51Z, not booked; same VM, same zone) | `cvH_t05_a1` ran (11:27:26–11:47:04Z) | TERMINATED (verified both ways) |

- **Checks.** For the three attempts that ran or were retried, every deploy, arm check, probe and restore passed. For the two takes that ran, the condition gate (including `first_queued_hold` and the hold's startup line), `STARTUP_CHECK` and video verify passed (`GATE OK`, `RESTORE OK`); the aborted `cvH_t04_a1` has no recordings (video verify FLAGGED, as expected for a pre-gate abort).
- **Model calls.** 6 per take, all `completed`/`valid`, 0 refusals. Estimated spend $0.0453 and $0.0482; this retake booked $0.0960 in total against its $0.40 guard.
- **Stop.** Take 5 ran because take 4's failure was the model's yielder choice, not a harness fault (12.2). After take 5, `cv` has 5 of 5 valid takes, so the scenario is complete.

### 12.2 First Decision and What Grounding Added (Verified From `decisions/*.json` and the m5 Log)

| | Take 4 (`cvH_t04_a2`, request `08f4dca0`, scene 27.9 s) | Take 5 (`cvH_t05_a1`, request `a489dd3c`, scene 26.4 s) |
|---|---|---|
| Model answer | `yield`, yielder **robot_1**, `involved_robots` [robot_1, robot_2], no crossing order; plan: robot_1 `yield`, robot_2 `cross`, robot_3 `continue`, robot_4 `continue` | identical structure: yielder **robot_1**, the same pair, the same four legs |
| Grounding added | `grounding_queued_crossers_added` [robot_3, robot_4]; both `crossing_order=augmented:<id>:goal_across_corridor` tags; plan `repaired` with 2 `substitute` edits (`queued crosser hold: robot_3/robot_4: continue substituted to cross`) | the same |
| Dispatched | yield robot_1 (backup 0.986 m to park x −1.124, lateral 0.36, hold 135 s, crossing order [robot_2, robot_3, robot_4], `crossing_clear_m` [1.913, 1.435, 2.008]); linked `temporary_wait` 360 s for robot_2 → 0, robot_3 → 1, robot_4 → 2 | the same, backup 0.918 m, `crossing_clear_m` [1.98, 1.435, 2.008] |

- **Who decided what.** The model did **not** name robot_3 or robot_4 in either take; the hold added them. The model chose the strategy and the yielder.
- **Expected per the fix report.** The yielder was robot_1 both times. Offline, with this prompt, 6 of 18 stored answers pick robot_1 (fix report section 6). That is the variant the scene file calls the censored-alternative latch, and the fix report (section 5.1) predicted it: "robot_2's escort latches about 0.45 m from robot_3".

### 12.3 Execution (Verified From m4/m5 Lines and GT; Sim Times of m5-Only Lines Interpolated From M4's `sim_t` Anchors, Inferred)

The sequence was the same in both takes:

1. **Back-out.** robot_1 backed west and pulled off to (−1.13, +0.37), arriving between about 45 s and 50 s (GT). While it backed up, M4 held the exempt pairs robot_1+robot_2, +robot_3 and +robot_4. The yielder's closest approach to the queued robots was 0.767 m (take 4) and 0.762 m (take 5) to robot_3, and 1.337 m and 1.332 m to robot_4 (GT centre distance), so the new exemption was never close to binding.
2. **The key question: were robot_3 and robot_4 held? Yes.**
   - M5 logged `start delay elapsed, base mission released robots=['robot_3', 'robot_4']` at about sim 51.8 s (take 4) and 50.7 s (take 5). That is 12.2 and 5.8 wall-s before `gate_admit` (54.8 s and 52.2 s).
   - Both robots were already members of the yield command, with `temporary_wait` ACTIVE and `exempt=False` since the first dispatch (m4 `coordination status` lines, and `handoff guard: controller stop` for each). M4 logged no line about robot_3 or robot_4 within ±10 wall-s of the release; their wait had no terminal status until `gate_release` marked the command COMPLETED. So the evidence for the hold at the release moment is the still-ACTIVE wait plus GT, not a release-time M4 line.
   - GT: robot_3 did not move more than 2 cm in either take. robot_4 first moved at 189.6 s and 187.0 s, after `gate_release … reason=hold_timer` (189.8 s and 187.2 s).
   - In takes 1–3, by contrast, both robots drove through the gate right after their release (section 5.2).
3. **Gate.** `gate_admit` admitted robot_2 only, and robot_2 was escorted west 1.913 m (take 4) and 1.98 m (take 5). It stopped at x = −1.48 m, 0.418 m (at 72.5 s) and 0.419 m (at 78.2 s) from the held robot_3 at x = −1.90 m.
   - That pair, one per take, was under M4's 0.45 m `min_distance_m` and non-exempt (after `gate_admit` the exempt pairs were robot_1+robot_2 only), so the escort latched and later logged `FAILED escort timed out in phase drive`.
   - robot_3 and robot_4 were never admitted: the gate passed 1 of 3 robots in the crossing order.
4. **After `gate_release` (hold timer).** robot_1 drove east through the empty corridor and arrived (GT within 0.35 m at 211.1 s and 208.5 s; m5 `arrived at base goal` logged). robot_4 crept 0.17 m east and stopped 0.399 m / 0.394 m from robot_3. robot_2 (0.52 m from its goal at (−2.0, 0)), robot_3 and robot_4 stayed latched to the 260 s horizon.
5. **Later triggers (5 per take).**
   - Take 4: one `reverse` (plan `repaired`, yield re-grounded by the same-side check) and four `junction_clear` (no legacy template).
   - Take 5: three `yield` robot_2 with order [robot_3, robot_4, robot_2], each refused with `yield refused: both robots outside the corridor on the same side; a reverse would traverse it`, then one `reverse` and one `junction_clear`.
   - Every later trigger ran as 8 s waits for robot_2, robot_3 and robot_4. The hold added nothing to them (key absent, as designed: it acts only on a yield that grounds).

### 12.4 Outcome, Safety and Contacts (Verified)

| | Take 4 | Take 5 |
|---|---|---|
| Arrivals (GT) | 1/4: robot_1 at 211.1 s | 1/4: robot_1 at 208.5 s |
| **Label** | **Unresolved failure**: the model chose robot_1 as yielder; the grounder held the queued robots, but the escort of robot_2 west latched against held robot_3 (the scene's censored alternative) | **Unresolved failure**: same cause |
| Latch pairs < 0.45 m (GT centre) | robot_2–robot_3 0.418 m at 72.5 s (non-exempt); robot_3–robot_4 0.399 m at 190.7 s (non-exempt) | 0.419 m at 78.2 s; 0.394 m at 188.1 s |
| Closest pair centre distance (GT) | 0.276 m, robot_1–robot_2 standoff at 24.6 s, before any dispatch | 0.370 m, robot_1–robot_2 at 66.6 s (exempt, during the escort) |
| Floor stops (`hard_contact_floor`) | 0 | 0 |
| Recompute: min robot–robot body gap | 0.185 m, robot_1–robot_2 at 68.3 s (exempt pair, escort pass) | 0.191 m, robot_1–robot_2 at 65.9 s |
| Recompute: min robot–static gap | 0.057 m, robot_1 vs `aisle_barrier/south` at 200.5 s | 0.042 m, robot_1 vs `aisle_barrier/south` at 198.0 s |
| Contact events | none: static `clear`, robot-robot `clear` | none |
| Recording (ffprobe, frames read) | annotated 4 segments / 1091 frames; raw 7 / 1938 | annotated 5 / 1220; raw 7 / 1990 |
| Manifest | `6c9d0e22` (89 files incl. `cvH_t04_a1`; 86 `runs/` files re-hashed OK) | `bd017429` (61; 58 `runs/` files re-hashed OK) |

- **What these takes show.** The hold did what it was built to do: both queued robots were in the yield command, stayed in place through their own start-delay release, and were not released until the gate's hold timer. That removes takes 1–3's failure mode (uncommanded robots following the passer).
- **What they do not show.** The resolving sequence, which needs robot_2 as yielder, never ran, because the model picked robot_1 twice, the 1-in-3 variant offline. With n = 2 this is no rate, and nothing here says whether the robot_2 sequence would resolve live.
- **What is still open.** The robot_1 variant cannot resolve in this scene under the hold: the escorted robot_2 meets the held robot_3, which M4 protects with the full 0.45 m latch. That is a property of the scene and the yielder choice, not a kit fault.

### 12.5 Simulator-Only Test (Verified From `cvh/vm/pxr_test/`; Ran in Both Invocations)

- **What ran.** pytest 8.3.4 installed into `~/dmc_cvh/pytest_target` with Isaac's `python.sh` (Python 3.12.13), pip rc 0. The Isaac site-packages listing md5 was identical before and after (`b6805498…`). Then the one test ran on a scratch copy of the VM's pinned `isaac/vgu_sim` (md5s logged, equal to the pinned files) plus v7m's `contact_geometry.py` (`77e862ce`).
- **Result.** `1 skipped, 43 deselected`, rc 0: `SKIPPED [1] test_contact_geometry.py:444: could not import 'pxr': No module named 'pxr'`. The bare-import probe also failed: `import pxr` gives `ModuleNotFoundError` under plain `python.sh`.
- **Restore.** The restore removed the scratch (316 KiB) and target (2164 KiB) directories and verified they were gone, in both invocations (`cvh/vm/deploy/restore_20261115T105329Z.log` and `restore_20261115T114754Z.log`).
- **Log provenance.** Take 5's pull overwrote take 4's copies in `cvh/vm/pxr_test/`. Take 4's outcome is the identical `PXR_TEST (non-fatal): pip_rc=0 test_rc=0 1 skipped, 43 deselected …` deploy line in its driver log. The files on disk are take 5's (no manifest lists them): `pip_install.log` `90964963`, `pxr_step.log` `c80f0116`, `pxr_test.log` `6808b9cb`.
- **Owner's request not met.** The test was skipped both times, and `cv` has now used its 5 valid takes, so no planned VM start is left to retry it.
- **What it establishes.** Isaac's `python.sh` on this VM can install and run pytest from a separate `--target` directory without touching its own environment, and the VM has network access for pip.
- **What it does not establish.** Builder parity. The test was skipped, and a skip is not a pass. `pxr` is only importable inside a Kit/`SimulationApp` context here (as `build_dmc.sh`'s `isaac.scripts.build_scenario` uses it), not from a bare interpreter. A rerun would need the test to run under `SimulationApp`, or with the USD libraries' paths added; that is not done.

### 12.6 Video

Nothing has been rendered (another agent owns the renderer).

- **Candidate.** `cvH_t05_a1`: one attempt, the longer annotated stream (5 segments, 1220 frames; raw 7 segments, 1990 frames, both ffprobe-read), and its later triggers show the explicit same-side refusals.
- **Caption.** Label "Unresolved failure". The caption must say that robot_3's and robot_4's roles came from M3 (the queued-robot hold), not from the model, and that the model chose robot_1 as yielder.

### 12.7 Verified and Inferred

| Claim | Status |
|---|---|
| Invocation times, stockout, abort, gate/restore results, VM TERMINATED, ledger rows | verified (driver logs, `gcloud describe`, ledger) |
| First decisions, added robots, tags, edits, dispatched commands | verified (artifacts, m5 dispatch lines, m4 `command received`) |
| robot_3 and robot_4 held through their release; robot_4 moved only after `gate_release` | verified (m4/m5 lines, GT) |
| Sim time of M5's release line (≈ 51.8 s / 50.7 s) | inferred (linear interpolation between M4's `gate_admit` and `gate_release` `sim_t` anchors) |
| robot_2's escort latched on held robot_3 under the non-exempt 0.45 m rule | verified (GT pair distance, M4 exempt-pair lines, escort FAILED line) |
| Contact figures | verified (offline recompute, footprint model `urdf_footprint_v1`) |
| The robot_2 variant would resolve live under the hold | not shown (did not occur; smoke n = 1 only) |
| `pxr` importable only under Kit | inferred from the probe and the build path; not tested |

---

## 13. Presentation Cut of the Demo Videos (Added 2026-11-15, Rev 12)

**Status.** An audience version of the same five takes, for judges and lecturers. Offline post-processing only: no VM and no API call; the bundles were read, never written. **The engineering cuts (sections 5.6, 6.5, 7.3, 8.5, 9 and 11.5) remain the record.** Re-hashed after this work, unchanged: `ibD_t05_a1_panel.mp4` `fdf07a82…`, `cvD_t01_a1_panel.mp4` `82431944…`, `hoD_t01_a1_panel.mp4` `2aa6534a…`, `m5D_t01_a1_panel.mp4` `33e9f5ee…`, `ER2LIVE_20260930_panel.mp4` `93cbfe71…`, `demo_campaign_combined.mp4` `de8cb6ed…`. Every take stays an illustrative demo, not controlled experimental evidence.

**Renderer.** v7g `feat/demo-panel-renderer`, `render --profile presentation` (commits `bb37be0`, `7cae7b8`, `e8c609f`, `0e799d6`, `a4bbbce`, `575b396`, `74dfe63`, `da5c416`). The default profile is unchanged: its transcripts for the five bundles regenerate equal to the stored ones, apart from the `time_map.method` wording that `0212306` changed earlier. Unit tests `test_demo_panel.py` and `test_demo_combine.py`: 108 passed (53 before); ruff clean. Method: v7g `docs/guides/demo_panel_video.md`, section "Presentation Profile". Every caption, card line and zoom crop: v7g `config/demo_presentation/<label>.json`.

### 13.1 Files (v7g `data/demo/campaign/presentation/`, git-ignored)

ffprobe (verified): all H.264, yuv420p, 24 fps. No `_small` copy was needed (all under 28 MB). Each video has its transcript, eight stills (intro, trigger, response, check, dispatch, mid, outcome, outro) and a `.md5` file beside it.

| File | md5 | Size | Frames, duration |
|---|---|---|---|
| `ibD_t05_a1_presentation.mp4` | `8c09f71fa34b727b82d6757692df76d7` | 9.9 MB | 3152, 131.33 s |
| `cvD_t01_a1_presentation.mp4` | `f96210bc7958884a49b8f17ca7bc287e` | 27.6 MB | 9095, 378.96 s |
| `hoD_t01_a1_presentation.mp4` | `32176fba6aeb7411a0036da51baf34f1` | 5.6 MB | 2706, 112.75 s |
| `m5D_t01_a1_presentation.mp4` | `a51992a27877f2d801cb56f522ab34a6` | 20.2 MB | 7007, 291.96 s |
| `ER2LIVE_20260930_presentation.mp4` | `cfabf6cda7424d511e3cf3dc9f762722` | 6.0 MB | 2677, 111.54 s |
| `presentation_combined.mp4` (1920x1124) | `ce8f4101b16e544372b2798cf2ce3c20` | 23.5 MB | 9373, 390.54 s |

Each video is a 13 s intro card, the full take uncut (same camera segments and frame maps as the engineering cuts) and a 10 s outro card.

### 13.2 What Differs From the Engineering Cut

- **Terminal, log lines.** The filter adds M5's `yield re-grounded|yield refused|refusal withheld` lines and ends in a displayed `sed -E` stage. The stage cuts the `[proc] [LEVEL] [epoch] [name_node]:` prefix to `name:` and keeps 8 of 32 hex characters per id. Safety-stop repeats are collapsed as before and drawn dim, not yellow. Decision and plan lines are bold yellow, check lines bold orange, and `action=` lines bold green.
- **Terminal, decision block.** The block now prints:
  - the model's plan (`plan: robot_3 reverse, robot_4 reverse, robot_1 yield, robot_2 cross`) and `crossing_order`. Without a plan channel it prints `yield_robot`. A nulled plan prints `plan: null`;
  - the check verdict (`provenance=… reason=… dispatch_order_source=…`, or `{yield_robot_grounded_from[, dispatch_order_source]}`);
  - the image input: `file -b frames/<id>.png`, the frame M5 dumped as the one the model sees, plus `image_tokens` where recorded.

  It drops the prompt hash and length, `backend_id`, `total_tokens` and `degradations`. `dispatch_order=` (`dispatched_robot_ids`) is removed: it held the first phase's recipients and was filled for withheld decisions too. The `cost.log` poll lines are kept, dim.
- **Timing.** The sim clock holds 7 s on the model's answer and 4 s on the check. The engineering cut held one 4 s pause per block.
- **Outside the terminal.**
  - A stage strip (Trigger, VLM request, VLM response, Check, Dispatch, Execution) driven by the log anchors in the guide.
  - Plain-language header and captions, revealed at their anchor lines. The outcome line appears only at the last arrival (or the end for unresolved takes). A few captions name the step about to happen (for example "robot_3 will be escorted past it") or keep the report's wording that runs ahead (the five-robot escort line).
  - A legend for verbatim terms.
  - A zoom inset beside the camera: a 4:3 crop of the same frame, ×2.7 to ×4.0, labelled. Nothing is drawn on the camera image.
  - Intro and outro cards: what was the model's and what was the system's.
  - The kept wording: the disclosure, the outcome labels and takes, the intersection sentences (allowed actions, the back-out order, a default order computed offline in captions only, take 5 of 5), the five-robot escort-into-island line, and every ER2LIVE caveat (earlier run; model's yielder kept by the gate; escort and Nav2 recovery are the system's; predates the 0.20 m floor on centre distance and the safety-exemption fix; 0.264 m / 0.19 m). The retreat pick is not shown.

### 13.3 Transcript Check Against the Engineering Cut (Verified)

Log items were compared by source (`m5.log:N` / `m4.log:N`) with the stored engineering transcripts:

| Take | Engineering log lines | Presentation | Added (all gate lines) | Removed | Order | Collapse markers |
|---|---|---|---|---|---|---|
| ib take 5 | 75 | 75 | 0 | 0 | same | 3 = 3, identical |
| cv take 1 | 88 | 96 | 8 `yield refused` | 0 | same | 20 = 20 |
| ho take 1 | 27 | 28 | 1 `yield re-grounded` | 0 | same | 2 = 2 |
| m5 take 1 | 47 | 59 | 6 `yield refused` + 6 `refusal withheld` | 0 | same | 56 = 56 |
| ER2LIVE | 23 | 23 | 0 | 0 | same | 1 = 1 |

- Every shown line equals the `sed` stage applied to its source line (0 mismatches). The displayed commands, run for real on a fixture, give the displayed lines (unit tests).
- The default back-out order appears in no intersection terminal line.
- At all 58 clock holds, the decision, plan and check lines are on screen.
- The terminal has 26 body rows at 20 px (about 99 columns).

### 13.4 Combined Presentation Video

Manifest `presentation_combined_manifest.json` (md5 `da190783a2b2343362a55de927d9cf9f`), sidecar `presentation_combined_sources.json`, `--crf 26`. New combine mode `outcome_reveal: "after"`: title cards and the caption bar carry no outcome label. Three outcome cards follow the last excerpt of cv, ER2LIVE and m5. The ib and ho excerpts end 3 s after their own outcome line. Clip order follows v3, with excerpts:

1. ib 35.8–116.4 s;
2. cv 17.9–55.0 s;
3. cv 339.8–368.9 s, then an outcome card;
4. ho 46.0–97.6 s;
5. ER2LIVE 17.8–52.5 s;
6. ER2LIVE 92.3–97.3 s, then an outcome card;
7. m5 19.6–99.0 s (decisions 1 and 2, with the escort into the island; v3's excerpts 5 and 5b are contiguous here);
8. m5 241.8–281.9 s, then an outcome card.

Each take's excerpts contain the call, the answer, the check, the dispatch (for m5's last excerpt, the withheld refusal) and the outcome. Total 6 min 31 s, about 30 s over the 6 min target: each shown decision now holds about 11 s.

### 13.5 Known Limits

- The five-robot bundle has an empty `frames/` directory. Its image input is shown only by `image_tokens` 1064.
- The camera pane is blank after the last recorded frame (cv after sim 259.97 s, m5 after 600.23 s), as in the engineering cut.
- The five-robot escort caption (kept wording) says the escort later timed out, about 55 sim-s before that happens.
- The robot ids in the zoom are the perception overlay's own small red labels. They are legible at ×2.7–×4 but low in contrast.
- The combined video's ER2LIVE outcome card carries the selection reason and every ER2LIVE caveat in about 75 words on a 3 s card. That is too short to read aloud; pause there when presenting.
- The five-robot intro says "a limitation demonstration" (kept wording), which hints at the ending.
- "Call, response, check, dispatch and outcome" holds per take across its excerpts, not per excerpt.

---

## 14. Convoy Rerun with the Queued-Robot Hold and Yielder Correction (ER-2; Added 2026-11-15, Rev 13)

**Status.** One demonstration take of the Four-robot convoy counterflow scene (`convoy_counterflow_slip`, seed 42), run on the owner's request "also inspect why robots in convoy demo did not come to destination, if ok rerun the demo". It is illustrative, n = 1, not controlled evidence, and not the registered convoy experiment (v7f `feat/convoy-live-resolution`, whose VLM arm remains unrun).

**Setup.**

- **Kit and registration.** Kit `demo_campaign/cvy/kit` (ledger key `cvy`), registration section 13 and its share amendment 13.6 (`wall_sec_cvy` 5 400 → 7 200 s, committed `8e316fd` before the VM start). Delta `fd85e2f9c8617ff306c36367bc68fee4` (v7t `fix/convoy-yielder-feasibility`), with the queued-robot hold (`grounding_hold_queued_crossers`) and the counterflow yielder correction (`grounding_yield_counterflow_swap`) both on. Everything else equals the convoy takes 4–5 (section 12): live ER-2, legacy grounding, the 0.20 m floor, the safety-exemption scope fix, the 260 sim-s horizon.
- **Why the rerun.** v7t `docs/reports/2026-11-15-convoy-non-arrival-and-yielder-feasibility.md`: takes 1–3 failed because the queued robots were released uncommanded, and takes 4–5 because the model chose the platoon-side yielder robot_1.
- **Sources.** `cvy/runs/cvY_t01_a2/` (decision artifacts, m4/m5 logs, GT), `cvy/driver_cvy_20261115T142504Z.log`, `cvy/vm/chain_dmc.log`. Contacts: v7m `scripts/recompute_gt_contacts.py`, output in the session scratchpad, outside the bundle. Sim times of log lines without their own `sim_t` are interpolated from M4's `gate_admit`/`gate_release` anchors (inferred, marked ≈).

### 14.1 Invocation (Verified From the Driver Log, `gcloud` and the Ledger)

| Item | Value |
|---|---|
| Driver | 14:25:04Z – 14:53:44Z; kit md5 `194a09b7` (VM) / `ebcedf81` (all); `ADMIT cap_sec=7200` |
| Stockout | 1 failed start (14:25:15Z), about 2 min; VM started 14:27:26Z (same VM, same zone) |
| Attempts | `cvY_t01_a1`: bring-up abort `NAV2_BRINGUP_FAILED` (robot_3 stack, 2/4 active), no recordings, not a valid take; retried by the chain. `cvY_t01_a2`: ran 14:34:27Z – 14:51:16Z, the valid take |
| Checks | deploy, arm check, probes (3, all HTTP 200), condition gate (`GATE OK`, every check PASS incl. the two-key startup line, `first_queued_hold` and `first_counterflow` branch `model_chose`), `STARTUP_CHECK OK`, `RESTORE_DMC OK` (PINS_V3 OK, installed packages = snapshot) |
| Simulator-only test step | ran again, `1 skipped, 43 deselected` (`pxr` not importable from bare `python.sh`), non-fatal, as section 12.5 |
| VM after | TERMINATED 14:53:22Z (verified by the driver and by a separate `gcloud … describe`) |
| Booked | 1556 s wall; $0.0147 ($0.0132 take estimate + probes) |

### 14.2 First Decision and What the Grounder Did (Verified From `decisions/cfaabdc5….json` and m5)

- **Trigger.** `starting analysis request=cfaabdc5…` with robot_2 stalled ≥ 12 s; scene stamp 28.57 s. robot_1 stood at x −0.03 (at the gate) and robot_2 at x +0.36.
- **The model's raw answer (ER-2).** `strategy` `yield`, `yield_robot` **robot_2**, `involved_robots` [robot_1, robot_2], `crossing_order` null; plan legs robot_2 `yield`, robot_1 `cross`, robot_3 `continue`, robot_4 `continue`. The model did **not** name robot_3 or robot_4.
- **Queued-robot hold (the grounder).** `grounding_queued_crossers_added` [robot_3, robot_4], with both `crossing_order=augmented:<id>:goal_across_corridor` tags; plan `repaired` with 2 `substitute` edits (`queued crosser hold: robot_3/robot_4: continue substituted to cross`); `dispatch_matches_plan=true`.
- **Counterflow yielder correction (the grounder).** Armed (startup line `… grounding_hold_queued_crossers=True grounding_yield_counterflow_swap=True`), but it **did not fire**: the model's yielder robot_2 was already the feasible one. `yield_robot_grounded_from` null, `yield_regrounded_reason` null, no `yield re-grounded` m5 line, no counterflow tag.
- **Dispatched (m5 `dispatch` ×4, m4 `command received` ×4, sim ≈ 31.4 s).** yield robot_2: backup 0.758 m to park x 1.124, lateral pull-off 0.36, `hold_sec` 137.9, crossing order [robot_1, robot_3, robot_4], `crossing_clear_m` [1.807, 3.683, 4.256]. Linked `temporary_wait` 367.7 s: robot_1 → 0, robot_3 → 1, robot_4 → 2. This is the resolving sequence of the fix report (section 5.2).

### 14.3 Execution (Verified From m4/m5 Lines and GT)

1. **Back-out.** robot_2 backed east from x 0.36 to 1.137 by about 40 s and pulled off to (1.137, −0.377), parked by 47.5 s (GT). Exempt pairs during the back-out: robot_1+robot_2, robot_2+robot_3, robot_2+robot_4.
2. **Held robots.** M5 logged `start delay elapsed, base mission released robots=['robot_3', 'robot_4']` at ≈ 51.7 s. Both were already in the yield command with `temporary_wait` ACTIVE (`exempt=False`). GT: robot_3 first moved at 73.0 s and robot_4 at 114.2 s, each at its own `gate_admit`, so both stayed held until admitted.
3. **Gate, in order.**
   - robot_1 admitted at sim 52.97 s (escort 1.807 m; COMPLETED, moved 1.814 m, at 73.07 s); arrived (GT) at 75.3 s.
   - robot_3 admitted at 73.07 s (escort 3.683 m; COMPLETED 3.684 m at 114.23 s); arrived at 116.4 s.
   - robot_4 admitted at 114.23 s (escort 4.256 m; COMPLETED 4.257 m at 161.8 s); arrived at 158.1 s.
   - M4's `exempt pairs changed` sequence (every line, not de-duplicated): at dispatch robot_1+robot_2, robot_2+robot_3, robot_2+robot_4 (back-out); after robot_1's admit robot_1+robot_2; after robot_3's admit robot_1+robot_2, robot_2+robot_3; after robot_4's admit robot_1+robot_2, robot_2+robot_3, robot_2+robot_4; after `gate_release … reason=clearance` at 161.80 s `-`. The passer–passer pairs were never exempt. Corroboration: no `min_distance_violation` line after wall 1794753423.163, 0.26 s after the dispatch.
4. **Yielder's return.** robot_2 left the park point at 161.8 s and drove west through the empty corridor; arrived (GT) at 180.1 s. Its first `compute_path_to_pose` right after release aborted once (`Failed to create plan with tolerance of: 0.5`); the next path was passed to the controller and it continued (the only Nav2 abort in the take).
5. **Later trigger.** One: request `9ea3e3c2` at scene 166.6 s (robot_2 stalled, distance 2.46 m, during its return). The model answered `congestion_detected=false`, strategy `none`; `no dispatch stage=vlm`. Nothing was dispatched before the last arrival (classifier: `later_dispatched_before_resolution=0`).
6. **Real-time factor.** About 0.30 (108.8 sim-s over 367.6 wall-s between the first `gate_admit` and `gate_release`; derived from M4's anchors).

### 14.4 Outcome, Safety and Contacts (Verified)

| Item | Value |
|---|---|
| Arrivals (GT, within 0.35 m and never beyond 0.5 m after) | **4/4**: robot_1 75.3 s, robot_3 116.4 s, robot_4 158.1 s, robot_2 180.1 s; m5 `arrived at base goal` for all four |
| **Label** | **Resolved — grounder held the queued robots; model chose strategy and yielder** (kit classifier `mac_extra_classify_cvy.py` and own check agree) |
| Pairs under 0.45 m (GT centre distance) | robot_1–robot_2 25.1–31.0 s, min 0.393 m: the standoff that triggered the analysis. The 2 672 `min_distance_violation` lines split into 732 at start-up (wall …363.8–374.6, before the robots moved; 366 of them for a `robot_35` ghost id that also appears in earlier takes' m4 logs) and 1 940 for robot_1/robot_2 during the standoff (…402.6–423.163); the last 22 of these fall within 0.26 s after the m5 dispatch, before the back-out exemption registered at …423.173. None after that; after dispatch only exempt pairs: robot_1–robot_2 62.8–68.2 s (min 0.374 m, escort past the parked yielder), robot_2–robot_3 103.9–109.2 s (0.378 m), robot_2–robot_4 151.5–156.7 s (0.379 m) |
| Non-exempt pairs (never exempt in this command) | robot_1–robot_3 min **0.497 m** at 116.0 s, on the goal side (robot_3 arriving beside robot_1 at its goal), 0.047 m above the 0.45 m latch; robot_1–robot_4 0.665 m at 161.4 s; robot_3–robot_4 0.656 m at 161.4 s (after 100 s). No non-exempt pair latched. After `gate_release` (no exemptions) the closest pair was robot_1–robot_3 at 0.618 m |
| Closest centre distance overall (GT) | 0.374 m, robot_1–robot_2 at 65.5 s (exempt) |
| Floor stops (`hard_contact_floor_m` 0.2) | 0 |
| Recompute: min robot–robot body gap | 0.195 m, robot_1–robot_2 at 65.9 s (exempt pair, escort pass); verdict `clear` |
| Recompute: min robot–static gap | **0.0185 m**, robot_2 vs `aisle_barrier/south` at 165.5 s (during its return through the gate); threshold 0.005 m, verdict `clear`. Row-level check (`--rows`): a smooth trough, 0.0197 → 0.0186 → 0.0185 → 0.0185 → 0.0189 m over 165.3–165.7 s at 0.13–0.17 m/s; the robot moves about 15 mm per 10 Hz row, but the gap changes by at most 1 mm per row near the minimum, so the sampled minimum is not hiding a deeper dip. Others: robot_1 0.169 m, robot_3 0.178 m, robot_4 0.177 m |
| Contact events | none (robot-robot `clear`, static `clear`) |
| Recording (ffprobe, frames read) | annotated 5 segments / 1334 frames; raw 7 segments / 1824 frames; video verify OK |
| Manifest | `cvy/MANIFEST_20261115T142504Z.md5` `073e8d029b51e135ea9bd194bf82c9cb` (82 files, both attempts); the 79 `runs/` files re-hashed equal |

- **Goal-side margin.** The fix report flagged robot_1–robot_3 near the goals as the thin margin (smoke 0.495 m; earlier replicates 0.463 / 0.475 m). This take gave 0.497 m: it held, but by 0.047 m.
- **robot_2's return.** Its 0.0185 m clearance to the south barrier is the closest static approach of the take and was produced by Nav2 local control, not by a coordination command.

### 14.5 What Was the Model's and What Was the System's

- **The model (ER-2):** the yield strategy, robot_2 as yielder, robot_1 as passer, and the plan legs for robot_1 and robot_2. Its second answer ("no congestion" during robot_2's return) dispatched nothing.
- **The grounder (M3):** robot_3 and robot_4 in the crossing order and their linked waits (queued-robot hold), the plan edits, the park point, backup and escort distances. The counterflow yielder correction was armed but changed nothing. **It was not exercised live:** with this answer the queued-robot hold alone gives the same command, so this take is no live test of the correction (its effect is shown offline only, fix report section 5).
- **The execution and safety monitor (M4) and Nav2:** the gate admissions, escorts, release on clearance, and robot_2's drive home.
- So this is a **system-corrected resolution**: the model chose the strategy and the feasible yielder; the grounder held the queued robots. It is not labelled VLM-driven. With n = 1 it is illustrative only, not evidence that the VLM resolves convoy congestion; the model chose robot_1 in 3 of the 5 earlier live first decisions, and those five takes stay Unresolved failure as reported in sections 5 and 12.

### 14.6 Video

Not rendered here (another agent owns the renderer).

- **Candidate.** `cvY_t01_a2` (the only valid take): annotated 5 segments / 1334 frames, raw 7 / 1824, frame maps written by video verify.
- **Caption facts.** Label "Resolved — grounder held the queued robots; model chose strategy and yielder". The model named only robot_1 and robot_2 and chose robot_2 to yield; the grounder added robot_3 and robot_4 to the crossing order and held them (queued-robot hold); the yielder correction was armed and did not fire; crossing order robot_1 → robot_3 → robot_4, then robot_2 returned; arrivals 75.3 / 116.4 / 158.1 / 180.1 sim-s; closest non-exempt pair 0.497 m; robot_2 passed 0.0185 m from the south barrier on its return (no contact by recompute); one later analysis answered "no congestion" and dispatched nothing. Demonstration take 1 of 1 of the rerun, after five unresolved convoy takes.

### 14.7 Stop and Ledger

- **No second take.** Take 1 resolved, which meets the goal; registration 13.5 stops there.
- **Ledger** (`ledger_dmc.py status`): campaign 27 223 s of 43 200 s, $2.8784 of $10; `cvy` 1556 s of 7200 s, $0.0147, valid 1, bring-up aborts 1/3, `next_take=2`.

### 14.8 Verified and Inferred

| Claim | Status |
|---|---|
| Invocation times, stockout, abort, checks, VM TERMINATED, ledger rows | verified (driver log, chain log, `gcloud describe`, ledger) |
| Model answer, hold additions, no swap, dispatched command | verified (decision artifact, m5 dispatch lines, m4 `command received`, condition gate re-run on the Mac) |
| robot_3 and robot_4 held until their own `gate_admit` | verified (GT first-move times vs m4 `sim_t`) |
| Arrivals, pair distances, exempt status | verified (GT; m4 `exempt pairs changed` lines) |
| Contact figures | verified (offline recompute, `urdf_footprint_v1`) |
| Sim times of the dispatch (≈ 31.4 s) and M5's release line (≈ 51.7 s); RTF ≈ 0.30 | inferred (interpolation from M4 anchors) |
| `robot_35` is a start-up perception ghost id, not a robot | inferred (only before sim motion; also in `cvH_t05_a1`'s m4 log) |
| The VLM resolves convoy congestion | not shown (n = 1; the model's yielder choice varied across takes) |
