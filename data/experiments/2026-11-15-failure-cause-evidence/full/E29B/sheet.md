# Evidence Sheet E29B

- Censoring: t_end 570.67 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: U:no_m4_clock_anchor (m4.log has fewer than 2 sim_t= lines)
- Outcome fields (frozen, copied): {"a33_involved_f1": [null, null], "a33_n_conflicts": 2, "a33_n_detected": 0, "a33_type_correct": [null, null], "censor_reason": "horizon", "completeness_status": "failed", "source": "[T] batch6/scores_t1/s1_scoring.jsonl", "t_end_rel": 570.67, "tasks_completed": 0, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_4 | 15.97 | 570.67 | False | - | - |
| FU2 | conflict | robot_2, robot_3, robot_5 | 19.57 | 570.67 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 16.67, 'until_rel': 570.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 16.37, 'to_rel': 570.67, 'duration_s': 554.3, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_4', 'from_rel': 16.57, 'to_rel': 570.67, 'duration_s': 554.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 8.87 | gt_submargin | robot_1|box:obstacle_1 | to 10.47 min gap 0.014 m |
| 17.933 | m1_stale | robot_1 | STALE 0.7 s |
| None | safety_stop_span | robot_1 | to None (136452 lines) |
| None | safety_stop_span | robot_4 | to None (136452 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 16.1 | unverifiable_in_bundle / unverifiable_in_bundle | 5/88 | 5/88 | 5/88 | True | {'robot': 'robot_1', 'heading_deg': 45, 'distance_m': 0.06} |

### FU2

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 19.77, 'until_rel': 570.67}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 22.07, 'until_rel': 570.67}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 19.47, 'to_rel': 570.67, 'duration_s': 551.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_3', 'from_rel': 19.47, 'to_rel': 570.67, 'duration_s': 551.2, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_5', 'from_rel': 21.87, 'to_rel': 570.67, 'duration_s': 548.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.67 | gt_submargin | robot_2|box:obstacle_2 | to 14.07 min gap 0.0213 m |
| None | safety_stop_span | robot_3 | to None (135539 lines) |
| None | safety_stop_span | robot_2 | to None (135539 lines) |
| None | safety_stop_span | robot_5 | to None (134934 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 19.733 | unverifiable_in_bundle / unverifiable_in_bundle | 97/237 | 97/237 | 97/237 | True | {'robot': 'robot_5', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: []
- Safety-stop spans: robot_1|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans
