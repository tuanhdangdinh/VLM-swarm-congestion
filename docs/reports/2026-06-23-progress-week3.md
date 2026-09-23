# Weekly Progress Report — Week 3

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 17–23 June 2026 · **Report date:** 23 June 2026

> This is an individual capstone project. Contributions are attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 3 turned implemented code into observed behaviour. The two blockers carried over from Week 2 were cleared: ArUco markers were generated and authored onto the simulated robots, and the M6→M1→M5→M2 pipeline was executed end-to-end on a cloud GPU host with a real VLM backend rather than a mock. In parallel, work began on Module 4 (ROS2 Execution and Safety): a phased plan was written and its first phase — the robot drive chain — was completed, so the simulated TurtleBot3 robots now move in response to velocity commands and a head-on deadlock emerges dynamically from their motion instead of being a static spawn. This satisfies the core of Milestone 2 (robot movement). The week's main lesson was that the published integration guide, written for a Windows host, did not transfer to the Linux cloud environment used for the billed run; several scripts and transport assumptions had to be adapted. Next week will bring up the Nav2 navigation stack so robots plan paths to goals, and begin the coordination-strategy execution that closes the loop.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | ArUco marker generation and authoring | Perception / Simulation | `DICT_4X4_50` texture generator, committed textures, per-robot marker quad authored in USD with an emissive per-id material, round-trip parity test against the M1 detector, and a pre-flight marker-id verifier |
| 2 | Marker geometry fixes | Perception | Marker size aligned to the 0.12 m physical size; marker frame raised above the lidar; marker rotated −90° so detected heading matches robot yaw |
| 3 | **First live end-to-end run (M6→M1→M5→M2)** | Integration | Pipeline executed on a GCP GPU VM (Isaac Sim 6.0 source build) with the real OpenAI backend producing an actual congestion decision; documented in `docs/reports/2026-06-18-m6-m2-integration-gcp-run.md` |
| 4 | Anthropic (Claude) VLM backend | Semantic reasoning | Third hosted backend added behind the existing `VLMBackend` protocol with no change to prompt building or parsing |
| 5 | Module 4 specification and phased plan | Specification | `docs/specs/module4/` — execution and safety spec with a phased Nav2 rollout |
| 6 | **M4 Phase 1 — robot drive chain** | Execution / Simulation | Wheel-velocity drive authoring, contact friction, OmniGraph drive chain (`cmd_vel` → differential controller → articulation), dynamic TF tree, a 0.5 s command watchdog, and a headless Fabric-sync fix so world poses update each step; verified by a recorded MP4 of M1 tracking both robots into deadlock |

The week's organizing goal was to prove the pipeline on real data rather than mocks. Attaching markers was the precondition — without them the perception module has nothing to detect — and several small but blocking geometry errors (marker size, height above the lidar, and a heading offset) surfaced only once real frames were processed. The first billed cloud run then exercised the full observe-and-reason path with a live VLM. Separately, Module 4 Phase 1 addressed the other half of a real scenario: making robots move. The drive chain was built so that a deadlock is produced by the robots' own motion, which is what a coordination experiment requires, rather than by placing robots in a pre-arranged jam.

## III. In-Progress / Ongoing Tasks

- **Nav2 navigation stack (M4 Phase 2, Milestone 2 completion) — starting.** Robots can be driven by raw velocity commands, but they do not yet plan paths to navigation goals. Phase 2 will install and configure Nav2, author an occupancy-grid map, and provide per-robot bringup. *Target:* Week 4.
- **Coordination-strategy execution (M4 Phase 3) — not started.** The orchestrator can decide on a strategy, but M4 does not yet carry out yield, wait, reroute, or reverse. This is the step that closes the loop. *Target:* Weeks 4–5.
- **Reproducible integration environment — partially solved.** The cloud run succeeded, but only after ad-hoc adaptations; the guide still assumes a host ROS2 install that the Linux VM cannot provide. *Next action:* record a Linux-native runbook. *Target:* Week 4.
- **M3 RAG action grounding — still specification stage.** M2 continues to hand its decision to a placeholder grounding step.

## IV. Outcomes & Achievements

The project reached its first live, end-to-end demonstration: a simulated warehouse scene was observed by the perception module, tracked by identity, and analysed by a real VLM that returned a congestion decision — the observe-and-reason half of the architecture, running on genuine simulator output. Milestone 2 (robot movement) is substantially met, as both robots now drive and produce an emergent deadlock captured on video. In roughly 20 commits the test suite grew to about 350 test functions across the module set. A notable qualitative result is that the VLM backend abstraction again held: a third provider was added this week with no change to the surrounding pipeline. The cloud integration run also produced its own deliverable — a written account of exactly where the environment assumptions break on Linux — which will save time on every subsequent run.

## V. Challenges, Risks & Mitigation

- **Integration guide did not transfer to the cloud host.** The guide targets a Windows host with a separate WSL2 ROS2 checkout, whereas the billed run used a single Linux VM whose Ubuntu 22.04 base cannot host system ROS2 Jazzy. *Impact:* blocked the run until worked around. *Mitigation:* Isaac Sim ran with its bundled ROS2 bridge while the ROS2 nodes ran in a `ros:jazzy` container sharing host transport; the working configuration was documented.
- **Robots initially would not translate.** The drive chain output non-zero wheel velocities but the chassis did not move, due to missing wheel contact friction and a headless pose-sync gap. *Impact:* no motion, no dynamic scenario. *Mitigation:* contact friction was configured and a Fabric-sync fix was applied; both are recorded in the Phase 1 completion report.
- **Real-VLM cost.** Billed cloud runs are expensive to repeat. *Mitigation:* the local and mock backends remain the default for development; billed runs are reserved for milestone verification.

## VI. Plan for Next Week

Week 4 completes the navigation layer and begins closing the loop. Nav2 will be installed and configured on the simulation host, a static occupancy-grid map will be authored from the warehouse configuration, and each robot will receive a Nav2 bringup so it can plan paths to goals — the outstanding part of Milestone 2. Once robots navigate autonomously, the first coordination strategies (yield and temporary wait) will be implemented in Module 4 so that an orchestrator decision produces an actual change in robot behaviour. Safety enforcement will be brought up alongside, since autonomous motion makes collision avoidance a live concern. All tasks are individual work.

| # | Task | Dependency | Expected deliverable | Target |
|---|------|------------|----------------------|--------|
| 1 | Install and verify Nav2 (Jazzy) on the simulation host | — | Recorded install verification | 24–25 Jun |
| 2 | Author static occupancy-grid map from warehouse config | — | Map consumed by Nav2 | 25 Jun |
| 3 | Per-robot Nav2 bringup; wire RTX lidar for costmaps | 1–2 | Robots plan paths to goals (Milestone 2 done) | 25–26 Jun |
| 4 | Safety monitor: min-distance and command-timeout fallback | 3 | Safe stop on proximity or hang | 26–28 Jun |
| 5 | Implement yield and temporary-wait strategies | 3–4 | Orchestrator decision changes robot behaviour | 28–30 Jun |

**Remarks.** The billed cloud run confirmed that environment assumptions are as important as code: budgeting time to adapt the runbook is now part of every integration plan. One request for supervisory input: confirmation that a source-built Isaac Sim on a single Linux VM is an acceptable evaluation environment, given that the documented target was a Windows workstation.

## VII. References

Yang, J., Zhang, H., Li, F., Zou, X., Li, C., & Gao, J. (2023). *Set-of-Mark prompting unleashes extraordinary visual grounding in GPT-4V*. https://arxiv.org/abs/2310.11441

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online motion planning for connected multi-robot systems using vision language models as high-level planners. *Proceedings of Machine Learning Research*, 1–21. https://mit-realm.github.io/VLM-gcbfplus-website/

Bradski, G., & OpenCV contributors. (2026). *OpenCV ArUco marker detection documentation* (Version 4.x). https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html

NVIDIA Corporation. (2026). *NVIDIA Isaac Sim 6.0 documentation: ROS 2 bridge and OmniGraph*. https://docs.isaacsim.omniverse.nvidia.com/

Open Robotics. (2026). *Nav2 documentation (ROS 2 Jazzy)*. https://docs.nav2.org/
