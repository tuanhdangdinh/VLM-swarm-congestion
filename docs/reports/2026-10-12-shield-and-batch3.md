# The A26 Retreat Shield, the B3 Fast-fail and Live Batch 3

**Prepared:** 2026-10-12

**Revision history:**

- Initial draft: A26(i) retreat shield (B1 + M5 task intent) and A26(ii) B3 fresh-latch fast-fail built test-first on the 9 real A25 yields; zero-delta suite; merged; full A26 stack (with the A25 swept-axis fix) deployed; live batch 3 (E18-E21); Rev 5 aggregates.

---

## Summary

**Status: built, deployed and exercised live. Every dispatched live yield in batch 3 was admitted (5/5, against 3/9 before A26). The budget_k bar is still one episode short (7 of 8).**

| Question | Answer |
|---|---|
| Shield predicate | A derived yield on a dynamic footprint view holds every bystander outside the command whose M5 **intent path** comes within 0.45 + 0.05 m of the retreat centreline (backup, then pull-off), unless the bystander is **pinned**. The intent path runs from its position to its current task node, then to its next node when it can reach the current node and finish its dwell inside the yield's nominal motion time. Pinned means within 0.45 m of a non-member, both not MOVING: a mutual latch neither robot can leave. Each shielded robot gets an unlinked `temporary_wait` with the yield's wait budget, tagged `grounding=retreat_shield:<id>`, and is never a passer (§2) |
| Intent read | The brief's premise needed a second leg. No A25 blocker was dwelling at its decision. E14 r2 and E17b r2 were traveling to the node they would dwell at, and only the leg AFTER arrival and dwell crosses the retreat. M5 therefore also supplies the next task node and the dwell left (`TaskStreamTracker.departure`), injected beside the node-handoff `goal_reference_of` (§2.1) |
| Fixtures | **4/4 mechanism-B blockers shielded:** E10 r3, E13 r2, and E14 r2 and E17b r2 (the last two only through the intent read). **E16: nobody shielded.** Over-hold on the 9 scenes: 5 of 10 holds, by the live-GT counterfactual (§2.4) |
| E16 discriminator | **The pin.** E16 r3's intent crosses the corridor at 0.0 m, but r3 stood 0.413 m from r2, both STOPPED, and GT shows the pair frozen there from 105 to 200 sim-s. The same scene with r2 MOVING shields r3. No margin or intent rule separates it otherwise without losing E10 and E13 (§2.3) |
| B3 | A clearing robot continuously held for 2 s by a hold that began after its command started fails its backup or pull-off at once. The command carries M3's key `fresh_latch_fast_fail`; M4 reads `/safety/holds` through `FreshLatchWatch`. **Live: it fired once,** on E19's reverse r3, 8.1 wall-s in against a 195 s deadline, 2.1 s after bystander r1 was latched with it. It cannot fire on a physical block: E18's reverse r5 ran to its deadline against a corner with no latch (§3, §6) |
| Suite | Zero delta: 62/6578/153/3 → 62/6646/153/3, identical failing ids. Merged into `feat/v3-integration` as `86f83bc` |
| Batch 3 | **E18, E19 and E20 ran** (3/3 first-attempt sequential bring-ups; pooled sequential 0 aborts in 17). E21 was not run: the $0.04 start floor was not met, with $0.0363 remaining. **Admitted/dispatched 5/5** (E18 2/2, E19 0/0, E20 3/3), against 3/9 for E6-E17. Two of the five were released by passer **clearance** (E20); before this batch only E6 ever was. Shield: 3 events, 7 robot-holds, all on admitted yields. B3: 1 firing (a reverse) |
| Safety finding | A shield halts the robot where it is at DISPATCH, not at the snapshot the sweep validated. E18's shielded r1 drifted 0.70 m during the M2 call and stopped 0.25 m off the corridor. The yielder (an exempt pair) then backed past it at a **0.23 m centre distance**. There was no contact, but the margin was thin (§6.2) |
| Rev 5 aggregates | (a) **NO LIVELOCK UNDER THE REAL MODEL**: 5 opportunity episodes (E13, E16, E17, E18, E20), 0 ARCH, 0 alternations in 15 live episodes. (b) **budget_k bar NOT met, 7 of 8** nonzero productive (E18 and E20 are new; live 6/15), so **n_more = 3** (was 9). (c) First-conflict yield **3/15** live (CI 0.043-0.481) against MC 10/15; batch 3 alone 2/3. (d) Both clusters named 14/89 (0/22 in batch 3). (e) Still one S1b finisher; 0/41 occupied-node arrivals had a finisher occupant. (f) Median $0.0335 per episode |
| Cost | Batch 3 **$0.1637** of $0.20 (the A25 reserve-one-call rule never had to fire). All-live total $0.6477 over 15 episodes. Offline build $0 |
| VM | Clean and **RUNNING**. A new A26 pin line is in NOTES; the pinned configs are unchanged |

