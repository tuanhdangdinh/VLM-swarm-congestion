# ruff: noqa: E501  (fixture log lines are copied verbatim)
"""Unit tests for the offline demo-video renderer (`scripts/demo_panel`).

The log lines below are copied verbatim from the archived bundle
`ib10_safety/runs/ib10S_e03_armA_a1` (m5.log, m4.log); the decision artifact
is a reduced copy of that bundle's `decisions/18c2a25e....json` keeping only
the fields the terminal commands read. The tests need `jq`, `grep`, `sort`
and `awk` on PATH (the renderer runs them for real).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.demo_panel import logparse as lp
from scripts.demo_panel.bundle import build_time_map, fallback_anchor, load_bundle, load_gt
from scripts.demo_panel.pipeline import load_clip_map
from scripts.demo_panel.render import wrap_text
from scripts.demo_panel.scene import CameraClipScene
from scripts.demo_panel.terminal import (
    build_transcript,
    decision_commands,
    filter_command,
    mask_stamp,
    python_filter,
    run_shell,
)
from scripts.demo_panel.timeline import (
    BURST_CAPTION,
    CallSpan,
    TimelineItem,
    TimelineParams,
    build_timeline,
    smooth_captions,
)
from scripts.demo_panel.timemap import Anchor, ClipTimeMap, SceneClock, WallSimMap, estimate_offset

pytestmark = pytest.mark.skipif(
    any(shutil.which(t) is None for t in ("jq", "grep", "sort", "awk")),
    reason="jq/grep/sort/awk required",
)

REQ = "18c2a25e8e434b808f050116de741892"
M5_LINES = [
    "[INFO] [launch]: All log files can be found below /root/.ros/log/x",
    "[orchestrator_node-1] [INFO] [1794638362.273284983] [orchestrator_node]: session_id=864de40cb3854403924a743303f3e446 run_id=20261114_063740",
    f"[orchestrator_node-1] [INFO] [1794638416.604590078] [orchestrator_node]: starting analysis request={REQ} robots=['robot_2', 'robot_3'] reason=2 robot(s) stalled >= 12.0s order=id_asc distance_to_goal_m={{'robot_3': 1.97, 'robot_2': 2.0}}",
    "[orchestrator_node-1] Gemini Interactions API has no ('temperature', 'top_p', 'top_k', 'presence_penalty') fields",
    f"[orchestrator_node-1] [INFO] [1794638425.010272826] [orchestrator_node]: shadow request={REQ} scenario=intersection strategy=yield yield=robot_1 disagree=true",
    f"[orchestrator_node-1] [INFO] [1794638425.013946175] [orchestrator_node]: decision artifact written: data/logs/m5_decisions/{REQ}.json",
    f"[orchestrator_node-1] [INFO] [1794638425.015180609] [orchestrator_node]: dispatch request={REQ} command={REQ}-junction-recede-robot_4 robot=robot_4 plan_id=1",
    "[orchestrator_node-1] [INFO] [1794638425.221939686] [orchestrator_node]: trigger suppressed robots=['robot_1', 'robot_2', 'robot_3', 'robot_4'] frame_ready=True",
    f"[orchestrator_node-1] [INFO] [1794638470.159162722] [orchestrator_node]: junction_clear phase advance command={REQ}-junction-recede-robot_4 completed=True phase_reached=recede done=False",
]
M4_LINES = [
    "[safety_monitor_node-3] [INFO] [1794638351.449445195] [safety_monitor_node]: Safety monitor started min_distance_m=0.45 max_linear_velocity_mps=0.2 scoped_clearing_exemption=True",
    "[safety_monitor_node-3] [WARN] [1794638404.657593650] [safety_monitor_node]: safety stop robot=robot_2 reason=min_distance_violation",
    "[safety_monitor_node-3] [WARN] [1794638404.688877307] [safety_monitor_node]: safety stop robot=robot_3 reason=min_distance_violation",
    "[safety_monitor_node-3] [WARN] [1794638404.701000000] [safety_monitor_node]: safety stop robot=robot_2 reason=min_distance_violation",
    "[safety_monitor_node-3] [WARN] [1794638404.726000000] [safety_monitor_node]: safety stop robot=robot_2 reason=min_distance_violation",
    "[safety_monitor_node-3] [WARN] [1794638404.731000000] [safety_monitor_node]: safety stop robot=robot_3 reason=min_distance_violation",
    f"[command_bus_node-1] [INFO] [1794638425.015251459] [command_bus_node]: command received command={REQ}-junction-recede-robot_4 robot=robot_4 action=reverse",
    f"[command_bus_node-1] [INFO] [1794638425.100222838] [command_bus_node]: status published command={REQ}-junction-recede-robot_4 robot=robot_4 status=ACTIVE",
    "[safety_monitor_node-3] [INFO] [1794638425.220512662] [safety_monitor_node]: exempt pairs changed pairs=robot_1+robot_4,robot_2+robot_4,robot_3+robot_4",
    f"[command_bus_node-1] [INFO] [1794638570.769385587] [command_bus_node]: crossing_chain gate_admit command={REQ}-junction-cross yielder=robot_1 passer=robot_2 clear_m=1.921 escort_m=1.921 sim_t=73.267",
]
DECISION = {
    "request_id": REQ,
    "prompt_version": 3,
    "prompt": {
        "user_prompt": "You are a warehouse swarm robotics traffic controller.\n\nRobot states:\n- robot_1",
        "user_sha256": "a8bb1b522dc871b89f3f052294914f2a8ea1c594a6bdd229289d1f76a94f74da",
    },
    "decision": {
        "strategy": "junction_clear",
        "involved_robots": ["robot_1", "robot_2", "robot_3", "robot_4"],
        "justification": "A multi-robot junction deadlock is present.",
    },
    "diagnostics": {
        "backend_id": "gemini",
        "served_model": "gemini-robotics-er-2-preview",
        "latency_ms": 8201,
        "attempts": 1,
        "token_usage": {"total_tokens": 3823},
        "decision_degradations": ["proposed_plan=default:invalid_structure"],
    },
    "plan": {"provenance": "m3_default", "rejection_reason": "plan absent"},
    "dispatched_robot_ids": ["robot_4", "robot_1", "robot_2", "robot_3"],
    "scene": {"stamp": 30.0},
}


def _gt_row(t: float, d: float = 2.0) -> dict:
    robots = {
        rid: {"x": x, "y": 0.0, "theta": 0.0, "goal_x": 1.0, "goal_y": 0.0}
        for rid, x in (("robot_1", -1.0), ("robot_2", 1.0))
    }
    return {"sim_time_sec": t, "robots": robots, "min_pairwise_distance_m": d}


def make_bundle(tmp_path: Path, decision: dict | None = None, m5: list[str] | None = None) -> Path:
    root = tmp_path / "ib10S_test_armA_a1"
    (root / "decisions").mkdir(parents=True)
    (root / "gt").mkdir()
    (root / "m5.log").write_text("\n".join(M5_LINES if m5 is None else m5) + "\n")
    (root / "m4.log").write_text("\n".join(M4_LINES) + "\n")
    (root / "CONDITION.txt").write_text("label=ib10S_test_armA_a1 arm=A backend=gemini map=x\n")
    dec = DECISION if decision is None else decision
    (root / "decisions" / f"{REQ}.json").write_text(json.dumps(dec))
    # Scene log: monotonic t and sim stamps with wall = t + 1794636848.5 and
    # 0.28 sim-s per wall-s, so the decision anchor (wall 416.6 -> sim 30.0) fits.
    rows = []
    for k in range(0, 600):
        t = 1500.0 + k
        rows.append({"t": t, "scene": {"stamp": 30.0 + (t + 1794636848.5 - 1794638416.6) * 0.28}})
    rows = [r for r in rows if r["scene"]["stamp"] >= 0]
    (root / "m5_scene.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    gt = [_gt_row(i * 0.1) for i in range(0, 1500)]
    (root / "gt" / "ground_truth.jsonl").write_text("\n".join(json.dumps(r) for r in gt) + "\n")
    return root


def test_parse_ros_line_extracts_wall_stamp_and_message():
    r = lp.parse_ros_line(M5_LINES[2])
    assert r is not None and r.wall == pytest.approx(1794638416.604590078)
    assert r.node == "orchestrator_node" and r.msg.startswith("starting analysis")


def test_parse_ros_line_rejects_unstamped_line():
    assert lp.parse_ros_line(M5_LINES[3]) is None


def test_parse_starting_analysis_reads_robots_and_reason():
    st = lp.parse_starting_analysis(lp.parse_ros_line(M5_LINES[2]).msg)
    assert st["request"] == REQ
    assert st["robots"] == ["robot_2", "robot_3"]
    assert st["reason"] == "2 robot(s) stalled >= 12.0s"


def test_parse_artifact_written_returns_request_id():
    assert lp.parse_artifact_written(lp.parse_ros_line(M5_LINES[5]).msg) == REQ


def test_parse_sim_t_reads_embedded_sim_time():
    assert lp.parse_sim_t(lp.parse_ros_line(M4_LINES[-1]).msg) == pytest.approx(73.267)


def test_filter_command_output_equals_python_filter(tmp_path):
    root = make_bundle(tmp_path)
    shell = run_shell(filter_command(), root)
    py = python_filter({"m5.log": M5_LINES, "m4.log": M4_LINES})
    assert shell == py
    assert all("trigger suppressed" not in ln and "shadow request" not in ln for ln in shell)


def test_transcript_log_items_are_verbatim_lines_from_the_logs(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    t = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    originals = set(M5_LINES) | set(M4_LINES)
    logs = [it for it in t.items if it.kind == "log"]
    assert logs and all(it.text in originals for it in logs)


def test_transcript_has_no_arrival_line_when_log_has_none(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    t = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    assert not any("arrived at base goal" in it.text for it in t.items)
    assert not any("no dispatch" in it.text for it in t.items)


def test_transcript_collapses_repeated_safety_stops_with_count(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    t = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    stops = [it for it in t.items if it.kind == "log" and "safety stop" in it.text]
    markers = [it for it in t.items if it.kind == "marker"]
    assert len(stops) == 2  # first robot_2 and first robot_3 line, verbatim
    assert [m.text for m in markers] == ["[… 3 similar 'safety stop' lines]"]


def test_mask_stamp_makes_repeats_equal():
    assert mask_stamp(M4_LINES[1]) == mask_stamp(M4_LINES[3])
    assert mask_stamp(M4_LINES[1]) != mask_stamp(M4_LINES[2])


def test_decision_block_output_matches_running_jq_directly(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    t = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    for cmd in decision_commands(REQ, has_plan=True):
        shown_idx = next(i for i, it in enumerate(t.items) if it.text == f"$ {cmd}")
        shown = []
        for it in t.items[shown_idx + 1 :]:
            if it.kind != "output":
                break
            shown.append(it.text)
        direct = subprocess.run(["bash", "-c", cmd], cwd=root, capture_output=True, text=True)
        assert shown == direct.stdout.splitlines()


def test_decision_commands_print_concise_model_call_line(tmp_path):
    root = make_bundle(tmp_path)
    out = run_shell(decision_commands(REQ, has_plan=True)[2], root)
    assert out == [
        '{"backend_id":"gemini","served_model":"gemini-robotics-er-2-preview",'
        '"latency_ms":8201,"attempts":1,"total_tokens":3823}'
    ]


def test_decision_commands_show_mock_backend_without_model_or_tokens(tmp_path):
    mock = json.loads(json.dumps(DECISION))
    mock["diagnostics"].update(
        backend_id="mock",
        served_model=None,
        latency_ms=0,
        token_usage=None,
        decision_degradations=[],
    )
    root = make_bundle(tmp_path, decision=mock)
    out = run_shell(decision_commands(REQ, has_plan=True)[2], root)
    assert out == [
        '{"backend_id":"mock","served_model":null,"latency_ms":0,"attempts":1,"total_tokens":null}'
    ]


def test_decision_commands_skip_grounding_without_plan():
    assert not any("provenance" in c for c in decision_commands(REQ, has_plan=False))


def test_scene_clock_rejects_decreasing_sim():
    with pytest.raises(ValueError):
        SceneClock([0.0, 1.0, 2.0], [0.0, 2.0, 1.0])


def test_wall_sim_map_recovers_offset_from_anchors():
    clock = SceneClock([0.0, 10.0, 20.0], [0.0, 3.0, 5.0])
    anchors = [Anchor(1000.0 + 10.0, 3.0, "a"), Anchor(1000.0 + 15.0, 4.0, "b")]
    off, spread = estimate_offset(anchors, clock)
    assert off == pytest.approx(1000.0) and spread == pytest.approx(0.0)
    wmap = WallSimMap(clock, off)
    assert wmap.wall_to_sim(1005.0) == pytest.approx(1.5)
    assert all(abs(r) < 1e-9 for _, r in wmap.residuals(anchors))


def test_build_time_map_reports_anchor_error_within_threshold(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    info = build_time_map(b, load_gt(b)).info
    assert info.anchor_count >= 1 and info.max_abs_error_sim_sec < 0.5


SESSION = "864de40cb3854403924a743303f3e446"


def _move_scene_log(root: Path, *names: str) -> None:
    src = root / "m5_scene.jsonl"
    for n in names:
        (root / n).write_text(src.read_text())
    src.unlink()


def test_scene_log_prefers_m5_scene_jsonl(tmp_path):
    root = make_bundle(tmp_path)
    (root / f"scene_{SESSION}.jsonl").write_text('{"t": 1.0, "scene": {"stamp": 1.0}}\n')
    b = load_bundle(root)
    assert b.scene_log == "m5_scene.jsonl" and len(b.scene_rows) > 1


def test_scene_log_falls_back_to_session_named_file(tmp_path):
    root = make_bundle(tmp_path)
    _move_scene_log(root, f"scene_{SESSION}.jsonl", "scene_00000000000000000000000000000000.jsonl")
    b = load_bundle(root)
    assert b.scene_log == f"scene_{SESSION}.jsonl"
    assert f"scene_{SESSION}.jsonl" in build_time_map(b, load_gt(b)).info.method


def test_scene_log_falls_back_to_single_scene_file(tmp_path):
    root = make_bundle(tmp_path)
    _move_scene_log(root, "scene_abc.jsonl")
    assert load_bundle(root).scene_log == "scene_abc.jsonl"


def test_scene_log_rejects_ambiguous_scene_files(tmp_path):
    root = make_bundle(tmp_path)
    _move_scene_log(root, "scene_abc.jsonl", "scene_def.jsonl")
    with pytest.raises(ValueError, match="ambiguous"):
        load_bundle(root)


def test_scene_log_absent_loads_empty(tmp_path):
    root = make_bundle(tmp_path)
    (root / "m5_scene.jsonl").unlink()
    b = load_bundle(root)
    assert b.scene_log == "" and b.scene_rows == []


def test_fallback_anchor_pairs_first_stop_with_gt_threshold_crossing(tmp_path):
    root = make_bundle(tmp_path)
    b = load_bundle(root)
    gt = [_gt_row(0.0), _gt_row(27.0, 0.44), _gt_row(28.0, 0.40)]
    a = fallback_anchor(b, gt)
    assert a.wall == pytest.approx(1794638404.657593650)
    assert a.sim == pytest.approx(27.3)  # GT time + 0.300 s GT clock offset


def test_clip_time_map_maps_frames_and_sim_both_ways():
    m = ClipTimeMap([(0, 10.0), (100, 20.0)])
    assert m.sim_at_frame(50) == pytest.approx(15.0)
    assert m.frame_at_sim(15.04) == 50
    assert m.frame_at_sim(9.0) is None


def test_load_clip_map_accepts_recorder_style_json(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"first_stamp": 5.0, "last_stamp": 15.0, "frames": 101}))
    assert load_clip_map(p).frame_at_sim(10.0) == 50


def test_camera_clip_scene_shows_frame_for_sim_time(tmp_path):
    path = tmp_path / "clip.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for i in range(20):
        w.write(np.full((48, 64, 3), i * 12, dtype=np.uint8))
    w.release()
    scene = CameraClipScene(path, ClipTimeMap([(0, 100.0), (19, 119.0)]))
    assert scene.frame_index_at(107.5) == 7
    img = scene.frame_at(107.5, (64, 48))
    assert abs(int(img[24, 32, 0]) - 7 * 12) <= 4
    assert scene.frame_at(150.0, (64, 48)).max() == 40  # outside the clip: blank


def test_camera_clip_scene_continues_frame_index_across_segments(tmp_path):
    paths = []
    for k in range(2):
        p = tmp_path / f"clip_{k:03d}.mp4"
        w = cv2.VideoWriter(str(p), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
        for i in range(10):
            w.write(np.full((48, 64, 3), (k * 10 + i) * 12, dtype=np.uint8))
        w.release()
        paths.append(p)
    scene = CameraClipScene(paths, ClipTimeMap([(0, 0.0), (19, 19.0)]))
    assert scene.frame_count == 20
    img = scene.frame_at(13.2, (64, 48))
    assert abs(int(img[24, 32, 0]) - 13 * 12) <= 4


def test_cost_poll_is_printed_after_the_artifact_it_counts(tmp_path):
    root = make_bundle(tmp_path)
    (root / "cost.log").write_text(
        "06:40:18 analyses=1 artifacts=0 billed_calls=0 est_usd=0.0000\n"
        "06:40:25 analyses=1 artifacts=1 billed_calls=1 est_usd=0.0074\n"
    )
    (root / "gt" / "run_manifest.json").write_text(
        json.dumps({"started_at_utc": "2026-11-14T06:38:12.790889Z"})
    )
    b = load_bundle(root)
    t = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    texts = [it.text for it in t.items]
    artifact = next(i for i, x in enumerate(texts) if "decision artifact written" in x)
    poll = texts.index("$ grep -m1 ' billed_calls=1 ' cost.log")
    assert poll > artifact
    assert texts[poll + 1] == "06:40:25 analyses=1 artifacts=1 billed_calls=1 est_usd=0.0074"


def test_wrap_text_keeps_every_character():
    line = M5_LINES[2]
    rows = wrap_text(line, 50)
    assert "".join(rows) == line and all(len(r) <= 50 for r in rows)


def test_timeline_plays_model_call_at_true_wall_duration():
    items = [TimelineItem(10.0, 1, False), TimelineItem(12.0, 1, False)]
    tl = build_timeline(
        items, [CallSpan(10.0, 12.0, 8.0)], 20.0, TimelineParams(log_rows_per_sec=100)
    )
    assert tl.reveal[1] - tl.reveal[0] == pytest.approx(8.0, abs=0.05)


def test_timeline_holds_sim_clock_during_line_burst():
    items = [TimelineItem(5.0, 2, False) for _ in range(5)]
    tl = build_timeline(items, [], 10.0, TimelineParams(log_rows_per_sec=4.0))
    gaps = np.diff(tl.reveal)
    assert np.all(gaps >= 0.5 - 1e-9)
    assert tl.sim_at(tl.reveal[2]) == pytest.approx(5.0)


def test_smooth_captions_merges_burst_flicker():
    caps = [(0, 1, "3x"), (1, 1.3, BURST_CAPTION), (1.3, 1.31, "3x"), (1.31, 1.6, BURST_CAPTION)]
    out = smooth_captions(caps, 0.6)
    assert out == [(0, 1, "3x"), (1, 1.6, BURST_CAPTION)]


def test_fit_scene_box_matches_clip_aspect():
    from scripts.demo_panel.render import Layout, fit_scene_box

    assert fit_scene_box(Layout(), (1280, 960)).scene_box == (40, 92, 800, 600)
    assert fit_scene_box(Layout(), (480, 960)).scene_box == Layout().scene_box


def _clip(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (64, 48))
    for _ in range(20):
        w.write(np.full((48, 64, 3), 100, dtype=np.uint8))
    w.release()
    return path


def test_compositor_draws_captions_under_scene_and_leaves_terminal_unchanged(tmp_path):
    from scripts.demo_panel.pipeline import compositor, prepare
    from scripts.demo_panel.render import Layout

    root = make_bundle(tmp_path)
    cmap = tmp_path / "map.json"
    cmap.write_text(json.dumps({"anchors": [[0, 0.0], [19, 140.0]]}))
    lay = Layout()
    p = prepare(root, lay, [_clip(tmp_path)], cmap)
    plain = compositor(p, lay).frame(5.0)
    captioned = compositor(p, lay, captions=["Unresolved failure - take 1 of 3", "second line"])
    img = captioned.frame(5.0)
    assert captioned.layout.scene_box == (40, 92, 800, 600)
    tx, ty, tw, th = lay.term_box
    assert np.array_equal(img[ty : ty + th, tx : tx + tw], plain[ty : ty + th, tx : tx + tw])
    sx, sy, sw, _ = lay.scene_box

    def caption_pixels(frame: np.ndarray) -> int:
        region = frame[sy + 600 : lay.height - 60, sx : sx + sw].astype(int)
        return int((np.abs(region - np.array([240, 214, 120])).sum(axis=2) < 60).sum())

    assert caption_pixels(img) > 50
    assert caption_pixels(plain) == 0
