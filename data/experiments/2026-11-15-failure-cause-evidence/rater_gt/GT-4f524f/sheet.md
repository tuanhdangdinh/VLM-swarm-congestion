# Evidence Sheet GT-4f524f

- Censoring: t_end 571.97 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_3, robot_4 | 14.67 | 571.97 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 30.37 | 571.97 | False | - | - |
| FU3 | lone_stall | robot_2 | 139.37 | 571.97 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_3', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.27, 'until_rel': 571.97}]

### FU2

- Pairs: [['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 30.77, 'until_rel': 571.97}]

### FU3


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
