from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_analyze
from app.models.user import User
from app.schemas.assessment_task_analysis import TaskAnalysisRunResponse
from app.schemas.common import APIResponse
from app.services.assessment_task_analysis import (
    AssessmentTaskAnalysisService,
    assessment_task_analysis_service,
)

router = APIRouter()


def get_analysis_service() -> AssessmentTaskAnalysisService:
    return assessment_task_analysis_service


@router.get("/{assessment_id}/analysis", response_model=APIResponse[TaskAnalysisRunResponse])
async def get_task_analysis(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_service: AssessmentTaskAnalysisService = Depends(get_analysis_service),
):
    data = await analysis_service.get_analysis(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="3B analysis retrieved", data=data)


@router.post("/{assessment_id}/analyze", response_model=APIResponse[TaskAnalysisRunResponse])
async def run_task_analysis(
    assessment_id: UUID,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(rate_limit_analyze),
    db: AsyncSession = Depends(get_db),
    analysis_service: AssessmentTaskAnalysisService = Depends(get_analysis_service),
):
    data = await analysis_service.analyze_tasks(
        db, current_user.id, assessment_id, regenerate=regenerate
    )
    message = "3B analysis complete" if data.analyses else "3B analysis started"
    return APIResponse(success=True, message=message, data=data)
