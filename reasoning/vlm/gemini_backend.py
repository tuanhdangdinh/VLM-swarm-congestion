from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import requests

from reasoning.schemas import load_schema
from reasoning.vlm.errors import BackendTimeoutError
from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

logger = logging.getLogger(__name__)

# ReasonerConfig always carries these with defaults, so "the caller explicitly set
# it" is unknowable on a frozen model. Interactions API generation_config has none
# of them (not merely unsupported values -- they are absent from the schema), so
# GeminiBackend never sends them and instead records them per call (see analyze).
_UNSUPPORTED_SAMPLING_FIELDS = ("temperature", "top_p", "top_k", "presence_penalty")


class GeminiBackend:
    """HTTP adapter for the Gemini Interactions API (Robotics-ER 2 preview).

    Unlike `OpenAIBackend`/`AnthropicBackend`, this does not send `temperature`,
    `top_p`, or `top_k` -- the Interactions API's `generation_config` has no such
    fields at all. The nearest controls are `seed` (the only reproducibility knob
    this API offers) and `thinking_level`. `AnthropicBackend` already drops the
    same four `ReasonerConfig` sampling fields, but silently; this backend
    instead records their values in `BackendResponse.raw["unsupported_sampling"]`
    on every call and logs one WARNING per backend instance naming them, so the
    confound is visible in run artifacts rather than invisible (see
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
            raise BackendTimeoutError(f"Gemini request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"Gemini connection failed: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Gemini request failed: {type(exc).__name__}") from exc

        if resp.status_code >= 400:
            # Truncate and never echo request headers/body -- avoids leaking the key.
            raise ConnectionError(
                f"Gemini returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        data = resp.json()
        raw = dict(data)
        raw["unsupported_sampling"] = unsupported_sampling
        return BackendResponse(
            text=self._extract_text(data),
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=raw,
            served_model=self._extract_served_model(data),
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
            for entry in step.get("content", []) or []
            if entry.get("type") == "text" and "text" in entry
        ]
        return "\n".join(texts)

    @staticmethod
    def _extract_usage(data: dict) -> dict[str, int] | None:
        usage = data.get("usage") or data.get("usage_metadata")
        if not usage:
            return None
        # Local names match OpenAIBackend/LlamaServerBackend's token_usage keys so
        # downstream diagnostics/logging stay backend-agnostic; Gemini's own names
        # are preserved verbatim in BackendResponse.raw.
        key_map = {
            "prompt_tokens": "total_input_tokens",
            "completion_tokens": "total_output_tokens",
            "thought_tokens": "total_thought_tokens",
            "total_tokens": "total_tokens",
        }
        result = {
            local_key: usage[gemini_key]
            for local_key, gemini_key in key_map.items()
            if gemini_key in usage
        }
        return result or None

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # The Interactions API is not documented to echo a served version; read
        # `model` if it is present, else record None rather than the request id.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
