# tests/simulation/conftest.py


def pytest_configure(config):
    config.addinivalue_line("markers", "isaac_sim: requires Isaac Sim 6.0 on Linux")
    config.addinivalue_line("markers", "ros2: requires ROS 2 Jazzy sourced")
