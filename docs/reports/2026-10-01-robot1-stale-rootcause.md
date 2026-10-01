# M1 Root-Cause — robot_1 / (-1.75, 0) STALE Dropout at the IB10 Spawn

**Prepared:** 2026-10-01

**Revision history:**

- Initial draft: root-causes the "registered risk" flagged in
  `docs/reports/2026-10-01-m1-y-extent-verification.md` (robot_1, marker_id
  1, STALE 74.0%/82.1% across two replicated runs at `(x, y) = (-1.75, 0)`,
  the exact spawn of `isaac/config/scenarios/intersection_bottleneck.yaml`'s
  robot_1) before v2 build-order step 6 (IB10 composite mock smoke,
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`).

**commit:** `3f24ac9` (swap + nudge probes), `f155d7a` (goalpose probe),
branch `feat/v2-stale-rootcause`

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

Three short mock-backend VM runs (`BACKEND_ID=mock`, zero VLM calls —
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
  pose probe**, added after the first two runs (see "Why a third run" below).
  All four robots held at their actual `intersection_bottleneck.yaml` GOAL
  positions, all at `yaw = 0` — the real Nav2 arrival orientation
  (`command_bus_node.py`: `yaw = goal.get("yaw", 0.0) if isinstance(goal,
  dict) else 0.0`; IB10's `cross_intersection` goals are plain `[x, y]`
  lists, so every robot's commanded arrival yaw defaults to 0, not its
  spawn yaw).

All three scenarios built, validated (`validate_simulation.py`: `PASS` on
every USD) and run through `scripts/vm/fc_launch.sh` via a new driver,
`scripts/vm/m1_stale_rootcause_probe.sh` (modeled on, but kept separate
from, `scripts/vm/m1_y_extent_probe.sh`). `orchestrator.yaml` was restored
and verified pristine (md5 `1f656533a30a35882d57d0d64a57bd0d`, both source
and installed copies) after every run. Detection scored the same way as the
y-extent report, via `scripts/m1_y_extent_probe_analysis.py` against each
run's own `scenario.yaml` spawns and `gt/ground_truth.jsonl`.

**Zero VLM spend, all three runs:** `data/logs/m5_decisions/` carried the
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

GT cross-check (all three runs): every robot stayed within `0.0001`-`0.0003`
m of its authored spawn for the whole episode (stationary premise holds),
and `min_pairwise_distance_m` stayed at `2.04`-`2.47` m throughout every run
— far beyond any marker-overlap range, ruling out the overlapping-marker
`STALE` mechanism (hypothesis 5) directly from this task's own GT, same as
the y-extent report's run.

---

## Mechanism

Five hypotheses were in play. Static scene inspection ruled out three
before any VM time was spent, and the swap/nudge/goalpose runs resolved the
rest:

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
   `min_pairwise_distance_m` stayed 2.04-2.47 m in every run here (and
   2.122 m in the original y-extent runs).
4. **Marker-identity vs. position, resolved by direct test.** The **swap
   run** shows the catastrophic failure does **not** travel with marker 1:
   at its new position `(+1.75, 0)`, marker 1 is clean (100% fresh, 93.15%
   exact-stamp). It also does **not** stay at the position regardless of
   marker: marker 2 at `(-1.75, 0)` shows only mild, scattered degradation
   (95.55% fresh, 7-row max streak) — nowhere near marker 1's historical
   74-82% `STALE` rate there. The **goalpose run** independently replicates
   this exact split (marker 1 at its own goal, `(1.75, 0, yaw 0)`: 100%/100%;
   marker 2 at `(-1.75, 0, yaw 0)`: 96.63%/70.03%, 5-row streak) at a second
   yaw, ruling out yaw as the discriminator. **The severe failure needs
   both the specific marker_id=1 bit pattern and the specific position
   `x ~= -1.75` together** — neither alone reproduces it.
5. **A real, position-generic background marginality exists underneath
   it, measured directly.** Every run that places *any* marker at
   `|x| ~= 1.75-1.85` shows some exact-stamp-match degradation even when
   `fresh_rate` stays 100% (robot_1/swap at `+1.75`: 93.15%;
   robot_4/goalpose at `0,-1.75`: 93.27%; robot_2's own mirror position in
   the original y-extent study: 87.7%/92.4%) — a shared, low-severity noise
   floor from the marker's small rendered footprint (next point), not
   unique to marker 1 or to `x = -1.75`'s sign.

**Where the marginality comes from (measured, not inferred from frames —
no debug frames were captured on these runs; this is reasoned from the
asset's own pixel geometry and OpenCV's documented defaults, not from
rendered output).** `isaac/vgu_sim/marker_asset.py`'s `MARKER_SIZE_M = 0.12`
quad carries `aruco.yaml`'s `marker_size_m` texture at `640x640` px; the
black 6x6 ArUco cell (border + 4x4 data) occupies the center `512/640 = 80%`
of that texture (measured directly: `cv2.imread` + threshold on
`isaac/assets/markers/aruco_4x4_50/marker_1.png`), i.e. `0.096` m physical.
`aruco.yaml`'s homography gives `0.0043583` m/pixel at the overhead camera's
resolution, so the full marker quad projects to `27.5` camera px and the
black 6x6 cell to `22.0` px — **`3.67` px per ArUco cell**. OpenCV's
`cv2.aruco.DetectorParameters()` default `perspectiveRemovePixelPerCell` is
`4` (confirmed by direct inspection of the installed
`opencv-contrib-python` in this task's environment) — the marker's rendered
footprint sits *below* the resolution OpenCV's own default decode step
expects per cell. This is a generic marginal-footprint condition at
`|x| ~= 1.75-1.85` that costs any marker a few percent of exact-frame
detections; which specific marker IDs tip from "a few percent of frames"
to "74-82% chronically STALE" at which specific position is then a function
of that ID's exact bit pattern interacting with the sub-pixel sampling
phase at that exact world coordinate under `errorCorrectionRate=0.6`
nearest-dictionary-entry matching — a renderer/decode-level interaction,
observed here only through its effect on `STALE` rates, not confirmed
against captured frames. Also note this interaction is **not** a clean
`|x|`-symmetric band: `-1.75` (yaw 0) is markedly worse for both tested
markers than `+1.75` is for marker 1, despite the camera, homography and
rack layout all being structurally symmetric — an unexplained renderer-level
asymmetry, reported as an open detail rather than resolved.

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

## Why a third run (goalpose)

The swap run alone left a gap: it tested marker 1 at `(+1.75, 0, yaw=pi)`,
not at `(+1.75, 0, yaw=0)` — robot_1's *actual* IB10 goal orientation, since
`command_bus_node.py` defaults every Nav2 arrival yaw to `0.0` regardless of
spawn yaw (`intersection_bottleneck.yaml`'s goals are plain `[x, y]`, not
`{x, y, yaw}` dicts). The N-S arrival poses `(0, +-1.75, yaw=0)` were never
tested at that yaw either. The goalpose run closes this gap directly and
narrows the practical IB10 risk considerably (see Scope below).

---

## Scope against IB10

The registered risk worried about two IB10-scored consumers of M1 state:
the "all four robots reach goals, position-verified" resolution criterion,
and Arm B's shadow classification. The goalpose run measures exactly the
first of these directly, and both the swap and goalpose runs together
narrow the second:

- **robot_1's own IB10 goal arrival, `(1.75, 0, yaw=0)`: confirmed clean**
  (100% fresh, 100% exact-stamp-match, 0 `STALE`, in both the swap run at a
  different yaw and the goalpose run at the real arrival yaw). The marker
  that actually fails catastrophically is clean at the position it will
  actually be commanded to reach.
- **robot_2's IB10 goal arrival, `(-1.75, 0, yaw=0)` — the position that
  broke marker 1: only mild, generic degradation** (95.6%/96.6% fresh
  across the two runs that test it, 70-74% exact-stamp-match, longest
  streak 5-7 rows ~ 5-7 s), matching the same order of magnitude as the
  background noise floor measured at other markers/positions in this study
  and the prior y-extent report. Not zero risk to a scoring check sampled
  at an unlucky instant, but not the chronic 74-82% failure either.
- **robot_3/robot_4's IB10 goal arrivals, `(0, +-1.75, yaw=0)`: clean**
  (100% fresh both; exact-stamp-match 100%/93.27%, in line with the
  background floor).
- **The catastrophic 74-82% `STALE` failure is specific to robot_1 sitting
  still at its own IB10 *spawn*, `(-1.75, 0, yaw=0)`, before it departs** —
  not to any of the four scored goal arrivals. In the real IB10 run robot_1
  is only stationary there during the ~8-10 s M5/Nav2 bring-up window before
  `cross_intersection` dispatches its goal (per `expected_conflict.
  onset_window_sec: [8.0, 40.0]`); once it departs it moves off `x = -1.75`
  and, per the above, is clean again at every other position tested. Whether
  this transient pre-departure window reaches any scored output depends on
  exactly when Arm B first samples `/perception/scene_state` relative to
  that bring-up — not established by this task; flagged for the step-6
  owner to check against Arm B's actual sampling start, not assumed benign.

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
- **The Scope section above found the practical risk narrower than the
  nudge would fix anyway.** The nudge fixes robot_1's *spawn*; the
  position-verified *goal* arrivals (the actually-scored checkpoint) are
  already confirmed clean for robot_1 and only mildly noisy for robot_2 —
  the IB10-relevant question is not simply "does nudging -1.75 help"
  (yes) but "does the un-nudged scenario's scored output actually need it"
  (narrower than originally feared, and not fully settled here — see the
  open Arm B sampling-timing question above).

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

Three options, none applied here:

1. **Accept as-is.** If Arm B's first `/perception/scene_state` sample
   post-dates robot_1's departure from `x ~= -1.75` (needs a direct check
   against the composite mock smoke's own logs), the catastrophic window
   never reaches a scored consumer and no scenario change is needed — only
   the mild, already-quantified background noise at robot_2's goal arrival
   remains, which is within the range already tolerated elsewhere in this
   study.
2. **Symmetric redesign.** Nudge the whole E-W arm (both `robot_1` and
   `robot_2` spawns/goals) by the same delta to a jointly-clean radius,
   re-deriving `test_approach_radii_are_equal` and the downstream park-
   offset/backup-clearance numbers consistently, as part of IB10's already-
   planned re-authoring.
3. **Instrument, don't move.** Leave geometry untouched and have the step-6
   mock smoke explicitly check for this signature (a long `robot_1` `STALE`
   streak confined to the pre-departure window) so it is recognized as this
   known, bounded issue rather than re-investigated from scratch.

---

## Artifacts

- Scenario yamls: `isaac/config/scenarios/m1_stale_rootcause_probe_swap.yaml`,
  `isaac/config/scenarios/m1_stale_rootcause_probe_nudge.yaml`,
  `isaac/config/scenarios/m1_stale_rootcause_probe_goalpose.yaml`.
- Driver: `scripts/vm/m1_stale_rootcause_probe.sh`.
- Analysis (reused from the y-extent probe, unmodified):
  `scripts/m1_y_extent_probe_analysis.py`.
- VM raw logs (git-ignored, left on the VM at
  `/home/ubuntu/vgu-vlm-swarm/data/logs/vm_runs/stale_rootcause/`):
  `swap_20261001_160116/`, `nudge_20261001_161427/`,
  `goalpose_20261001_163514/`.
- Synced copy, durable in the main checkout (git-ignored, under
  `data/logs/`, not just this worktree): same three directory names under
  `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs/stale_rootcause/`,
  each holding `scenario.yaml`, `m5_scene.jsonl`, `gt/ground_truth.jsonl`,
  `m1.log`, `m5.log`, `isaac.log`, `launcher.log`, `restore_build.log`.

Reproduce the tables above:

```bash
python3 scripts/m1_y_extent_probe_analysis.py \
  data/logs/vm_runs/stale_rootcause/swap_20261001_160116 \
  data/logs/vm_runs/stale_rootcause/nudge_20261001_161427 \
  data/logs/vm_runs/stale_rootcause/goalpose_20261001_163514
```

---

## VM and repo state at close

- `orchestrator.yaml`: pristine, md5 `1f656533a30a35882d57d0d64a57bd0d`
  (source and installed, verified after every run).
- `config/rag.yaml`: untouched, md5 `e18c723cff9cada3f320d564c2ecee5a`.
- `data/logs/m5_decisions/`: 2177 files, newest unchanged
  (`b14c2237c2fd4cba8437f2a4dadeff47.json`, predates this task) — zero VLM
  spend across all three runs.
- No `run_simulation`/Isaac `kit` process on the host; no `ros2`/orchestrator/
  perception/Nav2 process inside `vgu_ros`; `nvidia-smi` shows `0%` GPU
  utilization, `171 MiB`/`24570 MiB` memory. GPU idle.
- Deploy tarballs (`/tmp/stale_rootcause_repo*.tar`) removed from the VM.
- Local `pytest` on this dev machine has 63 pre-existing failures unrelated
  to this task (an `opencv-contrib-python 5.0.0.93` vs. the `requirements.txt`
  `>=4.8` floor API-shape mismatch — e.g. `test_aruco_parity.py`'s
  `detect_aruco_markers` call raises `IndexError` on this machine's cv2
  before this task's changes existed; all three new scenario yamls and the
  new driver script add zero new failures, confirmed by name-matching the
  failure list against files this task touched).
