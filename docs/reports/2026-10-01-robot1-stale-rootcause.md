# M1 Root-Cause — robot_1 / (-1.75, 0) STALE Dropout at the IB10 Spawn

**Prepared:** 2026-10-01

**Revision history:**

- Initial draft: root-causes the "registered risk" flagged in
  `docs/reports/2026-10-01-m1-y-extent-verification.md` (robot_1, marker_id
  1, STALE 74.0%/82.1% across two replicated runs at `(x, y) = (-1.75, 0)`,
  the exact spawn of `isaac/config/scenarios/intersection_bottleneck.yaml`'s
  robot_1) before v2 build-order step 6 (IB10 composite mock smoke,
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`).
- Rev 2 (2026-10-01): added a fourth probe (`yieldpark`) after review caught
  a gap — the original scope section only checked robot_1's transient
  pre-departure dwell and its goal arrival, not the much longer dwell it
  gets if chosen as the single-yield junction yielder. Corrected two
  over-claims (the marker footprint is not position-dependent; yaw was not
  actually varied for marker 1 at the failing position) and added the
  `position-verified` scoring source and the arrival-yaw structural
  guarantee, both previously assumed rather than cited.
- Rev 3 (2026-10-01): a second review pass found the first `position-
  verified` citation (`congestion_detector.py`) was the wrong file — it is
  M5's live stall trigger, not the arrival scorer. Replaced with the actual
  implementation (`swarm_orchestrator/arrival.py::classify_arrival`/
  `ArrivalGate`), and added the distinction between that live, stale-
  tolerant online gate (what any future IB10 run is actually scored by) and
  `scripts/rescore_arrivals.py`'s stricter, legacy-only offline rescorer
  (pre-dates the online gate, not used on new runs). Softened "confirmed
  clean"/"neighborhood" language to per-pose claims, since the mechanism is
  a sub-pixel-phase effect with no established "neighborhood" of safety,
  and flagged that the v2 composite `junction_clear` command step 6 is
  meant to test does not exist in code yet, so the single-yield geometry
  this task verified does not necessarily cover it. Recommendation changed
  from "accept as-is, well-supported" to "instrument by default".

**commit:** `3f24ac9` (swap + nudge probes), `f155d7a` (goalpose probe),
`82ae057` (initial report), `5c7b833` (yieldpark probe), `4edd4c8` (rev 2),
`173d036` (rev 3 draft), branch `feat/v2-stale-rootcause`

---

## Purpose

`docs/reports/2026-10-01-m1-y-extent-verification.md` found, and replicated,
a severe M1 tracking dropout specific to one (position, marker) pair:
robot_1 (marker_id 1) spent 74.0% and 82.1% of two independent 120 s
stationary holds `STALE` at `(x, y) = (-1.75, 0)` (53- and 51-row streaks,
~20 s max carried-forward age), while the mirror point robot_2 (marker_id 2)
at `(+1.75, 0)` was 100% fresh both times, and robot_1 itself was 100% fresh
at a different `x` (`-2.4`). That report left the finding un-root-caused and
flagged it as a build-order item before IB10's composite mock smoke (step
6), since IB10's robot_1 spawns at exactly that pose. This report finds the
mechanism, measures its real scope against IB10, and states why no fix is
applied to `intersection_bottleneck.yaml` or to M1 code.

---

## Method

Four short mock-backend VM runs (`BACKEND_ID=mock`, zero VLM calls —
confirmed below), each holding all four robots **stationary** for 120 sim-s
(same mechanism as the y-extent probe: `orchestrator.yaml`'s `initial_tasks`
rewritten to a 100000 s `start_delay_sec` hold, restored byte-for-byte on
exit), on the standing VM (`vgu-vgu-thule-base-isaac-workstation-vm`,
container `vgu_ros`):

- `isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml` — **swap
  probe**. `ScenarioConfig`'s own validator
  (`isaac/vgu_sim/config.py:590-594`) requires `robot_N` to carry
  `marker_id=N`, so marker identity cannot be reassigned independently of
  `robot_id`; the discriminator is instead to swap which *position* robot_1
  and robot_2 spawn at. robot_1 (marker 1) moves to the previously-clean
  mirror point `(+1.75, 0, yaw=pi)`; robot_2 (marker 2) moves to the
  previously-failing `(-1.75, 0, yaw=0)`. robot_3/robot_4 stay at the
  already-verified `y = -1.2`/`+1.2` as an in-run sanity control.
- `isaac/config/scenarios/m1_stale_rootcause_probe_nudge.yaml` — **nudge
  probe**. robot_1 (marker 1) moves 0.10 m off the failing x, to `-1.65`;
  robot_2 (marker 2) gets a bonus far-side nudge to `+1.85`. Tests the
  cheapest candidate fix directly.
- `isaac/config/scenarios/m1_stale_rootcause_probe_goalpose.yaml` — **goal-
  pose probe**, added after the first two runs (see "Closing the yaw gap"
  below). All four robots held at their actual `intersection_bottleneck.yaml`
  GOAL positions, all at `yaw = 0` — the real Nav2 arrival orientation.
- `isaac/config/scenarios/m1_stale_rootcause_probe_yieldpark.yaml` —
  **yield-park probe**, added after review of the first three runs (see
  "Closing the yield-park gap" below). robot_1 and robot_2 held at the real
  pose a single-yield junction yielder parks at, computed directly from the
  project's own grounding code rather than assumed.

All four scenarios built, validated (`validate_simulation.py`: `PASS` on
every USD) and run through `scripts/vm/fc_launch.sh` via a new driver,
`scripts/vm/m1_stale_rootcause_probe.sh` (modeled on, but kept separate
from, `scripts/vm/m1_y_extent_probe.sh`). `orchestrator.yaml` was restored
and verified pristine (md5 `1f656533a30a35882d57d0d64a57bd0d`, both source
and installed copies) after every run. Detection scored the same way as the
y-extent report, via `scripts/m1_y_extent_probe_analysis.py` against each
run's own `scenario.yaml` spawns and `gt/ground_truth.jsonl`.

**Zero VLM spend, all four runs:** `data/logs/m5_decisions/` carried the
same file count (2177) and newest file (`b14c2237...`, dated before this
task) before and after every run — the held-stationary robots never got
close enough, or stalled with a goal, to trip the congestion detector.

---

## Results

| Run | Robot (marker) | Spawn (x, y, yaw) | fresh_rate | exact_stamp_match | max_age (s) | longest STALE streak |
|---|---|---|---|---|---|---|
| swap | robot_1 (1) | `(1.75, 0, pi)` | 100% | 93.15% | 0.8 | 0 |
| swap | robot_2 (2) | `(-1.75, 0, 0)` | 95.55% | 73.63% | 3.133 | 7 |
| swap | robot_3 (3) | `(0, -1.2, pi/2)` | 100% | 100% | 0.0 | 0 |
| swap | robot_4 (4) | `(0, 1.2, -pi/2)` | 100% | 100% | 0.0 | 0 |
| nudge | robot_1 (1) | `(-1.65, 0, 0)` | 100% | 100% | 0.0 | 0 |
| nudge | robot_2 (2) | `(1.85, 0, pi)` | 100% | 100% | 0.0 | 0 |
| nudge | robot_3 (3) | `(0, -1.2, pi/2)` | 100% | 100% | 0.0 | 0 |
| nudge | robot_4 (4) | `(0, 1.2, -pi/2)` | 100% | 100% | 0.0 | 0 |
| goalpose | robot_1 (1) | `(1.75, 0, 0)` | 100% | 100% | 0.0 | 0 |
| goalpose | robot_2 (2) | `(-1.75, 0, 0)` | 96.63% | 70.03% | 2.633 | 5 |
| goalpose | robot_3 (3) | `(0, 1.75, 0)` | 100% | 100% | 0.0 | 0 |
| goalpose | robot_4 (4) | `(0, -1.75, 0)` | 100% | 93.27% | 0.367 | 0 |
| yieldpark | robot_1 (1) | `(-1.37, 0.359, 0)` | 100% | 97.87% | 0.067 | 0 |
| yieldpark | robot_2 (2) | `(1.481, -0.344, pi)` | 100% | 100% | 0.0 | 0 |
| yieldpark | robot_3 (3) | `(0, -1.2, pi/2)` | 100% | 100% | 0.0 | 0 |
| yieldpark | robot_4 (4) | `(0, 1.2, -pi/2)` | 100% | 100% | 0.0 | 0 |

GT cross-check (all four runs): every robot stayed within `0.0001`-`0.0003`
m of its authored spawn for the whole episode (stationary premise holds),
and `min_pairwise_distance_m` stayed at `1.61`-`2.47` m throughout every run
— far beyond any marker-overlap range, ruling out the overlapping-marker
`STALE` mechanism (hypothesis 5) directly from this task's own GT, same as
the y-extent report's run.

---

## Mechanism

Five hypotheses were in play. Static scene inspection ruled out three
before any VM time was spent, and the swap/nudge/goalpose/yieldpark runs
resolved the rest:

1. **Static occlusion/prop or lighting asymmetry — ruled out by scene
   inspection, not a VM run.** `isaac/vgu_sim/warehouse_builder.py`'s
   `_build_rack_blocks` places four identical, symmetric rack quadrants
   starting only where `|x| >= 0.6 AND |y| >= 0.6`; the full E-W corridor
   (`|y| < 0.6`, including `x = -1.75`) is open floor for its entire length,
   confirmed by `intersection_bottleneck.yaml`'s own header ("No
   aisle_barrier... No obstacles"). The overhead camera
   (`isaac/vgu_sim/config.py` `CameraConfig`) is nadir, identity-orientation,
   centered at the origin — geometrically symmetric E-W. Markers are
   authored fully **emissive**
   (`isaac/vgu_sim/marker_asset.py:_bind_emissive_texture`,
   `diffuseColor=(0,0,0)`, `emissiveColor` driven by the texture), so scene
   lighting (a single uniform dome light,
   `isaac/vgu_sim/runner.py:_add_scene_lighting`) cannot shade them
   unevenly even if geometry were asymmetric. There is no occluder and no
   shading mechanism available to explain a position-specific effect here.
2. **Homography/undistortion local degradation — ruled out, same as the
   y-extent report.** The mirror point `(+1.75, 0)` is clean in every run
   that tests it with marker 1 (swap: 100%/93.15%; goalpose: 100%/100%).
3. **Overlapping-marker STALE (2026-07 mechanism) — ruled out.** GT
   `min_pairwise_distance_m` stayed 1.61-2.47 m in every run here (and
   2.122 m in the original y-extent runs).
4. **Marker-identity vs. position, resolved by direct test.** The **swap
   run** shows the catastrophic failure does **not** travel with marker 1:
   at its new position `(+1.75, 0)`, marker 1 is clean (100% fresh, 93.15%
   exact-stamp). It also does **not** stay at the position regardless of
   marker: marker 2 at `(-1.75, 0)` shows only mild, scattered degradation
   (95.55% fresh, 7-row max streak) — nowhere near marker 1's historical
   74-82% `STALE` rate there. The **goalpose run** independently replicates
   this exact split at `(1.75, 0, yaw 0)` for marker 1 (100%/100%) and
   `(-1.75, 0, yaw 0)` for marker 2 (96.63%/70.03%, 5-row streak). Note what
   this does and does not establish on yaw: marker 2 was tested at
   `(-1.75, 0, yaw 0)` in *both* the swap and goalpose runs (the same yaw
   both times, not two different ones), and marker 1 has only ever been
   tested at the failing position `(-1.75, 0)` at `yaw 0` (the original
   y-extent runs). Yaw as a possible factor there is untested, not ruled
   out — it does not change the IB10 conclusion, since `yaw = 0` is the
   only orientation robot_1 is ever structurally given at that position
   (see "Closing the yaw gap" below), but the claim is narrower than "yaw
   is ruled out". **The severe failure needs both the specific
   marker_id=1 bit pattern and the specific position `x ~= -1.75`
   together** — neither alone reproduces it.
5. **A real, generic background marginality exists underneath it, measured
   directly — but it is not position-localized.** Every run shows some
   exact-stamp-match degradation even when `fresh_rate` stays 100%:
   `93.15%` at `(1.75, 0)`, `93.27%` at `(0, -1.75)`, `97.87%` at
   `(-1.37, 0.359)`, `87.7%-92.4%` at `(1.75, 0)` in the original y-extent
   study — and `100%` exact-stamp-match at `(0, -1.2)`/`(0, 1.2)` (this
   study's own robot_3/robot_4 controls, every run) and at `(-2.4, 0)`
   (robot_1 itself, the original y-extent study's run B). This noise is
   **not** a function of distance from the camera centre: the camera is
   nadir and `aruco.yaml`'s homography is pure scale-plus-offset with no
   perspective term (confirmed by the intrinsics/homography values
   themselves), so the marker's rendered pixel footprint is identical at
   `x = 0`, `x = 1.2`, `x = 1.75`, and `x = 2.4` alike — a
   uniformly small footprint cannot by itself explain *why* a given
   position is worse than its neighbor. What varies with position instead
   is the **sub-pixel sampling phase**: at this footprint, a small shift in
   world x shifts exactly where cell boundaries land on the camera's pixel
   grid, and decode success is sensitive to that phase. Degradation shows
   up at some poses near radius 1.75-1.8 and not at others (`1.2`, `1.65`,
   `1.85`, `2.0`, `2.4` were all clean or near-clean in this study and the
   y-extent study) — a phase effect, not a radial band.

**Where the marginality comes from (inferred from the asset's own pixel
geometry and OpenCV's documented defaults — no debug frames were captured
on these runs, so this is not confirmed against rendered output).**
`isaac/vgu_sim/marker_asset.py`'s `MARKER_SIZE_M = 0.12` quad carries
`aruco.yaml`'s `marker_size_m` texture at `640x640` px; the black 6x6 ArUco
cell (border + 4x4 data) occupies the center `512/640 = 80%` of that
texture (measured directly: `cv2.imread` + threshold on
`isaac/assets/markers/aruco_4x4_50/marker_1.png`), i.e. `0.096` m physical.
`aruco.yaml`'s homography gives `0.0043583` m/pixel at the overhead camera's
resolution (uniformly, per the point above), so the full marker quad
projects to `27.5` camera px and the black 6x6 cell to `22.0` px —
**`3.67` px per ArUco cell**, everywhere in frame. OpenCV's
`cv2.aruco.DetectorParameters()` default `perspectiveRemovePixelPerCell` is
`4` (confirmed by direct inspection of the installed
`opencv-contrib-python` in this task's environment): the marker's rendered
footprint is comparable to, not comfortably above, OpenCV's own default
per-cell resample grid. A footprint this close to the resample resolution
makes decode outcomes sensitive to exactly where cell boundaries fall
against the pixel grid — i.e. to sub-pixel phase — everywhere in frame; it
is this phase sensitivity, not the footprint size itself, that is
position-dependent. Which specific marker IDs tip from "a few percent of
frames" to "74-82% chronically STALE" at which specific phase is then a
function of that ID's exact bit pattern interacting with
`errorCorrectionRate=0.6` nearest-dictionary-entry matching at that phase —
a renderer/decode-level interaction, observed here only through its effect
on `STALE` rates, not confirmed against captured frames. This interaction
is also **not** symmetric in the one place it could be checked directly:
`-1.75` (yaw 0) is markedly worse for both tested markers than `+1.75` is
for marker 1, despite the camera, homography and rack layout all being
structurally symmetric — an unexplained renderer-level asymmetry, reported
as an open detail rather than resolved.

No config-exposed ArUco detection parameter exists to tune this today:
`perception_node.py` never declares or wires a `detector_params` ROS
parameter into `process_frame` (`detection.py`'s `detect_aruco_markers`
always receives `detector_params=None`, i.e. OpenCV stock defaults), and
`aruco.yaml`'s `min_detection_confidence` is dead — not read anywhere in
`perception_node.py`/`pipeline.py` (confirmed by grep; its only other
occurrences are test-mock function signatures in `test_perception.py` /
`test_isaac_calibration.py`). **Any detector-parameter tuning (e.g.
`cornerRefinementMethod`, `perspectiveRemovePixelPerCell`,
`errorCorrectionRate`) would require adding new wiring to
`perception_node.py`/`pipeline.py` — M1 code, v1-frozen.**

---

## Closing the yaw gap (goalpose run)

The swap run alone left a gap: it tested marker 1 at `(+1.75, 0, yaw=pi)`,
not at `(+1.75, 0, yaw=0)` — robot_1's *actual* IB10 goal orientation.
This is structurally guaranteed, not just the observed default: M5's base-
mission goal type, `TaskAssignment.goal` (`swarm_orchestrator/models.py:47`),
is typed `tuple[float, float]` — it has no yaw field at all — and
`command_bus_node.py`'s dispatch (`yaw = goal.get("yaw", 0.0) if
isinstance(goal, dict) else 0.0`) falls back to `0.0` for exactly this
shape. `intersection_bottleneck.yaml`'s `cross_intersection` goals are
plain `[x, y]` lists (`orchestrator.yaml`'s own documented example:
`robot_2: { ..., goal: [-1.75, 0.0] }`), so every robot's Nav2 arrival yaw
is `0`, never its spawn yaw. The N-S arrival poses `(0, +-1.75, yaw=0)`
were never tested at that yaw either. The goalpose run closes this gap
directly.

## Closing the yield-park gap (yieldpark run)

The first three runs characterized robot_1's *transient* pre-departure
spawn dwell and its *goal* arrival, but missed a third, longer dwell:
if robot_1 is chosen as the composite command's single-yield **yielder**,
it backs up and parks for the whole maneuver (tens of seconds), not a
transient window. `intersection_bottleneck.yaml`'s own header notes "the
1.7 m backup clearance binds, parking a north-south yielder at
`|y| ~= 1.70-1.72`" — close enough to the failing `-1.75` that this needed
checking directly rather than assumed benign or assumed dangerous either
way. That number is specific to the **north-south** yielder, though: the
backup distance (`reasoning/rag/maneuver_geometry.py:derive_backup_distance`)
is computed per-yielder from its own real-time offsets to the crossing
robots, not a fixed geometric constant shared across axes, so it does not
by itself establish where an **east-west** yielder (robot_1) parks.

Computed directly from the project's own pinned grounding code
(`tests/unit/test_intersection_bottleneck_scenario.py`'s existing
`_frames()`/`_ground()` helpers, run locally — not a new test, the existing
pinned coverage already includes `robot_1` as yielder) against both the
synthetic standoff cases and the real IB10 ground-truth standoff frame
(`IB10_STANDOFF`, from the smoke run `INTERSECTION_SMOKE_SUMMARY.txt`),
robot_1's park pose as the E-W yielder is:

| Case | retreat (x, y) |
|---|---|
| standoff 0.3 m | `(-1.40, 0.36)` |
| standoff 0.4 m | `(-1.30, 0.36)` |
| standoff 0.5 m | `(-1.20, 0.36)` |
| real IB10 standoff | `(-1.37, 0.359)` |

None of these are anywhere near `-1.75` — and the pull-off sidestep also
moves the park point off the `y = 0` centreline (`y ~= 0.36`), a third
variable neither the spawn nor the goal pose had varied. The yieldpark
probe holds robot_1 at the real-IB10-standoff pose `(-1.37, 0.359, yaw=0)`
directly (yaw 0: backing up does not rotate the robot, and robot_1's
approach heading toward its `+x` goal is already `0`), plus robot_2 at its
own computed park pose `(1.481, -0.344, yaw=pi)` as a bonus check. Result:
**100% fresh, 97.87% exact-stamp-match, 0 `STALE`** for robot_1 — clean at
that pose.

---

## Scope against IB10

The registered risk worried about two IB10-scored consumers of M1 state:
the "all four robots reach goals, position-verified" resolution criterion
(`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "(a)" > "Scoring"),
and Arm B's shadow classification. "Position-verified" has a precise,
already-implemented meaning in this codebase, found by tracing the term
rather than assumed, and there are two distinct implementations with
**different** `STALE`-handling that must not be conflated:

- **The live, online gate — the one that governs every current and future
  run, including IB10's step 6** — is `swarm_orchestrator/arrival.py::
  ArrivalGate`/`classify_arrival`, which gates M4's relayed Nav2 "Goal
  succeeded" report against M1's own position estimate (module docstring:
  "a Nav2 false success cannot become a false episode success"; shipped
  active, `orchestrator.yaml`: `arrival_position_check: true`). This gate
  is **stale-tolerant by design**: a stale or missing M1 estimate is
  accepted, not rejected (`reason="stale_estimate"`, `accepted=True`, and
  `on_nav2_success` calls `mark_arrived` on any `accepted` verdict,
  stale included — "an M1 outage must not block every arrival in a run, it
  only means the arrival is unverified"). A fresh M1 reading that is
  `beyond_tolerance` is the only way this gate rejects an arrival; this
  study's measured bias on fresh reads is a few millimetres everywhere,
  nowhere near a tolerance-breaking error.
- **A separate, offline rescorer, `scripts/rescore_arrivals.py`, is
  stricter — but it only re-scores runs recorded *before* the online gate
  existed** (its own docstring: runs predating commit `4f39899`), using
  ground truth as an independent cross-check column, not the primary
  scoring input. Its own `robot_arrived_m1`/`run_both_arrived_m1` columns
  credit only `reason == "within_tolerance"`, explicitly passing over a
  `stale_estimate` verdict as "not evidence either way" — stricter than the
  online gate, but **not the mechanism any future IB10 run would be scored
  by**, since it is a legacy-data tool, not referenced anywhere in the v2
  design spec or the orchestrator config. Its "latched at goal" fallback
  (for a robot held by an M4 safety latch that never gets an explicit
  Nav2-success line, requiring the robot's *final* scene-log sample to be
  fresh enough) is the one place a `STALE` read costs a credit in *that*
  tool specifically.

So for IB10's actual future step-6 run, the operative mechanism is the
online gate, and it is stale-tolerant: this dropout is not the scoring
hazard the original registered risk implied for the primary
arrival-acceptance path. The residual risk is Arm B's own sampling (not
traced to its exact mechanism in this task) and, if this project's
scoring pipeline ever revives an offline re-score step for new runs too
(not established here either way), the stricter `within_tolerance`-only
rule that step would apply.

With that correction, the four runs above describe each pose directly —
each result is a single tested point, not a claim about a continuous
"clean neighborhood" around it, since the mechanism (Mechanism point 5
above) is a sub-pixel-phase effect, not a radius-based one:

- **robot_1 at its own IB10 goal pose, `(1.75, 0, yaw=0)`: clean at that
  pose** (100% fresh, 100% exact-stamp-match, 0 `STALE`, in both the swap
  run at a different yaw and the goalpose run at the real arrival yaw).
- **robot_1 at the single-yield yielder's park pose, `(-1.37, 0.359,
  yaw=0)`: clean at that pose** (100% fresh, 97.87% exact-stamp-match, 0
  `STALE` — the yieldpark run). This covers the fallback single-yield
  grounding path that exists in code today
  (`reasoning/rag/maneuver_geometry.py`); the v2 composite `junction_clear`
  command the prereg-v2 spec describes for IB10's actual step-6 smoke does
  not exist in this codebase yet (`grep -rl junction_clear reasoning/
  ros2_ws/src` finds nothing), so its own recede-phase geometry — which
  may put the E-W pair somewhere other than this single-yield park point —
  is **not** covered by this probe and cannot be until that command is
  built.
- **robot_2 at its own IB10 goal pose, `(-1.75, 0, yaw=0)` — the position
  that broke marker 1: mild, generic degradation at that pose** (95.6%/96.6%
  fresh across the two runs that test it, 70-74% exact-stamp-match, longest
  streak 5-7 rows ~ 5-7 s), the same order of magnitude as the background
  noise floor measured at other markers/positions in this study and the
  prior y-extent report.
- **robot_3/robot_4 at their own IB10 goal poses, `(0, +-1.75, yaw=0)`:
  clean at those poses** (100% fresh both; exact-stamp-match 100%/93.27%,
  in line with the background floor).
- **The catastrophic 74-82% `STALE` failure has only ever been observed at
  one pose: robot_1 sitting still at its own IB10 *spawn*,
  `(-1.75, 0, yaw=0)`.** In the real IB10 run robot_1 is stationary there
  only during the M5/Nav2 bring-up window (~10.6 sim-s per the scenario
  header) before `cross_intersection` dispatches its goal. Given
  `classify_arrival`'s stale-tolerant design, this window is unlikely to
  cost the primary position-verified arrival credit directly; it remains a
  live question for the narrower latched-at-goal path and for Arm B's own
  sampling — neither traced to a conclusive answer in this task.

---

## Fix: not applied

A 0.10 m spawn nudge (`-1.75` to `-1.65`) **fully clears** the failure in
isolation (nudge run: 100% fresh, 100% exact-stamp-match, 0 `STALE`, 293/293
rows) and was the task's own suggested candidate. It is **not** applied to
`intersection_bottleneck.yaml`, for reasons distinct from (and in addition
to) the general "tests/pins" caveat the task anticipated:

- **It is a scenario-geometry redesign, not a parameter tweak.**
  `tests/unit/test_intersection_bottleneck_scenario.py:183-185`
  (`test_approach_radii_are_equal`) pins all four approach radii to exactly
  `{1.75}`; moving only robot_1's spawn breaks that invariant, and the
  scenario's own header explains *why* the invariant exists ("all four
  approach radii are equal, so the robots reach the centre together" —
  otherwise the N-S pair stalls before the E-W pair arrives, changing a
  four-way intersection into a two-robot head-on). Equal radii also feed
  already-derived downstream geometry (the M3 park offset of `1.018` m and
  the `1.7` m backup clearance that parks a yielder at `|y| ~= 1.70-1.72`).
  Fixing the pin without re-deriving that chain is not unambiguous; updating
  it to match requires the scenario-design judgment call this task is not
  positioned to make unilaterally.
- **`intersection_bottleneck.yaml` is already flagged "NOT tag-ready,
  re-authoring needed"** (its own header, 2026-09-29) — this nudge decision
  belongs with whoever re-authors it, alongside the live open question of
  how the composite command's yield/backup geometry interacts with any
  changed spawn radius.
- **The Scope section above found the practical risk narrower, and
  differently shaped, than the nudge would fix anyway.** The nudge fixes
  robot_1's *spawn*; the two longer-duration poses tested (robot_1's own
  goal arrival, and the single-yield park point) are clean at the specific
  points tested, and `classify_arrival`'s own stale-tolerant design means a
  `STALE` read at the primary arrival-acceptance gate does not cost a
  credit the way the original registered risk assumed. The real remaining
  exposure (the narrower latched-at-goal path, Arm B's sampling, and the
  not-yet-built composite command's own geometry) is not something a
  spawn-position nudge is known to fix, since none of it was shown to need
  fixing in the first place — see Recommendation below.
- **Swapping the E-W roles instead (robot_1 spawns east, robot_2 spawns
  west) does not avoid this for free.** It keeps the approach radii equal
  (passes the pin) and might look like a cost-free fix, but robot_1 (the
  marker that actually fails) would then be the one arriving at
  `(-1.75, 0, yaw=0)` — the original failing pose, since Nav2 arrival yaw
  is always `0` regardless of which side a robot starts on (see "Closing
  the yaw gap"). This data already rules that option out; it is not a
  free lunch for whoever re-authors IB10.

This is the same STOP-after-diagnosis posture the task specifies for an M1
code change, applied here to a shared, already-flagged-for-redesign
scenario file with a pinned geometry invariant, for the same reason: an
ambiguous, multi-consumer change needs the owning design review, not a
unilateral edit during a tracking diagnosis.

No M1 perception code was changed or is recommended for change in this
task. The missing config knob (`detector_params` wiring, a real
`min_detection_confidence`) is recorded above for whoever picks up that
work; it is out of scope here since it touches `perception_node.py`/
`pipeline.py`.

---

## Recommendation for the step-6 owner

The mechanism is a sub-pixel-phase effect (Mechanism point 5), not a
radius-based one, and the v2 composite `junction_clear` command step 6
actually needs to smoke-test does not exist in code yet — its own
recede-phase geometry for the E-W pair is unknown and unverifiable until
it is built. Both facts argue against treating any one computed pose
(including the single-yield park point this task verified clean) as a
durable guarantee for every pose the eventual composite command will use.
**Recommendation: option 3 is the default; options 1 and 2 are not ruled
out but need more than this task established before being safe to pick.**

1. **Accept as-is.** Possible, but not fully supported by this task alone:
   the primary, *online* position-verified arrival path is confirmed
   stale-tolerant by design (`classify_arrival`, `ArrivalGate.
   on_nav2_success` — a stale M1 estimate is still `accepted=True` and
   still calls `mark_arrived`), and every non-spawn pose checked here is
   clean or near-clean — but "every non-spawn pose checked here" excludes
   the composite command's own geometry (not yet built) and was never
   meant to be exhaustive over every dwell IB10 could produce. Revisit
   once `junction_clear` exists and its own poses can be checked the same
   way.
2. **Symmetric redesign.** Nudge the whole E-W arm (both `robot_1` and
   `robot_2` spawns/goals) by the same delta to a jointly-clean radius,
   re-deriving `test_approach_radii_are_equal` and the downstream park-
   offset/backup-clearance numbers consistently, as part of IB10's already-
   planned re-authoring. (Swapping which robot starts on which side,
   instead of changing the radius, does not work — see "Fix: not applied".)
   A phase-dependent mechanism also means the chosen replacement radius
   needs its own clean-pose check, not an assumption that "away from 1.75"
   is automatically safe.
3. **Instrument, don't move (recommended default).** Leave geometry
   untouched and have the step-6 mock smoke (and any later composite-
   command smoke) check for this signature generically: a long `STALE`
   streak on *any* robot at *any* stationary dwell — spawn, single-yield
   park, composite recede/park, or goal arrival — not just robot_1's
   pre-departure window specifically. Given the mechanism is a per-pose
   phase effect, and marker 1 has now been tested at 6 distinct poses
   across this study and the y-extent study (failing chronically at 1 of
   them), a running check that catches it wherever it next appears is more
   proportionate than hand-verifying every future pose one VM run at a
   time.

---

## Artifacts

- Scenario yamls: `isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml`,
  `isaac/config/scenarios/m1_stale_rootcause_probe_nudge.yaml`,
  `isaac/config/scenarios/m1_stale_rootcause_probe_goalpose.yaml`,
  `isaac/config/scenarios/m1_stale_rootcause_probe_yieldpark.yaml`.
- Driver: `scripts/vm/m1_stale_rootcause_probe.sh`.
- Analysis (reused from the y-extent probe, unmodified):
  `scripts/m1_y_extent_probe_analysis.py`.
- VM raw logs (git-ignored, left on the VM at
  `/home/ubuntu/vgu-vlm-swarm/data/logs/vm_runs/stale_rootcause/`):
  `swap_20261001_160116/`, `nudge_20261001_161427/`,
  `goalpose_20261001_163514/`, `yieldpark_20261001_170347/`.
- Synced copy, durable in the main checkout (git-ignored, under
  `data/logs/`, not just this worktree): same four directory names under
  `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs/stale_rootcause/`,
  each holding `scenario.yaml`, `m5_scene.jsonl`, `gt/ground_truth.jsonl`,
  `m1.log`, `m5.log`, `isaac.log`, `launcher.log`, `restore_build.log`.

Reproduce the tables above:

```bash
python3 scripts/m1_y_extent_probe_analysis.py \
  data/logs/vm_runs/stale_rootcause/swap_20261001_160116 \
  data/logs/vm_runs/stale_rootcause/nudge_20261001_161427 \
  data/logs/vm_runs/stale_rootcause/goalpose_20261001_163514 \
  data/logs/vm_runs/stale_rootcause/yieldpark_20261001_170347
```

---

## VM and repo state at close

- `orchestrator.yaml`: pristine, md5 `1f656533a30a35882d57d0d64a57bd0d`
  (source and installed, verified after every run).
- `config/rag.yaml`: untouched, md5 `e18c723cff9cada3f320d564c2ecee5a`.
- `data/logs/m5_decisions/`: 2177 files, newest unchanged
  (`b14c2237c2fd4cba8437f2a4dadeff47.json`, predates this task) — zero VLM
  spend across all four runs.
- No `run_simulation`/Isaac `kit` process on the host; no `ros2`/orchestrator/
  perception/Nav2 process inside `vgu_ros`; `nvidia-smi` shows `0%` GPU
  utilization, `171 MiB`/`24570 MiB` memory. GPU idle.
- Deploy tarballs (`/tmp/stale_rootcause_repo*.tar`) removed from the VM.
- **VM tree additions this task leaves behind** (for the next md5-manifest
  deploy to account for): 4 scenario yamls under
  `isaac/config/scenarios/m1_stale_rootcause_probe_{swap,nudge,goalpose,
  yieldpark}.yaml`; 4 built USDs under
  `isaac/scenarios/m1_stale_rootcause_probe_*.usd`; 4 generated maps under
  `ros2_ws/src/swarm_simulation/maps/warehouse_map_m1_stale_rootcause_
  probe_*.{pgm,yaml}`, present in both the source tree and the `colcon`-
  installed copy; the driver `scripts/vm/m1_stale_rootcause_probe.sh`.
  `orchestrator.yaml` itself is pristine (see above) — only new files were
  added, no shared file was left modified.
- Local `pytest` on this dev machine has 63 pre-existing failures in code
  this task did not touch (an `opencv-contrib-python 5.0.0.93` vs. the
  `requirements.txt` `>=4.8` floor API-shape mismatch — e.g.
  `test_aruco_parity.py`'s `detect_aruco_markers` call raises `IndexError`
  on this machine's cv2). Not independently verified against a clean
  checkout predating this task's commits; the basis for calling it
  pre-existing and unrelated is that none of this task's changes touch
  `detection.py`, any marker asset, or `requirements.txt`, and no test in
  the failure list globs or otherwise references the new scenario yamls or
  driver script this task added.
