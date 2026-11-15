# Safety-Mechanism Scripted Tests: Registration

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft (registered before the VM starts): purpose, forcing case from the offline proof, takes, pass/fail criteria, caps and stop rules.

---

## 1. Purpose and Label

- **SAFETY TEST, not a demo, not an experiment.** Every decision in these takes is SCRIPTED (mock backend, scripted file). The decisions are chosen deliberately to force a situation. They must never be presented as demo footage, as VLM behaviour, or as experiment evidence, and they are never pooled.
- Goal: validate live, n = 1 per mechanism, three default-off safety mechanisms:
  - the M3 reverse obstacle guard (`grounding.reverse_obstacle_guard`, `fix/escort-obstacle-guard`);
  - the M4 stall abort (`safety.stall_abort.enabled`, `fix/m4-stall-abort`);
  - the M3 escort obstacle guard (`grounding.escort_obstacle_guard`): see section 4, no take.
- Ground-truth contact logging (`feat/gt-contact-logging`) is on in every take. It is a measurement, not a mechanism.
- Owner approval (2026-11-15) covers:
  - scripted forcing decisions;
  - contact logging in every take;
  - exactly ONE new safety mechanism on per take;
  - the stall abort keeping the existing Nav2 failure path.

## 2. Tree, Kit, Configuration

- **Branch** `test/safety-mechanisms-scripted` (worktree v7s), based on `demo/validation-guard-contacts` (`a412949`: campaign code + escort guard + contact logging, what `m5V_t01_a1` ran). Merged into it:
  - `fix/escort-obstacle-guard` tip `92158d3` (reverse extension): merge `527707a`; the only conflict was `docs/implementation_notes.md`, kept both entries;
  - `fix/m4-stall-abort` tip `1016e0b`: merge `af5a9df`, no conflict.
  - Every runtime file equals its branch tip byte for byte, except `orchestrator_node.py`, which carries both startup-line fields.
- **Committed test inputs** (`99edbf3`):
  - `config/mock_decisions/sft_reverse_r5_r3_r1_once.json` (md5 `f0fa1264`): [reverse robot_5, robot_3, robot_1; then `none`].
  - `config/grounding/sft_s1b_reverse_guard.yaml` (`80048c83`): the pinned `s1b_dynamic_shield_escort.yaml` (`40968886`) plus one line, `reverse_obstacle_guard: true`.
- **Kit** `demo_campaign/sft/` on v7j (gitignored). It is assembled from `common/` + `sft/spec/`.
  - VM list `kit_md5_dmc.txt` `bc9290f9`, all files `7b25566a`.
  - Runtime delta `runtime_delta_sft/`: `DELTA_ID d49170f2`, 21 files. These are v7s HEAD's runtime files vs the VM pin `68e67b5`, including the stall abort's `swarm_execution` files and `package.xml`.
  - Pre-registered verdict `verdict_sft.py` md5 `21151463`; condition gate `cond_dmc.py` `fbb04498`.
- **Scene:** as `m5` / `m5v`: five robots, seed position 21 (2107305794), scenario yaml `61fd6faf` (USD rebuilt from it, unchanged), overlay `09bc16e6`, 0.20 m floor + scoped exemption.
- **Session:** ONE VM session with two takes, back to back:

| Take | Arm | New key ON | Off | Overlay | Installed M4 safety.yaml |
|---|---|---|---|---|---|
| 1 | R | `reverse_obstacle_guard` (grounding file above) | escort guard (absent), stall abort (absent) | `take_R.yaml` `1e1e65f4` = base + the grounding_params_path line | merged `65fb84a3` |
| 2 | S | `stall_abort.enabled` (rearm before the take, swarm_execution rebuilt) | both grounding guards (pinned grounding file) | `take_S.yaml` = base `09bc16e6` | `2ffc80c7` = `65fb84a3` + the fragment's block |

- **Arm check, per take**, from the deployed loaders before launch:
  - exactly one new key true, the others false or absent;
  - md5s of the contact files, the scripted file, the grounding file and the installed safety file.
