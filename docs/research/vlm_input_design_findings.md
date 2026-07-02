# VLM Input Design — Research Findings

**Prepared:** 2026-06-15

**Revision history:**

- Initial draft: findings on what to feed the M2 VLM (single image vs temporal/video), current M2 input-encoding issues grounded in code, and recommendations with citations.
- Rev 2 (2026-06-15): calibrated the anti-video conclusion to snapshot-first + ablation; corrected "no temporal signal" to "no explicit history/windowed signal" (velocity is derived from temporal differencing); separated implemented / specified / recommended M5 behavior; softened SwarmVLM, DUAL-VAD, and Garg-token claims; added balanced temporal-input evidence (NaVid, ContextVLA); fixed cadence/heading-arrow/timestamp wording.
- Rev 3 (2026-06-15): reclassified Co-NavGPT as textual map-feature encoding (not image-to-VLM); reframed Layer 2 as event-driven per the M2 spec (≤15 s/attempt, ~30 s worst case) instead of a 0.5–2 Hz rate; split the ablation into separate M5-detector and M2-classifier evaluations; marked SwarmVLM temporal/token cost as "not reported"; distinguished Garg's and VGU's detectors as a shared pattern; renamed the proposed field to `stall_duration_sec`; presented the 2–4-frame stack as this project's hypothesis; made goal coords+IDs in text required; cited Garg as a preprint/manuscript.
- Rev 4 (2026-06-15): reverted the Rev 3 Co-NavGPT error — v3 uses GPT-4o with annotated top-view map images, so it is image-snapshot-to-VLM evidence; distinguished specified (15/30 s) from code-default (30 s) and currently-configured (120 s / ~240 s) M2 latency; qualified that `distance_to_goal_delta` needs added history beyond M5's running-minimum; changed "confirmed congested" to "confirmed stalled / congestion candidate"; made the stall-duration overlay explicit about needing a zero-velocity timer; aligned SwarmVLM §3.1 prose with the table; separated current-vs-proposed detection ownership in the overview; reframed status duplication as benign and kept textual status.

---

## 1. Overview

This is a research-only report on the **input to the M2 VLM**: what data the
reasoner should receive, and whether the current single-image design is adequate.
Note the responsibility split this report recommends: **M5 detects** congestion
and **M2 classifies/resolves** it. Today M2's prompt still performs detection
itself (it decides `congestion_detected`); §6 proposes moving detection to M5.

The investigation was prompted by a design concern: congestion and deadlock are
**temporal** phenomena, yet M2 currently reasons over a single still frame. The
report separates verified facts from the literature from recommendations for the
VGU pipeline.

Throughout, behaviors are tagged as **implemented** (present in code),
**specified** (described in a spec but not yet coded), or **recommended** (this
report's proposal).

Scope:

- What the reviewed multi-robot / swarm coordination systems feed their VLMs.
- Whether single image, temporal frame stacks, or video is the right modality.
- What information is embedded in the VGU annotated frame today (from code).
- Recommendations that fit M2's event-driven invocation (M5 triggers). Latency
  budgets differ by layer: **specified** ≤15 s/attempt (~30 s worst case,
  `module2_vlm_reasoning.md`); **code default** 30 s (`models.py`); **currently
  configured** 120 s × 2 attempts ≈ 240 s worst case (`config/models.yaml`,
  sized for the Cosmos Reason 2 reasoning trace).

---

## 2. Sources Checked

| Source | ID | Relevance to VLM input |
|---|---|---|
| Zafar et al. 2025, SwarmVLM | arXiv:2508.07814 | Warehouse swarm, VLM-RAG, top-down visual input (no temporal sequence described); shares the top-view → VLM → RAG pattern with VGU |
| Garg et al. 2026, VLMs as High-level Planners (deadlock), preprint | mit-realm (manuscript) | Deadlock = numeric trigger, then single rendered top-view image; ~constant visual token cost in their experiments |
| Batool et al. 2025, ImpedanceGPT | arXiv:2503.02723 | VLM-RAG mini-drone swarm; single top-down view |
| Zhang et al. 2024, NaVid | arXiv:2402.15852 | Video-based VLM; encodes historical observations as spatio-temporal context (positive temporal evidence) |
| Jang et al. 2025, ContextVLA | arXiv:2510.04246 | Multi-frame context compressed to one token; improves over single-frame VLA (positive temporal evidence) |
| Schroeder et al. 2025, ROVER | arXiv:2508.01943 | Long *unmanaged* frame context degrades VLM reasoning; recursive decomposition mitigates it |
| Pan et al. 2026, Thinker | arXiv:2601.21199 | Improves video understanding by combining key frames **with** full sequences |
| Jung et al. 2025, DUAL-VAD | arXiv:2509.11605 | Anomaly-focused temporal sampling improves relevant baselines (distinct frame- vs video-level benchmarks) |
| Zou et al. 2025, ASK-Hint | arXiv:2510.02155 | Structured prompting lets a frozen VLM do video anomaly detection |
| Cheng et al. 2025, V-STaR | arXiv:2503.11495 | Spatio-temporal "when→where→what" reasoning for events |
| Schroeder et al. 2026, SOLE-R1 | arXiv:2603.28730 | Per-timestep spatio-temporal CoT for progress estimation |
| Abaza et al. 2026, Semantic Autonomy Stack | arXiv:2605.02525 | VLM inference 2–9 s on edge; ~88% of decisions routed away from the VLM |
| Wang et al. 2025, COMRES-VLM | arXiv:2509.26324 | VLM reasons over shared map + state snapshot (not video) |
| Yu et al. 2023, Co-NavGPT (v3) | arXiv:2310.07937 | GPT-4o reasons over annotated top-view map *images* (frontiers as colored dots) + text; image-snapshot-to-VLM, a close analog to VGU's Set-of-Mark frame |
| Yang et al. 2023, Set-of-Mark | arXiv:2310.11441 | Visual-mark overlays improve VLM spatial grounding |

---

## 3. Findings

### 3.1 The reviewed coordination systems favor compact snapshots

Across the multi-robot / swarm coordination systems reviewed here, the input is
typically one compact symbolic snapshot (a map or annotated top-down view plus a
robot-state list) rather than raw video. This is a pattern in the reviewed
sample, not an established universal.

- **SwarmVLM** (Zafar et al. 2025) processes top-down visual input (no temporal
  sequence described) with a lightweight local model (Molmo-7B-D 4-bit); 92%
  navigation success, 80% VLM-RAG accuracy under good lighting.
- **Garg et al. 2026** send a single rendered top-view image (agents, goals,
  obstacles seen so far) plus a text list of coordinates.
- **COMRES-VLM** reasons over a single aggregated occupancy-map snapshot, not
  frames.
- **Co-NavGPT** (v3) feeds GPT-4o annotated top-view map *images* (candidate
  frontiers as colored dots) plus text — a single-snapshot, Set-of-Mark-style
  input close to VGU's annotated frame, not a frame sequence.

In these systems the temporal information the model needs is carried inside the
state / rendered snapshot, not as a pixel sequence.

### 3.2 Congestion is temporal, but detection can be a cheap numeric trigger

Congestion and deadlock are temporal: a still frame cannot distinguish "stopped
for 0.3 s at a pick station" from "deadlocked for 30 s."

The strongest match to VGU's problem, **Garg et al. 2026**, resolves this
without feeding video. They detect deadlock with a numeric criterion computed by
the low-level system — *instantaneous average swarm speed below a threshold while
average goal distance stays high* — and only **then** invoke the VLM, reactively,
on a single snapshot. The temporal reasoning lives in the **trigger**; the
semantic reasoning lives in the **VLM**.

VGU **shares this architectural pattern** (a numeric gate before the VLM) but
specifies a **different detector**: per-robot *lack of distance-to-goal
improvement over a duration*, rather than an instantaneous swarm-wide average.
That gate is **specified** for VGU M5 (`module5_orchestrator.md` FR5.1.1:
distance-to-goal progress tracking, `stall_threshold_sec`) but **not yet
implemented**: the current `congestion_detector.py` is a single threshold helper
(`is_congested(wait_time_sec, threshold_sec)`), and the orchestrator node is a
scaffold.

### 3.3 Unmanaged long-context / raw video carries real costs under M2's budget

M2 is **event-driven**, not fixed-rate: `module2_vlm_reasoning.md` specifies M5
triggers a reasoning pass on congestion. The per-call budget differs between spec
and runtime — **specified** ≤15 s (~30 s worst case), **configured** 120 s × 2 ≈
240 s (`config/models.yaml`, sized for the Cosmos Reason 2 trace). Either way the
pass is multi-second, so raw frame sequences must be *managed*, not dumped in:

- **ROVER** (2025): VLMs "struggle in settings that require reasoning over
  extended sequences of camera frames," and long *unmanaged* context increases
  hallucinations; their fix is recursive decomposition, not abandoning temporal
  input.
- **Semantic Autonomy Stack** (2026): VLM inference is 2–9 s per decision on
  edge hardware; they route ~88% of decisions away from the VLM entirely.
- **Garg et al. 2026**: in their experiments the image-modality token cost is
  approximately constant (~1000 tokens) regardless of scene complexity, because
  all information is plotted onto a same-sized graphic. They did **not** test
  frame sequences; the expectation that multi-frame input would raise token cost
  is therefore a hypothesis to **measure**, not a result they established.

### 3.4 Temporal input demonstrably helps in robotics when managed

Counter-evidence that temporal input is beneficial, not merely tolerable:

- **NaVid** (Zhang et al. 2024): a video-based VLM for vision-and-language
  navigation that encodes historical observations as spatio-temporal context and
  reaches state-of-the-art navigation from a monocular RGB stream.
- **ContextVLA** (Jang et al. 2025): compresses past observations into a single
  context token and **consistently improves over single-frame VLAs**, capturing
  temporal cues (e.g., robot movement) with reduced training/inference cost —
  direct support for *compact temporal summaries* over both single-frame and
  full-video extremes.
- **Thinker** (Pan et al. 2026): improves video understanding by combining key
  frames **with** full sequences (managed temporal input helps).

### 3.5 Temporal input also helps in offline video understanding — different shape

Video-level input benefits **offline** video understanding, a higher-latency,
larger-budget regime than VGU's reactive Layer 2:

- **DUAL-VAD** (Jung et al. 2025): anomaly-focused temporal sampling improves the
  relevant baselines. The frame-level and video-level results come from
  *distinct* benchmarks, so this is not a controlled universal "video beats
  image" result.
- **ASK-Hint** (2025), **V-STaR** (2025), **SOLE-R1** (2026): structured
  prompting / spatio-temporal reasoning for events and progress estimation.

### 3.6 What the VGU frame embeds today (implemented, from code)

The VGU annotated frame (`ros2_ws/src/swarm_perception/swarm_perception/annotation.py`)
embeds, per robot:

| Overlay | Encodes | Note |
|---|---|---|
| Status-colored box | MOVING=green, SLOW=yellow, STOPPED=red, STALE=gray | color is the only status cue |
| ID text label | `robot_id` | above the box |
| Heading arrow | heading (`theta`) only | drawn when speed > 0 but **fixed 40 px length**; does not encode the measured velocity vector |
| Goal marker | `robot.goal` | image-only |

A parallel **text channel** in `reasoning/vlm/prompt_builder.py` carries
`robot_id, x, y, theta, status, task, linear_velocity, angular_velocity`, the
known-ID list, the congestion taxonomy, a 0.5 m conflict heuristic, and the JSON
output schema. `linear_velocity` / `angular_velocity` are derived from
consecutive observations via finite differences and a first-order low-pass
filter (`state_estimator.py`).

---

## 4. Current M2 VLM Architecture Issues

- **No explicit history, persistence, or windowed-progress signal.** Velocity is
  a *derived temporal quantity* (finite difference + LPF in `state_estimator.py`),
  so the input is not strictly atemporal. But it is delivered as an instantaneous
  scalar with no accumulation: there are no position trails, no stall/stopped
  duration timer, no progress-toward-goal delta. A robot stopped for 0.3 s and
  one deadlocked for 30 s therefore render identically (same red box, same
  velocity ≈ 0, same text).

- **`status=STOPPED` is instantaneous.** It is derived from a velocity
  threshold, not duration, so it cannot itself disambiguate transient stops from
  deadlocks.

- **Channel asymmetry.** Some cues live in only one channel: `linear_velocity`
  magnitude is text-only (the heading arrow is fixed length and conveys no
  speed), and `goal` is image-only (omitted from the text block), so the VLM
  must fuse two partial views. Note `status` is sent in both channels (box color
  + text); that duplication is redundant **but consistent** and is not itself a
  defect — keeping textual status is safer than forcing the VLM to rely on box
  color alone.

- **Detection currently sits in the VLM prompt, not a pre-VLM gate.** The prompt
  asks the VLM to decide `congestion_detected` from a single frame. Garg et al.
  confirm congestion numerically *before* the VLM is called; VGU specifies this
  in M5.1 but has not yet implemented it.

---

## 5. Comparison Matrix

| Criterion | VGU (current) | SwarmVLM | Garg et al. 2026 |
|---|---|---|---|
| Input modality | Single annotated image + text state | Top-down visual input (sequence not described) | Single rendered top-view + text coords |
| Temporal info in input | Derived velocity (instantaneous); no history | Not reported | Accumulated obstacles drawn into image |
| Congestion/deadlock detection | VLM decides from one frame (M5.1 numeric gate specified, not implemented) | Implicit | Numeric trigger before VLM |
| Speed encoded visually | No (fixed-length heading arrow) | n/a | n/a |
| Token cost vs scene size | Grows with text state | Not reported | Constant (~1000, reported) |
| Latency posture | M2 event-driven; ≤15 s/attempt specified, 120 s/~240 s configured | Slow layer | Bounded query frequency |

---

## 6. Recommendation

Adopt a **snapshot-first** design and **validate it against alternatives with an
ablation** — do not categorically reject temporal input. The reviewed
coordination systems and the latency evidence favor a compact snapshot, but
NaVid and ContextVLA show managed temporal input can help, so the choice should
be measured in VGU's own domain, not assumed.

### 6.1 Implement the specified M5.1 numeric trigger (specified → implement)

The progress-based detector is already **specified** (`module5_orchestrator.md`
FR5.1.1) but only scaffolded in code. Implement it so the VLM is invoked only on
scenes already flagged as a **congestion candidate** (one or more robots stalled;
M5 fires on a single stall, since spatial clustering is FR5.1.6 future work), and
then **classifies and resolves** rather than detects from scratch (shares Garg et
al.'s gate-before-VLM pattern). A stall is the trigger; whether it is true swarm
congestion is part of what M2 then assesses.

### 6.2 Carry temporal state fields into the prompt (recommended)

Add per-robot temporal fields to `RobotStateInput` and render them in
`format_robot_state_lines`, populated from M5's progress history:

- `stall_duration_sec` — `now − last_improved_at`, the time without
  distance-to-goal improvement. This is what M5's specified progress detector
  tracks (`min_distance` + `last_improved_at`); note a robot creeping sideways
  still counts as stalled. A true zero-velocity `stopped_duration_sec` would
  require a separate velocity-threshold timer and is not available from M5.
- `distance_to_goal_delta` — progress over a fixed window. **Not directly
  available** from M5, which keeps only the running minimum and `last_improved_at`;
  this needs added timestamped distance history or a stored window-start value.

Additive and backend-agnostic; no image-format change.

### 6.3 Strengthen the visual channel (recommended)

In `annotation.py`, make the rendered frame carry the cues it currently drops:

- **Speed-proportional arrow length** so the image conveys velocity magnitude.
- **Stall-duration color ramp** (color deepens the longer a robot is stalled),
  driven by M5's `stall_duration_sec`. A zero-velocity "stopped"-duration ramp
  would need the separate velocity-threshold timer noted in §6.2.
- Optional **position trails** (last N centers) for motion-over-time.

### 6.4 Resolve the channel asymmetry (recommended)

**Require goal coordinates and robot IDs in the text channel.** Today the goal is
image-only and drawn in the robot's status color with no label
(`annotation.py:61-66`), so robots sharing a status have indistinguishable goal
markers — the VLM cannot reliably attribute a goal to a robot from the image
alone. Keep `status` in both channels (text + box color); the duplication is
consistent and safer than color-only. The fix is to close the *one-sided* cues
(goal, velocity), not to remove the redundant one.

### 6.5 Evaluate detection and classification separately (recommended)

The architecture splits detection (M5) from classification/resolution (M2), so
the evaluation must too. Conflating them is what an earlier draft did.

**6.5a — M5 detector evaluation (no VLM).** On VGU congestion scenarios (M6.4),
measure the numeric trigger against ground-truth congestion onsets:
precision, recall, and trigger delay. This validates *when* the VLM is invoked.

**6.5b — M2 input-encoding ablation (after a confirmed trigger).** Holding the
M5 trigger fixed, vary only what M2 receives and measure classification accuracy
(congestion type), involved-robot identification, and strategy quality:

1. **Snapshot** — current single annotated frame + instantaneous state.
2. **Temporal text** — snapshot + `stall_duration_sec` / progress deltas (§6.2).
3. **Trajectory overlay** — snapshot + rendered trails / speed-scaled arrows (§6.3).
4. **Sampled frames** — a small managed key-frame stack; **2–4 frames is this
   project's hypothesis** (managed-temporal input helps per Thinker/ContextVLA;
   the specific count is not taken from any cited paper).

Together these turn "image vs video" from an assumption into a measured result
and keep the detection/classification responsibilities distinct.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Temporal summary does not match the frame it is paired with | Beyond `RobotState.stamp ≤ SceneState.stamp` (ordering only), attach explicit history-window start/end timestamps to the temporal fields and validate freshness before invoking the VLM |
| Detector state corrupted by dropped/late frames | Hold detector timers on `dropped_frame=True` (M5.1 FR5.1.4) |
| Added overlays clutter the frame and hurt VLM reading | A/B against the ablation harness (§6.5, M6.4); keep overlays sparse, Set-of-Mark style (Yang et al. 2023) |
| Trails/frames inflate latency | Cap trail length; if sampling frames, keep the stack small and managed (managed-temporal input per Thinker/ContextVLA; the 2–4 count is our hypothesis, §6.5), and measure token/latency cost rather than assuming it (§3.3) |
| Over-claiming novelty of temporal state | Frame as an additive engineering choice; the temporal-trigger idea is credited to Garg et al. 2026 |

---

## 8. Sources

- [SwarmVLM (Zafar et al. 2025) - arXiv:2508.07814](https://arxiv.org/abs/2508.07814)
- [VLMs as High-level Planners for Deadlock Resolution (Garg et al. 2026, preprint/manuscript — venue record not finalized)](https://mit-realm.github.io/VLM-gcbfplus-website/)
- [ImpedanceGPT (Batool et al. 2025) - arXiv:2503.02723](https://arxiv.org/abs/2503.02723)
- [NaVid (Zhang et al. 2024) - arXiv:2402.15852](https://arxiv.org/abs/2402.15852)
- [ContextVLA (Jang et al. 2025) - arXiv:2510.04246](https://arxiv.org/abs/2510.04246)
- [ROVER (Schroeder et al. 2025) - arXiv:2508.01943](https://arxiv.org/abs/2508.01943)
- [Thinker (Pan et al. 2026) - arXiv:2601.21199](https://arxiv.org/abs/2601.21199)
- [DUAL-VAD (Jung et al. 2025) - arXiv:2509.11605](https://arxiv.org/abs/2509.11605)
- [ASK-Hint (Zou et al. 2025) - arXiv:2510.02155](https://arxiv.org/abs/2510.02155)
- [V-STaR (Cheng et al. 2025) - arXiv:2503.11495](https://arxiv.org/abs/2503.11495)
- [SOLE-R1 (Schroeder et al. 2026) - arXiv:2603.28730](https://arxiv.org/abs/2603.28730)
- [Semantic Autonomy Stack (Abaza et al. 2026) - arXiv:2605.02525](https://arxiv.org/abs/2605.02525)
- [COMRES-VLM (Wang et al. 2025) - arXiv:2509.26324](https://arxiv.org/abs/2509.26324)
- [Co-NavGPT (Yu et al. 2023, v3: GPT-4o over annotated top-view map images) - arXiv:2310.07937](https://arxiv.org/abs/2310.07937)
- [Set-of-Mark Prompting (Yang et al. 2023) - arXiv:2310.11441](https://arxiv.org/abs/2310.11441)
