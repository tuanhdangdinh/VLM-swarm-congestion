"""Deterministic, balanced, scene-capped item sampling."""
from dataclasses import dataclass

from reasoning.vlm.capability_probes.selection import balanced_sample


@dataclass(frozen=True)
class _Candidate:
    scene: str
    answer: str
    tag: int


def _pool() -> list[_Candidate]:
    # 3 scenes x 2 answer values x several candidates each, so both the
    # balance and the per-scene cap have room to matter.
    pool = []
    tag = 0
    for scene in ("scene_a", "scene_b", "scene_c"):
        for answer in ("left", "right"):
            for _ in range(5):
                pool.append(_Candidate(scene=scene, answer=answer, tag=tag))
                tag += 1
    return pool


class TestDeterminism:
    def test_same_seed_same_candidates_gives_the_same_selection(self):
        pool = _pool()
        first = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=10, seed=7, max_per_scene=4
        )
        second = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=10, seed=7, max_per_scene=4
        )
        assert [c.tag for c in first] == [c.tag for c in second]

    def test_different_seeds_can_give_different_selections(self):
        pool = _pool()
        tags_by_seed = {
            seed: tuple(
                c.tag
                for c in balanced_sample(
                    pool, lambda c: c.answer, lambda c: c.scene,
                    target=6, seed=seed, max_per_scene=3,
                )
            )
            for seed in range(5)
        }
        assert len(set(tags_by_seed.values())) > 1


class TestBalance:
    def test_draws_roughly_evenly_across_balance_groups(self):
        pool = _pool()
        selected = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=10, seed=1, max_per_scene=10
        )
        counts = {"left": 0, "right": 0}
        for c in selected:
            counts[c.answer] += 1
        assert counts["left"] == counts["right"] == 5


class TestSceneCap:
    def test_never_exceeds_max_per_scene(self):
        pool = _pool()
        selected = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=30, seed=3, max_per_scene=2
        )
        counts: dict[str, int] = {}
        for c in selected:
            counts[c.scene] = counts.get(c.scene, 0) + 1
        assert all(count <= 2 for count in counts.values())

    def test_spans_every_available_scene_when_capped(self):
        pool = _pool()
        selected = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=30, seed=3, max_per_scene=2
        )
        assert {c.scene for c in selected} == {"scene_a", "scene_b", "scene_c"}


class TestShortfall:
    def test_returns_fewer_than_target_when_pool_is_exhausted(self):
        pool = _pool()[:4]
        selected = balanced_sample(
            pool, lambda c: c.answer, lambda c: c.scene, target=100, seed=1, max_per_scene=100
        )
        assert len(selected) == 4

    def test_empty_pool_yields_empty_selection(self):
        selected = balanced_sample(
            [], lambda c: c.answer, lambda c: c.scene, target=5, seed=1, max_per_scene=5
        )
        assert selected == []
