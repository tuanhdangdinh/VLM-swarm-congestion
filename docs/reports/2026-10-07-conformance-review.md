# Provider-Conformance Code Review: the M2 Backend Layer, Nine Arms

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: an independent review of `reasoning/vlm/` (adapters, factory, models, parser, refusal and fallback pipeline), `config/models.yaml`, the two serving scripts and `scripts/preflight_backend.py`. It is checked against provider documentation fetched on 2026-10-07. It is review only: no code, config or test changed.

---

## Summary

This review covers the backend layer at `feat/prereg-v2-composite` tip `060abe0`, which carries all nine arms. It was done on branch `feat/v2-conformance-review`. Every provider page cited below was fetched on **2026-10-07** with `curl` (raw HTML or `.md`) and grepped for verbatim text. No summarizer output is cited. The only "live" verification was a local socket server on 127.0.0.1. No provider API was called, and spend was **$0.00**.

Headline: **no CRITICAL finding, five HIGH.**

- **Request construction conforms on every arm.** Endpoints, auth headers, required fields, image encoding, role rules and sampling and thinking legality all match current docs (see Clean Areas).
- **Response and error handling diverge, and that is where the defects are.** The four adapters were written by different hands, and each handles the unhappy path differently:
  - **F01:** three of four adapters let transport exceptions escape `Reasoner.run`. This was reproduced locally.
  - **F02:** there is no status-code taxonomy or backoff on any arm.
  - **F03:** only Anthropic's structured refusal is recognized. Every other provider's documented refusal channel lands in "transport" or "parse", so refusal accounting and the grey-image "parity" are not comparable across arms.
  - **F04:** `served_model` echoes the request id on all nine arms, so the Group-D rolling-pin mitigation has no signal.
  - **F05:** gemini-3.8-flash runs a 2,048 `max_output_tokens` cap that the docs say *includes* thought tokens, against a measured 1,963 thought tokens, and the adapter never reads `status: incomplete`.

New lifecycle fact (**F12**): OpenAI deprecated **gpt-5.1** on 2026-10-01, with shutdown on 2027-04-01. The spec's lifecycle record covers only gpt-4o.

The local suite was verified to show zero delta. Details are in Verification.

---

## Doc Sources (all fetched 2026-10-07)

| Key | URL |
|---|---|
| A-err | https://platform.claude.com/docs/en/api/errors |
| A-rl | https://platform.claude.com/docs/en/api/rate-limits |
| A-stop | https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons |
| A-ref | https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback |
| A-think | https://platform.claude.com/docs/en/build-with-claude/thinking |
| A-vis | https://platform.claude.com/docs/en/build-with-claude/vision |
| A-msg | https://platform.claude.com/docs/en/api/messages |
| A-ver | https://platform.claude.com/docs/en/api/versioning |
| O-err | https://developers.openai.com/api/docs/guides/error-codes |
| O-rl | https://developers.openai.com/api/docs/guides/rate-limits |
| O-chat | https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create |
| O-vis | https://developers.openai.com/api/docs/guides/images-vision |
| O-lm | https://developers.openai.com/api/docs/guides/latest-model |
| O-dep | https://developers.openai.com/api/docs/deprecations |
| O-51 | https://developers.openai.com/api/docs/models/gpt-5.1 |
| G-int | https://ai.google.dev/gemini-api/docs/interactions |
| G-api | https://ai.google.dev/api/interactions-api |
| G-think | https://ai.google.dev/gemini-api/docs/thinking |
| G-err | https://ai.google.dev/gemini-api/docs/api-errors |
| G-ts | https://ai.google.dev/gemini-api/docs/troubleshooting |
| G-img | https://ai.google.dev/gemini-api/docs/image-understanding |
| G-er | https://ai.google.dev/gemini-api/docs/robotics-overview |
| D-rl | https://api-docs.deepseek.com/quick_start/rate_limit |
| D-err | https://api-docs.deepseek.com/quick_start/error_codes |
| D-chat | https://api-docs.deepseek.com/api/create-chat-completion |
| D-vis | https://api-docs.deepseek.com/guides/vision |
| D-think | https://api-docs.deepseek.com/guides/thinking_mode |
| Z-code | https://docs.z.ai/api-reference/api-code |
| Z-chat | https://docs.z.ai/api-reference/llm/chat-completion |
| Z-think | https://docs.z.ai/guides/capabilities/thinking |
| L-srv | https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md (master, not the pinned image build) |
| V-oai | https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/docs/serving/online_serving/openai_compatible_server.md |
| V-sec | https://raw.githubusercontent.com/vllm-project/vllm/v0.31.0/docs/usage/security.md |

---

## Findings

Ranking rule:

- **CRITICAL:** silently corrupts confirmatory data, or leaks key material.
- **HIGH:** decision, data or retries lost on a realistic path, a documented provider contract violated, or a registered mitigation that cannot work as specified.
- **MEDIUM:** artifact fidelity or uniformity defect with a bounded impact.
- **LOW:** hygiene, cost accounting, or drift with little measurement impact.
- **INFO:** recorded fact, already ruled, or no action needed.

