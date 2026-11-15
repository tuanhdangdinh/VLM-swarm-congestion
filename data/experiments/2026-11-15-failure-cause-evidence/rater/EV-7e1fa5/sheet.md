# Evidence Sheet EV-7e1fa5

- Censoring: t_end 570.67 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: linear fit over m4.log sim_t= lines (rubric 7.1), fit n=6 max residual 0.006 s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_3, robot_4 | 14.97 | 570.67 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 30.67 | 570.67 | False | - | - |
| FU3 | lone_stall | robot_2 | 138.17 | 570.67 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 5, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.57, 'until_rel': 570.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_3', 'from_rel': 29.87, 'to_rel': 570.67, 'duration_s': 540.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.903}, {'robot': 'robot_4', 'from_rel': 29.87, 'to_rel': 570.67, 'duration_s': 540.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.903}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 14.952 | safety_stop_span | robot_3 | to 518.419 (142297 lines) |
| 14.961 | safety_stop_span | robot_4 | to 518.42 (142297 lines) |
| 14.978 | nav2 | robot_4 | [follow_path] [ActionServer] Aborting handle. |
| 16.567 | analysis | D1 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_3 |
| 16.567 | withheld | D1 | robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |
| 20.4 | analysis | D2 | positive strategy=reverse involved=['robot_3', 'robot_4'] yield=None |
| 20.4 | dispatched | D2 | robot_3:temporary_wait, robot_4:temporary_wait |
| 33.3 | analysis | D3 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_4 |
| 33.3 | withheld | D3 | robot_4:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 59.867 | analysis | D4 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_4 |
| 59.867 | withheld | D4 | robot_4:temporary_wait, robot_3:temporary_wait withheld=refusal_no_action |
| 64.0 | analysis | D5 | positive strategy=yield involved=['robot_3', 'robot_4'] yield=robot_3 |
| 64.0 | withheld | D5 | robot_3:temporary_wait, robot_4:temporary_wait withheld=refusal_no_action |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 15.3 | episode_gate_pass / episode_gate_pass | 29/88 | 29/88 | 29/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.09} |
| D1 | 16.567 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.1} |
| D2 | 20.4 | pass / pass | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.1} |
| D3 | 33.3 | pass / pass | 8/88 | 8/88 | 8/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.1} |
| D4 | 59.867 | pass / pass | 7/88 | 7/88 | 7/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.1} |
| D5 | 64.0 | pass / pass | 8/88 | 8/88 | 8/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.1} |

### FU2

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 30.87, 'until_rel': 570.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 30.67, 'to_rel': 570.67, 'duration_s': 540.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.903}, {'robot': 'robot_5', 'from_rel': 28.57, 'to_rel': 570.67, 'duration_s': 542.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.9}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 16.649 | nav2 | robot_1 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 16.678 | nav2 | robot_1 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 16.711 | nav2 | robot_1 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| 30.57 | safety_stop_span | robot_1 | to 518.42 (137935 lines) |
| 30.575 | safety_stop_span | robot_5 | to 518.42 (137935 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 30.767 | episode_gate_pass / episode_gate_pass | 2/88 | 2/88 | 2/88 | True | {'robot': 'robot_1', 'heading_deg': 90, 'distance_m': 0.04} |

### FU3

- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': True, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': None, 'lone_stall_positive_naming_robot': []}
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_1: [18.87, 21.27] 0.001

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 88.367 | m1_stale | robot_2 | STALE 0.2 s |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 138.2 | episode_gate_pass / episode_gate_pass | 4/32 | 4/32 | 4/32 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

