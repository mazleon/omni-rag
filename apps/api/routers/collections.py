import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db, set_rls_context
from core.models import Document, Org, User, Collection
from apps.api.routers.auth import get_current_active_user

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreateRequest(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    document_count: int
    created_at: str
    updated_at: str


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]
    total: int


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(
    request: CollectionCreateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    collection = Collection(
        id=uuid.uuid4(),
        org_id=org.id,
        name=request.name,
        description=request.description,
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)

    return CollectionResponse(
        id=str(collection.id),
        name=collection.name,
        description=collection.description,
        document_count=0,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)

    total = await session.scalar(
        select(func.count(Collection.id)).where(Collection.org_id == org.id)
    )

    stmt = (
        select(Collection, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.collection_id == Collection.id)
        .where(Collection.org_id == org.id)
        .group_by(Collection.id)
        .order_by(Collection.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()

    return CollectionListResponse(
        collections=[
            CollectionResponse(
                id=str(col.id),
                name=col.name,
                description=col.description,
                document_count=doc_count,
                created_at=col.created_at.isoformat(),
                updated_at=col.updated_at.isoformat(),
            )
            for col, doc_count in rows
        ],
        total=total or 0,
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    row = (await session.execute(
        select(Collection, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.collection_id == Collection.id)
        .where(Collection.id == collection_id, Collection.org_id == user.org_id)
        .group_by(Collection.id)
    )).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Collection not found")
    collection, doc_count = row

    return CollectionResponse(
        id=str(collection.id),
        name=collection.name,
        description=collection.description,
        document_count=doc_count,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


@router.patch("/{collection_id}", response_model=CollectionResponse)
@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: uuid.UUID,
    request: CollectionUpdateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.org_id == user.org_id,
        )
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    if request.name is not None:
        collection.name = request.name
    if request.description is not None:
        collection.description = request.description

    await session.commit()
    await session.refresh(collection)

    doc_count = await session.scalar(
        select(func.count(Document.id)).where(Document.collection_id == collection.id)
    ) or 0

    return CollectionResponse(
        id=str(collection.id),
        name=collection.name,
        description=collection.description,
        document_count=doc_count,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Collection).where(
            Collection.id == collection_id,
            Collection.org_id == user.org_id,
        )
    )
    collection = result.scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    await session.delete(collection)
    await session.commit()

    return {"message": "Collection deleted", "collection_id": str(collection_id)}
