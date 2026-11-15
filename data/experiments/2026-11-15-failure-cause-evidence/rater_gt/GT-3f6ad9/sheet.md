# Evidence Sheet GT-3f6ad9

- Censoring: t_end 102.277 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 12.277 | 102.277 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 81.177 | 102.277 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_3', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 12.78, 'until_rel': 102.28}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 34.98, 'until_rel': 102.28}]

### FU2

- Pairs: [['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 81.28, 'until_rel': 102.28}]

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
