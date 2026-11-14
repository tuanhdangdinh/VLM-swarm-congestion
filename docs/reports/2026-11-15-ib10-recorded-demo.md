# IB10 Recorded Demo: Results (Demo Only, Not Experiment Data)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: outcome of the one demo invocation (D1 harness failure at Nav2 bring-up; D2 not run); the convoy demo is prepared but on hold.

---

## 1. Summary

**This is demo footage, not experiment data.** Nothing here is counted or pooled. Registration: `docs/superpowers/specs/2026-11-15-ib10-recorded-demo.md` (`7bc2952`; convoy amendment `fb60dd3`).

The one invocation (`run_ibd.sh demo`, 2026-11-14 17:39:50Z) produced **no usable video and no episode**. In order:

1. D1 (Arm A) aborted during Nav2 bring-up, before M4 and M5 started.
2. The chain stopped on the key-line gate (`harness_fail:floor_or_key_not_armed`), so D2 was never started.
3. The VM was restored (`PINS_V3 OK`), the data was pulled, and the VM was stopped and verified TERMINATED.
4. The convoy demo (D3/D4) was not started: the owner's hold of 2026-11-15 ("Do not start new VM runs or make paid API calls yet") arrived while D1 was running.
5. In line with the brief, the episode was not re-run.

---

## 2. What Happened in D1 (`ib10D_d1_armA_a1`)

| Item | Fact (verified from the pulled bundle) |
|---|---|
| Probes | Two one-token probes, both `http=200 verdict=OK model=gemini-robotics-er-2-preview`: the early one at 17:41:01Z and the one before D1 at 17:44:42Z. |
| Preparation | Snapshot, USD build, deploy (key line OK) and overlay/parse all OK by 17:44:34Z. |
| Stage 5 | M1 live at 17:45:43. `annotated_frame measured rate 9.301 Hz -> stamping fps=9.301`. The annotated recorder started; its first frame was at `header_stamp=7.567 wall_clock=1794678351.519`. |
| Nav2 | 4 stacks launched 17:45:51–17:46:00 (parallel). |
| Failure | robot_1's `lifecycle_manager_navigation` logged `Configuring controller_server` and then nothing more. `controller_server` logged `failed to send response to /robot_1/controller_server/change_state (timeout)`. `/robot_1/navigate_to_pose` therefore never appeared. `wait_action` timed out after 150 s, and `fc_launch.sh` exited at 17:48:34 through its abort cleanup: Isaac stop flag, backend restore, container restart. |
| Classification | The 150 s `wait_action` timeout is not a `NAV2_BRINGUP_FAILED` line, so the chain did not treat it as a bring-up abort to retry. The map start-up check was OK, because robot_1's `map_server` did activate. M4 never started, so the key-line gate failed and the chain stopped as designed. |
| Cost | 0 analyses, 0 artifacts, `est_usd=0.0000`. The only paid calls were the two probes. |
| Episode restore | `RESTORE OK`. |
| GT | No robot moved; the frozen scorer raised `no robot ever moved`. |

**Failure class.** A Nav2 lifecycle `change_state` response was dropped during the parallel 4-stack bring-up. It is the same class of failure as the IB10 safety e02 a1 `map_server` configure response (2026-11-14). The `fc_launch.sh` header documents the parallel-bring-up timing sensitivity.

**Did recording cause it? Inferred, not verified.** fc_launch's own annotated recorder was running during the bring-up. It is started in stage 5, before Nav2. The kit's raw recorder did not run: it waits for the Nav2 gate line and logged `launch ended before the Nav2 gate; raw recorder NOT started`. Recording load may have contributed, but one failure cannot show it.

---

## 3. Recordings

| File | Size | Frames | State |
|---|---|---|---|
| `data/logs/vm_runs/ib10_demo/runs/ib10D_d1_armA_a1/rec/annotated_000.mp4` | 2,883,628 B | 350 written (per `rec.log`), 0 readable | **Unplayable.** `ffprobe` reports `moov atom not found`. |
| `camera_raw_*.mp4` | none | — | Never started (see above). |

**Why the annotated file is unplayable.** On fc_launch's abort path, cleanup restarts the container before any recorder SIGTERM, and stage 10's `stop_recorder_cleanly` runs only on a normal exit. The recorder was therefore SIGKILLed inside its first 2000-frame segment.

- The `mdat` payload (mp4v elementary stream) is intact, so the file is probably recoverable with an externally supplied header.
- It is not worth recovering: it shows only the bring-up, sim 7.6 s to about 50 s, with the robots never moving.
- No stills or time maps are usable. `video_check_ibd.py` printed `VIDEO_CHECK ib10D_d1_armA_a1 PROBLEM`.

---

## 4. Teardown and Bookkeeping (Verified)

**Restore.**

```
[restore_ibd 17:49:58] PINS_V3 OK
[restore_ibd 17:49:58] RESTORE_IBD OK
RESTORE_STATUS OK 2026-11-14T17:49:58Z
```

**Pull.** `pull runs/ OK (try 1)`, `pull VM tree OK (try 1)`.

**Stop.**

```
[run_ibd 17:51:28] VM TERMINATED (verified)
```

Own check afterwards: `gcloud compute instances describe vgu-thu-base-isaac-vm-asia-northeast1-a … --format='get(status)'` returned `TERMINATED`.

**Wall clock.** 683 s of the 2 h IB10 cap (3.5 h demo total). `../wallclock_ledger.tsv`.

**Spend.** Two probes; $0 in analyses.

**Manifest.** `data/logs/vm_runs/ib10_demo/MANIFEST.md5` (66 files, md5 `504571702bd205d52e33eb44de00bad6`).

---

## 5. Changes Needed Before Any Re-Take

These are proposals only; neither is applied. Both kits are frozen at their registered md5s.

1. **Count a `wait_action` timeout as a bring-up abort.** Treat an fc_launch abort before `Nav2 action servers live` (or before `all components started` with no M4 log) as `bringup_abort` and retry it, as the chain already does for `NAV2_BRINGUP_FAILED`. Today it is a harness failure that stops the chain.
2. **SIGTERM every recorder on the abort path.** On the abort trigger, `rawrec_*.sh` could SIGTERM every recorder, not only its own. There are a few seconds between fc_launch logging `abort before the M5 tail finished` and the container restart. That would let the annotated recorder write its trailer.

**Convoy demo kit.** It is ready and dry-tested (`TEST_DRY_CVD OK`; md5s in registration section 8) and is on hold. Launch, only when the owner lifts the hold: `cd data/logs/vm_runs/convoy_demo/kit && bash run_cvd.sh demo`.

**IB10 re-take.** A re-take is the owner's call. It needs a new label and an owner decision, because `run_ibd.sh` refuses when demo bundles already exist.

**Frame map tool.** `data/logs/vm_runs/ib10_demo/post/overlay_framemap.py` decodes each frame's overlay into the renderer's `anchors` / `frame_sim_times` map. Tested on the 2026-09-16 run G footage, it decoded 120 of 120 frames, and its first value matched the logged `header_stamp`.
