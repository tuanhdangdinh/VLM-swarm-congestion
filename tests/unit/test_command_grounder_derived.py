"""Derived-mode grounding (rev-8 Appendix A) and the legacy-equivalence pins.

Kept apart from test_command_grounder.py so that file stays byte-for-byte
unmodified: every pre-existing legacy assertion is part of the guarantee.
"""

import hashlib
import itertools
import json
import math

import pytest

from reasoning.rag.command_grounder import (
    DEGRADATION_TAGS,
    CommandGroundingError,
    degradation_cause,
    ground_reasoner_result,
    prepare_retreat_selection,
    resolve_yield_roles,
    validate_coordination_command,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import ArmGeometry, CorridorGeometry, SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)


def _decision(**overrides) -> CongestionDecision:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "head-on standoff",
        "strategy": "yield",
        "justification": "j",
        "yield_robot": "robot_1",
    }
    base.update(overrides)
    return CongestionDecision(**base)


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-1",
        decision=decision,
        raw_text=None,
        diagnostics=ReasonerDiagnostics(
            request_id="req-1", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _frame(*robots: tuple[str, float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta) for rid, x, y, theta in robots
        ],
    )


def _head_on_frame() -> SnapshotFrame:
    return _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 0.4, 0.0, math.pi))


def _geometry() -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _junction_geometry(**arms: ArmGeometry) -> SceneGeometry:
    # Mirrors the four-way corridor in the 2026-09-29 design study (section
    # 4, "Arm B classification against where the waiting robots are held").
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
        ),
        arms=arms or None,
    )


def _positions_frame(positions: dict[str, tuple[float, float]]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0) for rid, (x, y) in positions.items()
        ],
    )


_DERIVED = GroundingParams(mode="derived", aisle_y_band_m=(-0.6, 0.6))
_DERIVED_GEOMETRY = GroundingParams(mode="derived")
# Family blocker and deadlock positions, as in test_command_grounder.py.
_WEST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)
_DEADLOCK = _frame(("robot_1", -0.3, 0.0, 0.0), ("robot_2", 0.3, 0.0, math.pi))


# Legacy-equivalence matrix: every strategy x yielder x position set x
# geometry x gate configuration (576 inputs). The digest was computed at
# d255a09, the commit before the mode switch existed, so it pins the legacy
# output to the behaviour every collected decision artifact was grounded with.
_LEGACY_MATRIX_SHA256 = "d1958150f10e2436e4d5709118cbfcd2788a34210b2a99a6d82f023fef0f3eb4"
_MATRIX_STRATEGIES = [
    "yield",
    "reverse",
    "temporary_wait",
    "reroute",
    "convoy",
    "priority_override",
]
_MATRIX_POSITIONS = [
    None,
    {"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
    {"robot_1": (-0.04, 0.0), "robot_2": (0.08, 0.0)},
    {"robot_1": (-2.5, 0.0), "robot_2": (-1.5, 0.0)},
    {"robot_1": (-1.9, 0.0), "robot_2": (0.2, 0.0)},
    {"robot_1": (-0.1, 0.0), "robot_2": (12.0, 0.0)},
]
_MATRIX_GATES = [
    ((), "off"),
    ((_WEST_BLOCKER,), "off"),
    ((_WEST_BLOCKER,), "swap"),
    ((_WEST_BLOCKER,), "refuse"),
]


def _matrix_result(strategy: str, yield_robot: str | None) -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=["robot_1", "robot_2"],
        root_cause="head-on aisle conflict",
        strategy=strategy,
        justification="robots are stopped face to face",
        yield_robot=yield_robot,
    )
    return ReasonerResult(
        request_id="req1",
        decision=decision,
        raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req1", backend_id="openai", attempts=1, parse_status="valid"
        ),
    )


def _matrix_digest(**extra) -> str:
    outputs = []
    for strategy, yield_robot, positions, geometry, (obstacles, mode) in itertools.product(
        _MATRIX_STRATEGIES, [None, "robot_2"], _MATRIX_POSITIONS, [None, _geometry()], _MATRIX_GATES
    ):
        kwargs = dict(extra)
        if "snapshot" in kwargs:
            kwargs["snapshot"] = _positions_frame(positions or {"robot_1": (0.0, 0.0)})
        outputs.append(
            ground_reasoner_result(
                _matrix_result(strategy, yield_robot),
                robot_positions=positions,
                geometry=geometry,
                static_obstacles=obstacles,
                yield_feasibility_mode=mode,
                **kwargs,
            )
        )
    assert all("degradations" not in command for command in outputs)
    blob = json.dumps(outputs, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class TestLegacyModeUnchanged:
    def test_legacy_matrix_matches_pre_switch_digest(self):
        assert _matrix_digest() == _LEGACY_MATRIX_SHA256

    def test_explicit_legacy_params_ignore_every_derived_argument(self):
        # What the M5 flip will look like: snapshot, stage-2 choice and order
        # all supplied, only `mode` still legacy. Output must not move.
        digest = _matrix_digest(
            params=GroundingParams(),
            snapshot=True,
            retreat_choice=RetreatChoiceDecision(retreat_choice="B", justification="j"),
            crossing_order=["robot_2"],
        )
        assert digest == _LEGACY_MATRIX_SHA256

    def test_no_arguments_means_legacy_without_degradations(self):
        command = ground_reasoner_result(_result(_decision()))
        assert "degradations" not in command
        assert command["actions"][0]["parameters"]["backup_distance_m"] == 1.3

    def test_repo_config_is_derived_with_default_thresholds(self):
        # Flipped 2026-09-28: the shipped config is exactly the derived-mode
        # defaults, so every `_DERIVED_GEOMETRY` test here speaks for it.
        from pathlib import Path

        from reasoning.rag.maneuver_geometry import load_grounding_params

        assert load_grounding_params(Path("config/rag.yaml")) == _DERIVED_GEOMETRY

    def test_repo_config_keeps_the_verified_maneuver_m4_executes(self):
        # Not byte equality (derived adds degradations, retreat_* instead of
        # park_*, linked_position, crossing_order): every parameter M4 reads
        # matches the legacy command at the verified deadlock pose.
        from pathlib import Path

        from reasoning.rag.maneuver_geometry import load_grounding_params

        legacy = ground_reasoner_result(
            _result(_decision()),
            robot_positions={"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
            geometry=_geometry(),
        )
        derived = ground_reasoner_result(
            _result(_decision()),
            snapshot=_DEADLOCK,
            params=load_grounding_params(Path("config/rag.yaml")),
            geometry=_geometry(),
        )
        m4_keys = (
            "backup_distance_m", "hold_sec", "pull_off_lateral_m", "passer_robot_id",
            "passer_clear_m", "passer_escort_distance_m",
        )
        for index in (0, 1):
            assert derived["actions"][index]["robot_id"] == legacy["actions"][index]["robot_id"]
            assert derived["actions"][index]["action"] == legacy["actions"][index]["action"]
        legacy_yield = legacy["actions"][0]["parameters"]
        derived_yield = derived["actions"][0]["parameters"]
        assert {k: derived_yield[k] for k in m4_keys} == {k: legacy_yield[k] for k in m4_keys}
        assert derived_yield["retreat_x_m"] == legacy_yield["park_coord_m"]
        assert (
            derived["actions"][1]["parameters"]["duration_sec"]
            == legacy["actions"][1]["parameters"]["duration_sec"]
        )
        assert derived["expected_resolution_time_sec"] == legacy["expected_resolution_time_sec"]


class TestDerivedYield:
    def test_derived_distances_and_ordering_fields(self):
        command = ground_reasoner_result(
            _result(_decision()), snapshot=_head_on_frame(), params=_DERIVED
        )
        yield_action = command["actions"][0]
        assert yield_action["robot_id"] == "robot_1"
        p = yield_action["parameters"]
        assert p["backup_distance_m"] == 1.3
        # Escort here is 2.2, not the verified scenario's 2.4: this synthetic
        # yielder starts at x=0 (not -0.35), so the chosen candidate parks at
        # x=-1.3 and the passer's along-axis distance is 1.7 + clearance 0.5.
        assert p["passer_escort_distance_m"] == 2.2
        assert p["passer_clear_m"] == 2.2
        assert p["crossing_order"] == ["robot_2"]
        assert p["retreat_choice"] == "A"
        assert (p["retreat_x_m"], p["retreat_y_m"]) == (-1.3, 0.35)
        assert command["degradations"] == ["retreat=default:no_choice"]
        waits = [a for a in command["actions"] if a["action"] == "temporary_wait"]
        assert waits[0]["robot_id"] == "robot_2"
        assert waits[0]["parameters"] == {"duration_sec": 120.0, "linked_position": 0}
        assert command["expected_resolution_time_sec"] == 150.0

    def test_retreat_choice_applied_without_default_tag(self):
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_head_on_frame(),
            params=_DERIVED,
            retreat_choice=RetreatChoiceDecision(retreat_choice="B", justification="j"),
        )
        p = command["actions"][0]["parameters"]
        assert p["retreat_choice"] == "B"
        assert p["pull_off_lateral_m"] == -0.35
        assert command["degradations"] == []

    def test_unrendered_retreat_label_falls_back_to_default(self):
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_head_on_frame(),
            params=_DERIVED,
            retreat_choice=RetreatChoiceDecision(retreat_choice="D", justification="j"),
        )
        assert command["actions"][0]["parameters"]["retreat_choice"] == "A"
        assert command["degradations"] == ["retreat=default:invalid_label"]

    def test_missing_yield_robot_uses_legacy_convention_tagged(self):
        command = ground_reasoner_result(
            _result(_decision(yield_robot=None)), snapshot=_head_on_frame(), params=_DERIVED
        )
        assert command["actions"][0]["robot_id"] == "robot_1"
        assert "roles=legacy-convention" in command["degradations"]

    def test_default_is_the_ranked_first_candidate_by_construction(self):
        # Arm B's stage-2 answer is ranked[0]; the no-choice fallback must
        # ground exactly that pose, differing only in the degradation tag.
        selection = prepare_retreat_selection(_head_on_frame(), "robot_1", ["robot_2"], _DERIVED)
        classical = RetreatChoiceDecision(
            retreat_choice=selection.candidates[0].label, justification="geometry-max"
        )
        fallback = ground_reasoner_result(
            _result(_decision()), snapshot=_head_on_frame(), params=_DERIVED
        )
        explicit = ground_reasoner_result(
            _result(_decision()),
            snapshot=_head_on_frame(),
            params=_DERIVED,
            retreat_choice=classical,
        )
        assert fallback["actions"] == explicit["actions"]
        assert fallback["degradations"] == ["retreat=default:no_choice"]
        assert explicit["degradations"] == []


class TestDerivedWithGeometry:
    def test_reproduces_the_legacy_scene_geometry_maneuver(self):
        # Same scene_geometry derivations as the legacy grounder: at the
        # deadlock positions the derived yield lands on the pinned legacy
        # numbers (backup 1.489, lateral 0.36, escort 2.739).
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_DEADLOCK,
            params=_DERIVED_GEOMETRY,
            geometry=_geometry(),
        )
        p = command["actions"][0]["parameters"]
        assert p["backup_distance_m"] == 1.489
        assert p["pull_off_lateral_m"] == 0.36
        assert p["passer_escort_distance_m"] == 2.739
        assert p["retreat_x_m"] == -1.789
        assert command["degradations"] == ["retreat=default:no_choice"]

    def test_gate_swap_runs_before_candidates(self):
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_DEADLOCK,
            params=_DERIVED_GEOMETRY,
            geometry=_geometry(),
            static_obstacles=(_WEST_BLOCKER,),
            yield_feasibility_mode="swap",
        )
        yield_action = command["actions"][0]
        assert yield_action["robot_id"] == "robot_2"
        p = yield_action["parameters"]
        assert p["yield_robot_grounded_from"] == "robot_1"
        assert "robot_1 has" in p["yield_regrounded_reason"]
        # robot_2 retreats east, to its own side, away from the blocker.
        assert p["retreat_x_m"] == 1.789
        assert p["crossing_order"] == ["robot_1"]
        assert command["degradations"] == ["yield_robot=regrounded", "retreat=default:no_choice"]

    def test_gate_swap_matches_legacy_swap_distances(self):
        kwargs = {
            "geometry": _geometry(),
            "static_obstacles": (_WEST_BLOCKER,),
            "yield_feasibility_mode": "swap",
        }
        legacy = ground_reasoner_result(
            _result(_decision()),
            robot_positions={"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
            **kwargs,
        )
        derived = ground_reasoner_result(
            _result(_decision()), snapshot=_DEADLOCK, params=_DERIVED_GEOMETRY, **kwargs
        )
        derived_params = derived["actions"][0]["parameters"]
        legacy_params = legacy["actions"][0]["parameters"]
        for key in ("backup_distance_m", "passer_escort_distance_m", "passer_robot_id"):
            assert derived_params[key] == legacy_params[key]

    def test_gate_refusal_keeps_the_legacy_wait_fan_out(self):
        kwargs = {
            "geometry": _geometry(),
            "static_obstacles": (_WEST_BLOCKER,),
            "yield_feasibility_mode": "refuse",
        }
        legacy = ground_reasoner_result(
            _result(_decision()),
            robot_positions={"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
            **kwargs,
        )
        derived = ground_reasoner_result(
            _result(_decision()), snapshot=_DEADLOCK, params=_DERIVED_GEOMETRY, **kwargs
        )
        assert {k: v for k, v in derived.items() if k != "degradations"} == legacy
        assert len(derived["degradations"]) == 1
        assert derived["degradations"][0].startswith("yield=infeasible:yield refused")

    def test_same_side_refusal_is_kept(self):
        frame = _frame(("robot_1", -2.5, 0.0, 0.0), ("robot_2", -1.5, 0.0, math.pi))
        legacy = ground_reasoner_result(
            _result(_decision()),
            robot_positions={"robot_1": (-2.5, 0.0), "robot_2": (-1.5, 0.0)},
            geometry=_geometry(),
        )
        derived = ground_reasoner_result(
            _result(_decision()), snapshot=frame, params=_DERIVED_GEOMETRY, geometry=_geometry()
        )
        assert {k: v for k, v in derived.items() if k != "degradations"} == legacy
        assert derived["degradations"][0].startswith("yield=infeasible:yield refused: both")

    def test_park_point_out_of_band_reroutes_the_yielder(self):
        # Yielder west of the corridor but east of the passer: its own-side
        # park point is on the far side of the corridor (3.3 m away).
        frame = _frame(("robot_1", -1.2, 0.0, math.pi), ("robot_2", -0.5, 0.0, 0.0))
        derived = ground_reasoner_result(
            _result(_decision(yield_robot="robot_2")),
            snapshot=frame,
            params=_DERIVED_GEOMETRY,
            geometry=_geometry(),
        )
        assert derived["actions"][0] == {
            "robot_id": "robot_2",
            "action": "reroute",
            "parameters": {"waypoints": []},
        }
        assert derived["degradations"][0].startswith("yield=infeasible:park point")


class TestDerivedDegradations:
    def test_no_snapshot_degrades_yield_to_nonspatial_wait(self):
        command = ground_reasoner_result(_result(_decision()), snapshot=None, params=_DERIVED)
        assert all(a["action"] == "temporary_wait" for a in command["actions"])
        assert all(a["parameters"]["requested_strategy"] == "yield" for a in command["actions"])
        assert command["degradations"] == ["distances=unavailable"]

    def test_no_snapshot_degrades_reverse_to_nonspatial_wait(self):
        command = ground_reasoner_result(
            _result(_decision(strategy="reverse", yield_robot=None)), params=_DERIVED
        )
        assert all(a["action"] == "temporary_wait" for a in command["actions"])
        assert command["degradations"] == ["distances=unavailable"]

    def test_no_snapshot_is_not_a_degradation_for_a_wait(self):
        # A wait needs no distances: tagging it would inflate no_snapshot.
        command = ground_reasoner_result(
            _result(_decision(strategy="temporary_wait", yield_robot=None)), params=_DERIVED
        )
        assert command["degradations"] == []
        assert command["actions"][0]["parameters"] == {"duration_sec": 8.0}

    def test_involved_robot_missing_from_snapshot_is_unavailable(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        command = ground_reasoner_result(_result(_decision()), snapshot=frame, params=_DERIVED)
        assert all(a["action"] == "temporary_wait" for a in command["actions"])
        assert command["degradations"] == ["distances=unavailable"]
        assert "robot_2 not in snapshot" in command["actions"][0]["parameters"]["reason"]

    def test_infeasible_backup_returns_reroute_outcome(self):
        # A third robot 0.5 m behind the yielder blocks the retreat band.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -0.5, 0.0, 0.0),
        )
        command = ground_reasoner_result(
            _result(_decision(involved_robots=["robot_1", "robot_2", "robot_3"])),
            snapshot=frame,
            params=_DERIVED,
        )
        assert command["actions"][0]["action"] == "reroute"
        assert command["actions"][0]["robot_id"] == "robot_1"
        assert command["degradations"][0] == "order=implicit"
        assert command["degradations"][1].startswith("yield=infeasible:no backup distance")

    def test_no_valid_candidate_returns_reroute_outcome(self):
        # robot_3 on the shared backup path vetoes every candidate.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 0.35, 0.0),
        )
        command = ground_reasoner_result(
            _result(_decision()), snapshot=frame, params=_DERIVED
        )
        assert command["actions"][0]["action"] == "reroute"
        assert command["degradations"] == ["retreat=no-valid-candidate"]

    def test_reverse_refusal_is_tagged(self):
        frame = _frame(("robot_1", -2.5, 0.0, 0.0), ("robot_2", -1.5, 0.0, math.pi))
        command = ground_reasoner_result(
            _result(_decision(strategy="reverse", yield_robot=None)),
            snapshot=frame,
            params=_DERIVED_GEOMETRY,
            geometry=_geometry(),
        )
        assert command["degradations"][0].startswith("reverse=infeasible:reverse refused")

    def test_unsupported_strategy_wait_is_tagged(self):
        command = ground_reasoner_result(
            _result(_decision(strategy="convoy", yield_robot=None)),
            snapshot=_head_on_frame(),
            params=_DERIVED,
        )
        assert command["degradations"] == ["strategy=unsupported:convoy"]

    def test_reroute_passes_through_untagged(self):
        command = ground_reasoner_result(
            _result(_decision(strategy="reroute", yield_robot=None)),
            snapshot=_head_on_frame(),
            params=_DERIVED,
        )
        assert command["actions"][0]["action"] == "reroute"
        assert command["degradations"] == []

    def test_empty_decision_still_raises(self):
        empty = _result(_decision()).model_copy(update={"decision": None})
        with pytest.raises(CommandGroundingError):
            ground_reasoner_result(empty, snapshot=_head_on_frame(), params=_DERIVED)


class TestCrossingOrder:
    _THREE = _frame(
        ("robot_1", 0.0, 0.0, 0.0),
        ("robot_2", 0.4, 0.0, math.pi),
        ("robot_3", 1.2, 0.0, math.pi),
    )

    def _ground(self, crossing_order=None):
        return ground_reasoner_result(
            _result(_decision(involved_robots=["robot_1", "robot_2", "robot_3"])),
            snapshot=self._THREE,
            params=_DERIVED,
            crossing_order=crossing_order,
        )

    def test_explicit_order_sequences_the_waits(self):
        command = self._ground(["robot_3", "robot_2"])
        p = command["actions"][0]["parameters"]
        assert p["crossing_order"] == ["robot_3", "robot_2"]
        assert p["passer_robot_id"] == "robot_3"
        waits = [
            (a["robot_id"], a["parameters"]["linked_position"]) for a in command["actions"][1:]
        ]
        assert waits == [("robot_3", 0), ("robot_2", 1)]
        assert command["degradations"] == ["retreat=default:no_choice"]

    def test_non_permutation_order_falls_back_tagged(self):
        command = self._ground(["robot_2"])
        assert command["actions"][0]["parameters"]["crossing_order"] == ["robot_2", "robot_3"]
        assert "order=default:non_permutation" in command["degradations"]

    def test_implicit_order_for_three_robots_is_tagged(self):
        assert "order=implicit" in self._ground()["degradations"]

    def _ground_decision_order(self, decision_order, crossing_order=None, yield_robot="robot_1"):
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            yield_robot=yield_robot,
            crossing_order=decision_order,
        )
        return ground_reasoner_result(
            _result(decision),
            snapshot=self._THREE,
            params=_DERIVED,
            crossing_order=crossing_order,
        )

    def test_decision_crossing_order_is_used_when_caller_passes_none(self):
        # The decision lists every involved robot, yielder last; the grounder
        # takes the non-yielders in that order.
        command = self._ground_decision_order(["robot_3", "robot_2", "robot_1"])
        p = command["actions"][0]["parameters"]
        assert p["crossing_order"] == ["robot_3", "robot_2"]
        assert p["passer_robot_id"] == "robot_3"
        assert "order=implicit" not in command["degradations"]
        assert "order=default:non_permutation" not in command["degradations"]

    def test_decision_crossing_order_drops_the_yielder_wherever_it_sits(self):
        command = self._ground_decision_order(["robot_1", "robot_3", "robot_2"])
        assert command["actions"][0]["parameters"]["crossing_order"] == ["robot_3", "robot_2"]

    def test_explicit_caller_order_overrides_the_decision_order(self):
        command = self._ground_decision_order(
            ["robot_3", "robot_2", "robot_1"], crossing_order=["robot_2", "robot_3"]
        )
        assert command["actions"][0]["parameters"]["crossing_order"] == ["robot_2", "robot_3"]


class TestResolveYieldRoles:
    def test_rejects_a_non_yield_decision(self):
        with pytest.raises(ValueError):
            resolve_yield_roles(_decision(strategy="reroute"), _head_on_frame())

    def test_single_robot_yield_is_refused(self):
        roles = resolve_yield_roles(_decision(involved_robots=["robot_1"]), _head_on_frame())
        assert roles.refusal_reason is not None
        assert roles.degradations == ["yield=no-passer"]

    def test_stage_two_flow_grounds_the_rendered_pose(self):
        # The Phase-2 sequence: resolve roles (gate included), render the
        # selection for that yielder, ask stage 2, ground the answer.
        kwargs = {
            "geometry": _geometry(),
            "static_obstacles": (_WEST_BLOCKER,),
            "yield_feasibility_mode": "swap",
        }
        roles = resolve_yield_roles(_decision(), _DEADLOCK, **kwargs)
        selection = prepare_retreat_selection(
            _DEADLOCK,
            roles.yielder_id,
            roles.crossing_order,
            _DERIVED_GEOMETRY,
            geometry=_geometry(),
        )
        rendered = selection.candidates[1]
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_DEADLOCK,
            params=_DERIVED_GEOMETRY,
            retreat_choice=RetreatChoiceDecision(retreat_choice=rendered.label, justification="j"),
            **kwargs,
        )
        yield_action = command["actions"][0]
        assert yield_action["robot_id"] == roles.yielder_id == "robot_2"
        p = yield_action["parameters"]
        assert (p["retreat_x_m"], p["retreat_y_m"]) == (round(rendered.x, 3), round(rendered.y, 3))


