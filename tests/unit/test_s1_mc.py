"""Pins for the S1 kinematic Monte Carlo (scripts/s1_mc.py).

The MC is the S1a hotspot machinery rebuilt and committed; these tests pin
that it still reproduces the S1a published row in shape (scene design S1,
row D: every episode has an encounter, the junction dominates first
conflicts, free-flow makespan median ~177 sim-s) on a small draw, that its
costmap model matches the live Nav2 dump's classes, and that the S1b floor
keeps the Delta artifact at zero under its recomputed stagger.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import s1_mc as M  # noqa: E402
import s1b_layout as L  # noqa: E402


@pytest.fixture(scope="module")
def s1a():
    floor = M.s1a_floor()
    return floor, M.build_routes(floor, "nominal")


def test_nominal_routes_have_the_scene_doc_leg_lengths(s1a):
    _, routes = s1a
    assert M.polyline_len(routes[("N", "S")]) == pytest.approx(3.10)
    assert M.polyline_len(routes[("N", "E")]) == pytest.approx(3.85)
    assert M.polyline_len(routes[("Wp", "N")]) == pytest.approx(3.945, abs=1e-3)
    assert M.polyline_len(routes[("Wm", "E")]) == pytest.approx(4.695, abs=1e-3)


def test_costmap_classes_follow_the_live_dump(s1a):
    floor, _ = s1a
    # bottleneck_merge rack face at y = 0.6: centre distances 0.05 / 0.10 /
    # 0.15 m read INSCRIBED / inflated / free in the live dump.
    # Cell centres at y = 0.575 / 0.525 / 0.475 (first rack cell centre 0.625).
    for y, cost in [(0.575, M.COST_INSCRIBED), (0.525, M.COST_INFLATED), (0.475, 0)]:
        r, c = floor.cell(-1.5, y)
        assert floor.cost[r, c] == cost, y


def test_s1a_reproduction_shape_on_sixty_draws(s1a):
    floor, routes = s1a
    eps = [
        M.run_episode(floor, routes, s, delta=4.0, finished="wander", freeze=True)
        for s in range(1, 61)
    ]
    summary = M.summarise(eps)
    assert summary["with_encounter"] == 60
    assert summary["first_region"]["junction"] / 60 > 0.6
    assert 10.0 <= summary["first_t_median"] <= 17.0
    assert summary["first_delta_artifact"] == 0
    free = [
        M.run_episode(floor, routes, s, delta=4.0, finished="wander", freeze=False)
        for s in range(1, 61)
    ]
    assert 170.0 <= M.flow_summary(free)["makespan_median"] <= 185.0


def test_s1b_has_no_delta_artifact_at_its_stagger():
    floor = L.s1b_floor()
    routes = M.build_routes(floor, "grid")
    eps = [
        M.run_episode(floor, routes, s, delta=3.0, finished="park", freeze=True)
        for s in range(1, 41)
    ]
    assert M.summarise(eps)["first_delta_artifact"] == 0
