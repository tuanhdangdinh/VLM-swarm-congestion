# Weekly Progress Report — Week 4

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 24–30 June 2026 · **Report date:** 30 June 2026

> This is an individual capstone project. Contributions are attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 4 completed the navigation layer and executed the first coordination strategies, taking the system from "robots move" to "robots plan paths and respond to orchestrator decisions." The Nav2 stack was installed and verified on the simulation host, a static occupancy-grid map was authored from the warehouse configuration, and each robot received a per-robot Nav2 bringup with an RTX lidar wired into its costmaps, closing Milestone 2. On top of autonomous navigation, Module 4 Phase 2 added the safety layer and the first two coordination behaviours: the yield strategy holds a robot until a passing robot clears the aisle, and the temporary-wait strategy pauses Nav2 for a set duration. The Module 2 prompt was also refined so the VLM receives each robot's goal and a clearer definition of deadlock. With these pieces in place, an orchestrator decision now produces a concrete change in robot behaviour — the essential requirement for closing the loop. The week's recurring difficulty was a race between Nav2 and the safety monitor that could zero out commanded velocity; the fix required bypassing the collision monitor for deliberate backup manoeuvres. Next week will focus on making the closed loop reliable on naturally emerging deadlocks.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | Nav2 install verified on the simulation host | Execution | Recorded verification of the Nav2 Jazzy package install |
| 2 | Static warehouse occupancy-grid map | Simulation | Map authored directly from `WarehouseConfig` for use by Nav2 costmaps |
| 3 | **Per-robot Nav2 bringup (Milestone 2 complete)** | Execution | Per-robot Nav2 launch and parameters, ground-truth `map→odom` TF, and a vendored Nav2 launch pinning the lifecycle nodes; robots now plan paths to goals |
| 4 | RTX lidar integration | Simulation / Execution | RTX lidar USD prim helper with offline tests and per-robot ROS graph wiring; ArUco/lidar height-separation verified |
| 5 | Nav2 adapter with unit tests | Execution | `Nav2Adapter` covered by unit tests using a fake action client, plus a documented-skip goal-with-obstacle acceptance test |
| 6 | **Safety monitor and backup manoeuvre** | Execution / Safety | Minimum-distance and command-timeout enforcement; a direct backup path that cancels the active Nav2 goal and bypasses the collision monitor to break a jam safely |
| 7 | **Yield and temporary-wait strategies** | Execution / Orchestration | Yield holds position until the passing robot clears the aisle; temporary-wait holds Nav2 paused for a configured duration before completing |
| 8 | Module 2 prompt refinement | Semantic reasoning | Deadlock definition clarified and per-robot goals passed to the VLM, improving decision relevance |

The week's aim was to make the orchestrator's decisions actionable. Autonomous navigation came first, because a coordination strategy such as "yield" is only meaningful once a robot is otherwise driving itself toward a goal; this required not just Nav2 but a map, correct TF, and a lidar feeding the costmaps. The two coordination strategies were then implemented as the minimal set needed to resolve a head-on encounter: one robot yields while the other is granted passage, or a robot waits out a transient obstruction. Building the safety monitor in the same week was deliberate — autonomous motion makes proximity a real hazard, and the coordination manoeuvres themselves (particularly reversing) must not be vetoed by a naïve collision stop, which is why the backup path is allowed to bypass the collision monitor under controlled conditions.

## III. In-Progress / Ongoing Tasks

- **Reliable closed-loop resolution — ~60%.** Individual strategies execute, but the full detect→decide→ground→act→resolve loop is not yet dependable on a naturally emerging deadlock; command lifecycle and safety-timing edge cases remain. *Next action:* harden the M5 command tracker and safety timing against real runs. *Target:* Week 5.
- **Nav2/safety race conditions — mitigated, not closed.** The backup-command race was fixed this week, but related timing between goal cancellation, the collision monitor, and command timeouts needs further tuning. *Target:* Week 5.
- **Additional strategies (reroute, reverse, convoy) — pending.** Only yield and temporary-wait are implemented; the remaining strategies in the VLM's vocabulary are not yet executable in M4.
- **M3 RAG action grounding — still specification stage.** Grounding remains a placeholder; the priority has been closing the physical loop first.
- **Credible congestion scenario — under review.** The current aisle geometry does not always force a genuine deadlock, which weakens the eventual evaluation. *Target:* Week 5.

## IV. Outcomes & Achievements

Milestone 2 is fully closed: robots navigate autonomously to goals using Nav2 with lidar-based costmaps on the simulated warehouse map. More significantly, the system executed its first coordination behaviours — an orchestrator decision now changes what a robot physically does, which is the qualitative threshold between a perception-and-reasoning demo and an actual coordination system. In roughly 14 commits the test suite reached about 390 test functions, with new coverage for the Nav2 adapter, safety timing, and the strategy handlers. The Module 2 prompt refinement is a smaller but meaningful result: passing goals and a sharper deadlock definition to the VLM measurably improved the relevance of its decisions on the head-on scenario.

## V. Challenges, Risks & Mitigation

- **Safety-monitor vs. coordination race.** The collision monitor and Nav2 goal cancellation could together zero the commanded velocity, so a robot ordered to back out of a jam would instead freeze. *Impact:* the loop could not resolve a deadlock. *Mitigation:* deliberate backup manoeuvres cancel the Nav2 goal and bypass the collision monitor under bounded conditions; a follow-up fix reduced the monitor's stop-publish timeout.
- **ROS2 Jazzy environment friction.** Nav2 on Jazzy required a vendored launch to pin lifecycle nodes and careful parameter typing. *Impact:* silent startup failures. *Mitigation:* the working install and launch configuration were recorded for reuse.
- **Scenario realism.** A deadlock that does not reliably form undermines the evaluation. *Impact:* weak experimental evidence. *Mitigation:* a narrower, more constrained corridor scenario is planned for Week 5.

## VI. Plan for Next Week

Week 5 will make the closed loop reliable rather than merely demonstrable. The focus is on hardening: fixing the command-lifecycle and safety-timing edge cases that prevent a naturally emerging deadlock from being resolved every time, and tightening the safety margins now that manoeuvres run under sim time. A more constrained corridor scenario will be authored so that congestion is credible and repeatable, giving the evaluation a defensible test case. If time permits, the coordination vocabulary will be extended beyond yield and temporary-wait. All tasks are individual work.

| # | Task | Dependency | Expected deliverable | Target |
|---|------|------------|----------------------|--------|
| 1 | Harden M5 command lifecycle (no expiry mid-manoeuvre) | — | Commands survive an active robot | 1–2 Jul |
| 2 | Fix safety timing (sim-time, monotonic watchdogs, holds) | 1 | Stable safety behaviour under load | 3 Jul |
| 3 | Raise and align safety minimum distance | 2 | Consistent 0.45 m margin | 3 Jul |
| 4 | Author a narrow, credible corridor scenario | — | Repeatable natural deadlock | 4 Jul |
| 5 | Verify a full closed-loop resolution on a natural deadlock | 1–4 | Recorded end-to-end run | 4–5 Jul |

**Remarks.** The main lesson is that safety and coordination logic interact in non-obvious ways; the freezing-on-backup bug was a coordination failure caused entirely by a safety feature working as designed. One request for supervisory input: guidance on the safety minimum-distance value appropriate for 0.22 m/s TurtleBot3 robots in constrained aisles, since it trades off directly against the ability to resolve tight deadlocks.

## VII. References

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online motion planning for connected multi-robot systems using vision language models as high-level planners. *Proceedings of Machine Learning Research*, 1–21. https://mit-realm.github.io/VLM-gcbfplus-website/

Trautman, P., & Krause, A. (2010). Unfreezing the robot: Navigation in dense, interacting crowds. *2010 IEEE/RSJ International Conference on Intelligent Robots and Systems*, 797–803.

van den Berg, J., Guy, S. J., Lin, M., & Manocha, D. (2011). Reciprocal n-body collision avoidance. In C. Pradalier, R. Siegwart, & G. Hirzinger (Eds.), *Robotics research*. Springer.

Open Robotics. (2026). *Nav2 documentation (ROS 2 Jazzy)*. https://docs.nav2.org/

NVIDIA Corporation. (2026). *NVIDIA Isaac Sim 6.0 documentation: RTX lidar and ROS 2 bridge*. https://docs.isaacsim.omniverse.nvidia.com/
