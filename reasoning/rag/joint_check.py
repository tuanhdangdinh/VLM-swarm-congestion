"""Joint check of per-group choices: what can be checked when their commands run together.

Shared by the offline VLM bench and, later, the live per-group gate. Each
chosen option is grounded again with `ground` (each one alone, as M3 always
grounds) and the commands are compared pairwise on the scene's poses:

- exact: a robot addressed by two commands (a hold in one and a move in the
  other included), and two yield retreat points closer than the safety
  radius;
- heuristic, timing-free: straight-line motion segments of one command within
  the safety radius of the other command's segments or robots.

Not covered: timing and order, Nav2 paths after an escort, swept footprints,
M4 latch interaction.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from reasoning.rag.cluster_options import Grounder
from reasoning.rag.retreat_shield import retreat_corridor, segment_distance
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.executable_options import ClusterOption
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

DEFAULT_SAFETY_RADIUS_M = 0.45


class JointCheck(BaseModel):
    """What can be checked offline when the chosen commands are issued together."""

    model_config = ConfigDict(frozen=True)

    n_commands: int
    # Exact, from the grounded commands: a robot addressed by two commands
    # (including a hold in one and a move in the other).
    shared_robots: tuple[str, ...] = ()
    # Exact: two yield retreat points closer than the safety radius.
    retreat_clashes: tuple[tuple[str, str], ...] = ()
    # Heuristic, timing-free: straight-line motion segments of one command
    # within the safety radius of another command's segments or robots.
    path_proximity: tuple[tuple[str, str], ...] = ()
    safety_radius_m: float

    @property
    def exact_conflict(self) -> bool:
        """Whether an exact check fired."""
        return bool(self.shared_robots or self.retreat_clashes)


_Segment = tuple[tuple[float, float], tuple[float, float]]


def _addressed(command: dict[str, Any]) -> set[str]:
    return {a["robot_id"] for a in command.get("actions") or []}


def _motions(pose: Mapping[str, RobotStateInput], command: dict[str, Any]) -> list[_Segment]:
    out: list[_Segment] = []
    for action in command.get("actions") or []:
        robot = pose.get(action["robot_id"])
        if robot is None:
            continue
        start = (float(robot.x), float(robot.y))
        params = action.get("parameters") or {}
        kind = action.get("action")
        if kind == "yield" and params.get("retreat_x_m") is not None:
            facing = params.get("backup_facing_rad", robot.theta)
            out += retreat_corridor(
                start,
                float(facing),
                float(params.get("backup_distance_m") or 0.0),
                (float(params["retreat_x_m"]), float(params["retreat_y_m"])),
            )
            order = params.get("crossing_order") or [params.get("passer_robot_id")]
            headings = params.get("crossing_escort_heading_rad") or [
                params.get("passer_escort_heading_rad")
            ]
            escorts = params.get("crossing_escort_m") or [params.get("passer_escort_distance_m")]
            for passer, heading, dist in zip(order, headings, escorts, strict=False):
                other = pose.get(passer)
                if other is None or heading is None or not dist:
                    continue
                p = (float(other.x), float(other.y))
                end = (p[0] + dist * math.cos(heading), p[1] + dist * math.sin(heading))
                out.append((p, end))
        elif kind == "reverse":
            dist = float(params.get("backup_distance_m") or 0.0)
            theta = float(robot.theta)
            end = (start[0] - dist * math.cos(theta), start[1] - dist * math.sin(theta))
            out.append((start, end))
        elif kind == "reroute":
            points = [start] + [(float(w[0]), float(w[1])) for w in params.get("waypoints") or []]
            out += list(itertools.pairwise(points))
    return out


def _stations(pose: Mapping[str, RobotStateInput], command: dict[str, Any]) -> list[_Segment]:
    points = {rid: (float(r.x), float(r.y)) for rid, r in pose.items()}
    return [(points[r], points[r]) for r in sorted(_addressed(command)) if r in points]


def _retreat(command: dict[str, Any]) -> tuple[float, float] | None:
    for action in command.get("actions") or []:
        params = action.get("parameters") or {}
        if action.get("action") == "yield" and params.get("retreat_x_m") is not None:
            return (float(params["retreat_x_m"]), float(params["retreat_y_m"]))
    return None


def joint_check(
    snapshot: SnapshotFrame,
    chosen: Mapping[str, ClusterOption | None],
    ground: Grounder,
    geometry: SceneGeometry | None,
) -> JointCheck:
    """Check the chosen options against each other as if issued together (scene only).

    Args:
        snapshot: The analysed scene (robot poses).
        chosen: Label -> chosen option (None for `none_feasible`).
        ground: Grounds one decision into an M3 command, as for enumeration.
        geometry: The episode geometry; its `robot.safety_radius_m` is the
            radius (`DEFAULT_SAFETY_RADIUS_M` when None).

    Returns:
        The exact checks (shared robots, retreat clashes) and the heuristic
        path-proximity pairs.
    """
    radius = geometry.robot.safety_radius_m if geometry is not None else DEFAULT_SAFETY_RADIUS_M
    pose = {r.robot_id: r for r in snapshot.robots}
    commands = {
        label: ground(option.decision()) for label, option in chosen.items() if option is not None
    }
    shared: set[str] = set()
    clashes: list[tuple[str, str]] = []
    near: list[tuple[str, str]] = []
    for (la, ca), (lb, cb) in itertools.combinations(commands.items(), 2):
        shared |= _addressed(ca) & _addressed(cb)
        ra = _retreat(ca)
        rb = _retreat(cb)
        if ra is not None and rb is not None and math.dist(ra, rb) < radius:
            clashes.append((la, lb))
        ma, mb = _motions(pose, ca), _motions(pose, cb)
        sa, sb = ma + _stations(pose, ca), mb + _stations(pose, cb)
        close = any(segment_distance(*x, *y) < radius for x in ma for y in sb) or any(
            segment_distance(*x, *y) < radius for x in mb for y in sa
        )
        if close:
            near.append((la, lb))
    return JointCheck(
        n_commands=len(commands),
        shared_robots=tuple(sorted(shared)),
        retreat_clashes=tuple(clashes),
        path_proximity=tuple(near),
        safety_radius_m=radius,
    )


__all__ = ["DEFAULT_SAFETY_RADIUS_M", "JointCheck", "joint_check"]
