# PILOT: Frozen V-JEPA 2 Encoder + Linear Probe on the Battery-v2 Conflict and Temporal Probes

**Prepared:** 2026-10-11

**Status:** PILOT. Exploratory, non-confirmatory, and EXCLUDED from every confirmatory count.

**Revision history:**

- Rev 0 (`66ac9eb`, committed before any held-out or battery item was scored): the frozen probe configuration and the decision rule.
- Rev 1: summary, dataset card, method, results from the single scoring pass, caveats, runtime and recommendation. The decision-rule and frozen-configuration sections are unchanged from Rev 0, except that two table cells were escaped. Rev 0's opening sentence says "leave-one-episode-out"; the frozen configuration it committed already used leave-one-scenario-family-out (see "Split change before scoring").

---

## Summary

**Verdict by the pre-committed rule: this earns a paragraph, not a thesis table.**
T3 passes; T1 and T2 fail.

Three-way comparison on the battery-v2 `main` items that could be mapped to a
dense preceding clip (encoder-capability comparison, NOT protocol-identical;
see Caveats):

| Task (mapped n / full n) | Chance | gpt-4o (same items) | ER-2 (same items) | V-JEPA probe, `dyn` | `static` control | Non-learned baselines |
|---|---|---|---|---|---|---|
| conflict_prediction (13 / 20) | 0.50 (always-yes 7/13) | 5/13 [0.18, 0.64] | 12/13 [0.67, 0.99] | **13/13** [0.77, 1.00] | **13/13** | constant-velocity CPA from GT state 12/13 |
| temporal_order (12 / 19) | 0.50 | 0/12 [0.00, 0.24] | 6/12 [0.25, 0.75] | **12/12** [0.76, 1.00] | **12/12** | lower-id 9/12; drawn-STOPPED colour rule 11/12 |
| Full-battery reference | | conflict 9/20, temporal 1/19 | conflict 16/20, temporal 12/19 | | | |

Brackets are Wilson 95% intervals. Exact McNemar on the same items:

- conflict: probe vs gpt-4o 8/0, p = 0.008; probe vs ER-2 1/0, p = 1.0.
- temporal: probe vs gpt-4o 12/0, p = 0.0005; probe vs ER-2 6/0, p = 0.031.
- `dyn` vs `static`: 0 discordant items on either task.

**The battery numbers do not show motion understanding.** Three readings:

1. **The static control ties everywhere.** `static` sees the last annotated
   frame repeated 8 times, so it has no motion. It scores 13/13 and 12/12, the
   same as `dyn`, on the same items. By the pre-committed readout, both battery
   scores are attributed to static cues.
   - On temporal_order the cue is M1's lagging status colour. The
     drawn-STOPPED rule alone scores 11/12.
   - On conflict_prediction it is the scene and status layout. The 13 mapped
     items split cleanly by scene and episode phase: head-on approach and
     early-convoy frames are "yes"; late head-on, late-convoy and IBB4 frames
     are "no". The probe's training
     set also contains `intersection_bottleneck` (IBA1, `v2_demo/ep2`), the
     same scenario as the IBB4 battery episode. Those runs passed the 8 s
     trajectory near-duplicate rule, but share the layout.
2. **On unseen scenario families the conflict probe is at chance.**
   - Held-out command-free clips: balanced accuracy **0.53** for `dyn` and
     0.45 for `static`. That is 106 clips, 29 of them "yes", from 3 episodes
     in 2 families.
   - It missed all 24 bottleneck_merge "yes" clips.
   - A constant-velocity closest-approach rule on GT state reaches 0.83 on
     the same clips.
   - T1 (>= 0.70) fails, and T2 (`dyn` - `static` = 0.076 < 0.10) fails.
   - Within the training families, leave-one-family-out CV did separate `dyn`
     (0.73) from `static` (0.58). The motion signal exists in-family, but it
     does not transfer across families at this data scale.
3. **Temporal order is solved by the static cue, as predicted before
   scoring.**
   - Held-out broad pairs: `dyn` 0.95, `static` 0.96 (145 pairs).
   - Where the later robot stopped 3-8 s before the frame (mostly before the
     clip starts): `dyn` 21/28, `static` 22/28.
   - The earlier event (32-183 s back) is invisible to any clip.

**What the pilot does support.** A frozen, motion-pretrained encoder with a
linear head trained on about 1.7k in-domain labels reads the information the
battery asks for off our annotated frames. gpt-4o's 0/12 temporal inversion
is therefore not a perception gap in the pixels: the cue (status colour) is
there and linearly decodable. This sharpens the H-JEPA assessment's (b) verdict
toward "VLM reasoning/inversion failure", not "missing motion features". It is
not evidence that V-JEPA's motion features fix it.

**What it confirms from the assessment's (a) verdict.** The non-learned
state baseline (CPA on GT positions and velocities, which M1 already
provides) beats the video probe on unseen families: 0.83 against 0.53
balanced accuracy. With state available, video is the wrong abstraction for
conflict forecasting at our data scale.

**Brief premise corrected.** The v3 S1a/S1b/IB10-closure bundles have GT but
**zero frames** (every `frames/` directory is empty, and there is no
recording). The dataset therefore comes from the pre-v3 bundles that carry an
in-bundle `annotated_*.mp4` recording or harvest snapshots.

Cost: $0 API. Mac only (M1 Pro, MPS). The VM was not touched. Wall time
about 32 min for feature extraction and under 1 min for probes.

---

## Decision Rule (Fixed Before Scoring)

The probe configuration below was selected by leave-one-episode-out CV on
TRAIN episodes only and frozen in this revision. Held-out TEST clips and the
mapped battery items are then scored exactly once.

**"Earns a thesis table"** requires all three:

- **T1.** The held-out conflict probe (`dyn`, command-free clips) reaches
  balanced accuracy >= 0.70, and its Wilson 95% lower bound on plain accuracy
  is above 0.5.
- **T2.** Motion is what the probe uses. `dyn` beats the `static` control
  (last frame repeated) by >= 0.10 on held-out conflict balanced accuracy, or
  by >= 0.10 on held-out broad temporal pair accuracy.
- **T3.** On the mapped battery conflict items, `dyn` scores at least
  gpt-4o + 3 on the same items. This is direction only; n is too small for a
  test.

Otherwise the result **earns a paragraph** (Discussion / Future Work), not a
table. Two readouts are fixed in advance as well:

- If `static` is within 0.05 of `dyn` on a task, that task's score is
  attributed to static cues (status colour, arrow, label, layout), not motion.
- On temporal_order, the earlier event lies 32-183 s before every battery
  frame, outside any clip. A clip probe can at best detect "which robot moved
  recently". The lower-id rule (15/19 on the full battery) and the
  drawn-STOPPED rule are the bars it has to clear.

## Frozen Configuration

Frozen at this revision from `data/logs/vjepa_pilot_20261011/probe/frozen.json`
(gitignored; reproduced here verbatim in substance).

| Setting | Value |
|---|---|
| Encoder | `facebook/vjepa2-vitl-fpc64-256` (ViT-L/16, ~300M params, MIT licence), frozen, fp32 on Apple MPS |
| Clip | 8 frames, 0.50-0.60 sim-s apart (3.0-5.2 s of history), 256x256, ImageNet mean/std |
| Tokens | 4 (tubelet 2) x 16 x 16, width 1024; pooled at extraction, never stored raw |
| Conflict crop | 960 px square centred on the pair midpoint at the last frame |
| Temporal crop | 480 px square centred on the robot at the last frame |
| Conflict features | `[g, (A+B)/2, abs(A-B), (dA+dB)/2, abs(dA-dB)]` (5x1024) |
| Conflict model | StandardScaler + LogisticRegression(class_weight=balanced), threshold 0.5; C = **0.0001** (dyn), **0.001** (static) |
| Conflict training rows | battery-identical label, command-free only: 375 clips (142 yes), 7 episodes, 5 scenario families |
| Temporal features | `[mean R, R_last-R_first, std R] (3x1024), robot-own pooled tokens only` |
| Temporal model | StandardScaler + Ridge on log1p(min(still_sec,30)); first = larger prediction; alpha = **1000** (dyn), **1000** (static) |
| Temporal training rows | 1725 robot clips, 8 episodes, 5 families |
| Selection | leave-one-scenario-family-out over TRAIN families only; selection metric balanced acc (conflict) / pair acc (temporal) |
| Broad temporal pair rule | same clip, abs(still_a - still_b) >= 2.0 s, later stop <= 8.0 s |
| Split | scenario families: test = ['bottleneck_merge', 'loop', 's6_dual_conflict']; train = ['blocked_path', 'dynamic_anomaly', 'intersection_bottleneck', 'obstacle_in_candidate', 't2b_flow_ordering'] |

CV scores on TRAIN families only (the selection data; not a result):

- conflict balanced accuracy, dyn: 0.0001: 0.732, 0.0003: 0.722, 0.001: 0.725, 0.003: 0.725, 0.01: 0.722, 0.03: 0.722, 0.1: 0.722
- conflict balanced accuracy, static: 0.0001: 0.573, 0.0003: 0.577, 0.001: 0.582, 0.003: 0.580, 0.01: 0.577, 0.03: 0.572, 0.1: 0.567
- temporal broad-pair accuracy (448 pairs), dyn: 10.0: 0.942, 100.0: 0.962, 1000.0: 0.973, 10000.0: 0.971, 100000.0: 0.967
- temporal broad-pair accuracy, static: 10.0: 0.920, 100.0: 0.938, 1000.0: 0.940, 10000.0: 0.926, 100000.0: 0.902

**Split change before scoring.** `build_dataset.py` first split by episode.
Before any held-out score was computed, the episode table showed same-scenario,
same-seed near-replays on both sides (`B1DEMO`/`B1DEMO2`, bottleneck_merge
seed 43; the two `t3b_smoke` runs). The split and the CV grouping were moved
to scenario families (`probe.py family_split`), and the probes refitted. The
features were not re-extracted; only the role labels changed.

---

## Dataset Card

Built by `scripts/pilot_vjepa/inventory.py` and `scripts/pilot_vjepa/build_dataset.py`.
The output is `data/logs/vjepa_pilot_20261011/dataset.json` (gitignored; SHA-256
`695d0f3f…`). Frames and GT are read in place from the main checkout's
`data/logs/vm_runs/`, and nothing is copied.

### Sources

| Source | Episodes | Frame timing |
|---|---|---|
| Battery-v2 harvest snapshots (`battery_v2_harvest/b2_*`) | 4 | sim stamp in the file name, 0.5-0.6 s spacing, occasional holes up to 1.7 s |
| In-bundle `annotated_*.mp4` recordings of `/perception/annotated_frame` | 22 usable | sim stamp read by OCR of the recorder's burned-in `t=…s f=N` clock |

- **Clock OCR.** The Mac OpenCV build draws Hershey glyphs differently from
  the VM's, so digit templates are harvested from each video's own `f=`
  field. That field is the running frame count, so its digits are known.
  - Checks: f-field self-consistency is 0-66 misreads per video, out of
    322-3,843 frames.
  - The first kept OCR stamp is within 0.01 s of `rec.log`'s first
    `header_stamp` on 19 of the 21 videos that have one. The two exceptions:
    - `v2_demo/ep2` (6.97 against 6.83): its first frames were dropped by
      the median filter.
    - `v3_reroute_demo` (6.03 against 8.03): it has a single robot and only
      temporal samples.
  - A stamp is kept only if it agrees within 1 s with its ±4-frame median and
    is monotone.
- **Clock leak removed.** The clock region (x < 340, y < 48) is blacked out
  on every frame from every source before cropping.
