"""Tests for the B2-visual pair `priority_visual_r1` / `priority_visual_r2`.

Byte-identical to v1's `priority_urgent_r1`/`_r2` pair except `name`, which
robot's `robots[].loaded` is true, and the oracle block (prereg-v2 design
docs/superpowers/specs/2026-09-30-prereg-v2-design.md, "(c) B2-visual
urgency pair"). The pair carries urgency ONLY visually: both robots share
one task label, neither carries a registry `priority`, and these tests pin
that no text channel leaks urgency -- the grep-level pin style of B1's
aperture-absence test (`tests/unit/test_bottleneck_merge_scenario.py`,
`TestTextChannels`). The load prop's own mounting geometry is pinned,
without a simulator, in `tests/unit/test_load_prop_asset.py`.
"""
from __future__ import annotations

import difflib
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm_orchestrator.models import RobotView, SceneSnapshot, TaskAssignment
from swarm_orchestrator.models import registry_priorities as _registry_priorities
from swarm_orchestrator.reasoning_pipeline import (
    attach_registry_assignments,
    build_reasoner_request,
)

from isaac.scripts.generate_warehouse_map import load_scenario
from isaac.vgu_sim.config import PriorityOracleConfig
from reasoning.baselines.classical_reasoner import load_classical_params, resolve_classical
from reasoning.rag.command_grounder import ground_reasoner_result
from reasoning.rag.maneuver_geometry import load_grounding_params
from reasoning.rag.scene_geometry import SceneGeometry
from reasoning.vlm.models import (
    CURRENT_PROMPT_VERSION,
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RobotStateInput,
    SnapshotFrame,
)
from reasoning.vlm.prompt_builder import build_prompt_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
R1_PATH = SCENARIOS / "priority_visual_r1.yaml"
R2_PATH = SCENARIOS / "priority_visual_r2.yaml"
T1_PATH = SCENARIOS / "family/head_on_asymmetric_wopen_eopen_o0.yaml"
V1_PAIR_PATH = SCENARIOS / "priority_urgent_r1.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
MOCKS = REPO_ROOT / "config/mock_decisions"
NEUTRAL_TASK = "cross_narrow_aisle"
MEMBERS = {"r1": ("robot_1", "robot_2"), "r2": ("robot_2", "robot_1")}  # loaded, empty
# Terms that would leak urgency through any text channel (B1's
# aperture-absence pin, generalized to this pair's vocabulary). "priority"
# and "empty" are deliberately excluded: both appear in the fixed v2
# template regardless of scene (`priority_override`'s strategy-enum listing,
# and a field-rendering rule's "empty when ..." instruction), verified by
# rendering this pair's own prompt and diffing against the raw template
# text -- a real leak would be a NEW occurrence of one of the remaining
# terms, which the fixed template contains none of.
FORBIDDEN_TERMS = ("urgent", "load", "loaded", "pallet", "cargo", "payload")

STANDOFF_GRID = list(itertools.product((0.24, 0.46, 0.70), (-0.2, -0.1, 0.0, 0.1, 0.2)))


def _path(member: str) -> Path:
    return R1_PATH if member == "r1" else R2_PATH


def _scenario(member: str):
    return load_scenario(_path(member))


def _geometry() -> SceneGeometry:
    return SceneGeometry(**yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"])


def _tasks(member: str) -> dict[str, TaskAssignment]:
    goals = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}
    return {rid: TaskAssignment(task=NEUTRAL_TASK, goal=goals[rid]) for rid in goals}


def _frame(member: str, r1_x: float = -0.12, r2_x: float = 0.12) -> SnapshotFrame:
    tasks = _tasks(member)
    return SnapshotFrame(stamp=30.0, robots=[
        RobotStateInput(robot_id="robot_1", x=r1_x, y=0.0, theta=0.0, linear_velocity=0.0,
                        status="STOPPED", task=tasks["robot_1"].task,
                        goal=tasks["robot_1"].goal),
        RobotStateInput(robot_id="robot_2", x=r2_x, y=0.0, theta=math.pi, linear_velocity=0.0,
                        status="STOPPED", task=tasks["robot_2"].task,
                        goal=tasks["robot_2"].goal),
    ])


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-b2v", decision=decision, raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-b2v", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _override_decision() -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=["robot_1", "robot_2"],
        root_cause="head-on", strategy="priority_override", yield_robot=None,
        justification="j",
    )


