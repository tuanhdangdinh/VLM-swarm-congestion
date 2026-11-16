# Novelty-Threat Scan: LLM/VLM Multi-Robot Coordination, Congestion & Deadlock (2025-07 → 2026-10)

Scan date: 2026-10-01. Scope: new work threatening five pre-registration claims. Known prior art (Garg 2404.06413, LLMDR 2503.00717, Oxford CCTV 2606.06762, RoCo, COHERENT, SMART-LLM, LaMMA-P, VLMLight, COMRES-VLM 2509.26324) deliberately excluded except for follow-ups.

VERIFIED = abstract fetched directly from arXiv API or Semantic Scholar in this scan. UNVERIFIED = seen only in search snippets.

---

## KQ1: Any 2025–2026 paper where a VLM classifies congestion/deadlock TYPE from scene images and selects among discrete resolution strategies?

### Takeaway
No direct hit found. Nothing in the scan has a VLM looking at an overhead warehouse camera image, classifying the congestion/deadlock type semantically, and choosing from a discrete strategy taxonomy. The nearest neighbors are (a) EFLUX, which uses an LLM over a *structured scene representation* (not raw image) to choose among discrete formation actions, and (b) traffic-domain VLM congestion *detection* without robot actuation. Claim (1) appears to still be open as stated.

