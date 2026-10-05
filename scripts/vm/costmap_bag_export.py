#!/usr/bin/env python3
"""Export a costmap-probe bag to JSONL for offline replay (VM, in-container).

Reads the `ros2 bag record` output of scripts/vm/costmap_probe.sh with
rosbag2_py and writes one JSON row per message of interest, every row keyed
by its header (sim) stamp where the message has one, plus the bag's receive
time `rec` (ns, wall) for ordering:

- `scan`      : `/<robot>/scan` -- angle_min/increment, range_min/max, ranges
                (non-finite -> null).
- `map_odom`  : `map -> <robot>/odom` from `/tf` (the camera localizer's
                correction, future-stamped by its transform_tolerance).
- `odom_tf`   : `<robot>/odom -> <robot>/base_footprint` from `/tf`.
- `tf_static` : every `/tf_static` edge, once.
- `odom`      : `/<robot>/odom` pose and twist.
- `scene`     : robot's row of `/perception/scene_state` (M1), with the
                scene stamp.
- `cmd_vel`   : `/<robot>/cmd_vel` (no header; `rec` only).
- `phase`     : `/costmap_probe/phase` markers (sim time inside).
- `grid`      : the global costmap after every full grid or update, as the
                cells that are lethal (100) now but were not in the FIRST full
                grid (the static map), as flat indices, plus the crop of the
                second aisle the waypoint probe used. `grid_meta` once.

Usage: costmap_bag_export.py BAG_DIR OUT_JSONL [ROBOT_ID]
"""
import json
import math
import sys

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message

CROP_BOX = (0.4, 2.1, 0.6, 1.5)


def _stamp(header) -> float:
    return header.stamp.sec + header.stamp.nanosec * 1e-9


def _yaw(q) -> float:
    return 2.0 * math.atan2(q.z, q.w)


def main() -> int:
    """CLI entry point."""
    bag_dir, out_path = sys.argv[1], sys.argv[2]
    robot = sys.argv[3] if len(sys.argv) > 3 else "robot_1"
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=bag_dir, storage_id="mcap"),
                rosbag2_py.ConverterOptions("cdr", "cdr"))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    msg_cls = {name: get_message(kind) for name, kind in types.items()}
    grid = None
    static_lethal = None
    seen_static = set()
    out = open(out_path, "w", encoding="utf-8")

    def write(kind, rec, **fields):
        row = {"kind": kind, "rec": rec}
        row.update(fields)
        out.write(json.dumps(row) + "\n")

    def write_grid(rec, stamp, source):
        w, h, res, ox, oy = grid["w"], grid["h"], grid["res"], grid["ox"], grid["oy"]
        data = grid["data"]
        new = [i for i, v in enumerate(data) if v == 100 and not static_lethal[i]]
        x0, x1, y0, y1 = CROP_BOX
        cols = [c for c in range(w) if x0 <= ox + (c + 0.5) * res <= x1]
        rows = [r for r in range(h) if y0 <= oy + (r + 0.5) * res <= y1]
        crop = [[data[r * w + c] for c in cols] for r in rows]
        write("grid", rec, stamp=stamp, source=source, new_lethal=new,
              crop_c0=cols[0], crop_r0=rows[0], crop=crop)

    while reader.has_next():
        topic, raw, rec = reader.read_next()
        if topic not in msg_cls:
            continue
        msg = deserialize_message(raw, msg_cls[topic])
        if topic == f"/{robot}/scan":
            write("scan", rec, stamp=_stamp(msg.header), amin=msg.angle_min,
                  ainc=msg.angle_increment, rmin=msg.range_min, rmax=msg.range_max,
                  ranges=[round(r, 4) if math.isfinite(r) else None for r in msg.ranges])
        elif topic == "/tf":
            for tf in msg.transforms:
                t, r = tf.transform.translation, tf.transform.rotation
                if tf.header.frame_id == "map" and tf.child_frame_id == f"{robot}/odom":
                    write("map_odom", rec, stamp=_stamp(tf.header), x=t.x, y=t.y, yaw=_yaw(r))
                elif (tf.header.frame_id == f"{robot}/odom"
                      and tf.child_frame_id == f"{robot}/base_footprint"):
                    write("odom_tf", rec, stamp=_stamp(tf.header), x=t.x, y=t.y, yaw=_yaw(r))
        elif topic == "/tf_static":
            for tf in msg.transforms:
                key = (tf.header.frame_id, tf.child_frame_id)
                if key in seen_static:
                    continue
                seen_static.add(key)
                t, r = tf.transform.translation, tf.transform.rotation
                write("tf_static", rec, parent=key[0], child=key[1], x=t.x, y=t.y, z=t.z,
                      qx=r.x, qy=r.y, qz=r.z, qw=r.w)
        elif topic == f"/{robot}/odom":
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            write("odom", rec, stamp=_stamp(msg.header), x=p.x, y=p.y, yaw=_yaw(q),
                  vx=msg.twist.twist.linear.x, wz=msg.twist.twist.angular.z)
        elif topic == "/perception/scene_state":
            try:
                scene = json.loads(msg.data)
            except ValueError:
                continue
            row = next((r for r in scene.get("robots", []) if r.get("robot_id") == robot), None)
            if row is not None:
                write("scene", rec, stamp=scene.get("stamp"), x=row["x"], y=row["y"],
                      theta=row["theta"], status=row.get("status"))
        elif topic == f"/{robot}/cmd_vel":
            write("cmd_vel", rec, vx=msg.linear.x, wz=msg.angular.z)
        elif topic == "/costmap_probe/phase":
            write("phase", rec, **json.loads(msg.data))
        elif topic == f"/{robot}/global_costmap/costmap":
            info = msg.info
            grid = {"w": info.width, "h": info.height, "res": info.resolution,
                    "ox": info.origin.position.x, "oy": info.origin.position.y,
                    "data": list(msg.data)}
            if static_lethal is None:
                static_lethal = [v == 100 for v in grid["data"]]
                write("grid_meta", rec, stamp=_stamp(msg.header), w=grid["w"], h=grid["h"],
                      res=grid["res"], ox=grid["ox"], oy=grid["oy"],
                      static_lethal_count=sum(static_lethal))
            write_grid(rec, _stamp(msg.header), "full")
        elif topic == f"/{robot}/global_costmap/costmap_updates":
            if grid is None:
                continue
            for row in range(msg.height):
                start = (msg.y + row) * grid["w"] + msg.x
                grid["data"][start:start + msg.width] = msg.data[row * msg.width:(row + 1) * msg.width]
            write_grid(rec, _stamp(msg.header), "update")
    out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
