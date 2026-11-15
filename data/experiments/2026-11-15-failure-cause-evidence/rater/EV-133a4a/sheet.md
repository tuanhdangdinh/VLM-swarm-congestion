# Evidence Sheet EV-133a4a

- Censoring: t_end 571.97 rel-s, reason horizon
- Clock: all times rel-s (GT sim-s minus robot_1 release on the GT clock (A33(0)); = M1/ROS sim-s minus t0_m1); wall mapping: U:no_m4_clock_anchor (m4.log has fewer than 2 sim_t= lines)

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_3, robot_4 | 14.67 | 571.97 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 30.37 | 571.97 | False | - | - |
| FU3 | lone_stall | robot_2 | 139.37 | 571.97 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_3', 'robot_4']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.27, 'until_rel': 571.97}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_3', 'from_rel': 15.07, 'to_rel': 571.97, 'duration_s': 556.9, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_4', 'from_rel': 15.17, 'to_rel': 571.97, 'duration_s': 556.8, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| None | safety_stop_span | robot_4 | to None (138467 lines) |
| None | safety_stop_span | robot_3 | to None (138467 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 14.833 | unverifiable_in_bundle / unverifiable_in_bundle | 29/88 | 29/88 | 29/88 | True | {'robot': 'robot_3', 'heading_deg': 45, 'distance_m': 0.08} |

### FU2

- Pairs: [['robot_1', 'robot_5']]
- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': 0, 'lone_stall_positive_naming_robot': None}
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 30.77, 'until_rel': 571.97}]
- X2 input (stationary >= 60 s, no M4 leg, task traveling): [{'robot': 'robot_1', 'from_rel': 30.47, 'to_rel': 571.97, 'duration_s': 541.5, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}, {'robot': 'robot_5', 'from_rel': 35.27, 'to_rel': 571.97, 'duration_s': 536.7, 'to_censor': True, 'safety_stop_cover_fraction': 0.0}]

Event timeline (rel-s; rubric 7.1 event kinds touching this FU's robots):

| rel-s | Event | Ref | Detail |
|---|---|---|---|
| None | safety_stop_span | robot_5 | to None (133787 lines) |
| None | safety_stop_span | robot_1 | to None (133787 lines) |

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 30.5 | unverifiable_in_bundle / unverifiable_in_bundle | 2/88 | 2/88 | 2/88 | True | {'robot': 'robot_1', 'heading_deg': 90, 'distance_m': 0.04} |

### FU3

- Evidence gate inputs: {'t0_snapshot': True, 'decision_artifacts': False, 'm4_log': True}
- V1 input: {'a33_matched_positive_analyses': None, 'lone_stall_positive_naming_robot': []}

| Snapshot | rel-s | Fidelity (as written / +stage2+intents) | T1 as written | T1 +intents | T1 all guards on | T2 | T2 shortest |
|---|---|---|---|---|---|---|---|
| t0 | 139.667 | unverifiable_in_bundle / unverifiable_in_bundle | 4/32 | 4/32 | 4/32 | True | {'robot': 'robot_2', 'heading_deg': 0, 'distance_m': 0.01} |

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
- Safety-stop spans: robot_4|min_distance_violation: 1 spans; robot_3|min_distance_violation: 1 spans; robot_5|min_distance_violation: 1 spans; robot_1|min_distance_violation: 1 spans