class TestJunctionSameAxisFilter:
    """J1 (v2-branch divergence from the v1-frozen Arm B, design study
    2026-09-29 section 4 / Decision): two robots held on the same declared
    arm axis but opposite sides cannot both get a sane crossing action --
    the IB10 replay has `robot_3`'s escort pass through `robot_4` at
    0.000 m. The filter drops such a pair, not "any robot off the yielder's
    axis": a legitimate cross-axis passer with no opposite-side partner
    (e.g. `bottleneck_merge`'s T-junction) is untouched -- see
    `TestCrossAxisPasserWithNoPartner` below.
    """

    _FOUR_WAY_ARMS = {
        "robot_1": ArmGeometry(axis="x", side=-1),
        "robot_2": ArmGeometry(axis="x", side=1),
        "robot_3": ArmGeometry(axis="y", side=-1),
        "robot_4": ArmGeometry(axis="y", side=1),
    }

    def _four_way_frame(self) -> SnapshotFrame:
        # h = 1.2, the study's C' held-in-zone offset (section "C' -- held in
        # zone"); robot_2 yields E-W, robot_1 is its same-axis passer.
        return _positions_frame(
            {
                "robot_1": (-0.33, 0.0),
                "robot_2": (0.33, 0.0),
                "robot_3": (0.0, -1.2),
                "robot_4": (0.0, 1.2),
            }
        )

    def test_cross_axis_waiters_are_dropped_from_the_lead_of_the_order(self):
        # Arm B's own order (study table, section 4): robot_3, robot_4,
        # robot_1, yielder robot_2 last.
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3", "robot_4"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_3", "robot_4", "robot_1", "robot_2"],
        )
        geometry = _junction_geometry(**self._FOUR_WAY_ARMS)

        roles = resolve_yield_roles(decision, self._four_way_frame(), geometry=geometry)

        # Study: "Executed order with J1 | robot_1 only (one passer)".
        assert roles.crossing_order == ["robot_1"]
        assert roles.refusal_reason is None
        assert "order=junction_same_axis" in roles.degradations

    def test_same_axis_waiter_is_kept_in_place(self):
        # Tie/edge case: a same-axis waiter ahead of the eventual passer
        # survives the filter untouched, in its original FCFS position.
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_5"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_5", "robot_1", "robot_2"],
        )
        arms = {**self._FOUR_WAY_ARMS, "robot_5": ArmGeometry(axis="x", side=-1)}
        geometry = _junction_geometry(**arms)
        frame = _positions_frame(
            {"robot_1": (-0.33, 0.0), "robot_2": (0.33, 0.0), "robot_5": (-0.5, 0.0)}
        )

        roles = resolve_yield_roles(decision, frame, geometry=geometry)

        assert roles.crossing_order == ["robot_5", "robot_1"]
        assert "order=junction_same_axis" not in roles.degradations

    def test_an_undeclared_arm_waiter_is_not_filtered(self):
        # A robot with no declared arm carries no axis to differ by, so it
        # is left on the single corridor's crossing order untouched.
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_6"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_6", "robot_1", "robot_2"],
        )
        geometry = _junction_geometry(**self._FOUR_WAY_ARMS)
        frame = _positions_frame(
            {"robot_1": (-0.33, 0.0), "robot_2": (0.33, 0.0), "robot_6": (-0.5, 0.0)}
        )

        roles = resolve_yield_roles(decision, frame, geometry=geometry)

        assert roles.crossing_order == ["robot_6", "robot_1"]
        assert "order=junction_same_axis" not in roles.degradations

    def test_refuses_when_no_involved_robot_shares_the_yielder_axis(self):
        decision = _decision(
            involved_robots=["robot_2", "robot_3", "robot_4"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_3", "robot_4", "robot_2"],
        )
        geometry = _junction_geometry(**self._FOUR_WAY_ARMS)
        frame = _positions_frame(
            {"robot_2": (0.33, 0.0), "robot_3": (0.0, -1.2), "robot_4": (0.0, 1.2)}
        )

        roles = resolve_yield_roles(decision, frame, geometry=geometry)

        assert roles.crossing_order == []
        assert roles.refusal_reason is not None
        assert "order=junction_same_axis" in roles.degradations
        assert "yield=no-passer" in roles.degradations

    def test_filter_is_a_noop_without_a_declared_yielder_arm(self):
        # Regression pin: a geometry that declares no `arms` at all (every
        # non-junction scene, e.g. `_geometry()`) must ground
        # byte-identically -- the filter never fires.
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_3", "robot_1", "robot_2"],
        )
        frame = _positions_frame(
            {"robot_1": (-0.33, 0.0), "robot_2": (0.33, 0.0), "robot_3": (0.0, -1.2)}
        )

        roles = resolve_yield_roles(decision, frame, geometry=_geometry())

        assert roles.crossing_order == ["robot_3", "robot_1"]
        assert "order=junction_same_axis" not in roles.degradations

    def test_filter_is_a_noop_with_no_geometry_at_all(self):
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_3", "robot_1", "robot_2"],
        )
        frame = _positions_frame(
            {"robot_1": (-0.33, 0.0), "robot_2": (0.33, 0.0), "robot_3": (0.0, -1.2)}
        )

        roles = resolve_yield_roles(decision, frame)

        assert roles.crossing_order == ["robot_3", "robot_1"]
        assert "order=junction_same_axis" not in roles.degradations


class TestCrossAxisPasserWithNoPartner:
    """A cross-axis passer with no opposite-side partner is NOT the J1
    pattern (`reasoning/rag/command_grounder.py:_junction_same_axis_order`):
    mirrors the real, already-shipped `bottleneck_merge` (B1) T-junction,
    whose yielder's declared arm is perpendicular to its only passer.
    Regression pin found by running the full local suite after landing J1 --
    the literal "drop every robot off the yielder's axis" reading refused
    this scene outright (`tests/unit/test_bottleneck_merge_scenario.py`).
    """

    _T_JUNCTION_ARMS = {
        "robot_1": ArmGeometry(axis="x", side=-1),
        "robot_2": ArmGeometry(axis="y", side=1),
        "robot_3": ArmGeometry(axis="x", side=-1),
    }

    def test_lone_cross_axis_passer_is_kept(self):
        decision = _decision(
            involved_robots=["robot_1", "robot_2"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_1", "robot_2"],
        )
        geometry = _junction_geometry(**self._T_JUNCTION_ARMS)
        frame = _positions_frame({"robot_1": (-0.3, 0.0), "robot_2": (0.2, 0.4)})

        roles = resolve_yield_roles(decision, frame, geometry=geometry)

        assert roles.crossing_order == ["robot_1"]
        assert roles.refusal_reason is None
        assert "order=junction_same_axis" not in roles.degradations

    def test_a_same_side_queue_behind_the_passer_is_kept(self):
        # robot_1 and robot_3 are both on the yielder's cross axis, same
        # side (queued one behind the other), not opposite -- no pair to
        # drop (the mock bottleneck_merge_yield_once.json shape).
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            type="bottleneck",
            yield_robot="robot_2",
            crossing_order=["robot_1", "robot_3", "robot_2"],
        )
        geometry = _junction_geometry(**self._T_JUNCTION_ARMS)
        frame = _positions_frame(
            {"robot_1": (-0.3, 0.0), "robot_2": (0.2, 0.4), "robot_3": (-0.6, 0.0)}
        )

        roles = resolve_yield_roles(decision, frame, geometry=geometry)

        assert roles.crossing_order == ["robot_1", "robot_3"]
        assert "order=junction_same_axis" not in roles.degradations


