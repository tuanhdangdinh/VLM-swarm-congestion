"""Tests for the B2 priority pair `priority_urgent_r1` / `priority_urgent_r2`.

The pair inherits every geometry constraint from the validated T1
`head_on_asymmetric_wopen_eopen_o0` scene; these tests pin that inheritance,
the pair's label-only difference, Arm B's label blindness, the M3 priority
route, and that urgency reaches the prompt through the task label alone.
"""
from __future__ import annotations

import difflib
import itertools
import json
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
from reasoning.vlm.output_parser import parse_decision_text
from reasoning.vlm.prompt_builder import build_prompt_payload

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = REPO_ROOT / "isaac/config/scenarios"
R1_PATH = SCENARIOS / "priority_urgent_r1.yaml"
R2_PATH = SCENARIOS / "priority_urgent_r2.yaml"
T1_PATH = SCENARIOS / "family/head_on_asymmetric_wopen_eopen_o0.yaml"
MAPS_DIR = REPO_ROOT / "ros2_ws/src/swarm_simulation/maps"
ORCHESTRATOR_YAML = REPO_ROOT / "ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml"
OVERRIDE_MOCK = REPO_ROOT / "config/mock_decisions/priority_urgent_override_once.json"
URGENT, ROUTINE = "urgent_order_delivery", "routine_order_delivery"
MEMBERS = {"r1": ("robot_1", "robot_2"), "r2": ("robot_2", "robot_1")}  # urgent, routine

# The T2b standoff grid (separation x shift), both robots stopped facing.
STANDOFF_GRID = list(itertools.product((0.24, 0.46, 0.70), (-0.2, -0.1, 0.0, 0.1, 0.2)))


def _path(member: str) -> Path:
    return R1_PATH if member == "r1" else R2_PATH


def _scenario(member: str):
    return load_scenario(_path(member))


def _geometry() -> SceneGeometry:
    # As shipped: the corridor is the T1 barrier (0.55 x 2.0 at x = 0).
    return SceneGeometry(**yaml.safe_load(ORCHESTRATOR_YAML.read_text())["scenario_geometry"])


def _tasks(member: str) -> dict[str, TaskAssignment]:
    urgent, routine = MEMBERS[member]
    goals = {"robot_1": (2.5, 0.0), "robot_2": (-2.5, 0.0)}
    return {
        urgent: TaskAssignment(task=URGENT, goal=goals[urgent], priority=1),
        routine: TaskAssignment(task=ROUTINE, goal=goals[routine]),
    }


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
        request_id="req-b2", decision=decision, raw_text="{}",
        diagnostics=ReasonerDiagnostics(
            request_id="req-b2", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _yield_decision(yielder: str) -> CongestionDecision:
    return CongestionDecision(
        congestion_detected=True, type="deadlock", involved_robots=["robot_1", "robot_2"],
        root_cause="head-on", strategy="yield", yield_robot=yielder, justification="j",
    )


class TestPair:
    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_member_loads_as_a_head_on_with_a_priority_oracle(self, member):
        scenario = _scenario(member)
        urgent, routine = MEMBERS[member]
        assert scenario.name == f"priority_urgent_{member}"
        assert scenario.family == "head_on"
        oracle = scenario.oracle
        assert isinstance(oracle, PriorityOracleConfig)
        assert (oracle.urgent_robot, oracle.correct_yielder, oracle.correct_first_passer) == (
            urgent, routine, urgent
        )
        assert oracle.classical_yielder == "robot_2"
        tasks = {r.robot_id: r.initial_task for r in scenario.robots}
        assert tasks == {urgent: URGENT, routine: ROUTINE}

    def test_arm_b_disagrees_with_urgency_in_exactly_one_member(self):
        contrasts = {m: _scenario(m).oracle.contrasts_classical for m in MEMBERS}
        assert contrasts == {"r1": False, "r2": True}

    def test_members_differ_only_in_name_labels_and_oracle(self):
        r1, r2 = (yaml.safe_load(p.read_text()) for p in (R1_PATH, R2_PATH))
        for data in (r1, r2):
            data.pop("name"), data.pop("oracle")
            for robot in data["robots"]:
                robot.pop("initial_task")
        assert r1 == r2

    def test_text_diff_is_confined_to_name_robots_and_oracle(self):
        def block_of(lines: list[str], index: int) -> str:
            for line in reversed(lines[: index + 1]):
                if line and not line.startswith((" ", "#")):
                    return line.split(":")[0]
            return ""

        a = R1_PATH.read_text().splitlines()
        b = R2_PATH.read_text().splitlines()
        touched, changed = set(), []
        matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            touched |= {block_of(a, i) for i in range(i1, max(i2, i1 + 1))}
            touched |= {block_of(b, j) for j in range(j1, max(j2, j1 + 1))}
            changed += a[i1:i2]
        assert touched == {"name", "robots", "oracle"}
        robot_lines = [line for line in changed if "initial_task" in line]
        assert len(robot_lines) == 2

    def test_labels_share_their_form_and_differ_in_one_token(self):
        assert URGENT.split("_")[1:] == ROUTINE.split("_")[1:]
        assert URGENT.split("_")[0] != ROUTINE.split("_")[0]


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
            grid(f"priority_urgent_{member}"), grid("head_on_asymmetric_wopen_eopen_o0")
        )

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_duration_covers_the_makespan(self, member):
        assert 120.0 + 60.0 <= _scenario(member).duration_sec == 200.0


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


class TestGroundedManeuvers:
    # Design table (derived, L 2.0): standoff -> (backup, escort) per yielder.
    TABLE = {
        (-0.12, 0.12): {"robot_1": (1.669, 2.559), "robot_2": (1.669, 2.559)},
        (-0.25, 0.05): {"robot_1": (1.539, 2.489), "robot_2": (1.739, 2.689)},
        (0.05, 0.30): {"robot_1": (1.839, 2.739), "robot_2": (1.489, 2.389)},
    }

    @pytest.mark.parametrize("standoff", sorted(TABLE))
    @pytest.mark.parametrize("yielder", ["robot_1", "robot_2"])
    def test_both_yields_ground_the_design_distances(self, standoff, yielder):
        frame = _frame("r2", *standoff)
        command = ground_reasoner_result(
            _result(_yield_decision(yielder)), snapshot=frame, geometry=_geometry(),
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
        )
        action = command["actions"][0]
        assert (action["robot_id"], action["action"]) == (yielder, "yield")
        backup, escort = self.TABLE[standoff][yielder]
        assert action["parameters"]["backup_distance_m"] == pytest.approx(backup, abs=1e-3)
        assert action["parameters"]["passer_escort_distance_m"] == pytest.approx(
            escort, abs=1e-3
        )
        passer_x = standoff[0] if yielder == "robot_2" else standoff[1]
        end = passer_x + (escort if yielder == "robot_2" else -escort)
        assert abs(end) == pytest.approx(2.439, abs=1e-3)
        # The passer's goal (+-2.5) sits 0.061 m beyond its escort end.
        assert 2.5 - abs(end) == pytest.approx(0.061, abs=1e-3)


class TestPriorityRoute:
    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_override_mock_grounds_the_routine_robot_yielding(self, member):
        urgent, routine = MEMBERS[member]
        first = json.loads(OVERRIDE_MOCK.read_text())[0]
        decision = parse_decision_text(json.dumps(first))
        assert decision.strategy == "priority_override" and decision.yield_robot is None
        command = ground_reasoner_result(
            _result(decision), snapshot=_frame(member), geometry=_geometry(),
            params=load_grounding_params(REPO_ROOT / "config/rag.yaml"),
            priorities=_registry_priorities(_tasks(member)),
        )
        action = command["actions"][0]
        assert (action["robot_id"], action["action"]) == (routine, "yield")
        assert action["parameters"]["passer_robot_id"] == urgent
        assert command["degradations"][-1] == "strategy=aliased:priority_override"

    def test_override_mock_clears_after_one_decision(self):
        _first, *rest = json.loads(OVERRIDE_MOCK.read_text())
        assert [parse_decision_text(json.dumps(d)).strategy for d in rest] == ["none"]

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_registry_priority_names_the_urgent_robot(self, member):
        assert _registry_priorities(_tasks(member)) == {MEMBERS[member][0]: 1}


class TestPromptChannel:
    def _prompt(self, member: str) -> str:
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
        request = build_reasoner_request("req-b2", attached, "/tmp/req-b2.png")
        assert request.prompt_version == CURRENT_PROMPT_VERSION == 2
        return build_prompt_payload(request).user_prompt

    @pytest.mark.parametrize("member", sorted(MEMBERS))
    def test_labels_render_as_task_fields(self, member):
        urgent, routine = MEMBERS[member]
        prompt = self._prompt(member)
        assert f"task={URGENT}" in prompt and f"task={ROUTINE}" in prompt
        urgent_line = next(line for line in prompt.splitlines() if f"task={URGENT}" in line)
        assert urgent in urgent_line

    def test_members_prompts_differ_only_by_the_swapped_labels(self):
        r2 = self._prompt("r2")
        swapped = r2.replace(URGENT, "\0").replace(ROUTINE, URGENT).replace("\0", ROUTINE)
        assert swapped == self._prompt("r1")


class TestM5Settings:
    def test_goal_table_lists_the_pair(self):
        table = ORCHESTRATOR_YAML.read_text()
        assert "priority_urgent_r1 / priority_urgent_r2 (B2 pair" in table
        assert "task: urgent_order_delivery, priority: 1" in table.replace("\n#     ", " ")

    def test_shipped_config_declares_no_priority(self):
        config = yaml.safe_load(ORCHESTRATOR_YAML.read_text())
        assert all("priority" not in spec for spec in config["initial_tasks"].values())
