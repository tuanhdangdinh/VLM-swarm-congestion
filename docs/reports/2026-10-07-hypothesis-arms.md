# Hypothesis Arms: gemini-3.8-flash (H1), Molmo2-ER (H2) and glm-5.3-flash

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: H1/H2 reading rule registered before any battery call (results pending).
- Rev 2: results for the two ruled arms and the scope-extension GLM arm; nine-arm table; H1/H2 verdicts.

---

## Summary

The contract is the main checkout's `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`:

- the "WIRE-NEXT (user 2026-10-06)" ruling inside the v3.4 block;
- the "Model-wiring ruling" validation standard (preflight, probe battery v1, two head-on episodes, seeds 42/43), extended by the brief to battery v2 main;
- the "Prompt-style invariance ruling": one semantic template (v3.4); transport is per adapter, from provider docs fetched for this round;
- for GLM, the "Roster closure + confirmatory-tier ruling (2026-10-07)" (scope extension from the coordinator).

Branch `feat/v2-hypothesis-arms`, cut from `feat/prereg-v2-composite` at `b092f87`.

**The two hypotheses:**

- **H1, lab-controlled specialization.** gemini-3.8-flash vs ER-2: same lab, adapter, packing and thinking dose (`low`); robotics tuning varies.
- **H2, cross-lab specialist replication.** Molmo2-ER vs ER-2: embodied specialization held; lab varies (Ai2 vs Google).

**Verdicts, by the rule registered before any battery call (`59cc784`):**

- **H1: NOT SUPPORTED.** gemini-3.8-flash scored **20/20** on conflict_prediction [0.84, 1.00], against ER-2's 16/20.
  - GT-yes 10/10, GT-no 10/10, "yes" rate 10/20, so the profile is not degenerate.
  - Exact McNemar against ER-2: 4 discordant items, all in flash's favour, p = 0.125.
  - ER-2's conflict_prediction lead does not survive against its own lab's generalist. Flash posts the best score any arm has recorded, so the dynamics advantage is not attributable to robotics tuning within Google.
  - Confound: flash is a newer generation (Sep 2026, stable) than the ER-2 preview, and ER-2's base is undocumented. The contrast is lab-matched, not base-matched.
- **H2: NOT REPLICATED.** Molmo2-ER scored **9/20** [0.26, 0.66] on conflict_prediction, against ER-2's 16/20.
  - Exact McNemar: 7 discordant items, all in ER-2's favour, p = 0.016.
  - **Degenerate profile:** "yes" on 19/20 items, GT-no 0/10. This trips the registered always-yes check, so the 9/20 is a response bias and not a dynamics reading.
  - It answered "yes" on both letters A and B, so it is a content bias, not a letter bias.
  - A second embodied specialist does not reproduce ER-2's profile.
  - Confound: 4.85B local bf16 against a hosted frontier preview, so scale and serving are confounded with lab.

**Other headlines:**

- **Probe battery v1:** flash 60/60, GLM 58/60, Molmo2-ER **49/60** [0.70, 0.89].
  - Molmo2-ER is the first arm whose CI excludes the ER-2/Sonnet/DeepSeek ceiling.
  - It undercounts: robot_count 12/15, all 3 misses at true count 3 answered 2. locate_robot is 12/15.
- **Head-on, all six episodes resolved 2/2 with 0 refusals.** Delay sums were 147.0–157.0 s, inside or near the 143.8–153.3 s band of earlier arms.
  - **Flash:** verbatim plans with the correct yielder in both seeds. **Stage 2 timed out in both** (the 8 s `stage2_timeout_sec`, 2 attempts each), so M3's default letter was used.
    - Diagnostic replay: flash spends about 1,960 thought tokens (about 28 s) on the stage-2 prompt even at `thinking_level: low`. ER-2 spends 450–620 tokens (about 9 s). This accounts for most of flash's +7 s delay.
  - **Molmo2-ER:** correct yielder in both seeds, but `proposed_plan: null` both times (m3_default, absent).
    - Qwen3-VL had the same 0/15 emission. Both Qwen-backbone arms never emit plans, while all three Google/Zhipu arms do. This is the Group-B quasi-family signal the roster ruling anticipated.
  - **GLM:** s42 was verbatim and correct under `id_asc`. s43 named robot_1 under `id_desc`, and the swap gate repaired it.
- **VRAM:** Molmo2-ER is **not** "well under the Qwen 8B footprint", contrary to the brief's expectation.
  - Its shards are fp32 (19.4 GB); bf16 weights take 9.11 GiB, against Qwen Q4_K_M's whole 7.7 GB server.
  - The vLLM server holds 14,323 MiB at util 0.60, rising to about 15.2 GB after first use.
  - Isaac plus vLLM peaked at **17,425 MiB**, with a minimum of **6,668 MiB** free. The gate held.
- **Spend:** about **$0.36** in total, against the $10 hard stop.
  - flash: about $0.32, including an estimate for the 4 timed-out stage-2 calls;
  - GLM: about $0.04;
  - Molmo2-ER: $0 (local).
- **Suite:** 63 failed / 5,246 passed / 153 skipped / 3 errors, against 63 / 5,216 / 153 / 3 at `b092f87` (same flags, `--continue-on-collection-errors`).
  - The sorted failed and error node IDs are identical (66 = 66, `diff` empty).
  - The +30 passes are the new tests.

**STOP items for the owner:**

1. **GLM thinking cannot be disabled (deviation from the ruled "thinking DISABLED").**
   - `thinking.type: "disabled"` and `reasoning_effort: "none"` both return HTTP 400, code 1210: "This model always engages in thinking and cannot be disabled; please use low, high, or max". This was verified live on 2026-10-07, and docs.z.ai says the same.
   - The arm runs the lowest documented dose, `reasoning_effort: low`, with an output cap raised to 16,384 so the cap cannot be hit (the DeepSeek trap).
   - Measured reasoning tokens: at most 103 on probes and at most 146 on episodes. The cap was never approached.
   - Whether a forced-thinking arm is admissible under the frozen dose rule is the owner's call.
2. **Flash stage-2 latency exceeds the registered 8 s stage-2 timeout,** 2/2 episodes, both attempts.
   - Stage 2 then defaults to M3's rank-0 letter, so the arm's stage-2 decisions are never its own.
   - The fix options are owner decisions, recorded as facts only: the timeout, flash's thinking level, or accepting the defaults.
   - Flash's stage-2 thought use, about 1,960 tokens, also sits close to the adapter's 2,048 `max_output_tokens`. That is a cap-proximity watch item for flash.
3. **Molmo2-ER multi-image smoke: FAIL as registered**, so `multi_image` stays off.
   - Gate A, the colour order, answered "royal blue / crimson" for blue→red. The order is semantically correct, but the precedent's literal substring test fails on "crimson".
   - Gate B (the recorded v2 tile-on prompt) failed to parse: it answered `key: value` lines after free text in response to the v2 `<think>`-format prompt.
   - The v3.4 sanity replay was separately 3/3 valid JSON.
   - Head-on and probes are single-image, so validation is unaffected. A zoom-tile apparatus run on this arm would need the gate re-run under v3.4.
4. **The GGUF/llama.cpp fallback was not needed.** vLLM 0.31.0 served the model on the first attempt.
   - For the record, no GGUF of Molmo2-ER exists on Hugging Face, official or community: a search on 2026-10-07 returned only `allenai/Molmo2-ER`, and allenai's GGUF repos are OLMo/OLMoE only. Had vLLM failed, the fallback branch would have been a STOP.

---

## Registered Reading Rule

Written 2026-10-06T16:45Z, before any probe-battery call on either new arm (only the gemini-3.8-flash preflight had run). Nothing below may be tuned to the data.

**The two hypotheses:**

- **H1, lab-controlled specialization.** gemini-3.8-flash versus Gemini Robotics-ER 2. The lab (Google), the adapter and the packing are held, and so is the thinking dose (`thinking_level: low` on both). What varies is robotics tuning. Question: does ER-2's conflict_prediction lead survive against its own lab's generalist?
- **H2, cross-lab specialist replication.** Molmo2-ER versus ER-2. Embodied specialization is held, and the lab varies (Ai2 versus Google). Question: does a second embodied specialist replicate ER-2's conflict_prediction profile?

**Anchor measure.** Battery v2 main `conflict_prediction`: the same 20 frozen items (`manifest_v2.json`, sha256 `faf1953b…`), the frozen v1 probe template, one call per item.

**Statistics, per arm against ER-2's 2026-10-04 run:**

- accuracy with Wilson 95% CI;
- the GT-yes / GT-no split and the "yes" rate;
- an exact two-sided McNemar test on the per-item discordant pairs.

**Reading of the lead.** ER-2 scored 16/20 [0.58, 0.92]. Its "lead" is a lead over gpt-4o only (9/20, at chance). It ties or trails Sonnet (16), gpt-5.1 (15), Qwen (15) and DeepSeek (19) on overlapping CIs. So:

- **H1 verdict rule:**
  - flash ≤ 10/20, or its Wilson upper bound < 0.66 → **H1 SUPPORTED**: the dynamics advantage tracks robotics tuning within the lab.
  - flash ≥ 14/20 with a McNemar p ≥ 0.05 against ER-2 → **H1 NOT SUPPORTED**: the lab's generalist lands with ER-2, so the "lead" is a lab/generation property, not specialization.
  - Anything else (11–13/20, or ≥ 14 but significantly different) → **INCONCLUSIVE at n = 20**, reported with the split and yes-rate.
- **H2 verdict rule:**
  - Molmo2-ER ≥ 14/20 with McNemar p ≥ 0.05 against ER-2 → **H2 REPLICATED**: a second specialist lands with ER-2.
  - Molmo2-ER ≤ 10/20, or its Wilson upper bound < 0.66 → **H2 NOT REPLICATED**.
  - Otherwise → **INCONCLUSIVE at n = 20**.
- **Profile check, both arms.** A score reached by always-yes or never-yes (yes-rate ≥ 18/20 or ≤ 2/20) is reported as a degenerate profile, whatever the verdict rule says.

**Secondary evidence, not used for the verdicts:**

- probe battery v1 (60, at ceiling and unable to rank backends);
- motion_direction (arrow-confounded);
- temporal_order (QUARANTINED);
- the head-on plan metrics.

The new arms' head-on episodes run prompt v3.4. Every earlier arm's episodes ran v3.2 or v3.3, so any head-on comparison is confounded by prompt version.

**Structural confounds, stated up front:**

- **H1 is lab-matched, not base-matched.** ER-2's base model is undocumented, so flash and ER-2 may differ in generation and size as well as in tuning.
- **H2 confounds scale and serving with lab.** Molmo2-ER is a 4.85B open model served locally in bf16; ER-2 is a hosted frontier-scale preview.

---

## Wiring

Commits on `feat/v2-hypothesis-arms`:

| Commit | Change |
|---|---|
| `068819d` | `gemini_flash` and `llama_server_molmo2er` sections; `system_placement: user_prefix` for llama_server; gemini and key-less listings in `preflight_backend.py`; tests |
| `6500cd3` | `scripts/vm/molmo_serve.sh` (pinned vLLM serving) |
| `59cc784` | The registered H1/H2 reading rule (this report's first draft) |
| `18ddb4b` | `zhipu_glm` section; `reasoning_tokens` in OpenAI-compatible usage; tests |

Every pinned section is unchanged; `test_existing_pinned_sections_are_unchanged` passes unedited.

| Section | Adapter | Model id (live-listed) | Request controls | Reasoner |
|---|---|---|---|---|
| `gemini_flash` | gemini (Interactions API) | `gemini-3.8-flash` (GET `/v1beta/models`, 2026-10-06) | `thinking_level: low` (= ER-2); no sampling sent (`unsupported_sampling` recorded) | temperature 0.0 (recorded only); 4 attempts; grey fallback after 2 |
| `llama_server_molmo2er` | llama_server (vLLM, OpenAI-compatible) | `molmo2-er` (`--served-model-name`; vLLM `/v1/models`) | `system_placement: user_prefix`; `multi_image` off | temperature 0.0; shared 2 attempts, no fallback (local-arm precedent: Qwen) |
| `zhipu_glm` | openai | `glm-5.3-flash` (api.z.ai GET `/models`, 2026-10-07; also listed on open.bigmodel.cn) | `thinking: {"type": "enabled"}`, `reasoning_effort: low` (forced thinking, see STOP 1) | temperature 0.0; `max_tokens` 16,384; 4 attempts; grey fallback after 2 |

### Per-Adapter Transport (Prompt-Style Invariance Ruling)

Provider docs were fetched as raw HTML/Markdown on 2026-10-06/07, and the excerpts are kept in `data/logs/vm_runs/hypothesis_arms/preflight/provider_docs_20261006/`. The audit rule from the v3.4 report applies: a change needs an explicit provider recommendation, and examples alone do not count.

| Arm | Image vs text | Preamble | JSON | Sampling / thinking | Docs evidence and verdict |
|---|---|---|---|---|---|
| gemini-3.8-flash | text → image | `system_instruction` | prompt only | none sent; `thinking_level: low` | image-understanding guide: "When using a single image with text, place the text prompt before the image". The latest-model guide (3.8 Flash migration): "Strip temperature, top_p, and top_k from generation configs … Note that minimal is not supported on 3.8 Flash". The Interactions API `generation_config` reference has no temperature field. **Same packing as ER-2; no change** |
| Molmo2-ER | image → text | **user_prefix** (system text + blank line + user text, in one user turn) | prompt only | temperature 0.0 | `chat_template.jinja` at revision `dab22564…` raises "Conversation roles must alternate user/assistant/…" on a leading system role. **Gate S verified it live: a system-role request returned HTTP 400; the user_prefix request answered.** The template also emits every `<|image|>` before the text, whatever the content order. The model card's example decodes greedily. **New transport value, recorded as `system_placement: "user_prefix"`** |
| glm-5.3-flash | text → image | `system` message | prompt only (`json_object` is documented but not sent) | `thinking` enabled, `reasoning_effort: low`, temperature 0.0 (documented range [0, 1]) | The chat-completion reference's only image example is image-first, with no stated preference, so it is **not applied** (audit rule). The image_url schema lists `url` only; `detail: "high"` is accepted live with identical prompt_tokens with and without it. **Same packing as the other openai-adapter arms; no change** |

`PayloadFormat.system_placement` gains the value `user_prefix`, and `describe_payload_format` derives it from the config. The Qwen and Cosmos request bodies are byte-identical to the pre-change bodies, pinned by `test_existing_llama_server_bodies_are_byte_identical_to_the_pre_change_bodies`. All 9 wired arms are covered by `test_recorded_payload_format_matches_the_request_actually_sent`. Every arm stays at `payload_format.version: "v1"`, because no existing arm's packing moved; Molmo's is a new arm's first packing.

### Usage Recording

`OpenAIBackend._extract_usage` now adds `reasoning_tokens` when the provider reports `completion_tokens_details.reasoning_tokens`. The change is additive: it moves no request byte. It means the gpt-4o and gpt-5.1 artifacts will also carry the key (0 for gpt-4o). Without it, GLM's distance from the output cap would be invisible per call.

### Tests

`tests/unit/test_hypothesis_arms.py` has 24 tests, and `test_model_wiring.py`'s payload-format parametrization covers the 3 new arms. All HTTP is mocked. Ruff is clean on every changed file.

---

## Molmo2-ER Serving

`scripts/vm/molmo_serve.sh` (`fetch | verify | pull | gate | start | status | stop`) mirrors `qwen_serve.sh`:

- **Weights.** `allenai/Molmo2-ER` at revision `dab22564403d2607855bb1fffb0721285b445081`.
  - **All 22 read files are sha256-pinned**, not only the four LFS shards. `--trust-remote-code` executes the repo's `processing_molmo2.py`, `modeling_molmo2.py` and the related files, so they are pinned too.
  - Shards are fp32: 19,403,476,800 B for 4,850,869,200 params.
  - Verified after download and again before every start.
  - Served offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) from the verified directory, mounted read-only.
- **Server.** `vllm/vllm-openai:v0.31.0`, pulled by its **linux/amd64 manifest digest** `sha256:a4a4c043…`; the multi-arch index is `sha256:c1c9f6fd…`. The server reported `{"version":"0.31.0"}` and `Resolved architecture: Molmo2ForConditionalGeneration`, which is native since vLLM 0.15.0.
  - It is a container, not a venv: the host has no CUDA toolkit, the nvidia runtime is configured, and the driver is 595.84 / CUDA 13.2.
  - Flags: `--dtype bfloat16 --max-model-len 16384 --max-num-seqs 1 --gpu-memory-utilization 0.60 --limit-mm-per-prompt '{"image": 2, "video": 0}' --trust-remote-code`, host network, 127.0.0.1:8090.
- **Startup.** 200 s.
  - Model load: 9.11 GiB.
  - KV cache: 4.36 GiB, 31,728 tokens, so 1.94× concurrency at 16,384.
  - Peak activation: 0.53 GiB.
  - CUDA graphs: 0.02 GiB.
- **The VRAM gate** was registered in the script header before its first run:
  - need = 0.60 × total = 14,742 MiB, plus a 2,048 MiB margin, plus a 3,072 MiB Isaac reserve when Isaac is not running;
  - required 19,862 MiB, against 23,922 MiB free → **GATE OK**.

| VRAM measure | Value |
|---|---|
| Server idle after start | 14,323 MiB |
| Server after first requests (resident thereafter) | 15,209 MiB |
| Isaac + server, peak over 4 episodes | **17,425 MiB**; minimum free **6,668 MiB** |
| Stage-1 latency under Isaac (10 decisions) | 7.0–7.7 s (about 2.6k prompt and 150–180 output tokens) |

**Smoke gates** (`preflight/molmo_smoke.json`; the script is `_vm_driver/molmo_smoke.py`, copied from the Qwen gate plus a Gate S):

| Gate | Result |
|---|---|
| S: leading system role, raw | **HTTP 400** "Conversation roles must alternate user/assistant/user/assistant/..." |
| S: through the arm (`user_prefix`) | answered `{"ok": true}` |
| A: colours in send order, both orders | red→blue named "red / royal blue" (PASS). blue→red named "royal blue / crimson": the order is correct, but the registered substring test needs "red", so **FAIL as registered** |
| B: recorded v2 tile-on prompt (frame + zoom tile) | **FAIL**: free text plus `key: value` lines, no JSON, under the v2 `<think>`-format prompt |
| Container preflight (`vgu_ros`) | `PREFLIGHT OK`, `molmo2-er` served and listed |
| v3.4 sanity replay (3 stored decisions, single image) | **3/3 valid**: `deadlock`/`yield` robot_2 ×2, `none` on the re-check |

`multi_image` stays **off** (STOP item 3).

**Left on the VM:**

- the weights at `/home/ubuntu/models/molmo2er/` (**19 GB**, sha256-verified);
- the drivers at `/home/ubuntu/hypothesis_arms/`.

The vLLM container is stopped and removed. The image was removed with `docker rmi` (32.3 GB uncompressed), following the Qwen precedent; `molmo_serve.sh pull` re-pulls the pinned digest.

---

## Preflights

| Arm | Local | Container (`vgu_ros`) | Live listing |
|---|---|---|---|
| gemini-3.8-flash | OK (1 image and 2 images; served `gemini-3.8-flash`) | OK | listed among 62 ids |
| Molmo2-ER | Gate S plus the smoke gates, through an SSH tunnel | OK | `molmo2-er` (the only id) |
| glm-5.3-flash | OK (1 and 2 images; served `glm-5.3-flash`; `reasoning_tokens` 0) | OK, after the key was appended (below) | listed among 11 ids |

**Keys.**

- `ZHIPUAI_API_KEY` was absent from the VM's `/home/ubuntu/vgu-vlm-swarm/.env` (`/ws/.env`).
- I appended exactly that line from the local `.env` over SSH stdin. It was never echoed, and the file stays mode 600.
- Its presence was then checked inside `vgu_ros`.
- A scan of every artifact and report file for the four key values found 0 hits.

---

## Nine-Arm Comparison

All battery runs used the frozen inputs:

- v1: `manifest_v1.json` (`9659782d…`), 60 items;
- v2: `manifest_v2.json` (`faf1953b…`) `--subset main`, 59 items;
- prompt version 1, one call per item, temperature 0 where the API honours it.

