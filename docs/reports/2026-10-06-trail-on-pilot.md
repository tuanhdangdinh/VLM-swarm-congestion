# PILOT: Motion-Trails-On Re-Run of Battery-v2 Main Probes (Same Frames, Offline)

**Prepared:** 2026-10-06

**Status:** PILOT. Exploratory and EXCLUDED from every confirmatory count.

**Revision history:**

- Rev 0 (`4e79d06`, committed before any API call): the decision rule.
- Rev 1: method, fidelity checks, results, cost and recommendation. The
  decision rule section is unchanged from rev 0.

---

## Summary

**Recommendation: NO. Do not register a trail arm in prereg-v3 with the
current trail parameters.** By the rule fixed before any call, every
primary backend × type comparison has |net| ≤ 1.

| Backend | Type (n) | OFF-frozen (10-04) | OFF-retest (today) | ON (today) | ON vs retest: on-only / off-only, net |
|---|---|---|---|---|---|
| Gemini ER-2 | conflict_prediction (20) | 16 | 16 | **17** | 1 / 0, **+1** |
| Gemini ER-2 | temporal_order (19) | 12 | 13 | **12** | 1 / 2, **−1** |
| Gemini ER-2 | motion_direction (20) | 20 | — | 19 | vs frozen 0 / 1, −1 |
| gpt-4o | conflict_prediction (20) | 9 | 9 | **8** | 2 / 3, **−1** |
| gpt-4o | temporal_order (19) | 1 | 0 | **1** | 1 / 0, **+1** |
| gpt-4o | motion_direction (20) | 16 | — | 13 | vs frozen 0 / 3, −3 (p = 0.25) |

- **This is the second null on trails.** Battery v2 matched trails-on and
  trails-off frames by configuration across different episodes, over 40
  pairs. This pilot pairs the SAME frame with and without trails, the
  tightest pairing available, and still finds no change beyond test-retest
  noise.
- **Likely cause: the stimulus barely exists.** At these speeds
  (0.15 m/s), a 3.0 s trail is 0.45 m long, and the 0.20 m robot-clear disc
  hides the newest part of it.
  - The median visible trail is 222 px of a 1.23 Mpx frame.
  - 8 of 59 frames show no trail pixel at all.
  - The prompt also never explains what a trail is (battery-v2 open item 3).
- **gpt-4o refusals are noise-level and item-unstable.** ON had 4/59,
  OFF-retest 6/39 and OFF-frozen 2/59. The refused items barely overlap
  between runs. The harm flag (ON minus retest ≥ +3 on shared items) was
  not raised: ON had 4 and retest 6 on the 39 shared items.
- **gpt-4o's temporal_order inversion is unchanged.** When it answers, it
  picks the later robot (ON 3/4 answered, retest 3/3, frozen 7/8). It
  abstains on 14, 13 and 11 of the 19 items respectively.
- **Method: fully offline, no VM.** Fidelity was verified (see Fidelity).
- **Cost: about $0.51**, under the $0.60 cap. No probe family was cut.

---

## Decision Rule (Fixed Before Any API Call)

Arms, all on the 59 frozen battery-v2 `main` items (`manifest_v2.json`,
SHA `faf1953b…`), same frozen v1 prompt, same seeded lettering, same pinned
backends (gpt-4o-2024-08-06, gemini-robotics-er-2-preview), one call per
item, no re-ask:

- **ON** — trails-on composite of the same frame (all 59 items, both backends).
- **OFF-retest** — the frozen trails-off frame, re-asked the same day
  (conflict_prediction + temporal_order, 39 items, both backends), as a
  test-retest noise floor. Gemini's API drops temperature, so its answers
  are not deterministic.
- **OFF-frozen** — the 2026-10-04 battery-v2 main results (no new calls).

Primary comparison: ON vs OFF-retest per backend on conflict_prediction and
temporal_order; secondary: ON vs OFF-frozen on all three types. "Net" =
on-only-correct minus off-only-correct over matched items. "Drift" = the net
of OFF-retest vs OFF-frozen on the same items.

- **YES (register a trail arm in v3)** — for at least one backend, ON beats
  OFF-retest on conflict_prediction or temporal_order by net >= +3 of the
  type's items, AND that net is at least twice |drift| for the same
  backend × type, AND no backend × type shows net <= -3 (harm).
- **NO** — every backend × type on the primary comparison has |net| <= 2
  (no detectable change at pilot n), consistent with the battery-v2 40-pair
  null.
- **NEEDS-BIGGER-PILOT** — anything else (an effect of >= 3 that fails the
  drift test, or effects of opposite sign across backends/types).
- **Harm flag (reported regardless):** gpt-4o refusals ON minus OFF-retest
  >= +3 on the 39 shared items.

Results are reported for all 59 items and for the 44-item exact-history
subset (see Method); the decision uses all items, with the subset as a
robustness check.

---

## Method

### Why offline compositing, not raw-frame re-annotation and not the VM

The brief's preferred path was to re-annotate recorded raw frames with
`motion_trails=true`. It is impossible for most items:

- **36 of the 59 main frames are harvest snapshots with no raw frame.** The
  battery-v2 harvest saved the annotated topic only.
- **The 23 decision frames have a `<request_id>_raw.png`, but it is not the
  annotated frame's source image.**
  - M5 grabs it from the camera topic at a slightly different instant
    (`raw_frame_skew_sec`).
  - Re-annotating it with trails off differed from the recorded annotated
    frame by 250k–600k pixels on 13 of 15 distinct decision frames, mostly
    render noise.
  - Only 2 frames came within about 3k px.

The VM fallback was not needed and was not used. Nothing on the VM was
touched or fetched; every input was already mirrored locally under the main
checkout's `data/logs/vm_runs/`.

**The trails-on frame is a composite on the frozen frame itself.** For each
item:

1. Load the frozen annotated frame (SHA-verified against the manifest).
2. Rebuild M1's `TrailHistory` with the registered parameters (3.0 s
   window, 0.1 s minimum step, 40 points). Feed it the item's M1 state
   history in order, from the first logged message through the drawing
   state.
3. Draw M1's own `draw_motion_trails` onto a copy.
4. Restore every pixel from the frozen frame that falls in:
   - the 0.20 m robot-clear footprint discs;
   - any pixel the robot overlay touches (boxes, arrows, goal markers);
   - the robot-id label rectangles.

This reproduces the live M1 order: trails go under the overlays, and
footprints are cleared. Every pixel outside the trail is therefore
byte-identical to the frozen trails-off stimulus.

- **With trails off, the composite equals the recorded frame by
  construction.** That is not a fidelity result; the checks below are.
- **Known residual.** A trail passing under an anti-aliased overlay edge
  keeps the trails-off pixel there (0 px on every item).
- **Label rectangles.** A trail under a label rectangle is suppressed
  rather than blended: 16–62 px, on 4 items only.

Code: `scripts/pilot_trail_probe.py` (`render`, `validate`, `run`). It
imports and calls M1's `TrailHistory`, `draw_motion_trails`,
`render_annotated_frame` and `_footprint_mask` unchanged.

### History quality per item

| Tag | Items | State source |
|---|---|---|
| exact | 44 (36 snapshots + 8 decision frames: md_014, md_015, md_018, cp_003, cp_009, to_003, to_006, to_012) | Every M1 `/perception/scene_state` message (`snapshots/scene_state.jsonl`, or `scene_full.jsonl`), about 30 Hz, giving about 30 trail points per robot |
| approx | 15 (other decision frames) | M5's sparse scene log (about 2.5–4 Hz) plus `decision.scene`, giving 6–12 trail points over 3 s; the polyline geometry is the same, with coarser vertices and alpha buckets |

### Fidelity checks

1. **The overlay is redrawn exactly.** This shows the state, calibration
   and projection are the ones that drew the frozen frame.
   - Method: render the M1 robot overlay of the chosen state on black and
     on white canvases. "Opaque" pixels are those identical on both,
     excluding labels. Then compare them with the frozen frame.
   - **All 44 exact-history items match 100%:** 1,138–2,533 opaque px each,
     every one equal.
   - Two discrepancies had to be resolved first, and both are themselves
     findings:
     - **Half-pixel ties.** M1 positions come from averages of marker
       corners, so many robots project to exactly `u.5`/`v.5`. The result
       of `int(round(...))` then depends on the last ulp of `inv(H) @ p`,
       which differs between the VM's and this Mac's numpy. Each tied
       point's rounding was chosen against the frozen frame.
     - **Label glyphs.** These differ between OpenCV builds (VM vs Mac
       cv2 5.0.0). Labels are therefore compared and protected as whole
       rectangles.
   - **Decision frames.** For all 8 exact decision frames, the state that
     drew the frame is a neighbouring M1 message, −0.200 s to +0.233 s from
     `decision.scene`'s stamp, not `decision.scene` itself. M5 pairs frame
     and scene within a skew bound. The trail history is cut at the drawing
     state.
     - **Side note for the battery-v2 auditor:** its "exact M1 state" for
       decision frames is off by up to 0.23 s.
   - **The 15 approx items** reach 0.75–1.00 opaque match (4 at 1.00). The
     sparse M5 log cannot pin the drawing instant, so their trail endpoints
     may sit a few px off. Results are reported separately below.
2. **The trail logic matches live M1 trails.**
   - The `b2_headon_on` and `b2_convoy_on` harvest runs recorded real
     trails-on frames with the same code and parameters. For 104 of their
     frames with visible trails, the trail was replayed from each run's
     `scene_state.jsonl` onto a per-pixel median background and compared
     with the live frame on the predicted trail pixels.
   - Median absolute error:

     | Comparison on the predicted trail pixels | Median absolute error |
     |---|---|
     | replay vs live frame | 5.3 |
     | no trail drawn | 24.2 |
     | same trail shifted by 4 px | 20.7 |

   - Replay beat both controls on **104/104** frames. The 5.3 residual is
     mostly the median-background approximation of the raw floor.
   - Output: `validate_live_trails.json`.
3. **The prompt is identical.** The driver asserts that each ON payload
   equals the frozen-frame payload except for `image_path`, and verifies the
   SHA of both frames before any call.

### Runner

`pilot_trail_probe.py run` reuses the battery's own pieces:

- `capability_probes.load_backend_settings` and `run_item`;
- `build_item_choices`, with the manifest seed;
- `build_capability_probe_prompt_payload`;
- `score_records`.

Runs used one call per item, no re-ask and 3 s pacing. Keys came from the
environment, via `set -a; source .env` in the calling shell. One grey-frame
preflight per backend answered correctly and served the pinned model ids.
`manifest_v2.json` is untouched.

---

## Results

### All 59 items (correct / n; refusals and abstentions in brackets)

| Backend | Type | OFF-frozen | OFF-retest | ON | ON vs retest (on-only / off-only, net, exact McNemar p) | Drift: retest vs frozen (net) |
|---|---|---|---|---|---|---|
| Gemini | motion_direction | 20/20 | — | 19/20 | — (vs frozen 0 / 1, −1) | — |
| Gemini | conflict_prediction | 16/20 | 16/20 | 17/20 | 1 / 0, +1, p = 1.0 | 0 (1 / 1) |
| Gemini | temporal_order | 12/19 | 13/19 | 12/19 | 1 / 2, −1, p = 1.0 | +1 |
| gpt-4o | motion_direction | 16/20 | — | 13/20 | — (vs frozen 0 / 3, −3, p = 0.25) | — |
| gpt-4o | conflict_prediction | 9/20 [2 ref] | 9/20 [3 ref] | 8/20 [3 ref] | 2 / 3, −1, p = 1.0 | 0 (1 / 1) |
| gpt-4o | temporal_order | 1/19 [11 abst] | 0/19 [3 ref, 13 abst] | 1/19 [1 ref, 14 abst] | 1 / 0, +1, p = 1.0 | −1 |

Gemini had 0 refusals and 0 abstentions in every arm.

### Exact-history subset (44 items)

| Backend | Type (n) | OFF-frozen | OFF-retest | ON | ON vs retest net |
|---|---|---|---|---|---|
| Gemini | motion_direction (17) | 17 | — | 16 | (vs frozen −1) |
| Gemini | conflict_prediction (15) | 14 | 13 | 14 | +1 |
| Gemini | temporal_order (12) | 6 | 8 | 7 | −1 |
| gpt-4o | motion_direction (17) | 13 | — | 10 | (vs frozen −3) |
| gpt-4o | conflict_prediction (15) | 7 | 7 | 7 | 0 |
| gpt-4o | temporal_order (12) | 0 | 0 | 1 | +1 |

The same reading holds: no primary |net| above 1.

### Per-type detail

- **conflict_prediction.**
  - Gemini gets all 10 "yes" items right in every arm. Its "no" items go
    6/10 → 7/10 with trails, which is one fewer false alarm.
  - gpt-4o keeps its yes-lean: it said "yes" 13 (frozen), 13 (retest) and
    14 (ON) times out of 20. Its "no" items went 2 → 2 → 1.
- **temporal_order.**
  - Gemini picks the lower id 14 (frozen), 15 (retest) and 14 (ON) times
    out of 19, so the confound described in the battery-v2 report is
    untouched.
  - gpt-4o answered 8, 3 and 4 of 19. When it answers it picks the later
    robot: 7/8, 3/3 and 3/4.
- **motion_direction** (secondary; no retest arm, because it reads the
  heading arrow).
  - gpt-4o lost 3 items with trails on: md_006, md_009 and md_014, all
    exact-history items with 88–103 trail px.
  - This is the largest movement in the pilot, but p = 0.25, and there was
    no same-day retest to size its drift. (gpt-4o's conflict and temporal
    retest-vs-frozen discordance ran 1–2 items per type.)
  - It is recorded as a possible distraction signal, not a finding.

### Refusals (gpt-4o; Gemini 0 everywhere)

| Arm | Count | Items |
|---|---|---|
| OFF-frozen (59) | 2 | cp_017, cp_019 |
| OFF-retest (39) | 6 | cp_003, cp_005, cp_006, to_004, to_007, to_011 |
| ON (59) | 4 | cp_006, cp_013, cp_015, to_014 |

- Only cp_006 recurs across runs. All refusals are on conflict or temporal
  items, none on motion_direction.
- Refusal is item-unstable at this rate, so trails show no refusal effect
  in either direction.

### Stimulus size

Trail pixels visible after the footprint and overlay restore:

| Type | Median | Items with none |
|---|---|---|
| motion_direction | 99 | 3/20 |
| conflict_prediction | 297 | 3/20 |
| temporal_order | 190 | 2/19 |

Overall: median 222 px, maximum 602 px, out of 1,228,800.

---

## Cost

List prices as in battery v2: gpt-4o $2.50 / $10.00 per 1M input/output
tokens; ER-2 $1.00 / $5.00, with thought tokens billed as output.

| Arm | Calls | Input | Output (+ thought) | Cost |
|---|---|---|---|---|
| Gemini ON | 59 | 69,666 | 647 + 17,310 | $0.159 |
| Gemini OFF-retest | 39 | 46,170 | 429 + 13,518 | $0.116 |
| gpt-4o ON | 59 | 52,359 | 524 | $0.136 |
| gpt-4o OFF-retest | 39 | 34,723 | 379 | $0.091 |
| Preflights | 2 | 2,025 | 43 | ≈ $0.003 |
| **Total** | 198 | | | **≈ $0.51** |

There were no backend errors. Outputs were scanned for key prefixes, PNG
base64 headers and `data:image`, with no matches.

---

## Recommendation

**NO: do not register a trail arm in prereg-v3 as currently parameterized.**

Two pairings now agree there is no effect: battery v2's 40
configuration-matched pairs, and this pilot's 59 same-frame pairs. If trails
are to be revisited, change the stimulus first. That is a design decision
for the owner, not a pilot result:

1. **Make the trail visible past the footprint.**
   - At 0.15 m/s, a 3 s window gives 0.45 m, of which the 0.20 m clear disc
     hides the newest ~0.2 m.
   - Options: a longer window (6–10 s), or a thicker or less faded line.
2. **State the trail convention in the probe prompt.** The deployed M2 v3
   prompt already has the sentence.
3. **Measure a gpt-4o motion_direction retest before calling the −3 a
   distraction effect.**

After those changes, a re-pilot on this same offline harness costs about
$0.30 and needs no VM.

---

## Artifacts

Under the worktree, gitignored:
`data/logs/capability_probes/trail_pilot_20261006/`

- `frames_on/<item_id>.png`: the 59 composites.
- `render_metrics.jsonl`: per-item quality, provenance, overlay match,
  trail pixels and points.
- `validate_live_trails.json`: the live-trail check.
- `<backend>__on/`, `<backend>__off/`: per-item JSONL and summaries.
- `*_on.log`, `*_off.log`: per-item progress.

Frozen OFF results:
`<main>/data/logs/capability_probes/battery_v2_20261004/<backend>__main/`.
