# Evidence Sheet EV-7bf1e2

- Censoring: t_end 569.203 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=18 max residual 0.286 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_5 | 11.203 | 569.203 | False | - | - |
| FU2 | conflict | robot_3, robot_4 | 63.803 | 569.203 | False | D1:robot_3:backup, D1:robot_4:escort, D1:robot_4:wait | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 28.6, 'until_rel': 569.2}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 11.9, 'until_rel': 569.2}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 58.8, 'to_rel': 569.2, 'duration_s': 510.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_2', 'from_rel': 58.8, 'to_rel': 569.2, 'duration_s': 510.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 58.8, 'to_rel': 569.2, 'duration_s': 510.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 10.805 | safety_stop_span | robot_1 | to 593.055 (137615 lines) |
| 10.818 | safety_stop_span | robot_5 | to 593.055 (137615 lines) |
| 13.0 | gt_submargin | robot_2|box:obstacle_2 | to 14.5 min gap 0.0193 m |
| 14.067 | m1_stale | robot_1 | STALE 5.57 s |
| 28.481 | safety_stop_span | robot_2 | to 593.055 (133446 lines) |
| 48.8 | analysis | D2 | positive strategy=temporary_wait involved=['robot_1', 'robot_2', 'robot_5'] yield=None |
| 48.8 | dispatched | D2 | robot_1:temporary_wait, robot_2:temporary_wait, robot_5:temporary_wait |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 11.367 | episode_gate_pass / episode_gate_pass | 21/237 | 21/237 | 21/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D2 | 48.8 | pass / pass | 35/237 | 35/237 | 35/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.04} |

### FU2

- Pairs: [['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.767 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 64.3, 'until_rel': 569.2}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_3', 'from_rel': 64.2, 'to_rel': 569.2, 'duration_s': 505.0, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 68.4, 'to_rel': 569.2, 'duration_s': 500.8, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.052 | safety_stop_span | robot_4 | to 18.827 (1596 lines) |
| 12.063 | safety_stop_span | robot_3 | to 18.827 (1596 lines) |
| 13.767 | analysis | D1 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_4 |
| 13.767 | dispatched | D1 | robot_3:yield, robot_4:temporary_wait |
| 18.766 | m4_leg_start | D1:robot_3:backup | backup commanded=1.355 |
| 18.829 | exempt_change | - | robot_3+robot_4 |
| 47.366 | m4_leg_start | D1:robot_4:escort | escort commanded=1.354 |
| 48.867 | m1_stale | robot_3 | STALE 1.87 s |
| 63.349 | m4_terminal | D1:robot_3:backup | COMPLETED  moved=1.414 tags=['completed'] deadline=False |
| 63.391 | m4_terminal | D1:robot_4:escort | COMPLETED escort complete: moved 1.356 m moved=1.321 tags=['completed'] deadline=False |
| 63.777 | safety_stop_span | robot_4 | to 593.055 (125051 lines) |
| 63.779 | safety_stop_span | robot_3 | to 593.055 (125051 lines) |
| 67.1 | analysis | D3 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_3 |
| 67.1 | withheld | D3 | robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 64.067 | episode_gate_pass / episode_gate_pass | 29/88 | 29/88 | 29/88 | True | {'robot': 'robot_3', 'heading_deg': 315, 'distance_m': 0.04} |
| D3 | 67.1 | pass / pass | 8/88 | 8/88 | 8/88 | True | {'robot': 'robot_3', 'heading_deg': 315, 'distance_m': 0.05} |

## Decisions

### D1 at 13.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_4, crossing_order ['robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 and Robot 3 are facing each other in a tight corridor, requiring one to yield and back up so the other can proceed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_4 has no retreat candidate surviving the sweep; robot_3 has an executable retreat; swapped roles robot_4 (yield) <-> robot_3 (cross)', 'robot_ids': ['robot_3', 'robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_4 has no retreat candidate surviving the sweep; robot_3 has an executable retreat, from robot_4
- Degradation tags: ['yield_robot=sweep_regrounded:robot_4->robot_3', 'retreat=default:no_choice', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.354']
- Actions: [('robot_3', 'yield', {'backup_distance_m': 1.355, 'crossing_order': ['robot_4'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.354, 'passer_robot_id': 'robot_4', 'reason': "Robot 3 and Robot 4 are facing each other head-on at extremely close proximity, blocking each other's paths.", 'retreat_choice': 'A'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=sweep_regrounded:robot_4->robot_3', 'yield_robot_grounded_from=robot_4'], 'G6_verbatim_contradicted': False}

### D2 at 48.8 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_2', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_5'}]
- Justification: Robots 1 and 2 should hold in place to allow robot_5 to maneuver and clear the crowded top-left corridor once the lower region clears.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_2', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 67.1 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_3, crossing_order ['robot_4', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 3 should yield (back up) to let Robot 4 clear the passage, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_3', 'robot_4']}, yield refusal yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_3,robot_4:46']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along x but sit 46 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_3:backup | backup | 1.355 | 13.767 | 18.766 | 63.349 | COMPLETED | 1.414 | 1.044 | 0.1833 (obstacle_2) | None (None) | completed | False |
| D1:robot_4:escort | escort | 1.354 | 13.767 | 47.366 | 63.391 | COMPLETED | 1.321 | 0.975 | 0.4399 (rack/SW_south) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 18.829, 'pairs': 'robot_3+robot_4'}, {'rel': 63.381, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_2|min_distance_violation: 1 spans
