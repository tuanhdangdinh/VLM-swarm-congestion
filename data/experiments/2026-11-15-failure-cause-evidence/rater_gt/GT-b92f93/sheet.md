# Evidence Sheet GT-b92f93

- Censoring: t_end 570.67 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_3, robot_4 | 14.97 | 570.67 | False | - | - |
| FU2 | conflict | robot_1, robot_5 | 30.67 | 570.67 | False | - | - |
| FU3 | lone_stall | robot_2 | 138.17 | 570.67 | False | - | finished_all_or_between_tasks_at_censor (tool flag; rubric silent) |

### FU1

- Pairs: [['robot_3', 'robot_4']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 15.57, 'until_rel': 570.67}]

### FU2

- Pairs: [['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 30.87, 'until_rel': 570.67}]

### FU3

- GT contacts (gap <= 0.005 m) of FU robots: robot_2|box:obstacle_1: [18.87, 21.27] 0.001

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
