# Evidence Sheet E16

- Censoring: t_end 570.073 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=23 max residual 2.452 s
- Outcome fields (frozen, copied): {"censor_reason": "horizon", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 570.1, "tasks_completed": 3, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 22.073 | 570.073 | False | ede6d209:robot_3:reverse, ede6d209:robot_4:reverse | - |
| FU2 | conflict | robot_1, robot_5 | 135.073 | 570.073 | False | eafbb338:robot_1:backup | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.2 rel-s
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 22.37, 'until_rel': 570.07}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 122.17, 'until_rel': 570.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 71.07, 'to_rel': 570.07, 'duration_s': 499.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.976}, {'robot': 'robot_3', 'from_rel': 71.07, 'to_rel': 570.07, 'duration_s': 499.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.976}, {'robot': 'robot_4', 'from_rel': 121.97, 'to_rel': 570.07, 'duration_s': 448.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.973}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| -0.38 | safety_stop_span | robot_2 | to 0.894 (263 lines) |
| 11.835 | safety_stop_span | robot_3 | to 14.635 (712 lines) |
| 11.844 | safety_stop_span | robot_4 | to 14.636 (712 lines) |
| 13.2 | analysis | ede6d209821e49b6998cd4feb7ecc7a1 | positive strategy=reverse involved=['robot_3', 'robot_4'] yield=None |
| 13.2 | dispatched | ede6d209821e49b6998cd4feb7ecc7a1 | robot_3:reverse, robot_4:reverse |
| 14.639 | exempt_change | - | robot_3+robot_4 |
| 14.766 | m4_leg_start | ede6d209:robot_3:reverse | reverse commanded=1.3 |
| 14.766 | m4_leg_start | ede6d209:robot_4:reverse | reverse commanded=1.3 |
| 18.249 | safety_stop_span | robot_4 | to 83.188 (16674 lines) |
| 21.794 | safety_stop_span | robot_2 | to 557.855 (138419 lines) |
| 21.795 | safety_stop_span | robot_3 | to 557.855 (138419 lines) |
| 48.913 | m4_terminal | ede6d209:robot_3:reverse | FAILED  moved=0.66 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 48.948 | m4_terminal | ede6d209:robot_4:reverse | FAILED  moved=0.345 tags=['not_executed(<50%)', 'stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 52.967 | analysis | df2ed72f21c04b9492900561f68248f5 | positive strategy=reroute involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 52.967 | dispatched | df2ed72f21c04b9492900561f68248f5 | robot_1:reroute, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 76.733 | analysis | eafbb338892b4ca5aa0f181f4a987711 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 76.733 | dispatched | eafbb338892b4ca5aa0f181f4a987711 | robot_1:yield, robot_4:temporary_wait |
| 83.19 | exempt_change | - | robot_1+robot_4 |
| 120.17 | gt_submargin | robot_4|box:obstacle_1 | to 121.27 min gap 0.0246 m |
| 121.267 | safety_stop_span | robot_4 | to 557.855 (112784 lines) |
| 163.4 | analysis | ef117f2f7faa4067b0377d2957796fdc | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 163.4 | withheld | ef117f2f7faa4067b0377d2957796fdc | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 22.133 | episode_gate_pass / episode_gate_pass | 14/237 | 14/237 | 14/237 | True | {'robot': 'robot_2', 'heading_deg': 225, 'distance_m': 0.03} |
| df2ed72f21c04b9492900561f68248f5 | 52.967 | pass / pass | 16/237 | 16/237 | 11/237 | True | {'robot': 'robot_2', 'heading_deg': 270, 'distance_m': 0.04} |
| ef117f2f7faa4067b0377d2957796fdc | 163.4 | pass / pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_3', 'heading_deg': 90, 'distance_m': 0.04} |

### FU2

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 76.733 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 135.27, 'until_rel': 570.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 157.47, 'to_rel': 570.07, 'duration_s': 412.6, 'to_censor': True, 'safety_stop_cover_fraction': 0.97}, {'robot': 'robot_5', 'from_rel': 134.97, 'to_rel': 570.07, 'duration_s': 435.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.972}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 75.162 | m4_terminal | df2ed72f:robot_1:reroute | FAILED  moved=None tags=None deadline=None |
| 76.733 | analysis | eafbb338892b4ca5aa0f181f4a987711 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 76.733 | dispatched | eafbb338892b4ca5aa0f181f4a987711 | robot_1:yield, robot_4:temporary_wait |
| 81.7 | m4_leg_start | eafbb338:robot_1:backup | backup commanded=1.392 |
| 83.19 | exempt_change | - | robot_1+robot_4 |
| 85.567 | m1_stale | robot_5 | STALE 0.67 s |
| 133.654 | safety_stop_span | robot_1 | to 557.855 (109574 lines) |
| 133.664 | safety_stop_span | robot_5 | to 557.855 (109574 lines) |
| 157.45 | m4_terminal | eafbb338:robot_1:backup | COMPLETED  moved=1.578 tags=['completed'] deadline=False |
| 163.4 | analysis | ef117f2f7faa4067b0377d2957796fdc | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 163.4 | withheld | ef117f2f7faa4067b0377d2957796fdc | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 135.3 | episode_gate_pass / episode_gate_pass | 8/88 | 8/88 | 8/88 | True | {'robot': 'robot_1', 'heading_deg': 180, 'distance_m': 0.04} |

## Decisions

### ede6d209821e49b6998cd4feb7ecc7a1 at 13.2 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Both robots must reverse to clear the narrow passage and allow for redirection or sequential passing.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_3', 'robot_4'], 'involved': ['robot_3', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x']
- Actions: [('robot_3', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### df2ed72f21c04b9492900561f68248f5 at 52.967 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reroute, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reroute', 'robot_id': 'robot_3'}, {'action': 'reroute', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since reversing has failed, we must reroute robot_4 and robot_3 to use alternative paths to clear the area.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': True, 'C3_detail': {'involved_0': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'reroute', {'waypoints': []}), ('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### eafbb338892b4ca5aa0f181f4a987711 at 76.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 is stale and in close proximity to Robot 4, preventing progress. Forcing Robot 1 to yield/back up will clear the bottleneck.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=dynamic_arms:lane:x', 'grounding=escort_off:robot_4:goal_behind']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.392, 'crossing_order': ['robot_4'], 'passer_robot_id': 'robot_4', 'reason': "Robot 1 is stale and blocked by Robot 4's position in the narrow passage.", 'retreat_choice': 'C'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### ef117f2f7faa4067b0377d2957796fdc at 163.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2', 'robot_1', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}]
- Justification: A multi-robot junction clear is required to systematically back robots away and let them cross in order.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ede6d209:robot_3:reverse | reverse | 1.3 | 13.2 | 14.766 | 48.913 | FAILED | 0.66 | 0.507 | 0.2419 (obstacle_1) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| ede6d209:robot_4:reverse | reverse | 1.3 | 13.2 | 14.766 | 48.948 | FAILED | 0.345 | 0.266 | 0.1984 (obstacle_1) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | True |
| df2ed72f:robot_1:reroute | reroute | None | 52.967 | 54.037 | 75.162 | FAILED | None | None | None (None) | None (None) | - | None |
| eafbb338:robot_1:backup | backup | 1.392 | 76.733 | 81.7 | 157.45 | COMPLETED | 1.578 | 1.134 | 0.2098 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_1": [{"from_rel": 20.733, "to_rel": 82.067, "duration_s": 61.33, "ge_10s": true}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 14.639, 'pairs': 'robot_3+robot_4'}, {'rel': 48.966, 'pairs': '-'}, {'rel': 83.19, 'pairs': 'robot_1+robot_4'}, {'rel': 157.482, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_17|min_distance_violation: 1 spans; robot_3|min_distance_violation: 2 spans; robot_4|min_distance_violation: 3 spans; robot_1|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans
