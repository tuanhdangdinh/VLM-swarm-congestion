# Capability-Probe Battery v2: Predictive/Temporal Probes — Build, Harvest and Live Results

**Prepared:** 2026-10-04

**Revision history:**

- Initial draft: built battery v2 (three GT-derived dynamic probe types, separate frozen `manifest_v2`), harvested mid-motion frames with four mock VM episodes (trails off/on twins), ran the manifest once per pinned backend, including the first trails-on vs trails-off paired measurement.

---

## Summary

This implements the registered "Battery v2 — predictive/temporal probes"
block and the "Trails = amortized temporal context" block of
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (main checkout).
Branch `feat/v2-battery2`, cut from `feat/prereg-v2-composite` at `5f0eaf1`.

| Backend (served model) | main (59) | motion_direction | conflict_prediction | temporal_order | Refusals | Abstentions |
|---|---|---|---|---|---|---|
| Gemini ER-2 (`gemini-robotics-er-2-preview`) | 48/59 | **20/20** | 16/20 | 12/19 | 0/139 | 0/139 |
| gpt-4o (`gpt-4o-2024-08-06`) | 26/59 | 16/20 | 9/20 | **1/19** | **6/139** | **24/139** |

Headline findings:

- **v2 has the headroom v1 lacked.** v1 was 60/60 and 58/60. On v2
  the two backends separate: Gemini 81% [0.70, 0.89] against gpt-4o
  44% [0.32, 0.57] on the main battery.
- **motion_direction is not a motion-integration probe on these frames.**
  - Gemini scores 20/20 and gpt-4o 16/20.
  - M1 already draws a heading arrow and a MOVING/SLOW/STOPPED colour on
    every robot. The reversing-robot exclusion guarantees the arrow is
    truthful, so the item reads off a static annotation.
  - Treat it as an arrow/colour-reading check, not evidence of temporal
    reasoning.
- **conflict_prediction is the discriminating predictive type.**
  - Gemini: 16/20 [0.58, 0.92]. All 10 "yes" are right; 6/10 "no" are
    right, so its errors are false alarms.
  - gpt-4o: 9/20 [0.26, 0.66], at chance (0.5). It says "yes" to 6/10
    "no" items and refuses 2.
- **temporal_order is confounded and must not be read as a capability score.**
  - The correct robot is the lower id in 15/19 main items and 11/11 pair
    items. A "pick the lower id" rule scores 79% and 100%.
  - M1's lagging status colour still shows the later robot as MOVING or
    SLOW in 15/19 main items, which is a static cue.
  - Gemini 12/19 is below the lower-id heuristic.
  - gpt-4o abstains on 11/19 main items ("I'm unable to determine…"). On
    the 8 it answers, it is right once: it picks the later robot 13 of
    15 times across all arms.
- **Trails comparison (first datum for the amortized-context hypothesis):
  null at this n.**
  - 40 matched pairs per backend: the same question, the same lettering
    seed, GT configuration within 0.10 m. Only the M1 trail overlay differs.
  - Gemini: 36/40 trails-off vs 35/40 trails-on. Discordant 4 off-only /
    3 on-only, exact McNemar p = 1.0.
  - gpt-4o: 17/40 vs 15/40, discordant 4 / 2, p = 0.69.
  - No type shows a trails gain. The prompt does not state the trail
    convention, as the brief required; see "Trails Comparison" for what
    the null can and cannot mean.
- **gpt-4o refuses again: 6/139 (4.3%), against 0/60 on v1.** All six
  are the stock "I'm sorry, I can't assist with that.", on 4
  conflict_prediction items and 2 temporal_order items. Gemini refused
  0/139.
- **Spend: $0.70 in total** (Gemini $0.377, gpt-4o $0.320, preflights
  about $0.003). The $10 per-backend stop was never in play.
- **VM:** four mock runs, all gates OK, and M5 verified started in each.
  The VM is restored to its pre-deploy tree: all 782 tracked paths
  md5-identical, installed copies verified, GPU idle. It is still RUNNING.

---

## Frozen Inputs

| Input | Pin |
|---|---|
| Manifest | `reasoning/vlm/capability_probes/manifest_v2.json`, SHA-256 `faf1953b1b565f93d057faeb53fbdec28edc295a1bac7015a4a38eff3e042f8f`, commit `23e36c5`, seed `20261004`, 139 items |
| Rebuild determinism | A second build from the same logs and seed reproduces the same SHA-256 |
| Audit | `scripts/audit_capability_probe_manifest.py --manifest …/manifest_v2.json` → `OK: all 139 items passed every check` |
| Prompt | the **frozen v1 template**, `CAPABILITY_PROBE_PROMPT_VERSION = 1`, template SHA `b1af71e8…`, unchanged; no v2 prompt version was needed |
| v1 manifest | `manifest_v1.json` byte-unchanged, SHA `9659782d…` (now test-pinned) |
| Registered constants | recorded in the manifest's own `constants` block (`dynamics.py` module constants) |

The v1 template is "question, then a lettered option list, then a strict
JSON reply", and it fits every v2 item:

- yes/no items render as `A: yes` / `B: no`, with seeded letters;
- robot items render as lettered robot ids.

The template, the system prompt and both v1 rendered-fixture pins are
untouched.

---

## What Was Built

All code is under `reasoning/vlm/capability_probes/`, reusing the v1
package machinery: `letters.py`, `selection.balanced_sample`,
`manifest_io` hashing and `scanning` dedup. v1's files keep v1's behaviour.

| File | Role |
|---|---|
| `dynamics.py` (new) | Pure GT derivations: `GtTrack`, motion classes, `motion_direction_answer`, `conflict_prediction_answer`, `exclusion_horizon_sec`, `horizon_is_command_free`, `wall_to_sim`, onsets, goal and stop event times, `temporal_order_answer`. Every registered constant, with its reason. |
| `episode_v2.py` (new) | Frame sources (decision dumps and harvest snapshots), exact M1 state per frame, M5-log command windows, frame gates (`gate_frame`), the answer-level rules (`derive`) and the question wording. Shared by the builder and the auditor. |
| `models_v2.py` (new) | `ProbeItemV2` / `ProbeManifestV2` (`manifest_version: 2`). Validators: main = unpaired trails-off; every pair has one off and one on member with identical question, options, answer and seed. |
| `models.py` | `AnyProbeType` widens the record and summary `probe_type` only. `ProbeItem` stays v1-only. Optional `manifest_version` / `item_filter` on `ProbeRunSummary`. |
| `manifest_io.py` | `load_manifest_v2`, `load_any_manifest`. |
| `scripts/build_capability_probe_manifest_v2.py` (new) | scan → gate → derive → dedupe → seeded balanced selection → configuration-matched trails pairs. |
| `scripts/audit_capability_probe_manifest.py` | `audit_manifest_v2`: re-derives every v2 item from source. The v1 path is unchanged (still `OK: all 60`). |
| `scripts/capability_probes.py` | Loads either manifest version. `--subset` / `--frame-condition` restrict a v2 run to one arm, and the filter is recorded in the summary. |

Commits: `f3ec9d1` (VM harvest hooks), `c508bd0` (v2 types, builder,
audit), `b9a0337` (yes-item horizon, exact edge gate), `c6ffb9a`
(two-sided pair dedupe, a defect the audit caught), `23e36c5` (manifest).

---

## Item Types and Registered Rules

Every answer is machine-derived from Isaac GT (`gt/ground_truth.jsonl`,
10 Hz). Motion is always the GT **position** difference over the 0.5 s
before the frame, never `theta × speed_mps`. GT `speed_mps` is unsigned,
and M1's arrow follows the heading even when a robot reverses.

### Frame-Level Gates (All Types)

- Metric grid not drawn (from M1's own report). Trails decide the item's
  frame condition.
- A GT row within **0.1 s** of the frame stamp (v1 used 0.5 s, too loose
  for motion).
- 2 to 5 robots.
- M1 and GT track the same robots, within 0.10 m per axis (v1's bound).
- Frame size equals the calibration's.
- Legibility is v1's rule (no STALE, ≥70 px separation, no box/label
  overlap) with one change. **The v1 70 px centre-to-edge margin is
  replaced by the exact condition it approximated:** every drawn box and
  label rect, and the robot's footprint disc, sit at least 10 px inside
  the frame.
  - The approximation excluded every frame after an arrival in both
    harvest scenes. Their goals sit at u ≈ 1200–1218 px, with labels
    ending at ≤ 1253 px of 1280.
  - The change applies to v2 only; v1's gate is untouched.

M1 state is exact for both sources, never interpolated:

- **Decision frames:** the decision artifact's own `scene`.
- **Snapshots:** the harvest saved every `/perception/scene_state`. All
  2,291 harvested annotated frames had an exact-stamp state (530/530,
  528/528, 370/370 and 363/363 per run).

### motion_direction — "Which robot is currently moving toward X?"

- **Targets.** X is another labelled robot (scenes with 3 or more
  robots; options are the other robots) or an image edge (left, right,
  top, bottom; options are every robot). Unlabelled goal markers are
  never used as targets.
- **Classification.**
  - MOVING is ≥ 0.08 m/s; STATIONARY is ≤ 0.03 m/s.
  - "Toward" means MOVING with image-space motion within 30° of the
    bearing to X.
  - "Not toward" means STATIONARY, or MOVING at ≥ 75° from the bearing.
- **Kept** only when exactly one option is "toward" and none is in the
  margin band.
- **Dropped** when any option robot is reversing (motion more than 90°
  off its GT heading, so the drawn arrow lies). Also dropped when M1's
  drawn status contradicts the GT motion class: moving must be drawn
  MOVING or SLOW, stationary must be drawn STOPPED.

### conflict_prediction — "Will A and B come within 0.5 m (centre to centre) in the next 10 s?"

Answers come from the GT future relative to the stamp:

- **yes** if the future minimum distance is ≤ 0.40 m;
- **no** if it is ≥ 0.65 m;
- the (0.40, 0.65) band is dropped. Head-on standoffs settle at
  0.2–0.4 m.

The pair must meet these conditions at the stamp:

- **Separated:** at least 0.75 m apart, so the item is not a static
  proximity question.
- **Moving:** at least one robot MOVING, for yes and no items alike.
- **Reachable:** the threshold must be reachable at current speeds
  (gap − 0.5 ≤ 10 s × (v_A + v_B)).
  - Added after a dry scan of the logged decision frames: all 20 of the
    "no" items selected there sat 3.5–4.1 m apart.
  - Unreachable "no" items are answerable from separation alone.

The final checks:

- GT covers the full horizon.
- Neither robot reverses.
- Neither robot is in the ambiguous speed band.
- M1's status agrees with GT for both robots.
- **Balance:** strictly balanced yes/no (the larger class is trimmed).

**Dispatch exclusion (registered; documented as instructed).** The
no-command outcome cannot be observed, so the rule is a conservative
superset of "a dispatched command after the stamp changes the answer":

1. **Command windows from M5's log.** Each dispatched request's window
   opens at its decision's scene stamp. It closes at the last
   `command … resolved` line, plus 1.0 s.
   - Wall-to-sim mapping uses anchors: each `starting analysis` line's
     wall time paired with its decision stamp, interpolated linearly.
   - Beyond the last anchor the mapping extrapolates at real-time factor
     1. Isaac runs at RTF ≤ 1 here, so this over-estimates end times.
   - A command never resolved keeps its window open to the episode end.
   - A dispatch with no mappable anchor, or a missing `m5.log`, means
     the episode gives no conflict items.
2. **Task-dispatch onsets.** Each robot's first motion onset (initial or
   delayed task start) is a ±1 s event window, since it cannot be seen
   before it happens.
3. **The rule.**
   - A "no" item is excluded if any window overlaps [t, t + 10 s].
   - A "yes" item is excluded if any window overlaps [t, first time the
     pair is within 0.5 m]. A command acting after the threshold is
     crossed cannot undo a "yes", so this reads "changes the answer"
     literally, not loosely.
4. **Safety-monitor cancel-alls are dynamics, not commands.** They fire
   at the safety radius, at or after the threshold crossing.

### temporal_order — "Robots A and B have both reached their goals / come to a stop. Which of them … first?"

- **Goal event:** the first GT row at ≤ 0.20 m from the goal the robot
  still holds at the frame. The robot must stay within 0.35 m through
  the frame.
- **Stop event:** the start of the robot's current STATIONARY run,
  preceded by MOVING motion within 1.5 s. The pair must be within 1.0 m
  of each other at the frame (a standoff).
