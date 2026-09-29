# Intersection Resolvability — Design Study (S1)

**Prepared:** 2026-09-29

**Revision history:**

- Initial draft: offline design study of whether the four-way `intersection_bottleneck` can be made resolvable with existing machinery plus bounded, named changes (schemes A, B, C, D and a held-in-zone variant), with per-phase clearance, classification, band and duration numbers.

---

## Question and Verdict

The v2 smoke (`data/logs/vm_runs/intersection_v2/`, notes entry 2026-09-29)
discharged S2 (own-arm grounding, `8397509`) and the yielder latch
(backup-phase exemption, `2613575`). S1 stays open: at the standoff the first
passer sits 0.28–0.42 m from the waiting cross pair, and no command exempts
that pair. This study asks whether any design built from existing machinery
plus bounded, named changes resolves the scene, or whether rev 9.3's T1-X
log-only fallback (decision C, `3177615`) stands.

**Verdict: NO-GO for a resolvable four-way. D (T1-X) stands.** The decisive
numbers:

- **The four-way jam itself cannot be cleared.** At the recorded standoffs,
  every first passer's straight escort passes a non-exempt waiter at
  0.017–0.351 m. That holds for every yielder, every order, and a same-axis
  crossing set too. The latch is 0.45 m, and no emergent stop lands a robot
  ≥ 0.45 m from its neighbour: recorded final gaps are 0.241–0.417 m.
- **The shipped grounding cannot clear any north-south pass in this arena.**
  A N-S passer's escort ends at |y| 2.08–2.25. That is 0.28–0.45 m beyond
  the verified tracked band (1.80), which fails the band criterion on its
  own. For s ≤ 0.13, `evaluate_latches` also holds the passer and the parked
  yielder permanently. This binds every staged variant.
- **Only the staged variants resolve, and only with J2.** J2 is a
  junction-scoped `backup_clearance_m` of 1.1, which puts the escort end at
  1.668 m (0.132 m inside the band).
- **Staging loses the tier's identity.** Once the phases are separated,
  Arm B's `intersection` label depends only on the waiting robots sitting
  inside its 1.5 m membership radius:
  - Scheme A holds them at 1.75 m and gets `head_on`.
  - The held-in-zone variant C′ holds them at 1.2 m and gets
    `intersection`.
  - Both ground the same executed E-W command: the same backup, park
    coordinate and escort in 8/8 rows under J2. So the executed resolution
    is two sequential head-ons either way.

C′ is recorded below as the owner-override path, with its build list and its
cost. It is resolvable on every computed number, but the label it earns is an
artifact of the classifier radius, not of the conflict.

---

## Sources Checked

| Source | What it supplied |
|---|---|
| `data/logs/vm_runs/intersection_smoke/IB10_20260929_085349` (git-ignored) | Valid four-way standoff; full-rate `scene_full.jsonl`, `gt/ground_truth.jsonl`, `m4.log` |
| `data/logs/vm_runs/intersection_v2/IBA1_20260929_100038`, `IBB4_20260929_102427` (git-ignored) | Both yield axes exercised; phase timings; yielder park GT; RTF |
| `INTERSECTION_SMOKE_SUMMARY.txt`, `INTERSECTION_V2_SUMMARY.txt`, `PREDICTION_pre_run.txt` | Audit table, pre-registered failure mode, run log |
| `reasoning/baselines/classical_reasoner.py` | Arm B rule order (`head_on` → `intersection` → `blocked_path`), crowding, membership, FCFS |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/shadow_classical.py` | `find_censored_arrivals` |
| `reasoning/rag/command_grounder.py`, `maneuver_geometry.py`, `scene_geometry.py`, `retreat_candidates.py` | Derived grounding: backup clearance, park floor, passer travel, crossing-order resolution |
| `ros2_ws/src/swarm_execution/swarm_execution/safety.py`, `config/safety.yaml` | Latch 0.45 m, STALE band 0.6 m, pair exemption, `admitted_partners` |
| `ros2_ws/src/swarm_simulation/config/nav2_params.yaml` | `collision_monitor` `forward_stop` polygon, footprint, speeds |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/{state_machine,presentation_order,congestion_detector}.py`, `models.py` | Fold rule (solo stall only), episode members and close rule, `start_delay_sec` (wall clock) |
| `ros2_ws/src/swarm_execution/swarm_execution/base_mission.py` | `start_pending` robots get no Nav2 goal |
| `isaac/vgu_sim/{config,oracle,warehouse_builder}.py`, `isaac/scripts/generate_warehouse_map.py` | What a scenario can express (static/timed boxes, barrier); GT intersection oracle; rack geometry |
| `tests/unit/test_intersection_bottleneck_scenario.py` | Junction geometry harness (`_junction_geometry`), the T1 no-scene-objects pin |

