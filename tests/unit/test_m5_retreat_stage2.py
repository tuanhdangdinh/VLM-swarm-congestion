"""M5 wiring of derived grounding and stage-2 retreat selection (no rclpy)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    PipelineOutcome,
    RetreatStage2Record,
    RobotView,
    SceneSnapshot,
    TerminalStage,
)
from swarm_orchestrator.reasoning_pipeline import (
    GroundingParamsSource,
    InProcessPipeline,
    attach_registry_assignments,
    build_reasoner_request,
    load_grounding_source,
    write_decision_artifact,
)
from swarm_orchestrator.retreat_stage2 import (
    format_stage2_log,
    run_retreat_stage2,
    snapshot_frame_from_request,
)

from reasoning.rag.command_grounder import ground_reasoner_result, prepare_retreat_selection
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.scene_geometry import CorridorGeometry, SceneGeometry
from reasoning.vlm.backend_factory import build_retreat_choice_backend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    BackendResponse,
    CongestionDecision,
    ReasonerConfig,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RetreatChoiceResult,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.retreat_chooser import RetreatChooser

_DERIVED = GroundingParams(mode="derived")
_WEST_BLOCKER = StaticObstacleInput(
    obstacle_id="obstacle_1", x=-1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
)


def _geometry() -> SceneGeometry:
    # Mirrors scenario_geometry in swarm_orchestrator/config/orchestrator.yaml.
    return SceneGeometry(
        corridor=CorridorGeometry(
            axis="x", center_m=0.0, half_length_m=1.0, aisle_half_width_m=0.6, occluder_height_m=0.9
        )
    )


def _snapshot() -> SceneSnapshot:
    return SceneSnapshot(
        stamp=42.5,
        frame_id="overhead_camera",
        robots=[
            RobotView(robot_id="robot_1", x=-0.3, y=0.0, theta=0.0,
                      linear_velocity=0.0, status="STOPPED", stamp=42.5),
            RobotView(robot_id="robot_2", x=0.3, y=0.0, theta=math.pi,
                      linear_velocity=0.0, status="STALE", stamp=42.5),
        ],
    )


def _request():
    snapshot = attach_registry_assignments(
        _snapshot(),
        lambda rid: (2.5, 0.0) if rid == "robot_1" else (-2.5, 0.0),
        lambda _rid: "cross_narrow_aisle",
    )
    return build_reasoner_request("r1", snapshot, "/tmp/r1.png")


def _decision(strategy: str = "yield", **update) -> CongestionDecision:
    base = dict(
        congestion_detected=True, type="deadlock", involved_robots=["robot_1", "robot_2"],
        root_cause="head-on standoff", strategy=strategy, justification="x",
        yield_robot="robot_1" if strategy == "yield" else None,
    )
    base.update(update)
    return CongestionDecision(**base)


def _result(decision: CongestionDecision) -> ReasonerResult:
    diag = ReasonerDiagnostics(request_id="r1", backend_id="mock", attempts=1, parse_status="valid")
    return ReasonerResult(request_id="r1", decision=decision, raw_text="{}", diagnostics=diag)


class _FakeReasoner:
    def __init__(self, decision: CongestionDecision) -> None:
        self._result = _result(decision)

    def run(self, request):
        return self._result


class _FixedChooser:
    """Stage-2 caller answering one letter, recording what it was asked."""

    def __init__(self, letter: str, cause: str | None = None) -> None:
        self._letter = letter
        self._cause = cause
        self.requests = []

    def choose(self, request):
        self.requests.append(request)
        return RetreatChoiceResult(
            request_id=request.request_id,
            backend_id="fixed",
            choice=RetreatChoiceDecision(retreat_choice=self._letter, justification="j"),
            raw_text="{}",
            attempts=1,
            failure_cause=self._cause,
        )


class _RaisingChooser:
    def __init__(self) -> None:
        self.calls = 0

    def choose(self, request):
        self.calls += 1
        raise RuntimeError("stage-2 backend exploded")


def _pipeline(decision=None, params=_DERIVED, chooser=None, **kwargs) -> InProcessPipeline:
    return InProcessPipeline(
        reasoner=_FakeReasoner(decision or _decision()),
        ground_fn=ground_reasoner_result,
        scene_geometry=kwargs.pop("scene_geometry", _geometry()),
        grounding_params=params,
        retreat_chooser=chooser,
        **kwargs,
    )


def _yield_params(outcome: PipelineOutcome) -> dict:
    [action] = [a for a in outcome.grounded_command["actions"] if a["action"] == "yield"]
    return action["parameters"]


# ---- GroundFn receives the derived-mode arguments ----

class TestGroundFnArguments:
    def _record(self, seen):
        def _ground(result, robot_positions=None, geometry=None, **kwargs):
            seen.update(kwargs, robot_positions=robot_positions)
            return ground_reasoner_result(result, robot_positions, geometry, **kwargs)
        return _ground

    def test_snapshot_round_trips_from_the_analysed_scene(self):
        seen: dict = {}
        request = _request()
        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision()), ground_fn=self._record(seen),
            grounding_params=_DERIVED,
        )
        pipe.run(request)
        frame = seen["snapshot"]
        assert isinstance(frame, SnapshotFrame)
        assert frame == snapshot_frame_from_request(request)
        assert frame.stamp == _snapshot().stamp
        assert [(r.robot_id, r.x, r.y, r.theta) for r in frame.robots] == [
            (v.robot_id, v.x, v.y, v.theta) for v in _snapshot().robots
        ]
        # The registry goals the prompt saw ride along too.
        assert frame.find_robot("robot_1").goal == (2.5, 0.0)
        assert seen["robot_positions"] == {"robot_1": (-0.3, 0.0), "robot_2": (0.3, 0.0)}

    def test_params_and_choice_are_passed(self):
        seen: dict = {}
        chooser = _FixedChooser("B")
        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision()), ground_fn=self._record(seen),
            scene_geometry=_geometry(), grounding_params=_DERIVED, retreat_chooser=chooser,
        )
        pipe.run(_request())
        assert seen["params"] is _DERIVED
        assert seen["retreat_choice"].retreat_choice == "B"
        assert "crossing_order" not in seen

    def test_legacy_params_never_call_stage2(self):
        seen: dict = {}
        chooser = _FixedChooser("B")
        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision()), ground_fn=self._record(seen),
            grounding_params=GroundingParams(), retreat_chooser=chooser,
        )
        outcome = pipe.run(_request())
        assert chooser.requests == []
        assert seen["retreat_choice"] is None
        assert outcome.stage2 is None
        assert "degradations" not in outcome.grounded_command

    def test_no_params_grounds_legacy(self):
        outcome = _pipeline(params=None, chooser=_FixedChooser("B")).run(_request())
        assert outcome.stage2 is None
        assert "park_x_m" in _yield_params(outcome)


# ---- stage-2 outcomes flow through to the grounded command ----

class TestStage2Flow:
    def test_forced_letter_grounds_that_candidate(self):
        chooser = _FixedChooser("B")
        outcome = _pipeline(chooser=chooser).run(_request())
        assert outcome.terminal_stage is TerminalStage.OK
        selection = prepare_retreat_selection(
            snapshot_frame_from_request(_request()), "robot_1", ["robot_2"], _DERIVED,
            geometry=_geometry(),
        )
        [b] = [c for c in selection.candidates if c.label == "B"]
        params = _yield_params(outcome)
        assert params["retreat_choice"] == "B"
        assert (params["retreat_x_m"], params["retreat_y_m"]) == (round(b.x, 3), round(b.y, 3))
        assert params["pull_off_lateral_m"] == b.lateral_m
        assert outcome.grounded_command["degradations"] == []
        assert outcome.stage2.status == "answered"
        assert outcome.stage2.default_label == selection.candidates[0].label
        [asked] = chooser.requests
        assert [c.label for c in asked.candidates] == [c.label for c in selection.candidates]
        assert asked.image_path == "/tmp/r1.png"

    def test_mock_forced_letter_flows_through(self, monkeypatch):
        monkeypatch.setenv(
            "VGU_MOCK_RETREAT_CHOICE_FILE", "config/mock_decisions/retreat_choice_b.json"
        )
        backend = build_retreat_choice_backend("mock", MockBackend())
        chooser = RetreatChooser(backend, ReasonerConfig(backend_id="mock"))
        outcome = _pipeline(chooser=chooser).run(_request())
        assert _yield_params(outcome)["retreat_choice"] == "B"
        assert outcome.stage2.status == "answered"
        assert outcome.stage2.response["choice"]["retreat_choice"] == "B"

    def test_no_backend_skips_and_grounds_the_default(self):
        outcome = _pipeline(chooser=None).run(_request())
        assert outcome.stage2.status == "skipped"
        assert outcome.stage2.skip_reason == "no_backend"
        assert outcome.stage2.prompt is None
        assert _yield_params(outcome)["retreat_choice"] == outcome.stage2.default_label
        assert outcome.grounded_command["degradations"] == ["retreat=default:no_choice"]

    def test_disabled_skips_without_calling(self):
        chooser = _FixedChooser("B")
        outcome = _pipeline(chooser=chooser, stage2_enabled=False).run(_request())
        assert chooser.requests == []
        assert outcome.stage2.skip_reason == "disabled"
        assert outcome.grounded_command["degradations"] == ["retreat=default:no_choice"]

    def test_invalid_letter_is_tagged_invalid_label(self):
        outcome = _pipeline(chooser=_FixedChooser("D", cause="invalid_label")).run(_request())
        assert outcome.stage2.status == "degraded"
        assert outcome.stage2.failure_cause == "invalid_label"
        assert outcome.grounded_command["degradations"] == ["retreat=default:invalid_label"]

    def test_stage2_exception_never_blocks_the_cycle(self):
        chooser = _RaisingChooser()
        outcome = _pipeline(chooser=chooser).run(_request())
        assert chooser.calls == 1
        assert outcome.terminal_stage is TerminalStage.OK
        assert outcome.stage2.status == "degraded"
        assert "stage-2 backend exploded" in outcome.stage2.error
        assert outcome.grounded_command["degradations"] == ["retreat=default:no_choice"]

    def test_backend_failure_degrades_to_the_default(self):
        class _CapHit:
            def analyze(self, payload, config):
                raise RuntimeError("HTTP 429 exceeded its monthly spending cap")

        chooser = RetreatChooser(_CapHit(), ReasonerConfig(backend_id="gemini", max_attempts=2))
        outcome = _pipeline(chooser=chooser).run(_request())
        assert outcome.terminal_stage is TerminalStage.OK
        assert outcome.stage2.failure_cause == "backend_error"
        assert outcome.stage2.response["attempts"] == 2
        assert outcome.grounded_command["degradations"] == ["retreat=default:no_choice"]

    def test_refusal_degrades_to_the_default(self):
        class _Refuses:
            def analyze(self, payload, config):
                return BackendResponse(text="I'm sorry, I can't assist with that.",
                                       backend_id="openai")

        chooser = RetreatChooser(_Refuses(), ReasonerConfig(backend_id="openai", max_attempts=1))
        outcome = _pipeline(chooser=chooser).run(_request())
        assert outcome.stage2.failure_cause == "refusal"
        assert outcome.grounded_command["degradations"] == ["retreat=default:no_choice"]

    def test_non_yield_strategy_has_no_stage2(self):
        chooser = _FixedChooser("B")
        outcome = _pipeline(decision=_decision("temporary_wait"), chooser=chooser).run(_request())
        assert chooser.requests == []
        assert outcome.stage2 is None
        assert outcome.grounded_command["degradations"] == []

    def test_stage2_offers_the_gate_swapped_yielder(self):
        chooser = _FixedChooser("A")
        outcome = _pipeline(
            chooser=chooser, static_obstacles=(_WEST_BLOCKER,), yield_feasibility_mode="swap"
        ).run(_request())
        [asked] = chooser.requests
        [action] = [a for a in outcome.grounded_command["actions"] if a["action"] == "yield"]
        assert asked.yielder_id == action["robot_id"] == "robot_2"
        assert outcome.stage2.yielder_id == "robot_2"

    def test_record_is_logged_without_prompt_text(self):
        outcome = _pipeline(chooser=_FixedChooser("B")).run(_request())
        line = format_stage2_log("r1", outcome.stage2)
        assert line.startswith("stage2 request=r1 status=answered")
        assert "choice=B" in line
        assert "Retreat positions" not in line


class TestRunRetreatStage2:
    def test_refused_yield_is_skipped(self):
        frame = SnapshotFrame(stamp=1.0, robots=[])
        choice, record = run_retreat_stage2(
            _request(), _decision(involved_robots=["robot_1"]), frame, _DERIVED, _FixedChooser("A")
        )
        assert choice is None
        assert record.skip_reason == "yield_refused"

    def test_no_candidates_is_skipped(self):
        # robot_2 sits 1.0 m down robot_1's retreat path: clearing it by 1.7 m
        # needs a 2.7 m backup, outside the [0.5, 2.0] m band.
        request = build_reasoner_request(
            "r1",
            SceneSnapshot(
                stamp=1.0, frame_id="cam",
                robots=[
                    RobotView(robot_id="robot_1", x=0.0, y=0.0, theta=0.0,
                              linear_velocity=0.0, status="STOPPED", stamp=1.0),
                    RobotView(robot_id="robot_2", x=-1.0, y=0.0, theta=0.0,
                              linear_velocity=0.0, status="STOPPED", stamp=1.0),
                ],
            ),
            "/tmp/r1.png",
        )
        choice, record = run_retreat_stage2(
            request, _decision(), snapshot_frame_from_request(request), _DERIVED,
            _FixedChooser("A"),
        )
        assert choice is None
        assert record.skip_reason == "no_candidates"
        assert record.candidates == []


# ---- grounding params: loaded once, fail fast ----

class TestLoadGroundingSource:
    def test_missing_file_fails_fast(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="grounding params"):
            load_grounding_source(tmp_path / "absent.yaml")

    def test_unknown_key_fails_fast(self, tmp_path):
        path = tmp_path / "rag.yaml"
        path.write_text("grounding:\n  mode: derived\n  lateral: 0.4\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_grounding_source(path)

    def test_bad_mode_fails_fast(self, tmp_path):
        path = tmp_path / "rag.yaml"
        path.write_text("grounding:\n  mode: derivd\n", encoding="utf-8")
        with pytest.raises(ValidationError):
            load_grounding_source(path)

    def test_non_mapping_fails_fast(self, tmp_path):
        path = tmp_path / "rag.yaml"
        path.write_text("- grounding\n", encoding="utf-8")
        with pytest.raises(ValueError, match="mapping"):
            load_grounding_source(path)

    def test_missing_section_is_recorded_as_legacy_defaults(self, tmp_path):
        path = tmp_path / "rag.yaml"
        path.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
        source = load_grounding_source(path)
        assert source.section_present is False
        assert source.params == GroundingParams()

    def test_repo_config_loads(self):
        source = load_grounding_source(Path("config/rag.yaml"))
        assert source.section_present is True
        assert source.path == "config/rag.yaml"


# ---- decision artifact ----

def _source(mode: str = "derived") -> GroundingParamsSource:
    return GroundingParamsSource(
        path="config/rag.yaml", section_present=True, params=GroundingParams(mode=mode)
    )


class TestArtifact:
    def test_degradations_mode_and_stage2_are_recorded(self, tmp_path):
        outcome = _pipeline(chooser=None).run(_request())
        payload = json.loads(
            write_decision_artifact(
                tmp_path, outcome, request=_request(), grounding_source=_source()
            ).read_text()
        )
        assert payload["grounding_mode"] == "derived"
        assert payload["grounding_params_source"]["path"] == "config/rag.yaml"
        assert payload["grounding_params_source"]["params"]["mode"] == "derived"
        assert payload["grounding_degradations"] == ["retreat=default:no_choice"]
        assert payload["stage2"]["skip_reason"] == "no_backend"
        assert payload["stage2"]["candidates"][0]["label"] == payload["stage2"]["default_label"]

    def test_stage2_prompt_and_response_are_recorded_without_image_bytes(self, tmp_path):
        outcome = _pipeline(chooser=_FixedChooser("B")).run(_request())
        text = write_decision_artifact(
            tmp_path, outcome, request=_request(), grounding_source=_source()
        ).read_text()
        stage2 = json.loads(text)["stage2"]
        assert stage2["stage2_prompt_version"] == 1
        assert stage2["prompt"]["image_path"] == "/tmp/r1.png"
        assert len(stage2["prompt"]["user_sha256"]) == 64
        assert stage2["response"]["backend_id"] == "fixed"
        assert stage2["choice"] == {"retreat_choice": "B", "justification": "j"}
        assert "base64" not in text

    def test_legacy_outcome_records_null_derived_fields(self, tmp_path):
        outcome = _pipeline(params=GroundingParams()).run(_request())
        payload = json.loads(
            write_decision_artifact(tmp_path, outcome, grounding_source=_source("legacy"))
            .read_text()
        )
        assert payload["grounding_mode"] == "legacy"
        assert payload["grounding_degradations"] is None
        assert payload["stage2"] is None

    def test_absent_source_records_null_mode(self, tmp_path):
        outcome = _pipeline(params=None).run(_request())
        payload = json.loads(write_decision_artifact(tmp_path, outcome).read_text())
        assert payload["grounding_mode"] is None
        assert payload["grounding_params_source"] is None

    def test_stage2_record_survives_a_grounding_failure(self):
        def _raise(result, robot_positions=None, geometry=None, **_kwargs):
            raise ValueError("schema invalid")

        pipe = InProcessPipeline(
            reasoner=_FakeReasoner(_decision()), ground_fn=_raise, scene_geometry=_geometry(),
            grounding_params=_DERIVED, retreat_chooser=_FixedChooser("A"),
        )
        outcome = pipe.run(_request())
        assert outcome.terminal_stage is TerminalStage.GROUNDING
        assert isinstance(outcome.stage2, RetreatStage2Record)
        assert outcome.stage2.status == "answered"
