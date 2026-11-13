"""Change 1 of the v4 refusal-feedback build: offer M2 only strategies M3 can ground.

`groundable_strategies` is the single source of truth for which strategy
tokens the M2 prompt may offer on a scene; the grounder's `junction_clear`
branch reads the same predicate (`junction_clear_declared`), so the anti-drift
tests below pin that the two agree on the recorded S1b geometry and on the IB10
composite geometry (the `test_dynamic_grounding` fixture; no recorded IB10
bundle overlay carries `junction_recede_offset_m`).
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from reasoning.rag.command_grounder import (
    ground_reasoner_result,
    groundable_strategies,
    junction_clear_declared,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerRequest,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.prompt_builder import build_prompt_payload

REPO = Path(__file__).resolve().parents[2]
S1B_OVERLAY = REPO / "config/overlays/v4_s1b_pc_shadow/orch_seed1.yaml"
S1B_GROUNDING = REPO / "config/grounding/s1b_dynamic_shield_escort.yaml"
RECORDED = REPO / "tests/unit/data/refusal_feedback/s1b_recorded_requests.jsonl"
ALL_STRATEGIES = (
    "yield", "reroute", "convoy", "priority_override", "temporary_wait", "reverse",
    "junction_clear",
)
# IB10 composite geometry (orchestrator.yaml header, prereg-v2 step 6/7b).
IB10_GEOMETRY: dict[str, Any] = {
    "corridor": {
        "axis": "x", "center_m": 0.0, "half_length_m": 0.6,
        "aisle_half_width_m": 0.6, "occluder_height_m": 0.0,
    },
    "arms": {
        "robot_1": {"axis": "x", "side": -1},
        "robot_2": {"axis": "x", "side": 1},
        "robot_3": {"axis": "y", "side": -1},
        "robot_4": {"axis": "y", "side": 1},
    },
    "junction_recede_offset_m": 1.2,
    "junction_backup_clearance_m": 1.1,
    "junction_recede_stagger_m": 0.2,
    "tracked_extent_m": 1.75,
}
JC_LINE = (
    '  - "junction_clear": multi-robot junction recovery: some robots first back out, '
    "one inside robot yields, then an ordered crossing"
)
JC_GRAMMAR_LINE = '- strategy "junction_clear": at least one "reverse" or "yield" leg'


def _s1b_geometry() -> SceneGeometry:
    return SceneGeometry(**yaml.safe_load(S1B_OVERLAY.read_text())["scenario_geometry"])


def _s1b_params() -> GroundingParams:
    return GroundingParams(**yaml.safe_load(S1B_GROUNDING.read_text())["grounding"])


def _derived() -> GroundingParams:
    return GroundingParams(mode="derived")


def _recorded() -> list[dict[str, Any]]:
    return [json.loads(line) for line in RECORDED.read_text().splitlines()]


def _ib10_snapshot() -> SnapshotFrame:
    poses = {
        "robot_1": (-0.2192, -0.0014, 0.0),
        "robot_2": (0.33, 0.0158, math.pi),
        "robot_3": (-0.0208, -0.2583, math.pi / 2),
        "robot_4": (0.0045, 0.2773, -math.pi / 2),
    }
    return SnapshotFrame(
        stamp=10.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=t, status="STOPPED")
            for rid, (x, y, t) in poses.items()
        ],
    )


def _junction_clear(involved: list[str]) -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=involved,
        root_cause="r", strategy="junction_clear", justification="j",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


def _request(**update: Any) -> ReasonerRequest:
    return ReasonerRequest.model_validate({**_recorded()[0]["request"], **update})


class TestGroundableStrategies:
    def test_junction_clear_dropped_on_recorded_s1b_geometry(self):
        assert groundable_strategies(_s1b_geometry(), _s1b_params()) == ALL_STRATEGIES[:-1]

    def test_junction_clear_kept_on_ib10_composite_geometry(self):
        assert groundable_strategies(SceneGeometry(**IB10_GEOMETRY), _derived()) == ALL_STRATEGIES

    def test_junction_clear_dropped_in_legacy_mode(self):
        params = GroundingParams(mode="legacy")
        assert "junction_clear" not in groundable_strategies(SceneGeometry(**IB10_GEOMETRY), params)

    def test_junction_clear_dropped_without_geometry(self):
        assert "junction_clear" not in groundable_strategies(None, _derived())

    def test_junction_clear_dropped_without_recede_offset(self):
        geometry = SceneGeometry(**{
            k: v for k, v in IB10_GEOMETRY.items()
            if k not in ("junction_recede_offset_m", "junction_recede_stagger_m")
        })
        assert not junction_clear_declared(geometry)

    def test_junction_clear_dropped_without_cross_axis_arm(self):
        arms = {"robot_1": {"axis": "x", "side": -1}, "robot_2": {"axis": "x", "side": 1}}
        assert not junction_clear_declared(SceneGeometry(**{**IB10_GEOMETRY, "arms": arms}))


class TestGrounderAgreesWithOfferedSet:
    def test_undeclared_geometry_grounds_junction_clear_through_fallback(self):
        geometry = SceneGeometry(**{**IB10_GEOMETRY, "junction_recede_offset_m": None,
                                    "junction_recede_stagger_m": None})
        command = ground_reasoner_result(
            _junction_clear(["robot_1", "robot_2", "robot_3", "robot_4"]),
            geometry=geometry, snapshot=_ib10_snapshot(), params=_derived(),
            yield_feasibility_mode="swap",
        )
        assert "junction_clear=fallback:no_candidates" in command["degradations"]

    def test_declared_geometry_grounds_junction_clear_recede_phase(self):
        command = ground_reasoner_result(
            _junction_clear(["robot_1", "robot_2", "robot_3", "robot_4"]),
            geometry=SceneGeometry(**IB10_GEOMETRY), snapshot=_ib10_snapshot(),
            params=_derived(), yield_feasibility_mode="swap",
        )
        assert "junction_clear=recede" in command["degradations"]


class TestOfferedStrategiesRequestField:
    def test_unknown_strategy_rejected(self):
        with pytest.raises(ValidationError):
            _request(offered_strategies=("yield", "teleport"))

    def test_none_token_rejected(self):
        with pytest.raises(ValidationError):
            _request(offered_strategies=("none", "yield"))

    def test_empty_offer_rejected(self):
        with pytest.raises(ValidationError):
            _request(offered_strategies=())


class TestOfferedStrategiesPrompt:
    def test_recorded_prompts_byte_identical_when_unset(self):
        for row in _recorded():
            request = ReasonerRequest.model_validate(row["request"])
            user = build_prompt_payload(request).user_prompt
            assert hashlib.sha256(user.encode()).hexdigest() == row["user_sha256"]

    def test_full_offer_renders_byte_identical_prompt(self):
        base = build_prompt_payload(_request()).user_prompt
        offered = build_prompt_payload(_request(offered_strategies=ALL_STRATEGIES)).user_prompt
        assert offered == base

    def test_junction_clear_gloss_absent_when_not_offered(self):
        user = build_prompt_payload(
            _request(offered_strategies=ALL_STRATEGIES[:-1])
        ).user_prompt
        assert JC_LINE not in user

    def test_junction_clear_plan_rule_absent_when_not_offered(self):
        user = build_prompt_payload(
            _request(offered_strategies=ALL_STRATEGIES[:-1])
        ).user_prompt
        assert JC_GRAMMAR_LINE not in user

    def test_no_junction_clear_token_when_not_offered(self):
        user = build_prompt_payload(
            _request(offered_strategies=ALL_STRATEGIES[:-1])
        ).user_prompt
        assert "junction_clear" not in user

    def test_only_offered_lines_removed(self):
        base = build_prompt_payload(_request()).user_prompt
        user = build_prompt_payload(
            _request(offered_strategies=ALL_STRATEGIES[:-1])
        ).user_prompt
        assert user == base.replace(JC_LINE + "\n", "").replace(JC_GRAMMAR_LINE + "\n", "")

    def test_v2_request_ignores_offer(self):
        base = _request(prompt_version=2)
        offered = _request(prompt_version=2, offered_strategies=ALL_STRATEGIES[:-1])
        assert build_prompt_payload(offered).user_prompt == build_prompt_payload(base).user_prompt
