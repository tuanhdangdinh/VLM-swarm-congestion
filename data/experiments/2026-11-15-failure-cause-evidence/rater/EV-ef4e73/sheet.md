# Evidence Sheet EV-ef4e73

- Censoring: t_end 570.907 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=53 max residual 4.934 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4, robot_5 | 184.407 | 570.907 | False | - | - |
| FU2 | conflict | robot_1, robot_3 | 219.007 | 570.907 | False | D5:robot_1:backup, D5:robot_3:escort, D5:robot_3:wait | - |

### FU1

- Pairs: [['robot_2', 'robot_5'], ['robot_4', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 184.61, 'until_rel': 570.91}, {'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 195.11, 'until_rel': 570.91}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 217.21, 'to_rel': 570.91, 'duration_s': 353.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_4', 'from_rel': 217.21, 'to_rel': 570.91, 'duration_s': 353.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 217.21, 'to_rel': 570.91, 'duration_s': 353.7, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 124.667 | m1_stale | robot_2 | STALE 3.93 s |
| 125.867 | m1_stale | robot_4 | STALE 10.73 s |
| 137.7 | m1_stale | robot_4 | STALE 7.63 s |
| 146.5 | m1_stale | robot_4 | STALE 6.13 s |
| 153.767 | m1_stale | robot_4 | STALE 1.4 s |
| 156.467 | m1_stale | robot_4 | STALE 0.7 s |
| 158.267 | m1_stale | robot_4 | STALE 9.5 s |
| 164.0 | m4_terminal | D4:robot_2:backup | COMPLETED  moved=1.35 tags=['completed'] deadline=False |
| 169.067 | m1_stale | robot_4 | STALE 0.03 s |
| 182.51 | safety_stop_span | robot_5 | to 672.71 (106121 lines) |
| 182.511 | safety_stop_span | robot_2 | to 672.71 (106121 lines) |
| 194.78 | safety_stop_span | robot_4 | to 672.71 (103435 lines) |
| 206.2 | analysis | D6 | positive strategy=temporary_wait involved=['robot_2', 'robot_4', 'robot_5'] yield=None |
| 206.2 | dispatched | D6 | robot_2:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 184.467 | U:T1_fidelity / U:T1_fidelity | 47/237 | 47/237 | 47/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |
| D6 | 206.2 | pass / pass | 54/237 | 54/237 | 8/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |

### FU2

- Pairs: [['robot_1', 'robot_3']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- Chain start (earliest qualifying dispatch): 171.7 rel-s
- V1 input: {'a33_matched_positive_analyses': 1, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 223.01, 'until_rel': 570.91}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 235.61, 'to_rel': 570.91, 'duration_s': 335.3, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_3', 'from_rel': 235.71, 'to_rel': 570.91, 'duration_s': 335.2, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|robot_3: [222.31, 570.91] -0.0003

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 171.7 | analysis | D5 | positive strategy=yield involved=['robot_1', 'robot_3'] yield=robot_1 |
| 171.7 | dispatched | D5 | robot_1:yield, robot_3:temporary_wait |
| 173.251 | exempt_change | - | robot_1+robot_3 |
| 175.6 | m4_leg_start | D5:robot_1:backup | backup commanded=1.373 |
| 204.634 | m4_leg_start | D5:robot_3:escort | escort commanded=1.843 |
| 205.7 | m1_stale | robot_1 | STALE 1.33 s |
| 222.31 | gt_contact | robot_1|robot_3 | to 570.91 min gap -0.0003 m |
| 231.667 | m1_stale | robot_1 | STALE 339.1 s |
| 231.667 | m1_stale | robot_3 | STALE 339.1 s |
| 235.587 | m4_terminal | D5:robot_1:backup | COMPLETED  moved=1.582 tags=['completed'] deadline=False |
| 235.631 | safety_stop_span | robot_3 | to 672.71 (94400 lines) |
| 235.635 | m4_terminal | D5:robot_3:escort | COMPLETED escort complete: moved 1.843 m moved=1.845 tags=['completed'] deadline=False |
| 235.636 | safety_stop_span | robot_1 | to 672.71 (94400 lines) |
| 236.767 | analysis | D7 | positive strategy=yield involved=['robot_1', 'robot_3'] yield=robot_1 |
| 236.767 | withheld | D7 | robot_1:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 261.69 | nav2 | robot_3 | Failed to make progress |
| 261.691 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 287.167 | nav2 | robot_3 | Failed to make progress |
| 287.167 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 312.672 | nav2 | robot_3 | Failed to make progress |
| 312.672 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 337.488 | nav2 | robot_3 | Failed to make progress |
| 337.489 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 349.763 | nav2 | robot_3 | [spin] [ActionServer] Aborting handle. |
| 380.512 | nav2 | robot_3 | Failed to make progress |
| 380.512 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 405.825 | nav2 | robot_3 | Failed to make progress |
| 405.825 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 418.036 | nav2 | robot_3 | [backup] [ActionServer] Aborting handle. |
| 443.299 | nav2 | robot_3 | Failed to make progress |
| 443.299 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 468.772 | nav2 | robot_3 | Failed to make progress |
| 468.772 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 480.612 | nav2 | robot_3 | [spin] [ActionServer] Aborting handle. |
| 512.46 | nav2 | robot_3 | Failed to make progress |
| 512.461 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 537.209 | nav2 | robot_3 | Failed to make progress |
| 537.209 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 549.276 | nav2 | robot_3 | [backup] [ActionServer] Aborting handle. |
| 575.545 | nav2 | robot_3 | Failed to make progress |
| 575.545 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 601.375 | nav2 | robot_3 | Failed to make progress |
| 601.375 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |
| 613.215 | nav2 | robot_3 | [spin] [ActionServer] Aborting handle. |
| 645.312 | nav2 | robot_3 | Failed to make progress |
| 645.312 | nav2 | robot_3 | [follow_path] [ActionServer] Aborting handle. |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 219.367 | U:T1_fidelity / U:T1_fidelity | 26/88 | 26/88 | 26/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.04} |
| D7 | 236.767 | pass / pass | 3/88 | 3/88 | 3/88 | False | None |

## Decisions

### D1 at 12.933 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_2', 'robot_4'], yield_robot robot_4, crossing_order ['robot_2', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since Robot 2 and Robot 4 are in a head-on standoff within 0.28 meters, Robot 4 (which is already stopped) should yield and back up or step aside, allowing Robot 2 to proceed.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x', 'grounding=retreat_shield:robot_5']
- Actions: [('robot_4', 'yield', {'backup_distance_m': 1.437, 'crossing_order': ['robot_2'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 2.35, 'passer_robot_id': 'robot_2', 'reason': 'Robot 2 and Robot 4 are in a head-on conflict in a narrow passage.', 'retreat_choice': 'B'}), ('robot_2', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_4's retreat"})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': True}

### D2 at 75.333 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The robots have moved apart, and there is no active deadlock, bottleneck, or crowding detected.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 79.8 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy priority_override, involved ['robot_1', 'robot_2'], yield_robot None, crossing_order ['robot_2', 'robot_1'], type deadlock
- Plan legs (model): None
- Justification: The active plan is still in progress with Robot 2 currently crossing past Robot 1; we hold the existing plan.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['strategy=unsupported:priority_override']
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_2', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 92.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_2'], yield_robot robot_2, crossing_order ['robot_1', 'robot_2'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_2'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: robot_2 is facing robot_1 at close range, so robot_2 needs to yield (back up and step aside) to let robot_1 clear the lane first.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_2'], 'yield_robot': 'robot_2'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan False
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=node_handoff:robot_2->robot_1', 'grounding=dynamic_arms:heading_lane:robot_2:37', 'grounding=escort_off:robot_1:goal_behind', 'grounding=retreat_shield:robot_5', 'grounding=retreat_shield:robot_3', 'grounding=retreat_shield:robot_4']
- Actions: [('robot_2', 'yield', {'backup_distance_m': 1.285, 'crossing_order': ['robot_1'], 'fresh_latch_fast_fail': True, 'passer_robot_id': 'robot_1', 'reason': "robot_1 and robot_2 are physically conflicting at a distance of 0.42 m, blocking each other's paths.", 'retreat_choice': 'A'}), ('robot_1', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"}), ('robot_3', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"}), ('robot_4', 'temporary_wait', {'reason': "retreat shield: intent crosses robot_2's retreat"})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=node_handoff:robot_2->robot_1'], 'G6_verbatim_contradicted': True}

### D5 at 171.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3'], yield_robot robot_1, crossing_order ['robot_3', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_1 yield will allow robot_3 to proceed first and clear the narrow passage.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['grounding=dynamic_arms:lane:x', 'grounding=escort_turn_cap:robot_3:2.35->1.843']
- Actions: [('robot_1', 'yield', {'backup_distance_m': 1.373, 'crossing_order': ['robot_3'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.843, 'passer_robot_id': 'robot_3', 'reason': 'robot_1 and robot_3 are in a head-on conflict within 0.40 m and both are stopped.', 'retreat_choice': 'A'}), ('robot_3', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 206.2 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_2', 'robot_4', 'robot_5'], yield_robot None, crossing_order None, type bottleneck
- Plan legs (model): None
- Justification: The queued robots should hold in place while robot 3 completes its cross action and robot 1 yields, resolving the immediate blockage.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_2', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D7 at 236.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_3'], yield_robot robot_1, crossing_order ['robot_3', 'robot_1'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 1 is closest to its start but blocked, yielding will allow Robot 3 to pass and clear the narrow lane.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_1'], 'yield_robot': 'robot_1'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_1', 'robot_3']}, yield refusal yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_1,robot_3:78']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_1 and robot_3 both run along x but sit 78 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1:robot_4:backup | backup | 1.437 | 12.933 | 15.667 | 68.661 | COMPLETED | 1.487 | 1.035 | 0.0158 (rack/NE_north) | None (None) | completed | False |
| D1:robot_2:escort | escort | 2.35 | 12.933 | 45.3 | 68.73 | COMPLETED | 2.349 | 1.0 | 0.2007 (obstacle_1) | None (None) | completed | False |
| D4:robot_2:backup | backup | 1.285 | 92.7 | 95.667 | 164.0 | COMPLETED | 1.35 | 1.05 | 0.0911 (rack/NE_north) | None (None) | completed | False |
| D5:robot_1:backup | backup | 1.373 | 171.7 | 175.6 | 235.587 | COMPLETED | 1.582 | 1.152 | 0.0643 (rack/SE_east) | -0.0003 (robot_3) | completed | False |
| D5:robot_3:escort | escort | 1.843 | 171.7 | 204.634 | 235.635 | COMPLETED | 1.845 | 1.001 | 0.1161 (rack/SE_east) | -0.0003 (robot_1) | completed | False |

## Perception STALE Spans of 10 s or More

{"robot_4": [{"from_rel": 96.3, "to_rel": 100.967, "duration_s": 4.67, "ge_10s": false}, {"from_rel": 105.9, "to_rel": 111.767, "duration_s": 5.87, "ge_10s": false}, {"from_rel": 112.9, "to_rel": 115.9, "duration_s": 3.0, "ge_10s": false}, {"from_rel": 121.033, "to_rel": 121.367, "duration_s": 0.33, "ge_10s": false}, {"from_rel": 125.867, "to_rel": 136.6, "duration_s": 10.73, "ge_10s": true}, {"from_rel": 137.7, "to_rel": 145.333, "duration_s": 7.63, "ge_10s": false}, {"from_rel": 146.5, "to_rel": 152.633, "duration_s": 6.13, "ge_10s": false}, {"from_rel": 153.767, "to_rel": 155.167, "duration_s": 1.4, "ge_10s": false}, {"from_rel": 156.467, "to_rel": 157.167, "duration_s": 0.7, "ge_10s": false}, {"from_rel": 158.267, "to_rel": 167.767, "duration_s": 9.5, "ge_10s": false}, {"from_rel": 169.067, "to_rel": 169.1, "duration_s": 0.03, "ge_10s": false}], "robot_1": [{"from_rel": 205.7, "to_rel": 207.033, "duration_s": 1.33, "ge_10s": false}, {"from_rel": 231.667, "to_rel": 570.767, "duration_s": 339.1, "ge_10s": true}], "robot_3": [{"from_rel": 231.667, "to_rel": 570.767, "duration_s": 339.1, "ge_10s": true}]}

## Nav2 Abort Lines

- robot_3 261.69 rel-s: Failed to make progress
- robot_3 261.691 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 287.167 rel-s: Failed to make progress
- robot_3 287.167 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 312.672 rel-s: Failed to make progress
- robot_3 312.672 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 337.488 rel-s: Failed to make progress
- robot_3 337.489 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 349.763 rel-s: [spin] [ActionServer] Aborting handle.
- robot_3 380.512 rel-s: Failed to make progress
- robot_3 380.512 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 405.825 rel-s: Failed to make progress
- robot_3 405.825 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 418.036 rel-s: [backup] [ActionServer] Aborting handle.
- robot_3 443.299 rel-s: Failed to make progress
- robot_3 443.299 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 468.772 rel-s: Failed to make progress
- robot_3 468.772 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 480.612 rel-s: [spin] [ActionServer] Aborting handle.
- robot_3 512.46 rel-s: Failed to make progress
- robot_3 512.461 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 537.209 rel-s: Failed to make progress
- robot_3 537.209 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 549.276 rel-s: [backup] [ActionServer] Aborting handle.
- robot_3 575.545 rel-s: Failed to make progress
- robot_3 575.545 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 601.375 rel-s: Failed to make progress
- robot_3 601.375 rel-s: [follow_path] [ActionServer] Aborting handle.
- robot_3 613.215 rel-s: [spin] [ActionServer] Aborting handle.
- robot_3 645.312 rel-s: Failed to make progress
- robot_3 645.312 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: [{'rel': 16.338, 'pairs': 'robot_2+robot_4,robot_4+robot_5'}, {'rel': 43.42, 'pairs': 'robot_2+robot_4'}, {'rel': 68.705, 'pairs': '-'}, {'rel': 97.682, 'pairs': 'robot_1+robot_2,robot_2+robot_3,robot_2+robot_4,robot_2+robot_5'}, {'rel': 119.337, 'pairs': 'robot_1+robot_2'}, {'rel': 164.002, 'pairs': '-'}, {'rel': 173.251, 'pairs': 'robot_1+robot_3'}, {'rel': 235.627, 'pairs': '-'}]
- Safety-stop spans: robot_4|min_distance_violation: 2 spans; robot_2|min_distance_violation: 3 spans; robot_1|min_distance_violation: 3 spans; robot_3|min_distance_violation: 2 spans; robot_5|min_distance_violation: 1 spans
