# Evidence Sheet EV-b13ac7

- Censoring: t_end 569.94 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=6 max residual 0.022 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 12.24 | 569.94 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_3'], ['robot_2', 'robot_5'], ['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 6, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 40.94, 'until_rel': 569.94}, {'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 17.24, 'until_rel': 569.94}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 72.74, 'until_rel': 569.94}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 38.94, 'until_rel': 569.94}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 16.94, 'to_rel': 569.94, 'duration_s': 553.0, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_2', 'from_rel': 40.94, 'to_rel': 569.94, 'duration_s': 529.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.994}, {'robot': 'robot_3', 'from_rel': 17.44, 'to_rel': 569.94, 'duration_s': 552.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 38.94, 'to_rel': 569.94, 'duration_s': 531.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.995}, {'robot': 'robot_5', 'from_rel': 72.44, 'to_rel': 569.94, 'duration_s': 497.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.985}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.6 | safety_stop_span | robot_4 | to 15.845 (991 lines) |
| 11.606 | safety_stop_span | robot_3 | to 15.846 (991 lines) |
| 14.4 | analysis | D1 | positive strategy=reverse involved=['robot_3', 'robot_4'] yield=None |
| 14.4 | dispatched | D1 | robot_3:reverse, robot_4:reverse |
| 15.8 | m4_leg_start | D1:robot_3:reverse | reverse commanded=1.3 |
| 15.8 | m4_leg_start | D1:robot_4:reverse | reverse commanded=1.3 |
| 15.847 | exempt_change | - | robot_3+robot_4 |
| 16.986 | safety_stop_span | robot_1 | to 609.329 (139570 lines) |
| 16.987 | safety_stop_span | robot_3 | to 609.329 (139570 lines) |
| 17.386 | m4_terminal | D1:robot_3:reverse | FAILED  moved=0.106 tags=['not_executed(<50%)'] deadline=False |
| 18.533 | m1_stale | robot_2 | STALE 0.77 s |
| 20.24 | gt_submargin | robot_5|box:obstacle_2 | to 21.74 min gap 0.0171 m |
| 31.724 | m4_terminal | D1:robot_4:reverse | COMPLETED  moved=1.31 tags=['completed'] deadline=False |
| 33.467 | analysis | D2 | positive strategy=yield involved=['robot_1', 'robot_3'] yield=robot_1 |
| 33.467 | withheld | D2 | robot_1:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 34.31 | nav2 | robot_2 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 37.467 | analysis | D3 | positive strategy=junction_clear involved=['robot_1', 'robot_3', 'robot_4'] yield=None |
| 37.467 | withheld | D3 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 41.7 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 41.7 | withheld | D4 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 41.791 | safety_stop_span | robot_4 | to 609.329 (133766 lines) |
| 44.288 | safety_stop_span | robot_2 | to 609.329 (133192 lines) |
| 45.867 | analysis | D5 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 45.867 | withheld | D5 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 74.767 | analysis | D6 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 74.767 | withheld | D6 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 80.003 | safety_stop_span | robot_5 | to 609.329 (124821 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.433 | episode_gate_pass / episode_gate_pass | 60/237 | 60/237 | 60/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D1 | 14.4 | pass / pass | 60/237 | 60/237 | 10/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D2 | 33.467 | pass / pass | 83/237 | 83/237 | 80/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 37.467 | pass / pass | 18/237 | 18/237 | 12/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D4 | 41.7 | pass / pass | 89/237 | 89/237 | 36/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D5 | 45.867 | pass / pass | 85/237 | 85/237 | 32/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D6 | 74.767 | pass / pass | 122/237 | 122/237 | 64/237 | True | {'robot': 'robot_5', 'heading_deg': 90, 'distance_m': 0.03} |

## Decisions

### D1 at 14.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Both robots are facing each other at very close range and are stopped; reversing will allow them to create enough clearance to negotiate passing.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_3', 'robot_4'], 'involved': ['robot_3', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x']
- Actions: [('robot_3', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True}), ('robot_4', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 33.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3'], yield_robot robot_1, crossing_order ['robot_3', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since reverse has failed, robot_1 will yield to let robot_3 cross first and clear the narrow corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_3']}, yield refusal yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_1,robot_3:88']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 88 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 37.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_1', 'robot_3', 'robot_4'], type crowding
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 and robot 1/3 are facing each other in close proximity; reversing failed, so a coordinated junction clearance with robot_4 yielding/reversing first is necessary.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 41.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_2', 'robot_1', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: A multi-robot deadlock is occurring in the bottom-left region. Proposing a junction clear where robot_4 reverses or yields, allowing robot_3 to move.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: yield infeasible: robot_1/robot_2 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 45.867 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_1', 'robot_2'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 will reverse out of the cluster first to create space, while the others wait in place for the junction to clear.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### D6 at 74.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_1', 'robot_2', 'robot_3', 'robot_4'], type crowding
- Plan legs (model): None
- Justification: The existing plan has robot_4 reversing out of the congested area while others wait, which will clear the congestion. We hold this plan.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_3:reverse | reverse | 1.3 | 14.4 | 15.8 | 17.386 | FAILED | 0.106 | 0.082 | 0.3898 (rack/SW_south) | None (None) | not_executed(<50%) | False |
| D1:robot_4:reverse | reverse | 1.3 | 14.4 | 15.8 | 31.724 | COMPLETED | 1.31 | 1.007 | 0.2559 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_2 34.31 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 15.847, 'pairs': 'robot_3+robot_4'}, {'rel': 31.725, 'pairs': '-'}]
- Safety-stop spans: robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_1|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
