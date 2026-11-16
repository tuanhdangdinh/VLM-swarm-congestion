# Centralized LLM/VLM-Based Task Planners and Coordinators for Multi-Robot Systems (2022–2026)

Research notes for the related-work section positioning a VLM as "Centralized Multi-Agent Coordinator / congestion-resolution planner" for a warehouse swarm. All arXiv IDs verified against live arXiv pages or search results on 2026-10-01. Note: arXiv IDs of the form 25xx/26xx (e.g., 2503.x, 2509.x, 2607.x) are 2025/2026 postings.

## KQ1: Landmark systems and their exact coordination topology (one central model vs dialog among per-robot LLMs)

### Takeaway
The field splits into three topologies, named explicitly by Chen et al. (ICRA 2024): CMAS (one central LLM emits actions for all robots), DMAS (per-robot LLM agents in turn-taking dialog), and hybrids (HMAS-1/2: central proposer + local LLM checkers). Landmark centralized systems: SMART-LLM, COHERENT, LaMMA-P, Co-NavGPT, EMOS (central discussion stage), DART-LLM; landmark decentralized/dialog systems: RoCo, CoELA, GameChat.

### Cited Findings
- **Taxonomy paper**: "Scalable Multi-Robot Collaboration with Large Language Models: Centralized or Decentralized Systems?" — Yongchao Chen, Jacob Arkin, Yang Zhang, Nicholas Roy, Chuchu Fan, ICRA 2024, arXiv:2309.15943. Defines DMAS (decentralized, each robot has its own LLM agent, dialog in rounds of turn-taking), CMAS (a single LLM produces actions for all robots), and two hybrids; compares task success rate and token efficiency for increasing numbers of agents in four coordination-dependent 2D task scenarios plus 3D simulation — [arXiv:2309.15943](https://arxiv.org/abs/2309.15943)
- **SMART-LLM**: "SMART-LLM: Smart Multi-Agent Robot Task Planning using Large Language Models" — Shyam Sundar Kannan, Vishnunandan L. N. Venkatesh, Byung-Cheol Min (Purdue), IROS 2024, arXiv:2309.10062. Fully centralized: one LLM converts a high-level instruction into a multi-robot plan through staged programmatic prompts — task decomposition, coalition formation, task allocation — under few-shot prompting; evaluated in simulation (AI2-THOR-based benchmark) and real robots — [arXiv:2309.10062](https://arxiv.org/abs/2309.10062); [project site](https://sites.google.com/view/smart-llm/)
- **RoCo**: "RoCo: Dialectic Multi-Robot Collaboration with Large Language Models" — Zhao Mandi, Shreeya Jain, Shuran Song, ICRA 2024, arXiv:2307.04738. Decentralized dialog topology: each robot (arm) is delegated to an LLM agent; agents "talk" in natural language to agree on sub-task plans AND task-space waypoint paths, then a central multi-arm motion planner computes trajectories — [arXiv:2307.04738](https://arxiv.org/abs/2307.04738). Note: the LLM survey (arXiv:2502.03814) classifies RoCo's final plan-merging step as a centralized "RoCo coordinator" element, so it is dialog + central merge.
- **CoELA**: "Building Cooperative Embodied Agents Modularly with Large Language Models" — Zhang et al. (UMass Embodied AGI), ICLR 2024, arXiv:2307.02485. Fully decentralized with costly communication: each embodied agent runs five modules (Perception, Memory, Communication, Planning, Execution) around its own LLM (GPT-4); no central model at all — [arXiv:2307.02485](https://arxiv.org/abs/2307.02485); [GitHub](https://github.com/UMass-Embodied-AGI/CoELA)
- **LaMMA-P**: "LaMMA-P: Generalizable Multi-Agent Long-Horizon Task Allocation and Planning with LM-Driven PDDL Planner" — ICRA 2025, arXiv:2409.20560. Centralized LM pipeline for heterogeneous robot teams: six modules (Precondition Identifier, Task Allocator, Problem Generator, PDDL Validator, Fast Downward/LLM Planner, Sub-Plan Combiner) — [arXiv:2409.20560](https://arxiv.org/abs/2409.20560); [project page](https://lamma-p.github.io/); [IEEE Xplore 11127951](https://ieeexplore.ieee.org/document/11127951/)
- **COHERENT**: "COHERENT: Collaboration of Heterogeneous Multi-Robot System with Large Language Models" — Liu et al., ICRA 2025, arXiv:2409.15146. Centralized task assigner LLM + per-robot executor agents in a Proposal-Execution-Feedback-Adjustment (PEFA) loop; quadrotors, quadrupeds, robotic arms — [arXiv:2409.15146](https://arxiv.org/abs/2409.15146); [GitHub](https://github.com/SHAILAB-IPEC/COHERENT)
- **EMOS**: "EMOS: Embodiment-aware Heterogeneous Multi-robot Operating System with LLM Agents" — ICLR 2025, arXiv:2410.22662. Hybrid: "Centralized Group Discussion" stage for embodiment-aware task planning/assignment (agents reason over "robot resumes" generated from URDF + kinematics tools), then "Decentralized Action Parallel Execution" — [arXiv:2410.22662](https://arxiv.org/abs/2410.22662); [project](https://emos-project.github.io/)
- **DART-LLM**: "DART-LLM: Dependency-Aware Multi-Robot Task Decomposition and Execution using Large Language Models" — Wang et al., arXiv:2411.09022. Centralized QA-LLM decomposes instructions into a DAG of subtasks with dependency edges, Breakdown Function module assigns robots, plus a VLM-based object detector for perception; applied to construction robotics on edge devices — [arXiv:2411.09022](https://arxiv.org/abs/2411.09022); [project](https://wyd0817.github.io/project-dart-llm/)
- **Co-NavGPT**: "Co-NavGPT: Multi-Robot Cooperative Visual Semantic Navigation Using Vision Language Models" — Yu et al., arXiv:2310.07937. A single VLM is the *global planner*: merges sub-maps from multiple robots into one global map, encodes robot states and frontier regions, and assigns frontiers across robots; validated in Habitat HM3D and on real quadrupeds — [arXiv:2310.07937](https://arxiv.org/pdf/2310.07937). This is one of the closest published analogs to a "central VLM coordinator."
- **Deadlock resolution (most on-point for the thesis)**: "Foundation Models to the Rescue: Deadlock Resolution in Connected Multi-Robot Systems" — Kunal Garg, Jacob Arkin, Songyuan Zhang, Nicholas Roy, Chuchu Fan, 2024, arXiv:2404.06413. Hierarchical: a central LLM *or VLM* high-level planner resolves deadlocks for a connected MRS by assigning a leader and waypoints; a GNN-based distributed low-level control policy executes; up to 15 agents and 40 obstacles — [arXiv:2404.06413](https://arxiv.org/pdf/2404.06413); [Semantic Scholar](https://www.semanticscholar.org/paper/09498b36bb66169f05e6be614a5493576123b6ed). The LLM-for-MRS survey notes the VLM variant used Claude-3 for deadlock resolution via visual understanding — [survey](https://arxiv.org/html/2502.03814v1)
- **GameChat**: "GameChat: Multi-LLM Dialogue for Safe, Agile, and Socially Optimal Multi-Agent Navigation in Constrained Environments" — decentralized natural-language negotiation to break spatial symmetry and prioritize urgent tasks in navigation conflicts — [ResearchGate record](https://www.researchgate.net/publication/389916498_GameChat_Multi-LLM_Dialogue_for_Safe_Agile_and_Socially_Optimal_Multi-Agent_Navigation_in_Constrained_Environments) (arXiv ID not captured in my searches)
- **Organized teams**: "Embodied LLM Agents Learn to Cooperate in Organized Teams" — arXiv:2403.12482; imposing a leader/hierarchy on LLM agent teams improves cooperation (contrast point: hierarchy helps even in dialog systems) — [arXiv:2403.12482](https://arxiv.org/pdf/2403.12482)
- **Survey anchor**: "Large Language Models for Multi-Robot Systems: A Survey" — Peihan Li et al., arXiv:2502.03814 (journal version: Autonomous Robots, 2026, [Springer 10.1007/s10514-026-10257-4](https://link.springer.com/article/10.1007/s10514-026-10257-4)). Classifies: centralized = EMOS, SMART-LLM, DART-LLM, RoCo-coordinator; decentralized = RoCo robot dialogue, LLM2Swarm (Strobel et al.); hierarchical = Wu et al.'s two-layer Task-LLM + Action-LLM framework — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)

### Inferences
- The CMAS/DMAS/HMAS vocabulary of Chen et al. (arXiv:2309.15943) is the standard framing to cite when calling an architecture "Centralized Multi-Agent Coordinator"; the thesis architecture (central VLM at 0.5–2 Hz over per-robot Nav2) maps to CMAS at the semantic layer with classical local control below — structurally closest to Garg et al. 2404.06413 and Co-NavGPT.
- Dialog-based systems (RoCo, CoELA, GameChat) dominate tabletop/household settings; centralized single-model systems dominate when a global state summary is cheap to construct (maps, frontier lists, warehouse grids) — exactly the warehouse overhead-camera case.

### Gaps
- GameChat's arXiv ID and venue were not captured (only ResearchGate hit); verify before citing formally.
- I did not find a SayCan-descendant explicitly marketed as "SayCan for teams"; SMART-LLM and LaMMA-P are the de facto team-scale descendants (skill-grounded decomposition), but no paper self-describes that lineage in my results.

## KQ2: Does the central model emit full ordered multi-robot action sequences, or high-level subgoals refined by classical planners?

### Takeaway
Almost no credible system lets the central LLM emit motion-level commands; the dominant and best-performing pattern is LLM/VLM emits allocation + ordered subgoals (or waypoints/leader designations), with classical planners (PDDL/Fast Downward, motion planners, MAPF solvers, GNN policies) doing the refinement. Direct LLM sequencing of paths demonstrably fails (KQ3).

### Cited Findings
- SMART-LLM's central LLM generates the full decomposed task plan (decomposition → coalition → allocation) as code-like output executed by robots' skill primitives — [arXiv:2309.10062](https://arxiv.org/abs/2309.10062)
- LaMMA-P's LLM allocates sub-tasks by robot skill and *generates PDDL problem files*; the Fast Downward heuristic planner produces each robot's actual action sequence; sub-plans are then combined and converted to executable commands — [arXiv:2409.20560](https://arxiv.org/html/2409.20560v1)
- TwoStep: "Multi-agent Task Planning using Classical Planners and Large Language Models" (arXiv:2403.17246) — LLM only splits a goal into helper-agent subgoals; classical planners do all sequencing — [arXiv:2403.17246](https://arxiv.org/pdf/2403.17246)
- LiP-LLM: integrates linear programming + dependency graphs with LLMs for multi-robot task planning — LLM produces the dependency structure, LP solves the allocation — [arXiv:2410.21040](https://arxiv.org/pdf/2410.21040)
- RoCo's LLM agents do go lower than most: they propose task-space *waypoint paths* per arm, but a centralized multi-arm motion planner still computes trajectories, with collision-check feedback re-prompting the LLMs — [arXiv:2307.04738](https://arxiv.org/abs/2307.04738)
- Garg et al.: foundation model outputs only {leader assignment + a set of waypoints}; a GNN-based distributed low-level policy executes — explicitly motivated by the claim that smooth low-level policies deadlock and the high-level model only needs to break the symmetry — [arXiv:2404.06413](https://arxiv.org/pdf/2404.06413)
- LLMDR: LLM classifies which MAPF agents are deadlocked and suggests *priority strategies*; actual resolution is executed by Priority Inheritance with Backtracking (PIBT), a classical MAPF mechanism — [arXiv:2503.00717](https://arxiv.org/abs/2503.00717)
- Co-NavGPT's VLM assigns frontier goals to robots; local navigation reaches them — [arXiv:2310.07937](https://arxiv.org/pdf/2310.07937)
- Counter-example (LLM as direct sequencer): Chen/Koenig/Dilkina let a central LLM output MAPF move sequences directly and document failure beyond trivial maps — [arXiv:2401.03630](https://arxiv.org/pdf/2401.03630)
- Survey taxonomy of output types: DART-LLM outputs DAG dependencies; SMART-LLM outputs subtasks+allocation; Wu et al.'s Action-LLM outputs "control parameters for the controller" (rare motion-level case); LLCoach (Brienza et al.) outputs high-level natural-language plans for robot soccer — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)

### Inferences
- The thesis design (VLM outputs congestion type + strategy; M3 RAG grounds to concrete commands; Nav2 executes) follows the field's consensus division of labor and can cite LaMMA-P, TwoStep, LLMDR, and Garg et al. as the pattern "semantic decision up top, classical refinement below."
- LLMDR + Garg et al. jointly establish "LLM/VLM as deadlock/congestion *arbiter* (who yields, who leads, what priority)" as a recognized niche — the thesis's congestion-resolution planner is a VLM-grounded instance of this niche.

### Gaps
- Exact output schema (JSON? code? NL?) for COHERENT and EMOS was not extracted from abstracts; check the PDFs if schema comparison is needed.

## KQ3: Reported failure modes for central-model sequencing

### Takeaway
Documented failure modes: inability to plan on maps with obstacles/mazes (MAPF), degradation beyond ~6 agents in centralized topologies, context-token blowup with agent count, faithfulness hallucinations, large accuracy drops as problem clauses accumulate, and 15–30 s/step latency — all arguments for keeping the central model at the semantic/arbitration level.

### Cited Findings
- Central LLM solving MAPF directly "fail[s] to plan on the harder room map and maze map of the standard MAPF benchmark," succeeding only on empty/obstacle-free rooms; authors attribute this to combined multi-agent coordination + planning difficulty and the inability to leverage external tools for the needed reasoning — Weizhe Chen, Sven Koenig, Bistra Dilkina, arXiv:2401.03630 — [arXiv:2401.03630](https://arxiv.org/pdf/2401.03630)
- Scaling agents "increases context token length requirements and LLM inference runtime and API costs"; dialog-based DMAS suffers token inefficiency and poor scalability as robot count grows — [arXiv:2309.15943](https://arxiv.org/html/2309.15943v2)
- Survey (arXiv:2502.03814): "performance degrades beyond 6 agents in centralized architectures"; GPT-4 "response time per step ranged between 15 and 30 seconds" (Chen et al.); "faithfulness hallucinations occur when generated content diverges from user instructions," risking faulty decision-making; LLM math/reasoning drops "up to 65%" as clauses are added (Huang et al.); server-hosted models need reliable connectivity, a problem for field robots — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)
- RoCo requires environment feedback (collision checking) to repair LLM-proposed waypoints in-context — i.e., first-shot geometric proposals are routinely infeasible — [arXiv:2307.04738](https://arxiv.org/abs/2307.04738)
- LLMDR exists precisely because learned MAPF policies deadlock ("no movement or wandering without consistent goal-oriented movement") and shows LLM intervention improves success rates in deadlock-prone scenarios — [arXiv:2503.00717](https://arxiv.org/abs/2503.00717)
- LaMMA-P's 105% success-rate improvement over LM-only multi-agent planners is itself evidence of how poorly unconstrained LM planning performs on long-horizon multi-robot tasks — [arXiv:2409.20560](https://arxiv.org/abs/2409.20560)

### Inferences
- "Hallucinated agents" specifically: I found no paper naming that exact failure; the nearest documented categories are faithfulness hallucination (survey) and infeasible action/waypoint proposals (RoCo, LaMMA-P validator module's existence). The thesis can cite the PDDL-validator and collision-feedback mechanisms as the field's standard guards.
- The 15–30 s/step GPT-4 latency figure directly motivates a 0.5–2 Hz (or slower, event-triggered) slow loop — central LLM/VLM reasoning cannot sit in a control loop.

### Gaps
- No quantitative taxonomy of central-LLM error types (e.g., % ordering errors vs % infeasible actions) surfaced; papers report aggregate success rates, not error breakdowns. LaMMA-P and SMART-LLM appendices may contain per-category failures — worth a PDF pass if needed.

## KQ4: Closed-loop plan revision with execution feedback vs one-shot planning

### Takeaway
First-generation systems (SMART-LLM) are essentially one-shot plan-then-execute; the 2024–2025 generation is closed-loop: COHERENT's PEFA loop, RoCo's feedback re-prompting, LaMMA-P's regenerate-on-failure, VADER's error-recovery replanning, and event-triggered intervention (Garg, LLMDR) where the central model engages only when execution stalls — the latter matching the thesis's congestion-timeout trigger.

### Cited Findings
- COHERENT's PEFA: centralized assigner proposes decomposition/assignment → robot executors attempt actions → each reports *self-reflection feedback* → assigner adjusts plan; loops until task completion — [arXiv:2409.15146](https://arxiv.org/abs/2409.15146)
- RoCo: environment feedback (e.g., collision checks) is injected and "prompts the LLM agents to improve their plan and waypoints in-context" — [arXiv:2307.04738](https://arxiv.org/abs/2307.04738)
- LaMMA-P: "If the initial plan fails, the LLM regenerates and adapts the plan until a viable solution is produced" (PDDL validation loop) — [arXiv:2409.20560](https://arxiv.org/html/2409.20560v1)
- VADER (Ahn et al., per the survey): detects "deviations from expected task progression and performing error recovery by replanning" — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)
- Garg et al.: the foundation-model planner is invoked *when the low-level controller deadlocks* — an event-triggered closed loop over a persistent low-level policy, not continuous replanning — [arXiv:2404.06413](https://arxiv.org/pdf/2404.06413)
- LLMDR analyzes agent movement within a sliding detection window of the execution plan, i.e., continuous monitoring with conditional intervention — [arXiv:2503.00717](https://arxiv.org/abs/2503.00717)
- SMART-LLM, by contrast, is described purely as instruction → staged plan generation → execution, with no feedback stage in abstract or project page — [arXiv:2309.10062](https://arxiv.org/abs/2309.10062)

### Inferences
- No surveyed system maintains a *persistent, versioned* central plan that the model incrementally edits against a task registry (as M5+M2 do); closest are PEFA (full re-proposal each round) and event-triggered arbitration. This is a defensible novelty claim if phrased carefully.

### Gaps
- VADER's own arXiv ID was not retrieved (known only via the survey); verify before citing directly.

## KQ5: Benchmarks, metrics, and slow-loop central reasoning over fast local control

### Takeaway
Standard metrics are task success rate, token cost/efficiency, completion steps, and response latency, on benchmarks like RoCoBench, Habitat-MAS, COHERENT's 100-task suite, and Chen et al.'s BoxNet/warehouse/BoxLift. Explicit two-rate architectures exist (foundation-model planner over GNN/learned low-level control) but nobody publishes a "0.5–2 Hz" number — the latency data (15–30 s/step GPT-4) implies even slower loops in practice.

### Cited Findings
- Chen et al. evaluate task success rate and *token efficiency* across agent counts in four 2D scenarios (environments named BoxNet, warehouse, BoxLift per the survey) + 3D sims with vision-to-text and dynamical errors; hybrid HMAS-2 "achieves better task success rates across all four tasks and scales better to more agents" — [arXiv:2309.15943](https://arxiv.org/abs/2309.15943); [survey](https://arxiv.org/html/2502.03814v1)
- RoCoBench: 6 multi-robot collaboration tasks + text-only reasoning dataset; RoCo reports high success across tasks and adaptation to task-semantics variation — [arXiv:2307.04738](https://arxiv.org/abs/2307.04738)
- COHERENT-Benchmark: 100 complex long-horizon heterogeneous tasks; metrics = success rate and execution efficiency; "surpasses previous methods by a large margin" — [arXiv:2409.15146](https://arxiv.org/abs/2409.15146)
- LaMMA-P: 105% higher success rate and 36% higher efficiency than existing LM-based multi-agent planners on its MAT-THOR-style benchmark — [arXiv:2409.20560](https://arxiv.org/abs/2409.20560)
- Habitat-MAS (EMOS): manipulation, perception, navigation, multi-floor rearrangement requiring embodiment-aware reasoning — [arXiv:2410.22662](https://arxiv.org/abs/2410.22662)
- CoELA: C-WAH and TDW-MAT benchmarks; GPT-4-driven CoELA beats strong planning baselines; human-trust user study — [arXiv:2307.02485](https://arxiv.org/abs/2307.02485)
- DART-LLM: three task-complexity levels; DeepSeek-r1-671B gives highest success rate while Llama-3.1-8B gives best response-time reliability — an explicit accuracy-vs-latency tradeoff datapoint — [arXiv:2411.09022](https://arxiv.org/abs/2411.09022)
- Two-rate architectures: Garg et al. (foundation-model high-level planner + GNN distributed low-level policy, up to 15 agents/40 obstacles) — [arXiv:2404.06413](https://arxiv.org/pdf/2404.06413); survey's "hierarchical" class (Task LLM + Action LLM, Wu et al.) — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)
- Latency: GPT-4 15–30 s per planning step (survey, citing Chen et al.) — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)
- VLM coordination results: COMRES-VLM (VLM coordinates multi-robot exploration/search over frontier clusters + topological skeletons): 10.2% faster exploration completion, 55.7% higher object-search efficiency vs SOTA coordination — [arXiv:2509.26324](https://arxiv.org/pdf/2509.26324); Co-NavGPT outperforms baselines on HM3D success rate and efficiency without task-specific training — [arXiv:2310.07937](https://arxiv.org/pdf/2310.07937)
- Industrial contrast (non-LLM central brain): DeepFleet (Amazon Robotics, arXiv:2508.08574) trains four fleet foundation-model architectures (robot-centric decision transformer, robot-floor cross-attention, image-floor conv+temporal transformer, graph-floor GNN) on 700K–5M robot-hours from "hundreds of thousands of robots" for congestion forecasting, adaptive routing, proactive rescheduling; these are learned world models, *not* LLMs/VLMs; robot-centric model best (DTW deviation 8.68); power-law scaling observed — [arXiv:2508.08574](https://arxiv.org/html/2508.08574)
- 2026-adjacent entries for completeness: Multi-Agent Robotic Control with Onboard VLMs in simulated industrial warehouses — [arXiv:2607.07403](https://arxiv.org/html/2607.07403v1); DynaHMRC decentralized heterogeneous collaboration — [arXiv:2606.14882](https://arxiv.org/pdf/2606.14882)
- Pure-software multi-agent LLM contrast (brief): "Multi-Agent Collaboration Mechanisms: A Survey of LLMs" — [arXiv:2501.06322](https://arxiv.org/pdf/2501.06322); BOLAA orchestration benchmark (via the MRS survey) — [arXiv:2502.03814](https://arxiv.org/html/2502.03814v1)

### Inferences
- No paper in my sweep reports a central LLM/VLM loop running at 0.5–2 Hz over 20–50 Hz local control; published central-reasoning cadences are either per-plan-step (tens of seconds) or event-triggered. The thesis's explicit two-rate (0.5–2 Hz semantic / 20–50 Hz reactive) framing with a congestion-timeout trigger appears to be an articulation gap in the literature it can fill, citing Garg et al. and LLMDR as the nearest event-triggered precedents and DeepFleet as the non-LLM industrial ceiling.
- Metric set to adopt for comparability: task/resolution success rate, time-to-resolution (analog of completion steps), token cost per intervention, and intervention latency.

### Gaps
- No standardized warehouse-congestion benchmark for LLM/VLM coordinators exists in my results; Chen et al.'s "warehouse" 2D environment and DeepFleet's proprietary data are the closest, and the survey itself notes "limited LLM-specific warehouse studies."
- Token/dollar cost numbers beyond Chen et al.'s token-efficiency comparisons were not found in abstract-level sources; per-paper appendices would be needed.
- LLM2Swarm (Strobel et al.), LLCoach (Brienza et al.), VADER (Ahn et al.), Wu et al. hierarchical framework, Gupte et al. (initial task allocation, logistics): known only via the survey (arXiv:2502.03814); fetch individual arXiv IDs before formal citation.
