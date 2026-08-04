from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pipeline import get_assessment_service
from app.models.user import User
from app.schemas.assessment import AssessmentPublicResponse, AssessmentStartResponse
from app.schemas.common import APIResponse
from app.schemas.pipeline import AssessmentDebugResponse
from app.services.assessment import AssessmentService

router = APIRouter()


@router.post(
    "",
    response_model=APIResponse[AssessmentStartResponse],
)
async def start_assessment(
    background_tasks: BackgroundTasks,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.start_assessment(db, current_user.id)

    if not result.already_running:
        background_tasks.add_task(
            assessment_service.run_competency_pipeline,
            result.assessment_id,
        )
        response.status_code = status.HTTP_202_ACCEPTED
    else:
        response.status_code = status.HTTP_200_OK

    return APIResponse(
        success=True,
        message="Assessment already in progress" if result.already_running else "Assessment started",
        data=AssessmentStartResponse(
            assessment_id=result.assessment_id,
            pipeline_run_id=result.pipeline_run_id,
            status=result.status if result.already_running else "PROCESSING",
            already_running=result.already_running,
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
    data = await assessment_service.get_assessment_debug(db, current_user.id, assessment_id)
    return APIResponse(success=True, message="Assessment debug data retrieved", data=data)
