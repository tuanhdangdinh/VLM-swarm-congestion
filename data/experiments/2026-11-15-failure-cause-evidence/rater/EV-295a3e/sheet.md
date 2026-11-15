# Evidence Sheet EV-295a3e

- Censoring: t_end 568.17 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=46 max residual 2.62 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 65.07 | 568.17 | False | D1:robot_2:backup, D1:robot_3:escort, D1:robot_3:wait, D1:robot_5:wait, D1:robot_4:wait, D1:robot_1:wait | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_2', 'robot_3'], ['robot_2', 'robot_4'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.8 rel-s
- V1 input: {'a33_matched_positive_analyses': 8, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 65.67, 'until_rel': 568.17}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 100.97, 'until_rel': 568.17}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 133.57, 'until_rel': 568.17}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 267.07, 'until_rel': 568.17}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 94.17, 'to_rel': 267.97, 'duration_s': 173.8, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_1', 'from_rel': 276.27, 'to_rel': 568.17, 'duration_s': 291.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_2', 'from_rel': 100.77, 'to_rel': 185.27, 'duration_s': 84.5, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 114.87, 'to_rel': 267.97, 'duration_s': 153.1, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 276.27, 'to_rel': 568.17, 'duration_s': 291.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 133.57, 'to_rel': 267.97, 'duration_s': 134.4, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 276.27, 'to_rel': 568.17, 'duration_s': 291.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 276.27, 'to_rel': 568.17, 'duration_s': 291.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_5|box:rack/SW_west: [111.37, 139.47] -0.0017; robot_5|box:obstacle_1: [155.67, 157.97] 0.0032

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.05 | safety_stop_span | robot_2 | to 19.164 (1713 lines) |
| 12.066 | safety_stop_span | robot_3 | to 19.165 (1713 lines) |
| 12.27 | gt_submargin | robot_1|box:obstacle_2 | to 12.97 min gap 0.0467 m |
| 13.8 | analysis | D1 | positive strategy=yield involved=['robot_2', 'robot_3'] yield=robot_3 |
| 13.8 | dispatched | D1 | robot_2:yield, robot_3:temporary_wait, robot_5:temporary_wait, robot_4:temporary_wait, robot_1:temporary_wait |
| 18.062 | safety_stop_span | robot_5 | to 99.478 (19998 lines) |
| 18.071 | safety_stop_span | robot_4 | to 99.479 (19998 lines) |
| 18.2 | m4_leg_start | D1:robot_2:backup | backup commanded=1.415 |
| 19.167 | exempt_change | - | robot_1+robot_2,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5 |
| 50.59 | exempt_change | - | robot_2+robot_3 |
| 51.733 | m4_leg_start | D1:robot_3:escort | escort commanded=1.669 |
| 53.4 | m1_stale | robot_2 | STALE 7.6 s |
| 63.004 | safety_stop_span | robot_1 | to 581.909 (126361 lines) |
| 63.005 | safety_stop_span | robot_3 | to 581.909 (126361 lines) |
| 94.114 | m4_terminal | D1:robot_2:backup | COMPLETED  moved=1.597 tags=['completed'] deadline=False |
| 98.292 | safety_stop_span | robot_2 | to 581.909 (117723 lines) |
| 99.481 | exempt_change | - | robot_1+robot_4,robot_1+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5 |
| 100.133 | analysis | D2 | positive strategy=reverse involved=['robot_4', 'robot_5'] yield=None |
| 100.133 | dispatched | D2 | robot_4:reverse, robot_5:reverse |
| 101.8 | m4_leg_start | D2:robot_4:reverse | reverse commanded=1.3 |
| 101.8 | m4_leg_start | D2:robot_5:reverse | reverse commanded=1.3 |
| 111.37 | gt_contact | robot_5|box:rack/SW_west | to 139.47 min gap -0.0017 m |
| 113.268 | m4_terminal | D2:robot_4:reverse | COMPLETED  moved=1.191 tags=['completed'] deadline=False |
| 113.333 | exempt_change | - | robot_1+robot_5,robot_3+robot_5,robot_4+robot_5 |
| 114.801 | m4_terminal | D1:robot_3:escort | FAILED escort timed out in phase drive moved=1.163 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 131.534 | safety_stop_span | robot_4 | to 581.91 (109619 lines) |
| 135.842 | m4_terminal | D2:robot_5:reverse | FAILED  moved=1.225 tags=[] deadline=True |
| 136.806 | nav2 | robot_5 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 141.067 | analysis | D3 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 141.067 | withheld | D3 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 145.1 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=robot_3 |
| 145.1 | withheld | D4 | robot_3:temporary_wait, robot_1:temporary_wait, robot_2:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 149.6 | analysis | D5 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 149.6 | withheld | D5 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 155.67 | gt_contact | robot_5|box:obstacle_1 | to 157.97 min gap 0.0032 m |
| 174.9 | nav2 | robot_5 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 182.286 | safety_stop_span | robot_5 | to 185.842 (872 lines) |
| 183.267 | analysis | D6 | positive strategy=yield involved=['robot_2', 'robot_5'] yield=robot_2 |
| 183.267 | dispatched | D6 | robot_5:yield, robot_2:temporary_wait |
| 185.233 | m4_leg_start | D6:robot_5:backup | backup commanded=1.295 |
| 185.845 | exempt_change | - | robot_2+robot_5 |
| 213.3 | m4_leg_start | D6:robot_2:escort | escort commanded=2.211 |
| 257.824 | m4_terminal | D6:robot_5:backup | COMPLETED  moved=1.362 tags=['completed'] deadline=False |
| 261.6 | analysis | D7 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 261.6 | withheld | D7 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 266.033 | analysis | D8 | positive strategy=temporary_wait involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 266.033 | dispatched | D8 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 267.082 | safety_stop_span | robot_5 | to 581.909 (76550 lines) |
| 279.367 | analysis | D9 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=robot_5 |
| 279.367 | withheld | D9 | robot_5:temporary_wait, robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 65.367 | U:T1_fidelity / U:T1_fidelity | 100/237 | 100/237 | 100/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D2 | 100.133 | pass / pass | 107/237 | 107/237 | 107/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 141.067 | pass / pass | 80/237 | 80/237 | 65/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |
| D4 | 145.1 | pass / pass | 98/237 | 98/237 | 86/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D5 | 149.6 | pass / pass | 86/237 | 86/237 | 74/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D6 | 183.267 | pass / pass | 65/237 | 65/237 | 61/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |
| D7 | 261.6 | pass / pass | 55/237 | 55/237 | 51/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D8 | 266.033 | pass / pass | 57/237 | 57/237 | 53/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| D9 | 279.367 | pass / pass | 65/237 | 65/237 | 61/237 | True | {'robot': 'robot_5', 'heading_deg': 90, 'distance_m': 0.02} |

## Decisions

### D1 at 13.8 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3'], yield_robot robot_3, crossing_order ['robot_2', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_3 yield and back up clears the way for robot_2 to proceed through the corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_3 has no retreat candidate surviving the sweep; robot_2 has an executable retreat; swapped roles robot_3 (yield) <-> robot_2 (cross)', 'robot_ids': ['robot_2', 'robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_3 has no retreat candidate surviving the sweep; robot_2 has an executable retreat, from robot_3
- Degradation tags: ['yield_robot=sweep_regrounded:robot_3->robot_2', 'retreat=default:no_choice', 'grounding=dynamic_arms:lane:y', 'grounding=escort_turn_cap:robot_3:2.35->1.669', 'grounding=retreat_shield:robot_5', 'grounding=retreat_shield:robot_4', 'grounding=retreat_shield:robot_1']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.415, 'crossing_order': ['robot_3'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.669, 'passer_robot_id': 'robot_3', 'reason': 'robot_2 and robot_3 are facing each other in a narrow corridor with a distance of 0.29 m.', 'retreat_choice': 'C'}), ('robot_3', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"}), ('robot_4', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"}), ('robot_1', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=sweep_regrounded:robot_3->robot_2', 'yield_robot_grounded_from=robot_3'], 'G6_verbatim_contradicted': False}

### D2 at 100.133 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Since Robot 4 and Robot 5 are head-on within 0.38m of each other, they need to reverse to clear the deadlock and allow safe passage.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4', 'robot_5'], 'involved': ['robot_4', 'robot_5']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:y']
- Actions: [('robot_4', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True}), ('robot_5', 'reverse', {'backup_distance_m': 1.3, 'fresh_latch_fast_fail': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 141.067 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order ['robot_1', 'robot_3', 'robot_2', 'robot_4'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: A junction clear allows coordinated actions (reversing and crossing) to resolve the high-density cluster where simple reversing didn't succeed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 145.1 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot robot_3, crossing_order ['robot_2', 'robot_4', 'robot_1', 'robot_3'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Reversing failed to clear the congestion previously, so a junction clearance strategy will coordinate the movement of the robot group by reversing robot_4 and robot_2, waiting with robot_1 and robot_3, and clearing the junction systematically.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: yield infeasible: robot_3 has 0.15 m retreat room < 0.77 m required; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_3', 'robot_1', 'robot_2', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_3 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 149.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): None
- Justification: The active resolution plan is already in progress and nothing in the environment or robot status has changed to warrant a revision.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 183.267 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_5'], yield_robot robot_2, crossing_order ['robot_5', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}]
- Justification: Robot_2 and Robot_5 are head-on in close proximity; Robot_2 must yield (back up) to allow Robot_5 to continue through the narrow corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_2 has no retreat candidate surviving the sweep; robot_5 has an executable retreat; swapped roles robot_2 (yield) <-> robot_5 (cross)', 'robot_ids': ['robot_2', 'robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_2 has no retreat candidate surviving the sweep; robot_5 has an executable retreat, from robot_2
- Degradation tags: ['yield_robot=sweep_regrounded:robot_2->robot_5', 'retreat=default:no_choice', 'grounding=dynamic_arms:lane:y', 'grounding=escort_turn_cap:robot_2:2.35->2.211']
- Actions: [('robot_5', 'yield', {'backup_distance_m': 1.295, 'crossing_order': ['robot_2'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 2.211, 'passer_robot_id': 'robot_2', 'reason': 'Robot_2 and Robot_5 are stopped in a head-on conflict within 0.5 meters of each other.', 'retreat_choice': 'A'}), ('robot_2', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=sweep_regrounded:robot_2->robot_5', 'yield_robot_grounded_from=robot_2'], 'G6_verbatim_contradicted': False}

### D7 at 261.6 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_1', 'robot_3', 'robot_4', 'robot_2'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_2'}]
- Justification: Robot 5 has the highest velocity and is moving down, so clearing the junction by letting Robot 5 finish its delivery and then ordering the remaining robots to disperse avoids deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan inconsistent: strategy 'junction_clear' is not refined by actions ['cross', 'cross', 'cross', 'wait', 'wait'], held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D8 at 266.033 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): None
- Justification: Wait for robot_2 to finish its crossing phase before initiating the next moves for the waiting robots.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D9 at 279.367 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_2', 'robot_4', 'robot_3', 'robot_1', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_1'}]
- Justification: Using a junction clear strategy forces robot_5 to yield or reverse first, allowing the remaining robots to exit the crowded bottleneck in an orderly fashion.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_5', 'robot_1', 'robot_2', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.15 m, robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_2:backup | backup | 1.415 | 13.8 | 18.2 | 94.114 | COMPLETED | 1.597 | 1.129 | 0.2807 (rack/SW_south) | None (None) | completed | False |
| D1:robot_3:escort | escort | 1.669 | 13.8 | 51.733 | 114.801 | FAILED | 1.163 | 0.697 | 0.3703 (obstacle_2) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| D2:robot_4:reverse | reverse | 1.3 | 100.133 | 101.8 | 113.268 | COMPLETED | 1.191 | 0.916 | 0.1185 (rack/NW_west) | None (None) | completed | False |
| D2:robot_5:reverse | reverse | 1.3 | 100.133 | 101.8 | 135.842 | FAILED | 1.225 | 0.942 | -0.0017 (rack/SW_west) | None (None) | - | True |
| D6:robot_5:backup | backup | 1.295 | 183.267 | 185.233 | 257.824 | COMPLETED | 1.362 | 1.052 | 0.1963 (obstacle_2) | None (None) | completed | False |
| D6:robot_2:escort | escort | 2.211 | 183.267 | 213.3 | None | None | 0.002 | 0.001 | 0.0944 (obstacle_1) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_5 136.806 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.
- robot_5 174.9 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 19.167, 'pairs': 'robot_1+robot_2,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5'}, {'rel': 50.59, 'pairs': 'robot_2+robot_3'}, {'rel': 94.116, 'pairs': '-'}, {'rel': 99.481, 'pairs': 'robot_1+robot_4,robot_1+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5'}, {'rel': 113.333, 'pairs': 'robot_1+robot_5,robot_3+robot_5,robot_4+robot_5'}, {'rel': 135.879, 'pairs': '-'}, {'rel': 185.845, 'pairs': 'robot_2+robot_5'}, {'rel': 257.834, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_5|min_distance_violation: 3 spans; robot_4|min_distance_violation: 2 spans; robot_1|min_distance_violation: 1 spans