### D1 at 16.567 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_3, crossing_order ['robot_4', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_3 yield by backing up or stepping aside will allow robot_4 to clear the passage, resolving the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'would_dispatch_robot_ids': ['robot_3', 'robot_4']}, yield refusal yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, regrounded None, from None
- Degradation tags: ["yield=infeasible:yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'grounding=dynamic_arms:ambiguous_refused:robot_3:39']
- Actions: [('robot_3', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"}), ('robot_4', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D2 at 20.4 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy reverse, involved ['robot_3', 'robot_4'], yield_robot None, crossing_order None, type deadlock
- Plan legs (model): [{'action': 'reverse', 'robot_id': 'robot_3'}, {'action': 'reverse', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Since robot_3 and robot_4 are head-on and very close (0.35 m), they must back out of each other's paths to clear the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': False, 'C2': None, 'C3': None, 'C1_detail': {'reverse_legs': ['robot_3', 'robot_4'], 'involved': ['robot_3', 'robot_4']}}
- Plan verifier: provenance repaired, edits [{'op': 'substitute', 'reason': "robot_3: reverse infeasible: robot_3/robot_4 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_3']}, {'op': 'substitute', 'reason': "robot_4: reverse infeasible: robot_3/robot_4 both outside the corridor on the same side; a reverse would traverse it; substituted to wait toward M3's derived plan", 'robot_ids': ['robot_4']}], rejection None, held False, dispatch_matches_plan True
- Grounding: published True, withheld None, yield refusal None, regrounded None, from None
- Degradation tags: ['reverse=infeasible:reverse refused: both robots outside the corridor on the same side; backing up would re-enter it', 'grounding=dynamic_arms:ambiguous']
- Actions: [('robot_3', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'}), ('robot_4', 'temporary_wait', {'reason': 'reverse refused: both robots outside the corridor on the same side; backing up would re-enter it'})]
- Mechanical flags: {'G2_m3_default_with_plan': False, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D3 at 33.3 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_4, crossing_order ['robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_2'}, {'action': 'continue', 'robot_id': 'robot_5'}]
- Justification: Having robot_4 yield allows robot_3 to clear the bottleneck along the southern corridor.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'would_dispatch_robot_ids': ['robot_4', 'robot_3']}, yield refusal yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, regrounded None, from None
- Degradation tags: ["yield=infeasible:yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'grounding=dynamic_arms:ambiguous_refused:robot_3:39']
- Actions: [('robot_4', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"}), ('robot_3', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D4 at 59.867 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_4, crossing_order ['robot_3', 'robot_4'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_4'}, {'action': 'cross', 'robot_id': 'robot_3'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Robot 4 can back up or step aside to allow Robot 3 to pass or clear the deadlock since Robot 4 has more open space behind it.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_4'], 'yield_robot': 'robot_4'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, held True, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'would_dispatch_robot_ids': ['robot_4', 'robot_3']}, yield refusal yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, regrounded None, from None
- Degradation tags: ["yield=infeasible:yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'grounding=dynamic_arms:ambiguous_refused:robot_3:39']
- Actions: [('robot_4', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"}), ('robot_3', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

### D5 at 64.0 rel-s (positive)

- Parse: valid, attempts 1, refusal None, error None, decision degradations [], terminal stage ok
- Decision: strategy yield, involved ['robot_3', 'robot_4'], yield_robot robot_3, crossing_order ['robot_4', 'robot_3'], type deadlock
- Plan legs (model): [{'action': 'yield', 'robot_id': 'robot_3'}, {'action': 'cross', 'robot_id': 'robot_4'}, {'action': 'continue', 'robot_id': 'robot_1'}, {'action': 'continue', 'robot_id': 'robot_5'}, {'action': 'continue', 'robot_id': 'robot_2'}]
- Justification: Robot 3 can yield or back up to allow Robot 4 to pass through or clear the deadlock.
- Contract C1-C3: {'plan_present': True, 'C1': None, 'C2': False, 'C3': None, 'C2_detail': {'yield_legs': ['robot_3'], 'yield_robot': 'robot_3'}}
- Plan verifier: provenance m3_default, edits [], rejection plan unrepairable: yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, held False, dispatch_matches_plan True
- Grounding: published False, withheld {'reason': 'refusal_no_action', 'refusal_reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'would_dispatch_robot_ids': ['robot_3', 'robot_4']}, yield refusal yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured, regrounded None, from None
- Degradation tags: ["yield=infeasible:yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured", 'grounding=dynamic_arms:ambiguous_refused:robot_3:39']
- Actions: [('robot_3', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"}), ('robot_4', 'temporary_wait', {'reason': "yield refused: ambiguous lane: robot_3 heads 39 deg off both axes (beyond the 30 deg snap), and robot_4's x lane crosses the pair's y bearing; no retreat room was measured"})]
- Mechanical flags: {'G2_m3_default_with_plan': True, 'G3_plan_nulled_by_parser': False, 'G4_role_change_tags': [], 'G6_verbatim_contradicted': False}

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_1 16.649 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.
- robot_1 16.678 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.
- robot_1 16.711 rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.
- robot_4 14.978 rel-s: [follow_path] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: []
- Safety-stop spans: robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
