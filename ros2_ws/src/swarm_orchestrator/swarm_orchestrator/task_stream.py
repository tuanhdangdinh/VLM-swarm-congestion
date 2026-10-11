"""v3 S1 (MAPD-5) task-stream schedule and per-episode bookkeeping for M5 (no rclpy).

Scene doc `2026-10-06-v3-scene-design.md` S1: five destination nodes per robot,
each different from the node the robot leaves, never a forbidden pair, drawn
uniformly from the episode seed; labels alternate starting with `pickup`;
releases are staggered in robot-id order, on M5's wall clock or (prereg-v3
A12(ii)) on the M1 scene clock; a robot dwells at each node and its
registry goal stays that node until the dwell ends (pop-on-dwell-end, the
registered dwell-versus-stall rule). Everything here is pure: the node feeds
it arrivals, releases and scene stamps and applies the returned events to the
registry.
"""
from __future__ import annotations

import hashlib
import math
import random
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from swarm_orchestrator.models import TaskAssignment, TaskStreamConfig

TaskStreamEventKind = Literal["released", "arrived", "dwell_complete", "issued", "robot_done"]
_ROBOT_ID_NUMBER = re.compile(r"^(.*?)(\d+)$")
# Goals are copied from the node table, never computed, so equality is exact
# in practice; the tolerance only absorbs a float round-trip through JSON.
_GOAL_MATCH_TOLERANCE_M = 1e-6


def robot_sort_key(robot_id: str) -> tuple[str, int, str]:
    """Natural robot-id order: `robot_2` before `robot_10`.

    Args:
        robot_id: A robot identifier.

    Returns:
        A sort key comparing the non-numeric prefix, then the trailing number.
    """
    match = _ROBOT_ID_NUMBER.match(robot_id)
    if match is None:
        return (robot_id, -1, robot_id)
    return (match.group(1), int(match.group(2)), robot_id)


def _rng(seed: int, stream: str) -> random.Random:
    # Derived through sha256, never `hash()`, so PYTHONHASHSEED cannot change
    # a registered seed's draw; each stream is salted so the start and task
    # draws are independent.
    digest = hashlib.sha256(f"vgu-task-stream:{stream}:{seed}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def draw_start_nodes(
    seed: int, robot_ids: Iterable[str], node_ids: Iterable[str]
) -> dict[str, str]:
    """Draw a distinct start node per robot from the episode seed.

    Args:
        seed: The episode's registered seed.
        robot_ids: The scene's robots.
        node_ids: The task nodes.

    Returns:
        Robot id -> start node.

    Raises:
        ValueError: If there are fewer nodes than robots.
    """
    robots = sorted(robot_ids, key=robot_sort_key)
    nodes = sorted(node_ids)
    if len(nodes) < len(robots):
        raise ValueError(f"{len(robots)} robots need {len(robots)} distinct start nodes")
    return dict(zip(robots, _rng(seed, "start").sample(nodes, len(robots)), strict=True))


def draw_task_sequences(
    seed: int,
    start_nodes: dict[str, str],
    node_ids: Iterable[str],
    tasks_per_robot: int,
    forbidden_legs: Iterable[Sequence[str]] = (),
) -> dict[str, tuple[str, ...]]:
    """Draw each robot's FIFO destination sequence from the episode seed.

    Each destination is uniform over the nodes other than the one the robot
    leaves, minus that node's forbidden partners.

    Args:
        seed: The episode's registered seed.
        start_nodes: Robot id -> the node it starts on.
        node_ids: The task nodes.
        tasks_per_robot: Sequence length (N_T).
        forbidden_legs: Unordered node pairs never drawn as one leg.

    Returns:
        Robot id -> its destination node ids, in task order.

    Raises:
        ValueError: If some node has no legal next node.
    """
    nodes = sorted(node_ids)
    forbidden = {frozenset(leg) for leg in forbidden_legs}
    rng = _rng(seed, "tasks")
    sequences: dict[str, tuple[str, ...]] = {}
    for robot_id in sorted(start_nodes, key=robot_sort_key):
        current = start_nodes[robot_id]
        drawn: list[str] = []
        for _ in range(tasks_per_robot):
            candidates = [
                node for node in nodes
                if node != current and frozenset((current, node)) not in forbidden
            ]
            if not candidates:
                raise ValueError(f"node {current!r} has no legal next node")
            current = rng.choice(candidates)
            drawn.append(current)
        sequences[robot_id] = tuple(drawn)
    return sequences


class StreamTask(BaseModel):
    """One registered task: a destination node with its registry label."""

    model_config = ConfigDict(frozen=True)

    task_index: int = Field(ge=0)
    node: str = Field(min_length=1)
    label: str = Field(min_length=1)
    goal: tuple[float, float]


class TaskStreamPlan(BaseModel):
    """The full drawn schedule of one episode, written as the first JSONL record."""

    model_config = ConfigDict(frozen=True)

    seed: int
    start_nodes: dict[str, str]
    # True when `start_nodes` came from the seed, False when the config pinned it.
    start_nodes_drawn: bool
    tasks: dict[str, tuple[StreamTask, ...]]
    # Exactly one of the two is set: wall offsets ride `start_delay_sec`;
    # sim offsets count from the first scene stamp the stream sees.
    release_offsets_wall_sec: dict[str, float] | None
    release_offsets_sim_sec: dict[str, float] | None = None

    @property
    def tasks_total(self) -> int:
        """Total registered tasks over every robot (N_T x N_A)."""
        return sum(len(queue) for queue in self.tasks.values())


def build_task_stream_plan(config: TaskStreamConfig, robot_ids: Iterable[str]) -> TaskStreamPlan:
    """Draw one episode's schedule from the stream config.

    Args:
        config: An enabled `task_stream` block (its validator guarantees a seed).
        robot_ids: The registry's robots (`initial_tasks`).

    Returns:
        The plan: start nodes, every robot's labelled tasks, and the release
        offsets on the configured clock (the other clock's offsets are None).

    Raises:
        ValueError: If the config is disabled or carries no seed.
    """
    if not config.enabled or config.seed is None:
        raise ValueError("build_task_stream_plan needs an enabled task_stream with a seed")
    robots = sorted(robot_ids, key=robot_sort_key)
    drawn = config.start_nodes is None
    start_nodes = (
        draw_start_nodes(config.seed, robots, config.nodes)
        if config.start_nodes is None
        else {rid: config.start_nodes[rid] for rid in robots}
    )
    sequences = draw_task_sequences(
        config.seed, start_nodes, config.nodes, config.tasks_per_robot, config.forbidden_legs
    )
    labels = config.task_labels
    tasks = {
        rid: tuple(
            StreamTask(
                task_index=index,
                node=node,
                label=labels[index % len(labels)],
                goal=config.nodes[node],
            )
            for index, node in enumerate(sequences[rid])
        )
        for rid in robots
    }
    sim_stagger = config.release_stagger_sim_sec
    return TaskStreamPlan(
        seed=config.seed,
        start_nodes=start_nodes,
        start_nodes_drawn=drawn,
        tasks=tasks,
        release_offsets_wall_sec=(
            {rid: index * config.release_stagger_wall_sec for index, rid in enumerate(robots)}
            if sim_stagger is None
            else None
        ),
        release_offsets_sim_sec=(
            None
            if sim_stagger is None
            else {rid: index * sim_stagger for index, rid in enumerate(robots)}
        ),
    )


def stream_initial_tasks(
    plan: TaskStreamPlan, initial_tasks: dict[str, TaskAssignment]
) -> dict[str, TaskAssignment]:
    """Registry assignments at startup: each robot's first task, held by its offset.

    Under the sim-time stagger no assignment carries a wall delay: the caller
    holds every robot in the registry instead (`TaskRegistry.load_assignments`
    `held`), and scene callbacks release them.

    Args:
        plan: The drawn schedule.
        initial_tasks: The configured roster; only `priority` is carried over.

    Returns:
        Robot id -> its first task's assignment, in `initial_tasks` order.
    """
    wall = plan.release_offsets_wall_sec
    return {
        rid: TaskAssignment(
            task=plan.tasks[rid][0].label,
            goal=plan.tasks[rid][0].goal,
            start_delay_sec=0.0 if wall is None else wall[rid],
            priority=assignment.priority,
        )
        for rid, assignment in initial_tasks.items()
    }


class TaskStreamEvent(BaseModel):
    """One task-stream transition, logged and appended to the tasks JSONL."""

    model_config = ConfigDict(frozen=True)

    event: TaskStreamEventKind
    robot_id: str = Field(min_length=1)
    task_index: int | None = None
    node: str | None = None
    label: str | None = None
    goal: tuple[float, float] | None = None
    wall_t: float
    sim_t: float | None = None


@dataclass
class _TaskTimes:
    issued_wall: float | None = None
    issued_sim: float | None = None
    arrived_wall: float | None = None
    arrived_sim: float | None = None
    dwell_complete_wall: float | None = None
    dwell_complete_sim: float | None = None


Phase = Literal["held", "traveling", "dwelling", "done"]


@dataclass
class _RobotState:
    phase: Phase
    index: int = 0
    # Sim time the current dwell is measured from; None while the arrival
    # came before any scene stamp, filled in by the next scene.
    dwell_from_sim: float | None = None


class TaskStreamTracker:
    """Per-robot queue state and the episode's per-task timestamps.

    Transitions: `held` -> (release) -> `traveling` -> (accepted arrival at
    the current node) -> `dwelling` -> (dwell elapsed in sim-s) -> the next
    task's `traveling`, or `done` after the last one. A task counts as
    completed when its dwell completes.
    """

    def __init__(self, plan: TaskStreamPlan, dwell_sim_sec: float,
                 horizon_sim_sec: float | None = None) -> None:
        self._plan = plan
        self._dwell = dwell_sim_sec
        self._horizon = horizon_sim_sec
        self._robots = {rid: _RobotState(phase="held") for rid in plan.tasks}
        self._times = {rid: [_TaskTimes() for _ in queue] for rid, queue in plan.tasks.items()}
        self._start_wall: float | None = None
        self._start_sim: float | None = None
        self._last_sim: float | None = None

    @property
    def plan(self) -> TaskStreamPlan:
        """The drawn schedule this tracker runs."""
        return self._plan

    @property
    def last_sim_t(self) -> float | None:
        """Highest scene stamp accepted so far; a lower one is a clock reset."""
        return self._last_sim

    @property
    def episode_start_sim(self) -> float | None:
        """Stamp of the first scene the stream saw; makespan is measured from it."""
        return self._start_sim

    def start(self, wall_t: float, released: Iterable[str]) -> list[TaskStreamEvent]:
        """Start the episode: the robots released at once begin their first task.

        Args:
            wall_t: M5's monotonic start time.
            released: Robots the registry does not hold (zero release offset).

        Returns:
            One `issued` event per released robot, in natural robot-id order.
        """
        self._start_wall = wall_t
        events: list[TaskStreamEvent] = []
        for robot_id in sorted(released, key=robot_sort_key):
            events.extend(self.on_release(robot_id, wall_t, None))
        return events

    def on_release(
        self, robot_id: str, wall_t: float, sim_t: float | None
    ) -> list[TaskStreamEvent]:
        """A held robot's stagger elapsed: its first task is issued now.

        Returns:
            `released` and `issued` events; empty when the robot was not held.
        """
        state = self._robots.get(robot_id)
        if state is None or state.phase != "held":
            return []
        state.phase = "traveling"
        released = TaskStreamEvent(event="released", robot_id=robot_id, wall_t=wall_t, sim_t=sim_t)
        return [released, self._issue(robot_id, wall_t, sim_t)]

    def on_arrival(
        self,
        robot_id: str,
        goal: tuple[float, float],
        wall_t: float,
        sim_t: float | None,
    ) -> TaskStreamEvent | None:
        """Start the dwell on an accepted arrival at the robot's current task node.

        Idempotent: an arrival while dwelling, held or done, or at any goal
        other than the current task's node, changes nothing.

        Args:
            robot_id: Robot the arrival gate accepted.
            goal: The goal it was accepted at.
            wall_t: Monotonic time of the acceptance.
            sim_t: Latest scene stamp, or None before any scene.

        Returns:
            The `arrived` event, or None when the arrival was ignored.
        """
        state = self._robots.get(robot_id)
        if state is None or state.phase != "traveling":
            return None
        task = self._plan.tasks[robot_id][state.index]
        if math.dist(goal, task.goal) > _GOAL_MATCH_TOLERANCE_M:
            return None
        state.phase = "dwelling"
        state.dwell_from_sim = sim_t
        times = self._times[robot_id][state.index]
        times.arrived_wall, times.arrived_sim = wall_t, sim_t
        return self._event("arrived", robot_id, task, wall_t, sim_t)

    def on_scene(self, sim_t: float, wall_t: float) -> list[TaskStreamEvent]:
        """Advance sim-time releases and dwell timers on one scene stamp (sim-s).

        A stamp older than the last one seen (M1 clock reset, late frame) is
        ignored: a dwell must never complete, and a sim-time release never
        fire, on a clock running backwards.

        Returns:
            Under the sim-time stagger, first the `released`/`issued` pairs of
            every held robot whose offset this stamp reaches; then
            `dwell_complete` events, each followed by the next task's `issued`
            or the robot's `robot_done`; each group in natural robot-id order.
        """
        if self._last_sim is not None and sim_t < self._last_sim:
            return []
        self._last_sim = sim_t
        if self._start_sim is None:
            self._start_sim = sim_t
        events: list[TaskStreamEvent] = []
        for robot_id in self.sim_releases_due(sim_t):
            events.extend(self.on_release(robot_id, wall_t, sim_t))
        for robot_id in sorted(self._robots, key=robot_sort_key):
            state = self._robots[robot_id]
            if state.phase != "dwelling":
                continue
            if state.dwell_from_sim is None:
                state.dwell_from_sim = sim_t
                times = self._times[robot_id][state.index]
                times.arrived_sim = sim_t
            if sim_t - state.dwell_from_sim < self._dwell:
                continue
            task = self._plan.tasks[robot_id][state.index]
            times = self._times[robot_id][state.index]
            times.dwell_complete_wall, times.dwell_complete_sim = wall_t, sim_t
            events.append(self._event("dwell_complete", robot_id, task, wall_t, sim_t))
            state.dwell_from_sim = None
            if state.index + 1 < len(self._plan.tasks[robot_id]):
                state.index += 1
                state.phase = "traveling"
                events.append(self._issue(robot_id, wall_t, sim_t))
            else:
                state.phase = "done"
                events.append(
                    TaskStreamEvent(event="robot_done", robot_id=robot_id, wall_t=wall_t,
                                    sim_t=sim_t)
                )
        return events

    def sim_releases_due(self, sim_t: float) -> list[str]:
        """Held robots whose sim-time release offset `sim_t` reaches.

        Offsets count from `episode_start_sim`, never from the absolute M1
        clock, so a stream whose first scene is already tens of sim-s in
        still spaces its releases by the stagger instead of releasing every
        robot at once.

        Args:
            sim_t: A scene stamp (sim-s).

        Returns:
            Robot ids in natural order; empty on the wall-clock path or
            before the first scene.
        """
        offsets = self._plan.release_offsets_sim_sec
        if offsets is None or self._start_sim is None:
            return []
        elapsed = sim_t - self._start_sim
        return [
            robot_id for robot_id in sorted(self._robots, key=robot_sort_key)
            if self._robots[robot_id].phase == "held" and offsets[robot_id] <= elapsed
        ]

    def current_task(self, robot_id: str) -> StreamTask | None:
        """The task whose node is the robot's registry goal, or None if unknown."""
        state = self._robots.get(robot_id)
        if state is None:
            return None
        return self._plan.tasks[robot_id][state.index]

    def departure(
        self, robot_id: str, sim_t: float | None
    ) -> tuple[tuple[float, float] | None, float] | None:
        """Where a robot goes after its current task node, and how long it dwells first.

        prereg-v3 A26(i): M3's retreat shield reads this beside the
        registry's current task node, so a robot that arrives, dwells and
        departs mid-maneuver is scored on the leg it will drive then.

        Args:
            robot_id: A stream robot.
            sim_t: The latest scene stamp (sim-s), or None before any.

        Returns:
            `(next_goal, dwell_sec)`: the next task's node (None after the
            last task) and the sim-s still to dwell at the current node (the
            full dwell while traveling, the remainder while dwelling). None
            for a held, finished or unknown robot.
        """
        state = self._robots.get(robot_id)
        if state is None or state.phase not in ("traveling", "dwelling"):
            return None
        queue = self._plan.tasks[robot_id]
        next_goal = queue[state.index + 1].goal if state.index + 1 < len(queue) else None
        dwell = self._dwell
        if state.phase == "dwelling" and state.dwell_from_sim is not None and sim_t is not None:
            dwell = max(0.0, self._dwell - (sim_t - state.dwell_from_sim))
        return next_goal, dwell

    def phase(self, robot_id: str) -> Phase | None:
        """The robot's queue phase, or None for a robot outside the stream."""
        state = self._robots.get(robot_id)
        return None if state is None else state.phase

    def completed_count(self, robot_id: str | None = None) -> int:
        """Tasks whose dwell completed, for one robot or the whole episode."""
        robots = self._times if robot_id is None else {robot_id: self._times[robot_id]}
        return sum(
            1 for queue in robots.values() for times in queue
            if times.dwell_complete_wall is not None
        )

    @property
    def all_done(self) -> bool:
        """Whether every robot's queue is empty."""
        return all(state.phase == "done" for state in self._robots.values())

    def manifest(self) -> dict[str, Any]:
        """Episode-level S1 bookkeeping, JSON-ready.

        `makespan_sim_sec` is the last dwell completion minus
        `episode_start_sim` (first scene stamp), and stays null until every
        queue is empty; `makespan_wall_sec` is the same on M5's clock from
        stream start. `tasks_completed_within_horizon` counts dwells completed
        within `horizon_sim_sec` of the episode start (null without a horizon
        or a sim start).
        """
        completions = [
            times.dwell_complete_sim
            for queue in self._times.values() for times in queue
            if times.dwell_complete_sim is not None
        ]
        complete = self.all_done
        makespan_sim = (
            max(completions) - self._start_sim
            if complete and completions and self._start_sim is not None
            else None
        )
        wall_completions = [
            times.dwell_complete_wall
            for queue in self._times.values() for times in queue
            if times.dwell_complete_wall is not None
        ]
        makespan_wall = (
            max(wall_completions) - self._start_wall
            if complete and wall_completions and self._start_wall is not None
            else None
        )
        within = None
        if self._horizon is not None and self._start_sim is not None:
            within = sum(1 for t in completions if t - self._start_sim <= self._horizon)
        return {
            "tasks_total": self._plan.tasks_total,
            "tasks_completed": self.completed_count(),
            "complete": complete,
            "per_robot_completed": {
                rid: self.completed_count(rid) for rid in sorted(self._times, key=robot_sort_key)
            },
            "episode_start_sim": self._start_sim,
            "makespan_sim_sec": makespan_sim,
            "makespan_wall_sec": makespan_wall,
            "horizon_sim_sec": self._horizon,
            "tasks_completed_within_horizon": within,
            "tasks": {
                rid: [
                    {
                        "task_index": task.task_index,
                        "node": task.node,
                        "label": task.label,
                        "issued_wall": times.issued_wall,
                        "issued_sim": times.issued_sim,
                        "arrived_wall": times.arrived_wall,
                        "arrived_sim": times.arrived_sim,
                        "dwell_complete_wall": times.dwell_complete_wall,
                        "dwell_complete_sim": times.dwell_complete_sim,
                    }
                    for task, times in zip(self._plan.tasks[rid], self._times[rid], strict=True)
                ]
                for rid in sorted(self._times, key=robot_sort_key)
            },
        }

    def _issue(self, robot_id: str, wall_t: float, sim_t: float | None) -> TaskStreamEvent:
        state = self._robots[robot_id]
        task = self._plan.tasks[robot_id][state.index]
        times = self._times[robot_id][state.index]
        times.issued_wall, times.issued_sim = wall_t, sim_t
        return self._event("issued", robot_id, task, wall_t, sim_t)

    @staticmethod
    def _event(
        kind: TaskStreamEventKind,
        robot_id: str,
        task: StreamTask,
        wall_t: float,
        sim_t: float | None,
    ) -> TaskStreamEvent:
        return TaskStreamEvent(
            event=kind,
            robot_id=robot_id,
            task_index=task.task_index,
            node=task.node,
            label=task.label,
            goal=task.goal,
            wall_t=wall_t,
            sim_t=sim_t,
        )


def stream_start_record(plan: TaskStreamPlan, config: TaskStreamConfig) -> dict[str, Any]:
    """The `stream_start` JSONL record: the whole drawn schedule and its parameters.

    Args:
        plan: The drawn schedule.
        config: The stream config it was drawn from.

    Returns:
        A JSON-ready record (without the run/session/clock envelope).
    """
    record = {
        "event": "stream_start",
        "seed": plan.seed,
        "nodes": {node: list(pose) for node, pose in sorted(config.nodes.items())},
        "start_nodes": dict(plan.start_nodes),
        "start_nodes_drawn": plan.start_nodes_drawn,
        "sequences": {rid: [task.node for task in queue] for rid, queue in plan.tasks.items()},
        "labels": {rid: [task.label for task in queue] for rid, queue in plan.tasks.items()},
        "release_offsets_wall_sec": (
            None
            if plan.release_offsets_wall_sec is None
            else dict(plan.release_offsets_wall_sec)
        ),
        "tasks_per_robot": config.tasks_per_robot,
        "tasks_total": plan.tasks_total,
        "forbidden_legs": [list(leg) for leg in config.forbidden_legs],
        "dwell_sim_sec": config.dwell_sim_sec,
        "release_stagger_wall_sec": config.release_stagger_wall_sec,
        "horizon_sim_sec": config.horizon_sim_sec,
        "finished_mode": config.finished_mode,
    }
    if plan.release_offsets_sim_sec is not None:
        # Sim-time path only, so a wall-clock record keeps its exact key set.
        record |= {
            "release_clock": "sim",
            "release_offsets_wall_sec": None,
            "release_stagger_wall_sec": None,
            "release_offsets_sim_sec": dict(plan.release_offsets_sim_sec),
            "release_stagger_sim_sec": config.release_stagger_sim_sec,
        }
    return record


def start_position_offsets(
    plan: TaskStreamPlan,
    nodes: dict[str, tuple[float, float]],
    positions: dict[str, tuple[float, float]],
) -> dict[str, float | None]:
    """Distance of each robot's first M1 position from its configured start node.

    Args:
        plan: The drawn schedule.
        nodes: Node id -> (x, y).
        positions: Robot id -> M1 (x, y), for robots M1 tracks.

    Returns:
        Robot id -> metres, None for a robot M1 does not report.
    """
    return {
        rid: (
            None if rid not in positions
            else round(math.dist(positions[rid], nodes[plan.start_nodes[rid]]), 3)
        )
        for rid in sorted(plan.start_nodes, key=robot_sort_key)
    }
