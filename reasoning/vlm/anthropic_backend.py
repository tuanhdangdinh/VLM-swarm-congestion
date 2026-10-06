from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig
from reasoning.vlm.transport import http_error


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
    """

    _API_VERSION = "2023-06-01"

    def __init__(
        self,
        model_id: str = "claude-opus-4-8",
        base_url: str = "https://api.anthropic.com/v1",
        api_key_env: str = "ANTHROPIC_API_KEY",
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self._api_key = os.environ.get(api_key_env)
        if not self._api_key:
            raise ValueError(f"{api_key_env} is not set in the environment")

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        # temperature / top_p / top_k from ReasonerConfig are omitted: Claude Opus
        # 4.7+ reject sampling parameters with HTTP 400. We also leave `thinking`
        # off so the first content block is the text block the output parser reads.
        body = {
            "model": self.model_id,
            "system": payload.system_prompt,
            "messages": self._build_messages(payload),
            "max_tokens": config.max_tokens,
        }

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
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"Anthropic request failed: {type(exc).__name__}") from exc

        if resp.status_code >= 400:
            # Classified for the shared retry policy (429/5xx retried with
            # backoff, other 4xx final); the message is truncated and never
            # echoes request headers or body, so the key cannot leak.
            raise http_error("Anthropic", resp)

        try:
            data = resp.json()
        except ValueError as exc:
            raise ConnectionError("Anthropic response body malformed") from exc
        return BackendResponse(
            text=self._extract_text(data),
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=data,
            served_model=self._extract_served_model(data),
        )

    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        media_type, image_data = self._encode_image(payload.image_path)
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            },
            {"type": "text", "text": payload.user_prompt},
        ]
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
    def _extract_text(data: dict) -> str:
        # A safety refusal returns HTTP 200 with stop_reason="refusal" and an empty
        # content array; surface it as ConnectionError so the Reasoner returns
        # decision=None (its retry path) rather than crashing on an IndexError.
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"]
        raise ConnectionError(
            f"Anthropic returned no text content (stop_reason="
            f"{data.get('stop_reason')!r})"
        )

    @staticmethod
    def _extract_usage(data: dict) -> dict[str, int] | None:
        usage = data.get("usage")
        if not usage:
            return None
        keys = ("input_tokens", "output_tokens")
        return {k: usage[k] for k in keys if k in usage} or None

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # The Messages API echoes the model id that served the request.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
