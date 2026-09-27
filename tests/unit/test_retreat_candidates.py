import math

import pytest

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_candidates import (
    RetreatCandidate,
    generate_retreat_candidates,
    rank_candidates,
)
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def _frame(*robots: tuple[str, float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta) for rid, x, y, theta in robots
        ],
    )


def _geometry(aisle_half_width_m: float = 0.6) -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x",
            center_m=0.0,
            half_length_m=1.0,
            aisle_half_width_m=aisle_half_width_m,
            occluder_height_m=0.9,
        )
    )


_HEAD_ON = _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 0.4, 0.0, math.pi))
_DEADLOCK = _frame(("robot_1", -0.3, 0.0, 0.0), ("robot_2", 0.3, 0.0, math.pi))


class TestGenerateRetreatCandidates:
    def test_open_floor_yields_four_labeled_candidates(self):
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, GroundingParams())
        assert [c.label for c in candidates] == ["A", "B", "C", "D"]
        assert [round(c.lateral_m, 2) for c in candidates] == [0.35, -0.35, 0.7, -0.7]
        # yielder faces east, so retreat is west and "left" is +y
        assert candidates[0].x == pytest.approx(-1.3)
        assert candidates[0].y == pytest.approx(0.35)

    def test_aisle_band_discards_far_candidates(self):
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        assert [round(c.lateral_m, 2) for c in candidates] == [0.35, -0.35]
        assert [c.label for c in candidates] == ["A", "B"]

    def test_robot_at_far_left_end_discards_left_candidates(self):
        # robot_3 sits exactly where the far-left sidestep ends. The plan's
        # (-1.3, 0.35) placement was 0.35 m from the shared backup endpoint,
        # which vetoed all four candidates, not just the left ones.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 0.7, 0.0),
        )
        candidates = generate_retreat_candidates(frame, "robot_1", 1.3, GroundingParams())
        assert [round(c.lateral_m, 2) for c in candidates] == [-0.35, -0.7]
        assert [c.label for c in candidates] == ["A", "B"]

    def test_robot_on_shared_backup_path_discards_every_candidate(self):
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 0.35, 0.0),
        )
        assert generate_retreat_candidates(frame, "robot_1", 1.3, GroundingParams()) == []

    def test_preexisting_standoff_separation_does_not_veto_retreat(self):
        # robot_2 is 0.4 m away (< min_distance 0.45) before the maneuver even
        # starts; retreating away from it must still validate.
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, GroundingParams())
        assert candidates, "deadlock standoff must not veto its own resolution"

    def test_sweep_that_closes_on_a_robot_is_discarded(self):
        # A robot 1.0 m behind the yielder: backing 1.3 m sweeps straight
        # through it, even though both endpoints clear it.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.0, 0.0, 0.0),
        )
        assert generate_retreat_candidates(frame, "robot_1", 1.3, GroundingParams()) == []

    def test_unknown_yielder_returns_empty(self):
        assert generate_retreat_candidates(_HEAD_ON, "robot_9", 1.3, GroundingParams()) == []

    def test_lone_yielder_reports_no_clearance_rather_than_infinity(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        candidates = generate_retreat_candidates(frame, "robot_1", 1.3, GroundingParams())
        assert candidates
        assert all(c.min_sweep_clearance_m is None for c in candidates)
        assert all(c.lateral_clearance_m is None for c in candidates)

    def test_candidate_serializes_to_json(self):
        candidate = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, GroundingParams())[0]
        dumped = candidate.model_dump(mode="json")
        assert dumped["label"] == "A"
        assert dumped["lateral_clearance_m"] == pytest.approx(1.7)


class TestGenerateWithGeometry:
    def test_declared_aisle_yields_two_candidates(self):
        # The declared 0.6 m aisle half-width bounds the sidestep at
        # pull_off_lateral_m = 0.36, so the far (0.72 m) variants hit the band:
        # the head-on family offers k = 2, not T3b's k = 3.
        candidates = generate_retreat_candidates(
            _DEADLOCK,
            "robot_1",
            1.489,
            GroundingParams(),
            geometry=_geometry(),
            passer_id="robot_2",
        )
        assert [(c.label, c.lateral_m) for c in candidates] == [("A", 0.36), ("B", -0.36)]
        assert candidates[0].x == pytest.approx(-1.789)
        assert candidates[0].y == pytest.approx(0.36)

    def test_explicit_band_can_offer_three_candidates(self):
        params = GroundingParams(aisle_y_band_m=(-0.4, 0.8))
        candidates = generate_retreat_candidates(
            _DEADLOCK, "robot_1", 1.489, params, geometry=_geometry(), passer_id="robot_2"
        )
        assert [c.lateral_m for c in candidates] == [0.36, -0.36, 0.72]
        assert [c.label for c in candidates] == ["A", "B", "C"]

    def test_aisle_too_narrow_to_step_aside_yields_nothing(self):
        candidates = generate_retreat_candidates(
            _DEADLOCK,
            "robot_1",
            1.489,
            GroundingParams(),
            geometry=_geometry(aisle_half_width_m=0.2),
            passer_id="robot_2",
        )
        assert candidates == []

    def test_geometry_needs_the_passer(self):
        with pytest.raises(ValueError, match="passer_id"):
            generate_retreat_candidates(
                _DEADLOCK, "robot_1", 1.489, GroundingParams(), geometry=_geometry()
            )


class TestRankCandidates:
    def test_side_away_from_third_robot_ranks_first(self):
        # robot_3 north of the parked zone: right-side (negative lateral)
        # candidates have larger sidestep clearance and must rank first.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 1.0, 0.0),
        )
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(frame, "robot_1", 1.3, params)
        ranked = rank_candidates(candidates, 0.0, (0.0, 0.0))
        assert ranked[0].lateral_m == pytest.approx(-0.35)

    def test_symmetric_scene_breaks_tie_by_label(self):
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        ranked = rank_candidates(candidates, 0.0, (0.0, 0.0))
        assert [c.label for c in ranked] == ["A", "B"]

    def test_equal_clearance_prefers_farther_from_corridor(self):
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, GroundingParams())
        ranked = rank_candidates(candidates, 0.0, (0.0, 0.0))
        assert [c.label for c in ranked] == ["C", "D", "A", "B"]

    def test_ranking_is_deterministic(self):
        params = GroundingParams()
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        first = rank_candidates(candidates, 0.0, (0.0, 0.0))
        second = rank_candidates(list(reversed(candidates)), 0.0, (0.0, 0.0))
        assert [c.label for c in first] == [c.label for c in second]

    def test_unmeasured_clearance_ranks_as_unbounded(self):
        def candidate(label: str, clearance: float | None) -> RetreatCandidate:
            return RetreatCandidate(
                label=label,
                x=-1.3,
                y=0.35,
                backup_m=1.3,
                lateral_m=0.35,
                min_sweep_clearance_m=clearance,
                lateral_clearance_m=clearance,
            )

        ranked = rank_candidates([candidate("A", 0.5), candidate("B", None)], 0.0, (0.0, 0.0))
        assert [c.label for c in ranked] == ["B", "A"]
