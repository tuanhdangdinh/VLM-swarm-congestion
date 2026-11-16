# VGU VLM Swarm

Research code for warehouse multi-robot congestion resolution with a vision-language
model (VLM) in the loop, run in simulation (Isaac Sim + ROS2 Jazzy + Nav2).

The system has two layers:

- **Fast layer (20–50 Hz):** each robot runs Nav2 locally; M4 dispatches commands and
  enforces the safety limits.
- **Coordination layer (0.5–2 Hz):** M1 turns the overhead camera frame into robot
  states, M2 (VLM) reads the scene and names the congestion and a strategy, M3
  grounds that decision into concrete per-robot commands, and M5 runs the pipeline.

| Module | What it does | Code |
|---|---|---|
| M1 Perception | Overhead camera → ArUco → robot states + annotated frame | `ros2_ws/src/swarm_perception` |
| M2 VLM reasoning | Prompt building, backend adapters, output parsing | `reasoning/vlm` |
| M3 Action grounding | Decision → per-robot commands (rules + retrieval) | `reasoning/rag` |
| M4 Execution & safety | Command dispatch, Nav2 client, safety invariants | `ros2_ws/src/swarm_execution` |
| M5 Orchestrator | State machine, task registry, M2→M3→M4 trigger | `ros2_ws/src/swarm_orchestrator` |
| M6 Simulation | Isaac Sim scenes, ground-truth logging, ROS2 launch | `isaac/vgu_sim`, `ros2_ws/src/swarm_simulation` |

## Repository Layout

- `ros2_ws/` — ROS2 packages (interfaces, perception, orchestrator, execution, simulation).
- `reasoning/` — Python-only M2/M3 code, testable without ROS2.
- `isaac/` — Isaac Sim runtime: scene builder, scenarios, runner (`isaac/scripts/run_simulation.py`).
- `config/` — central configuration, including the opt-in overlay fragments in
  `config/safety/`, `config/grounding/` and `config/gt/`.
- `benchmarks/` — baselines, metrics, scoring and the offline VLM bench.
- `scripts/` — shell helpers, VM launchers and offline analysis scripts.
- `data/experiments/` — frozen experiment inputs and results cited by the reports.
- `docs/` — specs, plans, reports and the implementation log (see below).
- `research_notes/` — literature notes collected during the project.
- `tests/` — `unit/` (offline), `integration/` (ROS2), `simulation/` (scenarios).

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make test      # plain pytest
make lint      # ruff
```

The unit suite has known failures, the same set on `main` as at the evaluated pin (62 failed, plus 3 collection
errors for tests that need Isaac Sim's `pxr`). Use `pytest --continue-on-collection-errors`
outside Isaac Sim, and compare failing test IDs, not counts, when checking a change.

ROS2 workflows run inside a ROS2 Jazzy environment:

```bash
make build-ros2
make run-simulation
```

Guides in `docs/guides/`: Isaac Sim with M1 (`run_isaac_sim_with_m1.md`), M1
perception (`run_m1_perception.md`), a local llama.cpp VLM server
(`run_local_llama_server.md`, `make run-llama-server`), hardware setup, the demo
panel video, and the naming glossary.

## Safety and Grounding Mechanisms

Every mechanism added after the evaluated pin is **off by default**. Each turns on
only through its config key or an overlay fragment, so a default run matches the
evaluated configuration. `ros2_ws/src/swarm_execution/config/safety.yaml` is unchanged
from the pin.

| Mechanism | Key |
|---|---|
| Scoped clearing exemption | `scoped_clearing_exemption` |
| M4 stall abort | `safety.stall_abort.enabled` |
| Escort / reverse obstacle guards | `escort_obstacle_guard`, `reverse_obstacle_guard` |
| Plan/dispatch mismatch record | `plan_dispatch_mismatch_visibility` |
| Hold queued crossers / counter-flow yielder swap | `grounding_hold_queued_crossers`, `grounding_yield_counterflow_swap` |
| Plan-grammar prompt rules | `prompt_plan_grammar_rules`, `prompt_plan_grammar_release_rule` |
| Offer groundable strategies / refusal feedback | `prompt_offer_groundable_strategies`, `refusal_feedback.enabled` |
| Per-cluster shadow | `per_cluster_shadow.enabled` |
| Ground-truth contact logging | `gt_contact_logging.enabled` (`run_simulation.py --gt-config`) |

Validation status of each one is recorded in `docs/reports/2026-11-15-session-wrap-up.md`
and `docs/implementation_notes.md`.

## Where to Read

- `docs/implementation_notes.md` — the living implementation log: dated facts,
  fixes, gotchas, newest first per module.
- `docs/reports/` — one report per investigation or experiment;
  `docs/reports/2026-11-15-session-wrap-up.md` indexes the November results with
  their evidence grade.
- `docs/superpowers/specs/` — designs and pre-registrations (`prereg-v1`, v2, v3);
  `docs/superpowers/plans/` — task-level plans.
- `docs/modules.md`, `docs/project_proposal.md` — module decomposition and proposal.
- The thesis report is on the `docs/thesis` branch (not merged into `main`).
- Run bundles and videos are in GitHub release `evidence-2026-11-16`.

All results are from simulation unless a report says otherwise.

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
