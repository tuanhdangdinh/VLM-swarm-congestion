# Demo Runtime Delta: VLM Recede-Order Channel on IB10

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: runtime files, overlay fragment and kit gate assertions for a live demo of the VLM recede-order channel (conditions A and B), on top of the 2026-11-14 runtime.

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
- **Branch:** `demo/vlm-order-channel`, commits `347898c` (prompt condition) and `e906ac4` (startup line).
- `git diff --name-only 68e67b5..HEAD -- ros2_ws reasoning config` lists exactly the eight files below.

---

## Runtime Files

| File | 68e67b5 md5 | Demo md5 | Origin |
|---|---|---|---|
| `ros2_ws/src/swarm_execution/swarm_execution/safety.py` | `c6c9cbaeb9cb816dd2ba759c2464afb4` | `3011d9a735e790f56f6c46d98c76f1d9` | 2026-11-14 safety, unchanged |
| `ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` | `7b45075fcb940e3e3b57154b3b727958` | `c2cad302be27cf1b638fbeebf295ae7d` | 2026-11-14 safety, unchanged |
| `config/safety/scoped_clearing_exemption.fragment.yaml` | absent | `08c06b51491e9273c77d4c2e96b4c1ba` | 2026-11-14 safety, unchanged. Merged into swarm_execution `config/safety.yaml` = `65fb84a396c3d61a4e4179cd2360897b` |
| `reasoning/vlm/prompt_builder.py` | `9007becb85773b9a14b16875a40dfcb2` | `721f1a1292c09aa0293063c91f4dfcf4` | new: `_PLAN_GRAMMAR_RULES`, `_PLAN_GRAMMAR_V35`, selection on `request.plan_grammar_rules` |
| `reasoning/vlm/models.py` | `0c0c844971278a92da844a9f38793e4e` | `51f8446cfe82ab4d1f7a5599760dbb5e` | new: `ReasonerRequest.plan_grammar_rules` (default False) |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `273bbf7f7d01755226506fd892a380fa` | `7ee292a318966256caba3e31c96d7f68` | new: config key `prompt_plan_grammar_rules` (default False, requires `plan_channel_enabled`); `plan_order_status_line` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `e1b3b289ec05e3c21921fa0253829542` | `2db3018b6f5807b37fde70a4f0507345` | new: passes the key into the request; logs the startup line |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `39a51bfc0de66a42b6f6ac4c78a60478` | `21af8e8c360cf3de0a74fb05ad79ef27` | new: `build_reasoner_request(plan_grammar_rules=)`; `prompt_conditions.plan_grammar_rules` (omitted when False) |

What is unchanged:

- Grounding, verification, repair, the parser and every safety check: `command_grounder.py`, `maneuver_geometry.py`, `output_parser.py`, the plan tracker and M4.
- `plan_dispatch_order_source: model_when_verified` is existing code (`a98574b`, 2026-10-07) and needs no file change.
- Not part of the runtime: `scripts/replay_live_decisions.py`, which only reconstructs the new condition for replays.

**Default behaviour is unchanged.** With the three keys at their defaults, every prompt is byte-identical to v3.4: the six v3 pins and five apparatus pins hold. Artifacts gain no key. The startup line is not logged. The full unit suite has the same 57 failures and 3 collection errors as the base; all are environmental (`pxr`, ArUco, scenario files).

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

The backend stays the 2026-11-14 ER-2 arm (`gemini`, `gemini-robotics-er-2-preview`, `config/models.yaml` unchanged).

---

## Kit Gate Assertions

**Before launch.**

1. The installed copies of the eight files match the demo md5s above, and `PINS_V3`-style restore lists them.
2. `load_config(overlay)` succeeds and returns:
   - `plan_dispatch_order_source == "model_when_verified"`;
   - `prompt_plan_grammar_rules is True`;
   - `prompt_candidate_options` is `False` for A and `True` for B;
   - `plan_channel_enabled is True`.

**M5 startup line**, exactly one per M5 process (`m5.log`):

```text
plan order condition plan_dispatch_order_source=model_when_verified prompt_plan_grammar_rules=True prompt_candidate_options=False
```

For B the last field reads `prompt_candidate_options=True`. A missing line means the overlay did not reach M5, and the run is invalid.

**Every congestion decision artifact** (`decisions/<request_id>.json`):

| Field | A | B |
|---|---|---|
| `prompt_version` | `3` | `3` |
| `prompt_conditions.prompt_version` | `3` | `3` |
| `prompt_conditions.plan_grammar_rules` | `true` | `true` |
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

The two sentences of prompt v3.5, inserted after the grammar's list-order line:

```text
Name each robot exactly once: its one leg is its whole role in the resolution.
A "cross" leg must come after the "yield" leg that releases it.
```