class TestPair:
    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_member_loads_as_a_head_on_with_a_priority_oracle(self, member):
        scenario = _scenario(member)
        loaded, empty = MEMBERS[member]
        assert scenario.name == f"priority_visual_{member}"
        assert scenario.family == "head_on"
        oracle = scenario.oracle
        assert isinstance(oracle, PriorityOracleConfig)
        assert (oracle.urgent_robot, oracle.correct_yielder, oracle.correct_first_passer) == (
            loaded, empty, loaded
        )
        assert oracle.classical_yielder == "robot_2"

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_exactly_one_robot_is_loaded_and_it_is_the_urgent_robot(self, member):
        scenario = _scenario(member)
        loaded_ids = [r.robot_id for r in scenario.robots if r.loaded]
        assert loaded_ids == [scenario.oracle.urgent_robot]

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_both_robots_share_the_same_neutral_task_label(self, member):
        scenario = _scenario(member)
        tasks = {r.initial_task for r in scenario.robots}
        assert tasks == {NEUTRAL_TASK}

    def test_arm_b_disagrees_with_urgency_in_exactly_one_member(self):
        contrasts = {m: _scenario(m).oracle.contrasts_classical for m in MEMBERS}
        assert contrasts == {"r1": False, "r2": True}

    def test_members_differ_only_in_name_loaded_robot_and_oracle(self):
        r1, r2 = (yaml.safe_load(p.read_text()) for p in (R1_PATH, R2_PATH))
        for data in (r1, r2):
            data.pop("name"), data.pop("oracle")
            for robot in data["robots"]:
                robot.pop("loaded", None)
        assert r1 == r2

    def test_text_diff_is_confined_to_name_robots_and_oracle(self):
        def block_of(lines: list[str], index: int) -> str:
            for line in reversed(lines[: index + 1]):
                if line and not line.startswith((" ", "#")):
                    return line.split(":")[0]
            return ""

        a = R1_PATH.read_text().splitlines()
        b = R2_PATH.read_text().splitlines()
        touched = set()
        matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            touched |= {block_of(a, i) for i in range(i1, max(i2, i1 + 1))}
            touched |= {block_of(b, j) for j in range(j1, max(j2, j1 + 1))}
        assert touched == {"name", "robots", "oracle"}


class TestInheritedT1Geometry:
    """C1-C13 are inherited from the validated wopen_eopen geometry."""

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_geometry_is_wopen_eopen(self, member):
        t1, scene = load_scenario(T1_PATH), _scenario(member)

        def pose(s):
            return [(r.robot_id, r.spawn, r.goal) for r in s.robots]

        assert pose(scene) == pose(t1)
        assert scene.aisle_barrier == t1.aisle_barrier
        assert scene.static_obstacles == t1.static_obstacles == ()
        assert scene.expected_conflict == t1.expected_conflict

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_map_equals_the_t1_map(self, member):
        def grid(name):
            data = yaml.safe_load((MAPS_DIR / f"warehouse_map_{name}.yaml").read_text())
            return np.array(Image.open(MAPS_DIR / data["image"]))

        assert np.array_equal(
            grid(f"priority_visual_{member}"), grid("head_on_asymmetric_wopen_eopen_o0")
        )

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_duration_covers_the_makespan(self, member):
        assert 120.0 + 60.0 <= _scenario(member).duration_sec == 200.0

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_geometry_matches_v1_b2s_pair_too(self, member):
        # Same base geometry as v1's priority_urgent pair; only the urgency
        # channel differs.
        v1 = load_scenario(V1_PAIR_PATH)
        scene = _scenario(member)
        assert scene.aisle_barrier == v1.aisle_barrier
        assert [(r.robot_id, r.spawn, r.goal) for r in scene.robots] == [
            (r.robot_id, r.spawn, r.goal) for r in v1.robots
        ]


class TestArmB:
    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_label_blind_head_on_yield_by_robot_2_over_the_grid(self, member):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        for separation, shift in STANDOFF_GRID:
            frame = _frame(member, shift - separation / 2, shift + separation / 2)
            resolution = resolve_classical([frame], [], params)
            assert resolution.classification.scenario == "head_on", (separation, shift)
            assert resolution.decision.strategy == "yield"
            assert resolution.decision.yield_robot == "robot_2"

    def test_arm_b_answer_is_identical_in_both_members(self):
        params = load_classical_params(REPO_ROOT / "config/rag.yaml")
        answers = {
            m: resolve_classical([_frame(m)], [], params).decision.model_dump_json()
            for m in MEMBERS
        }
        assert answers["r1"] == answers["r2"]


class TestPriorityRoute:
    """No robot carries a registry priority, so `priority_override` cannot
    ground: M3's alias needs a UNIQUE registry max among the involved
    robots (reasoning/rag/command_grounder.py, `_ordered_yield_alias`); with
    every robot at the default 0 it ties, so the route degrades to
    `strategy=unsupported`, an asymmetry against v1 B2 where the override
    route is executable."""

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_registry_priorities_is_empty(self, member):
        assert _registry_priorities(_tasks(member)) == {}

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_priority_override_degrades_to_unsupported(self, member):
        command = ground_reasoner_result(
            _result(_override_decision()), snapshot=_frame(member), geometry=_geometry(),
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
            priorities=_registry_priorities(_tasks(member)),
        )
        assert command["degradations"][-1] == "strategy=unsupported:priority_override"

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_yield_once_mock_grounds_the_empty_robot_yielding(self, member):
        import json

        from reasoning.vlm.output_parser import parse_decision_text

        loaded, empty = MEMBERS[member]
        mock_path = MOCKS / f"priority_visual_{member}_yield_once.json"
        first = json.loads(mock_path.read_text())[0]
        decision = parse_decision_text(json.dumps(first))
        assert decision.strategy == "yield" and decision.yield_robot == empty
        command = ground_reasoner_result(
            _result(decision), snapshot=_frame(member), geometry=_geometry(),
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
        )
        action = command["actions"][0]
        assert (action["robot_id"], action["action"]) == (empty, "yield")

    def test_yield_once_mocks_clear_after_one_decision(self):
        import json

        from reasoning.vlm.output_parser import parse_decision_text

        for member in MEMBERS:
            mock_path = MOCKS / f"priority_visual_{member}_yield_once.json"
            _first, *rest = json.loads(mock_path.read_text())
            assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]


class TestNoTextUrgency:
    """The whole point of this pair: urgency reaches no text channel
    (B1's aperture-absence pin, docs/superpowers/specs/
    2026-09-29-unified-scene-design.md "Oracle-block conventions")."""

    def _prompt(self, member: str, order: str = "id_asc") -> str:
        tasks = _tasks(member)
        snapshot = SceneSnapshot(
            stamp=30.0,
            frame_id="overhead_camera",
            robots=[
                RobotView(robot_id=s.robot_id, x=s.x, y=s.y, theta=s.theta,
                          linear_velocity=0.0, status="STOPPED", stamp=30.0)
                for s in _frame(member).robots
            ],
        )
        attached = attach_registry_assignments(
            snapshot, lambda rid: tasks[rid].goal, lambda rid: tasks[rid].task
        )
        request = build_reasoner_request(
            "req-b2v", attached, "/tmp/req-b2v.png", robot_presentation_order=order
        )
        assert request.prompt_version == CURRENT_PROMPT_VERSION == 2
        return build_prompt_payload(request).user_prompt

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    @pytest.mark.parametrize("order", ["id_asc", "id_desc"])
    def test_rendered_prompt_names_no_urgency_term(self, member, order):
        text = self._prompt(member, order).lower()
        for term in FORBIDDEN_TERMS:
            assert term not in text, (member, order, term)

    def test_members_prompts_are_byte_identical(self):
        # Unlike v1's pair (whose task labels swap between members), nothing
        # in either member's prompt differs: both robots share one task
        # label and neither carries a rendered priority.
        assert self._prompt("r1") == self._prompt("r2")

    def test_both_presentation_orders_are_byte_identical_across_members(self):
        for order in ("id_asc", "id_desc"):
            assert self._prompt("r1", order) == self._prompt("r2", order)

    def test_goal_table_lists_the_pair(self):
        table = ORCHESTRATOR_YAML.read_text()
        assert "priority_visual_r1 / priority_visual_r2 (B2-visual pair" in table

    def test_shipped_config_declares_no_priority(self):
        config = yaml.safe_load(ORCHESTRATOR_YAML.read_text())
        assert all("priority" not in spec for spec in config["initial_tasks"].values())
