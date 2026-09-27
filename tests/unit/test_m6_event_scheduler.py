import pytest

from isaac.vgu_sim.config import Pose2D, TimedObstacleConfig
from isaac.vgu_sim.event_scheduler import EventScheduler, timed_obstacle_prim_path
from isaac.vgu_sim.runner import build_obstacle_scheduler


def _make_obs(obs_id: str, spawn: float, remove: float | None) -> TimedObstacleConfig:
    return TimedObstacleConfig(
        obstacle_id=obs_id,
        asset="dynamic_obstacle.usd",
        spawn_at_sec=spawn,
        remove_at_sec=remove,
        pose=Pose2D(x=1.5, y=0.0, yaw_rad=0.0),
    )


def test_no_events_before_spawn():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    applied = sched.apply_due_events(5.0)
    assert applied == ()
    assert not sched.is_active("obs1")


def test_obstacle_activates_at_spawn_time():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    applied = sched.apply_due_events(8.0)
    assert "obs1" in applied
    assert sched.is_active("obs1")


def test_obstacle_deactivates_at_remove_time():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    applied = sched.apply_due_events(20.0)
    assert "obs1" in applied
    assert not sched.is_active("obs1")


def test_event_applied_only_once():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    applied_again = sched.apply_due_events(9.0)
    assert "obs1" not in applied_again


def test_events_sorted_by_time():
    obs_a = _make_obs("obs_a", 15.0, None)
    obs_b = _make_obs("obs_b", 5.0, None)
    sched = EventScheduler([obs_a, obs_b])
    applied = sched.apply_due_events(10.0)
    assert "obs_b" in applied
    assert "obs_a" not in applied


def test_reset_restores_inactive_state():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    assert sched.is_active("obs1")
    sched.reset()
    assert not sched.is_active("obs1")


def test_reset_allows_events_to_fire_again():
    sched = EventScheduler([_make_obs("obs1", 8.0, 20.0)])
    sched.apply_due_events(8.0)
    sched.reset()
    applied = sched.apply_due_events(8.0)
    assert "obs1" in applied
    assert sched.is_active("obs1")


def test_permanent_obstacle_never_deactivates():
    sched = EventScheduler([_make_obs("obs_perm", 5.0, None)])
    sched.apply_due_events(5.0)
    applied = sched.apply_due_events(100.0)
    assert "obs_perm" not in applied
    assert sched.is_active("obs_perm")


class _FakePrim:
    def __init__(self, active: bool = False) -> None:
        self.active = active
        self.calls: list[bool] = []

    def IsValid(self) -> bool:  # noqa: N802 - mirrors Usd.Prim
        return True

    def SetActive(self, active: bool) -> None:  # noqa: N802 - mirrors Usd.Prim
        self.active = active
        self.calls.append(active)


class _InvalidPrim:
    def IsValid(self) -> bool:  # noqa: N802 - mirrors Usd.Prim
        return False


class _FakeStage:
    def __init__(self, prims: dict[str, object]) -> None:
        self.prims = prims

    def GetPrimAtPath(self, path: str) -> object:  # noqa: N802 - mirrors Usd.Stage
        return self.prims.get(path, _InvalidPrim())


def _stage_with(*obstacle_ids: str) -> tuple[_FakeStage, dict[str, _FakePrim]]:
    prims = {oid: _FakePrim() for oid in obstacle_ids}
    stage = _FakeStage({timed_obstacle_prim_path(oid): prim for oid, prim in prims.items()})
    return stage, prims


def test_timed_obstacle_prim_path_matches_builder_namespace():
    assert timed_obstacle_prim_path("obs1") == "/World/DynamicObstacles/obs1"


def test_runner_scheduler_leaves_prim_inactive_before_spawn():
    stage, prims = _stage_with("obs1")
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, 20.0)], lambda: stage)
    sched.apply_due_events(7.9)
    assert prims["obs1"].calls == []


def test_runner_scheduler_activates_prim_at_spawn_time():
    stage, prims = _stage_with("obs1")
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, 20.0)], lambda: stage)
    sched.apply_due_events(8.0)
    assert prims["obs1"].calls == [True]


def test_runner_scheduler_deactivates_prim_at_remove_time():
    stage, prims = _stage_with("obs1")
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, 20.0)], lambda: stage)
    for t in (7.9, 8.0, 13.4, 19.9, 20.0, 25.0):
        sched.apply_due_events(t)
    assert prims["obs1"].calls == [True, False]
    assert prims["obs1"].active is False


def test_runner_scheduler_toggles_only_the_due_obstacle():
    stage, prims = _stage_with("early", "late")
    sched = build_obstacle_scheduler(
        [_make_obs("early", 5.0, None), _make_obs("late", 15.0, None)], lambda: stage
    )
    sched.apply_due_events(10.0)
    assert (prims["early"].calls, prims["late"].calls) == ([True], [])


def test_runner_scheduler_reset_deactivates_spawned_prim():
    stage, prims = _stage_with("obs1")
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, 20.0)], lambda: stage)
    sched.apply_due_events(10.0)
    sched.reset()
    assert prims["obs1"].calls == [True, False]


def test_runner_scheduler_resolves_stage_at_event_time():
    # SimulationContext.reset() reloads the stage after the scheduler exists.
    stale, stale_prims = _stage_with("obs1")
    live, live_prims = _stage_with("obs1")
    current = {"stage": stale}
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, None)], lambda: current["stage"])
    current["stage"] = live
    sched.apply_due_events(8.0)
    assert (stale_prims["obs1"].calls, live_prims["obs1"].calls) == ([], [True])


def test_runner_scheduler_raises_when_obstacle_prim_missing():
    stage, _prims = _stage_with()
    sched = build_obstacle_scheduler([_make_obs("obs1", 8.0, None)], lambda: stage)
    with pytest.raises(RuntimeError, match="/World/DynamicObstacles/obs1"):
        sched.apply_due_events(8.0)
