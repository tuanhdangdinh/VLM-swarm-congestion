import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import (
    Derivation,
    GroundingParams,
    derive_backup_distance,
    derive_escort_distance,
    load_grounding_params,
    maneuver_limits,
    project_progress,
    retreat_axes,
)
from reasoning.rag.scene_geometry import (
    CorridorGeometry,
    SceneGeometry,
    passer_clearance_m,
    pull_off_lateral_m,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)


def _frame(*robots: tuple[str, float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta) for rid, x, y, theta in robots
        ],
    )


def _geometry(axis: str = "x", aisle_half_width_m: float = 0.6) -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis=axis,
            center_m=0.0,
            half_length_m=1.0,
            aisle_half_width_m=aisle_half_width_m,
            occluder_height_m=0.9,
        )
    )


def _head_on(yielder_x: float, passer_x: float) -> SnapshotFrame:
    theta_1 = 0.0 if yielder_x < passer_x else math.pi
    return _frame(
        ("robot_1", yielder_x, 0.0, theta_1),
        ("robot_2", passer_x, 0.0, theta_1 + math.pi),
    )


class TestGroundingParams:
    def test_defaults_are_legacy_mode(self):
        assert GroundingParams().mode == "legacy"

    def test_unknown_key_rejected(self):
        with pytest.raises(ValidationError):
            GroundingParams(backup_clearence_m=1.7)

    def test_inverted_band_rejected(self):
        with pytest.raises(ValidationError):
            GroundingParams(backup_band_m=(2.0, 0.5))

    def test_sweep_step_capped_at_spec_interval(self):
        # Appendix A.3: swept segments are sampled at <= 0.1 m intervals.
        with pytest.raises(ValidationError):
            GroundingParams(sweep_step_m=0.2)


class TestProjectProgress:
    def test_progress_along_x_axis(self):
        assert project_progress((0.0, 0.0), (2.5, 1.0), 0.0) == pytest.approx(2.5)

    def test_progress_along_y_axis(self):
        assert project_progress((0.0, 0.0), (1.0, 3.0), math.pi / 2) == pytest.approx(3.0)

    def test_backward_motion_is_negative(self):
        assert project_progress((0.0, 0.0), (-1.0, 0.0), 0.0) == pytest.approx(-1.0)


class TestManeuverLimits:
    def test_without_geometry_uses_params(self):
        limits = maneuver_limits(GroundingParams(), None)
        assert (limits.min_distance_m, limits.lateral_m, limits.escort_clearance_m) == (
            0.45,
            0.35,
            0.5,
        )

    def test_with_geometry_reuses_scene_geometry_derivations(self):
        geometry = _geometry()
        limits = maneuver_limits(GroundingParams(), geometry)
        assert limits.lateral_m == round(pull_off_lateral_m(geometry), 3) == 0.36
        assert limits.escort_clearance_m == passer_clearance_m(geometry) == pytest.approx(0.65)
        assert limits.min_distance_m == geometry.robot.safety_radius_m

    def test_narrow_aisle_leaves_no_lateral_room(self):
        limits = maneuver_limits(GroundingParams(), _geometry(aisle_half_width_m=0.2))
        assert limits.lateral_m == 0.0


class TestRetreatAxes:
    def test_heading_frame_without_geometry(self):
        axes = retreat_axes(_head_on(0.0, 0.4), "robot_1", "robot_2", None)
        assert axes.retreat == pytest.approx((-1.0, 0.0))
        assert axes.left == pytest.approx((0.0, 1.0))

    def test_geometry_frame_retreats_away_from_passer_along_corridor(self):
        # robot_1 is east of the passer and (misleadingly) faces east: the
        # declared corridor, not the heading, fixes the retreat direction.
        frame = _frame(("robot_1", 0.3, 0.0, 0.0), ("robot_2", -0.3, 0.0, 0.0))
        axes = retreat_axes(frame, "robot_1", "robot_2", _geometry())
        assert axes.retreat == pytest.approx((1.0, 0.0))
        # Robot-frame left of a yielder facing the passer (west) is -y.
        assert axes.left == pytest.approx((0.0, -1.0))

    def test_geometry_frame_on_y_axis(self):
        frame = _frame(("robot_1", 0.0, -0.3, math.pi / 2), ("robot_2", 0.0, 0.3, -math.pi / 2))
        axes = retreat_axes(frame, "robot_1", "robot_2", _geometry(axis="y"))
        assert axes.retreat == pytest.approx((0.0, -1.0))
        assert axes.left == pytest.approx((-1.0, 0.0))

    def test_missing_yielder_returns_none(self):
        assert retreat_axes(_head_on(0.0, 0.4), "robot_9", "robot_2", None) is None

    def test_geometry_frame_needs_a_passer(self):
        assert retreat_axes(_head_on(0.0, 0.4), "robot_1", None, _geometry()) is None


