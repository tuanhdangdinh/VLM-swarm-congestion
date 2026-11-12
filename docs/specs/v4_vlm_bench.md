# v4 Offline VLM Bench

**Prepared:** 2026-10-22

**Revision history:**

- Initial draft: purpose, data inventory, item model, metric definitions, modes, reporting.
- Rev 2 (2026-11-12): listed the implemented variants; added the `grounding_first_per_cluster` variant (per-group answer contract, schema delivery, per-group scoring, joint check) and its CLI flags.

---

## Purpose

The bench lets us iterate on the M2 prompt, input representation and model
offline. It runs against S1b scenes that were recorded live. It reuses the
production M3 grounder and the A33 GT definitions, so a candidate is scored on
what would happen downstream, not on text alone.

- **Exploratory, v4 only.** Bench numbers are never pooled with, cited as, or
  substituted for any prereg-v3 confirmatory measure (A32-A36). The scenes
  come from pilots E6-E26 and tranche 1 E27-E31. They are neither unseen nor
  representative. The bench ranks candidates; it does not estimate effects.
- **No network in `recorded` and `classical` modes.** `replay` is the only mode
  that may call a backend. It does so through the `VLMBackend` protocol, behind
  a content-hash cache.

---

## Data Source and Inventory

Bundles are the 31 live S1b episodes. Their roots are under
`vgu-vlm-swarm-v3/data/logs/vm_runs/`, untracked:

- E6-E26 are listed in `batch5/live21.txt`;
- E27-E31 are in `batch6/`. That is 5 Arm A plus 5 Arm B; E27 B is attempt
  a2, because a1 was a bring-up abort and is not an episode under A33(0).

Arm B (Layer 2 off) has no decision artifacts, so it contributes no items.
Each decision artifact `decisions/<uuid>.json` stores the following:

- the scene with registry goals;
- the rendered system and user prompt with SHA-256 hashes, the prompt version,
  the presentation order and the prompt conditions;
- `failure_context`, `last_failed_context` and the pre-analysis `plan_state`;
- `raw_text`, the parsed `decision` and `diagnostics`, which carry attempts,
  token usage, latency and the model id;
- the M3 outcome: `yield_refusal_reason`, `dispatch_withheld`,
  `dispatched_command`, the `plan` block and the `stage2` record;
- the grounding params actually used (`grounding_params_source`);
- the live `shadow_classical` record.

Each bundle also holds `orchestrator.overlaid.yaml`, `rag.overlaid.yaml`,
`m5_scene.jsonl`, `gt/ground_truth.jsonl` and the task stream.

| Batch | Episodes (Arm A) | Artifacts | Backend-failed | Frames on disk | Grounding file |
|---|---|---|---|---|---|
| E6-E11 (churn_wave, live_batch, resume) | 6 | 69 | 38 (E10) | none | `s1b_dynamic.yaml` |
| batch2 E12-E17 | 6 | 36 | 0 | none | `s1b_dynamic.yaml` |
| batch3 E18-E20 | 3 | 22 | 0 | none | `s1b_dynamic_shield.yaml` |
| batch4 E21-E23 | 3 | 14 | 0 | none | `s1b_dynamic_shield.yaml` |
| batch5 E24-E26 | 3 | 18 | 0 | none | `s1b_dynamic_shield_escort.yaml` |
| batch6 E27-E31 (Arm A) | 5 | 28 | 0 | none | `s1b_dynamic_shield_escort.yaml` |

**Frames.** No annotated or raw frame was harvested for any S1b bundle. The M5
`frame_dump_dir` (`data/logs/m5_frames`) stayed on the VM, and every bundle's
`frames/` directory is empty. The bench therefore runs text-first:

- `recorded` and `classical` need no image;
- `replay` attaches the bundle frame when `m5_frames/<request_id>.png` exists.
  Otherwise it attaches a neutral grey PNG and marks the item `image=neutral`.

Every backend adapter requires an image path. A truly image-free call would
need a backend seam, which is out of scope here.

**MC reference.** The S1 Monte Carlo first-conflict predictions are files
beside the bundles, keyed by stream seed:

