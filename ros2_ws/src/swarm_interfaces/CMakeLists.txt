cmake_minimum_required(VERSION 3.8)
project(swarm_interfaces)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotState.msg"
  "msg/CoordinationCommand.msg"
  "msg/CoordinationStatus.msg"
  "srv/TriggerCongestionAnalysis.srv"
)

ament_package()
