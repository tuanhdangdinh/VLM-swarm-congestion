# PILOT: Per-Arm Provider-Side Reasoning Dose on Battery-v2 conflict_prediction

**Prepared:** 2026-10-07

**Status:** PILOT. It is exploratory and EXCLUDED from all confirmatory counts. The registration is in the prereg-v2 design spec, "Reasoning-dose pilot (registered 2026-10-06)".

**Revision history:**

- Rev 0 (pre-registration, committed before any API call): dose matrix, item set, scoring, low-dose reuse test, and the decision rule with exact numbers.

---

## Decision Rule (Fixed Before Any API Call)

### Doses

Each arm has a lower dose L, which is the current pin in `config/models.yaml`, and a higher dose H. H is the smallest documented provider-side step above the pin.

| Arm | L (pin) | H | Basis for H |
|---|---|---|---|
| gpt-5.1 (`openai_gpt51`) | `reasoning_effort: none`, temperature 0.0 | `reasoning_effort: low`. `temperature` and `top_p` are omitted, because GPT-5.1 returns HTTP 400 on sampling fields at any effort other than `none`. | The next documented effort above `none` |
| Sonnet 5.5 (`anthropic`) | `thinking: {type: between_tools}`, thinking off | `thinking: {type: adaptive}` + `output_config: {effort: low}` | The brief asked for a small thinking budget, but `budget_tokens` returns 400 on Sonnet 5.5 (claude-api reference, cached 2026-09-25), so no budget can be set. Adaptive thinking at the lowest documented effort (`low`) is the minimum thinking-on dose. |
| ER-2 (`gemini`) | `thinking_level: low` | `thinking_level: medium` | The documented levels for `gemini-robotics-er-2-preview` are `minimal, low, medium, high` (ai.google.dev thinking guide, fetched 2026-10-06). `medium` is one step up, and the Robotics-ER page recommends it for "a good balance between latency and performance". |
| DeepSeek (`deepseek`) | `thinking: {type: disabled}` | `thinking: {type: enabled}` + `reasoning_effort: low` | When thinking is enabled, DeepSeek defaults to effort `high`. That is not a small step, so H uses the lowest documented effort (`low/high/max`), to match the other arms' smallest-step doses. |

`max_tokens` stays at the pinned 2048 in both doses. Thinking tokens share that cap, so a truncated answer, or one with no text, scores as wrong. Every call records its `stop_reason` / `finish_reason`.

The overrides live only in a pilot copy of `models.yaml`, kept outside `config/` and passed with `--models-yaml`. Its sha256 is recorded below. `config/models.yaml` is not edited.

### Items and Calls

- The items are the 20 `conflict_prediction` items of the battery-v2 `main` subset (`manifest_v2.json`, SHA `faf1953b…`): 10 GT-yes and 10 GT-no.
- The prompt is the frozen capability-probe prompt v1, with the same seeded lettering.
- Each item gets one call, with no re-ask and no grey-image fallback. This is the runner's standing policy.
- Each call records:
  - wall-clock latency of `analyze()`;
  - input, output and thinking/reasoning tokens;
  - the request body, with images replaced by their sha256;
  - the served model.
- Before each H run there is one smoke call per H config, on a conflict_prediction item, excluded from scoring. It checks four things:
  - the request is accepted;
  - the thinking-token field is present;
  - DeepSeek accepts an image with thinking enabled;
  - whether DeepSeek ignores or rejects `temperature`.
- For this pilot, any HTTP 4xx is fatal: the arm stops, the cause is fixed, and the whole arm-dose is re-run. Other transport errors follow the runner policy. They score `backend_error` (wrong) and are reported item by item.

### Low-Dose Source

- **Primary L, reused from storage.** The stored L results for gpt-5.1, ER-2 and DeepSeek are reused only if the full request body for each of the 20 items is byte-identical at the stored run's commit and at HEAD. The bodies are captured through a fake `requests.post`, with the image payloads hashed.
  - gpt-5.1: 15/20, from two segments at `66e4f44` and `a0db9f6`. Both segments must match.
  - ER-2: 16/20, at `23e36c5`.
  - DeepSeek: 19/20, at `66e4f44`.
  - Any mismatch means L is re-run fresh and becomes the primary.
- **Sonnet's primary L is a fresh run under HEAD** (brief).
- **Same-day retest.** A same-day L retest (20 calls) is run for every arm. It is the latency source for L, because the stored records carry `latency_ms: null`, and it is the drift/noise reading. The rule is applied against the primary L. The verdict against the retest L is reported beside it, and any disagreement goes to the owner.

### Rule

- **net** = (H correct) − (L correct) on the 20 paired items. Refusals, unparsed answers and backend errors all count as wrong.
- **Registered margin: net ≥ +3 (of 20).**
- **Registered latency bound: the median per-call wall-clock latency of the 20 H calls is ≤ 15.0 s.** This is the orchestrator's re-analysis `cooldown_sec: 15.0` (`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`). It is a PROXY: a probe call is one short single-image prompt, and a stage-1 episode call carries the v3.4 prompt and differs in latency.
- **Adopt H for an arm only if both hold.** Otherwise the arm keeps L.
- **ER-2 exception.** ER-2's config is v1-frozen. If H passes for ER-2, it is NOT adopted; it is flagged as an owner decision.
- An exact two-sided McNemar test on the discordant pairs is reported for every arm. It is not part of the decision.

### Ceilings, Stated in Advance

- DeepSeek's primary L is 19/20, so net is at most +1. The rule cannot adopt DeepSeek's H by construction. The arm runs anyway for the latency, token and answer-change record.
- ER-2's net is at most +4 and gpt-5.1's at most +5. Sonnet's ceiling depends on its fresh L.

### Budget

- Hard stop: **$5**.
- Cost is computed from per-call usage at list prices, with thinking/reasoning tokens billed as output:
  - gpt-5.1: $1.25 / $10 per MTok.
  - Sonnet 5.5: $2 / $10.
  - ER-2: $1.00 / $5.00 (the battery-v2 report's rates).
  - DeepSeek Flash: $0.15 / $0.60 off-peak, doubled at peak (01–04 and 06–10 UTC).