- **Geometry.** Robot centres projected from GT through
  `swarm_perception/config/calibration.yaml` land on the drawn M1 boxes in
  100% of probes on every usable episode (`inventory.json` `geometry`),
  including the s6 floor. One exception: `t0_t3c_verify/…113513` has its
  robots at or off the frame edge, so it yields 0 clips.
- **Unusable.** B1S1, IB9 and IB10 have truncated MP4s (no readable frames).
  Seven `_aborted` runs were skipped. All v3 bundles (S1a, S1b, IB10-closure,
  live_batch, churn) have GT but no frames.

### Episode roles

| Role | Episodes | Rule |
|---|---|---|
| battery (test-only) | `b2_headon_off`, `b2_convoy_off`, `IBB4_20260929_102427` | host the 59 battery-v2 main items |
| excluded twin | `b2_headon_on`, `b2_convoy_on` | trails-on harvest twins |
| excluded twin | `B3DEMO` | same scenario and seed as `b2_convoy_off` |
| excluded twin | `ER2LIVE`, `GPT4OLIVE`, `B2DEMO`, `t3c_v2/…125419`, `v2_demo/ep1_scripted` | some 8 s GT window (16 samples, 0.5 s apart) has every robot within 0.10 m of a battery item's window. This is the clip-level analogue of the battery near-duplicate rule. |
| train (5 families) | `blocked_path` (t3a ×2), `dynamic_anomaly` (t3c 123505, t0_t3c 113513), `intersection_bottleneck` (IBA1, v2 ep2), `obstacle_in_candidate` (t3b ×2), `t2b_flow_ordering` (D1) | seeded scenario-family split |
| test (3 families) | `bottleneck_merge` (B1DEMO, B1DEMO2), `loop` (both reroute demos, 1 robot), `s6_dual_conflict` (s6 live, s6 mock) | seeded scenario-family split, stratified on conflict-"yes" presence |

### Clips and labels

- **Clips.** 8 frames, 256×256.
  - Snapshot episodes use 8 consecutive snapshots ending at the item frame,
    with the span capped at 6 s.
  - Recordings take the nearest frame within 0.5 s to targets spaced
    0.50/0.53/0.56/0.60 s apart (a seeded choice per clip). This matches the
    snapshot timing.
  - Realised spans are 3.0-5.2 s (mean 3.8 s). 203 of the 3,128 extracted
    clips repeat a frame across a recorder hole.
  - The brief asked for 8-16 frames at 2-4 fps. 16 frames (7.5 s of history)
    left 7 of the 20 battery conflict items uncovered, because the harvests
    start too late. 8 frames covers 13.
- **Conflict label.** The battery's own `dynamics.conflict_prediction_answer`
  decides: "yes" if the pair's future minimum distance is <= 0.40 m within
  10 s, "no" if it is >= 0.65 m, and the band in between is dropped.
  - The pair must be >= 0.75 m apart, with one robot moving and the threshold
    reachable.
  - Plus the battery's reversing and ambiguous-speed drops and its
    command-free exclusion (`episode_v2.load_episode` windows).
  - **Deviation from the brief:** the brief's "below 0.45 m" falls inside the
    battery's dropped band. The battery rule is used so training and evaluation
    share one definition.
  - One M1-specific rule was not reproduced: there is no M1 state per video
    frame, so the M1 status-agreement drop is not applied to video clips.
- **Temporal target.** Per robot: the seconds since GT speed last exceeded
  0.03 m/s, capped at 30 s.
- **Temporal pairs.**
  - Broad pairs: two robots in the same clip whose targets differ by >= 2 s,
    with the later stop <= 8 s ago.
  - Battery-rule pairs: `dynamics.temporal_order_answer`.

