from pathlib import Path

import yaml


PARAMS_PATH = Path("ros2_ws/src/swarm_simulation/config/nav2_params.yaml")


def _nav2_params():
    with open(PARAMS_PATH) as f:
        return yaml.safe_load(f)


def test_costmap_obstacle_layers_subscribe_to_robot_scan_topic():
    params = _nav2_params()

    local_scan = params["local_costmap"]["local_costmap"]["ros__parameters"][
        "obstacle_layer"
    ]["scan"]["topic"]
    global_scan = params["global_costmap"]["global_costmap"]["ros__parameters"][
        "obstacle_layer"
    ]["scan"]["topic"]

    assert local_scan == "/<robot_namespace>/scan"
    assert global_scan == "/<robot_namespace>/scan"


def test_dwb_last_mile_tolerance_matches_goal_checker():
    params = _nav2_params()
    controller = params["controller_server"]["ros__parameters"]
    follow_path = controller["FollowPath"]
    goal_checker = controller["general_goal_checker"]

    assert follow_path["xy_goal_tolerance"] == goal_checker["xy_goal_tolerance"]
    assert follow_path["trans_stopped_velocity"] < follow_path["max_vel_x"]
