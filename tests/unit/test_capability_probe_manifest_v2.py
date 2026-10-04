"""Battery-v2 manifest contracts, v1 freeze isolation, and the runner's arm filter."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from reasoning.vlm.capability_probes.letters import build_item_choices
from reasoning.vlm.capability_probes.manifest_io import load_any_manifest, sha256_file
from reasoning.vlm.capability_probes.models import ProbeManifest
from reasoning.vlm.capability_probes.models_v2 import ProbeItemV2, ProbeManifestV2
from reasoning.vlm.capability_probes.prompt import (
    CAPABILITY_PROBE_PROMPT_VERSION,
    build_capability_probe_prompt_payload,
)
from scripts.build_capability_probe_manifest_v2 import build_manifest
from scripts.capability_probes import run_battery, select_items
from tests.unit.conftest import CAPABILITY_PROBE_CALIBRATION_PATH as _CALIBRATION_PATH
from tests.unit.test_build_capability_probe_manifest_v2 import _write_episode

_V1_MANIFEST = Path("reasoning/vlm/capability_probes/manifest_v1.json")
_V1_SHA256 = "9659782d710a5c286b420fe17e256d8045eac3459638a4714b8757f51b34dbdb"


def _item(**overrides) -> ProbeItemV2:
    fields = dict(
        item_id="main_conflict_prediction_000",
        probe_type="conflict_prediction",
        subset="main",
        frame_condition="trails_off",
        run_id="h/off",
        scenario="s",
        frame_source="snapshot",
        frame_ref="annotated_00010.00.png",
        frame_relpath="h/off/snapshots/annotated_00010.00.png",
        frame_sha256="0" * 64,
        image_width=1280,
        image_height=960,
        sim_time_sec=10.0,
        gt_sim_time_sec=10.0,
        question_key="robot_1|robot_2",
        question="Will robots robot_1 and robot_2 come within 0.5 m?",
        options=["yes", "no"],
        correct_answer="yes",
        seed=3,
        m1_gt_max_disagreement_m=0.0,
    )
    fields.update(overrides)
    return ProbeItemV2(**fields)


def test_v1_manifest_is_byte_frozen():
    assert sha256_file(_V1_MANIFEST) == _V1_SHA256


def test_v1_manifest_still_loads_as_v1():
    manifest = load_any_manifest(_V1_MANIFEST)
    assert isinstance(manifest, ProbeManifest)
    assert len(manifest.items) == 60


def test_main_items_must_be_unpaired_trails_off():
    with pytest.raises(ValidationError):
        _item(frame_condition="trails_on")
    with pytest.raises(ValidationError):
        _item(pair_id="pair_x")


def test_pair_items_require_a_pair_id():
    with pytest.raises(ValidationError):
        _item(subset="trails_pair")


def test_correct_answer_must_be_an_option():
    with pytest.raises(ValidationError):
        _item(correct_answer="maybe")


def test_pair_members_must_agree_on_question_answer_and_seed():
    off = _item(item_id="p_off", subset="trails_pair", pair_id="p")
    on = _item(
        item_id="p_on", subset="trails_pair", pair_id="p", frame_condition="trails_on", seed=4
    )
    with pytest.raises(ValidationError):
        ProbeManifestV2(seed=1, items=[off, on])
    on_ok = _item(item_id="p_on", subset="trails_pair", pair_id="p", frame_condition="trails_on")
    assert len(ProbeManifestV2(seed=1, items=[off, on_ok]).items) == 2


def test_a_pair_needs_both_conditions():
    off = _item(item_id="p_off", subset="trails_pair", pair_id="p")
    with pytest.raises(ValidationError):
        ProbeManifestV2(seed=1, items=[off])


def test_yes_no_item_renders_through_the_frozen_v1_template():
    item = _item()
    choices = build_item_choices(item.options, item.correct_answer, item.seed)
    payload = build_capability_probe_prompt_payload(
        question=item.question,
        choices=choices,
        image_path="x.png",
        image_choices=False,
        known_robot_ids=[],
    )
    assert CAPABILITY_PROBE_PROMPT_VERSION == 1
    assert item.question in payload.user_prompt
    for letter, option in choices.option_by_letter.items():
        assert f"{letter}: {option}" in payload.user_prompt


@pytest.fixture
def v2_manifest(tmp_path: Path) -> tuple[Path, Path]:
    _write_episode(tmp_path, "off", [])
    _write_episode(tmp_path, "on", ["motion_trails"])
    manifest, _, _ = build_manifest(
        tmp_path, _CALIBRATION_PATH, seed=7, target_main=4, target_pairs=3, max_per_scene=10
    )
    path = tmp_path / "manifest_v2.json"
    path.write_text(manifest.model_dump_json(indent=2) + "\n")
    return path, tmp_path


def test_select_items_filters_one_arm(v2_manifest):
    path, _ = v2_manifest
    manifest = load_any_manifest(path)
    on = select_items(manifest, {"subset": "trails_pair", "frame_condition": "trails_on"})
    assert on and all(i.frame_condition == "trails_on" and i.subset == "trails_pair" for i in on)
    assert len(select_items(manifest, None)) == len(manifest.items)


def test_select_items_rejects_filters_on_v1():
    with pytest.raises(ValueError):
        select_items(load_any_manifest(_V1_MANIFEST), {"subset": "main"})


def test_runner_scores_a_v2_arm_with_the_mock_backend(v2_manifest, tmp_path):
    path, logs_root = v2_manifest
    records, summary = run_battery(
        path, "mock", logs_root, tmp_path / "out", item_filter={"subset": "main"}
    )
    assert records and all(
        r.probe_type in {"motion_direction", "conflict_prediction", "temporal_order"}
        for r in records
    )
    assert summary["manifest_version"] == 2
    assert summary["item_filter"] == {"subset": "main"}
    assert summary["prompt_version"] == 1
