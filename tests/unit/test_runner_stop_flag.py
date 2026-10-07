"""Offline tests for the Isaac runner's stop flag (2026-10-07 shutdown-timing
ruling): a flag file makes `run_repetition` leave its loop normally, so GT is
closed and the manifest is written with an explicit aborted marker. Kit,
omni and carb are stubbed; only the loop, GT writer and manifest are real."""
import json
import sys
import types
from pathlib import Path

import pytest
import yaml

from isaac.vgu_sim import runner
from isaac.vgu_sim.config import ResolvedRunConfig, ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_YAML = ROOT / "isaac" / "config" / "scenarios" / "head_on_deadlock.yaml"
RENDER_DT = 1.0 / 30.0
PRE_FLAG_MANIFEST_KEYS = {
    "run_id", "scenario", "scenario_schema_version", "seed", "repetition", "headless",
    "isaac_sim_version", "ros_distribution", "physics_hz", "rendering_hz",
    "started_at_utc", "completed", "failure",
}


class FakeSimContext:
    def __init__(self) -> None:
        self.current_time = 0.0


class FakeApp:
    """Advances the fake sim clock one render step per update; touches the
    stop flag (as fc_launch's cleanup would) after `touch_after` updates."""

    def __init__(self, ctx: FakeSimContext, flag: Path | None, touch_after: int | None):
        self.ctx = ctx
        self.flag = flag
        self.touch_after = touch_after
        self.updates = 0

    def is_running(self) -> bool:
        return True

    def update(self) -> None:
        self.updates += 1
        self.ctx.current_time += RENDER_DT
        if self.touch_after is not None and self.updates == self.touch_after:
            self.flag.touch()


@pytest.fixture
def stub_isaac(monkeypatch):
    """Stub the Kit modules and the stage/graph helpers around the loop."""
    omni = types.ModuleType("omni")
    omni_usd = types.ModuleType("omni.usd")
    omni_usd.get_context = lambda: types.SimpleNamespace(get_stage=lambda: object())
    omni_timeline = types.ModuleType("omni.timeline")
    omni_timeline.get_timeline_interface = lambda: types.SimpleNamespace(stop=lambda: None)
    omni.usd = omni_usd
    omni.timeline = omni_timeline
    carb = types.ModuleType("carb")
    carb.log_error = lambda msg: None
    carb.log_warn = lambda msg: None
    for name, module in (("omni", omni), ("omni.usd", omni_usd),
                         ("omni.timeline", omni_timeline), ("carb", carb)):
        monkeypatch.setitem(sys.modules, name, module)

    ctx = FakeSimContext()
    for helper in ("_open_stage", "_enable_extensions", "_validate_stage",
                   "_set_timeline_window", "_add_scene_lighting", "_wire_ros_graphs"):
        monkeypatch.setattr(runner, helper, lambda *a, **k: None)
    monkeypatch.setattr(runner, "_attach_debug_rgb_annotator", lambda robots: None)
    monkeypatch.setattr(runner, "_start_cmd_vel_watchdog", lambda robots: None)
    monkeypatch.setattr(runner, "_wait_for_ros_topics", lambda *a, **k: None)
    monkeypatch.setattr(
        runner, "sample_robot_positions",
        lambda stage, ids: {rid: (0.1 * ctx.current_time, 0.0, 0.0) for rid in ids},
    )
    # run_repetition reads sim time from the context `_make_sim_context` returns.
    monkeypatch.setattr(runner, "_make_sim_context", lambda *a: _ctx_proxy(ctx))
    return ctx


def _ctx_proxy(ctx: FakeSimContext):
    class Proxy:
        def reset(self) -> None:
            pass

        def play(self) -> None:
            pass

        @property
        def current_time(self) -> float:
            return ctx.current_time

    return Proxy()


def _config(tmp_path: Path) -> ResolvedRunConfig:
    scenario = ScenarioConfig.model_validate(yaml.safe_load(SCENARIO_YAML.read_text()))
    return ResolvedRunConfig(
        scenario_path=tmp_path / "scene.usd", scenario=scenario, headless=True,
        repetitions=1, output_dir=tmp_path / "out", topic_timeout_sec=1.0,
        ros_domain_id=None,
    )


