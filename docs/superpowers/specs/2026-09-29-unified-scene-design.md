# Unified Scene Design for the Congestion Battery

**Prepared:** 2026-09-29

**Revision history:**

- Initial draft: real-world fidelity frame, one scene vocabulary with a consistency audit of the built battery, full specifications of the bottleneck (B1), priority (B2) and convoy (B3) scenes, the head-on family migration cost table, and the freeze impact.

---

## Question and Verdict

The coverage check (`reports/Congestion scenario coverage check.md`) asks for
one capacity-one aperture used in three robot compositions. The goal is to make
the dead contract labels `bottleneck`, `priority_override` and `convoy`
falsifiable before `prereg-v1`. This document does four things:

- It anchors the simulator to a real warehouse class.
- It defines one scene vocabulary and audits the built battery against it.
- It specifies B1, B2 and B3 to the coordinate.
- It prices a consistency migration of the head-on family.

It is a design document. It adds no scenario code, config or VM run.

**Verdict.**

- **Scale.** The reference class is free-navigating AMRs of the MiR250 class,
  with the Kiva drive unit as a cross-check.
  - The scale factor is **s = 3.3**, set by robot width: 0.58 / 0.178 (MiR250)
    and 0.60 / 0.178 (Kiva) give 3.26 and 3.37.
  - Longitudinal quantities scale between 5.4 and 5.8, because the TurtleBot3
    is wider than it is long.
- **Module.** One single-lane module, **C55**: width 0.55 m, length L chosen by
  a maneuver-span rule.
  - The capacity-one band is [0.50, 0.63) m. The floor is the narrowest width
    proven plannable; the ceiling is 0.18 + 0.45, the width at which two robots
    abreast still breach the 0.45 m latch.
  - The aperture is C55 with L = 1.0, in two placements: **A55-J** centred at
    the junction and **A55-E** centred at x = 1.2.
- **New scenes.**
  - **B1** (bottleneck merge, 3 robots, A55-E, derived grounding): north-arm
    yield, predicted makespan ~130 sim-s.
  - **B2** (priority, a label-counterfactual pair on the T1 `wopen_eopen`
    geometry, 2 active robots): urgency rides the task label that v2 already
    renders, so **no prompt v3**.
  - **B3** (convoy, 4 robots, A55-J, legacy grounding): one yield plus three
    ordered passers, predicted makespan ~190 sim-s at RTF 0.19–0.26.
- **Migration.** **Conservative.** Adopt the vocabulary as documentation.
  Existing scenes are either instances of the rules or recorded deviations,
  so no validated result is invalidated and **0 re-validation runs** are
  needed. The full-consistency variant costs about 25 VM runs and 4–6 days,
  and buys nothing measurable.

**Where fidelity and the apparatus conflict.** Four places, each shown with its
math below:

1. A faithful tight aperture (MiR minimized-field single corridor, 1.47
   widths) scales to 0.26 m. That is below the 0.50 m plannability floor.
   Capacity-one is therefore enforced by the 0.45 m separation policy, not by
   body geometry, and the fidelity claim is restricted to the standard-field
   regime.
2. Convoy headway cannot go below 0.55 m centre-to-centre, which is 3.9 robot
   lengths.
3. Followers that close on a stopped leader latch permanently at ~0.32 m, so
   every queue must be built from hold-backs.
4. The sim is 2.6–4.1× slow for its size. It is ~11× more forgiving of
   reasoner latency than a MiR250 at RTF 0.38, and 17–20× more at four
   stacks (Kiva: 6.8× and 11–12×).

**Three findings change the scene designs:**

- **B2 cannot have three active robots in one lane.** With the single-yield
  primitive, urgency collapses into flow or into feasibility. The derivation
  is in the B2 section.
- **Arm B's head-on FCFS is structurally a tie** at any equal-speed standoff,
  whatever the spawn or start offset.
- **Arm B reads a held robot as `blocked_path`** whenever the head-on rule
  fails. This happens in B1 for every standoff pose, and in 10 of 45 B3 grid
  cases.

---

## Sources Checked

| Source | What it supplied |
|---|---|
| `reports/Congestion scenario coverage check.md` | B1/B2/B3 compositions, per-class metrics, scoping sentences, novelty accounting |
| `reports/Four way intersection robot congestion.md` | Single-yielder doctrine, A-DRIVE yielding cost χ, the ≥ 0.9 m / ≥ 0.68 m pocket heuristic, latch-at-margin theorem |
| `docs/superpowers/specs/2026-09-27-scenario-battery-design.md` | T0–T3 build map, T2b dependencies, prompt-v2 bundle |
| `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md` | Stop mechanics (0.24–0.42 m emergent gaps), N-S band limit, J2, four-stack RTF 0.21–0.24, T_r = 20 + RTF·D |
| `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` rev 9.3 | Battery, run matrix, oracle schemas, measurement and pooling rules |
| `isaac/config/scenarios/*.yaml`, `family/*.yaml`, `family_manifest.csv` | Every geometry constant in the audit table |
| `reasoning/rag/scene_geometry.py`, `maneuver_geometry.py`, `retreat_candidates.py`, `command_grounder.py` | Park, escort, band and strategy-grounding behaviour |
| `reasoning/baselines/classical_reasoner.py`, `config/rag.yaml` | Arm B rules and thresholds |
| `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`, `swarm_orchestrator/models.py` | Goal table, `TaskAssignment` (`task`, `goal`, `start_delay_sec`), stall clocks |
| `ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`, `nav2_adapter.py`, `config/safety.yaml` | Crossing chain, escort along spawn yaw, 15× wall-clock escort bound, 0.45 m latch, 0.6 m STALE band |
| `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` | Footprint 0.14 × 0.18 m, `forward_stop` polygon 0.02–0.25 m × ±0.12 m, 0.18 m/s cap |
| `isaac/vgu_sim/warehouse_builder.py`, `isaac/config/warehouse.yaml` | 12 × 8 m floor, 1.2 m cross aisles, 0.9 m racks, 0.1 m walls |
| `docs/reports/2026-09-29-t1-tuning-basket.md` | Transit p50 0.152 m/s, max 0.1803 m/s; maneuver legs 0.08–0.11 m/s |
| `docs/reports/2026-09-27-three-robot-feasibility.md` | RTF table, follower latch at ~0.32 m (Layer 4) |
| `docs/implementation_notes.md` | Validated counts (`_bshort` 15/15, T2b smoke, T3a/T3b smokes) |
| [ROBOTIS TurtleBot3 - official docs](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/) | Burger 138 × 178 × 192 mm, 0.22 m/s max (the simulated robot is `turtlebot3_burger`) |
| [MiR250 - official specifications](https://mobile-industrial-robots.com/products/robots/mir250/specifications) | 800 × 580 mm, 2.0 m/s; corridor 1,450 mm single / 3,000 mm passing (standard), 850 / 1,700 mm (minimized); doorway 1,500 / 800 mm |
| [Amazon Robotics family - AllAboutLean](https://www.allaboutlean.com/amazon-robotics-family/), [Kiva - IEEE Spectrum](https://spectrum.ieee.org/three-engineers-hundreds-of-robots-one-warehouse) | Kiva drive unit ~750 × 600 mm, 1.3 m/s (secondary sources) |
| [Geek+ P800R - QVIRO spec sheet](https://qviro.com/product/geek/p800r/specifications) | 1,090 × 830 mm, 1.6–2.0 m/s (secondary source; sensitivity row only) |

**Method.** The Arm B verdicts and grounded maneuver numbers below were
produced from the repo's own code: `classify_scene`, `resolve_classical`,
`ground_reasoner_result` and `park_offset_m`. They ran against the shipped
`config/rag.yaml` and `orchestrator.yaml` `scenario_geometry`, on synthetic
standoff frames, from a session-scratchpad script that is not committed.

- Each table names the function it came from, so it can be regenerated.
- Standoff poses are predictions from the head-on corpus and the
  intersection runs. They are not observations of these scenes.

---

## 1. Real-World Fidelity Frame

### Reference class and scale factor

The simulated robot is a TurtleBot3 Burger: 0.138 m long, 0.178 m wide, top
speed 0.22 m/s. In Nav2 it runs a 0.14 × 0.18 m footprint and a 0.18 m/s cap.
Two reference classes were considered:

- **Grid-reserved goods-to-person units** (Kiva, Geek+ P800). They run under
  central space-time reservation, so a formed jam is unreachable by
  construction; the intersection literature review makes this point. Their
  conflict mechanism does not match this apparatus, where Nav2 plans each
  robot independently and a safety latch stops it.
- **Free-navigating AMRs** (MiR250, Locus class). They plan locally, keep
  separation with safety-rated protective fields, and do form corridor
  standoffs. They also publish corridor and doorway widths for one-way and
  passing traffic, which is exactly the capacity-one question.

**Chosen: MiR250-class free-navigating AMR.** Kiva is kept as a cross-check,
because its width gives nearly the same scale.

| Reference | Length × width (m) | Speed (m/s) | s by width | s by length |
|---|---|---|---|---|
| MiR250 (chosen) | 0.80 × 0.58 | 2.0 | **3.26** | 5.80 |
| Kiva drive unit (cross-check) | 0.75 × 0.60 | 1.3 | 3.37 | 5.43 |
| Geek+ P800R (sensitivity) | 1.09 × 0.83 | 1.6–2.0 | 4.66 | 7.90 |

- **Why width sets the scale.** Aisle capacity, the question "can two pass?",
  is a lateral quantity. The scene conflicts are all about lateral capacity.
- **The consequence of the aspect ratio.** The Burger is wider than it is long
  (0.78:1); real AMRs run 1.25–1.38:1. Longitudinal quantities (headway,
  backup distance, queue spacing) therefore map at 5.4–5.8 when counted in
  body lengths. Both mappings are shown where it matters.

### Scale-mapping table (s = 3.3)

| Sim quantity | Sim value | In robot widths | Full scale at s = 3.3 | Real anchor |
|---|---|---|---|---|
| Robot footprint | 0.14 × 0.18 m | 0.78 × 1 | 0.46 × 0.59 m | MiR250 0.80 × 0.58 m |
| Cross aisle (free floor) | 1.2 m | 6.7 | 3.96 m | MiR passing corridor, standard fields: 3.0 m (5.2 widths) — two-way, faithful |
| C55 single-lane module | 0.55 m | 3.06 | 1.82 m | Standard single 1.45 m (2.5 w) ≤ 1.82 < standard passing 3.0 m (5.2 w): single-lane. Minimized passing 1.70 m (2.93 w) < 1.82: two-way under minimized fields |
| T3a corridor | 0.50 m | 2.78 | 1.65 m | Inside the single-lane band for both field configurations |
| 0.45 m latch (centre to centre) | 0.45 m | 2.5 | 1.49 m | A separation policy; body gap 0.27 m → 0.89 m |
| Emergent stop gap | 0.24–0.42 m | 1.3–2.3 | 0.79–1.39 m | Protective-field stop; real fields scale with speed, these do not |
| Yielder park offset (L 2.0) | 1.789 m | 9.9 | 5.9 m (s_len 5.6: 10.0 m) | Spare-point retreat (warehouse AGV refuge cells) |
| Retreat-pocket heuristic | ≥ 0.9 m | 5.0 | ≥ 3.0 m | Unlabeled-disc bound transferred with 2r ≈ 0.45 (heuristic) |
| Tracked band | 5.0 × 3.6 m | 28 × 20 | 16.5 × 11.9 m | Camera-observed zone of one overhead unit |
| Warehouse floor | 12 × 8 m | — | 39.6 × 26.4 m | One small picking cell |
| Transit speed | 0.15 m/s (p50 0.152) | 0.83 w/s | 0.50 m/s at equal time | Kiva 1.3 (2.2 w/s), MiR 2.0 (3.4 w/s) |
| Maneuver legs (backup/escort) | 0.09–0.10 m/s | 0.55 w/s | 0.33 m/s | Creep/reversing speeds, 0.3–0.5 m/s typical |
| Episode horizon | 300 sim-s | — | 114 s at Kiva time scale; 74 s at MiR | Time scale = s·v_sim / v_real = 0.38 (Kiva), 0.25 (MiR) |
| M5 stall trigger | 12 wall-s ≈ 4.6 sim-s at RTF 0.38 | 3.8 widths of travel | 1.75 s at Kiva time scale | Fleet-manager stall timeouts |

### Where the sim is and is not faithful

**Faithful. The thesis can cite these.**

- **Main-aisle capacity ratio.** 1.2 m is 6.7 widths. The MiR standard passing
  corridor is 5.2 widths. The cross aisles are two-way, as real main aisles
  are.
- **Capacity-one by separation policy.** The 0.55 m module is single-lane
  because the 0.45 m separation floor forbids two abreast, not because two
  bodies cannot fit. That is how a standard-field AMR corridor works: the
  1.45 m single-lane rating for a 0.58 m robot is set by its protective
  fields, not its body.
- **Centralized pose knowledge.** Overhead ArUco tracking gives the controller
  global poses. Median error is ≤ 0.011 m and the maximum 0.084 m. Real fleets
  get the same from floor fiducials or a fleet server. Overhead cameras
  specifically have one fielded analog (the Oxford CCTV fleet controller,
  arXiv:2606.06762, cited in the coverage check).
- **Conflict cardinality.** Two to four robots per conflict matches the
  social-mini-games canon.

**Not faithful. The thesis must state these.**

- **Speed-to-size ratio.** The sim runs at 0.83 widths/s; Kiva at 2.2 and
  MiR at 3.4. The sim is 2.6–4.1× slow for its size.
- **Latency budget.** During a reasoner call of L wall-seconds the sim robot
  covers 0.15·RTF·L m. At RTF 0.38 that is 0.057·L m, or 0.32·L widths.
  - A MiR250 covers 2.0·L m, or 3.4·L widths. A Kiva covers 1.3·L m, or
    2.2·L widths.
  - The ratio is (v_real / w_real) / (0.833·RTF). So the sim is **10.9× more
    forgiving of reasoner latency than the reference MiR250 at RTF 0.38**,
    and 17–20× at four stacks (RTF 0.21–0.24). Against Kiva the figures are
    6.8× and 10.8–12.4×.
  - This is mitigated because M2 acts only on formed jams, where the robots are
    stopped. Latency then costs resolution time, not safety.
  - It still means the sim cannot support any claim that a VLM is "fast
    enough" for a real fleet.
- **Aspect ratio.** Backup and queue distances are 1.7× longer in body lengths
  than a real AMR would need for the same lateral geometry.
- **Stop mechanics.** Stops are a centre-distance latch with a ~0.5 s
  reaction, which lands at 0.30–0.34 m, plus a fixed 0.25 m forward polygon.
  Real protective fields grow with speed and slow the robot before a stop.
- **Queues.** A follower that closes on a stopped leader stops at ~0.32 m.
  Neither robot is exempt, so both latch permanently (three-robot feasibility
  report, Layer 4). A real fleet queues at field distance and resumes.
- **Sensing.** Nav2 sees one lidar plane at 0.182 m. At 1× scale only the 7 cm
  LDS head of another Burger is scannable (the T3a 1.82× scale finding).
- **Prompt scale words.** The stage-1 prompt says robots are "roughly 0.3 m
  wide". They are 0.18 m. This is recorded, not changed here, because changing
  it is a template edit (see Freeze Impact).

### The apparatus conflict: a faithful tight aperture cannot be built

| Quantity | Real (MiR250) | Robot widths | At s = 3.3 | Apparatus verdict |
|---|---|---|---|---|
| Doorway, minimized fields | 0.80 m | 1.38 | 0.24 m | Below the plannability floor |
| Single corridor, minimized fields | 0.85 m | 1.47 | 0.26 m | Below the floor (0.50 proven, global inflation band 0.38) |
| Doorway, standard fields | 1.50 m | 2.59 | 0.47 m | Below 0.50: not proven plannable |
| Single corridor, standard fields | 1.45 m | 2.50 | 0.45 m | Below 0.50 |
| Passing corridor, minimized fields | 1.70 m | 2.93 | 0.53 m | Inside the band; the real robots could pass here |
| Passing corridor, standard fields | 3.00 m | 5.17 | 0.93 m | Two-way in both worlds |

- **Plannability.** Nav2 plans through a gap only if w/2 exceeds the global
  inflated half-width of 0.19 m, i.e. w > 0.38. The collision box must also
  clear the walls. 0.50 m is the narrowest width with demonstrated transit
  (T3a smoke), with 0.13 m of box-to-wall clearance.
- **The compromise.**
  - Capacity-one is enforced by the 0.45 m policy, not by bodies. With both
    robots aligned, their GT lateral separation is at most w − 0.18, so two
    abreast breach the latch whenever w < 0.63.
  - The thesis may claim fidelity to **standard-field single-lane corridors**,
    whose real band [2.50, 5.17) widths contains the whole apparatus band
    [2.78, 3.50) widths.
  - It must not claim fidelity to minimized-field deployments, where 0.55 m
    (3.06 widths) would admit passing.

### Real-world counterpart per scene

| Scene | Real-world counterpart |
|---|---|
| T0 `normal_flow` | Two-way main-aisle passing with no conflict |
| T1 `head_on_deadlock`, `wopen_eopen` | Single-lane bidirectional aisle conflict (standard-field narrow transfer corridor) |
| T1-X `intersection_bottleneck` | Four-way cross-aisle jam after reservation failure (A-DRIVE's fault regime) |
| T2a `_bshort` pair | Head-on where one robot's retreat is blocked by a parked cart |
| T2b `t2b_flow_ordering` | Head-on with a queued follower behind one side |
| T3a `blocked_path_*` | Stalled at a pallet (reroute) vs an unregistered vehicle or person (wait) |
| T3b `obstacle_in_candidate` | Designated retreat pocket occupied by an unregistered pallet |
| T3c `dynamic_anomaly_v2` | Temporary pallet drop across a lane |
| **B1** `bottleneck_merge` | Merge at a transfer-station gate: a main-aisle stream (2 robots) and a cross-aisle robot contend for a single-lane gate |
| **B2** `priority_urgent_*` | Expedited-order robot meets a routine robot at a shared single-lane aperture |
| **B3** `convoy_counterflow` | Wave-released platoon of three same-direction AMRs meets one counter-flow robot at a single-lane corridor |

---

## 2. Unified Scene Vocabulary

### Apparatus constants every rule derives from

| Constant | Value | Source |
|---|---|---|
| Robot footprint | 0.14 × 0.18 m (half-width 0.09) | `nav2_params.yaml` footprint |
| Latch floor | 0.45 m centre to centre, M1 positions | `safety.yaml` `min_distance_m` |
| STALE fail-safe band | 0.6 m | `safety.yaml` `stale_unsafe_distance_m` |
| Mover legality criterion | ≥ 0.55 m GT to every non-exempt robot | Latch 0.45 + 0.10 M1 budget (intersection study) |
| Emergent stop gap | 0.24–0.42 m (latch acts at ~0.30–0.34 m) | Intersection study, Constraint 1 |
| Follower stop gap | ~0.32 m (`forward_stop` 0.25 m + leader rear 0.07 m) | Three-robot feasibility, Layer 4 |
| Tracked band | \|x\| ≤ 2.5, \|y\| ≤ 1.80 (homography edge 2.789 / 2.092) | Scenario headers; IBB4 |
| Transit / maneuver speed | 0.15 m/s (max 0.1803) / 0.09–0.10 m/s | Tuning basket |
| Park offset | P(L) = (L/2)·2.79/2.1 + 0.06 + 0.4 = 0.6643·L + 0.46 | `park_offset_m` |
| Passer clearance | 0.65 m (0.45 + 0.2) | `passer_clearance_m` |
| Derived backup clearance | 1.7 m from the passer (binds when L < 2.05 m) | `config/rag.yaml` |
| Escort axis | Odom yaw 0 = spawn heading | `command_bus_node.py` `_admit` |
| Escort wall bound | max(15 × nominal, 30) wall-s | `nav2_adapter.drive_heading` |
| Stall trigger | 12 wall-s | `orchestrator.yaml` |
| RTF by stack count | 2: 0.388–0.395; 3: ~0.34; 4 (four Nav2 stacks): 0.21–0.24 (window 0.19–0.26) | Feasibility report; intersection study |
| M5 start (sim-s) | ~12 at 2–3 stacks; 19.8–20.6 at 4 stacks | Scenario headers; intersection study |
| Arm B | r_conflict 1.5, r_block 1.0, fcfs zone 1.0, opposition ≥ 150°, crossing axes 45–135° | `config/rag.yaml` `classical:` |

**Correction to the brief's constants.** "RTF ~0.28 at 4 robots" is the
`dynamic_anomaly` measurement, which ran **four Isaac robots but only two Nav2
stacks** (0.277–0.310). With four full stacks the measured RTF is 0.21–0.24,
and four-stack bring-up failed 3 of 8 launches. Every B3 timing below uses the
0.19–0.26 window.

### The single-lane module C55

**Width: 0.55 m, for every single-lane bidirectional conflict scene.**

- **Latch math.** The capacity-one band is [0.50, 0.63) m.
  - Two robots abreast have GT lateral separation ≤ w − 0.18, which breaches
    0.45 for every w < 0.63.
  - Nav2's usable centre band is w − 2·(0.09 + 0.10) = w − 0.38. At 0.55 that
    is 0.17 m, far below 0.45, so the planner never even attempts a pass.
  - 0.55 sits 0.08 m under the ceiling and 0.05 m over the proven floor.
- **Fidelity.** 0.55 m is 3.06 widths, inside the standard-field single-lane
  band [2.50, 5.17).
- **Evidence weight.** Every head-on run in the corpus used 0.55: the T1
  family, `_bshort` 15/15, T2b and T3b. 0.50 has only the T3a smokes.

**Length L is not a free parameter.** It is set by the **maneuver-span rule**:

```text
park(L)       = 0.6643 L + 0.46                     (park_offset_m)
escort_end(L) = centre ± (park(L) + 0.65)           (passer escort end)
constraint    = |escort_end| + goal_margin ≤ 2.5    (tracked band, x)
derived mode  : park = max(park(L), passer + 1.7) — the 1.7 m clearance binds for L < 2.05
```

| L (m) | park | escort end (centred at 0) | required room | Grounding mode it admits | Instance |
|---|---|---|---|---|---|
| 0.5 | 0.792 | 1.442 | 0.832 | Legacy only (1.7 binds) | — |
| 1.0 | 1.124 | 1.774 | 0.914 | Legacy only | T2b; B1 and B3 apertures |
| 1.6 | 1.523 | 2.173 | 1.013 | Legacy; derived when the park floor binds | T3b (centre 1.2) |
| 2.0 | 1.789 | 2.439 | 1.079 | Derived | T1, T2a family, T3a |
| 2.05 | 1.822 | 2.472 | 1.087 | Derived (break-even) | — |

**Rule C55-L.**

- A **two-robot derived-mode** scene uses L = 2.0 centred at x = 0. Its escort
  end is 2.439, leaving 0.061 m to a ±2.5 goal.
- A scene with **≥ 1 queued passer** uses L = 1.0 centred at x = 0 on legacy
  grounding. Its escort end is 1.774, leaving 0.73 m for later passers' goals.
- **The derived-mode head-on window.** In derived mode the passer's escort
  ends at the passer's standoff position plus 2.35 m (1.7 + 0.65). A
  derived-mode head-on therefore stays in band only when its standoff centre
  satisfies |c| ≤ 2.5 − 2.23 ≈ 0.27 m. That is why every head-on is centred
  at x = 0.

### Aperture placements A55-J and A55-E

The aperture is C55 with L = 1.0. `aisle_barrier` narrows only the E-W aisle,
between |y| ∈ [0.275, 0.6]. Placed at the junction, its blocks seal both N-S
arms: the T3a header states this, and so does the intersection study.
Placement is therefore chosen by composition:

| Placement | Barrier | N-S arms | Park points (legacy) | Escort ends | Used by |
|---|---|---|---|---|---|
| **A55-J** | 0.55 × 1.0 at centre 0 | Sealed | x = ±1.124 | x = ±1.774 | T2b (already), B3 |
| **A55-E** | 0.55 × 1.0 at centre 1.2 (x ∈ [0.7, 1.7]) | Open (0.1 m clear of the N-S aisle edge 0.6) | West 0.076 / east 2.324 | East-bound escort end 2.974 — **out of band** | B1 (only a N-S yielder; see B1) |

- **A55-E cannot host an axis-aligned head-on.** An eastbound passer's escort
  would end at 2.974. Its only role is a merge whose yielder is on the N-S arm,
  so the escort is computed against the junction box, not the aperture.
- **Visibility is fine.** The barrier top projects outward by 2.79 / 2.1 =
  1.33. At A55-E its image covers x ≤ 2.26 and |y| ≤ 0.80. That occludes no
  park point on the N-S arm (y ≈ 1.7), and no marker on the y = 0 transit line
  (the line of sight stays in the y = 0 plane).

### Spawn, goal and queue rules

| Rule | Statement | Derivation |
|---|---|---|
| R-TRACK | Every spawn, goal, park point and escort end lies within \|x\| ≤ 2.5, \|y\| ≤ 1.80 | Verified tracked band; \|x\| = 3.0 gave 0/146 detections |
| R-RUN | Spawn ≥ 0.5 m of straight run before the module mouth, facing the goal | Run 11 wall-lock (`head_on_deadlock` header); the escort drives the spawn heading |
| R-GOAL-FAR | Passer goal = escort end + margin m_g, with 0.05 ≤ m_g and the goal within R-TRACK | Nav2 stops the passer 0.07–0.10 m short (`_bshort` realised margin 0.063–0.096) |
| R-GOAL-YIELDER | The passer's rest pose is ≥ 0.55 m from the yielder's return path | `_gshort` H2/H3 losses |
| R-BLOCKED-SHORT | A robot with a blocker behind its spawn gets its spawn as its goal; only that goal is shortened | Amendments A1 (blocker on the passer's goal path lost 5 of 12 pilot episodes) |
| R-JUNCTION | Junction spawns and goals sit at radius 1.75 on each arm, ≥ 0.25 outside the 1.5 m zone | Intersection header; y band 1.80 |
| R-LANE | Parallel lanes at y = ±0.35: 0.70 m pass, lane centres 0.25 m from the rack faces | `normal_flow` header |
| R-QUEUE-1 | Queued robots sit on the lane centreline, facing the goal | The escort is a straight leg along spawn yaw; an off-centre queue hits the barrier (\|y\| < 0.275) |
| R-QUEUE-2 | Queue spacing ≥ 0.57 m GT | 0.45 latch + 0.084 M1 max ≥ 0.534; ≥ 0.55 criterion |
| R-QUEUE-3 | Every queued robot is **held** (`start_delay_sec`) and released after the worst-case dispatch, never before | Only hold-back or a timed gate stops a robot at a chosen gap; a follower closing on a stopped leader latches permanently |
| R-QUEUE-4 | Queued robots ≥ r_conflict (1.5) + 0.1 from the nearer standoff robot | Keeps Arm B's head_on uncrowded (T2b precedent) |
| R-GOAL-STACK | Each passer goal ≥ 0.60 m from every other goal and from every later passer's escort end | T2b's 0.06 m trap at L 2.0 |
| R-POCKET | Sidestep candidates keep \|lateral\| + 0.09 + 0.05 ≤ 0.6 inside the world aisle; pockets ≥ 0.9 m from other pockets and ≥ 0.68 m from **non-exempt** crossing paths | Pocket heuristic (intersection review); exempt yielder↔passer pairs rely on the pair-scoped exemption |
| R-FCFS | Spawns ≥ fcfs_zone_radius (1.0) + 0.1 from the expected pair midpoint | T1 basket: spawn-boundary censoring |

**Two consequences of these rules (derived, not tuned):**

- The ±2.6 `_bshort` passer goal **violates R-TRACK by 0.1 m**. It works only
  because Nav2 stops the passer 0.07–0.10 m short, at a realised 2.50–2.53.
  It is recorded as deviation D2, not adopted as a rule.
- At L = 2.0 there is no goal that satisfies both R-TRACK and an m_g of
  0.15 m. The family's ±2.5 (m_g = 0.061) and ±2.6 (outside the band) are the
  two sides of that conflict.

### Naming scheme

- **New scenes** are named `<conflict_class>_<composition>[_<variant>]`: for
  example `bottleneck_merge`, `priority_urgent_r1`, `priority_urgent_r2`,
  `convoy_counterflow`. The tier and module go in the YAML's `family:` field
  and in a battery manifest row, not in the file name.
- **Existing names are grandfathered.** They are cited verbatim in rev 9.3, in
  run ids and in artifact paths. A rename would break that provenance. A
  manifest alias column carries the vocabulary instead.

### Oracle-block conventions per tier type

| Tier type | Block | Frozen fields | Validity check |
|---|---|---|---|
| Geometry-sufficient (T1) | none | — | Arm B's own answer is the reference |
| Ordering (T2a, T2b, B1, B3) | `OracleConfig` | `correct_yielder`, `fcfs_yielder`, `feasible_yielders`, `correct_order` (≥ 3 robots), `objective`, `rationale`, `margin` record | Forced-order harness, both orders, n = 2 seeds; censored alternative = dominated (lower bound) |
| Semantic-channel pair (T3a, B2) | Pair-specific shape; members byte-identical except the entity or label and the oracle | T3a `BlockerOracleConfig`; B2 new `PriorityOracleConfig` (`urgent_robot`, `correct_yielder`, `correct_first_passer`, `classical_yielder`, `objective: urgent_first`, `rationale`) | Diff test pins the member difference |
| Strategy-label (B3) | `OracleConfig` plus new `correct_strategy: convoy`, `accepted_strategies: [convoy, yield]`, `platoon: [...]` | as ordering | Forced-order harness (4 robots) |
| Stage-2 (T3b) | `RetreatOracleConfig` | as built | 269-case pin |
| Descriptive (T3c) | `expected_conflict` only | — | — |

### Geometry-declaration conventions

- **Every scene header carries a goal-table row.** It is a comment block
  listing each `orchestrator.yaml` key the scene needs:
  - `initial_tasks`: task, goal, `start_delay_sec`, and `priority` (new);
  - `scenario_geometry`: corridor centre, half-length, aisle half-width,
    occluder height, and `arms` when a yielder retreats along a junction arm;
  - `shadow_classical_zones`, `grounding.mode`, `grounding_aisle_y_band_m`,
    `t0_probe_mode`, `prompt_static_obstacles`.

  This is today's practice. The header row is the contract, because M5 does
  not read the scenario YAML.
- **Every scene with a scripted forced order ships a preflight** that refuses
  a run whose installed `orchestrator.yaml` differs from the row (the
  `t2b_forced_order.py` pattern).
- **The `scenario_geometry` barrier mirror.** `corridor.center_m` and
  `half_length_m` mirror `aisle_barrier`, except in a merge scene. There the
  corridor is the junction box (half-length 0.6, occluder 0.0), and the
  barrier sits off the maneuver.

### Standard constraint-check table

Every scene pins these in `tests/unit/test_<scene>_scenario.py`. It uses M3's
and Arm B's own functions, over a parametrized grid:

- standoff separation {0.24, 0.46, 0.70} × shift {−0.2 … 0.2} × M1 jitter
  {−0.1, 0, 0.1} — the T2b grid, 45 cases per yielder;
- plus scene-specific axes: heading for merges, RTF for timing.

This is the T3b 269-case pattern, generalised.

| Id | Check | Criterion |
|---|---|---|
| C1 | Spawns, goals, park points and escort ends in the tracked band | R-TRACK, marker half-size 0.06 included for escort ends |
| C2 | Every non-exempt pair at every phase (approach, hold, backup, each escort, returns, parked) | GT gap ≥ 0.55 m |
| C3 | Spawn-time pairs | ≥ 0.57 m (no spawn latch) |
| C4 | Arm B verdict at the designed standoff, over the grid | The registered verdict in ≥ the registered fraction of cases |
| C5 | Park feasibility | Room ≥ `required_room_m` on every side the oracle needs |
| C6 | Retreat candidates inside the world aisle | R-POCKET |
| C7 | Escort end vs every goal and parked robot | ≥ 0.60 m (R-GOAL-STACK) |
| C8 | FCFS arrival censoring | R-FCFS |
| C9 | Hold-back release window | Released after the worst-case dispatch and before the robot's admission, for RTF ∈ window |
| C10 | Duration | Predicted oracle makespan + 60 sim-s ≤ `duration_sec` at the slowest RTF |
| C11 | Escort wall bound | Nominal escort time / RTF_min < 15 × nominal (always true at RTF > 0.067) |
| C12 | Robot count | ≤ 4 robots, with the RTF window registered |
| C13 | Map and USD | Per-scenario map contains the barrier; USD regenerated after any YAML edit (verified by content) |

### Consistency audit of the built battery

| Scene | Module (w × L @ centre) | Spawns | Goals | Hold / queue | Objects | Grounding | Status under the vocabulary |
|---|---|---|---|---|---|---|---|
| `head_on_deadlock` | 0.55 × 2.0 @ 0 | ±1.5 (0.5 m run) | ±2.5 | — | — | derived | Rule instance; hand-authored twin of `wopen_eopen` |
| `head_on_asymmetric_wopen_eopen_o0` | 0.55 × 2.0 @ 0 | ±1.5 | ±2.5 (m_g 0.061) | — | — | derived | Rule instance |
| family `w0p2`/`e0p2` `_o0` (v1) | 0.55 × 2.0 @ 0 | ±1.5 | ±2.5 | — | box 0.3 × 0.3 × 0.5 at ∓1.85 (0.2 m behind spawn) | derived | Superseded (A1): blocker on the goal path |
| family `_gshort` | same | ±1.5 | opponent spawn ±1.5 | — | same | derived | Superseded: violates R-GOAL-YIELDER |
| family `_bshort` (T2a) | same | ±1.5 | passer ±2.6; blocked side = own spawn | — | same | derived | **Deviation D2**: passer goal 0.1 m outside R-TRACK |
| `t2b_flow_ordering` | 0.55 × 1.0 @ 0 (A55-J) | ±1.5 (1.0 m run); robot_3 −2.45 | +2.5 / −2.0 / +1.85 | robot_3 held 55 wall-s | — | legacy | Rule instance (C55-L queued) |
| `intersection_bottleneck` (T1-X) | none; junction box half 0.6 | radius 1.75 | radius 1.75 | — | — | derived + arms | Rule instance (R-JUNCTION) |
| `normal_flow` (T0) | none | ∓2.5 on lanes ∓0.35 | ±2.5 | — | — | — | Rule instance (R-LANE) |
| `dynamic_anomaly_v2` (T3c) | none | as T0 | as T0 | — | pallet 0.3 × 1.05 × 0.5 at (1.5, −0.075), 30–110 s | derived | Rule instance |
| `blocked_path_object` / `_transient` (T3a) | **0.50** × 2.0 @ 0 | robot_1 −2.5; robot_2 pocket (0, 0.9) | robot_1 +2.5; robot_2 (0, 1.75) | — | blocker 0.25 × 0.32 × 0.35 at (−0.5, 0), spawned at 16 s | derived | **Deviation D1**: width 0.50 is load-bearing (a 0.22 m lidar cross-section closes 0.50; 0.55 needs > 0.30) |
| `obstacle_in_candidate` (T3b) | 0.55 × 1.6 @ 1.2 | (0, 0), (2.5, 0) | ±2.5 | — | box 0.40 × 0.30 × 0.35 at (−0.32, 0.81) | derived + y band [−0.55, 1.0] | **Deviation D3**: placement is load-bearing (the park point must land in the junction for k = 3) |
| `dynamic_anomaly` (retired) | none | ±3.0 | — | — | — | — | Out of battery; violated R-TRACK |

Only three genuine deviations remain: D1, D2 and D3. Each is load-bearing, and
each is recorded with its reason. Every other constant is an instance of a
rule.

---

## 3. The Three New Scenes

### B1 — `bottleneck_merge` (bottleneck, 3 robots)

**Composition.**

- Robot roles:
  - `robot_1`: main-aisle lead, from the west, eastbound.
  - `robot_3`: main-aisle follower, from the west, **held**.
  - `robot_2`: merges from the north arm.
- All three are bound east through the A55-E gate, so no robot opposes
  another.
- The standoff forms when `robot_1` and `robot_2` reach the gate mouth within
  ~3 s of each other.

```text
            y
   NW rack  |  robot_2 spawn (0, 1.75), yaw -pi/2       NE rack
            |  park (0.15 -/+ 0.36, 1.70)
  ----------+----------------------------------------------------- y = 0.6
  robot_3   robot_1          merge ~(0.1, 0)   [ A55-E gate 0.7..1.7 ]  goals
  (-2.45,0) (-1.0,0)  ------------------------>[======0.55 m=======]  (2.45,-0.3)
  held 80 s                                    [===================]  (2.45,+0.3)
  ----------+----------------------------------------------------- y = -0.6   (1.90, 0)
   SW rack  |                                                      SE rack
```

| Robot | Spawn (x, y, yaw) | Goal | Task label | Hold |
|---|---|---|---|---|
| robot_1 | (−1.0, 0, 0) | (2.45, −0.30) | `cross_narrow_aisle` | — |
| robot_2 | (0.0, 1.75, −π/2) | (1.90, 0.00) | `cross_narrow_aisle` | — |
| robot_3 | (−2.45, 0, 0) | (2.45, +0.30) | `cross_narrow_aisle` | `start_delay_sec: 80` |

**Timing (3 stacks, RTF ~0.34, window 0.28–0.39).**

- **Merge synchrony.** `robot_1` travels 1.1 m to the merge (7.3 s). `robot_2`
  travels ~1.3 m to its latch pose, about (0.15, 0.45) (≈ 8.7 s). So
  **Δt ≈ +1.4 s, with `robot_1` leading.**
- **The outcome is trimodal in Δt:**
  - **0 < Δt < ~2.5 s** (designed): a perpendicular latch at ~0.3–0.45 m.
    `robot_2` is still heading about −70° to −90°.
  - **Δt ≥ ~3 s:** `robot_1` is through first. There is no conflict and no
    trigger; the episode is discarded as a no-event and counted.
  - **Δt < 0:** `robot_2` turns into the gate first, and `robot_1` closes
    behind it. This is a **same-direction follower latch**, which no
    vocabulary command can clear: `robot_1`'s yield is refused because
    `robot_3` is behind it, and `robot_2` cannot reverse along its arm. The
    episode is censored and counted as an apparatus failure, not a reasoner
    result.
- **Timeline.**
  - Standoff ~18–22 sim-s. Trigger +4.1 sim-s, i.e. ~41–48 wall-s after M5
    starts.
  - Dispatch by ≤ ~75 wall-s, including gpt-4o refusal retries.
  - The `robot_3` release at 80 wall-s falls at T_r = 12 + RTF·80 = 34–43
    sim-s. That is after dispatch, when its goal is only recorded under its
    linked wait, and before its admission (~58 sim-s).
- **Oracle timeline.**
  - `robot_2` backs up 1.25–1.35 m at 0.09 m/s and holds (~44 sim-s).
  - `robot_1` is escorted 1.05–1.35 m and clears at ~58 sim-s.
  - `robot_3` is escorted 3.7 m and clears at ~95 sim-s.
  - `robot_2` returns ~3.6 m, reaching its goal at ~120 sim-s.
  - **Predicted makespan ~120–130 sim-s. `duration_sec: 200`** (C10 margin
    ≥ 70 s).

**Grounded oracle** (derived mode; junction box half-length 0.6, occluder
0.0; arms `robot_1`/`robot_3` x/−1 and `robot_2` y/+1; from
`ground_reasoner_result` at four standoff poses):

| Standoff (robot_1; robot_2, heading) | robot_2 backup | Park (x, y) | robot_1 escort → end x | robot_3 escort → end x |
|---|---|---|---|---|
| (0.10, 0); (0.15, 0.45, −80°) | 1.25 m | (0.51, 1.70) | 1.15 → 1.25 | 3.70 → 1.25 |
| (0.00, 0); (0.20, 0.40, −70°) | 1.30 m | (0.56, 1.70) | 1.25 → 1.25 | 3.70 → 1.25 |
| (0.20, 0); (0.30, 0.42, −60°) | 1.28 m | (0.66, 1.70) | 1.05 → 1.25 | 3.70 → 1.25 |
| (−0.10, 0); (0.10, 0.35, −90°) | 1.35 m | (0.46, 1.70) | 1.35 → 1.25 | 3.70 → 1.25 |

- **The alternative is refused, not merely slower.** A `robot_1` yield grounds
  as `yield=infeasible: no backup distance in band [0.5, 2.0] m satisfies
  clearance 1.7 m`, because `robot_3` sits behind it. With the frozen `swap`
  gate it is re-grounded to `robot_2`.
- **So the oracle is feasibility-determined**, like T2a:
  `correct_yielder: robot_2`, `correct_order: [robot_1, robot_3]`,
  `feasible_yielders: [robot_2]`. The forced-order harness has no executable
  alternative arm, so it is skipped and the margin record says so.

**Constraint checks.**

| Id | Check | Value | Verdict |
|---|---|---|---|
| C1 | robot_2 park y | 1.70 (0.10 inside 1.80) | PASS, tight |
| C1 | Goals, escort ends | x ≤ 2.45; escort end 1.25 | PASS |
| C2 | robot_1 escort vs held robot_3 | gap grows from 1.45 m | PASS |
| C2 | robot_3 escort vs robot_1 at its goal (2.45, −0.3) | 1.24 m at robot_3's escort end | PASS |
| C2 | robot_2 return vs robot_3 | robot_3 has moved 3.7 m before robot_2's hold ends | PASS |
| C3 | Spawn gaps | robot_1–robot_3 1.45; robot_1–robot_2 2.02 | PASS |
| C6 | Sidestep candidate A in the N-S aisle | x_park = x_robot_2 + 0.36: **0.51–0.66 vs limit 0.46** | **FAIL for x_robot_2 > 0.10** |
| C6 | Reverse along the heading (M4 reverses on odometry) | endpoint x = x0 + d·cos(θ + π) stays ≥ −0.46 for θ ≤ −62° (x0 ≤ 0.3, d ≤ 1.35) | PASS for heading −62° to −90°; smoke gate |
| C7 | Goal stack | robot_2 (1.90, 0) to others 0.63 m; robot_1–robot_3 goals 0.60 m | PASS (≥ 0.60) |
| C9 | robot_3 release | 80 wall-s → 34–43 sim-s; dispatch ≤ ~31 sim-s; admission ~58 sim-s | PASS over RTF 0.28–0.39 |
| C12 | Robots / RTF | 3 / ~0.34 | PASS |

C6 is a real build item. `_aisle_band` centres the sidestep band on the
yielder's own x (`retreat_candidates.py`). It has no world wall, and
`grounding_aisle_y_band_m` exists only for x-axis yielders. **B1 needs an
arm-aware world band**, i.e. an x band [−0.46, 0.46] for y-arm yielders.
Without it, candidate A lands in the NE rack whenever the merge forms east of
x ≈ 0.10.

**What M2 should answer.**

- `congestion_detected: true`, `type: bottleneck`. The v2 guidance defines it
  as "several robots queued … one-way congestion, not opposing", which all
  three robots satisfy.
- `involved_robots: [robot_1, robot_2, robot_3]`, `strategy: yield`,
  `yield_robot: robot_2`, `crossing_order: [robot_1, robot_3, robot_2]`.
- `deadlock` is recorded as a near-miss type: the merge pair is mutually
  blocked.

**What Arm B answers (computed).**

- At all four poses, **with or without a mapped zone** at the gate mouth
  (`aperture_1`, (0.4, 0), r 1.5), the verdict is **`blocked_path`, involved
  `[robot_3]`, strategy `reroute`**.
- The head-on rule fails on heading opposition (~80–90°). The intersection
  rule fails because every goal bearing is within ~7–15° of east: the axes are
  parallel, not crossing at 45–135°.
- The held `robot_3` has no robot within 1.0 m ahead of it, so it reads as
  blocked.
- **Arm B has no path to `bottleneck` here.** Its only `bottleneck` output
  comes through the intersection branch, which needs crossing goal axes.
- Executed, `reroute robot_3` re-sends `robot_3`'s goal and releases it into
  the jam. It then closes to ~0.32 m behind `robot_1` and latches.
- With the proposed **held-robot exclusion**, the verdict becomes `unknown
  [robot_1, robot_2]` → `temporary_wait`, then `reroute`. Neither is exempt
  from the latch, so the prediction is **censored at the horizon** either way.
  - The exclusion is an A10 analogue: robots with `start_pending: true` leave
    Arm B's stopped set.
  - It is an owner decision, being an Arm B rule change before the tag.

**Expected-conflict block.**

```yaml
expected_conflict:
  type: bottleneck
  involved_robots: [robot_1, robot_2, robot_3]
  onset_window_sec: [8.0, 40.0]
  min_duration_sec: 2.0
```

**Metrics.**

- The A4 outcome.
- **Gate flow rate:** robots exiting x = 1.7 per 100 sim-s, from the first
  entry at x = 0.7 to the last exit, from GT.
- **Per-robot stop time:** GT speed < 0.02 m/s summed over ≥ 1 s spells.
- **Makespan:** first departure to last position-verified arrival.
- The type label.

**Build fit.**

| # | Item | Size |
|---|---|---|
| 1 | Scenario YAML, per-scenario map with the barrier at 1.2, USD | S |
| 2 | Goal-table row: junction box + 3 arms, `initial_tasks` with `robot_3` held 80 s, `shadow_classical_zones` optional (no effect, above) | S |
| 3 | Arm-aware world lateral band for y-arm yielders (M3, pinned) | S |
| 4 | GT `bottleneck_conflict_active` oracle function + gate-flow scorer | M |
| 5 | Held-robot exclusion in Arm B (owner decision) | S |
| 6 | Constraint pin test (C1–C13; grid over standoff pose × heading −90°…−60°) | M |
| 7 | Mock smoke, n = 3, with a pre-registered prediction: Δt, standoff poses, robot_2 heading, RTF | 3 runs |

### B2 — `priority_urgent_r1` / `priority_urgent_r2` (priority override)

**Why B2 has two active robots, not three.** In a single lane under the
single-yield primitive, a third active robot is either a queued follower or a
counter-flow follower. Both collapse the contrast:

- **Follower on the urgent robot's side.** Flow says that side passes first,
  so urgency and flow agree. There is no priority contrast.
- **Follower on the non-urgent side.** Urgency says the urgent robot passes
  first, so the non-urgent side must yield. But the lone urgent robot passing
  before a platoon produces a second head-on with the follower. In T2b this
  "lone-first" order ended in the permanent `robot_2`+`robot_3` latch on both
  seeds (margin ≥ 0.6485). Urgency is then indistinguishable from
  infeasibility.
- **A perpendicular third robot needs A55-E.** There only the N-S robot can
  yield executably: an x-axis yield is refused, and the N-S passer's escort
  would drive straight south. No counterfactual order exists.

So a three-active B2 is structurally impossible with v1 primitives. It is
recorded as a prereg-v2 item at the junction, where the coverage check already
places the second priority elicitor. B1 (3 robots) and B3 (4) carry the
N-scaling claim.

**Composition.** A **label-counterfactual pair** on the T1
`head_on_asymmetric_wopen_eopen_o0` geometry, which validates both yields.

- The two members are byte-identical except the task labels and the oracle
  block, following the T3a pattern.
- The urgent robot is `robot_2` in `_r2` and `robot_1` in `_r1`. That
  counterbalances the robot_1 and first-slot priors, which would otherwise
  inflate %CP in one member and deflate it in the other.

| Field | `priority_urgent_r2` | `priority_urgent_r1` |
|---|---|---|
| Module | C55 0.55 × 2.0 @ 0 | same |
| robot_1 | (−1.5, 0, 0) → (2.5, 0), `routine_order_delivery` | (−1.5, 0, 0) → (2.5, 0), `urgent_order_delivery` |
| robot_2 | (1.5, 0, π) → (−2.5, 0), `urgent_order_delivery` | (1.5, 0, π) → (−2.5, 0), `routine_order_delivery` |
| `priority` (registry, not rendered) | robot_2: 1, robot_1: 0 | robot_1: 1, robot_2: 0 |
| Oracle | `correct_yielder: robot_1`, `correct_first_passer: robot_2` | `correct_yielder: robot_2`, `correct_first_passer: robot_1` |
| Grounding | derived, stage 2 on (as T1) | same |

**How urgency enters.**

- **M5 registry.** `TaskAssignment` gains `priority: int = 0`. It is additive,
  and absent means 0, so every existing row stays byte-identical. It is set in
  `initial_tasks`.
- **v2 prompt.** Only through the task label, which `format_robot_state_lines`
  already renders as `task=<label>`. The v2 template already tells the model
  to decide "from the robot states (including their stated goals and tasks)".
  - The template text and its SHA do not change, so this is not v3. Labels are
    per-scene data, like T3a's `traverse_aisle`.
  - The integer `priority` is **not rendered**. Rendering it would add a
    state-line field, which is a builder change and would force v3.
  - The two labels have the same form and differ in one token, so neither
    reads as "the odd one out".

**Why no arrival offset, and a finding about FCFS.**

- For two robots approaching at equal speed, Arm B's FCFS is **always a tie**,
  whatever their spawn distances or start delays.
- The FCFS zone is centred on the midpoint of the two stopped positions. The
  robots reach that midpoint (less half the gap) at the same instant, so they
  cross the radius-1.0 circle at the same instant too.
- Algebraically, a departure offset Δt shifts the midpoint by 0.075·Δt.
  Arrival times are then t₁ = t₂ = 3.33 + 0.5·Δt, identical.
- So the tie always falls to commitment (also equal), then to robot_id. The
  nominal answer is `robot_1` passes and `robot_2` yields. The live 3/6 coin
  flip in T2b is noise around that tie.
- **A verified discrepancy.** `_passing_order` sorts by `(-commitment, rid)`
  and yields `order[-1]`, so on a full tie the code yields **`robot_2`**.
  - Two checks confirm it. `test_decide_head_on_breaks_full_tie_by_robot_id`
    pins `yield_robot == "robot_2"`. `resolve_classical` on a symmetric
    ±1.5 → ±0.12 buffer at 0.15 m/s returns order `[robot_1, robot_2]`,
    yielder `robot_2`.
  - The family manifest, the T2b YAML and rev 8.6 all record
    `fcfs_yielder: robot_1`, the opposite reading.
  - Consequences for the nominal answers:
    - `w0p2_eopen`'s correct yielder `robot_2` equals the nominal FCFS pick,
      so its manifest flag `contrasts_fcfs: true` is nominally false.
    - `wopen_e0p2` (correct `robot_1`) is the variant that nominally
      contrasts.
  - Rev 9's rule scores Arm B on the answer it actually produced, and live
    answers are coin flips around the tie. So no score changes. The owner
    should still correct the frozen `fcfs_yielder` and `contrasts_fcfs`
    fields, or annotate them, before the tag. They are recorded here and not
    changed.
- B2 therefore cannot make "default right of way" deterministic by geometry.
  **The pair makes it deterministic by construction.** Arm B's answer is the
  same in both members, so it disagrees with urgency in exactly one member of
  every pair.

**Grounded maneuvers** (derived, L 2.0, `ground_reasoner_result`):

| Standoff (robot_1, robot_2) | Yield robot_1: backup / escort | Yield robot_2: backup / escort | Passer escort end |
|---|---|---|---|
| (−0.12, 0.12) | 1.669 / 2.559 | 1.669 / 2.559 | ∓2.439 |
| (−0.25, 0.05) | 1.539 / 2.489 | 1.739 / 2.689 | ∓2.439 |
| (0.05, 0.30) | 1.839 / 2.739 | 1.489 / 2.389 | ∓2.439 |

Both yields are feasible over the grid. The passer's goal (±2.5) sits
0.061 m beyond the escort end, the validated T1 margin. Arm B reads
**`head_on` (robot_1, robot_2), `yield`** over the whole grid, in both
members.

**Constraint checks.** C1–C13 are inherited from `wopen_eopen`, which is
validated. Only the labels are new. C4 is Arm B `head_on` in both members:
PASS. Timing:

- 2 stacks, RTF ~0.39. Standoff at 19–22 sim-s, trigger 4.6 sim-s later.
- Makespan ~100–120 sim-s. `duration_sec: 200`.

**What M2 should answer.**

- `type: deadlock`, `involved: [robot_1, robot_2]`.
- Either `strategy: yield` with `yield_robot` = the routine robot, or
  `strategy: priority_override`.
- Under v2, `yield_robot` is null for anything but `yield`. A
  `priority_override` answer therefore names no beneficiary. Its implied first
  passer is the robot with the maximum registry `priority`, resolved in M3
  (build item 3).
- **Scoring is decision-level, by route.**
  - Yield route: first passer = the non-yielder.
  - `priority_override` route: first passer = the registry maximum.
  - Both routes are reported.

**What Arm B answers.** It reads no task label, so the answer is the same in
both members: `yield`, with the nominal `robot_2` yielding under the id
tie-break. Its divergent rate is **0 by construction**, the same forced
non-divergence T3a has. B2 is therefore a **semantic-channel tier**: the text
channel carries what Arm B cannot see.

- Adding an urgency rule to Arm B would be a rule addition outside the
  tuning-parity clause, and is an owner decision.
- **Recommendation: do not add one.** Report the channel asymmetry the way T3a
  does.

**Metrics.**

- **Primary: divergent-and-correct rate** over pairs. A pair scores when the
  first passer is the urgent robot in both members. A label-blind model scores
  0 (deterministic) or 0.25 (random).
- **Secondary: %CP per episode.** The urgent robot crosses x = 0 toward its
  goal first, from GT. Tested against chance 0.5.
- The urgent robot's time-to-goal, the `priority_override` label rate, and the
  A4 outcome.
- **Free contrast.** The seed-matched T1 `wopen_eopen` cell is the same scene
  without urgency labels, so its yielder distribution is the no-label baseline.

**Expected conflict:** `deadlock`, `[robot_1, robot_2]`, `[8.0, 40.0]`,
`min_duration_sec: 2.0`.

**Build fit.**

| # | Item | Size |
|---|---|---|
| 1 | Two YAMLs (hand-authored from `wopen_eopen`; the family generator's two-robot asserts stay untouched), pair diff test | S |
| 2 | `TaskAssignment.priority` (M5, additive, default 0, byte-identical when absent) | S |
| 3 | M3 alias: `priority_override` grounds as a yield by every involved robot below the unique registry-max priority, crossing order max-first; no unique max → `strategy=unsupported` (today's behaviour) | S |
| 4 | `PriorityOracleConfig` + %CP scorer (GT x = 0 crossing order) | S |
| 5 | Offline render check: labels render, template SHA unchanged, `prompt_version` 2 | S |
| 6 | Mock smoke per member | 2 runs |

### B3 — `convoy_counterflow` (convoy, 4 robots)

**Composition.** A T2b extension on the A55-J gate with legacy grounding, the
same tier-scoped apparatus difference T2b already registers.

- `robot_1` leads a three-robot eastbound platoon; `robot_3` and `robot_4` are
  held behind it on the centreline.
- `robot_2` is the counter-flow robot.
- The correct resolution is one yield by `robot_2`, then the platoon
  nose-to-tail.

```text
  robot_4    robot_3    robot_1     [A55-J  -0.5..0.5]    robot_2        goals east
  (-2.47,0)  (-1.9,0)   (-1.2,0) --> [=====0.55 m=====] <-- (1.2,0)       (2.45,-0.3)
  held 120   held 120                park (+/-1.124, +/-0.36)             (2.45,+0.3)
                                     escort ends +/-1.774                 (1.85, 0)
```

| Robot | Spawn | Goal | Hold |
|---|---|---|---|
| robot_1 | (−1.2, 0, 0) | (2.45, −0.30) | — |
| robot_2 | (1.2, 0, π) | (−2.00, 0.00) | — |
| robot_3 | (−1.90, 0, 0) | (2.45, +0.30) | `start_delay_sec: 120` |
| robot_4 | (−2.47, 0, 0) | (1.85, 0.00) | `start_delay_sec: 120` |

All tasks are `cross_narrow_aisle`. `scenario_geometry.corridor` has
`center_m` 0.0 and `half_length_m` 0.5. `grounding.mode` is legacy.

**Timing (4 stacks, RTF 0.19–0.26).**

- M5 starts at ~20 sim-s.
- The standoff forms at ~27 sim-s: a 1.08 m approach at 0.15 m/s.
- The trigger comes 2.3–3.1 sim-s later, i.e. 39–49 wall-s after M5 starts.
- Dispatch by ≤ ~75 wall-s, including refusal retries.
- **Release window.** The lower bound on D is the worst dispatch, about
  75 wall-s. The upper bound is `robot_3`'s escort end (~108 sim-s), which in
  wall time is ≥ 340 wall-s. **D = 120** gives T_r = 20 + RTF·120 = 43–51
  sim-s, after dispatch and before the first admission (~70 sim-s).
- **Oracle timeline.**
  - `robot_2` backs up 1.00–1.08 m, then sidesteps, and holds (~50 sim-s).
  - `robot_1` is escorted 1.89–1.97 m (~70 sim-s).
  - `robot_3` is escorted 3.57 m (~107 sim-s).
  - `robot_4` is escorted 4.17 m (~150 sim-s).
  - `robot_2` returns 3.1 m, plus the recurring 8–19 s east-mouth stall seen
    in T2b (~180–190 sim-s).
- **Predicted makespan ~190 sim-s. `duration_sec: 260`** (C10 margin 70 s).
- At RTF 0.21 that is ~1,240 wall-s (21 min) per episode.
- C11: the longest escort, 42 sim-s = 200 wall-s at RTF 0.21, sits well under
  its 15× bound of ~675 wall-s.

**Grounded oracle** (legacy, `ground_reasoner_result`, positions mode):

| Standoff (robot_1, robot_2) | robot_2 backup → park | robot_1 / robot_3 / robot_4 escort | All escort ends |
|---|---|---|---|
| (−0.12, 0.12) | 1.004 → x 1.124, lateral 0.36 | 1.894 / 3.574 / 4.174 | x = 1.774 |
| (−0.20, 0.04) | 1.084 → x 1.124, lateral 0.36 | 1.974 / 3.574 / 4.174 | x = 1.774 |

- The yield holds until the last passer in `crossing_order` clears.
- `CrossingChain` admits one passer at a time, on the previous passer's
  clearance. The strict chain is built, so B3 needs no M4 change.

**Constraint checks.**

| Id | Check | Value | Verdict |
|---|---|---|---|
| C1 | robot_4 spawn | x −2.47 (0.03 inside the band) | PASS, tight |
| C2 | Passers past the parked robot_2 (lateral 0.36) | exempt pair (pair-scoped exemption) | PASS by exemption, not by distance |
| C2 | robot_1 backup path (alternative) vs held robot_3 | 0.78 m along the lane at park −1.124; 0.86 m to the lateral pocket | PASS |
| C2 | robot_2 escort end (alternative, x −1.774) vs held robot_3 (−1.90) | 0.13 m | Latches: the alternative is censored, a lower-bound margin as in T2b |
| C3 | Spawn gaps | robot_1–robot_3 0.70; robot_3–robot_4 0.57 | PASS (0.57 at R-QUEUE-2) |
| C4 | Arm B `head_on` (robot_1, robot_2) over the 45-case grid | 35/45; **10/45 flip to `blocked_path [robot_3]`** (all at westward shift ≥ 0.1 m or separation 0.70) | Registered as 35/45; 45/45 with the held-robot exclusion |
| C7 | Later escort ends (1.774, 0) vs goals (2.45, ±0.3) | 0.74 m | PASS |
| C7 | robot_4 goal (1.85, 0) vs robot_2 park (1.124, ±0.36) / other goals | 0.81 / 0.67 m | PASS |
| C8 | Spawns vs FCFS zone (1.0 around ~0) | 1.2 m | PASS (0.2 margin) |
| C9 | Release | D 120 wall-s → 43–51 sim-s | PASS over RTF 0.19–0.26 |
| C12 | Robots / RTF | 4 / 0.21–0.24; 3 of 8 four-stack bring-ups failed | Needs the lifecycle-gate fold |

Moving the queue 0.1 m east (`robot_3` at −1.8, `robot_4` at −2.4) makes C4
worse: 18/45 cases flip. The queue is pinned as far west as the band allows.

**The omitted-queue trap: Arm B's B3 outcome is censored by construction.**

- Arm B, and any Arm A answer that lists only the pair, commands a two-robot
  yield. `robot_3` and `robot_4` are then not under a linked wait.
- At T_r (43–51 sim-s) they receive their goals and drive east along y = 0.
  `robot_2` is parked at (1.124, ±0.36) and holds until `robot_1` clears
  (~70 sim-s).
- Under this command `robot_3` is not an admitted passer, so the pair
  `robot_2`+`robot_3` is latchable. Its lateral offset is 0.36 m, so the gap
  falls below 0.45 m once robot_3 is within √(0.45² − 0.36²) = 0.27 m of the
  park x, i.e. at x ≈ 0.85. That happens on either pull-off side, while
  `robot_2`'s hold is still active. This is **T2b's permanent bystander
  latch**, the mechanism behind its frozen margin.
- A trailing `robot_4`, or a `robot_3` that closes on the slower escorted
  `robot_1` (0.15 vs 0.10 m/s), adds a follower latch at ~0.32 m.

**A follower-headway polygon does not fix this. Retracted.**

- Extending the queued robots' `forward_stop` so they queue at ~0.57 m would
  remove the follower latch. It would not remove the bystander latch against
  the parked yielder: lateral 0.36 m is outside the polygon's ±0.12 m reach,
  and within the latch radius.
- So no scoped Nav2 change turns Arm B's path into an executable alternation.
- **Registered consequence.** Any B3 answer that omits the queued robots ends
  in a permanent latch, and the episode is censored at the horizon.
  - This applies to Arm B always.
  - It is the outcome contrast of B3, in the same sense the occupied default
    is T3b's.
  - The A-vs-B makespan and yield-count comparison therefore has no executed
    Arm B side. Makespan is reported for Arm A against the forced-order
    harness's oracle and alternative arms.
- **Alternative left open (not recommended).** Hold the queue until it is
  released after the pair resolves: D ≈ 300 wall-s, T_r ≈ 75–105 sim-s.
  The second head-on would then form against a held robot. This depends on
  an untested assumption: that a `start_pending` robot can be admitted and
  escorted before its release. It also removes the convoy conflict from Arm
  A's first analysis.

**What M2 should answer.**

- `type: deadlock`; `bottleneck` is accepted and recorded.
- `involved: [robot_1, robot_2, robot_3, robot_4]`.
- `strategy: convoy`, or `yield` with `yield_robot: robot_2`.
- `crossing_order: [robot_1, robot_3, robot_4, robot_2]`.

**What Arm B answers (computed).** `head_on (robot_1, robot_2)`, `yield`,
nominal `yield_robot: robot_2`, `crossing_order: null`. Two robots are
involved, so the platoon is never ordered, and it never emits `convoy`: the
strategy is outside its policy table. Its nominal yielder matches the oracle
only through the robot_id tie-break. The live result is a coin flip, as in
T2b.

**Grounding `convoy`.** Today `convoy` grounds to a bounded `temporary_wait`
(`strategy=unsupported`).

- **Build alias:** `convoy` grounds as a yield by the unique involved robot
  whose goal bearing opposes the majority. The crossing order is the
  decision's if it is a valid permutation, otherwise queue order by distance
  to the gate. No unique minority → `strategy=unsupported`.
- **Consequence.** In this apparatus, `convoy` and "`yield` robot_2 + platoon
  order" are **executionally identical**. The label is the only difference.
- **Scoring.**
  - Primary: **platoon-correct decision rate.** Yielder = robot_2, and the
    order lists robot_1, robot_3, robot_4 consecutively before it, under
    `strategy` ∈ {convoy, yield}.
  - Secondary: the `convoy` label rate, registered as a novelty claim with no
    external baseline.
  - Flow: makespan and the number of executed yields (1 vs ≥ 2), Arm A vs Arm B.
  - Negative probe: the T1-X intersection's `convoy` count, which should be 0,
    at zero build cost.

**Expected conflict:** `deadlock`, `[robot_1, robot_2, robot_3, robot_4]`,
`[15.0, 50.0]` (four-stack start ~20 sim-s), `min_duration_sec: 2.0`.

**Build fit.**

| # | Item | Size |
|---|---|---|
| 1 | YAML (A55-J = T2b barrier), map, USD; goal-table row | S |
| 2 | `fc_launch.sh` four-stack lifecycle gate + M5 log pre-create (intersection build item 5) | S |
| 3 | M3 `convoy` alias (shares a slice with the B2 alias) | S |
| 4 | Rescorer: `censored_omitted_queue` flag (latched robot not in the command, gap < 0.45 m to a parked yielder) | S |
| 5 | Held-robot exclusion in Arm B (owner decision; shared with B1) | S |
| 6 | Forced-order harness to four robots; both orders, n = 2 seeds; censored rule | M + 4 runs |
| 7 | Constraint pin test (grid above, plus the RTF window) | M |
| 8 | Mock smoke, n = 3, recording RTF and hold-back positions at trigger | 3 runs |

**Slip order.** If the freeze is threatened, B3 slips first, as the coverage
check anticipates. It carries the robot cap, four-stack RTF, the censored
Arm B side and the harness extension.

---

## 4. Head-On Family Consistency Redesign

### What changes, what stays

- **Stays.**
  - The family is already C55 (0.55 × 2.0 at 0).
  - Spawns ±1.5 satisfy R-RUN (0.5 m run) and R-FCFS (0.5 m beyond the 1.0
    zone).
  - Blockers at 0.2 m behind the spawn feed the `required_room` 1.079 oracle.
  - The ±2.5 goals of `wopen_eopen` and `head_on_deadlock` are R-GOAL-FAR
    instances (m_g 0.061).
  - T2b is the C55-L queued instance. T3b is D3. T3a is D1.
- **Changes under the conservative variant.**
  - Documentation only: this vocabulary, the audit table, deviations D1–D3
    with their reasons, and a manifest alias column mapping the existing names
    onto the scheme.
  - C1–C13 pin tests for the scenes that lack them (`head_on_deadlock`, the
    family, `normal_flow`). These run offline and need 0 VM runs.
- **Would change under the full-consistency variant.** One goal rule, one
  module length, and one width everywhere, plus a machine-readable
  `m5_settings` block in every YAML.

### Migration cost table

| # | Proposed change | Validated results it invalidates | Re-validation batch | Cost | Verdict |
|---|---|---|---|---|---|
| M1 | T3a width 0.50 → 0.55 | T3a mock smokes (both members); funded battery 1 T3a comparability; closability (needs a > 0.30 m lidar cross-section, so the blocker grows past its recorded 1.82× scale confound) | Re-author the blocker; 2 member smokes | 2 runs, ~1 day | Reject: D1 is load-bearing |
| M2 | Goal rule ±2.6 → ±2.5 (drop D2) | `_bshort` 15/15 (gpt-4o 6/6, ER-2 6/6 + 3); A1 adjudication; designed escort margin back to 0.061, realised about −0.04 to −0.01 | Both sides n = 3 mock + n = 6 per model pilot | ~18 runs, 2–3 days (gpt-4o credit-gated) | Reject |
| M3 | Goal rule ±2.5 → ±2.6 for T1 (`wopen_eopen`, `head_on_deadlock`) | T1 pilot comparability; T1 tuning-basket confirmation run (T1B1 full-rate); moves T1 goals outside R-TRACK | 1 confirmation + 2 T1 smokes | 3 runs, ~1 day | Reject: it spreads a deviation |
| M4 | Family L 2.0 → 1.0 (one length everywhere) | Every family oracle (`required_room` 1.079 → 0.914, blocker feasibility re-derived); family validity report (2026-09-18); `_bshort` 15/15; A1; derived grounding (1.7 binds, so T1/T2a move to legacy under pooling rule b); the `fcfs_zone_radius_m` 1.0 rationale (= T1 half-length) | Regenerate 7 YAMLs + USDs; validity n = 3 × 3 cells; `_bshort` re-pilot 12; T1 confirmation 1; basket re-check 1 | ~25 runs, 4–5 days | Reject |
| M5 | T2b L 1.0 → 2.0 | T2b margin ≥ 0.6485; three-robot smoke | — | — | Impossible: robot_3's escort end 0.06 m from robot_1's goal |
| M6 | T3b to the standard placement | T3b 269-case pin; parallax check; both mock smokes | — | — | Impossible: k = 3 needs the park point in the junction |
| M7 | Machine-readable `m5_settings` block + preflight in every YAML | None behaviourally; USD content must be re-verified identical (schema is `extra="forbid"`) | Offline: schema, tests, md5 equality of regenerated USDs | 0 VM runs, ~1 day | Defer to after the tag (it touches every frozen YAML) |
| M8 | Rename to the new naming scheme | Prereg text, run ids and artifact paths cite the old names | — | — | Reject: alias column instead |
| M9 | C1–C13 pin tests for unpinned scenes | None | Offline | 0 runs, ~0.5 day | Adopt (both variants) |

### Variants and recommendation

| Criterion | Conservative | Full consistency (M1 + M2 or M3 + M4 + M7) |
|---|---|---|
| Validated results invalidated | none | family oracles, `_bshort` 15/15, A1, T3a smokes, T1 basket confirmation |
| Re-validation | 0 VM runs; ~0.5 day offline | ~25–45 VM runs; ~4–6 days; gpt-4o credit-gated |
| New-scene cost (both) | B1 3 + B2 2 + B3 7 ≈ 12 runs (plus Arm B smokes ≈ 15) | same |
| Measurable gain | — | none: every deviation is load-bearing or a rule instance |
| Risk | Three recorded deviations stay | Re-opens validated cells days before the freeze |

**Recommendation: conservative.** The audit shows the built battery was
already consistent in everything but three load-bearing deviations. The full
variant spends a week re-validating geometry that the rules show was right.

---

## 5. Freeze Impact

### Run matrix additions

| Cell | Scenario | Arms / condition | N | Primary test | Episodes × wall |
|---|---|---|---|---|---|
| B1 bottleneck | `bottleneck_merge` | A vs B paired, dual; derived | 15 pairs | Descriptive: A's `bottleneck` rate with one-sided 95% binomial bound; pre-gate yielder/order agreement with the feasibility-determined oracle; flow metrics. Arm B has **no path to `bottleneck`** (structural, disclosed) | 30 × ~10 min (200 sim-s @ 0.34) ≈ 5 h |
| B2 priority | `priority_urgent_r1` / `_r2` | A executed (B shadow), dual; derived | 15 pairs (= 30 episodes) | Divergent-and-correct rate, one-sided 95% binomial lower bound > 0.5; secondary %CP vs 0.5 per member | 30 × ~8.5 min (200 @ 0.39) ≈ 4.3 h |
| B3 convoy | `convoy_counterflow` | A vs B paired, dual; legacy (not poolable with derived) | 10 pairs | Descriptive: platoon-correct decision rate; `convoy` label rate (novelty, no baseline); A makespan vs forced-order harness arms; Arm B outcome censored by construction (omitted-queue latch) | 20 × ~21 min (260 @ 0.21) ≈ 6.9 h |
| T1-X | `intersection_bottleneck` | existing probes | 10 | Add: `convoy` label count (should be 0) | 0 |

- **Budget.** +80 episodes and ≈ 16 h of simulation on top of the ≈ 390-episode,
  33–43 h baseline. That is +37–48%.
- **VLM calls.** ~80–240 more, at 1–3 per episode.
- **Credit.** OpenAI credit is exhausted, so gpt-4o cells are gated on a
  top-up.
- **Smokes.** About 15 pre-collection smoke runs.

### Per-class metrics to register

| Class | Metrics | Definition (GT unless stated) |
|---|---|---|
| All | A4 outcome, A5 safety columns, degradation breakdown | As rev 9.3 |
| Bottleneck (B1) | Gate flow rate; per-robot stop time; makespan; type label | Exits at x = 1.7 per 100 sim-s from first entry at x = 0.7; Σ spells ≥ 1 s at speed < 0.02 m/s; first departure → last verified arrival |
| Priority (B2) | Divergent-and-correct; %CP; urgent time-to-goal; route split | First GT crossing of x = 0 toward goal; decision-level first passer by route |
| Convoy (B3) | Platoon-correct decision; `convoy` label rate; makespan; executed yields; total transit time | Yield count from M4 command records |

Scoring bottleneck or priority scenes on the deadlock rubric would recreate
the coverage gap one level down. These metrics must be registered with the
cells.

### Scoping sentences to register

1. **Throughput** (verbatim from the coverage check): *no episodic ≤4-robot
   battery can measure the throughput-defined congestion regimes that dominate
   warehouse literature; the study's construct is conflict-resolution quality
   at constrictions, for which the mini-games metric set (success/deadlock
   rate, time-to-goal, stop time, flow rate, %CP) is the established
   instrument.*
2. **Crowding** stays in the enum as a documented distractor label with no
   elicitor, following the ≥ 5-agent CrowdNav convention and its dependence on
   throughput.
3. **Blind and L-corners** are excluded architecturally: the overhead camera
   removes occlusion by design. **Roundabouts** have no counterpart geometry on
   a plus-shaped floor. **Livelock and queue spillback** are not named
   phenomena, having no 2024–2026 AMR scoring precedent.
4. The battery **represents** the canonical episodic classes reachable under
   its constraints. It does not claim to be exhaustive.
5. **Novelty claims with no external baseline:** convoy as a commanded, scored
   strategy (B3), and priority override by a VLM from a text urgency channel
   (B2).
6. **Fidelity:** the capacity-one module is faithful to standard-field AMR
   corridors only. The sim is 2.6–4.1× slow for its size. It is 11–20× more
   forgiving of reasoner latency than the MiR250 reference, so no
   latency-sufficiency claim transfers to a real fleet.

### Prompt implications

- **B2 urgency fits the task-label channel. No v3.**
  - The label renders through `format_robot_state_lines` under the frozen v2
    template, which already says to decide from "stated goals and tasks".
  - The template SHA and `prompt_version: 2` are unchanged. The collection
    configuration gains per-scene `initial_tasks` labels, which it already
    varies per tier (T3a).
- **The registry `priority` integer is M3-only.** Rendering it would add a
  state-line field. That is a builder change: a new prompt version, a
  calibration mini-pilot, and no pooling across the break.
- **No v2 guidance covers `convoy` or `priority_override`.** Both appear only
  in the output enum.
  - B2 and B3 therefore measure **uncoached** elicitation: whether the model
    maps urgency or platoon semantics onto the enum by itself.
  - The primary B2 and B3 metrics are decision-level (who yields, what order),
    so they stay scorable whatever label the model picks.
  - Coaching the model would be v3. It would re-open every pilot and the
    calibration mini-pilot. If the owner wants it, it must land once, before
    any collected cell, together with the "roughly 0.3 m wide" correction.
    **Recommendation: no v3 for v1.**
- **`yield_robot` is null for `priority_override` under v2's bullet text.**
  The beneficiary is resolved from the registry (B2 build item 3), and that
  route is reported separately.
- **Order and stage 2.**
  - `crossing_order` is requested "when three or more robots must be ordered".
    B1 (3) and B3 (4) request it; B2 (2) does not.
  - `prompt_robot_order: random` draws 3! and 4! permutations.
  - Stage 2 is on for B1 and B2 (derived) and absent for B3 (legacy, the T2b
    precedent).
- **Grounding aliases change semantics before the freeze.** Today every
  `convoy`/`priority_override` answer degrades to a wait. After the alias
  slice they execute. This is a pooling-rule addendum: no decision with those
  strategies pools across the alias commit. It must land before the tag.

---

## Risks and Mitigations

| Risk | Where it bites | Mitigation |
|---|---|---|
| Merge synchrony: Δt < 0 gives an uncleared same-direction latch; Δt ≥ 3 s gives no event | B1 | Designed Δt +1.4 s; smoke records Δt; no-event and follower-latch episodes counted and reported, never silently re-run |
| N-S yielder sidestep into the NE rack (candidate A at x 0.51–0.66) | B1 | Arm-aware world band (build item 3) before any B1 run |
| Reverse along a slanted heading drifts west | B1 | Heading gate −90° … −62° pinned; smoke records heading at trigger |
| Arm B names a held robot `blocked_path` and releases it | B1 always, B3 10/45 | Held-robot exclusion (owner); otherwise registered as Arm B's live behaviour |
| Bystander latch (released queued robot vs parked yielder, lateral 0.36 m) when an answer omits the queued robots | B3 always under Arm B. T2b's Arm-B-executed episodes share the mechanism: robot_3 is released at 55 wall-s, is not in Arm B's two-robot command, and transits past robot_2 parked at (1.124, ±0.36). Inferred, not observed; verify before T2b collection | Registered as censored by construction; `censored_omitted_queue` flag; T2b smoke with Arm B executed |
| Four-stack RTF below 0.19 or bring-up failure (3/8) | B3 | Lifecycle-gate fold; RTF recorded per run; C9 window re-derived from the smoke |
| Park y 1.70 is 0.10 m inside the band | B1 | Pinned; abort criterion GT \|y\| > 1.80 |
| Escort end margin 0.061 m to the ±2.5 goals | B2 (inherited from T1) | Validated in the family; unchanged |
| Decision-level scoring of `priority_override` depends on registry resolution | B2 | Route-split reporting; the yield route alone suffices for the primary test |

---

## Not Settled by the Data

- **The B1 merge standoff pose and Δt distribution.** They are predicted from
  corpus speeds. No run has fed a N-S robot into an E-W gate.
- **Whether Nav2 transits A55-E's 1.0 m gate unescorted.** The Nav2 return
  legs of the yielder (B1 `robot_2`) and of the passers after their escorts
  are inferred from the T3a/T2b transits, not observed at x = 0.7–1.7.
- **Whether a `start_pending` robot can be admitted and escorted before its
  release.** This decides whether the long-hold B3 alternative is viable.
- **How VLMs read `urgent_order_delivery`** without a guidance line, and
  whether they use `priority_override` or `yield`.
- **RTF with four full stacks on the B3 scene** (0.21–0.24 was measured on the four-way).
- **Whether T2b's own Arm-B-executed episodes hit the bystander latch.** The
  mechanism is the same, but it is unobserved.

---

## References

- Coverage check: `reports/Congestion scenario coverage check.md`
- Intersection literature: `reports/Four way intersection robot congestion.md`
- Battery build map: `docs/superpowers/specs/2026-09-27-scenario-battery-design.md`
- Intersection design study: `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
- Research design (binding, rev 9.3): `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
- Head-on family design: `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
- Three-robot feasibility: `docs/reports/2026-09-27-three-robot-feasibility.md`
- T1 tuning basket: `docs/reports/2026-09-29-t1-tuning-basket.md`
- [ROBOTIS TurtleBot3 - official docs](https://emanual.robotis.com/docs/en/platform/turtlebot3/features/)
- [MiR250 - official specifications](https://mobile-industrial-robots.com/products/robots/mir250/specifications)
- [Amazon Robotics family - AllAboutLean](https://www.allaboutlean.com/amazon-robotics-family/)
- [Kiva Systems - IEEE Spectrum](https://spectrum.ieee.org/three-engineers-hundreds-of-robots-one-warehouse)
- [Geek+ P800R - QVIRO spec sheet](https://qviro.com/product/geek/p800r/specifications)
