# Evidence Sheet GT-a74755

- Censoring: t_end 568.54 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_4, robot_5 | 69.04 | 568.54 | False | - | - |
| FU2 | conflict | robot_2, robot_3 | 240.94 | 568.54 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 69.24, 'until_rel': 568.54}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 179.84, 'until_rel': 568.54}]

### FU2

- Pairs: [['robot_2', 'robot_3']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 241.44, 'until_rel': 568.54}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_3|box:obstacle_2: [114.74, 568.54] -0.0002; robot_2|box:obstacle_2: [238.54, 568.54] 0.0038

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
