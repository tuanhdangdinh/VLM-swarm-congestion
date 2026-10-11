# The A25 No-Admit Yield Defect: Offline Diagnosis and the Swept-Axis Backup Fix

**Prepared:** 2026-10-12

**Revision history:**

- Initial draft: offline diagnosis of the 6 live yields that ran ACTIVE 191-294 s and FAILED without `gate_admit` (prereg-v3 A25(iv)); per-case M4/GT traces; split verdict; Fix A (M3+M4, dynamic mode only) built test-first on the real cases; Fix B evaluated offline and left for a ruling; no VM run.

---

## Summary

**Status: diagnosed, and half fixed. It is not one defect. Two mechanisms share one symptom, and only one is fixed here.**

- **A, geometry mismatch (E11, E17a).** M3 swept the retreat along the snapped lane axis, but M4 backed along the yielder's own heading. Fixed.
- **B, bystander latch (E10, E13, E14, E17b).** A robot outside the command walked into the retreat, and the latch froze both robots until the deadline. Not fixed; it needs a ruling.

Every one of the six failures was the M4 primitive's OS-monotonic safety deadline firing. In four it was the backup's, in two the sidestep's. **Not one reached the hold, and the hold is where `gate_admit` fires.**

| Question | Answer |
|---|---|
| Which timeout fired | The **M4 primitive safety deadlines**, wall-clock `time.monotonic()`. Backup: `max(d/0.1 × 15, 30)` s, so 191-211 s for d = 1.28-1.41 m. Sidestep: `max((π/0.5 + \|L\|/0.1) × 15, 30)` s, so 148.2 s at L = 0.36 and 202.2 s at L = 0.72. Measured durations match within 0.3 s. The two sidestep cases show 214 / 294 s because the backup time comes first (65.7 / 91.6 s). It is not the command timeout, not the Nav2-leg watchdog (Nav2 legs only), and not an M5 expiry |
| Where the yields died | 4 in the **backup**: E10, E11, E13, E17a (one ACTIVE status, robot stalled at 59-93 % of the distance). 2 in the **sidestep's turn-back**: E14, E17b (backup COMPLETED, lateral drive completed, the final turn back to the start yaw frozen). None reached the hold |
| Candidates ruled out | **(c)** `_start_hold` calls `_admit(chain.current)` unconditionally, so no admit means exactly "never reached hold". `passer_reference_at_dispatch` is unset in all 9 yields, including the 3 that completed, so it cannot be the discriminator. **(d)** The passer's motion cannot block the admit. **(e)** No yield used a heading lane; the relevant variant is the snapped lane 18-23° off the heading (mechanism A) |
| Verdict | **Split.** **A** (E11, E17a): code defect, M3/M4 contract. The candidates and gate validate a world-axis retreat while M4 executes a start-heading line; at 18-23° off-axis over 1.3-1.4 m, that misses by 0.42-0.62 m and the yielder pins itself on island W. **B** (E10, E13, E14, E17b): semantics. The retreat sweep checks bystanders only at their snapshot positions. A moving bystander enters the retreat, forms a fresh latch that A19 does not waive, and both robots are held at 40 Hz until the deadline. E14 is B with an A component (its executed retreat landed 0.62 m off M3's) |
| Fix built (A) | M3 states the swept line: `backup_facing_rad` (world facing, opposite to the retreat direction) and `backup_reference_yaw_rad` (the yielder's world yaw in the same snapshot). These go on derived yields under a dynamic footprint view only, and only when the turn is ≤ 45°. M4 holds the backup line turned by `wrap(facing − reference)` from its own odom start yaw (the A11(iii) escort-heading pattern). Declared mode is byte-identical; without the keys M4 is bit-identical |
| Fixture flips | `tests/unit/test_a25_backup_axis.py`, 76 tests over the 9 real yields. Offline re-grounding reproduces every dispatched yield exactly. **Red → green:** the swept facing is stated (9/9). In the M4-controller replay the executed retreat lands on M3's point: landing error 0.42-0.62 m → 0.012-0.028 m for E11, E14 and E17a, and ≤ 0.031 m for all 9. Island contact disappears (E11, E17a). The heading-line replay reproduces the live contact points |
| Suite | Zero delta: 62/6502/153/3 → 62/6578/153/3, identical failing ids. Two byte-identity baselines of dynamic commands now strip exactly the two new keys |
| Fix B (not built) | The snapshot goal-path hold heuristic catches 2/4 blockers (E10 r3, E13 r2). It misses E14 and E17b, whose blocker was dwelling at a node with its next task not in the snapshot. It over-holds in E11, E14 and E16 (E16 is a completed yield). **OWNER RULING NEEDED** (§5) |
| VM | **Not run.** A live echo episode would not reproduce these scenes. The offline replay through M4's own controllers, from the 9 real decision snapshots, is the stronger evidence. Deploying would also move three pinned runtime files (§7) |
| Projected effect | Admitted yields on these 9 scenes: 3 → **5** (E11, E17a, geometric). E14 is race-favourable but not counted. E10, E13 and E17b are unchanged (B). Live first-conflict yield (c) moves by at most +1 (E14, race-dependent). Of the three ESCALATION episodes, none is removed by A alone. **budget_k: Fix A alone does not change the n_more estimate materially; Fix B is the larger lever** (§6) |

PILOT-ONLY, RECORD = 0. $0 API, $0 VM.

---

## 1. Inputs

- **Rule:** prereg-v3 A25(iv) (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Source report:** `docs/reports/2026-10-11-live-batch2.md` §5.3.
- **The 9 live S1b yields ever dispatched** (E6-E17): `churn_wave/s1b_E6_seed6_er2_a3`, `live_batch/s1b_E10_seed10_er2_a1`, `resume/s1b_E11_seed11_er2_b1` and `batch2/s1b_E1{3..7}_*_c1` under `data/logs/vm_runs/` (gitignored).
- **Per bundle:** `m4.log` (command bus, safety monitor, coordination client), `gt/ground_truth.jsonl` (30 Hz poses), and the decision artifacts.
- **Wall-to-sim mapping:** from the coordination client's `sim_t=` lines. E17b's M4 log has no `sim_t` sample after 251.3 sim-s, so its timeline below comes from GT directly.
- **Tree:** `feat/v3-integration` @ `cd35ae1`. Worktree `vgu-vlm-swarm-v3z`, branch `feat/v3-admit-fix`, created fresh with no stash.

---

## 2. Per-case Trace

The columns are:

- **Off-axis:** the yielder's heading against the snapped lane axis M3 swept along (every case is `dynamic_arms:lane:x` or `lane:y`).
- **Phases:** the M4 statuses reached. A plain backup publishes 1 ACTIVE; the pull-off adds a 2nd; the hold adds a 3rd, and `gate_admit` comes with that 3rd.
- **Where it stopped:** GT displacement of the backup, and the sim time it stopped making progress.
- **Blocker:** what held the robot there.

| Case | Yield (cmd) | Off-axis | Phases | Where it stopped (GT) | Blocker | Deadline that fired | Class |
|---|---|---|---|---|---|---|---|
| E10 | r1 → r5 (`63f8d1ce`) | 1.4° | backup only | 1.009 of 1.408 m, stalled from 53.0 sim-s | **Latch r1+r3 at 52.2 sim-s** (0.44 m). r3 was MOVING to Wp (−2.3, 1.35), the node r1 was backing toward. Both held, so frozen for 152 s | backup, 211.2 s (measured 211.4) | **B** |
| E11 | r4 → r5 (`7a47f2f7`) | **22.8°** | backup only | 0.820 of 1.395 m. From about 71 sim-s pinned on island W's SW corner (box distance 0.093 → 0.075 m); heading dragged −0.41 → −1.57 | **Island W** (no latch on r4). Executed line 0.57 m off M3's retreat | backup, 209.2 s (209.5) | **A** |
| E13 | r1 → r4 (`984e3bdf`) | 2.9° | backup only | 0.866 of 1.349 m, stalled from 54.7 sim-s | **Latch r1+r2 at 53.6 sim-s** (0.40 m). r2 was MOVING to Wp, the node r1 was backing toward. Both held | backup, 202.3 s (202.4) | **B** |
| E14 | r1 → r4 (`c5a5e687`) | **22.6°** | backup ✓ (62.9 sim-s, 1.389 m), pull-off: turn-out ✓, drive 0.72 m ✓ (76.0), turn-back | Frozen 0.23 rad short of the start yaw | **Latch r1+r2 at 80.5 sim-s** (0.43 m), r2 heading east. Executed retreat 0.62 m off M3's | sidestep, 202.2 s after the pull-off start (91.6 + 202.5 = 294.1) | **B** (+A) |
| E17a | r3 → r4 (`6745a136`) | **18.4°** | backup only | 1.190 of 1.276 m (93 %), sliding along island W's west face (0.093 m) from about 155 sim-s | **Island W** (no latch). Executed line 0.42 m off M3's retreat | backup, 191.4 s (191.4) | **A** |
| E17b | r1 → r3, r4 (`6d37a549`) | 0.0° | backup ✓ (about 265 sim-s, 1.28 m), pull-off: turn-out ✓, drive 0.36 m ✓ (273.8), turn-back | Frozen about 0.8 rad short of the start yaw | **Latch r1+r2 at about 275 sim-s** (0.40 m), r2 leaving node E toward N. GT ends 298.5 (cost-cap stop) | sidestep, 148.2 s after the pull-off start (65.7 + 148.4 = 214.1) | **B** |
| E6 | r2 → r4 (`83baf2e4`) | 2.9° | backup, pull-off, hold | — | — | `gate_admit` 108.1; released by **clearance** 134.5 | admitted |
| E15 | r2 → r5 (`8066f542`) | 8.5° | backup, pull-off, hold | — | — | `gate_admit` 81.1; released by **hold timer** 126.1 | admitted |
| E16 | r1 → r4 (`eafbb338`) | 2.8° | backup, pull-off, hold | — | — | `gate_admit` 145.5; released by **hold timer** 190.5 | admitted |

**Reading notes.**

- **The latched robot is genuinely frozen.** GT shows zero displacement for 150+ s, because the safety monitor's 40 Hz zero-Twist beats the 20 Hz backup command outright. That is also why the E13 and E14 M4 logs carry about 660-680k `min_distance_violation` lines: `_emergency_stop` logs on every hold tick.
- **The latch cannot release.** It is memoryless and releases only at ≥ 0.45 m, and both members are held, so it lasts until the deadline. This is the A19 boundary working as designed: "a latch formed during the window fires as before".
- **"Admitted means completed" is a tautology.** Once a yield is in its hold, the hold timer guarantees COMPLETED (E15 and E16 were both hold-timer releases). Only E6 was released by clearance. The clean split in the source report says nothing beyond "reached the hold".
- **Off-axis heading separates A from the rest.** The two island cases are 18-23° off their axis. Every yield that completed was ≤ 9° off. E14 is 22.6° off, but its retreat happened to land in open floor.

---

## 3. Mechanism A: the Swept Line and the Executed Line Disagree

- **What M3 validates.** Under a dynamic view the lane axis is snapped (any heading within 30° of an axis). `retreat_axes` then runs the retreat along the world axis, and so do the yield gate's rear room, the footprint box sweep (`retreat_candidates`, grown islands) and the escort.
- **What M4 executes.** `backup_line_hold` (A11(iii) sibling) holds the line through the backup's start pose **along its start heading**.
- **The evidence.** For all 9 dispatched yields, the retreat point equals start + backup × axis + lateral × left(axis) with a residual of 0.000-0.001 m; along −heading it is off by 0.015-0.625 m.
- **The design already knew this.** `derive_dynamic_arms` rule 5 says an ambiguous robot may only pass "since M4 would back it up along its diagonal heading, not the swept axis". The 30° snap tolerance assumed that difference was negligible. Over a 1.3-1.4 m backup it is not.

**Why not fix it in M3 (sweep along the heading instead)?** That would re-lay rule 3's lane, gate, park floor, bands and escort for every derived lane yield. It would also most likely turn E11 and E17a into refusals, because their heading lines run into island W. M3's axis plans were valid: the grown-island sweep clears them by about 0.21 m (E11) and 0.31 m (E17a). So the defect is in execution, and the fix makes M4 execute the plan.

---

## 4. Fix A (Built): the Yield Backs Along the Swept Axis

Branch `feat/v3-admit-fix`, two commits.

| Layer | Change | Scope guard |
|---|---|---|
| M3 `maneuver_geometry.backup_line_facing` (new) | `(facing, reference_yaw)` = (`atan2(−retreat)`, yielder θ in the snapshot), from the same `retreat_axes` the candidates use | Returns None unless `geometry.rear_room_band == "footprint"` (a dynamic view; declared geometry is `"aisle"`) and the turn is ≤ 45°. A larger turn is the `rear_inconsistent` case, and that keeps the legacy line |
| M3 `command_grounder._ground_derived` | The yield gains `backup_facing_rad` / `backup_reference_yaw_rad` (6 dp) | Only under `params.dynamic_scene_arms`, only on derived yields. Reverses, junction recede phases and legacy grounding are untouched |
| M4 `nav2_adapter.backup_line_turn` (new) | `wrap(facing − reference)`. None if either key is missing, non-numeric, non-finite or bool, or if the turn is > 90° | Pure function |
| M4 `nav2_adapter.backup(line_turn_rad=0.0)` | The line runs through the start pose along `start_yaw + line_turn_rad` | The 0.0 default is bit-identical |
| M4 `command_bus_node` | With `backup_line_hold` and a valid turn on a `yield`, passes `line_turn_rad` | No keys: same two-kwarg call as before (existing strict-signature tests unchanged) |

**Frozen surfaces.**

- The safety monitor, its thresholds, the A19 scope and the sidestep are untouched.
- The flags-off goldens and the IB10 dynamic-switch-on-declared-geometry goldens pass unchanged.
- `config/` is not edited, and no pinned config md5 moves.
- **The change does reach S1a.** S1a's dynamic yields share the `dynamic_scene_arms` switch, so they now carry the keys too. In S1a's 1.2 m aisles a 20° drift would hit a wall sooner, so following the axis is the safer direction there.

**Tests** (`tests/unit/test_a25_backup_axis.py`, fixtures `tests/unit/data/a25_no_admit/yields.json`).

- **Fixture fidelity.**
  - The fixtures hold the 9 decisions, stage-2 labels and snapshots. The stage-2 set-of-mark letter is mapped back to its candidate label.
  - `ground_reasoner_result` on the shipped S1b overlay reproduces each dispatched yield's yielder, backup, lateral, retreat point, passer, order and hold. All 9 match.
  - Adding the keys changes nothing else in any of the 9 commands.
- **The defect's geometry is pinned.** Every live retreat lies on a world axis. The −heading landing misses by more than 0.4 m for E11, E14 and E17a.
- **Red → green on the real cases.** Red was run first against stubs: 23 tests failed for the intended reasons.
  - The swept facing is stated; 9/9 flip.
  - **The M4-controller replay.** The actual `Nav2Adapter.backup` and then `sidestep` are integrated on a unicycle at 20 Hz from each live start pose. The 0.14 × 0.18 m chassis is checked by separating axis against the S1b islands and walls.
    - With the keys, all 9 stay clear and land within 0.06 m of M3's retreat. Red were E6, E11, E13, E14, E15, E16 and E17a.
    - Without them, E11 and E17a hit island W at (−1.21, −0.81) and (−1.41, −0.54). The live robots stopped at (−1.37, −0.73) and (−1.39, −0.62).
- **Guards.**
  - The initial turn (up to 23°) never closes on the exempt partner.
  - Keys absent or malformed means legacy behaviour; a reverse ignores the keys.
  - Past 45° (M3) or 90° (M4) the keys are not used.
  - The 0.0 default reproduces the pre-A25 servo output exactly.

**Executed-retreat landing error, heading line → axis line (replay).**

| Case | Turn | Heading line | Axis line |
|---|---|---|---|
| E6 | −2.9° | 0.065 m | 0.017 m |
| E10 | −1.4° | 0.060 m | 0.031 m |
| E11 | +22.8° | **0.571 m, island contact** | 0.012 m |
| E13 | −2.9° | 0.098 m | 0.031 m |
| E14 | +22.6° | **0.625 m** | 0.028 m |
| E15 | +8.5° | 0.252 m | 0.030 m |
| E16 | −2.8° | 0.063 m | 0.031 m |
| E17a | −18.4° | **0.420 m, island contact** | 0.016 m |
| E17b | 0.0° | 0.015 m | 0.015 m |

**Suite.** Run against a fresh `cd35ae1` worktree: 62 failed / 6502 passed / 153 skipped / 3 errors → 62 / 6578 / 153 / 3, with identical failing ids (the 65 pre-existing ones). The change set is the 76 new tests, plus two existing byte-identity baselines of dynamic commands that now strip exactly the two new keys:

- `test_plan_offlane_hold::test_dispatched_command_is_byte_identical_to_the_baseline`, with 7 S1a/S1b cases;
- `test_s1_episode_loop`'s two E1 escort tests.

Ruff is clean on the changed files. `nav2_adapter.py` carries its two pre-existing findings, unchanged.

---

## 5. Mechanism B (Not Fixed): a Bystander Walks into the Retreat

**Mechanism.**

- `generate_retreat_candidates` sweeps the backup and the sidestep against every other robot's **snapshot position** only.
- A bystander moving at about 0.15 m/s covers about 2 m during a 23-28 sim-s maneuver.
- In all four B cases the bystander's route ran through the retreat:
  - **E10, E13:** the retreat ran onto node Wp, the bystander's own goal.
  - **E14:** the retreat lay on r2's route east.
  - **E17b:** the retreat lay on r2's route from E toward N.
- The fresh latch then holds both robots until the deadline.

**Counterfactual check.** The replayed yielder path is run against the live GT of every other robot, with a time scale of 1.0-1.25 to bracket the live realtime factor.

- **The heading line reproduces every live B latch:** E10 r3 at 50-54 sim-s (live 52.2), E13 r2 at 53-55 (53.6), E14 r2 at 78.6 (80.5), and E17b r2 at 274.9 (about 275).
- **E14 and E17b are races.** At scale 1.0 the maneuver ends before the bystander arrives, so the yield would have been admitted. The live sidestep was slower and lost by a few seconds.
- **Under the axis line, E10, E13 and E17b are unchanged.** E14 shows no contact, but r2's GT is frozen after its live latch, which biases that toward "clear". **E14 is therefore not counted as converted.**

**Fix B options, evaluated offline on the 9 snapshots.**

| Option | Catches (of E10, E13, E14, E17b) | Cost |
|---|---|---|
| B1. M3 holds every bystander whose straight path to its snapshot goal passes within 0.45 m of the retreat sweep (a linked `temporary_wait`, the A21 `off_lane` precedent; it becomes a command partner, so it is exempt during the maneuver) | **2/4** (E10 r3, E13 r2). It misses E14 and E17b: r2 was dwelling at a node, and its next task is not in the snapshot | Over-holds in **E11** (r1, r2), **E14** (r3) and **E16** (r3, a yield that COMPLETED). It also adds robots the model did not name, which touches plan-verbatim metrics. Covering dwelling robots needs M5's next-task intent |
| B2. M3 keeps retreats off task nodes | E10, E13 (retreat on Wp) | Yielders sit next to nodes by construction (conflicts form at nodes). Refusal cost unmeasured and probably high |
| B3. M4 fails fast on a mutual bystander latch (both robots held for N s) | 0 admits gained | Reclaims about 150 s per event and shortens the escalation chains. It does not raise the yield rate |

**OWNER RULING NEEDED:**

- Is holding robots the model did not name (B1) admissible as M3 grounding? If so, may M3 read M5's next-task intent so it covers dwelling bystanders?
- Is B3 wanted as a stop-gap?

Conclusion from the table: B1 is worth building only together with M5's next-task intent. Without that intent it covers just 2 of the 4 blockers and over-holds in 3 episodes. It would then be gated to the dynamic footprint view, like Fix A.

---

## 6. Projected Effect

| Quantity | Before | After Fix A (same 9 scenes, offline) | Notes |
|---|---|---|---|
| Dispatched live yields reaching `gate_admit` | 3/9 | **5/9** (+E11, +E17a) | Geometric: the replayed path is clear and no bystander comes within 0.45 m in the counterfactual. E14 is race-favourable, not counted. E10, E13 and E17b remain (B) |
| Live first-conflict yield (c) | 1/12 | ≤ 2/12 | Of the MC-matching first-conflict yields that failed, E13 is B and E14 is race-dependent. E11's yield was not the MC pair. E17a was not a first conflict. **The (c) gap to MC is mostly B plus pair selection** |
| Productive events | 6 (5 nonzero episodes) | +0 to +1 expected | Admitted is not productive: 1 of the 3 admitted yields (E6) was productive. Converting E11's `7a47f2f7` and E17's `6745a136` could add at most one productive event. Neither flips a zero episode to nonzero (E11 and E17 are already nonzero) |
| ESCALATION episodes (E13, E16, E17) | 3 | 3 | E13's chain starts from a B failure. E16 has no failed yield. E17 loses one of its three unproductive yields to A, but keeps E17b (B) |
| budget_k n_more | 9 (18 at batch 2's rate) | about unchanged | Fix A removes two ~200 s freezes per 9 yields. The distribution moves only where an admitted yield is also productive. **B is the lever for budget_k**: four of the six failures, including both MC-matching first-conflict yields |

These are offline projections on the 9 live scenes, not a measured rate.

---

## 7. Deployment Note and Open Items

- **Deploy before any live use** (VM harness traps apply).
  - Runtime files that change: `reasoning/rag/command_grounder.py` and `reasoning/rag/maneuver_geometry.py` (read through the `/ws` mount), plus `swarm_execution/nav2_adapter.py` and `swarm_execution/command_bus_node.py` (colcon-installed: rebuild `swarm_execution`, then md5-verify source and installed).
  - The new keys reach M4 by passthrough: M5 encodes each action's `parameters` verbatim (`swarm_orchestrator/reasoning_pipeline.py:841`, `json.dumps(action.get("parameters", {}), sort_keys=True)`), the same path that carried the live escort-heading keys. There is no whitelist in between.
  - The A23 pins in VM NOTES (`orchestrator_node.py`, `reanalysis_suppression.py`, `fc_launch.sh`, the configs) do not move. The new runtime md5s must be recorded as a new pin line.
- **Reverses still back along their own heading.** The dynamic-mode `reverse` path is unchanged. If a reverse ever shows the same island pinning, it is the same contract gap.
- **A sidestep turn-back frozen by a bystander latch** (E14, E17b) has already achieved its lateral offset, and only the heading restore remains. This was deliberately not short-circuited into the hold. Doing so would flip the yields to admitted+COMPLETED through the hold timer without proving anything about resolution.
- **The `min_distance_violation` log volume** (40 Hz per held robot, about 680k lines per episode) is a logging cost only. It was left as is.

---

## References

- **Spec:** prereg-v3 A25 (`feat/v3-design`, `docs/superpowers/specs/2026-10-06-prereg-v3-design.md`).
- **Source report:** `docs/reports/2026-10-11-live-batch2.md` §5.3.
- **Code:**
  - `reasoning/rag/maneuver_geometry.py` (`backup_line_facing`, `retreat_axes`);
  - `reasoning/rag/command_grounder.py` (`_ground_derived`);
  - `ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py` (`backup_line_turn`, `backup`, `sidestep`);
  - `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`;
  - `ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` and `safety.py` (latch semantics, unchanged).
- **Tests:** `tests/unit/test_a25_backup_axis.py`, `tests/unit/data/a25_no_admit/yields.json`.
- **Bundles** (gitignored): `data/logs/vm_runs/{churn_wave,live_batch,resume,batch2}/`.
- **Analysis kit** (gitignored): `data/logs/vm_runs/a25_no_admit/`.
  - `trace.py` / `trace.jsonl`: per-case phases, deadlines and GT displacement. Its E17b row has a known sim-window bug (no M4 `sim_t` after 251.3); §2 uses the GT-derived E17b timeline instead.
  - `deep.py`: per-case time series.
  - `counterfactual.py`: the §5 latch replay.
  - `extract_fixture.py`: builds the test fixture.
  - `reground.py`: the fidelity check.
  - `base.txt` / `new.txt` / `*_ids.txt`: suite evidence.
