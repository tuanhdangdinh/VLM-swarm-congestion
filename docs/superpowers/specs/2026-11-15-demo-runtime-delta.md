# Demo Runtime Delta: VLM Recede-Order Channel on IB10

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: runtime files, overlay fragment and kit gate assertions for a live demo of the VLM recede-order channel (conditions A and B), on top of the 2026-11-14 runtime.
- Rev 2 (2026-11-15): refreshed for the release-rule sub-condition `edeb98c` (tip `9102ce9`): five runtime md5s, condition B3 (the campaign's frozen intersection config), the startup line's release-rule field, the artifact field and the third sentence.

---

## Purpose

This is the kit input for the live demo. In the demo, the VLM's verified plan sets the order of the `junction_clear` recede phases that M4 executes. It lists:

- what differs from the 2026-11-14 deployed runtime;
- the overlay keys that select condition A or B;
- the log lines and artifact fields a kit gate must assert to prove the condition was live.

It does not authorise a run. The go/no-go inputs are in `docs/reports/2026-11-15-vlm-order-channel-plan-check.md`. Machine-readable copy: `data/experiments/2026-11-15-vlm-order-channel-plan-check/demo_runtime_delta.json`.

---

## Base

- **Base:** the v3 pin `68e67b5`, plus the three 2026-11-14 safety items, unchanged (`docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md`, section 2).
- **Branch:** `demo/vlm-order-channel` at `9102ce9`: commits `347898c` (prompt condition), `e906ac4` (startup line) and `edeb98c` (release-rule sub-condition).
- `git diff --name-only 68e67b5..HEAD -- ros2_ws reasoning config` lists exactly the eight files below.

---

## Runtime Files

| File | 68e67b5 md5 | Demo md5 | Origin |
|---|---|---|---|
| `ros2_ws/src/swarm_execution/swarm_execution/safety.py` | `c6c9cbaeb9cb816dd2ba759c2464afb4` | `3011d9a735e790f56f6c46d98c76f1d9` | 2026-11-14 safety, unchanged |
| `ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` | `7b45075fcb940e3e3b57154b3b727958` | `c2cad302be27cf1b638fbeebf295ae7d` | 2026-11-14 safety, unchanged |
| `config/safety/scoped_clearing_exemption.fragment.yaml` | absent | `08c06b51491e9273c77d4c2e96b4c1ba` | 2026-11-14 safety, unchanged. Merged into swarm_execution `config/safety.yaml` = `65fb84a396c3d61a4e4179cd2360897b` |
| `reasoning/vlm/prompt_builder.py` | `9007becb85773b9a14b16875a40dfcb2` | `a9ad857cf8355cd9f5601124b0b814b2` | new: `_PLAN_GRAMMAR_RULES`, `_PLAN_GRAMMAR_V35`, `_PLAN_GRAMMAR_RELEASE_RULE`, `_PLAN_GRAMMAR_V36`, selection on `request.plan_grammar_rules` / `plan_grammar_release_rule` |
| `reasoning/vlm/models.py` | `0c0c844971278a92da844a9f38793e4e` | `2025f18179c9f3b05a81072027c32637` | new: `ReasonerRequest.plan_grammar_rules`, `plan_grammar_release_rule` (both default False) |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `273bbf7f7d01755226506fd892a380fa` | `73f3fa4f35ceab61a5df646a71a902a6` | new: config keys `prompt_plan_grammar_rules` (default False, requires `plan_channel_enabled`) and `prompt_plan_grammar_release_rule` (default False, requires `prompt_plan_grammar_rules`); `plan_order_status_line` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `e1b3b289ec05e3c21921fa0253829542` | `37a6bbadf91cb8c9def21d6f625c8bfe` | new: passes both keys into the request; logs the startup line |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `39a51bfc0de66a42b6f6ac4c78a60478` | `49fff7ab8fb460b9a94ea198cf5b523a` | new: `build_reasoner_request(plan_grammar_rules=, plan_grammar_release_rule=)`; `prompt_conditions.plan_grammar_rules` and `.plan_grammar_release_rule` (each omitted when False) |

What is unchanged:

- Grounding, verification, repair, the parser and every safety check: `command_grounder.py`, `maneuver_geometry.py`, `output_parser.py`, the plan tracker and M4.
- `plan_dispatch_order_source: model_when_verified` is existing code (`a98574b`, 2026-10-07) and needs no file change.
- Not part of the runtime: `scripts/replay_live_decisions.py`, which only reconstructs the new condition for replays.

**Default behaviour is unchanged.** With the four keys at their defaults, every prompt is byte-identical to v3.4: the six v3 pins and five apparatus pins hold. Artifacts gain no key. The startup line is not logged. The full unit suite has the same 57 failures and 3 collection errors as the base; all are environmental (`pxr`, ArUco, scenario files).

---

## Overlay Fragment

Start from the 2026-11-14 Arm A overlay `ib10s_l2on.yaml` (md5 `0196f1e8db0ffb9553c166707441362d`). It already has `plan_channel_enabled: true` and `grounding_yield_feasibility: 'off'`; keep both. Add:

```yaml
# Condition A
plan_dispatch_order_source: model_when_verified
prompt_plan_grammar_rules: true
```

```yaml
# Condition B (= A plus the existing options block; a declared construct change)
plan_dispatch_order_source: model_when_verified
prompt_plan_grammar_rules: true
prompt_candidate_options: true
```

```yaml
# Condition B3 (= B plus the release-rule sentence): the demo campaign's frozen intersection config
plan_dispatch_order_source: model_when_verified
prompt_plan_grammar_rules: true
prompt_plan_grammar_release_rule: true
prompt_candidate_options: true
```

A3 is A plus `prompt_plan_grammar_release_rule: true`. The demo campaign (`demo/campaign-kits`, `data/logs/vm_runs/demo_campaign/runtime_delta/`) applies B3 to the intersection kit only.

The backend stays the 2026-11-14 ER-2 arm (`gemini`, `gemini-robotics-er-2-preview`, `config/models.yaml` unchanged).

---

## Kit Gate Assertions

**Before launch.**

1. The installed copies of the eight files match the demo md5s above, and `PINS_V3`-style restore lists them.
2. `load_config(overlay)` succeeds and returns:
   - `plan_dispatch_order_source == "model_when_verified"`;
   - `prompt_plan_grammar_rules is True`;
   - `prompt_plan_grammar_release_rule` is `True` for A3 and B3, else `False`;
   - `prompt_candidate_options` is `False` for A and `True` for B;
   - `plan_channel_enabled is True`.

**M5 startup line**, exactly one per M5 process (`m5.log`):

```text
plan order condition plan_dispatch_order_source=model_when_verified prompt_plan_grammar_rules=True prompt_candidate_options=False
```

For B the last field reads `prompt_candidate_options=True`. With the release rule on (A3, B3) the line gains a fourth field, `prompt_plan_grammar_release_rule=True`. For B3:

```text
plan order condition plan_dispatch_order_source=model_when_verified prompt_plan_grammar_rules=True prompt_candidate_options=True prompt_plan_grammar_release_rule=True
```

A missing line means the overlay did not reach M5, and the run is invalid.

**Every congestion decision artifact** (`decisions/<request_id>.json`):

| Field | A | B |
|---|---|---|
| `prompt_version` | `3` | `3` |
| `prompt_conditions.prompt_version` | `3` | `3` |
| `prompt_conditions.plan_grammar_rules` | `true` | `true` |
| `prompt_conditions.plan_grammar_release_rule` | absent (A); `true` (A3) | absent (B); `true` (B3) |
| `prompt_conditions.candidate_options_requested` | `false` | `true` |
| `prompt_conditions.construct_constrained_selection` | `false` | `true` |
| `prompt.user_prompt` contains both sentences verbatim (section "Sentences") | yes | yes |
| `plan_dispatch_order_source` | `"model_when_verified"` | `"model_when_verified"` |
| `dispatch_order_source` | `"model"` exactly when `plan.provenance == "vlm_verbatim"` on a `junction_clear` | same |
| `plan.provenance`, `plan.dispatch_matches_plan`, `plan.order_equivalent`, `plan.legs`, `plan.edits` | present (plan channel on) | present |
| `grounding_yield_feasibility` | `"off"` (as 2026-11-14) | same |

**Demo event**, per `junction_clear` decision. All four must hold:

1. `plan.provenance == "vlm_verbatim"`;
2. `dispatch_order_source == "model"`;
3. the plan's recede order (its `reverse` legs in list order) differs from chi's order on that snapshot;
4. the `junction-recede-<robot>` commands appear in that same order in `m5.log` (`dispatch request=... command=<rid>-junction-recede-<robot>`) and in `m4.log` (`command received command=<rid>-junction-recede-<robot>`).

chi's order is not written to the artifact. Compute it offline from the artifact's scene and `grounding_params_source` with `rank_recede_candidates` (`scripts/vlm_order_channel_plan_check.py` does this).

Also report `plan.dispatch_matches_plan`. A verbatim plan naming robot_2 as yielder dispatches robot_1 (the yielder gap, open by owner decision) and records `false`.

---

## Sentences

The two sentences of prompt v3.5, inserted after the grammar's list-order line (A, B):

```text
Name each robot exactly once: its one leg is its whole role in the resolution.
A "cross" leg must come after the "yield" leg that releases it.
```

The release rule (v3.6, A3 and B3) appends a third sentence after them:

```text
A plan with any "cross" leg must also contain a "yield" leg listed before it; a "reverse" or "wait" leg does not release a crossing.
```
