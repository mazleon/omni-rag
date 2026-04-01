import uuid
from typing import Any

from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, callable] = {}
        self._definitions: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> callable:
        def decorator(func: callable) -> callable:
            self._tools[name] = func
            self._definitions.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            })
            return func
        return decorator

    def get_tool(self, name: str) -> callable | None:
        return self._tools.get(name)

    def get_all_tools(self) -> dict[str, callable]:
        return self._tools.copy()

    def get_definitions(self) -> list[dict[str, Any]]:
        return self._definitions.copy()


_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _global_registry


@_global_registry.register(
    name="search_documents",
    description="Search for relevant documents using semantic search",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "limit": {"type": "integer", "description": "Maximum results", "default": 5},
        },
        "required": ["query"],
    },
)
async def search_documents(
    query: str,
    limit: int = 5,
    org_id: uuid.UUID | None = None,
    session: Any = None,
) -> dict[str, Any]:
    from services.ingestion.embedder import get_embedder_service
    from services.retrieval.dense import get_dense_retriever_service

    if not org_id or not session:
        return {"results": [], "error": "org_id and session required"}

    embedder = get_embedder_service()
    retriever = get_dense_retriever_service()

    embedding = await embedder.embed_query(query)
    results = await retriever.search(org_id, embedding)

    return {
        "results": [
            {
                "chunk_id": str(r.chunk_id),
                "content": r.content[:300],
                "score": r.score,
            }
            for r in results[:limit]
        ],
    }


@_global_registry.register(
    name="get_document_info",
    description="Get information about a specific document",
    parameters={
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "description": "Document UUID"},
        },
        "required": ["document_id"],
    },
)
async def get_document_info(
    document_id: str,
    session: Any = None,
) -> dict[str, Any]:
    if not session:
        return {"error": "session required"}

    from sqlalchemy import select
    from core.models import Document

    result = await session.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()

    if not doc:
        return {"error": "Document not found"}

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status.value,
        "num_chunks": doc.num_chunks,
        "num_pages": doc.num_pages,
    }


@_global_registry.register(
    name="list_collections",
    description="List all document collections in the organization",
    parameters={
        "type": "object",
        "properties": {
            "org_id": {"type": "string", "description": "Organization UUID"},
        },
        "required": ["org_id"],
    },
)
async def list_collections(
    org_id: str,
    session: Any = None,
) -> dict[str, Any]:
    if not session:
        return {"error": "session required"}

    from sqlalchemy import select
    from core.models import Collection

    result = await session.execute(
        select(Collection).where(Collection.org_id == uuid.UUID(org_id))
    )
    collections = result.scalars().all()

    return {
        "collections": [
            {"id": str(c.id), "name": c.name, "description": c.description}
            for c in collections
        ],
    }