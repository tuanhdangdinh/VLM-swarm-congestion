from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedTemplate:
    name: str
    score: float
    content: dict[str, object]


class VectorStore:
    """Placeholder vector-store interface."""

    def search(self, query: str, top_k: int = 3) -> list[RetrievedTemplate]:
        raise NotImplementedError("Vector store is not configured yet.")
