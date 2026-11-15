# Evidence Sheet EV-3e6d9b

- Censoring: t_end 570.37 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: U:no_m4_clock_anchor (m4.log has fewer than 2 sim_t= lines)

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_5 | 14.27 | 570.37 | False | - | - |
| FU2 | conflict | robot_2, robot_3, robot_4 | 20.57 | 570.37 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 15.17, 'until_rel': 570.37}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 14.67, 'to_rel': 570.37, 'duration_s': 555.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_5', 'from_rel': 14.87, 'to_rel': 570.37, 'duration_s': 555.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| 12.47 | gt_submargin | robot_1|box:obstacle_2 | to 13.27 min gap 0.0411 m |
| None | nav2 | robot_1 | [compute_path_to_pose] [ActionServer] Aborting handle. |
| None | safety_stop_span | robot_1 | to None (141400 lines) |
| None | safety_stop_span | robot_5 | to None (141400 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 14.5 | unverifiable_in_bundle / unverifiable_in_bundle | 31/88 | 31/88 | 31/88 | True | {'robot': 'robot_5', 'heading_deg': 180, 'distance_m': 0.12} |

### FU2

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4'], ['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 20.77, 'until_rel': 570.37}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 28.27, 'until_rel': 570.37}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 28.27, 'until_rel': 570.37}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_2', 'from_rel': 20.67, 'to_rel': 570.37, 'duration_s': 549.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_3', 'from_rel': 20.67, 'to_rel': 570.37, 'duration_s': 549.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_4', 'from_rel': 27.97, 'to_rel': 570.37, 'duration_s': 542.4, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| None | safety_stop_span | robot_2 | to None (139765 lines) |
| None | safety_stop_span | robot_3 | to None (139765 lines) |
| None | safety_stop_span | robot_4 | to None (137742 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 20.6 | unverifiable_in_bundle / unverifiable_in_bundle | 69/237 | 69/237 | 69/237 | True | {'robot': 'robot_4', 'heading_deg': 0, 'distance_m': 0.01} |

## Decisions

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

- robot_1 None rel-s: [compute_path_to_pose] [ActionServer] Aborting handle.

## Safety Latch

- Exempt changes: []
- Safety-stop spans: robot_1|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_2|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_4|min_distance_violation: 1 spans
