"""Offline replay of recorded M4 raw-cmd_vel primitives through the stall abort.

Report: docs/reports/2026-11-15-m4-stall-abort.md. Read-only on the bundles;
no VM, no API call.

For every raw-cmd_vel primitive M4 ran in a bundle (yield/reverse backup,
yield pull-off, escort), this rebuilds an episode from the logs and replays it
through the real `Nav2Adapter` primitive with a `StallWatch` attached:

- Start: the escort's `gate_admit ... sim_t=` (exact), the backup's hand-over
  `controller stop ... reason=handover sim_t=` (exact), or the pull-off's
  ACTIVE `status published` line (wall time, mapped to sim time).
- End: the primitive's next `status published` line (or the escort's
  terminal line), wall time mapped to sim time by linear interpolation
  between the neighbouring `sim_t=` anchors of m4.log, m5.log and
  launcher.log.
- Parameters: the bundle's decision artifacts (dispatched command, junction
  phases and fallback), so the adapter computes the same commands it
  published live. The commanded stream itself is not recorded; the replay
  regenerates it from the primitive's own logic on the recorded poses.
- Measurement: ground truth (`gt/ground_truth.jsonl`, `base_link`, 10 Hz)
  transformed into the robot's odom frame (spawn pose = first GT row), fed as
  odometry stamped with ROS sim time. GT's clock starts after Isaac's ROS
  topic wait, so GT time = ROS sim time - offset; the offset is estimated
  per bundle by aligning M1's sim-stamped poses (`m5_scene.jsonl`) with GT
  (0.48 and 0.52 s against the 0.50 s an odometry bag gives exactly). In the Isaac setup `/odom` is
  `IsaacComputeOdometry` on the chassis prim, a physics pose, so GT stands in
  for it (the report's section 2 checks this against recorded bags).
- Real odometry: when the bundle carries a rosbag (`bag/*.mcap`) with the
  robot's `/<robot>/odom`, those messages are used instead of GT
  (`odom_source: bag`); read with `scripts/mcap_lite.py`.
- Safety holds: `cmd_vel relay hold engaged/released robot=` lines of
  isaac.log, mapped to sim time, gate the command to zero.

Usage (repo root):
    python scripts/stall_abort_replay.py [--export DIR] <bundle_dir> [...]

Prints one tab-separated row per primitive. `--export DIR` also writes each
episode as JSON; `--pack FILE.jsonl.gz` appends them to one gzip file (the
unit-test fixture `tests/unit/data/stall_abort/replay_episodes.jsonl.gz`).
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import json
import math
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from swarm_execution.crossing_chain import plan_crossing
from swarm_execution.nav2_adapter import Nav2Adapter, backup_line_turn
from swarm_execution.stall_abort import StallAbortConfig, StallWatch

_LINE = re.compile(r"\[(?:INFO|WARN|WARNING|ERROR|DEBUG)\] \[(\d+\.\d+)\] \[[^\]]+\]: (.*)$")
_SIM_T = re.compile(r"sim_t=(\d+(?:\.\d+)?)")
_RECEIVED = re.compile(r"command received command=(\S+) robot=(\S+) action=(\S+)")
_STATUS = re.compile(r"^status published command=(\S+) robot=(\S+) status=(\S+)")
_HANDOVER = re.compile(
    r"controller stop robot=(\S+) command=(\S+) action=\S+ reason=handover sim_t=([0-9.]+)"
)
_ADMIT = re.compile(
    r"gate_admit command=(\S+) yielder=(\S+) passer=(\S+) clear_m=\S+ escort_m=(\S+) "
    r"sim_t=([0-9.]+)"
)
_ESCORT = re.compile(r"^escort (\S+): (ACTIVE|COMPLETED|FAILED) (.*)$")
_HOLD = re.compile(r"cmd_vel relay hold (engaged|released) robot=(\S+)")
_TICK = 0.05
# An escort or backup with no terminal line is replayed this long.
_OPEN_END_SEC = 120.0
_END_SLACK_SEC = 2.0
# A start found from the GT motion onset is moved back by this much: the
# command precedes the first measured motion by about one tick plus the
# drive's response. Exact starts (`sim_t=` lines) are used as logged.
_START_LEAD_SEC = 0.1
# Window around the mapped wall time in which the GT onset is searched.
_ONSET_BEFORE_SEC = 12.0
_ONSET_AFTER_SEC = 8.0
_EXTRAPOLATION_SPAN_SEC = 120.0
# gt_motion: a robot is stopped once its pose stays within this radius for
# this long.
_STOP_RADIUS_M = 0.01
_STOP_HOLD_SEC = 2.0


class _Clock:
    def __init__(self) -> None:
        self.seconds = 0.0

    def now(self) -> SimpleNamespace:
        return SimpleNamespace(nanoseconds=int(round(self.seconds * 1e9)))


class _Pub:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    def publish(self, msg: Any) -> None:
        self.messages.append(msg)


class _Timer:
    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class _Logger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, msg: str) -> None:
        self.lines.append(str(msg))

    warning = info
    error = info


class _Client:
    def service_is_ready(self) -> bool:
        return False


class ReplayNode:
    """The rclpy surface `Nav2Adapter`'s raw-cmd_vel primitives touch, on sim time."""

    def __init__(self) -> None:
        self.clock = _Clock()
        self.logger = _Logger()
        self.publishers: dict[str, _Pub] = {}
        self.odom_callbacks: dict[str, Callable[[Any], None]] = {}
        self.timers: list[_Timer] = []

    def get_clock(self) -> _Clock:
        return self.clock

    def get_logger(self) -> _Logger:
        return self.logger

    def create_publisher(self, _type: Any, topic: str, _qos: int) -> _Pub:
        return self.publishers.setdefault(topic, _Pub())

    def create_subscription(self, _type: Any, topic: str, callback: Any, _qos: int) -> str:
        self.odom_callbacks[topic] = callback
        return topic

    def destroy_subscription(self, sub: str) -> None:
        self.odom_callbacks.pop(sub, None)

    def create_timer(self, _period: float, callback: Callable[[], None]) -> _Timer:
        timer = _Timer(callback)
        self.timers.append(timer)
        return timer

    def create_client(self, _type: Any, _name: str) -> _Client:
        return _Client()


