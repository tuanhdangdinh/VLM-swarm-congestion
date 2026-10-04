#!/usr/bin/env python3
"""Save overhead-camera snapshots at a fixed sim-time interval (VM-only helper).

Evidence tool for the step-9 visual pass (prereg-v2 build-order step 9,
docs/reports/2026-10-03-loop-family-and-visual-pass.md): subscribes to M1's
`/perception/annotated_frame` (what M2 is shown) and the raw
`/camera/image_raw`, and writes one lossless PNG of each every
`INTERVAL_SIM_SEC` of the image header stamp (sim time under
`use_sim_time`), named `<topic>_<stamp>.png`. PNG, never base64, never in a
log line. Not part of the runtime stack.

Battery-v2 harvest additions (2026-10-04,
docs/reports/2026-10-04-battery-v2-results.md): `TOPICS` (comma list,
default `annotated,raw`) selects which images are saved, and every run
also writes `frames.jsonl` (one row per saved PNG with its full-precision
header stamp) and `scene_state.jsonl` (every `/perception/scene_state`
message M1 published, verbatim), so each saved annotated frame can be
matched to the exact M1 state it was drawn from (status colour, drawn
position) instead of interpolating the ~3 Hz M5 scene log.

Usage: frame_snapshots.py OUT_DIR DURATION_WALL_SEC [INTERVAL_SIM_SEC [TOPICS]]
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String

TOPICS = {"annotated": "/perception/annotated_frame", "raw": "/camera/image_raw"}
SCENE_STATE_TOPIC = "/perception/scene_state"


def to_bgr(msg: Image) -> np.ndarray:
    """Convert an rgb8/bgr8 Image message to a BGR array for cv2.imwrite."""
    frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
    if msg.encoding.lower() == "rgb8":
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame.copy()


class Snapshots(Node):
    def __init__(self, out: Path, interval: float, names: list[str]) -> None:
        super().__init__("frame_snapshots")
        self.out, self.interval = out, interval
        self.next_at = {name: 0.0 for name in names}
        self.frames_log = (out / "frames.jsonl").open("a", encoding="utf-8")
        self.scene_log = (out / "scene_state.jsonl").open("a", encoding="utf-8")
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        for name in names:
            self.create_subscription(
                Image, TOPICS[name], lambda m, n=name: self._on(n, m), qos
            )
        self.create_subscription(String, SCENE_STATE_TOPIC, self._on_scene, 50)

    def _on(self, name: str, msg: Image) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if stamp < self.next_at[name]:
            return
        self.next_at[name] = stamp + self.interval
        filename = f"{name}_{stamp:08.2f}.png"
        cv2.imwrite(str(self.out / filename), to_bgr(msg))
        self.frames_log.write(
            json.dumps(
                {
                    "file": filename,
                    "topic": name,
                    "stamp_sec": msg.header.stamp.sec,
                    "stamp_nanosec": msg.header.stamp.nanosec,
                }
            )
            + "\n"
        )
        self.frames_log.flush()

    def _on_scene(self, msg: String) -> None:
        self.scene_log.write(msg.data.replace("\n", " ") + "\n")
        self.scene_log.flush()

    def close(self) -> None:
        self.frames_log.close()
        self.scene_log.close()


def main() -> None:
    out, duration = Path(sys.argv[1]), float(sys.argv[2])
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    names = sys.argv[4].split(",") if len(sys.argv) > 4 else list(TOPICS)
    unknown = [name for name in names if name not in TOPICS]
    if unknown:
        raise SystemExit(f"unknown snapshot topics {unknown}; known: {sorted(TOPICS)}")
    out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Snapshots(out, interval, names)
    end = time.time() + duration
    try:
        while time.time() < end and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        node.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
