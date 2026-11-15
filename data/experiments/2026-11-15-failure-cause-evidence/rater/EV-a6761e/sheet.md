# Evidence Sheet EV-a6761e

- Censoring: t_end 570.473 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=15 max residual 0.047 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3 | 12.073 | 570.473 | False | D1:robot_3:wait | - |
| FU2 | conflict | robot_1, robot_4, robot_5 | 69.773 | 570.473 | False | D1:robot_1:backup, D1:robot_4:escort, D1:robot_4:wait, D1:robot_5:wait | - |

### FU1

- Pairs: [['robot_2', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 12.0 rel-s
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 12.57, 'until_rel': 570.47}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 12.37, 'to_rel': 570.47, 'duration_s': 558.1, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 68.07, 'to_rel': 570.47, 'duration_s': 502.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.0 | analysis | D1 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 12.0 | dispatched | D1 | robot_1:yield, robot_4:temporary_wait, robot_5:temporary_wait, robot_3:temporary_wait |
| 12.052 | safety_stop_span | robot_3 | to 624.659 (140728 lines) |
| 12.064 | safety_stop_span | robot_2 | to 624.659 (140728 lines) |
| 71.1 | analysis | D2 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 71.1 | withheld | D2 | robot_2:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 75.533 | analysis | D3 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 75.533 | withheld | D3 | robot_2:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 101.467 | analysis | D4 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 101.467 | withheld | D4 | robot_2:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.4 | U:T1_fidelity / episode_gate_pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.13} |
| D2 | 71.1 | pass / pass | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.15} |
| D3 | 75.533 | pass / pass | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.15} |
| D4 | 101.467 | pass / pass | 6/88 | 6/88 | 6/88 | True | {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.15} |

### FU2

- Pairs: [['robot_1', 'robot_4'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 12.0 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 70.07, 'until_rel': 570.47}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 99.87, 'until_rel': 570.47}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 70.07, 'to_rel': 570.47, 'duration_s': 500.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_4', 'from_rel': 69.87, 'to_rel': 570.47, 'duration_s': 500.6, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_5', 'from_rel': 99.77, 'to_rel': 570.47, 'duration_s': 470.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.99}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.0 | analysis | D1 | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 12.0 | dispatched | D1 | robot_1:yield, robot_4:temporary_wait, robot_5:temporary_wait, robot_3:temporary_wait |
| 15.3 | m4_leg_start | D1:robot_1:backup | backup commanded=1.425 |
| 15.475 | exempt_change | - | robot_1+robot_4 |
| 46.57 | gt_submargin | robot_1|box:rack/SW_west | to 47.47 min gap 0.0462 m |
| 49.133 | m4_leg_start | D1:robot_4:escort | escort commanded=1.692 |
| 50.233 | m1_stale | robot_1 | STALE 0.4 s |
| 67.999 | m4_terminal | D1:robot_1:backup | COMPLETED  moved=1.628 tags=['completed'] deadline=False |
| 68.034 | m4_terminal | D1:robot_4:escort | COMPLETED escort complete: moved 1.693 m moved=1.687 tags=['completed'] deadline=False |
| 70.335 | safety_stop_span | robot_1 | to 624.659 (127144 lines) |
| 70.336 | safety_stop_span | robot_4 | to 624.659 (127144 lines) |
| 89.57 | gt_submargin | robot_5|box:obstacle_1 | to 91.17 min gap 0.0159 m |
| 104.515 | safety_stop_span | robot_5 | to 624.659 (119394 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 69.867 | U:T1_fidelity / episode_gate_pass | 10/237 | 10/237 | 10/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### D1 at 12.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order ['robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: robot_1 should yield and back up to allow robot_4 to pass, resolving the head-on deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_1->robot_4', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.692', 'grounding=retreat_shield:robot_5', 'grounding=retreat_shield:robot_3']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.425, 'crossing_order': ['robot_4'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.692, 'passer_robot_id': 'robot_4', 'reason': 'robot_1 and robot_4 are facing each other in a narrow aisle at a distance of 0.32 m.', 'retreat_choice': 'B'}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True}), ('robot_3', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4'], 'G6_verbatim_contradicted': True}

### D2 at 71.1 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_3 yield will allow robot_2 to continue to its goal, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3']}, yield refusal yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_3:40', 'grounding=heading_regrounded:robot_3->robot_2', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_3->robot_2'], 'G6_verbatim_contradicted': False}

### D3 at 75.533 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 3 can yield and step aside to allow Robot 2 to pass safely, thereby resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3']}, yield refusal yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_3:40', 'grounding=heading_regrounded:robot_3->robot_2', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_3->robot_2'], 'G6_verbatim_contradicted': False}

### D4 at 101.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_3 yield or reverse allows robot_2 to proceed to its nearby goal, resolving the head-on conflict.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3']}, yield refusal yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_3:40', 'grounding=heading_regrounded:robot_3->robot_2', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_2 has no retreat candidate surviving the sweep; robot_3 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_3->robot_2'], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_1:backup | backup | 1.425 | 12.0 | 15.3 | 67.999 | COMPLETED | 1.628 | 1.142 | 0.0462 (rack/SW_west) | None (None) | completed | False |
| D1:robot_4:escort | escort | 1.692 | 12.0 | 49.133 | 68.034 | COMPLETED | 1.687 | 0.997 | 0.1691 (rack/SW_west) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 15.475, 'pairs': 'robot_1+robot_4'}, {'rel': 68.116, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
