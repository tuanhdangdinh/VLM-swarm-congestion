"""Unit tests for the improved-annotation replay runner and analysis (offline, mocked).

Data-dependent tests read the 24 stored frames from the main checkout's untracked
`data/logs/vm_runs` (override with `VGU_VM_RUNS_DIR`); they skip when it is absent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from reasoning.vlm.models import BackendResponse, ReasonerConfig, StaticObstacleInput
from reasoning.vlm.reasoner import Reasoner
from scripts.analyze_improved_annotation import (
    conditional_rule,
    is_provider_stop_row,
    line_alone_flag,
    line_effect,
    rule1,
)
from scripts.replay_improved_annotation import (
    PLANNED_CELLS,
    PRIORITY,
    PROMPT_LINE,
    PROMPT_LINE_ANCHOR,
    PromptLineProxy,
    base_prompt,
    build_runs,
    cell_prompt,
    image_path_for,
    insert_prompt_line,
    outcome,
    pilot_stopped,
    project_cells,
)
from scripts.replay_live_decisions import Artifact, reconstruct_request, sha256_text

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(
    os.environ.get(
        "VGU_VM_RUNS_DIR", "/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs"
    )
)
OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-improved-annotation-replay"
PREV_CALLS = REPO_ROOT / "data/experiments/2026-11-14-head-on-swapped-id-replay/calls.jsonl"
needs_frames = pytest.mark.skipif(
    not (RUNS_DIR / "20260925_063520").is_dir(), reason="stored vm_runs frames not present"
)

SCENE = {
    "dropped_frame": False,
    "frame_id": "overhead_camera",
    "robots": [
        {
            "linear_velocity": 0.0,
            "robot_id": "robot_2",
            "stamp": 1790322777.5,
            "status": "STOPPED",
            "theta": 3.141592653589793,
            "x": 0.17,
            "y": 0.0,
        },
        {
            "linear_velocity": 0.0,
            "robot_id": "robot_1",
            "stamp": 1790322777.5,
            "status": "STOPPED",
            "theta": 0.0,
            "x": -0.22,
            "y": 0.0,
        },
    ],
    "stamp": 1790322777.5,
}


def _artifact(tmp_path: Path) -> Artifact:
    image = tmp_path / ("ab" * 16 + ".png")
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(image)
    return Artifact(
        run="20260925_075116",
        request_id="ab" * 16,
        path=tmp_path / "a.json",
        image_path=image,
        scene=SCENE,
        failure_context=None,
        stored_order="id_asc",
        stored_user_sha256="",
        stored_system_sha256="",
        stored_user_prompt="",
        include_pairwise_geometry=True,
        include_static_obstacles=True,
        static_obstacles=(
            StaticObstacleInput(
                obstacle_id="obstacle_1", x=1.85, y=0.0, size_x_m=0.3, size_y_m=0.3
            ),
        ),
        obstacle_x=1.85,
        live_parse_status="valid",
        live_attempts=1,
        live_error_message=None,
        live_raw_text=None,
        live_decision=None,
        stamp=1790322777.5,
    )


def _decision(yield_robot: str | None, strategy: str = "yield") -> str:
    return json.dumps(
        {
            "congestion_detected": True,
            "type": "deadlock",
            "involved_robots": ["robot_1", "robot_2"],
            "root_cause": "standoff",
            "strategy": strategy,
            "justification": "x",
            "yield_robot": yield_robot,
        }
    )


class _RecordingBackend:
    def __init__(self, responses):
        self._responses = list(responses)
        self.payloads = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        return self._responses.pop(0)


def test_prompt_line_wording_names_no_scene_fact():
    lowered = PROMPT_LINE.lower()
    for word in ("obstacle", "image", "west", "east", "left", "right", "robot_", "side", "box"):
        assert word not in lowered
    assert PROMPT_LINE == "A robot that backs up needs free floor behind it."


def test_insert_prompt_line_adds_exactly_the_sentence():
    base = f"a\n- x {PROMPT_LINE_ANCHOR}\n- y"
    plus = insert_prompt_line(base)
    assert plus.count(PROMPT_LINE) == 1
    assert plus.replace(" " + PROMPT_LINE, "", 1) == base
    assert len(plus) - len(base) == len(PROMPT_LINE) + 1


def test_insert_prompt_line_rejects_missing_anchor():
    with pytest.raises(ValueError, match="anchor"):
        insert_prompt_line("no anchor here")


def test_insert_prompt_line_rejects_double_insertion():
    with pytest.raises(ValueError, match="already"):
        insert_prompt_line(insert_prompt_line(PROMPT_LINE_ANCHOR))


@pytest.mark.parametrize("line", [True, False])
def test_proxy_sends_line_on_every_attempt_only_in_plus_cells(tmp_path, line):
    artifact = _artifact(tmp_path)
    backend = _RecordingBackend(
        [
            BackendResponse(text="not json", backend_id="mock"),
            BackendResponse(text="", backend_id="mock", refusal=True),
            BackendResponse(text=_decision("robot_1"), backend_id="mock"),
        ]
    )
    proxy = PromptLineProxy(backend, 0.0)
    proxy.prompt_line = line
    config = ReasonerConfig(
        backend_id="openai", max_attempts=4, image_fallback_after_attempts=2, allow_reask=True
    )
    result = Reasoner(proxy, config).run(
        reconstruct_request(artifact, "id_asc", artifact.image_path, False)
    )
    assert result.decision is not None
    assert len(backend.payloads) == 3
    assert result.diagnostics.image_fallback_used
    for payload in backend.payloads:
        assert payload.user_prompt.count(PROMPT_LINE) == (1 if line else 0)
    base = base_prompt(artifact, "id_asc", artifact.image_path)
    sent = backend.payloads[0].user_prompt
    assert sent == (insert_prompt_line(base) if line else base)
    assert proxy.calls[0].user_sha256 == sha256_text(sent)


def test_build_runs_counts_and_determinism(tmp_path):
    scenes = []
    for i in range(24):
        a = _artifact(tmp_path)
        rid = ("810c9104" if i == 0 else "189ae2a6" if i == 1 else f"{i:08d}") + "0" * 24
        scenes.append(a.__class__(**{**a.__dict__, "request_id": rid}))
    for backend, reps in (("openai", 2), ("gemini", 4)):
        pilot, blocks = build_runs(backend, scenes, PLANNED_CELLS)
        assert len(pilot) == len(PLANNED_CELLS) * 4
        keys = [r.key() for r in pilot] + [r.key() for b in blocks for r in b]
        assert len(keys) == len(set(keys)) == len(PLANNED_CELLS) * 48 * reps
        assert len(blocks) == reps
        again = build_runs(backend, scenes, PLANNED_CELLS)
        assert [r.key() for r in again[0]] == [r.key() for r in pilot]
        cells_in_first_20 = {r.cell for r in blocks[0][:20]}
        assert len(cells_in_first_20) > 2


def test_planned_cells_drop_only_k1p():
    assert PLANNED_CELLS == PRIORITY[:-1]
    assert PRIORITY[-1] == "K1+P"


def test_project_cells_cuts_from_bottom():
    rows = [{"cell": c, "pilot": True, "usd": 0.01} for c in PLANNED_CELLS for _ in range(4)]
    kept, log = project_cells("gemini", rows, PLANNED_CELLS, 0.0, 0.03)
    # 0.01 x 1.1 x 188 runs = 2.068 per cell; 2 cells fit under 5.97, 3 do not.
    assert kept == PLANNED_CELLS[:2]
    assert [step["fits"] for step in log][-1] is True


def test_pilot_rule_stops_on_three_failures():
    rows = [
        {
            "cell": "L2",
            "pilot": True,
            "decision": None if i < 3 else {},
            "image_fallback_used": False,
        }
        for i in range(4)
    ]
    assert pilot_stopped(rows, "L2") is True
    assert pilot_stopped(rows[:3], "L2") is None


@pytest.mark.parametrize(
    ("decision", "side", "expected"),
    [
        ({"yield_robot": "robot_2"}, "west", "correct"),
        ({"yield_robot": "robot_1"}, "west", "wrong"),
        ({"yield_robot": "robot_1"}, "east", "correct"),
        ({"yield_robot": None, "strategy": "reverse"}, "east", "no_yielder"),
    ],
)
def test_outcome_scores_physical_robot(decision, side, expected):
    assert outcome(decision, False, None, side) == expected


def _rows(cell, model, correct_fn, scenes=12):
    reps = {"openai": 2, "gemini": 4}[model]
    rows = []
    for side in ("west", "east"):
        for s in range(scenes):
            for order in ("id_asc", "id_desc"):
                for rep in range(reps):
                    ok = correct_fn(side, s, order, rep)
                    rows.append(
                        {
                            "cell": cell,
                            "scene": f"{side}{s}",
                            "side": side,
                            "order": order,
                            "outcome": "correct" if ok else "no_yielder",
                            "decision": {},
                        }
                    )
    return rows


def test_rule1_passes_when_all_cells_meet_thresholds():
    rows = _rows("L2", "openai", lambda *a: True) + _rows("D_ref", "openai", lambda *a: False)
    assert rule1("openai", rows, "L2")["verdict"] == "PASSES"


def test_rule1_fails_on_one_side_order_cell():
    rows = _rows(
        "L2", "openai", lambda side, s, order, rep: not (side == "east" and order == "id_desc")
    )
    rows += _rows("D_ref", "openai", lambda *a: False)
    assert rule1("openai", rows, "L2")["verdict"] == "FAILS"


def test_rule1_scene_clause_binds():
    # ER-2: 5 scenes 2/4 correct and 7 scenes 4/4 give 38/48 runs (>= 36) but only
    # 7 of 12 scenes with >= 3/4, so the scene clause alone fails the cell.
    def fn(side, s, order, rep):
        return rep < 2 if s < 5 else True

    rows = _rows("L2", "gemini", fn) + _rows("D_ref", "gemini", lambda *a: False)
    res = rule1("gemini", rows, "L2")
    assert res["verdict"] == "FAILS"
    assert "7/12 scenes" in res["detail"]["west/id_asc"]


def test_rule1_margin_against_control():
    rows = _rows("L2", "openai", lambda *a: True) + _rows("D_ref", "openai", lambda *a: True)
    assert rule1("openai", rows, "L2")["margin_ok"] is False


def test_rule1_not_assessable_when_incomplete():
    rows = _rows("L2", "openai", lambda *a: True, scenes=10) + _rows(
        "D_ref", "openai", lambda *a: False
    )
    assert rule1("openai", rows, "L2")["verdict"].startswith("NOT ASSESSABLE")


def test_rule1_plus_cell_uses_plus_control():
    rows = _rows("L2+P", "openai", lambda *a: True) + _rows("D_ref+P", "openai", lambda *a: True)
    rows += _rows("D_ref", "openai", lambda *a: False)
    res = rule1("openai", rows, "L2+P")
    assert res["control"] == "D_ref+P"
    assert res["verdict"] == "FAILS"


def test_conditional_rule_not_assessable_with_few_named():
    rows = _rows("L2", "gemini", lambda side, s, order, rep: s == 0 and rep == 0)
    rows += _rows("D_ref", "gemini", lambda *a: False)
    assert conditional_rule("gemini", rows, "L2")["verdict"].startswith("NOT ASSESSABLE")


def test_conditional_rule_passes_with_enough_correct_named():
    rows = _rows("L2", "gemini", lambda side, s, order, rep: s < 6 and rep < 1)
    rows += _rows("D_ref", "gemini", lambda *a: False)
    # 6 scenes x 2 orders x 1 rep = 12 named per side, 6 per order, all correct.
    assert conditional_rule("gemini", rows, "L2")["verdict"] == "PASSES"


def test_line_alone_flag_detects_side_bias_shift():
    def west_only(side, *a):
        return side == "west"

    rows = _rows("D_ref+P", "openai", west_only) + _rows("D_ref", "openai", lambda *a: False)
    flag = line_alone_flag(line_effect(rows, "D_ref+P", "D_ref"))
    assert flag.startswith("FLAG")


@needs_frames
def test_all_prompts_are_text_off_and_plus_differs_by_one_sentence():
    from scripts.render_annotation_variants import load_scenes

    manifest = json.loads((OUT_DIR / "manifest.json").read_text())
    for a in load_scenes(RUNS_DIR):
        key = a.request_id[:8]
        for order in ("id_asc", "id_desc"):
            base = base_prompt(a, order, a.image_path)
            plus = cell_prompt(a, order, a.image_path, True)
            assert "obstacle" not in base.lower() and "1.85" not in base
            assert "obstacle" not in plus.lower() and "1.85" not in plus
            assert PROMPT_LINE not in base
            assert plus.count(PROMPT_LINE) == 1
            assert plus.replace(" " + PROMPT_LINE, "", 1) == base
            for variant in ("grey", "L2", "K1"):
                assert base_prompt(a, order, image_path_for(variant, a, OUT_DIR)) == base
            entry = manifest["scenes"][key]["prompts"][order]
            assert entry["base_sha256"] == sha256_text(base)
            import hashlib

            assert entry["base"] == hashlib.md5(base.encode()).hexdigest()  # noqa: S324
            assert entry["plus"] == hashlib.md5(plus.encode()).hexdigest()  # noqa: S324


@needs_frames
def test_original_12_prompts_equal_earlier_replay_text_off_prompts():
    manifest = json.loads((OUT_DIR / "manifest.json").read_text())
    prev = [json.loads(line) for line in PREV_CALLS.read_text().splitlines() if line.strip()]
    pairs = {
        (r["scene"], r["order"]): r["prompt_user_sha256"]
        for r in prev
        if r["arm"] in ("C_real_notext", "D_grey_notext")
    }
    assert len(pairs) == 24
    for (scene, order), sha in pairs.items():
        assert manifest["scenes"][scene]["prompts"][order]["base_sha256"] == sha


def test_conditional_rule_not_assessable_when_cell_incomplete():
    rows = _rows("L2", "gemini", lambda side, s, order, rep: rep < 1, scenes=10)
    rows += _rows("D_ref", "gemini", lambda *a: False)
    assert conditional_rule("gemini", rows, "L2")["verdict"].startswith("NOT ASSESSABLE")


def test_line_alone_flag_not_assessable_when_incomplete():
    rows = _rows("D_ref+P", "openai", lambda side, *a: side == "west") + _rows(
        "D_ref", "openai", lambda *a: False
    )
    effect = line_effect(rows, "D_ref+P", "D_ref")
    assert line_alone_flag(effect, complete=False).startswith("NOT ASSESSABLE")


def test_provider_stop_row_is_not_a_data_point():
    assert is_provider_stop_row({"decision": None, "provider_stop": "HTTP 429 (quota/credit)"})
    assert not is_provider_stop_row({"decision": None, "provider_stop": None})
    assert not is_provider_stop_row({"decision": {}, "provider_stop": "x"})
