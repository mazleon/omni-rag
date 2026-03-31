"""Domain exceptions and FastAPI HTTP error helpers."""

from fastapi import HTTPException, status


class OmniRAGError(Exception):
    """Base class for all OmniRAG domain errors."""


class DocumentNotFoundError(OmniRAGError):
    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document {document_id} not found")
        self.document_id = document_id


class DocumentAlreadyExistsError(OmniRAGError):
    def __init__(self, content_hash: str) -> None:
        super().__init__(f"Document with hash {content_hash} already indexed")
        self.content_hash = content_hash


class IngestionError(OmniRAGError):
    """Raised when the ingestion pipeline fails unrecoverably."""


class RetrievalError(OmniRAGError):
    """Raised when the retrieval engine encounters an error."""


class OrganizationNotFoundError(OmniRAGError):
    def __init__(self, org_id: str) -> None:
        super().__init__(f"Organization {org_id} not found")
        self.org_id = org_id


class AgentCostCeilingError(OmniRAGError):
    """Raised when the agent loop exceeds the per-query cost ceiling."""


class AgentMaxIterationsError(OmniRAGError):
    """Raised when the agent loop hits MAX_ITERATIONS without finishing."""


# ── HTTP error factories ───────────────────────────────────────────────────────

def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(detail: str = "Insufficient permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def service_unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
