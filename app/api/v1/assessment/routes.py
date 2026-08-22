from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pipeline import get_assessment_service
from app.dependencies.rate_limit import rate_limit_assessment_start
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCurrentResponse,
    AssessmentPublicResponse,
    AssessmentStartResponse,
    AssessmentSummaryResponse,
)
from app.schemas.common import APIResponse
from app.schemas.pipeline import AssessmentDebugResponse
from app.services.assessment import AssessmentService
from app.services.task_dispatch import dispatch_competency_pipeline

router = APIRouter()


@router.get("", response_model=APIResponse[list[AssessmentSummaryResponse]])
async def list_assessments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    data = await assessment_service.list_assessments_for_user(db, current_user.id)
    return APIResponse(success=True, message="Assessments retrieved", data=data)


@router.get("/current", response_model=APIResponse[AssessmentCurrentResponse])
async def get_current_assessment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    data = await assessment_service.resolve_current_assessment(db, current_user.id)
    message = (
        "Existing assessment loaded"
        if data.reused_existing
        else "No reusable assessment sync required"
    )
    return APIResponse(success=True, message=message, data=data)


@router.post(
    "",
    response_model=APIResponse[AssessmentStartResponse],
)
async def start_assessment(
    background_tasks: BackgroundTasks,
    response: Response,
    force: bool = Query(default=False, description="Force a new assessment even if a valid one exists"),
    current_user: User = Depends(rate_limit_assessment_start),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.start_assessment(db, current_user.id, force=force)

    should_dispatch = (not result.already_running) or result.needs_pipeline_dispatch
    if should_dispatch:
        dispatch_competency_pipeline(
            background_tasks,
            assessment_id=result.assessment_id,
            run_pipeline=assessment_service.run_competency_pipeline,
        )
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        response.status_code = status.HTTP_200_OK

    if result.reused_existing and result.status == "COMPLETED":
        message = "Existing competency mapping loaded"
    elif result.reused_existing and not result.needs_pipeline_dispatch:
        message = "Assessment already in progress"
    elif result.profile_stale:
        message = "Profile updated regenerating competency mapping"
    else:
        message = "Assessment started"

    return APIResponse(
        success=True,
        message=message,
        data=AssessmentStartResponse(
            assessment_id=result.assessment_id,
            pipeline_run_id=result.pipeline_run_id,
            status=result.status if result.reused_existing else "PROCESSING",
            already_running=result.already_running,
            reused_existing=result.reused_existing,
            profile_stale=result.profile_stale,
        ),
    )


@router.get("/{assessment_id}", response_model=APIResponse[AssessmentPublicResponse])
async def get_assessment(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    data = await assessment_service.get_assessment_public(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="Assessment retrieved", data=data)


@router.post(
    "/{assessment_id}/retry",
    response_model=APIResponse[AssessmentStartResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_assessment(
    assessment_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.retry_assessment(db, current_user.id, assessment_id)
    background_tasks.add_task(
        assessment_service.run_competency_pipeline,
        result.assessment_id,
    )
    return APIResponse(
        success=True,
        message="Assessment retry started",
        data=AssessmentStartResponse(
            assessment_id=result.assessment_id,
            pipeline_run_id=result.pipeline_run_id,
            status=result.status,
            already_running=False,
        ),
    )


@router.get("/{assessment_id}/debug", response_model=APIResponse[AssessmentDebugResponse])
async def get_assessment_debug(
    assessment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )
    data = await assessment_service.get_assessment_debug(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="Assessment debug data retrieved", data=data)
