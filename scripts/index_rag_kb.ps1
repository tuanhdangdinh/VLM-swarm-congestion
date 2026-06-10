# Index the RAG knowledge base.

$ErrorActionPreference = "Stop"

python -m reasoning.rag.index_knowledge_base
exit $LASTEXITCODE
