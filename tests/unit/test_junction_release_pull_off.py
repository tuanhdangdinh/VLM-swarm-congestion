"""prereg-v3 addendum A8 (i): lateral pull-off for the held receder's release.

`SceneGeometry.junction_release_pull_off_m` (default 0.0, off) makes every
recede candidate that sits on the release lead's exit lane sidestep off it
inside its release `yield` before the lead passes. With the field at its
default the phase plan must be byte-identical to the pre-change grounder:
the goldens in `data/junction_release/default_phase_plans.json` were written
by `_golden_plans` below on the untouched integration tip (19a1859) before
any edit.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from reasoning.rag.command_grounder import ground_junction_clear_phases
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import (
    ArmGeometry,
    CorridorGeometry,
    SceneGeometry,
    release_pull_off_lateral_m,
)
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)

_GOLDEN = Path(__file__).parent / "data" / "junction_release" / "default_phase_plans.json"

# IB10 four-way standoff, the `test_dispatch_order_source` fixture positions
# (chi ranks robot_4 before robot_3), plus its mirror (robot_3 farther out,
# so robot_3 leads). Headings face the junction, as at a formed jam.
_STANDOFF_R4_LEAD = {
    "robot_1": (-0.2192, -0.0014, 0.0),
    "robot_2": (0.33, 0.0158, math.pi),
    "robot_3": (-0.0208, -0.2583, math.pi / 2),
    "robot_4": (0.0045, 0.2773, -math.pi / 2),
}
_STANDOFF_R3_LEAD = {
    **_STANDOFF_R4_LEAD,
    "robot_3": (-0.0208, -0.2773, math.pi / 2),
    "robot_4": (0.0045, 0.2583, -math.pi / 2),
}
_ARMS = {
    "robot_1": ArmGeometry(axis="x", side=-1),
    "robot_2": ArmGeometry(axis="x", side=1),
    "robot_3": ArmGeometry(axis="y", side=-1),
    "robot_4": ArmGeometry(axis="y", side=1),
}


def _geometry(
    *, stagger_m: float | None = 0.2, j2: float | None = 1.1, **extra: Any
) -> SceneGeometry:
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    return SceneGeometry(
        corridor=corridor,
        arms=_ARMS,
        junction_recede_offset_m=1.2,
        junction_backup_clearance_m=j2,
        junction_recede_stagger_m=stagger_m,
        tracked_extent_m=1.75,
        **extra,
    )


def _frame(standoff: dict[str, tuple[float, float, float]]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta)
            for rid, (x, y, theta) in standoff.items()
        ],
    )


def _result() -> ReasonerResult:
    decision = CongestionDecision(
        congestion_detected=True,
        type="deadlock",
        involved_robots=list(_STANDOFF_R4_LEAD),
        root_cause="four-way standoff",
        strategy="junction_clear",
        justification="jam",
    )
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


_GOLDEN_CASES: dict[str, tuple[dict[str, tuple[float, float, float]], dict[str, Any]]] = {
    "r4_lead_stagger": (_STANDOFF_R4_LEAD, {}),
    "r3_lead_stagger": (_STANDOFF_R3_LEAD, {}),
    "r4_lead_no_stagger": (_STANDOFF_R4_LEAD, {"stagger_m": None}),
    "r4_lead_missing_j2": (_STANDOFF_R4_LEAD, {"j2": None}),
}


def _plan(standoff: dict[str, tuple[float, float, float]], **geometry_kwargs: Any) -> Any:
    return ground_junction_clear_phases(
        _result(),
        snapshot=_frame(standoff),
        params=GroundingParams(mode="derived"),
        geometry=_geometry(**geometry_kwargs),
    )


def _golden_plans(**extra: Any) -> dict[str, Any]:
    return {
        name: _plan(standoff, **{**kwargs, **extra}).model_dump(mode="json")
        for name, (standoff, kwargs) in _GOLDEN_CASES.items()
    }


_PULL_OFF = {"junction_release_pull_off_m": 0.33, "junction_release_pull_off_side": -1}


def _release_params(plan: Any) -> dict[str, dict[str, Any]]:
    release = plan.phases[-1]
    assert release.label == "release"
    return {a["robot_id"]: a["parameters"] for a in release.command["actions"]}


# ---- default off: byte-identical to the pre-change grounder ----


def test_default_geometry_phase_plans_match_pre_change_golden():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert json.dumps(_golden_plans(), sort_keys=True) == json.dumps(golden, sort_keys=True)


def test_explicit_zero_pull_off_phase_plans_match_pre_change_golden():
    golden = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    plans = _golden_plans(junction_release_pull_off_m=0.0, junction_release_pull_off_side=-1)
    assert json.dumps(plans, sort_keys=True) == json.dumps(golden, sort_keys=True)


# ---- enabled: who pulls off, which way, and the gates ----


def test_pull_off_held_receder_steps_left_when_robot_3_is_held():
    # robot_3 faces +y, so its left is -x: the declared world side -1.
    params = _release_params(_plan(_STANDOFF_R4_LEAD, **_PULL_OFF))
    assert params["robot_3"]["pull_off_lateral_m"] == 0.33
    assert params["robot_3"]["passer_reference_at_dispatch"] is True


def test_pull_off_held_receder_steps_right_when_robot_4_is_held():
    # robot_4 faces -y, so its left is +x: world -x is its right.
    params = _release_params(_plan(_STANDOFF_R3_LEAD, **_PULL_OFF))
    assert params["robot_4"]["pull_off_lateral_m"] == -0.33
    assert params["robot_4"]["passer_reference_at_dispatch"] is True


def test_pull_off_skips_the_yielder_on_the_crossing_axis():
    for standoff in (_STANDOFF_R4_LEAD, _STANDOFF_R3_LEAD):
        params = _release_params(_plan(standoff, **_PULL_OFF))
        assert "pull_off_lateral_m" not in params["robot_1"]
        assert "passer_reference_at_dispatch" not in params["robot_1"]


def test_pull_off_keeps_the_lead_unaddressed_and_its_clearance():
    plan = _plan(_STANDOFF_R4_LEAD, **_PULL_OFF)
    params = _release_params(plan)
    assert "robot_4" not in params
    # 1.2 + 1.0 + 0.45: the offset only widens the pass, so the lead's gate
    # (now measured from its pocket) is unchanged.
    assert params["robot_3"]["passer_clear_m"] == 2.65
    assert params["robot_1"]["passer_clear_m"] == 2.65
    assert plan.phases[-1].held_robot_ids == ("robot_3", "robot_1")


def test_pull_off_sizes_the_receder_crossing_gate_as_the_hypotenuse():
    params = _release_params(_plan(_STANDOFF_R4_LEAD, **_PULL_OFF))
    # Along-axis 1.0 + 0.6 + 0.45 = 2.05, with a 0.33 m lateral leg.
    assert params["robot_1"]["crossing_order"] == ["robot_4", "robot_3"]
    assert params["robot_1"]["crossing_clear_m"] == [2.65, round(math.hypot(2.05, 0.33), 3)]
    assert params["robot_1"]["crossing_clear_m"][1] == 2.076


def test_pull_off_leaves_recede_cross_and_fallback_unchanged():
    for standoff in (_STANDOFF_R4_LEAD, _STANDOFF_R3_LEAD):
        off = _plan(standoff)
        on = _plan(standoff, **_PULL_OFF)
        assert on.phases[:-1] == off.phases[:-1]
        assert on.fallback_command == off.fallback_command
        assert on.fallback_held_robot_ids == off.fallback_held_robot_ids
        assert on.phases[-1].command["degradations"] == off.phases[-1].command["degradations"]


def test_pull_off_release_differs_from_default_only_in_the_added_keys():
    off = _release_params(_plan(_STANDOFF_R4_LEAD))
    on = _release_params(_plan(_STANDOFF_R4_LEAD, **_PULL_OFF))
    added = {"pull_off_lateral_m", "passer_reference_at_dispatch"}
    assert {k: v for k, v in on["robot_3"].items() if k not in added} == off["robot_3"]
    assert {k: v for k, v in on["robot_1"].items() if k != "crossing_clear_m"} == {
        k: v for k, v in off["robot_1"].items() if k != "crossing_clear_m"
    }


# ---- release_pull_off_lateral_m: lane membership and sign convention ----


def test_release_pull_off_none_when_off():
    assert release_pull_off_lateral_m(_geometry(), "robot_3", "robot_4") is None


def test_release_pull_off_none_for_the_lead_itself():
    assert release_pull_off_lateral_m(_geometry(**_PULL_OFF), "robot_4", "robot_4") is None


def test_release_pull_off_none_for_a_robot_off_the_lead_axis():
    assert release_pull_off_lateral_m(_geometry(**_PULL_OFF), "robot_1", "robot_4") is None


def test_release_pull_off_none_for_an_undeclared_robot():
    assert release_pull_off_lateral_m(_geometry(**_PULL_OFF), "robot_9", "robot_4") is None


def test_release_pull_off_applies_on_the_lead_own_arm():
    # A shallower receder stacked on the lead's own arm sits on its inward lane.
    geometry = _geometry(**_PULL_OFF).model_copy(
        update={"arms": {**_ARMS, "robot_5": ArmGeometry(axis="y", side=1)}}
    )
    assert release_pull_off_lateral_m(geometry, "robot_5", "robot_4") == -0.33


def test_release_pull_off_side_plus_one_flips_both_signs():
    geometry = _geometry(junction_release_pull_off_m=0.33, junction_release_pull_off_side=1)
    assert release_pull_off_lateral_m(geometry, "robot_3", "robot_4") == -0.33
    assert release_pull_off_lateral_m(geometry, "robot_4", "robot_3") == 0.33


def test_release_pull_off_x_axis_arm_uses_y_as_lateral_axis():
    # robot_1 (x arm, side -1) faces +x, so its left is +y; robot_2 faces -x.
    geometry = _geometry(junction_release_pull_off_m=0.33, junction_release_pull_off_side=1)
    assert release_pull_off_lateral_m(geometry, "robot_1", "robot_2") == 0.33
    assert release_pull_off_lateral_m(geometry, "robot_2", "robot_1") == -0.33


# ---- SceneGeometry validation ----


def test_pull_off_requires_a_declared_side():
    with pytest.raises(ValidationError, match="junction_release_pull_off_side"):
        _geometry(junction_release_pull_off_m=0.33)


def test_pull_off_requires_a_recede_pocket():
    corridor = CorridorGeometry(
        axis="x", center_m=0.0, half_length_m=0.6, aisle_half_width_m=0.6, occluder_height_m=0.0
    )
    with pytest.raises(ValidationError, match="junction_recede_offset_m"):
        SceneGeometry(corridor=corridor, arms=_ARMS, **_PULL_OFF)


def test_pull_off_rejects_a_step_past_the_wall_safe_bound():
    # 0.6 aisle half-width - 0.09 robot half-width - 0.15 wall margin = 0.36.
    _geometry(junction_release_pull_off_m=0.36, junction_release_pull_off_side=-1)
    with pytest.raises(ValidationError, match="wall-safe"):
        _geometry(junction_release_pull_off_m=0.37, junction_release_pull_off_side=-1)


def test_pull_off_rejects_a_negative_step():
    with pytest.raises(ValidationError):
        _geometry(junction_release_pull_off_m=-0.1, junction_release_pull_off_side=-1)


def test_side_without_pull_off_is_inert():
    assert _geometry(junction_release_pull_off_side=1).junction_release_pull_off_m == 0.0
