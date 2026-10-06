from __future__ import annotations

import base64
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PayloadFormat, PromptPayload, ReasonerConfig

# Transport conventions (format audit 2026-10-06): the Qwen3-VL-8B-Instruct
# model card's only example puts the image part before the text, as does the
# Cosmos Reason 2 guide; llama-server's README documents `image_url` parts
# without an order. No detail flag exists. `response_format` stays unsent
# (constrained-decoding prohibition). Unchanged since wiring. A server with no
# mmproj sends text only (`image_position` None in the effective config).
PAYLOAD_FORMAT = PayloadFormat(
    version="v1",
    image_position="before_text",
    system_placement="system_message",
)


class LlamaServerBackend:
    """HTTP adapter for llama-server (llama.cpp) OpenAI-compatible endpoint.

    Targets NVIDIA Cosmos Reason2 served via:
        llama-server -m cosmos.gguf --port 8080 -ngl 99 [--mmproj mmproj.gguf]

    Operates in text-only mode when mmproj_path is None (server started without
    --mmproj). Switches to vision mode automatically when mmproj_path is set,
    which requires the server to have been started with the matching --mmproj flag.
    Also serves Qwen3-VL-8B-Instruct (`scripts/vm/qwen_serve.sh`); with
    `multi_image` the prompt-apparatus extra images (zoom tile) follow the
    frame as further `image_url` parts, otherwise they are refused. Any other
    OpenAI-compatible Chat Completions server works the same way, e.g. vLLM
    serving Molmo2-ER (`scripts/vm/molmo_serve.sh`); `system_placement`
    "user_prefix" folds the preamble into the user turn for a served chat
    template that rejects a system role.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model_id: str = "cosmos-reason2-8b",
        mmproj_path: str | None = None,
        multi_image: bool = False,
        system_placement: str = "system_message",
    ) -> None:
        if system_placement not in ("system_message", "user_prefix"):
            raise ValueError(f"unknown system_placement {system_placement!r}")
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.mmproj_path = mmproj_path
        self.multi_image = multi_image
        self.system_placement = system_placement

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        messages = self._build_messages(payload)
        # No response_format=json_object here: it forces the first generated token to
        # open a JSON object, which suppresses the model's <think> chain-of-thought.
        # Cosmos Reason 2 relies on that reasoning trace for grounding accuracy, so we
        # request JSON in the prompt instead and parse it out of the final answer.
        body = {
            "model": self.model_id,
            "messages": messages,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "presence_penalty": config.presence_penalty,
            "max_tokens": config.max_tokens,
            "stream": False,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=body,
                timeout=config.timeout_sec,
            )
        except requests.exceptions.Timeout as exc:
            raise ConnectionError(f"llama-server request timed out: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConnectionError(f"llama-server connection failed: {exc}") from exc

        if resp.status_code >= 400:
            raise ConnectionError(
                f"llama-server returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        token_usage = self._extract_usage(data)

        return BackendResponse(
            text=text,
            backend_id=self.model_id,
            token_usage=token_usage,
            raw=data,
            served_model=self._extract_served_model(data),
        )

    def is_ready(self) -> bool:
        """Return True if llama-server health endpoint responds ok."""
        base = self.base_url.removesuffix("/v1")
        try:
            resp = requests.get(f"{base}/health", timeout=5)
            return resp.status_code == 200 and resp.json().get("status") == "ok"
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        if payload.extra_image_paths and not (self.multi_image and self.mmproj_path):
            # Multi-image input through llama-server's mtmd path must be
            # smoke-verified per served model (config `multi_image`); refuse
            # rather than silently drop the zoom tile the prompt text announces.
            raise ValueError(
                "llama_server backend does not support extra images "
                f"({len(payload.extra_image_paths)} given); disable prompt_zoom_tile"
            )
        user_text = payload.user_prompt
        prefix_system = self.system_placement == "user_prefix"
        if prefix_system:
            user_text = f"{payload.system_prompt}\n\n{payload.user_prompt}"
        system = {"role": "system", "content": payload.system_prompt}

        if self.mmproj_path is not None:
            # Media-first ordering: Cosmos Reason 2 / Qwen3-VL are trained with the
            # image preceding the user text; reversing it degrades spatial grounding.
            # The overhead frame stays first and any zoom tile follows it, matching
            # the prompt's "a second image follows the overhead view".
            user_content: list[dict] = [
                {"type": "image_url", "image_url": {"url": self._encode_image(path)}}
                for path in [payload.image_path, *payload.extra_image_paths]
            ]
            user_content.append({"type": "text", "text": user_text})
            user = {"role": "user", "content": user_content}
        else:
            user = {"role": "user", "content": user_text}

        if prefix_system:
            return [user]
        return [system, user]

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

    @staticmethod
    def _extract_served_model(data: dict) -> str | None:
        # llama-server echoes its loaded model name (alias or file) here.
        model = data.get("model")
        return model if isinstance(model, str) and model else None