**Method.** Every grounded number below was produced by M3's own
`ground_reasoner_result` under the goal-table junction geometry (corridor
half-length 0.6, aisle half-width 0.6, per-robot `arms`) and the shipped
`config/rag.yaml`. The only change is the `backup_clearance_m` override where
J2 is named.

- Classifications come from `resolve_classical` and `find_censored_arrivals`
  on synthetic 60 s ring buffers: 0.25 s sampling, robots at 0.15 m/s from
  their spawns.
- Latch outcomes come from `evaluate_latches`, stepped at 0.1 s.
- Stop and timing facts come from the GT and log files above.
- J1 (same-axis crossing set) is emulated by grounding a two-robot decision.
  Its real change site is the order resolution in `resolve_yield_roles`.
- The analysis scripts ran from the session scratchpad and are not
  committed. Each table names the function it came from, so it can be
  regenerated.

Three conventions apply:

- **Tracked band.** The verified tracked band is |x| ≤ 2.5 and |y| ≤ 1.80.
  IBB4 tracked `robot_3` at GT y −1.80 with 0 STALE. The homography edge is
  |y| 2.092.
- **Mover legality.** The criterion is ≥ 0.55 m GT clearance from every
  non-exempt robot: the latch 0.45 plus 0.10 for M1 error.
- **M1 error.** The measured M1 static error in this arena is median ≤ 0.011
  m and max 0.084 m, over the three runs' stationary rows.

---

## Constraints That Bind Every Scheme

### 1. How robots actually stop

From `gt/ground_truth.jsonl` and the first `safety stop` line per robot in
`m4.log`, mapped to sim time through `scene_full.jsonl`:

| Run | Robot | Stopped by | GT gap to nearest at latch fire (m) | Speed at fire (m/s) | Travel after fire (m) | Final GT gap (m) |
|---|---|---|---|---|---|---|
| IB10 | robot_1 | latch | 0.338 | 0.150 | 0.007 | 0.324 |
| IB10 | robot_3 | latch | 0.338 | 0.133 | 0.011 | 0.324 |
| IB10 | robot_4 | Nav2/collision monitor (stopped 0.03 s before fire) | 0.357 | 0.001 | 0.000 | 0.357 |
| IB10 | robot_2 | Nav2/collision monitor (stopped 0.23 s before fire) | 0.418 | 0.000 | 0.000 | 0.417 |
| IBA1 | robot_1 | latch | 0.335 | 0.142 | 0.035 | 0.279 |
| IBA1 | robot_2 | latch | 0.338 | 0.071 | 0.001 | 0.337 |
| IBA1 | robot_3 | latch | 0.342 | 0.152 | 0.033 | 0.304 |
| IBA1 | robot_4 | latch | 0.313 | 0.162 | 0.024 | 0.279 |
| IBB4 | robot_1 | latch | 0.301 | 0.161 | 0.034 | 0.241 |
| IBB4 | robot_2 | Nav2/collision monitor | 0.327 | 0.009 | 0.000 | 0.327 |
| IBB4 | robot_3 | latch | 0.301 | 0.171 | 0.043 | 0.241 |
| IBB4 | robot_4 | Nav2/collision monitor | 0.327 | 0.001 | 0.000 | 0.327 |

- The first GT pair crossed 0.45 m at 29.4 / 30.7 / 30.3 sim-s. The first
  latch line followed 0.53 / 0.50 / 0.50 sim-s later, at closing speeds of
  0.29–0.33 m/s. So the latch acts at ~0.30–0.34 m, not 0.45.
- For a single mover closing on a stationary robot at 0.15 m/s:
  - The latch path stops it at about 0.45 − 0.15·0.5 − ≤ 0.04 ≈ 0.34 m.
  - The `forward_stop` polygon reaches 0.25 m ahead of `base_link`, ±0.12 m.
    Against a robot body of half-width 0.09, it stops the mover at a centre
    gap of about 0.25 + 0.09 = 0.34 m.
- **No emergent stop lands at ≥ 0.45 m, let alone the 0.5–0.6 m a wait line
  needs.** Only two things can stop a robot at a chosen position:
  - **The spawn under hold-back** (`start_delay_sec`: `start_pending`, no
    Nav2 goal). T2b showed 0.000 m GT displacement in 6/6 runs.
  - **A physical `timed_obstacles` gate.** A `static_obstacles` box would
    close the lane for good.

### 2. The north-south tracked band against the shipped yield

A N-S pass is a two-robot N-S yield: the yielder backs along its own arm, and
the passer escorts to the park point + `passer_clearance_m` (0.45 + 0.2).
Grounded with the E-W robots parked at (±1.75, 0) and standoff offsets ±s:

| s (m) | Backup (m) | Park \|y\| (m) | Escort (m) | Passer end \|y\| (m) | End beyond 1.80 (m) |
|---|---|---|---|---|---|
| 0.10 | 1.50 | 1.60 | 2.35 | 2.25 | +0.45 |
| 0.13 | 1.44 | 1.57 | 2.35 | 2.22 | +0.42 |
| 0.20 | 1.30 | 1.50 | 2.35 | 2.15 | +0.35 |
| 0.27 | 1.16 | 1.43 | 2.35 | 2.08 | +0.28 |

The binding term is `backup_clearance_m` 1.7:

```text
park = max(park_offset 1.018, y_passer + 1.7) = 1.7 - s
end  = park + 0.65 = 2.35 - s
```

Every end is ≥ 2.08. With the marker half-size (0.06), the whole marker
reaches ≥ 2.14, past the 2.092 homography edge, so the passer goes STALE.

Stepping `evaluate_latches` through the escort shows what follows. The run
assumes M1 loses the marker at the verified edge, |y| 1.80. The
yielder↔passer pair stays exempt through the hold, and the last both-fresh
gap is remembered: 0.422 / 0.462 / 0.509 m for s = 0.13 / 0.20 / 0.27. When
the yield completes the exemption drops, and the check still holds both
robots latched after 60 simulated seconds:

- **s = 0.13.** The carried pose sits 0.422 m from the yielder, so the latch
  reason is `min_distance_violation`.
- **s = 0.20 and 0.27.** The remembered gap is under the 0.6 band, so the
  latch reason is `stale_pose_unsafe`.

Release needs a fresh reading of the passer. It is out of frame and latched,
so it can never provide one.

The verified edge is conservative, though. The marker only clips the image
at about 2.092 − 0.06 = 2.03. The STALE rule stops firing once the last
fresh gap to the yielder at (0.36, P) reaches 0.6. That needs a last fresh y
of at least P + 0.48:

| s | Park P | Last fresh y needed to escape the latch | Reachable before the 2.03 clip |
|---|---|---|---|
| 0.10 | 1.60 | 2.08 | no: always latched |
| 0.13 | 1.57 | 2.05 | no: always latched |
| 0.20 | 1.50 | 1.98 | only if M1 keeps a fresh fix at 1.98–2.03 (unverified) |
| 0.27 | 1.43 | 1.91 | only if M1 keeps a fresh fix past 1.91 (unverified) |

**The latch is permanent for s ≤ 0.13.** For larger s it depends on M1's
unverified detection extent between 1.80 and 2.03. The recorded four-way N-S
offsets (0.22–0.33) sit at that sensitive end. The escort end (2.08–2.25 vs
1.80) fails the band criterion regardless, so the conclusion does not change.

This is a property of the arena's short N-S tracked axis (1.80 vs 2.5 on x),
not of the four-way. The existing pin "a N-S same-arm passer's escort would
end outside M1's y band" is its first symptom.

### 3. J2 — a junction-scoped backup clearance (the only escape)

Passer end |y| from the same grounding, sweeping the clearance:

| backup_clearance_m | s = 0.13 park / end | s = 0.20 park / end | s = 0.27 park / end |
|---|---|---|---|
| 1.7 (shipped) | 1.570 / 2.220 | 1.500 / 2.150 | 1.430 / 2.080 |
| 1.5 | 1.370 / 2.020 | 1.300 / 1.950 | 1.230 / 1.880 |
| 1.3 | 1.170 / 1.820 | 1.100 / 1.750 | 1.030 / 1.680 |
| 1.2 | 1.070 / 1.720 | 1.018 / 1.668 | 1.018 / 1.668 |
| 1.1 | 1.018 / 1.668 | 1.018 / 1.668 | 1.018 / 1.668 |

- **Where the floor binds.** The park floor `park_offset_m` = 1.018 binds
  whenever s ≥ clearance − 1.018. At 1.1 it binds for s ≥ 0.082, which
  covers every recorded and corpus offset. The end is then fixed at 1.668 m.
- **Margin.** That leaves 0.132 m to the verified band (1.80), or 0.032 m if
  the full 0.10 M1 budget is charged. Against it, the measured errors are:
  - M4 retreat error, grounded vs GT: IBA1 0.027 m, IBB4 0.041 m.
  - M1 static error: median ≤ 0.011 m, max 0.084 m.
- **Nothing narrower does it.** Lowering `park_margin_m`, a scenario-declared
  field, does nothing while the clearance binds.
- **J2 has to be scoped.** It cannot be a global `rag.yaml` change, because
  1.7 is the verified head-on tuning. It must apply only when the yielder
  has a declared arm, so every head-on pin stays byte-identical. At 1.1 it
  still keeps the "2 × min_distance + margin" form (0.9 + 0.2).

J2 is a prerequisite for **every** four-way variant, the prereg-v2 path
included.

### 4. Arm B classification against where the waiting robots are held

`resolve_classical` on an E-W standoff, with the N-S robots stationary at
(0, ±h) from t = 0 (four E-W standoff sets: corpus ±0.12, IB10, IBA1, IBB4),
zone `crossing_1` r 1.5:

| h (m) | Verdict (sets) | Involved | Arm B order | Yielder | Censored |
|---|---|---|---|---|---|
| 0.60–1.48 | `intersection` (4/4) | all four | robot_3, robot_4, robot_1, robot_2 | robot_2 (E-W) | robot_3, robot_4 |
| 1.50 | `head_on` (corpus, IB10), `intersection` (IBA1, IBB4) | mixed | — | — | — |
| 1.55 | `head_on` (3), `blocked_path` robot_3+robot_4 (IBB4) | mixed | — | — | — |
| 1.75 | `head_on` (4/4) | robot_1, robot_2 | FCFS pair | robot_2 (corpus, IBA1) / robot_1 (IB10, IBB4) | none |

- **Where the flip happens.** It happens where a held robot comes within
  `r_conflict_m` 1.5 of an E-W member: `head_on` is then "crowded" and
  loses. The crowding test needs hypot(x_EW, h) ≤ 1.5, i.e. h ≤ 1.46–1.495
  for |x_EW| 0.12–0.33.
- **What happens between the two tests.** The zone-membership test needs
  h ≤ 1.5. Between the two, IBB4 at h = 1.55 falls through to
  `blocked_path`.
- **The held robots always arrive first.** They are in the zone from the
  first buffered frame, so they are always censored and always ordered
  first. Arm B's own order therefore puts two held robots ahead of the E-W
  passer.
- **Shrinking the FCFS zone makes it worse.** At radius 1.0 (h = 1.2 and
  1.36), the held robots are never seen inside it. They move to the back of
  the order, and **Arm B yields a held robot** (`robot_4`).
- **The yielder choice is a radius effect.** The E-W yielder differs between
  h = 1.75 (IB10 and IBB4 pick robot_1) and h ≤ 1.48 (robot_2). That comes
  from FCFS and commitment being measured over the 1.5 m zone instead of the
  1.0 m pair zone. It is not evidence of intersection-specific reasoning.
- **Phase 2 needs the E-W goals outside the crowding radius.** For a N-S
  standoff with the E-W robots parked at their goals, a goal radius of 1.75
  gives `head_on` (3/3 offsets). A goal radius of 1.45 or 1.2 gives
  `intersection` with **yielder robot_2, a parked robot**, and all four
  censored.

---

## Scheme A — Full Stagger

The N-S pair is held at its spawns (0, ±1.75) (`start_delay_sec`) until the
E-W pair has resolved and arrived.

| Phase | Mover path | Min GT gap to a non-exempt robot (m) | Band check | Notes |
|---|---|---|---|---|
| 1, E-W, shipped | yielder backup 1.15–1.46, park \|x\| 1.37–1.59 | ≥ 1.67 | end \|x\| 2.02–2.25 (margin +0.25 to +0.48) | park → passer goal 0.40–0.53 m: < 0.45 in 4/8 rows, a release race |
| 1, E-W, shipped | passer escort 2.35 m | ≥ 1.66 | in band | — |
| 1, E-W, shipped | returns to goals (straight / worst lane) | 1.49–1.55 / 1.30–1.41 | in band | — |
| 1, E-W, J2 | backup 0.69–0.91, park \|x\| 1.02, escort 1.77–2.00 | ≥ 1.65 | end \|x\| 1.67 | park → passer goal 0.81–0.86 (no race) |
| 2, N-S, shipped | yield along the N-S arm | ≥ 1.72 (E-W parked at goals) | **end \|y\| 2.08–2.25: out of band** | latch permanent for s ≤ 0.13, M1-extent-dependent above (Constraint 2) |
| 2, N-S, J2 | backup 0.75–0.92, park \|y\| 1.02, escort 1.77–1.94 | ≥ 1.72 | end \|y\| 1.668 (+0.132) | resolvable |

- **Classification.** Phase 1 is `head_on` (robot_1, robot_2) for both arms.
  The held robots are 1.67–1.76 m from the E-W pair, beyond the 1.5 m
  crowding radius. Phase 2 is also `head_on`: the parked E-W robots are
  1.75 m out. **The tier degenerates into two sequential head-ons exactly
  when every waiting robot sits more than 1.5 m from both standoff members
  and from the zone centre.** At spawn radius 1.75 that is always true.
