# Evidence Sheet GT-83c441

- Censoring: t_end 573.807 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_3 | 54.607 | 573.807 | False | - | - |
| FU2 | conflict | robot_4, robot_5 | 73.507 | 573.807 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_2', 'robot_3']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 96.61, 'until_rel': 573.81}, {'pair': ['robot_2', 'robot_3'], 'close_and_stopped_from_rel': 54.91, 'until_rel': 573.81}]

### FU2

- Pairs: [['robot_4', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_4', 'robot_5'], 'close_and_stopped_from_rel': 73.61, 'until_rel': 573.81}]

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
