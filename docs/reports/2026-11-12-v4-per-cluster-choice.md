# v4 Grounding-First Per-Cluster Choice: Design, Ceiling and Naive Chooser

**Prepared:** 2026-11-12

**Revision history:**

- Initial draft: `grounding_first_per_cluster` variant, zero-cost ceiling, fixed first-option-per-group chooser, joint-feasibility and single-dispatch finding, replay commands not run.

---

## Scope

This report covers v4 lever 3, a per-cluster choice for the grounding-first
`replay` variant of the offline bench (`docs/specs/v4_vlm_bench.md`, Rev 2).
It follows the v2 report (`docs/reports/2026-10-24-v4-gf-cluster-candidates.md`,
Rev 2), whose finding motivated it: with one option list and one choice, the
models covered 6-9 of 61 two-cluster positives and 1-2 of the 44 whose clusters
fall in different observed groups, and ER-2 answered "none" on 21-22 of 137.

- **Hypothesis.** Forcing one decision per observed group, with the group
  labels as the answer's required keys, removes that under-selection.
- **Zero API calls.** No key was loaded and no network backend ran. The
  chooser runs use the zero-network `FixedGroupChoiceBackend`, with caches in a
  scratch directory, never under `data/bench/cache`.
- **Exploratory v4 only.** Nothing here pools with or replaces any prereg-v3
  confirmatory measure (A32-A36).
- **Items.** The same 187 items as every v4 report: `items_live31.jsonl`,
  md5 f1dc2ccb (137 recorded positives).
- **Code.** `benchmarks/vlm_bench/variants/per_cluster.py` (variant, contract,
  joint check), `variants/per_cluster_report.py` (GT-scored report) and
  `scoring.score_group_decisions`, commit d4ae78d; tests
  `tests/unit/test_vlm_bench_per_cluster.py`, commit 510faca; yielder and
  oracle tie-order fix with its tests, commit 89df9fc. Existing variants and
  generators are unchanged and stay the default.

---

## Design

### Slots

The variant reuses the v2 observed grouping and the v2 option list. It never
reads `item.gt`; a test replaces `gt` with an object that raises on any
attribute access and gets identical slots and joint checks.

- **One slot per observed group.** A slot holds exactly the options v2 lists in
  that group's section, in v2 order: group yields, group reverse, in-group
  pairs, reroutes, partial pairs (one robot in the group, one in no group), then
  waits. Each option was probed with the real offline M3 and kept only when it
  executes as asked (v2 rule, unchanged).
- **Span pairs are not offered.** Choosing one option in each group is this
  variant's way of naming both groups.
- **Robots in no group get no slot** (v2's default `--gf-offgroup drop`). They
  still appear in partial-pair options.
- **No-group fallback (deviation, kept from v2).** On a scene with no observed
  group, v2 keeps the outside section whatever the flag says. Here that section
  becomes the single slot `outside`, so the model still has options. This
  applies to 4/187 items, 2 of them recorded positives.
- **Per-group `none_feasible`.** Every slot accepts `none_feasible`. All slots
  `none_feasible` is a negative answer.

### Option Ids

- **Default `numbered`.** v2's global 1-based numbers, so the option text and
  numbers are those of an R5/R6 prompt; only the "none" line and the answer
  instruction change. This keeps one change against R5a/R6a.
- **Flag `--option-ids opaque`.** A per-item token: a letter plus 3 base32
  characters of sha256(`item_id:executed_key_v2`), longer only on a collision
  (none on these items). It follows the option, not its position, under
  `--shuffle-options`. The resource scan suggests opaque ids against position
  priors; that claim is unverified secondary material, and opaque ids are a
  second change relative to R5/R6, so the choice is listed under Owner Rulings.

### Prompt and Answer Contract

- **Prompt.** The live prompt verbatim, then the v2-style header, a header per
  group ("Group A: robot_1, robot_3, robot_4 (options 1-6)"), its options, a
  `none_feasible` line per group, and the instruction. The instruction names the
  required keys and adds one machine-readable line,
  `Answer keys and allowed ids: {"A": ["1", ..., "none_feasible"], ...}`.
- **Contract.** The reply's JSON object must carry `choices`, whose keys are
  exactly the slot labels. It is validated against a per-item model from
  `pydantic.create_model`: frozen, `extra="forbid"`, one required
  `Literal[ids..., "none_feasible"]` field per slot. A missing group, an extra
  key, or an id from another group fails. Integer ids are read as strings for
  numbered ids; nothing else is coerced.
- **Re-ask.** A failure is re-asked with the production `build_reask_prompt`,
  up to the backend's `max_attempts`, then `decision=None`,
  `parse_status="failed"`. Backend errors back off as in the v1/v2 variant.
- **Backend-agnostic.** Prompt building, parsing and validation live in the
  variant; no backend code changed.

### Schema Delivery per Backend

Neither backend can take a per-item schema through the existing interface, so
the sanctioned fallback is used for both: prompt-stated keys plus strict
validation.

| Backend | How a response schema reaches the provider today | Per-item required keys possible without live changes |
|---|---|---|
| any (`VLMBackend.analyze(payload, config)`) | `PromptPayload` has no schema field (`reasoning/vlm/models.py`) | no |
| `gemini` (`GeminiBackend`) | `force_schema` loads one static schema (`reasoning/schemas` `vlm_decision`) at construction and sends it as `response_format`; `force_schema: false` in `config/models.yaml` | no: static per instance, and off on the pinned arm |
| `anthropic` (`AnthropicBackend`) | no schema or structured-output field is sent; text only | no |

Sending a per-item schema would need a schema field on `PromptPayload` (a
shared live contract) and adapter changes, which the brief excludes. The
R1-R6 runs also used prompt-stated formats only, so this keeps the delivery
like-for-like.

### Scoring a Multi-Group Answer

The bench scores one decision per item. `scoring.score_group_decisions` keeps
rows comparable with R1/R2/R4a/R4b/R5/R6 on the 137 basis:

- Each chosen decision is grounded alone with `score_item`. No merged decision
  is ever grounded, because M3 would ground a different command or refuse it.
- **Involved** = the union of the chosen options' robots, in slot order.
  Coverage, per-cluster recall, the A33(6) matched conflict and matched F1 are
  computed on that union with the existing functions and denominators.
- **M3 feasibility** = every chosen option feasible; the first refusal is kept.
- **Strategy** = the chosen strategies joined with `+` in slot order.
- **Yielder** (and its M3-oracle, live-shadow and MC agreement): the chosen
  yield containing the MC first-conflict pair, else the one sharing most robots
  with the matched conflict. When no chosen yield shares a robot with the
  matched conflict, the row has no yielder: that yield resolves another
  cluster, and a single-decision run would name none there either. With no
  matched conflict, the first chosen yield. With one chosen option this equals
  `score_item` (tested). The no-overlap case occurs on 7 naive-chooser rows and
  5 oracle-`coverage` rows of the 137; none of them has an MC reference, so the
  MC column is unaffected.
- **Extras** (GT side, report module only): `none_feasible` per slot; spurious
  commands, a chosen option naming no robot of any active GT cluster; and
  per-cluster best-option F1, the mean over active clusters of the best F1 of
  any one chosen option.
- **Union F1 drops mechanically.** On a split item the union names two
  clusters, but matched F1 compares it with one matched conflict.
  `match_analysis` (A33(6)) picks, among the conflicts whose window contains
  the item time, the one sharing most robots with the union, then one already
  started (latest onset), else the earliest upcoming. The per-cluster
  best-option F1 is reported beside it for that reason.
- **Analysis gotcha.** `analysis_20261023/analyze.py`'s strict check re-grounds
  `ItemScore.decision`; for per-cluster rows that dict is the union record, not
  a decision. Use `data/bench/v4/analysis_20261112_pc/analyze_pc.py`
  (untracked), which re-grounds each `group_decisions` entry.

### Existing Behaviour Unchanged

- `candidates` v1 output md5 ee3943f0 and v2 default md5 a84e4444, both
  regenerated in this tree and equal to the published values.
- The whole bench suite passes (143 tests; 108 before, 35 new). One existing
  assertion changed: the registry list test now includes the new variant name.
- `replay` rejects `--option-ids opaque` on other variants and section flags
  other than `drop` on this one.

---

## Ceiling on the 137 Recorded Positives (Zero Cost)

The command was `python -m benchmarks.vlm_bench candidates --generator
per-cluster` at git 89df9fc. Output:
`data/bench/v4/candidates_gf_pc.{jsonl,md}` in the worktree
`vgu-vlm-swarm-v6c` (jsonl md5 f333fb8e, untracked). The oracle scores every
combination of one option or `none_feasible` per slot. Ties keep the earlier
combination: `none_feasible` comes first in each slot, so a tie keeps fewer
commands, and single choices run in v2 option order, as v2's oracle does.

### Slots and Options

| Recorded positives (137) | Value |
|---|---|
| Slots per item | 1 slot: 92; 2 slots: 45; no item has 3 |
| Of these, `outside` fallback | 2 |
| Options per slot | mean 11.8 (median 11, range 1-29) |
| Options per item | mean 15.7 (median 15, range 7-29), equal to v2 default |
| 2-slot items by stratum | split 38, touch 7 |
| 1-slot items by stratum | one cluster 76, touch 10, split 6 |

The 6 one-slot split items have one cluster in the group and the other among
robots in no group; partial-pair options reach it.

### Oracle Ceilings Next to v1 and v2

Rule `coverage` = coverage, then matched F1, then mean recall; `f1` = matched
F1, then coverage; `match` = Jaccard of the chosen robots with the union of the
active clusters, then coverage, then matched F1 (the v2 report's rules).
`single` restricts rule `coverage` to at most one non-none slot, which is v2's
single choice over the same options. M3 feasibility is 1.000 in every row, by
construction.

| Set (137 recorded positives) | Rule | Coverage | Mean cluster recall | Involved F1 matched | Per-cluster best-option F1 | Yielder vs MC |
|---|---|---|---|---|---|---|
| v1 | coverage | 1.000 | 0.548 | 0.672 | n/a | 0.778 (14/18) |
| v2 default (drop span) | coverage | 0.766 | 0.704 | 0.899 | n/a | 0.900 (18/20) |
| v2, keep span | coverage | 1.000 | 0.688 | 0.779 | n/a | 0.875 (14/16) |
| per-cluster, `single` (self-check) | coverage | 0.766 | 0.704 | 0.899 | 0.762 | 0.900 (18/20) |
| per-cluster | coverage | **1.000** | **0.891** | 0.856 | 0.889 | 0.947 (18/19) |
| per-cluster | match | 0.978 | 0.922 | 0.858 | 0.901 | 0.833 (20/24) |
| per-cluster | f1 | 0.620 | 0.683 | **0.966** | 0.759 | 0.957 (22/23) |

- **Self-check.** `single` reproduces the v2-default coverage-rule ceiling
  exactly: coverage, recall, matched F1 and MC 18/20. A first version broke
  ties in a different order and gave MC 14/16 with the other three equal;
  enumerating single choices in v2 option order restored 18/20 (commit
  89df9fc), which confirms the tie order was the only difference.
- `none_feasible` slots chosen by the oracle: 4/182 (coverage), 0/182 (match),
  44/182 (f1). Spurious commands: 0 in every oracle row.

**Coverage by active GT cluster count** (rule `coverage` unless named):

| Set | 1 cluster (76) | 2 clusters (61) | 2 clusters, one group touches both (17) | 2 clusters, split across groups (44) |
|---|---|---|---|---|
| v1 | 76 | 61 | 17 | 44 |
| v2 default | 76 | 29 | 17 | 12 |
| v2, keep span | 76 | 61 | 17 | 44 |
| per-cluster | 76 | **61** | 17 | **44** |
| per-cluster, rule `match` | 76 | 58 | 17 | 41 |
| per-cluster, rule `f1` | 76 | 9 | 9 | 0 |
| per-cluster, `single` | 76 | 29 | 17 | 12 |

### Is the Hypothesis Killed?

No. On the 44 split items the per-group ceiling is 44/44 against v2's 12/44,
and every split item is reachable (no active cluster lies wholly outside the
listed options). The test is weak, though: per-group choice is a superset of
v2-default single choice over the same options, so its oracle cannot be below
v2 by construction. It reaches the keep-span coverage ceiling (1.0) while
keeping a higher recall (0.891 vs 0.688) and matched F1 (0.856 vs 0.779). It
cannot reach v2-default's matched F1 under rule `coverage` (0.856 vs 0.899),
because the union is compared with one matched conflict. The per-cluster
best-option F1 (0.889) shows the options themselves still fit their clusters.

---

## Naive Chooser (Zero-Network, First Option in Every Group)

The command was `replay --prompt-variant grounding_first_per_cluster
--fixed-group-choice first --backend gemini` with a scratch `--cache-dir`, at
git 89df9fc. Every base prompt reproduced its stored hash (0 skipped), with
165 cache misses and 22 hits, as in R5/R6. The opaque-id run
(`--option-ids opaque --backend anthropic`) chose the same options on 187/187
items and scored identically; it had 187 misses and 0 hits, because opaque ids
are item-specific. The replay rows equal the report module's "first" rows on
all 187 items. Files: `data/bench/v4/run_pc_fixed_first{,_opaque}.*`
(untracked). The jsonl md5 varies between runs only in `latency_ms`.

| 137 recorded positives | Recorded ER-2 | v1 option 1 | v2 option 1 | R5a ER-2 GF v2 | R6a Sonnet GF v2 | Per-cluster first in every group |
|---|---|---|---|---|---|---|
| valid / positive | 137 / 137 | 137 / 137 | 137 / 137 | 137 / 116 | 137 / 137 | 137 / 137 |
| M3 feasibility | 0.496 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 (137/137; 182/182 options strict) |
| cluster coverage | 0.686 (94) | 0.526 (72) | 0.672 (92) | 0.496 (68) | 0.620 (85) | **0.949 (130)** |
| mean per-cluster recall | 0.710 | 0.423 | 0.618 | 0.500 | 0.621 | **0.827** |
| involved F1, matched (n) | 0.911 (136) | 0.733 (124) | 0.802 (136) | 0.850 (116) | 0.861 (137) | 0.771 (136) |
| involved F1, unconditional | 0.904 | 0.663 | 0.796 | 0.720 | 0.861 | 0.765 |
| per-cluster best-option F1 | n/a | n/a | n/a | n/a | n/a | 0.791 |
| yielder vs MC first conflict | 0.467 (7/15) | 0.759 (22/29) | 0.793 (23/29) | 0.875 (21/24) | 0.875 (21/24) | 0.828 (24/29) |
| coverage: 1 / 2 / touch / split | n/a | n/a | n/a | 60 / 8 / 6 / 2 | 76 / 9 / 7 / 2 | 75 / 55 / 16 / 39 |
| `none_feasible` slots / spurious commands | n/a | n/a | n/a | n/a | n/a | 0/182 / 1 |

The R5a and R6a columns were recomputed with this tree's analysis script and
equal the v2 report's Rev 2 table.

- **Coverage becomes cheap.** With `min_overlap = 1`, any answer in every slot
  names every group, and the observed groups agree well with the GT clusters
  (partly by definition, as the v2 report notes). A chooser with no
  intelligence covers 130/137 and 39/44 split items. Under this variant
  coverage measures little; recall, per-cluster best-option F1, the
  `none_feasible` rate and spurious commands are the informative metrics.
- **Uncovered by the naive chooser:** 7 items. Six have a single slot (5 split,
  1 touch) whose first option does not name both clusters; one is a one-cluster
  item on the `outside` fallback slot.
- **Matched F1 falls** (0.802 for v2 option 1, 0.771 here) for the union
  reason above. The naive chooser's per-cluster best-option F1 (0.791) is below
  the oracle's 0.889.
- **Over all 187 items** the naive chooser covers 177/185 (v2 option 1: 99/185),
  with recall 0.866. The two items with no active GT cluster are both answered
  positive, as v2 option 1 does.

---

## Joint Feasibility and Single Dispatch

Each option is probed feasible on its own. Two commands issued together may
conflict, and the live pipeline would not issue them together.

### What the Live Pipeline Does (Read, Not Modified)

Verified in the code:

- **One decision per analysis.** `CongestionDecision` carries one strategy, one
  involved set and one yield robot (`reasoning/vlm/models.py`).
  `ground_reasoner_result` turns one `ReasonerResult` into one command dict
  (`reasoning/rag/command_grounder.py`).
- **One command per outcome.** `PipelineOutcome.grounded_command` is a single
  dict (`swarm_orchestrator/models.py`). `OrchestratorStateMachine` is a
  "single in-flight reasoning cycle": only `MONITORING` starts an analysis, and
  `on_outcome` returns one `DISPATCH` directive. `_dispatch` publishes the one
  command from `registry_dispatch(outcome)`, fanned out per action under one
  `command_id` (`orchestrator_node.py`, `reasoning_pipeline.fan_out_command`).
- **One event per scene.** `CongestionDetector.update` returns one
  `CongestionEvent` whose `involved_robots` is every stalled robot in the
  scene, not one event per cluster (`congestion_detector.py`). A two-cluster
  scene is therefore one analysis.
- **Busy gate.** `on_event` suppresses an event when any involved robot is in
  an unresolved dispatched command or in cooldown (`state_machine.py`).
- **Plan channel represents, but does not dispatch, a scene-wide plan.** With
  `plan_channel_enabled` (true in all 187 item overlays; a live plan block on
  137), `InProcessPipeline` runs `verify_and_repair_plan`, which returns a
  complete scene-wide leg list (one `{robot_id, action}` per robot; actions
  yield, reverse, cross, wait, reroute, continue), and `PlanTracker` tracks it.
  The command dispatched is still the decision's one `grounded` command,
  tagged with the `plan_id`; `dispatch_matches_plan` records whether it matches
  the plan. No code path dispatches the other legs.
- **Precedent for several commands from one decision.** `junction_clear`
  dispatches later phases from M5 without a new M2 call
  (`_dispatch_junction_phase`, `JunctionPhaseQueue`, behind the same flag). It
  is specific to `junction_clear`.

Inferred, not verified:

- Whether `verify_and_repair_plan` would keep a plan with yields in two groups:
  it audits the plan against the decision's own fields, which name one
  strategy; this was not tested.

- A per-group answer would need either a live change to dispatch several
  commands from one outcome, or sequential cycles. With sequential cycles, once
  group A's command is out, the next event names A's robots whenever they are
  still stalled, and is suppressed until that command resolves. So group B
  would likely wait for A's command, and group B's chosen option would be
  discarded and re-asked on a later scene. Whether A's robots stay in the
  stalled set while they execute was not checked.

### What Offline M3 Checks and What It Does Not

M3 grounds each command alone. It never sees another chosen command. Its A26
retreat shield holds bystanders whose route crosses a yield's retreat, but it
reads their task intents, not another command's motion. `joint_check`
(`variants/per_cluster.py`) adds the following on the scene and the grounded
commands, never GT, and filters nothing:

| Tier | Check | Basis |
|---|---|---|
| Exact | the same robot addressed by two chosen commands, a hold in one and a move in the other included | grounded actions |
| Exact | two yield retreat points closer than `safety_radius_m` (0.45 m) | grounded `retreat_x_m`, `retreat_y_m` |
| Heuristic | a motion segment of one command within 0.45 m of the other command's segments or addressed robots | yield backup and pull-off (`retreat_corridor`), passer escort lines (escort heading and distance), reverse backups along the heading, reroute polylines |
| Not checked | timing and order; passers' Nav2 paths after the escort; swept footprints (centrelines only); M4 safety-monitor interaction; whether M5 would dispatch both | |

Results on the 137 recorded positives:

| Chooser | Items with ≥ 2 commands | Shared robot | Retreat clash | Path proximity (heuristic) | Any |
|---|---|---|---|---|---|
| Oracle, rule `coverage` | 41 | 2 | 2 | 6 | 7 |
| First in every group | 45 | 5 | 2 | 10 | 11 |

The exact conflicts are of three kinds:

- **Same retreat cell.** E26 `3b37822b` and `3627ad58`: the two groups'
  yields park 0.16 m and 0.41 m apart, inside the 0.45 m safety radius.
- **Shield hold vs move.** E18 `e0783ffa`, and E26 `3627ad58`: group B's yield
  holds a robot of group A (the A26 shield) while group A's yield passes it.
- **Shared partial-pair robot.** E17 `51f90185`, `a0f42386`, `4710c25c` under
  the naive chooser: robot_1 is in no group and appears in a partial pair of
  each group.

So 7 of 41 oracle multi-command answers, and 11 of 45 naive ones, would put
two commands in conflict or near-conflict if issued together. The exact checks
cover 3 and 6 of them. Nothing here shows the other combinations would execute
jointly; they are only not flagged.

---

## Prompt Size, Cost Estimate and Replay Commands (Not Run)

**Prompt size.** Mean composed length, system plus user, over the 187 rebuilt
prompts: v2 default 10,133 characters; per-cluster numbered 10,548 (×1.041);
per-cluster opaque 10,620 (×1.048).

**Cost estimate.** Formula only, in the earlier reports' method. It scales the
Rev 2 actuals by the prompt-length ratio, and by billed calls for opaque ids
(187 instead of 165, since opaque prompts never repeat). Output tokens may grow
a little with the `choices` object; re-asks on invalid choices would add calls.
These are not invoices.

| Run | Basis | Billed calls | Est $ |
|---|---|---|---|
| R7a ER-2, per-cluster, numbered | R5a $1.272 × 1.041 | 165 | ~1.32 |
| R7b Sonnet 5.5, per-cluster, numbered | R6a $2.546 × 1.041 | 165 | ~2.65 |
| ER-2, opaque ids (optional) | R5a × 1.048 × 187/165 | 187 | ~1.51 |
| Sonnet 5.5, opaque ids (optional) | R6a × 1.048 × 187/165 | 187 | ~3.02 |
| R7a + R7b | | 330 | **~3.97** |

**Commands.** Run from the repo root with the repo venv and the pyproject
`PYTHONPATH`. They need the owner's API keys in the environment. They were not
run.

```bash
python -m benchmarks.vlm_bench replay --backend gemini \
  --prompt-variant grounding_first_per_cluster --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r7a_er2_pc.jsonl --summary data/bench/v4/run_r7a_er2_pc.md \
  --cache-dir data/bench/cache/r7a
python -m benchmarks.vlm_bench replay --backend anthropic \
  --prompt-variant grounding_first_per_cluster --items data/bench/v4/items_live31.jsonl \
  --out data/bench/v4/run_r7b_sonnet55_pc.jsonl --summary data/bench/v4/run_r7b_sonnet55_pc.md \
  --cache-dir data/bench/cache/r7b
python data/bench/v4/analysis_20261112_pc/analyze_pc.py run_r7a_er2_pc run_r7b_sonnet55_pc
```

Add `--option-ids opaque` (with a new `--out` and `--cache-dir`) for the
opaque-id arm. The run `.md` summaries compute coverage over each run's own
positives; read the 137-item rows from the analysis script.

---

## Owner Rulings Needed

- **Run R7a/R7b?** About $4 for both numbered-id runs.
- **Option ids.** Numbered (one change vs R5/R6, default) or opaque (also
  against position priors, about 13% more billed calls)? Or both, as a
  separate arm?
- **Primary metric under this variant.** Coverage is near-saturated by a naive
  chooser (0.949). Should recall and per-cluster best-option F1 be primary for
  R7, with coverage reported only for comparability?
- **Joint conflicts.** Keep unfiltered (current), reject choices with an exact
  conflict at validation and re-ask, or remove partial-pair options from the
  slots? Any filter makes the answer contract depend on other slots.
- **Live path.** A per-group answer is not executable in live M5 as one
  decision. Is the lever bench-only (a diagnostic of under-selection), or should
  a design note scope it live? The plan channel already carries a scene-wide
  leg list but dispatches only the decision's command; `junction_clear`'s phase
  queue is the only path that dispatches several commands from one decision.
  No live code was changed.
- **No-group fallback.** The `outside` slot repeats v2's deviation on 4 items
  (2 positives). Accept?

---

## Approximations and Limits

- **Exploratory v4 only.** Pilot and tranche-1 scenes, never pooled with or
  substituted for prereg-v3 confirmatory measures (A32-A36).
- **Tuned on the same items.** The grouping's seed and MOVING-attach rules
  were chosen after a GT-agreement sweep on these 187 items, so the slots, the
  ceiling and the naive chooser are not held-out.
- **No model was asked.** The ceiling uses GT to choose and bounds the slots,
  not a model. The naive chooser shows what the format alone yields.
- **The kill test is weak by construction.** Per-group choice contains v2's
  single choice, so its oracle cannot fall below v2.
- **Coverage is cheap here.** `min_overlap = 1` coverage rewards answering
  every group, and groups agree with GT clusters partly by definition.
- **Union F1.** Matched F1 compares the union with one matched conflict and
  penalises naming two clusters; per-cluster best-option F1 is the
  complementary view.
- **Joint check is partial.** Exact checks cover shared robots and retreat
  points only; path proximity is a timing-free centreline heuristic.
- **Yielder rule.** One yielder per row, chosen by the MC pair, then overlap.
  Other chosen yields are not scored against any reference.
- **Text-only.** Replays will use the neutral grey image, as R1-R6.
- **Output files.** `data/bench/` is gitignored. This report's files live in
  the worktree `vgu-vlm-swarm-v6c` (`data/bench/v4/candidates_gf_pc.*`,
  `run_pc_fixed_first*.*`, `analysis_20261112_pc/analyze_pc.py`), with copies
  of the items and R1-R6 run files taken from `vgu-vlm-swarm-v6a`.
