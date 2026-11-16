# Evaluation Methodology for LLM/VLM-Driven Embodied Planning & Multi-Robot Experiments (2024–2026)

Research notes compiled 2026-10-01. Scope: practices a small-n, pre-registered, two-arm Isaac Sim + Nav2 study can adopt. Verification status is marked per item: **[verified]** = abstract/landing page fetched or primary source confirmed via search; **[search-snippet]** = reported in search result summaries around the primary source, not independently confirmed from the paper body; **[background]** = pre-2024 canonical reference known independently, URL provided.

---

## Q1. Statistical practice for small-n robotics experiments (CoRL/ICRA/RA-L 2024–2026 expectations)

### Takeaway
There is now an explicit, citable best-practices literature for small-n robot policy evaluation: Kress-Gazit et al. (2024) is the anchor citation for "report conditions, use multiple metrics, do statistical analysis, narrate failures," and Miller (2024, Anthropic) is the anchor for how to compute error bars, paired comparisons, and power analysis. No official CoRL/ICRA/RA-L-mandated statistics checklist was found — the field's norm is still weak (modal per-condition n of 10–20 with no CIs), which means a thesis that does paired design + CIs + exact tests is already above the venue median.

### Cited Findings
- "Robot Learning as an Empirical Science: Best Practices for Policy Evaluation" (Hadas Kress-Gazit, Kunimatsu Hashimoto, Naveen Kuppuswamy, Paarth Shah, Phoebe Horgan, Gordon Richardson, Siyuan Feng, Benjamin Burchfiel; Cornell + Toyota Research Institute; arXiv Sep 2024, cs.RO preprint, no venue stated on abstract page) observes that robot-learning papers commonly report success rates with "little to no information regarding the number of runs, the initial conditions, and the success criteria, little to no narrative description of the behaviors and failures observed, and little to no statistical analysis," and proposes four best practices: (1) explicitly report experimental conditions, (2) evaluate several metrics designed to complement success rate, (3) conduct statistical analysis, (4) add qualitative description of failure modes. **[verified — abstract fetched]** — [arXiv:2409.09491](https://arxiv.org/abs/2409.09491)
- Search summaries around this paper state that in recent robot-learning papers the modal per-condition sample size is 10–20 with no confidence intervals or paired tests reported, while more rigorous exemplars report Bayesian posterior credible regions and paired statistical tests at ~50 real trials per condition. **[search-snippet — consistent with the paper's thesis, but the exact numbers should be re-checked in the PDF before quoting in the thesis]** — [arXiv:2409.09491 PDF](https://arxiv.org/pdf/2409.09491)
- Evan Miller, "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations" (arXiv Nov 2024): treats eval questions as a random sample from a population; gives concrete recipes for standard errors on eval scores, **clustered standard errors** (for questions/episodes grouped by scenario), **variance reduction via paired comparisons** (evaluate both systems on the same items and analyze the per-item difference), resampling (run each item k times), and **power analysis** (how many items/repeats are needed to resolve a given effect size). **[verified — abstract page confirmed]** — [arXiv:2411.00640](https://arxiv.org/abs/2411.00640)
- An open-source Python implementation of Miller's methods exists (clustered SEs, paired comparisons, leaderboards, power analysis). **[verified — repo exists]** — [github.com/antonsoo/errorbars](https://github.com/antonsoo/errorbars)
- PhAIL (May 2026) demonstrates that distributional evaluation (time-to-success CDFs + Kolmogorov–Smirnov tests, bootstrap CIs) can resolve model comparisons at **N ≤ 30 rollouts per condition** where binary success-rate comparisons could not — direct evidence that tens-of-episodes-per-cell designs can be statistically defensible when the metric is a full distribution rather than a proportion. **[verified — abstract fetched; details in Q2]** — [arXiv:2605.29710](https://arxiv.org/abs/2605.29710)
- Agarwal et al., "Deep Reinforcement Learning at the Edge of the Statistical Precipice" (NeurIPS 2021, outstanding paper): the canonical small-n prescription in learning-based control — report interquartile mean (IQM) instead of mean/median, stratified bootstrap CIs, performance profiles; implemented in the `rliable` library. Pre-2024 but still the standard citation that 2024–2026 papers point at. **[background]** — [arXiv:2108.13264](https://arxiv.org/abs/2108.13264)
- A third-party "CoRL Paper Reproducibility Guide" exists as a tooling skill (reproducibility manifests, simulator/driver version pinning, seed policies, calibration documentation) but it is **not official CoRL guidance** — it is a community artifact on an MCP marketplace. **[verified as third-party, not venue policy]** — [mcpmarket.com/tools/skills/corl-paper-reproducibility](https://mcpmarket.com/tools/skills/corl-paper-reproducibility)

### Inferences
- For the two-arm design specifically: because both arms run the same frozen scenario battery, a **paired/matched design keyed on (scenario, seed)** is the single highest-value statistical choice — it is exactly Miller's paired-difference variance reduction and Kress-Gazit's "explicit conditions" recommendation combined. Report per-cell paired differences with bootstrap CIs; for binary outcomes (resolved/not, classification correct/not) use McNemar's exact test on paired episodes and Wilson or Clopper–Pearson intervals on proportions; at n in the tens per cell, exact tests dominate asymptotic ones.
- Clustered standard errors (Miller) map directly onto this study's structure: episodes cluster within scenario configurations; naive pooling across the battery understates variance.
- The venue-expectation picture (2024–2026) is best characterized in the thesis as: "no mandated checklist at CoRL/ICRA/RA-L, but an emerging best-practices literature [2409.09491, 2411.00640, 2108.13264] that this evaluation adopts" — that framing is both accurate and reviewer-proof.

### Gaps
- No official CoRL, ICRA, or RA-L author-guideline document mandating statistical reporting was found (NeurIPS has its paper checklist; nothing equivalent surfaced for the robotics venues). If the thesis wants to claim this absence, phrase it as "we found no mandated statistical-reporting checklist at the major robotics venues as of 2026" rather than a categorical negative.
- The exact statistical tests recommended in the body of arXiv:2409.09491 (beyond the abstract-level "conduct statistical analysis") were not extracted; read the PDF before citing specific test recommendations from it.

---

## Q2. Censored-outcome handling (episodes hitting a time horizon): survival analysis / RMST in robotics

### Takeaway
Survival-analysis treatment of robot/agent episodes is just now (2026) appearing — PhAIL explicitly extracts right-censored time-to-success pairs from real-robot rollouts, and an agentic-UQ paper quantifies how badly max-step (administrative) censoring biases naive statistics. Restricted mean survival time (RMST) itself remains a clinical-trials tool with no established robotics precedent found, so adopting KM/RMST for time-to-resolution is both well-grounded (huge biostatistics literature) and near-novel in this domain.

### Cited Findings
- PhAIL ("A Real-Robot VLA Benchmark and Distributional Methodology," Sergey Arkhangelskiy, arXiv 28 May 2026, cs.RO) uses the **time-to-success cumulative distribution function as the evaluation primitive**; per search-result detail it "extracts sequences of times-to-success with event indicators from rollout episodes, using **right-censored pairs** when episodes end with operations remaining." Primary metric is Human-Relative Throughput with bootstrap CIs; significance via Kolmogorov–Smirnov tests per-object, macro-averaged; worked at N ≤ 30 rollouts per condition. The fetched abstract did **not** explicitly mention Kaplan–Meier or restricted means. **[verified abstract + search-snippet for the censoring detail — confirm the censoring estimator in the PDF]** — [arXiv:2605.29710](https://arxiv.org/abs/2605.29710)
- "Proper Scoring Rules for Agentic Uncertainty Quantification" (arXiv 2605.24756, 2026): in a corpus of 308 agent trajectories, 163 completed and 145 hit administrative max-step stops (**47.08% censoring rate**), and admin-censored trajectories were ~3× longer on average than completed ones (30.0 vs 9.88 observed steps) — i.e., censoring is informative and ignoring it badly biases step/time statistics. **[search-snippet — numbers from search summary of the paper]** — [arXiv:2605.24756](https://arxiv.org/pdf/2605.24756)
- RMST methodology (clinical statistics): Royston & Parmar establish RMST ("area under the survival curve up to a cutoff t*") as an alternative to hazard ratios for randomized two-arm trials with time-to-event outcomes; it is valid **without the proportional-hazards assumption**, is reported in plain time units, and the between-arm contrast "difference in RMST up to horizon H" is directly interpretable. **[verified — canonical open-access paper]** — [Royston & Parmar 2013, BMC Med Res Methodol](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3922847/); tutorial-level primer: [Korean J Radiol 2022](https://www.kjronline.org/src/PDFs/kjr-v23n5.pdf); R implementations exist in the `survival`/`survRM2`/`simtrial` ecosystem — [CRAN survival vignette](https://cran.r-project.org/web/packages/survival/vignettes/survival.pdf), [CRAN Task View: Survival](https://cran.r-project.org/web/views/Survival.html)
- Goodman et al. 2004 ("Estimating episode lengths when some observations are probably censored," Statistics in Medicine) — methodological precedent for episode-length estimation under censoring outside robotics. **[verified — publisher page]** — [doi:10.1002/sim.1798](https://onlinelibrary.wiley.com/doi/10.1002/sim.1798)
- No robotics or embodied-AI paper applying RMST by name to robot task completion was found; search results on "RMST + robot task completion" returned only clinical-statistics sources. **[verified absence within search scope]**

### Inferences
- Direct adoption recipe for time-to-resolution with never-resolving episodes: treat each episode's resolution as a time-to-event observation, right-censored at the horizon H; plot per-arm Kaplan–Meier "fraction unresolved" curves; report (a) resolution rate at H with exact binomial CI and (b) **RMST difference up to H** with bootstrap CI as the primary time metric. This cleanly replaces the common-but-biased alternatives (mean time among resolved episodes only, or imputing H for unresolved episodes), and the proportional-hazards-free property matters because yield-vs-reroute strategies plausibly change the *shape*, not just the rate, of resolution.
- PhAIL's KS-on-CDF approach and the KM/RMST approach are compatible: KS answers "are the distributions different," RMST answers "by how much, in seconds." Citing PhAIL + Royston & Parmar together gives both a robotics precedent (2026) and a 10+-year statistical pedigree.
- The ~47% censoring + 3× length asymmetry number from arXiv:2605.24756 is a strong motivating citation for why the thesis's "censoring valve" and horizon handling are necessary rather than cosmetic.

### Gaps
- Whether PhAIL uses Kaplan–Meier specifically (vs empirical CDFs with censored pairs fed to KS variants) is unconfirmed from the abstract — read the PDF method section before citing it as "KM in robotics."
- No field-robotics survival-analysis tradition (e.g., MTBF/failure-time literature) surfaced in these searches; if the thesis wants that lineage (Carlson & Murphy-style UGV reliability work), it needs a separate targeted search.

---

## Q3. Pre-registration in robotics / embodied AI

### Takeaway
Pre-registration exists in robotics only at the margins of HRI (≈3.4% of child-robot-interaction papers; isolated OSF pre-registrations of human-robot teaming studies) and in the statistics community's new template for *simulation studies*. No pre-registered systems-level robot-learning or embodied-AI planning evaluation was found. A pre-registered, git-tag-frozen, two-arm coordinator comparison therefore appears genuinely novel for this subfield — claimable with a "to our knowledge" qualifier and the citations below as the comparison baseline.

### Cited Findings
- A systematic review of reproducibility in child-robot interaction found **only 3.38% of 296 manuscripts reported pre-registration**. **[search-snippet from the review]** — [arXiv:2309.01822](https://arxiv.org/pdf/2309.01822)
- "Registered Reports and Preregistration: A new way to conduct research" (ACM, HRI-adjacent venue) advocates the registered-report model (design peer-reviewed before data collection, in-principle acceptance independent of results) and names OSF pre-registration with embargo as the voluntary alternative. **[verified — ACM DL page]** — [doi:10.1145/3545947.3573352](https://dl.acm.org/doi/10.1145/3545947.3573352)
- Concrete example of a pre-registered robot experiment: "Exploring the Cost of Interruptions in Human-Robot Teaming" was pre-registered on OSF explicitly to avoid HARKing. **[search-snippet]** — [arXiv:2311.00785](https://arxiv.org/pdf/2311.00785)
- The **Simulation Studies Preregistration Template** (Björn Siepe, František Bartoš, Samuel Pawel) is now an official OSF Registries template; the Center for Open Science frames it as letting readers "distinguish between confirmatory and exploratory findings." Directly applicable to an Isaac Sim study. **[verified — COS announcement]** — [cos.io blog](https://www.cos.io/blog/introducing-the-simulation-studies-preregistration-template); Registered Reports overview: [cos.io/initiatives/registered-reports](https://www.cos.io/initiatives/registered-reports)
- Pawel, Kook & Reeve-type argument for why: "Pitfalls and potentials in simulation studies" shows questionable research practices in comparative simulation studies "allow for spurious claims of superiority of any method" — the exact failure mode a two-arm coordinator comparison risks, and the exact argument for freezing configs/oracles before runs. **[verified — arXiv]** — [arXiv:2203.13076](https://arxiv.org/pdf/2203.13076)
- Adjacent field adopting it: software engineering is drafting an OSF-based registered-report template for controlled experiments (2026). **[verified — arXiv listing]** — [arXiv:2602.09292](https://arxiv.org/pdf/2602.09292)
- Searches for pre-registration in embodied AI / robot learning outside HRI returned **no hits** — the general embodied-AI search produced only surveys and unrelated papers with no pre-registration content. **[verified absence within search scope]**

### Inferences
- The thesis's git-tag freeze (prompts, oracles, configs, veto list, model pins, hashes) is functionally equivalent to an OSF pre-registration with timestamping; the COS blog itself lists GitHub/Zenodo as acceptable time-stamping archives per the simulation-template Q&A. Framing: "pre-registration via cryptographically hashed, publicly tagged repository state, following the intent of the OSF Simulation Studies Preregistration Template [COS 2024/25]."
- Novelty claim wording that survives review: "Pre-registration is established in HRI user studies (at ~3% adoption [2309.01822]) and in methodological simulation studies [COS template], but we are not aware of any pre-registered evaluation of an LLM/VLM-based robot coordination system." Do not claim "first pre-registered robotics experiment" — HRI counterexamples exist.
- Optionally mirroring the frozen protocol to OSF (even post-hoc as a timestamped registration pointing at the git tag) would convert an internal discipline into an externally legible credential at near-zero cost.

### Gaps
- Could not exhaustively verify that *zero* robot-learning/embodied-planning papers pre-register — the evidence is absence across several searches plus the 3.38% HRI figure. A dedicated OSF Registries search ("robot" in registration titles) would strengthen the negative claim but was out of call budget.

---

## Q4. LLM-agent evaluation pitfalls: nondeterminism, version drift, prompt sensitivity, seeds

### Takeaway
2025–2026 produced a concrete pitfalls literature: nondeterminism persists even at T=0 (batch-size variation identified as the primary cause, not floating point), silent provider-side model drift is documented as a reproducibility threat with "pin dated snapshots + repeat N times + report variance" as the consensus mitigation, and Princeton's HAL (Oct 2025) is the closest thing to a HELM-for-agents standard (standardized harness, three-dimensional model/scaffold/benchmark analysis, cost-aware).

### Cited Findings
- "Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference" (arXiv 2025/26): identifies **batch-size variation — not floating-point arithmetic — as the primary cause** of nondeterministic outputs under identical inputs. **[search-snippet]** — [arXiv:2506.09501](https://arxiv.org/html/2506.09501v2)
- "LLM Output Drift: Cross-Provider Validation & Mitigation for Financial Workflows" (arXiv Nov 2025): determinism is architecture-dependent — well-engineered 7–8B models achieved perfect output consistency while a 120B model achieved only **12.5% consistency even at T=0.0, greedy decoding, fixed seeds**. **[search-snippet]** — [arXiv:2511.07585](https://arxiv.org/html/2511.07585v1)
- "Reflections on the Reproducibility of Commercial LLM Performance in Empirical Software Engineering Studies" (arXiv Oct 2025): documents provider-side model drift ("a pipeline that performs reliably with one model version may produce degraded or different outputs after a silent backend update"); recommendations include **pinning dated model snapshots (e.g., gpt-4o-2024-08-06, never "latest")** and running each prompt N times reporting mean + variance — "the only honest way to score non-deterministic systems"; notes that statistical power estimation is only feasible in small, highly controlled setups. **[search-snippet]** — [arXiv:2510.25506](https://arxiv.org/pdf/2510.25506)
- Chen, Zaharia & Zou, "How Is ChatGPT's Behavior Changing Over Time?" — the original documentation of large behavioral drift between GPT-4 versions (2023). **[background]** — [arXiv:2307.09009](https://arxiv.org/abs/2307.09009)
- **Holistic Agent Leaderboard (HAL)**: "The Missing Infrastructure for AI Agent Evaluation" (Kapoor, Ströbl, Kirgis, Nadgir + ~25 others, Princeton, arXiv Oct 2025) — standardized, cost-aware, third-party evaluation harness across 9 benchmarks; three-dimensional analysis across **models × scaffolds × benchmarks**; argues standardized harnesses eliminate common implementation bugs; maintains a public reliability dashboard. This is the current reference point for "HELM-style for agents." **[verified — arXiv abstract page confirmed]** — [arXiv:2510.11977](https://arxiv.org/abs/2510.11977); dashboard: [hal.cs.princeton.edu/reliability](https://hal.cs.princeton.edu/reliability/)
- Miller (arXiv:2411.00640, Q1) covers the statistical side of repeated runs: resample each item k times and use clustered SEs rather than treating repeats as independent. **[verified]** — [arXiv:2411.00640](https://arxiv.org/abs/2411.00640)
- Survey of LLM-agent evaluation practice: "Evaluation and Benchmarking of LLM Agents: A Survey" (Mohammadi et al., 2025). **[verified — arXiv listing]** — [arXiv:2507.21504](https://arxiv.org/pdf/2507.21504)

### Inferences
- Thesis-adoptable checklist assembled from these sources: (1) pin dated model snapshot IDs in the pre-registration tag and report them in the paper; (2) record every raw request/response (the study's plan-provenance JSONL already does this); (3) report T=0 but do **not** claim determinism — cite 2506.09501/2511.07585 that T=0 ≠ reproducible, and instead quantify within-condition variance via the repeated episodes; (4) report study dates as a drift bound ("all VLM calls executed between date X and Y against snapshot Z"); (5) treat prompt text as a frozen artifact with its hash in the tag — this doubles as the prompt-sensitivity disclosure (one prompt, declared, not tuned post-hoc).
- The study's existing design (frozen prompts under git tag, model pins + hashes planned at tag time) already implements most of the 2025–2026 recommendations; the main additions worth making are explicit run-date windows and within-cell repeat-variance reporting.
- "Evaluation cards" as a formalized artifact for agents did not surface as an established standard; HAL's harness + logs is the de facto equivalent. Don't cite "evaluation cards" as an established norm.

### Gaps
- No single consolidated "best-practice statement" paper for *API-model-in-the-loop robotics* experiments was found — the pieces above come from SE, finance, and agent-benchmark communities. The thesis can legitimately synthesize them (and that synthesis is itself a minor contribution).
- Prompt-sensitivity *reporting norms* (e.g., mandated paraphrase robustness checks) were not found as an established requirement anywhere; only ad-hoc practice.

---

## Q5. Benchmarks for multi-robot LLM coordination (2025–2026)

### Takeaway
A benchmark ecosystem now exists — PARTNR (ICLR 2025) is the flagship for embodied multi-agent planning, with LLM-Coordination (NAACL 2025), COHERENT, Tool-RoCo (a RoCoBench successor), CoCoBench, MeCoBench and MultiUAV-Plat following in 2025–26 — but none covers centralized VLM coordination of Nav2-driven warehouse robots under congestion/deadlock, so the custom battery should be *situated against* these, not replaced by them.

### Cited Findings
- **PARTNR** (Meta FAIR, ICLR 2025): "A Benchmark for Planning and Reasoning in Embodied Multi-agent Tasks" — 100,000 natural-language human-robot collaboration tasks, 60 houses, 5,819 objects, Habitat 3.0; LLM-in-the-loop task generation with simulation-based grounding/verification; finds SoTA LLMs show "poor coordination and failures in task tracking and recovery from errors"; LLM+human pairs need 1.5× the steps of human-human pairs. **[verified — Meta page, ICLR proceedings PDF, GitHub repo all confirmed]** — [ai.meta.com publication page](https://ai.meta.com/research/publications/partnr-a-benchmark-for-planning-and-reasoning-in-embodied-multi-agent-tasks/); [ICLR 2025 proceedings PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/a3cf318fbeec1126da21e9185ae9908c-Paper-Conference.pdf); [github.com/facebookresearch/partnr-planner](https://github.com/facebookresearch/partnr-planner)
- **LLM-Coordination** (Findings of NAACL 2025): benchmark for pure-coordination settings (agents cooperate to maximize shared gain); evaluates agentic coordination and coordination-QA. **[verified — ACL Anthology]** — [aclanthology.org/2025.findings-naacl.448](https://aclanthology.org/2025.findings-naacl.448/)
- **Tool-RoCo** (arXiv Nov 2025): "An Agent-as-Tool Self-organization Large Language Model Benchmark in Multi-robot Cooperation" — a direct successor line to RoCoBench. **[verified — arXiv listing]** — [arXiv:2511.21510](https://arxiv.org/pdf/2511.21510)
- **COHERENT-Benchmark** (Liu et al. 2025): heterogeneous multi-robot collaboration in dynamic scenarios; metrics include task-allocation efficiency, inter-robot communication, collaborative problem-solving. **[search-snippet — cited via the Springer survey; locate the primary paper before citing]**
- **CoCoBench** (arXiv Aug 2026): "A Cooperative Coordination Benchmark for Embodied Multi-Agent Task Planning." **[verified — arXiv listing]** — [arXiv:2608.28266](https://arxiv.org/pdf/2608.28266)
- **MeCo/MeCoBench** (arXiv Jan 2026): first benchmark for similar-task multi-robot collaboration with memoization; reports reduced planning cost. **[verified — arXiv listing]** — [arXiv:2601.20577](https://arxiv.org/html/2601.20577v2)
- **MultiUAV-Plat** (arXiv Jun 2026): LLM-oriented platform/benchmark for multi-UAV collaborative task planning. **[verified — arXiv listing]** — [arXiv:2606.31073](https://arxiv.org/pdf/2606.31073)
- Surveys to frame the landscape: "Multi-agent Embodied AI: Advances and Future Directions" — [arXiv:2505.05108](https://arxiv.org/pdf/2505.05108); "Large language models for multi-robot systems: a survey" (Autonomous Robots, 2026) — [Springer](https://link.springer.com/article/10.1007/s10514-026-10257-4). **[verified — listings]**

### Inferences
- None of these benchmarks matches the thesis setting (overhead-camera VLM scene reasoning + centralized strategy selection + Nav2 execution + congestion/deadlock resolution with physical dynamics). The strongest positioning move is: cite PARTNR and LLM-Coordination for *what the community measures* (coordination success, steps, recovery-from-error), cite the PARTNR finding of "poor coordination and failure recovery" as motivation, and present the custom battery as filling the navigation-level, physically-grounded coordination gap that tabletop/household benchmarks do not cover.
- The thesis metric set (resolution rate, time-to-resolution, strategy regret vs forced sweeps, plan provenance, churn) is richer than what these benchmarks report (mostly success rate + steps); explicitly comparing metric sets in a related-work table would be an easy, defensible contribution claim.

### Gaps
- No standardized warehouse/Nav2/MAPF-style LLM coordination benchmark surfaced for 2025–2026; "Why Solving Multi-Agent Path Finding with Large Language Models Has Not Succeeded" ([arXiv:2401.03630](https://arxiv.org/abs/2401.03630), **[background — not re-verified in this session]**) remains the closest MAPF-LLM reference point and should be checked for 2025+ successors.
- COHERENT's primary citation (venue, arXiv ID) was not pinned down.

---

## Q6. Reporting API cost / latency / token budgets as experimental variables

### Takeaway
Cost-aware evaluation is now an explicit norm in the agent-evaluation community: "AI Agents That Matter" (Princeton, 2024) made dollar-cost a first-class axis (accuracy–cost Pareto frontiers), and HAL (2025) operationalized it in a standard harness. No robotics-venue-specific norm was found, so importing the Princeton framing is the state-of-the-art move for a robotics thesis.

### Cited Findings
- Kapoor, Ströbl, Siegel, Nadgir & Narayanan, "AI Agents That Matter" (Princeton, arXiv Jul 2024): argues maximizing accuracy without cost control produces misleading conclusions; shows simple repeated-call baselines beat complex agent architectures at far lower cost on HumanEval; proposes visualizing results as a **Pareto curve of accuracy vs inference dollar cost** and jointly optimizing both; argues downstream evaluation should use **dollar cost, not proxies** like parameter count. **[verified — arXiv + multiple corroborating pages]** — [arXiv:2407.01502](https://arxiv.org/pdf/2407.01502)
- HAL (arXiv:2510.11977, Q4) builds cost-awareness into its standard harness and reports cost alongside accuracy across 9 benchmarks. **[verified]** — [arXiv:2510.11977](https://arxiv.org/abs/2510.11977)
- Evaluation cost itself is becoming a recognized constraint ("AI evals are becoming the new compute bottleneck," evalevalai.com, Apr 2026 — community analysis, not peer-reviewed). **[verified page exists; treat as informal]** — [evalevalai.com](https://evalevalai.com/research/2026/04/29/eval-costs-bottleneck/)

### Inferences
- Adoptable reporting block per arm and per episode: tokens in / tokens out, dollar cost at pinned snapshot pricing, wall-clock decision latency (P50/P95), and number of VLM/RAG calls per resolution. For this architecture latency is doubly load-bearing — Layer 2 runs at 0.5–2 Hz, so decision latency is a *system* variable (affects time-to-resolution), not just a cost variable; reporting the latency → time-to-resolution coupling preempts an obvious reviewer question.
- The rule-based arm has ~zero marginal cost, so an accuracy-vs-cost Pareto framing (VLM arm's resolution-rate gain per dollar) is the honest comparison format and directly follows Kapoor et al.'s prescription.

### Gaps
- No robotics paper reporting token budgets as a controlled experimental variable was found; the norm is imported from the LLM-agent community, and the thesis should say so.
