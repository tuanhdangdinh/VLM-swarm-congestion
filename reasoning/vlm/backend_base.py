from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VLMRequest:
    prompt: str
    image_path: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class VLMResponse:
    text: str
    raw: dict[str, Any] | None = None


class VLMBackend(ABC):
    """Common interface for VLM providers."""

    @abstractmethod
    def analyze(self, request: VLMRequest) -> VLMResponse:
        """Analyze an annotated scene and return model output text."""