- `batch2/mc_seeds_12_17.jsonl`;
- `batch3/mc_seeds_18_21.jsonl`;
- `batch4/mc_seeds_21_23.jsonl`;
- `batch5/mc_seeds_24_26.jsonl`;
- `batch6/mc_seeds_p10.jsonl`.

They cover E12-E31. MC is an upper bound (A22), used as context only.

---

## Bench Item Model

One recorded analysis (one decision artifact) is one `BenchItem`, a frozen
Pydantic model in `benchmarks/vlm_bench/items.py`. Each item is
self-contained, so scoring never re-reads the bundle.

- **Identity:** `item_id` (`<bundle>:<request_id>`), batch, episode label,
  condition tag, stream seed, rel-s time `t_s` on the A33(0) clock.
- **Inputs:** the scene robots and stamp, the stored prompt text and hashes,
  the apparatus fields needed to rebuild the `ReasonerRequest`, `frame_path`
  (null when absent), and the classical history window. The window is the
  `m5_scene.jsonl` rows in [stamp − 60 s, stamp] at the shadow's 0.25 s
  decimation.
- **Recorded answer:** `raw_text`, `decision`, `parse_status`, attempts, token
  usage, latency and model id.
- **Live M3 outcome:** refusal reason, the dispatched action kinds and the
  stage-2 status.
- **Grounding context:** the overlay dict (`orchestrator.overlaid.yaml`), the
  recorded `GroundingParams` dict, the grounding file path, the md5 of that
  file in this tree, and whether the file's params equal the recorded ones.
  Goal references and task intents are rebuilt from the task stream at the
  stamp, as M5's registry and `TaskStream.departure` would give them.
- **GT context (A33(5)):** every GT conflict episode whose matching window
  `[onset − pre_s, end + post_s]` contains `t_s`, plus the A33(6) matched
  conflict index of the recorded answer, computed by `match_analysis`.
- **References:** the live `shadow_classical` decision, and the MC record for
  the episode's seed.

---

## Scoring Metrics

All metrics are pure functions in `scoring.py` over items plus one decision
per item. A decision is the recorded answer, the classical answer or a replayed
answer. "Valid" means the decision is not null. Rates report numerator and
denominator.

1. **M3 feasibility.**
   - Domain: valid decisions with `congestion_detected = true`.
   - A decision is feasible when the real `ground_reasoner_result` returns a
     command and neither `summarize_yield_grounding(cmd).refusal_reason` nor
     `empty_reroute_fallback(cmd)` fires.
   - Inputs: the item's recorded params, the overlay's geometry, static
     obstacles, `grounding_yield_feasibility`, registry priorities, goal
     references and task intents. There is no network call and no stage-2
     choice (`retreat_choice = None`).
   - Also reported: the yield-only rate, a refusal histogram by reason class
     (the text before the first `:` after `yield refused:`), and live
     reproduction (the offline refused flag equals the live one, for recorded
     answers).
2. **Cluster coverage.**
   - A cluster is an A33(5) GT conflict episode active in the item's window:
     a connected set of robots with pairwise GT gap < 0.45 m, merged at
     `merge_gap_s` = 2.0.
   - Domain: items with ≥ 1 cluster and a valid decision.
   - An item is covered when every cluster shares at least `min_overlap` = 1
     robot with `decision.involved_robots`; a negative decision covers
     nothing.
   - Per-cluster recall is the mean of |D ∩ I_c| / |I_c| over (item, cluster)
     pairs.
3. **Involved-robot F1.**
   - This is A33(6) `f1(D, I_c)` against the conflict that `match_analysis`
     selects.
   - It is reported conditionally (matched positives) and unconditionally
     (items with ≥ 1 cluster, 0 when unmatched).
4. **Yielder agreement.**
   - Domain: yield decisions that name `yield_robot`.
   - **Geometry oracle (M3-executable set).** For each robot y in the
     decision's involved set, the same decision with `yield_robot = y` is
     grounded offline. y is executable when the grounder neither refuses nor
     swaps it, that is, when the grounded `yield` action's robot is y. This is
     the rule the S1 MC applies (`scripts/s1_grounding_replay.py`, which feeds
     echo-named pairs through `ground_reasoner_result` and counts executable
     yields).
   - The oracle agrees when the chosen yielder is in the set. `oracle_empty`
     (no executable yielder) is reported separately.
   - **Classical:** equality with the live shadow's `yield_robot`
     (`reasoning.baselines.classical_reasoner.resolve_classical`: FCFS
     passing order with commitment tiebreak, last arrival yields), when the
     shadow chose `yield`.
   - **MC:** equality with the seed's MC yielder. This applies only to items
     whose matched conflict is the episode's first GT conflict containing the
     MC first-conflict pair, and only when MC predicts `executable_yield`.
