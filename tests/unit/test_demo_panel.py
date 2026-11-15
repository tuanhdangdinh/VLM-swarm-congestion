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
from scripts.demo_panel.pipeline import load_clip_map, run_caption
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


def test_run_caption_uses_variant_and_omits_missing_arm(tmp_path):
    root = make_bundle(tmp_path)
    (root / "CONDITION.txt").write_text(
        "variant=head_on_x side=west label=ER2LIVE backend=gemini\n"
    )
    cap = run_caption(load_bundle(root))
    assert cap.startswith("ER2LIVE  |  head_on_x  |  backend gemini")
    assert "None" not in cap and "arm" not in cap


def test_run_caption_keeps_scenario_and_arm(tmp_path):
    cap = run_caption(load_bundle(make_bundle(tmp_path)))
    assert "arm A" in cap and "backend gemini" in cap


# Presentation profile ---------------------------------------------------------------

from scripts.demo_panel import presentation as pr  # noqa: E402
from scripts.demo_panel.present_render import (  # noqa: E402
    PresentPane,
    validate_crop,
    zoom_factor,
)

GATE_LINE = f"[orchestrator_node-1] [INFO] [1794638425.014500000] [orchestrator_node]: yield re-grounded request={REQ} from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible"
PLAN_DECISION = json.loads(json.dumps(DECISION))
PLAN_DECISION["decision"].update(
    proposed_plan=[
        {"robot_id": "robot_3", "action": "reverse"},
        {"robot_id": "robot_1", "action": "yield"},
    ],
    crossing_order=["robot_2", "robot_1"],
    congestion_detected=True,
)
PLAN_DECISION["plan"] = {"provenance": "vlm_verbatim", "rejection_reason": None}
PLAN_DECISION["dispatch_order_source"] = "model"
PLAN_DECISION["diagnostics"]["token_usage"]["input_tokens_image"] = 1064


def _present(tmp_path: Path, decision: dict | None = None, gate: bool = True):
    m5 = M5_LINES[:6] + ([GATE_LINE] if gate else []) + M5_LINES[6:]
    root = make_bundle(tmp_path, decision=PLAN_DECISION if decision is None else decision, m5=m5)
    (root / "frames").mkdir()
    (root / "frames" / f"{REQ}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    b = load_bundle(root)
    return root, b, pr.build_present_transcript(b, build_time_map(b, load_gt(b)), 150.0)


def test_present_filter_sed_output_equals_python_shortening(tmp_path):
    root, _, _ = _present(tmp_path)
    raw = run_shell(pr.raw_filter_command(), root)
    shown = run_shell(pr.present_filter_command(), root)
    assert len(raw) == len(shown) and raw
    assert shown == [pr.shorten_line(r) for r in raw]


def test_shorten_line_strips_prefix_and_keeps_first_eight_hex_of_ids():
    out = pr.shorten_line(M5_LINES[6])
    assert out == (
        "orchestrator: dispatch request=18c2a25e command=18c2a25e-junction-recede-robot_4 "
        "robot=robot_4 plan_id=1"
    )


def test_present_filter_adds_gate_lines_to_the_engineering_filter(tmp_path):
    root, _, _ = _present(tmp_path)
    eng = run_shell(filter_command(), root)
    raw = run_shell(pr.raw_filter_command(), root)
    assert [ln for ln in raw if ln not in eng] == [GATE_LINE]


def test_present_transcript_log_items_are_the_displayed_filter_output(tmp_path):
    root, _, pt = _present(tmp_path)
    shown = run_shell(pt.transcript.filter_command, root)
    logs = [it.text for it in pt.transcript.items if it.kind == "log"]
    markers = [it.text for it in pt.transcript.items if it.kind == "marker"]
    assert logs and all(t in shown for t in logs)
    assert len(shown) - len(logs) == 3 and markers == ["[… 3 similar 'safety stop' lines]"]


def test_present_transcript_times_lines_like_the_engineering_transcript(tmp_path):
    root, b, pt = _present(tmp_path, gate=False)
    eng = build_transcript(b, build_time_map(b, load_gt(b)), 150.0)
    e = [(it.sim_time, it.source) for it in eng.items if it.kind in ("log", "marker")]
    p = [(it.sim_time, it.source) for it in pt.transcript.items if it.kind in ("log", "marker")]
    assert e == p


def test_present_block_output_matches_running_the_shown_commands(tmp_path):
    root, _, pt = _present(tmp_path)
    items = pt.transcript.items
    cmds = [i for i, it in enumerate(items) if it.kind == "command"]
    assert cmds
    for i in cmds:
        shown = []
        for it in items[i + 1 :]:
            if it.kind != "output":
                break
            shown.append(it.text)
        direct = subprocess.run(
            ["bash", "-c", items[i].text[2:]], cwd=root, capture_output=True, text=True
        )
        assert shown == direct.stdout.splitlines()


def test_present_block_prints_plan_and_crossing_order(tmp_path):
    _, _, pt = _present(tmp_path)
    texts = [it.text for it in pt.transcript.items]
    assert "plan: robot_3 reverse, robot_1 yield" in texts
    assert "crossing_order: robot_2, robot_1" in texts
    assert "provenance=vlm_verbatim reason=null dispatch_order_source=model" in texts


def test_present_block_prints_null_when_parser_nulled_the_plan(tmp_path):
    dec = json.loads(json.dumps(PLAN_DECISION))
    dec["decision"]["proposed_plan"] = None
    dec["decision"]["crossing_order"] = None
    _, _, pt = _present(tmp_path, decision=dec)
    texts = [it.text for it in pt.transcript.items]
    assert "plan: null" in texts and "crossing_order: null" in texts


def test_present_block_without_plan_prints_yield_robot_and_gate_field(tmp_path):
    dec = json.loads(json.dumps(PLAN_DECISION))
    dec["plan"] = None
    dec["decision"]["yield_robot"] = "robot_1"
    dec["yield_robot_grounded_from"] = "robot_1"
    _, _, pt = _present(tmp_path, decision=dec)
    texts = [it.text for it in pt.transcript.items]
    assert "yield_robot: robot_1" in texts
    assert '{"yield_robot_grounded_from":"robot_1","dispatch_order_source":"model"}' in texts


def test_present_block_never_prints_dispatched_robot_ids(tmp_path):
    _, _, pt = _present(tmp_path)
    assert not any(
        "dispatch_order=" in it.text or "dispatched_robot_ids" in it.text
        for it in pt.transcript.items
    )


def test_present_block_proves_image_input_with_file_and_image_tokens(tmp_path):
    _, _, pt = _present(tmp_path)
    texts = [it.text for it in pt.transcript.items]
    assert f"$ file -b frames/{REQ}.png" in texts
    assert any('"image_tokens":1064' in t for t in texts)


def test_present_block_skips_plan_and_check_when_no_congestion(tmp_path):
    dec = json.loads(json.dumps(PLAN_DECISION))
    dec["decision"]["congestion_detected"] = False
    _, _, pt = _present(tmp_path, decision=dec)
    roles = {t.split(":", 1)[1] for t in pt.tags if ":" in t}
    assert roles == {"request", "response"}


def test_present_block_uses_full_path_when_prefix_glob_is_ambiguous(tmp_path):
    root, b, _ = _present(tmp_path)
    (root / "decisions" / f"{REQ[:8]}ffff.json").write_text("{}")
    cmds = pr.present_block(load_bundle(root), REQ, PLAN_DECISION)
    assert all(f"decisions/{REQ}.json" in c.command for c in cmds if "decisions/" in c.command)


def test_present_style_dims_safety_stops_and_highlights_actions_and_checks():
    assert pr.present_style(M4_LINES[1], pr.shorten_line(M4_LINES[1])) == "dim"
    assert pr.present_style(M4_LINES[6], pr.shorten_line(M4_LINES[6])) == "action"
    assert pr.present_style(GATE_LINE, pr.shorten_line(GATE_LINE)) == "check"
    assert pr.present_style(M5_LINES[2], pr.shorten_line(M5_LINES[2])) == "m5"


@pytest.mark.parametrize(
    ("tag", "text", "stage"),
    [
        ("log", "orchestrator: starting analysis request=1 robots=[]", "Trigger"),
        ("log", "orchestrator: decision artifact written: x.json", "VLM request"),
        ("x:request", "anything", "VLM request"),
        ("x:response", "anything", "VLM response"),
        ("x:check", "anything", "Check"),
        ("log", "orchestrator: yield re-grounded request=1", "Check"),
        ("log", "orchestrator: dispatch request=1 command=c robot=r", "Dispatch"),
        ("log", "command_bus: command received command=c robot=r action=yield", "Dispatch"),
        ("log", "command_bus: crossing_chain gate_admit command=c", "Execution"),
        ("log", "orchestrator: robot robot_1 arrived at base goal (0, 0)", "Execution"),
        ("log", "safety_monitor: safety stop robot=robot_1 reason=x", None),
        ("log", "safety_monitor: exempt pairs changed pairs=-", None),
        ("poll", "02:19:49 analyses=1", None),
    ],
)
def test_item_stage_maps_anchor_to_stage(tag, text, stage):
    assert pr.item_stage(tag, text)[0] == stage


def test_item_stage_marks_withheld_and_no_dispatch_as_cycle_end():
    assert pr.item_stage("log", "orchestrator: request=1 no dispatch stage=vlm") == ("Check", True)
    assert pr.item_stage("log", "orchestrator: refusal withheld request=1") == ("Check", True)


def test_stage_at_is_none_before_first_trigger():
    assert pr.stage_at(0.5, [1.0, 2.0], ["Trigger", "Dispatch"], [False, False]) is None


def test_stage_at_turns_trigger_into_request_after_delay():
    rev, st, ends = [1.0], ["Trigger"], [False]
    assert pr.stage_at(1.0 + pr.TRIGGER_SEC - 0.1, rev, st, ends) == "Trigger"
    assert pr.stage_at(1.0 + pr.TRIGGER_SEC + 0.1, rev, st, ends) == "VLM request"


def test_stage_at_turns_dispatch_into_execution_after_delay():
    rev, st, ends = [1.0], ["Dispatch"], [False]
    assert pr.stage_at(1.0 + pr.DISPATCH_SEC + 0.1, rev, st, ends) == "Execution"


def test_stage_at_goes_idle_after_cycle_without_dispatch():
    rev, st, ends = [1.0, 2.0], ["Trigger", "Check"], [False, True]
    assert pr.stage_at(2.5, rev, st, ends) == "Check"
    assert pr.stage_at(2.0 + pr.IDLE_AFTER_SEC + 0.1, rev, st, ends) is None


def test_stage_at_skips_items_without_stage():
    assert pr.stage_at(5.0, [1.0, 4.0], ["Check", None], [False, False]) == "Check"


def test_compute_holds_after_model_answer_and_after_gate_line(tmp_path):
    _, _, pt = _present(tmp_path)
    items = pt.transcript.items
    held = [(items[i].text, h) for i, h in enumerate(pt.holds) if h > 0]
    assert held == [
        ("crossing_order: robot_2, robot_1", pr.RESPONSE_HOLD_SEC),
        (pr.shorten_line(GATE_LINE), pr.CHECK_HOLD_SEC),
    ]


def test_present_timeline_holds_sim_clock_through_response_hold(tmp_path):
    from scripts.demo_panel.pipeline import present_timeline_items
    from scripts.demo_panel.present_render import hold_windows

    _, _, pt = _present(tmp_path)
    pane = PresentPane(pt.transcript, (1208, 772), 20, 14)
    calls = [CallSpan(a, s, w) for a, s, w in pt.transcript.calls]
    tl = build_timeline(present_timeline_items(pt, pane), calls, 150.0)
    (i, a, b), _ = hold_windows(tl, pt.holds)
    assert b - a >= pr.RESPONSE_HOLD_SEC
    assert tl.sim_at(a + 0.1) == pytest.approx(tl.sim_at(b - 0.1))


def test_present_pane_never_shows_more_rows_than_fit(tmp_path):
    _, _, pt = _present(tmp_path)
    pane = PresentPane(pt.transcript, (1208, 772), 20, 14)
    assert pane.body_rows <= 30
    assert len(pane.visible_rows(len(pt.transcript.items))) <= pane.body_rows


def _anchor(**kw) -> pr.Anchor:
    return pr.Anchor(**kw)


def test_anchor_requires_exactly_one_kind():
    with pytest.raises(ValueError):
        pr.Anchor(match="x", start=True)
    with pytest.raises(ValueError):
        pr.Anchor()


def test_anchor_time_raises_when_match_is_missing():
    with pytest.raises(ValueError, match="only 0"):
        pr.anchor_time(_anchor(match="arrived"), ["a", "b"], [1.0, 2.0], 9.0)


def test_caption_is_not_shown_before_its_anchor_line():
    texts = ["starting analysis", "x", "robot robot_2 arrived at base goal"]
    reveal = [1.0, 2.0, 30.0]
    caps = [
        pr.Caption(at=_anchor(start=True), text="driving"),
        pr.Caption(at=_anchor(match="arrived at base goal"), text="4 of 4 arrived"),
    ]
    sched = pr.caption_schedule(caps, texts, reveal, 40.0)
    assert pr.caption_at(sched, 29.9) == "driving"
    assert pr.caption_at(sched, 30.0) == "4 of 4 arrived"


def test_anchor_end_fires_at_end_hold():
    assert pr.anchor_time(_anchor(end=True), ["a"], [1.0], 55.0) == 55.0


def test_validate_crop_rejects_crop_outside_frame_or_not_four_by_three():
    validate_crop((0, 0, 256, 192), (1280, 960))
    with pytest.raises(ValueError, match="outside"):
        validate_crop((1100, 0, 256, 192), (1280, 960))
    with pytest.raises(ValueError, match="4:3"):
        validate_crop((0, 0, 256, 256), (1280, 960))


def test_zoom_factor_is_relative_to_the_full_camera_view():
    assert zoom_factor(192, 384, 640, 1280) == pytest.approx(4.0)


SCRIPT = {
    "header": "h",
    "camera_label": "c",
    "intro_title": "t",
    "intro_lines": ["l"],
    "watch_for": ["w"],
    "captions": [{"at": {"start": True}, "text": "driving"}],
    "outcome": {"at": {"match": "phase advance"}, "text": "Outcome: X"},
    "legend": "g",
    "disclosure": "Illustrative demo, not controlled experimental evidence.",
    "outro_title": "o",
    "outro_lines": ["o"],
    "zooms": [{"start": {"start": True}, "stop": {"end": True}, "crop": [0, 0, 32, 24]}],
    "outcome_kind": "VLM-driven execution",
}


def test_present_compositor_reveals_outcome_only_at_its_anchor(tmp_path):
    from scripts.demo_panel.pipeline import prepare_present
    from scripts.demo_panel.present_render import INTRO_SEC, PresentCompositor

    root, _, _ = _present(tmp_path)
    cmap = tmp_path / "map.json"
    cmap.write_text(json.dumps({"anchors": [[0, 0.0], [19, 140.0]]}))
    p = prepare_present(root, [_clip(tmp_path)], cmap)
    comp = PresentCompositor(
        p.pt, p.timeline, p.scene, p.pane, pr.PresentScript.model_validate(SCRIPT)
    )
    k = next(i for i, it in enumerate(p.pt.transcript.items) if "phase advance" in it.text)
    assert comp.outcome_t == pytest.approx(p.timeline.reveal[k])
    assert comp.outcome_t > max(p.timeline.reveal[:k])
    before = comp.frame(INTRO_SEC + comp.outcome_t - 0.5)
    after = comp.frame(INTRO_SEC + comp.outcome_t + 0.5)
    band = slice(comp.lay.band_top, comp.lay.height)
    assert not np.array_equal(before[band], after[band])
    assert comp.total_sec == pytest.approx(INTRO_SEC + p.timeline.total_video_sec + 10.0)
