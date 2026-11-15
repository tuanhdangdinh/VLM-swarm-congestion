# Evidence Sheet GT-9c8ad7

- Censoring: t_end 568.17 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 65.07 | 568.17 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_2', 'robot_3'], ['robot_2', 'robot_4'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 65.67, 'until_rel': 568.17}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 100.97, 'until_rel': 568.17}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 133.57, 'until_rel': 568.17}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 267.07, 'until_rel': 568.17}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_5|box:rack/SW_west: [111.37, 139.47] -0.0017; robot_5|box:obstacle_1: [155.67, 157.97] 0.0032

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
