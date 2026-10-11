# A23 Infra Wave: Five-stack Bring-up Fix, backend_failed Suppression, and the Live Resume

**Prepared:** 2026-10-11

**Revision history:**

- Initial draft: tier 1 (bring-up diagnosis, sequential fix, validation), the A23 backend_failed suppression ruling, and tier 2 (live E9/E11 resume) with the updated batch aggregates.

---

## Summary

**Status: both tiers done. Tier 1 validated; tier 2 ran E9 and E11 live. E12 not run (budget floor).**

| Question | Answer |
|---|---|
| Diagnosis | Every five-stack abort hit a stack whose lifecycle transition overlapped another stack's startup. Stagger-6 aborts fall in **two phase-locked windows**: class A (5/9) is an r3 bond timeout as r5 spawns; class B (4/9) is an r4 `bt_navigator` get_state failure while r5 configures. r1 never failed. In Jazzy the bond wait is `bond_timeout/2` = 2.0 s and get_state is a hard-coded 2 s. **GUI/autorun refuted.** CPU contention is the cause, as **inter-stack** overlap; the Isaac warm-up share cannot be separated |
| Fix | `NAV2_BRINGUP_MODE=sequential` in `fc_launch.sh` (stack k+1 only after stack k is active in its own log, plus a post-loop health gate). A **harness change**: no Nav2 or lifecycle parameter changes. The default stays `parallel`. Per-stack retry was not needed |
| Validation | **Sequential 6/6 clean** (rule 12: ≥ 5/6). Same-day parallel controls 4/4 clean, but with the batch era's contention profile. Bond lag 2.5-8.8 s vs 0.14-0.25 s sequential. Pooled: **parallel 9/20 vs sequential 0/8** (with both live bring-ups; Fisher one-sided p ≈ 0.024). Cost **+21 s per attempt** (gate 80-85 s vs 60-62 s) and **t0 +6 sim-s** |
| A23 suppression ruling | `decision=None` on a stall analysis arms `backend_failed`. The E10 402 replay collapses **38 → 2** analyses. Suite zero delta (62/6459/153/3 → 62/6475/153/3) |
| E9 (seed 9) | Clean. 7 valid analyses, all naming {r4, r5}. 6 yields refused `no executable retreat` (exactly the MC prediction) and withheld, plus 1 reverse grounded to waits. `clogged`, 4/25 tasks. $0.0495 |
| E11 (seed 11) | Clean. A vb yield r4 and a vb reverse r1+r5 were dispatched, both breaking latches and both unproductive → **`intermittent` → ARCHITECTURE-CHURN by the registered rule** (first live specimen; 0 alternations, opportunity not met). It is an edge case and needs an owner ruling (§7). 6/25 tasks. $0.0707 |
| Updated aggregates (E6-E11, 6 live) | (a) 0/6 opportunity, 1 ARCH (E11) → the pooled verdict is MET by the letter: **LIVELOCK UNDER A REAL MODEL**. Only the "k of the opportunity episodes" annotation does not fit (1 ARCH, 0 opportunity). A ruling is needed before citing; (b) p95 = 2 (n = 18), budget_k still unfreezable; (c) first-conflict yield **0/6** (CI 0-0.46) vs MC 3/6; (d) wandering vs park undecided (1 finisher, 0/24); (e) median $0.031, total $0.227. Both clusters named 2/31, dispatched 1/31 |
| Cost / VM | **$0.1202** this wave (cap $0.15). VM RUNNING idle, pins verified, NOTES updated |

PILOT-ONLY, RECORD = 0.

---

## 1. Diagnosis: Why Five Parallel Nav2 Stacks Abort

**Data.** Every local fc_launch bundle with per-robot Nav2 logs (`data/logs/vm_runs/**`), including the E6 a1/a2 and E9 a1-a3 abort bundles pulled from the VM for this wave: 56 launches, 36 with five stacks and 20 with four. The parser is `data/logs/vm_runs/bringup/diag_bringup.py` (gitignored kit). For every stack it extracts the launch time, the lifecycle transitions, the bond formation, the time the stack went active, and the first lifecycle-manager error. Output: `diag.json`.

**The nine stagger-6 aborts.** "busy" lists the other stacks that had been launched but were not yet active when the failure happened. "r5 launch − fail" is r5's launch time minus the failure time.

