# Convoy Non-Arrival and the Counterflow Yielder Swap

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: why the five convoy demo takes did not arrive; options; the default-off counterflow yielder swap; tests; offline replay; safety review; the `cvy` rerun kit (prepared, not launched).

---

## Summary

- **Why no take arrived (verified from bundles, GT and code).**
  - Takes 1–3 (no hold): the model's first decision named only the standoff pair, so the two queued robots were released uncommanded and followed the passer through the gate. All four latched under M4's 0.45 m distance.
  - Takes 4–5 (hold on): the queued robots were held, but the model chose robot_1, the platoon-side robot, as yielder. robot_2 was then escorted toward the held platoon and latched 0.418 / 0.419 m from robot_3. Only robot_1 arrived (1 of 4).
- **General cause.** A legacy corridor yield parks the yielder on its own side and escorts every passer through the gate to that side. It can only work when every robot that crosses after the yield starts on the opposite side, that is, when all crossers travel the same direction.
- **The existing gate does not help (verified by running).** `grounding_yield_feasibility: swap` scores only static-obstacle retreat room. The convoy declares no static obstacles, so the gate never fires: 0 of 49 first-trigger yields change.
- **Fix (built, default off).** The key `grounding_yield_counterflow_swap`, branch `fix/convoy-yielder-feasibility`, worktree v7t, commit `a0311b0`.
  - When a legacy single-corridor yield's crossing order (with the hold's added robots) has a crosser on the yielder's park side, the yield is handed to another named robot whose crossers all start opposite it. If no named robot qualifies, the yield is refused.
  - This follows the head-on gate's precedent: `yield_robot_grounded_from`, `yield_regrounded_reason` and the M5 `yield re-grounded … from= to= reason=` line, plus a tag.
  - 51 unit tests pass, including mirrored geometry, a y-axis corridor and a shifted centre.
- **Replay (verified by running, offline, no model calls).** With the hold and the fix, all 49 first-trigger yields ground into the smoke's resolving sequence:
  - 27 where the model chose robot_2 (unchanged from hold-only);
  - 22 where it chose robot_1 (swapped).

  Hold-only reaches 27 of 49. Every one of 43 later convoy decisions and 15 head-on, intersection and five-robot decisions is unchanged.
- **Live, still uncertain.** The robot_2 sequence has resolved once (smoke, n = 1, not owner-accepted). Its closest non-exempt pair was 0.495 m, 0.045 m above the latch distance, and earlier scene replicates cleared it by only 0.013–0.025 m. Four-stack bring-up fails about 3 times in 8.
- **Kit.** `demo_campaign/cvy/kit` is built and `TEST_DRY_DMC cvy OK`. It has not been launched. Under the 5,400 s sub-cap it allows one take, not two (section 7.3).

---

## 1. Part A: What Happened in Each Take

Scene `convoy_counterflow_slip`, seed 42 (header of `isaac/config/scenarios/convoy_counterflow_slip.yaml`):

- the gate is the C55 barrier at x = 0, `half_length_m` 0.5;
- robot_1 (−1.2, 0), goal (2.45, −0.36), leads the eastbound platoon;
- robot_3 (−1.90, 0), goal (2.45, +0.36), and robot_4 (−2.47, 0), goal (1.85, 0), queue behind it, held by M5's 120 wall-s start delay;
- robot_2 (1.2, 0), goal (−2.0, 0), is the westbound counter-flow robot.

The robot_1/robot_2 standoff forms at about 25 sim-s. End positions below are GT at 260 s; arrival means GT within 0.35 m of the goal. The script is in the session scratchpad and its outputs are quoted here.

| Take | robot_1 | robot_2 | robot_3 | robot_4 | Event that blocked arrival |
|---|---|---|---|---|---|
| 1 `cvD_t01_a1` (model: yield robot_2) | linked wait, escorted east 1.898 m; end (1.71, 0.00), 0.83 m short | yield: backup 0.903 m to park x 1.124, lateral 0.36; end (1.13, −0.38) | no command; released about 50 s, followed through the gate; end (1.31, 0.19) | no command; released, followed; end (0.81, −0.10) | from about 75 s, latch pairs robot_1–robot_3 0.437 m and robot_2–robot_4 0.42 m (non-exempt after `gate_release … hold_timer`); escort `FAILED … timed out in phase drive` |
| 2 `cvD_t02_a1` (model: yield robot_1) | yield: backup 0.993 m to park x −1.124; end (−1.13, 0.37) | escorted west 1.904 m; end (−0.90, 0.01) | no command; released, drove east into robot_2; end (−1.31, −0.01) | same; end (−1.69, −0.16) | from about 70 s, four pairs at 0.411–0.425 m west of the gate |
| 3 `cvD_t03_a1` (model: yield robot_2) | as take 1, escort 1.807 m; end (1.61, −0.01) | as take 1, backup 0.88 m; end (1.13, −0.38) | as take 1; end (1.21, 0.17) | as take 1; end (0.83, −0.09) | as take 1: robot_1–robot_3 0.436 m, robot_2–robot_4 0.42 m |
| 4 `cvH_t04_a2` (hold; model: yield robot_1) | yield: backup 0.986 m to park x −1.124; after `gate_release` at 189.8 s drove east and **arrived at 211.1 s** | escorted west 1.913 m; stopped at x −1.48, 0.52 m short | held (linked wait 1), never admitted; did not move | held (linked wait 2); crept 0.17 m after `gate_release` | robot_2's escort latched 0.418 m from held robot_3 at 72.5 s (non-exempt pair), escort timed out; robot_4 then 0.399 m from robot_3 |
| 5 `cvH_t05_a1` (hold; model: yield robot_1) | as take 4, backup 0.918 m; **arrived at 208.5 s** | escorted west 1.98 m; end (−1.48, 0.00) | as take 4 | as take 4 | robot_2–robot_3 0.419 m at 78.2 s; robot_3–robot_4 0.394 m |

Sources: campaign report v7j `docs/reports/2026-11-15-demo-campaign-results.md` sections 5.1–5.2 and 12.2–12.4 (m4/m5 lines), and GT `gt/ground_truth.jsonl` of each bundle, re-read here.

### 1.1 The Mechanism

`_ground_legacy` sets up the yield as follows:

- the yielder parks on its own side, away from the first passer: `side = -1` when its x is below the passer's;
- the park point is `park_offset_m` 1.124 from the centre, with a 0.36 m pull-off;
- every passer is escorted through the gate to the yielder's side, past the park point plus `passer_clearance_m`;
- M4's `crossing_chain` admits the passers in order.

The escort for this scene ends at x = 1.774 on the yielder's side (scene header).

- **Yielder robot_2 (east, the non-platoon side).** The passers robot_1, robot_3 and robot_4 all start west and all travel east, nose to tail. Nobody waits on the east side, so no escort runs into a waiting robot. This is the smoke's executed sequence (v7f `cvL_e01_armC_a1` m4: `gate_admit` robot_1 at sim 51.97 s, robot_3 at 74.03 s, robot_4 at 115.23 s, `gate_release … reason=clearance` at 162.8 s). It resolved 4 of 4, with GT arrivals at 76.3, 117.4, 159.1 and 181.1 s.
- **Yielder robot_1 (west, the platoon side).** The only robot that crosses toward the yielder's side is robot_2, escorted west to about x = −1.77. robot_3 and robot_4 wait exactly there, at x −1.90 and −2.47, to cross east. M4 exempts only the yielder–passer pair, so robot_2–robot_3 keeps the full 0.45 m latch. The scene file pre-states this outcome: "yielding robot_1 instead escorts robot_2 west to x −1.774, 0.13 m from the held robot_3 (a latch)".

### 1.2 When a Convoy Yield Is Feasible (General Terms)

A single-corridor yield with several crossers can resolve only if all of the following hold:

1. **Every crosser is held.** Every robot whose goal lies across the corridor is in the command, holding until its turn. If not, it follows the passer uncommanded (takes 1–3).
2. **Every crosser starts opposite the yielder.** No robot waits on the yielder's park side to cross the other way, because it occupies the passers' exit (takes 4–5).
3. **The order runs nose to tail.** The first passer is the robot nearest the yielder (the existing first-passer check).
4. **The yielder can actually retreat.** It has room to park (the existing room gate). It and the first passer are not both past the same corridor mouth (the existing same-side check).
5. **The goals leave room.** The passers' goals on the yielder's side leave at least the latch distance to the parked yielder and to each other. This is scene geometry, with a thin margin here (section 5).

---

## 2. Part B: Options

### 2.1 Existing Configuration Only: `grounding_yield_feasibility: swap` (Verified by Running; Insufficient)

- **What the gate checks.** `_apply_yield_feasibility` scores each involved robot's retreat room. It measures from the corridor mouth on its side to the nearest static obstacle in the aisle band (`yield_retreat_room_m`), against `required_room_m`. Robots are not obstacles to it.
- **Does it run in legacy mode?** Yes: `_ground_legacy` calls it when the mode is not `off`.
- **Result here.** The convoy overlay declares `static_obstacles: []`, so every room is unbounded and every yielder is feasible. On all 49 first-trigger yields (takes 1–3, takes 4–5, the smoke and the 44 stored answers) the gate returns no swap and no refusal. robot_1 passes it.
- **Why it cannot be configured to help.** No obstacle list can express "a held robot of the platoon stands on this side", because the gate reads no robot poses.
- **Verdict.** Option 1 is not a fix.

### 2.2 A General Counterflow Condition as a Default-Off Key (Chosen; Built)

The condition is "every robot the yield sends through the gate starts on the side opposite the yielder's park side", and it is read from runtime state only:

- snapshot poses and goals;
- the declared corridor axis, centre and half-length;
- the hold's own `traverses_corridor` predicate for the added robots.

It uses no robot ids and no scenario constants.

**Why this is a feasibility check, not a hardcoded answer.**

- **Mirrored geometry.** With the platoon on the east side behind robot_2, the same code swaps the other way: model robot_2 → robot_1 (unit test `test_mirrored_platoon_swaps_to_the_other_robot`).
- **The model's choice is respected.** When the model's yielder is already feasible, the command is identical to hold-only grounding.
- **It never picks the platoon.** It hands the yield only to another robot the decision names. With platoons on both sides it refuses through the existing refused-yield path.

### 2.3 Other Ideas (Not Built)

| Idea | Risk / why not |
|---|---|
| Exempt the escorted passer against held robots | Relaxes the latch for robots not in the manoeuvre. Excluded by the owner's rules. |
| Shorten the escort so robot_2 stops short of robot_3 | robot_2 would still be the wrong-way crosser, with no path past the queue. It shortens a safety-sized clearance. |
| Re-sequence (move the platoon first, then let robot_2 cross) | This is the same as yielding robot_2, just reached by a new M4 sequencing mode. Larger, and it touches M4. |
| Prompt the model about the platoon side | Changes registered prompt bytes. The earlier held-state prompt check moved plan legs but not the structure (0/44 four-robot answers). |
| Make the room gate count held robots as obstacles | Mixes two checks. A held robot behind a yielder is not a retreat-room problem: robot_1 has room. The conflict is the passer's exit. |

---

## 3. The Fix

### 3.1 Key and Scope

**Key.** `grounding_yield_counterflow_swap: bool = False` (`OrchestratorConfig`). M5 passes `yield_counterflow_swap=True` to `ground_reasoner_result` and `verify_and_repair_plan` only when the key is on.

**Scope.** Exactly the hold's scope:

- legacy grounding (`params.mode` legacy or None);
- a snapshot is present;
- a plain single corridor (`is_single_corridor`);
- `strategy == "yield"`, after the convoy/priority alias.

### 3.2 Logic (`command_grounder.counterflow_yield_outcome`)

1. **Leave existing refusals alone.** Run the room gate (if on), the first-passer check and the corridor same-side check on the model's yield. If any of them refuses, do nothing: that refusal stands.
2. **Look for counterflow crossers.** Build the crossing order the command would carry: the named passers, plus the hold's added robots when the hold is on. `counterflow_crossers` lists every one standing outside the corridor on the yielder's park side, where the side comes from the same expression `_ground_legacy` uses. An empty list means nothing changes.
3. **Try the other named robots.** Take them in `involved_robots` order. Each must pass the room gate (if on). With it as yielder, its passers ordered by distance to it, it must pass the same checks and give an empty counterflow list. The first that qualifies yields. The rewritten decision carries its full crossing order and is grounded exactly like a decision that named it.
4. **Refuse if none qualifies.** The reason is `yield refused: counterflow: no yielder whose crossers all start on the far side (…)`, and the wait fan-out goes to the named robots only.

### 3.3 Records

- **Swap.**
  - On the yield action: `yield_robot_grounded_from` = the model's yielder, and `yield_regrounded_reason` = `yield re-grounded: counterflow: robot_1 parks on the side where robot_3, robot_4 wait to cross the other way; robot_2 feasible`.
  - In the artifact: the same two fields.
  - In the M5 log: `yield re-grounded request=… from=robot_1 to=robot_2 reason=…`.
  - Tag `yield=counterflow_regrounded:<from>:<to>`, registered in `DEGRADATION_TAGS` as provenance.
  - The artifact's `decision` stays the model's own.
- **Refusal.** Tag `yield=counterflow_refused:<model yielder>`, cause `infeasible_geometry`.
- **Plan verifier.** On a swap:
  - M3's default plan yields the new robot;
  - a `_PlanYieldVerdict` names it, so a `yield` leg on any other robot fails;
  - the repair's yield-touching `swap` op is allowed only when such a verdict names a yielder. The derived retry domain already implies the room gate's `swap` mode, so this changes nothing there.
  - The model's `[robot_1 yield, robot_2 cross, robot_3 continue, robot_4 continue]` becomes `repaired` with 3 edits (1 `swap` + 2 `queued crosser hold:` substitutes; bound 4), and `dispatch_matches_plan=true`.
  - On a refusal: the default plan is the waits, and a plan with a yield leg is `plan unrepairable: yield refused: counterflow: …`.

### 3.4 Startup Line

With both keys on:

```text
plan order condition plan_dispatch_order_source=chi prompt_plan_grammar_rules=False prompt_candidate_options=False grounding_hold_queued_crossers=True grounding_yield_counterflow_swap=True
```

### 3.5 Files (`a0311b0`, Base `fix/convoy-hold-queued-robots` `d85d1ed`)

| File | md5 now |
|---|---|
| `reasoning/rag/command_grounder.py` | `c6ce7120a70619db0d90d2e3204da55d` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` | `738710977c48bf8ade3ccb5e0a021309` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` | `add660823aba751c42ad490147c02dd5` |
| `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` | `815e2ec3057fa8ae734caf325a1b6349` |
| `tests/unit/test_counterflow_yielder.py` | new, 51 tests |

`scene_geometry.py` (`eda27ce7`) and the two `reasoning/vlm` files are unchanged from the hold branch. Replay script and outputs: `a7635b7`.

---

## 4. Tests (Verified by Running; One Pytest Process at a Time, Targeted Files)

**`tests/unit/test_counterflow_yielder.py`: 51 passed.** It covers:

- **Predicate:** park-side crossers listed; opposite starts give an empty list; robots inside the corridor are ignored.
- **Outcome:** swap with reason; feasible yielder left alone; a pair yield without the hold is a no-op.
- **Grounding** on the take-1 and take-2 frames:
  - the swap gives the smoke structure;
  - the swap equals hold-only grounding of the feasible yielder, apart from the two provenance keys and the tag;
  - provenance keys and tag recorded;
  - feasible model yielder identical to hold-only;
  - key off byte-identical to hold-only, and both keys off byte-identical to the default.
- **Geometry variants:** the mirrored platoon swaps to the other robot and keeps the other robot's feasible choice; y-axis corridor; shifted corridor centre.
- **Named-all-four:** with the platoon-side yielder it is swapped, both with and without the hold, and equals the feasible named-all-four command.
- **Refusals and modes:** platoons on both sides → refusal, with waits on the named robots and the refusal tag; the existing same-side refusal is unchanged; the room gate in `swap` and `refuse` modes composes; no-op in derived mode, with arms, for non-yield and without a snapshot.
- **Verifier:**
  - one swap plus 2 prefixed substitutes;
  - the plan matches the dispatch (plan present or absent);
  - an absent plan defaults to the feasible yielder;
  - key off is identical to hold-only;
  - feasible model yielder identical;
  - refusal → `m3_default` waits;
  - derived-mode no-op.
- **M5:**
  - the pipeline dispatches robot_2 with `repaired` and a matching plan;
  - the default pipeline passes no new keyword;
  - hold-only unchanged;
  - the artifact keeps the model's decision and records `yield_robot_grounded_from` and the reason;
  - config default off;
  - exact startup line;
  - `_build_default_pipeline` receives the key.

**Neighbouring suites on this branch.**

| Suite | Result |
|---|---|
| `test_queued_crosser_hold.py` | 51 passed |
| `test_plan_verifier.py` | 982 passed, 128 skipped |
| `test_command_grounder.py` | 74 passed |
| `test_m5_reasoning_pipeline.py` | 112 passed, 1 failed |
| `test_m5_node_plan_channel.py` | 13 passed |
| `test_m5_node_grounding.py` | 19 passed |

The 1 failure, `test_write_decision_artifact_preserves_m2_result_on_grounding_failure`, also fails on the unchanged v7o tip (checked) and is the base failure the hold report lists.

**Import path check.** Pytest from v7t imports v7t's `command_grounder.py` and M5 `models.py`; the paths were printed.

**Full unit suite: pending.** Swap free was 0.45–1.5 GB, below the 2 GB rule.

---

## 5. Part C: Offline Validation

### 5.1 Method

Harness `scripts/convoy_counterflow_yielder_replay.py {first,later,other} --docs-root /Users/tuanhdangdinh/Documents`:

- **Pipeline.** M5's `InProcessPipeline._run_from_result` on each artifact's own config and legacy params, with no model call.
- **Three arms:** `off` (both keys off), `hold` (hold only) and `fix` (hold plus swap).
- **Output.** Written to `data/experiments/2026-11-15-convoy-counterflow-yielder-replay/` only. Summary md5s:
  - `first_summary.json` `32e7934b`;
  - `later_summary.json` `dfd09b4e`;
  - `other_summary.json` `0dea0717`.

**Gates (all passed).**

- The `off` arm reproduces the recorded dispatch of takes 1–3 and the smoke (4/4).
- The `hold` arm reproduces takes 4–5 (2/2), which ran with the hold on.
- The `hold` arm equals the committed hold-replay `on` rows (48/48).

### 5.2 First Triggers (50 Answers: 49 Yields and 1 `reverse`)

"Resolving" means: yield robot_2, `crossing_order` [robot_1, robot_3, robot_4], linked waits robot_1 → 0, robot_3 → 1, robot_4 → 2.

| Answers | Model's yielder | n | Resolving: off / hold / fix | Swapped (fix) | Plan provenance (fix) | Edits (fix) | Plan matches dispatch | Fix = hold-only grounding of the feasible yielder |
|---|---|---|---|---|---|---|---|---|
| Live takes 1, 3 | robot_2 | 2 | 0 / 2 / 2 | 0 | `repaired` 2 | 2 substitutes | 2 | — |
| Live take 2 | robot_1 | 1 | 0 / 0 / **1** | 1 | `repaired` | swap + 2 substitutes | 1 | 1 |
| Live takes 4, 5 (`cvh`) | robot_1 | 2 | 0 / 0 / **2** | 2 | `repaired` 2 | swap + 2 substitutes | 2 | 2 |
| Smoke (scripted, all four named) | robot_2 | 1 | 1 / 1 / 1 | 0 | `m3_default` | — | 1 | — |
| Stored, take frames (C + H) | robot_2 | 22 | 0 / 22 / 22 | 0 | `repaired` 22 | 2 substitutes | 22 | — |
| Stored, take frames (C + H) | robot_1 | 13 | 0 / 0 / **13** | 13 | `repaired` 13 | swap + 2 substitutes | 13 | 13 |
| Stored, smoke frame | robot_2 | 2 | 0 / 2 / 2 | 0 | `repaired` 2 | 2 substitutes | 2 | — |
| Stored, smoke frame | robot_1 | 6 | 0 / 0 / **6** | 6 | `repaired` 6 | swap + 2 substitutes | 6 | 6 |
| **All yields** | robot_2 / robot_1 | 27 / 22 | **1 / 27 / 49** | 22 | — | — | 49 | 22 / 22 |
| Stored `reverse` (H, take 2) | — | 1 | 0 / 0 / 0 | 0 | `repaired` (as before) | 1 | — | unchanged (not a yield) |

No refusal occurred (0 of 49).

### 5.3 Field-by-Field Comparison With the Smoke's Executed Command

The fields compared are those of the hold report's comparison:

- robots, actions and linked positions;
- wait durations and expected resolution time;
- yielder, crossing order and passer;
- park coordinate, lateral pull-off and `hold_sec`;
- backup, `passer_clear_m` and `crossing_clear_m`;
- the yield parameter key set.

**Identical in every case:** robots, actions, linked positions, wait 367.7 s, resolution 459.6 s, yielder, order, passer, park 1.124, lateral 0.36 and `hold_sec` 137.9.

**The only differences:**

| Field | Take 1 | Take 2 | Take 3 | Take 4 | Take 5 | Smoke |
|---|---|---|---|---|---|---|
| `backup_distance_m` | 0.903 | 0.994 | 0.88 | 0.985 | 0.918 | 1.003 |
| `passer_clear_m` = `crossing_clear_m[0]` | 1.898 | 1.905 | 1.807 | 1.912 | 1.98 | 1.971 |
| `crossing_clear_m[1:]` (robot_3, robot_4) | 3.683, 4.256 | 3.683, 4.256 | 3.684, 4.256 | 3.683, 4.256 | 3.683, 4.256 | 3.683, 4.256 |

- The first two rows depend on each frame's standoff poses, and the smoke's decision was sized the same way. The third row agrees with the smoke within 1 mm (take 3 differs by 1 mm).
- Swapped answers carry two extra yield parameter keys: `yield_robot_grounded_from` and `yield_regrounded_reason`.
- The stored answers on the smoke frame match the smoke exactly (yielder robot_2: no difference; robot_1: only the two extra keys).

### 5.4 Later Triggers and Other Scenes

| Set | Decisions | Fix = hold | Recorded dispatch reproduced (recorded arm) |
|---|---|---|---|
| Later convoy decisions, takes 1–3 | 33 | 33 | 33 (`off`) |
| Later convoy decisions, takes 4–5 | 10 | 10 | 10 (`hold`) |
| Head-on `hoD_t01_a1` | 2 | 2 | 1 |
| Intersection `ibD_t01_a2` … `ibD_t05_a1` | 5 | 5 | 5 |
| Five-robot `m5D_t01_a1` | 8 | 8 | 6 |

- The 3 non-reproduced other-scene dispatches are the hold report's known replay limitation: stage-2 choices and task intents are not fed offline. The same pipeline runs in every arm.
- Takes 4–5's later yields (robot_2 with order [robot_3, robot_4, robot_2]) are still refused by the same-side check. The swap only acts on a yield that would otherwise ground.

### 5.5 Safety Review (Code Reading Plus Smoke GT)

**Exemptions are unchanged.** The swapped command equals hold-only grounding of robot_2's yield (22/22), so it is the smoke's command in structure. The smoke's m4 log shows the exempt pairs:

- during robot_2's backup and pull-off: robot_2 + robot_1, robot_3, robot_4 (`backing_up` exempts the yielder against its command members). robot_2 backs east, away from robot_3 and robot_4, which are 3 m or more to the west;
- after each `gate_admit`: robot_2 plus the admitted passer;
- robot_1 + robot_2 stays exempt until release;
- the passer–passer pairs are never exempt: robot_1–robot_3, robot_1–robot_4 and robot_3–robot_4 keep the full 0.45 m latch;
- `hard_contact_floor_m` 0.2 applies throughout.

No threshold, exemption or distance rule changed.

**Planned separations** (legacy template, this scene):

| Pair | Planned separation |
|---|---|
| Park point (1.124, −0.36) ↔ escort end (1.774, 0) | 0.74 m |
| Escort end ↔ robot_1's goal (2.45, −0.36) | 0.77 m |
| robot_4's goal (1.85, 0) ↔ robot_1 / robot_3 goals | 0.70 m |
| robot_4's goal ↔ parked robot_2 | 0.81 m |

**Smoke GT** (`cvL_e01_armC_a1`, after dispatch), against the 0.45 m latch:

| Pair | Exempt? | Minimum |
|---|---|---|
| robot_1–robot_3 | no | **0.495 m at 117.1 s** (robot_3 arriving beside the parked robot_1) |
| robot_1–robot_4 | no | 0.666 m |
| robot_3–robot_4 | no | 0.57 m |
| robot_1–robot_2 | yes | 0.374 m |
| robot_2–robot_3 | yes | 0.383 m |
| robot_2–robot_4 | yes | 0.384 m |

- No robot-robot contact.
- The smoke's 1060 `min_distance_violation` lines are all robot_1/robot_2: the standoff before dispatch.

### 5.6 What Offline Replay Cannot Show

- **Live resolution.** M4, Nav2 and timing are not exercised. The robot_2 sequence resolved once (smoke, n = 1, not owner-accepted).
- **Margin on the platoon's goal side.** The non-exempt robot_1–robot_3 approach cleared the latch by 0.045 m in the smoke. The scene header records 0.475 / 0.463 m (0.013–0.025 m clearance) in two earlier clean runs, after 3 of 4 latches with the previous goal table. A latch there is a plausible live failure that this fix does not touch.
- **Later triggers.** In takes 4–5, M5 suppressed triggers while the yield command was active, and the first later analysis came after `gate_release` (191 s). In a resolving run a later trigger is possible after the chain releases, for example while robot_2 returns. No recorded snapshot covers that state.
- **Bring-up.** 3 of 8 four-stack bring-ups failed historically (scene header); take 4 needed an `a2`.
- **Model answers that are not yields.** These are not changed: 1 of 45 stored answers is a `reverse`. A `convoy` answer aliases to robot_2's yield by the minority-bearing rule.

### 5.7 Realistic Per-Take Expectation

- The grounded first command is the smoke sequence in 49 of 49 yields, whichever yielder the model names.
- About 40 % of answers will be swapped: 22/49 offline, and 3 of the 5 live first decisions. The label then says the grounder corrected the yielder.
- What remains uncertain is live execution of a sequence seen to succeed once:
  - the thin goal-side margin;
  - Nav2 progress during the three escorts and robot_2's return;
  - bring-up;
  - the chance of a non-yield first answer (about 2 %).
- With n = 1, no resolution rate can be stated.

---

## 6. What Was the Model's and What Was the System's

- **The model:** the strategy (yield), the yielder (accepted when feasible) and the plan legs.
- **The grounder:**
  - holds robot_3 and robot_4 (hold key);
  - corrects a platoon-side yielder to the counter-flow robot (this key), recorded on the yield, in the artifact, in the M5 line and in the tag.
- A resolved take is never "VLM-driven". The labels are in section 7.2.

---

## 7. Part D: Rerun Kit `cvy` (Prepared, Not Launched)

### 7.1 Layout

- **Runtime delta.** `demo_campaign/runtime_delta_cvy/`:
  - `DELTA_ID fd85e2f9c8617ff306c36367bc68fee4`, files = 7, keys = 2;
  - the same 7 paths as `cvh`, at v7t HEAD bytes;
  - a two-line overlay fragment;
  - arm-check rows plus `c.grounding_yield_counterflow_swap True`.
- **Kit.** `demo_campaign/cvy/spec/` and the assembled `demo_campaign/cvy/kit/`:
  - kit md5 lists `194a09b7` (VM, 36 entries) and `7a745d5f` (all, 55 entries);
  - VM home `~/dmc_cvy`, labels `cvY_tNN_aK`, tag `demo_campaign_cvy`;
  - ledger key `cvy`;
  - `REPO_ROOT` v7t;
  - the restore returns the VM to its pin, as `cvh`.
- **Unchanged from `cvh`:** scene, seed 42, base overlay 7e3ab552, legacy grounding file 63f50f91, ER-2, 260 sim-s horizon, the 0.20 m floor and scoped exemption, and the inherited non-fatal simulator-only test step.

### 7.2 Checks

- **Condition gate (`scenario.json`):**
  - the exact two-key startup line;
  - `first_queued_hold` (as `cvh`);
  - new: `first_counterflow:robot_2:robot_1,robot_3,robot_4`. On the first artifact the dispatched yield must be robot_2's, with that order and those linked waits, and no refusal tag. Exactly one branch must hold:
    - `model_chose`: no swap fields, model yielder robot_2;
    - `swap`: from = the model's yielder, the `yield re-grounded: counterflow:` reason, the tag, and a plan swap edit when the model's plan yields its yielder;
    - `alias` (convoy).
  - robot_2 is the scene file's `oracle.correct_yielder`. The gate uses it only to check the apparatus.
- **Label (`mac_extra_classify_cvy.py`):**
  - "Resolved — grounder held the queued robots and corrected the yielder; model chose the strategy" when the swap fired;
  - "Resolved — grounder held the queued robots; model chose strategy and yielder" when the model chose robot_2;
  - "Unresolved failure" unless all four logged `arrived at base goal`;
  - later commands dispatched before the last arrival are counted for the caption;
  - never "VLM-driven".
- **Dry test (verified by running).** `MIN_MAC_FREE_KB=3000000 bash test_dry_dmc.sh /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7t` ends `TEST_DRY_DMC cvy OK`. It includes:
  - gate PASS on all 7 real two-key artifacts generated offline by v7t's own pipeline and writer (takes 1–5, named-all-four, plan-says-cross);
  - 10 single-defect cases, each failing exactly the matching check;
  - label cases;
  - restore (9 cases);
  - the ledger dry paths.

  `test_dry_dmc.sh` is forked from common only to read the valid-take cap (2) and to book (sub-cap − 4,800 s) in the happy path.
- **Ledger.** A read-only `admit cvy 4800 0.05` against the real ledger gives `ADMIT cap_sec=5400 spend_left=0.25 aborts_left=3 next_take=1 valid=0`. The ledger md5 was unchanged before and after.

### 7.3 Budget

**Ledger state** (`ledger_dmc.py status`, read-only):

- campaign: 25,667 s of 43,200 s and $2.8637 of $10;
- `cv`: 8,149 s of 12,600 s, 5 valid takes.

**Booking.** The rerun is booked under `cvy`: wall 5,400 s, $0.25, 2 valid takes. Adding the queued 7,200 s session gives 25,667 + 5,400 + 7,200 = 38,267 s ≤ 43,200 s, so both sessions fit, with 4,933 s left.

**5,400 s allows one take, not two.**

- Each invocation needs 4,800 s of headroom (prep 900 + take budget 3,000 + teardown 900).
- The chain admits a take only if it can end 900 s before the cap deadline. So a second take in the same invocation would have to start within 1,500 s of VM start, which is impossible after a roughly 1,200 s take.
- A second invocation is refused once the first has booked more than 600 s. The `cvh` invocations booked 1,602 s and 1,718 s.
- **Two valid takes need `wall_sec_cvy` of at least about 6,600 s; 7,200 s is suggested.** With the other session: 25,667 + 7,200 + 7,200 = 40,067 s ≤ 43,200 s.

**Launch** (by the scheduling session, VM free of `sft`):

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v7j/data/logs/vm_runs/demo_campaign/cvy/kit && bash run_dmc.sh --episodes 1
```

---

## 8. Verified and Inferred

| Claim | Status |
|---|---|
| Per-take commands, end poses, latch pairs, arrivals (section 1) | verified (GT re-read; m4/m5 via the campaign report) |
| The yielder's side must hold no counter-direction crosser | verified from code (`_ground_legacy` park side, escort direction) and GT (takes 2, 4, 5 versus the smoke) |
| The room gate never fires in the convoy | verified by running (49/49) and from code |
| The fix grounds every first-trigger yield into the smoke sequence | verified by running (49/49) |
| Nothing else changes (later, head-on, intersection, five-robot) | verified by running (58/58) |
| Exemptions and thresholds unchanged by the swap | verified (command equality 22/22; no M4 change) |
| Smoke separations and exempt pairs | verified (smoke GT and m4 log) |
| The swapped sequence resolves live | not shown (smoke n = 1) |
| The goal-side margin is the main live risk | inferred (smoke 0.495 m, scene header 0.463 / 0.475 m) |
| 5,400 s allows one take | verified from the driver's arithmetic and the dry test's ledger paths; not run on the VM |
| Full unit suite | pending (swap below 2 GB) |
