# Evidence Sheet EV-f7ab58

- Censoring: t_end 144.303 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=27 max residual 2.695 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4 | 14.903 | 144.303 | False | D1:robot_1:backup | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_2', 'robot_3'], ['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.033 rel-s
- V1 input: {'a33_matched_positive_analyses': 5, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 101.6, 'until_rel': 144.3}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 23.4, 'until_rel': 144.3}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.1, 'until_rel': 144.3}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 23.0, 'to_rel': 131.0, 'duration_s': 108.0, 'to_censor': False, 'safety_stop_cover_fraction': 0.994}, {'robot': 'robot_3', 'from_rel': 14.8, 'to_rel': 99.4, 'duration_s': 84.6, 'to_censor': False, 'safety_stop_cover_fraction': 0.991}, {'robot': 'robot_4', 'from_rel': 14.8, 'to_rel': 99.4, 'duration_s': 84.6, 'to_censor': False, 'safety_stop_cover_fraction': 0.991}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.453 | safety_stop_span | robot_1 | to 16.096 (1169 lines) |
| 13.033 | analysis | D1 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_5 |
| 13.033 | dispatched | D1 | robot_1:yield, robot_5:temporary_wait |
| 15.333 | m4_leg_start | D1:robot_1:backup | backup commanded=1.361 |
| 15.537 | safety_stop_span | robot_4 | to 155.814 (35473 lines) |
| 15.543 | safety_stop_span | robot_3 | to 155.814 (35473 lines) |
| 16.1 | exempt_change | - | robot_1+robot_5 |
| 23.692 | safety_stop_span | robot_2 | to 155.814 (33401 lines) |
| 45.167 | m1_stale | robot_1 | STALE 10.73 s |
| 47.2 | analysis | D2 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_4'] yield=None |
| 47.2 | withheld | D2 | robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 55.972 | m4_terminal | D1:robot_1:backup | COMPLETED  moved=1.421 tags=['completed'] deadline=False |
| 97.833 | analysis | D3 | positive strategy=reverse involved=['robot_3', 'robot_4'] yield=None |
| 97.833 | dispatched | D3 | robot_3:temporary_wait, robot_4:temporary_wait |
| 101.53 | safety_stop_span | robot_1 | to 155.814 (13518 lines) |
| 102.933 | m1_stale | robot_1 | STALE 39.03 s |
| 110.8 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 110.8 | withheld | D4 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 129.233 | analysis | D5 | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 129.233 | dispatched | D5 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait |
| 142.0 | analysis | D6 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 142.0 | withheld | D6 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 143.067 | m1_stale | robot_1 | STALE 0.93 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 15.1 | U:T1_fidelity / episode_gate_pass | 102/237 | 102/237 | 102/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D2 | 47.2 | pass / pass | 26/237 | 26/237 | 12/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 97.833 | pass / pass | 9/237 | 9/237 | 9/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D4 | 110.8 | pass / pass | 33/237 | 33/237 | 8/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |
| D5 | 129.233 | pass / pass | 20/237 | 20/237 | 20/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |
| D6 | 142.0 | pass / pass | 8/237 | 8/237 | 8/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |

## Decisions

### D1 at 13.033 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_5, crossing_order ['robot_1', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having robot_5 (which is stale) yield and step aside allows robot_1 to proceed to its goal.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_5 has 0.00 m retreat room < 0.77 m required; swapped roles robot_5 (yield) <-> robot_1 (cross)', 'robot_ids': ['robot_1', 'robot_5']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_5 has 0.00 m retreat room < 0.77 m required; robot_1 feasible, from robot_5
- Degradation tags: ['yield_robot=regrounded', 'grounding=dynamic_arms:crossing', 'grounding=dynamic_arms:junction_box:N']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.361, 'crossing_order': ['robot_5'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.169, 'passer_robot_id': 'robot_5', 'reason': 'robot_1 and robot_5 are in a head-on conflict within 0.34 meters of each other, blocking both of their paths.', 'retreat_choice': 'A'}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=regrounded', 'yield_robot_grounded_from=robot_5'], 'G6_verbatim_contradicted': False}

### D2 at 47.2 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: A junction_clear strategy is needed to resolve the deadlock among the three adjacent robots by reversing or yielding to clear the path sequentially.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_2: yield infeasible: robot_2/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 97.833 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): None
- Justification: Robot 3 and Robot 4 are physically conflicting (distance < 0.5 m) and facing each other, so reversing Robot 3 as planned will resolve the local block.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 110.8 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_1', 'robot_4', 'robot_3', 'robot_2'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: The robots are in a tight, multi-robot cluster facing opposing directions. Executing a junction_clear strategy will coordinate their backing up and crossing turns.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: yield infeasible: robot_4/robot_1 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 129.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_2 and robot_3 reverse will clear space in the congested area, allowing robot_4 and robot_1 to eventually pass through once the way is clear.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_3'], 'involved': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_1/robot_2 both outside the corridor on the same side; a reverse would traverse it; swapped roles robot_2 (reverse) <-> robot_4 (wait)', 'robot_ids': ['robot_2', 'robot_4']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 142.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_3', 'robot_4', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Clear the deadlock by having the opposing robots (robot_4 and robot_1) reverse and yield, letting robot_2 and robot_3 cross first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_1:backup | backup | 1.361 | 13.033 | 15.333 | 55.972 | COMPLETED | 1.421 | 1.044 | 0.167 (rack/NW_north) | None (None) | completed | False |
| D1:robot_5:escort | escort | 1.169 | 13.033 | 44.066 | 56.056 | COMPLETED | 1.167 | 0.999 | 0.3162 (obstacle_1) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_1": [{"from_rel": 45.167, "to_rel": 55.9, "duration_s": 10.73, "ge_10s": true}, {"from_rel": 102.933, "to_rel": 141.967, "duration_s": 39.03, "ge_10s": true}, {"from_rel": 143.067, "to_rel": 144.0, "duration_s": 0.93, "ge_10s": false}]}

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 16.1, 'pairs': 'robot_1+robot_5'}, {'rel': 56.017, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans
