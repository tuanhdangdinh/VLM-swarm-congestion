from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig


class OpenAIBackend:
    """HTTP adapter for the OpenAI Chat Completions API (GPT vision models).

    Mirrors `LlamaServerBackend` (both speak the OpenAI-compatible
    `chat/completions` schema) but targets the hosted endpoint with bearer auth.
    The API key is read from the environment at construction, never accepted via
    config and never logged. Like the other backends, this returns the raw
    assistant text in `BackendResponse`; JSON extraction and decision validation
    stay backend-agnostic in `output_parser.py` and the `Reasoner`.
    """

    def __init__(
        self,
        model_id: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        organization: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        raw_api_key = os.environ.get(api_key_env)
        self._api_key = "".join(raw_api_key.split()) if raw_api_key else None
        if not self._api_key:
            raise ValueError(f"{api_key_env} is not set in the environment")
        self._organization = organization

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        # top_k / presence_penalty in ReasonerConfig are llama/Cosmos-specific; OpenAI
        # rejects top_k, so we omit it rather than send an unsupported field.
        body = {
            "model": self.model_id,
            "messages": self._build_messages(payload),
            "temperature": config.temperature,
            "top_p": config.top_p,
            "max_tokens": config.max_tokens,
            "stream": False,
        }

        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=config.timeout_sec,
            )
        except requests.exceptions.Timeout as exc:
            raise ConnectionError(f"OpenAI request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"OpenAI connection failed: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"OpenAI request failed: {type(exc).__name__}") from exc

        if resp.status_code >= 400:
            # Truncate and never echo request headers/body — avoids leaking the key.
            raise ConnectionError(
                f"OpenAI returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        data = resp.json()
        message = data["choices"][0]["message"]
        text = message.get("content")
        if text is None:
            text = message.get("refusal") or ""
        return BackendResponse(
            text=text,
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=data,
        )

    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        data_url = self._encode_image(payload.image_path)
        user_content = [
            {"type": "text", "text": payload.user_prompt},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
        ]
        return [
            {"role": "system", "content": payload.system_prompt},
            {"role": "user", "content": user_content},
        ]

    @staticmethod
    def _encode_image(image_path: str) -> str:
        path = Path(image_path)
        suffix = path.suffix.lower()
        mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        data = base64.b64encode(path.read_bytes()).decode()
        return f"data:{mime};base64,{data}"

    @staticmethod
    def _extract_usage(data: dict) -> dict[str, int] | None:
        usage = data.get("usage")
        if not usage:
            return None
        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        return {k: usage[k] for k in keys if k in usage} or None
