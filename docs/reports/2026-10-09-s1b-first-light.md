# S1b First Light: Sparse-Warehouse Floor, Monte Carlo Gate from S1a Data, and a Failed Live Pass Check

**Prepared:** 2026-10-10

**Revision history:**

- Initial draft: S1b Phase 1 (floor, nodes, map, Monte Carlo gate derived from S1a data, scene and tests) and Phase 2 on the new VM. The Phase 2 live pass check latched, so by the pre-registered rule the program stopped before the M1 coverage session, the free-flow legs, the S1b pilot and the S1a mini-program.

---

## Summary

S1b is the sparse-warehouse regime variant of S1 (prereg-v3 R3.6 and R3.6a). It keeps S1a's tracked band, removes the racks and adds two short rack islands.

**Phase 1 (offline) is done, and the derived Monte Carlo gate passes 6/6.**

- **Gate.** The six gates (event presence, timing, regime distinctness, Δ artifact, geometric resolvability, ≥3-robot contacts) are derived from S1a's own Monte Carlo and live data.
- **Machinery.** The S1a Monte Carlo was rebuilt and committed (`scripts/s1_mc.py`). It reproduces S1a's published row.

Phase 1 also raised three findings that change how the result should be read.

- **Δ is 2.5 sim-s, not the brief's 4.0.**
  - R3.6a requires Δ to be recomputed for the new layout, and the recompute gives Δ < 2.67.
  - On this floor Δ = 4.0 makes 41/400 first conflicts (10.3 %) release artifacts.
  - The regime axis therefore differs in Δ as well as in floor.
- **The current M3 grounds an executable yield for only about 0.4 of first conflicts. That is a capability limit, not a floor property.** The open floor makes a single yield geometrically possible in 0.82 of first conflicts. But when the echo mock asks, the real `ground_reasoner_result` grounds an executable yield in only 0.405 of them (S1a: 0.345). The rest fails two ways:
  - **Refusals.** Diagonal open-floor headings fall into the `dynamic_arms:ambiguous` refusal.
  - **No-ops.** The room gate keeps a yielder that the retreat sweep then refuses, which produces empty `reroute` no-ops.
- **Latch-cluster risk is not reduced by geometry alone.** Without Layer 2, a ≥3-robot cluster forms within 60 sim-s of the first encounter in 346/400 S1b draws, against 360/400 on S1a.

**Phase 2: the R3.6a make-or-break live pass check FAILED, so the program stopped.**

- **What happened.** Two robots met head-on in the narrowest shared gap (0.90 m) and latched at an M1 gap of 0.423 m. They froze 0.286 m apart (GT) to the horizon.
- **The rule.** This was the one pre-registered attempt, with 0 STALE rows, so it is a FAIL, not a VOID.
- **The prior held.** In the three S1a bundles, 0 of 4 opposing approaches cleared 0.45 m.

