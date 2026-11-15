# Evidence Sheet EV-52a0c3

- Censoring: t_end 572.67 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=29 max residual 0.701 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 12.17 | 572.67 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5'], ['robot_2', 'robot_5'], ['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 98.47, 'until_rel': 572.67}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 16.97, 'until_rel': 572.67}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 112.67, 'until_rel': 572.67}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 100.67, 'until_rel': 572.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 112.17, 'to_rel': 572.67, 'duration_s': 460.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_2', 'from_rel': 112.17, 'to_rel': 572.67, 'duration_s': 460.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 112.17, 'to_rel': 572.67, 'duration_s': 460.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 112.17, 'to_rel': 572.67, 'duration_s': 460.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.22 | safety_stop_span | robot_5 | to 577.019 (142501 lines) |
| 11.23 | safety_stop_span | robot_2 | to 17.444 (1539 lines) |
| 12.189 | nav2 | robot_1 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 13.667 | analysis | D1 | positive strategy=yield involved=['robot_2', 'robot_5'] yield=robot_5 |
| 13.667 | dispatched | D1 | robot_2:yield, robot_5:temporary_wait, robot_3:temporary_wait, robot_1:temporary_wait |
| 15.07 | gt_submargin | robot_3|box:obstacle_2 | to 16.77 min gap 0.0215 m |
| 16.788 | safety_stop_span | robot_1 | to 577.019 (141128 lines) |
| 17.333 | m4_leg_start | D1:robot_2:backup | backup commanded=1.396 |
| 17.448 | exempt_change | - | robot_2+robot_5 |
| 50.6 | m4_leg_start | D1:robot_5:escort | escort commanded=1.768 |
| 94.899 | m4_terminal | D1:robot_2:backup | COMPLETED  moved=1.589 tags=['completed'] deadline=False |
| 97.947 | safety_stop_span | robot_3 | to 577.019 (120659 lines) |
| 98.67 | gt_submargin | robot_4|box:obstacle_2 | to 99.17 min gap 0.049 m |
| 100.482 | safety_stop_span | robot_4 | to 577.019 (120030 lines) |
| 101.47 | gt_submargin | robot_2|box:obstacle_1 | to 102.67 min gap 0.0237 m |
| 102.867 | analysis | D3 | positive strategy=temporary_wait involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 102.867 | dispatched | D3 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 104.569 | safety_stop_span | robot_2 | to 104.757 (48 lines) |
| 112.292 | safety_stop_span | robot_2 | to 577.019 (117044 lines) |
| 115.667 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 115.667 | withheld | D4 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.433 | U:T1_fidelity / episode_gate_pass | 71/237 | 71/237 | 71/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D1 | 13.667 | U:T1_fidelity / pass | 86/237 | 86/237 | 80/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 102.867 | pass / pass | 106/237 | 106/237 | 61/237 | True | {'robot': 'robot_5', 'heading_deg': 90, 'distance_m': 0.02} |
| D4 | 115.667 | pass / pass | 107/237 | 107/237 | 62/237 | True | {'robot': 'robot_2', 'heading_deg': 180, 'distance_m': 0.02} |

## Decisions

### D1 at 13.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_5'], yield_robot robot_5, crossing_order ['robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 5 is closer to an open area where it can back up and yield to let robot 2 pass.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: dispatch yields robot_2, not robot_5 (grounding=node_handoff_regrounded:robot_5->robot_2); swapped roles robot_5 (yield) <-> robot_2 (cross)', 'robot_ids': ['robot_2', 'robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_2->robot_5', 'grounding=node_handoff_regrounded:robot_5->robot_2', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_5:2.35->1.768', 'grounding=retreat_shield:robot_3', 'grounding=retreat_shield:robot_1']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.396, 'crossing_order': ['robot_5'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.768, 'passer_robot_id': 'robot_5', 'reason': "Robot 2 and robot 5 are facing each other in close proximity and both are stopped, blocking each other's path.", 'retreat_choice': 'B'}), ('robot_5', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat", 'retreat_shield_hold': True}), ('robot_1', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat", 'retreat_shield_hold': True})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_2->robot_5', 'grounding=node_handoff_regrounded:robot_5->robot_2'], 'G6_verbatim_contradicted': False}

### D2 at 98.7 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The robots are in the process of executing the active plan and clearing the area.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 102.867 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): None
- Justification: The active plan is still pending robot_4's continue action, so we should allow the robots to finish their maneuvers.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_2', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 115.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_2', 'robot_1', 'robot_3', 'robot_4'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}]
- Justification: The robots are in close proximity (several pairwise distances under 0.5m) and facing each other, so they need coordinated reversals to clear space at the junction.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: yield infeasible: robot_1 has 0.00 m retreat room < 0.77 m required; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.15 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_2:backup | backup | 1.396 | 13.667 | 17.333 | 94.899 | COMPLETED | 1.589 | 1.138 | 0.1454 (rack/NW_west) | None (None) | completed | False |
| D1:robot_5:escort | escort | 1.768 | 13.667 | 50.6 | None | None | 0.0 | 0.0 | 0.289 (obstacle_1) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_1 12.189 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 17.448, 'pairs': 'robot_2+robot_5'}, {'rel': 94.943, 'pairs': '-'}]
- Safety-stop spans: robot_5|min_distance_violation: 1 spans; robot_2|min_distance_violation: 3 spans; robot_1|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans
