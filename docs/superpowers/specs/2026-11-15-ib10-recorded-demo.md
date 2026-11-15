# IB10 Recorded Demo (Demo Video Only)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: registration of a two-episode recorded demo on the IB10 four-robot `intersection_bottleneck` scene, written offline before any VM use.

---

## 1. Purpose and Status

The owner's instruction (2026-11-15), verbatim:

> "spend cap is up, Do one separate demo run with recording on, for the video only"

This run makes footage for the thesis demo video. **It is not experiment data.**

- The two episodes are never counted and never pooled with any experiment: not prereg-v3, not IB10 2026-11-13 (`ib10_live`), not IB10 2026-11-14 (`ib10_safety`), not the convoy experiment.
- They are labelled demo everywhere: tag `ib10_demo`, labels `ib10D_*`, kit `ib10_demo`, VM directory `~/ib10d`.
- **Recording may change the real-time factor (RTF) and the timing of the stack.** Without recording, the 2026-11-14 episodes ran at about 0.30. The recorders add CPU load and DDS subscribers, and stage 5 of `fc_launch.sh` adds about 15 wall-s (a 12 s `ros2 topic hz` plus a 3 s sleep) before the Nav2 bring-up. No timing from these episodes (RTF, trigger and dispatch times, time to resolution) is comparable with any experiment.
- The facts of each episode are reported (section 7) only to describe what the video shows.

---

## 2. Episodes

| Slot | Label | Arm | Overlay |
|---|---|---|---|
| D1 | `ib10D_d1_armA_a<n>` | Layer 2 on, live `gemini-robotics-er-2-preview` | `ib10d_l2on.yaml` = `0196f1e8`, the 2026-11-13/14 Arm A bytes |
| D2 | `ib10D_d2_armB_a<n>` | Layer 2 off: no detection, no M2/M3 call, no dispatch; the robots stay frozen in the jam | `ib10d_l2off.yaml` = `14c19b7b`, the 2026-11-13 Arm B bytes (Arm A + `reasoning_enabled: false`) |

- **Order.** One invocation (`run_ibd.sh demo`) runs D1, then D2. There is no smoke/follow split.
- **Labels.** Labels carry an attempt suffix `_a<n>`, because a retry needs a new bundle directory.
- **Arm B source.** The Arm B definition and gate are the 2026-11-13 ones: `feat/ib10-live-resolution:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md`, "Overlay, Arm B" and "Arm B" rows, and that kit's `cond_ib.py`.
- **D2 always runs.** If D1 does not resolve (it failed 1 in 11 VLM-on episodes this week), D2 still runs and the facts are reported. Nothing is re-run automatically; a re-take is the owner's call.
- **D1 failures that stop the chain.** A harness or condition-gate failure in D1 (restore, `logs saved to`, key line, condition gate) stops the chain, and D2 does not run. Only non-resolution lets D2 proceed.
- **Retry.** A Nav2 bring-up abort or a map start-up `PROBLEM` (section 4) retries the slot once (`MAX_ATTEMPTS=2`).

---

## 3. Runtime (Exactly the 2026-11-14 Run)

| Item | Value |
|---|---|
| Base | The v3 pin on the VM, git `68e67b5`. |
| Code delta | `safety.py` `3011d9a7` and `safety_monitor_node.py` `c2cad302` from `fix/safety-exemption-scope` (`8933863`). |
| Safety config | Merged `safety.yaml` `65fb84a3` (the 0.20 m floor file `c41913f0` plus `scoped_clearing_exemption: true`, `waiver_closing_tolerance_m: 0.05`, `waiver_closing_readings: 3`), byte-identical to the 2026-11-14 file. |
| Key assertion | Before the condition gate of each episode, the chain requires M4's startup line to end in `hard_contact_floor_m=0.2 exempt_actions=reverse,yield scoped_clearing_exemption=True waiver_closing_tolerance_m=0.05 waiver_closing_readings=3`. |
| Scene | `intersection_bottleneck.yaml` `042802d6`, 300 sim-s horizon, seed label 42. The USD is built fresh. |
| Grounding | `config/rag.yaml` (derived), unchanged. |
| Nav2 bring-up | Parallel. |
| Recording | `RECORD=1` (section 5). This is the only difference from the 2026-11-14 runtime, and it changes no runtime file. |

