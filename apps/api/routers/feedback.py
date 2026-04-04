from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db, set_rls_context
from core.models import User, Query as QueryModel
from apps.api.routers.auth import get_current_active_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    query_id: str
    feedback: int


class FeedbackResponse(BaseModel):
    message: str
    query_id: str
    feedback: int


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    try:
        query_id = __import__("uuid").UUID(request.query_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid query_id format")

    result = await session.execute(
        select(QueryModel).where(
            QueryModel.id == query_id,
            QueryModel.org_id == user.org_id,
        )
    )
    query_record = result.scalar_one_or_none()
    
    if not query_record:
        raise HTTPException(status_code=404, detail="Query not found")

    if request.feedback not in [-1, 0, 1]:
        raise HTTPException(status_code=400, detail="Feedback must be -1, 0, or 1")

    query_record.feedback = request.feedback
    await session.commit()

    return FeedbackResponse(
        message="Feedback recorded successfully",
        query_id=request.query_id,
        feedback=request.feedback,
    )
