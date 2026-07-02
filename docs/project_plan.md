# Project Plan

Milestone-based semester plan for the ROS2 + VLM/RAG warehouse swarm robotics
project.

## 1. Purpose

This document turns the research proposal and module decomposition into an
implementation roadmap. It is written for two audiences:

- **Academic review:** shows how the proposed methodology will become an
  evaluable research prototype.
- **Engineering work:** defines milestone deliverables, dependencies,
  acceptance criteria, and risks for implementation.

Primary source documents:

- `docs/project_proposal.md` — research motivation, methodology, and evaluation
  goals.
- `docs/modules.md` — system module decomposition.
- `docs/codespace_file_structure.md` — repository layout.
- `docs/specs/module1_perception.md` — detailed M1 perception specification.
- `docs/specs/module2_vlm_reasoning.md` — detailed M2 VLM reasoning
  specification.

## 2. Success Definition

The project succeeds when it demonstrates a working hybrid swarm coordination
loop in simulation:

1. Multiple simulated robots navigate a warehouse-like environment using ROS2.
2. The perception layer produces robot state and annotated scene observations.
3. The orchestrator detects when local navigation is insufficient and triggers
   semantic reasoning.
4. The VLM layer emits valid congestion decisions.
5. The RAG layer grounds decisions into structured coordination commands.
6. ROS2 execution applies those commands with safety checks.
7. Benchmark scenarios report throughput, waiting time, collision rate, energy,
   and deadlock recovery time.

The final academic output should be able to compare the proposed VLM+RAG
intervention loop against classical or baseline coordination strategies.

## 3. Current State

The repository currently contains:

- A ROS2 workspace scaffold under `ros2_ws/src/`.
- ROS2 packages for interfaces, perception, orchestration, execution, and
  simulation.
- A Python-only semantic reasoning package under `reasoning/`.
- JSON schemas for robot state, VLM decisions, and coordination commands.
- Benchmark, config, data, script, and test directories.
- Draft module specs for M1 and M2.
- Git repository initialized on branch `main`.

Important current limitations:

- ROS2 build has not been verified on the local machine because ROS2 Jazzy is
  not available there.
- M1 and M2 have detailed specs, but M3-M6 still need detailed specs.
- Most source files are scaffolds or placeholders, not complete behavior.
- The benchmark runners and simulation scenarios are not yet executable.

## 4. Milestone Roadmap

### Milestone 1 — Repository and ROS2 Foundation

**Goal:** Make the scaffold buildable and usable in a ROS2 Jazzy environment.

Deliverables:

- Verify `.devcontainer/` can build a ROS2 Jazzy workspace.
- Confirm `ros2_ws/src/swarm_interfaces` builds message and service types.
- Confirm Python packages install cleanly.
- Establish standard commands through `Makefile` and `scripts/`.

Acceptance criteria:

- `colcon build --symlink-install` completes in the ROS2 environment.
- `python -m compileall reasoning benchmarks tests` completes.
- Python schema validation passes for all JSON schemas.
- Repository status remains clean after build artifacts are ignored.

Dependencies:

- ROS2 Jazzy.
- Colcon.
- Python 3.10+.

### Milestone 2 — Simulation Baseline and Robot Movement

**Goal:** Create a minimal warehouse simulation where robots can move before
semantic reasoning is added.

Deliverables:

- Functional warehouse world or equivalent simulation scene.
- TurtleBot3-compatible robot model setup.
- Basic map and launch flow.
- Initial Nav2 or baseline movement path for at least two robots.

Acceptance criteria:

- Simulation launch starts without errors.
- Robots spawn with unique namespaces or IDs.
- At least two robots can execute simple navigation goals.
- Robot state can be observed through ROS2 topics.

Dependencies:

- M1/M4 later depend on this simulation for integration testing.
- Map and robot coordinate conventions must be stable before perception and
  execution code rely on them.

### Milestone 3 — Perception and Tracking Pipeline

**Goal:** Implement M1 so the system can observe robot positions and produce a
VLM-ready annotated frame.

Deliverables:

- Frame-source abstraction for simulated and future hardware cameras.
- Calibration artifact loading.
- ArUco detection using `DICT_4X4_50`.
- Pixel-to-world homography transform.
- Robot state estimation with velocity and status labels.
- Scene annotation with IDs, status colors, velocity arrows, and goal markers.

Acceptance criteria:

- Detected robot IDs remain stable across test runs.
- Reported positions are within the chosen tolerance of simulator ground truth.
- Missing markers are marked stale rather than silently dropped.
- `SceneState` output conforms to the shared schema.
- Annotated frames match the same timestamp as the state output.

Dependencies:

- Uses `docs/specs/module1_perception.md` as the implementation reference.
- Requires simulation camera output or a recorded frame source.

### Milestone 4 — Orchestrator and Shared Contracts

**Goal:** Implement M5 and stabilize the cross-module interfaces.

Deliverables:

- Finalize ROS2 messages and JSON schemas for robot state, VLM decisions, and
  coordination commands.
- Implement congestion trigger policy based on waiting time, local navigation
  failure, or stopped robots.
- Implement task/status registry.
- Implement command lifecycle states: pending, active, completed, failed, and
  timed out.

Acceptance criteria:

- Orchestrator receives perception state.
- Orchestrator triggers reasoning only after the configured congestion threshold.
- Request IDs correlate perception input, VLM decision, RAG command, and
  execution status.
- Invalid or stale inputs are rejected with diagnostics.

Dependencies:

- Requires M1 state output.
- Provides trigger and task/status input to M2 and M4.

### Milestone 5 — VLM Reasoning Integration

**Goal:** Implement M2 as a model-agnostic congestion decision service.

Deliverables:

- Deterministic prompt builder from scene state and annotated frame.
- Backend interface for local or hosted VLMs.
- At least one working backend implementation or mockable test backend.
- JSON extraction and schema validation.
- Retry or re-ask path for invalid model output.
- Diagnostics for backend, latency, parse status, and request ID.

Acceptance criteria:

- Valid model output is parsed into a schema-valid decision.
- Invalid JSON or invalid enums do not reach M3.
- Hallucinated robot IDs are rejected or corrected according to the parser
  policy.
- `congestion_detected=false` is handled as a valid outcome with no M3 command
  request.

Dependencies:

- Uses `docs/specs/module2_vlm_reasoning.md` as the implementation reference.
- Requires stable M1 and M5 contracts.

### Milestone 6 — RAG Command Grounding

**Goal:** Implement M3 so semantic decisions become concrete executable commands.

Deliverables:

- Detailed M3 specification.
- Coordination template knowledge base.
- Embedding and vector-store indexing flow.
- Retrieval query based on congestion type, strategy, and root cause.
- Command grounding into structured command JSON.
- Validation against `coordination_command.schema.json`.

Acceptance criteria:

- Each supported strategy maps to at least one reusable command template.
- Grounded commands include concrete robot IDs and action parameters.
- Invalid or incomplete grounded commands fail validation before ROS2 execution.
- Retrieval provenance is logged for interpretability.

Dependencies:

- Requires M2 decision output.
- Feeds M4 command dispatch.

### Milestone 7 — ROS2 Execution and Safety Loop

**Goal:** Implement M4 so commands affect robot behavior while preserving safety.

Deliverables:

- Command bus on ROS2 topics.
- Per-robot coordination client node.
- Nav2 adapter for reroute or waypoint-based actions.
- Safety monitor enforcing minimum distance, maximum velocity, and timeout
  fallback.
- Execution status reporting back to M5.

Acceptance criteria:

- Robots filter commands by robot ID.
- Supported actions execute in simulation: yield, temporary wait, reroute, and
  reverse at minimum.
- Command timeout triggers stop-and-wait fallback.
- Execution status closes the command lifecycle in M5.

Dependencies:

- Requires M3 command output.
- Requires simulation baseline and stable robot namespaces.

### Milestone 8 — Benchmark Scenarios and Final Evaluation

**Goal:** Produce measurable evidence for the proposed architecture.

Deliverables:

- Executable scenarios for head-on deadlock, intersection bottleneck, and
  dynamic anomaly.
- Baseline strategies for comparison.
- Metric collectors for throughput, waiting time, collision rate, energy, and
  deadlock recovery.
- Experiment runner and result output format.
- Final result tables and plots for the report.

Acceptance criteria:

- Each scenario can run repeatedly with configurable fleet sizes.
- Results are written to `benchmarks/results/`.
- Metrics are computed consistently across baseline and VLM+RAG runs.
- Final evaluation supports the claims in the project proposal.

Dependencies:

- Requires the full M1-M5-M4 loop.
- Requires stable scenario configuration and logging.

## 5. Module Deliverables

| Module | Main Deliverable | Planning Status | Implementation Status |
| --- | --- | --- | --- |
| M1 Perception & Tracking | Robot state + annotated frame | Detailed spec exists | Scaffold only |
| M2 VLM Reasoning | Validated congestion decision | Detailed spec exists | Scaffold only |
| M3 RAG Grounding | Executable command JSON | Needs detailed spec | Scaffold only |
| M4 ROS2 Execution & Safety | Robot command execution | Needs detailed spec | Scaffold only |
| M5 Orchestrator | Trigger and lifecycle state machine | Needs detailed spec | Scaffold only |
| M6 Simulation & Evaluation | Scenarios, baselines, metrics | Needs detailed spec | Scaffold only |
| C1 Interfaces/Schemas | Shared contracts | Initial schemas exist | Needs ROS2/schema alignment |
| C2 Config & Logging | Traceable runtime configuration | Initial config exists | Needs integration |

## 6. Testing Strategy

Unit tests:

- Schema validation.
- VLM output parsing.
- Command validation.
- Homography and state estimation.
- Congestion trigger policy.
- Metric calculations.

Integration tests:

- Perception output to VLM prompt.
- VLM decision to RAG command.
- RAG command to ROS2 command bus.
- Command lifecycle from M5 to M4 and back.

Simulation tests:

- Head-on deadlock recovery.
- Intersection bottleneck resolution.
- Dynamic anomaly response.
- Safety fallback on command timeout.
- Multi-robot scalability for fleet sizes 4, 8, 12, and 16 where practical.

Acceptance tests:

- End-to-end demo run from simulation launch to benchmark result output.
- All emitted decisions and commands are schema-valid.
- No malformed model output reaches execution.
- Safety monitor prevents unsafe command execution.

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| ROS2/Gazebo setup instability | Blocks simulation and integration | Use devcontainer as the canonical environment; verify Milestone 1 first |
| VLM runtime unavailable or too slow | Blocks real semantic reasoning | Keep backend interface model-agnostic; use mock backend until runtime is ready |
| VLM hallucinated robot IDs or invalid JSON | Unsafe or invalid commands | Enforce schema validation and referential integrity before M3 |
| RAG retrieves wrong template | Incorrect action grounding | Log retrieval provenance and validate grounded commands before ROS2 dispatch |
| Perception calibration error | Wrong robot positions and bad reasoning | Test homography against simulator ground truth before VLM integration |
| Scope pressure near evaluation | Incomplete benchmark story | Prioritize one complete scenario before expanding to all scenarios |
| Safety failure during execution | Collision or unrealistic behavior | Implement M4 safety monitor before full autonomous command execution |

## 8. Final Semester Outcomes

Minimum acceptable outcome:

- ROS2 simulation runs.
- Perception or simulated state source provides robot states.
- VLM reasoning can be exercised with a mock or real backend.
- RAG produces validated command JSON.
- At least one congestion scenario produces benchmark output.

Target outcome:

- Full M1-M5-M2-M3-M4 loop runs in simulation.
- Three benchmark scenarios are executable.
- At least two baseline strategies are compared against VLM+RAG.
- Evaluation tables support the project proposal's research claims.

Stretch outcome:

- Real VLM backend integrated in addition to mock backend.
- Multiple fleet sizes are evaluated.
- Ablation compares VLM-only, RAG-only/template-only, and VLM+RAG variants.
- Final report includes qualitative reasoning traces and quantitative metrics.