- **Frame window:** the frame lies **0.5–3.0 s after the later event**
  (M1's trail window is 3.0 s), so a trails-on frame still shows the
  later robot's approach.
- **Gap:** events at least 2 s apart. The realised gaps are 32–183 s,
  median 43 s.

### Lettering, Selection and Pairs

- **Lettering:** seeded with `letters.py`, as in v1. A pair's two
  members share one seed, derived from the pair id, so they render
  identical letters.
- **Main selection:** trails-off only, near-duplicate scenes removed
  (v1's 0.10 m rule), `balanced_sample` with up to 20 per type and at
  most 8 per episode.
  - Balance keys: the correct robot id (motion), yes/no (conflict), and
    the answer's slot in the sorted options (temporal).
- **Pairs:**
  - **Matched by configuration, not stamp.** Same-seed episodes drift
    1–2.5 s; for example, pair `motion_000` matches 22.70 s off to
    20.27 s on.
  - **Match conditions:** a trails-off candidate's closest trails-on
    twin from a different episode of the same scenario. Same question,
    options and derived answer; max per-robot GT displacement under
    0.10 m; for temporal_order, time-since-later-event within 0.5 s.
  - One conflict pair's trails-off member is a logged decision frame
    from a different episode of the same head-on scenario
    (`live_demo/GPT4OLIVE_20260930_154216`). The rule allows any
    same-scenario episode; the other 39 pairs are harvest twins.
  - **Selection:** greedy one-to-one, deduplicated on BOTH sides
    (`c6ffb9a`, after the audit flagged two trails-on members 0.09 m
    apart), then sampled with up to 15 per type.

---

## Frame Harvest (VM, Mock Backend, Zero API)

### Inventory First

Before any VM run, every `data/logs/vm_runs/**` episode with GT and frames
was scanned: 83 episodes, 1,027 decision/probe frames.

- Only 116 frames had at least one robot moving (≥ 0.08 m/s), and 19 had
  two. Decisions fire on stalls, so mid-motion frames are scarce.
- No logged frame had trails without the grid. `annot_r1` has both, and
  its 6 grid frames are excluded by rule.
- Logged frames alone gave 0 "yes" conflict items and no trails-on frames.
  A harvest was therefore required.

### Mechanism (Least Invasive Existing Path)

The existing `scripts/vm/frame_snapshots.py` grabber (step-9 visual pass;
run by `v2_final_run.sh` with `SNAPSHOTS=1`), extended additively in
`f3ec9d1`:

- `SNAP_INTERVAL` (0.5 sim-s used) and `SNAP_TOPICS` (`annotated` only;
  the raw topic was dropped to save disk);
- a `frames.jsonl` of full-precision stamps;
- a verbatim `scene_state.jsonl` of every M1 state.

`apparatus_smoke.sh` gained `OVERLAYS`, so the trails-on run turns on
`motion_trails` alone. The grid stays off, and the installed
`annotation.yaml` is md5-verified with exactly that flag set. It also
gained `OUT_ROOT`.

`v2_overlay.py` gained the `battery_v2_head_on` scene: the bshort
head-on tasks, `keep_debug_frames`, and the plan channel, so the
known-good `*_plan_once` yield mock resolves the jam. It sets no
prompt-apparatus flags.

Both runs of a twin share one M5 overlay. Only M1's `annotation.yaml`
differs. The no-overlay defaults are unchanged.

### Runs

Seed 42, YAML `duration_sec` governs. Driver:
`data/logs/vm_runs/battery_v2_harvest/harvest_driver.log`.

| Label | Scenario | M5 overlay / mock | M1 trails | Analyses | Arrivals | Snapshots |
|---|---|---|---|---|---|---|
| `b2_headon_off` | `head_on_asymmetric_w0p2_eopen_bshort_o0` | `battery_v2_head_on` / `head_on_yield_robot_2_plan_once` | off | 6 | 2 | 530 |
| `b2_headon_on` | same | same | **on** | 6 | 2 | 528 |
| `b2_convoy_off` | `convoy_counterflow` (4 robots) | `convoy_slip` / `convoy_counterflow_oracle_order_once` | off | 6 | 4 | 370 |
| `b2_convoy_on` | same | same | **on** | 8 | 4 | 363 |

The standing traps were each handled:

- **Isaac survives cleanup.** `pgrep -f run_simulation` was EMPTY before
  each launch. The literal never appeared on an SSH line: the driver ran
  from a script file under `sudo nohup`.
- **Invalid runs.** Zero "jump back in time" warnings in any run.
- **GATE OK on aborts.** M5 started in every run; the analyses and
  accepted arrivals are in each `m5.log`.
- **Pristine configs.** The pristine md5 gate passed, and every run's
  `RESTORE.txt` reads `RESTORE OK` (`orchestrator.yaml` src = installed
  = `1f656533…`, `rag.yaml` `e18c723c…`). `ANNOTATION RESTORE OK` held
  in all four runs.

### Deploy and Restore

The procedure follows the apparatus smoke:

1. **Compare.** An md5 manifest of the branch's 782 tracked files was
   compared with the VM tree: 51 mismatches, 18 of them new files.
2. **Back up.** The VM originals of the 32 changed files were tarred to
   `/home/ubuntu/b2_predeploy_backup/`.
3. **Deploy.**
   - 50 files were extracted with `--touch` and reset to the originals'
     `root:root` ownership. The pristine `orchestrator.yaml` was not
     touched.
   - Deployed md5s were verified.
   - `swarm_perception` and `swarm_orchestrator` were rebuilt, and every
     installed copy was md5-verified.
4. **Restore, after the harvest.**
   - The originals were re-extracted with `--touch` and byte-compared
     equal to the backup. The 18 new files were removed.
   - Stale `zoom_tile.py` / `permutation_votes.py` copies were found in
     colcon's `build/` cache and removed, along with their installed
     copies and `.pyc` files. A rebuild had silently reinstalled them
     from `build/`, a variant of the stale-mtime trap.
   - After the rebuild, every installed `swarm_perception` /
     `swarm_orchestrator` file matched its source, and imports were OK.
5. **Final state.**
   - All **782 tracked paths are md5-identical to the pre-deploy
     snapshot.**
   - The installed `orchestrator.yaml` is `1f656533…`, and there is no
     installed `annotation.yaml`.
   - No Isaac process remains. The GPU is idle (0 %, 171 MiB).
   - The VM is **RUNNING** and bills while running.
   - Harvest bundles stay on the VM and are mirrored to the main
     checkout's `data/logs/vm_runs/battery_v2_harvest/` (gitignored,
     about 1.2 GB).

---

## Item Composition

Build output (`scripts/build_capability_probe_manifest_v2.py --logs-root
<main>/data/logs/vm_runs`, defaults):

| Subset / type | Items | Target | Eligible pool | Episodes | Scenarios (items) | Answers |
|---|---|---|---|---|---|---|
| main / motion_direction | 20 | 20 | 351 | 8 | head-on bshort 8, convoy 8, bottleneck_merge 2, IBA1 1, IBB4 1 | r1 5, r2 6, r3 5, r4 4; edge 12 (L5 R5 B2), robot-target 8 |
| main / conflict_prediction | 20 | 20 | 48 | 7 | head-on 8, convoy 6, IBB4 2, bottleneck_merge 2, normal_flow 1, priority_urgent_r2 1 | yes 10 / no 10 |
| main / temporal_order | **19 (SHORT)** | 20 | 26 | 7 | convoy 8, bottleneck_merge 4, IBB4 3, intersection_bottleneck 2, t2b alt 1, head-on 1 | goal 9 / stop 10; lower id correct 15/19 |
| pair / motion_direction | 15 × 2 | 15 | 243 | 2 + 2 | convoy 9, head-on 6 | r1 4, r2 3, r3 4, r4 4 |
| pair / conflict_prediction | **14 × 2 (SHORT)** | 15 | 19 | 3 + 2 | head-on 8, convoy 6 | yes 7 / no 7 |
| pair / temporal_order | **11 × 2 (SHORT)** | 15 | 11 | 2 + 2 | convoy 10, head-on 1 | goal 5 / stop 6; lower id correct 11/11 |

Main frame sources: 36 harvest snapshots and 23 logged decision or
T0-probe frames. SHORT types are reported short and never padded.

### Exclusion-Rule Counts (Candidate Level, Before Selection)

| Rule | Count |
|---|---|
| frame: no GT row within 0.1 s (incl. pre-sim-time wall-clock runs) | 222 |
| frame: not legible | 208 |
| frame: M1–GT disagreement > 0.10 m | 18 |
| frame: metric grid drawn | 6 |
| motion_direction: no robot toward / several toward | 10,488 / 16 |
| motion_direction: option in the angle or speed margin band | 363 |
| motion_direction: reversing option robot | 505 |
| motion_direction: M1 status contradicts GT | 262 |
| conflict: already within 0.75 m | 1,789 |
| conflict: neither robot moving | 2,721 |
| conflict: threshold unreachable at current speeds | 1,037 |
| conflict: GT horizon beyond log end | 265 |
| **conflict: dispatched command / task onset in the exclusion horizon** | **195** |
| conflict: future minimum distance in the (0.40, 0.65) m band | 72 |
| conflict: M1 status contradicts GT / reversing / ambiguous speed | 50 / 37 / 2 |
| temporal: event missing (not both events by the stamp, or event state left) | 6,986 |
| temporal: outside the 0.5–3.0 s window after the later event | 5,349 |
| temporal: not a standoff (> 1.0 m) / gap < 2 s | 112 / 8 |
| near-duplicate scenes (motion / conflict / temporal) | 319 / 19 / 26 |

`conflict_prediction` items whose horizon is command-free are therefore
mostly the approach phases before each first decision, and the
free-flow phases after a command resolves.

---

## Run Configuration

| Field | Gemini | gpt-4o |
|---|---|---|
| Configured / served model | `gemini-robotics-er-2-preview` / same ×139 | `gpt-4o-2024-08-06` / same ×139 |
| Temperature | 0.0 configured, dropped by the API (recorded per call) | 0.0 |
| Attempts per item | 1 (no re-ask, no grey-image fallback) | 1 |
| Pacing | ≥ 3 s | ≥ 3 s |
| Arms | `main` (59), `trails_pair` × `trails_off` (40), `trails_pair` × `trails_on` (40) | same |

Results (gitignored):
`data/logs/capability_probes/battery_v2_20261004/<backend>__<arm>/`. Each
holds the per-item JSONL, `*_summary.json` (manifest SHA `faf1953b…`,
`prompt_version: 1`, `manifest_version: 2`, `item_filter`, effective
sampling block) and stdout/stderr. Run stamps are 2026-10-04T18:15Z to
18:36Z.

A scan of every output file for key prefixes, PNG base64 headers and
`data:image` returned no matches.

**Preflight.** One call per backend went through `build_backend` /
`load_backend_settings`, on a grey 1280×960 frame with a two-option
colour question. Both answered `{"choice": "A"}` correctly and served the
pinned ids (Gemini 1,162 in / 42 out incl. thought; gpt-4o 869 / 10).

---

## Accuracy per Backend × Type (Wilson 95%)

### Main Battery (Trails-Off Frames)

| Type | Gemini ER-2 | gpt-4o | Chance |
|---|---|---|---|
| motion_direction | 20/20, 100% [0.839, 1.000] | 16/20, 80% [0.584, 0.919] | 0.400 |
|   edge target | 12/12 | 11/12 | |
|   robot target | 8/8 | 5/8 | |
| conflict_prediction | 16/20, 80% [0.584, 0.919] | 9/20, 45% [0.258, 0.658] | 0.500 |
|   GT yes | 10/10 | 7/10 | |
|   GT no | 6/10 (4 false "yes") | 2/10 (6 false "yes", 2 refusals) | |
| temporal_order | 12/19, 63% [0.410, 0.809] | 1/19, 5% [0.009, 0.246] | 0.500 |
|   goal / stop | 3/9 / 9/10 | 0/9 / 1/10 | |
| **overall** | **48/59, 81% [0.696, 0.893]** | **26/59, 44% [0.322, 0.567]** | |

### Trails Pairs, Each Arm

| Type | Gemini off | Gemini on | gpt-4o off | gpt-4o on |
|---|---|---|---|---|
| motion_direction (15) | 15/15 [0.796, 1.000] | 15/15 [0.796, 1.000] | 10/15 [0.417, 0.848] | 9/15 [0.357, 0.802] |
| conflict_prediction (14) | 13/14 [0.685, 0.987] | 14/14 [0.785, 1.000] | 7/14 [0.268, 0.732] | 5/14 [0.163, 0.612] |
| temporal_order (11) | 8/11 [0.434, 0.903] | 6/11 [0.280, 0.787] | 0/11 [0.000, 0.259] | 1/11 [0.016, 0.377] |
| overall (40) | 36/40 [0.769, 0.960] | 35/40 [0.739, 0.945] | 17/40 [0.285, 0.578] | 15/40 [0.242, 0.530] |

### Reading Each Type

**motion_direction.**

- M1 draws a heading arrow on every MOVING or SLOW robot, plus a status
  colour. With reversing robots excluded and status agreement enforced,
  the arrow always points along the true motion. The item is therefore
  answerable from one frame's static annotation.
- Gemini's 35/35 and gpt-4o's 80% measure arrow/colour reading plus
  relational geometry (gpt-4o's robot-target items 5/8 and 2–3/6).
  Unaided motion integration is not what is measured.
- **A version with arrows suppressed would be needed to test motion
  integration;** this is a design note, not something implemented here.

**conflict_prediction.**

- This is the type with real headroom. Gemini's errors are all false
  alarms (4/10 "no" items answered yes). gpt-4o is at chance with a
  yes-lean (13 of its 18 answered main items said "yes").
- Its two main-battery refusals are both on "no" items with three or
  four robots (convoy snapshot, bottleneck_merge decision frame).

**temporal_order.** Three confounds stop this score being read as
temporal reasoning:

1. **Lower-id prior.** The earlier event belongs to the lower robot id
   in 15/19 main items and 11/11 pair items. Convoy robots arrive in id
   order, and the pool, 26 eligible, could not be rebalanced without
   collapsing to 8 items.
2. **Status-colour cue.** M1's EMA-lagged status still shows the later
   robot as MOVING (12) or SLOW (11) in 23 of 30 trails-off temporal
   items, while the earlier one is drawn STOPPED in 29 of 30. A static "the red one
   stopped first" cue exists in both conditions.
3. **Long gaps.** The earlier event is 32–183 s in the past, so no trail
   ever shows it; only the later robot's last ≤3 s can.

Behaviour under these confounds:

- **Gemini:** right on 11/15 lower-id-correct items and 1/4 others.
  Below the lower-id heuristic (15/19).
- **gpt-4o:**
  - It abstains on 24/41 temporal calls ("I'm unable to determine…",
    scored `parse_failure`, not refusal) and refuses 2.
  - When it answers, it picks the LATER robot 13/15 times. This is a
    systematic inversion of "first", so the 5% is not a chance-level
    score.

---

## Trails Comparison (Same Items, Trails-Off vs Trails-On Frames)

These are the first measured data for the "trails = amortized temporal
context" hypothesis. Pairs share the question, the options, the answer,
the lettering seed and the prompt. Per-robot GT position matches within
0.10 m. Only M1's trail overlay differs.

| Backend / type | n | Off correct | On correct | Both | Off only | On only | Neither | Exact McNemar p |
|---|---|---|---|---|---|---|---|---|
| Gemini / all | 40 | 36 | 35 | 32 | 4 | 3 | 1 | 1.00 |
| Gemini / motion_direction | 15 | 15 | 15 | 15 | 0 | 0 | 0 | — |
| Gemini / conflict_prediction | 14 | 13 | 14 | 13 | 0 | 1 | 0 | 1.00 |
| Gemini / temporal_order | 11 | 8 | 6 | 4 | 4 | 2 | 1 | 0.69 |
| gpt-4o / all | 40 | 17 | 15 | 13 | 4 | 2 | 21 | 0.69 |
| gpt-4o / motion_direction | 15 | 10 | 9 | 9 | 1 | 0 | 5 | 1.00 |
| gpt-4o / conflict_prediction | 14 | 7 | 5 | 4 | 3 | 1 | 6 | 0.63 |
| gpt-4o / temporal_order | 11 | 0 | 1 | 0 | 0 | 1 | 10 | 1.00 |

**Reading: a null, with three reasons it is weak evidence either way.**

1. **The prompt omits the trail convention, as the brief required.** The
   same probe prompt is used in both conditions. The deployed M2 v3
   prompt gets a sentence explaining that the faint end of a trail is
   the oldest position. Here an unexplained faint polyline may be read
   as noise. A null cannot separate "trails carry no usable history"
   from "trails went unexplained".
2. **The trails-off frames already carry motion history.** The heading
   arrow and the lagging status colour do this. motion_direction is at
   ceiling for Gemini, and temporal_order has the colour cue, so there
   is little left for trails to add on these items.
3. **The sample is small.** At n = 11–15 per type, only a large effect
   could have shown. The 95% Wilson CIs of the two arms overlap
   everywhere. The trails at 0.15 m/s are also faint (apparatus report,
   open item 5); see the pair spot-check at
   `data/logs/vm_runs/battery_v2_harvest/b2_headon_on/snapshots/annotated_00020.27.png`.

Not done: the three-way design (single frame vs trails vs 2–3 raw
keyframes) registered in the "Trails" block. The keyframe arm needs a
multi-image probe path. The harvest snapshots at 0.5 s with exact M1
states would supply its frames.

---

## Refusal, Abstention and Letter-Bias Checks

| Backend | Refusals | Abstentions (prose "unable to determine", scored `parse_failure`) | Invalid letters | Backend errors |
|---|---|---|---|---|
| Gemini | 0/139 | 0/139 | 0 | 0 |
| gpt-4o | 6/139 (4.3%): conflict ×4 (main 017, 019; pair 002_off, 011_off), temporal ×2 (pair 003_on, 007_on) | 24/139, all temporal_order | 0 | 0 |

- **gpt-4o refusals.** v1 had 0/60. All six are verbatim "I'm sorry, I
  can't assist with that." Five of the six are on convoy-scene or
  four-robot frames. The rate sits far below the 19–38% recorded on the
  congestion prompt.
- **First-listed position.** The first-listed option was correct on
  32/59 main items.
  - Gemini picked first-listed on 31/59 (main), 17/40 (off) and 20/40
    (on).
  - gpt-4o picked it on 23/59, 14/40 and 14/40.
  - No first-slot prior is visible.
- **Letter distribution (main).**
  - Gemini: A 31, B 23, C 4, D 1.
  - gpt-4o: A 21, B 17, C 7, D 1, none 13.
  - Two-option items dominate (49/59 main items), which explains the
    A/B mass.
- **robot_1 prior (motion_direction).** Gemini picked robot_1 5 times,
  0 wrong. gpt-4o picked it 5 times, 1 wrong. robot_1 was correct on 5
  main items.
- **robot_1 prior (temporal_order).** Here the id prior and the answer
  coincide (lower id correct 15/19), so the prior can neither be
  measured nor ruled out.

---

## API Spend

The list prices are the ones used in the v1 report: gpt-4o $2.50 / $10.00
per 1M input/output tokens; ER-2 $1.00 / $5.00, with thought tokens
billed as output.

| Backend | Calls | Input tokens | Output tokens (incl. thought) | Cost |
|---|---|---|---|---|
| Gemini ER-2 | 139 | 164,146 | 42,658 | $0.377 |
| gpt-4o | 139 | 123,371 | 1,155 | $0.320 |
| Preflights | 2 | 2,031 | 52 | ≈ $0.003 |
| **Total** | | | | **≈ $0.70** |

The projection from v1's per-call cost was about $0.25–0.35 per backend.
The $10 per-backend hard stop was never approached.

---

## Tests and Suite

New tests (71) cover:

- **GT-derivation correctness on synthetic tracks:** every drop reason
  for each type, the yes-horizon rule, wall-to-sim mapping, command-window
  parsing including unresolved and unmappable cases, onsets, goal and
  stop events.
- **The synthetic build/audit tree:** two trails-off/on episodes.
  - Rebuild determinism.
  - Main is trails-off only.
  - Pairs share question, answer and seed, and are near-duplicate-free
    on both sides.
  - Strict yes/no balance, and GT answers matching the synthetic
    geometry.
  - The audit passes, then catches GT drift and frame drift.
  - The command window excludes conflict items, and grid frames are
    rejected.
- **The v2 edge gate.**
- **Manifest validators.**
- **The v1 manifest byte pin and its loading as v1.**
- **v2 rendering through the frozen v1 template.**
- **The runner's arm filter and a mock end-to-end v2 run.**
- **The `battery_v2_head_on` overlay scene.**

The no-leak AST test also now covers the three new modules (+6
collected).

Suite (`pytest --continue-on-collection-errors`, same venv):

| Tree | Failed | Passed | Skipped | Errors |
|---|---|---|---|---|
| Clean detached baseline `5f0eaf1` | 63 | 4,826 | 153 | 3 |
| `feat/v2-battery2` | 63 | 4,903 | 153 | 3 |

- The failing-name set is identical (diffed).
- The +77 passes are this branch's 71 new tests plus 6 no-leak
  parametrizations.
- The 3 errors are the `pxr` collection errors.

---

## Open Items

1. **temporal_order rebalance.** Harvest a scene where higher ids arrive
   first (or permute spawn ids), and keep frames inside the trail window
   of BOTH events (gap ≤ 3 s), or the type stays confounded.
2. **Arrow-free motion_direction variant.** It would test motion
   integration instead of arrow reading. It needs an M1 overlay flag, so
   it is an owner decision.
3. **Trails arm with the convention sentence, and the raw-keyframe arm.**
   Both are needed before the amortized-context hypothesis can be judged.
4. **gpt-4o abstentions.** These are separate from refusals and stay
   scored wrong. If v2 is ever cited per backend, report
   accuracy-when-answered beside raw accuracy.
5. **VM still RUNNING** (idle); stop it when no further runs are planned.
