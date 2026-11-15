# Evidence Sheet EV-072a17

- Censoring: t_end 571.437 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=20 max residual 0.565 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_5 | 22.937 | 571.437 | False | D1:robot_2:backup, D1:robot_5:escort, D1:robot_5:wait | - |
| FU2 | conflict | robot_1, robot_4 | 30.137 | 571.437 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_5'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 14.133 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 105.64, 'until_rel': 571.44}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 23.14, 'until_rel': 571.44}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 105.64, 'to_rel': 571.44, 'duration_s': 465.8, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 22.94, 'to_rel': 102.24, 'duration_s': 79.3, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 110.54, 'to_rel': 571.44, 'duration_s': 460.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.679 | safety_stop_span | robot_2 | to 18.449 (1634 lines) |
| 11.687 | safety_stop_span | robot_5 | to 18.449 (1634 lines) |
| 14.133 | analysis | D1 | positive strategy=yield involved=['robot_2', 'robot_5'] yield=robot_5 |
| 14.133 | dispatched | D1 | robot_2:yield, robot_5:temporary_wait |
| 16.14 | gt_submargin | robot_3|box:obstacle_2 | to 17.04 min gap 0.0431 m |
| 18.267 | m4_leg_start | D1:robot_2:backup | backup commanded=1.438 |
| 18.451 | exempt_change | - | robot_2+robot_5 |
| 22.735 | safety_stop_span | robot_5 | to 590.468 (138613 lines) |
| 22.735 | safety_stop_span | robot_3 | to 590.468 (138613 lines) |
| 51.867 | m4_leg_start | D1:robot_5:escort | escort commanded=1.775 |
| 96.302 | m4_terminal | D1:robot_2:backup | COMPLETED  moved=1.613 tags=['completed'] deadline=False |
| 100.067 | analysis | D2 | positive strategy=temporary_wait involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 100.067 | dispatched | D2 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 105.762 | safety_stop_span | robot_2 | to 590.467 (118271 lines) |
| 113.567 | analysis | D3 | positive strategy=junction_clear involved=['robot_2', 'robot_3', 'robot_5'] yield=None |
| 113.567 | withheld | D3 | robot_2:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 23.067 | episode_gate_pass / episode_gate_pass | 125/237 | 125/237 | 125/237 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |
| D3 | 113.567 | pass / pass | 52/237 | 52/237 | 52/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.02} |

### FU2

- Pairs: [['robot_1', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 30.34, 'until_rel': 571.44}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 30.24, 'to_rel': 102.24, 'duration_s': 72.0, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_1', 'from_rel': 110.54, 'to_rel': 571.44, 'duration_s': 460.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 32.64, 'to_rel': 102.24, 'duration_s': 69.6, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 110.54, 'to_rel': 571.44, 'duration_s': 460.9, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 30.172 | safety_stop_span | robot_4 | to 590.468 (136798 lines) |
| 30.179 | safety_stop_span | robot_1 | to 590.468 (136798 lines) |
| 30.181 | nav2 | robot_1 | [follow_path] [ActionServer] Aborting handle. |
| 100.067 | analysis | D2 | positive strategy=temporary_wait involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 100.067 | dispatched | D2 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 30.167 | episode_gate_pass / episode_gate_pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 135, 'distance_m': 0.03} |
| D2 | 100.067 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 135, 'distance_m': 0.03} |

## Decisions

### D1 at 14.133 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_5'], yield_robot robot_5, crossing_order ['robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 5 is stopped and has space to back up or step aside to allow Robot 2 to proceed through.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_5 has no retreat candidate surviving the sweep; robot_2 has an executable retreat; swapped roles robot_5 (yield) <-> robot_2 (cross)', 'robot_ids': ['robot_2', 'robot_5']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_5 has no retreat candidate surviving the sweep; robot_2 has an executable retreat, from robot_5
- Degradation tags: ['yield_robot=sweep_regrounded:robot_5->robot_2', 'retreat=default:no_choice', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_5:2.35->1.775']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.438, 'crossing_order': ['robot_5'], 'passer_escort_distance_m': 1.775, 'passer_robot_id': 'robot_5', 'reason': 'Two robots are blocked head-on in close proximity and both have stopped.', 'retreat_choice': 'B'}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=sweep_regrounded:robot_5->robot_2', 'yield_robot_grounded_from=robot_5'], 'G6_verbatim_contradicted': False}

### D2 at 100.067 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): None
- Justification: The active plan is still valid and in progress; the stopped robots are pending their continue actions while robot_2 is currently moving and clearing the area.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 113.567 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 2 must reverse to create clearance for robot 5 to proceed, resolving the head-on conflict.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.15 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_2:backup | backup | 1.438 | 14.133 | 18.267 | 96.302 | COMPLETED | 1.613 | 1.122 | 0.1658 (rack/SW_west) | None (None) | completed | False |
| D1:robot_5:escort | escort | 1.775 | 14.133 | 51.867 | None | None | 0.0 | 0.0 | 0.418 (obstacle_1) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_1 30.181 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 18.451, 'pairs': 'robot_2+robot_5'}, {'rel': 96.306, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_5|min_distance_violation: 2 spans; robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans
