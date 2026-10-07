# v3 Scene Design — MAPD-5, Axis-Choice Junction, Persistence, Scale, Dual Conflict

**Prepared:** 2026-10-06

**Revision history:**

- Initial draft: concrete designs for the v3 scenes S1 (MAPD-5, the Ghofrani scenario analog), S2 (asymmetric junction, axis choice scored), S3 (symmetric both-axes junction), S4 (persistence-judgment classification), S5 (N = 8 scale probe) and S6 (dual conflict). It covers code-derived geometry, density feasibility, oracles, free-flow segment lists, migration and open questions.

---

## Question and Verdict

The prereg-v3 design (`2026-10-06-prereg-v3-design.md`, rev 2) names the v3
scenes but does not fix their geometry. This document does for them what
`2026-09-29-unified-scene-design.md` did for B1, B2 and B3. For each scene it
gives the layout, spawns, goals and props, with every number derived by the
repo's own functions. It then checks density and feasibility before any
oracle, as v3 Step 3 requires.

It is a design document only. It adds no scenario YAML, no config and no code,
and it involves no VM run and no API call. The local test suite is untouched,
because only this file changes.

**Verdicts.**

| Scene | Verdict | Key numbers |
|---|---|---|
| **S1** MAPD-5 (Ghofrani analog) | **Fails density feasibility as a literal analog on the C55/A55 floor at N_A = 5.** It is registrable only with three named prerequisites (below). The family axis and the run protocol are specified. | The floor inside the band is 54.3% obstacle, against their 10%. It has 5.4 free 0.55 m cells per agent, against their 40.5, which equals their density at N_A ≈ 37. Off-route parking capacity is zero. A node-occupancy hold gridlocks in 400/400 episodes at N = 5. With spawns on nodes, only a release stagger Δ < 4.42 sim-s avoids robots running into unreleased robots. At the registered Δ = 4 the Layer-2-off proxy completes 0/400; first encounters come at a median of 15.0 sim-s, 309/400 of them at the junction. |
| **S2** asymmetric junction | **Feasible. Use a parked follower on an E-W arm**, not pocket-distance asymmetry. The χ-cheaper axis is then necessarily N-S, the shipped default (derived, not chosen). | One follower adds +0.5 χ. The axis gap at the IB10 standoff is 0.486. Over 14 recorded jams the gap ranges from 0.227 to 0.739, so it is ≥ ε = 0.15 in 14/14. The mirrored N-S passer end is \|y\| = 1.669: +0.131 m to the band, or +0.031 m with the full M1 budget charged. |
| **S3** symmetric junction | **Feasible**, but equivalence must be judged per episode, at the dispatched snapshot. | The axis-set gap over 14 recorded four-way jams runs from −0.273 to +0.239. 11/14 fall inside ε = 0.15. Even the "symmetric" IB10 is not symmetric in 3/14 jams. |
| **S4** persistence-judgment cell | **Feasible as a held-robot tableau with log-only probes.** A driven robot on the loop map self-detours, so it must be held. Held robots give no stall evidence, so no triggered analysis fires. | 3–9 probes fall before removal, depending on RTF and the registered clear time. |
| **S5** scale probe | **Feasible for classification and triage at N = 8, and also at N = 10.** Resolution cannot be scored (six reasons below). | The lead radius is 1.15 and followers sit 0.65 behind. The non-jam pairwise floor is 0.650 m throughout the approach. |
| **S6** dual conflict | **Not subsumed by S1, and not resolvable on the loop map with current primitives.** It is specified as a decision-scored dual-conflict cell; executed outcomes are not scored. | S1's proxy gives a disjoint second conflict within 60 s in only 34/400 episodes at the registered Δ = 4. Larger staggers inflate the rate with collisions against unreleased robots (268/400 at Δ = 20, but only 21 survive excluding those). A head-on in the second aisle ends its escort in a rack (x = −0.773) or parks past the end of the aisle (x = 2.923). |

**Six findings change the plan.**

1. **The MAPD floor has zero off-route parking capacity.** Every point of the
   free floor in the band sits within 0.45 m of some lane or node.
   - So the analog needs one of three things: a wandering-mode analog, a
     horizon cut, or floor surgery.
   - With N_A = N_G and robots spawning on nodes, every arrival process
     is degenerate except a narrow window. Δ = 0 gives a synchronized
     5-way junction pile-up (400/400). Any Δ ≥ 4.42 sim-s makes the first
     robot drive into a node whose occupant has not been released (all
     321 "node handoff" first encounters at Δ = 20 were this artifact).
     The registered Δ = 4 sits inside the window.
   - At Δ = 4, 77% of first conflicts are junction crossings or head-ons
     between robots on different arms. Grounding them needs per-snapshot
     junction `arms` (finding 5). Node handoffs (a robot arriving where
     another dwells) need a further M3 grounding that does not exist.
2. **A N-S follower cannot exist.** The cross-traffic goals at radius 1.75
   and the 1.80 band leave no N-S slot 0.57 m behind a spawn.
   - So in an S2 cell the follower's +0.5 always lands on the E-W axis.
   - The correct axis therefore always coincides with M3's default.
   - S2 is scored on emitted plans only, against S3 as its baseline.
3. **The axis-set χ noise is about twice the order noise.** The order
   noise is a 0.142 m maximum over 9 runs. The axis noise is 0.273 m over
   14 runs.
   - ε = 0.15 was sized for order. For axis sets it must be re-measured,
     as the v3 rule says, and the choice changes S2's floor (see S2).
4. **A follower listed as involved breaks the composite today.**
   - In the mirrored grounding the parked robot becomes a zero-χ recede
     candidate and a third receder. That needs the unbuilt N-way release
     chain.
   - In the shipped grounding it becomes a crossing passer.
   - A parked-robot exclusion is a build item.
5. **Junction `arms` are static per robot.** MAPD robots change arms on
   every leg, so S1 needs `arms` derived per snapshot. This is M3 contract
   work, on top of Step 3's registry work.
6. **A resolution-scored dual-conflict cell needs two in-band, resolvable,
   disjoint conflicts.**
   - The plus floor admits only one in-band resolvable head-on centre
     (|c| ≤ 0.27 around x = 0).
   - The loop map's second aisle admits none.

---

## Sources and Method

| Source | What it supplied |
|---|---|
| `docs/superpowers/specs/2026-10-06-prereg-v3-design.md` rev 2 (this branch) | Binding constraints for every step |
| `docs/superpowers/specs/2026-09-29-unified-scene-design.md` | s ≈ 3.3, C55/A55 modules, rules R-*, checks C1–C13 |
| `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md` | Stop mechanics; the Scheme A row "2, N-S, J2" (passer end \|y\| 1.668, +0.132 to the band) |
| `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (this branch) | χ = s·D_SPACE + t·N_f; the χ-ε rule (ε = 0.15); the STALE instrumentation ruling and the 1.75 → 1.65 fallback; the MAPD candidate registration |
| `feat/prereg-v2-composite@b5cafe4`: `reasoning/rag/{scene_geometry,maneuver_geometry,command_grounder}.py`, `config/rag.yaml`, `isaac/vgu_sim/config.py`, `orchestrator.yaml`, `congestion_detector.py`, `scripts/vm/fc_launch.sh` | Every derived number below. The χ, stagger, J2, `tracked_extent_m`, loop-map and junction-oracle code exists only on this commit, not on the spec lineage. |
| Same commit, `docs/reports/`: `2026-10-01-m1-y-extent-verification.md`, `2026-10-01-robot1-stale-rootcause.md`, `2026-10-03-step7b-oracle-freeze.md`, `2026-10-03-plan-grammar-fixes.md`, `2026-10-02-loop-preemption-smoke.md`, `2026-10-05-free-flow-table.md` | Clean poses, the stagger window, the order-ε measurement, loop geometry, the free-flow method |
| `data/logs/vm_runs/` in the main checkout (gitignored): 14 four-way GT files | Settled-jam standoff poses for the axis-set χ noise |
| Asadi, Nowé, Ghofrani, GECCO '25, 10.1145/3712256.3726339, read from the local PDF | §3 problem statement, §4.1.1 setup, Table 2 |
| `reports/Swarm congestion foundations.md`, `research_notes/.../swarm_robotics_congestion.md`, `reports/VLM centralized multi robot coordination.md`, `research_notes/.../vlm_scene_coordination.md` | Marcolino / dos Passos lineage and the Garg / MIT-REALM line, with their verification status |

**Method.**

- Every geometric number was produced by M3's own functions on a
  `git archive` of `b5cafe4`. The functions are `ground_junction_clear_phases`,
  `recede_cost`, `rank_recede_candidates`, `recede_follower_count`,
  `park_offset_m`, `passer_clearance_m` and `pull_off_lateral_m`.
- Parameters came from that tree's `config/rag.yaml`: s = 1.0, t = 0.5,
  ε = 0.15, mode `derived`.
- The axis-set noise was computed from GT at the first settled-jam frame:
  all four robots within 0.5 m of the centre, all speeds < 0.01 m/s.
- The S1 hotspot and density numbers come from a kinematic Monte Carlo. Its
  assumptions:
  - robots run at 0.15 m/s on nominal piecewise-linear centreline and lane
    routes;
  - each robot dwells for the registered time at every node;
  - an encounter is a GT centre gap < 0.45 m, and both robots then freeze
    (the Layer-2-off proxy);
  - Nav2 deviation is not modeled.
- The scripts ran from a session scratchpad and are not committed. Each table
  names its function or model, so it can be regenerated.
- **Every number is a prediction, not an observation of these scenes.**

---

## Shared Constraints (inherited, restated once)

| Constraint | Value | Source |
|---|---|---|
| Tracked band | \|x\| ≤ 2.5, \|y\| ≤ 1.80; \|y\| = 1.8 verified stationary, 2.0 reached clean once | y-extent report, Run B |
| Pair latch | 0.45 m, permanent unless a command exempts the pair | `safety.yaml`; unified design |
| STALE pocket rule | Two stationary robots < 0.6 m apart sit in M4's `stale_unsafe` band, and marker-overlap STALE was observed at 0.076–0.144 m. Every new stationary pocket keeps ≥ 0.6 m (design target 0.65). Every new (marker, pose) pair is unverified until probed: the dropout is a sub-pixel-phase effect specific to marker × pose. | step-7b ruling (iv); root-cause report |
| Marker 1 at (−1.75, 0, yaw 0) | Reproducible 74–82% STALE. Fallback: re-radius 1.75 → 1.65 on both E-W arms (−1.65 verified clean, +1.65 untested). | v2 step-6 ruling |
| Verified-clean poses (marker: pose) | 1: (−2.4, 0), (−1.65, 0), (1.75, 0), (−1.37, 0.359). 2: (±1.75, 0) (−1.75 mildly degraded), (1.85, 0), (2.4, 0), (1.481, −0.344). 3: (0, −1.2), (0, −1.8), (0, 1.75). 4: (0, 1.2), (0, 2.0), (0, −1.75). | y-extent and root-cause reports |
| Mover legality | ≥ 0.55 m GT to every non-exempt robot | intersection study |
| Queue spacing | ≥ 0.57 m (R-QUEUE-2); followers closing on a stopped leader latch at ~0.32 m | unified design |
| χ weights / ε | s = 1.0, t = 0.5 per follower; ε = 0.15 (order, verification only); re-measured per family | `GroundingParams`; v2 χ-ε ruling; v3 Step 2 |
| Junction composite | offset 1.2, stagger 0.2 (second pocket 1.0), J2 = 1.1, `tracked_extent_m` 1.75 | `orchestrator.yaml` goal table |
| GT clock offset | Fitted per run from odometry (0.300 s with 1 robot, 0.500 s with 4); never a constant | v3 Step 0.7 |
| Free-flow method | `solo_in_space`, origin `own_departure`, arrival `gt_within_0.35_stay_0.5`, one table keyed by (scene, robot or segment) | free-flow report |
| Detour family | NO-GO expected (fix-invariant NavFn flip) | v3 Step 1 |
| Stall trigger | 12 wall-s; ≈ 2.4–4.6 sim-s at RTF 0.2–0.38 | `orchestrator.yaml` |
| Stacks and RTF | 2: 0.39; 3: ~0.34; 4: 0.21–0.24 (3/8 bring-up failures pre-gate); **5 and 8: never measured**; `fc_launch.sh` launches one Nav2 stack per scenario robot | notes 2026-09-28 / 2026-09-29 |

---

## S1 — MAPD-5 Emergent-Congestion Family: Ghofrani Scenario Analog (GECCO '25, 10.1145/3712256.3726339)

### Ghofrani parameters adopted, and the mapping

The measures are **analogous, not directly comparable**: grid MAPD with
discrete steps against continuous Nav2 at 0.15 m/s. Values below were read
from the PDF. Each "§" reference is to the paper.

| Parameter | GECCO '25 value | S1 registered value | Mapping note |
|---|---|---|---|
| Grid / floor | N_Y = N_X = 15 (225 cells) | C55/A55 floor inside the tracked band, 5.0 × 3.6 m | One overhead camera bounds the floor. |
| Task nodes N_G | 5 (§4.1.1) | **5**: Wp, Wm, N, S, E (layout below) | Adopted as is |
| Tasks per agent N_T | 5 orders (§4.1.1); a task is a destination node; pickup and delivery modes alternate (§3) | **5** destination nodes per robot, alternating pickup and delivery labels | Adopted as is |
| Agents N_A | 10 for tuning; {5, 10, 25} in evaluation (Table 2) | **5** (S1); 10 reserved for the S5 MAPD rung (v3 Step 5) | Adopted as is. See Open Question S1-9 on how this interacts with S5 at N = 8. |
| Static-obstacle ratio N_O | 10% (22.5 of 225 cells) | **Not realizable.** The band is 50.7% racks; with the A55-E gate blocks it is 54.3%. | Derived below |
| Start nodes | "each agent starts from a designated node" (§3) | Each robot starts on a distinct task node. The assignment is seeded. | See the parking finding below |
| Finished agents | Switch to **wandering mode**: travel to the node with the lowest agent concentration (§3) | Wandering analog. Requires new M5 work. | The floor has no other parking (derived) |
| Conflict handling | Local wait / repath / random actions with priorities (§3) | **Layer 2** (detection and resolution); Layer-2-off is the control | That is the experiment |
| Runs | 100 random configurations per setting (§4.2, Table 2) | A **100-seed registered list**. The family axis is the seeded task order and start assignment. Confirmatory n is **R = 20 per arm, registered**, from the first 20 seeds; seeds 21–100 are an extension only. | GECCO randomizes whole configurations. We randomize task order and start assignment on a fixed floor. Stated, not hidden. |
| Horizon | 800 steps; at N_A = 5 the baseline makespan is mean 149, sd 32, 0 failed runs (Table 2), so the cap is 5.4× the mean | **H = 600 sim-s.** That is 3.4× the predicted free-flow median of 177 sim-s (Δ = 4), a deliberately shorter ratio. | Budget-bound; see the run cost |
| Measures | Makespan M(Π); completeness (failed runs); throughput = completed orders / (N_T·N_A) over time (§4.2) | Makespan and time-to-full-resolution; completeness via outcome classes; throughput as completed tasks / 25 over sim time; plus `delay_vs_free_flow` per segment, which they lack | Analogous only |

**Obstacle density cannot be matched, and the existing racks already exceed
10%.** Within the tracked band, the free floor is:

- the E-W aisle, 5.0 × 1.2 = 6.00 m²;
- plus the N-S strips outside it, 1.2 × 2.4 = 2.88 m²;
- for a total of 8.88 of 18 m², which is **50.7% obstacle**;
- the A55-E gate blocks add 0.65 m², giving **54.3%**.

Across the whole 12 × 8 floor the racks are 76.5%. Removing racks would
change the module, which v3 forbids (S1 uses the existing map).

**Free cells per agent is the comparison that matters.** The table uses two
cell sizes, labelled as a mapping choice:

| Cell = | Our free cells | Per agent at N = 5 | Same density in GECCO at N_A ≈ |
|---|---|---|---|
| C55 lane, 0.55 m | 27.2 | 5.4 | **37** |
| Latch, 0.45 m | 40.6 | 8.1 | **25** |
| GECCO, at their N_A = 5 / 10 / 25 | 202.5 | 40.5 / 20.2 / 8.1 | — |

- Matching their N_A = 5 density at 0.55 m cells would take 61.3 m² of free
  floor. The tracked band is 18 m².
- **Our N_A = 5 floor therefore sits at or beyond their N_A = 25 rung.** At
  that rung 91/100 baseline and 76/100 CA runs failed (Table 2).
- This is the registered framing: S1 matches their N_A, N_G, N_T and run
  protocol, never their density.

### Layout

The map is B1's `warehouse_map_bottleneck_merge`, with the A55-E gate
(C55 0.55 × 1.0 at x ∈ [0.7, 1.7]). It gives one capacity-one bottleneck
into the east bay.

```text
                      N (0, 1.55)  yaw -pi/2
                          |
  rack NW                 | N-S arm (|x| <= 0.6)          rack NE
  ------------------------+----------------------------------------- y = 0.6
  Wp (-2.3, +0.35) yaw 0  lane y=+0.35 -->                [A55-E gate]   E (2.3, 0)
                          (junction box |x|,|y| <= 0.6)   [0.7 .. 1.7]   yaw pi
  Wm (-2.3, -0.35) yaw 0  lane y=-0.35 -->                [==0.55 m==]
  ------------------------+----------------------------------------- y = -0.6
  rack SW                 |                               rack SE
                          S (0, -1.55)  yaw +pi/2
