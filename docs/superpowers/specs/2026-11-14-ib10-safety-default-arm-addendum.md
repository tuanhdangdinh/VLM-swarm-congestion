# IB10 Safety Smoke and Grounder-Default Arm: Addendum (Exploratory)

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: registration of a key-on safety smoke plus a 9-episode interleaved Arm C / Arm A follow-up on IB10, written before any episode ran.
- Rev 2: before any episode ran, after review:
  - Arm A failed-call rule.
  - Arm C re-trigger path verified in code.
  - Inert not-honoured lines.
  - `mock_backend.py` moved from a hard pin to an Arm C precondition.
  - Precedents and changes from 2026-11-13 stated.
- Amendment (2026-11-14): section 13 added after the results were seen. It registers a re-run of the invalid slot e02 (Arm C) before that re-run. Sections 1-12 are unchanged.

---

## 1. Question and Owner Instruction

The owner's instruction (2026-11-14), verbatim:

> "Run the intersection safety smoke with the fix enabled and the 0.20 m floor armed. If it passes, run the Grounder-default-only arm under the same safety settings."

A later update from the owner (2026-11-14) added: "add the four VLM-on episodes interleaved".

The run asks two questions:

1. **Smoke.** Does the IB10 Layer 2 pipeline still run cleanly when the exemption-scope fix is on (`safety.scoped_clearing_exemption: true`) and the 0.20 m floor is armed?
2. **Arm C against Arm A.** Under the same runtime and safety settings, does the four-way jam clear the same way when no VLM is called? In Arm C the strategy and robot set come from a script and the plan is M3's default.

This addendum extends `docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md`. That spec is on branch `feat/ib10-live-resolution`, registered at `50704c2`; its results report is `docs/reports/2026-11-13-ib10-live-resolution-results.md`, also on that branch. The 2026-11-13 definitions apply unless this addendum states otherwise: scene, seed label, Nav2 bring-up, overlay, frozen outcomes, exclusions and attempt rules.

This run is exploratory. It is never pooled with prereg-v3, and never pooled with the 2026-11-13 run.

---

## 2. Runtime

| Item | Value |
|---|---|
| Base | The v3 pin on the VM (git `68e67b5`), as on 2026-11-13. |
| Code delta | Two files from `fix/safety-exemption-scope`; the branch tip is `8933863`, and the code is unchanged since `2553631`. See the next table. They are deployed into the source tree, built once with colcon, and verified at the colcon-installed path, which is what the nodes import. |
| Safety config | swarm_execution `config/safety.yaml` = the floor file `config/safety/safety_floor020.yaml` (`c41913f0`, `hard_contact_floor_m: 0.20`) with three keys appended from `config/safety/scoped_clearing_exemption.fragment.yaml`: `scoped_clearing_exemption: true`, `waiver_closing_tolerance_m: 0.05` and `waiver_closing_readings: 3`. Every other key is byte-identical. Merged md5 `65fb84a396c3d61a4e4179cd2360897b`. |
| Arm C script | `config/mock_decisions/intersection_junction_clear_m3_default_once.json` (`6c670a6e`). It is tracked at `68e67b5` and is not edited. |
| Excluded | The remedies branch `feat/v4-refusal-feedback` is not an ancestor of the deployed tree. The kit's preflight asserts that `git diff --name-only 68e67b5..HEAD -- ros2_ws reasoning config` is exactly the two code files plus the fragment. |
| Restore | Every invocation ends at the v3 pin. The 68e67b5 sources are put back with plain `cp` + `touch`, both packages are purged and rebuilt, and the installed-package md5 list must equal the pre-run snapshot. `PINS_V3 OK` is required. |

Deployed runtime files:

| File | 68e67b5 md5 | Deployed md5 |
|---|---|---|
| `ros2_ws/src/swarm_execution/swarm_execution/safety.py` | `c6c9cbaeb9cb816dd2ba759c2464afb4` | `3011d9a735e790f56f6c46d98c76f1d9` |
| `ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` | `7b45075fcb940e3e3b57154b3b727958` | `c2cad302be27cf1b638fbeebf295ae7d` |
| `ros2_ws/src/swarm_execution/config/safety.yaml` | `598396622ca50baddc3e19b4608fa3e3` | `65fb84a396c3d61a4e4179cd2360897b` (merged) |

The kit is `data/logs/vm_runs/ib10_safety/kit/`, which is gitignored. Its VM file list md5 is in `kit_md5_ibs.txt`, and the md5 of every kit file is in `kit_md5_all_ibs.txt`.

---

## 3. Design

| Item | Value |
|---|---|
| Arm A | Layer 2 on, live `gemini-robotics-er-2-preview` (`BACKEND=gemini`), as on 2026-11-13. A Gemini probe runs before every Arm A episode, and the run stops on HTTP 429 or 402 or on any other probe error. |
| Arm C | "Grounder default only". Layer 2 trigger, M3 grounding and phased M4 dispatch are on, and no VLM is called. M5's backend is the existing scripted `MockBackend` replaying the Arm C script (section 5). |
| Shared | One overlay for both arms: `ib10s_l2on.yaml`, byte-identical to the 2026-11-13 Arm A overlay `0196f1e8`. Both arms run the same runtime and safety settings (key on, 0.20 m floor). They differ only in the backend fc_launch starts M5 with. |
| Order | Fixed in advance: e01 A (the smoke), then e02 C, e03 A, e04 C, e05 A, e06 C, e07 A, e08 C, e09 A, e10 C. |
| n | Arm C 5 episodes; Arm A 4 follow-up episodes plus the smoke. |
| Labels | `ib10S_eNN_armX_aK`. The VM directory is `~/ib10s`, so nothing can collide with the 2026-11-13 `ib10L_*` bundles or with `~/ib10/attempts.tsv`. |
| Episode table | `kit/episodes_ibs.txt`, one line of `NN:ARM` tokens. The first token is the smoke. |

**Smoke counting rule.** This is the 2026-11-13 rule. The smoke episode counts as Arm A episode 1 only if two conditions hold:

- its harness gates pass (`attempts.tsv` records it `ran`);
- the owner accepts it by writing `SMOKE_ACCEPTED`.

Otherwise it is scored and reported as excluded, with its outcome. A harness-failed smoke may be re-run under a new attempt label. Excluded attempts are always reported. With the smoke counted, Arm A has 5 counted episodes.

---

## 4. Smoke Pass Criteria

`smoke_check_ibs.py` prints `SMOKE_CHECK PASS` only if all four of these hold:

1. **Harness gates OK.**
   - `attempts.tsv` records the bundle as `ran`.
   - `GATE OK` and `RESTORE OK` are present.
   - Every Arm A check of `cond_ibs.py` passes (section 6). This includes M4's startup line, which must end in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`.
2. **Floor stops.** 0 hard-contact-floor stops (M4 `hard_contact_floor_m=0.2 pairs=` lines).
3. **GT contact.** 0 GT frames in which any robot pair is closer than 0.18 m, counted over all frames.
4. **Key-on stalls.** No command stalled to its deadline by a key-on hold. A key-on stall is defined below.

**Definition: deadline-ended command.** A command is deadline-ended if any of these appears:

- M4 `crossing_chain gate_release ... reason=hold_timer`: a yield hold ended by its timer instead of by its passer clearing;
- M4 `nav2 leg watchdog fired`;
- M5 `command <id> resolved status=timed_out|failed`. The bus logs no failure detail, so every such resolution counts, including a backup or side-step timing out.

**Definition: key-on stall.** A key-on stall is a deadline-ended command that shares any of the following with a key-on-only M4 line:

- its command id;
- its decision request (the 32-hex prefix);
- a robot it addressed.

The key-on-only lines are:

- `plan continue partners not honoured`
- `rejected leg not a member`
- `latch waiver revoked ... reason=closing`

The test is conservative. A FAIL means "inspect", not "proven caused by the key".

A `plan continue partners not honoured` line is **inert** when every named partner is itself a member of the same command, taken from that command's status lines. An inert line is counted separately and is never a hold signal, because the partner stays exempt as a member.

In IB10's four-robot `junction_clear` phases every involved robot is a member, and the plan has no `continue` leg. So the line is expected only for degenerate plans, such as e09's two-robot one. The parser has been tested only on synthetic lines built from the node's own f-strings. No live key-on log exists yet.

The attribution rests on the fix report (`docs/reports/2026-11-14-safety-exemption-fix.md`, "Behaviour"). The key changes nothing for a command that has no unhonoured partner and no rejected leg, and each of those cases logs one of the lines above.

**Informational lines.** These are printed but are not criteria:

- third-robot waivers captured: `latch waiver armed` partners that are unhonoured partners or rejected-leg robots of the same command;
- the count of `latch waiver revoked ... reason=closing` lines;
- not-honoured and rejected-leg counts;
- deadline-ended commands without key attribution;
- frozen `resolved`, arrivals and attribution.

**If the smoke does not resolve.** The check states whether any key-on hold signal or revocation occurred.

**The follow-up is never automatic.** `run_ibs.sh follow` refuses unless both of these hold:

- `SMOKE_ACCEPTED` exists. Only the owner writes it.
- `SMOKE_CHECK.txt` says PASS.

---

## 5. Arm C Mechanism

Arm C uses existing code and config only. No runtime change was needed.

The mechanism is a chain of five steps:

1. **Driver.** `ep_run_ibs.sh` starts `scripts/vm/fc_launch.sh` with `MOCK_DECISION_FILE=config/mock_decisions/intersection_junction_clear_m3_default_once.json`. The path is repo-relative and resolves under `/ws` inside the container.
2. **fc_launch.**
   - Lines 258-262: a set `MOCK_DECISION_FILE` forces `BACKEND_ID=mock`.
   - Lines 325-336: it passes a repo-relative path through unchanged.
   - Lines 910-912: it exports `VGU_MOCK_DECISION_FILE` to M5.
3. **Backend factory.**
   - `reasoning/vlm/backend_factory.py:326-337`: for `backend_id == "mock"`, `build_backend` reads `VGU_MOCK_DECISION_FILE`.
   - `_load_mock_script` (lines 201-211) turns a JSON array into a `MockBackend` response sequence.
   - `build_retreat_choice_backend` (lines 276-281) gives the mock no stage-2 backend unless `VGU_MOCK_RETREAT_CHOICE_FILE` is set, and the kit never sets it.
4. **Mock backend.** `reasoning/vlm/mock_backend.py:43-45` replays the entries in order and holds the last entry once the sequence is exhausted. It makes no network call.
5. **M3 default plan.** M3 grounds the `junction_clear` decision with `ground_junction_clear_phases`, which derives the plan from chi ranking (`reasoning/rag/command_grounder.py:2656-2791`). With no `proposed_plan`, plan verification returns `provenance="m3_default"` and `rejection_reason="plan absent"` (`command_grounder.py:4943-4948`). That is the attribution of the excluded 2026-11-13 bundle `ib10L_e01_armA_a1`.

**Re-trigger after the skipped first analysis.** Verified in code at this runtime.

- The `none` answer takes M5's `COOLDOWN` branch (`orchestrator_node.py:1386-1390`, log `no dispatch stage=vlm`), which starts a `cooldown_sec` cooldown on the analysed robots. The overlay sets it to 15 s, measured on the monotonic wall clock.
- The scene-unchanged re-analysis suppression is off on IB10. Its defaults are `enabled: False` and `applies_to: task_stream_only` (`models.py`), the overlay does not set it, and IB10 has no task stream. None of the 2026-11-13 `m5.log` files has a suppression line.
- So a persisting jam is analysed again after one cooldown plus the stall detector's own timing. The second entry, `junction_clear`, is then dispatched.
- At the 2026-11-13 real-time factor (about 0.19), 15 wall-s is about 3 sim-s. The re-trigger delay at this runtime is inferred from the code, not measured.
- If the second analysis never came, `c_dispatched` would fail and stop the chain. Nothing is dispatched silently.

**M5 still loads `/ws/.env` in Arm C.** fc_launch always sources `/ws/.env` (`M5_INNER`). The key is therefore present in M5's environment, but no Gemini backend is ever built, because `build_backend("mock")` returns before any provider branch. Zero tokens and zero `served_model` per artifact are gated (section 6).

**The script** is tracked at `68e67b5`. Its three entries are:

1. `none`, which skips the first analysis;
2. `junction_clear`, type `bottleneck`, naming `robot_1` to `robot_4`, with no `proposed_plan`, no `crossing_order` and no `yield_robot`;
3. `none`, which is then held for every later analysis.

Precedents, all on code older than 68e67b5:

- **2026-10-02 composite smoke.** This exact file produced `m3_default` / "plan absent" on run A (`docs/reports/2026-10-02-ib10-composite-smoke.md`). That run did not resolve: before the release-lane remedy, the held `none` answered the post-composite secondary conflict.
- **Closure wave, 2026-10-07.** The mock runs used the same three-entry pattern with a `vlm_verbatim` plan. R was 2 runs on `intersection_bottleneck`; P was 3 runs on `intersection_bottleneck_r3lead_probe`. All 5 resolved under the remedy, and in R1 the second analysis followed the skipped first one 3.1 sim-s later.
- **Convoy B3 references.** These are a scripted oracle mock (`convoy_counterflow_oracle_order_once`) run through the same `MOCK_DECISION_FILE` path (`docs/reports/2026-10-06-layer2off-pilot.md`).

**What `ib10L_e01_armA_a1` received.** Verified from its decision artifact:

- strategy `junction_clear`, `involved_robots` all four, `proposed_plan: null`;
- `crossing_order` `[robot_1, robot_2, robot_3, robot_4]`, type `deadlock`, `yield_robot: null`, `stage2: null`.

**Offline check (`kit/reground_c.py`).** The script's `junction_clear` entry was re-grounded on the recorded first-dispatch snapshot of five 2026-11-13 Arm A episodes: a1, a2, e03, e05 and e07. In each case it produced the recorded `junction_phases`: the same recede order, actions and parameters, apart from free-text `reason`. The only difference is one degradation tag, `order=discarded_yield_axis`. It is absent for the script because the script gives no `crossing_order`, and `_as_yield_decision` clears the order anyway.

This includes a2, e03, e05 and e07, whose model plans were labelled `repaired`. On these snapshots the commands the VLM-on arm dispatched first were the same as M3's default plan.

**Alternative definitions considered:**

| Alternative | What the existing backends can express | Consequence |
|---|---|---|
| **Chosen**: the tracked `[none, junction_clear ×4 no plan, none]` | Yes. A tracked file; no file is added to the VM unless it is absent. | The first trigger is answered `none`, so the first dispatch lands one cooldown later: about 3 sim-s, inferred above. Every later trigger is answered `none`, so Arm C can never re-dispatch after a failed plan, unlike 2026-11-13 e09. In 2026-11-13, only a2 and e03 had an analysis after the plan, and ER-2 answered `none` in both. |
| `[junction_clear, none]` (2 entries, kit file) | Yes, as a `MockBackend` sequence. The file would have to live under the VM repo. | First dispatch at the first trigger, like Arm A. Needs a new untracked file on the VM, which must be installed and then removed. Not chosen. |
| A single `junction_clear` object, answered every time | Yes (`response_text`). | Every later trigger dispatches a fresh four-robot plan. That includes the single-robot re-trigger after the release phase, seen at about 128-132 sim-s in 2026-11-13 a2 and e03, where ER-2 answered `none`. This would interrupt arrivals; Arm A never showed that behaviour. Not chosen. |
| The a1 decision verbatim (`crossing_order`, type `deadlock`) | Yes, as a scripted object. | Phases are identical to the chosen script apart from the `order=discarded_yield_axis` tag. No gain. |
| Echo mock with `MOCK_ECHO_STRATEGY=junction_clear` | Yes (`EchoMockBackend`). | It names the closest engaged latch pair (prereg-v3 A21), so it gives a two-robot `junction_clear`, like e09's degenerate plan, not all four robots. It is also apparatus-only by A12(i). Rejected. |
| Default `MockBackend` (no file): the 2026-10-06 `layer2off_pilot` mechanism | Yes. | It always answers no congestion, so nothing is dispatched. That is Layer 2 off in effect. Rejected. |
| `reasoning_enabled: false` overlay: the 2026-11-13 Arm B | Yes. | No trigger and no M3 at all. Not a grounder arm. Rejected. |
| Echo mock with a `junction_clear` seed: the S1b pilot apparatus | Yes. | Same as the echo row above: the robot set comes from the echo's pair rule, not from a fixed script. Rejected. |

---

## 6. Condition Gates

`cond_ibs.py` runs after every episode. It evaluates every check and prints one `CHECK PASS|FAIL` line per check, then one `COND` line. Any failure stops the chain with `harness_fail:condition`.

**Both arms:**

- `CONDITION.txt` carries `tag=ib10_safety`, `record=0`, `confirmatory=0` and the arm;
- `ARM_CHECK.txt` exists;
- M4's startup line ends in the floor, key and threshold tail;
- the hand-off race guard line is present;
- an M5 session line is present;
- there is no Layer-2-off status line;
- every `junction_clear` release phase carries a pull-off of ±0.33 m.

**Arm A.** These checks are non-vacuous, because the 2026-11-13 gate passed an empty model set:

- `CONDITION.txt` says `backend=gemini`, with no mock file;
- every artifact's `diagnostics.backend_id` and `reasoner_config_effective.backend_id` is `gemini`;
- every artifact that carries a decision or names any served model has `diagnostics.served_model` equal to `gemini-robotics-er-2-preview`, read from `served_model`, never from `backend_id`;
- an artifact of a failed call (`decision` null, no served model) is allowed, because a transient provider error is data, not a harness failure. None of the 38 recorded Gemini artifacts (tranche 1 and 2026-11-13) is such a case, so this path is tested only on a synthetic fixture;
- no artifact has a `mock_mode`;
- the chain logged `probe before <label>: ... rc=0`.

**Arm C:**

- artifacts > 0;
- dispatched > 0;
- `CONDITION.txt` says `backend=mock`, with the script path and its md5;
- every artifact's `backend_id` (both fields) is `mock`;
- every artifact has `served_model` None;
- every artifact has `mock_mode` None, so it is the scripted mock, not the echo;
- zero token usage, meaning zero billed calls;
- no cost log;
- no probe line for the label;
- every dispatched artifact has `provenance: m3_default` with "plan absent";
- every dispatched decision is `junction_clear` with the four robots and `proposed_plan: null`.

**Offline gate test (`kit/test_gates_ibs.py`, 47 cases).** Verified offline against the 2026-11-13 bundles, which are read only:

| Fixture | Arm checked as | Failing checks |
|---|---|---|
| a1, as recorded | C | Exactly the no-VLM set (`c_cond_backend`, `c_backend_mock`, `c_no_served_model`, `c_no_tokens`, `c_no_cost_log`), plus the tag, arm and key line of a 2026-11-13 bundle. |
| a1, as recorded | C | Dispatch, `m3_default` and scripted-decision checks pass. |
| a1, as recorded | A | Only the tag and the key line. The model id is read correctly from `served_model`. |
| a1 re-labelled to this kit (tag, arm, key line) | C | Exactly the no-VLM set. |
| a1 re-labelled to this kit, with mock artifacts | C | None (passes). |
| a2, e03, e05, e07, e09 | C | The no-VLM set. |
| a2 | C | Also `c_m3_default` (its plan was `repaired`). |
| Arm B e02, e04, e06, e08, e10 | C | `c_artifacts` and `c_dispatched`. |
| The 2026-10-02 real mock `m3_default` artifact | C | All artifact checks pass. |
| The closure R1 mock (`vlm_verbatim`) | C | `c_m3_default` and `c_scripted_decision`. |
| Real 2026-11-13 probe line (relabelled) | A | None (passes). |
| Synthetic failed-call artifact | A | None (allowed). |
| Synthetic decision with no model id | A | `a_served_model`. |

---

## 7. Outcomes

- **Primary and secondary outcomes.** These are the frozen 2026-11-13 definitions, unchanged: frozen `resolved`, episode success, time to resolution, GT minimum pairwise distance, floor stops and arrivals. They are scored by `kit/score_ibs.py`, which wraps the pinned `score_ib10` (`scripts/coverage_scene_scores.py`, `a17ac751`, byte-identical to 68e67b5). The scorer passes `allow_mock=True` for Arm C only.
  - Regression: re-scoring the 11 bundles from 2026-11-13 reproduces every scoring field of their `episodes.jsonl`.
  - `--check-r1` reproduces closure R1.
- **Attribution.** As on 2026-11-13. Arm C is `m3_default` by construction; the gate enforces it.
- **Added per episode (secondary, descriptive).** Third-robot waivers captured, `latch waiver revoked ... reason=closing` lines, not-honoured and rejected-leg lines, deadline-ended commands, and key-on stalls.
- **Comparison.** Arm A against Arm C within this run, counts only. The 2026-11-13 arms are a separate reference and are not pooled.

---

## 8. What Each Outcome Supports

| Outcome | Supports | Does not support |
|---|---|---|
| Smoke passes | The key-on runtime does not break the normal IB10 Layer 2 path in one episode: no floor stop, no contact, no key-on stall. | That the fix works live. See caveat (a). |
| Smoke fails | The key-on runtime needs inspection on IB10 before any further run. | A verdict on the fix itself. Read the FAIL line. |
| Arm C resolves as often as Arm A | On this scene, with strategy and robot set given, M3's default plan content is enough. | "The VLM adds nothing." See caveat (b). |
| Arm C resolves less often than Arm A | Something Arm A does beyond the first plan matters on this scene. Candidates are later re-dispatch, timing, or plan content. | Which of these it is, without the episode traces. |
| Time differences A vs C | Nothing quantitative. | See caveat (c). |

---

## 9. Caveats

These hold whatever the results are.

- **(a) The smoke is not a live validation of the fix.** In the 11 bundles of 2026-11-13, the cross-cluster exemption path that the fix changes fired in e09 only. A smoke pass shows that the key does not break the normal path. It does not show that the fix works when that path fires.
- **(b) Arm C isolates plan content only.** The script gives Arm C the strategy (`junction_clear`) and the robot set (all four). Strategy and robot selection are therefore not tested, and Arm C cannot show that the VLM adds nothing. Offline re-grounding (section 5) already shows that on five recorded first-dispatch snapshots, the first commands Arm A dispatched were identical to M3's default plan. Arm C mainly tests the live loop around that plan.
- **(c) Arm C times are not directly comparable with Arm A's.** Arm C dispatches without model latency. Its first trigger is also answered `none` by the script's first entry, so its first dispatch comes one re-trigger later.
- **(d) The matched comparison is within this run.** Arm A and Arm C share runtime, key, floor, overlay and VM session. The 2026-11-13 arms ran with the key off on the `68e67b5` runtime. They differ from this run in two things, the code delta and the key, and they are a separate, unpooled reference.
- **(e) The episodes are near-repeats.** There is no pose jitter, one scene and one seed label, so episodes are near-repeats, not independent samples. There are no p-values and no intervals. The run is exploratory and is never pooled with prereg-v3.

---

## 10. Caps

| Cap | Value | Enforcement |
|---|---|---|
| Wall clock | 5 h in total, from VM start to TERMINATED, summed over every invocation (smoke + follow + any resume). | Each invocation's cap is the remainder, booked in `wallclock_ledger.tsv`. A VM is never started with less than 1.5 h left. An episode starts only if it can end within its 40 min budget before the chain deadline, which is the invocation cap minus a 30 min teardown reserve. A dead-man on the VM restores and powers off at cap + 20 min. |
| Spend | $1.00 est in total. | Arm A only: `cost_watch.py` per-episode guard $0.25. No Arm A episode starts with less than $0.25 left. Arm C makes no calls. Probes are one-token calls and are not in the estimate. |
| Analyses | No count cap (`MAX_ANALYSES=0`). | As on 2026-11-13. |

**Changes from 2026-11-13 enforcement:**

- **Per-episode spend guard:** $0.50 → $0.25, to fit the $1.00 total.
- **Episode admission budget:** 2700 s → 2400 s.
- **Teardown reserve:** 2700 s → 1800 s.
- **Driver wait after the chain deadline:** 1200 s → 600 s, so at least 20 min stay inside the cap for restore, pull and stop.
- **Wall-clock cap:** now cumulative across invocations, not per invocation.

If teardown still overruns the cap, the dead-man fires at the invocation cap + 20 min.

**Estimated wall time.** On 2026-11-13, Arm A episodes took 18.5-21.5 min of wall time; the smoke took 26 min from VM start to TERMINATED.

- **Smoke.** About 26-35 min. The colcon deploy and the restore of the code delta add a few minutes.
- **Follow-up.** About 10-15 min of setup, then 9 episodes at about 18.5-23 min, then teardown: about 3.1-3.7 h.
- **Total.** About 3.5-4.2 h.

All nine follow-up episodes are admitted if they average up to about 22.5 min. At about 23 min or more, the last slot (e10, Arm C) is refused by the wall-clock rule and reported as not run. `test_dry_ibs.sh` prints this table.

---

## 11. Runbook

From `data/logs/vm_runs/ib10_safety/kit/` in the `vgu-vlm-swarm-v7d` worktree:

```bash
bash test_dry_ibs.sh     # offline, must print TEST_DRY_IBS OK
bash run_ibs.sh smoke    # step 1
# inspect (below); only on SMOKE_CHECK PASS and owner acceptance:
touch ../SMOKE_ACCEPTED
bash run_ibs.sh follow   # step 2
```

Between the two commands, check:

1. The driver log ends with `VM TERMINATED (verified)`, and there is no `RESTORE_FAILED_*` or `VM_NOT_STOPPED_*` marker.
2. `../SMOKE_CHECK.txt` says PASS. Read the four `CRITERION` lines and the `INFO` lines: third-robot waivers, revocations, resolved.
3. The smoke bundle's `m4.log` startup line ends with the key tail, and its `decisions/` look like a normal Arm A episode.
4. The `INFO arm_C_prerequisite` line says `match` (`reasoning/vlm/mock_backend.py` is `c27742a0`). Otherwise Arm C cannot run.
5. If the smoke did not resolve, or the check failed, stop and ask the owner.

---

## 12. Verified Offline, and What Only the VM Can Show

Verified offline on 2026-11-14 (`kit/test_dry_ibs.sh`):

- Bash syntax checks, Python compile checks and kit md5s.
- The git preflight.
- The key-on startup line, derived by the branch's own `startup_log_line` from the merged file.
- The episode tables.
- Every driver DRY_RUN path, the cumulative ledger and the follow gates.
- Snapshot, deploy and restore on a fake VM tree. The tree was extracted from 68e67b5, with shimmed docker, colcon and md5sum. The cases were happy, double restore, half-deployed, install drift, mock absent, foreign mock, tampered backup and colcon failure.
- The gate tests (section 6), the scorer regression and closure R1, and the Arm C re-grounding (section 5).
- The test run also found and fixed one kit bug carried over from 2026-11-13: a refused snapshot overwrote the pre-run pin log that the restore compares against.
- The real `fc_launch.sh` in DRY_RUN with Arm C's environment, run from outside the repo: it forces `reasoning_backend_id: mock` and exports `VGU_MOCK_DECISION_FILE`.

Only the VM can show:

- **`reasoning/vlm/mock_backend.py` is the 68e67b5 bytes (`c27742a0`).** This file was never recorded on this VM, so it is not a hard pin. The snapshot prints it as an `info` line and `smoke_check` echoes it; `ep_run_ibs.sh` refuses every Arm C episode on a mismatch, which stops the chain at e02.
  - Recorded on this VM: `backend_factory.py` `82ee9b8f` and `reasoner.py` `d7bc7db1` were recorded by the v4 per-cluster snapshot and restore on 2026-11-13, so they are hard pins.
  - Not recorded: `src safety.py` is a new hard pin. On 2026-11-13 the installed copy matched `c6c9cbae` and every installed swarm_execution `.py` equalled its source.
  - Not known: whether the Arm C script is present on the VM. If it is absent, the kit installs it and removes it again.
- **The deploy works.** The real colcon build, and the key-on startup line in a live M4 log.
- **Behaviour on the live scene.** How the key-on monitor behaves on IB10, and how Arm C's skip-first script lines up with the live trigger timing.
- **Timing and quota.** Per-episode wall time and the Gemini quota.

---

## 13. Amendment (2026-11-14): Re-run of Slot e02

This section was written on 2026-11-14 **after** the results of sections 1-12 were known (`docs/reports/2026-11-14-ib10-safety-default-arm-results.md`). It was committed before the re-run started.

### 13.1 What Is Re-run and Why

The owner's instruction (2026-11-14), verbatim:

> "re-run the invalid default-only episode"

- **Slot.** e02, Arm C (grounder default only). The recorded bundle is `ib10S_e02_armC_a1`. `attempts.tsv` records it `ran`, and the scorer scores it `invalid_jam`.
- **Why it is invalid.** robot_1's Nav2 stack hosts the shared `map_server`. Its lifecycle manager logged `Configuring map_server` and never `Activating map_server`. No costmap received a map, so the robots got no plan, did not move and no jam formed. The results report gives the evidence ("e02: facts, then inference").
- **What runs.** One launch of the same slot, labelled `ib10S_e02_armC_a2`. The settings are those of every other Arm C episode: key on, 0.20 m floor, the same mock script (`6c670a6e`), the same overlay (`0196f1e8`), the same runtime and gates.
- **This is post hoc.** The re-run was decided with knowledge of every other result of this run: Arm A 5/5 resolved and Arm C 4/4 valid resolved. It is reported as a re-run, never as a registered episode.

### 13.2 Counting Rule

This is the rule already registered in the 2026-11-13 spec, section 5, and inherited by section 1: an invalid jam (criterion 1 fails) is excluded from the primary denominator and reported.

- `attempts.tsv` is never edited. Its a1 row stays `ran`, as recorded.
- The scorer applies the rule keyed on the scored status. A `ran` attempt whose status is `invalid_jam` is listed as `EXCLUDED:invalid_jam`. The slot's counted attempt is its one `ran` attempt that is not `invalid_jam`.
- **If a2 forms a valid jam**, a2 is the slot's counted episode and a1 is reported as excluded.
- **If a2 is also invalid, or fails a harness gate**, both attempts are reported and slot e02 has no counted episode.

### 13.3 No Third Attempt

There is no third attempt, whatever a2's outcome.

- The chain's rerun mode launches exactly once. It has no Nav2 bring-up retry, unlike the normal three-attempt loop.
- The driver runs the rerun mode once only. It writes `RERUN_STARTED_<ts>` before the VM starts and refuses if any such file exists.
- If the invocation fails for a harness reason, it is restored, stopped and reported, and it is not relaunched.

### 13.4 Kit Change

All guards are unchanged:

- kit md5 check, git preflight, snapshot, deploy and verify;
- arm check and condition gate;
- the cumulative wall-clock ledger and the 5 h cap;
- the $1.00 cap (Arm C makes no calls);
- per-episode restore;
- the EXIT trap: restore, pull (`rsync -a`, never `--delete`), stop, then verify `TERMINATED`;
- the `RESTORE_FAILED_*` and `VM_NOT_STOPPED_*` markers;
- on a stockout, only the same VM's start is retried.

**Wall clock.** 12,324 s of the 18,000 s cap are used, so 5,676 s remain. That is above the 5,400 s minimum for starting the VM, so no threshold was changed.

