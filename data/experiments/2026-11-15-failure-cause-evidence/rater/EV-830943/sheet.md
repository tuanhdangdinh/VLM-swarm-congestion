# Evidence Sheet EV-830943

- Censoring: t_end 568.803 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=18 max residual 1.458 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 22.803 | 568.803 | False | D1:robot_1:backup, D1:robot_5:escort, D1:robot_5:wait, D1:robot_3:wait, D1:robot_4:wait | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_5'], ['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 15.433 rel-s
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 84.0, 'until_rel': 568.8}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 102.3, 'until_rel': 568.8}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 23.3, 'until_rel': 568.8}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 81.3, 'until_rel': 568.8}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 83.8, 'to_rel': 568.8, 'duration_s': 485.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.997}, {'robot': 'robot_2', 'from_rel': 106.2, 'to_rel': 568.8, 'duration_s': 462.6, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 99.4, 'to_rel': 568.8, 'duration_s': 469.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 81.2, 'to_rel': 568.8, 'duration_s': 487.6, 'to_censor': True, 'safety_stop_cover_fraction': 0.998}, {'robot': 'robot_5', 'from_rel': 102.1, 'to_rel': 568.8, 'duration_s': 466.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.989}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.6 | gt_submargin | robot_1|box:obstacle_2 | to 12.3 min gap 0.045 m |
| 13.249 | safety_stop_span | robot_1 | to 19.121 (1323 lines) |
| 13.258 | safety_stop_span | robot_5 | to 19.122 (1323 lines) |
| 15.433 | analysis | D1 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_1 |
| 15.433 | dispatched | D1 | robot_1:yield, robot_5:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 18.866 | m4_leg_start | D1:robot_1:backup | backup commanded=1.388 |
| 19.125 | exempt_change | - | robot_1+robot_5 |
| 22.388 | safety_stop_span | robot_3 | to 613.759 (134590 lines) |
| 22.408 | safety_stop_span | robot_2 | to 613.76 (134590 lines) |
| 48.4 | m4_leg_start | D1:robot_5:escort | escort commanded=2.038 |
| 70.209 | m4_terminal | D1:robot_1:backup | COMPLETED  moved=1.452 tags=['completed'] deadline=False |
| 70.255 | m4_terminal | D1:robot_5:escort | COMPLETED escort complete: moved 2.043 m moved=2.037 tags=['completed'] deadline=False |
| 72.7 | gt_submargin | robot_5|box:rack/SE_east | to 74.3 min gap 0.0281 m |
| 74.667 | analysis | D2 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 74.667 | withheld | D2 | robot_3:reroute, robot_2:temporary_wait withheld=empty_reroute |
| 79.267 | analysis | D3 | positive strategy=reroute involved=['robot_2', 'robot_3'] yield=None |
| 79.267 | dispatched | D3 | robot_2:reroute, robot_3:temporary_wait |
| 81.259 | m4_leg_start | D3:robot_2:reroute | reroute commanded=None |
| 81.992 | safety_stop_span | robot_4 | to 613.76 (120935 lines) |
| 85.334 | safety_stop_span | robot_1 | to 613.76 (120187 lines) |
| 104.633 | analysis | D4 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_2 |
| 104.633 | withheld | D4 | robot_3:reroute, robot_2:temporary_wait withheld=empty_reroute |
| 105.501 | nav2 | robot_2 | Failed to make progress |
| 105.501 | nav2 | robot_2 | [follow_path] [ActionServer] Aborting handle. |
| 105.533 | m1_stale | robot_1 | STALE 0.97 s |
| 106.14 | m4_terminal | D3:robot_2:reroute | FAILED  moved=None tags=None deadline=None |
| 107.189 | safety_stop_span | robot_5 | to 613.76 (115265 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 22.933 | U:T1_fidelity / episode_gate_pass | 111/237 | 111/237 | 111/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D2 | 74.667 | pass / pass | 15/237 | 15/237 | 15/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 79.267 | pass / pass | 19/237 | 19/237 | 19/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |
| D4 | 104.633 | pass / pass | 85/237 | 85/237 | 85/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.02} |

## Decisions

### D1 at 15.433 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_1, crossing_order ['robot_5', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 1 and Robot 5 are less than 0.5 m apart and directly facing each other, both stopped. Robot 1 should yield to allow Robot 5 to proceed, clearing the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_5:0.230', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_5:2.35->2.038', 'grounding=retreat_shield:robot_3', 'grounding=retreat_shield:robot_4']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.388, 'crossing_order': ['robot_5'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 2.038, 'passer_robot_id': 'robot_5', 'reason': 'Robot 1 and Robot 5 are in a head-on standoff in a narrow corridor.', 'retreat_choice': 'A'}), ('robot_5', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True}), ('robot_4', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_1's retreat", 'retreat_shield_hold': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### D2 at 74.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 3 can yield and back up to allow Robot 2 to continue its delivery path northward, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield degrades to reroute: robot_3 has no retreat candidate clearing its park point (escort_hits_park:robot_2:0.316), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'fallback_reason': 'yield=infeasible:escort_hits_park:robot_2:0.316', 'reason': 'empty_reroute', 'would_dispatch_robot_ids': ['robot_3', 'robot_2']}, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_2:0.316', 'yield=infeasible:escort_hits_park:robot_2:0.316', 'grounding=node_handoff:robot_3->robot_2', 'grounding=dynamic_arms:lane:y']
- Actions: [('robot_3', 'reroute', {'waypoints': []}), ('robot_2', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_2'], 'G6_verbatim_contradicted': False}

### D3 at 79.267 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reroute, involved ['robot_2', 'robot_3'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reroute', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: rerouting robot_3 will resolve the head-on conflict by taking an alternative path, while robot_2 waits.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': True, 'C3_detail': {'involved_0': 'robot_2'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'reroute', {'waypoints': []}), ('robot_3', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### D4 at 104.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_2, crossing_order ['robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot_2 and robot_3 are in a head-on deadlock within 0.39 m. Having robot_2 yield and back up will clear the path for robot_3 to proceed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield degrades to reroute: robot_3 has no retreat candidate clearing its park point (escort_hits_park:robot_2:0.316), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'fallback_reason': 'yield=infeasible:escort_hits_park:robot_2:0.316', 'reason': 'empty_reroute', 'would_dispatch_robot_ids': ['robot_3', 'robot_2']}, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_2:0.316', 'yield=infeasible:escort_hits_park:robot_2:0.316', 'grounding=node_handoff:robot_3->robot_2', 'grounding=node_handoff_regrounded:robot_2->robot_3', 'grounding=dynamic_arms:lane:y']
- Actions: [('robot_3', 'reroute', {'waypoints': []}), ('robot_2', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_2', 'grounding=node_handoff_regrounded:robot_2->robot_3'], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_1:backup | backup | 1.388 | 15.433 | 18.866 | 70.209 | COMPLETED | 1.452 | 1.046 | 0.1256 (obstacle_2) | None (None) | completed | False |
| D1:robot_5:escort | escort | 2.038 | 15.433 | 48.4 | 70.255 | COMPLETED | 2.037 | 1.0 | 0.1605 (rack/SE_east) | None (None) | completed | False |
| D3:robot_2:reroute | reroute | None | 79.267 | 81.259 | 106.14 | FAILED | None | None | None (None) | None (None) | - | None |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_2 105.501 rel-s: Failed to make progress
- robot_2 105.501 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 19.125, 'pairs': 'robot_1+robot_5'}, {'rel': 70.353, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 2 spans; robot_5|min_distance_violation: 2 spans; robot_3|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans
