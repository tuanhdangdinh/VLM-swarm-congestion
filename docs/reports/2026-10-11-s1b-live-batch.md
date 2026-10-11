# A22 Live Batch: Echo Rotation and Five Live ER-2 Episodes on S1b

**Prepared:** 2026-10-11

**Revision history:**

- Rev 1 (2026-10-11, PARTIAL): A22 echo-rotation fix (build, tests, merge, deploy); live batch episodes E7 and E8, E9 not run (3 Nav2 bring-up aborts); E10/E11 ran unattended on the VM but their bundles were NOT retrieved, because SSH to the VM was lost mid-batch (the Mac's public IP changed and the VM firewall admits only the old IP). All aggregates are PROVISIONAL over E6-E8.
- Rev 2 (2026-10-11, FINAL): SSH restored; E10 and E11 retrieved. E10 ran but is censored at 123.5 sim-s (Gemini prepaid credits depleted, HTTP 402 on 38/40 analyses); E11 not run (3 bring-up aborts). Final aggregates over the four live episodes (E6, E7, E8, E10), the both-clusters count, and the VM end state are in §9-§13. Rev 1 numbers that changed are marked superseded in place.
- Rev 3 (2026-10-11): aggregate update after the A23 resume ran E9 and E11 live (`docs/reports/2026-10-11-bringup-and-resume.md`). §14 has the aggregates over six live episodes (E6, E7, E8, E10, E9, E11). Rev 2 numbers that changed are marked superseded in place.
- Rev 4 (2026-10-12): aggregate update after the A24(iii) predicate fix and live batch 2 (E12-E17, `docs/reports/2026-10-11-live-batch2.md`). §15 has the aggregates over twelve live episodes with the fixed predicate. Rev 3 numbers that changed are marked superseded in place.
- Rev 5 (2026-10-12): aggregate update after the A26 stack (A25 swept-axis backup, retreat shield, B3 fast-fail) and live batch 3 (E18-E20; E21 not run on the budget floor; `docs/reports/2026-10-12-shield-and-batch3.md`). §16 has the aggregates over fifteen live episodes. Rev 4 numbers that changed are superseded by §16.

---

## Summary (Rev 5)

**The A26 stack shipped and batch 3 ran E18-E20 live** (E21 not run: $0.0363 left, below the $0.04 start floor). Every batch-3 yield that was dispatched was admitted: **5/5, against 3/9** for E6-E17. Details: `docs/reports/2026-10-12-shield-and-batch3.md`. Every Rev 4 aggregate is superseded by §16.

| Question | Rev 5 answer (live E6-E20, fixed predicate) |
|---|---|
| (a) Attribution | Opportunity episodes are now E13, E16, E17, E18 and E20: all `intermittent`, 0 alternations, APPARATUS (the A25(iii) ESCALATION class). **Pooled: NO LIVELOCK UNDER THE REAL MODEL (5 opportunity, 0 ARCH)** |
| (b) Productive resolutions | All classified n = 27, **7 nonzero** (+E18, +E20), p95 = 1; live 6/15. Bar (≥ 8) **NOT met, by one**; **n_more = 3** live episodes |
| (c) First-conflict yields | **Live 3/15** (E15, E18, E20), CI 0.043-0.481, against MC 10/15 |
| (d) Wandering vs park | 1 finisher ever; 0/41. Undecided |
| (e) Cost | Median $0.0335; batch 3 $0.1637; all-live total $0.6477 |

## Summary (Rev 4)

**The A24(iii) predicate fix shipped and batch 2 ran E12-E17 live.** All six had a first-attempt sequential bring-up; E17 is censored by its cost cap at about 298 sim-s. Details: `docs/reports/2026-10-11-live-batch2.md`. Every Rev 3 aggregate is superseded by §15.

| Question | Rev 4 answer (live E6-E17, fixed predicate) |
|---|---|
| Predicate fix | One classification changed in 18 bundles. E11 `c417cbff` becomes productive, so E11 goes `intermittent` → `resolved` and its verdict ARCH → INDETERMINATE |
| (a) Attribution | First opportunity episodes: E13, E16 and E17, all `intermittent` with 0 alternations, so APPARATUS under the A24 conjunction. **Pooled: NO LIVELOCK UNDER THE REAL MODEL (3 opportunity, 0 ARCH).** Under the pre-A24 rule it would read LIVELOCK, 3 of 3 |
| (b) Productive resolutions | All classified n = 24, 5 nonzero, p95 = 1. Live 4/12 nonzero. Bar (≥ 8 nonzero) NOT met; **9 more live episodes needed** at the pooled live rate |
| (c) First-conflict yields | **Live 1/12 (E15, the first)**, CI 0.002-0.385, against MC 7/12. 6 of 9 dispatched live yields FAILED in execution without admit |
| (d) Wandering vs park | 1 finisher ever; 0/33. Undecided |
| (e) Cost | Median $0.0301; batch 2 $0.2568 (cap overshoot $0.0068, one call); all-live total $0.4840 |
| Both clusters named | 14/67 valid analyses (14/43 two-cluster scenes), 6/12 episodes; batch 2 alone 12/36. Clearing legs in both clusters dispatched 3/67; verbatim ∧ matched still 1 (E7) |
| Bring-up | Sequential pooled 0/14 |

---

## Summary (Rev 3)

> Rev 4: superseded by the Rev 4 summary above and §15. In particular, E11 is no longer ARCHITECTURE-CHURN under the A24(iii) predicate fix.


**The A23 resume ran E9 and E11 live**, with sequential Nav2 bring-up; both brought up on the first attempt and completed cleanly. Details are in `docs/reports/2026-10-11-bringup-and-resume.md`. **There are now six live episodes.** The Rev 2 summary below stands for the four-episode state; every aggregate it quotes is superseded by §14.

| Question | Rev 3 answer (live E6, E7, E8, E10, E9, E11) |
|---|---|
| E9 / E11 | E9: 7 valid analyses, yields refused `no executable retreat` (= MC), `clogged`, $0.0495. E11: 9 valid analyses, 2 unproductive latch-breaking dispatches → `intermittent`, $0.0707 |
| (a) Attribution | **E11 = ARCHITECTURE-CHURN by the registered rule** (`intermittent`, 0 alternations). 0/6 opportunity episodes. The pooled verdict is MET by the letter: **LIVELOCK UNDER A REAL MODEL**. Only the "k of the opportunity episodes" annotation does not fit (1 ARCH, 0 opportunity). It is an edge case and needs an owner ruling before citing (A23 report §7) |
| (b) Productive resolutions | Live 2, 0, 0, 1*, 0, 0. All classified n = 18, p95 = 2. budget_k still unfreezable |
| (c) First-conflict yields | **Live 0/6** (CI 0-0.46) against an MC upper bound of 3/6 |
| (d) Wandering vs park | 1 finisher ever; 0/24 occupied-node arrivals with a finisher occupant. Undecided |
| (e) Cost | Median $0.0310 (mean of the middle two); range $0.0174-0.0707; all-live total $0.2272 |
| Both clusters named | 2/31 valid analyses (2/20 two-cluster scenes); dispatched 1/31; episodes 1/6 (E7) |
| Bring-up | Stagger-6 parallel pooled 9/20 (incl. 4 same-day controls). Sequential 0/8 |

---

## Summary (Rev 2, FINAL)

> Rev 3: superseded for every aggregate by §14 and the Rev 3 summary above. The episode statuses for E6-E10 stand. E9 and E11 later ran in the A23 resume (§14).

**Status: batch closed.** Four live ER-2 episodes ran in total: E6 from the A21 wave, plus E7, E8 and E10 from this batch. E9 and E11 never ran: each had three Nav2 bring-up aborts. **There are four live episodes, not six.** Every "E6-E11" aggregate below is computed over E6, E7, E8 and E10.

**Headline 1: Gemini prepaid credits ran out mid-E10.** From analysis 3 (123.5 sim-s, 20:13:35Z) every call returned HTTP 402 `RESOURCE_EXHAUSTED` ("prepayment credits are depleted"), so 38 of E10's 40 analyses failed with no decision. A failed analysis is not suppressed, so M5 re-triggered about every 3 sim-s. Those failures used up the MAX_ANALYSES = 40 hard stop at 232.2 sim-s. The stop was set off by the dead backend, not by model churn. E10 is therefore **censored at 123.5 sim-s**. No further live ER-2 work is possible until the owner tops up AI Studio billing. If E11 had brought up, it would have hit the same 402.

**Headline 2: the E7 overturn stands, and it happened only once.** Over the 15 valid live analyses, a model named both clusters 2 times (2 of the 8 analyses whose scene had two latch clusters), and a scene-wide plan was dispatched once (E7 analysis 1). Both cases are in E7, so 1 of 4 live episodes. E10's two-cluster scene (analysis 2) named only {r2, r4}.

| Question | Final answer (live E6, E7, E8, E10) |
|---|---|
| Episodes | E7 ran (4 analyses, $0.0284). E8 ran (4, $0.0277). E9 NOT RUN (3/3 aborts). **E10 ran, censored at 123.5 sim-s** (2 valid analyses + 38 HTTP 402; $0.0174). **E11 NOT RUN** (3/3 aborts) |
| (a) Attribution | **INDETERMINATE: 0 of 4 live episodes had ≥ 3 clearing dispatches into one cluster** (max 2, 1, 1, 1). Alternations 0 everywhere. E10's value is a censored lower bound |
| (b) Productive resolutions | Live: E6 2, E7 0, E8 0, E10 1 (censored). All 16 classified S1/S1b episodes: nearest-rank p95 = 2 (n = 16). Per productive event, dispatches into its cluster: [1, 2, 1], p95 = 2 |
| (c) First-conflict yields | **Live 0/4** (95% CI 0-0.60) against a per-seed MC upper bound of **2/4** (E6, E10). E10's first analysis DISPATCHED the MC-predicted yield (r1) but it was never admitted (`gate_admit` absent; r1 FAILED after about 212 s). Echo pilots 0/5 against 4/5 MC |
| (d) Wandering vs park | Unchanged: one S1b finisher to date (E4 r2). 0 occupied-node arrivals with a finisher as occupant (21 arrivals over S1b E1-E8 + E10), 0 parked-finisher occupancy events, tail gridlock in every episode |
| (e) Cost | $0.0335 / $0.0284 / $0.0277 / $0.0174 (E10 truncated by the 402; a floor). Median $0.0281 (the script's upper-median: $0.0284). **Batch total $0.0735** (E7 + E8 + E10, lower bound), $0.1070 with E6 |
| Both clusters named | 2/15 valid live analyses (2/8 two-cluster scenes); dispatched scene-wide 1/15 (1/8); episodes 1/4 (E7) |
| Bring-up | This batch 6 aborts in 9 launches. Stagger-6 era **9 in 16 (0.56)**. The batch abort rule did not fire (consecutive counter 1) |
| VM | Idle, pins verified, ownership fixed, NOTES updated (§13) |

PILOT-ONLY, RECORD = 0.

---

## Summary (Rev 1)

> Superseded by the Rev 2 summary above wherever the numbers differ: episode statuses, every aggregate, cost and bring-up counts. Rev 1 text is kept unchanged below.

**Status: PARTIAL.** The rotation fix shipped. Of the five live episodes, two ran and were analysed (E7, E8). E9 was not run: three Nav2 bring-up aborts. E10 started at 20:03Z, brought up cleanly and was running when SSH was lost at about 20:15Z. The chain continues unattended on the VM (E10, then E11) with every pre-registered stop rule enforced on the VM side. Its bundles have not been retrieved, so every aggregate below covers E6-E8 only and is provisional.

**Headline: a live model named BOTH clusters and its scene-wide plan was dispatched (E7), which revises A22's "S6-in-S1 = NO".** E7's first analysis saw two head-on pairs ({r1, r3} and {r2, r4}), named all four robots, proposed a four-robot `reverse` plan, and the plan went out verbatim (vb ∧ dispatch_matched). 3 of 4 reverses COMPLETED and both latches broke, but nothing progressed: both pairs re-latched (r2 into r5) and the episode gridlocked at 63.7 rel-s with 0 tasks. A later E7 `junction_clear` also named both clusters and was withheld (`no feasible yielder`, 0.00 m legacy reading).

| Question | Answer (provisional, E6-E8) |
|---|---|
| Rotation fix | Merged (`e3a5456`), deployed (md5-verified), suite zero delta (62/6435/153/3 → 62/6459/153/3). On E5's scenes the second cluster is now analysed and grounds an executable yield |
| Episodes | E7 ran (4 analyses, $0.0284), E8 ran (4 analyses, $0.0277), E9 NOT RUN (3/3 bring-up aborts), E10/E11 unattended, not retrieved |
| (a) Attribution | **INDETERMINATE: 0 of 3 live episodes had ≥ 3 clearing dispatches into one cluster** (max 2, 1, 1). Alternations 0 everywhere. No livelock seen, and no opportunity for one either |
| (b) Productive resolutions | Live: E6 2, E7 0, E8 0. All 15 classified S1/S1b episodes: nearest-rank p95 = 2 (n = 15). Too few nonzero values to freeze the A21 bound |
| (c) First-conflict yields | **Live 0/3** (95% CI 0-0.71) against a per-seed MC upper bound of 1/3. Echo pilots 0/5 against 4/5 MC. Every VM S1b episode so far: 0/8 |
| (d) Wandering vs park | Still a single S1b finisher to date (E4's robot_2). 0 occupied-node arrivals with a finisher as occupant, 0 parked-finisher occupancy events, tail gridlock in every episode |
| (e) Cost | $0.0335 / $0.0284 / $0.0277 per live episode (median $0.0284). Batch retrieved spend $0.0561, plus E10's ≈ $0.017 at the last read and whatever E10/E11 spend after it, under the VM-enforced $0.40 batch gate |

PILOT-ONLY, RECORD = 0.

---

## 1. Build: the Echo Rotation (A22, Apparatus Only)

| Item | Where | What shipped |
|---|---|---|
| Selection | `reasoning/vlm/mock_backend.py` `echo_engaged_pairs`, `echo_selection`, `echo_select` | Engaged pairs (two stalled robots < 0.45 m) in a fixed order: closest first, ties by the presentation index of the first member, then the second. The echo names the first pair not refused in the current epoch (`rotated_pair`). Once every engaged pair has been refused it falls back to the pre-A20 all-stalled rule (`all_refused_fallback`) |
| Memory | `EchoMockBackend.note_dispatch_outcome(refused, dispatched)` | REFUSED = M5 withheld the dispatch (`dispatch_withheld` set). The EPOCH ends only at a dispatched command. Pairs are stored as robot-id sets, never presentation indices |
| Wiring | `InProcessPipeline.note_dispatch_outcome`, `_build_default_pipeline`, `OrchestratorNode` next to `_update_suppression` | The observer is `getattr(backend, "note_dispatch_outcome", None)`: only the echo has it. Gemini, OpenAI, Anthropic, llama-server and the scripted `MockBackend` have no hook (pinned by a test), so every scored arm is untouched |
| Trace | decision `justification` | A rotated or fallback echo decision says so (`A22 rotation: rotated_pair, 1 engaged pair(s) refused this epoch skipped.`). No artifact schema change |

**Why M5 has to tell the echo.** The prompt carries no refusal signal. E5's second prompt has `failure_context` and `last_failed_context` null and a plan block reading "Nothing has changed since this plan was accepted." Inferring a refusal from "my last pair is still latched" would also rotate after a dispatched yield that re-latched, which rebuilds E3's cross-cluster alternation.

**Why the epoch is not the suppression reference.** All three E5 re-analyses arrived through a `robot_set_changed` reset of the reference. An epoch tied to the reference would never rotate on E5.

**Default behaviour is unchanged.** With an empty memory `echo_select` equals `d7dae79`'s on 200 000 random scenes, so the MC replay (S1b 0.635, S1a 0.42) is unchanged by construction.

**E5 replay (`tests/unit/data/echo_rotation_a22/e5_scenes.json`, the three live E5 scenes):**

| Analysis | Live (A21 echo) | A22 echo | Grounding on this tree |
|---|---|---|---|
| f4057cac | [r1, r5] refused | [r1, r5] (closest, 0.36 m) | refused, `no executable retreat` (reproduces live exactly) |
| 65b4bfcd | [r1, r5] refused | **[r3, r4]** (rotated) | **EXECUTABLE yield robot_3, lane x** |
| c37ae913 | [r1, r5] refused | (epoch ended by the dispatch: [r1, r5]) | — |

The second cluster now gets analysed, and at its first analysis it grounds an executable yield. An all-refused counterfactual on the third scene rotates [r1, r5] → [r3, r4] → [r1, r2] → all-stalled.

**Suite.** Zero delta against a fresh `d7dae79` worktree, with no stash: 62 / 6435 / 153 / 3 → 62 / 6459 / 153 / 3, with identical failing ids (the 24 new tests pass). Commit `b368500` (feat/v3-echo-rotation), merged as `e3a5456`.

**Live relevance: none.** The batch below is Gemini, which has no hook. The rotation matters for echo arms only.

---

## 2. VM Deploy, Scenarios and Pre-registration

| Step | Result |
|---|---|
| Scenarios | `mapd_5_s1b_seed{7..11}` regenerated from the UNCHANGED VM `mapd_5_s1b.yaml` (`728e58df`) with the p3 generator, built alone as root (`build_s7.sh`): build rc 0, every USD newer than its yaml (`5c93ce7c` / `ec01845a` / `b27f6b7b` / `e8d7ee0e` / `d24bfa00`), usd_check islands and spawns equal the draws, validate seed 7 rc 0 |
| Overlays | Built from the `d7dae79` `mapd_5_s1b.yaml` header (`3d2659b6`, the A20 boxes; the NOTES line-107 trap) with `build_overlay.py`. The procedure byte-reproduces `s1b_orch_seed6.yaml`. Parsed on the DEPLOYED tree inside `vgu_ros`: seed, `junction_declared` + [NW, SW, N, S], plan channel on, suppression on, `refusal_no_action` on, `churn_bound` off (values None), `s1b_dynamic.yaml`, H 600 |
| Deploy p4 | `e3a5456` delta = `mock_backend.py`, `reasoning_pipeline.py`, `orchestrator_node.py`. Pre-image md5 OK (= `d7dae79`), source / live-mount / installed md5 OK, PACKAGES SRC==INSTALLED OK, pins untouched. In `vgu_ros`, `GeminiBackend` has no `note_dispatch_outcome`: the live path is untouched |
| Pre-registration | Rule 11 appended to `~/v3_s1b/NOTES.md` before any batch data (condition = E6's; hard stops; bring-up rule; capture schema; per-seed MC predictions; the five aggregate definitions, including the pooled attribution rule and the nearest-rank p95). Copy: `data/logs/vm_runs/live_batch/notes_prereg_p4.md` |
| Chain | `chain_p4.sh`, run as ubuntu. Before every attempt: an idle gate, pins (orchestrator `1f656533` src + installed, rag `e18c723c`, `s1b_dynamic` `535f5281`) and the USD present. Before every episode: batch est. spend + $0.10 ≤ $0.40. Per episode: `cost_watch` (cap $0.10, MAX_ANALYSES 40), `pin_watch` (300 sim-s pin rule) and `live_watch` sidecars. Every attempt is logged to `p4/attempts.tsv` |
| Procedure correction | The chain was first launched with sudo. It was aborted at +29 s, before M5 started ($0, no analysis, not counted as an attempt), pins were re-verified pristine, and it was relaunched as ubuntu. Logged in NOTES |

**Per-seed MC predictions (A22 tree, echo, empty refusal memory).**

| Seed | First encounter (MC) | Echo names | MC outcome |
|---|---|---|---|
| 6 | r1+r3 7.8 s | [r1, r3] | executable (r1) |
| 7 | r2+r4 10.3 s, r1+r3 10.9 s | [r1, r3] | refused (ambiguous lane) |
| 8 | r2+r4 12.5 s | [r2, r4] | refused (no executable retreat) |
| 9 | r4+r5 16.8 s | [r4, r5] | refused (no executable retreat) |
| 10 | r1+r5 10.3 s | [r1, r5] | executable (r1) |
| 11 | r4+r5 28.2 s, r2+r3 30.6 s | [r2, r3] | executable (r2) |

---

## 3. Bring-up Log (Stagger 6)

| Attempt | STAMP | Outcome |
|---|---|---|
| E7 a1 | 20261010_180127 | ran |
| E8 a1 | 20261010_185746 | ran |
| E9 a1 | 20261010_195408 | ABORT: robot_3 `controller_server` bond timeout (4.00 s) |
| E9 a2 | 20261010_195649 | ABORT: robot_4 `bt_navigator` get_state `async_send_request failed` |
| E9 a3 | 20261010_195930 | ABORT: robot_3 `controller_server` bond timeout. **E9 not run** (consecutive-x3 counter = 1) |
| E10 a1 | 20261010_200211 | brought up; 2 analyses and $0.0174 by 20:12Z; then out of reach |

> Rev 2: superseded. E10 a1 ran (§9). E11 a1-a3 aborted (§10). Final counts: this batch 6 / 9, stagger-6 era 9 / 16 (0.56).

There were 3 aborts in 6 batch launches. Over the stagger-6 era: pilot 2 1/3, A21 wave 2/4, this batch 3/6, so **6 aborts in 13 launches (0.46)**. Every abort is one of the two known classes (bond timeout, get_state), always on one robot, with 4/5 stacks active. A host check during E10's bring-up showed no lingering process (only Kit at 185 % CPU, load average 15-22 on 8 vCPU). The abort rule (2 consecutive episodes x3) had not fired at the last read.

---

## 4. E7 (Seed 7): Both Clusters Named, Scene-wide Plan Dispatched, No Progress

**Run.** `s1b_E7_seed7_er2_a1`, STAMP 20261010_180127. GATE OK, RESTORE OK, 0 tracebacks. `backend_id` gemini on 4/4, all valid, 1 attempt each. No hard stop fired.

| # | sim-s | Model decision | Scene clusters | Plan (provenance) | M3 / M5 outcome |
|---|---|---|---|---|---|
| 1 | 37.4 | reverse r1/r2/r3/r4 ("two separate head-on deadlocks") | {r1,r3}, {r2,r4} | 1/2/3/4 reverse (**vb, matched**), **active legs in BOTH clusters** | dispatched; r1, r2, r3 COMPLETED, r4 FAILED; 2 latch breaks, unproductive |
| 2 | 81.2 | yield r1 → r3 | {r1,r3}, {r2,r5} | 1 yield 3 cross (m3_default, matched) | refused `ambiguous lane` (r1 40°, r3 36°) → withheld |
| 3 | 85.7 | yield r1 → r3 (same) | same | same | same refusal → withheld |
| 4 | 90.2 | junction_clear r1-r5 | {r1,r3}, {r2,r4,r5} | 1,2 yield; 3,4,5 cross (m3_default, matched), **both clusters** | `no feasible yielder (0.00 m x4, r5 0.15 m)` → withheld; suppressed to H (184) |

- **Outcome.** Gridlock at 63.7 rel-s (outcome `gridlock`), 0/25 tasks, final clusters {r2, r4, r5} + {r1, r3}. 3 occupied-node arrivals (no finisher occupant), 0 finishers.
- **Churn.** `clogged`: 1 clearing dispatch, 1 resolution event (unproductive), alternation 0, resolution-time share 0.003.
- **Provenance.** vb 1 / m3_default 3; vb ∧ matched 1/4.
- **MC.** The first encounter held (MC r2+r4 10.3 s / r1+r3 10.9 s; live r2+r4 11.1, r1+r3 11.9 rel-s). MC predicted a refusal; the live first analysis was a dispatched four-robot reverse, not a yield.
- **Pin watch.** One 13.5 sim-s PIN episode (robot_4 against `fence_W`, 66.5-80.0) self-freed. No stop.
- **Echo counterfactual (stateless).** Same cluster as the model 4/4. Executable 1/4 (analysis 1: yield r2 in {r2, r4}); ambiguous-lane refusals 3/4.

---

## 5. E8 (Seed 8): One Five-robot Cluster at S

**Run.** `s1b_E8_seed8_er2_a1`, STAMP 20261010_185746. GATE OK, RESTORE OK, 0 tracebacks. Gemini 4/4, valid, 1 attempt each. No hard stop.

| # | sim-s | Model decision | Scene clusters | Plan (provenance) | Outcome |
|---|---|---|---|---|---|
| 1 | 38.1 | yield r2 → r4 | {r2,r4} | 2 yield 4 cross (m3_default, matched) | refused `no executable retreat` (no candidate survives the sweep, either robot) → withheld |
| 2 | 41.9 | reverse r2+r4 | {r2,r4} | 2/4 reverse (**vb, matched**) | dispatched; r2 COMPLETED, r4 FAILED; latch broke once, unproductive |
| 3 | 79.4 | junction_clear r2-r5 | {r2,r3,r4,r5} | 5,4 yield; 2 wait; 3 cross (m3_default, matched) | `no feasible yielder` (0.15 / 0.00 m) → withheld |
| 4 | 89.4 | junction_clear r1-r5 | {r1..r5} | 1,3 cross; 4,2 wait; 5 reverse → **repaired** (2 edits), **mismatched** | `no feasible yielder` (0.00 m x5) → withheld; suppressed to H (185) |

- **Outcome.** `partial`: 3/25 tasks (r1 N then Wm, r3 S; last progress 76.7 sim-s), gridlock 64.2 rel-s, final cluster ALL FIVE at S.
- **Wandering vs park.** 3 occupied-node arrivals at S (no finisher occupant), 0 finishers.
- **Churn.** `clogged` (1 unproductive event, alternation 0).
- **Provenance.** vb 1 / repaired 1 / m3_default 2. vb ∧ matched 1/4. The one mismatch is again a withheld junction_clear (A18 residual (2)).
- **MC.** The first-conflict prediction held exactly: r2+r4 refused, `no executable retreat`.
- **Echo counterfactual (stateless).** Same cluster 4/4, executable 0/4. Analysis 1 has only one stalled robot in the scene, so `no_pair`.

---

## 6. E9-E11

> Rev 2: superseded for E10 and E11. See §9 (E10) and §10 (E11).

- **E9.** Not run (section 3).
- **E10 and E11.** Running or queued unattended on the VM (section 8). Not analysed.

---

## 7. Aggregates (PROVISIONAL, E6-E8 Live; Definitions per Rule 11)

> Rev 2: every number in this section is superseded by §11 (final, over E6, E7, E8, E10). The verdicts of (a), (c) and (d) do not change; (b) gains E10's 1, and (e) gains E10's $0.0174.

### 7.1 (a) Attribution

| Episode | Clearing dispatches (max into one cluster) | Alternations (max in one cluster) | churn_class | Verdict |
|---|---|---|---|---|
| E6 | 3 (2) | 0 | resolved | INDETERMINATE |
| E7 | 1 (1) | 0 | clogged | INDETERMINATE |
| E8 | 1 (1) | 0 | clogged | INDETERMINATE |

**Pooled: INDETERMINATE (0/3 opportunity episodes).** The model never churned, but it never got the chance to either. Each episode ends in refusals of yields and junction_clears followed by permanent suppression after 1-3 clearing dispatches. The mechanism that prevents livelock under the live model is the same one that prevents resolution: refusal + `refusal_no_action` + scene-unchanged suppression.

### 7.2 (b) Productive-resolution Counts

| Set | n | Values | p95 (nearest rank) |
|---|---|---|---|
| All classified S1/S1b episodes (A21 table + E6-E8) | 15 | 13 × 0, A1 1, E6 2 | 2 |
| Live only | 3 | 2, 0, 0 | 2 |
| Per productive event: clearing dispatches into its cluster up to and including it (live) | 2 | 1, 2 | 2 |

These are not enough to freeze `budget_k`.

### 7.3 (c) First-conflict Yield

| Set | Live yield | MC (upper bound) |
|---|---|---|
| Live ER-2 (E6-E8) | 0/3 (CI 0-0.71) | 1/3 |
| Echo pilots (S1b E1-E5) | 0/5 | 4/5 |

The live first analyses were reverse (E6, E7) and a refused yield (E8).

### 7.4 (d) Wandering vs Park

Across S1b E1-E8 there is 1 finisher in total (E4 robot_2, parked at N, no occupancy conflict). Occupied-node arrivals total 19, and 0 had a finisher as occupant. **Wandering-vs-park remains undecided: there are almost no finishers to observe.**

### 7.5 (e) Cost

Per live episode: $0.0335, $0.0284, $0.0277. Every call is about 3.1-3.3k prompt tokens (1064 image) plus 0.3-0.4k completion plus 0.3-0.5k thought, at about $0.007/call. No stage-2 call occurred in E7 or E8.

> Rev 2: E10's first analysis made one stage-2 call (retreat choice), so E10 has 3 billed calls for 2 analyses (§9).

---

## 8. VM State at Loss of Access, and the Resume Checklist

> Rev 2: superseded. The checklist was executed on 2026-10-11 after SSH was restored. The chain had already ended normally at 20:33:14Z. See §13.

**State at loss of access (about 20:15Z).**

- RUNNING; chain_p4 in E10 attempt 1 (2 analyses, $0.0174).
- E11 follows unless a stop rule fires.
- Expected chain end about 21:55-22:30Z, after which the VM is idle.
- Pins were verified before every attempt.

**Cause of the loss.** The Mac's public IP changed to 42.112.79.64. `vgu-vgu-thu-base-isaac-workstation-fwrules-ssh` admits only 118.69.30.138/32. Widening the rule was not done (it was refused as a security change); the owner decides.

**Resume checklist (after reconnecting):**

1. Confirm `CHAIN_P4 DONE` in `~/v3_s1b/p4/chain_p4.log`, and read `p4/attempts.tsv`.
2. Tar-pull `runs/s1b_E10_*`, `runs/s1b_E11_*` and `p4/` into `data/logs/vm_runs/live_batch/`.
3. Run `aggregate.py` over E6-E11 (`data/logs/vm_runs/live_batch/aggregate.py`, from the repo root with `PYTHONPATH=.:ros2_ws/src/swarm_orchestrator:ros2_ws/src/swarm_execution`).
4. Append the per-episode results and the end state to NOTES.
5. Run `sudo chown -R ubuntu:ubuntu ~/v3_s1b data/logs/m5_decisions data/logs/m5_scene`.
6. Verify the pins (orchestrator `1f656533` src + installed, rag `e18c723c`, `s1b_dynamic` `535f5281`), no Isaac/Kit/chain process, and no leftover GT dir.
7. Revise this report to Rev 2.

---

## 9. E10 (Seed 10): MC-predicted Yield Dispatched but Not Admitted; Credits Depleted at 123.5 sim-s (Rev 2)

**Run.** `s1b_E10_seed10_er2_a1`, STAMP 20261010_200211. GATE OK, RESTORE OK. `backend_id` gemini 40/40. Only analyses 1-2 are valid. Analyses 3-40 failed on a single attempt each with HTTP 402 `RESOURCE_EXHAUSTED` ("Your prepayment credits are depleted"): no decision, no dispatch, unbilled. **Hard stop fired: MAX_ANALYSES = 40** (sidecar at 20:23:34Z, then the Isaac stop flag), set off by the 402 loop. The $0.10 cost stop and the pin rule did not fire.

| # | sim-s | Model decision | Scene clusters | Plan (provenance) | M3 / M5 outcome |
|---|---|---|---|---|---|
| 1 | 38.0 | yield r5 → r1 | {r1,r5} | 5 yield, 1 cross → **swap** to 1 yield, 5 cross (repaired, 1 edit; matched) | dispatched yield r1 (retreat B, stage-2 call) + r5 `temporary_wait`. **No `gate_admit`**: r1 FAILED after about 212 s, r5 COMPLETED. r5 later progressed (106.4, 111.4 sim-s) → productive |
| 2 | 84.3 | reverse r2+r4 | {r1,r3}, {r2,r4} | 4/2 reverse (**vb, MISmatched**: only r2 reverse dispatched, `node_handoff:robot_2->robot_4`) | dispatched; r2 FAILED after about 195 s; 2 latch breaks, unproductive |
| 3-40 | 123.5-232.2 | none (HTTP 402) | {r1,r3}, {r2,r4} then {r1,r3}, {r2,r4,r5} | none | `decision=None`, no dispatch. Requests `3a70abe2` … `c746b92c`, re-triggered about every 3 sim-s with no suppression |

- **Outcome.** `partial`: 1/25 tasks, last progress 111.4 sim-s. Gridlock onset 100.4 rel-s, which is about 124.7 sim-s (t0 = 24.27 M1 sim-s). That is 1.2 s after the first 402 analysis, so whether the model would have broken the gridlock is unobservable. Final clusters {r2, r4, r5} + {r1, r3}. 2 occupied-node arrivals (r1 at N with occupant r5, r2 at S with occupant r4), no finisher, tail gridlock.
- **Churn.** `resolved` (censored): 2 clearing dispatches (1 per cluster), 1 productive and 1 unproductive event, 3/3 latch breaks attributed, alternation 0, resolution-time share 0.31.
- **Provenance.** repaired 1, vb 1. vb ∧ matched 0/2. The vb mismatch is a single-robot reverse grounding of a two-robot reverse plan.
- **MC.** The first encounter held (MC r1+r5 10.3 s; live r1+r5 11.7 rel-s). MC predicted an executable echo yield of r1. The model named r5 as yielder. The grounder's swap gate re-grounded it to r1, the MC choice, and dispatched it, but the yield never reached `gate_admit`. During the yield window M4 logged about 7 000 `min_distance_violation` safety stops on r1, and r1 and r3 latched from 28.3 rel-s to the end. Under rule 11 (c) this counts as **not** a first-conflict yield: dispatched, not admitted.
- **Echo counterfactual (stateless).** Both valid analyses were on the same cluster as the model and executable (yield in [r1, r5]; yield in [r2, r4]). The 38 402-scenes also ground executable echo yields ([r4, r5] 37, [r1, r3] 1), but no live decision exists to compare them with, so they are not counted.
- **Cost.** $0.0174 over 3 billed calls (analysis 1 reasoner + stage 2: $0.0104; analysis 2: $0.0070). This is a floor truncated by the dead backend, not a typical episode cost.
- **Apparatus observation (not fixed here).** A backend failure (`decision=None`) does not arm the scene-unchanged suppression, so a dead backend re-analyses about every 3 sim-s until MAX_ANALYSES.

---

## 10. E11 (Seed 11): Not Run, Three Bring-up Aborts (Rev 2)

| Attempt | STAMP | Outcome |
|---|---|---|
| E11 a1 | 20261010_202512 | ABORT: robot_3 **`planner_server`** bond timeout (4.00 s) |
| E11 a2 | 20261010_202755 | ABORT: robot_4 `bt_navigator` get_state `async_send_request failed` |
| E11 a3 | 20261010_203031 | ABORT: robot_4 `bt_navigator` get_state `async_send_request failed`. **E11 not run** |

The counter of consecutive episodes with three aborts stood at 1, because E10 ran between E9 and E11. The batch abort rule (2 consecutive) therefore did not fire. The chain ended normally (`CHAIN_P4 DONE` 20:33:14Z) because E11 was the last episode.

**Bring-up totals.** This batch had 6 aborts in 9 launches. Over the stagger-6 era (pilot 2 1/3, A21 wave 2/4, this batch 6/9) the total is **9 in 16 (0.56)**. The bond-timeout class now includes `planner_server` as well as `controller_server`. Every abort hit one robot (r3 or r4) with 4/5 stacks active.

E11 was an MC-positive seed (echo [r2, r3] → executable yield r2). If it had brought up, it would have run against the depleted credits (§9).

---

## 11. Final Aggregates (Rule 11 Definitions; Live E6, E7, E8, E10) (Rev 2)

> Rev 3: superseded by §14, which recomputes every block with E9 and E11 added.

Computed with `aggregate.py` over `churn_wave/s1b_E6_seed6_er2_a3` and the batch bundles E7, E8 and E10. Output: `data/logs/vm_runs/live_batch/agg_final.json`. E9 and E11 have no live data. **E10's 38 failed analyses are excluded from every per-analysis denominator**, and its episode-level values are censored at 123.5 sim-s.

### 11.1 (a) Attribution

| Episode | Clearing dispatches (max into one cluster) | Alternations (max in one cluster) | churn_class | Verdict |
|---|---|---|---|---|
| E6 | 3 (2) | 0 | resolved | INDETERMINATE |
| E7 | 1 (1) | 0 | clogged | INDETERMINATE |
| E8 | 1 (1) | 0 | clogged | INDETERMINATE |
| E10 | 2 (1) | 0 | resolved (censored) | INDETERMINATE (censored lower bound) |

**Pooled: INDETERMINATE (0/4 opportunity episodes).** No live episode gave the model three clearing dispatches into one cluster. E10 might have, but its backend died after two analyses, so its "no opportunity" result is a censoring artefact rather than the natural outcome.

### 11.2 (b) Productive-resolution Counts

| Set | n | Values | p95 (nearest rank) |
|---|---|---|---|
| All classified S1/S1b episodes (A21 table + E6, E7, E8, E10) | 16 | 13 × 0, A1 1, E10 1, E6 2 | 2 |
| Live only | 4 | 2, 0, 0, 1 (censored) | 2 |
| Per productive event: clearing dispatches into its cluster up to and including it (live) | 3 | 1, 2, 1 | 2 |

This is still too thin to freeze `budget_k`.

### 11.3 (c) First-conflict Yield

| Set | Live yield | MC (upper bound) |
|---|---|---|
| Live ER-2 (E6, E7, E8, E10) | **0/4** (Clopper-Pearson 95% CI 0-0.60) | 2/4 (E6, E10) |
| Echo pilots (S1b E1-E5) | 0/5 | 4/5 |

The live first analyses were reverse (E6, E7), a refused yield (E8), and a dispatched but never-admitted yield (E10). E10 is the first live episode whose first analysis dispatched a yield at all. Across all VM S1b episodes so far the count is 0/9.

### 11.4 (d) Wandering vs Park

| Episode | Finishers | Occupied-node arrivals | With finisher occupant | Parked-finisher occupancy | Tail gridlock |
|---|---|---|---|---|---|
| S1b E1 (echo) | 0 | 1 | 0 | 0 | yes |
| S1b E2 (echo) | 0 | 4 | 0 | 0 | yes |
| S1b E3 (echo) | 0 | 2 | 0 | 0 | yes |
| S1b E4 (echo) | 1 (r2, 171.3 sim-s) | 1 | 0 | 0 | yes |
| S1b E5 (echo) | 0 | 2 | 0 | 0 | yes |
| E6 (live) | 0 | 3 | 0 | 0 | yes |
| E7 (live) | 0 | 3 | 0 | 0 | yes |
| E8 (live) | 0 | 3 | 0 | 0 | yes |
| E10 (live, censored) | 0 | 2 | 0 | 0 | yes |

The total is 1 finisher and 21 occupied-node arrivals, 0 of them with a finisher as occupant. **Wandering-vs-park stays undecided because there are almost no finishers to observe.**

### 11.5 (e) Cost

| Episode | Valid analyses | Billed calls | Est. USD (published ER-2 rate, lower bound) |
|---|---|---|---|
| E6 | 5 | 5 | 0.0335 |
| E7 | 4 | 4 | 0.0284 |
| E8 | 4 | 4 | 0.0277 |
| E10 | 2 (+38 × 402) | 3 | 0.0174 (truncated floor) |

The median is $0.0281 (the mean of the middle two values). `aggregate.py` reports the upper median, $0.0284. The range is $0.0174-0.0335. **The batch total is $0.0735** (E7 + E8 + E10), under the $0.40 gate, and $0.1070 including E6. These are estimates against an account balance that is now exhausted, so the owner should check actual billing in AI Studio. A stage-2 call happened once in the batch (E10 analysis 1).

---

## 12. Both Clusters Named: How Often the E7 Overturn Occurs (Rev 2)

> Rev 3: superseded by §14. With E9 (6 two-cluster scenes) and E11 (6) the totals are 2/31 valid analyses and 2/20 two-cluster scenes; the scene-wide dispatch count is still 1 (E7).

| Episode | Valid analyses | Two-cluster scenes | Named both clusters | Scene-wide plan dispatched |
|---|---|---|---|---|
| E6 | 5 | 3 | 0 | 0 |
| E7 | 4 | 4 | **2** (`c7aeaac1` reverse r1-r4; `ca36d298` junction_clear r1-r5) | **1** (`c7aeaac1`, vb ∧ matched) |
| E8 | 4 | 0 (one cluster of up to five) | 0 | 0 |
| E10 | 2 | 1 (`d5541ff0`, named {r2, r4} only) | 0 | 0 |
| **Total** | **15** | **8** | **2/15 (2/8)** | **1/15 (1/8)** |

A two-cluster scene has at least two latch clusters (< 0.45 m components of the artifact's own M1 scene) with two or more robots each. **The overturn of A22's "S6-in-S1 = NO" rests on one dispatched plan in one episode out of four.** It is real (verbatim and dispatch-matched), but it is rare. In the other 6 two-cluster scenes (E6 3, E7 2, E10 1) the model named one cluster. The E7 dispatch made no progress (§4).

---

## 13. VM End State (Rev 2, 2026-10-11 about 04:15Z)

| Check | Result |
|---|---|
| Chain | `CHAIN_P4 DONE` 20:33:14Z (normal end). `p4/attempts.tsv` has 9 rows: E7 a1 ran, E8 a1 ran, E9 a1-a3 abort, E10 a1 ran, E11 a1-a3 abort |
| Processes | No run_simulation / Kit / fc_launch / chain / sidecar process on the host. `vgu_ros` up and idle. GPU 0 %, 136 MiB |
| Pins | `orchestrator.yaml` `1f656533` in source AND installed (`install/share`). `rag.yaml` `e18c723c`, `s1_dynamic.yaml` `66900e13`, `s1b_dynamic.yaml` `535f5281` in source. These three have no installed copy: the container reads them through the `/ws` bind mount, which is the source file |
| Leftover GT | `data/logs/simulation/` empty |
| Ownership | `chown -R ubuntu:ubuntu ~/v3_s1b data/logs/m5_decisions data/logs/m5_scene` changed 54 files from root to ubuntu. Re-check: 0 non-ubuntu files |
| NOTES | "A22 BATCH END STATE" appended to `~/v3_s1b/NOTES.md` (167 lines, md5 `21f288e9`). Local copy: `data/logs/vm_runs/live_batch/NOTES_vm_final.md` |
| Retrieval | `runs/s1b_E10_*`, `runs/s1b_E11_*` (3 attempts), the `_backup_*` dirs and `p4/` pulled into `data/logs/vm_runs/live_batch/` (`p4/` as `p4_vm/`). Tarball md5 matched both ends, and the VM tarball was removed |
| API | $0 spent in this close-out (retrieval and offline aggregation only) |

**VM: IDLE.** The next live ER-2 work is blocked on the Gemini prepaid balance.

---

## 14. Rev 3 Aggregate Update: E9 and E11 from the A23 Resume

E9 and E11 ran on the A23 tree (`9e18639`). The only behavioural differences from E6-E10 are:

- sequential Nav2 bring-up (harness only), which moves t0 about 6 sim-s later;
- `backend_failed` suppression, which never fired because neither episode had a decision=None.

The condition is otherwise rule 11's (rule 13 in VM NOTES). Aggregation used `data/logs/vm_runs/bringup/aggregate_a23.py` (A22's script plus an MC entry for seed 12; it reproduces `agg_final.json` byte-equal) and wrote `data/logs/vm_runs/bringup/agg_a23.json`.

### 14.1 (a) Attribution

| Episode | Clearing dispatches (max into one cluster) | Alternations | churn_class | Verdict |
|---|---|---|---|---|
| E6 | 3 (2) | 0 | resolved | INDETERMINATE |
| E7 | 1 (1) | 0 | clogged | INDETERMINATE |
| E8 | 1 (1) | 0 | clogged | INDETERMINATE |
| E10 | 2 (1) | 0 | resolved (censored) | INDETERMINATE |
| E9 | 0 (0) | 0 | clogged | INDETERMINATE |
| **E11** | 2 (2) | 0 | **intermittent** | **ARCHITECTURE-CHURN** |

**Pooled, by the letter: LIVELOCK UNDER A REAL MODEL. The verdict is met** (≥ 1 live ARCHITECTURE-CHURN episode). The registered annotation ("k of the opportunity episodes") does not cover an ARCH episode with no opportunity; the script prints "1 of 0".

E11's `intermittent` rests on two unproductive resolution events. The first is a vb yield r4 on {r4, r5}; the second is a vb reverse that M3 dispatched as r1 + r5 on {r1, r5}. The progress they arguably produced together (r4 reaching S at 112.9 sim-s after r5 reversed out of it) is credited to neither event by `s1_churn_stats`'s cluster-intersection window. The second event was also vb but MISmatched: the model planned r1 reverse with r5 waiting, and M3 dispatched r1 and r5 reverse. Its dispatched form therefore came from the grounder. **An owner ruling is needed before this verdict is cited.**

### 14.2 (b)-(e) and Both Clusters

| Aggregate | Value |
|---|---|
| (b) productive, live | 2, 0, 0, 1*, 0, 0. All classified episodes n = 18, nearest-rank p95 = 2. Per productive event [1, 2, 1], p95 2 |
| (c) first-conflict yield | Live 0/6 (Clopper-Pearson 0-0.46). MC upper bound 3/6 (E6, E10, E11). E9's first conflict refused exactly as MC predicted. E11's first analysis was a single-robot no-congestion call |
| (d) wandering vs park | 1 finisher (S1b E4 r2); 0/24 occupied-node arrivals with a finisher occupant; 0 parked-finisher events; tail gridlock in all 11 S1b VM episodes |
| (e) cost | $0.0335 / 0.0284 / 0.0277 / 0.0174 / 0.0495 / 0.0707. Median $0.0310 (`aggregate.py` upper median $0.0335). All-live total $0.2272; A23 resume $0.1202 |
| Both clusters named | 2/31 valid live analyses (2/20 two-cluster scenes); scene-wide plan dispatched 1/31 (E7). E9 and E11 named one cluster in all 12 of their two-cluster scenes |

---

## 15. Rev 4 Aggregate Update: the A24(iii) Predicate Fix and Batch 2 (E12-E17)

> Supersedes §14. The full account is in `docs/reports/2026-10-11-live-batch2.md` §5.

**The predicate fix (`9746f3b`).**

- **(a) Credit.** Progress is now credited to robots RELEASED by a dispatch's own attributed latch breaks, as well as to its cluster.
- **(b) Verdict.** ARCH = opportunity ∧ ≥ 1 alternation ∧ (`intermittent` ∨ ≥ 2 alternations).

Re-run over every bundle, it changes only E11. §14.1's "E11 = ARCHITECTURE-CHURN" and its pooled "LIVELOCK (1 of 0)" are **withdrawn**: E11 is `resolved` and INDETERMINATE.

| Aggregate | §14 (six live) | **Rev 4 (twelve live, fixed predicate)** |
|---|---|---|
| (a) Pooled verdict | LIVELOCK by the letter ("1 of 0") | **NO LIVELOCK UNDER THE REAL MODEL** (E13, E16, E17 opportunity; 0 alternations; APPARATUS) |
| (b) Nonzero / n / p95, all classified | 3 / 18 / 2 | **5 / 24 / 1** (live 4/12, p95 2); per-event dispatches [1, 1, 2, 1, 2, 3], p95 3 |
| (b) budget_k | unfreezable | **unfreezable**: bar 8, 9 more live episodes needed |
| (c) First-conflict yield | 0/6 vs MC 3/6 | **1/12** vs MC 7/12 |
| (d) Wandering vs park | 1 finisher, 0/24 | 1 finisher, 0/33 |
| (e) Cost | median $0.0310, total $0.2272 | median $0.0301, total **$0.4840** |
| Both clusters named | 2/31 | **14/67** (batch 2 12/36) |

## 16. Rev 5 Aggregate Update: the A26 Stack and Batch 3 (E18-E20)

> Supersedes §15. The full account is in `docs/reports/2026-10-12-shield-and-batch3.md` §5-§7.

**Batch 3 ran on a different runtime.** The A25 swept-axis backup, the A26 retreat shield and the B3 fresh-latch fast-fail were all on, through `config/grounding/s1b_dynamic_shield.yaml`. The scorer is the same: the fixed predicate at `9746f3b`. `aggregate_b3.py` is `aggregate_b2.py` plus MC entries for seeds 18-21, and it reproduces `agg_b2.json` exactly on the twelve prior live bundles.

| Aggregate | §15 (twelve live) | **Rev 5 (fifteen live)** |
|---|---|---|
| (a) Pooled verdict | NO LIVELOCK (3 opportunity) | **NO LIVELOCK UNDER THE REAL MODEL** (E13, E16, E17, **E18, E20**; 0 alternations in all 15) |
| (b) Nonzero / n / p95, all classified | 5 / 24 / 1 (live 4/12) | **7 / 27 / 1** (live 6/15, p95 2); per-event dispatches [1, 1, 2, 1, 2, 3, 2, 1], p95 3; dispatch → progress p95 79.3 s |
| (b) budget_k | bar unmet, 9 more needed | **bar unmet by one (7 of 8): n_more = ceil(1 / (6/15)) = 3** |
| (c) First-conflict yield | 1/12 vs MC 7/12 | **3/15** vs MC 10/15 (batch 3: 2/3 vs 3/3) |
| (d) Wandering vs park | 1 finisher, 0/33 | 1 finisher, 0/41 |
| (e) Cost | median $0.0301, total $0.4840 | median $0.0335, total **$0.6477** (batch 3 $0.1637) |
| Both clusters named | 14/67 | 14/89 (batch 3 0/22) |
| Dispatched yields admitted | 3/9 | **8/14** (batch 3 5/5; two clearance releases in E20) |

## References

- Spec: prereg-v3 A21-A22 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- Prior report: `docs/reports/2026-10-10-churn-and-first-live.md`.
- Code:
  - `reasoning/vlm/mock_backend.py`;
  - `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` (`note_dispatch_outcome`), `orchestrator_node.py`.
- Tests: `tests/unit/test_echo_rotation_a22.py`.
- Scripts:
  - `scripts/s1b_live_batch_stats.py` (new; the per-analysis E6 schema);
  - `scripts/s1_churn_stats.py` (additive `cluster_groups`, `max_clearing_dispatches_one_cluster`, `max_alternations_one_cluster`).
- VM kit and bundles: `data/logs/vm_runs/live_batch/` (gitignored): `chain_p4.sh`, `pin_watch.py`, `aggregate.py`, `mc_seeds*.py`, `notes_prereg_p4.md`, `agg_partial.json`.
- Rev 5: `docs/reports/2026-10-12-shield-and-batch3.md`; `data/logs/vm_runs/batch3/` (E18-E20 bundles, `agg_b3.json`, `aggregate_b3.py`, `extras_b3.json`, `b3_extras.py`).
- Rev 4: `docs/reports/2026-10-11-live-batch2.md`; `data/logs/vm_runs/batch2/` (E12-E17 bundles, `agg_b2.json`, `aggregate_b2.py`).
- Rev 3: `docs/reports/2026-10-11-bringup-and-resume.md`; `data/logs/vm_runs/resume/` (E9 b1, E11 b1 bundles), `data/logs/vm_runs/bringup/agg_a23.json`, `aggregate_a23.py`.
- Rev 2 additions (same directory, gitignored): `s1b_E10_seed10_er2_a1/`, `s1b_E11_seed11_er2_a{1,2,3}/` with their side logs, `p4_vm/` (the VM `p4/` kit incl. `attempts.tsv` and `chain_p4.log`), `agg_final.json` (final aggregates), `NOTES_vm_final.md` (VM NOTES after the end-state entry, md5 `21f288e9`).

