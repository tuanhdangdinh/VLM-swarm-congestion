# Evidence Sheet GT-00408f

- Censoring: t_end 569.807 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 23.607 | 569.807 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_2', 'robot_4'], ['robot_2', 'robot_5'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 69.71, 'until_rel': 569.81}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 89.41, 'until_rel': 569.81}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 73.11, 'until_rel': 569.81}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 82.31, 'until_rel': 569.81}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|box:rack/NW_west: [67.51, 569.81] -0.0

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
