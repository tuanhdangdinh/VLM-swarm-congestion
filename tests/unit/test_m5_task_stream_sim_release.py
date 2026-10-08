"""Sim-time release stagger for the v3 S1 task stream (prereg-v3 A12(ii), S1-10).

Pure tracker/config tests plus node-level tests on the ROS2 stand-ins of
`test_m5_node_probe`. The registered window is Delta in (0, 4.42) sim-s; the
sim-time stagger must land every consecutive release inside it whatever the
real-time factor, and the wall-clock path must behave exactly as before.
"""
from __future__ import annotations

import random

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import TaskStreamConfig, load_config
from swarm_orchestrator.task_registry import TaskRegistry
from swarm_orchestrator.task_stream import (
    TaskStreamTracker,
    build_task_stream_plan,
    stream_initial_tasks,
    stream_start_record,
)

from tests.unit.test_m5_node_probe import node_env  # noqa: F401  (fixture)
from tests.unit.test_m5_node_task_stream import NODES as NODE_NODES
from tests.unit.test_m5_node_task_stream import START as NODE_START
from tests.unit.test_m5_node_task_stream import (
    _feed,
    _make,
    _positions,
    _registry,
    _tasks_log,
)
from tests.unit.test_m5_task_stream import ROBOTS, S1_NODES, _orchestrator

DELTA_SIM = 4.0
WINDOW = (0.0, 4.42)
# M5's first scene in pilot episode 1 was stamped 29.6 sim-s: the M1 clock
# runs through bring-up, so an absolute schedule would release everyone here.
FIRST_STAMP = 29.6


def _sim_stream(**overrides) -> TaskStreamConfig:
    base = dict(
        enabled=True,
        nodes=S1_NODES,
        seed=7,
        forbidden_legs=(("Wp", "Wm"),),
        release_stagger_sim_sec=DELTA_SIM,
        dwell_sim_sec=5.0,
    )
    base.update(overrides)
    return TaskStreamConfig(**base)


def _tracker(stream: TaskStreamConfig | None = None) -> TaskStreamTracker:
    stream = stream or _sim_stream()
    return TaskStreamTracker(build_task_stream_plan(stream, ROBOTS), stream.dwell_sim_sec)


def _release_stamps(tracker: TaskStreamTracker, stamps, wall_of) -> dict[str, float]:
    released: dict[str, float] = {}
    for sim_t in stamps:
        for event in tracker.on_scene(sim_t, wall_of(sim_t)):
            if event.event == "released":
                released[event.robot_id] = event.sim_t
    return released


class TestConfig:
    def test_both_stagger_keys_set_is_rejected(self):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            _sim_stream(release_stagger_wall_sec=24.0)

    def test_both_keys_rejected_through_yaml_loading(self):
        raw = _orchestrator(_sim_stream()).model_dump(mode="json")
        assert "release_stagger_wall_sec" not in raw["task_stream"]
        raw["task_stream"]["release_stagger_wall_sec"] = 24.0
        with pytest.raises(ValidationError, match="mutually exclusive"):
            load_config(raw)

    def test_sim_config_round_trips_through_its_dump(self):
        config = _orchestrator(_sim_stream())
        reloaded = load_config(config.model_dump(mode="json"))
        assert reloaded.task_stream == config.task_stream
        assert reloaded.task_stream.release_clock == "sim"

    def test_wall_config_dump_is_unchanged(self):
        dumped = TaskStreamConfig(release_stagger_wall_sec=24.0).model_dump(mode="json")
        assert dumped["release_stagger_wall_sec"] == 24.0
        assert "release_stagger_sim_sec" not in dumped

    def test_sim_key_alone_selects_the_sim_clock(self):
        assert _sim_stream().release_clock == "sim"

    def test_wall_key_alone_keeps_the_wall_clock(self):
        stream = TaskStreamConfig(release_stagger_wall_sec=24.0)
        assert stream.release_clock == "wall"
        assert stream.release_stagger_sim_sec is None

    def test_default_is_the_wall_clock_at_four(self):
        stream = TaskStreamConfig()
        assert stream.release_clock == "wall"
        assert stream.release_stagger_wall_sec == 4.0

    def test_non_positive_sim_stagger_is_rejected(self):
        with pytest.raises(ValidationError):
            _sim_stream(release_stagger_sim_sec=0.0)


class TestPlan:
    def test_sim_plan_carries_sim_offsets_only(self):
        plan = build_task_stream_plan(_sim_stream(), ROBOTS)
        assert plan.release_offsets_wall_sec is None
        assert plan.release_offsets_sim_sec == {
            rid: index * DELTA_SIM for index, rid in enumerate(ROBOTS)
        }

    def test_sim_plan_initial_tasks_carry_no_wall_delay(self):
        plan = build_task_stream_plan(_sim_stream(), ROBOTS)
        roster = _orchestrator(_sim_stream()).initial_tasks
        assert all(t.start_delay_sec == 0.0 for t in stream_initial_tasks(plan, roster).values())

    def test_wall_plan_is_unchanged(self):
        plan = build_task_stream_plan(_sim_stream(release_stagger_sim_sec=None), ROBOTS)
        assert plan.release_offsets_sim_sec is None
        assert plan.release_offsets_wall_sec == {
            rid: index * 4.0 for index, rid in enumerate(ROBOTS)
        }

    def test_wall_stream_start_record_has_no_sim_keys(self):
        stream = _sim_stream(release_stagger_sim_sec=None, release_stagger_wall_sec=24.0)
        record = stream_start_record(build_task_stream_plan(stream, ROBOTS), stream)
        assert "release_clock" not in record
        assert "release_offsets_sim_sec" not in record
        assert "release_stagger_sim_sec" not in record
        assert record["release_stagger_wall_sec"] == 24.0

    def test_sim_stream_start_record_names_the_sim_schedule(self):
        stream = _sim_stream()
        record = stream_start_record(build_task_stream_plan(stream, ROBOTS), stream)
        assert record["release_clock"] == "sim"
        assert record["release_stagger_sim_sec"] == DELTA_SIM
        assert record["release_offsets_sim_sec"]["robot_5"] == 4 * DELTA_SIM
        assert record["release_offsets_wall_sec"] is None
        assert record["release_stagger_wall_sec"] is None


class TestTrackerRelease:
    def test_first_scene_releases_robot_k0_only_with_its_sim_t(self):
        tracker = _tracker()
        events = tracker.on_scene(FIRST_STAMP, 100.0)
        released = [e for e in events if e.event == "released"]
        assert [e.robot_id for e in released] == ["robot_1"]
        assert released[0].sim_t == FIRST_STAMP
        assert [e.event for e in events] == ["released", "issued"]

    def test_offsets_count_from_the_first_scene_not_the_absolute_clock(self):
        tracker = _tracker()
        tracker.on_scene(FIRST_STAMP, 0.0)
        assert tracker.sim_releases_due(FIRST_STAMP + DELTA_SIM - 0.01) == []
        assert tracker.sim_releases_due(FIRST_STAMP + DELTA_SIM) == ["robot_2"]

    def test_wall_path_tracker_never_releases_on_scenes(self):
        tracker = _tracker(_sim_stream(release_stagger_sim_sec=None))
        events = tracker.on_scene(FIRST_STAMP + 100.0, 0.0)
        assert [e for e in events if e.event == "released"] == []
        assert tracker.phase("robot_2") == "held"

    def test_clock_reset_releases_nothing(self):
        tracker = _tracker()
        tracker.on_scene(FIRST_STAMP + 10.0, 0.0)
        before = {rid: tracker.phase(rid) for rid in ROBOTS}
        assert tracker.on_scene(FIRST_STAMP + 1.0, 1.0) == []
        assert {rid: tracker.phase(rid) for rid in ROBOTS} == before

    def test_a_late_scene_releases_every_due_robot_on_that_scene(self):
        tracker = _tracker()
        tracker.on_scene(FIRST_STAMP, 0.0)
        events = tracker.on_scene(FIRST_STAMP + 2 * DELTA_SIM + 0.1, 1.0)
        assert [e.robot_id for e in events if e.event == "released"] == ["robot_2", "robot_3"]

    @pytest.mark.parametrize("rtf", [0.1, 0.129, 0.164, 0.188, 0.214, 0.5, 1.0])
    @pytest.mark.parametrize("scene_period_sim", [1 / 30, 0.1, 0.2, 0.4])
    def test_delta_lands_in_the_registered_window_at_any_rtf(self, rtf, scene_period_sim):
        rng = random.Random(f"{rtf}:{scene_period_sim}")
        stamps, sim_t = [], FIRST_STAMP
        while sim_t < FIRST_STAMP + 5 * DELTA_SIM + 1.0:
            stamps.append(round(sim_t, 6))
            # Irregular delivery: gaps jitter but stay at most the period.
            sim_t += scene_period_sim * rng.uniform(0.5, 1.0)
        # Wall time is RTF-scaled with delivery jitter; the schedule must not
        # read it at all.
        released = _release_stamps(
            _tracker(), stamps, lambda s: s / rtf + rng.uniform(0.0, 2.0)
        )
        assert sorted(released) == ROBOTS
        times = [released[rid] for rid in ROBOTS]
        deltas = [b - a for a, b in zip(times, times[1:], strict=False)]
        for delta in deltas:
            assert WINDOW[0] < delta < WINDOW[1]
            assert DELTA_SIM - scene_period_sim < delta < DELTA_SIM + scene_period_sim

    def test_delta_is_identical_across_rtfs_for_the_same_stamps(self):
        stamps = [FIRST_STAMP + 0.05 * i for i in range(500)]
        by_rtf = [
            _release_stamps(_tracker(), stamps, lambda s, r=rtf: s / r)
            for rtf in (0.12, 0.164, 0.3, 1.0)
        ]
        assert all(result == by_rtf[0] for result in by_rtf)


