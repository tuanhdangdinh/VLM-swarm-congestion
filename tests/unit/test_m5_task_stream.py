"""Unit tests for the v3 S1 task-stream schedule, tracker and config (pure, no rclpy)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    OrchestratorConfig,
    TaskAssignment,
    TaskStreamConfig,
    load_config,
)
from swarm_orchestrator.task_registry import TaskRegistry
from swarm_orchestrator.task_stream import (
    TaskStreamTracker,
    build_task_stream_plan,
    draw_start_nodes,
    draw_task_sequences,
    robot_sort_key,
    start_position_offsets,
    stream_initial_tasks,
    stream_start_record,
)

S1_NODES = {
    "Wp": (-2.3, 0.35),
    "Wm": (-2.3, -0.35),
    "N": (0.0, 1.55),
    "S": (0.0, -1.55),
    "E": (2.3, 0.0),
}
ROBOTS = [f"robot_{i}" for i in range(1, 6)]


def _stream(**overrides) -> TaskStreamConfig:
    base = dict(
        enabled=True,
        nodes=S1_NODES,
        seed=7,
        forbidden_legs=(("Wp", "Wm"),),
        release_stagger_wall_sec=4.0,
        dwell_sim_sec=5.0,
    )
    base.update(overrides)
    return TaskStreamConfig(**base)


def _orchestrator(stream: TaskStreamConfig, **overrides) -> OrchestratorConfig:
    base = dict(
        stall_threshold_sec=12.0,
        progress_epsilon_m=0.1,
        cooldown_sec=15.0,
        command_timeout_sec=20.0,
        reasoning_backend_id="mock",
        initial_tasks={rid: TaskAssignment(task="t", goal=(0.0, 0.0)) for rid in ROBOTS},
        frame_dump_dir="/tmp/frames",
        task_stream=stream,
    )
    base.update(overrides)
    return OrchestratorConfig(**base)


def _tracker(dwell: float = 5.0, horizon: float | None = None, **stream_overrides):
    plan = build_task_stream_plan(_stream(**stream_overrides), ROBOTS)
    return TaskStreamTracker(plan, dwell, horizon), plan


def _arrive_and_dwell(tracker, plan, robot_id: str, sim_t: float, dwell: float = 5.0):
    task = tracker.current_task(robot_id)
    tracker.on_arrival(robot_id, task.goal, wall_t=sim_t, sim_t=sim_t)
    return tracker.on_scene(sim_t + dwell, wall_t=sim_t + dwell)


class TestSeededDraw:
    def test_start_nodes_identical_for_same_seed(self):
        assert draw_start_nodes(3, ROBOTS, S1_NODES) == draw_start_nodes(3, ROBOTS, S1_NODES)

    def test_start_nodes_distinct_per_robot(self):
        starts = draw_start_nodes(11, ROBOTS, S1_NODES)
        assert sorted(starts.values()) == sorted(S1_NODES)

    def test_start_nodes_independent_of_input_order(self):
        assert draw_start_nodes(5, reversed(ROBOTS), list(reversed(S1_NODES))) == (
            draw_start_nodes(5, ROBOTS, S1_NODES)
        )

    def test_start_nodes_differ_across_seeds(self):
        draws = {tuple(draw_start_nodes(seed, ROBOTS, S1_NODES).values()) for seed in range(20)}
        assert len(draws) > 1

    def test_start_nodes_raise_when_fewer_nodes_than_robots(self):
        with pytest.raises(ValueError):
            draw_start_nodes(1, ROBOTS, ["A", "B"])

    def test_sequences_identical_for_same_seed(self):
        starts = draw_start_nodes(9, ROBOTS, S1_NODES)
        first = draw_task_sequences(9, starts, S1_NODES, 5, [("Wp", "Wm")])
        assert first == draw_task_sequences(9, starts, S1_NODES, 5, [("Wp", "Wm")])

    def test_sequences_differ_across_seeds(self):
        starts = draw_start_nodes(0, ROBOTS, S1_NODES)
        draws = {
            tuple(draw_task_sequences(seed, starts, S1_NODES, 5, [("Wp", "Wm")])["robot_1"])
            for seed in range(20)
        }
        assert len(draws) > 1

    @pytest.mark.parametrize("seed", range(40))
    def test_sequences_never_repeat_node_or_take_forbidden_leg(self, seed):
        starts = draw_start_nodes(seed, ROBOTS, S1_NODES)
        sequences = draw_task_sequences(seed, starts, S1_NODES, 5, [("Wp", "Wm")])
        for robot_id, sequence in sequences.items():
            path = [starts[robot_id], *sequence]
            assert len(sequence) == 5
            for leg in zip(path, path[1:], strict=False):
                assert leg[0] != leg[1]
                assert set(leg) != {"Wp", "Wm"}

    def test_sequences_raise_when_a_node_has_no_successor(self):
        with pytest.raises(ValueError):
            draw_task_sequences(1, {"robot_1": "A"}, ["A", "B"], 2, [("A", "B")])

    def test_robot_sort_key_orders_numerically(self):
        assert sorted(["robot_10", "robot_2", "robot_1"], key=robot_sort_key) == [
            "robot_1", "robot_2", "robot_10",
        ]


class TestPlan:
    def test_plan_labels_alternate_starting_with_pickup(self):
        plan = build_task_stream_plan(_stream(), ROBOTS)
        labels = [task.label for task in plan.tasks["robot_3"]]
        assert labels == ["pickup", "delivery", "pickup", "delivery", "pickup"]

    def test_plan_goals_are_node_poses(self):
        plan = build_task_stream_plan(_stream(), ROBOTS)
        for task in plan.tasks["robot_2"]:
            assert task.goal == S1_NODES[task.node]

    def test_plan_release_offsets_stagger_in_robot_id_order(self):
        plan = build_task_stream_plan(_stream(release_stagger_wall_sec=4.0), ROBOTS)
        assert plan.release_offsets_wall_sec == {
            "robot_1": 0.0, "robot_2": 4.0, "robot_3": 8.0, "robot_4": 12.0, "robot_5": 16.0,
        }

    def test_plan_tasks_total_is_tasks_per_robot_times_robots(self):
        assert build_task_stream_plan(_stream(), ROBOTS).tasks_total == 25

    def test_plan_uses_pinned_start_nodes(self):
        pinned = dict(zip(ROBOTS, ["E", "S", "N", "Wm", "Wp"], strict=True))
        plan = build_task_stream_plan(_stream(start_nodes=pinned), ROBOTS)
        assert plan.start_nodes == pinned
        assert plan.start_nodes_drawn is False
        assert plan.tasks["robot_1"][0].node != "E"

    def test_plan_raises_when_stream_disabled(self):
        with pytest.raises(ValueError):
            build_task_stream_plan(TaskStreamConfig(), ROBOTS)

    def test_initial_tasks_hold_later_robots_by_offset(self):
        plan = build_task_stream_plan(_stream(), ROBOTS)
        roster = {rid: TaskAssignment(task="t", goal=(0.0, 0.0), priority=2) for rid in ROBOTS}
        initial = stream_initial_tasks(plan, roster)
        assert initial["robot_1"].start_delay_sec == 0.0
        assert initial["robot_4"].start_delay_sec == 12.0
        assert initial["robot_4"].goal == plan.tasks["robot_4"][0].goal
        assert initial["robot_4"].task == "pickup"
        assert initial["robot_4"].priority == 2

    def test_stream_start_record_carries_schedule(self):
        config = _stream()
        plan = build_task_stream_plan(config, ROBOTS)
        record = stream_start_record(plan, config)
        assert record["event"] == "stream_start"
        assert record["seed"] == 7
        assert record["sequences"]["robot_1"] == [t.node for t in plan.tasks["robot_1"]]
        assert record["tasks_total"] == 25
        assert record["forbidden_legs"] == [["Wp", "Wm"]]

    def test_start_position_offsets_measure_distance_to_start_node(self):
        pinned = dict(zip(ROBOTS, ["E", "S", "N", "Wm", "Wp"], strict=True))
        plan = build_task_stream_plan(_stream(start_nodes=pinned), ROBOTS)
        offsets = start_position_offsets(plan, S1_NODES, {"robot_1": (2.0, 0.0)})
        assert offsets["robot_1"] == pytest.approx(0.3)
        assert offsets["robot_2"] is None


class TestTracker:
    def test_start_issues_first_task_for_released_robots_only(self):
        tracker, _plan = _tracker()
        events = tracker.start(100.0, ["robot_1"])
        assert [(e.event, e.robot_id) for e in events] == [
            ("released", "robot_1"), ("issued", "robot_1"),
        ]
        assert tracker.phase("robot_1") == "traveling"
        assert tracker.phase("robot_2") == "held"

    def test_release_issues_first_task(self):
        tracker, plan = _tracker()
        tracker.start(100.0, ["robot_1"])
        events = tracker.on_release("robot_2", 104.0, 51.0)
        assert events[1].event == "issued"
        assert events[1].goal == plan.tasks["robot_2"][0].goal
        assert events[1].sim_t == 51.0

    def test_release_of_unheld_robot_is_ignored(self):
        tracker, _plan = _tracker()
        tracker.start(100.0, ["robot_1"])
        assert tracker.on_release("robot_1", 101.0, None) == []

    def test_arrival_at_current_node_starts_dwell(self):
        tracker, plan = _tracker()
        tracker.start(0.0, ROBOTS)
        event = tracker.on_arrival("robot_1", plan.tasks["robot_1"][0].goal, 10.0, 20.0)
        assert event.event == "arrived"
        assert tracker.phase("robot_1") == "dwelling"

    def test_arrival_at_other_goal_is_ignored(self):
        tracker, _plan = _tracker()
        tracker.start(0.0, ROBOTS)
        assert tracker.on_arrival("robot_1", (9.0, 9.0), 10.0, 20.0) is None
        assert tracker.phase("robot_1") == "traveling"

    def test_arrival_while_held_is_ignored(self):
        tracker, plan = _tracker()
        tracker.start(0.0, ["robot_1"])
        assert tracker.on_arrival("robot_2", plan.tasks["robot_2"][0].goal, 1.0, 1.0) is None

    def test_second_arrival_during_dwell_does_not_restart_dwell(self):
        tracker, plan = _tracker()
        tracker.start(0.0, ROBOTS)
        goal = plan.tasks["robot_1"][0].goal
        tracker.on_arrival("robot_1", goal, 10.0, 20.0)
        assert tracker.on_arrival("robot_1", goal, 12.0, 23.0) is None
        events = tracker.on_scene(25.0, 14.0)
        assert [e.event for e in events] == ["dwell_complete", "issued"]

    def test_dwell_not_complete_before_dwell_sim_sec(self):
        tracker, plan = _tracker(dwell=5.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_arrival("robot_1", plan.tasks["robot_1"][0].goal, 10.0, 20.0)
        assert tracker.on_scene(24.9, 30.0) == []
        assert tracker.current_task("robot_1").task_index == 0

    def test_dwell_complete_issues_next_task(self):
        tracker, plan = _tracker(dwell=5.0)
        tracker.start(0.0, ROBOTS)
        events = _arrive_and_dwell(tracker, plan, "robot_1", 20.0)
        assert [e.event for e in events] == ["dwell_complete", "issued"]
        assert events[1].task_index == 1
        assert events[1].goal == plan.tasks["robot_1"][1].goal
        assert events[1].label == "delivery"
        assert tracker.completed_count("robot_1") == 1

    def test_dwell_measured_on_sim_clock_not_wall(self):
        tracker, plan = _tracker(dwell=5.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_arrival("robot_1", plan.tasks["robot_1"][0].goal, 10.0, 20.0)
        # 100 wall-s later but only 2 sim-s: still dwelling.
        assert tracker.on_scene(22.0, 110.0) == []

    def test_dwell_from_unknown_sim_time_starts_on_next_scene(self):
        tracker, plan = _tracker(dwell=5.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_arrival("robot_1", plan.tasks["robot_1"][0].goal, 10.0, None)
        assert tracker.on_scene(40.0, 11.0) == []
        assert [e.event for e in tracker.on_scene(45.0, 12.0)] == ["dwell_complete", "issued"]

    def test_backwards_stamp_never_completes_dwell(self):
        tracker, plan = _tracker(dwell=5.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_scene(30.0, 1.0)
        tracker.on_arrival("robot_1", plan.tasks["robot_1"][0].goal, 2.0, 30.0)
        assert tracker.on_scene(10.0, 3.0) == []
        assert tracker.phase("robot_1") == "dwelling"

    def test_last_dwell_marks_robot_done(self):
        tracker, plan = _tracker(dwell=1.0)
        tracker.start(0.0, ROBOTS)
        t = 10.0
        for _ in range(4):
            _arrive_and_dwell(tracker, plan, "robot_1", t, dwell=1.0)
            t += 10.0
        events = _arrive_and_dwell(tracker, plan, "robot_1", t, dwell=1.0)
        assert [e.event for e in events] == ["dwell_complete", "robot_done"]
        assert tracker.phase("robot_1") == "done"
        assert tracker.on_arrival("robot_1", plan.tasks["robot_1"][4].goal, 99.0, 99.0) is None


class TestManifest:
    def _complete_all(self, tracker, plan, start_sim: float = 100.0) -> float:
        tracker.on_scene(start_sim, 0.0)
        t = start_sim
        for robot_id in ROBOTS:
            for _ in range(5):
                t += 10.0
                _arrive_and_dwell(tracker, plan, robot_id, t, dwell=1.0)
        return t + 1.0

    def test_manifest_counts_completed_tasks(self):
        tracker, plan = _tracker(dwell=1.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_scene(100.0, 0.0)
        _arrive_and_dwell(tracker, plan, "robot_2", 110.0, dwell=1.0)
        _arrive_and_dwell(tracker, plan, "robot_2", 120.0, dwell=1.0)
        manifest = tracker.manifest()
        assert manifest["tasks_completed"] == 2
        assert manifest["tasks_total"] == 25
        assert manifest["per_robot_completed"]["robot_2"] == 2
        assert manifest["per_robot_completed"]["robot_1"] == 0

    def test_manifest_makespan_null_until_all_queues_empty(self):
        tracker, plan = _tracker(dwell=1.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_scene(100.0, 0.0)
        _arrive_and_dwell(tracker, plan, "robot_1", 110.0, dwell=1.0)
        manifest = tracker.manifest()
        assert manifest["complete"] is False
        assert manifest["makespan_sim_sec"] is None
        assert manifest["makespan_wall_sec"] is None

    def test_manifest_makespan_is_last_dwell_minus_first_scene(self):
        tracker, plan = _tracker(dwell=1.0)
        tracker.start(0.0, ROBOTS)
        last = self._complete_all(tracker, plan, start_sim=100.0)
        manifest = tracker.manifest()
        assert manifest["complete"] is True
        assert manifest["tasks_completed"] == 25
        assert manifest["makespan_sim_sec"] == pytest.approx(last - 100.0)
        assert manifest["episode_start_sim"] == 100.0

    def test_manifest_counts_tasks_within_horizon(self):
        tracker, plan = _tracker(dwell=1.0, horizon=25.0)
        tracker.start(0.0, ROBOTS)
        tracker.on_scene(100.0, 0.0)
        _arrive_and_dwell(tracker, plan, "robot_1", 110.0, dwell=1.0)  # done at 111
        _arrive_and_dwell(tracker, plan, "robot_1", 130.0, dwell=1.0)  # done at 131
        manifest = tracker.manifest()
        assert manifest["tasks_completed_within_horizon"] == 1
        assert manifest["horizon_sim_sec"] == 25.0

    def test_manifest_records_per_task_timestamps(self):
        tracker, plan = _tracker(dwell=1.0)
        tracker.start(5.0, ROBOTS)
        tracker.on_scene(100.0, 6.0)
        goal = plan.tasks["robot_1"][0].goal
        tracker.on_arrival("robot_1", goal, 7.0, 104.0)
        tracker.on_scene(105.0, 8.0)
        first = tracker.manifest()["tasks"]["robot_1"][0]
        assert first["issued_wall"] == 5.0
        assert first["issued_sim"] is None
        assert first["arrived_sim"] == 104.0
        assert first["dwell_complete_sim"] == 105.0
        assert tracker.manifest()["tasks"]["robot_1"][1]["issued_sim"] == 105.0


class TestRegistry:
    def test_set_base_keeps_active_override(self):
        registry = TaskRegistry()
        registry.load_assignments({"robot_1": TaskAssignment(task="pickup", goal=(1.0, 0.0))})
        registry.set_override("robot_1", "yield", (1.0, 0.0), "cmd-1")
        registry.set_base("robot_1", "delivery", (0.0, 1.55))
        assert registry.effective("robot_1") == ("yield", (1.0, 0.0))
        registry.clear_override("robot_1")
        assert registry.effective("robot_1") == ("delivery", (0.0, 1.55))

    def test_set_base_changes_mission_task(self):
        registry = TaskRegistry()
        registry.load_assignments({"robot_1": TaskAssignment(task="pickup", goal=(1.0, 0.0))})
        registry.set_base("robot_1", "delivery", (0.0, 1.55))
        assert registry.mission_task("robot_1") == "delivery"

    def test_set_base_unknown_robot_is_noop(self):
        registry = TaskRegistry()
        registry.set_base("robot_9", "pickup", (0.0, 0.0))
        assert registry.effective("robot_9") is None

    def test_load_initial_equals_load_assignments_of_initial_tasks(self):
        config = _orchestrator(
            TaskStreamConfig(),
            initial_tasks={
                "robot_1": TaskAssignment(task="t", goal=(1.0, 0.0)),
                "robot_2": TaskAssignment(task="t", goal=(2.0, 0.0), start_delay_sec=5.0),
            },
        )
        a, b = TaskRegistry(), TaskRegistry()
        a.load_initial(config, 10.0)
        b.load_assignments(config.initial_tasks, 10.0)
        assert a.to_json() == b.to_json()
        assert a.release_at == b.release_at == {"robot_2": 15.0}


class TestConfig:
    def test_default_stream_is_disabled(self):
        config = _orchestrator(TaskStreamConfig())
        assert config.task_stream.enabled is False
        assert config.dispatch_enabled is True

    def test_enabled_stream_requires_seed(self):
        with pytest.raises(ValidationError, match="seed"):
            _stream(seed=None)

    def test_enabled_stream_requires_two_nodes(self):
        with pytest.raises(ValidationError, match="two nodes"):
            _stream(nodes={"A": (0.0, 0.0)})

    def test_forbidden_leg_must_name_known_nodes(self):
        with pytest.raises(ValidationError, match="forbidden_legs"):
            _stream(forbidden_legs=(("Wp", "X"),))

    def test_node_without_successor_rejected(self):
        with pytest.raises(ValidationError, match="no legal next node"):
            _stream(nodes={"A": (0.0, 0.0), "B": (1.0, 0.0)}, forbidden_legs=(("A", "B"),))

    def test_start_nodes_must_be_distinct(self):
        with pytest.raises(ValidationError, match="own node"):
            _stream(start_nodes={"robot_1": "N", "robot_2": "N"})

    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            TaskStreamConfig(enabled=False, dwell_sec=5.0)

    def test_disabled_stream_skips_validation(self):
        assert TaskStreamConfig(enabled=False, nodes={}).seed is None

    def test_start_nodes_must_cover_roster(self):
        with pytest.raises(ValidationError, match="must equal"):
            _orchestrator(_stream(start_nodes={"robot_1": "N"}))

    def test_stream_rejects_initial_start_delay(self):
        tasks = {rid: TaskAssignment(task="t", goal=(0.0, 0.0)) for rid in ROBOTS}
        tasks["robot_2"] = TaskAssignment(task="t", goal=(0.0, 0.0), start_delay_sec=3.0)
        with pytest.raises(ValidationError, match="start_delay_sec"):
            _orchestrator(_stream(), initial_tasks=tasks)

    def test_stream_requires_arrival_position_check(self):
        with pytest.raises(ValidationError, match="arrival_position_check"):
            _orchestrator(_stream(), arrival_position_check=False)

    def test_stream_needs_a_node_per_robot_when_drawing_starts(self):
        nodes = {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0)}
        with pytest.raises(ValidationError, match="distinct start node"):
            _orchestrator(_stream(nodes=nodes, forbidden_legs=()))

    def test_load_config_parses_yaml_shaped_stream(self):
        raw = {
            "stall_threshold_sec": 12.0,
            "progress_epsilon_m": 0.1,
            "cooldown_sec": 15.0,
            "command_timeout_sec": 20.0,
            "reasoning_backend_id": "mock",
            "frame_dump_dir": "/tmp/f",
            "initial_tasks": {rid: {"task": "t", "goal": [0.0, 0.0]} for rid in ROBOTS},
            "task_stream": {
                "enabled": True,
                "seed": 3,
                "nodes": {k: list(v) for k, v in S1_NODES.items()},
                "forbidden_legs": [["Wp", "Wm"]],
            },
            "dispatch_enabled": False,
        }
        config = load_config(raw)
        assert config.task_stream.nodes["N"] == (0.0, 1.55)
        assert config.task_stream.forbidden_legs == (("Wp", "Wm"),)
        assert config.dispatch_enabled is False
