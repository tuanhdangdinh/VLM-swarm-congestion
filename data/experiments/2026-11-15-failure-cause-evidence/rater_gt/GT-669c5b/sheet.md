# Evidence Sheet GT-669c5b

- Censoring: t_end 269.007 rel-s

## Failure Units

| FU | Kind | Robots | t0 | End | Excluded | Chain (rubric) | Flags |
|---|---|---|---|---|---|---|---|
| FU1 | conflict | robot_1, robot_2, robot_5 | 245.307 | 269.007 | False | - | - |

### FU1

- Pairs: [['robot_1', 'robot_2'], ['robot_1', 'robot_5']]
- X3 GT input (pair < 0.45 m and both stopped to censoring): [{'pair': ['robot_1', 'robot_2'], 'close_and_stopped_from_rel': 245.71, 'until_rel': 269.01}, {'pair': ['robot_1', 'robot_5'], 'close_and_stopped_from_rel': 268.71, 'until_rel': 269.01}]
- GT contacts (gap <= 0.005 m) of FU robots: robot_1|box:obstacle_1: [54.01, 136.01] -0.0002; robot_2|box:obstacle_2: [184.01, 215.41] -0.0001

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
