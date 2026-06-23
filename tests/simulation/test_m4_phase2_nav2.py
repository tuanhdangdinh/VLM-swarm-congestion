"""M4 Phase 2 Nav2 goal-with-obstacle acceptance test (documented-skip).

Task 8: drive `robot_1` to a goal across the aisle with a static obstacle
(`task8_static_blocker`, see
`isaac/config/scenarios/head_on_deadlock_task8_obstacle.yaml`) placed directly
on the spawn-to-goal centerline, and confirm Nav2's local planner deviates
around it rather than driving through it or getting stuck. See
`docs/reports/2026-06-23-m4-phase2-task8-acceptance-verification.md` for the
host measurements (final position vs. goal, lateral deviation, `/robot_1/scan`
cleanliness under motion, and the obstacle's actual collision clearance).

There is no in-process `isaac_host` fixture yet (booting Isaac Sim, wiring the
ROS graphs, bringing up the namespaced Nav2 stack, and polling action-server
goal results against a live scenario is not something the current
`tests/simulation/` harness exposes — mirrors the Phase 1 gap documented in
`test_m4_phase1_drive.py`). Per the Phase 2 plan, this test therefore
documents the manual [HOST] procedure and is skipped rather than asserting a
passing automated result that does not exist.
"""
import pytest

GOAL_X, GOAL_Y, GOAL_YAW = 2.0, 0.0, 0.0
TOLERANCE_M = 0.15


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_robot_reaches_goal_around_static_obstacle():
    """Drive robot_1 to a goal across an aisle-blocking static obstacle.

    Manual [HOST] procedure (run under the env recipe in
    `docs/specs/module4_execution_safety.md` / Task 8 brief — `ROS_DISTRO`,
    `LD_LIBRARY_PATH`, `FASTRTPS_DEFAULT_PROFILES_FILE` set host-side before
    `setup_ros_env.sh`, and the matching `FASTRTPS_DEFAULT_PROFILES_FILE`
    set container-side before any `ros2` CLI use):

    1. Build `head_on_deadlock_task8_obstacle.yaml` (single robot, `robot_1`,
       plus one static obstacle, `task8_static_blocker`, at
       `pose: {x: 0.7, y: 0.0, yaw_rad: 0.0}` — between `robot_1`'s spawn
       `x=-0.6` and the goal `x=2.0`, on the centerline) via
       `isaac.scripts.run_simulation` (or the equivalent headless boot used
       by `isaac.vgu_sim.runner.run_simulation`).
    2. Inside the `vgu_ros` container, launch:

           ros2 launch swarm_simulation nav2_robot.launch.py \\
               robot_id:=robot_1 x:=-0.6 y:=0.0 yaw:=0.0

    3. Instantiate `swarm_execution.nav2_adapter.Nav2Adapter` and call::

           adapter.send_goal("robot_1", 2.0, 0.0, 0.0)

       (the only component permitted to talk to the Nav2 action server
       directly, per this project's M4 design rule).
    4. Poll `/robot_1/odom` (or TF) until the goal result callback fires or
       60 s of sim time elapse.
    5. Assert the final position is within 0.15 m of `(2.0, 0.0)`.
    6. Confirm the deviation was a real avoidance, not a drive-through: check
       `/robot_1/local_plan` (or the odom trace) for nonzero lateral
       (`y != 0.0`) excursion while passing the obstacle's `x`-range.
    7. Confirm `/robot_1/scan` stays clean (no spurious self-returns from the
       robot's own ArUco marker plate) while the robot is actually moving,
       not just at rest — Task 2/4's original lidar-vs-marker-plate gate has
       not previously been checked under motion.
    """
    pytest.skip(
        "No in-process isaac_host fixture; Phase 2 Task 8 goal-with-obstacle "
        "navigation verified manually on host. See "
        "docs/reports/2026-06-23-m4-phase2-task8-acceptance-verification.md "
        "and the manual procedure in this test's docstring."
    )
