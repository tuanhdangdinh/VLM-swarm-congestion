# Demo Video: Scene Beside a Log-Replay Terminal

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: renderer (`scripts/render_demo_panel.py`, `scripts/demo_panel/`), terminal rules, time mapping, camera input path, known limits.
- Rev 2 (2026-11-15): scene-log file name fallback for older bundles; how the ER2LIVE (2026-09-30) frame map was made and checked.

---

## What the Video Shows

The left pane shows the scene. The right pane is a terminal that replays the run's own log lines in step with simulation time.

- **Left pane.** If the run has a camera recording, the left pane shows it. Otherwise it shows a top-down view drawn from `gt/ground_truth.jsonl`. That view is labelled on screen: "Reconstructed from ground-truth poses (no camera recording for this run)". It draws the racks from the repo's Nav2 map for the scenario, `ros2_ws/src/swarm_simulation/maps/warehouse_map_<map>.yaml`. That map is not part of the bundle. Robot footprints come from `ros2_ws/src/swarm_simulation/config/nav2_params.yaml`.
- **Right pane.** The terminal shows only three kinds of line:
  1. Original lines from `m5.log` and `m4.log`, verbatim. They are selected by one fixed filter, and the filter is printed as the command at the top of the terminal:

     ```bash
     cd <bundle> && grep -hE 'session_id=|reasoning_enabled=|starting analysis|decision artifact written|dispatch request=|no dispatch|phase advance|arrived at base goal|Safety monitor started|command received|exempt pairs changed|crossing_chain|safety stop' m5.log m4.log | sort -s -t'[' -k4,4n
     ```

     The `sort` orders the merged lines by their own wall stamp. The renderer runs this command for real and displays its output. `tests/unit/test_demo_panel.py` checks the command's output against a pure-Python version of the same filter. `tail -f m5.log m4.log | grep ...` is not used: on finished files it prints only the last lines of each file, under `==> file <==` headers.
  2. `[… N similar 'safety stop' lines]` markers. The marker names the line it collapses, so a reader does not take it for the line printed above it. The M4 safety latch logs `safety stop robot=<id> reason=<r>` about 40 times per second per robot. Within one latch episode, the first line of each distinct message is shown verbatim. Repeats of it (same text apart from the wall stamp) are counted. The count is printed every 10 sim-s and when the episode ends. An episode ends after a gap of more than 2 wall-s between stop lines.
  3. Read-only commands, each printed as `$ <command>` and followed by its actual output. When a `decision artifact written` line appears, the renderer runs short `jq` commands on `decisions/<request_id>.json`. They print:
     - the request: prompt version, a 12-character prefix of the prompt's SHA-256, the prompt length, and the prompt's first line;
     - the model call: backend, served model, latency, attempts and total tokens;
     - the decision: strategy, involved robots and the model's justification;
     - grounding (only when `plan` is not null): provenance, rejection reason, degradations and dispatch order.

     When `cost.log` exists, the renderer also runs `grep -m1 ' billed_calls=<n> ' cost.log` for each poll where `billed_calls` first rose. The poll stamp is `HH:MM:SS` UTC, so the poll is placed at the end of its second. It therefore never prints before the artifact it counts.
- **Colours.** One small fixed scheme: M5 lines white, M4 lines cyan, WARN yellow, commands green, markers grey.
- **Wrapping.** Long lines wrap at the terminal width, as a real terminal wraps them. Nothing is truncated.
- **Captions.** Captions sit outside the terminal: the run label, sim clock, speed state and a provenance sentence.

### Speed States

The caption names the current speed state.

| Caption | Meaning |
|---|---|
| `Nx sim time` | Sim time plays N times faster than real time: 3x near log lines, 8x between them, 30x after the last line. |
| `1x wall clock (real time) while waiting for the model` | Plays from `starting analysis` to `decision artifact written`, so the model's real latency is seen at its true length. |
| `PAUSED (sim clock held) while the command output prints` | The `jq` and `grep` blocks print at about 7 rows/s, then hold for 4 s. |
| `SLOWED: sim clock held/slowed so a burst of log lines stays readable` | The dispatch bursts print at about 7 rows/s instead of all at once. |

## What It Does Not Prove

The video is an illustration. The evidence is the bundle. Every terminal line can be checked against the bundle in one of two ways:

- Re-run the filter command shown at the top inside the bundle directory.
- Re-run the printed `$` commands.

The renderer also writes `<video>_transcript.json`. It lists every terminal item with its source (`m5.log:<line>`, `m4.log:<line>`, or the command), its sim time and how that time was obtained.

The two-part video (`ib10_vlm_on_vs_off.mp4`) puts two episodes one after the other. They come from different days and kits: `ib10_safety` on 2026-11-14 and `ib10_live` on 2026-11-13 (UTC). The VLM-on run had the M4 safety key `scoped_clearing_exemption=True`. The Layer-2-off run's M4 startup line has no such key. The video is therefore not a controlled comparison.

## How to Render

Run from the repo root, with `jq`, `grep`, `sort`, `awk`, `bash` and `ffmpeg` on PATH:

```bash
# One bundle, ground-truth reconstruction on the left:
python3 scripts/render_demo_panel.py render --bundle <bundle_dir> --out data/demo/<label>_panel.mp4 --stills

# One bundle with a real camera recording on the left (one-liner once footage exists;
# list the recorder's segments in order):
python3 scripts/render_demo_panel.py render --bundle <bundle_dir> --camera <bundle_dir>/rec/annotated_000.mp4 <bundle_dir>/rec/annotated_001.mp4 --camera-map <bundle_dir>/rec/<frame_map>.json --camera-label "Camera: /perception/annotated_frame" --out data/demo/<label>_panel.mp4 --stills

# Several bundles one after the other, with caption cards; --calibrate-on measures the
# fallback time anchor's error on a bundle that has real anchors:
python3 scripts/render_demo_panel.py sequence --bundle <on> --bundle <off> --calibrate-on <on> \
  --card "Part 1 ..." --card "Part 2 ..." --out data/demo/<name>.mp4 --stills
# add footage for the i-th bundle (others keep the GT reconstruction):
#   --camera-for <i> <map.json> <segment_000.mp4> [<segment_001.mp4> ...]
```

`render` also takes `--caption "<line>"` (repeatable) for the outcome label, take, model and disclosure lines. They are drawn under the scene pane, never in the terminal; the first line is highlighted. With camera footage, the scene box is then fitted to the clip's aspect ratio (800x600 for 4:3) so the lines fit above the footer.

Output is H.264 (`libx264`, `yuv420p`, `+faststart`, 24 fps, 1920x1080), so it plays in QuickTime, browsers and on phones. `data/demo/` is git-ignored.

`--camera-map` accepts any one of these JSON shapes:

- `{"anchors": [[frame_index, sim_time], ...]}`
- `{"frame_sim_times": [...]}` (one sim time per frame)
- `{"first_stamp": s0, "last_stamp": s1, "frames": n}`

Between anchors the frame-to-sim map is linear. Outside them the pane is blank. Several `--camera` segments are read as one clip, and the frame index runs on across them. The camera path was exercised end to end with a synthetic two-segment `mp4v` clip on `ib10S_e03_armA_a1`; no real footage was available yet.

## Combining Per-Scenario Videos

`combine` joins finished panel videos (or any MP4s) into one video. It reads a JSON manifest and never edits the source files.

```bash
python3 scripts/render_demo_panel.py combine --manifest <manifest.json> \
    --out data/demo/<name>.mp4 [--title-card-sec 3] [--fps 24] [--size WxH] [--font F] [--crf 23]
```

