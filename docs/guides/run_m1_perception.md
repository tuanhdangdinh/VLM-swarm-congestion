# Running M1 Perception & Robot ID Tracking

This guide explains how to run Module 1 (M1), the perception and robot tracking module.

---

## Prerequisites

1. **ROS2 Jazzy environment** with colcon installed.
2. **Built workspace** — run `make build-ros2` to compile all packages.
3. **Python dependencies** — M1 requires `numpy`, `opencv-contrib-python`, `pydantic`, `pyyaml`.

---

## Quick Start

### Hardware Camera Source

To run M1 with a hardware camera (e.g., USB camera, CSI camera):

```bash
make run-perception
```

This launches:
- **CameraNode:** Publishes raw RGB frames from the configured camera device.
- **PerceptionNode:** Subscribes to frames, runs ArUco detection, publishes robot state and annotated frames.

**Default camera device:** `/dev/video0` (first USB camera). Override via parameter:

```bash
ros2 launch swarm_perception perception.launch.py device:=2 fps:=30
```

**Topics published:**
- `/perception/scene_state` — Robot state vectors (JSON)
- `/perception/annotated_frame` — Annotated RGB image (sensor_msgs/Image)
- `/perception/status` — Per-frame diagnostics (JSON)

**Subscribes to:**
- `/coordination/tasks` — Task registry from M5 (JSON)

---

## Isaac Sim / External Bridge Mode

When running with **Isaac Sim** or any external source that publishes `/camera/image_raw`:

```bash
make run-perception-isaac
```

Or explicitly:

```bash
ros2 launch swarm_perception perception.launch.py use_camera_node:=false
```

This skips the hardware CameraNode and only runs PerceptionNode, which subscribes to whatever publishes `/camera/image_raw` (e.g., Isaac Sim ROS2 bridge).

---

## Configuration

M1 parameters are configured in `config/aruco.yaml` and `config/calibration.yaml`:

### `config/aruco.yaml`

```yaml
aruco:
  dictionary: DICT_4X4_50        # ArUco marker dictionary
  marker_size_m: 0.08             # Physical marker size in meters
  min_detection_confidence: 0.5    # Confidence threshold (reserved)
```

Change the dictionary if your markers use a different format (e.g., `DICT_5X5_100`). The launch script reads this and passes it to PerceptionNode.

### `config/calibration.yaml`

Defines camera intrinsics, distortion, and the homography matrix mapping pixel → world coordinates.

- **intrinsics:** 3×3 camera matrix (focal length, principal point).
- **distortion:** Distortion coefficients.
- **homography:** 3×3 matrix (pixel → world). Estimated via `estimate_homography()` from ≥4 correspondences.
- **image_size:** Camera resolution `[width, height]`.

To use a custom calibration:

```bash
ros2 launch swarm_perception perception.launch.py \
  calibration_path:=$(pwd)/my_calibration.yaml
```

---

## Testing (Offline)

To test M1 logic without ROS2:

```bash
# Run unit tests
make test

# Run perception smoke test (exercises pure logic, models, publishing helpers)
python scripts/smoke_perception.py
```

---

## Typical Workflow

### 1. Set Up Hardware or Sim

**Hardware:**
- Attach a USB camera and verify it appears as `/dev/video0` or `/dev/video1`.
- Calibrate: follow `docs/specs/module1_perception.md` § Calibration to compute intrinsics and homography.

**Isaac Sim:**
- Launch Isaac Sim with ROS2 Jazzy support.
- Ensure the Isaac bridge publishes to `/camera/image_raw`.

### 2. Build

```bash
make build-ros2
```

### 3. Launch M1

```bash
# Hardware
make run-perception

# Isaac Sim
make run-perception-isaac
```

### 4. Monitor Output

In another terminal, inspect the published topics:

```bash
# List all topics
ros2 topic list

# Watch robot states
ros2 topic echo /perception/scene_state

# View annotated frame metadata
ros2 topic echo /perception/annotated_frame --field header
```

### 5. Publish Tasks (Optional)

If M5 Orchestrator is running, it publishes tasks. Otherwise, manually inject a task registry:

```bash
# In a new terminal
ros2 topic pub -1 /coordination/tasks std_msgs/String \
  'data: "{\"robot_0\": {\"task\": \"deliver_A\", \"goal\": {\"x\": 1.0, \"y\": 2.0}}}"'
```

---

## Troubleshooting

### **Camera Not Found**

If CameraNode fails to open the device:

```
Failed to open camera device: '/dev/video0'
```

**Solutions:**
- List available devices: `ls /dev/video*`
- Check device ownership: `ls -la /dev/video0`
- Add user to video group: `sudo usermod -aG video $USER` (then log out/in)
- Override device: `ros2 launch swarm_perception perception.launch.py device:=1`

### **Calibration Error**

If PerceptionNode fails to load calibration:

```
CalibrationError: Calibration file not found: ...
```

**Solutions:**
- Verify the file exists: `ls -la config/calibration.yaml` or `ros2_ws/src/swarm_perception/config/calibration.yaml`
- Use an explicit path: `ros2 launch swarm_perception perception.launch.py calibration_path:=/path/to/my_cal.yaml`

### **No Detections**

If ArUco markers are not being detected:

- Verify marker dictionary matches your markers (check `config/aruco.yaml`).
- Check marker size and image quality.
- Ensure adequate lighting.
- Increase `min_detection_confidence` if too many false negatives.

### **ROS2 Setup Issues**

If you see "Package 'swarm_perception' not found":

- Ensure the workspace is built: `make build-ros2`
- Source the setup: `source ros2_ws/install/setup.bash`
- Verify ROS2 Jazzy is sourced first: `source /opt/ros/jazzy/setup.bash`

---

## Next Steps

Once M1 is running and publishing state:

- **M2 VLM:** Subscribe to `/perception/scene_state` and `/perception/annotated_frame` to perform semantic analysis.
- **M5 Orchestrator:** Subscribe to `/perception/scene_state` and publish to `/coordination/tasks`.
- **M4 Execution:** Subscribe to `/perception/scene_state` for safety monitoring.

---

## Reference

- **M1 Specification:** `docs/specs/module1_perception.md`
- **Launch Config:** `ros2_ws/src/swarm_perception/launch/perception.launch.py`
- **ROS2 Topics:**
  - Input: `/coordination/tasks` (task registry)
  - Output: `/perception/scene_state`, `/perception/annotated_frame`, `/perception/status`
