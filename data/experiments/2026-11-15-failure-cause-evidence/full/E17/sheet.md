# Evidence Sheet E17

- Censoring: t_end 269.007 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=63 max residual 1.862 s
- Outcome fields (frozen, copied): {"censor_reason": "stop_flag", "source": "[O] batch5/agg_b5.json gridlock.tasks_completed, gridlock.gt_end_rel_s; censor [P] batch6/s1_scoring_pilots.jsonl", "t_end_rel": 269.0, "tasks_completed": 9, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_5 | 245.307 | 269.007 | False | 6d37a549:robot_1:backup | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 218.167 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 245.71, 'until_rel': 269.01}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 268.71, 'until_rel': 269.01}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 72.21, 'to_rel': 135.71, 'duration_s': 63.5, 'to_censor': False, 'safety_stop_cover_fraction': 0.0}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|box:obstacle_1: [54.01, 136.01] -0.0002; robot_2|box:obstacle_2: [184.01, 215.41] -0.0001

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 186.226 | nav2 | robot_1 | Failed to make progress |
| 186.226 | nav2 | robot_1 | [follow_path] [ActionServer] Aborting handle. |
| 189.196 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_5,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5 |
| 189.313 | m4_terminal | 9cf93ebe:robot_5:reverse | COMPLETED  moved=1.046 tags=['completed'] deadline=False |
| 189.331 | exempt_change | - | robot_1+robot_2,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5 |
| 191.0 | m1_stale | robot_5 | STALE 3.03 s |
| 192.221 | safety_stop_span | robot_1 | to 218.064 (6555 lines) |
| 205.61 | gt_submargin | robot_2|robot_5 | to 206.71 min gap 0.0219 m |
| 212.995 | m4_terminal | 9cf93ebe:robot_2:reverse | FAILED  moved=0.62 tags=['not_executed(<50%)', 'pinned_on_declared_box:obstacle_2'] deadline=True |
| 218.067 | exempt_change | - | robot_1+robot_3,robot_1+robot_4 |
| 218.167 | analysis | 6d37a549469c4d6680c06100b7bd91a8 | positive strategy=yield involved=['robot_1', 'robot_4', 'robot_3'] yield=robot_4 |
| 218.167 | dispatched | 6d37a549469c4d6680c06100b7bd91a8 | robot_1:yield, robot_3:temporary_wait, robot_4:temporary_wait |
| 219.634 | m4_leg_start | 6d37a549:robot_1:backup | backup commanded=1.308 |
| 238.691 | safety_stop_span | robot_1 | to 273.081 (8462 lines) |
| 238.693 | safety_stop_span | robot_2 | to 273.081 (8462 lines) |
| 242.91 | gt_submargin | robot_2|box:obstacle_2 | to 245.01 min gap 0.014 m |
| 246.71 | gt_submargin | robot_5|box:obstacle_1 | to 248.61 min gap 0.0175 m |
| 256.036 | m4_terminal | 6d37a549:robot_1:backup | FAILED  moved=1.365 tags=['stalled_clear(no robot or box within 0.05 m)'] deadline=True |
| 261.815 | safety_stop_span | robot_5 | to 273.081 (2555 lines) |
| 266.333 | analysis | 599619fb11cb4ceab20243cb9d9022fc | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_5'] yield=None |
| 266.333 | withheld | 599619fb11cb4ceab20243cb9d9022fc | robot_1:temporary_wait, robot_2:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 245.467 | episode_gate_pass / episode_gate_pass | 75/237 | 75/237 | 75/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| 599619fb11cb4ceab20243cb9d9022fc | 266.333 | pass / pass | 74/237 | 74/237 | 71/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### 023ae8e783e349d6abba9dc3ee67a2cc at 17.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Both robots need to back up slightly to resolve the dead-end head-on standoff, or robot_5 must reverse and yield to let robot_2 proceed.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_5'], 'involved': ['robot_2', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: reverse infeasible: robot_2/robot_5 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_2: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### ce33c3db74014420ac25eafe2e026f22 at 29.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Both robots are facing each other in close proximity and are stopped, representing a clear head-on deadlock. Reversing both will clear the immediate collision risk and allow them to replan.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_5'], 'involved': ['robot_2', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_2: reverse infeasible: robot_2/robot_5 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_2']}, {'op': 'substitute', 'reason': "robot_5: reverse infeasible: robot_2/robot_5 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 1964feb1381a400e84d2b3d1d7b8075a at 42.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_5'], yield_robot robot_5, crossing_order ['robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having robot_5 yield by backing up or stepping aside allows robot_2 to proceed to its nearby goal, after which robot_5 can resume its path.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_5', 'robot_2']}, yield refusal yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_5,robot_2:51']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_2 both run along x but sit 51 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### fc52c0ed841a4faf90446209c3a5bf0c at 47.033 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_5', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Both robot pairs are stuck in close-quarters head-on deadlocks. Forcing robot_2 and robot_4 to reverse will create the necessary clearance to resolve the standoff.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_4'], 'involved': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_2/robot_5 both outside the corridor on the same side; a reverse would traverse it; swapped roles robot_2 (reverse) <-> robot_3 (wait)', 'robot_ids': ['robot_2', 'robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=node_handoff:robot_3->robot_4', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_4'], 'G6_verbatim_contradicted': False, 'G4_robots_dropped': ['robot_4']}

