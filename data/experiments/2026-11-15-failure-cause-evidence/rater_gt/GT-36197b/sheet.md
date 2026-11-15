# Evidence Sheet GT-36197b

- Censoring: t_end 577.437 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_4 | 148.937 | 577.437 | False | - | - |
| FU2 | conflict | robot_1, robot_3, robot_5 | 162.237 | 577.437 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 149.24, 'until_rel': 577.44}]

### FU2

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 173.54, 'until_rel': 577.44}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 166.34, 'until_rel': 577.44}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_3|box:rack/SW_west: [20.84, 49.84] -0.0; robot_3|box:rack/SW_south: [143.54, 577.44] -0.0015

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
