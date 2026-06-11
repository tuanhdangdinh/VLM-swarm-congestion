from isaac.vgu_sim.config import Pose2D, TimedObstacleConfig
from isaac.vgu_sim.event_scheduler import EventScheduler


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
