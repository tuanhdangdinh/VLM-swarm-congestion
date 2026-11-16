# Grounding, Verification & Repair Architectures for LLM/VLM-Proposed Multi-Robot Plans (2024–2026)

Scope note: GAVEL, PAAI, SyncPlan, RoCo, and arXiv:2505.14763 were excluded per assignment (already known); findings below are positioned relative to them only where useful. Caveat on sourcing: for several 2026 papers only abstract-level detail was retrievable; this is flagged per-entry. Quantitative claims pulled from search-result summaries rather than full-paper reads are marked "(snippet-level)".

## Q1: What verify-then-repair architectures exist for multi-robot plans, and how do they bound repair?

### Takeaway
The 2025–2026 pattern has converged on "LLM/VLM as proposal layer, deterministic verifier as gatekeeper, bounded repair on rejection." Repair bounds appear in three forms: iteration caps on re-prompting (typically 3–5), bounded edit radius on localized plan surgery (ALAS), and architectural bounds (repair scope limited to the coupling topology of affected subtasks). No paper freezes the repair bound as an experimental variable the way the user's pipeline proposes.

### Cited Findings
- **Verification-Gated Agentic Mission-State Governance** (Tang, Jia, Tan, Huang, Ji, Chen; arXiv June 2026) — the closest architectural match to our M3/M5 design: dual synchronized state objects (a *task forest* maintaining hierarchy and repairability + a *governed blackboard* tracking execution state, resource locks, verification records). Proposals from heuristic, optimization, or agentic reasoning modules undergo "deterministic verification and atomic commit" before updating mission state; AI is explicitly a "proposal-generating layer governed by inspectable mission-state verification." A derived *execution coupling topology* enables bounded repair, deferrals, or constraint updates on verification failure. Evaluated on 30-seed remote-construction and factory benchmarks: "fewer invalid commitments, lock conflicts, duplicate assignments, abandoned nodes, and disruptive repairs" — but no absolute acceptance-rate numbers in the abstract (abstract-level only) — [arXiv:2606.31339](https://arxiv.org/abs/2606.31339)
- **INPROVF** (Meng et al., ICLR Workshop 2025) — inverts the roles: LLM generates *repair candidates* for high-level robot controllers whose environment assumptions were violated; formal methods (reactive synthesis lineage, Kress-Gazit group) verify each candidate. Failed candidates produce feedback (which unsafe behaviors / unsatisfied tasks) that is translated into natural language and used to iteratively re-prompt — [INPROVF, ICLRW 2025](https://mlanthology.org/iclrw/2025/meng2025iclrw-leveraging); [paper page](https://awesomepapers.io/papers/meng2025inprovf)
- **ALAS: Transactional and Dynamic Multi-Agent LLM Planning** (arXiv Nov 2025/2026) — performs *localized repair that preserves work in progress* via separated planning and validation; explicitly "contains runtime perturbations with a bounded edit radius," reporting less makespan degradation than global recompute (snippet-level) — [arXiv:2511.03094](https://arxiv.org/html/2511.03094v1)
- **Logic-Based Verification of Task Allocation for LLM-Enabled Multi-Agent Manufacturing Systems** (Lim, Tavakkoli Anbarani, Meira-Góes, Kovalenko; arXiv April 2026) — LLM proposes task allocations; safety constraints translated to LTLf, converted to safety automata, and candidate allocations verified pre-execution against the automata in a discrete-event-systems framework. Demonstrated on a multi-robot assembly scenario; no quantitative acceptance/repair statistics in abstract (abstract-level only) — [arXiv:2604.17142](https://arxiv.org/pdf/2604.17142)
- **LaMMA-P** (Zhang, Qin, Wang, Dong, Li; ICRA 2025) — LLM decomposes long-horizon multi-robot tasks and drives a PDDL heuristic planner per robot; the classical planner is the correctness engine, not a verifier of LLM plan text. Reports **105% higher success rate and 36% higher efficiency** than existing LM-based multi-agent planners (SMART-LLM baseline lineage) — [arXiv:2409.20560](https://arxiv.org/abs/2409.20560v2); [ICRA 2025 DOI](https://api.openalex.org/works/doi:10.1109%2FICRA55743.2025.11127951)
- **Phase-Adaptive LLM Framework with Multi-Stage Validation for Construction Robot Task Allocation** (arXiv Dec 2025/2026) — three dedicated agents (Task Decomposition, Task Allocation, Code Generation), each gated by an *independent validation node* checking syntactic, semantic, and logical correctness before the next stage runs; systematically benchmarked against traditional optimization algorithms (snippet-level) — [arXiv:2512.02810](https://arxiv.org/pdf/2512.02810)
- Iteration-cap precedent: a PDDL Planning Copilot line of work runs VAL on LLM plans, extracts VAL's "plan repair advice," reports it to the LLM, and repeats **up to four times** (snippet-level) — [ICAPS 2026 demo](https://icaps26.icaps-conference.org/files/demos/icaps26-demo_paper_12.pdf); [review](https://www.themoonlight.io/review/toward-pddl-planning-copilot)
- **GNNVerifier** (arXiv 2026) — a learned (GNN) verifier for LLM task plans producing a graph-level plausibility score for accept/reject plus node/edge-level risk scores that *localize* the erroneous region of the plan — localization is exactly what a bounded-repair step needs (snippet-level) — [arXiv:2603.14730](https://www.alphaxiv.org/abs/2603.14730.md)

### Inferences
- Repair bounds in the literature are operational conveniences (loop caps, edit radii), not preregistered experimental variables; a frozen repair bound treated as a design constant with reported consequences would be novel.
- The mission-state-governance paper (2606.31339) is the one to read in full before finalizing our M5 commit semantics — its "atomic commit after deterministic verification" and resource-lock records map directly onto the task-registry ownership model in CLAUDE.md.

### Gaps
- No multi-robot paper found that reports the *distribution of repair sizes* (how much repair was needed per accepted plan) except via ALAS's qualitative "bounded edit radius" claim and the single-agent Levenshtein stat in Q2.
- 2606.31339 and 2604.17142 quantitative internals (acceptance rates, verification latency) unavailable from abstracts; full-text reads needed.

## Q2: Re-prompt-with-error-feedback vs classical-repair-without-reprompt — head-to-head measurements?

### Takeaway
The canonical head-to-head remains Valmeekam et al. (NeurIPS 2023): silent LPG repair of LLM seed plans vs VAL-feedback back-prompting, with the famous result that >50% of the final repaired plan content was planner edits. For 2024–2026 I found **no multi-robot head-to-head** of these two arms; the field has instead split into camps (re-prompting loops vs planner-as-backend), which is itself a finding.

### Cited Findings
- **Valmeekam et al., "On the Planning Abilities of LLMs: A Critical Investigation"** (NeurIPS 2023; the baseline both camps cite) — Arm 1: Instruct-GPT3 plans on 600 Blocksworld instances fed as *seed plans* to LPG (local-search planner that repairs flaws iteratively); LPG repairs them "with relative ease," and LLM+LPG needs far fewer search steps than LPG from scratch. Measured **average Levenshtein edit distance 7.22 between the LLM plan and LPG's final correct plan, vs average final plan length 11.7 — i.e., >50% of the final plan attributable to planner edits**. Arm 2: VAL as external verifier back-prompting the LLM with error feedback; repeated interaction improves plan correctness, especially in common-sense domains — [arXiv:2305.15771](https://arxiv.org/pdf/2305.15771); [NeurIPS 2023 version](https://papers.neurips.cc/paper_files/paper/2023/file/efb2072a358cefb75886a315a6fcf880-Paper-Conference.pdf)
- **"On the Generalization Gap in LLM Planning: Tests and Verifier-Reward RL"** (arXiv Jan 2026) — uses VAL as a reward signal (RL arm) rather than a repair arm: fine-tuned LLM reaches **82.9% valid-plan rate in-domain but 0% on unseen domains**; verifier-reward RL saturates in half the supervised epochs but does not improve cross-domain generalization (snippet-level) — [arXiv:2601.14456](https://arxiv.org/html/2601.14456v1)
- **LAD-VF** (arXiv Sept 2025) — a third option between the two arms: formal-verification feedback drives *automated prompt engineering* (a "formal-verification-informed text loss"), no fine-tuning; improves specification compliance **from 60% to >90%** (snippet-level) — [arXiv:2509.18384](https://arxiv.org/pdf/2509.18384)
- **"Replan, Repair, or Edit?"** (arXiv Sept 2026) — a unified empirical comparison of revision strategies under disruption, in the travel-itinerary domain (not robotics); the only 2026 paper found that frames the replan-vs-repair-vs-edit choice as the experimental variable — [arXiv:2609.19654](https://arxiv.org/pdf/2609.19654)
- **"How Far Are LLMs from Symbolic Planners? An NLP-Based Perspective"** (Armony, Meroño-Peñuela, Canal; arXiv Aug 2025) — recovery-pipeline framing: initial LLM plan success **21.9%**, after their recovery pipeline **27.5%**; LLM plans average only 2.65 executable actions vs 8.4-action reference plans — [arXiv:2508.01300](https://arxiv.org/abs/2508.01300)

### Inferences
- The in-domain vs out-of-domain collapse (82.9% → 0%) is a strong argument for keeping a deterministic verifier in the loop permanently rather than trusting any fine-tuned proposal model.
- Because no 2024–2026 multi-robot head-to-head exists, our pipeline's planned comparison (re-prompt vs silent classical repair under a frozen repair bound) would be a genuinely open measurement, not a replication.

### Gaps
- No head-to-head in a multi-robot or MAPF setting; no measurement anywhere of *latency* differences between the two arms (re-prompt rounds cost seconds of VLM latency; classical repair costs milliseconds — nobody quantifies this trade for Layer-2-speed loops like ours).

## Q3: Formal methods on LLM plan outputs (LTL/STL/PDDL/MAPF-as-verifier) 2024–2026 — success rates?

### Takeaway
LTL/STL grounding with syntax+semantics re-prompting (AutoTAMP lineage) reaches ~82–88% on multi-agent benchmark tasks; LTL critics and model-checking loops with counterexample feedback reach near-100% pass rates after multiple iterations; meanwhile the MAPF community's verdict is that LLMs cannot *produce* valid joint paths at scale, cementing the MAPF-solver-as-verifier/executor role.

### Cited Findings
- **AutoTAMP** (ICRA 2024) — LLM as translator NL→STL plus LLM syntax/semantics checkers re-prompting the translation; STL planner produces trajectories. GPT-4 with syntax+semantics checking: **82.5%** HouseWorld1 soft time constraints, **82.0%** hard time constraints, **87.7%** Chip's Challenge; includes multi-agent scenarios — [arXiv:2306.06531](https://arxiv.org/pdf/2306.06531); [project/GitHub](https://github.com/yongchao98/AutoTAMP)
- **VerifyLLM** (Grigorev, Kovalev, Panov; IROS 2025) — pre-execution verification: NL instructions → LTL, then LLM analysis of the action sequence against the LTL to find ordering errors/gaps; "keep unchanged" is one of its verification decisions. Abstract reports no numeric accuracy; code at verifyllm.github.io — [arXiv:2507.05118](https://arxiv.org/abs/2507.05118)
- **LogicGuard** (arXiv 2025) — temporal-logic-based critic improving embodied LLM agents (LTL critic over agent trajectories) — [arXiv:2507.03293](https://arxiv.org/pdf/2507.03293)
- **PAT-Agent** (arXiv Sept 2025) — autoformalization for model checking with an iterative repair loop feeding counterexamples and verification feedback back to the LLM: **100% full-pass rate, with multiple repair iterations often necessary** (snippet-level) — [arXiv:2509.23675](https://arxiv.org/pdf/2509.23675)
- **MAPF-as-LLM-benchmark** (Chen et al., TMLR 2025) — LLMs solve MAPF only in easy regimes: e.g., Gemma2 100% success on 8x8 empty maps with 2 agents falling to **43.75% at 16 agents**; GPT-3.5-turbo 100% → **50%**; failure on harder room/maze maps of the standard MAPF benchmark (snippet-level) — [TMLR 2025](https://mlanthology.org/tmlr/2025/chen2025tmlr-solving); companion position paper ["Why Solving MAPF with LLM Has Not Succeeded Yet"](https://themoonlight.io/review/why-solving-multi-agent-path-finding-with-large-language-model-has-not-succeeded-yet)
- **LLMDR** (Seo, Kim, Shin, Suh; arXiv Mar 2025) — division of labor matching ours: learned MAPF policy runs the robots; the LLM is invoked to *detect deadlocks and prescribe resolution strategies*, integrated via prioritized planning; improves learned-MAPF success rates "particularly in deadlock-prone scenarios" on standard benchmark maps (no absolute numbers in abstract; code: github.com/ssbacc/llmdr-dhc) — [arXiv:2503.00717](https://arxiv.org/abs/2503.00717)
- **Fine-Tuning Language Models Using Formal Methods Feedback** (arXiv, 2023/2024 lineage feeding LAD-VF) — automated fine-tuning from model-checking signals for controller synthesis — [arXiv:2310.18239](https://arxiv.org/pdf/2310.18239)
- NLP-perspective evidence that symbolic-planner recovery pipelines lift LLM success only modestly (21.9%→27.5%) when domains are unconstrained — [arXiv:2508.01300](https://arxiv.org/abs/2508.01300)

### Inferences
- For our stack the MAPF results justify never asking the VLM for paths: the VLM proposes *strategy-level* interventions (yield/reroute/convoy), and Nav2/MAPF-grade machinery remains the feasibility authority — the same split LLMDR landed on independently.
- Near-100% numbers (PAT-Agent, LAD-VF >90%) all come from loops with *unbounded or generous* iteration budgets; no paper reports the success-vs-iteration-budget curve that a frozen repair bound requires.

### Gaps
- No paper found using an MAPF solver *explicitly as a verifier* of LLM-proposed joint plans with accept/reject statistics (the MAPF community went straight to "LLM can't do it" rather than "solver checks LLM").
- LDK Benchmark: no results surfaced in these searches; cannot confirm its existence/content.

## Q4: Does any 2024–2026 paper report provenance-style statistics (verbatim vs modified vs fallback)?

### Takeaway
**No.** Across all retrieved 2024–2026 verification/repair papers, none reports the distribution of *executed* plans by provenance (model-verbatim / repaired / fallback). The nearest analogues are a 2023 edit-distance statistic and scattered "initial validity rate" numbers, which only bound the verbatim rate from above. The user's `vlm_verbatim/repaired/fallback` provenance metric appears to be **unclaimed** — confirmed within the limits of this search.

### Cited Findings
- Closest analogue (2023, single-agent Blocksworld, not a provenance fraction): average Levenshtein distance 7.22 between LLM seed plan and LPG's final plan, average final length 11.7 — ">50% of the final plan might have been due to the edits made by the LPG planner" — [Valmeekam et al., arXiv:2305.15771](https://arxiv.org/pdf/2305.15771)
- Initial-validity rates (upper bounds on a hypothetical verbatim rate, not framed as provenance): LLM plans initially valid/successful **21.9%** before recovery in [arXiv:2508.01300](https://arxiv.org/abs/2508.01300); fine-tuned in-domain valid-plan rate **82.9%** in [arXiv:2601.14456](https://arxiv.org/html/2601.14456v1)
- VerifyLLM can *decide* to keep actions unchanged but does not report what fraction of plans pass unchanged — [arXiv:2507.05118](https://arxiv.org/pdf/2507.05118)
- Verification-gated governance (2606.31339) counts *invalid commitments prevented* and *disruptive repairs*, which is the complement of a provenance statistic but is reported only as "fewer than baseline," not as a provenance split — [arXiv:2606.31339](https://arxiv.org/abs/2606.31339)

### Inferences
- A three-way provenance split over executed interventions (verbatim / repaired / fallback), reported per-scenario with a frozen repair bound, would be a publishable measurement novelty; the Valmeekam Levenshtein stat is the citation to position against ("prior work measured edit distance on seed plans in Blocksworld; we measure provenance of executed multi-robot interventions").
- "Disruptive repairs" count (2606.31339) suggests reviewers will also want the *cost* of repair (disruption/makespan delta), not just the provenance split.

### Gaps
- Cannot prove a negative exhaustively: ICAPS/AAMAS 2025–2026 workshop papers were not individually swept; a full-text search of 2606.31339 and the Phase-Adaptive construction paper (2512.02810) is the remaining risk for prior claims.

## Q5: Safety/feasibility shields for multi-robot dispatch — architectures and overhead

### Takeaway
2025–2026 shields for LLM-driven robots are temporal-logic synthesis layers between the planner and the actuators: RoboGuard's control-synthesis reconciliation cuts unsafe-plan execution from 92% to <2.5% under worst-case jailbreaks. Multi-robot-specific dispatch shields exist mostly as verification gates (Q1 papers); runtime-overhead numbers are almost never reported.

### Cited Findings
- **RoboGuard** (RA-L, accepted Feb 2026; arXiv 2503.07885) — two stages: (1) chain-of-thought LLM generates *context-dependent* safety specifications as temporal logic from the scene; (2) temporal-logic control synthesis resolves conflicts between those specs and the (possibly adversarial) proposed plan, correcting unsafe commands while preserving planner intent where possible. **Reduces execution of unsafe plans from 92% to below 2.5%** under worst-case jailbreak attacks — [arXiv:2503.07885](https://alphaxiv.org/abs/2503.07885); [ar5iv](https://ar5iv.labs.arxiv.org/html/2503.07885)
- **Safety Guardrails for LLM-Enabled Robots** (2025) — survey/framework positioning shields, including the RoboGuard result above — [review page](https://www.themoonlight.io/review/safety-guardrails-for-llm-enabled-robots)
- **Shield synthesis for LLM agents** (Rodriguez et al., KR 2026) — actions filtered by a formally synthesized shield enforcing temporal-logic safety properties online, correcting unsafe commands while preserving LLM intent (snippet-level) — [KR 2026 paper](https://proceedings.kr.org/2026/104/kr2026-0104-rodriguez-et-al.pdf)
- **Pre-Execution Safety Gate & Task Safety Contracts for LLM-Controlled Robot Systems** (arXiv April 2026) — contract-based pre-execution gate pattern for LLM-controlled robots (abstract-level) — [arXiv:2604.05427](https://arxiv.org/pdf/2604.05427)
- **Safety Chip** lineage — NL→LTL constraints, human-verifiable and machine-checkable; at runtime unsafe actions are pruned and explanations trigger re-planning (re-prompt-on-shield-violation pattern) — cited in [Trust in LLM-controlled Robotics survey, arXiv:2601.02377](https://arxiv.org/pdf/2601.02377)
- Reachability-based filters (SanDRA and "Safe LLM-controlled robotics") reject plans whose execution would leave precomputed safe sets — per the same survey — [arXiv:2601.02377](https://arxiv.org/pdf/2601.02377)
- Simulation as feasibility shield: frameworks validate LLM/VLM multi-robot plans in simulation before deployment, with "erroneous plans failing in simulation even if they pass initial evaluation checks"; PerceptTwin builds the interactive simulation *from the robot's perception stack* for pre-execution validation — [Foundation Model Driven Robotics review, arXiv:2507.10087](https://arxiv.org/pdf/2507.10087)

### Inferences
- Our M4 safety invariants (min distance, speed limits) are a static shield; the RoboGuard pattern suggests a cheap upgrade: generate scenario-conditioned constraints at M3 time and enforce them with deterministic synthesis/checking at M4, keeping the VLM out of the safety path.
- The near-total absence of published shield latency/overhead numbers means even a simple wall-clock overhead table for our safety gate would fill a reporting gap.

### Gaps
- No paper found reporting shield computational overhead (ms per dispatch) for multi-robot systems; RoboGuard reports safety deltas, not latency.
- No multi-robot shield paper quantifies conservatism cost (task throughput lost to shield interventions).
