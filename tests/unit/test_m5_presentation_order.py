"""Unit tests for the M5 per-episode robot presentation-order policy."""
from __future__ import annotations

import pytest
from swarm_orchestrator.presentation_order import (
    EpisodeOrderTracker,
    PresentationOrderPolicy,
    derive_order_seed,
)


def _random_policy(seed: int = 0) -> PresentationOrderPolicy:
    return PresentationOrderPolicy(mode="random", seed=seed)


def test_order_for_episode_returns_mode_when_ascending_fixed():
    policy = PresentationOrderPolicy(mode="id_asc", seed=12345)

    assert [policy.order_for_episode(k) for k in range(5)] == ["id_asc"] * 5


def test_order_for_episode_returns_mode_when_descending_fixed():
    policy = PresentationOrderPolicy(mode="id_desc", seed=12345)

    assert [policy.order_for_episode(k) for k in range(5)] == ["id_desc"] * 5


def test_order_for_episode_ignores_seed_when_mode_is_fixed():
    assert PresentationOrderPolicy(mode="id_asc", seed=1).order_for_episode(
        3
    ) == PresentationOrderPolicy(mode="id_asc", seed=2).order_for_episode(3)


def test_order_for_episode_is_deterministic_when_seed_and_index_repeat():
    first = [_random_policy(7).order_for_episode(k) for k in range(10)]
    second = [_random_policy(7).order_for_episode(k) for k in range(10)]

    assert first == second


def test_order_for_episode_draws_both_orders_when_random_over_ten_episodes():
    drawn = {_random_policy(0).order_for_episode(k) for k in range(10)}

    assert drawn == {"id_asc", "id_desc"}


def test_order_for_episode_differs_between_seeds_when_random():
    assert [_random_policy(0).order_for_episode(k) for k in range(10)] != [
        _random_policy(1).order_for_episode(k) for k in range(10)
    ]


def test_order_for_episode_rejects_negative_episode_index():
    with pytest.raises(ValueError, match="episode_index"):
        _random_policy().order_for_episode(-1)


def test_derive_order_seed_is_stable_for_one_run_id():
    assert derive_order_seed("20260925_0101", "session_a") == derive_order_seed(
        "20260925_0101", "session_b"
    )


def test_derive_order_seed_falls_back_to_session_id_when_run_id_absent():
    assert derive_order_seed(None, "session_a") != derive_order_seed(None, "session_b")
    assert derive_order_seed(None, "session_a") == derive_order_seed("session_a", "other")


def test_order_for_is_constant_within_one_episode():
    tracker = EpisodeOrderTracker(_random_policy())
    first = tracker.order_for(["robot_1", "robot_2"])
    again = tracker.order_for(["robot_1", "robot_2"])

    assert first == again


def test_order_for_keeps_episode_when_robot_sets_overlap():
    tracker = EpisodeOrderTracker(_random_policy())
    index, order = tracker.order_for(["robot_1", "robot_2"])

    assert tracker.order_for(["robot_2", "robot_3"]) == (index, order)


def test_order_for_opens_next_episode_when_robot_sets_are_disjoint():
    tracker = EpisodeOrderTracker(_random_policy())
    first_index, _ = tracker.order_for(["robot_1", "robot_2"])
    second_index, _ = tracker.order_for(["robot_8", "robot_9"])

    assert (first_index, second_index) == (0, 1)


def test_order_for_opens_next_episode_after_an_arrival_ends_the_current_one():
    tracker = EpisodeOrderTracker(_random_policy())
    tracker.order_for(["robot_1", "robot_2"])
    tracker.end_episode(["robot_2"])

    assert tracker.order_for(["robot_1", "robot_2"])[0] == 1


def test_order_for_varies_across_episodes_when_random():
    tracker = EpisodeOrderTracker(_random_policy(0))
    orders = []
    for _ in range(10):
        orders.append(tracker.order_for(["robot_1", "robot_2"])[1])
        tracker.end_episode(["robot_1"])

    assert set(orders) == {"id_asc", "id_desc"}


def test_order_for_stays_fixed_across_episodes_when_mode_is_fixed():
    tracker = EpisodeOrderTracker(PresentationOrderPolicy(mode="id_desc", seed=0))
    orders = []
    for _ in range(10):
        orders.append(tracker.order_for(["robot_1", "robot_2"])[1])
        tracker.end_episode(["robot_1"])

    assert orders == ["id_desc"] * 10


def test_order_for_follows_the_policy_sequence_by_episode_index():
    policy = _random_policy(0)
    tracker = EpisodeOrderTracker(policy)
    orders = []
    for _ in range(5):
        orders.append(tracker.order_for(["robot_1"])[1])
        tracker.end_episode(["robot_1"])

    assert orders == [policy.order_for_episode(k) for k in range(5)]


def test_end_episode_reports_false_when_no_episode_tracks_the_robots():
    tracker = EpisodeOrderTracker(_random_policy())
    assert tracker.end_episode(["robot_1"]) is False

    tracker.order_for(["robot_1"])
    assert tracker.end_episode(["robot_9"]) is False
    assert tracker.end_episode(["robot_1"]) is True


def test_episode_index_starts_before_the_first_episode():
    assert EpisodeOrderTracker(_random_policy()).episode_index == -1