| Split | Conflict, command-free (yes / no) | Conflict, all kinematic | Temporal robot clips | Broad pairs (lower id first) |
|---|---|---|---|---|
| train (families) | 142 / 233 | — | 1,725 | 448 CV pairs |
| test (families) | 29 / 77 | 37 / 125 | — | 145 |
| battery (mapped) | 13 items (7 yes / 6 no) | — | 12 items × 2 robots | — |

- On the original episode split, the lower id stopped first in 151/399 train
  pairs and 88/194 test pairs. These pairs carry no lower-id prior,
  unlike battery temporal_order (15/19).
- **Battery mapping.**
  - conflict: 13/20 mapped. Not mapped: 5 items in episodes with no dense
    frames (decision frames only: `t0_t3c_verify/111348`, `SW2R2`,
    `simtime_shadow_val`, `SW1_wait_s42` ×2) and 2 convoy items whose
    harvest starts too late.
  - temporal: 12/19 mapped. Not mapped: 7 items in decision-frame-only
    episodes (`plan_grammar_cal`, `t2b_smoke`, `SW1_*`).
  - Every mapped snapshot item's last clip frame is the battery frame itself.
  - IBB4 items use the recording frame nearest the decision stamp
    (0.03-0.13 s off). It is the same topic but not byte-identical to the
    PNG the VLMs saw.

---

## Method

- **Encoder.** `facebook/vjepa2-vitl-fpc64-256` (HF id verified 2026-10-11,
  MIT licence, transformers 5.19.0 `VJEPA2Model.get_vision_features`).
  - Frozen, fp32 on MPS.
  - Measured on this Mac: 0.67 s per 16-frame clip and 0.57-0.61 s per 8-frame
    clip-pair (dyn + static), including decoding.
- **Pooling instead of an attentive probe.** Tokens are pooled at extraction
  (global mean, per-tubelet mean, and a 3×3-patch pool at each robot's
  GT-projected position per tubelet), and fed to linear probes.
  - This deviates from the V-JEPA frozen-eval protocol, which uses an
    attentive probe on all tokens.
  - Two reasons: disk (13 GiB free; raw tokens are about 4 MB per clip),
    and n (375 conflict training clips would overfit an attentive probe).
- **Pair and robot conditioning.**
  - The conflict crop is centred on the pair, and the pair's two robot pools
    enter symmetrically.
  - The temporal regressor sees only the robot's own pool. Its crop shows
    neighbours, but the global token is not used.
- **Static control.** Each clip is also encoded as its last frame repeated 8
  times and given an identical, independently tuned probe. This control sees
  what a single-image VLM sees, without the text.
- **Baselines.**
  - conflict: always-yes, and constant-velocity closest approach from GT
    position and 0.5 s velocity (yes if <= 0.5 m within 10 s).
  - temporal: lower-id, and drawn-STOPPED (pick the robot M1 drew STOPPED,
    with ties going to the lower id). Battery items only, since M1 statuses
    are recorded per item.
- **VLM numbers** come from the frozen 2026-10-04 per-item JSONL
  (`battery_v2_20261004/{openai,gemini}__main`), re-scored on exactly the
  mapped items. Full-battery totals reproduce: 9/20, 16/20, 1/19, 12/19.
  No new API calls.

---

## Results (Single Scoring Pass)

### Held-out scenario families

| Set | n | `dyn` | `static` | Baselines |
|---|---|---|---|---|
| conflict, command-free | 106 (29 yes) | acc 0.689 [0.60, 0.77], **balanced 0.528**, said yes 14 | acc 0.594, balanced 0.452 | CPA balanced **0.831**; always-yes 0.274 acc |
| conflict, all kinematic | 162 (37 yes) | acc 0.599, balanced 0.474 | acc 0.556, balanced 0.436 | CPA balanced 0.896 |
| temporal, broad pairs | 145 | 0.952 [0.90, 0.98] | 0.959 [0.91, 0.98] | lower-id 0.531 |
| temporal, battery-rule pairs | 7 | 7/7 | 7/7 | lower-id 7/7 |

- **Conflict by episode (`dyn`).**
  - B1DEMO2: yes 0/15, no 16/16.
  - B1DEMO: yes 0/9, no 52/61.
  - s6 live: yes 5/5.
- **Temporal by the age of the later stop (`dyn` / `static`):**

  | Age of the later stop | `dyn` | `static` |
  |---|---|---|
  | still moving (< 0.5 s) | 100/100 | 100/100 |
  | 0.5-3 s | 17/17 | 17/17 |
  | 3-8 s | 21/28 | 22/28 |

- The episode-cluster bootstrap is reported in `results.json`. With 2-3 test
  episodes it is not informative and is not quoted.
- The clip-level Wilson intervals treat clips 0.5 s apart as independent.
  They are optimistic.

### Battery items (mapped subset)

The table is in the Summary. Per-item probe scores, VLM answers and M1
statuses are in `data/logs/vjepa_pilot_20261011/probe/results.json`.

- The probe's conflict probabilities are 0.85-0.94 on "yes" items and
  0.17-0.30 on "no" items for `dyn`, and 0.96-0.98 / 0.04-0.37 for `static`.
  `static` is more confident.

### Decision rule outcome

| Criterion | Value | Result |
|---|---|---|
| T1: held-out conflict balanced >= 0.70 and Wilson lower bound > 0.5 | 0.528 (Wilson LB 0.60 on plain accuracy) | **fail** |
| T2: `dyn` - `static` >= 0.10 on held-out conflict balanced or temporal pairs | +0.076 / -0.007 | **fail** |
| T3: battery conflict `dyn` >= gpt-4o + 3 | 13 against 5 | pass |

**Earns a paragraph.**

---

## Protocol Caveats (Read Before Citing Any Number)

1. **Not protocol-identical.**
   - The VLMs answered a TEXT question about one annotated frame, zero-shot,
     with lettered options.
   - The probe sees an 8-frame clip and was SUPERVISED on in-domain GT labels
     for exactly this question form.
   - Put the probe row beside the VLM rows only as "what a frozen video
     encoder plus about 400 / 1,700 in-domain labels can read off these
     frames". It is not "V-JEPA beats gpt-4o".
2. **Mapped subset only.** 13/20 and 12/19 items. The VLMs' mapped-subset
   scores (5/13, 12/13, 0/12, 6/12) are the comparison, not 9/20 and 16/20.
3. **Static cues dominate the battery.** The `static` control ties `dyn` on
   every battery item. Battery-v2 conflict and temporal items on annotated
   frames are answerable from one frame by a supervised linear probe. This
   reinforces the battery-v2 report's own temporal_order confound list
   (status-colour cue, long gaps) and adds a scene/phase cue for
   conflict_prediction.
4. **Family overlap with the battery.** `intersection_bottleneck` (IBA1,
   v2 ep2) is in training, and IBB4 hosts 2 mapped conflict and 3 mapped
   temporal items. The trajectory near-duplicate rule removed the true
   replays, but not shared layout. The held-out-family result (0.53) is the
   honest generalisation number.
5. **Small held-out set.** 2 families with conflict labels, 3 episodes,
   autocorrelated clips.
6. **Annotated frames only.** No raw frames exist for the recordings, so the
   encoder always sees M1's boxes, labels, arrows and status colours.
   - This matches what the VLMs saw.
   - It also means a "motion encoder" is never tested on unannotated motion.

---

## Runtime Notes

| Step | Time |
|---|---|
| venv (`torch 2.14.1`, `transformers 5.19.0`, cv2 5.0.0) at `…/vgu-vlm-swarm-v3x-venv`, plus the 1.3 GB checkpoint download | a few minutes |
| Inventory + clock OCR of 22 recordings | about 75 s |
| Dataset build | about 20 s |
| Feature extraction (3,128 clips × 2 variants, ViT-L, MPS fp32) | 1,910 s |
| Probe CV + fit / score | < 1 min each |

