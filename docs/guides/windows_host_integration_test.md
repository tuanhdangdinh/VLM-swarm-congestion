# Windows Host Agent Guide: M6 to M2 Integration Test

**Purpose:** run the first defensible capstone integration test on the Windows
Isaac Sim host:

```text
Isaac Sim M6 -> ROS 2 topics -> M1 perception -> M5 trigger -> M2 decision
```

This test is intentionally scoped to prove that simulated assets, ROS 2 Jazzy,
M1 perception, M5 orchestration, and the M2 VLM decision backend work together.
It does not require M3 grounding, M4 execution, or Nav2 to be complete.

## Pass Criteria

The run passes only when all of these are true:

- Isaac Sim 6.0 starts the `head_on_deadlock` scenario on the Windows host.
- ROS 2 Jazzy sees the Isaac camera topics.
- M1 publishes non-empty robot detections for `robot_1` and `robot_2` on
  `/perception/scene_state`.
- M1 publishes `/perception/annotated_frame`.
- M5 accepts a manual trigger on `/orchestrator/trigger_analysis`.
- M5 writes `data/logs/m5_decisions/<analysis_id>.json`.
- The decision artifact contains an M2 decision for `robot_1` and `robot_2`,
  preferably with `decision.type` equal to `deadlock`.

Expected current terminal stage is usually `grounding`, because M3 grounding is
still a stub. That is acceptable for this test if the artifact contains the M2
decision.

## Required Local Context

Read these files before running commands:

- `docs/guides/run_isaac_sim_with_m1.md`
- `isaac/config/scenarios/head_on_deadlock.yaml`
- `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`
- `scripts/build_ros2.sh`
- `scripts/run_simulation.ps1`
- `scripts/run_perception.sh`
- `scripts/run_orchestrator.sh`

The orchestrator config must target:

```yaml
reasoning_backend_id: openai
initial_tasks:
  robot_1: { task: cross_narrow_aisle, goal: [3.0, 0.0] }
  robot_2: { task: cross_narrow_aisle, goal: [-3.0, 0.0] }
```

## Host Assumptions

- Windows 10 or 11 runs Isaac Sim 6.0 natively with the NVIDIA GPU.
- WSL2 Ubuntu runs ROS 2 Jazzy, the ROS 2 workspace, M1, M5, and ROS 2 CLI
  checks.
- The repo is available both from Windows PowerShell for Isaac Sim commands and
  from WSL2 for ROS 2 commands. This can be one shared checkout under
  `/mnt/c/...`, or two synchronized checkouts.
- All Isaac Sim assets are generated on the Windows host.
- Isaac Sim publishes ROS 2 topics from Windows; WSL2 consumes them.

Use Windows PowerShell only for Isaac Sim/M6 commands. Use WSL2 Ubuntu terminals
for build, M1, M5, ROS 2 topic checks, trigger calls, and evidence collection.

## Environment Setup

Set these on Windows PowerShell for Isaac Sim:

```powershell
$env:ISAAC_SIM_ROOT = "C:\path\to\isaac-sim-6.0.0"
$env:ROS_DOMAIN_ID = "0"
```

Check Windows tools:

```powershell
Test-Path "$env:ISAAC_SIM_ROOT\python.bat"
nvidia-smi
```

Set these in WSL2 Ubuntu:

```bash
export ROS_DOMAIN_ID=0
export OPENAI_API_KEY="sk-..."
source /opt/ros/jazzy/setup.bash
```

Check WSL2 tools:

```bash
test -f /opt/ros/jazzy/setup.bash
ros2 --version
```

If `OPENAI_API_KEY` is not available, switch only for a dry plumbing test by
temporarily setting `reasoning_backend_id: mock` in
`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`. Do not claim an M2
hosted VLM pass from a mock run.

A mock run also produces a **different decision artifact** than the one in
[Evidence Collection](#evidence-collection), because `MockBackend` returns a
fixed no-congestion decision by default. Do not treat these mock values as a
failure of the plumbing — they are expected:

```json
{
  "terminal_stage": "vlm",
  "grounded_command_present": false,
  "decision": {
    "congestion_detected": false,
    "type": "none",
    "involved_robots": []
  },
  "diagnostics": {
    "backend_id": "mock"
  }
}
```

Note `terminal_stage` is `vlm` (the pipeline stops at M2 because
`congestion_detected` is false), not `grounding`, and `decision.type` is `none`.
A mock run only proves M6 -> M1 -> M5 -> M2 transport and artifact writing; it
does not prove M2 produced a `deadlock` decision from the live scene.

## One-Time Build

Build the ROS 2 workspace:

```bash
source /opt/ros/jazzy/setup.bash
./scripts/build_ros2.sh
```

If the build fails because Python packages are missing, install the project
requirements in the Python environment used by ROS 2, then rerun the build. Do
not switch to Humble; this project expects Jazzy.

## One-Time Isaac Asset Generation

Generate or refresh all M6 assets on the Windows host. If these already exist,
still validate them before the integration run.

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.build_warehouse
```

If the TurtleBot3 USD asset is missing, import it from the local TurtleBot3
Burger URDF:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.import_turtlebot3 `
  --urdf C:\path\to\turtlebot3_burger.urdf `
  --output-dir isaac\assets\robots
```

Build the test scenario:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.build_scenario `
  --config isaac\config\scenarios\head_on_deadlock.yaml
```

Validate the scenario:

```powershell
& "$env:ISAAC_SIM_ROOT\python.bat" -m isaac.scripts.validate_simulation `
  --scenario isaac\scenarios\head_on_deadlock.usd
```

Do not continue until validation passes.

## Run Procedure

Use one Windows PowerShell terminal and three WSL2 Ubuntu terminals from the
repo root.

### Terminal A: Isaac Sim M6

```powershell
.\scripts\run_simulation.ps1 `
  --scenario head_on_deadlock `
  --seed 42 `
  --duration-sec 45 `
  --topic-timeout-sec 30
```

GUI mode is preferred for this acceptance run so the agent can visually confirm
that `robot_1` and `robot_2` enter the narrow aisle head-on. Use `--headless`
only after GUI mode has worked.

Leave this terminal running.

### Terminal B: M1 Perception (WSL2)

```bash
export ROS_DOMAIN_ID=0
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
./scripts/run_perception.sh --isaac-sim
```

This disables the hardware camera node and consumes Isaac Sim's
`/camera/image_raw`.

Leave this terminal running.

### Terminal C: M5 Orchestrator (WSL2)

```bash
export ROS_DOMAIN_ID=0
export OPENAI_API_KEY="sk-..."
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
./scripts/run_orchestrator.sh
```

Wait for the node to start without backend/config errors. The config uses
OpenAI by default, so missing `OPENAI_API_KEY` should be treated as a setup
failure for the real acceptance run.

Leave this terminal running.

### Terminal D: ROS 2 Checks and Trigger (WSL2)

Load ROS 2 and the workspace into this terminal:

```bash
export ROS_DOMAIN_ID=0
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
```

List the required topics:

```bash
ros2 topic list
```

Required upstream topics:

```text
/camera/image_raw
/camera/camera_info
/clock
```

Required M1 topics:

```text
/perception/scene_state
/perception/annotated_frame
```

Check one camera frame:

```bash
ros2 topic echo /camera/image_raw --field header --once
```

Check one M1 scene state:

```bash
ros2 topic echo /perception/scene_state --field data --once
```

The scene state must include both `robot_1` and `robot_2`. If it is empty, wait
until the robots enter the camera region and try again. If it remains empty,
stop and troubleshoot M6 marker visibility or M1 ArUco calibration.

Check one annotated frame:

```bash
ros2 topic echo /perception/annotated_frame --field header --once
```

Trigger M5 manually:

```bash
ros2 service call /orchestrator/trigger_analysis \
  swarm_interfaces/srv/TriggerCongestionAnalysis \
  "{reason: 'windows host capstone m6_m1_m5_m2'}"
```

Expected response:

```text
accepted: true
analysis_id: "<non-empty id>"
message: "analysis started"
```

Save the `analysis_id`.

## Evidence Collection

After the trigger completes, inspect the decision artifact:

```bash
analysis_id="<paste analysis_id here>"
artifact="data/logs/m5_decisions/${analysis_id}.json"
test -f "$artifact"
cat "$artifact"
```

The JSON must include:

```json
{
  "request_id": "<analysis_id>",
  "terminal_stage": "grounding",
  "grounded_command_present": false,
  "decision": {
    "congestion_detected": true,
    "type": "deadlock",
    "involved_robots": ["robot_1", "robot_2"]
  },
  "diagnostics": {
    "backend_id": "openai"
  }
}
```

Exact wording in `root_cause`, `strategy`, and `justification` may vary. The
important evidence is that M2 produced a structured decision from the live M1
annotated frame and scene state.

Also collect the M6 run directory:

```bash
ls -la data/logs/simulation
```

Keep the directory matching `head_on_deadlock` and seed `42`; it contains the
simulation manifest and ground-truth log.

## Failure Triage

### Isaac Sim does not start

Check:

```powershell
Test-Path "$env:ISAAC_SIM_ROOT\python.bat"
nvidia-smi
```

Then rerun `validate_simulation`. Do not debug M1 or M5 until M6 launches.

### ROS 2 topics are missing

Check that Windows PowerShell and every WSL2 terminal use the same domain.

Windows:

```powershell
echo $env:ROS_DOMAIN_ID
```

WSL2:

```bash
echo "$ROS_DOMAIN_ID"
```

Restart Terminal A after changing `ROS_DOMAIN_ID`; Isaac Sim reads the domain at
process startup.

### M1 scene state is empty

Check:

```bash
ros2 topic hz /camera/image_raw
ros2 topic echo /perception/scene_state --field data --once
```

Likely causes:

- Scenario robots are not in the overhead camera view yet.
- ArUco marker assets were not generated or attached to the robots.
- M1 `aruco.yaml` marker size/dictionary does not match generated markers.
- Calibration is stale; regenerate with `python -m isaac.scripts.export_calibration`
  and rebuild ROS 2.

### M5 rejects the trigger

If the response says no scene snapshot is available, M5 has not received M1
data. Confirm `/perception/scene_state` is publishing before triggering.

If the response says the trigger is rejected because analysis is already active,
wait for the previous request to finish or restart M5 for a clean run.

### No decision artifact appears

Check Terminal C for:

```text
decision artifact written: data/logs/m5_decisions/<id>.json
```

If OpenAI failed, confirm:

```bash
test -n "$OPENAI_API_KEY"
```

Then rerun M5 and trigger again. A missing artifact means the test did not prove
M2 completion.

## Final Report Format

When reporting back, include:

- Git commit or branch name used.
- Isaac Sim version and `ISAAC_SIM_ROOT`.
- WSL2 Ubuntu version and ROS 2 Jazzy path `/opt/ros/jazzy`.
- Scenario: `head_on_deadlock`, seed `42`.
- Whether `/camera/image_raw`, `/perception/scene_state`, and
  `/perception/annotated_frame` were observed.
- Trigger response, including `analysis_id`.
- Path to `data/logs/m5_decisions/<analysis_id>.json`.
- The artifact fields: `terminal_stage`, `decision.congestion_detected`,
  `decision.type`, `decision.involved_robots`, and `diagnostics.backend_id`.

Do not mark the integration test passed without the decision artifact.
