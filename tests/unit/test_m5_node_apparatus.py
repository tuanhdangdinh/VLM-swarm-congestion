"""Node-level prompt-apparatus wiring (ROS2 stubbed; harness from test_m5_node_probe.py)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from swarm_orchestrator.models import (
    AnnotationOverlayReport,
    PipelineOutcome,
    RobotView,
    SceneSnapshot,
    TerminalStage,
    parse_annotation_overlays,
)

from reasoning.vlm.prompt_builder import (
    _CANDIDATE_OPTIONS_HEADER,
    _METRIC_GRID_SENTENCE,
    _MOTION_TRAILS_SENTENCE,
    _ZOOM_TILE_SENTENCE,
)
from tests.unit.test_m5_node_probe import (  # noqa: F401  (node_env is a fixture)
    WAIT_SEC,
    _artifact,
    _config,
    _make_node,
    _result,
    _run_probe,
    _snapshot,
    node_env,
)

_CALIBRATION = str(Path("ros2_ws/src/swarm_perception/config/calibration.yaml").resolve())


class _RecordingPipeline:
    def __init__(self) -> None:
        self.requests = []

    def run(self, request):
        self.requests.append(request)
        return PipelineOutcome(
            request_id=request.request_id,
            reasoner_result=_result(request.request_id, congested=False),
            grounded_command=None,
            terminal_stage=TerminalStage.VLM,
            failure_reason="congestion_detected=false",
        )

    def analyze(self, request):
        return self.run(request)


def _scene_msg(stamp: float, diagnostics: dict) -> object:
    from types import SimpleNamespace

    payload = _snapshot(stamp, close=True).model_dump(mode="json")
    payload.pop("dropped_frame")
    payload["diagnostics"] = diagnostics
    return SimpleNamespace(data=json.dumps(payload))


def _run_trigger(node, diagnostics: dict | None = None, stamp: float = 60.0) -> str:
    node._frame_stamp = stamp
    node._on_scene_state(_scene_msg(stamp, diagnostics or {}))
    node._future.result(timeout=WAIT_SEC)
    request_id = node._pending_request.request_id
    node._on_timer()
    return request_id


def _node(node_env, tmp_path, pipeline, **overrides):  # noqa: F811
    overrides.setdefault("t0_probe_mode", False)
    node, clock = _make_node(node_env, tmp_path, pipeline, **overrides)
    node._frame_rgb = np.full((960, 1280, 3), 90, dtype=np.uint8)
    return node, clock


_GRID_ON = {"annotation_overlays": ["metric_grid"], "metric_grid_spacing_m": 0.5}


class TestFlagsOff:
    def test_request_carries_no_apparatus_and_v2_prompt(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(node_env, tmp_path, pipeline)
        _run_trigger(node)
        request = pipeline.requests[0]
        assert request.prompt_version == 2
        assert request.metric_grid_spacing_m is None
        assert request.motion_trails_drawn is False
        assert request.zoom_tile_path is None
        assert request.candidate_options is None

    def test_artifact_records_every_flag_off(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(node_env, tmp_path, pipeline)
        request_id = _run_trigger(node)
        conditions = _artifact(node, request_id)["prompt_conditions"]
        assert conditions["metric_grid"] == {"requested": False, "m1_drawn": False, "stated": False}
        assert conditions["motion_trails"] == {
            "requested": False, "m1_drawn": False, "stated": False
        }
        assert conditions["zoom_tile_requested"] is False and conditions["zoom_tile"] is None
        assert conditions["permutation_votes"] == 1
        assert conditions["candidate_options_requested"] is False
        assert conditions["construct_constrained_selection"] is False


class TestOverlaySentences:
    def test_grid_stated_only_when_requested_and_drawn(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_metric_grid=True
        )
        request_id = _run_trigger(node, _GRID_ON)
        request = pipeline.requests[0]
        assert request.metric_grid_spacing_m == 0.5
        payload = _artifact(node, request_id)
        assert _METRIC_GRID_SENTENCE.format(spacing="0.5") in payload["prompt"]["user_prompt"]
        assert payload["prompt_conditions"]["metric_grid"]["stated"] is True

    def test_grid_requested_but_not_drawn_is_not_stated_and_is_logged(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_metric_grid=True
        )
        request_id = _run_trigger(node, {})
        assert pipeline.requests[0].metric_grid_spacing_m is None
        conditions = _artifact(node, request_id)["prompt_conditions"]["metric_grid"]
        assert conditions == {"requested": True, "m1_drawn": False, "stated": False}
        assert node.get_logger().matching("apparatus mismatch")

    def test_grid_drawn_but_not_requested_is_recorded_not_stated(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(node_env, tmp_path, pipeline, plan_channel_enabled=True)
        request_id = _run_trigger(node, _GRID_ON)
        assert pipeline.requests[0].metric_grid_spacing_m is None
        conditions = _artifact(node, request_id)["prompt_conditions"]["metric_grid"]
        assert conditions == {"requested": False, "m1_drawn": True, "stated": False}

    def test_trails_stated_when_requested_and_drawn(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_motion_trails=True
        )
        request_id = _run_trigger(node, {"annotation_overlays": ["motion_trails"]})
        assert pipeline.requests[0].motion_trails_drawn is True
        assert _MOTION_TRAILS_SENTENCE in _artifact(node, request_id)["prompt"]["user_prompt"]


class TestZoomTile:
    def test_tile_written_attached_and_recorded(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_zoom_tile=True,
            stage2_calibration_path=_CALIBRATION, keep_debug_frames=True,
        )
        request_id = _run_trigger(node)
        request = pipeline.requests[0]
        assert request.zoom_tile_path == str(Path(tmp_path / "frames" / f"{request_id}_zoom.png"))
        assert Path(request.zoom_tile_path).is_file()
        payload = _artifact(node, request_id)
        tile = payload["prompt_conditions"]["zoom_tile"]
        assert tile["attached"] is True
        assert tile["robot_ids"] == ["robot_1", "robot_2"]
        assert tile["output_size"] == [640, 480]
        assert _ZOOM_TILE_SENTENCE in payload["prompt"]["user_prompt"]

    def test_tile_frames_the_whole_involved_set(self, node_env, tmp_path):  # noqa: F811
        # Apparatus ruling 2026-10-04: the tile frames the congestion event's
        # involved set -- here two robots 1.6 m apart, beyond one 0.6 m margin --
        # and not an uninvolved robot in the same scene.
        node, _ = _node(
            node_env, tmp_path, _RecordingPipeline(), plan_channel_enabled=True,
            prompt_zoom_tile=True, stage2_calibration_path=_CALIBRATION,
        )
        snapshot = SceneSnapshot(
            stamp=60.0,
            frame_id="overhead_camera",
            robots=[
                RobotView(robot_id=rid, x=x, y=y, theta=0.0, linear_velocity=0.0,
                          status="STOPPED", stamp=60.0)
                for rid, x, y in (
                    ("robot_1", -0.8, 0.0), ("robot_2", 0.8, 0.1), ("robot_3", 2.0, 1.5)
                )
            ],
        )
        _, record = node._apparatus_inputs(
            "req-zoom", snapshot, ["robot_1", "robot_2"], node._frame_rgb
        )
        assert record.attached and record.robot_ids == ("robot_1", "robot_2")
        assert record.world_bounds_m == pytest.approx((-1.4, 1.4, -0.6, 0.7))

    def test_tile_removed_with_the_frame_when_frames_are_not_kept(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_zoom_tile=True,
            stage2_calibration_path=_CALIBRATION,
        )
        request_id = _run_trigger(node)
        assert not (tmp_path / "frames" / f"{request_id}_zoom.png").exists()

    def test_missing_calibration_drops_the_tile_and_its_sentence(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True, prompt_zoom_tile=True,
            stage2_calibration_path=str(tmp_path / "missing.yaml"),
        )
        request_id = _run_trigger(node)
        assert pipeline.requests[0].zoom_tile_path is None
        payload = _artifact(node, request_id)
        assert payload["prompt_conditions"]["zoom_tile"]["attached"] is False
        assert _ZOOM_TILE_SENTENCE not in payload["prompt"]["user_prompt"]

    def test_llama_server_with_zoom_tile_fails_fast(self, node_env, tmp_path):  # noqa: F811
        node_module, _ = node_env
        with pytest.raises(ValueError, match="llama_server"):
            node_module.OrchestratorNode(
                config=_config(
                    tmp_path, reasoning_backend_id="llama_server", plan_channel_enabled=True,
                    prompt_zoom_tile=True,
                ),
                pipeline=_RecordingPipeline(),
            )


class TestCandidateOptions:
    def test_options_rendered_and_construct_change_recorded(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, _ = _node(
            node_env, tmp_path, pipeline, plan_channel_enabled=True,
            prompt_candidate_options=True,
        )
        request_id = _run_trigger(node)
        options = pipeline.requests[0].candidate_options
        assert sorted(entry.robot_id for entry in options) == ["robot_1", "robot_2"]
        payload = _artifact(node, request_id)
        assert _CANDIDATE_OPTIONS_HEADER in payload["prompt"]["user_prompt"]
        conditions = payload["prompt_conditions"]
        assert conditions["construct_constrained_selection"] is True
        assert len(conditions["candidate_options"]) == 2


class TestProbeArtifact:
    def test_probe_records_m1_overlays_but_states_nothing(self, node_env, tmp_path):  # noqa: F811
        pipeline = _RecordingPipeline()
        node, clock = _node(
            node_env, tmp_path, pipeline, t0_probe_mode=True, plan_channel_enabled=True,
            prompt_metric_grid=True, prompt_permutation_votes=3,
        )
        node._latest_overlays = AnnotationOverlayReport(
            overlays=("metric_grid",), metric_grid_spacing_m=0.5
        )
        request_id = _run_probe(node, clock, at=1020.0)
        conditions = _artifact(node, request_id)["prompt_conditions"]
        assert conditions["prompt_version"] == 2
        assert conditions["metric_grid"] == {"requested": True, "m1_drawn": True, "stated": False}
        assert conditions["permutation_votes"] == 1

    def test_grid_on_t0_run_tags_the_probe_frame_condition(self, node_env, tmp_path):  # noqa: F811
        # Apparatus ruling 2026-10-04: a T0 run with M1's grid/trails on but
        # every prompt flag off (the frozen v2 probe prompt) must still show
        # the frame condition on each probe artifact, so grid-on probes are
        # never pooled with grid-off ones.
        from types import SimpleNamespace

        node, clock = _node(node_env, tmp_path, _RecordingPipeline(), t0_probe_mode=True)
        payload = _snapshot(50.0).model_dump(mode="json")
        payload.pop("dropped_frame")
        payload["diagnostics"] = {
            "annotation_overlays": ["metric_grid", "motion_trails"],
            "metric_grid_spacing_m": 0.5,
        }
        node._on_scene_state(SimpleNamespace(data=json.dumps(payload)))
        assert node._future is None, "the scene must not trigger a real analysis"
        request_id = _run_probe(node, clock, at=1020.0)
        artifact = _artifact(node, request_id)
        assert artifact["probe"] is True
        conditions = artifact["prompt_conditions"]
        assert conditions["metric_grid"] == {"requested": False, "m1_drawn": True, "stated": False}
        assert conditions["motion_trails"] == {
            "requested": False, "m1_drawn": True, "stated": False
        }
        assert conditions["metric_grid_spacing_m"] == 0.5
        assert conditions["prompt_version"] == 2

    def test_grid_off_t0_run_tags_the_probe_frame_condition_off(self, node_env, tmp_path):  # noqa: F811
        node, clock = _node(node_env, tmp_path, _RecordingPipeline(), t0_probe_mode=True)
        request_id = _run_probe(node, clock, at=1020.0)
        conditions = _artifact(node, request_id)["prompt_conditions"]
        assert conditions["metric_grid"]["m1_drawn"] is False
        assert conditions["motion_trails"]["m1_drawn"] is False


class TestDefaultPipelineVotes:
    def test_configured_votes_reach_the_default_pipeline(self, node_env, tmp_path):  # noqa: F811
        node_module, _ = node_env
        node = node_module.OrchestratorNode(
            config=_config(tmp_path, prompt_permutation_votes=3, t0_probe_mode=False)
        )
        assert node._pipeline._permutation_votes == 3
        assert node._pipeline._registry_order == ("robot_1", "robot_2")


class TestConfigValidation:
    @pytest.mark.parametrize(
        "flag",
        [
            "prompt_metric_grid",
            "prompt_motion_trails",
            "prompt_zoom_tile",
            "prompt_candidate_options",
        ],
    )
    def test_apparatus_text_flags_require_prompt_v3(self, tmp_path, flag):
        with pytest.raises(ValidationError, match="plan_channel_enabled"):
            _config(tmp_path, **{flag: True})

    def test_votes_do_not_require_prompt_v3(self, tmp_path):
        assert _config(tmp_path, prompt_permutation_votes=3).prompt_permutation_votes == 3

    def test_votes_below_one_rejected(self, tmp_path):
        with pytest.raises(ValidationError):
            _config(tmp_path, prompt_permutation_votes=0)

    def test_every_apparatus_flag_defaults_off(self, tmp_path):
        config = _config(tmp_path)
        assert not (
            config.prompt_metric_grid
            or config.prompt_motion_trails
            or config.prompt_zoom_tile
            or config.prompt_candidate_options
        )
        assert config.prompt_permutation_votes == 1


class TestParseOverlays:
    def test_reads_names_and_spacing(self):
        raw = json.dumps({"diagnostics": _GRID_ON})
        assert parse_annotation_overlays(raw) == AnnotationOverlayReport(
            overlays=("metric_grid",), metric_grid_spacing_m=0.5
        )

    @pytest.mark.parametrize("raw", ["{}", "not json", json.dumps({"diagnostics": None})])
    def test_missing_or_malformed_is_empty(self, raw):
        assert parse_annotation_overlays(raw) == AnnotationOverlayReport()

    def test_rejects_non_positive_spacing(self):
        raw = json.dumps(
            {"diagnostics": {"annotation_overlays": ["metric_grid"], "metric_grid_spacing_m": 0}}
        )
        assert parse_annotation_overlays(raw).metric_grid_spacing_m is None
