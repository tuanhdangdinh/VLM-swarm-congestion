"""VM overlay scenes for the prompt-apparatus smoke (scripts/vm/v2_overlay.py)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from swarm_orchestrator.models import load_config

from scripts.vm.v2_overlay import overlay_orchestrator, overlay_rag

ORCH = Path("ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml")


def _config(scene: str):
    return load_config(yaml.safe_load(overlay_orchestrator(ORCH.read_text(), scene)))


def test_annotation_scene_turns_on_v3_and_the_three_visual_flags():
    config = _config("apparatus_annotation")
    assert config.plan_channel_enabled
    assert config.prompt_metric_grid and config.prompt_motion_trails and config.prompt_zoom_tile
    assert not config.prompt_candidate_options
    assert config.prompt_permutation_votes == 1
    assert config.keep_debug_frames and config.keep_raw_frames


def test_votes_scene_turns_on_only_three_votes():
    config = _config("apparatus_votes")
    assert config.prompt_permutation_votes == 3
    assert not (config.plan_channel_enabled or config.prompt_metric_grid or config.prompt_zoom_tile)
    assert config.keep_debug_frames


@pytest.mark.parametrize("scene", ["apparatus_annotation", "apparatus_votes"])
def test_scenes_set_the_bshort_head_on_goals(scene):
    tasks = _config(scene).initial_tasks
    assert tasks["robot_1"].goal == (2.6, 0.0)
    assert tasks["robot_2"].goal == (-1.5, 0.0)


@pytest.mark.parametrize("scene", ["apparatus_annotation", "apparatus_votes"])
def test_scenes_leave_rag_untouched(scene):
    assert overlay_rag("grounding:\n  mode: derived\n", scene) is None


def test_a_file_without_the_plan_channel_key_gets_it_appended():
    text = ORCH.read_text().replace("plan_channel_enabled: false\n", "")
    overlaid = overlay_orchestrator(text, "apparatus_annotation")
    assert overlaid.rstrip().endswith("prompt_zoom_tile: true")
    assert overlaid.count("plan_channel_enabled: true") == 1


@pytest.mark.parametrize("scene", ["apparatus_annotation", "apparatus_votes"])
def test_overlaying_twice_is_refused(scene):
    once = overlay_orchestrator(ORCH.read_text(), scene)
    with pytest.raises(ValueError):
        overlay_orchestrator(once, scene)


def test_battery_v2_head_on_scene_turns_on_only_the_plan_channel():
    config = _config("battery_v2_head_on")
    assert config.plan_channel_enabled
    assert not (
        config.prompt_metric_grid
        or config.prompt_motion_trails
        or config.prompt_zoom_tile
        or config.prompt_candidate_options
    )
    assert config.prompt_permutation_votes == 1
    assert config.keep_debug_frames and not config.keep_raw_frames
    assert config.initial_tasks["robot_1"].goal == (2.6, 0.0)
    assert config.initial_tasks["robot_2"].goal == (-1.5, 0.0)


def test_battery_v2_head_on_scene_leaves_rag_untouched():
    assert overlay_rag("grounding:\n  mode: derived\n", "battery_v2_head_on") is None


def test_battery_v2_head_on_scene_refuses_a_second_overlay():
    once = overlay_orchestrator(ORCH.read_text(), "battery_v2_head_on")
    with pytest.raises(ValueError):
        overlay_orchestrator(once, "battery_v2_head_on")
