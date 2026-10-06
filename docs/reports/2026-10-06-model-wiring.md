# Model Wiring: Sonnet 5.5, Qwen3-VL-8B, gpt-5.1 Pilot, DeepSeek

**Prepared:** 2026-10-06

**Revision history:**

- Initial draft: wiring for the four ruled or extended arms, validation of Qwen3-VL-8B (full standard) and gpt-5.1 (pilot standard), and the two key-blocked skips (Sonnet 5.5 and DeepSeek).

---

## Summary

The contract is the "Model-wiring ruling (2026-10-06)" block of `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` in the main checkout. The coordinator later added DeepSeek as a fourth, exploratory arm. Every arm sits behind the `VLMBackend` interface. Keys are read from the environment only and are never logged.

| Arm | Wiring + unit tests | Preflight | Probe battery v1 (60) | Head-on episodes | Status |
|---|---|---|---|---|---|
| Qwen3-VL-8B Q4_K_M (`llama_server_qwen3vl`) | done | OK | **57/60** | s42 `clogged` 1/2; s43 `intermittent` 2/2 | validated (full standard) |
| gpt-5.1 pilot (`openai_gpt51`) | done | OK (live listing confirms the pin) | **54/60** | s42 `resolved` 2/2, verbatim plan | validated (pilot standard) |
| Claude Sonnet 5.5 (`anthropic`) | done | **SKIPPED: no `ANTHROPIC_API_KEY`** | skipped | skipped | key needed from the user |
| DeepSeek (`deepseek`, exploratory) | done | **SKIPPED: no `DEEPSEEK_API_KEY`** | skipped | skipped | key needed from the user |

Headlines:

- **Qwen3-VL-8B has the perception primitives but never uses the plan channel.**
  - It scored 57/60 on probe battery v1. That is level with gpt-4o (58/60) and inside the same Wilson band.
  - It named the correct yielder (robot_2) on both trigger decisions.
  - It returned `"proposed_plan": null` on all 17 of its stage-1 decisions. Plan emission is **0/15** dispatched plans, so every plan was `m3_default` (absent).
  - In s42 it then replanned `temporary_wait` 11 times while robot_2 sat about 2.64 m from its goal. The episode ended `clogged`.
- **gpt-5.1 at `reasoning_effort: "none"` gave the cleanest head-on run so far, at n = 1 and on prompt v3.3 against the pilot's v3.2 (see STOP item 4).**
  - Its trigger plan was `vlm_verbatim` with 0 edits, naming the correct yielder robot_2.
  - The episode resolved 2/2 with a delay sum of 143.8 s. Every verbatim-pilot head-on episode was between 147.4 and 153.3 s.
  - It refused 0 of its 5 stage-1 attempts and 0 of 60 probes.
  - On the probes it is the weakest arm: 54/60. It miscounted robots on 4/15 `robot_count` items, all at true counts of 3 or 4.
  - All 6 of its probe misses chose letter A.
- **The VRAM co-residency gate held with a wide margin.**
  - With Isaac Sim and llama-server both running, the L4's peak use was 10,085 MiB of 24,570 MiB, leaving at least 14,008 MiB free.
  - The gate (need 9,216 + margin 2,048 + Isaac reserve 3,072 MiB) was registered and committed before it first ran.
- **Multi-image under llama-server passed.** Both smoke gates passed (see "Qwen3-VL-8B"), so the Qwen arm ships with `multi_image: true`. The head-on overlay has no zoom tile, so the episodes were single-image in any case.
- **Spend:** about $0.10 in total, all gpt-5.1. Qwen costs $0 in API fees. The hard stop was $10.

**STOP items for the owner:**

1. **Sonnet 5.5 validation is blocked on a key.** `ANTHROPIC_API_KEY` is absent from the VM's `/ws/.env`, from the `vgu_ros` container environment, and from the local `.env`. The live model-ID check (`GET /v1/models`) could not run either. `claude-sonnet-5-5` is wired from the bundled claude-api reference table (cached 2026-09-25) and is **unverified against the live listing**. With a key, run `scripts/preflight_backend.py --backend anthropic --list-models` before any probe.
2. **DeepSeek validation is blocked on a key, and the requested model ID is retired.** `DEEPSEEK_API_KEY` is absent from the same three places. The raw HTML of DeepSeek's docs was fetched on 2026-10-06 and grepped; the quotes below are verbatim:
   - Pricing page (`api-docs.deepseek.com/quick_start/pricing`): "Use deepseek-flash as the model name. The legacy names deepseek-v4-flash and deepseek-v4-flash-vision-exp are still accepted, but the corresponding models have been retired, their requests are served by the DeepSeek-V4.1-Flash model and billed at the Flash price."
   - Vision guide (`/guides/vision`): "The legacy model name deepseek-v4-flash-vision-exp is still accepted, but the model has been retired and its requests are served by the latest Flash model as well."
   - The same guide sets the image budget: images are resized so "the total pixel count after resizing is roughly that of a 1300×1300 image. As a result, there is an upper bound of 1024 tokens per image".
   - **Where the 384 figure comes from.** The coordinator's "up to 384 tokens" is verbatim from the 2026-08-21 launch note (`/news/news260821`: "Images are tokenized for billing: up to 384 tokens each"). The docs' change log then lists "DeepSeek-V4.1-Flash Release 2026/09/10". The 384 cap therefore describes the retired `-exp` model, not the model that now serves that name.
   - **Consequences.** The arm is wired with the requested ID, plus a comment and per-call served-model recording. Whether to re-pin to `deepseek-flash` is the owner's decision. Either way, the ≤384-token compression question no longer has a live model to test: any call will be served by V4.1-Flash at a cap of up to 1,024 tokens.
3. **Qwen never emits a plan.** For a plan-quality study, Qwen's arm measures only the M3 default. Whether that is acceptable, or the prompt should press for a plan, is an owner decision. It is a prompt-apparatus question, not a wiring one.
4. **The episode comparison is confounded by the prompt version.** The verbatim-pilot head-on rows ran prompt **v3.2** on tree `a8fc1bc`. These episodes ran **v3.3** (66a4f4f, list-order line present in 22/22 stage-1 prompts). List order was the head-on reorder driver, so provenance and edit counts are not like-for-like. See "Comparability".

---

## Wiring

Three code commits on `feat/v2-model-wiring`, branched from `feat/prereg-v2-composite` at `41ba9e0`, plus this report's commit:

- `7c362cc` — the adapters, the config, and the refusal pipeline;
- `73b79cb` — the serving script;
- `565fac3` — `multi_image: true` for Qwen, committed after its smoke gate passed.

### Arm selection

`config/models.yaml` gains four sections. The existing `reasoner`, `llama_server` (Cosmos), `openai` (gpt-4o) and `gemini` sections are **unchanged**; `test_existing_pinned_sections_are_unchanged` pins them verbatim.

- A section whose name is not an adapter name selects its transport with an `adapter:` key.
- One adapter type table, `BACKEND_CONFIG_TYPES` in `reasoning/vlm/backend_factory.py`, feeds every consumer: `backend_adapter`, `load_backend_config`, M5's `_load_vlm_config`, and the probe runner's `load_backend_settings`.
- M5's zoom-tile fail-fast now refuses only a llama_server arm whose `multi_image` is off. The Cosmos pin keeps that refusal.
- `build_backend` still dispatches on adapter names only, so an unknown ID with a config still raises (the existing pin).

| Section | Adapter | Model ID | Request controls | Reasoner override |
|---|---|---|---|---|
| `anthropic` | anthropic | `claude-sonnet-5-5` | `thinking: {"type": "between_tools"}`; no temperature/top_p/top_k ever sent | temperature 0.0 (recorded as unsupported) |
| `openai_gpt51` | openai | `gpt-5.1-2025-11-13` | `reasoning_effort: "none"`, `max_completion_tokens` | temperature 0.0, `max_attempts` 4, image fallback after 2 (mirrors the gpt-4o pin) |
| `llama_server_qwen3vl` | llama_server | `qwen3-vl-8b-instruct-q4_k_m` (the server alias) | `multi_image: true` | temperature 0.0 (blocks the Cosmos 0.6 preset) |
| `deepseek` | openai | `deepseek-v4-flash-vision-exp` | base URL `https://api.deepseek.com`, `thinking: {"type": "disabled"}` | temperature 0.0 |

`EffectiveSamplingConfig` gains `reasoning_effort`, `thinking_mode` and `effort`, so every decision artifact shows these controls. They stay `null` for the existing pins.

### Anthropic adapter

The adapter existed but had never been exercised. The changes:

- **Sampling is never sent.** Sonnet 5.5 returns HTTP 400 on non-default sampling values. The configured temperature, top_p, top_k and presence_penalty are recorded per call in `raw["unsupported_sampling"]`, following the ER-2 precedent, and one WARNING is logged per backend instance.
- **Thinking is now explicit.** On Sonnet 5.5, omitting `thinking` runs adaptive thinking, billed as output. The old comment assumed it was off.
  - The arm sends `between_tools`, which turns thinking off. It is legal at effort `high` or below, and effort is not sent.
  - This matches the other new hosted arms, which answer as no- or low-thinking classifiers (gpt-5.1 at `none`, ER-2 at `low`).
  - The adapter now skips `thinking` blocks when reading text.
- **Refusals are refusals.** An HTTP-200 response with `stop_reason: "refusal"` used to raise `ConnectionError`, so the Reasoner treated it as a transport failure. It was never counted in `refusal_attempts`, never triggered the grey-image fallback, and the probe runner scored it `backend_error`.
  - It now returns a `BackendResponse` with `refusal=True` and `refusal_category` taken from `stop_details.category`.
  - `Reasoner`, `RetreatChooser` and the probe runner treat that flag exactly like a text refusal (`is_refusal`), even when the refusal carries parseable text.
  - `ReasonerDiagnostics.refusal_category` records the category.
  - The old test that pinned `ConnectionError` was rewritten deliberately.
  - No server-side `fallbacks` parameter is sent: it would re-route a refusal to a different model inside the arm.
- **Multi-image and usage.** The payload is frame first, then the zoom tile, then the text. Usage records `input_tokens`, `output_tokens` and the two cache counters.
- **Owner note for when the key arrives.** The `anthropic` section inherits the shared `max_attempts: 2` and has no grey-image fallback, whereas gpt-4o and gpt-5.1 use 4 attempts with the fallback after 2. Pick one setting before comparing refusal profiles across arms.

### OpenAI-compatible adapter

- **New fields, absent by default.** `reasoning_effort`, `max_tokens_param` and DeepSeek's `thinking` are added only when configured.
- **The gpt-4o pin is byte-identical.** Its request body is compared against the exact JSON the pre-wiring adapter produced from the shipped config (`test_gpt4o_pin_request_body_is_byte_identical_to_the_pre_wiring_body`).
- **gpt-5.1 rejects `max_tokens`.** The live API answered: "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead." That is why the arm sets `max_tokens_param` (`preflight/gpt51_max_tokens_check.txt`).
- **Truncated bodies are transport errors.** A truncated or malformed HTTP-200 body now raises `ConnectionError` (a transport retry), not a crash. This covers DeepSeek's reported 1–3% of silently closed connections; a closed socket was already a `ConnectionError`. The request timeout is the configured `timeout_sec`.

### Tests

`tests/unit/test_model_wiring.py` adds 33 tests, mocked HTTP only:

- the config pins;
- request shapes for all four arms. The Sonnet body's key set is exactly `{model, system, messages, max_tokens, thinking}`, with no temperature key;
- refusal classification (empty and with-text);
- multi-image ordering for Anthropic, DeepSeek and llama_server;
- usage extraction;
- transport-error mapping;
- the structured refusal through `Reasoner` (counted, category recorded, grey-image fallback fires on attempt 3) and through `RetreatChooser`.

`test_capability_probes_runner.py` gains a structured-refusal tagging test. Its "unsupported backend" test now uses a non-existent ID, because `llama_server` is a supported battery backend now.

**Full suite:** 63 failed / 5184 passed / 153 skipped / 3 errors, against 63 / 5149 / 153 / 3 at `41ba9e0`. The sorted failed/error node IDs are identical before and after, and the flags were identical (`--continue-on-collection-errors`). The +35 passes are the new tests.

---

## Qwen3-VL-8B

### Serving and served-model verification

`scripts/vm/qwen_serve.sh` (`fetch | verify | gate | start | status | stop`) pins everything it serves:

- **Weights:** the official `Qwen/Qwen3-VL-8B-Instruct-GGUF` at revision `f982a07559d4a2f6c8744d840bf6fccab30eea96`.
  - `Qwen3VL-8B-Instruct-Q4_K_M.gguf`: 5,027,784,800 B, sha256 `67d1659b…`.
  - `mmproj-Qwen3VL-8B-Instruct-F16.gguf`: 1,159,029,824 B, sha256 `ca524100…`.
  - Both were verified after download and again before every start.
- **Server:** llama.cpp `server-cuda` pinned by digest `sha256:c6fd6053…`, reporting `build_info b11434-5e03bdd87`.
  - It runs under the nvidia runtime, on the host network, bound to 127.0.0.1:8080, with `-c 8192 -np 1 -ngl 99 --jinja --alias qwen3-vl-8b-instruct-q4_k_m`.
  - The host has no CUDA toolkit, and the nvidia container runtime was already configured, so no daemon change was needed.
- **Served-model verification:**
  - `/props` reported `model_path=/models/Qwen3VL-8B-Instruct-Q4_K_M.gguf`, `modalities.vision=true` and `total_slots=1`.
  - `/v1/models` reported `ftype "Q4_K - Medium"`, `n_params 8,190,735,360` and `n_ctx 8192`.
  - Every response's `model` field was `qwen3-vl-8b-instruct-q4_k_m`: in 60/60 probes and in 17/17 stage-1 decisions (`served_model`).

### Smoke gates

| Gate | Result |
|---|---|
| VRAM gate before start (Isaac not running) | free 23,922 MiB ≥ required 14,336 → **GATE OK** |
| Multi-image A: colours of two images, both orders | red→blue and blue→red both named in send order → **PASS** (1,551 prompt tokens; the 640×480 tile adds about 290 over the frame alone) |
| Multi-image B: recorded tile-on v2 prompt (`apparatus_smoke/annot_r1`, frame + zoom tile) | answer parsed as a valid decision by `parse_decision_text` → **PASS** |
| Pre-joint co-residency (server up, Isaac about to start) | free 16,284 MiB ≥ Isaac reserve 3,072 + margin 2,048 → **OK** |
| Container preflight (`vgu_ros`, `--two-images`) | `{"ok": true, "images": 2}`, served model as pinned |

One quirk: with a single grey image, Qwen answered `"images": 0` to the count question. It answered 2 when shown two images. The colour gate shows the images do reach the model.

### VRAM and throughput

| Measure | Value |
|---|---|
| Idle server (weights + mmproj + KV at -c 8192) | 7,725 MiB |
| Peak during the probe battery (server alone) | 7,809 MiB |
| Peak during episodes (Isaac + server) | 10,085 MiB (s42) / 9,960 MiB (s43); minimum free 14,008 MiB |
| GPU utilisation during episodes | mean 33% (s42) / 27% (s43); peak 100% |
| Probe-size calls (about 1,310 prompt tokens, server alone, n=66) | prefill about 930 tok/s; generation 56 tok/s; median wall time 1.5 s; battery 60 items in 167.5 s |
| Episode-size calls with Isaac co-resident (about 2,970 prompt tokens, n=17) | prefill about 1,110 tok/s; generation 26.5–30.6 tok/s (median about 27.5); about 11 s wall for about 230 output tokens |
| Matched control without Isaac: multi-image Gate B (3,333 prompt tokens, 230 output tokens, n=1) | prefill 2.29 s; generation 47.8 tok/s; 7.1 s server time (9.4 s wall through the tunnel) |
| M5 stage-1 latency (17 decisions) | median 11.9 s, max 12.6 s |

**Isaac co-residency slows generation by about 40%.** For calls of matched size, generation fell from 47.8 tok/s (Gate B, no Isaac, n=1) to about 27.5 tok/s with Isaac running. Prefill was barely affected. The 56 tok/s figure from the probe-size calls is not comparable: those calls generate only about 7 tokens on a shorter context.

Qwen's JSON answers run about 230 tokens, so a stage-1 call takes about 12 s under co-residency. gpt-5.1's median was 4.0 s.

### Model files left on the VM

The files are cached at `/home/ubuntu/models/qwen3vl/`: **5.8 GB** (Q4_K_M 5.03 GB + mmproj 1.16 GB). llama-server is stopped and its container removed. The server image was removed too (`docker rmi`), so the VM's image list is back to `ros:jazzy`. `qwen_serve.sh start` re-pulls the pinned digest.

---

## Probe Battery v1: Accuracy Against the Baselines

Every run used the same frozen inputs:

- manifest `manifest_v1.json`, sha256 `9659782d…`;
- prompt version 1;
- one `analyze` call per item and temperature 0.

**Topology and order.**

- **Qwen's battery ran on the Mac**, through an SSH tunnel from local 127.0.0.1:8080 to the VM's 127.0.0.1:8080, against the VM's llama-server with no Isaac running. The frames live in the main checkout and passed the hash check there (`run_battery` checks every item). The 167.5 s wall time includes the network round trip.
- **gpt-5.1's battery also ran on the Mac**, against the OpenAI API, with ≥ 3 s pacing.
- **Deviation from the brief's order.** The brief ordered qwen, then sonnet, then gpt-5.1. The gpt-5.1 battery actually ran while the two Qwen episodes were still going on the VM: after Qwen's smoke gates and probe battery had passed, but before the Qwen arm finished. The two processes were independent (Mac against OpenAI, versus VM M5 against the local server), so nothing was shared. The gpt-5.1 head-on episode ran after both Qwen episodes, as ordered.

Wilson 95% intervals are shown. ER-2 and gpt-4o are the 2026-10-04 baseline runs (`docs/reports/2026-10-04-capability-probe-results.md`).

| Backend (served model) | Overall | locate_robot | left_right | robot_count | nearest_first | Refusals |
|---|---|---|---|---|---|---|
| Gemini ER-2 (`gemini-robotics-er-2-preview`) | 60/60 [0.940, 1.000] | 15/15 | 15/15 | 15/15 | 15/15 | 0/60 |
| gpt-4o (`gpt-4o-2024-08-06`) | 58/60 [0.886, 0.991] | 15/15 | 13/15 | 15/15 | 15/15 | 0/60 |
| **Qwen3-VL-8B Q4_K_M** (`qwen3-vl-8b-instruct-q4_k_m`) | **57/60** [0.863, 0.983] | 15/15 | 14/15 | 15/15 | **13/15** | 0/60 |
| **gpt-5.1** (`gpt-5.1-2025-11-13`, effort none) | **54/60** [0.799, 0.953] | 15/15 | 13/15 | **11/15** | 15/15 | 0/60 |

All four intervals overlap. At n=15 per type the battery still cannot rank the backends. The descriptive differences:

- **left_right.** `left_right_004` (correct B, "left") was missed by gpt-4o, Qwen and gpt-5.1, and each chose the first-listed letter A. `left_right_009` was missed by gpt-4o and gpt-5.1, again choosing A. This is the same first-listed profile the 2026-10-04 report found for gpt-4o.
- **robot_count (gpt-5.1 only).** By true count: 5/5 at 2 robots, 4/5 at 3, 2/5 at 4. The misses were off by one in both directions (4→3, 4→5, 3→4, 4→5), and every one chose letter A.
- **nearest_first (Qwen only).** Two misses, both choosing the second-listed letter A. The chosen robot was robot_3 or robot_2, so neither the robot_1 prior nor a first-slot prior explains them.
- **Letter-A responses.** All 6 gpt-5.1 misses answered "A"; this is a descriptive observation at n=6.
- **Token footprint.** Qwen used about 1,310 prompt tokens per probe and gpt-5.1 765 (45,901 / 60).

Runs (gitignored): `data/logs/capability_probes/llama_server_qwen3vl_20261006T105737Z/` and `data/logs/capability_probes/openai_gpt51_20261006T110426Z/`. Each holds the per-item JSONL, a summary with `reasoner_config_effective` and served-model counts, and the runner's stdout and stderr.

---

## Head-On Episodes

### Apparatus

