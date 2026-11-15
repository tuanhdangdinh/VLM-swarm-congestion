# Evidence Sheet GT-5cb09c

- Censoring: t_end 210.103 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3 | 28.303 | 210.103 | False | - | - |
| FU2 | conflict | robot_2, robot_4, robot_5 | 67.003 | 210.103 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_3']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 28.6, 'until_rel': 210.1}]

### FU2

- Pairs: [['robot_2', 'robot_4'], ['robot_4', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 68.8, 'until_rel': 210.1}, {'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 100.7, 'until_rel': 210.1}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_2: [66.5, 210.1] -0.0014

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
