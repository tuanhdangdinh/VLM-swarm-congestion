# Evidence Sheet E14

- Censoring: t_end 572.07 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=18 max residual 0.237 s
- Outcome fields (frozen, copied): {"censor_reason": "horizon", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 572.1, "tasks_completed": 1, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_4, robot_5 | 12.27 | 572.07 | False | - | - |
| FU2 | conflict | robot_1, robot_2 | 50.67 | 572.07 | False | c5a5e687:robot_1:backup | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 20.57, 'until_rel': 572.07}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 33.27, 'until_rel': 572.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 83.87, 'to_rel': 572.07, 'duration_s': 488.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}, {'robot': 'robot_3', 'from_rel': 20.47, 'to_rel': 88.87, 'duration_s': 68.4, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 110.97, 'to_rel': 572.07, 'duration_s': 461.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}, {'robot': 'robot_4', 'from_rel': 105.87, 'to_rel': 572.07, 'duration_s': 466.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}, {'robot': 'robot_5', 'from_rel': 105.87, 'to_rel': 572.07, 'duration_s': 466.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_5|box:obstacle_1: [26.47, 28.77] 0.0032

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 10.77 | gt_submargin | robot_1|box:obstacle_2 | to 11.37 min gap 0.0463 m |
| 10.873 | safety_stop_span | robot_1 | to 18.18 (1792 lines) |
| 10.891 | safety_stop_span | robot_4 | to 18.18 (1792 lines) |
| 14.0 | analysis | c5a5e6876e804b9ea9367d0c1575535a | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 14.0 | dispatched | c5a5e6876e804b9ea9367d0c1575535a | robot_1:yield, robot_4:temporary_wait |
| 17.933 | m4_leg_start | c5a5e687:robot_1:backup | backup commanded=1.401 |
| 18.181 | exempt_change | - | robot_1+robot_4 |
| 20.247 | safety_stop_span | robot_3 | to 570.512 (139137 lines) |
| 20.248 | safety_stop_span | robot_4 | to 570.512 (139137 lines) |
| 26.47 | gt_contact | robot_5|box:obstacle_1 | to 28.77 min gap 0.0032 m |
| 33.554 | safety_stop_span | robot_5 | to 570.512 (135793 lines) |
| 52.018 | safety_stop_span | robot_1 | to 570.512 (131146 lines) |
| 52.3 | m1_stale | robot_1 | STALE 1.0 s |
| 70.695 | m4_terminal | c5a5e687:robot_1:backup | FAILED  moved=1.598 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 73.7 | analysis | 25db404d8b8f4c36bc82956b95e38314 | positive strategy=reverse involved=['robot_1', 'robot_2'] yield=None |
| 73.7 | dispatched | 25db404d8b8f4c36bc82956b95e38314 | robot_1:temporary_wait, robot_2:temporary_wait |
| 87.333 | analysis | 8e1e9b74a16a4046a5e5eb51a50c233e | positive strategy=reroute involved=['robot_3', 'robot_4', 'robot_5'] yield=None |
| 87.333 | dispatched | 8e1e9b74a16a4046a5e5eb51a50c233e | robot_3:reroute, robot_4:temporary_wait, robot_5:temporary_wait |
| 88.778 | m4_leg_start | 8e1e9b74:robot_3:reroute | reroute commanded=None |
| 110.892 | m4_terminal | 8e1e9b74:robot_3:reroute | FAILED  moved=None tags=None deadline=None |
| 111.833 | analysis | 1a77463db2a448c2afd0da0b9966a0d1 | positive strategy=junction_clear involved=['robot_3', 'robot_4', 'robot_5'] yield=None |
| 111.833 | withheld | 1a77463db2a448c2afd0da0b9966a0d1 | robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.367 | episode_gate_pass / episode_gate_pass | 120/237 | 120/237 | 120/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| c5a5e6876e804b9ea9367d0c1575535a | 14.0 | pass / pass | 118/237 | 118/237 | 118/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| 8e1e9b74a16a4046a5e5eb51a50c233e | 87.333 | pass / pass | 171/237 | 171/237 | 171/237 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.03} |
| 1a77463db2a448c2afd0da0b9966a0d1 | 111.833 | pass / pass | 171/237 | 171/237 | 171/237 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.03} |

### FU2

- Pairs: [['robot_1', 'robot_2']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 14.0 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 50.87, 'until_rel': 572.07}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 83.87, 'to_rel': 572.07, 'duration_s': 488.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}, {'robot': 'robot_2', 'from_rel': 83.87, 'to_rel': 572.07, 'duration_s': 488.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| -2.229 | safety_stop_span | robot_2 | to -0.169 (338 lines) |
| 10.77 | gt_submargin | robot_1|box:obstacle_2 | to 11.37 min gap 0.0463 m |
| 10.873 | safety_stop_span | robot_1 | to 18.18 (1792 lines) |
| 14.0 | analysis | c5a5e6876e804b9ea9367d0c1575535a | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 14.0 | dispatched | c5a5e6876e804b9ea9367d0c1575535a | robot_1:yield, robot_4:temporary_wait |
| 17.933 | m4_leg_start | c5a5e687:robot_1:backup | backup commanded=1.401 |
| 18.181 | exempt_change | - | robot_1+robot_4 |
| 52.017 | safety_stop_span | robot_2 | to 570.512 (131146 lines) |
| 52.018 | safety_stop_span | robot_1 | to 570.512 (131146 lines) |
| 52.3 | m1_stale | robot_1 | STALE 1.0 s |
| 70.695 | m4_terminal | c5a5e687:robot_1:backup | FAILED  moved=1.598 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 73.7 | analysis | 25db404d8b8f4c36bc82956b95e38314 | positive strategy=reverse involved=['robot_1', 'robot_2'] yield=None |
| 73.7 | dispatched | 25db404d8b8f4c36bc82956b95e38314 | robot_1:temporary_wait, robot_2:temporary_wait |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 50.867 | episode_gate_pass / episode_gate_pass | 10/88 | 10/88 | 10/88 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.03} |
| 25db404d8b8f4c36bc82956b95e38314 | 73.7 | pass / pass | 48/88 | 48/88 | 48/88 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.02} |

## Decisions

### c5a5e6876e804b9ea9367d0c1575535a at 14.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 and Robot 4 are head-on and stopped closer than 0.5 m. Robot 1 has room to yield and let Robot 4 continue its path.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.919']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.401, 'crossing_order': ['robot_4'], 'passer_escort_distance_m': 1.919, 'passer_robot_id': 'robot_4', 'reason': 'Robot 1 and Robot 4 are in a head-on standoff in a narrow corridor.', 'retreat_choice': 'C'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 25db404d8b8f4c36bc82956b95e38314 at 73.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_2'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since yielding by robot_1 did not resolve the congestion, reversing both robots will create the necessary clearance to allow robot_2 to proceed.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_1', 'robot_2'], 'involved': ['robot_1', 'robot_2']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: reverse infeasible: robot_1/robot_2 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_2: reverse infeasible: robot_1/robot_2 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 8e1e9b74a16a4046a5e5eb51a50c233e at 87.333 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reroute, involved ['robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): [{'action': 'reroute', 'robot_id': 'robot_3'}, {'action': 'reroute', 'robot_id': 'robot_4'}, {'action': 'reroute', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Since the pathway is blocked by a static object, the queued robots (3, 4, 5) need to be rerouted to find another clear path.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': False, 'C3_detail': {'involved_0': 'robot_3'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_3', 'reroute', {'waypoints': []}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### 1a77463db2a448c2afd0da0b9966a0d1 at 111.833 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_3', 'robot_4', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Using a junction clearance strategy will allow the crowded robots (specifically robot_4 and robot_5) to back up or yield, giving robot_3 the space to move out of the blocked area.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: yield infeasible: robot_5 has 0.00 m retreat room < 0.77 m required; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c5a5e687:robot_1:backup | backup | 1.401 | 14.0 | 17.933 | 70.695 | FAILED | 1.598 | 1.141 | 0.0871 (obstacle_2) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| c5a5e687:robot_4:escort | escort | 1.919 | 14.0 | None | None | None | None | None | None (None) | None (None) | escort_not_admitted (no gate_admit line) | False |
| 8e1e9b74:robot_3:reroute | reroute | None | 87.333 | 88.778 | 110.892 | FAILED | None | None | None (None) | None (None) | - | None |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 18.181, 'pairs': 'robot_1+robot_4'}, {'rel': 70.81, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_17|min_distance_violation: 1 spans; robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
