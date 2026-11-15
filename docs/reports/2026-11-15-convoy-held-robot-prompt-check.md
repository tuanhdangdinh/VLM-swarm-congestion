# Convoy Held-Robot Prompt Check

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: pre-registration (section 1), written and committed before any paid call.

---

## 1. Pre-Registration (2026-11-15, Before Any Paid Call)

**Question.** In the three live convoy takes (`docs/reports/2026-11-15-demo-campaign-results.md` section 5), ER-2's first decision named only the standoff pair. The prompt showed robot_3 and robot_4 as `STOPPED`, with no sign that M5 was holding them back (section 5.3 there). Does stating that hold-back state make ER-2's first answer ground into the command that resolved the scripted smoke? That command is a yield by robot_2, linked waits for robot_1, robot_3 and robot_4, and a crossing order covering all three.

**Is the state available at request time? Yes, as live M5 state (verified from code).**

- M5's `TaskRegistry` holds every robot with `start_delay_sec > 0`, or a task-stream hold, in `release_at` until it is released. `is_pending` reads it (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/task_registry.py:75-77`).
- Release happens in M5's own timer (`orchestrator_node.py:1017-1021`, `_on_timer` → `release_due`). The registry publishes `start_pending: true` for held robots (`task_registry.py:177`), which M4's base mission obeys (`swarm_execution/base_mission.py` `on_registry`).
- The request is built in the same node from the same registry (`orchestrator_node.py` `_submit_pipeline` → `_apparatus_inputs`, the new read at line 2609). No new plumbing across modules is needed. Branch 2a applies.
- The goals are already in the prompt (`goal_x`, `goal_y` on every state line), so branch 2b's alternative adds nothing.

**The condition (commit `2f83faf`, `feat: add default-off held-robot state prompt condition`).**

- Config key: `prompt_held_robot_state: bool = False`. It requires `plan_channel_enabled` (v3 only), like the other prompt conditions.
- Request field: `ReasonerRequest.held_robot_ids: list[str] | None`. None means off. M5 fills it with `sorted(r for r in snapshot robots if registry.is_pending(r))`.
- Rendered text, v3 only, and only when at least one listed robot is in the scene:
  - Each held robot's state line ends with `, start_pending=true`.
  - One note follows the state lines, verbatim:

    > start_pending=true: the system has not yet released this robot to start its task; once released, it starts driving toward its goal_x, goal_y.

  - The note is facts only. It names no robot, strategy, role or order.
- Artifact: `prompt_conditions.held_robot_ids`, omitted when off. Replay (`scripts/replay_live_decisions.py` `_apparatus_kwargs`) rebuilds the prompt from it.
- Startup line: `plan_order_status_line` now also logs when only this key is on, with the suffix ` prompt_held_robot_state=True`. Every earlier line is unchanged.
- Off, or on with an empty list, the prompt is byte-identical (tests).

**Stimuli (4 first-trigger snapshots).**

| Stimulus | Bundle | Request | Stored `user_sha256` | Treatment `user_sha256` |
|---|---|---|---|---|
| take 1 | v7j `demo_campaign/cv/runs/cvD_t01_a1` | `35084986` | `24b34947…` | `3fb81862…` |
| take 2 | v7j `demo_campaign/cv/runs/cvD_t02_a1` | `759bdb94` | `8e44f2ab…` | `f1b379c9…` |
| take 3 | v7j `demo_campaign/cv/runs/cvD_t03_a1` | `ab6a10c5` | `5ca37656…` | `df03e11f…` |
| smoke | v7f `convoy_live/runs/cvL_e01_armC_a1` | `39f28463` | `6163da99…` | `a4a486fb…` |

The treatment adds 182 characters. No other convoy first-trigger stimulus with a recorded prompt and frame exists. The smoke's answer was scripted, so its stimulus is the real prompt and frame, not a model answer.

**Held set.** The recorded artifacts predate the field, so the set comes from bundle evidence:

- robots with `start_delay_sec > 0` in the bundle's `orchestrator.overlaid.yaml` (robot_3 and robot_4, 120 s);
- whose `start delay elapsed, base mission released robots=[...]` line in `m5.log` comes after this request's first `dispatch` line (69–82 wall-s after it in all four bundles).

The result is `[robot_3, robot_4]` on all four.

**Free gates (passed; `data/experiments/2026-11-15-convoy-held-robot-prompt-check/gates.json`).**

- The rebuilt control prompt matches the stored `user_sha256` on 4 of 4.
- An offline replay of each recorded first decision reproduces its dispatched command, 4 of 4. It runs the M5 `chi` pipeline with the artifact's own legacy grounding params, which is the runner's `make_pipeline` and `_run_from_result`. The smoke's replayed command has the target structure.
- The effective ER-2 config equals the live takes' config: `gemini-robotics-er-2-preview`, temperature 0.6, top_p 0.95, top_k 20, thinking low, 2048 tokens, 2 attempts, payload v1.

**Conditions.**

- `C`: the recorded live prompt, rebuilt.
- `H`: the same request plus `held_robot_ids=[robot_3, robot_4]`.
- Same frame, same model and sampling.

**n.**

- 6 replicates per condition on each live take, 4 on the smoke: 22 calls per condition, 44 in all.
- Replicates run in order (rep 0 to 5). Each rep is C then H for every stimulus.
- Harness: `scripts/convoy_held_robot_plan_check.py`. It reuses `vlm_order_channel_plan_check.py`'s `Stimulus`, `GuardedBackend`, `Ledger`, shipped `Reasoner` and offline replay.

**Budget.**

- Expected about $0.0067 per call at list price, from the takes' recorded usage (about 2.9k input and 0.75k output and thought tokens, at $1 / $5 per M), so about $0.30 for 44 calls.
- The ledger counts 1.25 × list. Its cap is 0.48, which is $0.384 at list price, under the hard cap of $0.40. It stops before any attempt whose reserve would cross that cap.
- If it stops early, the analysis uses all billed calls and also reports complete replicates only.

**Measures (per condition; the primary is on the 3 live takes, n = 18 per condition).**

1. **Primary (P).** The answer's grounded command, from the offline `chi` replay with the artifact's legacy params, has the smoke structure (`full_sequence`):
   - exactly one `yield`;
   - linked `temporary_wait` (`linked_position`) for all three other robots;
   - all three in the yield's `crossing_order`;
   - and the yielder is **robot_2** (the variant known to resolve).
2. The same structure with **robot_1** yielding. The scene file says this variant latches. It is counted separately, never toward go.
3. The answer names all four robots with roles: `involved_robots` is all four, and no plan leg is `continue`.
4. Strategy mix, the grounded yielder, grounding refusals and `m3_default` fallbacks.
5. Everything above on the smoke stimulus (n = 4 per condition), reported separately.

**Go rule for a live convoy retake, fixed now.** Go only if, on the 3 live takes:

- P under H is at least 9 of 18; and
- P under H exceeds P under C by at least 6.

Otherwise no-go. The per-take chance estimate will be H's P share times an assumed probability that this structure resolves live. The smoke resolved 1 of 1, and the scene file says the robot_2 variant resolves; that probability is inferred, not measured.

**Not changed.** Grounding, verification, safety, feasibility and parser code; the convoy kit; the runtime delta.
