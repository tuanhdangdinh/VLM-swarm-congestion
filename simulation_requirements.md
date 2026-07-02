# Simulation Requirements

## Objective

Build an Isaac Sim-based warehouse simulation to test the complete VLM
swarm-coordination pipeline using TurtleBot3 robots and ROS 2.

## Scope

### 1. Isaac Sim Backend

- Use Isaac Sim as the only simulation backend.
- Develop scenes using Isaac Sim Python APIs and OpenUSD.
- Support GUI development and standalone/headless execution.

### 2. Modular Warehouse Scenes

- Create a reusable base warehouse containing:
  - Floor
  - Walls
  - Racks
  - Aisles
  - Intersections
  - Loading zones
- Create separate scenario layers for:
  - Head-on deadlock
  - Intersection bottleneck
  - Dynamic obstacle/anomaly
- Compose assets with USD references and scenario override layers instead of
  generating one flattened file.

### 3. TurtleBot3 Asset

- Import TurtleBot3 Burger from URDF once.
- Save it as a reusable, physics-ready USD asset.
- Configure:
  - Articulation
  - Differential drive
  - Wheel joints
  - Collision geometry
  - 2D lidar
  - Robot identification marker
- Instantiate multiple robots as `/World/Robots/robot_N`.

### 4. ROS 2 Integration

- Use `isaacsim.ros2.bridge` and ROS 2 OmniGraph nodes.
- Provide the following topics per robot:
  - `/robot_N/cmd_vel`
  - `/robot_N/odom`
  - `/robot_N/scan`
  - `/tf`
  - `/tf_static`
- Provide the following global topics:
  - `/clock`
  - `/camera/image_raw`
  - `/camera/camera_info`
- Keep ROS namespaces and TF frames unique.

### 5. VLM Observation

- Add a fixed overhead RGB camera covering the warehouse.
- Publish frames to the existing M1 perception pipeline.
- Attach visible ArUco markers to TurtleBots for ID tracking.
- Have M1 produce annotated images and robot state vectors for the VLM.
- Use simulator ground truth only for validation, not as VLM input.

### 6. Scenario Execution

- Define robot spawns, goals, timed obstacles, duration, and expected conflict
  in the scenario configuration.
- Use a standalone Isaac Sim runner to load the base scene and apply the
  selected scenario.
- Support:
  - Deterministic seeds
  - GUI and headless modes
  - Reset
  - Repetition

### 7. VLM Pipeline Under Test

```text
Isaac overhead camera
    -> ROS 2 image
    -> M1 perception and annotation
    -> VLM congestion reasoning
    -> RAG command grounding
    -> ROS 2 coordination command
    -> TurtleBot3 control in Isaac Sim
```

## Proposed USD Structure

```text
isaac/
├── assets/
│   ├── robots/
│   │   └── turtlebot3_burger.usd
│   └── warehouse/
│       ├── rack.usd
│       ├── loading_zone.usd
│       └── warehouse_base.usd
├── scenarios/
│   ├── head_on_deadlock.usd
│   ├── intersection_bottleneck.usd
│   └── dynamic_anomaly.usd
└── scripts/
    ├── import_turtlebot3.py
    ├── build_warehouse.py
    ├── build_scenario.py
    └── run_simulation.py
```

## Implementation Notes

### URDF Import and USD Composition

The URDF importer (`isaacsim.asset.importer.urdf`) produces a single flattened
USD during conversion. This does not conflict with the requirement to avoid
one flattened scene file. That requirement applies to scene composition.

Save the robot as one reusable USD asset and add it to scenes through USD
references.

### ROS 2 Bridge and Timeline

Publishers and subscribers from `isaacsim.ros2.bridge` are active only while
the timeline is playing. ROS 2 must be sourced before launch, unless the
lightweight libraries bundled with Isaac Sim are used.

The standalone runner must start playback before expecting ROS 2 topics and
must account for the timeline in reset and repetition logic.

### Per-Robot Namespacing

Each robot must own a ROS 2 Action/OmniGraph graph with an explicit namespace
and TF frame prefix. Unique `/robot_N/*` topics and TF frames are not created
automatically from the `/World/Robots/robot_N` prim path.

## Implementation Order

1. Import and validate one TurtleBot3 USD.
2. Control it through ROS 2 `/cmd_vel`.
3. Build the reusable warehouse.
4. Add the overhead camera and ROS image publishing.
5. Add multiple namespaced robots.
6. Implement the head-on scenario.
7. Connect M1 and validate ArUco tracking.
8. Connect VLM, RAG, and M4.
9. Add the other scenarios and headless repetition.

## First Acceptance Target

Two TurtleBot3 robots enter a narrow warehouse aisle, become blocked, appear
correctly in the overhead camera, are identified by M1, and can receive
separate ROS 2 velocity commands after a VLM decision.

## Current Repository Constraint

The premature simulation document is absent; no new documentation or runtime
code remains from that step.
