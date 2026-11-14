# Improved-Annotation Follow-Up - Test Scope

**Prepared:** 2026-11-14

**Revision history:**

- Initial draft: scope for an offline replay follow-up to the head-on swapped-ID replay. Covers frame measurements, provider image handling, Type L and Type K variants with rendered examples, cells, decision rules, cost and owner decisions. No model call was made.

---

## Question and Status

**Question.** On the head-on standoff scenes, with no obstacle text in the prompt, can
a model name the physically correct yielder from the camera frame once the frame is
easier to read? The thesis sentence under test is: "the correct decision depends on
visual information that is not available in the robots' geometric state."

**Status.** This is a scope document. No experiment has run, and no model API, VM or
cloud command was used. The only code added is an offline prototype that measures and
renders frames. It changes no runtime behaviour.

**Starting point.** The finished replay is
`docs/reports/2026-11-14-head-on-swapped-id-replay-results.md` (design:
`docs/superpowers/specs/2026-11-14-head-on-swapped-id-replay-design.md`). No model met
the "image use" rule. The one lead: in `C_real_notext`, ER-2 named a yielder in 11 of
48 runs, and 10 of the 11 were correct. In `D_grey_notext` it was correct in 2 of 7.
It answered `reverse`, with no yielder, in most runs.

Evidence labels used below: **[verified]** means measured or read from a file or an
official page in this session. **[inferred]** means reasoned from verified facts but
not observed.

---

## The Validity Distinction

Two kinds of "improved annotation" answer different questions. They are separate arms
and are never pooled in a verdict.

| Type | What it changes | What a pass shows | Can it support the thesis sentence? |
|---|---|---|---|
| **L** (legibility only) | How the frame shows what is already in it: label size, contrast and placement, box thickness, a fixed crop, upscaling. It adds no fact the frame does not already show. | The model saw the obstacle side in the scene pixels. | **Yes**, for this scene family. |
| **K** (knowledge injection) | Draws facts the system holds as geometry, such as the obstacle outline and name from M5's `static_obstacles`. | The model reads an overlay drawn from the system's own state. | **No.** The deciding fact is in the system's geometric state by construction. At best this compares channels: the same known fact as an image overlay vs as text. |

### What the system knows about the obstacle [verified]

- **M1 does not detect obstacles.** `grep -rln obstacle ros2_ws/src/swarm_perception/`
  returns nothing. M1 detects only ArUco markers. Its overlay draws only robot boxes,
  labels, velocity arrows and goals (`annotation.py:60-100`, `473-475`).
- **M5 holds the obstacle as hand-mirrored config.** The field is
  `OrchestratorConfig.static_obstacles: tuple[StaticObstacleInput, ...] = ()`
  (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py:377-379`). It reaches
  the prompt only when `prompt_static_obstacles` is true (`models.py:366`;
  `orchestrator_node.py:1158-1159`, `1839-1840`). The scenario run used
  `static_obstacles: [{obstacle_id: obstacle_1, x: -1.85, y: 0.0, size_x_m: 0.3, size_y_m: 0.3}]`
  (`data/logs/vm_runs/20260925_063520/orchestrator.yaml.used:92-93`).
- **M3 uses the same config.** Its feasibility gate reads `static_obstacles` together
  with `scenario_geometry` (`orchestrator.yaml:236` comment; `reasoning/rag/retreat_candidates.py:47`).
  That gate re-grounds the yield in the live runs (artifact field
  `yield_regrounded_reason`, for example
  "robot_1 has 0.70 m retreat room < 1.08 m required").
- **`StaticObstacleInput` has no height** (`reasoning/vlm/models.py:116-125`). The
  0.5 m box height exists only in the Isaac scenario file
  (`isaac/config/scenarios/family/head_on_asymmetric_w0p2_eopen_o0.yaml`,
  `size.z_m: 0.5`), which never reaches M5.

Any overlay that marks the obstacle is therefore Type K. A Type L variant may only make
the pixels the camera already recorded easier to read.

---

## Sources Checked

| Source | What was taken from it |
|---|---|
| `annotation.py` (M1) | Overlay geometry: 40 x 40 px box, 2 px line (`:72-75`); label `cv2.FONT_HERSHEY_SIMPLEX`, scale 0.5, thickness 1, origin `(cx-20, cy-25)` (`:77-86`); arrow only when `abs(linear_velocity) > 1e-3` (`:88`), so no arrow is drawn on these stopped robots. |
| `ros2_ws/src/swarm_perception/config/calibration.yaml` | Homography for the marker plane (z = 0.21 m): 0.004358 m/px, i.e. 229.4 px/m; 1280 x 960; principal point at world (0, 0). |
| `orchestrator.yaml.used` (pilot runs) | `keep_debug_frames: true`, `frame_downscale_width: null`. M2 receives the 1280 x 960 annotated PNG unchanged. |
| `swarm_orchestrator/models.py:343-354` | `keep_debug_frames`, `keep_raw_frames` (debug only: "the M2 request still carries the annotated frame"), `frame_downscale_width`. |
| `reasoning/vlm/{openai,gemini,anthropic}_backend.py` | Each backend sends the PNG bytes as base64 without resizing. OpenAI sends `detail: "high"` (`openai_backend.py:234`); Gemini leaves `media_resolution` at the provider default (`gemini_backend.py:33`); Anthropic sends an `image/png` block (`anthropic_backend.py:164-185`). |
| OpenAI images and vision guide ([developers.openai.com/api/docs/guides/images-vision](https://developers.openai.com/api/docs/guides/images-vision), fetched 2026-11-14) | For gpt-4o `detail: high`: fit inside 2048 x 2048; then, if the shortest side exceeds 768 px, scale it to 768; count 512 px tiles; cost is 85 tokens plus 170 per tile. |
| Anthropic vision guide ([platform.claude.com/docs/en/build-with-claude/vision](https://platform.claude.com/docs/en/build-with-claude/vision), fetched 2026-11-14) | Visual tokens = ceil(w/28) x ceil(h/28). High-resolution tier ("Claude 4.7 and later models", which covers `claude-sonnet-5-5`): long edge up to 2,576 px and up to 4,784 tokens, otherwise downscaled. The page also advises: "If the image contains important text, make sure it's legible and not too small." |
| Gemini image understanding ([aistudio.google.com/docs/image-understanding](https://aistudio.google.com/docs/image-understanding)) and media resolution ([aistudio.google.com/docs/media-resolution](https://aistudio.google.com/docs/media-resolution)), fetched 2026-11-14 | Gemini 3 / 4 image tokens: `unspecified` (default) 1120, `low` 280, `medium` 560, `high` 1120, `ultra_high` 2240. Neither page says how pixels are resampled to that budget, and Robotics-ER is not mentioned. The 768 x 768 tiling rule on the first page is for earlier models. |
| `calls.jsonl` and `probes.jsonl` of the finished replay | ER-2 billed `input_tokens_image` 1,064 for the 1280 x 960 frame and for the grey image alike, and 1,089 for a 64 x 64 probe. gpt-4o's text-off prompt was 1,646 tokens with the frame. |

---

## What the Frames Show

### Stimuli and raw frames [verified]

The 12 replay stimuli are the first SHA-verified genuine standoff of each pilot run
(`select_standoff_artifacts` in `scripts/replay_live_decisions.py:1019`). The
prototype re-derives them with that selector and gets the same 12 request IDs.

| Batch | Scene (request prefix) | Blocker side | Raw frame on disk |
|---|---|---|---|
| 1 | `53264de9`, `5e7b5a59`, `2c3fbfa5` | west | no |
| 1 | `61119197`, `d053d0dc`, `3120c65f` | east | no |
| 2 | `810c9104`, `42fb0cb8`, `d4b96fbd` | west | **yes** (`<request_id>_raw.png`) |
| 2 | `189ae2a6`, `e4b1bd03`, `618a9f29` | east | **yes** |

Six of the 12 have a raw frame: the batch-2 scenes. Raw and annotated frames are
taken at different instants, by -0.355 to +0.228 s (`raw_frame_skew_sec` from
`m5.log`). Both robots are stopped, so this skew is harmless.

### Measurements (all 24 candidate scenes; 12 original + 12 extra, below) [verified]

Measured by `render_variants.py`. Per-scene values are in `measurements.json`.

| Quantity | Value (min / median / max) | Note |
|---|---|---|
| Frame | 1280 x 960 RGB PNG, about 0.68 MB | sent unchanged to every provider |
| Robot box | 40 x 40 px, 2 px red `(200, 0, 0)` (status STOPPED) | `annotation.py:72-75` |
| Robot marker (white square) | 28-30 px a side | about 0.12 m at 229 px/m |
| Robot centre separation | 38 / 58 / 91 px | the robots are about 0.25 m apart, in the frame centre |
| Label strip height (with the `_` descender) | 12 / 14 / 15 px | font scale 0.5, 1 px stroke |
| Label x-height | 5 / 8 / 8 px | 23 of 24 measurable |
| Gap between the two labels | -17 / 3 / 36 px | **13 of 24 scenes have a gap of 3 px or less, and 5 overlap.** The frame reads `robot_1robot_2`, or, in `7b0fbf9e`, `robotrobot_2`, where `robot_2`'s label overwrites the end of `robot_1`'s. |
| Label contrast (red on corridor floor about `(56, 55, 48)`) | 1.94 / 1.97 / 2.03 : 1 (WCAG ratio) | low; WCAG asks 4.5:1 for small text |
| Obstacle top face | 77 x 77 px, RGB about 147 | top face at u = 128-204 (west) or 1075-1151 (east), v = 442-518, **at the same pixels in every scene of a side** |
| Obstacle contrast with the corridor floor | 3.28 / 3.32 / 3.33 : 1 | a light box on a dark floor, with a darker side face and shadow toward the frame centre |
| Nearest robot centre to obstacle top-face edge | 396 / 406 / 419 px | about 1.75 m |

Plain reading: the obstacle is large, well-lit and unambiguous: a 77 px light square.
The robot labels are the weak element. They are 8 px high, low in contrast, and run
together in half the scenes. The 40 px boxes of the two robots almost touch. The
prompt gives coordinates in metres but never states how the image is oriented ("image
left = west, -x"). The only in-image link between a robot's name and its side of the
corridor is therefore the label. **[verified for the frames; the "weak element"
reading is inferred]**

### What each provider does to a 1280 x 960 PNG

| Provider / model | Original 1280 x 960 | Crop+upscale variant 2048 x 640 | Status |
|---|---|---|---|
| OpenAI gpt-4o, `detail: high` | shortest side 960 > 768, so scaled to **1024 x 768 (0.8x)**; 2 x 2 tiles = 85 + 680 = **765 tokens**; label x-height about 6.4 px | fits 2048, shortest side 640 < 768, so **not resized**; 4 x 2 tiles = 85 + 1360 = **1,445 tokens** | rule from the docs [verified]; resulting pixel sizes [inferred] |
| Anthropic Sonnet 5.5 (high-resolution tier) | **not resized**; 46 x 35 = **1,610 visual tokens** | **not resized**; 74 x 23 = **1,702 tokens** | rule [verified]; the finished replay billed 3,019 input tokens per Sonnet call, consistent with this |
| Google ER-2 | billed **1,064 image tokens**, the same for the frame and for grey; 1,089 for a 64 x 64 probe | budget expected to stay about 1,064-1,120 | tokens [verified]; resampling rule **undocumented** |

Gemini legibility is an estimate [inferred]. The token count does not depend on input
size, so ER-2 resamples every image to a fixed budget. If each token covers about
28 x 28 px (the Anthropic patch size), the frame is seen at about 0.82x and the label
x-height is about 6.5 px. If each token covers 16 x 16 px, it is seen at about 0.47x
and the x-height is about 3.8 px. Either way, the 1280 x 400 crop holds 0.51 MP
against the full frame's 1.23 MP. The same budget then covers about 2.4x more tokens
per original pixel, roughly **1.55x linear**, whatever the patch size. Only the crop
helps Gemini; upscaling adds nothing at a fixed budget.

---

## Additional Scenes Available Offline [verified]

`data/logs/vm_runs` holds 25 head-on asymmetric runs with M5 frames (`*_w0p2_eopen_o0` 13,
`*_wopen_e0p2_o0` 12). The `bshort` variants have no frames. Applying the same selector
(first SHA-verified standoff per run, failure-context artifacts excluded) gives 12 more
scenes. They come from the 2026-09-25 ER-2 live runs and all render prompt v1 with
obstacle text on. `20260925_181526` has no standoff.

| Run | Scene | Side | Raw | Stored order |
|---|---|---|---|---|
| `20260925_124609` | `710c40e5` | west | no | `id_asc` |
| `20260925_130115` | `7b0fbf9e` | west | no | `id_asc` |
| `20260925_132335` | `ea126abd` | west | no | `id_desc` |
| `20260925_133841` | `bb48067c` | east | no | `id_asc` |
| `20260925_135334` | `d592a820` | east | no | `id_asc` |
| `20260925_140824` | `32aec602` | east | no | `id_asc` |
| `20260925_183343` | `bc56a57a` | west | yes | `id_asc` |
| `20260925_184840` | `920ec0d9` | west | yes | `id_asc` |
| `20260925_190322` | `8027a8a2` | west | yes | `id_asc` |
| `20260925_191810` | `41d72639` | east | yes | `id_desc` |
| `20260925_193307` | `653be8f3` | east | yes | `id_desc` |
| `20260925_194800` | `f94cb7ed` | east | yes | `id_desc` |

`check_integrity` matched 169 of 169 artifacts of these 12 runs. With these, the scene
set is **24 scenes (12 west, 12 east)**, and **12 of the 24 (6 per side) have a raw frame**.

**These 24 scenes add count, not diversity.** They are the same two scenario cells at
seed 42. The obstacle sits at the same pixels in every scene of a side, and the robots
stop within 38-91 px of each other at the frame centre. Visually, the set is two
layouts (blocked left, blocked right) with small pose jitter. More scenes or more
replicates from this family cannot change that. Genuinely new layouts need new
simulator runs, which are out of scope here. **Recommended scene set: all 24**,
because they are free and they double the scene-level count. The report must still
call them one family.

---

## Proposed Image Variants

Every variant is produced offline from the stored frames and paired with the stored
prompt reconstructed with `include_static_obstacles=False` (text off). The crop box is
**fixed for every scene**: u 0-1280, v 280-680. It never depends on where the obstacle
is.

| Variant | What it changes | Type | How produced | Scenes covered | Ship later in M1/M5 behind a default-off option? |
|---|---|---|---|---|---|
| **L1** crop + upscale | Fixed 1280 x 400 corridor-band crop, Lanczos upscale 1.6x to 2048 x 640. Both corridor ends and the obstacle stay in view. Labels are unchanged: still 8 px and still run together, now about 13 px high. | L | post-process the annotated PNG | all 24 | Yes, in M5, where the frame is written for M2. Next to `frame_downscale_width` (`models.py:354`, `orchestrator_node.py:1107`, `1848`), add `frame_crop_box_px: null` and `frame_upscale: 1.0`, set per scenario like `scenario_geometry`. |
| **L2** legible labels + L1 | Removes the old 1 px red labels (Telea inpaint over the label pixels only). Redraws each label as a white-on-black panel (scale 0.7, stroke 2) with a red border and a short leader line. Each panel is pushed 45 px away from the pair's midpoint so the two never overlap. Boxes are redrawn at 3 px. Then the L1 crop+upscale. The label x-height in the sent image is about 16 px; the contrast is 21:1. Panel placement uses only the robot poses M1 already publishes. | L | post-process the annotated PNG (all 24). For the 12 raw scenes, the same overlay drawn on the raw frame (`L2raw`) agrees to within 80 and 23 px of 1.3 M in the two checked scenes | all 24 (raw-based: 12) | Yes, in M1. `render_annotated_frame` already has an unused `style` argument (`annotation.py:444`, `455`). Add `annotation.legible_labels: false` (and font scale) to `config/annotation.yaml`, read in `perception_node.py` like `annotation.metric_grid` (`:62`), passed through `pipeline.py:66`. With the flag off, the frame stays byte-identical (pinned by `tests/unit/test_annotation_apparatus.py`). |
| **K1** obstacle outlined + L2 | L2, plus a cyan outline of the declared obstacle's ground footprint and the label `obstacle_1` (the neutral ID the prompt uses). The footprint comes from `static_obstacles`, mapped with the camera height (`scenario_geometry.camera`). | **K** | post-process | all 24 | Only as an ablation, never as a default. M1 does not know the obstacle, so the overlay would have to be drawn in M5 (which holds `static_obstacles`) or fed to M1 as new config. With no height in `StaticObstacleInput`, it can mark only the footprint. |

Considered and not recommended:

- **A free-retreat-space shading** (Type K): it encodes the M3 feasibility answer.
- **A compass or "+x east" legend**: it is not obstacle information, but it is a second
  route from coordinates to image side. It would blur what L2 tests.
- **Mirror-flipped frames**: the pose text would then contradict the image.

**Optional (owner decision): `L2swap`.** L2 redraws the labels from the scene state.
Swapping `robot_1` and `robot_2` in the state before drawing therefore gives a
swapped-ID image arm, which the finished replay could not build because it lacked raw
frames. It is not needed for the decision rule below. That rule already requires
correctness on both sides, which no label prior can pass.

### Rendered examples (`data/experiments/2026-11-14-improved-annotation-scope/`)

| File | Scene | What it shows |
|---|---|---|
| `810c9104_L1.png` | west-blocked, raw exists | The corridor band, 2048 x 640. Light-grey box at the left end, beside a dark round fixture. The two robots touch at the centre, with tiny red labels running together above them. Barriers top and bottom. |
| `810c9104_L2.png` | same | Same pixels. The two robots now carry separate black panels, `robot_1` (left) and `robot_2` (right), with thicker red boxes. The obstacle region is untouched. |
| `810c9104_L2raw.png` | same | The L2 overlay drawn on the raw frame. Visually identical to `810c9104_L2.png`. |
| `810c9104_K1.png` | same | L2 plus a cyan square and the text `obstacle_1` beside the left box. |
| `189ae2a6_L1.png`, `_L2.png`, `_L2raw.png`, `_K1.png` | east-blocked, raw exists | Mirror case: the light-grey box sits at the right end, and the cyan K1 outline sits just inside it. |
| `53264de9_L1.png`, `_L2.png`, `_K1.png` | west-blocked, batch 1 (no raw) | Shows L2 by post-processing alone. |

**Check that Type L adds nothing** [verified, `type_l_checks.json`]. For all 24 scenes,
every pixel L2 changes before the crop lies inside a zone around the two robots,
u ± 160 px and v from 110 px above the robots to just below their boxes. The changed
area is about 10,200 px, with its bounding box inside u 481-770 and v 423-509. The
obstacle region (u 128-204 or 1075-1151) is never changed. The panels stay below the
barrier's lower face. 0-3 old red label pixels remain per scene. They are box
corners: `7b0fbf9e` shows 40 where the two boxes abut. Visual checks on
`810c9104`, `189ae2a6`, `53264de9` and `7b0fbf9e` agree.

**K1 placement limit** [verified]. The calibration homography is for the marker plane
(0.21 m), and the camera is 3.0 m above the origin. The box's top face (0.5 m high)
therefore images at u 128-204, but its ground footprint images at u 213-277, next to
the top face. K1 draws the footprint, because the system holds no obstacle height. The
outline therefore sits on the box's shadowed side and base, not on its bright top. A
first prototype using the marker-plane homography straddled both and was corrected.

---

## Recommended Design

### Cells

All cells use text off (`include_static_obstacles=False`), prompt v1, original IDs,
both listing orders (`id_asc`, `id_desc`), the 24 scenes, and the shipped retry policy
and configs from `config/models.yaml`, unchanged.

| Cell | Image | Role |
|---|---|---|
| `C_ref` | annotated frame (= old `C_real_notext`) | reference: legibility as shipped |
| `D_ref` | grey 1280 x 960 (= old `D_grey_notext`) | reference: states only |
| `L2` | L2 | primary Type L test |
| `K1` | K1 | Type K: annotation reading |
| `L1` (optional) | L1 | separates crop/resolution from labels |

**Re-run the references in the same session (recommended).** gpt-4o's behaviour moved
between September and November on byte-identical prompts (the decisive-cell
disagreement in the finished report). Every contrast must therefore be within one
session. The November `C_real_notext` / `D_grey_notext` rows cover only 12 of the 24
scenes and stay a separate stratum.

**Replicates.** gpt-4o: 2 (temperature 0, so replicates mostly agree; the scene is the
real unit). ER-2: 4. ER-2 takes no temperature, and its named-yielder count is the
bottleneck, so more draws per scene buy observations cheaply. That gives 96 runs per
cell for gpt-4o and 192 for ER-2.

**Order of execution.** Per model: a 4-run pilot per cell (scenes `810c9104` and
`189ae2a6`, both orders), with the finished replay's pilot rule. Then
`D_ref`, `C_ref`, `L2`, `K1` (and `L1`), interleaved scene by scene so that any drift
hits all cells alike. The run resumes on a key. Same transient and quota stop rules
as the finished replay.

### Models

| Model | In? | Reason |
|---|---|---|
| Gemini ER-2 (`gemini-robotics-er-2-preview`) | **in** | The only model with a scene-consistent lead (10 of 11). Cheap. |
| gpt-4o (`gpt-4o-2024-08-06`) | **in** | The slot-prior baseline. It refuses real frames sometimes (6/48 on attempt 1 in Cell C); the fallback stratum is reported separately as before. |
| Claude Sonnet 5.5 | **out** | It refused about 88% of non-real-frame pilot runs and 30/48 real-frame runs, `reasoning_extraction`, triggered by the `<think>` block. At about $0.02 per run (ledger) and about 0.12-0.38 answers per run, 96 runs x 4 cells costs about $8 for about 50-140 answers, with whole arms likely to stop at the pilot. Including it would need a Sonnet-specific prompt, which is a different experiment. |

### Scoring ER-2 [verified schema facts; proposal]

- **The schema cannot say which robot reverses.** `CongestionDecision`
  (`reasoning/vlm/models.py:409-458`) carries `yield_robot`, "only meaningful when
  strategy == yield". Prompt v1 defines `reverse` as "both back up to clear"
  (`prompt_v1.py:69`). v1 does not ask for `proposed_plan` or `crossing_order`, and 0
  of the 240 ER-2 attempts in the finished replay contain either. Of ER-2's 207
  `reverse` decisions, 184 name no robot in `root_cause` or `justification`, and 23 name
  both. **Scoring "the robot told to reverse" is therefore not possible, and mining
  free text for one would be a metric discovered after the data. It is not proposed.**
- **Primary (all models, unchanged):** P(names the physically correct robot), over all
  runs; `reverse`, refusals and errors count as not correct. ER-2 is expected to fail
  this through `reverse`. That outcome is reported, not rescued.
- **ER-2 secondary, stated now: "conditional image use".** Among runs that name a
  yielder, per side (orders pooled):
  - at least 12 named runs per side, from at least 6 of the 12 scenes and at least 4
    in each order;
  - named-correct at least 0.80 on **each** side;
  - and either `D_ref` is not assessable on the same criteria, or the variant's
    conditional accuracy exceeds `D_ref`'s by at least 0.25.

  If fewer than 12 named runs per side exist, the verdict is "not assessable". The
  naming rate per cell is always reported beside it. A pass supports only "when ER-2
  commits to one yielder, the choice follows the image". It does not support "ER-2's
  decision policy uses the image". Expected yield: at the Cell C naming rate (11/48,
  about 23%), 192 runs give about 44 named, about 22 per side.
- **Forced choice is a different prompt.** Removing `reverse`, or asking a follow-up
  question, changes the prompt. It is only allowed as a separate arm with its own
  same-session `D_ref` (owner decision; default out).

---

## Decision Rules (fixed before any call; counts only)

Per model and per variant V in {`L2`, `K1`, `L1`}. A side x order cell holds 12 scenes;
r = 2 for gpt-4o, r = 4 for ER-2.

1. **Image use under V.** All three must hold:
   - in each of the 4 side x order cells, at least 75% of runs correct
     (gpt-4o 18/24; ER-2 36/48);
   - in each cell, at least 8 of the 12 scenes with at least 75% of their replicates
     correct (gpt-4o 2/2; ER-2 3/4);
   - overall P(correct | V) minus P(correct | `D_ref`) of at least 0.25, both from this
     session.

   Requiring both sides defeats a pure `robot_1` or `robot_2` prior, because the
   correct label flips with the side. Requiring both orders defeats a slot prior.
2. **Legibility effect (L variants only).** L passes rule 1, `C_ref` fails it, and
   P(L) - P(`C_ref`) is at least 0.15.
3. **Annotation reading (K1 only).** Rule 1 applied to K1. A K1 pass is reported under
   its own heading. **It never counts as image use for the thesis sentence.**
4. **ER-2 conditional image use**, as stated above. It is secondary and reported
   separately.
5. **Not assessable:** a cell stopped at the pilot, or one with fewer than 20 decisions
   (any strategy).

**What the counts can and cannot carry.** Replicates within a scene are dependent:
gpt-4o at temperature 0 mostly repeats itself. The scene-level clause is what gives
the rule meaning. But the 24 scenes are themselves two visual layouts with pose
jitter, from one family at one seed. **That is the binding limit. More replicates do
not fix it, and more scenes from this family do not either.** A pass means "the model
can tell a left-blocked from a right-blocked corridor in this rendering", not more.

---

## Calls, Cost and Wall Time

Per-run cost uses the finished replay's ledger rates (gpt-4o $2.50 / $10.00 per MTok;
ER-2 $1.00 / $5.00, thought tokens as output). Base per-run costs come from its
`ledger.jsonl`: ER-2 $0.0040 per run in both C and D; gpt-4o $0.0065 in C and $0.0061 in D.

| Cell | gpt-4o runs | gpt-4o $/run | gpt-4o $ | ER-2 runs | ER-2 $/run | ER-2 $ |
|---|---|---|---|---|---|---|
| `C_ref` | 96 | 0.0065 | 0.62 | 192 | 0.0040 | 0.77 |
| `D_ref` | 96 | 0.0061 | 0.59 | 192 | 0.0040 | 0.77 |
| `L2` | 96 | about 0.0085 | 0.82 | 192 | 0.0040 | 0.77 |
| `K1` | 96 | about 0.0085 | 0.82 | 192 | 0.0040 | 0.77 |
| **Recommended total** | **384** | | **2.85** | **768** | | **3.07** |
| `L1` (optional) | +96 | about 0.0085 | +0.82 | +192 | 0.0040 | +0.77 |

- The gpt-4o variant cost adds 680 image tokens per attempt (8 tiles against 4). That
  is $0.0017 per attempt, at about 1.15 attempts per run [inferred]. ER-2's image
  budget is fixed, so its cost does not change [inferred from the probe].
- **Recommended total about $5.90** (about $7.50 with L1). API calls: about 440
  gpt-4o and about 770 ER-2.
- **Proposed hard caps:** $9.00 total and $4.50 per model, with the finished replay's
  worst-case pre-check before every run.
- **Wall time** (mean per run from the finished replay: ER-2 7.1 s, gpt-4o 3.4 s):
  ER-2 768 x 7.1 s, about 91 min; gpt-4o 384 x 3.4 s, about 22 min. About 2 hours
  sequentially (about 2.5 h with L1), or about 1.5 h with the two providers in parallel.

---

## What Each Outcome Would Let the Thesis Say

| Outcome | What the thesis may say |
|---|---|
| **L2 passes** (for a model) | In this one head-on layout, with legible labels and no obstacle text, the model reads the blocked side from the image and picks the right yielder. This supports the thesis sentence for this family only. If `C_ref` fails in the same session (rule 2), the shipped annotation, not the model, was the bottleneck, which argues for shipping L2 behind its flag. |
| **L2 fails, K1 passes** | The model reads an overlay that names the obstacle but does not perceive the obstacle in the scene. The deciding fact then came from the system's geometry, so this **does not support** the thesis sentence. It is a channel result: the same known fact works as an overlay (compare text-on results such as `A_grey` from the earlier stratum, not pooled). It strengthens the existing conclusion that M3's geometric gate should decide the yielder. |
| **Nothing passes** | Neither legible pixels nor an explicit overlay moves the choice. Together with the prompt finding below, the likely reading is that the task framing gives the model no reason to use the picture, rather than that the picture is unreadable. The thesis keeps the finished replay's claim (the yielder comes from M3, not M2) on firmer ground. It still cannot claim VLMs cannot do this in general. |
| **L2 passes, K1 fails** | Unexpected. The overlay may distract. Report it as is, with no claim. |
| **ER-2 passes only the conditional rule** | "When ER-2 commits to one robot, the choice follows the image." That is a property of its committed answers, not of its decision policy, because it mostly answers `reverse`. Weak support at most. |
| **`C_ref` passes** | Drift from the November result. The legibility contrast is void, and the session-to-session instability becomes the finding. |

---

## Risks and Limits

- **One scenario family, two robots, seed 42, two visual layouts.** This is the binding
  limit, as stated above.
- **First decision only, offline.** No M3 gate, no execution, no closed loop.
- **Provider preprocessing.** It is documented for OpenAI and Anthropic. For ER-2, the
  resampling is unknown beyond a fixed token budget of about 1,064-1,120. Its legibility
  figures are estimates. Raising Gemini `media_resolution` to `ultra_high` (2,240
  tokens) would be a request change; it is not proposed.
- **The prompt gives no reason to look for obstacles when the text is off** [verified,
  rendered for all 12 original scenes]. With text off, the only obstacle sentence is
  removed (`_OBSTACLES_OFF = {"obstacle_use_clause": ""}`, `prompt_v1.py:138-144`, selected at `:414`).
  What remains about the image and the yielder is:
  - "Analyze the overhead camera view together with the robot states below and detect
    congestion patterns ..."
  - "classify as type="deadlock" and strategy="yield" (the robot named in yield_robot
    backs up) or strategy="reverse" (both back up to clear)."
  - "Decide from the robot coordinates and the image, not from assumptions about
    intent."
  - The `<think>` recipe: "Read the pairwise geometry (distance and whether each robot
    faces the other), check the robot statuses, identify any conflicts, decide the
    congestion type and strategy, and if the strategy is "yield", state which robot
    should yield and why." It never mentions the image, obstacles or retreat room.

  Nothing tells the model that backing up needs free space. **Proposal:** a neutral
  task-knowledge line, such as "A robot that backs up needs free floor behind it." It
  states no scene fact, so it is compatible with Type L. But it is a prompt change, so
  it is a **separate factor**: cells `L2+P` and `D_ref+P`, never mixed into the
  primary verdict. Default: a second phase, run only if L2 fails phase 1, registered
  now. Cost: about $0.82 + $0.59 for gpt-4o plus $1.54 for ER-2, about $3.00.
- **Label redraw artefacts.** Inpainting leaves 0-3 box-corner pixels. The panels
  cover about 10k px of plain floor around the robots. They never touch the obstacle,
  the barriers or the corridor ends.
- **K1 marks the footprint, not the visible top face.** See "K1 placement limit".
- **The crop drops the N-S cross-aisle.** It holds no robots or obstacles. This is a
  loss of context, not an added fact.
- **gpt-4o refusals** on real frames. Attempt-1 and fallback strata are reported as
  before.
- **Analysis code** must be written and frozen with the rules before the first call,
  unlike the finished replay, where it was written after rows were visible.

---

## Owner Decisions

| # | Decision | Recommended default |
|---|---|---|
| 1 | Run this follow-up at all | Yes, as an offline replay. |
| 2 | Scene set | All 24 (12 original + 12 extra ER-2-run standoffs), called one family. |
| 3 | References | Re-run `C_ref` and `D_ref` in the same session. Do not reuse the November rows. |
| 4 | Variants | `L2` and `K1`. `L1` only if the owner wants crop separated from labels (+$1.60). |
| 5 | Models | ER-2 and gpt-4o. Sonnet out. |
| 6 | Replicates | gpt-4o 2, ER-2 4. |
| 7 | ER-2 scoring | Primary all-runs rule plus the pre-stated conditional rule. No free-text mining. Forced choice out. |
| 8 | Neutral retreat-space instruction line | Registered now as phase 2 (`L2+P`, `D_ref+P`), run only if `L2` fails phase 1. |
| 9 | `L2swap` | Out. |
| 10 | Caps | $9.00 total, $4.50 per model. |
| 11 | Ship L2 in M1 behind `annotation.legible_labels: false` | Only after a pass. No runtime change now. |

**Smallest single-arm version.** Run `L2` only, with a same-session `D_ref`, on ER-2
(4 replicates) and gpt-4o (2 replicates), all 24 scenes, both orders. That is
96 + 96 gpt-4o runs and 192 + 192 ER-2 runs, about $3.00 and about 1 h. It answers the
Type L question by rule 1. It gives up the legibility contrast (rule 2, which needs
`C_ref`) and the K1 channel comparison.

---

## Reproducibility

| Item | Location (branch `exp/head-on-swapped-id-replay`) |
|---|---|
| Prototype (measure, render, Type L check) | `data/experiments/2026-11-14-improved-annotation-scope/render_variants.py` |
| Measurements, all 24 scenes | `data/experiments/2026-11-14-improved-annotation-scope/measurements.json` |
| Type L change-zone checks | `data/experiments/2026-11-14-improved-annotation-scope/type_l_checks.json` |
| Example images | `data/experiments/2026-11-14-improved-annotation-scope/{810c9104,189ae2a6,53264de9}_{L1,L2,K1}.png`, `{810c9104,189ae2a6}_L2raw.png` |

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-swapid
/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv/bin/python \
  data/experiments/2026-11-14-improved-annotation-scope/render_variants.py \
  --runs-dir /Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs
```

The frames are read from the main checkout's `data/logs/vm_runs`, which is untracked.
The script makes no network call.
