"""Record a ROS2 `sensor_msgs/Image` topic to an MP4 file for offline review.

This is a debugging/evidence tool, not part of the runtime stack: it subscribes
to one image topic (`rgb8` or `bgr8`), converts each message to BGR, and writes
it to an `mp4v`-encoded MP4 via `cv2.VideoWriter`.

Timing limitation: frames are written in receive order, one container frame per
received message, but the container is stamped at the fixed `--fps` given on the
command line. Playback therefore runs at real time only when the topic's actual
publish rate is close to `--fps`; if the topic runs slower the video plays fast,
if it runs faster the video plays slow. No timestamp interpolation or frame
duplication is performed, deliberately, so that every video frame corresponds
to exactly one published message. Measure the topic rate (`ros2 topic hz`)
before recording and pass it as `--fps`; the exit line reports the achieved mean
rate (`frames / secs`) so the real-time factor of the playback can be recovered
afterwards.

The overlay clock uses each message's own `header.stamp`, not the recorder's
clock, so overlaid times line up with the publisher's time base (sim time when
the stack runs with `use_sim_time`). The first-frame log line prints both the
header stamp and the recorder's wall clock so the two bases can be related.

An MP4 is only playable once its trailer is written at `release()`, so a
`SIGKILL` (host repair, OOM kill, `docker kill`) loses the entire recording.
`--segment-frames N` bounds that loss: the writer is closed and reopened every
`N` frames on numbered outputs (`out_000.mp4`, `out_001.mp4`, ...), so a hard
kill costs at most the current segment. Rejoin segments losslessly afterwards
with ffmpeg's concat demuxer.

Example:
    python3 scripts/record_topic_video.py \
        --topic /perception/annotated_frame \
        --output /tmp/run_annotated.mp4 --fps 10 --qos best_effort
"""
from __future__ import annotations

import argparse
import signal
import time
from pathlib import Path
from types import FrameType

import numpy as np

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
    from sensor_msgs.msg import Image as RosImage

    _HAS_ROS2 = True
except ImportError:  # pragma: no cover - lets the module parse without ROS2
    rclpy = None
    Node = object
    RosImage = None
    QoSDurabilityPolicy = QoSHistoryPolicy = QoSProfile = QoSReliabilityPolicy = None
    _HAS_ROS2 = False

SUPPORTED_ENCODINGS = ("rgb8", "bgr8")
QUEUE_DEPTH = 30


def image_msg_to_bgr(msg: RosImage) -> np.ndarray:
    """Convert a `sensor_msgs/Image` message into a writable BGR array.

    Args:
        msg: Image message encoded as `rgb8` or `bgr8`.

    Returns:
        Writable `uint8` array of shape `(height, width, 3)` in BGR channel
        order, ready for `cv2` drawing and `cv2.VideoWriter.write`.

    Raises:
        ValueError: If the message encoding is not `rgb8` or `bgr8`, or the
            payload is too small for the declared height/step.
    """
    if msg.encoding not in SUPPORTED_ENCODINGS:
        raise ValueError(
            f"unsupported encoding {msg.encoding!r}; expected one of {SUPPORTED_ENCODINGS}"
        )

    height = int(msg.height)
    width = int(msg.width)
    step = int(msg.step) or width * 3
    buffer = np.frombuffer(msg.data, dtype=np.uint8)
    if buffer.size < height * step:
        raise ValueError(f"payload {buffer.size} bytes too small for height={height} step={step}")

    # np.frombuffer is read-only and msg.step may exceed width*3 (row padding),
    # so crop the stride away and copy before any in-place drawing.
    rows = buffer[: height * step].reshape(height, step)
    frame = rows[:, : width * 3].reshape(height, width, 3).copy()
    if msg.encoding == "rgb8":
        frame = frame[:, :, ::-1].copy()
    return frame


def stamp_to_sec(msg: RosImage) -> float:
    """Return a message header stamp as float seconds."""
    return float(msg.header.stamp.sec) + float(msg.header.stamp.nanosec) * 1e-9


class TopicVideoRecorder(Node):
    """ROS2 node that writes one image topic to an MP4 file."""

    def __init__(
        self,
        topic: str,
        output: str,
        fps: float,
        qos: str,
        overlay_clock: bool,
        segment_frames: int = 0,
    ) -> None:
        """Create the recorder node and subscribe to the image topic.

        Args:
            topic: Image topic to record.
            output: Destination MP4 path.
            fps: Container frame rate stamped into the MP4.
            qos: `best_effort` or `reliable` subscription reliability.
            overlay_clock: Draw header-stamp seconds and frame count top-left.
            segment_frames: Close and reopen the writer every this many frames
                on numbered outputs; `0` writes one file.
        """
        super().__init__("topic_video_recorder")
        import cv2

        self._cv2 = cv2
        self._topic = topic
        self._output = output
        self._fps = fps
        self._overlay_clock = overlay_clock
        self._segment_frames = max(0, segment_frames)
        self._writer: object | None = None
        self._size: tuple[int, int] | None = None
        self._frames = 0
        self._segment_index = 0
        self._segment_written = 0
        self._paths: list[str] = []
        self._skipped = 0
        self._start_monotonic = time.monotonic()
        self._first_stamp: float | None = None

        reliability = (
            QoSReliabilityPolicy.RELIABLE if qos == "reliable" else QoSReliabilityPolicy.BEST_EFFORT
        )
        profile = QoSProfile(
            reliability=reliability,
            durability=QoSDurabilityPolicy.VOLATILE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=QUEUE_DEPTH,
        )
        self._sub = self.create_subscription(RosImage, topic, self._on_image, profile)
        print(f"waiting for first frame on {topic} qos={qos} fps={fps} output={output}", flush=True)

    @property
    def frames(self) -> int:
        """Number of frames written so far."""
        return self._frames

    def elapsed_sec(self) -> float:
        """Seconds since the recorder started."""
        return time.monotonic() - self._start_monotonic

    def _on_image(self, msg: RosImage) -> None:
        try:
            frame = image_msg_to_bgr(msg)
        except ValueError as exc:
            self._skipped += 1
            print(f"skip frame: {exc}", flush=True)
            return

        height, width = frame.shape[:2]
        if self._writer is None:
            self._size = (width, height)
            self._open_writer()
            self._first_stamp = stamp_to_sec(msg)
            print(
                f"first frame: size={width}x{height} encoding={msg.encoding} "
                f"header_stamp={self._first_stamp:.3f} wall_clock={time.time():.3f}",
                flush=True,
            )
        elif (width, height) != self._size:
            # VideoWriter geometry is fixed once opened; a resized stream would
            # be silently dropped by write(), so make the loss visible instead.
            self._skipped += 1
            print(f"skip frame: size {width}x{height} != {self._size}", flush=True)
            return

        if self._overlay_clock:
            label = f"t={stamp_to_sec(msg):.2f}s  f={self._frames + 1}"
            self._cv2.putText(
                frame, label, (12, 34), self._cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4
            )
            self._cv2.putText(
                frame, label, (12, 34), self._cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2
            )

        self._writer.write(frame)
        self._frames += 1
        self._segment_written += 1
        if self._frames % 50 == 0:
            print(f"frames={self._frames} elapsed={self.elapsed_sec():.1f}", flush=True)
        if self._segment_frames and self._segment_written >= self._segment_frames:
            self._close_writer()
            self._segment_index += 1
            self._open_writer()

    def _segment_path(self) -> str:
        if not self._segment_frames:
            return self._output
        stem = Path(self._output)
        return str(stem.with_name(f"{stem.stem}_{self._segment_index:03d}{stem.suffix}"))

    def _open_writer(self) -> None:
        assert self._size is not None
        path = self._segment_path()
        fourcc = self._cv2.VideoWriter_fourcc(*"mp4v")
        writer = self._cv2.VideoWriter(path, fourcc, self._fps, self._size)
        if not writer.isOpened():
            raise RuntimeError(f"cv2.VideoWriter could not open {path}")
        self._writer = writer
        self._segment_written = 0
        self._paths.append(path)

    def _close_writer(self) -> None:
        if self._writer is None:
            return
        self._writer.release()
        self._writer = None
        print(
            f"segment {self._segment_path()} frames={self._segment_written} "
            f"total={self._frames} elapsed={self.elapsed_sec():.1f}",
            flush=True,
        )

    def finish(self) -> None:
        """Release the writer so the MP4 trailer is written, then report."""
        self._close_writer()
        secs = self.elapsed_sec()
        written = " ".join(self._paths) if self._paths else self._output
        print(f"WROTE {written} frames={self._frames} secs={secs:.1f}", flush=True)
        if self._skipped:
            print(f"skipped={self._skipped}", flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the recorder."""
    parser = argparse.ArgumentParser(description="Record a sensor_msgs/Image topic to MP4.")
    parser.add_argument("--topic", required=True, help="Image topic to subscribe to.")
    parser.add_argument("--output", required=True, help="Destination MP4 path.")
    parser.add_argument(
        "--duration-sec", type=float, default=60.0, help="Stop after this many seconds."
    )
    parser.add_argument(
        "--fps", type=float, default=10.0, help="Container frame rate stamped into the MP4."
    )
    parser.add_argument(
        "--qos",
        choices=("best_effort", "reliable"),
        default="best_effort",
        help="Subscription reliability; must be compatible with the publisher.",
    )
    parser.add_argument(
        "--segment-frames",
        type=int,
        default=0,
        help=(
            "Close and reopen the writer every N frames on numbered outputs so a "
            "SIGKILL loses at most one segment; 0 writes a single file."
        ),
    )
    parser.add_argument(
        "--overlay-clock",
        dest="overlay_clock",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw header-stamp seconds and frame count in the top-left corner.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the recorder until the duration elapses or SIGTERM/SIGINT arrives."""
    if not _HAS_ROS2:
        raise RuntimeError("rclpy is unavailable; source a ROS2 environment first")
    args = parse_args(argv)

    stopping = {"flag": False}

    def _request_stop(signum: int, _frame: FrameType | None) -> None:
        stopping["flag"] = True
        print(f"stop requested signal={signum}", flush=True)

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    rclpy.init()
    node = TopicVideoRecorder(
        topic=args.topic,
        output=args.output,
        fps=args.fps,
        qos=args.qos,
        overlay_clock=args.overlay_clock,
        segment_frames=args.segment_frames,
    )
    try:
        while not stopping["flag"] and node.elapsed_sec() < args.duration_sec:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.finish()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