### Cited Findings
- **EFLUX: Elastic Multi-Robot Formation Navigation and Adaptation with Agentic LLMs** — arXiv:2607.12050, 2026-07-13, VERIFIED. LLM "extracts a structured scene representation and uses an LLM to reason jointly over both deformation actions, such as scaling and shearing, and reconfiguration actions, such as splitting and merging... reducing deadlock and navigation failures compared with baselines." Discrete strategy selection by an LLM for multi-robot deadlock avoidance — but formation navigation, structured (non-image) scene input, no congestion-type taxonomy, no warehouse. [arXiv](https://arxiv.org/abs/2607.12050)
- **Multi-Agent Visual-Language Reasoning for Comprehensive Highway Scene Understanding** — arXiv:2508.17205, 2025-08-24, VERIFIED. GPT-4o + Qwen2.5-VL-7B mixture-of-experts doing "traffic congestion detection" from highway camera video. Congestion *classification* from fixed-camera images by VLMs exists in the traffic domain, but with no robot/agent actuation and no resolution-strategy selection. Cite as related work, not a threat. [arXiv](https://arxiv.org/abs/2508.17205)
- **From Intents to Algorithms: Verified Algorithm Discovery for Transport Networks** — arXiv:2609.27386, 2026-09-23, UNVERIFIED (title/date from arXiv API listing only). Transport-network congestion + LLM, not embodied robots.
- **ParkSense (VLM for delivery parking)** — arXiv:2604.07912, 2026-04-09, UNVERIFIED listing hit for "congestion+VLM"; single-vehicle, not multi-robot coordination.
- An arXiv full-text search for cs.RO/cs.MA abstracts containing (congestion AND {LLM|VLM|vision-language|language model}) returned only 9 papers through 2026-09, none of which is a warehouse multi-robot congestion resolver (list verified via arXiv API, 2026-10-01).

### Inferences
- The overhead-camera + semantic congestion-strategy-taxonomy combination remains unoccupied in the public literature as of 2026-10-01. The main crowding risk is compositional: Oxford CCTV (known) supplies the overhead-camera fleet control, Garg/GameChat supply VLM deadlock strategies — a reviewer could call claim (1) "a combination," so the taxonomy itself should be positioned as the contribution.

### Gaps
- Could not search OpenReview CoRL 2026 / ICRA 2026 submission lists directly (not indexed in the searches run); a camera-ready crop landing Oct–Dec 2026 could still surface a hit.
- Google Scholar not directly fetchable; citation sweep relied on Semantic Scholar, which lags ~1–3 months.

---

## KQ2: Any new system reporting plan-preservation / repair / provenance statistics for model-proposed robot plans?

### Takeaway
This is the most crowded of the five claims. Two 2026 systems do deterministic, non-LLM verification/repair of LLM-proposed robot plans and *report repair-related statistics* (GAVEL; Physical Agentic AI), and an MDPI line reports repair-budget metrics. **None reports three-way per-leg provenance (verbatim/repaired/defaulted) as a first-class metric, and none is multi-robot congestion** — but claim (2) must now be worded against GAVEL and Physical Agentic AI as concurrent work.

### Cited Findings
- **GAVEL: Graph World Models for Verified and Efficient Long-Horizon LLM Task Planning** — arXiv:2609.19315, 2026-09-16 (Wang, Hsu, Mehta, Kim, Dou, Pajic — Duke), VERIFIED. Explicit graph world model "can predict the consequences of LLM-generated actions before execution, detect violations, and repair those whose corrections follow directly from the world model. This method also reserves LLM replanning solely for errors requiring semantic reasoning." Single-robot BEHAVIOR-1K household tasks; success 41.2%→91.8% with Qwen3-8B. **Direct conceptual overlap with "deterministic non-LLM minimal repair of model-proposed plans."** No multi-robot, no congestion, and the abstract reports success rates, not per-step provenance fractions. [arXiv](https://arxiv.org/abs/2609.19315)
- **Physical Agentic AI: An Architecture for Orchestrating a Robot Crew with LLMs** — arXiv:2608.22657, 2026-08-23, VERIFIED. "A deterministic Robot Orchestrator validates and authorizes one skill at a time" between an LLM Mission Planner and a multi-robot crew (drone+UGV, humanoid+quadruped), and reports *per-dispatch* gate statistics: "retrieval raises skill grounding from 51% to 96% yet leaves informed planners dispatching 23-29% of faulted steps. Per-dispatch enforcement reduces false dispatch to 0% with no false blocks." **This is per-step auditing of an LLM-proposed multi-robot plan with reported step-level statistics** — the closest thing found to claims (2) and (4). It gates/refuses rather than minimally repairs, and has no verbatim/repaired/defaulted trichotomy and no congestion scenario. [arXiv](https://arxiv.org/abs/2608.22657)
- **Robot Planning via LLM Proposals and Symbolic Verification** — MDPI Machine Learning & Knowledge Extraction 8(1):22, 2026, UNVERIFIED (MDPI returned HTTP 403; details from search snippets only). "When parsing, solving, or validation fails, a bounded repair loop" feeds planner error logs back to the LLM; "metrics track the share of solved problems within a small repair budget and the average number of repair attempts." LLM-in-the-repair-loop (not deterministic repair), single-agent PDDL. [MDPI](https://doi.org/10.3390/make8010022)
- **LLM-Assisted Plan Execution for Robots in Dynamic Environments** — MDPI Robotics 15(4):80, 2026, UNVERIFIED (403; snippets only). Search snippet: "Preserving the execution of necessary actions during the transition between plans has a significant impact on robot performance" — i.e., plan-preservation as a *property studied*, during LLM-assisted replanning. Verify before pre-registration whether it quantifies preservation as a reported metric. [MDPI](https://www.mdpi.com/2218-6581/15/4/80)
- **Logic-Based Verification of Task Allocation for LLM-Enabled Multi-Agent Manufacturing Systems** — arXiv:2604.17142, 2026-04-18, VERIFIED. Temporal logic + discrete-event-system verification of LLM task allocations in a multi-robot assembly cell; blocks unsafe allocations pre-execution. Verification-only (no repair, no provenance stats). [arXiv](https://arxiv.org/abs/2604.17142)
- **Hierarchical LLM-Based Multi-Agent Framework with Prompt Optimization for Multi-Robot Task Planning** — arXiv:2602.21670, 2026-02-25, VERIFIED. LLM→PDDL→classical planner with TextGrad-style prompt repair on failure; beats LaMMA-P on MAT-THOR (0.95/0.84/0.60). Repair target is the *prompt*, not the plan legs. Relevant as a LaMMA-P follow-up. [arXiv](https://arxiv.org/abs/2602.21670)
- **Agentic Harnesses: LLM-Driven Verification Layers for Robot Autonomy** — arXiv:2608.09857, 2026, UNVERIFIED (snippet only). "Ensemble of LLM judges... deterministic provenance and prompt-injection checks" — the word "provenance" here means artifact/input provenance for security, not per-leg plan provenance. Check full text before claiming the metric name is unused. [Pith listing](https://pith.science/paper/2608.09857)

### Inferences
- The *trichotomous per-leg provenance metric* (verbatim/repaired/defaulted) as a first-class reported quantity appears novel; the *deterministic verify-and-repair harness around an LLM planner* is no longer novel on its own (GAVEL, Physical Agentic AI, both mid/late 2026 — frame as concurrent work, both are <4 months old).
- Recommended wording shift: claim the provenance *reporting* and the *minimal-repair-for-multi-robot-congestion-plans* combination, not deterministic repair per se.

### Gaps
- MDPI full texts (MAKE 8(1):22 and Robotics 15(4):80) could not be fetched (403). Their exact metrics must be checked manually before the pre-registration text asserts "no prior work reports plan-preservation statistics."
- GAVEL full text not read; it may report "% of failures repaired by world model vs. sent to LLM," which would be a two-way provenance statistic. Check Section on evaluation before finalizing claim (2) wording.

---

## KQ3: Any new VLM-vs-classical two-arm comparisons on embodied multi-robot scenarios?

### Takeaway
VLM/LLM-vs-baseline comparisons are now routine, but the baselines are greedy heuristics, RL policies, or exploration planners — not a *literature-grounded rule-based congestion coordinator on identical Nav2 warehouse scenarios*. No matched two-arm congestion-resolution comparison found.

### Cited Findings
- **D-VLC: Decentralized Vision-Language Collaboration for Heterogeneous Embodied Multi-Robot Systems** — arXiv:2607.29009, 2026-07-31, VERIFIED. VLM-driven heterogeneous multi-robot framework; explicitly motivated against "conventional rule-based methods"; evaluation compares against a "geometric greedy baseline" (completion time −55.8%). Decentralized, unknown environments, not congestion/Nav2. [arXiv](https://arxiv.org/abs/2607.29009)
- **Virtual Traffic Lights for Multi-Robot Navigation: Decentralized Planning with Centralized Conflict Resolution** — arXiv:2511.07811, 2025-11-11, VERIFIED. **Non-LLM** centralized conflict resolver issuing stop commands only ("functioning as a virtual traffic light"), validated on quadrupeds and Duckiebots; "increased the success rate... while reducing deadlocks." This is exactly the class of literature-grounded rule-based coordinator the thesis's Arm B embodies — cite it as evidence the rule-based arm is a live, current baseline, and as a candidate Arm-B design reference. [arXiv](https://arxiv.org/abs/2511.07811)
- **Deadlock-Free Hybrid RL-MAPF Framework for Zero-Shot Multi-Robot Navigation** — arXiv:2511.22685, 2025-11-27, VERIFIED. Non-LLM: safety layer detects deadlocks by monitoring progress, triggers on-demand MAPF for affected agents. Another current classical/learned deadlock-resolution baseline; no VLM arm. [arXiv](https://arxiv.org/abs/2511.22685)
- **CostNav: A Navigation Benchmark for Real-World Economic-Cost Evaluation of Physical AI Agents** — arXiv:2511.20216, 2025, UNVERIFIED (snippet). Benchmarks rule-based Nav2 variants against learned agents — Nav2-vs-AI comparisons exist, but single-robot and cost-focused. [arXiv](https://arxiv.org/abs/2511.20216)
- **IROS: A Dual-Process Architecture for Real-Time VLM-Based Indoor Navigation** — arXiv:2601.21506, 2026-01, UNVERIFIED (snippet): VLM-only baseline 5.83% vs hybrid 67.5% episode success — single robot, but useful for the "raw VLM is a weak arm" argument.
- No paper found that runs a central VLM congestion resolver and a rule-based coordinator over *identical, matched* warehouse Nav2 scenarios as a two-arm experiment (absence claim based on all searches run 2026-10-01).

### Inferences
- The matched-scenario two-arm *experimental design* (claim 3) is still distinctive; its threat surface is methodological reviewers calling the comparison obvious rather than someone having done it.

### Gaps
- IEEE RA-L recent issues not swept directly (paywalled); RA-L 2026 papers may contain a VLM-vs-classical fleet comparison not yet on arXiv.

---

## KQ4: Follow-ups to Garg et al. (2404.06413) and LLMDR (2503.00717)?

### Takeaway
Garg et al. has only a thin citation trail (5 citing papers on Semantic Scholar, none scooping the warehouse/overhead-camera setting); LLMDR shows **zero** citations on Semantic Scholar as of 2026-10-01. The MIT-REALM line itself (VLM-GCBF+ hierarchical planner) remains the strongest adjacent lineage.

### Cited Findings
- Semantic Scholar citations of arXiv:2404.06413 (fetched 2026-10-01, VERIFIED, 5 results): (1) **LLM-Enabled Human-in-the-Loop Control of Multi-UAV Teams under Communication Constraints**, ICUAS 2026, no arXiv id; (2) **Prompting Robot Teams With Natural Language**, IEEE RA-L 2025, arXiv:2509.24575 — distills LLM task decompositions into onboard RNN+GNN policies; not deadlock-specific (abstract VERIFIED); (3) **Seeing, Saying, Solving: An LLM-to-TL Framework for Cooperative Robots**, arXiv:2505.13376, 2025 — heterogeneous warehouse robots negotiate help requests in natural language with formal (temporal-logic) verification, "coordinate conflict recovery with no central dispatcher" (snippet, UNVERIFIED detail) — a decentralized warehouse conflict-recovery system worth citing against claims (1)/(3); (4) **GameChat: Multi-LLM Dialogue for Safe, Agile, and Socially Optimal Multi-Agent Navigation**, MRS 2025, arXiv:2503.12333, VERIFIED — decentralized LLM dialogue resolving spatial-symmetry conflicts/deadlocks at doorways and intersections, no central coordinator, no camera; (5) **Large language models for multi-robot systems: a survey**, Autonomous Robots 2025, arXiv:2502.03814. [S2 API](https://api.semanticscholar.org/graph/v1/paper/arXiv:2404.06413/citations)
- Semantic Scholar citations of arXiv:2503.00717 (LLMDR): **empty result set** (VERIFIED fetch, 2026-10-01). No indexed follow-ups yet.
- Semantic Scholar citations of arXiv:2606.06762 (Oxford CCTV warehouse): **empty result set** (VERIFIED fetch, 2026-10-01). No indexed follow-ups.
- MIT-REALM follow-on: "Online Motion Planning for Connected Multi-Robot Systems using VLMs" / VLM-GCBF+ project page (hierarchical: VLM assigns leader + waypoints over the Garg deadlock setting) — [project site](https://mit-realm.github.io/VLM-gcbfplus-website/), UNVERIFIED whether a new 2026 paper version exists beyond the known line. Worth one manual check before tag.
- **SyncPlan: Long-Horizon LLM Coordination with Explicit Synchronization and Adaptive Correction** — arXiv:2608.01652, 2026-08-03, VERIFIED (surfaced in the deadlock sweep, not a Garg citer). Centralized LLM coordinator produces per-agent action chains in one call; execution layer has "explicit wait primitives and deadlock detection"; a "Plan Staleness Detector continuously assesses the remaining plan and triggers replanning." Evaluated on Overcooked / Honor of Kings (games, not robots). **Relevant to claims (4) and (5)** — see KQ5. [arXiv](https://arxiv.org/abs/2608.01652)

### Inferences
- The deadlock-resolution-via-foundation-models niche is moving toward *decentralized dialogue* (GameChat, Seeing-Saying-Solving) and *hierarchical leader-assignment* (VLM-GCBF+), not centralized overhead-camera semantic classification — the thesis's centralized-perception angle remains differentiated.

### Gaps
- Semantic Scholar indexing lag means late-2026 citers of Garg/LLMDR may be missing; Google Scholar could not be queried programmatically.

---

## KQ5: New warehouse/AGV industry or academic systems using foundation models for traffic/congestion (DeepFleet follow-ups, AMR vendors)? Plus: persistent incrementally-edited central plans (claims 4–5).

### Takeaway
DeepFleet now has a technical paper (arXiv:2508.08574) but it is a *predictive world model* of fleet movement, not a semantic congestion resolver; no public DeepFleet-v2/control follow-up found. For claims (4)/(5), SyncPlan is the main concurrent threat: a centralized LLM emitting scene-wide per-agent plans that persist and are corrected incrementally with execution feedback — in game environments, not embodied warehouse robots.

### Cited Findings
- **DeepFleet: Multi-Agent Foundation Models for Mobile Robots** — arXiv:2508.08574, Amazon, 2025-08, UNVERIFIED (search snippets + Amazon press). Four neural architectures *pre-trained to predict* large-scale mobile robot fleet movement on millions of robot-hours; deployed as traffic management, ~10% travel-time improvement across 300+ facilities. Predictive/forecasting, not VLM scene reasoning or strategy selection. [arXiv](https://arxiv.org/abs/2508.08574); [Amazon announcement](https://www.aboutamazon.com/news/operations/amazon-million-robots-ai-foundation-model). No follow-up model/paper found in this scan.
- **SyncPlan** (arXiv:2608.01652, VERIFIED, details in KQ4): single-call centralized LLM plan for all agents + persistent plan maintained during execution + staleness-triggered correction with "outcome-level execution feedback" (also used as RL training signal). This partially occupies claim (5)'s *mechanism* (persistent central plan, incremental correction on execution feedback) but in Overcooked/Honor-of-Kings, with replanning rather than minimal in-place edits, and no leg-level audit. Must be cited as concurrent work for claims (4)/(5). [arXiv](https://arxiv.org/abs/2608.01652)
- **Physical Agentic AI** (arXiv:2608.22657, VERIFIED, details in KQ2): LLM planner assigns each phase to a robot-skill pair and a deterministic orchestrator authorizes "one skill at a time" — an ordered scene-wide plan audited step-by-step before actuation. Closest occupant of claim (4)'s audit idea; task orchestration (search-and-dispatch), not congestion, and no repair/provenance.
- **Containing Behavioral Cascades from Manipulated Claims in LLM-Powered Multi-Robot Systems** — arXiv:2609.30523, 2026-09-24, VERIFIED. Team-level "Verify-Adapt-Hold" plan: some robots keep ("hold") their trusted plans while a subset adapts — a form of selective plan preservation across a fleet, motivated by security (false claims causing "congestion"), with Sum-of-Costs/makespan metrics. Adjacent to claims (2)/(5) in spirit (preserve most of the standing plan, change only what must change); cite it. [arXiv](https://arxiv.org/abs/2609.30523)
- **IndoorR2X: Indoor Robot-to-Everything Coordination with LLM-Driven Planning** — arXiv:2603.20182, 2026, UNVERIFIED (snippet only). LLM-driven indoor multi-robot coordination; check full text for congestion handling. [arXiv](https://arxiv.org/abs/2603.20182)
- **Hybrid LLM-based Intelligent Framework for Robot Task Scheduling** — arXiv:2605.15486, 2026, UNVERIFIED listing hit; scheduling, likely warehouse-adjacent.
- No AMR vendor (Locus, 6 River, Geek+, Fetch/Zebra, OTTO) foundation-model traffic-control announcement surfaced in the searches run; the industry signal remains DeepFleet only (absence claim, searches of 2026-10-01).

### Inferences
- Claim (5)'s defensible core after this scan: *incremental minimal edits to a persistent plan* (vs. SyncPlan's detect-staleness-then-replan) + *embodied Nav2 warehouse setting* + integration with the provenance-audited repair of claim (2). The bare "persistent central LLM plan with execution feedback" is no longer claimable alone.
- Claim (4)'s defensible core: leg-by-leg audit *with repair and provenance*, since Physical Agentic AI already audits per-dispatch with refuse-only semantics.

### Gaps
- DeepFleet technical paper (2508.08574) abstract not fetched directly; its exact scope (prediction-only vs. any control/congestion module) should be confirmed by reading the paper before the pre-reg's related-work section characterizes it.
- CoRL 2026 / ICLR 2026 / ICRA 2026 OpenReview listings and LangRob/MRS workshop pages were not individually swept; residual risk of an unindexed workshop paper on VLM congestion resolution.

---

## Summary threat matrix

| Claim | Status | Top threats to cite as concurrent work |
|---|---|---|
| (1) Overhead-camera VLM congestion-strategy taxonomy | **Open** — no occupant found | Seeing-Saying-Solving 2505.13376; EFLUX 2607.12050; highway-VLM 2508.17205 (domain-adjacent) |
| (2) Deterministic minimal repair + 3-way per-leg provenance metric | **Partially crowded** — repair harness no longer novel; provenance metric still unclaimed | **GAVEL 2609.19315**; **Physical Agentic AI 2608.22657**; MDPI MAKE 8(1):22; cascade-containment 2609.30523 |
| (3) Matched two-arm VLM vs rule-based on identical Nav2 scenarios | **Open** — no such comparison found | Virtual Traffic Lights 2511.07811 (validates Arm-B class); D-VLC 2607.29009 (greedy-baseline comparisons) |
| (4) Scene-wide ordered plan audited leg-by-leg | **Partially crowded** (audit-and-refuse exists; audit-and-repair does not) | **Physical Agentic AI 2608.22657**; SyncPlan 2608.01652 |
| (5) Persistent incrementally-edited central plan w/ execution feedback | **Partially crowded** (mechanism in games; not embodied/minimal-edit) | **SyncPlan 2608.01652**; cascade-containment 2609.30523 |

Highest-priority manual follow-ups before `git tag prereg-v1`: read GAVEL's evaluation section (possible two-way repair-provenance statistic), fetch the two MDPI full texts (2504-4990/8/1/22 and 2218-6581/15/4/80), and skim DeepFleet 2508.08574.
