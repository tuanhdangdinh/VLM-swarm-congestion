# Demo Campaign: Recorded Demo Videos for Four Scenarios

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: registration of the owner-approved demo-video campaign (four scenarios, one VM, 12 VM-hours, $10), written offline before any VM use. The kits are prepared and dry-tested only; nothing has run.

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
| Demo runtime delta | An INPUT (section 10). The default, as committed, is EMPTY: DELTA_ID `ae8740a08dfc178769dbcfa64a645c4b` (`empty=1`). |
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

**Demo goal.** The intersection resolves (GT arrivals 4/4) under a live VLM decision. `goal_check` prints:

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

- arrivals and resolved;
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

Arrivals are reported, but 2/2 is NOT required.

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
- `REC_SEC` 5400, an admission budget of 6000 s, and a per-take guard of $0.50.

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
- `--duration-sec` = `REC_SEC − 60`.

**Start (1c).** Both recorders start right after fc_launch logs `first stack launch -> gate passed`, never during the parallel or sequential Nav2 bring-up. The evidence that nothing is lost (verified offline):

- **No motion before M5.** In all 22 IB10 bundles of 2026-11-13/14 (v7a and v7d), the first robot displacement over 5 cm (GT) comes at or after M5's first scene record. That happens 0.1–1.3 sim-s later, except one map-server-abort bundle at +24 sim-s. Robots cannot move before M4 and M5 start, and fc_launch starts them only after the gate line (stages 7 and 8, `fc_launch.sh` lines 880–938).
- **Margin.** M5's session line comes 10.5–15.0 wall-s after the gate line (median 12.7 s; 22 bundles).
- **Recorder start time.** The 2026-11-14 recorder took 3.5 s from `docker exec` to its first frame (17:45:48 → `wall_clock=1794678351.519`).
- **Conclusion.** Both recorders are up at least about 5 s before M5 starts, and so before any motion. What is not recorded is the static bring-up: robots at spawn, sim time roughly 7–15 s.
- **Load avoided.** The old stage-5 recorder ran inside the bring-up window that aborted on 2026-11-14. It achieved only 350 frames in 149 s (≈2.3 fps) against 9.3 Hz measured. Whether it caused the abort is unknown (one failure).

**Stop (1b).** Both recorders get SIGTERM and a bounded wait (`REC_STOP_WAIT_SEC` 30 s) on the FIRST of:

- Isaac's process gone. fc_launch then idles 45 s before its container restart (`isaac_wait_exit_or_cap`), so on the normal path the trailers are always written.
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
| Wall clock, per scenario | `ib` 2.5 h, `cv` 2.5 h, `ho` 2 h, `m5` 5 h |
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

**Reading of "up to 3 startup attempts per scenario in total".** The kits read it as at most 3 BRING-UP ABORTS per scenario, counted across invocations by the ledger. At the third, the chain logs `BRINGUP BUDGET EXHAUSTED`, the scenario stops and is reported, and the driver refuses further invocations of it. The other reading is "at most 3 launches per take". It can be enforced by passing `--episodes 1` and stopping a take by hand. The session lead should confirm which reading the owner meant.

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
  - **VLM-driven**;
  - **M3-default** (the dispatched commands were M3's default plan: `provenance=m3_default`, or for the intersection no counterfactual difference);
  - **unresolved**.

  "VLM-driven" may be used only as section 10 defines it.
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
| `ib` | `b0b43ee9136dd3caeeaa329e86931cd5` | `a5c8879ce7b7ea82d350c5215fbd42f4` | `0196f1e8` | `TEST_DRY_DMC ib OK` |
| `cv` | `9aa182ba5ec2408ed2ef08ae10713ed2` | `fcdd2d0473ca63d16e134ec83c04dd25` | `7e3ab552` | `TEST_DRY_DMC cv OK` |
| `ho` | `d2077a9980d98c90c5beedcf4628a905` | `0d7c535ffe4649a5ea9604cc1c2f4898` | `3929a087` | `TEST_DRY_DMC ho OK` |
| `m5` | `c2e4ea05b822cbcd629a46c56e770cde` | `ac16ad9d6f3ccc27ae9191214052038e` | `09bc16e6` | `TEST_DRY_DMC m5 OK` |

The shared files are the same in every kit: `run_dmc.sh` `290ca269`, `chain_dmc.sh` `6a16ac95`, `ep_run_dmc.sh` `25203d1b`, `recmgr_dmc.sh` `c9a30e88`.

**Wall estimates (inferred).** Each invocation costs about 10 min of prep (start, push, probe, snapshot, USD build, deploy) plus 3–5 min of teardown. The recorded RTF is unmeasured. Five takes per scenario do not fit in the sub-caps; the sub-caps fit about 2–3 takes.

| Scenario | Unrecorded take | Recorded take (guess) | Per invocation | Fits in the sub-cap |
|---|---|---|---|---|
| `ib` | 18.5–19.5 min | 25–35 min | 40–50 min | 2 one-take invocations, or 3 takes with `--episodes`, in 2.5 h |
| `cv` | 17–23 min (registered estimate) | 25–35 min | 40–50 min | 2–3 takes in 2.5 h |
| `ho` | ~13–18 min | 18–25 min | 30–40 min | 2 invocations, or 3 takes with `--episodes 3`, in 2 h |
| `m5` | 53–65 min | 60–100 min | 75–115 min (more if the USD must be rebuilt) | 2 invocations in 5 h |

The admission budgets are:

| Scenario | Prep + take budget + reserve |
|---|---|
| `ib` | 4 800 s |
| `cv` | 4 800 s |
| `ho` | 3 900 s |
| `m5` | 7 800 s |

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

> **PLACEHOLDER — to be filled by the session lead from the separate VLM-plan decision-path investigation, before any VM use.**

- [ ] Go / no-go for the campaign.
- [ ] The demo runtime delta: files (relpath, md5, kind), overlay fragment, deployed-loader expectations, the commit that carries them on `demo/campaign-kits`, and the resulting DELTA_ID. Empty means the 2026-11-14 runtime: `ae8740a08dfc178769dbcfa64a645c4b`.
- [ ] The definition of **"VLM-driven"** used in section 7: which artifact or `goal_check` facts make a take VLM-driven. Examples: a dispatched plan whose provenance is not `m3_default`, or an intersection counterfactual difference from M3's default. Also state how a take where M3 overrode or re-grounded the model is labelled.
- [ ] Re-run all four `test_dry_dmc.sh` after the delta is filled; record the new kit and overlay md5s.

---

## 11. What Could Not Be Verified Offline

- The VM's current state: `PINS_V3`, the installed maps for the head-on variant and `mapd_5_s1b`, and whether `mapd_5_s1b_seed21.yaml` and its USD are present (v4 restored them at 2026-11-13T15:45Z; the IB10 runs since may have changed this). The snapshot gates fail fast on a mismatch, before anything is changed.
- The RTF and recorder frame rates with two recorders, and the 5-robot recorder load.
- Gemini credit, quota and pricing on the day. Probes run before every take.
- That `untrunc` would rebuild a hard-killed segment. It is not installed, so such a segment is FLAGGED, not repaired.
- The bring-up abort rate with recording started after the gate. The 2026-11-14 abort's cause is not established.
