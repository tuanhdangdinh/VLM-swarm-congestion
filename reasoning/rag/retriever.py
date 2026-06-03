from reasoning.rag.vector_store import RetrievedTemplate, VectorStore


def retrieve_templates(
    vector_store: VectorStore,
    congestion_type: str,
    strategy: str,
    root_cause: str,
    top_k: int = 3,
) -> list[RetrievedTemplate]:
    query = f"type={congestion_type}; strategy={strategy}; root_cause={root_cause}"
    return vector_store.search(query=query, top_k=top_k)
