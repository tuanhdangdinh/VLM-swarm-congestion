# Evidence Sheet GT-f5063e

- Censoring: t_end 577.27 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 25.07 | 577.27 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_2', 'robot_3'], ['robot_2', 'robot_4'], ['robot_2', 'robot_5'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_4'], 'close_and_stopped_from_rel': 64.57, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_4'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 46.77, 'until_rel': 577.27}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 26.07, 'until_rel': 577.27}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 25.47, 'until_rel': 577.27}]

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
