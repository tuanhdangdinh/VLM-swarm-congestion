# Demo Campaign: Recorded Demo Videos for Four Scenarios

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: registration of the owner-approved demo-video campaign (four scenarios, one VM, 12 VM-hours, $10), written offline before any VM use. The kits are prepared and dry-tested only; nothing has run.
- Rev 2 (2026-11-15): section 10 filled (go for the intersection under B3, the options-block check and caption, the demo runtime delta in two directories, the take classifier, the budget split); sub-caps `ho` 1.5 h and `m5` 4 h; kit md5s in section 9 re-recorded. Still offline; nothing has run.
- Rev 3 (2026-11-15): section 10.7, the per-scenario wall shares reallocated (`ib` 3.5 h, `ho` 0.5 h; `cv`, `m5` and every campaign total unchanged).
- Rev 4 (2026-11-15): section 10.8, closing note: intersection takes 4–5 on ER-2 instead of Sonnet, convoy stopped after 3 takes, the five-robot result.
- Rev 5 (2026-11-15): section 12, owner-approved convoy takes 4–5 with the M3 queued-robot hold (`cvh` kit), the second wall-share amendment (12.4) and the simulator-only test step; written before the VM start.

---

## 1. Purpose and Status

The owner approved a demo-video campaign: real Isaac Sim overhead-camera footage plus a synchronized terminal replay of each run's own logs (`feat/demo-panel-renderer`, `scripts/render_demo_panel.py`), for four scenarios.

**Every take is an illustrative demo. None of it is experiment data.**

- Takes are never counted and never pooled with any experiment: not prereg-v3, not IB10 (`ib10_live`, `ib10_safety`), not the registered convoy experiment, not v4.
- They are labelled demo everywhere: tags `demo_campaign_<scn>`, labels `<scn>D_tNN_aK`, VM directories `~/dmc_<scn>`, Mac directories `data/logs/vm_runs/demo_campaign/<scn>/`.
- Recording changes the real-time factor (RTF) and the timing of the stack. No timing from a take (RTF, trigger, dispatch, time to resolution) is comparable with any experiment.
- Every attempt, including every aborted one, is archived (bundle, attempts ledger, md5 manifest) and labelled.
- A video may say only what its own bundle shows, and must carry the labels of section 7.

This document is written before any VM use. Section 10 ("Demo runtime delta and go/no-go result") is a placeholder for the session lead.

---

## 2. Scenarios and Order

The campaign runs on the one GPU VM (`vgu-thu-base-isaac-vm-asia-northeast1-a`), one scenario after the other, in this order:

| # | Key | Scenario | Robots | Kit |
|---|---|---|---|---|
| 1 | `ib` | `intersection_bottleneck` | 4 | `data/logs/vm_runs/demo_campaign/ib/kit/` |
| 2 | `cv` | `convoy_counterflow_slip` | 4 | `data/logs/vm_runs/demo_campaign/cv/kit/` |
| 3 | `ho` | `head_on_asymmetric_w0p2_eopen_bshort_o0` (head-on with obstacle) | 2 | `data/logs/vm_runs/demo_campaign/ho/kit/` |
| 4 | `m5` | `mapd_5_s1b`, seed position 21 (`mapd_5_s1b_seed21`) | 5 | `data/logs/vm_runs/demo_campaign/m5/kit/` |

**Arm.** Every take runs Layer 2 on with the live VLM `gemini-robotics-er-2-preview` (backend `gemini`). There is no Layer-2-off or scripted arm.

**Safety.** Every take keeps all grounding, feasibility and safety checks on:

- the M4 key `scoped_clearing_exemption` on, with 0.05 m / 3 readings;
- the 0.20 m hard-contact floor.

Before each take's condition gate, M4's startup line must end in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`.

---

## 3. Runtime

| Item | Value |
|---|---|
| Base | The v3 pin on the VM, git `68e67b5`. |
| Base delta | `safety.py` `3011d9a7` and `safety_monitor_node.py` `c2cad302` from `fix/safety-exemption-scope` (`8933863`), plus the merged `safety.yaml` `65fb84a3`. This is exactly the 2026-11-14 runtime. |
| Demo runtime delta | An INPUT (section 10). Filled 2026-11-15: `runtime_delta/` (`ib`, B3) DELTA_ID `5c7973d3a345df6bbcd0c7db17f55845`; `runtime_delta_inert/` (`cv`, `ho`, `m5`) `4843a776550ff4bd6f33e2d88c881bd2`. It was EMPTY before (`ae8740a08dfc178769dbcfa64a645c4b`). |
| Restore target | `PINS_V3 OK` after every invocation (snapshot, deploy, verify, restore), as the 2026-11-14 kits. |

**How the demo runtime delta is supplied.** It lives in `data/logs/vm_runs/demo_campaign/runtime_delta/`, outside every kit md5 list:

- `delta_files.tsv` lists each file as `relpath`, `md5` and `kind`. The kind is `pkg:swarm_orchestrator`, `pkg:swarm_execution` or `live`, and the bytes go in `files/`.
- `overlay_fragment.yaml` holds keys appended to every scenario overlay.
- `arm_expect.tsv` holds one deployed-loader expectation per key.

The kits use the delta as follows:

- **Validation.** `delta_dmc.py` validates it. It refuses kit-managed paths, wrong md5s, and a fragment that sets keys with no expectation.
- **Git preflight.** HEAD's runtime diff against 68e67b5 must be exactly the 3 safety files plus the delta's files. Merge the delta branch first.
- **Snapshot, deploy and restore.** The snapshot backs up each delta file, including ones ABSENT before the run. The deploy installs them and purge-rebuilds the touched packages. `pins run` checks them where the nodes read them. The restore removes or restores them.
- **Overlay.** The effective overlay is the base overlay followed by the fragment. With an empty fragment it is byte-identical to the base.
- **Arm check.** It checks every expectation through the deployed loader, so a key the loader does not know is refused instead of silently dropped.
- **Recording the id.** The delta id is printed by the driver, stored on the VM, and written into every bundle (`CONDITION.txt delta_id=`, `DELTA_ID.txt`).

---

## 4. Per-Scenario Settings and Demo Goals

### 4.1 Intersection (`ib`)

**Settings.** Exactly the 2026-11-14 IB10 safety-default Arm A, with the Layer-2-off arm dropped:

- overlay `ib10d_l2on.yaml` `0196f1e8`;
- deployed-loader reading `True True True 0.33 -1 config/rag.yaml True`;
- scene `intersection_bottleneck.yaml` `042802d6`, seed label 42, the yaml's 300 sim-s horizon, the USD built fresh;
- parallel Nav2 bring-up, as every IB10 record;
- `REC_SEC` 3300;
- an episode admission budget of 3000 s;
- a per-take live guard of $0.25.

**Demo goal.** The intersection resolves (GT arrivals 4/4: distance to goal < 0.3 m at some GT row; this rule agrees with the frozen IB10 scorer's `all_arrived` on all 21 IB10 bundles of 2026-11-13/14, including the one unresolved Arm A episode `ib10L_e09`) under a live VLM decision. `goal_check` prints:

- the plan provenance of each dispatch;
- the counterfactual: whether the executed commands differ from M3's default plan on this take's own snapshot. It re-grounds with the IB10 safety kit's `reground_c.py` and the M3-default script `6c670a6e`.

Dry run on `ib10S_e03_armA_a1`: `executed_differs_from_m3_default=False`, `provenance=m3_default`.

### 4.2 Convoy (`cv`)

**Settings.** The registered convoy settings, unchanged (v7f `docs/superpowers/specs/2026-11-14-convoy-live-resolution-experiment.md` and its kit, read only):

- overlay `cvl_l2on.yaml` `7e3ab552`;
- the legacy grounding file `config/grounding/cvl_convoy_legacy.yaml` `63f50f91`, installed by the deploy, removed by the restore, and loaded through the installed loader as `legacy`;
- the convoy USD built from `9684b5fc` (`duration_sec: 260.0`);
- the installed-map gate (`2cf00224` / `f48cb508`);
- robot_3's 120 s start delay, the "120 wall-s release", in the overlay and the arm check;
- deployed-loader reading `True True True 0.5 config/grounding/cvl_convoy_legacy.yaml legacy True 120.0`;
- a per-take guard of $0.20;
- parallel bring-up.

**Demo goal.** Show a live VLM convoy resolution. `goal_check` prints, per artifact:

- arrivals and resolved, by the convoy scorer's rule (within 0.35 m of the goal and never beyond 0.5 m afterwards; the registered `resolved` also needs a valid jam, which `goal_check` does not score);
- GT minimum pair distance and floor stops;
- strategy, involved robots and crossing order;
- grounding and provenance.

**Disclosure.** These are live VLM convoy episodes, seen before the registered convoy experiment's VLM arm has run. They are not part of that experiment and must not be used to change its registered rules.

### 4.3 Head-on with obstacle (`ho`)

**Variant.** `head_on_asymmetric_w0p2_eopen_bshort_o0`:

- yaml `49c7500b`;
- west blocker at x = −1.85;
- oracle `correct_yielder: robot_2` (robot_1 cannot park);
- goals 2.6 / −1.5;
- map `188dccd3` / `e97aba6b`.

**Why this variant.** It has the most validated live history: 12 ER-2 September episodes on the west side, all 2/2 arrivals. 4 of them ran under the current apparatus (CE1, CE3, CE2b and the 2026-09-30 ER-2 demo recording). It also has a defined oracle.

**Production configuration (September), reproduced.** The base overlay is the VM-pinned `orchestrator.yaml` `1f656533` with exactly the seven September edits of `bshort2/_vm_driver/gen_orch_b2.py`:

- goals 2.6 / −1.5;
- `grounding_yield_feasibility: "swap"` (quoted);
- `prompt_static_obstacles: true`;
- `prompt_robot_order: random`;
- `keep_debug_frames` / `keep_raw_frames` true;
- `static_obstacles` UNCOMMENTED with obstacle_1 at (−1.85, 0.0), 0.3 × 0.3 m.

The result is `ho_w0p2_bshort_on.yaml` `3929a087`. Its non-comment content is identical to the 2026-09-30 ER-2 demo's installed yaml (verified by diff).

`fc_launch` gets `MODALITY=on`, which its obstacle guard requires.

**Arm check.** Deployed-loader reading `True True True True 1 -1.85 swap random False config/rag.yaml [2.6, 0.0] [-1.5, 0.0] True True`. The fields are:

- Layer 2 on, gate and submit;
- obstacle text on, and ONE loaded obstacle at x −1.85;
- the gate `swap` and the order `random`;
- the plan channel off, so prompt v2;
- derived grounding;
- both goals;
- stage-2 and the classical shadow.

**What the 68e67b5 runtime expects for a 2-robot head-on:**

- prompt v2 (`CURRENT_PROMPT_VERSION = 2`; v3 only with the plan channel on);
- derived grounding (`config/rag.yaml` `mode: derived`);
- the plan channel off (pristine default).

The September launch settings load on this runtime: dry-loaded through the loader above, and fc_launch in DRY_RUN passes the guard with `MODALITY=on`.

**The known trap is guarded twice:**

1. The kit's dry test renders the prompt through the worktree's prompt builder from the loaded overlay. It contains `- obstacle_1: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m`. For the 2026-09-30 demo artifact `67d5cb88`'s own scene and drawn order, it is byte-identical to that artifact's recorded prompt.
2. With the list still commented out:
   - the prompt has no obstacle line;
   - the arm check refuses the overlay (0 obstacles);
   - the condition gate requires the obstacle line in every recorded prompt (`prompt_contains`), plus `grounding_yield_feasibility=swap`, `prompt_robot_order_mode=random` and `prompt_version=2` in every artifact.

**Settings that differ from September, and why:**

| Setting | September | Here | Why |
|---|---|---|---|
| Code | Trees `e708ffa` / `cf4899f` (J/K/N: prompt v1, legacy grounder) and `3959d7f` (CE runs and the 09-30 demo: prompt v2, derived grounding, stage-2, shadow) | 68e67b5 + the 3 safety files (+ the demo delta, if any) | The campaign runtime. Prompt v2 output is byte-identical to 09-30. M4 adds the key and the 0.20 m floor. |
| Base `orchestrator.yaml` | That tree's pristine file | VM-pinned `1f656533` | The VM's pin. The non-comment content is identical after the edits. 68e67b5-only keys stay at their defaults (plan channel off, contradiction trigger off, `dispatch_enabled: true`, task stream off, `plan_dispatch_order_source: chi`). |
| Scenario yaml | Without `loop_map: null` | `49c7500b`, with it (commit `181a4ac`) | The tracked file at 68e67b5. The USD is rebuilt from it. |
| Recording | `RECORD=1`: fc_launch stage 5, before Nav2, `REC_SEC` 1000 | `RECORD=0` to fc_launch; the kit records both streams after the Nav2 gate (section 5) | The 2026-11-14 lesson (1b, 1c). |
| `REC_SEC` / grace / Nav2 timeout | 1000 / fc default / 240 | 2400 / `ISAAC_EXIT_GRACE_SEC` 45 / `NAV2_ACTIVE_TIMEOUT_SEC` 360 | Recording slows the RTF. The 45 s grace is the recorder stop window. 360 is the kits' value. |
| Bring-up | Parallel | Parallel | Unchanged. |
| Temperature | ER-2 has none (the Interactions API drops sampling fields) | Same | Do not report 0.0. |

**Demo goal.** "Yield completed" plus who yielded. `goal_check` prints:

- the model's `yield_robot`;
- the gate's re-grounding (`yield_robot_grounded_from` / reason);
- who yielded on the floor (the first robot of the first yield dispatch);
- whether that yield resolved `completed`;
- the oracle's `correct_yielder`;
- the classical shadow's raw and gated picks (`shadow_classical.decision.yield_robot` and `classical_retreat.yielder_id`);
- the drawn presentation order.

Arrivals are reported (GT < 0.3 m; `scripts/rescore_arrivals.py` is the reference rule for head-on and may differ near the blocker), but 2/2 is NOT required.

**Correction to the brief.** The brief says the blocker lies on the opposing robot's goal path. That holds for the base `_o0` variants (±2.5 goals; `docs/reports/2026-09-25-overnight-findings.md`). It does not hold for this `_bshort` variant: J/K/N reached 2/2 in 15/15 episodes (`BSHORT_PILOT_SUMMARY.txt`, `bshort2/BSHORT2_PILOT_SUMMARY.txt`). The goal definition above covers both cases.

Dry run of `goal_check` on the 09-30 demo bundle: the model named robot_2, it yielded and completed, and the oracle is robot_2. The shadow's raw pick was robot_1, gated to robot_2.

### 4.4 Five robots (`m5`)

**Seed.** Position 21 of `config/s1_seeds.yaml` (`442a5e0f`), seed 2107305794. Positions 1–20 are the preregistered confirmatory list (`confirmatory_count: 20`): tranche 1 used 1–5 and the proposed tranche 2 is 6–20. Position 21 is outside it: a registered extension seed already used by pilot E21 and by the exploratory v4 Stage 1 shadow run (`v4pcs_pos21_armA_a1`, 2026-11-13). The kit's dry test checks this.

**Disclosure.** The demo takes reuse a seed seen in exploratory runs. They are illustrative and must not be read as new evidence on that seed.

**Settings.** The prereg-v3 tranche-1 Arm A procedure, unchanged:

- overlay `s1b_shield_escort_orch_seed21.yaml` `09bc16e6`, a byte copy from the v4 kit. It carries no v4 key. The shadow overlays (`v4_pc_shadow_*`) are not used.
- per-seed scenario yaml `mapd_5_s1b_seed21.yaml` `61fd6faf`. It is installed from the kit only if absent, and removed again only if it was absent.
- the 600 sim-s horizon;
- sequential Nav2 bring-up, as tranche 1 and v4;
- deployed-loader reading `True True True config/grounding/s1b_dynamic_shield_escort.yaml True True swap True True 2107305794 600.0`;
- `REC_SEC` 6600 (the M5-tail cap: a take slower than 110 min wall is cut there; Isaac still finishes its horizon), an admission budget of 6600 s, and a per-take guard of $0.50.

**Demo goal.** Show the limitation. The expected outcome, from the 2026-10-21 tranche-1 and 2026-11-13 v4 reports: no resolution, few motion commands, withheld analyses, and Layer 2 going quiet (`scene_unchanged`) long before the horizon. `goal_check` prints analyses, grounded dispatches, withheld analyses, `scene_unchanged` mentions and arrivals.

**Takes.** One or two at most.

**Recorder load with five robots** is unmeasured: there is no 5-robot recording history. The two recorders start after the sequential bring-up, never during it.

---

## 5. Recording (Fixes of the 2026-11-14 Weaknesses)

**Who records.** `fc_launch.sh` (pinned `055db01e`, unchanged) runs with `RECORD=0`. The kit's `recmgr_dmc.sh` owns both recorders. Both use the pinned `scripts/record_topic_video.py` (`90aa8971`), launched as fc_launch launches its own: `docker exec -d`, same ROS environment and FastDDS profile, `best_effort`.

| Stream | Topic | Files in the bundle |
|---|---|---|
| Annotated | `/perception/annotated_frame` | `rec/annotated_NNN.mp4`, `rec/annotated_rec.log` |
| Raw camera | `/camera/image_raw` | `rec/camera_raw_NNN.mp4`, `rec/camera_raw_rec.log` |

**Recorder parameters:**

- 300-frame segments;
- nominal `--fps 5`, a playback rate only;
- `--duration-sec` = `REC_SEC − 60`;
- no `ros2 topic hz` measurement (it would add subscribers at approach onset): the achieved rate comes from the recorder logs.

**Start (1c).** Both recorders start right after fc_launch logs `first stack launch -> gate passed`, never during the parallel or sequential Nav2 bring-up. The evidence that nothing is lost (verified offline):

- **No motion before M5.** In all 22 IB10 bundles of 2026-11-13/14 (v7a and v7d), the first robot displacement over 5 cm (GT) comes at or after M5's first scene record. That happens 0.1–1.3 sim-s later, except one map-server-abort bundle at +24 sim-s. Robots cannot move before M4 and M5 start, and fc_launch starts them only after the gate line (stages 7 and 8, `fc_launch.sh` lines 880–938).
- **Margin.** M5's session line comes 10.5–15.0 wall-s after the gate line (median 12.7 s; 22 bundles).
- **Recorder start time.** The 2026-11-14 recorder took 3.5 s from `docker exec` to its first frame (17:45:48 → `wall_clock=1794678351.519`).
- **Conclusion.** Both recorders are up at least about 5 s before M5 starts, and so before any motion. What is not recorded is the static bring-up: robots at spawn, sim time roughly 7–15 s.
- **Load avoided.** The old stage-5 recorder ran inside the bring-up window that aborted on 2026-11-14. It achieved only 350 frames in 149 s (≈2.3 fps) against 9.3 Hz measured. Whether it caused the abort is unknown (one failure).

**Stop (1b).** Both recorders get SIGTERM and a bounded wait (`REC_STOP_WAIT_SEC` 30 s) on the FIRST of:

- Isaac gone: the `Isaac PID N` wrapper's `ps` state (fc_launch's own rule) or the `run_simulation` pattern, whichever says so first. fc_launch then idles 45 s before its container restart (`isaac_wait_exit_or_cap`), so on the normal path the trailers are always written.
- An fc_launch abort or end line.
- fc_launch gone.
- A stop request (`$H/REC_STOP`).
- A timer before the M5-tail cap.
- Both recorders exiting by themselves.

**Kit-initiated teardowns stop the recorders FIRST:**

- `ep_run_dmc.sh`'s EXIT trap does it before its restore.
- `restore_dmc.sh` does it before it stops the chain or kills anything. The driver's EXIT trap and the dead-man both go through it.

**Remaining exposure.** An fc_launch-internal abort after the gate races its own container restart (about 3 s on 2026-11-14). That is the hard-kill case: the 300-frame segments bound the loss to one segment (about 1–2 min of footage).

**Post-pull verification (`video_verify_dmc.py`).** Every MP4 must have a readable frame count above 0 (`ffprobe -count_frames`). Otherwise:

- one repair is attempted on a copy: an error-tolerant remux, then `untrunc` against a readable sibling segment if `untrunc` is installed (it is not on the Mac today);
- if the repair fails, the segment is FLAGGED by name;
- a missing `WROTE` line in the recorder log is flagged too.

**Archive.** Right after each pull the driver selects every bundle that this invocation brought back (a before/after listing of `runs/`: every attempt of every take, aborted ones included), writes `../MANIFEST_<ts>.md5` over all their files plus the VM-side `attempts.tsv`, chain log and probe log, and runs the startup check, the video verify and `goal_check` on each.

The frame map (`rec/<stream>_framemap.json`, `{"frame_sim_times": [...], "anchors": ...}`) is decoded from the burned-in clock by `overlay_framemap.py`, over the longest contiguous readable prefix of segments.

---

## 6. Limits, Caps and the Stop Rule

**Campaign ledger.** `data/logs/vm_runs/demo_campaign/ledger/campaign_ledger.tsv` (`ledger_dmc.py`, caps in `caps_dmc.tsv`) books:

- wall clock from VM start to TERMINATED;
- estimated spend: cost-watch estimates per take, plus one-token probes at $0.0005 each;
- every attempt's outcome;
- scenario stops.

| Cap | Value |
|---|---|
| Wall clock, total | 12 h (43 200 s) |
| Wall clock, per scenario | `ib` 2.5 h, `cv` 2.5 h, `ho` 1.5 h, `m5` 4 h reserved, 1.5 h slack (section 10.5; was `ho` 2 h, `m5` 5 h) |
| Spend, total | $10, including any offline spend (`book-spend <scn> offline <usd>`) |
| Live guard, per take | `CAP_EP`: `ib` $0.25, `cv` $0.20, `ho` $0.20, `m5` $0.50. `cost_watch.py` stops Isaac at the guard. |
| Valid takes per scenario | 5 |
| Bring-up aborts per scenario | 3 |

**Admission:**

- An invocation starts only if prep (900 s), one take budget and the teardown reserve (900 s) fit in the smaller of the campaign's and the scenario's remaining wall clock, and the spend left is at least the scenario's minimum.
- Each take is admitted on the VM only if it can end before the chain deadline.

**Bring-up retry (1a).** `classify_dmc.py` runs BEFORE the key-line gate. It classifies a launch as a bring-up abort if:

- fc_launch started Isaac but never logged `first stack launch -> gate passed`. This covers every abort before `Nav2 action servers live` (a lifecycle `change_state` timeout, a `wait_action` / `wait_topic` timeout) and `NAV2_BRINGUP_FAILED`; or
- the map start-up check says PROBLEM (the map_server class).

A bring-up abort retries the same take as attempt K+1 while the scenario's budget lasts.

**Reading of "up to 3 startup attempts per scenario in total".** The kits read it as at most 3 BRING-UP ABORTS per scenario, counted across invocations by the ledger. The VM's own `attempts.tsv` (it persists in `~/dmc_<scn>`) also bounds the count, so a failed pull cannot buy extra attempts. At the third, the chain logs `BRINGUP BUDGET EXHAUSTED`, the scenario stops and is reported, and the driver refuses further invocations of it. The other reading is "at most 3 launches per take". It can be enforced by passing `--episodes 1` and stopping a take by hand. The session lead should confirm which reading the owner meant.

**Never retried** (the chain stops):

- a refused episode (arm check, overlay, pins, labels);
- fc_launch exiting before Isaac (its guards);
- a missing `logs saved to`;
- a per-episode restore failure;
- a missing map-check verdict;
- the key line;
- a failed condition gate;
- a Gemini probe that is not rc=0 (401/402/quota-429 included).

**Stop rule.**

- The driver runs ONE take per invocation by default (`--episodes N` runs N).
- After each invocation, the operator (the session lead) reads `goal_check`'s `GOAL_SUMMARY` and decides: stop the scenario at the first take that meets its demo goal, or run another take, up to 5 valid takes.
- The kit decides nothing.
- Every take, including unused ones, stays archived.

**Teardown.** Each invocation ends by:

1. restore: recorders first, then `PINS_V3 OK`;
2. pull: `rsync -a`, never `--delete`;
3. stop, and verify TERMINATED.

Markers:

- `RESTORE_FAILED_*` or `VM_NOT_STOPPED_*` in ANY scenario directory blocks every scenario.
- `PULL_FAILED_*` is written when the pull did not complete.

A stockout retries the same VM's start only.

---

## 7. Labelling Rules for Videos

Every video carries the following on screen or in its caption:

- "**Illustrative demo, not controlled experimental evidence.**"
- "**Take N of M**", where M is the number of valid takes run for that scenario.
- Exactly one outcome label:
  - **VLM-driven execution**;
  - **M3-default resolution**;
  - **Unresolved failure**.

  For the intersection the label is exactly `take_class_dmc.py`'s `TAKE_CLASS` (section 10.4). A repaired, re-grounded or yielder-swapped plan is M3-default, and so is a take where a fallback or stage-2 command ran. For the other scenarios, "VLM-driven" may not be used unless a rule is added to section 10.4 before their first take. The fallback reading is M3-default: `provenance=m3_default`, or no counterfactual difference.
- For the convoy: "**Shown before the registered convoy experiment's VLM arm ran.**"
- For five robots: "**Seed position 21 (exploratory extension seed); shows a current limitation.**"
- Takes that were not chosen are listed in the report. Selecting the best take must be disclosed ("selected take").

---

## 8. Runbook

**Setup, once.** Commit any demo runtime delta (section 10). Then assemble and dry-test all four kits:

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign
for k in ib cv ho m5; do bash common/assemble_dmc.sh $k && (cd $k/kit && bash test_dry_dmc.sh | tail -1); done
python3 ib/kit/ledger_dmc.py status     # run from any kit, the ledger defaults to demo_campaign/ledger/campaign_ledger.tsv
```

**Per scenario, in order.** One take per invocation. Repeat until the demo goal is met, or a cap or the bring-up budget stops it:

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/ib/kit && bash run_dmc.sh
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/cv/kit && bash run_dmc.sh
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/ho/kit && bash run_dmc.sh
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/m5/kit && bash run_dmc.sh
```

Add `--episodes N` to run N takes in one invocation. This saves about 15 min of prep and teardown per extra take, but delays the stop decision.

**Between invocations, check:**

1. The driver log (`../driver_<scn>_<ts>.log`) ends with `VM TERMINATED (verified)`, and there is no `RESTORE_FAILED_*`, `VM_NOT_STOPPED_*` or `PULL_FAILED_*` file.
2. The `[chain]` lines: `CLASSIFY`, `END`, `COND` and no `GATE FAILED`. For a bring-up abort, check the budget left.
3. Each `VIDEO_VERIFY` line says OK. If a stream is FLAGGED, look at its segments before deciding on another take.
4. The `GOAL_SUMMARY`, `COUNTERFACTUAL`, `YIELD` or `LIMITATION` lines against the scenario's demo goal (section 4).
   For the intersection, also run `python3 take_class_dmc.py <bundle>` in the kit directory. Its `TAKE_CLASS` line is the video label. `DEFAULT_ORDER` goes in the caption only.
5. `python3 ledger_dmc.py status`, run in the kit directory, for wall, spend and take counts.

**Render.** Use the renderer guide (`feat/demo-panel-renderer`, `docs/guides/demo_panel_video.md`):

```bash
python3 scripts/render_demo_panel.py render --bundle <bundle> \
  --camera <bundle>/rec/annotated_000.mp4 [...] --camera-map <bundle>/rec/annotated_framemap.json \
  --out data/demo/<label>_panel.mp4 --stills