Wilson 95% CIs. McNemar is exact two-sided on the 20 conflict_prediction items, paired with ER-2's 2026-10-04 run. Script: `data/logs/vm_runs/hypothesis_arms/_analysis/eight_arm_table.py`, which writes `eight_arm_table.json` (nine arms).

| | Gemini ER-2 | gpt-4o | Qwen3-VL-8B | gpt-5.1 | Sonnet 5.5 | DeepSeek Flash | **gemini-3.8-flash** | **Molmo2-ER** | **glm-5.3-flash** |
|---|---|---|---|---|---|---|---|---|---|
| Group | A, B | A, C | B | C, D | — | D | **B** | **B** | **D** |
| Lab | Google | OpenAI | Alibaba | OpenAI | Anthropic | DeepSeek | Google | Ai2 | Zhipu |
| Probes v1 (60) | 60 [0.94, 1.00] | 58 [0.89, 0.99] | 57 [0.86, 0.98] | 54 [0.80, 0.95] | 60 | 60 | **60** [0.94, 1.00] | **49** [0.70, 0.89] | **58** [0.89, 0.99] |
| — locate / left_right / count / nearest | 15/15/15/15 | 15/13/15/15 | 15/14/15/13 | 15/13/11/15 | 15/15/15/15 | 15/15/15/15 | 15/15/15/15 | 12/12/12/13 | 15/14/15/14 |
| v2 main (59) | 48 | 26 | 38 | 37 | 48 | 43 | **55** [0.84, 0.97] | **36** [0.48, 0.72] | **44** [0.62, 0.84] |
| v2 excl. temporal_order (40) | 36 | 25 | 32 | 31 | 36 | 34 | **40** [0.91, 1.00] | **21** [0.38, 0.67] | **33** [0.68, 0.91] |
| motion_direction (20) | 20 | 16 | 17 | 16 | 20 | 15 | **20** | **12** [0.39, 0.78] | **18** |
| **conflict_prediction (20)** | **16** [0.58, 0.92] | 9 [0.26, 0.66] | 15 [0.53, 0.89] | 15 [0.53, 0.89] | 16 [0.58, 0.92] | 19 [0.76, 0.99] | **20** [0.84, 1.00] | **9** [0.26, 0.66] | **15** [0.53, 0.89] |
| — GT-yes / GT-no | 10/10, 6/10 | 7/10, 2/10 | 5/10, 10/10 | 10/10, 5/10 | 10/10, 6/10 | 10/10, 9/10 | **10/10, 10/10** | **9/10, 0/10** | **10/10, 5/10** |
| — "yes" answers | 14/20 | 13/20 | 5/20 | 15/20 | 14/20 | 11/20 | **10/20** | **19/20 ⚠ degenerate** | **15/20** |
| — McNemar vs ER-2 (ER-2-only / arm-only, p) | — | 8/1, 0.039 | 5/4, 1.0 | 4/3, 1.0 | 1/1, 1.0 | 1/4, 0.38 | **0/4, 0.125** | **7/0, 0.016** | **2/1, 1.0** |
| temporal_order ⚠ quarantined (19; lower-id rule = 15) | 12 | 1 | 6 | 6 | 12 | 9 | 15 | 15 | 11 |
| Probe refusals / errors (v1 + v2) | 0 / 0 | 2 / 11 unparsed | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** | **0 / 0** | **0 / 1** (HTTP 500 "Internal network failure", a temporal_order item, scored wrong) |
| Head-on episodes | s42/s43/s44 (v3.2) | s42/s43 (v3.2) | s42/s43 (v3.3) | s42 (v3.3) | s42/s43 (v3.3) | s42 (v3.3) | **s42/s43 (v3.4)** | **s42/s43 (v3.4)** | **s42/s43 (v3.4)** |
| Plan emission (dispatched) | 3/3 | 3/3 | 0/15 | 1/1 | 2/2 | 1/1 | **2/2** | **0/2** | **2/2** |
| Trigger provenance (edits) | rep 1 / rep 1 / verb 0 | rep 1 / rep 1 | m3_default ×2 | verb 0 | rep 1 / verb 0 | rep 1 | **verb 0 ×2** | **m3_default (absent) ×2** | **verb 0 / rep 1 (swap)** |
| Correct yielder pre-repair | 2/3 | 0/2 | 2/2 | 1/1 | 1/2 | 0/1 | **2/2** | **2/2** | **1/2** |
| Outcome | resolved ×3 | intermittent, resolved | clogged, intermittent | resolved | resolved ×2 | resolved | **resolved ×2** | **resolved ×2** | **resolved ×2** |
| Delay sum (s) | 149.8 / 148.9 / 147.4 | 153.3 / 147.9 | ≥ 320.6 / 183.6 | 143.8 | 366.6 / 222.3 | 146.5 | **157.0 / 157.0** | **147.0 / 150.3** | **150.8 / 152.5** |
| Stage-2 (answered / degraded) | answered | answered | answered | answered | answered | answered | **0 / 2 (timeout)** | **2 / 0** | **2 / 0** |
| Stage-1 refused attempts | 0 | 1/21 | 0/17 | 0/5 | 91/96 (v3.3) | 0/5 | **0/9** | **0/10** | **0/9** |
| Cost actuals (this report's work) | — | — | $0 | — | — | — | **≈ $0.32** | **$0** | **≈ $0.04** |

Earlier rows are carried from `docs/reports/2026-10-06-roster-validation.md` and `docs/reports/2026-10-06-v34-repin.md`, re-scored from their per-item JSONL by the same script; every count reproduces. The Sonnet 17/20 conflict_prediction in the reasoning-dose pilot is a different run and is not used here.

### Groups Framing (Roster-Closure Ruling)

- **A, the v1-frozen pair (ER-2, gpt-4o).** Unchanged.
- **B, the specialization 2×2: {Google, Qwen-backbone} × {embodied-tuned, generalist}.**

  | | Embodied-tuned | Generalist |
  |---|---|---|
  | Google | ER-2: CP 16, yes 14/20 | gemini-3.8-flash: CP **20**, yes 10/20 |
  | Qwen backbone | Molmo2-ER: CP **9**, yes **19/20** | Qwen3-VL-8B: CP 15, yes 5/20 |

  - On conflict_prediction, **the generalist is at or above the specialist in both rows**: Google 20 vs 16, Qwen backbone 15 vs 9.
  - Embodied tuning does not buy dynamics accuracy on this battery in either family, and in the Qwen row the specialist shifts the response bias from never-yes to always-yes.
  - Plan emission splits by **backbone**, not by tuning: both Google arms emit verbatim plans; both Qwen-backbone arms never do (Molmo 0/2, Qwen 0/15).
  - Caveats: the quasi-family control is approximate. Molmo2 is Qwen3-4B with SigLIP2, not Qwen3-VL, and the scales differ: 4.85B bf16 against 8B Q4_K_M.
- **C, the generation pair (gpt-4o → gpt-5.1).** Unchanged.
- **D, the churn-risk pilots (gpt-5.1, deepseek-flash, glm-5.3-flash). ROLLING-PIN CAVEAT** on every row: the pins are undated aliases.
  - GLM served `glm-5.3-flash` on 118/119 probes (the 119th was the HTTP 500) and on every episode call. The analyses must condition on that string.
  - GLM's conflict profile (15/20, GT-no 5/10, "yes" 15/20) is gpt-5.1's false-alarm shape almost exactly.

---

## H1 and H2 Readings (Mechanical Application of the Registered Rule)

**H1 (gemini-3.8-flash vs ER-2).**

- The rule: "flash ≥ 14/20 with McNemar p ≥ 0.05 against ER-2 → H1 NOT SUPPORTED".
- Flash scored 20/20, with p = 0.125. **→ H1 NOT SUPPORTED.**
- The profile check passes (yes-rate 10/20).
- The descriptive direction is the reverse of H1: every discordant item is one flash got right and ER-2 got wrong (4 GT-no false alarms of ER-2's).
- **Reading.** ER-2's conflict_prediction lead was a lead over gpt-4o. It does not survive against Google's own current generalist. What separated ER-2 from gpt-4o is a property the lab's 2026-09 Flash also has, and robotics tuning is not needed for it.
- **Bounds.** n = 20; a generation confound (3.8 Flash, Sep 2026, against an ER-2 preview of undocumented base); one probe template.

**H2 (Molmo2-ER vs ER-2).**

- The rule: "Molmo2-ER ≤ 10/20, or its Wilson upper bound < 0.66 → H2 NOT REPLICATED".
- Molmo2-ER scored 9/20, with an upper bound of 0.658 and p = 0.016. **→ H2 NOT REPLICATED.**
- The profile check fires: 19/20 "yes" is a **degenerate always-yes profile**, so the 9/20 measures a response bias, not motion integration.
- **Reading.** A second, cross-lab embodied specialist does not reproduce ER-2's conflict_prediction profile, and it scores at gpt-4o's chance level.
- Its v1 primitives are also the weakest recorded: 49/60, with an undercounting failure mode. Its v2 motion_direction is 12/20 [0.39, 0.78], against ER-2's 20/20.
- **Bounds.** n = 20; scale (4.85B local) and serving (bf16 vLLM) are confounded with lab.

**Joint reading.** The two verdicts point the same way:

- On this battery, "embodied specialist" is not the variable that predicts dynamics reasoning.
- The two highest conflict_prediction scores are generalists: flash 20/20 and DeepSeek 19/20.
- The specialists split: ER-2 16/20, Molmo2-ER 9/20, degenerate.

This is a battery-level finding (one frozen template, n = 20 per type). It says nothing yet about crowded congestion-onset frames.

---

## Head-On Episodes

**Apparatus.** Identical to the model-wiring and roster rounds:

- cell `head_on_asymmetric_w0p2_eopen_bshort_o0`;
- overlay `ho_orchestrator.yaml`, **md5 `b571636a…` verbatim**: plan channel on, `prompt_robot_order: random`, gate `swap`, `MODALITY=on`;
- `RECORD=0`, `REC_SEC` 1000, `SIM_SEC` 1200.

**Prompt v3.4 was verified on every one of the 27 stage-1 artifacts:** the JSON-only sentence is present and there is no `<think>`. The effective blocks name each arm with its configured attempts, fallback and payload format, and the served model matches the pin on every call.

**Trees.**

- Episodes 1–4 ran `59cc784` = `b5cafe4` plus the 22-file delta. The VM's pre-deploy tree was md5-identical to `b5cafe4` for all 22 paths.
- `DEPLOY MD5 MATCH LOCAL`; installed-vs-source 126/126; `.pyc` 49/49.
- For GLM, the VM was restored to `b5cafe4`, then the `18ddb4b` delta was deployed the same way.

**Drivers.** `_vm_driver/ha_{deploy,run,chain,instcheck}.sh`, copied from the roster `rv_*.sh`. The run driver's health check for Molmo is `/v1/models` listing `molmo2-er`, because vLLM's `/health` returns an empty 200. Every standing gate is kept:

- the pristine-config refusal;
- `pgrep` empty before launch (0 s waits);
- `GATE OK` from the `logs saved to` line;
- `M5 STARTED`;
- `RESTORE OK` with source and installed md5s;
- GT moved per run;
- a chain abort on 429/quota.

All six runs passed every gate. Each settle was clear in 10 s, so no PID kill was needed. The vLLM server stayed resident through the flash and Molmo episodes and was stopped before the GLM episodes.

| Episode | Order | Trigger (sim s) | Trigger decision / plan | Provenance (edits) | yld | Stage 2 | Outcome (arrivals) | Delay sum (s) | Dissolution (s) | Analyses / dispatches |
|---|---|---|---|---|---|---|---|---|---|---|
| flash s42 (`ha01`) | id_desc | 27.1 | yield r2; [r2 yield, r1 cross] | vlm_verbatim 0 | ✓ | **degraded (timeout ×2) → default A** | resolved (2/2) | 157.0 | 72.1 | 4 / 1 |
| flash s43 (`ha02`) | id_desc | 27.2 | yield r2; [r2 yield, r1 cross] | vlm_verbatim 0 | ✓ | **degraded (timeout ×2) → default** | resolved (2/2) | 157.0 | 72.5 | 5 / 1 |
| Molmo2-ER s42 (`ha03`) | id_desc | 26.4 | yield r2; plan `null` | m3_default (absent) | ✓ | answered A | resolved (2/2) | 147.0 | 67.8 | 5 / 1 |
| Molmo2-ER s43 (`ha04`) | id_desc | 26.9 | yield r2; plan `null` | m3_default (absent) | ✓ | answered B | resolved (2/2) | 150.3 | 68.2 | 5 / 1 |
| GLM s42 (`ha05`) | **id_asc** | 25.8 | yield r2; [r2 yield, r1 cross] | vlm_verbatim 0 | ✓ | answered B | resolved (2/2) | 150.8 | 68.7 | 4 / 1 |
| GLM s43 (`ha06`) | id_desc | 25.8 | yield **r1**; [r1 yield, r2 cross] | repaired 1 (swap: robot_1 0.70 m < 1.08 m) | ✗ | answered A | resolved (2/2) | 152.5 | 70.8 | 4 / 1 |

Every post-resolution re-check answered `congestion_detected=false`, with no dispatch, with one exception. In GLM s42 one re-check (sim 97.0) was `parse_status: invalid` after its re-ask: `root_cause` was null, which fails the schema. No dispatch followed.

**Verbatim trigger reasoning:**

- **flash s42:** "Robots robot_1 and robot_2 are facing each other head-on within 0.22 m in a narrow corridor, resulting in a deadlock. One robot needs to yield or reverse to allow the other to pass through. robot_2 can yield backwards to the east where there is clear space, allowing robot_1 to proceed."
- **Molmo2-ER s42:** "Two robots are head-on and within ~0.5 m of each other, both stopped and facing each other in the same narrow aisle. This constitutes a deadlock situation." / "To resolve the deadlock, one robot should yield and back up while the other proceeds through the aisle."
- **Molmo2-ER s43** justification: "The robot named in yield_robot should back up and step aside while the others pass". This is close to the prompt's own strategy gloss.

**Flash stage-2 timeouts.** `stage2_timeout_sec` is 8.0 in the overlay, and stage-1 latencies were 3.8–9.6 s.

The diagnostic replay (`stage2_latency_diag/`; DIAGNOSTIC, outside every table) sent the two stored stage-2 prompts and marks images with a 60 s client timeout:

| Arm | Wall time | thought_tokens |
|---|---|---|
| flash | 28.4 s / 27.3 s | 1,963 / 1,962 |
| ER-2 | 9.6 s / 8.9 s | 621 / 453 |

Flash's stage-2 thinking is about 4× ER-2's at the same `low` level, and it sits close to the 2,048 `max_output_tokens` (STOP item 2). The timeouts explain most of flash's +7–10 s delay over the other resolved arms.

**Comparability.** Every earlier arm's episodes ran v3.2 or v3.3; these ran v3.4. Provenance and edit counts are not like-for-like across that boundary, while the outcome metrics are comparable (same overlay, cell, goals, gate and scorer). Every episode is a validation/pilot episode, excluded from confirmatory counts.

---

## Refusal Accounting

| Arm | Stage-1 decisions / attempts | Refused attempts | Grey fallback fired | Stage 2 answered / degraded | Probe refusals (v1 + v2) |
|---|---|---|---|---|---|
| gemini-3.8-flash | 9 / 9 | 0 | 0 (armed after attempt 2) | 0 / 2 (timeout) | 0/119 |
| Molmo2-ER | 10 / 10 | 0 | — (not configured) | 2 / 0 | 0/119 |
| glm-5.3-flash | 8 / 9 (1 parse re-ask) | 0 | 0 (armed after attempt 2) | 2 / 0 | 0/119 |

The v3.4 sanity replay (3 stored decisions per arm) was 9/9 valid, with 0 refused attempts. All three arms named robot_2 on both standoffs and `none` on the re-check.

**GLM output-cap evidence.** Reasoning tokens per call:

- probes: max 103, median 8 (64/119 nonzero);
- stage 1: max 146.

The largest completion was 382 tokens, against a 16,384 cap; even the shared 2,048 cap would never have been reached.

---

## Cost Actuals

Rates:

- gemini-3.8-flash: $0.75 / $3.75 per MTok, output including thinking, through 2026-12-31 (pricing page, fetched 2026-10-06);
- ER-2: $1 / $5;
- glm-5.3-flash: $0.15 / $0.50 (docs.z.ai pricing).

| Item | USD |
|---|---|
| flash preflights (3 local + 1 container) | < 0.01 |
| flash v3.4 sanity replay (3) | 0.008 |
| flash probes v1 + v2 (119; 141,307 in / 831 out + 29,180 thought) | 0.219 |
| flash episodes, stage 1 (9 calls, logged) | 0.027 |
| flash episodes, stage 2 (4 timed-out calls; billing unknown; estimated at the replay's 1,374 / 2,003) | ≤ 0.034 (est.) |
| stage-2 latency diagnostic (2 flash + 2 ER-2) | 0.026 |
| **flash subtotal** | **≈ 0.32** |
| GLM raw transport probe (4 calls, 2 HTTP 400), preflights | < 0.002 |
| GLM sanity replay (3) | 0.002 |
| GLM probes v1 + v2 (205,952 in / 2,938 out) | 0.032 |
| GLM episodes (stage 1 + stage 2, logged per attempt) | 0.006 |
| **GLM subtotal** | **≈ 0.04** |
| Molmo2-ER (local) | 0 |
| **Total** | **≈ $0.36** of the $10 hard stop |

VM time: 16:37–18:52 UTC (about 2 h 15 min). That covers the fetch and pull, 6 episodes, two deploys and two restores.

---

## VM State After the Work

- **Source tree:** restored to `b5cafe4`. `RESTORE MD5 MATCH PREDEPLOY`, and an independent check of all 22 delta paths against `git show b5cafe4:` matched. Files new in the delta were removed.
- **Installed tree:**
  - installed-vs-source 126/126;
  - `.pyc` 49/49;
  - `orchestrator.yaml` `1f656533…` in source and installed; `rag.yaml` `e18c723c…`.
- **Processes:** `ps` count 0 for `fc_launch`, `run_simulation`, `isaac.scripts`, `llama-server` and `vllm serve`. The GPU is at 171 MiB / 0%.
- **Docker:** `vgu_ros` only; images `ros:jazzy` only. The vLLM container and image were removed.
- **Left on disk:**
  - `/home/ubuntu/models/molmo2er/` (19 GB, pinned);
  - `/home/ubuntu/hypothesis_arms/` (drivers, chain logs, runs);
  - the `ZHIPUAI_API_KEY` line appended to `/ws/.env`;
  - `/home/ubuntu/models/qwen3vl/` (from the earlier round).
- **Instance:** left RUNNING as found. Disk free is 80 GB.

---

## Artifacts

In the main checkout (gitignored):

- `data/logs/capability_probes/hypothesis_arms_20261007/{gemini_flash,llama_server_molmo2er,zhipu_glm}__{v1,v2main}/`: per-item JSONL, summary, stdout and stderr.
- `data/logs/vm_runs/hypothesis_arms/runs/ha0{1..6}_*/`: each run's bundle (GT, node logs, decisions, `m5_scene.jsonl`, frames, overlay, sidecar, `vram.csv`, `vllm_server.log` for Molmo, and the `CONDITION`, `GATE`, `M5_STARTED` and `RESTORE` files).
- `data/logs/vm_runs/hypothesis_arms/_vm_driver/`: the drivers, deploy tars and md5 lists (deploy 1 and deploy 2), `molmo_smoke.py`, `vllm_startup_key_lines.txt`, and `vm_side/` (the chain logs, fetch/pull/start logs, and the full vLLM server log).
- `data/logs/vm_runs/hypothesis_arms/preflight/`: every preflight transcript, `molmo_smoke.json`, and `provider_docs_20261006/` (the Gemini, vLLM, Molmo2 and Z.ai docs fetched for the audit).
- `data/logs/vm_runs/hypothesis_arms/v34_sanity_replay/`: script, `results.jsonl`, run logs.
- `data/logs/vm_runs/hypothesis_arms/stage2_latency_diag/`: the diagnostic script and results.
- `data/logs/vm_runs/hypothesis_arms/_analysis/`: `eight_arm_table.{py,json}` (nine arms), `plan_table.py`, `pull_score.sh`, `*_plans.json`, `*_flow.json`.