- **Cell and config.** Cell `head_on_asymmetric_w0p2_eopen_bshort_o0` with the verbatim pilot's head-on overlay **verbatim**: `ho_orchestrator.yaml`, md5 `b571636a…`.
  - Goals (2.6, 0) and (−1.5, 0), gate `swap`, `prompt_robot_order: random`, obstacles on (`MODALITY=on`), arrival check, shadow on, debug and raw frames, and `plan_channel_enabled: true`.
  - Derived grounding with stage 2 on. `RECORD=0`, `REC_SEC` 1000, `SIM_SEC` 1200. Scenario `duration_sec` 300 governs.
- **Tree.** The VM ran `565fac3`: the branch delta was shipped over the VM's `b5cafe4` tree. Prompt v3.3; the list-order line was present in 22/22 stage-1 prompts.
- **Driver.** `_vm_driver/mw_run.sh` and `mw_chain.sh`, derived from the verbatim pilot's `vp_run.sh` and `vp_chain.sh`. Every standing gate is kept:
  - the pristine-config refusal before the overlay;
  - `pgrep -f run_simulation` empty before launch (0 s waits);
  - `GATE OK` from the `logs saved to` line, plus `M5_STARTED` (session line and analysis count);
  - `RESTORE OK` with source and installed md5s, after every run;
  - GT moved per run.
- **Driver additions:**
  - a 2 s `nvidia-smi` sampler (`vram.csv`);
  - a llama-server `/health` refusal for the Qwen arm;
  - the server log captured per run;
  - a `connection_errors` count, which was 0 in every run.

All three runs passed every gate. Isaac never outlived a run: each chain's settle step was clear after 10 s, so no PID kill was needed.

### Plan-metrics rows against the verbatim-pilot head-on rows

Scorers:

- plan metrics from the project's own `score_plan_decision`, via `_analysis/plan_table.py`. This is the pilot's script extended with v3.3, refusal-category and effective-block fields.
- outcomes from `coverage_scene_scores.py flow`.

"yld" means the yielder named before repair matches `correct_yielder` robot_2.

| Episode | Tree / prompt | Order | Trigger decision | Trigger provenance (edits) | yld | Emitted / consistent (all dispatched plans) | Outcome (arrivals) | Delay sum (s) | Dissolution (s) | Analyses / dispatches |
|---|---|---|---|---|---|---|---|---|---|---|
| **Qwen s42** (`mw01`) | 565fac3 / v3.3 | id_desc | `yield` r2, plan `null` | m3_default (absent), 0 | ✓ | 0/12 / — | **clogged** (1/2) | ≥ 320.6 (lower bound) | 69.8 | 12 / 12 |
| **Qwen s43** (`mw02`) | 565fac3 / v3.3 | id_asc | `yield` r2, plan `null` | m3_default (absent), 0 | ✓ | 0/3 / — | intermittent (2/2) | 183.6 | 70.0 | 5 / 3 |
| **gpt-5.1 s42** (`mw03`) | 565fac3 / v3.3 | id_desc | `yield` r2; [r2:yield, r1:cross] | **vlm_verbatim**, 0 | ✓ | 1/1 / 1/1 | **resolved** (2/2) | **143.8** | 66.4 | 5 / 1 |
| ER-2 s42 (`vp01`) | a8fc1bc / v3.2 | id_desc | `yield` r1; [r1:yield, r2:cross] | repaired, 1 (swap) | ✗ | 1/1 / 1/1 | resolved (2/2) | 149.8 | 69.1 | 5 / 1 |
| ER-2 s43 (`vp02`) | a8fc1bc / v3.2 | id_asc | `yield` r2; [r1:cross, r2:yield] | repaired, 1 (reorder) | ✓ | 1/1 / 1/1 | resolved (2/2) | 148.9 | 66.2 | 5 / 1 |
| ER-2 s44 (`vp03`) | a8fc1bc / v3.2 | id_asc | `yield` r2; [r2:yield, r1:cross] | vlm_verbatim, 0 | ✓ | 1/1 / 1/1 | resolved (2/2) | 147.4 | 67.6 | 3 / 1 |
| gpt-4o s42 (`vp04`) | a8fc1bc / v3.2 | id_desc | `yield` r1; [r1:yield, r2:cross] | repaired, 1 (swap) | ✗ | 2/2 / 2/2 | intermittent (2/2) | 153.3 | 68.1 | 2 / 2 |
| gpt-4o s43 (`vp05`) | a8fc1bc / v3.2 | id_asc | `yield` r1; [r1:yield, r2:cross] | repaired, 1 (swap) | ✗ | 1/1 / 1/1 | resolved (2/2) | 147.9 | 68.9 | 5 / 1 |

Per-arm reading (descriptive; n is 1–2 per arm):

- **Qwen3-VL-8B.**
  - The trigger strategy and yielder were right in both seeds, so M3 grounded the correct `yield` robot_2 with no swap-gate re-grounding.
  - Qwen never filled `proposed_plan`. The v3.3 prompt says that omitting it "lets the system derive the resolution", and Qwen took that option every time.
  - **s42 failure mode.** robot_2 completed its yield, then stalled at about (1.14, 0.14), 2.64 m from its goal, from sim 120 s to the end. Each stall trigger got another `temporary_wait` (11 in a row, all `completed`). This is the trap-3 shape, a repeated verdict, but produced by the model instead of a frozen mock.
  - **s43.** Two post-resolution abstentions and one more `temporary_wait`. robot_2 arrived at 149.2 s.
- **gpt-5.1.**
  - Verbatim, consistent and correct at the trigger.
  - Four post-resolution re-checks answered `congestion_detected=false`.
  - Under `id_desc`, robot_2 is listed first. gpt-5.1 named it, while gpt-4o named robot_1 under the same order (`vp04`). This is one episode, so no prior claim is made.

### IB10-style criteria per episode

| Criterion | Qwen s42 | Qwen s43 | gpt-5.1 s42 |
|---|---|---|---|
| Jam forms first (trigger snapshot: both robots `STOPPED`) | PASS (t = 26.9) | PASS (t = 27.9) | PASS (t = 26.9) |
| Resolution sequence executes (trigger command `completed`, stage 2 answered) | PASS (yield → letter B) | PASS | PASS (letter A) |
| Provenance correct (artifact provenance matches emission; `dispatch_matches_plan`) | PASS (`m3_default`/absent, dm ✓) | PASS (same) | PASS (`vlm_verbatim`, dm ✓) |
| Deploy check (no grounding degradations; effective block names the arm, pinned model, temperature 0, and the served model matches) | PASS | PASS | PASS (`reasoning_effort: none` recorded) |
| 2/2 arrivals at the ArrivalGate (`arrived at base goal`; 0 rejections) | **FAIL** (robot_1 only) | PASS | PASS |

### Comparability

- **The prompt and tree changed between the arms.** The pilot rows ran v3.2 on `a8fc1bc`; these ran v3.3 on `b5cafe4` plus the wiring delta. v3.3 adds the list-order line and a junction_clear gloss, which head-on never uses.
  - In the pilot, list order drove one of the four head-on repairs (`vp02`, a reorder).
  - gpt-5.1's verbatim plan listed yield before cross, the order the v3.3 line now states. It cannot be credited to the model alone.
  - Qwen's rows are unaffected, because it emitted no plans.
- **The outcome metrics are comparable.** Overlay, cell, goals, gate and scorer are identical.
- **Pilot status.** Every episode here is a pilot or validation episode, excluded from confirmatory counts, as the verbatim pilot's were.

---

## Refusal Accounting

| Arm | Stage-1 calls / attempts | Refused attempts | Terminal refusals | Grey-image fallbacks | Stage-2 answered / refused | Probe refusals |
|---|---|---|---|---|---|---|
| Qwen3-VL-8B | 17 / 17 | 0 | 0 | 0 (mitigation off) | 2 / 0 | 0/60 |
| gpt-5.1 | 5 / 5 | 0 | 0 | 0 (armed after attempt 2) | 1 / 0 | 0/60 |
| Reference: gpt-4o, verbatim pilot head-on plus IB10 | 20 / 21 | 1 | 0 | 0 | 4 / 0 | 0/60 |

- **gpt-5.1's refusal profile.** It shows 0 refusals in 65 calls, counting probes and stage 1. On the probe battery, gpt-4o also had 0/60, so the pilot's open question is only partly answered.
  - The refusal-relevant stimulus is the live annotated frame. Here, 5 of 5 live frames got answers, against gpt-4o's history of 19–38% first-attempt refusals.
  - That history is a different, larger sample, so this is suggestive only.
- **gpt-5.1 at chance?** On probes, no (54/60). On head-on, it named the correct yielder, while gpt-4o named robot_1 in both pilot episodes.
- **Abstentions.** Qwen 2 (s43), gpt-5.1 4. All were post-resolution re-checks.

---

## Cost Actuals

| Item | Tokens (in / out) | USD |
|---|---|---|
| gpt-5.1 preflights (local + container) | 1,370 / 40 | 0.002 |
| gpt-5.1 `max_tokens` check (HTTP 400, not billed) | — | 0 |
| gpt-5.1 probe battery (60) | 45,901 / 889 | 0.066 |
| gpt-5.1 episode, stage 1 (5 calls) | 11,818 / 1,204 | 0.027 |
| gpt-5.1 episode, stage 2 (1 call; tokens not logged; estimated) | about 1,300 / 300 | about 0.005 |
| Qwen (local) | — | 0 |
| **Total** | | **about $0.10** of the $10 hard stop |

Rates: gpt-5.1 $1.25 / $10 per MTok, from `research_notes/VLM model landscape 2026/wiring_practicalities.md`.

VM time ran 10:26–12:05 UTC (about 1 h 40 min), including the 11 min model download.

---

## VM State After the Work

- **Source tree:** restored. The 16 delta files were restored to their pre-deploy copies, or removed if new, with fresh mtimes.
  - `RESTORE MD5 MATCH PREDEPLOY`.
  - The full 739-file source manifest is identical to the layer-2-off pilot's post-deploy (`b5cafe4`) manifest.
- **Installed tree:**
  - `swarm_orchestrator` was purge-rebuilt.
  - The installed-vs-source check passed 126/126, with 519 installed files.
  - The `.pyc` body check passed 49/49.
  - `orchestrator.yaml` is `1f656533…` in source and installed; `rag.yaml` is `e18c723c…`.
- **Processes:** `pgrep` for Isaac, `fc_launch`, `run_simulation` and llama-server returns nothing. The only `pgrep` match was the SSH command line itself (trap 5); a `ps` count gives 0.
- **GPU:** 0% / 171 MiB.
- **Docker:** `vgu_ros` only, and the image list is `ros:jazzy` only.
- **Instance:** left RUNNING as found.
- **Left on disk:** `/home/ubuntu/models/qwen3vl/` (5.8 GB, the pinned GGUFs) and `/home/ubuntu/model_wiring/` (the driver, chain logs and per-run directories).

---

## Artifacts

In the main checkout (gitignored):

- `data/logs/vm_runs/model_wiring/runs/mw0{1,2,3}_*/`: each run's GT, every node log, decision artifacts, `m5_scene.jsonl`, frames, the overlay as installed, the 150 s sidecar, `vram.csv`, `llama_server.log` for Qwen, and the `CONDITION`, `GATE`, `M5_STARTED` and `RESTORE` files.
- `data/logs/vm_runs/model_wiring/_vm_driver/`:
  - the drivers: `mw_deploy.sh`, `mw_run.sh`, `mw_chain.sh`, `mw_instcheck.sh`, `pyc_check_all.py`, `qwen_multi_image_smoke.py`;
  - the pre-deploy, post-deploy and post-restore manifests;
  - the chain logs, `llama_server_full.log`, `fetch.log`, `start1.log`, and the VRAM samples from the probe battery.
- `data/logs/vm_runs/model_wiring/preflight/`: every preflight transcript, the multi-image smoke JSON, and the container key check.
- `data/logs/vm_runs/model_wiring/_analysis/`: per-run `*_plans.json` and `*_flow.json`, plus `plan_table.py`.
- `data/logs/capability_probes/{llama_server_qwen3vl_20261006T105737Z, openai_gpt51_20261006T110426Z}/`.

No key appears in any artifact: keys are read from the environment by the adapters and never printed. A scan of the run bundle and both probe directories for API-key patterns (`sk-…`, `sk-ant-…`, `AIza…`) found no matches.
