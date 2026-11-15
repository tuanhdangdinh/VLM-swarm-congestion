# Evidence Sheet GT-595e94

- Censoring: t_end 572.07 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_3, robot_4, robot_5 | 12.27 | 572.07 | False | - | - |
| FU2 | conflict | robot_1, robot_2 | 50.67 | 572.07 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_4'], ['robot_3', 'robot_4'], ['robot_3', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_3', 'robot_4'], 'close_and_stopped_from_rel': 20.57, 'until_rel': 572.07}, {'pair': ['robot_3', 'robot_5'], 'close_and_stopped_from_rel': 33.27, 'until_rel': 572.07}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_5|box:obstacle_1: [26.47, 28.77] 0.0032

### FU2

- Pairs: [['robot_1', 'robot_2']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 50.87, 'until_rel': 572.07}]

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