| Attempt | Failing stack | Class : node | In transition (age) | Since first launch | Since Isaac start | Busy others | r5 launch − fail |
|---|---|---|---|---|---|---|---|
| S1b E3 a1 | r3 | bond : controller_server | activating (2.4 s) | 24.0 s | 71 s | r4 | 0.0 s |
| E6 a1 | r4 | get_state : bt_navigator | configuring (19.8 s) | 53.6 s | 101 s | r5 | −28.6 s |
| E6 a2 | r3 | bond : controller_server | activating (2.6 s) | 24.2 s | 74 s | r4, r5 | −0.2 s |
| E9 a1 | r3 | bond : controller_server | activating (4.4 s) | 26.2 s | 71 s | r4, r5 | −2.2 s |
| E9 a2 | r4 | get_state : bt_navigator | configuring (18.3 s) | 55.1 s | 100 s | r5 | −30.1 s |
| E9 a3 | r3 | bond : controller_server | activating (2.5 s) | 23.5 s | 70 s | r4 | +0.5 s |
| E11 a1 | r3 | bond : planner_server | activating (4.6 s) | 26.5 s | 72 s | r4, r5 | −1.5 s |
| E11 a2 | r4 | get_state : bt_navigator | configuring (5.9 s) | 54.1 s | 100 s | r5 | −30.1 s |
| E11 a3 | r4 | get_state : bt_navigator | configuring (21.3 s) | 54.1 s | 101 s | r5 | −30.1 s |

**Verdict: the aborts share a timing signature. They fall in two windows that are locked to the launch schedule.**

- **Class A, 5 of 9.** r3's activation bond times out on `controller_server` or `planner_server`, between 2.2 s before and 0.5 s after r5's process launch (23.5-26.5 s after the first launch).
- **Class B, 4 of 9.** r4's `get_state` on `bt_navigator` fails while r4 is configuring its behavior-tree plugins and r5 is also configuring (53.6-55.1 s after the first launch).
- r1 and r2 never fail. Every four- and five-stack abort, in any era, had at least one other stack mid-startup. The stagger-3 era (3 of 19 five-stack aborts) fits too: r2 bond at 15.2 s with r3-r5 busy, r3 get_state at 36.9 s, and r3 bond at 32.9 s with r4-r5 busy. So do the four-stack VOIDs: r2 bond timeouts with r3-r4 busy.

