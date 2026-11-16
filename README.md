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

## History and archived lines

In November 2026, `main` was consolidated from `integration/2026-11`. That
branch merged the November branches by frozen SHA, as they stood. The merges
are not a record of review: a branch's presence in `main` does not mean its
content was re-checked during the consolidation. Every safety and grounding
mechanism that came in with these merges stays default-off. Each one turns on
only through an explicit config key or overlay fragment.

Reference points:

- `prereg-v3-pin` (`68e67b5`): the evaluated runtime pin, and the base that
  `integration/2026-11` was cut from.
- `archive/main-2026-09-19` (`f2ca3c6`): `main` before the 2026-11
  consolidation.
- The thesis report lives on the unmerged `docs/thesis` branch and at tag
  `thesis-long-2026-11-15`. The run evidence is in GitHub release
  `evidence-2026-11-16`.

The lines below were not merged. Each one is kept as an annotated
`archive/<branch>` tag, and the branches themselves were not deleted.

| Tag | Tip | What the line held |
|---|---|---|
| `archive/prereg-v1-hotfix` | `3988524` | v1 confirmatory driver: reasoner transport hotfixes F01/F02, an in-loop stop flag for aborted Isaac runs, and a clean `fc_launch` recorder stop |
| `archive/feat/v3-vjepa-probe` | `53a4b78` | V-JEPA 2 probe pilot: frozen config, results, dataset card and the Rev 2 corrected static control |
| `archive/feat/trail-probe-pilot` | `cb1c171` | Trail-on probe pilot: a pre-registered decision rule and a null report (not registered) |
| `archive/feat/prereg-v2-composite` | `dd5f93c` | VM recorder fix: stop the `fc_launch` recorder cleanly before cleanup, on the v2 composite |
| `archive/feat/robot-order-counterbalance` | `d20cc97` | Pre-registration of the robot-order counterbalance experiment |
| `archive/m1-isaac-camera-wiring` | `8e8e1ca` | M1 Isaac camera wiring spec and plan consistency fixes (docs only) |
| `archive/claude/laughing-volta-fwnqvs` | `df720f0` | Repository audit report, including finding A15 on stale Nav2 spawn offsets (remote-only branch) |
| `archive/wip/untracked-local-state` | `4224645` | Weekly progress reports for weeks 1–6 and a `uv.lock` snapshot from the local workspace |
| `archive/worktree-m4-phase2-nav2-stack` | `bb22915` | June 2026 M4 Phase 2 Nav2 stack line: per-robot Jazzy bringup, RTX lidar scan, static map and TF, DWB and costmap fixes, aisle barrier |
| `archive/probe/shutdown-timing` | `8da4964` | Shutdown-timing probe report; its content is already contained elsewhere, so the tag only keeps it findable |
| `archive/wip/m4-watchdog-forward-stop-2026-06` | `fd71c12` | Uncommitted June cmd_vel watchdog forward-stop and Nav2 parameter changes, committed on top of `bb22915` to preserve them |
