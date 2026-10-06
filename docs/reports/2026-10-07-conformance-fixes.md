# Conformance Fixes: the Ruled Program on the Nine-Arm Backend Layer, plus the v1 Transport Hotfix

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: implementation of every FIX NOW and RULED item of the "Conformance-review RULINGS (2026-10-07)" block, on `feat/v2-conformance-fixes`, and the F01+F02 transport hotfix on `prereg-v1-hotfix`.

---

## Summary

This report implements the conformance-review rulings in the prereg-v2 design spec (main checkout, `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, "Conformance-review RULINGS (2026-10-07)"). The findings, locations and doc citations are in `docs/reports/2026-10-07-conformance-review.md`. No provider API was called: every provider shape in the tests is a mocked response copied from documentation fetched on 2026-10-07. Spend was **$0.00**, and no VM, merge or push was involved.

- **Branch `feat/v2-conformance-fixes`** (worktree from `feat/prereg-v2-composite` at `d746768`):
  - `c1e3c43`: F01, no exception escapes `Reasoner.run` or stage 2.
  - `e713c14`: F02, the uniform retry policy.
  - `d8570b2`: F03 through F27, the rest of the ruled batch.
  - A docs commit carries this report and the implementation-notes entry.
- **Branch `prereg-v1-hotfix`** (from tag `prereg-v1` = `569d95c`):
  - `efe085d`: F01, re-applied to the tag-era code.
  - `a475fe0`: F02, re-applied to the tag-era code.
  - Nothing else: prompts, parser decision semantics and config are untouched.
- **No request byte moved, except the two ruled flash fields.** A byte-freeze pin compares all nine arms' request bodies with the bodies generated at `d746768` before any edit. Only `gemini_flash` differs, by `max_output_tokens: 16384` (F05) and `store: false` (F10). The frozen ER-2 body is pinned byte-for-byte and sends no `store`.
- **Local suite, v2 branch.** The failing set went from 66 to 65 ids. The only change is `test_factory_requires_config_for_openai` turning green (F27). See Verification.
- **Local suite, hotfix branch.** Zero delta: 66 failing ids before and after.

---

## Per-Finding Fix Table

Each "Ruling" cell names the spec block's disposition.

| ID | Ruling | What changed | Pinned by |
|---|---|---|---|
| F01 | FIX NOW | Applied the review's ready diff (`git apply --check` passed). On top of it: `Reasoner.run` separates the backend call from the parse step. Any exception from the call is one recorded attempt. Any exception while reading a returned (billed) response is a parse failure of that attempt. A last-resort net returns a failed result with every attempt's usage. Stage 2 gets the same two handlers plus a net. Malformed bodies (non-object JSON, `message` not an object, non-dict steps or blocks) are guarded in every adapter. | `tests/unit/test_transport_no_escape.py`: all 8 probe cases of the review's socket harness through `Reasoner` (`attempts=4`, `ConnectionError`, usage `[None]*4`). The same 8 run through `RetreatChooser`. Plus unexpected adapter, parser and stage-2 parser exceptions. Pre-fix, the 4 review escapes plus the 3 new cases fail. |
| F02 | RULED | New `reasoning/vlm/retry_policy.py` and `BackendHTTPError` (`errors.py`, a `ConnectionError` subclass). Every adapter raises it through `transport.http_error` for any status of 400 or above. 429 and 5xx are retried with backoff and honour `Retry-After`. Every other 4xx ends the call after that attempt. Attempt budgets are unchanged. The same policy runs in both stages. Parameters are in Retry Policy below. | `tests/unit/test_retry_policy.py`: a 429 with `Retry-After: 7` sleeps exactly 7.0 s and then answers. A 400 consumes exactly one attempt on each of the 4 adapters and on stage 2. A persistent 503 spends 4 attempts with jittered waits in [1,2], [2,4] and [4,8]. Also covered: no wait after a timeout or after the final attempt, the total cap, HTTP-date `Retry-After`, and the classification of every status. |
| F03 | FIX NOW | Each adapter maps its provider's documented refusal channel to `BackendResponse.refusal` and `refusal_category`, using the raw provider code:<br>- OpenAI `message.refusal`.<br>- `finish_reason` `content_filter` (OpenAI, DeepSeek) and `sensitive` (Zhipu).<br>- Zhipu business error `1301`, delivered as HTTP 400 and checked before the generic 4xx stop.<br>- Gemini generation-blocked codes in an HTTP error body or on `status: failed`.<br>Anthropic was already structured. The English regex now runs only when no provider signal fired. Each attempt records `refusal_source` (`provider` or `text_pattern`). | Provider-Shape Tests below. A Zhipu 1301 sequence takes `attempts=4`, `refusal_attempts=4` and `image_fallback_attempt=3`, not a one-attempt stop. A Gemini `safety` block falls back and answers on attempt 3. |
| F04 | FIX NOW | `BackendResponse.system_fingerprint` is read from the body. It is folded into `ReasonerDiagnostics.system_fingerprint`, into `reasoner_config_effective.system_fingerprint` (like `served_model`) and into every `AttemptRecord`. | `test_deepseek_system_fingerprint_reaches_effective_config_and_records` |
| F05 | RULED | `gemini_flash.reasoner.max_tokens: 16384`, the GLM treatment. The Gemini adapter records the interaction `status` as `finish_reason`, so `incomplete` appears per attempt. | `test_gemini_flash_cap_is_16384`, `test_gemini_status_incomplete_is_recorded_per_attempt`, and the flash pins in `test_hypothesis_arms.py` |
| F06 | FIX NOW | `BackendResponse.finish_reason`, verbatim: OpenAI-compatible `finish_reason`, Anthropic `stop_reason`, or Gemini `status`. It is persisted per attempt (`AttemptRecord.finish_reason`), as the last value (`ReasonerDiagnostics.finish_reason`), and in the JSONL trace. | `test_finish_reason_is_persisted_in_decision_and_trace` (5 arms) |
| F07 | FIX NOW | A valid 200 with no text yields `text=""` and its usage, so it takes the parse path on every adapter: Anthropic no longer raises, and a llama `null` content becomes `""`. Non-JSON or truncated bodies stay transport failures. | `test_valid_200_without_text_is_a_parse_failure_with_usage` (4 adapters). `test_non_refusal_without_text_is_an_empty_billed_response`, renamed in `test_anthropic_backend.py`. |
| F08 | FIX NOW | The OpenAI-compatible adapter lists `top_k` and `presence_penalty` in `raw["unsupported_sampling"]` on every call, plus `temperature`/`top_p` under `omit_sampling`. That follows the existing convention: "configured values recorded, unsent subset repeated". No request byte moves. | Extended wire pin `test_recorded_sampling_and_thinking_fields_are_exactly_what_is_sent` (9 arms). Each sampling field is either sent with its recorded value, or listed as unsent and absent from the body. `thinking_level`, `seed`, the token cap, `thinking_mode`, `effort` and `reasoning_effort` each equal the body's value. It fails on the 4 OpenAI-adapter arms before the fix. |
| F09 | FIX NOW | `diagnostics.backend_id` and `RetreatChoiceResult.backend_id` are the arm id (`ReasonerConfig.backend_id`) on every path. Documented on both models, including how to group records written before the fix. | `test_success_records_the_arm_id_not_the_model_id`; `test_retreat_chooser.py::test_rendered_letter_is_answered` (updated) |
| F10 | RULED | New `GeminiBackendConfig.store: bool \| None = None`. `None` omits the field. It is appended last, only when set. `gemini_flash` sets `store: false`. ER-2 keeps its frozen wire shape (see the privacy note below). | `test_gemini_flash_sends_store_false`, `test_er2_frozen_request_shape_is_byte_identical_and_sends_no_store` |
| F11 | FIX NOW | A `requests` timeout raises `BackendTimeoutError` on all four adapters, so stage 2 labels it `timeout` deterministically. | `test_requests_timeout_is_a_backend_timeout_on_every_adapter`, `test_stage2_labels_a_requests_timeout_as_timeout` (4 adapters each) |
| F13 | RULED | `llama_server_qwen3vl` and `llama_server_molmo2er` now use `max_attempts: 4` and `image_fallback_after_attempts: 2`. The Cosmos `llama_server` section is not an arm and stays a pinned section. | `test_local_arms_have_full_parity`, `test_local_arm_grey_fallback_fires_on_a_text_refusal` |
| F14 | FIX NOW | A stage-1 re-ask is built from the un-suffixed base: the original payload, or the neutral-image payload once the fallback fired. The suffix therefore appears exactly once, as in stage 2. | `test_stage1_reask_suffix_never_stacks`, `test_stage1_reask_after_fallback_keeps_the_neutral_image` |
| F15 | FIX NOW | New `transport.redact_secret` and `safe_error_text`, which redact before truncating. They apply to every HTTP error body and every `requests` exception message on the keyed adapters. The `scripts/probe_*` copies stay as they are (F20 deferred). | `test_http_error_body_echoing_the_key_is_redacted` (OpenAI, Anthropic, Gemini, Zhipu) |
| F16 | FIX NOW | Additive `token_usage` keys:<br>- `cached_tokens` (OpenAI and Zhipu `prompt_tokens_details`; Gemini `total_cached_tokens`).<br>- `image_tokens` (OpenAI).<br>- `prompt_cache_hit_tokens` and `prompt_cache_miss_tokens` (DeepSeek).<br>- `tool_use_tokens` and `input_tokens_<modality>` (Gemini).<br>The nonexistent Gemini `usage_metadata` fallback is removed. | `test_openai_usage_adds_cached_and_image_tokens`, `test_deepseek_usage_adds_cache_hit_and_miss`, `test_zhipu_usage_adds_cached_tokens`, `test_gemini_usage_adds_cached_tool_and_modality_tokens`, `test_gemini_usage_ignores_the_nonexistent_usage_metadata_field` |
| F18 | FIX NOW | `BackendResponse.provider_request_id`, and the same field on `BackendHTTPError`, recorded per attempt. Sources: the `x-request-id` header (OpenAI) or `request-id` header (Anthropic); otherwise the body's `request_id` (Zhipu, Anthropic error bodies); otherwise the body's `id` (completion or interaction id). | `test_openai_request_id_header_is_recorded`, `test_anthropic_request_id_header_is_recorded_on_an_http_error`, `test_zhipu_body_request_id_is_recorded`, `test_gemini_interaction_id_is_recorded` |
| F21 | FIX NOW | `scripts/vm/molmo_serve.sh` passes `--generation-config vllm`, with a comment citing V-oai. | `test_molmo_vllm_server_ignores_the_repo_generation_config` |
| F22 | FIX NOW | Stale comments fixed:<br>- `gemini_backend` "silently" and "not documented to echo a served version".<br>- `models.py`, the fallback scope comments.<br>- The `OpenAIBackendConfig` and `AnthropicBackendConfig` defaults, now marked "model default only". The default values themselves are unchanged. | (comments only) |
| F27 | FIX NOW | `build_backend("openai", None)` and `build_backend("gemini", None)` now raise `ValueError("<adapter> backend requires …")`. | `test_factory_requires_config_for_openai` (was red, now green); `test_factory_requires_config_for_gemini` (updated) |

Not in this program, per the rulings:

- **Accepted as reported:** F17, F19, F23, F24 and F25.
- **Deferred to v3:** F20 (adapter dedup). It is the root of F01, F07 and F11; `transport.py` is the start of that shared layer.
- **Spec amendments, the coordinator's to write:** F12 and F04 (GLM and ER-2 wording).

---

## Retry Policy (F02)

The module constants live in `reasoning/vlm/retry_policy.py`. `test_documented_parameters` pins them.

| Parameter | Value | Meaning |
|---|---|---|
| `BACKOFF_BASE_SEC` | 2.0 | Exponential ceiling before retry *k* (k = 1-based index of the failed attempt): `min(cap, base * 2^(k-1))` |
| `BACKOFF_CAP_SEC` | 30.0 | Largest exponential ceiling |
| jitter | equal | The wait is uniform in [ceiling/2, ceiling]. Waits after attempts 1, 2 and 3 fall in [1,2], [2,4] and [4,8] s. |
| `RETRY_AFTER_CAP_SEC` | 60.0 | A `Retry-After` value (seconds or HTTP-date) replaces the exponential wait and is clamped here |
| `MAX_TOTAL_BACKOFF_SEC` | 90.0 | Sum of waits within one call. Once it is spent, any remaining retries go out without waiting. |

Classification (`classify_failure`):

| Failure | Decision |
|---|---|
| HTTP 429, any 5xx (including Anthropic 529) | retry after backoff |
| Any other HTTP 4xx (400, 401, 402, 403, 404, 408, 413, 422, …) | **stop**: the call ends after this attempt |
| Transport (connection reset, body closed mid-stream, malformed body) | retry after backoff |
| Timeout (`BackendTimeoutError`) | retry with no wait, because the call already spent `timeout_sec` |
| Any other adapter exception | retry with no wait (it is local; the F01 classification) |
| A documented refusal delivered as a 4xx (Zhipu 1301, Gemini blocked codes) | not an error: the refusal path and grey fallback |

**The `error_type` vocabulary is unchanged.** `BackendHTTPError` is recorded as `"ConnectionError"` (`recorded_error_type`), because two analysis scripts classify transport failures by `error_type ∈ {"ConnectionError", "BackendTimeoutError"}`:

- `scripts/probe_presentation_order.py:449`.
- `scripts/probe_presentation_order.py:880`.

The status, provider code, `Retry-After` and backoff are in `AttemptRecord` instead.

**Worst-case wall clock (flag for the owner).** No wait follows the final attempt, so the waits add to the ruled per-attempt bounds as follows:

- **Stage 1** (4 attempts × 120 s): at most 3 waits, capped at 90 s in total. The worst case is 570 s, against 480 s before.
- **Stage 2** (2 attempts × 8 s): at most one wait. The exponential wait is 1 to 2 s, but a `Retry-After` can be honoured up to 60 s, so the worst case is 76 s, against 16 s before.
  - `RetreatChoiceResult.max_attempts` and `timeout_sec` still describe the attempt bound.
  - The actual waits are recorded per attempt as `AttemptRecord.backoff_sec`.
  - M5's worker has no outer wall-clock bound (`orchestrator_node.py:767`). The machine stays in ANALYZING while the worker waits.
  - If the 8 s stage-2 bound should be wall-clock as well as per attempt, a stage-2-specific `RetryPolicy(retry_after_cap_sec=…)` is a one-line change. It is not made here, because the ruling says "uniform".

**Quota 429s are retried, as ruled.** The ruling's literal text is "429/5xx retry". The review's 47 OpenAI `credit_balance_exhausted` and 42 Gemini spend-cap 429s are quota events that the docs call non-retryable:

- O-err says "Add credits to continue".
- G-err's `quota_exceeded` says "Wait until the quota resets".
- A-err says "A tier spend-cap 429 has no `retry-after` header and keeps failing".

They now cost at most 90 s of waiting per call, not zero. `AttemptRecord.provider_error_code` records the code, so these events can be identified. A quota carve-out is an **open item** for the owner and is not implemented.

---

## Artifact Changes

All fields are additive and defaulted, so artifacts written before these fixes still parse.

- **`AttemptRecord`** (new; `ReasonerDiagnostics.attempt_records`, `RetreatChoiceResult.attempt_records`). It is index-aligned with `attempt_token_usage`, with these fields:
  - `outcome`: one of `answered`, `invalid_label`, `parse_failure`, `refusal`, `timeout`, `http_error`, `transport_error` or `unexpected_error`.
  - `error_type`, `http_status` and `provider_error_code`.
  - `finish_reason`, `provider_request_id` and `system_fingerprint`.
  - `refusal_source`, `retry_after_sec` and `backoff_sec`.
- **`ReasonerDiagnostics`:** adds `system_fingerprint`, `finish_reason` and `attempt_records`.
- **`EffectiveSamplingConfig`:** adds `system_fingerprint`.
- **`BackendResponse`:** adds `finish_reason`, `provider_request_id` and `system_fingerprint`.
- **JSONL trace:** adds `finish_reason`, `system_fingerprint` and `attempt_records`, each written when present.
- **`GeminiBackendConfig`:** adds `store`.

Semantic changes, all ruled:

- `diagnostics.backend_id` is the arm id on success too (F09).
- The OpenAI-adapter arms' `unsupported_sampling` is no longer `None`; it lists `top_k` and `presence_penalty` (F08).
- Timeouts on the openai, anthropic and llama_server adapters record `BackendTimeoutError` instead of `ConnectionError` (F11). Both names are in the transport set the analysis scripts use.
- An Anthropic empty 200 is a parse failure with usage, no longer a transport failure (F07).
- Provider refusals count in `refusal_attempts` and fire the grey fallback (F03).

**F10 privacy note (ER-2 deviation).** The frozen ER-2 pin still sends no `store`. Its interactions are therefore stored provider-side by default: "By default, the API stores all Interaction objects (store=true) … Paid tier: The system retains interactions for 55 days" (G-int). Every annotated frame, zoom tile and prompt sent on the `gemini` arm is retained for 55 days. This is the ruled cost of keeping the frozen pin's wire shape. It is recorded here and in the `gemini_flash` comment in `config/models.yaml`.

---

## Provider-Shape Tests (F03, F04, F16, F18)

Every test lives in `tests/unit/test_conformance_fixes.py`. Each test's docstring quotes the doc text (fetched 2026-10-07) whose shape it mocks.

| Provider | Test | Documented shape (doc) |
|---|---|---|
| OpenAI | `test_openai_message_refusal_is_a_provider_refusal` | `message.refusal` string, `content` null (O-chat) |
| OpenAI / gpt-5.1 / DeepSeek | `test_content_filter_finish_reason_is_a_provider_refusal` | `finish_reason: "content_filter"` (O-chat, D-chat) |
| Zhipu | `test_zhipu_sensitive_finish_reason_is_a_provider_refusal` | `finish_reason: "sensitive"` (Z-chat) |
| Zhipu | `test_zhipu_1301_http_400_is_a_provider_refusal` | HTTP 400 `{"error": {"code": "1301", …}}`, code as a string (Z-code example) and as an integer (Z-chat `Error.code: integer`) |
| Zhipu | `test_zhipu_non_refusal_400_stays_a_deterministic_error` | HTTP 400 code `1210` (Z-code) |
| Zhipu | `test_zhipu_1301_takes_the_refusal_path_with_grey_fallback` | 1301 through the full pipeline |
| Gemini | `test_gemini_generation_blocked_code_is_a_provider_refusal` (11 codes) | `{"error": {"code": <blocked code>, "message": …}}` (G-err "Generation blocked codes" and "Error response format") |
| Gemini | `test_gemini_blocked_code_takes_the_refusal_path_with_grey_fallback` | the same, through the full pipeline (flash) |
| Gemini | `test_gemini_failed_status_with_blocked_code_is_a_provider_refusal`, `…without_blocked_code_is_a_transport_failure` | Interaction `status: "failed"` (G-api) |
| Gemini | `test_gemini_status_incomplete_is_recorded_per_attempt` | `status: "incomplete"` (G-api) |
| Anthropic | `test_anthropic_refusal_shape_is_a_provider_refusal` | the A-ref "What a refusal looks like" body, verbatim (`stop_details.category: "cyber"`) |
| any | `test_text_pattern_is_only_the_fallback_refusal_channel`, `test_provider_refusal_counts_on_stage2` | plain `stop` with refusal text; stage-2 `content_filter` |
| DeepSeek | `test_deepseek_system_fingerprint_reaches_effective_config_and_records` | `system_fingerprint` (D-chat) |
| OpenAI / DeepSeek / Zhipu / Gemini | the four `…usage_adds…` tests | `prompt_tokens_details.{cached_tokens,image_tokens}` (O-chat); `prompt_cache_hit/miss_tokens` (D-chat); `prompt_tokens_details.cached_tokens` (Z-chat); the G-api example `usage` block |
| OpenAI / Anthropic / Zhipu / Gemini | the four `…request_id…` tests | `x-request-id` header (O-ov); `request-id` header plus the error body's `request_id` (A-err); body `request_id` (Z-chat); interaction `id` (G-api) |

Doc URLs use the review's keys. One page is new here: O-ov = `https://developers.openai.com/api/reference/overview` ("x-request-id: Unique identifier for this API request").

---

## Existing Tests Updated Deliberately

Each of these pinned pre-ruling behaviour. Each update is named here, so the zero-delta claim is auditable.

| Test | Finding | Change |
|---|---|---|
| `test_anthropic_backend.py::test_non_refusal_without_text_maps_to_connection_error` | F07 | Renamed `…_is_an_empty_billed_response`. It now asserts `text=""`, `finish_reason="max_tokens"` and usage kept. |
| `test_anthropic_backend.py::test_timeout_maps_to_connection_error` | F11 | Renamed `…_to_backend_timeout_error` |
| `test_openai_backend.py::test_timeout_maps_to_connection_error` | F11 | Renamed `…_to_backend_timeout_error` |
| `test_gemini_backend.py::test_factory_builds_gemini_backend_with_default_config` | F27 | Renamed `test_factory_requires_config_for_gemini` (raises) |
| `test_hypothesis_arms.py::test_gemini_flash_request_sends_no_sampling_and_thinking_low` | F05 | The cap is 16384 |
| `test_hypothesis_arms.py::test_gemini_flash_request_is_packed_exactly_like_the_er2_pin` | F05, F10 | It still asserts equal packing, and now pins the two ruled differences explicitly |
| `test_reasoning_dose_knobs.py::test_omit_sampling_records_the_dropped_values_per_call` | F08 | Adds `top_k` and `presence_penalty` |
| `test_reasoning_dose_knobs.py::test_omit_sampling_defaults_off_and_keeps_sampling_fields` | F08 | `unsupported_sampling` is `{top_k, presence_penalty}` |
| `test_retreat_chooser.py::TestChoose::test_rendered_letter_is_answered` | F09 | `backend_id` is the config's arm id |

`tests/unit/conftest.py` gains an autouse fixture that makes the policy's default sleep a no-op in unit tests. Tests that assert on waits inject `RetryPolicy(sleep=…)`.

---

## v1 Transport Hotfix (`prereg-v1-hotfix`)

This implements the V1-COLLECTION BRIDGE ruling: collection runs from the tag plus F01 and F02 only. The branch was created with `git branch prereg-v1-hotfix prereg-v1` in the main repo, and checked out as a worktree at `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v1-hotfix`.

- **`efe085d` (F01).**
  - The review's ready diff applies cleanly to the tag (`git apply --check` passed).
  - Two tag-era gaps were added. The OpenAI and Anthropic adapters call `resp.json()` unguarded at the tag; the OpenAI malformed-body guard dates from 2026-10-06, after the tag.
  - Six of the eight probe cases escape at the tag, against four at `060abe0`. All 8 are now caught.
  - `Reasoner.run` gets the same split handlers and last-resort net as v2, adapted: the tag-era diagnostics have no `attempt_token_usage`.
  - Stage 2 needed only its parse handler widened to `Exception`. The tag-era `RetreatChooser` already caught every backend exception, so there is no separate stage-2 net on this branch.
- **`a475fe0` (F02).** The same `errors.py`, `retry_policy.py` and `transport.py` as v2's `e713c14`, with the same constants and classification. The four adapters raise `http_error`, and the policy is wired into the tag-era `Reasoner` and `RetreatChooser`.
- **F02 without F03 on ER-2 (for the protocol note).** On this branch, a Gemini generation-blocked code delivered as an HTTP 4xx is a deterministic stop. ER-2 therefore spends 1 attempt where it previously spent 2, and the call ends `decision=None` with a "ConnectionError". The ruling treats this as moot ("ER-2 never refuses"), so nothing changes in practice, but the coordinator's protocol note should state it.
- **Docstring pointer.** The hotfix's `retry_policy.py` docstring points to this report, which exists only on the v2 branch.
- **Untouched on this branch.** Prompts, the parser's decision semantics, config, refusal detection (F03 is not needed for v1), artifact fields (no `AttemptRecord`), and every request byte. `git diff --stat prereg-v1 prereg-v1-hotfix` touches only `reasoning/vlm/` adapters, `reasoner.py`, `retreat_chooser.py`, `errors.py`, the two new modules, and tests.
- **Verification** (repo venv, `pytest -q -p no:cacheprovider --continue-on-collection-errors`):

| Run | Result |
|---|---|
| Tag `569d95c`, clean `git archive` export | 63 failed / 2933 passed / 16 skipped / 3 errors (66 failing ids) |
| `prereg-v1-hotfix` at `a475fe0` | 63 failed / 2994 passed / 16 skipped / 3 errors. The sorted failing ids are identical (zero delta); +61 tests are new. |
| Reasoner and adapter subset at the tag (`test_{anthropic,gemini,openai}_backend`, `test_llama_server_scripts`, `test_m5_retreat_stage2`, `test_reasoner`, `test_retreat_chooser`, `test_vlm_{config,models,output_parser}`) | 1 failed / 294 passed / 1 skipped |
| The same subset plus the two new files, on the hotfix | 1 failed / 355 passed / 1 skipped. The 1 failure is the pre-existing `test_factory_requires_config_for_openai`, F27, which is not in the hotfix scope. |

**Protocol note: open for the coordinator.** The ruling asks for the hotfix to be "documented as a protocol note in the amendments doc". That note is **not written here**; it is the coordinator's to write. The branch is not pushed.

---

## Verification (v2 branch)

The command was `pytest -q -p no:cacheprovider --continue-on-collection-errors`, run in the worktree with the repo venv.

| Run | Result |
|---|---|
| Before (`d746768`) | 63 failed / 5256 passed / 153 skipped / 3 errors (66 failing ids) |
| After F01 (`c1e3c43`) | 63 / 5275 / 153 / 3; identical failing set |
| After F02 (`e713c14`) | 63 / 5317 / 153 / 3; identical failing set |
| After the batch (`d8570b2`) | 62 / 5404 / 153 / 3 (65 failing ids). The only set change is `test_openai_backend.py::test_factory_requires_config_for_openai` turning green. |

The 3 errors are the `pxr`-dependent USD tests (no Isaac Python on the Mac). The 62 remaining failures are pre-existing and outside this program.

Discrimination check: the new test modules were run against a clean `git archive` export of the pre-fix code (`d746768`, with its `config/models.yaml`).

- `test_conformance_fixes.py`: 70 of 86 fail. The 16 that pass are invariants that already held:
  - the byte freeze for the 8 unchanged arms (ER-2 included), plus the ER-2 frozen-shape pin;
  - the wire pin on the five non-OpenAI-adapter arms;
  - Gemini's existing timeout mapping;
  - the re-ask-after-fallback case.
- `test_transport_no_escape.py`: 7 of 19 fail. These are the review's 4 escapes plus the 3 extended cases.

---

## Open Items for the Owner

- **Stage-2 wall clock.** `Retry-After` can add up to 60 s to the 2 × 8 s stage-2 bound (see Retry Policy). It is uniform as ruled; a stage-2 clamp is a one-line change if wanted.
- **Quota 429 carve-out.** All 429s are retried as ruled. `provider_error_code` makes quota events identifiable (OpenAI `insufficient_quota`/`credit_balance_exhausted`, Gemini `quota_exceeded`, Zhipu 1113/1308–1321), so a carve-out could be added later.
- **Gemini `RetryInfo`.** Only the `Retry-After` header is honoured. A delay carried in a Gemini error body is not parsed, because G-err documents no such body field.
- **Amendments doc.** The coordinator still has to write the v1 hotfix protocol note, plus the F04 (Group-D wording) and F12 (gpt-5.1 lifecycle) spec amendments.
- **Zhipu `reasoning_tokens`.** It is still read from `completion_tokens_details`, which Z-chat's usage schema does not list. It works live; the code notes this.
- **Downstream consumers of the semantic changes.** `scripts`, `ros2_ws/src` and `benchmarks` were grepped for readers of `unsupported_sampling` (F08) and `backend_id` (F09):
  - `scripts/capability_probes.py:270` already keys on the selector, and `scripts/summarize_capability_probes_v2.py:36` reads those records.
  - `scripts/probe_presentation_order.py:561` writes the field without classifying on it.
  - `scripts/probe_refusals.py:58` maps both `"openai"` and `"gpt-4o"` to gpt-4o, so the F09 arm id still maps correctly.
  - No reader classifies arms on `unsupported_sampling is None`.
  - **One interaction needs a decision.** `scripts/probe_refusals.py:172` counts refusals by regex on `raw_text` only, so it would miss provider-channel refusals (F03), which often carry no text. A reader of new artifacts should use `diagnostics.refusal_attempts` or `attempt_records[].refusal_source`. Not patched; it is outside this program's scope.
