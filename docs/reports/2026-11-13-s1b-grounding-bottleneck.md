# Why the 5-Robot S1b Scene Does Not Resolve: the M3 Grounding Bottleneck

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: refusal taxonomy, offline re-grounding parity, repeats, GT free space, counterfactuals and ranked remedies over 12 recorded S1b Arm A episodes.

---

## Scope

- **Question.** In the live S1b scene (`mapd_5_s1b`, 5 robots, task stream),
  Layer 2 analyses often, but robots rarely move. Where does the chain stop?
- **Data.** 12 recorded Arm A episodes, all `gemini-robotics-er-2-preview`:
  - the 7 Stage 1 shadow episodes of 2026-11-13 (`v4pcs_pos{21..27}_armA_a1`;
    `docs/reports/2026-11-13-v4-stage1-shadow-results.md`);
  - the 5 prereg-v3 tranche-1 Arm A episodes E27-E31
    (`docs/reports/2026-10-21-s1b-confirmatory-tranche1.md`).
- **Method.** Offline only: re-grounding of recorded decisions through the
  live M3 code at fdf333d, plus a GT free-space model that is independent of
  the grounder. No API call, no simulation, no VM.
- **Evidence grade: exploratory / decision-only.** Nothing was simulated
  forward. A counterfactual "groundable" means M3 would emit a motion command,
  not that the scene would resolve.
- **Safety margins were not relaxed.** No grounding constraint, safety radius,
  floor or margin was changed in code or config. The threshold sweep below
  relaxes constraints on in-memory copies, as analysis only.

---

## Summary

- **78 analyses → 13 motion commands.**
  - 47 withheld (42 `refusal_no_action`, 5 `empty_reroute`);
  - 26 dispatched: 13 carried a yield or reverse action, 13 were waits only;
  - 5 no decision (`congestion_detected=false`).
- **The refusals are M3's, and they are deterministic.** All 78 decisions
  re-ground offline to the live outcome (78/78 agree, 78/78 same actions).
- **One refusal class dominates.** `junction_clear` falls back to a
  declared-geometry yield gate that no pose on the S1b floor can pass. That
  accounts for 27/47 refusals, 24 of the 33 in the Stage 1 episodes.
- **The loop repeats itself.** The 47 withheld analyses are 15 distinct scenes
  (32 later analyses re-ask an already-refused scene). M2 is never told that
  a decision was withheld. The prompt then shows the withheld proposal's plan
  as the active plan.
- **There was room to move.** In 47/47 withheld scenes, at least one involved
  robot had >= 0.5 m of free straight-line reverse travel in GT (45/47 with a
  0.05 m margin).
- **Live reverses are not safer.** Reverse grounding skips the swept-path
  check that yields get, and 2 of the 4 dispatched reverses ended `failed`.

---

## Evidence

### Directories (gitignored)

| Path (under `vgu-vlm-swarm-v6d/`) | Files | Key file md5 |
|---|---|---|
| `data/logs/vm_runs/grounding_bottleneck_analysis/` (12 MB) | 28 (14 scripts, 13 outputs, `items_12ep.jsonl`) | `items_12ep.jsonl` 531cb090984921201765826eb5414315; `tables.txt` 3b839ae7fba52cc4f1cf8326111c8ef7; `parity.json` 9acd51e079c95c22ef5cae1345c907e8; `counterfactual.json` c54fa9b05e8f934a2876a5a95c0c9041; `gt_freespace.json` 4fd4a174e548dbe444c9ec6c3b8f82f9; `distinct_scenes.json` dfb492c3738c43fe6e492aa989c59454; `shadow_reground.json` 4a9ec5b2b1b943fdcc5f8be1f4623229; `threshold_sweep.json` 29c421335e240fea7cacfc3c718082d2; `episodes.json` b210e0b81ab9093af32571d984006467; `rows.json` 3efea91900c545564c8624efc7948d97 |
| `data/logs/vm_runs/v4_s1b_pc_shadow/runs/` | see the Stage 1 report | Stage 1 bundles (input) |
| `vgu-vlm-swarm-v3/data/logs/vm_runs/batch6/s1b_E{27..31}_seed*_armA_er2_confT1_a1` | not counted here | tranche-1 bundles (input, other checkout) |

