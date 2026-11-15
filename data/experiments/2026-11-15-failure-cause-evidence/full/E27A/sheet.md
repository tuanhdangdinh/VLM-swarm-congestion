# Evidence Sheet E27A

- Censoring: t_end 570.673 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=51 max residual 0.203 s
- Outcome fields (frozen, copied): {"a33_involved_f1": [0.6666666666666666], "a33_n_conflicts": 1, "a33_n_detected": 1, "a33_type_correct": [false], "censor_reason": "horizon", "completeness_status": "failed", "source": "[T] batch6/scores_t1/s1_scoring.jsonl", "t_end_rel": 570.673333334, "tasks_completed": 8, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_4, robot_5 | 17.373 | 570.673 | False | - | - |
| FU2 | lone_stall | robot_2 | 107.673 | 570.673 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_1', 'robot_5'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 9, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 73.97, 'until_rel': 570.67}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 17.87, 'until_rel': 570.67}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 49.27, 'until_rel': 570.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 112.17, 'to_rel': 570.67, 'duration_s': 458.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.916}, {'robot': 'robot_3', 'from_rel': 112.17, 'to_rel': 570.67, 'duration_s': 458.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.916}, {'robot': 'robot_4', 'from_rel': 112.17, 'to_rel': 570.67, 'duration_s': 458.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.916}, {'robot': 'robot_5', 'from_rel': 112.17, 'to_rel': 570.67, 'duration_s': 458.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.916}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 17.23 | safety_stop_span | robot_3 | to 531.94 (136763 lines) |
| 17.236 | safety_stop_span | robot_4 | to 531.94 (136763 lines) |
| 19.3 | analysis | a8b5600dc5b143f7a668027da26a7a27 | positive strategy=temporary_wait involved=['robot_3', 'robot_4'] yield=None |
| 19.3 | dispatched | a8b5600dc5b143f7a668027da26a7a27 | robot_3:temporary_wait, robot_4:temporary_wait |
| 20.87 | gt_submargin | robot_5|box:obstacle_2 | to 21.87 min gap 0.0354 m |
| 32.667 | analysis | 409cfdf83fbf4c69adfde3005129ed0b | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_4 |
| 32.667 | withheld | 409cfdf83fbf4c69adfde3005129ed0b | robot_4:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 32.733 | m1_stale | robot_5 | STALE 0.6 s |
| 38.77 | gt_submargin | robot_1|box:obstacle_2 | to 39.67 min gap 0.0386 m |
| 39.433 | analysis | d70129ed15e54b65865e5b8bb35311e3 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_3 |
| 39.433 | withheld | d70129ed15e54b65865e5b8bb35311e3 | robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 48.911 | safety_stop_span | robot_5 | to 531.94 (128466 lines) |
| 51.0 | m1_stale | robot_1 | STALE 2.67 s |
| 56.767 | analysis | 12a36853d9a241d19c11145352ae8de2 | positive strategy=temporary_wait involved=['robot_3', 'robot_4', 'robot_5'] yield=None |
| 56.767 | dispatched | 12a36853d9a241d19c11145352ae8de2 | robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 69.7 | analysis | 8eb0d9081ea5485ba9ea042a8d34e08d | positive strategy=junction_clear involved=['robot_3', 'robot_4', 'robot_5'] yield=robot_5 |
| 69.7 | withheld | 8eb0d9081ea5485ba9ea042a8d34e08d | robot_5:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 69.97 | gt_submargin | robot_1|box:obstacle_1 | to 71.07 min gap 0.0348 m |
| 73.767 | safety_stop_span | robot_1 | to 531.94 (121930 lines) |
| 75.633 | analysis | 07a43e5d7c0147e08a7a423f363b7e3b | positive strategy=priority_override involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=robot_1 |
| 75.633 | dispatched | 07a43e5d7c0147e08a7a423f363b7e3b | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 88.9 | analysis | 61136b87034a4af69c2eed6e5e484102 | positive strategy=convoy involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 88.9 | dispatched | 61136b87034a4af69c2eed6e5e484102 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 102.467 | analysis | b1d25d98fd2140579b5748f54119fa62 | positive strategy=temporary_wait involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 102.467 | dispatched | b1d25d98fd2140579b5748f54119fa62 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait |
| 115.833 | analysis | c882ce6c77cd41999b27c573cbe5f795 | positive strategy=junction_clear involved=['robot_1', 'robot_3', 'robot_4', 'robot_5'] yield=None |
| 115.833 | withheld | c882ce6c77cd41999b27c573cbe5f795 | robot_1:temporary_wait, robot_3:temporary_wait, robot_4:temporary_wait, robot_5:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 17.667 | episode_gate_pass / episode_gate_pass | 13/237 | 13/237 | 13/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| a8b5600dc5b143f7a668027da26a7a27 | 19.3 | pass / pass | 13/237 | 13/237 | 13/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 409cfdf83fbf4c69adfde3005129ed0b | 32.667 | pass / pass | 39/237 | 39/237 | 36/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| d70129ed15e54b65865e5b8bb35311e3 | 39.433 | pass / pass | 37/237 | 37/237 | 37/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |
| 12a36853d9a241d19c11145352ae8de2 | 56.767 | pass / pass | 13/237 | 13/237 | 13/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.01} |
| 8eb0d9081ea5485ba9ea042a8d34e08d | 69.7 | pass / pass | 23/237 | 23/237 | 23/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |
| 07a43e5d7c0147e08a7a423f363b7e3b | 75.633 | pass / pass | 20/237 | 20/237 | 20/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |
| 61136b87034a4af69c2eed6e5e484102 | 88.9 | pass / pass | 20/237 | 20/237 | 20/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |
| b1d25d98fd2140579b5748f54119fa62 | 102.467 | pass / pass | 20/237 | 20/237 | 20/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |
| c882ce6c77cd41999b27c573cbe5f795 | 115.833 | pass / pass | 11/237 | 11/237 | 11/237 | True | {'robot': 'robot_4', 'heading_deg': 135, 'distance_m': 0.02} |

### FU2

- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': None, 'lone_stall_positive_naming_robot': []}

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 107.967 | episode_gate_pass / episode_gate_pass | 2/32 | 2/32 | 2/32 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### a8b5600dc5b143f7a668027da26a7a27 at 19.3 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type bottleneck
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: robot_3 should wait for robot_4 to resume its movement and clear the narrow corridor before continuing.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 409cfdf83fbf4c69adfde3005129ed0b at 32.667 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_4, crossing_order ['robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Robot 4 needs to yield or reverse to give Robot 3 room to navigate out of the narrow corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_4', 'robot_3']}, yield refusal yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_4,robot_3:47']
- Actions: [('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_4 and robot_3 both run along y but sit 47 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### d70129ed15e54b65865e5b8bb35311e3 at 39.433 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_3, crossing_order ['robot_4', 'robot_3'], type bottleneck
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_3 yield allows robot_4 to continue to its goal, resolving the spatial conflict in the narrow aisle.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'would_dispatch_robot_ids': ['robot_3', 'robot_4']}, yield refusal yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured, regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured', 'grounding=dynamic_arms:parallel_refused:robot_3,robot_4:47']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no shared lane: robot_3 and robot_4 both run along y but sit 47 deg across it (side by side); no retreat room was measured'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### d16aefe1458b4344a75d11c78a447753 at 43.8 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: The active wait plan for robot 3 and robot 4 is executing as intended with no changes in robot positions or states that suggest a deadlock.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 69b1d9d65d9e42d68ec6b5dbecce4595 at 50.567 rel-s (negative)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage vlm
- Decision: strategy none, involved [], yield_robot None, crossing_order None, type none
- Plan legs (model): None
- Justification: No new congestion has been detected; the existing queue management plan is actively running and remains correct.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Grounding: published False, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: []
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 12a36853d9a241d19c11145352ae8de2 at 56.767 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_5'], type bottleneck
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'wait', 'robot_id': 'robot_3'}, {'action': 'wait', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Having the robots wait temporarily in sequence will allow the leading robot to proceed and clear the path for the trailing robots.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 8eb0d9081ea5485ba9ea042a8d34e08d at 69.7 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_3', 'robot_4', 'robot_5'], yield_robot robot_5, crossing_order ['robot_3', 'robot_4', 'robot_5'], type crowding
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: A junction clear is necessary to break the deadlock and allow the robots to move out of the narrow left aisle sequentially.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection repair distance exceeds bound 4, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_5', 'robot_3', 'robot_4']}, yield refusal yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['yield=infeasible:yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_5 0.00 m, robot_3 0.15 m, robot_4 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 07a43e5d7c0147e08a7a423f363b7e3b at 75.633 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy priority_override, involved ['robot_1', 'robot_3', 'robot_4', 'robot_5'], yield_robot robot_1, crossing_order ['robot_4', 'robot_3', 'robot_5', 'robot_1'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Robot 4, robot 3, and robot 5 all need to proceed northwards, while robot 1 wants to head south but is currently stuck behind them. Giving priority to the group of north-moving robots clears the corridor quickly.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_1: yield infeasible: robot_1/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['strategy=unsupported:priority_override']
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### 61136b87034a4af69c2eed6e5e484102 at 88.9 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy convoy, involved ['robot_1', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_5', 'robot_1'], type bottleneck
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_5'}, {'action': 'cross', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Robot 4 is at the front of the queue with an open path ahead and should proceed first, followed in single file by the rest of the queue.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_3: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_5: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_1: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}], rejection None, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['strategy=unsupported:convoy']
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### b1d25d98fd2140579b5748f54119fa62 at 102.467 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy temporary_wait, involved ['robot_1', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_5', 'robot_1'], type crowding
- Plan legs (model): None
- Justification: Having robot_2 clear first allows the remaining robots to systematically resume operations one by one once the passage is clear.
- Contract C1-C3: {'plan_present': False, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance m3_default, edits [], rejection plan absent, held True, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: []
- Actions: [('robot_1', 'temporary_wait', {}), ('robot_3', 'temporary_wait', {}), ('robot_4', 'temporary_wait', {}), ('robot_5', 'temporary_wait', {})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### c882ce6c77cd41999b27c573cbe5f795 at 115.833 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy junction_clear, involved ['robot_1', 'robot_3', 'robot_4', 'robot_5'], yield_robot None, crossing_order ['robot_4', 'robot_3', 'robot_5', 'robot_1'], type crowding
- Plan legs (model): [{'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'yield', 'robot_id': 'robot_5'}, {'action': 'yield', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: The robots must back up to clear space in the narrow passage so they can take turns or reroute safely.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': None, 'C3': None}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_4: cross infeasible: cross leg has no preceding yield leg to release it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}, {'op': 'substitute', 'reason': "robot_5: yield infeasible: robot_5/robot_1 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_5']}, {'op': 'substitute', 'reason': "robot_1: yield infeasible: robot_1/robot_3 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_1']}], rejection None, held True, dispatch_matches_plan False
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'would_dispatch_robot_ids': ['robot_1', 'robot_3', 'robot_4', 'robot_5']}, yield refusal yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required), regrounded None, from None
- Degradation tags: ['roles=legacy-convention', 'yield=infeasible:yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)', 'order=discarded_yield_axis', 'junction_clear=fallback:no_candidates', 'junction_geometry=shipped_unsolved:missing=junction_recede_offset_m,junction_backup_clearance_m']
- Actions: [('robot_1', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_3', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_4', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'}), ('robot_5', 'temporary_wait', {'reason': 'yield refused: no feasible yielder (robot_1 0.00 m, robot_3 0.15 m, robot_4 0.15 m, robot_5 0.15 m retreat room < 0.77 m required)'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: []
- Safety-stop spans: robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans
