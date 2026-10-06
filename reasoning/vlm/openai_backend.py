from __future__ import annotations

import base64
import os
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PayloadFormat, PromptPayload, ReasonerConfig
from reasoning.vlm.transport import http_error

# Transport conventions (format audit 2026-10-06, docs fetched that day):
# OpenAI's images-vision guide and DeepSeek's vision guide state no
# image/text order preference and both put the text part first in every
# example; `detail: "high"` is the tile-based mode for gpt-4o/gpt-5.1 (`auto`
# behaves the same) and is "original" on DeepSeek (also its `auto`). JSON is
# asked for in the prompt only: JSON mode / Structured Outputs are documented
# but not sent (constrained-decoding prohibition). Unchanged since wiring.
# Zhipu GLM-5.3-Flash (docs.z.ai chat-completion reference, fetched
# 2026-10-07) rides the same packing: its only image example puts images
# first but states no preference (examples alone do not move the packing,
# audit rule), and its image_url schema lists `url` only -- `detail` is
# accepted live (HTTP 200, identical prompt_tokens with and without it) and
# stays sent so the packing is one constant per adapter.
PAYLOAD_FORMAT = PayloadFormat(
    version="v1",
    image_position="after_text",
    system_placement="system_message",
    image_detail="high",
)


class OpenAIBackend:
    """HTTP adapter for the OpenAI Chat Completions API (GPT vision models).

    Mirrors `LlamaServerBackend` (both speak the OpenAI-compatible
    `chat/completions` schema) but targets a hosted endpoint with bearer auth:
    OpenAI itself, or another OpenAI-compatible provider via `base_url`
    (DeepSeek). Provider-specific request fields (`reasoning_effort`, the
    `max_completion_tokens` name, DeepSeek's `thinking`) are opt-in by config.
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
        reasoning_effort: str | None = None,
        max_tokens_param: str = "max_tokens",
        thinking_type: str | None = None,
        omit_sampling: bool = False,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        raw_api_key = os.environ.get(api_key_env)
        self._api_key = "".join(raw_api_key.split()) if raw_api_key else None
        if not self._api_key:
            raise ValueError(f"{api_key_env} is not set in the environment")
        self._organization = organization
        self.reasoning_effort = reasoning_effort
        self.max_tokens_param = max_tokens_param
        self.thinking_type = thinking_type
        self.omit_sampling = omit_sampling

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        # top_k / presence_penalty in ReasonerConfig are llama/Cosmos-specific; OpenAI
        # rejects top_k, so we omit it rather than send an unsupported field.
        body = {
            "model": self.model_id,
            "messages": self._build_messages(payload),
            "temperature": config.temperature,
            "top_p": config.top_p,
            self.max_tokens_param: config.max_tokens,
            "stream": False,
        }
        unsupported_sampling: dict[str, float] | None = None
        if self.omit_sampling:
            # gpt-5.1 above reasoning_effort "none" rejects these with HTTP 400;
            # the configured values are kept in the response record instead.
            unsupported_sampling = {
                "temperature": body.pop("temperature"),
                "top_p": body.pop("top_p"),
            }
        # Optional fields are appended only when configured, so a config that
        # sets none of them (the gpt-4o pin) sends the exact pre-existing body.
        if self.reasoning_effort is not None:
            body["reasoning_effort"] = self.reasoning_effort
        if self.thinking_type is not None:
            body["thinking"] = {"type": self.thinking_type}

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
            # Classified for the shared retry policy (429/5xx retried with
            # backoff, other 4xx final); the message is truncated and never
            # echoes request headers or body, so the key cannot leak.
            raise http_error("OpenAI", resp)

        try:
            data = resp.json()
            message = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            # A connection the provider closes mid-body (seen on DeepSeek) can
            # arrive as a truncated HTTP 200; that is a transport failure for
            # the standing retry policy, never a refusal or a parse failure.
            raise ConnectionError(
                f"OpenAI-compatible response body malformed: {type(exc).__name__}"
            ) from exc
        text = message.get("content")
        if text is None:
            text = message.get("refusal") or ""
        raw = data
        if unsupported_sampling is not None:
            raw = dict(data)
            raw["unsupported_sampling"] = unsupported_sampling
        return BackendResponse(
            text=text,
            backend_id=self.model_id,
            token_usage=self._extract_usage(data),
            raw=raw,
            served_model=self._extract_served_model(data),
        )

    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        # Chat Completions takes any number of image parts in one user
        # message; the overhead frame stays first and any prompt-apparatus
        # extra image (the zoom tile) follows it, matching the prompt's
        # "a second image follows the overhead view".
        user_content: list[dict] = [{"type": "text", "text": payload.user_prompt}]
        for image_path in [payload.image_path, *payload.extra_image_paths]:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._encode_image(image_path), "detail": "high"},
                }
            )
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
        extracted = {k: usage[k] for k in keys if k in usage}
        # Reasoning tokens are billed inside completion_tokens (gpt-5.1 above
        # effort "none"; DeepSeek with thinking on; forced-thinking Zhipu
        # GLM-5.3-Flash) and count against max_tokens -- the breakdown is the
        # only per-call evidence of how much the model reasoned and how close
        # a call came to the output cap (the DeepSeek thinking-cap trap).
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict) and isinstance(details.get("reasoning_tokens"), int):
            extracted["reasoning_tokens"] = details["reasoning_tokens"]
        return extracted or None

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # Chat Completions echoes the snapshot that served an alias request
        # (`gpt-4o` -> `gpt-4o-2024-08-06`), refusals included.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