- Disk: pooled fp16 features are 117 MB, against about 13 GiB free.
- ViT-L fits comfortably. The brief's > 6 h fallback (smaller checkpoint) was
  not needed.
- A VM run would only help with larger frame sets, and those would need new
  recordings with raw frames.

---

## Recommendation

- **Thesis use: a paragraph** in Discussion/Future Work, beside the H-JEPA
  assessment's (a)/(b) verdicts. Suggested content:
  - A frozen V-JEPA 2 ViT-L with a linear probe reads the battery's answers
    off our annotated frames, but a single-frame control does equally well.
  - On unseen scenario families its conflict prediction is at chance (0.53
    balanced), while a constant-velocity rule on M1-style state reaches 0.83.
  - Video-pretrained motion features do not add usable foresight over the
    state M1 already provides. gpt-4o's temporal failure is a reasoning
    failure over cues that are present, not missing motion features.
- **Do not** put the 13/13 and 12/12 in a results table beside gpt-4o and
  ER-2. The static control explains them.
- **If revisited**, the test that would mean something needs:
  - unannotated (raw) recordings, which need a recorder change on the VM;
  - an arrow- and colour-free condition, as in battery-v2 open item 2;
  - more scenario families for conflict;
  - a temporal_order rebuild with both events inside the clip window
    (battery-v2 open item 1).

  The dataset scripts here are reusable as-is for that.

---

## Artifacts

Code (committed): `scripts/pilot_vjepa/`

| File | Role |
|---|---|
| `common.py` | OCR, frame index, clip matching, crops |
| `inventory.py` | inventory and OCR checks |
| `build_dataset.py` | roles, labels, battery mapping |
| `extract_features.py` | frozen encoder and pooling |
| `probe.py` | `fit` / `score` |
| `stats.py` | dataset card |

Data (gitignored), under `data/logs/vjepa_pilot_20261011/` in the worktree:

| Path | Contents |
|---|---|
| `inventory.json` | inventory and OCR checks |
| `timelines/*.json` | per-frame OCR |
| `dataset.json` | the reusable clip dataset |
| `features/{dyn,static}.npz` | pooled features |
| `features/index.json` | per-clip metadata and frame stamps |
| `probe/frozen.json` | the frozen configuration |
| `probe/{dyn,static}.pkl` | fitted probes |
| `probe/results.json` | scoring output |
| `stats.json` | dataset-card statistics |
| `extract.log` | extraction log |

---

## Rev 2: Static-Control Bug Fix (Frozen Before Re-Scoring)

**Bug (found in review after the Rev 1 scoring pass).** The `static` clip
showed only the last frame. Its robot pools, however, were taken at each
tubelet's GT trajectory position, the same positions as `dyn`.

- For a robot that moved, the early tubelets pooled background where it used
  to be.
- So `ra[-1] - ra[0]` and `dA`/`dB` in the "static" features encoded the GT
  trajectory.
- Check on held-out temporal robot clips, mean `||ra[-1] - ra[0]||`:
  - leaky static: 51.5 for moving robots against 38.0 for robots still >= 30 s;
  - fixed static: 37.7 against 38.0.

**Fix.** `0eb4b13`. Static pools every tubelet at the last-frame position
(`extract_features.pool_patches`).

- Only the static variant was re-extracted, in 917 s.
- `dyn` features, the `dyn` probes and the split are byte-identical to Rev 1
  (`frozen.json` diff).
- Rev 1 artifacts are kept as `features/static_rev1_leaky.npz` and
  `probe_rev1/`.

**Refit with the same procedure** (leave-one-family-out on train families
only). The selection data is not a result:

| Probe | Selected | Leaky Rev 1 static (superseded) |
|---|---|---|
| static conflict | C = **0.03**; CV balanced 0.501-0.519 across the grid | C 0.001, CV 0.582 |
| static temporal | alpha = **1000**; CV pair accuracy 0.924 | 0.940 |

This configuration is committed before the corrected static probe scores
any held-out or battery item. Decision rule unchanged.