class TestRegistryHold:
    def test_held_robots_are_never_released_by_the_wall_clock(self):
        registry = TaskRegistry()
        plan = build_task_stream_plan(_sim_stream(), ROBOTS)
        roster = _orchestrator(_sim_stream()).initial_tasks
        registry.load_assignments(stream_initial_tasks(plan, roster), 0.0, held=ROBOTS)
        assert registry.release_due(1e9) == []
        assert all(registry.is_pending(rid) for rid in ROBOTS)

    def test_explicit_release_frees_only_pending_robots(self):
        registry = TaskRegistry()
        plan = build_task_stream_plan(_sim_stream(), ROBOTS)
        roster = _orchestrator(_sim_stream()).initial_tasks
        registry.load_assignments(stream_initial_tasks(plan, roster), 0.0, held=ROBOTS[:2])
        assert registry.release(["robot_1", "robot_5"]) == ["robot_1"]
        assert not registry.is_pending("robot_1")
        assert registry.is_pending("robot_2")


def _sim_node_stream(**overrides) -> TaskStreamConfig:
    base = dict(
        enabled=True, nodes=NODE_NODES, seed=42, start_nodes=NODE_START,
        release_stagger_sim_sec=DELTA_SIM, dwell_sim_sec=5.0, tasks_per_robot=3,
    )
    base.update(overrides)
    return TaskStreamConfig(**base)


class TestNodeSimRelease:
    def test_every_robot_starts_held(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        registry = _registry(node)
        assert registry["robot_1"]["start_pending"] is True
        assert registry["robot_2"]["start_pending"] is True
        assert [r["event"] for r in _tasks_log(node)] == ["stream_start"]

    def test_wall_time_alone_releases_nobody(self, node_env, tmp_path):  # noqa: F811
        node, clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        clock.t += 10_000.0
        node._on_timer()
        assert node._registry.is_pending("robot_1")
        assert node._registry.is_pending("robot_2")
        assert node.get_logger().matching("release before any scene") == []
        assert not any(r["event"] == "release_before_scene" for r in _tasks_log(node))

    def test_first_scene_releases_robot_1_with_a_sim_t(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        _feed(node, FIRST_STAMP, _positions(node))
        assert "start_pending" not in _registry(node)["robot_1"]
        assert _registry(node)["robot_2"]["start_pending"] is True
        released = [r for r in _tasks_log(node) if r["event"] == "released"]
        assert [(r["robot_id"], r["sim_t"]) for r in released] == [("robot_1", FIRST_STAMP)]
        assert node.get_logger().matching("sim release stagger elapsed")

    def test_scene_at_the_offset_releases_robot_2(self, node_env, tmp_path):  # noqa: F811
        node, clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        _feed(node, FIRST_STAMP, _positions(node))
        clock.t += 1.0
        _feed(node, FIRST_STAMP + DELTA_SIM - 0.05, _positions(node))
        assert node._registry.is_pending("robot_2")
        clock.t += 1.0
        _feed(node, FIRST_STAMP + DELTA_SIM + 0.03, _positions(node))
        assert not node._registry.is_pending("robot_2")
        released = [r for r in _tasks_log(node) if r["event"] == "released"]
        assert released[-1]["robot_id"] == "robot_2"
        assert released[-1]["sim_t"] - released[0]["sim_t"] == pytest.approx(DELTA_SIM + 0.03)

    def test_dropped_frames_release_nobody(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        _feed(node, FIRST_STAMP, _positions(node), dropped=True)
        assert node._registry.is_pending("robot_1")

    def test_stream_start_record_names_the_sim_schedule(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path, stream=_sim_node_stream())
        record = _tasks_log(node)[0]
        assert record["release_clock"] == "sim"
        assert record["release_offsets_sim_sec"] == {"robot_1": 0.0, "robot_2": DELTA_SIM}
        assert node.get_logger().matching("release_offsets_sim_sec=")


class TestNodeWallPathUnchanged:
    def test_wall_stream_start_record_keeps_its_key_set(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        record = _tasks_log(node)[0]
        assert "release_clock" not in record
        assert "release_offsets_sim_sec" not in record
        assert record["release_offsets_wall_sec"] == {"robot_1": 0.0, "robot_2": 4.0}
        assert node.get_logger().matching("sim release stagger") == []

    def test_wall_scenes_release_nobody(self, node_env, tmp_path):  # noqa: F811
        node, _clock, _ = _make(node_env, tmp_path)
        _feed(node, FIRST_STAMP + 100.0, _positions(node))
        assert node._registry.is_pending("robot_2")