- **Condition gate, per take**, from the bundle:
  - M4 `Command bus started.` line, exactly: R has no suffix, S has the `stall_abort=True ...` suffix;
  - M5 `grounding mode=` line, exactly: R ends `reverse_obstacle_guard=True`, S ends `stage2_retreat_selection=True`;
  - every artifact's params and backend `mock`, zero tokens;
  - the first artifact is the scripted reverse;
  - GT contact fields.
- **Not changed:** latch, exemptions, floor, B3 and the deadlines. No scenario or USD edit.
- **Added observers:**
  - a passive observer subscribes to `/coordination/status`, `/safety/holds` and `/robot_5/cmd_vel`, because M4 never logs the status detail;
  - Isaac is stopped through its own stop flag at GT sim 100 s (R) and 130 s (S);
  - no recording.
- **`pxr` builder-parity test:** runs once in the deploy step, inside a started Kit app (`src/pxr_kit_pytest.py`). It is non-fatal and time-boxed to 300 s; pytest is installed via `pip --target ~/dmc_sft/pytest_target`, which the restore removes.

## 3. Offline Proof (Phase 0): the Forcing Case

- **Evidence:** the three recorded seed-21 runs (v3 `batch4/s1b_E21_seed21_er2_e1`, v7j `m5D_t01_a1`, `m5V_t01_a1`). The first analysis fires at sim 42.2 / 44.5 / 38.7 s, when robot_1 and robot_4 jam at the SW, before any decision.
- **robot_5 at the first trigger:** snapshot (-2.068, 1.392, 0.149) / (-2.011, 1.384, 0.050) / (-2.051, 1.350, -0.118). It has just left its spawn heading east, so a reverse backs it west.
- **Grounded with the merged tree's real parser and real M5 loader on all three snapshots:**
  - R file: three 8 s waits, tag `reverse=infeasible:reverse_hits_obstacle:robot_5:obstacle_3:{0.295, 0.349, 0.312}`. No other leg is blocked. M5 does not withhold it.
  - S file: three 1.3 m reverses (`backup_line_hold`), no refusal.
  - The scripted robot order matters: robot_5 and robot_1 as the first two fail the same-side check before the guard is reached.
- **Margin (reverse guard):** refused for every 1 Hz M1 snapshot from 34 s until robot_5 passes x = -1.15 (m5V 44.7 s, 6 s after its trigger; in m5D robot_5 stops at -1.73). Arithmetically it holds for x ≤ -1.06 and |θ| up to about 76°. The recorded x spread at the trigger is -2.07 to -2.01, which leaves ≥ 0.94 m of margin.
- **Stall-abort prediction (URDF footprint vs the authored boxes, v7m `contact_geometry`):**
  - robot_5 backs into `rack/NW_west` (face x = -2.50) after 0.326 / 0.386 / 0.342 m.
  - Over a grid x0 ∈ [-2.31, -1.2], y0 ∈ [1.30, 1.42], θ ∈ [-0.3, 0.3] every leg contacts within 1.3 m; contact is lost only from x0 ≈ -1.1.
  - Mock dispatch latency is about 0.3 wall-s (convoy Arm C). Expected contact is about 3.5-4.5 sim-s after hand-over.
  - Expected abort 2.3-3.0 sim-s after contact (replay; analogue E7 `c7aeaac1` robot_4 at `rack/NW_west`: 2.3 s).
  - Expected reason `stall_abort: commanded 0.100 m/s for 3.0 s, measured <0.075 m ...`, log `stall abort robot=robot_5 ... primitive=backup ... reason=stall`.
  - Latch: at the contact robot_5 is ≥ 2 m from every robot (min latch 0.45 m), so it is not held.
- **Clear legs in the same command:**
  - robot_1 (min footprint gap 0.21-0.31 m to `rack/SW_west` over the leg). Precedent: in `m5V` `b07a700f` (sim 56.9) the same robot_1 reverse at the same jam, robot_4 left on its base mission, ended COMPLETED.
  - robot_3 (min gap 0.19-0.26 m to `rack/SE_east`). Risk noted: robot_2 may follow robot_3 and re-latch it. That is not a criterion, so its completion is only reported.
