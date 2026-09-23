# Weekly Progress Report — Week 2

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 10–16 June 2026 · **Report date:** 16 June 2026

> This is an individual capstone project. Contributions are therefore attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 2 delivered the two prerequisites identified at the end of Week 1: a simulation substrate for the perception module, and the semantic reasoning layer itself. The Isaac Sim scene-authoring pipeline (Module 6) was implemented so that warehouse scenes and congestion scenarios are generated from declarative YAML rather than hand-built in a GUI, guaranteeing the deterministic, repeatable experiments the evaluation requires. The overhead camera was then calibrated analytically from its configured pose and optics, closing the interface between simulation and perception without a physical checkerboard procedure. With the input path defined, Module 2 (VLM Semantic Reasoning) and Module 5 (Orchestrator) were implemented against mock and local backends. Beyond the original plan, a locally hosted `llama.cpp` vision-server toolchain was built so that reasoning experiments do not depend on a paid API, two hosted VLM backends were added behind the same interface, and Windows PowerShell launch scripts were written so the Isaac Sim workstation can run the same repository as the development machine. Next week shifts from module implementation to live integration: launching the generated scene in Isaac Sim and verifying perception against simulator ground truth.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | M6 simulation specification | Specification | `docs/specs/module6_simulation.md` — scene, scenarios, ROS2 interfaces, and acceptance criteria |
| 2 | **Warehouse and scenario scene authoring** | Simulation | Pydantic configuration models, canonical path resolution, warehouse USD builder, scenario USD builder composing reusable assets by reference |
| 3 | TurtleBot3 import and stage validation | Simulation | URDF import into the physics scene plus programmatic USD stage validation that fails fast on malformed scenes |
| 4 | ROS2 publishing wired via OmniGraph | Simulation | Authored graph nodes publishing camera images, odometry, TF, and clock; ROS2 launch file and standalone runner |
| 5 | Canonical scenario definitions | Simulation | YAML-as-source-of-truth configs for head-on deadlock, intersection bottleneck, and dynamic anomaly, plus a timed obstacle-event scheduler and a conflict oracle for validation-only ground truth |
| 6 | **Overhead camera calibrated analytically** | Perception / Simulation | Intrinsics derived from `CameraConfig`, pixel-to-world homography derived from camera pose, `calibration.yaml` exported and verified through the full M1 `process_frame` pipeline (merged as PR #1) |
| 7 | **M2 VLM reasoning implemented** | Semantic reasoning | Deterministic prompt builder, `VLMBackend` protocol, tolerant JSON parser with enum and de-duplication validators, referential-integrity check on `involved_robots`, bounded retry/re-ask policy, `Reasoner.run` orchestrator with JSONL trace logging, deterministic mock backend |
| 8 | **M5 Orchestrator implemented** | Orchestration | Progress-based congestion detector, task registry with coordination overrides, command and cooldown trackers, state machine, reasoning-pipeline adapter, and a configurable ROS2 node with launch file |
| 9 | Local `llama.cpp` vision server *(beyond plan)* | Semantic reasoning | Apple-Silicon launcher, health-check command, portable model paths, operator guide |
| 10 | OpenAI and Anthropic backends *(beyond plan)* | Semantic reasoning | Two hosted backends added behind the existing protocol with no change to prompt building, parsing, or retry logic |
| 11 | Windows launch scripts and integration guides | Infrastructure | PowerShell scripts and guides for running Isaac Sim with M1 on the simulation workstation |

The week's organizing principle was that the evaluation must be reproducible, which dictated the design of the simulation layer. Scenes are therefore *generated* from configuration: a scenario is defined by one YAML file describing robot start poses, goals, obstacles, and timed events, from which the builder composes a USD stage referencing shared warehouse and robot assets. Reproducing an experiment consequently requires distributing a text file rather than a binary scene. The reasoning layer was built on the complementary principle that no unvalidated model output may reach the robots: every VLM response is parsed into a Pydantic schema, checked for valid congestion-type and strategy values, and verified to reference only robot identifiers actually present in the observed scene, with failures returning a null decision after bounded retries rather than propagating downstream. Because M2 and M5 were developed against a deterministic mock backend, both modules could be completed and tested before a live simulator existed.

## III. In-Progress / Ongoing Tasks

The distinction between what was built and what has been observed is important. **This week produced scene-authoring and scenario-generation code together with its offline test suite; it is not yet a running multi-robot simulation.** The system can compose a valid USD warehouse stage and validate it programmatically, but the runtime behaviour has not been observed.

- **Live Isaac Sim execution of the generated scene (M6.1) — ~70%.** Builders, URDF import, OmniGraph wiring, and validation are implemented and unit-tested; what remains is launching the composed stage in Isaac Sim 6.0 on the Windows workstation and confirming that the camera, odometry, TF, and clock topics publish at the expected rates. *Next action:* run the standalone runner and capture a validation log. *Target:* Week 3.
- **Perception accuracy against ground truth (Milestone 3 acceptance) — blocked on the above.** Calibration is verified mathematically, but a gap has been identified: the simulated robots carry no ArUco marker textures, so detection would currently return nothing. *Next action:* generate `DICT_4X4_50` textures and author them onto each robot in USD. *Target:* Week 3.
- **Nav2 baseline navigation (Milestone 2) — ~20%.** Launch topology and robot namespacing are designed, but Nav2 has not been brought up and ROS2 Jazzy remains absent from the development machine, so all ROS2 code is still exercised only through mocks. *Next action:* stand up a containerized ROS2 Jazzy environment. *Target:* Weeks 3–4.
- **M3 RAG action grounding — specification stage.** The knowledge base of coordination templates, the embedding and vector-store flow, and the grounding chain are designed but not specified in detail; M2 currently hands its decision to a placeholder grounding step. *Target:* Weeks 4–5.
- **M4 ROS2 execution and safety — scaffold only,** dependent on M3 output and the Nav2 baseline.
- **VLM input-encoding ablation — design complete, implementation pending.** A design document examines whether the VLM should receive the annotated image, the textual state list, or both; this feeds the evaluation but is not on the critical path.

## IV. Outcomes & Achievements

The project now covers four of six modules in code. In 84 commits this week the repository reached 115 Python modules, and the automated test suite grew from roughly 70 test functions covering perception alone to approximately 290 spanning five modules (M1 perception, M2 reasoning, M5 orchestration, M6 simulation configuration and validation, and the server tooling). Two feature branches were developed and merged through pull requests, establishing a review discipline for the remainder of the project. Milestone 4 (Orchestrator and Shared Contracts) is implemented, including the congestion trigger policy and the pending/active/completed/failed/timed-out command lifecycle. Milestone 5 (VLM Reasoning Integration) exceeds its stated acceptance criterion of "at least one working or mockable backend": four are supported behind one interface. That result also constitutes early evidence for a central claim of the proposal — that the pipeline is genuinely modular. Adding two hosted backends required no change whatsoever to prompt construction, output parsing, retry policy, or decision validation, indicating that the module boundaries are drawn where the proposal assumes they are.

## V. Challenges, Risks & Mitigation

- **Isaac Sim 6.0 API drift.** The URDF importer used to bring TurtleBot3 into the scene had changed relative to publicly available tutorials, and the import failed. *Impact:* without robot import there is no simulation at all. *Mitigation:* corrected against the current official API, and a standing rule was adopted requiring version-sensitive external APIs to be verified against primary documentation before implementation.
- **ROS2 Jazzy still unavailable locally.** *Impact:* integration defects may accumulate undetected. *Mitigation:* ROS2 logic remains confined to thin node adapters over offline-testable pure functions; a containerized environment becomes the canonical target in Week 3.
- **Dependence on external VLM services.** *Impact:* experiments that rely on a paid or rate-limited API are costly and hard to reproduce at evaluation scale. *Mitigation:* the local `llama.cpp` vision-server toolchain was built ahead of schedule, and the backend protocol allows the same experiment to be re-run locally or hosted without code changes.
- **Breadth ahead of depth.** Four modules exist but none has run in a live loop. *Impact:* a broad but never-integrated system would produce no evaluable results. *Mitigation:* Weeks 3–4 are reserved for integration rather than new module development, prioritizing one complete congestion scenario over partial coverage of all three.

## VI. Plan for Next Week

Week 3 converts implemented code into observed behaviour. The generated warehouse scene will be launched inside Isaac Sim and its ROS2 interfaces verified; ArUco markers will be attached to the simulated robots so perception has something to detect; and perception accuracy will then be measured against simulator ground truth, satisfying the outstanding Milestone 3 criterion. In parallel, a containerized ROS2 Jazzy environment will be prepared so Nav2 can drive at least two robots to navigation goals, closing Milestones 1 and 2. Together these steps establish a verified path from simulated camera pixels to world-frame robot states — the precondition for triggering the reasoning layer on a real scene rather than on mock input. Specification of Module 3 begins at the end of the week. All tasks are individual work.

| # | Task | Dependency | Expected deliverable | Target |
|---|------|------------|----------------------|--------|
| 1 | Generate `DICT_4X4_50` textures and author markers per robot | — | Marker generator, committed textures, per-robot validation | 17–18 Jun |
| 2 | Launch the composed scene in Isaac Sim 6.0 | 1 | Validation log confirming the stage loads and physics runs | 18 Jun |
| 3 | Verify ROS2 topics publish at expected rates | 2 | Topic-rate report; QoS aligned with M1 | 18–19 Jun |
| 4 | Run M1 on live frames; measure position error vs. ground truth | 1–3 | Milestone 3 acceptance evidence | 19–20 Jun |
| 5 | Containerized ROS2 Jazzy environment; verify `colcon build` | — | Milestone 1 acceptance evidence | 19–20 Jun |
| 6 | Bring up Nav2 and drive two robots to goals | 5 | Milestone 2 acceptance evidence | 20–22 Jun |
| 7 | Draft the M3 RAG grounding specification | — | Reviewed specification | 21–22 Jun |

**Remarks.** Two lessons carry forward. Building the local model server before it was strictly needed removed a dependency that would otherwise have constrained the evaluation budget. Conversely, the URDF import failure confirmed that tutorial material lags rapidly evolving simulator APIs, so primary documentation must be consulted for version-sensitive interfaces. One request for supervisory input: whether the evaluation should prioritize breadth (all three congestion scenarios at a shallow level) or depth (one scenario compared thoroughly against all baselines), as this shapes the Week 4–8 schedule.

## VII. References

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2021). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. https://arxiv.org/abs/2005.11401

Lin, J., Yin, H., Ping, W., Lu, Y., Molchanov, P., Tao, A., Mao, H., Kautz, J., Shoeybi, M., & Han, S. (2024). *VILA: On pre-training for visual language models*. https://arxiv.org/abs/2312.07533

Yang, J., Zhang, H., Li, F., Zou, X., Li, C., & Gao, J. (2023). *Set-of-Mark prompting unleashes extraordinary visual grounding in GPT-4V*. https://arxiv.org/abs/2310.11441

Zafar, M., Khan, R. A., Batool, F., Yaqoot, Y., Guo, Z., Litvinov, M., Fedoseev, A., & Tsetserukou, D. (2025). *SwarmVLM: VLM-guided impedance control for autonomous navigation of heterogeneous robots in dynamic warehousing*. https://arxiv.org/abs/2508.07814

Gerganov, G., & llama.cpp contributors. (2026). *llama.cpp — llama-server multimodal documentation*. https://github.com/ggml-org/llama.cpp

NVIDIA Corporation. (2026). *NVIDIA Isaac Sim 6.0 documentation: URDF importer and ROS 2 bridge (OmniGraph)*. https://docs.isaacsim.omniverse.nvidia.com/

Pixar Animation Studios. (2026). *OpenUSD documentation*. https://openusd.org/release/index.html

Open Robotics. (2026). *ROS 2 Jazzy Jalisco documentation*. https://docs.ros.org/en/jazzy/
