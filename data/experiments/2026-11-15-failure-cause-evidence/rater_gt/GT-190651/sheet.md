# Evidence Sheet GT-190651

- Censoring: t_end 570.907 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4, robot_5 | 184.407 | 570.907 | False | - | - |
| FU2 | conflict | robot_1, robot_3 | 219.007 | 570.907 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_5'], ['robot_4', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 184.61, 'until_rel': 570.91}, {'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 195.11, 'until_rel': 570.91}]

### FU2

- Pairs: [['robot_1', 'robot_3']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 223.01, 'until_rel': 570.91}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|robot_3: [222.31, 570.91] -0.0003

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
