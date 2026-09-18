# Gemini Robotics-ER 2 Integration — Design

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft: transport-surface correction (Interactions API, not the legacy `:generateContent` page), Option A `gemini` backend sketch, the no-sampling-controls reproducibility finding, Option B deferral, a cost estimate, and the probe gate.

**Status:** Design/evaluation only. No backend code lands from this document —
`reasoning/vlm/gemini_backend.py`, `reasoning/vlm/backend_factory.py`, and
`config/models.yaml` stay untouched until `scripts/probe_gemini_er2.py` (§7)
passes.

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

**(c) `thinking_level` (`low`/`high`) is a new ablation axis with no
counterpart in the other arms.** Cosmos Reason 2 (`llama_server`) has its own
chain-of-thought behavior via prompt-driven `<think>` tags at a fixed sampling
preset; `openai`/`anthropic` have no comparable knob. `thinking_level` is
Gemini-specific, changes latency and output token count (and therefore cost,
§6), and — because it is not a sampling parameter — sits outside the
temperature-pinning discussion entirely. It should be treated as its own
documented axis (a candidate value, not swept) if `gemini` is added, not
folded into "decoding" as if it were a substitute for `temperature`.

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

**Order-of-magnitude estimate only** — the probe measures the real number.
The rendered M2 prompt is ≈3 600 characters of text
(`docs/implementation_notes.md`, 2026-09-17 entry, ≈900 tokens at a rough
4 chars/token) plus one image; a generous total input estimate of
1 500–3 000 tokens and an output estimate of 200–400 tokens (JSON decision,
`thinking_level: low`) puts one analysis at roughly:

```text
input:  ~2,000 tok * $1.00 / 1e6 tok ≈ $0.002
output: ~300 tok   * $5.00 / 1e6 tok ≈ $0.0015
total:  ≈ $0.003–0.005 per analysis (order of magnitude, NOT measured)
```

— the same order of magnitude as the project's measured ≈$0.006/analysis for
`gpt-4o`. `thinking_level: high` would raise the output-token count (and
therefore this estimate) by an unknown, model-dependent factor; this is
exactly why §4(c) treats `thinking_level` as its own axis rather than a
tuning knob to set once and ignore.

---

## Open questions / gate

**The gate.** No backend code (`reasoning/vlm/gemini_backend.py`,
`reasoning/vlm/backend_factory.py`, `config/models.yaml`) lands until
`scripts/probe_gemini_er2.py` answers one question:

> Given the real M2 prompt (`reasoning.vlm.prompt_builder`) plus one scene
> image, sent to `gemini-robotics-er-2-preview` on the Interactions API with
> `reasoning/schemas/vlm_decision.schema.json` as `response_format`, does the
> response's extracted text pass the existing `reasoning.vlm.output_parser`
> (`parse_decision_text`) and produce a valid `CongestionDecision`?

A "no" is a reportable outcome for this design document, the same way a "no"
is a reportable outcome for the parent research question (rev-8 spec,
"Research objective"): it means either the schema subset needs trimming
(e.g. dropping `$schema`, which is not in the documented supported-keyword
list) before Option A is viable, or that Option A needs a looser
`response_format: {"type":"text","mime_type":"application/json"}` (no
`schema`) plus prompt-level JSON discipline like the other backends.

**Secondary, non-gating questions the probe additionally surfaces** (useful
for the follow-up implementation task, not blockers on their own):

- Which auth header actually works — `x-goog-api-key` or bearer fallback —
  so `GeminiBackend.__init__` doesn't have to guess.
- Real token usage, to replace the §6 estimate with a measured number.
- Whether `parse_vlm_decision` (strict jsonschema check against the same
  schema file) and `parse_decision_text` (tolerant, `<think>`-stripping)
  agree — if `--schema` output passes the tolerant parser but fails the
  strict one, that is evidence the model isn't honoring the schema exactly
  even when asked to, which matters for a chain-of-thought-style
  `thinking_level: high` run more than a `low` one.

**Modality condition.** `scripts/probe_gemini_er2.py` builds its
`ReasonerRequest` with `include_pairwise_geometry` at its production default
(`True`), so the gate result reflects the dual-channel-with-derived-geometry
condition, not the geometry-off ablation condition (rev-8 spec 8.5). A future
reader of the probe's output should read the gate as scoped to that one
modality, the same way the parent spec's research answer is scoped to its
pre-registered model/prompt conditions.
