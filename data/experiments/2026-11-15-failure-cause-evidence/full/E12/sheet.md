# Evidence Sheet E12

- Censoring: t_end 570.14 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=6 max residual 0.018 s
- Outcome fields (frozen, copied): {"censor_reason": "horizon", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 570.1, "tasks_completed": 3, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_5 | 12.74 | 570.14 | False | - | - |
| FU2 | conflict | robot_2, robot_4 | 40.44 | 570.14 | False | d374802a:robot_2:reverse, d374802a:robot_4:reverse | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 12.94, 'until_rel': 570.14}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 89.64, 'until_rel': 570.14}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 12.64, 'to_rel': 570.14, 'duration_s': 557.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.989}, {'robot': 'robot_3', 'from_rel': 12.64, 'to_rel': 570.14, 'duration_s': 557.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.989}, {'robot': 'robot_5', 'from_rel': 89.54, 'to_rel': 570.14, 'duration_s': 480.6, 'to_censor': True, 'safety_stop_cover_fraction': 0.982}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.611 | safety_stop_span | robot_1 | to 563.771 (141313 lines) |
| 12.618 | safety_stop_span | robot_3 | to 563.772 (141313 lines) |
| 20.74 | gt_submargin | robot_5|box:obstacle_2 | to 21.54 min gap 0.0402 m |
| 32.6 | m1_stale | robot_5 | STALE 1.63 s |
| 35.4 | analysis | 3d294b6d96174da893c318656d80dbe1 | positive strategy=junction_clear involved=['robot_1', 'robot_3'] yield=robot_3 |
| 35.4 | withheld | 3d294b6d96174da893c318656d80dbe1 | robot_3:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |
| 91.6 | analysis | b035a168a1ca44478af55b66d1abc1d1 | positive strategy=junction_clear involved=['robot_1', 'robot_3', 'robot_5', 'robot_2', 'robot_4'] yield=None |
| 91.6 | withheld | b035a168a1ca44478af55b66d1abc1d1 | robot_1:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait, robot_2:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 91.961 | safety_stop_span | robot_5 | to 563.772 (121069 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.833 | episode_gate_pass / episode_gate_pass | 7/237 | 7/237 | 7/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| 3d294b6d96174da893c318656d80dbe1 | 35.4 | pass / pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| b035a168a1ca44478af55b66d1abc1d1 | 91.6 | pass / pass | 3/237 | 3/237 | 3/237 | True | {'robot': 'robot_3', 'heading_deg': 135, 'distance_m': 0.02} |

### FU2

- Pairs: [['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.233 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 40.94, 'until_rel': 570.14}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 40.74, 'to_rel': 570.14, 'duration_s': 529.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.987}, {'robot': 'robot_4', 'from_rel': 40.84, 'to_rel': 570.14, 'duration_s': 529.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.987}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:rack/NW_north: [27.24, 33.94] -0.0015

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 10.88 | safety_stop_span | robot_2 | to 14.724 (973 lines) |
| 10.89 | safety_stop_span | robot_4 | to 14.724 (973 lines) |
| 13.233 | analysis | d374802aa0394e63a4d436010f48f04e | positive strategy=reverse involved=['robot_2', 'robot_4'] yield=None |
| 13.233 | dispatched | d374802aa0394e63a4d436010f48f04e | robot_2:reverse, robot_4:reverse |
| 14.667 | m4_leg_start | d374802a:robot_2:reverse | reverse commanded=1.3 |
| 14.7 | m4_leg_start | d374802a:robot_4:reverse | reverse commanded=1.3 |
| 14.728 | exempt_change | - | robot_2+robot_4 |
| 27.24 | gt_contact | robot_2|box:rack/NW_north | to 33.94 min gap -0.0015 m |
| 29.063 | m4_terminal | d374802a:robot_4:reverse | COMPLETED  moved=1.291 tags=['completed'] deadline=False |
| 32.294 | m4_terminal | d374802a:robot_2:reverse | COMPLETED  moved=1.301 tags=['completed'] deadline=False |
| 39.467 | analysis | 551d3132d3984dcd837ef0247c301a6e | positive strategy=yield involved=['robot_2', 'robot_4'] yield=robot_4 |
| 39.467 | withheld | 551d3132d3984dcd837ef0247c301a6e | robot_4:temporary_wait, robot_2:temporary_wait withheld=refusal_no_action |
| 41.462 | safety_stop_span | robot_4 | to 563.771 (133956 lines) |
| 41.465 | safety_stop_span | robot_2 | to 563.771 (133956 lines) |
| 42.333 | m1_stale | robot_2 | STALE 140.77 s |
| 47.233 | m1_stale | robot_4 | STALE 0.77 s |
| 91.6 | analysis | b035a168a1ca44478af55b66d1abc1d1 | positive strategy=junction_clear involved=['robot_1', 'robot_3', 'robot_5', 'robot_2', 'robot_4'] yield=None |
| 91.6 | withheld | b035a168a1ca44478af55b66d1abc1d1 | robot_1:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait, robot_2:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 185.7 | m1_stale | robot_2 | STALE 0.8 s |
| 189.8 | m1_stale | robot_2 | STALE 63.7 s |
| 254.733 | m1_stale | robot_2 | STALE 9.77 s |
| 266.133 | m1_stale | robot_2 | STALE 0.23 s |
| 267.567 | m1_stale | robot_2 | STALE 9.0 s |
| 278.7 | m1_stale | robot_2 | STALE 207.9 s |
| 351.333 | m1_stale | robot_4 | STALE 1.77 s |
| 488.1 | m1_stale | robot_2 | STALE 53.77 s |
| 543.167 | m1_stale | robot_2 | STALE 26.77 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 40.767 | episode_gate_pass / episode_gate_pass | 2/88 | 2/88 | 2/88 | True | {'robot': 'robot_2', 'heading_deg': 90, 'distance_m': 0.02} |

## Decisions

### d374802aa0394e63a4d436010f48f04e at 13.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since both robots are facing each other in a tight corridor and are stopped, they must both reverse to clear the path before they can resume their tasks safely.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_4'], 'involved': ['robot_2', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x']
- Actions: [('robot_2', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 3d294b6d96174da893c318656d80dbe1 at 35.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_3'], yield_robot robot_3, crossing_order ['robot_1', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robots 1 and 3 must execute a coordinated sequence where robot_3 yields or backs up to allow robot_1 to proceed through.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_3', 'robot_1']}, yield refusal yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m retreat room < 0.77 m required)'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 551d3132d3984dcd837ef0247c301a6e at 39.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_4'], yield_robot robot_4, crossing_order ['robot_2', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 can yield and hold its position or step back to allow Robot 2 to proceed through the corridor first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_4', 'robot_2']}, yield refusal yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_4,robot_2:51']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_4 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 604733ebb02b4a13be799f3fc563eb31 at 43.9 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The existing plan continues to safely resolve the proximity of robot_2/robot_4 and robot_1/robot_3 without any deadlock occurring.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 26964ab0e5964387818d30716b7c3062 at 81.3 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: No new congestion patterns or state changes have been detected since the active plan was accepted.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 8e8d9a2fe0894e14b59e7d0569730ce4 at 85.233 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: No new congestion patterns or plan failures are detected; the existing plan remains valid.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### b035a168a1ca44478af55b66d1abc1d1 at 91.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_3', 'robot_5', 'robot_2', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_3', 'robot_1', 'robot_4', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_5'}]
- Justification: Clearing the junction requires sequencing the robots so they don't block each other's pathing, starting with those who can clear the corridor first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_3', 'robot_5', 'robot_2', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_5 0.00 m, robot_2 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d374802a:robot_2:reverse | reverse | 1.3 | 13.233 | 14.667 | 32.294 | COMPLETED | 1.301 | 1.001 | -0.0015 (rack/NW_north) | None (None) | completed | False |
| d374802a:robot_4:reverse | reverse | 1.3 | 13.233 | 14.7 | 29.063 | COMPLETED | 1.291 | 0.993 | 0.2108 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_2": [{"from_rel": 42.333, "to_rel": 183.1, "duration_s": 140.77, "ge_10s": true}, {"from_rel": 185.7, "to_rel": 186.5, "duration_s": 0.8, "ge_10s": false}, {"from_rel": 189.8, "to_rel": 253.5, "duration_s": 63.7, "ge_10s": true}, {"from_rel": 254.733, "to_rel": 264.5, "duration_s": 9.77, "ge_10s": false}, {"from_rel": 266.133, "to_rel": 266.367, "duration_s": 0.23, "ge_10s": false}, {"from_rel": 267.567, "to_rel": 276.567, "duration_s": 9.0, "ge_10s": false}, {"from_rel": 278.7, "to_rel": 486.6, "duration_s": 207.9, "ge_10s": true}, {"from_rel": 488.1, "to_rel": 541.867, "duration_s": 53.77, "ge_10s": true}, {"from_rel": 543.167, "to_rel": 569.933, "duration_s": 26.77, "ge_10s": true}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 14.728, 'pairs': 'robot_2+robot_4'}, {'rel': 32.297, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_1|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
