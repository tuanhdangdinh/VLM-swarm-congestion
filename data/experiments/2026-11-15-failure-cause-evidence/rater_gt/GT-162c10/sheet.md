# Evidence Sheet GT-162c10

- Censoring: t_end 570.673 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_4, robot_5 | 17.373 | 570.673 | False | - | - |
| FU2 | lone_stall | robot_2 | 107.673 | 570.673 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_1', 'robot_5'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 73.97, 'until_rel': 570.67}, {'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 17.87, 'until_rel': 570.67}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 49.27, 'until_rel': 570.67}]

### FU2


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
