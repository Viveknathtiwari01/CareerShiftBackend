from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai_readiness import AIReadinessResponse
from app.schemas.common import APIResponse
from app.services.ai_readiness import AIReadinessService, ai_readiness_service

router = APIRouter()


def get_readiness_service() -> AIReadinessService:
    return ai_readiness_service


@router.get("/{assessment_id}/readiness", response_model=APIResponse[AIReadinessResponse])
async def get_ai_readiness(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    readiness_service: AIReadinessService = Depends(get_readiness_service),
):
    data = await readiness_service.get_readiness(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="AI readiness score calculated", data=data)
