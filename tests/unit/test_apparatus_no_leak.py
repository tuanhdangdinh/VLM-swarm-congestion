"""No prompt-apparatus text or image can reach Arm B or the capability-probe battery.

Both are structurally outside the apparatus: neither imports the stage-1
prompt builder, and the probe battery builds its own `PromptPayload` with no
extra image. These checks pin that, so a later refactor that routed either
through `prompt_builder` would fail here rather than leak an A/B condition
into a registered comparator or the frozen probe set.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from reasoning.vlm.capability_probes import prompt as probe_prompt
from reasoning.vlm.prompt_builder import (
    _CANDIDATE_OPTIONS_HEADER,
    _METRIC_GRID_SENTENCE,
    _MOTION_TRAILS_SENTENCE,
    _ZOOM_TILE_SENTENCE,
)

_ISOLATED_SOURCES = [
    *sorted(Path("reasoning/baselines").glob("*.py")),
    Path("ros2_ws/src/swarm_orchestrator/swarm_orchestrator/shadow_classical.py"),
    *sorted(Path("reasoning/vlm/capability_probes").glob("*.py")),
    Path("scripts/capability_probes.py"),
]
_APPARATUS_NAMES = {
    "prompt_metric_grid",
    "prompt_motion_trails",
    "prompt_zoom_tile",
    "prompt_permutation_votes",
    "prompt_candidate_options",
    "metric_grid_spacing_m",
    "motion_trails_drawn",
    "zoom_tile_path",
    "candidate_options",
    "extra_image_paths",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


@pytest.mark.parametrize("path", _ISOLATED_SOURCES, ids=str)
def test_isolated_module_never_imports_the_stage1_prompt_builder(path: Path):
    assert "reasoning.vlm.prompt_builder" not in _imports(path)


@pytest.mark.parametrize("path", _ISOLATED_SOURCES, ids=str)
def test_isolated_module_never_names_an_apparatus_field(path: Path):
    source = path.read_text()
    assert not [name for name in _APPARATUS_NAMES if name in source]


def test_probe_payload_carries_no_extra_image():
    source = Path(probe_prompt.__file__).read_text()
    for sentence in (
        _METRIC_GRID_SENTENCE.split("{")[0],
        _MOTION_TRAILS_SENTENCE,
        _ZOOM_TILE_SENTENCE,
        _CANDIDATE_OPTIONS_HEADER,
    ):
        assert sentence not in source
