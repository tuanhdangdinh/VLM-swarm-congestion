# Hardware Setup Guide

**Prepared:** 2026-06-11

**Revision history:**
- Initial draft: hardware inventory, placement requirements, and network setup for running the VGU VLM Swarm stack on physical robots.

---

## Overview

This guide lists the physical hardware and network configuration required to run
the VGU VLM Swarm stack end-to-end on real robots. The software stack is tuned
to specific hardware — the configs below drive those assumptions.

> **Current software status:** Only M1 Perception is fully implemented.
> M3 (RAG), M4 (Nav2 dispatch), and M5 (Orchestrator) are scaffolds.
> A hardware-only M1 demo (camera → robot states) is runnable today.
> Full autonomous swarm coordination requires M3–M5 to be completed first.

---

## Device summary

| Device | Qty | Role |
|---|---|---|
| TurtleBot3 Burger | 2–4 | Physical robots carrying ArUco markers |
| Overhead RGB camera | 1 | M1's only sensor; ceiling-mounted nadir |
| ROS 2 / coordination host | 1 | Runs M1, M4, M5 (Linux, Ubuntu 24.04) |
| VLM compute host | 1 | Runs Cosmos Reason2 via llama-server (NVIDIA GPU) |
| Network switch / router | 1 | Connects all devices on the same LAN |

The ROS 2 host and VLM host can be the same machine if the GPU machine runs
Ubuntu 24.04.

---

## 1. Robots — TurtleBot3 Burger

From `isaac/config/robot.yaml`:

| Parameter | Value |
|---|---|
| Wheel radius | 0.033 m |
| Wheel separation | 0.160 m |
| Max linear velocity | 0.22 m/s |
| Max angular velocity | 2.84 rad/s |

Each Burger carries a **Raspberry Pi** + **OpenCR** control board and connects
to ROS 2 over Wi-Fi. No modification to the robot is required except mounting
the ArUco marker (§3).

**Minimum count by scenario:**

| Scenario | Robots needed |
|---|---|
| Head-on deadlock | 2 |
| Intersection bottleneck | 4 |
| Dynamic anomaly | 2 (+ manual obstacle) |

---

## 2. Overhead camera

From `config/camera.yaml`: the perception node expects **1280 × 960 RGB at 30 fps**
over topic `/camera/image_raw`.

**Mounting requirements:**
- Position: ceiling-mounted, **nadir (straight down)**, no tilt.
- Height: ~3.0 m above the ground plane (matches the Isaac Sim camera model and
  the analytic calibration in `ros2_ws/src/swarm_perception/config/calibration.yaml`).
- Field of view: must cover the **6.0 m × 4.5 m** conflict zone centered at
  (0, 0) in world frame. At 3.0 m height, an ~106° diagonal FOV covers this.
- Connection: USB 3.0 to the ROS 2 host, or GigE if a long cable run is needed.

**Compatible cameras (examples):**

| Camera | Interface | Notes |
|---|---|---|
| Logitech C920 / C930e | USB 3.0 | Inexpensive; 1080p capable |
| FLIR Blackfly S (BFS-U3) | USB 3.0 | Industrial; better lens options |
| Basler ace 2 | GigE | For long cable runs (> 3 m) |

Any USB or GigE camera that publishes via `usb_cam` or `camera_ros` at the
required resolution and frame rate is compatible.

---

## 3. ArUco markers

From `config/aruco.yaml`:

| Parameter | Value |
|---|---|
| Dictionary | `DICT_4X4_50` |
| Physical size | **0.08 m** (80 mm per side) |
| Placement | Flat, horizontal, top of each robot |
| Marker IDs | One unique ID per robot (e.g. 0–3) |

**Printing and mounting:**
- Print on matte white paper or rigid foam board; avoid glossy surfaces that
  cause glare.
- Each black border cell should be ≥ 4 px at the camera resolution — at 3.0 m
  height and 640 px focal length, an 80 mm marker spans ~17 px/cell, well above
  the minimum.
- Mount flat on the robot's top plate with the marker fully visible from above
  and not obscured by the LiDAR.

> **Note:** The Isaac Sim scenario config uses 0.12 m markers. If you use the
> same URDF or USD for both sim and hardware, reconcile this to 0.08 m before
> printing.

---

## 4. ROS 2 / coordination host

| Requirement | Minimum |
|---|---|
| OS | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy |
| CPU | 4-core (for M1 + M5 nodes at 30 Hz) |
| RAM | 8 GB |
| Network | Gigabit Ethernet or 5 GHz Wi-Fi |

This machine runs:
- `PerceptionNode` (M1) — processes camera frames at 30 Hz
- `OrchestratorNode` (M5) — state machine, task registry
- `CommandBusNode` (M4) — Nav2 dispatch to each TurtleBot3

The camera's USB cable must reach this host, or the camera can publish
independently over GigE/USB and the topic forwarded via the same LAN.

---

## 5. VLM compute host

`reasoning/vlm/llama_server_backend.py` targets **NVIDIA Cosmos Reason2 8B**
served by `llama-server` (llama.cpp) with `-ngl 99` (fully offloaded to GPU).

| Requirement | Minimum | Recommended |
|---|---|---|
| GPU | NVIDIA RTX 3060 12 GB | RTX 4070 / A10G or better |
| VRAM | 12 GB (text-only) | 16–24 GB (vision mode with `--mmproj`) |
| CUDA | 12.x | 12.x |
| OS | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 |
| RAM | 16 GB | 32 GB |

The VLM host only needs to run `llama-server` on port 8080. It does not need
ROS 2 installed. The `ReasonerConfig.timeout_sec` (default in
`reasoning/vlm/models.py`) governs how long M2 waits per inference call.

---

## 6. Network

All devices must be on the same LAN with a matching `ROS_DOMAIN_ID` (default: 0).

| Device | Connection |
|---|---|
| TurtleBot3 robots | 5 GHz Wi-Fi (2.4 GHz has too much latency for 30 Hz control) |
| Overhead camera | USB 3.0 cable to ROS 2 host, or GigE on same switch |
| ROS 2 host | Gigabit Ethernet preferred |
| VLM host | Gigabit Ethernet |

**DDS multicast (UDP 7400)** must not be blocked between the ROS 2 host and
robots. If using a managed switch, ensure IGMP snooping does not filter DDS
multicast traffic.

Set the domain ID consistently on every shell and in every launch file:

```bash
export ROS_DOMAIN_ID=0
```

---

## 7. Demo-only configuration (M1 only)

To run an M1-only hardware demo before M3–M5 are implemented:

1. Mount the camera and markers.
2. On the ROS 2 host, launch the camera driver (e.g. `usb_cam`) and M1:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch swarm_perception perception.launch.py use_camera_node:=false
```

3. Monitor robot state output:

```bash
ros2 topic echo /perception/scene_state
```

This validates the camera-to-world-frame pipeline and ArUco detection without
requiring the VLM host or any swarm coordination software.

---

## Reference

| Resource | Location |
|---|---|
| Camera config | `ros2_ws/src/swarm_perception/config/camera.yaml` |
| ArUco config | `ros2_ws/src/swarm_perception/config/aruco.yaml` |
| Robot config | `isaac/config/robot.yaml` |
| Calibration source | `isaac/vgu_sim/calibration.py` |
| Isaac Sim demo guide | `docs/guides/run_isaac_sim_with_m1.md` |
| M1 perception guide | `docs/guides/run_m1_perception.md` |
| M1 spec | `docs/specs/module1_perception.md` |
