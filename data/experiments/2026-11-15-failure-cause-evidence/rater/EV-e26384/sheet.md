# Evidence Sheet EV-e26384

- Censoring: t_end 108.807 rel-s, reason stop_flag
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=15 max residual 1.182 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_5 | 14.507 | 108.807 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 3, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 15.31, 'until_rel': 108.81}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 26.31, 'to_rel': 108.81, 'duration_s': 82.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}, {'robot': 'robot_5', 'from_rel': 26.31, 'to_rel': 108.81, 'duration_s': 82.5, 'to_censor': True, 'safety_stop_cover_fraction': 1.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 13.816 | safety_stop_span | robot_5 | to 118.704 (26557 lines) |
| 13.822 | safety_stop_span | robot_1 | to 118.704 (26557 lines) |
| 16.733 | analysis | D1 | positive strategy=temporary_wait involved=['robot_1', 'robot_5'] yield=None |
| 16.733 | dispatched | D1 | robot_1:temporary_wait, robot_5:temporary_wait |
| 29.4 | analysis | D2 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_5 |
| 29.4 | withheld | D2 | robot_5:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |
| 34.2 | analysis | D3 | positive strategy=yield involved=['robot_1', 'robot_5'] yield=robot_5 |
| 34.2 | withheld | D3 | robot_5:temporary_wait, robot_1:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 14.8 | U:T1_fidelity / episode_gate_pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |
| D1 | 16.733 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |
| D2 | 29.4 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |
| D3 | 34.2 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.03} |

## Decisions

### D1 at 16.733 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_5'], yield_robot None, crossing_order None, type crowding
- Plan legs (model): [{'action': 'wait', 'robot_id': 'robot_1'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having the robots wait or proceed sequentially will prevent a collision and allow them to clear the narrow corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance vlm_verbatim, edits [], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 29.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_5, crossing_order ['robot_1', 'robot_5'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Robot 5 should yield to allow Robot 1 to move forward to its goal, thereby resolving the close-proximity deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_5', 'robot_1']}, yield refusal yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_5,robot_1:88']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 34.2 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_1', 'robot_5'], yield_robot robot_5, crossing_order ['robot_1', 'robot_5'], type bottleneck
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_4'}]
- Justification: Having robot_5 yield and move aside will allow robot_1 to clear the corridor towards its goal.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_5'], 'yield_robot': 'robot_5'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_5', 'robot_1']}, yield refusal yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_5,robot_1:88']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured'}), ('robot_1', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_5 and robot_1 both run along y but sit 88 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 42.1 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_4, crossing_order ['robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_4 yield allows robot_3 to proceed first and clears the deadlock in the central aisle.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance repaired, edits [{'op': 'swap', 'reason': 'yield re-grounded: dispatch yields robot_3, not robot_4 (grounding=heading_regrounded:robot_4->robot_3); swapped roles robot_4 (yield) <-> robot_3 (cross)', 'robot_ids': ['robot_3', 'robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['retreat=escort_park_filtered:A:robot_4:0.215', 'grounding=dynamic_arms:bearing_lane:robot_4:30', 'grounding=heading_regrounded:robot_4->robot_3', 'grounding=dynamic_arms:lane:y', 'grounding=escort_turn_cap:robot_4:2.35->1.825']
- Actions: [('robot_3', 'yield', {'backup_distance_m': 1.319, 'crossing_order': ['robot_4'], 'fresh_latch_fast_fail': True, 'passer_escort_distance_m': 1.825, 'passer_robot_id': 'robot_4', 'reason': "robot_3 and robot_4 are head-to-head in a narrow corridor, blocking each other's paths.", 'retreat_choice': 'B'}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': ['grounding=heading_regrounded:robot_4->robot_3'], 'G6_verbatim_contradicted': False}

### D5 at 102.2 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: Robot 3 has successfully yielded and is now moving, allowing the other robots to proceed as planned without any active deadlock or bottleneck.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D6 at 106.533 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The robots involved in the previous action have cleared each other, and no new congestion is detected.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D4:robot_3:backup | backup | 1.319 | 42.1 | 44.8 | 97.904 | COMPLETED | 1.534 | 1.163 | 0.3216 (obstacle_1) | None (None) | completed | False |
| D4:robot_4:escort | escort | 1.825 | 42.1 | 77.234 | 97.913 | COMPLETED | 1.721 | 0.943 | 0.3286 (obstacle_2) | None (None) | completed | False |

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: [{'rel': 46.023, 'pairs': 'robot_3+robot_4'}, {'rel': 97.945, 'pairs': '-'}]
- Safety-stop spans: robot_5|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans
