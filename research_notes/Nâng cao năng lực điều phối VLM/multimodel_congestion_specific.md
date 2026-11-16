# Multi-Model Architectures and Congestion-Specific LLM/VLM Coordination (2024–2026)

Scope: (A) multi-model designs — ensemble/voting, judge/verifier, debate, hierarchical big-plans/small-monitors, routers — with measured gains vs single-model; (B) congestion-specific LLM/VLM work — traffic signals, intersection management, warehouse AGV, crowd flow, deadlock resolution — metrics and grounding mechanisms. Research date: 2026-10-06.

## Does multi-instance debate or judge-verifier measurably beat single-shot planning in embodied/multi-agent tasks?

### Takeaway
Yes, with real numbers in several embodied settings — debate yields 18–35% gains over compute-matched zero-shot in robot co-design, self-verification/self-debugging adds +16–27.5% success in robot routing, and debate resolves embodied ambiguity at 76.7% success for small models — but the gains are strongest for weaker base models and no paper tests debate specifically on congestion/ordering decisions.

### Cited Findings
- **Debate2Create (D2C)** (ICML 2026 poster) formulates robot co-design as a structured thesis–antithesis–synthesis debate between a design agent and a control agent, with *pluralistic LLM judges* giving multi-objective feedback. Across five MuJoCo locomotion benchmarks it achieves up to 3.2x the default Ant score and ~9x on Swimmer; iterative debate yields **18–35% gains over compute-matched zero-shot generation** — so the gain is not just from extra tokens — [arXiv 2510.25850](https://arxiv.org/pdf/2510.25850), [ICML 2026](https://icml.cc/virtual/2026/poster/66635)
- Multi-agent debate for **ambiguity detection in robot requests**: collaboration significantly improves small open models (Llama3-8B, Mistral-7B); debates led by Mistral-7B reached **76.7% success**, effective on complex spatial ambiguities — [arXiv 2507.12370](https://arxiv.org/pdf/2507.12370)
- Classic multi-agent debate result (Du et al.): debate "consistently improved factual accuracy by up to 8 pp and reasoning by up to 26 pp across tasks" vs single models — [alphaXiv overview of 2305.14325](https://alphaxiv.org/overview/2305.14325v1)
- A 2026 study found individual debate accuracies of both LLM agents outperform single-model baselines in **19 of 21 settings, average +7.05% mean accuracy** — [arXiv 2601.22297](https://arxiv.org/html/2601.22297)
- **Judge/verifier over a planner, embodied numbers**: in LLM robot routing (TSP/mTSP variants), adding **self-debugging raises mean success rate by +27.5%**, and adding **self-verification adds a further +16.0%** for GPT-4 Turbo — [arXiv 2403.10795](https://arxiv.org/pdf/2403.10795)
- **Guardian** (Dec 2025): VLM-based detection of robotic planning and execution errors; the authors state improved failure detection "translates into tangible gains in online robot experiments" — [arXiv 2512.01946](https://arxiv.org/pdf/2512.01946)
- **VerifyLLM**: pre-execution task-plan verification by converting NL instructions to LTL and analyzing action sequences before the robot runs them — [publication page](https://rairi.frccsc.ru/en/publications/678), [arXiv 2507.05118](https://arxiv.org/abs/2507.05118v1)
- A "Judge-Planner" two-agent framing externalizes critique into an independent judge, enabling explicit precision–recall accounting and modular substitution of the judge LLM — [emergentmind on 2607.05391](https://www.emergentmind.com/papers/2607.05391)
- **LLM-as-a-Verifier** computes continuous scores from score-token logits (no training) and, used as dense feedback for RL, improves sample efficiency of SAC and GRPO on robotics benchmarks — [arXiv 2509.02761](https://arxiv.org/pdf/2509.02761v3)
- Counter-evidence (not re-verified in this pass): Smit et al., "Should we be going MAD?" (ICML 2024) reported that multi-agent debate does **not** reliably beat simpler self-consistency/ensembling baselines at matched compute on reasoning tasks — [arXiv 2311.17371](https://arxiv.org/abs/2311.17371). I did not fetch this paper this session; treat the direction (debate gains are not free or universal) as the claim, not specific numbers.

### Inferences
- The pattern across these papers: debate/judging helps most where the single model's failure mode is *unexamined commitment* (ambiguity, infeasible plans, hallucinated routes) — exactly the failure mode we see in gpt-4o's first-slot/robot_1 prior. A cheap verifier that checks the ordering decision against geometric feasibility (like our M3 `swap` gate) is the literature-consistent design; full free-form debate is the expensive version of the same idea.
- D2C is the only one with a compute-matched control (18–35%), which is the honest number to quote; Du-style debate numbers conflate debate with extra inference compute.
- None of these operate at Layer-2 cadence constraints (0.5–2 Hz); GameChat (below) is the only one that reports negotiation latency against a vehicle-motion deadline.

### Gaps
- No paper found that runs *debate between model instances about a congestion/right-of-way decision* and scores it against an optimal schedule. This appears genuinely open.
- Guardian's exact online-gain numbers were not extracted (abstract-level claim only).

## Cross-model ensembles (two different VLM providers voting) — any robotics results?

### Takeaway
No true cross-provider voting result exists in robotics coordination as of Oct 2026; the closest things are intra-model temporal trajectory voting (VOTE), energy-based ensembling of multiple VLA *policies* (EnsembleVLA), and the deadlock-resolution paper that *benchmarks* Claude/GPT models side by side without combining them.

### Cited Findings
- **VOTE** (2025): voting-based adaptive ensemble over action predictions from *adjacent time steps of the same VLA model* — an "action sampling committee" weighted by accumulated tickets from prior predictions; motivation is latency reduction and robustness, not cross-provider redundancy — [arXiv 2507.05116](https://arxiv.org/pdf/2507.05116)
- **EnsembleVLA** (ICML 2026): formulates diffusion- and flow-based VLA models as energy-based models so multiple pre-trained policies compose additively into a stronger ensemble policy at the distribution level — [ICML 2026 poster](https://icml.cc/virtual/2026/poster/61698)
- The multi-robot deadlock paper (below) evaluates Claude3-Sonnet, Claude3-Opus, GPT-4o, GPT-4-Turbo, GPT-4, GPT-3.5, Claude2 side by side on the same deadlock tasks — a cross-provider *comparison*, not an ensemble — [arXiv 2404.06413](https://arxiv.org/html/2404.06413v2)
- **Router literature** (general, not robotics): HierRouter assembles inference pipelines from a pool of specialized lightweight LLMs via PPO, improving response quality up to 2.4x vs individual models at minimal added cost — [arXiv 2511.09873](https://arxiv.org/html/2511.09873v1); cascade routing (cheap model first, escalate when likely wrong) can match large-model accuracy at -17% cost, and RouteLLM-style routing retains ~95% of frontier quality while sending ~85% of queries to cheaper models (45–85% cost cut) — [routing/cascade overview](https://tianpan.co/blog/2025-11-03-llm-routing-model-cascades) (secondary source, blog)

### Inferences
- A two-provider vote on the M2 strategy enum (e.g., gpt-4o + Gemini ER-2 voting on yield/reroute/swap) would be novel relative to the published record — nothing found does provider-level voting on a coordination decision. Given our finding that gpt-4o's ordering choice is dominated by presentation-order priors while ER-2 opens with `reverse` on asymmetric scenes, the two models' error modes are plausibly decorrelated, which is the precondition ensembles need.
- The router/cascade numbers justify a "small model monitors, big model arbitrates" split economically, but no robotics paper has published that split's effect on coordination quality.

### Gaps
- No measured robotics result for cross-provider voting or disagreement-triggered escalation. Any claim we make here has to come from our own experiments.
- HierRouter's "2.4x quality" is on QA-style benchmarks, not embodied tasks.

## LLM/VLM for traffic signal control / intersection management 2024–2026 (LLMLight lineage) — deltas vs RL, and what transfers to swarm intersections?

### Takeaway
LLMLight/LightGPT reaches parity with SOTA RL on in-distribution travel time (274.03s vs Advanced-CoLight 274.67s on Jinan) and wins decisively on transfer, scale-out, and extreme-traffic robustness; the lineage's 2025–2026 successors (CoLLMLight, ProcessLight, LIDSA) add network-wide cooperation, process supervision, and explicit right-of-way arbitration — and the transferable lesson for swarm intersections is that the LLM's edge is generalization and rule-grounded arbitration, not raw in-distribution throughput.

### Cited Findings
- **LLMLight + LightGPT** (KDD 2025; ranked No. 3 most-influential KDD 2025 paper): prompts LLM with task description, traffic state, and prior knowledge; CoT picks next signal phase. Outperformed 9 baselines and 10 advanced LLMs over ten real/synthetic datasets — [arXiv 2312.16044](https://arxiv.org/abs/2312.16044)
- Exact numbers (average travel time, lower is better): **Jinan**: LightGPT (Llama2-13B backbone) 274.03s vs Advanced-CoLight (SOTA RL) 274.67s vs GPT-4 275.26s vs ChatGPT-3.5 536.79s (3.5 hallucinates badly). **Hangzhou**: Advanced-CoLight 304.47s, LightGPT 310.78s, GPT-4 318.71s, unfinetuned Llama2-70B 357.95s — [arXiv html v5](https://arxiv.org/html/2312.16044v5)
- Transfer: LightGPT shows "remarkable transferability across all datasets" on unseen road networks while RL methods decline notably after transfer; on New York (196 intersections) LLMLight's average waiting time is ~50% shorter than top RL baselines (RL keeps marginally lower ATT in some cases); under extreme high traffic, RL degrades below the Maxpressure heuristic while LightGPT stays superior; a finetuned Qwen2-0.5B LightGPT beats much larger unfinetuned models — [arXiv html v5](https://arxiv.org/html/2312.16044v5)
- **CoLLMLight** (ICLR 2026, same HKUST-GZ group): first *cooperative* LLM-agent framework for network-wide TSC; asynchronous architecture — slow spatiotemporal cooperative reasoning runs off the control path, its guidance is cached and injected as context into real-time signal decisions; adaptive reasoning-chain depth by traffic complexity; RL-refined with rewards penalizing excessive reasoning. Claims consistent outperformance of existing methods on four real-world networks (numbers not extracted) — [arXiv 2503.11739](https://arxiv.org/pdf/2503.11739), [ICLR 2026](https://iclr.cc/virtual/2026/poster/10010107)
- **ProcessLight** (2026): process supervision (step-level reward) for LLM-based TSC — the lineage's current frontier — [arXiv 2609.22746](https://arxiv.org/pdf/2609.22746)
- **LLMs as Traffic Control Systems at Urban Intersections** (2024): GPT-mini, Gemini, Llama tested on conflict detection/resolution at four-leg intersections; fine-tuned GPT-mini: **83% overall accuracy, F1 0.84, ROUGE-L 0.95 (conflict ID), 0.94 (priority assignment), 0.92 (waiting-time optimization)**; outputs delivered as yield/slow/stop advisories to drivers/AVs via wireless, Python simulation as ground truth — [arXiv 2411.10869](https://arxiv.org/pdf/2411.10869)
- **LIDSA** (2026): cognitive arbitration for *signal-free* autonomous intersection management; LLM assigns roles CLEAR / YIELD / SHARE under a fixed precedence order, breaking remaining conflicts into CLEAR/YIELD pairs via successive tiebreakers (priority class -> weighted wait -> queue pressure); emergency vehicles trigger strict preemption — [arXiv 2605.12321](https://arxiv.org/pdf/2605.12321)
- A vehicle-infrastructure cooperative framework (2025) generates a **global vehicle pass order** through intra-group consensus alignment and inter-group divergence-resolution negotiation by LLMs — [arXiv 2503.16552](https://arxiv.org/pdf/2503.16552)

### Inferences
- What transfers to robot-swarm intersections: (1) the asynchronous slow-reasoner/fast-controller split in CoLLMLight is structurally the same as our Layer-2/Layer-1 split and validates caching LLM guidance as context rather than blocking; (2) LIDSA's CLEAR/YIELD/SHARE role vocabulary with deterministic tiebreakers is a direct template for making our M2 strategy enum arbitration auditable; (3) the LLMLight evidence pattern — parity in-distribution, large wins off-distribution — is the right framing for our prereg claims (do not promise throughput wins over tuned baselines in-distribution).
- The ChatGPT-3.5 536.79s vs GPT-4 275.26s gap (~2x travel time) is the cleanest published evidence that model capability, not prompt engineering, dominates TSC quality — relevant to our model-wiring ruling (sonnet / qwen3-vl / gpt-5.1).

### Gaps
- CoLLMLight's exact ATT/queue deltas vs CoLight/MPLight were not extracted (paywall-free HTML exists; worth a follow-up fetch if numbers are needed for the report).
- No TSC paper grounds decisions through anything like Nav2; all grounding is "emit phase/role, simulator applies it" — the grounding problem we face (command -> Nav2 behavior tree) is harder than anything in this lineage.

## Warehouse/AGV-specific LLM coordination (DeepFleet and after): congestion handling specifics?

### Takeaway
DeepFleet is a *predictive world model* (next-fleet-state prediction), not an LLM coordinator — four architectures were benchmarked, robot-centric and graph-floor won, and congestion handling is a downstream application (forecasting, adaptive routing) with a press-claimed ~10% travel-efficiency gain; beyond DeepFleet, warehouse congestion work in 2025–2026 remains RL/optimization-dominated with essentially no published LLM-in-the-loop AGV congestion controller.

### Cited Findings
- **DeepFleet** (Amazon, Aug 2025): a suite of foundation models trained on fleet movement data (positions, goals, interactions) from **hundreds of thousands of robots** in Amazon warehouses. Four architectures: **Robot-Centric (RC)** — autoregressive decision transformer on per-robot neighborhoods; **Robot-Floor (RF)** — cross-attention between robots and floor; **Image-Floor (IF)** — convolutional encoding of the full fleet as a multi-channel image; **Graph-Floor (GF)** — temporal attention + GNN for spatial relations. Finding: **RC and GF "show the most promise"**, attributed to asynchronous robot state updates and localized interaction structure — [arXiv 2508.08574](https://arxiv.org/abs/2508.08574)
- Intended applications: congestion forecasting, adaptive routing, proactive rescheduling; Amazon's press claim is ~**10% robot travel-efficiency improvement**, fleet now >1M robots, rerouting "on the fly to avoid jams" — [Digital Commerce 360](https://www.digitalcommerce360.com/2025/07/03/amazon-deepfleet-ai-model-for-robotics/) (press, not peer-reviewed)
- Amazon Science's own framing: "Predicting congestion in fleets of robots" — i.e., the published contribution is congestion *prediction*, with control left to existing planners — [Amazon Science blog](https://amazon.science/blog/predicting-congestion-in-fleets-of-robots)
- Post-DeepFleet warehouse congestion work found is non-LLM: GNN-policy task scheduling for lifelong MAPD improving throughput up to 10% over the 2024 League of Robot Runners winning scheduler at up to 500 agents — [papers.cool 2512.03194](https://papers.cool/arxiv/2512.03194); hierarchical transformer RL for AGV scheduling — [CityU](https://scholars.cityu.edu.hk/en/publications/efficient-agv-scheduling-in-warehouses-via-hierarchical-transform/); multi-task PPO with CNN–GNN fusing local congestion patterns with warehouse topology — [DOAJ, Ain Shams Eng. J. Jan 2026](https://doaj.org/article/8b217e8a8a2848eaaadb9eefd96b2dba)
- The closest LLM-in-warehouse result is **LLMDR** (see next section), whose headline numbers are on a *warehouse map*: DHC 1% -> 83% success at 64 agents with LLM deadlock resolution — [arXiv 2503.00717](https://arxiv.org/html/2503.00717v1)

### Inferences
- The substance we may have missed on DeepFleet: it is explicitly *not* semantic reasoning — no language, no VLM, no strategy selection. Its evaluation is next-state prediction fidelity, and the RC/GF architectural lesson (asynchronous, locality-structured state beats global image encodings) is about representation, not decision-making. It neither competes with nor validates a VLM Layer-2; it would slot in as a congestion *forecaster feeding* a Layer-2 trigger.
- The absence of published LLM-based AGV congestion controllers means our M2/M3 pipeline occupies a genuinely unpopulated niche between TSC-style LLM arbitration (LIDSA) and MAPF-style LLM deadlock repair (LLMDR).

### Gaps
- DeepFleet's paper-level evaluation metrics/numbers (prediction error, horizon) were not extracted from the abstract page; the full PDF (2508.08574v2) would be needed. No peer-reviewed number for the "10% efficiency" claim exists — press only.
- No published account of how (or whether) DeepFleet predictions are actually wired into Amazon's live routing.

## Work scoring the model's ORDERING decisions (who goes first) against optimal or convention baselines — plus deadlock-resolution numbers and grounding

### Takeaway
GameChat is the one paper that directly scores who-goes-first correctness: LLM negotiation lifts priority-respecting ordering from 50% (coin-flip, game-theory-only) to 100% at a cost of ~0.2s makespan, grounding the decision as leader/follower velocity constraints inside MPC-CBF; LLM deadlock-resolution work (2404.06413, LLMDR) shows large success-rate gains over grid/learnt planners but scores goal-reaching, not ordering optimality.

### Cited Findings
- **GameChat** (2025): multi-LLM dialogue (gpt-4o-mini via OpenAI API) for navigation in constrained spaces. Agents converse to consensus on task priority; higher-priority agent becomes leader, lower-priority agent minimally slows; roles enforced as velocity constraints in MPC with CBFs; default fallback is a game-theoretic strategy with subgame-perfect-equilibrium property. **Intersection scenario: no-LLM GameChat 11.6s makespan with 50% priority-first rate; with communication 11.8–11.87s and 100% priority-first; SMG-CBF baseline 15.0s / 50%; hardcoded wait baseline 18.4s. Doorway: 11.27s -> 11.53–11.6s with 100% priority accuracy. Negotiation latency 2.77s +/- 0.44s, completing before agents must stop** — [arXiv 2503.12333](https://arxiv.org/html/2503.12333v1); abstract claims >35% time reduction vs naive and >20% vs SOTA baseline — [abs](https://arxiv.org/abs/2503.12333)
- **Foundation Models to the Rescue** (2024, deadlock resolution in connected MRS): hierarchical — GPT-4/Claude-class model outputs `{"Leader": id, "Waypoints": [[x,y],...]}`; a GNN-based distributed low-level controller enforces safety and connectivity while the leader pulls the formation out of deadlock. Tested at N=5 (rooms), N=25 and N=50 (mazes): GPT-4 LLM ~80–85% goal-reach vs A* ~60–65% and random <50% at N=5; LLMs beat VLMs on reach rate; VLM token use stays ~1000 while LLM prompts blow past context windows at N=50 with 375 obstacles; deadlock trigger = mean velocity <0.2 with mean goal distance >0.4; validated on 4 TurtleBot3s where the low-level controller alone deadlocks and the hierarchy completes — [arXiv 2404.06413](https://arxiv.org/html/2404.06413v2)
- **LLMDR** (2025): LLM detects deadlock from movement patterns in a detection window ("no movement" or "wandering"), groups deadlocked agents within 2 Manhattan distance, assigns "leader" or "radiation" strategies; LLM-set agent/action priorities feed **PIBT**, which produces collision-free one-step moves, re-applied iteratively. **Warehouse map, 64 agents: DHC 1% -> 83% success with LLMDR; DCC 16% -> 74%; random32, 64 agents: DCC 90% -> 100%.** GPT-4o beats GPT-3.5-turbo on episode length. Authors flag LLM computational cost as the real-time blocker — [arXiv 2503.00717](https://arxiv.org/html/2503.00717v1)
- Prioritized CBS variant where the **LLM decides which robot receives priority** at each detected conflict on candidate paths — [arXiv 2603.16537](https://arxiv.org/html/2603.16537v1)
- LIDSA's arbitration (CLEAR/YIELD/SHARE with deterministic tiebreakers) is an ordering mechanism but is evaluated as intersection performance, not ordering-vs-optimal — [arXiv 2605.12321](https://arxiv.org/pdf/2605.12321)
- Multi-robot LLM navigation where robots converse until consensus on whose task has higher priority, using priority knowledge explicitly "to break symmetry" — [survey, arXiv 2604.00061](https://arxiv.org/pdf/2604.00061)
- Crowd/evacuation (adjacent, thin): LLM agent simulation of ~13,000 evacuating agents calibrated against an observed May 2025 stadium egress (social regrouping redesign) — [arXiv 2509.21868](https://arxiv.org/pdf/2509.21868); RESCUE (ICCV 2025 Highlight) is social-force + gait, not LLM-decided flow control — [project page](https://cic.tju.edu.cn/faculty/likun/projects/RESCUE/)

### Inferences
- GameChat's 50%->100% priority-first result is the closest published analogue to our presentation-order finding: without language-mediated tie-breaking, the game-theoretic layer picks who goes first at chance relative to task priority — the same "ordering is the weak link" diagnosis we reached for gpt-4o, solved there by making priority an explicit negotiated variable rather than an emergent choice. Their 2.77s negotiation inside an ~11.6s maneuver also gives a concrete latency budget precedent for Layer-2.
- Across all of (B), grounding follows one of three patterns: (1) role/priority token -> classical solver (PIBT, CBS, precedence rules) — LLMDR, LIDSA, prioritized-CBS; (2) leader+waypoints -> learned safe low-level controller (GNN) — 2404.06413; (3) role -> constraint in MPC-CBF — GameChat. Our M3 RAG->Nav2-command grounding is a pattern (1)/(3) hybrid; nobody re-plans trajectories with the LLM directly, which supports keeping M2 output at the strategy/role level.
- Measured quantities in (B) are: makespan/time-to-goal (GameChat), goal-reach/success rate (2404.06413, LLMDR), ATT/queue/waiting time (TSC lineage), throughput (MAPD schedulers). Nobody measures *clearance time of a congestion event* as a primary metric — our congestion-onset-to-clearance framing would be a differentiating measurement.

### Gaps
- No paper scores LLM ordering decisions against a *provably optimal* schedule (e.g., optimal MILP pass order) or against social-convention baselines (right-hand rule, FCFS) — GameChat scores against task priority only. This confirms the niche for our ordering-vs-optimal evaluation.
- No cross-provider ensemble result anywhere in (B); no debate-based congestion decision result; no published latency-vs-quality Pareto for judge-verifier layers in a live control loop.
- Reach-rate figures for 2404.06413 at N=25/50 were only available as chart-level approximations ("~80–85%"), not table values.
