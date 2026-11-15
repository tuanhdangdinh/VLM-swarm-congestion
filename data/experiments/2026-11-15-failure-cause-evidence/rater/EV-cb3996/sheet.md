# Evidence Sheet EV-cb3996

- Censoring: t_end 576.703 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=12 max residual 0.02 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4, robot_5 | 31.603 | 576.703 | False | D1:robot_2:reverse, D1:robot_4:reverse | - |
| FU2 | conflict | robot_1, robot_3 | 37.803 | 576.703 | False | D1:robot_1:reverse, D1:robot_3:reverse | - |

### FU1

- Pairs: [['robot_2', 'robot_4'], ['robot_2', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.4 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 64.0, 'until_rel': 576.7}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 31.9, 'until_rel': 576.7}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 31.6, 'to_rel': 576.7, 'duration_s': 545.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_4', 'from_rel': 63.7, 'to_rel': 576.7, 'duration_s': 513.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.981}, {'robot': 'robot_5', 'from_rel': 31.6, 'to_rel': 576.7, 'duration_s': 545.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_4|box:rack/NW_west: [22.0, 54.4] -0.0

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 9.891 | safety_stop_span | robot_2 | to 15.238 (1038 lines) |
| 9.91 | safety_stop_span | robot_4 | to 15.239 (1038 lines) |
| 13.4 | analysis | D1 | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 13.4 | dispatched | D1 | robot_1:reverse, robot_2:reverse, robot_3:reverse, robot_4:reverse |
| 15.2 | m4_leg_start | D1:robot_2:reverse | reverse commanded=1.3 |
| 15.233 | m4_leg_start | D1:robot_4:reverse | reverse commanded=1.3 |
| 15.236 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4 |
| 15.244 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4 |
| 15.267 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4,robot_3+robot_4 |
| 22.0 | gt_contact | robot_4|box:rack/NW_west | to 54.4 min gap -0.0 m |
| 26.6 | gt_submargin | robot_5|box:obstacle_1 | to 28.8 min gap 0.0067 m |
| 29.62 | m4_terminal | D1:robot_2:reverse | COMPLETED  moved=1.286 tags=['completed'] deadline=False |
| 29.689 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_4,robot_3+robot_4 |
| 29.744 | exempt_change | - | robot_1+robot_4,robot_2+robot_4,robot_3+robot_4 |
| 29.9 | gt_submargin | robot_5|box:obstacle_1 | to 30.0 min gap 0.0499 m |
| 30.3 | gt_submargin | robot_5|box:obstacle_1 | to 30.4 min gap 0.0496 m |
| 32.239 | safety_stop_span | robot_2 | to 740.689 (138673 lines) |
| 32.253 | safety_stop_span | robot_5 | to 740.689 (138673 lines) |
| 33.433 | m1_stale | robot_5 | STALE 2.83 s |
| 60.453 | m4_terminal | D1:robot_4:reverse | FAILED  moved=0.647 tags=['not_executed(<50%)'] deadline=True |
| 66.233 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 66.233 | withheld | D4 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 73.223 | safety_stop_span | robot_4 | to 740.689 (130638 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 31.667 | episode_gate_pass / episode_gate_pass | 33/237 | 33/237 | 33/237 | True | {'robot': 'robot_2', 'heading_deg': 45, 'distance_m': 0.04} |
| D4 | 66.233 | pass / pass | 76/237 | 76/237 | 76/237 | True | {'robot': 'robot_4', 'heading_deg': 180, 'distance_m': 0.03} |

### FU2

- Pairs: [['robot_1', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 13.4 rel-s
- V1 input: {'a33_matched_positive_analyses': 2, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 38.0, 'until_rel': 576.7}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 38.0, 'to_rel': 576.7, 'duration_s': 538.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.995}, {'robot': 'robot_3', 'from_rel': 37.9, 'to_rel': 576.7, 'duration_s': 538.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.995}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 11.069 | safety_stop_span | robot_3 | to 15.235 (811 lines) |
| 11.083 | safety_stop_span | robot_1 | to 15.235 (811 lines) |
| 13.4 | analysis | D1 | positive strategy=reverse involved=['robot_1', 'robot_2', 'robot_3', 'robot_4'] yield=None |
| 13.4 | dispatched | D1 | robot_1:reverse, robot_2:reverse, robot_3:reverse, robot_4:reverse |
| 15.2 | m4_leg_start | D1:robot_1:reverse | reverse commanded=1.3 |
| 15.2 | m4_leg_start | D1:robot_3:reverse | reverse commanded=1.3 |
| 15.236 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4 |
| 15.244 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4 |
| 15.267 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4,robot_3+robot_4 |
| 29.628 | m4_terminal | D1:robot_3:reverse | COMPLETED  moved=1.285 tags=['completed'] deadline=False |
| 29.689 | exempt_change | - | robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_4,robot_3+robot_4 |
| 29.712 | m4_terminal | D1:robot_1:reverse | COMPLETED  moved=1.296 tags=['completed'] deadline=False |
| 29.744 | exempt_change | - | robot_1+robot_4,robot_2+robot_4,robot_3+robot_4 |
| 32.516 | nav2 | robot_3 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 40.684 | safety_stop_span | robot_3 | to 740.689 (137031 lines) |
| 40.686 | safety_stop_span | robot_1 | to 740.689 (137031 lines) |
| 57.233 | analysis | D2 | positive strategy=yield involved=['robot_1', 'robot_3'] yield=robot_1 |
| 57.233 | withheld | D2 | robot_1:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 61.733 | analysis | D3 | positive strategy=yield involved=['robot_1', 'robot_3'] yield=robot_1 |
| 61.733 | withheld | D3 | robot_1:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 66.233 | analysis | D4 | positive strategy=junction_clear involved=['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 66.233 | withheld | D4 | robot_1:temporary_wait, robot_2:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 37.933 | episode_gate_pass / episode_gate_pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 180, 'distance_m': 0.06} |
| D2 | 57.233 | pass / pass | 8/88 | 8/88 | 6/88 | True | {'robot': 'robot_1', 'heading_deg': 180, 'distance_m': 0.06} |
| D3 | 61.733 | pass / pass | 6/88 | 6/88 | 6/88 | True | {'robot': 'robot_1', 'heading_deg': 180, 'distance_m': 0.06} |

## Decisions

### D1 at 13.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'reverse', 'robot_id': 'robot_2'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since both robot pairs (1-3 and 2-4) are locked head-on in narrow corridors, they must reverse to clear sufficient space to allow rerouting or safe passing.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_1', 'robot_2', 'robot_3', 'robot_4'], 'involved': ['robot_1', 'robot_2', 'robot_3', 'robot_4']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:ambiguous']
- Actions: [('robot_1', 'reverse', {'backup_distance_m': 1.3}), ('robot_2', 'reverse', {'backup_distance_m': 1.3}), ('robot_3', 'reverse', {'backup_distance_m': 1.3}), ('robot_4', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 57.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3'], yield_robot robot_1, crossing_order ['robot_3', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 will yield and back up, allowing robot 3 to proceed first and clear the narrow passageway.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_3']}, yield refusal yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured', 'grounding=dynamic_arms:ambiguous_refused:robot_1:40', 'grounding=dynamic_arms:ambiguous_refused:robot_3:36']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 61.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3'], yield_robot robot_1, crossing_order ['robot_3', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 and Robot 3 are head-on and very close (0.40 m); having Robot 1 yield will allow Robot 3 to pass and clear the lane.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_3']}, yield refusal yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured', 'grounding=dynamic_arms:ambiguous_refused:robot_1:40', 'grounding=dynamic_arms:ambiguous_refused:robot_3:36']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: ambiguous lane: robot_1 heads 40 deg and robot_3 heads 36 deg off both axes (beyond the 30 deg snap); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 66.233 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_3', 'robot_4', 'robot_5', 'robot_1', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_5'}]
- Justification: Robot 1 and Robot 3 are in a head-on conflict, as are Robot 2 and Robot 4. A multi-robot junction clear strategy will allow the conflicting pairs to back up or yield to resolve the blockages.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_2', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_2', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_2 0.00 m, robot_3 0.00 m, robot_4 0.00 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_1:reverse | reverse | 1.3 | 13.4 | 15.2 | 29.712 | COMPLETED | 1.296 | 0.997 | 0.0763 (obstacle_2) | None (None) | completed | False |
| D1:robot_2:reverse | reverse | 1.3 | 13.4 | 15.2 | 29.62 | COMPLETED | 1.286 | 0.989 | 0.2761 (obstacle_1) | None (None) | completed | False |
| D1:robot_3:reverse | reverse | 1.3 | 13.4 | 15.2 | 29.628 | COMPLETED | 1.285 | 0.989 | 0.2707 (rack/SE_east) | None (None) | completed | False |
| D1:robot_4:reverse | reverse | 1.3 | 13.4 | 15.233 | 60.453 | FAILED | 0.647 | 0.497 | -0.0 (rack/NW_west) | None (None) | not_executed(<50%) | True |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_3 32.516 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 15.236, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4'}, {'rel': 15.244, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4'}, {'rel': 15.267, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_3,robot_2+robot_4,robot_3+robot_4'}, {'rel': 29.689, 'pairs': 'robot_1+robot_2,robot_1+robot_3,robot_1+robot_4,robot_2+robot_4,robot_3+robot_4'}, {'rel': 29.744, 'pairs': 'robot_1+robot_4,robot_2+robot_4,robot_3+robot_4'}, {'rel': 60.47, 'pairs': '-'}]
- Safety-stop spans: robot_2|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_3|min_distance_violation: 2 spans; robot_1|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans
