# Inference-Time Techniques for Better Spatial/Temporal/Multi-Step VLM Reasoning (2025–2026)

Scope: techniques adoptable WITHOUT training, judged against our setting — one annotated overhead frame (set-of-mark style), numeric state block, temperature 0, discrete strategy menu, classical verify/repair layer. Research notes compiled 2026-10-01.

## Key Question 1: Visual/multimodal CoT and "thinking with images" — what works for spatial decisions?

### Takeaway
Text-only CoT is now documented to *hurt* visual spatial reasoning across many models and benchmarks; what works is making the model manipulate or receive manipulated images (sketch/crop/zoom/redraw). Gains of ~9–12 pp on spatial tasks are reported for Visual Sketchpad-style tool use, but most of those pipelines need a tool loop, which our single-shot pipeline lacks — the adoptable version is to do the image manipulation ourselves on the annotation side.

### Cited Findings
- "CoT prompting consistently degrades performance in visual spatial reasoning," evaluated across 17 models and 13 spatial benchmarks; a "No-Image++" ablation shows models hallucinate visual details from textual priors even with the image absent; the authors advocate vision-centric reasoning over text-only CoT for spatial tasks — [Chain-of-Thought Degrades Visual Spatial Reasoning Capabilities of Multimodal LLMs](https://arxiv.org/abs/2604.16060) (verified abstract; per-task numbers not extracted).
- LRR-Bench: humans ~90% while VLMs are "close to random guessing in most cases" on relative-movement tasks; "advanced reasoning methods like Chain-of-Thought do not consistently improve spatial understanding" — [LRR-Bench](https://arxiv.org/abs/2507.20174) (verified via abstract/HTML summary).
- Visual Sketchpad (tool loop that lets GPT-4o draw/crop/segment as intermediate reasoning): +11.2% average on math tasks, +9.1% on spatial reasoning, +12.1% on relative depth; SOTA at the time on V*Bench 80.3% and BLINK spatial 83.9% — [Visual Sketchpad, NeurIPS 2024](https://arxiv.org/abs/2406.09403) (verified via paper HTML/search summary).
- OpenAI o3/o4-mini "think with images in their chain-of-thought" (zoom, crop, rotate inside reasoning); o3 reached 95.7% on V* visual search, "largely solving the benchmark" — [OpenAI: Thinking with images](https://openai.com/index/thinking-with-images/) (verified).
- 2025–26 surveys frame the shift from "thinking about images" to "thinking with images" (image as manipulable workspace, interleaved visual state updates) — [Thinking with Images survey](https://arxiv.org/abs/2506.23918); [Image-Grounded CoT survey, ACL 2026](https://aclanthology.org/2026.acl-long.2087.pdf) (verified existence; taxonomy-level only).
- Always-on world-model "imagination" (MindJourney-style, generating hypothetical future views) lifts SAT-Real spatial accuracy: GPT-4o 60.3%→69.3%, GPT-4.1 74.0%→77.3%; adaptive gating (AVIC) reaches 79.3–85.3% — but costs are extreme: always-on = 162.6K tokens and ~12 world-model calls per question vs 0.7K baseline (~230× tokens); AVIC still needs a trained gating policy + world model — [AVIC: When and How Much to Imagine](https://arxiv.org/html/2602.08236) (verified via fetch).

### Inferences
- For us, the actionable form of "thinking with images" is pre-computed, not model-driven: since we control the annotation pipeline, we can render the visual intermediates ourselves (zoomed crop of the congestion zone as a second image tile, schematic redraw) — this captures the mechanism Sketchpad exploits at ~1–2× cost (extra image tokens) with no tool loop. Adoptable: YES.
- Agentic crop/zoom loops (Sketchpad, o3-style): cost 3–10× (multi-turn), needs a backend with tool use; our Gemini/llama.cpp backends don't reliably support it. Adoptable: NO for now; revisit if backend supports native image tools.
- World-model imagination: not adoptable (needs trained world model; 20–230× cost).
- The CoT-degrades finding directly supports keeping our temperature-0 direct classification short, and is a warning against adding long free-text "reason step by step" blocks for the congestion-type call specifically (but see KQ5 — a *bounded* reasoning field before the JSON answer is a different, supported pattern).

### Gaps
- No per-benchmark numbers extracted from 2604.16060 (PDF fetch returned abstract only); magnitude of CoT degradation unknown.
- Found no paper measuring sketch/crop-style visual CoT specifically on top-down/BEV multi-robot scenes.

## Key Question 2: Test-time scaling (self-consistency, best-of-N, verifier selection) — gains on spatial tasks, costs

### Takeaway
Plain majority voting is the robust winner for VLMs; self-verification-based best-of-N is repeatedly shown to be no better or worse, because VLMs cannot distinguish an image-grounded answer from a confident language-prior guess at selection time. For our temperature-0 constraint, the sampling axis is closed on one backend — but voting over *prompt permutations* (which we can always generate) is the equivalent lever and doubles as debiasing (KQ3).

### Cited Findings
- RL-tuned VLMs on GeoQA/MathVista: majority voting beats best-of-N with self-verification in most cells — e.g. VLAA-Thinker-7B GeoQA 52.1% (MV) vs 44.3% (BoN self-verify); R1-VL-7B MathVista 66.0% vs 61.1%; "simple majority voting consistently and substantially outperforms verification-centric strategies"; only 8.3% of responses had confirmed "aha" self-corrections with minimal accuracy correlation; removing the image sometimes *improved* self-verification — [Aha Moment Revisited](https://arxiv.org/abs/2506.17417) (verified via HTML fetch; 4–8 samples ⇒ 4–8× cost).
- Sequential self-correction ("think again") "does not meaningfully improve VLM reasoning"; parallel decoding + voting does — [Aha Moment Revisited](https://arxiv.org/abs/2506.17417) (verified).
- Majority-voting gains plateau early and sit far below Pass@K ceilings on reasoning tasks (one reported case: MV peaks 26.8% at K=10 vs 47.8% Pass@K) — surfaced in search results around [Efficient Test-Time Scaling for Small VLMs](https://arxiv.org/abs/2510.03574) (UNVERIFIED attribution — number came from a search snippet; confirm source before citing).
- Audit of perturbation-grounded selection (re-scoring candidates by stability under perturbed image views): apparent gains up to +31.8 pp over CoT-majority-voting vanish against a format-matched control; "short-answer aggregation on original images is surprisingly effective" as a low-cost baseline; apparent wins were mostly a decoding-format effect (short direct answers vs CoT), not the perturbation signal — [It's the Decoding Format, Not the Perturbation](https://arxiv.org/html/2608.01207) (verified via fetch).
- Spatial-specific test-time scaling exists but via world models, not sampling (see KQ1, AVIC: o1 74.6%→85.3% on SAT-Real) — [AVIC](https://arxiv.org/html/2602.08236) (verified; not adoptable).

### Inferences
- At temperature 0 identical samples are useless, so classic self-consistency is only adoptable on backends with temperature control (cost K×, K=3–5 realistic). On the no-temperature backend (Gemini ER-2), vote over semantically-equivalent prompt variants instead: permuted robot listing order, permuted menu letters, mirrored image with label remap. This is exactly the "aggregate short answers" regime that 2608.01207 found strong, and it cancels order priors simultaneously. Adoptable: YES, K=3–6× cost.
- Do NOT build an LLM-self-verifier selection stage ("which of these answers is right?") — evidence is consistently against it; our classical verify/repair layer is the right verifier (external, symbolic verifiers are not subject to the self-verification failure). Pairwise tournament among spatial options by the same VLM inherits the same failure plus position bias of the comparison itself.
- Because our output is a small discrete menu, voting is cheap to aggregate and ties are a natural "escalate to classical fallback" signal.

### Gaps
- No published numbers found for majority voting specifically on top-down multi-agent coordination choices (who yields); nearest proxies are spatial-QA benchmarks.
- Could not verify any tournament/pairwise-comparison result on spatial option selection; nothing credible found.

## Key Question 3: Debiasing position/order priors beyond randomized ordering

### Takeaway
The literature's strongest fix is permutation *averaging* (marginalize the answer distribution over option orders), which is strictly stronger than per-query randomization (randomization removes bias in expectation across a dataset; averaging removes it per decision). Vision does not shield against this bias. PriDe-style prior estimation gets most of the benefit at near-zero marginal cost.

### Cited Findings
- Permutation-based debiasing "averages the model's prediction distributions under various option permutations, which intuitively cancels out both the model's token bias and position bias" — framing from [LLMs Are Not Robust Multiple Choice Selectors (PriDe), ICLR 2024](https://arxiv.org/abs/2309.03882) (verified existence; PriDe's specific trick — estimate the positional prior on a small sample, then divide it out for all later queries at ~no extra cost — from training knowledge, UNVERIFIED details).
- Position bias can hide behind ceiling effects; exhaustive answer-order permutation per question is proposed as the diagnostic (chi-squared / Cramér's V signature) — [Position Bias is Hidden Behind Ceiling Effects](https://arxiv.org/abs/2607.20864) (verified via search summary).
- In large multimodal models, "visual context does not act as a shield against selection bias — even when visual evidence is clear, a biased model might still select based on position preference" — [Choosing 'Right' from Wrong: Selection Bias in Spatial MCQs in LMMs](https://lacuna.tiptreesystems.com/work/choosing-right-from-wrong-a-closer-look-at-selection-bias-in-spatial-multiple/wrk_ec8f09ea59481162904f4dfe53c392c3) (verified via search summary; secondary source — locate the primary paper before citing formally).
- Multi-image position bias (which image slot gets attended) is its own phenomenon with attention-calibration mitigations (needs logits, so closed APIs excluded) — [Logit-Attention Divergence](https://arxiv.org/abs/2605.11591) (verified existence only).
- Training-time fixes exist (permutation-aware GRPO, permutation-equivariant heads) but are out of scope — [PA-GRPO](https://arxiv.org/html/2603.21016); [AAAI permutation-equivariant](https://ojs.aaai.org/index.php/AAAI/article/view/40401) (verified existence; not adoptable).

### Inferences
- Upgrade path for us: from randomize-per-call → query the model N times with cyclic permutations of the robot list / menu letters and average (or vote). N=3 cyclic shifts ≈ 3× cost and converts our known first-slot/robot_1 prior from a confound into noise *per decision*, not just per experiment. This is the same calls as KQ2's permutation voting — one mechanism, two benefits. Adoptable: YES.
- A spatial-specific debiasing we can add for the left/right-near-chance problem: horizontal-flip consistency — run the mirrored frame with IDs remapped; a left/right answer that doesn't invert under mirroring is prior-driven and should be discarded/escalated. Found no paper doing exactly this for VLM coordination (it's standard test-time augmentation logic); treat as our own inference, cheap (2×) and decision-level.
- Content-free prior calibration (ask with a blank/empty scene to measure the slot prior, then subtract) is the PriDe/contextual-calibration analogue; needs answer distributions or repeated sampling to estimate. Adoptable: PARTIAL (works with logprobs on llama.cpp; not on Gemini without logprobs).

### Gaps
- No measured numbers found for how much permutation averaging recovers on *spatial* MCQ specifically (papers report bias magnitude, not post-averaging accuracy delta, in what I could access).

## Key Question 4: Multi-frame/temporal prompting — 2–3 keyframes vs 1; trails/overlays

### Takeaway
There is now direct decomposition evidence that direction/motion questions get a real multi-frame gain (+17–19 pp full-video over single-frame on TempCompass direction), and direction has only weak *order* dependency — meaning a small unordered set of frames carries most of the signal. This argues for trying 2–3 keyframes; evidence on baked-in motion trails/frame-differencing as a substitute is thin.

### Cited Findings
- Information-ladder decomposition (blank / single repeated frame / full video) on TempCompass with Molmo and Qwen families: overall multi-frame gain ≈ +0.20–0.22; per aspect — Direction +0.17–0.19 multi-frame gain with weak order dependency (+0.12–0.14); Speed +0.11 multi-frame but near-zero order gain (+0.03–0.05); Attribute Change +0.46–0.52; Action only +0.05–0.09 — [What Does a Temporal Benchmark Score Measure?](https://arxiv.org/abs/2607.12304) (verified via HTML fetch).
- LRR-Bench: VLMs on image *sequences* for relative movement are still close to random — multi-frame input alone does not solve motion judgment — [LRR-Bench](https://arxiv.org/abs/2507.20174) (verified).
- Optimal frame sampling is model-specific on MVBench; some tasks solvable from a few salient frames — [Frame Sampling Strategies Matter](https://arxiv.org/html/2509.14769v1) (verified via search summary; small VLMs).
- Tiling many frames into one composite image ("video panels") is studied for long-video understanding — [Video Panels for Long Video Understanding](https://arxiv.org/html/2509.23724v2) (verified existence; no congestion-relevant numbers extracted).
- I found NO 2025–26 paper directly measuring motion-trail or frame-difference overlays baked into a single image vs. true multi-frame input for motion/intent judgment. (Searched; absence noted as a gap.)

### Inferences
- The decomposition result is the best available justification for a cheap A/B in our harness: send t, t−1s, t−2s annotated keyframes (~3× image tokens, 1 call). Direction's weak order-dependency suggests even unordered presentation helps; we should still timestamp-label the tiles. Expected effect is uncertain for an overhead BEV warehouse scene (benchmarks are natural video), but the cost is low and it directly targets our "intent/motion" weakness. Adoptable: YES (experiment-worthy, not guaranteed).
- LRR-Bench tempers expectations: sequences help but don't fix relative-motion reasoning; our velocity arrows + numeric velocities remain the primary motion channel, with keyframes as corroboration.
- Trails baked into one frame: no literature support either way; cheapest option (1× cost, we already can draw them), worth including as an arm in the same A/B rather than assuming it substitutes for keyframes.

### Gaps
- No benchmark isolates "2–3 keyframes" (all compare single frame vs full video or vary sampling density); the 2-3-frame operating point is unmeasured.
- No evidence found on motion-trail overlays (for or against).

## Key Question 5: Structured-output reliability — does strict schema hurt reasoning? Two-pass?

### Takeaway
Strict constrained decoding measurably hurts reasoning (helps pure classification), and 2026 work pins the mechanism on *premature serialization*: performance recovers whenever unconstrained reasoning precedes the structured answer. The supported pattern is reasoning-field-first inside the schema, or two-pass free-form-then-extract.

### Cited Findings
- Format restrictions degrade LLM reasoning, with stricter constraints (JSON-mode > format instructions > NL-then-convert) causing larger drops; JSON-mode can *help* classification-type tasks — [Let Me Speak Freely?, EMNLP 2024 Industry](https://arxiv.org/abs/2408.02442) (verified abstract/summary; the "3–9 pp drop, >15 pp on math" figures came from secondary search summaries — UNVERIFIED exact numbers, check Table in paper).
- "Capacity, Not Format": failures arise from premature serialization — forcing schema-compliant tokens before reasoning completes; "performance recovering whenever unconstrained reasoning precedes structured submission"; both two-pass (reason free, then convert) and reasoning-field-first inside the JSON work — [Capacity, Not Format](https://arxiv.org/abs/2606.09410) (verified via fetch; qualitative — numeric tables not extracted).
- JSONSchemaBench evaluates constrained-decoding engines on 10K real schemas (efficiency/coverage/quality) — [JSONSchemaBench, OpenReview](https://openreview.net/pdf?id=FKOaJqKoio) (verified existence; engine-level, not reasoning-level).
- Interaction with voting: switching from CoT to short direct answers changed VLM accuracy more than the selection mechanism being studied — decoding format is itself a first-order variable — [It's the Decoding Format, Not the Perturbation](https://arxiv.org/html/2608.01207) (verified).

### Inferences
- For us: (a) congestion-type classification can stay strict-JSON (classification is the case where JSON-mode is neutral-to-positive); (b) the multi-robot ordered *plan* is the reasoning-heavy output — put a bounded free-text `analysis` field as the FIRST key in the schema, or run two-pass (free-form plan → second cheap call/regex extract to schema). Two-pass costs ~1.3–2×; reasoning-field-first costs ~1× plus a few hundred tokens. Adoptable: YES — reasoning-field-first is the no-cost default; note tension with KQ1 (keep that field short and structured — e.g. forced per-robot one-liners — since open-ended spatial CoT can hurt).
- Our classical verify/repair layer already compensates for malformed output, so relaxing to "JSON by instruction, not by grammar" on the llama.cpp backend is viable if grammar-constrained decoding is found to clip reasoning.

### Gaps
- No paper measures schema-constraint effects specifically on *spatial* reasoning quality in VLMs (all evidence is text-task LLMs + the format effect observed in 2608.01207).

## Key Question 6: Prompt-level grounding aids — grids, rulers, schematic re-rendering, captioning passes

### Takeaway
Drawing explicit coordinate scaffolds on the image is one of the best-evidenced zero-training aids: a trivial 9×9 grid overlay roughly doubled localization IoU, and axis/mark-grid scaffolds are confirmed helpers in GUI grounding. Schematic re-rendering (image→diagram) and structured object-representation prompting have 2026 support at the concept level; auxiliary captioning passes have weaker direct evidence.

### Cited Findings
- 9×9 black grid, alpha 0.3, 1-px lines, alpha-blended onto COCO val images: IoU 0.27→0.56 (+107%), GIoU 0.18→0.53 (+194%) for coordinate/bbox prediction, as a pure preprocessing step — [Grid-Augmented Vision](https://arxiv.org/abs/2411.18270) (verified via HTML fetch; models tested not clearly specified in paper — weakness to note).
- Coordinate Scaffold, Axis-Grid Scaffold, Mark-Grid Scaffold (drawn axes/labels on screenshots) each improve GUI grounding accuracy at inference time — [How Auxiliary Reasoning Unleashes GUI Grounding in VLMs](https://arxiv.org/abs/2509.11548) (verified existence + method; numbers not extracted).
- Set-of-Mark improves grounding for GPT-4V but "does not transfer well to open-source VLMs" — relevant since one of our backends is open-weight — [Contrastive Region Guidance](https://arxiv.org/html/2403.02325v1) discussion of SoM (verified via search summary); SoM original: [arXiv:2310.11441](https://arxiv.org/abs/2310.11441).
- "Thinking with Blueprints": assisting VLM spatial reasoning via structured object representations (explicit object/coordinate lists) — [arXiv:2601.01984](https://arxiv.org/abs/2601.01984) (verified existence only; aligns with our numeric state block).
- Visual Position Prompt: axis-like position reference overlaid on input improves visual grounding (the training-free global variant is an overlay) — [VPP](https://arxiv.org/html/2503.15426v2) (verified existence; full method involves training).
- Whiteboard-of-Thought (model re-renders the problem as its own matplotlib/diagram before answering) reports large gains on visual/spatial text tasks — [arXiv:2406.14562](https://arxiv.org/abs/2406.14562) (UNVERIFIED numbers — from training knowledge, not fetched; also requires code-execution loop).

### Inferences
- Highest-confidence cheap win for us: add a labeled metric grid (world-frame coordinates, e.g. 1 m cells with axis labels in meters matching the numeric state block's units) to the annotated frame. It attacks two pain points at once: left/right near chance (explicit axes give the model a frame of reference) and the ignored geometry text block (the image now *shows* the same coordinates the text states, letting cross-modal agreement do the grounding). Cost ~1×. Adoptable: YES — top recommendation of this section.
- Bird's-eye schematic re-rendering: we can render a clean schematic (flat colors, no photoreal clutter) alongside or instead of the camera frame. Two project-internal facts make this promising: our synthetic frames produced 0/240 refusals vs ~22–25% on realistic frames, and congestion topology survives schematization. Literature support is indirect (blueprint/diagram prompting), so frame it as an experiment; it is also the only identified mitigation for the realistic-frame refusal problem that stays prompt-level. Cost ~1× (2× if dual-image).
- Auxiliary captioning pass (describe scene first, then decide): weak direct evidence, and KQ1's text-CoT warning applies — a *constrained* perception pass (extract per-robot facts into a table, then decide from the table) is safer than free captioning. Low priority.

### Gaps
- Grid-overlay evidence is for localization/pointing, not for relational judgments (who is left of whom, who should yield); transfer to our decision task is plausible but unmeasured.
- No paper found on schematic re-rendering specifically reducing VLM refusals; that link is our own hypothesis from project data.

## Cross-cutting adoption summary (for the report writer)

| Technique | Evidence strength | Measured gain (source task) | Cost | Adopt? |
|---|---|---|---|---|
| Labeled metric grid/axes on frame | Strong (localization) | IoU 0.27→0.56 ([2411.18270](https://arxiv.org/abs/2411.18270)) | ~1× | Yes — first |
| Reasoning-field-first / two-pass JSON for plans | Strong (text LLMs) | Recovers premature-serialization losses ([2606.09410](https://arxiv.org/abs/2606.09410), [2408.02442](https://arxiv.org/abs/2408.02442)) | 1–2× | Yes |
| Permutation voting/averaging (robot order, menu letters) | Strong (MCQ bias lit) | Cancels position+token bias per decision ([2309.03882](https://arxiv.org/abs/2309.03882)) | 3–6× | Yes |
| Mirror-flip consistency check for left/right | Inference (TTA logic) | unmeasured | 2× | Yes (as validity gate in classical layer) |
| 2–3 timestamped keyframes | Moderate (video decomposition) | Direction +17–19 pp full-video vs 1 frame ([2607.12304](https://arxiv.org/abs/2607.12304)) | ~3× image tokens | Experiment |
| Schematic (synthetic-style) re-render | Weak lit + strong project data (refusals) | unmeasured for decisions | 1–2× | Experiment |
| Pre-cropped congestion-zone zoom tile | Moderate (Sketchpad mechanism, [2406.09403](https://arxiv.org/abs/2406.09403)) | Sketchpad +9.1% spatial (agentic version) | ~1.5× | Experiment |
| Temperature>0 self-consistency | Strong but plateaus | e.g. MV >> self-verify BoN ([2506.17417](https://arxiv.org/abs/2506.17417)) | K× | Only on backends with temp control; prefer permutation voting |
| VLM self-verification / pairwise tournament | Strong NEGATIVE | MV beats it ([2506.17417](https://arxiv.org/abs/2506.17417), [2608.01207](https://arxiv.org/html/2608.01207)) | — | No |
| Long free-text spatial CoT | Strong NEGATIVE | Degrades across 17 models/13 benchmarks ([2604.16060](https://arxiv.org/abs/2604.16060)) | — | No |
| Agentic crop/zoom tool loops, world-model imagination | Strong but infra-heavy | V* 95.7% (o3); SAT-Real +9–11 pp (AVIC) | 3–230× | No (infra/cost) |