5. **False-positive rate.**
   - Domain: valid items with no cluster in their window.
   - FP rate = positives / domain. The A33(6) unmatched-positive count is
     co-reported.
6. **Plan quality (i-a)-(vi).**
   - Computed with A33(6)'s `plan_quality`, which calls
     `reasoning.rag.plan_metrics.score_decision_artifact`, over the live
     artifacts in `recorded` mode.
   - (v) is null, because no S1 order oracle exists. In `classical` and
     `replay` modes there is no live plan block, so these are null.
7. **Cost and latency.**
   - Per item: prompt, completion, thought and total tokens and `latency_ms`,
     read from the recorded `diagnostics`; null when absent.
   - Dollars come only from each bundle's `cost.log` (`est_usd /
     billed_calls`). They are never derived from token prices.

---

## Modes

- **`recorded`.** Scores the stored ER-2 answer and makes zero API calls.
- **`classical`.** Re-runs `resolve_classical` on the item's history window,
  with the bundle's `rag.overlaid.yaml` params and `shadow_classical_zones`
  and the recorded `prior_attempts`. It grounds the result like any decision.
  Agreement with the live shadow record is reported as reproduction. This is
  an Arm-C-lite reference, not Arm B: Arm B is Layer 2 off.
- **`replay`.**
  - Rebuilds each item's `ReasonerRequest` through the production
    `build_reasoner_request`. Under `baseline` the rendered user prompt must
    hash to the stored `user_sha256`, otherwise the item is skipped and
    counted.
  - Applies the prompt variant, then runs the production `Reasoner` with
    `build_backend(<id>)` wrapped in `CachedBackend`.
  - The cache key is the SHA-256 of the backend id, model id, system prompt,
    user prompt, image bytes and sampling config. Entries are stored under
    `data/bench/cache/`.
  - Variants: `baseline` (the live builder as is); `grounding_first` (an
    M3-executable option list appended, generator `--generator v1` pairs or
    `v2` options per observed group; reports
    `docs/reports/2026-10-23-v4-grounding-first-candidates.md` and
    `docs/reports/2026-10-24-v4-gf-cluster-candidates.md`);
    `grounding_first_per_cluster` (one choice per observed group, below).

**Candidate levers (listed, not implemented):**

- a geometry-in-text table;
- randomized robot order;
- a one-shot M3-feedback retry, which re-asks with the refusal reason.

### `grounding_first_per_cluster`

Code: `benchmarks/vlm_bench/variants/per_cluster.py`; GT-scored report
`variants/per_cluster_report.py`; report
`docs/reports/2026-11-12-v4-per-cluster-choice.md`.

- **Slots.** One slot per `gf-candidates-v2` observed group (scene state only,
  never `item.gt`). A slot holds exactly the options v2 lists in that group's
  section, each probed with the offline M3 and kept only when it executes as
  asked. The span section is not offered and robots in no group get no slot
  (`--gf-offgroup drop`), except that a scene with no observed group gets the
  single slot `outside` holding v2's outside section (v2's fallback).
- **Option ids.** `--option-ids numbered` (default): v2's global 1-based
  numbers, so the option text and numbers equal an R5/R6 prompt. `opaque`: a
  per-item token, a letter plus 3+ base32 characters of
  sha256(`item_id:executed_key_v2`), stable under shuffling. `--shuffle-options`
  permutes within each slot.
- **Prompt.** The live prompt verbatim, then a header per group, its options,
  a per-group `none_feasible` line, the required keys, and one line
  `Answer keys and allowed ids: {json}` (label -> ids, `none_feasible` last).
- **Answer contract.** The reply's JSON object must carry `choices`, an object
  whose keys are exactly the slot labels. It is validated against a per-item
  model built with `pydantic.create_model`: frozen, `extra="forbid"`, one
  required `Literal[ids..., "none_feasible"]` field per slot. Integer ids are
  read as strings for numbered ids; nothing else is coerced. A failure is
  re-asked with the production `build_reask_prompt`, up to `max_attempts`;
  then `decision=None`, `parse_status="failed"`.
- **Schema delivery.** `VLMBackend.analyze(payload, config)` carries no
  response schema: `PromptPayload` has no schema field, `GeminiBackend`
  loads one static schema (`vlm_decision`) at construction behind
  `force_schema` (false in `config/models.yaml`), and `AnthropicBackend` sends
  none. The keys are therefore stated in the prompt and enforced by the
  validator above, the same for every backend.
- **Answer record.** `VariantAnswer.group_decisions` maps each label to the
  chosen option's decision (`ClusterOption.decision`, crossing order kept) or
  None for `none_feasible`; `decision` is None. The run config's `per_item`
  adds `slots`, `choices`, `chosen_v2_numbers` and `joint_check`.
- **Scoring (`scoring.score_group_decisions`).** Each chosen decision is
  grounded alone with `score_item`; no merged decision is ever grounded. The
  row combines them:
  - involved = the union of the chosen robots, in slot order; coverage,
    per-cluster recall, the A33(6) matched conflict and F1 are computed on it
    with the existing functions, so rows compare with single-decision runs on
    the same denominators;
  - M3 feasibility = every chosen decision feasible (first refusal kept);
  - strategy = the chosen strategies joined with `+`, in slot order;
  - yielder, and its M3-oracle, live-shadow and MC agreement: from the chosen
    yield that contains the MC first-conflict pair, else the one sharing most
    robots with the matched conflict (no yielder when none shares a robot
    with it), else, with no matched conflict, the first;
  - all slots `none_feasible` = a negative answer.
  - The GT-side extras (per-slot `none_feasible` rate, spurious commands =
    chosen options naming no robot of an active GT cluster, per-cluster
    best-option F1) are computed in `per_cluster_report`, never in the
    variant.
- **Joint check (`joint_check`, scene only).** Exact, from the grounded
  commands: robots addressed by two chosen commands (a hold in one and a move
  in the other included) and yield retreat points closer than
  `geometry.robot.safety_radius_m`. Heuristic, timing-free: straight-line
  motion segments (yield backup and pull-off, passer escort lines, reverse
  backups, reroute polylines) within that radius of the other command's
  segments or addressed robots. It filters nothing. Live M5 dispatches one
  grounded command per analysis (the plan channel tracks a scene-wide leg list
  but dispatches only that command), so a per-group answer is not executable
  live as one decision.
- **CLI.** `replay --prompt-variant grounding_first_per_cluster
  [--option-ids numbered|opaque] [--shuffle-options --seed N]`;
  `--fixed-group-choice first|none_feasible` is the zero-network chooser
  (cached under `<cache-dir>/fixed-group-choice-<rule>`); `candidates
  --generator per-cluster` writes the GT-scored ceiling rows and summary.
  `--gf-offgroup` and `--gf-cross-group` other than `drop` are rejected.

---

## Reporting

Each run writes three files:

- `run.jsonl`: one line per item, holding the decision, every per-item metric
  field and the grounding outcome;
- `run.md`: the summary table, pooled and per batch;
- `run.config.json`: the mode, the prompt variant and its hash, the
  representation flags, the model id, md5s of the bench code and of each
  grounding and rag file used, the item-file md5 and the git HEAD.

CLI:

```bash
python -m benchmarks.vlm_bench build-items <bundle>... --out items.jsonl
python -m benchmarks.vlm_bench score --mode recorded|classical --items items.jsonl --out run.jsonl --summary run.md
python -m benchmarks.vlm_bench replay --backend <id> --prompt-variant baseline --items items.jsonl --out run.jsonl --summary run.md
python -m benchmarks.vlm_bench replay --backend <id> --prompt-variant grounding_first_per_cluster --items items.jsonl --out run.jsonl --summary run.md
python -m benchmarks.vlm_bench candidates --generator per-cluster --items items.jsonl --out rows.jsonl --summary rows.md
```
