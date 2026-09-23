# Weekly Progress Report — Week 1

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 03–09 June 2026 · **Report date:** 09 June 2026

> This is an individual capstone project. Contributions are therefore attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 1 was dedicated to project initialization: converting the approved research proposal into an implementable engineering plan and a working code base. The proposal's pipeline (Camera → Perception → VLM → RAG → ROS2 → Robots) was decomposed into six independently developable modules with explicit data contracts, and that decomposition was turned into an eight-milestone semester roadmap in which every milestone carries falsifiable acceptance criteria. The repository was then initialized with a ROS2 workspace, a non-ROS Python reasoning package, and a test tree. With the planning layer fixed, implementation began with Module 1 (Perception and Robot ID Tracking), which was completed end-to-end and unit-tested, because it produces the robot-state and annotated-frame inputs on which every downstream module depends. Beyond the original plan, a written engineering-standards document was added to keep type hints, data contracts, module boundaries, and testing conventions consistent across the whole semester. Next week will focus on building the simulation environment so that perception has a real frame source, and on specifying the VLM reasoning module.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | Module decomposition of the proposal | System architecture | `docs/modules.md` — six modules (M1 Perception, M2 VLM, M3 RAG, M4 Execution, M5 Orchestrator, M6 Simulation) plus shared schemas and config, each with inputs, outputs, dependencies, and a recommended build order |
| 2 | Milestone roadmap | Project management | `docs/project_plan.md` — 8 milestones with deliverables and acceptance criteria, a risk register, and minimum/target/stretch outcomes |
| 3 | Repository and ROS2 scaffold | Infrastructure | Git repository on `main`; `ros2_ws/src/` with `swarm_interfaces`, `swarm_perception`, `swarm_orchestrator`, `swarm_simulation`; `reasoning/`, `tests/`, `benchmarks/`, `config/`, `data/` |
| 4 | Engineering standards document | Infrastructure | `CLAUDE.md` — type-hint, Pydantic, docstring, module-boundary, error-handling, and testing rules applied to all subsequent commits |
| 5 | Detailed specifications for M1 and M2 | Specification | `docs/specs/module1_perception.md`, `docs/specs/module2_vlm_reasoning.md`, written *before* implementation and used as the acceptance reference |
| 6 | **M1 Perception implemented end-to-end** | Perception | Frame-source abstraction, calibration loading, ArUco `DICT_4X4_50` detection, pixel→world homography, robot state estimation with filtered velocity and MOVING/SLOW/STOPPED/STALE classification, Set-of-Mark scene annotation, and a ROS2 `PerceptionNode` |
| 7 | M1 unit test suite | Perception | ~70 unit tests covering geometry, detection, state estimation, schema validation, and late-frame suppression |
| 8 | Operator guide for M1 | Documentation | `docs/guides/run_m1_perception.md` and a run script |

The week's central decision was to plan before coding. Rather than implementing against the proposal directly, the proposal was first decomposed so that a delay in any one module would not block the others, and each milestone was given measurable acceptance criteria instead of a vague goal. Implementation then started at M1, since perception is the upstream dependency of the entire pipeline. M1 was deliberately structured as a set of pure, individually testable functions — geometry, detection, state estimation, annotation — with the ROS2 node reduced to a thin adapter around them. This structure means the perception logic can be validated on a development machine without a ROS2 installation, which matters because ROS2 Jazzy is not available locally. Two invariants were fixed in code and tests this week: every robot timestamp must not exceed its scene timestamp, and out-of-order frames are suppressed and reported in diagnostics rather than silently dropped.

## III. In-Progress / Ongoing Tasks

- **Simulation environment (M6, Milestone 2) — design stage, ~10%.** The module decomposition specifies an Isaac Sim warehouse with 1.2 m aisles, a four-way intersection, TurtleBot3 Burger robots, and a fixed overhead RGB camera, but no scene-authoring code exists yet. *Next action:* write the detailed M6 specification and begin the scene builder. *Target:* Week 2.
- **M1 accuracy verification — blocked on the item above.** M1 is unit-tested against synthetic input, but the Milestone 3 acceptance criterion — reported positions within tolerance of simulator ground truth — cannot be evaluated until a simulated camera exists. Camera calibration is also still a placeholder file rather than a derived artifact.
- **ROS2 build verification (Milestone 1) — not yet possible, ~30%.** Packages and manifests are written, but `colcon build` has not been run because ROS2 Jazzy is absent from the development machine. *Next action:* prepare a containerized ROS2 Jazzy environment. *Target:* Weeks 2–3.
- **M2 VLM reasoning — specified, not implemented.** The specification defines the prompt builder, a model-agnostic backend interface, and the output parser with its congestion-type and strategy enumerations. Implementation is scheduled once a frame source exists. Legacy backend stubs were removed this week to prevent them being mistaken for working code.
- **M3–M5 — scaffold only.** These require detailed specifications before implementation and are scheduled for later milestones.

## IV. Outcomes & Achievements

The project now has an executable, tested code base rather than a proposal document. In 5 commits the repository grew to 65 Python modules with roughly 70 dedicated unit tests, all covering Module 1. Milestone 3 (Perception and Tracking) is implemented and unit-verified, pending only in-simulator accuracy validation — ahead of the roadmap, which sequences it third. Two planning artifacts were produced that will govern the remainder of the semester: a module decomposition that makes the modules independently replaceable, and a milestone plan whose acceptance criteria can be checked rather than argued. A concrete early benefit of specification-first development was observed: writing the M1 and M2 specifications surfaced several interface mismatches — notably the ownership of task and status fields — on paper rather than in code, resolved by the rule that the orchestrator owns the task registry while motion status is always derived locally by perception.

## V. Challenges, Risks & Mitigation

- **ROS2 Jazzy unavailable on the development machine.** *Impact:* the Milestone 1 build criterion is unverified and integration defects may accumulate. *Mitigation:* ROS2-specific code is confined to thin node adapters over pure functions that are testable offline; a containerized ROS2 environment will become the canonical execution target.
- **No frame source yet.** *Impact:* perception accuracy cannot be measured. *Mitigation:* the `FrameSource` abstraction accepts simulator, video, or hardware inputs interchangeably, so no perception code will need rewriting once the simulator is ready.
- **Uncertainty over VLM availability and cost.** *Impact:* could block the core contribution. *Mitigation:* the specification keeps the backend model-agnostic behind one interface, so a mock backend can be used until a runtime is chosen.

## VI. Plan for Next Week

Week 2 will build the simulation environment that Week 1's perception module requires. The priority is a warehouse scene generated from declarative configuration rather than hand-built in a GUI, so that congestion scenarios are deterministic and repeatable — a precondition for the quantitative evaluation. In parallel, the overhead camera will be calibrated so that perception can consume simulated frames, and implementation of the VLM reasoning module will begin against a mock backend, allowing the reasoning pipeline to be developed before a live simulator is available. All tasks are individual work.

| # | Task | Expected deliverable | Target |
|---|------|----------------------|--------|
| 1 | Write the detailed M6 simulation specification | Reviewed spec covering scene, scenarios, and ROS2 interfaces | 10 Jun |
| 2 | Implement warehouse and scenario scene authoring | USD builders driven by YAML scenario configs | 10–11 Jun |
| 3 | Import TurtleBot3 robots and wire ROS2 publishing | Physics-ready robots publishing camera, odometry, and TF | 11–12 Jun |
| 4 | Derive overhead camera calibration | Exported `calibration.yaml` verified through the M1 pipeline | 11–12 Jun |
| 5 | Implement M2 VLM reasoning against a mock backend | Prompt builder, backend interface, validated output parser | 12–15 Jun |

**Remarks.** Specification-first development is proving worthwhile and will be continued for M3–M6. One request for supervisory input: guidance on the acceptable position-error tolerance for perception relative to simulator ground truth, since that threshold determines whether ArUco-based tracking alone is sufficient.

## VII. References

Asadi, M., Nowé, A., & Ghofrani, J. (2025). Congestion-aware multi-agent path planning for pick-up and delivery tasks. *Proceedings of the Genetic and Evolutionary Computation Conference*, 1523–1531. https://doi.org/10.1145/3712256.3726339

Brambilla, M., Ferrante, E., Birattari, M., & Dorigo, M. (2013). Swarm robotics: A review from the swarm engineering perspective. *Swarm Intelligence, 7*, 1–41. https://doi.org/10.1007/s11721-012-0075-2

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online motion planning for connected multi-robot systems using vision language models as high-level planners. *Proceedings of Machine Learning Research*, 1–21. https://mit-realm.github.io/VLM-gcbfplus-website/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2021). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. https://arxiv.org/abs/2005.11401

Wurman, P. R., D'Andrea, R., & Mountz, M. (2008). Coordinating hundreds of cooperative, autonomous vehicles in warehouses. *AI Magazine, 29*(1), 9. https://doi.org/10.1609/aimag.v29i1.2082

Yang, J., Zhang, H., Li, F., Zou, X., Li, C., & Gao, J. (2023). *Set-of-Mark prompting unleashes extraordinary visual grounding in GPT-4V*. https://arxiv.org/abs/2310.11441

Bradski, G., & OpenCV contributors. (2026). *OpenCV ArUco marker detection documentation* (Version 4.x). https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html

Open Robotics. (2026). *ROS 2 Jazzy Jalisco documentation*. https://docs.ros.org/en/jazzy/