### 0f26edcc7b4c40d9b5a4ed51ef0d202d at 59.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_3', 'robot_4', 'robot_5', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Both pairs robot_3/robot_4 and robot_2/robot_5 are facing each other within conflicting distances, requiring coordinated reverse and wait actions to clear.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### c694543bb3c840198083af63da1996e3 at 65.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2', 'robot_5'], type deadlock
- Plan legs (model): None
- Justification: A junction clear is necessary to orchestrate coordinated reverses for the conflicting pairs to safely resolve both head-on situations.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 150b95a61e46411f9c295f770c006aa9 at 70.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_5'}]
- Justification: Robot 4 and Robot 3 are blocking each other's path directly, and robot 4 needs to reverse to allow robot 3 to proceed to its goal.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_4'], 'involved': ['robot_3', 'robot_4']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to reverse toward M3's derived plan", 'robot_ids': ['robot_3']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_3->robot_4']
- Actions: [('robot_3', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_4'], 'G6_verbatim_contradicted': False, 'G4_robots_dropped': ['robot_4']}

### 6745a1362818416281da9aafbc3c1968 at 108.8 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot robot_4, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Robot 4 and Robot 5 should yield to allow Robot 3 and Robot 2 respectively to proceed or bypass them, resolving the standoffs.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': True, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4', 'robot_5'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan inconsistent: strategy 'yield' is not refined by actions ['yield', 'yield', 'cross', 'cross', 'continue'], held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded yield re-grounded: robot_4 has no retreat candidate surviving the sweep; robot_3 has an executable retreat, from robot_4
- Degradation tags: ['order=implicit', 'order=lane_scoped:robot_2,robot_5', 'yield_robot=sweep_regrounded:robot_4->robot_3', 'retreat=default:no_choice', 'grounding=dynamic_arms:lane:y', 'grounding=escort_turn_cap:robot_4:2.35->2.339']
- Actions: [('robot_3', 'yield', {'backup_distance_m': 1.276, 'crossing_order': ['robot_4'], 'passer_escort_distance_m': 2.339, 'passer_robot_id': 'robot_4', 'reason': 'Two separate head-on deadlocks exist: robot_3 and robot_4 on the left, and robot_2 and robot_5 on the right.', 'retreat_choice': 'A'}), ('robot_4', 'temporary_wait', {}), ('robot_2', 'temporary_wait', {'reason': "outside the yield's lane conflict"}), ('robot_5', 'temporary_wait', {'reason': "outside the yield's lane conflict"})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['yield_robot=sweep_regrounded:robot_4->robot_3', 'yield_robot_grounded_from=robot_4'], 'G6_verbatim_contradicted': False}

### 5dfe6dad65344fee9f5354e1452d709a at 150.133 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations ['proposed_plan=default:invalid_structure'], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): None
- Justification: Both robots are stopped within 0.28m facing each other, so reversing robot_5 is necessary to clear the narrow aisle and resolve the deadlock.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_5', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': True, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 68ddd1d7ad5b41d7a23fd4b6a0f42386 at 162.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_2', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Robot 3 and Robot 4 on the left, as well as Robot 2 and Robot 5 on the right, are in close proximity (less than 0.5m) and facing each other, necessitating a coordinated reverse and clear to resolve the mutual blocks.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 21ce6358b83d4d7c9bd374cf51f90185 at 168.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_5', 'robot_3', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Using a junction clearance strategy allows the conflicting robots to systematically back away or yield, clearing the deadlocks on both sides of the environment.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_2 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 9cf93ebe0149404392cd8b264710c25c at 176.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'wait', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}]
- Justification: Robot 2 and Robot 3 need to reverse to resolve the localized deadlocks with their respective counterparts.
- Contract C1-C3: {'plan_present': True, 'C1': True, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_2', 'robot_3'], 'involved': ['robot_2', 'robot_3', 'robot_4', 'robot_5']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held True, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:ambiguous']
- Actions: [('robot_2', 'reverse', {'backup_distance_m': 1.3}), ('robot_3', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3}), ('robot_5', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### 6d37a549469c4d6680c06100b7bd91a8 at 218.167 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_4', 'robot_3'], yield_robot robot_4, crossing_order ['robot_1', 'robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 will yield and step aside, allowing robot_1 and robot_3 to proceed first to resolve the local corridor deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_4 is off the dynamic lane robot_1/robot_3; swapped roles robot_4 (yield) <-> robot_1 (cross)', 'robot_ids': ['robot_1', 'robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=node_handoff:robot_1->robot_3', 'grounding=node_handoff_regrounded:robot_4->robot_1', 'grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_4:2.35->1.282']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.308, 'crossing_order': ['robot_3', 'robot_4'], 'passer_escort_distance_m': 3.056, 'passer_robot_id': 'robot_3', 'reason': 'robot_1 and robot_4 are in a head-on deadlock within 0.40 meters of each other.', 'retreat_choice': 'A'}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_1->robot_3', 'grounding=node_handoff_regrounded:robot_4->robot_1'], 'G6_verbatim_contradicted': False}

### 599619fb11cb4ceab20243cb9d9022fc at 266.333 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_1', 'robot_2'], type crowding
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Using junction_clear forces Robot 1 and 2 to reverse, allowing Robot 5 to cross and clear the narrow corridor first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.15 m, robot_2 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 150b95a6:robot_3:reverse | reverse | 1.3 | 70.733 | 72.2 | 107.366 | FAILED | 0.456 | 0.351 | 0.368 (obstacle_1) | None (None) | not_executed(<50%); stalled_clear(no robot or box within 0.05 m) | True |
| 6745a136:robot_3:backup | backup | 1.276 | 108.8 | 110.834 | 146.524 | FAILED | 1.238 | 0.97 | -0.0015 (obstacle_1) | None (None) | pinned_on_declared_box:obstacle_1 | True |
| 6745a136:robot_4:escort | escort | 2.339 | 108.8 | None | None | None | None | None | None (None) | None (None) | escort_not_admitted (no gate_admit line) | False |
| 9cf93ebe:robot_2:reverse | reverse | 1.3 | 176.4 | 177.734 | 212.995 | FAILED | 0.62 | 0.477 | -0.0001 (obstacle_2) | 0.0219 (robot_5) | not_executed(<50%); pinned_on_declared_box:obstacle_2 | True |
| 9cf93ebe:robot_3:reverse | reverse | 1.3 | 176.4 | 177.734 | 189.278 | COMPLETED | 1.043 | 0.802 | 0.0607 (obstacle_1) | None (None) | completed | False |
| 9cf93ebe:robot_4:reverse | reverse | 1.3 | 176.4 | 177.734 | 189.192 | COMPLETED | 1.037 | 0.798 | 0.3846 (rack/NW_north) | None (None) | completed | False |
| 9cf93ebe:robot_5:reverse | reverse | 1.3 | 176.4 | 177.734 | 189.313 | COMPLETED | 1.046 | 0.805 | 0.3116 (rack/SE_east) | None (None) | completed | False |
| 6d37a549:robot_1:backup | backup | 1.308 | 218.167 | 219.634 | 256.036 | FAILED | 1.365 | 1.043 | 0.2719 (rack/NW_north) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| 6d37a549:robot_3:escort | escort | 3.056 | 218.167 | None | None | None | None | None | None (None) | None (None) | escort_not_admitted (no gate_admit line) | False |

## Perception STALE Spans of 10 s or More

{"robot_1": [{"from_rel": 65.833, "to_rel": 66.033, "duration_s": 0.2, "ge_10s": false}, {"from_rel": 68.2, "to_rel": 68.667, "duration_s": 0.47, "ge_10s": false}, {"from_rel": 73.667, "to_rel": 114.433, "duration_s": 40.77, "ge_10s": true}, {"from_rel": 115.6, "to_rel": 132.5, "duration_s": 16.9, "ge_10s": true}, {"from_rel": 159.867, "to_rel": 160.533, "duration_s": 0.67, "ge_10s": false}, {"from_rel": 168.333, "to_rel": 169.067, "duration_s": 0.73, "ge_10s": false}, {"from_rel": 171.367, "to_rel": 172.467, "duration_s": 1.1, "ge_10s": false}, {"from_rel": 173.567, "to_rel": 174.433, "duration_s": 0.87, "ge_10s": false}, {"from_rel": 177.8, "to_rel": 181.933, "duration_s": 4.13, "ge_10s": false}, {"from_rel": 183.167, "to_rel": 187.967, "duration_s": 4.8, "ge_10s": false}]}

## Nav2 Abort Lines

- robot_1 72.408 rel-s: Failed to make progress
- robot_1 72.408 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_1 93.374 rel-s: Failed to make progress
- robot_1 93.374 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_1 113.658 rel-s: Failed to make progress
- robot_1 113.658 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_1 132.307 rel-s: Failed to make progress
- robot_1 132.307 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_1 168.257 rel-s: Failed to make progress
- robot_1 168.257 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_1 186.226 rel-s: Failed to make progress
- robot_1 186.226 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 256.778 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 72.742, 'pairs': 'robot_1+robot_3'}, {'rel': 107.557, 'pairs': '-'}, {'rel': 112.565, 'pairs': 'robot_2+robot_3,robot_3+robot_4,robot_3+robot_5'}, {'rel': 146.573, 'pairs': '-'}, {'rel': 178.401, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5'}, {'rel': 178.45, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_1+robot_5,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5'}, {'rel': 189.196, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_5,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5'}, {'rel': 189.331, 'pairs': 'robot_1+robot_2,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5'}, {'rel': 213.24, 'pairs': '-'}, {'rel': 218.067, 'pairs': 'robot_1+robot_3,robot_1+robot_4'}, {'rel': 256.079, 'pairs': '-'}]
- Safety-stop spans: robot_5|min_distance_violation: 2 spans; robot_2|min_distance_violation: 2 spans; robot_4|min_distance_violation: 4 spans; robot_3|min_distance_violation: 3 spans; robot_1|stale_pose_unsafe: 1 spans; robot_1|min_distance_violation: 3 spans
