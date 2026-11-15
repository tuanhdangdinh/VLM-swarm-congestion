# Evidence Sheet E23

- Censoring: t_end 170.907 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=15 max residual 0.887 s
- Outcome fields (frozen, copied): {"censor_reason": "stop_flag", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 170.9, "tasks_completed": 6, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 15.307 | 170.907 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 5, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 37.01, 'until_rel': 170.91}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 16.01, 'until_rel': 170.91}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 26.41, 'to_rel': 170.91, 'duration_s': 144.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 36.71, 'to_rel': 170.91, 'duration_s': 134.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.992}, {'robot': 'robot_4', 'from_rel': 26.41, 'to_rel': 170.91, 'duration_s': 144.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 14.306 | safety_stop_span | robot_4 | to 191.775 (42058 lines) |
| 14.323 | safety_stop_span | robot_2 | to 191.775 (42058 lines) |
| 16.933 | analysis | a81e5925acdb48a7a861037ea0c6c61a | positive strategy=temporary_wait involved=['robot_2', 'robot_4'] yield=None |
| 16.933 | dispatched | a81e5925acdb48a7a861037ea0c6c61a | robot_2:temporary_wait, robot_4:temporary_wait |
| 31.51 | gt_submargin | robot_3|box:obstacle_1 | to 32.81 min gap 0.0215 m |
| 37.765 | safety_stop_span | robot_3 | to 191.775 (36485 lines) |
| 70.0 | analysis | 21d78102cc704db288683f1caf2db334 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 70.0 | withheld | 21d78102cc704db288683f1caf2db334 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 110.633 | analysis | 0c4ad5c8eb084af49f919c930f4d4ca9 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 110.633 | withheld | 0c4ad5c8eb084af49f919c930f4d4ca9 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 114.3 | analysis | 5f9603fbccb543799ff0fa942a7d1cbc | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 114.3 | withheld | 5f9603fbccb543799ff0fa942a7d1cbc | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 168.4 | analysis | 40636339c4ef49d39dbbe96d12d95ab9 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 168.4 | withheld | 40636339c4ef49d39dbbe96d12d95ab9 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 15.467 | episode_gate_pass / episode_gate_pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| a81e5925acdb48a7a861037ea0c6c61a | 16.933 | pass / pass | 12/237 | 12/237 | 12/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| 21d78102cc704db288683f1caf2db334 | 70.0 | pass / pass | 83/237 | 83/237 | 83/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |
| 0c4ad5c8eb084af49f919c930f4d4ca9 | 110.633 | pass / pass | 81/237 | 81/237 | 81/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |
| 5f9603fbccb543799ff0fa942a7d1cbc | 114.3 | pass / pass | 80/237 | 80/237 | 80/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |
| 40636339c4ef49d39dbbe96d12d95ab9 | 168.4 | pass / pass | 60/237 | 60/237 | 60/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |

## Decisions

### a81e5925acdb48a7a861037ea0c6c61a at 16.933 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_2', 'robot_4'], yield_robot None, crossing_order None, type bottleneck
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 is waiting for Robot 2 to resume moving before it can proceed along its path.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 9803bd34c5e249ad9e2d097a82c4ef37 at 29.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_5, crossing_order ['robot_1', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having robot_5 yield allows robot_1 to continue and clears the deadlock at the bottom corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_5', 'yield', {'backup_distance_m': 1.325, 'crossing_order': ['robot_1'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 2.35, 'passer_robot_id': 'robot_1', 'reason': 'robot_1 and robot_5 are in a head-on deadlock, facing each other in close proximity.', 'retreat_choice': 'C'}), ('robot_1', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 21d78102cc704db288683f1caf2db334 at 70.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 and robot 2/3 must be resolved by having robot_4 back out or yield to clear the intersection space, allowing robot_2 and robot_3 to resolve their head-on conflict by yielding or reversing.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: yield infeasible: robot_3/robot_2 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 0c4ad5c8eb084af49f919c930f4d4ca9 at 110.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 must reverse to provide maneuvering room for Robots 2 and 3 to clear the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### 5f9603fbccb543799ff0fa942a7d1cbc at 114.3 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): None
- Justification: Robot 4 needs to reverse to clear the narrow passage, allowing robots 2 and 3 to sequentially pass each other.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 40636339c4ef49d39dbbe96d12d95ab9 at 168.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_2'}]
- Justification: Robot 4 and robot_3 should reverse to create space, allowing robot 2 to yield or clear the area, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: yield infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9803bd34:robot_5:backup | backup | 1.325 | 29.6 | 33.7 | 92.176 | COMPLETED | 1.512 | 1.141 | 0.092 (obstacle_2) | None (None) | completed | False |
| 9803bd34:robot_1:escort | escort | 2.35 | 29.6 | 65.967 | 92.218 | COMPLETED | 2.295 | 0.977 | 0.2476 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_5": [{"from_rel": 70.333, "to_rel": 92.967, "duration_s": 22.63, "ge_10s": true}, {"from_rel": 123.833, "to_rel": 124.867, "duration_s": 1.03, "ge_10s": false}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 34.519, 'pairs': 'robot_1+robot_5'}, {'rel': 92.22, 'pairs': '-'}]
- Safety-stop spans: robot_4|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans
