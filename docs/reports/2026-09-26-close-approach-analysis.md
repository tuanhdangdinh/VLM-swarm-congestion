# Close-Approach Root-Cause Analysis - K1 and G4

**Prepared:** 2026-09-26

**Revision history:**

- Initial draft: root cause of the two 0.076 m close approaches (G4 `20260925_191810`, K1 `bshort2/20260926_063238`), established from ground truth, M1 scene logs, M4/M5/Nav2 logs and the robot collision geometry; ranked mitigations; no runtime change.

---

## Summary

The robots were **in physical contact, not interpenetrating**. For about 51 sim-s
in each run, their URDF collision boxes sat face to face with a signed gap of
0.0000 ± 0.0003 m. The 0.076 m centre distance is exactly nose-to-nose for this
robot, as the 2026-09-16 Run D host probe had already measured.

Every layer that "stayed silent" was either **disarmed or never existed**:

- **M4's safety monitor was disarmed by its own coordination exemption.**
  The M3 grounding of ER-2's `reroute` put robot_1 on an `ACTIVE` Nav2 leg and
  robot_2 on an `ACTIVE` `temporary_wait`. Any `ACTIVE` member exempts the pair
  from both the 0.45 m rule and the STALE fail-safe. M5 injects the robot's
  base goal into a waypoint-less `reroute`, so the leg drove robot_1 straight at
  its now-stationary partner. The exemption lasted until the command bus's
  120 s wall-clock Nav2-leg watchdog fired (about 46 sim-s). In K1 the exemption
  also lifted a latch that had already fired.
- **The ground-truth contact field is not a detector.** `robot_robot_contacts`
  is the literal `[]` in the record builder.
- **M1 did flag both robots, contrary to the brief and to Rev 7 §AC.** Both went
  `STALE` at contact in both runs. The monitor ignored the flag under the same
  exemption.

The "~5880 safety stops" in K1 are log lines from a 40 Hz hold loop. They
record about 58 s of latched time across four latch windows, and G4 logged
more (6122) under the same mechanism.

The precondition is a `reroute` that lands on the post-`reverse` re-approach
before any yield. That happened in 2 of the 27 archived runs that opened with
`reverse`, and those 2 runs are the only runs with contact.

**Top-ranked mitigation:** restrict the monitor's exemption to the raw-`cmd_vel`
clearing maneuvers (`yield` and `reverse`). Nav2-goal legs (`reroute`, `convoy`,
`navigate`) and `wait` commands would no longer exempt a pair. This preserves
the yield mechanism, and the unexempted monitor stopped this same pair at
0.27 m on the first approach of both runs.

---

## Scope, Evidence and Method

**Runs.** G4 is `data/logs/vm_runs/20260925_191810/` (east `wopen_e0p2`,
`id_desc`, ER-2). K1 is `data/logs/vm_runs/bshort2/20260926_063238/` (east
`_bshort`, `id_asc`, ER-2). The artifact tree is git-ignored. G4's ground truth
is `ground_truth/ground_truth.jsonl` in the run directory. No `_rescue` copy
was needed.

**Clock alignment.** Ground truth (GT) is in sim time at 10 Hz. M1 stamps and
every ROS log line are wall-clock. I fitted `sim = a + b·wall` per run by
matching moving, non-STALE M1 frames to GT poses within ±3 s sim of an
event-based prior:

| Run | Frames matched | RTF (b) | Residual SD | M1-vs-GT position error |
|---|---|---|---|---|
| G4 | 101 | 0.383 | 0.36 s sim | 7 mm mean |
| K1 | 105 | 0.379 | 0.32 s sim | 7 mm mean |

Sim times quoted for log events below come from this fit (±0.4 s). Wall times
are written `…NNNN.NN`. The elided prefix is `179036` for G4 and `179040` for
K1.

**Geometry.** The Isaac scene imports
`isaac/assets/robots/turtlebot3_burger/turtlebot3_burger.urdf` with
`collision_from_visuals=False` (`isaac/vgu_sim/robot_asset.py:37-42`), so the
URDF collision primitives are the physics shapes. Units are metres, in the
`base_link` frame with x forward:

| Collider | URDF lines | Plan-view extent (base_link) | World z |
|---|---|---|---|
| Chassis box 0.140 × 0.140 × 0.143 | 63-68 | x −0.102…+0.038, y ±0.070 | 0.009–0.152 |
| Wheels, cylinder r 0.033 × 0.018, axis y | 93-98, 123-128 | x ±0.033, y ±(0.071…0.089) | 0.000–0.066 |
| LDS, cylinder r 0.055, centre x −0.017 | 181-186 | x −0.072…+0.038 | 0.160–0.191 |

GT `(x, y, theta)` is the `base_link` world pose
(`isaac/vgu_sim/acceptance_logging.py:230-258`). The chassis nose is therefore
+0.038 m ahead of the logged centre, and two robots nose to nose touch at
2 × 0.038 = **0.076 m**. The Nav2 footprint `[[±0.07, ±0.09]]`
(`ros2_ws/src/swarm_simulation/config/nav2_params.yaml:219`) is a symmetric
planning approximation, not the collision shape.

I computed the signed separation between the two robots' collider sets at every
GT row: exact polygon distance when apart, and SAT penetration depth when
overlapping. The chassis and wheels form one height layer and the two LDS
housings form another. The script is scratch-only and has not been committed.

**Labels.** **Established** means read directly from code (file:line) or a log
timestamp. **Inferred** means reasoned from GT kinematics and timing, or from
code that was not exercised in these runs.

---

## What Happened

Both runs follow the same sequence: approach 1 is latched, `reverse`
separates the pair, the second analysis lands during the re-approach, ER-2
returns `reroute`, and contact follows.

### G4 timeline

| Sim s | Wall | Event | Source |
|---|---|---|---|
| 20.7 | …3984.45 | d crosses 0.45 m at 0.31 m/s closing; monitor latches both robots | GT; `component_logs/m4.log` |
| 21.5 | — | Pair at rest, d = 0.2696 m (0.18 m of post-latch travel) | GT |
| 27.5 | …4001.58 | `reverse` dispatched to both robots (ER-2 decision #0) | M4, M5 |
| 41.2 | …4037.45 | `reverse` COMPLETED; both base missions resumed | M4 |
| 47.7 | …4054.37 | M5 starts analysis: "2 robot(s) stalled >= 12.0s", both robots **MOVING** at x = ∓0.57 | `m5.log`; decision `94a2b925…` |
| 49.8 | …4060.04 | d crosses 0.45 m (M1 frame shows d = 0.409); no latch is logged | GT; scene log |
| 50.1 | …4060.62-.63 | robot_2 `temporary_wait` ACTIVE; robot_1 `reroute` ACTIVE and Nav2 "navigating … to (2.50, 0.00)" | M4; `nav2_r1.log` |
| 50.3 | — | robot_2 stops (the wait cancels its Nav2 goal); robot_1 keeps going at 0.13–0.16 m/s, yawing +0.38 rad | GT |
| **53.2** | ≈…4069.7 | **Contact:** signed collider gap reaches 0 | GT + geometry |
| 52.3–54.7 | …4066.5–…4073.4 | M1 loses both markers; robot_1 is STALE by …4070.10, robot_2 by …4073.43 | scene log |
| 64.5 | …4098.38 | robot_2's 15 s wait completes; robot_2 resumes its base mission toward (−2.50, 0) and pushes; the pair rotates about 0.5 rad; d goes 0.103 → 0.076 | M4; `nav2_r2.log`; GT |
| 67–96 | — | Nose to nose at d = 0.076–0.077 m, gap 0.0000 ± 0.0003 m | GT + geometry |
| 96.4 | …4181.65 | Nav2-leg watchdog fails the `reroute` 121.0 s wall after ACTIVE | M4 |
| 96.4 | …4181.70 | Monitor latches both robots on carried STALE poses (d = 0.130) | M4 |
| 104.6 | …4203.11 | Second `reverse` ACTIVE; contact ends at 104.2–104.9 | M4; GT |
| 135.0 | …4282.60 | `yield` (resolution) | M4 |

Contact lasted from sim 53.2 to 104.2 (**51.0 s**, one continuous interval).
GT has 785 rows below 0.45 m (26.2%).

### K1 timeline

| Sim s | Wall | Event | Source |
|---|---|---|---|
| 21.3 | …4454.07 | Latch at the 0.45 m crossing; rest at 0.268 m | `m4.log`; GT |
| 27.8 | …4471.05 | `reverse` dispatched to both robots | M4 |
| 42.2 | …4509.21 | `reverse` COMPLETED; base missions resumed | M4 |
| 48.8 | …4526.79 | M5 analysis: "2 robot(s) stalled >= 12.0s", both **MOVING** (x = −0.62 / +0.36) | `m5.log`; decision `01c47751…` |
| 50.55 | …4531.33 | d crosses 0.45 m; monitor **latches both** | M4 |
| 50.85 | …4532.12-.13 | robot_2 `temporary_wait` ACTIVE; robot_1 `reroute` ACTIVE and Nav2 "navigating from (−0.30, 0.00) to (1.50, 0.00)"; the latch is lifted | M4; `nav2_r1.log` |
| 51.0–51.5 | — | Both robots slowed by the 0.8 s wall latch; robot_2 stops at d = 0.296 and stays stopped | GT |
| 51.5–53.5 | — | robot_1 re-accelerates to 0.15 m/s at +0.35 rad yaw; d closes 0.296 → 0.110 | GT |
| **53.3** | ≈…4538.6 | **Contact** | GT + geometry |
| 52.85 | …4537.4 | Last fresh M1 frame; both robots STALE by …4542.68 | scene log |
| 65.45 | …4570.70 | robot_2's wait completes; robot_2 resumes toward (−2.60, 0); the pair rotates; d goes 0.100 → 0.076 | M4; `nav2_r2.log`; GT |
| 97.15 | …4654.42 | Watchdog fails the `reroute` 122.3 s wall after ACTIVE; monitor latches at …4654.49 on carried poses (d = 0.119) | M4 |
| 105.2 | …4675.59 | Second `reverse`; contact ends at 104.9 | M4; GT |
| 134.3 | …4752.57 | `yield` (resolution) | M4 |

Contact lasted from sim 53.3 to 104.9 (**51.6 s**). GT has 770 rows below 0.45 m
(25.7%).

---

## Q1 - Interpenetration or Contact?

**Verdict (established): sustained face-to-face contact. The rigid bodies did
not interpenetrate, and the geometry did touch.**

The signed separation between the two collider sets is 0.0000 m ± 0.0003 m for
every row of the wedge in both runs. The deepest "overlap" is −0.3 mm
(G4 sim 56.8, chassis against wheel; K1 sim 53.8), which is at the 0.1 mm
rounding floor of GT plus the PhysX contact offset. No row in either run
overlaps by more than 2 mm.

```text
G4  t=70.0  d=0.0763  body-body gap=+0.0000  lidar-lidar gap=+0.0002  heading-to-bearing r1=+4.5 deg  r2=+4.5 deg
K1  t=84.0  d=0.0760  body-body gap=-0.0000  lidar-lidar gap=-0.0000  heading-to-bearing r1=+0.1 deg  r2=+0.1 deg
```

The robots are aligned nose to nose: each heading is within about 10° of the
bearing to the other robot. That is why the lateral offsets the brief noted
(G4 r1 y = +0.074, r2 y = +0.027) do not imply a corner-to-corner miss. The
pair had rotated jointly about 0.6 rad while keeping contact, so both front
faces and both LDS housings touch at d = 0.076.

This agrees with the prior host measurement in `docs/implementation_notes.md`
(2026-09-16, Run D). Driving one robot into another at 0.1 and 0.2 m/s
plateaued at 0.0760 / 0.0765 m, collision is enforced on all five collider
prims, and "an earlier reading of this as interpenetration was wrong". The Run H
entry (2026-09-17) also records "contact is 0.076 m".

**The contact detector was not wrong. It does not exist.** `build_acceptance_record`
writes `"robot_static_contacts": []` and `"robot_robot_contacts": []` as
literals (`isaac/vgu_sim/acceptance_logging.py:98-99`), and nothing else in the
repository populates them. The Run D entry already said so. Rev 7 §AC's framing
("detector silence") and the claims of "interpenetration" and "≈0.35 m robots"
in Rev 7 §AC and Rev 10 §AI are therefore incorrect. So is the
"~0.14 × 0.18 m bodies … chassis overlapped" in
`bshort2/_analysis/notes.txt` item 5. The 0.14 × 0.18 m figure is the Nav2
footprint, and the collision box is 0.14 m long but offset 0.032 m rearward.

**Contact duration** (signed gap < 1 mm): one interval per run, G4 sim
53.2–104.2 (51.0 s) and K1 sim 53.3–104.9 (51.6 s). The other 41 archived runs
with GT and an M4 log never came within 0.05 m of contact. Their minimum signed
gap is +0.073 m (run `20260925_130115`, centre distance 0.164 m).

---

## Q2 - What M4's Safety Monitor Did

### How it measures and acts (established)

- **Distance source:** M1 `/perception/scene_state` only, centre to centre
  (`safety_monitor_node.py:91-97, 128-158`; `safety.py:97`). It does not use odom
  or TF.
- **On breach** it cancels the robot's Nav2 goals once, on the newly-flagged
  edge (`safety_monitor_node.py:170-177`). It then publishes a zero `Twist` on
  `/<robot>/cmd_vel` at 40 Hz (`:76, :99, :118-120`) and publishes
  `/safety/holds`. The Isaac `cmd_vel` relay zeroes held robots
  (`99edaca`, 2026-09-17 notes).
- **Release** needs a fresh, non-STALE reading at or beyond 0.45 m
  (`safety.py:144-146`).
- **Exemption:** a robot whose last `/coordination/status` was `ACTIVE` joins
  `_coordinating` (`safety_monitor_node.py:109-116`). Any pair with a
  coordinating member is skipped by the distance rule (`safety.py:95-96`) and by
  the STALE rule (`safety.py:192-193`). A coordinating robot's existing latch is
  not kept (`safety.py:202-203`), and coordinating robots are removed from the
  final latched set (`safety_monitor_node.py:161`).
- **Who publishes ACTIVE:** the command bus. It does so on Nav2 goal acceptance
  for `navigate`, `goal`, `priority_override`, `reroute` and `convoy` legs
  (`command_bus_node.py:113-155, 340-343`), and immediately for any `wait`,
  `temporary_wait` or `stop` with a duration (`:298-305`). Yield and reverse
  publish ACTIVE through their backup callbacks.
  `coordination_client` never publishes ACTIVE for base missions
  (`coordination_client_node.py:125-142`).

### What it logged (established)

Every `safety stop` line, clustered into latch windows:

| Run | Latch window (wall) | Duration | Lines | Relation to contact |
|---|---|---|---|---|
| K1 | …4454.07–…4471.17 | 17.1 s | 1738 | Approach 1; ended by the `reverse` exemption |
| K1 | …4531.33–…4532.70 | 1.4 s | 142 | Approach 2; **lifted by the `reroute`/`temporary_wait` ACTIVE at …4532.13** |
| K1 | …4654.49–…4675.60 | 21.1 s | 2126 | Last 7.7 sim-s of contact, after the watchdog FAILED |
| K1 | …4734.09–…4752.57 | 18.5 s | 1874 | Approach 3; ended by the `yield` exemption |
| G4 | …3984.45–…4001.71 | 17.3 s | 1752 | Approach 1 |
| G4 | …4181.70–…4203.13 | 21.4 s | 2174 | Last 8 sim-s of contact |
| G4 | …4261.09–…4282.61 | 21.5 s | 2196 | Approach 3 |

The monitor logged **zero lines** from the `reroute` ACTIVE to the watchdog
FAILED: …4532.70–…4654.49 in K1 and …4060.63–…4181.70 in G4. That span covers
the whole closing from about 0.41 m to contact and the first ≈43 sim-s of
contact.

### Reconciling "5880 safety stops" (established)

`_emergency_stop` logs `safety stop robot=… reason=min_distance_violation` on
every call, and the 40 Hz hold timer calls it for every latched robot
(`safety_monitor_node.py:118-120, 214-218`). That gives about 100 lines/s with
two robots latched. 5880 lines therefore measure about 58 s of latched wall time
across four windows, not 5880 events. G4 has more (6122 lines over three
windows), so K1's count is not anomalous.

Two instrumentation defects follow:

- `bshort2/_analysis/analyze_b2.py:174` (`m4_safety_stops`) measures latch
  duration.
- The `reason=` field is not usable. Line 217 hard-codes
  `min_distance_violation`, which contradicts the comment at lines 173-174.
  Only the once-per-latch line at line 176 carries the real reason. Both
  re-latches in the wedge log `min_distance_violation`: rule 1 fired on the
  frozen carried poses (0.119 / 0.130 m).

### Candidate mechanisms tested

| Candidate | Verdict | Evidence |
|---|---|---|
| Approach speed vs stop latency | **Rejected** as the cause | Unexempted, the same pair at the same 0.30–0.31 m/s closing came to rest at 0.268 m (K1) and 0.2696 m (G4) on approach 1. Across the 84 other full-speed (closing ≥ 0.25 m/s) 0.45 m crossings in the archive, rest distance was 0.164–0.397 m (median 0.277), with post-crossing travel 0.053–0.286 m. None reached contact. Their exemption state was not checked individually. |
| Stop applied to one robot while the other advanced | **Observed, but a symptom** | robot_2 was stopped by its `temporary_wait` cancel while robot_1 advanced. robot_1 was not latched at all, because its pair was exempt. |
| Commanded maneuver leg bypassing the monitor | **Root cause (established)** | The exemption rules above. The silent window equals the `reroute` ACTIVE span, and the latch fires within 0.07 s wall of FAILED. |
| Stale or different position source | **Rejected** | M1 was fresh (age ≤ 0.7 s wall) through the closing and went STALE only at contact. The frozen poses (0.119 / 0.130 m) were below 0.45 m, and a non-exempt monitor latched on them immediately (…4654.49, …4181.70). |
| Hysteresis or timeout re-enabling motion | **Rejected** | Release requires a fresh reading ≥ 0.45 m and none occurred. The only release in the wedge was K1's exemption lift at …4532.13. |

**G4 ordering (inferred).** G4 shows no latch at all near the crossing. M1
reported d = 0.409 in a frame stamped …4060.04, and the exemption went ACTIVE
0.59 s wall later. Either the monitor received that frame after …4060.62,
because M1's publish latency is not logged, or it saw no earlier sub-0.45 m
frame. In both runs the exemption covered the entire closing. In K1 it
provably released an existing latch. The same mechanism produces both
outcomes, with different timing.

**The exemption's duration is not what the spec says (established).**
`docs/specs/module4/safety-monitor.md` §7 (lines 230-235) says a wedged
`ACTIVE` is "bounded … by the nav2-leg watchdog … (`command_timeout_sec: 20.0`)".
The actual deadline is `max(3 × command.timeout_sec, 120 s)` on
`time.monotonic()` (`command_bus_node.py:42-44, 355-359`, from `ac640ae`,
2026-07-03, which predates the spec text). The `timeout_sec` on the wire is
M5's `command_timeout_sec: 20.0` (`swarm_orchestrator/config/orchestrator.yaml:26`,
`orchestrator_node.py:517-519`), so the deadline is max(60, 120) = 120 s wall.
The `safety.yaml` key of the same name is loaded only by the safety monitor,
which ignores it (`safety_monitor_node.py:231-247`). Both watchdogs fired at
121–122 s wall, which is about 46 sim-s at RTF 0.38. The `reroute` leg was never "wedged" either. Nav2
kept replanning at about 1 Hz (118 "Passing new path to controller" lines in K1)
and handled "Failed to make progress" (K1 …4583.49, G4 …4112.13) with a costmap
clear, so the goal never terminated.

---

## Q3 - Why M1 Did Not Flag Anything

**Verdict (established): M1 did flag both robots, in both runs.** The brief's
premise and Rev 7 §AC ("M1 did not go STALE in G4") are wrong:

| Run | Last fresh frame | STALE by | Fresh again |
|---|---|---|---|
| G4 | robot_1 …4066.5 (sim 52.3, d ≈ 0.138); robot_2 …4067.4 | …4070.10 / …4073.43 | …4203.9 (after the second `reverse`) |
| K1 | both …4537.4 (sim 52.85) | …4542.68 | …4678.9 |

Through the closing, M1 tracked both robots with fresh detections and correct
kinematic status: MOVING, then SLOW or STOPPED for the robot held by its wait.
M1 poses matched GT to 7 mm. The markers are 0.12 m squares centred on
`base_link` (`isaac/vgu_sim/marker_asset.py:6`), so at centre distances below
about 0.12–0.16 m (depending on yaw) the quads overlap in the overhead view and
neither is detectable. This is the Run D mechanism (2026-09-16 notes), and
`stale_after_sec: 3.0` (`perception.launch.py:78`) then declared STALE on
schedule. G4's robot_1 lost its marker 0.9 sim-s before body contact, because
its 35° yaw widened its plate's extent.

STALE was a consequence of the contact, not a cause. The STALE fail-safe
(`safety.py:185-205`) would have latched on either half of its rule: the
remembered fresh distance 0.119 / 0.138 m is below `stale_unsafe_distance_m`
0.6. It was skipped for the same reason as rule 1: a coordinating member was
present (`safety.py:192-193, 202-203`). The spec had anticipated this blind
window (§7, "a wedged `ACTIVE` status disarms the fail-safe") but bounded it at
20 s.

**Side finding (established).** M1's `linear_velocity` is metres per
**wall** second. It is computed over image-header stamps
(`state_estimator.py:22-27`, `perception_node.py:156`), which Isaac fills with
system time. At RTF 0.38, M1 reported 0.060 m/s while GT showed 0.155 m/s.
The monitor's `speed_limit_violation` rule (0.2 m/s) therefore cannot fire
unless the true sim speed exceeds about 0.52 m/s, and `stale_after_sec` is about
1.15 sim-s. Any speed-based mitigation fed by M1 must correct for this.

---

## Q4 - Why the Opening Non-Yield Phase

**Verdict: the exposure window is a `reroute` that lands during the post-`reverse`
re-approach, before any yield. Both parts are established. The rate is
descriptive only (n = 2).**

1. **What the `reroute` command does (established).** M3 grounds `reroute` as
   `reroute {"waypoints": []}` for the first robot and a 15 s `temporary_wait`
   for the others (`reasoning/rag/command_grounder.py:533-550`). M5 then
   injects the robot's current base goal (`orchestrator_node.py:545-552`), and
   the command bus sends a `navigate_to_pose` to that goal
   (`command_bus_node.py:126-146`). Nav2 confirms it: robot_1 was sent to
   (1.50, 0) in K1 and (2.50, 0) in G4, which is its own base goal on the far
   side of its partner in a single lane. The wait stops the partner. When the
   wait expires 15 s later, the partner resumes its base mission toward the
   first robot. Both robots stay exempt throughout.
2. **Why it lands mid-approach (established code, inferred timing).** M5's
   progress detector keeps each robot's best distance-to-goal and does not reset
   it when a command completes (`congestion_detector.py:99-108`). After a
   `reverse`, a re-approaching robot shows no "improvement" until it passes its
   pre-reverse best. The stall clock therefore runs through the reverse and the
   re-approach, and it fires as soon as the 15 s cooldown ends.
   - K1: robot_1 distance-to-goal was 2.12 at the analysis, against a best of
     about 1.77 at the approach-1 standoff.
   - Both analyses started with the pair MOVING at d ≈ 1.0–1.1 m.
   - With about 5 s wall of ER-2 latency, the command landed at d ≈ 0.41
     (G4) and at 0.30 m, 0.8 s wall after the latch (K1).
3. **Discriminator across the archive (established, descriptive).**

| Group | Runs | Contact |
|---|---|---|
| Opened with `reverse`; post-reverse decision `yield` | 25 | 0 |
| Opened with `reverse`; post-reverse decision `reroute` | 2 (G4, K1) | 2 |
| `reroute` dispatched after a yield had already resolved the head-on | 6 (`20260925_063520`, `_162451`, `_163949`, gshort H2, H3, H6) | 0 |

In those 6 later runs, the robots were STOPPED or SLOW at d = 0.43–1.61 m and
had already passed each other. The Nav2 leg ran up to 122.7 s exempt without
contact, because driving to the goal then moves away from the partner.
Of the runs whose local artifact copy records the backend, 15 ER-2 runs opened
with `reverse` and 0 of 12 gpt-4o runs did. This is why the exposure appears
under ER-2. Twelve reverse-opened runs (J and H batches, early 09-25 runs) have
no backend recorded locally.

"East-side" is not supported as a factor at n = 2. Both contacts are east
variants, but so are most of the reverse-opened runs that yielded without
incident.

---

## Verdict on Physical Contact

| Claim | Status |
|---|---|
| The robots' collision geometries were in contact, nose to nose, for 51.0 s (G4) and 51.6 s (K1) of sim time | **Established** (GT + URDF geometry; matches the Run D host probe) |
| The rigid bodies interpenetrated | **Refuted** (≤ 0.3 mm, within rounding and contact offset) |
| Contact was driven, not a resting touch | **Established**: robot_1 under an ACTIVE Nav2 `reroute` leg, then robot_2 on its resumed base mission, with visible joint rotation (GT yaw change of about 0.5 rad at sim 65–75) |
| Contact force or impulse magnitude | **Unknown** (not logged) |

---

## Q5 - Mitigations, Ranked

None of these is implemented. The constraint for every option is that a
completed yield legitimately brings the pair to 0.164–0.28 m (archive minimum
gap +0.073 m), and a yield command stays ACTIVE for up to about 150 s wall
(K1 `…4752.57`–`…4901.45`). A bare 0.45 m hard stop or a short exemption bound
on yield would break the mechanism.

### 1. Restrict the exemption to clearing maneuvers (recommended)

Only a robot whose ACTIVE command is `yield` or `reverse` should exempt a pair.
These run raw-`cmd_vel` backup, sidestep, hold and escort primitives. Nav2-goal
legs (`reroute`, `convoy`, `navigate`/`goal`, `priority_override`) and
`wait`/`temporary_wait`/`stop` should not exempt anything. The monitor needs to
know the action behind each ACTIVE. `CoordinationStatus` carries none, so it
would have to track `/coordination/commands` by `(command_id, robot_id)`, or the
bus would have to publish an explicit exemption set.

- **Why it would have prevented both contacts.** Without the exemption, the
  monitor stopped this pair from the same closing speed at 0.268 / 0.2696 m on
  approach 1 of both runs. None of the 84 other archived full-speed crossings
  reached contact (minimum rest 0.164 m). In K1 the latch had already fired, and
  only the exemption released it. Established from the logs; the counterfactual
  itself is inferred.
- **Yield is preserved** (inferred from code):
  - During backup, pull-off, hold and escort, the yielder's own `yield` stays
    ACTIVE (`command_bus_node.py:196-296`). The pair stays exempt through the
    yielder even though the passer's linked `temporary_wait` would no longer
    exempt it.
  - The escorted passer passes the parked yielder at about 0.37 m, inside
    0.45 m, and that is covered by the yielder's exemption. At yield COMPLETED
    the pair is already 0.73–0.76 m apart (K1 `…4901.12`, G4 `…4433.45`
    scene frames), so dropping the exemption latches nothing.
  - For `reverse`, both robots are ACTIVE and moving apart.

  Still to verify: the existing safety and command-bus unit tests, plus one
  host run.
- **Costs:**
  - A `reroute` that has to pass within 0.45 m of a non-coordinating robot will
    latch. In a single lane that is the correct outcome, and M5's close/slow
    trigger re-analyses.
  - A held robot with an ACTIVE Nav2 leg sits until the 120 s wall watchdog,
    about 46 sim-s of dead time. Pair this option with option 2.
  - It changes the spec (§5.1, §7) and the monitor interface.
  - It changes no M2/M3/M5 behaviour, so it applies equally to every
    experiment arm.

### 2. Bound Nav2-leg exposure and fix the spec (pair with 1)

Fail a coordination Nav2 leg promptly when its robot is held or Nav2 reports
"Failed to make progress", and correct the §7 text from "20 s" to the actual
behaviour.

- **Alone, it does not prevent contact.** Contact came 2.4–2.5 sim-s after the
  leg went ACTIVE, and no plausible bound is that short. It would have cut the
  51 s pushing to seconds.
- **Evidence the cost is small:** 4 of the 8 archived `reroute` legs ran to
  the 120 s watchdog (G4, K1, `_162451`, `_163949`). The others completed in
  0.1–97 s wall.
- **Cost:** it may abort a slow but legitimate reroute. None has been observed.

### 3. Closing-speed-gated hard floor plus an approach-speed cap inside 0.45 m (defence in depth)

The brief's 0.15 m floor does not work on its own. Post-latch travel at full
closing is 0.053–0.286 m (median 0.173), so a trigger at 0.15 m leaves
0.074 m before contact and would not have stopped G4's 0.31 m/s closing. M1
also loses the markers at about 0.12–0.14 m, which leaves less than one frame of
margin. A floor high enough to stop in time (≥ 0.36 m) collides with
legitimate yield distances (0.164–0.28 m). The floor becomes viable only with a
closing-speed cap inside 0.45 m. Travel scales with speed, so about 0.03 m at
0.05 m/s closing (inferred, linear extrapolation). It must also be gated on
*closing*, so that the parked, static yield pair is not affected.

- **Costs:**
  - Nav2 and raw-`cmd_vel` speed plumbing.
  - Tuning.
  - Closing speed must not come from M1 `linear_velocity` without correcting
    for RTF (Q3 side finding).
  - The escort drive past a parked yielder must stay outside the cap, which is
    why the cap is gated on closing.

### 4. Real contact reporting in Isaac (measurement, not prevention)

Populate `robot_robot_contacts` from a PhysX contact report on the chassis
colliders so that the safety columns measure contact instead of inferring it
from distance.

- **Cost:** M6 code. Behaviour under the Newton backend is unverified; the
  memory notes show Newton differs from PhysX for Fabric sync. Until this
  lands, the signed-gap computation used here (collider geometry against GT
  pose) is a sound offline substitute and should replace the contact columns.

### 5. Not recommended mid-pre-registration

- **Reset the M5 stall memory on command completion.** This removes the
  mid-approach trigger timing, but a later `reroute` at a latched standoff
  still releases the pair (the K1 pattern). It changes the trigger instrument
  for every arm.
- **Stop injecting the base goal into waypoint-less `reroute`, or treat it as
  infeasible in a single lane.** This removes the "drive through the partner"
  semantics, but it changes the M3/M5 strategy-to-action mapping, which is part
  of the pre-registered instrument. It also leaves the exemption hole open for
  `convoy` and `navigate`.

---

## What Remains Unknown

- **Why Nav2's own guards did not stop robot_1.** Neither the DWB local costmap
  nor `collision_monitor`'s `forward_stop` polygon (x 0.02–0.25 m, y ±0.12 m;
  `nav2_params.yaml:366-373`) stopped robot_1 while it drove into a stationary
  robot_2. None of the 88 archived Nav2 logs contains a "Robot to stop" line. A
  plausible cause, not checked, is that the 2D scan plane (world z about 0.18 m)
  clears the partner's chassis top (0.152 m) and hits only its LDS housing, and
  that the LDS `minRange` is 0.12 m (`isaac/config/lidar/turtlebot3_lds_01.json`).
  This fourth layer was absent from the brief's list.
- **G4's latch/exemption race.** It is unknown whether the monitor received the
  first sub-0.45 m frame before `…4060.62`, because M1's publish latency is not
  logged.
- **Contact forces**, and whether either chassis tipped or climbed. GT has no z,
  but the exact 0.076 m plateau, identical to the flat-floor host probe, argues
  against climbing.
- **Backend for 12 reverse-opened runs.** The local config copy does not record
  it, so the ER-2 attribution in Q4 rests on the 27 runs whose backend is known.

---

## Corrections to Earlier Documents

These are recorded here rather than edited in place. A Rev 11 of
`docs/reports/2026-09-25-overnight-findings.md` should carry them.

- Rev 7 §AC and Rev 10 §AI:
  - "interpenetrated" / "chassis overlapped" should read "in sustained
    nose-to-nose contact at 0.076 m".
  - "≈0.35 m robots" is wrong: the collision box is 0.14 m and the nose is
    0.038 m from the logged centre.
  - "M1 did not go STALE in G4" is wrong: both robots were STALE for about
    133 s wall in G4 and about 136 s in K1.
  - "zero contacts is detector silence" should read "the contact fields are
    hard-coded `[]`".
- `bshort2/_analysis/notes.txt` item 5: same interpenetration correction. The
  5880 safety stops are about 58 s of latched time, not events.
- Rev 7 §AC ("the July "Run D" incident") and the investigation brief: Run D
  was 2026-09-16, which is what `safety.yaml`'s own comment says.
- `docs/specs/module4/safety-monitor.md` §7: the exemption bound is 120 s
  wall-monotonic (about 46 sim-s at RTF 0.38), not 20 s.
