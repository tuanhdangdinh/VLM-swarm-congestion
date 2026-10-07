# Weekly Progress Report — Week 5

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 01–07 July 2026 · **Report date:** 07 July 2026

> This is an individual capstone project. Contributions are attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 5 made the closed loop reliable and then stepped back to design the experiment that will justify it. The first half of the week hardened the detect→decide→ground→act→resolve loop against a naturally emerging deadlock: the command lifecycle was fixed so a decision is not discarded while a robot is mid-manoeuvre, the safety monitor was moved onto simulation time with monotonic watchdogs and a raised 0.45 m margin, and a rendering fix enabled the lidar to perceive moving robots. The yield strategy was reworked into a genuine pull-off-and-escort manoeuvre, and a narrow 0.55 m corridor scenario was authored so that congestion is credible and repeatable rather than incidental. The second half of the week was a design pivot: recognising that a working demonstration is not yet a defensible research result, a controlled experiment was designed around the project's research question, iterated through seven revisions incorporating external review, culminating in a two-arm experimental design. Next week will consolidate this design into a preregistration and begin executing the controlled runs.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | Verified closed-loop pipeline snapshot | Integration | A recorded, reproducible state of the full pipeline resolving a deadlock, used as the baseline for subsequent fixes |
| 2 | **M5 command-lifecycle hardening** | Orchestration | Commands are no longer expired while a robot is ACTIVE; commands for a robot already mid-manoeuvre are rejected; linked waits are released when a yield reaches a terminal state |
| 3 | **Safety monitor hardening** | Safety | Runs on sim time; backup deadlines use OS-monotonic time; a watchdog covers hung Nav2 legs; safety holds publish an unconditional 1 s heartbeat so the retry loop backs off; minimum distance raised to 0.45 m |
| 4 | Lidar sees moving robots | Simulation | RTX raytracing motion BVH enabled via the required three-setting kit argument, so costmaps reflect other robots in motion |
| 5 | **Yield reworked as pull-off and escort** | Execution | The yielder performs a raw-`cmd_vel` sidestep and parks clear of the aisle; the passing robot is escorted through the gap during the hold; the hold ends from the passer's odometry once it has cleared |
| 6 | Narrow corridor congestion scenario | Simulation | A 0.55 m × 2.0 m corridor with robots spawned outside and entering aligned, producing a credible, repeatable natural deadlock |
| 7 | Nav2 tuning for tight transit | Execution | Softened local inflation and progress checker, DWB timing, and forward-stop polygon shrunk to fit the corridor |
| 8 | **Controlled experiment design** | Research design | A four-pillar spatial-congestion-resolution design iterated through seven revisions under external review, arriving at a controlled two-arm experiment framed directly around the research question |

The week had two distinct halves. The first was engineering consolidation: the individual strategies from Week 4 worked in isolation but did not compose into a dependable resolution, and the failures were almost all in timing and lifecycle rather than in logic — commands expiring too early, safety holds fighting the retry loop, and a lidar that could not see moving robots because motion BVH was off. Fixing these turned an occasional success into a repeatable one, and the yield manoeuvre was rebuilt so that yielding actually vacates the aisle and actively lets the other robot through. The second half was a deliberate shift from building to evaluating: a demonstration that the loop resolves one deadlock does not establish that the VLM+RAG approach outperforms alternatives, so the remainder of the week was spent designing a controlled experiment, refined repeatedly against external feedback into a two-arm comparison.

## III. In-Progress / Ongoing Tasks

- **Experiment preregistration — design frozen at rev 7, not yet preregistered.** The two-arm design is settled, but the preregistration cannot be finalised until the exact model identifiers and statistical plan are locked. *Next action:* write the statistical plan and freeze model IDs. *Target:* Week 6.
- **Full experimental execution — not started.** No controlled runs have been collected; the week produced the design, not the data. *Target:* Weeks 6–7.
- **Coordination vocabulary — partial.** Yield and temporary-wait are robust; reroute, reverse, and convoy are still not executable in M4. Whether the experiment requires them depends on the frozen scenario set. *Target:* to be decided with the preregistration.
- **M3 RAG action grounding — still specification stage.** Grounding remains a placeholder; closing and stabilising the physical loop took priority. This is now the largest unimplemented module.
- **Nav2 recovery loop on pull-off — open item.** The yielder occasionally enters a Nav2 recovery cycle after the sidestep; a targeted fix is pending.

## IV. Outcomes & Achievements

The headline result is a repeatable closed-loop deadlock resolution: on the narrow corridor scenario, a naturally emerging head-on deadlock is now detected, reasoned about by the VLM, and resolved by a yield-and-escort manoeuvre, reliably rather than occasionally. This is the first time the complete architecture has functioned as a coordination system on a credible congestion case. In roughly 46 commits — the most active week so far — the test suite grew to about 500 test functions. The second achievement is methodological: the project now has a controlled two-arm experimental design, hardened through seven revisions of external review, which converts an engineering demonstration into a testable research claim. The narrow-corridor scenario is itself a durable asset, since a repeatable natural deadlock is a prerequisite for any statistically meaningful comparison.

## V. Challenges, Risks & Mitigation

- **Timing bugs masquerading as logic bugs.** Most closed-loop failures traced to sim-time vs. wall-clock confusion, premature command expiry, and safety holds contending with the retry loop. *Impact:* intermittent, hard-to-reproduce resolution failures. *Mitigation:* safety deadlines were moved to OS-monotonic time, command expiry was made lifecycle-aware, and holds were turned into a steady heartbeat.
- **Lidar blind to moving robots.** Motion BVH was disabled, so costmaps did not register other robots in motion, and post-init mutation of the setting crashed the renderer. *Impact:* unsafe planning during the manoeuvre. *Mitigation:* the full three-setting kit-argument combination is now passed at launch.
- **Demonstration is not evidence.** A single successful run does not support the proposal's claims. *Impact:* the core research contribution would be unsubstantiated. *Mitigation:* the week's design work established a controlled comparison; the risk now shifts to executing it within the schedule.

## VI. Plan for Next Week

Week 6 moves from design to measurement. The immediate priority is to finalise the preregistration: lock the exact VLM model identifiers, write the statistical plan, and specify the second experimental arm and its metrics. In parallel, the open Nav2 recovery-loop item on the yield pull-off will be closed so that resolution is robust across repeated trials, since the experiment depends on it. Once the preregistration is frozen, the first batch of controlled runs will be collected on the narrow-corridor scenario. All tasks are individual work.

| # | Task | Dependency | Expected deliverable | Target |
|---|------|------------|----------------------|--------|
| 1 | Freeze VLM model identifiers | — | Locked model list for preregistration | 8 Jul |
| 2 | Write the statistical plan and second-arm spec | 1 | Preregistration-ready design | 8–10 Jul |
| 3 | Close the Nav2 recovery-loop item on yield pull-off | — | Robust repeated resolution | 9–10 Jul |
| 4 | Finalise and preregister the two-arm experiment | 1–2 | Frozen preregistration document | 11 Jul |
| 5 | Collect first batch of controlled runs | 3–4 | Initial results on the corridor scenario | 11–13 Jul |

**Remarks.** The clearest lesson of the week is that stabilising a distributed real-time loop is dominated by timing and lifecycle correctness, not by the coordination logic itself. A second lesson is the value of external review on the experimental design: seven revisions materially sharpened the research question before any data was collected, which is far cheaper than discovering design flaws after the runs. One request for supervisory input: agreement on the exact set of baselines and metrics for the second experimental arm, as this determines the scope of the remaining weeks.

## VII. References

Asadi, M., Nowé, A., & Ghofrani, J. (2025). Congestion-aware multi-agent path planning for pick-up and delivery tasks. *Proceedings of the Genetic and Evolutionary Computation Conference*, 1523–1531. https://doi.org/10.1145/3712256.3726339

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online motion planning for connected multi-robot systems using vision language models as high-level planners. *Proceedings of Machine Learning Research*, 1–21. https://mit-realm.github.io/VLM-gcbfplus-website/

Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015). Conflict-based search for optimal multi-agent pathfinding. *Artificial Intelligence, 219*, 40–66. https://doi.org/10.1016/j.artint.2014.11.006

van den Berg, J., Guy, S. J., Lin, M., & Manocha, D. (2011). Reciprocal n-body collision avoidance. In C. Pradalier, R. Siegwart, & G. Hirzinger (Eds.), *Robotics research*. Springer.

Open Robotics. (2026). *Nav2 documentation (ROS 2 Jazzy)*. https://docs.nav2.org/

NVIDIA Corporation. (2026). *NVIDIA Isaac Sim 6.0 documentation: RTX lidar motion BVH and ROS 2 bridge*. https://docs.isaacsim.omniverse.nvidia.com/