"RULED" cites the prereg-v2 design spec block in the main checkout (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`).

### CRITICAL

None found. Key handling was audited specifically and is clean, apart from the LOW hygiene item F15. No path was found that silently corrupts a recorded decision.

### HIGH

| ID | Finding and location | Provider doc (fetched 2026-10-07) | Risk | Fix or accept |
|---|---|---|---|---|
| F01 | **Transport exceptions escape `Reasoner.run` on three of four adapters.** The cases differ by adapter:<br>- `anthropic_backend.py:107-117` and `llama_server_backend.py:78-87` catch only `Timeout` and `requests.ConnectionError`. A body the server closes mid-stream raises `requests.ChunkedEncodingError`, which is neither.<br>- `llama_server_backend.py:94-95` and `gemini_backend.py:112` call `resp.json()` and index `choices` unguarded.<br>- `llama_server_backend.py:98`: a `null` content fails `BackendResponse(text=...)` validation.<br>- `reasoner.py:376-380` catches only `BackendTimeoutError`, `ConnectionError`, `VLMOutputParseError` and `DecisionValidationError`.<br>Reproduced locally (see Verification, probe 1): mid-body close escapes on anthropic and llama_server; a non-JSON 200 escapes on llama_server and gemini; openai is caught on both. | D-rl: "your HTTP request will remain connected … If the request has not started inference after 10 minutes, the server will close the connection." A-err: the SDK "automatically retries transient failures (such as connection errors …)". | M5 (`reasoning_pipeline.py:1066`) records it as "reasoner raised" through `build_failed_outcome`. That result carries `backend_id="unknown"`, `attempts=1`, no effective config and no `attempt_token_usage`. The remaining attempts are never spent, and earlier billed attempts' usage is lost. Under `prompt_permutation_votes` the whole ballot is lost. Stage 2 (`retreat_chooser.py:78`, `except Exception`) survives the same event, so stage 1 and stage 2 diverge. This is the 2026-10-06 DeepSeek truncation fix (`openai_backend.py:119-128`) applied to one adapter only. It breaks the CLAUDE.md M2 contract ("backend/model failures should return `ReasonerResult(decision=None)` after bounded retries"). | **FIX.** The ready diff is under Ready Diffs (mechanical; no request byte moves). |
| F02 | **No status-code taxonomy, backoff or `Retry-After` on any arm.**<br>- Every adapter turns any status of 400 or above into `ConnectionError` (`openai_backend.py:113`, `anthropic_backend.py:119`, `gemini_backend.py:106`, `llama_server_backend.py:89`).<br>- `reasoner.py:376-379` retries with `continue` and no delay.<br>- Deterministic errors are retried too: 400, 401, 402 or 403, quota 429s, and Zhipu 1210.<br>- Transient errors are retried immediately: 429 rate limits, 500, 503 and 529. | O-rl: "follow Retry-After when the header is present … If it's missing or invalid, fall back to exponential backoff with jitter"; "unsuccessful requests contribute to your per-minute limit". A-rl: 429 comes "along with a `retry-after` header indicating how long to wait". A-err: 500 "Retry the request with exponential backoff". G-ts: "we recommend implementing an exponential backoff strategy". G-err: 402 "Don't retry". D-err: 503 "Please retry your request after a brief wait". Z-code: 1302 and 1305 (429), 1113 (429 balance). | A transient 429, 529 or 503 burst burns all four attempts in under a second, so the decision is lost and the episode outcome moves. The artifacts show the path is live, counting distinct events deduplicated by `request_id` across `data/logs`:<br>- 47 OpenAI 429s, all `credit_balance_exhausted`; 46 of them burned the full 4-attempt budget.<br>- 42 Gemini 429s, all the monthly-spend-cap message; every one burned ER-2's full 2-attempt budget.<br>- 3 Gemini 503s and 1 OpenAI 500.<br>Both 429 kinds are quota events, which the docs treat as non-retryable (O-err: "Add credits to continue"; G-err 402 "Don't retry"). | **FIX, with an owner ruling.** One shared policy in `Reasoner`: classify status as retryable or not, honour `Retry-After`, otherwise use capped exponential backoff with jitter, under a wall-clock budget. Because it is uniform it preserves cross-arm comparability, but it is an apparatus change after validation, so it needs a ruling. |
| F03 | **Refusal channels are uniform in name only.** Only `anthropic_backend.py:131` sets `refusal=True`. Every other documented refusal or safety outcome goes elsewhere:<br>- Gemini generation-blocked codes are listed in G-err's error-code table, and G-err's standard path delivers error codes as an HTTP status plus an `error` object. The inference is that they arrive as HTTP errors, which become `ConnectionError` and count as transport. G-api also documents `status: failed`. The adapter reads neither shape, so it misses the block either way.<br>- Zhipu 1301 is HTTP 400, so it counts as transport.<br>- Zhipu `finish_reason: "sensitive"`, OpenAI and DeepSeek `content_filter`, and the OpenAI `message.refusal` field (`openai_backend.py:129-131`) all count as parse.<br>`is_refusal` (`reasoner.py:45-48`) is two English regexes tuned to gpt-4o's phrasing. | G-err: "Generation blocked codes … safety … prohibited_content … When you receive one of these codes, modify your input and retry." Z-code: "1301 400 System detected potentially unsafe or sensitive content". Z-chat: finish_reason "Can be stop, tool_calls, length, sensitive, …". O-chat: "content_filter if content was omitted due to a flag from our content filters"; "refusal: string The refusal message generated by the model". D-chat: finish_reason values include `content_filter`. | `refusal_attempts` and `image_fallback_used` are measured outcomes. The parity rulings (model-wiring ruling 1; roster-validation ruling 2) exist so that "refusal profiles are measured under identical mitigation". As written, the grey-image fallback cannot fire on a Gemini, Zhipu or OpenAI-filter refusal, and those refusals are counted as transport or parse. Cross-arm refusal comparisons are therefore not like-for-like. | **FIX.** Each adapter maps its documented refusal channel to `BackendResponse.refusal` (and `refusal_category`). The shared pipeline stays unchanged. Until then, every refusal comparison carries this caveat. |
| F04 | **`served_model` is uninformative on every arm, and the Group-D caveat depends on it.** Artifact tally over every `served_model` occurrence in `data/logs`: these are records, not distinct calls, because decision JSON, traces and probe files repeat them. **Zero** records differ from the arm's configured `model_id`. Examples: `deepseek-flash` 192 records (5 distinct decision requests), `glm-5.3-flash` 164 (8), `gemini-3.8-flash` 170 (9). No adapter records `system_fingerprint` (`openai_backend.py:187-192`). | D-chat: "system_fingerprint string required This fingerprint represents the backend configuration that the model runs with." O-chat: `system_fingerprint` "Deprecated … Can be used … to understand when backend changes have been made". Z-chat documents no version field. G-api echoes `"model"` (the request id). | Roster-closure ruling: Group-D analyses "must condition on the served-model string". That string is constant by construction, so the condition can never detect drift. An analysis would wrongly conclude the pin held. | **FIX** for DeepSeek: record `system_fingerprint` per call. **Amend the ruling text** for GLM and the Gemini preview: drift there is undetectable from the response. |
| F05 | **The gemini_flash output cap is not cap-proofed.**<br>- `models.yaml:168-177` inherits `max_tokens: 2048`, sent as `max_output_tokens` (`gemini_backend.py:134`).<br>- Measured thought use is 1,962 to 1,963 tokens on stage 2 (`2026-10-07-hypothesis-arms.md` lines 385-389).<br>- The adapter never reads `status` (`gemini_backend.py:112-121`).<br>GLM was cap-proofed to 16,384 for the same trap; flash was not. | G-think: "max_output_tokens … sets the maximum number of tokens a response can generate, including thought tokens. When set, this parameter acts as a hard cutoff enforced by the infrastructure". G-api: status "incomplete: The interaction is completed, but contains incomplete results (e.g. hitting max_tokens)". | When thought use reaches about 1,990 tokens, the answer is cut silently. Today that shows up as an empty or partial text, which counts as a parse failure plus a re-ask, and the cause is not recorded. The hypothesis-arms report lists it only as a "watch item". Ruling 2 (2026-10-07) covers the stage-2 *timeout*, not the cap. **UNRULED.** | **Owner ruling.** Options: raise `gemini_flash.reasoner.max_tokens` (GLM precedent; flash is not the frozen ER-2 pin), or accept it with the record. In either case, record `status` per call (F06). |

### MEDIUM

| ID | Finding and location | Provider doc (fetched 2026-10-07) | Risk | Fix or accept |
|---|---|---|---|---|
| F06 | **Stop and finish reasons are never persisted.**<br>- `BackendResponse.raw` is read only for `unsupported_sampling` (`reasoner.py:332`), then discarded.<br>- No diagnostics field carries `finish_reason`, `stop_reason` or `status`.<br>- `gemini_backend.py:184` says Gemini's own names "are preserved verbatim in BackendResponse.raw". They never reach an artifact. | O-chat: `length`, `content_filter`. A-stop: `max_tokens`, `refusal`, `model_context_window_exceeded` ("Treat the response as truncated"). G-api: `incomplete`, `failed`. D-chat: `insufficient_system_resource`, `aborted`. Z-chat: `sensitive`, `network_error`. | Truncation, provider aborts and filtering cannot be told apart from model garbage. The DeepSeek thinking-cap trap was diagnosable only through token counts. | **FIX.** Add `finish_reason: str \| None` to `BackendResponse` and record it per attempt next to `attempt_token_usage`. |
| F07 | **"200 with no text" is classified three ways.**<br>- Anthropic raises `ConnectionError` (`anthropic_backend.py:184-187`), so it counts as transport, takes no re-ask, and records usage as `None`.<br>- OpenAI (`:129-131`), Gemini (`:175`) and llama (content `""`) count it as a parse failure and re-ask.<br>- llama with `null` content escapes (F01). | A-stop: `max_tokens` / `model_context_window_exceeded` responses are normal 200s with usage. | The same event gets a different retry path and a different `error_type` per arm. An Anthropic truncated or thinking-only 200 is billed but recorded as `None`, against the intent of roster-validation ruling 3. | **FIX.** Return the response with empty text and its usage (parse path), uniformly. |
| F08 | **Recorded sampling is not sent sampling on the four OpenAI-adapter arms.**<br>- `describe_effective_sampling` (`backend_factory.py:173-189`) records `top_k: 20` and `presence_penalty: 0.0` for gpt-4o, gpt-5.1, DeepSeek and GLM.<br>- `openai_backend.py:72-79` never sends them, and they are absent from `unsupported_sampling`. `models.py:726-728` says `None` means "honoured every … field".<br>- With `omit_sampling` on, only temperature and top_p are listed.<br>- The wire-derivation pin (`test_model_wiring.py:805`) derives packing only, not sampling or thinking fields. | O-chat documents no `top_k` field for Chat Completions. | The artifact claims `top_k=20` was in force, but it was not. At temperature 0 the effect is nil; the defect is in proof fidelity. This is the exact property the effective-config block exists to prove. | **FIX.** List them in `unsupported_sampling` (an artifact change; no request byte moves). Extend the wire-derivation pin to every sampling and thinking field, the model for the "recorded = sent" guarantee. |
| F09 | **`backend_id` means two things.** A success records `response.backend_id`, which is the *model id* (`reasoner.py:352`). A failure records `self._config.backend_id`, which is the *arm id* (`:402`). `RetreatChooser` switches from one to the other mid-call (`retreat_chooser.py:59,84`). | n/a (data contract) | Grouping artifacts by `diagnostics.backend_id` splits each arm into a success bucket and a failure bucket. Analysts must use `reasoner_config_effective.backend_id` or `model_id`. | **FIX** (record the arm id on both paths), or document it in the analysis plan. |
| F10 | **The Gemini Interactions API stores every request by default.** Neither Gemini arm sends `store` (`gemini_backend.py:139-144`). We never use `previous_interaction_id`. | G-int: "By default, the API stores all Interaction objects (store=true) … Paid tier: The system retains interactions for 55 days … If you don't want this, you can set store=false". | Every annotated frame, zoom tile and prompt is retained provider-side for 55 days without purpose. This is a data-governance and best-practice gap. | **FIX** for `gemini_flash`. For ER-2, it needs an **owner ruling**: `store` is not a generation field, but the frozen pin's body would change. |
| F11 | **Stage-2 `failure_cause` depends on the adapter and on a race.**<br>- Gemini maps a `requests` timeout to `BackendTimeoutError`, recorded as `"timeout"` (`gemini_backend.py:99-100`).<br>- The other three adapters map it to `ConnectionError`, recorded as `"backend_error"` (`retreat_chooser.py:74-80`).<br>- The inner timeout equals the outer future timeout (`timeout=config.timeout_sec` in both), so which fires first is a race. | n/a (measurement-plan vocabulary `Stage2FailureCause`) | The same 8 s overrun is labelled differently on flash than on any other arm, and not deterministically on those. It bears on the ruled "flash timeout as a measured property". | **FIX.** Map `requests` timeouts to `BackendTimeoutError` in every adapter. |
| F12 | **gpt-5.1 is deprecated.** It was announced on 2026-10-01 with shutdown on 2027-04-01; the recommended replacement is `gpt-6-sol`. The model page marks `gpt-5.1-2025-11-13` "Deprecated". The spec's lifecycle facts (model-wiring ruling) record only gpt-4o. | O-dep: "2026-10-01: GPT-5.3-Codex, GPT-5.1, GPT-5.4-Nano The following models are deprecated and will be removed from the API on April 1, 2027". O-51. | The roster-closure ruling puts this arm in the confirmatory tier. The arm disappears in six months. | **ACCEPT and record** in the spec's lifecycle block. Schedule gpt-5.1 collection before 2027-04-01. |

### LOW

| ID | Finding and location | Provider doc (fetched 2026-10-07) | Risk | Fix or accept |
|---|---|---|---|---|
| F13 | **No ruling covers the local arms' attempt budget.** Qwen3-VL and Molmo2-ER inherit 2 attempts and no grey fallback. The parity rulings say "every hosted arm" (roster-validation ruling 2), so local arms sit outside the rulings' scope. | n/a | It is unclear whether a reader should treat this as deliberate. Local arms rarely refuse, so the impact is small. | **Owner sentence** in the spec: either parity or an explicit exception. **UNRULED.** |
| F14 | **Re-ask suffixes stack in stage 1 but not stage 2.** `reasoner.py:398` re-asks from the *current* payload, so suffixes accumulate across attempts. After a structured refusal the model is shown "Your previous response was invalid: provider refusal (category=…)". `retreat_chooser.py:104` re-asks from `base_payload`. | A-ref: for `reasoning_extraction`, "change the prompt rather than retry the request". | Prompts drift on attempts 3 and 4, and the two stages behave differently. **UNRULED.** | **FIX** (re-ask from the base payload), or rule it as intended. |
| F15 | **Error bodies go unredacted into artifacts.** `resp.text[:400]` is copied into `error_message` (all four adapters), then into the decision JSON and the JSONL trace. A redaction helper already exists (`scripts/probe_gemini_er2.py:90 redact_secret`) but is not used by the adapters. | O-err lists "401 - Incorrect API key provided" (body text not reproduced in the docs). | No key material was found: a scan of `data/logs` for key patterns (`sk-…`, `AIza…`, `sk-ant-`) found only the false positive `sk-label` and the 2026-10-06 provider-doc HTML snapshots. Residual risk is a provider echoing a masked key fragment. | **FIX** (mechanical): apply `redact_secret(text, self._api_key)` before truncation. |
| F16 | **Token usage is incomplete.**<br>- Cached tokens are dropped: OpenAI `prompt_tokens_details.cached_tokens`, DeepSeek `prompt_cache_hit/miss_tokens`, Zhipu `prompt_tokens_details.cached_tokens`, Gemini `total_cached_tokens`.<br>- Also dropped: OpenAI `image_tokens`, and Gemini `input_tokens_by_modality` and `total_tool_use_tokens`.<br>- The Zhipu `reasoning_tokens` key is read from `completion_tokens_details`, which Z-chat's usage schema does not list (it works live).<br>- `gemini_backend.py:179` falls back to `usage_metadata`, a field that does not exist in G-api. | O-chat, D-chat ("prompt_tokens … equals prompt_cache_hit_tokens + prompt_cache_miss_tokens"), Z-chat, G-api. | "Cost = sum of `attempt_token_usage`" overprices DeepSeek and Zhipu whenever the static preamble hits the cache. GLM's cap-proximity evidence rests on an undocumented field. | **FIX**: additive keys. |
| F17 | **Abandoned worker threads.** On the outer timeout, `invoke_backend` abandons the worker (`reasoner.py:113-117`), but the request can still complete and be billed. DeepSeek's keep-alive empty lines defeat the per-read `requests` timeout, so a thread can live up to 10 minutes. Up to `max_attempts` requests can be in flight at once for one call. | D-rl (keep-alive empty lines; 10-minute close). | Unrecorded billing, extra rate-limit pressure, and thread build-up during long runs. | **ACCEPT**, or add a total-deadline guard in the adapter. |
| F18 | **Request ids are not recorded.** None of these reaches an artifact: Anthropic's `request-id` header, OpenAI's `x-request-id`, the Gemini interaction `id` (in the body, but discarded with `raw`), or the Zhipu `request_id` (client-suppliable). | A-err: "Every API response includes a unique request-id header … When contacting support … include this ID". Z-chat: `request_id` "Passed by the user side". | No provider-side traceability for refusals or anomalies. | **FIX**: one additive diagnostics field. |
| F19 | **The gpt-4o pin sends deprecated `max_tokens` and alters both temperature (0.0) and top_p (0.95).** | O-chat: `max_tokens` "Deprecated … now deprecated in favor of max_completion_tokens"; top_p: "We generally recommend altering this or temperature but not both." | Nil at temperature 0. The deprecated field still works. | **ACCEPT.** This is the frozen pin, byte-pinned since v1. |
| F20 | **Adapter code is duplicated.**<br>- `_encode_image` exists four times, MIME by suffix only; an unknown suffix is silently labelled `image/png`.<br>- `_extract_served_model` exists four times.<br>- Key loading exists three times; `preflight_backend.py:69` uses `.strip()` where the adapters use whitespace-join.<br>- The sampling-drop warning exists twice. | O-vis, A-vis and D-vis list supported formats; frames are PNG today. | F01, F07 and F11 are the cost of this duplication: the same concern is handled four ways. | **FIX later** (a shared transport helper), outside this review's scope. |
| F27 | **The factory's config contract has drifted, and the backend layer's own test is red.**<br>- `build_backend("openai", None)` and `("gemini", None)` silently construct default configs (`backend_factory.py:296-298, 319-321`). For openai that default is the floating `gpt-4o` alias, not the pin.<br>- `anthropic` and `llama_server` raise, as the docstring says ("backends that require it raise on absence").<br>- `tests/unit/test_openai_backend.py::test_factory_requires_config_for_openai` still pins the raise contract. It fails at tip `060abe0` and is one of the 63 pre-existing failures. A `ValueError` is raised, but it is the missing-key error, not "openai backend requires". | O-dep (aliases move; the pin exists to prevent that) | A caller that forgets the config gets an unpinned model rather than a startup failure. The red test has been normalised into the failure baseline. | **FIX**: raise on a `None` config for every hosted adapter, which turns the test green. |
| F21 | **vLLM applies `generation_config.json` defaults by default.** | V-oai: "By default, the server applies `generation_config.json` from the Hugging Face model repository … To disable this behavior, please pass `--generation-config vllm`." | Low: the file is sha-pinned (117 B) and every request sets all four sampling fields. | **ACCEPT**, or add `--generation-config vllm` at the next script change. |

### INFO

| ID | Finding and location | Doc | Note |
|---|---|---|---|
| F22 | **Some comments and defaults are stale.**<br>- `gemini_backend.py:200` says the Interactions API "is not documented to echo a served version", but G-api example responses carry `"model"`.<br>- `gemini_backend.py:43` says `AnthropicBackend` drops sampling "silently"; it records it.<br>- The `AnthropicBackendConfig` default is `claude-opus-4-8`, and the `OpenAIBackendConfig` default is the floating `gpt-4o`. The shipped config overrides both.<br>- `models.py:676-679` and `:884-886` call the fallback "every backend but openai" / "backends that never refuse (gemini, llama_server)". | G-api | No behavioural effect; it misleads readers. |
| F23 | **Anthropic `reasoning_extraction` refusals are retried up to four times.** The docs list the category as billed with no fallback model. | A-ref: "This category has no recommended fallback model, so change the prompt rather than retry the request." | **RULED:** the parity ruling (model-wiring ruling 1), plus the v3.4 Sonnet watch item (v3.4 re-pin ruling 4). ACCEPT; F14 is related. |
| F24 | **The local servers are unauthenticated, loopback-bound on a host network.** | V-sec: `--api-key` "only for endpoints under the `/v1` … prefixes. Many other sensitive endpoints are exposed … without any authentication". | Acceptable on the single-tenant VM; both scripts bind to 127.0.0.1. |
| F25 | **`--trust-remote-code` surface on Molmo.** All 22 files are sha-pinned and verified before start, including the five `.py` files the remote code runs. The server runs with `HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` and a `:ro` mount. `verify_files` does not flag *extra* files in the directory; only `auto_map`-referenced code runs. | V-sec | ACCEPT. The residual risk is noted. |
| F26 | **The llama.cpp server README is cited at `master`, not at the pinned `server-cuda` digest build.** | L-srv | Behaviour was validated live per model (model-wiring report); the doc pin is only approximate. |

---

## Cross-Arm Uniformity Matrix

The matrix reflects stage 1 unless a row says stage 2, from the shipped `config/models.yaml` and `orchestrator.yaml`. **Bold** marks a divergence; the status column shows whether it is ruled.

| Property | gpt-4o `openai` | gpt-5.1 `openai_gpt51` | Sonnet 5.5 `anthropic` | DeepSeek `deepseek` | GLM `zhipu_glm` | ER-2 `gemini` | flash `gemini_flash` | Qwen3-VL `…_qwen3vl` | Molmo2-ER `…_molmo2er` | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| adapter | openai | openai | anthropic | openai | openai | gemini | gemini | llama_server | llama_server (vLLM) | — |
| max_attempts | 4 | 4 | 4 | 4 | 4 | **2** | 4 | **2** | **2** | ER-2: RULED (v3.4 re-pin ruling 1). Local arms: **UNRULED** (F13) |
| grey fallback after | 2 | 2 | 2 | 2 | 2 | **off** | 2 | **off** | **off** | same as above |
| timeout_sec (stage 1) | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | 120 | uniform |
| stage 2: attempts / timeout | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | 2 / 8 s | uniform; flash's overrun RULED (hypothesis-arms ruling 2) |
| max_tokens | 2048 | 2048 (`max_completion_tokens`) | 2048 | 2048 | **16384** | 2048 | 2048 (**includes ~1,960 thought**) | 2048 | 2048 | GLM: RULED (hypothesis-arms ruling 1). Flash cap: **UNRULED** (F05) |
| temperature sent | 0.0 | 0.0 | **none** (recorded 0.0) | 0.0 | 0.0 | **none** (recorded **0.6**) | **none** (recorded 0.0) | 0.0 | 0.0 | Anthropic and Gemini: documented absence, RULED (model-wiring ruling; ER-2 integration spec §4) |
| top_p sent | 0.95 | 0.95 | none | 0.95 | 0.95 | none | none | 0.95 | 0.95 | consistent with recording |
| top_k / presence_penalty sent | **no** (recorded 20 / 0.0) | **no** | no (recorded as unsupported) | **no** | **no** | no (recorded as unsupported) | no (recorded as unsupported) | 20 / 0.0 | 20 / 0.0 | **UNRULED** recording gap (F08) |
| thinking / effort | — | effort `none` | `between_tools` | disabled | **enabled, effort `low`** | level `low` | level `low` | — | — | GLM: RULED (hypothesis-arms ruling 1). Rest: RULED (dose pilot freeze) |
| backoff between attempts | none | none | none | none | none | none | none | none | none | uniform but non-conformant; **UNRULED** (F02) |
| Retry-After honoured | no | no | no | no | no | no | no | n/a | n/a | **UNRULED** (F02) |
| transport catch complete (no escape) | yes | yes | **no** (mid-body) | yes | yes | **no** (non-JSON 200) | **no** | **no** (both, plus null content) | **no** | **UNRULED** (F01) |
| requests timeout raised as | ConnectionError | ConnectionError | ConnectionError | ConnectionError | ConnectionError | **BackendTimeoutError** | **BackendTimeoutError** | ConnectionError | ConnectionError | **UNRULED** (F11) |
| empty-200 classification | parse | parse | **transport** | parse | parse | parse | parse | parse (null content: **escape**) | same | **UNRULED** (F07) |
| refusal detected by | regex | regex | **structured** + regex | regex | regex | regex | regex | regex | regex | **UNRULED** (F03) |
| provider safety outcome lands in | parse (`content_filter`) | parse | refusal | parse | **transport** (1301) / parse (`sensitive`) | **transport** (blocked codes) | **transport** | n/a | n/a | **UNRULED** (F03) |
| served_model informative | = request | = request | = request | = alias | = alias | = request | = request | = alias | = alias | **UNRULED** (F04) |
| re-ask base, stage 1 / stage 2 | cumulative / base | same | same | same | same | same | same | same | same | uniform across arms, divergent across stages (F14) |
| constrained decoding | none | none | none | none | none | none (`force_schema` off) | none (`force_schema` off) | none | none | clean |

---

## Clean Areas

These were checked and **no finding** results. Absence is stated, not implied.

- **Endpoints, auth and versioning.**
  - OpenAI, DeepSeek and Zhipu use `POST {base}/chat/completions` with Bearer auth. The base URLs `api.openai.com/v1`, `api.deepseek.com` and `api.z.ai/api/paas/v4` match D-chat and Z-chat.
  - Anthropic sends `x-api-key` plus `anthropic-version: 2023-06-01`, the only current version (A-ver).
  - Gemini posts `{base}/interactions` with `x-goog-api-key`. The key travels in a header, never in the URL, so it never appears in `requests` exception text.
- **Sampling and thinking legality per model.**
  - Sonnet 5.5 sends no sampling. A-think: "non-default `temperature`, `top_p`, or `top_k` values return a 400 error".
  - `between_tools` is the documented way to turn off up-front thinking on Sonnet 5.5. A-think: "Claude Sonnet 5.5 … rejects `thinking: {type: "disabled"}` … send `thinking: {type: "between_tools"}` instead". No effort is sent, and the constraint "high or below" holds by default.
  - gpt-5.1 sends temperature 0.0 at effort `none`, with `max_completion_tokens`. O-chat: `max_completion_tokens` covers "visible output tokens and reasoning tokens". **Doc caveat:** no gpt-5.1-specific statement of the temperature rule was found on 2026-10-07. O-51 has no sampling text, and the rule in O-lm ("When reasoning effort is not none, remove temperature, top_p") sits in the GPT-6 section. The legality at `none` therefore rests on the live HTTP 200s recorded in the model-wiring and dose-pilot reports, not on re-verified docs. The `omit_sampling` guard covers higher efforts.
  - DeepSeek sends thinking `disabled`, so temperature is honoured. D-think: thinking mode ignores temperature.
  - GLM sends `thinking: enabled` plus `reasoning_effort: low`. Z-chat: "GLM-5.3-FLASH model, only the low / high / max levels are supported". Temperature 0.0 is inside [0.0, 1.0], and top_p 0.95 is Zhipu's own default.
  - The Gemini arms send no sampling fields. G-api's `generation_config` lists `max_output_tokens`, `seed`, `stop_sequences`, `thinking_level` and others, with no temperature field. `generation_config.thinking_level` is the documented location (G-api: "thinking_level ThinkingLevel (optional) … minimal … low … medium … high").
  - thinking_level `low` is valid on both Gemini arms per G-think's table: "gemini-3.8-flash On (medium) low, medium, high" and "gemini-robotics-er-2-preview On (high) minimal, low, medium, high". ER-2's provider default is `high`, so the pinned `low` is a recorded choice, not the default.
  - G-er (ER-2 page): "Builds on Gemini 3.5 Flash"; "Gemini Robotics ER Preview: The Gemini Robotics ER model is in preview"; "Gemini Robotics ER 1.6 was deprecated on August 31, 2026". It states no sampling, `media_resolution` or ordering rule. Its examples are image-first with `thinking_level: "high"`, and its REST example nests `thinking_config.thinking_level`, unlike G-api and its own Python example. That is a doc inconsistency; our flat placement follows G-api. Nothing in it moves the audited ER-2 packing (the 2026-10-06 audit's "examples alone do not count" rule).
- **Role rules.**
  - DeepSeek images are user-only. D-vis: "Images in system or assistant messages return a 400 error". Ours are in the user turn.
  - Molmo uses `user_prefix`, with no system turn, and multi-image is off. Both are RULED (hypothesis-arms ruling 3).
- **Image encoding and size.**
  - Frames are PNG, 1280×960 (every one of 300 sampled artifacts), at most 846 KB on disk.
  - Anthropic: base64 without a `data:` prefix, which is correct. 1280×960 sits within the high-resolution tier (2576 px / 4784 tokens), so there is no resize, and it is under 10 MB per image (A-vis).
  - OpenAI: `detail: "high"` is a documented value (O-vis).
  - DeepSeek: `high` "Provided for compatibility; equivalent to `original`" (D-vis), under the 48 MiB body limit.
  - Zhipu: `detail` is accepted live (already recorded).
- **Payload-format fidelity.** `test_recorded_payload_format_matches_the_request_actually_sent` covers all nine arms, deriving order, placement, detail and JSON flag from the sent body. This review re-ran it and it passed. F08 is the gap *outside* that block.
- **Constrained-decoding prohibition.** It holds on every arm: no `response_format` or JSON-schema field is sent anywhere, `force_schema` is false on both Gemini arms, and there is no grammar on llama-server and no guided decoding on vLLM.
- **Key handling.**
  - Keys come from the environment only. The config holds only the env-var *name*.
  - Whitespace is stripped, and construction fails fast when a key is missing.
  - No `print` or `logger` call emits a key or headers. The sampling warnings log only the model id.
  - Exception text carries no headers. `raw` holds only the response body.
  - The preflight never prints keys or headers.
  - A scan of `data/logs` for key patterns found no key material (F15 is hygiene only).
- **Refusal usage on the success, refusal and transport paths.** Per-attempt usage is appended before parsing, so refused attempts are recorded. Transport attempts are recorded as `None`. This is pinned by the ruling-3 tests. The exceptions are the F01 escape paths and the F07 Anthropic empty-200.
- **Anthropic structured refusal.** It reads `stop_reason == "refusal"` and `stop_details.category`, exactly the documented locations (A-stop: "`stop_details` is `null` for all stop reasons other than `refusal`"). `output_tokens_details.thinking_tokens` is a documented field (A-msg).
- **Gemini usage names.** `total_input_tokens`, `total_output_tokens`, `total_thought_tokens` and `total_tokens` match G-api exactly.
- **Serving-script supply chain.**
  - Both images are pinned by digest.
  - Every model file is pinned by size plus sha256, verified on download before `mv`, and re-verified on every `start` under `set -euo pipefail`, so a mismatch aborts.
  - Downloads use pinned Hugging Face revisions.
  - Volumes are mounted read-only.
  - Both servers bind to 127.0.0.1.
  - VRAM gates are registered before first run, refuse with exit 3, and add an Isaac reserve when Isaac is not running.
- **Lifecycle.** `gpt-4o-2024-08-06` does not appear on O-dep (fetched 2026-10-07), consistent with the spec.
- **Idempotency keys.** None of the fetched references for these seven endpoints documents an idempotency key: O-chat, A-msg, G-api, D-chat, Z-chat, L-srv, V-oai. No finding. Zhipu's client `request_id` is a tracing id, covered in F18.
- **User-agent.** Every adapter sends the default `python-requests/<ver>` UA. None of the fetched pages requires or recommends a custom UA. No finding.
- **Timeouts against provider-stated latency.** Stage 1 uses a uniform 120 s and stage 2 a uniform 8 s (RULED). The only latency guidance in the fetched docs is A-err's 504 note ("Consider using the streaming Messages API for long-running requests") and D-rl's queueing keep-alive (F17). Measured stage-1 latencies are well under 120 s on every arm (hypothesis-arms and dose-pilot reports). No finding beyond F11 and F17.

---

## Ready Diffs (Not Applied)

**F01: catch the remaining transport failures uniformly.** This patch was generated with `diff -ru` from `/tmp` copies of the tip files. `git apply --check -p1` passes against `060abe0`, and probe 1 re-run against a patched `/tmp` copy shows all 8 cases caught (`attempts=4`, `ConnectionError`). It moves no request byte, and the error type matches the openai adapter's. It deliberately leaves the llama `null`-content case (an escape through `BackendResponse` validation) to F07, because mapping it to `""` changes its class from escape to parse, which is not mechanical.

```diff
diff -ru a/reasoning/vlm/anthropic_backend.py b/reasoning/vlm/anthropic_backend.py
--- a/reasoning/vlm/anthropic_backend.py	2026-10-07 02:20:26
+++ b/reasoning/vlm/anthropic_backend.py	2026-10-07 02:20:26
@@ -115,6 +115,8 @@
             raise ConnectionError(f"Anthropic request timed out: {exc}") from exc
         except requests.exceptions.ConnectionError as exc:
             raise ConnectionError(f"Anthropic connection failed: {exc}") from exc
+        except requests.exceptions.RequestException as exc:
+            raise ConnectionError(f"Anthropic request failed: {type(exc).__name__}") from exc
 
         if resp.status_code >= 400:
             # Truncate and never echo request headers/body — avoids leaking the key.
diff -ru a/reasoning/vlm/gemini_backend.py b/reasoning/vlm/gemini_backend.py
--- a/reasoning/vlm/gemini_backend.py	2026-10-07 02:20:26
+++ b/reasoning/vlm/gemini_backend.py	2026-10-07 02:20:26
@@ -109,7 +109,10 @@
                 f"Gemini returned HTTP {resp.status_code}: {resp.text[:400]}"
             )
 
-        data = resp.json()
+        try:
+            data = resp.json()
+        except ValueError as exc:
+            raise ConnectionError("Gemini response body malformed") from exc
         raw = dict(data)
         raw["unsupported_sampling"] = unsupported_sampling
         return BackendResponse(
diff -ru a/reasoning/vlm/llama_server_backend.py b/reasoning/vlm/llama_server_backend.py
--- a/reasoning/vlm/llama_server_backend.py	2026-10-07 02:20:26
+++ b/reasoning/vlm/llama_server_backend.py	2026-10-07 02:20:26
@@ -85,14 +85,21 @@
             raise ConnectionError(f"llama-server request timed out: {exc}") from exc
         except requests.exceptions.ConnectionError as exc:
             raise ConnectionError(f"llama-server connection failed: {exc}") from exc
+        except requests.exceptions.RequestException as exc:
+            raise ConnectionError(f"llama-server request failed: {type(exc).__name__}") from exc
 
         if resp.status_code >= 400:
             raise ConnectionError(
                 f"llama-server returned HTTP {resp.status_code}: {resp.text[:400]}"
             )
 
-        data = resp.json()
-        text = data["choices"][0]["message"]["content"]
+        try:
+            data = resp.json()
+            text = data["choices"][0]["message"]["content"]
+        except (ValueError, KeyError, IndexError, TypeError) as exc:
+            raise ConnectionError(
+                f"llama-server response body malformed: {type(exc).__name__}"
+            ) from exc
         token_usage = self._extract_usage(data)
 
         return BackendResponse(
```

**F15: redact before truncating** (all four adapters, same shape). This is an illustrative hunk, not an applicable patch, because it needs `redact_secret` moved to a shared module first.

```diff
-            raise ConnectionError(f"OpenAI returned HTTP {resp.status_code}: {resp.text[:400]}")
+            body = redact_secret(resp.text, self._api_key)[:400]
+            raise ConnectionError(f"OpenAI returned HTTP {resp.status_code}: {body}")
```

Every other FIX in this report changes an artifact or the retry policy, so each needs a ruling or a test-first change rather than a diff.

---

## Verification

**Probe 1: escape paths (local only, 127.0.0.1, no provider call).** A socket server answers each request in one of two ways:

- `midbody`: `HTTP/1.1 200`, `Content-Length: 5000`, ten bytes of body, then close.
- `html200`: a `text/html` 200.

Each adapter runs through the real `Reasoner` (`max_attempts=4`).

```text
midbody anthropic    ESCAPED Reasoner.run: requests.exceptions.ChunkedEncodingError
midbody llama_server ESCAPED Reasoner.run: requests.exceptions.ChunkedEncodingError
midbody gemini       RESULT attempts=4 error_type=ConnectionError usage_list=[None, None, None, None]
midbody openai       RESULT attempts=4 error_type=ConnectionError usage_list=[None, None, None, None]
html200 anthropic    RESULT attempts=4 error_type=ConnectionError usage_list=[None, None, None, None]
html200 llama_server ESCAPED Reasoner.run: requests.exceptions.JSONDecodeError
html200 gemini       ESCAPED Reasoner.run: requests.exceptions.JSONDecodeError
html200 openai       RESULT attempts=4 error_type=ConnectionError usage_list=[None, None, None, None]
```

The probe script (`/tmp`, not committed). Run it with the repo venv from any directory; it uses a dummy key value.

```python
import os, socket, sys, threading
sys.path.insert(0, "<worktree>")
from PIL import Image
from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import ReasonerConfig, ReasonerRequest, RobotStateInput
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.reasoner import Reasoner

MODE = {"m": "midbody"}
def serve(sock):
    while True:
        conn, _ = sock.accept(); conn.recv(1 << 20)
        try:
            while True:
                conn.settimeout(0.2)
                if not conn.recv(1 << 20): break
        except Exception: pass
        if MODE["m"] == "midbody":
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                         b"Content-Length: 5000\r\n\r\n{\"id\":\"x\",")
        else:
            body = b"<html>gateway</html>"
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                         b"Content-Length: %d\r\n\r\n" % len(body) + body)
        conn.close()

s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen(8)
threading.Thread(target=serve, args=(s,), daemon=True).start()
base = f"http://127.0.0.1:{s.getsockname()[1]}/v1"
os.environ["K"] = "dummy-not-a-key"
Image.new("RGB", (64, 48)).save("/tmp/f.png")
req = ReasonerRequest(request_id="r", image_path="/tmp/f.png", frame_id="f", stamp=0.0,
                      robot_states=[RobotStateInput(robot_id="robot_1", x=0, y=0, theta=0)])
arms = {"anthropic": lambda: AnthropicBackend(base_url=base, api_key_env="K"),
        "llama_server": lambda: LlamaServerBackend(base_url=base, model_id="m", mmproj_path="x"),
        "gemini": lambda: GeminiBackend(base_url=base, api_key_env="K"),
        "openai": lambda: OpenAIBackend(base_url=base, api_key_env="K")}
for mode in ("midbody", "html200"):
    MODE["m"] = mode
    for name, make in arms.items():
        try:
            r = Reasoner(make(), ReasonerConfig(backend_id=name, max_attempts=4, timeout_sec=5)).run(req)
            print(mode, name, "RESULT", r.diagnostics.attempts, r.diagnostics.error_type)
        except Exception as e:
            print(mode, name, "ESCAPED", type(e).__module__ + "." + type(e).__name__)
```

**Probe 2: artifact tallies (read-only, `data/logs` in the main checkout).**

- `served_model` per arm equals the configured id in every record (F04).
- HTTP-error `error_message` counts, as distinct events deduplicated by `request_id` (93 in total) (F02):
  - 47 OpenAI 429, all `credit_balance_exhausted`; 46 at `attempts=4`.
  - 42 Gemini 429, all spend-cap; all at `attempts=2`.
  - 3 Gemini 503 and 1 OpenAI 500.
  - A raw `grep` counts more, because decision JSON and traces repeat each event.
- A key-pattern scan found none (F15).
- Frame size 1280×960, maximum 846,452 B (Clean Areas).

**Local suite: zero delta.** The command was `pytest -q -p no:cacheprovider --continue-on-collection-errors`, run in the worktree with the repo venv.

| Run | Result |
|---|---|
| Before (tip `060abe0`) | 63 failed / 5,256 passed / 153 skipped / 3 errors |
| After (this commit, docs only) | 63 failed / 5,256 passed / 153 skipped / 3 errors; the sorted failed and error node ids are identical |

The 3 collection errors are the `pxr`-dependent USD tests (no Isaac Python on the Mac). The 63 failures are pre-existing and unchanged. Exactly one of them is in this review's scope: `test_factory_requires_config_for_openai` (F27). The payload-format pins (`-k payload_format`, 19 tests) pass.

**Spend:** $0.00. No provider API or listing call was made; every doc claim was settled by the fetched pages.

---

## Open Items for the Owner

Rulings are needed on four items:

- **F02:** a uniform retry policy, as an apparatus change after validation.
- **F05:** the flash cap.
- **F10:** `store` on the frozen ER-2 pin.
- **F13:** the local-arm attempt budget.

Spec text should be amended for two items:

- **F04:** the Group-D wording.
- **F12:** the gpt-5.1 lifecycle.

Every other FIX is an implementation task that moves no request byte (F01, F15, F27) or moves only artifact fields (F06–F09, F11, F14, F16, F18).