```

The bundle keeps the file names the renderer reads: `m5.log`, `m4.log`, `decisions/<request_id>.json`, `cost.log`, `CONDITION.txt`, `m5_scene.jsonl`, `gt/ground_truth.jsonl`.

---

## 9. Kits and Wall Estimates

**Assembly.** Each kit is assembled from `common/` (one skeleton: driver, chain, episode runner, recorder manager, gates, ledger, video verify) plus `<scn>/spec/`. Kit md5s as dry-tested:

| Kit | `kit_md5_dmc.txt` (VM files) | `kit_md5_all_dmc.txt` | Overlay | Dry test |
|---|---|---|---|---|
| `ib` | `98a57626afd3080f5d104ac64e40b47d` | `c97d0f3fa29c253b79a0b7c99ef0b375` | `0196f1e8` base, `614beed0` effective (B3) | `TEST_DRY_DMC ib OK` |
| `cv` | `37e73d8750d736858f9c182914182a42` | `056dd75d1d3215bb65566889e15bc5af` | `7e3ab552` | `TEST_DRY_DMC cv OK` |
| `ho` | `69a4ed79e8ee6d5409ed1c48e13abb2d` | `8718682abad7cf3c7ed217d8876f79c6` | `3929a087` | `TEST_DRY_DMC ho OK` |
| `m5` | `89112a40fe2b11c7e604b6636f92f27b` | `afb389654ac4802ea5384f40356afa85` | `09bc16e6` | `TEST_DRY_DMC m5 OK` |

Re-recorded 2026-11-15 after the section 10 fill (dry tests run with `MIN_MAC_FREE_KB=3000000`: the Mac had 4.9 GB free, below the driver's 5 GiB floor). The shared files are the same in every kit: `run_dmc.sh` `e811bbd2`, `chain_dmc.sh` `b8a32893`, `ep_run_dmc.sh` `25203d1b`, `recmgr_dmc.sh` `0f7adf25`, `goal_check_dmc.py` `f03087a9`.

**Wall estimates (inferred).** Each invocation costs about 10 min of prep (start, push, probe, snapshot, USD build on EVERY invocation, deploy) plus 3–5 min of teardown. The recorded RTF is unmeasured. Five takes per scenario do not fit in the sub-caps; the sub-caps fit about 2–3 takes.

| Scenario | Unrecorded take | Recorded take (guess) | Per invocation | Fits in the sub-cap |
|---|---|---|---|---|
| `ib` | 18.5–19.5 min | 25–35 min | 40–50 min | 2 one-take invocations, or 3 takes with `--episodes`, in 2.5 h |
| `cv` | 17–23 min (registered estimate) | 25–35 min | 40–50 min | 2–3 takes in 2.5 h |
| `ho` | ~13–18 min | 18–25 min | 30–40 min | 1 invocation (3 takes with `--episodes 3`), or 2 short ones, in 1.5 h |
| `m5` | 53–65 min | 60–100 min | 75–115 min (the USD is rebuilt every invocation) | 1 invocation (2 with a short first one) in 4 h |

The admission budgets are:

| Scenario | Prep + take budget + reserve |
|---|---|
| `ib` | 4 800 s |
| `cv` | 4 800 s |
| `ho` | 3 900 s |
| `m5` | 8 400 s |

**Dry-test coverage** (`bash test_dry_dmc.sh`, all four OK):

- syntax and kit md5s;
- git preflight: empty delta OK; a fake extra file plus key REFUSED until committed;
- key line; base overlay; effective overlay with empty and fake fragments; the deployed-loader arm check, with the fake key REFUSED;
- the take table and labels;
- the classifier on real and synthetic launches;
- the REAL chain with stubbed episodes: retry to a2, budget exhausted, condition, probe 4 and probe 3 never retried, the spend gate;
- the condition gate on a live fixture of the scenario. The convoy has none; it has never run live.
- the recorder manager on shims: start only after the gate, four stop paths, recorders stopped first by the restore;
- fc_launch DRY_RUN with `RECORD=0` and the kit environment;
- every driver DRY path and every ledger cap;
- video verify, including the real moov-less 2026-11-14 file;
- `goal_check` on the fixture;
- the fake-VM snapshot / deploy / restore with the empty and the fake delta;
- the head-on prompt render and trap;
- the five-robot seed check.

---

## 10. Demo Runtime Delta and Go/No-Go Result

Filled 2026-11-15, offline, before any VM use. Sources: `docs/reports/2026-11-15-vlm-order-channel-plan-check.md` (sections 5, 6, 10; merged into this branch) and `docs/superpowers/specs/2026-11-15-demo-runtime-delta.md` (rev 2).

### 10.1 Offline Go/No-Go Result (ER-2, 20 Recorded IB10 Snapshots)

| Cycle | Condition | `vlm_verbatim` | Demo events (first trigger: verbatim, recede order ≠ chi, `dispatch_matches_plan`) |
|---|---|---|---|
| 1 | A | 2/40 | 0/38 |
| 1 | B | 2/40 | 1/38 |
| 2 | A3 (A + release rule) | 6/40 | 0/38 |
| 2 | **B3** (B + release rule) | **14/29 (partial, cap)** | **7/27** |

Owner criteria, for B3:

- **(a) structurally valid and feasible plan:** 27/29 parsed, 14/29 verified `vlm_verbatim`.
- **(b) M3 executes the VLM's plan, not a silent replacement:** of the 14 verbatim plans, 10 also match dispatch. The other 4 name robot_2 as yielder, and dispatch yields robot_1 (the yielder gap, open by owner decision). Every other answer is recorded as `repaired` or `m3_default`.
- **(c) executed commands differ from the no-VLM default:** 7/27 first triggers (26 %), recede order only. That is about 78 % over 5 takes, inferred.

**Go for the intersection under B3, as a demo only.** This is not evidence. One scene, n = 29, partial.

### 10.2 What the Options Block Does, and the Caption (Part-1 Check, Verified Offline)

**Why section 5 of the plan-check report excluded it (cycle 1):**

- B did not raise ER-2's verbatim rate (2/40, the same as A).
- It added an invalid-action failure (9/40 plans copied `"reverse (north arm)"` as the action).
- It is a construct change: constrained selection from a listed menu instead of free composition.

Cycle 2's release rule removed the first objection (14/29) and reduced the second (2/29). The third still holds, and the caption wording below follows from it.

**How the block is built (code, verified).** At each analysis M5 calls `build_candidate_options` → `derive_candidate_options` (`reasoning/rag/command_grounder.py`). Its inputs are:

- the live M1 snapshot;
- the running scenario's declared geometry and static obstacles;
- the yield-gate mode;
- M3's grounding params.

Each (robot, action) pair is offered iff the verifier's own leg audit (`_plan_problems`) flags nothing on a probe plan. The block uses no recorded, oracle or ground-truth input.

The block lists actions per robot, never plans or orders, so the grounder's chi order is in no slot:

- rows follow the prompt's robot presentation order (`id_asc` at the intersection);
- actions follow the fixed vocabulary order;
- there is no ranking, marker or "preferred" wording.

It does reveal the recede SET: only robot_3 and robot_4 are offered `reverse`. That set is fixed by geometry, and the verifier enforces it anyway.

On all 20 stimuli the B3 prompt differs from the A3 prompt only by this block, and the block is identical across the 20 stimuli.

**What ER-2 chose under B3.**

- Recede order: of the 14 verbatim plans, 10 list `3rev 4rev` and 4 list `4rev 3rev`. Counted over all 24 B3 plans that reverse both pair robots, 19 put robot_3 first (ascending id = the listing slot). The bias predates the block: under A3, with no block, 13 of 18 put robot_3 first.
- The ascending-id choice does not follow the scene: chi prefers 4→3 in 17 of the 29 B3 calls (20 snapshots), and on the same snapshot ER-2 changes its order between replicates (`ib10S_e01`).
- Of the 10 order changes, 8 are ascending-id plans on snapshots where chi prefers 4→3. Of the 7 demo events, 6 are ascending-id.
- Because `id_asc` makes id order and listing slot the same, the two cannot be separated here.

**Verdict: legitimate. The block does not leak the answer or hardcode it.** The model is selecting each robot's action from a list of verifier-accepted actions, and the order it writes is mostly robot-id order.

**Caption sentence (mandatory, every intersection video labelled VLM-driven):**

> "The VLM (Gemini ER-2) chose each robot's action from the list of actions the verifier accepts in this scene and chose the order in which robot_3 and robot_4 back out; the verifier accepted that order and it was executed as written, differing from the system's default order (computed offline)."

Never call the plan "authored". Never imply the order was reasoned from the scene: it mostly follows robot-id order.

### 10.3 The Demo Runtime Delta (Frozen Config)

The five runtime files come from `demo/vlm-order-channel` `9102ce9`, merged into this branch (`aa16b0d`). On top of the three 2026-11-14 safety files, `git diff --name-only 68e67b5..HEAD -- ros2_ws reasoning config` lists exactly these:

| relpath | md5 | kind |
|---|---|---|
| `reasoning/vlm/models.py` | `2025f18179c9f3b05a81072027c32637` | live |
| `reasoning/vlm/prompt_builder.py` | `a9ad857cf8355cd9f5601124b0b814b2` | live |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `73f3fa4f35ceab61a5df646a71a902a6` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `37a6bbadf91cb8c9def21d6f625c8bfe` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `49fff7ab8fb460b9a94ea198cf5b523a` | pkg:swarm_orchestrator |

**Two delta directories, the same files.** The difference between them is the fragment. The profile key `DELTA_SUBDIR` selects the directory, and `run_dmc.sh` defaults to it.

| Directory | Kits | DELTA_ID | Fragment | Deployed-loader expectations |
|---|---|---|---|---|
| `runtime_delta/` | `ib` | `5c7973d3a345df6bbcd0c7db17f55845` | `plan_dispatch_order_source: model_when_verified`, `prompt_plan_grammar_rules: true`, `prompt_plan_grammar_release_rule: true`, `prompt_candidate_options: true` | the four values |
| `runtime_delta_inert/` | `cv`, `ho`, `m5` | `4843a776550ff4bd6f33e2d88c881bd2` | empty (registered overlays byte-identical) | `chi`, `False`, `False`, `False` |

**Frozen intersection config.** The 2026-11-14 Arm A overlay `ib10d_l2on.yaml` `0196f1e8` plus the four fragment keys gives the effective overlay `614beed0`. It keeps `plan_channel_enabled: true` and `grounding_yield_feasibility: 'off'`. The backend is `gemini` / `gemini-robotics-er-2-preview`.

**Why B3 is applied at the intersection only (recommendation, adopted in the kits):**

- **Head-on.** With the plan channel off (prompt v2, the September configuration), the loader refuses the B3 keys (verified: `... require plan_channel_enabled (prompt v3)`).
- **Convoy and five-robot.** Both load with B3. But the B3 keys would change registered prompts that were never checked offline, and `model_when_verified` only acts on `junction_clear` recede phases.

**Safety fix.** `fix/safety-exemption-scope` (`8933863`) is the base delta, not part of this delta:

- `safety.py` `3011d9a7`, `safety_monitor_node.py` `c2cad302`, the fragment `08c06b51` and the merged `safety.yaml` `65fb84a3`;
- the same bytes at `9102ce9`, at `8933863` and in every kit; nothing to cherry-pick.

`scoped_clearing_exemption` and the 0.20 m `hard_contact_floor_m` are asserted on M4's startup line in three places, in all four kits:

- the deploy's KEY LINE check (installed loader + installed yaml);
- the chain's per-take `floor_or_key_not_armed` check;
- `cond_dmc.py` `floor_key_line`.

**Arm and condition checks added**, on top of the existing ones:

- `arm_expect.tsv` rows, evaluated by the deployed loader;
- `ib`, `scenario.json`:
  - `m5_line:` the full startup line `plan order condition plan_dispatch_order_source=model_when_verified prompt_plan_grammar_rules=True prompt_candidate_options=True prompt_plan_grammar_release_rule=True`;
  - `artifact_field:plan_dispatch_order_source:model_when_verified`;
  - `prompt_contains:` for both v3.5 sentences, the release sentence and the options header;
- `cv` / `ho` / `m5`: `m5_line_absent:plan order condition`, a new check kind.

### 10.4 Take Classification Rule (Fixed Before Take 1)

`take_class_dmc.py` (`cb70f53e`; tests `test_take_class_dmc.py` `78447e2e`, 13 synthetic cases) is in every kit. It reads only `m5.log`, `m4.log`, `decisions/<id>.json` and the bundle's `orchestrator.overlaid.yaml`, and prints exactly one class:

- **Unresolved failure:** not every robot logged `arrived at base goal` in `m5.log`.
- **VLM-driven execution:** resolved, and EVERY dispatched decision (an m5 `dispatch request=<id> command=<id>-...` line) is a `junction_clear` with `plan.provenance == vlm_verbatim` whose dispatched legs, read from the logs, match the plan:
  - the recede order is the m5 dispatch order of `<id>-junction-recede-<robot>`, each with an m4 `action=reverse`, and it equals the plan's `reverse` legs in order;
  - the yielder is the m4 `command=<id>-junction-cross ... action=yield`, and it equals the plan's `yield` leg;
  - under that decision m5 dispatched only the plan's phase commands (each recede, cross, release; no fallback or stage-2 command), and every recede and the cross resolved `completed`;
  - and the dispatched recede order differs from the grounder's default (chi) order for that snapshot.

  `plan.legs` alone is never trusted. A verbatim plan whose yielder was swapped at dispatch is not VLM-driven.
- **M3-default resolution:** every other resolved take, including any take with a non-qualifying dispatched decision.

The classifier only labels takes at the intersection. It cannot certify a non-`junction_clear` dispatch as VLM-driven, so `cv` and `m5` takes classify as M3-default or Unresolved, and `goal_check`'s facts stay the record there. Head-on keeps the rule of section 7 (no plan channel).

**The default order is in no log line.** When the model's order is dispatched, chi's order is not logged and not in the artifact. The classifier computes it offline (`rank_recede_candidates`, as the runtime does) and prints it as `DEFAULT_ORDER ... source=computed_offline`. It goes in the caption, never in the terminal pane.

Validation on the 22 recorded IB10 bundles (`ib10_live`, `ib10_safety`; verified):

- the computed order equals the m5-dispatched order in 18/18 chi-dispatched `junction_clear` decisions;
- log resolution equals the GT 0.3 m rule on 22/22 bundles (`ib10L_e09` and `ib10S_e02_armC_a1` are Unresolved);
- every resolved bundle is M3-default, `ib10S_e03_armA_a1` included.

### 10.5 Budget Split and Take Plan

Of the 12 VM-hour cap, enforced in `caps_dmc.tsv`:

| Scenario | Cap |
|---|---|
| `ib` | ≤ 2.5 h |
| `cv` | ≤ 2.5 h |
| `ho` | ≤ 1.5 h (was 2 h) |
| `m5` | ≤ 4 h reserved (was 5 h) |
| slack | 1.5 h |

At 1.5 h, head-on admits one 3 900 s invocation plus at most one more if the first is short (use `--episodes 2–3`). At 4 h, five-robot admits one 8 400 s invocation.

**Intersection.** The five valid episodes are split as follows:

- up to 3 takes with ER-2 under B3;
- then, only if none is VLM-driven, up to 2 takes with Sonnet 5.5. The owner allowed Sonnet or gpt-4o if needed (2026-11-15).

Open item: the kits hard-assert gemini / ER-2 (`cond_dmc.py` `a_backend_gemini`, `a_served_model`, `a_cond_backend`; the Gemini probe). A Sonnet take needs a separate kit arm before it can run. This is not built.

**Spend.** Offline API spend so far is roughly $1.6–2.0 of the $10 campaign API cap. Book it (`python3 ledger_dmc.py book-spend ib offline 2.00`) before take 1.

### 10.6 Checklist

- [x] Go / no-go: go for `ib` under B3, demo only (10.1).
- [x] Delta: files, fragment, expectations, commit `aa16b0d`, DELTA_IDs (10.3).
- [x] "VLM-driven" definition and the overridden / re-grounded case (10.4): a re-grounded, repaired or yielder-swapped plan is M3-default.
- [x] All four `test_dry_dmc.sh` re-run after the fill; new kit md5s in section 9.

### 10.7 Wall-Share Amendment (2026-11-15)

**What changed.** The per-scenario wall shares in `common/caps_dmc.tsv`, which this planning session set itself (10.5):

| Scenario | Old share | New share |
|---|---|---|
| `ib` | 9 000 s | 12 600 s |
| `cv` | 9 000 s | 9 000 s (unchanged) |
| `ho` | 5 400 s | 1 800 s |
| `m5` | 14 400 s | 14 400 s (unchanged) |
| Sum | 37 800 s | 37 800 s |

**Why.** The ledger refused intersection take 4: the kit's registered admission (prep 900 + take 3 000 + teardown 900 = 4 800 s) exceeded `ib`'s remaining share (9 000 − 5 014 = 3 986 s), although the measured one-take invocations used 1 559–1 849 s. Head-on finished after one resolved take (1 302 s used), so most of its share was idle. The new `ho` share (1 800 s) admits no further head-on invocation.

**Unchanged.** The campaign totals (43 200 s, $10), the 5 valid takes and 3 bring-up aborts per scenario, the admission logic (`ledger_dmc.py`) and every kit's per-take budget. The sum of the shares stays under the 43 200 s total.

**How.** `common/caps_dmc.tsv` edited (two values and the header comment); the `ib` and `m5` kits reassembled with the unchanged `common/assemble_dmc.sh` (a scratch reassembly before the edit was byte-identical to both kits). `kit_md5_dmc.txt` (VM files) is unchanged: `ib` `98a57626`, `m5` `89112a40`. `kit_md5_all_dmc.txt` is now `ib` `510882a6`, `m5` `8cd74255`. Both `test_dry_dmc.sh` end OK (`MIN_MAC_FREE_KB=3000000`, test only; the real ledger was not touched). On a ledger copy, `ledger_dmc.py admit ib 4800 0.25` now gives `ADMIT cap_sec=7586 ... next_take=4 valid=3`. The `cv`, `ho` and `ib_sonnet` kits were not reassembled and keep the old split in their own caps copies; this changes nothing for `cv` (its share is the same), and `ho` has finished. Sections 6 and 10.5 show the original split; this note supersedes them for `ib` and `ho`.

### 10.8 Take-Plan Deviations and Closing Note (2026-11-15)

Recorded after all live runs finished. The results are in `docs/reports/2026-11-15-demo-campaign-results.md`.

- **Intersection takes 4–5 ran on ER-2, not on Sonnet 5.5.** Section 10.5 planned up to 2 Sonnet 5.5 takes after 3 ER-2 takes if none was VLM-driven. The Sonnet arm was built and dry-tested (`ib_sonnet/kit`). But the offline Sonnet B3 check gave only 1 of 15 qualifying first triggers (about 13 % over 2 takes), because of the yielder gap. See `docs/reports/2026-11-15-vlm-order-channel-plan-check.md` section 11 and the results report section 3.4–3.5. Takes 4 and 5 therefore ran on the unchanged ER-2 `ib` kit, after the wall-share amendment of 10.7. Take 5 is the campaign's one VLM-driven take (results report section 7).
- **Convoy stopped after 3 takes, not 5.** All three takes were unresolved in the same way: the first yield ran as named, the model left out the queued robots, and the scene latched. No further convoy take was run, so 2 of its 5 valid takes went unused (ledger: `cv` valid 3, `next_take=4`; the ledger's `stopped` flag stays `no`). See results report section 5.
- **Five robots: one take.** `m5D_t01_a1` (seed position 21) was unresolved, 1 of 5 robots arrived, and it was used as the limitation demonstration (results report section 8). Section 4.4 allows one or two takes.
- Head-on ran 1 take, which resolved (results report section 6).

## 11. What Could Not Be Verified Offline

- The owner's hold of 2026-11-15 ("Do not start new VM runs or make paid API calls yet", recorded in `docs/reports/2026-11-15-ib10-recorded-demo.md`): the campaign approval is relayed by the session lead; confirm the hold is lifted before the first invocation.
- New hard pins never recorded on this VM: `reasoning/vlm/prompt_v2.py` `4804b237` and the head-on family yaml `49c7500b` (git 68e67b5 values). A mismatch stops the head-on kit at the snapshot, before anything changes.
- The VM's current state: `PINS_V3`, the installed maps for the head-on variant and `mapd_5_s1b`, and whether `mapd_5_s1b_seed21.yaml` and its USD are present (v4 restored them at 2026-11-13T15:45Z; the IB10 runs since may have changed this). The snapshot gates fail fast on a mismatch, before anything is changed.
- The RTF and recorder frame rates with two recorders, and the 5-robot recorder load.
- Gemini credit, quota and pricing on the day. Probes run before every take.
- That `untrunc` would rebuild a hard-killed segment. It is not installed, so such a segment is FLAGGED, not repaired.
- The bring-up abort rate with recording started after the gate. The 2026-11-14 abort's cause is not established.

---

## 12. Convoy Takes 4–5 with the Queued-Robot Hold (Amendment, 2026-11-15)

Written offline, before the VM start. Owner approval (2026-11-15): build the grounding fix that holds the queued robots, then run the two remaining convoy takes with it; on the next VM start, also run the one simulator-only test.

### 12.1 Purpose and Scope

- **Purpose.** Convoy takes 1–3 latched because the model's first yield named only robot_1 and robot_2, so robot_3 and robot_4 were released uncommanded (results report section 5). The fix (`fix/convoy-hold-queued-robots`, worktree v7o, commits `10b4807` `2037edf` `3ce6e8a` `d85d1ed`; report `docs/reports/2026-11-15-convoy-hold-queued-robots.md` there) lets M3 add every unnamed robot whose goal lies across the corridor to the yield's crossing order. These takes show that fix live, as demo footage.
- **Scope.** This is the demo campaign's convoy scenario (ledger key `cv`), takes 4 and 5 of its 5. It is **not** the registered convoy experiment (v7f `feat/convoy-live-resolution`). That experiment's VLM arm remains unrun; using the hold there would need its own amendment.
- **What the model still decides.** Strategy and yielder. The roles of robot_3 and robot_4 come from M3 when the model leaves them out, and every caption must say so.

### 12.2 What Is Deployed (Kit `cvh`)

The kit is `demo_campaign/cvh/kit`, assembled by the unchanged `common/assemble_dmc.sh cvh <v7o>`. It has its own VM home `~/dmc_cvh`, its own Mac directory, labels `cvH_t04_aK` and `cvH_t05_aK`, and tag `demo_campaign_cvh`. It books under the ledger key `cv`.

It is byte-identical to the `cv` kit in the scene, seed 42, the 260 sim-s horizon, the base overlay `cvl_l2on.yaml` (`7e3ab552`), the legacy grounding file (`63f50f91`), the scenario yaml (`9684b5fc`), live ER-2, the safety-exemption fix and the 0.20 m floor, the per-take budget (3 000 s) and the $0.20 per-take guard. `diff -r cv/kit cvh/kit` lists only the files below plus `README.md`, `test_restore_dmc.sh` (fork: fake Isaac interpreter, whole-tree md5 check), the Mac-only `mac_extra_dry.sh`, `mac_extra_gen_keyon.py` and `mac_extra_fixture.txt` (replacing `mac_extra_nofixture.txt`), the two `src/` test-step files and the kit md5 lists.

| Difference | Content |
|---|---|
| Runtime delta `runtime_delta_cvh/` (id `8fa937e6`) | The 7 runtime files of v7o HEAD `d85d1ed` that differ from the VM pin `68e67b5`. All 7 md5s equal the fix report's section 7 table (verified). |
| Overlay fragment | `grounding_hold_queued_crossers: true`. The effective overlay `e553edf4` is the base plus this line and the generator's comment line. |
| Arm check | The four inert B3 rows, plus `c.grounding_hold_queued_crossers True` and `c.prompt_held_robot_state False`. `want_arm` is unchanged. |
| Condition gate (`cond_dmc.py` fork, `scenario.json`) | `m5_line:` with the exact startup line `plan order condition plan_dispatch_order_source=chi prompt_plan_grammar_rules=False prompt_candidate_options=False grounding_hold_queued_crossers=True` (replacing `m5_line_absent:plan order condition`), and the new `first_queued_hold` check (12.3). |
| `env_dmc.sh`, `run_dmc.sh` forks | VM home from `VM_HOME_KEY`. The pull also excludes the test step's scratch and target directories. |
| `restore_dmc.sh` fork | The m5v restore (orphan bytecode of added modules; none are added here), plus removal and verification of the test step's two directories. |
| Ledger and caps copy | The m5v `ledger_dmc.py` (per-scenario spend cap). Caps are the amended shares (12.4) plus `usd_cv` `0.6791`. |
| Deploy check | The legacy load (as `cv`), then the non-fatal simulator-only test step (12.5). |

Delta files:

| File | md5 | Kind |
|---|---|---|
| `reasoning/rag/command_grounder.py` | `691d1730dfa141149284c9eaae44b608` | live |
| `reasoning/rag/scene_geometry.py` | `eda27ce7525e2bbb8f5fbe2bf854d296` | live |
| `reasoning/vlm/models.py` | `52cba14c5f94b50567f1766cbcd4ff17` | live |
| `reasoning/vlm/prompt_builder.py` | `f2f33b778360c5a0f4a6cd82b10c42b5` | live |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `575e7abb577650108a54e552623c9d80` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `ad9a46c65dc95e6b968e976d25c0ac8d` | pkg:swarm_orchestrator |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `76185f21e84a6c1ab43a3d3789291813` | pkg:swarm_orchestrator |

Kit md5s: `kit_md5_dmc.txt` (VM files) `f2356ee8`, `kit_md5_all_dmc.txt` `8c384150`. The kit lives under the git-ignored `data/logs/`, so this section is its committed record.

### 12.3 Checks

- **Before every take** (unchanged mechanism): the deployed loader's arm check with the six delta rows; the pins in run mode; the probe.
- **After every take** (condition gate; a failure stops the chain and is never retried):
  - every existing `cv` check;
  - the exact startup line above;
  - `first_queued_hold` on the **first** decision artifact by `scene.stamp`. It requires:
    - `grounding_mode == legacy`;
    - either `grounding_queued_crossers_added == [robot_3, robot_4]` with both `crossing_order=augmented:<id>:goal_across_corridor` tags, or the key absent and `decision.involved_robots` naming all four;
    - `dispatched_robot_ids` covering all four;
    - a `queued crosser hold:` edit for each added robot whose leg in the model's own plan (`decision.proposed_plan`) is not `cross`, and every added robot's final plan leg `cross`.
  - "Not `vlm_verbatim`" is **not** required.
  - Later artifacts carry no requirement.
- **Gate tested offline on real key-on artifacts.** `mac_extra_dry.sh` generated them with v7o's own M5 pipeline and artifact writer from takes 1–3's recorded first decisions, plus two variants: the model naming all four, and a plan already saying `cross`.
  - All 5 pass all 23 checks.
  - Each of 10 single defects fails exactly the matching check(s).
  - The gate's startup line equals v7o's `plan_order_status_line()` on the effective overlay.
- **Dry tests (verified by running):**
  - `test_dry_dmc.sh <v7o>` ends `TEST_DRY_DMC cv OK` (`MIN_MAC_FREE_KB=3000000`, test only).
  - `test_restore_dmc.sh` passes 9 cases. In the real-delta case, the whole fake repo tree (371 files) equals its pre-snapshot md5 list after the restore, and the test step's directories are removed while their logs are kept.
  - The fix's `tests/unit/test_queued_crosser_hold.py`: 51 passed. The full unit suite was not re-run; the fix author ran it on this tree.
- **Label of a resolved take.** "Resolved — grounder held the queued robots; model chose strategy and yielder". If the model itself named all four, the report says so (the hold then added nothing). A take is never labelled "VLM-driven". The take classifier is not used for convoy yields.

### 12.4 Caps and the Second Wall-Share Amendment

The shares in `common/caps_dmc.tsv` are this planning session's own split of the owner's 43 200 s cap. `cv`'s remaining share (9 000 − 4 829 = 4 171 s) is below the kit's per-invocation admission (prep 900 + take 3 000 + teardown 900 = 4 800 s), as the intersection's was in 10.7. The finished scenarios shrink to just above their ledger use:

| Scenario | Used (ledger) | Old share | New share |
|---|---|---|---|
| `ib` | 8 239 s | 12 600 s | 8 400 s |
| `cv` | 4 829 s | 9 000 s | 12 600 s |
| `ho` | 1 302 s | 1 800 s | 1 400 s |
| `m5` | 3 833 s | 14 400 s | 4 000 s |
| `m5v` | 4 144 s | 9 000 s (its own copy) | 4 200 s |
| Sum | 22 347 s | — | 30 600 s (≤ 43 200 s) |

- **Unchanged.** The campaign totals (43 200 s, $10), 5 valid takes and 3 bring-up aborts per scenario, the admission logic, and every kit's per-take budget. The campaign-level check still binds: 22 347 s used of 43 200 s.
- **How the files changed.**
  - `common/caps_dmc.tsv` edited: four values, one added `wall_sec_m5v` row and the header comment; md5 now `d7941db7`.
  - The `m5` kit was reassembled. A scratch reassembly before the edit was byte-identical. Its `kit_md5_dmc.txt` is unchanged (`89112a40`) and `kit_md5_all_dmc.txt` is now `d57688e5`.
  - Its `test_dry_dmc.sh` stops at step 2 (git preflight). This is pre-existing and unrelated to the caps: v7j HEAD's M5/M2 files have moved past `runtime_delta_inert` since the held-robot prompt work. The same preflight also refuses any `m5` invocation.
  - The `ib`, `ho`, `cv`, `m5v` and `ib_sonnet` kits keep their old copies. Each kit's own `ledger_dmc.py admit` on a ledger copy (before the retake): `ib`, `ib_sonnet`, `cv`, `m5` and `m5v` refuse (valid-take or wall limit). `ho`'s stale copy (5 400 s) still admits (`cap_sec=4098`), but `ho`'s git preflight, like `ib`'s and `cv`'s, refuses on the current v7j HEAD (verified), so no stale kit can start the VM. (Corrected 2026-11-15 after the retake; the first wording said every one refuses on its own limit.)
- **Admission on a ledger copy.** `cv` gives `ADMIT cap_sec=7771 spend_left=0.4 aborts_left=3 next_take=4 valid=3`, and `ib`, `ho`, `m5` and `m5v` refuse.
- **Spend.** The ledger total is $2.7677 of $10. The brief's ≈ $3.2 includes offline checks that were not booked. This retake's own guard is $0.40: `usd_cv` 0.6791 = `cv`'s booked $0.2791 + $0.40, read by this kit's ledger only, on top of the unchanged $0.20 per-take guard.

### 12.5 Simulator-Only Test Step (Non-Fatal)

- **Test.** The one `pxr`-dependent test, `test_scene_boxes_match_usd_builders_when_pxr_available` in v7m `feat/gt-contact-logging` `b5eaee5` `tests/unit/test_contact_geometry.py` (`533811c5`). It checks USD-builder parity: the geometric box set against what `scenario_builder` and `warehouse_builder` author.
- **Where.** In the deploy check, after the legacy load and before any take, so it adds a few minutes of VM time once. It never touches `$R`.
  - **Scratch copy.** It copies the VM's pinned `isaac/__init__.py` and `isaac/vgu_sim/*.py`, plus v7m's `contact_geometry.py` (`77e862ce`) and the test, into `~/dmc_cvh/pxr_test/tree`. `isaac` is a regular package, so a second `PYTHONPATH` root would not merge. The md5s of the pinned files used are logged.
  - **pytest.** It runs `python.sh -m pip install --no-cache-dir --no-compile --target ~/dmc_cvh/pytest_target pytest==8.3.4` with Isaac's own `python.sh` (build_dmc.sh's interpreter), as ubuntu. Nothing is installed into Isaac's site-packages; a listing md5 before and after is logged.
  - **Run.** `PYTHONPATH=<target>:<scratch>:<repo>`, `-p no:cacheprovider --noconftest --basetemp <scratch>/bt -k <the test>`, with every command under `timeout`.
- **Logs.** In `~/dmc_cvh/pxr_test/`, pulled into `cvh/vm/pxr_test/`.
- **Restore.** The restore removes the scratch and target directories and verifies they are gone.
- **Failures.** A failure, a skip (no `pxr`) or no network is recorded and never aborts the takes. A skip is not a pass.

### 12.6 Stop Rules

- **Invocations.** At most two (`bash run_dmc.sh --episodes 1` each). After each, on every path, the VM must be verified TERMINATED.
- **After take 4.** Stop if the convoy resolved (all four arrived by ground truth). Otherwise run take 5 only if take 4's failure is not a harness or kit fault that would simply repeat (at most one kit fix, dry-tested first).
- **Expected outcome.** A take where the model picks robot_1 as yielder is expected to latch, per the scene's design. That is a valid result and is kept as is.
- **GPU stockout.** Retry the same VM's start only.
- **Never.** No weakened checks, no hardcoded plans, no ground-truth edits, no edits to pulled bundles, no `rsync --delete`, no push.
