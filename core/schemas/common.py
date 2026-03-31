"""Shared base schemas used across all API responses."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class BaseResponse(BaseModel):
    """Every API response carries a request_id for distributed tracing."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class PaginatedResponse(BaseResponse, Generic[DataT]):
    items: list[DataT]
    total: int
    page: int
    page_size: int
    has_next: bool


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
