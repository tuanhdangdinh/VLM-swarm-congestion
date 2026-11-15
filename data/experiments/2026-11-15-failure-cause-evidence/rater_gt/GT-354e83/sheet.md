# Evidence Sheet GT-354e83

- Censoring: t_end 570.14 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_5 | 12.74 | 570.14 | False | - | - |
| FU2 | conflict | robot_2, robot_4 | 40.44 | 570.14 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 12.94, 'until_rel': 570.14}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 89.64, 'until_rel': 570.14}]

### FU2

- Pairs: [['robot_2', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 40.94, 'until_rel': 570.14}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:rack/NW_north: [27.24, 33.94] -0.0015

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
