from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.assessment_task import (
    AssessmentTaskResponse,
    AssessmentTasksBulkUpsert,
    TaskGenerationResponse,
)
from app.schemas.common import APIResponse
from app.services.assessment_tasks import AssessmentTaskService, assessment_task_service

router = APIRouter()


def get_assessment_task_service() -> AssessmentTaskService:
    return assessment_task_service


@router.get("/{assessment_id}/tasks", response_model=APIResponse[list[AssessmentTaskResponse]])
async def list_tasks(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task_service: AssessmentTaskService = Depends(get_assessment_task_service),
):
    data = await task_service.get_tasks(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="Tasks retrieved", data=data)


@router.post(
    "/{assessment_id}/tasks/generate",
    response_model=APIResponse[TaskGenerationResponse],
)
async def generate_tasks(
    assessment_id: UUID,
    regenerate: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task_service: AssessmentTaskService = Depends(get_assessment_task_service),
):
    data = await task_service.generate_tasks(
        db, current_user.id, assessment_id, regenerate=regenerate
    )
    return APIResponse(success=True, message="Tasks generated", data=data)


@router.put("/{assessment_id}/tasks", response_model=APIResponse[list[AssessmentTaskResponse]])
async def save_tasks(
    assessment_id: UUID,
    payload: AssessmentTasksBulkUpsert,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    task_service: AssessmentTaskService = Depends(get_assessment_task_service),
):
    data = await task_service.save_tasks(db, current_user.id, assessment_id, payload)
    return APIResponse(success=True, message="Tasks saved", data=data)
