#!/usr/bin/env python3
"""Save overhead-camera snapshots at a fixed sim-time interval (VM-only helper).

Evidence tool for the step-9 visual pass (prereg-v2 build-order step 9,
docs/reports/2026-10-03-loop-family-and-visual-pass.md): subscribes to M1's
`/perception/annotated_frame` (what M2 is shown) and the raw
`/camera/image_raw`, and writes one lossless PNG of each every
`INTERVAL_SIM_SEC` of the image header stamp (sim time under
`use_sim_time`), named `<topic>_<stamp>.png`. PNG, never base64, never in a
log line. Not part of the runtime stack.

Usage: frame_snapshots.py OUT_DIR DURATION_WALL_SEC [INTERVAL_SIM_SEC]
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

TOPICS = {"annotated": "/perception/annotated_frame", "raw": "/camera/image_raw"}


def to_bgr(msg: Image) -> np.ndarray:
    """Convert an rgb8/bgr8 Image message to a BGR array for cv2.imwrite."""
    frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, -1)
    if msg.encoding.lower() == "rgb8":
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame.copy()


class Snapshots(Node):
    def __init__(self, out: Path, interval: float) -> None:
        super().__init__("frame_snapshots")
        self.out, self.interval = out, interval
        self.next_at = {name: 0.0 for name in TOPICS}
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        for name, topic in TOPICS.items():
            self.create_subscription(Image, topic, lambda m, n=name: self._on(n, m), qos)

    def _on(self, name: str, msg: Image) -> None:
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if stamp < self.next_at[name]:
            return
        self.next_at[name] = stamp + self.interval
        cv2.imwrite(str(self.out / f"{name}_{stamp:08.2f}.png"), to_bgr(msg))


def main() -> None:
    out, duration = Path(sys.argv[1]), float(sys.argv[2])
    interval = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
    out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Snapshots(out, interval)
    end = time.time() + duration
    while time.time() < end and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.2)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
