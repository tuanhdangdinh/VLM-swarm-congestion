# Demo Campaign Results

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: intersection live takes 1–3 (ER-2, B3), why live ER-2 gave no usable plan, and the Sonnet 5.5 arm built for takes 4–5.

---

## Summary

- **Status.** Every take here is an illustrative demo, not controlled experimental evidence. Takes are never pooled with experiment data.
- **Intersection, ER-2 under B3, 3 takes (2026-11-14/15 UTC).** Take 1 unresolved (3 of 4 arrived), takes 2 and 3 resolved. None is VLM-driven: the labels are Unresolved, M3-default, M3-default. No GT contact, no floor stop.
- **Why ER-2 gave no usable plan live (section 2).** The live prompt is byte-identical to the offline B3 prompt for the same snapshot, and nothing was truncated. The three takes failed for three different reasons:
  - take 3: the known options-detail copy (`"reverse (south arm)"`);
  - take 2: the known missing releasing `yield`;
  - take 1: a trigger on an approach snapshot caused by a one-frame M1 identity glitch, plus a malformed leg key never seen offline.
  Had take 3's two actions been parsed as `reverse`, it would have been the demo event.
- **Take 1 unresolved (section 2.4).** The M3 default plan ran on that pre-jam geometry. The release gate for robot_1 needed robot_3 to travel 2.65 m, but robot_3's goal was only about 2.54 m away. Its fallback hold of 240 s outlasted the 300 s horizon. This is not related to the model's output.
- **Sonnet 5.5 arm built and dry-tested (section 3).** It is a separate kit, `demo_campaign/ib_sonnet/kit`. The probe works from the Mac.
- **Offline Sonnet B3 check (n = 16, $0.216 at list).** 16/16 answered and valid, and 11 were `vlm_verbatim`. But only 1 of 15 first triggers would be classified VLM-driven, because of the yielder gap: chance over 2 takes is about 13 %.
- **Recommendation: no-go for Sonnet takes as a route to a "VLM-driven" video; owner decision.** Launching also needs an owner-approved take-budget deviation (section 3.5).

---

## 1. Intersection Live Takes 1–3 (ER-2, B3)

Illustrative, not controlled evidence. Kit `demo_campaign/ib/kit`, effective overlay `614beed0` (B3), delta `5c7973d3`, live `gemini-robotics-er-2-preview`. Sources: `ib/runs/<label>/`, `ib/driver_ib_*.log`, `ib/take*_stdout.log`, `take_class_dmc.py`.

| Take (label) | Resolved | Label (`TAKE_CLASS`) | Provenance | Dispatched recede order | Default (chi) order | GT min pair | Safety | Recording frames (annotated / raw) | Manifest md5 |
|---|---|---|---|---|---|---|---|---|---|
| 1 (`ibD_t01_a2`; a1 = bring-up abort, `change_state` timeout on robot_1) | no, 3/4 (robot_1 not arrived) | Unresolved failure | `m3_default` (plan absent) | robot_3, robot_4 | robot_3, robot_4 | 0.370 m | floor stops 0, GT contacts 0; `min_distance_violation` lines 2182, `stale_pose_unsafe` 2 | 1481 / 2271 | `a4e4eaef` (81 files, both attempts) |
| 2 (`ibD_t02_a1`) | yes, 4/4 | M3-default resolution | `repaired` | robot_4, robot_3 | robot_4, robot_3 | 0.288 m | floor stops 0, GT contacts 0; `min_distance_violation` lines 13787 | 1605 / 2213 | `5dddd2fb` (55 files) |
| 3 (`ibD_t03_a1`) | yes, 4/4 | M3-default resolution | `m3_default` (plan absent) | robot_4, robot_3 | robot_4, robot_3 | 0.314 m | floor stops 0, GT contacts 0; `min_distance_violation` lines 10321 | 1423 / 1975 | `a92ebe37` (51 files) |

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

`demo_campaign/ib_sonnet/spec/` was assembled by the unchanged `common/assemble_dmc.sh ib_sonnet` into `ib_sonnet/kit/` (`kit_md5_dmc.txt` `858e0803`, `kit_md5_all_dmc.txt` `777a3f1b`). The spec files override the common files of the same name. Nothing under `common/`, `ib/`, `runtime_delta/` or the ledger was modified; `ib/kit` still passes `KIT_MD5 OK`.

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
- **Not possible without a runtime change, so not done.** M5 logs no startup line naming the backend or model. The backend and model are asserted from fc_launch's lines, M5's first-call line, the deployed-loader resolution and every artifact.

### 3.2 Dry Test (Verified by Running)

`cd ib_sonnet/kit && MIN_MAC_FREE_KB=3000000 bash test_dry_dmc.sh` ends with `TEST_DRY_DMC ib OK`. The name is the ledger key `ib`. All cases OK:

- **1:** syntax and kit md5; `test_key_dmc.sh` (install, replace and remove byte-exact; refusals; mode kept; container count; no temp files; key never printed); no VM path calls the Gemini probe.
- **2–6:** the `ib` cases. The take table reads `live Sonnet 5.5 claude-sonnet-5-5`; labels are `ibD_sonnet55_tNN_aK`.
- **7:** the real ER-2 take-3 bundle FAILS exactly `a_backend_anthropic, a_served_model, a_rce_model, launcher_line, launcher_line_2, m5_line_3, m5_line_absent`, and 27 checks pass.
- **9:** fc_launch DRY_RUN switches to `anthropic`.
- **10:** driver paths:
  - key install after the dead-man and before the probe;
  - verified removal in the trap, also after a probe abort;
  - `KEY_NOT_REMOVED` written and blocking the next invocation;
  - missing, two-line and 644 key sources refused before any start;
  - the dummy key never printed;
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
- Spend: $0.216 at list ($0.2705 ledger units). Not booked in the campaign ledger yet, because the convoy run was writing it (section 3.6).

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

### 3.6 Ledger Booking Owed (Not Done: the Convoy Driver Was Writing the Ledger)

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
