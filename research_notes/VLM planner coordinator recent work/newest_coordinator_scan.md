# Newest VLM/LLM Multi-Robot Planner/Coordinator Work (mid-2026 onward) — Freshness Pass of 2026-10-04

Scope: NEW work and NEW citers only, beyond the 2026-10-01 novelty scan (GAVEL, Physical Agentic AI, SyncPlan, Seeing-Saying-Solving, COMRES-VLM, EFLUX, Virtual Traffic Lights, Garg et al., LLMDR, Oxford CCTV). Flags: **VERIFIED** = read from primary source (arXiv page/HTML or Semantic Scholar record); **UNVERIFIED** = search-snippet or secondary only.

## KQ1: Anything new (Sep–Oct 2026) where a VLM emits full multi-robot plans or coordinates congestion/deadlock resolution?

### Takeaway
Two substantive new entries: **Safe Multi-Robot Coordination via VLM-LLM Reasoning and Reachability Analysis (arXiv:2609.27816)** — the closest new threat, a VLM+LLM+formal-verification-gate multi-robot coordinator, but ego-camera, 2 robots, audit-and-REJECT (no repair), no congestion/deadlock scenarios, no baselines — and **DuoMind (arXiv:2610.02161)** — per-robot VLM orchestrators for multi-robot manipulation, distributed, no central plan, no congestion. Neither touches overhead-camera congestion strategy, matched rule-based arms, or plan provenance. CoRL 2026 camera-readies and ICRA 2027 OpenReview submissions did not surface in searches (not visible).

### Cited Findings
- **"Safe Multi-Robot Coordination via VLM-LLM Reasoning and Reachability Analysis"**, Mohamed Dwedar, Ahmad Hafez, Alexander Jesser, Amr Alanwar, arXiv:2609.27816v1 [cs.RO] (ID series = Sep 2026; the HTML states v1 "submitted 18 August 2026" — minor date inconsistency, flag). **VERIFIED** (full HTML read) — [arXiv HTML](https://arxiv.org/html/2609.27816)
  - Architecture: VLM (Qwen2.5-VL) turns a Unitree Go2's **ego camera** frames into structured JSON scene descriptions; LLM (Qwen3) proposes symbolic directives from the enum {PROCEED, AVOID_AND_PROCEED, REPLAN, HOLD, STOP}; a zonotope reachability gate verifies obstacle avoidance, safe-corridor containment, and inter-robot separation predicates. Quote: "The proposal is not a command: it only selects which candidate control is submitted to the fourth gate."
  - **No congestion or deadlock scenarios** (test matrix: clear path, stairwell hazard, pedestrian, human tracking; 2 heterogeneous robots, hardware, lab).
  - **Audit without repair**: failed predicates ⇒ the motion is "rejected outright"; directives REPLAN/HOLD/STOP; "No incremental repair is reported." Aggregate audit stats only: **39.8% of commands approved, 60.2% withheld** over 1,953 decision cycles / 17,577 verified candidate arcs; no repaired-vs-replanned decomposition.
  - **No quantitative baseline**: "no published system reports a command-approval rate for a camera-less robot verified against a partner's perception" — capability-matrix comparison only (Table I, binary axes vs. SayCan, PaLM-E, RT-2, SMART-LLM, RTD, REFINE, SPARROWS, etc.).
  - **No persistent plan**: reactive 30 Hz loop, candidate paths "generated afresh each cycle."
- **"DuoMind: Enabling Distributed Multi-Robot Coordination with Semantic Communication"**, Hanchu Zhou et al., arXiv:2610.02161, published 2026-10-01. **VERIFIED** (abstract via arXiv API). Each robot runs a VLM-based orchestrator (high-level reasoning + inter-robot semantic messages) over a VLA executor; introduces **RoboPoly** benchmark for long-horizon multi-robot **manipulation**. Distributed (no central plan), no congestion/deadlock, no navigation/warehouse — [arXiv](https://arxiv.org/abs/2610.02161)
- **"Watch, Infer, Coordinate: Inferring Robot Partner Constraints for Zero-Shot Coordination"**, Ye et al., arXiv:2610.02170, 2026-10-01. **VERIFIED** abstract. Constraint inference from observed joint behavior for physically coupled manipulation; not a VLM planner; peripheral — [arXiv](https://arxiv.org/abs/2610.02170)
- **"Token Communication-Assisted Collaborative Embodied Artificial Intelligence"**, Yi & Liang, arXiv:2610.01826, 2026-10-01. **VERIFIED** abstract. Concept/framework article on token-level semantic communication among embodied agents; no planner provenance; peripheral — [arXiv](https://arxiv.org/abs/2610.01826)
- **"Large language models for multi-robot systems: a survey"**, Autonomous Robots, DOI 10.1007/s10514-026-10257-4. Existence **VERIFIED** (search result); content **UNVERIFIED** (Springer auth-redirect blocked fetch). Useful positioning citation once accessible — [Springer](https://link.springer.com/article/10.1007/s10514-026-10257-4)
- Broad arXiv cs.RO/cs.MA date-sorted sweeps (2026-08-01→2026-10-01, two query formulations, 45 newest-first abstracts reviewed) surfaced **no** overhead-camera VLM congestion coordinator, no Nav2-based VLM-vs-rule-based comparison, and no plan-provenance system — [arXiv listing via search tool](https://arxiv.org/list/cs.RO/2610)

### Inferences
- The field's Sep–Oct 2026 energy in multi-robot VLM work is going to (a) formal safety gates on LLM proposals (2609.27816) and (b) distributed VLM-orchestrator-over-VLA manipulation stacks (DuoMind). Centralized, scene-wide, congestion-focused planning over an overhead camera remains unoccupied.
- 2609.27816 is the paper to cite as "verification-gate convergence": it shares the audit instinct of claim 4 but explicitly lacks repair, provenance, congestion, and baselines.

### Gaps
- CoRL 2026 camera-readies and ICRA 2027 OpenReview submissions could not be inspected (no OpenReview listing surfaced in searches); coverage of those venues is incomplete.

## KQ2: New citers of the ten watched papers (anything scooping or converging)?

### Takeaway
Citation graphs are quiet. The only noteworthy citers: GAVEL itself cites COMRES-VLM; SyncPlan's sole citer ("Fresh Memory, Stale Plans") is a real conceptual neighbor of claim 5 but non-embodied. Nothing scoops any of the five claims.

### Cited Findings (all via Semantic Scholar Graph API, citers with publicationDate ≥ 2026-06-01; **VERIFIED** as citation records, contents checked only where noted)
- **Seeing-Saying-Solving (2505.13376)**: "Staying on Spec: Real-Time Monitoring under Uncertainty with a Maritime Case Study" (arXiv:2608.02811, 2026-08-03) and a biomedical STL-translation paper — both runtime-monitoring, unrelated — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2505.13376/citations)
- **LLMDR (2503.00717)**: no citers ≥ 2026-06 returned — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2503.00717/citations)
- **Garg et al. (2404.06413)**: "LLM-Enabled Human-in-the-Loop Control of Multi-UAV Teams under Communication Constraints", ICUAS 2026 (2026-06-15). Multi-UAV LLM control, HITL — converging on LLM multi-robot control but aerial/HITL, not congestion resolution; content not examined — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2404.06413/citations)
- **Virtual Traffic Lights (2511.07811)**: one citer, "Human-Aware Target Tracking and Navigation..." (arXiv:2609.07091, 2026-09-07) — unrelated — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2511.07811/citations)
- **Oxford CCTV (2606.06762)**: zero recent citers returned — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2606.06762/citations)
- **SyncPlan (2608.01652)**: one citer — "Fresh Memory, Stale Plans: Derivation Currency for Distributed LLM-Agent Memory", Evan Chen, Shiqiang Wang, Christopher G. Brinton, arXiv:2609.03340 (v1 2026-09-03, v2 2026-09-27). **VERIFIED** (abstract read). Maintains inherited persistent plans across distributed LLM agents and checks **"derivation currency"** (were the plan's recorded inputs still current) before protected actions; Planfence links plan steps "to their recorded inputs"; quantitative: 30 live five-agent workflows with a mid-run revision; stall overhead 143–237 ms per action across a 64× update-rate range. **Non-embodied** (software agents, no robots) — [arXiv](https://arxiv.org/abs/2609.03340)
- **COMRES-VLM (2509.26324)**: two citers — **GAVEL (2609.19315)** and "Semantic Area Graph Reasoning for Multi-Robot Language-Guided Search" (arXiv:2604.16263, 2026-04-17; multi-robot language-guided search, content not examined) — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2509.26324/citations)
- **GAVEL (2609.19315), Physical Agentic AI (2608.22657), EFLUX (2607.12050)**: zero citers in Semantic Scholar as of 2026-10-04 — [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2609.19315/citations)
- Caveat: final S2 existence re-checks for 2503.00717 / 2606.06762 hit HTTP 429 rate limits; "zero citers" for those two could partly reflect indexing lag rather than ground truth.

### Inferences
- "Fresh Memory, Stale Plans" is the one citer worth tracking: it legitimizes "plan staleness/currency of a persistent plan" as a measurable quantity, from the distributed-systems side. Claim 5's "embodied" qualifier is what keeps it clear.

### Gaps
- Google Scholar could not be queried directly (no scraping route); Semantic Scholar is the sole citation source, and its indexing of Aug–Sep 2026 arXiv papers lags.

## KQ3: Any system now reporting plan-preservation / repair / provenance statistics as experimental quantities?

### Takeaway
Still nobody reports **per-leg, three-way provenance (verbatim/repaired/defaulted)** as an experimental quantity, and nobody does it for multi-robot plans. GAVEL comes closest with a run-level, two-way repair-vs-replan ablation (single-agent); 2609.27816 reports audit (approve/withhold) fractions without repair.

### Cited Findings
- **GAVEL** (arXiv:2609.19315, "GAVEL: Graph World Models for Verified and Efficient Long-Horizon LLM Task Planning", Ruiyang Wang, Hao-Lun Hsu, Swarajh Mehta, Jiwoo Kim, Zhihao Dou, Miroslav Pajic, submitted 2026-09-16). **VERIFIED** (HTML read): Table I ablation — gavel-basic (graph repair only): **76.2% success, 1.00 LLM attempts**; full gavel (repair + LLM replanning): **91.8% success, 1.5 LLM attempts**; also "Graph-derived repair alone raises Qwen3-4B single-task success to 67.7%... Allowing LLM re-queries for unresolved semantic failures further raises this to 88.8%." Figure 3: "Failure breakdown... remaining failures after each pipeline step." **No per-action provenance logging, no explicit repaired-vs-replanned count table, no plan-preservation metric. Single agent, BEHAVIOR-1K / OmniGibson symbolic level** — [arXiv HTML](https://arxiv.org/html/2609.19315v1)
- **2609.27816** reports approval/withholding fractions (39.8% / 60.2%) and per-scenario gate approval rates (56.4% clear path, 0% stairwell, 37.9–47.7% dynamic) — audit statistics, explicitly **no repair** and no repair/replan decomposition. **VERIFIED** — [arXiv HTML](https://arxiv.org/html/2609.27816)
- **MDPI Robotics 15(4):80** (see KQ4): LLM decides **when** to initiate plan repair; abstract reports experimental validation "using real robots" but no quantitative preservation/provenance statistic at abstract level. **VERIFIED abstract** — [S2 record](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/robotics15040080)
- **MDPI MAKE 8(1):22** (see KQ4): iterated "local corrections" with re-validation; abstract-level quantities: "approximately 71–75% of tasks" completed "with a relatively low number of simulation iterations" — iteration counts are the closest thing to a repair-budget metric visible at abstract level. **VERIFIED abstract** — [S2 record](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/make8010022)
- **EvoPlan** (arXiv:2607.06724, Jul 2026): per search snippet, "a neural model generates and repairs candidate plans, while symbolic validation and data-derived temporal-logic constraints decide which candidates may be executed." **UNVERIFIED** (snippet only; not read; appears single-robot neuro-symbolic) — [arXiv PDF](https://arxiv.org/pdf/2607.06724)
- Targeted arXiv search (abs: "plan repair" OR "plan preservation" OR "minimal repair" + LLM/VLM, cs.RO/cs.AI/cs.MA, ≥2026-06-01, date-sorted) returned **no additional system** reporting such statistics — search tool result, 2026-10-04.

### Inferences
- Provenance-as-measurement remains open. GAVEL's framing ("reserves LLM replanning solely for errors requiring semantic reasoning") shows the two-way split is now a recognized design axis, but it is reported only as an ablation delta, not as logged per-leg provenance, and only single-agent.

### Gaps
- EvoPlan's actual repair statistics unexamined (ran out of call budget); recommend a one-paper follow-up read before the freeze if claim-2 wording cites "no prior repair statistics."

## KQ4: The two MDPI reading gates — MAKE 8(1):22 and Robotics 15(4):80

### Takeaway
**Gate partially cleared.** Both papers are now definitively identified with full bibliographic data and abstracts (via Semantic Scholar); **full texts remain inaccessible** after exhausting direct HTML, PDF endpoint, UA+referrer-spoofed curl, DOI redirect, and mirror/preprint searches (MDPI 403s everything; no arXiv/preprints.org/ResearchGate copy exists). Crucially, **both are single-robot PDDL pipelines** — neither touches multi-robot plans, congestion, or provenance taxonomies, so neither scoops claims 1–5; they are adjacent "LLM+symbolic verify/repair" work.

### Cited Findings
- **MAKE 8(1):22 = Drejc Pesjak, Jure Žabkar, "Robot Planning via LLM Proposals and Symbolic Verification"**, Machine Learning and Knowledge Extraction 8(1):22, DOI 10.3390/make8010022, published **2026-01-16**. **VERIFIED metadata+abstract** via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/make8010022). What it measures (abstract): hybrid Sense–Plan–Code–Act (SPCA): LLM → PDDL world description → heuristic symbolic planner → second LLM → code → syntactic (compile) + semantic (simulation) validation; "When errors are detected, local corrections can be applied and the process is repeated as necessary." Evaluated on OpenAI Gym MiniGrid + Gazebo UR5 arm with a task curriculum; "successfully completes approximately 71–75% of tasks across environments with a relatively low number of simulation iterations." The earlier presumption "repair-budget metrics" is **plausible but NOT confirmed** at abstract level — the abstract quantifies only completion rate and alludes to iteration counts. **Single robot arm / gridworld; no multi-robot, no provenance.**
- **Robotics 15(4):80 = Juan Diego Peña Narváez, Rodrigo Pérez-Rodríguez, Juan Carlos Manzanares, Francisco Miguel Moreno, Francisco Martín, "LLM-Assisted Plan Execution for Robots in Dynamic Environments"**, Robotics 15(4):80, DOI 10.3390/robotics15040080, published **2026-04-15**. **VERIFIED metadata+abstract** via [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/robotics15040080). What it measures (abstract): uses LLMs "to make informed plan repair decisions during robot operation" — an "LLM-based semantic evaluation heuristic" that tracks environmental features and forecasts hazards to decide **the appropriate moment to initiate repairs** of PDDL plans; "experimentally demonstrate the validity of our approach using real robots in environments where both the environmental conditions and the goals... change dynamically." The earlier presumption "plan preservation during replanning" is **NOT what the abstract claims** — the contribution is repair-timing (when to repair), not preservation accounting. Note: Francisco Martín is the PlanSys2 lead, so this is almost certainly a ROS 2/PlanSys2-family system (inference, flag as such). **Single-robot framing; no provenance statistics at abstract level.**
- Access attempts, all failed (**VERIFIED failures**, 2026-10-04): mdpi.com HTML → HTTP 403 (both); mdpi.com /pdf endpoints with Chrome UA + scholar.google.com referrer → 398–411-byte block pages, not PDFs; S2 openAccessPdf URL (version 1768569821) → same block; title-based web searches for preprint/mirror copies → none found ([search 1](https://arxiv.org/pdf/2607.06724) returned only unrelated neuro-symbolic planning papers; search 2 likewise).

### Inferences
- For the freeze: treat both gates as **cleared for threat purposes** (identity + scope established; both single-robot, neither reports multi-robot plan provenance or preservation statistics) but **not cleared for citation-of-numbers purposes** — any sentence quoting their internal metrics (iteration counts, repair-decision accuracy) must wait for full-text access (institutional proxy or author request).

### Gaps
- Full texts of both MDPI papers remain inaccessible from this environment; exact repair-iteration distributions (MAKE) and repair-decision evaluation metrics (Robotics) unknown.

## KQ5: GAVEL's evaluation — does it report a repaired-vs-replanned statistic (two-way provenance)? Does it force claim-2 wording?

### Takeaway
GAVEL **routes** two ways (deterministic graph-derived repair vs. LLM replanning for semantic failures) and **quantifies the split only as an ablation** (repair-only arm vs. full system; LLM-attempt counts), not as logged per-action provenance. It is single-agent, symbolic-level, non-multi-robot. Claim 2 wording should be tightened but survives.

### Cited Findings
- GAVEL abstract: "detect violations, and repair those whose corrections follow directly from the world model... reserves LLM replanning solely for errors requiring semantic reasoning"; BEHAVIOR-1K single-task success 41.2%→91.8%, multi-task 19.9%→92.6%, ~5.4% travel-distance reduction. **VERIFIED** — [arXiv abs](https://arxiv.org/abs/2609.19315)
- Evaluation section (**VERIFIED**, HTML): Table I — gavel-basic (repair only) 76.2% success / 1.00 LLM attempts vs. gavel (repair+replan) 91.8% / 1.5 LLM attempts; Figure 3 failure breakdown "after each pipeline step"; "does **not** provide an explicit table or percentage showing how many individual failures were repaired vs. returned to LLM"; "**No** per-action provenance tracking"; "**No** explicit plan-preservation metric"; single-agent, BEHAVIOR-1K symbolic level with a lightweight 2-D executor, validated in OmniGibson — [arXiv HTML](https://arxiv.org/html/2609.19315v1)

### Inferences
- **Forced wording change for claim 2 (moderate):** claim 2 can no longer read as "first to distinguish repaired from replanned plan content" in the generic sense — GAVEL already operationalizes a two-way repair/replan split with an ablation-level statistic. The defensible registered wording is: **first three-way per-leg provenance (verbatim / repaired / defaulted), logged per leg as an experimental quantity, with deterministic minimal repair, for multi-robot congestion plans** — four differentiators GAVEL lacks (per-leg logging; three-way incl. "defaulted"; multi-robot; embodied Nav2 congestion domain).
- Claims 1, 3, 5 face no new pressure: no new overhead-camera congestion taxonomy (claim 1); 2609.27816 pointedly lacks any quantitative baseline, so a matched two-arm VLM-vs-rule-based Nav2 comparison (claim 3) remains unoccupied; claim 5's nearest neighbor (Fresh Memory, Stale Plans) is non-embodied. Claim 4's "audited-AND-repaired with logged provenance" is differentiated from 2609.27816's audit-and-reject and from GAVEL's unlogged repair.

### Gaps
- GAVEL raw logs might allow recovering a repaired/replanned count even though the paper doesn't tabulate it; if the authors release code, re-check before asserting "GAVEL does not report the statistic" in print — the safe phrasing is "does not report a per-leg or per-failure repaired-vs-replanned tabulation."
