# Closed-Loop Feedback, Replanning, and Memory Techniques for LLM/VLM Multi-Robot Coordination (2024–2026)

Scope: techniques where execution feedback flows back into the model to improve later decisions within (and across) an episode. Focus on applicability to a centralized coordinator that re-analyzes a congestion scene every few seconds (0.5–2 Hz slow loop over a 20–50 Hz fast loop). Excludes GAVEL, PAAI, SyncPlan, RoCo as baselines already known (RoCo appears only as the benchmark substrate for a newer reflection paper).

Note on provenance: entries marked "(search-summary figures)" come from search-engine digests of the paper rather than a direct read of the PDF; figures should be spot-checked against the paper before citing in a prereg or publication.

## Q1: Does injecting the previous failed attempt / outcome into the next prompt measurably improve resolution?

### Takeaway
Yes — across every 2024–2026 system found, feeding structured failure context (what failed, and ideally *why*) back into the next query yields large measured gains (roughly +25 to +40 points success rate, or 3–4x fewer infeasible actions), and the *explanation* component specifically is shown to matter beyond the bare failure label. The literature supports bounded-depth failure context (the failure + its analysis), not long transcripts — over-long histories actively degrade MAPF-style coordination.

### Cited Findings
- LLM-MAPF (Chen, Koenig, Dilkina, USC, Feb 2024): collisions are detected externally and returned as explicit error messages ("Agent (1,2), (4,5) are colliding"); the LLM regenerates the step until valid, capped at 5 attempts per timestep. Step-by-step generation with this conflict feedback substantially outperformed one-shot planning, which "failed with as few as 4 agents." Success on an empty 8x8 map: 100% (2 agents) → 60% (16 agents); room map 100% → 20% (8 agents); maze 0% even with 2 agents. 77% of failures were oscillation (agents dithering in one map region), i.e., reasoning limits, not constraint-violation limits — [arXiv:2401.03630](https://arxiv.org/html/2401.03630v2)
- LLM-MAPF history-depth evidence: 128K-context models significantly outperformed 8K variants, and the "restart" mechanism (wiping conversation history every 7–10 steps when tokens overflow) caused agents to "completely forget that they have been to certain locations," directly explaining degradation on harder maps — [arXiv:2401.03630](https://arxiv.org/html/2401.03630v2)
- LERa — Look, Explain, Replan (Pchelintsev et al., MIPT/Sber/AIRI, 2025): a modular VLM replanner that takes only a raw RGB image, the failed action, the instruction, and the current plan. Full pipeline improves success by >40% over baselines (incl. a one-step VLM replanner); 49.55% on ALFRED-ChaOS, 94.06% on VirtualHome-ChaOS, +67% on PyBullet tabletop, 15/18 real xArm6 trials. Ablations: Replan-only gives minimal improvement; adding the Explain (error-reasoning) step is what drives gains in complex environments — [arXiv:2507.05135](https://arxiv.org/html/2507.05135v2)
- ReplanVLM (2024): VLM-based replanning with internal (pre-execution) and external (post-execution) error-correction loops; average success 94.2% for the full framework, falling to 87.1% / 78.5% with one correction loop removed and 68.6% with both removed (search-summary figures; ablation label naming ambiguous in the digest) — [arXiv:2407.21762](https://arxiv.org/pdf/2407.21762)
- Guardian (2025): a VLM error detector for robotic planning/execution that, upon detecting failure, "injects back the failure reasoning trace to help with replanning, and retries up to three times" — i.e., the same failure-trace-injection pattern adopted as a design primitive (search-summary) — [arXiv:2512.01946](https://arxiv.org/pdf/2512.01946)
- RAG-Modulo (Jain, Jermaine, Unhelkar, Rice, 2024): stores interaction tuples including the previous action and its *feasibility feedback*; retrieving these as in-context examples cut infeasible actions from 13.98 to 3.74 per episode (BabyAI-BossLevel) and from 21.73 to 7.17 (ALFWorld) vs LLM-Planner, while success rose 0.24→0.57 and 0.17→0.54 — [arXiv:2409.12294](https://arxiv.org/html/2409.12294v1)
- A prompt-optimization study on VLM failure handling: optimized failure-context prompts improved VLMs' failure detection, issue analysis, and recovery-plan generation by 5.8 / 5.8 / 7.5 points respectively, and motion-level position-error correction accuracy by 65.78% vs unoptimized prompts (search-summary figures; source digest did not isolate the exact paper — likely the unified VLM+reactive-planner+behavior-tree failure-handling framework) — [arXiv:2503.15202](https://arxiv.org/pdf/2503.15202)

### Inferences
- Our "most recent attempt + most recent failed attempt" depth policy sits between the two failure modes the literature documents: (a) no failure context → minimal improvement (LERa's Replan-only arm, LLM-MAPF one-shot), and (b) unbounded history → context overflow and forced resets that destroy performance (LLM-MAPF restart finding). Nothing found contradicts the policy; LERa additionally suggests attaching an *explanation of why the attempt failed* (not just the raw failed command + outcome) is the highest-leverage addition.
- For a congestion coordinator, the LLM-MAPF oscillation finding (77% of failures) is a direct warning: without memory of previously tried-and-failed strategies, per-step re-query loops oscillate. Injecting the failed strategy by name ("yield robot_1 was issued and did not clear the jam within T seconds") is exactly the anti-oscillation mechanism these papers operationalize.

### Gaps
- No paper was found that ablates failure-context *depth* specifically (1 vs 2 vs k past attempts) in a robot setting; the depth-policy evidence is indirect (context-length and restart effects in LLM-MAPF, token-pruning in BRACE). Our depth policy is consistent with but not directly validated by the literature.
- ReplanVLM and the prompt-optimization numbers come from search digests, not a direct paper read; exact ablation conditions need verification.

## Q2: Plan stability / churn — who measures it, and what supersession policies win?

### Takeaway
Plan stability is being rediscovered in the LLM-agent era under new names ("budgeted replanning," "belief-action gap," "repair vs edit"): 2026 work measures replan counts, edit distance, and latency tails, and converges on *scoped* repair (revise only invalidated plan legs) plus explicit budgets, rather than full re-plans — but no single strategy dominates on all of feasibility, preservation, and cost.

### Cited Findings
- Classical anchor: Fox, Gerevini, Long, Serina, "Plan stability: replanning versus plan repair" (2006) — plan repair achieves more stability than replanning and produces repaired plans more efficiently — [Strathclyde](https://strathprints.strath.ac.uk/2776/)
- "Replan, Repair, or Edit?" (2026): a unified empirical evaluation of LLM travel agents revising itineraries under resource disruptions; finds hierarchical and local repairs make fewer edits than full replanning, strategies have distinct computational costs, and "no strategy dominates all dimensions, so selection should balance feasibility recovery, preservation, and computational cost" — the closest existing study to a pending-legs-only vs full-supersession comparison — [arXiv:2609.19654](https://arxiv.org/pdf/2609.19654)
- BRACE — "When Replanning Becomes the Bottleneck: Budgeted Replanning for Embodied Agents" (ICML 2026): frames replanning as a budgeted control loop — decide *whether* to replan, select a replanning *mode*, and allocate an explicit token budget and latency SLO. Key observation: replanning latency develops heavy tails and misses real-time deadlines even when task success stays high. Results: 62–92% token reduction across Meta Habitat, RoboFactory, AirSim; SLO-violation rates cut from 85.5–100% down to 4.7–50%; in harder settings 80% success with 4.6% SLO violations, where open-loop, frozen-plan, and plain event-triggered baselines fail. Includes E-RECAP, cost-aware progressive token pruning of the replanning context — [arXiv:2608.01428](https://arxiv.org/pdf/2608.01428)
- Bayesian Partner Modelling for LLM coordination (Aug 2026): introduces the "belief-action gap" (fraction of decisions where an agent with a correct partner estimate still executes a non-complementary skill) as a stability-adjacent coordination metric, and reduces replans by an order of magnitude vs heuristic triggers — [arXiv:2608.18490](https://arxiv.org/abs/2608.18490)
- "Learning When to Plan" (2025): frames when-to-replan as test-time compute allocation; frequent replanning is computationally expensive, induces "overthinking," and "constant replanning can introduce noise and behavioral instability in long-duration tasks" — [arXiv:2509.03581](https://arxiv.org/html/2509.03581v1)

### Inferences
- For our coordinator, the actionable synthesis: (1) measure churn explicitly (replans per episode, command-supersession count, and a belief-action-gap analogue: "coordinator issued a new strategy while the previous one was still progressing"); (2) prefer superseding only the pending legs of a grounded command sequence, per the repair-vs-replan consensus; (3) impose a replan budget per congestion event — BRACE's latency-tail finding maps directly onto a 0.5–2 Hz loop where one slow VLM call can blow the cycle.
- The travel-agent study is the only head-to-head supersession-policy comparison found; its "no dominant strategy" result argues for making supersession policy a measured experimental factor in our prereg rather than a fixed design choice.

### Gaps
- Nobody measures plan churn for *centralized multi-robot congestion commands* specifically; the closest substrates are itinerary revision (single-agent, symbolic) and Overcooked (2-agent).
- Fox et al.'s plan-stability *metric* (action-set distance between old and new plan) has no established LLM-era robotic equivalent; we would have to define one.

## Q3: Reflexion / self-refine lineage in embodied multi-robot settings — real gains or only text games?

### Takeaway
The Reflexion pattern (verbalize failure → store reflection → condition next trial) has crossed into single-robot *real hardware* with measured gains (LERa's xArm6, VLM-critic/LLM-actor behavior-tree refinement on mobile robots), but for *multi-robot* teams the measured gains remain simulation-only (RoCoBench, metacognitive frameworks); no real-hardware multi-robot Reflexion result with quantitative deltas was found.

### Cited Findings
- Reflexion (Shinn et al., 2023): agents verbally reflect on task feedback and keep reflective text in an episodic memory buffer to improve subsequent trials — the lineage root; evaluated in simulated/text environments with ground-truth or hand-engineered observations, not physical embodiment — [arXiv:2303.11366](https://www.arxiv.org/pdf/2303.11366v2)
- "Integrating Retrospective Framework in Multi-Robot Collaboration" (Liang et al., Feb 2025): two LLMs — an actor running real-time collaborative discussion among robots (RoCo-style) and a critic that retrospectively evaluates executed outcomes, critiques prior plans, and proposes improved alternatives. Evaluated on RoCoBench measuring success rates, average steps, and *re-planning attempts*; reports "notable performance increase in almost all tasks" vs baselines. Abstract-level only; per-task numbers not extracted — [arXiv:2502.11227](https://arxiv.org/abs/2502.11227)
- "Think, Reflect, Create" / REFLEX — metacognitive learning for zero-shot multi-robot planning with LLMs (2025): skill decomposition + self-reflection; a validation mechanism detects planning failures and triggers reflection; explicitly labeled an "early-stage framework" — [arXiv:2505.14899](https://arxiv.org/pdf/2505.14899)
- MHRC (2024): closed-loop *decentralized* multi-heterogeneous-robot collaboration with LLMs — closed-loop feedback in multi-robot sim — [arXiv:2409.16030](https://arxiv.org/pdf/2409.16030)
- Real-hardware single-robot transfer: a verbal-RL framework where executable behavior trees are iteratively refined by an LLM actor using structured natural-language feedback from a VLM critic observing the *physical* robot and execution traces (search-summary; likely "A Pragmatist Robot," 2025) — [arXiv:2507.16713](https://arxiv.org/pdf/2507.16713); and LERa's 15/18 real xArm6 trials — [arXiv:2507.05135](https://arxiv.org/html/2507.05135v2)
- Bilevel Coordinated Reflection (2026): extends reflection "from the individual to the collective level" via role specialization and consensus among multiple LLM agents, targeting the cognitive-bottleneck/hallucination problem of single-model reflection — game-theoretic, not embodied — [arXiv:2609.02750](https://huggingface.co/papers/2609.02750.md)
- MALLVI (2026): distributed LLM-planning + VLM-monitoring manipulation framework with a dedicated "reflector agent" providing targeted feedback for error recovery — multi-agent architecture, manipulation domain — [arXiv:2602.16898](https://arxiv.org/html/2602.16898v1)

### Inferences
- For our setting the honest read: within-episode reflection (critic-style retrospective evaluation of the last strategy's outcome) has multi-robot *sim* evidence (2502.11227 on RoCoBench) and single-robot *hardware* evidence; a centralized congestion coordinator doing retrospective critique of its own superseded strategies would be novel-ish but well-precedented in pattern.
- The actor/critic split (separate critique call, not just appending raw outcome) is the common structural choice across 2502.11227, MALLVI, and the VLM-critic BT work — relevant to whether our M2 prompt should include a self-critique section or a separate cheap critique pass.

### Gaps
- No real-hardware multi-robot Reflexion-lineage result with quantitative deltas found (2024–2026). This appears to be a genuine open slot in the literature, not a search failure.
- 2502.11227's per-task numbers vs RoCo were not retrievable from the abstract; the full PDF needs reading before citing effect sizes.

## Q4: Event-triggered re-planning vs fixed-period re-query — direct comparisons?

### Takeaway
Direct comparisons now exist (2025–2026) and consistently favor event-triggered: a contradiction-triggered coordinator matched periodic replanning's reward with ~20x fewer replans (2.0 vs 43 per episode), and budgeted/learned triggers beat both fixed-period and naive event triggers on latency and cost — supporting our congestion-timeout trigger over a fixed re-query period.

### Cited Findings
- Bayesian Partner Modelling (Overcooked, Aug 2026): interrupts the current skill only when a partner's actions *contradict* the inferred skill. Periodic-10 (replan every 10 env steps) achieved comparable reward only by replanning far more often — 43 replans/episode vs 2.0 for the contradiction trigger; generic heuristics trigger tens-to-100+ replans/episode vs low single digits for the selective trigger; "an order of magnitude fewer replans than heuristic methods" — [arXiv:2608.18490](https://arxiv.org/abs/2608.18490)
- BRACE (ICML 2026): goes beyond binary event-vs-periodic — a budgeted controller choosing whether/how/with-what-budget to replan outperforms open-loop, frozen-plan, and plain event-triggered baselines; 62–92% token reduction, SLO violations 85.5–100% → 4.7–50% — [arXiv:2608.01428](https://arxiv.org/pdf/2608.01428)
- "Learning When to Plan" (2025): learns the trigger as test-time compute allocation; documents that frequent planning improves accuracy but causes overthinking and behavioral instability — [arXiv:2509.03581](https://arxiv.org/html/2509.03581v1)
- CoMuRoS-style hierarchical heterogeneous-team framework (Nov 2025): Task Manager LLM allocates subtasks; each robot's local LLM monitors events continuously; *task failures or user-intent changes* trigger replanning (event-driven by design, no periodic arm reported) — [arXiv:2511.22354](https://arxiv.org/pdf/2511.22354)
- MHRC (2024) similarly uses closed-loop event-driven replanning in decentralized multi-robot collaboration — [arXiv:2409.16030](https://arxiv.org/pdf/2409.16030)

### Inferences
- Our architecture (M5 triggers M2→M3 on congestion *timeout*, not on a clock) is the pattern the 2026 comparisons validate. The refinement they suggest: add a *contradiction* trigger — re-query early if robot motion contradicts the issued strategy's expected effect (e.g., yielded robot not actually yielding), rather than waiting out the full timeout; and a *budget* — cap replans per congestion event to prevent the oscillation failure mode.
- The 43-vs-2.0 result also implies cost: at 0.5–2 Hz, periodic re-query of a VLM is the expensive arm; event-triggering is what makes frontier-model coordination economically viable per episode.

### Gaps
- All direct comparisons are in sim (Overcooked, Habitat, RoboFactory, AirSim); none in a warehouse-congestion or Nav2-style navigation stack.
- No study compares trigger designs for a *centralized* coordinator watching N robots (all event-trigger work found is per-agent or 2-agent).

## Q5: Cross-episode memory (learned priors, retrieved past cases, RAG over episodes) for coordination — 2024–2026 robot results?

### Takeaway
Cross-episode retrieval demonstrably helps single-agent embodied tasks (RAG-Modulo: success more than doubles; ViReSkill: lifelong skill memory for robot replanning), and 2025–2026 produced memory architectures (MEMORA/EAM, MemER, robotmem) — but no published 2024–2026 result applies RAG-over-past-episodes to *multi-robot coordination* specifically; that remains open.

### Cited Findings
- RAG-Modulo (2024): stores (goal, previous action, feasibility feedback, observation) → action tuples from past episodes; retrieves top-K by embedding similarity as in-context examples. Success: 0.24→0.57 (BabyAI-BossLevel), 0.17→0.54 (ALFWorld-unseen); infeasible actions cut ~3–4x; removing memory costs 0.20 success — performance grows as memory populates across episodes — [arXiv:2409.12294](https://arxiv.org/html/2409.12294v1)
- ViReSkill (2025): vision-grounded replanning with a *skill memory* — successful recovery plans are stored and reused in later episodes, so the robot doesn't re-derive fixes it already found (lifelong robot learning framing) — [arXiv:2509.24219](https://arxiv.org/html/2509.24219v1)
- MEMORA / Embodied Action Memory (2026): formalizes experience as persistent memory state with a formation–consolidation–retrieval lifecycle over four typed stores (Environment, Entity, Activity, Inferred Knowledge) — [arXiv:2607.14252](https://www.alphaxiv.org/abs/2607.14252.md)
- MemER (2025): hierarchical policy whose high-level selects and tracks task-relevant keyframes from past experience to condition low-level execution — robot memory, single-agent — [arXiv:2510.20328](https://arxiv.org/html/2510.20328v1)
- Survey coverage: "From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms" (2026) — [arXiv:2605.06716](https://arxiv.org/pdf/2605.06716); "Large Language Models for Multi-Robot Systems: A Survey" (2025) — [arXiv:2502.03814](https://arxiv.org/pdf/2502.03814)
- Multi-robot task planning with distributed on-site knowledge (2025): LLM replans multi-robot retrieval tasks using per-robot accumulated local knowledge plus succeed/fail labels and contextual observations fed back as input — within-episode knowledge accumulation, not cross-episode retrieval — [arXiv:2509.12838](https://arxiv.org/pdf/2509.12838)

### Inferences
- For our M3 RAG layer, RAG-Modulo is the strongest template: its retrieved unit (state + attempted action + feasibility outcome) maps almost one-to-one onto "congestion scene signature + issued strategy + resolution outcome," and its infeasible-action reduction is precisely the failure class our M3 feasibility gate targets. Extending the knowledge base with *episode outcome records* (scene → strategy → resolved/failed in T seconds) would be a straightforwardly literature-supported upgrade, and the multi-robot version appears unpublished — a potential contribution slot.
- The typed-store designs (MEMORA) suggest separating "what the warehouse is like" (semantic priors: this aisle jams under convoy) from "what happened in this episode" (episodic) — matching our existing split between the knowledge base and failure-context injection.

### Gaps
- No 2024–2026 paper found that retrieves *past multi-robot coordination episodes* to condition a coordinator's next decision; evidence is single-agent (BabyAI/ALFWorld/manipulation). Transfer of the measured effect sizes to congestion coordination is an extrapolation.
- robotmem (open-source episodic memory across episodes) surfaced only via a Zenodo record (March 2026) with no peer-reviewed evaluation found — treat as tooling, not evidence.
- No paper found on learned priors over congestion/deadlock classes specifically.