The kit deploys and restores the delta exactly as the 2026-11-14 kit did: snapshot, deploy, per-episode overlay, and a restore to `PINS_V3 OK`.

---

## 4. Guards (All of the Base Kit's, Plus)

**Kept from the base kit:**

- kit md5 check;
- git preflight (runtime delta = the 3 fix-branch files; `fc_launch.sh` `055db01e` and `record_topic_video.py` `90aa8971` pinned);
- snapshot;
- deploy and verify of the 3 safety files;
- arm check through the deployed loader (Arm A `True True True 0.33 -1 config/rag.yaml True`, Arm B `False False False 0.33 -1 config/rag.yaml True`);
- the key-line gate;
- per-episode restore;
- the EXIT trap: restore, pull (`rsync -a`, never `--delete`), stop, verify TERMINATED;
- `RESTORE_FAILED_*` / `VM_NOT_STOPPED_*` markers;
- the VM-side dead-man;
- stockout: retry the same VM's start only.

**Condition gate (`cond_ibd.py`):**

| Arm | Checks |
|---|---|
| Both | `tag=ib10_demo`, `record=1`, `confirmatory=0`, the arm, the arm's overlay; `ARM_CHECK.txt`; the key line; the handoff guard; an M5 session line; a non-empty scene log. |
| A | No Layer-2-off line; the release-lane remedy (0.33 m pull-off); `backend=gemini`; at least one artifact; every artifact `gemini` (both fields); the served model `gemini-robotics-er-2-preview` named by at least one artifact and by every artifact that carries a decision; tokens > 0; no `mock_mode`; a probe line ending `rc=0`. |
| B | `backend=gemini`, no mock file; exactly one Layer-2-off line; 0 artifacts, 0 analyses, 0 dispatch lines; no cost log; no probe line. |

