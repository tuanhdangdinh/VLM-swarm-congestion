from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig

logger = logging.getLogger(__name__)

# Claude 5.5-generation models reject sampling parameters (Sonnet 5.5:
# non-default values -> HTTP 400; Opus 5.5: removed), so the request never
# carries them. Their configured values are recorded per call instead, the
# Gemini ER-2 precedent (`gemini_backend._UNSUPPORTED_SAMPLING_FIELDS`).
_UNSUPPORTED_SAMPLING_FIELDS = ("temperature", "top_p", "top_k", "presence_penalty")


class AnthropicBackend:
    """HTTP adapter for the Anthropic Messages API (Claude vision models).

    The direct analog of `OpenAIBackend`: a hosted provider reached over raw
    `requests` rather than the official SDK, to keep the backend layer
    dependency-free and consistent with the other adapters. The wire format
    differs from the OpenAI-compatible backends in several ways handled here:
    `x-api-key` + `anthropic-version` auth, a top-level `system` field, a
    structured base64 image source (no `data:` URL), and a `content[0].text`
    response shape. The API key is read from the environment at construction,
    never accepted via config and never logged. Raw assistant text is returned
    in `BackendResponse`; JSON extraction and decision validation stay
    backend-agnostic in `output_parser.py` and the `Reasoner`.

    Sampling fields are never sent and are recorded in
    `BackendResponse.raw["unsupported_sampling"]` on every call. A safety
    refusal (HTTP 200, `stop_reason: "refusal"`) is returned as a response with
    `refusal=True` and the provider's `stop_details.category`, so the shared
    refusal pipeline counts it; it is not a transport error.
    """

    _API_VERSION = "2023-06-01"

    def __init__(
        self,
        model_id: str = "claude-opus-4-8",
        base_url: str = "https://api.anthropic.com/v1",
        api_key_env: str = "ANTHROPIC_API_KEY",
        thinking_type: str | None = None,
        effort: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        raw_api_key = os.environ.get(api_key_env)
        self._api_key = "".join(raw_api_key.split()) if raw_api_key else None
        if not self._api_key:
            raise ValueError(f"{api_key_env} is not set in the environment")
        self.thinking_type = thinking_type
        self.effort = effort
        self._warned = False

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        unsupported_sampling = {
            field: getattr(config, field) for field in _UNSUPPORTED_SAMPLING_FIELDS
        }
        if not self._warned:
            logger.warning(
                "Anthropic %s rejects %s; ReasonerConfig values are dropped from the "
                "request and recorded in raw['unsupported_sampling'] instead",
                self.model_id,
                _UNSUPPORTED_SAMPLING_FIELDS,
            )
            self._warned = True

        body: dict[str, object] = {
            "model": self.model_id,
            "system": payload.system_prompt,
            "messages": self._build_messages(payload),
            "max_tokens": config.max_tokens,
        }
        # Omitted unless configured: on Sonnet 5.5 an absent `thinking` runs
        # adaptive thinking, which the pinned arm records via its config.
        if self.thinking_type is not None:
            body["thinking"] = {"type": self.thinking_type}
        if self.effort is not None:
            body["output_config"] = {"effort": self.effort}

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self._API_VERSION,
            "content-type": "application/json",
        }

        try:
            resp = requests.post(
                f"{self.base_url}/messages",
                json=body,
                headers=headers,
                timeout=config.timeout_sec,
            )
        except requests.exceptions.Timeout as exc:
            raise ConnectionError(f"Anthropic request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"Anthropic connection failed: {exc}") from exc

        if resp.status_code >= 400:
            # Truncate and never echo request headers/body — avoids leaking the key.
            raise ConnectionError(
                f"Anthropic returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise ConnectionError("Anthropic response body malformed") from exc
        raw = dict(data)
        raw["unsupported_sampling"] = unsupported_sampling
        refusal = data.get("stop_reason") == "refusal"
        return BackendResponse(
            text=self._extract_text(data, refusal),
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=raw,
            served_model=self._extract_served_model(data),
            refusal=refusal,
            refusal_category=self._extract_refusal_category(data) if refusal else None,
        )

    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        # Image-first, as before; a prompt-apparatus extra image (zoom tile)
        # follows the overhead frame, then the text.
        user_content: list[dict] = []
        for image_path in [payload.image_path, *payload.extra_image_paths]:
            media_type, image_data = self._encode_image(image_path)
            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )
        user_content.append({"type": "text", "text": payload.user_prompt})
        return [{"role": "user", "content": user_content}]

    @staticmethod
    def _encode_image(image_path: str) -> tuple[str, str]:
        path = Path(image_path)
        suffix = path.suffix.lower()
        media_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        # Anthropic wants bare base64 in source.data — no `data:<mime>;base64,` prefix.
        data = base64.b64encode(path.read_bytes()).decode()
        return media_type, data

    @staticmethod
    def _extract_text(data: dict, refusal: bool) -> str:
        # Thinking blocks (empty text by default on 5.5-generation models) are
        # skipped; the answer is the text blocks, joined in order.
        texts = [
            block["text"]
            for block in data.get("content", []) or []
            if block.get("type") == "text" and isinstance(block.get("text"), str)
        ]
        if texts:
            return "\n".join(texts)
        if refusal:
            # A refusal may carry no content at all; `refusal=True` is the signal.
            return ""
        raise ConnectionError(
            f"Anthropic returned no text content (stop_reason="
            f"{data.get('stop_reason')!r})"
        )

    @staticmethod
    def _extract_refusal_category(data: dict) -> str | None:
        details = data.get("stop_details")
        if not isinstance(details, dict):
            return None
        category = details.get("category")
        return category if isinstance(category, str) and category else None

    @staticmethod
    def _extract_usage(data: dict) -> dict[str, int] | None:
        usage = data.get("usage")
        if not usage:
            return None
        keys = (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
        return {k: usage[k] for k in keys if isinstance(usage.get(k), int)} or None

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # The Messages API echoes the model id that served the request.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
