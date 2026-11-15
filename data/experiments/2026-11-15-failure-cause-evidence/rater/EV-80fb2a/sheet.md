# Evidence Sheet EV-80fb2a

- Censoring: t_end 577.437 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=21 max residual 1.755 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4 | 148.937 | 577.437 | False | - | - |
| FU2 | conflict | robot_1, robot_3, robot_5 | 162.237 | 577.437 | False | D4:robot_3:reverse, D4:robot_5:reverse | - |

### FU1

- Pairs: [['robot_2', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 149.24, 'until_rel': 577.44}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 151.94, 'to_rel': 577.44, 'duration_s': 425.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 149.04, 'to_rel': 577.44, 'duration_s': 428.4, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 109.479 | m4_terminal | D2:robot_2:backup | COMPLETED  moved=1.385 tags=['completed'] deadline=False |
| 109.519 | m4_terminal | D2:robot_4:escort | COMPLETED escort complete: moved 2.354 m moved=2.342 tags=['completed'] deadline=False |
| 111.167 | m1_stale | robot_2 | STALE 0.37 s |
| 115.34 | gt_submargin | robot_2|box:obstacle_1 | to 116.94 min gap 0.035 m |
| 136.022 | exempt_change | - | robot_1+robot_3,robot_1+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5 |
| 143.24 | gt_submargin | robot_4|box:obstacle_2 | to 144.54 min gap 0.0208 m |
| 148.153 | safety_stop_span | robot_2 | to 591.101 (109456 lines) |
| 148.154 | safety_stop_span | robot_4 | to 591.102 (109456 lines) |
| 149.264 | exempt_change | - | robot_1+robot_3,robot_3+robot_4,robot_3+robot_5 |
| 233.533 | m1_stale | robot_4 | STALE 0.47 s |
| 271.5 | m1_stale | robot_4 | STALE 0.13 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 149.067 | episode_gate_pass / episode_gate_pass | 30/88 | 30/88 | 30/88 | True | {'robot': 'robot_2', 'heading_deg': 135, 'distance_m': 0.04} |

### FU2

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 133.667 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 173.54, 'until_rel': 577.44}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 166.34, 'until_rel': 577.44}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 48.64, 'to_rel': 137.34, 'duration_s': 88.7, 'to_censor': False, 'safety_stop_cover_fraction': 0.985}, {'robot': 'robot_1', 'from_rel': 166.04, 'to_rel': 577.44, 'duration_s': 411.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}, {'robot': 'robot_3', 'from_rel': 61.54, 'to_rel': 135.44, 'duration_s': 73.9, 'to_censor': False, 'safety_stop_cover_fraction': 0.991}, {'robot': 'robot_3', 'from_rel': 173.14, 'to_rel': 577.44, 'duration_s': 404.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.998}, {'robot': 'robot_5', 'from_rel': 25.94, 'to_rel': 135.44, 'duration_s': 109.5, 'to_censor': False, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 166.04, 'to_rel': 577.44, 'duration_s': 411.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.999}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_3|box:rack/SW_west: [20.84, 49.84] -0.0; robot_3|box:rack/SW_south: [143.54, 577.44] -0.0015

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 111.0 | analysis | D3 | positive strategy=junction_clear involved=['robot_1', 'robot_3', 'robot_5'] yield=None |
| 111.0 | withheld | D3 | robot_1:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |
| 133.667 | analysis | D4 | positive strategy=reverse involved=['robot_1', 'robot_3', 'robot_5'] yield=None |
| 133.667 | dispatched | D4 | robot_3:reverse, robot_5:reverse |
| 135.4 | m4_leg_start | D4:robot_3:reverse | reverse commanded=1.3 |
| 135.4 | m4_leg_start | D4:robot_5:reverse | reverse commanded=1.3 |
| 136.022 | exempt_change | - | robot_1+robot_3,robot_1+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5 |
| 143.54 | gt_contact | robot_3|box:rack/SW_south | to 577.44 min gap -0.0015 m |
| 149.252 | m4_terminal | D4:robot_5:reverse | COMPLETED  moved=1.222 tags=['completed'] deadline=False |
| 149.264 | exempt_change | - | robot_1+robot_3,robot_3+robot_4,robot_3+robot_5 |
| 166.605 | safety_stop_span | robot_5 | to 591.102 (104927 lines) |
| 166.606 | safety_stop_span | robot_1 | to 591.101 (104927 lines) |
| 171.656 | m4_terminal | D4:robot_3:reverse | FAILED  moved=1.01 tags=['pinned_on_undeclared_box:rack/SW_south'] deadline=True |
| 172.986 | nav2 | robot_3 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 173.784 | safety_stop_span | robot_3 | to 591.101 (103139 lines) |
| 174.667 | analysis | D5 | positive strategy=yield involved=['robot_1', 'robot_3', 'robot_5'] yield=robot_1 |
| 174.667 | withheld | D5 | robot_1:temporary_wait, robot_3:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 162.4 | episode_gate_pass / episode_gate_pass | 70/237 | 70/237 | 70/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| D5 | 174.667 | pass / pass | 9/237 | 9/237 | 9/237 | True | {'robot': 'robot_5', 'heading_deg': 45, 'distance_m': 0.11} |

