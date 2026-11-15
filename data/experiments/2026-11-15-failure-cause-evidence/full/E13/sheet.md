# Evidence Sheet E13

- Censoring: t_end 569.807 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=18 max residual 0.157 s
- Outcome fields (frozen, copied): {"censor_reason": "horizon", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 569.8, "tasks_completed": 1, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 23.607 | 569.807 | False | 984e3bdf:robot_1:backup, 984e3bdf:robot_4:escort, 984e3bdf:robot_4:wait | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_2', 'robot_4'], ['robot_2', 'robot_5'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 11.4 rel-s
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 69.71, 'until_rel': 569.81}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 89.41, 'until_rel': 569.81}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 73.11, 'until_rel': 569.81}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 82.31, 'until_rel': 569.81}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 94.61, 'to_rel': 569.81, 'duration_s': 475.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.939}, {'robot': 'robot_2', 'from_rel': 24.01, 'to_rel': 569.81, 'duration_s': 545.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.945}, {'robot': 'robot_3', 'from_rel': 82.01, 'to_rel': 569.81, 'duration_s': 487.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.941}, {'robot': 'robot_4', 'from_rel': 89.31, 'to_rel': 569.81, 'duration_s': 480.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.94}, {'robot': 'robot_5', 'from_rel': 73.11, 'to_rel': 569.81, 'duration_s': 496.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.942}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|box:rack/NW_west: [67.51, 569.81] -0.0

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| -0.357 | safety_stop_span | robot_2 | to 2.093 (478 lines) |
| 9.42 | safety_stop_span | robot_4 | to 14.052 (1196 lines) |
| 9.438 | safety_stop_span | robot_1 | to 14.052 (1196 lines) |
| 11.21 | gt_submargin | robot_2|box:obstacle_1 | to 11.81 min gap 0.0478 m |
| 11.4 | analysis | 984e3bdf9d8642e584ed70b6e482ed5b | positive strategy=yield involved=['robot_1', 'robot_4'] yield=robot_1 |
| 11.4 | dispatched | 984e3bdf9d8642e584ed70b6e482ed5b | robot_1:yield, robot_4:temporary_wait |
| 13.834 | m4_leg_start | 984e3bdf:robot_1:backup | backup commanded=1.349 |
| 14.053 | exempt_change | - | robot_1+robot_4 |
| 15.81 | gt_submargin | robot_3|box:obstacle_2 | to 16.71 min gap 0.0396 m |
| 22.714 | safety_stop_span | robot_2 | to 66.498 (11622 lines) |
| 22.715 | safety_stop_span | robot_1 | to 61.49 (10250 lines) |
| 26.71 | gt_submargin | robot_5|box:obstacle_1 | to 28.11 min gap 0.0166 m |
| 29.638 | safety_stop_span | robot_5 | to 53.231 (6257 lines) |
| 29.639 | safety_stop_span | robot_4 | to 53.613 (6359 lines) |
| 48.278 | m4_terminal | 984e3bdf:robot_1:backup | FAILED  moved=0.901 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 51.567 | analysis | 652ac9ac585d465fbc4e99832517c4eb | positive strategy=reverse involved=['robot_4', 'robot_5'] yield=None |
| 51.567 | dispatched | 652ac9ac585d465fbc4e99832517c4eb | robot_5:reverse |
| 53.2 | m4_leg_start | 652ac9ac:robot_5:reverse | reverse commanded=1.3 |
| 53.233 | exempt_change | - | robot_1+robot_5,robot_2+robot_5 |
| 56.41 | gt_submargin | robot_5|box:obstacle_1 | to 62.61 min gap 0.0179 m |
| 58.469 | safety_stop_span | robot_4 | to 61.49 (795 lines) |
| 58.469 | safety_stop_span | robot_5 | to 62.067 (953 lines) |
| 59.733 | analysis | ea23b1a79f564a25a375dd7af8c32d93 | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 59.733 | dispatched | ea23b1a79f564a25a375dd7af8c32d93 | robot_1:reverse, robot_3:reverse, robot_4:reverse |
| 59.867 | m1_stale | robot_5 | STALE 1.3 s |
| 59.987 | safety_stop_span | robot_3 | to 61.489 (400 lines) |
| 61.234 | m4_leg_start | ea23b1a7:robot_1:reverse | reverse commanded=1.3 |
| 61.234 | m4_leg_start | ea23b1a7:robot_3:reverse | reverse commanded=1.3 |
| 61.234 | m4_leg_start | ea23b1a7:robot_4:reverse | reverse commanded=1.3 |
| 61.492 | exempt_change | - | robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_5,robot_3+robot_4 |
| 67.51 | gt_contact | robot_1|box:rack/NW_west | to 569.81 min gap -0.0 m |
| 67.658 | safety_stop_span | robot_2 | to 540.988 (126343 lines) |
| 67.659 | safety_stop_span | robot_1 | to 540.988 (126343 lines) |
| 69.422 | m4_terminal | 652ac9ac:robot_5:reverse | COMPLETED  moved=1.105 tags=['completed'] deadline=False |
| 69.438 | exempt_change | - | robot_1+robot_3,robot_1+robot_4,robot_3+robot_4 |
| 70.716 | safety_stop_span | robot_5 | to 540.988 (125523 lines) |
| 73.238 | m4_terminal | ea23b1a7:robot_3:reverse | COMPLETED  moved=1.068 tags=['completed'] deadline=False |
| 73.238 | m4_terminal | ea23b1a7:robot_4:reverse | COMPLETED  moved=1.061 tags=['completed'] deadline=False |
| 73.308 | exempt_change | - | robot_1+robot_3,robot_1+robot_4 |
| 80.777 | safety_stop_span | robot_3 | to 540.988 (122879 lines) |
| 88.233 | safety_stop_span | robot_4 | to 540.988 (120914 lines) |
| 94.556 | m4_terminal | ea23b1a7:robot_1:reverse | FAILED  moved=0.588 tags=['not_executed(<50%)', 'pinned_on_undeclared_box:rack/NW_west'] deadline=True |
| 99.4 | analysis | f2a4c4037a254500bd27bbf7f72c9953 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 99.4 | withheld | f2a4c4037a254500bd27bbf7f72c9953 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 23.867 | U:T1_fidelity / episode_gate_pass | 82/237 | 82/237 | 82/237 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.01} |
| ea23b1a79f564a25a375dd7af8c32d93 | 59.733 | pass / pass | 150/237 | 150/237 | 116/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |
| f2a4c4037a254500bd27bbf7f72c9953 | 99.4 | pass / pass | 113/237 | 113/237 | 75/237 | True | {'robot': 'robot_3', 'heading_deg': 315, 'distance_m': 0.01} |

## Decisions

### 984e3bdf9d8642e584ed70b6e482ed5b at 11.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4'], yield_robot robot_1, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 should yield by backing up or moving aside to allow Robot 4 to pass through.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_1->robot_4', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.736']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.349, 'crossing_order': ['robot_4'], 'passer_escort_distance_m': 1.736, 'passer_robot_id': 'robot_4', 'reason': 'Robot 1 and Robot 4 are in a head-on standoff in a narrow corridor.', 'retreat_choice': 'B'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_4'], 'G6_verbatim_contradicted': False}

### 652ac9ac585d465fbc4e99832517c4eb at 51.567 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}]
- Justification: Reversing robot_4 to the east will open up space for robot_5 to continue its delivery to the east, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4'], 'involved': ['robot_4', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to reverse toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_5->robot_4']
- Actions: [('robot_5', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_5->robot_4'], 'G6_verbatim_contradicted': False, 'G4_robots_dropped': ['robot_4']}

### ea23b1a79f564a25a375dd7af8c32d93 at 59.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_3'}]
- Justification: Robot 4 and robot 5 must continue reversing to resolve the head-on blocks and create space for robot 1, 2, and 3 to safely proceed or wait.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4', 'robot_5'], 'involved': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_4->robot_2', 'grounding=rear_exempt:robot_5', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_1', 'reverse', {'backup_distance_m': 1.3}), ('robot_3', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_4->robot_2', 'grounding=rear_exempt:robot_5'], 'G6_verbatim_contradicted': True, 'G4_robots_dropped': ['robot_2', 'robot_5']}

### f2a4c4037a254500bd27bbf7f72c9953 at 99.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_1', 'robot_5', 'robot_3', 'robot_2', 'robot_4'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}]
- Justification: A junction clear is proposed since the previous simple reverse failed. It will task robot_4 and robot_2 to reverse or yield, allowing robot_1 to cross first, followed by the others.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: yield infeasible: robot_2/robot_1 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 984e3bdf:robot_1:backup | backup | 1.349 | 11.4 | 13.834 | 48.278 | FAILED | 0.901 | 0.668 | 0.3146 (rack/NW_north) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| 984e3bdf:robot_4:escort | escort | 1.736 | 11.4 | None | None | None | None | None | None (None) | None (None) | escort_not_admitted (no gate_admit line) | False |
| 652ac9ac:robot_5:reverse | reverse | 1.3 | 51.567 | 53.2 | 69.422 | COMPLETED | 1.105 | 0.85 | 0.0179 (obstacle_1) | None (None) | completed | False |
| ea23b1a7:robot_1:reverse | reverse | 1.3 | 59.733 | 61.234 | 94.556 | FAILED | 0.588 | 0.452 | -0.0 (rack/NW_west) | None (None) | not_executed(<50%); pinned_on_undeclared_box:rack/NW_west | True |
| ea23b1a7:robot_3:reverse | reverse | 1.3 | 59.733 | 61.234 | 73.238 | COMPLETED | 1.068 | 0.822 | 0.307 (obstacle_1) | None (None) | completed | False |
| ea23b1a7:robot_4:reverse | reverse | 1.3 | 59.733 | 61.234 | 73.238 | COMPLETED | 1.061 | 0.816 | 0.215 (obstacle_1) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 14.053, 'pairs': 'robot_1+robot_4'}, {'rel': 48.281, 'pairs': '-'}, {'rel': 53.233, 'pairs': 'robot_1+robot_5,robot_2+robot_5'}, {'rel': 61.492, 'pairs': 'robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_5,robot_3+robot_4'}, {'rel': 69.438, 'pairs': 'robot_1+robot_3,robot_1+robot_4,robot_3+robot_4'}, {'rel': 73.308, 'pairs': 'robot_1+robot_3,robot_1+robot_4'}, {'rel': 94.583, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 3 spans; robot_17|min_distance_violation: 1 spans; robot_4|min_distance_violation: 4 spans; robot_1|min_distance_violation: 3 spans; robot_5|min_distance_violation: 3 spans; robot_3|min_distance_violation: 2 spans