def odom_message(stamp: float, x: float, y: float, yaw: float) -> SimpleNamespace:
    """A duck-typed `nav_msgs/Odometry` with a header stamp."""
    sec = int(math.floor(stamp))
    return SimpleNamespace(
        header=SimpleNamespace(
            stamp=SimpleNamespace(sec=sec, nanosec=int(round((stamp - sec) * 1e9)))
        ),
        pose=SimpleNamespace(
            pose=SimpleNamespace(
                position=SimpleNamespace(x=x, y=y, z=0.0),
                orientation=SimpleNamespace(
                    x=0.0, y=0.0, z=math.sin(yaw / 2.0), w=math.cos(yaw / 2.0)
                ),
            )
        ),
    )


def replay_episode(
    episode: dict[str, Any], config: StallAbortConfig | None = None
) -> dict[str, Any]:
    """Run one recorded primitive through the adapter with a stall watch.

    Args:
        episode: The exported episode (see `build_episodes`): `primitive`,
            `robot_id`, `params`, `start_sim`, `end_sim`, `odom` rows
            `[t, x, y, yaw]` in the odom frame, `held` intervals.
        config: Stall-abort parameters, or None to replay without a watch
            (the key-off primitive).

    Returns:
        `outcome` (`COMPLETED`, `FAILED` or `running` at `end_sim`), `detail`,
        `t` (sim time of the terminal), `min_ratio` (the smallest judged
        progress ratio per mode), `log` (the stall abort line or None), and
        `verdict`.
    """
    node = ReplayNode()
    adapter = Nav2Adapter(node)
    robot = episode["robot_id"]
    held = [tuple(h) for h in episode.get("held", [])]
    logs: list[str] = []
    watch = None if config is None else StallWatch(
        config,
        robot_id=robot,
        command_id=episode.get("command_id", "replay"),
        primitive=episode["primitive"],
        is_held=lambda: any(a <= node.clock.seconds < b for a, b in held),
        log=logs.append,
    )
    result: dict[str, Any] = {"outcome": "running", "detail": "", "t": None}

    def on_result(status: str, detail: str) -> None:
        if status in ("COMPLETED", "FAILED") and result["outcome"] == "running":
            result.update(outcome=status, detail=detail, t=node.clock.seconds)

    params = episode["params"]
    rows = episode["odom"]
    start, end = float(episode["start_sim"]), float(episode["end_sim"])
    node.clock.seconds = start
    primitive = episode["primitive"]
    if primitive == "backup":
        adapter.backup(
            robot,
            float(params["distance_m"]),
            on_result=on_result,
            hold_start_line=bool(params.get("hold_start_line")),
            line_turn_rad=float(params.get("line_turn_rad") or 0.0),
            stall_watch=watch,
        )
    elif primitive == "pull_off":
        adapter.sidestep(
            robot, float(params["lateral_m"]), on_result=on_result, stall_watch=watch
        )
    elif primitive == "escort":
        adapter.drive_heading(
            robot,
            target_yaw_rad=float(params["target_yaw_rad"]),
            distance_m=float(params["distance_m"]),
            on_result=on_result,
            relative_to_start=bool(params.get("relative_to_start")),
            stall_watch=watch,
        )
    else:
        raise ValueError(f"unknown primitive {primitive}")
    topic = f"/{robot}/odom"
    index = bisect.bisect_left([r[0] for r in rows], start - 1e-9)
    steps = int(math.ceil((end - start) / _TICK)) + 1
    for i in range(steps):
        now = round(start + i * _TICK, 6)
        node.clock.seconds = now
        while index < len(rows) and rows[index][0] <= now + 1e-9:
            callback = node.odom_callbacks.get(topic)
            if callback is not None:
                callback(odom_message(*rows[index]))
            index += 1
        live = [t for t in node.timers if not t.cancelled]
        if not live or result["outcome"] != "running":
            break
        live[-1].callback()
        if result["outcome"] != "running":
            break
    result["min_ratio"] = {} if watch is None else dict(watch.detector.min_ratio_seen)
    result["log"] = logs[0] if logs else None
    result["verdict"] = (
        watch.verdict.model_dump() if watch is not None and watch.verdict is not None else None
    )
    return result


class _WallToSim:
    """Piecewise-linear wall -> sim map over `sim_t=` anchors.

    Several log lines often print the same `sim_t` within a fraction of a
    wall second, so each distinct sim value keeps its earliest wall time.
    Beyond the first or last anchor the map extrapolates with the mean
    real-time factor of the anchors within `_EXTRAPOLATION_SPAN_SEC` wall
    seconds of that end (a duplicate pair there would otherwise give slope 0).
    """

    def __init__(self, anchors: Iterable[tuple[float, float]]) -> None:
        first_wall: dict[float, float] = {}
        for wall, sim in anchors:
            if sim not in first_wall or wall < first_wall[sim]:
                first_wall[sim] = wall
        points = sorted((w, s) for s, w in first_wall.items())
        # Drop any anchor whose sim value is not above its predecessor's.
        cleaned: list[tuple[float, float]] = []
        for w, sim in points:
            if not cleaned or (w > cleaned[-1][0] and sim > cleaned[-1][1]):
                cleaned.append((w, sim))
        if len(cleaned) < 2:
            raise ValueError("need two sim_t anchors")
        self.walls = [p[0] for p in cleaned]
        self.sims = [p[1] for p in cleaned]

    def _end_slope(self, at_end: bool) -> float:
        w, s = self.walls, self.sims
        if at_end:
            j = len(w) - 1
            i = next((k for k in range(j - 1, -1, -1) if w[j] - w[k] >= _EXTRAPOLATION_SPAN_SEC), 0)
        else:
            i = 0
            j = next(
                (k for k in range(1, len(w)) if w[k] - w[0] >= _EXTRAPOLATION_SPAN_SEC),
                len(w) - 1,
            )
        return (s[j] - s[i]) / (w[j] - w[i])

    def __call__(self, wall: float) -> float:
        w, s = self.walls, self.sims
        if wall >= w[-1]:
            return s[-1] + self._end_slope(True) * (wall - w[-1])
        if wall <= w[0]:
            return s[0] + self._end_slope(False) * (wall - w[0])
        i = bisect.bisect_right(w, wall)
        return s[i - 1] + (s[i] - s[i - 1]) * (wall - w[i - 1]) / (w[i] - w[i - 1])


def _commands_by_id(bundle: Path) -> dict[str, dict[str, Any]]:
    commands: dict[str, dict[str, Any]] = {}
    for path in sorted((bundle / "decisions").glob("*.json")):
        if path.name.startswith("tasks_"):
            continue
        artifact = json.loads(path.read_text())
        found = [artifact.get("dispatched_command")]
        phases = artifact.get("junction_phases") or {}
        found += [p.get("command") for p in phases.get("phases", []) or []]
        found.append(phases.get("fallback_command"))
        for command in found:
            if command and command.get("command_id"):
                commands[command["command_id"]] = command
    return commands


def _ground_truth(bundle: Path) -> list[tuple[float, dict[str, Any]]]:
    for name in ("gt/ground_truth.jsonl", "ground_truth/ground_truth.jsonl"):
        path = bundle / name
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                return [
                    (float(row["sim_time_sec"]), row["robots"])
                    for row in map(json.loads, handle)
                ]
    return []


def estimate_clock_offset(
    bundle: Path, gt: list[tuple[float, dict[str, Any]]]
) -> float | None:
    """ROS sim time minus GT time, from M1's sim-stamped poses of moving robots.

    Args:
        bundle: The bundle (reads `m5_scene.jsonl`).
        gt: The bundle's GT rows.

    Returns:
        The offset in seconds (0.00-1.50 s, 0.01 s steps) that minimises the
        median M1-to-GT position error, or None without M1 data.
    """
    path = bundle / "m5_scene.jsonl"
    if not path.is_file() or not gt:
        return None
    samples = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            for robot in json.loads(line).get("scene", {}).get("robots", []):
                if robot.get("status") in ("MOVING", "SLOW") and robot.get("stamp") is not None:
                    samples.append(
                        (float(robot["stamp"]), robot["robot_id"], robot["x"], robot["y"])
                    )
    samples = samples[::3]
    if not samples:
        return None
    times = [t for t, _ in gt]

    def at(t: float, robot: str) -> tuple[float, float] | None:
        i = min(max(bisect.bisect_left(times, t), 1), len(gt) - 1)
        a, b = gt[i - 1][1].get(robot), gt[i][1].get(robot)
        if a is None or b is None or times[i] <= times[i - 1]:
            return None
        f = (t - times[i - 1]) / (times[i] - times[i - 1])
        return (a["x"] + f * (b["x"] - a["x"]), a["y"] + f * (b["y"] - a["y"]))

    best: tuple[float, float] | None = None
    for k in range(151):
        offset = k * 0.01
        errors = sorted(
            math.hypot(p[0] - x, p[1] - y)
            for t, robot, x, y in samples
            if (p := at(t - offset, robot)) is not None
        )
        if errors:
            median = errors[len(errors) // 2]
            if best is None or median < best[1]:
                best = (offset, median)
    return None if best is None else best[0]


def _odom_rows(
    gt: list[tuple[float, dict[str, Any]]],
    robot: str,
    t0: float,
    t1: float,
    offset: float,
) -> list[list[float]]:
    spawn = next((r[robot] for _, r in gt if robot in r), None)
    if spawn is None:
        return []
    c, s = math.cos(spawn["theta"]), math.sin(spawn["theta"])
    rows = []
    for t_gt, robots in gt:
        t = t_gt + offset
        if t < t0 or t > t1 or robot not in robots:
            continue
        r = robots[robot]
        dx, dy = r["x"] - spawn["x"], r["y"] - spawn["y"]
        turn = r["theta"] - spawn["theta"]
        yaw = math.atan2(math.sin(turn), math.cos(turn))
        rows.append(
            [round(t, 4), round(c * dx + s * dy, 5), round(-s * dx + c * dy, 5), round(yaw, 5)]
        )
    return rows


def _bag_odometry(bundle: Path) -> dict[str, list[list[float]]]:
    """`/<robot>/odom` rows `[stamp, x, y, yaw]` from the bundle's rosbag, if any."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mcap_lite

    rows: dict[str, list[list[float]]] = {}
    for bag in sorted((bundle / "bag").glob("*.mcap")) if (bundle / "bag").is_dir() else []:
        topics = {f"/robot_{i}/odom" for i in range(1, 10)}
        for topic, _log_time, payload in mcap_lite.iter_messages(bag, topics):
            odom = mcap_lite.decode_odometry(payload)
            yaw = 2.0 * math.atan2(odom["qz"], odom["qw"])
            rows.setdefault(topic.split("/")[1], []).append(
                [round(odom["stamp"], 4), round(odom["x"], 5), round(odom["y"], 5), round(yaw, 5)]
            )
    for robot_rows in rows.values():
        robot_rows.sort()
    return rows


def _parse_logs(bundle: Path) -> dict[str, Any]:
    anchors: list[tuple[float, float]] = []
    received: dict[tuple[str, str], str] = {}
    statuses: dict[tuple[str, str], list[tuple[float, str]]] = {}
    handover: dict[tuple[str, str], float] = {}
    admits: list[tuple[str, str, str, float]] = []
    escort_events: list[tuple[float, str, str, str]] = []
    holds: list[tuple[float, str, str]] = []
    for name in ("m4.log", "m5.log", "launcher.log", "isaac.log"):
        path = bundle / name
        if not path.is_file():
            continue
        with path.open(errors="replace") as handle:
            for line in handle:
                if (
                    "sim_t=" not in line
                    and "status published" not in line
                    and "command received" not in line
                    and "escort robot" not in line
                    and "relay hold" not in line
                ):
                    continue
                match = _LINE.search(line)
                if match is None:
                    continue
                wall, text = float(match.group(1)), match.group(2)
                sim = _SIM_T.search(text)
                if sim is not None:
                    anchors.append((wall, float(sim.group(1))))
                if name == "isaac.log":
                    hold = _HOLD.search(text)
                    if hold is not None:
                        holds.append((wall, hold.group(2), hold.group(1)))
                    continue
                if name != "m4.log":
                    continue
                if (m := _RECEIVED.search(text)) is not None:
                    received.setdefault((m.group(1), m.group(2)), m.group(3))
                elif (m := _STATUS.search(text)) is not None:
                    statuses.setdefault((m.group(1), m.group(2)), []).append((wall, m.group(3)))
                elif (m := _HANDOVER.search(text)) is not None:
                    handover.setdefault((m.group(2), m.group(1)), float(m.group(3)))
                elif (m := _ADMIT.search(text)) is not None:
                    if m.group(4) != "None":
                        admits.append((m.group(1), m.group(3), m.group(4), float(m.group(5))))
                elif (m := _ESCORT.search(text)) is not None:
                    escort_events.append((wall, m.group(1), m.group(2), m.group(3)))
    return {
        "anchors": anchors,
        "received": received,
        "statuses": statuses,
        "handover": handover,
        "admits": admits,
        "escort_events": escort_events,
        "holds": holds,
    }


def _hold_intervals(
    holds: list[tuple[float, str, str]], robot: str, to_sim: _WallToSim
) -> list[list[float]]:
    intervals: list[list[float]] = []
    start: float | None = None
    for wall, rid, kind in sorted(holds):
        if rid != robot:
            continue
        if kind == "engaged" and start is None:
            start = to_sim(wall)
        elif kind == "released" and start is not None:
            intervals.append([round(start, 3), round(to_sim(wall), 3)])
            start = None
    if start is not None:
        intervals.append([round(start, 3), 1e9])
    return intervals


def _action_params(command: dict[str, Any] | None, robot: str) -> dict[str, Any] | None:
    for action in (command or {}).get("actions", []):
        if action.get("robot_id") == robot:
            return action.get("parameters") or {}
    return None


def build_episodes(bundle: Path) -> list[dict[str, Any]]:
    """Every raw-cmd_vel primitive episode of one bundle (see module docstring)."""
    logs = _parse_logs(bundle)
    to_sim = _WallToSim(logs["anchors"])
    commands = _commands_by_id(bundle)
    gt = _ground_truth(bundle)
    estimated = estimate_clock_offset(bundle, gt)
    offset = 0.5 if estimated is None else estimated
    gt_end = (gt[-1][0] + offset) if gt else 0.0
    bag_rows = _bag_odometry(bundle)
    episodes: list[dict[str, Any]] = []

    def odom_rows(robot: str, t0: float, t1: float) -> tuple[str, list[list[float]]]:
        if robot in bag_rows:
            return "bag", [r for r in bag_rows[robot] if t0 <= r[0] <= t1]
        return "gt", _odom_rows(gt, robot, t0, t1, offset)

    def add(
        primitive, command_id, robot, params, start, end, live, live_detail="", source="exact"
    ):
        if live == "COMPLETED":
            # The mapped end can fall a little before the recorded poses
            # reach the target; the replayed primitive stops itself there.
            end += _END_SLACK_SEC
        end = min(end, gt_end)
        if end <= start:
            return None
        odom_source, rows = odom_rows(robot, start - 0.5, end + 0.5)
        episode = {
                "bundle": bundle.name,
                "command_id": command_id,
                "robot_id": robot,
                "primitive": primitive,
                "params": params,
                "start_sim": round(start, 3),
                "end_sim": round(end, 3),
                "live_outcome": live,
                "live_detail": live_detail,
                "start_source": source,
                "clock_offset_s": offset,
                "clock_offset_estimated": estimated is not None,
                "held": _hold_intervals(logs["holds"], robot, to_sim),
                "odom_source": odom_source,
                "odom": rows,
            }
        episodes.append(episode)
        return episode

    for (command_id, robot), action in sorted(logs["received"].items()):
        if action not in ("yield", "reverse"):
            continue
        params = _action_params(commands.get(command_id), robot)
        stream = logs["statuses"].get((command_id, robot), [])
        if params is None or not stream or stream[0][1] != "ACTIVE":
            continue
        distance = float(params.get("backup_distance_m", 0.3))
        pull_off = params.get("pull_off_lateral_m") if action == "yield" else None
        exact = logs["handover"].get((command_id, robot))
        if exact is not None:
            start, start_source = exact, "handover_sim_t"
        else:
            mapped = to_sim(stream[0][0])
            window = odom_rows(robot, mapped - _ONSET_BEFORE_SEC, mapped + _ONSET_AFTER_SEC)[1]
            onset = motion_onset(window, mapped, turn_first=abs(distance) == 0.0)
            if onset is None:
                start, start_source = mapped, "mapped_wall"
            else:
                start, start_source = onset - _START_LEAD_SEC, "gt_onset"
        nxt = stream[1] if len(stream) > 1 else None
        end = to_sim(nxt[0]) if nxt else start + _OPEN_END_SEC
        if nxt is None:
            live = "no terminal line"
        elif nxt[1] == "FAILED":
            live = "FAILED"
        else:
            live = "COMPLETED"
        line_turn = backup_line_turn(params) if action == "yield" else None
        backup_episode = None
        if abs(distance) > 0.0:
            backup_episode = add(
                "backup",
                command_id,
                robot,
                {
                    "distance_m": distance,
                    "hold_start_line": params.get("backup_line_hold") is True,
                    "line_turn_rad": line_turn or 0.0,
                },
                start,
                end,
                live,
                source=start_source,
            )
        if pull_off is not None and nxt is not None and nxt[1] == "ACTIVE" and len(stream) > 2:
            after = stream[2]
            # The sidestep starts on the backup's COMPLETED tick, so the
            # replayed backup's completion is a sharper start than the
            # mapped wall time of the pull-off's ACTIVE line.
            pull_start, pull_source = to_sim(nxt[0]), "mapped_wall"
            if backup_episode is not None:
                chained = replay_episode(backup_episode, config=None)
                if chained["outcome"] == "COMPLETED":
                    pull_start, pull_source = chained["t"], "chained_backup"
            elif abs(distance) == 0.0:
                pull_start, pull_source = start, start_source
            add(
                "pull_off",
                command_id,
                robot,
                {"lateral_m": float(pull_off)},
                pull_start,
                to_sim(after[0]),
                "FAILED" if after[1] == "FAILED" else "COMPLETED",
                source=pull_source,
            )
    for command_id, passer, _escort_m, admit_sim in logs["admits"]:
        yielder_params = None
        for action in (commands.get(command_id) or {}).get("actions", []):
            if action.get("action") == "yield":
                yielder_params = action.get("parameters") or {}
        if yielder_params is None:
            continue
        plan = next((p for p in plan_crossing(yielder_params) if p.robot_id == passer), None)
        if plan is None or plan.escort_m is None:
            continue
        admit_wall = next(
            (w for w, s in zip(to_sim.walls, to_sim.sims, strict=True) if s >= admit_sim), None
        )
        terminal = next(
            (
                (w, status, detail)
                for w, rid, status, detail in logs["escort_events"]
                if rid == passer
                and status != "ACTIVE"
                and (admit_wall is None or w >= admit_wall - 5)
                and to_sim(w) >= admit_sim
            ),
            None,
        )
        turn = plan.escort_turn_rad
        add(
            "escort",
            command_id,
            passer,
            {
                "distance_m": float(plan.escort_m),
                "target_yaw_rad": 0.0 if turn is None else float(turn),
                "relative_to_start": turn is not None,
            },
            admit_sim,
            to_sim(terminal[0]) if terminal else admit_sim + _OPEN_END_SEC,
            terminal[1] if terminal else "no terminal line",
            terminal[2] if terminal else "",
        )
    return episodes


def motion_onset(
    rows: list[list[float]], near: float, turn_first: bool = False
) -> float | None:
    """Start of the motion nearest `near` in odom rows, for starts without a sim stamp.

    A candidate is a row after at least 1 s of rest (< 0.01 m and < 0.03 rad
    of change over that second) from which the robot moves 0.02 m or turns
    0.05 rad within 0.5 s. With `turn_first` (a pull-off, which starts by
    turning in place) rest only requires no rotation and the onset must be a
    turn with under 0.01 m of travel: a robot can still be rolling under
    Nav2 when the pull-off takes over.

    Args:
        rows: `[t, x, y, yaw]` rows around the mapped start.
        near: The mapped start.
        turn_first: Look for a turn-in-place onset.

    Returns:
        The candidate closest to `near`, or None.
    """
    def change(a: list[float], b: list[float]) -> tuple[float, float]:
        dyaw = abs(math.atan2(math.sin(b[3] - a[3]), math.cos(b[3] - a[3])))
        return math.hypot(b[1] - a[1], b[2] - a[2]), dyaw

    candidates = []
    for i, row in enumerate(rows):
        before = [q for q in rows[:i] if q[0] >= row[0] - 1.0]
        after = [q for q in rows[i:] if q[0] <= row[0] + 0.5]
        if not before or before[0][0] > row[0] - 0.9 or len(after) < 2:
            continue
        rest = change(before[0], row)
        go = change(row, after[-1])
        if turn_first:
            if rest[1] < 0.03 and go[1] >= 0.05 and go[0] < 0.01:
                candidates.append(row[0])
        elif rest[0] < 0.01 and rest[1] < 0.03 and (go[0] >= 0.02 or go[1] >= 0.05):
            candidates.append(row[0])
    if not candidates:
        return None
    return min(candidates, key=lambda t: abs(t - near))


def gt_motion(
    episode: dict[str, Any], after: float | None = None
) -> dict[str, float | None]:
    """GT displacement over the episode and the first stop after `after`.

    Args:
        episode: An exported episode.
        after: Only look for a stop after this sim time (e.g. once the
            primitive's drive phase has moved the robot); default: start.

    Returns:
        `moved_m` (max displacement from the start pose) and `stop_t`: the
        first sim time after `after`, once the robot has moved at least
        0.05 m, from which it stays within `_STOP_RADIUS_M` for
        `_STOP_HOLD_SEC` (None if it never does).
    """
    rows = [r for r in episode["odom"] if episode["start_sim"] <= r[0] <= episode["end_sim"]]
    if not rows:
        return {"moved_m": None, "stop_t": None}
    x0, y0 = rows[0][1], rows[0][2]
    moved = max(math.hypot(r[1] - x0, r[2] - y0) for r in rows)
    stop_t = None
    floor = episode["start_sim"] if after is None else after
    for i, r in enumerate(rows):
        if r[0] < floor or math.hypot(r[1] - x0, r[2] - y0) < 0.05:
            continue
        window = [q for q in rows[i:] if q[0] <= r[0] + _STOP_HOLD_SEC]
        if window[-1][0] - r[0] < _STOP_HOLD_SEC - 0.15:
            break
        if all(math.hypot(q[1] - r[1], q[2] - r[2]) <= _STOP_RADIUS_M for q in window):
            stop_t = r[0]
            break
    return {"moved_m": moved, "stop_t": stop_t}


def _field(name: str, value: float | None, spec: str) -> str:
    return f"{name}=-" if value is None else f"{name}={value:{spec}}"


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, default=None)
    parser.add_argument(
        "--pack",
        type=Path,
        default=None,
        help="also append every episode, one JSON line each, to this .jsonl.gz",
    )
    parser.add_argument("bundles", nargs="+", type=Path)
    args = parser.parse_args()
    packed = gzip.open(args.pack, "at", encoding="utf-8") if args.pack is not None else None
    for bundle in args.bundles:
        if not (bundle / "m4.log").is_file():
            print(f"{bundle.name}\tskipped: no m4.log")
            continue
        for episode in build_episodes(bundle):
            replay = replay_episode(episode, StallAbortConfig(enabled=True))
            motion = gt_motion(episode)
            ratios = ",".join(f"{k}:{v:.2f}" for k, v in sorted(replay["min_ratio"].items()))
            fired = replay["outcome"] == "FAILED" and replay["detail"].startswith("stall_abort")
            print(
                "\t".join(
                    [
                        bundle.name,
                        episode["command_id"][:8] + episode["command_id"][32:],
                        episode["robot_id"],
                        episode["primitive"],
                        f"{episode['start_sim']:.1f}-{episode['end_sim']:.1f}",
                        f"live={episode['live_outcome']}",
                        _field("gt_moved", motion["moved_m"], ".3f"),
                        _field("gt_stop", motion["stop_t"], ".1f"),
                        f"held={len(episode['held'])}",
                        f"odom={episode['odom_source']}",
                        f"start={episode['start_source']}",
                        (
                            f"replay={replay['outcome']}@{replay['t']:.1f}"
                            if replay["t"] is not None
                            else "replay=running"
                        ),
                        "FIRED" if fired else "-",
                        replay["detail"][:90] if fired else "",
                        f"min_ratio={ratios or '-'}",
                    ]
                )
            )
            if args.export is not None:
                args.export.mkdir(parents=True, exist_ok=True)
                name = (
                    f"{bundle.name}__{episode['command_id'][:8]}{episode['command_id'][32:]}"
                    f"__{episode['robot_id']}__{episode['primitive']}.json"
                )
                (args.export / name).write_text(json.dumps(episode, separators=(",", ":")))
            if packed is not None:
                packed.write(json.dumps(episode, separators=(",", ":")) + "\n")
    if packed is not None:
        packed.close()


if __name__ == "__main__":
    main()
