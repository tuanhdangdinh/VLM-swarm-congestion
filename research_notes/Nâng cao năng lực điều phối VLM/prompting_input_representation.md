# Prompting & Input-Representation Techniques for VLM Spatial Multi-Robot Planning (2024–2026)

Scope: input-side techniques (visual prompting, structured-output grammars, spatial CoT variants, temporal input, scene serialization) with measured effects. Positioning: goes beyond the already-known set (GAVEL, PAAI, SyncPlan, RoCo, arXiv:2505.14763, LRR-Bench); those are mentioned only for context. Each entry notes applicability to our setting: a centralized overhead-camera coordinator that emits an ordered multi-robot action plan as JSON.

## KQ1: Which visual-prompt formats (set-of-mark, grid overlays, motion trails, numbered agents) measurably improve multi-object spatial reasoning or planning, and by how much?

### Takeaway
Overlaying discrete alphanumeric marks or a coordinate grid on the image yields the largest measured gains of any input-side intervention: SoM lifts GPT-4V referring comprehension from 25.7 to 86.4 ACC@0.5, and Scaffold's dot-matrix grid adds +13.3 pp on spatial-reasoning benchmarks over textual CoT. Motion-trail overlays (TraceVLA) add ~10% on robot benchmarks but required fine-tuning, not pure prompting.

### Cited Findings
- **Set-of-Mark (SoM), Microsoft.** Overlaying alphanumeric marks on segmented regions lifts GPT-4V referring expression comprehension on RefCOCOg from 25.7 ACC@0.5 (raw coordinate prediction) to **86.4 ACC@0.5** — a +60.7 pp jump from the overlay alone, zero-shot, beating fine-tuned specialists Grounding DINO and PolyFormer (both 85.8). RES: 75.6 mIoU vs PolyFormer's 67.2. Flickr30K phrase grounding 89.2 R@1 (vs Grounding DINO 90.5). — [SoM paper (ar5iv 2310.11441)](https://ar5iv.labs.arxiv.org/html/2310.11441); [arXiv abs](https://arxiv.org/pdf/2310.11441)
- **Scaffold prompting (2024, arXiv:2402.12058).** Overlays a **dot matrix with multi-dimensional coordinate labels** on the image and references the coordinates in text. Average **+9.6 pp over GPT-4V textual CoT across 11 benchmarks** (55.3% vs 48.8%, 1,852 samples). Spatial reasoning is the strongest category: **avg +13.3 pp**, with MME-Position 51.7%→75.0% (+23.3 pp), Visual Spatial Reasoning 70.4%→74.4%, EgoThink-Spatial 74.0%→76.0%; V*Bench +17.4 pp (30.8%→44.6%); HallusionBench-Hard +7.4 pp. — [Scaffold abstract](https://arxiv.org/abs/2402.12058); numbers from arXiv HTML v2 of 2402.12058
- **PIVOT (Google DeepMind, ICML 2024, arXiv:2402.07872).** Casts action selection as iterative VQA: candidate robot actions/trajectories are drawn ON the image as annotated proposals; the VLM picks the best, proposals are resampled around the pick. Enables zero-shot real-robot navigation and manipulation with no robot training data. Gains are reported per-task rather than as one headline number. — [PMLR](https://proceedings.mlr.press/v235/nasiriany24a.html); [ar5iv](https://ar5iv.labs.arxiv.org/html/2402.07872)
- **TraceVLA (ICLR 2025, arXiv:2412.10345).** "Visual trace prompting": overlays the recent **state-action trajectory (motion trail) onto the current frame**. Fine-tuned on 150K trajectories, it outperforms OpenVLA by **10% on SimplerEnv (137 configs) and 3.5x on real WidowX tasks**. Caveat: the trace is an input representation, but the gain was measured after fine-tuning, not as a pure zero-shot prompt effect. — [arXiv](https://arxiv.org/pdf/2412.10345); [ICLR 2025 proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/8667f264f88c7938a73a53ab01eb1327-Abstract-Conference.html)
- **Visualization-of-Thought (VoT), Microsoft, NeurIPS 2024 (arXiv:2404.03622).** Elicits the model to render its own ASCII/grid "mental map" at each reasoning step and condition on it. Significantly improves multi-hop spatial tasks (natural-language navigation, visual navigation, visual tiling in 2D grid worlds); VoT-prompted LLMs **outperformed existing MLLMs** on these tasks. — [arXiv](https://arxiv.org/pdf/2404.03622); [NeurIPS page](https://neurips.cc/virtual/2024/poster/96156)
- **Wonderful Team (TMLR, Feb 2025, arXiv:2407.19094).** Hierarchical multi-agent VLLM framework where a single off-the-shelf VLM does planning plus low-level coordinate extraction from annotated images, zero-shot, validated on VIMABench and real robots; self-corrective agent hierarchy. Quantitative deltas are per-suite rather than one number. — [arXiv](https://arxiv.org/pdf/2407.19094)

### Inferences
- For our coordinator, SoM-style numbered agent marks are the single best-attested intervention: M1's annotation layer already draws robot IDs; the SoM evidence says IDs referenced identically in the JSON plan (robot_1 ↔ mark "1") is what closes the grounding loop, and the failure mode it fixes (raw-coordinate reasoning, 25.7%) is exactly a coordinator asked to reason about unmarked robots.
- Scaffold's coordinate grid is cheap to add to an overhead warehouse frame (known homography → metric grid labels) and its biggest wins are position/relation benchmarks — the congestion-geometry judgments M2 makes.
- PIVOT's propose-and-select loop maps to Layer 2's slow cadence: render 2–4 candidate resolution plans as arrow overlays and let the VLM pick, rather than free-form generation.

### Gaps
- No paper found that isolates "numbered agents on an overhead multi-robot frame" as its own ablation with effect size; SoM/Scaffold numbers are single-image multi-object benchmarks, so transfer to top-down swarm frames is an inference.
- PIVOT and Wonderful Team do not report a single headline effect size comparable across papers.

## KQ2: Does stating an explicit plan GRAMMAR / action vocabulary in the prompt improve plan validity and consistency (beyond arXiv:2505.14763)?

### Takeaway
Yes — the strongest 2024 evidence is Formal-LLM, which compiles a developer-written context-free grammar of valid plans into a pushdown automaton and restricts the LLM's per-step choices to automaton-valid actions, yielding >50% overall performance improvement and eliminating invalid plans.

### Cited Findings
- **Formal-LLM (2024, arXiv:2402.00798).** Developer writes a CFG over the allowed plan structure; it is auto-translated to a pushdown automaton; at each planning step the LLM is prompted with only the valid actions for the current automaton state. Achieves **over 50% overall performance increase** on benchmark and real-life tasks and "prevents invalid and unsuccessful plans." Open-source (agiresearch/Formal-LLM). — [arXiv](https://arxiv.org/pdf/2402.00798)
- The constrained-decoding literature (KQ3) provides the complementary measurement: schema/grammar enforcement raises format validity to 100% (e.g., 0%→100% JSON-schema compliance in a Qwen2.5-7B experiment) — the validity half of the question is uncontested; the debate is only about reasoning quality. — [dev.to practitioner experiment](https://dev.to/vaibhav_mittal_ac22a2c5d6/structured-output-fixed-my-json-and-cut-math-accuracy-by-18-points-jm5)

### Inferences
- Formal-LLM's recipe is directly portable to M3: our action vocabulary (yield/reroute/convoy/backup/swap, per-robot, ordered) is small enough to write as a CFG, and the "valid next actions only" prompting style can be emulated even with closed APIs by enumerating legal actions in the prompt at each step.
- Combined with KQ3: state the vocabulary and plan grammar in the prompt (soft constraint) for the reasoning pass, and enforce the schema (hard constraint) only on the final JSON emission.

### Gaps
- Found no 2024–2026 paper that ablates "action vocabulary stated in prompt" vs "free-form" alone (without machine enforcement) with an effect size; Formal-LLM bundles prompting and automaton restriction. arXiv:2505.14763 (already known) remains the closest ablation.

## KQ3: Constrained decoding / JSON-schema-forced outputs — help or hurt reasoning quality? (the 2024–2025 debate, with measurements)

### Takeaway
The debate resolved to: naive JSON-mode that leaves no room for reasoning hurts (up to −18 pp on reasoning tasks), but well-designed constrained generation — schema includes a reasoning field placed before the answer, prompt states the schema — matches or slightly beats unstructured output, while guaranteeing parseability.

### Cited Findings
- **"Let Me Speak Freely?" (Appier, 2024, arXiv:2408.02442).** Across constrained decoding (JSON-mode), format-restricting instructions, and NL-to-format: "significant decline in LLMs' reasoning abilities under format restrictions," stricter constraints → worse reasoning; but strict formats **improved classification** accuracy by reducing answer-selection errors. Recommends looser restrictions or two-step NL-then-format. — [arXiv](https://arxiv.org/pdf/2408.02442)
- **.txt (dottxt) rebuttal "Say What You Mean" (2024).** Identifies five flaws: mismatched prompts between conditions, JSON prompt that never stated the schema, an AI "parser" (Claude-3-Haiku) that underperformed regex (57% vs 61%), conflation of structured generation with JSON-mode, and ignored classification wins. With matched prompts, **structured ≥ unstructured: GSM8K 0.78 vs 0.77, Last Letter 0.77 vs 0.73, Shuffled Objects 0.44 vs 0.41**. — [dottxt blog](https://blog.dottxt.ai/say-what-you-mean.html)
- **Practitioner replication (Qwen2.5-7B, math).** Constrained decoding raised JSON-schema compliance **0% → 100%** while recoverable math accuracy fell **79.6% → 61.2% (−18.4 pp)** on the same questions — the schema allowed only the answer, demonstrating the "no room to think" failure mode rather than constraint overhead per se. (Practitioner blog; lower evidentiary weight than the two above.) — [dev.to](https://dev.to/vaibhav_mittal_ac22a2c5d6/structured-output-fixed-my-json-and-cut-math-accuracy-by-18-points-jm5)
- **Mechanism for why schema design matters:** with strict structured outputs the grammar compiler turns property order into a finite-state machine; the model "cannot reorder and cannot think first and answer second unless the schema lets it." — [dev.to analysis](https://dev.to/ji_ai/why-json-schema-field-order-breaks-structured-output-accuracy-2985)

### Inferences
- For M2/M3: keep JSON output, but (a) include a free-text `reasoning` field ahead of the decision fields, (b) state the full schema in the prompt, (c) if a provider's strict mode is used, verify the schema's property order permits reasoning-first decoding. Where provider JSON-mode is unavailable (e.g., our Gemini ER-2 path has no think block), the Appier "NL-to-format" two-pass is the measured fallback.
- The classification result cuts our way too: congestion-type classification (a closed label set) is the sub-task where strict formatting *helps*.

### Gaps
- No study found that runs this exact debate on a *multimodal planning* task (all measurements are text reasoning/classification); the transfer to VLM plan emission is assumed, not measured.

## KQ4: Multi-frame or short-history input vs single frame for congestion/dynamic scenes — measured gains?

### Takeaway
Evidence is mixed and thinner than for visual marks: VLM4D (ICCV 2025) shows frontier VLMs systematically fail motion-direction judgments even WITH video input, and one study found naive all-frames input (59.5%) *worse* than iterative keyframe selection (73.3%) — so frame stacking helps only with careful selection; no clean congestion-specific single-vs-multi-frame ablation was found.

### Cited Findings
- **VLM4D (ICCV 2025, arXiv:2508.02095).** First benchmark targeting spatiotemporal (translational/rotational motion, perspective, continuity) reasoning in VLMs; "significant performance gaps compared to human baselines" across SOTA open and closed models; example failure: humans see a car moving right, GPT-4o answers left. VLMs "struggle particularly with integrating multiple visual cues and maintaining temporal coherence"; targeted spatiotemporal fine-tuning and 4D feature fields help. — [ICCV page](https://openaccess.thecvf.com/content/ICCV2025/html/Zhou_VLM4D_Towards_Spatiotemporal_Awareness_in_Vision_Language_Models_ICCV_2025_paper.html); [arXiv](https://arxiv.org/abs/2508.02095v1)
- **"Can World Models Benefit VLMs for World Dynamics?" (2025, arXiv:2510.00855).** Multi-frame inputs "capture more useful semantic features than single frame," and multi-frame reasoning transferred from single-image training "consistently enhances spatial understanding across various benchmarks"; also notes cross-frame reasoning shows "a sharp performance drop compared to within-frame reasoning." — [arXiv](https://arxiv.org/pdf/2510.00855)
- **MosaicThinker (2026, arXiv:2602.07082).** Keyframe-strategy ablation: feeding **all frames scored 59.5% vs 73.3% for an iterative keyframe-selection** approach — more frames is not monotonically better. — [arXiv](https://arxiv.org/pdf/2602.07082)
- (Positioning: LRR-Bench — already in our known set — remains the closest dynamic-scene probe; nothing newer found that ablates 1-frame vs k-frame specifically for congestion.)

### Inferences
- Given VLM4D's finding that models misread motion direction *from raw video*, the better-attested route for our coordinator is to keep a single annotated frame and encode history symbolically/visually instead: M1's velocity arrows and a TraceVLA-style short motion trail per robot put the temporal information into the single-frame channel where VLMs are strongest. This converges with our existing design (annotated frame + state vector) rather than arguing for frame stacks.
- If multi-frame is tried, use 2–3 selected frames (e.g., t−2s, t−1s, t) rather than dense stacks, per the MosaicThinker ablation.

### Gaps
- No paper found with a direct "single annotated frame vs N-frame stack" ablation on a congestion/deadlock or traffic-coordination task with effect sizes — a genuine open measurement (and one our harness could produce cheaply).
- VLM4D's exact human-vs-model percentage gap was not extracted (behind the paper's tables; search snippets only said "significant").

## KQ5: Reasoning-first vs answer-first JSON field ordering; self-consistency / permutation voting for planning outputs

### Takeaway
Field-order evidence is split: the mechanism (strict decoding freezes order, so answer-first schemas forbid pre-answer CoT) is well documented, but a controlled GPT-family experiment found negligible accuracy difference between reasoning-first and answer-first on classification; meanwhile permutation self-consistency — shuffling input list order across samples and aggregating — has large measured gains (up to 34–52%) and maps directly onto our robot-presentation-order bias.

### Cited Findings
- **Field-order experiment (GPT models, classification tasks).** Comparing "reasoning first, answer second" vs "answer first, reasoning second" schemas found "minimal performance differences ... negligible variations in accuracy ... consistent across different GPT model versions and both easy and hard classification tasks"; the CoT-ordering hypothesis "wasn't clearly supported." — [getcoai summary](https://getcoai.com/news/why-field-order-may-not-improve-model-reasoning)
- **Counter-mechanism:** under strict structured outputs the schema's property order is compiled into an FSM, so the model literally cannot emit reasoning before an earlier-ordered answer key — answer-first schemas structurally suppress CoT whether or not a given task benefits from it. — [dev.to analysis](https://dev.to/ji_ai/why-json-schema-field-order-breaks-structured-output-accuracy-2985)
- **Permutation self-consistency (Tang et al., NAACL 2024, arXiv:2310.07712).** Shuffle the input list across k prompts, aggregate output rankings via the Kendall-tau central ranking: improves listwise ranking over conventional inference by **up to 34–52% (Mistral), 7–18% (GPT-3.5), 8–16% (LLaMA-2-70B)**, explicitly marginalizing out prompt-order position bias. — [NAACL 2024](https://preview.aclanthology.org/nschneid-patch-4/2024.naacl-long.129); [arXiv](https://arxiv.org/pdf/2310.07712)
- Related: permutation-based option-shuffling with majority voting is described as widely adopted for de-biasing multiple-choice evaluation (same self-consistency idea, randomness from order rather than sampling). — [arXiv:2510.00628 (position bias in audio-LLMs; surveys the technique)](https://arxiv.org/pdf/2510.00628)

### Inferences
- Reasoning-first ordering is cheap insurance: the null result is from classification tasks, while planning is the regime where pre-answer tokens plausibly matter (consistent with KQ3's finding that strict formats hurt *reasoning* tasks specifically). Keep reasoning-first; don't expect large gains from it alone.
- Permutation voting is the most direct countermeasure in the literature to our measured gpt-4o first-slot/robot_1 prior (presentation-order finding, 2026-09-25): sample the plan under 3–5 shuffled robot orderings and aggregate (majority on strategy; central ranking on robot ordering). The 7–52% listwise-ranking gains are the best available proxy effect size for an ordered multi-robot plan output.

### Gaps
- No paper found applying permutation/self-consistency voting specifically to *robot plan* outputs with success-rate deltas; the gains are measured on ranking/QA tasks.
- The field-order experiment covers GPT classification only; no multimodal or planning-task measurement of field ordering found.

## KQ6 (supporting): Scene-graph or symbolic scene serialization alongside the image

### Takeaway
Serializing the scene into an LLM-friendly hierarchical graph and prompting CoT over its edges beats unstructured scene text by >10 pp success rate in zero-shot navigation (SG-Nav), and coordinate-grounded CoT (SpatialCoT) beats language-only output pipelines on embodied planning.

### Cited Findings
- **SG-Nav (NeurIPS 2024, arXiv:2410.08189).** Online hierarchical 3D scene graph (objects–groups–rooms) serialized for the LLM, with hierarchical CoT traversing nodes/edges plus a re-perception correction mechanism: surpasses previous zero-shot SOTA by **more than 10% SR on all of MP3D, HM3D, RoboTHOR**; first zero-shot method to beat supervised methods on MP3D; decisions are explainable. — [NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/098491b37deebbe6c007e69815729e09-Abstract.html)
- **SpatialCoT (Huawei Noah's Ark, 2025, arXiv:2501.10074).** Two stages: bidirectional coordinate↔language alignment, then CoT "spatial grounding" that translates reasoning into coordinate-based actions; "significantly outperforms previous state-of-the-art" on navigation and manipulation in sim and real; motivated by the finding that language-only outputs limit complex embodied planning. — [arXiv](https://arxiv.org/pdf/2501.10074)

### Inferences
- Our SceneState JSON is already a flat serialization; SG-Nav's result argues for upgrading it to a relational form at prompt time (robot–aisle–zone hierarchy, blocking/approaching edges) rather than a bare robot list — the gain came from structure the LLM can traverse, not from more data.

### Gaps
- No found ablation of "image + scene text" vs "image only" vs "text only" for a *centralized multi-robot* coordinator (GAVEL/RoCo territory; nothing newer with clean deltas).

## Applicability matrix (overhead-camera coordinator → ordered multi-robot JSON plan)

| Technique | Paper (year) | Measured effect | Applies to our coordinator? |
|---|---|---|---|
| Set-of-Mark numbered agents | SoM 2310.11441 | REC 25.7→86.4 ACC@0.5 | Direct — mark IDs = robot IDs in plan JSON |
| Coordinate dot-matrix grid | Scaffold 2402.12058 (2024) | +9.6 pp avg; +13.3 pp spatial | Direct — metric grid via known homography |
| Iterative visual proposals | PIVOT 2402.07872 (ICML 2024) | Zero-shot robot control (per-task) | Yes at Layer-2 rates (0.5–2 Hz) |
| Motion-trail overlay | TraceVLA 2412.10345 (ICLR 2025) | +10% SimplerEnv, 3.5x real | Yes as annotation; gain measured w/ fine-tuning |
| Self-rendered grid sketch | VoT 2404.03622 (NeurIPS 2024) | Beats MLLMs on 2D nav/tiling | Partial — text-side aid for grid-world reasoning |
| CFG/PDA plan grammar | Formal-LLM 2402.00798 (2024) | >50% overall; no invalid plans | Direct for M3 action grounding |
| Schema-in-prompt + reasoning field, constrained emit | dottxt 2024 vs 2408.02442 | Structured ≥ unstructured when prompts matched; naive JSON-mode −18.4 pp | Direct — current M2/M3 output design |
| Multi-frame input | VLM4D 2508.02095; MosaicThinker | Models fail motion from video; all-frames 59.5% < selected 73.3% | Weak — prefer velocity arrows/trails on one frame |
| Reasoning-first field order | getcoai experiment | ~0 on classification | Keep anyway (cheap; planning untested) |
| Permutation voting over agent order | 2310.07712 (NAACL 2024) | +7–52% listwise ranking | Direct — counters our measured robot_1/first-slot prior |
| Hierarchical scene-graph serialization | SG-Nav 2410.08189 (NeurIPS 2024) | >+10 pp SR, 3 benchmarks | Direct — restructure SceneState prompt view |
| Coordinate-aligned CoT | SpatialCoT 2501.10074 (2025) | "Significantly outperforms" SOTA (no digits extracted) | Partial — requires fine-tuning stage |
