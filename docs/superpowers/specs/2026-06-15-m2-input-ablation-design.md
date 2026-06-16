# M2 VLM Input-Encoding Ablation — Design

**Prepared:** 2026-06-15

**Revision history:**

- Initial draft: design for an offline ablation harness comparing four M2 VLM
  input encodings, fed from recorded scenes, validated against the mock backend.

---

## 1. Overview

This design covers an **offline ablation** for the M2 VLM reasoner: it compares
how four different input *encodings* of the same scene affect congestion
classification. It implements the M2-classifier ablation proposed in
`docs/research/vlm_input_design_findings.md` §6.5b, holding the (future) M5
trigger fixed by replaying pre-recorded, already-triggered scenes.

The harness varies **only what M2 receives** and measures classification
accuracy and output validity. It does not implement the M5 progress detector,
production frame-overlay changes, or the live model run; those are out of scope
(§9).

The four input variants under test:

1. **Snapshot** — current annotated frame + instantaneous robot-state text
   (today's M2 input; the baseline).
2. **Temporal text** — snapshot plus per-robot `stall_duration_sec` and
   `distance_to_goal_delta` text fields.
3. **Trajectory overlay** — a rendered current frame carrying position trails,
   speed-proportional arrows, and labeled goal markers, plus base state text.
4. **Keyframe stack** — 2–4 frames sampled across the scene history (default 3),
   plus base state text.

Together these turn "image vs. video for M2" from an assumption into a measured
result. **Decision (M5) is evaluated separately** and is not part of this work.

---

## 2. Goals and Non-Goals

**Goals:**

- A pluggable `InputEncoder` boundary with four implementations.
- A `RecordedScene` dataset format that accepts synthetic geometry now and real
  Isaac-recorded frames later, with no code change.
- An offline harness that runs `encoders × backend` over a labeled dataset and
  reports per-encoder metrics.
- Full offline, deterministic unit coverage against the mock backend.

**Non-Goals (see §9 for the full list):** the M5 trigger, production overlay
changes, the live Cosmos Reason 2 run, Isaac-recorded data, strategy-quality
scoring.

---

## 3. Module Layout

New code lives under M2's home (`reasoning/vlm/`); the runner lives in
`benchmarks/`:

```text
reasoning/vlm/ablation/
  __init__.py
  scene.py        # RecordedScene, SceneFrame, GroundTruthLabel + JSON loader
  encoders.py     # InputEncoder Protocol + 4 encoders
  rendering.py    # offline frame renderer (boxes, trails, speed arrows, goals)
  metrics.py      # type accuracy, involved-robot P/R/F1, valid-output rate
benchmarks/runners/vlm_input_ablation.py   # CLI: dataset × encoders × backend
data/ablation/scenes/      # synthetic scene fixtures (JSON geometry + labels)
benchmarks/results/        # generated reports (JSON + markdown)
```

The ablation renderer (`rendering.py`) is **deliberately separate** from
`ros2_ws/src/swarm_perception/swarm_perception/annotation.py`: `reasoning/`
must not import the ROS2 package (CLAUDE.md module boundaries), and the
production overlay work (research §6.3) is out of scope here.

---

## 4. Data Model

All models are frozen Pydantic v2, consistent with existing M2 contracts.

- **`GroundTruthLabel`**
  - `type: Literal["none", "deadlock", "bottleneck", "crowding", "anomaly"]`
  - `involved_robots: list[str]`

- **`SceneFrame`**
  - `stamp: float` (`ge=0`)
  - `robots: list[RobotStateInput]`
  - `image_path: str | None = None` — set for Isaac-recorded scenes; `None`
    means the frame is rendered from geometry by `rendering.py`.

- **`RecordedScene`**
  - `scene_id: str` (`min_length=1`)
  - `frames: list[SceneFrame]` — chronological, non-empty; the last frame is the
    "current" timestep. A validator enforces non-decreasing `stamp`.
  - `known_robot_ids: list[str]`
  - `label: GroundTruthLabel`
  - Validator: every `label.involved_robots` id and every per-frame `robot_id`
    must be in `known_robot_ids`.

### 4.1 Temporal fields on `RobotStateInput`

Add three **optional, default-`None`** fields to the existing
`reasoning/vlm/models.py:RobotStateInput` (additive; matches research §6.2):

- `goal: tuple[float, float] | None = None`
- `stall_duration_sec: float | None = None`
- `distance_to_goal_delta: float | None = None`

These default `None`, so the production prompt path (`build_prompt_payload`) is
unaffected: it simply does not populate or render them today. The snapshot
encoder ignores them (preserving variant 1 exactly); the temporal encoder
renders them. That difference is the ablation contrast.

### 4.2 Dataset format

Each scene is a JSON file under `data/ablation/scenes/` holding a serialized
`RecordedScene`. Synthetic fixtures carry geometry only (`image_path: null`) and
are rendered at load time; Isaac-recorded scenes will instead reference real
PNG `image_path`s. The loader (`scene.py`) reads a directory of JSON files into
`list[RecordedScene]`, raising on malformed files.

---

## 5. Input Encoders

`InputEncoder` is a `Protocol` (mirroring `VLMBackend`/`FrameSource`):

```python
class InputEncoder(Protocol):
    def encode(self, scene: RecordedScene) -> PromptPayload: ...
```

A `FrameProvider` resolves a `SceneFrame` to a concrete image path: it returns
the frame's `image_path` if set, else renders the frame from geometry via
`rendering.py` into a work directory and returns that path.

| Encoder | Image(s) | State text |
|---|---|---|
| `SnapshotEncoder` | current frame | instantaneous state (today's `build_prompt`) |
| `TemporalTextEncoder` | current frame | state + `stall_duration_sec`, `distance_to_goal_delta` |
| `TrajectoryOverlayEncoder` | rendered current frame w/ trails + speed arrows + goals | base state |
| `KeyframeStackEncoder` | 2–4 sampled frames (default 3) | base state, noting the sequence |

- `SnapshotEncoder` delegates to `build_prompt_payload` (or its line formatter)
  unchanged, so variant 1 stays byte-for-byte the production input.
- `TemporalTextEncoder` extends the per-robot line formatter to append temporal
  fields when present.
- `TrajectoryOverlayEncoder` renders one frame: per-robot position trails (last
  `N` centers, `N` capped), speed-proportional heading arrows, and labeled goal
  markers, Set-of-Mark style.
- `KeyframeStackEncoder` uniformly samples `k` frames (default 3, clamped to
  available history) across the scene and emits a multi-image payload.

---

## 6. Multi-Image Contract Change

Variant 4 requires more than one image per call. Change
`reasoning/vlm/models.py:PromptPayload`:

- `image_path: str` → **`image_paths: list[str]`** (`min_length=1`).

Downstream updates:

- `prompt_builder.build_prompt_payload` passes `[request.image_path]` (single —
  production behavior unchanged).
- `LlamaServerBackend._build_messages` loops over `image_paths`, attaching each
  as an `image_url` content part **before** the text part, preserving the
  media-first ordering established for Cosmos Reason 2.

`ReasonerRequest` stays single-image (`image_path`): the production M2 path
still feeds one frame; multi-image is an ablation-only construction built
directly by the keyframe encoder.

**Verification (pre-live-run only):** confirm `llama-server` accepts multiple
`image_url` parts in one request against current docs (CLAUDE.md external-library
rule). The harness validates against the mock backend, so this does not block the
build; it is a checklist item before any live Cosmos Reason 2 run.

---

## 7. Reasoner Seam

`Reasoner.run(request)` currently builds the payload internally via
`build_prompt_payload(request)`, so the harness needs a way to inject an
encoder-built payload.

Refactor: extract the retry / parse / re-ask / validate loop into

```python
Reasoner.run_payload(payload: PromptPayload, request_id: str,
                     known_ids: set[str]) -> ReasonerResult
```

`run(request)` keeps its input validation (duplicate-id check, image existence),
builds the payload, then delegates to `run_payload`. `build_failed_result` is
generalized to take `request_id` instead of the whole request. Production
behavior is unchanged (guarded by a test); the harness calls `run_payload`
directly with the encoder's payload, reusing the exact retry, re-ask, parsing,
validation, and diagnostics. The harness validates that each payload image path
exists before invoking the backend.

---

## 8. Harness, Metrics, and Results

### 8.1 Metrics (`metrics.py`)

Computed per encoder across the dataset:

- `type_accuracy` — fraction where `decision.type == label.type`.
- `involved_robots` — micro-averaged precision / recall / F1 over involved-robot
  id sets (true positives = predicted ∩ ground-truth).
- `valid_output_rate` — fraction of scenes whose result has a non-`None`
  decision that parsed and passed `validate_involved_robots`
  (`parse_status` ∈ {`valid`, `invalid`}); measures input-format robustness.
- `mean_latency_ms` — context only (≈0 on mock; meaningful on live runs).

Failures (`decision is None`) count as wrong for `type_accuracy`, as missed for
recall, and as invalid for `valid_output_rate`.

### 8.2 Runner (`benchmarks/runners/vlm_input_ablation.py`)

CLI:

```text
--dataset data/ablation/scenes
--backend mock|llama_server
--encoders snapshot,temporal,trajectory,keyframe   (default: all four)
--keyframes 3
--out benchmarks/results/<run-name>
--config config/models.yaml
```

Flow: load scenes → render required frames into a work directory → for each
`(encoder, scene)`: `encode` → `run_payload` → score → accumulate.

### 8.3 Results

Written to `benchmarks/results/<run-name>/`:

- `records.jsonl` — one row per `(encoder, scene)`: the `write_reasoner_log`
  shape extended with `encoder_id`, the ground-truth label, and per-scene scores.
- `summary.json` and `summary.md` — the per-encoder metrics table.

---

## 9. Out of Scope

- **M5 progress detector / live trigger** (research §6.1) — temporal fields come
  from recorded data, not a live M5.
- **Production overlay changes** to `swarm_perception/annotation.py` (§6.3) — the
  ablation renderer is separate and offline.
- **Live Cosmos Reason 2 run and committed results** — the harness ships
  validated on the mock backend; the live run is a documented command the user
  triggers with the model loaded.
- **Isaac-recorded scenes** — only the format plus a few synthetic fixtures now.
- **Strategy-quality scoring** — dropped in favor of `valid_output_rate`; the
  strategy field is still produced, just not scored.

---

## 10. Testing

All offline, mock backend, deterministic; frames render to a pytest `tmp_path`,
no binaries committed.

- `test_ablation_scene.py` — JSON load/validate: chronological-stamp rule, label
  enum normalization, known-id consistency, malformed-file errors.
- `test_ablation_encoders.py` — one behavior per encoder: snapshot text equals
  today's `build_prompt` output (variant-1 regression guard); temporal encoder
  includes the two temporal lines; trajectory encoder yields exactly one image;
  keyframe encoder yields the configured count, clamped to available history.
- `test_ablation_rendering.py` — renderer produces a valid image of expected
  size from geometry; trail length capped at `N`; arrow length scales with speed.
- `test_ablation_metrics.py` — type accuracy, involved-robot P/R/F1, and
  valid-output rate on hand-built decision/label pairs, including all-`none` and
  empty-involved edge cases, and `decision is None` failures.
- `test_reasoner.py` (extend) — `run_payload` matches `run` behavior on a
  single-image payload (refactor guard).
- Multi-image backend test — `LlamaServerBackend` (or a mock) attaches `N`
  `image_url` parts before the text part.

---

## 11. References

- Research findings: `docs/research/vlm_input_design_findings.md` (§6.2, §6.3,
  §6.5b).
- M2 spec: `docs/specs/module2_vlm_reasoning.md`.
- M2 code: `reasoning/vlm/{models,prompt_builder,reasoner,output_parser,llama_server_backend}.py`.
- Coding standards: `docs/standards/coding_style.md`.
