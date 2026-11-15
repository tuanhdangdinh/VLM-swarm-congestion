# VLM Order-Channel Plan Check: Design (Paid, Offline)

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: design of the bounded paid offline check, written and committed before the first paid call (provider probes included).

---

## 1. Question

Would the VLM's own plan drive the recede order M3 dispatches on the IB10 four-robot intersection, if the existing default-off key `plan_dispatch_order_source: model_when_verified` were on and the prompt stated two generic plan-grammar rules? The check measures this offline on recorded snapshots and real frames. No simulation, no VM.

The answer feeds the owner's go/no-go for a live demo. This document does not decide go/no-go.

Background and the findings this builds on: `docs/reports/2026-11-15-vlm-plan-influence-trace.md`.

---

## 2. Conditions

Both conditions keep every grounding, feasibility, collision-avoidance and safety check of the runtime as recorded (`68e67b5` plus the three 2026-11-14 safety files). Nothing in verification or grounding is changed.

| Condition | Prompt | Config keys (on top of the recorded overlay) |
|---|---|---|
| A | v3.4 plus the two plan-grammar sentences (prompt v3.5, commit `347898c`) | `prompt_plan_grammar_rules: true` |
| B | A plus the existing verifier-candidate-options block | A + `prompt_candidate_options: true` |

The two sentences, inserted after the grammar's list-order line:

```text
Name each robot exactly once: its one leg is its whole role in the resolution.
A "cross" leg must come after the "yield" leg that releases it.
```

- B is a declared change of construct: plans under B measure constrained selection among verifier-accepted actions, not free planning (`swarm_orchestrator/models.py`, `prompt_candidate_options`).
- B's block is built exactly as M5 builds it: `build_candidate_options` with each snapshot's recorded feasibility mode and grounding parameters. At IB10 it offers `reverse` only to robot_3 and robot_4 (verified offline, trace `order_channel_v7i.jsonl`).
- Both conditions are scored offline with `plan_dispatch_order_source` at `chi` and at `model_when_verified`.

---

## 3. Stimuli

The 15 live four-robot ER-2 `junction_clear` snapshots the trace used (fidelity gate passed), plus the 5 Arm C snapshots. Each keeps its recorded scene, real frame, presentation order, failure context and plan-state block. Bundle list and request ids: `STIMULI` in `scripts/vlm_order_channel_plan_check.py`.

Integrity gate (run before any paid call, `stimuli.json`):

- The base request rebuilt through `build_reasoner_request` / `build_prompt_payload` reproduces the stored `user_sha256` byte for byte for 16 of 20: the 11 November live and the 5 Arm C snapshots.
- The 4 October snapshots (vp08, vp09, ep2, cal_ep1) were rendered under earlier v3 revisions (v3.2, v3.2, v3.0, v3.1). The unified diff of stored against re-rendered prompt touches only template lines: the list-order line, the strategy glosses, the grammar block and the `<think>` answer block. Robot states, geometry and every scene line are identical. They are kept and flagged.
- `ceff5efa` (ib10L_e09) is the episode's third trigger, not a first trigger. It carries a plan-state block. It is kept with its recorded conditions and flagged in every table.
- Frames are referenced by bundle path and SHA-256; no image is copied.

Under A every prompt grows by 143 characters (the two sentences). Under B it grows by a further 342 characters (the options block).

---

## 4. Models and Calls

Backends run through `config/models.yaml` exactly as M5 resolves them (`backend_adapter`, `load_backend_config`, `resolve_reasoner_config`) and through the shipped `Reasoner` (retry, re-ask, parse and validation). These are the settings of the 2026-11-14 intersection runs.

| Priority | Arm | Model | Reasoner settings |
|---|---|---|---|
| 1 | `gemini` | `gemini-robotics-er-2-preview` (the demo model) | shared block: temperature 0.6, top_p 0.95, top_k 20, max_tokens 2048, 2 attempts, `thinking_level: low` (as recorded in the 2026-11-14 artifacts) |
| 2 | `anthropic` | `claude-sonnet-5-5` | its section: temperature 0.0, 4 attempts, image fallback after 2 |
| 3 | `openai` | `gpt-4o-2024-08-06` | its section: temperature 0.0, 4 attempts, image fallback after 2; only if its probe shows credits |

Order of work:

1. **Probe**, one per provider, with `scripts/preflight_backend.py --backend <arm>` (one neutral-grey image and a one-line JSON instruction). HTTP 401, 402 or a quota 429 (for OpenAI, `insufficient_quota`) means the provider is skipped and reported. No retry.
2. **Round 1:** one call per stimulus per condition per model, ER-2 first, then Sonnet, then gpt-4o if probed live. A and B are interleaved per stimulus, so partial coverage stays balanced across conditions.
3. **Round 2, budget permitting:** a second replicate for ER-2 only.

Stop rules, applied per attempt by a guarding backend proxy:

- HTTP 401, 402, 403 or 429: stop the provider; record the call.
- Anthropic refusal (provider refusal channel or refusal text): record it and stop Sonnet.
- The cap or the arm's sub-cap would be exceeded by a worst-case reservation: stop cleanly before the call.

---

## 5. Budget

- **Hard cap:** $1.50 in total for this job, probes included. The ledger (`ledger.json`) is checked before every attempt, not every call.
- **Prices** (USD per million tokens, input / output):
  - ER-2: 1.00 / 5.00; thought tokens billed as output (`scripts/summarize_capability_probes_v2.py`).
  - Sonnet 5.5: 2.00 / 10.00 (`docs/reports/2026-10-06-roster-validation.md`).
  - gpt-4o: 2.50 / 10.00 (`scripts/summarize_capability_probes_v2.py`).
- The ledger multiplies each attempt's cost by 1.25, so it overstates spend.
- **Reservation before each attempt:** 5,000 input tokens plus the arm's `max_tokens` output, at the ledger rates.
- **Sub-caps** (cumulative per arm, ledger dollars):

| Arm | Round 1 | Round 2 |
|---|---|---|
| `gemini` | 0.45 | 0.95 (cumulative) |
| `anthropic` | 0.55 | none |
| `openai` | 0.25 | none |

The sub-caps keep Sonnet and gpt-4o from consuming the ER-2 replicate.

---

## 6. Records

`data/experiments/2026-11-15-vlm-order-channel-plan-check/`:

- `stimuli.json`: integrity gate, frame SHA-256, prompt SHA-256 per condition.
- `calls.jsonl`: one line per call, keyed `arm|condition|rep|request_id` (resumable). Each line holds every attempt's text, token usage and ledger cost, and the full `ReasonerResult`. No image data, no keys, no provider payloads.
- `ledger.json`: running conservative spend, by arm.
- `fidelity_recorded.jsonl`: the offline path replayed on the recorded live answers (section 7).
- `analysis.jsonl`, `tables.txt`: the offline analysis.

Requests carry only what the existing prompt builder sends. No user or project identifiers are added.

---

## 7. Offline Analysis

Every stored answer goes through the real M5/M3 path, `InProcessPipeline._run_from_result`, built as M5's default pipeline from the snapshot's recorded overlay, grounding parameters and feasibility mode. Each run gets a fresh `PlanTracker`.

Each answer is run three ways:

1. flag `chi`;
2. flag `model_when_verified`;
3. the same decision with `proposed_plan=None`, flag `chi`. This is the no-plan default on the same snapshot, the trace's counterfactual.

- `retreat_chooser=None`: a `yield` answer gets no stage-2 call (no unbudgeted spend); stage 2 is recorded as skipped.
- **Fidelity check, done before any paid call:** replaying the 15 recorded live answers reproduces the recorded provenance 15/15. It reproduces the recorded junction phases exactly on the 11 November artifacts. The October artifacts store no phases.
- **Synthetic positive control:** a chi-ordered plan verifies `vlm_verbatim` 15/15 live and 5/5 Arm C. A chi-swapped plan verifies 13/15 and 5/5, and under `model_when_verified` only the recede phases change. This reproduces the trace's `prototype_order_channel.py`.

Counts per model and condition. Counts only: no p-values, no intervals.

1. Valid response (parsed decision).
2. Strategy `junction_clear` naming all four robots.
3. Plan present after parsing. When it is nulled or absent, the reason from the model's own text.
4. Plan verified `vlm_verbatim`; otherwise `repaired` (edit reasons) or `m3_default` (rejection reason).
5. Of verbatim plans: recede order equal to chi's on that snapshot, or different.
6. With the flag on, reported separately:
   - `dispatch_order_source=model`;
   - dispatched phases differ from the no-plan default, and which phase labels differ;
   - `dispatch_matches_plan` (a verbatim plan naming another yielder fails it: the yielder gap, left open by owner decision).
7. Every answer where a check that protects safety or feasibility rejected or edited the plan, with the check named:
   - verification edits and rejections;
   - grounding failures;
   - yield refusals.

**Swapped-order caveat.** For each verbatim plan whose order differs from chi, the chi margin against epsilon (0.15) and whether verification accepted it.

**Per-episode chance.** For ER-2 and each condition, the observed fraction of first-trigger answers meeting all three of: `vlm_verbatim`, order different from chi, and phases different from the no-plan default under the flag. It is also reported with `dispatch_matches_plan` added. The 5-take figure 1 − (1 − p)^5 is arithmetic on that fraction, labelled inferred: it assumes independent takes and live first triggers like these snapshots.

**Recorded-precedent context.** From the GT of the recorded episodes: whether the rank-1 (shallower-pocket) robot ever began receding first, and the closest pairwise centre distances in episodes of each executed recede order. This uses the scorer's centre-to-centre definition (`ib10_safety/kit/score_ibs.py`). Script: `scripts/ib10_recede_order_precedent.py`.

---

## 8. Limits Declared in Advance

- One scene, near-identical snapshots, small n. The counts describe these stimuli, not a population.
- The demo would show causal control over the recede order, not that the VLM's order is better. chi rates the two orders as equivalent within epsilon on 13/15 live snapshots.
- ER-2 may order by robot id rather than by scene reasoning. The analysis reports order against chi; it cannot separate the two.
- The yielder gap stays open: a verbatim plan naming robot_2 as yielder still dispatches robot_1.
- B changes what is being demonstrated (constrained selection).
- Offline replay exercises M2 parsing and M3 verification and grounding only. M4 safety (floor, latch, waivers) is not exercised.