| File | Change |
|---|---|
| `chain_ibs.sh` | `MODE=rerun`, hard-wired to `RERUN_SLOT=02; RERUN_ARM=C; RERUN_ATTEMPT=2`. It is the only path that runs a slot already recorded `ran`. It refuses unless the a1 row is `ran`, the highest existing bundle of the slot is a1, and no a2 row exists. One launch, no bring-up retry. Slot resolution is factored into `resolve_slot`; smoke and follow behave as before (dry-tested). |
| `run_ibs.sh` | `rerun` mode, with the same SMOKE gates as `follow`. Once-only marker; refuses if `runs/ib10S_e02_armC_a2` exists. **No existing evidence file is written:** the VM tree is pulled into `vm_rerun/`; `runs/` is pulled with `--ignore-existing`; the wall clock is booked in `wallclock_ledger_rerun.tsv`, and the cap sums both ledgers; the scorer writes `summary_rerun/`. After scoring, it prints the start-up report. |
| `score_ibs.py` | The invalid-jam rule (13.2). `--attempts` is repeatable. |
| `startup_check_ibs.py` (new, Mac) | Reports, without gating, whether the `map_server` host stack logged `Activating map_server` and the map lifecycle manager's `Managed nodes are active`. It also counts `no map received` and `Costmap timed out waiting for update` per stack, and prints the scorer's jam status. |
| `test_dry_ibs.sh` | Covers the new path: rerun table; slot resolution on a fake VM tree, with four refusal cases and follow still skipping 9/9; the rerun driver path; the scorer rule; the start-up report on the real e02 a1 (PROBLEM) and e04 (OK) bundles. |
| `mac_kit_md5_ibs.sh`, `README.md` | Lists the new file; documents the rerun. |

Unchanged, byte-identical to the run of sections 1-12:

- `ep_run_ibs.sh` `7a209793`
- `cond_ibs.py` `50035500`
- `ibs_env.sh` `f2825e23`
- `start_ibs_chain.sh` `3e91bedb`
- `deploy_ibs.sh` `34d68ba0`
- `restore_ibs.sh` `85c3c1a1`
- the overlay `0196f1e8`
- every `src/` and `code/` file

Kit md5s:

| File | Before (sections 1-12 run) | After |
|---|---|---|
| `kit_md5_ibs.txt` (VM list, 28 files) | `72358e80fb040861fc8fdac27ca5a67b` | `c2d0274def56dc6f62d90f0f15ab5e83` |
| `kit_md5_all_ibs.txt` (all files; 40 before, 41 after) | `0db47b478920d42da89ea1418c79964f` | `e6463a18b79d90d428129a06c72382c5` |
| `chain_ibs.sh` | `c12d3dc6c14e2ea226032eb5713882e1` | `61c668b9c1ab48d1b63ca6fe18004990` |
| `run_ibs.sh` | `2499ae200b4340708bd7f495291af0ca` | `5b94bd46d78d1d4e569cd28712b7f0b6` |
| `score_ibs.py` | `01845ab99557b4dcefcede0157139738` | `34bc4ed1bb9a88e6b12878cedf78cae6` |
| `test_dry_ibs.sh` | `59cceec158dfba5a8a451aad99fff39e` | `10f44f29fe4f2a2788fe8879fd69d7c9` |
| `mac_kit_md5_ibs.sh` | `653082fecadd15a0a7d7bf8dff6288a9` | `8091306a0abe88eee40b87bead4d8840` |
| `README.md` | `dd941f90551ab524fe7884865b5a097e` | `2c3f508322d870e2295a49e48c0582f2` |
| `startup_check_ibs.py` | absent | `448f636cb7f675186d60602eb27e0fbb` |

**Traceability.**

- The full diff is `data/logs/vm_runs/ib10_safety/summary_rerun/kit_change_rerun_20261114.diff` (md5 `1add02a432024c983117783d1209c096`).
- The previous md5 lists are kept beside it as `kit_md5_ibs.before_rerun.txt` and `kit_md5_all_ibs.before_rerun.txt`.
- The frozen `MANIFEST.md5` and archive still record the kit as it was. Those 8 kit files are the only manifest entries that now differ.

**Dry test.** `test_dry_ibs.sh` ended `TEST_DRY_IBS OK` on 2026-11-14 with the new kit (all sections, including 4b, 5b and 7f).

### 13.5 Reporting

- The re-run is reported in a dated section of the results report.
- Pooled Arm C is shown both before and after the re-run, and the report states that the re-run was decided after the results were seen.
- The new files are covered by a supplementary manifest and a supplementary archive. The original manifest and archive are not touched.
- No p-values and no intervals.

