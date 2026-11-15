# Evidence Sheet GT-c34011

- Censoring: t_end 571.173 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 36.573 | 571.173 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 101.873 | 571.173 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 36.77, 'until_rel': 571.17}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 133.27, 'until_rel': 571.17}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_1: [35.97, 571.17] -0.0001; robot_4|box:obstacle_1: [39.87, 74.27] -0.0057

### FU2

- Pairs: [['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 102.07, 'until_rel': 571.17}]

## Decisions

## Dispatched Legs (T3)

| Leg | Kind | Commanded m | Dispatch | Start | End | M4 terminal | Moved max | Fraction | Min static gap (box) | Min robot gap | Tags | Deadline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Perception STALE Spans of 10 s or More

none

## Nav2 Abort Lines

none

## Safety Latch

- Exempt changes: None
- Safety-stop spans: 
