# Ground-Truth Contact Logging: Footprint Geometry and Recompute

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: defect, design, always-on decision, reader audit, tests, the offline recompute over 44 bundles, limits and deployment notes.

---

## Scope

- **Branch:** `feat/gt-contact-logging`, based on `8933863` (the VM pin
  `68e67b5` plus the safety-exemption fix). Local commits only.
- **Owner approval:** real contact logging in the simulator ground truth
  (2026-11-15).
- **Evidence grade:**
  - Unit tests (geometry, scene boxes, logger, recompute tool).
  - Parity with the static-map generator, run here. It is cell-level, on a
    0.05 m grid: it proves the box set and placement to one cell, not to the
    millimetre. Millimetre exactness rests on the shared `config.py` helpers
    (`rack_quadrant_rects`, `rack_clearance_remnants`), the explicit wall and
    barrier extent assertions, and the m5D regression (section 5.2).
  - Offline recompute over 44 recorded bundles, read-only.
  - **No Isaac Sim run.** A live validation run is still needed; it is not
    part of this work.

---

## 1. The Defect

`isaac/vgu_sim/acceptance_logging.py` (lines 99-100 at `8933863`) wrote

```python
"robot_static_contacts": [],
"robot_robot_contacts": [],
```

into every ground-truth row. No detector existed, so "0 contacts" in ground
truth recorded nothing. Earlier findings of this:

- `docs/reports/2026-09-25-overnight-findings.md`, Metric correction 2: the
  robot-robot list stayed empty through 51 sim-s of driven nose-to-nose
  contact at 0.076 m centre distance.
- Prereg amendment A5 (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`):
  the contact flags are disqualified as evidence; safety is reported from
  distance channels.
- `fc73151` (prereg-v2 caveat extension, 2026-10-09): the same holds for
  static contacts. v1/v2 contact scoring is by distance recompute against
  declared obstacle and rack footprints, and `robot_static_contacts` "is not
  citable as evidence until v3 implements it."
- `docs/reports/2026-11-15-demo-campaign-results.md` section 8.7: in take
  `m5D_t01_a1`, robot_3 sat pinned against rack island `obstacle_2` for
  about 450 s while both lists stayed empty.

This work implements the field. It does not reopen those rulings. Section 6
says what the new values may and may not support.

---

## 2. Design

### 2.1 What Is Measured

`isaac/vgu_sim/contact_geometry.py` is a new module with no Isaac or USD
import. For each logged row, it places the TurtleBot3 Burger URDF collision
shapes at the row's `base_link` pose and measures the signed planar gap to
every collidable box and to every other robot. A negative gap is overlap.

Robot shapes (`isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf`),
in the `base_link` frame:

| Shape | URDF | Plan view | Height (world z) |
|---|---|---|---|
| Chassis | box 0.140 × 0.140 × 0.143 at (−0.032, 0, 0.070) | 0.140 × 0.140, x −0.102 to +0.038 | 0.009–0.152 |
| Wheels (2) | cylinder r 0.033, l 0.018 at (0, ±0.080, 0.023), axis along y | 0.066 × 0.018, y reach ±0.089 | 0.000–0.066 |
| Caster | box 0.030 × 0.009 × 0.020 at (−0.081, 0, −0.004), rolled −90° | 0.030 × 0.020 | 0.0015–0.0105 |
| Lidar | cylinder r 0.055 at (−0.017, 0, 0.1655) | circle r 0.055 | 0.160–0.191 |

The lidar and caster lie inside the chassis plan (tested). The wheels set the
lateral reach (±0.089 m), and the chassis sets the nose (+0.038 m) and the
rear (−0.102 m).

Static boxes are what the builders author. The module mirrors their arithmetic
without importing them:

| Category | Id | Builder |
|---|---|---|
| Walls (4) | `wall/north` … | `warehouse_builder._build_walls`, outside the 12 × 8 m floor, 1.2 m tall |
| Racks | `rack/NE` …; `rack/NE_<remnant>` under `loop_map`; `rack/<Q>_<side>` under `rack_clearance` | `_build_rack_blocks`, `_author_loop_connectors`, `_author_rack_clearance`; 0.9 m (loop connector remnants: their configured height) |
| Aisle barrier | `aisle_barrier/north`, `/south` | `_author_aisle_barrier`, including its early return |
| Declared static obstacles | the yaml `obstacle_id` | `_author_static_obstacles` → `_author_box`, with yaw |
| Box-type timed obstacles | the yaml `obstacle_id` | `_author_obstacle`, active from `spawn_at_sec` until `remove_at_sec` (same rule as `EventScheduler`) |

The floor is excluded. `robot_visual_no_marker` timed props (the robot meshes
scaled 1.82) are not boxes. They are left out and listed by
`unmodelled_obstacle_ids`.

A shape counts against a box only if it reaches below the box top. Every box
in the current scenes is at least 0.3 m tall, so all robot shapes count.

### 2.2 Geometry

- **Rectangle–rectangle:** a separating-axis test over both rectangles' edge
  normals. Overlap returns minus the penetration depth. Separation returns
  the exact Euclidean distance (vertex to edge), so corner-to-corner
  diagonals are exact rather than an axis bound.
- **Circle–rectangle:** the exact signed distance from the centre to the
  rectangle, minus the radius.
- **Circle–circle:** centre distance minus the radii.
- **Pruning:** the exact gap is computed only where a lower bound (centre
  distance minus the 0.124 m footprint bounding radius) is below both the
  running minimum and the cutoff. The minima stay exact (tested against brute
  force).

### 2.3 Thresholds (Named Constants)

| Constant | Value | Physical meaning |
|---|---|---|
| `CONTACT_GAP_THRESHOLD_M` | 0.005 m | A pair is a contact entry when its footprint gap is at most 5 mm. The slack covers GT x/y rounding (0.1 mm), URDF primitives standing in for the USD colliders, solver rest offsets, and the jitter of a robot squaring up against a face. It was fixed before the two suspected grazes were examined. |
| `SUSTAINED_CONTACT_MIN_SEC` (recompute tool) | 1.0 s | One second of consecutive in-threshold rows separates a robot held against something from one brushing past. |
| `NEAR_CUTOFF_M` (recompute tool) | 0.02 m | Pairs within 2 cm keep their exact gap in the per-row sidecar. |

The empirical noise floor (section 5.2) is far below 5 mm. While robot_3 is
pressed against the island, the median gap is 0.0 mm and the 95th percentile
is 0.06 mm.

### 2.4 Row Schema

The existing field names and list shape are kept. Entries became objects:

```json
{
  "robot_static_contacts": [{"robot_id": "robot_3", "obstacle_id": "obstacle_2", "gap_m": -0.0001}],
  "robot_robot_contacts": [{"robot_ids": ["robot_1", "robot_2"], "gap_m": 0.0}],
  "min_static_gap_m": -0.0001,
  "min_robot_robot_gap_m": 0.0849,
  "contact_model": "urdf_footprint_v1"
}
```

- `min_static_gap_m` and `min_robot_robot_gap_m` are the unthresholded minima
  (`null` with no box or with fewer than two robots). Later analysis need not
  depend on the 5 mm threshold.
- `contact_model` is the discriminator. A row without it is a pre-2026-11-15
  stub, and its empty lists mean nothing. A row with it carries computed
  lists, so an empty list there is a computed "no pair within 5 mm".
- `min_pairwise_distance_m` is unchanged: centre to centre, as before.
- The logger computes from the rounded pose the row itself records. An
  offline recompute of a new row therefore reproduces its contact fields
  exactly (tested).
- `AcceptanceLogger.__init__` builds the box list once. A scene-geometry
  error fails before the sim loop rather than inside the runner's broad
  `except`.

The spec (`docs/specs/module6_simulation.md` §4.4, Rev 6) now records this as
implemented. Its frozen model had declared robot-id tuples and id pairs,
which were never implemented.

### 2.5 PhysX Contact Reports (Option, Not Implemented)

A physics-side detector would subscribe to contact reports on the chassis and
obstacle prims: `PhysxSchema.PhysxContactReportAPI` on the bodies, with
`omni.physx.get_physx_simulation_interface().subscribe_contact_report_events`,
or Isaac Sim's contact sensor (`isaacsim.sensors.physics`). This is a
version-sensitive API and cannot be tested here, so it was not implemented.

Two cautions:

- The runtime moves the robots under the **Newton** backend
  (`docs/implementation_notes.md`, 2026-06-21: `omni.physx.fabric` does not
  sync Newton articulations). Whether PhysX contact reports fire for Newton
  articulations at all must be checked first.
- Before any use, verify the APIs against the Isaac Sim 5.x documentation:
  "Contact Sensor" in the Isaac Sim sensors manual
  (`docs.isaacsim.omniverse.nvidia.com`, `isaacsim.sensors.physics`), and
  "Contact Reports" in the Omniverse PhysX developer guide. Neither was
  fetched for this report.

The geometric field would stay useful next to a physics detector, as a
threshold-free gap channel.

---

## 3. Always-On, Not a Flag

**Decision: always-on, with no config flag.** No pinned gate or scorer
changes its verdict between old and new logs.

| Reader | What it does with the fields | Old logs | New logs | Pinned? |
|---|---|---|---|---|
| `benchmarks/s1_scoring/bundle_io.py` (prereg-v3 A33(0) scorer) | Documented "Never read: … `robot_robot_contacts`"; neither field is referenced | n/a | n/a | yes, unaffected |
| batch-6 / tranche-1 kit scorers (`score_p10*.py`, `aggregate_b6.py`, `mc_seeds_p10.py`) | no reference (grep) | n/a | n/a | yes, unaffected |
| IB10 scoring (`score_ibs.py::gt_min_pairwise`, as cited by `v7j scripts/ib10_recede_order_precedent.py`; v3 `ib10_quick.py`, `closure_quick.py`) | contact by GT centre distance; docstrings say "never `robot_robot_contacts`" (trap 20); `score_ibs.py` itself was not opened | n/a | n/a | yes; no reference found in any worktree's `*.py` |
| `tests/simulation/test_m6_scenarios.py::_assert_no_static_contacts` | fails a scenario run on any non-empty `robot_static_contacts` | always passes (stub) | fails on a real contact, as spec §9.4 intends | no: an `isaac_sim`-marked live test, not in any gate chain; it already fails off-VM (`data/logs/vm_runs/batch6/suite/final_97d68e0_ids.txt`) |
| `scripts/ib10_recede_order_precedent.py` (v7j) | counts rows with a non-empty list, collects `json.dumps` of entries | 0 rows | counts real entries; dict entries serialize fine | no (diagnostic) |
| `v3 …/v3_step0/_analysis/ib10_lead_flip.py`, `…/s1_resume/…/s1_analyze.py` | collect or count entries (truthiness / iteration) | 0 | real entries | no (one-off analysis) |
| `tests/unit/test_m6_acceptance_logging.py` | asserted `== []` for robots ±0.2 m in the open aisle | pass | pass (no pair within 5 mm there) | n/a |
| `tests/unit/test_rescore_arrivals.py` | writes `[]` in fixtures only | — | — | n/a |

Other points:

- No reader validates GT rows against a strict schema, so the three new keys
  break nothing. Rows are no longer byte-identical to pre-change rows.
- **Reproducibility of the pinned prereg.** The pinned experiment runs from
  its tag (`569d95c` for prereg-v1; the `68e67b5` VM pin for tranche 1). That
  code still writes the stub, so its logged schema stays reproducible. This
  branch is not deployed to those runs.
- **The fc73151 ruling stands.** v1/v2 contact scoring stays a distance
  recompute. New-style values are a geometric footprint measure, unvalidated
  in Isaac. They become citable only after the live validation in section 7.

---

## 4. Tests

| File | New tests | Covers |
|---|---|---|
| `tests/unit/test_contact_geometry.py` | 44 collected: 43 pass here, 1 skipped (`pxr`) | rect–rect clear, corner-diagonal, touching, overlapping, rotated, symmetric; circle–rect clear/corner/touching/overlapping/rotated; circle–circle; footprint reach (wheels 0.089, nose 0.038, bounding radius); lidar and caster inside the chassis; the m5D pin pose (0.838, 0.572, π) gives 0 against `obstacle_2`; robot rotated 90°; height filter; nose-to-nose at 0.076 m gives 0; side by side; frame entries for overlapping vs clear, two boxes at once, threshold boundary, exact minimum under pruning, robot pairs, timed-box window; scene boxes for default, rack clearance, loop map, barrier (and its early return), timed and robot-visual obstacles; **rasterized parity with `isaac/scripts/generate_warehouse_map.build_occupancy_grid` for five scene configurations**; USD builder parity (skipped without `pxr`; runs on the kit) |
| `tests/unit/test_m6_acceptance_logging.py` | +5 | logger writes a static entry when a robot overlaps a box; empty lists with numeric minima and `contact_model` when clear; robot-robot entry nose to nose; `min_pairwise_distance_m` unchanged; offline recompute of a written row reproduces its fields |
| `tests/unit/test_recompute_gt_contacts.py` | 5 | sustained vs brief vs clear classification; CLI writes sidecars and leaves the bundle byte-identical; refuses an output directory inside a bundle |

**Unit suite** (`pytest tests/unit --continue-on-collection-errors`):

| | Passed | Failed | Skipped | Collection errors |
|---|---|---|---|---|
| Before (`8933863`) | 6967 | 57 | 151 | 3 (`pxr`) |
| After | 7020 | 57 | 152 | 3 (`pxr`) |

- The sorted failing and erroring test ids are identical before and after
  (diffed). Nothing new fails.
- The +53 passes and +1 skip are the 54 new tests.
- The 57 pre-existing failures are ArUco parity (49), `test_t2b_forced_order`
  (3), `test_m6_validation` (2), and one each in the M5 congestion detector,
  the M5 reasoning pipeline and `test_m6_config`.
- Lint: `ruff check` passes on every new or changed file. Other `isaac/vgu_sim`
  files carry pre-existing findings, which were not touched.

---

## 5. Recompute Over Recorded Bundles

Command (read-only on bundles; summaries committed, per-row sidecars, 28 MB, not committed):

```bash
xargs python scripts/recompute_gt_contacts.py \
  --out-dir data/experiments/2026-11-15-gt-contact-recompute --rows < bundles.txt
```

`bundles.txt` lists 44 bundles, with `_backup_*` excluded:

- the 11 demo-campaign attempts (`v7j …/demo_campaign/{ib,cv,ho,m5}/runs/`);
- the 11 IB10 live bundles (`v7a …/ib10_live/runs/`);
- the 11 IB10 safety bundles (`v7d …/ib10_safety/runs/`);
- the 11 tranche-1 bundles E27–E31 (`v3 …/batch6/s1b_E*`).

Every bundle had `gt/ground_truth.jsonl`, `scenario.yaml` and `theta` (yaw) in
every row. Every scenario parsed with the current `ScenarioConfig`, and none
has timed obstacles. In all 44 bundles the logged contact lists are empty on
every row, and no row has `contact_model`: they are the stub.

Outputs are in `data/experiments/2026-11-15-gt-contact-recompute/`: one
`<label>.summary.json` per bundle plus `index.json`.

### 5.1 Results per Bundle

Gaps are footprint to footprint, in millimetres. "Static" covers walls, racks,
barrier blocks and declared obstacles. The intersection scenes declare no
obstacles, but their rack blocks and walls are boxes and are included.

| Group | Bundle | Rows | Static verdict | Min static gap (robot, box, sim s) | Robot–robot verdict | Min robot–robot gap (pair, sim s) |
|---|---|---|---|---|---|---|
| demo | `cvD_t01_a1` | 2601 | clear | 103.0 (r4, `aisle_barrier/north`, 65.0) | clear | 195.0 (r1/r2, 67.2) |
| demo | `cvD_t02_a1` | 2601 | clear | 137.3 (r1, `rack/NW`, 53.9) | clear | 176.3 (r1/r2, 25.7) |
| demo | `cvD_t03_a1` | 2601 | clear | 96.8 (r4, `aisle_barrier/north`, 65.5) | clear | 190.1 (r1/r2, 26.1) |
| demo | `hoD_t01_a1` | 3001 | clear | 44.5 (r2, `aisle_barrier/north`, 121.0) | clear | 138.8 (r1/r2, 22.3) |
| demo | `ibD_t01_a1` | 585 | clear | 511.0 (r1, `rack/NW`, 0.0) | clear | 2302.5 (r2/r3, 34.3) |
| demo | `ibD_t01_a2` | 3001 | clear | 136.4 (r1, `rack/NW`, 56.3) | clear | 191.6 (r1/r2, 76.1) |
| demo | `ibD_t02_a1` | 3001 | clear | 131.0 (r1, `rack/SW`, 74.9) | clear | 135.6 (r2/r4, 28.7) |
| demo | `ibD_t03_a1` | 3001 | clear | 93.6 (r1, `rack/NW`, 130.5) | clear | 153.8 (r2/r3, 28.0) |
| demo | `ibD_t04_a1` | 3001 | clear | 129.3 (r1, `rack/SW`, 72.8) | clear | 147.6 (r2/r3, 28.2) |
| demo | `ibD_t05_a1` | 3001 | clear | 129.4 (r1, `rack/SW`, 73.8) | clear | 149.0 (r1/r4, 27.9) |
| demo | **`m5D_t01_a1`** | 6001 | **sustained contact** | **−0.2 (r3, `obstacle_2`, 191.4)** | clear | 85.0 (r1/r4, 42.6) |
| IB10 live | `ib10L_e01_armA_a1` | 3001 | clear | 103.5 (r1, `rack/NW`, 131.9) | clear | 152.0 (r1/r3, 28.2) |
| IB10 live | `ib10L_e01_armA_a2` | 3001 | clear | 132.3 (r1, `rack/SW`, 72.8) | clear | 156.8 (r2/r3, 27.7) |
| IB10 live | `ib10L_e02_armB_a1` | 3001 | clear | 504.9 (r3, `rack/SE`, 23.3) | clear | 140.0 (r1/r4, 27.6) |
| IB10 live | `ib10L_e03_armA_a1` | 3001 | clear | 128.5 (r1, `rack/SW`, 126.6) | clear | 145.0 (r2/r4, 26.5) |
| IB10 live | `ib10L_e04_armB_a1` | 3001 | clear | 496.5 (r3, `rack/SE`, 24.1) | clear | 126.8 (r2/r3, 27.7) |
| IB10 live | `ib10L_e05_armA_a1` | 3001 | clear | 108.7 (r1, `rack/NW`, 131.4) | clear | 139.5 (r1/r4, 28.6) |
| IB10 live | `ib10L_e06_armB_a1` | 3001 | clear | 487.6 (r3, `rack/SE`, 23.4) | clear | 157.5 (r2/r3, 27.4) |
| IB10 live | `ib10L_e07_armA_a1` | 3001 | clear | 101.3 (r1, `rack/NW`, 130.4) | clear | 172.9 (r2/r3, 28.1) |
| IB10 live | `ib10L_e08_armB_a1` | 3001 | clear | 497.2 (r3, `rack/SE`, 24.6) | clear | 151.1 (r1/r4, 27.3) |
| IB10 live | `ib10L_e09_armA_a1` | 3001 | clear | 121.9 (r1, `rack/NW`, 57.5) | clear | 82.1 (r1/r2, 295.4) |
| IB10 live | `ib10L_e10_armB_a1` | 3001 | clear | 490.1 (r3, `rack/SE`, 21.8) | clear | 163.1 (r2/r3, 27.5) |
| IB10 safety | `ib10S_e01_armA_a1` | 3001 | clear | 95.9 (r1, `rack/NW`, 129.7) | clear | 121.7 (r3/r4, 109.4) |
| IB10 safety | `ib10S_e02_armC_a1` | 3001 | clear | 171.0 (r1, `rack/SW`, 283.6) | clear | 1772.2 (r2/r3, 43.7) |
| IB10 safety | `ib10S_e02_armC_a2` | 3001 | clear | 115.8 (r1, `rack/NW`, 131.9) | clear | 149.6 (r1/r4, 27.5) |
| IB10 safety | `ib10S_e03_armA_a1` | 3001 | clear | 125.0 (r1, `rack/SW`, 71.8) | clear | 155.0 (r2/r3, 27.3) |
| IB10 safety | `ib10S_e04_armC_a1` | 3001 | clear | 130.2 (r1, `rack/SW`, 74.1) | clear | 157.3 (r2/r3, 27.0) |
| IB10 safety | `ib10S_e05_armA_a1` | 3001 | clear | 125.0 (r1, `rack/SW`, 73.6) | clear | 162.3 (r2/r3, 28.1) |
| IB10 safety | `ib10S_e06_armC_a1` | 3001 | clear | 128.1 (r1, `rack/SW`, 74.2) | clear | 159.8 (r2/r3, 27.3) |
| IB10 safety | `ib10S_e07_armA_a1` | 3001 | clear | 130.7 (r1, `rack/SW`, 71.0) | clear | 134.9 (r2/r3, 26.1) |
| IB10 safety | `ib10S_e08_armC_a1` | 3001 | clear | 129.4 (r1, `rack/SW`, 73.5) | clear | 201.5 (r1/r2, 89.8) |
| IB10 safety | `ib10S_e09_armA_a1` | 3001 | clear | 110.0 (r1, `rack/NW`, 132.3) | clear | 185.0 (r1/r3, 29.4) |
| IB10 safety | `ib10S_e10_armC_a1` | 3001 | clear | 130.5 (r1, `rack/SW`, 75.0) | clear | 142.3 (r2/r3, 27.9) |
| tranche 1 | `E27 A a1` | 6001 | clear | 34.8 (r1, `obstacle_1`, 99.8) | clear | 221.9 (r1/r5, 581.7) |
| tranche 1 | `E27 B a1` (bring-up abort) | 670 | clear | 97.9 (r4, `rack/SW_west`, 37.8) | clear | 1922.8 (r1/r2, 29.4) |
| tranche 1 | `E27 B a2` | 6001 | clear | 34.7 (r5, `obstacle_2`, 50.4) | clear | 215.8 (r3/r4, 46.9) |
| tranche 1 | `E28 A a1` | 6001 | clear | 28.1 (r5, `rack/SE_east`, 104.4) | clear | 223.5 (r1/r5, 45.5) |
| tranche 1 | `E28 B a1` | 6001 | clear | 41.1 (r1, `obstacle_2`, 42.5) | clear | 101.1 (r1/r5, 44.8) |
| tranche 1 | `E29 A a1` | 6001 | clear | 7.1 (r2, `obstacle_2`, 42.8) | clear | 133.4 (r1/r4, 46.4) |
| tranche 1 | `E29 B a1` | 6001 | clear | 14.0 (r1, `obstacle_1`, 38.8) | clear | 119.4 (r1/r4, 46.1) |
| tranche 1 | **`E30 A a1`** | 6001 | **brief graze** | **1.0 (r2, `obstacle_1`, 48.9)** | clear | 231.7 (r3/r4, 44.9) |
| tranche 1 | `E30 B a1` | 6001 | clear | 10.0 (r2, `obstacle_1`, 47.9) | clear | 169.1 (r3/r4, 43.3) |
| tranche 1 | `E31 A a1` | 6001 | clear | 19.3 (r2, `obstacle_2`, 44.3) | clear | 178.9 (r1/r5, 577.2) |
| tranche 1 | `E31 B a1` | 6001 | clear | 8.7 (r2, `obstacle_2`, 42.0) | clear | 209.3 (r1/r5, 41.2) |

Totals:

- **Robot–static:** 1 sustained contact, 2 brief grazes (one of them in
  `m5D_t01_a1`, beside the sustained contact), 42 bundles clear.
- **Robot–robot:** no footprint contact in any bundle. The closest pair is
  82.1 mm, in `ib10L_e09_armA_a1`.

Short bundles (`ibD_t01_a1`, 585 rows; tranche-1 E27 B a1, 670 rows) and
`ib10S_e02_armC_a1` have robot–robot minima above 1.7 m. Those runs ended
early or never brought robots together. That was not examined further here.

### 5.2 The Known Positive: `m5D_t01_a1` robot_3 vs `obstacle_2`

**Sustained contact.**

- From sim 146.7 s to 600.0 s, 4526 of 4534 rows are within 5 mm. The
  minimum is −0.16 mm, at 191.4 s.
- The in-contact rows form four events:
  - 146.7–266.4 s: 1198 rows, median gap 0.0 mm, speed at most 0.09 m/s;
  - 266.6 s: 1 row, 4.8 mm;
  - 266.8–267.4 s: 7 rows, minimum 0.06 mm;
  - 268.1–600.0 s: 3320 rows, median 0.02 mm, maximum 0.1 mm.
- The 8 rows outside 5 mm are 266.5 s (5.9 mm), 266.7 s (5.5 mm) and
  267.5–268.0 s (8.1 to 13.45 mm). This is while the line-hold servo turned
  the robot against the face, its heading swinging from −1.57 to −3.07 rad.
- **Empirical noise floor:** while the robot is pressed against the face, the
  gap is at most 0.1 mm in the last event, and the 95th percentile over all
  in-contact rows is 0.06 mm. Isaac held the contact at essentially zero gap,
  so the 5 mm threshold is generous, not tight.

**Regression against §8.7.2 (the ad hoc 5 mm-sampled recompute).**

- Reproduced:
  - 4526 of 4534 rows within 5 mm from 146.7 s;
  - the −0.2 mm minimum (−0.16 mm here);
  - 8 exception rows with a 13.5 mm maximum (13.45 mm here);
  - robot_2 at 3.8 mm at 270.7–270.9 s (270.7–271.0 s here).
- Differs: §8.7.2 dates the exception rows 266.5–267.7 s. Here they run to
  268.0 s (rows 267.8–268.0 s at 13.45, 9.4 and 7.0 mm). The count and the
  maximum agree, so the earlier span reads as approximate.

The convoy minimum is 96.8 mm here, against §8.7.4's 0.097 m. The tranche-1
minima are at least 7 mm except E30 Arm A (7.1 mm in E29 A), as §8.7.4 found.
E30 A comes out at 0.97 mm here, against §8.7.4's 1.2 mm. The 0.2 mm
difference is that recompute's 5 mm sampling; this one is exact.

### 5.3 The Two Suspected Grazes

Both are classified **brief graze within noise, not established contact.**

| | `m5D_t01_a1` robot_2 vs `obstacle_2` | tranche-1 E30 Arm A robot_2 vs `obstacle_1` |
|---|---|---|
| Rows within 5 mm | 4 (270.7–271.0 s, span 0.4 s) | 7 (48.6–49.2 s, span 0.7 s) |
| Minimum gap | 3.79 mm at 270.8 s | 0.97 mm at 48.9 s |
| Gap profile | 6.4 → 5.0 → 4.2 → **3.8** → 4.0 → 4.5 → 5.6 mm | 3.6 → 2.2 → 1.3 → **1.0** → 1.2 → 1.7 → 3.6 mm |
| Speed through the event | 0.13–0.17 m/s, no dip | 0.13–0.17 m/s, no dip |
| Heading | turning steadily, 0.59 → 0.33 rad (about −0.4 rad/s) | turning steadily, 0.57 → 0.34 rad (about −0.4 rad/s) |
| What happens | rounding the island's north-west corner (x 0.25, y 0.70) on the way east, under Nav2 | rounding the island's north-west corner (x −1.30, y 0.90), under Nav2 |
| Row resolution (speed × 0.1 s) | 16.5 mm | 17.0 mm |

Why not contact:

- Both minima are positive.
- Each gap profile is a smooth parabola across the rows. The robot sweeps
  tangentially past a corner, so the unsampled minimum is close to the
  sampled one.
- There is no kinematic signature of contact: the speed does not collapse,
  the turn rate does not change, and the heading does not square up.
- But both are inside the 5 mm threshold and within the URDF-vs-USD collider
  uncertainty. A real touch cannot be ruled out either.
- Scale: both sit inside the 5 mm model-fidelity threshold, but 10× (0.97 mm)
  and 38× (3.8 mm) above the pressed-contact floor of at most 0.1 mm measured
  in section 5.2.
- The threshold was set in code before the recompute ran. The brief had
  already given the approximate graze values (about 1.2 mm and 3.8 mm), so
  this is not a blind choice.

E30 Arm B passed the same corner at a 10.0 mm minimum (47.8–47.9 s).

---

## 6. What the New Values Support

- **Supported:** a planar footprint proximity of each robot to each authored
  box and to each other robot. It is exact for the URDF primitives at the
  logged pose, to 0.1 mm.
- **Not supported:**
  - A physics contact force, or that the solver registered contact.
  - Contact by the imported USD colliders, if they differ from the URDF
    primitives.
  - Ride-up or tilt.
  - Contact between GT rows: at 10 Hz a moving robot travels
    `speed × 0.1 s` between rows, which the tool reports per event.
- A brief, millimetre-level graze of a moving robot is not established
  contact. A sustained in-threshold run with the robot stopped is strong
  evidence of contact, as in `m5D_t01_a1`, where the overhead recording
  agrees.

---

## 7. Limits and Deployment

### 7.1 Limits

- The geometric approximation uses the URDF collision primitives. The
  imported USD (`turtlebot3_burger.usda`) colliders were not inspected here.
- Planar only: robots are treated as upright, and the robot shapes reach at
  most 0.191 m, which is below every current box top.
- The scene boxes mirror the builders' arithmetic. Parity with the map
  generator was verified here. The USD-builder parity test needs `pxr` and
  has not been run.
- Bundles do not record `WarehouseConfig`. Both builders and this module use
  its defaults, which equal `isaac/config/warehouse.yaml`.
- `robot_visual_no_marker` props are not modelled. A computed empty list in
  a scene with such a prop (blocked-path scenes) says nothing about contact
  with it. None of the recomputed bundles has timed obstacles.
- **No real-data positive control for robot–robot.** The static path is
  anchored by m5D. The robot–robot path is tested only on synthetic poses:
  nose to nose at 0.076 m, and side by side. "No robot–robot footprint
  contact in any bundle" has not been checked against a recorded robot–robot
  contact. Candidates are the 2026-09-25 G4/K1 wedge bundles, or the IB10
  lead-flip bundle with a 0.084 m centre distance; neither was among the
  bundles run here.
- The map-generator parity is cell-level (0.05 m); see Scope.
- **Not validated in Isaac Sim.** A live run is needed to confirm that
  logged entries appear when a robot is pinned, and that the per-row cost
  does not slow the sim loop measurably. Offline, about 6000 rows of a
  five-robot scene take about 7 s, roughly 1.1 ms per row against a 100 ms
  logging period.

### 7.2 What a Kit Needs to Deploy It

- Ship `isaac/vgu_sim/contact_geometry.py` with the changed
  `isaac/vgu_sim/acceptance_logging.py`. They have no new dependency: the
  stdlib and `isaac.vgu_sim.config` only.
- Nothing in `runner.py` changes. `AcceptanceLogger(gt_file, scenario)` builds
  the boxes itself.
- Rebuilding the scenario USD is not needed: the geometry comes from the
  scenario yaml, not the USD.
- On the kit, run `pytest tests/unit/test_contact_geometry.py` with `pxr`
  available, so the USD-builder parity test runs too.
- In a validation run, check `contact_model` in the GT rows. Then check a
  scripted drive into a box: entries are expected within 5 mm, and gap ≈ 0
  while pressed.
