# Forcing-Audit Fixes A1–A5 on the v2 Composite

**Prepared:** 2026-10-07

**Revision history:**

- Initial draft: the five FIX NOW items of the "Forcing/hardcode audit RESULT + RULINGS (2026-10-07)" block, on `feat/v2-audit-fixes`.
- Rev 2 (2026-10-07): follow-up ruling A7 (the `no_candidates` fallback merges degradations); the two remaining residual gaps ruled ACCEPTED.

---

## Summary

This report implements items A1–A5 of the forcing-audit rulings. The rulings sit in the prereg-v2 design spec (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, block "Forcing/hardcode audit RESULT + RULINGS (2026-10-07…)"). That block exists only in the main checkout (`fix/deadlock-collision-resolution` at `708a590`), not on the composite tip this branch starts from. The audit's own full report (`docs/reports/2026-10-07-forcing-audit.md`) is likewise only on that branch (`c967752`). Item A6 was ruled a wording correction with no code change, so it is not touched here. Follow-up ruling A7 (block on `fix/deadlock-collision-resolution` at `53bc294`) is implemented below.

- **Branch `feat/v2-audit-fixes`**, a worktree from `feat/prereg-v2-composite` at `941c1c3`:
  - `cf410be`: A1, the `junction_clear` phase record is serialized into decision artifacts.
  - `6f370d6`: A5b, the registry-filtered dispatch is recorded, and the recorded command is the one dispatched.
  - `7ca6473`: A5a, a reverse leg shortened by the tracked-band clamp is tagged.
  - `8cce46c`: A4, a discarded yield-axis crossing order gets its own tag.
  - `8094cb7`: A3, `resolved` requires a dispatch; adds `self_resolved` and the `n_dispatches` column.
  - `6b8c95c`: A2, scorers report `backend_id` and refuse mock bundles unless `--allow-mock` is passed.
  - `6ef47c6`: A7 (follow-up ruling), the `junction_clear` `no_candidates` fallback merges the plain yield's degradations instead of replacing them.
  - A docs commit carries this report and the implementation-notes entry.
- **No VM run, no live API call, no merge, no push.** Prompts, `config/models.yaml`, oracles and the retry/transport layer are untouched.
- **Additive only.** No existing artifact key or scorer field changes shape or meaning. One vocabulary addition is the exception: `outcome_class` gains a fourth value, `self_resolved` (A3).
- **Local suite: zero delta.** The same 65 ids fail before and after (62 failed + 3 collection errors). Passes went from 5,413 to 5,447, all from new tests.

---

## Per-Item Fixes

### A1: `junction_phases` serialized into the decision artifact (highest priority)

- **Defect.** `write_decision_artifact` (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py`) never wrote `PipelineOutcome.junction_phases` (`models.py:545`). Phase 0's command reached the artifact only indirectly. The precomputed recede, cross and release commands, the fallback command, and their `degradations` were visible only in ROS log lines. Those degradations include `junction_geometry=shipped_unsolved:missing=…`.
- **Fix.** A `junction_phases` key, added only when the outcome carries a phase plan. This follows the same conditional-add pattern as `plan`. The value is `JunctionClearPhasePlan.model_dump(mode="json")`, which holds every phase (`label`, `robot_id`, `command` including its `degradations`, `held_robot_ids`), plus `fallback_command` and `fallback_held_robot_ids`.
- **Proof.**
  - `test_write_decision_artifact_round_trips_every_junction_phase_field`. It runs the real pipeline with J2 undeclared, writes the artifact, and parses `junction_phases` back into a model equal to the outcome's. Every phase has its four fields, and the `shipped_unsolved` tag survives on the recede, cross and fallback commands.
  - `test_write_decision_artifact_omits_junction_phases_key_when_absent` covers the case with no phase plan.
- **Judgment call: runtime phase status stays log-only.** `PipelineOutcome` carries no per-phase status or timestamps. Phases advance after the artifact is written, and the scorer already reads that from the M5 log (`junction_clear phase advance … phase_reached=… done=…`, `coverage_scene_scores._PHASE_ADVANCE_RE`). Re-persisting per transition would mean rewriting the artifact on every status change, and `PlanDispatchInfo` documents avoiding exactly that. The artifact therefore records the full precomputed record, and runtime status remains in the log.

### A5b: recorded == dispatched under the second robot filter

- **Defect, corrected against the audit's anchor.** Two different filters run on the command:
  - The pipeline filters the grounded command to the robots in the request snapshot (`reasoning_pipeline.py`, `_run_from_result`).
  - `_dispatch` filters it again to the robots in `initial_tasks` (`orchestrator_node.py:1046-1049`), after the artifact write.

  The two sets differ whenever M1 tracks a robot that has no registry task. When they do, M4 receives fewer robots than M3 grounded, and a yield's `crossing_order` and `crossing_clear_m` are pruned. The artifact never showed either effect, because it never recorded the grounded command at all; it holds only `grounded_command_present`.
- **Fix.** New pure function `registry_dispatch(outcome, registry_robot_ids)` (`reasoning_pipeline.py`) and model `RegistryDispatch` (`models.py`).
  - `_handle_outcome` computes it once, before the artifact write.
  - `write_decision_artifact(dispatch=...)` records four keys:
    - `dispatched_command`: the filtered command, exactly as fanned out.
    - `dispatched_robot_ids`.
    - `dispatch_dropped_robot_ids`.
    - `dispatch_filter_error`: present only when the filter refused the command.
  - Under `junction_phases`, it also records `junction_phases_dispatched_robot_ids`: each later phase's and the fallback's robot ids after the same filter.
  - `_dispatch` fans out that same `RegistryDispatch.command`, so the recorded and dispatched sets are equal by construction. When called with one argument, as tests do, it computes the value itself.
- **Proof.**
  - `tests/unit/test_m5_node_registry_dispatch.py` runs through the stubbed node, using the `test_m5_node_probe` harness. A grounded yield addresses intruder `robot_9`, which has no registry task. The artifact's `dispatched_robot_ids` equal the published `CoordinationCommand` robot ids (`robot_2`, `robot_1`), `dispatch_dropped_robot_ids == ["robot_9"]`, and the recorded `crossing_order` and `crossing_clear_m` equal the pruned values sent to M4.
  - `test_m5_reasoning_pipeline.py` adds pure tests for `registry_dispatch`: a junction phase plan with `robot_4` unregistered, the no-command case, and a recorded refusal.
- **Judgment call: mirror the filter, don't move it.** Moving the registry filter into the pipeline would have changed which command `dispatch_matches_plan`, the `yield_*` artifact fields and the state machine see. The pipeline also has no registry. The mirror changes no dispatch behavior and makes equality structural.
  - **The new keys are unconditional.** They are written on every grounded outcome M5 records, not gated behind a flag. The pinned key-set test `test_probe_mode_off_triggered_analysis_unchanged` now expects `_TRIGGERED_ARTIFACT_KEYS | _DISPATCH_ARTIFACT_KEYS`. The keys mean "what the dispatch path sends if the state machine dispatches this outcome", because they are written before the directive is known.
  - **Preserved behavior: the filter refusal still raises.** When no action is left for a registry robot, `_dispatch` raises `CommandGroundingError` out of the timer callback, as the inline filter did before. The only difference is that the refusal is now in the artifact first.
- **No T3a intruder fixture existed.** The T3a scenes in the repo (`blocked_path_object`, `blocked_path_transient`) use timed obstacles, not untasked robots, so the node test above builds the intruder case itself.

### A5a: tracked-band clamp is tagged

- **Defect.** `_clamp_reverse_distance_to_tracked_band` (`reasoning/rag/command_grounder.py:226-262`) shortened a `reverse` leg with no trace. It is called from `_ground_legacy`, which also grounds `reverse` in derived mode. In derived mode, the wrapper (`_with_degradations(legacy, _legacy_template_degradations(...))`) replaced the command's `degradations` list rather than extending it.
- **Fix.**
  - When the clamp actually changes a distance, the command carries `degradations: ["reverse=clamped_tracked_band:<robot>:<from>-><to>"]`, for example `…:robot_3:1.3->0.62`.
  - An unclamped command gains no key. The clamp never fires without a declared `tracked_extent_m`, so v1 output stays byte-identical.
  - The derived wrapper now merges the lists instead of replacing them.
  - The tag is registered in `DEGRADATION_TAGS` with cause `None`, as provenance.
- **Proof.** `test_reverse_clamp_is_tagged_when_it_shortens_the_leg`, `test_unclamped_reverse_carries_no_degradations_key` and `test_reverse_clamp_tag_survives_derived_mode_grounding`, all in `tests/unit/test_command_grounder.py`. The existing exact-`actions` pin is unchanged and still green.

### A4: discarded yield-axis order is tagged distinctly

- **Defect, refined.** `_as_yield_decision` clears the decision's `crossing_order`. Three grounding sites use it, and the audit's description fits only one of them:
  - **4-robot plain-yield fallback command** in `ground_junction_clear_phases`. Here `order=implicit` ("none given") fired even though the model had given an order. This is the mis-tag the audit describes.
  - **IB10 cross phase** (two yield-axis robots, one passer). `order=implicit` never fires here, so the discard was untagged entirely.
  - **`no_candidates` fallback.** The branch replaces the yield's tags with its own list, so no order tag survived there.
- **Fix.** New helper `_tag_discarded_order` handles the first two sites. It replaces `order=implicit` with `order=discarded_yield_axis`, or appends that tag when `implicit` did not fire. The `no_candidates` branch uses the same helper; since A7 that branch keeps the yield's tags, so the tag replaces `order=implicit` there too. Two limits apply:
  - **Explicit override:** no tag is added when a caller supplies its own `crossing_order` override, because that override is then the operative order.
  - **Behavior:** grounding output does not change. The tag is the only addition; the discarded order is not newly honoured.

  The tag is registered with cause `None`.
- **Consumers.** None was found that switches on the order tag. `reasoning/rag/plan_metrics.py` does not read `degradations`, so no change to the plan-metrics tests was needed. The only references are `DEGRADATION_TAGS` and `tests/unit/test_command_grounder_derived.py`, which still passes unchanged.
- **Proof.** `TestDiscardedYieldAxisOrder` (7 tests) in `tests/unit/test_junction_clear_grounding.py`:
  - Fallback: `discarded` replaces `implicit`; without a model order it stays `implicit`.
  - Single-passer cross phase: the discarded order is marked.
  - `no_candidates` path: the discarded order is marked.
  - An explicit override is not marked.
  - The tag maps to cause `None`.

### A3: `resolved` requires at least one dispatch

- **Defect.** `classify_outcome` (`scripts/coverage_scene_scores.py:1598-1647`) labelled an all-arrived episode with zero dispatched decisions `resolved`. A test pinned that case as `no_dispatch_all_arrived → RESOLVED`.
- **Fix.** A fourth value, `OutcomeClass.SELF_RESOLVED = "self_resolved"`, applies to an all-arrived episode with `n_dispatches == 0`. `resolved` now means exactly one dispatch and no fallback. The precedence order is:
  1. `clogged`: `fallback_exhausted`, or any robot censored.
  2. `intermittent`: two or more dispatches, or a fallback.
  3. `self_resolved`: zero dispatches. This is checked before the composite "no M5 log" guard, because with no dispatch no phase can have failed over.
  4. `None`: unknown dispatch count, or a composite cell without M5's log.
  5. `resolved`.

  Every `flow_fields` row now carries `n_dispatches` at the top level beside `outcome_class`. It remains inside `outcome_evidence` as well.
- **Proof.** In `tests/unit/test_flow_metrics.py`:
  - The `no_dispatch_all_arrived` case now expects `SELF_RESOLVED`, and a new `no_dispatch_censored` case expects `CLOGGED`.
  - `test_resolved_is_never_awarded_without_a_dispatch` covers plain and composite cells.
  - `test_zero_dispatch_episode_reports_self_resolved_with_its_count` runs end to end through `score_ib10`.
  - The registered-strings pin and the additive key set were updated.
- **Judgment call: a new enum value, not `None`.** Returning `None` would merge zero-dispatch episodes with invalid and unknown runs and drop them from denominators silently. That matters most for the layer-2-off arm, where zero dispatches is the expected case (`docs/reports/2026-10-06-layer2off-pilot.md` flagged it). A distinct value keeps the case countable and never credited to the decision layer. `outcome_rank` does not branch on the class, and no other code consumer exists.
- **Coordinator action needed.** The spec registers three classes (resolved, intermittent, clogged). `self_resolved` needs an append-only registration line.

### A2: backend column and mock refusal in scorers

- **Defect.** No scorer read `diagnostics.backend_id`, so a mock-answered bundle scored identically to a live one.
- **Fix.**
  - **Shared helpers.** New stdlib-only module `scripts/artifact_backend.py`:
    - `record_backend_id` prefers `reasoner_config_effective.backend_id`, the arm id, because pre-F09 successes carry the provider model id in `diagnostics`. It falls back to `diagnostics.backend_id`.
    - `record_is_mock` checks both fields.
    - `MockBackendError` is the refusal.

    It is a separate module because `coverage_scene_scores` imports `strategy_regret`, so putting the helpers in either one would make the import circular.
  - **`coverage_scene_scores.py`:**
    - New `decision_backend(decisions_dir, allow_mock=False)`.
    - Every subcommand that reads decisions (`b1`, `b3`, `ib10`, `loop`, `flow` via `flow_fields`, and `b2`'s `:DECISIONS`) emits `backend_id`. Several distinct ids are joined by `+`; the value is null when no artifact records one.
    - These subcommands refuse a bundle in which any artifact names `mock`: `MockBackendError`, CLI exit 2 with a message naming `--allow-mock`. The new `--allow-mock` flag, and `allow_mock=True` in the library, override the refusal.
  - **`strategy_regret.py regret`:** emits `backend_id` and applies the same refusal and flag.
- **Policy choices.**
  - **No backend id recorded:** surfaced as `null` and not refused. Every real M5 artifact carries `diagnostics.backend_id`, a required field, and the existing scorer tests use bare records, so none of them needed the flag.
  - **Mock-by-design harnesses are not gated:** `strategy_regret score`/`plan`, `t2b_forced_order`, `free_flow_table`. Their forced arms are mock sweeps on purpose, and they do not score decisions.
  - **`rescore_arrivals.py` is not gated.** It reads decisions only for FR5.1.9 alias resolution.
- **Proof.** 8 tests in `test_flow_metrics.py`:
  - The effective-first preference, the diagnostics fallback, and null for bare records.
  - Refusal by the library and by the CLI; a mock named only in `diagnostics` is also refused.
  - `--allow-mock` scores the bundle and reports `mock`.
  - A live bundle reports its arm.

  `TestMockRefusal` (4 tests) in `test_strategy_regret.py`.

---

## Where the Audit's Anchors Were Off

- `reasoning_pipeline.py:853-936` and `models.py:545` (A1), and `coverage_scene_scores.py:1598-1647` (A3), are accurate.
- `command_grounder.py:2916-2925` (A4) points at the right function, `_as_yield_decision` (2893–2930). The claim that it "tags `order=implicit`" holds only for the 4-robot fallback command, as A4 above details.
- `command_grounder.py:226-262` (A5a) is the clamp's definition. The mutation happens at its call site in `_ground_legacy`, and in derived mode the wrapper also dropped any tag.
- `orchestrator_node.py:1046-1049` (A5b) is accurate as a location. The mechanism differs from the audit's wording: the divergence is between two different filters (snapshot versus registry), and the artifact recorded no robot list to compare against.

---

### A7 (follow-up ruling): the `no_candidates` fallback keeps the yield's provenance

- **Defect.** `_ground_derived`'s `junction_clear` branch, when no recede candidate survives, grounds a plain yield and then set the command's `degradations` to its own list (`junction_clear=fallback:no_candidates`, plus `junction_geometry=shipped_unsolved:*` when a field is missing). That threw away the yield's own tags, such as `retreat=default:*`, `yield=infeasible:*` and `order=junction_same_axis`, on the path the `fallback_exhausted` analysis scores. It was flagged here first as a residual gap; the coordinator ruled it FIX NOW.
- **Fix.** The branch merges: the yield's tags come first, in their original order, then the fallback's own. The A4 discarded-order marker goes through `_tag_discarded_order` as at the other two sites. This is the same merge discipline as the A5a wrapper fix.
- **Proof.** `TestNoCandidatesFallbackKeepsYieldProvenance` in `tests/unit/test_junction_clear_grounding.py` grounds the same scene as a plain `yield` and as a `junction_clear` with no declared pocket. The fallback's tag list starts with the plain yield's full list (`roles=legacy-convention`, `order=implicit`, `order=junction_same_axis`, `retreat=default:no_choice`), followed by `junction_clear=fallback:no_candidates` and the `shipped_unsolved` tag. Before the fix it held only the last two. The existing `no_candidates` and loudness-guard tests assert membership and pass unchanged.

---

## Residual Gaps (Ruled ACCEPTED)

- **Runtime phase status** (which phase was reached, completion and timestamps) remains in the M5 log only; see A1.
- **Publish-time parameter injection.** `_publish_fanned_out` still adds a reroute's `goal` and a reverse leg's `plan_continue_partners` to `parameters_json` after the artifact write. These are parameter-level additions, not robot-set changes, so `dispatched_command` does not show them. This is recorded as the known, bounded exception to recorded == dispatched.

---

## Verification

| Step | Result |
|---|---|
| Baseline at `941c1c3` (`pytest --continue-on-collection-errors`) | 62 failed, 5,413 passed, 153 skipped, 3 errors |
| After `6b8c95c` | 62 failed, 5,446 passed, 153 skipped, 3 errors |
| After `6ef47c6` (A7) | 62 failed, 5,447 passed, 153 skipped, 3 errors |
| Failing-id set diff (65 ids, `FAILED` + `ERROR`) | identical |
| `ruff check` on every touched file | clean |
