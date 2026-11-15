# Evidence Sheet GT-b3d4ec

- Censoring: t_end 572.67 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3, robot_4, robot_5 | 12.17 | 572.67 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_3'], ['robot_1', 'robot_5'], ['robot_2', 'robot_5'], ['robot_3', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_3'], 'close_and_stopped_from_rel': 98.47, 'until_rel': 572.67}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 16.97, 'until_rel': 572.67}, {'pair': ['robot_2', 'robot_5'], 'close_and_stopped_from_rel': 112.67, 'until_rel': 572.67}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 100.67, 'until_rel': 572.67}]

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
