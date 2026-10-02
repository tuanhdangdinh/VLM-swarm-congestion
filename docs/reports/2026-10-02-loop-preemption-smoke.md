# Loop Map — Nav2 Pre-emption Control Smoke (v2 build-order step 8, Phase 1)

**Prepared:** 2026-10-02

**Revision history:**

- Initial draft (Rev 1): geometry analysis and go/no-go gate, written and
  committed before any builder code or VM time, per
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` build-order step 8
  ("Loop map: USD + Nav2 + reroute grounding; the pre-emption control smoke
  before any scenario authoring") and the design doc's own risk paragraph
  under "(b) Loop map". This revision answers only the STOP/GO geometry
  question; builder extensions and the live VM smoke follow in later
  revisions.
- Rev 2: builder extension landed (Section 4) and scenario YAMLs authored
  (Section 5), both local-only (no VM time): (a) the M1-coverage bonus
  probe's second point moved from `(1.4, 1.2)` to `(1.2, 1.2)` — the
  original was only 0.447 m from the other probe point, under both the
  0.45 m latch and the 0.57 m spawn-pair rule; (b) the blocker's "present
  from `t=0`" claim narrowed to not assert literal-first-costmap timing
  (Section 5 — the 3.5 m `obstacle_max_range` margin is only 0.025 m);
  (c) protocol note: adding `loop_map` to `ScenarioConfig` makes
  `generate_head_on_family.py`'s generic `model_dump` emit a new
  `loop_map: null` line in all 7 committed v1 head-on-family fixtures —
  mechanical, null-only, required to keep that generator's own
  byte-identity test passing, recorded here as the one v1-frozen-artifact
  touch this build makes (relationship-to-v1 rule 2: v2-branch-only, never
  merged into the collection tree pre-completion).

---

## Purpose

The design doc's loop-map section states the risk this report exists to
retire before any loop scenario is authored:

> Nav2 on a loop map may reroute *on its own* when the global costmap sees
> the blocker, pre-empting the decision layer. Design control: blocker
> placed so the global planner's path stays viable (narrowed-not-blocked,
> below costmap lethal threshold) while transit is throttled — the decision
> to detour must remain M2/M3's. This is the first thing the loop-map smoke
> must verify.

Before that smoke can run, two things must independently hold:

1. **Geometric fit.** A second E-W aisle plus the N-S connector(s) needed to
   close a cycle must sit inside the region M1 actually tracks, not just
   inside the 12 m x 8 m warehouse floor.
2. **Visibility, not just coordinates.** A point inside the tracked `|x|`/`|y|`
   rectangle is only usable if the overhead camera's line of sight to it is
   not blocked by the rack mass that has to exist between the two aisles for
   the loop to be a real cycle (not just a widened single aisle).

This revision works both questions from the repo's own constants and the
existing M1 verification evidence, with no new VM run. It is the STOP gate
the task calls for: build on (3) below only if this geometry holds.

---

## 1. Constants used (all from the repo, not re-derived)

| Constant | Value | Source |
|---|---|---|
| Warehouse floor | 12 x 8 m | `isaac/config/warehouse.yaml` / `WarehouseConfig` |
| Nominal aisle half-width `aw` | 0.6 m | `nominal_aisle_width_m: 1.2` |
| Rack block height | 0.9 m | `warehouse_builder._build_rack_blocks` (`rack_h = 0.9`) |
| NE rack footprint | x in [0.6, 6.0], y in [0.6, 4.0] | `_rack_block_obstacles` (`rack_half_width=2.7`, `rack_half_depth=1.7`, centre (3.3, 2.3)) |
| Overhead camera pose | (0, 0, 3.0), nadir | `CameraConfig.position_m`, identity quat |
| Camera horizontal half-FOV | 45.0 deg (`atan((20.955/2)/10.48)`) | `CameraConfig.horizontal_aperture_mm` / `focal_length_mm` -> ground half-width `3.0*tan(45) = 3.0 m`, matching `roi_width_m: 6.0` |
| Camera vertical half-FOV | 36.87 deg (`atan((15.716/2)/10.48)`) | `CameraConfig.vertical_aperture_mm` -> ground half-depth `3.0*tan(36.87) = 2.25 m`, matching `roi_depth_m: 4.5` |
| M1 tracked extent, verified clean | `\|x\| <= 2.5`, `\|y\| <= 2.0` | `docs/reports/2026-10-01-m1-y-extent-verification.md` (Rev 2, PASS; Run B additionally confirms `\|y\|=1.8` and `\|y\|=2.0` clean) |
| M1 hard homography edge | x: 2.789, y: 2.092 | same report / intersection study |
| Registered risk: avoid `robot_1` (marker_id 1) at `(x=-1.75, y=0, yaw=0)` | reproducible STALE, 51-53 row streaks, 2 independent runs | same report, "Registered risk" section |
| Clean reference point for `robot_1`/marker_id 1 | `(x=-2.4, y=0, yaw=0)`: 100% fresh, 100% exact-stamp, bias 0.0123 m | same report, Run B |
| Clean reference point, `\|y\| ~= 1.2` (both signs) | 100% fresh, 0 STALE, bias 0.0029-0.0072 m, replicated 2x | same report, Run A1/A2 |
| C55 single-lane module, proven plannable floor | 0.55 m (band [0.50, 0.63)) | `docs/superpowers/specs/2026-09-29-unified-scene-design.md` |
| Lidar scan plane height | 0.182 m | `nav2_params.yaml` footprint / T3a header |
| Nav2 planner inflation floor | gap > 0.38 m plannable in principle, 0.50 m proven in practice (T3a) | unified scene design, "apparatus conflict" table |

---

## 2. Minimal loop topology

The base warehouse is a single cross: one E-W strip `\|y\| <= 0.6` and one
N-S strip `\|x\| <= 0.6`, both open for the full floor; the four quadrants
beyond that (`\|x\| > 0.6` and `\|y\| > 0.6`) are solid 0.9 m rack. This
matters directly: **the existing N-S strip already functions as one of the
two connectors a loop needs**, for free, at every x in `[-0.6, 0.6]` and
every y up to the north wall. Building "two new N-S connectors" would
create a second, redundant cycle through the same junction square; the
minimal loop needs exactly **one new connector**, east of the primary
aisle, plus a new second E-W aisle segment to carry it back to the N-S
strip.

Chosen geometry (all new pieces scenario-local; the shared warehouse asset
is untouched — see Section 4):

| Piece | Geometry | Rationale |
|---|---|---|
| Second aisle | centre `y = 1.2`, width `0.55 m` (`y in [0.925, 1.475]`), `x in [0.6, 2.2]` | `y=1.2` reuses the single most-verified off-axis point in the whole corpus (0.0029-0.0072 m bias, 0 STALE, replicated); width reuses the proven C55 floor |
| West connector | the existing N-S strip, `\|x\| <= 0.6`, unmodified | already open for all y; no new geometry |
| East connector (new) | centre `x = 1.8`, width `0.55 m` (`x in [1.525, 2.075]`), `y in [0.6, 0.925]` | links the primary aisle's north edge to the second aisle's south edge, east of the junction square so it cannot be confused with local junction maneuvering |
| Partial blocker (control) | centred `x = 1.2`, strictly between the N-S strip (`x<=0.6`) and the new connector (`x>=1.525`) | forces the choice to be "squeeze through" vs. "take the real loop", not a local dodge inside the open junction |
| Robot | spawn `(-2.4, 0, 0)`, goal `(2.3, 0, 0)` | spawn reuses `robot_1`'s verified-clean point (avoids the registered `-1.75` STALE risk); goal sits 0.225 m east of the new connector's mouth and 0.2 m inside the `\|x\|<=2.5` verified edge |

Direct path length (spawn to goal along the primary aisle): 4.7 m. Loop
path length (spawn -> junction -> north through the N-S strip -> east along
the second aisle -> south through the new connector -> goal): ~6.1 m, about
1.4 m (30%) longer — a real but moderate detour cost, not a trivial one, so
a self-reroute is a genuine planner decision rather than a coin flip.

**C1 check (tracked band).** Every new coordinate: aisle south edge 0.925,
north edge 1.475, connector edges 1.525/2.075, goal 2.3 — all inside
`\|x\| <= 2.5`, `\|y\| <= 2.0` with margin (smallest margin: goal-to-edge,
0.2 m; aisle-north-edge-to-edge, 0.525 m). **PASS.**

---

## 3. Visibility: the occlusion check the y-extent report never ran

The y-extent report's points were all on-axis (`x=0` or `y=0`), with open
floor between the camera nadir and the marker — no rack mass was ever
between the camera and the target. The loop puts a rack divider directly
between the camera and the second aisle, which is a materially different
geometry and is checked here for the first time.

**Model.** The camera is a perspective projection at `(0, 0, 3.0)`, nadir.
For a target at ground position `(x, y)` and height `h` (marker ~0.2 m),
the sight line crosses a rack-height plane `z = H` at parameter
`t* = (3 - H) / (3 - h)`, landing at `(t*x, t*y)`. A rack segment of height
`H` and footprint `F` therefore occludes every target whose `(x, y)`,
scaled by `k = (3-h)/(3-H) = 2.8/(3-H)`, lands inside `F` — i.e. the
occluded region in target space is `F` scaled by `k` about the origin.
`k > 1` whenever `H > h`, so **taller dividers always shadow a region
beyond their own footprint**, and dividers close to the camera's nadir
project that shadow onto whatever sits just past them — exactly where a
second aisle has to be.

**If the divider between the two aisles were left at the shared warehouse's
standard 0.9 m rack height** (`k = 2.8/2.1 = 1.333`): the connector-band
remnant at `x in [0.6, 1.525]`, `y in [0.6, 0.925]` would shadow target
region `x in [0.8, 2.03]`, `y in [0.8, 1.23]` — which blankets almost the
entire second aisle (`y in [0.925, 1.475]`) over most of its usable length.
**At standard rack height this loop does not fit inside what the camera can
see.** This is the geometric near-miss the task's STOP clause anticipates.

**Fix (scenario-local, not a shared-asset change).** Build only the two
thin connector-band remnants (the rack mass immediately flanking the new
connector, `y in [0.6, 0.925]`) at a reduced height of **0.3 m** instead of
0.9 m — a low divider wall, still physically plausible, still above the
0.182 m lidar scan plane (so Nav2's local costmap still sees it as a solid
boundary, keeping the map and the physics world consistent, the same
concern `generate_warehouse_map.py`'s own docstring flags for
`aisle_barrier`). At `H = 0.3`: `k = 2.8/2.7 = 1.037`.

Re-running the two remnants' shadows at `H = 0.3`:

| Remnant | Footprint | Shadow (`k=1.037`) | Overlaps the drivable lane? |
|---|---|---|---|
| West-of-connector (`piece A`) | x[0.6,1.525], y[0.6,0.925] | x[0.622,1.582], y[0.622,0.959] | Only a 3.4 cm sliver of the aisle's extreme south edge (y up to 0.959); the robot's usable lane centre-band, keeping its 0.09 m half-width inside the 0.55 m aisle, is y in [1.015, 1.385] — clear by 0.056 m |
| East-of-connector (`piece B`) | x[2.075,6.0], y[0.6,0.925] | x[2.152,6.22], y[0.622,0.959] | Outside the loop's used extent (`x<=2.2`) entirely |

The two untouched, full-height (0.9 m) remnants — the far north slab
(`y in [1.475,4.0]`) and the second-aisle's eastward continuation
(`x in [2.2,6.0], y in [0.925,1.475]`) — shadow `y >= 1.967` and
`x >= 2.933` respectively, both well outside the aisle/connector region
used here.

**Residual, flagged not fixed.** A small corner (`x in [1.525,1.582]`,
`y in [0.925,0.959]`, about 6 cm x 3 cm) at the connector's extreme
southwest is still technically shadowed by `piece A` even at 0.3 m. It sits
outside the connector's own carved opening's drivable centre and is not
reachable by the robot's footprint on the design path (connector centre
`x=1.8`). Recorded here, not re-derived further; a live stationary check
(Section 6) covers it empirically if the mitigation ladder or later
scenario authoring ever moves a robot that close to the corner.

**Verdict: the loop fits and stays visible, conditional on one explicit,
scenario-local deviation** — the two connector-flanking rack remnants are
authored at 0.3 m instead of the shared 0.9 m rack height. This is the same
kind of recorded, load-bearing deviation the unified scene design document
already uses for D1-D3 (e.g. T3a's 0.50 m corridor width); it changes
nothing in any existing scenario, because it only exists in new,
scenario-local replacement geometry (Section 4) that the shared
`warehouse.usd` never contains.

**GO.** Geometry and visibility both clear; proceeding to the builder
extension and the VM smoke.

---

## 4. Builder plan (not yet implemented as of this revision)

Kept strictly additive, per `CLAUDE.md`'s module-boundary and scope-discipline
rules — no edit to `WarehouseConfig`, `warehouse_builder.py`, or the default
`warehouse_map.pgm`/`.yaml`, since every v1 scenario sublayers/derives from
them unchanged:

- New `LoopMapConfig` on `ScenarioConfig` (default `None`), named fields for
  the second-aisle band, its x-extent, and the one new connector — mirroring
  `AisleBarrierConfig`'s shape and validators.
- `scenario_builder.py`: a new `_author_loop_connectors`, called only when
  `config.loop_map is not None`, exactly like `_author_aisle_barrier`'s
  existing call site. It (a) overrides `/World/Environment/RackBlocks/NE`
  to `active=False` in the scenario's own root layer (an additive USD
  override in the stronger layer — the shared warehouse `.usd` file on disk
  is never written), and (b) authors four replacement cubes reconstructing
  NE's footprint minus the second-aisle and connector notches, matching
  Section 3's heights (0.9 m for the two untouched remnants, 0.3 m for the
  two connector-flanking remnants). NW/SE/SW racks are untouched.
- `generate_warehouse_map.py`: a new `rasterize_loop_map`, mirroring
  `rasterize_aisle_barrier`'s style but clearing (FREE) rather than marking
  (OCCUPIED) the same three world rectangles (second aisle, and the gap the
  new connector opens through the rack), applied after the base rack-block
  pass so it carves into, rather than conflicts with, the default occupancy.
- Regression check before any commit: regenerate the default map and every
  existing per-scenario map with the new code path unexercised
  (`loop_map: None`) and diff their bytes/md5 against the pre-change copies
  — they must be identical, since no existing scenario sets `loop_map`.
- Check `isaac/vgu_sim/validation.py` for any rack/free-floor legality
  assumption the carve could silently violate (per
  `project_aruco_marker_placement` memory: validation must be kept in sync
  or it fails silently).

## 5. Blocker presentation (decided, not yet built)

The control blocker must be **sensor-seen, not map-baked** — the design
doc's risk is phrased as "when the global costmap *sees* the blocker",
which only exercises the pre-emption question if the blocker arrives the
way T3a's does: as a `timed_obstacles` entry (lidar-visible, untracked by
M1, absent from the static map at `t=0`), not as a structural
`aisle_barrier` baked into the map from the start. A baked-only narrow
aisle answers "does Nav2 plan through a 0.55 m gap" (already answered,
everywhere else in the battery) rather than "does Nav2 *replan toward the
loop* when a new obstacle narrows its existing plan" (the actual risk).

- `asset: static_box`, `size: {x_m: 0.25, y_m: 0.65, z_m: 0.35}` (z clears
  the 0.182 m lidar plane, matching T3a's own box), pose
  `(1.2, -0.275, 0)` — spans `y in [-0.6, 0.05]`, leaving a `y in [0.05,
  0.6]` gap, i.e. a **0.55 m remaining corridor width**, the same proven
  C55 floor used everywhere else in the battery (reused evidence, not a new
  number).
- Present from `spawn_at_sec: 0.0` (not injected mid-episode), so there is
  no transient/object timing question. **Not claimed:** that the literal
  first costmap update reflects it — `nav2_params.yaml`'s
  `obstacle_max_range` is 3.5 m, and the box's near face sits 3.475 m from
  spawn, a 0.025 m margin too thin to assert sensor-geometry timing on.
  What the design actually needs — lidar detection well before the robot
  reaches the gap, not a map-baked fact — holds regardless: the box is
  already inside range at spawn and the robot closes distance immediately.
- Baseline run: identical scenario with `timed_obstacles: []`.
- Both runs keep `aisle_barrier: null` — the primary aisle stays its full
  structural 1.2 m; only the timed box narrows it, so the two runs differ
  by exactly one obstacle.

---

## 6. What the live VM smoke still owes (next revision)

1. Builder extension + unit tests (pure-Python: config validation, map
   rasterization — runnable locally) and USD authoring (needs `pxr`, VM-only).
2. Map regeneration + byte-identical regression check on every existing map.
3. A short stationary M1-coverage probe (mirroring the y-extent probe
   pattern) with one robot held at the second aisle's worst-case point
   (near the connector, close to the flagged residual corner) — empirical
   confirmation of Section 3's analysis, not required for the GO verdict
   above but registered as the cheap close-out for the one residual noted
   there.
4. Baseline run (no blocker): confirm Nav2 does not take the loop
   spuriously, from global-plan topic logs and GT trajectory.
5. Partial-blocker run: confirm Nav2 pushes through/waits in the primary
   aisle without self-detouring, same evidence; mock backend confirmed
   silent (no dispatch, no decision artifact) on both runs.
6. Mitigation ladder (blocker footprint / connector-side costmap inflation,
   scenario-local only) only if run 5 fails, with measured numbers either
   way.
7. STALE streak check on every run's stationary dwell.
8. VM pristine restore, md5 verification, logs synced.
