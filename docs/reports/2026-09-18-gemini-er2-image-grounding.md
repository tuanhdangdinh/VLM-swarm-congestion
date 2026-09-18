# Does Gemini Robotics-ER 2 Ground Its Congestion Decisions in the Image?

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: pointing test, the incongruent 2x2, and the geometry-off ablation on two measured frames from the live ER-2 run.

---

## Question

Every ER-2 result recorded so far is consistent with pure arithmetic on the
text robot-state block: the gating probe answered `congestion_detected=false`
at a stated 1.00 m and `deadlock` at 0.35 m, and in the live closed-loop run
(`run_id=gemini_20260918_084649`) every justification quoted a numeric
distance from the state block while none referenced anything visual. The
design document
(`docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`)
carries this as an open item: a paired-image/paired-state probe is required
before any image-grounding claim.

This report runs that probe. Two questions are kept apart on purpose:

1. **Perception** — can ER-2 see the robots in our overhead frame at all?
2. **Decision** — does the image change the congestion decision the project's
   own M2 prompt asks for?

---

## Stimuli

Both frames come from the same recorder video of the live ER-2 run
(`data/logs/gem_run_20260918_084649/annotated_000.mp4`, 1280x960, captured
from `/perception/annotated_frame`), so image format, compression, and overlay
style are matched across conditions. Each frame is an M1 **annotated** frame —
the production M2 input — so the manipulation is more precisely "synthetic text
state block vs. M1's rendered overlay of what it actually measured".

| Stimulus | Frame | Header stamp (burned in) | Measured separation | Ground-truth source |
|---|---|---|---|---|
| `FRAME_CONFLICT` | `f=203` | 1789721320.33 s | **0.251 m** | robot_1 ArUco, robot_2 M1 scene log |
| `FRAME_CLEAR` | `f=1667` | 1789721707.53 s | **4.884 m** | both ArUco |

- `FRAME_CONFLICT`: the genuine head-on standoff — robot_1 at
  world `(-0.125, -0.009)` / pixel `(611.2, 482.0)`, robot_2 at
  world `(0.125, 0.001)` / pixel `(669.0, 480.0)`, nose-to-nose between the
  two aisle barriers. `sha256 1dea9aed…3589`.
- `FRAME_CLEAR`: post-resolution, both robots parked at opposite ends of the
  aisle — robot_1 at world `(2.418, -0.027)` / pixel `(1194.8, 486.2)`,
  robot_2 at world `(-2.466, -0.004)` / pixel `(74.2, 481.0)`.
  `sha256 ad5db360…ea31`.

Both are well inside the target bands (conflict ≤ 0.5 m, clear ≥ 1.5 m).

One bookkeeping note for the tables below: `FRAME_CONFLICT`'s separation is
0.251 m computed from world coordinates, and 0.252 m when re-derived from the
ground-truth *pixels*, because `world_to_pixel` rounds to integer pixels
(±0.5 px ≈ 2 mm) and the pointing scorer works in pixel space. That ~2 mm
quantization, plus the 0.40 s offset of the matched scene-log row, is the
floor under this frame's millimetre-scale numbers — they are reported as
measured, not as accurate to 1 mm.

### How the separations were measured, and what did not work

The brief's plan was to re-run the project's own ArUco detector
(`swarm_perception.detection` + the configured calibration) over each frame.
**That only half worked, for a structural reason worth recording:** the
stimuli are *annotated* frames, and M1's own overlay — a 40x40 px status box
plus a velocity arrow and ID text — is drawn directly on top of the 28 px
marker, destroying the quiet zone the detector needs. On `FRAME_CONFLICT` the
two overlay boxes overlap (the markers are 57 px apart), and re-detection
recovers marker 1 only; a sweep of 121 frames sampled across the whole video
recovered both markers in 3 frames and neither in 75. Relaxing detector
parameters produced false marker IDs (17, 37, 45) and was rejected.

Ground truth therefore comes from two sources, in this order:

1. **ArUco re-detection** on the frame, where it succeeds (both robots in
   `FRAME_CLEAR`, robot_1 in `FRAME_CONFLICT`).
2. **M1's own recorded state** at the frame's header stamp — the recorder
   burns each message's `header.stamp` into the frame
   (`scripts/record_topic_video.py`), and `data/logs/m5_scene/<session>.jsonl`
   carries M1's per-frame `SceneState`. Matched rows were 0.40 s
   (`FRAME_CONFLICT`) and 0.49 s (`FRAME_CLEAR`) from the frame stamp; both
   chosen windows are static for > 10 s, so the ~1 Hz log is adequate here.

The two sources agree where they overlap: on `FRAME_CLEAR`, re-detection gives
robot_1 `(2.417786, -0.027239)` — identical to the scene-log row — and robot_2
within 0.0011 m of it. On `FRAME_CONFLICT`, re-detected robot_1 matches the
scene-log row exactly. This is what licenses using the log for the one robot
the annotated frame will not give back.

---

## Pre-stated pass criteria

Fixed before any result was looked at.

**Experiment 1 (pointing).** A TurtleBot3 is ~0.3 m across, and the
calibration's measured scale is 0.0043583 m/px, so:

| Grade | Threshold | In pixels |
|---|---|---|
| Clear hit (point landed on the robot) | ≤ 0.15 m (half robot width) | ≤ 34.4 px |
| Right robot | ≤ 0.30 m (one robot width) | ≤ 68.8 px |
| Miss | > 0.30 m | > 68.8 px |

Two guards against a degenerate pass: points are assigned to robots
**one-to-one** by minimising total error (never nearest-neighbour, so one blob
reported twice cannot score two hits), and the **returned inter-point
separation** is recorded next to the true separation. On `FRAME_CONFLICT` half
the true separation is 28.8 px — inside the clear-hit ring — so that frame's
result only means "localized two robots" if the returned separation is near
0.251 m.

**Experiment 2 (the 2x2), fixed in advance.**

- Gate: cell A (congruent conflict) must answer conflict and cell D
  (congruent clear) must answer clear. Otherwise B and C are uninterpretable.
- If B answers clear and C answers conflict → the decision tracks the **text**.
- If B answers conflict and C answers clear → it tracks the **image**.
- Mixed answers, or justifications citing visual evidence, are partial
  grounding and get quoted verbatim.

---

## Method

All calls go through the project's own `GeminiBackend`
(`reasoning/vlm/gemini_backend.py`, Interactions API, `x-goog-api-key`) at
`thinking_level: low`, `force_schema: false`, matching `config/models.yaml`'s
`vlm.gemini` block and the live run. **No `seed` was sent** — with
`generation_config.seed` pinned the repeats would be one sample reported three
times, and the Interactions API has no temperature field to hold constant
instead (design doc §4). Decision cells run through the real
`reasoning.vlm.reasoner.Reasoner` with the unmodified
`reasoning.vlm.prompt_builder` prompt and a real `ReasonerRequest`; only the
image and the text robot states vary.

| Text condition | States sent |
|---|---|
| `conflict` | robot_1 `(-0.175, 0.0)` θ=0.00, robot_2 `(0.175, 0.0)` θ=π, both `STOPPED` — 0.35 m, mutually facing |
| `clear` | robot_1 `(-1.25, 0.0)` θ=π, robot_2 `(1.25, 0.0)` θ=0.00, both `MOVING` at 0.15 m/s — 2.50 m, diverging |

No goals or tasks are sent in either condition, so nothing but the geometry
and status can explain a difference between cells.

| Cell | Image | Text | Run order |
|---|---|---|---|
| A | `FRAME_CONFLICT` | conflict | 1 (gate) |
| D | `FRAME_CLEAR` | clear | 2 (gate) |
| B | `FRAME_CONFLICT` | clear | 3 |
| C | `FRAME_CLEAR` | conflict | 4 |

Harness: `scripts/probe_gemini_er2_grounding.py`. Every call is appended to a
JSONL artifact under `data/logs/er2_grounding/` (git-ignored) with the
condition, the stimulus SHA-256, the verbatim response, diagnostics, and token
usage — no API key, no base64 image. 42 live calls total (6 + 12 + 24), all at
`attempts=1` and `parse_status=valid`; ≈ $0.21 at standard pricing, $0.00 on
the free tier.

---

## Experiment 1 — pointing (n = 3 per frame)

| Frame | Rep | Returned labels | robot_1 error | robot_2 error | Returned sep. | True sep. | Verdicts |
|---|---|---|---|---|---|---|---|
| `FRAME_CONFLICT` | 1 | `robot_1`, `robot_2` | 0.005 m (1.1 px) | 0.010 m (2.3 px) | 0.246 m | 0.252 m | 2x clear hit |
| `FRAME_CONFLICT` | 2 | `robot_1`, `robot_2` | 0.009 m (2.0 px) | 0.016 m (3.6 px) | 0.245 m | 0.252 m | 2x clear hit |
| `FRAME_CONFLICT` | 3 | `robot_1`, `robot_2` | 0.005 m (1.1 px) | 0.013 m (2.9 px) | 0.257 m | 0.252 m | 2x clear hit |
| `FRAME_CLEAR` | 1 | `robot`, `robot` | 0.125 m (28.8 px) | 0.123 m (28.3 px) | 4.636 m | 4.884 m | 2x clear hit |
| `FRAME_CLEAR` | 2 | `robot`, `robot` | 0.104 m (23.9 px) | 0.096 m (21.9 px) | 4.686 m | 4.884 m | 2x clear hit |
| `FRAME_CLEAR` | 3 | `robot`, `robot` | 0.104 m (23.8 px) | 0.095 m (21.8 px) | 4.686 m | 4.884 m | 2x clear hit |

All 12 returned points are clear hits, and the assignment is never ambiguous:
the swapped assignment costs 0.50 m (conflict) and 9.5 m (clear) against best
totals of 0.015–0.025 m and 0.199–0.249 m. On `FRAME_CONFLICT` the returned
separation (0.245–0.257 m) sits on the true 0.251 m, so ER-2 resolved **two
distinct robots 0.25 m apart**, not one blob reported twice. Output was stable
across repeats to within ~2 px. Latency 1.9–2.4 s, 1304–1408 total tokens.

Two honest qualifications:

- The stimuli are annotated frames, so the printed `robot_1`/`robot_2` labels
  are visible; the correct IDs on `FRAME_CONFLICT` are confounded with reading
  that text. The claim supported here is "the points landed on the robots",
  not ID-level grounding. On `FRAME_CLEAR` ER-2 labelled both simply `robot`.
- The overlay box centre coincides with the true robot centre by construction,
  so pointing could in principle be aided by the drawn box. Against that: on
  `FRAME_CLEAR` every point was displaced 22–29 px *inward from the marker
  toward the robot body*, i.e. at the vehicle's visual centroid rather than the
  box centre. A raw-frame (un-annotated) repeat would remove the ambiguity and
  is not run here.

---

## Experiment 2 — the incongruent 2x2 (n = 3 per cell, derived geometry on)

| Cell | Image | Text | `congestion_detected` | `type` | `strategy` | Tracks |
|---|---|---|---|---|---|---|
| A (gate) | conflict | conflict | true, true, true | deadlock x3 | reverse x3 | — |
| D (gate) | clear | clear | false, false, false | none x3 | none x3 | — |
| B | **conflict** | clear | false, false, false | none x3 | none x3 | **text** |
| C | clear | **conflict** | true, true, true | deadlock x3 | yield, reverse, reverse | **text** |

Both gate cells passed unanimously, so B and C are interpretable. B answered
clear and C answered conflict — the pre-registered signature of a decision
that tracks the **text**. 6/6 incongruent calls followed the state block;
0/6 followed the image. No justification in any of the 12 calls cited visual
evidence, and none acknowledged the contradiction between image and states.

Verbatim, cell B (image shows two robots nose-to-nose 0.25 m apart):

> "Robot 1 is heading west and Robot 2 is heading east, representing a
> diverging pattern with a safe distance of 2.50 meters."

Verbatim, cell C (image shows the robots parked 4.9 m apart at opposite ends):

> "The pairwise geometry specifies that the two robots are 0.35 meters apart,
> each facing the other, and both are stopped, which constitutes a head-on
> deadlock."

Latency 2.3–3.7 s; 2192–2567 total tokens; thought tokens 103–503.

---

## Experiment 3 — derived geometry withheld (`include_pairwise_geometry=False`)

Cells B and C re-run with the rev-8 modality switch off, so the prompt carries
raw `x, y, theta, status` plus the image but no pre-computed distance/facing
lines. n = 3 was the pre-registered size; a labelled follow-up added n = 9 per
cell after the first run produced one image-consistent answer, for n = 12.

| Cell | Image | Text | Answers (n = 12) | Tracks |
|---|---|---|---|---|
| B | **conflict** | clear | `none` 12/12 | text 12/12 |
| C | clear | **conflict** | `deadlock` 10/12, `none` 2/12 | text 10/12, image 2/12 |

The 10 text-tracking C answers do the arithmetic themselves and say so —
"within 0.34 m of each other" (0.34 m, not the 0.35 m the geometry block used
to hand them), "robot_1 at x=-0.17 is facing east and robot_2 at x=0.17 is
facing west". So withholding the derived geometry does not force the image in;
it just moves the arithmetic into the model.

The 2/12 exceptions are the only responses in all 36 decision calls whose
justification reads visual rather than numeric:

> "The robots are located on opposite sides of the central corridor, separated
> by a distance much greater than 0.5 m, and do not present any physical
> conflict or bottleneck."

> "The robots are situated far apart on opposite sides of the corridor,
> meaning they do not block each other and no congestion is present."

Both describe `FRAME_CLEAR` correctly and contradict the text states they were
given, with no numbers quoted. Two of twelve is a rate, not a capability
claim, and an alternative reading — that these are arithmetic failures whose
prose happens to match the picture — cannot be excluded from the answer text
alone (ER-2 returns no visible reasoning trace; design doc §4(d)).

**Both exceptions fall on the same side, which matters.** Cell B's
image-consistent answer would be `deadlock`, and it never appeared: B returned
`congestion_detected=false` in **15/15** calls across both geometry
conditions. Cell C's image-consistent answer is `none`, and that is where both
exceptions landed. So no call in this probe ever asserted a conflict the text
denied; the image-consistent answers coincide exactly with the
lower-commitment answer, in the condition whose thought-token load roughly
doubled (~700 vs ~180–440). That is at least as consistent with an occasional
`none` slip under self-computed arithmetic as with image use.

Geometry-off calls are slower and think more: latency mean 4.4–4.6 s vs
2.5–3.5 s with geometry on, thought tokens mean ~700 vs ~180–440.

---

## Conclusion

Keep the two verdicts separate.

- **Perception: demonstrated.** ER-2 localizes both robots in our overhead
  annotated frames, including a nose-to-nose pair 0.25 m apart, to
  0.005–0.125 m (1–29 px) — inside half a robot width on 12/12 points, stable
  across three repeats per frame (n = 3 per frame, 6 calls).
- **Decision-level image grounding: not demonstrated** in the production
  modality, and at best **marginal** with the derived geometry withheld. With
  the derived geometry present, 6/6 incongruent calls followed the text and
  0/6 followed the image (n = 3 per cell). With it withheld, 22/24 followed
  the text and 2/24 followed the image, both in cell C (n = 12 per cell) —
  and since cell B answered `none` in 15/15 calls across both conditions, no
  call ever asserted a conflict the text denied, so even those two are
  consistent with an occasional `none` slip rather than image use.

For this scenario and this prompt, ER-2's congestion decision is therefore
**equivalent to a text-only reasoner**: the image demonstrably reaches the
model and is demonstrably readable by it, and it still does not move the
answer. That is a finding the preregistration needs, because it applies to the
`gemini` Arm A cell whatever the numbers say: a "correct" ER-2 decision in this
pipeline is evidence about arithmetic on M1's state block, not about visual
scene understanding, and the same is likely true of the `openai` cell, which
has never been tested this way. The pointing result is the other half of the
finding: this is not a model that cannot see; it is a pipeline whose prompt
makes the image redundant.

---

## Threats to validity

- **The prompt directs the model to the text.** With geometry on, the prompt
  says "Use the pairwise geometry above; do not re-derive distances or facing
  from the coordinates"; with it off, "Compute distances and facing from the
  coordinates". Both give the state block primacy for geometry, and only a
  single clause ("Decide from the robot coordinates and the image") points at
  the image at all. The finding is scoped to **this project's production
  prompt**. A prompt that asked the model to verify the states against the
  image was not tested and is the obvious next probe.
- **Two stimuli, one scenario, one seed, one thinking level.** All frames come
  from one `head_on_deadlock` run at `thinking_level: low`. `high` is untested
  and is its own axis (design doc §4(c)).
- **Stimulus artifacts.** Both frames carry the recorder's burned-in
  `t=…  f=…` clock and H.264 compression; both carry it equally, so neither
  can explain a B-vs-C difference, but neither is byte-identical to what M5
  sends in production. Robot_2's overlay in `FRAME_CONFLICT` reads `STALE`
  (grey) — the known overlapping-marker artifact — while every cell's text
  says `STOPPED`.
- **Ground truth is M1's, not an external oracle.** Positions come from the
  project's ArUco + homography pipeline (re-detected, or as recorded at the
  frame's stamp), so a systematic M1 bias would move the "true" centres and
  the pointing errors together. The scene-log fallback is validated only to
  the ~1 mm agreement reported above.
- **Assignment scoring, not detection scoring.** Experiment 1 asked for one
  point per visible robot and got exactly two every time; it does not test
  false positives on an empty aisle.
- **No visible reasoning trace.** ER-2 returns none (design doc §4(d)), so
  "the justification cites numbers, not the image" is evidence about the
  *answer text*, not about the internal computation.

---

## Evidence index

- Harness: `scripts/probe_gemini_er2_grounding.py`; unit tests
  `tests/unit/test_probe_gemini_er2_grounding.py`.
- Call-level artifacts (VM, git-ignored):
  `data/logs/er2_grounding/grounding_run1.jsonl` (experiments 1–3, n = 3) and
  `data/logs/er2_grounding/grounding_run2_exp3_n9.jsonl` (experiment 3
  follow-up, n = 9).
- Stimuli (VM, git-ignored):
  `data/logs/er2_grounding/stimuli/frame_conflict_f203.png`,
  `data/logs/er2_grounding/stimuli/frame_clear_f1667.png`; source video
  `data/logs/gem_run_20260918_084649/annotated_000.mp4`.
- Ground-truth scene log:
  `data/logs/m5_scene/59254dd811cc467fa0cf2dbe79c7b857.jsonl`
  (`run_id=gemini_20260918_084649`).
- Reproduction (inside container `vgu_ros` on
  `vgu-canary-base-isaac-workstation-vm`, repo bind-mounted at `/ws`):

```bash
sudo docker exec -w /ws vgu_ros bash -lc "set -a && source /ws/.env && set +a && \
  python3 scripts/probe_gemini_er2_grounding.py --experiment all --repeats 3 \
    --frame-conflict data/logs/er2_grounding/stimuli/frame_conflict_f203.png \
    --frame-clear data/logs/er2_grounding/stimuli/frame_clear_f1667.png \
    --conflict-stamp 1789721320.33 --clear-stamp 1789721707.53 \
    --scene-log data/logs/m5_scene/59254dd811cc467fa0cf2dbe79c7b857.jsonl"
```