PILOT-ONLY, RECORD = 0.

---

## 1. Inputs

- **Rulings:** prereg-v3 A25 and A26 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`). A26(i) adopts B1 WITH intent (a retreat shield through the node-handoff registry channel, config-gated, default-off, S1 cells only). A26(ii) adopts B3 as a stop-gap. A26(iii) rejects B2.
- **Source report:** `docs/reports/2026-10-12-no-admit-diagnosis.md`, mechanism B (§5), the offline B1 check, and its over-hold and dwelling-miss cases.
- **Fixtures:**
  - `tests/unit/data/a25_no_admit/yields.json`: the 9 live S1b yields E6-E17, each re-grounded offline to the exact dispatched yield.
  - `tests/unit/data/a26_retreat_shield/intents.json` (new): M5's task intent at each of the 9 decisions. It is reconstructed from each bundle's authoritative `decisions/tasks_*.jsonl`: the current task node, the next node, and the dwell left. It agrees with an independent `m5.log` reconstruction.
- **Tree:** `feat/v3-integration` @ `0f9d423`. Worktree `vgu-vlm-swarm-v4a`, branch `feat/v3-retreat-shield`, created fresh with no stash.

---

## 2. The Retreat Shield (A26(i))

### 2.1 What the intent read had to add

The brief assumed `TaskRegistry.mission_goal` covers the "dwelling" blockers. **It does not, on its own.**

- No blocker was dwelling at its decision. E14 r2 and E17b r2 were still TRAVELING to the node they would dwell at:
  - E14 r2: 0.40 m from Wm, then on to E.
  - E17b r2: 1.11 m from E, then on to Wp.
- Their CURRENT-goal legs never come near the retreat (3.43 m and 2.03 m). The leg that hits it starts after they arrive, dwell 5 s and depart (0.27 m and 0.42 m).
- While a robot dwells, `mission_goal` is the node it is sitting on, so it never reports where the robot goes next.

So the intent read is two values from M5, both injected exactly like the node-handoff `goal_reference_of`:

- the registry's current task node (`TaskRegistry.mission_goal`, the same channel);
- from the task stream (`TaskStreamTracker.departure`), the next task's node and the dwell still to wait at the current one.

The new lookup is `OrchestratorNode._task_intent` → `InProcessPipeline(task_intent_of=...)` → `ground_reasoner_result(task_intents=...)`. It is read only when `retreat_shield` is on.

### 2.2 The predicate

`reasoning/rag/retreat_shield.py`. For a derived yield on a dynamic footprint view, with `retreat_shield` and `dynamic_scene_arms` on, every robot outside the command is scored.

- **Corridor:** the retreat centreline as M4 drives it. The backup runs from the yielder's snapshot pose along `backup_facing_rad` (else its heading) for `backup_distance_m`. The pull-off leg then runs to `(retreat_x_m, retreat_y_m)`.
- **Intent path:**
  - snapshot position → current task node;
  - then → the next node, only if the robot can reach the current node and finish its dwell inside the yield's nominal motion time. That test is `distance / 0.2 m/s + dwell ≤ backup/0.1 + π/0.5 + |lateral|/0.1`: M4's speed limit and M4's own naive motion formulas, so there are no new free constants.
- **Shield** when the intent path comes within `min_distance_m + retreat_shield_margin_m` (0.45 + 0.05 m) of the corridor, **unless the robot is pinned**.
- **Pinned:** within `min_distance_m` of another robot outside the command, both not MOVING. M4's safety monitor holds both members of such a pair, and the latch releases only at 0.45 m separation, which neither can reach. So the robot cannot move during the maneuver.
- **Shape (the A21 lane-scope precedent):**
  - one UNLINKED `temporary_wait` per shielded robot, with the yield's own wait budget (its passers' `duration_sec`);
  - `requested_strategy: "yield"`, so `project_dispatched_legs` reads it as a `wait`;
  - one `grounding=retreat_shield:<id>` tag each (a provenance marker in `DEGRADATION_TAGS`);
  - never a passer, so it is outside the crossing order and the escort.
- **Release:** M4 releases the waits when the yield terminates (`_release_linked_waits`); no new timer.

**Safety note.** A shielded robot is a command member. While the yielder backs up, M4 therefore exempts the yielder–shielded pair (`admitted_partners`, the off-lane-hold precedent). This is acceptable only because the robot is held where the decision snapshot saw it, plus the M2-call drift, a position the retreat sweep already checked. `hard_contact_floor_m` is 0.0 in `safety.yaml`, so nothing else guards that pair.

### 2.3 E16: the discriminating condition

E16's r3 was the diagnosis's false-hold, in a yield that COMPLETED.

- Its intent path crosses the corridor (0.0 m). No corridor margin or intent rule can exclude it without also losing E10 and E13.
- **The discriminator is the pin.** At the decision r3 stood 0.413 m from r2, both STOPPED. GT shows the pair frozen at exactly 0.413 m from 105 to 200 sim-s, through the whole yield.
- `test_e16_r3_would_be_shielded_if_it_were_free_to_move` shows the pin alone decides it: the same scene with r2 MOVING shields r3.
- No special case is involved. The pin rule is the safety monitor's own latch semantics read off the snapshot.
- E16's other bystander, r5, stays outside the margin: 0.57 m against the 0.50 m threshold.

### 2.4 Fixture outcomes (margin 0.05, frozen before the VM)

| Case | Live outcome | Shielded | Required | Live-GT classification of each shielded robot |
|---|---|---|---|---|
| E6 | admitted | r3 (next leg) | — | r3 over-hold (closest 2.4 m) |
| E10 | B, r3 | **r3** | r3 ✓ | necessary (0.04 m) |
| E11 | A (island) | r1, r2 | — | over-hold, both (≥ 1.5 m) |
| E13 | B, r2 | **r2** | r2 ✓ | necessary (0.18 m) |
| E14 | B, r2 | **r2** (intent only), r3 | r2 ✓ via intent | r2 necessary on the live heading line (0.43 m); under the A-fixed axis line its GT is frozen after the live latch (biased "clear", 1.01 m). r3 over-hold (0.89 m) |
| E15 | admitted | r3 | — | over-hold (1.0 m) |
| E16 | admitted | **none** | none ✓ | r3 pinned (crosses at 0.0 m); r5 at 0.57 m |
| E17a | A (island) | none | — | — |
| E17b | B, r2 | **r2** (intent only), r5 | r2 ✓ via intent | r2 necessary (0.43 m); r5 necessary at the parked yielder (0.41 m) |

The classification column uses the A25 counterfactual method:

- the yielder's replayed path (M4's own controllers, at 1.0× and 1.25× time) against each shielded robot's LIVE GT track;
- "necessary" means it comes within 0.45 m during the motion or within 30 s after it;
- the kit is `data/logs/vm_runs/a26_shield/overhold.py`, with `overhold.json` for the axis line and `overhold_heading.json` for the heading line.

Results:

- **Required: 4/4 mechanism-B blockers shielded.** E14 and E17b are shielded only through the intent read (`test_blocker_is_shielded_only_through_the_intent_read`). E16 is not shielded.
- **Over-hold cost on the 9 scenes:** 5 of 10 shield holds are over-holds (E6 r3, E11 r1, E11 r2, E14 r3, E15 r3), against 5 necessary.
  - Two over-holds fall on yields that were admitted anyway (E6, E15). There, a shielded robot sits out the yield's wait budget, released at the yield's terminal: 55 s in E6, 79 s in E15.
  - The shield is deliberately conservative. It reads a straight intent path at the maximum speed and ignores the timing of the crossing.
- **A rejected alternative:** a constant-speed space-time conflict check was tried offline. It was speed-assumption-sensitive (E16 r3 sits at 0.46 m against a 0.45 m bar, and E17b r2 at 0.45 m) and still over-held E6 and E15.

### 2.5 Config

- The new keys are on `GroundingParams`: `retreat_shield` (False), `retreat_shield_margin_m` (0.05) and `retreat_fast_fail` (False). They stay out of every artifact dump in which they are off.
- They are enabled only by the new `config/grounding/s1b_dynamic_shield.yaml` (md5 `ee5fe68f`). It is the pinned `s1b_dynamic.yaml` (535f5281, untouched) plus those three keys, pinned by a test, and selected per run by an overlay's `grounding_params_path`.

---

## 3. The B3 Fresh-latch Fast-fail (A26(ii))

- **M3:** with `retreat_fast_fail`, every dynamic `yield`/`reverse` carries `fresh_latch_fast_fail: true`. It reaches M4 through M5's verbatim parameters passthrough, like `backup_facing_rad`. One grounding file gates both A26 features, and no pinned M4 config moves.
- **M4, pure (`swarm_execution/fresh_latch.py`, `FreshLatchWatch`):**
  - It is fed every `/safety/holds` payload.
  - It is armed when a flagged clearing command starts its backup.
  - It returns a FAILED detail once the clearing robot has been continuously held for 2.0 s by a hold that began after the arm time.
  - Why a hold means a fresh latch: A19 waives a latch the clearing robot started in, so the clearing robot being held at all after its command started means a latch formed during the maneuver.
  - The detail reads `fresh latch fast-fail: <robot> latched during <backup|pull_off> held_for=<s> co_held=<ids>`. `co_held` lists the other robots newly held since arm time; the monitor publishes no pairs.
- **M4, primitives:**
  - `Nav2Adapter.backup` and `sidestep` take `abort_check`, polled on their own 20 Hz tick before the deadline. A non-None detail ends the step FAILED with that detail.
  - The default None never polls, so every existing call is bit-identical.
- **M4, bus:**
  - `CommandBusNode` subscribes to `/safety/holds` lazily, on the first flagged command, so a node that never sees the key never subscribes.
  - It passes the checks to the backup and the pull-off, and disarms at hold start and at every terminal.
- **Expected saving per B event:** the step deadline minus the wall time to the latch minus 2 s. From the A25 traces, the latch fell 59 / 52 / 190 / 116 wall-s into the yields that failed at 211 / 202 / 294 / 214 s (E10 / E13 / E14 / E17b). So B3 would have ended them about 150 / 148 / 102 / 96 s earlier. That is below the ruling's 150-200 s estimate for the two sidestep cases, whose latch came late. It gains no admits by itself.
- **Logging gap (found after deploy):** M4 publishes the status detail but no node logs it. A live B3 firing is therefore inferred: a FAILED backup or pull-off well before that step's deadline, with the yielder under a safety stop. A follow-up should log the detail.

---

## 4. Suite, Merge and Deploy

- **Suite (fresh `0f9d423` worktree vs branch):** 62 failed / 6578 passed / 153 skipped / 3 errors → 62 / 6646 / 153 / 3. The failing ids are identical (the 65 pre-existing ones); +68 tests in `tests/unit/test_a26_retreat_shield.py`. Ruff is clean on the changed files; `nav2_adapter.py` keeps its two pre-existing findings.
- **Commits:**
  - `6da72ae` test;
  - `1b90db7` feat;
  - merged into `feat/v3-integration` as `86f83bc`.
- **Deploy (VM `p7/deploy_p7.sh`):**
  - The pre-images matched the batch-2 runtime (9746f3b). The A25 fix had never been deployed, so this batch is its first live exercise too.
  - The sources were touched, the installed copies and `__pycache__` purged, and `swarm_execution` and `swarm_orchestrator` colcon-rebuilt (rc 0).
  - Checks: SOURCE, LIVE-MOUNT (`/ws`), INSTALLED and PACKAGES SRC==INSTALLED all OK.
  - In-container smoke: the shield file loads as shield True / 0.05 / fast-fail True, and the pinned file as both False.

| File | Layer | md5 |
|---|---|---|
| `reasoning/rag/command_grounder.py` | M3, live mount | 3436f10c |
| `reasoning/rag/maneuver_geometry.py` | M3, live mount | bd78ceea |
| `reasoning/rag/retreat_shield.py` (new) | M3, live mount | 1019f7d4 |
| `config/grounding/s1b_dynamic_shield.yaml` (new) | M3 config, live mount | ee5fe68f |
| `swarm_execution/command_bus_node.py` | M4, colcon | 3d1f394f |
| `swarm_execution/nav2_adapter.py` | M4, colcon | 0d290cfd |
| `swarm_execution/fresh_latch.py` (new) | M4, colcon | 021d63bd |
| `swarm_orchestrator/orchestrator_node.py` | M5, colcon | f149ecff (was 51218d7a) |
| `swarm_orchestrator/reasoning_pipeline.py` | M5, colcon | fbf18d2d |
| `swarm_orchestrator/task_stream.py` | M5, colcon | 6e67c9ae |

These pins did not move: `orchestrator.yaml` 1f656533 (source and installed), `rag.yaml` e18c723c, `s1b_dynamic` 535f5281, `s1_dynamic` 66900e13, `fc_launch.sh` 5a5ee4ac and `reanalysis_suppression` b22d16b9.

---

## 5. Live Batch 3: Pre-registration and Run

- **Rule 15** was appended to the VM NOTES before any live call: `data/logs/vm_runs/batch3/p7/notes_prereg_p7.md`.
- **Condition:** rule 14 verbatim. That is gemini-robotics-er-2-preview, plan channel on, suppression with refusal_no_action and backend_failed arming, churn bound off, Δ 2.5, H 600 and `NAV2_BRINGUP_MODE=sequential`. Two things differ:
  - the A26 runtime tree;
  - the overlay `grounding_params_path` points at `s1b_dynamic_shield.yaml`. That is the only line changed against the p6 overlay procedure, which still byte-reproduces `s1b_orch_seed6.yaml`.
- **Seeds:** 18-21 from `config/s1_seeds.yaml` (1648691287, 1509617270, 447088698, 2107305794). The scenarios were generated and built by the p4 procedure: USDs newer than their yamls, spawns equal to the draws, validate rc 0.
- **MC (echo, upper bound):** EXECUTABLE yield on all four seeds (r2, r4, r4, r1).
- **Budget:** batch cap $0.20 and episode cap min($0.08, remaining). `cost_watch` stops an episode once its estimate plus $0.008 (one call) reaches the cap, and polls every 5 s. An episode starts only if at least $0.04 remains.

| Episode | Stamp | Analyses | est $ | Dispatched yields → admitted | Shield | B3 | Tasks | Churn class | Productive |
|---|---|---|---|---|---|---|---|---|---|
| E18 (seed 18) | 20261011_190708 | 9 | 0.0646 | 2 → **2** (hold-timer ×2) | 1 event: r5, r4, r1, 78.5 sim-s each | 0 (one reverse ran to its deadline: no latch) | 1/25 | intermittent (3 clearing into one group, 0 alt) | 1 |
| E19 (seed 19) | 20261011_200223 | 6 | 0.0405 | 0 | — | **1** (reverse r3, 8.1 s vs 195 s) | 3/25 | clogged | 0 |
| E20 (seed 20) | 20261011_205820 | 7 (10 billed) | 0.0586 | 3 → **3** (clearance, hold-timer, clearance) | 2 events: r5 for 56.5 sim-s; r5, r3, r4 for 28.3 sim-s | 0 | 8/25 | intermittent (3 clearing, 0 alt) | 1 |
| E21 (seed 21) | — | — | — | not run (budget floor) | — | — | — | — | — |

**Per-episode one-liners.**

- **E18:**
  - The first analysis (46.3 sim-s) dispatched the MC-predicted yield, r2 for r3. M3 swept-regrounded it from r3, on a lane:y view.
  - It shielded all three bystanders, was admitted at 84.2 and released by the hold timer at 129.2.
  - A later reverse (r4, r5) let r4 complete. r5 backed into the SW corner and ran to its 195 s deadline with no latch, so B3 was armed but silent.
  - A second yield (r5 for r2, analysed at 215.8) was admitted at 245.8.
  - Five `junction_clear` analyses around and after it were refused ("no feasible yielder"), and one wait was dispatched. Productive 1 (the reverse at 134.3), 1/25 tasks.
- **E19:**
  - The first analysis chose a `reverse` for r3 and r4 (verbatim), not the MC yield.
  - r3 reversed into bystander r1. **B3 failed it 2.1 s after the latch**, 8.1 s after the start, against a 195 s deadline. r4 completed.
  - The r1–r3 latch then stood to the end of the episode. It is mutual and neither robot was commanded again, so the saved ~187 s bought nothing for the scene.
  - Five refused analyses followed: no shared lane, then four "no feasible yielder". Clogged, 0 productive.
- **E20:**
  - The first analysis dispatched the MC-predicted yield, r4 for r2 (verbatim), shielding r5. It was admitted at 75.0 and **released by clearance** at 101.9: productive, with the cluster's progress at 79.3 s.
  - A no-congestion analysis (105.1) and a priority_override (109.5) followed.
  - Next came a yield, r2 for r1 (verbatim), with r5, r3 and r4 shielded. It was admitted at 153.7 and released by the hold timer at 198.7.
  - Then a yield, r1 for r3 (verbatim, no shield). It was admitted at 234.4 and **released by clearance** at 263.4.
  - A wait was dispatched (235.9) and the last analysis was refused (no shared lane). 8/25 tasks, the second-best S1b live episode after E17 (9/25).

---

## 6. What the Three Mechanisms Did Live

### 6.1 Admits (the headline)

| Population | Dispatched live yields | Admitted |
|---|---|---|
| E6-E17 (pre-A25/A26 runtime) | 9 | 3 |
| **Batch 3 (A25 + A26)** | **5** | **5** |
| Pooled E6-E20 | 14 | 8 |

- All five carried the A25 swept-axis keys (`backup_facing_rad`) and the B3 key. None failed in backup or pull-off, and none ran to a deadline.
- **E20 had two clearance releases.** Only E6 had ever been released by clearance before, so "admitted" here sometimes means the passer actually cleared, not only that the hold timer ran out.
- **Caveat: n = 5 on three seeds that were not used before.** The scenes differ from the 9 A25 scenes, so this is not a controlled before/after. In particular, it cannot say how many of the five would have failed without the shield.
- Only one of the 7 shield holds is plausibly necessary: E18 r1, which was heading for node S, the yielder's retreat end. That is the classic mechanism B (§6.2). The other six holds stood 1.4-3.8 m off the corridor when they halted, and are probably over-holds. A held robot has no live counterfactual.

### 6.2 The shield's halt point (safety)

| Command | Shielded | Snapshot → corridor | Halt (dispatch) → corridor | Drift | Min centre distance to the yielder |
|---|---|---|---|---|---|
| E18 `56b599af` | r1 | 0.94 m | **0.25 m** | 0.70 m | **0.23 m** at 64.0 sim-s |
| E18 `56b599af` | r5 / r4 | 1.24 / 1.86 m | 1.42 / 1.61 m | 0.56 / 0.58 m | 1.39 / 1.60 m |
| E20 `f269ab37` | r5 | 2.75 m | 2.34 m | 0.44 m | 2.35 m |
| E20 `c18ade97` | r5 / r3 / r4 | 1.58 / 4.15 / 3.49 m | 1.58 / 3.77 / 3.48 m | 0.01 / 0.47 / 0.01 m | 1.56 / 3.05 / 3.47 m |

- The retreat sweep validates the corridor against **snapshot** positions. The shield stops a robot only when the command lands, after the M2 call: 1.5-4.4 s, 0.3-0.7 m of drift at about 0.16 m/s.
- On the 9 fixtures every halt point was still ≥ 1.0 m off the corridor (`a26_shield/drift.py`). Live, E18's r1 was not.
- Being a command member, its pair with the backing yielder was exempt (`admitted_partners`), and `hard_contact_floor_m` is 0.0. So nothing would have stopped the yielder.
- It passed at 0.23 m centre to centre, about 0.05-0.09 m between bodies. Without the exemption the pair would have latched at 0.45 m, B3 would have failed the yield, and r1 would never have reached S.
- **Recommendation (owner ruling):** either
  - score the shield on the robot's projected halt point (snapshot + v × an M2-latency bound) and re-sweep the retreat against it; or
  - take shield-only members out of the exempt-partner set, so a too-close hold latches and B3 fails the step instead.

### 6.3 B3

- **One firing, on a reverse (E19).** It saved about 187 wall-s, but the mutual latch it ended on persisted (both robots held). This is the predicted "no admit gained" behaviour; the scene stayed clogged.
- **No firing on a yield,** because no yield failed.
- **One deadline failure with B3 armed but no latch (E18 reverse r5, a corner):** B3 covers fresh latches by design, not physical blocks.
- **Still open:** M4 never logs status details. A follow-up should log the FAILED detail (`fresh latch fast-fail: …`) in the command bus.

### 6.4 Plan metrics

- All three shielded commands report `dispatch_matches_plan = False` purely because of the shield waits: each robot's plan leg says `continue` and dispatch holds it on a `wait`. With the shield legs excluded, all three match.
- That costs two vb∧matched headlines (`f269ab37`, `c18ade97`). Batch 3 vb∧matched is 3 raw and **5 with shield legs excluded**.
- Both-clusters naming did not occur in batch 3 (0/22 valid analyses).

---

## 7. Rev 5 Aggregates (All Live Episodes E6-E20)

The script is `data/logs/vm_runs/batch3/aggregate_b3.py`: `aggregate_b2.py` verbatim plus the MC entries for seeds 18-21. It reproduces `agg_b2.json` block-for-block on the 12 prior live bundles. Output: `batch3/agg_b3.json`. The full table is in `docs/reports/2026-10-11-s1b-live-batch.md` §16.

| Aggregate | Rev 5 |
|---|---|
| (a) Attribution | Opportunity is reached in E13, E16, E17, **E18 and E20**, all `intermittent` with 0 alternations, so APPARATUS under the A24 conjunction. These are the A25(iii) **ESCALATION** class: E18 and E20 retried different strategies on the same group. **Pooled: NO LIVELOCK UNDER THE REAL MODEL (5 opportunity, 0 ARCH).** E19 is INDETERMINATE (clogged) |
| (b) Productive | All classified n = 27, **7 nonzero** (S1a A1, E6, E10, E11, E17, **E18, E20**), p95 1. Live 6/15 nonzero, p95 2. **Bar (≥ 8 nonzero) NOT met.** n_more = ceil((8 − 7) / (6/15)) = **3 live episodes** (was 9 at Rev 4). Per-event dispatches-into-group to the productive event: [1, 1, 2, 1, 2, 3, 2, 1], p95 3. Dispatch → credited progress p95 79.3 s |
| (c) First-conflict yield | **3/15 live** (E15, E18, E20), CI 0.043-0.481, against MC 10/15. Batch 3 alone 2/3 against MC 3/3 (E19's model chose reverse). The MC upper bound still holds |
| (d) Both clusters | Named 14/89 valid analyses (14/45 two-cluster scenes); a both-cluster plan dispatched 7/89. Batch 3: 0/22 |
| (e) Wandering vs park | One S1b finisher ever (echo E4); 0/41 occupied-node arrivals had a finisher occupant. Undecided |
| (f) Cost | Per episode: E18 $0.0646, E19 $0.0405, E20 $0.0586. All-live median $0.0335 (range 0.0174-0.0954). Batch 3 $0.1637; all-live total $0.6477 |

**budget_k.** The bar is unmet by one episode, so no triple is derived. The Rev 4 reference-only triple (3, 130 s, 0) stays reference-only. For the record, today's inputs would read:

- budget_k p95 = 3;
- window = max(p95 latency 79.3, the longest inter-dispatch gap in a productive group), rounded up;
- alternation_max = 0.

These are not frozen. The next 3 live episodes at the pooled rate are expected to clear the bar.

---

## 8. VM End State and Pins

- **Processes:** no Isaac, Kit, fc_launch, chain or watch process. `vgu_ros` is up and idle; GPU 0 %, 136 MiB; `data/logs/simulation` is empty.
- **Ownership:** `chown -R ubuntu` done, including an old root-owned `data/logs/fc_run_20261010_180028`; 0 non-ubuntu files remain.
- **Pins verified at close:** the unchanged pins of §4 and the A26 runtime, source equal to installed.
- **NOTES:** the new pin line and the end state are appended to `~/v3_s1b/NOTES.md`. A copy is in `batch3/NOTES_vm_b3.md`.
- **Bundles:** pulled to `data/logs/vm_runs/batch3/` (gitignored).
- **The VM is RUNNING.** Stop it with `gcloud compute instances stop vgu-vgu-thu-base-isaac-workstation-vm --zone asia-southeast1-b --project project-5b0644ea-c6bd-4d13-a4a` when idle.

---

## References

- **Rulings:** prereg-v3 A25 and A26 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Diagnosis:** `docs/reports/2026-10-12-no-admit-diagnosis.md`.
- **Aggregates (Rev 5):** `docs/reports/2026-10-11-s1b-live-batch.md` §16.
- **Code:**
  - `reasoning/rag/retreat_shield.py`;
  - `reasoning/rag/command_grounder.py` (`ground_reasoner_result`, `DEGRADATION_TAGS`);
  - `reasoning/rag/maneuver_geometry.py` (`GroundingParams`);
  - `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/{task_stream,reasoning_pipeline,orchestrator_node}.py`;
  - `ros2_ws/src/swarm_execution/swarm_execution/{fresh_latch,nav2_adapter,command_bus_node}.py`;
  - `config/grounding/s1b_dynamic_shield.yaml`.
- **Tests:** `tests/unit/test_a26_retreat_shield.py`, `tests/unit/data/a26_retreat_shield/intents.json`.
- **Kits** (gitignored):
  - `data/logs/vm_runs/a26_shield/`: `extract_intents.py`, `geo.py`, `spacetime.py` (the rejected alternative), `overhold.py`, `drift.py`, and suite evidence;
  - `data/logs/vm_runs/batch3/`: `p7/` and `p7_vm/` (deploy, gen, overlays, build, chain, cost_watch, pre-registration, logs), `aggregate_b3.py`, `b3_extras.py`, `oneliner.py`, `agg_b3.json`, `extras_b3.json`, `mc_seeds_18_21.jsonl`, and the three bundles.

