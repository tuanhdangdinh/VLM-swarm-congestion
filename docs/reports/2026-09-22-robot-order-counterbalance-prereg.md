# Robot-Order Counterbalance — Pre-Registration

**Prepared:** 2026-09-22

**Status:** Pre-registered. Written and committed before any stimulus was
collected and before any model call was made.

**Branch:** `feat/robot-order-counterbalance`

**Related:** `docs/reports/2026-09-18-head-on-family-validity.md` (the null
this experiment exists to interpret),
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
(rev-8, tuning-parity and freeze rules).

---

## 1. The question

When M2 names a robot in `yield_robot`, does that choice follow the
**robot's identity** or its **position in the prompt's robot list**?

## 2. Why it has to be answered first

`build_prompt_payload` sorts robot states by ID and derives three separate
prompt features from that one sorted list: the robot-state block, the
`known_robot_ids` JSON array, and the pairwise-geometry lines. The template
header states "Robot states (sorted by ID)". Because the scenarios spawn
`robot_1` and `robot_2`, **`robot_1` has been presented first in every
artifact this project has ever collected.**

"The model chose `robot_1`" and "the model chose the first-listed robot"
are therefore the same observation. This applies to:

- the paired obstacle-modality A/B runs of 2026-09-19, whose null result
  is uninterpretable until this is separated;
- the 44/44 yielder census previously read as evidence that list position
  was an unused channel;
- every `yield_robot` value in the 599 archived decision artifacts.

No claim about yielder selection can be made until identity and position
are pulled apart.

## 3. Design

**One factor, two levels, within-stimulus.** Every stimulus is rendered and
sent twice:

| Level | Robot list order | Header text |
|---|---|---|
| `ascending` | sorted by ID (production default) | `sorted by ID` |
| `reversed` | descending by ID | `reverse-sorted by ID` |

The obstacle modality stays **OFF** (the production default) in both
levels. It was measured and found null on 2026-09-19; making this a 2×2
would multiply cost for a channel already tested.

`failure_context` is **`None`** for every stimulus. This fixes each
stimulus at the first-analysis decision point rather than mixing in
recovery advice. Standardizing matters: 6 of the 15 archived standoff
scenes carried a failure-context block and 9 did not.

**Unit of analysis is the stimulus, not the call.** gpt-4o at temperature
0.0 on this endpoint is near-deterministic but not deterministic (Finding
A1: raw responses unique in 2-5 of 5 repeats). Repeats measure stability,
not independent evidence. Conclusions are drawn across stimuli; repeats
per cell report stability only.

**Repeats:** 5 per stimulus per level.

## 4. Stimuli

Archived scenes cannot be used. The OpenAI backend base64-encodes
`payload.image_path`, and the frames for all 15 archived standoff scenes no
longer exist on the VM. This is itself a defect (see §7) and is fixed
before stimuli are collected.

**Collection:** one simulation run on the blocked head-on variant with
frame retention in place, capturing matched scene-and-frame pairs.

**Selection rule**, applied mechanically to the captured run, fixed here
before collection:

1. Exactly 2 robots in the scene.
2. Inter-robot distance ≤ 0.60 m.
3. Both robots `STOPPED` or `STALE`.
4. A readable frame exists on disk for the request.
5. Deduplicate on both robots' `(x, y)` rounded to 2 decimals; keep the
   earliest artifact of each duplicate group.

All stimuli surviving the rule are used. No stimulus is dropped after its
responses are seen.

## 5. Measures

Recorded separately for every call, because they can dissociate:

- **`yield_robot`** — the named field. The primary measure.
- **`involved_robots`** — the list order the model returned.
- `strategy`, `congestion_detected`, and the raw response text.

A call where `strategy != "yield"` or `yield_robot` is absent contributes
no `yield_robot` datum and is reported as such, not silently dropped.

A stimulus is scored **position-following** if its modal `yield_robot`
differs between the two levels, and **identity-following** if it is the
same robot at both levels.

## 6. Pre-registered criterion

Let *N* be the number of stimuli yielding a usable pair of modal answers.

- **Position-driven** if ≥ 80 % of the *N* stimuli are position-following.
- **Identity-driven** if ≥ 80 % are identity-following.
- **Indeterminate** otherwise.

An indeterminate result licenses **collecting more stimuli under this same
pre-registration**. It does not license reinterpreting the criterion, and
it does not license reporting the majority direction as the finding.

`involved_robots` order is scored the same way and reported as its own
line. If `yield_robot` tracks identity while `involved_robots` tracks
presentation, the named field is carrying real information the positional
convention did not. If both track presentation, it is not.

## 7. Defect fixed as part of this work

`frame_dump_dir` is a relative path resolved against the node's working
directory, and the decision artifact records prompt SHA-256 hashes but no
frame path and no frame hash. The text half of every historical stimulus
is frozen and the image half is not recoverable. Three frames survive on
the VM against 599 decision artifacts.

Fix: resolve the dump directory to an absolute path, and record the frame
path plus its SHA-256 in the decision artifact.

## 8. Limitation that this experiment does not remove

`robot_1` spawns on the **west** side in every scenario in the family.
Counterbalancing list order separates identity from position; it does not
separate identity from **side**. Mirroring the coordinates in a replay
would desynchronize the text from the overhead image, so the replay
apparatus cannot address it.

Separating side requires a mirrored *scenario* run, with a real image, and
is out of scope here. A reader must not take a result from this experiment
as having cleared all three confounds.
