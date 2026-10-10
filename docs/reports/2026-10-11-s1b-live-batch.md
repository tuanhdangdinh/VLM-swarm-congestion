# A22 Live Batch: Echo Rotation and Five Live ER-2 Episodes on S1b

**Prepared:** 2026-10-11

**Revision history:**

- Rev 1 (2026-10-11, PARTIAL): A22 echo-rotation fix (build, tests, merge, deploy); live batch episodes E7 and E8, E9 not run (3 Nav2 bring-up aborts); E10/E11 ran unattended on the VM but their bundles were NOT retrieved, because SSH to the VM was lost mid-batch (the Mac's public IP changed and the VM firewall admits only the old IP). All aggregates are PROVISIONAL over E6-E8.

---

## Summary

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

- **E9.** Not run (section 3).
- **E10 and E11.** Running or queued unattended on the VM (section 8). Not analysed.

---

## 7. Aggregates (PROVISIONAL, E6-E8 Live; Definitions per Rule 11)

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

---

## 8. VM State at Loss of Access, and the Resume Checklist

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