## Decisions

### D1 at 11.367 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_3'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_1'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since both robot 1 and robot 3 are stopped head-on, having them reverse to clear the conflict is the safest and most effective way to resolve the standoff.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_1', 'robot_3'], 'involved': ['robot_1', 'robot_3']}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x']
- Actions: [('robot_1', 'reverse', {'backup_distance_m': 1.3}), ('robot_3', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 52.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_4'], yield_robot robot_4, crossing_order ['robot_2', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 is closer to the corner/intersection space and should yield to let Robot 2 continue to its destination.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: robot_4 has 0.68 m retreat room < 0.74 m required; swapped roles robot_4 (yield) <-> robot_2 (cross)', 'robot_ids': ['robot_2', 'robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=default:no_choice', 'grounding=node_handoff:robot_2->robot_4', 'grounding=node_handoff_regrounded:robot_4->robot_2', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.314, 'crossing_order': ['robot_4'], 'passer_escort_distance_m': 2.35, 'passer_robot_id': 'robot_4', 'reason': "Robot 2 and Robot 4 are in a direct head-on deadlock blocking each other's path in the top-left corridor.", 'retreat_choice': 'A'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_2->robot_4', 'grounding=node_handoff_regrounded:robot_4->robot_2'], 'G6_verbatim_contradicted': False}

### D3 at 111.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_3', 'robot_5'], yield_robot None, crossing_order ['robot_5', 'robot_1', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: A junction clearing maneuver is required where robot_3 and robot_1 back out (reverse/yield) to allow robot_5 and robot_1 to resolve their positions.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_1: yield infeasible: robot_1 has 0.00 m retreat room < 0.77 m required; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}], rejection None, held False, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_3', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.00 m, robot_5 0.00 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 133.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_1', 'robot_3', 'robot_5'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): None
- Justification: Robot 3 needs to reverse to clear the narrow passage, while Robot 1 and Robot 5 wait for the space to be cleared.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_3->robot_1', 'grounding=dynamic_arms:lane:x']
- Actions: [('robot_3', 'reverse', {'backup_distance_m': 1.3}), ('robot_5', 'reverse', {'backup_distance_m': 1.3})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_3->robot_1'], 'G6_verbatim_contradicted': False, 'G4_robots_dropped': ['robot_1']}

### D5 at 174.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3', 'robot_5'], yield_robot robot_1, crossing_order ['robot_5', 'robot_1', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 1 will yield and move aside, allowing robot_5 to pass, which will then resolve the congestion for robot_3 as well.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_3', 'robot_5']}, yield refusal yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_1,robot_5:47']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_5 both run along x but sit 47 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_1:reverse | reverse | 1.3 | 11.367 | 12.734 | 48.541 | FAILED | 1.175 | 0.904 | 0.435 (rack/SW_south) | None (None) | stalled_clear(no robot or box within 0.05 m) | True |
| D1:robot_3:reverse | reverse | 1.3 | 11.367 | 12.734 | 48.566 | FAILED | 0.784 | 0.603 | -0.0 (rack/SW_west) | None (None) | pinned_on_undeclared_box:rack/SW_west | True |
| D2:robot_2:backup | backup | 1.314 | 52.467 | 56.267 | 109.479 | COMPLETED | 1.385 | 1.054 | 0.2598 (obstacle_1) | None (None) | completed | False |
| D2:robot_4:escort | escort | 2.35 | 52.467 | 84.834 | 109.519 | COMPLETED | 2.342 | 0.997 | 0.3402 (obstacle_1) | None (None) | completed | False |
| D4:robot_3:reverse | reverse | 1.3 | 133.667 | 135.4 | 171.656 | FAILED | 1.01 | 0.777 | -0.0015 (rack/SW_south) | None (None) | pinned_on_undeclared_box:rack/SW_south | True |
| D4:robot_5:reverse | reverse | 1.3 | 133.667 | 135.4 | 149.252 | COMPLETED | 1.222 | 0.94 | 0.0827 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_3 172.986 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 12.766, 'pairs': 'robot_1+robot_3'}, {'rel': 48.573, 'pairs': '-'}, {'rel': 56.588, 'pairs': 'robot_2+robot_4'}, {'rel': 109.49, 'pairs': '-'}, {'rel': 136.022, 'pairs': 'robot_1+robot_3,robot_1+robot_5,robot_3+robot_4,robot_3+robot_5,robot_4+robot_5'}, {'rel': 149.264, 'pairs': 'robot_1+robot_3,robot_3+robot_4,robot_3+robot_5'}, {'rel': 171.741, 'pairs': '-'}]
- Safety-stop spans: robot_1|min_distance_violation: 3 spans; robot_3|min_distance_violation: 3 spans; robot_2|min_distance_violation: 2 spans; robot_4|min_distance_violation: 2 spans; robot_5|min_distance_violation: 2 spans
