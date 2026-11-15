# Evidence Sheet GT-a3cdae

- Censoring: t_end 576.703 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4, robot_5 | 31.603 | 576.703 | False | - | - |
| FU2 | conflict | robot_1, robot_3 | 37.803 | 576.703 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_4'], ['robot_2', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 64.0, 'until_rel': 576.7}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 31.9, 'until_rel': 576.7}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_4|box:rack/NW_west: [22.0, 54.4] -0.0

### FU2

- Pairs: [['robot_1', 'robot_3']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 38.0, 'until_rel': 576.7}]

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
