# Evidence Sheet E31B

- Censoring: t_end 571.173 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: U:no_m4_clock_anchor (m4.log has fewer than 2 sim_t= lines)
- Outcome fields (frozen, copied): {"a33_involved_f1": [null, null], "a33_n_conflicts": 2, "a33_n_detected": 0, "a33_type_correct": [null, null], "censor_reason": "horizon", "completeness_status": "failed", "source": "[T] batch6/scores_t1/s1_scoring.jsonl", "t_end_rel": 571.173333334, "tasks_completed": 0, "tasks_total": 25}

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_5 | 11.773 | 571.173 | False | - | - |
| FU2 | conflict | robot_3, robot_4 | 12.073 | 571.173 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 28.27, 'until_rel': 571.17}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 12.37, 'until_rel': 571.17}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 12.07, 'to_rel': 571.17, 'duration_s': 559.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_2', 'from_rel': 28.17, 'to_rel': 571.17, 'duration_s': 543.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_5', 'from_rel': 12.17, 'to_rel': 571.17, 'duration_s': 559.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.57 | gt_submargin | robot_2|box:obstacle_2 | to 14.47 min gap 0.0087 m |
| 13.7 | m1_stale | robot_1 | STALE 2.47 s |
| None | safety_stop_span | robot_1 | to None (140529 lines) |
| None | safety_stop_span | robot_5 | to None (140529 lines) |
| None | safety_stop_span | robot_2 | to None (136520 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.033 | unverifiable_in_bundle / unverifiable_in_bundle | 33/237 | 33/237 | 33/237 | True | {'robot': 'robot_1', 'heading_deg': 0, 'distance_m': 0.05} |

### FU2

- Pairs: [['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 12.37, 'until_rel': 571.17}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_3', 'from_rel': 12.17, 'to_rel': 571.17, 'duration_s': 559.0, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_4', 'from_rel': 12.07, 'to_rel': 571.17, 'duration_s': 559.1, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| None | safety_stop_span | robot_3 | to None (140467 lines) |
| None | safety_stop_span | robot_4 | to None (140467 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 12.267 | unverifiable_in_bundle / unverifiable_in_bundle | 33/88 | 33/88 | 33/88 | True | {'robot': 'robot_3', 'heading_deg': 0, 'distance_m': 0.06} |

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
- Safety-stop spans: robot_1|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans
