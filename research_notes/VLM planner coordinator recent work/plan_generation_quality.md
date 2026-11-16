# Model-Emitted Structured Plans: Quality, Validity, Grammar Adherence, Scoring (2025–2026)

Scope: full ordered action-sequence emission by LLMs/VLMs (not subgoal/task allocation). Each citation is tagged **VERIFIED** (page fetched in this session) or **unverified** (search-result snippet only; corroborated where noted). Relevance notes map findings to our thesis metrics: emission rate, consistency-with-stated-grammar rate, edit distance, verbatim/repaired/defaulted provenance.

## Q1. Plan-validity benchmarks for VLMs/LLMs in embodied settings (2025–2026); multi-agent plan emission

### Takeaway
Validity rates on full multi-step plans remain bimodal: non-reasoning LLMs sit at ~3–25% valid on classical domains while reasoning models (o4-mini class) reach ~94%; VLM-input embodied benchmarks show top MLLMs below ~45% accuracy even on single-next-action choice, and multi-agent full-plan emission (MAPF-style) collapses once obstacles or >10 agents appear. No 2025–2026 benchmark scores *multi-robot joint action-sequence* emission as a first-class artifact — that is a genuine gap our provenance metrics would fill.

### Cited Findings
**Single-agent symbolic-domain plan emission (text input):**
- "How Far Are LLMs from Symbolic Planners? An NLP-Based Perspective" (arXiv:2508.01300, Aug 2025, King's College London) — **VERIFIED**. Blocksworld + Logistics, Fast-Downward/A*/LM-Cut ground truth. Low-SR models (GPT-3.5, Claude 3 Haiku, small Qwen/Llama/Gemma): ~3–14% success on Blocksworld; o4-mini: 94% (→100% after their recovery pipeline). On failed plans, on average only **2.65 actions of an 8.4-action ground-truth plan are executable** before the first constraint violation; >50% of low-SR plans fail at the *first* action. Pipeline recovery lifted overall SR 21.9%→27.5%. — [arXiv:2508.01300](https://arxiv.org/html/2508.01300v1)
- "Chasing Progress, Not Perfection: Revisiting Strategies for End-to-End LLM Plan Generation" (arXiv:2412.10675) — unverified snippet. On extended PlanBench: CoT and self-correction improve *executability* but not *validity*; RL with a Longest-Contiguous-Common-Subsequence reward was the only strategy improving both. — [arXiv:2412.10675](https://arxiv.org/html/2412.10675v1)
- "ACPBench: Reasoning About Action, Change, and Planning" (AAAI 2025, IBM; arXiv:2410.05669) and "ACPBench Hard: Unrestrained Reasoning about Action, Change, and Planning" (arXiv:2503.24378) — unverified snippets. ACPBench Hard switches from multiple-choice to *generative* answers (the kind a symbolic planner would consume); across 14 models, even the largest LLMs fail on action reachability and action applicability; reasoning models (o1 family) are better but "still fall short of being reliably usable in planners"; no model dominates across tasks. — [ACPBench Hard](https://arxiv.org/html/2503.24378v2), [AAAI page](https://mlanthology.org/aaai/2025/kokel2025aaai-acpbench)

**VLM-input embodied plan benchmarks:**
- EgoPlan-Bench2 (arXiv:2412.04447) — unverified snippets (consistent across arXiv HTML + alphaxiv). 24 scenarios across 4 real-world domains; 21 MLLMs evaluated; GPT-4V direct prediction 37.63%, +CoT 39.82%, best multimodal-CoT + self-consistency prompt combination 43.04% (a +10.24 point training-free gain). Note this is next-action choice given a plan context, not free plan emission — relevant as an upper-bound indicator. — [arXiv:2412.04447](https://arxiv.org/abs/2412.04447)
- "EmbodiedBrain: Expanding Performance Boundaries of Task Planning for Embodied Intelligence" (arXiv:2510.20578, Oct 2025) — **VERIFIED** (abstract). 7B/32B VLM trained with SFT + Step-GRPO ("preceding steps as guided precursors" — i.e., explicitly training the model to condition on plan prefixes); introduces an end-to-end simulation benchmark; per search snippets (unverified) the companion test set **VLM-PlanSim-99** contains 99 household tasks whose ground-truth step sequences were *executed in AI2-THOR to guarantee executability* — a plan-validity-by-simulation scoring pattern. — [arXiv:2510.20578](https://arxiv.org/abs/2510.20578)
- Embodied Agent Interface (NeurIPS 2024 D&B oral; arXiv:2410.07166) — **VERIFIED** (abstract/venue). Decomposes evaluation into goal interpretation / subgoal decomposition / **action sequencing** / transition modeling, with fine-grained error types (hallucination, affordance, planning errors) instead of a single success rate. Still the reference design for module-level plan scoring in 2025 citations. — [arXiv:2410.07166](https://arxiv.org/abs/2410.07166)

**Multi-agent plan emission:**
- "Solving Multi-Agent Path Finding as an LLM Benchmark: How, How Good and Why" (TMLR 2025; earlier version "Why Solving MAPF with LLM Has Not Succeeded Yet," arXiv:2401.03630, Chen et al.) — unverified snippets, two corroborating sources. The LLM emits full joint move sequences. Success on empty 20×20 maps only: ~62.5% at 10 agents, degrading with agent count; **near-total failure on standard MAPF room and maze maps** (i.e., once geometry forces ordered yields/detours). This is the closest published analog to our multi-robot `proposed_plan` setting and it documents exactly the regime (corridor conflicts) where emission breaks. — [TMLR page](https://mlanthology.org/tmlr/2025/chen2025tmlr-solving), [arXiv:2401.03630](https://arxiv.org/abs/2401.03630)
- "Neural Algorithmic Reasoners informed Large Language Model for Multi-Agent Path Finding" (arXiv:2508.17971, 2025) — unverified; reported to outperform LLM baselines on obstacle maps by injecting an algorithmic-reasoner prior. — [arXiv:2508.17971](https://arxiv.org/pdf/2508.17971)
- Multi-robot *task*-planning suites that nonetheless score emitted action programs: LLaMAR + MAP-THOR benchmark (~30% improvement over LLM baselines on long-horizon multi-agent planning; NeurIPS 2024) and Scale-Plan + **MAT2-THOR** ("cleaned benchmark built on AI2-THOR for reliable evaluation of multi-robot planning systems", 2025, arXiv:2502.18836 vicinity) — unverified snippets. — [arXiv:2502.18836](https://arxiv.org/abs/2502.18836v1), [SMART-LLM repo](https://github.com/SMARTlab-Purdue/SMART-LLM)
- "Large Language Models to the Rescue: Deadlock Resolution in Multi-Robot Systems" (arXiv:2404.06413) — unverified; note the contrast: their LLM emits only a *leader + direction* token, not a full plan, precisely because full joint-plan emission was unreliable; validated up to 15 agents / 40 obstacles with a GNN low-level layer. — [arXiv:2404.06413](https://arxiv.org/html/2404.06413v2)

### Inferences
- The field's consistent finding — executability improves before validity — supports splitting our metrics into grammar-consistency (cheap to fix) vs semantic validity (the real bottleneck).
- Published multi-agent results evaluate either (a) joint paths on grids (MAPF) or (b) task allocation + per-robot subplans (MAP-THOR/MAT2-THOR). A VLM emitting an *ordered multi-robot maneuver plan over a congestion scene*, scored with provenance, has no direct published competitor benchmark; the MAPF-LLM failure on constrained maps is the best external baseline to cite.
- The first-action-failure statistic (>50% of weak-model plans invalid at step 1; mean 2.65 executable actions) argues for reporting a "longest valid prefix" metric alongside edit distance.

### Gaps
- No fetched source gives per-model executability percentages for VLM-PlanSim-99 (EmbodiedBrain numbers are in the PDF body, not abstract).
- Found no 2025–2026 benchmark that scores *emission rate* (did the model produce a parseable plan at all) as a named metric; it is usually folded into "syntax error" counts.

## Q2. Does stating the action grammar / plan schema in-prompt measurably improve plan validity? Constrained decoding vs prompted grammar

### Takeaway
Yes, and the ordering is now quantified: putting grammar/syntax knowledge in the prompt roughly tripled semantic accuracy (7%→23%) in a 2025 controlled comparison, while *enforcing* the grammar by constrained decoding achieved 0% syntax errors but collapsed semantic accuracy to ~2% — the strongest published evidence that a told-contract prompt beats a hard-enforced contract for plan content, and that solver/validator-feedback revision beats both.

### Cited Findings
- "Addressing the Challenges of Planning Language Generation" (arXiv:2505.14763, May 2025, rev. Oct 2025) — **VERIFIED** (HTML v1). 8 modular pipelines for PDDL generation, Qwen-3 32B on BlocksWorld: baseline ~7% syntax≈semantic accuracy; **knowledge prompt (PDDL syntax examples in-prompt) ~23%**; Python wrapper (Py2PDDL) *decreased* performance; **constrained decoding with PDDL grammar: 0% syntax errors but ~98% of outputs semantically wrong (~2% accuracy)** — the paper's explanation is that masking "suppressed the semantic tokens" needed for correct action definitions; revision with solver feedback ~2× syntax / ~1.5× semantics; solver+validator revision best overall ("more than double"). This is the closest thing to a told-contract vs enforced-contract isolation study. — [arXiv:2505.14763](https://arxiv.org/html/2505.14763v1)
- "Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of LLMs" (arXiv:2408.02442, EMNLP 2024 Industry) — unverified snippets, widely corroborated. Strictness ordering for reasoning tasks: JSON-schema constrained decoding < format-restricting instructions < NL-then-format < free NL. For classification, restriction can *help*. Instructing JSON format *without* a rigid schema improved some models and reduced prompt-perturbation variance — i.e., a stated-but-soft contract is the sweet spot. — [arXiv:2408.02442](https://arxiv.org/pdf/2408.02442)
- "The Hidden Cost of Structured Generation in LLMs: Draft-Conditioned Constrained Decoding" (arXiv:2603.03305, 2026) — unverified snippet. Confirms mechanism: constrained decoding "alters the model's distribution at every token by masking invalid tokens and renormalizing," reducing semantic correctness on reasoning-intensive tasks despite guaranteed validity; proposes drafting free-form then constraining. — [arXiv:2603.03305](https://arxiv.org/pdf/2603.03305v1)
- "Meta-Ctrl: Guaranteed Plan Generation by Decoupling Syntactic and Semantic Constraints" (arXiv:2608.22149, 2026) — unverified, title/abstract only; the decoupling framing (syntax guaranteed mechanically, semantics left to the model) is the same architecture as our classical verify-and-repair layer. — [arXiv:2608.22149](https://arxiv.org/pdf/2608.22149)

### Inferences
- Direct support for our design: state the grammar in-prompt (lifts consistency-with-stated-grammar rate and content quality), do **not** hard-constrain decoding, and let the classical layer repair — this mirrors the field's best-performing pipeline (prompted grammar + external validator feedback), except we repair deterministically instead of re-prompting.
- Our "consistency-with-stated-grammar rate" metric has no exact published counterpart; the nearest is 2505.14763's "syntax accuracy" under knowledge-prompting (~23–100% depending on model), so reporting it per-model is a contribution.

### Gaps
- No paper found that varies *only* the presence/absence of the schema statement while holding everything else fixed on an *embodied/multi-robot* task (2505.14763 does it for PDDL text domains only).
- "Let Me Speak Freely" has a known partial rebuttal (.txt/dottxt "Say What You Mean" blog arguing careful schema design recovers performance) — not fetched; flag if the thesis leans hard on the "constraints hurt" claim.

## Q3. Plan-similarity / edit-distance metrics in recent evaluations (beyond Fox et al. 2006)

### Takeaway
Levenshtein edit distance over action sequences is now a standard secondary metric in 2025 LLM-planning papers, usually normalized by max sequence length (NED), sometimes with context-weighted edit costs or LCS-based variants; 2508.01300's "Steps-to-Validity" (edit distance to the *optimal* plan) plus per-action quality labels is the richest published scheme.

### Cited Findings
- arXiv:2508.01300 — **VERIFIED**. Defines **Steps-to-Validity (StV)** = Levenshtein distance between generated and optimal plan; **Last Executable Action (LEA)** = index of final valid action; **Action-Quality Mapping (AQM)** with per-action labels {correct, misplaced, same_act, diff_act, redundant}; plus LCS. Finding: 52.3% of failed plans needed effectively complete replanning (complement plan length = ground-truth length) — i.e., edit distance saturates at plan length for half the failures. — [arXiv:2508.01300](https://arxiv.org/html/2508.01300v1)
- An LLM-planning study (surfaced in search, attribution uncertain among the result set) reports average Levenshtein distance 7.22 over 600 instances with mean final plan length 11.7 — unverified and **attribution unclear**; do not cite without pinning the paper. — [search trail](https://arxiv.org/pdf/2506.22604)
- Normalized edit distance (edit distance / max sequence length) used for trajectory/plan proximity, and extended Levenshtein over *tool-call* sequences (insertion/deletion/substitution of calls) in tool-planning evaluations, e.g., CostBench (arXiv:2511.02734) and GRAFT (arXiv:2605.11706) — unverified snippets. — [CostBench](https://arxiv.org/pdf/2511.02734), [GRAFT](https://arxiv.org/pdf/2605.11706)
- Weighted edit distance with custom context-aware per-operation costs proposed in 2025 tool-planning work — unverified snippet, same search trail.
- "Chasing Progress..." (arXiv:2412.10675) uses Longest Contiguous Common Subsequence as an RL *reward*, implicitly a similarity metric between emitted and reference plans. — [arXiv:2412.10675](https://arxiv.org/html/2412.10675v1)

### Inferences
- Our planned edit-distance metric is mainstream; the differentiator is measuring distance to the *minimally repaired feasible* plan (repair cost) rather than to a gold plan — none of the found papers score repair cost, only distance-to-reference. GAVEL (Q5) repairs but reports success rate, not edit magnitude.
- Adopting AQM-style per-action labels (correct / misplaced / substituted / redundant) would give our verbatim/repaired/defaulted provenance a published precedent to cite and extend.

### Gaps
- No found paper normalizes edit distance for *multi-agent interleaved* plans (where swapping agent order is semantically free); we would need to define agent-permutation-invariant distance ourselves.

## Q4. Failure taxonomies of model-emitted plans; "omits the enabling precondition action" analogs

### Takeaway
"Missing prerequisite/enabling action" is a named, first-class error category in current taxonomies — Embodied Agent Interface's "missing-step" error and 2025–26 agent-failure taxonomies' "Logic Error: missing prerequisites" are direct published analogs of our "no recede legs" observation; the MAPF-LLM line documents the geometric version (failure precisely when agents must back out / detour in constrained maps).

### Cited Findings
- Embodied Agent Interface (NeurIPS 2024 D&B oral, arXiv:2410.07166) — **VERIFIED** venue/metrics; its error taxonomy (per search snippets and the paper's known structure) includes **missing-step errors (necessary prior actions omitted)**, additional-step, **wrong-temporal-order errors (preconditions satisfied at a different time point)**, and affordance errors, detected via per-action precondition verification — the exact formalization of "model omits the enabling precondition action." — [arXiv:2410.07166](https://arxiv.org/abs/2410.07166)
- A 2025/26 six-category agent-failure taxonomy (surfaced under "Diagnosing with Insights: Structured Analysis of Agent Failures via Behavioral Abstractions," arXiv:2609.02371, and/or "Agent Planning Benchmark," arXiv:2606.04874 — **attribution between these two unverified**): Goal Understanding / Premature Conclusion / Constraint Violation / **Logic Error (invalid causal dependencies, illogical ordering, missing prerequisites)** / Tool Use Error / Hallucination. — [arXiv:2609.02371](https://arxiv.org/pdf/2609.02371), [arXiv:2606.04874](https://arxiv.org/pdf/2606.04874)
- Coupled failure mode reported in 2025 embodied-planning analysis: invalid action generation (precondition violations the LLM "cannot infer from surface text") and **state drift** amplify each other in a degenerative cycle — unverified snippet from the same search trail.
- arXiv:2508.01300 — **VERIFIED**: >50% of weak-model plans fail at the first action; no monotonic quality decay along the plan (failures are structural, not length-driven) — consistent with omitted-setup-action failures rather than attention decay. — [arXiv:2508.01300](https://arxiv.org/html/2508.01300v1)
- MAPF-LLM (arXiv:2401.03630 / TMLR 2025) — unverified: models succeed on empty maps and fail on room/maze maps, i.e., exactly where plans require non-greedy enabling moves (backing out, waiting, detouring) before progress — the multi-agent geometric analog of missing "recede legs." — [arXiv:2401.03630](https://arxiv.org/abs/2401.03630)
- "Subtle Risks, Critical Failures: A Framework for Diagnosing Physical Safety of LLMs for Embodied Decision Making" (arXiv:2505.19933, 2025) — unverified; safety-oriented failure framework for embodied LLM decisions, relevant for the safety-invariant side of our M4 layer. — [arXiv:2505.19933](https://arxiv.org/pdf/2505.19933)

### Inferences
- Our "no recede legs" case can be framed as a *multi-agent instance of the missing-step error class* (EAI terminology), strengthening the thesis narrative: a known single-agent failure class, shown to persist and interact with geometry in multi-robot congestion.
- No found taxonomy names **symmetry/axis-mirror** errors (choosing the mirrored but infeasible side). That specific failure mode appears unpublished — a citable novelty claim, consistent with our prior presentation-order findings (first-slot/robot_1 priors as symmetry-breaking by position).

### Gaps
- Exact per-category error *rates* (e.g., % of failures that are missing-step) from EAI were not fetched; they exist in the paper body/appendix.
- No published analog found for mirror/axis-choice errors in plan emission (searched via deadlock/warehouse angle); absence of evidence after one targeted search, not a strong claim.

## Q5. Test-time methods that raise plan validity (voting, sample+rank by verifier, refinement without re-prompt loops)

### Takeaway
Three families are quantified in 2025–26: (1) verifier-gated revision (solver/validator feedback) more than doubles PDDL-pipeline performance; (2) sample-then-verify (best-of-N with external or multi-agent verifiers) scales past self-consistency, while pure LLM *self*-verification is known not to help on planning; (3) the newest and most on-thesis: deterministic model-side repair without any LLM call — GAVEL repairs model-derivable violations itself and only returns irreducible ones to the LLM, lifting Qwen3-8B task success from 41.2%→91.8% (single-task) and 19.9%→92.6% (multi-task).

### Cited Findings
- **GAVEL: Graph World Models for Verified and Efficient Long-Horizon LLM Task Planning** (arXiv:2609.19315, submitted 16 Sep 2026, Duke) — unverified snippets, two corroborating sources. Graph world model encodes object relations, action pre/post-conditions, beliefs over unobserved locations; rolls each LLM plan forward, **"repairs model-derivable failures" without another LLM call**, returns only unresolved violations to the LLM at most T=5 times. Qwen3-8B: single-task success 41.2%→91.8%; multi-task 19.9%→92.6%. The closest published system to our verify-and-minimally-repair M3/M4 layer; it does *not* report repair magnitude or provenance fractions — our metrics remain novel. — [arXiv:2609.19315](https://arxiv.org/pdf/2609.19315)
- arXiv:2505.14763 — **VERIFIED**: inference-time revision with solver feedback (~2× syntax) and solver+validator feedback (best, >2× overall) dominates all prompting/pre-inference interventions, including Pass@N. — [arXiv:2505.14763](https://arxiv.org/html/2505.14763v1)
- "On the Self-Verification Limitations of LLMs on Reasoning and Planning Tasks" (arXiv:2402.08115, Kambhampati group) — unverified; the standing negative result that LLM self-critique does not improve plan validity (external sound verifiers do). Any thesis claim should cite this to justify a *classical* verifier over LLM self-check. — [arXiv:2402.08115](https://arxiv.org/pdf/2402.08115)
- Multi-Agent Verification / BoN-MAV (arXiv:2502.20379 vicinity) — unverified: best-of-N with multiple verifier models scales better than self-consistency and reward-model ranking. Sampling-based search + verification lifted Gemini 1.5 Pro past o1-preview on reasoning benchmarks even beyond self-consistency saturation (Berkeley/Google 2025) — unverified snippets. — [papers.cool/2502.20379](https://papers.cool/arxiv/2502.20379), [venturebeat summary](https://venturebeat.com/ai/less-is-more-uc-berkeley-and-google-unlock-llm-potential-through-simple-sampling)
- "When Does Verification Pay Off?" (arXiv:2512.02304, Dec 2025) — unverified; systematic study of verifier value across model families; useful if we need to argue when the classical verifier adds most (weak proposer + strong verifier regime). — [arXiv:2512.02304](https://arxiv.org/html/2512.02304v1)
- **Localized In-Context Learning / "Localizing and Correcting Errors for LLM-based Planners"** (arXiv:2602.00276, 2026) — unverified: identifies the *first constraint violation* in a plan trace and injects a minimal targeted demonstration for the failing step, rather than whole-plan re-prompting — a middle ground between our deterministic repair and full re-prompt loops. — [alphaxiv 2602.00276](https://www.alphaxiv.org/abs/2602.00276)
- INPROVF (ICLR 2025 workshop) — unverified: LLM generates repair candidates for high-level robot controllers, formal methods verify; iterative but with formal gating. — [ICLR page](https://www.iclr.cc/virtual/2025/36231)
- EgoPlan-Bench2 — unverified: plan-level self-consistency (multimodal CoT + self-consistency voting) is part of the +10.24-point training-free gain for GPT-4V — evidence that voting helps even in VLM planning, though on next-action accuracy, not full-plan validity. — [arXiv:2412.04447](https://arxiv.org/abs/2412.04447)

### Inferences
- The literature's efficiency frontier is moving exactly toward our architecture: prompted grammar → single emission → deterministic external verification → *non-LLM repair*, with LLM re-prompt only as escalation. GAVEL is the paper to position against; our contributions beyond it are (a) VLM scene input, (b) multi-robot joint plans, (c) repair *provenance accounting* (verbatim/repaired/defaulted fractions + edit distance) as first-class metrics.
- Since LLM self-verification is a published negative result, framing M3's gate as a *sound* classical verifier (not LLM critique) is both practically and rhetorically supported.

### Gaps
- GAVEL numbers come from secondary summaries of a very recent (Sep 2026) preprint; fetch the PDF before quoting percentages in the thesis.
- No paper found that reports anything like our "defaulted" provenance class (verifier substitutes a safe fallback when repair fails); appears unpublished.

## Cross-cutting source-reliability notes
- VERIFIED this session (content fetched): arXiv:2505.14763 (HTML v1), arXiv:2508.01300 (HTML), arXiv:2410.07166 (abstract/venue), arXiv:2510.20578 (abstract).
- All other numbers are from search snippets or aggregator summaries (alphaxiv, themoonlight, mlanthology); corroborated across ≥2 sources where stated, but quote-check before thesis citation. Particular caution: GAVEL percentages, EgoPlan-Bench2 43.04%, MAPF 62.5%, the "7.22 edit distance" (attribution unresolved), and the six-category taxonomy attribution (2609.02371 vs 2606.04874).
- Several 2026 arXiv IDs (26xx.xxxxx) are legitimate 2026 submissions, but a few search hits (e.g., 2603.08383, 2607.08024, 2605.23023) were not inspected at all — treat as leads only.
