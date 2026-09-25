# Gemini Robotics-ER 2 Integration — Design

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: transport-surface correction (Interactions API, not the legacy `:generateContent` page), Option A `gemini` backend sketch, the no-sampling-controls reproducibility finding, Option B deferral, a cost estimate, and the probe gate.
- Rev 2 (2026-09-18): resolved the §7 gate with live-VM probe evidence (PASSED, with and without schema forcing); added the no-visible-reasoning-trace confound (§4(d)); replaced the cost estimate with the measured per-call figure; added the VM reproduction recipe and two new open items (`thinking_summaries`, a paired-image/paired-state probe).
- Rev 3 (2026-09-18): Option A landed. `GeminiBackend` (`reasoning/vlm/gemini_backend.py`), `GeminiBackendConfig` (`reasoning/vlm/models.py`), the `"gemini"` branch in `backend_factory.py`, and a `vlm.gemini` block in `config/models.yaml` are implemented, unit-tested (`tests/unit/test_gemini_backend.py`), and live-verified through the real `reasoning.vlm.reasoner.Reasoner` path (not the probe script) on the VM: a genuine head-on scene (two robots 0.35 m apart, mutually facing) returned `congestion_detected=true, type=deadlock, strategy=yield` in 2492 ms, with `raw["unsupported_sampling"]` populated and one WARNING logged. Unlike `AnthropicBackend`, the four dropped `ReasonerConfig` sampling fields are recorded per call in `BackendResponse.raw["unsupported_sampling"]` rather than silently omitted (§4(b) below); `AnthropicBackend`'s equivalent silent drop is added as a new open item.
- Rev 5 (2026-09-18): resolved the image-grounding open item with the paired-image/paired-state probe (`docs/reports/2026-09-18-gemini-er2-image-grounding.md`) — ER-2 localizes both robots in our frames, but its congestion decision tracked the text state block in 6/6 incongruent calls with derived geometry on and 22/24 with it off.
- Rev 6 (2026-09-18): identified the prompt as the cause of Rev 5's null result and measured the fix. A new opt-in modality flag, `ReasonerRequest.include_visual_crosscheck` (default `False`; `reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`), appends a block giving the image precedence over the state block on a clear contradiction while leaving Fix B's "do not re-derive distances or facing from the coordinates" clause verbatim. With it on, ER-2's incongruent cells invert from 0/10 to 10/10 image-consistent answers (n = 5 per cell) and the Fix-B regression cell (1.2 m apart, `|Δθ| = π`, diverging, both MOVING) still answers no-congestion 5/5 — the fix does not reopen run 3. Two caveats recorded in the report, not resolved here: cell B's *classification* drifts to `type=anomaly` with `priority_override`/`reroute` in 4/5 calls even though its detection is right, so the flag is not production-ready; and the same 2x2 against `gpt-4o` at its production temperature 0.0 reproduced the null result 6/6, so Rev 5's finding is **apparatus-wide, not Gemini-specific**. §4(d)'s unverified claim about the `openai` arm's `<think>` block is also settled there: `gpt-4o` emits one in 12/12 calls, but its content is a verbatim echo of the prompt's template sentence and carries no reasoning.
- Rev 4 (2026-09-18): closed the gap Rev 3 left open — `raw["unsupported_sampling"]` never reached a persisted run artifact, only `BackendResponse.raw` (in-memory) and a stderr WARNING. `ReasonerDiagnostics.unsupported_sampling` (`reasoning/vlm/models.py`) now carries it through every `Reasoner.run()` path (success, re-ask-then-success, and exhausted-retries), and `write_reasoner_log` emits the key in the JSONL artifact when set (omitted, not `null`, when the backend reported nothing). §4(b) below is corrected accordingly: this document previously described artifact visibility that did not yet exist.

**Status:** Landed and live-verified (2026-09-18). The §7 gate **PASSED**
(live VM run, 2026-09-18) and Option A is now implemented: `GeminiBackend`,
`GeminiBackendConfig`, the `backend_factory.py` `"gemini"` branch, and
`config/models.yaml`'s `vlm.gemini` block all exist and were exercised
end-to-end through `reasoning.vlm.reasoner.Reasoner` (see Rev 3 note above),
not just the gating probe. `force_schema` defaults `False` per the gate
result (schema forcing is optional, not load-bearing). Open items carried
forward, none of which block the landed backend: `thinking_summaries` as a
candidate mitigation for the no-visible-reasoning-trace confound (§4(d)); and
`gemini`/`anthropic`'s absence from
the parent spec's "Model and decoding pre-registration" table (§4(b)), which
this implementation does not resolve on its own. The image-grounding open
item is **resolved** (Rev 5): see §7's open-items list and
`docs/reports/2026-09-18-gemini-er2-image-grounding.md`.

**Parent spec:** `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
(Arm A backend roster in "Model and decoding pre-registration"; Appendix A.7
apparatus disclosure, cited in §5 below).

---

## Context

**Gemini Robotics-ER 2** ("Embodied Reasoning") is a Gemini model family
specialized for spatial and embodied reasoning over images/video rather than
open-ended chat: pointing, 2D/3D bounding boxes, object-affordance reasoning,
and trajectory generation, intended as a grounding layer for robot
perception/planning rather than an end-to-end action policy. Google positions
it as a "thinking" model for spatial understanding, distinct from a
vision-language chat model like `gpt-4o` or `claude-opus-4-8` (the two
backends already registered in `reasoning/vlm/backend_factory.py`).

**URL correction (record per CLAUDE.md "External Library Verification").**
The page originally proposed for this evaluation,
`ai.google.dev/gemini-api/docs/generate-content/robotics-spatial`, is marked
**"(Legacy)"** as of the 2026-09-18 docs fetch and describes the older
`:generateContent` surface. The live, authoritative transport is the
**Interactions API** (`POST .../v1beta/interactions`), documented separately
from `:generateContent` and with a different request/response envelope (§2).
Do not implement against the legacy page.

Authoritative sources (fetched 2026-09-18):

- Robotics overview: <https://ai.google.dev/gemini-api/docs/robotics-overview>
- Interactions API reference: <https://ai.google.dev/api/interactions-api>
- ER-2 model card: <https://ai.google.dev/gemini-api/docs/models/gemini-robotics-er-2-preview>
- Structured output: <https://ai.google.dev/gemini-api/docs/structured-output>
- Robotics streaming (Live API variant): <https://ai.google.dev/gemini-api/docs/robotics-streaming>
- Pricing: <https://ai.google.dev/gemini-api/docs/pricing>

**Model IDs.**

- `gemini-robotics-er-2-preview` — standard Interactions API model. Structured
  output supported. This is the only candidate for Option A (§3).
- `gemini-robotics-er-2-streaming-preview` — Live API variant for the
  streaming surface (`robotics-streaming` doc). **Structured output is not
  supported** on this variant, which rules it out for a backend that must
  emit a schema-validated `CongestionDecision`.
- `gemini-robotics-er-1.6-preview` — being shut down end of August 2026 and
  absent from the current pricing page. Not a target for this or any future
  work; mentioned only so nobody resurrects it from an older bookmark.

**Model card facts** (ER-2 standard, as of the July 2026 update): inputs
text/image/video/audio → output text; input token limit 131 072; output token
limit 65 536; structured outputs supported.

---

## Transport delta: OpenAI Chat Completions vs. the Interactions API

`reasoning/vlm/openai_backend.py` and `reasoning/vlm/anthropic_backend.py`
both speak a "one message list, one response object" HTTP shape that a
Gemini backend does **not** share. A `gemini_backend.py` cannot be written by
copying either file and swapping field names — the request envelope, the
response path, and the sampling surface are all different in kind, not just
naming.

| Aspect | OpenAI `chat/completions` | Anthropic Messages | Gemini Interactions API |
|---|---|---|---|
| Endpoint | `POST {base_url}/chat/completions` | `POST {base_url}/messages` | `POST https://generativelanguage.googleapis.com/v1beta/interactions` |
| Prompt field | `messages: [{role, content[]}]` | `system` (string) + `messages: [{role, content[]}]` | top-level `system_instruction` (string) + `input: [Content]` — no `role`/`messages` list at all |
| Image attachment | `{"type":"image_url","image_url":{"url":"data:<mime>;base64,..."}}` part inside `messages[].content[]` | `{"type":"image","source":{"type":"base64","media_type":...,"data":...}}` part (no `data:` prefix) | `{"type":"image","data":"<base64>","mime_type":"image/png"}` item inside the `input` array (verified against the Interactions API reference, 2026-09-18) |
| Response text path | `choices[0].message.content` | `content[]` array, first block with `type == "text"` | `steps[].content[].text`, filtered to `content[]` entries with `type == "text"` — `steps[]` are typed too (`"model_output"`, `"user_input"`, `"function_call"`, …) and must not be assumed to always carry text |
| Sampling controls | `temperature`, `top_p`, `max_tokens` top-level; `top_k` unsupported (omitted) | **none** — Claude Opus 4.7+ rejects `temperature`/`top_p`/`top_k` with HTTP 400, so `AnthropicBackend.analyze` omits all three (`anthropic_backend.py:42`) | **none** — `temperature`/`top_p`/`top_k` are not fields of `generation_config` at all (not merely unsupported values); nearest controls are `seed` and `thinking_level` (§4) |
| Structured output | `response_format: {"type":"json_object"}` (loose, no schema) | none (prompt-only JSON discipline) | `response_format: {"type":"text","mime_type":"application/json","schema": <JSON Schema>}` — actually schema-validated, but only a documented subset of JSON Schema keywords |
| Auth | `Authorization: Bearer <key>` | `x-api-key` + `anthropic-version` headers | unconfirmed by docs; try `x-goog-api-key: $GEMINI_API_KEY` first, fall back to `Authorization: Bearer $GEMINI_API_KEY` on 401/403 (§7 probe reports which worked) |

Two consequences follow directly from this table and are binding on any
follow-up implementation:

1. There is no `messages`/`role` concept to reuse — `PromptPayload.system_prompt`
   maps to the top-level `system_instruction` string, and
   `PromptPayload.user_prompt` plus the encoded image become two `Content`
   items in a flat `input` array, not a `user`-role message.
2. Response parsing must walk `steps[]` and concatenate every `content[]`
   entry whose `type == "text"` (across all steps), not index a single fixed
   path the way `choices[0].message.content` does — the docs only give
   example step types, not an exhaustive enum, and a non-text step (e.g. a
   `function_call` step, unused today but part of the documented surface)
   must be skipped rather than crashing the extractor.

---

## Option A (recommended): a `gemini` backend behind the existing `VLMBackend` Protocol

A `GeminiBackend` implementing the same three-line `VLMBackend` Protocol
(`reasoning/vlm/backend_base.py`) as `OpenAIBackend`/`AnthropicBackend`/
`LlamaServerBackend` is a drop-in **third reasoner cell for Arm A**
(alongside `openai` and the not-yet-pre-registered `anthropic`): identical
`PromptPayload` in, identical `CongestionDecision` contract out, so M3
grounding and M4 execution are completely unaware which backend produced the
decision. No new dependency: like every other backend in this repo,
`GeminiBackend` would use plain `requests` (already in `requirements.txt`)
against a public HTTP endpoint with a JSON body — there is nothing in the
Interactions API that requires the `google-genai` SDK, so CLAUDE.md's
"Add external dependencies without documenting why" rule is a non-issue for
transport. (§4 below does add a *config-shape* obligation, not a dependency.)

**Class shape** (illustrative — not landed by this document):

```python
class GeminiBackend:
    """HTTP adapter for the Gemini Interactions API (Robotics-ER 2 preview).

    Unlike OpenAIBackend/AnthropicBackend, this does not send `temperature`,
    `top_p`, or `top_k` — the Interactions API's `generation_config` has no
    such fields (see design doc §4). The nearest controls are `seed` and
    `thinking_level`.
    """

    def __init__(
        self,
        model_id: str = "gemini-robotics-er-2-preview",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        api_key_env: str = "GEMINI_API_KEY",
        thinking_level: str = "low",
    ) -> None: ...

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse: ...
```

**Config model**, mirroring `OpenAIBackendConfig` in `reasoning/vlm/models.py`:

```python
class GeminiBackendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_id: str = "gemini-robotics-er-2-preview"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    api_key_env: str = "GEMINI_API_KEY"  # env var NAME holding the key; never the key itself
    thinking_level: Literal["low", "high"] = "low"
```

`resolve_reasoner_config`/`backend_section` in `backend_factory.py` already
handle "shared `reasoner:` block + per-backend override" generically, so a
`vlm.gemini` section would slot in the same way `vlm.openai` does today —
except its `reasoner:` override must *declare* `temperature` inapplicable
rather than pin a value (§4), which today's `ReasonerConfig` has no field for.

**`api_key_env` treatment.** Same discipline as every other hosted backend
in this repo: the key name is `GEMINI_API_KEY`, it is never written into
`config/models.yaml` (only the env-var *name* lives there, exactly as
`api_key_env: OPENAI_API_KEY` does today) and never passed on a command
line. On the VM, per the existing pattern for `OPENAI_API_KEY`
(`docs/implementation_notes.md`, 2026-09-16 entry; `scripts/run_phase3_demo.sh`),
it goes in `/home/ubuntu/vgu-vlm-swarm/.env` (`chmod 600`) and is loaded with
`set -a && source /ws/.env && set +a` immediately before launching M5 —
never interpolated into a command string, which is exactly the mistake that
`run_phase3_demo.sh`'s comment (line ~169) already documents as a leak
vector for `OPENAI_API_KEY`.

**File list a follow-up implementation task would touch** (not touched here):

| File | Change |
|---|---|
| `reasoning/vlm/gemini_backend.py` | New `GeminiBackend` (Interactions API HTTP adapter) |
| `reasoning/vlm/models.py` | Add `GeminiBackendConfig` |
| `reasoning/vlm/backend_factory.py` | Add `"gemini"` branch to `build_backend`, add `GeminiBackendConfig` to the `BackendConfig` union |
| `reasoning/vlm/__init__.py` | Re-export `GeminiBackend`, `GeminiBackendConfig` |
| `config/models.yaml` | New `vlm.gemini` section; per-backend `reasoner:` override that declares `temperature` inapplicable (§4) instead of pinning a value |
| `docs/specs/module2_vlm_reasoning.md` | Document the backend per module boundary rules (§6.5-equivalent) |
| `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` | Add `gemini` to "Model and decoding pre-registration" if/when it becomes a reported cell — see §4's finding about `anthropic`'s current absence from that table |
| `tests/unit/test_gemini_backend.py` | New, mirroring `tests/unit/test_openai_backend.py` / `tests/unit/test_anthropic_backend.py` (mocked `requests`, no live calls) |

---

## The reproducibility consequence — no sampling controls on the Interactions API

This is the most important finding in this document, not an implementation
detail to bury in a code comment.

The Interactions API's `generation_config` allows only `max_output_tokens`,
`seed`, `speech_config`, `stop_sequences`, `thinking_level`,
`thinking_summaries`, `tool_choice`, `transcription_config`, and
`video_config`. **`temperature`, `top_p`, and `top_k` are not among them** —
this is not "unsupported and ignored," it is "not a field that exists in the
request schema."

The project's `openai` arm is pinned to `temperature: 0.0`
(`config/models.yaml`) for a documented, evidence-backed reason: at
`temperature: 0.6`, `gpt-4o` matched `|Δθ| ≈ π` on two robots driving *apart*
and answered `deadlock`/`reverse`, causing a yield/reverse oscillation (run 3,
2026-09-17; see `reasoning/vlm/prompt_builder.py`'s `_FACING_COS` comment and
rev-8 spec 8.4). Greedy decoding is load-bearing for that arm's reliability,
not a stylistic default.

**(a) `ReasonerConfig.temperature` is structurally inapplicable to a Gemini
backend and must be declared inapplicable, not silently ignored.**
`ReasonerConfig` (`reasoning/vlm/models.py`) has no representation for "this
field does not apply to this backend" — every field has a default and is
always populated, the same shape problem `AnthropicBackend` already has
(`analyze` silently omits `temperature`/`top_p`/`top_k` from the request body;
`anthropic_backend.py:42`, comment only). A `GeminiBackend` inherits the same
problem, one field worse: `AnthropicBackendConfig`/`GeminiBackendConfig` give
the backend layer nowhere to *say* "inapplicable" — omission happens inside
`analyze()` and is invisible from the config or the spec. Any follow-up task
must add that declaration at the spec/prereg layer (e.g., an explicit "N/A"
row, not a `0.0` default that reads as a decoding choice) rather than
inventing a new optional field on a shared Pydantic contract for one
backend's limitation.

**(b) This is a between-arm confound the preregistration must record, not an
implementation detail.** It already isn't being recorded: `anthropic` is
registered in `backend_factory.py` but is **absent** from the parent spec's
"Model and decoding pre-registration" table (only `openai` primary and
`llama_server` secondary are pinned there). Its inability to honor
`temperature`/`top_p`/`top_k` at all exists only as a code comment today.
Landing `gemini` while repeating that pattern would leave a research design
with three Arm A cells, only one of which (`openai`) has a decoding
guarantee that matches the reliability argument the design was built on
(temperature 0.0 for a classification workload). If `gemini` or `anthropic`
becomes a reported cell, the prereg table needs an explicit row stating
"sampling control: none available; nearest analog: `seed` / N/A" — a "no"
result from an ungreedy-decoded cell is not comparable to a "no" from the
greedy `openai` cell without that caveat attached.

**(b), updated 2026-09-18 (Rev 4): the dropped-sampling-fields confound now
lands in the persisted run artifact, not only in-memory/stderr.** When
`GeminiBackend` landed (Rev 3), the visibility this section and the class's
own docstring described — `raw["unsupported_sampling"]` plus a one-time
WARNING — stopped at `BackendResponse`: `Reasoner.run()` only threaded
`latency_ms`/`token_usage`/`parse_status` into `ReasonerDiagnostics`, so
`raw` (and the dropped-fields dict inside it) was discarded before
`write_reasoner_log` ever wrote a line. A preregistered run's JSONL trace
therefore carried no record of the confound at all — a correction, not a new
finding: this section previously read as though artifact visibility already
existed, and it did not. `ReasonerDiagnostics.unsupported_sampling`
(`reasoning/vlm/models.py`) now carries the value through every
`Reasoner.run()` path — first-attempt success, re-ask-then-success, and
exhausted-retries — and `write_reasoner_log` (`reasoning/vlm/reasoner.py`)
emits an `"unsupported_sampling"` key in the JSONL record when the backend
reported one, omitting it entirely otherwise. The prereg-table obligation
this section describes is unchanged by this fix — a "sampling control: none
available" row is still owed — but the underlying fact is now checkable from
the run artifact itself instead of only from a live log stream.

**(c) `thinking_level` (`low`/`high`) is a new ablation axis with no
counterpart in the other arms.** Cosmos Reason 2 (`llama_server`) has its own
chain-of-thought behavior via prompt-driven `<think>` tags at a fixed sampling
preset; `openai`/`anthropic` have no comparable knob. `thinking_level` is
Gemini-specific, changes latency and output token count (and therefore cost,
§6), and — because it is not a sampling parameter — sits outside the
temperature-pinning discussion entirely. It should be treated as its own
documented axis (a candidate value, not swept) if `gemini` is added, not
folded into "decoding" as if it were a substitute for `temperature`.

**(d) NEW (2026-09-18, from the §7 probe): ER-2 returns no visible reasoning
trace, while still billing thought tokens — a second, distinct confound.**
The prompt (`reasoning/vlm/prompt_builder.py`, shared unmodified by every
backend) explicitly asks for a `<think>…</think>` block immediately before
the final JSON object; `reasoning.vlm.output_parser`'s tolerant parser
strips `<think>…</think>` generically (comment: "Cosmos Reason 2 emits a
`<think>...</think>` chain-of-thought before the answer"), and
`LlamaServerBackend.analyze` (`llama_server_backend.py`) deliberately omits
`response_format` *specifically so that trace is not suppressed* ("forces
the first generated token to open a JSON object, which suppresses the
model's `<think>` chain-of-thought... Cosmos Reason 2 relies on that
reasoning trace for grounding accuracy" — comment, asserted by
`tests/unit/test_reasoner.py::test_llama_backend_body_allows_reasoning_and_sends_sampling`).
Both §7 probe calls to ER-2 — **with and without** schema forcing — returned
bare JSON with **no `<think>` block at all**, while the response reported
171 and 202 `total_thought_tokens` respectively: ER-2 reasons internally and
withholds the trace text regardless of `response_format`. This breaks
trace-level comparability with the Cosmos/`llama_server` arm, whose visible
trace is a deliberate design property of this codebase, not an artifact of
one prompt. Whether the `openai`/`anthropic` arms' raw output actually
contains a visible `<think>` block in practice is **not verified by this
document** — neither `openai_backend.py` nor `anthropic_backend.py` forces
`response_format` either, so nothing in this codebase structurally
suppresses the trace for them the way `LlamaServerBackend` avoids doing on
purpose, but no live `raw_text` sample was inspected here to confirm one is
actually present. At minimum, comparability against the Cosmos arm is
broken; the `openai`/`anthropic` arms are unconfirmed either way. This is a
second between-arm confound of the same family as (b)'s missing-temperature
finding — a between-arm asymmetry the preregistration must record, not a
defect to fix in a future `gemini_backend.py`. **Candidate mitigation,
untested:** `generation_config.thinking_summaries` is a documented field of
the Interactions API (<https://ai.google.dev/api/interactions-api>); §7
lists it as the next probe to run before assuming it recovers a usable
trace.

---

## Option B (do not build now): ER-2 spatial primitives as a perception/grounding source

ER-2 advertises spatial primitives beyond decision-making: 2D points
(`[{"point": [y, x], "label": ...}]`, normalized 0–1000 in **[y, x]** order),
boxes, and trajectories, plus video input and multi-robot-collaboration
framing (`robotics-overview` doc). This makes it tempting to use ER-2 as a
grounding source — feeding it the raw scene and letting it emit *where the
robots should go* directly, rather than a semantic decision that M3 then
grounds into geometry.

**Why this is deferred, not just "future work."** M3's grounding
(`reasoning/rag/command_grounder.py`) is, per the parent spec's Appendix A.7
audit (rev 8.1, 2026-09-16), "a deterministic strategy-to-template bridge,
not retrieval": `yield` expands to reverse-to-park / side-step / hold /
escort, computed from the robots' perceived positions and a *declared* scene
geometry (`reasoning/rag/scene_geometry.py`, `scenario_geometry` in
`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`) — e.g. a ≈1.79 m
park offset and a 0.36 m side-step for `head_on_deadlock`, hand-maintained to
mirror the Isaac scenario. That appendix already names this scripted geometry
step as the biggest caveat in the decision-source comparison: "the
decision-source comparison remains valid" only because the *geometry* half
of the pipeline is identical across arms, and only the *decision* half (VLM
vs. rule-based) varies.

Replacing that scripted geometry step with model-generated points/boxes/
trajectories is the single most direct attack on that caveat — but it
changes what is being compared. It would make M3 partly model-derived
instead of purely templated, breaking the "identical downstream pipeline
across arms" property the rev-8 Arm A/B comparison depends on: a difference
in outcome would no longer isolate "VLM vs. rule-based decision," it would
also reflect "templated geometry vs. model-derived geometry." That is a
legitimate and interesting question, but it is a **separate third arm** (or a
follow-up design document), not a drop-in upgrade to Option A's `gemini`
reasoner cell.

Two concrete engineering obstacles for that follow-up design to address,
noted here so they aren't rediscovered from scratch:

- ER-2's spatial coordinates are normalized **0–1000 in `[y, x]` order**.
  This project's convention throughout M1 (`CLAUDE.md` OpenCV/Geometry
  section) is pixel `(u, v)` and world `(x, y)` in metres — the opposite
  axis order and a different normalization. Converting a `[y, x]`/1000 point
  into a usable command requires: denormalize against the image's `(H, W)`,
  swap to `(u, v)` pixel order, then run M1's existing pixel-to-world
  homography (`ros2_ws/src/swarm_perception/.../geometry.py`) to get `(x, y)`
  metres — a real conversion step, not a relabeling.
- ER-2 takes video, which is a different M1 output shape than the single
  annotated frame `ReasonerRequest.image_path` carries today; using video
  meaningfully would also touch M1's frame-delivery contract, which is out
  of scope for an M2-only backend.

**Recommendation:** track this as a distinct design question once Option A's
probe-gated `gemini` reasoner cell (if adopted) has produced enough decision
data to know whether ER-2's classification quality on this project's scenes
is competitive at all. Attacking the A.7 caveat before that is answered
front-loads risk on two axes at once.

---

## Cost

Per the pricing page (standard model, per 1M tokens; one input rate covers
text/image/video/audio; valid **through 2026-12-31**, doubling on
2027-01-01):

| | Standard | Batch (half) |
|---|---|---|
| Input (text/image/video/audio) | $1.00 → $2.00 | $0.50 → $1.00 |
| Output | $5.00 → $10.00 | $2.50 → $5.00 |
| Context caching | $0.10 → $0.20 | — |

A **free tier exists** ("Free of charge" in the pricing page's free-tier
column) — cheap enough for the probe call in §7 to cost nothing or close to
it regardless of which tier applies. `gemini-robotics-er-1.6-preview` is
absent from the pricing page entirely, consistent with its scheduled
shutdown.

**Measured (2026-09-18), replacing the order-of-magnitude estimate below.**
§7's live probe ran `thinking_level: low` both with and without schema
forcing; token counts were nearly identical between the two:

| | with schema (Result 1) | without schema (Result 2) |
|---|---|---|
| `total_input_tokens` | 1 907 (text 843, image 1 064) | 1 907 (text 843, image 1 064) |
| `total_output_tokens` | 88 | 85 |
| `total_thought_tokens` | 171 | 202 |
| `total_tokens` | 2 166 | 2 194 |
| `total_cached_tokens` | 0 | 0 |
| latency_ms | 3 562 | 2 605 |

(Both responses also reported a `raw_prompt_token` value — 2 341 and 2 089
respectively — that does not reconcile with `total_input_tokens`; recorded
here verbatim, not used in the arithmetic below because the discrepancy is
unexplained.)

At standard (non-free-tier) pricing from the table above (input $1.00/1M,
output $5.00/1M) and Result 1's counts, thought tokens billed as output
tokens even though their text is never returned (§4(d)):

```text
input:  1,907 tok * $1.00 / 1e6 tok               ≈ $0.0019
output: (88 + 171) tok * $5.00 / 1e6 tok          ≈ $0.0013
total:  ≈ $0.0032 per analysis (measured, thinking_level: low)
```

— roughly half the project's measured ≈$0.006/analysis for `gpt-4o`. Both
probe calls in §7 actually ran on the **free tier**, so they cost $0.00; the
arithmetic above is what the same call would cost off the free tier.
Latency (2.6–3.6 s per call) is a new Layer-2 budget datum: on the same
order as the project's other backends and compatible with the 0.5–2 Hz M2
cadence. `thinking_level: high` is untested and — per §4(c) — is expected to
raise both latency and output-token cost by an unknown, model-dependent
factor; this is exactly why §4(c) treats `thinking_level` as its own axis
rather than a tuning knob to set once and ignore.

**Order-of-magnitude estimate (superseded by the measurement above; kept for
the arithmetic method).** The rendered M2 prompt is ≈3 600 characters of
text (`docs/implementation_notes.md`, 2026-09-17 entry, ≈900 tokens at a
rough 4 chars/token) plus one image; a generous total input estimate of
1 500–3 000 tokens and an output estimate of 200–400 tokens (JSON decision,
`thinking_level: low`) put one analysis at roughly:

```text
input:  ~2,000 tok * $1.00 / 1e6 tok ≈ $0.002
output: ~300 tok   * $5.00 / 1e6 tok ≈ $0.0015
total:  ≈ $0.003–0.005 per analysis (order of magnitude, NOT measured)
```

---

## Gate result and open questions

**The gate — PASSED (2026-09-18).** The gate question was:

> Given the real M2 prompt (`reasoning.vlm.prompt_builder`) plus one scene
> image, sent to `gemini-robotics-er-2-preview` on the Interactions API with
> `reasoning/schemas/vlm_decision.schema.json` as `response_format`, does the
> response's extracted text pass the existing `reasoning.vlm.output_parser`
> (`parse_decision_text`) and produce a valid `CongestionDecision`?

Both a schema-forced and a non-schema-forced live call against the real API
returned a payload satisfying `reasoning/schemas/vlm_decision.schema.json`
under the project's unmodified prompt, and both passed the tolerant parser
(`parse_decision_text`) and the strict schema parser (`parse_vlm_decision`).
Schema forcing is therefore optional, not load-bearing, for this prompt —
Option A is viable as a drop-in on the existing output contract. This
result is scoped to `include_pairwise_geometry=True` (Modality condition
below) and to a single sample per condition (Limitation below): it resolves
the go/no-go gate, not a claim of general reliability.

**Reproduction recipe.** Host: GCP VM
`vgu-canary-base-isaac-workstation-vm`, project `summer-flux-501516-n6`,
zone `us-central1-a`; repo at `/home/ubuntu/vgu-vlm-swarm` bind-mounted into
container `vgu_ros` at `/ws`. The key lives in
`/home/ubuntu/vgu-vlm-swarm/.env` as `GEMINI_API_KEY` and is sourced inside
the container so it never reaches a command line:

```bash
sudo docker exec -w /ws vgu_ros bash -lc "set -a && source /ws/.env && set +a && python3 scripts/probe_gemini_er2.py --schema --thinking-level low"
```

Container interpreter: python 3.12.3, requests 2.31.0, pydantic 2.13.5,
numpy 1.26.4, cv2 4.6.0 — nothing needed installing. Auth: `x-goog-api-key`
worked on the first attempt (no fallback to `Authorization: Bearer` was
exercised); the key is a new-style Google key (length 53, prefix `AQ.`).
Scene image: the probe's repo-search precedence found a real committed-on-VM
frame, `data/logs/m5_frames/0cad824071954e21832da19a6fcb588b.png`; that
directory is git-ignored, which is why no committed frame was found when
this repo is checked out fresh (e.g. on the Mac). No placeholder was
synthesized for this run.

**Result 1 — with schema forcing** (`--schema --thinking-level low`): HTTP
200, latency 3 562 ms. Response (verbatim):

```json
{
  "congestion_detected": false,
  "type": "none",
  "involved_robots": [],
  "root_cause": "",
  "strategy": "none",
  "justification": "The robots are spaced 1.00 meter apart, which is greater than the 0.5 meter threshold required for physical conflict, meaning no immediate deadlock or congestion is detected."
}
```

Tolerant parser accepted: True. Strict schema parser accepted: True.
Decision: `congestion_detected=False type=none strategy=none`.

**Result 2 — without schema forcing** (`--no-schema --thinking-level low`):
HTTP 200, latency 2 605 ms. Response (verbatim):

```json
{
  "congestion_detected": false,
  "type": "none",
  "involved_robots": [],
  "root_cause": "",
  "strategy": "none",
  "justification": "The robots are currently 1.00 m apart, which is greater than the 0.5 m threshold for physical conflict or deadlock, despite facing each other."
}
```

Tolerant parser accepted: True. Strict schema parser accepted: True.
Decision: `congestion_detected=False type=none strategy=none`. Token usage
for both results: §6 (Cost).

**Limitation — what these two calls do and do not show.** The probe's robot
states are hardcoded synthetic (`build_reasoner_request`: robot_1 at (0,0)
θ=0, robot_2 at (1,0) θ=π, both STOPPED, 1.00 m apart), sent alongside a real
scene frame that does not necessarily depict that configuration. Both
justifications cite only the 1.00 m spacing rule, so these two calls
demonstrate schema conformance and correct threshold arithmetic, but **do
not demonstrate image grounding**. `congestion_detected=false` is the
textually correct answer under the prompt's own ">0.5 m ⇒ not conflicting"
rule (see `reasoning/vlm/prompt_builder.py`), and is notably
the exact discrimination `gpt-4o` failed at temperature 0.6 on two robots
driving apart (matched `|Δθ| ≈ π` and answered `deadlock`/`reverse`; rev-8
spec 8.4, `docs/implementation_notes.md` 2026-09-17 root-cause entry) — but
this is one sample per condition, so it is encouraging, not evidence of
superiority. A paired-image/paired-state probe is required before any
grounding or comparative-quality claim; it ran on 2026-09-18 and found no
decision-level image grounding
(`docs/reports/2026-09-18-gemini-er2-image-grounding.md`; open item below).

**Answered secondary questions** (listed as non-gating in the initial
draft):

- Auth header: `x-goog-api-key` worked on the first attempt; no bearer
  fallback was exercised.
- Real token usage: measured, §6 (Cost).
- `parse_vlm_decision` vs. `parse_decision_text` agreement: both parsers
  accepted both results — no divergence observed at `thinking_level: low`.

**New open items surfaced by the probe** (not resolved by this run):

- `generation_config.thinking_summaries` — a documented field of the
  Interactions API (<https://ai.google.dev/api/interactions-api>); untested.
  Candidate mitigation for §4(d)'s no-visible-trace finding. Next probe to
  run, and belongs in the preregistration alongside the missing-temperature
  confound (§4(b)) once resolved either way.
- **RESOLVED (Rev 5, 2026-09-18): the paired-image/paired-state probe ran, and
  decision-level image grounding was not demonstrated.** Report:
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`; harness:
  `scripts/probe_gemini_er2_grounding.py`; artifacts:
  `data/logs/er2_grounding/grounding_run{1,2_exp3_n9}.jsonl` on the VM. Two
  measured frames from the live ER-2 run — 0.251 m nose-to-nose and 4.884 m
  apart — were crossed with synthetic 0.35 m-facing and 2.50 m-diverging text
  states through the unmodified prompt and `Reasoner`. Both congruent gate
  cells passed 3/3, and in the incongruent cells the decision followed the
  **text**: 6/6 calls with `include_pairwise_geometry=True` (n = 3 per cell)
  and 22/24 with it `False` (n = 12 per cell), the 2 exceptions being the only
  responses in 36 decision calls whose justification read visual rather than
  numeric. Separately, ER-2's native pointing localized both robots in both
  frames to 0.005–0.125 m (12/12 points inside half a robot width, n = 3 per
  frame), including the pair 0.25 m apart — so the image is readable to it and
  still does not move the decision. Consequence for the preregistration: for
  this scenario and prompt the `gemini` Arm A cell is **equivalent to a
  text-only reasoner**, which must be stated wherever its decisions are
  reported. Follow-ups this probe did not run: the same 2x2 on a prompt that
  asks the model to verify the states against the image, the same probe on the
  `openai` cell, and pointing on raw (un-annotated) frames.
- **RESOLVED (Rev 6, 2026-09-18): two of those three follow-ups ran.** (i) The
  cross-check prompt variant (`include_visual_crosscheck`, default `False`)
  inverts ER-2's incongruent cells to 10/10 image-consistent at n = 5 while the
  Fix-B regression cell stays no-congestion 5/5 — so Rev 5's null result was
  caused by this project's prompt, not by a model that cannot use the image.
  (ii) The same 2x2 against `openai`/`gpt-4o` at its pinned temperature 0.0
  reproduced the null result 6/6, making the text-tracking finding
  apparatus-wide. Report:
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md` (Experiments 4–5);
  artifacts `data/logs/er2_grounding/grounding_run3_{xcheck_off,xcheck_on,gpt4o_off}.jsonl`.
  Still open: pointing on raw (un-annotated) frames; the cross-check variant
  against `gpt-4o`; and the type/strategy drift to `anomaly` +
  `priority_override` that makes the cross-check flag unfit for production use
  as it stands. Prereg consequence: any reported Arm A cell must now state
  **which prompt variant produced it**, and the "equivalent to a text-only
  reasoner" caveat applies to the `openai` primary cell as well as `gemini`.
- **NEW (Rev 3, from landing `GeminiBackend`; status updated Rev 4,
  2026-09-18): `AnthropicBackend` silently drops `temperature`/`top_p`/
  `top_k` instead of recording them, and still does after Rev 4's artifact
  fix.** `AnthropicBackend.analyze` (`anthropic_backend.py:42`) omits these
  three `ReasonerConfig` fields with a code comment only ("Claude Opus 4.7+
  reject sampling parameters with HTTP 400") and never surfaces the dropped
  values in `BackendResponse.raw` or a log line, unlike `GeminiBackend`'s
  `raw["unsupported_sampling"]` + one-time WARNING (§4(a)/(b) above already
  flagged this as the same-family confound; it was not yet in this open-items
  list). Rev 4 closed the artifact half of this gap generically —
  `ReasonerDiagnostics.unsupported_sampling` and `write_reasoner_log` read
  from `BackendResponse.raw` for *any* backend, so `AnthropicBackend` would
  get the same JSONL visibility `GeminiBackend` now has the moment it started
  populating that key — but `anthropic_backend.py` remains untouched (out of
  scope for both the `gemini` backend task and this artifact-visibility
  task), so its `raw` never carries the key and its diagnostics
  `unsupported_sampling` is `None`, indistinguishable from "backend honoured
  everything." The `anthropic` and `openai` cells therefore still have
  asymmetric confound visibility. Any prereg table addressing §4(b)'s
  missing-temperature confound should also flag that `anthropic`'s version of
  it is invisible in its own run artifacts.

**Modality condition.** `scripts/probe_gemini_er2.py` builds its
`ReasonerRequest` with `include_pairwise_geometry` at its production default
(`True`), so the gate result reflects the dual-channel-with-derived-geometry
condition, not the geometry-off ablation condition (rev-8 spec 8.5). A future
reader of the probe's output should read the gate as scoped to that one
modality, the same way the parent spec's research answer is scoped to its
pre-registered model/prompt conditions.

**Second modality axis (Rev 6, 2026-09-18).**
`ReasonerRequest.include_visual_crosscheck` is an independent, opt-in axis
alongside `include_pairwise_geometry`, default `False`. It is a **diagnostic
ablation, not a pre-registered condition**: every gate and live-run result in
this document was produced with it off, and the off-variant prompt is
byte-identical to the pre-flag prompt (pinned by SHA-256 in
`tests/unit/test_prompt_builder.py`). The axis is recorded in the parent spec's
"Modality-condition input table (Arm A)" with `—` in all three registered
columns for that reason. It is *not* a substitute for the `image-only`
condition: it changes how the prompt ranks two channels that are both present,
rather than withholding one.
