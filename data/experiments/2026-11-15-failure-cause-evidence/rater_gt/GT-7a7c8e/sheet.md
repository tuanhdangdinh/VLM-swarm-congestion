# Evidence Sheet GT-7a7c8e

- Censoring: t_end 144.303 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4 | 14.903 | 144.303 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_2', 'robot_3'], ['robot_3', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 101.6, 'until_rel': 144.3}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 23.4, 'until_rel': 144.3}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.1, 'until_rel': 144.3}]

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
