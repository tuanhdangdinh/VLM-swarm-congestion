# VLM Plan Influence Trace - Four-Robot Live Episodes

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: offline trace of every four-robot live-model analysis from the VLM's raw answer to the commands M4 received, with counterfactual re-grounding and a proposal for a safe test of VLM influence.
- Rev 2 (2026-11-15): added the two 2026-10-02 smoke bundles found by a second scan, corrected three counts, added the feasibility-gate check and a second grammar sentence.

---

## Purpose

The owner asked whether the VLM makes a meaningful contribution to the commands the robots execute, or only produces a response while M3 executes its default plan. This report traces the decision path of every analysis in every existing four-robot live-model bundle. No VM was started and no paid API call was made. Every claim is labelled **verified** (read from a bundle or computed by the repo's own code on a recorded snapshot) or **inferred**.

Terms used throughout:

- **Valid response:** the answer parsed and passed the decision schema (`parse_status=valid`).
- **Accepted plan:** M3's verification returned `vlm_verbatim`. A `repaired` plan counts as accepted only where an executed element comes from the VLM. Here "comes from the VLM" means causally: the executed element would have been different had the VLM proposed differently.
- **Plan that changed behaviour:** re-grounding the same decision with `proposed_plan=None` on the same snapshot gives different commands from those recorded.

---

## Answers to the Owner's Four Questions

1. **What the VLM proposed.**
   - At the intersection, ER-2 gave 24 congestion answers in 17 bundles. The first answer of every episode was `junction_clear` for all four robots, except e09 of 2026-11-13, which answered `yield`. Later answers were two-robot `junction_clear` (e09 and one 2026-10-02 smoke episode, 2) and `reverse` of robot_3 and robot_4 (the 2026-10-02 smoke episodes, 3).
   - It wrote a `proposed_plan` in 22 of the 24, but never a `junction_clear` plan in M3's grammar. Typical plans:
     - the right pair (robot_3, robot_4) reversing, plus one inside robot also `reverse`d;
     - the wrong pair (robot_1, robot_2) reversing;
     - receders that `reverse` and then `cross` again, which names a robot twice.
   - gpt-4o (vp10) never chose `junction_clear` (0/13). It chose `yield`, `reverse` of two to four robots, and `temporary_wait`.
   - Full table in section A.
2. **Why `provenance=m3_default reason=plan absent` in ib10S_e03 (request `18c2a25e…`).**
   - The model did send a plan: `r4 reverse, r3 reverse, r2 cross, r1 cross, r3 cross, r4 cross`.
   - Its recede pair and order were exactly M3's own. It names robot_3 and robot_4 twice, though, and the stage-1 parser nulls any plan that repeats a robot (`reasoning/vlm/output_parser.py:130-136`; schema invariant `reasoning/vlm/models.py:515-524`).
   - M3 then saw no plan. The prompt never states the one-leg-per-robot rule, and its `junction_clear` description invites a back-out-then-cross plan (section C).
3. **Any four-robot episode where a VLM plan was accepted and executed?**
   - **No `junction_clear` plan, in any episode.** 0 of 20 ER-2 `junction_clear` answers verified `vlm_verbatim`: 11 were `repaired`, 8 `m3_default`, and 1 failed grounding before verification.
   - Fourteen four-robot `vlm_verbatim` plans exist: 11 from gpt-4o in vp10, 1 from s6, and 2 ER-2 `reverse` plans for robot_3 and robot_4 in the 2026-10-02 smoke episodes. In each, the commands came from the decision fields (strategy, robots, yield robot), not from the plan. 6 of the 14 were not even dispatched as written (`dispatch_matches_plan=false`: vp10 5, s6 1).
   - The October closure control R1 (mock, `vlm_verbatim`) shows the same gap: its plan said robot_4 recedes first, robot_3 receded first, and the artifact still records `vlm_verbatim` with `dispatch_matches_plan=true`.
4. **Did the VLM's decision change the executed commands versus the no-VLM default?**
   - **The plan never did:** 0 of the 39 live four-robot congestion analyses that pass the fidelity gate, out of 41. Of the other two, ER-2 sent no plan in `bed37d40`; its run predates the release phase, so the gate fails there. `125d841c` failed grounding and dispatched nothing.
   - In this runtime the plan is an audit. The grounder never reads it, and the one switch that lets it act was never turned on in any run (section D).
   - **The VLM's other choices did, through other fields, in four episodes:**
     - In e09 (2026-11-13), its `yield` and then its two-robot `junction_clear` replaced the default four-robot sequence. The episode never resolved (0/4 arrivals).
     - In vp10 (gpt-4o), every one of 13 dispatches differed from the Arm C default. The episode ended clogged (0/4).
     - In the two 2026-10-02 smoke episodes, three later `reverse` answers for robot_3 and robot_4 differed from the default. Those development-era runs failed 4/4 arrivals for code reasons fixed the same day (`docs/reports/2026-10-02-ib10-composite-smoke.md`). Whether the VLM's choices helped or hurt there cannot be separated.
   - Where the effect can be judged (e09, vp10), the VLM's own choices made the outcome worse.
   - The VLM's stage-2 retreat letter flipped the pull-off side in 2 of 3 answered cases.
   - In the other 17 gated intersection analyses, the executed commands equal what M3 produces from the strategy token alone.

---

## Sources Checked

| Source | What was read | Status |
|---|---|---|
| `vgu-vlm-swarm-v7a/.../ib10_live/runs/ib10L_e01_armA_a1`, `_a2`, `e03`, `e05`, `e07`, `e09` | all `decisions/*.json`, `m5.log`, `m4.log`, overlays | verified |
| `vgu-vlm-swarm-v7d/.../ib10_safety/runs/ib10S_e01`, `e03`, `e05`, `e07`, `e09` (Arm A); `e02_a2`, `e04`, `e06`, `e08`, `e10` (Arm C) | same | verified |
| `vgu-vlm-swarm/.../verbatim_pilot/vp08`, `vp09`, `vp10`; `v2_demo/ep2_live_er2`; `plan_grammar_cal/cal_ep1_rerun`; `s6_first_light/s6_live_er2_pilot` | same; October artifacts store no dispatched command, so `m4.log` `command received` lines were used | verified |
| `vgu-vlm-swarm-v3/.../ib10_closure/R/ib10cl_R_r1`, `R_r2`, `P/ib10cl_P_r1` (mock positive control) | same | verified |
| `vgu-vlm-swarm/.../ib10_smoke/live_20261002_120337`, `episode2_20261002_125412` (2026-10-02 step-6 smoke; flat layout, no overlay copy) | the 12 artifacts in the bundle root, `m5.log`, `m4.log`; geometry from the nearest-dated IB10 overlay (`v2_demo/ep2_live_er2`) | verified |
| Scan of every `decisions/` directory in every `vgu-vlm-swarm*` worktree (3,265 unique artifacts), then of every `*.json` carrying `raw_text` in any directory (3,410 files) | exactly four robots with a non-mock backend: only the bundles above. The second scan added only the two smoke bundles | verified |
| Runtime code: `68e67b5` (identical to this branch for `reasoning/` and `swarm_orchestrator/`; `git diff --stat` empty); October trees `a8fc1bc` and `af7cec5` via `git archive` | parser, verifier, grounder, pipeline | verified |
| `docs/reports/2026-11-13-ib10-live-resolution-results.md` (branch `feat/ib10-live-resolution`), `2026-11-14-ib10-safety-default-arm-results.md`, `2026-10-06-verbatim-pilot.md`, `2026-10-08-ib10-closure.md`, `2026-10-03-plan-grammar-fixes.md` | claims checked against the bundles (section G) | verified |

Analysis scripts and outputs are gitignored, in `data/logs/vm_runs/vlm_plan_influence_analysis/` on this branch:

| File | Role |
|---|---|
| `trace_plan_influence.py` | Per-analysis trace with counterfactual re-grounding and a fidelity gate |
| `prototype_order_channel.py` | Offline replay of the pipeline's existing order-from-plan path on recorded snapshots (section F) |
| `mirror_axis_probe.py` | Re-grounds snapshots with the declared corridor axis flipped (inference aid for "wrong pair") |
| `make_table.py` | Merges the outputs: `per_analysis.jsonl`, `per_analysis_table.txt` (readable table and counts) |
| `scan_bundles.py`, `scan_any_json.py` | Worktree-wide artifact index (`scan_index.jsonl`) and the second, layout-independent scan (`scan_any_extra.jsonl`) |

**Method.** The trace re-grounds each recorded decision with the runtime's own functions, using the artifact's recorded params, its feasibility mode and recorded stage-2 answer, and the bundle's overlay geometry. A diff is trusted only if the re-grounded recorded decision reproduces the recorded dispatch exactly (the fidelity gate):

- November and s6 bundles: actions and parameters from `junction_phases` or `dispatched_command`.
- October and smoke bundles: actions per command, against M4's `command received` lines. vp08 to vp10 ran `a8fc1bc`; ep2, cal_ep1 and the smoke episodes ran earlier trees. The runtime tree, `a8fc1bc` and `af7cec5` all reproduce the same actions.

39 of the 41 live congestion analyses pass the gate (verified):

- **`bed37d40`:** M4 received recede, recede, cross and then the fallback reroute, while current code adds a release phase. The model sent no plan there.
- **`125d841c`:** grounding failed in the run itself, so nothing was dispatched.

Counterfactual counts below use only gated rows. The counterfactuals are:

- **no-plan:** the same decision with `proposed_plan=None`.
- **Arm C:** `junction_clear`, all four robots, no other fields: the 2026-11-14 scripted decision.
- **no-stage-2:** the recorded decision without the stage-2 retreat answer.
- **shadow rule:** the `shadow_classical` decision, grounded.

---

## A. Per-Analysis Table

Strategies: `jc` is `junction_clear`. Plans are written `robot:action` in list order, with robot_N shortened to N. "Default" means the Arm C counterfactual. Every row's no-plan counterfactual equals the recorded dispatch.

| Episode, request | VLM answer (raw) | Stage 1 | M3 verification | Executed (recede order; yielder → passer) | Same as default? |
|---|---|---|---|---|---|
| ib10L_e01_a1 `0b9d2939` | jc; `4rev 3rev 2rev 1cross 2cross 3cross 4cross` | nulled: 2, 3, 4 named twice | `m3_default`, plan absent | 4, 3; 1 → 2 | yes |
| ib10L_e01_a2 `d9374445` | jc; `2rev 3rev 4rev 1cross` | valid | `repaired`: reorder (2, 4), swap (1, 2), substitute 1 | 4, 3; 1 → 2 | yes |
| ib10L_e03 `6c5406d8` | jc; `1rev 2rev 3cross 4cross` | valid | `repaired`: swap (1, 3), swap (2, 4), substitute 1 | 3, 4; 1 → 2 | yes |
| ib10L_e05 `a71c50a9` | jc; `3rev 4rev 1cross 2cross` | valid | `repaired`: substitute 1 (cross needs a releasing yield) | 3, 4; 1 → 2 | yes |
| ib10L_e07 `d7da0457` | jc; `2rev 3rev 4rev 1cross` | valid | `repaired`: reorder (2, 4), swap (1, 2), substitute 1 | 4, 3; 1 → 2 | yes |
| ib10L_e09 `e2678399` | **yield** 1, all four; `1yield 2cross 3cross 4cross` | valid | `m3_default`, repair bound 4 | one yield 1 → 2 (pull-off +0.36, from the VLM's stage-2 letter); 3 and 4 not commanded | **no** |
| ib10L_e09 `a73d6e03` | **jc over 2 and 4 only**; `4rev 2cross 1cross 3wait` | valid; order nulled (non-permutation) | `m3_default`, repair bound 4 | recede 4; 2 held 8 s; no passer | **no** |
| ib10L_e09 `ceff5efa` | jc; `2rev 1yield 4cross 3cross 1cross 2cross` | nulled: 1, 2 named twice | `m3_default`, plan absent | 4, 3; cross phase never resolved | yes |
| ib10S_e01 `bfaef39f` | jc; `1rev 3rev 4rev 2cross` | valid | `repaired`: reorder (1, 4), substitute 1 | 3, 4; 1 → 2 | yes |
| ib10S_e03 `18c2a25e` | jc; `4rev 3rev 2cross 1cross 3cross 4cross` | nulled: 3, 4 named twice | `m3_default`, plan absent | 4, 3; 1 → 2 | yes |
| ib10S_e05 `580328a5` | jc; `1rev 2rev 3cross 4cross` | valid | `repaired`: swap (1, 3), swap (2, 4), substitute 1 | 4, 3; 1 → 2 | yes |
| ib10S_e07 `1d8cbac7` | jc; `1rev 2cross 3cross 4cross` | valid | `repaired`: 4 edits | 4, 3; 1 → 2 | yes |
| ib10S_e09 `3f26b4c8` | jc; `4rev 3rev 2rev 1cross` | valid | `repaired`: swap (1, 2), substitute 1 | 4, 3; 1 → 2 | yes |
| vp08 `8fad1c84` | jc; `1cross 2wait 3rev 4rev` | valid | `repaired`: reorder (1, 4), substitute 1 | 4, 3; 1 → 2 | yes |
| vp09 `339b0880` | jc; `1rev 2rev 3rev 4rev` | valid | `repaired`: 4 edits | 3, 4; 1 → 2 | yes |
| ep2 `5dfbeb07` | jc; `3cross 1wait 4wait 2wait` | valid | `m3_default`, plan inconsistent (no reverse or yield leg) | 3, 4; 1 → 2 | yes |
| cal_ep1 `aec068b5` | jc; `1rev 2rev 3cross 4cross` | valid | `repaired`: swap (1, 3), swap (2, 4), substitute 1 | 3, 4; 1 → 2 | yes |
| vp10 (13 analyses, gpt-4o) | yield ×5, reverse ×5 (sets {1, 2, 4}, {1, 2}, {3, 4}, all four), temporary_wait ×3 | valid 13/13 | `vlm_verbatim` 11, `m3_default` 2 | the strategy the model chose, for the robots it named; 5 of the 11 verbatim plans not dispatched as written | **no** (13/13) |
| smoke `live_20261002` (2 analyses) | jc, `1cross 2wait 3wait 4wait`; then reverse {3, 4}, `3rev 4rev 1continue 2continue` | valid | `m3_default` (inconsistent); then `vlm_verbatim` | 3, 4 then cross (pre-release-phase code); then reverse 3 and 4 | yes; then **no** |
| smoke `episode2_20261002` (5 analyses) | jc, `3cross 1wait 2wait 4wait`; reverse {3, 4} ×2 (one with no plan); jc over 3 and 4 with yield robot_4; jc, no plan | valid | `m3_default`; `vlm_verbatim`; `m3_default`; grounding failed; `m3_default` (plan absent) | 3, 4 then cross; reverse 3 and 4 (×2); nothing; 4, 3, cross failed, fallback reroute | yes; **no**, **no**; not applicable; gate fails |
| s6 (4 analyses, two head-on pairs) | reverse {3, 4}; yield 2; reverse all four; yield 2 | valid 4/4 | `repaired` 2, `vlm_verbatim` 1, `m3_default` 1 | waits, a reroute, and a four-robot reverse | not applicable (no junction default) |

No ER-2 `junction_clear` plan (0 of 20) verified. Every executed recede order equals chi's, and every executed yielder is robot_1. The per-row JSONL (`per_analysis.jsonl`) adds, for each row: the chi costs and margin, the m5 phase trace, the M4-received commands, and the shadow-rule and no-stage-2 counterfactuals.

---

## B. Three-Level Classification

Counts cover the live four-robot analyses above (verified, `per_analysis_table.txt`):

| Level | Intersection ER-2 (24 analyses, 17 bundles) | vp10 gpt-4o (13) | s6 ER-2 (4) | All (41) |
|---|---|---|---|---|
| 1. Valid response | 24 | 13 | 4 | 41 (plus 29 valid `none` answers; 70/70 valid) |
| Plan written in `raw_text` | 22 | 12 | 4 | 38; 3 of these nulled at stage 1 |
| 2. Accepted (`vlm_verbatim`) | 2 (both `reverse` of robot_3 and robot_4; 0 of 20 `junction_clear`) | 11 | 1 | 14 |
| 2. Accepted and dispatched as written | 2 | 6 | 0 | 8 |
| 2. `repaired` with a VLM-caused executed element | 0 | 0 | 0 | 0 |
| 3. Plan changed execution versus no plan (gated rows) | 0 of 22 | 0 of 13 | 0 of 4 | **0 of 39** |
| 0.5 Decision fields changed execution versus the Arm C default (gated rows) | 5 (e09 triggers 1 and 2; three smoke `reverse` answers) | 13 | not applicable | 18, in 4 episodes |
| 0.5 Stage-2 retreat letter changed execution | 1 of 1 answered (e09) | 1 of 2 answered | 0 | 2 |

**`repaired` plans and what came from the VLM.** For each of the 11 repaired intersection plans, the executed recede set, recede order, yielder and passer were checked one by one against the VLM's plan:

- **Recede set:** always {robot_3, robot_4}. It is fixed by geometry, so the plan cannot set it.
- **Recede order:** always chi's.
- **Yielder:** always robot_1, the first yield-axis robot in `involved_robots` (`roles=legacy-convention`).
- **Passer:** always robot_2.

Where the model's plan agreed with these, it was coincidence: the no-plan re-grounding produces the same commands. So no executed element of a repaired plan is the VLM's.

**Against Layer 2 off (Arm B, 2026-11-13).** Without Layer 2, nothing is dispatched and the jam never clears (5/5 censored, reported). Every Arm A dispatch therefore changed behaviour relative to Layer 2 off. Arm C shows that this change comes from having a Layer 2 trigger plus M3's default: a scripted strategy token reproduces it exactly.

**Against the shadow classical rule.** The shadow rule disagreed in every analysis (`any_disagreement=true`). Grounded, its decision is a single two-robot `yield`, for example robot_1 yields to robot_2 on ib10S_e03. It never recedes the cross pair. The rule therefore differs from the executed four-phase sequence in every analysis (verified, `cf_shadow`). Whether it would resolve is not known. The one comparable live case, e09's first `yield`, did not resolve (inferred).

---

## C. Why Plans Were Rejected

### The ib10S_e03 Case (Verified)

- **Model answer** (`raw_text`, prompt version 3, `user_sha256 a8bb1b52…`):

```json
"crossing_order": ["robot_2", "robot_1", "robot_3", "robot_4"],
"proposed_plan": [
  {"robot_id": "robot_4", "action": "reverse"},
  {"robot_id": "robot_3", "action": "reverse"},
  {"robot_id": "robot_2", "action": "cross"},
  {"robot_id": "robot_1", "action": "cross"},
  {"robot_id": "robot_3", "action": "cross"},
  {"robot_id": "robot_4", "action": "cross"}
]
```

- **Rule violated:**
  - `_sanitize_optional_fields` builds the legs and raises `ValueError("duplicate robot_id in proposed_plan")` (`reasoning/vlm/output_parser.py:130-133`). It then nulls the field and tags `proposed_plan=default:invalid_structure` (`output_parser.py:134-136`).
  - The same rule is a schema invariant: "each robot at most once" (`reasoning/vlm/models.py:515-524`).
  - With `proposed_plan=None`, `verify_and_repair_plan` returns `m3_default` with "plan absent" (`reasoning/rag/command_grounder.py:4943-4949`).
  - Re-running the parser rule on the raw plan reproduces the failure (`raw_plan_verdict`).
- **What the prompt said** (`reasoning/vlm/prompt_builder.py`, rendered byte for byte in the artifact):
  - The invitation (`prompt_builder.py:218-224`): "an ordered list naming every known robot".
  - The grammar (`prompt_builder.py:243-260`): one action per entry, with "cross: proceed through in its assigned turn" and "The list order is the execution order".
  - The strategy line (`prompt_builder.py:117-118`): "junction_clear: … some robots first back out, one inside robot yields, then an ordered crossing".
  - The field rule (`prompt_builder.py:120-121`): `yield_robot` must be null unless the strategy is `yield`.
- **Diagnosis:**
  - **Primarily an under-specified prompt.** The prompt never says "each robot exactly once". It describes `junction_clear` as a sequence in which the backing-out robots later cross, and the grammar has no way to give one robot two steps.
  - **The model's plan was otherwise M3's own:** the right pair, in chi order (margin 0.007), with robot_2 crossing first, as M3's yield of robot_1 also has it.
  - **Not a prompt/validator version mismatch.** Both are from the same tree, and the v3.3 grammar text is present.
  - **Not a missing field or wrong key.**
  - A tolerant parse that keeps each robot's first leg would still not verify. It gives `4rev 3rev 2cross 1cross`, which is `repaired` (reorder (1, 2), substitute 1→yield), because the grammar wants the inside robot as `yield`, not `cross`.

### All Rejected, Absent and Repaired Plans

Categories over the 41 live congestion analyses (verified):

| Outcome or edit reason | Count |
|---|---|
| Stage 1 nulled: robot named twice (e01_a1, e09 trigger 3, ib10S_e03) | 3 |
| No plan in the answer (vp10 `d9b1c4a3`; smoke `c781656c`, `bed37d40`) | 3 |
| `m3_default`: repair distance exceeds bound 4 (e09 triggers 1 and 2, vp10 `62b8bbe9`) | 3 |
| `m3_default`: plan inconsistent with the strategy (ep2 and both smoke first answers: one cross and three waits; s6: two yield legs under `yield`) | 4 |
| Grounding failed before verification (smoke `125d841c`, two-robot jc) | 1 |
| `repaired` | 13 |
| Edit: `reverse` leg on a non-structural (yield-axis) robot | 21 edits |
| Edit: `cross` leg without a releasing `yield` leg | 9 edits |
| Edit: structural recede candidate without `reverse`; cross listed before a recede | 1 + 1 edits |
| Edit: reverse would traverse the corridor (s6) | 2 edits |
| `vlm_verbatim` | 14 |

### What "Wrong Pair" Meant (Verified, With One Inference)

The 2026-11-14 report says the proposed recede pair was wrong in all four Arm A episodes that had a parsed plan (e01, e05, e07, e09). The bundles confirm that all four fail the structural rule (`_plan_problems`, `command_grounder.py:3926-3965`), but "wrong" means two different things:

- **The right pair plus an inside robot labelled `reverse`** (e01: `1rev 3rev 4rev`; e09: `4rev 3rev 2rev`).
  - The extra robot is the inside yielder the strategy description asks for.
  - The model used `reverse` (straight back along its own lane) where the grammar's `yield` (back up and step aside) was needed.
  - Inference: a straight reverse would leave that robot in the passer's lane, so this is a vocabulary error, not a bad pair.
  - Across the 15 four-robot `junction_clear` plans of 2026-10-03 to 2026-11-14, the model's inside backer was robot_2 in 4 plans. M3's convention always yields robot_1.
- **The axis-mirror pair** (e05: `1rev 2rev`; also e03 and cal_ep1 in other runs) and **robot_1 alone** (e07).
  - The recede set is not checked for physical feasibility. `_junction_recede_candidates` (`command_grounder.py:1563-1593`) defines it as the robots off the declared `corridor.axis` (`x`), a scene convention.
  - Inference only: the IB10 scene is symmetric (no obstacles, 1.75 m arms). Re-grounding the snapshots with the axis flipped gives an analogous four-phase plan for robot_1 and robot_2 with similar distances (0.75-1.03 m; `mirror_axis_probe.jsonl`). This is not a physical proof.

So the earlier finding holds as a statement about M3's structural rule. It does not show the plans were infeasible.

---

## D. Does the Architecture Let a VLM Plan Influence `junction_clear` Execution?

**The plan cannot influence dispatch, except through one switch that was never enabled.** The code path (verified):

1. **Grounding never reads the plan.** `ReasoningPipeline` grounds `grounded = self._ground_fn(result, …)` (`reasoning_pipeline.py:1606-1617`) and, for `junction_clear`, `ground_junction_clear_phases(result, …)` (`reasoning_pipeline.py:1665-1677`). Neither reads `proposed_plan`; the only reads in `command_grounder.py` are in `verify_and_repair_plan` (`4943-4971`). This was also true at `a8fc1bc`.
2. **The plan is verified after grounding** (`reasoning_pipeline.py:1638-1652`). The result only sets `provenance`, `edits`, the tracked legs and `dispatch_matches_plan` in the artifact.
3. **The one plan-to-dispatch path** is `plan_dispatch_order_source: model_when_verified` (`swarm_orchestrator/models.py:466-474`, `reasoning_pipeline.py:1708-1757`).
   - If the plan verified `vlm_verbatim`, it re-grounds with `recede_order=plan_recede_order(verified.legs)`.
   - It changes only the temporal order of the recede phases. Pockets, cross, release and fallback stay keyed to chi rank (`command_grounder.py:2680-2702`, `2930-2945`).
   - Every recorded artifact has `plan_dispatch_order_source` `chi` or absent. None of the 3,265 indexed artifacts, nor the 12 flat smoke artifacts, has `dispatch_order_source=model` (verified).
   - The flag landed in `a98574b` (2026-10-07) with 26 unit tests, which pass on this tree. It has never run on the VM.
4. **A secondary plan read:** `continue` legs feed `plan_continue_partners` on a `reverse` (`orchestrator_node.py:1648-1665`). This is safety-exemption metadata, not motion. It is not logged in vp10's `m4.log`, so whether it fired there could not be verified.

Which executed `junction_clear` quantities can come from the VLM:

| Quantity | Source in this runtime | Can the VLM set it? |
|---|---|---|
| Recede set | `_junction_recede_candidates`: robots off `corridor.axis` | No (any other set fails verification) |
| Recede order | `rank_recede_candidates` (chi) | Only with `model_when_verified`, `vlm_verbatim`, and within ε = 0.15 of chi |
| Recede distances, pockets | `recede_distance_m` at the chi-rank pocket | No |
| Yielder (cross phase) | `_as_yield_decision` keeps `decision.yield_robot` if it is on the yield axis, else the first yield-axis robot in `involved_robots` (`command_grounder.py:4221-4256`) | **Yes, through the decision fields**, but the prompt says `yield_robot` must be null for `junction_clear`, and ER-2 always lists robots in ascending order |
| Passer, crossing order | The other yield-axis robot. The model's `crossing_order` is discarded (`order=discarded_yield_axis`) | No |
| Pull-off side, retreat | Stage 2 runs only for `strategy == "yield"` (`reasoning_pipeline.py:1559-1583`). `junction_clear` gets `retreat=default:no_choice` | No |
| Release order, holds | chi rank 0 leads; config hold times | No |

**The yield feasibility gate was off in every run.** Every analysed artifact, including the Arm C and closure controls (49 congestion artifacts), records `grounding_yield_feasibility: off` (verified). This is the gate that room-checks the yielder; verification of recede legs and M4's latch were on.

**What `dispatch_order_source: chi` is.** chi is `recede_cost`: `junction_recede_cost_space_weight` × recede distance plus `junction_recede_cost_follower_weight` × followers (`maneuver_geometry.py:930-940`). The recede phases are dispatched in ascending chi order. Under the default `chi` mode this order overrides the VLM's unconditionally.

Under the chi-epsilon rule a plan whose recede order inverts chi still verifies `vlm_verbatim` when the margin is below 0.15 (`recede_orders_equivalent`). The robots then execute chi's order regardless. Closure R1 is the recorded instance: its plan said robot_4 first, robot_3 receded first (chi margin 0.055), and the artifact records `vlm_verbatim`, `order_equivalent=true`, `dispatch_matches_plan=true` (verified).

**Verified yielder gap.** For every recorded snapshot, a well-formed plan naming robot_2 as the yielder (`P_y2`: chi order, robot_2 yield, robot_1 cross) verifies `vlm_verbatim`. Dispatch still yields robot_1, and `dispatch_matches_plan=false` (15/15 live and 5/5 Arm C snapshots). This is an accepted plan that is not executed.

**October verbatim and closure runs against live runs.** Three things differed:

- **Closure (mock):** the mock plan was M3's default written in the grammar (`config/mock_decisions/intersection_junction_clear_vlm_verbatim_once.json`: `4rev 3rev 1yield 2cross`). It verified because it matched the convention, not because a plan was executed.
- **vp10 (gpt-4o):** it reached `vlm_verbatim` 11 times because its strategies (`reverse`, `temporary_wait`, multi-passer `yield`) carry no leg constraint or only weak ones (reported in `2026-10-06-verbatim-pilot.md`, re-verified here). The commands came from its strategy fields.
- **Config:** the same in all of them: `plan_channel_enabled: true`, `plan_dispatch_order_source` defaulting to `chi`, repair bound 4, prompt v3.

No live-model four-robot episode reached `vlm_verbatim` for `junction_clear`, nor a repair that kept the VLM's order (verified).

Outside the four-robot scope, the five-robot `s1b_*` / `v4pcs_*` ER-2 bundles hold 7 live `junction_clear` `vlm_verbatim` plans. All 7 have `dispatch_matches_plan=false` (verified from the scan, not analysed further).

---

## E. vp10 and e09: Where the VLM's Choice Visibly Changed What Ran

**vp10 (gpt-4o, 2026-10-06, tree `a8fc1bc`).**

- At 35.3 s gpt-4o chose `yield`: robot_1 yields, with crossing order robot_2, robot_3, robot_4.
  - The plan went `m3_default` (bound).
  - The grounder dispatched a two-robot yield, robot_1 → robot_2.
  - Its stage-2 letter set the pull-off to +0.36 m. Without that answer it would be −0.36 m (verified, `cf_no_stage2`). The yield failed.
- At 67.1 s it chose `reverse` for robot_1, robot_2 and robot_4, leaving robot_3 as `continue`.
  - M4 received `reverse` for exactly those three (verified, `m4.log`) and nothing for robot_3.
  - This is the "three reverse while the fourth continues" episode.
- Eleven more dispatches followed (reverse, temporary_wait, yield). Three of the yields became reroutes (`03e4bf76`, `3cbf3c39`, `2262686d`).
- Every dispatch differs from the Arm C default on the same snapshot, which is a four-phase recede, yield and release (verified, 13/13).
- All 13 no-plan counterfactuals are identical to what ran. The difference came from gpt-4o's strategy and robot-set fields, not its plans.
- The episode ended clogged, 0/4 (reported in the pilot report).
- **Negative evidence of influence:** the VLM steered execution, and away from the sequence that resolves.

**e09 of 2026-11-13 (ER-2).**

- **Trigger 1 (31.3 s):** `yield` instead of `junction_clear`.
  - Executed: one yield, robot_1 → robot_2, pull-off +0.36 m from the VLM's stage-2 letter (default −0.36 m).
  - robot_3 and robot_4 were never commanded.
  - The default would have been the four-phase sequence (verified).
- **Trigger 2 (108.0 s):** `junction_clear` naming only robot_2 and robot_4.
  - M3 receded robot_4 and held robot_2 for 8 s with no passer ("yield refused").
  - All four robots then stood still for 120.1 s (reported).
  - The default on that snapshot would again be the four-phase sequence (verified).
- **Trigger 3 (244.6 s):** all four robots.
  - The plan was nulled for repeating robots. The 2026-11-13 report says the model answered `proposed_plan: null`; it did not (section G).
  - M3's default ran, but its cross phase had not resolved by the end of the episode (`m5.log`).
- 0/4 arrivals.
- **The second piece of evidence that the VLM changes behaviour, and again for the worse.**

---

## Comparison Matrix

Options for a demonstration of genuine VLM influence, each keeping M3 verification and M4 safety on:

| Criterion | (i) Prompt fix only | (ii) Order from a verified plan (existing flag) | (iii) (ii) on a scene with two feasible orders | (iv) Scene where the default is worse |
|---|---|---|---|---|
| Code change | Prompt text, new pinned version | None: `plan_dispatch_order_source: model_when_verified` exists | Same as (ii); IB10 already qualifies | New scene and evidence; unknown |
| Changes execution alone? | **No.** The grounder never reads the plan (section D) | Only for `vlm_verbatim` plans whose order differs from chi within ε | Same | Unknown |
| Offline result on the 15 recorded four-robot ER-2 `junction_clear` snapshots of 2026-10-03 to 2026-11-14 (the 2026-10-02 smoke snapshots predate the release phase and were left out) | 0 verbatim strict; 0 with first-leg tolerance | 0 would have changed dispatch (no recorded plan verified) | 13/15 live and 5/5 Arm C snapshots are within ε; a swapped well-formed plan verifies and moves only the recede phases | No evidence |
| What stays enforced | All | Recede set, ε bound, pockets, release, fallback, M4 latch | Same | — |
| Evidence the demo would produce | None | "VLM order X verified; chi was Y; M4 received X" | Same; both orders already ran safely (below) | — |
| Main risk | No effect | A verbatim plan is still rare with the current prompt | The swapped temporal order has never run live | No basis |

**Two orders, both safe in recorded runs (verified).**

- Recede order robot_3 first executed and resolved 4/4 in ib10L_e03, ib10L_e05, ib10S_e01, Arm C e08, e10 and e02_a2, and in vp09, ep2 and cal_ep1. The October outcomes come from the verbatim-pilot table and the bundles' `ib10_score.json`.
- robot_4 first executed and resolved 4/4 in the other November episodes (except e09) and in vp08.
- The two branches are 0.60-0.67 m RMS apart in trajectory (2026-11-14 report). The choice is visible.
- **Caveat:** in every recorded run the first robot to recede was the chi-rank-0 robot, which takes the deeper pocket. Under (ii) a model-ordered swap makes the rank-1 robot (shallower pocket) recede first, while pockets and release stay chi's. The end state is identical by construction (`command_grounder.py:2680-2702`), but this temporal order has never run (inferred to be safe; not demonstrated).

---

## Decision

**Recommendation:** run option (ii) on the existing IB10 scene, which is (iii), with two supporting prompt changes. All checks stay on.

1. **Enable the existing flag:** `plan_dispatch_order_source: model_when_verified` in the Arm A overlay. No code change. Verification and the M4 latch stay on. Verification still sets `m3_default` or `repaired`, and so chi dispatch, for any plan with:
   - a wrong recede set;
   - an order beyond ε;
   - a cross listed before a recede;
   - a missing releasing yield.
2. **Make a verbatim plan reachable.** No recorded ER-2 `junction_clear` plan verified, so the flag alone would change nothing (0/15 four-robot `junction_clear` plans, offline).
   - **(a) Two generic grammar sentences:** "Name each robot exactly once; its one action is its role in the resolution" and "A cross leg must come after the yield leg that releases it".
     - This is a prompt-builder edit (`_PLAN_GRAMMAR`, about 3 lines) with a new prompt version and pins.
     - The first removes the invalid-structure cause (3/41). The second states the rule behind 9 edits ("cross leg without a releasing yield leg"), which `_plan_problems` already enforces but the prompt never shows.
     - That rule is what kept the two closest recorded plans at `repaired`: ib10L_e05, and ib10S_e03 after first-leg tolerance.
   - **(b) The existing `prompt_candidate_options: true` condition**, which lists per robot the actions M3's audit accepts. At IB10 it offers `reverse` only to robot_3 and robot_4 (verified, `order_channel_v7i.jsonl`). That addresses the dominant repair cause: `reverse` on a yield-axis robot, 21 edits.
   - This is a declared construct change: plans measure constrained selection, not free planning (`swarm_orchestrator/models.py` comment at `prompt_candidate_options`).
   - Even with (a) and (b), verbatim plans may stay rare. ER-2's rate under the new text cannot be measured without model calls. The recorded answers cannot show it, because they were written under the old prompt.
   - **Feasibility gate:** it was `off` in every recorded run. Re-running the prototype under `swap` and under `refuse` gives the same outcomes as `off` for all four synthetic plans on every snapshot (verified, `order_channel_v7i_yfm_*.jsonl`).
   - Turning it on (`yield_feasibility_mode: swap`) therefore costs nothing offline, but it departs from the recorded Arm C baseline. This is an owner decision.
3. **Score the demo on one quantity**, per decision:
   - the VLM's recede order;
   - its verification verdict;
   - chi's order on the same snapshot;
   - the order of `junction-recede-*` commands in `m5.log` and `m4.log`;
   - `dispatch_order_source`.
   - A genuine-influence event is `vlm_verbatim`, VLM order ≠ chi, and executed = VLM order.
4. **What the demo would and would not show.**
   - It shows causal control authority: the VLM's choice decides which arm moves first, verified as feasible.
   - It does not show that the VLM chooses better. chi rates the two orders as equivalent within ε. No recorded evidence supports option (iv).
   - The recorded behaviour suggests ER-2 orders by robot id rather than by scene reasoning:
     - it listed the structural pair ascending (3, 4) in 6 of the 9 plans that reversed both, and descending in 3;
     - its order disagreed with chi in 3 of those 9 (e01_a2, e07, vp08).
   - Expect a minority of decisions to differ from chi (inferred).

**Offline validation done** (`prototype_order_channel.py`, the runtime's own functions, replaying `reasoning_pipeline.py:1708-1757`):

| Plan on each recorded snapshot | Verdict | Under `model_when_verified` |
|---|---|---|
| `P_chi` (chi order, robot_1 yield, robot_2 cross) | `vlm_verbatim` 15/15 live, 5/5 Arm C | identical to the default |
| `P_swap` (chi order reversed) | `vlm_verbatim` 13/15 live, 5/5 Arm C; `repaired` on ib10L_e03 (margin 0.151) and e09 trigger 3 (0.182) | only the recede phases move; cross, release and fallback identical; `dispatch_matches_plan=true` |
| `P_y2` (robot_2 yield) | `vlm_verbatim` 15/15 | yielder stays robot_1; `dispatch_matches_plan=false` (yielder gap) |
| `P_axis` (robot_1/robot_2 reverse) | `repaired` 14, `m3_default` 1 | chi, unchanged |
| Recorded raw plans: strict / first-leg / intent-normalised (diagnostic only) | 0 / 0 / 2 verbatim | 0 would have changed the dispatched order |

`tests/unit/test_dispatch_order_source.py`: 26 passed on this tree.

**Before any VM run, still offline:**

- Render the candidate-options prompt on the recorded IB10 snapshots and check the text.
- Add a unit test that replays the 24 recorded intersection raw answers through parse → verify → `model_when_verified` and pins the 0-change result.
- Add one test that a within-ε swapped plan dispatches the swapped order with the same pockets and release (already covered by `test_model_mode_*`; extend with a recorded snapshot).

Decide the yielder gap first. Either make verification reject a `junction_clear` yield leg that dispatch will not execute (safe: it only narrows acceptance), or leave it and report `dispatch_matches_plan=false` honestly.

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| The swapped temporal order (rank-1 robot recedes first) has never run live | Held robots and the M4 latch stay on, and the end state is identical by construction. Gate the first run on a key-on smoke as on 2026-11-14 |
| The model still rarely produces a verbatim plan, so the demo shows nothing | A mock cannot measure this. After the owner rules, a handful of single-call probes on recorded frames with the new prompt text would estimate the verbatim rate before any VM run |
| "Verbatim" is read as "executed" | Report `vlm_verbatim`, `dispatch_order_source` and the m5 and m4 order side by side. Closure R1 shows that verbatim alone proves nothing |
| The candidate-options condition makes the choice constrained | Declare it as constrained selection among verified options. The claim is control authority, not free planning |
| The yielder gap (`P_y2`) produces accepted-but-not-executed plans | Fix it in verification before the run, or score it explicitly |

---

## G. Contradictions With Earlier Reports

| Earlier claim | Finding (verified) |
|---|---|
| 2026-11-14: "in e03 the VLM gave a strategy token only" | ER-2 wrote a six-leg plan with the correct pair in chi order. The parser nulled it for naming robot_3 and robot_4 twice |
| 2026-11-13: e09 trigger 3 "answered `junction_clear` with `proposed_plan: null`" | The model wrote `2rev 1yield 4cross 3cross 1cross 2cross`. The parser nulled it (robot_1 and robot_2 repeated) |
| 2026-11-14: "proposed pair wrong in all four" | True under the structural rule. In two of the four (e01, e09) the pair was right, plus the inside yielder labelled `reverse` (section C) |
| 2026-11-14: e01 and e09 retreat side "not a model choice" | Confirmed for 2026-11-14 (no stage-2 block). On 2026-11-13, e09 trigger 1 did have a stage-2 answer, and it flipped the pull-off side |
| 2026-11-13: "4 repaired, 1 m3_default"; "M3 repaired the model's plan back to its own default" (2026-11-14) | Confirmed. Strictly, repair never feeds dispatch: the dispatched commands are identical with no plan at all |
| 2026-11-14: Arm C re-grounding reproduces the executed phases | Confirmed, and extended to all gated intersection ER-2 analyses, the October pilots, and the plan-absent counterfactual |