| Question | Answer |
|---|---|
| Gate verdict | **PASS 6/6** on derived thresholds (PROPOSED for Step 6); see [MC Gate](#4-monte-carlo-gate-derived-from-s1a-data) |
| Regime-axis density (per agent, 0.55 m cells) | nominal S1a **5.44** / S1b **10.74**; post-inflation (cost < 253) **5.02 / 10.02**; zero-cost 4.59 / 9.35 |
| Pass check | **FAIL**. Latch at an M1 gap of 0.423 m (GT 0.445 m); stopped at 0.286 m with 0.151 m lateral offset; 0 STALE |
| Resolution events (the planned headline) | **None measured**: the pilot was not run. Offline expectation: 0.405 executable per first conflict |
| Wandering vs park (S1-1) | **Still undecided.** No episode ran |
| S1a anchor (mini-program) | **Not run.** Seeds 3–5 are staged (USD and overlays) on the VM |
| Branch / merge | `feat/v3-s1b`, merged into `feat/v3-integration` (see [Commits and Merge](#9-commits-merge-and-suite)) |
| API spend | **$0** |
| VM | RUNNING, idle, clean (see [VM End State](#8-vm-end-state)) |

This is **pilot-only** work: RECORD = 0, and nothing here enters a scored dataset.

---

## 1. Floor and Corridors

### New primitive: `rack_clearance`

No existing block could remove racks. `loop_map` only re-authors the NE quadrant, and `aisle_barrier` and `static_obstacles` only add geometry. So one default-off scenario key was added, following the loop-map pattern.

- **Config.** `RackClearanceConfig` plus `rack_clearance_remnants` in `isaac/vgu_sim/config.py`.
- **USD.** `scenario_builder._author_rack_clearance` deactivates all four `/World/Environment/RackBlocks/*` cubes with an `over` and re-authors the remnants outside the rectangle. The warehouse USD is never edited. `validation.validate_rack_clearance` checks the result at build time.
- **Map.** `generate_warehouse_map.rasterize_rack_clearance` frees the identical cells.
- **Dumps.** `ScenarioConfig` omits the key from dumps when it is unset, because the head-on family YAMLs are byte-compared.
- **Regression check.** All 32 committed maps regenerate byte-identical.

### S1b floor

| Item | Value |
|---|---|
| Band | \|x\| ≤ 2.5, \|y\| ≤ 1.8 (S1a's), cleared of racks. The edge is the rack remnants' faces, except the two aisle stubs, which are dead ends as in S1a |
| Islands | Two static obstacles, 0.55 × 1.60 × **0.30 m**: W at x [−1.30, −0.75], y [−0.70, +0.90]; E at x [+0.25, +0.80], y [−0.90, +0.70]. They are staggered (a chicane) and shifted 0.25 m west |
| Height | 0.30 m is the loop-map connector-remnant precedent. It sits above the 0.182 m lidar plane. The camera shadow beyond an outer face is 0.033 r ≤ 0.05 m, against 0.43–0.53 m for a 0.9 m rack |
| Coverage | 2 × 0.55 × 1.60 = 1.76 m², which is **9.78 %** of the 18 m² band (S1a: 54.3 %) |
| Map | `ros2_ws/src/swarm_simulation/maps/warehouse_map_mapd_5_s1b.{pgm,yaml}`, pinned byte for byte by the regen test |

### Corridor arithmetic (R3.6a item 1)

Two passing robots need a centre separation of at least 0.45 m (the M4 latch).

- **Wall clearance.** Each centre must keep its 0.18 m chassis outside the 0.10 m global inflation, so it sits at least 0.09 + 0.10 = 0.19 m off the face.
- **Quantization.** One 0.05 m costmap cell is added.
- **Result.** W_min = 0.45 + 2 × 0.19 + 0.05 = **0.88 m**, inside R3.6a's 0.85–0.90 m.

Widths below were measured on the map's costmap at mid-span (`scripts/s1b_layout.py`).

| Gap | W (m) | cost < 253 (m) | cost = 0 (m) |
|---|---|---|---|
| West wall ↔ island_w | 1.20 | 1.15 | 1.10 |
| island_w ↔ island_e | 1.00 | 0.90 | 0.80 |
| island_e ↔ east wall | 1.70 | 1.65 | 1.60 |
| island_w ↔ north wall | **0.90** | 0.80 | 0.70 |
| island_w ↔ south wall | 1.10 | 1.00 | 0.90 |
| island_e ↔ north wall | 1.10 | 1.05 | 1.00 |
| island_e ↔ south wall | **0.90** | 0.85 | 0.80 |

Every gap is ≥ 0.90 m, which clears W_min. Every zero-cost band is ≥ 0.70 m, which clears 0.45 m. That is the geometric claim. [§5](#5-phase-2-live-pass-check-r36a-acceptance) shows that it is not sufficient.

---

## 2. Regime-Axis Table

The free area is inside the band, divided by N_A = 5. "Nominal" means geometric, before inflation. "Post-inflation" counts the band cells of the Nav2 global costmap.

The inflation model was checked against the live S1a global-costmap dump (`s1_pilot/evidence_ep1_r3_corner`):

- cells ≤ 0.0707 m from an occupied cell read INSCRIBED;
- cells at 0.10 m read 80/100;
- cells beyond read 0.

| Floor | Obstacle in band | Nominal free m² | per agent, 0.55 m cells | per agent, 0.45 m cells | Post-infl. cost < 253 m² (0.55 / 0.45 per agent) | Post-infl. cost = 0 m² (0.55 / 0.45 per agent) | Δ (sim-s) | Conflict regime |
|---|---|---|---|---|---|---|---|---|
| S1a (`mapd_5`) | 9.77 m², 54.3 % | 8.23 | **5.44** | 8.13 | 7.59 (5.02 / 7.50) | 6.94 (4.59 / 6.85) | 4.0 | deterministic single-lane |
| S1b (`mapd_5_s1b`) | 1.76 m², 9.78 % | 16.24 | **10.74** | 16.04 | 15.16 (10.02 / 14.97) | 14.14 (9.35 / 13.97) | **2.5** | open floor, stochastic |

- **Regime, not density.** The pair is a regime axis (R3.6a item 2).
- **Δ differs too.** The Δ column is part of that difference. S1a's 4.0 is not usable on S1b (see [§3](#3-nodes-legs-and-the-release-stagger)).

---

## 3. Nodes, Legs and the Release Stagger

S1a's labels and forbidden pair are kept. Every seed therefore draws the **identical** start assignment and 25-task stream on both floors, and the regime axis is paired by seed (test `test_seed_draws_are_identical_on_both_floors`). The positions are new and **lane-aligned**: Wp–N and Wm–S run along the two island_w gaps, and N–S runs down the inter-island corridor.

| Node | (x, y) | Yaw | Placement |
|---|---|---|---|
| Wp | (−2.30, +1.35) | 0 | West wall; north-gap centreline |
| Wm | (−2.30, −1.35) | 0 | West wall; the mirror (0.10 m south of the south gap's centreline) |
| N | (−0.25, +1.35) | −π/2 | North-gap lane, over the inter-island corridor |
| S | (−0.25, −1.35) | +π/2 | South-gap lane, under the inter-island corridor |
| E | (+2.30, 0.00) | π | East, in front of the E aisle stub |

- **Separation.** The minimum pairwise distance is 2.05 m, more than 4× the 0.5 m handoff/arrival radius. No node sits in another's handoff radius.
- **Envelope.** Every node is inside S1a's node envelope, off the band corners, and away from marker 1's STALE pose (−1.75, 0).
- **Forbidden leg Wp↔Wm: kept for seed pairing only.**
  - The S1b leg is 2.70 m, so S1a's geometric reason (a 0.70 m leg) does not apply.
  - Dropping it is a one-line change. It breaks the pairing and regenerates every seed's draw.
- **Legs** (m; grid router):
  - Wp–N 2.05 and Wm–S 2.05;
  - N–S 2.70;
  - E–N 2.89–2.91 and E–S 2.91–2.96;
  - S–Wp 3.57 and N–Wm 3.68;
  - E–Wp 4.85–4.95 and E–Wm 4.93–5.02.
- **Shared corridors.** At least 3 routes traverse a gap end to end, with no endpoint inside it:
  - island_w ↔ north wall: N–Wp, N–Wm, E–Wp;
  - island_w ↔ south wall: S–Wp, S–Wm, E–Wm;
  - west wall ↔ island_w: N–Wm, S–Wp.
- **Δ (R3.6a recompute).**
  - The bound is 4Δ < (L_min − 0.45) / v = (2.05 − 0.45) / 0.15 = 10.67 sim-s, so Δ < 2.67.
  - **Δ = 2.5** is 0.94 of the bound (S1a: 4.0 = 0.90 of 4.42).
  - The MC-measured Δ artifact is 0/400. On the S1b islands, S1a's Δ = 4.0 gave 41/400.
  - **This overrides the brief's "sim stagger 4.0"** on R3.6a's recompute rule.

### Grounding file

`config/grounding/s1b_dynamic.yaml` differs from S1a's `s1_dynamic.yaml` **only** in its two aisle bands, and a test pins that.

- **Why S1a's bands fail here.** They are [−0.46, 0.46], and they veto every S1b retreat away from the E–W centreline. A synthetic south-gap head-on grounds a 1.30 m yield with S1b's bands and `retreat=no-valid-candidate` with S1a's (pinned as a test).
- **S1b's bands.** They are the band minus the 0.14 m chassis margin: y ±1.66 and x ±2.36.
- **Declared corridor.** It stays S1a's box, because `aisle_half_width_m` sets the dynamic-lane sidestep (0.6 − 0.24 = 0.36 m). Declaring the whole band gave a 1.56 m sidestep.
- **Fences.** The overlay declares the islands plus four M3-only band-edge fences. These generalise S1a's aisle-mouth end caps, since the racks no longer bound the band.

---

## 4. Monte Carlo Gate, Derived from S1a Data

### Machinery and reproduction

S1a's MC ran from a scratchpad and was never committed. `scripts/s1_mc.py` rebuilds it with the assumptions the scene doc states:

- 0.15 m/s on piecewise-linear routes;
- 5 s dwell;
- an encounter is a centre gap < 0.45 m, after which both robots freeze;
- the shipped `task_stream` draws.

Routes come from either the scene doc's hand routes or a NavFn-like grid router on the inflated costmap.

| S1a published row (scene doc, row D) | Rebuilt MC, 400 draws (two seed sets) |
|---|---|
| ≥ 1 encounter 400/400 | 400/400 |
| First encounter median 15.0, p90 17.3 sim-s | 13.6–14.9, 17.3–17.4 |
| Junction share 309/400 | 303–315/400 |
| Encounters per episode 3.85 (994/1538 into frozen robots) | 3.63–3.67 (916/1458) |
| Kinds crossing 279 / head-on 121 | 268–284 / 115–131 |
| Free-flow makespan median 177 (p10 171, p90 185) | 176.8 (170.5, 185.8) |
| Arrivals onto an occupied node 3.2 | 3.3 |

- **One deviation.** Wander legs are 1.5 vs 3.5 per episode; the published re-wander rule is not stated. It does not affect first conflicts.
- **Router choice.** The grid router fits the live S1a first-conflict *places* better than the hand routes. Live: 0/3 at the junction (2 at the E bay, 1 in the S strip). The hand routes put 77 % there; the grid router puts 20 % there. S1a vs S1b comparisons therefore use the same grid router.

### Live S1a inputs (same encounter definition, GT)

From `scripts/s1_live_conflict_stats.py` on the three bundles. Times are from robot_1's release.

| Bundle | First encounter | Pairs ever < 0.45 m | Permanent (to H) | ≥ 3-robot cluster |
|---|---|---|---|---|
| ep1 (pilot, wall-clock stagger) | 20.5 sim-s | 3 | 3/3 | at 338 s |
| E1 (seed 1, echo) | **17.94** | 3 (4 intervals) | 2 (2 transient: the cb78 yield) | none |
| E2 (seed 2, echo) | **18.74** | 4 | 4/4 | at **25.4** s |

The M1 latch onsets match GT within 0.1 s: E2 first latch at 40.07 absolute M1 sim-s.

### Thresholds and result

Draws are 400 (seeds 1..400), park finishers, Δ = 2.5. The threshold derivations are frozen in the `mapd_5_s1b.yaml` header as PROPOSED for Step 6.

| Gate | Quantity | Derivation | Threshold | S1b | Pass |
|---|---|---|---|---|---|
| G1 | P(≥ 1 encounter in H) | ≥ 1 event per episode, with E[event-free episodes] ≤ 0.5 in an R = 20 cell: 1 − 1/(2R) | ≥ 0.975 | 1.000 | yes |
| G2 | First-encounter p90 | Lag k = max(17.94, 18.74)/15.0 = 1.249; k·p90 ≤ H − 300 sim-s stop window | ≤ 240.1 | 20.1 | yes |
| G3 | Largest share of first conflicts in any 1.2 × 1.2 m window | Below S1a's own share under the same router (grid 0.445; registered hand-route MC 0.773) | < 0.445 | 0.275 | yes |
| G4 | Δ-artifact share of first conflicts | S1a 0/400; tolerance = G1's 1/(2R) | ≤ 0.025 | 0.000 | yes |
| G5a-geo | First conflict geometrically resolvable by one yield (a member has ≥ 1.7 − gap m of clear rear room) | A 2-episode pilot shows one with P ≥ 0.95: q ≥ 1 − √0.05 | ≥ 0.776 | 0.818 | yes |
| G5b | ≥ 3-robot < 0.45 m contact onsets per episode, pass-through run | Below S1a's own rate (E2's cluster pattern) | < 3.31 | 2.55 | yes |

**Other S1b first-conflict figures:**

- **Timing.** Median 12.0 sim-s (p10 8.0).
- **Kinds.** Head-on 334, crossing 35, same-direction 19, static 12.
- **Hotspots** (0.5 m cells):

  | Cell | First conflicts |
  |---|---|
  | (−1.5, −1.5) | 43 |
  | (−1.5, +1.0) | 40 |
  | (−2.0, −0.5) | 31 |
  | (−1.0, +1.0) | 31 |
  | (−1.0, −1.5) | 29 |
  | (−0.5, +1.0) | 29 |

  These are the two island_w gaps and the west passage. By named region: south gap 81, north gap 78, open 71, west passage 69, east passage 35.

### Grounded executability: reported, not gated (an M3 limit)

G5a-geo asks whether the floor allows a resolving yield. The M3 question is answered separately by `scripts/s1_grounding_replay.py`. It replays each first-conflict scene 2.5 sim-s after the encounter through the real `ground_reasoner_result`, with:

- the decision the echo mock would send: stalled robots in `id_asc` order, the first one as yielder;
- each floor's overlay, boxes and grounding file;
- swap mode.

| Floor | Executable yield | Empty `reroute` (no-op) + 15 s wait | Refused (of which `ambiguous`) | Pulled in to 0.35 m |
|---|---|---|---|---|
| S1b, lane-aligned (shipped) | **0.405** | 0.310 | 0.285 (0.200) | 0.405 |
| S1b, first layout (diagonal routes) | 0.247 | 0.218 | 0.535 (0.463) | 0.245 |
| S1a | 0.345 | 0.415 | 0.240 (0.200) | 0.325 |

There are two mechanisms, and both are M3 behaviour on any floor.

- **The ambiguous fallback.** A heading more than 30° off both axes falls back to declared geometry, which refuses (A14(iii)). Open-floor diagonal routes put 46 % of first conflicts there. The nodes were lane-aligned to bring that down to 20 %.
- **The room-gate / sweep mismatch.** The swap gate's 0.95 m room requirement keeps a yielder whose retreat sweep then needs 1.7 − gap ≈ 1.3 m and finds no candidate. The gate never swaps to the partner that has the room. M4 executes the resulting empty `reroute` as a no-op (`command_bus_node` returns False), and `refusal_no_action` does not withhold it.

**Pilot expectation:** P(≥ 1 executable first-conflict yield in 2 episodes) = 1 − 0.595² ≈ 0.65.

### Latch-cluster risk: transient vs permanent exposure

| Measure (400 draws) | S1a (grid) | S1b |
|---|---|---|
| ≥ 3-robot frozen cluster within 60 sim-s of the first encounter, Layer-2-off | 360 | **346** |
| The same, robots replanning around frozen robots (Nav2-like) | 336 | 314 |
| Median lag, first encounter → 3-cluster (sim-s) | 11.3 (23.6 rerouting) | 19.2 (30.3 rerouting) |
| Encounters geometrically single-yield resolvable (all, not only first) | 0.58 | 0.76 |
| Pass-through contacts per episode | 20.2 | 17.0 |
| Head-on contacts per episode | 11.1 | 8.0 |
| Node-handoff (static) contacts per episode | 4.9 | 6.2 |
| ≥ 3-robot contact onsets per episode | 3.31 | 2.55 |

**Verdict: S1b exposure is shorter-lived and more often clearable, but not transient by geometry alone.**

- **The freeze proxy is permanent by construction.** Each latch it records is permanent unless something clears it.
- **Clusters still form.** Without Layer 2 they form in most draws, only later.
- **Node handoffs do not fall.** S1a's node structure, with parked finishers, is kept.
- **Transience needs two things:**
  - Layer 2 grounding a clearing yield within about 19 sim-s, which happens about 0.4 of the time per first conflict;
  - Nav2 passing at ≥ 0.45 m, which [§5](#5-phase-2-live-pass-check-r36a-acceptance) shows it does not.

### Iterations

The layout came from an offline search. The islands stayed the same throughout; only the nodes and Δ changed between gate runs.

| Gate run | Nodes / Δ | Result |
|---|---|---|
| 1 | Wp/Wm (−2.3, ±0.90), N/S (0.05, ±1.55), Δ 3.0 | PASS, with resolvability scored on M3's 0.95 m room gate |
| 2 | Wp/Wm at y ±1.20 (re-scored on the 1.7 − gap backup requirement, run 1 was a thin 0.795) | PASS; G5a-geo 0.885, but grounded executability 0.247 |
| 3 (shipped) | Lane-aligned nodes, Δ 2.5 | PASS; G5a-geo 0.818, grounded 0.405 |

A further footprint search cannot fix the grounding mechanisms above: S1a's full axis aisles score only 0.345.

---

## 5. Phase 2: Live Pass Check (R3.6a Acceptance)

### Deployment and build (VM `vgu-vgu-thu-base`, 2026-10-09 17:1x–17:33 UTC)

- **Delta.** The 13 files of `de2112d` were deployed as a git archive. The pre-image md5s matched `face0f1` for the 4 modified runtime files; post md5 OK.
- **Map.** `colcon build --packages-select swarm_simulation` installed the map; installed md5 = source (pgm `b787d825`, yaml `64a8caf8`).
- **USDs.** 29 USDs were built as root in one SimulationApp session:
  - the scene and the seed-2 pilot;
  - the pass check;
  - the 5 M1 Latin-square runs;
  - the 18 free-flow legs;
  - S1a seeds 3–5 at H = 300.
- **First execution of the `pxr` path.** `usd_check.py` on every S1b USD shows:
  - all four `RackBlocks` **inactive**;
  - 8 `ClearedRackBlocks` remnants;
  - islands at z-centre 0.15 with half-extents (0.275, 0.8, 0.15);
  - spawns equal to the seed draws.
- **Validation.** `validate_simulation` rc 0 on `mapd_5_s1b` and `s1b_pass_check`; kit-kernel cache chowned back.

### Pre-registered rule (VM `NOTES.md`, written before the run)

| Item | Rule |
|---|---|
| Corridor | island_w ↔ north wall, 0.90 m, the narrowest shared gap. The bound is tested, not the 1.7 m passage |
| Setup | robot_1 goes (−2.3, 1.35) → (0.25, 1.35) and robot_2 the reverse; both are dispatched at M5 start and meet at the gap centre. Default mock (no Layer-2 dispatch); map `mapd_5_s1b` |
| Attempts | One. Repeated only on an infrastructure fault or a VOID |
| PASS | Zero `min_distance_violation` safety stops on the pair in `m4.log` |
| VOID | STALE or absent M1 rows within ±5 sim-s of closest approach, or a `stale_unsafe` stop |
| FAIL | A latch. **Program stop** |

### Result: FAIL

| Measure | Value |
|---|---|
| Run | `pass_check_a1`, STAMP `20261009_172515`; Nav2 2/2; RESTORE OK; GT complete (H = 120 sim-s) |
| Departure | Both at 12.3 GT-s, on the y = 1.35 centreline |
| Avoidance | robot_1 began veering north at about a 1.3 m gap (16.0 s). robot_2 held the line until 19.5 s |
| Latch | M1 gap **0.423 m** at 19.53 sim-s (GT 0.445 m at 19.0 s, x ≈ −1.01, the gap centre). 30 110 safety-stop lines, **all** `reason=min_distance_violation` |
| Frozen pose | 19.7 s to H: robot_1 (−1.134, 1.485), robot_2 (−0.890, 1.334). GT gap **0.286 m**, lateral offset **0.151 m** of the 0.45 m needed |
| Room left unused | The gap's zero-cost band is 0.70 m, so centres at about y 1.65 and 1.05 (0.6 m apart) were available |
| M1 | **0 STALE rows** on either robot for the whole run, so not VOID |
| Nav2 / M5 | 0 arrivals, 0 progress failures. 17 analyses, default mock, nothing dispatched |
| Evidence | GT, M1 scene log, `m4.log`, `nav2_r1`/`nav2_r2` logs. The bag (`evidence/pass_a1_172802`) covers only the latched state: it was restarted after a relative-path launch error and missed the approach |

**Verdict:** the S1b premise fails under Nav2 as configured.

- **The premise.** Corridors ≥ 0.85–0.90 m are genuinely two-lane under the 0.45 m latch.
- **What actually happens.** DWB's local avoidance (local inflation 0.07 m) offsets an opposing pair by about 0.15 m, and the latch then freezes both permanently.
- **The S1a prior held.** None of the 4 opposing approaches in the S1a bundles cleared 0.45 m (0.303–0.394 m). E2's was in a 1.2 m strip, so width alone is not the variable.

By the pre-registered rule the program **stopped here**.

---

## 6. Not Run

| Step | Status | Staged on the VM |
|---|---|---|
| M1 coverage (5-run Latin square, 75 sim-s each) | Not run | `s1b_m1cov_p1–p5` USDs and `tasks.json` |
| S1b free-flow legs (18, pilot) | Not run | 18 `s1b_ff_*` USDs, robot rotating over the legs |
| S1b echo pilot, seeds 1–2 | **Not run; no resolution events measured** | `mapd_5_s1b` + `_seed2` USDs; overlays `s1b_orch_seed{1,2}` (load_config-validated) |
| S1a mini-program, seeds 3–5, H = 300 | Not run | `mapd_5_seed{3,4,5}` USDs; overlays `s1a_orch_seed{3,4,5}` (+ suppression, `refusal_no_action`, horizon 300) |

- **Wandering vs park (S1-1)** stays undecided. No episode produced finisher data.
- **Drivers.** `ep_run.sh` and `solo_run.sh` (in `~/v3_s1b`, derived from the S1 resume and free-flow drivers) are ready.

---

## 7. Recommendations (Owner / Step 6)

1. **The S1b premise needs a passing mechanism before any S1b episode.** Geometry is not enough. Options:
   - lane discipline, for example one-way gaps or a directional cost;
   - a "keep-right" or social cost so DWB holds ≥ 0.45 m;
   - a latch-aware release for opposing pairs with free lateral room;
   - registering latch-on-pass as S1b's conflict class, which is then the same regime as S1a.

   The cheapest discriminating check is the same pre-registered pass check rerun with one of these.
2. **M3 on open floors.** The `dynamic_arms:ambiguous` refusal and the room-gate vs sweep mismatch cap grounded executability at about 0.3–0.4 on both floors. That caps any S1 resolution measurement:
   - an honest ambiguous-branch refusal reason (A14(iii));
   - a swap to the partner when the named yielder's sweep fails.

   Both are Step-6 items.
3. **Δ.** S1b needs Δ ≤ 2.67, from R3.6a's recompute. Any future S1a/S1b comparison must carry the Δ difference.
4. **The S1a anchor** (seeds 3–5) is independent of S1b's premise and fully staged. Running it costs about 1.7 VM-h.

---

## 8. VM End State

- **Power and processes.** RUNNING and idle. No `run_simulation`, `fc_launch`, Kit, bag or watcher processes. GPU 0 %, 136 MiB. `vgu_ros` is up; `vgu_ros_nav12` stays stopped.
- **Configs.** `orchestrator.yaml` is `1f656533` in source and installed; `rag.yaml` is `e18c723c`.
- **Ownership.** No root-owned files in the ubuntu caches.
- **Repo tree.**
  - Base: `4bfcd43` + `2fba10f` + the `de2112d` S1b delta (pre-images in `~/v3_s1b/deploy/pre`).
  - Plus 28 VM-only scenario yamls in `isaac/config/scenarios/` and their USDs.
  - The installed `mapd_5.yaml` is still E2's seed 2 (unchanged).
- **Notes and bundle.** `~/v3_s1b/NOTES.md` holds the pre-registration and the run log. The bundle is at `data/logs/vm_runs/s1b_first_light/v3_s1b_bundle.tgz` (md5 `02e3e41d`, gitignored) and has been extracted beside it.
- **API spend: $0.**

---

## 9. Commits, Merge and Suite

The commits are on `feat/v3-s1b`, branched from `feat/v3-integration@face0f1`. Subject lines:

- `4614e14` feat: rack_clearance scenario primitive for open-band floors
- `72d213f` feat: commit S1 Monte Carlo and S1b gate derivation scripts
- `0bd9e5f` feat: S1b sparse-warehouse scene, map and grounding file
- `6ed3159` docs: implementation note for S1b phase 1 and MC gate
- `629dd3b` feat: lane-align S1b nodes, grounded-executability replay
- `de2112d` docs: S1b phase 1 note with grounded executability
- this report and the Phase 2 implementation note.

**Suite** (fresh `face0f1` baseline in a throwaway detached worktree, no stash):

| Tree | Failed | Passed | Skipped | Errors |
|---|---|---|---|---|
| Baseline `face0f1` | 62 | 6182 | 153 | 3 |
| Branch | 62 | 6240 | 153 | 3 |

The failing ids are identical in both: environment-only failures, plus 3 `pxr` collection errors. The merge hash and the merged-tip suite are recorded in the implementation note.

---

## References

- Specs: prereg-v3 R3.6, R3.6a and A12–A14, with the A14 corrigendum; v3 scene design S1 (`feat/v3-design`).
- Scene: `isaac/config/scenarios/mapd_5_s1b.yaml` (header: corridors, nodes, Δ, density, MC gate). Grounding: `config/grounding/s1b_dynamic.yaml`.
- Code: `isaac/vgu_sim/config.py` (`RackClearanceConfig`), `scenario_builder.py`, `validation.py`, `isaac/scripts/generate_warehouse_map.py`.
- Scripts:
  - `scripts/s1_mc.py`, `scripts/s1b_layout.py`, `scripts/s1b_mc_gate.py`;
  - `scripts/s1_grounding_replay.py`;
  - `scripts/s1_live_conflict_stats.py`.
- Tests: `tests/unit/test_rack_clearance.py`, `test_mapd_5_s1b_scenario.py`, `test_s1_mc.py`.
- S1a evidence: `docs/reports/2026-10-08-s1-pilot.md`, `2026-10-09-s1-pilot-resume.md`, `2026-10-09-s1-e2-e3.md`, `2026-10-09-env-audit.md`.
- Bundle: `data/logs/vm_runs/s1b_first_light/` (gitignored).
