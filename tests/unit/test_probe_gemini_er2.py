"""Unit tests for the pure helpers in scripts/probe_gemini_er2.py.

Covers only offline logic: request-body construction, response-text
extraction from a fabricated Interactions API payload, and the key
redaction helpers. No HTTP is made or mocked at the transport level because
none of these functions perform I/O; nothing here touches the network.
"""
from __future__ import annotations

import pytest

from scripts.probe_gemini_er2 import (
    build_content_parts,
    build_request_body,
    describe_key,
    elide_image_data,
    extract_response_text,
    extract_usage,
    redact_secret,
)

_FAKE_KEY = "AIzaFakeKeyValueForTestingOnly123"


def _schema() -> dict:
    return {"type": "object", "properties": {"congestion_detected": {"type": "boolean"}}}


def test_build_content_parts_has_text_then_image():
    parts = build_content_parts("describe the scene", "YmFzZTY0", "image/png")
    assert parts == [
        {"type": "text", "text": "describe the scene"},
        {"type": "image", "data": "YmFzZTY0", "mime_type": "image/png"},
    ]


def test_build_request_body_shape_without_schema():
    body = build_request_body(
        model="gemini-robotics-er-2-preview",
        system_instruction="sys",
        user_text="user",
        image_b64="YmFzZTY0",
        mime_type="image/png",
        thinking_level="low",
        include_schema=False,
        schema=None,
    )
    assert body["model"] == "gemini-robotics-er-2-preview"
    assert body["system_instruction"] == "sys"
    assert body["input"] == build_content_parts("user", "YmFzZTY0", "image/png")
    assert body["generation_config"] == {"thinking_level": "low"}
    assert "response_format" not in body


def test_build_request_body_attaches_schema_when_requested():
    schema = _schema()
    body = build_request_body(
        model="gemini-robotics-er-2-preview",
        system_instruction="sys",
        user_text="user",
        image_b64="YmFzZTY0",
        mime_type="image/png",
        thinking_level="high",
        include_schema=True,
        schema=schema,
    )
    assert body["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": schema,
    }
    assert body["generation_config"] == {"thinking_level": "high"}


def test_build_request_body_never_carries_an_api_key():
    # build_request_body takes no api_key parameter at all: the key is a header
    # concern (send_request), never a body field, so there is nothing for a key
    # value to leak into here even by accident.
    body = build_request_body(
        model="m",
        system_instruction="sys",
        user_text="user",
        image_b64="YmFzZTY0",
        mime_type="image/png",
        thinking_level="low",
        include_schema=True,
        schema=_schema(),
    )
    assert _FAKE_KEY not in str(body)


def test_elide_image_data_replaces_base64_with_length_marker():
    body = build_request_body(
        model="m",
        system_instruction="sys",
        user_text="user",
        image_b64="A" * 128,
        mime_type="image/png",
        thinking_level="low",
        include_schema=False,
        schema=None,
    )
    elided = elide_image_data(body)
    image_item = next(item for item in elided["input"] if item["type"] == "image")
    assert "AAAA" not in image_item["data"]
    assert "128" in image_item["data"]
    # Original body is untouched.
    original_image_item = next(item for item in body["input"] if item["type"] == "image")
    assert original_image_item["data"] == "A" * 128


def test_extract_response_text_concatenates_text_content_across_steps():
    data = {
        "steps": [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": '{"congestion_detected": '}],
            },
            {
                "type": "model_output",
                "content": [{"type": "text", "text": "false}"}],
            },
        ]
    }
    assert extract_response_text(data) == '{"congestion_detected": false}'


def test_extract_response_text_skips_a_non_text_step():
    data = {
        "steps": [
            {
                "type": "function_call",
                "content": [{"type": "function_call", "name": "lookup"}],
            },
            {
                "type": "model_output",
                "content": [{"type": "text", "text": '{"congestion_detected": false}'}],
            },
        ]
    }
    assert extract_response_text(data) == '{"congestion_detected": false}'


def test_extract_response_text_raises_when_no_text_anywhere():
    data = {"steps": [{"type": "function_call", "content": [{"type": "function_call"}]}]}
    with pytest.raises(RuntimeError):
        extract_response_text(data)


def test_extract_usage_prefers_usage_key():
    assert extract_usage({"usage": {"total_tokens": 42}}) == {"total_tokens": 42}


def test_extract_usage_falls_back_to_usage_metadata_key():
    assert extract_usage({"usage_metadata": {"totalTokenCount": 7}}) == {"totalTokenCount": 7}


def test_extract_usage_returns_none_when_absent():
    assert extract_usage({}) is None


def test_describe_key_reveals_only_length_and_prefix():
    description = describe_key(_FAKE_KEY)
    assert str(len(_FAKE_KEY)) in description
    assert _FAKE_KEY[:3] in description
    assert _FAKE_KEY not in description
    assert len(description) < 40


def test_redact_secret_scrubs_every_occurrence():
    text = f"HTTP 403: bad key {_FAKE_KEY} in header Authorization: Bearer {_FAKE_KEY}"
    redacted = redact_secret(text, _FAKE_KEY)
    assert _FAKE_KEY not in redacted
    assert redacted.count("***REDACTED***") == 2


def test_redact_secret_is_noop_for_empty_secret():
    text = "nothing to redact here"
    assert redact_secret(text, None) == text
    assert redact_secret(text, "") == text
