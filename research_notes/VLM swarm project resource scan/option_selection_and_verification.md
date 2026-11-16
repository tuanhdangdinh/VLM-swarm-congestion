# Option Selection, Set-Valued Decisions, and Verifier-in-the-Loop for the M2/M3 Grounding-First Planner (2024–2026)

Scope: fixing the grounding-first trade-off (feasibility 0.37 → 1.0, cluster coverage 0.64 → ~0.47) caused by the VLM picking one closest-pair option and under-addressing multi-cluster scenes, plus first-slot and robot-id priors and ER-2's missing temperature control.

Dedup note: items already in the six existing notes are skipped. That covers PriDe 2309.03882, permutation self-consistency 2310.07712, Let Me Speak Freely 2408.02442, Aha Moment Revisited 2506.17417, Position Bias Behind Ceiling 2607.20864, PA-GRPO 2603.21016, LLM-Modulo 2402.01817 and the travel-planning paper 2405.20625, KnowNo, Reflexion, LLMDR 2503.00717, and Garg et al. 2404.06413. Where I add new detail to one of these, I say so. All links were checked on 2026-11-12: arXiv and GitHub URLs returned HTTP 200 or were fetched.

## KQ1: How do LLMs pick SETS of options or several independent sub-decisions, and how is that evaluated?

### Takeaway
The closest primary evidence is SATA-Bench. When asked to "select all that apply", LLMs systematically pick too few options (count bias with a negative signed count error) and avoid certain positions (unselection bias). Better prompting barely helps. Two things help a lot: telling the model how many answers to give, and splitting the question into one sub-question per item. Our coverage drop has the same shape as this count bias. The direct fix is to make the clusters explicit in M3: ask for one decision per cluster, or tell the model the number of clusters K and require exactly K entries.

### Cited Findings
- **SATA-Bench** (Xu et al., Amazon; arXiv 2506.00643, v3 Oct 2025). Tests 27 models on select-all-that-apply questions. The best model reaches only 41.8% exact match. The paper names selection bias and count bias, defined as failing to predict how many answers are correct — [arXiv](https://arxiv.org/abs/2506.00643). Code and data: [GitHub sata-bench/sata-bench](https://github.com/sata-bench/sata-bench).
  - Metrics that map directly onto our "cluster coverage":
    - Jaccard index and exact match over the predicted vs. gold set.
    - Precision, recall, and false-positive rate.
    - Count metrics: CtDif (signed, where negative means under-selection), CtDifAbs, and CtAcc.
    - Positional metrics: SPD, RStd, and RSD — [arXiv HTML v3](https://arxiv.org/html/2506.00643v3).
  - What helps and what doesn't:
    - Reasoning models score slightly higher on Jaccard but "failed to reduce selection and count bias".
    - Most prompting variants gave no consistent gains: changing option symbols, few-shot examples, and going option by option.
    - Telling the model the number of correct answers raised exact match by **+20.95 points** and reduced selection bias. Giving only the dataset-average count hurt.
    - Splitting the question into single-choice sub-questions improved performance by **12.53%** — [arXiv HTML v3](https://arxiv.org/html/2506.00643v3).
  - **Choice Funnel** is the paper's decoding method:
    - It debiases first-token option probabilities with PriDe.
    - It picks the top option, removes it, and repeats.
    - It stops when the model picks a "None of the above" option or when an option's probability passes a threshold τ.
    - Reported results: up to 29% higher exact match than baselines and 64.5% fewer forward passes than yes/no-per-option.
    - It **requires token logprobs**, which the paper says proprietary models generally don't expose — [arXiv HTML v3](https://arxiv.org/html/2506.00643v3).
- **Judging Is Not Enumerating** (Chen et al., arXiv 2608.01000, Aug 2026).
  - Models are much better at judging whether a single candidate belongs to a set than at writing out the whole set. The judging advantage is +0.29 to +0.34 F1 and does not close across a 24× parameter range.
  - **Omission is the dominant error.** Models catch planted over-inclusions 6–7× more often than planted omissions, and a 43k-item production deployment failed omission-first at 10:1 — [arXiv](https://arxiv.org/abs/2608.01000).
- **Beware of Reasoning Overconfidence** (arXiv 2512.01725). On multi-solution tasks, a model's confidence that its solution set is complete significantly exceeds its actual ability to recover the full set — [arXiv](https://arxiv.org/abs/2512.01725). This comes from a search summary; I opened the abstract page only.
- **EVE: Toward Faithful and Complete Answer Construction** (Chen & Fleming, arXiv 2602.06103, Feb 2026). Splits the task into extraction, validation, and enumeration stages. Reports recall up to +24%, precision up to +29%, and F1 +31% — [arXiv](https://arxiv.org/abs/2602.06103). This is staged decomposition, not query-and-merge as one search snippet claimed.
- **New detail on Garg et al. 2404.06413** (already in plan_feasibility_grounding.md). For large teams the v2 paper splits agents into clusters with k-means and assigns a main leader plus sub-leaders. The leaders are chosen by a heuristic (minimum distance to goal), and the foundation model only supplies waypoints. Reach rate "drops significantly when only one leader is used" (Fig. 11, Claude-3-Sonnet VLM N=50, GPT-3.5 N=25; I could not extract the numbers) — [arXiv HTML v2](https://arxiv.org/html/2404.06413v2). The project website listed in the paper returned 404 on 2026-11-12.
- **Hierarchical LLM multi-agent planning** (arXiv 2602.21670). Spreads decomposition and allocation across layers of LLM agents and revises prompts using feedback from a planner check. It notes that most prior methods are open-loop — [arXiv](https://arxiv.org/abs/2602.21670). Known from search summary only.
- **PIP-LLM** (arXiv 2510.22784). Combines PDDL with integer programming; a verifier and debugger check the generated PDDL, and allocation is solved per node of a graph — [arXiv](https://arxiv.org/abs/2510.22784). Known from search summary only.

### Inferences
- **The coverage drop is the SATA count bias.** A single-choice menu forces K=1. Even a multi-select menu would under-select, because both SATA-Bench and 2608.01000 find omission is the default error. Apply to us:
  - M3 clusters the jams before the VLM call and sends one sub-question per cluster ("cluster A: pick one of {a1, a2, a3}; cluster B: pick one of {b1, b2}"). This is SATA's decomposition result (+12.5%).
  - Alternatively, the schema states the count: "exactly K=2 entries, one per cluster_id". This is SATA's told-count result (+21 EM).
  - Either way, coverage is guaranteed by construction rather than left to the model.
- **The Garg et al. precedent** shows that per-cluster leaders, chosen heuristically, beat a single global leader at scale. That supports clustering in M3 and asking the VLM only for the per-cluster choice. It also supports a deterministic fallback per cluster when the VLM abstains.
- **Evaluation for the bench.** Report per-scene:
  - Jaccard and exact match of the addressed clusters vs. the gold cluster set.
  - Signed count error (CtDif) to show under-addressing directly.
  - A positional statistic (the RStd-style spread of chosen slot index), so first-slot bias is measured rather than inferred.
- **"Judge each option" beats "list all options"** (2608.01000). If we keep a multi-select format, a per-option yes/no ("does option X resolve cluster B? yes/no") is the more reliable query. It costs more calls; SATA reports Choice Funnel cut 64% of passes relative to it, but Choice Funnel needs logprobs.

### Gaps
- I found no paper that evaluates multi-select or per-cluster decomposition specifically for multi-robot coordination or spatial VLM scenes. The SATA results are text-only MCQ, so carrying them to our image-plus-state prompt is an inference.
- I could not extract the Garg et al. single- vs. multi-leader numbers from the figure.

## KQ2: Position and first-option bias mitigations cheap enough for an API bench

### Takeaway
Vision-language models carry the same option-position bias as text-only LLMs, and the bias grows with task difficulty. The logit-based fixes are new and recent (2509.16805, SATA's PriDe adaptation), but they need logprobs, which rules them out for Gemini ER-2 and Claude. For closed APIs, permutation voting remains the practical tool, and it was already recommended in adoptable_techniques.md. New in 2025: a label-free permutation-bias metric for measuring the bias, and KV-cache batching to make majority voting cheaper (local models only).

### Cited Findings
- **Fool Your (Vision and) Language Model with Embarrassingly Simple Permutations** (arXiv 2310.01651). Permuting the answer set is an effective adversarial attack on LLMs and VLMs; a VLM example keeps predicting "A" after the correct answer moved — [arXiv](https://arxiv.org/abs/2310.01651).
- **Benchmarking and Mitigating MCQA Selection Bias of LVLMs** (Atabuzzaman, Asgarov & Thomas, arXiv 2509.16805, Sep 2025).
  - Bias grows with difficulty: LLaVA-1.5-13B picks "A" about 3× its true frequency on hard CUB.
  - Mitigation works at inference time on frozen models. It subtracts a confidence-scaled bias vector from the option logits, estimated from content-free templates and a random 10% of real items.
  - Gains: LLaVA Food-hard 54.46 → 60.99; Qwen2.5-VL-7B only +1.15 to +1.84. **Needs logits** — [arXiv HTML](https://arxiv.org/html/2509.16805v1). Code: [GitHub](https://github.com/Atabuzzaman/Selection-Bias-of-LVLMs).
- **Quantifying and Mitigating Selection Bias in LLMs** (Guda et al., arXiv 2511.21709, Nov 2025). Introduces:
  - A label-free **Permutation Bias Metric**: how inconsistent predictions are across answer orderings.
  - **BaQCKV**, which batches question and context in the KV cache to make majority voting over permutations cheaper.
  - An unsupervised LoRA fine-tune.
  - The abstract gives no numbers — [arXiv](https://arxiv.org/abs/2511.21709).
- **CalibraEval** (ACL 2025). A label-free, inference-time method that adjusts observed prediction distributions toward unbiased ones. It targets LLM-as-judge pairwise selection — [ACL Anthology](https://aclanthology.org/2025.acl-long.162). Known from search summary only.
- **Mixed evidence on how universal the bias is.** An LREC 2026 study of 14 multimodal models found predictions sensitive to both choice order and modality order, while a cross-cultural theory-of-mind study found Qwen2.5-VL largely robust to option permutation. Both are from search snippets and were not opened — [search lead: arXiv 2512.17394](https://arxiv.org/abs/2512.17394).

### Inferences
- **For Gemini ER-2, Claude, and gpt-4o-without-logprobs, logit calibration is unavailable.** Use the Permutation Bias Metric as a **diagnostic**: run each bench scene under 2–3 cyclic option orders and report the inconsistency rate per model. That turns the "first-slot prior" finding into a per-model number at 2–3× cost.
- **Per-cluster decomposition (KQ1) also reduces position bias.** Each sub-question has only 2–3 options, and options from different clusters stop competing for slot 1. That is an inference, not something the papers measured.
- **Opaque option IDs.** Labels like "opt_k3" instead of robot-id-ordered letters remove the robot_1 prior at the token level. This follows from the token-bias framing in 2509.16805 and is cheap, but I found no paper testing it in a spatial VLM setting.

### Gaps
- I found no paper giving post-mitigation accuracy for permutation voting on closed-API VLMs in a spatial or robot task.

## KQ3: Verifier-in-the-loop and retry-with-feedback for structured decisions — evidence of gains

### Takeaway
The strongest new 2026 evidence (2607.14167) says it is the **content** of the feedback that drives repair. When the rejection includes the *admissible alternatives*, repair success rises by +42–44 points. Location and observed value alone stay near the raw baseline, and JSON vs. prose formatting makes no difference. This maps directly onto feeding M3's rejection back: return the still-feasible options and the uncovered clusters, not just "infeasible".

### Cited Findings
- **Structured Feedback Improves Repair in an LLM Agent Loop** (Ray & Goyal, arXiv 2607.14167, Jul 2026).
  - Setup: VeriHarness, where external validators own acceptance and budget; 50 paired TextWorld games; 4-call cap.
  - Feedback with location + observed value + **admissible alternatives** raised terminal success from 14 → 36 of 50 (Qwen2.5-Coder-14B) and 8 → 29 of 50 (Llama-3.1-8B).
  - Dropping the alternatives left results near baseline. Prose and keyed JSON gave roughly the same success. The ordering held across budgets and one sampled-decoding setting — [arXiv](https://arxiv.org/abs/2607.14167).
- **Self-Reflective APIs: Structure Beats Verbosity** (arXiv 2606.05037, Jun 2026). On validation failure, returns machine-readable repair suggestions in two types of structured semantic feedback. Experiments cover context-dependent validation, where the model cannot guess the fix — [arXiv](https://arxiv.org/abs/2606.05037). Results not extracted.
- **Robust Planning with Compound LLM Architectures: an LLM-Modulo Approach** (Gundawar, Valmeekam, Verma & Kambhampati, arXiv 2411.14484). Reports "significant performance gains" across four scheduling domains and studies modifications to the framework. A secondary review says these include binary vs. full-critique feedback — [arXiv](https://arxiv.org/abs/2411.14484). This extends the travel-planning case already in our notes; I could not extract the numbers from the abstract.

### Inferences
- **Retry message for M3.** On rejection or under-coverage, the retry should list:
  - which cluster is uncovered,
  - why the option failed,
  - the admissible options per uncovered cluster.

  This is the "admissible alternatives" field that carried nearly all of the gain in 2607.14167. Keep a hard cap (2–3 calls) and a deterministic per-cluster fallback, following the external-validators-own-acceptance design.
- **The coverage gap can be handled as a verifier check.** M3 already knows the clusters, so "decision does not address cluster B" is a checkable rejection that can trigger a single targeted re-ask. It is cheaper than re-asking the whole scene.

### Gaps
- 2607.14167 used text games and small open models. I found no published test of admissible-alternative feedback with frontier VLMs or robot tasks.

## KQ4: Self-consistency and voting for categorical decisions when temperature can't be controlled

### Takeaway
Universal Self-Consistency (USC) generalizes voting to free-form outputs but adds an LLM-as-selector step with its own position bias. For a small categorical menu, plain majority vote over exact-match answers is enough. Without temperature control, diversity has to come from the prompt; Dipper (EMNLP 2025) is the peer-reviewed reference for that.

### Cited Findings
- **Universal Self-Consistency** (Chen et al., arXiv 2311.17311; ICML 2024 workshop). Has the LLM itself choose the most consistent candidate among samples, removing the need for answer extraction. Matches standard self-consistency on math and execution-based voting on code — [arXiv](https://arxiv.org/abs/2311.17311).
- **Limits of USC** (secondary summaries). Later work notes the selection prompt can carry position and self-favor bias. It also notes that USC degrades on short-answer tasks, where standard self-consistency is strong. Both points come from search summaries and are unverified — see [Latent Self-Consistency, arXiv 2508.18395](https://arxiv.org/abs/2508.18395).
- **Dipper** (arXiv 2412.15238, EMNLP 2025 main). A training-free ensemble that feeds one model an optimized set of diverse prompts in parallel. Three Qwen2-MATH-1.5B instances outperform a 7B model on MATH — [arXiv](https://arxiv.org/abs/2412.15238).

### Inferences
- **Recommended voter for ER-2.** Our labels are categorical (strategy × robot × cluster), so exact-match majority vote is enough; do not use USC. For diversity, use Dipper-style prompt variants combined with option permutations, which also debiases (KQ2). Treat a tie or no-majority as an escalation signal sent to the deterministic per-cluster fallback.
- **Vote per cluster, not per scene.** This keeps one cluster's disagreement from discarding a confident decision on another cluster.

### Gaps
- I found no voting results for robot-coordination decisions specifically.

## KQ5: Structured-output and constrained-decoding tools for option choice

### Takeaway
Every provider now supports enum or JSON-schema constraints, which guarantee parseable, in-menu answers but do nothing about which option is chosen. The useful lever is schema shape: put a per-cluster array with fixed length or cluster-id keys in the schema, so coverage is enforced syntactically.

### Cited Findings
- **Gemini structured output.**
  - Supports enum-constrained single-option selection and JSON schema.
  - Property order matters and can be set with `propertyOrdering` — [Gemini API docs](https://ai.google.dev/gemini-api/docs/structured-output).
  - A practitioner benchmark found schema-constrained Gemini outputs can underperform unstructured outputs on some tasks — [Dylan Castillo blog](https://dylancastillo.co/posts/gemini-structured-outputs.html). This is a non-peer-reviewed blog post.
- **JSONSchemaBench** (Geng et al., arXiv 2501.10868; ICML 2025 ES-FoMo workshop).
  - 10k real-world schemas; evaluates Guidance, Outlines, llama.cpp, XGrammar, OpenAI, and Gemini on efficiency, coverage, and quality.
  - Reports constrained decoding can speed generation by up to 50% — [arXiv](https://arxiv.org/abs/2501.10868).
  - Code: [GitHub guidance-ai/jsonschemabench](https://github.com/guidance-ai/jsonschemabench).
- **Open-source constrained-decoding engines** (for llama.cpp or other local backends): [XGrammar](https://github.com/mlc-ai/xgrammar), [Outlines](https://github.com/dottxt-ai/outlines), [llguidance](https://github.com/guidance-ai/llguidance).

### Inferences
- **Schema design for us.** Use an object keyed by M3's cluster ids, where each value is an enum of that cluster's feasible option ids, and mark every cluster key as required.
  - This makes "address every cluster" a syntactic guarantee on Gemini, OpenAI, and llama.cpp.
  - It turns the coverage metric into a pure quality metric (were the right options chosen).
  - Put a short `rationale` field before the choice fields, consistent with the field-order finding already in our notes.
- **Abstention.** Add an explicit `"none_feasible"` or NOTA member per cluster enum, mirroring SATA's finding that NOTA outperforms "I don't know".

### Gaps
- I found no public measurement of whether enum member order inside a schema biases selection on Gemini or OpenAI. It is plausible given KQ2, but untested — worth one cheap permutation check on our bench.
