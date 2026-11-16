# Classical (Non-LLM) Centralized Multi-Robot Coordination for Congestion/Deadlock in Warehouses, and Classical-vs-LLM Comparisons (through 2026)

Research notes prepared 2026-10-01. Scope: centralized coordination; decentralized methods appear only as contrast or where they are the canonical citation for a mechanism (e.g., deadlock recovery). All claims carry inline sources; weakly sourced items are flagged.

## Key Question 1: Centralized warehouse coordination at scale — what does the central coordinator decide, and at what rate?

### Takeaway
The dominant classical pattern is a central coordinator that allocates space-time resources (path reservations, zones, intersection tiles) while robots execute locally; the canonical modern formulation is lifelong MAPF with windowed replanning (RHCR), where the central solver replans every h timesteps under a ~1 s compute budget for hundreds of agents — i.e., the classical central layer already operates at roughly the 0.5–2 Hz band the thesis assigns to its VLM layer.

### Cited Findings
- **Kiva/Amazon**: Wurman, D'Andrea, Mountz, "Coordinating Hundreds of Cooperative, Autonomous Vehicles in Warehouses," AI Magazine 29(1), 2008. A large installation may require 500+ vehicles; it is described as the first commercially available large-scale autonomous robot system; although the overall system is cooperative, "the Kiva robots are essentially independent" — central software handles resource allocation (which pod/station/path) while each drive unit navigates fiducial-marked grid cells itself — [AI Magazine PDF](https://www.dcsc.tudelft.nl/~sc4081/2018/assign/pap/robert_kiva_paper.pdf); [AAAI copy](https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/download/2082/1981)
- **Lifelong MAPF / RHCR**: Li, Tinka, Kiesel, Durham, Kumar, Koenig, "Lifelong Multi-Agent Path Finding in Large-Scale Warehouses," AAAI 2021, arXiv:2005.07371. RHCR (Rolling-Horizon Collision Resolution) decomposes lifelong MAPF into a sequence of Windowed MAPF instances: collisions are resolved only within a bounded time horizon w, and the central solver **replans paths once every h timesteps** (h user-specified), interleaving planning and execution; scales to 1,000 agents in simulated warehouses, significantly outperforming prior work — [arXiv:2005.07371](https://arxiv.org/abs/2005.07371); [AAAI version](https://ojs.aaai.org/index.php/AAAI/article/view/17344/17151); [code](https://github.com/Jiaoyang-Li/RHCR)
- **Central coordinator compute budget**: GRAND ("Guidance, Rebalancing, and Assignment for Networked" robot fleets, arXiv:2512.03194, 2025) couples a GNN/RL global guidance policy with min-cost-flow rebalancing on the League of Robot Runners (LRR) benchmark, up to 500 agents, improving throughput up to 10% over the 2024 LRR winning scheduler while "keeping per-step latency within a **1-second compute budget**" — i.e., the competitive central-planner cadence for 500-agent warehouses is ~1 Hz — [arXiv PDF](https://www.arxiv.org/pdf/2512.03194)
- **Central reservation at intersections (FCFS/auction family)**: Dresner & Stone's Autonomous Intersection Management (AIM) — a centralized intersection manager divides the junction into a grid of space-time tiles; vehicles request a slot, the manager grants reservations to a non-conflicting subset using a **first-come-first-served (FCFS) policy**; FCFS shown to improve over optimized signals — "A Multiagent Approach to Autonomous Intersection Management," JAIR 31, 2008 — [JAIR PDF](https://www.cs.utexas.edu/~aim/papers/JAIR08-dresner.pdf); earlier AAMAS 2004 version — [Stone's page](https://www.cs.utexas.edu/~pstone/Papers/bib2html/b2hd-AAMAS04.html)
- **Fleet-management design-space study**: "Lifelong Scalable Multi-Agent Realistic Testbed and A Comprehensive Study on Design Choices in Lifelong AGV Fleet Management Systems" (arXiv:2602.15721, 2026) — a systematic study of central fleet-management design choices (planner, executor, task assigner) under realistic AGV kinematics — [arXiv PDF](https://arxiv.org/pdf/2602.15721)
- **Amazon's own learned direction (contrast)**: "DeepFleet: Multi-Agent Foundation Models for Mobile Robots" (arXiv:2508.08574, 2025) — Amazon trains fleet-scale foundation models for mobile-robot coordination, i.e., industry itself is moving from hand-built central allocators toward learned central predictors/coordinators — [arXiv HTML](https://arxiv.org/html/2508.08574v1)

### Inferences
- The classical central coordinator decides: (a) task/pod assignment, (b) space-time path reservations or zone grants, (c) priority orderings at conflict points. It does **not** normally issue semantic "maneuver commands" (back up, yield, convoy) — those outcomes emerge implicitly from reservation denial/replanning. This is the cleanest conceptual contrast for the thesis: the VLM arm issues explicit recovery maneuvers; the classical family issues space-time allocations.
- RHCR's h-timestep replanning at ~1 s budgets means the thesis's 0.5–2 Hz "slow layer" is not novel as a *rate*; the novelty must rest on *what* the slow layer decides (semantic recovery commands from pixels) rather than how often.

### Gaps
- Exact replanning frequency (in wall-clock Hz) of the production Kiva/Amazon coordinator is not published; Wurman et al. 2008 describe architecture, not rates.

## Key Question 2: Deadlock/congestion-specific central mechanisms — avoidance vs published RECOVERY of already-formed deadlocks

### Takeaway
The AGV literature is overwhelmingly about *avoidance/prevention* (banker's-algorithm variants, zone-control circular-wait checks, Petri nets, time-expanded graphs); published *recovery* procedures for already-formed multi-robot deadlocks exist but are sparse and mostly decentralized or pairwise (Jäger & Nebel 2001; Grover et al. IJRR 2023; A-DRIVE 2022) — a centrally *commanded* recovery from a formed multi-robot scrum, driven by scene-level perception, does not appear as an established classical baseline.

### Cited Findings
**Avoidance/prevention (the dominant classical family):**
- Banaszak & Krogh proposed a centralized deadlock-avoidance algorithm based on a Petri-net model of concurrent job flow and dynamic resource allocation (originally IEEE Trans. Robotics & Automation, 1990) — summarized in [AGV deadlock-handling literature](https://www.mdpi.com/2076-3417/11/14/6494)
- Banker's-algorithm variants: Lawley, Reveliotis, Ferreira, "The Application and Evaluation of Banker's Algorithm for Deadlock-Free Buffer Space Allocation in Flexible Manufacturing Systems," Int. J. Flexible Manufacturing Systems 10:73–100, 1998 — banker's algorithm, dismissed as too conservative for OSes, becomes practical when future resource needs are well-defined by part/vehicle routes — [Springer](https://link.springer.com/article/10.1023/A:1007969601583); Reveliotis's broader deadlock-avoidance theory for sequential resource allocation systems — [Georgia Tech PDF](https://www2.isye.gatech.edu/~spyros/publications/accept-SU-compl.pdf)
- Reveliotis, "Conflict resolution in AGV systems," IIE Transactions 32(7):647–659, 2000 — central conflict resolution for zone-controlled AGVs — [Springer record](https://link.springer.com/article/10.1023/A:1007663100796)
- Zone-control deadlock prediction: when a vehicle requests the next zone, the controller looks ahead for circular waits among guidepath zones and blocks the move if one would form ("Deadlock prediction and avoidance for zone-control AGVS," Yeh & Yeh / related zone-control line) — [ResearchGate record](https://www.researchgate.net/publication/261671114_Deadlock_prediction_and_avoidance_for_zone-control_AGVS)
- Modern industrial-grade central prevention: "Hierarchical Traffic Management of Multi-AGV Systems With Deadlock Prevention Applied to Industrial Environments," IEEE T-ASE 21(3):3155–3169 (published online 2023) — three-layer architecture (topological layer / traffic-sensitive path planning / roadmap-layer coordination) with deadlock prevention via **time-expanded graphs**, explicitly handling real-plant issues (predefined roadmaps, vehicle errors, dynamic obstacles) — [IEEE Xplore](https://ieeexplore.ieee.org/document/10132864/); predecessor without deadlock prevention — [IEEE Xplore 2021](https://ieeexplore.ieee.org/document/9560828)
- "Traffic Management of Multi-AGV Systems by Improved Dynamic Resource Reservation," 2024 — reservation-based central traffic management refinement — [IEEE Xplore](https://ieeexplore.ieee.org/document/10419190/)
- "BDD-Based Deadlock Avoidance for Automated Guided Vehicles in Warehouse Logistics" (case-study paper, 2025/2026) — symbolic (binary decision diagram) central avoidance in warehouse logistics — [ACM/Springer](https://dl.acm.org/doi/10.1007/978-3-032-26204-2_16)
- "AGVs Collision and Deadlock Handling Based on Structural Online Control Policy: A Case Study in a Square Topology," Applied Sciences 11(14):6494, 2021 — taxonomy: deadlock handling = (1) detection & resolution (online detect + recover), (2) prevention, (3) avoidance via online state analysis — [MDPI](https://www.mdpi.com/2076-3417/11/14/6494)

**Recovery of formed deadlocks (the thin literature the thesis sits against):**
- Jäger & Nebel, "Decentralized collision avoidance, deadlock detection, and deadlock resolution for multiple mobile robots," IROS 2001 — generally credited as the first deadlock-*resolution* algorithm for multiple mobile robots: on detected deadlock, robots are asked to plan alternative trajectories until the deadlock breaks (resolution by replanning, not physical retreat) — [paper PDF](https://gki.informatik.uni-freiburg.de/papers/jaeger-nebel-iros01.pdf); [dblp](https://dblp.org/rec/conf/iros/JagerN01.html)
- Grover, Liu, Sycara, "The Before, During, and After of Multi-robot Deadlock," IJRR (published 2023, DOI 10.1177/02783649221074718; arXiv:2206.01781) — analyzes deadlocks that arise under CBF-based collision avoidance, characterizes admissible deadlock configurations geometrically, and gives a **provably correct decentralized deadlock-resolution algorithm** validated on Khepera-IV robots — recovery exists, but decentralized and for point-like holonomic robots — [IJRR](https://dx.doi.org/10.1177/02783649221074718); [arXiv PDF](https://arxiv.org/pdf/2206.01781)
- Related symmetry analysis: "Why Does Symmetry Cause Deadlocks?" IFAC World Congress 2020 — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2405896320334042)
- A-DRIVE: "Autonomous Deadlock Detection and Recovery at Road Intersections for Connected and Automated Vehicles," IEEE Intelligent Vehicles Symposium (IV) 2022 — explicit detection-plus-**recovery** protocol for already-formed deadlocks among CAVs at intersections — [IEEE/ACM DL](https://dl.acm.org/doi/abs/10.1109/IV51971.2022.9827436)
- "Multi-Robot Trajectory Planning with Feasibility Guarantee and Deadlock Resolution: An Obstacle-Dense Environment" (arXiv:2210.04231, RA-L 2023) — optimization-based planner with built-in deadlock resolution in dense environments — [arXiv PDF](https://arxiv.org/pdf/2210.04231)
- Industrial practice (LOW CONFIDENCE — vendor marketing page, not peer-reviewed): warehouse deadlock recovery reportedly uses timeout-based rollback after 10–30 s of no progress, reverse-release of reserved segments, and dispatcher override by mission criticality/battery state — [vendor page](https://www.hycmoop.com/news/robotics-automation/agv-amr/AGV-traffic-control-algorithm-bottlenecks-at-intersections.html). Treat as anecdotal; do not cite in the thesis without a better source.

### Inferences
- The classical field's center of mass is *never letting the scrum form* (banker's/zone/reservation/time-expanded-graph prevention). Once a deadlock has physically formed among free-ranging robots, the published playbook is thin: replan alternatives (Jäger & Nebel), geometric perturbation (Grover et al., decentralized), or V2V-negotiated backup at a structured intersection (A-DRIVE). None of these is a *centralized, perception-driven, commanded* recovery over a Nav2-class stack — this supports the thesis's novelty claim, but the claim should be phrased against this specific recovery literature (especially A-DRIVE and Grover et al.), not against the avoidance literature.
- Industrial systems clearly have recovery procedures (timeouts, dispatcher override) but they are unpublished/proprietary; the thesis can honestly say published recovery baselines are scarce.

### Gaps
- No peer-reviewed source found documenting the exact deadlock-recovery procedures of commercial AMR fleet managers (Amazon, Geek+, Locus); only a vendor page (flagged above).
- Did not locate a classical paper that commands a *multi-robot* (3+) physical untangling maneuver from a central controller — absence of evidence after several searches, noted as such rather than proven absence.

## Key Question 3: Rule-based/heuristic congestion resolvers directly comparable to a simple classical reasoner arm

### Takeaway
The thesis's classical arm (detect head-on/intersection conflict → pick yielder by FCFS/priority → command retreat) has direct ancestors: FCFS reservation granting (AIM), zone-control circular-wait blocking, priority-based yielding, and A-DRIVE's detect-then-back-up protocol — so the classical arm is well-grounded as "representative of the classical family," which strengthens rather than weakens the two-arm design.

### Cited Findings
- FCFS as the canonical priority rule: AIM's centralized manager grants space-time tiles strictly first-come-first-served and this alone beats optimized traffic signals for full-CAV traffic — [Dresner & Stone, JAIR 2008](https://www.cs.utexas.edu/~aim/papers/JAIR08-dresner.pdf)
- Deadlock-handling taxonomy including online detection-and-recovery as a legitimate strategy class, with a structural online control policy case study on a square AGV topology — [Applied Sciences 2021](https://www.mdpi.com/2076-3417/11/14/6494)
- Alternative-trajectory replanning as the resolution rule once deadlock is detected — [Jäger & Nebel IROS 2001](https://gki.informatik.uni-freiburg.de/papers/jaeger-nebel-iros01.pdf)
- Priority/recovery at intersections: A-DRIVE's deadlock detection and recovery protocol for CAVs — [IV 2022](https://dl.acm.org/doi/abs/10.1109/IV51971.2022.9827436)
- Simulation-based what-if deadlock avoidance: banker's-algorithm variants embedded in what-if simulations for bidirectional AGV systems, identifying route segments where deadlocks can occur — ["Simulation-based Deadlock Avoidance and Optimization in Bidirectional AGVS"](https://dl.acm.org/doi/pdf/10.5555/2151054.2151085); also [ASIM simulation-based AGV deadlock study](https://www.asim-gi.org/fileadmin/user_upload_asim/ASIM_Publikationen_OA/AM190/a4705.arep.47_OA.pdf)
- RL-aided sequential optimization for unsignalized robot-traffic intersections (hybrid heuristic/learned central arbiter) — [arXiv:2302.05082](https://arxiv.org/pdf/2302.05082)

### Inferences
- A defensible classical-arm spec, each element citable: conflict detection (circular-wait / mutual-blocking test per zone-control literature), yielder selection (FCFS per AIM, or static priority per AGV zone control), recovery action (retreat/backup per A-DRIVE; alternative-path per Jäger & Nebel). Framing the classical arm as "AIM-style FCFS yielding + A-DRIVE-style backup" makes it a literature-grounded baseline, not a strawman.

### Gaps
- No single published paper found that implements exactly the thesis's classical arm (head-on/intersection classification + FCFS yielder + commanded retreat) as a *centralized* module over Nav2; the arm must be assembled from the cited components.

## Key Question 4: Published head-to-head of LLM/VLM coordination vs classical/rule-based coordination on the same scenarios

### Takeaway
Head-to-heads exist but in adjacent settings: LLMs fail badly against classical solvers on standard MAPF benchmarks (Chen/Koenig/Dilkina 2024); LLM-driven deadlock resolution over learned MAPF policies (LLMDR 2025) and LLM/VLM leader-assignment over GNN controllers (Garg et al. 2024) show foundation models *helping* low-level policies escape deadlocks in grid/point-robot simulation — but no published two-arm comparison of a central VLM congestion resolver vs a rule-based classical reasoner on the same Nav2-driven warehouse scenarios was found.

### Cited Findings
- Chen, Koenig, Dilkina, "Why Solving Multi-agent Path Finding with Large Language Model has not Succeeded Yet," arXiv:2401.03630 (2024) — GPT-4-class LLMs succeed only on empty maps and **fail to plan on the room and maze maps of the standard MAPF benchmark**; argues MAPF uniquely combines coordination + planning, defeating tool-augmented LLM reasoning — [arXiv](https://arxiv.org/abs/2401.03630)
- LLMDR: "LLM-Driven Deadlock Detection and Resolution in Multi-Agent Pathfinding," arXiv:2503.00717 (2025) — uses an LLM to detect and resolve deadlocks arising under learned MAPF policies; the closest published analogue to "LLM as central deadlock referee over a non-LLM execution layer" in grid MAPF — [arXiv PDF](https://arxiv.org/pdf/2503.00717)
- Garg et al., "Foundation Models to the Rescue: Deadlock Resolution in Connected Multi-Robot Systems," arXiv:2404.06413 (2024; earlier title "Large Language Models to the Rescue…") — hierarchical framework: LLM/VLM high-level planner resolves formed deadlocks by **assigning a leader and waypoints**, executed by a GNN-based distributed low-level control policy (GCBF+); systematic prompt-engineering study; this is the paper that most directly overlaps the thesis's "commanded recovery from formed deadlock" claim, though with connected point robots, not warehouse Nav2 fleets — [arXiv PDF](https://arxiv.org/pdf/2404.06413); [Semantic Scholar](https://www.semanticscholar.org/paper/09498b36bb66169f05e6be614a5493576123b6ed); project page with VLM online-planning extension — [MIT REALM](https://mit-realm.github.io/VLM-gcbfplus-website/files/Online_planning_using_VLMs.pdf)
- GameChat: "Multi-LLM Dialogue for Safe, Agile, and Socially Optimal Multi-Agent Navigation in Constrained Environments," arXiv:2503.12333 (2025) — decentralized contrast: agents negotiate roles ("leader"/"blocker") in natural language to break symmetry in doorways/corridors — [arXiv](https://arxiv.org/html/2503.12333v1)
- MAPF-GPT: "Imitation Learning for Multi-Agent Pathfinding at Scale," arXiv:2409.00134 — transformer trained by imitation of classical solvers (LLM *principles*, not prompted LLM); competitive decentralized learned baseline — [alphaXiv](https://www.alphaxiv.org/abs/2409.00134v5)
- LLM-NAR: "Neural Algorithmic Reasoners informed Large Language Model for Multi-Agent Path Finding," arXiv:2508.17971 (2025) — explicitly motivated by "poor performance of LLMs in MAPF"; adds GNN-based neural algorithmic reasoner + cross-attention to fix it — [arXiv](https://arxiv.org/abs/2508.17971)
- "Can LLM-Reasoning Models Replace Classical Planning? A Benchmark Study," arXiv:2507.23589 (2025) — direct LLM-vs-classical-planner benchmark (single-agent planning focus) — [arXiv PDF](https://arxiv.org/pdf/2507.23589)
- Survey: "Large Language Models for Multi-Robot Systems: A Survey," arXiv:2502.03814; journal version Autonomous Robots (2026) — notes "LLMs and VLMs have been used to resolve deadlock after it occurs by identifying a leader agent to move first" — [arXiv](https://arxiv.org/html/2502.03814v1); [Springer](https://link.springer.com/article/10.1007/s10514-026-10257-4)
- VLMLight: "Traffic Signal Control via Vision-Language Meta-Control and Dual-Branch Reasoning," arXiv:2505.19486 (2025) — LLM meta-controller routes between a fast RL policy (routine flow) and slow VLM deliberation (safety-critical scenes); a published fast-classical/slow-VLM *arbitration* precedent in traffic control — [ar5iv](https://ar5iv.labs.arxiv.org/html/2505.19486)
- MTU-LLM: LLM-based multi-robot task allocation + path planning for SAR, reporting LLM mean computation time 0.033 s vs 0.596 s for the classical baseline at 10 robots/100 victims (CAUTION: an LLM being ~18x faster than a classical MRTA solver is implausible as stated unless it measures only local inference of a distilled model; verify before citing) — [IntechOpen](https://www.intechopen.com/journals/1/articles/619)
- Known weakness of generative planners in multi-agent benchmarks (PARTNR): coordination errors, precedence violations, poor recovery from partial failure — reported via [hierarchical LLM multi-robot planning paper, arXiv:2602.21670](https://arxiv.org/html/2602.21670v2)

### Inferences
- The field's verdict so far: prompted LLMs lose to classical solvers at *path-level* coordination (2401.03630), but win a niche as *event-triggered high-level referees* that unstick otherwise-strong low-level policies (2404.06413, 2503.00717). The thesis sits exactly in that niche — its contribution should be framed as (a) VLM (pixels, not state text) as the referee, (b) real warehouse/Nav2 execution layer, (c) controlled two-arm comparison against a literature-grounded rule-based referee — because the referee-vs-rule-based head-to-head on identical embodied scenarios is what is missing from the record.
- No found paper runs a VLM coordinator and a classical rule-based coordinator as matched arms on the same warehouse congestion scenarios with throughput/recovery metrics; nearest neighbors compare LLM-aided vs un-aided learned policies (LLMDR) or prompt variants (Garg et al.).

### Gaps
- Metrics used in LLMDR and Garg et al. (success rate? makespan? deadlock-resolution rate?) were not extracted — fetch the PDFs (arXiv:2503.00717, arXiv:2404.06413) before writing the related-work section; both are directly load-bearing for the novelty claim.
- MTU-LLM's timing claim needs verification from the primary article before any citation.

## Key Question 5: Hybrid two-layer architectures — slow semantic/central layer over fast local reactive control; precedents and terminology

### Takeaway
The pattern is now standard and has names: "fast–slow" / "dual-system" / "System-1/System-2" architectures; VLM-UDMC (slow VLM at 0.3–1.5 s inference reconfiguring a 20 Hz motion controller) matches the thesis's 0.5–2 Hz over 20–50 Hz split almost exactly in autonomous driving, and the classical AGV world has its own three-layer central traffic-management precedent (IEEE T-ASE 2023).

### Cited Findings
- VLM-UDMC: "VLM-Enhanced Unified Decision-Making and Motion Control for Urban Autonomous Driving," arXiv:2507.15266 (2025) — upper **slow system** (VLM scene reasoning, inference 0.3–1.5 s) dynamically reconfigures the downstream **fast system** (20 Hz motion planning/actuation) — [arXiv](https://arxiv.org/html/2507.15266)
- "Slow Brain, Fast Planner: Latency-Resilient VLM-Augmented Urban Navigation," arXiv:2606.20458 (2026) — explicit latency-resilience framing for VLM-over-planner stacks — [arXiv](https://arxiv.org/abs/2606.20458v1)
- VLMLight (arXiv:2505.19486) — meta-controller chooses fast RL policy vs slow deliberative VLM branch per situation (traffic signals) — [ar5iv](https://ar5iv.labs.arxiv.org/html/2505.19486)
- UniFS: "Unified Fast-to-Slow Hierarchical Architecture for Vision-Language-Action Models," arXiv:2606.22794 (2026) — layer groups of a VLM updated at different frequencies (manipulation) — [arXiv PDF](https://arxiv.org/pdf/2606.22794)
- FSR-VLN: "Fast and Slow Reasoning for Vision-Language Navigation with Hierarchical Multi-modal Scene Graph" (2025/2026) — fast/slow terminology in VLN — [project page](https://horizonrobotics.github.io/robot_lab/fsr-vln/)
- Multi-robot instance of the pattern: Garg et al. (arXiv:2404.06413) — event-triggered LLM/VLM high-level planner invoked on deadlock, over a continuously running GNN/CBF low-level controller — [arXiv PDF](https://arxiv.org/pdf/2404.06413)
- Classical precedent for layered central control: the three-layer AGV traffic management architecture (topological / path-planning / roadmap-coordination layers) in IEEE T-ASE 21(3):3155–3169 — layering by timescale and abstraction predates LLMs in this exact domain — [IEEE Xplore](https://ieeexplore.ieee.org/document/10132864/)
- RHCR itself is a two-rate design: central replanning every h timesteps over per-timestep agent execution — [arXiv:2005.07371](https://arxiv.org/abs/2005.07371)

### Inferences
- Terminology to adopt in the thesis for discoverability: "fast–slow (dual-system) architecture," "hierarchical VLM-in-the-loop planning," "event-triggered high-level replanning." The frequency split itself (sub-2 Hz semantic layer over tens-of-Hz reactive layer) is well-precedented in driving and manipulation; the thesis's distinguishing features are the *multi-robot central* slow layer and the *congestion-recovery* task, not the two-rate structure.

### Gaps
- No found paper applies the fast–slow VLM pattern to a *centralized multi-robot warehouse* coordinator specifically (driving, signals, VLA manipulation, and connected point-robot teams are covered); after multiple query variants this appears to be a genuine open slot, though absence cannot be proven.

## Overall synthesis for the thesis's baseline-family and novelty claims

### Takeaway
The classical baseline family the VLM arm must beat is: (1) RHCR-style windowed central replanning, (2) reservation/zone-based avoidance with banker's/circular-wait logic, (3) rule-based detect→prioritize(FCFS)→retreat recovery assembled from AIM + A-DRIVE + Jäger-Nebel components. The novelty claim survives in narrowed form.

### Cited Findings
- (All citations above; this section is synthesis only.)

### Inferences
- **Safe novelty phrasing**: "To our knowledge, no prior work compares a centralized VLM congestion-resolution planner against a literature-grounded rule-based classical reasoner as matched arms on identical Nav2-executed warehouse deadlock scenarios; prior foundation-model deadlock resolvers operate on grid MAPF (LLMDR) or connected point-robot teams with GNN controllers (Garg et al.), and prior fast–slow VLM stacks target driving or signal control."
- **Unsafe phrasing to avoid**: claiming novelty for (a) centralized recovery per se (A-DRIVE, LLMDR, Garg et al. exist), (b) the two-layer frequency split (VLM-UDMC et al.), or (c) LLM-vs-classical comparison in general (Chen/Koenig/Dilkina, arXiv:2507.23589).
- The classical arm as specified (head-on/intersection detection, FCFS/priority yielder, commanded retreat) is defensible as representative: every component has a citable classical ancestor (AIM FCFS; zone-control circular-wait detection; A-DRIVE backup).

### Gaps
- Before the related-work chapter is final: fetch and extract metrics/baselines from arXiv:2404.06413, arXiv:2503.00717, and the IJRR Grover et al. paper; verify MTU-LLM's timing claim; and attempt to find any 2026 paper pairing a VLM coordinator with Nav2 fleets (searches to date found none).
