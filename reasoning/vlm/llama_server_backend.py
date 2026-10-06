from __future__ import annotations

import base64
from pathlib import Path

import requests

from reasoning.vlm.models import BackendResponse, PromptPayload, ReasonerConfig


class LlamaServerBackend:
    """HTTP adapter for llama-server (llama.cpp) OpenAI-compatible endpoint.

    Targets NVIDIA Cosmos Reason2 served via:
        llama-server -m cosmos.gguf --port 8080 -ngl 99 [--mmproj mmproj.gguf]

    Operates in text-only mode when mmproj_path is None (server started without
    --mmproj). Switches to vision mode automatically when mmproj_path is set,
    which requires the server to have been started with the matching --mmproj flag.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model_id: str = "cosmos-reason2-8b",
        mmproj_path: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.mmproj_path = mmproj_path

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
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"llama-server request failed: {type(exc).__name__}") from exc

        if resp.status_code >= 400:
            raise ConnectionError(
                f"llama-server returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ConnectionError(
                f"llama-server response body malformed: {type(exc).__name__}"
            ) from exc
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
        system = {"role": "system", "content": payload.system_prompt}

        if self.mmproj_path is not None:
            data_url = self._encode_image(payload.image_path)
            # Media-first ordering: Cosmos Reason 2 / Qwen3-VL are trained with the
            # image preceding the user text; reversing it degrades spatial grounding.
            user_content = [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": payload.user_prompt},
            ]
            user = {"role": "user", "content": user_content}
        else:
            user = {"role": "user", "content": payload.user_prompt}

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
