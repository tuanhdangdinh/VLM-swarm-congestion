# Prompt Apparatus v2: Metric Grid, Zoom Tile, Motion Trails, Permutation Votes, Candidate Options

**Prepared:** 2026-10-04

**Revision history:**

- Initial draft: the five rev-6 prompt-apparatus items, updated by the round-3 scan deltas, built on `feat/v2-apparatus`. Each item sits behind its own flag, and every flag defaults off. Covers the local build, unit tests and pins, plus the coordinator-authorized mock-backend VM smoke: one annotation run and one permutation-vote run, VM restored pristine.

---

## Summary

Branch `feat/v2-apparatus` was cut from `feat/prereg-v2-composite` at
`aec58cc`. The authoritative spec is
`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (main checkout):
"Prompt apparatus (rev 6)", the "Round-3 scan deltas (2026-10-04)" block
and the (a0) rulings. The candidate-options rationale is in
`reports/VLM planner coordinator recent work.md`, section "Composition
from marked candidates is unclaimed".

All five items are **A/B conditions, never defaults**. The round-3 delta
is honoured: the grid ships as a per-backend A/B, never on by default.
With every flag off, three things are pinned unchanged:

- the shipped prompt: the six v3.2 pins pass untouched, and v1/v2 are untouched;
- the annotated frame;
- the backend request bodies.

| # | Item | Flag(s) | Owner |
|---|---|---|---|
| 1 | Labeled metric grid on the annotated frame | M1 `annotation.metric_grid` (+ `metric_grid_spacing_m`, registered 0.5 m); M5 `prompt_metric_grid` | M1 draws, M5 states |
| 2 | Zoomed congestion-crop tile (second image) | M5 `prompt_zoom_tile` (+ `_margin_m` 0.6, `_width_px` 640) | M5 crops; backends carry an ordered image list |
| 3 | Motion-trail overlay | M1 `annotation.motion_trails` (+ window 3.0 s, step 0.1 s, cap 40); M5 `prompt_motion_trails` | M1 draws, M5 states |
| 4 | Permutation voting | M5 `prompt_permutation_votes` (default 1) | M5 |
| 5 | Verifier-candidate-options block | M5 `prompt_candidate_options` | M3 derives, M5 renders |

Suite: **63 failed / 4796 passed / 153 skipped / 3 errors**, against the
clean detached baseline at `aec58cc` of 63 / 4581 / 152 / 3.

- The failing-name set is identical.
- The +215 passes are this branch's new tests.
- The +1 local skip is the `launch_ros` annotation-loader test, since
  `launch_ros` is absent locally. In the VM container the skip is instead
  the build-gated frame hash pin; see "Pins".
- The VM container ran the apparatus test files on OpenCV 4.6.0: 209 passed, 1 skipped.

VM smoke: see "VM Verification Smoke".

---

## Cross-Cutting Rules

- **Gate on what was rendered, not on config.** A sentence renders only
  when the request says the frame or attachment actually carries the
  thing it names. This is the `_OBSTACLES_ON` precedent.
  - M1 reports its overlays in `SceneState.diagnostics`
    (`annotation_overlays`, `metric_grid_spacing_m`). The keys appear
    only when an overlay is on, so flag-off diagnostics are
    byte-identical.
  - M5 states the grid/trail sentence only when its flag is on AND M1
    reports drawing it. A mismatch in either direction is logged
    (`apparatus mismatch`) and recorded.
  - The tile sentence renders only when a tile file was actually written.
- **v3-only.** The sentences, the options block and the tile attachment
  are rendered by the prompt-v3 template only. The frozen v1/v2 templates
  ignore the fields (pinned).
  - `OrchestratorConfig` fails fast when a text-bearing flag is on
    without `plan_channel_enabled`, because M5 renders v3 only behind
    that flag.
  - Votes carry no text and work at any version.
- **Every flag in every artifact.** A new top-level `prompt_conditions`
  block is written on every decision artifact, triggered or probe, with
  every flag including all-off. It records:
  - per overlay: `requested` / `m1_drawn` / `stated`;
  - the grid spacing;
  - the full zoom-tile record (crop bounds, world bounds, sizes, reason
    when dropped);
  - the vote count;
  - the options block contents and `construct_constrained_selection`;
  - the prompt version.

  This is the one deliberate exception to the conditional-add
  byte-identity pattern, because the brief requires the flags in every
  artifact. `_TRIGGERED_ARTIFACT_KEYS` gains `prompt_conditions`.
- **Replay.** `scripts/replay_live_decisions.py` rebuilds the apparatus
  request fields from `prompt_conditions`. An apparatus-on artifact
  re-renders byte-identically (test-pinned). An artifact without the
  block reconstructs as all-off.
- **No leak into Arm B or the probe battery.** `reasoning/baselines`,
  `shadow_classical.py`, `reasoning/vlm/capability_probes` and
  `scripts/capability_probes.py` never import the stage-1 prompt builder
  and never name an apparatus field (AST/grep-pinned). T0 probes render
  frozen v2 and never vote (`analyze`). Their artifacts still record
  M1's overlays, because a drawn grid reaches the probe's image channel.
  That is a confound worth reporting if the grid is ever on during
  collection.
- **RGB/BGR.** Overlays draw RGB colours on the RGB frame. The zoom tile
  is cut from the RGB frame and converted to BGR only at `cv2.imwrite`
  (test: red lands in BGR channel 2).

---

## Item 1 — Labeled Metric Grid (M1)

`swarm_perception/annotation.py`: `MetricGridSpec`,
`metric_grid_spec(calibration, spacing_m)`, `draw_metric_grid`, and the
pure label helpers `metric_grid_cell_label` / `metric_grid_cell_bounds`.
The bounds helper is the verifier direction, label → world box.

- **Convention.** The grid is world-frame and aligned to multiples of
  the spacing over the calibrated camera's visible floor.
  - Columns are lettered **west → east** (A = smallest x; AA, AB… past
    Z). Rows are numbered **north → south** (1 = largest y).
  - A cell is addressed as letter+number, e.g. `C4` = x ∈ [−2.0, −1.5),
    y ∈ [0.5, 1.0) on the shipped calibration.
  - Shipped camera: x0 = −3.0, y0 = 2.5, 12 columns (A–L) × 10 rows.
- **Recessive styling.**
  - Lines are 1 px, alpha-blended white at 0.40, weighted by the
    anti-aliased coverage.
  - Labels sit **in the margins only** (letters along the top, numbers
    along the left), at 0.45 scale with a dark shadow, alpha 0.80.
  - An edge cell with less than 40 % of its width visible gets no label.
  - The probe battery's `grid.py` 3×3 badges were a style reference only:
    this is a finer metric grid with no floor badges.
- **No occlusion.** Every overlay pixel inside a 0.20 m disc around each
  tracked robot (footprint plus slack) is restored from the un-overlaid
  frame, so neither the grid nor a trail can cover a robot body or its
  marker (pinned per robot).
  - Overlays are drawn under the robot boxes.
  - M1 detection runs on the undistorted frame BEFORE annotation, so
    overlays cannot affect tracking. The mask protects the VLM's view
    only.
- **Prompt sentence** (v3, verbatim, spacing from the request):

  > The overhead image carries a labeled metric grid on the floor, one line every 0.5 m: columns are lettered from west to east and rows are numbered from north to south along the image margins, and a cell is named by its column letter and row number, e.g. C4.

- **Plumbing.** The node declares `annotation.metric_grid`,
  `annotation.metric_grid_spacing_m` and the trail parameters.
  `perception.launch.py` reads them from the new
  `config/annotation.yaml` (all off; a missing or malformed file keeps
  them off, the `aruco.yaml` pattern). `process_frame` gains keyword-only
  `metric_grid` / `motion_trails` arguments.
- **Label scope.** Measured grid gains are point-grounding results; their
  transfer to plan-level outputs is our inference (round-3 report). The
  label→metric helper exists for discrete cell references. No M3 code
  consumes cell labels yet.

## Item 2 — Zoomed Congestion-Crop Tile (M5 + backends)

- **Crop** (`swarm_orchestrator/zoom_tile.py`).
  - The tile is cut from the same annotated RGB frame M2 is sent, so it
    carries the same M1 annotation and overlays.
  - The crop covers the world bounding box of the robots the analysis
    was triggered for, plus a 0.6 m margin. It is projected through M1's
    calibration (shared with the stage-2 marker,
    `CandidateMarker.calibration`), widened to the frame aspect ratio,
    clamped to the frame, and resized to 640 px wide: `INTER_CUBIC` up,
    `INTER_AREA` down.
  - The tile is written synchronously in `_submit_pipeline` as
    `<request_id>_zoom.png`, so the request never names a tile that
    failed. It is cleaned up with the frame unless `keep_debug_frames`.
  - Every failure drops the tile and its sentence and records a reason:
    no calibration, no frame, no robots, non-uniform resize, write error.
- **Payload.** `PromptPayload.extra_image_paths` (ordered, default
  empty). The overhead frame stays first in every backend.
  - **openai:** text, frame `image_url`, tile `image_url` (both
    `detail: high`). Chat Completions takes several image parts.
  - **gemini:** `input` = text, frame `image`, tile `image`. The
    Interactions API's multi-image input shape was checked against the
    image-understanding guide's multi-image example on 2026-10-04. It
    is the same part shape we already send.
  - **anthropic:** frame, tile, then text (image-first, as before).
  - **llama_server:** **raises** on extra images. Multi-image support
    through mtmd is unverified, so the backend refuses rather than drop
    an image the prompt announces. M5 fails fast at startup on
    `prompt_zoom_tile` + `llama_server`.
  - Flag-off openai/gemini bodies match their `aec58cc` hashes, pinned.
  - No HTTP-layer redesign was needed for either required backend.
- **Reasoner.** The existence check covers extra images. The
  refusal-mitigation neutral-image fallback now **neutralizes every
  image**, the tile included. The tile is a crop of the realistic
  annotated frame, which is the refusal trigger, so replacing only the
  frame would have kept the trigger. The image count and sizes stay as
  sent.
- **Prompt sentence** (v3, verbatim):

  > A second image follows the overhead view: an enlarged crop of the same annotated frame around the robots this analysis was triggered for. It shows part of the same scene at higher magnification, not additional robots.

## Item 3 — Motion-Trail Overlay (M1)

The state estimator keeps no position history: it filters velocity from
the previous pose only. The annotator therefore owns a small
`TrailHistory` ring buffer.

- **Buffer contents.** It appends only freshly detected poses: not STALE,
  and `robot.stamp == scene.stamp`. It keeps one point per ≥ 0.1 s of
  frame-stamp time, holds a 3.0 s window with a hard cap of 40 points,
  and forgets robots that leave the scene.
- **Resets.** The buffer clears on `clock_reset` or a backward stamp.
  Dropped frames are ignored.
- **Time base.** The window is frame-stamp (sim-time) seconds, so trail
  length does not depend on fps or the real-time factor.
- **Drawing.** A fading polyline in the robot's status colour, 2 px, in
  four age buckets (alpha 0.20 / 0.40 / 0.65 / 0.90; older is fainter).
  It is drawn under the robot boxes and masked out of every robot
  footprint. A stationary history draws nothing (pinned).
- **Prompt sentence** (v3, verbatim):

  > Each robot's recently detected positions are drawn behind it as a fading trail in its status color: the faint end is the oldest position, the solid end the most recent.

No literature exists on baked-in trails. This is a novel measurement
cell, as registered.

## Item 4 — Permutation Voting (M5)

`swarm_orchestrator/permutation_votes.py`, run inside
`InProcessPipeline.run` BEFORE stage 2, grounding and the plan channel,
so all three consume the winning call only.

- **Calls.** With `prompt_permutation_votes: N > 1`, the SAME request is
  rendered under N cyclic shifts of its own presentation order: shift k
  = `base[k mod n:] + base[:k mod n]`.
  - Call 0 is the unshifted request, so its prompt is byte-identical to
    the single-call condition's.
  - Each call is a complete, ordinary `Reasoner.run`: its own attempts,
    re-asks and refusal/neutral-image mitigation, exactly the
    single-call policy (pinned per call).
- **Vote** on `(congestion_detected, type, strategy, yield_robot)`.
  Calls whose decision is None (exhausted or refused) abstain.
- **Tie rule (registered, as the brief states it):** among the keys tied
  for the most votes, the key voted by the call whose rendered order
  **matches the registry order** wins.
  - The registry order is M5's task-registry robot order: the
    `initial_tasks` order, restricted to the request's robots, with
    robots the registry does not name following in ascending id. It is
    passed as `InProcessPipeline(registry_order=…)`.
  - **Fallback**, to keep the rule total: if no tied call rendered the
    registry order, the earliest call wins. Call 0 is the episode's
    drawn order.
  - The record carries `registry_order` and `tie_resolved_by`
    (`registry_order` / `earliest_call` / null).
  - If every call abstains, the outcome is call 0's failure.
  - **Design gap (open item 2):** with three or more robots under a
    `random` or `id_desc` draw, the cyclic shifts of the drawn base need
    not include the registry order at all, e.g. id_desc (3, 2, 1) never
    rotates to (1, 2, 3). Every tie in such a cell resolves by the
    fallback, which is pinned by test.
- **Winner's response, whole.** `proposed_plan`, `reasoning`,
  `root_cause`, `justification`, `crossing_order` and `blocker_kind` are
  the winning call's own answer, never merged across calls (pinned).
- **Artifact.** A `permutation_votes` block records:
  - every call: index, shift, order, system/user SHA-256, vote, decision,
    raw text, diagnostics;
  - `vote_counts` with call indices;
  - `registry_order` and `tie_resolved_by`;
  - `winner_index`, `winner_vote`, `tie_broken`, `tie_rule`;
  - `distinct_orders`;
  - `total_backend_attempts`.

  The top-level `prompt` and `robot_presentation_order` are the
  **winner's**, so they match the stored decision and the replay
  integrity arm re-hashes the right prompt. Disagreement itself is
  scoreable from the block.
- **Not voted.** T0 probes (`analyze`) never vote.
- **Cost multiplier:** N× API calls (the realised count is
  `total_backend_attempts`). Worst-case wall time is
  N × `max_attempts` × `timeout_sec`, because calls run sequentially on
  the worker thread. At N = 3 with the shipped openai budget, that is up
  to 6 calls per decision.
- **Two-robot caveat (design-level, flagged).** Cyclic shifts of a
  two-robot scene wrap: three votes render [A, B], [B, A], [A, B], so
  `distinct_orders` = 2 and the base order is counted twice.
  - In the head-on cells, N = 3 therefore does NOT cancel the
    first-slot prior per decision. It biases the vote toward the drawn
    order 2:1.
  - Options for the owner: use N = 2 (both orders, tie → drawn order) or
    an even N for two-robot cells; or define the vote over distinct
    orders only. The current implementation records the wrap and
    implements the brief as written.

## Item 5 — Verifier-Candidate-Options Block (M3 → M5 → M2)

`reasoning/rag/command_grounder.py::derive_candidate_options`. **Never
hand-written:** each (robot, action) is offered iff `_plan_problems` —
the exact leg audit `verify_and_repair_plan` applies — flags nothing on
that robot's leg in a probe plan.

The audit is strategy-conditioned, because it takes a decision, and no
strategy-free per-robot answer exists in M3. Each action is therefore
probed under one registered context (an **open design item** for the
owner):

| Action | Probe context |
|---|---|
| `yield` | strategy `yield`, involved = [robot, nearest other robot], yield_robot = robot, legs [robot: yield, partner: cross] |
| `reverse` | if the scene declares junction arms and the all-robot `junction_clear` recede set is non-empty: strategy `junction_clear` over every robot, legs [robot: reverse]; else strategy `reverse`, both of the pair reversing |
| `cross` | offered iff some other robot's yield probe, with this robot as crosser, flags neither leg |
| `wait` / `reroute` | strategy `temporary_wait` / `reroute`, [robot: action, partner: wait] |

- `continue` is never listed: the plan grammar already states it as the
  "not part of the resolution" leg.
- `reverse` carries the declared arm as detail, e.g. "south arm".
- The gate mode, obstacles, geometry and grounding params are the ones
  the audit will verify this decision with.

Pinned outcomes:

- **Audit agreement.** Every offered single-leg option passes
  `_plan_problems` under its stated context: head-on and IB10, gate
  `swap`.
- **IB10 axis mirror.** `reverse` is offered **only to the N-S recede
  pair** (robot_3 "south arm", robot_4 "north arm"). The axis-mirror E-W
  reverse is never offered. This is the round-3 report's
  axis-mirror-to-discrete-choice conversion. Under the yield context the
  N-S pair is still offered `yield`, which the rule above implies.
- **Head-on with a west blocker under `swap`.** robot_1 (boxed in) is
  not offered `yield`, and robot_2 is not offered `cross`, since no
  feasible releasing yield exists. With the gate `off`, the boxed-in
  yield is offered, exactly like the audit.

**Prompt block** (v3; one framing sentence, then one line per robot in
the request's presentation order, so voting shifts rotate it too):

> Plan actions the system's verifier accepts for each robot in the current scene (a plan leg outside these is repaired or the plan is replaced):
> - robot_1: yield, wait
> - robot_2: reverse (south arm), wait

> **CONSTRUCT CHANGE — read before scoring.** With this flag on, the plan
> channel no longer measures free multi-robot planning. It measures
> **constrained selection** among verifier-accepted actions (the
> published per-leg *selection* recipe, not the unclaimed
> composition-from-marked-candidates gap). Plan-quality metrics (i-a)
> through (vi) under this condition are not comparable to free-planning
> cells. Every artifact records the condition in `prompt_conditions`:
> `candidate_options_requested`, the rendered `candidate_options`, and
> `construct_constrained_selection: true` exactly when the block was
> rendered. A probe-context change is a construct change too: re-pin and
> re-register.

---

## Pins

### Prompt (v3.2, `tests/unit/test_prompt_apparatus_v3.py`)

The six v3.2 pins in `test_prompt_builder_v3.py` are **untouched and
passing**, including baseline `c3fb9fcf…`. Each condition alone, on the
same `_request` fixture:

| Condition | Length | SHA-256 |
|---|---|---|
| metric_grid (0.5 m) | 6287 | `5e454e849ff85241f1357e63d22d0fdc77a6d2f37c4a0263dabc62f65d466ec5` |
| motion_trails | 6199 | `e8448cd34241c30dab4facb2bdd50b50dc7566e5aefd2c17647be5bbf5eba01b` |
| zoom_tile | 6248 | `edadb4292b42f19cd1d898938c02e609330ce520496659d2fd0748ef8762f54d` |
| candidate_options | 6233 | `bb8c8674f2b1df2a194b74a7640edd11b797acdb9f2d55fbfc952afcf53e9f8b` |
| all_on | 6878 | `fec35f089741f326767641973137fc7addd787b821973cd0ba52e0b3e23c5f23` |

Also pinned:

- Each condition only inserts text before the plan invitation.
- Each sentence renders exactly once.
- The text is scenario-agnostic: no `robot_`, `deadlock`, `junction`,
  `yield`, `head-on` or `aisle`.
- v1/v2 render neither the text nor the tile.

### Frame (`tests/unit/test_annotation_apparatus.py`)

- **Flag-off frame**, two pins:
  - The SHA-256 `079de2b7…` was recorded on the clean `aec58cc`
    baseline. It runs only on the recording build (OpenCV 5.0.0 /
    numpy 2.4.6), because anti-aliased output differs by build: the
    container's OpenCV 4.6.0 renders other bytes.
  - A build-independent equality with the verbatim pre-apparatus code
    path runs everywhere.
- **Flag-on frames** are pinned structurally, not by hash:
  - every robot footprint is pixel-identical to flag-off;
  - grid pixels change, as a blend and not opaque;
  - margin labels stay at the frame edges;
  - trails sit in the status colour and fade with age;
  - a stationary history draws nothing.

### Backends (`tests/unit/test_backend_multi_image.py`)

- openai messages flag-off: `ebbc3440…`. gemini body flag-off:
  `0daa73c6…`. Both match `aec58cc`.
- The order of the multi-image parts is pinned per backend.

---

## VM Verification Smoke

Coordinator-authorized addendum. Mock backend only, zero API spend. VM
`vgu-vgu-thule-base-isaac-workstation-vm`, container `vgu_ros`, scenario
`head_on_asymmetric_w0p2_eopen_bshort_o0` (bshort goals
robot_1 → (2.6, 0), robot_2 → (−1.5, 0)), seed 42, YAML
`duration_sec: 300` governs.

### Deploy and restore

1. **Deploy.** A full md5 manifest of the branch's 780 tracked files was
   compared with the VM tree: 44 mismatches. The VM held the
   `af7cec5`-era files plus the known pristine `orchestrator.yaml`.
   - The VM's originals of the 27 existing files were tarred to
     `/home/ubuntu/apparatus_predeploy_backup/`, and the 16 new files
     were listed.
   - The branch files were extracted with `--touch` (fresh mtimes).
     Afterwards the manifest showed only the pristine `orchestrator.yaml`
     mismatch.
2. **Build.** `swarm_perception` and `swarm_orchestrator` were rebuilt
   (merge-install). Every **installed** copy of every deployed package
   file was md5-verified equal to source, and the live-mounted
   `reasoning/` files match.
3. **In-container tests.** The apparatus test files ran in the container
   (OpenCV 4.6.0): 209 passed, 1 skipped.
   - The first in-container pass caught the build-dependence of the
     flag-off frame hash. It is now build-gated, with a build-independent
     reference-path test (`dc25824`).
4. **Runs.** Each run went through the new `scripts/vm/apparatus_smoke.sh`,
   which wraps `v2_final_run.sh` and so applies every standing trap:
   - the pristine-md5 gate;
   - the wait for `pgrep -f run_simulation` to be EMPTY (0 s both times;
     Isaac was confirmed gone between runs);
   - verbatim restore with a fresh mtime, plus installed-copy md5
     verification.

   M5 actually started in both runs (analyses and arrivals in `m5.log`),
   so the gate line is not the only evidence. With `ANNOTATION=1` the
   wrapper flips M1's `annotation.yaml` (installed md5 `4433257c…`
   verified before launch) and restores it afterwards.
5. **Restore, after both runs.**
   - `RESTORE OK` both times: `orchestrator.yaml` src = installed =
     `1f656533a30a35882d57d0d64a57bd0d`, `rag.yaml`
     `e18c723cff9cada3f320d564c2ecee5a`.
   - `ANNOTATION RESTORE OK` (`151574cb…` src = installed).
   - The pre-deploy tree was then restored: the 27 originals were
     re-extracted with `--touch` and byte-compared OK against the backup,
     and the 16 new files were removed.
   - Both packages were rebuilt, the installed copies were md5-verified
     equal to source, and the stale installed new files were removed.
   - Imports OK. The manifest compare is back to the same 44 pre-deploy
     mismatches.
   - No Isaac process remains; the GPU is idle (0 %, 171 MiB). The VM is
     still RUNNING (bills while running).

Run bundles (gitignored, main checkout):
`data/logs/vm_runs/apparatus_smoke/{annot_r1,votes_r1}/`. Evidence PNGs:
`data/logs/vm_runs/apparatus_smoke/evidence/01–07_*.png`.

### Run 1: `annot_r1` (grid + trails + zoom tile, `fc_run_20261003_204630`)

**Setup.** Overlay `apparatus_annotation`: plan channel on (prompt v3),
`prompt_metric_grid`, `prompt_motion_trails`, `prompt_zoom_tile`,
`keep_debug_frames` and `keep_raw_frames`. M1 had `metric_grid: true`
and `motion_trails: true`. The mock was
`head_on_yield_robot_2_plan_once.json`. Annotated and raw snapshots were
taken every 4 sim-s (72 + 71 PNGs).

**Outcome.** The jam formed, the trigger decision dispatched `yield`
robot_2 (plan `vlm_verbatim`), robot_1 arrived (0.10 m), and robot_2
arrived (0.08 m). There were six analyses; every one has
`prompt_conditions` grid / trails `requested = m1_drawn = stated = true`
and a tile `attached: true`.

- **Grid: PASS.** The frame was verified at real resolution (1280×960,
  evidence 01 and 03).
  - Thin, low-contrast lines; margin letters A–L and numbers 2–9 are
    legible. Rows 1 and 10 are slivers and unlabeled, as designed.
  - No label touches the floor.
  - The lines break around every robot (footprint mask): no marker or
    robot body is crossed (evidence 01, 06).
- **Occlusion: none.** The jam crop (evidence 06, raw | annotated) shows
  no overlay pixel on either marker.
- **M1 freshness.** This is a sanity check, not occlusion evidence:
  detection runs before annotation. Scene log, 666 rows:
  - robot_1: 0 STALE.
  - robot_2: 9 STALE rows (1.4 %), one streak of 9, at sim 24.0–27.0 s.
    The pair's separation there was **0.149 m**: the two markers
    physically touch in the RAW frame (evidence 06, left). This is the
    known overlapping-marker STALE band.
  - Comparators: the flag-off funded A1 run of the same cell (closest
    approach 0.263 m) had 2 STALE rows. The flag-off `votes_r1` (closest
    0.222 m) had 0.
  - The jam simply formed closer this run (minimum 0.141 m). Since
    overlays are drawn after detection on a copy, they cannot cause it.
- **Trails: draw correctly.**
  - Approach (evidence 03 and 04 top): fading green polylines behind
    both moving robots, faint end oldest.
  - While stopped (04, t = 43 and 55 s): no trail, as specified.
  - Backup phase (05): a faint trail behind robot_2.
  - They are legible but faint at 0.1 m/s; see open item 5. Not a FAIL:
    no cosmetic change was made.
- **Zoom tile: PASS.**
  - Trigger tile (evidence 02): `crop_px` [444, 350, 811, 625] (367×275,
    4:3), `world_bounds_m` = robot_1 (−0.05, −0.03) ± 0.6 m.
  - Every other analysis's tile is centred on robot_2 (evidence 07).
  - All are 640×480 and show the same annotation and grid.
  - The rendered v3 prompt carries the three sentences verbatim.

### Run 2: `votes_r1` (`prompt_permutation_votes: 3`, `fc_run_20261003_210400`)

**Setup.** Overlay `apparatus_votes` (plan channel off, so prompt v2 and
votes only). The scripted mock was `head_on_permutation_votes_once.json`:
call 0 says robot_1 yields (the minority), calls 1 and 2 say robot_2
yields, then the scene is clear.

**Outcome.**

- The trigger analysis made **3 calls**. The majority went to call 1
  (no tie), M5 dispatched `yield` robot_2 (the winning call), M4 ran it
  to COMPLETED, and both robots arrived (0.13 m, 0.08 m).
- The four later re-checks each voted 3 × none (winner 0).

Artifact excerpt (`decisions/484af59e….json`, `permutation_votes`):

```text
votes_requested=3 distinct_orders=2 winner_index=1 tie_broken=False
tie_rule=earliest_call_first:call_0_is_the_episode_drawn_order total_backend_attempts=3
(the VM ran the pre-`registry_order` tie code; no tie occurred, so the outcome is unaffected)
call 0 shift 0 order [robot_1, robot_2] user_sha256 e4ea7a476a4c… vote yield/robot_1
call 1 shift 1 order [robot_2, robot_1] user_sha256 c3599e5007ce… vote yield/robot_2
call 2 shift 0 order [robot_1, robot_2] user_sha256 e4ea7a476a4c… vote yield/robot_2
vote_counts: yield/robot_2 x2 (calls 1, 2); yield/robot_1 x1 (call 0)
top-level robot_presentation_order=[robot_2, robot_1], prompt.user_sha256 = call 1's (re-hash OK)
decision.justification = call 1's ("…call 1: robot_2 yields (the majority answer).")
```

- Per-call prompt hashes are recorded, and the order draws are those of
  the registered cyclic shift.
- **On a two-robot scene only two orders are distinct.** Call 2 repeats
  call 0's order and prompt hash byte for byte. This is the open item 1
  wrap, now observed live; the coordinator's "distinct order draws"
  criterion cannot hold at N = 3 with two robots.
- M1 freshness with overlays off: 0 STALE for either robot (649 rows).

### Coordinator criteria, met / not met

| Criterion | Status |
|---|---|
| Grid renders recessively and legibly at real resolution | **Met** (evidence 01, 03) |
| Grid occludes no marker or robot | **Met** (footprint mask; evidence 01, 06) |
| M1 detection stays 100 % fresh under the overlays | **Not met as stated.** robot_2 had 9 STALE rows (1.4 %), all at a 0.149 m separation where the markers physically overlap in the RAW frame (evidence 06). Detection runs before annotation, so the overlays cannot cause it; the flag-off comparator jams formed farther apart (0.263 m, 0.222 m). |
| Trails draw correctly for moving robots | **Met**, faint at backup speed (open item 5) |
| Zoom tile generated with correct crop bounds | **Met** (crop_px / world_bounds recorded; evidence 02, 07) |
| Three calls per analysis in `permutation_votes`, per-call prompt hashes | **Met** |
| Distinct order draws | **Not met: inherent.** With two robots and N = 3, calls 0 and 2 render the same order and prompt hash (open item 1). |
| Majority vote resolves per the tie rule | Majority **met** live (2-1, winner call 1). The **tie path was not exercised live** (no tie occurred); it is covered by unit tests only. |
| Dispatched decision matches the winning call | **Met** (yield robot_2 dispatched and COMPLETED) |

---

## Open Items for the Coordinator

1. **Two-robot vote wrap** (Item 4). Choose N = 2, an even N, or
   distinct-order voting for two-robot cells, or accept the 2:1
   drawn-order weight. Observed live in `votes_r1`.
2. **Tie rule vs. the drawn order** (Item 4). Ties go to the call
   rendering the registry order, per the brief. But cyclic shifts of a
   `random`/`id_desc` base may never render that order, and then the
   earliest-call fallback decides. If the intent is "ties go to the
   registry order whenever possible", the shift set would have to include
   it: an owner design call.
3. **Candidate-options probe contexts** (Item 5). Ratify the per-action
   context table, especially `reverse` under `junction_clear` when arms
   are declared.
4. **Zoom framing set.** The tile frames the robots the analysis was
   *triggered for*: M5's stall-detector set, which in both VM runs was a
   single robot per analysis.
   - At the head-on trigger that was robot_1 alone. robot_2, 0.13 m away,
     was inside the 0.6 m margin and fully in the tile.
   - A partner farther than the margin would fall outside it.
   - Framing over every robot within some radius, or scene-wide, is a
     one-line change if preferred.
5. **Trail legibility at backup speed.** Trails render correctly but
   faintly at the head-on's 0.1 m/s.
   - The 0.20 m footprint mask consumes about 2 s of a 3 s window.
   - A reversing robot's trail lies on the same side as M1's heading
     arrow. That arrow is pre-existing M1 behaviour: it follows theta,
     not the motion direction.
   - A longer window (e.g. 6 s) would lengthen the visible trail. It is a
     registered parameter, not a cosmetic tweak, so it was left at 3.0 s
     for a ruling.
6. **Grid during probes.** If the grid is ever on during T0 probe
   collection, the frozen v2 probe prompt does not state it while the
   image carries it. The record is per artifact, but it is a confound to
   rule on.