class TestPrepareRetreatSelection:
    def test_selection_exposes_ranked_candidates(self):
        selection = prepare_retreat_selection(_head_on_frame(), "robot_1", ["robot_2"], _DERIVED)
        assert selection.backup.feasible
        assert [c.label for c in selection.candidates] == ["A", "B"]
        assert selection.yielder_id == "robot_1"

    def test_infeasible_backup_yields_empty_candidates(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        selection = prepare_retreat_selection(frame, "robot_1", ["robot_9"], _DERIVED)
        assert not selection.backup.feasible
        assert selection.candidates == []

    def test_selection_is_deterministic(self):
        first = prepare_retreat_selection(_head_on_frame(), "robot_1", ["robot_2"], _DERIVED)
        second = prepare_retreat_selection(_head_on_frame(), "robot_1", ["robot_2"], _DERIVED)
        assert first == second


class TestDegradationTags:
    @pytest.mark.parametrize(
        "tag, cause",
        [
            ("distances=unavailable", "no_snapshot"),
            ("yield=infeasible:no backup distance in band", "infeasible_geometry"),
            ("reverse=infeasible:reverse refused", "infeasible_geometry"),
            ("retreat=no-valid-candidate", "infeasible_geometry"),
            ("retreat=default:invalid_label", "invalid_label"),
            ("retreat=default:no_choice", None),
            ("order=default:non_permutation", "non_permutation_order"),
            ("order=implicit", None),
            ("order=junction_same_axis", None),
            ("roles=legacy-convention", None),
            ("yield_robot=regrounded", None),
            ("strategy=unsupported:convoy", None),
            # Stage-1 parser tags (prompt-v2 optional fields), one vocabulary.
            ("blocker_kind=default:invalid_label", "invalid_label"),
            ("crossing_order=default:non_permutation", "non_permutation_order"),
        ],
    )
    def test_tag_maps_to_measurement_cause(self, tag, cause):
        assert degradation_cause(tag) == cause

    def test_unknown_tag_raises(self):
        with pytest.raises(KeyError):
            degradation_cause("retreat=mystery")

    def test_every_key_resolves_to_itself(self):
        for key, cause in DEGRADATION_TAGS.items():
            assert degradation_cause(key) == cause


class TestCommandSchema:
    def test_degradations_list_is_schema_valid(self):
        command = {
            "command_id": "c",
            "actions": [{"robot_id": "robot_1", "action": "temporary_wait"}],
            "expected_resolution_time_sec": 1,
            "fallback": "stop",
            "degradations": ["retreat=default:no_choice"],
        }
        assert validate_coordination_command(command) == command

    def test_non_string_degradation_rejected(self):
        with pytest.raises(CommandGroundingError):
            validate_coordination_command(
                {
                    "command_id": "c",
                    "actions": [{"robot_id": "robot_1", "action": "temporary_wait"}],
                    "expected_resolution_time_sec": 1,
                    "fallback": "stop",
                    "degradations": [3],
                }
            )


# Two-robot derived commands: every strategy x yielder x pose x geometry, as
# grounded before the per-passer clearances and backstop scaling (tree
# 9d20b39). One passer means no crossing_clear_m and unscaled backstops.
_DERIVED_TWO_ROBOT_SHA256 = "702b7392f41efa548a5eac8b824f3e05dd2ad8152354d8b5eb34e9334e3a3913"


def _derived_two_robot_digest() -> str:
    outputs = []
    poses = [
        {"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)},
        {"robot_1": (-0.12, 0.0), "robot_2": (0.12, 0.0)},
        {"robot_1": (-0.04, 0.02), "robot_2": (0.08, -0.03)},
    ]
    for strategy, yield_robot, positions, geometry, params in itertools.product(
        _MATRIX_STRATEGIES, [None, "robot_2"], poses, [None, _geometry()],
        [_DERIVED, _DERIVED_GEOMETRY],
    ):
        frame = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0 if rid == "robot_1" else math.pi)
                for rid, (x, y) in positions.items()
            ],
        )
        outputs.append(
            ground_reasoner_result(
                _matrix_result(strategy, yield_robot),
                snapshot=frame,
                params=params,
                geometry=geometry,
            )
        )
    return hashlib.sha256(json.dumps(outputs, sort_keys=True).encode("utf-8")).hexdigest()


