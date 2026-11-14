"""Unit tests for the improved-annotation stimulus renderer (offline).

Proves, for all 24 scenes: L2 changes pixels only in the robot label/box zone and
then applies the declared fixed crop/upscale (Type L); K1 is L2 plus only the
obstacle outline and its label; renders are deterministic and match the committed
manifest. Reads the stored frames from the main checkout's untracked
`data/logs/vm_runs` (override with `VGU_VM_RUNS_DIR`).
"""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path

import numpy as np
import pytest

from scripts.render_annotation_variants import (
    CROP_BOX,
    EXPECTED_SCENES,
    changed_outside,
    colour_mask,
    crop_upscale,
    k1_zone,
    load_homography,
    load_scenes,
    md5_file,
    overlay_colours,
    pixel_md5,
    png_bytes,
    render_scene,
    robot_pixels,
    type_l_zone,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = Path(
    os.environ.get(
        "VGU_VM_RUNS_DIR", "/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/data/logs/vm_runs"
    )
)
OUT_DIR = REPO_ROOT / "data/experiments/2026-11-14-improved-annotation-replay"
needs_frames = pytest.mark.skipif(
    not (RUNS_DIR / "20260925_063520").is_dir(), reason="stored vm_runs frames not present"
)
# Obstacle top face columns per side (scope measurements), rows 442-518.
TOP_FACE_U = {"west": (128, 204), "east": (1075, 1151)}


@functools.cache
def _scenes():
    return load_scenes(RUNS_DIR)


@functools.cache
def _rendered(key: str):
    artifact = next(a for a in _scenes() if a.request_id.startswith(key))
    return artifact, render_scene(artifact, load_homography())


def test_colour_mask_matches_saturated_status_colours():
    img = np.zeros((1, 3, 3), dtype=np.uint8)
    img[0, 0] = (200, 0, 0)
    img[0, 1] = (200, 200, 0)
    img[0, 2] = (56, 55, 48)
    assert colour_mask(img, (200, 0, 0)).tolist() == [[True, False, False]]
    assert colour_mask(img, (200, 200, 0)).tolist() == [[False, True, False]]


def test_crop_upscale_has_fixed_output_size():
    out = crop_upscale(np.zeros((960, 1280, 3), dtype=np.uint8))
    assert out.shape == (640, 2048, 3)
    assert CROP_BOX == (0, 280, 1280, 680)


@needs_frames
def test_scene_set_is_the_pre_registered_24():
    scenes = _scenes()
    assert tuple(a.request_id[:8] for a in scenes) == EXPECTED_SCENES
    assert sum(a.obstacle_side == "west" for a in scenes) == 12


@needs_frames
@pytest.mark.parametrize("key", EXPECTED_SCENES)
def test_l2_changes_only_robot_zone_before_crop(key):
    artifact, r = _rendered(key)
    px = robot_pixels(artifact, load_homography())
    changed, outside = changed_outside(r.annotated, r.l2_full, [type_l_zone(px)])
    assert changed > 0
    assert outside == 0
    u0, u1 = TOP_FACE_U[artifact.obstacle_side]
    assert np.array_equal(r.annotated[430:530, u0 : u1 + 1], r.l2_full[430:530, u0 : u1 + 1])


@needs_frames
@pytest.mark.parametrize("key", EXPECTED_SCENES)
def test_l2_sent_image_is_the_fixed_crop_upscale(key):
    _, r = _rendered(key)
    assert r.l2.shape == (640, 2048, 3)
    assert np.array_equal(r.l2, crop_upscale(r.l2_full))


@needs_frames
@pytest.mark.parametrize("key", EXPECTED_SCENES)
def test_k1_is_l2_plus_only_outline_and_label(key):
    artifact, r = _rendered(key)
    changed, outside = changed_outside(r.l2_full, r.k1_full, k1_zone(artifact, load_homography()))
    assert changed > 0
    assert outside == 0
    assert np.array_equal(r.k1, crop_upscale(r.k1_full))


@needs_frames
@pytest.mark.parametrize("key", EXPECTED_SCENES)
def test_l2_keeps_each_robot_overlay_colour(key):
    artifact, r = _rendered(key)
    px = robot_pixels(artifact, load_homography())
    assert overlay_colours(r.l2_full, px) == overlay_colours(r.annotated, px)


@needs_frames
@pytest.mark.parametrize("key", EXPECTED_SCENES)
def test_renders_are_deterministic_and_match_manifest(key):
    artifact, r = _rendered(key)
    again = render_scene(artifact, load_homography())
    assert np.array_equal(r.l2, again.l2) and np.array_equal(r.k1, again.k1)
    entry = json.loads((OUT_DIR / "manifest.json").read_text())["scenes"][key]
    assert entry["C_ref"] == md5_file(artifact.image_path)
    for name, img in (("L2", r.l2), ("K1", r.k1)):
        assert entry[f"{name}_pixels"] == pixel_md5(img)
        assert png_bytes(img) == png_bytes(again.l2 if name == "L2" else again.k1)
        stim = OUT_DIR / "stimuli" / f"{key}_{name}.png"
        if stim.is_file():
            assert md5_file(stim) == entry[name]
