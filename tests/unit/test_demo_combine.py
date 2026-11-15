"""Unit tests for `scripts/demo_panel/combine.py` (manifest, layout, trim, sidecar)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from scripts.demo_panel.combine import (
    BAR_HEIGHT,
    DISCLAIMER,
    OUTCOMES,
    ClipInfo,
    ClipSpec,
    ManifestError,
    Trim,
    caption_text,
    card_lines,
    combine,
    letterbox_rect,
    outcome_card_lines,
    output_size,
    parse_manifest,
    probe_clip,
    resolve_trim,
    source_index,
    trim_text,
)


def _clip(**kw: object) -> dict:
    base = {"path": "a.mp4", "title": "T", "outcome": OUTCOMES[0], "take": "take 2 of 5"}
    base.update(kw)
    return base


def _spec(**kw: object) -> ClipSpec:
    return ClipSpec.model_validate(_clip(**kw))


def test_parse_manifest_accepts_all_three_outcomes() -> None:
    m = parse_manifest({"clips": [_clip(outcome=o) for o in OUTCOMES]})
    assert [c.outcome for c in m.clips] == list(OUTCOMES)


def test_parse_manifest_rejects_unknown_outcome() -> None:
    with pytest.raises(ManifestError, match="unknown outcome label"):
        parse_manifest({"clips": [_clip(outcome="Success")]})


def test_parse_manifest_rejects_missing_take_and_unknown_key() -> None:
    bad = _clip()
    del bad["take"]
    with pytest.raises(ManifestError, match="take"):
        parse_manifest({"clips": [bad]})
    with pytest.raises(ManifestError, match="Extra inputs"):
        parse_manifest({"clips": [_clip(crop=[0, 0, 1, 1])]})


def test_parse_manifest_rejects_empty_clip_list() -> None:
    with pytest.raises(ManifestError):
        parse_manifest({"clips": []})


def test_resolve_trim_defaults_to_full_clip() -> None:
    t = resolve_trim(_spec(), 10.0)
    assert (t.start, t.end, t.trimmed) == (0.0, 10.0, False)
    assert trim_text(t) == "full clip"


def test_resolve_trim_rejects_end_past_source_and_empty_range() -> None:
    with pytest.raises(ManifestError, match="exceeds"):
        resolve_trim(_spec(end=20), 10.0)
    with pytest.raises(ManifestError, match="not before"):
        resolve_trim(_spec(start=8, end=5), 10.0)


def test_trim_text_states_excerpt_bounds() -> None:
    t = resolve_trim(_spec(start=12, end=95), 114.58)
    assert trim_text(t) == "excerpt 12-95 s of 114.6 s"


def test_trim_text_shows_start_only_cut() -> None:
    t = resolve_trim(_spec(start=5), 86.4)
    assert trim_text(t) == "excerpt 5-86.4 s of 86.4 s"


def test_caption_text_carries_title_outcome_take_and_trim() -> None:
    t = resolve_trim(_spec(start=12, end=95), 114.58)
    text = caption_text(_spec(title="4-robot intersection"), t, 200)
    assert text == (
        "4-robot intersection | VLM-driven execution | take 2 of 5 | excerpt 12-95 s of 114.6 s"
    )


def test_caption_text_shortens_only_the_title_when_narrow() -> None:
    t = resolve_trim(_spec(start=12, end=95), 114.58)
    text = caption_text(_spec(title="x" * 80), t, 110)
    assert len(text) <= 110
    assert text.endswith("| VLM-driven execution | take 2 of 5 | excerpt 12-95 s of 114.6 s")
    assert "..." in text


def test_card_lines_include_note_and_fixed_line() -> None:
    rows = card_lines(_spec(note="gridlock then yield"))
    assert ("note", "gridlock then yield") in rows
    assert rows[-1] == ("fixed", DISCLAIMER)
    assert all(r[0] != "note" for r in card_lines(_spec()))
    assert DISCLAIMER == "Illustrative demonstration, not controlled experimental evidence."


def test_output_size_uses_largest_source_and_adds_bar_outside() -> None:
    infos = [ClipInfo(1920, 1080, 24, 10), ClipInfo(1280, 720, 30, 10)]
    assert output_size(infos) == (1920, 1080, 1080 + BAR_HEIGHT)
    assert output_size(infos, (1001, 501)) == (1002, 502, 502 + BAR_HEIGHT)


def test_letterbox_rect_preserves_aspect_and_never_crops() -> None:
    assert letterbox_rect((1920, 1080), (1920, 1080)) == (0, 0, 1920, 1080)
    x, y, w, h = letterbox_rect((1280, 960), (1920, 1080))
    assert (w, h) == (1440, 1080) and x == 240 and y == 0
    x, y, w, h = letterbox_rect((1000, 2000), (1920, 1080))
    assert h == 1080 and w == 540 and w <= 1920


def test_source_index_resamples_and_clamps() -> None:
    tr = Trim(2.0, 4.0, 10.0)
    assert source_index(0, 24, tr, 30, 300) == 60
    assert source_index(24, 24, tr, 30, 300) == 90
    assert source_index(0, 24, Trim(0, 10, 10), 30, 300) == 0
    assert source_index(10_000, 24, tr, 30, 300) == 299


def _write_video(path: Path, size: tuple[int, int], fps: float, n: int) -> None:
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for i in range(n):
        f = np.zeros((size[1], size[0], 3), np.uint8)
        f[:] = (10 + i * 3 % 200, 80, 160)
        w.write(f)
    w.release()


def test_probe_clip_rejects_missing_and_unreadable(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="not found"):
        probe_clip(tmp_path / "nope.mp4")
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(ManifestError, match="unreadable"):
        probe_clip(bad)


def test_combine_writes_video_and_sidecar_with_md5_and_trim(tmp_path: Path) -> None:
    import hashlib

    a, b = tmp_path / "a.mp4", tmp_path / "b.mp4"
    _write_video(a, (320, 240), 10, 30)
    _write_video(b, (200, 300), 25, 50)
    man = tmp_path / "m.json"
    man.write_text(
        json.dumps(
            {
                "clips": [
                    _clip(path="a.mp4", start=1, end=2.5, note="n"),
                    _clip(path="b.mp4", outcome=OUTCOMES[2]),
                ]
            }
        )
    )
    out = tmp_path / "out.mp4"
    sidecar, dur = combine(man, out, fps=10, card_sec=1.0, font=None)
    side = json.loads(sidecar.read_text())
    assert side["clips"][0]["md5"] == hashlib.md5(a.read_bytes()).hexdigest()
    assert side["clips"][0]["trim"]["caption"].startswith("excerpt 1-2.5 s")
    assert side["clips"][1]["trim"]["trimmed"] is False
    assert side["clips"][1]["outcome"] == OUTCOMES[2]
    assert side["output_size"] == [320, 300 + BAR_HEIGHT]
    info = probe_clip(out)
    assert (info.width, info.height) == (320, 300 + BAR_HEIGHT)
    assert dur == pytest.approx(1.0 + 1.5 + 1.0 + 2.0)
    assert abs(info.duration - dur) < 0.3


def test_combine_fails_before_encoding_on_missing_clip(tmp_path: Path) -> None:
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"clips": [_clip(path="missing.mp4")]}))
    out = tmp_path / "out.mp4"
    with pytest.raises(ManifestError, match="not found"):
        combine(man, out)
    assert not out.exists()


def test_after_mode_leaves_outcome_off_card_and_bar() -> None:
    spec = _spec(note="n")
    t = resolve_trim(spec, 10.0)
    assert all(OUTCOMES[0] not in text for _, text in card_lines(spec, "after"))
    assert OUTCOMES[0] not in caption_text(spec, t, 200, "after")
    assert OUTCOMES[0] in caption_text(spec, t, 200)


def test_outcome_card_names_outcome_take_and_fixed_line() -> None:
    rows = outcome_card_lines(_spec(outcome_note="2 of 2 arrived"))
    assert ("body", f"Outcome: {OUTCOMES[0]}") in rows
    assert ("note", "2 of 2 arrived") in rows and rows[-1] == ("fixed", DISCLAIMER)


def test_manifest_rejects_unknown_reveal_mode() -> None:
    with pytest.raises(ManifestError):
        parse_manifest({"clips": [_clip()], "outcome_reveal": "never"})


def test_combine_after_mode_appends_outcome_card_and_records_it(tmp_path: Path) -> None:
    a = tmp_path / "a.mp4"
    _write_video(a, (320, 240), 10, 30)
    man = tmp_path / "m.json"
    man.write_text(
        json.dumps(
            {
                "outcome_reveal": "after",
                "clips": [_clip(path="a.mp4", end=2.0, outcome_card=True, outcome_note="x")],
            }
        )
    )
    sidecar, dur = combine(man, tmp_path / "o.mp4", fps=10, card_sec=1.0)
    side = json.loads(sidecar.read_text())
    assert side["outcome_reveal"] == "after" and side["clips"][0]["outcome_card"] is True
    assert dur == pytest.approx(1.0 + 2.0 + 1.0)


def test_sidecar_default_mode_has_no_reveal_keys(tmp_path: Path) -> None:
    a = tmp_path / "a.mp4"
    _write_video(a, (320, 240), 10, 20)
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"clips": [_clip(path="a.mp4")]}))
    sidecar, _ = combine(man, tmp_path / "o.mp4", fps=10, card_sec=1.0)
    side = json.loads(sidecar.read_text())
    assert "outcome_reveal" not in side and "outcome_card" not in side["clips"][0]
