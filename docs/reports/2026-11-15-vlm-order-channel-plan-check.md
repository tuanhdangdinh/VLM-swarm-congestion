# VLM Order-Channel Plan Check: Prompt v3.5 and Paid Offline Replay

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: prompt v3.5 condition, paid offline replay on 20 recorded IB10 snapshots (ER-2, Sonnet 5.5, gpt-4o), go/no-go inputs and demo runtime delta.

---

## Summary

- **What changed.** A new, default-off prompt condition, `prompt_plan_grammar_rules` (prompt v3.5), adds two generic sentences to the plan grammar. A startup log line names the plan-order condition. No grounding, verification, parser or safety code changed.
- **Prompt pins.** The default prompt is byte-identical to v3.4 (all pins hold), and the unit suite fails exactly as the base does.
- **Paid check.** It used the shipped `Reasoner` on recorded frames. Every answer was then replayed offline through `InProcessPipeline._run_from_result`, with `plan_dispatch_order_source` at `chi`, at `model_when_verified`, and with no plan.
- **ER-2, the demo model**, 40 calls per condition (2 replicates of 20 stimuli):
  - **A:** 2 of 40 verbatim. One of the 38 first-trigger answers changed the dispatched recede order, and that one fails `dispatch_matches_plan` (yielder gap).
  - **B:** 2 of 40 verbatim. One of 38 changed the order, and it matches dispatch.
  - **Per-episode chance:** about 1 in 38 (2.6 %) in each condition. Over 5 takes that is about 12 % (inferred).
- **Why ER-2 rarely verifies.**
  - Under A, it still names robots twice (11 of 40 plans nulled) and reverses a yield-axis robot (51 structural edits).
  - Under B, it gets the recede pair right in 29 of 31 plans but writes two `cross` legs and no releasing `yield` (23 of 29), so the plans are repaired.
  - B also introduces a new failure: ER-2 copies the options block's detail text as the action (`"reverse (north arm)"`), and the parser nulls 9 of 40 plans.
- **Sonnet 5.5 under B** verifies 9 of 15 and changes the order in 5 of 14 first-trigger answers. But 4 of those 5 name robot_2 as yielder, which dispatch replaces with robot_1 (`dispatch_matches_plan=false`).
- **Recommendation: no-go for an ER-2 demo under A or B as built.** The exact blocker is in section 7.

---

## 1. What Was Changed

Branch `demo/vlm-order-channel` (worktree `vgu-vlm-swarm-v7k`, from `docs/vlm-plan-influence-trace`):

| Commit | Change |
|---|---|
| `347898c` | `feat: add plan-grammar rules prompt condition (v3.5)` |
| `88397ea` | Design spec and harness, committed before the first paid call |
| `e906ac4` | `feat: log the plan-order condition at M5 startup` |

The condition:

- `_PLAN_GRAMMAR_RULES` and `_PLAN_GRAMMAR_V35` in `reasoning/vlm/prompt_builder.py`. `_PLAN_GRAMMAR` (v3.4) is untouched.
- Request field `ReasonerRequest.plan_grammar_rules` (default False; v3 template only, like the apparatus).
- Config key `prompt_plan_grammar_rules` (default False; requires `plan_channel_enabled`, via the existing apparatus validator).
- `prompt_conditions.plan_grammar_rules` in the artifact, omitted when False. Replay reconstruction is in `scripts/replay_live_decisions.py`.

The two sentences, inserted after the grammar's list-order line:

```text
Name each robot exactly once: its one leg is its whole role in the resolution.
A "cross" leg must come after the "yield" leg that releases it.
```

- Both state rules M3 already enforces:
  - the parser's repeated-robot null (`output_parser._sanitize_optional_fields`);
  - `_plan_problems`'s "cross leg has no preceding yield leg to release it" (`command_grounder.py:3859-3863`), which applies to every strategy.
- They name no robot, scene, strategy or order. A test asserts this.
- The parser's repeated-robot rule and every verification rule are unchanged.

**Why a condition, not `PromptVersion` 4.** Two existing tests assert that `prompt_version=4` is rejected (`test_prompt_builder_v2.py:86`, `test_prompt_builder_v3.py:525`). A condition keeps every existing test untouched and follows the apparatus pattern. The artifact records it as `prompt_conditions.plan_grammar_rules: true` plus a distinct `user_sha256`.

**Startup line.** M5 logs one line only when a plan-order key is off its default:

```text
plan order condition plan_dispatch_order_source=model_when_verified prompt_plan_grammar_rules=True prompt_candidate_options=False
```

With every key at its default, M5 logs nothing new.

---

## 2. Test Results (Verified)

- **New:** `tests/unit/test_prompt_plan_grammar_rules.py`, 40 tests. They cover:
  - on/off rendering on 11 fixtures (the six v3 pins and five apparatus conditions);
  - a line diff showing exactly the two sentences, inserted after the list-order line;
  - v1/v2 ignoring the flag;
  - the config validator and the artifact block;
  - replay reconstruction;
  - node wiring;
  - the startup line.
- **Pins unchanged:** `test_prompt_builder_v3.py` (six v3 pins), `test_prompt_apparatus_v3.py` (five apparatus pins plus baseline `6d08540f...`), the v1 frozen and v2 tests, and `test_dispatch_order_source.py` (26) all pass. No existing test was edited.
- **Full unit suite against the base** (same worktree before any edit; `--continue-on-collection-errors`):

| Run | Passed | Failed | Collection errors |
|---|---|---|---|
| Base (`1400533`) | 6967 | 57 | 3 |
| After `e906ac4` | 7003 at `347898c`, 4 more at `e906ac4` | 57 | 3 |

- The failure lists are identical. All failures are environmental: `pxr` absent, ArUco decoding, M6 scenario files, a congestion-detector timing test, `t2b_forced_order`, and one `write_decision_artifact` test.

---

## 3. Method of the Paid Check

Design: `docs/superpowers/specs/2026-11-15-vlm-order-channel-plan-check.md` (committed `88397ea`, before the provider probes). Runner: `scripts/vlm_order_channel_plan_check.py`. Data: `data/experiments/2026-11-15-vlm-order-channel-plan-check/`.

**Stimuli.** 20 snapshots: the 15 live ER-2 `junction_clear` snapshots the trace used, plus the 5 Arm C snapshots. Each carries its recorded scene, real frame, order, failure context and plan state.

**Integrity gate** (`stimuli.json`):

- 16 of 20 re-render byte-identically to the stored prompt.
- The 4 October snapshots differ only in template lines from earlier v3 revisions (v3.0 to v3.2). Their scene lines are identical.
- `ceff5efa` (e09) is a third trigger with a plan-state block. It is flagged and excluded from the per-episode figure.

**Conditions.**

- A = v3.4 + the two sentences.
- B = A + the existing candidate-options block, built with `build_candidate_options` exactly as M5 does.

**Backends** (as M5 resolves them from `config/models.yaml`):

- ER-2: the 2026-11-14 settings. Its adapter drops sampling fields, as it did live.
- Sonnet 5.5 and gpt-4o: their own sections.

**Offline path, real functions.** `InProcessPipeline._run_from_result` is built as M5's default pipeline from each snapshot's recorded overlay, grounding params and feasibility mode (`off`, as recorded). Each answer gets a fresh `PlanTracker` and `retreat_chooser=None`, so there are no stage-2 calls.

Each answer is run three ways:

1. flag `chi`;
2. flag `model_when_verified`;
3. same decision with `proposed_plan=None` (the no-plan default).

**Fidelity of the offline path (verified, `fidelity_recorded.jsonl`).** Replaying the 15 recorded live answers reproduces:

- the recorded provenance, 15 of 15;
- the recorded junction phases exactly, 11 of 11 November artifacts. The October artifacts store no phases.

Synthetic chi-ordered and swapped plans reproduce the trace's prototype: chi verbatim 20 of 20, swap verbatim 18 of 20, and only the recede phases move.

**Providers and spend.**

- Probes (`scripts/preflight_backend.py`, one per provider): Gemini OK, Anthropic OK, OpenAI OK. OpenAI had credits on 2026-11-15, unlike 2026-11-14.
- Calls: 129 in total, plus 3 probes.

| Arm | Calls | Stopped by |
|---|---|---|
| ER-2 | 80 (2 replicates × 20 × A/B) | complete |
| Sonnet 5.5 | 31 (16 A, 15 B) | its 0.55 sub-cap. Missing: A on the last 4 Arm C stimuli; B on those plus e02 |
| gpt-4o | 18 (9 A, 9 B) | its 0.25 sub-cap |

- No refusals, no HTTP errors, no retries.
- Ledger spend is **$1.384** of the $1.50 cap. That figure is conservative: it is the cited prices × 1.25. At the cited prices it is about $1.11.

---

## 4. Counts per Model and Condition (Verified)

"FT" means first-trigger answers (excluding e09's third trigger). Counts (6) use flag `model_when_verified`.

| Count | ER-2 A | ER-2 B | Sonnet A | Sonnet B | gpt-4o A | gpt-4o B |
|---|---|---|---|---|---|---|
| Calls | 40 | 40 | 16 | 15 | 9 | 9 |
| (1) Valid response | 40 | 40 | 16 | 15 | 9 | 9 |
| (2) `junction_clear`, all four robots | 40 | 40 | 9 (7 `yield`) | 15 | 0 (9 `yield`) | 0 (9 `yield`) |
| (3) Plan present after parsing | 29 | 31 | 16 | 14 | 9 | 9 |
| (3) Nulled: robot named twice | 11 | 0 | 0 | 1 | 0 | 0 |
| (3) Nulled: invalid action (`"reverse (north arm)"`, copied from the options block) | 0 | 9 | 0 | 0 | 0 | 0 |
| (4) `vlm_verbatim` | 2 | 2 | 2 | 9 | 2 (`yield`) | 2 (`yield`) |
| (4) `repaired` | 27 | 29 | 8 | 5 | 1 | 1 |
| (4) `m3_default` | 11 (plan absent) | 9 (plan absent) | 6 (repair bound 4) | 1 (plan absent) | 6 (repair bound 4) | 6 (repair bound 4) |
| (5) Verbatim recede order = chi | 1 | 1 | 0 | 4 | n/a | n/a |
| (5) Verbatim recede order ≠ chi | 1 | 1 | 2 | 5 | n/a | n/a |
| (6) `dispatch_order_source=model` | 2 | 2 | 2 | 9 | 0 | 0 |
| (6) Dispatched phases ≠ no-plan default (only `recede` phases differ) | 1 | 1 | 2 | 5 | 0 | 0 |
| (6) `dispatch_matches_plan` among source=model (true / false) | 1 / 1 | 2 / 0 | 0 / 2 | 2 / 7 | n/a | n/a |
| FT answers | 38 | 38 | 15 | 14 | 8 | 8 |
| FT: verbatim and order ≠ chi and phases ≠ default | 1 | 1 | 2 | 5 | 0 | 0 |
| ... and `dispatch_matches_plan` | 0 | 1 | 0 | 1 | 0 | 0 |

Per replicate, ER-2 (rep 0 / rep 1):

- **A:** verbatim 1 / 1; order changes 0 / 1.
- **B:** verbatim 1 / 1; order changes 0 / 1.

**Repair and rejection reasons**, edit counts (verified, `analysis.jsonl`):

| Reason (check) | ER-2 A | ER-2 B | Sonnet A | Sonnet B | gpt-4o |
|---|---|---|---|---|---|
| Recede set fixed by geometry: a `reverse` on a yield-axis robot, or a recede candidate without `reverse` | 51 | 2 | 16 | 0 | 0 |
| Releasing-yield order: a `cross` leg with no earlier `yield` | 11 | 30 | 5 | 6 | 0 |
| Yield refused: first passer not nearest the yielder | 0 | 0 | 0 | 0 | 1 per condition |
| Other (`wait` substituted to `yield`; cross before recede; plain reorder) | 4 | 2 | 1 | 0 | 0 |

ER-2 under B writes the right pair with two `cross` legs and no `yield` in 23 of its 29 pair-correct plans.

**(7) Safety and feasibility checks.**

- No answer reached a grounding failure. No yield refusal fired in dispatch, and no epsilon rejection occurred: every plan whose order differs from chi had a margin of 0.096 or less, below 0.15.
- The yield room gate is `off`, as in every recorded run, so it never checked anything.
- The checks that fired are M3's structural checks: recede set, releasing-yield order, first passer and repair bound. They protect the feasibility of the four-phase sequence; none is a collision check.
- M4 safety is not exercised offline.

**Swapped-order caveat**, for every verbatim plan whose order differs from chi:

| Model, condition | Episode | Plan | chi order | Margin | Verified | `dispatch_matches_plan` |
|---|---|---|---|---|---|---|
| ER-2 A rep 1 | ib10L_e05 | 4rev 3rev 2yield 1cross | 3, 4 | 0.028 | `vlm_verbatim` | false (yielder robot_2) |
| ER-2 B rep 1 | vp08 | 3rev 4rev 1yield 2cross | 4, 3 | 0.047 | `vlm_verbatim` | true |
| Sonnet A | ib10L_e07, ib10S_e05 | 3rev 4rev 2yield 1cross | 4, 3 | 0.030, 0.012 | `vlm_verbatim` | false (yielder robot_2) |
| Sonnet B | ib10L_e05 | 4rev 3rev 2yield 1cross | 3, 4 | 0.028 | `vlm_verbatim` | false |
| Sonnet B | ib10L_e07, ib10S_e09, vp08 | 3rev 4rev 2yield 1cross | 4, 3 | 0.030, 0.020, 0.047 | `vlm_verbatim` | false |
| Sonnet B | ib10S_e07 | 3rev 4rev 1yield 2cross | 4, 3 | 0.044 | `vlm_verbatim` | true |

Each was accepted within epsilon. Under the flag, only the two recede phases swap; cross, release and fallback are identical.

**Order bias (verified).** Of plans that reverse both robot_3 and robot_4:

| Model, condition | Plans | Pair listed ascending (3, 4) | Pair order = chi |
|---|---|---|---|
| ER-2 A | 15 | 10 | 5 |
| ER-2 B | 29 | 21 | 13 |
| Sonnet B | 14 | 10 | 7 |

This is consistent with ordering by robot id more often than by chi. Inferred; the data cannot separate the two.

**Recorded precedent** (verified, `gt_recede_precedent.json`, `scripts/ib10_recede_order_precedent.py`; GT centre-to-centre distances as `score_ibs.gt_min_pairwise`):

- In 23 recorded two-recede dispatches (15 live, 5 Arm C, 3 closure mock), the rank-1 (shallower-pocket) robot never began receding first: 0 of 23. Dispatch and GT agree in every case. There is no recorded precedent for the swapped temporal order.
- **Recede-window minimum separation:**
  - robot_3 first: 0.301 / 0.323 / 0.407 m (min / median / max, n = 11, 11 of 11 resolved);
  - robot_4 first: 0.309 / 0.325 / 0.392 m (n = 12, 11 of 12 resolved; e09 unresolved).
- Zero GT contacts in any recede window. Recedes never overlapped: the second starts about 10 s after the first.
- The window minimum is the standing jam separation measured before any recede. It does not show that a rank-1-first recede would be safe.
- **Side finding:** in 5 episodes (ib10S_e01, e05, e07, closure R1, P1), `plan.legs` lists the rank-1 robot's `reverse` first while dispatch was chi. The frozen scorer's `chi_pair.executed_recede` reads `plan.legs`, which is why ib10S_e01 shows `executed_order_correct: false`. Executed order must be read from the m5/m4 command order, never from `plan.legs`.

---

## 5. Should `prompt_candidate_options` Be Part of the Demo?

**From the code (verified).** At IB10 the block offers `reverse` only to robot_3 and robot_4. That targets the dominant recorded repair cause (a `reverse` on a yield-axis robot).

**From the data (verified).**

- **It works for that cause.** ER-2's structural recede-set edits drop from 51 under A to 2 under B.
- **It exposes the next blocker.** ER-2 omits the releasing `yield`, which accounts for 30 edits. The second grammar sentence does not fix this, even with `yield` listed for robot_1 and robot_2.
- **It adds a new defect.** The block renders details in parentheses (`reverse (north arm)`, `_render_option`). ER-2 copied them as the action in 9 of 40 answers, and the parser nulled those plans. Sonnet did not do this.
- **Net effect for ER-2:** B gives the same verbatim rate as A (2 of 40). It is also a construct change (constrained selection).

---

## 6. Go/No-Go Inputs (Owner Criteria)

| Criterion | ER-2, A | ER-2, B |
|---|---|---|
| (a) Structurally valid and feasible plan | Rarely: 2 of 40 verbatim (5 %). 29 of 40 plans survive parsing; 27 are repaired. | Rarely: 2 of 40 verbatim (5 %). 31 of 40 survive parsing; 29 are repaired. |
| (b) M3 accepts and executes the VLM's plan, not a silent replacement | When verbatim, the order is executed (source=model 2 of 2), but 1 of the 2 names robot_2 as yielder and dispatch yields robot_1. For the other 38 answers, M3 replaces the plan; this is recorded as `repaired` or `m3_default`, not silent. | When verbatim, 2 of 2 executed and matching. Otherwise as A. |
| (c) Executed commands differ from the no-VLM default on the same scene | 1 of 38 FT (2.6 %), recede order only | 1 of 38 FT (2.6 %), recede order only |
| (d) All checks enabled | Yes. Nothing weakened; the feasibility gate is `off` as in every recorded run (owner choice). | Same |
| (e) Validated offline with tests | Yes (section 2) | Yes |

**Per-episode chance** of "verbatim AND order ≠ chi" on a live first trigger, from the ER-2 FT answers:

| Condition | Per episode | Over 5 takes | With `dispatch_matches_plan` also required |
|---|---|---|---|
| A | 1 of 38 = 2.6 % | about 12 % | 0 of 38 |
| B | 1 of 38 = 2.6 % | about 12 % | 1 of 38 |

The 5-take figure is 1 − (1 − p)^5. It assumes independent takes and live triggers like these snapshots; it is inferred, not measured.

**For comparison, not the demo model:** Sonnet 5.5 under B reaches 5 of 14 FT order changes, but only 1 of 14 also matches dispatch, because of the yielder gap.

---

## 7. Recommendation

**No-go for the ER-2 demo under A or B as built.**

**The exact blocker.** ER-2 rarely writes a plan that verifies `vlm_verbatim` at this junction (2 of 40 per condition). Under B, the remaining cause is mechanical and dominant: ER-2 writes `cross` for both yield-axis robots instead of `yield` for one of them (23 of 29 pair-correct plans). The two generic sentences do not change that. The expected chance of a qualifying event is about 1 in 38 per episode, about 12 % over 5 takes.

**What would change the picture** (owner decisions, not done here):

- **The yielder gap.** It is the blocker for Sonnet B, the only arm with a usable rate. Closing it in verification only narrows acceptance; the trace noted this.
- **A third sentence**, for example "a `yield` leg releases each crossing", or a shorter options detail text.

Either is a new design change that would need its own offline check, about $0.35 per ER-2 round.

---

## 8. Limits

- One scene, near-identical snapshots, small n. The counts describe these 20 stimuli, not a population.
- The demo would show causal control over the recede order, not that the VLM's order is better. chi rates the two orders equivalent within epsilon on 18 of 20 snapshots, and the recorded data have no rank-1-first precedent.
- ER-2 lists the pair ascending more often than in chi order (10 of 15 and 21 of 29), which is consistent with ordering by id.
- The yielder gap is open by owner decision. 1 of 2 ER-2 A order changes and 4 of 5 Sonnet B order changes are accepted but not executed as written.
- B changes the construct being demonstrated.
- Sonnet and gpt-4o coverage is partial (sub-caps). Their Arm C coverage is the thinnest.
- ER-2's sampling fields are dropped by its adapter, as live, so replicates vary by provider sampling.
- No stage-2 calls. M4 safety is not exercised offline.

---

## 9. Verified and Inferred

| Claim | Status |
|---|---|
| All counts in sections 4 and 6 | verified: `analysis.jsonl`, `summary.json`, computed by the runtime's own pipeline functions |
| The offline path reproduces the recorded live provenance and phases | verified: `fidelity_recorded.jsonl` |
| Default prompts unchanged; suite failures identical to the base | verified |
| No rank-1-first recede in recorded GT | verified: `gt_recede_precedent.json` |
| That a rank-1-first recede is safe | not shown; inferred only from the identical end state and verification |
| 5-take chance | inferred (arithmetic) |
| ER-2 orders by robot id | inferred |

**Contradictions with the trace report.**

- The trace expected the first sentence to remove the robot-named-twice cause. Under A, ER-2 still did it in 11 of 40 answers. The trace's recorded rate was 3 of 41, but on prompt v3.4 without the sentence and over different calls, so the two rates are not directly comparable.
- The trace expected B to address the dominant repair cause. It does (51 to 2 edits), but the verbatim rate does not move, because the releasing-yield omission takes over and the options detail text introduces invalid actions.
- The trace's scorer-based view of recorded order can mislead: `chi_pair.executed_recede` reads `plan.legs`, not dispatch (section 4).