Manifest (`path` is relative to the manifest's directory unless absolute; unknown keys are rejected):

```json
{"clips": [
  {"path": "a.mp4", "title": "4-robot intersection",
   "outcome": "VLM-driven execution", "take": "take 2 of 5",
   "start": 12, "end": 95, "note": "optional one line"}
]}
```

- `outcome` must be exactly one of `VLM-driven execution`, `M3-default resolution`, `Unresolved failure`.
- `start` and `end` (seconds) are optional. Omitted bounds mean the clip's start or end.
- Before each clip: a plain title card (`--title-card-sec`, default 3 s) with title, outcome, take, note, and the fixed line "Illustrative demonstration, not controlled experimental evidence."
- During each clip: a 44 px caption bar above the clip area with title, outcome, take and the trim (`excerpt 12-95 s of 114.6 s`, or `full clip`). Only the title is shortened if the line is too long.
- The content area is the largest source size (or `--size`), so same-size sources are not rescaled. Other sizes are letterboxed in black, never cropped; the output is that size plus the bar (1920x1124 for 1080p sources). Frame rate is resampled to `--fps` by nearest earlier source frame.
- A missing file, an unreadable video, an unknown outcome label or a bad trim stops the run with an error before any encoding.
- A sidecar `<out stem>_sources.json` lists each source path, md5, size, fps, duration, trim, labels and note.

Tool test: `data/demo/combine_tool_test.mp4` (two existing videos, labels invented for the test) is not a demo video.

## Recording a Real Camera Video Later

Recording is enabled by `RECORD=1` on `scripts/vm/fc_launch.sh`; the default is `RECORD=0`. With `RECORD=1`, stage 5 does the following:

1. Measures the rate of `/perception/annotated_frame` with `ros2 topic hz`. If the measurement fails, it falls back to 9.
2. Starts the recorder:

   ```bash
   python3 /ws/scripts/record_topic_video.py --topic /perception/annotated_frame --output <REC_DIR>/annotated.mp4 --duration-sec <REC_SEC> --fps <measured> --qos best_effort --segment-frames 2000
   ```

The output lands in `data/logs/fc_run_<STAMP>/` on the VM. Because of `--segment-frames 2000`, the files are `annotated_000.mp4`, `annotated_001.mp4`, and so on. They are `mp4v`, one container frame per received message. The recorder burns the header stamp into each frame by default (`t=<stamp>s f=<n>`). Its log prints the first frame's `header_stamp` and a final `WROTE ... frames=<F> secs=<S>`.

The recorder writes no per-frame timestamps, and best-effort QoS can drop frames. So:

- The frame-to-sim map is exact only at anchors: the first frame, plus any frame whose burned-in clock is read.
- The two-anchor form (`first_stamp`, `last_stamp`, `frames`) assumes a uniform frame rate.
- Frame maps with one sim time per frame are made by decoding the burned-in clock. The campaign kit's decoder (`data/logs/vm_runs/demo_campaign/ho/kit/overlay_framemap.py` in the campaign worktree, md5 `a5f2dd256222b03e93784995fa6ec0a5`) also works unchanged on the 2026-09-30 ER2LIVE recording (same overlay code at `3959d7f`): 3745 of 3745 frames decoded, median IoU 0.849, and 16 frames read by eye matched to 0.00 s. Run it as `python3 overlay_framemap.py --out <map.json> annotated_000.mp4 annotated_001.mp4`; the renderer reads its `anchors`.
- A per-frame stamp sidecar written by the recorder would remove this limit. That is a follow-up; the recorder is unchanged here.

Recording costs CPU/GPU on the VM and may lower the real-time factor. Record a separate demo run, not an experiment episode.

## Time Mapping and Its Error

ROS log lines carry wall stamps; the scene and the ground truth carry sim time. The mapping works like this:

1. `m5_scene.jsonl` rows pair M5's `time.monotonic()` receipt time `t` with the scene's sim `stamp`.

   Older bundles (for example `ER2LIVE_20260930_152222`) carry the same rows as `scene_<session_id>.jsonl`. The loader takes the first match of: `m5_scene.jsonl`; `scene_<session_id>.jsonl`, with `session_id` from the first `session_id=` line in `m5.log`; the only `scene_*.jsonl`. Several `scene_*.jsonl` files with none matching the session is an error. The time-map method string in the transcript names the file used.
2. The renderer estimates the constant wall-minus-monotonic offset. It takes the median over two kinds of anchor:
   - M4 lines that print their own `sim_t=`;
   - `starting analysis` lines, paired with their decision's `scene.stamp`. This is the same method as `scripts/rescore_arrivals.py`.
3. It then maps wall stamp to sim time by piecewise-linear interpolation of `(t, stamp)`. There is no global linear fit, because the sim-to-wall rate drifts (about 0.2–0.3 sim-s per wall-s).

In `ib10S_e03_armA_a1`, 41 anchors agree within **0.22 sim-s**. Ground truth runs 0.300 s behind ROS stamps (`scripts/gt_offset_audit.py`), so the scene pane draws GT at sim t − 0.300 s.

A bundle with no anchors falls back to one coarse anchor. That anchor pairs the first `safety stop` line with the first GT row whose minimum pairwise distance is below `min_distance_m`. `ib10L_e02_armB_a1` (Layer 2 off) is such a bundle. On `ib10S_e03_armA_a1` this rule is off by 0.39 sim-s. Whenever the fallback is used, the footer says that alignment is uncertain.

## Known Limits

- **Reconstructed scene.** Without camera footage, the left pane is drawn from GT poses, not the camera image.
- **Lines the filter excludes.** Some lines never reach the terminal:
  - Unstamped stderr lines in `m5.log`, for example the Gemini sampling-field notice.
  - `trigger suppressed`, `shadow request` (classical shadow), `status published` and per-robot `command ... resolved` lines.
- **Prompt not dumped.** The terminal shows the prompt's identity (version, hash prefix, length) and first line only. The full text is in `decisions/<id>.json` at `.prompt.user_prompt`.
- **Model output.** The model's raw answer is in `.raw_text`. The terminal shows the parsed `.decision` fields. In `ib10S_e03_armA_a1` the raw answer contained a `proposed_plan`, which M3 rejected (`proposed_plan=default:invalid_structure`). The executed sequence is M3's default (`provenance=m3_default`), and the grounding line shows this.
- **Arrival lines vs the scorer.** M5's `arrived at base goal` lines (Nav2 goal reached plus M1 position check) come about 4–7 sim-s after the scorer's GT-based arrival times. In `ib10S_e03_armA_a1`, robot_2 is logged at 99.3 against the scorer's GT 91.8 + 0.3. This is a difference between the two rules, not an alignment error.
- **Cost-poll timing.** `cost.log` lines carry HH:MM:SS only, and the poll runs every ~5 s.