**Mechanism (Nav2 Jazzy 1.3.13, verified against the jazzy `lifecycle_manager.cpp` and the container's `lifecycle_service_client.hpp`).**

- `createBondConnection` waits **`bond_timeout / 2` = 2.0 s** for the bond to form, although its error text says "after 4.00s".
- `changeStateForNode` calls `get_state()` with the client's **hard-coded 2 s default**. No lifecycle parameter changes it.
- Under contention both windows are exceeded. In the successful stagger-6 launches, the slowest lifecycle transition (mostly `bt_navigator` configure) takes 10-19 s, r4 and r5 take about 36-39 s from launch to active, and the lifecycle manager logs "connected with bond" up to 5 s after the server logged "Creating bond". That last figure is a lag in the manager's own processing and a starvation proxy; it is not the formation window.

**Hypotheses.**

| Hypothesis | Verdict | Evidence |
|---|---|---|
| CPU contention during parallel stack launches at RTF warm-up | **Supported, as inter-stack contention** | Every abort overlaps another stack's startup, the phase lock above, and a stack alone comes up in 6-11 s. The Isaac-warm-up share cannot be separated: the Isaac-start offsets (70-74 s, 100-101 s) are fixed by the same schedule |
| Lifecycle bond window too tight under five-stack load | **True but insufficient** | The window is 2.0 s, not 4.0 s. Bumping `bond_timeout` could address class A at most. Class B (4 of 9) runs on a hard-coded 2 s timeout. `bond_timeout` is also the runtime heartbeat timeout, so bumping it would change episode behaviour |
| GNOME / GUI Kit stealing cycles (autorun) | **Refuted** | Idle load 0.00. During bring-up, gnome-shell, Xorg and tracker never appear in the top-8 CPU samples. There is no `~/.config/autostart` and no GUI Kit (`~/Desktop/IsaacSim.desktop` is only a shortcut; `ep_run.sh` already refuses to start while a GUI Kit runs). Steady state with five stacks: Kit about 270-290 %, `perception_node` 75-130 %, and five `camera_localize` plus five lifecycle managers at about 9 % each. The 1-min load average reaches 40-54 on 8 vCPU (4 physical cores) |

The rate comparison "stagger 6 did worse than stagger 3" (9/16 vs 3/19 before today) is consistent with the phase lock: stagger 6 puts r3's activation on top of r5's spawn burst. With today's controls it is 9/20 vs 3/19. The phase lock carries the diagnosis better than the rate comparison does.

---

## 2. Fix: Sequential, Lifecycle-gated Bring-up (Harness Only)

`scripts/vm/fc_launch.sh` (`3cfc80c`, md5 `5a5ee4ac`):

| Item | Behaviour |
|---|---|
| `NAV2_BRINGUP_MODE` | `parallel` (default, unchanged; the two-robot goldens stay byte-identical) or `sequential`. Sequential launches stack k+1 only after stack k's **own** log shows `lifecycle_manager_navigation ... Managed nodes are active`. It aborts on `Aborting bringup` or when the per-stack budget `NAV2_STACK_ACTIVE_TIMEOUT_SEC` runs out (default 120 polls) |
| Health gate (sequential) | After the usual lifecycle gate, every stack's last active line must follow its last `CRITICAL FAILURE` (bond heartbeat loss). A stack that went down after activating is given `NAV2_HEALTH_GRACE_SEC` (45) to respawn. This closes the old gate's blind spot: three stagger-3 bundles went down 8-18 s after the gate and were still scored OK |
| `BRINGUP_ONLY=1` | The validation path. It skips the backend rewrite and rebuild, so `orchestrator.yaml` is never touched, and never starts M4 or M5 ($0 API). It holds `BRINGUP_HOLD_SEC`, re-checks health, logs `BRINGUP_ONLY PASS`, and exits through the stop-flag cleanup |
| Registered as | A **harness** change. No Nav2 parameter and no lifecycle parameter differs; the A11 Nav2-tuning exclusion is untouched |

Per-stack retry was not built: in sequential mode it would only be a fallback, and the validation needed none.

**Caveat.** The "active Ns after its launch" lines and the `stack_s` column count poll iterations (about 1.4 s each), not seconds, so `NAV2_STACK_ACTIVE_TIMEOUT_SEC` is about 1.4× longer in wall time than its name says. The deployed md5 was left unchanged. Every timing in this report comes from log timestamps.

**Tests.** `tests/unit/test_fc_launch_dry_run.py` adds 12 cases:

- launch/wait order r1 → wait r1 → … → r5;
- per-stack own-log polls and budget;
- no stagger sleep in sequential mode;
- the health gate sits between the lifecycle gate and M4;
- the parallel default is unchanged;
- an unknown mode is refused;
- BRINGUP_ONLY skips stage 1 and never starts M4/M5;
- the single new timing line on the default path.

The state classifier (`aborted`, `active`, `down`, `pending`) was checked under the container's mawk 1.3.4 against real logs: an E11 abort, an s1r_E1 recovered stack, a truncated copy of it, and a missing file.

---

## 3. Validation (Rule 12, Pre-registered in VM NOTES Before Run 1)

**Design.**

- Six consecutive `BRINGUP_ONLY` runs. Each uses real Isaac with the seed's USD, M1 and five Nav2 stacks, with a 30 s hold past the gate. Seeds 9, 11, 7, 9, 11, 10: seeds 9 and 11 went 0/6 in the batch.
- Idle gate and pins (orchestrator src and installed, rag, s1b_dynamic, fc_launch) before and after every run.
- CLEAN means `BRINGUP_ONLY PASS` and no `Aborting bringup`, `unable to be reached`, `get_state service client` or `CRITICAL FAILURE` line in any Nav2 log.
- Driver `~/v3_s1b/bringup/val_chain.sh`. Results and bundles are in `data/logs/vm_runs/bringup/vm/`.

| Run | Seed | Verdict | First launch → gate | Isaac → gate | Sim clock at check |
|---|---|---|---|---|---|
| seq r1 | 9 | CLEAN | 85 s | 130 s | 36 s |
| seq r2 | 11 | CLEAN | 81 s | 130 s | 35 s |
| seq r3 | 7 | CLEAN | 85 s | 131 s | 35 s |
| seq r4 | 9 | CLEAN | 80 s | 129 s | 35 s |
| seq r5 | 11 | CLEAN | 83 s | 129 s | 35 s |
| seq r6 | 10 | CLEAN | 82 s | 131 s | 35 s |

**Result: 6/6 CLEAN. VALIDATED (≥ 5/6). Proceeded to tier 2.**

**Same-day parallel controls (stagger 6, `BRINGUP_ONLY`, seeds 9, 11, 9, 11).** Pre-registered as "reported separately, not part of the decision". Result: 4/4 CLEAN, gate 60-62 s, Isaac → gate 108-110 s, sim clock 29 s.

**Same-day margins (the core evidence; log timestamps).**

| Metric | Sequential today (n = 6) | Parallel today (n = 4) | Parallel stagger-6 era, successful launches (n = 7) |
|---|---|---|---|
| Max stacks in lifecycle at once | **1** | 2 | 2 |
| Median launch → active, r1 / r2 / r3 / r4 / r5 | 7.5 / 8.2 / 11.0 / 16.8 / 27.8 s | 6.6 / 8.2 / 21.1 / 38.1 / 35.8 s | 7.2 / 11.4 / 21.2 / 39.2 / 35.4 s |
| Slowest single lifecycle transition per launch | 1.8-10.0 s | 11.4-16.8 s | 10.0-18.7 s |
| Manager-side bond lag (connected − server's "Creating bond") | **0.14-0.25 s** | 2.49-8.78 s | 0.79-4.96 s |
| First launch → all active (median) | 71.9 s | 59.8 s | 60.1 s |

The parallel controls reproduce the batch era's timing profile on every row. Today's host was **not** quieter. Those four attempts survived the same contention that aborted 9 of the earlier 16. Sequential removes the overlap that both abort classes need.

**Before / after.**

| Comparison | Abort rate |
|---|---|
| Stagger-6 parallel, batch era | 9 / 16 (0.56) |
| Stagger-6 parallel, pooled with today's controls | **9 / 20 (0.45)** |
| Sequential, validation | **0 / 6** (Clopper-Pearson upper 0.46) |
| Sequential, validation + every rule-13 live bring-up (pooling pre-registered before those attempts) | **0 / 8** (6 validation + E9 b1 + E11 b1, each brought up first try; Clopper-Pearson upper 0.37; against pooled parallel 9/20, Fisher one-sided p ≈ 0.024) |

Validation alone gives Fisher one-sided p ≈ 0.054: suggestive, not established. The adoption case does not rest on significance:

- the mechanism is removed (concurrency 1, bond lag ≤ 0.25 s);
- expected wall time favours sequential: about +21 s per attempt, against about 0.45 × 150 s ≈ 68 s of expected parallel retry overhead;
- sequential dominates on lost episodes (E9 and E11 were lost entirely in the batch).

**Condition side effect.** M5 starts about 6 sim-s later (35-36 vs 29 sim-s at the check). Isaac's `duration_sec` 600 is absolute, so the observation window (600 − t0) shrinks by about 1 %. This is recorded in rule 13.

---

## 4. A23 Ruling: backend_failed Arms the Scene-unchanged Suppression

| Item | What shipped (`d7ed1b3`) |
|---|---|
| Behaviour | `_update_suppression`: a **stall** analysis with `decision=None` (after the reasoner's bounded retries) now arms the reference with outcome `backend_failed`. Before, it reset with `no_decision`. Non-stall analyses and a missing snapshot still reset. A changed robot set or a move past epsilon still releases the next analysis |
| Why | E10: the 402 loop re-analysed the unchanged scene every ~3 sim-s and spent 38 of MAX_ANALYSES = 40 on failures |
| Replay fixture | `tests/unit/data/backend_failed_a23/e10_402_triggers.json`: the 38 decision=None E10 analyses, with trigger sets from the M5 log and positions from each artifact's scene. Replayed through the node's own `_suppression.check` and `_update_suppression`, **38 → 2 executed analyses**: one per trigger-set change ({r1..r4} ×2, then all five ×36). 36 triggers are suppressed against a `backend_failed` reference |
| Tests | `test_backend_failure_arms_backend_failed` replaces the pre-A23 `test_backend_failure_does_not_arm` pin. Also added: release on a changed scene, no arming on a contradiction analysis, and the two replay tests |
| Suite | Zero delta against a fresh `dfe4e49` worktree (no stash): 62 / 6459 / 153 / 3 → 62 / 6475 / 153 / 3, identical failing ids (+16 new tests). Ruff clean on the changed lines (two E501 in the test file predate this wave) |
| Live relevance | On a valid decision the behaviour is identical. E6-E8 had zero decision=None analyses. **Trade-off for the owner:** a transient failure on a frozen gridlock now silences re-analysis until the scene moves past epsilon or changes its robot set. The reasoner's in-call bounded retries are the only retry |

---

## 5. Tier 2: Deploy and Pre-registration (Rule 13)

| Step | Result |
|---|---|
| Merge | `feat/v3-bringup` (`3cfc80c` + `d7ed1b3`) merged into `feat/v3-integration` as `9e18639` |
| Deploy p5 (`~/v3_s1b/p5/deploy_p5.sh`, as root) | Delta = `orchestrator_node.py` + `reanalysis_suppression.py`. Pre-image md5 OK (`f84c9ba2` / `0079ec57` = the A22 tree, in source and installed), backed up to `p5/deploy/pre`. Source md5 OK, colcon rc 0, installed `51218d7a` / `b22d16b9` OK, PACKAGES SRC==INSTALLED OK. `fc_launch.sh` `5a5ee4ac` was deployed for tier 1 (pre-image `5ef336f5` kept in `~/v3_s1b/bringup/pre/`). Pins untouched: orchestrator `1f656533` (source and installed), rag `e18c723c`, s1b_dynamic `535f5281`. In `vgu_ros`, `_update_suppression` imports and contains `backend_failed` |
| Pre-registration | Rule 12 result and rule 13 appended to `~/v3_s1b/NOTES.md` before any live call (192 lines, md5 `b98aa7fd`). Rule 13 records: rule 11's condition verbatim except `NAV2_BRINGUP_MODE=sequential` and its ~6 sim-s later t0; the $0.15 hard batch cap (an episode starts only when ≥ $0.04 remains, with cost_watch cap = min($0.10, remaining)); the per-seed MC predictions (A23 tree: s9 refused, no executable retreat; s11 executable yield r2; s12 executable yield r4); the definition of "completes cleanly" that gates E12; and pooling of every live bring-up attempt into the sequential rate |
| Chain | `p5/chain_p5.sh`, run as ubuntu with `EPISODES="9 11"`. It reuses chain_p4's gates and sidecars, extends the pins check with fc_launch and the installed `orchestrator_node.py`, and logs every attempt to `p5/attempts.tsv` with labels `s1b_E{k}_seed{k}_er2_b{a}` |
| API | Gemini credits were taken as working per the A23 corrigendum (HTTP 200 probe); no extra probe was spent |

---

## 6. E9 (Seed 9)

**Run.** `s1b_E9_seed9_er2_b1`, STAMP 20261011_095329, first-attempt bring-up (sequential gate 84 s). GATE OK, RESTORE OK, 0 tracebacks. `backend_id` gemini on 7/7, all valid on one attempt each. No decision=None, so `backend_failed` was never exercised. No hard stop fired; the episode ran to the Isaac horizon (end 600.6 sim-s, t0 ≈ 30.9 sim-s). **Completed cleanly** under rule 13's definition.

| # | sim-s | Model decision | Scene clusters | Plan (provenance) | M3 / M5 outcome |
|---|---|---|---|---|---|
| 1 | 50.2 | yield r5 → r4 | {r4,r5} | 5 yield, 4 cross (m3_default, matched) | refused `no executable retreat` → withheld |
| 2 | 54.7 | yield r5 → r4 | {r2,r3}, {r4,r5} | same | same refusal → withheld |
| 3 | 58.9 | yield r5 → r4 | {r2,r3}, {r4,r5} | same | same → withheld |
| 4 | 95.4 | yield r5 → r4 | {r2,r3}, {r4,r5} | same | same → withheld |
| 5 | 99.6 | reverse r4+r5 | {r2,r3}, {r4,r5} | 4/5 reverse (repaired, matched) | dispatched as `temporary_wait` ×2 (`grounding=dynamic_arms:ambiguous`). No clearing leg, no latch break |
| 6 | 112.4 | yield r5 → r4 | {r2,r3}, {r4,r5} | same as 1 | same refusal → withheld |
| 7 | 155.6 | yield r5 → r4 | {r1,r2,r3}, {r4,r5} | same | same → withheld; suppressed to the end (186 suppressed triggers) |

- **Outcome.** `partial`: 4/25 tasks (last progress 134.9 sim-s), gridlock 122.1 rel-s, final clusters {r1, r2, r3} + {r4, r5}, latched to the end. 2 occupied-node arrivals at N, neither with a finisher occupant. 0 finishers, tail gridlock.
- **Churn.** `clogged`: 0 clearing dispatches, 0 resolution events, alternation 0. Attribution INDETERMINATE (no opportunity).
- **Provenance.** m3_default 6, repaired 1, vb 0. vb ∧ matched 0/7.
- **MC.** The first encounter held exactly (MC r4+r5 at 16.8 s; live r4+r5 at 17.3 rel-s). So did the predicted outcome: the model named the same pair, and M3 refused it `no executable retreat` on every yield. First-conflict yield: **no**.
- **Both clusters.** 6 two-cluster scenes; the model named only {r4, r5} in all 6. No plan addressed both.
- **Echo counterfactual (stateless).** Same cluster as the model on 7/7. Executable on 0/7 (6 `no executable retreat`, 1 `no shared lane`).
- **Cost.** $0.0495 over 7 billed calls (about $0.0071 per call); no stage-2 call. This is the costliest live episode so far, because it had 7 valid analyses against 2-5 before.

---

## 7. E11 (Seed 11)

**Run.** `s1b_E11_seed11_er2_b1`, STAMP 20261011_104946, first-attempt bring-up (sequential gate 82 s). GATE OK, RESTORE OK, 0 tracebacks. Gemini 9/9 valid on one attempt each, plus one stage-2 call: 10 billed calls. No decision=None. No hard stop fired; the episode ran to the horizon. **Completed cleanly.**

| # | sim-s | Model decision | Scene clusters | Plan (provenance) | M3 / M5 outcome |
|---|---|---|---|---|---|
| 1 | 32.7 | no congestion (single-robot r1 stall) | — | — | armed `no_congestion` |
| 2 | 59.5 | yield r4 → r5 | {r4,r5} | 4 yield, 5 cross (**vb, matched**) | dispatched yield r4 (stage-2 retreat call; `node_handoff:robot_4->robot_5`, lane x) + r5 `temporary_wait`. No `gate_admit`. Latch broke at 63.7: **unproductive** |
| 3 | 105.8 | reverse r1 (r5 wait) | {r1,r5}, {r2,r3} | 1 reverse, 5 wait (**vb, MISmatched**) | dispatched r1 **and r5** reverse. 2 latch breaks at 107.6: **unproductive** |
| 4 | 125.2 | temporary_wait r2-r4 | {r2,r3} | m3_default, matched | dispatched waits ×3 |
| 5 | 138.3 | temporary_wait r2-r4 | {r1,r5}, {r2,r3} | 4 cross, 2/3 wait → repaired, matched | dispatched waits ×3 |
| 6 | 151.8 | no congestion | {r1,r5}, {r2,r3} | — | armed `no_congestion` |
| 7 | 161.6 | no congestion | {r1,r5}, {r2,r3} | — | armed `no_congestion` |
| 8 | 166.0 | temporary_wait r2-r4 | {r1,r5}, {r2,r3,r4} | m3_default, matched | dispatched waits ×3 |
| 9 | 179.2 | junction_clear r2-r4 | {r1,r5}, {r2,r3,r4} | 4 yield; 2, 3 cross (m3_default, matched) | `no feasible yielder` (0.00 m ×3) → withheld; suppressed to the end (151 suppressed triggers) |

- **Outcome.** `partial`: 6/25 tasks (last progress 159.3 sim-s), gridlock 133.0 rel-s, final clusters {r2, r3, r4} + {r1, r5}. 1 occupied-node arrival (r4 at S, occupant r5), no finisher, tail gridlock.
- **Churn.** 2 clearing dispatches, both latch-breaking and both scored UNPRODUCTIVE by `s1_churn_stats`. That makes `churn_class` **`intermittent`**. Alternation 0. The two clusters intersect through r5, so the max clearing count into one cluster is 2 (opportunity needs ≥ 3).
- **Rule 10/11 verdict: ARCHITECTURE-CHURN.** The rule is "churn_class intermittent OR ≥ 2 A-B-A alternations". This is the first live specimen.
- **Edge case for an owner ruling. The verdict is reported as registered and not reinterpreted here.**
  - The two events are different strategies on different (r5-sharing) pairs, with no A-B-A. This is not E3's oscillation.
  - r4 arrived at S at 112.9 sim-s, after r5 had reversed out of S. That progress is credited to neither event:
    - event 1's productive window closes at the next clearing dispatch that intersects its cluster (the r1+r5 reverse at 107.3, 5.6 s earlier);
    - r4 is not in event 2's cluster {r1, r5}.
  - Under a group-level productive credit the episode would be `resolved`.
  - **The second unproductive event's dispatched form came from the grounder, not the model.** Analysis 3 was vb but MISmatched: the model planned r1 reverse with r5 waiting, and M3 dispatched r1 **and** r5 reverse. E10 analysis 2 was the mirror case: a two-robot reverse plan grounded as one robot. This bears on architecture-vs-apparatus attribution.
  - The `intermittent` threshold (≥ 2 unproductive) is met at its minimum.
- **Provenance.** vb 2, m3_default 3, repaired 1, none 3 (no-congestion). vb ∧ matched 1/9 (analysis 2).
- **MC.** The first encounter held exactly (MC r4+r5 at 28.2 s; live r4+r5 at 28.1 rel-s). MC's echo named [r2, r3] → executable yield r2. The live first analysis was a single-robot no-congestion call. First-conflict yield: **no**. The model's first yield (analysis 2, on {r4, r5}) was dispatched but never reached `gate_admit`.
- **Both clusters.** 6 two-cluster scenes; the model named one cluster in all 6.
- **Echo counterfactual (stateless).** Same cluster as the model on 4/9. Executable on 2/9 (analyses 2 and 3, both yields; the other 7 were `no shared lane` or `no declared junction` refusals).
- **Cost.** $0.0707 over 10 billed calls. Analysis 2 cost $0.0125 including the stage-2 call; the rest were about $0.005-0.009 each.

---

## 8. Updated Aggregates Over All Live Episodes

Computed with `data/logs/vm_runs/bringup/aggregate_a23.py`. It is A22's `aggregate.py` unchanged except for an MC entry for seed 12; it first reproduced Rev 2's `agg_final.json` byte-equal on every block. Inputs: E6 (`churn_wave/s1b_E6_seed6_er2_a3`), E7, E8, E10 (censored), E9 b1 and E11 b1. Output: `data/logs/vm_runs/bringup/agg_a23.json`. E10's 38 HTTP-402 analyses are excluded from every per-analysis denominator.

| Aggregate | Rev 2 (E6, E7, E8, E10) | **Now (+ E9, E11)** |
|---|---|---|
| (a) Attribution per episode | INDETERMINATE ×4 | INDETERMINATE ×5, **ARCHITECTURE-CHURN ×1 (E11, `intermittent`)** |
| (a) Opportunity episodes (≥ 3 clearing into one cluster) | 0/4 | **0/6** (max 2, 1, 1, 1, 0, 2) |
| (a) Alternations (max in one cluster) | 0 everywhere | 0 everywhere |
| (a) Pooled verdict, by the letter | INDETERMINATE | **LIVELOCK UNDER A REAL MODEL: the verdict is met** (≥ 1 live ARCHITECTURE-CHURN episode). The registered annotation "k of the opportunity episodes" does not cover an ARCH episode with no opportunity (the script prints "1 of 0"). See §7 for the edge case. **Owner ruling needed before citing** |
| (b) Productive resolutions, live | 2, 0, 0, 1* | 2, 0, 0, 1*, **0, 0** |
| (b) All classified episodes, nearest-rank p95 | 2 (n = 16) | **2 (n = 18)** |
| (b) Dispatches per productive event | [1, 2, 1], p95 2 | unchanged ([1, 2, 1], p95 2): still too thin to freeze `budget_k` |
| (c) First-conflict yield, live | 0/4 (CI 0-0.60), MC 2/4 | **0/6 (CI 0-0.46), MC upper bound 3/6** (E6, E10, E11) |
| (d) Wandering vs park | 1 finisher, 0/21 | **1 finisher ever, 0/24** occupied-node arrivals with a finisher occupant, 0 parked-finisher events, tail gridlock in all 11 S1b episodes. UNDECIDED |
| (e) Cost per live episode | $0.0335 / 0.0284 / 0.0277 / 0.0174 | + **$0.0495 (E9) / $0.0707 (E11)**. Median $0.0310 (mean of the middle two; the script's upper median is $0.0335). Range $0.0174-0.0707. All-live total $0.2272. This batch $0.1202 |
| Both clusters named | 2/15 valid (2/8 two-cluster scenes); dispatched 1/15 | **2/31 valid analyses (2/20 two-cluster scenes); scene-wide plan dispatched 1/31 (1/20); episodes 1/6 (E7 only)**. E9 and E11 had 12 two-cluster scenes and named one cluster in all of them |

**Reading.**

- The live model keeps naming one cluster.
- It still never produced a first-conflict yield that reached `gate_admit`: 0/6 against an MC upper bound of 3/6.
- Under the registered definitions, the first ARCHITECTURE-CHURN episode is E11. That rests on two unproductive resolutions (the minimum) whose progress credit is split by the cluster-intersection rule, with 0 alternations. The attribution question the batch was meant to power is therefore **answered positively by the letter (LIVELOCK UNDER A REAL MODEL)**. That verdict rests on a definitional edge (§7) that needs a ruling before it is cited.
- The new episodes were costlier: 7 and 9 valid analyses, against 2-5 before.

---

## 9. Costs and VM End State

| Item | Value |
|---|---|
| API spend, this wave | **$0.1202** (E9 $0.0495 + E11 $0.0707; cost_watch estimate at the published ER-2 rate, a lower bound). Batch cap $0.15 respected. Per-episode cap $0.10 never reached. $0 for tier 1 (bring-up-only runs never start M5) |
| E12 | **Not run.** $0.0298 remained, below the pre-registered $0.04 floor. The seed-12 kit (`p5/gen_s12.sh`, `build_s12.sh`, `ov_s12.sh`) was left unused; no seed-12 scenario, USD or overlay was generated |
| Bring-up this wave | Sequential: 6 validation runs + 2 episode attempts, **0 aborts / 8**. Parallel controls 4/4 clean |
| Processes | No run_simulation, Kit, fc_launch, chain or sidecar process. `vgu_ros` up and idle. GPU 0 %, 136 MiB |
| Pins | `orchestrator.yaml` `1f656533` (source and installed), rag `e18c723c`, s1_dynamic `66900e13`, s1b_dynamic `535f5281`. A23 runtime: `orchestrator_node.py` `51218d7a` + `reanalysis_suppression.py` `b22d16b9` (source and installed), `fc_launch.sh` `5a5ee4ac` |
| Leftover GT / ownership | `data/logs/simulation/` empty. `chown -R ubuntu:ubuntu ~/v3_s1b data/logs/m5_decisions data/logs/m5_scene`: 0 non-ubuntu files |
| NOTES | Rules 12 and 13, the rule-12 result and the A23 end state appended (`~/v3_s1b/NOTES.md`, 200 lines, md5 `0aade116`). Local copy: `data/logs/vm_runs/bringup/NOTES_vm_a23.md` |
| Retrieval | E9 b1 and E11 b1 bundles, side logs, `_backup_*` and `p5/` pulled to `data/logs/vm_runs/resume/`. Validation and control bundles in `data/logs/vm_runs/bringup/vm/` |
| VM | **RUNNING, idle** (not stopped, per the brief) |

---

## References

- Spec: prereg-v3 A23 and its corrigendum (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- Prior report: `docs/reports/2026-10-11-s1b-live-batch.md` (Rev 3 aggregates updated from this wave).
- Code: `scripts/vm/fc_launch.sh`; `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (`_update_suppression`), `reanalysis_suppression.py`.
- Tests: `tests/unit/test_fc_launch_dry_run.py`, `tests/unit/test_m5_reanalysis_suppression.py`, `tests/unit/data/backend_failed_a23/`.
- Kit and bundles (gitignored): `data/logs/vm_runs/bringup/` (`evidence/`: `both.py` for the both-clusters counts, `mc_seeds_9_11_12.py` for the rule-13 MC predictions, suite outputs `base.txt` / `new.txt` / `*_ids.txt`, `agg_repro.json`; `diag_bringup.py`, `diag.json`, `diag_sameday.json`, `val_chain.sh`, `notes_prereg_bringup.md`, `notes_rule12_result.md`, `vm/` validation and control bundles, `e6/` and `e9/` pulled abort bundles, `p5/` resume kit).
- External: Nav2 jazzy `nav2_lifecycle_manager/src/lifecycle_manager.cpp` (`createBondConnection`, `changeStateForNode`); container `/opt/ros/jazzy/include/nav2_util/nav2_util/lifecycle_service_client.hpp` (`get_state` default 2 s).