- **Escort guard:** a scripted yield robot_2→robot_3 yields an `escort_hits_obstacle:robot_3:obstacle_2` refusal on the m5D first-trigger snapshot only. On E21 and m5V, robot_2 has no executable retreat at the trigger (robot_3 not yet settled). That is 1 of 3, not reproducible, so there is **no escort take**: the escort guard stays "armed once live, blocks offline only".

## 4. Pass/Fail Criteria (fixed before the VM starts; `verdict_sft.py` 21151463)

**Reverse-guard take (R).** A0 is the earliest artifact whose decision is the scripted reverse. PASS iff all of:

- **R1:** A0's command carries `reverse=infeasible:reverse_hits_obstacle:robot_5:obstacle_3:<m>`, and its actions are exactly `temporary_wait` for robot_5, robot_3, robot_1 (8.0 s, `requested_strategy: reverse`, that reason).
- **R2:** M5 dispatched it to all three, M4 published COMPLETED for each, and there was no reverse hand-over and no `stall abort` under the command.
- **R3 (GT):** over [A0 − offset, +10 s] no robot moved more than 0.02 m along its own backing direction.
- **R4:** contact logging lists no robot–static contact of these robots in that window.

**Stall-abort take (S).** PASS iff all of:

- **S1:** `stall abort robot=robot_5 command=<A0> primitive=backup ... reason=stall`, at most 5.0 sim-s after the first logged GT contact of robot_5 (offset GT→ROS estimated per bundle).
- **S2:** `status published ... robot=robot_5 status=FAILED` after that line.
- **S3:** the observer saw the FAILED status with a detail starting `stall_abort:`.
- **S4:** a zero twist on `/robot_5/cmd_vel` within 0.5 s, and no backup-like twist (v ≤ -0.05) in the following 5 s.
- **S5:** contact logging recorded the contact. Also, for this first live contact event of the logger, the logged rows must equal the offline recompute (`scripts/recompute_gt_contacts.py`) row by row; checked after the pull.
- **S6:** robot_1's reverse COMPLETED with no abort. robot_3 has no abort unless GT shows a contact within 3.5 s before it.

What robot_5 does after the abort (the existing Nav2 failure path) is an observation, not a criterion.

**INCONCLUSIVE (not FAIL), when the forced situation did not arise:**

- R: no scripted artifact, or robot_5's snapshot outside the envelope (x > -1.07 or |θ| > 0.6).
- S: robot_5 got no 1.3 m reverse, its snapshot x > -1.20, or no GT contact after hand-over with no abort.
- S: robot_5 latch-held at the contact (the known blind spot).

Each INCONCLUSIVE report states what would be needed. An INCONCLUSIVE take is not re-run in the hope that the situation arises.

## 5. Caps and Stop Rules

- **Wall:** ≤ 7200 s for the whole session (one VM start). **API:** $0 (mock backend, no probe; ≤ $0.20 cap).
  - Booked under ledger key `sft` (caps copy: `wall_sec_sft` 7200, `usd_sft` 0.20, 2 valid takes, 3 bring-up aborts).
  - These sit inside the campaign totals (used 25,667 s of 43,200 s, $2.86 of $10), which are unchanged.
  - The convoy rerun `cvy` (≤ 7200 s) uses the VM first; this session starts only when the VM is TERMINATED and no `cvy` driver is alive.
- **The kit stops the chain on a harness failure:** arm check, condition gate, rearm, pins, restore. It never retries them.
- **Bring-up aborts** are retried by the kit (same take, budget 3).
- **A verdict FAIL or INCONCLUSIVE never stops the next take**, the restore or the stop.
- **On a harness failure,** the evidence is inspected and the cause stated, with at most one dry-tested kit fix and one re-run of the affected take within the wall cap.
- **Every path ends** with the restore to the pin (added files and bytecode removed) and the VM verified TERMINATED.
- **Never:** weaken a safety, grounding or verification check; edit ground truth or a pulled bundle; use `rsync --delete`; create a VM or change zone.
