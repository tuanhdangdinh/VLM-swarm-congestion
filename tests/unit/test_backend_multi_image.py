"""Ordered image lists in the backend payloads (prompt-apparatus zoom tile, 2026-10-04).

Flag-off request bodies are pinned to their pre-apparatus hashes (computed on
the clean `aec58cc` baseline), so a single-image request is sent byte for
byte as before. With an extra image the overhead frame stays first and the
tile follows; llama_server refuses rather than silently dropping it.
"""
import base64
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from reasoning.vlm.anthropic_backend import AnthropicBackend
from reasoning.vlm.gemini_backend import GeminiBackend
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.mock_backend import MockBackend
from reasoning.vlm.models import (
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.openai_backend import OpenAIBackend
from reasoning.vlm.reasoner import Reasoner

# json.dumps(body, sort_keys=True) SHA-256 of the flag-off request bodies on
# the baseline, for the fixed fixture image below.
_OPENAI_FLAG_OFF_MESSAGES = "ebbc3440a5d743ad0c4a9e79d18ec8f6fd92b14b814de9aaac7284e6f22a6076"
_GEMINI_FLAG_OFF_BODY = "0daa73c601a144d049f16cf6216f1ae74e049be348bce8b9d49e00f531498086"


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "test-key")


def _fixed_image(tmp_path: Path) -> Path:
    path = tmp_path / "fixed.png"
    path.write_bytes(bytes(range(256)) * 4)
    return path


def _payload(image: Path, extras: list[str] | None = None) -> PromptPayload:
    return PromptPayload(
        system_prompt="sys",
        user_prompt="user",
        image_path=str(image),
        known_robot_ids=["robot_1"],
        extra_image_paths=extras or [],
    )


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def _tile(tmp_path: Path) -> Path:
    path = tmp_path / "frame_zoom.png"
    path.write_bytes(b"tile-bytes")
    return path


class TestFlagOffBodiesUnchanged:
    def test_openai_single_image_messages_match_baseline(self, tmp_path):
        messages = OpenAIBackend()._build_messages(_payload(_fixed_image(tmp_path)))
        assert _hash(messages) == _OPENAI_FLAG_OFF_MESSAGES

    def test_gemini_single_image_body_matches_baseline(self, tmp_path):
        body = GeminiBackend()._build_body(
            _payload(_fixed_image(tmp_path)), ReasonerConfig(backend_id="gemini")
        )
        assert _hash(body) == _GEMINI_FLAG_OFF_BODY


class TestOpenAIMultiImage:
    def test_frame_then_tile_after_the_text(self, tmp_path):
        frame, tile = _fixed_image(tmp_path), _tile(tmp_path)
        content = OpenAIBackend()._build_messages(_payload(frame, [str(tile)]))[1]["content"]
        assert [part["type"] for part in content] == ["text", "image_url", "image_url"]
        assert content[1]["image_url"]["url"].endswith(_b64(frame))
        assert content[2]["image_url"]["url"].endswith(_b64(tile))
        assert content[2]["image_url"]["detail"] == "high"


class TestGeminiMultiImage:
    def test_frame_then_tile_as_input_parts(self, tmp_path):
        frame, tile = _fixed_image(tmp_path), _tile(tmp_path)
        body = GeminiBackend()._build_body(
            _payload(frame, [str(tile)]), ReasonerConfig(backend_id="gemini")
        )
        assert [part["type"] for part in body["input"]] == ["text", "image", "image"]
        assert body["input"][1]["data"] == _b64(frame)
        assert body["input"][2]["data"] == _b64(tile)
        assert body["input"][2]["mime_type"] == "image/png"


class TestAnthropicMultiImage:
    def test_images_first_in_order_then_text(self, tmp_path):
        frame, tile = _fixed_image(tmp_path), _tile(tmp_path)
        content = AnthropicBackend()._build_messages(_payload(frame, [str(tile)]))[0]["content"]
        assert [part["type"] for part in content] == ["image", "image", "text"]
        assert content[0]["source"]["data"] == _b64(frame)
        assert content[1]["source"]["data"] == _b64(tile)

    def test_single_image_shape_unchanged(self, tmp_path):
        content = AnthropicBackend()._build_messages(_payload(_fixed_image(tmp_path)))[0]["content"]
        assert [part["type"] for part in content] == ["image", "text"]


class TestLlamaServerRefusesExtraImages:
    def test_extra_image_raises_instead_of_dropping(self, tmp_path):
        backend = LlamaServerBackend(model_id="m", mmproj_path="/x.gguf")
        with pytest.raises(ValueError, match="extra images"):
            backend._build_messages(_payload(_fixed_image(tmp_path), [str(_tile(tmp_path))]))


def _png(path: Path, size=(32, 24)) -> Path:
    Image.new("RGB", size, (10, 200, 30)).save(path)
    return path


def _request(tmp_path: Path, **update) -> ReasonerRequest:
    return ReasonerRequest(
        request_id="r1",
        image_path=str(_png(tmp_path / "frame.png")),
        frame_id="c",
        stamp=1.0,
        robot_states=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
        prompt_version=3,
        **update,
    )


class _Recorder(MockBackend):
    def __init__(self, texts):
        super().__init__(response_sequence=texts)
        self.payloads: list[PromptPayload] = []

    def analyze(self, payload, config):
        self.payloads.append(payload)
        return super().analyze(payload, config)


_REFUSAL = "I'm sorry, I can't assist with that."
_VALID = (
    '{"congestion_detected": false, "type": "none", "involved_robots": [], '
    '"root_cause": "clear", "strategy": "none", "justification": "clear"}'
)


class TestReasonerExtraImages:
    def test_missing_tile_raises_before_any_backend_call(self, tmp_path):
        backend = _Recorder([_VALID])
        reasoner = Reasoner(backend, ReasonerConfig(backend_id="mock"))
        with pytest.raises(FileNotFoundError, match="extra image"):
            reasoner.run(_request(tmp_path, zoom_tile_path=str(tmp_path / "nope.png")))
        assert backend.payloads == []

    def test_tile_reaches_the_backend_payload(self, tmp_path):
        tile = _png(tmp_path / "zoom.png", (64, 48))
        backend = _Recorder([_VALID])
        Reasoner(backend, ReasonerConfig(backend_id="mock")).run(
            _request(tmp_path, zoom_tile_path=str(tile))
        )
        assert backend.payloads[0].extra_image_paths == [str(tile)]

    def test_neutral_fallback_neutralizes_the_tile_too(self, tmp_path):
        tile = _png(tmp_path / "zoom.png", (64, 48))
        backend = _Recorder([_REFUSAL, _VALID])
        config = ReasonerConfig(backend_id="mock", max_attempts=2, image_fallback_after_attempts=1)
        result = Reasoner(backend, config).run(_request(tmp_path, zoom_tile_path=str(tile)))
        assert result.diagnostics.image_fallback_used
        second = backend.payloads[1]
        assert second.image_path != backend.payloads[0].image_path
        assert len(second.extra_image_paths) == 1
        assert second.extra_image_paths[0] != str(tile)

    def test_neutral_tile_keeps_its_size_and_is_grey(self, tmp_path):
        tile = _png(tmp_path / "zoom.png", (64, 48))
        seen: list[tuple[tuple[int, int], tuple[int, int, int]]] = []

        class _Grab(_Recorder):
            def analyze(self, payload, config):
                if payload.extra_image_paths and payload.extra_image_paths[0] != str(tile):
                    with Image.open(payload.extra_image_paths[0]) as image:
                        seen.append((image.size, image.getpixel((0, 0))))
                return super().analyze(payload, config)

        config = ReasonerConfig(backend_id="mock", max_attempts=2, image_fallback_after_attempts=1)
        Reasoner(_Grab([_REFUSAL, _VALID]), config).run(
            _request(tmp_path, zoom_tile_path=str(tile))
        )
        assert seen == [((64, 48), (128, 128, 128))]