- **Required changes.** Scenario-local: N-S `start_delay_sec`. Shared: J2.
- **Verdict.** Resolvable with J2, but never an intersection: it is T1
  `head_on_deadlock` run twice. Rejected.

---

## Scheme B — Partial Stagger

One robot is delayed (`robot_4` at (0, 1.75)). The other three form a
cluster; the recorded standoffs minus `robot_4` stand in for it. Arm B
classifies `intersection` with 3 involved (yielder robot_2 for IB10 and
IBB4, robot_3 for IBA1). First passer's straight escort vs the nearest
non-exempt waiter (`ground_reasoner_result`, orders honoured):

| Yielder / first passer | IB10 (m) | IBA1 (m) | IBB4 (m) |
|---|---|---|---|
| robot_2 / robot_1 (E-W passer) | 0.257 | 0.285 | 0.132 |
| robot_2 / robot_3 (N-S passer) | 0.198 | 0.103 | 0.201 |
| robot_1 / robot_2 (E-W passer) | 0.274 | 0.230 | 0.236 |
| robot_1 / robot_3 (N-S passer) | 0.351 | 0.246 | 0.256 |
| robot_3 / robot_1 (opposing E-W pair) | 0.018 | 0.055 | 0.104 |
| robot_3 / robot_2 (opposing E-W pair) | 0.017 | 0.055 | 0.104 |

- **All 18 fail.** The maximum is 0.351 m, under the 0.45 latch. Any
  cluster that contains a cross-axis robot reproduces S1, because a passer
  is exempt only against the yielder.
- **Changes considered.** Scenario-local: one `start_delay_sec`. None
  helps. Rejected.

---

## Scheme C — Wait Line and Same-Axis Crossing Set

### C as specified (cluster, J1, cross pair latched with no command)

J1 (below) confines the crossing set to the yielder's axis. In the recorded
four-way cluster, the only passer still skims the latched cross pair:

| Yield | IB10 (m) | IBA1 (m) | IBB4 (m) |
|---|---|---|---|
| robot_2, passer robot_1 | 0.257 | 0.258 | 0.132 |
| robot_3, passer robot_4 | 0.223 | 0.106 | 0.221 |

A wait line at 0.5–0.6 m needs a stop mechanism, and Constraint 1 shows none
exists: emergent stops land at 0.24–0.42 m. **Fails.**

### C-gate (a `timed_obstacles` box as the wait line)

- **Geometry.** A box across each N-S arm mouth, face at |y| 0.70, stops a
  N-S robot at `base_link` ≈ 0.70 + 0.25 = 0.95 m. That clears the transit
  line by 0.95 m.
- **It breaks the T1 contract.** `test_t1_carries_no_oracle_and_no_scene_objects`
  requires `timed_obstacles == ()`. The box is also in Arm A's camera frame,
  inviting `blocked_path`.
- **The gated pair triggers first.** It stops ~5.3 sim-s after departure,
  (1.75 − 0.95) / 0.15. Its stall trigger (12 wall-s ≈ 2.5–3.1 sim-s) then
  fires at ~29 sim-s, before the E-W standoff (31–32).
- **That trigger opens its own analysis.** A two-robot event is not a solo
  stall, so it is **not folded** and starts an analysis. Arm B classifies
  that scene as `blocked_path` (robot_3, robot_4) with the E-W pair at
  ±1.0 or ±0.6, and `unknown` at ±0.3. The first command is a reroute
  against the gate.
- **The removal is open-loop.** It is sim-time scripted, not a reasoner
  outcome. Phase 2 then hits Constraint 2 without J2.
- **Fails.**

### C′ — held in zone (the hold-back as the wait line)

The N-S robots spawn at (0, ±h), inside the 1.5 m membership radius, held by
`start_delay_sec`. The goals are unchanged at (0, ∓1.75). With J1 and J2 in
force, at h = 1.2:

| Phase | Check | Value | Criterion |
|---|---|---|---|
| 1 | Arm B verdict | `intersection`, 4 involved, all four standoff sets | — |
| 1 | Arm B own order | robot_3, robot_4, robot_1 (yield robot_2) | — |
| 1 | Own order **without** J1 | robot_3's 2.45 m escort passes through robot_4: 0.000 m | FAIL |
| 1 | Executed order with J1 | robot_1 only (one passer) | — |
| 1 | Yielder backup and pull-off vs held robots | 1.13–1.23 m | ≥ 0.55 PASS |
| 1 | Passer escort vs held robots | 1.11–1.20 m | ≥ 0.55 PASS |
| 1 | Yielder return, straight / worst lane | 0.90–0.98 / 0.75–0.86 m | ≥ 0.55 PASS |
| 1 | Park → passer goal | 0.81–0.86 m (shipped 1.7: 0.39–0.52, 6/8 < 0.45) | ≥ 0.45 PASS |
| 1 | Escort end | \|x\| 1.67 | ≤ 2.5 PASS |
| 2 | Arm B verdict (E-W parked at 1.75) | `head_on` robot_3, robot_4 | — |
| 2 | N-S movers vs parked E-W | ≥ 1.72 m | ≥ 0.55 PASS |
| 2 | N-S passer end | \|y\| 1.668 (J2) / 2.08–2.25 (shipped) | ≤ 1.80 PASS / FAIL |

**The h window.**

- Lower bound: the worst-lane yielder return must stay ≥ 0.55 m. At h = 1.0
  it measures 0.60–0.73 m across the eight rows, only 0.05 m of margin at
  worst. So h ≥ ~1.0.
- Upper bound: the robots must stay crowded and in zone with M1 error, so
  h ≤ ~1.36.
- **The GT intersection oracle (≥ 3 robots within 1.0 m of the origin,
  `isaac/vgu_sim/oracle.py`) is inactive for every h ≥ 1.0.** Making it fire
  needs h < 1.0, which leaves ~0.05 m of return clearance.

**Identity check against scheme A.** Every phase-1 command under J2 is the
same in 8/8 rows (4 standoffs × 2 E-W yielders): backup, park point and
escort. Under the shipped clearance, 3/8 rows differ only in the pull-off
side, because the candidate ranking reacts to the held robots. The executed
resolution is the scheme-A head-on. The `intersection` label comes from the
held robots sitting 0.55 m closer, inside the 1.5 m radius.

**Episode fit.**

- **Phase 1.**
  - The held robots are `start_pending`, so they give no stall evidence.
    At h = 1.2 they are ≥ 1.13 m from anyone, beyond the 0.5 m proximity
    threshold, so they give no close/slow evidence either.
  - The first event is the E-W pair, and J1 dispatches only the E-W pair.
    The episode keeps two members, so the two-robot rules apply: it closes
    on the first arrival.
- **Phase 2.** Its event (robot_3, robot_4) is disjoint from phase 1, so it
  opens a new episode. The fold is never needed.
- **Arm A answers that command a N-S robot.** Such an answer makes phase 1 a
  ≥ 3-member episode that closes on the last arrival. Phase 2 then merges
  into it and inherits its order and failure context.

**Duration budget (sim-s, J2).**

The phase timings come from IBA1 and IBB4:

- Standoff at 31.1–31.6.
- Dispatch at 34.6–38.2.
- The IBA1 backup ran at 0.091 m/s, and from backup end to hold took 11.2 s.
- Escorts at 0.10 m/s; Nav2 legs at 0.15 m/s.

| Segment | Phase 1 | Phase 2 (from release T_r) |
|---|---|---|
| Standoff | 31–32 | T_r + 9 (1.08 m approach) |
| Dispatch | 35–38 | T_r + 16 |
| Hold (backup 0.69–0.92 m + 11.2 s) | ~59 | T_r + 37 |
| Passer clear (escort 1.77–2.00 m) | ~79 | T_r + 57 |
| Yielder at goal (2.79 m return) | ~101 | T_r + 79 |

**Release timing.** `start_delay_sec` runs on M5's wall clock, so T_r ≈ 20 +
RTF·D, where D is the delay in wall seconds. The 20 is M5's start in sim
time: its first `m5.log` line maps to 19.8 / 20.1 / 20.6 sim-s in IB10 /
IBA1 / IBB4, through `scene_full.jsonl`. The constraints are:

- T_r ≥ ~126: phase 1 plus 10 % plus 15 s.
- T_r + 79 ≤ 300.
- RTF between 0.19 and 0.26 (observed 0.21–0.24 at four stacks).

That gives **D ∈ [558, 773] wall-s**. D = 650 gives T_r 143–189 and an end
at 222–268 sim-s, 32–78 s inside the 300 s horizon. Without J2, phase 2's
passer ends out of band, and for offsets ≤ 0.13 m it never completes.

**Verdict.** C′ is resolvable on every computed number, given J1 and J2. It
misses D's identity condition, below.

---

## Scheme D — T1-X Fallback

T1-X (rev 9.3) runs the realigned four-way with `t0_probe_mode`, scores
stage-1 classification only (n = 10), and records the Arm B shadow. The live
record is 35/35 `intersection`. A scheme beats D only if **all** of these
hold:

| Condition | A | B | C / C-gate | C′ |
|---|---|---|---|---|
| Arm B says `intersection` in the phase the command executes | no (`head_on`) | yes | yes / no (`blocked_path` first) | yes |
| Arm B's own order executable (bounded filter allowed) | yes | no | no | only with J1 |
| Every mover ≥ 0.55 m from every non-exempt robot, continuously | yes | no (≤ 0.351) | no (≤ 0.258) | yes (≥ 0.75) |
| Every park and escort end in band after error | only with J2 | n/a | n/a | only with J2 |
| Fits 300 sim-s at RTF 0.19–0.26 | yes | n/a | n/a | yes (D 558–773 s) |
| Changes are scenario/config items plus bounded rules | yes | yes | no (gate breaks T1) | yes (J1, J2) |
| The executed resolution differs from what the same robots get when the waiting robots are outside the membership radius | no | — | — | **no (8/8 identical)** |
| The GT intersection oracle is active during the scored standoff | no | yes | — | **no (h ≥ 1.0)** |

No row of the matrix passes every condition. The last two rows are the
identity conditions: they ask whether the cell tests intersection
*resolution* rather than intersection *labelling*.

---

## Prereg-v2 Path — Composite Junction Clear

The only design that clears the actual IB10 jam is a two-stage command. The
cross pair first reverses along its own arms to |y| ≈ 1.2 (0.93–0.95 m each,
from ±0.25–0.27). That lands exactly in C′'s phase-1 geometry, and the E-W
yield then runs as tabulated there.

- **Exemption during the reverse.** `admitted_partners` pairs a `reverse`
  with every member of its own command. So the reverse legs, which start at
  0.24–0.34 m from the E-W pair, would be exempt without new M4 rules.
- **What it needs.** A multi-action strategy: an M2 schema field, M3
  grounding of per-robot reverses plus a yield, M5 dispatch, and prompt
  wording. It also needs J2 for the later N-S pass.
- **Why it is out of scope here.** That is a new decision contract, not a
  bounded change. It is recorded as the prereg-v2 candidate, next to the
  multi-axis grounding rev 9.3 already names.

---

## Comparison Matrix

| Criterion | A full stagger | B partial stagger | C as specified | C-gate | C′ held in zone | D T1-X |
|---|---|---|---|---|---|---|
| Phase-1 Arm B verdict | `head_on` | `intersection` (3) | `intersection` (4) | `blocked_path` → reroute | `intersection` (4) | `intersection` 35/35 live |
| Phase-2 Arm B verdict | `head_on` | not reached | not reached | not reached | `head_on` | n/a |
| Worst mover gap to non-exempt robot | ≥ 1.30 m | 0.017–0.351 m | 0.106–0.258 m | ~0.95 m | ≥ 0.75 m | n/a |
| N-S end in band (shipped / J2) | FAIL / +0.132 m | n/a | n/a | FAIL / +0.132 m | FAIL / +0.132 m | n/a |
| Shared changes | J2 | none | J1 | J1, J2 | J1, J2 | none |
| Scenario changes | N-S delay | one delay | none | timed boxes | N-S spawns ±1.2, delay 650 s | none (already built) |
| Four-way jam forms | no | no (3-way) | yes | no | no | yes |
| Tests intersection resolution | no | — | — | — | no (radius artifact) | no (RQ1 only, by design) |
| Verdict | reject | reject | reject | reject | owner-override only | **stands** |

---

## Decision

**NO-GO. The T1-X fallback (D) stands, and rev 9.3's text stays binding.**
The four-way jam cannot be cleared by any single-yield decomposition within
bounded changes. The first passer is always ≤ 0.351 m from a non-exempt
waiter, and the stop mechanics make every emergent gap 0.24–0.42 m. The
staged variants do resolve, but only by keeping the jam from forming. Their
executed commands are then scheme A's two head-ons, and the `intersection`
label survives only as a membership-radius artifact.

Two findings stand whatever the verdict:

- **Any N-S pass fails under the shipped grounding.** In this arena, a N-S
  pass with the shipped `backup_clearance_m` 1.7 ends 0.28–0.45 m out of the
  tracked band. It latches permanently for standoff offsets ≤ 0.13 m, and
  above that it depends on M1's unverified y detection extent. Any future
  N-S scenario, and the prereg-v2 path, need J2 first.
- **Arm B's intersection order puts censored held robots first.** Waiting
  robots that sit inside the zone from the first buffered frame always lead
  Arm B's intersection order. Without a same-axis filter, that order is
  inexecutable: the escort runs through the partner at 0.000 m.

**Owner-override path.** If the owner still wants a resolvable four-way cell
and accepts the identity cost, C′ is the design. The cost is that the
`intersection` label is a radius artifact, the GT oracle is inactive at
h = 1.2, both held robots are censored in every run, and the order has one
passer, so there is no RQ3 content. The build list follows.

---

## Owner-Override Build List (C′, conditional)

This is in order. Nothing here is started by this study.

1. **J2 (shared M3, ~10 lines + tests).**
   - Add `SceneGeometry.junction_backup_clearance_m: float | None = None`.
     `derive_backup_distance` uses it in place of `params.backup_clearance_m`
     when the yielder has a declared arm.
   - Pins: the 576-output legacy SHA, the derived two-robot digest and
     `TestJunctionGeometry` stay unchanged with no arms.
   - A new pin checks that the N-S passer end is ≤ 1.70 at s ∈ {0.10, 0.13,
     0.20, 0.27}.
2. **J1 (shared M3, ~20 lines + tests).**
   - In `resolve_yield_roles`: when the yielder has a declared arm, drop from
     the crossing order every robot whose declared arm axis differs. Those
     robots get no action. Tag the degradation `order=junction_same_axis`.
   - The no-arms path is byte-identical. Arm B's shadow retreat follows,
     because it uses the same grounder.
3. **Scenario and config (goal-table row plus YAML).**
   - Scenario: `robot_3` spawns at (0, −1.2) and `robot_4` at (0, 1.2);
     goals are unchanged. Re-derive `expected_conflict`: the onset and the
     involved set are an owner decision.
   - Goal-table row: `start_delay_sec: 650` for `robot_3` and `robot_4`, and
     `junction_backup_clearance_m: 1.1`. Zone `crossing_1` stays at r 1.5.
   - Rebuild the USD and validate it; the map is unchanged. Re-pin the
     scenario tests: the band, the classification at h = 1.2 across the four
     standoff sets, and every waiter gap ≥ 0.55.
4. **Ground-truth decision (owner).** Either redefine the phase-1 authored
   truth (E-W head-on with cross traffic held in zone), or accept that
   `oracle.intersection_conflict_active` stays inactive at h = 1.2. The only
   alternative, h ∈ [0.95, 1.0), leaves ~0.05 m of clearance.
5. **Apparatus.** Fold the Nav2 lifecycle gate and the M5-log pre-create
   into `fc_launch.sh`. Four stacks failed bring-up in 3/8 launches, and the
   workaround is VM-side only.
6. **Offline replay, then a VM mock smoke.**
   - Replay: Arm B forced on the C′ scene through M5's production pipeline,
     as `test_m5_node_t2b_dispatch.py` does for T2b.
   - Smoke: record RTF, the release sim-time, the phase-2 standoff offsets
     and the N-S escort end GT.
   - Pre-register the prediction before any VM action.
7. **Research design amendment (owner, separate change).** It is not made
   here.

---

## Risks and Mitigations

| Risk | Where it bites | Mitigation |
|---|---|---|
| J2 margin is 0.132 m to the verified band (0.032 m against a full 0.10 M1 budget) | C′ phase 2, A phase 2, prereg-v2 | The measured errors are smaller (M4 0.027–0.041, M1 median ≤ 0.011); pin the GT escort end in the smoke; abort criterion \|y\| > 1.80 |
| `start_delay_sec` is wall-clock | C′ release before phase 1 ends | D sized over RTF 0.19–0.26; record RTF per run; T_r at 20 + RTF·D |
| Arm A commands a held robot (N-S yielder or passer) | C′ phase 1 | Legitimate wrong answer (escort through the E-W pair, latched); it makes phase 1 a ≥ 3-member episode that merges phase 2 |
| Censored held robots in every record | C′ Arm B shadow, FCFS analysis | Report as structural, not as data-quality loss |
| Phase-2 standoff offsets assumed (±0.10–0.27) | J2 sizing | The floor binds for s ≥ 0.082, so the end is 1.668 m regardless |
| Release race, passer goal vs yielder park (0.39–0.53 m under shipped 1.7) | A and C′ phase 1 without J2 | J2 moves the park to \|x\| 1.02 (0.81–0.86 m) |

---

## Not Settled by the Data

- **Arm A's picks** on a C′ scene: its classification, yielder axis and
  whether it lists the held robots. This needs VLM runs.
- **Whether a two-robot E-W standoff forms beside robots held at ±1.2** as
  in the head-on corpus. It is inferred, not observed. No run held robots
  inside the zone.
- **Phase-2 N-S standoff offsets.** These are assumed from the head-on
  corpus (±0.12). J2's floor makes the band result insensitive to them.
- **The RTF window at four stacks** beyond the observed 0.21–0.24. The D
  window [558, 773] s assumes 0.19–0.26.
- **Escort overshoot.** It was not measured directly: no v2 escort moved.
  Only the retreat error (0.027–0.041 m) was measured.
- **M1's y detection extent between the verified 1.80 and the marker clip
  at ~2.03.** It decides whether the shipped-grounding N-S latch is also
  permanent for standoff offsets above 0.13 m (Constraint 2).
- **Nav2 bring-up flakiness at four stacks** (3/8 launch failures). Whether
  folding the gate into `fc_launch.sh` suffices, or a larger VM is needed.
