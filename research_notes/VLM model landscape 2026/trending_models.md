# VLM Model Landscape for Embodied/Spatial Reasoning (as of 2026-10-06)

Research notes for choosing the next VLM backends for the congestion-coordinator thesis. Verification key:
- **VERIFIED** = fetched from provider docs / HF / arXiv during this session (2026-10-06).
- **SEARCH-REPORTED** = from web-search result summaries; primary page not fetched directly.
- **UNVERIFIED** = from memory or task brief; treat as lead, not fact.

---

## Q1: Which VLMs do 2026 robotics/embodied papers actually evaluate, and which top late-2026 spatial/embodied benchmarks?

### Takeaway
The recurring eval-table roster in 2026 multi-robot/embodied papers is: GPT-5.x (GPT-5.2 appears by name), Gemini 3 Pro, Claude Opus 4.x, and Qwen3-VL (open-weight workhorse, 8B–235B). On embodied benchmarks (ERQA, VSI-Bench), late-2026 leaders are Qwen-family and Gemini 3 Pro among proprietary models, and Qwen3-VL / InternVL3.5 / Molmo2-ER among open weights — all VLMs still score well under human level, and plain-VLM baselines on actual multi-robot coordination tasks remain weak without scaffolding.

### Cited Findings
- A 2026 multi-agent path-planning paper reports plain-VLM waypoint-generation baselines on 2-robot coordination: best was Gemini-3-Pro at 16.67% success; GPT-5.2 10.0%; Claude Opus 4.5 0%; with their CaPE scaffolding, GPT-5.2 reaches 76.6% and Claude Opus 4.5 73.3% — numbers surfaced in search results around [Safe and Interpretable Multimodal Path Planning for Multi-Agent Cooperation (arXiv:2602.19304)](https://arxiv.org/pdf/2602.19304); **SEARCH-REPORTED, exact paper attribution of the numbers not confirmed by fetching the table**.
- [RoboTalk (arXiv:2609.23997)](https://arxiv.org/pdf/2609.23997) shows small open VLMs like **Qwen3-VL-8B-Instruct** coordinating in decentralized, partially-observable multi-robot tasks — SEARCH-REPORTED.
- [Safe Multi-Robot Coordination via VLM-LLM Reasoning and Reachability Analysis (arXiv:2609.27816)](https://arxiv.org/abs/2609.27816) (Dwedar, Hafez, Jesser, Alanwar) uses a VLM + LLM split for heterogeneous-team safety, but the abstract does not name the models — VERIFIED (abstract fetched; model names not in abstract).
- Other 2026 multi-robot VLM systems surfaced: COMRES-VLM (multi-robot exploration/search coordination) and GoalVLM (zero-shot cooperative object navigation) — SEARCH-REPORTED, model rosters not extracted.
- **ERQA leaderboard** (400 MCQ embodied-reasoning benchmark from the Gemini Robotics paper): as of 2026-09-10, Qwen3.8 Max leads at 77.8%, then Qwen3.8-Flash-Next 72.3%, Seed 2.1 Pro 72%, Qwen3.7-Plus 69.8%; in March 2026 Gemini 3 Pro led at 70.5% — [benchlm.ai ERQA](https://benchlm.ai/benchmarks/erqa); [benchmarklist.com ERQA](https://benchmarklist.com/benchmarks/erqa/) — SEARCH-REPORTED (leaderboard aggregator sites, not primary).
- **VSI-Bench** (most-used spatial benchmark): InternVL3.5 scales from 49.3 (1B) to 69.5 (largest); InternVL3.5-1B alone beats Qwen2.5-VL-72B — [InternVL3.5 paper (arXiv:2508.18265)](https://arxiv.org/pdf/2508.18265) — SEARCH-REPORTED from the paper's own numbers.
- **Molmo2-ER** (Ai2): embodied-reasoning finetune of Molmo2; claims to beat every open-weight baseline and the strongest closed models on 9 of 13 embodied-reasoning benchmarks, averaging 63.8% — [Ai2 MolmoAct2 blog](https://allenai.org/blog/molmoact2); [MolmoAct2 paper (arXiv:2605.02881)](https://arxiv.org/pdf/2605.02881) — SEARCH-REPORTED.
- New 2026 spatial benchmarks to know: **SpatiaLab** ([ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/31ab8d228b704e86d9eb87f072d2f5dc-Abstract-Conference.html)), **InternSpatial/InternSpatial-Bench** ([ICLR 2026](https://mlanthology.org/iclr/2026/deng2026iclr-internspatial/)), **SpaMEM** (dynamic spatial reasoning, [arXiv:2604.22409](https://arxiv.org/pdf/2604.22409)), **ERQA-Plus** ([arXiv:2606.17639](https://papers.cool/arxiv/2606.17639)) — SEARCH-REPORTED.
- Qwen3-VL claims top spatial-reasoning scores vs Google/OpenAI (SpatialBench; rotated bounding boxes, depth estimation) — SEARCH-REPORTED from a low-quality aggregator; treat as marketing-adjacent until checked against the Qwen3-VL tech report.

### Inferences
- The "N models" eval roster that matches 2026 literature practice is: one OpenAI GPT-5/6-family model, one Gemini (ER or 3-Pro), one Claude, one Qwen3-VL size, plus optionally one robotics specialist (Cosmos Reason2 or Molmo2-ER). That is exactly the family spread our adapters can reach.
- Chance-level plain-VLM performance on multi-robot waypoint tasks in the 2602.19304 cluster mirrors our own gpt-4o-at-chance finding — our result is consistent with the literature, which strengthens the thesis framing (scaffolding/grounding, i.e. our M3, is what makes VLM coordination work).

### Gaps
- Could not verify the Garg PMLR 2026 paper's exact model list (task brief says GPT-5 variants, GPT-4o/-mini, GPT-4, Claude models) — no search performed against PMLR directly; UNVERIFIED.
- RoboSpatial and EgoPlan-successor late-2026 leaderboards specifically: no current leaderboard found in this session; ERQA and VSI-Bench results stand in.
- The exact paper behind the GPT-5.2/Claude-Opus-4.5/Gemini-3-Pro CaPE numbers needs one fetch of arXiv:2602.19304's eval table before quoting in the thesis.

---

## Q2: Robotics-specialized lineage — newer Gemini ER? Cosmos Reason2 availability? Others?

### Takeaway
We are already on the newest Gemini robotics model: `gemini-robotics-er-2-preview` (shipped ~2026-07-30) is still the current release, with ER 1.6-preview as the deprecated predecessor. NVIDIA Cosmos Reason2 is fully open (2B/8B/32B weights on HF, NIM API on build.nvidia.com) and is the most integration-ready robotics specialist for a local/OpenAI-compatible adapter.

### Cited Findings
- **Gemini Robotics ER 2**: exact model ID `gemini-robotics-er-2-preview`, still preview (not GA); accepts text, image, video, audio; 131,072 in / 65,536 out tokens; supports structured outputs, function calling, caching; a `gemini-robotics-er-2-streaming-preview` variant exists; the docs page does **not** document temperature or thinking controls — [ai.google.dev ER-2 model page](https://ai.google.dev/gemini-api/docs/models/gemini-robotics-er-2-preview) — **VERIFIED (fetched 2026-10-06)**.
- ER 2 shipped 2026-07-30 with 91.3% moment-finding accuracy, ~4x execution speed of the previous generation, multi-robot (two-body) coordination support — [Seeking Alpha](https://seekingalpha.com/news/4574852-googles-deepmind-launches-more-advanced-gemini-robotics) — SEARCH-REPORTED.
- `gemini-robotics-er-1.6-preview` still listed on the Gemini models page; third-party reporting says ER 1.6 preview shuts down 2026-08-31 (already past) — [Gemini models page](https://ai.google.dev/gemini-api/docs/models) VERIFIED for the listing; [gigazine](https://gigazine.net/gsc_news/en/20260415-google-gemini-robotics-er-1-6) SEARCH-REPORTED for the shutdown date (conflicts with it still being listed — unresolved).
- **NVIDIA Cosmos Reason2**: open, released 2025-12-19 under the nvidia-open-model-license; sizes **2B, 8B, 32B**; vision input with 2D/3D point localization and bounding-box outputs plus reasoning text; weights on HF ([Cosmos-Reason2-32B](https://huggingface.co/nvidia/Cosmos-Reason2-32B), [Cosmos-Reason2-2B](https://huggingface.co/nvidia/Cosmos-Reason2-2B)); hosted API/NIM via [build.nvidia.com model card](https://build.nvidia.com/nvidia/cosmos-reason2-8b/modelcard); also served by AWS Marketplace, Vultr, Featherless — **VERIFIED model existence/variants via HF + build.nvidia.com listings in search; license/date SEARCH-REPORTED**.
- Cosmos Reason2 robotics evidence: NVIDIA's own Physical AI Bench numbers (2026-04-28): Cosmos-Reason2-32B robotics score 60.60 vs Qwen3-VL-32B-Instruct 55.06, across ERQA, CR-Common, CR-Embodied, Where2Place — [build.nvidia.com](https://build.nvidia.com/nvidia/cosmos-reason2-8b/modelcard) — SEARCH-REPORTED (vendor-reported benchmark; independent robotics-paper adoption of Reason2 not found this session).
- **MolmoAct2** (Ai2, released 2026-05-05): fully open VLA with 3D-aware reasoning, 400K+ downloads; its **Molmo2-ER** VLM backbone is the embodied-reasoning model relevant to us (perception, pointing, multi-image, temporal) — [allenai.org/blog/molmoact2](https://allenai.org/blog/molmoact2) — SEARCH-REPORTED.
- **RoboBrain 2.0** (BAAI): spans affordance prediction, spatial referring, trajectory forecasting, **multi-agent coordination**, scene-graph construction — [arXiv:2507.02029](https://arxiv.org/pdf/2507.02029) — SEARCH-REPORTED; no 2026 "RoboBrain 3" found this session.

### Inferences
- No action needed on the Gemini side: `gemini-robotics-er-2-preview` is the newest ER; the only watch-item is preview-model churn (ER 1.6 got ~4 months before shutdown notice), so pin outputs/logs now for reproducibility.
- Cosmos Reason2-8B is the best robotics-specialist addition: open weights remove the preview-deprecation reproducibility risk that ER-2 carries, and its bbox/point outputs match our annotated-overhead-frame task shape.

### Gaps
- No independent (non-NVIDIA) robotics paper found this session that uses Cosmos Reason2 as a baseline; adoption evidence is vendor-published.
- Whether Cosmos Reason2 has GGUF/llama.cpp support is unverified — plan on vLLM (OpenAI-compatible server) instead; it's on HF with standard inference-provider support.
- Molmo2-ER weight availability/serving path (vLLM? GGUF?) not checked.

---

## Q3: Frontier generalists with vision, October 2026 — verified model IDs

### Takeaway
OpenAI's flagship line has moved to a GPT-6 family (`gpt-6-astra` flagship; `gpt-4o` still served); Anthropic's current line is Opus 5.5 / Sonnet 5.5 / Haiku 4.5 (all vision-capable, but current-gen Claude **rejects non-default temperature**, which conflicts with our temperature-0 preference); Gemini's generalist line is the Gemini 3.x family with `gemini-3.1-pro-preview` at the top. Among open weights, Qwen3-VL is the clear spatial-evidence leader and ships official GGUFs with native llama.cpp support (2B–235B).

### Cited Findings

**OpenAI — VERIFIED from provider docs (fetched 2026-10-06), with a naming inconsistency to flag:**
- [developers.openai.com/docs/models](https://developers.openai.com/docs/models): flagship **`gpt-6-astra`** ("most capable", vision input, reasoning levels low→max, 1.05M context, cutoff 2026-04-30); **`gpt-6.1-sol`** (balanced, vision, 1.05M); **`gpt-6-luna`** (cheap/high-volume, vision). All support Responses API, structured outputs, tools.
- [developers.openai.com/docs/guides/images-vision](https://developers.openai.com/docs/guides/images-vision): vision-capable IDs listed include `gpt-6-astra`, a 5.x line (`gpt-5.6-*`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.2`, `gpt-5.1`) and legacy `gpt-4.1`, **`gpt-4o`, `gpt-4o-mini`** (still served). The guide explicitly warns these models perform poorly on "tasks requiring precise spatial reasoning."
- **CONFLICT**: the two doc fetches returned inconsistent suffix naming (`gpt-5.6-sol/terra/luna` vs `gpt-6.1-sol`/`gpt-6-luna`). WebFetch summarization may have garbled names. **Before wiring, confirm exact IDs with `GET /v1/models`** against the live API.
- 2026 robotics papers cite "GPT 5.2" in eval tables (see Q1) — so 5.x snapshots remain the literature-comparable choice even as 6.x ships.

**Anthropic — VERIFIED from the bundled Claude API reference (cached 2026-09-25; cross-check platform.claude.com/docs before wiring):**
- Current models: **`claude-opus-5-5`** ($4/$20 per MTok, 1M context, current default Opus), `claude-opus-5`, **`claude-sonnet-5-5`** ($2/$10), `claude-sonnet-5`, `claude-sonnet-4-6`, **`claude-haiku-4-5`** ($1/$5, 200K). All take image input (base64/URL content blocks).
- **Constraint for us**: on Opus 5.5 thinking cannot be disabled and sampling params (`temperature`/`top_p`/`top_k`) return 400; Sonnet 5.5 400s on non-default temperature; Haiku 4.5 still accepts `temperature`. So "temperature=0" is not expressible on current-gen Claude — determinism must come from structured outputs (`output_config.format` / `strict: true`) + low effort instead.
- Robotics-paper usage: Claude Opus 4.5 appears in 2026 multi-robot eval tables (Q1); task brief says Garg PMLR 2026 used several Claude models (UNVERIFIED).

**Google generalists — VERIFIED listing (fetched 2026-10-06), names possibly summarizer-garbled:**
- [Gemini models page](https://ai.google.dev/gemini-api/docs/models): top preview **`gemini-3.1-pro-preview`**; stable Flash line reported as `gemini-3.8-flash` … `gemini-3.5-flash-lite`; `gemini-2.5-pro`/`-flash` still listed (limited access). The dense 3.5–3.8 Flash versioning looks unusual — re-verify exact IDs on the page before wiring.
- Gemini 3 Pro was the top proprietary ERQA scorer in March 2026 (70.5%) and the best plain-VLM baseline in the Q1 coordination paper — the strongest generalist-with-spatial-evidence at Google.

**Open weights:**
- **Qwen3-VL** (Alibaba): official GGUF releases + native llama.cpp support merged upstream, sizes 2B–235B incl. [Qwen3-VL-30B-A3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF) and community [4B GGUF](https://huggingface.co/bartowski/Qwen_Qwen3-VL-4B-Instruct-GGUF); HF cards document `llama-server` OpenAI-compatible serving; runs CPU/CUDA/Metal/Vulkan — **VERIFIED via HF listings**. Spatial evidence: used in RoboTalk (8B), beaten-but-close baseline in NVIDIA's robotics bench (32B), RefCOCO-avg leader (235B-A22B-Thinking 92.1%, [benchmarklist](https://benchmarklist.com/benchmarks/refcoco_avg/) — SEARCH-REPORTED).
- **InternVL3.5** (Shanghai AI Lab): best open-source VSI-Bench scaling story (49.3→69.5), evaluated on VSI-Bench/ERQA/Space10/OmniSpatial — [arXiv:2508.18265](https://arxiv.org/pdf/2508.18265) — SEARCH-REPORTED; no newer InternVL4 found this session.
- Llama vision and Pixtral/Mistral: **no 2026 spatial/embodied evidence surfaced in any of this session's searches** — they did not appear in any eval table or benchmark result found. Treat as low-priority.

### Inferences
- gpt-4o is now two generations behind OpenAI's own line; keeping it as the "weak frontier baseline" is defensible historically, but a GPT-5.x or 6.x snapshot is needed for a current-generation claim — and it drops into the existing OpenAI adapter unchanged.
- For strict JSON with reasoning-first field ordering, every candidate (OpenAI structured outputs, Gemini structured outputs on ER-2, Claude `output_config.format`, llama.cpp grammar/json_schema on Qwen3-VL) has a native mechanism; the Claude adapter just can't pin temperature.

### Gaps
- Exact OpenAI snapshot-ID strings (dated snapshots à la `gpt-4o-2024-08-06`) were not resolvable from the fetched summaries; resolve via `GET /v1/models` at integration time.
- Anthropic model IDs come from a reference cached 2026-09-25, not a live fetch of platform.claude.com — re-check at integration (low risk; IDs are undated strings).
- No fetch of Qwen3-VL technical report for first-party spatial numbers.

---

## Q4: Which 2–3 additions give maximal family diversity at minimal integration cost?

### Takeaway
Recommended additions, in order: (1) **Qwen3-VL (8B or 30B-A3B, GGUF via the existing llama_server adapter — zero new adapter code, open-weight reproducibility)**, (2) **Claude Sonnet 5.5 or Opus 5.5 via the existing Anthropic adapter** (third frontier lab, literature-standard family; mind the no-temperature constraint), (3) **Cosmos Reason2-8B served with vLLM behind the existing OpenAI-compatible adapter** (robotics specialist, open weights, bbox/point outputs). That yields 5–6 model families across 5 labs (OpenAI, Google, Anthropic, Alibaba, NVIDIA) with ~zero new adapter surface.

### Cited Findings
- Qwen3-VL: official GGUFs + llama.cpp native support + documented `llama-server` OpenAI-compatible serving — [Qwen3-VL-30B-A3B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct-GGUF) — VERIFIED listing. Appears in 2026 robotics papers (RoboTalk 8B) and NVIDIA's own comparisons — SEARCH-REPORTED.
- Cosmos Reason2: open weights 2B/8B/32B on HF + hosted NIM API — [HF](https://huggingface.co/nvidia/Cosmos-Reason2-32B), [build.nvidia.com](https://build.nvidia.com/nvidia/cosmos-reason2-8b/modelcard) — VERIFIED listings; CLAUDE.md already names Cosmos Reason2 under External Library Verification, i.e. it was a planned backend for this project.
- Anthropic adapter already exists in the codebase (task brief); current vision-capable IDs `claude-opus-5-5` / `claude-sonnet-5-5` / `claude-haiku-4-5` — VERIFIED per bundled API reference (cached 2026-09-25).
- OpenAI adapter upgrade path: `gpt-4o` → a `gpt-5.x`/`gpt-6` snapshot is a config change on the existing adapter — [OpenAI models docs](https://developers.openai.com/docs/models) — VERIFIED that the 6.x family exists with vision; exact ID to be confirmed live.

### Inferences
- **Priority 1 — Qwen3-VL via llama_server**: the single highest-value add. Open weights kill the API-churn reproducibility problem (ER-2 is a preview that can vanish, as ER 1.6 did); it is the open-weight family 2026 robotics papers actually use; and the llama_server adapter already speaks its serving protocol. Choose 8B-Instruct if VRAM-bound (matches RoboTalk), 30B-A3B (MoE, ~3B active) for better quality at similar throughput.
- **Priority 2 — Claude Sonnet 5.5** (cheaper) or Opus 5.5 (stronger): completes the OpenAI/Google/Anthropic frontier triad that the Garg-style papers use, with an adapter already written. Requires one adapter tweak: do not send `temperature` to current-gen Claude; rely on structured output + fixed prompts.
- **Priority 3 — Cosmos Reason2-8B via vLLM → OpenAI-compatible endpoint**: gives a second robotics-specialist to pair against ER-2 (specialist-vs-specialist comparison), at the cost of standing up vLLM on the Isaac workstation VM (L4 GPU should hold 8B at fp8/awq; 32B will not fit).
- Optional cheap 4th: bump the OpenAI adapter's model string from `gpt-4o-2024-08-06` to a current GPT-5.x/6 snapshot — near-zero cost, and directly tests whether the gpt-4o chance-level conflict prediction and refusal behavior persist in the current generation.
- Family-diversity accounting for the thesis claim: currently 2 labs (OpenAI, Google). With the three additions: 5 labs, mixing closed API (3), open-weight generalist (1), open-weight robotics specialist (1), plus two robotics-specialized lineages (ER-2, Cosmos) vs three generalists — a strong "N models, M families" generality table.

### Gaps
- Cosmos Reason2 vLLM serving recipe and whether its chat template supports multi-image (frame + zoom) input: unverified — check the HF model card's inference section before committing.
- Qwen3-VL GGUF multi-image support through llama-server (we send 1–2 images): llama.cpp multimodal multi-image handling should be tested early; not verified this session.
- Per-model strict-JSON conformance (reasoning-field-first ordering) under each backend's JSON mode: needs a 10-prompt smoke test per backend; no literature shortcut found.
