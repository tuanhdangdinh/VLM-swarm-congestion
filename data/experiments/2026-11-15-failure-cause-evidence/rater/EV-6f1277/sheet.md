# Evidence Sheet EV-6f1277

- Censoring: t_end 569.673 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=6 max residual 0.008 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_4, robot_5 | 17.273 | 569.673 | False | - | - |
| FU2 | conflict | robot_1, robot_2, robot_3 | 23.473 | 569.673 | False | - | - |

### FU1

- Pairs: [['robot_4', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 7, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 17.77, 'until_rel': 569.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_4', 'from_rel': 78.37, 'to_rel': 569.67, 'duration_s': 491.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.96}, {'robot': 'robot_5', 'from_rel': 78.37, 'to_rel': 569.67, 'duration_s': 491.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.96}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 17.718 | safety_stop_span | robot_5 | to 550.223 (140189 lines) |
| 17.726 | safety_stop_span | robot_4 | to 550.223 (140189 lines) |
| 19.267 | analysis | D1 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 19.267 | withheld | D1 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 23.767 | analysis | D2 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 23.767 | withheld | D2 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 27.933 | analysis | D3 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 27.933 | withheld | D3 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 64.433 | analysis | D4 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 64.433 | withheld | D4 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 68.667 | analysis | D5 | positive strategy=reverse involved=['robot_4', 'robot_5'] yield=None |
| 68.667 | dispatched | D5 | robot_4:temporary_wait, robot_5:temporary_wait |
| 81.467 | analysis | D6 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 81.467 | withheld | D6 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 124.633 | analysis | D7 | positive strategy=yield involved=['robot_4', 'robot_5'] yield=robot_5 |
| 124.633 | withheld | D7 | robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 198.8 | m1_stale | robot_5 | STALE 0.2 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 17.333 | episode_gate_pass / episode_gate_pass | 6/88 | 6/88 | 6/88 | True | {'robot': 'robot_5', 'heading_deg': 315, 'distance_m': 0.06} |
| D1 | 19.267 | pass / pass | 6/88 | 6/88 | 6/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D2 | 23.767 | pass / pass | 7/88 | 7/88 | 5/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D3 | 27.933 | pass / pass | 7/88 | 7/88 | 5/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D4 | 64.433 | pass / pass | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D5 | 68.667 | pass / pass | 3/88 | 3/88 | 3/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D6 | 81.467 | pass / pass | 7/88 | 7/88 | 5/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |
| D7 | 124.633 | pass / pass | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.16} |

### FU2

- Pairs: [['robot_1', 'robot_2'], ['robot_2', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 122.57, 'until_rel': 569.67}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 23.77, 'until_rel': 569.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 122.27, 'to_rel': 569.67, 'duration_s': 447.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.955}, {'robot': 'robot_2', 'from_rel': 23.47, 'to_rel': 569.67, 'duration_s': 546.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.964}, {'robot': 'robot_3', 'from_rel': 23.57, 'to_rel': 569.67, 'duration_s': 546.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.964}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 18.77 | gt_submargin | robot_2|box:obstacle_1 | to 20.37 min gap 0.0067 m |
| 21.933 | m1_stale | robot_1 | STALE 0.8 s |
| 23.839 | safety_stop_span | robot_3 | to 550.223 (138582 lines) |
| 23.845 | safety_stop_span | robot_2 | to 550.223 (138582 lines) |
| 119.97 | gt_submargin | robot_1|box:obstacle_1 | to 121.37 min gap 0.0155 m |
| 122.761 | safety_stop_span | robot_1 | to 550.223 (112667 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 23.533 | episode_gate_pass / episode_gate_pass | 80/237 | 80/237 | 80/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### D1 at 19.267 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Since they are in a head-on deadlock in a narrow lane, Robot_5 (moving) should yield and back up or step aside to let Robot_4 (stopped) pass or resolve its route.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:42', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

### D2 at 23.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: robot_5 will yield and back up, allowing robot_4 to cross and clear the narrow aisle.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:42', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

### D3 at 27.933 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 5 can yield and back up to allow Robot 4 to pass through or proceed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:41', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

### D4 at 64.433 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: robot_4 and robot_5 are in a head-on deadlock within 0.30 m. Designating robot_5 to yield will allow robot_4 to pass safely.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:42', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

### D5 at 68.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Both robots are facing each other in very close proximity and are stopped, creating a physical deadlock that requires at least one of them to reverse to clear the lane.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4', 'robot_5'], 'involved': ['robot_4', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: reverse infeasible: robot_4/robot_5 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_5: reverse infeasible: robot_4/robot_5 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 81.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 5 should yield to allow Robot 4 to proceed to its goal first, resolving the head-on conflict.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:42', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

### D7 at 124.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_4', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Robot 5 can yield and back up to allow robot 4 to pass through the corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'would_dispatch_robot_ids': ['robot_4', 'robot_5']}, yield refusal yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)', 'grounding=dynamic_arms:bearing_lane:robot_5:41', 'grounding=heading_regrounded:robot_5->robot_4', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no executable retreat (robot_4 has no retreat candidate surviving the sweep; robot_5 would back up off its retreat axis)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_5->robot_4'], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: []
- Safety-stop spans: robot_5|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans
