# VLM Backend Wiring Practicalities (checked 2026-10-06)

Scope: integration facts for the five candidate backend families, verified against live provider docs on 2026-10-06. Project requirements checked against: 1–2 PNGs (~1280×960 + 640px crop), ~6k-char prompt (~1.5k tokens), lenient JSON parsing (reasoning field first, no forced schema), temperature 0 or documented absence, 10–60 calls/session, per-call usage reporting, refusal behavior on photorealistic robot scenes.

Cost model used throughout: 100 episodes × 5 calls = 500 calls; ~2.5k input + ~0.3k output tokens/call = 1.25M input + 0.15M output tokens. Note: the 2.5k input figure was measured on gpt-4o; image token accounting differs per provider (per-candidate corrections noted inline).

## 1. OpenAI GPT-5 family (and gpt-4o-2024-08-06 lifecycle)

### Takeaway
`gpt-5.1` (default snapshot `gpt-5.1-2025-11-13`) is the current mainline vision model at $1.25/$10 per MTok; it is a reasoning model whose temperature/top_p are only honored with `reasoning_effort: "none"`. Our pinned `gpt-4o-2024-08-06` is NOT on the deprecations page and keeps its $2.50/$10 pricing — but the older `gpt-4o-2024-05-13` snapshot shuts down 2026-10-23, a signal the 4o line is being wound down; collection on the pin is safe today but should not be assumed safe into 2027.

### Cited Findings
- Pricing (per 1M tokens, cached input in parens): `gpt-5` $1.25/$10 ($0.125), `gpt-5.1` $1.25/$10 ($0.125), `gpt-5-mini` $0.25/$2 ($0.025), `gpt-5-nano` $0.05/$0.40 ($0.005), `gpt-5-pro` $15/$120; `gpt-4o` and `gpt-4o-2024-08-06` both still listed at $2.50/$10 ($1.25 cached) — [OpenAI pricing](https://developers.openai.com/api/docs/pricing)
- Deprecations: neither `gpt-4o` nor `gpt-4o-2024-08-06` appears on the deprecation/shutdown list; `gpt-4o-2024-05-13` is deprecated with shutdown 2026-10-23; gpt-4o audio/realtime preview variants retire 2027-01-20 — [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations)
- `gpt-5.1`: default snapshot `gpt-5.1-2025-11-13`, image input supported, 400K context / 128K max output; `reasoning_effort` supports `none` (default), `low`, `medium`, `high`; rate limits Tier 1: 500 RPM / 500K TPM, Tier 2: 5,000 RPM / 1M TPM — [gpt-5.1 model page](https://developers.openai.com/api/docs/models/gpt-5.1)
- Temperature: logprobs, temperature and top_p are controllable on gpt-5.1 only when `reasoning_effort: "none"`; some SDKs (Vercel AI SDK) blanket-block temperature on all gpt-5.x by model name even when the API would accept it — [OpenAI community](https://community.openai.com/t/temperature-in-gpt-5-models/1337133); [vercel/ai#10932](https://github.com/vercel/ai/issues/10932)
- Image tokens (tile-based for gpt-5.1 and gpt-4o): scale into 2048×2048, shortest side to ≤768px, count 512px tiles; gpt-5.1 = 70 base + 140/tile, gpt-4o = 85 base + 170/tile; `detail: low|high|auto`; up to 1,500 images/request, 512 MB payload cap — [images & vision guide](https://developers.openai.com/api/docs/guides/images-vision)
- Structured outputs (`response_format: json_schema`) exist but are optional; plain-text JSON with lenient parsing remains supported (no change to chat completions shape) — [OpenAI pricing/docs](https://developers.openai.com/api/docs/pricing)

### Inferences
- Our two images cost ≈630 (1280×960 → 4 tiles) + ≈350 (640px crop → 2 tiles) ≈ 1.0k tokens on gpt-5.1 — the measured ~2.5k/call transfers almost exactly.
- For a classification workload wanting determinism, run gpt-5.1 with `reasoning_effort: "none"` + `temperature: 0` — that combination is API-legal and avoids reasoning-token billing on output. With any other effort level, temperature is rejected/ignored and reasoning tokens are billed as output (would inflate the 0.3k output assumption).
- Adapter impact: existing OpenAI-style HTTP adapter works unchanged; only new request field is `reasoning_effort`.
- gpt-4o pin: usable for continued collection now; the 2024-05-13 shutdown this month suggests planning a comparison arm on gpt-5.1 before any 08-06 deprecation notice lands (OpenAI gives advance notice on the deprecations page).

### Gaps
- The images guide (as summarized by the fetch) labeled `gpt-5` "deprecated" and referenced patch-based "GPT-6" models; neither claim is corroborated by the deprecations or pricing pages I fetched — treat as unverified summarizer noise, but worth a manual glance at the page before pinning gpt-5 (non-.1).
- Dated snapshots beyond `gpt-5.1-2025-11-13` (e.g., a dated `gpt-5-mini`) were not enumerated on the pages fetched.

## 2. Anthropic Claude current generation

### Takeaway
Current vision-capable IDs are `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-4-5` (all undated — the ID itself is the pin; Anthropic's current-gen IDs take no date suffix). Major wiring caveat: on Opus 5.5 and Sonnet 5.5 the temperature parameter is REMOVED (non-default values → HTTP 400) and thinking cannot be fully disabled on Opus 5.5 — this is the "documented absence of temperature" case, and thinking tokens are billed as output.

### Cited Findings
- Current models/pricing (per 1M in/out): Opus 5.5 `claude-opus-5-5` $4/$20; Sonnet 5.5 `claude-sonnet-5-5` $2/$10; Haiku 4.5 `claude-haiku-4-5` $1/$5 (200K context; others 1M). IDs are complete without date suffixes — bundled claude-api skill model table (cached 2026-09-25), cross-referenced with [platform.claude.com docs](https://platform.claude.com/docs/en/api/rate-limits) which lists the same model generation
- Sampling: Opus 5.5 — temperature/top_p/top_k "Removed – 400"; Sonnet 5.5 — non-default values → 400; Haiku 4.5 — sampling allowed (and thinking off unless `budget_tokens` set) — claude-api skill thinking/effort table (cached 2026-09-25)
- Thinking: Opus 5.5 thinking is always on (`{"type":"disabled"}` → 400 at every effort); depth controlled via `output_config.effort` (default `medium`); Sonnet 5.5 can send `thinking: {"type":"between_tools"}` to suppress it at effort ≤ high; thinking is billed the same regardless of `display` setting — claude-api skill (cached 2026-09-25)
- Refusals: HTTP 200 with `stop_reason: "refusal"` + `stop_details.category` (e.g. `general_harms`, `cyber`); safety classifiers run on 5.5-generation models; server-side fallback parameter exists to auto-reroute refusals — claude-api skill (cached 2026-09-25)
- Rate limits (Messages API, Start tier): 1,000 RPM, 2M input TPM, 400K output TPM for Opus 5.5/Sonnet 5.5/Haiku 4.5; cache reads don't count toward ITPM — [rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- Usage reporting: `response.usage` carries `input_tokens`, `output_tokens`, `cache_*_input_tokens` per call — claude-api skill Python README
- Image input: base64 `image` content blocks (`media_type: image/png`), multiple images per user message supported in the documented content-block array shape — claude-api skill Python README; image token formula ≈ (width×height)/750, images over ~1568px long edge downscaled, per [Anthropic vision docs](https://platform.claude.com/docs/en/build-with-claude/vision) (formula from docs; not re-fetched this session — flag below)

### Inferences
- Our images ≈1,638 (1280×960) + ≈410 (640×480) ≈ 2.0k tokens by the (w×h)/750 rule → per-call input ≈3.5k, ~40% above the gpt-4o-measured 2.5k. Cost table below uses both.
- Determinism: the project cannot set temperature=0 on Opus/Sonnet 5.5 — the adapter must treat "parameter absent by design" as satisfying the spec ("temperature 0 or documented absence"). Haiku 4.5 is the only current Claude that still accepts temperature.
- Output-token budget: with thinking always on (Opus 5.5) the 0.3k output/call assumption will undercount; Sonnet 5.5 with `between_tools` or low effort is the closer fit to a terse classification call.
- The dormant Anthropic adapter needs: no `temperature` field for 5.5 models, `output_config.effort` support, and a `stop_reason == "refusal"` branch mapping to `ReasonerResult(decision=None)`.

### Gaps
- The (w×h)/750 image-token formula and the ~100-images-per-request cap come from Anthropic vision docs as cached knowledge; the vision page itself was not fetched this session — verify at platform.claude.com/docs/en/build-with-claude/vision before budgeting.
- No published data on refusal rates for photorealistic robot/warehouse scenes; Claude's classifier categories (cyber/bio/etc.) make scene-image refusals look unlikely but this is untested — the adapter being unexercised means zero project evidence either way.

## 3. Google Gemini: generalist line vs Robotics-ER

### Takeaway
The generalist landscape has moved under us: Gemini 2.5 models are now access-restricted to prior users, and the current line is Gemini 3.x Flash (flagship `gemini-3.8-flash`, $0.75/$3.75 per MTok **through 2026-12-31, doubling to $1.50/$7.50 after**). `gemini-robotics-er-2-preview` remains live with the same promo-pricing cliff ($1/$5 → $2/$10 on 2027-01-01) and stays a preview (ER-1.6-preview is being shut down), so deprecation risk is structural, not hypothetical.

### Cited Findings
- Models: flagship `gemini-3.8-flash`; 3.7/3.6/3.5 Flash remain as previous-generation; 2.5 series (Flash/Flash-Lite/Pro) "limiting access to users who have actively used them in the past"; robotics line lists "Gemini Robotics ER 2 and ER 1.6"; deprecated models get 2-week notice — [Gemini models](https://ai.google.dev/gemini-api/docs/models)
- Robotics IDs: `gemini-robotics-er-2-preview`, `gemini-robotics-er-2-streaming-preview` (Live API), `gemini-robotics-er-1.6-preview` (legacy, "will be shut down at the end of August" — year not stated on page); ER-2 limits 131,072 in / 65,536 out; supports images, pointing with normalized [y,x], structured outputs, thinking — [robotics overview](https://ai.google.dev/gemini-api/docs/robotics-overview)
- Pricing: Gemini 3.8/3.7/3.6 Flash $0.75 in / $3.75 out through Dec 31 2026, then $1.50/$7.50; Gemini 3.5 Flash $1.50/$9.00 standard; Gemini 2.5 Flash $0.30/$2.50; 2.5 Pro $1.25/$10 (≤200k); Robotics-ER-2 preview $1.00/$5.00 through Dec 31 2026, then $2.00/$10.00; batch = 50% off — [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). This confirms the "preview pricing valid through 2026-12-31" note: it is a price increase date, not (explicitly) a shutdown date.
- Image tokens: 258 flat if both dims ≤384px; else tiled into 768×768 crops at 258 tokens each, crop unit ≈ floor(min(w,h)/1.5) (960×540 → 6 tiles); max 3,600 image files/request; PNG/JPEG/WEBP/HEIC/HEIF; Gemini 3 adds a `media_resolution` parameter capping tokens per image — [image understanding](https://ai.google.dev/gemini-api/docs/image-understanding)
- Rate limits: numeric per-tier tables are no longer published; Tier 1 is governed by a $10-per-rolling-10-minute spend window (requires linked billing, $250 cap); actual limits shown per-account in AI Studio — [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- Project-observed (memory, 2026-09-25): the ER-2 adapter is merged and live-validated; ER-2 offered **no temperature control and no think block** in our integration; the robotics-overview page likewise does not document temperature for ER-2 — project memory `project_gemini_er2_integration.md` + [robotics overview](https://ai.google.dev/gemini-api/docs/robotics-overview)

### Inferences
- Our images on Gemini: 1280×960 → crop unit 640 → ~4 tiles ≈ 1,032 tokens; 640×480 crop → ~2–4 tiles ≈ 516–1,032 tokens; per-call input ≈3.0k (~20% over the 2.5k baseline). `media_resolution` (Gemini 3 only) could pull this down.
- If we wire a generalist Gemini arm, `gemini-3.8-flash` is the realistic choice: 2.5-line access is restricted for accounts that haven't used it (our account's prior `gemini-robotics-er-2-preview` use probably does not grandfather 2.5 generalist access — unverified).
- Thinking: Gemini 3.x Flash models are thinking models; thinking tokens bill as output, so the 0.3k output assumption undercounts unless thinking is bounded (check `thinkingBudget`/`thinking_level` controls on 3.x — not verified this session).
- Budget planning: any experiment extending past 2026-12-31 should budget at the doubled rates for both 3.8 Flash and ER-2.
- ER-2 deprecation risk: Google is actively shutting down the previous ER preview (1.6) with short notice windows (2 weeks for deprecated models). Pinning `gemini-robotics-er-2-preview` through a thesis timeline is exposed to the same pattern when ER-3 appears. Mitigation: keep the generalist adapter path warm.

### Gaps
- No numeric RPM/TPM for ER-2 at Tier 1 — Google now only shows per-account values in AI Studio; check the project account's dashboard.
- Temperature support on `gemini-3.8-flash` (and whether Google recommends fixing it at 1.0 as it did for earlier Gemini 3 thinking models) was not verified this session.
- Whether a dated/pinnable snapshot of `gemini-3.8-flash` exists (Google historically offers `-preview-MMDD` style pins only for previews) — not found on the models page summary.

## 4. NVIDIA Cosmos Reason2

### Takeaway
Cosmos-Reason2 ships as open weights (2B and 8B) under the NVIDIA Open Model License (commercial use allowed), built on Qwen3-VL-8B-Instruct. There is a hosted trial endpoint on build.nvidia.com and downloadable NIM containers (released 2026-01-21), but no production hosted API with published pricing — practical use means self-hosting, and the 8B card states a 32 GB minimum GPU, which does NOT fit the project's 24 GB L4 at BF16.

### Cited Findings
- Model: Cosmos-Reason2-8B is built on Qwen3-VL-8B-Instruct (ViT + dense LLM, 8.77B params); inputs: text + image (JPG) + video (mp4, trained at 4 FPS); 256K context; reference serving via HF `transformers` (`Qwen3VLForConditionalGeneration`, BF16); minimum GPU memory 32 GB, tested on A100/H100; released on HF 2025-12-19, improved weights 2026-03-10 — [HF model card](https://huggingface.co/nvidia/Cosmos-Reason2-8B)
- A 2B variant exists alongside the 8B — [NGC catalog](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/cosmos-reason2-2b)
- NIM: downloadable NIM containers for both 2B and 8B released 2026-01-21; NIM use governed by NVIDIA Software License Agreement + Product-Specific Terms; the build.nvidia.com trial API service is governed by the NVIDIA API Trial Terms of Service — [NGC cosmos-reason2-8b container](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/cosmos-reason2-8b); [governing terms](https://catalog.ngc.nvidia.com/orgs/nim/nvidia/containers/cosmos-reason2-2b/-/governing-terms)
- License: NVIDIA Open Model License — "models are commercially usable", derivative models allowed — [HF model card](https://huggingface.co/nvidia/Cosmos-Reason2-8B); [build.nvidia.com model card](https://build.nvidia.com/nvidia/cosmos-reason2-8b/modelcard)
- The build.nvidia.com model card page itself is JS-rendered and returned no content to a plain fetch — endpoint/API-shape details there could not be verified non-interactively.

### Inferences
- API shape: NIM serves an OpenAI-compatible chat completions endpoint (standard for NVIDIA NIMs), so the project's llama_server/OpenAI-style adapter would likely work — but this was not directly verified for this NIM; confirm against the NIM container docs before wiring.
- Hardware: 8B BF16 needs 32 GB → not on the L4. Options: (a) 2B variant (≈5 GB BF16, fits), (b) quantized 8B — since the base is Qwen3-VL-8B, a GGUF conversion servable by llama.cpp is plausible (~5 GB at Q4_K_M, see candidate 5) but no official Cosmos-Reason2 GGUF was found this session, (c) the free build.nvidia.com trial endpoint for low-volume experiments (10–60 calls/session fits trial-credit usage patterns, but trial ToS and rate limits apply).
- Cost: $0 API cost self-hosted; the real cost is GPU time and the VRAM collision with Isaac Sim (see candidate 5).
- "Thinking": Cosmos-Reason models emit a reasoning trace before the answer — this matches our "free-text reasoning first, then JSON" parse shape unusually well, but output token counts will exceed 0.3k/call.

### Gaps
- No official hosted production pricing (per-token) exists for Cosmos Reason2 — only trial access; could not verify whether the trial endpoint enforces a daily credit cap for this model.
- Exact prompt/chat template and whether the NIM honors `temperature: 0` was not verified (JS-only page); the HF transformers path obviously allows full sampling control.
- No Cosmos-Reason2 GGUF confirmed on HF this session.

## 5. Open-weight via llama.cpp: Qwen3-VL

### Takeaway
Qwen3-VL is natively supported in mainline llama.cpp with official Qwen GGUF releases (2B–235B) split into LLM + mmproj vision-encoder files; `llama-server -m model.gguf --mmproj mmproj.gguf` exposes the OpenAI-compatible `/v1/chat/completions` the project's llama_server adapter already targets. Qwen3-VL-8B at Q4_K_M is ~5 GB + mmproj, comfortably inside a 24 GB L4 — but the L4 is shared with Isaac Sim, so co-residency must be budgeted.

### Cited Findings
- llama.cpp support: Qwen3-VL merge landed in mainline llama.cpp (Dense and MoE variants); official GGUF weights 2B→235B; LLM in FP16/Q8_0/Q4_K_M, vision encoder (mmproj) in FP16/Q8_0; compatible with llama.cpp and Ollama; CUDA/Metal/Vulkan/CPU — [Qwen GGUF announcement coverage](https://toolnavs.com/en/article/662-qwen-announces-qwen3-vl-is-now-available-on-llamacpp-with-gguf-weights-ranging-f) (aggregator — primary confirmation is the HF repos below); [Qwen3-VL-2B-Thinking-GGUF](https://huggingface.co/Qwen/Qwen3-VL-2B-Thinking-GGUF)
- Qwen3-VL-8B-Instruct-GGUF file sizes: Q4_K_M 5.03 GB, Q8_0 8.71 GB, F16 16.4 GB; mmproj in F16 or Q8_0 (mixable with any LLM quant); run: `llama-server -m Qwen3VL-8B-Instruct-Q4_K_M.gguf --mmproj mmproj-...-F16.gguf`, serves web UI on :8080 and OpenAI-compatible `/v1/chat/completions`; native 256K context — [HF Qwen3-VL-8B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-GGUF)
- Variants: Instruct and Thinking flavors exist per size (the Thinking variant emits reasoning before the answer) — [HF Qwen3-VL-2B-Thinking-GGUF](https://huggingface.co/Qwen/Qwen3-VL-2B-Thinking-GGUF)

### Inferences
- VRAM budget on the 24 GB L4 (Isaac Sim co-resident): 8B-Q4_K_M ≈ 5 GB weights + ~1–2 GB mmproj/F16 + KV cache at a trimmed context (8–16K is ample for 2 images + 6k-char prompt) + CUDA overhead ≈ 7–9 GB total. Isaac Sim warehouse scenes on the project VM have historically consumed a large share of the 24 GB; serving the 8B alongside Isaac is feasible but should be validated with `nvidia-smi` headroom before a collection run, and `--n-gpu-layers`/context size tuned down if needed. A 32B-class quant (~19–20 GB) is NOT co-residable; it would require stopping Isaac or a second GPU/VM.
- Alternative topology: run llama-server on the Mac dev machine (Metal) or a second cloud instance and point the existing adapter at it over HTTP — avoids the Isaac collision entirely; the adapter only needs a base URL.
- Full control: temperature 0 trivially supported; no refusal classifiers of the hosted-API kind (the 19–38% refusal problem class disappears); per-call usage is returned in the OpenAI-compatible `usage` field of non-streaming responses.
- Multi-image: llama.cpp multimodal chat endpoint accepts multiple `image_url` (base64 data URI) parts per message for Qwen3-VL; image token cost is dynamic-resolution dependent (Qwen ViT), irrelevant for billing but relevant for latency on L4 (~seconds per 1280×960 image).
- CLAUDE.md lists llama.cpp llama-server as an external-verification target: before implementation, re-verify the exact llama.cpp version pin and mmproj flag behavior against the llama.cpp repo docs (tools/server README + multimodal.md), since multimodal server flags have churned historically.

### Gaps
- Multi-image-per-request behavior of Qwen3-VL under llama-server (vs single image) was not verified against llama.cpp primary docs this session — verify in llama.cpp's multimodal docs/issue tracker before relying on the two-image request shape.
- No measured tokens/sec for Qwen3-VL-8B Q4_K_M on an L4 with Isaac co-resident was found; needs an empirical check.
- The toolnavs source is an aggregator; the underlying Qwen announcement is corroborated by the official Qwen HF GGUF repos, which is the citation that matters.

## 6. Cost per 100 episodes (500 calls; 1.25M in / 0.15M out)

### Takeaway
All hosted candidates land in single-digit dollars per 100 episodes at the project's measured token profile; the spread (≈$0.75–$8) is small enough that refusal behavior, determinism controls, and deprecation risk should dominate the wiring decision, not price.

### Cited Findings
Prices from the provider pages cited in sections 1–3; arithmetic is mine.

| Backend | $/MTok in/out | Input cost | Output cost | Total /100 ep | Notes |
|---|---|---|---|---|---|
| gpt-5.1 (`reasoning: none`) | 1.25 / 10 | $1.56 | $1.50 | **$3.06** | temp 0 legal at `none`; token profile transfers ~1:1 |
| gpt-5-mini | 0.25 / 2 | $0.31 | $0.30 | **$0.61** | cheapest hosted frontier-family option |
| gpt-4o-2024-08-06 (current pin) | 2.50 / 10 | $3.13 | $1.50 | **$4.63** | baseline; 19–38% refusal history on annotated frames |
| claude-sonnet-5-5 | 2 / 10 | $2.50 | $1.50 | **$4.00** | at ~3.5k real input tokens: ≈$5.25; no temperature param; thinking billed as output |
| claude-opus-5-5 | 4 / 20 | $5.00 | $3.00 | **$8.00** | thinking always on → output > 0.3k/call in practice |
| claude-haiku-4-5 | 1 / 5 | $1.25 | $0.75 | **$2.00** | only current Claude with temperature control |
| gemini-3.8-flash (≤2026-12-31) | 0.75 / 3.75 | $0.94 | $0.56 | **$1.50** | doubles to ~$3.00 from 2027-01-01; thinking tokens extra |
| gemini-2.5-flash (if access retained) | 0.30 / 2.50 | $0.38 | $0.38 | **$0.75** | access restricted to prior users |
| gemini-robotics-er-2-preview (≤2026-12-31) | 1 / 5 | $1.25 | $0.75 | **$2.00** | doubles to ~$4.00 from 2027-01-01 |
| Cosmos Reason2 (self-host / trial) | — | — | — | **$0 API** | GPU time; 8B needs 32 GB BF16 (not L4); 2B fits |
| Qwen3-VL-8B Q4_K_M via llama-server | — | — | — | **$0 API** | ~7–9 GB VRAM; L4 shared with Isaac Sim |

### Inferences
- Output-side caveat: every thinking-model row (Claude 5.5s, Gemini 3.x, ER-2, Cosmos, Qwen-Thinking) will exceed the 0.3k output assumption; at these prices even 3× output inflation adds at most a few dollars per 100 episodes (worst case Opus 5.5: +$6).
- Rate limits are a non-issue at 10–60 calls/session for every hosted candidate (lowest observed floor: OpenAI Tier 1 at 500 RPM; Anthropic Start at 1,000 RPM; Gemini Tier 1 spend-window $10/10min ≫ our burn rate).

### Gaps
- OpenAI credits are exhausted on the project account (memory, 2026-09-25) — any OpenAI-line cost is contingent on a top-up.
- No verified per-token price exists for hosted Cosmos Reason2 (trial only).