```

| Node | Pose (x, y, yaw) | Why there |
|---|---|---|
| Wp | (−2.3, +0.35, 0) | West tip on R-LANE's +0.35 lane, 0.20 m inside the x band |
| Wm | (−2.3, −0.35, 0) | Mirror lane. Two lane nodes give N_G = 5. **0.70 m** apart (≥ 0.6, but 0.532 under 2 × the 0.084 M1 maximum; see Open Questions). |
| N | (0, +1.55, −π/2) | North tip, 0.25 inside the y band; marker 4 at (0, 1.75) is clean, 1.55 is unverified |
| S | (0, −1.55, +π/2) | South tip |
| E | (2.3, 0, π) | East bay beyond the gate mouth (1.7), 0.2 inside the band. B1's barrier projection covers x ≤ 2.26 only, off the marker line at y = 0. |

**Nominal routes.**

- Each route runs node → arm mouth → (0, 0) → arm mouth → node. The arm
  mouths are (−0.6, ±0.35), (0, ±0.6) and (0.6, 0).
- The leg lengths are 3.10 m (N↔S), 3.85 (N/S↔E), 3.94 (W*↔N/S) and 4.69
  (W*↔E). The mean is 3.67 m.
- A Wp↔Wm leg (0.70 m) is **forbidden by the generator**. It produced
  instant static encounters, because a robot crosses the 0.45 m latch radius
  of a node's occupant after 0.25 m of travel.

**Spawns.**

- Each robot starts on a distinct node. The seeded assignment is part of the
  family axis.
- Releases are staggered by **Δ = 4 sim-s**, in robot-id order. That is the
  registered arrival process.
  - **Why 4.** With N_A = N_G every node is occupied at t = 0, so a robot's
    first target always holds an unreleased robot. Every occupant must
    leave before the earliest first arrival:
    4Δ < (L_min − 0.45) / v = (3.10 − 0.45) / 0.15 = 17.7 s, so Δ < 4.42.
  - **Δ = 0** sends every robot to the junction together. The first
    encounter is then a 5-way junction head-on at 8.8 s in 400/400 episodes:
    an IB10-plus-one jam, not emergent congestion.
  - **Δ ≥ 4.42** makes the first robot drive into a node whose occupant is
    still held. At Δ = 20, all 321 static first encounters were this
    artifact; at Δ = 6 and 8 it is 42/400 and 131/400.
  - `start_delay_sec` is a wall clock, so the yaml value is 4 / RTF_pilot,
    re-derived after the pilot (the C9 pattern). RTF jitter moves Δ, and
    the window is narrow (Δ ∈ (0, 4.42) sim-s). Open Question S1-10.

**Task sequences.**

- Five destination nodes per robot, each ≠ the robot's current node, never a
  Wp↔Wm pair. Uniform over the rest, from the episode seed.
- Labels alternate `pickup` and `delivery`, starting with `pickup`. That
  follows GECCO's mode alternation.
- The labels render through the task channel, as B2 established. Their
  wording is an open question.

### Density and feasibility (before any oracle)

**Static pairwise floors.**

| Pair | Floor (m) | vs 0.45 latch / 0.6 STALE |
|---|---|---|
| Wp–Wm (two dwelling robots) | 0.70 | PASS / PASS, with 0.10 m of margin and 0.532 worst-case under M1 error |
| Any other node pair | ≥ 2.50 | PASS |
| Lane routes y = ±0.35 (two robots on opposite W lanes) | 0.70 | PASS |
| Any two routes inside the junction box | 0 (they cross) | Crossing hotspot by construction |
| Two robots on one arm segment | 0 | Head-on (opposite directions) or follower (same direction) |
| A robot dwelling at a node vs a robot arriving at that node | 0 | **Node handoff**: the dominant conflict |
| **Off-route parking anywhere in the band** | No point of free floor is ≥ 0.45 m from every lane or node | **Zero capacity** |

Why there is no parking: a 1.2 m aisle with two lanes at ±0.35 leaves no
point ≥ 0.45 m from both lanes. Every free point is in a lane, in the
junction or on a node.

**Dispatcher variants, all at N_A = 5, N_T = 5, dwell 5 s, Δ = 4.** Kinematic
proxy, 400 seeds (A: 300); free-flow and Layer-2-off columns.

| Variant | Free-flow completes | Free-flow makespan (sim-s) | Layer-2-off proxy |
|---|---|---|---|
| A. Node-occupancy hold, no wandering | 0 of 300 seeds; gridlocks at t = 0 by construction (all 5 nodes occupied, every target busy) | — | — |
| B. Hold with the wandering analog (finished robots go to free nodes) | Gridlocked in 400/400 at N = 5 (Δ = 20). It still gridlocks in 330/400 at N = 3, through swap cycles (A waits for B's node while B waits for A's). | — | Gridlock is invisible to the detector: held robots give no stall evidence |
| C. No hold, no wandering | 400/400 | median 236 at Δ = 20 | Finished robots never leave their last node: 6.62 arrivals per episode land on an occupied node, against 4.44 under D (both at Δ = 20) |
| **D. No hold, wandering analog (recommended)** | **400/400** | **median 177 (p10 171, p90 185); 3.5 wander legs per episode** | ≥ 1 encounter in 400/400; first encounter median 15.0 sim-s (p90 17.3); 3.85 encounters per episode; **completes 0/400** |

Row D, first-encounter hotspots (400 seeds):

| Region | First encounters | Kind |
|---|---|---|
| Junction box | 309 | crossing (different arms) and head-on |
| W arm (lanes) | 39 | lane head-on |
| S arm | 15 | head-on |
| N arm | 14 | head-on |
| E mouth | 13 | head-on |
| E gate / bay | 10 | gate head-on |
| **Kind totals** | crossing 279, head-on 121, static 0, same-direction 0 | |

**After the first conflict (the Layer-2-off world).** 2.85 further encounters
per episode follow. 994 of the 1,538 encounters over all episodes are robots
running into a robot already frozen in a conflict, 1,392 of them at the
junction. That is queue spillback into the first jam, which Layer 2 must
pre-empt.

**Verdict.**

- Under D, S1 is conflict-rich but never self-completing. With no Layer 2,
  0/400 episodes complete.
- Whether it is resolvable depends on two missing groundings:
  - **M3's junction `arms` are static per robot** (`SceneGeometry.arms`). A
    MAPD robot changes arm on every leg, and 77% of first conflicts are
    junction conflicts between robots on different arms.
  - **Every junction yield retreats outward** along the yielder's own arm.
    A tip handoff, where a robot arrives at a node another robot is
    dwelling on, needs the opposite: the arriving robot steps aside
    laterally, or backs inward toward the junction, while the dweller
    leaves past it. With Layer 2 on, handoffs follow the first conflicts:
    the free-flow census shows 3.2 arrivals per episode onto an occupied
    node.
- The head-on at the A55-E gate is resolvable only one way, and the oracle
  is feasibility-determined like B1's:
  - The bay robot must pass. Its escort ends westward, inside the band.
  - The outside robot must yield. An eastbound escort would end at 2.974,
    outside the band (unified design, A55-E).

**Registration prerequisites (all three are needed before S1 is registered
as scored):**

1. **M5 MAPD registry contract** (v3 Step 3, already named):
   - task queues;
   - the wandering-analog dispatch (least-loaded node);
   - its interaction with overrides, plan `continue` legs, the arrival gate
     and the race guard.
2. **M3 dynamic arms plus a node-handoff grounding.**
   - Arms are derived per snapshot from position and heading.
   - A lateral or inward yield for a robot arriving at an occupied dead-end
     node, with the dweller as the exempt passer.
   - This is new contract work. Without it, the 77% of first conflicts
     that are cross-arm junction conflicts have no correct grounding: a
     robot with no declared arm is grounded along the single declared
     corridor axis. Handoffs have no grounding at all.
3. **The launcher's 5-stack bring-up and the RTF measured** (pilot).

### Dwell-versus-stall specification

- **What the detector does today** (`congestion_detector.py`): a robot whose
  registry goal equals its current node is excused from stall evidence.
  - The excusal comes from either `goal_reached_tolerance_m` 0.15, or the
    arrival mark plus `arrived_radius_m` 0.5.
  - **So a dwell is natively excused if and only if the registry goal stays
    the dwell node until the dwell ends.**
- **Registered rule:** pop-on-dwell-end, not pop-on-arrival.
  - The dwell timer runs in sim-s: d = **5.0 sim-s**, registered.
  - That is 13–25 wall-s at RTF 0.2–0.38. Without the rule it would exceed
    the 12 wall-s trigger.
- **Not excused, by design:** the close/slow pair rule (two slow robots
  within 0.5 m for ≥ 12 wall-s) fires whatever the goals are. A dweller with
  a latched arriver beside it *is* a node-handoff conflict. That is the
  conflict, not a false positive.
- **The schema has no MAPD shape.**
  - `expected_conflict` is a single required block, with non-empty
    `involved_robots` and one onset window. The `ScenarioFamily` literal has
    no MAPD member.
  - S1 needs a family `mapd` and an "emergent" conflict declaration: no
    pre-declared involved set; the conflict episodes are found by a GT
    detector.
  - These are schema items, listed in Build Fit.

### Oracle sketch

- **No `accepted_strategies` per episode.** Rule it explicitly at the freeze,
  as v3 Step 6 asks.
- Scoring per conflict episode: detection (GT encounter → trigger latency),
  type label, involved-set F1, and plan-quality metrics (i-a)–(vi) as in v2.
- Scoring per run: completeness (all 25 tasks done by H), makespan,
  throughput curve, and per-segment `delay_vs_free_flow`.
- **Arms:** Layer 2 on, against Layer-2-off, re-run on the merged tree per
  Step 0.
- A prediction-avoidance arm remains the OPEN design question v3 Step 3
  names. Without it, the claim is limited to detection-resolution on task
  streams.

### Free-flow segments (`free_flow_v2`, keyed by (scene, segment))

There are 18 ordered legs: 5 × 4 minus the 2 forbidden Wp↔Wm legs.

| From \ To | Wp | Wm | N | S | E |
|---|---|---|---|---|---|
| Wp | — | forbidden | 3.94 | 3.94 | 4.69 |
| Wm | forbidden | — | 3.94 | 3.94 | 4.69 |
| N | 3.94 | 3.94 | — | 3.10 | 3.85 |
| S | 3.94 | 3.94 | 3.10 | — | 3.85 |
| E | 4.69 | 4.69 | 3.85 | 3.85 | — |

- Each entry is one solo run on the parent map: the robot at node A with its
  goal at node B. That is 18 × ~5.3 min ≈ 1.6 h of VM time, with zero API
  spend.
- **Mirror legs are not substituted.** The fix moved rotation-heavy routes
  the most (−0.8 s), and M1 cleanliness depends on marker and pose.
- The same generator pass keys each entry by (`mapd_5`, `A→B`). The v3
  "single method" rule holds: solo in space, no other robots and no
  blockers.

### M1 cleanliness

- All five nodes are unverified for every marker. The 25 (marker, node)
  pairs are covered by a **5-run Latin square**: each run holds all five
  robots stationary on a permutation of the nodes for 120 sim-s, the
  y-extent probe pattern. That is ~30 min of VM time.
- Wp–Wm stationary pairs sit at 0.70 m, inside the 0.6 m band only if M1
  errors line up adversarially. The probe records both robots' fresh rates
  together.

### Run cost (registered parameter, not silently smaller)

- **Per episode:** H = 600 sim-s at a 5-stack RTF that has never been
  measured.
  - The 2/3/4-stack trend (0.39 / 0.34 / 0.22) extrapolates to about
    0.15–0.19. **This is extrapolated, not measured.**
  - That gives ≈ 53–67 wall-min plus ~5 min of overhead.
- **R = 20 per arm, 2 arms:** ≈ 40–48 h.
- **GECCO's 100 per arm:** ≈ 200–240 h, unaffordable against the v2
  collection priority rule.
- R is a registered parameter with a 100-seed list. The confirmatory set is
  the first 20 seeds.

---

## S2 — Asymmetric Junction, Axis Choice Scored (v3 Step 2)

### Mechanism choice: a parked follower on an E-W arm

**Noise first.** Settled-jam GT across 14 recorded four-way jams (IB10
smoke, IBA1, IBB4, step-6 ×4, v2 demo ×2, costmap-fix ×2, verbatim pilot ×3).

| Statistic | Value |
|---|---|
| Axis gap χ(E-W recede set) − χ(N-S recede set), pocket 1.2, N_f = 0 | −0.273 … +0.239 (median ≈ +0.03) |
| \|gap\| ≥ 0.15 | 3/14: IBA1 +0.194, costmap-fix prefix r4 +0.239, vp09 −0.273 |
| N-S pair order margin (the quantity ε = 0.15 was sized on) | −0.146 … +0.046, consistent with the plan-grammar table |

The axis gap sums two robots' offsets per axis, so its noise is about twice
the order noise.

**Comparison of the two mechanisms.**

| Criterion | Follower (+0.5 per follower, `recede_follower_count`) | Pocket-distance asymmetry (Δp per axis) |
|---|---|---|
| Noise-free? | Yes. N_f is an integer count. | No. It rides on the same ±0.27 standoff noise. |
| Size needed above noise | One follower gives gap 0.5 + noise ∈ [0.227, 0.739] (14/14 ≥ 0.15) | 2·Δp ≥ 0.15 + 0.273, so Δp ≥ 0.21 m |
| Room | E-W follower at x = ±2.4 (0.65 m behind the 1.75 spawn): in band | N-S pockets are capped by the stagger STALE window (second pocket ≤ 1.05 at goal radius 1.75). Pushing E-W pockets out needs E-W goals moved out too. |
| Visible to the VLM? | Yes: a robot on the arm in the image and the text | No: pockets are declared constants. They are visible only as lettered marks, which the junction has no stage for. |
| Code change | None for χ. A parked-robot exclusion is needed (below). | Per-axis `junction_recede_offset_m` (a single scalar today) |
| A-DRIVE fidelity | It is A-DRIVE's own second term | D_SPACE is the first term, but only meaningful with a visible free pocket |

**Recommendation: the follower.** It is visible, integer-valued, and A-DRIVE's
own term.

**Derived limitation: the follower can only sit on an E-W arm.**

- A N-S follower needs |y| ≥ 1.75 + 0.57 = 2.32. That is outside the 1.80
  band.
- Moving N-S spawns in to 1.2 would leave room (a follower at 1.8). But the
  opposite N-S robot's goal (0, ±1.75) would then sit 0.05 m from the
  follower, and the cross-traffic structure needs that goal.
- So the follower's +0.5 always lands on χ(E-W). The χ-cheaper axis is always
  **N-S recede, the shipped default, M3's `m3_default` plan**.
- Consequences:
  - Axis choice is scored on **emitted plans only**. A token-only
    `junction_clear` executes the default and earns no axis credit.
  - The registered contrast is **S2 against S3**: the shift in the
    proposed-plan P(N-S recede) when a follower sits on an E-W arm.
  - Counterbalancing is by follower side (east `_fe` / west `_fw` members),
    not by axis.

### Geometry

All spawns and goals are IB10's at radius 1.75. The follower is `robot_5`,
parked.

```text
                         robot_4 (0, 1.75)  -> goal (0, -1.75)
                               |
  robot_1 (-1.75, 0) ---->  [junction box]  <---- robot_2 (1.75, 0)   robot_5 (2.40, 0)  [_fe]
  -> goal (1.75, 0)            |                    -> goal (-1.75,0)  parked, goal = spawn
                         robot_3 (0, -1.75) -> goal (0, 1.75)
  [_fw]: robot_5 at (-2.40, 0) instead (robot_1's spawn 0.65 m ahead of it)
```

| Item | `_fe` | `_fw` | Derivation |
|---|---|---|---|
| robot_5 pose | (2.40, 0, π) | (−2.40, 0, 0) | 0.65 m behind the 1.75 spawn (≥ 0.57 R-QUEUE-2; ≥ 0.6 STALE); x = 2.4 is the verified-clean coordinate for markers 1 and 2 |
| robot_5 arm | {axis x, side +1} | {axis x, side −1} | needed for N_f |
| robot_5 task / goal | goal = spawn (arrives at t = 0, excused) | same | |
| N_f | robot_2: 1 | robot_1: 1 | `recede_follower_count` |
| χ(N-S set) at the IB10 standoff | 0.942 + 0.923 = 1.865 | same | `recede_cost` |
| χ(E-W set) at the IB10 standoff | 0.981 + 1.370 = 2.351 | 1.481 + 0.870 = 2.351 | `recede_cost` |
| Axis gap | **+0.486** | **+0.486** | > ε = 0.15 |
| Gap over the 14 recorded jams | 0.227 … 0.739 | same | 0.5 + the noise above. Assumes a fifth (parked) robot or fifth stack does not change how the jam forms; untested. |

**Both axes' composites**, from `ground_junction_clear_phases` at the IB10
standoff with robot_5 (`_fe`) present. Offset 1.2, stagger 0.2, J2 1.1,
derived mode.

| Phase | Shipped: N-S recede, E-W yield (`corridor.axis: x`) | Mirrored: E-W recede, N-S yield (`corridor.axis: y`) |
|---|---|---|
| Recede 1 (lead) | robot_4 reverse 0.923 → y = +1.200 | robot_1 reverse 0.981 → x = −1.200 |
| Recede 2 (stagger) | robot_3 reverse 0.742 → y = −1.000 | robot_2 reverse 0.670 → x = +1.000 (N_f = 1 ranks it second) |
| Cross: yield | robot_1 backs 0.799 to park (−1.018, 0.359) | robot_3 backs 0.760 to park (0.339, −1.018) |
| Cross: passer escort | robot_2 1.998 → end x = −1.668 | robot_4 1.946 → end y = 0.2773 − 1.946 = **−1.669** |
| Release | robot_3 lead-gated yield; robot_1 chained behind [robot_4, robot_3] | robot_2 lead-gated yield; robot_3 chained behind [robot_1, robot_2] |

**Constraint checks.**

| Check | Value | Verdict |
|---|---|---|
| Mirrored N-S passer end vs the 1.80 band | \|y\| 1.669; the study row "2, N-S, J2" gives 1.668 / +0.132 | **+0.131 m; +0.031 m with the full 0.10 M1 budget.** The measured errors are smaller: M4 retreat 0.027–0.041, M1 median ≤ 0.011. Abort criterion: GT \|y\| > 1.80. |
| Passer end vs parked yielder (mirrored) | (0.0045, −1.669) to (0.339, −1.018): 0.732 | ≥ 0.6 PASS |
| E-W pockets in the x band | 1.200 / 1.000, well inside 2.5 | PASS. **But `tracked_extent_m` is one scalar (1.75)**, which is wrong for E-W arms (2.5). A per-axis extent is a build item. |
| Lead's endgame vs second pocket (mirrored) | The lead parks ~0.10 m short of its 1.75 goal, at ~1.65; that is 0.65–0.69 m from the 1.0 pocket | ≥ 0.6 PASS (the step-7b window p ≤ 1.05 holds by symmetry) |
| Lead's endgame vs follower | robot_1 at 1.65–1.69 against robot_5 at 2.40: 0.71–0.75 | PASS |
| Shipped passer end vs follower (`_fw`, passer westbound) | −1.668 vs −2.40: 0.732 | PASS |
| robot_2's goal vs west follower (`_fw`) | parks at −1.65 … −1.69: 0.71–0.75 | PASS |
| Spawn: robot_1 (−1.75) vs follower (−2.40) in `_fw` | 0.65; marker 1's STALE pose is robot_1's own spawn | 0.05 m over the band before M1 error. **Apply the 1.65 re-radius to `_fw`** (gap 0.75), or run `_fe` only. Owner call. |
| Arm B | Follower at 2.4: farther than 1.5 m from every jam member, so no crowding | PASS (unchanged from IB10) |

**χ with the follower listed as involved: breaks today.** The run used
`involved_robots` = all five.

- **Mirrored:** robot_5 becomes the χ-cheapest receder (D_SPACE floored to
  0, so χ = 0).
  - The recede set grows to three, and robot_2's pocket moves to 0.8.
  - The release phase is "scoped to exactly ONE release stage" in the
    `JunctionClearPhasePlan` docstring, so three candidates need the unbuilt
    N-way chain.
- **Shipped:** robot_5 is appended to the E-W crossing order as a second
  passer, which escorts a parked robot.
- **Build item:** exclude goal-arrived (parked) robots from recede
  candidates and crossing orders. Listing robot_5 is then scored as an
  involved-set error.

**STALE checks: new stationary poses, all unverified.**

| Marker | Pose | Role |
|---|---|---|
| 5 | (±2.40, 0) | follower, all episode |
| 1 | (−1.2, 0), (−1.0, 0), (−1.0, ±0.36) | mirrored pockets and the release pull-off |
| 2 | (1.2, 0), (1.0, 0), (1.0, ±0.36) | same |
| 3 | (0.339, −1.018) / mirror | N-S yield park |
| 4 | (0, ±1.669) | passer escort end (transient) |

- These need **two stationary probe runs** (four robots × 120 s each), or
  the instrumentation flag in scored runs.
- Marker 5 has never been rendered in any run.

### Oracle sketch

- `correct_axis: N-S`, i.e. recede set {robot_3, robot_4}.
- `axis_gap_at_dispatch` is computed from the dispatched snapshot.
- `equivalent` iff |gap| < ε_axis. In that case the episode is scored as
  S3-like and reported, never dropped.
- Inside-first and yielder-last are as in IB10's 11 criteria.

**ε_axis choice: owner ruling.**

| Choice | Effect |
|---|---|
| Keep 0.15 | S2's floor of 0.227 clears it in 14/14 |
| Re-measure to absorb all 14 symmetric jams (≥ 0.28) | 1/14 S2-equivalent episodes (vp09-like) fall inside it |

Either is registrable. The rule must be fixed before collection.

### Free-flow

- The IB10 four arm entries (`intersection_bottleneck` robot_1–robot_4) are
  re-harvested in `free_flow_v2`.
- **The follower stays in each solo variant as course geometry.** It is the
  `blocker_west` precedent: lidar-visible and 0.65 m from the robot_1/robot_2
  goal approaches. Stripping it could change the very legs it flanks.
- That makes 4 new entries per member, keyed `(s2_fe | s2_fw, robot_k)`.
  The parked robot has no entry.

---

## S3 — Symmetric Both-Axes Junction (ε-Equivalence Cell)

**Geometry.**

- IB10 exactly: four robots, radius 1.75, no follower, the same goal-table
  row as IB10.
- Plus the both-axes modeling: the mirrored composite above becomes a
  grounding M3 accepts.

**Derived χ.**

| Source | Value |
|---|---|
| IB10 smoke standoff | χ(N-S) 1.865, χ(E-W) 1.851, gap −0.014 |
| 14 jams | gap −0.273 … +0.239; **11/14 within ε = 0.15** |

**What it measures.**

- The choice distribution over {N-S, E-W, all-four, other} under
  `prompt_robot_order: random`, conditioned on the draw. This is v2-ruled.
- Restricted to episodes whose dispatched-snapshot gap is < ε_axis.
- The equivalence class is the axis set. Both axes are `vlm_verbatim` when
  they verify.
- The repair tie-break ("toward M3's derived plan") becomes: the derived plan
  is the χ-cheaper axis; within ε, the proposed axis stands. That is v3
  Step 2's re-specification.

**v3 IB10 provenance is not comparable with v2 IB10 repaired rates.** v2
scored the mirror as `repaired` by convention.

**Episodes outside ε are not dropped.**

- An "asymmetric by formation" episode, |gap| ≥ ε, is scored on the χ-cheaper
  axis like S2, and reported separately.
- At the observed 3/14, about 20% of S3 episodes are expected there.

**Constraint checks.**

- Same as the S2 table without the follower rows.
- The N-S passer end is +0.131 / +0.031 as above.
- STALE: the marker-1 and marker-2 E-W pocket poses listed for S2.

**Free-flow.** The four IB10 entries, already keyed
`intersection_bottleneck`, are re-harvested in Step 0. S3 needs no new entry.

---

## S4 — Persistence-Judgment Classification Cell (Step 1 NO-GO fallback; log-only)

**Why a held tableau.**

- On the loop map, a planner-visible blocker makes NavFn self-detour:
  - 3/3 runs on the v2 tree;
  - the flip point is fix-invariant (v3 Step 1).
- A driven robot therefore never stalls at the blocker, so there is nothing
  to classify.
- The robot is instead **held** (`start_delay_sec` longer than the horizon,
  the y-extent probe pattern). M5's T0 probe mode captures the frames: probes
  are log-only and never grounded or dispatched. **No detour executes.**
- **No triggered analysis competes with the probes.** A held robot has no
  progress goal (`_progress_goal` returns None while `start_pending`), so it
  gives no stall evidence. In the two-robot variant the robots are 0.65 m
  apart, above the 0.5 m close/slow threshold.
- **What the VLM sees.** The prompt renders a held robot with its mission
  goal and task through `_effective_goal` (status STOPPED). The held status
  itself is not rendered: `SnapshotFrame.held_robot_ids` is read only by
  Arm B. So the tableau reads as a stopped robot whose goal lies past the
  blocker, which is the intended construct. Whether the VLM reads "stopped
  before a box" as "blocked" without any stall history is untested (Open
  Question S4-3).

**Layout.** It reuses `loop_detour_{permanent,transient}` unchanged: loop map,
pinch barrier 0.50 × 0.55 at x = 0.975, blocker at (1.0, −0.11) or
(1.0, −0.095).

| Variant | Robots | Notes |
|---|---|---|
| `persist_1r_{perm,trans}` | robot_1 held at (−0.5, 0, 0), goal (2.3, 0) | 1.375 m short of the blocker's west face (0.875), inside T3a's 0.9–1.5 stall range. Marker 1 at (−0.5, 0) is unverified; the fallback is (−2.4, 0), clean but 3.3 m short. |
| `persist_2r_{perm,trans}` | plus robot_2 held at (−1.15, 0, 0), goal (2.3, −0.3) | Queued behind at 0.65 m (≥ 0.57; ≥ 0.6 STALE). The persistence call now gates two robots' plans. |

- Members differ only in `name`, the blocker entity and the oracle block. The
  prompt text is byte-identical, pinned like T3a and the loop pair.
- The permanent member uses a `static_box` 0.25 × 0.28 × 0.35. The transient
  uses `robot_visual_no_marker` at scale 1.82, removed at the registered
  `remove_at_sec`.

**Frame-capture instants.**

- `t0_probe_interval_sec` is 20 wall-s, from M5 start (~12 sim-s). The
  probe period in sim time is therefore 20·RTF.

| remove_at_sec | RTF 0.30 | RTF 0.38 | RTF 0.42 |
|---|---|---|---|
| 45 (loop placeholder) | 5 probes | 4 | 3 |
| 70 (T3a value) | 9 | 7 | 6 |

- **Recommendation: register 70 s** (≥ 6 pre-removal probes at any plausible
  one- or two-stack RTF).
- Scoring:
  - All pre-removal probes are scored as repeated measures, clustered by
    episode.
  - The first post-removal probe is a **manipulation check**: in the
    transient member it should read "clear", and in the permanent member it
    should not change.
  - The probe count before removal is recorded per run.

**What the oracle labels.**

- **Primary:** `persistence ∈ {permanent, transient}`, read from the
  decision's `blocker_kind`. `object` → permanent; `transient` → transient;
  `robot` → an error, because the blocker is unlisted (amendments item 15b).
- **Secondary, computed and never executed:** the expected-cost strategy per
  probe.
  - `temporary_wait` iff (remove_at − t_probe) < C_detour.
  - C_detour is the free-flow detour time via `reroute_waypoints`
    [(0.3, 1.2), (1.8, 1.2)]. It needs one solo free-flow run of the detour
    on the fixed stack, because no measured value exists.
  - Nominal path: 4.24 m against 2.80 m direct, from (−0.5, 0).
- **Arm B:** its held-robot exclusion (amendments item 28) removes a held
  robot from the `blocked_path` candidates, so Arm B answers `none`
  ("stopped robots are all ... held back") in both members. That differs
  from T3a and the loop family, where Arm B said blocked_path → reroute.
  The Arm B comparator is therefore degenerate in S4; report it as
  structural. Arm B reads no image in any case, so its persistence
  accuracy is undefined.

**What is new compared with T3a.** T3a already scores `blocker_kind`.

| Difference | What it adds |
|---|---|
| A **real alternative path** is in the image (loop), so the call is consequential, not just a label | The decision matters |
| A **registered clear time**, which turns the label into a per-probe expected-cost strategy oracle | A second scored quantity |
| **Held robots and probe instants**, which remove Nav2 from the measurement entirely | T3a depended on a NavFn failure to stall |
| A two-robot variant | Tests whether the call holds when two robots' plans hang on it |
| Persistence wording | An analysis relabel only, not a schema change |

**Density.** One or two robots, all stationary. Pairwise 0.65 m. Trivially
feasible.

**Free-flow.** None for the classification score. One detour solo run is
needed for C_detour.

---

## S5 — Scale Probe at N = 8 (Step 5 pilot)

**Citable base.**

- **Common-target congestion lineage:**
  - Marcolino & Chaimowicz, IROS 2009, "Traffic Control for a Swarm of
    Robots: Avoiding Target Congestion". Venue partially verified.
  - dos Passos, Duquesne & Marcolino, arXiv:2201.09335 (2022) and RAS 159
    (2023). Verified.
  - Soriano Marcolino et al. 2017 (ORCA equilibrium at a common target).
    Venue unverified; a DBLP check is owed.
- **Garg et al. / MIT-REALM** (arXiv:2404.06413; PMLR 2026 VLM-GCBF+):
  room-environment convergence with 5–50 robots, where "A* beats VLMs on
  small rooms".
  - The notes do not record their room geometry or the N used at small
    scale. **Cite qualitatively; the geometry is unverified.**
- The adaptation: radial four-arm convergence onto a shared region (the
  junction box) inside our tracked band.

**Geometry.** Four moving leads form an IB10-class jam. Held followers queue
behind them, one per arm. The followers are held, stationary, all episode.

```text
# S5 scale_probe_n8: radial common-target convergence. Lineages: Marcolino &
# Chaimowicz IROS'09 / dos Passos et al. arXiv:2201.09335 (common target area);
# Garg et al. arXiv:2404.06413 + PMLR'26 VLM-GCBF+ (room-environment convergence).
                    F4 (0, 1.80)   held
                    L4 (0, 1.15)   -> (0, -1.15)
  F1 (-1.80,0)  L1 (-1.15,0) -> [box] <- L2 (1.15,0)  F2 (1.80,0)     [N=10: + F5 (-2.45,0), F6 (2.45,0)]
                    L3 (0,-1.15)   -> (0, 1.15)
                    F3 (0,-1.80)   held
```

**Derived constraints.**

- **Lead radius.** The N-S follower needs |y| = r_L + 0.65 ≤ 1.80, so
  r_L ≤ 1.15. r_L = 1.2 puts the follower at 1.85, outside the band.
- **Equal radii.** All leads sit at 1.15 so the jam forms together (the IB10
  invariant).
- **Run length.** R-RUN holds: 0.55 m of run before the box mouth at 0.6.
- **Pairwise floors** (straight inward approach to the jam pose ±0.25;
  followers stationary):
  - spawn-time minimum 0.650 m;
  - **minimum non-jam pair over the whole approach 0.650 m**, for both
    N = 8 and N = 10;
  - only lead–lead pairs close, which is the jam itself.
- **N = 10.** E-W arms take a second follower at ±2.45 (0.65 behind ±1.80,
  0.05 inside the band). That fits v3 Step 5's "N = 8–10", but see Open
  Question S1-9.
- **Lead goals** are the opposite lead's spawn (r = 1.15), because the arm
  tips hold followers. A goal at 1.15 is 0.65 from the follower at 1.80.
- **Arm B.** The leads sit inside the 1.5 m FCFS zone from the first frame,
  so every arrival is censored. The followers at 1.80 are outside r_conflict
  1.5. Arm B is shadow-only and its censoring is reported as structural.

**Scoring (classification and triage only).**

- `congestion_detected`, the type label, and involved-set precision and
  recall against the core set {L1–L4}.
- Follower inclusion is reported, not scored.
- The proposed recede set or axis and the plan legs are log-only.
- Frames come from the first triggered analysis plus T0 probes.
  **Dispatch is not suppressed today.** Probe mode does not gate the
  triggered path, and M5 has no dispatch-off flag (see S6). Either score
  the first decision and leave execution unscored, or build the flag
  (Build Fit item 9).

**What cannot be scored at N = 8, and why.**

1. **Goals versus composite geometry.**
   - The J2 passer escort ends at |y| = 1.668. That is 0.13 m from the
     N-S follower at 1.80, under the 0.45 m latch.
   - The lead pocket at 1.2 is 0.60 m from that follower: the edge of the
     STALE band.
   - So the composite collides with the queue.
2. **Followers cannot be released.** Every arm tip is occupied, so a released
   follower has no goal that does not cross a held queue.
3. **The release chain.** The composite's release phase supports one stage.
   Receding more than two robots needs the unbuilt N-way chain.
4. **The oracle schema.** `JunctionOracleConfig.recede_pair` is a fixed pair
   of two. Success is defined as all robots arriving, which is undefined for
   held robots.
5. **Stacks.** Eight stacks have never been brought up, against a four-stack
   load of ~15 and RTF 0.22. Bring-up failure is likely without a
   **stackless-held launcher option**. Held robots need no Nav2, but
   `fc_launch.sh` launches one stack per scenario robot.
6. **M1.** The (marker, pose) cleanliness of markers 5–8 (and 9–10) at the
   follower poses is unverified. A 2-run probe would cover it.

**Free-flow.** None (no delay metric).

---

## S6 — Explicit Dual Conflict: Analysis First, Then Verdict

**Does S1 guarantee simultaneous conflicts?** From the S1 proxy, row D. The
last column excludes encounters with a robot that has not yet been released,
which are an arrival-process artifact (S1, Spawns).

| Arrival process | Disjoint second conflict ≤ 60 s after the first (no shared robot, midpoints > 1.5 m apart) | Excluding unreleased-robot encounters |
|---|---|---|
| **Δ = 4 sim-s (registered)** | **34/400 (8.5%)**; the same 34 at ≤ 120 s | 34/400 |
| Δ = 6 | 125/400 | 63/400 |
| Δ = 8 | 187/400 | 43/400 |
| Δ = 20 | 268/400 | 21/400 |
| Δ = 0 | 0/400 (the 5-way junction head-on absorbs every robot) | 0/400 |

At Δ = 4 the region pairs (first, second) are: junction+W 10, W+junction 7,
junction+E bay 7, W+E bay 3, E bay+junction 3, and four singletons.

**Verdict: S6 is NOT subsumed by S1.** Three reasons:

1. **The rate is low.** At the registered arrival process, 8.5% of episodes
   carry a disjoint second conflict within 60 s. The higher rates at larger
   staggers come almost entirely from robots driving into unreleased robots.
   The Layer-2-off freeze proxy also over-counts relative to a world in
   which Layer 2 is resolving the first conflict.
2. **The rate is uncontrolled.** It depends on seed and timing, and nothing
   registered controls it. Half of the dual episodes pair the junction with
   an arm, and those junction conflicts need the dynamic-arms grounding
   (S1, prerequisite 2).
3. **A scored claim needs a fixed pair.** A scored dual-conflict claim needs
   a fixed, reproducible pair of conflicts.

**Loop-map design, derived.**

Conflict B as a head-on in the second aisle (y = 1.2, x ∈ [0.6, 2.2],
width 0.55, treated as a corridor centred at 1.4, L = 1.6), from
`park_offset_m` and `passer_clearance_m`:

| Second-aisle occluder | Park offset | West park x | East park x (aisle ends at 2.2) | Westbound passer escort end (strip wall −0.6; centre limit −0.51) |
|---|---|---|---|---|
| 0.9 m (rack, as built) | 1.523 | −0.123 | 2.923, infeasible | **−0.773, in the NW rack** |
| 0.3 m (lowered remnant) | 1.287 | 0.113 | 2.687, infeasible | −0.537, in the rack by 0.027 |
| 0.0 (hypothetical) | 1.204 | 0.196 | 2.604, infeasible | −0.454 (0.056 m margin) |

- Derived mode is worse: park ≤ passer − 1.7 ≈ −0.18, escort end ≤ −0.83.
- The pull-off lateral in a 0.55 m aisle is 0.035 m, which is no sidestep.
- **A second-aisle head-on is not resolvable** with axis-aligned escorts.
  Conflict A also cannot be moved off x = 0 (the |c| ≤ 0.27 window).
- **Specified instead: S6 as a decision-scored dual-conflict cell.** It
  scores plan and classification only; executed outcomes are not scored.

**S6 layout.** The loop map plus the T1 C55 0.55 × 2.0 at x = 0 (the
`head_on_deadlock` barrier). That barrier seals the N-S strip from the primary
aisle, so the map has no cycle and NavFn has no self-detour.

| Robot | Spawn | Goal | Conflict |
|---|---|---|---|
| robot_1 | (−1.5, 0, 0) | (2.5, 0) | A: T1 head-on at x ≈ 0 |
| robot_2 | (1.5, 0, π) | (−2.5, 0) | A |
| robot_3 | (0.2, 1.2, 0) | (2.05, 1.2) | B: second-aisle head-on |
| robot_4 | (2.10, 1.2, π) | (0.0, 1.2) | B |

**Checks.**

- **Spawns.**
  - robot_3 sits 0.4 inside the strip–aisle mouth (x 0.6). robot_4 sits at
    the aisle's east end, near the connector top.
  - The spawn gap in B is 1.90 m. The minimum spawn gap across the two
    conflicts is 1.34 m (robot_4 to robot_2).
  - Marker 4 is clean at (0, 1.2) and marker 3 at (0, −1.2); the S6 poses
    (0.2, 1.2) and (2.10, 1.2) are unverified for both.
- **Separation of the conflicts.** B's standoff forms near
  x ≈ (0.2 + 2.1)/2 = 1.15, y = 1.2. A's is at (0, 0). The midpoints are
  1.66 m apart, beyond Arm B's r_conflict of 1.5. Both conflicts are scored
  as separate events.
- **Formation timing.** B closes 1.9 m at 0.3 m/s combined, so it stops about
  5.3 sim-s after departure. A forms at 19–22 sim-s in T1, i.e. ~8–10 sim-s
  after a departure at ~10.6–12 sim-s. A start delay of ≈ 3–5 sim-s on
  robot_3 and robot_4 (in wall-s via 1/RTF, re-derived after the pilot)
  brings both standoffs inside one ~2 s window.
- **Robots and stacks.** Four stacks: IB10's RTF 0.21–0.24.
- **Visibility.** The loop-map coverage probe showed 100% fresh tracking on
  the second aisle. The T1 barrier's camera projection (factor
  2.79 / 2.1 = 1.33, so x ∈ [−1.33, 1.33], |y| ≤ 0.80) does not reach
  y = 1.2.

**Scored (decision level only).**

- Whether the first triggered decision names both conflicts: two involved
  sets, {1, 2} and {3, 4}.
- The type for each.
- Whether the proposed plan carries legs for both.
- Detection latency for each.

**Execution is NOT suppressed.** `t0_probe_mode` only adds log-only probes:
the `ProbeLedger` refuses probe request ids at the dispatch boundary, and
nothing gates the triggered path (`orchestrator_node.py`, `probe.py` at
b5cafe4). Both jams will trip the stall and close/slow triggers, and those
decisions are grounded and dispatched. M5 has no dispatch-off or shadow flag.
Two options, owner call:

- (a) score the first triggered decision only and let execution run
  unscored. The B conflict's dispatch is ungroundable (table above), so
  its outcome is expected to be a latch or a wait.
- (b) build a dispatch-off flag (Build Fit item 9). S5 needs the same.

**Free-flow.** None (no delay metric).

---

## Migration and Compatibility

| Scene | Map | Props / obstacles | Junction `arms` / geometry row | Free-flow entries | Schema / code it needs that does not exist |
|---|---|---|---|---|---|
| S1 MAPD-5 | `warehouse_map_bottleneck_merge` (B1, A55-E), reused byte-for-byte | none (nodes are poses, not props; there is no non-blocking floor-marker prop) | none static; **dynamic arms** needed | 18 new `(mapd_5, A→B)` | Family `mapd`; emergent `expected_conflict`; M5 task queues, pop-on-dwell-end and wandering dispatch; M3 dynamic arms and node-handoff grounding; 5-stack launcher |
| S2 `_fe` / `_fw` | default plus-floor map (= IB10's) | none (the follower is a robot) | IB10 row + robot_5 arm + mirrored-axis support | IB10's 4 entries (re-harvested), plus 4 per member with the follower as course geometry | Axis-set χ comparison and the `correct_axis` oracle field; per-axis `tracked_extent_m`; mirrored-axis grounding selection (today the axis is structural); parked-robot exclusion; marker-5 asset run; 5 stacks or a stackless-held option |
| S3 | IB10 map | none | IB10 row + mirrored-axis support | IB10's 4 (Step 0 re-harvest) | Same as S2, minus the follower items |
| S4 | `warehouse_map_loop_detour_*` (both identical), reused | `static_box` / `robot_visual_no_marker` timed obstacles, as in the loop pair | `reroute_waypoints` (for C_detour only) | 1 detour solo run (C_detour) | Persistence relabel in the scorer; held-robot probe driver (the y-extent pattern exists) |
| S5 | IB10 map | none | none (no resolution) | none | Stackless-held launcher option; markers 5–8/10 probes; involved-core scorer |
| S6 | New: loop map + T1 barrier at x = 0 (generator supports both keys; a new per-scenario map) | none | none | none | Multi-event scorer (two involved sets per decision) |

**What changes for existing scenes: nothing.** No v1 or v2 yaml, map, pin or
free-flow entry changes. New fields must default to byte-identical behaviour,
the discipline every prior field followed.

---

## Build Fit and Order

| # | Item | Scenes | Size |
|---|---|---|---|
| 1 | Clean-pose probes: S1 Latin square (5 runs); S2/S3 pockets (2 runs); S5 followers (2 runs); S4 and S6 poses (1 run) | all | ~10 runs × ~5 min |
| 2 | Launcher: stackless-held robots; measure the 5-stack RTF | S2, S5 (stackless); S1 (5 stacks) | S + 1–2 runs |
| 3 | Parked-robot exclusion in junction grounding | S2 | S |
| 4 | Mirrored-axis grounding selection, axis-set χ, per-axis extent, oracle `correct_axis` / `axis_gap_at_dispatch` | S2, S3 | M |
| 5 | ε_axis ruling (owner) | S2, S3 | — |
| 6 | Persistence probe cell: driver, scorer, C_detour solo run | S4 | S + 1 run |
| 7 | Multi-event scorer, map | S6 | S |
| 8 | MAPD: schema, M5 registry, M3 dynamic arms and handoff grounding | S1 | **L** (v3 Step 3) |
| 9 | M5 dispatch-off (shadow) flag: triggered analyses are recorded but never grounded or dispatched (does not exist; `t0_probe_mode` does not provide it) | S5, S6 (optional) | S |

S1 slips first. It carries the largest contract work and the only L item.

---

## Risks and Mitigations

| Risk | Where | Mitigation |
|---|---|---|
| Node-handoff conflicts ungroundable | S1 | Prerequisite 2; do not register S1 before it |
| 5- and 8-stack RTF and bring-up | S1, S2, S5 | Stackless-held option; RTF recorded per run |
| N-S passer end margin +0.031 with full M1 budget | S2, S3 (mirrored axis) | Measured errors are smaller; abort at GT \|y\| > 1.80; pinned |
| Axis noise exceeds ε in ~20% of symmetric jams | S3 | Per-episode equivalence at the dispatched snapshot; report both strata |
| Follower listed as involved | S2 | Parked-robot exclusion; scored as an involved-set error |
| Marker 1 spawn STALE adjacent to the west follower (0.65 m) | S2 `_fw` | 1.65 re-radius, or `_fe` only |
| Proxy over- or under-states S1 rates (no Nav2, freeze model) | S1, S6 | Pilot n = 3 with GT encounter logging before registering the rates |
| Arrival-process artifact (robots driving into unreleased robots) | S1, S6 | Δ = 4 inside the derived window (0, 4.42); a pilot records each robot's release sim-time |
| Triggered analyses dispatch in "classification-only" cells | S5, S6 | Score the first decision only, or build the dispatch-off flag (item 9) |
| Wp–Wm 0.70 m under adversarial M1 error | S1 | Latin-square probe records it; fallback is N_G = 4 (drop Wm), which breaks the Ghofrani mapping (owner) |

---

## Open Questions (not derivable from code; flagged, not guessed)

**S1**

1. **Wandering-analog semantics.** GECCO sends a finished agent to the
   minimum-concentration node. Our proxy used present-or-inbound counts with
   seeded ties. The M5 rule and its tie-break must be ruled.
2. **Node-handoff grounding shape.** Lateral-only (needs a backup band
   floor of 0, but `backup_band_m` is [0.5, 2.0]), or an inward backup.
   Nothing in M3 does either today.
3. **Whether Nav2 holds the ±0.35 lane routes** the proxy assumed, or
   centres in the 1.2 m arm. Unmeasured; it decides the W-arm head-on rate.
4. **Dwell value.** 5.0 sim-s is a placeholder. GECCO's dwell is not stated
   in what was read.
5. **Task label wording** in the prompt (`pickup` / `delivery`, versus
   neutral). This touches B2's label-channel precedent.
6. **The 5-stack RTF**, and therefore the per-episode wall time and the
   affordable R. The 0.15–0.19 is an extrapolation.
7. **Prediction-avoidance arm** (v3 Step 3, open). This document does not
   design it.
8. **In-flight cancellation** (v3 Step 3). It is decided by S1's dispatcher
   ruling, not here.
9. **N_A = 10 reservation.** The coordinator reserves N_A = 10 for "the S5
   rung". The brief sizes S5 at N = 8, and v3 Step 5 separately lists "the
   MAPD cell at N = 10". Is N_A = 10 the MAPD rung (density twice S1's),
   S5's N, or both?
10. **Release-stagger robustness.** The non-degenerate window is
    Δ ∈ (0, 4.42) sim-s, and `start_delay_sec` is wall-clock. An RTF swing
    of ±10% moves Δ = 4 by ±0.4 s. Is a wall-clock stagger acceptable, or
    does M5 need a sim-time release? Alternatively, spawn robots off-node
    for the first leg only, which the floor's zero parking capacity makes
    hard.

**S2 / S3**

1. **ε_axis:** keep 0.15, or re-measure (≥ 0.28 absorbs all 14 jams). This
   changes S2's guaranteed floor.
2. **How χ aggregates over a recede set.** This document sums it over the
   jam pair only, excluding non-jam robots. Sum, max, or lead-only must be
   registered.
3. **The follower's task label** (it is rendered), and whether a
   goal-equals-spawn robot reads as "parked" to the VLM.
4. **`_fw` with the 1.65 re-radius, or `_fe` alone.**

**S4**

1. The C_detour value on the fixed stack. No measured detour time exists in
   the documents read here.
2. Whether marker 1 is clean at the held pose (−0.5, 0), or whether to fall
   back to (−2.4, 0).
3. Whether a held, stopped robot with no stall history is read as
   "blocked" at all. If not, the persistence label is still scorable but
   the strategy label loses its premise. A pilot of n = 2 per member
   settles it.

**S5**

1. Garg / MIT-REALM room geometry and N. Their notes do not record it.
2. Marcolino 2017 venue (DBLP).
3. Whether to build a dispatch-off (shadow) flag for S5 and S6, or score
   the first triggered decision with execution left running unscored.

**S6**

1. Whether `t0_probe_mode` probes on a two-conflict scene render both
   conflicts' robots with equal salience. This is a prompt question, not
   geometry.
2. The start-delay value that synchronizes A and B, re-derived from a pilot.

**Cross-cutting**

1. Marker 5–10 assets have never been rendered in any run.
2. Every RTF-dependent time here assumes the fixed stack's timings, which v3
   Step 0 re-baselines.

---

## References

- `docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (rev 2)
- `docs/superpowers/specs/2026-09-29-unified-scene-design.md`
- `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
- `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`
- `feat/prereg-v2-composite@b5cafe4`: the code and reports named in Sources
- Asadi, Nowé, Ghofrani, "Congestion-Aware Multi-Agent Path Planning for
  Pick-up and Delivery Tasks", GECCO '25, 10.1145/3712256.3726339
- Garg et al., arXiv:2404.06413, and the PMLR 2026 VLM-GCBF+ version
- Marcolino & Chaimowicz, IROS 2009; dos Passos, Duquesne & Marcolino,
  arXiv:2201.09335 / RAS 159 (2023)
- A-DRIVE, arXiv:2204.04910 (χ = s·D_SPACE + t·N_f)
