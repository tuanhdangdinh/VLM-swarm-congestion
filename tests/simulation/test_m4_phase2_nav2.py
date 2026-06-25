# tests/simulation/test_m4_phase2_nav2.py
"""M4 Phase 2 Nav2 acceptance test (documented-skip).

Acceptance criterion (spec phase2-nav2-stack.md §8): a single NavigateToPose
goal drives robot_1 to within 0.15 m of a free-space goal with a static
obstacle present in its direct path, requiring the local planner to deviate
around the obstacle.

There is no in-process ``isaac_host`` fixture yet. This test documents the
manual [HOST] procedure and is skipped rather than asserting a passing
automated result that does not exist.
"""
import pytest

from swarm_execution.nav2_adapter import Nav2Adapter

GOAL_X, GOAL_Y, GOAL_YAW = 2.0, 0.0, 0.0
TOLERANCE_M = 0.15


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_robot_reaches_goal_around_static_obstacle():
    """Send robot_1 a Nav2 goal with a static obstacle in its direct path.

    Manual [HOST] procedure (run inside the vgu_ros container against a
    running Isaac Sim publishing ``/robot_1/scan``, ``/robot_1/odom``,
    and ``/tf``):

    1. Launch the ``head_on_deadlock`` scenario with the static obstacle
       from Task 8 Step 1 placed between robot_1's spawn (x≈−0.6) and the
       goal (x=2.0, y=0.0) — close enough to force the local planner to
       deviate, far enough that a straight-line path clips it.

    2. Launch the Nav2 stack for robot_1::

           ros2 launch swarm_simulation nav2_robot.launch.py robot_id:=robot_1

       Confirm ``/robot_1/navigate_to_pose`` action server is live::

           ros2 action list | grep robot_1

    3. Instantiate Nav2Adapter and send the goal::

           adapter = Nav2Adapter()
           adapter.send_goal("robot_1", GOAL_X, GOAL_Y, GOAL_YAW)

    4. Poll ``/robot_1/odom`` until the NavigateToPose result callback fires
       or 60 s elapse.

    5. Assert the final position is within TOLERANCE_M of the goal::

           assert final.distance_to_xy(GOAL_X, GOAL_Y) < TOLERANCE_M

    6. Assert the local plan deviated around the obstacle — confirm a
       nonzero lateral excursion in ``/robot_1/local_plan`` rather than
       a straight-line path through the obstacle.

    7. Verify ``/robot_1/scan`` remained clean throughout (no phantom return
       at the ArUco marker's bearing — Task 2 / Task 4 gate still holding
       under motion, not just at rest).

    Record findings in a verification report following the pattern in
    ``docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md``.
    """
    pytest.skip(
        "No in-process isaac_host fixture; Phase 2 Nav2 goal-with-obstacle "
        "acceptance must be verified manually on host. See manual procedure "
        "in this test's docstring and spec phase2-nav2-stack.md §8."
    )
