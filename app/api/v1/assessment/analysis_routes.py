from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.rate_limit import rate_limit_analyze
from app.models.user import User
from app.repositories.profile import profile_repo
from app.schemas.assessment_task_analysis import TaskAnalysisRunResponse
from app.schemas.common import APIResponse
from app.services.assessment_task_analysis import (
    AssessmentTaskAnalysisService,
    assessment_task_analysis_service,
)
from app.services.task_3b_grounding import build_profile_grounding
from app.services.three_b_export import (
    build_category_export_context,
    build_task_export_context,
    render_category_html,
    render_category_json,
    render_category_pdf,
    render_task_pdf,
)

router = APIRouter()

VALID_EXPORT_CATEGORIES = {"BUILD", "BLEND", "BOT"}
VALID_EXPORT_FORMATS = {"pdf", "html", "json"}


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


from app.schemas.assessment_task_analysis import TaskAnalysisItem, TaskAnalysisStatusUpdate

@router.patch(
    "/{assessment_id}/analysis/{task_id}/status",
    response_model=APIResponse[TaskAnalysisItem],
)
async def update_task_analysis_status(
    assessment_id: UUID,
    task_id: UUID,
    payload: TaskAnalysisStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_service: AssessmentTaskAnalysisService = Depends(get_analysis_service),
):
    data = await analysis_service.update_task_status(
        db, current_user.id, assessment_id, task_id, payload.status
    )
    return APIResponse(success=True, message="Task status updated", data=data)


@router.get("/{assessment_id}/analysis/export")
async def export_category_analysis(
    assessment_id: UUID,
    category: str = Query(..., description="BUILD, BLEND, or BOT"),
    format: str = Query(default="pdf", alias="format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_service: AssessmentTaskAnalysisService = Depends(get_analysis_service),
):
    cat = category.upper().strip()
    fmt = format.lower().strip()
    if cat not in VALID_EXPORT_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category.")
    if fmt not in VALID_EXPORT_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format.")

    analysis = await analysis_service.get_analysis(db, current_user.id, assessment_id)
    profile = await profile_repo.get_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    context = build_category_export_context(
        analysis,
        cat,
        build_profile_grounding(profile),
    )

    filename_base = f"CareerShift-3B-{cat}"

    if fmt == "json":
        body = render_category_json(context)
        return Response(
            content=body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
        )
    if fmt == "html":
        html = render_category_html(context)
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.html"'},
        )

    pdf_bytes = render_category_pdf(context)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
    )


@router.get("/{assessment_id}/analysis/{task_id}/export")
async def export_task_analysis(
    assessment_id: UUID,
    task_id: UUID,
    format: str = Query(default="pdf", alias="format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_service: AssessmentTaskAnalysisService = Depends(get_analysis_service),
):
    fmt = format.lower().strip()
    if fmt != "pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF format is supported.")

    analysis = await analysis_service.get_analysis(db, current_user.id, assessment_id)
    profile = await profile_repo.get_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    context = build_task_export_context(analysis, str(task_id), build_profile_grounding(profile))
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task analysis not found.")

    task_title = context["task"].get("task_title", "task")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in task_title)[:40]
    pdf_bytes = render_task_pdf(context)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CareerShift-3B-{safe_name}.pdf"'},
    )