**Map start-up gate.** `startup_check_ibd.py` (the convoy kit's gate, logic unchanged) runs after every episode. A `PROBLEM` verdict is a bring-up abort, and the slot is retried once.

**Gemini probes.** There are two one-token probes:

- an early probe right after the kit lands, before anything on the VM is changed;
- the base kit's probe before D1.

HTTP 429/402 (spend cap, quota, billing) or any other probe error aborts. After the early probe, that means nothing runs, the restore finds nothing to undo, and the VM is stopped.

**Caps:**

- Wall clock: 2 h cumulative, VM start to TERMINATED (`wallclock_ledger.tsv`). A teardown reserve of 15 min. An episode is admitted only if its 45 min budget fits before the chain deadline, so D2 runs only if D1 ends by about T0 + 3600 s.
- Spend: $0.25 (D1 only).
- One invocation: the driver refuses when demo bundles already exist.

---

## 5. What Is Recorded

| Stream | Topic | Recorder | Output in the bundle | Segments |
|---|---|---|---|---|
| Annotated | `/perception/annotated_frame` (M1's overlay: status-coloured boxes, labels, velocity arrows) | `fc_launch.sh` stage 5 (`RECORD=1`); fps stamped from a 12 s `ros2 topic hz` | `rec/annotated_NNN.mp4`, log `rec.log` | 2000 frames |
| Raw camera | `/camera/image_raw` (the overhead camera, no overlay) | `rawrec_ibd.sh` (kit side): the same pinned `scripts/record_topic_video.py`, launched exactly as `fc_launch.sh` launches its own recorder (`docker exec -d`, same ROS environment and DDS profile, `best_effort`). It starts after the Nav2 bring-up gate line, so never inside the load-sensitive bring-up window. | `rec/camera_raw_NNN.mp4`, log `rec/camera_raw_rec.log`; the measured topic rate is in `rawrec.log` | 500 frames |

- **Format.** Both are mp4v (MPEG-4 Part 2) with the recorder's clock overlay `t=<header.stamp, sim s>  f=<frame>`.
- **Stopping.** At the end of stage 9, both get SIGTERM: from `rawrec_ibd.sh` and from `fc_launch.sh`'s stage-10 `stop_recorder_cleanly`, whose pattern matches both processes. `REC_STOP_WAIT_SEC=120`.
- **Hard kills.** Segmenting bounds what a hard kill can lose.
- **Durations.** `REC_SEC=3300`. That is the annotated recorder's own duration from stage 5 and the M5 tail cap, sized for an RTF well under 0.30.
- **Raw-camera density.** The raw recorder subscribes `best_effort`, so as not to load the camera publisher that M1 depends on. The 2026-09-16 run G recorded this topic at 1.73 Hz against 5.2 Hz measured, so the raw video may be sparse. The annotated stream carries the timing.
- **Recordings on the VM.** They stay on the VM under the repo's `data/logs/fc_run_<stamp>/`, a directory `fc_launch` creates in every run. The restore does not touch it, and it is not a pinned file.

**Frame-to-time mapping (`video_check_ibd.py`).** The recorder cannot dump per-frame stamps. For each video the kit writes `rec/<stream>_timemap.json` with:

- the quoted recorder lines: the stamped fps, `first frame: … header_stamp=… wall_clock=…`, the 50-frame progress lines, the segment lines and `WROTE … frames=<F> secs=<S>`;
- the measured topic rate;
- the achieved mean fps;
- the RTF from `m5_scene.jsonl`;
- a linear estimate of sim time per frame.

The burned-in overlay is authoritative. After the pull, a Mac-side step decodes each frame's overlay. The overlay is drawn with a fixed OpenCV Hershey font at a fixed position, so it can be matched against glyphs rendered the same way. The step writes a renderer map `rec/<stream>_framemap.json` (`{"frame_sim_times": [...]}`, 0-based global frame index) next to the source lines. Frames it cannot decode are left out, and the step falls back to `anchors`. Overlay values read off the stills by eye are a cross-check.

---

## 6. Kit

`data/logs/vm_runs/ib10_demo/kit/` in this worktree (gitignored, not committed). It is adapted from:

- the IB10 safety kit (v7d);
- the 2026-11-13 Arm B overlay and gate (v7a);
- the convoy kit's map start-up gate (v7f).

All three source kits are frozen evidence and were only read.

| Item | md5 |
|---|---|
| `kit_md5_ibd.txt` (VM-side files) | `35a302ca37f55196803c8c6bf2acbc41` |
| `kit_md5_all_ibd.txt` (every file) | `8dcdb96b3af8743496953b5ea41104f5` |
| `ep_run_ibd.sh` | `59b00fdef41c14857ff6cfec86ecbea8` |
| `chain_ibd.sh` | `ce591c6fe639a0d2dd5cb5cc8e4de356` |
| `rawrec_ibd.sh` | `8124add8a6ffb5acd99fda3db2d21486` |
| `cond_ibd.py` | `428e5a109a65b9d7db37aa20ad45eae1` |
| `run_ibd.sh` | `22dbe366159456eca47c33b02c0d852d` |
| `video_check_ibd.py` | `7615414545008dd155cdfc69797ff488` |

**Offline dry test.** `bash test_dry_ibd.sh` ended `TEST_DRY_IBD OK` before any VM use. It covers:

1. syntax checks and kit md5s;
2. the git preflight;
3. the key line, plus both overlays regenerated and parsed through the loader;
4. the episode table and slot resolution;
5. every driver DRY_RUN path: the early-probe 429 aborting before the snapshot, step, chain, pull and restore failures, stockout, free space, the 2 h ledger, once-only, tamper;
6. the admission table;
7. the fake-VM restore test, both arms' gates on temp copies of real bundles (21 cases), the scorer regression over the 2026-11-13 bundles, and the video check on synthetic mpeg4 segments;
8. the real `fc_launch.sh` in DRY_RUN with `RECORD=1`; the recorder process patterns; and `rawrec_ibd.sh` run for real on PATH shims over its three stop paths.

---

## 7. Reported After the Run

`docs/reports/2026-11-15-ib10-recorded-demo.md`, marked demo / not experiment data. It reports:

- **Gates:** the gates of each episode.
- **Timing:** t0 and onset.
- **D1 decision:** the analyses, the decision and its provenance.
- **Outcome:** arrivals, resolved, GT minimum distance, floor stops and key-on counters.
- **RTF:** the measured RTF with recording, against about 0.30 without.
- **Run bookkeeping:** spend, the restore lines and the VM status.
- **Videos:** paths, sizes, codecs, frame counts, durations, topics, time maps, and stills looked at. An H.264 copy is made where the Mac can produce one, frame-for-frame with no re-timing; the originals stay untouched.

---

## 8. Amendment (2026-11-15): Convoy Demo Episodes D3 and D4 (Prepared, on Hold)

The owner's addition (2026-11-15), verbatim:

> "add the convoy to the demo run"

It was written and committed before any convoy demo episode ran. On the same day the owner put new VM runs and paid calls on hold: "Do not start new VM runs or make paid API calls yet." The convoy demo kit is therefore prepared and dry-tested only, and **D3/D4 have not run**.

**Episodes.** Scene `convoy_counterflow_slip`, 4 robots. These are demo episodes like D1/D2: never counted, never pooled.

| Slot | Label | Arm |
|---|---|---|
| D3 | `cvD_d3_armA_a<n>` | Layer 2 on, live `gemini-robotics-er-2-preview`, overlay `cvl_l2on.yaml` (`7e3ab552`) |
| D4 | `cvD_d4_armB_a<n>` | Layer 2 off, overlay `cvl_l2off.yaml` (`8457f756`) |

**Settings.** The registered convoy experiment's settings apply unchanged: `vgu-vlm-swarm-v7f/docs/superpowers/specs/2026-11-14-convoy-live-resolution-experiment.md` and its kit `v7f/data/logs/vm_runs/convoy_live/kit/`, both read only. Those settings are:

- runtime 68e67b5 plus the 3 safety files, key on (0.05 m / 3 readings), floor 0.20 m;
- the legacy grounding file `config/grounding/cvl_convoy_legacy.yaml` (`63f50f91`), installed by the kit for both arms and removed by the restore;
- the convoy USD build and the map check;
- the 260 sim-s horizon and the 120 wall-s release;
- the map start-up gate;
- the registered Arm A and Arm B definitions and condition gates, with only `record=1` changed.

The only addition is the recording path of section 5. The kit is a demo variant of that kit:

- kit directory `data/logs/vm_runs/convoy_demo/kit/`;
- VM directory `~/cvd`, never `~/cvl` or `~/ib10d`;
- nothing is written in the v7f worktree, and its `SMOKE_ACCEPTED`, attempts and ledger files are untouched.

**Disclosure.** D3 would be the first convoy episode ever run with a live model. Its outcome would be seen before the registered convoy experiment's VLM-on arm runs. It is a disclosed pre-experiment demo episode. It is not part of that experiment, and it must not be used to change that experiment's registered rules.

**D3 may not resolve.**

- The scene has never run live.
- The model may answer something M3 cannot ground here, or name only two robots.
- If D3 does not resolve, D4 still runs, the facts are reported, and there is no automatic re-take.

**The registered standoff-gap / 0.20 m floor issue applies.** The report will give:

- the robot_1–robot_2 standoff gap and whether the floor fired in D3;
- the model's answer, strategy, robots named, crossing order and plan provenance;
- whether M3 grounded it, and with what command and phases;
- arrivals, and resolved or where it stopped;
- floor stops;
- the goal-stack minimum against the 0.45 m latch;
- dispatch time against the 120 wall-s release;
- the RTF with recording.

**Caps.**

- Wall clock: 3.5 h cumulative for the whole demo. `run_cvd.sh` sums its own ledger and the IB10 demo's.
- Spend: $0.50 for the whole demo. The convoy demo is capped at $0.25 with the registered $0.20 per-episode guard.
- A Gemini probe runs early and again before D3.
- One invocation, run after the IB10 demo invocation has been restored (`PINS_V3 OK`) and stopped.

**Kit md5s.**

| Item | md5 |
|---|---|
| `kit_md5_cvd.txt` | `035c19aab699e1ddf50ce1c92dfb72f2` |
| `kit_md5_all_cvd.txt` | `494475fd91cfa41fc88052d155a4ed00` |

`bash test_dry_cvd.sh` ended `TEST_DRY_CVD OK`. It combines the registered kit's sections 1–3, 7a–7c and 9 with the IB10 demo kit's sections 4–6, 7d, 8 and 8b.

**Launch, only when the owner lifts the hold:**

```bash
cd data/logs/vm_runs/convoy_demo/kit && bash run_cvd.sh demo
```
