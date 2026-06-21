# tests/simulation/test_m4_phase1_drive.py
"""M4 Phase 1 drive-chain acceptance test (documented-skip).

The drive chain (`/cmd_vel → /cmd_vel_safe → DifferentialController → physics →
/odom + /tf`) and the Branch B `CmdVelWatchdog` stop were verified on the Isaac
host during Task 6; see
`docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md` for the
measurements (yaw convention 0.0 deg over a 166 deg sweep, TF tracks odom,
watchdog zeroes the wheels in ~0.5 s of sim time).

There is no in-process `isaac_host` fixture yet (booting Isaac Sim, wiring the
ROS graphs, and coordinating a mid-run command-stop against a two-robot scenario
is not something the current `tests/simulation/` harness exposes). Per the Phase 1
plan, this test therefore documents the manual [HOST] procedure and is skipped
rather than asserting a passing automated result that does not exist.
"""
import pytest

from isaac.vgu_sim.diff_drive_oracle import forward_distance

SPEED = 0.10
DRIVE_SEC = 3.0


@pytest.mark.isaac_sim
@pytest.mark.ros2
def test_robot_drives_predicted_distance_then_watchdog_stops():
    """Drive robot_1 forward, check displacement vs oracle, then watchdog stop.

    Manual [HOST] procedure (run under Isaac Sim's Python on the GCP box):

    1. Build the scenario and boot the sim with the drive + watchdog graphs wired
       exactly as `isaac.vgu_sim.runner.run_simulation` does (open the scenario
       with an absolute path; `_wire_ros_graphs`; `_start_cmd_vel_watchdog`).
    2. Record robot_1's start pose from `/robot_1/odom`.
    3. Drive forward with the fixed-twist commander::

           from tests.simulation.stop_stub import FixedTwistDriver

           driver = FixedTwistDriver.spin_in_thread(["robot_1"], speed_mps=SPEED)
           # advance the sim for DRIVE_SEC of sim time, then:
           driver.request_stop()  # cease publishing; the watchdog now zeroes wheels

    4. Record the end pose; assert the integrated displacement matches the oracle::

           moved == pytest.approx(forward_distance(SPEED, DRIVE_SEC), rel=0.20)

       (`forward_distance(0.10, 3.0) == 0.30 m`; the 20 % tolerance absorbs
       spin-up/spin-down and friction.)
    5. Advance ~1.0 s more of sim time and assert the watchdog stopped the robot:
       `/robot_1/odom` linear velocity `< 0.01 m/s`.

    When subscribing to `/tf`/`/odom`, drain ALL ready rclpy callbacks per sim
    step (>=2 msgs/step); a single `spin_once` starves the `/tf` queue and looks
    like a freeze (Task 6 finding 4).
    """
    pytest.skip(
        "No in-process isaac_host fixture; Phase 1 drive + watchdog verified "
        "manually on host (Task 6). See "
        "docs/reports/2026-06-19-m4-phase1-task6-tf-watchdog-verification.md "
        "and the manual procedure in this test's docstring."
    )
