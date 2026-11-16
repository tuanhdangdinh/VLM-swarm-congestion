# LLM/VLM Multi-Robot Coordination and LLM+MAPF Work Since Mid-2026

Scan date: 2026-11-12. Before writing, I pulled every arXiv ID from the excluded notes (the three research_notes folders, `llm_vlm_coordination.md`, `trending_models.md`, and the deadlock-papers memory file) and grepped the candidate titles below against them. Items already there are skipped, including 2609.27816 (VLM-LLM + reachability), 2606.06762 (CCTV warehouse), 2607.12050 (EFLUX), 2603.20182 (IndoorR2X), 2602.19304 (CaPE), 2509.26324 (COMRES-VLM), 2509.16805 (LVLM selection bias), 2602.06967, 2503.00717 (LLMDR), 2404.06413, 2505.13376 and 2409.00134 (MAPF-GPT).

Verification labels:
- **VERIFIED** means I fetched the arXiv abstract page in this session; title, authors, date and code link come from that page.
- **SEARCH-REPORTED** means I saw the item only in search snippets.

## Q1: New LLM/VLM centralized or hierarchical coordinators for multi-robot traffic, deadlock and congestion

### Takeaway
No paper since mid-2026 does exactly what we do: a centralized VLM watching an overhead camera, detecting warehouse congestion and choosing a strategy. The two closest new items are CoPlanVLM (Oct 2026), where a VLM plus image overlay plans coordinated two-robot paths, and Verifier-Mediated Multi-LLM Coordination (Oct 2026), a centralized-vs-decentralized LLM planner with a geometric conflict verifier. Both are relevant baselines or related work. Neither targets congestion or deadlock strategy selection.

### Cited Findings
- **CoPlanVLM: Coordinated Path Planning for a Robot Team using Vision Language Models** (Martin, Paquet, Al Faruque, Khargonekar, Volle, Ramos, Nivison). arXiv:2610.14341, submitted 2026-10-09, cs.RO. **VERIFIED.** Code: https://github.com/AICPS/CoPlanVLM — [arXiv](https://arxiv.org/abs/2610.14341)
  - Method: from one natural-language instruction plus an image, a VLM produces coordinated paths for two robots.
  - Spatial-reasoning fixes: (1) an image overlay marking free space and obstacles; (2) a task classifier that picks the low-level planner and reasoning prompt; (3) task-specific chain-of-thought that identifies key objects, assigns roles and checks for collision-free routes.
  - Results: 84.4% average success vs 50.0% for the closest baseline, and paths about 27% shorter when both succeed. Validated in Gazebo and on physical TurtleBot 4 robots.
  - A search snippet says inter-robot collision avoidance is enforced *after* planning. I did not confirm this in the paper — [search snippet via ResearchGate listing](https://www.researchgate.net/publication/415747844_CoPlanVLM_Coordinated_Path_Planning_for_a_Robot_Team_using_Vision_Language_Models)
  - **Applicability:** this is the most direct new evidence that annotating the frame with free space and obstacles, plus routing by task type, fixes VLM spatial weakness. It speaks to our "VLM ignores geometry" problem and is a candidate prompt and overlay baseline. Open-source, ROS/Gazebo.
- **Verifier-Mediated Multi-LLM Coordination for Multi-Robot Path Planning** (Khatana, Song, Hovakimyan, Voulgaris). arXiv:2610.12761, submitted 2026-10-08. **VERIFIED.** No code link. Linked workshop page: zhourobotics.github.io/fm-mrs — [arXiv](https://arxiv.org/abs/2610.12761)
  - Method: compares one centralized LLM planning for the whole team against per-robot LLM planners. A geometric verifier turns the plans into trajectories, detects predicted inter-robot conflicts and returns structured feedback for targeted replanning.
  - Evaluation: CARLA and Crazyflie drones. The abstract gives no numbers.
  - **Applicability:** this is the same "semantic proposer + geometric verifier/feedback" split as our M2→M3 gate, which makes it a related-work and novelty-overlap item. The difference is that it plans paths rather than choosing deadlock strategies, and it is not warehouse or overhead-camera.
- **Hierarchical Control in Multi-Agent Games: LLM-based Planning and RL Execution** (Hösch, Sestini, … Gisslén). arXiv:2606.20014, v1 2026-06-18, v3 2026-07-09. **VERIFIED.** No code — [arXiv](https://arxiv.org/abs/2606.20014)
  - Method: an LLM acts as a central strategist that *selects among specialized RL skill policies*.
  - Results: 46.4% win rate vs 51.5% for a behavior tree (not significant), and clearly better than end-to-end RL.
  - **Applicability:** structurally it is "LLM picks a strategy from a fixed menu, a lower layer executes", which is our pattern, but in a game. Useful as a cross-domain citation, and its result (no better than hand-crafted rules) is a caution for our claims.
- **EmboTeam: Asymmetric State Grounding for Heterogeneous Multi-Robot Collaboration**. arXiv:2601.11063 (Jan 2026, included because it was not in the existing notes). **SEARCH-REPORTED.** — [arXiv](https://arxiv.org/html/2601.11063)
  - Method: an LLM produces structured state expectations, which are checked by PDDL symbolic search and compiled into a team behavior tree.
  - **Applicability:** a neuro-symbolic "LLM proposes, symbolic layer checks" precedent for task allocation rather than traffic. Low priority.
- **Dynamic Haven Selection for Multi-Agent Pickup and Delivery in Constrained Warehouses** (Hirayama, Yoshida, Sakaji, Noda). arXiv:2608.26939, 2026-08-27. **VERIFIED.** No LLM, no code — [arXiv](https://arxiv.org/abs/2608.26939)
  - Method: A-SHARP lets robots switch their protected waiting spot ("Haven") at task assignment in narrow-aisle, dead-end warehouses.
  - Results: proven safety invariants and eventual completion. Lower makespan in 107 of 138 configurations, never significantly worse, and a 16.7% median makespan reduction on the tree map, over 72k runs.
  - **Applicability:** a classical symbolic baseline for our `temporary_wait`/`yield` strategies. It is a provably safe "retreat to a haven" primitive that M3 could ground to.
- **Complete, Scalable, and Robust Prioritized Planning for Multi-Robot Ordered Storage and Retrieval at Maximum Capacity**. arXiv:2608.07734 (2026). **SEARCH-REPORTED.** Claims deadlock-free parallel execution at full storage density, with no LLM — [arXiv](https://arxiv.org/abs/2608.07734)
  - **Applicability:** a classical non-LLM deadlock-free baseline for dense warehouses.
- **LIDSA: Cognitive Arbitration for Signal-Free Autonomous Intersection Management**. arXiv:2605.12321. Already in the existing ID list, so not re-reported beyond this pointer.
- **Traffic-VL** (arXiv:2611.06353) and **VLALight** (arXiv:2609.30709 / 2609.36934) are VLM/VLA traffic-signal controllers for road traffic. **SEARCH-REPORTED** — [Traffic-VL](https://arxiv.org/html/2611.06353v1)
  - 2609.30709 and 2609.36934 are already in the existing notes. Traffic-VL appears new.
  - Traffic-VL is an 8B RL-tuned VLM that maps multi-view surveillance images plus phase descriptions to signal decisions.
  - **Applicability:** an RL-fine-tuned VLM making discrete control choices from camera views is an analogue of fine-tuning our M2 on strategy labels. Road domain, low priority.

### Inferences
- The "VLM picks strategy, symbolic grounder executes" niche for *warehouse congestion and deadlock from an overhead camera* still looks unoccupied as of 2026-11-12, as far as these searches reach.
- The nearest overlap is in architecture rather than task: the proposer/verifier split in 2610.12761, and LLM-as-menu-selector in 2606.20014.
- CoPlanVLM's overlay result (84.4% vs 50.0%) is the strongest new external support for adding a free-space/corridor overlay to our annotated frame to address geometry blindness.
- None of the new coordinators address multi-cluster congestion. All are single-conflict or two-robot setups, so our multi-cluster under-addressing remains a gap in the literature as well as in our system.

### Gaps
- I found no CoRL 2026 / IROS 2026 accepted-paper lists in search, so I could not confirm venue placement for any item.
- I could not get CoPlanVLM's full baseline list or failure analysis (the ResearchGate page returned 403; only the arXiv abstract was read).
- 2610.12761 reports no quantitative results in its abstract. Its centralized-vs-decentralized trade-off numbers are unknown.

## Q2: LLM + MAPF hybrids and foundation models for MAPF

### Takeaway
Since mid-2026, LLMs in MAPF mostly *write or tune planner code offline*, as in Late Autumn and LLM-guided AGV heuristic design. They are not used as online conflict resolvers. Learned-guidance MAPF (LaCAM/PIBT plus learned or local guidance) keeps advancing without LLMs, and I found no 2026 MAPF-GPT successor.

### Cited Findings
- **Late Autumn: LLM Agents Specialize a General Multi-Robot Planner for One Warehouse** (Tang, Zhang, Chan, Bıyık, Koenig, Chen). arXiv:2611.02391, submitted 2026-11-02. **VERIFIED.** No repo; ancillary `frontier_steps.csv` — [arXiv](https://arxiv.org/abs/2611.02391)
  - Method: LLM coding agents run autonomous research loops that patch a task-assignment + MAPF warehouse planner.
  - Throughput: +22–60%, holding on unseen seeds. Agents *rediscovered corridor-exit priorities, local guidance and rollouts*.
  - Transfer: gains mostly carried over to a new layout, a larger fleet and different service times. They shrank with a smaller fleet and mostly vanished under outbound-heavy demand.
  - Costs: patches were 0.7k–2.4k lines (median step 27 lines). Some patches increased compute by more than 100x, and human review caught problems the score missed.
  - **Applicability:** this is the most important new LLM+MAPF item. It is a different use of LLMs (offline planner specialization rather than online strategy choice), and it is a strong related-work contrast. The Koenig group is now involved.
- **LLM-Guided Heuristic Design from Simulation Traces: A Case Study in Dynamic Production and AGV Scheduling** (Li, Li). arXiv:2608.09343, 2026-08-10. **VERIFIED.** No code — [arXiv](https://arxiv.org/abs/2608.09343)
  - Method: a manager LLM forms bottleneck hypotheses from event traces, and editor agents propose code revisions.
  - Results: best-so-far score rose from 62.49 to 78.61 (0–100 scale). It beat rolling-MILP, rule-based and metaheuristic baselines over 100 seeds.
  - **Applicability:** a trace-driven LLM diagnosis loop. It is relevant if we ever have an LLM mine our run logs for failure modes, but it is not an online coordinator.
- **PRIMAL3: Pathfinding via Reinforcement and Imitation Multi-Agent Learning — Leveraging LaCAM3**. arXiv:2608.04905 (Aug 2026). **SEARCH-REPORTED.** Project page: https://marmotlab.github.io/PRIMAL3/ — [arXiv](https://arxiv.org/html/2608.04905v1)
  - Method: LaCAM3-guided confidence boosting during training, plus priority-aware PIBT action refinement. No LLM.
  - **Applicability:** a learned MAPF baseline if we ever compare against a learned decentralized solver.
- **Lifelong LaCAM with Local Guidance for Lifelong MAPF (LLLG)**. arXiv:2605.16855 (May 2026). **SEARCH-REPORTED** — [arXiv](https://arxiv.org/pdf/2605.16855)
  - Compares against RHCR, PIBT, LaCAM and Guided-PIBT. Inherits PIBT efficiency. No LLM.
  - **Applicability:** this is the "local guidance" mechanism that Late Autumn's agents rediscovered, and it is the current classical lifelong-MAPF baseline.
- **Multi-Agent Path Finding via Offline RL and LLM Collaboration** (Atasever, Hong, Kulkarni, Li, Deshmukh). arXiv:2509.22130, 2025-09-26 (late-2025, not in the existing notes). **VERIFIED.** No code — [arXiv](https://arxiv.org/abs/2509.22130)
  - Method: a Decision Transformer MAPF policy with GPT-4o briefly guiding agent policies when the environment changes.
  - **Applicability:** a minor LLM-in-the-loop MAPF precedent. It fits the "LLM intervenes occasionally on top of a learned or reactive base" framing that matches our slow layer.
- **MARL-GPT: Foundation Model for Multi-Agent Reinforcement Learning**. arXiv:2604.05943 (Apr 2026). **SEARCH-REPORTED** — [arXiv](https://arxiv.org/pdf/2604.05943)
  - Cites MAPF-GPT. I found no 2026 MAPF-GPT successor; the latest follow-up remains MAPF-GPT-DDG (arXiv:2506.23793, 2025) — [arXiv](https://arxiv.org/html/2506.23793)
  - The base repo is https://github.com/CognitiveAISystems/MAPF-GPT.

### Inferences
- In 2026 the LLM role in MAPF has moved from "LLM solves or deconflicts" (the 2024–25 papers already in our notes) to "LLM engineers the solver". That leaves *online, low-rate LLM/VLM strategy selection over a reactive base* still distinct, but reviewers may ask why we don't use Late Autumn-style offline specialization instead.
- Late Autumn's rediscovered mechanisms (corridor-exit priorities, local guidance) map onto our `yield`/`reverse` in aisles. They are candidate symbolic rule baselines for M2 ablations, for example "corridor-exit priority rule vs VLM".

### Gaps
- I found no 2026 paper that uses an LLM to guide CBS/PIBT/LaCAM *online*.
- I found no 2026 MAPF-GPT follow-up.
- PRIMAL3 and LLLG details are snippet-level only.

## Q3: Embodied-reasoning VLMs and spatial-grounding benchmarks relevant to top-down scenes

### Takeaway
The model side (Gemini Robotics-ER 2, Cosmos Reason2, RoboBrain 2.0) is already covered in `trending_models.md`. New items here are RoboBrain 2.5 (Jan 2026) and a few 2026 spatial benchmarks. They all confirm that VLMs remain unreliable at metric and multi-instance spatial comparison, which matches our geometry-blindness symptom. I found no 2026 benchmark for top-down *multi-agent* traffic scenes.

### Cited Findings
- **RoboBrain 2.5: Depth in Sight, Time in Mind** (BAAI). arXiv:2601.14352 (Jan 2026, not in the existing notes). **SEARCH-REPORTED** — [arXiv](https://arxiv.org/pdf/2601.14352)
  - Reports 2D spatial benchmark scores of 76.30 and 75.40, vs Gemini-3-Pro-Preview at 38.60 and GPT-5.2 at 33.00 on one of them. On RoboSpatial it trails Gemini-3-Pro-Preview.
  - These are vendor-reported numbers from snippets; the exact benchmark names are uncertain.
  - **Applicability:** an open-weight successor to RoboBrain 2.0 (which advertised multi-agent coordination). A possible open robotics-specialist backend alongside Cosmos Reason2.
- **SpatialQuery: Benchmarking Geometry-Grounded Multi-Instance Spatial Reasoning in VLMs** (Nguyen, Vu, Tran). arXiv:2608.01709, 2026-08-03. **VERIFIED.** Project: https://namhai1810.github.io/SpatialQuery/ — [arXiv](https://arxiv.org/abs/2608.01709v1)
  - Finding: VLMs are "unreliable in metric spatial reasoning", worst when comparing multiple instances of the same category. Robots of the same type in our frame are exactly that case.
  - Method: lifting the image to a bird's-eye view, plus uncertainty-aware CoT. With Qwen3-VL-8B this reaches 0.259 m floor MAE and 84.18% proximity-decision accuracy.
  - **Applicability:** supports giving M2 explicit metric geometry (distances or gaps in text) rather than relying on the image. "Which robot is closer to the aisle exit" is a same-category CIDQ-like query.
- **CityCube: Benchmarking Cross-view Spatial Reasoning** (ACL 2026). Reports that reasoning-oriented VLMs struggle on spatial tasks. **SEARCH-REPORTED** — [ACL Anthology](https://aclanthology.org/2026.acl-long.416.pdf)
- **CVSBench: Cross-view Spatial Reasoning and Dreaming**. arXiv:2606.22476. **SEARCH-REPORTED**; contents not confirmed — [arXiv](https://arxiv.org/pdf/2606.22476)
- **Do Multimodal LLMs Understand Order? Measuring the Fragility of Multimodal Reasoning under Input Order Perturbations** (LREC 2026). **SEARCH-REPORTED** — [ACL Anthology](https://aclanthology.org/2026.lrec-1.716/)
  - Evaluates 14 LVLMs on MMMU, CVQA and MMBench and finds predictions shift with both answer-choice order *and modality order*.
  - **Applicability:** direct external evidence for our first-option and robot_1 prior. It suggests also randomizing or ablating *image-before-text vs text-before-image* order, not only option order.
- **Gemini Robotics-ER 2** (2026-07-30) is already covered in `trending_models.md`. The only new material is secondary-blog claims of "multi-robot coordination" support, with no primary spatial-benchmark numbers found — [tech-now.io (secondary)](https://tech-now.io/en/blogs/gemini-robotics-er-2/)

### Inferences
- New benchmarks still test single-image indoor or cross-view setups. No public benchmark matches "top-down warehouse, multiple identical robots, who should yield". Our replay set could be framed as a contribution there.
- The order-perturbation finding (LREC 2026) and SpatialQuery's same-category weakness together explain two of our three open problems: option and robot priors, and geometry neglect among identical robots.

### Gaps
- No primary DeepMind spatial-benchmark numbers for ER-2 were found.
- No "RoboBrain 3" was found.
- I found no 2026 independent study of Cosmos Reason2 on multi-agent scenes.

## Q4: Novelty threats and direct baselines for "VLM picks strategy, symbolic grounder executes"

### Takeaway
I found no direct novelty threat since mid-2026. The closest new items share the architecture pattern but not the task: 2610.12761 (LLM proposer + geometric verifier feedback), 2606.20014 (LLM selects from a skill menu), and CoPlanVLM (VLM + overlay + planner selection). The most usable *direct baselines* are CoPlanVLM (open code, ROS/Gazebo, TurtleBot 4) and classical deadlock-free planners (A-SHARP havens, 2608.07734).

### Cited Findings
- CoPlanVLM has a task classifier that *selects a low-level planner and prompt*. That is close to selecting a strategy and then grounding it with a symbolic planner, and it ships open code — [arXiv](https://arxiv.org/abs/2610.14341); [GitHub](https://github.com/AICPS/CoPlanVLM)
- 2610.12761 frames the key problem as symbolic plans that are "jointly infeasible" after geometric grounding, which is the same motivation as our M3 feasibility gate — [arXiv](https://arxiv.org/abs/2610.12761)
- 2606.20014 shows an LLM menu-selector matching but not beating a hand-crafted behavior tree — [arXiv](https://arxiv.org/abs/2606.20014)
- Late Autumn shows that LLM-specialized classical planners gain 22–60% throughput in warehouses. That is a competing use of LLMs that reviewers may raise — [arXiv](https://arxiv.org/abs/2611.02391)

### Inferences
- Recommended baselines, in order:
  1. A rule baseline using corridor-exit priority or haven retreat (Late Autumn / A-SHARP mechanisms).
  2. CoPlanVLM-style overlay prompting as a "VLM with spatial scaffolding" arm.
  3. A verifier-feedback replanning arm (2610.12761 style), to separate our gate from re-prompting.
- Our distinct claims stay defensible as long as we emphasize:
  - overhead-camera congestion *detection* plus strategy choice;
  - multi-cluster scenes;
  - the measured order and identity priors.

### Gaps
- Searches cannot rule out unindexed CoRL/IROS 2026 camera-ready papers or very recent (Nov 2026) arXiv postings.
- A direct arXiv listing crawl of cs.RO/cs.MA for Oct–Nov 2026 was not done (search budget).
