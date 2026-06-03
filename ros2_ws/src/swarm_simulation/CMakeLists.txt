cmake_minimum_required(VERSION 3.8)
project(swarm_simulation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds models maps scenarios
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
