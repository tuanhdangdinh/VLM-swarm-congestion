# Evidence Sheet GT-4e2591

- Censoring: t_end 570.073 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_2, robot_3, robot_4 | 22.073 | 570.073 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 135.073 | 570.073 | False | - | - |

### FU1

- Pairs: [['robot_2', 'robot_3'], ['robot_2', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 22.37, 'until_rel': 570.07}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 122.17, 'until_rel': 570.07}]

### FU2

- Pairs: [['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 135.27, 'until_rel': 570.07}]

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
