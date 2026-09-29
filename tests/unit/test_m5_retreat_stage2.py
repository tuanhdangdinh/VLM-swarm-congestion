"""M5 wiring of derived grounding and stage-2 retreat selection (no rclpy)."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml
from pydantic import ValidationError
from swarm_orchestrator.models import (
    PipelineOutcome,
    RetreatStage2Record,
    RobotView,
    SceneSnapshot,
    TerminalStage,
    load_config,
)
from swarm_orchestrator.reasoning_pipeline import (
    GroundingParamsSource,
    InProcessPipeline,
    apply_aisle_x_band_override,
    apply_aisle_y_band_override,
    attach_registry_assignments,
    build_reasoner_request,
    load_grounding_source,
    write_decision_artifact,
)
from swarm_orchestrator.retreat_stage2 import (
    assign_letters,
    derive_letter_seed,
    derive_listing_seed,
    draw_listing_order,
    format_stage2_log,
    run_retreat_stage2,
    snapshot_frame_from_request,
)
from swarm_orchestrator.stage2_marks import CandidateMarker
from swarm_perception.models import CalibrationArtifact

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
    RetreatCandidateOption,
    RetreatChoiceDecision,
    RetreatChoiceRequest,
    RetreatChoiceResult,
    RobotStateInput,
    SnapshotFrame,
    StaticObstacleInput,
)
from reasoning.vlm.retreat_chooser import RetreatChooser
from reasoning.vlm.stage2_prompt import build_stage2_prompt_payload

_DERIVED = GroundingParams(mode="derived")
_ORCHESTRATOR_YAML = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")
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
        # The script forces the *shown* letter B; which candidate that is
        # depends on the letter draw, so read it off the assignment.
        shown_b = outcome.stage2.letter_assignment["B"]
        params = _yield_params(outcome)
        assert params["retreat_choice"] == shown_b["candidate_label"]
        assert (params["retreat_x_m"], params["retreat_y_m"]) == (
            round(shown_b["x"], 3), round(shown_b["y"], 3)
        )
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


class TestAisleXBandOverride:
    def test_no_band_keeps_the_loaded_source(self):
        source = _source()
        assert apply_aisle_x_band_override(source, None) is source

    def test_band_replaces_only_the_x_band_and_is_recorded(self):
        source = apply_aisle_y_band_override(_source(), (-0.55, 1.0))
        overridden = apply_aisle_x_band_override(source, (-0.46, 0.46))
        assert overridden.params.aisle_x_band_m == (-0.46, 0.46)
        assert overridden.aisle_x_band_override_m == (-0.46, 0.46)
        assert overridden.params.aisle_y_band_m == (-0.55, 1.0)
        assert overridden.aisle_y_band_override_m == (-0.55, 1.0)

    def test_unset_x_band_stays_out_of_the_artifact_dump(self):
        dumped = _source().model_dump(mode="json")
        assert "aisle_x_band_override_m" not in dumped
        assert "aisle_x_band_m" not in dumped["params"]

    def test_set_x_band_is_in_the_artifact_dump(self):
        dumped = apply_aisle_x_band_override(_source(), (-0.46, 0.46)).model_dump(mode="json")
        assert dumped["aisle_x_band_override_m"] == [-0.46, 0.46]
        assert dumped["params"]["aisle_x_band_m"] == [-0.46, 0.46]

    def test_inverted_band_fails_fast(self):
        with pytest.raises(ValidationError, match="aisle_x_band_m"):
            apply_aisle_x_band_override(_source(), (0.46, -0.46))


class TestAisleYBandOverride:
    def test_no_band_keeps_the_loaded_source(self):
        source = _source()
        assert apply_aisle_y_band_override(source, None) is source

    def test_band_replaces_only_the_aisle_band_and_is_recorded(self):
        source = _source()
        overridden = apply_aisle_y_band_override(source, (-0.55, 1.0))
        assert overridden.params.aisle_y_band_m == (-0.55, 1.0)
        assert overridden.aisle_y_band_override_m == (-0.55, 1.0)
        assert overridden.params.model_dump(exclude={"aisle_y_band_m"}) == (
            source.params.model_dump(exclude={"aisle_y_band_m"})
        )
        assert overridden.path == source.path

    def test_inverted_band_fails_fast(self):
        with pytest.raises(ValidationError, match="aisle_y_band_m"):
            apply_aisle_y_band_override(_source(), (1.0, -0.55))

    def test_band_turns_the_head_on_pair_into_three_candidates(self):
        frame = snapshot_frame_from_request(_request())
        default, wide = (
            prepare_retreat_selection(
                frame, "robot_1", ["robot_2"], source.params, geometry=_geometry()
            )
            for source in (_source(), apply_aisle_y_band_override(_source(), (-0.55, 1.0)))
        )
        assert len(default.candidates) == 2
        assert len(wide.candidates) == 3

    def test_band_is_recorded_in_the_artifact(self, tmp_path):
        outcome = _pipeline(chooser=None).run(_request())
        source = apply_aisle_y_band_override(_source(), (-0.55, 1.0))
        payload = json.loads(
            write_decision_artifact(
                tmp_path, outcome, request=_request(), grounding_source=source
            ).read_text()
        )
        recorded = payload["grounding_params_source"]
        assert recorded["aisle_y_band_override_m"] == [-0.55, 1.0]
        assert recorded["params"]["aisle_y_band_m"] == [-0.55, 1.0]

    def test_orchestrator_config_parses_the_band(self):
        raw = yaml.safe_load(_ORCHESTRATOR_YAML.read_text())
        config = load_config({**raw, "grounding_aisle_y_band_m": [-0.55, 1.0]})
        assert config.grounding_aisle_y_band_m == (-0.55, 1.0)

    def test_shipped_orchestrator_yaml_sets_no_band(self):
        # The band is per scenario: shipping one would change every scenario's k.
        raw = yaml.safe_load(_ORCHESTRATOR_YAML.read_text())
        assert "grounding_aisle_y_band_m" in raw
        assert load_config(raw).grounding_aisle_y_band_m is None


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
        assert stage2["stage2_prompt_version"] == 3
        assert stage2["prompt"]["image_path"] == "/tmp/r1.png"
        assert stage2["marks_drawn"] is False
        assert stage2["marks"]["reason"].startswith("marker_unavailable")
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


# ---- Set-of-mark letters drawn on the stage-1 frame ----

# Pixel -> world at 0.01 m/px for a 640 x 480 frame centred on the origin.
_SYNTHETIC_H = np.array([[0.01, 0.0, -3.2], [0.0, -0.01, 2.4], [0.0, 0.0, 1.0]])


def _marker() -> CandidateMarker:
    return CandidateMarker(
        CalibrationArtifact(
            intrinsics=np.eye(3), distortion=np.zeros(5), homography=_SYNTHETIC_H,
            image_size=(640, 480), source_id="synthetic", created_at=0.0,
        ),
        "synthetic.yaml",
    )


def _framed_request(tmp_path):
    frame = tmp_path / "r1.png"
    cv2.imwrite(str(frame), np.full((480, 640, 3), 128, dtype=np.uint8))
    snapshot = attach_registry_assignments(
        _snapshot(),
        lambda rid: (2.5, 0.0) if rid == "robot_1" else (-2.5, 0.0),
        lambda _rid: "cross_narrow_aisle",
    )
    return build_reasoner_request("r1", snapshot, str(frame))


class TestSetOfMark:
    def test_marked_image_and_prompt_reach_the_call(self, tmp_path):
        chooser = _FixedChooser("A")
        outcome = _pipeline(chooser=chooser, candidate_marker=_marker()).run(
            _framed_request(tmp_path)
        )
        [asked] = chooser.requests
        assert asked.marks_drawn is True
        assert asked.image_path == str(tmp_path / "r1_stage2.png")
        assert (tmp_path / "r1_stage2.png").is_file()
        stage2 = outcome.stage2
        assert stage2.marks_drawn is True
        assert stage2.prompt["image_path"] == str(tmp_path / "r1_stage2.png")
        assert "marked on the image" in stage2.prompt["user_prompt"]
        # Candidates sit at x=-1.79, y=+-0.36: pixel (141, 204) and (141, 276).
        pixels = {(m["u"], m["v"]) for m in stage2.marks["marks"]}
        assert pixels == {(141, 204), (141, 276)}

    def test_marks_follow_the_letters_shown(self, tmp_path):
        chooser = _FixedChooser("A")
        outcome = _pipeline(chooser=chooser, candidate_marker=_marker()).run(
            _framed_request(tmp_path)
        )
        [asked] = chooser.requests
        shown = {c.label: (c.x, c.y) for c in asked.candidates}
        drawn = {m["letter"]: (m["x"], m["y"]) for m in outcome.stage2.marks["marks"]}
        assert drawn.keys() == shown.keys()
        for letter, position in drawn.items():
            assert position == pytest.approx(shown[letter])

    def test_no_marker_sends_the_unmarked_frame(self, tmp_path):
        chooser = _FixedChooser("A")
        outcome = _pipeline(chooser=chooser).run(_framed_request(tmp_path))
        [asked] = chooser.requests
        assert asked.marks_drawn is False
        assert asked.image_path == str(tmp_path / "r1.png")
        assert outcome.stage2.marks_drawn is False
        assert "not drawn on the image" in outcome.stage2.prompt["user_prompt"]
        assert outcome.stage2.status == "answered"

    def test_unavailable_calibration_is_recorded_and_the_call_still_runs(self, tmp_path):
        chooser = _FixedChooser("A")
        marker = CandidateMarker.unavailable("calibration_unavailable: gone", "x.yaml")
        outcome = _pipeline(chooser=chooser, candidate_marker=marker).run(
            _framed_request(tmp_path)
        )
        assert len(chooser.requests) == 1
        assert outcome.stage2.marks_drawn is False
        assert outcome.stage2.marks["reason"] == "calibration_unavailable: gone"
        assert outcome.stage2.status == "answered"

    def test_a_raising_marker_never_costs_the_call(self, tmp_path):
        class _Raising:
            def render(self, *args):
                raise RuntimeError("cv2 exploded")

        chooser = _FixedChooser("A")
        outcome = _pipeline(chooser=chooser, candidate_marker=_Raising()).run(
            _framed_request(tmp_path)
        )
        assert len(chooser.requests) == 1
        assert outcome.stage2.status == "answered"
        assert outcome.stage2.marks_drawn is False
        assert "cv2 exploded" in outcome.stage2.marks["reason"]

    def test_skipped_stage2_draws_nothing(self, tmp_path):
        outcome = _pipeline(chooser=None, candidate_marker=_marker()).run(
            _framed_request(tmp_path)
        )
        assert outcome.stage2.marks_drawn is None
        assert not (tmp_path / "r1_stage2.png").exists()


# ---- Letter counterbalancing (amendments item 22) ----

# With base seed 0, draw 3 swaps the two head-on candidates (draw 0 does not).
_SWAP_DRAW = 3


class TestLetterCounterbalancing:
    def test_draw_three_swaps_two_candidates(self):
        assert assign_letters(2, derive_letter_seed(0, _SWAP_DRAW)) == [1, 0]
        assert assign_letters(2, derive_letter_seed(0, 0)) == [0, 1]

    def test_assignment_is_a_seeded_permutation(self):
        seed = derive_letter_seed(123, 4)
        order = assign_letters(4, seed)
        assert sorted(order) == [0, 1, 2, 3]
        assert assign_letters(4, seed) == order

    def test_seed_is_sha256_derived_and_salted(self):
        assert derive_letter_seed(5, 0) == derive_letter_seed(5, 0)
        assert derive_letter_seed(5, 0) != derive_letter_seed(5, 1)
        assert derive_letter_seed(5, 0) != derive_letter_seed(6, 0)
        # Not the presentation-order seed of the same base.
        assert derive_letter_seed(5, 0) != 5

    def test_forced_letter_grounds_the_candidate_shown_under_it(self):
        chooser = _FixedChooser("A")
        pipe = _pipeline(chooser=chooser)
        pipe._stage2_draws = _SWAP_DRAW
        outcome = pipe.run(_request())
        [asked] = chooser.requests
        [shown_a] = [c for c in asked.candidates if c.label == "A"]
        params = _yield_params(outcome)
        assert (params["retreat_x_m"], params["retreat_y_m"]) == (
            round(shown_a.x, 3), round(shown_a.y, 3)
        )
        # Shown "A" is M3's "B" here: the command carries M3's label.
        stage2 = outcome.stage2
        assert stage2.choice["retreat_choice"] == "A"
        assert stage2.grounded_label == "B" == params["retreat_choice"]
        assert stage2.default_label == "A"
        assert stage2.default_letter == "B"
        assert outcome.grounded_command["degradations"] == []

    def test_default_is_no_longer_first_listed_letter_a(self):
        chooser = _FixedChooser("A")
        pipe = _pipeline(chooser=chooser)
        pipe._stage2_draws = _SWAP_DRAW
        stage2 = pipe.run(_request()).stage2
        [asked] = chooser.requests
        default = stage2.candidates[0]
        shown = {c.label: (c.x, c.y) for c in asked.candidates}
        assert shown[stage2.default_letter] == (default["x"], default["y"])
        assert stage2.default_letter != "A"

    def test_default_letter_is_balanced_over_draws(self):
        letters = []
        for index in range(200):
            _choice, record = run_retreat_stage2(
                _request(), _decision(), snapshot_frame_from_request(_request()), _DERIVED,
                _FixedChooser("A"), geometry=_geometry(), letter_seed_base=11,
                letter_draw_index=index,
            )
            letters.append(record.default_letter)
        assert 70 <= letters.count("A") <= 130
        assert letters.count("A") + letters.count("B") == 200

    def test_default_rank_lands_on_every_letter_of_four(self):
        counts = [0, 0, 0, 0]
        for index in range(400):
            counts[assign_letters(4, derive_letter_seed(11, index)).index(0)] += 1
        assert all(60 <= count <= 140 for count in counts)

    def test_assignment_is_recorded_and_recoverable(self, tmp_path):
        chooser = _FixedChooser("B")
        pipe = _pipeline(chooser=chooser, stage2_letter_seed=99)
        outcome = pipe.run(_request())
        payload = json.loads(
            write_decision_artifact(
                tmp_path, outcome, request=_request(), grounding_source=_source()
            ).read_text()
        )
        stage2 = payload["stage2"]
        assert stage2["letter_seed_base"] == 99
        assert stage2["letter_draw_index"] == 0
        assert stage2["letter_seed"] == derive_letter_seed(99, 0)
        order = assign_letters(len(stage2["candidates"]), stage2["letter_seed"])
        letters = sorted(c["label"] for c in stage2["candidates"])
        for letter, rank in zip(letters, order, strict=True):
            entry = stage2["letter_assignment"][letter]
            assert entry["rank"] == rank
            assert entry["candidate_label"] == stage2["candidates"][rank]["label"]
            assert stage2["candidates"][rank]["letter"] == letter
        [asked] = chooser.requests
        for option in asked.candidates:
            entry = stage2["letter_assignment"][option.label]
            assert (entry["x"], entry["y"]) == (option.x, option.y)

    def test_pipeline_advances_the_draw_index_per_derived_yield(self):
        pipe = _pipeline(chooser=_FixedChooser("A"), stage2_letter_seed=3)
        first = pipe.run(_request()).stage2
        second = pipe.run(_request()).stage2
        assert (first.letter_draw_index, second.letter_draw_index) == (0, 1)
        assert first.letter_seed != second.letter_seed

    def test_skipped_call_records_no_letters(self):
        stage2 = _pipeline(chooser=None).run(_request()).stage2
        assert stage2.letter_assignment is None
        assert stage2.default_letter is None
        assert stage2.default_label == stage2.candidates[0]["label"]

    def test_unrendered_letter_passes_through_unmapped(self):
        outcome = _pipeline(chooser=_FixedChooser("D", cause="invalid_label")).run(_request())
        assert outcome.stage2.grounded_label == "D"
        assert outcome.grounded_command["degradations"] == ["retreat=default:invalid_label"]


# ---- Listing-order randomization (amendments item 26, stage-2 prompt v3) ----

# With base seed 0 and a three-candidate band, draw 0 shows the default under
# B and lists C first: default letter, first-listed letter and "A" all differ.
_TAXONOMY_DRAW = 0
_WIDE_BAND = GroundingParams(mode="derived", aisle_y_band_m=(-0.55, 1.0))


def _listed_letters(user_prompt: str) -> list[str]:
    return [
        line[2] for line in user_prompt.splitlines() if line[:2] == "- " and line[3:4] == ":"
    ]


class TestListingOrder:
    def test_listing_seed_is_salted_apart_from_the_letter_seed(self):
        assert derive_listing_seed(5, 0) == derive_listing_seed(5, 0)
        assert derive_listing_seed(5, 0) != derive_listing_seed(5, 1)
        assert derive_listing_seed(5, 0) != derive_listing_seed(6, 0)
        assert derive_listing_seed(5, 0) != derive_letter_seed(5, 0)

    def test_listing_order_is_a_seeded_permutation(self):
        seed = derive_listing_seed(123, 4)
        listing = draw_listing_order(["D", "B", "A", "C"], seed)
        assert sorted(listing) == ["A", "B", "C", "D"]
        assert draw_listing_order(["A", "B", "C", "D"], seed) == listing

    def test_letter_a_lands_in_every_listing_slot(self):
        counts = [0, 0, 0, 0]
        for index in range(400):
            counts[draw_listing_order("ABCD", derive_listing_seed(11, index)).index("A")] += 1
        assert all(60 <= count <= 140 for count in counts)

    def test_default_letter_lands_in_every_listing_slot(self):
        counts = [0, 0, 0, 0]
        for index in range(400):
            default = "ABCD"[assign_letters(4, derive_letter_seed(11, index)).index(0)]
            listing = draw_listing_order("ABCD", derive_listing_seed(11, index))
            counts[listing.index(default)] += 1
        assert all(60 <= count <= 140 for count in counts)

    def test_default_letter_and_slot_of_a_are_independent(self):
        joint: dict[tuple[str, int], int] = {}
        for index in range(1600):
            default = "ABCD"[assign_letters(4, derive_letter_seed(11, index)).index(0)]
            slot = draw_listing_order("ABCD", derive_listing_seed(11, index)).index("A")
            joint[default, slot] = joint.get((default, slot), 0) + 1
        assert len(joint) == 16
        assert all(55 <= count <= 145 for count in joint.values())

    def test_listing_order_is_recorded_and_recoverable(self, tmp_path):
        chooser = _FixedChooser("B")
        outcome = _pipeline(chooser=chooser, stage2_letter_seed=99).run(_request())
        stage2 = json.loads(
            write_decision_artifact(
                tmp_path, outcome, request=_request(), grounding_source=_source()
            ).read_text()
        )["stage2"]
        letters = sorted(stage2["letter_assignment"])
        assert stage2["listing_seed"] == derive_listing_seed(99, 0)
        assert stage2["listing_order"] == draw_listing_order(letters, stage2["listing_seed"])
        # The record matches what was rendered and what was asked.
        assert _listed_letters(stage2["prompt"]["user_prompt"]) == stage2["listing_order"]
        [asked] = chooser.requests
        assert asked.listing_order == stage2["listing_order"]
        assert asked.prompt_version == 3

    def test_listing_follows_the_draw_index(self):
        orders = set()
        for index in range(8):
            _choice, record = run_retreat_stage2(
                _request(), _decision(), snapshot_frame_from_request(_request()), _WIDE_BAND,
                _FixedChooser("A"), geometry=_geometry(), letter_draw_index=index,
            )
            assert record.listing_seed == derive_listing_seed(0, index)
            assert _listed_letters(record.prompt["user_prompt"]) == record.listing_order
            orders.add(tuple(record.listing_order))
        assert len(orders) > 1

    def test_skipped_call_records_no_listing(self):
        stage2 = _pipeline(chooser=None).run(_request()).stage2
        assert stage2.listing_order is None
        assert stage2.listing_seed is None

    def test_listing_is_logged(self):
        outcome = _pipeline(chooser=_FixedChooser("B")).run(_request())
        line = format_stage2_log("r1", outcome.stage2)
        assert f"listing={''.join(outcome.stage2.listing_order)}" in line

    @pytest.mark.parametrize("answer", ["A", "B", "C"])
    def test_three_positional_readings_stay_distinct(self, tmp_path, answer):
        pipe = _pipeline(chooser=_FixedChooser(answer), params=_WIDE_BAND)
        pipe._stage2_draws = _TAXONOMY_DRAW
        outcome = pipe.run(_request())
        stage2 = json.loads(
            write_decision_artifact(
                tmp_path, outcome, request=_request(), grounding_source=_source()
            ).read_text()
        )["stage2"]
        choice = stage2["choice"]["retreat_choice"]
        assert (stage2["default_letter"], stage2["listing_order"][0]) == ("B", "C")
        readings = {
            "chose_first_listed": choice == stage2["listing_order"][0],
            "chose_default": choice == stage2["default_letter"],
            "chose_letter_a": choice == "A",
        }
        assert sum(readings.values()) == 1
        expected = {"A": "chose_letter_a", "B": "chose_default", "C": "chose_first_listed"}
        assert readings[expected[answer]]
        # The default reading agrees across the two letter spaces.
        assert readings["chose_default"] == (
            stage2["grounded_label"] == stage2["default_label"]
        )

    def test_mock_answer_is_listing_independent(self, monkeypatch):
        monkeypatch.setenv(
            "VGU_MOCK_RETREAT_CHOICE_FILE", "config/mock_decisions/retreat_choice_b.json"
        )
        requests = [
            RetreatChoiceRequest(
                request_id="r1", image_path="/tmp/r1.png", yielder_id="robot_1",
                crossing_order=["robot_2"], robot_states=[],
                candidates=[
                    RetreatCandidateOption(label="A", x=-1.8, y=0.36, backup_m=1.5, lateral_m=0.36),
                    RetreatCandidateOption(
                        label="B", x=-1.8, y=-0.36, backup_m=1.5, lateral_m=-0.36
                    ),
                ],
                listing_order=listing,
            )
            for listing in (["A", "B"], ["B", "A"])
        ]
        answers = []
        for request in requests:
            backend = build_retreat_choice_backend("mock", MockBackend())
            chooser = RetreatChooser(backend, ReasonerConfig(backend_id="mock"))
            answers.append(chooser.choose(request).choice)
        assert answers[0] == answers[1]
        assert answers[0].retreat_choice == "B"


# ---- The stage-2 v2 corpus: the calibration mini-pilot (2026-09-28) ----

# Run 20260928_112237 (gpt-4o): the default was shown under B and the model
# answered A, the first-listed letter under v2. Inlined because
# `data/logs/vm_runs/` is git-ignored.
_CALIBRATION_ROBOTS = [
    {"robot_id": "robot_1", "x": -0.1285708846463498, "y": -0.002179132872137446,
     "theta": -0.04758234750964273},
    {"robot_id": "robot_2", "x": 0.1372875547918655, "y": 0.0, "theta": math.pi},
]
_CALIBRATION_STAGE2 = {
    "status": "answered",
    "stage2_prompt_version": 2,
    "yielder_id": "robot_2",
    "crossing_order": ["robot_1"],
    "candidates": [
        {"backup_m": 1.652, "label": "A", "lateral_clearance_m": 1.918, "lateral_m": 0.36,
         "letter": "B", "min_sweep_clearance_m": 0.266, "x": 1.7892875547918654, "y": -0.36},
        {"backup_m": 1.652, "label": "B", "lateral_clearance_m": 1.918, "lateral_m": -0.36,
         "letter": "A", "min_sweep_clearance_m": 0.266, "x": 1.7892875547918654, "y": 0.36},
    ],
    "default_label": "A",
    "default_letter": "B",
    "letter_seed_base": 733253476989578658,
    "letter_draw_index": 0,
    "letter_seed": 2780733127990461938,
    "marks_drawn": True,
    "prompt": {
        "image_path": "data/logs/m5_frames/84d3ba7ffe9742a986267b6bbdb2a5ea_stage2.png",
        "user_sha256": "76bb6640fc8e1a512093de6956844e423c8541172c76c82551bf7463d964413c",
    },
    "choice": {"retreat_choice": "A", "justification": "x"},
    "grounded_label": "B",
}
_CALIBRATION_DIR = Path(__file__).resolve().parents[2] / "data/logs/vm_runs/calibration"


def _rerender_v2(stage2: dict, robots: list[dict]) -> str:
    record = RetreatStage2Record(**stage2)
    request = RetreatChoiceRequest(
        request_id="replay",
        image_path=record.prompt["image_path"],
        marks_drawn=record.marks_drawn,
        yielder_id=record.yielder_id,
        crossing_order=record.crossing_order,
        robot_states=[
            RobotStateInput(robot_id=r["robot_id"], x=r["x"], y=r["y"], theta=r["theta"])
            for r in robots
        ],
        candidates=[
            RetreatCandidateOption(
                label=c["letter"], x=c["x"], y=c["y"], backup_m=c["backup_m"],
                lateral_m=c["lateral_m"],
            )
            for c in record.candidates
        ],
        prompt_version=record.stage2_prompt_version,
    )
    return build_stage2_prompt_payload(request).user_prompt


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestStage2V2Corpus:
    def test_calibration_record_parses_without_a_listing(self):
        record = RetreatStage2Record(**_CALIBRATION_STAGE2)
        assert record.stage2_prompt_version == 2
        assert record.listing_order is None
        assert record.listing_seed is None

    def test_calibration_prompt_rerenders_through_v2(self):
        user_prompt = _rerender_v2(_CALIBRATION_STAGE2, _CALIBRATION_ROBOTS)
        assert _sha256(user_prompt) == _CALIBRATION_STAGE2["prompt"]["user_sha256"]
        # Under v2 the first-listed letter is always A: the confound v3 removes.
        assert _listed_letters(user_prompt)[0] == "A"

    @pytest.mark.skipif(
        not _CALIBRATION_DIR.is_dir(), reason="git-ignored calibration runs not present"
    )
    def test_every_calibration_call_rerenders_through_v2(self):
        rerendered = 0
        for path in sorted(_CALIBRATION_DIR.glob("2*/decisions/*.json")):
            artifact = json.loads(path.read_text())
            stage2 = artifact.get("stage2")
            if not stage2 or stage2["status"] == "skipped":
                continue
            user_prompt = _rerender_v2(stage2, artifact["scene"]["robots"])
            assert _sha256(user_prompt) == stage2["prompt"]["user_sha256"], path
            rerendered += 1
        assert rerendered == 6