def _artifacts(result) -> tuple[dict, list[dict]]:
    manifest = json.loads(result.manifest_path.read_text())
    gt_path = result.manifest_path.parent / "ground_truth.jsonl"
    rows = [json.loads(line) for line in gt_path.read_text().splitlines()]
    return manifest, rows


def test_stop_requested_false_without_a_flag_path():
    assert runner.stop_requested(None) is False


def test_stop_requested_false_until_the_flag_exists(tmp_path):
    flag = tmp_path / "isaac.stop"
    assert runner.stop_requested(flag) is False
    flag.touch()
    assert runner.stop_requested(flag) is True


def test_flag_stops_the_loop_with_closed_gt_and_aborted_manifest(tmp_path, stub_isaac):
    flag = tmp_path / "isaac.stop"
    app = FakeApp(stub_isaac, flag, touch_after=300)  # ~10 sim-s in

    result = runner.run_repetition(app, _config(tmp_path), 0, stop_flag=flag)

    manifest, rows = _artifacts(result)
    assert result.completed is False
    assert manifest["completed"] is False
    assert manifest["aborted"] is True
    assert manifest["abort_reason"] == "stop_flag"
    assert manifest["abort_phase"] == "sim_loop"
    assert manifest["stop_flag_path"] == str(flag)
    assert manifest["aborted_at_sim_time_sec"] == pytest.approx(10.0, abs=0.1)
    assert manifest["failure"].startswith("aborted: stop flag")
    assert app.updates == 300
    assert 95 <= len(rows) <= 105
    assert rows[-1]["sim_time_sec"] < 10.1


def test_run_without_a_flag_keeps_the_pre_flag_manifest_shape(tmp_path, stub_isaac):
    app = FakeApp(stub_isaac, None, touch_after=None)

    result = runner.run_repetition(app, _config(tmp_path), 0, stop_flag=tmp_path / "never")

    manifest, rows = _artifacts(result)
    assert result.completed is True
    assert set(manifest) == PRE_FLAG_MANIFEST_KEYS
    assert len(rows) == 3001
    assert rows[-1]["sim_time_sec"] == pytest.approx(300.0, abs=0.05)


def test_flag_present_at_loop_entry_writes_no_sample_past_zero(tmp_path, stub_isaac):
    flag = tmp_path / "isaac.stop"
    flag.touch()
    app = FakeApp(stub_isaac, flag, touch_after=None)

    result = runner.run_repetition(app, _config(tmp_path), 0, stop_flag=flag)

    manifest, rows = _artifacts(result)
    assert app.updates == 0
    assert rows == []
    assert manifest["aborted_at_sim_time_sec"] == 0.0


def test_flag_during_topic_wait_marks_the_topic_wait_phase(tmp_path, stub_isaac, monkeypatch):
    flag = tmp_path / "isaac.stop"

    def stopped_wait(*args, **kwargs):
        raise runner._StopRequestedError(f"aborted: stop flag {flag} during the ROS topic wait")

    monkeypatch.setattr(runner, "_wait_for_ros_topics", stopped_wait)

    result = runner.run_repetition(FakeApp(stub_isaac, None, None), _config(tmp_path), 0,
                                   stop_flag=flag)

    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["completed"] is False
    assert manifest["abort_phase"] == "topic_wait"
    assert manifest["aborted_at_sim_time_sec"] is None


def test_run_simulation_passes_the_flag_and_closes_the_app(tmp_path, monkeypatch):
    seen = {}

    class App:
        closed = False

        def close(self) -> None:
            App.closed = True

    def fake_rep(app, config, rep, stop_flag=None):
        seen["stop_flag"] = stop_flag
        return types.SimpleNamespace(completed=False)

    monkeypatch.setattr(runner, "_get_app", lambda headless: App())
    monkeypatch.setattr(runner, "run_repetition", fake_rep)
    flag = tmp_path / "isaac.stop"

    results = runner.run_simulation(_config(tmp_path), stop_flag=flag)

    assert seen["stop_flag"] == flag
    assert App.closed is True
    assert len(results) == 1
