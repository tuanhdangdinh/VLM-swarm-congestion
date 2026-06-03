# Project Codespace File Structure

Draft structure for a ROS2 + VLM/RAG warehouse swarm robotics project, aligned with
`modules.md`.

```text
vgu-vlm-swarm/
├── .devcontainer/
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── post_create.sh
├── .github/
│   └── workflows/
│       ├── ros_ci.yml
│       └── python_ci.yml
├── docs/
│   ├── project_proposal.md
│   ├── modules.md
│   └── codespace_file_structure.md
├── ros2_ws/
│   ├── src/
│   │   ├── swarm_interfaces/
│   │   │   ├── package.xml
│   │   │   ├── CMakeLists.txt
│   │   │   ├── config/
│   │   │   │   └── qos_profiles.yaml
│   │   │   ├── msg/
│   │   │   │   ├── RobotState.msg
│   │   │   │   ├── CoordinationCommand.msg
│   │   │   │   └── CoordinationStatus.msg
│   │   │   └── srv/
│   │   │       └── TriggerCongestionAnalysis.srv
│   │   ├── swarm_perception/
│   │   │   ├── package.xml
│   │   │   ├── setup.py
│   │   │   ├── config/
│   │   │   │   ├── camera.yaml
│   │   │   │   └── aruco.yaml
│   │   │   ├── launch/
│   │   │   │   └── perception.launch.py
│   │   │   └── swarm_perception/
│   │   │       ├── camera_node.py
│   │   │       ├── aruco_tracker_node.py
│   │   │       ├── homography.py
│   │   │       ├── state_estimator.py
│   │   │       └── scene_annotator.py
│   │   ├── swarm_orchestrator/
│   │   │   ├── package.xml
│   │   │   ├── setup.py
│   │   │   ├── config/
│   │   │   │   └── orchestrator.yaml
│   │   │   ├── launch/
│   │   │   │   └── orchestrator.launch.py
│   │   │   └── swarm_orchestrator/
│   │   │       ├── orchestrator_node.py
│   │   │       ├── congestion_detector.py
│   │   │       ├── task_registry.py
│   │   │       └── command_lifecycle.py
│   │   ├── swarm_execution/
│   │   │   ├── package.xml
│   │   │   ├── setup.py
│   │   │   ├── config/
│   │   │   │   └── safety.yaml
│   │   │   ├── launch/
│   │   │   │   └── execution.launch.py
│   │   │   └── swarm_execution/
│   │   │       ├── coordination_client_node.py
│   │   │       ├── command_bus_node.py
│   │   │       ├── safety_monitor_node.py
│   │   │       └── nav2_adapter.py
│   │   └── swarm_simulation/
│   │       ├── package.xml
│   │       ├── CMakeLists.txt
│   │       ├── launch/
│   │       │   ├── warehouse_world.launch.py
│   │       │   └── benchmark.launch.py
│   │       ├── worlds/
│   │       │   └── warehouse.world
│   │       ├── models/
│   │       │   ├── aruco_turtlebot3/
│   │       │   └── warehouse_assets/
│   │       ├── maps/
│   │       │   └── warehouse_map.yaml
│   │       └── scenarios/
│   │           ├── head_on_deadlock.yaml
│   │           ├── intersection_bottleneck.yaml
│   │           └── dynamic_anomaly.yaml
│   ├── build/
│   ├── install/
│   └── log/
├── reasoning/
│   ├── vlm/
│   │   ├── __init__.py
│   │   ├── backend_base.py
│   │   ├── vila_backend.py
│   │   ├── cosmos_backend.py
│   │   ├── prompt_builder.py
│   │   └── output_parser.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   ├── command_grounder.py
│   │   └── templates/
│   │       ├── yield.yaml
│   │       ├── reroute.yaml
│   │       ├── convoy.yaml
│   │       ├── priority_override.yaml
│   │       ├── temporary_wait.yaml
│   │       └── reverse.yaml
│   └── schemas/
│       ├── robot_state.schema.json
│       ├── vlm_decision.schema.json
│       └── coordination_command.schema.json
├── benchmarks/
│   ├── baselines/
│   │   ├── apf/
│   │   ├── orca/
│   │   ├── cbs/
│   │   └── congestion_aware/
│   ├── metrics/
│   │   ├── throughput.py
│   │   ├── waiting_time.py
│   │   ├── collision_rate.py
│   │   ├── energy.py
│   │   └── deadlock_recovery.py
│   ├── runners/
│   │   ├── run_scenario.py
│   │   └── run_ablation.py
│   └── results/
│       └── .gitkeep
├── config/
│   ├── dds/
│   │   ├── cyclonedds.xml
│   │   └── fastdds.xml
│   ├── models.yaml
│   ├── rag.yaml
│   ├── robots.yaml
│   └── logging.yaml
├── data/
│   ├── calibration/
│   │   ├── checkerboard_images/
│   │   └── homography.yaml
│   ├── knowledge_base/
│   │   └── coordination_templates.yaml
│   ├── vector_store/
│   │   └── .gitkeep
│   └── logs/
│       └── .gitkeep
├── scripts/
│   ├── setup_codespace.sh
│   ├── build_ros2.sh
│   ├── run_simulation.sh
│   ├── run_orchestrator.sh
│   └── index_rag_kb.sh
├── tests/
│   ├── unit/
│   │   ├── test_vlm_output_parser.py
│   │   ├── test_command_grounder.py
│   │   └── test_schemas.py
│   ├── integration/
│   │   ├── test_perception_to_vlm.py
│   │   ├── test_vlm_to_rag.py
│   │   └── test_command_to_ros2.py
│   └── simulation/
│       ├── test_head_on_deadlock.py
│       ├── test_intersection_bottleneck.py
│       └── test_dynamic_anomaly.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── Makefile
```

## Top-level Purpose

- `.devcontainer/` defines the GitHub Codespaces environment with ROS2, Python,
  OpenCV, Gazebo/Webots dependencies, and optional GPU/VLM tooling.
- `ros2_ws/` is the ROS2 workspace containing perception, orchestration, execution,
  interfaces, and simulation packages.
- `reasoning/` contains Python-only VLM and RAG logic that can be tested independently from ROS2.
- `benchmarks/` contains baselines, metrics, scenario runners, and result outputs.
- `config/` centralizes model, RAG, robot, and logging configuration.
- `config/dds/` contains ROS2 DDS vendor configuration for Cyclone DDS or Fast DDS.
- `data/` stores calibration files, curated coordination knowledge, vector-store artifacts,
  and runtime logs.
- `scripts/` provides Codespaces-friendly setup and run commands.
- `tests/` separates unit, integration, and simulation-level validation.

## ROS2 Package Mapping

- `swarm_interfaces` maps to cross-cutting schemas and ROS2 message contracts.
- `swarm_interfaces/config/qos_profiles.yaml` defines topic reliability, durability,
  history depth, and deadline/liveliness policies for ROS2/DDS communication.
- `swarm_perception` maps to M1: camera, ArUco tracking, state estimation, annotation.
- `swarm_orchestrator` maps to M5: congestion trigger logic and pipeline lifecycle.
- `swarm_execution` maps to M4: command dispatch, robot clients, Nav2 adapter, safety.
- `swarm_simulation` maps to M6: worlds, maps, robot models, scenarios, benchmark launch.

## AI Module Mapping

- `reasoning/vlm` maps to M2: prompt construction, backend abstraction, JSON validation.
- `reasoning/rag` maps to M3: embedding, retrieval, action-template grounding.
- `reasoning/schemas` maps to C1: JSON schemas shared by ROS2 and Python modules.

## Recommended First Scaffold

1. Create `.devcontainer/`, `ros2_ws/src/swarm_interfaces`, and `ros2_ws/src/swarm_simulation`.
2. Add `swarm_execution` with a Nav2 baseline and safety monitor stub.
3. Add `swarm_perception` with simulated camera input and ArUco tracking.
4. Add `reasoning/schemas`, then `swarm_orchestrator` with a state-machine skeleton.
5. Add `reasoning/vlm` and `reasoning/rag` behind mockable interfaces.
6. Add benchmarks and simulation tests once the loop can run end to end.
