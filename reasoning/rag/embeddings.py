from collections.abc import Sequence


class EmbeddingModel:
    """Placeholder embedding model interface."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError("Embedding backend is not configured yet.")
