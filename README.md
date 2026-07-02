# VGU VLM Swarm

ROS2 + VLM/RAG research scaffold for warehouse swarm coordination.

The architecture separates fast local robot control from a slower semantic reasoning
layer:

- `ros2_ws/` contains ROS2 packages for interfaces, perception, orchestration,
  execution, and simulation.
- `reasoning/` contains Python-only VLM and RAG logic that can be tested outside ROS2.
- `benchmarks/` contains baseline planners, metrics, runners, and experiment outputs.
- `config/` centralizes model, robot, RAG, logging, and DDS configuration.
- `data/` stores calibration inputs, knowledge-base content, vector stores, and logs.
- `docs/` contains proposal and module-level design notes.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Local VLM Server

To run Cosmos Reason2 locally on Apple Silicon with the llama.cpp foreground
vision server, use:

```bash
make run-llama-server
```

See [docs/guides/run_local_llama_server.md](docs/guides/run_local_llama_server.md)
for setup, overrides, smoke tests, and troubleshooting.

ROS2 workflows are expected to run inside a ROS2 Jazzy environment:

```bash
./scripts/build_ros2.sh
./scripts/run_simulation.sh
```
