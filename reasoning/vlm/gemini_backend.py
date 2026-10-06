from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import requests

from reasoning.schemas import load_schema
from reasoning.vlm.errors import BackendTimeoutError
from reasoning.vlm.models import BackendResponse, PayloadFormat, PromptPayload, ReasonerConfig
from reasoning.vlm.transport import (
    http_error,
    json_body,
    provider_error_code,
    provider_request_id,
    safe_error_text,
)

logger = logging.getLogger(__name__)

# ReasonerConfig always carries these with defaults, so "the caller explicitly set
# it" is unknowable on a frozen model. Interactions API generation_config has none
# of them (not merely unsupported values -- they are absent from the schema), so
# GeminiBackend never sends them and instead records them per call (see analyze).
_UNSUPPORTED_SAMPLING_FIELDS = ("temperature", "top_p", "top_k", "presence_penalty")

# Transport conventions (format audit 2026-10-06): the image-understanding
# guide (updated 2026-09-23) says "When using a single image with text, place
# the text prompt before the image in the input array"; the Robotics-ER page's
# examples put the image first but state no preference, so the explicit tip
# wins. The preamble rides `system_instruction`. `media_resolution` is left at
# the provider default and `response_format` is sent only with the opt-in
# `force_schema` (off on the pinned arm). Unchanged since wiring.
# The "Generation blocked codes" of the Gemini api-errors page (fetched
# 2026-10-07): "policy, safety, or content restrictions blocked the model's
# output. When you receive one of these codes, modify your input and retry."
# Delivered as `{"error": {"code": ..., "message": ...}}`.
GENERATION_BLOCKED_CODES = frozenset(
    {
        "safety",
        "recitation",
        "language",
        "prohibited_content",
        "spii",
        "blocklist",
        "image_safety",
        "image_prohibited_content",
        "image_recitation",
        "image_other",
        "content_blocked",
    }
)

PAYLOAD_FORMAT = PayloadFormat(
    version="v1",
    image_position="after_text",
    system_placement="system_instruction",
)


class GeminiBackend:
    """HTTP adapter for the Gemini Interactions API (Robotics-ER 2 preview).

    Unlike `OpenAIBackend`/`AnthropicBackend`, this does not send `temperature`,
    `top_p`, or `top_k` -- the Interactions API's `generation_config` has no such
    fields at all. The nearest controls are `seed` (the only reproducibility knob
    this API offers) and `thinking_level`. `AnthropicBackend` drops the same
    four `ReasonerConfig` sampling fields and records them the same way: their
    values go to `BackendResponse.raw["unsupported_sampling"]` on every call
    and one WARNING per backend instance names them, so the confound is
    visible in run artifacts rather than invisible (see
    `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
    section 4). The API key is read from the environment at construction, never
    accepted via config and never logged. Like the other backends, this returns
    the raw assistant text in `BackendResponse`; JSON extraction and decision
    validation stay backend-agnostic in `output_parser.py` and the `Reasoner`.
    """

    def __init__(
        self,
        model_id: str = "gemini-robotics-er-2-preview",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        api_key_env: str = "GEMINI_API_KEY",
        thinking_level: str = "low",
        force_schema: bool = False,
        seed: int | None = None,
        store: bool | None = None,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        raw_api_key = os.environ.get(api_key_env)
        self._api_key = "".join(raw_api_key.split()) if raw_api_key else None
        if not self._api_key:
            raise ValueError(f"{api_key_env} is not set in the environment")
        self.thinking_level = thinking_level
        self.force_schema = force_schema
        self.seed = seed
        self.store = store
        self._schema = load_schema("vlm_decision") if force_schema else None
        self._warned = False

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        unsupported_sampling = {
            field: getattr(config, field) for field in _UNSUPPORTED_SAMPLING_FIELDS
        }
        if not self._warned:
            logger.warning(
                "Gemini Interactions API has no %s fields; ReasonerConfig values are "
                "dropped from the request and recorded in raw['unsupported_sampling'] "
                "instead (backend_id=%s)",
                _UNSUPPORTED_SAMPLING_FIELDS,
                self.model_id,
            )
            self._warned = True

        body = self._build_body(payload, config)
        headers = {"x-goog-api-key": self._api_key, "content-type": "application/json"}

        try:
            resp = requests.post(
                f"{self.base_url}/interactions",
                json=body,
                headers=headers,
                timeout=config.timeout_sec,
            )
        except requests.exceptions.Timeout as exc:
            raise BackendTimeoutError(
                f"Gemini request timed out: {safe_error_text(str(exc), self._api_key)}"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(
                f"Gemini connection failed: {safe_error_text(str(exc), self._api_key)}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Gemini request failed: {type(exc).__name__}") from exc

        if resp.status_code >= 400:
            body = json_body(resp)
            code = provider_error_code(body)
            if code in GENERATION_BLOCKED_CODES:
                # A generation-blocked code is a refusal whatever the HTTP
                # status (the status is undocumented for these codes), so it
                # takes the refusal path -- the grey-image fallback is exactly
                # the documented "modify your input and retry" (F03).
                raw_error: dict[str, object] = dict(body or {})
                raw_error["unsupported_sampling"] = unsupported_sampling
                raw_error["http_status"] = resp.status_code
                return BackendResponse(
                    text="",
                    backend_id=self.model_id,
                    raw=raw_error,
                    refusal=True,
                    refusal_category=code,
                    provider_request_id=provider_request_id(resp, body),
                )
            # Classified for the shared retry policy (429/5xx retried with
            # backoff, other 4xx final); the body is redacted and truncated
            # and request headers are never echoed, so the key cannot leak.
            raise http_error("Gemini", resp, self._api_key)

        try:
            data = resp.json()
            if not isinstance(data, dict):
                raise TypeError("body is not an object")
        except (ValueError, TypeError) as exc:
            raise ConnectionError("Gemini response body malformed") from exc
        status = data.get("status")
        status = status if isinstance(status, str) else None
        refusal_category: str | None = None
        if status == "failed":
            # G-api: status "failed" -- "The interaction failed." A blocked
            # code on it is a refusal; any other failure is retried as a
            # transport failure.
            code = provider_error_code(data)
            if code not in GENERATION_BLOCKED_CODES:
                raise ConnectionError(f"Gemini interaction failed (code={code})")
            refusal_category = code
        raw = dict(data)
        raw["unsupported_sampling"] = unsupported_sampling
        return BackendResponse(
            text=self._extract_text(data),
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=raw,
            served_model=self._extract_served_model(data),
            refusal=refusal_category is not None,
            refusal_category=refusal_category,
            # "incomplete" is G-api's "completed, but contains incomplete
            # results (e.g. hitting max_tokens)" -- the thought-inclusive
            # output cap (F05); recorded per attempt, read as a parse path.
            finish_reason=status,
            provider_request_id=provider_request_id(resp, data),
        )

    def _build_body(self, payload: PromptPayload, config: ReasonerConfig) -> dict:
        # The Interactions API `input` is an ordered list of content parts and
        # accepts several `image` parts (ai.google.dev image-understanding
        # guide, multi-image example, checked 2026-10-04); the overhead frame
        # stays first, any prompt-apparatus extra image (zoom tile) follows.
        image_parts: list[dict[str, str]] = []
        for image_path in [payload.image_path, *payload.extra_image_paths]:
            image_data, mime_type = self._encode_image(image_path)
            image_parts.append({"type": "image", "data": image_data, "mime_type": mime_type})
        generation_config: dict[str, object] = {
            "thinking_level": self.thinking_level,
            "max_output_tokens": config.max_tokens,
        }
        if self.seed is not None:
            generation_config["seed"] = self.seed

        body: dict[str, object] = {
            "model": self.model_id,
            "system_instruction": payload.system_prompt,
            "input": [{"type": "text", "text": payload.user_prompt}, *image_parts],
            "generation_config": generation_config,
        }
        if self.force_schema:
            body["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": self._schema,
            }
        if self.store is not None:
            # Appended last and only when configured, so the frozen ER-2 pin
            # (store unset) sends its exact pre-existing body (F10).
            body["store"] = self.store
        return body

    @staticmethod
    def _encode_image(image_path: str) -> tuple[str, str]:
        path = Path(image_path)
        suffix = path.suffix.lower()
        mime_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        data = base64.b64encode(path.read_bytes()).decode()
        return data, mime_type

    @staticmethod
    def _extract_text(data: dict) -> str:
        # steps[] are typed (model_output, function_call, code_execution_call/result,
        # file_search_call/result, user_input, ...); filter on content[].type == "text"
        # rather than step type, since the docs give example step types, not an
        # exhaustive enum, and a non-text step must be skipped rather than crash this.
        # A response with no text content anywhere (malformed or empty) yields "" here,
        # mirroring OpenAIBackend.analyze's tolerant fallback rather than raising.
        texts = [
            entry["text"]
            for step in data.get("steps", []) or []
            if isinstance(step, dict)
            for entry in step.get("content", []) or []
            if isinstance(entry, dict)
            and entry.get("type") == "text"
            and isinstance(entry.get("text"), str)
        ]
        return "\n".join(texts)

    @staticmethod
    def _extract_usage(data: dict) -> dict[str, int] | None:
        # G-api names the block `usage` only (the old `usage_metadata`
        # fallback named a field the Interactions API does not have, F16).
        usage = data.get("usage")
        if not isinstance(usage, dict) or not usage:
            return None
        # Local names match OpenAIBackend/LlamaServerBackend's token_usage keys so
        # downstream diagnostics/logging stay backend-agnostic.
        key_map = {
            "prompt_tokens": "total_input_tokens",
            "completion_tokens": "total_output_tokens",
            "thought_tokens": "total_thought_tokens",
            "total_tokens": "total_tokens",
            # Additive (F16): G-api `total_cached_tokens`, `total_tool_use_tokens`.
            "cached_tokens": "total_cached_tokens",
            "tool_use_tokens": "total_tool_use_tokens",
        }
        result = {
            local_key: usage[gemini_key]
            for local_key, gemini_key in key_map.items()
            if isinstance(usage.get(gemini_key), int)
            and not isinstance(usage[gemini_key], bool)
        }
        # G-api `input_tokens_by_modality: [{"modality": "text", "tokens": 7}]`,
        # flattened to int keys (`input_tokens_text`, `input_tokens_image`).
        for entry in usage.get("input_tokens_by_modality") or []:
            if not isinstance(entry, dict):
                continue
            modality, tokens = entry.get("modality"), entry.get("tokens")
            if isinstance(modality, str) and isinstance(tokens, int):
                result[f"input_tokens_{modality.lower()}"] = tokens
        return result or None

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # G-api's example responses echo `model`; it equals the requested id
        # (no dated snapshot), so on these arms it is not drift evidence (F04).
        # Recorded when present, else None.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
