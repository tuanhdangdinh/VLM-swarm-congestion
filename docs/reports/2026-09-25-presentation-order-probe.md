# Presentation-Order Probe - Does the Chosen Yielder Follow Slot, ID, or Geometry?

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: offline counterbalanced-order probe on the head-on asymmetric family, gpt-4o and gpt-4o-mini.

---

## Purpose and Hypotheses

The 2026-09-19 finding recorded in `docs/reports/2026-09-18-head-on-family-validity.md`
is that every live gpt-4o `yield` decision on the head-on asymmetric family named
`robot_1` — including on `head_on_asymmetric_w0p2_eopen_o0`, where a parked
0.3 x 0.3 m box 0.2 m behind `robot_1`'s spawn makes that yield physically
impossible. `robot_1` is also the robot the prompt always presents first, because
`build_prompt_payload` rendered robots sorted ascending by `robot_id`. Choice and
presentation order were therefore perfectly confounded, and the static-obstacle
modality A/B run against that scene was a null that bounded nothing.

This probe breaks the confound by counterbalancing the presentation order. Three
hypotheses predict distinct signatures across the variant x order cells, reported
as the chosen `yield_robot`:

| Hypothesis | w0p2_eopen, id_asc | w0p2_eopen, id_desc | wopen_e0p2, id_asc | wopen_e0p2, id_desc |
|---|---|---|---|---|
| H_slot (follows the first-listed slot) | robot_1 | robot_2 | robot_1 | robot_2 |
| H_id (always `robot_1`) | robot_1 | robot_1 | robot_1 | robot_1 |
| H_geom (follows `correct_yielder`) | robot_2 | robot_2 | robot_1 | robot_1 |

The two `id_desc` cells jointly separate all three: no single cell does. The
symmetric variant `wopen_eopen` discriminates nothing and is included only to
measure the default bias when both robots are feasible.

---

## Apparatus

### Modality

`ReasonerRequest` gained `robot_presentation_order: Literal["id_asc", "id_desc"]`
(default `id_asc`) in commit `922dd36`. Under `id_desc` the robot-state lines,
the `Known robot IDs` JSON list and the pairwise-geometry line's `first`/`second`
roles all reverse together; nothing else in the rendered prompt changes. The
default path is pinned byte-for-byte by
`test_build_prompt_payload_default_order_matches_the_pre_feature_prompt`
(3338 chars, SHA-256 `3b77d224…`), so every artifact collected before this
feature stays comparable. M5 exposes the axis as `prompt_robot_order` in
`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`, shipped at `id_asc`.

The template header still reads `Robot states (sorted by ID):`, which is true in
both directions and was left untouched so the two conditions differ only in
ordering. The prompt contains no "first listed" wording: the clause that used to
instruct the model to back up the first-listed robot was removed before this
probe (guard test `test_build_prompt_payload_omits_yielder_selection_criteria`).

### Probe

`scripts/probe_presentation_order.py`, run on commit `922dd36` (the modality);
the probe and its raw data are committed as `dadb3f5`. Twelve cells: three scenario variants x two presentation orders x the
static-obstacle channel on/off. Per cell, 5 samples at `temperature=0.0` (the
shipped `vlm.openai.reasoner.temperature`) and 10 at `temperature=0.6`, giving
180 calls per model. The production path is reused end to end:
`reasoning.vlm.reasoner.Reasoner` over `backend_factory.build_backend("openai")`,
so prompt rendering, re-ask, parsing and decision validation are the live code.

Scene: both robots `STOPPED` nose-to-nose at the corridor centre,
`robot_1 (-0.225, 0.0, theta=0.0)` and `robot_2 (0.225, 0.0, theta=pi)`, zero
velocities, `failure_context=None` (first decision of an episode),
`include_pairwise_geometry=True`. Scenario geometry is read from
`isaac/config/scenarios/family/*.yaml` with the project's own `ScenarioConfig`.
Prompt-facing obstacle ids are renumbered `obstacle_1…` exactly as the shipped M5
config requires, so the scenario file's `blocker_west` never reaches the model.

Robot states carry no `goal` and no `task`. That is not an omission: M5 builds
requests from a `SceneSnapshot` whose `RobotView` has neither field, so no live
prompt has ever contained them.

### Synthetic image caveat

The OpenAI backend requires an image. The probe renders a deterministic synthetic
top-down plan view with Pillow (one per variant, shared by all four cells of that
variant) at the live camera's ROI and scale (6.0 x 4.5 m onto 1280 x 960 px), using
`swarm_perception/annotation.py` conventions: status-coloured robot box, ID label,
goal circle-and-cross, and a heading line. It is **not** a camera frame: no ArUco
markers, no lighting, no perspective, no noise. Two consequences:

- The heading indicator is always drawn. M1 gates its velocity arrow on
  `|v| > 1e-3`, so the live annotated frame at a standoff has none. The synthetic
  image is therefore marginally *more* informative than the live one, which makes
  a null geometry effect the conservative reading.
- The blocker box is drawn in every variant image, including the
  obstacle-channel-OFF cells. OFF removes only the *textual* obstacle channel; it
  does not make the obstacle unobservable.

A structural consequence of that second point is worth stating plainly: with the
obstacle channel OFF, **all three variants render a byte-identical prompt for a
given order**. Those cells differ only in the image, so they are a direct test of
whether the model reads the blocker from the picture at all. Likewise, the
symmetric variant has no obstacles to render, so its channel-on and channel-off
cells are the same prompt and the same image — a within-model reproducibility
pair, not an ablation.

### Rate limiting

The account caps gpt-4o at 30,000 tokens per minute and one probe call costs
roughly 1.9k tokens. An unpaced first attempt at six workers spent 157 of 180
calls on HTTP 429. The script now paces every backend call (including
`Reasoner`'s internal retry) to one per `--min-interval-sec` (4.0 s) and applies
jittered exponential backoff on transport failures.

### Cost and volume

| Model | Calls | Prompt tokens | Completion tokens | Cost |
|---|---|---|---|---|
| gpt-4o | 180 | 300,180 | 33,955 | $1.09 |
| gpt-4o-mini | 180 | 4,752,660 | 30,007 | $0.73 |

gpt-4o-mini's prompt-token count is ~16x gpt-4o's for the identical payload
because the two models bill the same image at very different token counts; the
text is the same in both.

### Analysis choices and artifact integrity

The 0.70 modal-share margin below which a cell is called too close to read was
chosen **after** the first, rate-limited run had already shown cells near 0.50,
not pre-registered. It is disclosed here because it is what separates gpt-4o's
"mixed" verdict from gpt-4o-mini's "H_slot". The pooled order-effect and
geometry-effect statistics, which carry the conclusion, do not depend on it.

Every one of the 360 records has `parse_status="valid"`, so the re-ask path never
fired and the prompt recorded for each cell is the prompt that was sent; the
SHA-256 of each committed `prompts/<cell>.txt` matches the `prompt_sha256` on all
of that cell's records. 128 of the 360 calls needed a second backend attempt
after an HTTP 429 on the first; `Reasoner` reissues the *unchanged* payload on a
transport error, so those records are unaffected.

---

## Results

360 calls (180 per model), **zero parse failures and zero API errors**. Every
parsed decision reported `congestion_detected=true`; gpt-4o chose
`strategy="yield"` in 179 of 180 and `reverse` once, gpt-4o-mini chose `yield`
in 180 of 180. `P(strategy != yield)` is therefore ~0 everywhere and the
yielder's identity carries the whole signal.

`P(modal)` is the modal yielder's share within its cell. A cell whose modal
answer wins by less than 0.70 is too close to call, which is why the
per-condition signature verdict degrades to "mixed" rather than inheriting a
coin-flip's label.

### Per-cell results

#### gpt-4o, temperature 0.0

| Variant | Order | Obstacles | n | parse fail | modal yielder | P(modal) | P(first-listed) | P(robot_1) | P(correct) | P(!yield) |
|---|---|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_desc` | off | 5 | 0 | robot_2 | 0.60 | 0.60 | 0.40 | 0.60 | 0.00 |
| `w0p2_eopen` | `id_desc` | on | 5 | 0 | robot_2 | 0.80 | 0.80 | 0.20 | 0.80 | 0.00 |
| `wopen_e0p2` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_desc` | off | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| `wopen_e0p2` | `id_desc` | on | 5 | 0 | robot_2 | 0.60 | 0.60 | 0.40 | 0.40 | 0.00 |
| `wopen_eopen` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_desc` | off | 5 | 0 | robot_1 | 0.60 | 0.40 | 0.60 | 0.60 | 0.00 |
| `wopen_eopen` | `id_desc` | on | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |

#### gpt-4o, temperature 0.6

| Variant | Order | Obstacles | n | parse fail | modal yielder | P(modal) | P(first-listed) | P(robot_1) | P(correct) | P(!yield) |
|---|---|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | `id_asc` | off | 10 | 0 | robot_1 | 0.80 | 0.80 | 0.80 | 0.20 | 0.00 |
| `w0p2_eopen` | `id_asc` | on | 10 | 0 | robot_1 | 0.90 | 0.90 | 0.90 | 0.10 | 0.00 |
| `w0p2_eopen` | `id_desc` | off | 10 | 0 | robot_2 | 0.50 | 0.50 | 0.50 | 0.50 | 0.00 |
| `w0p2_eopen` | `id_desc` | on | 10 | 0 | robot_2 | 0.70 | 0.70 | 0.30 | 0.70 | 0.00 |
| `wopen_e0p2` | `id_asc` | off | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | on | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.10 |
| `wopen_e0p2` | `id_desc` | off | 10 | 0 | robot_2 | 0.50 | 0.50 | 0.50 | 0.50 | 0.00 |
| `wopen_e0p2` | `id_desc` | on | 10 | 0 | robot_1 | 0.60 | 0.40 | 0.60 | 0.60 | 0.00 |
| `wopen_eopen` | `id_asc` | off | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_asc` | on | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_desc` | off | 10 | 0 | robot_2 | 0.60 | 0.60 | 0.40 | 0.40 | 0.00 |
| `wopen_eopen` | `id_desc` | on | 10 | 0 | robot_1 | 0.60 | 0.40 | 0.60 | 0.60 | 0.00 |


#### gpt-4o-mini, temperature 0.0

| Variant | Order | Obstacles | n | parse fail | modal yielder | P(modal) | P(first-listed) | P(robot_1) | P(correct) | P(!yield) |
|---|---|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_desc` | off | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| `w0p2_eopen` | `id_desc` | on | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_desc` | off | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| `wopen_e0p2` | `id_desc` | on | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| `wopen_eopen` | `id_asc` | off | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_asc` | on | 5 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_desc` | off | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| `wopen_eopen` | `id_desc` | on | 5 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |

#### gpt-4o-mini, temperature 0.6

| Variant | Order | Obstacles | n | parse fail | modal yielder | P(modal) | P(first-listed) | P(robot_1) | P(correct) | P(!yield) |
|---|---|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | `id_asc` | off | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_asc` | on | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 |
| `w0p2_eopen` | `id_desc` | off | 10 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| `w0p2_eopen` | `id_desc` | on | 10 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | off | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_asc` | on | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_e0p2` | `id_desc` | off | 10 | 0 | robot_2 | 0.90 | 0.90 | 0.10 | 0.10 | 0.00 |
| `wopen_e0p2` | `id_desc` | on | 10 | 0 | robot_2 | 0.90 | 0.90 | 0.10 | 0.10 | 0.00 |
| `wopen_eopen` | `id_asc` | off | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_asc` | on | 10 | 0 | robot_1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 |
| `wopen_eopen` | `id_desc` | off | 10 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| `wopen_eopen` | `id_desc` | on | 10 | 0 | robot_2 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 |

### Pooled order effect (asymmetric variants only)

| Model | T | `id_asc` P(robot_1) | `id_desc` P(robot_1) | `id_asc` P(first-listed) | `id_desc` P(first-listed) | Fisher exact (two-sided) |
|---|---|---|---|---|---|---|
| gpt-4o | 0.0 | 20/20 = 1.00 | 5/20 = 0.25 | 1.00 | 0.75 | p = 7.7e-07 |
| gpt-4o | 0.6 | 36/39 = 0.92 | 19/40 = 0.47 | 0.92 | 0.53 | p = 1.7e-05 |
| gpt-4o-mini | 0.0 | 20/20 = 1.00 | 0/20 = 0.00 | 1.00 | 1.00 | p = 1.5e-11 |
| gpt-4o-mini | 0.6 | 40/40 = 1.00 | 2/40 = 0.05 | 1.00 | 0.95 | p = 1.4e-13 |

### Pooled geometry effect (asymmetric variants only)

`P(yield_robot == correct_yielder)`:

| Model | T | obstacles off | obstacles on |
|---|---|---|---|
| gpt-4o | 0.0 | 0.40 | 0.55 |
| gpt-4o | 0.6 | 0.55 | 0.59 |
| gpt-4o-mini | 0.0 | 0.50 | 0.50 |
| gpt-4o-mini | 0.6 | 0.55 | 0.55 |

### Signature verdicts

| Model | T | Obstacles | Verdict | Weakest discriminating cell P(modal) |
|---|---|---|---|---|
| gpt-4o | 0.0 | off | mixed | 0.60 |
| gpt-4o | 0.0 | on | mixed | 0.60 |
| gpt-4o | 0.6 | off | mixed | 0.50 |
| gpt-4o | 0.6 | on | mixed | 0.60 |
| gpt-4o-mini | 0.0 | off | H_slot | 1.00 |
| gpt-4o-mini | 0.0 | on | H_slot | 1.00 |
| gpt-4o-mini | 0.6 | off | H_slot | 0.90 |
| gpt-4o-mini | 0.6 | on | H_slot | 0.90 |

gpt-4o's "mixed" is not an absence of an order effect — the pooled table above
shows a very large one. It records that gpt-4o under `id_desc` does not commit
cleanly to either candidate, so no single signature fits all four of its
discriminating cells. gpt-4o-mini matches `H_slot` exactly.

Raw calls: `data/experiments/2026-09-25-presentation-order/<model>/calls.jsonl`
(one record per call, with the rendered prompt's SHA-256, the raw response and
the parsed decision). Per-cell aggregates: `summary.csv`. Rendered prompts:
`prompts/<cell>.txt`. Synthetic images: `images/<variant>.png`.

---

## Interpretation

**Presentation order determines the chosen yielder. Geometry does not.** That
holds for both models, at both temperatures, with and without the textual
obstacle channel.

### H_geom is refuted

The oracle's `correct_yielder` has no measurable influence on the choice in any
condition. Pooled over the two asymmetric variants, `P(yield_robot ==
correct_yielder)` spans 0.40 to 0.59 for gpt-4o and is 0.50, 0.50, 0.55, 0.55
for gpt-4o-mini — indistinguishable from the 0.50 a coin would give, and the
obstacle channel does not move it. gpt-4o-mini's figures are exactly 0.50 by
construction: it picks the first-listed robot in essentially every call, and the
oracle's answer is orthogonal to the slot. Supplying the blocker's centre and
extent as text, on top of drawing it in the image, buys nothing. This reproduces
the 2026-09-19 null on a distribution rather than a single paired run, and now
with the confound removed: the null is not an artifact of presentation order.

Nothing in any justification string cited the obstacle, even with the channel on.

### H_id is refuted

`P(yield_robot == robot_1)` is not order-invariant. Pooled over the asymmetric
variants it falls from 20/20 under `id_asc` to 5/20 under `id_desc` at
temperature 0.0 (Fisher exact two-sided p = 7.7e-07) and from 36/39 to 19/40 at
temperature 0.6 (p = 1.7e-05). For gpt-4o-mini the collapse is near-total:
20/20 to 0/20 (p = 1.5e-11) and 40/40 to 2/40 (p = 1.4e-13). Reversing the
presentation order — and nothing else — moves the answer.

### gpt-4o-mini is H_slot outright

gpt-4o-mini named the first-listed robot in every one of its 60 greedy calls and
in 59 of 60 `id_desc` calls at temperature 0.6 — `P(first-listed)` of 1.00, 1.00,
1.00 and 0.95 across the four conditions, matching the `H_slot` signature exactly
in all of them. The position of the robot in the list is, for this model, the
whole decision procedure.

### gpt-4o is slot-dominant with a residual ID pull

gpt-4o is not a clean mirror image. Under `id_asc` its choice is deterministic:
all six `id_asc` cells at temperature 0.0 chose the first-listed robot in 5/5
samples (30/30 calls), and the pooled figure at temperature 0.6 is 36/39. Under
`id_desc` it degrades to 0.75 (T=0.0) and 0.53 (T=0.6) — a near-coin-flip at the
sampled temperature rather than a confident flip to `robot_2`.

That is the signature of a **first-slot preference competing with a weaker
`robot_1`-identity preference**, not of either alone. Under `id_asc` the two
agree and the model is deterministic; under `id_desc` they oppose, the slot
preference still wins on balance, and the residual is the ID pull. Side by side
with gpt-4o-mini's clean `H_slot`, the reading is that both models default to the
first slot and only gpt-4o carries a second, weaker positional habit on top.

The practical consequence for the research programme is that the live 44/44
`robot_1` result is fully explained without any spatial reasoning: it is what two
agreeing positional biases produce when they are never put in conflict.

### The bias survives removal of the instruction that used to license it

The 44/44 census was collected under a prompt that explicitly told the model the
first-listed robot should back up (`docs/reports/2026-09-18-head-on-family-validity.md`,
Rev 6). That clause has since been removed, and a guard test now asserts the
string "first listed" is absent from the rendered prompt. This probe ran against
the post-removal prompt and still finds a deterministic first-slot choice under
`id_asc`. The positional bias is therefore **not** instruction-compliance: it
outlived the instruction.

### Where the model is unmoved

`congestion_detected` was true in all 360 calls, and the strategy was `yield` in
359 of them. Neither the order manipulation nor the obstacle channel changed
*what* either model decided to do; they changed only *whom* it named. gpt-4o also
echoes the presentation order in its own output: `involved_robots[0]` matched the
first-listed robot in 167/180 calls.

Because the three variants render a byte-identical prompt when the obstacle
channel is off, those cells differ only in the image — the blocker sits west,
east, or nowhere. Comparing `w0p2_eopen` against `wopen_e0p2` in those cells,
pooled over temperature, gives Fisher exact two-sided p = 0.48 (gpt-4o `id_asc`),
0.71 (gpt-4o `id_desc`), 1.00 and 1.00 (gpt-4o-mini). Moving the blocker from one
end of the corridor to the other, with the text held byte-identical, does not
detectably change which robot is named: the models are not reading the obstacle
out of the plan view either.

This is a text-and-synthetic-image probe, not the live pipeline. It establishes
what the current M2 prompt elicits from these two models; it does not by itself
establish what the deployed system does. The verdict needs a counterbalanced live
run before it is treated as a property of the system.

---

## Limitations

- **Offline, synthetic stimulus.** This is not the live pipeline: no Isaac Sim,
  no M1 perception, no real camera frame, and a hand-authored onset pose rather
  than a naturally-arrived deadlock. It constrains what the *prompt* elicits, not
  what the deployed system does. The verdict must be confirmed by live runs on
  the same family before it is treated as a property of the system.
- **Onset pose is idealised.** Both robots sit exactly on the corridor axis at a
  symmetric 0.45 m standoff. Live onsets carry M1 position bias and small lateral
  and heading offsets that could themselves break a tie.
- **The three ordered channels are not separable.** `id_desc` reverses the
  robot-state lines, the `Known robot IDs` list and the pairwise-geometry
  `first`/`second` roles *together*, so "follows the slot" here means "follows the
  first-mentioned robot across all three channels jointly". The probe cannot say
  which of the three carries the effect.
- **Two robots only.** Presentation order has one degree of freedom here. Nothing
  is established about three or more robots, where slot and ID can dissociate in
  more ways.
- **One prompt template.** The result is a property of the current M2 prompt, not
  of the model in general. The template still says `sorted by ID`, and it opens
  by naming the task as detection rather than adjudication.
- **`correct_yielder` is the oracle's objective**, `min_total_time_to_goal`, not a
  safety constraint. A model choosing the infeasible yielder is not violating a
  stated rule of the prompt — the prompt never tells it to consider feasibility.
- **Cost of the modality itself.** The probe validates the new `id_desc` path
  against the live prompt only through the unit-test pin on the `id_asc` default;
  no live run has yet rendered an `id_desc` prompt through M5.

---

## Next Steps

1. **Counterbalanced live run.** Run the head-on asymmetric family on the GPU VM
   with `prompt_robot_order: id_desc` on half the runs, paired with `id_asc`, on
   the same scenarios. This is the confirmation the interpretation above is
   explicitly conditional on.
2. **Separate the three ordered channels.** `id_desc` reverses the state lines,
   the known-ID list and the pairwise-geometry roles together. Reverse one at a
   time to find which carries the effect — cheap, offline, and it tells us where
   a debiasing fix would have to go.
3. **Debiasing candidates to test offline before any live run.** Randomise the
   presentation order per request; or state the yielder-selection criterion
   explicitly (feasibility first) and re-measure `P(correct)`. The second is a
   prompt change with downstream consequences and needs its own spec entry.
4. **Do not report the obstacle-channel A/B as a modality result** until the
   order confound is removed from the historical artifacts too. Every artifact
   collected before commit `922dd36` was rendered at `id_asc` and carries this
   bias.
5. **Re-check the oracle objective.** `correct_yielder` optimises
   `min_total_time_to_goal`. If the intended M2 contract is "never name a yielder
   that cannot execute", that is a feasibility constraint the prompt does not
   currently state at all, and no amount of geometry channel will supply it.
