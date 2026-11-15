# Evidence Sheet EV-7bda3f

- Censoring: t_end 102.277 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=24 max residual 0.649 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 12.277 | 102.277 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 81.177 | 102.277 | False | D3:robot_5:backup, D3:robot_1:escort, D3:robot_1:wait | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 4, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 12.78, 'until_rel': 102.28}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 34.98, 'until_rel': 102.28}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 23.78, 'to_rel': 88.18, 'duration_s': 64.4, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 23.78, 'to_rel': 88.18, 'duration_s': 64.4, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.566 | safety_stop_span | robot_2 | to 114.588 (24164 lines) |
| 11.572 | safety_stop_span | robot_3 | to 114.588 (24164 lines) |
| 14.267 | analysis | D1 | positive strategy=reverse involved=['robot_2', 'robot_3'] yield=None |
| 14.267 | dispatched | D1 | robot_2:temporary_wait, robot_3:temporary_wait |
| 27.2 | analysis | D2 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_5'] yield=None |
| 27.2 | withheld | D2 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 35.324 | safety_stop_span | robot_4 | to 114.588 (18546 lines) |
| 81.333 | analysis | D4 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=robot_2 |
| 81.333 | withheld | D4 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 85.867 | analysis | D5 | positive strategy=reverse involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 85.867 | dispatched | D5 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 99.433 | analysis | D6 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 99.433 | withheld | D6 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.367 | episode_gate_pass / episode_gate_pass | 61/237 | 61/237 | 61/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |
| D1 | 14.267 | pass / pass | 60/237 | 60/237 | 60/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |
| D4 | 81.333 | pass / pass | 23/237 | 23/237 | 23/237 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04} |
| D5 | 85.867 | pass / pass | 23/237 | 23/237 | 23/237 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04} |
| D6 | 99.433 | pass / pass | 23/237 | 23/237 | 23/237 | True | {'robot': 'robot_4', 'heading_deg': 270, 'distance_m': 0.04} |

### FU2

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 36.567 rel-s
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 81.28, 'until_rel': 102.28}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 27.2 | analysis | D2 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_5'] yield=None |
| 27.2 | withheld | D2 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 36.567 | analysis | D3 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_1 |
| 36.567 | dispatched | D3 | robot_5:yield, robot_1:temporary_wait |
| 38.234 | m4_leg_start | D3:robot_5:backup | backup commanded=1.361 |
| 38.912 | exempt_change | - | robot_1+robot_5 |
| 66.9 | m4_leg_start | D3:robot_1:escort | escort commanded=0.817 |
| 77.355 | m4_terminal | D3:robot_5:backup | COMPLETED  moved=1.422 tags=['completed'] deadline=False |
| 77.362 | m4_terminal | D3:robot_1:escort | COMPLETED escort complete: moved 0.819 m moved=0.807 tags=['completed'] deadline=False |
| 80.871 | safety_stop_span | robot_5 | to 114.588 (7665 lines) |
| 80.872 | safety_stop_span | robot_1 | to 114.588 (7665 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 81.367 | episode_gate_pass / episode_gate_pass | 28/88 | 28/88 | 28/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.02} |

## Decisions

### D1 at 14.267 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_3'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Both robots are stopped and face each other at a very close distance of 0.33m, which requires reversing to clear the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_3'], 'involved': ['robot_2', 'robot_3']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: reverse infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 27.2 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_3', 'robot_1', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: A junction_clear strategy is needed to resolve multiple close-proximity blocks by directing the robots to yield or reverse in a coordinated sequence.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 36.567 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_1, crossing_order ['robot_5', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 1 can yield and back up to allow Robot 5 to proceed, clearing the tight passageway.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: dispatch yields robot_5, not robot_1 (grounding=heading_regrounded:robot_1->robot_5); swapped roles robot_1 (yield) <-> robot_5 (cross)', 'robot_ids': ['robot_1', 'robot_5']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=dynamic_arms:bearing_lane:robot_1:37', 'grounding=heading_regrounded:robot_1->robot_5', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_1:2.35->0.817']
- Actions: [('robot_5', 'yield', {'backup_distance_m': 1.361, 'crossing_order': ['robot_1'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 0.817, 'passer_robot_id': 'robot_1', 'reason': "Robot 1 and Robot 5 are facing each other in close proximity, blocking each other's paths.", 'retreat_choice': 'A'}), ('robot_1', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_1->robot_5'], 'G6_verbatim_contradicted': False}

### D4 at 81.333 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot robot_2, crossing_order ['robot_3', 'robot_4', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 2 should reverse or yield to allow the convoy of Robot 3 and Robot 4 to proceed north and clear the aisle.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 85.867 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_3', 'robot_4', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: robot_2 needs to reverse to clear the deadlock with robot_3, allowing robot_3 and robot_4 to proceed.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2'], 'involved': ['robot_2', 'robot_3', 'robot_4']}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; swapped roles robot_2 (reverse) <-> robot_4 (wait)', 'robot_ids': ['robot_2', 'robot_4']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 99.433 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: A junction clear is needed to safely back the robots out and establish a sequential passing order to resolve the tight deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D3:robot_5:backup | backup | 1.361 | 36.567 | 38.234 | 77.355 | COMPLETED | 1.422 | 1.044 | 0.124 (obstacle_1) | None (None) | completed | False |
| D3:robot_1:escort | escort | 0.817 | 36.567 | 66.9 | 77.362 | COMPLETED | 0.807 | 0.988 | 0.1564 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 38.912, 'pairs': 'robot_1+robot_5'}, {'rel': 77.398, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_5|min_distance_violation: 2 spans; robot_1|min_distance_violation: 2 spans; robot_4|min_distance_violation: 1 spans
