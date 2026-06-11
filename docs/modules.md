# Module Decomposition

Derived from `project_proposal.md`. The system is a two-layer hybrid architecture:
**Layer 1** = fast reactive local control (20–50 Hz), **Layer 2** = slow centralized
VLM+RAG semantic reasoning (0.5–2 Hz). Modules below map the proposal's pipeline
(Camera → Perception → VLM → RAG → ROS2 → Robots) onto independently developable units.

```
                 ┌─────────────────────────────────────────────┐
                 │  M6 Simulation & Evaluation (Gazebo/Webots)  │
                 └─────────────────────────────────────────────┘
   overhead cam │
                ▼
 ┌────────────┐   states   ┌──────────┐  JSON   ┌──────────┐ command ┌──────────┐
 │ M1         │──────────▶ │ M2       │───────▶ │ M3       │───────▶ │ M4       │
 │ Perception │ annotated  │ VLM      │ decision│ RAG      │ struct. │ ROS2     │
 │ & Tracking │  frame     │ Reasoning│         │ Grounding│ command │ Execution│
 └────────────┘            └──────────┘         └──────────┘         └──────────┘
        ▲                        ▲                    ▲                    │
        │                        └──── M5 Orchestrator (state machine) ───┤
        └──────────────────── ROS2 status feedback ──────────────────────┘
```

---

## M1 — Perception & Robot ID Tracking
**Proposal §4.2** | Layer 1 input

Turns raw overhead camera frames into per-robot world-frame state and a VLM-ready
annotated image.

- **M1.1 Camera & Calibration** — overhead RGB acquisition (15–30 FPS), checkerboard
  calibration, homography `H` mapping pixel `(u,v)` → world `(x_w, y_w)`.
- **M1.2 ArUco Detection** — `DICT_4X4_50` marker detection via
  `cv2.aruco.detectMarkers()`; corner→world transform through `H`.
- **M1.3 State Estimation** — maintain `s_i = (x, y, θ, v, ω, task, status)`;
  velocity via low-pass-filtered finite differences; task/status from M5.
- **M1.4 Scene Annotation** — Set-of-Mark overlays: status-colored bounding boxes
  (green/yellow/red), ID labels, velocity arrows, goal icons.

**Outputs:** robot state vectors, annotated frame. **Key deps:** OpenCV.

---

## M2 — VLM Semantic Reasoning
**Proposal §4.3** | Layer 2

Runs the Think–Act loop: analyzes the annotated scene + textual states, detects and
classifies congestion, recommends a strategy.

- **M2.1 Prompt Builder** — assemble structured scene-analysis prompt (image + state list).
- **M2.2 VLM Backend Adapter** — model-agnostic interface (VILA-1.5, NVIDIA Cosmos
  Reasoner, or other) behind a standardized API.
- **M2.3 Output Parser** — validate/parse JSON: `congestion_detected`, `type`
  {deadlock, bottleneck, crowding, anomaly}, `involved_robots`, `root_cause`,
  `strategy` {yield, reroute, convoy, priority_override, temporary_wait, reverse},
  `justification`.

**Outputs:** validated semantic decision (JSON). **Key deps:** VLM inference runtime.

---

## M3 — RAG Action Grounding
**Proposal §4.4** | Layer 2

Translates the VLM's semantic decision into a concrete, executable command.

- **M3.1 Knowledge Base** — curated coordination action templates (scenario
  description, strategy, parameterized command template, pre/post-conditions,
  priority rules).
- **M3.2 Embedding & Vector Store** — `all-MiniLM-L6-v2` embeddings in ChromaDB.
- **M3.3 Retrieval** — build query from (type, strategy, root_cause); top-k=3 cosine search.
- **M3.4 Grounding Generation** — LangChain chain instantiates retrieved template with
  concrete robot IDs/coords/params; emits structured command JSON
  (`command_id`, `actions[]`, `expected_resolution_time_sec`, `fallback`).

**Outputs:** structured ROS2 command. **Key deps:** LangChain, ChromaDB.

---

## M4 — ROS2 Execution & Safety
**Proposal §4.5** | Layer 1 / actuation

Dispatches commands and runs the per-robot client + safety enforcement.

- **M4.1 Command Bus** — custom messages on `/coordination/commands`,
  status on `/coordination/status`.
- **M4.2 Coordination Client Node** (per robot) — filter by ID, switch
  Nav2-autonomous ↔ coordinated mode, execute action (yield/proceed/etc.),
  report status, revert on completion/timeout.
- **M4.3 Local Nav Stack** — Nav2 + DWA local planner (baseline reactive Layer 1).
- **M4.4 Safety Monitor** — invariants: `d_min = 0.3 m`, `v_max = 0.2 m/s`,
  command timeout → stop-and-wait fallback.

**Outputs:** robot motion, execution status. **Key deps:** ROS2, Nav2, TurtleBot3.

---

## M5 — Orchestrator
**Proposal §4.1, §4.6** | Layer 2 controller

Central state machine implementing the "Layer 2 intervenes only when Layer 1 fails"
principle. Monitors congestion-timeout threshold, triggers M2→M3→M4 pipeline, tracks
command lifecycle, owns task/status registry feeding M1.3.

**Outputs:** pipeline triggering, task assignment. **Cross-cuts:** M1–M4.

---

## M6 — Simulation & Evaluation
**Proposal §5** | Isaac Sim test harness

- **M6.1 World & Robots** — Isaac Sim 6.0 + ROS2 Jazzy warehouse built with
  OpenUSD references and scenario layers. Reusable assets live under `isaac/`;
  the ROS-facing integration remains in `swarm_simulation`. The environment
  provides 1.2 m aisles, a 4-way intersection, loading zones, physics-ready
  TurtleBot3 Burger robots (v≤0.22 m/s, ω≤2.84 rad/s), per-robot lidar, and a
  fixed overhead RGB camera at 1280×960 and 30 Hz.
- **M6.2 Scenarios** — deterministic, repeatable head-on deadlock, intersection
  bottleneck, and dynamic anomaly scenarios. YAML is the source of truth;
  generated scenario USD layers reference the reusable warehouse and robot
  assets.
- **M6.3 Baselines** — APF, ORCA, CBS, and Asadi et al. (2025) CNN congestion-aware.
- **M6.4 Metrics & Logging** — throughput, waiting time, collision rate, energy,
  deadlock recovery time; ablations (VLM-only vs. VLM+RAG).

**Interfaces:** `/clock`, `/camera/image_raw`, `/camera/camera_info`,
`/robot_N/cmd_vel`, `/robot_N/odom`, `/robot_N/scan`, `/tf`, and `/tf_static`.
Robot namespaces and TF frames are unique.

**Outputs:** composed USD scenes, ROS2 simulation streams, validation-only
ground truth, benchmark results, and ablation analysis.

**Detailed spec:** [`docs/specs/module6_simulation.md`](specs/module6_simulation.md).

---

## Cross-cutting
- **C1 Interfaces/Schemas** — shared JSON schemas (state vector, VLM decision,
  structured command) so M1–M5 stay independently upgradeable.
- **C2 Config & Logging** — central config; traceable VLM justification + RAG
  retrieval provenance for interpretability (a stated contribution).

## Suggested build order
1. M6.1 sim world + M4.3 Nav2 baseline (movement working).
2. M1 perception on simulated camera.
3. M5 orchestrator skeleton + C1 schemas.
4. M2 VLM (start with one backend) → M3 RAG.
5. M4.2/M4.4 coordination client + safety; close the loop.
6. M6.2–M6.4 scenarios, baselines, metrics, ablations.