def test_two_robot_derived_commands_are_unchanged():
    assert _derived_two_robot_digest() == _DERIVED_TWO_ROBOT_SHA256


class TestDerivedMultiPasser:
    # T2b oracle order: robot_2 yields east, robot_1 then the queued robot_3 cross.
    _T2B = _frame(
        ("robot_1", -0.12, 0.0, 0.0),
        ("robot_2", 0.12, 0.0, math.pi),
        ("robot_3", -2.45, 0.0, 0.0),
    )

    def _ground(self):
        decision = _decision(
            involved_robots=["robot_1", "robot_2", "robot_3"],
            yield_robot="robot_2",
            crossing_order=["robot_1", "robot_3", "robot_2"],
        )
        return ground_reasoner_result(
            _result(decision), snapshot=self._T2B, params=_DERIVED_GEOMETRY, geometry=_geometry()
        )

    def test_each_passer_gets_its_own_clearance(self):
        p = self._ground()["actions"][0]["parameters"]
        park_x = p["retreat_x_m"]
        assert p["crossing_order"] == ["robot_1", "robot_3"]
        assert p["crossing_clear_m"][0] == p["passer_clear_m"]
        # Unbanded: 4.4 m exceeds the 3.5 m escort band that sizes one passer.
        assert p["crossing_clear_m"][1] == pytest.approx(abs(-2.45 - park_x) + 0.65, abs=1e-3)
        assert p["crossing_clear_m"][1] > _DERIVED_GEOMETRY.escort_band_m[1]
        assert p["crossing_escort_m"] == p["crossing_clear_m"]

    def test_m4_plans_the_per_passer_clearances(self):
        from swarm_execution.crossing_chain import plan_crossing

        p = self._ground()["actions"][0]["parameters"]
        plans = plan_crossing(p)
        assert [plan.robot_id for plan in plans] == ["robot_1", "robot_3"]
        assert [plan.clear_m for plan in plans] == p["crossing_clear_m"]

    def test_backstops_scale_by_the_passer_budget(self):
        command = self._ground()
        p = command["actions"][0]["parameters"]
        budget = sum(max(1.0, c / 4.0) for c in p["crossing_clear_m"])
        assert p["hold_sec"] == round(_DERIVED_GEOMETRY.hold_backstop_sec * budget, 1)
        assert command["expected_resolution_time_sec"] == round(
            _DERIVED_GEOMETRY.resolution_backstop_sec * budget, 1
        )
        waits = [a["parameters"]["duration_sec"] for a in command["actions"][1:]]
        assert waits == [round(_DERIVED_GEOMETRY.wait_backstop_sec * budget, 1)] * 2
        assert p["hold_sec"] > 2 * _DERIVED_GEOMETRY.hold_backstop_sec