class TestDeriveBackupDistance:
    def test_reproduces_verified_head_on_tuning(self):
        # robot_1 faces east at origin, robot_2 stands 0.4 m ahead:
        # required d = backup_clearance 1.7 - 0.4 = 1.3 (the verified constant).
        frame = _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 0.4, 0.0, math.pi))
        result = derive_backup_distance(frame, "robot_1", ["robot_2"], GroundingParams())
        assert result.feasible
        # Exact, not approximate: the plan's accumulated 0.01 m scan landed on
        # 1.31 here through float drift.
        assert result.value_m == 1.3

    def test_robot_behind_yielder_makes_backup_infeasible(self):
        # The yielder faces east, so the retreat axis points west; robot_3 at
        # x=-0.5 sits 0.5 m into the retreat path. Its clearance constraint
        # |0.5 - d| >= 1.7 allows only d >= 2.2, above the 2.0 band max.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -0.5, 0.0, 0.0),
        )
        result = derive_backup_distance(frame, "robot_1", ["robot_2", "robot_3"], GroundingParams())
        assert not result.feasible
        assert "band" in result.reason

    def test_far_passer_needs_only_the_band_minimum(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 3.0, 0.0, math.pi))
        result = derive_backup_distance(frame, "robot_1", ["robot_2"], GroundingParams())
        assert result.value_m == 0.5

    def test_missing_yielder_is_infeasible_with_reason(self):
        frame = _frame(("robot_2", 0.4, 0.0, math.pi))
        result = derive_backup_distance(frame, "robot_1", ["robot_2"], GroundingParams())
        assert not result.feasible
        assert "robot_1" in result.reason

    def test_missing_other_robot_is_infeasible_with_reason(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        result = derive_backup_distance(frame, "robot_1", ["robot_9"], GroundingParams())
        assert not result.feasible
        assert "robot_9" in result.reason

    def test_geometry_floors_backup_at_the_park_point(self):
        # Clearance alone needs 1.1 m here (x = -1.4 parked), inside the band
        # the marker is occluded at; the declared park point needs 1.489.
        result = derive_backup_distance(
            _head_on(-0.3, 0.3), "robot_1", ["robot_2"], GroundingParams(), geometry=_geometry()
        )
        assert result.value_m == 1.489

    def test_geometry_park_point_out_of_band_is_infeasible(self):
        # The yielder is west of the corridor but east of the passer, so its
        # own side's park point is +1.789: a 3.3 m reverse through the corridor.
        result = derive_backup_distance(
            _head_on(-1.5, -2.5), "robot_1", ["robot_2"], GroundingParams(), geometry=_geometry()
        )
        assert not result.feasible
        assert "park" in result.reason and "band" in result.reason

    def test_geometry_already_parked_backs_up_only_for_clearance(self):
        result = derive_backup_distance(
            _head_on(-1.9, 0.2), "robot_1", ["robot_2"], GroundingParams(), geometry=_geometry()
        )
        assert result.value_m == 0.5

    def test_geometry_without_crossing_robot_is_infeasible(self):
        result = derive_backup_distance(
            _head_on(-0.3, 0.3), "robot_1", [], GroundingParams(), geometry=_geometry()
        )
        assert not result.feasible

    @pytest.mark.parametrize(
        "yielder_x, passer_x",
        [(-0.04, 0.08), (-0.3, 0.3), (0.5, -0.3), (-0.47, 0.59)],
    )
    def test_geometry_matches_legacy_park_backup_where_park_dominates(self, yielder_x, passer_x):
        # Same scene_geometry derivation, not a re-derivation: wherever the
        # park point (not clearance) binds, derived and legacy agree exactly.
        legacy = _legacy_yield_params(yielder_x, passer_x)
        derived = derive_backup_distance(
            _head_on(yielder_x, passer_x),
            "robot_1",
            ["robot_2"],
            GroundingParams(),
            geometry=_geometry(),
        )
        assert derived.value_m == legacy["backup_distance_m"]


class TestDeriveEscortDistance:
    def test_reproduces_verified_head_on_tuning(self):
        # Passer at x=0.25 facing west; yielder parked at x=-1.65:
        # along-axis distance 1.9 + escort_clearance 0.5 = 2.4 (verified).
        frame = _frame(("robot_2", 0.25, 0.0, math.pi))
        result = derive_escort_distance(frame, "robot_2", (-1.65, 0.0), GroundingParams())
        assert result.feasible
        assert result.value_m == pytest.approx(2.4, abs=0.01)

    def test_out_of_band_escort_is_infeasible(self):
        frame = _frame(("robot_2", 0.25, 0.0, math.pi))
        result = derive_escort_distance(frame, "robot_2", (-3.5, 0.0), GroundingParams())
        assert not result.feasible
        assert "band" in result.reason

    def test_passer_facing_away_is_infeasible(self):
        frame = _frame(("robot_2", 0.25, 0.0, 0.0))
        result = derive_escort_distance(frame, "robot_2", (-1.65, 0.0), GroundingParams())
        assert not result.feasible

    def test_missing_passer_is_infeasible(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        result = derive_escort_distance(frame, "robot_9", (0.0, 0.0), GroundingParams())
        assert not result.feasible
        assert "robot_9" in result.reason

    @pytest.mark.parametrize(
        "yielder_x, passer_x",
        [(-0.04, 0.08), (-0.3, 0.3), (0.5, -0.3), (-0.47, 0.59)],
    )
    def test_geometry_matches_legacy_escort(self, yielder_x, passer_x):
        legacy = _legacy_yield_params(yielder_x, passer_x)
        derived = derive_escort_distance(
            _head_on(yielder_x, passer_x),
            "robot_2",
            (legacy["park_coord_m"], 0.36),
            GroundingParams(),
            geometry=_geometry(),
        )
        assert derived.value_m == legacy["passer_escort_distance_m"]


class TestDerivationModel:
    def test_derivation_is_frozen(self):
        derivation = Derivation(feasible=True, value_m=1.0)
        with pytest.raises(ValidationError):
            derivation.feasible = False  # type: ignore[misc]


class TestLoadGroundingParams:
    def test_missing_section_yields_defaults(self, tmp_path):
        config = tmp_path / "rag.yaml"
        config.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
        params = load_grounding_params(Path(config))
        assert params.mode == "legacy"
        assert params.backup_clearance_m == 1.7

    def test_section_overrides_defaults(self, tmp_path):
        config = tmp_path / "rag.yaml"
        config.write_text("grounding:\n  mode: derived\n  lateral_m: 0.4\n", encoding="utf-8")
        params = load_grounding_params(Path(config))
        assert params.mode == "derived"
        assert params.lateral_m == 0.4

    def test_unknown_key_fails_loudly(self, tmp_path):
        config = tmp_path / "rag.yaml"
        config.write_text("grounding:\n  lateral: 0.4\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_grounding_params(Path(config))

    def test_repo_config_parses_as_legacy(self):
        params = load_grounding_params(Path("config/rag.yaml"))
        assert params.mode == "legacy"  # live loop stays legacy until the M5 flip
        assert params == GroundingParams()


def _legacy_yield_params(yielder_x: float, passer_x: float) -> dict:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="standoff",
        strategy="yield",
        justification="j",
    )
    result = ReasonerResult(
        request_id="req-1",
        decision=decision,
        raw_text=None,
        diagnostics=ReasonerDiagnostics(
            request_id="req-1", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )
    command = ground_reasoner_result(
        result,
        robot_positions={"robot_1": (yielder_x, 0.0), "robot_2": (passer_x, 0.0)},
        geometry=_geometry(),
    )
    return command["actions"][0]["parameters"]
