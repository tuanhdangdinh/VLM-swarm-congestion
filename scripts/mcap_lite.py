"""Minimal reader for uncompressed rosbag2 MCAP files (Odometry, Twist, Clock only).

Report: docs/reports/2026-11-15-m4-stall-abort.md. Written so the recorded
`/odom` and `/cmd_vel` evidence can be read offline without installing the
`mcap` packages. Handles uncompressed chunks only (the bags used here record
`compression_format: ""`) and decodes three CDR message types.
"""
from __future__ import annotations

import struct
from collections.abc import Iterator
from pathlib import Path

_MAGIC = b"\x89MCAP0\r\n"


def _string(buf: bytes, off: int) -> tuple[str, int]:
    (n,) = struct.unpack_from("<I", buf, off)
    return buf[off + 4 : off + 4 + n].decode(), off + 4 + n


def _records(buf: bytes, off: int, end: int) -> Iterator[tuple[int, bytes]]:
    while off + 9 <= end:
        op = buf[off]
        (n,) = struct.unpack_from("<Q", buf, off + 1)
        yield op, buf[off + 9 : off + 9 + n]
        off += 9 + n


def iter_messages(path: Path, topics: set[str]) -> Iterator[tuple[str, int, bytes]]:
    """Yield `(topic, log_time_ns, cdr_payload)` for the requested topics.

    Args:
        path: The `.mcap` file.
        topics: Topic names to keep.

    Raises:
        ValueError: On a bad magic or a compressed chunk.
    """
    buf = path.read_bytes()
    if not buf.startswith(_MAGIC):
        raise ValueError(f"not an MCAP file: {path}")
    channels: dict[int, str] = {}

    def handle(op: int, content: bytes) -> Iterator[tuple[str, int, bytes]]:
        if op == 0x04:
            (cid,) = struct.unpack_from("<H", content, 0)
            topic, _ = _string(content, 4)
            channels[cid] = topic
        elif op == 0x05:
            cid, _seq, log_time, _pub = struct.unpack_from("<HIQQ", content, 0)
            topic = channels.get(cid)
            if topic in topics:
                yield topic, log_time, content[22:]
        elif op == 0x06:
            off = 8 + 8 + 8 + 4
            compression, off = _string(content, off)
            if compression:
                raise ValueError(f"compressed chunk ({compression}) not supported")
            (n,) = struct.unpack_from("<Q", content, off)
            inner = content[off + 8 : off + 8 + n]
            for inner_op, inner_content in _records(inner, 0, len(inner)):
                yield from handle(inner_op, inner_content)

    for op, content in _records(buf, len(_MAGIC), len(buf) - len(_MAGIC)):
        yield from handle(op, content)


class _Cdr:
    def __init__(self, payload: bytes) -> None:
        self.b = payload[4:]
        self.o = 0

    def _align(self, n: int) -> None:
        self.o += (-self.o) % n

    def i32(self) -> int:
        self._align(4)
        (v,) = struct.unpack_from("<i", self.b, self.o)
        self.o += 4
        return v

    def u32(self) -> int:
        self._align(4)
        (v,) = struct.unpack_from("<I", self.b, self.o)
        self.o += 4
        return v

    def f64(self, count: int = 1) -> tuple[float, ...]:
        self._align(8)
        v = struct.unpack_from(f"<{count}d", self.b, self.o)
        self.o += 8 * count
        return v

    def string(self) -> str:
        n = self.u32()
        s = self.b[self.o : self.o + n - 1].decode()
        self.o += n
        return s


def decode_odometry(payload: bytes) -> dict:
    """Decode `nav_msgs/msg/Odometry` CDR: stamp, frame ids, pose, twist."""
    c = _Cdr(payload)
    sec = c.i32()
    nsec = c.u32()
    frame = c.string()
    child = c.string()
    px, py, pz = c.f64(3)
    qx, qy, qz, qw = c.f64(4)
    c.f64(36)
    vx, vy, vz, wx, wy, wz = c.f64(6)
    return {
        "stamp": sec + nsec * 1e-9,
        "frame_id": frame,
        "child_frame_id": child,
        "x": px,
        "y": py,
        "qz": qz,
        "qw": qw,
        "vx": vx,
        "wz": wz,
    }


def decode_twist(payload: bytes) -> dict:
    """Decode `geometry_msgs/msg/Twist` CDR."""
    c = _Cdr(payload)
    lx, _ly, _lz, _ax, _ay, az = c.f64(6)
    return {"linear_x": lx, "angular_z": az}


def decode_clock(payload: bytes) -> float:
    """Decode `rosgraph_msgs/msg/Clock` CDR into seconds."""
    c = _Cdr(payload)
    return c.i32() + c.u32() * 1e-9
