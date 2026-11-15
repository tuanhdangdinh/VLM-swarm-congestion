# Evidence Sheet GT-72693e

- Censoring: t_end 571.073 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_3, robot_4, robot_5 | 17.173 | 571.073 | False | - | - |
| FU2 | conflict | robot_1, robot_2 | 54.673 | 571.073 | False | - | - |

### FU1

- Pairs: [['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 17.87, 'until_rel': 571.07}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 49.77, 'until_rel': 571.07}]

### FU2

- Pairs: [['robot_1', 'robot_2']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 54.97, 'until_rel': 571.07}]

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