### Re-run for this report

All scripts were re-run on a scratch copy of the directory, with
`PYTHONPATH` set to the v6d tree at fdf333d plus `ros2_ws/src/*`. Each
re-generated output is byte-identical to the stored one: `tables.txt`,
`parity.json`, `counterfactual.json`, `shadow_reground.json`,
`gt_freespace.json`, `threshold_sweep.json`, `jc_as_yield.json` and
`episodes.json`. `jc_gate_grid.py` (no stored output) printed `poses x sides
scanned 3430 passing 0`. `distinct_scenes.json` has no generating script in
the directory, so it was used as stored. `tables.py` writes next to itself,
so it must not be run in place under `data/`.

---

## Outcomes of the 78 Analyses

| Episodes | Analyses | Withheld | Dispatched with motion | Dispatched wait-only | No decision |
|---|---|---|---|---|---|
| Stage 1 pos21-27 | 50 | 33 | 9 | 5 | 3 |
| Tranche 1 E27-E31 | 28 | 14 | 4 | 8 | 2 |
| **Total** | **78** | **47** | **13** | **13** | **5** |

- Source: `episodes.json`. "Motion" means the command carried a `yield` or
  `reverse` action. Whether the robot then moved far enough was not scored
  here.
- The 13 motion commands: 9 yields and 4 reverses. Every yield ended
  `completed`. Two reverses ended `failed`: pos26 `98ff87f6` (robot_2 +
  robot_3) and pos27 `5d51cf8d` (robot_1 + robot_4).

---

## Refusal Taxonomy (47 Withheld)

| Class | Count | Stage 1 / Tranche 1 | Model strategy | Code path (fdf333d) |
|---|---|---|---|---|
| `junction_clear` static gate ("no feasible yielder") | 27 | 24 / 3 | `junction_clear` 27 | `reasoning/rag/command_grounder.py` `_ground_derived`, `junction_clear` branch 2340-2395: with no ranked recede candidate it re-grounds as a plain yield (`_as_yield_decision`, 4221) tagged `junction_clear=fallback:no_candidates`. The refusal is raised by `_apply_yield_feasibility` (465-566; text at 564), over `scene_geometry.yield_retreat_room_m` (649) vs `required_room_m` (607) |
| Sweep / axis ("no executable retreat") | 7 | 6 / 1 | yield | `command_grounder.py` `_sweep_regrounded_roles` (1751; refusal text 1830, prefix `_NO_EXECUTABLE_RETREAT` 1728) |
| `escort_hits_park` | 5 | 2 / 3 | yield | `reasoning/rag/escort_clearance.py` 53, `escort_hits_park_reason` 256; tagged in `command_grounder.py` 2533; withheld as `empty_reroute` |
| Ambiguous lane | 4 | 0 / 4 | yield | `reasoning/rag/grounding_view.py` `_ambiguous_refusal` 779-790 |
| No shared lane | 3 | 0 / 3 | yield | `grounding_view.py` `_parallel_refusal` 826-840 |
| No declared junction | 1 | 1 / 0 | yield | `grounding_view.py` `_crossing_refusal` 799-817 |

- **The static gate cannot pass on S1b.** `jc_gate_grid.py` scans 3430 floor
  poses × retreat sides with the declared geometry: rear-room band `aisle`,
  required room 0.77 m. Every pose measures 0.0 m (2303) or 0.15 m (1127),
  so 0 pass. The model's `junction_clear` therefore can never ground on this
  map. The refusal strings in `threshold_sweep.json` read, for example, "no
  feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat
  room < 0.77 m required)".
- **Today vs tranche 1.** The mix shifted. In the Stage 1 episodes the model
  chose `junction_clear` far more often (24 of 33 refusals). In tranche 1 the
  refusals were mostly yield geometry: ambiguous lane 4, no shared lane 3,
  escort 3. This is an observation over 7 vs 5 episodes on different seeds,
  not a tested difference.
- **By involved-set size:** 2 robots 16, 3 robots 18, 4 robots 11, 5 robots
  2. Every 4- and 5-robot refusal is the `junction_clear` gate.

---

## Why It Repeats

- **Parity.** `parity.py` re-grounds every recorded decision with the
  episode's exact M3 inputs: 78/78 agree with the live outcome and 78/78 give
  the same per-robot actions. A refusal is therefore a fixed function of
  (decision, scene). Asking the same scene again yields the same refusal
  unless the model changes its answer.
- **Repeats.** The 47 withheld analyses fall into 15 distinct scenes
  (`distinct_scenes.json`; per scene 1-10 analyses, e.g. 10 for pos25
  {robot_2, robot_3, robot_4}, 9 of them the `junction_clear` gate). So 32 of
  the 47 re-ask a scene that was already refused.
- **No refusal feedback.** At fdf333d the prompt does not say a decision was
  withheld. The failure context refers to the last executed command.
- **Withheld plans are shown as accepted.** `accept_plan` runs in the
  pipeline worker before M5 withholds the dispatch. Example: pos25 `4d36cfc0`
  proposed plan 2 and was withheld (`refusal_no_action`). The next analysis,
  `bf71c142` 3.8 sim-s later, shows "Active plan (plan_id=2): robot_4: wait
  (pending) ..." and "Hold this plan unless the scene has changed". Across the
  78 recorded prompts, 36 showed a withheld plan this way (counted on branch
  `feat/v4-refusal-feedback`, see Remedies).
- **Suppression does not stop it.** Re-analysis suppression arms after each
  withhold. It releases on pose or robot-set change, so a slowly drifting
  scene is analysed again.

---

## Was There Room to Move? (Grounder-Independent)

`gt_freespace.py` reads GT poses at each withheld analysis. It models each
robot as a 0.114 m disc and treats the overlay's static boxes as obstacles. It
measures free straight-line travel along −heading (M4's reverse), +heading
and the 4 axes, capped at 2.0 m. Travel stops at a box or when the robot comes
closer to another robot than min(0.45 m, the starting separation).

- **47/47:** at least one involved robot has >= 0.5 m of free reverse
  travel. With a 0.05 m box margin: 45/47.
- **0/47** withheld scenes had a GT contact at the analysis time.
- M1 heading error vs GT is a few degrees (for example −3.6 to +2.1 deg in
  pos25), so lane ambiguity is not an M1 artefact.

**Limits.** This is static, straight-line, one robot at a time. It ignores
other robots' motion and Nav2. It ignores the passer's subsequent path, and
the escort and park geometry. It shows that the refusals are not forced by
lack of space alone. It does not show that any manoeuvre would resolve the
scene. Nothing was simulated forward.

---

## Counterfactuals (Offline, M3 Only)

`counterfactual.py` re-grounds alternative single decisions with each
withheld analysis's exact inputs. "Groundable" means the command is not
refused, is not an empty reroute, and carries a yield, reverse or waypoint
reroute.

| Alternative | Withheld analyses with >= 1 groundable option (of 47) |
|---|---|
| Same strategy and involved set, another involved robot as yielder | 15 |
| `reverse` on the model's involved set | 17 |
| `yield` on an ordered pair inside the involved set | 21 |
| `yield` on any ordered pair at <= 1.5 m | 30 |
| `yield` on any ordered pair of the 5 robots | 39 |
| `reverse` on any unordered pair | 47 |
| `reverse` on a pair inside the involved set | 26 |

**Shadow options (Stage 1, 33 withheld analyses with a shadow block).**
- The per-group shadow offered a yield option in 26/33.
- The shadow offered an in-group (`group` or `pair` scope) yield in 22/33.
  In 4 it offered only `pair_partial`.
- All 101/101 shadow yield options re-ground to exactly the key the shadow
  recorded (`shadow_reground.py`).
- So per-group enumeration finds groundable yields where the scene-wide
  decision was refused. Whether M2 would pick them, and whether they
  resolve, is untested.

**`junction_clear` routed as a dynamic yield (`threshold_sweep.json`).**
3/27 ground with the model's yielder, and 15/27 with some involved robot as
yielder.

**Reverse caveat.** `reverse` is groundable almost everywhere because its
grounding checks only `_beyond_corridor_same_side` for the first pair.
Derived mode hands non-yield strategies to the legacy templates
(`_ground_derived` docstring, 2300-2303), and `_ground_legacy` (811) grounds a
reverse at 1097-1107; the derived default plan does the same at 4442-4451.
It does not run the swept-path, retreat-candidate or escort checks that yields
get. Live, 2 of the 4 dispatched reverses ended `failed`. Reverse is not a
safe default remedy.

**Constraint sweep (analysis only, nothing changed).** Relaxing one
constraint at a time on in-memory copies admits few of the 47:

| Relaxation | Admits (model's decision / any involved yielder) |
|---|---|
| `escort_park_clearance` off | 5 / 5 |
| `retreat_box_margin_m` 0.05 → 0.00 | 3 / 4 |
| `backup_clearance_m` 1.7 → 0.9 | 2 / 3 |
| `backup_clearance_m` 1.7 → 1.2 | 1 / 2 |
| `safety_radius_m` 0.45 → 0.40 or 0.35; axis snap 30 → 40 or 45 deg | 1 / 1 each |
| `backup_band_m` upper 2.0 → 2.5; aisle bands off | 0 / 0 |

Relaxing safety margins is the least effective lever and is not proposed.

---

## Ranked Remedies

Ranked by the share of the 47 withheld analyses each addresses and by risk:

1. **Do not offer `junction_clear` where it cannot ground** (27/47). Built,
   default off: `prompt_offer_groundable_strategies`, commit 4f0d77d on
   `feat/v4-refusal-feedback`. Offline, 0/78 recorded S1b prompts offer
   `junction_clear` with the key on. Keys-off prompts rebuild byte-identically.
   What the model answers instead is **untested**.
2. **Tell M2 about withheld decisions and stop showing withheld plans as
   accepted** (repeats: 32/47). Built, default off: `refusal_feedback`,
   commits a70bf20 and 2706720 (prompt-only plan marking), with bench variant
   4907600, overlay d3e2f5a and notes 9361107 / 66c323f. Offline: 38/78
   prompts would carry feedback (25 of the 47 withheld). The model's response
   is **untested**. The branch notes cost the paired replay at about $0.67
   (not run).
3. **Per-group decisions** (in-group yield available in 22/33 shadow-withheld
   analyses). This is the v4 per-cluster lever. Stage 1 shadow ran; Stage 2
   dispatch is not started.
4. **Grounder-side yielder search inside the involved set** (another yielder
   15/47; pair inside set 21/47). Not built. It changes M3 behaviour on
   pinned cells, so it needs an owner ruling.
5. **Reverse as fallback.** Not recommended without a swept-path check (2/4
   live reverses failed).
6. **Relaxing margins.** Not recommended (sweep above). **No safety margin
   was relaxed** in this work.

The full branch for remedies 1-2 is `feat/v4-refusal-feedback`, 4f0d77d..66c323f
(7 commits, unpushed). Its evidence is in that branch's
`docs/implementation_notes.md` 2026-11-13 entries.

---

## Limits

- 12 episodes, one scene family, one model. 7 of the 12 episodes reuse pilot
  seeds.
- Decision-only and offline. Neither the counterfactuals nor the GT free-space
  model simulate the result of a manoeuvre.
- `distinct_scenes.json` has no generating script in the directory. Its
  clustering rule (same core set and positions) was not re-derived. An
  earlier session summary said "30/47 repeats". The stored file gives 47 − 15
  = 32. No rule that yields 30 was found.
- The 13 "motion" commands are counted from command content and terminal
  status. Displacement achieved was not measured here.

---

## References

- Stage 1 results: `docs/reports/2026-11-13-v4-stage1-shadow-results.md`.
- Tranche 1: `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md`.
- Earlier refusal analyses: `docs/implementation_notes.md` 2026-10-09 and 2026-10-10 entries (refusal-as-no-action, resolvability fixes).
- Per-cluster design: `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md`.
