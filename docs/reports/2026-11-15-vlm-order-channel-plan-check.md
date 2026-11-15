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
- **It adds a new defect.** The block renders details in parentheses (`_render_option`). ER-2 copied them as the action in 9 of 40 answers, and the parser nulled those plans. Sonnet did not do this. The block as rendered for ib10S_e03 (verified):

```text
Plan actions the system's verifier accepts for each robot in the current scene (a plan leg outside these is repaired or the plan is replaced):
- robot_1: yield, cross, wait, reroute
- robot_2: yield, cross, wait, reroute
- robot_3: yield, reverse (south arm), cross, wait, reroute
- robot_4: yield, reverse (north arm), cross, wait, reroute
```

- **Net effect for ER-2:** B gives the same verbatim rate as A (2 of 40). It is also a construct change (constrained selection).

**Decision:** on this evidence, `prompt_candidate_options` should not be part of the ER-2 demo condition. It does not raise the verbatim rate, it adds an invalid-action failure mode, and it changes what is being demonstrated.

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

**By stimulus class.** The A event is on `ib10L_e05`, a November live snapshot. The B event is on `vp08`, an October snapshot whose base prompt was re-rendered from v3.2.

| Condition | November live (`ib10L` + `ib10S`) | October | Arm C |
|---|---|---|---|
| A | 1 of 20 | 0 of 8 | 0 of 10 |
| B | 0 of 20 | 1 of 8 | 0 of 10 |

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
- Some analysis fields were added after the first answers were seen: the `invalid_leg` verdict, `model_pair_order` and the `tables` grouping. The paid calls, conditions and stop rules followed the committed design unchanged. Every count re-derives from `calls.jsonl` with `analyze` and `tables`.
- Every call took exactly one attempt and none recorded an error (verified, `calls.jsonl`).
- The startup line is unit-tested as a function (`plan_order_status_line`). Its emission by the node is wired, but no node-level test asserts the log call. The first live take should confirm it in `m5.log`.
- The two new scripts keep 11 lines over 100 characters (ruff E501), mostly the `STIMULI` table. The runtime files are lint-clean.

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

**A separate note, not a contradiction of the trace.** The trace read executed order from m5/m4 and `junction_phases`. The frozen scorer's `chi_pair.executed_recede` reads `plan.legs` instead (`scripts/coverage_scene_scores.py:1039-1057`, verified). For ib10S_e01, `plan.legs` lists `4rev 3rev` while `m5.log` dispatched `junction-recede-robot_3` first (verified).

---

## 10. Addendum (2026-11-15): Second Fix Cycle, Release-Rule Sentence

This is the second and last prompt-fix cycle for the ER-2 demo. It adds one generic grammar sentence as a new default-off sub-condition and re-runs the same offline ER-2 check. Sections 1 to 9 are unchanged.

### 10.1 Why ER-2's Plans Were Not Accepted (Cycle 1, Tabulated Before Any Change)

Source: the 80 ER-2 rows of `analysis.jsonl` (cycle 1). The raw-plan columns read the plan the model wrote (for nulled plans, `raw_plan` from its own text); the edit columns read `verify_and_repair_plan`'s edits. A plan can fail on more than one reason, so columns do not sum.

| Reason | ER-2 A (n = 40) | ER-2 B (n = 40) |
|---|---|---|
| Accepted `vlm_verbatim` | 2 | 2 |
| Plan nulled by the parser: robot named twice | 11 | 0 |
| Plan nulled by the parser: invalid action (options detail text copied) | 0 | 9 |
| Plan repaired | 27 | 29 |
| **Raw plan has a `cross` leg and no `yield` leg at all** | **30** | **32** |
| Raw plan lists its `yield` after a `cross` | 0 | 4 |
| Raw plan reverses a set other than the structural pair {robot_3, robot_4} | 29 | 11 (9 of them the invalid-action plans) |
| Repaired, edit "cross leg has no preceding yield leg" present | 11 | 29 |
| Repaired, edit "structural recede candidate" present | 22 | 2 |
| Repaired, only the releasing-yield edit | 5 | 25 |
| Repaired, only the recede-set edit | 13 | 0 |
| Parsed plans with the correct recede pair | 7 of 29 | 29 of 31 |

Most frequent repaired shapes: B `3rev 4rev 1cross 2cross` (13) and `4rev 3rev 1cross 2cross` (5); A `3rev 4rev 1cross 2cross` (4), `1rev 2rev 3cross 4cross` (3), `2rev 3rev 4rev 1cross` (3), `4rev 3rev 2rev 1cross` (3).

**Reading.**

- The one reason common to both conditions is a plan with `cross` legs and no `yield` leg: 62 of 80 answers (30 A, 32 B), plus 4 B answers that list the `yield` after the `cross`. M3 rejects every such plan (`_plan_problems`: "cross leg has no preceding yield leg to release it", every strategy). The cycle-1 sentence "A cross leg must come after the yield leg that releases it" did not prevent this. ER-2 appears to read it as conditional on a `yield` leg existing, and to treat its `reverse` legs as the release (inferred).
- Under B this is the dominant and nearly the only remaining cause: 29 of 29 repaired plans carry the releasing-yield edit, 25 of them alone.
- Under A, the recede-set error (a `reverse` on a yield-axis robot) co-occurs in 22 of 27 repaired plans, and 11 plans are nulled for naming a robot twice. A generic sentence cannot name which robots are recede candidates in a given scene, so this cause is not addressed here.

### 10.2 Pre-Registration (Written Before Any Paid Call of Cycle 2)

**The sentence** (appended after the two v3.5 sentences):

```text
A plan with any "cross" leg must also contain a "yield" leg listed before it; a "reverse" or "wait" leg does not release a crossing.
```

- It states what `_plan_problems` already enforces for every strategy: only a `yield` leg releases a `cross` leg. It names no robot, scene, strategy, arm or order, and does not say which robot yields. It is the same text for every provider.
- **Key:** request field `ReasonerRequest.plan_grammar_release_rule`; config `prompt_plan_grammar_release_rule` (default False; requires `prompt_plan_grammar_rules`); artifact `prompt_conditions.plan_grammar_release_rule`, omitted when False. With it off, every prompt is byte-identical to before, including the v3.5 prompts of conditions A and B (`user_sha256` of all 40 cycle-1 stimulus prompts re-checked).

**Conditions** (ER-2 only, `gemini-robotics-er-2-preview`, the same backend settings, the same 20 stimuli, the same runner and offline analysis):

| Label | Prompt | n | Priority |
|---|---|---|---|
| A3 | A + the release sentence (no options block) | 40 (2 replicates × 20) | 1: run first, complete |
| B3 | B + the release sentence (options block) | 40 (2 replicates × 20) | 2: run after A3; stops at the cap |

Run order: A3 rep 0, A3 rep 1, B3 rep 0, B3 rep 1. Output goes to a new directory, `data/experiments/2026-11-15-vlm-order-channel-plan-check-c2/`, so cycle-1 data stay as committed.

**Spend cap.** $0.50 at list price. The runner's ledger is list × 1.25, so the run uses `--cap 0.60` in ledger units ($0.48 at list), checked before every attempt with a worst-case reserve. Cycle 1's ER-2 calls cost $0.0065 each at list (median), so A3 is expected to complete and B3 to stop partway. Any condition with fewer than 40 billed calls is reported as partial.

**Acceptance measure.** Per condition: plans returned, structurally valid (plan present after parsing), accepted `vlm_verbatim` (flag `chi`, as cycle 1), and, of the verbatim plans, how many have a recede order that differs from chi on the same scene, with `dispatch_matches_plan` for those. Secondary: the count of answers with a `cross` leg and no earlier `yield` (the targeted reason). The comparison is descriptive against cycle 1 (A 2/40, B 2/40); no significance test.

**Ceilings declared in advance**, so a low A3 count is not read as the sentence failing:

- A3: if the sentence fixed every releasing-yield failure and nothing else, A's 2 verbatim + 5 yield-only repairs give about 7 of 40. The recede-set and robot-twice causes remain.
- B3: the 9 invalid-action nulls remain, so about 27 of 40 at most (2 verbatim + 25 yield-only repairs).

No grounding, verification, parser or safety code changes. This is the last cycle; there is no third.

### 10.3 Results (Verified, Cycle 2)

Data: `data/experiments/2026-11-15-vlm-order-channel-plan-check-c2/` (`calls.jsonl`, `analysis.jsonl`, `summary.json`, `tables.txt`, `ledger.json`, `stimuli.json`). Code: `edeb98c` (sub-condition), `bcdb569` (pre-registration and runner conditions, committed before the first paid call).

**Integrity (verified, free).** The 20 stimuli re-render exactly as in cycle 1 (16 of 20 byte-identical to the stored prompt; the same 4 October template differences). The cycle-1 A and B prompts reproduce for all 80 ER-2 calls (`user_sha256` 80 of 80). The release sentence adds 133 characters to every A and B prompt.

**Run.** A3 complete (40). B3 **partial: 29 of 40** (rep 0 complete, rep 1 the first 9 stimuli), stopped by the pre-registered cap before the 30th call. One B3 attempt timed out at 120 s and the Reasoner's retry succeeded (`ib10L_e03` rep 1, 2 attempts). No refusals, no HTTP errors.

| Count (ER-2) | A (cycle 1) | B (cycle 1) | **A3** | **B3 (partial)** |
|---|---|---|---|---|
| Calls billed | 40 | 40 | 40 | 29 |
| Plans returned (valid response) | 40 | 40 | 40 | 29 |
| Strategy `junction_clear`, all four robots | 40 | 40 | 39 (1 `none`, e09 third trigger) | 29 |
| Structurally valid (plan present after parsing) | 29 | 31 | 36 | 27 |
| ... nulled: robot named twice | 11 | 0 | 3 | 0 |
| ... nulled: invalid action (options detail text) | 0 | 9 | 0 | 2 |
| ... null plan / not congestion | 0 | 0 | 1 / 1 | 0 |
| Targeted reason: `cross` with no earlier `yield` (raw plan) | 30 | 36 | 19 | 11 |
| Recede set other than the structural pair (raw plan) | 29 | 11 | 27 | 5 |
| **Accepted `vlm_verbatim`** | **2** | **2** | **6** | **14** |
| `repaired` | 27 | 29 | 30 | 13 |
| `m3_default` | 11 | 9 | 3 | 2 |
| Verbatim with recede order = chi | 1 | 1 | 5 | 4 |
| **Verbatim with recede order ≠ chi** | **1** | **1** | **1** | **10** |
| ... of those, `dispatch_matches_plan` true | 0 | 1 | 0 | 7 |
| All verbatim: `dispatch_matches_plan` true / false | 1 / 1 | 2 / 0 | 1 / 5 | 10 / 4 |
| First-trigger answers | 38 | 38 | 38 | 27 |
| FT: verbatim, order ≠ chi, phases ≠ no-plan default | 1 | 1 | 1 | 10 |
| ... and `dispatch_matches_plan` | 0 | 1 | 0 | 7 |

Per replicate: A3 verbatim 4 / 2, order changes 1 / 0. B3 verbatim 10 of 20 / 4 of 9, order changes 6 / 4.

**What the sentence did (verified counts; causal reading inferred).**

- It cut the targeted reason under both prompts: A 30 → A3 19 of 40; B 36 of 40 → B3 11 of 29. Releasing-yield repair edits: A3 5 of 30 repaired plans, B3 11 of 13.
- **A3 (no options block):** verbatim rose from 2 to 6 of 40, within the pre-registered ceiling of about 7. The recede-set error now dominates (26 of 30 repaired plans; parsed plans with the correct pair 10 of 36). Only 1 of the 6 verbatim plans changes the recede order, and it names robot_2 as yielder, so dispatch replaces the yielder (`dispatch_matches_plan=false`). 5 of 6 A3 verbatim plans name robot_2 as yielder.
- **B3 (options block, partial):** verbatim rose from 2 of 40 to 14 of 29. 10 of the 14 have a recede order that differs from chi; 7 of those 10 also match dispatch (robot_1 as yielder). The 4 non-matching verbatim plans name robot_2 as yielder. The invalid-action defect persists at a lower rate (2 of 29 versus 9 of 40).
- In every order change, only the `recede` phases differ from the no-plan default. Every differing order was accepted within epsilon: chi margins 0.003 to 0.096, all below 0.15.
- No grounding failure and no yield refusal in either condition. The structural checks that fired are the same as in cycle 1.

**Per-episode chance of the demo event** (FT: verbatim AND order ≠ chi AND `dispatch_matches_plan`), from these offline answers:

| Condition | Per episode | Over 5 takes (inferred, 1 − (1 − p)^5) |
|---|---|---|
| A3 | 0 of 38 | about 0 |
| B3 (partial) | 7 of 27 (26 %) | about 78 % |

**Reading against the owner criteria (section 6).**

- **A3 alone does not make the ER-2 demo viable:** the order channel fires once in 38 first triggers, and that once is not executed as written.
- **B3 does, on this evidence, but it is a construct change** (constrained selection from the options block, section 5), and its n is 29, not 40. Whether B3 is acceptable as the demo condition is an owner decision. The yielder gap (robot_2 named as yielder) still costs 4 of 14 B3 verbatim plans.
- Same limits as section 8: one scene, near-identical snapshots, small n; the demo would show causal control over the recede order, not a better order.

**Runtime delta now stale.** The md5s in `docs/superpowers/specs/2026-11-15-demo-runtime-delta.md` predate `edeb98c` for five runtime files. Current md5s: `prompt_builder.py` `a9ad857cf8355cd9f5601124b0b814b2`, `reasoning/vlm/models.py` `2025f18179c9f3b05a81072027c32637`, `swarm_orchestrator/models.py` `73f3fa4f35ceab61a5df646a71a902a6`, `orchestrator_node.py` `37a6bbadf91cb8c9def21d6f625c8bfe`, `reasoning_pipeline.py` `49fff7ab8fb460b9a94ea198cf5b523a`. A demo overlay for A3 or B3 adds `prompt_plan_grammar_release_rule: true` to the A or B fragment. The spec itself is not updated here.

**Tests (verified).** `tests/unit/test_prompt_plan_grammar_rules.py`: 79 pass (40 before, 39 new). Full unit suite: 7046 passed, 57 failed, 3 collection errors, against 7007 / 57 / 3 at `e5ea5e2`; the failure lists are identical. No existing test was edited.

**Analysis-only change.** `analyze_one` now records a `strategy: none` answer as `not_congestion` and stops, because `verify_and_repair_plan` raises on it. Cycle 1 had no such answer, so its rows are unaffected. No grounding, verification, parser or safety code changed.

**Spend (verified, `ledger.json`).** 69 billed calls, ledger $0.583 (list × 1.25), so **$0.466 at list**, under the $0.50 cap. No probe was run. The timed-out attempt is not in the ledger; whether Google bills it is unknown.
